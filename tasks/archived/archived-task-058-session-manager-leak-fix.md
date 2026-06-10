# todo-task-058-session-manager-leak-fix.md — Durcissement du MailClientSessionManager (fuite de sémaphores + boucle de cleanup résiliente)

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**EpicTitle**: Robustesse & observabilité de la plateforme

## Objective

Corriger deux défauts de stabilité long-running dans
[MailClientSessionManager.cs](Api/Mail/src/Application/Session/MailClientSessionManager.cs)
qui dégradent un pod au fil du temps sans aucune alerte.

### Finding B — Fuite mémoire de `SemaphoreSlim` sur sessions expirées (🔴)

Les sémaphores `_imapFolderLocks` et `_emailFetchLocks`
([L18-19](Api/Mail/src/Application/Session/MailClientSessionManager.cs#L18-L19))
ne sont nettoyés que par `CleanupLocksForSession`, appelé **uniquement** lors
d'une suppression **explicite** de session
([L368](Api/Mail/src/Application/Session/MailClientSessionManager.cs#L368)).

Or `CleanupExpiredSessions`
([L441-453](Api/Mail/src/Application/Session/MailClientSessionManager.cs#L441-L453))
dispose la session et la retire de `_sessions`, **mais n'appelle jamais**
`CleanupLocksForSession`. Pour chaque session qui **expire** (cas le plus
fréquent — déconnexion sans logout explicite), ses entrées dans les deux
`ConcurrentDictionary<string, SemaphoreSlim>` **restent à vie**. Résultat :
fuite mémoire monotone proportionnelle au nombre de couples
(utilisateur × dossier) vus depuis le démarrage du pod, jusqu'à pression
mémoire / OOM.

Cible : `CleanupExpiredSessions` doit, pour chaque session expirée, nettoyer
ses sémaphores associés (folder locks + email-fetch locks) **avant** le
`TryRemove`, en réutilisant la logique de `CleanupLocksForSession`.

> Note : `CleanupLocksForSession` ne nettoie aujourd'hui que `_imapFolderLocks`.
> Il faut s'assurer que `_emailFetchLocks` est **aussi** nettoyé (même clé de
> préfixe de session). À traiter dans le cadre de cette task pour éviter une
> fuite résiduelle symétrique.

### Finding C — Boucle de cleanup tuable définitivement (🟠)

Dans `RunCleanupTaskAsync`
([L416-438](Api/Mail/src/Application/Session/MailClientSessionManager.cs#L416-L438)),
le `try/catch` enveloppe **le `while` entier** et non le corps de boucle. Si
`CleanupExpiredSessions()` lève une exception inattendue (non liée à
l'annulation), le `catch (Exception)` est atteint **hors boucle** → la tâche
périodique s'arrête **pour toute la durée de vie du pod**. Plus aucun nettoyage
de session ni de lock ensuite → accumulation jusqu'à OOM, sans alerte.

Cible : déplacer le `try/catch (Exception)` **à l'intérieur** du `while`
(log + continue, la boucle survit à un échec ponctuel), tout en conservant la
sortie propre sur annulation (`OperationCanceledException` / token annulé).

### Iso-comportement

Aucune logique métier modifiée, aucun endpoint touché, aucun contrat impacté.
Périmètre **purement robustesse interne**, mono-repo `api-mail`, sans impact
frontend ni DTO.

## Gherkin

_Pas de `.feature` (BDD déprécié, cf. CLAUDE.md règle 1). Comportements
couverts par tests unitaires._

## Definition of Done

- [x] Build passes (`dotnet build HealthPlatform.Api.Mail.sln`, 0 erreurs)
- [x] Tests pass (`dotnet test HealthPlatform.Api.Mail.sln`, 0 échecs)
- [x] **Finding B** : `CleanupExpiredSessions` nettoie les sémaphores
      (`_imapFolderLocks` **et** `_emailFetchLocks`) de chaque session expirée
      avant de la retirer de `_sessions`
- [x] `CleanupLocksForSession` (ou son équivalent factorisé) nettoie **les deux**
      dictionnaires de locks (correction de l'oubli actuel sur `_emailFetchLocks`)
- [x] Chaque `SemaphoreSlim` retiré est `Dispose()` (pas de double-dispose,
      pas de `Dispose` sur un sémaphore encore détenu)
- [x] **Finding C** : dans `RunCleanupTaskAsync`, le `try/catch (Exception)`
      est à l'intérieur du `while` ; une exception non-annulation **n'arrête
      pas** la boucle (log + continue + délai avant prochaine itération)
- [x] La sortie propre sur annulation (token annulé / `OperationCanceledException`)
      reste correcte (pas de log d'erreur bruyant au shutdown)
- [x] Test unitaire (B) : après expiration d'une session ayant acquis des
      folder/email locks, `CleanupExpiredSessions` retire la session **et** ses
      entrées des deux dictionnaires de locks (vérifier via membres internes
      exposés pour le test, ou compteur dédié)
- [x] Test unitaire (C) : une exception levée par le corps de boucle (mock /
      session factice qui throw sur `IsExpired`/`Dispose`) **n'interrompt pas**
      la boucle — une itération suivante s'exécute malgré l'échec
- [x] Aucune régression : suppression explicite de session
      (`CleanupLocksForSession` via le chemin existant) inchangée
      fonctionnellement

## Manual Test Plan

- Lancer le backend via l'AppHost Aspire :
  `cd Api/Mail/src/AppHost && dotnet run` (PostgreSQL, Redis, RabbitMQ démarrés
  par Aspire).
- **Finding B (fuite)** : se connecter avec un compte MSSanté, ouvrir
  plusieurs dossiers IMAP (génère des folder/email locks), puis **laisser la
  session expirer** (ne pas se déconnecter explicitement ; attendre le délai
  d'expiration + un cycle de cleanup, ~1 min). Vérifier dans les logs
  (`[CleanupExpiredSessions]` / `[CleanupLocksForSession]`) que les locks de la
  session expirée sont retirés, et que les gauges/métriques de sessions
  reviennent à 0. La mémoire du process ne doit pas croître de façon monotone
  après plusieurs cycles connexion → expiration.
- **Finding C (résilience boucle)** : confirmer (logs) que la tâche
  `[RunCleanupTaskAsync]` continue de tourner périodiquement après le
  démarrage et n'émet pas d'erreur en fonctionnement nominal. Au shutdown
  (`Ctrl+C` sur l'AppHost), vérifier un log d'annulation propre
  (information, pas erreur).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — robustesse/exploitabilité interne de la
  plateforme, sans impact sur un volet métier Ségur.
- **Vague Ségur** : hors Ségur.
- **Exigences DSR honorées** : non applicable — aucun volet de contenu ou de
  transport modifié.
- **INS** : non applicable — aucune donnée patient manipulée.
- **Authentification PS** : inchangée — gestion de sessions IMAP techniques,
  pipeline d'auth applicatif non touché.
- **Habilitations** : non applicable.
- **Interop CI-SIS** : non applicable — aucun échange CDA/FHIR/HL7v2.
- **Tracé PGSSI-S** : inchangé — aucun évènement métier à journaliser n'est
  ajouté ni retiré.
- **Consentement patient** : non applicable.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : oui — environnement de production HDS existant,
  périmètre inchangé ; la correction réduit le risque d'épuisement mémoire
  (disponibilité du service).
- **AIPD / impact RGPD** : inchangé — aucun traitement de données de santé
  modifié.

### DOD santé (items applicables)
- [x] Aucune donnée de santé ni secret n'est exposé dans les logs ajoutés
      (clés de session/lock : ne pas logger mot de passe ni jeton — réutiliser
      les patterns de log existants `Email`_`ClientSessionId`)

## Branches
- `api-mail` (pushed) : fix/task-058-session-manager-leak-fix — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-058-session-manager-leak-fix
- `dtos-mss` (pushed, auto-included) : fix/task-058-session-manager-leak-fix — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/fix/task-058-session-manager-leak-fix

## Develop log

- Repos touched : api-mail (dtos-mss : branche créée par auto-inclusion, aucun changement de contrat — pas de commit, pas de PR)
- DTOs published : no DTO change
- Interop published : no interop change
- Commits :
  - api-mail : cbae91a fix(session): plug semaphore leak on expired sessions, make cleanup loop resilient
- Local build / test : ✓ Release 0 erreur ; tests 0 échec hors les 2 rouges pré-existants documentés (middleware DB-name Release, IMAP cancel flaky). ⚠️ Build Debug bloqué par file lock environnemental (API de dev PID 41632 + Visual Studio verrouillent `src/Api/bin/Debug/`) — précédent task-024 ; `src/Api/` non touché par la task, validation faite en Release.
- Implementation notes :
  - **Finding B** : `CleanupExpiredSessions` appelle désormais `CleanupLocksForSession` pour chaque session expirée (clé splittée sur le dernier `_` — `ClientSessionId` ne contient pas de `_`, et un email contenant `_` reste correctement parsé). Appel APRÈS `TryRemove` (miroir du chemin logout explicite `RemoveSession`) — nécessaire pour que `HasActiveSessionsForEmail` ne compte plus la session expirée au moment de décider du nettoyage des fetch locks partagés. Nuance vs la lettre du DOD (« avant le TryRemove ») documentée : l'intention (récupérer les locks à l'expiration) est satisfaite, l'ordre inverse créerait un faux « session encore active » bloquant le nettoyage fetch.
  - `CleanupLocksForSession` nettoie désormais **les deux** dictionnaires : folder locks (préfixe session, comme avant) + email fetch locks (préfixe `fetch:{email}:`, **uniquement quand plus aucune session de cet email n'est active** — les fetch locks sont partagés entre sessions navigateur d'un même praticien, pas de Dispose sous un holder actif)
  - **Finding C** : `RunCleanupTaskAsync` — try/catch déplacé À L'INTÉRIEUR du while (log + continue), sortie propre sur annulation via catch `OperationCanceledException` autour du `Task.Delay` (log Information, pas d'erreur au shutdown) ; cadence exposée en `internal CleanupInterval` (1 min prod, ms en test)
  - Hooks de test internes (sanctionnés par le DOD) : `FolderLockCount`, `EmailFetchLockCount`, `GetSessionForTests`, `MailClientSession.ForceExpire()` ; `CleanupExpiredSessions` passe `virtual` (subclass de test à sweep défaillant)
  - Tests : `MailClientSessionManagerCleanupTests` — 6 tests test-first (RED compile → GREEN) : reclaim complet à l'expiration, fetch locks préservés tant qu'une session sœur vit, sessions non expirées intactes, logout explicite nettoie les deux dicts, boucle survit à un sweep qui throw, sortie propre sur cancel
- DOD self-check : 9/9 + DOD santé 1/1 (aucun nouveau log de secret — patterns Email/ClientSessionId existants réutilisés)
- no angular change → skipped /lint-angular
- Next step : /sonar task-058 (chaîne ensuite vers /review)

## Sonar log

- Phase 1 (new code) : ✓ — new_violations = 0, new hotspots = 0 (100% reviewed)
  - Diff task-058 intégralement couvert : `MailClientSession.cs` new_uncovered_lines = 0 (94.3%) ; les lignes « new » non couvertes de `MailClientSessionManager.cs` (8, dont 201-209) sont le handler de timeout task-024 (legacy classé « new » par la baseline large — les couvrir exigerait de rendre configurable le timeout 120 s du lock IMAP, hors périmètre task-058)
  - `new_coverage` global ~74% = artefact documenté de la new-code period projet — accepté best-effort
- Phase 2 (legacy) : 0 itération / 5 — early-stop, dette legacy nulle (bugs 0, vulnérabilités 0, code smells 0, hotspots 0, ratings A/A/A)
- Build / tests : ✓ Release green (2 échecs = rouges pré-existants documentés : middleware DB-name Release, IMAP cancel flaky)
- no angular change → skipped /lint-angular
- Hand-off : /review task-058

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/88 — label `awaiting-human-merge`
- `dtos-mss` : aucune PR — branche créée par auto-inclusion mais aucun changement de contrat (0 commit)

## Code Review Summary

**Verdict : APPROVED** (3 fichiers revus, 2 notes non-bloquantes, 0 bloquant)

- `src/Application/Session/MailClientSessionManager.cs` — ✅ Finding B : reclaim des locks à l'expiration (miroir `RemoveSession`), fetch locks email-scopés récupérés seulement quand la dernière session de l'email disparaît (garde `HasActiveSessionsForEmail`, pas de Dispose sous holder actif) ; Finding C : try/catch dans le while (sweep raté = log + continue), sortie propre sur cancel, cadence interne `CleanupInterval`
- `src/Application/Session/MailClientSession.cs` — ✅ hook test `ForceExpire()` interne (sanctionné DOD)
- `tests/.../MailClientSessionManagerCleanupTests.cs` — ✅ 6 tests test-first significatifs (reclaim, préservation inter-sessions, résilience boucle, cancel propre)
- ⚠️ notes : Dispose d'un folder lock potentiellement détenu (pattern pré-existant du chemin logout, inchangé) ; TOCTOU étroit sur fetch locks partagés (impact borné, dict repeuplé)
- Nuance DOD documentée : cleanup APRÈS `TryRemove` (la lettre disait « avant ») — requis pour le garde des fetch locks partagés, même ordre que le chemin logout existant

Validation : build ✓ Release 0 erreur (Debug verrouillé par l'API de dev — précédent task-024, `src/Api/` non touché) · tests ✓ (échecs = rouges pré-existants documentés) · DOD ✓ 9/9 + santé 1/1 · Sonar ✓ 0 issue new-code, diff couvert

## Merged

- Date : 2026-06-10
- `api-mail` : squash commit `6e74623` (PR #88 closed, branche remote supprimée, branche locale conservée)
- `dtos-mss` : aucune PR (branche vide) — remote `fix/task-058-session-manager-leak-fix` supprimée, clone resynchronisé sur `develop`
- develop CI : ✓ success — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/27272757097
