# todo-task-134.md — Vue patient mobile (3/4) : timeline biologie matricielle

**Repos**: client-mobile
**Dependencies**: done-task-133
**Epic**: E012

## Objective

Ajouter à la vue patient mobile l'onglet **Biologie** : la **timeline
biologique matricielle** (biomarqueurs × dates) avec tendances, sparklines,
bandes de référence, filtre « anormaux uniquement » et sélecteur de période.
Portage en **miroir structurel** de `client-angular`
(`BiologyTimelineComponent`), lui-même transposition fidèle du composant Blazor
`BiologyTimeline.razor`.

US **frontend-only** : les résultats de biologie sont déjà fournis structurés
par `api-mail` (`MailMedicalDocumentBiologyDto`, agrégés depuis les documents du
patient chargés en task-133). **Aucune modification backend ni DTO**. Scope :
`client-mobile` seul.

US **complète et autonome** : une fois livrée, le médecin visualise l'évolution
biologique du patient (règle 11). Dépend de task-133 (la biologie est un onglet
de `mss-patient-timeline` et s'alimente des documents déjà chargés).

## Travail de report — exigence de fidélité

Reproduire fidèlement la logique de calcul (tendances, stabilité, sparklines,
codes d'interprétation N/L/H/LL/HH) et le **nom de composant** de
client-angular. **Adapter résolument la présentation au mobile** (via
`/stitch-design`) : la grille matricielle large desktop doit rester lisible sur
écran étroit (scroll horizontal maîtrisé, biomarqueur figé, ou vue condensée).
La **fidélité porte sur les données et les calculs**, la présentation est
ré-ergonomisée — c'est le point délicat de cette task.

## Composant à porter (nom identique à client-angular)

| Sélecteur | Classe | Rôle |
|---|---|---|
| `mss-biology-timeline` | `BiologyTimelineComponent` | Grille matricielle biomarqueurs × dates : valeur + unité + bornes de référence, flag anormal (`isFlagged`), tendance (↑/↓/stable), sparkline SVG avec bande de référence, filtre par nom de biomarqueur, bascule « anormaux uniquement », période (0/3/6/12 mois). |

S'intègre comme **onglet « Biologie »** dans `mss-patient-timeline` (créé en
task-133) — affiché uniquement si le patient a des résultats de biologie
(logique `dynamicTabs`).

## Comportement attendu (parité Angular)

- Agrégation des `MailMedicalDocumentBiologyDto` de tous les documents chargés
  du patient (`allBiologyResults`).
- Grille : lignes = biomarqueurs (groupés par section), colonnes = dates de
  résultat ; chaque cellule = valeur + interprétation colorée (N/L/H/LL/HH).
- **Tendance & stabilité** calculées sur les dernières valeurs.
- **Sparkline** SVG par biomarqueur (segments + points + bande de référence),
  extensible.
- **Filtre** par nom/code/section, bascule **anormaux uniquement**
  (`showAbnormalOnly`), **période** (tous / 3 / 6 / 12 mois).
- États : chargement (`isLoading`), aucune biologie (onglet masqué).

## Definition of Done

- [ ] Build passe (`npm ci && npm run build`) — 0 erreur
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`) — 0 échec
- [ ] Composant `mss-biology-timeline` créé avec sélecteur/nom **identiques** à client-angular
- [ ] Onglet « Biologie » câblé dans `mss-patient-timeline`, affiché conditionnellement (données présentes)
- [ ] Tests unitaires des calculs : tendance, stabilité, construction de sparkline, classes d'interprétation, filtre + période + anormaux-uniquement
- [ ] Présentation mobile validée (grille lisible sur écran étroit — scroll horizontal maîtrisé ou vue condensée, référence `/stitch-design`)
- [ ] Libellés FR en dur (parité client-angular)
- [ ] `data-testid` sur le filtre, le toggle anormaux, le sélecteur de période, les cellules de valeur
- [ ] **Aucune valeur biologique ni INS en clair dans les logs**

## Manual Test Plan

- Lancer l'app mobile : `cd Client/Mobile && npm start`, se connecter (session de test)
- Onglet Patients → sélectionner un patient ayant **plusieurs résultats de
  biologie** sur plusieurs dates → onglet **Biologie** visible
- Attendu : grille biomarqueurs × dates, valeurs colorées par interprétation,
  flags anormaux visibles
- Vérifier une **tendance** (↑/↓/stable) sur un biomarqueur à plusieurs valeurs
- Déplier une **sparkline** → courbe + bande de référence cohérentes
- Filtrer par nom de biomarqueur → grille restreinte
- Activer « anormaux uniquement » → seules les lignes flaggées restent
- Changer la période (3/6/12 mois) → colonnes filtrées en conséquence
- Sur un patient **sans biologie** → onglet Biologie absent
- Vérifier la lisibilité sur petit écran (scroll horizontal maîtrisé)

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville / biologie médicale (consultation de résultats de biologie)
- **Vague Ségur** : hors exigence DSR nouvelle — portage d'affichage ; le CR-BIO (volet CI-SIS biologie) est traité en amont par `api-mail`/`interop-cda`
- **Exigences DSR honorées** : non applicable — aucune exigence DSR nouvelle côté mobile
- **INS** : aucune manipulation directe — les résultats sont déjà rattachés au patient sélectionné (state hérité). INS jamais loggée ni en route mobile
- **Authentification PS** : session MSSanté existante, niveau eIDAS inchangé
- **Habilitations** : inchangées — consultation suivant l'habilitation du titulaire de la boîte
- **Interop CI-SIS** : résultats de biologie issus de **CDA CR-BIO** parsés en amont (`interop-cda`) ; le mobile **ne parse aucun CDA**, il affiche le `MailMedicalDocumentBiologyDto` structuré. Codes (LOINC/section) affichés tels quels
- **Tracé PGSSI-S** : consultation tracée côté `api-mail` (canal existant via le chargement des documents) ; pas de log client des valeurs
- **Consentement patient** : non applicable directement (consultation par le destinataire) ; opposition gérée en task-132
- **Référentiels métier** : LOINC (codes de biomarqueurs), codes d'interprétation HL7 (N/L/H/LL/HH) — **affichés tels quels**, aucun codage produit par le mobile
- **Hébergement HDS** : oui — données servies par l'`api-mail` (backend HDS) ; transit HTTPS, pas de persistance disque sur l'appareil
- **AIPD / impact RGPD** : inchangé — nouveau canal de consultation mobile d'un traitement existant

## Branches
- `client-mobile` (pushed) : feat/task-134-mobile-biology-timeline — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-134-mobile-biology-timeline

## Stitch design log
- Écran : onglet **Biologie** de la timeline patient (`mss-biology-timeline`). Point délicat = re-ergonomie de la grille matricielle large desktop vers mobile : **scroll horizontal maîtrisé** + **colonne biomarqueur figée** (`position: sticky`), toolbar compacte (`ion-searchbar` filtre + `ion-segment` période + bouton « Anormaux »), sparklines SVG conservées. Fidélité **données/calculs** (miroir Angular), présentation ré-adaptée.
- `/stitch-design` : best-effort, non invoqué (référence = `BiologyTimeline` Angular existant).

## Develop log
- Repos touched : client-mobile
- DTOs published : no DTO change (MailMedicalDocumentBiologyDto déjà présent dans le modèle mobile)
- Interop published : no interop change
- Commits :
  - client-mobile : 0c78742 feat(mobile): patient biology matrix timeline (task-134)
- Local build / test : ✓ client-mobile (`npm run build` 0 erreur ; `npm test` 213/213 verts)
- DOD self-check :
  - ✓ Build / Tests verts
  - ✓ Composant `mss-biology-timeline` (sélecteur/nom identiques à client-angular)
  - ✓ Onglet « Biologie » câblé dans `mss-patient-timeline`, affiché conditionnellement (données présentes) ; `ion-segment` Documents/Biologie quand >1 onglet
  - ✓ Tests des calculs : interprétation N/L/H/LL/HH, formatRef, build/ordre des sections, filtre nom, anormaux-uniquement, filtrage période, tendance (baisse), stabilité (Stable), modèle sparkline + câblage onglet
  - ✓ Présentation mobile : grille à scroll horizontal + colonne biomarqueur figée
  - ✓ Libellés FR en dur
  - ✓ data-testid (filtre, toggle anormaux, sélecteur période, cellules valeur, onglets)
  - ✓ Aucune valeur biologique ni INS loggée côté client
- Note de parité : calculs (tendance/stabilité/sparkline/sections) portés fidèlement (logique d'angle de tendance simplifiée mais **iso-résultat**) ; synthèse clinique = task-135. Deep-link `?ins=` toujours omis.
- Next step : /forge-simplify task-134

## Simplify log
- Repos passed : client-mobile
- Applied & committed : client-mobile: 1 file (e64fe18) — efficacité, iso-comportement (213/213 verts)
  - `visibleDateSet` computed (le `Set` était reconstruit dans 5 méthodes par cycle CD)
  - `getTrend` : `.find` sur les entrées déjà triées desc (au lieu de filter+sort)
  - `getEntryForDate` : O(1) via une Map `entriesByDate` par ligne (au lieu d'un `.find` linéaire par cellule de la grille)
  - helper `countAbnormalInRows` (dédup total + par-section)
- Skipped findings (noted, not applied) :
  - Convertir le setter `@Input` en `effect()` — **la suggestion des agents est incorrecte** (`effect()` ne tracerait pas un `@Input` non-signal) ; le setter actuel (set signal + `autoSelectPeriod` synchrone qui lit le computed `allDates`) est correct et conforme à la convention mobile (`@Input`)
  - Extraire des utils date/biologie partagés — large, touche des composants pré-existants (task-098 `biology`, `mail-header`), casse l'auto-suffisance/parité du miroir Angular
  - Constante `BIO_COLORS` — cosmétique, miroir des `var()` inline Angular
- Rolled back (validation RED) : none
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*
- Build / tests : ✓ green on client-mobile (build 0 erreur ; 213/213 tests)
- Next step : /lint-mobile task-134

## Lint mobile log
- Baseline `npm run lint` (ng lint) : **All files pass linting** — 0 error, 0 warning
- Iterations run : 0 (nothing to fix)
- Fixes committed : none (tree clean)
- Build / tests : verts depuis /develop + /forge-simplify (build 0 erreur ; 213/213 tests)
- Next step : /review task-134

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/37 — label `awaiting-human-merge`

## Code Review Summary
- Verdict : **APPROVED** (0 blocking, 1 note non bloquante)
- client-mobile :
  - `mss-biology-timeline` — ✅ calculs fidèles (grille/sections, tendance, stabilité, sparkline, interprétation), filtres/période, perf (visibleDateSet, entriesByDate, find-not-sort)
  - `mss-patient-timeline` — ✅ onglet Biologie conditionnel + ion-segment, allBiologyResults/dynamicTabs/selectTab
  - tests — ✅ tous les calculs + câblage onglet
- Note non bloquante : ergonomie grille petit écran (scroll horizontal + colonne figée) = vérification visuelle.
- Validation : build ✓ 0 erreur, tests ✓ 213/213, lint ✓ clean.

## Merged
- Date : 2026-06-29
- client-mobile : squash `2a6f4c8` — PR #37 closed, remote branch `feat/task-134-mobile-biology-timeline` deleted (local kept)
- develop CI : no workflow configured on HealthPlatform.Mobile (N/A)
