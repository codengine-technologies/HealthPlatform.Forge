# E019 — Changelogs (vue ingénierie)

> **Audience** : équipes techniques, backlog, dette.
> Vue produit : [E019-integration-de-la-nouvelle-messagerie.md](E019-integration-de-la-nouvelle-messagerie.md).
> **Dernière mise à jour** : 2026-10-10 (v1.1)

---

## Historique détaillé des changelogs

### v1.0 — weda2 embarqué dans Weda : mode embarqué, pont v1, flag `weda_integration` — task-356

- **Task** : task-356, statut `done` (`/review` APPROVED le 2026-10-09). Implémentée **hors
  `/develop`**, à la demande de l'humain. Le Develop log a été complété après un premier `/review`
  bloqué (verrous 4a et 4b), puis la task est passée par `/e2e` et `/review`.
- **PRs** :
  - `api-mail` #284, `feat/task-356-weda-integration-pont` → `develop`, label
    `awaiting-human-merge` ;
  - `client-angular` : code-only (TFS, humain), branche
    `feature/nova-rewriting-mss-weda-integration`, commits locaux `9a00b0a6` et `bb7ce801`, plus
    la quarantaine e2e **non commitée** ;
  - hors forge, Weda : branche `lotus/segur/17546-enveloppe-segur-v2-with-mss-api`, `6b335d8610`.
- **api-mail** (commits `9b150938`, `7f2b260e`) :
  - `FeatureFlags.WedaIntegration` (`weda_integration`), ajouté à `All`, repli de démarrage à froid
    déclaré `false`. `FailClosedAtColdStart` passe à 5 flags ;
  - `FlagsmithSeeder` : semé ON en développement. En recette et en production, le flag est créé
    désactivé, puis activé par identité ;
  - weda2 lit le flag par `GET /api/v1/FeatureFlag`, qui évalue par identité.
    `GET /api/v1/FeatureFlag/{name}` est écarté : il appelle `IsEnabledAsync(featureName)` sans
    identité, donc ignore les surcharges des pilotes. **Effet de bord connu** : `ai_text_correction`
    (task-349), qui passe par cette route, ne peut pas être activé pour un seul praticien ;
  - tests : convention `WedaIntegration_IsDeclaredFailClosed` et ancrage littéral à 5 flags fermés ;
    intégration `FeatureFlagEndpointIntegrationTests.WedaIntegrationMissingFromEnvironment_TakesItsFailClosedDefault`,
    **vu rouge par mutation** (`[WedaIntegration] = true` → `Assert.False` en échec, 1/4), puis
    restauré (4/4).
- **client-angular** (weda2) :
  - mode embarqué (`apps/weda2/src/lib/embedded/`) : `EmbeddedHostService`. Weda2 est embarqué
    s'il est en iframe **et** que l'origine du referrer figure dans `EMBEDDED_HOST_ORIGINS`
    (joker de sous-domaine) ;
  - en mode embarqué : `login`, `loginPsc` et `$logout` délèguent à l'hôte (`session-expired`,
    `psc-login-required`) ; inactivité désactivée ; topbar masquée ;
  - pont v1 : `request()` (`requestId`, délais de 30 s et 120 s, écouteur unique filtrant fenêtre
    parente, origine et `source`, transferables), `version: 1` sur tous les messages ;
  - `WedaIntegrationService` : **seul lecteur** de `weda_integration`. `available` vaut embarqué ∧
    flag ∧ `host-capabilities` v1. Aucun appel hors iframe, lecture du flag après authentification
    et ouverture d'une boîte ;
  - port `MSS_PATIENT_RECORD_GATEWAY` (`libs/mss`), implémenté par `WedaPatientRecordGateway` ;
  - **correctif de fond** : `/session/has-session` ajouté à `AUTH_ROUTES`. Il passait par
    l'intercepteur, qui déclenchait un refresh voué à l'échec puis un logout : la connexion
    silencieuse n'avait jamais fonctionné, même hors iframe ;
  - `nginx.conf` : `X-Frame-Options: SAMEORIGIN` remplacé par
    `frame-ancestors 'self' https://*.weda.fr`, hérité par `location /` (index.html) ;
  - alias `@app/weda2/lib/embedded/*` dans `tsconfig.base.json`.
- **Weda** (hors forge) : `Default.aspx` sert de bandeau « Nouvelle expérience Weda » et d'hôte du
  pont v1 (`host-capabilities`). Contrat : ADR-007 du dépôt Weda, amendé deux fois le 2026-10-09
  (amendement 2 : api-mail moteur unique, rien que des identifiants par le pont).
- **Validation** :
  - api-mail : domain 190, infrastructure 683, application 3 569, api 1 186, integration 838 (16
    ignorés), 0 échec ;
  - client-angular : `npm ci` et `nx build weda2` OK, tests des 11 projets verts ; couverture de
    `lib/embedded` 98,6 % (lignes) ;
  - Weda : build MSBuild OK.
- **E2E** :
  - mobile : 31/31 ;
  - angular : 30 verts et **1 quarantaine humaine**, E2E-COMPOSE-002 (task-350, défaut établi
    « Transférer cliqué avant le chargement du contenu »), rouge aux deux essais sur deux runs ;
  - parité verte ; 5e occurrence au registre des flaky.
- **Incidents de cycle** :
  - premier `/e2e` bloqué en outillage : ports 4200 et 5052 occupés par les serveurs de l'humain ;
  - premier passage des tests api-mail compilé dans un `--artifacts-path` hors du dépôt : les tests
    qui cherchent `src/` en remontant ont donné 177 faux échecs. Rejoué dans le dépôt : vert.
- **Suggestions non bloquantes, reportées** :
  - en mode embarqué, `$logout()` émet `session-expired` (un événement dédié serait plus juste) ;
  - types obsolètes du classement par octets (`file-documents`, `get-filing-status`,
    `IWedaFilingPart`) : nettoyage dans task-360 ;
  - `mssApiUrl` de dev à `localhost:7012`, commité par l'humain ;
  - en-têtes de sécurité non hérités par le bloc nginx des fichiers statiques (préexistant).
- **Durée du cycle** (`## Timings` de `tasks/done-task-356.md`) : **23 min 40 s** au total.
  - `/review` : 10 min 08 s (3 builds, 3 suites de tests) ;
  - `/develop` : 1 min 31 s ;
  - `/e2e` : 12 min 00 s de mur, pour 6 mesures e2e cumulant 21 min 05 s (deux runs complets, plus
    les portes).


### v1.1 — Panneau « Dossier Weda » : patient Weda d'un document reçu, ouverture du dossier — task-357

- **Task** : task-357, statut `done` (`/review` APPROVED au 2e passage, le 2026-10-10).
  Implémentée hors `/develop`. Le 1er `/review` a rendu CHANGES REQUESTED : le parcours médecin
  n'avait pas de scénario e2e, parce que la ligne de DoD manquait (oubli de rédaction). Le
  blocage a été **levé par arbitrage du PO** : couverture reportée à task-360, dont l'E2E-WEDA-001
  part du panneau (`questions/answered/task-357.md`).
- **PRs** : **aucune PR forge**, faute de dépôt poussable touché.
  - `client-angular` : code-only, commit local `eca13388` sur
    `feature/nova-rewriting-mss-weda-integration`, à pousser sur TFS par l'humain ;
  - Weda : hors forge, `2c171f46d9` sur `lotus/segur/17546-enveloppe-segur-v2-with-mss-api`.
- **client-angular** (`libs/mss`) :
  - composant `mss-weda-patient-panel` (`features/mail/components/weda-patient-panel/`), branché
    dans `mail-detail`. Rendu seulement si `MSS_PATIENT_RECORD_GATEWAY` est fourni et `available()` ;
  - `patientIdentitiesOf` regroupe les documents par identité : INS + OID, sinon nom + prénom +
    naissance (casse ignorée). L'INS ne sert qu'à la clé, jamais au DOM. `formatIsoDate` est
    indépendant de la locale ;
  - vues : par INS, candidats « à vérifier », aucun, erreur, chargement ; échec d'ouverture
    signalé. Une seule recherche par identité, sans cache entre instances.
- **Weda** (hors forge) :
  - `api/mss/filing` (`MssFilingController`, `[Authorize]`, `HasMessagerieSecurisee`) :
    - `POST resolve-patient` : INS vérifiée par `PatientMixte.SelectPatientsByVerifiedIns`
      (cabinet de la session). Une INS portée par plusieurs dossiers donne des candidats. Sinon,
      recherche par nom et prénom filtrée par la naissance. Patients Weda seulement : les
      patients Archimed non convertis sont exclus en v1 ;
    - `GET context` : destinations 1, 2, 3, `LastDestinationUploadEvent`, glossaires de
      classification, destinataires de post-it ;
    - `GET patient-url/{patientId}` : `[PatientCabinetAuthorization]`, `PatientHelpers.GetPatientUrl` ;
  - `MssPatientMatcher` : règles extraites de `MessageBuilder.GetCDAMetadata`, que
    `MessageBuilder` appelle désormais (−64 lignes). Les deux écrans proposent les mêmes patients ;
  - `Default.aspx` : gestionnaires `resolve-patient`, `get-filing-context`, `open-patient-record`.
    `callApi` traduit les statuts HTTP en codes du contrat ; une redirection de connexion devient
    `weda-session-expired`.
- **Validation** :
  - client-angular : 11 projets verts (dont 20 tests du panneau ; couverture du panneau 98,1 %
    en lignes) ; `nx build weda2` OK, templates vérifiés ;
  - Weda : build MSBuild OK ; gestionnaires du pont vérifiés par une simulation Node, avec un
    faux `fetch` ;
  - test manuel du praticien validé (dossier par INS, candidats, aucun, ancien écran inchangé).
- **E2E** :
  - angular : 30 verts ; E2E-COMPOSE-002 en quarantaine, vert au 2e essai (6e occurrence au
    registre) ;
  - mobile : listing seul ; parité verte ;
  - avertissement « parcours touchés sans spec e2e » sur `mail-detail` et le panneau, levé par le
    report à task-360 ;
  - catalogue @ `origin/develop`, backend e2e construit sur `feat/task-356-weda-integration-pont` ;
  - voie angular jouée alors que la règle de pré-vol, qui ne regarde que les changements non
    commités, l'aurait sautée : les changements de la task étaient déjà commités en local.
- **Suggestions reportées** :
  - tests unitaires des fonctions pures de `MssPatientMatcher`, côté Weda ;
  - cache partagé des recherches de patient côté weda2 ;
  - `max-lines` sur `mail-detail` (préexistant).
- **Durée du cycle** (`## Timings` de `tasks/done-task-357.md`) : **8 min 43 s** au total.
  - `/e2e` : 5 min 41 s ;
  - `/review` : 2 min 13 s, les deux passages cumulés (2 builds, 2 suites de tests ; tests
    servis en partie par le cache Nx) ;
  - `/tech-writer` : 48 s.

---

## Annexe A — Cartographie des briques applicatives

| Brique | Emplacement | Rôle |
|---|---|---|
| Flag d'intégration | `Api/Mail/src/Application/Constants/FeatureFlags.cs`, `src/AppHost/FlagsmithSeeder.cs` | `weda_integration`, fermé à froid, évalué par identité |
| Mode embarqué et pont | `Client/Angular/front/apps/weda2/src/lib/embedded/` | `EmbeddedHostService`, `WedaIntegrationService`, `WedaPatientRecordGateway`, utilitaires d'origine |
| Port du dossier patient | `Client/Angular/front/libs/mss/src/core/tokens/mss-patient-record-gateway.token.ts`, `core/models/weda-patient-record.model.ts` | Contrat vu du module messagerie |
| Délégation de l'auth | `apps/weda2/src/lib/auth/services/authentication-callback.service.ts`, `auto-logout.service.ts`, `interceptors/utils/auth-interceptor.utils.ts` | Pas de redirection dans l'iframe, `has-session` hors intercepteur |
| Politique d'affichage en iframe | `Client/Angular/front/nginx.conf` | `frame-ancestors 'self' https://*.weda.fr` |
| Hôte Weda (hors forge) | Weda : `Weda/FolderMedical/WedaEchanges/NovaMss/` (`NovaMssHost.ascx`, `nova-mss-host.js`), inclus par `Default.aspx` | Bandeau, iframe, gestionnaire du pont (repère `nova-mss`, ADR-007 amendement 4) |
| Panneau « Dossier Weda » | `Client/Angular/front/libs/mss/src/features/mail/components/weda-patient-panel/` | Patient Weda par INS ou candidats, ouverture du dossier (task-357) |
| API Weda du dossier patient (hors forge) | Weda : `Weda/api/NovaMss/` (`NovaMssController`, route `api/nova-mss`) ; rapprochement partagé : `Weda/api/WMickey/Builder/PatientMatcher.cs` | `resolve-patient`, `filing-context`, `patient-url` (task-357) |
| Décisions | Weda : `docs/architecture/adr/007_integration-nouvelle-experience-messagerie.md` ; `Client/Angular/docs/ADR-2026-10-09-integration-weda-mode-embarque.md` | Contrat du pont, amendements 1 à 4 (le 3 fait foi ; le 4 fixe le repère `nova-mss` : import à la demande, WMickey garde la réception, boîte désignée par Weda) |

---

## Annexe B — Inventaire fonctionnel (2026-10-10)

- Tasks de l'EPIC : 4 actives, 2 `done` (356, 357) et 2 `todo` (362, 363). 4 en attente dans
  `tasks/onhold/` (358 à 361) : elles portaient le mode exclusif de l'amendement 2, abandonné par
  l'amendement 3 de l'ADR-007 (décision humaine du 2026-10-10).
- Contrat du pont : version 1. Types implémentés côté hôte : `host-capabilities` (task-356) ;
  `resolve-patient`, `get-filing-context`, `open-patient-record` (task-357). À venir :
  `get-mailbox` (task-362), seule demande émise avant la lecture du flag, et `file-documents`
  (task-363), avec transfert d'octets. `file-message` et `open-draft` sont abandonnés.
- Flags : `weda_integration` (fermé à froid, évalué sur l'identité de la boîte ouverte). Aucun
  mot-clé IMAP : `Weda` et `WedaClasse` sont abandonnés avec l'amendement 2.
- Quarantaines e2e ouvertes : 1 (E2E-COMPOSE-002, angular, task-350). Faux hôte de test et
  E2E-WEDA-001 (boîte désignée) : task-362. Couverture e2e du parcours « Dossier Weda », reportée de
  task-357 à task-360 puis reprise par task-363 : E2E-WEDA-002.

---

## Annexe C — Tasks ayant contribué à cet EPIC

| Task | Statut | Contribution | RGs |
|---|---|---|---|
| task-356 | done (PR api-mail #284, en attente de merge ; Angular à pousser sur TFS) | Mode embarqué, pont v1, `WedaIntegrationService`, port `MSS_PATIENT_RECORD_GATEWAY`, flag `weda_integration`, correctif `has-session` | RG-E019-03, 04, 06 |
| task-357 | done (aucune PR forge ; Angular à pousser sur TFS ; Weda hors forge) | Panneau « Dossier Weda » : patient Weda par INS vérifiée ou candidats par traits, ouverture du dossier ; API Weda `api/nova-mss` (`resolve-patient`, `filing-context`, `patient-url`) | RG-E019-01, 02 (affichage) |
| task-362 | todo | Boîte désignée par Weda : jeton `libs/mss` lu par `mailboxGuard` avant la table de décision, demande `get-mailbox`, écran de rattachement pré-rempli ; faux hôte de test et E2E-WEDA-001 ; côté Weda, `GET api/nova-mss/mailbox` | RG-E019-07 |
| task-363 | todo | Import à la demande : fenêtre d'import (patient, documents, destination, classification, commentaire, post-it), `file-documents` avec octets transférés, ni corbeille ni mot-clé, pas d'import pour la biologie et HPRIM ; E2E-WEDA-002 ; côté Weda, `POST api/nova-mss/documents` | RG-E019-01, 02, 05 |
| task-358 | en attente (`tasks/onhold/`, amendement 3) | API d'intégration api-mail `api/v1/integration`, canal serveur Weda → api-mail, compteur de non-lus de l'en-tête | — |
| task-359 | en attente (`tasks/onhold/`, amendement 3) | Réception des CR de biologie en bannette HPRIM sans WMickey, mots-clés `Weda` / `WedaClasse` | — |
| task-360 | en attente (`tasks/onhold/`, amendement 3) | Classer par identifiants via le canal serveur ; remplacée par task-363 | — |
| task-361 | en attente (`tasks/onhold/`, amendement 3) | « Envoyer par MSSanté » depuis un document Weda vers la rédaction de weda2 | — |
