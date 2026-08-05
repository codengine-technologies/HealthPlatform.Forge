# todo-task-231.md — Chaque envoi paie une connexion SMTP neuve (TLS + OCSP + AUTH) : réutiliser la connexion et construire le MIME avant de se connecter

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: task-216 (todo — retrait de la voie d'écriture IMAP task-213) :
**coordination obligatoire**, les deux tasks touchent le chemin d'envoi/archivage ;
celle-ci ne touche que la jambe SMTP et ne dépend pas de l'issue de task-216.
**Priorité**: **2** — `send` est hors grille SLO (p50 1 340 ms) et pèse 13,4 %
du temps serveur. Coût fixe par appel, indépendant de la charge.

> ⚠️ **Contrainte absolue — aucun impact frontend.** Même route
> (`POST Mail/sendmail`), même corps de réponse — notamment le champ
> `archived`/`warning` (sémantique anti-renvoi de document posée par
> task-223) reste **décidable au moment de l'acquittement** : l'archivage
> IMAP reste synchrone dans cette task. Le différer serait un changement de
> contrat → hors périmètre, décision produit séparée si besoin.

## Objective

Réduire le coût fixe de l'acquittement d'envoi en s'attaquant à ce que
l'analyse de code a établi comme postes évitables — sans toucher à l'ordre
métier (SMTP puis archivage) ni au contrat :

1. **Connexion SMTP jetable à chaque envoi** : `SmtpConnectionFactory` fait
   `new SmtpClient()` → CONNECT → TLS avec **vérification de révocation
   OCSP/CRL du certificat** → AUTH, puis `DisconnectAsync(true)` (QUIT) à la
   fin — **aucun pool**, contrairement à IMAP qui réutilise la connexion de
   session. C'est le poste dominant du coût fixe.
2. **Le MIME est construit après la connexion**, avec **2 lectures base sous
   session SMTP ouverte** (identité expéditeur via `GetSettingsAsync`,
   signature par défaut via `GetDefaultAsync`) : la connexion authentifiée
   est tenue inutilement pendant ces I/O.
3. La jambe IMAP (`AppendToSent` : SELECT + APPEND + CLOSE, ~2,3 s de
   détention p95 sur sa voie d'écriture dédiée, attente nulle) bénéficie déjà
   de la réutilisation de connexion après le premier envoi — le gain est
   côté SMTP.

## Remèdes demandés

1. **Réutiliser la connexion SMTP** au sein de la session praticien (même
   patron que le pool IMAP par session) : le CONNECT + TLS + OCSP + AUTH ne
   se paie qu'au premier envoi, les suivants font DATA (+ NOOP de validation
   de fraîcheur). Gestion propre : détection de connexion morte → reconnexion
   transparente ; fermeture au nettoyage de session (même cycle de vie que
   les clients IMAP de session).
2. **Construire le MIME avant d'ouvrir/emprunter la connexion** : les
   lectures base (identité, signature) se font hors session SMTP tenue ; les
   settings sont déjà cachés Redis 5 min — utiliser ce cache tel quel.
3. **Compter les allers-retours SMTP** dans `MailServerSolicitationRecorder`
   (aujourd'hui câblé sur IMAP uniquement) — la métrique de task-225 devient
   complète et la contre-épreuve lisible.

**Hors périmètre (décisions explicites)** : archivage différé (contrat
`archived`), désactivation du contrôle de révocation OCSP/CRL (exigence de
confiance MSSanté/IGC Santé — on ne détend pas la vérification de
certificat, on amortit son coût par la réutilisation de connexion).

## La mesure — tirs `journey-mssante-n300` du 2026-08-04

| Signal | Valeur (tir 17:05) |
|---|---|
| `send` p50 / p95 (palier 300) | 1 340 / 2 063 ms — hors grille SLO, **plat sur les 3 paliers** (coût fixe) |
| Part du temps serveur | 13,4 % (4 502 s, 2 853 appels) |
| Verrou `AppendToSent` (voie d'écriture) | attente 0,005 s / détention 2,322 s p95 — le coût est le travail, pas la contention |
| Route serveur `sendmail` p95 max | 5 250 ms |

Décomposition établie par l'analyse de code : validation + garde opposition
patient (1 requête/destinataire INS) → **connexion SMTP complète** → MIME
(2 lectures base sous connexion) → DATA → QUIT → archivage IMAP (3 RTT) →
réponse. Sous latence injectée, la jambe « connexion + handshake » est
l'essentiel de l'écart entre 1 340 ms observés et le plancher DATA + APPEND.

## Definition of Done

- [ ] Build passes (0 errors) — `dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) — `dotnet test HealthPlatform.Api.Mail.sln`
- [ ] **Zéro changement de contrat** : route, code HTTP, corps de réponse (`queued`/`archived`/`warning`) identiques — tests d'intégration existants inchangés ; l'archivage reste synchrone
- [ ] Connexion SMTP réutilisée au sein de la session : unit tests — 2e envoi sans CONNECT/AUTH, reconnexion transparente sur connexion morte, fermeture au nettoyage de session, pas de fuite de client SMTP (dispose vérifié)
- [ ] MIME construit avant l'emprunt de la connexion — unit test d'ordre d'appels (mock : aucune I/O base entre CONNECT et DATA)
- [ ] La vérification de révocation du certificat serveur reste active (aucune option de validation détendue) — assertion dans les tests de la factory
- [ ] Allers-retours SMTP comptés dans `MailServerSolicitationRecorder`
- [ ] Aucune donnée de santé en clair dans les logs (les logs de connexion SMTP ne portent ni sujet ni contenu ni INS)
- [ ] **Contre-épreuve au banc (bloquante pour le merge, pas pour la PR)** : tir `journey` n300 iso-conditions avant/après :
  - `send` p50 en **nette baisse** (référence : 1 340 ms ; attendu : plancher DATA + APPEND, ordre de grandeur ≤ 800 ms)
  - part de `send` dans le temps serveur en baisse (référence : 13,4 %)
  - 0 erreur d'envoi, vérification par base PASS (les messages envoyés arrivent, complétude tenue)
  - compteur de sollicitations SMTP : ~1 connexion par session et non plus ~1 par envoi

## Manual Test Plan

- Monter le banc : skill `loadtest-skill`
- Tir de contre-épreuve : `journey`, 300 médecins, latence `mssante`,
  iso-conditions avec `journey-mssante-n300-170512`
- Comparer : latence étape 6 « Envoi (acquittement UI) », part de `send` dans
  les axes d'amélioration
- Contrôle fonctionnel : envoyer 2 messages successifs depuis la même session
  → le second est nettement plus rapide ; vérifier la copie dans Envoyés
  (`archived: true`) pour les deux
- Contrôle de panne : couper le serveur SMTP entre deux envois → le second
  reconnecte de façon transparente ou rend l'erreur habituelle (jamais un
  faux succès)

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — optimisation interne
- **Exigences DSR honorées** : non applicable — pas de changement fonctionnel ; l'exigence de vérification des certificats IGC Santé est explicitement **préservée** (DOD)
- **INS** : non applicable — la garde d'opposition patient est inchangée
- **Authentification PS** : inchangée
- **Habilitations** : non applicable
- **Interop CI-SIS** : non applicable — en-têtes et corps MSSanté inchangés (même code de construction MIME, seul le moment change)
- **MSSanté** : la connexion réutilisée reste authentifiée par le même compte/certificat que la connexion jetable ; la vérification de révocation reste active à l'établissement
- **Tracé PGSSI-S** : inchangé — la trace d'envoi et la trace d'archivage (`MailArchiveSent`) sont conservées à l'identique
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé
- **AIPD / impact RGPD** : inchangé

## Branches

- `api-mail` (pushed) : `feat/task-231-smtp-connexion-reutilisee` —
  https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-231-smtp-connexion-reutilisee
- `dtos-mss` (pushed, auto-inclus) : `feat/task-231-smtp-connexion-reutilisee` —
  https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-231-smtp-connexion-reutilisee
  (branche créée par précaution ; aucun changement de contrat n'est attendu —
  la DOD exige zéro changement de contrat, donc elle restera probablement
  sans commit et sans PR)

> **Dépendance task-216 — tranchée au `/start` du 2026-08-05.** La règle
> mécanique de `/start` abandonne sur une dépendance non `done-*`, et task-216
> est en `todo`. Le task file la qualifie explicitement de **coordination
> obligatoire, pas de blocage** (« ne touche que la jambe SMTP et ne dépend pas
> de l'issue de task-216 »), et le contrôle confirme qu'aucune branche
> task-216 n'existe : personne ne travaille sur le chemin d'envoi/archivage.
> Décision : on continue. Si task-216 démarre avant le merge de celle-ci, la
> coordination redevient un point d'attention réel au moment de la synchro
> avec `develop`.

## Simplify log

Passe qualité `/forge-simplify` du 2026-08-05 — `api-mail` seul repo touché
(`dtos-mss` sans commit : aucun changement de contrat, comme la DOD l'exige).

Trois points corrigés, aucun comportement changé :

| Axe | Constat | Correction |
|---|---|---|
| Efficacité | la sonde de repli était allouée **à chaque emprunt**, avec un `NullLogger` pleinement qualifié en ligne | champ initialisé une fois |
| Simplification | `DiscardSmtpClient` / `DisposeSmtpClient` : deux noms pour une seule chose | un seul reste |
| Simplification | extension de test appelée une fois pour tester `Client is not null` | assertion directe, extension supprimée |

Non retenu : les trois appels à `RecordLockWait` d'`AcquireSmtpSlotAsync` se
ressemblent, mais chacun porte une issue distincte (`acquired` / `timeout` /
`cancelled`) — les factoriser rendrait l'étiquette moins lisible qu'elle ne l'est.

Build + **3 362 tests verts** avant et après la passe.

## Sonar log

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | **non mesuré** | **non mesuré** | — |
| New coverage | non mesuré | non mesuré | — |
| Bugs / Vulnérabilités / Smells | non mesuré | non mesuré | — |
| Coverage projet / Duplication / Ratings | non mesuré | non mesuré | — |

**`/sonar` n'a pas pu tourner le 2026-08-05** : le serveur SonarQube n'est pas
joignable (`http://127.0.0.1:9000/api/system/status` → pas de réponse, aucun
conteneur `sonar` en marche) et `SONAR_TOKEN` est absent de l'environnement.

**Ce n'est pas un « rien à signaler ».** Aucune analyse n'a eu lieu, donc la
qualité de ce diff n'est **ni verte ni rouge : elle est non mesurée**. Confondre
les deux serait exactement l'erreur que cette EPIC s'interdit — une absence de
mesure n'est pas un zéro.

Ce qui est établi sans Sonar, et qui ne le remplace pas : build 0 erreur,
**3 362 tests verts**, et la passe `/forge-simplify` (voir `## Simplify log`).

**À faire avant merge** (relève de l'humain — le banc et Sonar sont sur son
poste) : démarrer SonarQube, poser `SONAR_TOKEN`, puis relancer
`/sonar 231` sur la branche. Le diff est petit et localisé (chemin d'envoi
SMTP), donc l'analyse est rapide.

## Lint log

`/lint-angular` — **skip propre** : `client-angular` n'est pas dans les
`**Repos**:` de cette task (US backend pure, justifiée dans le corps) et son
arbre de travail est intact. Aucun code Angular produit, donc rien à linter.

## Lint mobile log

`/lint-mobile` — **skip propre** : `client-mobile` n'est pas dans les
`**Repos**:` de cette task, et `Client/Mobile/` n'est pas un dépôt git sur ce
poste. Aucun code mobile produit, rien à linter.

## Visual verify log

`/verify-visual` — **skip propre** : aucun écran `client-mobile` touché (pas de
`## Stitch design log` dans cette task, `client-mobile` hors `**Repos**:`).
Rien à capturer.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/158
  — label `awaiting-human-merge`, 17 fichiers, MERGEABLE
- `dtos-mss` : **aucune PR** — branche créée par précaution, restée sans commit.
  La DOD exigeait zéro changement de contrat, et il n'y en a eu aucun.

## Code Review Summary

Verdict : **APPROVED**. 17 fichiers revus.

**Un défaut trouvé à la revue et corrigé sur la branche** (`3659817`) :
`DiscardSmtpClient` faisait un `Disconnect(true)` **synchrone** sur le chemin de
requête. Un thread du pool s'y serait garé le temps d'un QUIT — le défaut même
que task-205 a mesuré comme facteur limitant de l'API, et que la règle S4462 du
repo interdit en flux normal. Le QUIT poli ne subsiste que là où il est gratuit
pour la requête : la fermeture de session.

Deux suggestions non bloquantes, consignées dans la PR :

1. `MailClientSession.Dispose` peut fermer un client pendant qu'un emprunt le
   détient. **Exposition pré-existante et identique côté IMAP** — à traiter pour
   les deux voies à la fois, pas ici.
2. `SmtpConnectionFactory` journalise un extrait de JWT en `LogWarning`.
   Pré-existant, hors périmètre, pas une donnée de santé — mais un fragment de
   secret dans les logs. Mérite une US.

**Point de contention nouveau, assumé et instrumenté** : la réutilisation
sérialise les envois concurrents d'une même session, ce qui n'était pas le cas
avant. Verrou `smtp_session`, attente et détention consignées.

## ⛔ Merge bloqué — contre-épreuve au banc du 2026-08-05

Deux choses, toutes deux sur le poste de l'humain :

1. **Contre-épreuve au banc** (DOD, bloquante pour le merge) : tir `journey`
   n300 en iso-conditions avec `journey-mssante-n300-021137`.
2. **`/sonar 231`** : la qualité de ce diff est **non mesurée** (serveur
   injoignable au moment du cycle), ce qui n'est pas la même chose que verte.

### Tir de contre-épreuve `journey-mssante-n300-133618` — 🔴 ROUGE

Iso-conditions strictes avec `journey-mssante-n300-021137` (paramètres recopiés
du `context.journeyPlan`, pas repris des défauts du harnais). 1 h 32,
19 374 passages, 500 bases purgées, maildir recréé, échantillonneur armé.

**1,53 % d'erreurs** (plafond 1 %) — 0,00 % à 100 médecins, 1,08 % à 200,
2,29 % à 300. Échecs = délais de **60 s sur `GET /mail/folders`**, donc sur le
chemin IMAP, **étranger** à la modification.

**Fuite de ressources attribuée par A/B sur la même machine :**

| | Réf. (sans task-231) | Cette branche |
|---|---|---|
| Threads ThreadPool | 6 → **10** | 7 → **8 164** |
| Threads processus | 57 → 81 | 69 → **8 228** |
| File d'attente ThreadPool | 0 | **0** |
| Connexions Kestrel | — | 0 → **701** |
| Mémoire | 386 → ~1 000 Mo | 386 → **2 350 Mo** |

Croissance monotone, ~1,5 thread/s, sur les cinq réplicas. File d'attente à zéro
⇒ threads **retenus**, pas injectés faute de débit. **La ligne fautive n'est pas
identifiée, et elle n'est pas devinée** — task-222 a été annulée pour avoir bâti
sur une cause plausible et fausse.

**Second résultat, indépendant** : la réutilisation ne se déclenche presque jamais
au parcours — 5 300 `connect` pour 5 301 `send_message`, `noop = 3` dont 2 de ma
sonde. Cause mesurée : **5 réplicas sans affinité de session**, le client SMTP
vivant dans un singleton par processus. Sonde de 12 envois consécutifs sur une
même session : `noop = 2` — le mécanisme marche, il n'est pas sollicité. Au
rythme du parcours (~4,8 min entre deux envois d'un médecin, ~24 min par
réplica), il vaut ~1/5 de sa promesse.

**Le tir étant non concluant, le `send` p50 à 1 199 ms (−11 %) ne peut pas être
invoqué** — ni pour, ni contre.

**Verdict DOD** : critère bloquant **non tenu**. Label `awaiting-human-merge`
retiré de la PR #158. À reprendre : trouver la fuite, la corriger, refaire le
tir. Et arbitrer si la réutilisation vaut d'être poursuivie sans affinité de
session.

## Fuite corrigée — 2026-08-05, commit `bcf86a1`

### La cause, nommée puis attribuée

Reproduction courte (100 médecins, 10 min) : threads processus 286 → 965,
pool 24 → 673, ~1,1 thread/s — la pente exacte du tir de 92 min. Capture de
piles sur un réplica : **93 threads sur 120 garés au même endroit** :

```
BaseRepository.get_DataContext()
  get => _dataContext ??= CreateDbContextAsync().GetAwaiter().GetResult();
```

Un getter sync-over-async dont le corps `await` le **sémaphore statique de
provisionnement** et le cache : chaque thread du pool s'y gare pendant que ses
continuations attendent… un thread du pool. Famine auto-entretenue — le
ThreadPool injecte ~1 thread/s, chaque nouveau thread se gare à son tour.
C'est aussi l'origine des délais de 60 s sur `GET /mail/folders`
(`ReconcileFoldersAsync` passe par ce getter). Violation S4462, le défaut même
que task-205 avait mesuré comme facteur limitant.

**Attribution par A/B** (même tir, seule la lignée change) : develop reste
plat (313 → 324), la branche s'emballe. Le défaut est pré-existant mais la
modification l'a rendu atteignable : les deux lectures base de l'envoi,
auparavant espacées par les ~1,3 s d'établissement SMTP, se font désormais
d'emblée — la pression concurrente sur le sémaphore dépasse son débit de
service.

### Le correctif

- `DataContext` ne crée plus rien : le getter **lève** si le contexte n'est
  pas résolu (un site oublié casse au premier test au lieu de fuir en
  silence) ; il ne sert plus que les montages de test (contexte injecté).
- La résolution passe par `GetDataContextAsync()` — `ValueTask` mémoïsée par
  instance, chemin chaud synchrone sans allocation, premier appel asynchrone
  de bout en bout (provisionnement compris), **aucun thread bloqué**.
- Conversion mécanique des ~394 sites : 13 repositories + 2 controllers,
  `var db = await GetDataContextAsync();` hissé avant le premier usage.
  Aucune signature publique modifiée ; 3 helpers privés de composition de
  requête reçoivent `db` en paramètre (pas d'`await` dans les lambdas EF).
- Build 0 erreur, **3 368 tests verts** (dont intégration, qui empruntent la
  vraie voie DI).

### Tir de vérification `fuite-fix-bcf86a1` — 🟢 la fuite est éteinte

Même tir que les deux jambes de l'A/B (100 médecins, 10 min, K=1,25,
latence mssante), 12 804 requêtes servies, `http_req_failed` < 1 % :

| | Branche avant correctif | develop (réf.) | **Branche corrigée** |
|---|---|---|---|
| Threads processus | 286 → **965** | 313 → 324 | **263 → 326** (max 362) |
| Threads ThreadPool | 24 → **673** | 39 → 32 | **23 → 31** (max 45) |

Pente nulle — le pool finit à 31 threads là où il en empilait 673. Le départ
plus bas (263) vient du redémarrage à froid du banc ; le palier rejoint celui
de develop.

Deux artefacts de banc rencontrés et neutralisés en route : (1) le redémarrage
de l'AppHost recrée Toxiproxy **sans ses proxies** (`dovecot-imap`,
`greenmail-smtp` — recréés via l'API, le seed n'a pas de mode « proxies
seuls ») ; (2) un premier tir avec k6 muet (`>/dev/null`) a produit une fausse
ligne plate à **0 requête servie** — le script de tir vérifie désormais le
volume servi et s'invalide sous 1 000 requêtes.

### Reste à faire avant merge (inchangé sur le fond)

1. **Contre-épreuve DOD au banc** : tir `journey` n300 iso-conditions avec
   `journey-mssante-n300-021137` — `send` p50 en baisse, part de `send` en
   baisse, 0 erreur, ~1 connexion SMTP par session. La fuite qui rendait le
   tir non concluant est éteinte ; le tir peut maintenant trancher.
2. **`/sonar 231`** : qualité du diff toujours non mesurée (serveur éteint).
3. **Arbitrage humain** : la réutilisation SMTP vaut ~1/5 de sa promesse sans
   affinité de session (5 réplicas, client par processus) — poursuivre,
   compléter par une affinité, ou re-scoper.

## Merged

- **Date** : 2026-08-05, via `/merge task-231 --i-tested` (attestation humaine HAG)
- **api-mail** : PR #158 squash-mergée → `0b026b1` sur `develop` ; branche distante supprimée, branche locale conservée. Sync develop : merge du chore local `1a5a1c0` (index des rapports de tir, jamais poussé) → `6788b13`, conflit INDEX.md résolu (les deux lignes de tir conservées, doublon du squash dédoublonné).
- **dtos-mss** : aucune PR (branche de précaution sans commit) — branche distante supprimée, clone resynchronisé sur `develop`.
- **CI develop** : run post-merge lancé (https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/31014481875)
- **Staging** : aucune branche `forge/staging-*` — run `/start` isolé, hors batch `/forge`.
- **Note** : la contre-épreuve DOD n300 et `/sonar 231` n'ont pas été rejoués avant merge — l'attestation `--i-tested` de l'humain (HAG, règle 10) couvre la décision. La fuite de threads qui invalidait le tir du 2026-08-05 est corrigée et vérifiée (voir « Fuite corrigée », tir `fuite-fix-bcf86a1`).
