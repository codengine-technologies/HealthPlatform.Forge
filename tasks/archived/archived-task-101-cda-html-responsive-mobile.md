# todo-task-101-cda-html-responsive-mobile.md — Rendre le HTML CDA responsive pour affichage mobile

**Repos**: interop-cda
**Dependencies**: none
**Epic**: E012

> **US mono-repo justifiée** : le défaut est dans le HTML produit par la transformation CDA->HTML du package `interop-cda`. Le correctif est attendu dans la feuille de style / structure HTML générée, sans changement d'API backend ni de DTO.

## Objective

Corriger le rendu HTML généré par `Interop.Cda.Parser` afin qu'il soit
**responsive mobile-first** : le contenu doit s'adapter à la largeur de
l'écran (smartphone), éviter les débordements horizontaux, et rester lisible
sans zoom manuel.

Le document HTML transformé depuis CDA doit être exploitable tel quel dans les
clients web/mobile (iframe ou rendu embarqué), avec un comportement cohérent
sur desktop et mobile.

## Problème observé

- Colonnes / tableaux CDA qui dépassent la largeur disponible
- Typographies et espacements non adaptés au viewport mobile
- Sections pouvant être tronquées visuellement selon la largeur de device
- Expérience nécessitant scroll horizontal ou zoom utilisateur

## Comportement attendu

- Le HTML généré inclut une stratégie responsive explicite (`meta viewport`,
  règles CSS fluides, breakpoints utiles)
- Les blocs principaux, tableaux et cellules s'ajustent à la largeur mobile
- Aucune fuite de contenu hors écran sur viewport mobile standard (320px+)
- La lisibilité clinique reste préservée (titres, sections, valeurs, unités)
- Le rendu desktop n'est pas régressé (pas de dégradation majeure)

## Scénarios d'acceptation

1. **Viewport mobile** — Étant donné un CDA transformé en HTML, quand je
   l'ouvre sur un viewport 390x844, alors aucun contenu important ne déborde
   horizontalement.
2. **Petit mobile** — Quand j'ouvre le même document sur 320px de large,
   alors le contenu reste lisible sans zoom, avec adaptation des tableaux.
3. **Desktop** — Quand j'ouvre le document sur desktop, alors la mise en page
   reste stable et lisible.
4. **Complexe CDA** — Pour un CDA avec sections longues, tableaux et listes,
   le rendu reste navigable sans perte d'information.

## Definition of Done

- [ ] Build passe : `cd interop/interop.cda.parser && dotnet build interop.cda.parser.sln` (0 erreur)
- [ ] Tests passent : `cd interop/interop.cda.parser && dotnet test interop.cda.parser.sln` (0 échec)
- [ ] Le HTML généré intègre les règles responsive nécessaires (viewport + CSS adaptative)
- [ ] Les tableaux / blocs larges n'induisent plus de débordement horizontal non maîtrisé en mobile
- [ ] Le rendu des principaux volets CDA reste lisible sur 320px, 390px et desktop
- [ ] Des tests (unitaires ou snapshot/rendu selon outillage existant) couvrent au moins un cas CDA avec tableau large
- [ ] Aucun script actif injecté dans le HTML généré (pas de régression sécurité)
- [ ] Aucun log en clair de données de santé ajouté par le correctif

## Manual Test Plan

- Générer un HTML depuis un CDA de test représentatif (incluant sections + tableaux)
- Ouvrir le HTML dans un navigateur avec mode responsive:
  - iPhone SE (375x667) ou équivalent
  - 390x844
  - 320x568
- Vérifier :
  - absence de débordement horizontal global
  - lisibilité des sections cliniques
  - adaptation correcte des tableaux
- Ouvrir ensuite en desktop (>=1280px) et vérifier l'absence de régression visuelle majeure
- Vérifier dans le client mobile MSS que le document occupe bien l'espace visible sans troncature due au layout HTML source

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR** : amélioration d'affichage d'un contenu CDA déjà produit (pas de nouveau flux)
- **Interop CI-SIS** : CDA r2 inchangé sur le fond ; seule la présentation HTML est ajustée
- **Sécurité** : aucune exécution de script côté document généré
- **AIPD / RGPD** : inchangé — pas de nouveau traitement, correction de présentation

## Branches (attendues via /start)

- `interop-cda` : `feat/task-101-cda-html-responsive-mobile`

## Branches
- `interop-cda` (pushed) : feat/task-101-cda-html-responsive-mobile — https://github.com/codengine-technologies/interop.cda.parser/tree/feat/task-101-cda-html-responsive-mobile

> Mono-repo (interop-cda). Chemin réel : `interop/` (sln `interop.cda.parser.sln`) — la commande du DOD `cd interop/interop.cda.parser` est à lire `cd interop`.

## Develop log
- Repos : interop-cda (mono-repo)
- Feuille active confirmée : resources/html/cda_asip.xsl (Resources.resx ResXFileRef → Resources.cda_asip, chargée par CDAHtmlTransformer)
- CSS responsive : display:block+overflow-x sur tables (≤1200px), overflow-wrap/word-break cellules, img max-width + box-sizing, @media 480px ; fix accolade @media 1200px manquante
- Test : CdaHtmlResponsiveTests (CDA tableau large → markers responsive + no <script>)
- Build ✓ · Tests ✓ 384 réussis / 5 ignorés / 0 échec
- Piège : GenerateResource incrémental sur mtime du .resx (pas du .xsl ResXFileRef) → build propre OK, incrémental local = toucher Resources.resx
- Commit : interop-cda @aad3013

## PRs
- `interop-cda` : https://github.com/codengine-technologies/interop.cda.parser/pull/6 — label `awaiting-human-merge`

## Suivi (rule 11)
- Bump consommateur `api-mail` (Directory.Packages.props) vers la nouvelle version NuGet d'interop.cda.parser après merge — hors périmètre mono-repo de cette US.

## Code Review Summary
- Verdict : APPROVED · Build ✓ · Tests ✓ 384/0 · pas de script · pas de log santé · sans changement API/DTO

## Merged
- Merged : 2026-06-18 (squash) by human authorization
- interop-cda : develop @21e55e4 (PR #6 closed)
- Suivi rule 11 : bump api-mail (NuGet interop.cda.parser) restant
- Local feature branch conservée
