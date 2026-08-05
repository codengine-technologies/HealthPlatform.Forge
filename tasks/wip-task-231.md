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
