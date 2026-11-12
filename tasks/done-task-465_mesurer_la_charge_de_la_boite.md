# todo-task-465.md — Mesurer la charge de la boîte

**Repos**: api-mail
**Dependencies**: aucune
**Epic**: E024
**Priorité**: EPIC E024, demandée par l'humain le 2026-11-11. **À passer juste après task-453.** Règle d'or n° 5 :
mesurer avant d'améliorer. Les tasks 454 à 463 se jugent sur l'avant/après, pas sur une impression.

> **Origine.** Analyse du 2026-11-11, manque I1 (Sinsky et Shanafelt : « mesurer, réduire, déléguer » ; le temps passé
> hors des heures de travail prédit l'épuisement, selon Arndt 2017 et Akbar 2021). **Aucune source publique ne dit
> combien de documents un généraliste reçoit par jour** : nous le mesurerons nous-mêmes. Usage décidé par le PO le
> 2026-11-11 : **mesure anonyme réservée à l'équipe produit**, rien n'est montré au médecin.
> Seule `api-mail` est touchée : aucun écran client.

## Ce qui est établi

- Le journal d'audit (`audit_traces`, base commune, partitionné, index `ix_audit_traces_mailbox_timestamp`) porte pour
  chaque acte : la boîte, la personne et son rôle, le type d'action et l'horodatage. Il comprend la lecture, l'envoi,
  la réponse, l'acquittement, le rattachement, le déplacement et la suppression.
- La catégorie des documents est en base de boîte (`MailMedicalDocument.Category`).
- `AuditTraceFilterDto` filtre déjà par personne, type et dates. Aucune agrégation n'existe.
- Aucun modèle d'exposition anonyme n'existe encore : task-452, qui devait le poser pour la recherche, a été supprimée
  par l'humain le 2026-11-11. Cette task pose donc le premier tableau de bord anonyme de l'équipe produit, dans le
  Grafana du projet : compteurs et durées seulement.

## Objective

L'équipe produit suit, chaque jour, **la charge réelle** de la messagerie, sans connaître ni les boîtes, ni les
personnes, ni les patients.

Indicateurs, agrégés par jour sur l'ensemble des boîtes :
- **Volume reçu** par boîte et par jour (médiane, p90), réparti par catégorie de document : biologie, comptes rendus,
  sans document, patient.
- **Délai de prise de connaissance** : de la réception à la première lecture (p50, p95), et pour la biologie anormale
  de la réception à l'acquittement.
- **Part du travail délégué** : part des gestes faits par un délégataire ou un membre plutôt que par le titulaire.
- **Travail hors heures** : part des gestes faits avant 8 h, après 20 h, ou le week-end (Europe/Paris).
- **Temps de session** passé dans la messagerie par personne et par jour (médiane, p90), estimé depuis les gestes.

Règles :
- **Anonyme** :
  - aucun identifiant de boîte, de personne ou de patient dans les mesures exposées ;
  - un découpage n'est publié que s'il porte sur **au moins 5 boîtes** ;
  - le rôle n'est publié qu'en trois catégories : titulaire, délégataire, membre.
- **Calcul en tâche de fond**, une fois par jour, sous verrou distribué. Le calcul ne gêne jamais le médecin.
- **Indicateurs prévus pour la suite** :
  - « délai jusqu'au traitement » et « part traitée par le secrétariat » arriveront avec task-454 ;
  - « répartition par nature » arrivera avec task-456.

  Ces deux tasks déclarent chacune l'ajout de leur indicateur. Ici, ils sont seulement réservés sur le tableau de bord
  (« disponible après task-454 / task-456 »).
- **Mesure de référence** relevée **avant** la mise en service de task-454, et consignée.

### Complément — décision humaine du 2026-11-12 (PR #366 encore ouverte)

L'humain demande d'ajouter au tableau de bord, dans cette même task, des indicateurs d'**usage** :
- **Personnes connectées** : nombre de personnes distinctes qui ont **ouvert une boîte** dans la journée (ouverture de
  session de boîte), même sans geste ensuite.
- **Plages horaires** (heure de Paris), deux graphiques : **personnes actives par heure** (au moins un geste dans la
  tranche) et **part des gestes par heure**.
- **Délégataires** : nombre de délégataires **inscrits** au registre (rattachements actifs en fin de journée) et
  nombre de délégataires **actifs** (au moins un geste) ; même découpage actif pour titulaires et membres.
- **Boîtes** : nombre total de boîtes **inscrites** (au moins un rattachement actif en fin de journée) et nombre de
  boîtes **actives** (ouverture ou geste dans la journée).

Mêmes règles d'anonymat : une valeur n'est publiée que si elle porte sur au moins 5 boîtes, une tranche horaire
comprise.

## Definition of Done

- [ ] Agrégation quotidienne depuis `audit_traces` et les bases de boîte, sous verrou distribué ; aucune donnée
      nominative dans le résultat.
- [ ] Seuil d'anonymat (au moins 5 boîtes) appliqué à chaque découpage, testé.
- [ ] Tests unitaires du calcul de chaque indicateur (≥ 1 test par indicateur), dont le fuseau Europe/Paris et le
      passage à l'heure d'hiver pour le « hors heures ».
- [ ] **Test d'intégration de bout en bout (règle 1b)** sur la route d'exposition des indicateurs :
      - un jeu de traces sur 6 boîtes rend les volumes et délais attendus ;
      - un découpage sur 4 boîtes n'est pas publié ;
      - aucun identifiant de boîte, de personne ou de patient dans la réponse ;
      - cas d'échec : une plage de dates invalide → 400 en `ProblemDetails`.
      Vu rouge par mutation.
- [ ] Tableau de bord ajouté au Grafana du projet ; capture dans le `## Develop log`.
- [ ] Mesure de référence relevée sur l'environnement de recette (corpus fictif) et consignée dans le task file.
- [ ] Aucune donnée de santé ni donnée personnelle dans les mesures et les logs (revue du schéma exposé consignée).
- [ ] Build et tests verts : `HealthPlatform.Api.Mail.sln`.
- [ ] (complément du 2026-11-12) Indicateurs personnes connectées, personnes actives et part des gestes par heure,
      délégataires inscrits et actifs, boîtes inscrites et actives : ≥ 1 test unitaire chacun, seuil de 5 boîtes par
      tranche horaire testé, et lus dans la réponse réelle par le test d'intégration de la route, vus rouges.
- [ ] (complément du 2026-11-12) Panneaux correspondants ajoutés au tableau de bord.

## Manual Test Plan

1. Lancer le backend (`cd Api/Mail/src/AppHost && dotnet run`) et le tableau de bord Grafana du projet.
2. Rejouer une journée de gestes sur six boîtes de recette (seed e2e ou banc), puis déclencher le calcul quotidien.
3. Ouvrir le tableau de bord « Charge de la messagerie » : volumes, délais, part déléguée, hors heures.
4. Vérifier qu'aucune boîte, personne ou patient n'apparaît nulle part, et qu'un filtre sur moins de 5 boîtes
   n'affiche rien.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — pilotage produit
- **Vague Ségur** : hors Ségur
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — aucune donnée patient dans les mesures
- **Authentification PS** : non applicable au calcul (tâche de fond) ; la consultation du tableau de bord est réservée
  à l'équipe produit
- **Habilitations** : équipe produit seulement ; aucun accès depuis les clients médecin
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : calcul quotidien en acte système ; lecture du journal par le calcul tracée en technique
  (`TechnicalActions`)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : le calcul tourne dans l'environnement HDS ; seuls des agrégats anonymes en sortent
- **AIPD / impact RGPD** : à mettre à jour — réutilisation du journal d'audit à des fins statistiques anonymes
  (finalité, seuil d'anonymat de 5 boîtes)

## Branches
- `api-mail` (pushed) : feat/task-465-mesurer-la-charge-de-la-boite — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-465-mesurer-la-charge-de-la-boite
- `dtos-mss` (pushed, créée par `/develop` — un contrat a bougé) : feat/task-465-mesurer-la-charge-de-la-boite — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-465-mesurer-la-charge-de-la-boite

## Develop log

- **Repos touchés** : `api-mail`, `dtos-mss` (branche paresseuse : nouvelle valeur d'audit).
- **DTOs publiés** : `HealthPlatform.Dtos.Mss` 597.0.0 → **601.0.0** (`AuditActionType.MailboxLoadComputed = 72`,
  run CI 43248101783) ; api-mail bumpé (Directory.Packages.props + lock files).
- **Interop publié** : aucun changement.
- **Miroirs de `AuditActionType` restant à faire** (dépôts non listés dans `**Repos**`, donc non touchés) :
  - `client-angular` : `libs/mss/src/core/models/audit.model.ts` (+ spec) — `MailboxLoadComputed = 72`, libellé
    « Calcul de la charge (système) » ;
  - `client-blazor` : `AuditActionLabels.cs` + bump `HealthPlatform.Dtos.Mss` 601.0.0.
  Sans eux, une trace de calcul affichée dans un écran d'audit tomberait sur la valeur inconnue. En pratique elle
  n'y apparaît pas : la trace est écrite avec `tenant_id = Guid.Empty` et sans boîte, donc invisible de tout
  écran praticien (RLS par boîte) — même choix que la trace de purge.

### Ce qui a été construit

| Pièce | Où | Rôle |
|---|---|---|
| Rôle `mss_audit_statistics` + politique `audit_traces_statistics_read` | migration `20261112090000_AddMailboxLoadStatistics` | seule porte vers le journal de **toutes** les boîtes (`SELECT` seulement, + `id, created_at` de `mss_mailboxes`) |
| Tables `mailbox_load_days` / `mailbox_load_values` | même migration, base commune | agrégats anonymes ; `CHECK (mailbox_count >= 5)` : le seuil tenu par la base |
| `PostgresMailboxLoadStore` | Infrastructure | lit les faits du jour sous `SET LOCAL ROLE`, enregistre/relit les journées |
| `MailboxLoadCalculator` (+ `MailboxLoadCalendar`, `MailboxLoadGestures`) | Application | calcul pur des indicateurs, seuil par découpage, fuseau Europe/Paris |
| `MailboxLoadService` | Application | calcule une journée, l'enregistre, trace l'acte système `MailboxLoadComputed` ; valide la plage |
| `MailboxLoadHostedService` | Application | toutes les heures : jauges, puis journées achevées manquantes (7 j) sous verrou Redis `lock:mailbox-load:{jour}` |
| `MailboxLoadMetrics` (`mss_mailbox_load`, `mss_mailbox_load_day`) | Telemetry, déclaré à OpenTelemetry | dernière journée calculée, pour Grafana |
| `GET /api/v1/product-metrics/mailbox-load?from=&to=` | `ProductMetricsController` | historique, clé `X-Product-Metrics-Key` ; sans clé configurée → 404, clé absente/fausse → 401 |
| Tableau de bord « MSSante - Charge de la messagerie » | `src/AppHost/grafana/dashboards/mssante-mailbox-load.json` | 13 panneaux + 3 indicateurs réservés (task-454 ×2, task-456) |

**Déclencheur réel** (consigne `declencheur-reellement-atteint`) : `MailboxLoadHostedService` est inscrit par
`AddApplication` (`AddHostedService`), donc démarré par l'hôte de l'API dans chaque réplica, sans geste du médecin.
Cadence : 1 h ; une journée est calculée 2 h après minuit (Paris), une seule fois (verrou Redis + table). Sans Redis,
rien n'est calculé (direction sûre, comme la purge). Désactivable : `ProductMetrics:MailboxLoad:Enabled=false`.

### Écart assumé avec la DoD : « depuis audit_traces **et les bases de boîte** »

Le calcul ne lit **que** la base commune (journal + date de création de la boîte), jamais les bases de boîte :
- la **catégorie** vient du LOINC déjà porté par la trace `MedicalDocumentProcess` (`11502-2` = biologie, la même
  règle que `HprimMedicalDocuments.BiologyLoinc`), et « patient » de l'expéditeur `@patient.mssante.fr`, testé en
  SQL sans que l'adresse quitte PostgreSQL ;
- ouvrir chaque base de boîte depuis une tâche de fond, c'est un pool Npgsql par praticien
  (`project_pg_pool_per_practitioner_ceiling`) : le contraire de « le calcul ne gêne jamais le médecin ».
**Limite** : la réception est l'instant où la plateforme a vu le message (trace `MailReceive`), pas l'en-tête `Date`.
Une boîte jamais ouverte reçoit « en retard ». La première synchronisation d'une boîte (24 h après sa création) et
tout dossier autre que `INBOX` sont écartés. task-466 (date de début du suivi) remplacera ce rodage.
**À arbitrer par `/review` ou l'humain** si la lecture des bases de boîte reste exigée.

### Définitions retenues (à relire par l'équipe produit)

- **Geste** : liste blanche explicite (`MailboxLoadGestures.Counted`, 52 actions) ; un test exige que chaque membre
  de `AuditActionType` soit classé geste ou exclu. Actes système (`is_system_act`) exclus.
- **Rôles** : `Holder` → titulaire, `Delegate` → délégataire, `Member` → membre ; `ToRequalify` et rôle absent
  exclus des parts (comptés dans le volume de gestes, le hors-heures et les sessions).
- **Hors heures** : avant 8 h, à partir de 20 h, samedi et dimanche, heure de Paris.
- **Session** : gestes séparés de 15 min au plus ; + 1 min pour le dernier geste de chaque session.
- **Délais** : mesurés le jour de la première lecture / du premier acquittement ; réception cherchée 30 jours en arrière.
- **Seuil** : chaque valeur porte sur ≥ 5 boîtes contributrices ; le temps de session exige en plus ≥ 5 personnes.
- **Quantiles** : interpolation linéaire (comme `percentile_cont`).

### Revue du schéma exposé (aucune donnée de santé ni personnelle)

| Sortie | Champs | Verdict |
|---|---|---|
| Route (JSON) | `day`, `computedAt`, `cells[].indicator/breakdown/statistic/value/mailboxCount` | noms d'indicateurs fixes, nombres ; aucun identifiant |
| Table `mailbox_load_values` | mêmes colonnes + `day` | idem ; `CHECK mailbox_count >= 5` |
| Jauges Prometheus | labels `indicator`, `breakdown`, `statistic` (ensemble fini) | idem |
| Trace d'audit du calcul | `day`, `publishedCells` dans `server_request` ; `tenant_id` vide, aucun acteur | acte système |
| Logs | « Journée {Day} calculée : {Cells} valeur(s) » | aucun identifiant |
Les identifiants de boîte et clés de personne ne vivent qu'en mémoire pendant le calcul. Le rôle statistique lit des
colonnes sensibles du journal (filtrage SQL), mais ne remonte que boîte, personne, rôle, instants et catégorie.

### Tests

- Unitaires (`tests/mss.mail.application.tests/Services/ProductMetrics/`, 54 cas) : calendrier (bornes, journées de
  23 h et 25 h, heures ouvrées, **passage à l'heure d'hiver**), chaque indicateur, seuil par découpage, classement
  des actions, service (fenêtres, trace système, trace perdue, validation de plage), tâche de fond (jours dus,
  verrou par jour, sans Redis).
- **Intégration (règle 1b)** — `MailboxLoadEndpointIntegrationTests` (8 cas) : vraie route, vrai calcul déclenché
  par `MailboxLoadHostedService.RunPassAsync`, vraie migration, journal partitionné, base de registre propre à la
  classe ; seul Redis (verrou) est simulé. 6 boîtes → volumes 4,5 / 5,5, délais 35 / 57,5 et 210 / 345 min, parts
  0,2941, sessions 2 min ; découpage « patient » sur 4 boîtes absent ; corps sans identifiant de boîte, de
  personne, d'adresse, d'INS ni de nom ; plage invalide (inversée, > 366 j, borne absente, date illisible) → 400
  `problem+json` ; sans clé → 401.
- **Preuves par mutation** (restaurées depuis copie, 2026-11-12) :
  1. politique `USING (true)` → `USING (false)` : 3 tests rouges (`Assert.Single … did not contain`) — prouve
     que la RLS joue sous le rôle statistique malgré le superutilisateur des tests ;
  2. seuil 5 → 4 (code + `CHECK`) : `…FourMailboxes_IsNotPublished` rouge (`DoesNotContain … matched`) ; code
     seul : écriture refusée par la base (`23514 mailbox_load_values_mailbox_count_check`) ;
  3. rodage retiré du SQL des réceptions : `Expected 4,5 / Actual 5` ;
  4. validation `fin < début` neutralisée : `Expected BadRequest / Actual OK` ;
  5. clé de personne mise en découpage des sessions : `DoesNotContain … Found "holder-"`.

### Commits, validation, passe qualité

- **Commits** :
  - dtos-mss : `3151fc7` feat(dto): AuditActionType.MailboxLoadComputed — calcul quotidien de la charge
  - api-mail : `ee432545` chore(deps): bump HealthPlatform.Dtos.Mss to 601.0.0 ; `804edf74`
    feat(product-metrics): mesurer la charge de la messagerie ; `6cb1141e` refactor(product-metrics): simplify pass
- **Migration (règle 7c)** : FluentMigrator écrite à la main (pas de génération, pas de snapshot) ; relue :
  rôle + droits au meilleur effort, politique conditionnée à l'existence du rôle, deux `CREATE TABLE IF NOT
  EXISTS`, `Down` symétrique (le rôle est conservé). Aucune opération fantôme.
- **Contrôles mécaniques §Q 2b** joués **avant** le commit : 4 × S125 (« ; » en commentaire) et 2 × S4457
  (`ThrowIfNull` dans `async` public) trouvés et corrigés — compteurs incrémentés dans `conventions/csharp.md`.
- **Passe qualité (/simplify)**, api-mail : 2 nettoyages — le quantile supérieur passé avec sa statistique
  (au lieu d'être déduit du nom), le jour AAAAMMJJ calculé sans aller-retour par une chaîne. Écarté : un helper
  d'ouverture de connexion pour le dépôt (gain nul, libération du contexte moins lisible). dtos-mss : sautée
  (porteur de contrat).
- **Rouge préexistant, hors task** : `TenantRegistryIntegrationTests.AttachMailboxAsync_UnderConcurrency_PersistsExactlyOneTenant`
  — rouge dans la suite complète et 3/3 isolé sur la branche, **rouge aussi sur `origin/develop` (ba27e7d3)**
  rejoué dans un worktree ; vert quand il tourne avec les autres tests du registre. Instable, antérieur à
  task-465 (qui ne touche pas `AttachMailboxAsync`).

- **Build / tests locaux** (après la passe qualité, vérification finale) : `HealthPlatform.Api.Mail.sln` 0 erreur ;
  domain 221, infrastructure 749, api 1 380, application 4 277, integration 1 290 (+16 ignorés) — **0 échec**.
  dtos-mss : build 0 erreur, NuGet 601.0.0 publié.
- **DoD self-check** (commandable) : 5/8 vérifiés — agrégation sous verrou sans donnée nominative ✓, seuil testé ✓,
  unitaires par indicateur dont Europe/Paris et heure d'hiver ✓, intégration de bout en bout vue rouge ✓,
  build/tests verts ✓ ; revue du schéma consignée ✓ (ci-dessus) ; **à faire au test humain (HAG)** : capture
  Grafana, mesure de référence sur la recette.
- **Étape suivante** : `/sonar task-465`.

### Reprise du 2026-11-12 — indicateurs d'usage (décision humaine, voir le complément de l'objectif)

| Indicateur (`indicator` / `breakdown` / `statistic`) | Source | Seuil |
|---|---|---|
| `connected_persons` / `all` / `count` | traces `MailboxSessionOpened` (première requête d'une session client sur une boîte), personnes distinctes | boîtes ouvertes ≥ 5 |
| `active_mailboxes` / `all` / `count` | boîtes ouvertes ou avec au moins un geste | ≥ 5 |
| `registered_mailboxes` / `all` / `count` | `mss_accounts` : boîtes avec un rattachement actif **en fin de journée** (`attached_at < fin` et non détaché avant la fin) | ≥ 5 |
| `registered_delegates` / `all` / `count` | idem, comptes distincts au rôle `Delegate` | boîtes déléguées ≥ 5 |
| `active_persons` / `all`, `holder`, `delegate`, `member` / `count` | personnes distinctes avec au moins un geste, par rôle | boîtes du découpage ≥ 5 |
| `active_persons_by_hour` / `00`…`23` / `count` | personnes distinctes avec un geste dans l'heure (Paris) | boîtes de la tranche ≥ 5 |
| `gesture_share_by_hour` / `00`…`23` / `share` | part des gestes du jour dans l'heure (Paris) | idem |

- **Registre lu à la fin du jour mesuré**, pas au moment du calcul : une journée rattrapée compte le registre de ce
  soir-là. Une journée de changement d'heure garde 24 tranches (la tranche répétée de l'heure d'hiver est fusionnée).
- **Migration** `20261112110000_GrantMailboxLoadRegistryRead` (séparée, pour ne pas changer une migration déjà
  jouable) : `GRANT SELECT (mailbox_id, account_id, role, attached_at, detached_at) ON mss_accounts` au rôle
  statistique — ni adresse, ni base, ni identité PSC, ni nom.
- **Tableau de bord** : rangée « Usage » (personnes connectées, boîtes actives et inscrites, délégataires inscrits et
  actifs, personnes actives) et deux histogrammes horaires (personnes actives, part des gestes), triés par heure ;
  29 panneaux ; `selftest.sh` vert.
- **Tests** : 8 unitaires de plus (69 au total dans `Services/ProductMetrics/`), dont le seuil par tranche horaire
  et le passage à l'heure d'hiver ; intégration `MailboxLoad_SixMailboxes_ExposesUsage` (registre réel avec un
  délégataire détaché la veille et un rattaché après la fin du jour, sessions réelles) — 10 tests verts.
- **Preuves par mutation** (restaurées depuis copie, 2026-11-12) :
  6. droit de lecture du registre retiré → `42501: permission denied for table mss_accounts` ;
  7. registre lu sans la borne de fin de journée → `Expected 5 / Actual 7` (détaché et tardif comptés) ;
  8. heure calculée en UTC → tranche « 10 » introuvable.
- **Contrôle mécanique §Q 2b** : 3 × S125 de plus, corrigés avant le commit (compteur porté à 27).

### Reste hors de portée de `/develop`

- **Capture Grafana** : le Grafana local répond mais son mot de passe administrateur n'est pas `admin`, et l'API
  n'était pas lancée ; à faire au test manuel (HAG). Le tableau de bord passe `tests/loadtest-k6/selftest.sh`.
- **Mesure de référence** sur la recette : à relever après déploiement (la tâche calcule seule les 7 derniers
  jours ; lire `GET …/mailbox-load` avec la clé) et à consigner ici **avant** la mise en service de task-454.
- **Clé de production** `ProductMetrics__MailboxLoad__ApiKey` : secret à poser par l'exploitant (DevOps, hors forge).
- **AIPD** : mise à jour à faire (finalité statistique anonyme, seuil 5 boîtes).

## Sonar log

- **Serveur** : SonarQube 25.6.0 (`sonar.token`), projet `healthplatform-api-mail`, conteneurs redémarrés par l'agent.
- **Phase 1 (new code) — périmètre de la task** : la période « new code » du projet court depuis le 2026-04-17
  (`PREVIOUS_VERSION`) et englobe des tasks déjà fusionnées ; le Quality Gate était déjà `ERROR` avant la task
  (98 violations, 16 hotspots non revus). Les findings ont donc été filtrés sur les fichiers du diff
  `origin/develop...HEAD` (mémoire `project_sonar_new_code_baseline_includes_prior_tasks`).
  - Analyse 1 : **4 findings** dans le diff, **0 hotspot**.
    - `CA1068` `PostgresMailboxLoadStore.ReadAsync<T>` — jeton avant le délégué → jeton en dernier ;
    - `ASP0025` hôte de test d'intégration → `AddAuthorizationBuilder().SetFallbackPolicy(…)` ;
    - `S138` ×2, **préexistants** (créés en septembre) mais **allongés par la task** : `ConfigureOpenTelemetry`
      (81 → 83) et `AddApplication` (110 → 111). Méthodes ramenées à 77 lignes chacune : `AddMssMeters`, `AddImap`,
      `AddMailSending`, `AddSemanticSearch` (déplacements purs, à la même place dans l'ordre des enregistrements).
  - Couverture new code des fichiers de la task sous 95 % : `MailboxLoadHostedService` 61,2 %, `MailboxLoadMetrics`
    83,3 %, `ProductMetricsController` 89,5 % → 7 tests ajoutés (boucle d'exécution, service désactivé, passe en échec,
    jauges avec et sans journée, série vide, route sans clé configurée → 404).
  - Analyse 2 : **0 finding dans le diff** ; tous les fichiers de la task ≥ 95 % (`MailboxLoadHostedService` 95,5 %).
  - Un test d'architecture rouge à l'analyse 2 (`MetricCaptureSerialisationScanTests`) : la classe de capture des jauges
    était dans une collection sérialisée à part → déplacée dans `MailMetricsCaptureCollection`, suites api et
    application revenues au vert (1 380 / 4 284).
- **Phase 2 (legacy)** : non jouée — best-effort, et les 96 violations restantes de la période appartiennent à des
  tasks fusionnées ; hors périmètre de cette US.
- **Itérations** : 2 analyses complètes.
- **Commits** : `57559c6c` (S138), `86a0bd02` (CA1068, ASP0025), `27dba85a` + `88e5398c` (tests de couverture).
- **Build / tests** : ✓ (Release, sous couverture : domain 221, application 4 284, infrastructure 749, api 1 380,
  integration 1 291 + 16 ignorés).
- **Conventions** : CA1068 → 4 (contrôle mécanique ajouté à `agents/develop.md` §Q 2b), S138 → 3, ASP0025 (nouvelle),
  capture-de-metriques-serialisee (nouvelle).

- **Reprise du 2026-11-12 (indicateurs d'usage)** : 3ᵉ analyse — **0 finding et 0 hotspot dans le diff**, tous les
  fichiers de la task ≥ 95 % de couverture new code ; KPIs projet inchangés (new coverage 97,9 %, new violations 96).
  Pendant l'analyse, `ThreadCountsScopedLoadTests.AddingForeignMailsDoesNotReadMoreRows` rouge une fois en suite
  complète Release, puis vert 3/3 en isolation : instabilité connue des tests qui partagent la base du fixture,
  hors diff.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | ERROR | ERROR | → (préexistant : hotspots non revus et violations de tasks fusionnées) |
| Findings new code dans le diff de la task | — | 0 | — |
| New coverage | 97,8 % | 97,9 % | +0,1 pt |
| New violations (projet) | 98 | 96 | −2 |
| Bugs | 2 | 2 | 0 |
| Vulnerabilities | 2 | 2 | 0 |
| Security hotspots | 16 | 16 | 0 |
| Code smells | 94 | 92 | −2 |
| Coverage (projet) | 97,8 % | 97,8 % | 0 |
| Duplication | 0,3 % | 0,3 % | 0 |
| Reliability / Security / Maintainability | D / D / A | D / D / A | → |

## Lint log

- `/lint-angular` : skip — `client-angular` absent des `**Repos**`, arbre de travail propre.

## Lint mobile log

- `/lint-mobile` : skip — `client-mobile` absent des `**Repos**`, dépôt sur `develop`, aucun changement.

## E2E log

> ⚠️ **Quarantaine de plus de 14 jours** : E2E-COMPOSE-002 (Angular), posée le 2026-10-09 pour task-350 — 34 jours.
> Un test en quarantaine ne protège rien : sa correction est due.
> ⚠️ **Flaky récurrents** (≥ 3 occurrences, task de stabilisation à ouvrir) : E2E-SEARCH-001 (Angular, 18ᵉ) et
> E2E-LIVE-001 (Angular, 6ᵉ).

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail et dtos-mss touchés | ✅ verte (jouée) | 61 verts, 0 flaky, 0 rouge, 0 quarantaine | 11 min 17 s |
| angular | api-mail et dtos-mss touchés | ✅ verte (jouée) | 80 verts, 2 flaky, 0 rouge, 1 quarantaine (passée) | 13 min 51 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task (`88e5398c`), inchangé par la task
- Rejoué le 2026-11-12 après la reprise (indicateurs d'usage) : mêmes résultats que le premier passage.
- Checkouts : api-mail `5a97a3aa` (task), client-mobile `f775f173` (`develop`, déjà aligné sur `origin/develop`),
  client-angular `ce7741dd` (branche de l'humain `feature/nova-mss-weda-integration`)
- Quarantaines : E2E-COMPOSE-002 (Angular, task-350) — passée
- Divergences ouvertes : 8, toutes côté mobile (E2E-SEARCH-004 à 010, 012 ; résorption task-450 / task-451)
- Parcours touchés sans spec e2e modifié : aucun (aucun écran modifié, task backend)
- Démontage : complet (ports 5052, 8100, 4200, 3993, 3465, 3143 libres ; aucun conteneur `e2e-dovecot-*` /
  `e2e-greenmail-*` résiduel)
- Porte : code 0

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**Flaky (vert au second essai, non bloquant)** (2) :

- [angular] « recherche — composer ses critères puis lancer la recherche » (E2E-SEARCH-001)
- [angular] « temps réel — un compte rendu arrive, notifié et affiché sans rechargement » (E2E-LIVE-001)

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
| E2E-PATIENT-004 | 1 | headless | La vue « Mails du patient » reste ouverte et ses pages viennent du serveur | ✅ | — |
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
| E2E-MAIL-006 | 1 | headless | Glisser sur la Corbeille un message d'un fil supprime ce message, et lui seul | ✅ | — |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-DRAFT-004 | 1 | headless | Une rédaction sans texte dans le corps ne laisse ni brouillon ni question | ✅ | ✅ |
| E2E-BIO-001 | 2 | headless | Acquitter un compte rendu de biologie, à son nom | ✅ | ✅ |
| E2E-BIO-002 | 1 | headless | La puce « Bio à acquitter » montre tous les résultats en attente, sur toutes les pages | ✅ | ✅ |
| E2E-BIO-003 | 1 | headless | Lire un résultat HPRIM puis l'acquitter | ✅ | ✅ |
| E2E-BIO-004 | 1 | headless | Un compte rendu acquitté puis déplacé depuis un autre client garde son acquittement | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SETTINGS-004 | 1 | headless | Paramètres indisponibles : rien n'est écrasé | ✅ | — |
| E2E-SEARCH-001 | 2 | headless | Composer ses critères puis lancer la recherche | ⚠️ flaky | ✅ (v1) · divergence (task-450) |
| E2E-SEARCH-002 | 1 | headless | Un mot rare et accentué trouve le message qui le contient | ✅ | ✅ |
| E2E-SEARCH-003 | 1 | headless | Un numéro de dossier trouve son message, et un seul | ✅ | ✅ |
| E2E-SEARCH-004 | 1 | headless | Un nom de patient tapé sans accent ni majuscule trouve ses messages, puis les messages partiels | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-005 | 1 | headless | Un mot absent de la boîte affiche « Aucun résultat » | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-006 | 1 | headless | Plus de résultats qu'une page — « Voir plus » affiche la suite, jusqu'au dernier | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-007 | 1 | headless | Une recherche en échec affiche un message, et l'ancienne liste n'est plus affichée | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-009 | 1 | headless | Fermer la recherche rend le dossier à la même position ; retirer une étiquette relance sans elle | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-010 | 1 | headless | Reconnaître un résultat et ouvrir le dossier du patient | ✅ | ⛔ non joué · divergence (task-451) |
| E2E-SEARCH-012 | 1 | headless | Traiter tous les résultats d'une recherche | ✅ | ⛔ non joué · divergence (task-451) |
| E2E-SEARCH-008 | 1 | headless | Restreindre la recherche à un patient et à ses biologies anormales | ✅ | ⛔ non joué · divergence (task-451) |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 2 | headless | Créer un contact à deux adresses, le modifier sans les perdre, puis le supprimer | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-CONTACT-004 | 1 | headless | Consulter un contact depuis le carnet et lui écrire | ✅ | ✅ |
| E2E-CONTACT-005 | 1 | headless | Une fiche modifiée ne se perd pas sans confirmation, une adresse mal formée est refusée | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ⚠️ flaky | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 2 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ | ✅ |
| E2E-MAILBOX-003 | 2 | headless | Rattacher ses boîtes depuis « Mes boîtes » en un geste — titulaire et membre | ✅ | ✅ |
| E2E-MAILBOX-006 | 1 | headless | Après le rattachement, l'identité d'expéditeur et la signature sont déjà là | ✅ | ✅ |
| E2E-MAILBOX-004 | 1 | headless | Ajouter une BAL déléguée par saisie — et refus de sa propre adresse | ✅ | ✅ |
| E2E-MAILBOX-005 | 1 | headless | Le délégataire refusé par l'opérateur perd l'accès, en ligne puis hors ligne ; le titulaire garde le sien | ✅ | ✅ |
| E2E-AUDIT-001 | 1 | headless | Le titulaire lit au journal le message supprimé par son délégataire, au nom du délégataire | ✅ | — |
| E2E-AUDIT-002 | 1 | headless | Le journal d'audit montre chaque action sur un mail | ✅ | — |
| E2E-SHARED-001 | 1 | headless | Une boîte partagée, une base — le patient rattaché par le titulaire est vu du délégataire, la signature reste à chacun | ✅ | ✅ |
| E2E-SHARED-002 | 1 | headless | Le délégataire écrit pour le compte du titulaire — le destinataire voit qui a écrit, sa réponse revient à la boîte | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |
| E2E-SESSION-004 | 1 | headless | Sur un appareil partagé, la personne suivante n'arrive jamais dans la boîte de la précédente | ✅ | ✅ |
| E2E-AI-002 | 1 | headless | Un délégataire interroge l'assistant dans la boîte qu'il a ouverte | ✅ | ✅ |
| E2E-MAILBOX-007 | 1 | headless | Après un changement de boîte, l'onglet Patients ne montre plus rien de la précédente | ✅ | ✅ |
| E2E-ERROR-001 | 1 | headless | Une erreur affiche un code et une référence à transmettre au support | ✅ | ✅ |

**Divergences temporaires ouvertes** (9) :

- E2E-SEARCH-001 [mobile] — le mobile adopte le formulaire à un seul niveau avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-004 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-005 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-006 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-007 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-009 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-010 [mobile] — la lecture enrichie arrive sur le mobile avec la refonte mobile — résorbée par task-451
- E2E-SEARCH-012 [mobile] — la sélection de tous les résultats arrive sur le mobile avec la refonte mobile — résorbée par task-451
- E2E-SEARCH-008 [mobile] — les critères médicaux arrivent sur le mobile avec la refonte mobile — résorbée par task-451

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/366 — label `awaiting-human-merge`
- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/64 — label `awaiting-human-merge`
- `client-angular`, `client-blazor` : non listés — miroirs de `AuditActionType` à reporter (voir Develop log)

## Code Review Summary

**Verdict** : APPROVED — 0 bloquant, 5 suggestions, 1 écart de DoD à arbitrer (revue initiale + reprise du 2026-11-12)

| Zone | Verdict |
|---|---|
| `MailboxLoadCalculator`, `MailboxLoadCalendar`, `MailboxLoadGestures` | ✅ calcul pur, seuil appliqué par découpage, fuseau Europe/Paris, toute action d'audit classée (test d'exhaustivité) |
| `PostgresMailboxLoadStore` + migration `20261112090000` | ✅ SQL paramétré, lecture sous `SET LOCAL ROLE mss_audit_statistics` dans une transaction, `CHECK mailbox_count >= 5` en base ; rôle en `SELECT` seul |
| `MailboxLoadService` | ✅ trace système `MailboxLoadComputed` sans personne ni boîte (règle 14) ; validation de plage → 400 RFC 7807 |
| `MailboxLoadHostedService` | ✅ verrou Redis par jour ; sans Redis, aucun calcul ; passe en échec journalisée par code d'erreur, service maintenu |
| `ProductMetricsController` | ✅ `[AllowAnonymous]` + clé `X-Product-Metrics-Key` comparée en temps constant ; sans clé configurée 404, clé absente ou fausse 401 (un médecin authentifié reçoit 401) |
| `MailboxLoadMetrics` + tableau de bord | ✅ seules les valeurs publiées sortent ; `noValue` partout, pas de `or vector(0)` (harnais vert) |
| Reprise : indicateurs d'usage (`AddUsage`, `AddHourlyActivity`, sessions et registre dans le dépôt, migration `20261112110000`) | ✅ registre lu **à la fin du jour mesuré** (journée rattrapée exacte) ; droits du rôle statistique limités à 5 colonnes de `mss_accounts` (ni adresse, ni base, ni identité PSC) ; seuil de 5 boîtes par tranche horaire |
| Extractions S138 (`AddMssMeters`, `AddImap`, `AddMailSending`, `AddSemanticSearch`) | ✅ déplacements purs, à la même place dans l'ordre des enregistrements |

**Règle 1b — comportement → test d'intégration → preuve rouge** (`MailboxLoadEndpointIntegrationTests` : vraie route, vrai PostgreSQL, vraie migration ; seul Redis est simulé) :

| Comportement | Test | Preuve rouge (mutation) |
|---|---|---|
| volumes, catégories, délais, parts, sessions sur 6 boîtes | `…SixMailboxes_ExposesTheExpectedVolumesDelaysAndShares` | politique RLS `USING (false)` ; rodage retiré du SQL (`4,5` attendu, `5` obtenu) |
| découpage sur 4 boîtes non publié | `…ABreakdownOverFourMailboxes_IsNotPublished` | seuil 5 → 4 (code + `CHECK`) ; code seul : écriture refusée par la base (`23514`) |
| aucun identifiant de boîte, de personne, d'adresse, d'INS ni de nom | `…TheResponse_NamesNoMailboxNoPersonNoPatient` | clé de personne mise en découpage → `Found "holder-"` |
| plage invalide → 400 `problem+json` | `…AnInvalidRange_Is400ProblemDetails` (4 cas) | validation `fin < début` neutralisée → `200` |
| sans la clé → 401 | `…WithoutTheProductTeamKey_Is401` | contrôle de clé neutralisé → `200` |
| personnes connectées, boîtes actives et inscrites, délégataires inscrits, personnes actives par rôle, personnes et part des gestes par heure | `…SixMailboxes_ExposesUsage` | droit de lecture du registre retiré → `42501` ; borne de fin de journée retirée → `5` attendu, `7` obtenu ; heure en UTC → tranche « 10 » introuvable |
| sans clé configurée → 404 | `…WithoutAConfiguredKey_DoesNotExist` | garde de configuration neutralisée → `500` |

**⚠️ Écart de DoD à arbitrer au merge.** La DoD dit « agrégation depuis `audit_traces` **et les bases de boîte** ». Le calcul ne lit **que** la base commune (journal et date de création de la boîte) :
- la catégorie se tire du LOINC déjà tracé par `MedicalDocumentProcess` (même règle que `HprimMedicalDocuments.BiologyLoinc`) ;
- ouvrir chaque base de boîte depuis une tâche de fond, c'est un pool par praticien, et un accès sans verdict de l'opérateur (règle 14) ;
- limite : la réception est l'instant où la plateforme voit le message, et la première synchronisation d'une boîte (24 h) est écartée en attendant task-466.

**Suggestions (non bloquantes)**
- Les délais de lecture et d'acquittement retrouvent la réception dans tout dossier, alors que le volume ne compte que `INBOX` : à aligner si l'équipe produit le juge utile.
- Une journée calculée n'est jamais recalculée, même après une panne partielle du journal : un effacement manuel par jour pourrait servir.
- `TryClaimAsync` horodate le verrou avec `DateTimeOffset.UtcNow` plutôt qu'avec le `TimeProvider` injecté (valeur informative seulement).
- Les boîtes et délégataires inscrits comptent aussi les rattachements en `AuthFailing` (encore rattachés) : à exclure si l'équipe produit veut « inscrits et en état de marche ».
- La route rend directement les records applicatifs : sans consommateur client, pas de contrat `dtos-mss` ; à déplacer si un client la lit un jour.

## Timings

*(généré par `tools/timing/report.sh --task task-465 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 26 s | — | — | — | — |
| /develop | ok | 15 min 15 s | 8 (2 min 39 s) | 19 (26 min 25 s) | — | dtos-mss 1B/0T, api-mail 7B/19T, reprise : indicateurs d'usage |
| /sonar | ok | 13 min 52 s | 6 (3 min 04 s) | 19 (28 min 57 s) | 6 (8 min 09 s) | 1 itération(s), api-mail 6B/19T |
| /lint-angular | skipped | 1.5 s | — | — | — | reprise : client non touché (absent des Repos) |
| /lint-mobile | skipped | 2.0 s | — | — | — | reprise : client non touché (absent des Repos) |
| /e2e | ok | 26 min 01 s | — | — | — | e2e ×10 (1 h 40 min) |
| /review | ok | 8 min 33 s | 4 (1 min 34 s) | 2 (14 min 48 s) | — | dtos-mss 1B/0T, api-mail 3B/2T |
| /tech-writer | ok | 1.8 s | — | — | — | — |
| **Total cycle** | | **1 h 04 min** | **18 (7 min 18 s)** | **40 (1 h 10 min)** | **6 (8 min 09 s)** | |

Autres commandes mesurées : nuget-wait ×1 (12 s), restore ×1 (8.7 s)
