# todo-task-300.md — Journal d'audit en base commune : sortir l'écriture du journal du sharding par praticien

**Repos**: api-mail
**Dependencies**: **task-299** (registre — définit le **tenant** et son `TenantId`, fournit la
dormance qui pilote la purge, et pose le motif « contrat isolé par espace de noms / implémentation
Postgres derrière lui » que cette US reproduit). **Indépendante de task-303** : `TenantId` étant défini dans task-299, les deux
lignes (audit et multi-BAL) peuvent avancer en parallèle. Recouvre partiellement **task-298** : voir « Ce que cette US rend caduc ».
**Epic**: E016
**Priorité**: **1** — c'est le levier de capacité le plus lourd identifié par E015. La mesure
désigne le drain du journal comme **97 %** des refus Postgres à 1000 médecins ; tout le reste
de la chaîne task-292 → 294 → 298 sont des garrots posés autour de ce placement.

## Objective

Que le journal d'audit MSS soit **écrit dans une table unique de la base commune**, et non plus
dans une table par praticien — de sorte qu'un lot de traces devienne **une insertion groupée sur
une connexion**, au lieu d'une centaine de connexions vers une centaine de bases.

Les invariants de task-186 et task-292 sont **conservés sans exception** : zéro perte,
contre-pression plutôt que perte, tampon Redis, durées de rétention par famille de trace,
aucune donnée de santé en clair dans les logs.

### Pourquoi le journal est le pire candidat possible au sharding par praticien — mesuré

| Fait | Source |
|---|---|
| ~2 000 traces/min à 1000 médecins (413 939 traces en 3 h 30 le 2026-09-08) | `AuditOptions.PeakTracesPerMinute` |
| Le drain persiste **0,2 à 0,45 trace/s** par réplica, pour **~4/s émises** | `AuditOptions.DrainParallelism` |
| Un lot de 100 traces s'étale sur **~100 bases ⇒ ~100 pools Npgsql ⇒ ~100 logins Postgres** | idem |
| **52 088 des 53 456** exceptions `53300` (« too many clients ») viennent de `AuditBackgroundService` — **97 %** | task-298, attribution Seq du 2026-09-11 |
| Le rejeu du tampon a porté Postgres à 2 500 backends en 3 minutes, 27 575 refus, VM figée 45 min — **trois fois dans la même journée** | task-296 jambe B |
| Le remède « évident » (drain concurrent, degré 8) a **aggravé** : 15 873 `08P01` contre 646 | `AuditOptions.DrainParallelism` |

Le raisonnement tient en une phrase : **un journal d'audit est un flux d'écriture append-only,
à fort débit, quasiment jamais relu ; le remède naturel d'un tel flux est l'insertion groupée,
et le sharding par tenant détruit mécaniquement la groupabilité.** On paie le coût maximal de
l'isolation pour un bénéfice d'isolation quasi nul : personne ne joint le journal au dossier
patient.

En base commune, le drain redevient : **une connexion, une insertion de 1 000 lignes**.

### Ce que cette US rend caduc

- Le plafond `Audit:DrainMaxConnections = 16` (task-298) n'a **plus d'objet sur le chemin
  d'audit** : il n'y a plus qu'une base à drainer. Le réglage reste pour le chemin de
  provisionnement. **task-298 ne doit pas être annulée pour autant** — son `application_name`
  explicite et l'attribution correcte des backends dans l'outillage de mesure sont nécessaires
  quelle que soit l'architecture, et son plafond protège l'existant jusqu'à la bascule.
- `Audit:DrainParallelism` devient sans objet (un seul groupe).
- La purge **opportuniste par tenant** devient une **purge planifiée globale**, ce que l'annuaire
  (task-299) rend enfin possible.

### ⚠️ Dépendance découverte à l'implémentation — le tenant n'est jamais matérialisé

L'en-tête de cette US affirme « **Indépendante de task-303** : `TenantId` étant défini dans
task-299 ». **Vérifié le 2026-09-13 dans le code mergé : la prémisse est fausse.**

| Ce que task-299 a livré | Ce qui manque |
|---|---|
| la table `tenants` et l'opération `EnsureTenantAsync` | **personne ne l'appelle** |
| `TenantRegistrySynchronizer` | n'appelle que `EnsureAccountAsync` — compte seul |
| `MssAuditTrace` | **aucun champ `TenantId`** |

Conséquence directe : la table `tenants` est **vide dans tous les environnements**, aucun
`TenantId` n'existe, et une table d'audit clée sur `tenant_id` n'aurait rien à écrire dedans.

**Résolu dans cette US, au plus petit périmètre possible** (plutôt que de sérialiser la ligne
audit derrière la ligne multi-BAL, ce que le plan excluait explicitement) :

1. `TenantRegistrySynchronizer` appelle `EnsureTenantAsync(subject, userContext.Email,
   userContext.UserDatabaseName)` après `EnsureAccountAsync` — la boîte courante devient un
   rattachement, avec le nom de base que l'application utilise déjà.
2. `MssAuditTrace` gagne `TenantId`, estampillé **à l'émission** (`AuditService`), là où le
   contexte de requête est disponible — jamais résolu par le drain, qui n'a plus de contexte.

**Ce que cela ne préempte pas de task-303.** Le couplage porte sur `UserContextInfo.Email`, dont
la *source* change avec task-303 (claim `mssEmail` → en-tête `Client-Email`) mais dont la *valeur*
ne change pas. task-303 remplace la résolution mono-boîte par la sélection multi-boîtes, ajoute la
compatibilité PSC et la fusion `mailboxes` + `tenants` → `mss_accounts` : elle **étend** ce que
cette US pose, elle ne le refait pas.

### Conception retenue

1. **Une table unique partitionnée** dans la base commune, **partitionnement déclaratif par mois**
   sur l'horodatage. Volumétrie à assumer dès le premier jour : ~2,9 M traces/jour à 1000
   médecins, soit ~1 milliard par an, avec une rétention de 3 653 jours sur les traces d'accès
   aux données de santé. Sans partitionnement, la purge et les index deviennent ingérables.

   **Créée par FluentMigrator, dans `Migrations/TenantDb/`** — le jeu de migrations de la base
   commune, borné par `TypeFilterOptions` et appliqué au démarrage (task-299). L'API fluente ne
   sait pas déclarer un partitionnement : la table mère et ses partitions passent par
   `Execute.Sql(...)`, **jamais** par une édition de migration déjà livrée (règle 7c).

   > ⚠️ **Les partitions futures doivent être créées d'avance, et c'est un point de panne
   > silencieux à retardement.** Une insertion dont l'horodatage ne tombe dans aucune partition
   > échoue — `no partition of relation … found for row`. Le défaut ne se déclenche pas à un
   > changement de code mais **à une date**, et ce jour-là c'est le journal d'audit qui s'arrête,
   > c'est-à-dire la conformité. Deux obligations, donc :
   >
   > - **avance d'au moins 3 mois** maintenue par le démarrage du service (idempotent :
   >   `CREATE TABLE IF NOT EXISTS … PARTITION OF …`), au même endroit que la migration — pas un
   >   cron, `api-mail` n'en a pas (voir `reference_api_mail_no_tenant_enumeration`) ;
   > - **une partition `DEFAULT`** comme filet : une trace hors plage y atterrit au lieu d'être
   >   perdue, et une métrique la signale. Un journal d'audit ne perd pas de ligne en silence.
   >
   > Le drain absorbe déjà l'indisponibilité par le tampon Redis — mais une erreur d'insertion
   > n'est pas une indisponibilité : elle serait rejouée indéfiniment jusqu'à saturer le tampon.
2. **Colonne `TenantId`** = l'identifiant du **tenant** au sens de task-299, c'est-à-dire du
   **rattachement (compte × messagerie)** — **jamais** l'id du compte, **jamais** celui de la
   messagerie, **jamais** l'email. Index principal `(tenant_id, timestamp desc)`.

   > ⚠️ Se tromper ici est une **fuite de données de santé entre praticiens**, pas une imprécision :
   > `MssAuditTrace.UserId` stocke l'email, donc deux PS partageant une adresse MSSanté
   > organisationnelle ont le **même** `UserId` et des bases distinctes. Seul le tenant les sépare.
   > La définition fait foi dans task-299 (§ Modèle retenu) ; cette US la consomme, elle ne la
   > réinvente pas.
3. **Isolation par la base de données, pas seulement par le code.** La frontière d'isolation
   cesse d'être une base PostgreSQL : elle doit être rétablie **dans** la base commune, sinon
   un filtre oublié devient une fuite de données de santé entre praticiens (la trace porte
   `PatientIns`, `PatientName`, `Subject`, `FromAddress`). Trois couches cumulées, pas une :
   - **RLS PostgreSQL** sur la table, prédicat sur `tenant_id`, alimenté par un
     `SET LOCAL` par requête ;
   - **filtre de requête global** obligatoire côté EF sur l'entité ;
   - **rôle d'écriture distinct** pour le drain (il écrit pour tous les tenants) du **rôle de
     lecture** utilisé par l'écran du praticien (soumis à RLS, sans contournement possible).
4. **Route directe conservée** (motif task-292 : un pooler saturé peut ralentir le praticien,
   il ne doit jamais faire échouer son journal), mais avec un pool **petit et fixe**
   (2 connexions), `Application Name=mss-mail-audit` (convention task-298).
   **Séparation d'avec l'annuaire** (arbitrage 2026-09-13 : la base centrale aura son propre
   backend d'API) : le chemin d'écriture du journal passe par un contrat **distinct** de
   `ITenantRegistryClient` — `IAuditSink.WriteBatchAsync(IReadOnlyList<AuditTraceRecord>)` dans
   `mss.mail.application.Services.Repository.TenantDb`, ses `record` de données dans
   `mss.mail.Domain.Entities.TenantDb`, implémentation Postgres dans
   `Infrastructure/Repositories/TenantDb`. Il est asynchrone, **par lots**, idempotent (clé de
   trace), et son indisponibilité est absorbée par le tampon Redis : c'est un contrat
   d'arrière-plan, pas de chemin de requête. Il pourra devenir distant (gRPC par lots) sans
   toucher au drain. L'écran de lecture du praticien passe, lui, par `IAuditReader` (même
   emplacement), scopé par tenant, RLS appliquée côté implémentation.

   > ⚠️ **Pas dans le SDK.** task-299 y avait placé `ITenantRegistryClient` ; la décision a été
   > **révisée le 2026-09-13** — un contrat publié en paquet impose un cycle publication + bump
   > à chaque évolution du modèle. Les deux contrats d'audit suivent la même règle : isolation
   > par espace de noms, garde-fous par test de réflexion. Voir « Révision post-review » dans
   > `done-task-299.md`.

   **Le contrat ignore la transition.** `IAuditReader` expose *lire les traces d'un tenant* —
   point. La lecture double source (§5) vit **entièrement dans l'implémentation** et disparaîtra
   avec elle (task-301) **sans toucher à une seule signature**.
5. **Lecture pendant la transition (double source).** Tant que task-301 n'a pas repris
   l'historique, l'écran d'audit du praticien lit **les deux** sources et les fusionne :
   la base commune pour les traces postérieures à l'instant de bascule, la table du tenant pour
   les antérieures. L'instant de bascule est enregistré **par tenant**, dans une colonne
   `AuditCutoverAt` **ajoutée au tenant par cette US** (task-299 crée la table, pas cette
   colonne — elle n'a de sens que pour le journal). Cela rend la partition du temps
   **déterministe** : aucune trace en double, aucune manquante. La
   pagination est bornée par le plafond de taille de page existant (200). **Ce chemin double
   est transitoire et retiré par task-301.**
6. **Purge planifiée** sur la base commune : suppression par lots des traces techniques au-delà
   de 365 j, **suppression de partition entière** pour les traces d'accès aux données de santé
   au-delà de 3 653 j. Les comptes dormants (registre) sont purgés comme les autres — c'est
   précisément le défaut RGPD que task-299 débloque.

   **La classification des familles n'est pas réinventée** : elle est déjà dans le code
   (`AuditRetentionPolicy.FamilyOf`, liste **explicite** de traces techniques, tout le reste en
   accès aux données de santé — le défaut est délibérément la rétention **la plus longue**). La
   purge appelle cette fonction, elle ne duplique pas la règle. Et elle **respecte le verrou
   légal** : une durée configurée à `0` désactive la purge de cette famille
   (`AuditRetentionOptions`, sémantique à trois états) — une partition qui contient une seule
   ligne sous verrou ne peut pas être supprimée.

### Le risque assumé, écrit noir sur blanc

Le mode de panne devient **global**. Aujourd'hui, une base praticien indisponible ne
contre-pressionne que ce praticien ; demain, la base commune indisponible les contre-pressionne
**tous**. Le tampon Redis couvre 3 heures de saturation (`SpillRetentionMinutes = 180`) et la
contre-pression reste le filet — mais c'est un arbitrage, pas un détail, et il doit être
explicitement accepté au HAG.

### Ce que ce n'est pas

Ni la reprise de l'historique (task-301), ni l'accès admin / sécurité (task-302), ni la
mutualisation des mails et des dossiers patients — **la base par praticien garde tout son sens
pour ceux-là** (secret médical, rayon de souffle, restauration par praticien, et un jeu de
travail qui se partitionne réellement). La réponse est hybride, pas « abandon du multi-base ».

## Definition of Done

- [ ] Build passes on `api-mail` (0 errors) ; tests pass (0 failures)
- [ ] Table d'audit commune **partitionnée par mois**, index `(tenant_id, timestamp desc)`,
      créée par une migration FluentMigrator de `Migrations/TenantDb/` (jeu borné par
      `TypeFilterOptions`, appliqué au démarrage — task-299), partitionnement déclaré via
      `Execute.Sql`
- [ ] **Partitions futures maintenues avec au moins 3 mois d'avance** au démarrage du service,
      de façon idempotente, **plus une partition `DEFAULT`** — et un test qui prouve qu'une trace
      horodatée hors de toute partition nommée **atterrit dans `DEFAULT` sans être perdue**, avec
      une métrique qui la signale. Sans cela, le journal s'arrête à une date, pas à un changement
      de code
- [ ] Test : deux pods qui démarrent ensemble ne se marchent pas dessus sur la création des
      partitions (même verrou consultatif que le provisionnement — `MigrationHelper`)
- [ ] Test unitaire : un lot de N traces couvrant M tenants distincts produit **une seule**
      insertion groupée et **une seule** connexion, quel que soit M (compteur de connexions
      observé) — c'est l'inversion exacte du défaut mesuré
- [ ] Test unitaire : invariant task-292 conservé — sous échec de persistance, les traces sont
      re-tamponnées et jamais jetées (`dropped == 0`) ; seul le cas poison reste plafonné par
      `MaxPersistAttempts`
- [ ] Test unitaire : contre-pression inchangée — tampon plein ⇒ l'appelant est retenu
      `BackpressureTimeout` puis l'action est refusée (503), jamais la trace perdue
- [ ] **Test de sécurité (bloquant)** : avec le rôle de lecture, une requête sans
      `SET LOCAL` de tenant rend **zéro ligne** ; une requête avec le tenant A ne rend **aucune**
      trace du tenant B, **même si le filtre applicatif est retiré** (le test doit échouer si
      la RLS n'est pas la couche qui tient). Extension de `CrossTenantOwnershipTests`
- [ ] **Test de sécurité (bloquant) — adresse organisationnelle** : deux comptes PS distincts
      rattachés à la **même** adresse MSSanté (donc même `MssAuditTrace.UserId`, deux tenants)
      ⇒ chacun ne voit **que** ses propres traces. C'est le cas que `TenantId = id du compte` ou
      `= id de la messagerie` casserait silencieusement
- [ ] Test : la purge appelle `AuditRetentionPolicy.FamilyOf` (aucune reclassification locale) ;
      une famille configurée à `0` jour (verrou légal) n'est **jamais** purgée, y compris par
      suppression de partition
- [ ] Test : le rôle d'écriture du drain ne peut pas **lire** la table ; le rôle de lecture ne
      peut pas écrire
- [ ] Test d'intégration : lecture double source — un praticien dont l'historique straddle
      l'instant de bascule voit **toutes** ses traces, dans le bon ordre, **sans doublon**
      (fixture : 3 traces avant bascule, 3 après, pagination par 2)
- [ ] Test : purge planifiée — les traces techniques > 365 j sont supprimées par lots, les
      partitions > 3 653 j sont supprimées entières, et **aucune trace en deçà n'est touchée** ;
      un compte dormant est purgé exactement comme un compte actif
- [ ] Chaîne de connexion du chemin d'audit : `Application Name=mss-mail-audit`, pool borné à 2
- [ ] `IAuditSink` / `IAuditReader` dans `mss.mail.application.Services.Repository.TenantDb`,
      `AuditTraceRecord` dans `mss.mail.Domain.Entities.TenantDb` ; implémentations Postgres dans
      `Infrastructure/Repositories/TenantDb`, **seules** à référencer le `DbContext` commun (test
      d'architecture, même motif que task-299). **Aucune entité de persistance ne franchit les deux
      contrats** — test de réflexion sur leur surface, comme
      `TenantRegistryContractTests.NoPersistenceType_CrossesTheContract`. Le drain ne connaît que
      `IAuditSink`
- [ ] Aucune donnée de santé en clair dans les logs et métriques du nouveau chemin (INS, nom de
      patient, sujet, contenu) — test de contrat sur les champs journalisés
- [ ] Métriques conservées et cohérentes : `mss_audit_traces_emitted_total ==
      mss_audit_traces_persisted_total` à vide, `mss_audit_traces_dropped_total` absent/0
- [ ] Documentation : ADR `Api/Mail/docs/ADR-2026-09-13-journal-audit-mutualise.md` (mesure,
      conception, **risque de mode de panne global**, ce qui devient caduc de task-292/294/298) ;
      mise à jour de `ADR-2026-07-27-pgbouncer-transaction-mode.md` § risques résiduels
- [ ] **Mesure au banc** (journey 1000, protocole iso task-298, Postgres 48 Go, mêmes bases) :
      **0** refus `53300` imputable à l'audit, backends max **< 1 500**, débit de persistance
      **≥ débit d'émission** en régime (le tampon se vide au lieu de croître), rejeu post-tir
      sans tempête ni redémarrage de VM ; rapport dans `Docs/audits/` et ligne dans
      `Api/Mail/tests/loadtest-k6/reports/INDEX.md`

> **Portée réalisable par la forge.** Tout le code et tous les tests unitaires / d'intégration
> sont dans le périmètre de `/develop`. La **mesure au banc** est un acte humain (tir de
> plusieurs heures via le skill `loadtest-skill`, 1000 bases hydratées) : `/review` la trouvera
> non cochée, c'est attendu.

## Manual Test Plan

- **Lancer** : `cd Api/Mail && aspire run --project src/AppHost`
- **Actions et vérifications** :
  1. Se connecter avec deux praticiens de test, faire une action tracée chez chacun (ouvrir un
     message), puis compter les lignes de la table d'audit commune par `tenant_id` : **une
     ligne par praticien**, dans la partition du mois courant.
  2. Ouvrir l'écran d'audit de chacun : **chacun ne voit que ses propres traces** — c'est la
     vérification métier centrale de cette US.
  3. Vérifier la couche de sécurité à la main. **Les deux rôles sont `NOLOGIN`** — ils sont
     endossés, jamais utilisés pour ouvrir une session : poser un mot de passe dans une migration
     serait un secret en clair dans le dépôt, et deux comptes de plus exposés au réseau. On les
     endosse donc :
     ```sql
     -- aucun tenant positionné ⇒ ZÉRO ligne (et non une erreur)
     BEGIN; SET LOCAL ROLE mss_audit_reader; SELECT count(*) FROM audit_traces; ROLLBACK;

     -- tenant A positionné ⇒ QUE les traces de A
     BEGIN; SET LOCAL ROLE mss_audit_reader;
       SELECT set_config('mss.tenant_id', '<tenant-A>', true);
       SELECT DISTINCT tenant_id FROM audit_traces; ROLLBACK;

     -- le rôle d'écriture ne peut pas lire
     BEGIN; SET LOCAL ROLE mss_audit_writer; SELECT count(*) FROM audit_traces; ROLLBACK;
     -- attendu : 42501 permission denied
     ```
  4. Vérifier l'attribution des connexions :
     `docker exec postgres-pgvector psql -U postgres -c "select application_name, count(*) from pg_stat_activity group by 1"`
     → `mss-mail-audit` reste à **2 au plus**, quel que soit le nombre de praticiens actifs
     (comparer à la situation actuelle, où il monte avec le nombre de bases drainées).
  5. Couper Postgres 2 minutes (`docker pause`), continuer à agir dans l'application, le
     relancer : les traces du tampon Redis sont rejouées **sans** tempête de connexions, et
     `mss_audit_traces_dropped_total` reste à 0.
  6. Lecture double source : sur un praticien disposant de traces antérieures à la bascule,
     paginer l'écran d'audit de bout en bout → continuité chronologique, **aucun doublon**,
     **aucun trou**.
- **Données de test** : praticiens synthétiques du banc, aucune donnée réelle.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — robustesse et conformité du journal de la messagerie MSSanté
- **Exigences DSR honorées** : non applicable directement — l'US sert l'exigence PGSSI-S de
  journalisation en la rendant **tenable à l'échelle** (aujourd'hui le journal est le premier
  composant qui casse sous charge, ce qui est en soi un risque de conformité)
- **INS** : la trace porte `PatientIns` — **c'est voulu et conforme** : l'INS est obligatoire
  dans le journal d'audit en base, et interdit dans les logs applicatifs (arbitrage 2026-09-07,
  task-186). Cette US **ne change ni le contenu ni la finalité de la trace**, seulement son
  emplacement physique
- **Authentification PS** : inchangée — PSC / e-CPS, eIDAS substantiel
- **Habilitations** : **inchangées pour le praticien** — il ne voit que ses propres traces, et
  cette US en renforce la garantie (RLS en base, là où il n'y avait qu'un `WHERE` applicatif).
  **Aucun accès transverse n'est ouvert ici** : c'est task-302, et elle est conditionnée à la
  création d'un modèle de rôles qui n'existe pas dans `api-mail` aujourd'hui
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : cette US **est** le journal PGSSI-S. Évènements journalisés inchangés ;
  durées de conservation inchangées (3 653 j accès aux données de santé, 365 j technique), mais
  désormais **effectivement applicables** grâce à la purge planifiée
- **Consentement patient** : non applicable — journal de traçabilité, base légale distincte du
  consentement (obligation de journalisation)
- **Sécurité / confidentialité** : la frontière d'isolation passe d'une frontière
  d'infrastructure (une base par praticien) à une frontière logique. **C'est le point sensible
  de l'US**, et il est traité par trois couches cumulées (RLS, filtre global, séparation des
  rôles lecture/écriture), chacune couverte par un test bloquant
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — la base commune héberge désormais des DSCP (INS, nom de patient,
  sujet de message). Même environnement HDS, même niveau d'exigence que les bases praticien
- **AIPD / impact RGPD** : **à mettre à jour — validé par le DPO le 2026-09-13**. La
  mutualisation des journaux en un traitement unique est acceptée. L'AIPD doit refléter : la
  nouvelle base porteuse de DSCP, les mesures de cloisonnement (RLS + rôles), et la purge
  planifiée qui corrige le défaut art. 5.1.e existant

---

## Branches

- `api-mail` (pushed) : `feat/task-300-journal-audit-base-commune` — base `origin/develop`
  @ `142e0cd7` (task-299 mergée)
- `dtos-mss` (pushed) : `feat/task-300-journal-audit-base-commune` — branche auto-incluse
  (CLAUDE.md « Auto-included repo »). Sans changement de contrat, elle restera **sans commit** et
  n'ouvrira aucune PR.

> **Pré-flight** : les six repos automatisés étaient sur `develop` ; arbres propres.
> Dépendance `task-299` satisfaite — `tasks/archived/archived-task-299.md`, état terminal qui suit
> `done-*`.

> **Note de séquencement.** Cette US crée la table d'audit **dans la base commune**, celle-là même
> où task-303 fusionnera `mailboxes` + `tenants` en `mss_accounts`. Les deux sont indépendantes :
> le renommage d'une table emporte ses clés étrangères côté PostgreSQL, et la colonne du journal
> reste `tenant_id` quel que soit l'ordre de merge (arbitrage du 2026-09-13 — le renommage s'arrête
> aux tables, `mss_accounts.id` **est** le `TenantId`).

## Timings

*(généré par `tools/timing/report.sh --task task-300 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 45 s | — | — | — | — |
| /develop | ok | 40 min 06 s | — | — | — | — |
| /sonar | ok | 18 min 55 s | — | — | — | 2 itération(s) |
| /lint-angular | skipped | 3.3 s | — | — | — | client-angular non touche par task-300 (Repos: api-mail) |
| /lint-mobile | skipped | 2.0 s | — | — | — | client-mobile non touche par task-300 (Repos: api-mail) |
| /verify-visual | skipped | 2.1 s | — | — | — | aucun ecran client-mobile touche (US backend) |
| /review | ok | 16 min 33 s | — | — | — | — |
| /tech-writer | ok | 3 min 18 s | — | — | — | — |
| **Total cycle** | | **1 h 19 min** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |

## Sonar log

**2 itérations** (scan initial + scan de vérification après correction).

### KPIs qualité (baseline → final)

| Métrique | Baseline (scan task-299) | Final | Δ |
|---|---|---|---|
| **Quality Gate (new code)** | ERROR | ERROR | = |
| `new_violations` | 155 | **167** | **+12** |
| `new_bugs` | 2 | 2 | = |
| `new_vulnerabilities` | 2 | 2 | = |
| `new_code_smells` | 151 | 166 | +15 |
| `new_coverage` | 89,1 % | 88,2 % | −0,9 |
| Coverage projet | 88,5 % | 88,1 % | −0,4 |
| Duplication | 0,3 % | 0,4 % | +0,1 |
| Reliability / Security / Maintainability | 3,0 / 5,0 / 1,0 | 3,0 / 5,0 / 1,0 | = |

### Ce que task-300 a réellement introduit : **0**

Le chiffre `+12` ne doit pas être lu comme de la dette introduite. Vérifié issue
par issue via l'API :

| Périmètre | Issues ouvertes |
|---|---|
| **Fichiers créés par task-300** (12 fichiers : contrats, `record`, entité, migration, maintenance des partitions, 3 implémentations, 2 fichiers de tests) | **0** |
| **Fichiers modifiés par task-300** | **0 imputable** — 5 issues, toutes préexistantes : `S138` sur `AddApplication` (97 lignes, méthode non touchée), `S4462 ×3` sur les chemins dégradés de `AuditService` (task-292), `xUnit2033` sur un test de middleware non modifié |

**D'où vient alors le +12ceau ?** De la **fenêtre de new-code**, pas du code neuf :
toucher un fichier y fait entrer ses issues **préexistantes**. C'est le piège
déjà documenté (« la new-code period inclut des tasks déjà mergées ») — un
Quality Gate `ERROR` sans dette introduite.

### Corrigé pendant cette étape (3 issues, toutes sur du code neuf)

| Règle | Où | Fait |
|---|---|---|
| `S4457` ×2 | `PostgresAuditSink.WriteBatchAsync`, `PostgresAuditReader.GetTracesAsync` | Validation sortie du corps `async` → méthode publique non-`async` qui délègue à un `…CoreAsync` privé |
| `xUnit2033` ×1 | `AuditJournalIntegrationTests` | Valeur **rendue** par `Assert.Single` au lieu de re-indexer |

> ⚠️ **`S4457` est une récidive** : la consigne existait dans
> `conventions/csharp.md` depuis task-299, et n'a pas été appliquée sur du code
> frais. Compteur incrémenté (1 → 2) avec l'avertissement correspondant.

### Security hotspots (`new_security_hotspots_reviewed` 83,3 % ⇒ ERROR)

Les 2 hotspots à revoir sont dans `tests/loadtest-k6/test_report_session_lock_regime.py`
(URLs `http://localhost` d'un test Python du banc, task-298). **Hors périmètre de
cette US**, aucun code livré ici n'est concerné.

## Lint log

**`/lint-angular` : skip propre.** `client-angular` n'est pas dans le
`**Repos**:` de cette US (`api-mail` seul) et aucune ligne d'Angular n'a été
écrite.

> Les deux fichiers modifiés dans `Client/Angular/` au moment du passage
> (`front/apps/mss/src/environments/environment.ts`,
> `front/apps/weda2/src/environments/environment.ts`, branche
> `feature/nova-rewriting-mss`) sont **antérieurs et étrangers** à task-300 —
> configuration locale de l'humain. Mode code-only : la forge ne touche ni au
> contenu ni à git sur ce repo.

**`/lint-mobile` : skip propre.** `client-mobile` n'est pas dans le `**Repos**:`
et aucun écran n'a été touché.

**`/verify-visual` : skip propre.** Aucun écran `client-mobile` touché — US
strictement backend (journal d'audit, migration, RLS).

---

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/234
  — label `awaiting-human-merge`.
- `dtos-mss` : **aucune PR** — branche auto-incluse, **0 commit** (cette US n'expose aucune route
  et ne change aucun contrat de fil).
- `client-angular` / `client-mobile` / `client-blazor` : **non concernés** — US strictement
  backend. Aucun écran, aucun DTO, aucune signature HTTP touchée.

## Code Review Summary

**APPROVED** — 35 fichiers revus. **4 défauts bloquants trouvés et corrigés avant la PR**,
0 restant.

| Défaut | Où | Pourquoi il était invisible |
|---|---|---|
| `ON CONFLICT (id, timestamp)` exige `SELECT` | `PostgresAuditSink` | Le rôle d'écriture ne doit pas pouvoir lire — refus `42501` à l'exécution seulement |
| `current_setting(…, true)` rend `''`, pas `NULL` | migration, politique RLS | Invisible sur connexion neuve ; `''::uuid` lève `22P02` sur une connexion recyclée |
| `DELETE … WHERE ctid IN (…)` faux sur table partitionnée | `PostgresAuditJournalPurge` | Le `ctid` n'est unique que **par** partition ⇒ suppression de traces encore en conservation |
| `SET LOCAL` hors transaction explicite sans effet | `PostgresAuditReader` | L'utilisateur des conteneurs de test est `SUPERUSER` et **contourne la RLS** |

Les quatre ont été **prouvés à l'exécution** avant correction, et le dernier a été **re-injecté**
après correction pour vérifier que son test mord (il échoue alors sur « Collection was empty » —
le symptôme exact de production : écran d'audit vide).

### Trois items de DOD non tenus, comblés pendant la revue

Cochés à blanc, ils auraient fait passer la PR pour complète :

1. chaîne de connexion dédiée `Application Name=mss-mail-audit`, pool borné à 2 ;
2. test d'intégration de la lecture double source (3 avant / 3 après, pagination par 2) ;
3. test de contrat « aucune donnée de santé dans les journaux techniques ».

### Suggestions non bloquantes

- La fenêtre de fusion double source est plafonnée à 2 000 lignes par source. Au-delà, la
  pagination profonde rend des pages incomplètes — acceptable car le chemin disparaît avec
  task-301, et le contrat HTTP plafonne déjà la page à 200.
- `AuditRetentionPolicy.ActionNamesOf` est appelé à chaque purge ; un cache statique serait
  gratuit. Non fait : la purge est planifiée, pas sur un chemin chaud.

---

## Merged — 2026-09-13

Mergée par l'humain après attestation `--i-tested` (HAG, règle 10).

| Repo | PR | Commit de squash | CI `develop` |
|---|---|---|---|
| `api-mail` | [#234](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/234) | `ff6332f7` | ✅ vert (4 min 04 s) |
| `dtos-mss` | — | aucune PR, **0 commit** | — |

Branches distantes supprimées ; **branches locales conservées** (le drapeau
`--delete-branch` de `gh` supprime aussi la locale — jamais utilisé ici).

Portes de sécurité au moment du merge : `mergeState CLEAN`, `MERGEABLE`, build `SUCCESS`,
aucun `CHANGES_REQUESTED`, **0 commit de retard** sur `develop`, arbres de travail propres.

### ⚠️ Collision à venir avec task-303 — à traiter dans task-303, pas ici

task-303 est **en cours dans une session parallèle** (6 commits sur
`feat/task-303-comptes-multi-messageries` au moment de ce merge), et son commit
`0f7d8844` fait passer le registre **à deux tables** : `tenants` devient `mss_accounts`,
`RegistryMailboxRow` disparaît. Vérifié sur sa branche.

task-300, qui vient d'être mergée, s'appuie sur `tenants` à trois endroits :

| Où | Ce qui casse | Comment ça se manifeste |
|---|---|---|
| migration `20260914090000` — `ALTER TABLE tenants ADD audit_cutover_at` | la table n'existe plus sous ce nom | ⚠️ **SILENCIEUX** — échec au démarrage avalé par le `LogWarning` du `TenantRegistrySchemaInitializer` |
| `PostgresAuditSink.MarkCutoverAsync` (`UPDATE tenants`) et `PostgresAuditReader.ReadCutoverAsync` (`context.Tenants`) | DbSet renommé | erreur de compilation — bruyant |
| `AuditJournalIntegrationTests` / `AuditDualSourceReadTests` (`RegistryMailboxRow`) | type supprimé | erreur de compilation — bruyant |

**C'est la même classe de piège que task-298 → task-299** : le renommage produit des
conflits bruyants sur le code, et **un trou parfaitement silencieux sur la migration**,
parce qu'un fichier neuf n'entre jamais en conflit textuel.

**Ce que task-303 doit faire en se resynchronisant sur `develop`** :

1. sa migration de renommage doit **emporter `audit_cutover_at`** — `ALTER TABLE … RENAME`
   conserve les colonnes, donc c'est gratuit **à condition** que sa migration s'exécute
   après celle de task-300 (numéro de version supérieur : `20260914090000` est déjà pris) ;
2. `PostgresAuditSink` et `PostgresAuditReader` suivent le renommage du DbSet ;
3. les deux fichiers de tests d'intégration du journal cessent de semer un
   `RegistryMailboxRow` ;
4. **vérifier au démarrage** que la migration du journal s'est appliquée — le
   `LogWarning` qui protège le démarrage est précisément ce qui masquerait l'échec.

L'ordre était contraint dans le bon sens : task-303 ne peut pas merger avant task-304
(règle 11, US-complete), donc elle se resynchronise de toute façon.

### Reste ouvert après ce merge

- **`devops`** : provisionner `mss_registry` et poser `TenantRegistry__ConnectionString`
  dans les environnements déployés. Chaîne vide ⇒ registre désactivé **en silence**, et
  le journal retombe sur l'ancien chemin par praticien — le correctif de capacité ne
  produirait alors aucun effet.
- **Mesure au banc** (DOD non cochée, attendu) : tir journey 1000, protocole iso
  task-298, Postgres 48 Go. **0** refus `53300` imputable à l'audit, backends max
  < 1 500, débit de persistance ≥ débit d'émission. Acte humain via `loadtest-skill`.
- **`questions/task-302.md`** : accès admin / sécurité au journal, en attente
  d'arbitrage — aucun modèle de rôles n'existe dans `api-mail`. Le journal mutualisé est
  livré ; seuls les praticiens peuvent le lire.
- **Le mode de panne global** a été accepté à ce merge : la base commune indisponible
  contre-pressionne **tous** les praticiens. Tampon Redis 3 h, contre-pression en filet,
  traces sans tenant sur l'ancien chemin, partition `DEFAULT` en dernier recours.
