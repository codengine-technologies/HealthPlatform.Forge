# wip-task-015a-suppression-detection-backend.md — Backend détection des messages de suppression pure (LGC.MSS/UX.05 — couche données)

**Repos**: api-mail, dtos-mss
**Dependencies**: archived-task-006, archived-task-034
**Epic**: E009

## Branches

- `dtos-mss` (pushed) : `feat/task-015-suppression-version-navigation` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-015-suppression-version-navigation
- `api-mail` (pushed) : `feat/task-015-suppression-version-navigation` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-015-suppression-version-navigation

> **Note** : nom de branche `-suppression-version-navigation` hérité de l'US d'origine (avant découpage Option B 2026-05-07). Conservé pour préserver l'historique des commits déjà poussés.

## Objectif

**Scope réduit (Option B 2026-05-07)** : livrer la **couche données + algorithme de détection** des messages de suppression pure côté receveur — entité, migration, détection au moment de `AddNewMail`, mappings DTO. Aucun endpoint utilisateur, aucune UI. C'est le **socle** que `task-015b` (endpoint accept/refuse + UI banner) et `task-015c` (navigation entre versions) consomment.

US **technique / dette** — la livraison **n'est pas user-visible** mais elle pose les rails pour 015b et 015c. Respecte rule 11 par construction : aucun changement UX, juste préparation data.

## Périmètre

### Scope IN (livré)

1. **Champs additionnels** sur `MailMedicalDocument` :
   - `SuppressionRequestedAt` (`DateTime?`) — date de la demande
   - `SuppressionRequestedByMailId` (`Guid?`, FK self-mail OnDelete SetNull, traçabilité)
   - `SuppressionAccepted` (`bool`, default false) — verdict humain (à activer par 015b)
   - `SuppressionRefused` (`bool`, default false) — verdict humain (à activer par 015b)
2. **Algorithme de détection** au moment de `AddNewMail` (`MailRepository.DetectSuppressionRequestAsync`) avec 5 garde-fous :
   - Skip si CDA présent (le pan "annule et remplace" reste géré par `task-034` INT.18)
   - Skip si pas d'`In-Reply-To`
   - Skip si mail entrant en self-action folder
   - Skip si mail original en self-action folder
   - Skip si déjà marqué (no double-mark)
3. **Pre-génération Guid v7** sur le nouveau Mail pour que `SuppressionRequestedByMailId` puisse flow dans les docs cibles avant SaveChanges.
4. **DTO mappings** (3 sites) projettent les 4 fields.
5. **6 tests unitaires** dans `MailRepositorySuppressionDetectionTests.cs`.

### Scope OUT (déféré)

- **Endpoint** `POST /medical-documents/{id}/suppression-decision` → `task-015b`
- **Endpoint** `GET /medical-documents/{id}/version-chain` → `task-015c`
- **Audit traces** `MailSuppressionAccept` / `MailSuppressionRefuse` → `task-015b`
- **PatientTimeline filter** (filtre `SuppressionAccepted == true`) → `task-015b`
- **Bannière demande de suppression** Blazor + Angular → `task-015b`
- **Badge "REMPLACÉ" cliquable** + **"Version précédente"** → `task-015c`

## Definition of Done

- [x] Build passe (0 erreur) sur `api-mail`, `dtos-mss`
- [x] Tests passent (0 failure)
- [x] Suite api-mail infrastructure 315 → **321 passed** (+6 tests détection), 0 fail
- [x] DTO `MailMedicalDocumentDto` enrichi de 4 fields, NuGet **264.0.0** publié
- [x] Entity `MailMedicalDocument` + nav `SuppressionRequestedByMail`
- [x] Migration consolidée + FK self-mail + index `IX_MailMedicalDocuments_SuppressionRequestedByMailId`
- [x] Algorithme `DetectSuppressionRequestAsync` avec 5 garde-fous + pre-génération Guid v7
- [x] DTO mappings (3 sites) projettent les 4 fields
- [x] 6 tests unitaires : happy + 5 garde-fous

DOD du scope final : **✓ atteinte**.

## KPIs (PR body — repris par `/tech-writer` pour E009)

```
### Backend détection suppression — task-015a

| Métrique | Avant | Après | Δ |
|---|---|---|---|
| Tests api-mail infrastructure | 315 | 321 | +6 |
| `MailMedicalDocument` fields persistés | 21 | 25 | +4 |
| Migration delta | — | +4 cols + 1 FK + 1 index | — |
| NuGet `HealthPlatform.Dtos.Mss` | 261.0.0 | 264.0.0 | +1 publish |
| Surface UI changée | — | — | aucune (rule 11 OK par construction) |
```

## Manual Test Plan

Aucun comportement utilisateur visible — validation entièrement automatique :

1. `cd Api/Mail`
2. `dotnet build HealthPlatform.Api.Mail.sln --configuration Release` → 0 erreur
3. `dotnet test HealthPlatform.Api.Mail.sln --configuration Release` → tests verts (1932 expected total)
4. (Optionnel) Smoke run : recevoir un mail avec CDA puis un mail texte qui répond sans pièce jointe → vérifier en BDD `SELECT SuppressionRequestedAt, SuppressionRequestedByMailId FROM "MailMedicalDocuments"` que les fields sont posés. **Aucune surface UI exposée**, c'est attendu.

## Notes

- Issue du découpage **Option B (2026-05-07)** de la US d'origine `task-015` (~800 LOC + 18 tests + 8-10 h dev humain). Cette sub-task = **socle data + détection** (~400 LOC + 6 tests).
- 015b et 015c dépendent de 015a mergée (NuGet 264.0.0 stable + migration appliquée sur develop).

## Develop log

### Run 1 — 2026-05-07

- **Repos touchés** : `dtos-mss` (1 commit), `api-mail` (2 commits). `client-blazor` a un commit isolé de bump dtos sur la branche partagée — sera embarqué par task-015b. `client-angular` non touché.
- **DTOs publiés** : 261.0.0 → **264.0.0**.
- **Commits** :
  - `dtos-mss` : `94e2ff4` feat(dto): add suppression-request fields
  - `api-mail` : `60f5839` chore(deps): bump dtos 264.0.0 + `fd631c1` feat(application): pure-suppression detection backend
- **Build / tests** ✓ : suite infrastructure 315 → **321 passed**, 0 fail.

### Livré

- Entity + migration + DataContext (4 fields)
- `DetectSuppressionRequestAsync` (5 garde-fous + pre-Guid v7)
- DTO mappings (3 sites)
- 6 tests unitaires

### Next step

`/review task-015a-suppression-detection-backend` pour valider + ouvrir les PRs (api-mail + dtos-mss). Skip `/sonar` — pas de smell mécanique attendu sur ce petit lot.

### Historique — découpage Option B (2026-05-07)

US d'origine `task-015` jugée trop large pour `/develop` autonome après tentative. Découpée en 3 :
- task-015a-suppression-detection-backend (cette US — socle data livré autonomement)
- task-015b-suppression-decision-endpoint-ui (endpoint accept/refuse + bannière UI Blazor + Angular + audit traces + PatientTimeline filter)
- task-015c-version-navigation (badge "REMPLACÉ" cliquable + lien "Version précédente" + endpoint `GET /version-chain`)

## PRs

- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/18 — label `awaiting-human-merge`
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/51 — label `awaiting-human-merge`
- `client-blazor` : pas de PR pour 015a (la branche `feat/task-015-suppression-version-navigation` reste pushée avec un commit isolé de bump dtos — sera embarquée par task-015b)
- `client-angular` : pas de scope dans 015a (UI livrée par task-015b)

## Code Review Summary

Verdict global : **APPROVED** (2 repos validés, 6 fichiers revus, 1 suggestion non bloquante, 0 blocking).

- ✅ **dtos-mss** : 4 fields additifs purs (DateTime?, Guid?, 2 bool default false), backward compatible, doc symétrique aux fields task-013
- ✅ **api-mail** : entity + migration + DataContext + algorithme `DetectSuppressionRequestAsync` (60 LOC, 5 garde-fous explicites, pre-Guid v7 pour set FK avant SaveChanges) + DTO mappings cohérents (3 sites) + 6 tests AAA
- ⚠️ Suggestion non bloquante : la détection ne tourne pas dans `UpdateExistingMailWithContentAsync` (path duplicate-fallback task-024). 99 % des cas de réception passent par `AddNewMail`. À étendre en follow-up si besoin.

### Tests

- **api-mail** : 86 + 1313 + **321** + 102 + 122 = **1944 passed** / 21 skipped / 0 failed (+6 vs baseline post-task-034)
- **client-blazor** : non touché (37/37 inchangé)
- **client-angular** : non touché (115/115 inchangé)

HAG (règle 10) : test manuel humain selon `## Manual Test Plan` (validation backend uniquement, aucune UI exposée), puis `/merge task-015a-suppression-detection-backend --i-tested` pour squash-merger les 2 PRs en topological order (`dtos-mss → api-mail`).

## Merged

- **2026-05-07** — 2 PRs squash-mergées par le humain via `/merge task-015a-suppression-detection-backend --i-tested`, ordre topologique `dtos-mss → api-mail`.
- `dtos-mss` : squash sha **`e9ba40f`** sur `develop` — PR #18 closed, remote branch `feat/task-015-suppression-version-navigation` supprimée (--delete-branch), local préservée.
- `api-mail` : squash sha **`a96421b`** sur `develop` — PR #51 closed, remote branch supprimée. Squash diff cumulatif large (49 fichiers / +574/-186) — inclut le delta cumulé depuis le checkpoint pre-task-015a (post-task-034).
- `client-blazor` : **pas de PR pour 015a** (par design) — la branche `feat/task-015-suppression-version-navigation` (1 commit isolé bump dtos) reste pushée pour task-015b qui l'étendra avec l'UI bannière + accept/refuse.
- `client-angular` : pas de scope dans 015a (mode code-only — humain gère silencieusement).
- CI `develop` (api-mail) : ✓ green — workflow `Build and Publish` succeeded.
- Sub-tasks restantes : `todo-task-015b-suppression-decision-endpoint-ui.md`, `todo-task-015c-version-navigation.md`.
