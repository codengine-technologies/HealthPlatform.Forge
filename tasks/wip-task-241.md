# todo-task-241.md — Le keep-alive de la connexion SMTP ne se déclenche jamais : comprendre avant de retoucher

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune. ⚠️ **Suite directe de task-238**, mergée le 2026-08-07
et dont la contre-épreuve a échoué **deux campagnes consécutives**.
**Priorité**: **2** — `send` est le seul bloqueur des paliers 50 et 100 (10/11
vertes sinon), et il pèse 10,5 % du temps serveur. Mais la priorité n'est pas
d'aller plus vite : c'est de **cesser de livrer sur une hypothèse non vérifiée**.

> ## ⚠️ CETTE US COMMENCE PAR UNE INSTRUCTION, PAS PAR UN CORRECTIF
>
> task-238 a livré un keep-alive, une sonde retirée du chemin nominal et des
> caches OCSP réglables. **Aucun de ces trois gestes n'a produit d'effet
> mesurable.** Écrire un quatrième correctif sans savoir pourquoi les trois
> premiers sont inertes reproduirait l'erreur de task-222 — une US applicative
> bâtie sur une cause plausible et fausse, annulée après coup.
>
> **Le premier livrable de cette US est donc une réponse, pas du code** : par
> quel chemin exact la connexion retenue meurt-elle entre deux envois, et
> pourquoi le mécanisme d'entretien ne s'exécute-t-il jamais ? Le correctif ne
> s'écrit qu'après, et il doit découler de la réponse.

## Objective

Que l'acquittement d'envoi passe sous 1 000 ms **parce qu'on a compris** ce qui
coûte, ou qu'on écrive noir sur blanc que ce n'est pas atteignable sans changer
d'architecture — et alors la grille SLO doit être amendée plutôt que laissée en
échec permanent.

## La mesure — deux campagnes K=1, verdict identique

| Signal | Référence `120344` (avant task-238) | `142630` (après task-238) |
|---|---|---|
| `send` p50 — 50 / 100 / 200 médecins | 1 245 / 1 238 / 1 279 ms | **1 235 / 1 228 / 1 294 ms** |
| Cible SLO | 1 000 ms | 1 000 ms |
| `connect` / `send_message` | — | **5 395 / 2 920** |
| `noop` (la sonde d'entretien) | — | **0** |

**Zéro `noop` est le fait qui commande toute la US** : le mécanisme d'entretien
livré par task-238 ne s'exécute **jamais** au rythme réel du parcours. Et
~1,85 connexion par envoi signifie que la connexion retenue est morte à
pratiquement chaque emprunt.

Contexte déjà établi et à ne pas re-mesurer : le coût est **plat** sur les trois
paliers (donc fixe par appel, indépendant de la charge) ; au rythme du parcours
un médecin laisse **~4,8 min** entre deux envois ; et les 5 réplicas n'ont
**aucune affinité de session** — le client SMTP vit dans un singleton par
processus, donc un même praticien change de réplica d'un envoi à l'autre.

## Les questions auxquelles l'instruction doit répondre

1. **Le service d'entretien tourne-t-il ?** Est-il enregistré, démarré, et sa
   boucle s'exécute-t-elle ? (Un `IHostedService` non enregistré ne dit rien.)
2. **Quelle est la durée de vie effective** de la connexion retenue, face aux
   ~4,8 min entre deux envois d'un même médecin — et face au délai d'inactivité
   du serveur SMTP d'en face ?
3. **L'absence d'affinité de session est-elle la cause dominante ?** Avec 5
   réplicas, la probabilité qu'un envoi retombe sur le réplica qui détient la
   connexion est de 1/5 : le mécanisme ne peut structurellement valoir que ~20 %
   de sa promesse. **Le chiffrer**, ne pas l'affirmer.
4. **Où partent réellement les ~1 240 ms ?** Décomposition d'une requête
   représentative par identifiant de trace (CONNECT, TLS, vérification de
   révocation, AUTH, DATA, archivage IMAP) — la méthode du § 5b-bis du skill.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que le remède est l'affinité de session.** C'est
  l'hypothèse la plus séduisante, donc celle qui mérite le plus d'être vérifiée
  avant d'être codée. Une affinité par praticien a un coût propre (routage,
  déséquilibre de charge, comportement au redémarrage d'un réplica) qui doit
  être posé face au gain **mesuré**, pas espéré.
- **Ne pas présumer qu'on peut détendre la vérification de révocation.** C'est
  une exigence de confiance MSSanté/IGC Santé, et task-231 l'avait déjà placée
  hors périmètre. On amortit son coût, on ne le supprime pas.
- **Ne pas présumer que la cible de 1 000 ms est atteignable.** Si la
  décomposition montre un plancher incompressible (TLS + OCSP + AUTH + DATA +
  archivage IMAP sous latence MSSanté), **le dire** et proposer l'amendement de
  la grille SLO. Une cible qu'on sait inatteignable et qu'on laisse rouge use la
  valeur d'alerte de toute la grille.
- **Ne pas présumer que l'archivage est négligeable.** `AppendToSent` détient le
  verrou de session **1,42 s p95** (premier détenteur depuis task-239) et
  l'archivage reste **synchrone** dans l'acquittement — décision de contrat prise
  par task-231. Il fait donc partie des ~1 240 ms et doit apparaître dans la
  décomposition.

## Definition of Done

- [ ] **Livrable n°1 — la réponse écrite** : pourquoi `noop = 0`, quelle est la
      durée de vie effective de la connexion, et quelle part du coût revient à
      chaque poste (décomposition par trace). Consignée dans le `## Develop log`.
- [ ] Le chiffre de l'absence d'affinité est **mesuré**, pas déduit : part des
      envois qui retombent sur le réplica détenteur de la connexion
- [ ] Le correctif, **s'il y en a un**, découle explicitement de la réponse et
      cite la mesure qui le justifie
- [ ] Si la conclusion est « cible inatteignable en l'état » : proposition
      d'amendement de `docs/SLO-parcours-medecin.md` avec le plancher mesuré et
      sa justification
- [ ] Build 0 erreur, tests verts
- [ ] **Zéro changement de contrat** : route, code HTTP, corps de réponse
      (`queued` / `archived` / `warning`) inchangés ; l'archivage reste synchrone
- [ ] La vérification de révocation du certificat serveur reste **active**
- [ ] Aucune donnée de santé dans les logs de connexion SMTP (ni sujet, ni
      contenu, ni INS) ; ⚠️ un fragment de JWT est journalisé en avertissement
      dans `SmtpConnectionFactory` — **dette signalée par la revue de task-231**,
      à traiter ici ou à re-signaler
- [ ] **Contre-épreuve au banc** : tir `journey` K=1 iso-conditions avec
      `142630`. Selon l'issue : `send` p50 < 1 000 ms, **ou** la démonstration
      chiffrée que le plancher est ailleurs — les deux sont des succès, un
      correctif sans effet mesuré n'en est pas un.

## Manual Test Plan

```bash
cd Api/Mail && dotnet run --project src/AppHost --launch-profile https-load-test
```

- Envoyer deux messages successifs depuis la **même session** praticien, espacés
  de ~5 minutes (le rythme réel du parcours) ; observer dans Seq si le second
  paie une connexion complète, et si une sonde d'entretien s'est exécutée entre
  les deux
- Relever le compteur de sollicitations : rapport `connect` / `send_message`
- Contrôle de panne : couper le serveur SMTP entre deux envois → le second
  reconnecte proprement ou rend l'erreur habituelle, **jamais un faux succès**
- Vérifier la copie dans Envoyés (`archived: true`) pour les deux envois

Données de test synthétiques uniquement — aucune donnée de santé réelle.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — performance interne du chemin d'envoi
- **Exigences DSR honorées** : aucune nouvelle ; l'exigence de vérification des
  certificats **IGC Santé** est explicitement **préservée** (DOD)
- **INS** : non applicable — la garde d'opposition patient est inchangée
- **Authentification PS** : inchangée
- **Habilitations** : non applicable
- **Interop CI-SIS** : non applicable — en-têtes et corps MSSanté inchangés
- **MSSanté** : ⚠️ **le point d'attention de la US.** Toute réutilisation ou
  affinité de connexion doit garantir qu'un message part **sous l'identité du
  praticien émetteur** et sous aucune autre — c'est le défaut le plus grave que
  ce mécanisme pourrait introduire, et task-231 l'avait verrouillé par un test
  dédié (« deux praticiens ne partagent jamais une connexion authentifiée »).
  Ce test doit rester vert, et toute affinité doit être couverte par le même
  raisonnement.
- **Tracé PGSSI-S** : inchangé — traces d'envoi et d'archivage conservées
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé
- **AIPD / impact RGPD** : inchangé

---

## Branches

- `api-mail` (pushed) : `fix/task-241-smtp-keepalive-diagnostic` —
  https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-241-smtp-keepalive-diagnostic
- `dtos-mss` (pushed) : même nom — **auto-incluse**, aucun changement de contrat attendu
  (contrainte absolue de la US) ; si vide, aucune PR, suppression au merge
  (10ᵉ occurrence attendue du défaut de cycle).

Préfixe `fix/` retenu comme pour task-238 et task-239 (même famille de travail perf sur E015),
étant entendu que **le premier livrable est une réponse écrite, pas un correctif** — cf.
l'encadré en tête de US.

Pré-flight vert sur les six repos mesurables, working trees propres. Dépendances : aucune ;
task-238 (contexte direct) est archivée. Le blocage constaté au premier `/start` — task-240
restée en `wip` alors que sa PR #173 était mergée — est levé : elle a été archivée.

---

## Develop log

### Livrable n°1 — la réponse, avant tout correctif

**Les deux faits fondateurs de la US sont des lectures d'instrument, pas des faits de
comportement.** Vérifié dans le code, site par site.

#### 1. `noop = 0` ne mesure pas le keep-alive — il mesure la sonde, et il vaut 0 *parce que task-238 a réussi*

`MailServerCommands.NoOp` n'est enregistré qu'à **un seul endroit** du dépôt :
`SmtpConnectionProbe.cs:35`, la **sonde de fraîcheur**. Le battement d'entretien
(`MailClientSession.SendSmtpKeepAliveNoopAsync`, ligne 339) appelle `NoOpAsync` **directement
sur le client, sans enregistrer de sollicitation**.

Or task-238 a précisément retiré la sonde du chemin nominal (`SmtpProbeMaxAge` = 60 s : pas de
sonde si le signal de santé a moins de 60 s). **`noop = 0` est donc la preuve que le remède 2 de
task-238 fonctionne**, et ne dit **rien** sur le keep-alive, qui n'est pas instrumenté. La US
conclut « le mécanisme d'entretien ne s'exécute jamais » à partir d'un compteur qui ne le compte
pas — exactement le motif de task-222, retrouvé cette fois dans les prémisses de la US.

#### 2. « ~1,85 connexion par envoi » agrège l'IMAP et le SMTP

Le compteur porte deux étiquettes, `command` **et** `operation`. Les sites d'enregistrement :

| `command` | `operation` | site |
|---|---|---|
| `connect` / `authenticate` | `ConnectImap` | `ImapConnectionService` |
| `connect` / `authenticate` | **`SmtpConnect`** | `SmtpConnectionFactory` |
| `noop` | `SmtpSend` | `SmtpConnectionProbe` (**seul site `noop`**) |
| `send_message` | `SmtpSend` | `SmtpService` |

`connect = 5 395` est donc la **somme IMAP + SMTP**, sur un parcours dont l'essentiel est de la
lecture. Le ratio 5 395 / 2 920 ne mesure pas les reconnexions SMTP par envoi : il faut filtrer
sur `operation="SmtpConnect"`, ce que le rapport ne fait pas.

#### 3. Le keep-alive est bien démarré — et il est **structurellement impuissant**

C'est la réponse de fond, et elle n'est pas l'affinité de session.

`EnsureKeepAliveStarted()` est bien appelé à l'adoption d'un client SMTP (task-238) comme à la
création du client IMAP : ce n'est pas un `IHostedService` oublié, c'est une boucle par session,
démarrée. **Mais deux horloges indépendantes gouvernent la connexion, et le keep-alive n'agit que
sur la mauvaise** :

- `LastSmtpAccessTime` est rafraîchi par `RefreshSmtp()`, appelé depuis **un seul endroit** —
  `MailClientSessionManager:170`, c'est-à-dire **à l'emprunt du jeton SMTP**, donc à l'envoi.
- `IsSmtpConnectionIdle` = `now − LastSmtpAccessTime > SmtpIdleTimeout` (**5 min**), et le
  balayage (`CleanupExpiredSessions`, cadence 1 min) **ferme la connexion** sur ce critère.
- Le battement, lui, met à jour `_lastSmtpHealthySignalUtc` — le **signal de santé**, que
  task-238 a délibérément rendu distinct de l'accès. Il ne touche **jamais** `LastSmtpAccessTime`.

**Conséquence** : le keep-alive garde la connexion *vivante sur le fil*, pendant que l'éviction la
ferme sur son *inactivité d'usage*. Aucun nombre de battements ne peut l'empêcher. Le remède 1 de
task-238 visait la bonne connexion et la mauvaise horloge.

**Et la marge est de douze secondes** : le parcours laisse **~4,8 min** entre deux envois d'un
même médecin, contre un `SmtpIdleTimeout` de **5 min**. Même sans dispersion, la marge est
dérisoire ; avec le temps de réflexion tiré au hasard qu'impose le modèle par parcours, une part
importante des intervalles dépasse 5 min. La connexion est donc évincée avant l'envoi suivant
dans une fraction élevée des cas — ce qui explique le coût **plat sur les trois paliers** (il est
payé par appel, pas subi sous la charge) et l'inertie des trois remèdes.

#### Ce que cette réponse ne tranche pas encore

- **La question 3 (affinité) reste ouverte et n'est pas la cause dominante identifiée.** Elle
  s'ajoute au mécanisme ci-dessus au lieu de le remplacer : même avec une connexion non évincée,
  1 réplica sur 5 la détient. Le chiffrer exige le banc, avec un filtre `operation="SmtpConnect"`.
- **La question 4 (décomposition des ~1 240 ms)** exige le banc et une trace représentative.

#### Ce qui découle directement de la réponse

1. **Instrumenter le battement** (`operation="SmtpKeepAlive"`) — sans quoi la question 1 restera
   sans réponse mesurable au prochain tir, et le prochain rapport redira « noop = 0 ».
2. **Séparer `connect` par `operation`** dans le rapport — sinon le ratio continuera de mélanger
   les deux protocoles.
3. **La correction de fond est un arbitrage, pas une évidence** : soit le battement rafraîchit
   aussi l'accès (la rétention devient « vivante tant qu'entretenue » — **changement de politique
   que task-238 s'était explicitement interdit**), soit `SmtpIdleTimeout` passe au-dessus de
   l'intervalle réel entre envois. Les deux augmentent le nombre de connexions retenues par boîte,
   face à la **contrainte opérateur MSSanté** que task-231 et task-238 ont toutes deux préservée.
   C'est le point qui mérite l'arbitrage humain au HAG, pas une décision de la forge.

### Ce qui a été livré ici — commit `9ec3a60`

**Le correctif d'instrument, et lui seul** : le battement d'entretien SMTP enregistre désormais
sa sollicitation sous l'étiquette d'opération **`SmtpKeepAlive`**, distincte de `SmtpSend`. Sans
lui, le prochain tir redirait « noop = 0 » et la question 1 resterait sans réponse mesurable.

Appel direct à `MailProcessingMetrics.RecordMailServerSolicitation` plutôt qu'au recorder par
requête : la boucle tourne **hors requête**, et l'y brancher attribuerait ses allers-retours à la
requête qui passe — le recorder tient un compte par requête et une étiquette d'activité.

**Validation** : build solution 0 erreur ; application **2073/2074**. L'unique échec est le flaky
pré-existant `MailExportServiceTests` (`UglyToad.PdfPig`, famille `Services/Export` signalée
depuis task-228) — sans rapport avec cette task.

**Aucun changement de comportement** : ni la politique de rétention, ni les délais, ni le contrat
d'envoi ne sont touchés. C'est délibéré — voir le point 3 ci-dessus : la correction de fond est un
arbitrage entre la durée de rétention et la contrainte opérateur MSSanté, et il revient à l'humain
au HAG, pas à la forge.

### 🚧 Ce que cette livraison ne prouve pas

Elle ne fait pas passer `send` sous 1 000 ms, et ne prétend pas le faire. Elle rend **mesurable**
ce qui ne l'était pas, et elle remplace deux faits fondateurs faux par un mécanisme établi depuis
le code. Le prochain tir `journey` K=1 doit maintenant rendre, en filtrant sur `operation` :
`SmtpKeepAlive` **non nul** (le battement tourne), `SmtpConnect` par envoi (le vrai ratio de
reconnexion SMTP, séparé de l'IMAP), et la décomposition des ~1 240 ms — questions 3 et 4, qui
exigent le banc.


## Simplify log

**Skip propre.** Le diff est d'un seul fichier et de 28 lignes, dont 21 de commentaire : une
constante d'étiquette et un appel d'enregistrement, au point exact où le geste a lieu. Il n'y a ni
duplication, ni indirection à retirer, ni niveau d'abstraction à corriger.

Candidat examiné et **non retenu** : instrumenter symétriquement le battement **IMAP**
(`SendKeepAliveNoopAsync`, même boucle, même absence de compteur). Ce serait cohérent et
probablement utile — mais la US porte sur `send`, et ajouter une étiquette d'opération IMAP
changerait la lecture des campagnes en cours sur un axe que personne n'a demandé. Signalé ici pour
qu'une prochaine US d'entretien le prenne, plutôt que glissé au passage.
