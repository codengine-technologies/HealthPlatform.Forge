# todo-task-373.md — Le dossier patient ne montre que les documents, résultats et choix de ce patient

**Repos**: client-angular, api-mail, client-mobile
**Dependencies**: task-371 (fenêtre du document et chargements annulables)
**Epic**: E009
**Single frontend**: false — client-mobile ajouté le 2026-10-24 (décision humaine, voir « Arbitrage mobile »)
**Priorité**: **1** — la fiche d'un patient affiche le document, la biologie et la synthèse clinique d'un autre patient ; des résultats sont présentés avec une mauvaise unité ; l'opposition affichée et modifiée peut être celle d'une autre fiche.

> **Origine.** Audit de détection de bugs du client Angular du 2026-10-13
> (`Docs/audits/client-angular-audit-bugs-20261013.md`, **ANG-20 ✔, ANG-50, ANG-51, ANG-52, ANG-53, ANG-54**).

## Ce qui est établi

- **ANG-20** — `patient-timeline.component.ts:121-129` : `allDocuments` verse dans la chronologie **tous** les documents de chaque mail (`getEmailContent`, qui ne filtre pas par patient — `MailRepository.cs:1253-1334`), sans regarder `doc.patientId`. Un mail à deux CDA rattachés à X et à Y : la fiche de X montre le document, la biologie et la synthèse de Y. Les décisions « suppression acceptée », « supplanté » et « doublon » sont aussi annulées à l'affichage. La route de contenu est en cache 15 min.
- **ANG-50** — `mss-patient.component.html:142-143`, `mss-api.service.ts:1241-1243, 1307-1382` : la fiche est relue par INS (`POST /Patients/resolve`) au lieu de son handle. Un matricule connu dans deux domaines (task-331) donne deux fiches : chronologie et opposition de l'autre fiche. Le front réintroduit le mélange AUD-34.
- **ANG-51** — `biology-timeline.component.ts:655-671, 377-385` : une ligne par `code|nom`, unité et normes prises sur le premier résultat ; tendances calculées entre unités différentes (g/L et mmol/L).
- **ANG-52** — biologie et synthèse calculées sur les seules pages de mails chargées ; la période choisie automatiquement masque le résultat le plus ancien (arithmétique en jours contre coupure en mois).
- **ANG-53** — `patient-card.component.ts:157-180`, `patient-consent.component.ts:97-121` : un échec d'enregistrement de l'opposition laisse la case cochée et le badge « Opposition active », sans message.
- **ANG-54** — `patient-attachment-dialog.component.ts:103-158, 292-307` : une réponse de candidats en retard s'affiche sous les traits d'un autre document ; « Rattacher » (sans confirmation) rattache au patient d'un autre.

## Objective

Que la fiche d'un patient ne présente **que** les documents, résultats et décisions qui lui appartiennent, avec l'unité et la norme de chaque résultat, et que les choix du médecin sur ce patient (opposition, rattachement) soient appliqués à **cette** fiche et reflètent l'état réel du serveur.

### Périmètre

1. **Documents du dossier servis par le serveur** depuis les documents actifs du patient (`ActiveDocumentsForPatient`), par page, au lieu du contenu complet des mails.
2. **Fiche désignée par son handle** dans la chronologie et l'opposition (les routes existent) ; domaine affiché dans les résultats de recherche quand deux fiches partagent un matricule.
3. **Biologie** : unité dans la clé de ligne (ou tendances seulement sur une unité homogène), unité et norme affichées par valeur ; données de biologie et de synthèse indépendantes de la pagination des mails ; période calculée avec la même arithmétique que la coupure, sans écraser le choix du médecin.
4. **Opposition** : retour à l'état précédent et message en cas d'échec ; état et date relus depuis la réponse du serveur.
5. **Rattachement manuel** : réponse ignorée si le document n'est plus celui du dialogue.

## Definition of Done

- [ ] Build et tests verts : weda2, api-mail
- [ ] Test d'intégration de bout en bout pour la route des documents du dossier patient : un mail à deux CDA rattachés à X et à Y — la réponse pour X ne contient que le document de X ; un document « suppression acceptée » n'y figure pas (lus dans la réponse réelle), vu rouge (règle 1b)
- [ ] Tests unitaires et de composant rouges d'abord :
  - [ ] la chronologie de X n'affiche aucun document dont `patientId` ≠ X
  - [ ] la chronologie et l'opposition sont chargées par le handle de la fiche, jamais par l'INS
  - [ ] deux résultats du même analyte en g/L et en mmol/L ne partagent ni ligne ni tendance ; chaque valeur affiche son unité
  - [ ] un résultat de 104 jours est visible avec la période choisie automatiquement
  - [ ] échec du `PUT` d'opposition : la case revient à son état, un message s'affiche
  - [ ] réponse de candidats du document A arrivée après l'ouverture sur B : ignorée
- [ ] Scénario E2E-PATIENT-003 « La fiche d'un patient ne montre pas les documents d'un autre patient du même mail » ajouté (angular `requis` ; mobile : `non-applicable` si la vue patient n'existe pas sur mobile, à confirmer au `/start`)
- [ ] Trou du filet : ligne dans `conventions/e2e.md`
- [ ] Aucune INS, NIR ni contenu CDA dans les journaux ou les URL

## Manual Test Plan

1. Recevoir un mail portant deux CDA sans INS ; rattacher le premier à X, le second à Y. Ouvrir la fiche de X → seul le document de X apparaît (documents, biologie, synthèse). Idem pour Y.
2. Patient dont la glycémie vient de deux laboratoires (g/L et mmol/L) → deux lignes, chacune avec son unité ; aucune tendance mêlant les deux.
3. Cocher l'opposition MSSanté avec le réseau coupé → la case se décoche et un message d'erreur s'affiche.
4. Deux fiches de même matricule : ouvrir la seconde → ses documents et son opposition s'affichent, pas ceux de la première.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif d'identito-vigilance de l'affichage du dossier
- **Exigences DSR honorées** : identito-vigilance (un document n'est présenté que dans le dossier du patient auquel il est rattaché)
- **INS** : utilisée seulement comme trait de recherche ; la fiche est désignée par son handle (INS hors des URL, task-184) ; aucun changement de statut INS
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : CDA r2 (affichage) ; résultats de biologie codés LOINC — l'unité devient partie de l'identification d'une série
- **Tracé PGSSI-S** : modification de l'opposition tracée comme aujourd'hui ; aucune trace nouvelle
- **Consentement patient** : opposition à l'envoi vers Mon Espace Santé — l'état affiché devient celui du serveur
- **Référentiels métier** : LOINC (biologie), UCUM (unités)
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangé

## Timings

*(généré par `tools/timing/report.sh --task task-373 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 1 min 04 s | — | — | — | — |
| /develop | ok | 51 min 36 s | 6 (3 min 29 s) | 16 (12 min 32 s) | — | api-mail 4B/12T, client-angular 1B/3T, client-mobile 1B/1T |
| /sonar | ok | 20 min 44 s | 2 (49 s) | 10 (12 min 18 s) | 4 (4 min 37 s) | 1 itération(s), api-mail 2B/10T |
| /lint-angular | ok | 1 min 21 s | — | — | — | — |
| /lint-mobile | ok | 27 s | — | — | — | reprise mobile |
| /e2e | ok | 29 min 12 s | — | — | — | e2e ×4 (25 min 13 s) |
| /review | ok | 6 min 09 s | 3 (1 min 37 s) | 3 (5 min 32 s) | — | api-mail 1B/1T, client-mobile 1B/1T, client-angular 1B/1T |
| **Total cycle** | | **1 h 50 min** | **11 (5 min 57 s)** | **29 (30 min 23 s)** | **4 (4 min 37 s)** | |

Autres commandes mesurées : lint ×2 (1 min 24 s)

## Branches

- `api-mail` (pushed) : fix/task-373-dossier-patient-du-seul-patient — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-373-dossier-patient-du-seul-patient
- `client-mobile` (pushed, ajouté le 2026-10-24) : fix/task-373-dossier-patient-du-seul-patient — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/fix/task-373-dossier-patient-du-seul-patient
- `client-angular` (code-only) : la forge écrit sur la branche courante de `Client/Angular/` (`feature/nova-mss-weda-integration` au /start, arbre propre) — humain gère branche, commit, push, PR TFS

## Develop log

- **Contrat** : aucun changement de `dtos-mss` (pas de publication NuGet).
  - `GET /api/v1/patients/{id}/folder?page&pageSize` : une page de mails ; le contenu de chaque mail (`content.medicalDocuments`) ne porte que **les documents actifs de cette fiche** (`ActiveDocumentsForPatient`). La fenêtre du document garde ainsi dossier et uid du mail.
  - `GET /api/v1/patients/{id}/documents` : tous les documents actifs de la fiche, avec biologie et synthèse, hors pagination (source des onglets Biologie et Synthèse).
  - Construction des documents : `MailRepository.GetMedicalDocumentsAsync(ids)`, la même que le contenu d'un mail. Trois recherches groupées par lot ; les pièces jointes en une requête pour toute la page (`LoadDocumentAttachmentsByMailAsync`, que le chemin d'un seul mail emprunte aussi).
  - Composition : `PatientFolderService`, injecté par `[FromServices]` (ni `PatientService` ni le contrôleur ne changent de constructeur).
  - Opposition : le `PUT` reste vide ; le client relit la fiche (`GET patients/{id}`) pour l'état et la date enregistrés.
- **api-mail** (`ce7cfc90`, `63c58647`) :
  - Règle 1b : `PatientFolderEndToEndTests.AMailCarryingTheDocumentsOfTwoPatients_EachFolderServesOnlyItsOwnActiveDocuments`. Un mail porte trois documents (X actif avec biologie et synthèse, X « suppression acceptée », Y) ; `folder` et `documents` sont lus dans la réponse réelle, avec une prémisse affirmée (trois documents en base).
    - Mutation **M1** (la page prend tous les documents du mail) : rouge, « The collection contained 3 items ».
    - Mutation **M2** (la liste complète ignore les statuts) : rouge, document supprimé présent.
  - 404 problem+json des deux routes ajouté à la théorie des poignées inconnues.
  - Tests unitaires `PatientFolderServiceTests` (4).
  - Seed e2e : `cda-deux-patients`, un message avec deux `IHE_XDM.ZIP`. Chaque archive porte la lettre de liaison du gabarit sans INS, avec une INS de test (`1.2.250.1.213.1.4.10`), des traits, un titre et des identifiants de document propres (`E2eTwoPatientsXdm`, testé à travers le vrai `CdaParsingService`).
  - Validation : build 0 avertissement, 0 erreur ; tests 195 + 695 + 3 607 + 1 280 + 966/982 (16 ignorés IA), 0 échec.
- **client-angular** (code-only, `feature/nova-mss-weda-integration`, non commité) :
  - Chronologie :
    - désignée par `patientId` (handle) ;
    - chargée par elle-même à chaque changement de fiche ; une réponse d'une fiche dépassée est ignorée (numéro de chargement) ;
    - documents servis par `folder`, biologie et synthèse par `documents` ;
    - par défense, tout document dont le `patientId` n'est pas celui de la fiche est écarté ;
    - plus aucun `getEmailContent`.
  - `mss-patient` ne pilote plus la chronologie (plus de `ViewChild` ni de `setTimeout`).
  - Carte patient : opposition lue et écrite par handle ; échec → retour à l'état d'avant et message (`patient-opposition-error`) ; succès → état et date relus depuis la fiche du serveur ; réponse d'une autre fiche ignorée.
  - Biologie :
    - l'unité entre dans la clé de série, et chaque valeur porte son unité (infobulle) ;
    - période automatique = la plus courte dont la coupure, en mois de calendrier, contient le plus ancien résultat ;
    - un choix du médecin n'est plus écrasé.
  - Dialogue de rattachement : la recherche de candidats précédente est abandonnée, et une réponse (candidats ou recherche) d'un autre document est ignorée.
  - **Suppressions** :
    - `patient-consent` : composant sans aucun gabarit qui l'utilise, et seul autre lecteur « par INS » ;
    - `getMailsByInsPaged`, `updatePatientOpposition(ins)`, `getMedicalDocumentsByIns`.
    - Le dossier ne peut plus être lu par INS. `getPatientOpposition(ins)` reste pour la rédaction (INS tirée de l'adresse), et lit désormais par handle après résolution.
  - Tests rouges d'abord : specs `patient-timeline` (nouveau, 4), `patient-card` (nouveau, 5), `biology-timeline` (+3), `patient-attachment-dialog` (+1). Preuve par mutation :
    - M1 filtre `patientId` retiré : rouge ;
    - M2 biologie lue sur la page chargée : rouge ;
    - M3 réponse d'une fiche dépassée : rouge ;
    - M4 pas de retour sur échec : rouge ;
    - M5 opposition lue par INS : rouge ;
    - M6 clé sans unité : rouge ;
    - M7 période sur des mois de 30 jours (calcul d'origine) : rouge ;
    - M8 choix du médecin écrasé : rouge ;
    - M9b abandon et garde retirés : rouge. Chacune des deux protections suffit seule (M9 et M9c, verts) : elles sont redondantes, pas mortes.
  - e2e : E2E-PATIENT-003 dans `functional.e2e.ts`, plus `OtherDevice.patientFolderDocumentTitles`. Le parcours lit la route `folder` relue, puis l'écran des deux fiches, présence du document de la fiche avant l'absence de l'autre.
  - Validation : `npm run build` vert ; `npm test` 2 653/2 653 (12 projets) ; lint des fichiers touchés 0 erreur, aucun avertissement sur du code neuf.
- **Passe qualité (§Q)** : api-mail relu, aucun nettoyage appliqué (helpers existants réutilisés, aucun N+1).
- **Écarts au périmètre** :
  - « Domaine affiché dans les résultats de recherche quand deux fiches partagent un matricule » : non fait. `MailPatientDto` ne porte pas le domaine ; l'exposer est un changement de contrat `dtos-mss` (publication NuGet, consommateurs Blazor et mobile). La lecture par handle supprime déjà le mélange (ANG-50). Task de suivi à ouvrir.
  - Le libellé des onglets compte toujours les documents des pages chargées (le compte des onglets Biologie et Synthèse est complet).
- **Constat hors task (mobile)** : la vue patient mobile lit `getMailsByInsPaged`, qui ne rend aucun contenu. Ses onglets Documents, Biologie et Synthèse sont donc vides en permanence, par INS. Voir l'arbitrage sur E2E-PATIENT-003 (colonne mobile).
- **Préventions** : `conventions/angular.md` « reponse-d-un-contexte-depasse » (nouvelle) ; trou du filet dans `conventions/e2e.md`.

## Sonar log

- Serveur 25.6.0.109173 (`sonar.token`), projet **`healthplatform-api-mail`**, branche `fix/task-373-dossier-patient-du-seul-patient` (`63c58647`).
- **Faux départ (consigné)** : une première analyse a été publiée sur le projet dormant `healthplatform`. La clé du `.env` n'avait pas été surchargée, alors que `agents/sonar.md` § Environment le prescrit. Elle n'altère pas le projet suivi. Seconde analyse sur la bonne clé. Prévention : la mémoire `reference_sonar_scanner_msys_argconv`, relue avant tout scan, porte désormais la clé.
- **Phase 1 (nouveau code de la task)** : aucun problème imputable à la task.
  - Les 3 problèmes situés dans des fichiers touchés sont antérieurs : S103 aux lignes 281 et 304 d'`IMailRepository`, S138 sur `LoadBulkContentLookupsAsync`.
  - Lignes ajoutées toutes couvertes : `PatientFolderService` et `PatientsController` à 100 % ; aucune ligne non couverte dans `GetActiveDocumentIdsAsync`, `GetFolderPageAsync`, `GetMedicalDocumentsAsync`, `LoadDocumentAttachmentsByMailAsync`.
  - Aucune correction nécessaire.
- **Phase 2 (dette héritée)** : non lancée (optionnelle, best-effort).
- Tests sous couverture : 195 + 3 607 + 695 + 1 280 + 966/982, 0 échec.

### KPIs qualité (baseline → final)

| Métrique | Baseline (analyse du 22/10, fin de task-376) | Final (branche task-373) | Δ |
|---|---|---|---|
| Quality Gate (new code) | ERROR | ERROR | → (hérité, 0 problème imputable à la task) |
| New coverage | 98,2 % | 98,2 % | 0 |
| New violations | 72 | 72 | 0 |
| Bugs | 2 | 2 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 15 | 15 | 0 |
| Code smells | 70 | 70 | 0 |
| Coverage (projet) | 98,0 % | 98,1 % | +0,1 pt |
| Duplication | 0,3 % | 0,3 % | 0 |
| Reliability / Security / Maintainability | D/A/A | D/A/A | → |

## Lint log

- `npx nx affected -t lint --base=origin/next --head=HEAD --parallel=3 --projects=tag:scope:mss` (arbre weda2 courant) : **0 erreur**, 13 projets. Les avertissements sont antérieurs (JSDoc `@example` vides, `max-lines`, `complexity` de `classifyDocument`) ; aucun sur une ligne de la task (relevé en `/develop`).
- 0 itération de correction. Build et `npm test` inchangés depuis `/develop` (`npm run build` vert, 2 653/2 653).

## Lint mobile log

- skipped : client-mobile non listé dans les Repos, non touché.

## Arbitrage mobile (2026-10-24)

- Constat : la vue patient mobile existe (E2E-PATIENT-001/002 `requis` sur mobile), mais n'affiche aucun document : elle lit par INS `medical-documents`, qui ne rend pas le contenu des mails.
- **Décision humaine : inclure le mobile dans task-373.** La vue patient mobile passe au handle et aux routes `folder` / `documents` ; E2E-PATIENT-003 y est `requis` et implémenté.

## Develop log — reprise mobile (2026-10-24, après arbitrage)

- **api-mail** (`2796ad2f`) :
  - `documents` sert les documents **sans leurs corps** : biologie et synthèse ne les affichent pas (projection d'en-tête de task-323).
  - `folder` les sert par défaut (weda2 les affiche dans la frise et la fenêtre) ; avec `withBodies=false`, il les omet (mobile, qui les charge à la demande).
  - Test d'intégration étendu : corps présent par défaut, absent avec `withBodies=false` et dans `documents`. Mutation « flag ignoré » : rouge.
  - Tests application 3 607, api 1 280, infrastructure 695, `PatientFolderEndToEndTests` 23 : verts.
  - **L'analyse Sonar porte sur `63c58647`**, pas sur ce commit : retouche de 8 lignes, couverte par les tests ci-dessus.
- **client-mobile** (`2666f34`, `15758e3`) :
  - Vue patient par handle : chronologie sur `folder` (sans corps) et `documents` ; garde de génération ; filtre `patientId`. Elle n'affichait aucun document : la lecture par INS de `medical-documents` ne rendait pas de contenu.
  - `patient-consent` par handle : date initiale lue sur la fiche, retour sur échec avec toast d'erreur, état et date relus, réponse d'une autre fiche ignorée.
  - Biologie : unité dans la série, unité par valeur, période automatique sur la coupure en mois, choix du médecin préservé.
  - API : `getOppositionByPatientId`, `updateOppositionByPatientId`, `getPatientFolderPage`, `getPatientDocuments` ; suppression de `getMailsByInsPaged` et de `updatePatientOpposition(ins)`. `getPatientOpposition(ins)` reste pour la rédaction.
  - e2e : E2E-PATIENT-003 (`functional.spec.ts`) et `OtherDevice.patientFolderDocumentTitles`.
  - Preuve par mutation (`ng test --include`) : MM1 filtre `patientId`, MM2 biologie sur la page, MM3 fiche dépassée, MM4 pas de retour sur échec, MM5 opposition par INS, MM6 clé sans unité, MM8 choix écrasé : toutes rouges.
  - Validation : `npm run build` vert ; 1 197/1 197 ; `npm run lint` propre.
- Passe qualité : aucun nettoyage appliqué.
- Reprise (mobile ajouté) : `npm run lint` sur `15758e3` — tous les fichiers passent, 0 itération. Build et tests verts (1 197/1 197, cf. Develop log).

## E2E log

| Voie | Commande | Résultat |
|---|---|---|
| mobile | `npm run e2e:headless` sur `15758e3` (api-mail `2796ad2f`) | 42 verts, 0 flaky, 0 rouge — parité verte |
| angular | `npm run e2e:mss` (arbre weda2 de la task, `NX_PLUGIN_NO_TIMEOUTS=true`) | 1er montage : **code 2 outillage** (api-mail e2e muet sur `/health` après 480 s, ports libres, voie mobile verte juste avant) ; rejoué : 49 verts, 1 flaky, 0 rouge — parité verte |
| gate | `mss.mail.e2e gate` sur le catalogue de la branche | code 0 |

- Démontage vérifié : aucun conteneur e2e résiduel, ports 5052/3993/3465/3143 libres.
- **Preuve rouge d'E2E-PATIENT-003** (banc mobile `--serve-only`, `--retries=0`) : mutation M1 côté serveur (la page du dossier sert tous les documents du mail) → rouge sur « le serveur sert à la première fiche son seul document » (un document en trop). Fichier restauré depuis une copie.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**Flaky (vert au second essai, non bloquant)** (1) :

- [angular] « recherche — requête et recherche avancée » (E2E-SEARCH-001)

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-PATIENT-003 | 1 | headless | La fiche d'un patient ne montre pas les documents d'un autre patient du même mail | ✅ | ✅ |
| E2E-CONTACT-001 | 2 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Écrire à l'adresse choisie d'un contact à plusieurs adresses, ou à son adresse par défaut | ✅ | ✅ |
| E2E-COMPOSE-005 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ⚠️ flaky | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 2 | headless | Créer un contact à deux adresses, le modifier sans les perdre, puis le supprimer | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 1 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## Code Review Summary

**Verdict : APPROVED** — 0 bloquant.

- Validation : api-mail build ✓, tests 195 + 695 + 3 607 + 1 280 + 966/982 (16 ignorés IA), 0 échec ; client-mobile build ✓, 1 197/1 197 ; weda2 (`feature/nova-mss-weda-integration`) build ✓, `npm test` ✓ (12 projets).
- E2E double verrou : `## E2E log` vert ✓ ; E2E-PATIENT-003 au catalogue (v1), implémenté sur les deux clients, vu rouge sous M1.
- Règle 1b, comportement → test → preuve rouge :
  - `folder` ne sert que les documents actifs de la fiche → `AMailCarryingTheDocumentsOfTwoPatients_…` → M1 rouge ;
  - `documents` ignore suppression acceptée, supplanté, doublon → même test → M2 rouge ;
  - `withBodies` → même test → M3 rouge ;
  - 404 problem+json des deux routes → `AnUnknownPatientHandle_Is404ProblemJson`.
- DoD : tous les items vérifiés, sauf le domaine affiché dans la recherche (écart au périmètre, contrat `dtos-mss`, task de suivi).
- Suggestions : borner `pageSize` de `folder` ; état d'acquittement biologique non calculé par `folder` (aucune vue patient ne le lit).

## PRs

- api-mail : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/308 — label `awaiting-human-merge`
- client-mobile : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/102 — label `awaiting-human-merge`
- client-angular : code-only — humain gère commit/push TFS et ouverture PR (`feature/nova-mss-weda-integration`). À commiter **avant le merge de la PR api-mail** (E2E-PATIENT-003 requis côté Angular). Fichiers modifiés :

```
   M front/e2e/mss-e2e/specs/functional.e2e.ts
   M front/e2e/mss-e2e/support/e2e-backend.ts
   M front/libs/mss/src/core/services/mss-api.service.ts
   M front/libs/mss/src/features/mail/components/patient-attachment-dialog/patient-attachment-dialog.component.spec.ts
   M front/libs/mss/src/features/mail/components/patient-attachment-dialog/patient-attachment-dialog.component.ts
   M front/libs/mss/src/features/patient/components/biology-timeline/biology-timeline.component.spec.ts
   M front/libs/mss/src/features/patient/components/biology-timeline/biology-timeline.component.ts
   M front/libs/mss/src/features/patient/components/patient-card/patient-card.component.html
   M front/libs/mss/src/features/patient/components/patient-card/patient-card.component.scss
   M front/libs/mss/src/features/patient/components/patient-card/patient-card.component.ts
   D front/libs/mss/src/features/patient/components/patient-consent/patient-consent.component.html
   D front/libs/mss/src/features/patient/components/patient-consent/patient-consent.component.scss
   D front/libs/mss/src/features/patient/components/patient-consent/patient-consent.component.ts
   M front/libs/mss/src/features/patient/components/patient-timeline/patient-timeline.component.ts
   M front/libs/mss/src/features/patient/mss-patient.component.html
   M front/libs/mss/src/features/patient/mss-patient.component.ts
  ?? front/libs/mss/src/features/patient/components/patient-card/patient-card.component.spec.ts
  ?? front/libs/mss/src/features/patient/components/patient-timeline/patient-timeline.component.spec.ts
```
