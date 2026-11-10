# E023 — Maquettes Stitch de la recherche mobile

> Préalable à la rédaction des tasks **450** (mobile : formulaire et mode résultats) et **451** (mobile : lecture,
> portée, sélection, suggestions). Décision de l'humain du 2026-11-10 : les US mobiles s'écrivent **après** validation
> des maquettes.

## État au 2026-11-10

- Projet Stitch : `client-mobile` (id `10088502293310567548`), design system « Clinical Precision Design System »
  (`assets/7f352f2521964c6dacc9c7df62922990`).
- Trois `generate_screen_from_text` lancés le 2026-11-10 vers 07:25 UTC, **expirés côté MCP** (attendu).
- **Génération non matérialisée** : trois instantanés `get_project` (à +2,5, +6 et +12 minutes) ne montrent aucun nouvel
  écran (64 instances avant et après). Conformément à `agents/stitch-design.md`, aucune génération n'a été relancée.
- Ancien écran `mail-search` (`fd767eca895f41b1b30a8bc932cf40cf`) : conception d'avant la refonte (filtres en puces,
  recherche avancée repliable). À conserver pour comparaison, puis à supprimer ou renommer.

## À faire par l'humain

1. Dans l'interface Stitch, vérifier d'abord qu'aucun écran `mail-search`, `mail-search-results` ou
   `mail-search-suggestions` n'est apparu entre-temps (une génération tardive créerait un doublon).
2. Sinon, lancer les trois descriptions ci-dessous (Generate, appareil **Mobile**, design system « Clinical
   Precision »), puis étiqueter chaque écran avec son nom (`mail-search`, `mail-search-results`,
   `mail-search-suggestions`).
3. Valider ou corriger les maquettes, puis demander la rédaction de task-450 et task-451.

## Descriptions d'écran

### `mail-search` — formulaire de critères (task-442, task-443, mobile en task-450)

```text
Screen title: "mail-search". Mobile search-criteria form of a secure medical messaging app (MSSanté) for French general practitioners. All UI text in French. Fictitious data only.

Layout, top to bottom:
- Header: back arrow, title "Recherche".
- Search field "Rechercher dans les messages…" with, just under it, a compact scope selector "Tous les dossiers ▾" (alternative: "Dossier courant").
- A single-level form (no nested "advanced search" panel), grouped in titled sections with 16px spacing:
  1. "Statut": toggle chips "Non lus", "Importants", "Pièces jointes".
  2. "Contenu médical": chips "Tous les documents", "Biologie", "Biologie anormale" (subtle red accent), "Compte rendu", "Ordonnance", "Imagerie".
  3. "Patient": a selector row "Choisir un patient" with a person icon and chevron (opens a picker; patient is chosen from a list, never typed freely).
  4. "Expéditeur": selector row "Choisir des correspondants" (laboratoires, établissements, confrères) plus a text field "De (adresse)".
  5. "Période d'envoi": chips "Aujourd'hui", "7 jours", "30 jours", "Personnalisée".
  6. "Date du document médical": two date fields "Du" / "Au".
  7. "Objet" text field, "Nom de pièce jointe" text field.
- Sticky bottom action bar, full width, safe-area aware, two buttons side by side: secondary outlined "Réinitialiser les paramètres" and primary solid blue "Lancer la recherche".
Show the state where "Non lus" and "Biologie anormale" are selected and the search field contains "bilan lipidique". Clinical, sober, high legibility, 44px touch targets, consistent with the other client-mobile screens.
```

### `mail-search-results` — mode « Résultats de recherche » (task-445, task-446, task-447, task-448 ; mobile en 450/451)

```text
Screen title: "mail-search-results". Mobile "search results mode" of a secure medical messaging app (MSSanté) for French general practitioners, inspired by Outlook's search mode. All UI text in French. Fictitious data only.

Layout, top to bottom:
- Header: a close button "Fermer la recherche" (X icon + label) on the left, title "Résultats : 25 messages", a filter/edit-criteria icon on the right.
- Horizontal scrollable row of active-criteria chips, each removable with a small x: "catherine bernard", "Tous les dossiers", "Pièces jointes".
- Refine bar: quick toggle chips "Non lus", "Importants", "Biologie", and a sort selector on the right "Pertinence ▾" (alternative "Les plus récents").
- A row with a checkbox "Tout sélectionner".
- "Patients" strip: one card "BERNARD Catherine · née le 12/03/1956 · F", badge "INS qualifiée", "18 messages", chevron (opens the patient's messages). Never show the INS number.
- Section header "Tous les mots (12)": message rows with avatar initials, sender "Laboratoire Biomédical du Parc", date "08/11/2026", subject "Résultats bilan sanguin", a two-line snippet where the searched words "Catherine BERNARD" are highlighted in yellow, and two small badges: where it was found "Document médical" and the origin folder "Boîte de réception". Show 3 rows (another from "CH Saint-Joseph · Cardiologie", folder "Archives", found in "Objet").
- Section header "Une partie des mots (8)": 1 row, found in "Corps".
- Section header "Résultats proches (5)" with muted styling and caption "Proches par le sens": 1 row without highlight, badge "Proche par le sens".
- A "Voir plus" button at the end of the list.
Clinical, sober, high legibility, 56px min list rows, consistent with the existing client-mobile mail-list screen.
```

### `mail-search-suggestions` — suggestions pendant la frappe (task-449 ; mobile en task-451)

```text
Screen title: "mail-search-suggestions". Mobile search screen of a secure medical messaging app (MSSanté) for French general practitioners, showing type-ahead suggestions grouped by category while the doctor types. All UI text in French. Fictitious data only.

Layout:
- Header: back arrow, search field focused containing "bern" with a clear (x) button, scope selector "Tous les dossiers ▾" under it.
- Suggestion list grouped by category headers (label-md, muted), max 5 items each, in this order:
  1. "Patients": "BERNARD Catherine · née le 12/03/1956 · F" with badge "INS qualifiée"; "BERNARDIN Paul · né le 04/07/1949 · M". Person icon. Never show an INS number. Matched letters "Bern" in bold.
  2. "Correspondants": "Dr Bernadette Lefèvre · Cardiologie" with address under it "b.lefevre@ch-exemple.mssante.fr"; building icon for "Clinique Saint-Bernard".
  3. "Types de document": no match → category hidden (do not show it).
  4. "Recherches récentes": clock icon, "bernard biologie", "bernard compte rendu".
- At the bottom of the list, a row "Rechercher « bern » dans les messages" with a search icon (equivalent to pressing Enter).
Tapping a patient opens the patient's messages; tapping a correspondent adds a removable criterion chip. Clinical, sober, high legibility, 56px min rows, consistent with other client-mobile screens.
```
