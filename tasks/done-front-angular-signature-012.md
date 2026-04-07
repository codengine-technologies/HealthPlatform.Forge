# done-front-angular-signature-012 — Angular : Gestion des signatures email

**Dependencies**: done-back-signature-010
**Feature**: tests/Features/Mss/Signature.feature
**Repo**: client-angular (path: `Client/Angular`) — **EXCLU de la forge, géré manuellement**
**Module**: Client/Angular/front/libs/mss
**Status**: done (rétroactif — livré dans le commit `c4e287f First MSS implementation` sur la branche `feature/mss`)

## Objectif

Interface Angular de gestion des signatures email : composant dédié, modèle, intégration dans le composeur et les settings.

## Travail réalisé

### 1. Modèle
- `front/libs/mss/src/core/models/signature.model.ts` — DTO TypeScript

### 2. Service API
- `front/libs/mss/src/core/services/mss-api.service.ts` modifié — endpoints signature (create/update/delete/list/setDefault)

### 3. Composant dédié
- `front/libs/mss/src/features/signatures/mss-signatures.component.ts`
- `front/libs/mss/src/features/signatures/mss-signatures.component.html`
- `front/libs/mss/src/features/signatures/mss-signatures.component.scss`

### 4. Intégration
- `front/libs/mss/src/features/settings/mss-settings.component.{ts,html}` modifié — section Signatures qui héberge `mss-signatures.component`
- `front/libs/mss/src/features/mail/components/mail-compose/mail-compose.component.{ts,html}` modifié — insertion automatique de la signature par défaut
- `front/libs/mss/src/core/index.ts`, `features/index.ts`, `src/index.ts` — exports publics

## Definition of Done

- [x] Build passes (vérification manuelle par le PO avant merge côté TFS)
- [x] CRUD fonctionnel via `mss-signatures.component` — couvre scénarios 1, 2, 3, 4
- [x] Insertion automatique dans `mail-compose` (nouveau message et réponse) — couvre scénarios 5, 6
- [x] Standalone component, OnPush, Angular Signals (convention du projet Angular)
- [ ] Scénario 7 (changer de signature pendant la rédaction) — **à vérifier** dans `mail-compose.component`
- [ ] Scénario 8 (prévisualisation) — **à vérifier** dans `mss-signatures.component`

## Notes de clôture rétroactive (2026-04-07)

Tâche archive rétroactive pour un repo **exclu de la forge** (voir CLAUDE.md section "Repos EXCLUDED from the forge"). Aucun agent dev ne sera dispatché ici. Les cases `[ ]` sont des gaps de traçabilité : si le PO veut les fermer, c'est une inspection manuelle côté TFS, pas un travail forge.
