# todo-task-016.md — Alignement fonctionnel Angular sur Blazor

**Repos**: client-angular
**Epic**: E009
**Dependencies**: aucune

> **Note automation** : `client-angular` est exclu de l'automation forge
> (TFS remote, gestion manuelle). `/start` ne creera pas de branche, `/review`
> ne buildera / testera / n'ouvrira pas de PR. Le humain gere le cycle
> completement en manuel dans WindSurf + TFS. La tache existe neanmoins pour
> tracer le travail et documenter l'ecart dans l'EPIC E009.

## Objectif

Le frontend Angular (legacy, deploye sur TFS) accuse un retard fonctionnel sur
le frontend Blazor qui sert de reference. Cette tache couvre l'alignement des
fonctionnalites majeures identifiees comme manquantes ou incompletes cote
Angular, afin qu'un medecin utilisant la version Angular dispose de la meme
valeur clinique qu'un medecin utilisant Blazor.

Le declencheur concret : lorsqu'un mail contient un document CDA de biologie,
Blazor affiche un onglet "Biologie" dans le viewer mail avec le rendu
structure (sections, valeurs anormales, filtres). Angular ne propose pas cet
onglet — le medecin doit telecharger la piece jointe pour lire la biologie,
ce qui casse le flux de lecture.

## Perimetre — ecarts a combler

### 1. Onglet "Biologie" dans le viewer mail (P0)

- **Blazor (reference)** : `Client/Blazor/Src/Modules/Mss/Plugin/Components/MailBodyComponent.razor`
  (L45-69) + `BiologyComponent.razor`. Quand `hasBiologyResults` est vrai, un
  onglet dynamique apparait a cote de l'onglet "Corps", rendant la biologie
  structuree (sections, valeurs anormales mises en evidence, filtres).
- **Angular (a faire)** : `libs/mss/src/features/mail/components/mail-body/`
  ne propose pas cet onglet. Il faut :
  - Detecter `hasBiologyResults` sur le mail selectionne
  - Ajouter un onglet dynamique "Biologie" dans le `mail-body`
  - Integrer un composant de rendu biologie (voir point 2)

### 2. `BiologyComponent` standalone reutilisable (P1)

- **Blazor (reference)** : `BiologyComponent.razor` (~364 lignes) — rendu
  autonome avec grilles, filtres, sections et mise en evidence des valeurs
  anormales, reutilisable dans Mail et Patient.
- **Angular (a faire)** : `BiologyTimelineComponent` existe
  (`libs/mss/src/features/patient/components/biology-timeline/`) mais est
  couple au contexte "Patient Timeline". Extraire un composant
  `BiologyComponent` reutilisable par Mail et Patient, sans dependre du
  contexte timeline.

### 3. Onglets dynamiques dans `PatientTimeline` (P1)

- **Blazor (reference)** : `PatientTimeline.razor` (L18-38) genere des
  onglets dynamiques selon les types de documents presents (Synthese
  Clinique, Synthese Biologie, Documents, Imagerie, CR hospitalier, etc.).
- **Angular (a faire)** : `libs/mss/src/features/patient/components/patient-timeline/`
  utilise des onglets statiques (`'documents' | 'biology' | 'synthesis'`).
  Generer les onglets dynamiquement selon `DocumentTypeFilter` (signal /
  computed), en conservant le tri et le filtrage actuels.

### 4. Rendu HTML structure des documents medicaux dans la modale (P0)

- **Blazor (reference)** : `MedicalDocumentModal` + `TimelineDocumentGroup`
  proposent un rendu HTML structure issu du CDA (sections, tableaux,
  resultats bio, syntheses) au-dela du simple PDF.
- **Angular (a faire)** : `libs/mss/src/features/patient/components/medical-document-modal/`
  existe mais n'expose que le PDF ou un toggle limite. Etendre le rendu
  structure par type de document (resultats bio, syntheses cliniques, etc.)
  en reutilisant les composants existants quand c'est possible.

### 5. Filtre `DocumentType` avance (P2)

- **Blazor (reference)** : `DocumentTypeFilter` enumerate finement les types
  (biologie, imagerie, CR hospitalier, etc.) et expose le rendu par
  categorie.
- **Angular (a faire)** : `DocumentType` enum existe
  (`libs/mss/src/core/models/patient.model.ts`) mais le filtre se limite a
  `'all'` ou une categorie. Etendre pour afficher / cacher les onglets
  correspondants en lien avec le point 3.

### 6. Timeline verticale avec dates dans la vue patient (P1)

- **Blazor (reference)** : `PatientTimeline.razor` rend une **timeline
  verticale** avec separateurs de periode (mois / annee) et dates
  positionnees le long d'un rail vertical (composant `timeline-documents`
  L79+, combine avec les separateurs de periode). La lecture chronologique
  est immediate.
- **Angular (a faire)** : `libs/mss/src/features/patient/components/patient-timeline/`
  et `timeline-period-separator/` existent mais le rendu est liste plate
  sans rail visuel vertical, sans dates positionnees sur l'axe. Il faut :
  - Reproduire le rail vertical (CSS flex / grid + pseudo-elements)
  - Afficher les dates sur l'axe (jour, mois, annee) avec regroupement par
    periode
  - Conserver les interactions existantes (clic document, filtres)

### 7. Synthese clinique en grille asymetrique multi-colonnes (P1)

- **Blazor (reference)** : `ClinicalSynthesisComponent.razor` utilise une
  grille `synthesis-grid-asymmetric` avec `grid-column-main` et des
  colonnes secondaires (allergies critiques en banniere, cartes par
  categorie : allergies, problemes actifs, traitements, antecedents,
  vaccinations). UX travaillee, lecture rapide par zone.
- **Angular (a faire)** : `libs/mss/src/features/patient/components/clinical-synthesis/`
  existe mais rend les sections en liste verticale simple. Il faut :
  - Reproduire la grille asymetrique (colonne principale + secondaires)
  - Reprendre les cartes avec headers colores par severite (warning,
    danger, info) et badges de comptage
  - Reprendre la banniere d'allergies critiques (`critical-allergies-card`)
    en tete de grille
  - Reprendre la banniere d'information (nombre de documents IPS sources +
    date de derniere MAJ)

### 8. Biologie : timeline horizontale avec courbes de tendance (P0)

- **Blazor (reference)** : `BiologyTimeline.razor` rend une **timeline
  horizontale** sous forme de grille matricielle :
  - Lignes = biomarqueurs (regroupes par sections : hemato, biochimie,
    etc.)
  - Colonnes = dates (jour/mois/annee, chronologique)
  - Colonne dediee **"Tendance"** avec sparkline / courbe de tendance par
    biomarqueur
  - Mise en evidence des valeurs anormales
  - Toolbar : KPI (total analyses + dates + anormales), toggle "anormaux
    seulement", filtre biomarqueur, selecteur de periode (3/6/12 mois /
    tout)
- **Angular (a faire)** : `libs/mss/src/features/patient/components/biology-timeline/`
  existe mais rend la biologie en liste verticale sans axe temporel
  horizontal ni sparkline. Il faut :
  - Reproduire la grille matricielle biomarqueurs x dates
  - Ajouter la colonne "Tendance" avec sparkline (SVG ou librairie legere
    type `ngx-charts` deja presente dans le projet si elle l'est, sinon
    SVG inline)
  - Reproduire la toolbar complete (KPI, toggle anormaux, filtre,
    selecteur de periode)
  - Conserver le groupement par sections de biomarqueurs

## Hors perimetre (a confirmer avec le PO)

- Fonctionnalites absentes des deux frontends (imagerie, CR hospitalier
  plein) : ne font PAS partie de cette tache d'alignement.
- `ManagementPage` (present en Blazor, absent en Angular) : non clinique,
  priorite faible, a traiter dans une tache dediee si besoin.
- `/settings` et `/signatures` presents en Angular mais absents de Blazor :
  pas a traiter ici (c'est Blazor qui pourrait etre aligne sur Angular, ou
  ne pas l'etre du tout).

## Exigence Segur couverte

- LGC.MSS/UX.03 — Visualisation structuree des documents CDA (biologie,
  syntheses cliniques) dans le viewer mail et le dossier patient
- LGC.MSS/UX.04 — Parite fonctionnelle entre frontends deployes

## References techniques

- Blazor Mail body : `Client/Blazor/Src/Modules/Mss/Plugin/Components/MailBodyComponent.razor`
- Blazor Biology : `Client/Blazor/Src/Modules/Mss/Plugin/Components/BiologyComponent.razor`
- Blazor Patient timeline : `Client/Blazor/Src/Modules/Mss/Plugin/Components/PatientTimeline.razor`
- Angular Mail body : `Client/Angular/front/libs/mss/src/features/mail/components/mail-body/`
- Angular Patient timeline : `Client/Angular/front/libs/mss/src/features/patient/components/patient-timeline/`
- Angular Biology timeline : `Client/Angular/front/libs/mss/src/features/patient/components/biology-timeline/`
- Angular Document type : `Client/Angular/front/libs/mss/src/core/models/patient.model.ts`

## Definition of Done

- [ ] Build Angular passe (0 errors) — `npm ci && npm run build` depuis
  `Client/Angular/front`
- [ ] Tests Angular passent (0 failures) — `npm test`
- [ ] Onglet dynamique "Biologie" affiche dans le viewer mail quand le mail
  selectionne contient au moins un document CDA de biologie
- [ ] Onglet "Biologie" cache quand aucun document de biologie n'est present
- [ ] `BiologyComponent` standalone reutilisable, sans dependance au contexte
  `PatientTimeline`, couvert par des tests unitaires (>= 3 tests : rendu sans
  donnees, rendu avec donnees, mise en evidence des valeurs anormales)
- [ ] Onglets dynamiques dans `PatientTimeline` generes a partir des types de
  documents presents, avec un test unitaire par type d'onglet genere
- [ ] Modale `MedicalDocumentModal` propose un rendu HTML structure pour au
  moins : biologie, synthese clinique, synthese medicale — avec fallback PDF
  pour les types non structures
- [ ] Filtre `DocumentType` expose au moins les memes categories que Blazor
  (biologie, imagerie, CR hospitalier, synthese clinique, synthese medicale,
  autres)
- [ ] Vue patient : timeline **verticale** avec rail visuel + dates
  positionnees sur l'axe + separateurs de periode, visuellement proche de
  Blazor (capture d'ecran comparative jointe a la PR)
- [ ] Synthese clinique : grille asymetrique multi-colonnes + cartes par
  categorie (allergies, problemes actifs, traitements, antecedents,
  vaccinations) + banniere allergies critiques + banniere info IPS, avec
  classes de severite (warning / danger / info)
- [ ] Biologie : grille **matricielle horizontale** biomarqueurs x dates
  avec colonne "Tendance" rendant une sparkline par biomarqueur + toolbar
  complete (KPI total/dates/anormales, toggle anormaux, filtre biomarqueur,
  selecteur de periode 3/6/12 mois/tout) + groupement par sections
- [ ] Composants UX (timeline rail, synthese grille, biologie sparkline)
  couverts par tests unitaires de rendu (>= 1 test par composant : rendu
  avec donnees representatives)
- [ ] Aucune regression visible sur les flux existants : liste des mails,
  ouverture d'un mail, patient timeline en vue "tous documents", recherche
  patient, widgets dashboard
- [ ] Data-testid sur tous les elements interactifs nouveaux (onglets,
  boutons de filtre, actions de la modale)
- [ ] Aucun hardcoded string en UI (tout via i18n)
- [ ] Types DTO Angular alignes sur les contracts backend (pas de drift avec
  `dtos-mss`)

## Manual Test Plan

**Pre-requis** :
- Backend `api-mail` demarre (`dotnet run` depuis `Api/Mail`)
- Seed de donnees avec au moins un mail contenant un document CDA de
  biologie + au moins un patient avec plusieurs types de documents

**Lancement Angular** :
- `cd Client/Angular/front`
- `npm start` (ou la commande locale equivalente)
- Ouvrir `http://localhost:4200`

**Test 1 — Onglet Biologie dans le mail** :
- Naviguer vers `/mail`
- Selectionner un mail contenant un document CDA de biologie
- Verifier : l'onglet "Biologie" apparait a cote de l'onglet "Corps"
- Cliquer sur l'onglet "Biologie" → verifier le rendu structure
  (sections, tableaux, valeurs anormales en rouge)
- Selectionner un mail SANS biologie → verifier que l'onglet n'apparait pas

**Test 2 — BiologyComponent reutilise** :
- Ouvrir la fiche patient correspondante
- Verifier que la biologie s'affiche dans la timeline patient avec le meme
  rendu que dans l'onglet mail (composant partage)

**Test 3 — Onglets dynamiques PatientTimeline** :
- Ouvrir un patient avec documents varies (bio + synthese + CR)
- Verifier qu'un onglet par type de document present est affiche
- Ouvrir un patient avec un seul type de documents → verifier qu'un seul
  onglet apparait

**Test 4 — Rendu HTML structure dans la modale** :
- Depuis une timeline patient, ouvrir un document de biologie dans la modale
- Verifier le rendu HTML structure (pas uniquement le PDF)
- Ouvrir un document de type non-structure (ex: PDF brut) → verifier le
  fallback PDF

**Test 5 — Filtre DocumentType** :
- Dans la timeline patient, ouvrir le filtre par type
- Verifier la presence des categories : biologie, imagerie, CR hospitalier,
  synthese clinique, synthese medicale, autres
- Filtrer sur "biologie" → verifier que seuls les documents de biologie
  restent visibles

**Test 6 — Timeline verticale patient** :
- Ouvrir la fiche patient (onglet "Documents")
- Verifier : rail visuel vertical, dates positionnees sur l'axe,
  separateurs de periode (ex: "Janvier 2026", "Decembre 2025")
- Comparer avec la capture Blazor equivalente → pas d'ecart UX majeur
- Cliquer sur une carte document → verifier que la modale s'ouvre

**Test 7 — Synthese clinique multi-colonnes** :
- Ouvrir un patient avec allergies + problemes actifs + traitements +
  antecedents (seed necessaire)
- Basculer sur l'onglet "Synthese Clinique"
- Verifier : grille asymetrique (colonne principale + secondaires), cartes
  avec headers colores par severite, badges de comptage
- Verifier : banniere "Allergies critiques" en haut si au moins une
  allergie critique est presente
- Verifier : banniere info "Synthese issue de X document(s) IPS — Derniere
  MAJ : JJ/MM/AAAA"
- Comparer avec la capture Blazor equivalente → pas d'ecart UX majeur

**Test 8 — Biologie timeline horizontale + sparkline** :
- Ouvrir un patient avec au moins 3 dates de biologie et plusieurs
  biomarqueurs (seed necessaire)
- Basculer sur l'onglet "Synthese Biologie"
- Verifier : grille matricielle (biomarqueurs en lignes, dates en colonnes)
- Verifier : colonne "Tendance" avec sparkline par biomarqueur (courbe
  visible)
- Verifier : KPI toolbar (total analyses, nombre de dates, nombre
  d'anormales)
- Activer le toggle "Anormaux" → verifier que seules les lignes avec au
  moins une valeur anormale restent visibles
- Taper un filtre biomarqueur → verifier le filtrage
- Changer le selecteur de periode (3/6/12 mois/tout) → verifier que les
  colonnes de dates sont filtrees en consequence
- Comparer avec la capture Blazor equivalente → pas d'ecart UX majeur

**Test 9 — Non regression** :
- Envoyer/recevoir un mail (flux complet)
- Rechercher un patient
- Ouvrir un dashboard widget
- Verifier l'absence de regression sur les flux existants

## Branches

- `client-angular` (local-only, managed manually) : la forge ne cree pas de
  branche — `client-angular` est entierement exclu de l'automation forge
  (TFS remote). Le humain cree la branche, implemente, push et ouvre la PR
  manuellement dans TFS + WindSurf. Convention de nom suggeree :
  `feat/task-016-alignement-angular-blazor`.

**Pre-flight** (effectue le 2026-04-22) : les 5 repos critiques non exclus
(`api-mail`, `client-blazor`, `dtos-mss`, `sdk`, `host`) sont sur `develop`.
`interop-cda` n'est pas clone localement (hors scope). `client-angular` est
exclu par regle du check de pre-flight.

## PRs

- `client-angular` : **managed manually by the human**.
  - Branche implementation : `feature/nova-rewriting-mss-fixes-20260410`
    (convention forge `feat/task-016-*` non utilisee — `client-angular` est
    exclu de l'automation forge, la convention de nommage n'est pas
    appliquee automatiquement)
  - Commit principal : `7199d98 Alignement avec blazor`
  - PR TFS : ouverte manuellement par le humain (URL a renseigner ici par
    le humain si besoin de tracabilite)

## Code Review Summary

**Code review automatique : NON EXECUTEE.** `client-angular` est
entierement exclu de l'automation forge (remote TFS) — la forge ne clone
pas, ne build pas, ne teste pas, ne review pas ce repo. La validation des
8 ecarts listes dans la Definition of Done a ete realisee manuellement par
le humain en WindSurf avant la confirmation d'Option A lors du `/review`.

**Validation DOD : deferee integralement au Manual Test Plan.** Tous les
items de la DOD (build Angular, tests Angular, onglet Biologie mail,
BiologyComponent standalone, onglets dynamiques timeline, rendu HTML
structure modal, filtre DocumentType, timeline verticale, synthese grille
asymetrique, biologie matricielle + sparkline, tests unitaires UX,
i18n, data-testid, alignement DTO) ont ete verifies par le humain en
local avant confirmation.

**Conformite HAG (regle 10)** : la forge n'a ni merge, ni pousse, ni
ouvert de PR — conforme. Le merge dans TFS reste l'action exclusive du
humain.
