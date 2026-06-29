# todo-task-120.md — Refonte Stitch composant `inbox-biology-ack-chip` (mobile)

**Repos**: client-mobile
**Dependencies**: done-task-110
**Single frontend**: true
**Epic**: E014

## Objective
Refondre **structurellement** le chip de filtre acquittement biologie
`inbox-biology-ack-chip`
(`src/app/features/mail/components/inbox-biology-ack-chip/*`) pour une fidélité
parfaite à sa **référence Stitch** `inbox-biology-ack-chip`, sur la base du socle
`done-task-110`.

Chip cliquable affichant le compte de résultats de biologie non acquittés, servant
de filtre dans l'inbox (états : actif/inactif, compteur). Travail **soigné**.
`client-mobile` uniquement — aucun changement fonctionnel.

## Référence Stitch
- **À créer** : l'écran/élément Stitch `inbox-biology-ack-chip` n'existe pas.
  `/stitch-design task-120` doit le créer (titre kebab `inbox-biology-ack-chip`).
  Fallback création manuelle dans l'UI Stitch si le MCP retimeoute. Stitch =
  référence, pas du code.

## Definition of Done
- [ ] Build passe (`npm ci && npm run build`, 0 erreur)
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`, 0 échec)
- [ ] Référence Stitch `inbox-biology-ack-chip` disponible (créée) et consignée
- [ ] Structure alignée : chip avec compteur, états actif/inactif, style clinique
      cohérent (radius 4px, label-md)
- [ ] Tokens du socle réutilisés — aucune valeur de design en dur
- [ ] `data-testid` préservés/complétés
- [ ] Aucune régression (bascule du filtre, compteur)
- [ ] Comparaison visuelle avec le screenshot Stitch consignée

## Manual Test Plan
- Lancer le mobile, ouvrir un dossier contenant des résultats de biologie.
- Vérifier le rendu du chip (compteur, état) au nouveau design.
- Activer/désactiver le filtre → la liste se restreint/rétablit, inchangé.
- Comparer à la maquette Stitch `inbox-biology-ack-chip`.

## Conformité santé / Ségur / ANS
- **Couloir Ségur** : biologie médicale (affichage filtre) — restyling UI sans
  logique métier. **Vague Ségur** : hors Ségur (UX).
- **DSR / INS / Authentification / Habilitations / Interop / PGSSI-S /
  Consentement / Référentiels / HDS / RGPD** : non applicable. Ne jamais exposer
  d'INS/contenu CDA/biologie en clair dans l'UI au-delà du strict affichage métier
  existant.

## Branches
- `client-mobile` (pushed) : feat/task-120-stitch-inbox-biology-ack-chip — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-120-stitch-inbox-biology-ack-chip

## Stitch design log
- Projet Stitch `client-mobile` (id 10088502293310567548, MOBILE) ; design system
  `assets/9aca84edc31f42798fd98bd24e151040` (« Clinical Precision »).
- Écran `inbox-biology-ack-chip` : **créé** via `generate_screen_from_text`
  (id `e6222381e2204ccd9d45bd785fa15d93`, fichier `0b11928de0b44afeaf9029f8664550ad`).
  Les deux appels MCP ont retourné un timeout côté client, mais la génération a
  **abouti côté serveur** (confirmé via `list_screens` au 2ᵉ essai, à la demande humaine).
  - Screenshot : https://lh3.googleusercontent.com/aida/AP1WRLsZJboy8-2b_61e0CK04yac1br189Wln8x_oeS0ZacAeeHbSz-LhH2dpxBopv3LlCldui509vN8pPQQtZ53jCbjYOoKnaVO3OJNTHNFa4AmhE2NaUdhpBDFq0f3ylqb_IkGme-w6bJBepMy-B88Vn7qqEbjUIyUvGyEtHWkspJv9rYh3Ta9vMKIHy6loiCaQRyVEqY6WniSfBM3Sz1G0B-SmWNFWySKFWvlA_YRYIZp8iVhhRFt-RWGcmGG
- **Comparaison visuelle** consignée : l'écran montre les deux états empilés
  (« État inactif » / « État actif »), pilule 4px (`0.25rem`), accent tertiaire
  `#920d00` actif, libellé « Bio à acquitter » / « Bio à acquitter (3) », dans le
  contexte de la barre de filtres (Tous/Non lus/Flaggés) — conforme à l'implémentation.
  - **Écart mineur assumé** : la maquette n'affiche le compteur qu'à l'état actif ;
    l'implémentation l'affiche dans le libellé aux deux états, par **parité avec
    client-angular** (le compteur dans le libellé est la référence fonctionnelle,
    et il est plus utile de connaître le nombre avant d'activer le filtre).
- Implémentation alignée sur la **spec design system** (connue via `get_project`) :
  « Chips : Small 4px radius, Surface Alt background, label-md typography » ; accent
  **tertiaire #920d00** (biologie) à l'état actif. Référence visuelle complémentaire :
  écran `inbox-biology-abnormal` (regroupement biologie hors normes).

## Develop log
- Repos touchés : `client-mobile` (poussé). Aucun DTO/interop/backend.
- Commit poussé : client-mobile `fc012d5` feat(mobile): Stitch restyle of inbox-biology-ack-chip + pending counter.
- Vérifs locales : `npm run build` ✓ (0 erreur ; seul warning budget pré-existant home.page.scss) ; `npm test` headless **151 ✓** (+3 vs 148).
- Stitch : création écran `inbox-biology-ack-chip` tentée → timeout MCP (best-effort) ; implémentation alignée sur la spec design system (chips 4px/label-md/surface-alt, accent tertiaire actif). Cf. ## Stitch design log.
- DOD : compteur ajouté, états actif/inactif token-driven, data-testid préservés/complétés (chip + label), pas de régression filtre (refetch on folder change). Comparaison Stitch déférée (écran à finaliser côté humain).
- Next step : /forge-simplify task-120.

## Simplify log
- Repos passed : client-mobile.
- Applied & committed : none — composant unique, token-driven, réutilise
  `getBiologyAckPendingMailUids` ; aucune duplication ni gain de simplification.
- No change : client-mobile.
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*.
- Next step : /lint-mobile task-120 (api-mail & client-angular non touchés ; client-mobile touché).

## Lint mobile log (client-mobile)
- Baseline `npm run lint` (ng lint) : **All files pass linting** — 0 erreur. Aucun fix, aucun commit. Skip clean.
- Next step : /review task-120.

## PRs
- `client-mobile` (pushed) : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/23 — label `awaiting-human-merge`

## Code Review Summary
✅ **APPROVED** — 0 bloquant. Restyle token-driven (4px/label-md/surface-alt, accent tertiaire actif), compteur « Bio à acquitter (N) » par dossier (`ngOnChanges`), filtre rejoué scopé au bon dossier (pas de régression), data-testid + aria-pressed. Build ✓, 151 tests ✓, lint 0 erreur. Écran Stitch à finaliser côté humain (timeout MCP) — non bloquant.

## Merged
- Date : 2026-06-25 (human `/merge --i-tested`, HAG rule 10 satisfaite).
- Squash-merge sur `develop` : `client-mobile` `13b1627` (PR #23 fermée).
- CI develop : aucun workflow CI sur ce repo (rien à attendre).
- Remote branch `feat/task-120-stitch-inbox-biology-ack-chip` supprimée ; branche locale conservée.
- Écran Stitch `inbox-biology-ack-chip` créé (id e6222381e2204ccd9d45bd785fa15d93) — comparaison visuelle consignée.
