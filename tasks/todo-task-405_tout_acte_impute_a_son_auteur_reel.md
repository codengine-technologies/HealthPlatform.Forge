# todo-task-405 — Tout acte est imputé à son auteur réel

**Repos**: dtos-mss, api-mail, client-angular, client-mobile
**Dependencies**: task-404 (la base partagée)
**Epic**: E020

> **Cadre** : CLAUDE.md règle 14, réécrite le 2026-10-28 — « tout acte est imputé à son auteur réel :
> règle d'or de la traçabilité ». Mots de l'humain : « tout, absolument tout doit être tracé par celui
> qui le fait. Si Cyril supprime un email de la BAL du titulaire, on écrit que Cyril a supprimé. » et
> « on doit savoir nominativement qui a fait quoi ».
>
> Reprend, sur le modèle « une base par boîte », l'objectif de la task-400 (abandonnée avec le
> retrait de `shared/`).

## Ce qui est établi

- **Qui, aujourd'hui** : `AuditService` écrit `UserId = _userContextInfo.Email` (`AuditService.cs:90`),
  c'est-à-dire l'**adresse de la boîte**, pas la personne. `TransportMssRpps` est le RPPS du
  rattachement. Aucun nom.
- **Lecture** : `audit_traces` sous RLS `tenant_id = mss.tenant_id`
  (`20260913120000_CreateTenantRegistry.cs:388-405`), `tenant_id` = rattachement (personne × boîte) :
  le titulaire ne voit pas les actes d'une autre personne sur sa boîte.
- **Nom** : la route `GET /v1/auth/userinfo` du proxy PSC rend prénom et nom ; api-mail appelle déjà
  le proxy avec le cookie de session et sa clé interne (`PscTokenProvider.cs:270-280`) — aucune
  évolution du proxy n'est requise (constat de la task-400).
- **Types d'actes** (`Dtos/AuditActionType.cs`, 41 membres) : connexions IMAP/SMTP, lecture, envoi,
  réponse, suppression, déplacement, drapeaux, brouillons, impression, exports, pièces jointes,
  acquittements biologie, rattachement / détachement de document patient, boîtes, refus de jeton.
  **Non tracés** : étiquettes, contacts et groupes, modèles, signatures, réglages, recherche,
  consultation d'une fiche patient, assistant IA.
- **Miroir TypeScript** : `AuditActionType` est un ordinal sur le fil, recopié à la main dans weda2 ;
  il a déjà divergé une fois.
- **weda2** (`libs/mss/src/features/audit`) : liste, filtres, détail, chronologie par `Message-ID`,
  export CSV. `PostgresAuditReader.ApplyFilters` ignore les filtres `ActionType` et `Search` envoyés.

## Décisions actées (humain, 2026-10-28)

1. **Tout acte** est tracé au nom de la personne qui le fait — jamais au nom de la boîte ni du
   titulaire.
2. **Nominatif** : la trace porte le **RPPS**, le **nom** et le **prénom** (quand ils sont
   disponibles) de la personne.
3. **Lecture** : toute personne rattachée à la boîte lit **tous** les actes de la boîte, **détails
   techniques compris** (adresse IP, navigateur, session, requête et réponse du serveur).
4. Conservation inchangée : 3 653 jours pour la famille `HealthDataAccess`.

## Objective

Sur une boîte où plusieurs personnes agissent, chaque acte est tracé **nominativement** au nom de
celui qui le fait : qui (RPPS, nom, prénom, rôle), quand, quoi, sur quel objet, dans quelle boîte.
Toute personne rattachée lit tout le journal de la boîte.

## Règles

1. **Qui.** La trace porte la personne réelle :
   - son compte (`sub` Keycloak) ;
   - son **RPPS**, son **nom** et son **prénom** — RPPS du jeton PSC, nom et prénom de la route
     `userinfo` du proxy, lus une fois par session ;
   - son **rôle** (titulaire, membre, délégataire — task-402).

   Le titulaire **hors ligne** (sans session PSC) est imputé avec le RPPS, le nom et le prénom
   **enregistrés à son rattachement**. Nom ou prénom indisponibles : le champ est vide, le RPPS
   suffit à l'imputation. Un acte sans personne (tâche de fond, consommateur du bus, purge) est tracé
   **acte système**, explicitement. La boîte n'est jamais l'auteur.
2. **Quoi : tout.** Toute route qui lit une donnée de santé ou modifie quoi que ce soit dans une
   boîte émet une trace.
   - Nouveaux types d'actes : étiquette posée / retirée, contact et groupe (création, modification,
     suppression), modèle, signature, réglage, recherche, consultation d'une fiche patient, question
     à l'assistant IA.
   - Un **test d'architecture** échoue si une action de contrôleur n'est ni tracée, ni explicitement
     exemptée avec sa raison (santé du service, référentiels publics…). La règle « tout » est tenue
     par le code, pas par la relecture.
3. **Quand et où** : horodatage serveur, boîte, objet de l'acte — UID et `Message-ID`, document,
   patient (identifiant interne ; l'INS reste dans le journal d'audit en base, **jamais** dans les
   journaux applicatifs).
4. **Lecture** : toute personne rattachée à la boîte lit **tous** les actes de la boîte, détails
   techniques compris. Le cloisonnement passe du rattachement à la **boîte**, toujours par RLS, avec
   un réglage de session posé **côté serveur**. Un tiers non rattaché ne lit rien.
5. **Filtres** : `ActionType` et `Search` sont appliqués côté serveur ; un filtre **par personne**
   s'y ajoute.
6. **Sur l'objet** : là où l'écran montre déjà un auteur, il montre la **personne réelle** —
   acquittement de biologie, rattachement de document patient (« Acquitté par Dr Prénom Nom,
   délégataire, le … »). Les autres actes se lisent dans le journal.
7. **`AuditActionType`** : chaque nouveau membre a une **valeur explicite**, reportée à la main dans
   le miroir TypeScript de weda2.

## Definition of Done

- [ ] Build passes (0 errors) sur `dtos-mss`, `api-mail`, `client-angular` (code-only), `client-mobile`
- [ ] Tests pass (0 failures) sur chaque repo listé
- [ ] Contrat `dtos-mss` : nouveaux types d'actes à valeurs explicites ; trace et DTO portant compte,
      RPPS, nom, prénom, rôle, acte système — package publié, consommateurs .NET bumpés, miroir
      TypeScript weda2 et types mobile mis à jour
- [ ] Migration `audit_traces` (colonnes de la personne et de la boîte) et politique RLS par boîte,
      auditées (règle 7c)
- [ ] Test d'architecture « toute action de contrôleur est tracée ou exemptée avec sa raison », vu
      rouge sur une action non tracée
- [ ] Test d'intégration de bout en bout : le délégataire supprime un message de la boîte du
      titulaire → la trace lue par le **titulaire** dans `GET /audit/traces` porte le RPPS, le nom, le
      prénom et le rôle du délégataire, et ses détails techniques — vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout : un tiers non rattaché ne lit aucune trace de la boîte
      (liste vide, 404 sur le détail) — vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout : chaque nouveau type d'acte lu dans le journal réel après
      sa route (étiquette, contact, groupe, modèle, signature, réglage, recherche, fiche patient,
      assistant IA) — vu rouge (règle 1b)
- [ ] Test d'intégration : acte d'un consommateur du bus → trace « système », sans personne — vu
      rouge (règle 1b)
- [ ] Test d'intégration : titulaire hors ligne → trace avec RPPS, nom et prénom enregistrés — vu
      rouge (règle 1b)
- [ ] Test d'intégration de bout en bout : filtres `ActionType`, `Search` et par personne appliqués,
      lus dans la réponse réelle — vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout : acquittement par le délégataire → auteur réel (RPPS, nom,
      prénom, rôle) lu dans la réponse de la biologie côté titulaire — vu rouge (règle 1b)
- [ ] weda2 : écran Audit avec colonne « Qui » (Dr Prénom Nom, RPPS, rôle) et filtre par personne ;
      mobile et weda2 : auteur réel sur l'acquittement et le rattachement de document ;
      `data-testid` sur tous les éléments interactifs
- [ ] UI component tests : colonne « Qui », filtre par personne, auteur réel sur l'acquittement
- [ ] Scénario E2E-AUDIT-00N (v1 : le délégataire supprime un message ; le titulaire lit dans le
      journal « supprimé par Dr Prénom Nom, délégataire, RPPS … ») ajouté dans
      Api/Mail/e2e/scenarios.yml, et implémenté dans chaque client où il est requis (angular ; mobile
      non applicable — l'application mobile n'a pas d'écran Audit)
- [ ] Scénario de l'acquittement de biologie existant versionné (auteur réel affiché) dans
      Api/Mail/e2e/scenarios.yml, et implémenté dans chaque client où il est requis (mobile, angular)
- [ ] Aucune donnée de santé en clair dans les logs (INS, NIR, contenu CDA, contenu MSSanté) ; l'INS
      reste réservé au journal d'audit en base
- [ ] Évènements PGSSI-S journalisés : tous les actes, avec la personne (RPPS, nom, prénom), le rôle
      et la boîte

## Manual Test Plan

- Backend e2e : `cd Api/Mail && dotnet run --project src/AppHost` (profil `e2e`) ; mobile
  `cd Client/Mobile && npm start` ; weda2 via le faux hôte.
- Titulaire e2e et délégataire e2e sur `boite-praticien`.
- Le délégataire supprime un message, pose une étiquette, acquitte un résultat, crée un contact,
  pose une question à l'assistant IA.
- Le titulaire ouvre le journal dans weda2 : les cinq actes sont au nom du délégataire (Dr Prénom
  Nom, RPPS, délégataire), détails techniques visibles. Le filtre « par personne » ne garde que lui.
- Sur le résultat de biologie, côté titulaire (mobile et weda2) : « Acquitté par Dr Prénom Nom
  (délégataire) ».
- Une troisième identité non rattachée : journal vide.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur
- **Exigences DSR honorées** : à confirmer par l'humain — traçabilité et imputabilité (PGSSI-S,
  référentiel Imputabilité). La DoD n'en dépend pas
- **INS** : jamais dans les journaux applicatifs ; conservé dans le journal d'audit en base, comme
  aujourd'hui (arbitrage task-186)
- **Authentification PS** : PSC / e-CPS ; l'identité imputée vient du jeton PSC et de la route
  `userinfo` du proxy
- **Habilitations** : lecture du journal ouverte à toute personne rattachée à la boîte (task-402)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : tout acte — qui (RPPS, nom, prénom, rôle), quand, quoi, objet, boîte.
  Conservation inchangée (3 653 jours pour `HealthDataAccess`)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé
- **AIPD / impact RGPD** : à mettre à jour — les actes nominatifs d'un PS, détails techniques
  compris (adresse IP, navigateur), deviennent visibles des autres personnes de la boîte

## Branches

- `dtos-mss` (lazy) : aucune branche au /start — `/develop` la crée au premier contrat touché
- `client-angular` (code-only) : la forge écrit sur la branche courante de `Client/Angular/` ;
  l'humain gère branche, commit, push et PR TFS
