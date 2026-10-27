# todo-task-400.md — Délégation de BAL : tracer qui agit dans quelle BAL, et le montrer au délégant

**Repos**: dtos-mss, api-mail, client-angular
**Dependencies**: task-397 (actes délégués, liste blanche d'audit de la règle 14, banc de délégation)
**Epic**: E009
**Single frontend**: true — la consultation du journal n'existe que dans weda2. Le mobile n'a pas
d'écran Audit, et cette task n'en crée pas (décision 1).
**Priorité**: **3** — un délégataire agit déjà dans la BAL de son délégant. Mailiz rend le délégant
**responsable** des accès qu'il ouvre, mais il ne voit aucun de ces actes, et rien ne désigne la
**personne** qui a agi.

> **Analyse** : [Docs/audits/delegation-bal-mailiz-analyse-20261025.md](../Docs/audits/delegation-bal-mailiz-analyse-20261025.md).
> **Revue du code** : [Docs/audits/delegation-bal-revue-code-20261025.md](../Docs/audits/delegation-bal-revue-code-20261025.md),
> §3.4. Trois constats y rendaient la première version de cette task inopérante :
> - la sécurité par ligne ;
> - les adresses organisationnelles ;
> - l'absence de nom.
>
> **Règle 14** : l'audit est la seule exception à « rien de persisté », réduit à l'action,
> l'auteur, le dossier, l'UID et le `Message-ID`.

## Ce qui est établi

- **Journal mutualisé** (ADR-2026-09-14) : table `audit_traces` du registre commun.
  - Partitionnée par mois.
  - Conservation de 3 653 jours pour la famille `HealthDataAccess`.
  - Purge globale par suppression de partitions.
- **Sécurité par ligne** (`20260913120000_CreateTenantRegistry.cs:388-405`, FORCE ROW LEVEL
  SECURITY) :
  - la politique `audit_traces_tenant_read` ne laisse lire que `tenant_id = mss.tenant_id`, réglage
    posé par `PostgresAuditReader.EnterTenantScopeAsync` ;
  - il n'existe aucun droit ni politique `UPDATE`.
- **Identité** :
  - `user_id` est l'**adresse de la BAL** de la session ;
  - `TransportMssRpps` est le RPPS **de la BAL** (registre), pas celui de la personne ;
  - l'identité PSC de la session est `SessionPscIdentity(Subject, Rpps)`, **sans nom** ;
  - les consommateurs du bus (`RestoreFromMessage`) ne la transportent pas.
- **Nom** : la route `GET /v1/auth/userinfo` du **proxy PSC** rend `FirstName` et `LastName`.
  api-mail appelle déjà le proxy avec le cookie de session (`proxy_session_id`) et sa clé interne
  (route `context`, `PscTokenProvider.cs:270-280`). Il peut donc appeler `userinfo` de la même
  façon, **sans évolution du proxy**.
- **Lecture** :
  - `AuditController` : liste et détail, limités au tenant ;
  - `PostgresAuditReader.Map` (`:247-280`) rend aussi `UserSessionId`, `SourceIp`, `UserAgent`,
    `CorrelationId`, `ServerRequest/Response` ;
  - `ApplyFilters` (`:208-244`) **ignore** les filtres `ActionType` et `Search` que weda2 envoie.
- **weda2** (`libs/mss/src/features/audit`) :
  - liste, filtres, détail, chronologie par `Message-ID` ;
  - **export CSV existant**, avec objet et destinataires (`mss-audit.component.ts:129`) ;
  - dédoublonnage côté client **par UID seul** (`:224, 242`).

## Décisions actées (humain, 2026-10-25)

1. **Le délégant consulte les actes de ses délégataires dans weda2**, dans l'écran Audit existant,
   avec un filtre « actes de mes délégataires ». Pas d'écran sur le mobile.
2. **La personne est identifiée par son RPPS et son nom**, enregistrés dans la trace.
   - Le RPPS vient de la session PSC.
   - Le nom vient de la route **`userinfo` du proxy PSC**.
3. **Une trace, deux lecteurs** : visible du délégataire (son acte) et du délégant (sa BAL).
4. **Traces passées** : laissées en l'état (la base de test a été purgée). Pas de reprise.

## Objective

Tout acte fait dans une BAL déléguée est tracé avec **qui** (RPPS et nom), **depuis quelle BAL** et
**dans quelle BAL**. Le délégant le voit dans le journal de weda2, aux côtés de ses propres actes ;
le délégataire aussi. Aucun tiers ne le voit, et le délégant ne voit rien d'autre que ce qui le
concerne.

## Règles

### Champs de la trace

- **Personne qui agit** :
  - le RPPS est `SessionPscIdentity.Rpps`, jamais `MssRpps` ;
  - le nom est lu une fois par session sur `userinfo` et gardé avec la session. C'est l'identité
    du délégataire lui-même, pas une donnée déléguée.
- **Traces sans session PSC** : actor **nul**. Sont concernés :
  - les consommateurs du bus, puisque `MessageUserIdentity` ne porte pas l'identité PSC ;
  - la purge de rétention ;
  - les erreurs de connexion avant authentification ;
  - le hors-ligne Keycloak.

  Ces traces restent valides.
- **BAL propriétaire**, posée **explicitement par l'appelant**, jamais déduite après coup :
  - adresse du délégant pour un acte sur `shared/<adresse>/…` ;
  - adresse émettrice (`From`) pour un envoi ou une réponse ;
  - dossier cible pour un archivage ou un brouillon IMAP ;
  - BAL de la session sinon.
- **Acte délégué** : `owner_mailbox <> user_id`, adresses comparées **en minuscules**.
- **Contenu d'une trace déléguée** : la liste blanche de task-397 (action, date, succès, auteur,
  dossier, UID, `Message-ID`), plus la personne qui agit et la BAL propriétaire.

### Lecture

- **Nouvelle politique de lecture** (sécurité par ligne) : une trace est lisible si son
  `owner_mailbox` vaut l'adresse de la session **et** si c'est un acte délégué.
  - L'adresse est passée par un second réglage de session, posé **côté serveur** par
    `EnterTenantScopeAsync`, jamais par le client.
  - La politique existante par tenant reste inchangée.
- **Adresses organisationnelles** : plusieurs praticiens d'une même adresse ont des tenants
  distincts. La condition « acte délégué » garantit qu'aucun ne voit les traces **ordinaires** d'un
  autre.
- **Le délégataire** voit ses traces comme aujourd'hui, actes délégués compris, marqués « dans la
  BAL de `<adresse>` ».
- **Le délégant** voit ses traces et les actes délégués faits dans sa BAL, marqués « par `<nom>`
  (RPPS `<n°>`), délégation ».
  - Un délégataire ne voit jamais les actes d'**autres** délégataires.
  - Un tiers ne voit rien.
- **Liste blanche du lecteur** pour une trace lue **hors de son tenant** : `UserSessionId`,
  `SourceIp`, `UserAgent`, `CorrelationId`, `ServerRequest`, `ServerResponse`, `ErrorMessage` et
  `document_*` sont vidés. Le délégant ne voit pas la session ni le poste de son délégataire.
- **Détail** : `GET /audit/traces/{id}` suit la même politique. Le délégant obtient le détail d'un
  acte de son délégataire ; un tiers reçoit 404.
- **Filtres** : `ActionType` et `Search`, aujourd'hui ignorés côté serveur, sont **appliqués**. Le
  filtre « actes de mes délégataires » s'y ajoute.
- **Délégant pas encore utilisateur** : la trace est rattachée à son adresse. Il la verra à sa
  première connexion.
- **Délégation retirée** : les traces passées restent visibles du délégant pendant leur durée de
  conservation.

### Schéma

- **Nouvelles colonnes** nullables sur `audit_traces` : RPPS de la personne, nom de la personne, BAL
  propriétaire. Elles sont ajoutées par une migration de registre nouvelle (règle 7c), en
  métadonnées seulement.
- **Index partiel** `(owner_mailbox, timestamp DESC) WHERE owner_mailbox <> user_id`, construit sans
  bloquer l'écriture du journal :
  - `CREATE INDEX … ON ONLY` sur la table mère ;
  - `CREATE INDEX CONCURRENTLY` par partition ;
  - puis `ATTACH`.
- **Les champs traversent toutes les couches** : `MssAuditTrace` (sans `[JsonIgnore]`, pour le rejeu
  du tampon Redis), `AuditTraceRecord`, `ToRecord`, `PostgresAuditSink.Columns` et ses paramètres,
  `AuditTraceRow`, et le mapping du `TenantRegistryDbContext`.

### weda2

- **Colonnes** « Personne » (nom, RPPS) et « BAL propriétaire », triables.
- **Mentions** : « par … (RPPS …), délégation » et « dans la BAL de … ».
- **Dédoublonnage** : supprimé, ou avec une clé qui inclut la BAL propriétaire, le dossier et la
  personne. Le délégant et le délégataire agissent sur les **mêmes UID**.
- **Chemins** : pour le délégant, `shared/<lui>/X` devient son chemin propre (`shared/<lui>` →
  `INBOX`, `/Sent` → `Sent`, `/Demo` → `Demo`), pour l'affichage et pour ouvrir le message.
- **Chronologie par `Message-ID`** : elle respecte les mêmes règles de lecture.
- **Export CSV** (existant) :
  - il ajoute la personne et la BAL propriétaire ;
  - pour un acte délégué, il n'exporte que les champs de la liste blanche, sans objet ni
    destinataires.

## Definition of Done

- [ ] **Migration du registre** : colonnes, politique de lecture et index construit sans blocage.
      Audit de migration (règle 7c). Test qui montre que l'écriture du journal n'est pas bloquée
      pendant la construction de l'index.
- [ ] `dtos-mss` : la trace expose la personne, la BAL propriétaire et l'indicateur « acte délégué ».
      Paquet publié, consommateurs .NET mis à jour, types TypeScript de weda2 alignés.
- [ ] **Tests d'intégration exécutés sous un rôle non superutilisateur**, puisque le superutilisateur
      contourne la sécurité par ligne. B lit, puis supprime un message de `shared/<A>`. Vu rouge
      (règle 1b), lu dans la réponse réelle :
      - la liste de **A** renvoie les deux traces avec le RPPS et le **nom** de B (nom lu par
        `userinfo` au banc) et la BAL propriétaire = A ;
      - le détail `GET /audit/traces/{id}` de A les renvoie aussi ;
      - la liste de **B** les renvoie, marquées « dans la BAL de A ».
- [ ] Test d'intégration — **cloisonnement** :
      - C, aussi délégataire de A, ne voit pas les traces de B ;
      - D, un tiers, ne voit rien de A, ni en liste ni en détail ;
      - **deux tenants qui partagent une adresse organisationnelle** ne voient jamais leurs traces
        ordinaires l'un de l'autre.
- [ ] Test d'intégration : pour une trace lue hors de son tenant, `UserSessionId`, `SourceIp`,
      `UserAgent`, `CorrelationId`, `ServerRequest/Response`, `ErrorMessage` et `document_*` sont
      vides.
- [ ] Test d'intégration : A n'a jamais utilisé l'application ; B agit ; A se connecte, puis voit les
      actes de B.
- [ ] Test d'intégration : la délégation de B est retirée ; A voit toujours les traces passées.
- [ ] Test d'intégration : une trace émise par un consommateur du bus a une personne nulle et reste
      valide.
- [ ] Test d'intégration : un envoi au nom de A (task-399, s'il est livré) a pour BAL propriétaire A.
- [ ] Test d'intégration : les filtres `ActionType`, `Search` et « actes de mes délégataires » sont
      appliqués par le serveur.
- [ ] Test : une trace passée par le tampon Redis garde la personne et la BAL propriétaire.
- [ ] Tests de composants weda2 :
      - colonnes et mentions ;
      - filtre ;
      - **pas de masquage** d'un acte du délégataire par un acte du délégant sur le même UID ;
      - traduction `shared/<A>/X` vers `X` pour le délégant ;
      - export CSV conforme ;
      - chronologie cloisonnée.
- [ ] **Banc e2e** :
      - seconde identité PSC avec son tenant pour la délégante ;
      - contournement d'authentification paramétré par identité ;
      - nom de la personne fourni par le seed, car le contournement ne passe pas par `userinfo`.
- [ ] Scénario **E2E-DELEG-008** ajouté dans `Api/Mail/e2e/scenarios.yml`, implémenté dans weda2 :
      « le délégant voit, dans son journal, les actes faits dans sa BAL par son délégataire ».
      - Clients : `mobile: non-applicable — l'application mobile n'a pas d'écran de journal
        d'audit`, `angular: requis`.
      - Le filtre par défaut de l'écran est « aujourd'hui ».
- [ ] Aucun **nom ni RPPS de la personne qui agit** dans les journaux applicatifs du **nouveau**
      code. Les noms de base `u_<RPPS>_…` et les journaux existants de RPPS sont hors de cette
      task.
- [ ] Build et tests verts : dtos-mss, api-mail, client-angular ; `/e2e` vert, avec parité verte.

## Manual Test Plan

Comptes de formation : Cyril, délégataire de Virginie.

1. Se connecter en **Cyril** sur weda2 par PSC. Dans la boîte déléguée de Virginie, ouvrir un
   message, puis en supprimer un autre.
2. Ouvrir l'écran Audit de Cyril : ses deux actes figurent, « dans la BAL de
   virginie.medecinrpps0062267@… », sans objet ni données patient.
3. Se connecter en **Virginie** sur weda2. Écran Audit, filtre « actes de mes délégataires » :
   - les deux actes de Cyril, « par *prénom nom* (RPPS 899700723440), délégation » ;
   - le dossier est affiché comme le sien (« Boîte de réception », sans `shared/…`) ;
   - le détail ne montre ni l'adresse IP, ni le navigateur, ni la session de Cyril.
4. Sans filtre, les actes de Cyril sont mêlés aux siens dans l'ordre chronologique. Un message lu
   par les deux montre les **deux** actes.
5. Exporter en CSV : la personne et la BAL propriétaire y figurent, sans objet ni destinataires pour
   les actes délégués.
6. Virginie retire la délégation dans le webmail Mailiz : son journal montre toujours les actes
   passés de Cyril.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — fonctionnalité Mailiz sans exigence DSR publiée
- **Exigences DSR honorées** : non applicable. La PGSSI-S (imputabilité, journalisation) est suivie.
- **INS** : non applicable — jamais dans une trace déléguée (règle 14)
- **Authentification PS** : inchangée. RPPS issu de la session PSC / e-CPS, nom issu de `userinfo`
  du proxy.
- **Habilitations** : lecture du journal limitée par la sécurité par ligne :
  - le délégataire voit ses propres actes ;
  - le délégant voit les actes délégués faits dans sa BAL ;
  - personne d'autre ne voit rien.

  Les données de session et de poste du délégataire ne sont pas montrées au délégant.
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : **objet de la task** — imputabilité explicite, BAL identifiée, conservation de
  10 ans
- **Consentement patient** : non applicable
- **Référentiels métier** : RPPS
- **Hébergement HDS** : oui — registre commun
- **AIPD / impact RGPD** : **à mettre à jour**.
  - Donnée personnelle nouvelle dans le journal : RPPS et nom de la personne qui agit, sur une base
    légale d'obligation de traçabilité.
  - Communiquée au délégant.
  - Conservation 10 ans.
  - Les données de session du délégataire ne sont pas communiquées.

## Notes de cadrage

- **Constats et lignes** : revue, §3.4.
- **Lieux à modifier** :
  - estampillage : `AuditService.cs:61-105` ;
  - persistance : `PostgresAuditSink.cs:59-66`, `AuditBackgroundService.ToRecord` (`:315-357`) ;
  - lecture : `PostgresAuditReader.cs:156-171` (portée), `:208-244` (filtres), `:247-280` (mapping) ;
  - migrations du registre : `Infrastructure/Migrations/TenantDb/`, la plus récente étant
    `20260915090000_DropAuditCutoverMarks.cs` ; noms partagés dans `AuditJournalSchema.cs` ;
  - appel au proxy : sur le modèle de `PscTokenProvider` (cookie `proxy_session_id`, clé interne).
- **Hors périmètre** :
  - écran de journal sur le mobile ;
  - notification au délégant à chaque acte ;
  - accès d'administration et de sécurité au journal (task-302) ;
  - reprise des traces passées.

## Branches
- `api-mail` (pushed) : feat/task-400-delegation-tracer-ce-qui-agit — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-400-delegation-tracer-ce-qui-agit
- `dtos-mss` (lazy) : aucune branche au /start — `/develop` la crée depuis `origin/develop` au premier contrat touché (règle du 2026-09-16)
- `client-angular` (code-only) : la forge écrit sur la branche courante de `Client/Angular/` — `feature/nova-mss-weda-integration` au /start (2026-10-27). L'arbre porte déjà, non commitées, les retouches weda2 du 2026-10-27 (bordure des dossiers délégués, alignement, quota déplacé dans les Paramètres) : humain gère branche, commit, push, PR TFS
