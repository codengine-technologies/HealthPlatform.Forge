# todo-task-133.md — Vue patient mobile (2/4) : timeline documents médicaux + viewer

**Repos**: client-mobile
**Dependencies**: done-task-132
**Epic**: E012

## Objective

Ajouter à la vue patient mobile (socle livré par task-132) la **timeline des
documents médicaux** du patient sélectionné : liste paginée des documents
groupés par période, filtres par type de document, et **visionneuse de
document** (PDF + vues structurées). Portage en **miroir structurel** de
`client-angular` (`libs/mss/src/features/patient/components/`).

US **frontend-only** : endpoints déjà en production dans `api-mail`
(`GET /api/v1/Patients/ins/{ins}/medical-documents` paginé,
`GET /attachment/{folderPath}/{uid}/{fileName}` pour le PDF,
`GET /mail/{folderPath}/{uid}` pour le contenu). **Aucune modification backend
ni DTO**. Scope : `client-mobile` seul.

US **complète et autonome** : une fois livrée, le médecin peut parcourir tous
les documents d'un patient et les ouvrir (règle 11 respectée). Dépend de
task-132 (a besoin du conteneur `mss-patient` et de la sélection patient).

## Travail de report — exigence de fidélité

Reproduire fidèlement structure et **noms de composants** de client-angular
(sélecteurs `mss-*`, noms de classe), adapter la seule présentation aux
ergonomies Ionic (via `/stitch-design` : les onglets desktop deviennent des
`ion-segment`, le rail vertical une liste mobile, le modal un `ion-modal`
plein écran). Réutiliser les DTOs/endpoints existants.

## Composants à porter (noms identiques à client-angular)

| Sélecteur | Classe | Rôle |
|---|---|---|
| `mss-patient-timeline` | `PatientTimelineComponent` | Conteneur onglets (Documents / Biologie / Synthèse — seul **Documents** est câblé ici ; Biologie→task-134, Synthèse→task-135) ; pagination (10/page), filtres par type, génération dynamique des onglets selon les données. |
| `mss-timeline-document-group` | `TimelineDocumentGroupComponent` | Groupe de documents sous un libellé de période ; expand/collapse ; icônes/labels de catégorie. |
| `mss-timeline-period-separator` | `TimelinePeriodSeparatorComponent` | Séparateur visuel de période (Aujourd'hui, Cette semaine, …). |
| `mss-medical-document-modal` | `MedicalDocumentModalComponent` | Visionneuse plein écran : PDF (blob) + vues structurées (HTML assaini / texte brut). Les vues biologie/synthèse internes seront enrichies par task-134/135. |

## Comportement attendu (parité Angular)

- À la sélection d'un patient (depuis task-132), `mss-patient-timeline`
  charge la **1ʳᵉ page** (10 documents) via l'endpoint paginé.
- Documents **groupés par période** (Aujourd'hui, Hier, Cette semaine, Ce mois,
  3 derniers mois, Cette année, Année) avec séparateurs.
- **Filtres par type** (chips/segment) : tous, biologie, synthèse clinique,
  synthèse médicale, CR hospitalier, imagerie, prescription, rapport, médical,
  autre — n'afficher que les filtres ayant des documents (logique
  `filterOptions`/`typeCounts`).
- **Pagination** : « charger plus » / `ion-infinite-scroll` → page suivante.
- Ouverture d'un document → `mss-medical-document-modal` :
  - bascule de vue (PDF si `hasExternalPdf`, sinon HTML assaini / texte brut) ;
  - PDF récupéré en **blob** et rendu ; **Object URL révoqué** à la fermeture ;
  - téléchargement éventuel via les capacités Capacitor/navigateur.
- États : chargement, vide (« Aucun document »), erreur (toast/alerte).

## Definition of Done

- [ ] Build passe (`npm ci && npm run build`) — 0 erreur
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`) — 0 échec
- [ ] Composants `mss-patient-timeline`, `mss-timeline-document-group`, `mss-timeline-period-separator`, `mss-medical-document-modal` créés avec sélecteurs/noms **identiques** à client-angular
- [ ] `MssApiService` : `getMailsByInsPaged(ins, page, pageSize)`, `downloadAttachment(folder, uid, fileName)`, `getEmailContent(folder, uid)` ajoutés + tests
- [ ] Test : groupement par période (`documentGroups`), filtre par type (`filteredDocuments`), pagination (chargement page 2)
- [ ] Test de rendu `mss-medical-document-modal` (bascule de vue, fermeture, libération du blob)
- [ ] **HTML de document assaini** avant rendu (pas d'injection depuis le corps du document)
- [ ] **Object URL du PDF révoqué** à la fermeture du modal (pas de fuite mémoire / pas de persistance disque non maîtrisée)
- [ ] Libellés FR en dur (parité client-angular)
- [ ] `data-testid` sur chips de filtre, groupes, items document, boutons du modal
- [ ] **Aucune donnée de santé en clair dans les logs** (titre, contenu, INS, PDF)

## Manual Test Plan

- Lancer l'app mobile : `cd Client/Mobile && npm start`, se connecter (session de test)
- Onglet Patients → sélectionner un patient ayant **plusieurs documents** sur plusieurs périodes
- Attendu : documents groupés par période, séparateurs visibles
- Vérifier les filtres par type : ne s'affichent que les types présents ; un
  filtre restreint bien la liste
- Faire défiler / « charger plus » → la page suivante s'ajoute sans doublon
- Ouvrir un document **avec PDF** → le PDF s'affiche, le téléchargement
  fonctionne, la fermeture libère le blob (pas de ralentissement après plusieurs
  ouvertures)
- Ouvrir un document **HTML** → contenu rendu proprement (pas de script injecté)
- Patient sans document → message « Aucun document », pas de crash

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (consultation des documents médicaux du patient)
- **Vague Ségur** : hors exigence DSR nouvelle — portage d'affichage d'une capacité déjà référencée
- **Exigences DSR honorées** : non applicable — aucune exigence DSR nouvelle
- **INS** : l'INS sert de clé d'appel API (`/Patients/ins/{ins}/medical-documents`) over HTTPS (contrat existant) ; **jamais** loggée côté client ni placée dans une route/param mobile (sélection patient tenue en state, héritée de task-132)
- **Authentification PS** : session MSSanté existante, niveau eIDAS inchangé
- **Habilitations** : inchangées — accès aux documents du patient suivant l'habilitation du titulaire de la boîte
- **Interop CI-SIS** : les documents sont des **CDA r2** déjà **parsés et structurés côté `api-mail`/`interop-cda`** (biologie, synthèse) ; le mobile **n'effectue aucun parsing CDA** — il consomme le JSON structuré et/ou le PDF. Le HTML/texte rendu est assaini avant affichage
- **Tracé PGSSI-S** : la consultation/ouverture de document est journalisée **côté `api-mail`** (canal existant) ; pas de log client du contenu ni de l'INS
- **Consentement patient** : non applicable directement — consultation par le médecin destinataire ; l'opposition reste gérée en task-132
- **Référentiels métier** : LOINC/CIM-10 éventuellement présents **dans** les documents (affichage tel quel) ; aucun codage produit par le mobile
- **Hébergement HDS** : oui — documents et PDF servis par l'`api-mail` (backend HDS) ; transit HTTPS, **PDF en blob mémoire, Object URL révoqué**, pas de persistance disque non maîtrisée sur l'appareil
- **AIPD / impact RGPD** : inchangé — nouveau canal de consultation mobile d'un traitement existant

## Branches
- `client-mobile` (pushed) : feat/task-133-mobile-patient-timeline — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-133-mobile-patient-timeline

## Stitch design log
- Écrans : timeline documents intégrée à l'onglet Patients (`mss-patient-timeline` sous la fiche) + visionneuse plein écran (`mss-medical-document-modal`, `ion-modal`). Design porté structurellement de la vue patient Angular (liste groupée par période + filtres + modal). Onglets desktop → filtres `ion-segment` scrollable ; rail vertical → liste mobile ; modal desktop → `ion-modal` plein écran.
- `/stitch-design` : best-effort, non invoqué (référence = vue patient Angular existante).

## Develop log
- Repos touched : client-mobile
- DTOs published : no DTO change (DTOs documents déjà présents dans le modèle mobile)
- Interop published : no interop change
- Commits :
  - client-mobile : 8da8323 feat(mobile): patient documents timeline + viewer (task-133)
- Local build / test : ✓ client-mobile (`npm run build` 0 erreur ; `npm test` 201/201 verts)
- DOD self-check :
  - ✓ Build / Tests verts
  - ✓ Composants `mss-patient-timeline`, `mss-timeline-document-group`, `mss-timeline-period-separator`, `mss-medical-document-modal` (sélecteurs/noms identiques à client-angular)
  - ✓ MssApiService.getMailsByInsPaged ajouté + test ; `getEmailContent`/`downloadAttachment` **réutilisés** (déjà présents — reuse before create)
  - ✓ Tests : groupement par période, filtre par type, pagination (page 2), modal (bascule de vue, fermeture, libération du blob)
  - ✓ HTML de document **assaini** via binding `[innerHTML]` (sanitizer Angular natif — pas de bypass sur le corps du document)
  - ✓ Object URL du PDF **révoqué** à la fermeture du modal (+ au masquage + sur le bouton télécharger) ; `takeUntilDestroyed` partout
  - ✓ Libellés FR en dur
  - ✓ data-testid (filtres, groupes, items, boutons du modal)
  - ✓ Aucune donnée de santé loggée côté client
- Note de parité : seul l'onglet **Documents** est câblé (filtres affichés si >1 type) ; onglets Biologie (task-134) et Synthèse (task-135) à venir. Le modal supporte PDF + HTML assaini + texte brut ; les vues biologie/synthèse détaillées seront ajoutées par 134/135. Deep-link `?ins=` toujours omis (garde-fou INS).
- Next step : /forge-simplify task-133

## Simplify log
- Repos passed : client-mobile
- Applied & committed : client-mobile: 4 files (4728af6)
  - Reuse : `downloadBlob()` util extrait (`core/utils/blob-download.util.ts`) — dédup du `triggerDownload` du modal **et** du `mail-attachment` existant (les deux pointent maintenant sur l'util)
  - Efficacité : `classifyDocument()` mis en cache dans un `computed` Map (il tournait 2× par document — `typeCounts` + `matchesFilter`)
- Skipped findings (noted, not applied) :
  - Convertir le modal en signal-inputs + `effect()` — la convention mobile est `@Input`/`ngOnChanges` (mail-detail, mail-body…) ; ngOnChanges + garde `loadedPdfKey` est la bonne altitude ici, pas un bandaid
  - Extraire helpers blob-URL/date sur 3 composants pré-existants — large, faible valeur, le cycle de vie reste local
  - Déplacer `typeLabels` dans le modèle — consommateur unique (spéculatif)
  - Factoriser `loadDocuments`/`loadMore` — différences sémantiques (reset vs append, garde, complete()) obscurciraient
  - Extraire classify/grouping en util — spéculatif (task-134/135 le feront si nécessaire) ; mirror Angular
  - Cacher `getDateGroupLabel` — appels peu coûteux, gain marginal
- Rolled back (validation RED) : none
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*
- Build / tests : ✓ green on client-mobile (build 0 erreur ; 201/201 tests)
- Next step : /lint-mobile task-133

## Lint mobile log
- Baseline `npm run lint` (ng lint) : **All files pass linting** — 0 error, 0 warning
- Iterations run : 0 (nothing to fix)
- Fixes committed : none (tree clean)
- Build / tests : verts depuis /develop + /forge-simplify (build 0 erreur ; 201/201 tests)
- Next step : /review task-133

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/36 — label `awaiting-human-merge`

## Code Review Summary
- Verdict : **APPROVED** (0 blocking, 1 note non bloquante)
- client-mobile :
  - `mss-api.service.ts` (getMailsByInsPaged) — ✅ co-localisé, params page/pageSize, INS encodé
  - `mss-patient-timeline` — ✅ pagination + groupement + filtres + classification cachée + orchestration modal
  - `mss-timeline-document-group` / `mss-timeline-period-separator` — ✅ liste groupée repliable + aperçu assaini
  - `mss-medical-document-modal` — ✅ PDF blob (iframe + download, Object URL révoqué) + html/raw assainis ; takeUntilDestroyed
  - `core/utils/blob-download.util.ts` — ✅ util `downloadBlob` partagé (dédup mail-attachment)
  - tests — ✅ service/timeline/modal/document-group
- Note non bloquante : heuristiques de classification = miroir Angular ; onglets Biologie (task-134) / Synthèse (task-135) à venir.
- Validation : build ✓ 0 erreur, tests ✓ 201/201, lint ✓ clean.

## Merged
- Date : 2026-06-28
- `client-mobile` : squash commit `f7e938ac5568c79d9067b31b9df3776d99e49834` — PR #36 mergée (squash), branche remote supprimée (locale conservée)
- develop CI : aucun workflow GitHub Actions configuré sur le repo (rien à vérifier ; PR « no checks reported », mergeState CLEAN au merge)
