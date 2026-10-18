# E019 — Changelogs (vue ingénierie)

> **Audience** : équipes techniques, backlog, dette.
> Vue produit : [E019-integration-de-la-nouvelle-messagerie.md](E019-integration-de-la-nouvelle-messagerie.md).
> **Dernière mise à jour** : 2026-10-14 (v1.6)

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


### v1.2 — Boîte désignée par Weda : weda2 embarqué s'ouvre sur la messagerie que Weda connaît — task-362

- **Task** : task-362, statut `done` (`/review` APPROVED le 2026-10-10). Premier cycle E019
  entièrement autonome (`/start` → `/develop` → … → `/review`). Priorité 1 : un compte Keycloak peut
  porter plusieurs boîtes, et weda2 ouvrait sa boîte « par défaut ».
- **PRs** :
  - `api-mail` #285, `feat/task-362-weda-designated-mailbox` → `develop`, label
    `awaiting-human-merge`. Catalogue seul : `d7af41e2`, E2E-WEDA-001 v1 (angular `requis`, mobile
    `non-applicable`) ;
  - `client-angular` : code-only, **non commité** sur `feature/nova-rewriting-mss-weda-integration`.
    **À commiter sur TFS avant le merge de #285** (convention `test-angular-non-commite`) ;
  - Weda (hors forge, règle 11) : `GET api/nova-mss/mailbox`, gestionnaire `get-mailbox` de
    `nova-mss-host.js`, switch masqué aux secrétaires. **Reste à faire par l'humain.**
- **client-angular** :
  - `libs/mss` : jeton `MSS_DESIGNATED_MAILBOX` (`() => Promise<string | null>`, optionnel).
    `mailboxGuard` l'interroge en parallèle de `store.initialize()`, puis applique la table :
    - boîte sélectionnable du compte → ouverte, quel que soit `isDefault` ;
    - non sélectionnable → `select` ;
    - absente du compte → `onboarding` ;
    - pas d'adresse → table inchangée ;
    - `PscRequired` reste prioritaire.
  - Journal `[MailboxEntry] designated-mailbox outcome=designated|attach-proposed|fallback`, sans
    adresse.
  - `MailboxSessionStore.designatedEmail` : en mémoire seulement, remis à zéro par `clear()`,
    jamais dans l'URL.
  - `isSameMailboxAddress` (`core/utils/mailbox-address.util.ts`) : comparaison sans casse ni
    espaces, partagée par la garde et l'écran.
  - Écran de rattachement : annonce `mailbox-onboarding-designated` et pré-remplissage par
    `AttachMailboxFormComponent.initialEmail` (`linkedSignal`), tant que le compte ne porte pas
    l'adresse.
  - `apps/weda2` : `designatedMailboxFactory`, fourni en mode embarqué seulement. `get-mailbox` à
    10 s ; une erreur, une adresse vide ou mal formée donnent `null`. `'get-mailbox'` est ajouté à
    `EmbeddedHostRequestType`.
- **Faux hôte e2e** (`e2e/mss-e2e/support/weda-host.ts`, réutilisable par task-363) :
  - `startFakeHost` : vrai serveur HTTPS loopback sur `https://localhost:47399`, avec le certificat
    de dev de `run.mjs`, déclaré dans `embeddedHostOrigins` de la configuration e2e ;
  - pont v1 côté hôte (`host-capabilities`, `get-mailbox`), avec contrôle de la fenêtre source et
    de l'origine ;
  - un `route.fulfill` initial était bloqué par le contrôle d'accès au réseau local de Chrome (page
    « publique »). La plage 44300-44399 est réservée par `http.sys` (IIS Express).
- **Validation** :
  - client-angular : `nx build weda2` OK, 11 projets de tests verts ;
  - api-mail : domain 190, infrastructure 683, api 1 186, application 3 569, integration 838 (16
    ignorés), 0 échec ; `ScenarioCatalogTests` 17/17.
- **Tests rouges d'abord et mutations** :
  - vus rouges avant implémentation : 9 cas de garde, 1 store, 2 cas de l'écran ;
  - mutations unitaires, toutes rouges sur l'assertion visée :
    - MG1 désignation ignorée, MG2 PSC non prioritaire, MG3 casse stricte ;
    - MO1 sans pré-remplissage ;
    - M1 fourni hors iframe, M2 délai par défaut, M3 validation d'adresse retirée ;
  - mutations e2e, rouges sur l'assertion visée : ME1 fournisseur absent, ME2 garde qui ignore la
    désignation.
- **E2E** :
  - mobile : 31/31 ;
  - angular : 31 verts, E2E-COMPOSE-002 en quarantaine (rouge, task-350) ;
  - porte verte, parité verte, E2E-WEDA-001 ✅.
- **Incidents de cycle** :
  - port 5052 tenu par l'AppHost de dev de l'humain pendant `/develop` : non arrêté par la forge ;
  - 1er essai mobile en outillage : API DCP élevée injoignable, `migrate.lock` de 0 octet. Réglé
    en purgeant `~/.dcp/state.elevated` ;
  - E2E-WEDA-001 rouge au 1er passage angular (faux hôte en `route.fulfill`), corrigé en reprise
    `/develop`. Prévention : `conventions/e2e.md`, entrée `hote-embarquant-en-loopback`.
- **Suggestions non bloquantes, décision produit** :
  - aucune sortie depuis l'écran de rattachement d'une boîte désignée dont le rattachement échoue.
    Le praticien embarqué n'atteint alors plus ses autres boîtes. Piste : lien vers `/select` ;
  - le titre « Rattachez votre première messagerie » reste affiché quand le compte en porte déjà
    d'autres.
- **Durée du cycle** (`## Timings` de `tasks/done-task-362.md`) : **54 min 18 s** au total.
  - `/e2e` : 26 min 40 s (5 mesures e2e cumulant 18 min 36 s) ;
  - `/develop` : 21 min 54 s ;
  - `/review` : 4 min 49 s (2 builds, 2 suites de tests).


### v1.3 — Import à la demande dans le dossier patient Weda — task-363

- **Task** : task-363, statut `done` (`/review` APPROVED le 2026-10-10). Cycle autonome. Le 1er
  `/e2e` a été bloqué en outillage : les ports 5052 et 4200 étaient tenus par les serveurs de
  développement de l'humain (`questions/answered/task-363.md`). Relancé par l'humain.
- **PRs** :
  - `api-mail` #286, `feat/task-363-weda-import-documents` → `develop`, label
    `awaiting-human-merge`. Commit `2aff4aff` : `E2eProfile.ForcedFeatureFlags` +
    `weda_integration`, tests `ForcedFeatureFlags_IncludeWedaIntegration` (vu rouge) et
    `ForcedFeatureFlags_AreAllKnownFlags`, catalogue E2E-WEDA-002 v1 ;
  - `client-angular` : code-only, **non commité** sur `feature/nova-rewriting-mss-weda-integration`.
    **À commiter sur TFS avant le merge de #286** ;
  - Weda (hors forge, règle 11), **reste à faire** : `POST api/nova-mss/documents`, gestionnaire
    `file-documents` (`413` → `payload-too-large`), `postItLevels` dans `get-filing-context`.
- **client-angular** :
  - `libs/mss/src/features/mail/components/weda-import/` : `WedaImportComponent`, posé dans
    `mail-detail` sous le panneau « Dossier Weda » ;
  - fonctions pures `weda-import.utils.ts` :
    - `isBiologyMail` : LOINC `11502-2` ou objet contenant `HNET.1/MSG/` ;
    - `importCandidatesOf` : PDF des CDA et pièces jointes cochés, en `attachment-{rang}`,
      enveloppe IHE_XDM exclue, message `body` non coché ;
    - `describeImportError` ;
  - patient : présélection par `byIns` seulement, candidats jamais présélectionnés, recherche
    manuelle par `resolve-patient` (contrat inchangé) ;
  - octets lus par `downloadAttachment` / `exportMailAsPdf`, transférés par la passerelle ;
  - nettoyage (amendement 3) : `getFilingStatus`, `IWedaFilingEntry`,
    `MAX_FILING_STATUS_MESSAGE_IDS`, `get-filing-status` et `WedaFiledBy` retirés.
    `IWedaFilingResult` devient `{ results: [{ part, fileStreamId }] }` ;
  - **ajout optionnel au contrat** : `IWedaFilingContext.postItLevels?` (libellés de Weda, table
    de configuration 70). Absent, weda2 envoie le niveau 0.
- **Faux hôte e2e** : il répond aussi à `resolve-patient` (dossiers synthétiques « à vérifier »),
  `get-filing-context`, `open-patient-record` et `file-documents`. D'un import, il ne garde que le
  nombre de pièces, leurs types et leurs tailles.
- **Validation** :
  - client-angular : `nx build weda2` OK, 11 projets verts (41 tests nouveaux pour l'import) ;
  - api-mail (dans `bin`, à `/review`) : domain 190, infrastructure 683, api 1 188, application
    3 569, integration 838 (16 ignorés), 0 échec.
- **Mutations** :
  - unitaires MU1 à MU7, toutes rouges sur l'assertion visée ;
  - e2e ME3 à ME6 (import jamais envoyé, biologie non reconnue, ouverture sans effet, message
    supprimé par l'import), rouges sur l'assertion visée. Deux essais invalides (mutation non
    compilée, ancre coupée par Prettier) ont été rejoués valides. La récidive est consignée dans
    `conventions/e2e.md` (`mutation-non-servie`, occurrence 4).
- **E2E** :
  - mobile : 31/31 ;
  - angular : 32 verts, E2E-COMPOSE-002 en quarantaine (task-350) ;
  - E2E-WEDA-002 vert au 1er passage, porte et parité vertes.
- **Incidents** :
  - pendant `/develop`, `src/Api/bin` était verrouillé par l'AppHost de développement : tests
    compilés dans `Api/Mail/artifacts/forge-363`, dans le dépôt ;
  - `SemanticSearchRepositoryIntegrationTests` rouges 3 fois tant que l'AppHost tournait
    (`develop` compris), verts une fois l'AppHost arrêté. Corrélation, cause non prouvée :
    mémoire de session ;
  - 1er build rouge sur un TS2322 du gabarit (`WedaDestination`), que vitest ne voit pas.
- **Suggestions reportées** :
  - préparation partielle si `resolve-patient` échoue ;
  - plusieurs patients dans un même message ;
  - post-it sans destinataire ;
  - `sentAt` vide.
- **Durée du cycle** (`## Timings` de `tasks/done-task-363.md`) : **1 h 02 min** au total.
  - `/develop` : 30 min 56 s ;
  - `/e2e` : 25 min 47 s, preuves par mutation comprises ;
  - `/review` : 4 min 55 s.

### v1.5 — Envoi d'un document du dossier patient Weda par la nouvelle messagerie, api-mail emballe en IHE_XDM — task-367

- **Task** : task-367, statut `done` (`/review` APPROVED le 2026-10-11). Cycle autonome. Décision : ADR-007 amendement 6
  (dépôt Weda) et amendement 4 de l'ADR client. Remplace task-361 (canal serveur abandonné).
- **PR** :
  - `dtos-mss` #44, à merger en premier ;
  - `api-mail` #289, label `awaiting-human-merge`, branche `feat/task-367-weda-envoi-ihe-xdm` ;
  - client-angular : code-only, 27 fichiers à commiter sur TFS **avant** le merge d'api-mail (E2E-WEDA-003 `requis`) ;
  - partie Weda (`nova-mss`) hors forge, à faire par l'humain (règle 11).
- **Contrat** (`HealthPlatform.Dtos.Mss` **524.0.0**) :
  - `AttachmentDto.Packaging` (`IheXdmPackagingDto?`) ;
  - `IheXdmPackagingKind` (`Unspecified`, `ExistingCda`, `PdfA`, sérialisé en chaîne) ;
  - `IheXdmPatientDto`, `IheXdmAuthorDto`, `IheXdmStructureDto`.
- **api-mail** :
  - consomme `Interop.Cda.Parser` **107.0.0** (task-366 mergée) ;
  - `IheXdmEnvelopeService.Apply(MailDto)`, appelé par `OutgoingMailService` juste après la résolution des pièces par
    référence, **avant** les règles de taille et les en-têtes `X-MSS-*`. L'envoi différé confirmé avec la carte passe
    par ce même chemin : l'enveloppe est construite à la confirmation ;
  - `ExistingCda` : la pièce est **remplacée** par `IHE_XDM.ZIP`. `PdfA` : le PDF est gardé, sans sa demande, et
    `IHE_XDM.ZIP` est insérée juste après ;
  - destinataires prévus : À + Cc, dédoublonnés, **sans Cci**. README : logiciel `HealthPlatform`, éditeur
    `Codengine Technologies` (à valider par l'humain). `DisableZip64` ;
  - auteur : comparé au RPPS de la carte de la session, sinon à `MssRpps`, préfixe 8 toléré ;
  - refus : `IheXdmAuthorNotSenderException` → **403** `IHE_XDM_AUTHOR_NOT_SENDER` ; deux pièces emballées → **400** ;
    `IheXdmPackagingRefusedException` → **422** `IHE_XDM_PACKAGING_REFUSED`, extension `field` (un nom, jamais une
    valeur) ;
  - packager d'Interop enregistré en singleton (`TryAddSingleton`), service d'enveloppe en scoped.
- **weda2** (client-angular) :
  - port `MSS_COMPOSE_INTENT` / `MSS_DOCUMENT_SENT`, fourni par `compose-intent.provider` : demande `get-compose-intent`
    (délai 120 s) et avis `document-sent` ;
  - `WedaIntegrationService.whenSettled()` : aucune demande tant que la disponibilité n'est pas tranchée ;
  - `ComposeIntentLauncherService` racine : `take()` mis en cache, `claim()` une fois. L'intention n'est livrée qu'à une
    instance vivante de `mss-mail` (`destroyRef.destroyed`) ;
  - rédaction d'intention :
    - pièces par contenu, `packaging` recopié, badge « Données structurées » ;
    - aucun brouillon automatique, et une fermeture venue d'ailleurs demande la confirmation d'abandon (décision de la
      forge, à valider) ;
    - erreurs d'emballage affichées, rédaction laissée ouverte ;
    - `document-sent` seulement après un envoi `success` ;
  - le premier dossier chargé ne ferme plus la rédaction ouverte (corrigé à la source).
- **Pont v1** : nouveaux types `get-compose-intent` et `document-sent`, côté Weda à réaliser (`GET
  api/nova-mss/compose-intent`, `POST api/nova-mss/sent-trace`, `nova-mss-host.js`).
- **e2e** : **E2E-WEDA-003** v1 (angular `requis`, mobile non applicable).
  - Le faux hôte rend un CDA N3 synthétique avec sa demande d'emballage et retient `document-sent`.
  - Prouvé rouge dans les trois cas de la DOD (ME1–ME3).
  - L'e2e a trouvé deux courses (vert 1/3), corrigées avec tests unitaires rouges sous mutation : consigne
    `service-propre-au-composant`.
- **Validation** :
  - api-mail : intégration 846 (16 ignorés), application 3 591, api 1 190, 0 échec ;
  - règle 1b : 8 tests d'intégration `IheXdmEnvelopeSendEndToEndTests`, preuves MA1–MA8 ;
  - Angular : 11 projets verts (mss-lib 759, weda2 2 686) ;
  - `/e2e` : mobile 31/31, angular 35/35, parité verte.
- **Qualité** : Quality Gate OK, new coverage 97,3 % ; 2 × S3925 en FALSE-POSITIVE (triplet présent) ; 4 tests de
  couverture ajoutés ; lint Angular : 5 `require-example` (exemples vides) corrigés, 0 erreur.
- **Signal** : la quarantaine `E2E-COMPOSE-002` [angular] passe, et sa task de correction (task-350) est mergée :
  levée à décider par l'humain.
- **Durée du cycle** (`## Timings` de `tasks/done-task-367.md`) : **2 h 06 min** mesurées, dont `/develop` 1 h 24 min,
  `/sonar` 18 min 49 s, `/e2e` 11 min 50 s, `/review` 6 min 20 s.

---

### v1.6 — weda2 déployé vise l'api-mail de son environnement et n'accepte que l'hôte Weda exact (ANG-05, ANG-65, ANG-70) — task-369

- **Task** : task-369, statut `done` (`/review` APPROVED le 2026-10-14). Origine : audit de bugs du client Angular du
  2026-10-13. Décision humaine : la forge code sans attendre ; le **constat** de la configuration réellement servie par
  chaque environnement est fait par l'humain (tableau à remplir dans `done-task-369.md`).
- **PR** : aucune GitHub. client-angular en code-only (9 fichiers, branche `feature/nova-rewriting-mss-weda-integration`) ;
  ConfigMap et manifest (`Client/Angular/devops/k8s`) rédigés dans le task file, **à appliquer avant l'image**.
- **Amorçage** (`apps/weda2/src/runtime-config.ts`, `main.ts`) : en production, `apiEndpoint`, `authEndpoint`,
  `mssApiUrl` et `embeddedHostOrigins` doivent venir de `/assets/config.json` ; une clé absente, vide, une origine à
  joker ou un `config.json` illisible → écran « Weda ne peut pas démarrer » qui nomme les clés (jamais leurs valeurs).
  Hors production (ng serve, filet e2e), repli inchangé sur les valeurs du build.
- **Build de production** (`environment.prod.ts`) : plus aucune URL ni origine ; `withDevToolsStub` (ANG-70 : l'état des
  stores n'est plus poussé vers Redux DevTools).
- **Hôte d'embarquement** (ANG-65) : `isOriginMatching` en égalité stricte — `https://*.weda.fr` n'autorise plus rien ;
  CSP `frame-ancestors 'self' $frame_ancestors`, variable posée par `/etc/nginx/frame-ancestors.conf` (défaut de l'image :
  aucune origine ; la ConfigMap monte la liste de l'environnement). Vérifié dans un conteneur nginx-unprivileged.
- **Tests** : `runtime-config.spec.ts` (12, dont 10 rouges d'abord), `embedded-host.utils.spec.ts` (joker refusé,
  origine exacte acceptée) ; weda2 11 projets verts. E2E Angular vert au 2ᵉ passage (E2E-COMPOSE-001 instable au
  premier), mobile listé, parité verte.
- **Suivis** : constat par environnement (humain) ; ConfigMap avant image ; protéger `$frame_ancestors` de la
  substitution de la pipeline de release.

### v1.7 — Sessions de messagerie bornées dans Weda, et sortie de weda2 quand Weda ferme la session — task-365

- **Task** : task-365, statut `done` (`/review` APPROVED le 2026-10-18, après une première revue CHANGES REQUESTED).
  Origine : constat du filet e2e de task-364 (107 connexions IMAP neuves en 5 min pour un praticien). Arbitrages
  humains : pistes D + C, piste B (fermeture au `pagehide`) retirée, pas d'ordre de fermeture après une déconnexion de
  Weda (psc-auth-proxy efface son cookie `proxy_session_id`).
- **PR** : api-mail #300 (`fix/task-365-session-imap-bornee`, label `awaiting-human-merge`) ; client-angular en code-only
  (branche `feature/nova-rewriting-mss-weda-integration`, à pousser sur TFS).
- **Piste D (api-mail)** : la clé du pool IMAP/SMTP dérive du cookie `proxy_session_id` (`ProxySessionPoolKey` :
  `px-` + SHA-256 tronqué à 128 bits, séparation de domaine), avant l'en-tête `Client-Session-Id`. Commune à Weda,
  à l'iframe et à l'onglet weda2 ; la valeur brute n'atteint ni la clé, ni les journaux, ni Redis. Garde de session :
  liaison **par boîte** pour une clé du proxy (`SessionMailboxBinding.PerMailbox`, `ISessionBindingStore` en
  `SET NX` / `DEL`, borné à 500 ms), retirée par `POST /sync/logout` ; la règle 409 reste pour l'en-tête.
- **Piste C (api-mail)** : `MailServers:MaxSessionsPerMailbox` = 3 par boîte et par réplica, éviction de la moins
  récemment utilisée, jamais d'une session tenue. Le keep-alive (NOOP) ne prolonge pas une session sans requête client.
- **weda2** : `SharedSessionWatchService` — `has-session` toutes les 60 s et au retour sur l'onglet (au plus une fois
  par 15 s), `/auth/userinfo` silencieux et borné ; sortie sans ordre de fermeture (autonome : écran de connexion ;
  embarqué : `session-expired`) ; rechargement sur un autre praticien. `TokenRefreshSchedulerService` borné à
  2³¹−1 ms (boucle de `POST /auth/refresh` trouvée par l'e2e avec le jeton du banc échu en 2099).
- **Défauts trouvés en cours de cycle** : course de liaison (deux `MailboxSessionOpened` pour un chargement, E2E-SESSION-001)
  → liaison atomique ; outillage e2e en panne (port Flagsmith persistant tombé dans une plage réservée par WinNAT,
  mémorisé dans les user-secrets de l'AppHost).
- **Tests** : `ProxySessionPoolKeyIntegrationTests` (9, pipeline réel, rouges par mutation), unitaires du plafond, du
  keep-alive et de la garde ; weda2 : surveillance (16), `$probeSession`, intercepteur silencieux, planificateur.
  api-mail 6 679 verts ; weda2 2 726 verts. Sonar : Quality Gate OK, new coverage 96,7 %, 0 issue.
- **E2E** : E2E-SESSION-001 (v1), 002 (v2), 003 (v2), Angular requis, prouvés par mutation. Plafond Dovecot du banc
  redescendu de 1000 à 30 ; voies vertes (mobile 37, angular 45), parité verte.
- **Suivis (HAG)** : mesures avant/après dans Weda ; stabilité de `proxy_session_id` au refresh à constater.

### v1.4 — Interop : enveloppe IHE_XDM en mémoire d'un CDA ou d'un PDF/A, conforme à celle de Weda — task-366

- **Task** : task-366, statut `done` (`/review` APPROVED le 2026-10-11). Cycle autonome. Fondation de task-367 (envoi d'un
  document Weda par la nouvelle messagerie, api-mail emballe le document). Décision : ADR-007 amendement 6, C4 et C5.
- **PR** : `interop.cda.parser` #10, `feat/task-366-ihe-xdm-packager` → `develop`, label `awaiting-human-merge`, commit
  `4d10204` (31 fichiers).
- **Package** : `Interop.Cda.Parser` **105.0.0**, publié par la CI depuis la branche (run 105). `api-mail` reste en 101.0.0 :
  le bump est porté par task-367.
- **API** (`Interop.Cda.IheXdm`, assembly `Interop.Cda`) :
  - `IIheXdmPackager.Package(IheXdmPackageRequest)` → `IheXdmPackageResult { Zip, FileName = "IHE_XDM.ZIP",
    DocumentTypeCode, PatientId }` ; `IheXdmPackager(TimeProvider?, ILogger?)` ;
  - document : `IheXdmCdaDocument` (CDA N1 ou N3, emballé **tel quel**) ou `IheXdmPdfDocument` (CDA R2 N1 construit en
    mémoire par `CdaN1Builder`, constructeur propre : `CdaBuilder` n'est pas réutilisé) ;
  - refus : `IheXdmPackagingException { Code (MissingField, InvalidField, InvalidCda, PatientMismatch), Field }`, levée avant
    toute génération ;
  - aucune écriture disque ; journal limité au type, au format et à la taille.
- **Métadonnées** (`IheXdmMetadataWriter`, XDocument) : un champ par ligne du tableau de la task. Écarts voulus avec Weda :
  `submissionTime` en UTC, `intendedRecipient` ajouté (`||^^Internet^{adresse}`), `eventCodeList` seulement si
  `serviceEvent/code`, pas de référence parasite. Échappement HL7 des délimiteurs dans les noms (`&` → `\T\`).
- **À confirmer au validateur de l'ANS** (Manual Test Plan) :
  - système du `formatCode` d'un N1 PDF : `1.3.6.1.4.1.19376.1.2.3`, comme Weda ; l'exemple de la task écrivait `.282` ;
  - forme de l'`intendedRecipient` ;
  - libellé de la classe 60.
- **Ancienne API `[Obsolete]`** : `GeneratePackage`, `IHEPackageBuilder.Build`, `GetIheXdmZipFile`,
  `IheFileHelper.GenerateIHEZipPackage`. Aucun consommateur hors d'Interop.
- **Linux** : la suite d'Interop y était rouge (41 tests), invisible car la CI ne jouait que le build.
  - Causes : `DateTime.Parse("30/12/1899")` dans `CdaMedicationsBuilder` et `CdaPathologiesBuilder`, séparateur `\` en dur
    dans l'ancien générateur, `C:\` et données locales `D:\` dans les tests.
  - Correction : la CI joue désormais `dotnet test` (setup .NET 10).
  - Consigne `portabilite-linux` ajoutée à `conventions/csharp.md`.
- **Validation** :
  - Windows : 501 / 0 échec / 6 ignorés ;
  - Linux (docker `sdk:10.0`) : 500 / 0 / 6 ;
  - CI ubuntu verte ;
  - 94 tests neufs.
- **Preuve rouge** : 94/94 sur le bouchon, puis 22 mutations, chacune rouge sur le test qui la nomme. Le schéma du N1 est
  validé contre `CDA_SDTC.xsd` (`CDA.xsd` du dépôt ne compile pas sous .NET), validation elle-même prouvée par mutation.
- **Incident** : au `/start`, la branche a d'abord été créée et poussée sur le plan de contrôle, parce que CLAUDE.md donnait
  `interop` comme chemin du dépôt (sans `.git`). Elle a été supprimée, puis recréée dans `interop/interop.cda.parser`.
  CLAUDE.md et `/start` (garde `git rev-parse --show-toplevel`) sont corrigés, en attente de relecture humaine.
- **Suggestions reportées** :
  - `IntendedRecipients = null` → exception non typée ;
  - identifiant de structure non numérique → `sourceId` non OID (forme de Weda) ;
  - retrait de l'ancienne API après task-367.
- **Durée du cycle** (`## Timings` de `tasks/done-task-366.md`) : **32 min 17 s** mesurées.
  - `/develop` : 29 min 21 s. Les deux passes de mutation, environ 20 min de tests, ont été jouées hors `measure.sh` ;
  - `/e2e` : skip (aucune voie) ;
  - `/review` : 1 min 49 s.

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
| API Weda du dossier patient (hors forge) | Weda : `Weda/api/NovaMss/` (`NovaMssController`, `NovaMssPatientMatcher`, route `api/nova-mss`) ; code Mickey intact, règle de rapprochement copiée de `MessageBuilder` | `resolve-patient`, `filing-context`, `patient-url` (task-357) |
| Boîte désignée par l'hôte | `Client/Angular/front/libs/mss/src/core/tokens/mss-designated-mailbox.token.ts`, `core/guards/mailbox.guard.ts`, `core/utils/mailbox-address.util.ts`, `apps/weda2/src/lib/embedded/designated-mailbox.provider.ts` | `get-mailbox`, ouverture d'office, rattachement pré-rempli (task-362) |
| Faux hôte Weda (e2e) | `Client/Angular/front/e2e/mss-e2e/support/weda-host.ts` | Serveur HTTPS loopback `localhost:47399`, pont v1 côté hôte : boîte désignée (task-362), dossier patient et import (task-363) |
| Import dans le dossier patient | `Client/Angular/front/libs/mss/src/features/mail/components/weda-import/` | Fenêtre d'import, documents proposés, erreurs du pont (task-363) |
| Enveloppe IHE_XDM (Interop) | `interop/interop.cda.parser/src/Interop.Cda/IheXdm/` (package `Interop.Cda.Parser` ≥ 105.0.0) | `IIheXdmPackager` : enveloppe en mémoire d'un CDA ou d'un PDF/A, consommée par api-mail à partir de task-367 |
| Enveloppe à l'envoi (api-mail) | `Api/Mail/src/Application/Services/Implementation/IheXdmEnvelopeService.cs`, `Exceptions/IheXdm{AuthorNotSender,PackagingRefused}Exception.cs` | `AttachmentDto.Packaging` → `IHE_XDM.ZIP` sur le chemin d'envoi commun, refus 403 / 400 / 422 (task-367) |
| Intention d'envoi (weda2) | `Client/Angular/front/apps/weda2/src/lib/embedded/compose-intent.provider.ts`, `libs/mss/src/core/services/compose-intent-launcher.service.ts`, `core/tokens/mss-compose-intent.token.ts` | `get-compose-intent`, `document-sent`, livraison à une instance vivante (task-367) |
| Décisions | Weda : `docs/architecture/adr/007_integration-nouvelle-experience-messagerie.md` ; `Client/Angular/docs/ADR-2026-10-09-integration-weda-mode-embarque.md` | Contrat du pont, amendements 1 à 4 (le 3 fait foi ; le 4 fixe le repère `nova-mss` : import à la demande, WMickey garde la réception, boîte désignée par Weda) |

---

## Annexe B — Inventaire fonctionnel (2026-10-11)

- Tasks de l'EPIC : 356, 357, 363 et 367 `done` ; 362 et 366 archivées (mergées). 365 `todo`. 4 en attente dans
  `tasks/onhold/` (358 à 361) : elles portaient le mode exclusif de l'amendement 2, abandonné par
  l'amendement 3 de l'ADR-007 (décision humaine du 2026-10-10).
- Contrat du pont : version 1. Types implémentés côté hôte : `host-capabilities` (task-356) ;
  `resolve-patient`, `get-filing-context`, `open-patient-record` (task-357) ; `get-mailbox`
  (task-362), seule demande émise avant la lecture du flag (côté Weda à réaliser) ;
  `file-documents` (task-363), avec transfert d'octets, et le champ optionnel `postItLevels`
  de `get-filing-context` (côté Weda à réaliser) ; `get-compose-intent` et `document-sent` (task-367, côté Weda à
  réaliser). `file-message` et `open-draft` sont abandonnés.
- Packages : `Interop.Cda.Parser` 107.0.0 (task-366 mergée) et `HealthPlatform.Dtos.Mss` 524.0.0, consommés par api-mail
  sur la branche de task-367.
- Flags : `weda_integration` (fermé à froid, évalué sur l'identité de la boîte ouverte). Aucun
  mot-clé IMAP : `Weda` et `WedaClasse` sont abandonnés avec l'amendement 2.
- Quarantaines e2e ouvertes : 1 (E2E-COMPOSE-002, angular, task-350). Faux hôte de test et
  E2E-WEDA-001 (boîte désignée) : livrés par task-362, verts. Couverture e2e du parcours « Dossier Weda », reportée de
  task-357 à task-360 puis reprise par task-363 : E2E-WEDA-002, vert,
  avec l'import et la biologie. E2E-WEDA-003 (envoi depuis le dossier patient) : livré par task-367, vert.

---

## Annexe C — Tasks ayant contribué à cet EPIC

| Task | Statut | Contribution | RGs |
|---|---|---|---|
| task-356 | done (PR api-mail #284, en attente de merge ; Angular à pousser sur TFS) | Mode embarqué, pont v1, `WedaIntegrationService`, port `MSS_PATIENT_RECORD_GATEWAY`, flag `weda_integration`, correctif `has-session` | RG-E019-03, 04, 06 |
| task-357 | done (aucune PR forge ; Angular à pousser sur TFS ; Weda hors forge) | Panneau « Dossier Weda » : patient Weda par INS vérifiée ou candidats par traits, ouverture du dossier ; API Weda `api/nova-mss` (`resolve-patient`, `filing-context`, `patient-url`) | RG-E019-01, 02 (affichage) |
| task-362 | archivée (PR api-mail #285 mergée) | Boîte désignée par Weda : jeton `libs/mss` lu par `mailboxGuard` avant la table de décision, demande `get-mailbox`, écran de rattachement pré-rempli ; faux hôte de test et E2E-WEDA-001 ; côté Weda, `GET api/nova-mss/mailbox` | RG-E019-07 |
| task-363 | done (PR api-mail #286, en attente de merge ; Angular à commiter sur TFS ; partie Weda à faire) | Import à la demande : fenêtre d'import (patient, documents, destination, classification, commentaire, post-it), `file-documents` avec octets transférés, ni corbeille ni mot-clé, pas d'import pour la biologie et HPRIM ; E2E-WEDA-002 ; côté Weda, `POST api/nova-mss/documents` | RG-E019-01, 02, 05 |
| task-366 | archivée (PR interop.cda.parser #10 mergée ; package 107.0.0) | Enveloppe IHE_XDM en mémoire d'Interop (`IIheXdmPackager`) : CDA emballé tel quel ou PDF/A en N1, métadonnées conformes à Weda, refus typé ; ancienne API obsolète ; suite d'Interop verte sous Linux | — (fondation de l'envoi, task-367) |
| task-367 | done (PRs dtos-mss #44 et api-mail #289, en attente de merge ; Angular à commiter sur TFS ; partie Weda à faire) | Envoi depuis le dossier patient : `AttachmentDto.Packaging`, `IheXdmEnvelopeService` sur le chemin d'envoi, refus 403 / 400 / 422 ; rédaction d'intention (`get-compose-intent`, `document-sent`) ; E2E-WEDA-003 ; côté Weda, `compose-intent` et `sent-trace` | — |
| task-365 | done (PR api-mail #300, en attente de merge ; Angular à commiter sur TFS) | Sessions de messagerie bornées : clé de pool dérivée de la session du proxy, liaison par boîte, plafond par boîte, keep-alive sans prolongation ; surveillance de la session partagée dans weda2 ; E2E-SESSION-001 à 003, plafond Dovecot du banc à 30 | — |
| task-358 | en attente (`tasks/onhold/`, amendement 3) | API d'intégration api-mail `api/v1/integration`, canal serveur Weda → api-mail, compteur de non-lus de l'en-tête | — |
| task-359 | en attente (`tasks/onhold/`, amendement 3) | Réception des CR de biologie en bannette HPRIM sans WMickey, mots-clés `Weda` / `WedaClasse` | — |
| task-360 | en attente (`tasks/onhold/`, amendement 3) | Classer par identifiants via le canal serveur ; remplacée par task-363 | — |
| task-361 | en attente (`tasks/onhold/`, amendement 3) | « Envoyer par MSSanté » depuis un document Weda vers la rédaction de weda2 ; remplacée par task-367 | — |
