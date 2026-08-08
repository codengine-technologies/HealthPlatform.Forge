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
