# E016 — Changelogs (vue ingénierie)

> **Audience** : équipes techniques, backlog, dette.
> **Document frère (vue produit)** : [`E016-socle-multi-tenant.md`](./E016-socle-multi-tenant.md)
> **Dernière mise à jour** : 2026-09-14

Historique détaillé des changements de l'EPIC **E016 — Socle multi-tenant**.
Une entrée par task ayant atteint `done-*` ou `archived-*`. Append-only : une
entrée existante n'est jamais réécrite.

---

## Historique détaillé des changelogs

### v1.3 — task-301 : reprise de l'historique d'audit (`api-mail`)

**Statut** : `done` — PR [Api.Mail#235](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/235), label `awaiting-human-merge`
**Branche** : `feat/task-301-reprise-historique-audit` (2 repos ; `dtos-mss` auto-inclus, **0 commit**)
**Commits** : 4 — **22 fichiers**
**Tests** : **4 463 / 0 échec** (16 ignorés), dont **10 dédiés à la reprise**

#### Ce que l'US ferme

task-300 a déplacé les traces **nouvelles** vers la base commune. Celles déjà écrites dans
les mille bases praticien y restaient, et le chemin de lecture double — commune au-delà de
la bascule, praticien en deçà — devait vivre indéfiniment.

task-301 recopie l'existant, **le vérifie**, puis fait cesser la lecture double **tenant par
tenant**.

#### La contrainte qui gouverne tout

> Une reprise qui prend une nuit est un succès. Une reprise qui sature le serveur est un
> échec, même plus rapide.

Le 2026-09-11, une opération large sur le parc — le rejeu du tampon d'audit — a ouvert
**2 500 backends en trois minutes**, produit **27 575 refus `53300`** et figé la VM Docker
**45 minutes**, trois fois dans la même journée. La reprise fait la même chose en pire :
elle touche *toutes* les bases, délibérément.

| Borne | Valeur | Ce qui la vérifie |
|---|---|---|
| Concurrence | 4 bases simultanées | test observant la concurrence **réelle** sur 40 tenants |
| Lots | 1 000 traces, curseur sur `Id` | — |
| Saturation | pause au-delà de 600 connexions | fixture simulant la saturation |
| Reprenable | tenant marqué ⇒ ignoré **sans lecture** | rejeu ⇒ 0 insertion |

**Chacune se perd sans que rien n'échoue** : une reprise sans plafond marche parfaitement
sur trois tenants de test, et met le serveur à genoux sur mille.

#### L'ordre des opérations est le cœur de la correction

`compter → copier → **vérifier** → marquer`.

Marquer avant de vérifier ferait cesser la lecture héritée pour un tenant dont la copie est
peut-être incomplète : **le praticien perdrait une partie de son historique sans qu'aucune
erreur ne soit levée.** Un comptage divergent échoue bruyamment, le tenant reste non marqué,
et rien n'est supprimé.

Un tenant en échec **n'interrompt jamais les autres** : sur mille bases, une reprise qui
s'arrête au premier incident n'arrive jamais au bout.

#### Le verrou de suppression a été déplacé du runbook vers le code

Trouvé pendant `/review`. La DOD demande que la suppression de la table héritée soit
« appliquée **uniquement** aux tenants marqués repris et vérifiés ». Le mécanisme existait,
mais la garde vivait dans la **documentation**.

Sur une opération **irréversible** portant sur une source de traçabilité PGSSI-S, ce n'est
pas suffisant : `DropLegacyTableAsync` prend désormais le **tenant** — et non le seul nom de
base — pour relire `audit_backfilled_at` et **refuser** si la marque est absente.

> Une garde qui n'existe que dans un document finit un jour par être contournée depuis une
> console, sur le mauvais tenant, à deux heures du matin.

#### Déclencheur : configuration, jamais route HTTP

`api-mail` n'a pas d'ordonnanceur, et le task file exclut le cron. Une route serait le
déclencheur naturel — mais **il n'existe aucun modèle de rôles** dans ce service
(`questions/task-302.md`). Exposer derrière une route non habilitée une opération qui lit
l'intégralité du journal d'audit du parc ouvrirait un chemin d'exfiltration pour gagner une
commodité d'exploitation.

`Backfill:RunOnStartup` + redémarrage d'**un seul** réplica. Le jour où task-302 livre un
modèle de rôles, une route pourra s'y substituer sans rien changer au service.

#### Écart assumé — la configuration « morte » ne l'est pas encore

La DOD demandait de supprimer `Audit:DrainParallelism` et le plafond de drain. **Non fait**,
et c'est raisonné : task-300 a gardé l'ancien chemin comme **filet** pour les traces sans
`TenantId` (registre désactivé ou injoignable), filet accepté à son merge. Les retirer ne
supprimerait aucune architecture parallèle mais rendrait ce chemin **non bornable** — soit
exactement le défaut que task-298 contient.

La DOD pose elle-même la condition : « tant que le chemin hérité vit, le réglage doit rester
réglable ». **Il vit.** Le retrait est rattaché à la suppression des tables héritées : même
déclencheur — parc entièrement repris — et même nature, on ne retire un filet qu'une fois
certain de ne plus en avoir besoin.

#### Tests dédiés (10)

`AuditBackfillServiceTests` (7 unitaires : concurrence observée, déjà-repris ignoré sans
lecture, idempotence, pause de saturation, échec isolé, comptage divergent bruyant, hygiène
des journaux) — `AuditDualSourceReadTests` (+1 : contenu **identique** avant/après reprise) —
`AuditJournalIntegrationTests` (+1 bloquant : verrou de suppression dans les deux sens) —
plus le test de bascule par tenant.

#### Sonar — 2 itérations, **0 issue sur le code neuf**

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| `new_violations` | 167 – 170 | 168 | ≈ 0 |
| `new_code_smells` | 166 | 164 | −2 |
| Quality Gate | ERROR | ERROR | = |

3 issues attribuables corrigées (`S138` — trois lignes d'enregistrement poussaient
`AddApplication` de 97 à 100 lignes ; `CA1822` ; `xUnit2033`). `S4457` appliqué **sans que
Sonar le signale**, par respect de la convention dont le compteur venait d'être incrémenté.

> **Note de méthode** : l'API `measures` et l'API `issues` de SonarQube rendent des chiffres
> différents par décalage d'indexation (170 vs 167 en fin de task-300). **Le compte d'issues
> ouvertes fait foi.** Vérifié ici : une `CA1822` listée juste après le scan avait disparu
> d'une requête faite une minute plus tard.

**Documentation** : runbook `Api/Mail/docs/runbook-reprise-audit.md` — lancer, suivre,
reprendre après incident, et surtout **vérifier avant de supprimer**.

---


### v1.2 — task-300 : journal d'audit en base commune (`api-mail`)

**Statut** : `done` — PR [Api.Mail#234](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/234), label `awaiting-human-merge`
**Branche** : `feat/task-300-journal-audit-base-commune` (2 repos ; `dtos-mss` auto-inclus, **0 commit**, pas de PR)
**Commits** : 6 — **35 fichiers, +3 364 / −28 lignes**
**Tests** : **4 456 / 0 échec** (16 ignorés), dont **21 dédiés au journal mutualisé**

#### Le défaut corrigé, et pourquoi c'était un défaut de placement

Le journal était écrit dans une table **par praticien** — placement hérité du choix
« un médecin, une base », jamais décidé pour le journal. Un lot de 100 traces s'étalait
donc sur ~100 bases, ~100 pools Npgsql, ~100 logins Postgres : **52 088 des 53 456**
exceptions `53300` venaient de là, soit **97 %**. Le remède « évident » — drain
concurrent, degré 8 — avait **aggravé** (15 873 `08P01` contre 646).

Un journal d'audit est un flux append-only à fort débit, quasiment jamais relu : le
remède naturel est l'insertion groupée, et le sharding par tenant **détruit
mécaniquement la groupabilité**. On payait le coût maximal de l'isolation pour un
bénéfice d'isolation quasi nul.

#### Ce qui a été livré

| Brique | Chemin | Rôle |
|---|---|---|
| `audit_traces` | migration `Migrations/TenantDb/20260914090000` | Table partitionnée par mois, PK `(id, timestamp)`, index `(tenant_id, timestamp DESC)`, partition `DEFAULT` |
| `IAuditSink` / `IAuditReader` / `IAuditJournalPurge` | `Application/Services/Repository/TenantDb/` | Contrats — **hors du SDK**, même règle que le registre depuis la révision du 13/09 |
| `AuditTraceRecord` | `Domain/Entities/TenantDb/` | Ce qui franchit le contrat ; **aucun champ `Transport…`** (l'un portait un mot de passe Postgres) |
| `PostgresAuditSink` | `Infrastructure/Repositories/TenantDb/` | Un lot, une instruction, une connexion — `Application Name=mss-mail-audit`, pool **2** |
| `PostgresAuditReader` | idem | Lecture double source, confinée ici, supprimée par task-301 sans toucher une signature |
| `PostgresAuditJournalPurge` | idem | Purge par lots + suppression de partition, verrou légal prioritaire |
| `AuditPartitionMaintenance` | `Migrations/TenantDb/` | Avance de 3 mois maintenue au démarrage, verrou consultatif partagé |
| `tenants.audit_cutover_at` | migration | Borne de bascule **par tenant**, posée à l'horodatage de la première trace mutualisée |

#### Trois couches d'isolation, à la place d'une frontière de base

| Couche | Ce qu'elle tient |
|---|---|
| RLS PostgreSQL | `tenant_id = NULLIF(current_setting('mss.tenant_id', true), '')::uuid`, `FORCE ROW LEVEL SECURITY` |
| Deux rôles | `mss_audit_writer` (INSERT, **pas** SELECT) / `mss_audit_reader` (SELECT sous RLS, **pas** INSERT) |
| Filtre applicatif | optimisation de plan, **jamais** la sécurité |

#### Quatre défauts trouvés à l'implémentation — tous silencieux, tous prouvés à l'exécution

C'est la partie de cette entrée qui vaut d'être relue avant la prochaine US touchant
PostgreSQL. Aucun des quatre n'aurait échoué en test unitaire.

1. **`ON CONFLICT (id, timestamp) DO NOTHING` exige le privilège `SELECT`** — PostgreSQL
   doit inspecter l'index arbitre. Or le rôle d'écriture ne doit précisément pas pouvoir
   lire : il écrit pour **tous** les tenants, donc un `SELECT` ferait de lui un point
   d'exfiltration de tout le parc. La forme **sans cible d'inférence** ne demande aucun
   privilège de lecture et couvre la même contrainte.
2. **`current_setting(…, true)` rend une chaîne vide, pas `NULL`, sur une connexion
   recyclée.** Une fois un paramètre personnalisé posé dans une session — fût-ce par
   `SET LOCAL` —, il revient à chaîne vide, et le cast en `uuid` lève `22P02`. Sans
   `NULLIF`, la lecture suivante servie par le pool **échouerait** au lieu de rendre zéro
   ligne.
3. **`DELETE … WHERE ctid IN (…)` est FAUX sur une table partitionnée.** Le `ctid` est un
   emplacement physique, unique **par** partition et non entre partitions. L'idiome
   standard pour borner un `DELETE` supprimait donc des traces d'autres partitions,
   **encore dans leur durée de conservation**. Constaté : une trace du jour supprimée par
   une purge visant les traces de plus de 365 jours.
4. **`SET LOCAL` hors transaction explicite n'a aucun effet** au-delà de l'instruction :
   PostgreSQL crée une transaction implicite puis la valide. Au moment où la requête
   part, rôle **et** tenant ont été annulés. En production, l'écran d'audit du praticien
   aurait été **vide**. Masqué parce que l'utilisateur des conteneurs de test est
   `SUPERUSER` et **contourne la RLS**, y compris `FORCE ROW LEVEL SECURITY`.

> **Le quatrième a produit une leçon de méthode** : un test de sécurité qui tourne sous
> superutilisateur ne teste pas la sécurité. Le test qui l'a attrapé se connecte avec un
> rôle **ordinaire**, et la régression a été **ré-injectée** après correction pour
> vérifier qu'il mord — il échoue alors sur « Collection was empty », le symptôme exact
> de production.

#### Dépendance découverte : le tenant n'était jamais matérialisé

L'en-tête de l'US affirmait « Indépendante de task-303 : `TenantId` étant défini dans
task-299 ». **Faux.** task-299 a livré la table des tenants et `EnsureTenantAsync`, mais
**rien ne l'appelait** : `TenantRegistrySynchronizer` n'appelait qu'`EnsureAccountAsync`,
et la table était vide dans tous les environnements. Un journal clé sur `tenant_id`
n'avait aucun tenant à référencer.

Résolu ici au plus petit périmètre — boîte courante, nom de base déjà utilisé par
l'application. task-303 étend cette résolution à la sélection multi-boîtes ; elle ne la
refait pas.

#### Tests dédiés (21)

`AuditJournalIntegrationTests` (10, vrai PostgreSQL : RLS, rôles, partitions, purge,
idempotence, borne de bascule) — `AuditDualSourceReadTests` (3, dont **1 bloquant sous
utilisateur ordinaire**) — `AuditDrainMutualisationTests` (3, unitaires : un appel par
lot, repli sans tenant, invariant task-292) — `AuditJournalLogHygieneTests` (2, aucune
donnée de santé dans les journaux techniques) — `TenantRegistryContractTests` (+6 cas :
surface des trois contrats du journal).

#### Trois items de DOD comblés pendant `/review`

Cochés à blanc, ils auraient fait passer la PR pour complète : chaîne de connexion dédiée
`mss-mail-audit` (pool 2), test de lecture double source, test d'hygiène des journaux.

#### Sonar — 2 itérations, **0 issue sur le code neuf**

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| `new_violations` | 155 | 167 | +12 |
| Quality Gate | ERROR | ERROR | = |
| `new_coverage` | 89,1 % | 88,2 % | −0,9 |

Le `+12` vient de la **fenêtre de new-code**, pas du code neuf : toucher un fichier y fait
entrer ses issues **préexistantes**. Vérifié issue par issue — **0 sur les 14 fichiers
créés**, 0 imputable sur les fichiers modifiés. 3 issues corrigées (`S4457` ×2,
`xUnit2033`), dont une **récidive** : la consigne S4457 existait depuis task-299
(compteur 1 → 2).

#### Ce que cette US rend caduc

`Audit:DrainMaxConnections` et `Audit:DrainParallelism` n'ont plus d'objet **sur le chemin
d'audit**. **task-298 n'est pas annulée pour autant** : son `application_name` explicite
reste nécessaire quelle que soit l'architecture, et son plafond protège le chemin de
provisionnement.

#### Le risque assumé, à accepter au HAG

Le mode de panne devient **global** : la base commune indisponible contre-pressionne
**tous** les praticiens. Tampon Redis de 3 h, contre-pression en filet. Deux atténuations
livrées : les traces **sans tenant** gardent l'ancien chemin (un registre absent ne rend
pas le journal inopérant), et la partition `DEFAULT` absorbe tout horodatage hors plage.

**Documentation** : `ADR-2026-09-14-journal-audit-mutualise.md`, plus la réserve §4.y
ajoutée à `ADR-2026-07-27-pgbouncer-transaction-mode.md`.

---


### v1.1 — task-299 : registre des tenants (`api-mail`, + un `sdk` réduit à sa CI)

**Statut** : `done` — PR [Host.Sdk#3](https://github.com/codengine-technologies/HealthPlatform.Host.Sdk/pull/3) et [Api.Mail#233](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/233), label `awaiting-human-merge`
**Branche** : `feat/task-299-registre-tenants` (3 repos ; `dtos-mss` auto-inclus, **0 commit**, pas de PR)
**NuGet publié** : `HealthPlatform.Host.Sdk 14.0.0` (run CI 14) — **référencé par personne** après la révision ci-dessous ; `api-mail` est revenu à `13.0.0`
**Commits** : `sdk` 3 - `api-mail` 8 - **~2 700 lignes ajoutées**
**Tests** : `sdk` **16/16** - `api-mail` **4 424 / 0 échec** (16 ignorés), dont **57 dédiés au registre** (dont **12 d'intégration sur vrai PostgreSQL**)

> **Révision du 13/09/2026, après `/review` et avant tout merge.** Le contrat du registre devait
> vivre dans le SDK pour préparer le futur service du réseau privé. Décision humaine : le coût réel
> était un **cycle de publication à chaque évolution du modèle** — commit SDK, attente de CI,
> publication NuGet, bump de consommateur — pour un modèle qui bougera à chaque vague de l'EPIC.
> Les types sont rapatriés dans `api-mail`, isolés par espace de noms. `Sdk/TenantRegistry/` est
> supprimé ; PR #3 ne porte plus que le déclencheur CI (`branches: [ "**" ]`), utile au cycle de
> la forge.
>
> **Ordre de merge : plus d'objet.** `api-mail` ne compile plus contre un paquet dont le code
> source serait absent de `develop` du SDK. Les deux PRs sont indépendantes.

#### Le défaut de conformité corrigé

`AuditRetentionOptions.PurgeInterval` l'admettait noir sur blanc : « no way to enumerate the
practitioner databases, so a global nightly job would have nothing to iterate over ». La purge
de rétention étant **opportuniste**, déclenchée par l'activité du tenant lui-même, un praticien
qui cessait d'utiliser le produit **ne déclenchait plus jamais de purge** — ses traces, porteuses
de `PatientIns` et de `PatientName`, restaient au-delà de leur durée de conservation,
indéfiniment (RGPD art. 5.1.e).

#### Contrat du registre — isolé par espace de noms, plus par paquet

| Rôle | Types | Emplacement |
|---|---|---|
| Données franchissant le contrat | `RegistryAccount`, `RegistryMailbox`, `RegistryTenant`, `TenantState` | `Domain/Entities/TenantDb` |
| Contrat | `ITenantRegistryClient`, `EnsureTenantRequest` | `Application/Services/Repository/TenantDb` |
| Pannes typées | `TenantRegistryUnavailableException`, `TenantRegistryConflictException` | `Application/Exceptions` |

Symétriquement, les **22 entités du courrier** descendent de `mss.mail.Domain.Entities` à
`mss.mail.Domain.Entities.MailDb` — 310 fichiers, renommage mécanique. Les deux domaines sont
désormais des espaces **frères**, comme `Migrations/`, `Persistance/` et `Repositories/` depuis la
restructuration FluentMigrator.

Cinq contraintes de migrabilité, **toutes tenues par des tests** parce qu'elles sont toutes
silencieuses à la perte (`TenantRegistryContractTests`, 8 tests, portés depuis le dépôt SDK) :
`record` immuables (détection `init`-only via `IsExternalInit`), **aucune entité de persistance ne
franchit le contrat**, aucune séquence différée en retour, pannes typées avec le contrat,
`CancellationToken` + `correlationId` sur chaque opération. Deux tests sont **nés de la révision** :
`NoPersistenceType_CrossesTheContract` remplace la barrière d'assembly perdue (tant que le contrat
vivait dans un paquet, exposer un `RegistryTenantRow` était *impossible* ; c'est désormais une ligne
qui compile), et `TheContract_DoesNotDependOnTheSdk` épingle la décision — le SDK reste référencé
pour `IResilientCacheService`, donc une rechute passerait sans bruit. Les énumérations de types sont
assertées **non vides** — sans quoi les tests passeraient à vide.

Le **versionnement par espace de noms** (`.V1`) est abandonné : il protège un consommateur externe
déjà livré, et il n'y en a plus.

#### Implémentation `api-mail`

| Brique | Chemin | Rôle |
|---|---|---|
| `PostgresTenantRegistryClient` | `src/Infrastructure/Repositories/TenantDb/` | **Seule** implémentation ; cache-first + invalidation explicite, budget de temps (`CallTimeout` 3 s), dégradation par opération, traduction des pannes |
| `TenantRegistryDbContext` + les trois `…Row` | `src/Infrastructure/Persistance/TenantDb/` | Trois tables ; index unique **filtré** `WHERE rpps IS NOT NULL` ; unique partiel `WHERE is_default` (au plus une messagerie par défaut par compte, garanti par la base) |
| `CreateTenantRegistry` + `TenantRegistryMigrator` | `src/Infrastructure/Migrations/TenantDb/` | Migration FluentMigrator du registre et son coureur, **bornés par `TypeFilterOptions`** au seul espace `…Migrations.TenantDb` |
| `MigrationHelper` | `src/Infrastructure/Migrations/` | Création de base (`42P04` bénin) et **verrou consultatif partagé** par les deux bases — `SET LOCAL lock_timeout`, clé SHA-256 stable, budget client > budget serveur |
| `TenantRegistrySchemaInitializer` | `src/Infrastructure/Migrations/TenantDb/` | `IHostedService` ; un échec **ne bloque pas le démarrage** |
| `TenantRegistrySynchronizer` | `src/Application/Services/Implementation/` | Crochet du middleware ; bride horaire sur l'horodatage d'activité |
| `TenantRegistryOptions` | `src/Application/Configuration/` | Défauts dans le code, pas dans le JSON ; chaîne vide = registre désactivé ; chaîne câblée par l'`AppHost` (`MSS_TENANT_REGISTRY_DB`, défaut `mss_registry`) |

#### Trois écarts assumés par rapport au task file

1. **Crochet dans `UserContextEnricherMiddleware`, pas sur le chemin de provisionnement.**
   `BaseRepository.HandleEnvironmentDbSetupAsync` est conditionné à `Development`/`Staging`
   (ligne 540) : s'y accrocher n'aurait **jamais rien écrit en Production**.
2. **Nommage `TenantRegistry`.** `DirectoryController` (`api/v{version}/Directory`) sert l'Annuaire
   Santé de l'ANS ; le `GET /v1/directory/self` prévu serait tombé dessus. Le registre n'expose
   **aucune route** — garde-fou `RegistryNamingGuardTests`.
3. ~~**Schéma en SQL, pas en migration FluentMigrator.** L'exécuteur du produit applique son
   assembly à **chaque base praticien** : y ajouter les tables du registre les créerait dans les
   mille bases du parc.~~

   > ⚠️ **Écart refusé par l'humain, corrigé le 2026-09-13.** Le constat était juste, la conclusion
   > non : la frontière n'est pas *« pas de FluentMigrator »*, c'est **`TypeFilterOptions`**
   > (`Namespace` + `NestedNamespaces`), qui borne un coureur à un jeu de migrations. Les deux jeux
   > coexistent donc dans le même assembly, séparés par leur espace de noms —
   > `…Migrations.MailDb` (appliqué à chaque base praticien, paresseusement) et
   > `…Migrations.TenantDb` (appliqué à une seule base, au démarrage). Trois tests tiennent cette
   > frontière (`TenantRegistryMigrationScopeTests`), et le verrou consultatif de provisionnement
   > est **unifié** dans `MigrationHelper` : le verrou du registre était plus faible que celui du
   > courrier sur trois points (pas de `lock_timeout` serveur, pas de `CommandTimeout`, `hashtext()`
   > au lieu d'une clé SHA-256 stable), ce qui l'aurait rendu inopérant entre pods lors d'un
   > déploiement progressif. L'unification a d'ailleurs révélé un **défaut préexistant** côté
   > courrier : budget client (300 s) **égal** au budget serveur (`5min`), en violation de
   > l'invariant que le code documentait lui-même — corrigé à 330 s.

#### Tests dédiés (57)

`PostgresTenantRegistryClientTests` (14) - `TenantRegistryContractTests` (8, portés du dépôt SDK à
la révision) - `TenantRegistryArchitectureTests` (5, **par réflexion** et non par balayage de
sources — `RepoRoot()` rend `null` sous `--artifacts-path`) - `TenantRegistrySynchronizerTests` (6)
- `TenantRegistryMigrationScopeTests` (3) - `ProvisioningLockTests` (5) -
`TenantRegistryOptionsBindingTests` (3) - `RegistryNamingGuardTests` (1) -
**`TenantRegistryIntegrationTests` (12, contre un vrai PostgreSQL)**.

> **Pourquoi 12 tests d'intégration après coup.** Les 45 premiers tournaient **tous** sur le
> fournisseur EF en mémoire — qui n'a ni index, ni contraintes, et évalue côté client ce qu'il ne
> sait pas traduire. Trois affirmations de la DOD y étaient donc **invérifiables** : « au plus une
> messagerie par défaut par compte, *garanti par la base* », l'index unique **filtré**
> `WHERE rpps IS NOT NULL`, et la traduction SQL du curseur `t.Id.CompareTo(cursor) > 0`. Les
> tests passaient au vert sans rien prouver. Les 12 tests d'intégration ferment ces trois trous,
> plus la frontière `TypeFilterOptions` (prouvée par le **schéma réellement produit**, pas par
> réflexion) et le verrou consultatif entre pods. **Effet immédiat** : le prérequis hérité inscrit
> dans la DOD de task-301 (curseur non prouvé traduisible) est **levé**.

Trois d'entre eux existent parce que le défaut qu'ils couvrent est **silencieux** :
- **adresse organisationnelle partagée** : 1 messagerie, 2 tenants, 2 bases (si le `TenantId`
  était celui de la messagerie, deux praticiens verraient les traces l'un de l'autre) ;
- **piège `MapInboundClaims`** : `FindFirstValue("sub")` rend toujours `null` ; le test échoue si
  la lecture repart sur `sub` seul ;
- **bride d'écriture** : 100 requêtes donnent 1 seule écriture d'activité.

#### Sonar — 4 itérations, delta **0**

| Métrique | Baseline | Pic | Final | Delta |
|---|---|---|---|---|
| `new_violations` | 155 | 165 | **155** | **0** |
| `new_code_smells` | 151 | 161 | **151** | **0** |
| `new_bugs` / `new_vulnerabilities` | 2 / 2 | 2 / 2 | **2 / 2** | 0 |
| `new_coverage` | 89,1 % | 89,1 % | **89,1 %** | 0 |

Corrigés : **S1854** (affectation morte — introduite par la passe `/simplify` elle-même),
**S4457** (validation d'arguments dans un corps `async`), **CA1068** x5, **CA1859** x2,
**S2699** (test sans assertion — dont la première correction était elle-même fausse : le double
levait avant d'incrémenter), **S103** x3, **S138**.

**Accepté** : S138 sur `AddApplication` — la méthode faisait déjà ~93 lignes avant les 2 lignes de
cette US (seuil 80). Non attribuable.
**QG ERROR** : `new_violations` 155 (seuil 0) et `new_security_hotspots_reviewed` 83,3 % — valeurs
**identiques avant l'US**. La new-code period du projet est une baseline large qui inclut des
tasks déjà mergées.

`conventions/csharp.md` : 3 entrées créées (S1854, S4457, CA1068), 1 compteur incrémenté
(CA1859, 3e récidive).

#### Revue de code — APPROVED, 2 suggestions reportées en DOD

Toutes deux sur des méthodes **sans appelant en production** :

1. **Curseur `t.Id.CompareTo(cursor) > 0` non prouvé traduisible en SQL** — les tests tournent sur
   le fournisseur EF **en mémoire**, qui évalue **côté client** : ils ne prouvent rien sur
   Postgres. Reporté au **DOD de task-301**.
2. **`EnsureTenantAsync` ne relit pas après `SaveIdempotentAsync`** — sur une course perdue, rend
   le tenant *tenté*, donc un `TenantId` inexistant, alors que c'est l'identifiant sur lequel le
   journal d'audit sera clé. `EnsureAccountAsync` fait la relecture correctement. Reporté au
   **DOD de task-303**.

#### Changement d'intégration continue (`sdk`)

Déclencheur élargi de `master`/`develop` à **toutes les branches**, comme `dtos-mss`. Sans cela,
aucun paquet n'aurait pu être publié depuis un `feat/*` et l'attente `gh run watch` du playbook
`/develop` aurait tourné à vide.

#### Dette laissée

- Les deux suggestions de revue (reportées en DOD de 301 et 303).
- S138 sur `AddApplication` (préexistante).
- La clé `RedisConnectionString` reste dans les `appsettings*.json` de `client-blazor` (task-305).

---


### v1.0 — task-305 : `HealthPlatform.Host.Sdk` retiré de `client-blazor`

**Statut** : `done` — PR [HealthPlatform.Client#73](https://github.com/codengine-technologies/HealthPlatform.Client/pull/73), label `awaiting-human-merge`
**Branche** : `chore/task-305-retirer-sdk-de-blazor` (base `origin/develop` @ `d4a0730`)
**Repos** : `client-blazor` (3 commits) ; `dtos-mss` (auto-inclus, **0 commit**, pas de PR)
**Cycle mesuré** : 14 min 02 s au total — `/start` 40 s, `/develop` 10 min 30 s (4 builds / 4 suites), `/review` 2 min 51 s (2 builds / 1 suite)

#### Objet

Le SDK redevient un paquet **strictement backend**, avec `api-mail` pour seul
consommateur. Préalable à task-299 : tant que `client-blazor` le référençait, tout
contrat de plateforme publié dedans (`ITenantRegistryClient`, `IAuditSink`) partait
dans la charge utile WASM du navigateur et imposait un bump de version à un
consommateur qui n'en consommait rien.

#### Constat — la référence était morte

| Fait | Preuve |
|---|---|
| `AddSdk` n'est **jamais** appelé dans `Client/Blazor/Src` | seul `AddShellService` l'est (`Src/Shell/Program.cs:63`) |
| Donc `IResilientCacheService` n'était ni enregistré ni injecté | unique occurrence dans le dépôt : le commentaire de `Src/Shell/Extensions/ServiceCollectionExtensions.cs:23` affirmant le contraire — **faux**, reliquat de task-218 |
| `using HealthPlatform.Host.Sdk.Services;` mort | `Src/Shell/Extensions/ServiceCollectionExtensions.cs:2`, aucun type du SDK utilisé dans le fichier |
| `IMarkdownService` / `MarkdownService` dupliqués | `Src/Component/Shared/Services/IMarkdownService.cs` + `Src/Modules/Mss/Plugin/Services/MarkdownService.cs` ; les 7 `@inject IMarkdownService` résolvent le contrat Blazor |
| `ICacheService` dupliqué | `Src/Component/Shared/Services/ICacheService.cs` + `InMemoryCacheService` — contrat différent de celui du SDK |
| Assembly expédié au navigateur | `HealthPlatform.Components.Shared.csproj` porte `<SupportedPlatform Include="browser" />` |

#### Deux dépendances transitives — le fichier de task n'en annonçait qu'une

Le §Piège de `todo-task-305.md` qualifiait `Markdig` de « seul effet de bord réel ».
**C'était faux**, et le build l'a montré au retrait. Le task file a été corrigé.

1. **`Markdig`** — réellement utilisé par `Src/Modules/Mss/Plugin/Services/MarkdownService.cs:1`
   sans `PackageReference` propre. Déclaré explicitement **dans un commit séparé,
   avant le retrait** (`Directory.Packages.props` + `HealthPlatform.Module.Mss.Plugin.csproj`,
   version `0.40.0` — celle qu'apportait le SDK), pour que le build ne soit jamais rouge.
2. **`Microsoft.Extensions.Caching.StackExchangeRedis`** — alimentait l'unique
   `AddStackExchangeRedisCache` de `Src/Shell/Extensions/ServiceCollectionExtensions.cs`.
   Enregistrement **inerte**, vérifié : aucun `IDistributedCache` injecté dans
   `Client/Blazor/Src` (grep), pas de `AddSession` / `UseSession`, pas de
   `AddOutputCache`, pas de backplane SignalR, et `AddDataProtection()`
   (`Src/Shell/Program.cs:57`) est **en mémoire** (pas de `PersistKeysToStackExchangeRedis`).
   Le seul consommateur possible aurait été le `CacheService` du SDK, enregistré par
   `AddSdk` — jamais appelé. **Retiré** avec son paramètre `IConfiguration`, devenu
   sans objet (appelant unique mis à jour : `Program.cs:63`).

La clé `RedisConnectionString` est **laissée** dans `appsettings.json` /
`appsettings.Test.json` : la retirer toucherait la surface de déploiement pour un
gain nul.

#### Fichiers touchés

| Fichier | Changement |
|---|---|
| `Directory.Packages.props` | `-PackageVersion HealthPlatform.Host.Sdk 12.0.0` ; `+PackageVersion Markdig 0.40.0` |
| `Src/Component/Shared/HealthPlatform.Components.Shared.csproj` | `-PackageReference HealthPlatform.Host.Sdk` |
| `Src/Modules/Mss/Plugin/HealthPlatform.Module.Mss.Plugin.csproj` | `+PackageReference Markdig` |
| `Src/Shell/Extensions/ServiceCollectionExtensions.cs` | `using` morts retirés, `AddStackExchangeRedisCache` retiré, signature sans `IConfiguration`, commentaire faux de task-218 corrigé |
| `Src/Shell/Program.cs` | appelant unique de `AddShellService` mis à jour |
| `tests/…/SdkReferenceGuardTests.cs` | **nouveau** — garde-fou anti-récidive (2 tests) |
| `tests/…/RepoScan.cs` | **nouveau** — helper partagé (passe qualité) |
| `tests/…/ClientSensitiveDataScanTests.cs` | refactor : délègue `RepoRoot` / `git ls-files` à `RepoScan` |

#### Garde-fou anti-récidive

`SdkReferenceGuardTests` — 2 tests :
- `ProductionProjects_DoNotReferenceTheBackendSdk` : aucun `Include="HealthPlatform.Host.Sdk"`
  dans `Src/**/*.csproj` ni `Directory.Packages.props` ;
- `ProductionSources_DoNotImportTheBackendSdk` : aucun `HealthPlatform.Host.Sdk.` dans
  `Src/**/*.{cs,razor}`, **hors lignes de commentaire** — documenter le retrait est le
  sujet de la task.

Deux précautions méthodologiques :
- **Vérifié par réinjection de la régression** : la ligne `PackageVersion` remise dans
  `Directory.Packages.props` fait virer le test au rouge, en pointant
  `Directory.Packages.props:8`. Puis restauré.
- **Protégé du faux vert** par `Assert.NotEmpty(files)` : si `git ls-files` échouait ou
  si `RepoRoot()` se résolvait mal, les deux assertions passeraient **à vide**. Un test
  qui ne peut pas échouer est pire qu'un test absent.
- `tests/` est exclu du scan : ce fichier nomme le paquet, un guard qui échoue sur
  lui-même est du bruit.

#### Passe qualité (`/simplify`, sous-étape de `/develop`)

**Reuse** : les deux gardes de balayage du dépôt (task-184 données sensibles, task-305
référence SDK) avaient chacune leur copie de « remonter jusqu'au `.sln`, puis
`git ls-files` ». Extraites dans `RepoScan` (`RepoRoot()`, `TrackedFiles(root, filter)`).
Deux copies d'un helper de parcours dérivent, et la dérive est invisible puisque chaque
garde continue de passer sur ses propres termes. Refactor fidèle : filtre et sémantique
identiques (`Src/Modules/Mss/` + `.cs|.razor`), `IEnumerable` → `List` (consommé une fois
en `foreach`). **184 tests verts avant comme après.**

#### Validation

- `dotnet build HealthPlatform.Client.sln` : **0 erreur, 0 avertissement**
- `dotnet test HealthPlatform.Client.sln` : **184 réussis / 0 échec / 2 ignorés**
  (skips préexistants de `BiologyAckPanelComponentTests`)
- `dotnet build HealthPlatform.Dtos.Mss.csproj` : 0 erreur (branche sans commit)
- `/sonar`, `/lint-angular`, `/lint-mobile`, `/verify-visual` : **skipped** — repos non touchés

#### Code review — APPROVED, 0 bloquant, 2 suggestions

1. **`ClientSensitiveDataScanTests` peut passer à vide.** Ce garde-fou de sécurité
   (task-184 : INS dans les URLs, journalisation nominative) n'assert pas que son
   énumération de fichiers est non vide : si `git ls-files` échouait, il passerait
   **sans rien garder**. Le nouveau `SdkReferenceGuardTests` s'en protège ; l'ancien
   mérite le même `Assert.NotEmpty`, d'autant qu'il partage désormais `RepoScan`.
   **Faiblesse préexistante**, non introduite par cette task.
2. **Deux résidus morts possibles** : `Microsoft.AspNetCore.DataProtection.StackExchangeRedis`
   reste déclaré dans `Directory.Packages.props` alors qu'`AddDataProtection()`
   (`Program.cs:57`) est en mémoire ; et trois `using` de `ServiceCollectionExtensions.cs`
   (`Ardalis.Result`, `System.Net`, `System.Net.Http.Headers`) ne correspondent à aucun
   type du fichier après nettoyage. `/review` est en lecture seule sur le code —
   signalés, pas corrigés.

#### Dette laissée

- Les deux suggestions ci-dessus, candidates à une task d'hygiène.
- `RedisConnectionString` reste dans les `appsettings*.json` (choix assumé).

---

## Annexe A — Cartographie des briques applicatives

### Contrats de plateforme (`TenantRegistry` livré par task-299 ; `Audit` à venir, task-300)

| Brique | Emplacement prévu | Rôle |
|---|---|---|
| `ITenantRegistryClient` + DTOs | `Sdk/TenantRegistry/V1/` | **Livré** (task-299) — comptes, messageries, tenants, dormance. Paquet `14.0.0` |
| `PostgresTenantRegistryClient` | `Api/Mail/src/Infrastructure/TenantRegistry/` | **Livré** (task-299) — seule implémentation ; test d'architecture (par réflexion) garantit que le `DbContext` n'est référencé nulle part ailleurs |
| `IAuditSink` / `IAuditReader` | `Sdk/` — `HealthPlatform.Host.Sdk.Audit.V1` | Contrat du journal mutualisé (écriture par lots / lecture scopée tenant) |

> **Nommage — piège connu.** `DirectoryController` (`api/v{version}/Directory`,
> `AnnuaireSanteService`) sert l'**Annuaire Santé de l'ANS** (`practitioners/search`,
> `specialties`, `professions`). Le registre de cet EPIC n'a rien à voir : ses
> identifiants portent **`TenantRegistry`**, jamais `Directory`, et il n'expose aucune
> route sous `/directory`.

### Briques touchées par task-305

| Brique | Emplacement | État |
|---|---|---|
| `RepoScan` | `Client/Blazor/tests/HealthPlatform.Module.Mss.Plugin.Tests/RepoScan.cs` | Helper partagé des gardes de balayage |
| `SdkReferenceGuardTests` | même répertoire | Garde-fou anti-récidive du retrait du SDK |
| `ServiceCollectionExtensions.AddShellService` | `Client/Blazor/Src/Shell/Extensions/` | Signature sans `IConfiguration` depuis task-305 |

---

## Annexe B — Inventaire fonctionnel (2026-09-13)

| Grandeur | Valeur |
|---|---|
| Tasks déclarant `**Epic**: E016` | 7 (299, 300, 301, 303, 304, 305, 306) |
| Tasks `done` | 2 (task-299, task-305) |
| Tasks `todo` | 5 |
| Questions ouvertes bloquantes | 1 (`questions/task-302.md` — identité et habilitation des administrateurs) |
| PRs ouvertes | 2 (Host.Sdk#3, Api.Mail#233 — `awaiting-human-merge`) ; 1 mergée (Client#73) |
| Paquets NuGet publiés par l'EPIC | 1 (`HealthPlatform.Host.Sdk 14.0.0`) |
| Consommateurs du SDK après task-305 | **1** (`api-mail`) — contre 2 avant |

---

## Annexe C — Tasks ayant contribué à cet EPIC

| Task | Apport | Repos | Statut |
|---|---|---|---|
| task-299 | Registre des tenants : comptes (`sub` Keycloak + RPPS), messageries, **tenants** (compte × messagerie, porteurs de la base isolée et de `TenantId`), horodatages de connexion et dormance. Contrat `ITenantRegistryClient` et implémentation Postgres dans `api-mail` — **le contrat a quitté le SDK à la révision du 13/09** | `api-mail` (`sdk` : CI seulement) | ✅ **done** (PR Sdk#3, Api.Mail#233) |
| task-300 | Journal d'audit en base commune : table partitionnée par mois, `TenantId` = id du **tenant**, RLS + rôles lecture/écriture séparés, purge planifiée s'appuyant sur `AuditRetentionPolicy.FamilyOf`, lecture double source transitoire | `api-mail` | ✅ **mergée** (`ff6332f7`) |
| task-301 | Reprise de l'historique d'audit à débit borné (≤ 4 bases simultanées), vérification par comptage par tenant, puis retrait de la lecture double source par tenant. **Retrait de la configuration morte reporté** — écart assumé, le chemin hérité vit encore comme filet (cf. v1.3) | `api-mail` | ✅ **done** (PR Api.Mail#235, en attente de merge) |
| task-303 | Vague 1 multi-BAL : la boîte devient une sélection par requête validée contre le registre **et** l'identité PSC ; disparition des claims `mssEmail`/`mssSub`/`mssRpps` ; bascule = fin de session + nouvelle session (garde `SESSION_MAILBOX_MISMATCH`) ; `AuditActionType` + 5 membres | `sdk`, `api-mail` | 🔜 todo |
| task-304 | Vague 2 multi-BAL : onboarding par le registre, écran de sélection, avatar → sélecteur, gestion des comptes, purge totale de l'état à la bascule — parité Blazor / Angular / mobile. Inclut la remise à niveau de l'outillage de capture visuelle | `client-blazor`, `client-angular`, `client-mobile` | 🔜 todo |
| task-305 | **Le SDK redevient backend-only** : retrait de la référence morte dans `client-blazor`, déclaration explicite de `Markdig`, retrait de l'enregistrement Redis inerte, garde-fou anti-récidive | `client-blazor` | ✅ done |
| task-306 | Banc de charge multi-BAL : dimension « boîtes par compte » (défaut 1, iso E015), parcours avec bascule réelle (`/sync/logout` + rotation de session), restitution du coût de bascule et de la résolution de registre | `api-mail` | 🔜 todo |

### Question ouverte

| Fichier | Objet | Blocage |
|---|---|---|
| `questions/task-302.md` | Accès des administrateurs et de la sécurité au journal mutualisé | **Aucun modèle de rôles n'existe dans `api-mail`** : la politique globale est `RequireAuthenticatedUser()` seule (`Program.cs:133`) et le gate de rôle « Doctor » a été désactivé le 2026-05-11 (`BiologyAcksController.cs:15`). Ouvrir un accès transverse dans cet état le rendrait accessible à tout utilisateur authentifié, sur un historique porteur de données de santé de tout le parc |

---

*Document vivant, régénéré par la forge à chaque fin de cycle. La vue produit vit dans
[`E016-socle-multi-tenant.md`](./E016-socle-multi-tenant.md).*
