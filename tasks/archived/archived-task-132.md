# todo-task-132.md — Vue patient mobile (1/4) : socle recherche + fiche + opposition

**Repos**: client-mobile
**Dependencies**: —
**Epic**: E012

## Objective

Remplacer le placeholder « Bientôt disponible » de l'onglet **Patients** du
`client-mobile` par le **socle de la vue patient**, porté en **miroir
structurel** de `client-angular` (`libs/mss/src/features/patient/`) : recherche
d'un patient, sélection, affichage de la **fiche démographique** et gestion de
l'**opposition MSSanté** (patient / professionnel).

US **frontend-only** : tous les endpoints `/api/v1/Patients/...` existent déjà
en production dans `api-mail` (`PatientsController`) et sont consommés tels
quels par `client-angular`. **Aucune modification backend ni DTO**. Le scope
est le seul repo `client-mobile` (parité d'affichage E012).

C'est la **première des 4 tasks** du portage de la vue patient
(socle → documents → biologie → synthèse). C'est une US **complète et
autonome** : une fois livrée, le médecin peut rechercher un patient, voir sa
fiche et gérer son opposition — valeur démontrable de bout en bout (règle 11
respectée).

## Travail de report — exigence de fidélité

Le portage doit être **soigné** : reproduire fidèlement la structure et les
**noms de composants** de `client-angular` (mêmes sélecteurs `mss-*` et mêmes
noms de classe), n'adapter que la **présentation** aux ergonomies Ionic mobile
(via `/stitch-design`). Réutiliser les **mêmes DTOs et endpoints** sans
modification. Architecture mobile cible : `src/app/features/patient/`
(miroir de `libs/mss/src/features/patient/`), composants `standalone`,
`ChangeDetectionStrategy.OnPush`, état par **signals** (convention
`MailStateService`).

## Composants à porter (noms identiques à client-angular)

| Sélecteur | Classe | Rôle |
|---|---|---|
| `mss-patient` | `MssPatientComponent` | Conteneur de la vue : orchestre recherche + fiche, tient l'état `selectedPatient`. Hébergé par la page `patients.page`. |
| `mss-patient-search` | `PatientSearchComponent` | Recherche par nom (debounce 300 ms), chargement initial des patients avec documents du jour, autocomplete, émet la sélection. |
| `mss-patient-card` | `PatientCardComponent` | Fiche démographique (nom, âge, sexe, contact) + badges/édition d'opposition MSSanté patient/professionnel. |
| `mss-patient-consent` | `PatientConsentComponent` | Affichage/édition autonome de l'opposition (réutilisable hors carte). |

## Services / état à créer (miroir conventions mobile)

- **`MssApiService`** (`src/app/core/services/mss-api.service.ts`) : ajouter
  - `searchPatients(lastName)` → `GET /api/v1/Patients/search?lastName=...`
  - `getPatientByIns(ins)` → `GET /api/v1/Patients/ins/{ins}`
  - `getPatientsWithDocsToday()` → `GET /api/v1/Patients/with-medical-docs/today`
  - `getPatientOpposition(ins)` → `GET /api/v1/Patients/ins/{ins}/opposition`
  - `updatePatientOpposition(ins, dto)` → `PUT /api/v1/Patients/ins/{ins}/opposition`
  - (optionnel) `advancedSearchPatients(filter)` → `POST /api/v1/Patients/search/advanced`
- **`PatientStateService`** + **`PatientEventService`**
  (`src/app/features/patient/services/`) : signals (`selectedPatient`,
  `searchResults`, `isLoading`, …) + bus d'évènements (sélection patient).
- **Modèles** : `patient.model.ts` existe déjà côté mobile
  (`MailPatientDto`, `SearchResultPatientDto`, `SearchFilterPatientDto`,
  `PagedResultDto<T>`) — compléter avec `PatientOppositionDto` si absent.

## Comportement attendu (parité Angular)

- À l'ouverture de l'onglet Patients : chargement des patients ayant des
  documents **aujourd'hui**, affichés en liste (`ion-list`).
- Barre de recherche (`ion-searchbar`) : saisie ≥ 2 caractères → recherche
  debouncée par nom ; résultats en liste sélectionnable.
- Sélection d'un patient → affichage de la **fiche** : nom complet, âge (calculé
  depuis la date de naissance), sexe (libellé FR), téléphone, email, adresse.
- **Opposition** : affichage des deux drapeaux (patient / professionnel) + date
  de dernière modification ; édition possible (toggles) → `PUT` opposition ;
  retour visuel succès/erreur (toast).
- États : chargement (`ion-progress-bar`/`ion-spinner`), liste vide
  (« Aucun patient »), erreur (toast/alerte via `extractProblemDetail`).

## Definition of Done

- [ ] Build passe (`npm ci && npm run build`) — 0 erreur
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`) — 0 échec
- [ ] Onglet Patients : placeholder remplacé par `mss-patient`
- [ ] Composants `mss-patient`, `mss-patient-search`, `mss-patient-card`, `mss-patient-consent` créés avec sélecteurs/noms **identiques** à client-angular
- [ ] `MssApiService` : 5 méthodes patient ajoutées + tests unitaires (succès + erreur, via `HttpTestingController`)
- [ ] Test de rendu pour `mss-patient-search` (recherche debouncée + sélection), `mss-patient-card` (affichage + toggle opposition)
- [ ] Test unitaire `PatientStateService` (sélection, reset)
- [ ] Libellés FR en dur (parité client-angular — pas de ngx-translate)
- [ ] `data-testid` sur searchbar, items de résultat, toggles d'opposition, conteneur fiche
- [ ] **Aucune donnée patient en clair dans les logs** (INS/NIR, nom, contact)
- [ ] **L'INS ne transite jamais via un paramètre de route/deep-link mobile** — sélection tenue en mémoire (state), pas dans l'URL
- [ ] Changement d'opposition tracé côté serveur (vérifier que le `PUT` est l'unique canal — pas de log client de l'INS)

## Manual Test Plan

- Lancer l'app mobile : `cd Client/Mobile && npm start`
- Se connecter avec une session MSSanté de test (api-mail de test avec patients)
- Ouvrir l'onglet **Patients**
- Attendu : liste des patients ayant des documents du jour
- Saisir un nom dans la recherche → résultats filtrés après debounce
- Sélectionner un patient → fiche affichée (nom, âge, sexe, contact)
- Vérifier les drapeaux d'opposition + date ; basculer un toggle → toast de
  confirmation, valeur persistée (recharger la fiche, la valeur tient)
- Rechercher un nom inexistant → message « Aucun patient », pas de crash
- Couper le réseau et rechercher → erreur lisible, pas de crash

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (consultation patient sur mobile MSSanté)
- **Vague Ségur** : hors exigence DSR nouvelle — portage d'affichage d'une capacité déjà référencée côté `client-angular`/`api-mail`
- **Exigences DSR honorées** : non applicable — aucune exigence DSR nouvelle ; identito-vigilance déjà couverte par le backend
- **INS** : affichage/identification d'un patient existant via INS déjà enregistrée. **Aucune récupération INSi ni qualification déclenchée par cette US** (lecture). L'INS transite dans le **path de l'API backend over HTTPS** (contrat existant), **jamais** dans les logs client, les libellés UI au-delà de l'usage prévu, ni une route/param mobile
- **Authentification PS** : aucune nouvelle authentification — session MSSanté du médecin déjà établie (PSC/e-CPS en amont), niveau eIDAS inchangé
- **Habilitations** : inchangées — l'accès patient suit l'habilitation du titulaire de la boîte MSSanté. Pas de délégation introduite
- **Interop CI-SIS** : non applicable — pas d'échange CDA/FHIR dans ce socle (démographie + opposition uniquement)
- **Tracé PGSSI-S** : la **consultation de fiche** et la **modification d'opposition** sont journalisées **côté `api-mail`** (canal existant) ; aucun log client de l'INS/des traits. Conservation selon politique backend
- **Consentement patient** : **l'opposition MSSanté est précisément le mécanisme d'opposition du patient** (patient / professionnel) — affichée et modifiable ; toute modification passe par le `PUT` opposition tracé serveur
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — les données patient proviennent de l'`api-mail` (backend HDS existant) ; transit HTTPS, pas de persistance disque sur l'appareil
- **AIPD / impact RGPD** : inchangé — nouveau canal de consultation mobile d'un traitement déjà en place ; pas de nouveau traitement

## Branches
- `client-mobile` (pushed) : feat/task-132-mobile-patient-socle — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-132-mobile-patient-socle

## Stitch design log

- Écrans concernés : `mss-patient` (onglet Patients), `patient-search`,
  `patient-card`, `patient-consent`. Design **porté structurellement** du
  client-angular (`features/patient`) : écran de recherche (searchbar + liste
  de résultats avatar/nom/âge/sexe/INS) puis fiche (en-tête identité + liste
  contact + bandeau d'opposition + bascules). Traduction Ionic
  (`ion-searchbar`/`ion-list`/`ion-item`/`ion-toggle`).
- `/stitch-design` : best-effort, non invoqué cette passe (référence visuelle =
  vue patient Angular existante, parité structurelle). Création/rafraîchissement
  Stitch dédié possible en suivi si besoin d'une maquette propre mobile.

## Develop log

- Repos touched : client-mobile
- DTOs published : no DTO change (DTOs patient déjà présents dans le modèle mobile)
- Interop published : no interop change
- Commits :
  - client-mobile : 430b8b9 feat(mobile): patient view socle — search + fiche + opposition (task-132)
- Local build / test : ✓ client-mobile (`npm run build` 0 erreur ; `npm test` 186/186 verts)
- DOD self-check :
  - ✓ Build / Tests verts
  - ✓ Onglet Patients : placeholder remplacé par `mss-patient`
  - ✓ Composants `mss-patient`, `mss-patient-search`, `mss-patient-card`, `mss-patient-consent` (sélecteurs/noms identiques à client-angular)
  - ✓ MssApiService : 5 méthodes patient + tests (succès + erreur, HttpTestingController)
  - ✓ Tests rendu/logique : patient-search (recherche debouncée + sélection), patient-card (affichage + bandeau opposition), patient-consent (load + toggle/save + erreur)
  - ✓ PatientStateService + test (sélection, clear, reset)
  - ✓ Libellés FR en dur
  - ✓ data-testid (searchbar, résultats, toggles opposition, fiche, statut)
  - ✓ Aucune donnée patient loggée côté client (aucun console.log)
  - ✓ INS jamais dans la route : sélection tenue dans PatientStateService (signal), pas de deep-link `?ins=` (≠ Angular, volontairement omis)
  - ✓ Opposition modifiée uniquement via le `PUT` (canal unique tracé serveur)
- Note de parité : la timeline documents est **hors socle** (task-133) ; le
  deep-link `?ins=` d'Angular est volontairement omis (garde-fou INS mobile).
  La logique opposition est **factorisée** dans `mss-patient-consent` (réutilisé
  par la carte) plutôt que dupliquée comme côté Angular.
- Next step : /forge-simplify task-132

## Simplify log
- Repos passed : client-mobile
- Applied & committed : client-mobile: 4 files (fced432)
  - Reuse : `getPatientGenderLabel` + `getPatientInitials` extraits dans `patient.model.ts` (dédup search + card)
  - Simplification : helper `setResults()` dans patient-search (handler de succès dédoublonné)
  - Efficacité/hygiène : `takeUntilDestroyed` ajouté aux 2 souscriptions de patient-consent (cohérence avec patient-search)
- Skipped findings (noted, not applied) :
  - Supprimer `reset()` de PatientStateService — **gardé** : diverge de `clearPatient()` dès task-133 (reset de l'état timeline à venir) ; référencé par le DOD
  - Fusionner `onPatientCleared`/`onSearchCleared` — gardés séparés (outputs distincts : card.closed vs search.searchCleared, peuvent diverger)
  - Router le clear via le `searchSubject` — introduirait un debounce 300 ms sur l'effacement (changement UX), double-appel inoffensif (switchMap annule)
  - Remonter l'opposition dans PatientStateService — généralisation spéculative (consommateur unique)
- Rolled back (validation RED) : none
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*
- Build / tests : ✓ green on client-mobile (build 0 erreur ; 186/186 tests)
- Next step : /lint-mobile task-132

## Lint mobile log
- Baseline `npm run lint` (ng lint) : **All files pass linting** — 0 error, 0 warning
- Iterations run : 0 (nothing to fix)
- Fixes committed : none (tree clean)
- Build / tests : verts depuis /develop + /forge-simplify (build 0 erreur ; 186/186 tests)
- Next step : /review task-132

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/35 — label `awaiting-human-merge`

## Code Review Summary
- Verdict : **APPROVED** (0 blocking, 1 note non bloquante)
- client-mobile :
  - `mss-api.service.ts` (5 méthodes patient) — ✅ co-localisées, encodage INS, HttpParams
  - `patient.model.ts` (helpers genderLabel/initials) — ✅ famille de helpers étendue
  - `mss-patient` + `patient-search` + `patient-card` + `patient-consent` — ✅ parité structurelle, opposition factorisée (consent réutilisé par la carte), takeUntilDestroyed
  - `PatientStateService` — ✅ état sélection (INS hors URL)
  - tests — ✅ service/state/search/card/consent
- Note non bloquante : éditeur d'opposition affiché en clair dans la fiche (choix UX mobile vs panneau repliable Angular).
- Validation : build ✓ 0 erreur, tests ✓ 186/186, lint ✓ clean.

## Merged
- Date : 2026-06-28
- `client-mobile` : squash commit `83bdc26d080000d7cebaa793f41bc0ade0d56ca5` — PR #35 mergée (squash), branche remote supprimée (locale conservée)
- develop CI : aucun workflow GitHub Actions configuré sur le repo (rien à vérifier ; PR « no checks reported », mergeState CLEAN au merge)
