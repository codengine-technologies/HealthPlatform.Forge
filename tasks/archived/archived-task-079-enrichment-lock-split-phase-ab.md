# todo-task-079-enrichment-lock-split-phase-ab.md — Perf enrichissement IMAP : séparer le lock fetch (Phase A) de la persistance DB (Phase B)

**Repos**: api-mail
**Dependencies**: —
**Epic**: E011
**EpicTitle**: Performance API Mail

## Objective

Réduire la **contention du lock de session IMAP** pendant l'enrichissement des
mails. Aujourd'hui, dans
[ImapService.cs](Api/Mail/src/Application/Services/Implementation/ImapService.cs),
`EnrichEmailsAsync` acquiert **un seul** lock de session
(`mailClientSessionManager.AcquireLockAsync` avec la clé
`EnrichEmails:{folder}:{pendingUidsHash}`) puis le conserve sur **tout** le
batch : le fetch réseau IMAP des corps/pièces jointes **ET** la persistance DB
(`EnrichSummaryAsync` → `ReadBodyPartAsTextAsync` + `BuildMailDtoAsync` +
upsert `MailRepository.AddNewMail`).

**Conséquence** : pendant qu'un batch d'enrichissement (potentiellement long —
N mails × fetch + DB) tient le lock, les opérations IMAP **courtes** de la même
session (`GetFolders`, `GetFolderStatus`, requêtes de dossier déclenchées par
l'UI) sont bloquées derrière lui. L'utilisateur perçoit une latence pendant les
synchronisations.

### Origine — WIP stash à ré-implémenter

Cette optimisation a été prototypée le 2026-06-04 dans un stash orphelin
(laissé par erreur sur la branche supprimée `chore/task-055-…`, sans rapport
avec ProblemDetails). Le stash **ne se re-pop pas proprement** : `develop` a
divergé depuis (task-068 fetch ciblé, fix leak sémaphore #88). Il faut donc
**ré-implémenter l'idée** proprement sur `develop` actuel, pas faire un
`git stash pop`.

Référence du prototype (read-only, pour inspiration) :
- stash commit : `25efd481a1cd622e9d1eaf60c1e3926c84da854a`
- base du stash : `2b5a85c781b182133c6362235c482468e9779f65`
- inspection : `git diff 2b5a85c7 25efd481 -- src/Application/Services/Implementation/ImapService.cs`

Une fois cette task mergée, **dropper le stash** (`git stash drop "stash@{0}"`).

## Cible

Découper `EnrichEmailsAsync` en deux phases distinctes :

1. **Phase A — fetch IMAP sous le lock de session.** Acquérir
   `AcquireLockAsync` uniquement le temps des I/O réseau IMAP (récupération des
   summaries + lecture des body-parts / pièces jointes), matérialiser le
   résultat en mémoire (liste de `FetchedMail` / structure équivalente), fermer
   le dossier, **puis relâcher le lock IMAP**.
2. **Phase B — persistance + notifications HORS du lock IMAP.** Itérer sur le
   résultat matérialisé pour construire les DTOs et faire l'upsert DB
   (`MailRepository.AddNewMail` / `UpdateExistingMailWithContentAsync`) +
   notifications client, **en dehors** du lock de session, afin que les
   opérations IMAP courtes de la même session ne soient plus bloquées par le
   travail DB.

### Garde-fou anti-race (obligatoire)

Le lock IMAP unique actuel protège **aussi** contre la race
`DbUpdateConcurrencyException` sur l'upsert par-UID (deux passes d'enrichissement
concurrentes sur le même set d'UIDs — cf. le commentaire `pendingUidsHash` dans
le code actuel). Relâcher le lock IMAP avant la persistance **réintroduirait**
cette race. La Phase B **doit donc être sérialisée par un lock dédié**
(de granularité `email + folderPath`), distinct du lock IMAP, afin de :
- sérialiser les persistances concurrentes du même couple mailbox+folder
  (préserver la protection anti-`DbUpdateConcurrencyException`) ;
- **sans** re-bloquer les lectures IMAP courtes de la session.

Le prototype ajoutait à cet effet `LockEnrichPersistAsync(email, folderPath, ct)`
/ `UnlockEnrichPersist(email, folderPath)` sur `IMailClientSessionManager` /
`MailClientSessionManager`. Reprendre cette approche (ou un `SemaphoreSlim` par
clé équivalent) — au choix de l'implémentation, tant que la sérialisation
per-(email, folder) est garantie et que le lock est **libéré dans un `finally`**
(pas de fuite, cf. fix #88).

### Hors périmètre

- Ne pas modifier les autres sites `AcquireLockAsync` du fichier
  (`GetFolders`, sync, etc.) — règle 6, scopes isolés.
- Pas de changement de contrat DTO ni d'impact frontend.
- Pas de migration de schéma.

## Gherkin

_Pas de `.feature` (BDD déprécié, cf. CLAUDE.md règle 1). Comportement de
concurrence couvert par tests unitaires sur `MailClientSessionManager`
(lock persist) + tests sur `ImapService` (séparation Phase A/B)._

## Definition of Done

- [x] Build passes (`dotnet build HealthPlatform.Api.Mail.sln`, 0 erreurs)
- [x] Tests pass (`dotnet test HealthPlatform.Api.Mail.sln`, 0 échecs hors
      rouges pré-existants documentés)
- [x] `EnrichEmailsAsync` relâche le lock de session IMAP **avant** la phase de
      persistance DB (vérifiable par lecture : le `await using lockScope` IMAP
      n'englobe plus l'upsert `MailRepository.AddNewMail`)
- [x] Un lock de persistance dédié, sérialisé par `(email, folderPath)`,
      protège la Phase B contre les passes concurrentes — libéré dans un
      `finally` (pas de fuite de sémaphore)
- [x] **Tests unitaires `MailClientSessionManager` (≥1 par méthode/branche)** :
      - [x] le lock persist sérialise deux acquisitions concurrentes du même
            `(email, folder)` (la 2ᵉ attend la 1ʳᵉ)
      - [x] deux `(email, folder)` différents ne se bloquent pas mutuellement
      - [x] `Unlock…` libère bien le lock (réacquisition immédiate possible)
      - [x] le lock persist n'est **pas** le même que le lock IMAP de session
            (une op IMAP courte n'est pas bloquée par un persist en cours)
- [x] **Tests unitaires `ImapService.EnrichEmailsAsync`** : la persistance
      s'exécute hors du lock IMAP (ordre fetch-sous-lock → release → persist),
      et l'annulation (`OperationCanceledException`) est gérée dans chaque phase
- [x] Aucune régression sur l'enrichissement : la suite `ImapServiceTests`
      existante reste verte (contenu enrichi, notifications incrémentales,
      skip du premier massive-sync, dossiers virtuels `tag:` ignorés)
- [x] Le stash prototype est droppé après merge (note dans la PR)

## Manual Test Plan

- Lancer le backend via l'AppHost Aspire :
  `cd Api/Mail/src/AppHost && dotnet run`.
- Avec un compte MSSanté de test possédant un dossier volumineux non encore
  enrichi, déclencher une synchronisation incrémentale (ouvrir le dossier dans
  l'UI).
- **Pendant** l'enrichissement (logs `Starting enrichment for …`), naviguer
  vers un autre dossier / rafraîchir la liste des dossiers : vérifier que ces
  opérations IMAP courtes **répondent sans attendre** la fin du batch
  d'enrichissement (avant le fix, elles étaient bloquées).
- Vérifier dans Seq qu'**aucune** `DbUpdateConcurrencyException` n'apparaît en
  déclenchant deux synchronisations rapprochées du même dossier (la
  sérialisation Phase B doit toujours prévenir la race).
- Vérifier que tous les mails du dossier sont bien enrichis (corps + pièces
  jointes présents, pas de placeholder `Pending` résiduel).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville — optimisation de performance interne
  du flux de réception MSSanté, aucun changement fonctionnel visible métier.
- **Vague Ségur** : V2 — perf/robustesse d'un comportement déjà couvert
  (réception et enrichissement des mails), aucune exigence nouvelle.
- **Exigences DSR honorées** : aucune nouvelle — préserve le flux
  d'enrichissement existant (E011 Performance API Mail).
- **INS** : non manipulée directement par cette task (l'enrichissement
  persiste des mails dont certains portent une INS, comportement inchangé) ;
  les tests utilisent exclusivement des **données factices**.
- **Authentification PS** : inchangée.
- **Habilitations** : non applicable.
- **Interop CI-SIS** : non applicable — aucun échange CDA/FHIR modifié.
- **Tracé PGSSI-S** : inchangé — aucun évènement ajouté ni retiré.
- **Consentement patient** : non applicable — réception, pas d'émission.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : oui — environnement existant ; améliore la réactivité
  d'un traitement de données de santé sans en changer la sémantique.
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement, simple
  réorganisation du verrouillage interne.

### DOD santé (items applicables)
- [x] Aucune INS réelle dans les fixtures de test (données factices uniquement)
- [x] Aucune donnée de santé réelle dans les logs ajoutés (clés de lock =
      email + dossier, pas de contenu de mail)

## Branches
- `api-mail` (pushed) : feat/task-079-enrichment-lock-split-phase-ab — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-079-enrichment-lock-split-phase-ab
- `dtos-mss` (pushed, auto-included) : feat/task-079-enrichment-lock-split-phase-ab — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-079-enrichment-lock-split-phase-ab

## Develop log

- Repos touched : api-mail (dtos-mss : branche auto-incluse, 0 commit, pas de PR)
- DTOs / Interop published : no change
- Commits :
  - api-mail : e9ac0e7 feat(imap): split enrichment into IMAP-fetch and DB-persist phases
- Local build / test : ✓ Release 0 erreur ; suite verte hors 2 flaky pré-existants documentés (MailExport PDF, IMAP cancel) — le rouge middleware passe même sur ce run
- Implementation notes :
  - Ré-implémentation propre du prototype (stash orphelin `25efd481`, inspecté en read-only) sur develop actuel — pas de `stash pop`
  - **Phase A** : le lock IMAP de session (`AcquireLockAsync`, clé `EnrichEmails:{folder}:{pendingUidsHash}` inchangée) ne couvre plus que les I/O réseau (summaries + body parts + zips IHE-XDM, matérialisés en record privé `FetchedMail`), fermeture du dossier, release par sortie du scope `await using` — désormais DANS le try de Phase A
  - **Phase B** (`PersistEnrichedBatchAsync`) : build DTO + upsert par-UID + audit + notifications HORS lock IMAP, sérialisée par le nouveau lock dédié `LockEnrichPersistAsync(email, folder)` (clé `enrich:{email}:{folder}`, timeout 3 min, miroir des fetch locks) — préserve la garantie anti-`DbUpdateConcurrencyException` ; release dans un `finally` (cf. #88)
  - `_enrichPersistLocks` intégré au contrat anti-fuite task-058 : `CleanupLocksForSession` récupère les locks `enrich:` quand la dernière session de l'email disparaît ; compteur interne `EnrichPersistLockCount` pour les tests
  - Annulation par phase : OCE en Phase A → log + return (jamais de persist) ; OCE en Phase B → log + release du lock
  - Hors périmètre respecté : aucun autre site `AcquireLockAsync` modifié, pas de changement DTO ni schéma
  - Tests : 11 nouveaux test-first (RED compile → GREEN) — sérialisation même (email, folder), indépendance entre dossiers ET vis-à-vis du lock IMAP de session, release/réacquisition, unlock sans lock, reclaim au RemoveSession ; ordre Unlock IMAP → Lock persist (Received.InOrder), pas de persist lock sans résultat fetch, annulation Phase A, release en finally sur échec DB
- DOD self-check : 8/8 vérifiables OK + DOD santé 2/2 (données factices, clés de lock = email+dossier) ; item « stash droppé après merge » → différé au /merge (noté pour la PR)
- no angular change → skipped /lint-angular
- Next step : /sonar task-079 (chaîne ensuite vers /review)

## Sonar log

- Phase 1 (new code) : ✓ après 2 commits de fix — Quality Gate **OK**, 0 violation, 0 hotspot, new_coverage 83.2% ≥ 80
  - Issues new-code fixées : S3776 (complexité 16 → sous le seuil : extraction `ComputePendingEnrichmentAsync` — fix manuel privilégié, pas de halt /sonar-s3776 car la complexité venait du code de la task elle-même, fraîchement testé), S103 (ligne 163 chars dans `IImapService` héritée du merge task-068, wrappée), S125 (commentaire en prose pris pour du code — reformulé)
  - Les ~165 lignes « new » non couvertes restantes d'`ImapService` appartiennent au diff task-068 (PR #90, mergée par l'humain hors session) — hors périmètre task-079 (règle 6)
- Phase 2 (legacy) : 0 itération / 5 — early-stop, dette nulle (0 bug, 0 vuln, 0 smell, ratings A/A/A, coverage projet 84.2%)
- Build / tests : ✓ Release green (1 seul échec = IMAP cancel flaky documenté ; middleware et PDF verts sur ces runs)
- no angular change → skipped /lint-angular
- Hand-off : /review task-079

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/91 — label `awaiting-human-merge`
- `dtos-mss` : aucune PR — branche auto-incluse, 0 commit

## Code Review Summary

**Verdict : APPROVED** (6 fichiers revus, 2 suggestions non-bloquantes, 0 bloquant)

- `src/Application/Services/Implementation/ImapService.cs` — ✅ découpage Phase A/B fidèle à la cible : lock IMAP limité aux I/O réseau (release par sortie du scope `await using` dans le try de Phase A), persistance hors lock IMAP sous lock dédié finally-released ; sémantique d'erreur par-mail et ordre des notifications conservés ; pré-vol extrait (`ComputePendingEnrichmentAsync`, fix S3776) ; aucun autre site `AcquireLockAsync` touché (règle 6)
- `src/Application/Session/MailClientSessionManager.cs` + interface — ✅ `LockEnrichPersistAsync`/`UnlockEnrichPersist` miroir des fetch locks (clé `enrich:{email}:{folder}`, timeout 3 min), intégré au contrat anti-fuite task-058 (`CleanupLocksForSession` + compteur interne)
- Tests — ✅ 11 nouveaux significatifs : `Received.InOrder` prouvant Unlock IMAP → Lock persist, indépendance des deux locks, annulation par phase, release en finally sur échec DB
- ⚠️ suggestions : matérialisation du batch complet en mémoire (prescrite par la US — chunking envisageable en follow-up si les syncs massives grossissent) ; TOCTOU hérité task-058 sur le reclaim des locks partagés

Validation : build ✓ Release 0 erreur · tests ✓ (1 échec = IMAP flaky documenté) · DOD ✓ 8/8 + santé 2/2 (item « stash droppé » différé au /merge) · Sonar ✓ Quality Gate OK, 0 issue new-code (3 fixées au fil de l'eau), coverage projet 84.2%

## Merged

- Date : 2026-06-10
- `api-mail` : squash commit `9681356` (PR #91 closed, branche remote supprimée, branche locale conservée)
- `dtos-mss` : aucune PR (branche vide) — remote supprimée, clone resynchronisé sur `develop`
- **Stash prototype droppé** : `stash@{0}` (`25efd481`) — exigence DOD honorée, plus aucun stash dans le repo
- develop CI : ✓ success — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/27292557290
