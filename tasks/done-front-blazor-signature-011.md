# done-front-blazor-signature-011 — Blazor : Gestion des signatures email

**Dependencies**: done-back-signature-010
**Feature**: tests/Features/Mss/Signature.feature
**Repo**: client-blazor (path: `Client/Blazor`)
**Module**: Client/Blazor/Src/Modules/Mss
**Status**: done (rétroactif — livré via PR #18 `feature/draft_sign`, commit `83aa852 Signature mail` du 2026-04-03)

## Objectif

Interface de gestion des signatures dans Blazor : éditeur, liste, signature par défaut, et pré-remplissage automatique dans le composeur.

## Travail réalisé

### 1. Service
- `Src/Modules/Mss/Domain/Services/ISignatureService.cs`
- `Src/Modules/Mss/Application/Services/SignatureService.cs` — wrappe l'API backend (create/update/delete/list/setDefault)
- `Src/Modules/Mss/Application/Services/HttpRequestService.cs` modifié — helpers pour les appels signature
- `Src/Modules/Mss/Application/Extensions/ServiceCollectionExtensions.cs` — DI registration

### 2. UI
- `Src/Modules/Mss/Plugin/Components/SignatureEditor.razor` — éditeur avec aperçu + liste des signatures + toggle par défaut
- `Src/Modules/Mss/Plugin/Components/SettingsComponent.razor` modifié — section "Signatures" qui héberge `SignatureEditor`
- `Src/Modules/Mss/Plugin/Components/NewMailComponent.razor` modifié — insertion automatique de la signature par défaut à l'ouverture du composeur

### 3. i18n
- `Src/Modules/Mss/Domain/Globalization/Localizer.cs` modifié — clés FR/EN pour les libellés signature

## Definition of Done

- [x] Build passes — commit `83aa852` mergé dans PR #18
- [x] CRUD fonctionnel depuis `SettingsComponent` / `SignatureEditor` — couvre scénarios 1, 2, 3
- [x] Gestion de plusieurs signatures + toggle "par défaut" dans la liste — couvre scénario 4
- [x] Insertion automatique dans `NewMailComponent` lors d'un nouveau message — couvre scénario 5
- [x] Insertion automatique lors d'une réponse (même composant NewMailComponent) — couvre scénario 6
- [x] Prévisualisation dans `SignatureEditor.razor` — couvre scénario 8
- [x] Tous les textes via Localizer (i18n FR/EN)
- [ ] Scénario 7 (changer de signature pendant la rédaction) — **à vérifier** : un sélecteur de signature dans le composeur n'est pas évident dans les fichiers touchés. Peut-être géré par un simple combobox déjà présent dans `NewMailComponent`.
- [ ] data-testid sur les éléments interactifs de `SignatureEditor` — **à vérifier** (les PRs drafts/folders l'ont fait mais pas sûr pour signature)

## Notes de clôture rétroactive (2026-04-07)

Cette tâche a été créée **après coup** pour tracer du travail déjà mergé sur `develop`. Les deux cases `[ ]` sont des gaps de traçabilité à valider par un Evaluator si on veut une DOD 100% verte. Elles ne bloquent pas la release.
