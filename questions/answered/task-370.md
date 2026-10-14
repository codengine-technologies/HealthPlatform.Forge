# task-370 — /e2e rouge : E2E-ATTACH-001 sur mobile (défaut du test, pas régression produit)

**Nature du blocage** : régression de suite — test **mal écrit**, hors périmètre de la task.

- Voie mobile : 35 verts, **1 rouge** (E2E-ATTACH-001, rouge au premier essai et au rejeu) ; voie Angular : 40 verts, 1 flaky (E2E-COMPOSE-001). Parité verte des deux côtés.
- task-370 ne touche pas client-mobile (`develop`, propre) : le rouge est sur le code de `develop`.
- **Cause** (`Client/Mobile/e2e/specs/functional.spec.ts:1250-1259`, inchangé depuis task-170) :
  `locator('[data-testid^="attachment-"]…').first().or(getByTestId('download-all-attachments-zip'))`.
  `.first()` s'applique au premier membre seulement ; quand la pièce `attachment-IHE_XDM.ZIP` **et** le bouton
  « Tout télécharger (ZIP) » sont visibles ensemble, le `or` résout 2 éléments → *strict mode violation*.
  L'écran est juste (les deux éléments doivent être là) ; le test ne tolère que l'un des deux.
  Il passait tant que le premier mail à pièce jointe de la liste n'affichait pas les deux à la fois.
- **Correctif proposé** (une ligne) : `.or(…)` puis `.first()` sur l'ensemble —
  `page.locator('[data-testid^="attachment-"]:not([data-testid*="banner"])').or(page.getByTestId('download-all-attachments-zip')).first()`.
  Consigne existante : `conventions/e2e.md` › `selecteur-ambigu`.

**Décision humaine** (la forge ne corrige pas dans `/e2e`, et client-mobile n'est pas dans les `**Repos**` de task-370) :
1. ajouter `client-mobile` aux `**Repos**` de task-370 et appliquer le correctif sur une branche de la task ; ou
2. correctif dans une task / PR dédiée, puis rejouer `/e2e task-370` ; ou
3. quarantaine humaine du test (tag `@quarantaine` + task de correction).

## Résolu (2026-10-14)

Option 1 retenue par l'humain : client-mobile ajouté à task-370, sélecteur corrigé (`a6166a4`), vert au rejeu de task-383.
