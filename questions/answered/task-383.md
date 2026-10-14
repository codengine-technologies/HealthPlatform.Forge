# task-383 — /e2e rouge après le merge de develop (task-374) — deux motifs, aucun ne vient de la mise à jour NuGet

1. **Parité mobile — `MissingRequired` E2E-MAILBOX-001.** Le test mobile du scénario (task-374, client-mobile #95) est
   sur `develop` ; la voie mobile a joué `fix/task-370-session-weda2`, créée avant. Remède : merger `develop` dans
   cette branche (task-370), puis rejouer.
2. **Angular — E2E-COMPOSE-001 rouge (2 essais).** `moreAction` → `delete-mail-btn` introuvable : le menu « Plus
   d'actions » se referme entre l'ouverture et le clic. Cause produit : `mail-detail.component.ts` `loadContent()`
   appelle `closeMoreMenu()` et `closePreview()` à chaque rechargement, **y compris l'enrichissement temps réel du
   mail affiché** (SSE `emailsEnriched$`) — le mail tout juste reçu est enrichi juste après son ouverture. Déjà
   flaky au /e2e de task-370 (vert au 2ᵉ essai).
   Remède proposé : ne fermer menu et aperçu qu'au **changement** de mail (test unitaire rouge d'abord), dans
   l'arbre client-angular — task-370, qui a client-angular dans son périmètre.

Mobile 36/36 verts, Angular 40 verts hors COMPOSE-001 : la mise à jour NuGet n'introduit aucune régression.
