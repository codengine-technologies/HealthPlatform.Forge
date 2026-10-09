# E019 — Changelogs (vue ingénierie)

> **Audience** : équipes techniques, backlog, dette.
> Vue produit : [E019-integration-de-la-nouvelle-messagerie.md](E019-integration-de-la-nouvelle-messagerie.md).
> **Dernière mise à jour** : 2026-10-09 (v1.0)

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

---

## Annexe A — Cartographie des briques applicatives

| Brique | Emplacement | Rôle |
|---|---|---|
| Flag d'intégration | `Api/Mail/src/Application/Constants/FeatureFlags.cs`, `src/AppHost/FlagsmithSeeder.cs` | `weda_integration`, fermé à froid, évalué par identité |
| Mode embarqué et pont | `Client/Angular/front/apps/weda2/src/lib/embedded/` | `EmbeddedHostService`, `WedaIntegrationService`, `WedaPatientRecordGateway`, utilitaires d'origine |
| Port du dossier patient | `Client/Angular/front/libs/mss/src/core/tokens/mss-patient-record-gateway.token.ts`, `core/models/weda-patient-record.model.ts` | Contrat vu du module messagerie |
| Délégation de l'auth | `apps/weda2/src/lib/auth/services/authentication-callback.service.ts`, `auto-logout.service.ts`, `interceptors/utils/auth-interceptor.utils.ts` | Pas de redirection dans l'iframe, `has-session` hors intercepteur |
| Politique d'affichage en iframe | `Client/Angular/front/nginx.conf` | `frame-ancestors 'self' https://*.weda.fr` |
| Hôte Weda (hors forge) | Weda : `Weda/FolderMedical/WedaEchanges/Default.aspx(.cs)` | Bandeau, iframe, gestionnaire du pont |
| Décisions | Weda : `docs/architecture/adr/007_integration-nouvelle-experience-messagerie.md` ; `Client/Angular/docs/ADR-2026-10-09-integration-weda-mode-embarque.md` | Contrat du pont, amendements 1 et 2 |

---

## Annexe B — Inventaire fonctionnel (2026-10-09)

- Tasks de l'EPIC : 6. 1 `done` (356), 1 `wip` (357), 4 `todo` (358 à 361).
- Contrat du pont : version 1. Types implémentés côté hôte : `host-capabilities` (task-356) ;
  `resolve-patient`, `get-filing-context`, `open-patient-record` (task-357, en attente de
  validation).
- Flags : `weda_integration` (fermé à froid). Mots-clés IMAP prévus : `Weda`, `WedaClasse`
  (task-359).
- Quarantaines e2e ouvertes : 1 (E2E-COMPOSE-002, angular, task-350).

---

## Annexe C — Tasks ayant contribué à cet EPIC

| Task | Statut | Contribution | RGs |
|---|---|---|---|
| task-356 | done (PR api-mail #284, en attente de merge ; Angular à pousser sur TFS) | Mode embarqué, pont v1, `WedaIntegrationService`, port `MSS_PATIENT_RECORD_GATEWAY`, flag `weda_integration`, correctif `has-session` | RG-E019-03, 04, 06 |
| task-357 | wip | Panneau « Dossier Weda » : patient Weda par INS vérifiée ou candidats par traits, ouverture du dossier ; API Weda `api/mss/filing` (`resolve-patient`, `context`, `patient-url`) | RG-E019-01, 02 (affichage) |
| task-358 | todo | API d'intégration api-mail `api/v1/integration`, canal serveur Weda → api-mail, compteur de non-lus de l'en-tête | — |
| task-359 | todo | Réception des CR de biologie en bannette HPRIM sans WMickey, mots-clés `Weda` / `WedaClasse` | RG-E019-05 |
| task-360 | todo | Classer en un clic dans le dossier patient Weda | RG-E019-01, 02 |
| task-361 | todo | « Envoyer par MSSanté » depuis un document Weda vers la rédaction de weda2 | — |
