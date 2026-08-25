# todo-task-272.md — L'acquittement d'un envoi n'attend plus l'archivage dans « Envoyés »

**Repos**: api-mail
**Dependencies**: task-269 (recommandée avant : les deux US se partagent le même chemin `send` et la même grille de mesure — les livrer dans cet ordre rend chaque gain attribuable)
**Epic**: E015

## Objectif

L'envoi reste la **seule étape rouge** de la grille SLO au palier 1000
(`Api/Mail/tests/loadtest-k6/reports/2026-08-25/report-journey-1000-solo-postimap-20260825-151054.md`) :
p50 **1 286 ms** pour une cible de 1 000, et **28,2 % du temps serveur** du
palier. La décomposition task-260, confirmée à 1 000 médecins, donne trois
tiers quasi égaux :

| Phase | Moyenne | p95 | Périmètre |
|---|---|---|---|
| `acquire_session` (SMTP) | 457 ms | 599 | **task-269** |
| `smtp_transmit` | 422 ms | 496 | incompressible (MAIL/RCPT/DATA sous ~100 ms de latence MSSanté) |
| `archive_sent` | **407 ms** | 800 | **cette US** |
| `build_mime` | 28 ms | 88 | négligeable |

**Le médecin attend aujourd'hui la copie dans « Envoyés » pour recevoir son
acquittement**, alors que l'envoi est juridiquement fait dès que le serveur
MSSanté a accepté le message (acquittement SMTP). L'archivage est une
conséquence locale de confort : il n'a pas à retenir la réponse.

**Intention métier** : l'acquittement UI est rendu dès l'acceptation SMTP ;
l'archivage vers « Envoyés » s'exécute ensuite, hors du chemin de la réponse,
sur la même session IMAP poolée du praticien (acquis de task-216 — **ne pas**
recréer de voie d'écriture dédiée : task-215/216 ont mesuré qu'une session
d'archivage séparée rendait l'envoi PLUS lent, et l'ont retirée).

**Règle métier de l'échec différé** (à graver, c'est le cœur de l'US) : un
archivage qui échoue après acquittement ne doit **jamais** être silencieux ni
faire échouer l'envoi rétroactivement. Rejeu automatique borné ; en échec
final, trace serveur corrélée (`traceId`) et le message reste retrouvable
(il a été envoyé — l'absence de copie locale est un incident de confort, pas
une perte de donnée de santé).

**Défaut connexe à instruire dans le même geste** : `SemaphoreFullException`
sur `AppendToSent` (mémoire du banc, 2026-08-06) — un envoi **réussi** rendu en
HTTP 500 parce que le verrou de session est relâché par clé et non par
référence. Sortir l'archivage du chemin synchrone supprime ce mode d'échec
visible du médecin ; la cause du double-relâchement doit néanmoins être
établie et corrigée, pas seulement masquée.

**Gain attendu** : ~400 ms sur le p50 de l'acquittement. Combiné à task-269
(~450 ms sur `acquire_session`), le p50 attendu passe sous ~550 ms pour une
cible de 1 000 — l'étape sort du rouge avec de la marge.

**Hors périmètre** : le pooling SMTP (task-269) ; toute voie d'écriture IMAP
dédiée (tranché par task-216) ; le regroupement des allers-retours
d'enrichissement.

## Definition of Done

- [ ] Build passes (0 errors), tests pass (0 failures) sur api-mail
- [ ] La réponse de `POST /sendmail` est rendue dès l'acquittement SMTP :
      test d'intégration prouvant que la latence de réponse n'inclut plus
      l'append IMAP (archivage artificiellement ralenti → réponse inchangée)
- [ ] L'archivage s'exécute après coup sur la session IMAP poolée du
      praticien, sérialisé par le verrou `imap_session` existant — aucun
      nouveau type de session, aucune voie d'écriture dédiée
- [ ] Échec d'archivage : rejeu borné, puis trace `Error` corrélée `traceId`
      sans donnée de santé en clair ; l'envoi reste acquitté — >= 1 test par
      branche (échec transitoire rejoué, échec final tracé)
- [ ] La cause de `SemaphoreFullException` sur `AppendToSent` est établie et
      écrite dans la task, et le double-relâchement corrigé — test unitaire
      reproduisant l'ancien scénario (relâchement par clé vs référence)
- [ ] `SendOperationScope` (task-260) reflète la nouvelle topologie :
      `archive_sent` n'apparaît plus dans le temps synchrone de l'envoi et
      reste mesuré hors chemin (même modèle que l'empreinte sémantique de
      l'enrichissement) — >= 1 test
- [ ] Les erreurs suivent la règle 12 (`ProblemDetails`) — aucun format ad hoc
- [ ] Unit tests pour tout nouveau service/handler (>= 1 par méthode publique)

## Manual Test Plan

- Lancer le banc local : `cd Api/Mail && dotnet run --project src/AppHost --launch-profile https-load-test`
- Seeder : `dotnet run --project tests/mss.mail.loadtest.seed -- --users 5 --messages 10 --api http://127.0.0.1:5052`
- Envoyer un message (`POST /api/v1/mail/sendmail`, identité loadtest-1,
  `Client-Session-Id` stable) : la réponse revient nettement plus vite
  qu'avant (~400 ms de moins) ; quelques secondes plus tard le message est
  visible dans le dossier « Envoyés » (`GET /mail/folders/Sent`)
- Couper Dovecot (arrêt du conteneur) juste après un envoi accepté :
  l'acquittement reste 2xx, Seq porte la trace d'échec d'archivage corrélée,
  aucun 500 rendu au client
- **Au banc (clôture de l'US, non bloquant pour le merge)** : tir journey
  distant iso-conditions avec `report-journey-1000-solo-postimap-20260825` —
  `send` p50 < 1 000 ms, `archive_sent` absent du chemin synchrone dans la
  décomposition

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — optimisation de performance ; le contrat
  fonctionnel « le message envoyé est retrouvable dans Envoyés » est conservé,
  seule sa temporalité devient asynchrone (confort, pas exigence DSR)
- **Exigences DSR honorées** : non applicable — l'émission MSSanté (MIME,
  acquittement SMTP) est inchangée
- **INS** : non applicable — aucun traitement patient modifié
- **Authentification PS** : inchangée (PSC en amont)
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable — le MIME émis est inchangé
- **Tracé PGSSI-S** : l'évènement d'envoi reste journalisé à l'identique ;
  l'échec d'archivage différé produit une trace corrélée sans contenu de
  santé en clair
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — inchangé
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement de données

## Branches
- `api-mail` (pushed) : feat/task-272-async-sent-archive — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-272-async-sent-archive
- `dtos-mss` (pushed, auto-inclus) : feat/task-272-async-sent-archive — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-272-async-sent-archive

## Journal d'implémentation (/develop, 2026-08-25)

- **Réutilisation avant création** : la file `IBackgroundTaskQueue` (task-075 —
  scope DI par travail, exceptions observées centralement) porte l'archivage ;
  l'identité voyage par `CopyIdentityTo` (task-234 — copie complète, le champ
  oublié qui visait une autre base ne peut pas se reproduire). Aucun nouveau
  type de session, aucune voie d'écriture (interdit task-216) : le travail
  différé retrouve la session IMAP poolée par `{Email}_{ClientSessionId}` et
  son verrou `imap_session`.
- **Nouveaux** : `ISentArchiveDispatcher`/`SentArchiveDispatcher` (singleton,
  capture identité par copie + traceId d'Activity, met en file) ;
  `ISentArchiveService`/`SentArchiveService` (scopé, rejeu borné 3 tentatives
  2 s/10 s, échec final LogError + compteur, jamais d'exception hors
  annulation). Métriques : durée publiée hors périmètre sur la série
  `archive_sent` existante (modèle empreinte sémantique task-245) +
  `mssante_send_archive_outcomes_total{outcome}`.
- **Contrat de réponse** : `{ queued, archivePending }` — `archived`/`warning`
  retirés (aucun consommateur : Blazor ne lit que `Queued`/`Message`, vérifié).
  `ApiMessages.MailSentButNotArchived` orphelin retiré (commentaire de renvoi).
  4 tests task-223 du contrat synchrone réécrits en préservant leur intention
  (jamais d'échec d'envoi rétroactif — désormais par construction ; zéro fuite
  — plus aucun canal d'erreur d'archivage dans la réponse).
- **DOD 4 (SemaphoreFullException)** : cause établie — libération par CLÉ
  (`UnLockImapClient(userContext)` → lookup → entrée recyclée → sémaphore neuf
  au plein), **déjà corrigée à la racine par task-223** (`ImapSessionLockHandle`,
  libération par jeton, idempotente) ; couverture vérifiée :
  `SessionLockReleaseMismatchTests` (entrée recyclée, double libération,
  verrou disposé). Sortir l'archivage du chemin supprime en plus toute
  possibilité qu'un résidu de cette famille atteigne le praticien.
- **Validation** : build 0 erreur ; api 685/685 (dont 2 nouveaux tests DOD 1 :
  réponse rendue avec archivage infiniment lent + composition complète du
  travail différé), application 2173/2173 (7 nouveaux SentArchive*), domain
  136, infrastructure 464, intégration 417/433 (16 ignorés Ollama). Flaky
  pré-existant Meter/parallélisme revu une fois (vert au re-run, hors diff).
- **Constaté hors périmètre** : le rejeu offline (`PendingActionService.
  ProcessSendMailAsync`) n'archive PAS dans « Envoyés » — écart pré-existant à
  cette US (le chemin offline n'a jamais archivé), candidat US.

## Simplify log (/forge-simplify, 2026-08-25)

- **Robustesse d'invariant** : `RetryDelays[attempt-1]` supposait
  `Length ≥ MaxAttempts−1` sans le dire — le dernier délai se répète désormais.
- **Altitude** : le `SendOperationScope.Begin()` du contrôleur ne couvrait plus
  que `SmtpService.SendMailAsync`, qui ouvre le même périmètre (task-260) —
  retiré, l'étape « Envoi » est mesurée à un seul endroit.
- Re-validation : build 0 erreur, api 685/685, SentArchive*/SendOperationScope
  14/14. `dtos-mss` non touché (contrat inchangé).

## Sonar log (/sonar, 2026-08-25 — mode chaîné, 2 itérations)

| KPI | Baseline (post-develop) | Final | Cible |
|---|---|---|---|
| Quality Gate | OK | **OK** | OK |
| Bugs / Vulnérabilités | 0 / 0 | **0 / 0** | 0 / 0 |
| Violations new-code | 38 | **37** | best-effort |
| Couverture new-code | 91,3 % | 91,3 % | gate |
| Couverture globale | 88,0 % | 88,0 % | — |

- **Corrigé (it. 2)** : S4457 sur `ArchiveWithRetryAsync` — garde de paramètre
  scindée hors de la machine async (lève à l'appel, pas à l'await).
- **Acceptés (faux positifs, famille documentée en task-269)** : S3604 ×2 sur
  `SentArchiveService` (initialiseurs avec constructeur primaire C# 12).
- **Hors périmètre** : le reste de la new-code period appartient aux lots
  précédents (mêmes items que le Sonar log de task-269).

## Lint log (/lint-angular, 2026-08-25)

- Skip propre : `client-angular` non listé dans **Repos** et non touché.

## Lint mobile log (/lint-mobile, 2026-08-25)

- Skip propre : `client-mobile` non listé dans **Repos** et non touché.

## Visual verify log (/verify-visual, 2026-08-25)

- Skip propre : aucun écran `client-mobile` touché (task backend uniquement).

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/202 — label `awaiting-human-merge`
- `dtos-mss` : aucun commit (pas de changement de contrat) — pas de PR ; branche à supprimer au /merge
- Autres repos : non concernés (US backend seule, justifiée dans le corps)

## Code Review Summary

APPROVED — 11 fichiers, 0 bloquant, 2 suggestions (perte possible de la copie « Envoyés » sur crash processus entre acquittement et exécution de la file — limite assumée par la US ; volume du log Information par envoi). Constaté hors périmètre : le rejeu offline n'archive pas (pré-existant, candidat US).
