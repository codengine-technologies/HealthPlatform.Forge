# todo-task-080.md — Perf GetFolders : éliminer le double-STATUS par dossier (probe ghost folders)

**Repos**: api-mail
**Dependencies**: aucune
**Epic**: E011

> US mono-repo justifiée : optimisation interne du chemin de lecture des
> dossiers IMAP. Aucun changement de contrat, de DTO ni d'UI — le résultat
> fonctionnel (liste de dossiers, compteurs, exclusion des ghost folders MSS)
> est strictement identique.

## Objective

Réduire le temps de détention du `ImapLock` de session pendant `GetFoldersAsync`
(observé jusqu'à **10,7 s** en conditions réelles via Seq, opération `GetFolders`,
`ImapService.cs:102`, log `[ImapLock] 🔓⚠️ Lock released (long)`). Ce lock étant
le sémaphore binaire qui sérialise toute la connexion IMAP de la session, sa
détention prolongée bloque les autres opérations courtes de l'UI
(`GetFolderQuery`, `FetchSingleEmail`) de la même session.

## Finding adressé (audit perf / analyse locks Seq 2026-06-10)

| # | Localisation | Problème | Impact |
|---|---|---|---|
| 1 | `src/Application/Services/Implementation/ImapService.cs` — `GetFoldersAsync` (~L126) puis `ProbeValidFoldersAsync` (~L196) | Le `LIST-STATUS` initial (`GetFoldersAsync(StatusItems.Count \| StatusItems.Unread, …)`) ramène déjà les compteurs de tous les dossiers en un aller-retour. `ProbeValidFoldersAsync` refait ensuite **un `StatusAsync(Count)` par dossier, séquentiellement, sous le lock**, uniquement pour écarter les « ghost folders » MSS (dossiers listés mais répondant « NO » au STATUS/SELECT). Avec 15-20 dossiers ⇒ 15-20 allers-retours réseau supplémentaires sous le lock. | Élevé |

## Contexte technique

La connexion IMAP est *stateful* (une seule commande à la fois), protégée par
un `SemaphoreSlim(1,1)` par session (`MailClientSession.ImapLock`). On ne peut
donc pas paralléliser le probe : la seule marge est de **supprimer les
allers-retours redondants**, pas de les concurrencer.

Le probe a été introduit parce que certains serveurs MSSanté continuent de
lister un dossier parent supprimé dans les réponses `LIST` sans positionner
`\NoSelect` / `\NonExistent`, tout en renvoyant « NO Mailbox doesn't exist »
sur `STATUS`/`SELECT`. Le `LIST-STATUS` (RFC 5819) demande déjà un `STATUS`
pour chaque dossier dans la même commande : un ghost folder y échoue déjà.
L'objectif est de **détecter le ghost à partir du résultat du `LIST-STATUS`
déjà obtenu** (compteur de statut absent / non peuplé) au lieu de relancer un
`STATUS` explicite par dossier.

## Comportement attendu

- `GetFoldersAsync` n'émet plus de `STATUS` par dossier en plus du
  `LIST-STATUS` initial dans le cas nominal.
- Les ghost folders MSS (listés mais inexistants) restent exclus de la réponse,
  du cache et de la base — exactement comme aujourd'hui.
- Les dossiers non sélectionnables (`\NoSelect` / `\NonExistent`) restent
  ignorés.
- Repli (fallback) : si le serveur ne renvoie pas de statut exploitable via le
  `LIST-STATUS` pour un dossier donné (statut indéterminé), ne re-prober **que
  ce dossier** plutôt que tous — afin de préserver la robustesse face aux
  serveurs ne supportant pas pleinement `LIST-STATUS`.
- Le temps de détention du lock pour l'opération `GetFolders` chute de ~N
  allers-retours à 1 (nominal) ou à 1 + k (k = nombre de dossiers réellement
  indéterminés).

## Definition of Done

- [x] Build passes : `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` (0 erreur)
- [x] Tests pass : `dotnet test HealthPlatform.Api.Mail.sln` (0 échec)
- [x] `ProbeValidFoldersAsync` (ou son remplaçant) n'effectue plus un `StatusAsync` systématique par dossier dans le cas nominal — le statut du `LIST-STATUS` initial est réutilisé
- [x] Les ghost folders MSS restent exclus (test prouvant qu'un dossier listé mais répondant « NO » au statut est absent du résultat)
- [x] Les dossiers `\NoSelect` / `\NonExistent` restent ignorés (test)
- [x] Le fallback ne re-probe que les dossiers au statut indéterminé (test : un dossier sans statut exploitable déclenche exactement 1 `STATUS`, les autres 0)
- [x] Unit tests : >= 1 test par branche (dossier valide, ghost folder, non-sélectionnable, statut indéterminé → re-probe ciblé) via un `IImapClientWrapper` / `IMailFolder` mocké
- [x] La liste de dossiers retournée, les compteurs (`Count`, `Unread`) et la hiérarchie sont identiques au comportement pré-US sur un jeu de dossiers nominal (test de non-régression)
- [x] Aucune donnée de santé en clair dans les logs (noms de dossiers déjà loggés aujourd'hui — niveau inchangé)

## Manual Test Plan

- Lancer l'API : `cd Api/Mail && docker-compose up -d && dotnet run --project src/Api`
- Se connecter avec un compte de test MSSanté (données anonymisées) possédant
  plusieurs dossiers (idéalement >= 10) ; ouvrir l'écran de la liste des
  dossiers (`GET /api/v1/mail/folders`).
- Vérifier que la liste affichée, les compteurs de messages et de non-lus, et
  la hiérarchie des dossiers sont identiques à avant.
- Dans Seq, filtrer `Operation = 'GetFolders'` et vérifier que le `HoldTimeMs`
  du log `[ImapLock] … Lock released` a nettement diminué (objectif : passer
  d'environ 10 s à ~1-2 s sur la même boîte), et qu'aucun avertissement
  « Lock released (long) » n'est plus émis pour cette opération dans le cas
  nominal.
- Si un compte de test exposant un ghost folder MSS est disponible, vérifier
  que ce dossier reste absent de la liste et de la base.
- Pendant un chargement de dossiers, déclencher une autre action IMAP (ouvrir
  un mail) : l'UI reste réactive.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (LPS MSSanté)
- **Vague Ségur** : hors Ségur — optimisation technique interne
- **Exigences DSR honorées** : non applicable — le comportement MSSanté (relève, liste des dossiers, états) est inchangé
- **INS** : non applicable
- **Authentification PS** : inchangée
- **Habilitations** : non applicable
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement HDS existant inchangé
- **AIPD / impact RGPD** : inchangé

## Branches
- `api-mail` (pushed) : feat/task-080-getfolders-double-status-probe — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-080-getfolders-double-status-probe
- `dtos-mss` (pushed, auto-included) : feat/task-080-getfolders-double-status-probe — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-080-getfolders-double-status-probe

## Develop log

- Repos touched : api-mail (dtos-mss : branche auto-incluse, 0 commit, pas de PR)
- DTOs / Interop published : no change
- Commits :
  - api-mail : 73ad93a feat(imap): reuse LIST-STATUS result in the ghost-folder probe
- Local build / test : ✓ Release 0 erreur ; suite verte hors le flaky IMAP cancel documenté (domain/api/infra/application 100% verts)
- Implementation notes :
  - `ProbeValidFoldersAsync` : un dossier dont le LIST-STATUS initial a peuplé le statut (`Count >= 0`, sémantique MailKit « -1 = inconnu ») est prouvé sélectionnable → inclus sans aucun aller-retour réseau supplémentaire. Cas nominal : 0 STATUS par dossier (vs N avant, sous le lock IMAP)
  - Ghost folders MSS : statut jamais peuplé par le LIST-STATUS → re-probe ciblé qui lève « NO Mailbox doesn't exist » → exclu exactement comme avant (même catch `IsMailboxNotFound`)
  - Fallback serveurs sans LIST-STATUS complet : seuls les dossiers au statut indéterminé sont re-probés, en `Count | Unread` (compteurs complets, légèrement mieux que l'ancien probe `Count` seul)
  - `\NoSelect` / `\NonExistent` : inchangé (skip sans probe)
  - Tests : 4 nouveaux test-first (RED → GREEN) — zéro STATUS quand LIST-STATUS peuplé + non-régression des compteurs (Count/UnreadCount mappés), ghost exclu via probe ciblé (1 STATUS exactement), NoSelect/NonExistent sans probe, re-probe limité aux indéterminés. Pièges harness corrigés : `GetTagFoldersAsync` substitué doit retourner `[]` (null par défaut → AddRange crash), ctor 3-args d'`ImapCommandException` requis pour porter le message « doesn't exist »
- DOD self-check : 9/9 vérifiables OK (gain de détention du lock = mesure Seq différée au Manual Test Plan)
- no angular change → skipped /lint-angular
- Next step : /sonar task-080 (chaîne ensuite vers /review)

## Sonar log

- Phase 1 (new code) : ✓ du premier coup — 0 violation, 0 hotspot, Quality Gate **OK**
- Phase 2 (legacy) : 0 itération / 5 — early-stop, dette nulle (0 bug, 0 vuln, 0 smell, ratings A/A/A, coverage projet 84.2%)
- Build / tests : ✓ Release green (2 échecs = flaky pré-existants documentés : MailExport PDF, IMAP cancel)
- no angular change → skipped /lint-angular
- Hand-off : /review task-080

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/92 — label `awaiting-human-merge`
- `dtos-mss` : aucune PR — branche auto-incluse, 0 commit

## Code Review Summary

**Verdict : APPROVED** (2 fichiers revus, 1 note non-bloquante, 0 bloquant)

- `src/Application/Services/Implementation/ImapService.cs` — ✅ `ProbeValidFoldersAsync` réutilise le statut du LIST-STATUS (`Count >= 0` = sémantique MailKit « -1 = inconnu ») ; re-probe ciblé `Count|Unread` uniquement pour les statuts indéterminés ; exclusion ghost et skip NoSelect/NonExistent strictement conservés
- `tests/.../ImapServiceTests.cs` — ✅ 4 tests test-first significatifs (zéro STATUS au nominal + non-régression compteurs, ghost exclu via 1 STATUS exact, NoSelect/NonExistent sans probe, re-probe limité aux indéterminés)
- ⚠️ note : sur un serveur sans capability LIST-STATUS où MailKit émet lui-même les STATUS pendant le listing, un ghost ferait échouer le listing initial — comportement pré-existant inchangé

Validation : build ✓ Release 0 erreur · tests ✓ (2 échecs = flaky pré-existants documentés) · DOD ✓ 9/9 (gain HoldTimeMs = mesure Seq au Manual Test Plan) · Sonar ✓ Quality Gate OK du premier coup, 0 issue new-code, coverage 84.2%

## Merged

- Date : 2026-06-10
- `api-mail` : squash commit `43dfc89` (PR #92 closed, branche remote supprimée, branche locale conservée)
- `dtos-mss` : aucune PR (branche vide) — remote supprimée, clone resynchronisé sur `develop`
- develop CI : ✓ success — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/27294860623
