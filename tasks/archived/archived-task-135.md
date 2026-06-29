# todo-task-135.md — Vue patient mobile (4/4) : synthèse clinique & antécédents

**Repos**: client-mobile
**Dependencies**: done-task-133
**Epic**: E012

## Objective

Ajouter à la vue patient mobile l'onglet **Synthèse** : la **synthèse clinique**
du patient (allergies critiques, problèmes actifs, traitements, antécédents,
vaccinations, mode de vie, antécédents familiaux) et le détail des
**antécédents** par section. Portage en **miroir structurel** de
`client-angular` (`ClinicalSynthesisComponent`, `MedicalHistoryComponent`).

US **frontend-only** : les éléments de synthèse sont déjà fournis structurés par
`api-mail` (`MailMedicalDocumentSummaryDto`, agrégés depuis les documents du
patient chargés en task-133). **Aucune modification backend ni DTO**. Scope :
`client-mobile` seul.

US **complète et autonome** : une fois livrée, le médecin dispose d'une synthèse
clinique consolidée du patient (règle 11). Dépend de task-133 (la synthèse est
un onglet de `mss-patient-timeline` et s'alimente des documents déjà chargés).

## Travail de report — exigence de fidélité

Reproduire fidèlement la logique de catégorisation (sections CDA → cartes), la
détection de criticité (mots-clés sévérité), les libellés/icônes et les **noms
de composants** de client-angular. **Adapter la présentation au mobile** (via
`/stitch-design`) : la grille multi-colonnes desktop devient un empilement de
**cartes** mobiles (`ion-card`) et des **sections repliables** (`ion-accordion`)
pour les antécédents.

## Composants à porter (noms identiques à client-angular)

| Sélecteur | Classe | Rôle |
|---|---|---|
| `mss-clinical-synthesis` | `ClinicalSynthesisComponent` | Synthèse clinique : bannière allergies critiques, carte principale allergies, cartes prioritaires (problèmes actifs, traitements), cartes secondaires (antécédents médicaux, vaccinations, mode de vie, antécédents familiaux). Sévérité (danger/warning/info/neutral). |
| `mss-medical-history` | `MedicalHistoryComponent` | Sections repliables d'antécédents (médicaux, chirurgicaux, familiaux…) ; une section ouverte à la fois ; libellés/icônes/statuts par type. |

S'intègre comme **onglet « Synthèse »** dans `mss-patient-timeline` (créé en
task-133) — affiché uniquement si le patient a des éléments de synthèse
(logique `dynamicTabs`). `mss-clinical-synthesis` est aussi réutilisé comme
**vue structurée** dans `mss-medical-document-modal` (task-133) — veiller à la
réutilisation, pas à la duplication.

## Comportement attendu (parité Angular)

- Agrégation des `MailMedicalDocumentSummaryDto` de tous les documents chargés
  du patient (`allSummaryItems`).
- **Bannière allergies critiques** en tête si présence d'allergie sévère
  (détection `isCritical` sur mots-clés sévérité).
- **Cartes** : allergies (principale), problèmes actifs + traitements
  (prioritaires), antécédents/vaccinations/mode de vie/antécédents familiaux
  (secondaires), chacune avec compteur et code couleur de sévérité.
- **Antécédents** (`mss-medical-history`) : sections repliables, une ouverte à
  la fois, libellés et icônes par type de section CDA.
- Affichage du dosage pour les traitements, du lien de parenté pour les
  antécédents familiaux, des dates (onset/abatement) formatées FR.
- États : chargement (`isLoading`), aucune synthèse (onglet masqué).

## Definition of Done

- [ ] Build passe (`npm ci && npm run build`) — 0 erreur
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`) — 0 échec
- [ ] Composants `mss-clinical-synthesis`, `mss-medical-history` créés avec sélecteurs/noms **identiques** à client-angular
- [ ] Onglet « Synthèse » câblé dans `mss-patient-timeline`, affiché conditionnellement (données présentes)
- [ ] `mss-clinical-synthesis` réutilisé (non dupliqué) par `mss-medical-document-modal` pour la vue structurée synthèse
- [ ] Tests unitaires : catégorisation par section (`filter`), détection criticité (`isCritical`), classes de sévérité, regroupement des antécédents, affichage dosage/parenté/dates
- [ ] Présentation mobile validée (cartes empilées + sections repliables, référence `/stitch-design`)
- [ ] Libellés FR en dur (parité client-angular)
- [ ] `data-testid` sur la bannière critique, les cartes, les en-têtes de section repliable
- [ ] **Aucune donnée de synthèse ni INS en clair dans les logs**

## Manual Test Plan

- Lancer l'app mobile : `cd Client/Mobile && npm start`, se connecter (session de test)
- Onglet Patients → sélectionner un patient ayant une **synthèse clinique riche**
  (allergies, problèmes actifs, traitements, antécédents) → onglet **Synthèse** visible
- Attendu : cartes par catégorie avec compteurs et couleurs de sévérité
- Patient avec **allergie critique** → bannière critique en tête, mise en avant
- Déplier une section d'antécédents (`mss-medical-history`) → contenu affiché ;
  ouvrir une autre section → la première se referme
- Vérifier l'affichage du dosage d'un traitement, du lien de parenté d'un
  antécédent familial, des dates formatées FR
- Ouvrir un **document de synthèse** depuis la timeline (task-133) → la vue
  structurée réutilise bien `mss-clinical-synthesis`
- Patient **sans synthèse** → onglet Synthèse absent

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (consultation de la synthèse clinique du patient)
- **Vague Ségur** : hors exigence DSR nouvelle — portage d'affichage ; le VSM / la synthèse (volets CI-SIS) sont traités en amont par `api-mail`/`interop-cda`
- **Exigences DSR honorées** : non applicable — aucune exigence DSR nouvelle côté mobile
- **INS** : aucune manipulation directe — éléments de synthèse rattachés au patient sélectionné (state hérité). INS jamais loggée ni en route mobile
- **Authentification PS** : session MSSanté existante, niveau eIDAS inchangé
- **Habilitations** : inchangées — consultation suivant l'habilitation du titulaire de la boîte
- **Interop CI-SIS** : éléments de synthèse issus de **CDA (VSM / synthèses)** parsés en amont (`interop-cda`) ; le mobile **ne parse aucun CDA**, il affiche le `MailMedicalDocumentSummaryDto` structuré. Sections/codes affichés tels quels
- **Tracé PGSSI-S** : consultation tracée côté `api-mail` (canal existant via le chargement des documents) ; pas de log client du contenu clinique
- **Consentement patient** : non applicable directement (consultation par le destinataire) ; opposition gérée en task-132
- **Référentiels métier** : SNOMED CT / CIM-10 / sections CDA éventuellement présents **dans** la synthèse — affichés tels quels, aucun codage produit par le mobile
- **Hébergement HDS** : oui — données servies par l'`api-mail` (backend HDS) ; transit HTTPS, pas de persistance disque sur l'appareil
- **AIPD / impact RGPD** : inchangé — nouveau canal de consultation mobile d'un traitement existant

## Branches
- `client-mobile` (pushed) : feat/task-135-mobile-clinical-synthesis — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-135-mobile-clinical-synthesis

## Develop log
- Repos touched : client-mobile
- DTOs published : no DTO change (MailMedicalDocumentSummaryDto déjà présent dans le modèle mobile)
- Interop published : no interop change
- Commits :
  - client-mobile : 27389a1 feat(mobile): patient clinical synthesis & medical history tab (task-135)
- Local build / test : ✓ client-mobile (`npm run build` 0 erreur ; `npm test` 231/231 verts, +18 vs 213)
- DOD self-check :
  - ✓ Build / Tests verts
  - ✓ Composants `mss-clinical-synthesis` + `mss-medical-history` (sélecteurs/noms identiques à client-angular)
  - ✓ Onglet « Synthèse » câblé dans `mss-patient-timeline`, affiché conditionnellement (`allSummaryItems().length > 0`) ; ion-segment Documents/Biologie/Synthèse
  - ✓ `mss-clinical-synthesis` réutilisé (non dupliqué) par `mss-medical-document-modal` : `structuredKind === 'synthesis'` prime quand `summaryItems` présents
  - ✓ Tests des calculs : catégorisation par section (filter → cards), détection criticité (isCritical + mots-clés sévérité), classes de sévérité, regroupement/ordre des antécédents, dosage/parenté/dates, status/severity classes, fallback nom, toggle accordéon
  - ✓ Présentation mobile : cartes empilées (ion-card) + sections repliables (ion-accordion-group, une ouverte à la fois)
  - ✓ Libellés FR en dur
  - ✓ data-testid (bannière critique, cartes `clinical-synthesis-card-*`, en-têtes de section `medical-history-section-*`, onglet synthèse)
  - ✓ Aucune donnée de synthèse ni INS loggée côté client
- Note de parité : logique de catégorisation (SECTION_TYPES → cartes), criticité (CRITICAL_SEVERITY_KEYWORDS), ordre/labels/icônes des sections portés fidèlement ; icônes design-system desktop → ionicons ; grille asymétrique desktop → empilement de cartes + accordéon mobile.
- Next step : /forge-simplify task-135

## Simplify log
- Repos passed : client-mobile
- Applied & committed : client-mobile: 2 files (6bc2337) — dédup template, iso-rendu (231/231 verts)
  - `otherCards` computed (`[...priorityCards, ...secondaryCards]`) → une seule boucle `@for` au lieu de deux blocs de markup byte-identiques (−31/+9 lignes)
- Skipped findings (noted, not applied) :
  - Extraire des utils date/section partagés (formatDateFr/formatDate/SECTION_*) — large, casse l'auto-suffisance/parité du miroir Angular (même arbitrage que task-134)
  - Fusionner la carte principale (allergies) dans la boucle commune — divergence réelle (branche empty-message + classe `--critical` par item) ; non fusionnée
- Rolled back (validation RED) : none
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*
- Build / tests : ✓ green on client-mobile (build 0 erreur ; 231/231 tests)
- Next step : /lint-mobile task-135 (api-mail & client-angular non touchés → /sonar et /lint-angular skip)

## Lint mobile log
- Baseline `npm run lint` (ng lint) : **All files pass linting** — 0 error, 0 warning
- Iterations run : 0 (nothing to fix)
- Fixes committed : none (tree clean)
- Build / tests : verts depuis /develop + /forge-simplify (build 0 erreur ; 231/231 tests)
- Next step : /review task-135

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/38 — label `awaiting-human-merge`

## Code Review Summary
- Verdict : **APPROVED** (0 blocking, 1 note non bloquante)
- client-mobile :
  - `mss-clinical-synthesis` — ✅ catégorisation par section, criticité (mots-clés sévérité), cartes principale/prioritaires/secondaires, sévérité colorée, bannière IPS ; dédup template (otherCards)
  - `mss-medical-history` — ✅ regroupement/ordre des sections, accordéon (une ouverte à la fois), dosage/parenté/dates FR, classes statut/sévérité
  - `mss-patient-timeline` — ✅ onglet Synthèse conditionnel (`allSummaryItems`), ion-segment Documents/Biologie/Synthèse
  - `mss-medical-document-modal` — ✅ réutilise `mss-clinical-synthesis` (vue structurée `synthesis`, non dupliquée)
  - tests — ✅ 18 nouveaux (catégorisation/criticité/regroupement/dosage/parenté/dates/classes/accordéon/câblage onglet/réutilisation modale)
- Note non bloquante : ergonomie petit écran (cartes empilées + accordéon) = vérification visuelle.
- Validation : build ✓ 0 erreur, tests ✓ 231/231, lint ✓ clean.

## Merged
- Date : 2026-06-29
- client-mobile : squash `5140eef` — PR #38 closed, remote branch `feat/task-135-mobile-clinical-synthesis` deleted (local kept)
- develop CI : no workflow configured on HealthPlatform.Mobile (N/A)
