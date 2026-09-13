# todo-task-300.md — Journal d'audit en base commune : sortir l'écriture du journal du sharding par praticien

**Repos**: sdk, api-mail
**Dependencies**: **task-299** (annuaire — fournit l'identifiant de tenant stable et la dormance
qui pilote la purge ; pose le motif « contrat SDK / implémentation api-mail » que cette US
reproduit). Recouvre partiellement **task-298** : voir « Ce que cette US rend caduc ».
**Epic**: E016
**Single frontend**: true
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

### Conception retenue

1. **Une table unique partitionnée** dans la base commune, **partitionnement déclaratif par mois**
   sur l'horodatage. Volumétrie à assumer dès le premier jour : ~2,9 M traces/jour à 1000
   médecins, soit ~1 milliard par an, avec une rétention de 3 653 jours sur les traces d'accès
   aux données de santé. Sans partitionnement, la purge et les index deviennent ingérables.
2. **Colonne `TenantId`** (identifiant stable issu de l'annuaire task-299), **jamais** l'email.
   Index principal `(tenant_id, timestamp desc)`.
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
   `IDirectoryClient` — `IAuditSink.WriteBatchAsync(IReadOnlyList<AuditTraceRecord>)` dans le SDK
   (`HealthPlatform.Host.Sdk.Audit.V1`), implémentation Postgres dans `api-mail`. Il est
   asynchrone, **par lots**, idempotent (clé de trace), et son indisponibilité est absorbée par
   le tampon Redis : c'est un contrat d'arrière-plan, pas de chemin de requête. Il pourra devenir
   distant (gRPC par lots) sans toucher au drain. L'écran de lecture du praticien passe, lui, par
   `IAuditReader` (même paquet), scopé par tenant, RLS appliquée côté implémentation.
5. **Lecture pendant la transition (double source).** Tant que task-301 n'a pas repris
   l'historique, l'écran d'audit du praticien lit **les deux** sources et les fusionne :
   la base commune pour les traces postérieures à l'instant de bascule, la table du tenant pour
   les antérieures. L'instant de bascule est enregistré par tenant dans l'annuaire, ce qui rend
   la partition du temps **déterministe** : aucune trace en double, aucune manquante. La
   pagination est bornée par le plafond de taille de page existant (200). **Ce chemin double
   est transitoire et retiré par task-301.**
6. **Purge planifiée** sur la base commune : suppression par lots des traces techniques au-delà
   de 365 j, **suppression de partition entière** pour les traces d'accès aux données de santé
   au-delà de 3 653 j. Les comptes dormants (annuaire) sont purgés comme les autres — c'est
   précisément le défaut RGPD que task-299 débloque.

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

- [ ] Build passes on api-mail (0 errors)
- [ ] Tests pass (0 failures)
- [ ] Table d'audit commune **partitionnée par mois**, index `(tenant_id, timestamp desc)`,
      créée et migrée par le chemin de migration de la base commune (task-299)
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
- [ ] Test : le rôle d'écriture du drain ne peut pas **lire** la table ; le rôle de lecture ne
      peut pas écrire
- [ ] Test d'intégration : lecture double source — un praticien dont l'historique straddle
      l'instant de bascule voit **toutes** ses traces, dans le bon ordre, **sans doublon**
      (fixture : 3 traces avant bascule, 3 après, pagination par 2)
- [ ] Test : purge planifiée — les traces techniques > 365 j sont supprimées par lots, les
      partitions > 3 653 j sont supprimées entières, et **aucune trace en deçà n'est touchée** ;
      un compte dormant est purgé exactement comme un compte actif
- [ ] Chaîne de connexion du chemin d'audit : `Application Name=mss-mail-audit`, pool borné à 2
- [ ] `sdk` : `IAuditSink` / `IAuditReader` + `AuditTraceRecord` dans
      `HealthPlatform.Host.Sdk.Audit.V1`, sans dépendance Npgsql/EF ; NuGet publié, consommateurs
      bumpés. `api-mail` : implémentations Postgres seules à référencer le `DbContext` commun
      (test d'architecture, même motif que task-299). Le drain ne connaît que `IAuditSink`
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
  3. Vérifier la couche de sécurité à la main :
     `docker exec postgres-pgvector psql -U mss_audit_reader -d mss_directory -c "select count(*) from audit_traces"`
     → **0** (aucun tenant positionné). Le même compte avec le tenant A positionné ne doit
     jamais rendre une trace du tenant B.
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
