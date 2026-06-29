# E012 — Changelogs (vue ingénierie)

> **Audience** : équipes techniques, backlog, dette.
> **Vue produit** : [E012-client-mobile-mssante.md](E012-client-mobile-mssante.md)
> **Dernière mise à jour** : 2026-06-29

---

## Historique détaillé des changelogs

### v1.19 — task-136 — Connexion CIBA e-CPS (RPPS + validation découplée) (2026-06-29)

- **PR** : [HealthPlatform.Mobile#39](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/39) — label `awaiting-human-merge`. Branche `feat/task-136-mobile-ciba-ecps-login`. Repo `client-mobile` uniquement (`**Single frontend**: true`). **Frontend-only** : l'endpoint proxy `POST /v1/auth/connect` est **déjà livré** (repos `psc-proxy-*` gérés manuellement, hors automation) ; aucun changement `api-mail`/DTO. Pas de dépendance.
- **`AuthService.connectCiba(rpps)`** : génère le binding message, valide le RPPS côté client (aucun appel réseau si invalide → `RppsValidationError`), `POST /auth/connect` `{ nationalId, bindingMessage, clientId: environment.authClientId, channel: 'MOBILE' }` en `withCredentials` (requête longue — polling serveur ≈ 2 min), puis `switchMap` → récupération du `TokenAggregate` via le cookie de session BFF et `tap` → mémorisation du RPPS. Retourne `CibaConnectHandle { bindingMessage, session$ }` (binding exposé **synchroniquement** pour l'affichage pendant l'attente).
- **`ciba.util.ts`** (helpers purs) : `CIBA_CHANNEL='MOBILE'`, `RPPS_REGEX=/^8\d{11}$/`, `RppsValidationError`, `isValidRpps`, `formatBindingMessage`/`generateBindingMessage` (bornes 00–99, normalisation modulo), `mapCibaError` (status → FR : 0 injoignable / 400 invalide / 404 inconnu / 408·504 timeout-non-validé / 409 déjà en cours / 503 IdP indisponible / défaut générique ; **ne réexpose jamais `detail`/`title`**).
- **`login.page`** : machine d'états `form`/`waiting`. Vue `form` = champ RPPS (pré-rempli via `authService.lastRpps`, modifiable) + bouton **principal** « Se connecter avec e-CPS » + lien **secondaire** « Autre moyen de connexion » (→ `loginPsc`). Vue `waiting` = binding code en grand + spinner + bouton **Annuler** (`unsubscribe` → interrompt le polling, retour `form`). `data-testid` sur tous les interactifs ; libellés FR en dur ; `FormsModule` ajouté au `LoginPageModule` (ngModel). Pré-remplissage RPPS persistant (`mobile_last_rpps` localStorage).
- **Réutilisation / altitude** : RPPS jamais loggé ni en URL (corps du POST uniquement). Mutualisation du pipeline `/auth/token`→session entre `refreshSession` et la connexion CIBA.
- **Simplify (`/forge-simplify`)** : extraction de `mintSessionFromCookie(mssApiUrl, emptyTokenError)` (réutilisé par `refreshSession` + connexion CIBA, axe reuse/altitude) ; suppression de l'état `submitting` write-only (la vue `form`/`waiting` pilote l'UI) ; fusion des règles SCSS dupliquées `.login-error`/`.session-expired` (commit `36aa64e`, −57/+27). Findings écartés : refactor `authentication.page`/`$exchangeCodeForToken` (hors diff) ; déplacement persistance RPPS vers `AuthSessionService` (ripple hors diff, nit marginal) ; suppression `formatBindingMessage` (gagne ses tests de bornes 00–99 exigés par la DOD) ; branche défensive `RppsValidationError` côté page (fallback bon marché).
- **Tests** : +18 → **263/263** verts. `ciba.util.spec` (bornes binding 00/05/99/overflow, `generateBindingMessage` toujours 2 chiffres + bornes via spy `Math.random`, `isValidRpps` valide/non-8/longueur/non-numérique/trim, `mapCibaError` par status + non-fuite) ; `auth.service.spec` connectCiba (succès e2e POST connect MOBILE→token cookie, RPPS invalide **sans réseau**, timeout 408, IdP 503, conflit 409, prefill) ; `login.page.spec` (prefill, RPPS invalide sans appel, succès→`/home`, mapping erreur→`form`, Annuler, lien secondaire PSC).
- **Build / lint** : `npm run build` ✓ 0 erreur (warning budget `login.page.scss` non bloquant, cohérent avec d'autres composants) ; `npm run lint` ✓ All files pass linting (0 fix nécessaire).
- **Stitch** : écran de référence `login` réutilisé + design system « Clinical Precision » ; génération d'un écran dédié `login-ecps` en timeout MCP (best-effort, non bloquant) — intention traduite en Ionic depuis la référence existante.
- **Commits** : 1da9212 (feature CIBA + tests), 36aa64e (simplify).
- **Conformité** : authentification PS via **e-CPS / CIBA** (canal `MOBILE`, validation découplée, eIDAS substantiel — Ségur V2 / PGSSI-S) ; `clientId` restreint à l'allowlist proxy ; **aucun RPPS en clair** (logs/URL/messages) ; erreurs `ProblemDetails` mappées en FR sans fuite ; journalisation probante longue durée assurée côté proxy/IdP. INS/contenu patient non applicables (authentification professionnelle).

---

### v1.18 — task-135 — Vue patient : synthèse clinique & antécédents (2026-06-29)

- **PR** : [HealthPlatform.Mobile#38](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/38) — label `awaiting-human-merge`. Branche `feat/task-135-mobile-clinical-synthesis`. Repo `client-mobile` uniquement. **Frontend-only** : les `MailMedicalDocumentSummaryDto` sont déjà fournis structurés (agrégés depuis les documents chargés en task-133), aucun changement `api-mail`/DTO. Dépend de task-133. **4/4 — clôt le portage de la vue patient mobile.**
- **`mss-clinical-synthesis`** (miroir fidèle de client-angular `ClinicalSynthesisComponent`) : `@Input` setter→signal (`summaryItems`, `ipsDocumentsCount`, `ipsLastUpdate`). Catégorisation par `sectionType` portée fidèlement via `filter(sectionTypes)` (Set lowercase) : `allergies` (Allergy/AllergyIntolerance), `mainCard` (allergies), `priorityCards` (ActiveProblem/Condition/Problem + Medication/MedicationStatement), `secondaryCards` (MedicalHistory/SurgicalHistory/PastIllness, Immunization/Vaccination, LifestyleFactor/SocialHistory, FamilyHistory) — cartes vides filtrées. Détection de criticité `isCritical` via `CRITICAL_SEVERITY_KEYWORDS` (severe/critical/high/grave/sévère/critique) → `criticalAllergies` + bannière. `ipsBanner` (compteur documents IPS), `severityClass` (danger/warning/info/neutral), `formatItemMeta` (dosage/fréquence/voie/dates onset-abatement/statut), `itemDisplayName` (fallback displayName→originalText→code), `formatDateFr`.
- **`mss-medical-history`** (miroir fidèle de client-angular `MedicalHistoryComponent`) : `@Input` setter→signal (`summaryItems`). `groupedItems` (regroupement par `sectionType`, tri `SECTION_ORDER` ActiveProblem→LifestyleFactor), `SECTION_LABELS`/`SECTION_ICONS` (icônes design-system desktop → ionicons), `getStatusClass`/`getSeverityClass` (heuristiques FR/EN), `isMedication`/`hasDosage`/`isFamilyHistory`, `formatDate`. **Sections repliables** via `ion-accordion-group` (mode `single` → une seule ouverte à la fois) ; `selectedSection` signal + `toggleSection`/`onAccordionChange`.
- **Ré-ergonomie mobile** : grille asymétrique multi-colonnes desktop → **empilement d'`ion-card`** (bannière critique + carte allergies + cartes prioritaires/secondaires colorées par sévérité via tokens `--app-*` + couleurs cliniques) ; détail antécédents → **accordéon Ionic**. Libellés FR en dur.
- **`mss-patient-timeline`** : onglet **Synthèse** câblé conditionnellement — `allSummaryItems` (agrégation des `summaryItems` des documents), `dynamicTabs` (Documents toujours ; Biologie si résultats ; Synthèse si éléments de synthèse), `ion-segment` Documents/Biologie/Synthèse ; l'onglet rend `mss-clinical-synthesis` + `mss-medical-history`.
- **Réutilisation (non duplication)** : `mss-medical-document-modal` réutilise `mss-clinical-synthesis` pour la **vue structurée de synthèse** — `structuredKind` retourne `'synthesis'` (prioritaire sur html/raw) quand le document porte des `summaryItems` ; nouveau `@case ('synthesis')` rendant le composant. Pas de duplication de la logique de synthèse.
- **Simplify (`/forge-simplify`)** : `otherCards` computed (`[...priorityCards, ...secondaryCards]`) → une seule boucle `@for` au lieu de deux blocs de markup byte-identiques (commit `6bc2337`, −31/+9 lignes, iso-rendu). Findings écartés : extraction d'utils date/section partagés (formatDateFr/formatDate/SECTION_* — casse l'auto-suffisance/parité du miroir Angular, même arbitrage que task-134) ; fusion de la carte allergies dans la boucle commune (divergence réelle : branche empty-message + classe `--critical` par item).
- **Tests** : +18 (213→231) — `mss-clinical-synthesis` (catégorisation par carte, cartes vides écartées, criticité + mots-clés sévérité, classes de sévérité, `formatItemMeta`, fallback nom, bannière IPS, état vide) ; `mss-medical-history` (regroupement/ordre, toggle accordéon, sync ionChange, labels/icônes, classes statut/sévérité, médication+dosage / parenté familiale, `formatDate` + fallback nom, classe item allergie/problème) ; `mss-patient-timeline` (onglet Synthèse affiché si éléments / `selectTab`) ; `mss-medical-document-modal` (vue `synthesis` prioritaire sur html). Total suite : **231/231** verts.
- **Build / lint** : `npm run build` ✓ 0 erreur ; `npm run lint` ✓ All files pass linting.
- **Commits** : 27389a1 (synthèse + antécédents + tests), 6bc2337 (simplify).
- **Conformité** : éléments de synthèse issus de **CDA (VSM / synthèses)** parsés en amont (`api-mail`/`interop-cda`) — le mobile **ne parse aucun CDA**, il affiche le `MailMedicalDocumentSummaryDto` structuré ; sections/codes (SNOMED CT/CIM-10) **affichés tels quels** ; **aucune donnée de synthèse ni INS loggée** côté client ; consultation tracée backend (PGSSI-S) ; auth PSC/e-CPS inchangée.

---

### v1.17 — task-134 — Vue patient : timeline biologie matricielle (2026-06-28)

- **PR** : [HealthPlatform.Mobile#37](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/37) — label `awaiting-human-merge`. Branche `feat/task-134-mobile-biology-timeline`. Repo `client-mobile` uniquement. **Frontend-only** : les `MailMedicalDocumentBiologyDto` sont déjà fournis structurés (agrégés depuis les documents chargés en task-133). Dépend de task-133. 3/4 de la vue patient.
- **`mss-biology-timeline`** (miroir fidèle de client-angular `BiologyTimelineComponent`, lui-même portage de Blazor `BiologyTimeline.razor`) : grille matricielle biomarqueurs (lignes, groupés par section ordonnée `SECTION_ORDER`) × dates (colonnes). **Calculs portés fidèlement** : `buildGridModel` (parse dates/valeurs `parseNumeric` rejetant `<>≤≥`, groupement code|nom, tri desc), `getTrend` (delta vs valeur précédente relatif à l'amplitude de référence → flèche/angle/couleur), `getStability` (≥3 valeurs → Stable/En hausse/En baisse), `buildSparkline` (SVG : segments + points + bande de référence, scaleX/scaleY), `getInterpretationClass` (N/L/H/LL/HH), `getTooltip`. Toolbar : filtre biomarqueur, bascule `showAbnormalOnly`, sélecteur de période (`BiologyPeriod` 3/6/12/0) avec **auto-sélection** selon l'étendue des données.
- **Ré-ergonomie mobile** (point délicat de la task) : `@Input` setter→signal (`biologyResults`), grille en **scroll horizontal** (`overflow-x:auto`) avec **colonne biomarqueur figée** (`position:sticky; left:0`), toolbar Ionic (`ion-searchbar` filtre, `ion-segment` période, bouton « Anormaux »), sparklines SVG conservées, variables CSS de couleur biologie (`--bio-color-*`). Libellés FR en dur.
- **`mss-patient-timeline`** : onglet **Biologie** câblé conditionnellement — `allBiologyResults` (agrégation des `biologyResults` des documents), `dynamicTabs` (Documents toujours ; Biologie si résultats), `activeTab`/`selectTab`, `ion-segment` Documents/Biologie affiché quand >1 onglet.
- **Simplify (`/forge-simplify`)** : `visibleDateSet` computed (le `Set` était reconstruit dans 5 méthodes/cycle CD) ; `getTrend` en `.find` sur tableau trié desc (au lieu de filter+sort) ; `getEntryForDate` en O(1) via Map `entriesByDate` par ligne ; helper `countAbnormalInRows` (commit `e64fe18`). Findings écartés : conversion setter→`effect()` (suggestion incorrecte — `effect()` ne trace pas un `@Input` non-signal) ; extraction d'utils date/biologie partagés (touche task-098/mail-header, casse l'auto-suffisance du miroir) ; constante `BIO_COLORS` (cosmétique).
- **Tests** : +12 (201→213) — `mss-biology-timeline` (classes d'interprétation, `formatRef`, build/ordre des sections, filtre nom, anormaux-uniquement, filtrage période, tendance baissière, stabilité Stable, modèle sparkline, toggle sparkline) ; `mss-patient-timeline` (onglet Biologie affiché si résultats / masqué sinon, `selectTab`). Total suite : **213/213** verts.
- **Build / lint** : `npm run build` ✓ 0 erreur ; `npm run lint` ✓ All files pass linting.
- **Commits** : 0c78742 (timeline biologie), e64fe18 (simplify).
- **Conformité** : résultats de biologie issus de **CDA CR-BIO** parsés en amont (`api-mail`/`interop-cda`) — le mobile **ne parse aucun CDA**, il affiche le `MailMedicalDocumentBiologyDto` structuré ; codes LOINC + interprétation HL7 (N/L/H/LL/HH) **affichés tels quels** ; **aucune valeur biologique ni INS loggée** côté client ; consultation tracée backend (PGSSI-S) ; auth PSC/e-CPS inchangée.

---

### v1.16 — task-133 — Vue patient : timeline documents médicaux + viewer (2026-06-28)

- **PR** : [HealthPlatform.Mobile#36](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/36) — label `awaiting-human-merge`. Branche `feat/task-133-mobile-patient-timeline`. Repo `client-mobile` uniquement. **Frontend-only** : endpoints déjà en production (`GET /api/v1/Patients/ins/{ins}/medical-documents` paginé, `getEmailContent`, `downloadAttachment`). Dépend de task-132 (socle). 2/4 de la vue patient.
- **`mss-api.getMailsByInsPaged(ins, page, pageSize)`** → `GET /api/v1/Patients/ins/{ins}/medical-documents?page=&pageSize=` → `PagedResultDto<MailDto>` (INS encodé). `getEmailContent` + `downloadAttachment` **réutilisés** (déjà présents, reuse before create).
- **`mss-patient-timeline`** (conteneur, miroir Angular) : `@Input patientIns` (charge sur changement, garde `lastLoadedIns`) ; pagination 10/page (`loadDocuments`/`loadMore` + `ion-infinite-scroll`) ; `mailIndex` (document→mail pour le PDF) ; computeds `allDocuments`/`filteredDocuments`/`documentGroups` (groupage par période, tri desc) ; `typeCounts`/`filterOptions` (chips de filtre, types présents seulement) ; `classifyDocument` (heuristiques catégorie/LOINC/titre, miroir Angular) **mise en cache** dans un computed Map (évite le double calcul typeCounts+matchesFilter) ; `loadMailsContent` via `forkJoin` (contenu des mails en parallèle). Seul l'onglet **Documents** est câblé (Biologie task-134, Synthèse task-135).
- **`mss-timeline-document-group`** : liste de documents sous un libellé de période, repliable (groupe + par document) ; icône/libellé de catégorie, badge version CDA (≠ « 1 »), praticien, badge « Biologie », bouton d'ouverture ; aperçu du corps `[innerHTML]` **assaini par Angular** (pas de bypass).
- **`mss-timeline-period-separator`** : séparateur de période (template inline).
- **`mss-medical-document-modal`** : `ion-modal` plein écran, `@Input document/visible/folderPath/mailUid`, `ngOnChanges` + garde `loadedPdfKey` ; **PDF** récupéré en blob (`downloadAttachment`), rendu en `<iframe>` via `bypassSecurityTrustResourceUrl` (sur notre propre blob), **Object URL révoqué** à la fermeture/au masquage/au `ngOnDestroy`/après téléchargement ; vue structurée HTML assaini (`[innerHTML]`) / texte brut / aucun. Téléchargement via l'util partagé `downloadBlob`. Biologie/synthèse détaillées = task-134/135.
- **Réutilisation (`/forge-simplify`)** : util `downloadBlob` extrait dans `core/utils/blob-download.util.ts` (dédup du `triggerDownload` du modal **et** du `mail-attachment` existant) ; `classifyDocument` mise en cache (commit `4728af6`). Findings écartés : conversion en signal-inputs+effect (convention mobile = `@Input`/`ngOnChanges`), extraction helpers blob-URL/date (large, pré-existant), `typeLabels` au modèle (consommateur unique), factorisation `loadDocuments`/`loadMore` (différences sémantiques).
- **Câblage** : `mss-patient-timeline` ajouté sous la fiche dans `mss-patient`.
- **Tests** : +15 (186→201) — `mss-api` (params page/pageSize) ; `patient-timeline` (groupement par période, filtre par type + filterOptions, pagination page 2, ouverture/fermeture du modal) ; `medical-document-modal` (vue structurée html/raw/none, fetch PDF + URL sûre, révocation du blob à la fermeture/au masquage) ; `timeline-document-group` (toggles, émission open, badge version, catégorie). Total suite : **201/201** verts.
- **Build / lint** : `npm run build` ✓ 0 erreur ; `npm run lint` ✓ All files pass linting.
- **Commits** : 8da8323 (timeline + viewer), 4728af6 (simplify).
- **Conformité** : documents = CDA parsés **côté `api-mail`/`interop-cda`** (le mobile ne parse aucun CDA) ; HTML de document **assaini** avant rendu (`[innerHTML]` Angular) ; **PDF en blob mémoire, Object URL révoqué** (pas de persistance disque non maîtrisée) ; INS clé d'appel API over HTTPS, **jamais loggée ni en route** ; consultation tracée côté backend (PGSSI-S) ; auth PSC/e-CPS inchangée.

---

### v1.15 — task-132 — Vue patient : socle recherche + fiche + opposition (2026-06-28)

- **PR** : [HealthPlatform.Mobile#35](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/35) — label `awaiting-human-merge`. Branche `feat/task-132-mobile-patient-socle`. Repo `client-mobile` uniquement. **Frontend-only** : endpoints `/api/v1/Patients/...` déjà en production (consommés par `client-angular`), aucun changement `api-mail`/DTO. 1/4 du portage de la vue patient.
- **`MssApiService`** : `getPatientsWithDocsToday()`, `getPatientByIns(ins)`, `searchPatients(lastName)`, `getPatientOpposition(ins)`, `updatePatientOpposition(ins, dto)` (endpoints `/api/v1/Patients/...`, INS encodé, `HttpParams` pour `lastName`). DTOs patient déjà présents dans `core/models/patient.model.ts`.
- **`mss-patient`** (`features/patient/`, conteneur, miroir Angular) : tant qu'aucun patient n'est sélectionné → recherche ; sinon → fiche. État (`selectedPatient`) tenu par **`PatientStateService`** (signal), **jamais dans l'URL** (le deep-link `?ins=` d'Angular est volontairement omis — garde-fou INS mobile).
- **`mss-patient-search`** : `ion-searchbar` + flux RxJS `Subject` `debounceTime(300)`/`distinctUntilChanged`/`switchMap` (saisie vide → docs du jour, sinon `searchPatients`) ; chargement initial des patients du jour ; liste `ion-item` (avatar initiales, nom, âge, sexe, INS) ; émet `patientSelected`.
- **`mss-patient-card`** : fiche démographique (`getPatientFullName`/`getPatientAge`/`getPatientGenderLabel`/`getPatientInitials` réutilisés) + bandeau de statut d'opposition ; **réutilise `mss-patient-consent`** pour l'édition (pas de duplication de la logique load/save, contrairement à Angular qui la dupliquait dans la carte).
- **`mss-patient-consent`** : charge l'opposition par INS (`ngOnChanges`, garde `lastLoadedIns`), deux `ion-toggle`, persiste chaque changement par le **`PUT` opposition** (canal unique tracé serveur), toast succès/erreur (`extractProblemDetail`), émet `oppositionChanged`. `takeUntilDestroyed` sur les souscriptions.
- **Onglet Patients** : `patients.page` passe d'écran placeholder à hôte mince projetant `mss-patient` (`PatientsPageModule` importe le composant standalone).
- **Helpers partagés** ajoutés à `patient.model.ts` : `getPatientGenderLabel`, `getPatientInitials` (dédup search/card, rejoignent `getPatientFullName`/`getPatientAge`).
- **Tests** : +28 (158→186) — `mss-api` (5 méthodes patient + propagation d'erreur) ; `PatientStateService` (sélection/clear/reset) ; `patient-search` (chargement initial, recherche debouncée `fakeAsync`, fallback docs-du-jour, sélection, helpers) ; `patient-card` (démographie, libellé sexe, bandeau opposition, close) ; `patient-consent` (load + emit, garde re-load, save PUT + toast, RAZ date, toast d'erreur). Total suite : **186/186** verts.
- **Build / lint** : `npm run build` ✓ 0 erreur ; `npm run lint` ✓ All files pass linting.
- **Simplify (`/forge-simplify`)** : extraction `getPatientGenderLabel`/`getPatientInitials` (reuse), helper `setResults()` dans patient-search, `takeUntilDestroyed` ajouté à patient-consent (commit `fced432`). Findings écartés : suppression de `reset()` (diverge dès task-133), fusion des handlers clear (outputs distincts), routage du clear via le subject (debounce indésirable), remontée de l'opposition dans le state (spéculatif).
- **Commits** : 430b8b9 (socle + tests), fced432 (simplify).
- **Conformité** : données patient = DSCP servies par l'`api-mail` (HDS), transit HTTPS, pas de persistance disque mobile ; **INS jamais loggée ni en route mobile** (sélection en state) ; opposition (mécanisme d'opposition du patient) modifiée uniquement via le `PUT` tracé serveur ; auth PSC/e-CPS inchangée ; consultation/modification tracées côté backend (PGSSI-S). Hors socle : timeline documents (task-133), biologie (task-134), synthèse clinique (task-135).

---

### v1.14 — task-131 — Synthèse IA d'un email (panneau détail) (2026-06-28)

- **PR** : [HealthPlatform.Mobile#34](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/34) — label `awaiting-human-merge`. Branche `feat/task-131-mobile-ai-email-summary`. Repo `client-mobile` uniquement. **Frontend-only** : endpoint backend déjà en production (consommé par `client-angular`), aucun changement `api-mail`/DTO.
- **`mss-api.getEmailSummary(folderPath, uid)`** → `GET /api/v1/mail/folders/{folder}/emails/summary/{uid}` → `MailSummaryDto` (`uid`, `folderPath`, `from`, `markdownSummary`). Nouveau modèle `core/models/mail-summary.model.ts` (miroir TS du `MailSummaryDto` C#).
- **`mss-mail-summary`** (`features/mail/components/mail-summary/`, miroir du composant Angular) : `@Input` `mail` + `content` (l'identité patient vient de `content.medicalDocuments[0]`, le contenu étant chargé séparément côté mobile, ≠ Angular où il est porté par `mail.content`). Signaux `isLoading`/`summary`/`error`/`notAvailable` ; chargement sur changement d'`uid` (garde `lastLoadedUid`) ; `retry()`. En-tête : `displayTitle` (titre doc médical sinon sujet), `patientDisplay` (réutilise le helper `getPatientAge`), `practitionerDisplay`, `senderDisplay`. Corps : `markdownToHtml` (échappement `&`/`<`/`>` **avant** substitution markdown → anti-XSS) puis `DomSanitizer.bypassSecurityTrustHtml`.
- **Cas 404** (`ProblemDetails` « AI summary is not available », pipeline IA désactivé) → état neutre `notAvailable` (« Synthèse IA non disponible »), **pas** d'alerte d'échec. Autres erreurs → message via `extractProblemDetail` + bouton « Réessayer ».
- **`mss-mail-detail`** : déclencheur « Synthèse IA » (icône `sparkles-outline`, `data-testid="detail-summary-toggle"`) + panneau repliable (`showSummary`/`toggleSummary`) rendu via `@if`. `data-testid` : `detail-summary-toggle`, `detail-summary-panel`, `summary-content`/`summary-loading`/`summary-unavailable`/`summary-error`/`summary-retry`.
- **Tests** : 12 nouveaux — `mss-api` (GET summary endpoint encodé ; propagation 404) ; `mail-summary` (succès, 404→neutre, erreur non-404, rechargement sur uid, retry, fallback titre, patient/praticien, échappement markdown anti-XSS). Total suite : **162/162** verts.
- **Build / lint** : `npm run build` ✓ 0 erreur ; `npm run lint` ✓ All files pass linting.
- **Simplify (`/forge-simplify`)** : réutilisation du helper existant `getPatientAge` au lieu d'un `calculateAge` privé dupliqué (commit `8f4314d`). Findings écartés : retrait du `DatePipe` (faux positif — pipe `| date` utilisé dans le template), extraction du 404 vers le service / de `markdownToHtml` en util (design spéculatif, consommateur unique).
- **Commits** : 8a37dcb (feature + tests), 8f4314d (simplify).
- **Conformité** : synthèse = donnée de santé produite/hébergée par l'`api-mail` (HDS) ; transit HTTPS, pas de persistance disque mobile ; **aucune donnée de santé loggée** côté client (synthèse, patient, INS) ; consultation tracée côté backend (PGSSI-S) ; auth PSC/e-CPS inchangée. Markdown IA assaini avant rendu (anti-XSS).

---

### v1.13 — task-108 — Vue Conversations (threads) (2026-06-19)

- **PR** : [HealthPlatform.Mobile#13](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/13) — label `awaiting-human-merge`. Branche `feat/task-108-mobile-conversation-threads`. Repo `client-mobile` uniquement. Clôt le batch issu de l'analyse différentielle angular↔mobile.
- **`mss-api.getThread(messageId)`** → `GET /api/v1/mail/thread/{messageId}` → `MailThreadInfoDto`.
- **`mail-state`** : `MailViewMode` (List/Conversation) ; `conversationList` (computed : en Conversation, racines uniquement = `isThreadRoot` ou mails hors fil) ; `expandedThreadId` + `threadChildren` ; `expandThread`/`collapseThread`/`isThreadExpanded` ; `setMailViewMode` replie le fil ouvert.
- **`mss-mail-header`** : inputs `threadCount`/`isExpanded`/`isThreadChild`, output `toggleThread` ; chip « N messages » + chevron sur une racine à plusieurs messages (mode Conversation) ; indentation des enfants.
- **`mss-mail-list`** : rend `conversationList` ; en Conversation, dépliage d'une racine affiche ses enfants (`getThread` à la demande, pas de reload au repliage) ; enfants ouverts via `MailEventService.requestSelectByUid$` (→ navigation détail par uid+dossier).
- **Inbox** : segment **Liste / Conversation** (`onViewModeChange`) ; abonnement `requestSelectByUid$` → navigation `/mail/{folder}/{uid}`.
- **Tests** : 6 nouveaux — `mss-api.getThread` (GET messageId encodé) ; `mail-state` (conversationList roots, expand/collapse + children, changement de mode replie) ; `mss-mail-header` (chip/chevron sur racine multi-messages, émission `toggleThread`). Total suite : **106/106** verts.
- **Build / lint** : `npm run build` ✓, `npm run lint` ✓ clean.
- **Commit** : a707509.
- **Conformité** : regroupement par en-têtes RFC-5322 (In-Reply-To/References) ; aucune donnée de santé en clair.

---

### v1.12 — task-107 — Notifications nouveaux mails (SSE in-app) (2026-06-19)

- **PR** : [HealthPlatform.Mobile#12](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/12) — label `awaiting-human-merge`. Branche `feat/task-107-mobile-new-mail-notifications`. Repo `client-mobile` uniquement. Issu de l'analyse différentielle.
- **Périmètre** : notification **in-app** (parité angular `NotificationStreamService`). Les **push natives Capacitor** (FCM/APNs + enregistrement device backend + `devops`) sont un **suivi infra hors US**.
- **`NotificationStreamService`** : `EventSource` `…/api/v1/mail/notifications/stream?token=` **scope-utilisateur** (distinct du folder-scoped de task-104), `connect`/`disconnect`, flux `notification$`, ré-entrée `NgZone`, **connexion unique** (anti même-URL), fermeture au `ngOnDestroy`, reconnexion native sur coupure. Lit token/baseURL depuis `AuthSessionService`.
- **Modèle** : `NotificationPayloadDto` (`NotificationKind` NewMail/AbnormalBiology, `UrgencyLevel`, title/body/mailUid/folderPath/receivedAt/playSound/showDesktop).
- **Inbox** : `connect()` à l'entrée ; **toast** à chaque notification (rouge si biologie anormale) ; sur un `NewMail` du **dossier courant** (hors recherche), `getEmails([mailUid])` + `appendEmails` (dédup + re-tri récent en tête, sans saut de scroll) ; `disconnect()` au destroy.
- **Tests** : 4 nouveaux — `NotificationStreamService` (URL+token, parsing `notification`, connexion unique, close au disconnect) via `FakeEventSource`. Total suite : **100/100** verts.
- **Build / lint** : `npm run build` ✓, `npm run lint` ✓ clean.
- **Commit** : 685cfda.
- **Conformité** : stream authentifié (JWT en `?token=`, jamais loggé) ; aucune donnée de santé dans le toast/les logs.

---

### v1.11 — task-106 — Recherche d'emails (2026-06-19)

- **PR** : [HealthPlatform.Mobile#11](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/11) — label `awaiting-human-merge`. Branche `feat/task-106-mobile-email-search`. Repo `client-mobile` uniquement. Issu de l'analyse différentielle.
- **`mss-api.semanticSearch(request)`** → `POST /api/v1/search/semantic` → `SearchResponseDto` (uids). Modèles `SearchRequestDto`/`SearchResponseDto`/`SearchFilterDto` (miroir).
- **`mss-mail-search`** : `ion-searchbar` + chips de filtres rapides (Non lus, Pièces jointes, Document médical, Biologie), **debounce 300ms** ; émet `searchResults` (uids) / `searchCleared` / `searchFailed`. Requête : `maxResults 50`, `minSimilarity 0.1`, `searchType/searchMode 3`, `folderPath` courant (parité angular).
- **Inbox** : héberge la recherche ; charge les uids résultats dans la liste en **mode recherche** qui suspend la pagination scroll (`mail-state.isSearchActive` → `hasMore` faux) ; `searchCleared` restaure la vue dossier paginée ; `searchFailed` → bandeau d'erreur.
- **Tests** : 6 nouveaux — `mss-api.semanticSearch` (POST endpoint) ; `mss-mail-search` (recherche debouncée + émission uids, filtres dans la requête, `searchCleared` sur critères vides, `clear()`) ; `mail-state` (pagination suspendue si recherche active). Total suite : **96/96** verts.
- **Build / lint** : `npm run build` ✓, `npm run lint` ✓ clean.
- **Commit** : 3385011.
- **Conformité** : la requête de recherche **n'est jamais loggée** (peut contenir un nom/identité patient) ; recherche scope-utilisateur ; aucun INS en clair.

---

### v1.10 — task-105 — Accusé de lecture : réponse sur consentement (2026-06-19)

- **PR** : [HealthPlatform.Mobile#10](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/10) — label `awaiting-human-merge`. Branche `feat/task-105-mobile-read-receipt-response`. Repo `client-mobile` uniquement. Issu de l'analyse différentielle angular↔mobile.
- **`mss-api.sendReadReceipt(folder, uid)`** → `POST /api/v1/mail/folders/{folder}/emails/{uid}/sendreadreceipt`.
- **`mss-mail-detail`** : getter `showReadReceiptPrompt` (mail reçu avec `requestReadReceipt`, hors « Envoyés » et brouillon, non déjà acquitté dans la session) ; bandeau + bouton « Envoyer l'accusé » ; `sendReadReceipt()` émet **uniquement sur action du PS** (consentement), toast au succès, `ProblemDetails` à l'échec, idempotent via un `Set<uid>` de session.
- **Tests** : 3 nouveaux — `mss-api.sendReadReceipt` (POST endpoint) ; `mss-mail-detail` (prompt visible seulement sur mail reçu demandeur / masqué sur sent/draft/sans-demande ; envoi → POST + masquage). Total suite : **90/90** verts.
- **Build / lint** : `npm run build` ✓, `npm run lint` ✓ clean.
- **Commit** : 571a876.
- **Conformité** : accusé MSSanté émis sur consentement explicite (jamais auto) ; imputé au PS authentifié (PSC) ; émission tracée backend (PGSSI-S) ; aucun RPPS dans les en-têtes ; aucune donnée de santé en clair.

---

### v1.9 — task-104 — Enrichissement + mises à jour live SSE (2026-06-19)

- **PR** : [HealthPlatform.Mobile#9](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/9) — label `awaiting-human-merge`. Branche `feat/task-104-mobile-enrichment-sse-parity`. Repo `client-mobile` uniquement. Dépend de task-100, task-102.
- **`mss-api.enrichEmailsSync(folder, uids)`** → `POST /api/v1/mail/folders/{folder}/emails/enrich/sync` (body = UIDs, `responseType: 'text'` → void).
- **`MailEventsStreamService`** (core, parité Angular) : `EventSource` folder-scoped vers `…/api/v1/mail/events/stream?folder=&token=` (JWT en query, EventSource ne pose pas d'en-tête) ; `connect`/`disconnect`/`setFolder` ; flux `emailsEnriched$` / `tagsUpdated$` ; ré-entrée `NgZone` (callbacks hors zone) ; **reconnexion** au changement de dossier, **anti double-connexion** (même URL ignorée), `close()` au `ngOnDestroy`. Lit le token/baseURL depuis `AuthSessionService`.
- **Modèle** : `core/models/mail-event.model.ts` (`EmailsEnrichedEvent` {folder, emails[]}, `TagsUpdatedEvent` {folder, uid, tags[]}).
- **`inbox.page`** : enrichit les UIDs de chaque lot chargé ; `setFolder`+`connect` du stream sur le dossier courant ; **patch in-place** de la liste sur `EmailsEnriched` (`updateMailInList` par uid, garde sur le dossier) et `TagsUpdated` ; `stream.disconnect()` au destroy.
- **`mail-detail.page`** : si le mail ouvert est inclus dans un `EmailsEnriched` (même dossier+uid), recharge son contenu (`getEmailContent`) sans navigation.
- **Tests** : 6 nouveaux — `MailEventsStreamService` (URL folder-scoped + token, parsing `EmailsEnriched`/`TagsUpdated`, reconnexion au changement de dossier, pas de réouverture même dossier, close au disconnect) via un `FakeEventSource` ; `mss-api.enrichEmailsSync` (POST body UIDs, responseType text). Total suite : **87/87** verts.
- **Build / lint** : `npm run build` ✓, `npm run lint` ✓ clean.
- **Commit** : ff624ca.
- **Conformité** : flux SSE authentifié (JWT en `?token=`, jamais loggé) ; identité récupérée serveur-side ; aucune donnée de santé en clair.

---

### v1.8 — task-103 — Pagination inbox orientée scroll (2026-06-19)

- **PR** : [HealthPlatform.Mobile#8](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/8) — label `awaiting-human-merge`. Branche `feat/task-103-mobile-inbox-pagination-scroll`. Repo `client-mobile` uniquement.
- **Étude** : `getFolder` renvoie déjà **tous** les UIDs du dossier → pagination **côté client** sur la liste triée desc, **sans évolution backend**. UX retenue : infinite scroll + fin-de-liste + retry. Lot = 30.
- **`mail-state`** : `pagedUids` + `pageCursor` (privés), `PAGE_SIZE=30`, `hasMore` (computed), `isLoadingMore` ; `startPaging(sortedUids)` (RAZ emails+curseur), `nextUidPage()` (lot suivant + avance), `appendEmails(mails)` (dédup par `uid`), `rewindPage(count)` (rollback du curseur sur échec).
- **`inbox.page`** : `loadEmailsForFolder` charge tous les UIDs triés → `startPaging` → 1er lot ; `loadNextPage()` (append, garde `isLoadingMore`, rollback `rewindPage` sur erreur) ; `ion-infinite-scroll [disabled]="!hasMore()"` (anti-double-trigger) ; état « Fin de la liste » ; bandeau d'erreur + **bouton Réessayer** (rejoue le même lot, pas de saut/doublon).
- **Tests** : 4 nouveaux (mail-state) — pagination par lots + fin de liste, append+dédup, **rollback erreur→retry refetch le même lot**, `startPaging` réinitialise. Total suite : **81/81** verts.
- **Build / lint** : `npm run build` ✓, `npm run lint` ✓ clean.
- **Commit** : 10d9149.
- **Conformité** : pas de changement d'auth ; aucune donnée de santé loggée ; amélioration ergonomique de consultation.

---

### v1.7 — task-102 — Refresh de session JWT + rejeu (2026-06-18)

- **PR** : [HealthPlatform.Mobile#7](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/7) — label `awaiting-human-merge`. Branche `feat/task-102-mobile-refresh-session-jwt`. Repo `client-mobile` uniquement. Dépend de task-100.
- **Décision (humain)** : refresh = **re-POST `/auth/token` (withCredentials, sans `code`)** → `TokenAggregate`, le BFF d'auth (hors workspace) mintant un nouvel access token via le cookie de session.
- **`MssHeadersInterceptor`** : détection centralisée d'expiration (`isSessionExpired` = `401` OU détail ProblemDetails « expired / refresh your session ») sur les requêtes API MSS ; **single-flight refresh** (`isRefreshing` + `BehaviorSubject<AuthSession|null>`), rejeu de la requête initiale avec en-têtes frais, **file d'attente** des requêtes concurrentes (un seul refresh effectif), **anti-boucle** via `HttpContextToken RETRIED` (max 1 rejeu). Échec refresh → `authSession.logout()` + `router.navigateByUrl('/login?expired=1')`. `AuthService` résolu paresseusement via `Injector` (évite le cycle HttpClient↔interceptor).
- **`AuthService.refreshSession()`** : `POST /auth/token` (FormData vide, `withCredentials`) → reconstruit la session (`mssApiUrl` courant conservé, JWT redécodé) et la persiste.
- **`login.page`** : bannière « Votre session a expiré. Veuillez vous reconnecter. » sur `?expired=1`.
- **Tests** : 7 nouveaux — interceptor (en-tête bearer, refresh ok→rejeu avec nouveau token, refresh ko→logout+redirect, **concurrence = 1 seul refresh**, anti-boucle), `AuthService.refreshSession` (re-POST `/auth/token` sans `code`, cookie, rebuild+save ; erreur si pas de session). Total suite : **77/77** verts.
- **Build / lint** : `npm run build` ✓, `npm run lint` ✓ clean.
- **Commit** : 850ef64.
- **Conformité** : aucun token ni donnée de santé loggé ; gestion d'expiration centralisée ; PSC/e-CPS inchangé (continuité de session).

---

### v1.6 — task-101 — HTML CDA responsive mobile (interop-cda) (2026-06-18)

- **PR** : [interop.cda.parser#6](https://github.com/codengine-technologies/interop.cda.parser/pull/6) — label `awaiting-human-merge`. Branche `feat/task-101-cda-html-responsive-mobile`. Repo `interop-cda` uniquement (mono-repo justifié : le rendu HTML vit dans le package, pas d'API/DTO modifié).
- **Feuille réellement modifiée** : `src/Interop.Cda/resources/html/cda_asip.xsl` — confirmée active via `Properties/Resources.resx` (`ResXFileRef` → `Resources.cda_asip`), écrite en tempDir et chargée par `CDAHtmlTransformer` (l.648) ; `xsl:output` HTML 4.01 + seul `<head>`/`<style>`/viewport du rendu. `cda_custom.xsl` (même contenu, non chargé) et `resources/html/cda.css` (jamais lu au runtime) écartés.
- **CSS responsive** (bloc `<style>` embarqué) :
  - `.cda-table/.cda-narr_table` ≤1200px : `display: block` + `overflow-x: auto` (le `display:block` est **requis** pour qu'`overflow-x` s'applique à une `<table>` — sinon débordement viewport) ; `max-width:100%` + `box-sizing`.
  - cellules : `overflow-wrap: anywhere` + `word-break` (longs jetons).
  - global : `img { max-width:100% }`, `box-sizing: border-box` sur conteneurs CDA.
  - nouveau `@media (max-width: 480px)` (densité réduite, lisible ~320px).
  - correction d'un `@media (max-width:1200px)` dont l'accolade fermante manquait.
  - viewport meta : déjà présent (inchangé).
- **Test** : `CdaHtmlResponsiveTests` — transforme un CDA à **tableau large (8 colonnes)** et vérifie viewport + `display: block` + `overflow-wrap` + `@media max-width:480px` dans le HTML, rendu du tableau, et **absence de `<script>`**.
- **Build / tests** : `dotnet build interop.cda.parser.sln` ✓ ; `dotnet test` ✓ **384 réussis / 5 ignorés / 0 échec**.
- **Piège build documenté** : `GenerateResource` est incrémental sur le timestamp du `.resx`, pas du `.xsl` ciblé par `ResXFileRef` → en build incrémental local, l'édition du `.xsl` n'est pas ré-embarquée tant que `Resources.resx` n'est pas touché (un build propre/CI régénère correctement).
- **Commit** : aad3013.
- **Suivi (rule 11)** : pour l'effet end-to-end, bumper `api-mail` (`Directory.Packages.props`) vers la nouvelle version NuGet d'`interop.cda.parser` après merge + publication — hors périmètre mono-repo de cette US.
- **Conformité** : aucun changement CDA r2 sur le fond ni d'API/DTO ; aucune exécution de script dans le HTML généré ; aucun log de données de santé ajouté.

---

### v1.5 — task-100 — Compose / envoi : mail-compose + html-editor (2026-06-18)

- **PR** : [HealthPlatform.Mobile#6](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/6) — label `awaiting-human-merge`. Branche `feat/task-100-mobile-compose-send`. Repo `client-mobile` uniquement. Dépend de task-096 (mergé @5086a82).
- **Composants miroir** :
  - `mss-mail-compose` — `ion-modal` ouverte via `MailEventService.openCompose$` (`ComposeRequest` typé : new/reply/forward). Champs To/Cc/Cci (Cc/Cci repliables), objet, corps HTML, **upload de pièces jointes** (FileReader → base64), case **accusé de lecture**. `send()` : validation ≥ 1 destinataire, construction `OutgoingMailDto`, POST, toast succès + fermeture, échec → message **ProblemDetails** (brouillon conservé). Reply : To = expéditeur, objet « Re: », corps cité, threading In-Reply-To/References. Forward : objet « Fwd: », corps cité, PJ d'origine reprises par référence (guid).
  - `mss-html-editor` — éditeur léger `contenteditable` (gras, italique, listes, liens via `execCommand`).
- **Intégration** : modale hébergée globalement dans `app.component` (atteignable depuis l'inbox et le détail) ; FAB « Nouveau » dans l'inbox ; boutons Répondre / Transférer dans `mss-mail-detail`.
- **`mss-api`** : `sendMail(OutgoingMailDto)` → `POST /api/v1/mail/sendmail` → `SendMailResultDto`. Nouveau DTO `OutgoingMailDto` (sous-ensemble de MailDto suffisant pour l'émission).
- **Tests** : 7 nouveaux — `mail-compose` (prefill reply/forward, refus sans destinataire, build payload + envoi + fermeture), `html-editor` (rendu initial + émission), `mss-api` (POST sendmail). Total suite : **70/70** verts.
- **Build / lint** : `npm run build` ✓, `npm run lint` ✓ clean.
- **Commit** : 53e0687.
- **Conformité** : envoi MSSanté = action sensible → PSC/e-CPS (en place) ; adresse émettrice = boîte du PS connecté ; **jamais de RPPS dans l'objet/en-têtes** ; aucune donnée de santé en clair ; envoi tracé côté backend (PGSSI-S).
- **Hors scope (décision PO)** : signatures, templates, éditeur HTML riche complet, suggestions de contacts, brouillons auto-sauvegardés, cancel-and-replace.

---

### v1.4 — task-099 — Actions message : lu/non-lu, flag, supprimer, déplacer (2026-06-18)

- **PR** : [HealthPlatform.Mobile#5](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/5) — label `awaiting-human-merge`. Branche `feat/task-099-mobile-message-actions`. Repo `client-mobile` uniquement. Dépend de task-096 (mergé @c94fa90).
- **Service** : `mail-actions.service` — orchestrateur MAJ optimiste + API + **rollback** : `toggleRead` (+ compteur non-lus dossier), `markRead` (idempotent, à l'ouverture), `toggleFlag`, `deleteMail` (retrait + réinsertion sur échec), `moveMail`.
- **`mss-mail-list`** : actions par **swipe** (`ion-item-sliding` enveloppant `mss-mail-header` dans un `ion-item`) — Lu/Non lu, Flag, Déplacer, Supprimer ; confirmation de suppression (`AlertController`), choix du dossier cible (`ActionSheetController` sur `imapFolders`).
- **`mss-mail-detail`** : barre d'actions (lu/flag/déplacer/supprimer), **mark-read à l'ouverture** (une fois par uid), émission `mailRemoved` après suppression/déplacement → `mail-detail.page` revient à `/inbox`.
- **Inbox** : segment de filtre **Tous / Non lus / Flaggés** (`mail-state.inboxFilter`).
- **`mss-api`** : `updateReadStatus`/`updateUnreadStatus`/`updateFlagStatus`/`updateUnflagStatus` (PUT `…/status/{read|unread|flagged|unflagged}`), `deleteEmail` (DELETE), `moveEmail` (PUT `…/move` `{targetFolderPath}`). Erreurs consommées au format **ProblemDetails** (`core/utils/http-error.util`).
- **`mail-state`** : `addMailToList` (rollback).
- **Tests** : 7 nouveaux — `mail-actions.service` (optimiste + rollback sur read/flag/delete, move), `mss-api` (PUT statuts, DELETE, PUT move). Total suite : **63/63** verts.
- **Build / lint** : `npm run build` ✓, `npm run lint` ✓ clean.
- **Commits** : fc281fe, a987f82.
- **Conformité** : suppression = action tracée côté backend ; rappel cascade Corbeille → lien patient (cf. mémoire projet) gérée backend, le mobile ne fait qu'appeler l'API ; aucune donnée de santé en clair.
- **Hors scope (rappel)** : compose/envoi (task-100). Bulk / multi-sélection volontairement hors scope (mono-action mobile).

---

### v1.3 — task-098 — Biologie : affichage + acquittement (2026-06-18)

- **PR** : [HealthPlatform.Mobile#4](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/4) — label `awaiting-human-merge`. Branche `feat/task-098-mobile-biology-ack`. Repo `client-mobile` uniquement. Dépend de task-096 (mergé @e59d54d).
- **Composants miroir** (`features/mail/components/`) :
  - `mss-biology` — tableau des résultats groupés par document médical, mise en évidence des valeurs flaggées (critiques LL/HH/AA rouge, anormales L/H/A orange + flèche), filtre « hors norme », plage de référence.
  - `mss-biology-ack-panel` — 5 actions (Acknowledged/PatientCalled/PatientSummoned/ReferredToColleague/MarkResolved, libellés FR), pastille de statut (À TRAITER / EN COURS / RÉSOLU), dernière action, dismiss. Toutes les actions passent par la modale (friction médico-légale).
  - `mss-biology-ack-confirm-dialog` — `ion-modal` : action choisie, **valeurs critiques** listées le cas échéant, code LOINC, note clinique optionnelle (max 500), Confirmer/Annuler.
  - `mss-biology-ack-badge` — badge ligne inbox (compteur `pendingBiologyAcksCount`, rouge si `hasCriticalPendingBiologyAck`).
  - `mss-inbox-biology-ack-chip` — chip de filtre « Bio à acquitter » (récupère les UIDs via l'API, émet l'ensemble / null).
- **Intégration** : onglet « Biologie » dans `mss-mail-body` (table + un `mss-biology-ack-panel` par CDA à biologie flaggée) ; badge dans `mss-mail-header` ; chip dans l'inbox (barre de filtre). `mss-mail-detail` relaie `ackPosted` → `mail-state.applyBiologyAck`.
- **État** (`mail-state`) : `biologyAckFilterUids` (filtre `displayedMails`) + `applyBiologyAck(uid, ack)` (décrément optimiste sur MarkResolved).
- **`mss-api`** : `recordBiologyAck(documentId, {action, note})` → `POST /api/v1/medical-documents/{id}/biology-ack` ; `getBiologyAckPendingMailUids(folderPath)` → `GET /api/v1/biology-acks/pending-mail-uids?folderPath=`.
- **Tests** : 17 nouveaux — `biology` (groupes, niveaux/flèches, filtre, format), `biology-ack-panel` (visibilité flagged, critique, record→dialog→post, MarkResolved→Resolved, annulation), `biology-ack-badge` (visibilité/compteur/critique), `inbox-biology-ack-chip` (fetch+emit set / null), `mss-api` (POST ack + GET pending uids), `mail-state` (filtre bio + applyBiologyAck). Total suite : **56/56** verts.
- **Build / lint** : `npm run build` ✓, `npm run lint` ✓ clean.
- **Commit** : ac8cc9b.
- **Conformité** : couloir biologie médicale (CR-BIO CI-SIS) ; codes LOINC + interprétation HL7 affichés tels quels ; acquittement = action médecin tracée côté backend (PGSSI-S, imputabilité) ; PSC/e-CPS ; aucune valeur de biologie / INS en clair dans les logs.
- **Hors scope (rappel)** : actions message lu/flag/suppression/déplacement (task-099), compose/envoi (task-100).

---

### v1.2 — task-097 — Pièces jointes : mail-attachment + prévisualisation inline (2026-06-18)

- **PR** : [HealthPlatform.Mobile#3](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/3) — label `awaiting-human-merge`. Branche `feat/task-097-mobile-attachments`. Repo `client-mobile` uniquement. Dépend de task-096 (mergé @8764368).
- **Composant** : `mss-mail-attachment` (Ionic) — liste des PJ avec icône par type, taille formatée, badge « Document médical » ; `select()` (preview si previewable sinon download), `download()` par fichier, `downloadAllZip()` (≥ 2 PJ).
- **Intégration `mss-mail-detail`** : getter `mergedAttachments` (PJ MIME `mail.attachments` + PJ des documents médicaux `content.medicalDocuments[].attachments` taguées `isMedical`, dédoublonnées par `guid || fileName`) ; **prévisualisation inline** via `ion-modal` — image (`<img>`), PDF (`<iframe>` blob), texte (`<pre>`) ; object URLs révoquées (`releasePreview` + `ngOnDestroy`).
- **`mss-api`** : `downloadAttachment(folderPath, uid, fileName)` → `GET …/emails/{uid}/download/attachment/{fileName}` (blob) ; `downloadAttachmentsZip(folderPath, uid)` → `GET …/emails/{uid}/attachments/download/zip` (blob). Endpoints existants (parité Angular). La génération ZIP reste **côté backend** (cf. `reference_ziparchive_kestrel_sync_io`) — le mobile consomme le flux.
- **Tests** : 7 nouveaux — `mail-attachment` (emit preview si previewable, download direct sinon, ZIP, formatSize/getIcon/rowKey), `mss-api` (URLs download + zip, responseType blob), `mail-detail` (mergedAttachments dédup + flag isMedical). Total suite : **39/39** verts.
- **Build / lint** : `npm run build` ✓, `npm run lint` ✓ clean.
- **Commit** : a8c6c03.
- **Hors scope (rappel)** : biologie + acquittement (task-098), actions message (task-099), compose/envoi (task-100).

---

### v1.1 — task-096 — Parité consultation email : mail-detail + mail-body + medical-html-frame (2026-06-18)

- **PR** : [HealthPlatform.Mobile#2](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/2) — label `awaiting-human-merge`. Branche `feat/task-096-mobile-mail-detail`. Repo `client-mobile` uniquement. Dépend de task-095 (mergé @f456a09).
- **Composants miroir** (`features/mail/components/`) :
  - `mss-mail-detail` — orchestrateur présentational (@Input mail/content/isLoading/isPlainText). En-tête à parité : `displaySubject` (titre doc médical sinon objet, préfixe XDM retiré), identité patient (nom + INS), destinataires To + Cc, date, badges (marqué, document médical, à rattacher, biologie/critique, non lu), n° de version CDA.
  - `mss-mail-body` — onglets (`ion-segment`) : corps mail + un onglet par document médical. Corps HTML assaini, bascule texte brut, **blocage des images distantes** (`blockRemoteContent`, task-089 parité) + bouton « Afficher les images ». Documents médicaux rendus via `mss-medical-html-frame`. Onglet biologie et mode PDF externe explicitement différés (task-098 / task-097).
  - `mss-medical-html-frame` — rendu du HTML CDA dans une **iframe `sandbox="allow-same-origin"` + blob** (isolation CSS, tokens design injectés, pas d'exécution de script).
  - `core/utils/remote-content.util.ts` — neutralisation des ressources distantes (miroir TS).
- **Hôte** : `mail-detail.page` refactorée en hôte mince — charge mail + contenu depuis les params de route, toggle texte brut en barre d'outils, projette `mss-mail-detail`. `core/mss` déjà supprimé en task-095.
- **Sécurité** : corps du mail via `[innerHTML]` **assaini par Angular** (scripts/handlers retirés → XSS bloqué) ; HTML CDA en **iframe sandbox** (pas d'exécution). Images distantes bloquées par défaut, révélation this-mail-only sans persistance.
- **Tests** : 12 nouveaux — `medical-html-frame` (blob safeUrl set/clear, pas de rebuild si html identique), `mail-body` (onglets mail+docs, blocage/révélation images distantes, priorité 1er doc, plain toggle, fallback plain), `mail-detail` (displaySubject doc médical, identité patient + To/Cc, badges bio/médical, rendu DOM du sujet). Total suite : **32/32** verts (Chrome Headless).
- **Build / lint** : `npm run build` ✓ (warning NG8107 de l'ancien template supprimé). `npm run lint` ✓ clean.
- **Commit** : dec408a.
- **Hors scope (rappel)** : PJ téléchargeables (task-097), biologie + acquittement (task-098), actions message (task-099), compose/envoi (task-100).

---

### v1.0 — task-095 — Socle features/mail miroir + parité Inbox + sélection de répertoire (2026-06-18)

- **PR** : [HealthPlatform.Mobile#1](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/1) — label `awaiting-human-merge`. Branche `feat/task-095-mobile-inbox-folders`. Repo `client-mobile` uniquement (full git automation, GitHub).
- **Refonte structurelle** (miroir `client-angular/front/libs/mss/src`) :
  - `core/models/` : `mail.model.ts`, `folder.model.ts`, `patient.model.ts`, `biology-ack.model.ts`, `draft.model.ts` (+ `index.ts`) — transposition TS des DTO Angular. `biology-ack`/`draft` posés pour task-098/task-100.
  - `core/utils/xdm-subject.utils.ts` (`stripXdmPrefix`).
  - `core/services/mss-api.service.ts` — déplacé depuis `core/mss/`, périmètre folders + emails (getFolders, getFolder, getEmails, getEmailContent).
  - `features/mail/services/` : `mail-state.service.ts` (signals : folders, imap/tagFolders computed, selectedFolder, emails, displayedMails trié+filtré, selectedMail, selection multi, InboxFilter) ; `mail-event.service.ts` (RxJS : mailSelected$, folderChanged$, refreshMailList$, openCompose$).
  - `features/mail/components/` (standalone, sélecteurs miroir) : `mss-mail-list`, `mss-mail-header`, `mss-mail-folder-list`, `mss-mail-folder-item`.
  - `inbox.page` refactorée en **hôte mince** : `ion-split-pane` (menu dossiers `mss-mail-folder-list` + liste `mss-mail-list`), orchestration chargement folders/emails + relais d'évènements.
  - `mail-detail.page` : imports re-câblés vers `core/models` + `core/services`.
  - Suppression de `core/mss/{models,mss-api.service}.ts`.
- **Parité ligne (`mss-mail-header`)** : `displaySubject` (titre du document médical sinon objet, préfixe XDM retiré), identité patient (nom + INS matricule), badges PJ / document médical / biologie (drapeaux serveur `hasMedicalDocuments`/`hasAbnormalBiology`/`attachmentCount`), badge critique bio, n° de version CDA (≠ 1), tags couleur, état lu/non-lu, flag, sujet barré si annulé. `data-testid` sur les éléments interactifs.
- **Sélection de répertoire** : `mss-mail-folder-list` lit `imapFolders` (computed) ; `mss-mail-folder-item` récursif (sous-dossiers dépliables), compteurs non-lus, émission `folderChanged$` → rechargement de la liste.
- **Tests** : 16 nouveaux (Jasmine/Karma) — `mail-header` (displaySubject doc médical / XDM, identité patient, badges DOM, émission mailClick), `mail-folder-item` (sélection, enfants, émission folderClick, toggle), `mail-state.service` (computed imap/tag, tri récent, filtre lu/flaggé, update/remove optimiste, compteur non-lus ≥ 0), `mss-api.service` (URLs folders/emails/content encodées, erreur sans session). Total suite : **20/20** verts (Chrome Headless).
- **Build / lint** : `npm run build` ✓ (1 warning NG8107 pré-existant dans `mail-detail.page.html`, hors scope — à traiter en task-096). `/lint-mobile` : 4 erreurs `@angular-eslint/component-selector` (préfixe `mss`) → règle eslint alignée sur `client-angular` (`prefix: ["app", "mss"]`) ; lint **clean** ensuite.
- **Commits** : 228b2e1 (refonte structure + inbox + dossiers), 5301647 (eslint préfixe `mss`).
- **Conformité** : aucune donnée de santé en clair (INS/identité/contenu) dans logs/URL ; affichage uniquement, consultation tracée côté backend.
- **Hors scope (rappel)** : consultation détail (task-096), PJ (task-097), biologie+ack (task-098), actions message (task-099), compose/envoi (task-100).
