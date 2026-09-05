# todo-task-184.md — INS dans les URL et données patient en clair dans les logs et la télémétrie

**Repos**: api-mail, client-blazor, client-angular, client-mobile
**Dependencies**: —
**Epic**: E009

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axe confidentialité).
> Viole frontalement le garde-fou projet « jamais d'INS, de NIR, de NIA ni de
> contenu CDA/MSSanté en clair dans les logs, les URL ou la télémétrie ».

> ### Re-vérification du 2026-08-23 — **toujours pertinente, et aggravée sur un point**
>
> Chaque preuve rejouée sur `develop`. Les numéros de ligne du bloc « Preuve »
> datent du 2026-07-25 ; **la colonne « au 2026-08-23 » fait foi**.
>
> | Preuve | 2026-07-25 | Au 2026-08-23 | État |
> |---|---|---|---|
> | INS en segment d'URL | `PatientsController.cs:25,113,147,163,244` ; `BiologyController.cs:42` | **`PatientsController.cs:33,137,175,195,280`** (dont un `[HttpPut("ins/{ins}/opposition")]`) ; **`BiologyController.cs:54`** | inchangé |
> | Masquage limité à `token=` | `RequestLoggingMiddleware.cs:91` | regex `:25`/`:35` (query seule), `RequestPath` poussé en **`:105`** | inchangé |
> | INS et traits journalisés | `:30,122,152,201,252` / `:75` | **`:38,146,180,200,288`** ; traits groupés en **`:233-234`** ; filtre entier en **`:91`** ; `BiologyController.cs:59,74` | inchangé |
> | Requête brute en `Error` | `SemanticSearchService.cs:114` | **`:114` — identique** | inchangé |
> | Diagnostics IA | `:67-68,145-146,291` | **`:67,145,291` — identiques** | inchangé |
> | Anonymisation contournée | `UserContextEnricherMiddleware.cs:530-536`, `:553-558` | **`:572-583`** et **`:596-603`** ; helpers déplacés en `:517`/`:540` | **aggravé** |
>
> **Aggravation à retenir** : les deux chemins de rejet loguent désormais aussi
> `Path={Path}` (`:581`, `:601`). Les deux défauts de cette task **se composent**
> — une requête `GET /patients/ins/{ins}/…` rejetée en 403 écrit l'INS **et**
> l'adresse MSSanté **et** le `sub` Keycloak complets dans la même ligne de log.
> Ce n'était pas le cas au 2026-07-25.

## Objective

Supprimer les fuites de données de santé et de traits d'identité patient vers les
journaux, la télémétrie et les URL. Quatre familles de fuites documentées, toutes
émises à un niveau qui passe les seuils configurés — elles atterrissent donc
réellement dans Seq et dans l'export OTLP, lisibles par un public bien plus large
que celui habilité aux DSCP.

**US full-stack (requalifiée le 2026-09-05)** : la task était déclarée
`**Repos**: api-mail` / `Single frontend: true`. C'est faux sur deux plans,
vérifié sur `develop` :

1. Les six routes portant l'INS en chemin sont appelées par **les trois
   frontends** — les sortir de l'URL sans basculer les appelants casse
   l'application (règle 11, US-complete).
2. **Chaque frontend a ses propres fuites**, indépendantes du backend : l'INS
   dans la barre d'adresse du navigateur (Blazor), la requête de recherche
   nominative journalisée côté client (Blazor), l'INS dans un identifiant
   d'objet de state (Angular). Aucune n'est corrigée par un correctif serveur.

### Preuve (état actuel du code)

1. **INS en segment d'URL** — cinq routes prennent l'INS en **chemin** :
   `src/Api/Controllers/V1/PatientsController.cs:25,113,147,163,244`
   (`[HttpGet("ins/{ins}")]`, `ins/{ins}/medical-documents`,
   `ins/{ins}/opposition`, …) et `src/Api/Controllers/V1/BiologyController.cs:42`.
   `src/Api/Middleware/RequestLoggingMiddleware.cs:91` pousse `RequestPath` dans le
   contexte Serilog et ne masque que `token=` en query string : **rien** ne masque
   les segments de chemin. L'INS voyage donc aussi dans les logs d'accès de tout
   reverse-proxy.
2. **INS et traits journalisés explicitement** — `PatientsController` logue
   `ins={Ins}` (`:30,122,152,201,252`), et `:201` logue ensemble `lastName`,
   `firstName`, `birthDate`, `gender` ; `:75` sérialise le filtre entier
   (`{@Filters}`). `BiologyController.cs:47,62` fait de même.
3. **Requête de recherche brute en Error** —
   `src/Application/Services/Implementation/SemanticSearchService.cs:114` :
   `_logger.LogError(ex, "Error performing hybrid search for query: {Query}", query)`.
   Le même fichier est pourtant exemplaire ailleurs (`:53`, `:212` ne loguent que
   `queryLength`), et `SearchController.cs:62` porte le commentaire
   « task-071 — PGSSI-S : never log the raw query (potentially nominative) ». Le
   chemin d'erreur a été oublié. Les requêtes sont bel et bien nominatives : le
   code embarque un `PatientNameExtractor.ExtractPatientFromQuery`.
4. **Diagnostics IA** — `src/Api/Controllers/V1/AiDiagnosticsController.cs:67-68`,
   `:145-146`, `:291` loguent la requête brute **et** le nom et prénom du patient
   auto-détecté (`"🔍 Patient auto-détecté dans la requête: {FirstName} {LastName}"`),
   en `Information`.
5. **Anonymisation contournée** —
   `src/Api/Middleware/UserContextEnricherMiddleware.cs:530-536` et `:553-558` :
   le middleware définit `AnonymiseEmail` et `TruncateSub` et les applique
   partout… sauf dans ses deux chemins de rejet, qui loguent l'adresse MSSanté du
   praticien et son `sub` Keycloak en entier. (PII professionnelle, pas DSCP —
   portée moindre, mais la politique du fichier est contredite.)

### Preuve — fuites propres aux frontends (relevé du 2026-09-05)

6. **`client-blazor` — INS dans la barre d'adresse** :
   `Src/Modules/Mss/Plugin/Widgets/PatientWidgetComponent.razor:212` et `:223`
   naviguent vers `/Patient?ins={ins}` ;
   `Src/Modules/Mss/Plugin/Pages/Patient.razor:41-45` reçoit l'INS en paramètre
   de query. L'INS atterrit donc dans l'historique du navigateur, dans le
   `Referer` de toute requête sortante de la page, et dans les journaux de tout
   proxy servant le SPA. C'est la même fuite que le point 1, côté client, et
   **aucun masquage serveur ne la couvre**.
7. **`client-blazor` — requête brute et INS journalisés côté client** :
   `Src/Modules/Mss/Plugin/Pages/Patient.razor:82` logue `{Ins}` sur le chemin
   d'erreur ; `Src/Modules/Mss/Application/Services/SemanticSearchService.cs:47`
   (`LogError`) et `:57` (`LogInformation`) loguent `{Query}` brute. C'est le
   **jumeau exact côté client** du point 3 — même défaut, y compris l'oubli du
   chemin d'erreur.
8. **`client-angular` — INS dans un identifiant de state** :
   `libs/mss/src/features/mail/mss-mail.component.ts:586-588` fabrique un dossier
   virtuel dont l'`id` et le `path` valent `__patient__/${ins}`. À établir pendant
   l'implémentation : si ce `path` est repris dans un appel API (déplacement en
   masse, rechargement de dossier), l'INS repart en URL ; sinon la fuite reste
   locale et il suffit de substituer le handle technique.
9. **`client-mobile`** — consommateur des routes
   (`src/app/core/services/mss-api.service.ts:333,345,540,547,560`) ; aucune
   journalisation nominative détectée. Bascule d'appels uniquement, plus la mise
   à jour des tests qui figent les URL actuelles
   (`mss-api.service.spec.ts:433-492`).

### Contenu attendu

1. **INS hors des URL** : les routes concernées ne doivent plus véhiculer l'INS en
   segment de chemin.

   **Voie retenue (2026-09-05) : handle technique + résolution en POST.**
   `MailPatient` a déjà une clé primaire non signifiante
   (`src/Domain/Entities/MailPatient.cs:17`, `Guid Id`) — rien à inventer.

   | Aujourd'hui | Cible |
   |---|---|
   | `GET patients/ins/{ins}` | `POST patients/resolve` — INS dans le **corps**, renvoie le patient + son `Id` |
   | `GET patients/ins/{ins}/medical-documents` | `GET patients/{patientId:guid}/medical-documents` |
   | `GET` / `PUT patients/ins/{ins}/opposition` | `GET` / `PUT patients/{patientId:guid}/opposition` |
   | `GET patients/ins/{ins}/validate-ins` | `POST patients/validate-ins` — corps `{ ins }` |
   | `GET biology/ins/{ins}` | `GET biology/patients/{patientId:guid}` |

   Le `POST` de lecture n'est pas une entorse locale : `POST search/advanced`
   (`PatientsController.cs:86`) existe déjà pour exactement cette raison. Le corps
   n'est journalisé ni par le middleware, ni par un reverse-proxy, ni par
   l'historique du navigateur, ni par le `Referer`. `validate-ins` est le seul cas
   qui ne peut **pas** prendre de handle : il valide un INS qui n'existe pas
   forcément en base — d'où le POST à corps.

   **Écarté** : un pseudonyme HMAC de l'INS en segment. Stateless et séduisant,
   mais c'est un identifiant patient stable et corrélable qui reste dans tous les
   journaux traversés — la fuite est déplacée, pas fermée.

   **Séquencement (règle 11, US-complete)** : les nouvelles routes sont livrées
   **en parallèle** des anciennes, les trois frontends basculent dessus **dans la
   même US**, et les anciennes routes sont marquées `[Obsolete]` + `Deprecated`
   OpenAPI. **Leur suppression fait l'objet d'une task de suite** — elle ne peut
   intervenir qu'après un délai de grâce couvrant les clients non maîtrisés.
   Le **masquage des segments de chemin** dans la journalisation et la télémétrie
   reste dû ici quoi qu'il arrive, puisque les anciennes routes survivent à cette
   task.

2. **Frontends — trois chantiers distincts** :
   - **`client-blazor`** : bascule des six appels
     (`Src/Modules/Mss/Application/Services/PatientService.cs:37,45,53,61,68,75`) ;
     **sortie de l'INS de la barre d'adresse** — `/Patient?ins={ins}` devient un
     deep-link porteur du handle technique ; assainissement des logs client
     (`Patient.razor:82`, `SemanticSearchService.cs:47,57` → longueurs et
     identifiants techniques, jamais `{Query}` ni `{Ins}`).
   - **`client-angular`** : bascule des six appels
     (`libs/mss/src/core/services/mss-api.service.ts:1162,1209,1230,1245,1263,1278`)
     et substitution de l'INS dans `__patient__/${ins}`
     (`features/mail/mss-mail.component.ts:586-588`). Rappel : repo **code-only**,
     la forge n'y touche jamais à git.
   - **`client-mobile`** : bascule des cinq appels
     (`src/app/core/services/mss-api.service.ts:333,345,540,547,560`) et des tests
     qui figent les URL (`mss-api.service.spec.ts:433-492`).

3. **Journalisation assainie** : ni INS, ni nom, prénom, date de naissance, sexe,
   ni requête de recherche brute, ni contenu de message ou de document. Remplacer
   par des grandeurs non identifiantes (longueurs, compteurs, identifiants
   techniques) — le fichier `SemanticSearchService` (backend) montre déjà le bon
   patron.
4. **Règle homogène** : appliquer l'anonymisation existante (`AnonymiseEmail`,
   `TruncateSub`) sur **tous** les chemins du middleware, y compris les rejets.
5. **Masquage du chemin — trois points d'émission, un seul assainisseur** :
   `RequestLoggingMiddleware` pousse le path brut en `:105` (`RequestPath`), le
   réémet dans le `LogDebug` suivant, **et** dans le message de
   l'`InvalidOperationException` du `catch` ; `UserContextEnricherMiddleware:581`
   et `:601` loguent `Path={Path}`. Côté télémétrie,
   `src/Api/DependencyInjectionExtensions.cs:180` ne pose qu'un `Filter` : sans un
   `EnrichWithHttpRequest` réécrivant le tag `url.path`, l'INS part en OTLP même
   une fois Serilog assaini (`http.route` reste le gabarit `ins/{ins}`, lui est
   sain). Un unique assainisseur canonique, appliqué aux cinq endroits.
6. **Garde-fou anti-récidive** : un contrôle mécanique (analyseur, test, revue
   outillée) empêchant de journaliser un champ marqué sensible. La récidive est
   avérée : task-071 avait déjà durci ce point sur le chemin nominal, et le chemin
   d'erreur juste à côté est passé au travers.

### Arbitrage tranché — traits patient en query string

Deux routes voisines fuient des traits d'identité en **query string**, et le
scrub ne connaît que `token=` (`RequestLoggingMiddleware.cs:25-35`) :
`GET patients/search?lastName=` (`PatientsController.cs:59`) et
`GET patients/match` (`:220`, traits groupés loggés en `:233-234`). Même famille
de fuite, même correctif, mêmes fichiers touchés — **inclus dans cette task**
plutôt que reportés : les traiter séparément imposerait de rouvrir les mêmes
controllers et le même middleware une seconde fois.

### Hors scope

- Le contenu clinique envoyé au fournisseur d'IA → task-178.
- Les DSCP écrites sur disque → task-185.
- La complétude du journal d'audit → task-186.
- La **suppression** des routes `ins/{ins}` dépréciées → task de suite, après
  délai de grâce.

## Definition of Done

### Socle

- [ ] Build passes (0 errors) sur les quatre repos
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés) sur les quatre repos

### DOD — backend, journalisation

- [ ] Test : aucun log émis par les chemins listés ne contient d'INS, de nom, de
      prénom, de date de naissance ni de requête brute (tests sur les cinq
      emplacements identifiés — ils doivent échouer sur le code actuel)
- [ ] Test : le chemin d'**erreur** de la recherche sémantique ne logue que des
      grandeurs non identifiantes (le cas précis oublié par task-071)
- [ ] Test : `RequestPath` journalisé et exporté en télémétrie est **masqué** sur
      les routes portant une INS — couvrant les **cinq** points d'émission
      (contexte Serilog, `LogDebug`, message d'exception, les deux `Path={Path}`
      du middleware d'identité) **et** le tag OTLP `url.path`
- [ ] Test : les deux chemins de rejet du middleware appliquent bien
      `AnonymiseEmail` / `TruncateSub`
- [ ] Test : les traits passés en query string (`search`, `match`) sont masqués
      dans `RequestQuery`
- [ ] Garde-fou anti-récidive en place et **prouvé** par un cas de test (une
      tentative de journalisation d'un champ sensible est détectée)

### DOD — backend, routes

- [ ] Les cinq routes cibles existent et sont testées (≥ 1 test d'intégration par
      route : cas passant + 1 mode d'échec)
- [ ] Les six anciennes routes `ins/{ins}` sont marquées `[Obsolete]` et
      `Deprecated` dans OpenAPI, et **fonctionnent toujours** (1 test de
      non-régression par route)
- [ ] Test d'architecture : aucun gabarit de route exposé par `EndpointDataSource`
      ne contient un paramètre au nom sensible (`ins`, `nir`, `lastName`,
      `firstName`, `birthDate`), hors la liste explicite des routes dépréciées —
      liste qui ne peut que décroître. Ce test échoue sur le code actuel.
- [ ] Décision documentée sur la sortie de l'INS des URL (voie retenue, calendrier,
      impact des trois frontends) ; masquage livré dans tous les cas

### DOD — client-blazor

- [ ] Les six appels de `PatientService` visent les nouvelles routes ; tests
      unitaires vérifiant l'URL émise (aucune ne contient l'INS)
- [ ] `/Patient?ins={ins}` ne véhicule plus l'INS : test vérifiant que la
      navigation depuis `PatientWidgetComponent` émet un handle technique
- [ ] Test : `SemanticSearchService` ne logue `{Query}` sur **aucun** chemin, y
      compris le chemin d'erreur
- [ ] Test : le chemin d'erreur de `Patient.razor` ne logue pas `{Ins}`

### DOD — client-angular

- [ ] Les six appels de `mss-api.service.ts` visent les nouvelles routes ; tests
      `HttpTestingController` vérifiant l'URL émise
- [ ] Le dossier virtuel patient n'embarque plus l'INS dans son `id`/`path` ; test
      de non-régression sur la sélection du dossier patient
- [ ] Constat consigné dans la task : le `path` du dossier virtuel est — ou n'est
      pas — repris dans un appel API (vérification faite, résultat écrit)

### DOD — client-mobile

- [ ] Les cinq appels de `mss-api.service.ts` visent les nouvelles routes ;
      `mss-api.service.spec.ts` mis à jour et vert
- [ ] Test : aucune URL émise par le service ne contient d'INS

### DOD — bout en bout

- [ ] Vérification de bout en bout dans Seq : aucune donnée identifiante sur un
      parcours patient complet, depuis **chacun** des trois frontends

## Manual Test Plan

1. Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
2. Ouvrir Seq et filtrer sur `mss.mail`.
3. Parcours patient (données de test anonymisées) : ouvrir un dossier patient,
   lister ses documents médicaux, poser une opposition MSS, consulter un résultat
   de biologie.
4. **Attendu dans Seq** : aucune ligne ne contient l'INS, ni le nom/prénom/date de
   naissance. Avant correctif, l'INS apparaît à la fois dans les messages et dans
   `RequestPath`.
5. **Recherche** : lancer une recherche nominative (« résultats Dupont »), puis
   provoquer un échec de recherche (arrêter le service de recherche vectorielle) →
   la ligne d'erreur ne contient **pas** la requête. Avant correctif, elle la
   contient intégralement.
6. **Diagnostics IA** : appeler un endpoint de diagnostic avec une requête
   contenant un nom de patient → ni la requête ni le nom détecté n'apparaissent.
7. **Rejet d'identité** : forger un jeton sans le claim `mssEmail` → la ligne de
   rejet montre une adresse **anonymisée** et un `sub` tronqué.
8. Vérifier le même résultat côté export OTLP (backend de télémétrie).

### Frontends — écran par écran

9. **Blazor** (`cd Client/Blazor && dotnet run`) : ouvrir le widget patient,
   cliquer un patient → **la barre d'adresse ne doit plus contenir l'INS**.
   Ouvrir la console du navigateur : ni INS, ni requête de recherche brute.
   Onglet Réseau : aucune URL appelée ne contient l'INS. Avant correctif,
   `/Patient?ins=...` est visible dans la barre d'adresse.
10. **Angular** (`cd Client/Angular/front && npm start`) : depuis la liste de
    mails, filtrer par patient → l'en-tête du dossier virtuel s'affiche
    correctement, et l'onglet Réseau ne montre aucune URL porteuse d'INS.
11. **Mobile** (`cd Client/Mobile && npm start`) : ouvrir une fiche patient, ses
    documents médicaux, poser une opposition → onglet Réseau sans INS dans les URL.
12. Sur les trois frontends : le parcours reste **fonctionnellement identique**
    (mêmes données affichées, deep-link toujours utilisable). La sortie de l'INS
    des URL ne doit rien retirer au médecin.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR honorées** : correctif de conformité PGSSI-S — confidentialité
  et journalisation (une trace ne doit jamais elle-même exposer la donnée)
- **INS** : **cœur du sujet** — l'INS ne doit apparaître ni dans les logs, ni dans
  la télémétrie, ni dans une URL (les URL sont journalisées par toute
  l'infrastructure traversée), **y compris les URL des frontends** : barre
  d'adresse, historique du navigateur et en-tête `Referer` sont autant de vecteurs
  hors de portée d'un masquage serveur
- **Authentification PS** : inchangée
- **Habilitations** : la population habilitée à lire Seq et la télémétrie est plus
  large que celle habilitée aux DSCP — c'est précisément ce qui qualifie la fuite
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : les évènements restent journalisés — c'est leur **contenu**
  qui est assaini. Ne pas réduire la couverture du journal en corrigeant (voir
  task-186 qui l'étend)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — vérifier que Seq et le backend de télémétrie sont
  eux-mêmes dans un périmètre conforme ; si non, la fuite est aggravée (à
  confirmer avec le humain)
- **AIPD / impact RGPD** : **à mettre à jour** — divulgation de données de santé
  et de traits d'identité à une population non habilitée. Qualifier la portée avec
  le DPO (rétention Seq, accès, période) et statuer sur la purge des journaux
  existants.

## Branches

Branche unique sur les repos pushables : `feat/task-184-ins-hors-urls-et-logs`
(créée depuis `origin/develop` le 2026-09-05).

- `api-mail` (pushed) : feat/task-184-ins-hors-urls-et-logs — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-184-ins-hors-urls-et-logs
- `client-blazor` (pushed) : feat/task-184-ins-hors-urls-et-logs — https://github.com/codengine-technologies/HealthPlatform.Client/tree/feat/task-184-ins-hors-urls-et-logs
- `client-mobile` (pushed) : feat/task-184-ins-hors-urls-et-logs — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-184-ins-hors-urls-et-logs
- `dtos-mss` (pushed, auto-inclus) : feat/task-184-ins-hors-urls-et-logs — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-184-ins-hors-urls-et-logs
- `client-angular` (code-only) : la forge écrit sur la branche checked out dans `Client/Angular/` — snapshot au moment du `/start` : **`feature/nova-rewriting-mss`**. Humain gère branche, commit, push, PR TFS.

## Timings

*(généré par `tools/timing/report.sh --task task-184 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 2 min 26 s | — | — | — | — |
| /develop | ok | 54 min 27 s | 11 (2 min 13 s) | 14 (7 min 19 s) | — | api-mail 5B/7T, client-blazor 3B/3T, client-mobile 1B/1T, client-angular 2B/3T |
| /sonar | ok | 22 min 39 s | 3 (41 s) | 12 (11 min 12 s) | 2 (58 s) | 1 itération(s), api-mail 3B/12T |
| /lint-angular | ok | 5 min 41 s | 1 (22 s) | 2 (46 s) | — | 1 itération(s), client-angular 1B/2T |
| /lint-mobile | ok | 42 s | — | — | — | — |
| /verify-visual | skipped | 17 s | — | — | — | aucun écran mobile touché — diff limité à mss-api.service.ts et sa spec |
| /review | ok | 7 min 47 s | 4 (28 s) | 4 (1 min 46 s) | — | dtos-mss 1B/0T, api-mail 1B/1T, client-blazor 1B/1T, client-mobile 1B/1T, client-angular 0B/1T |
| **Total cycle** | | **1 h 34 min** | **19 (3 min 45 s)** | **32 (21 min 05 s)** | **2 (58 s)** | |

Autres commandes mesurées : lint ×4 (1 min 21 s), nuget-wait ×1 (14 s), restore ×1 (3.0 s)

## Develop log

- **Repos touchés** : `dtos-mss`, `api-mail`, `client-blazor`, `client-mobile`, `client-angular` (code-only)
- **DTOs publiés** : `HealthPlatform.Dtos.Mss` 381.0.0 → **449.0.0** (nouveau `InsRequestDto`) ; consommateurs bumpés (`api-mail`, `client-blazor`)
- **Interop publié** : aucun changement

### Commits

| Repo | SHA | Message |
|---|---|---|
| `dtos-mss` | `7ad998f` | `feat(dto): add InsRequestDto to carry an INS in a request body` |
| `api-mail` | `e513703` | `chore(deps): bump HealthPlatform.Dtos.Mss to 449.0.0` |
| `api-mail` | `b39d064` | `feat(api): take the INS out of URLs, logs and telemetry` |
| `api-mail` | `e17eb11` | `refactor(api): simplify pass (/simplify) — task-184` |
| `client-blazor` | `69183b9` | `feat(mss): address patients by handle and stop logging identifiers` |
| `client-mobile` | `c28a5b7` | `feat(mobile): address patients by handle instead of INS in URLs` |
| `client-angular` | — | **non committé** (code-only), branche `feature/nova-rewriting-mss` |

### Build / test

| Repo | Build | Tests |
|---|---|---|
| `dtos-mss` | ✓ | n/a |
| `api-mail` | ✓ | ✓ **4093** (136 domain + 464 infra + 787 api + 426 integration + 2280 application), 0 échec, 16 skipped préexistants |
| `client-blazor` | ✓ | ✓ **168**, 0 échec, 2 skipped préexistants |
| `client-mobile` | ✓ | ✓ **807**, 0 échec |
| `client-angular` | ✓ (config `development`) | ✓ **329** (`mss-lib`), 0 échec |

> ⚠️ **`nx build mss --configuration=production` échoue, et c'est préexistant** :
> `apps/mss/src/environments/environment.prod.ts` est **absent du HEAD de la
> branche humaine** `feature/nova-rewriting-mss`, alors que le projet le
> référence dans ses `file replacements`. Le fichier **existe sur `origin/next`** :
> il a été supprimé par le commit `7de0cee3 « First MSS implementation »` de
> cette branche, bien avant task-184, et l'arbre ne porte aucune suppression non
> committée. Aucun fichier d'environnement n'est touché par cette task — les
> deux `environment.ts` modifiés sont le WIP humain constaté au pré-flight. Le
> build passe en configuration `development`, et `tsc --noEmit` sur la lib `mss`
> est propre.

### Voie retenue pour la sortie de l'INS des URL

`MailPatient.Id` (`Guid`, clé primaire non signifiante) sert de **handle**.
Les deux opérations dont l'entrée est réellement un INS passent par le **corps**
de la requête (`POST patients/resolve`, `POST patients/validate-ins`) ; toutes
les autres adressent le patient par son handle. HMAC de l'INS écarté : un
pseudonyme stable et corrélable déplace la fuite au lieu de la fermer.

La substitution est faite **à la frontière API** : les couches application et
infrastructure restent clés par INS, donc la task change ce qui voyage dans une
URL et rien d'autre.

Les six routes `ins/{ins}` restent servies, `[Obsolete]` + `Deprecated` OpenAPI,
le temps du délai de grâce. **Leur suppression est une task de suite.**

### Ce que les garde-fous ont trouvé et que la task ne listait pas

Les tests d'architecture ont été écrits avant les correctifs, et ils ont
immédiatement révélé **onze fichiers** au-delà des cinq preuves du task file —
tous corrigés dans cette task :

- **api-mail** : `RequestLoggingMiddleware` émettait le chemin brut sur **cinq**
  sites (la task en citait un) ; `UserContextEnricherMiddleware` sur **sept** ;
  `PatientContactService`, `PatientContactPublisher`,
  `CreatePatientContactConsumer` et `BiologyRepository` journalisaient l'INS
  (dont un message d'exception interpolé, invisible à toute regex de template) ;
  `CdaParsingService` le nom du patient ; la ligne « filtres actifs » de
  `SemanticSearchService` concaténait INS + nom + objet du message.
- **client-blazor** : **seize** templates journalisaient la requête brute, un
  INS ou un nom, dont neuf dans `SemanticSearchService` — le jumeau exact du
  défaut backend de task-071, chemin d'erreur compris.
- **client-angular** : `?patient={ins}` **et** `?ins={ins}` mettaient l'INS dans
  la barre d'adresse du SPA. Non listé dans la task ; aucun masquage serveur ne
  l'atteint.
- **client-angular** : réponse au constat demandé par la DOD — le `path` du
  dossier virtuel `__patient__/{…}` **n'est pas** repris dans un appel API
  (vérifié : deux occurrences, toutes deux locales, comparaisons de sélection).
  L'INS y est tout de même remplacé par le handle, et le libellé affiché
  neutralisé : laisser un identifiant dans un champ `path` de dossier, c'est
  parier que personne ne le réutilisera dans une URL de dossier.

### Passe qualité (`/simplify`)

- **Appliquée et committée** : `api-mail` (`e17eb11`) — la résolution handle→INS
  existait en double dans `PatientsController` et `BiologyController` ; extraite
  en `PatientHandleResolver`. Re-validation build + tests : verte.
- **Sans changement** : `client-blazor`, `client-mobile` — diffs mécaniques
  (substitution d'URL + assainissement de logs), rien à factoriser.
- **Sans changement, code-only** : `client-angular` — idem, et aucune opération
  git sur ce repo.
- **Sautée (porteurs de contrat)** : `dtos-mss`.

### Findings laissés ouverts (hors périmètre, à instruire)

- **Famille « Annuaire Santé »** : ~35 sites (`ContactController`,
  `DirectoryController`, 7 stratégies `AnnuaireSante/`) journalisent `{Query}`.
  La requête porte sur un **annuaire public de professionnels**, pas sur un
  patient — exposition matériellement moindre que les quatre familles de la
  task, dans un sous-système qu'elle ne couvre pas. **Exemptés explicitement**
  dans `SensitiveLogTemplateScanTests`, avec le raisonnement, plutôt que retirés
  de la regex : rien n'empêche un praticien de taper un nom de patient dans une
  recherche d'annuaire. À arbitrer en task de suite.
- **Suppression des six routes `ins/{ins}` dépréciées** : task de suite, après
  délai de grâce.

### Écart assumé au playbook

Les `packages.lock.json` ont été committés (le playbook dit de ne pas les
stager). Ils sont **suivis par git** et leur diff est exactement la montée de
version du DTO : les laisser modifiés laissait un arbre sale au pré-flight de
`/review`. Aucun `--locked-mode` n'est utilisé en CI, donc l'un ou l'autre
fonctionne ; l'arbre propre a été préféré.

- **DOD self-check** : tous les items commandables sont vérifiés par un test
  (voir les quatre blocs de DOD). Restent déférés au test manuel (HAG) :
  la vérification de bout en bout dans Seq, l'export OTLP, et les trois
  parcours frontend écran par écran.
- **Next step** : `/sonar task-184`

## Sonar log

Analyse complète sur `feat/task-184-ins-hors-urls-et-logs`
(`healthplatform-api-mail`, SonarQube 9.9.8), 1 itération.

### KPIs

| Métrique | Baseline | Final | |
|---|---|---|---|
| **Quality Gate** | OK | **OK** | ✅ |
| Bugs | 0 | **0** | ✅ |
| Vulnerabilities | 0 | **0** | ✅ |
| Security hotspots | 3 | **3** | = (préexistants) |
| Code smells | 66 | **65** | ▼ |
| Code smells (new code) | 40 | **38** | ▼ |
| Coverage | 88,2 % | **88,3 %** | ▲ |
| Coverage (new code) | — | **90,8 %** | ✅ |
| Duplication | 0,4 % | **0,4 %** | = |
| Reliability / Security / Maintainability | A / A / A | **A / A / A** | ✅ |

### Ce qui a été corrigé

**Deux findings, les deux sur du code de cette task** (`b2d3e57`) :

- **S3267** — `SensitiveRequestDataSanitizer.IsSensitiveQueryKey` : boucle
  explicite là où `Contains` + `StringComparer.OrdinalIgnoreCase` suffit.
- **S125** — `RequestLoggingMiddleware` : un commentaire de prose relevé comme
  code commenté, à cause d'un point-virgule en fin de ligne.

Les deux sont des **règles nouvelles** pour la forge → entrées créées dans
`conventions/csharp.md` (S3267, S125), pour que `/develop` les applique d'emblée.

### Les 38 restants — pourquoi ils restent

**Aucun n'appartient à task-184.** Le *new code period* couvre plusieurs commits
récents de `develop`, pas seulement ce diff : S3604 (18) dans
`MailClientSession`, `ImapService`, `SmtpService`… ; CA1861 (9) dans des tests
d'embedding ; S107 (3), S125 (3), S3267 (2), CA1859, S4456, S4457, xUnit2032.
Vérifié fichier par fichier contre `git diff --name-only origin/develop...HEAD`.

Les nettoyer signifierait toucher le code de session IMAP et d'enrichissement
depuis une task de confidentialité — un périmètre que le PO n'a pas demandé, et
un risque sans rapport avec l'objectif. Le Quality Gate est **OK** et les trois
notes sont **A** : rien n'oblige à le faire ici. À instruire séparément.

> **Récidive CA1861 à noter** : la règle est dans `conventions/csharp.md` avec
> `Occurrences: 2`, et 9 nouvelles occurrences apparaissent — mais **dans des
> tests écrits par d'autres tasks**, pas par task-184. Compteur non incrémenté :
> la consigne a été respectée ici.

### ⚠️ Flaky préexistant, prouvé et non imputable à cette task

Deux familles de tests d'instrumentation échouent **par intermittence**, et le
test qui échoue **change d'une exécution à l'autre** :
`EnrichmentOperationScopeTests`, `MailRepositoryEnrichPersistInstrumentationTests`,
`MailReadObjectCountTests`. Signature d'un état statique partagé
(`MailMetricsCaptureCollection`), pas d'une régression — une régression échoue
sur le même test.

**Preuve, plutôt qu'affirmation** : la suite a été rejouée deux fois sur
`origin/develop` dans un worktree isolé, **sans une ligne de cette task**.
Run 1 : `EnrichmentOperationScopeTests.The_total_includes_the_seeded_fetch…`
échoue. Run 2 : 2280/2280 vertes. Le flaky vit sur `develop`.

Aucun des fichiers concernés n'est dans le diff de task-184 (vérifié). Les deux
dernières exécutions complètes de la branche sont vertes : **4093 tests, 0
échec**.

## Lint log — client-angular (code-only)

Mode A (chaîné), 1 itération sur les 5 autorisées. Base `origin/next`,
scope lint `tag:scope:mss`.

| | Baseline | Final |
|---|---|---|
| Erreurs (`mss` + `mss-lib`) | **7** | **0** ✅ |
| Warnings | 39 | 39 (préexistants) |
| Itérations | — | 1 (auto-fix seul) |

### Ce qui a été corrigé

Les 7 erreurs étaient toutes `prettier/prettier` sur du code écrit par cette
task — parenthèses manquantes autour du paramètre unique des arrow functions
introduites par la résolution handle→INS (`patient =>` → `(patient) =>`) et un
retour à la ligne dans le `switchMap` de `getMailsByInsPaged`. **Auto-fixer
seul, aucun fix manuel** : rien à verser dans `conventions/angular.md` (les
corrections gratuites ne comptent pas — cf. le protocole de la boucle
d'auto-amélioration).

Les 39 warnings sont préexistants et hors périmètre : `jsdoc/require-example`,
`max-lines` (fichiers de 500+ lignes antérieurs), `complexity` sur `classify`,
`initializeFromPrefill`, `replacePlaceholders`.

### ⚠️ L'auto-fixer a débordé du scope — corrigé

`--projects=tag:scope:mss` **ne filtre pas** le `--fix` : Nx a exécuté la cible
sur les **11 projets affectés**, et l'auto-fixer a modifié 5 fichiers de
`apps/weda2/src/app/features/booking/daily/` (mappers, service, store, helper)
qui étaient **propres au pré-flight** et sont hors charte de la forge.

Les 5 fichiers ont été **restaurés** (`git checkout --`). L'arbre Angular ne
porte plus que les 5 fichiers MSS de cette task + les 2 `environment.ts` du WIP
humain constatés au pré-flight — exactement l'état attendu.

> **À corriger dans `agents/lint-angular.md`** : la commande documentée laisse
> croire que le scope protège les projets hors MSS. Ce n'est pas le cas avec le
> passthrough `-- --fix`. Il faut soit `nx run-many -t lint --projects=mss,mss-lib
> -- --fix`, soit vérifier l'arbre après coup. Non corrigé ici : modifier le
> playbook d'une étape depuis une task produit sort du périmètre de task-184.

### Validation

- Lint `mss` + `mss-lib` : **0 erreur**, 39 warnings acceptés (best-effort)
- Tests `nx affected -t test` (11 projets) : **2572 passed**, 14 skipped
- Tests `mss-lib` après restauration : **329 passed**
- Build `nx affected -t build` : `mss:build:production` échoue — **préexistant**,
  `environment.prod.ts` supprimé par `7de0cee3` sur la branche humaine (voir le
  Develop log). Le build `development` passe.

**Code-only respecté** : aucune opération git de mutation sur `client-angular`.
Les 5 fichiers MSS restent **non committés** sur `feature/nova-rewriting-mss` ;
l'humain gère commit / push / PR TFS.

## Lint mobile log — client-mobile

Mode A (chaîné), **0 itération consommée** sur les 5 autorisées.

| | Baseline | Final |
|---|---|---|
| Erreurs `ng lint` | **0** | **0** ✅ |
| Warnings | 0 | 0 |
| Itérations | — | **0** (rien à corriger) |

`ng lint` passe dès la baseline : « All files pass linting ». Le code écrit par
`/develop` sur `client-mobile` (bascule des cinq appels vers le handle,
résolution INS→handle en `switchMap`, réécriture des specs) respecte déjà les
règles ESLint du repo.

**Aucun commit, aucun push** : l'arbre est propre, il n'y a rien à corriger.
Pas d'entrée dans `conventions/angular.md` — la boucle d'auto-amélioration ne
se nourrit que des règles corrigées **à la main**, et il n'y en a eu aucune.

Build et tests de non-régression : déjà verts à l'étape `/develop`
(`npm run build` OK, **807 tests passed**) et inchangés depuis, cet arbre
n'ayant reçu aucune modification à cette étape.

## Visual verify log

**Skip propre — aucun écran mobile touché.**

Le diff `client-mobile` de cette task se limite à deux fichiers :

- `src/app/core/services/mss-api.service.ts`
- `src/app/core/services/mss-api.service.spec.ts`

Aucun `.html`, aucun `.scss`, aucune `.page.ts`, aucun composant. La task change
**ce qui voyage dans les URL** des appels API — les écrans reçoivent exactement
les mêmes données, affichées à l'identique. Il n'y a donc rien à capturer, et
aucun `## Stitch design log` n'a été produit par `/develop` (aucun écran créé ni
réécrit).

Ni serveur `ng serve` démarré, ni Playwright invoqué, ni capture produite : la
galerie « État visuel de l'application » (`Docs/epics/img/screens/client-mobile/`)
reste inchangée.

> Ce que l'humain doit tout de même vérifier au HAG, et qu'aucune capture ne
> couvrirait : la task ajoute **un aller-retour de résolution** avant chaque
> lecture patient sur mobile. Le rendu est identique ; c'est la **latence**
> perçue à l'ouverture d'une fiche patient qui est à juger sur l'appareil.
> Consigné au plan de test manuel (étape 11).

## PRs

| Repo | PR | Label |
|---|---|---|
| `dtos-mss` | https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/29 | `awaiting-human-merge` |
| `api-mail` | https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/218 | `awaiting-human-merge` |
| `client-blazor` | https://github.com/codengine-technologies/HealthPlatform.Client/pull/71 | `awaiting-human-merge` |
| `client-mobile` | https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/69 | `awaiting-human-merge` |

**`client-angular` — code-only, l'humain gère commit / push TFS et l'ouverture
de la PR.** 5 fichiers modifiés, **non committés**, sur
`feature/nova-rewriting-mss` :

- `front/libs/mss/src/core/services/mss-api.service.ts`
- `front/libs/mss/src/features/mail/mss-mail.component.ts`
- `front/libs/mss/src/features/patient/mss-patient.component.ts`
- `front/libs/mss/src/ui/patient-widget/patient-widget.component.ts`
- `front/libs/mss/src/ui/patient-widget/patient-widget.component.spec.ts`

> Les deux `environment.ts` également modifiés dans cet arbre sont le **WIP
> humain préexistant** constaté au pré-flight — pas cette task.

**Repos exclus** : `devops`, `psc-proxy-*` — managed manually by the human
(non listés par la task, aucun impact).

> ⚠️ **US-complete (règle 11)** : les cinq lots forment **une seule** US. Les
> quatre PRs se mergent ensemble, et l'Angular se pousse dans la même fenêtre.
> Merger `api-mail` seul déprécierait les routes sans basculer les appelants.

## Code Review Summary

**Verdict : APPROVED** — 68 fichiers revus, 0 blocage, 3 suggestions non
bloquantes.

### Correction

- ✅ **Le handle est toujours renseigné là où l'INS l'était.** Vérifié sur les
  deux projections dont dépendent les frontends : `AdvancedSearchAsync`
  (`Id = p.Id`) et `GetWithUnreadMailsAsync` (`PatientId = pat?.Id`, avec
  `Ins = hasIns ? pat!.Ins : null`). Un INS non nul **implique** un handle non
  nul — le garde `if (!patient.PatientId.HasValue) return` ne peut donc pas
  supprimer une navigation qui fonctionnait. Le seul cas nouvellement inerte est
  « ni INS ni handle », où l'ancien code naviguait avec une chaîne vide, c'est-
  à-dire vers une page incapable de résoudre quoi que ce soit.
- ✅ **`GetByInsAsync` n'assignait jamais `Id`** — défaut latent trouvé en
  écrivant le test d'intégration, sans conséquence avant cette task, fatal au
  nouveau schéma. Corrigé, couvert sur base réelle.
- ✅ **`Guid.Empty` lu comme « aucun patient »**, jamais comme « la première
  ligne » — testé côté repository et côté services clients.
- ✅ Un patient sans INS (issu d'un CDA non qualifié) lève `NotFoundException`
  au lieu de dégrader en recherche sur chaîne vide, qui aurait ramené les
  mauvaises lignes. Testé.

### Sécurité

- ✅ **L'isolation inter-praticiens n'est pas affaiblie.** Le handle est une clé
  primaire de la base **du praticien** (`BaseRepository`, une base par
  praticien) : un handle d'un autre tenant ne correspond simplement à rien.
  Aucune énumération possible — c'est un `Guid`.
- ✅ Aucun secret, aucune donnée de santé dans les nouveaux templates de log.
- ✅ Le masquage ne réduit **pas** la couverture du journal PGSSI-S : les
  évènements restent tous émis, la route reste identifiable, seule la valeur
  disparaît. Test dédié (`CompletionTraceStillNamesTheRouteItMasked`).
- ✅ `InsRequestDto` valide `[Required]` + `[StringLength(50, MinimumLength = 1)]`
  à la frontière.

### Architecture

- ✅ Substitution **à la frontière API** : application et infrastructure restent
  clés par INS. Le rayon d'action de la task est le plus étroit possible pour
  un correctif de conformité.
- ✅ `PatientHandleResolver` supprime le doublon entre les deux controllers
  (passe qualité `/simplify`).
- ✅ Les frontends ne dupliquent pas la logique de résolution dans leurs
  composants : elle est dans le service, les appelants sont inchangés.

### Suggestions (non bloquantes)

1. **⚠️ Coût d'un aller-retour supplémentaire, non caché.** `GetByIdAsync`
   n'est **pas** mis en cache, contrairement à `GetByInsAsync` (TTL 5 min, clé
   SHA-256). Chaque lecture adressée par handle fait donc une lecture base non
   mise en cache, **et** les frontends mobile/Angular ajoutent un aller-retour
   HTTP de résolution avant chaque lecture patient. Volontaire (un second cache
   devrait être invalidé en phase avec le premier, pour un gain non mesuré),
   mais **à surveiller au banc** : la fiche patient est déjà un poste connu du
   profil de charge. À rejouer sur l'escalier avant certification.
2. **Allocation sur le chemin chaud.** `SanitizePath` fait un `Split('/')` à
   chaque requête journalisée. ~6 petites chaînes par requête : négligeable
   devant le travail IMAP/base de chaque requête, et non bloquant. Une
   sortie anticipée est possible si un profil dit un jour le contraire.
3. **`PatientConsentSection` (Blazor) n'a aucun appelant.** Migré vers le handle
   pour rester cohérent et compiler, mais c'est du code mort — à supprimer dans
   une passe de ménage, hors de cette task.

### Couverture de test

- ✅ Les tests d'architecture ont été écrits **avant** les correctifs et étaient
  **rouges** sur le code d'avant (15 échecs constatés) — ce que la DOD exigeait.
- ✅ Chaque nouvelle route a un cas passant **et** un mode d'échec.
- ✅ Chaque route dépréciée garde son test de non-régression ; `CS0618` est levé
  explicitement, avec la raison, plutôt que les tests supprimés pour faire
  taire l'avertissement.
- ✅ Les deux garde-fous sont **prouvés** par un cas qui leur soumet les lignes
  exactes supprimées, et par un cas qui vérifie qu'ils ne signalent pas les
  remplacements — un garde qui signale tout est aussi inutile qu'un garde qui
  ne signale rien.
