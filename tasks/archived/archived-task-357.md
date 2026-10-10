# done-task-357.md — Intégration Weda, phase B : afficher le patient Weda d'un document reçu

**Repos**: client-angular
**Dependencies**: task-356 (pont v1, `WedaIntegrationService`, `MSS_PATIENT_RECORD_GATEWAY`)
**Epic**: E019
**Single frontend**: true — seul weda2 est embarqué dans Weda.
**Priorité**: **2** — premier livrable visible de l'intégration : dans un message reçu, le praticien
voit à quel dossier patient Weda correspond chaque document médical, et l'ouvre en un clic. C'est le
préalable au classement (phase C).

> **Origine.** Suite de task-356, décidée le 2026-10-09. Le contrat est celui de l'ADR-007 du dépôt
> Weda (§ D2 : `resolve-patient`, `get-filing-context`, `open-patient-record`). Côté Weda, le travail
> est hors forge : contrôleur `api/mss/filing` et gestionnaires du pont dans `Default.aspx`, sur la
> branche `lotus/segur/17546-enveloppe-segur-v2-with-mss-api`. **api-mail n'est pas touché** : les
> traits du patient (`patientIns`, `patientOid`, nom, prénom, naissance, sexe) sont déjà dans
> `MailMedicalDocumentDto`.

## Ce qui existe (constaté dans le code le 2026-10-09)

- **client-angular** :
  - `MSS_PATIENT_RECORD_GATEWAY.resolvePatient()` et `openPatientRecord()` existent (task-356) ;
    ils sont relayés au pont et rejettent `unsupported` tant que `available()` est faux.
  - `mail-detail.component.ts` › `medicalDocumentsOfMail()` expose les documents médicaux du mail,
    avec les traits du patient extraits du CDA.
- **Weda** :
  - l'ancien écran rapproche un patient dans `api/WMickey/Builder/MessageBuilder.cs`
    › `GetCDAMetadata` : INS vérifiée d'abord (`PatientMixte.SelectPatientsByVerifiedIns`), sinon nom
    et prénom (`vitalzen.patient.searchPatients`) filtrés par la date de naissance ;
  - l'URL signée du dossier vient de `PatientHelpers.GetPatientUrl`.

## Objective

1. **Weda** — contrôleur `api/mss/filing` (`[Authorize]`, réservé aux utilisateurs
   `HasMessagerieSecurisee`, cloisonné par le cabinet de la session) :
   - `POST resolve-patient` `{ ins?, insOid?, lastName?, firstName?, birthDate?, gender? }` →
     `{ byIns, candidates }`. Il applique **les mêmes règles que l'ancien écran**, extraites dans une
     classe partagée que `MessageBuilder` utilise aussi. Seuls les patients Weda (`PatientID > 0`)
     sont rendus ; les patients Archimed non convertis sont exclus en v1.
   - `GET context` → destinations (1 Consultation, 2 Examen, 3 Courrier), destination par défaut
     (`LastDestinationUploadEvent`), classifications (glossaires « classification » du cabinet),
     destinataires de post-it (praticiens et secrétaires du cabinet).
   - `GET patient-url/{patientId}` (`[PatientCabinetAuthorization]`) → URL signée du dossier.
2. **Weda** — `Default.aspx` : gestionnaires `resolve-patient`, `get-filing-context` et
   `open-patient-record`. Ce dernier navigue la fenêtre principale vers l'URL signée. Les erreurs HTTP
   sont traduites en codes du contrat (400 `invalid-payload`, 401 `weda-session-expired`,
   403 `forbidden`, 404 `not-found`, sinon `server-error`).
3. **client-angular** — composant `mss-weda-patient-panel`, rendu dans `mail-detail` **seulement si**
   `MSS_PATIENT_RECORD_GATEWAY` est fourni, si `available()` est vrai et si le mail porte au moins un
   document médical avec une identité patient :
   - une ligne par identité patient distincte (INS + OID, sinon nom + prénom + naissance) ;
   - un patient trouvé par INS → « Dossier Weda : DUPONT Marie, née le 31/01/1970 », avec le bouton
     « Ouvrir le dossier » ;
   - sinon, les candidats par traits → « Correspondances possibles », chacune avec le bouton
     « Ouvrir » ;
   - aucun → « Aucun dossier Weda correspondant » ;
   - recherche en échec → « Recherche du dossier Weda impossible », sans détail technique.

## Definition of Done

- [x] Build passes (0 errors) ; Tests pass (0 failures, hors flaky préexistants documentés)
- [x] **Angular** — tests de composant :
  - [x] rien n'est rendu, et `resolvePatient` n'est pas appelé, si le port est absent ou
    `available()` faux
  - [x] une seule recherche par identité distincte, même avec plusieurs documents
  - [x] chacun des trois affichages (par INS, candidats, aucun) et l'état d'échec
  - [x] « Ouvrir le dossier » appelle `openPatientRecord` avec l'identifiant Weda
  - [x] l'INS n'apparaît ni dans le DOM ni dans les logs
- [x] **Weda** — build du projet `Weda.csproj` (MSBuild Debug, 0 erreur) ; le rapprochement de l'ancien écran (`MessageBuilder`) est
  inchangé après l'extraction (même classe, mêmes règles)
- [x] `data-testid` sur le panneau, chaque ligne et chaque bouton ; libellés FR en dur
- [x] Aucune donnée de santé dans les logs : ni INS ni traits, côté Weda comme côté weda2
- [x] Scénario e2e du parcours « voir le dossier Weda du patient d'un document reçu et l'ouvrir » :
  **reporté à task-360**, dont le scénario E2E-WEDA-001 part de ce panneau. Arbitrage du PO le
  2026-10-10, après le `/review` bloquant (`questions/answered/task-357.md`).
  - Motif : le panneau ne s'affiche qu'embarqué dans Weda, et le faux hôte de test qui permet de
    le jouer est un livrable de task-360.
  - Jusque-là, le parcours est couvert par les 20 tests de composant et par le test manuel du
    praticien.

## Manual Test Plan

Prérequis : phase A en place (`available=true` dans la console de l'iframe), et un message reçu
contenant un CDA (IHE_XDM).

1. Un patient avec INS **qualifiée** dans Weda, et un CDA portant cette INS → le panneau affiche
   « Dossier Weda : … ». « Ouvrir le dossier » ouvre la fiche du patient dans la fenêtre Weda.
2. Un CDA sans INS, mais dont le nom, le prénom et la date de naissance correspondent à un patient
   Weda → « Correspondances possibles », avec ce patient.
3. Un CDA dont le patient est inconnu de Weda → « Aucun dossier Weda correspondant ».
4. Flag `weda_integration` éteint, ou weda2 ouvert dans un onglet → aucun panneau, et aucune demande
   `resolve-patient` dans les messages échangés.
5. Un mail sans document médical → aucun panneau.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — messagerie MSSanté intégrée au logiciel
- **Exigences DSR honorées** : préalable à RG-E009-034 (« classer en 1 clic dans le dossier
  patient »), qui sera couverte par la phase C
- **INS** : l'INS du CDA transite par le pont dans le `payload` (jamais dans une URL), et n'est
  comparée qu'aux INS **vérifiées** du cabinet. **Aucune identité n'est créée ni modifiée.** Un
  rapprochement par traits n'est qu'une **proposition**, présentée comme telle (identito-vigilance).
- **Authentification PS** : inchangée (session Weda et session proxy partagées)
- **Habilitations** : Weda revérifie tout. Les recherches sont cloisonnées par le cabinet de la
  session, et l'ouverture du dossier passe par `[PatientCabinetAuthorization]`.
- **Interop CI-SIS** : lecture des traits du CDA déjà extraits par api-mail ; rien n'est produit
- **Tracé PGSSI-S** : inchangé, aucune donnée de santé journalisée
- **Consentement patient** : non applicable — consultation du dossier par le praticien du cabinet
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé. Aucun identifiant Weda n'est persisté côté HealthPlatform.
- **AIPD / impact RGPD** : inchangé

## Branches

- `client-angular` (code-only) : branche courante `feature/nova-rewriting-mss-weda-integration`
  (humain : commit, push, PR TFS)
- Hors forge, `Weda` : `lotus/segur/17546-enveloppe-segur-v2-with-mss-api`
- `api-mail` : non concerné

## Avancement (2026-10-09)

Implémenté directement (hors `/develop`), à la demande de l'humain.

- **Weda** (non commité) :
  - `api/MssFilingController.cs` : `resolve-patient`, `context`, `patient-url/{patientId}` ;
  - `api/MssFiling/MssPatientMatcher.cs` : règles extraites de `MessageBuilder`, qui les appelle
    désormais (−64 lignes dans `MessageBuilder`) ;
  - `api/MssFiling/MssFilingContracts.cs` ;
  - entrées `Compile` dans `Weda.csproj`. Au commit, il faudra isoler ces 3 lignes des réglages
    weda-dev (`/weda-dev off https`).
  - `Default.aspx` : gestionnaires `resolve-patient`, `get-filing-context`, `open-patient-record`, et
    traduction des erreurs HTTP. Une redirection vers la page de connexion devient
    `weda-session-expired`.
  - Vérifications : build MSBuild du projet Weda OK ; gestionnaires vérifiés par simulation Node
    (faux `fetch`).
- **client-angular** (non commité) :
  - `mss-weda-patient-panel` (composant, utilitaires, styles), branché dans `mail-detail` ;
  - tests : 20 tests du panneau ; `libs/mss` 608 verts ; weda2 2 654 verts ;
  - couverture du panneau 98,1 % (lignes) ; ESLint sans erreur. Seul avertissement : `max-lines`,
    préexistant sur `mail-detail` ;
  - build `nx build weda2` (development) OK, templates vérifiés.

**Non vérifié** : le parcours réel dans le navigateur (Manual Test Plan), et le rendu de l'ancien
écran après l'extraction du rapprochement (même code, déplacé).

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| angular | client-angular modifié par la task (commit `eca13388`) | ✅ verte | 30 verts, 0 rouge, 1 quarantaine passée au 2e essai (E2E-COMPOSE-002, task-350) | 5 min 01 s |
| mobile | non touchée — listing | 📋 listée | listing de la suite mobile, parité contrôlée | — |

- Déclenchement de la voie angular : les changements Angular de la task sont **déjà commités en
  local**. La règle de pré-vol (« `status --porcelain` non vide ») aurait donc conclu « non
  touché ». La voie est jouée selon l'intention de la règle : la task modifie bien le client
  Angular.
- Catalogue : `Api/Mail/e2e/scenarios.yml` @ `origin/develop` (api-mail non touché par la task).
  Backend e2e construit depuis le checkout courant d'`Api/Mail` :
  `feat/task-356-weda-integration-pont` (PR #284 non mergée ; la task n'y touche pas).
- Quarantaines : E2E-COMPOSE-002 (angular), correction task-350, posée le 2026-10-09. Résultat de
  ce run : flaky (vert au 2e essai).
- Divergences ouvertes : aucune
- ⚠️ **Parcours touchés sans spec e2e modifié** (avertissement, non bloquant) :
  `libs/mss/src/features/mail/components/mail-detail/mail-detail.component.html` et
  `weda-patient-panel/weda-patient-panel.component.html`. Le panneau « Dossier Weda » n'est rendu
  qu'**embarqué dans Weda**, avec un port d'accès disponible. La suite e2e joue weda2 seul, et le
  panneau n'y apparaît pas. Sa couverture e2e arrive avec le **faux hôte de test** de task-360 et le
  scénario E2E-WEDA-001, qui part de ce panneau.
- Démontage : complet (ports 5052, 8100, 4200, 3993, 3465, 3143 libres ; aucun conteneur
  `e2e-dovecot-*` ni `e2e-greenmail-*` résiduel)

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Flaky — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | 📋 listé |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | 📋 listé |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | 📋 listé |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | 📋 listé |
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | 📋 listé |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | 📋 listé |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | 📋 listé |
| E2E-DETAIL-001 | 1 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | 📋 listé |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | 📋 listé |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ⚠️ flaky | 📋 listé |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | 📋 listé |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | 📋 listé |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | 📋 listé |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | 📋 listé |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | 📋 listé |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | 📋 listé |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | 📋 listé |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | 📋 listé |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | 📋 listé |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | 📋 listé |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | 📋 listé |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | 📋 listé |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | 📋 listé |
| E2E-CONTACT-002 | 1 | headless | Créer puis supprimer un contact | ✅ | 📋 listé |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | 📋 listé |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | 📋 listé |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | 📋 listé |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | 📋 listé |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | 📋 listé |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | 📋 listé |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | 📋 listé |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- **Aucune PR GitHub** : task-357 ne touche aucun dépôt poussable de la forge (api-mail non concerné).
- `client-angular` : code-only. L'humain gère le commit, le push TFS et l'ouverture de la PR. Branche
  `feature/nova-rewriting-mss-weda-integration`. Le code de la task est **déjà commité en local**
  (`eca13388`), et `git diff --name-only` est vide. Fichiers du commit :
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.html`, `.ts`
  - `front/libs/mss/src/features/mail/components/weda-patient-panel/weda-patient-panel.component.{ts,html,scss,spec.ts}`
  - `front/libs/mss/src/features/mail/components/weda-patient-panel/weda-patient-panel.utils{,.spec}.ts`
- Hors forge, `Weda` : branche `lotus/segur/17546-enveloppe-segur-v2-with-mss-api`, commit
  `2c171f46d9` :
  - `api/MssFilingController.cs`
  - `api/MssFiling/MssFilingContracts.cs`, `api/MssFiling/MssPatientMatcher.cs`
  - `api/WMickey/Builder/MessageBuilder.cs`
  - `FolderMedical/WedaEchanges/Default.aspx`
  - `Weda.csproj`

## Code Review Summary

**APPROVED**, 0 point bloquant (2e passage du 2026-10-10).

- **1er passage : CHANGES REQUESTED.** Le parcours médecin « Dossier Weda » n'avait pas de
  scénario e2e (règles 1b et 1c), parce que la DoD omettait la ligne, un oubli de rédaction.
  **Levé par arbitrage du PO** : la couverture est reportée à task-360 (E2E-WEDA-001 part du
  panneau), ligne de report ajoutée à la DoD (`questions/answered/task-357.md`).
- Build : ✓ client-angular (`npm ci`, `nx build weda2`)
- Tests : ✓ client-angular, 11 projets, 0 échec (dont 20 tests du panneau). Weda : build MSBuild
  OK (hors forge, sans tests automatisés, voir les suggestions).
- DOD : ✓ tous les items, dont la ligne de report e2e
- Verrou 4a (règle 1b, backend poussable) : sans objet. Aucun dépôt backend de la forge n'est
  touché. Les routes Weda sont hors forge, validées par le test manuel du praticien et par une
  simulation des gestionnaires du pont.
- Verrou 4b : `## E2E log` vert (angular 30 verts ; 1 quarantaine passée au 2e essai ; mobile
  listé ; parité verte).
- Revue :
  - ✅ panneau : identités regroupées, l'INS n'est jamais affichée, états de chargement, d'erreur
    et « aucun » ; une seule recherche par identité ; rien n'est rendu sans port disponible ;
  - ✅ Weda : la recherche par INS est limitée aux INS **vérifiées** du cabinet. La recherche par
    nom est cloisonnée par le cabinet de la session, avec les mêmes règles que l'ancien écran
    (cabinet copieur, rôles). L'URL du dossier passe par `[PatientCabinetAuthorization]` ; aucune
    identité n'est créée ;
  - ✅ `MessageBuilder` délègue au rapprochement partagé : les deux écrans proposent les mêmes
    patients, et le test manuel de l'ancien écran est validé par l'humain.
- Suggestions (non bloquantes) :
  - Weda : ajouter des tests unitaires aux fonctions pures de `MssPatientMatcher`
    (`PatientIdFromDataKey`, `NamesFromTraits`) ;
  - weda2 : le panneau relance la recherche du patient à chaque ouverture d'un message (cache par
    instance seulement) ; un cache partagé allègerait les appels à Weda ;
  - `mail-detail.component.ts` dépasse la limite `max-lines` (préexistant).

## Timings

*(généré par `tools/timing/report.sh --task task-357 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /e2e | ok | 5 min 41 s | — | — | — | e2e ×2 (5 min 07 s), vert : angular 30 verts + 1 quarantaine flaky (E2E-COMPOSE-002, task-350), mobile listé, parité verte ; avertissement : panneau Dossier Weda sans spec e2e (couverture via task-360) |
| /review | ok | 2 min 13 s | 2 (1 min 01 s) | 2 (3.3 s) | — | client-angular 2B/2T, APPROVED (blocage e2e levé par arbitrage PO : couverture reportée à task-360) ; client-angular code-only, Weda hors forge, aucune PR forge |
| /tech-writer | ok | 48 s | — | — | — | E019 v1.1 (Mode 1) : F2 validée, entrée changelog task-357, annexes |
| **Total cycle** | | **8 min 43 s** | **2 (1 min 01 s)** | **2 (3.3 s)** | **0 (0.0 s)** | |

## Merged

- **Date** : 2026-10-10, par `/merge task-357 --i-tested` (validation manuelle attestée par l'humain).
- **Aucune PR à merger** : la task ne touche aucun dépôt poussable de la forge. Pas de branche à
  supprimer, pas de CI `develop` à attendre.
- `client-angular` : géré manuellement par l'humain (commit local `eca13388`, à pousser sur TFS).
- Hors forge, Weda : branche `lotus/segur/17546-enveloppe-segur-v2-with-mss-api`. Le code de
  `2c171f46d9` a depuis pris le repère `nova-mss` (ADR-007, amendement 4) : `Weda/api/NovaMss/`,
  route `api/nova-mss`.
