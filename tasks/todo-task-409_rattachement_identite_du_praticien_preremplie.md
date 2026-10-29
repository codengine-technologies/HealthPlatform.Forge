# todo-task-409 — Rattachement : identité du praticien préremplie

**Repos**: api-mail, client-mobile, client-angular
**Dependencies**: task-408 (source FHIR ou LDAP ; cartes de test dans l'annuaire), task-405 (nom PSC enregistré sur le rattachement)
**Epic**: E020

> **Fronts : scénario e2e seulement, a priori.** Les écrans des paramètres (identité
> d'expéditeur) et des signatures existent sur mobile et sur weda2 ; ils affichent ce que le serveur
> a prérempli. Les fronts portent le scénario E2E-MAILBOX-006, et tout écart d'affichage constaté.

## Ce qui est établi (2026-10-29)

- **Registre** : le rattachement enregistre déjà le prénom et le nom PSC de la personne
  (`person_first_name` / `person_last_name`, task-405). Il ne porte ni civilité, ni profession, ni
  spécialité, ni structure d'exercice.
- **Identité d'expéditeur** (`SenderIdentityDto` : type de boîte, civilité, prénom, nom,
  organisation) :
  - c'est une donnée de la **boîte** (task-404), qui fait le nom affiché du `From` ;
  - le titulaire la modifie ; sans titulaire rattaché, toute personne rattachée la modifie
    (`MailboxSenderIdentityService`) ;
  - un délégataire n'y touche jamais (task-407, décision 1).
- **Signatures** (`MailSignature`, `IsDefault`) : données de la **personne**, dans la base de la boîte
  (règle 14).
- **Ce que publie l'annuaire.**
  - LDAP « partenaires » : `civiliteexercice`, `givenname`, `sn`, `title` (profession et
    spécialité), `raisonsociale`, `postaladdress`, `mail`.
  - FHIR : `Practitioner` (préfixe, nom, prénom), `PractitionerRole` (profession, spécialité),
    l'organisation et son adresse.
  - Aujourd'hui, `GetPractitionerMailboxesAsync` ne rend que l'adresse et le type de chaque BAL.
- Aujourd'hui, après un rattachement, le médecin doit **saisir lui-même** son identité d'expéditeur
  et sa signature.

## Décisions actées (humain, 2026-10-29)

1. **Au rattachement, le registre reçoit l'identité du professionnel** : tout ce que l'annuaire
   publie.
2. **Les paramètres de la messagerie sont préremplis** : identité d'expéditeur (civilité, prénom,
   nom, organisation). Le médecin n'a pas à les saisir.
3. **Une signature par défaut est construite, en version complète**, si la personne n'en a encore
   aucune :

   ```
   Dr Virginie MEDECIN RPPS0062267
   Médecin — Qualifié MG
   CABINET MME MEDECIN0062267
   2 R DE CHATEAUDUN 75009 PARIS
   virginie.medecinrpps0062267@medecin.formation.mssante.fr
   ```

   Une ligne que l'annuaire ne publie pas est omise.
4. **Task à part** de task-408.

## Objective

Quand un médecin rattache une boîte, il la trouve **prête à l'emploi** :
- son nom apparaît correctement chez ses destinataires ;
- sa signature est déjà là.

Il n'a rien à saisir. Il garde la main pour corriger, et ce qu'il a corrigé n'est jamais écrasé.

## Règles

1. **Source de l'identité** : l'annuaire configuré (task-408, FHIR ou LDAP), interrogé par le
   **RPPS du jeton PSC**.
   - Un seul appel par rattachement, avec la liste des BAL quand le mode Directory la demande déjà.
   - Prénom et nom : ceux de PSC (task-405) font foi, ceux de l'annuaire servent de repli.
   - Civilité d'exercice, profession, spécialité, structure et adresse postale viennent de
     l'annuaire.
2. **Registre** : le rattachement enregistre la civilité d'exercice, la profession, la spécialité et
   la structure d'exercice.
   - Elles sont **rafraîchies à chaque requalification**, à la ré-authentification. L'annuaire fait
     foi.
   - Ce sont des données professionnelles publiques, pas des données de santé.
3. **Identité d'expéditeur de la boîte**, préremplie **seulement si elle est vide** :
   - **titulaire d'une BAL personnelle** : civilité, prénom, nom ; type « personnelle » ;
   - **membre d'une BAL organisationnelle sans titulaire** : organisation = la raison sociale que
     l'annuaire publie pour l'adresse, si elle est publiée ; type « organisationnelle » ;
   - **délégataire, ou boîte « à requalifier »** : **jamais**. L'identité de la boîte est celle du
     titulaire (task-404, task-407).
   - Une identité déjà renseignée, par le médecin ou par un rattachement précédent, n'est **jamais**
     écrasée, ni au rattachement, ni à la requalification.
4. **Signature par défaut**, créée **seulement si la personne n'a aucune signature** dans cette boîte :
   - nommée « Signature annuaire » et marquée par défaut ;
   - lignes de la décision 3 : civilité prénom NOM ; profession — spécialité ; structure ;
     adresse postale ; **adresse MSSanté de la boîte rattachée** ;
   - pour **tout rôle**, délégataire compris : la signature est celle de la personne, avec sa
     propre identité ;
   - chaque valeur est **échappée** dans le HTML de la signature ; aucun contenu de l'annuaire
     n'est interprété ;
   - une signature existante, même supprimée puis recréée par le médecin, n'est jamais remplacée.
5. **Best-effort, jamais bloquant** : annuaire injoignable, praticien absent ou en **liste rouge**,
   champs manquants → le rattachement **aboutit** quand même.
   - Le préremplissage se fait avec ce qui est disponible. À défaut, il se limite au prénom et au
     nom PSC.
   - En mode Directory, l'indisponibilité de l'annuaire bloque déjà le rattachement (task-402) :
     cette règle ne change rien à ce cas.
6. **Imputation (règle 14)** :
   - le préremplissage de l'identité d'expéditeur et la création de la signature sont tracés au
     nom de la **personne qui rattache** ;
   - ces actes suivent le rattachement, mais restent des actes de la personne, pas des actes
     système.

## Definition of Done

- [ ] Build passes (0 errors) sur `api-mail`, `client-mobile`, `client-angular` (code-only)
- [ ] Tests pass (0 failures) sur chaque repo listé
- [ ] Migration du registre : civilité d'exercice, profession, spécialité, structure sur le
      rattachement. Audit 7c : migration relue, `.Designer.cs` et snapshot présents, aucune
      opération fantôme, « has pending changes » vide
- [ ] Unit tests de la lecture d'identité, sources FHIR et LDAP : chaque champ présent ou absent,
      liste rouge (rien) → même identité commune aux deux sources
- [ ] Unit tests du préremplissage : chaque rôle (titulaire PER, membre ORG sans titulaire, membre ORG
      avec titulaire, délégataire, à requalifier) × identité vide / déjà renseignée
- [ ] Unit tests de la signature : lignes complètes, lignes omises, échappement HTML (valeur
      contenant `<script>` ou `&`), signature existante → aucune création
- [ ] Test d'intégration de bout en bout pour `POST /account/mailboxes`, mode Directory, titulaire d'une
      BAL personnelle :
      - le registre porte la civilité, la profession, la spécialité et la structure ;
      - `GET` des paramètres rend l'identité d'expéditeur préremplie ;
      - `GET` des signatures rend « Signature annuaire », par défaut, avec ses lignes ;
      - vu rouge (règle 1b).
- [ ] Test d'intégration de bout en bout :
      - identité d'expéditeur déjà renseignée et signature existante → rien d'écrasé, rien de créé ;
      - vu rouge (règle 1b).
- [ ] Test d'intégration de bout en bout, **deux personnes sur la même boîte** (règle 14) :
      - le délégataire rattache la boîte du titulaire ;
      - l'identité d'expéditeur de la boîte reste celle du titulaire ;
      - le délégataire obtient sa propre signature par défaut, à son nom ;
      - la signature du titulaire est inchangée ;
      - les traces portent la personne qui a rattaché ;
      - vu rouge (règle 1b).
- [ ] Test d'intégration de bout en bout : annuaire injoignable pendant une délégation → rattachement
      réussi, identité limitée au prénom et nom PSC — vu rouge (règle 1b)
- [ ] Test d'intégration : requalification → registre rafraîchi, identité d'expéditeur et signature
      inchangées
- [ ] Faux annuaire e2e (`FakeAnnuaireServer`) : il publie civilité, profession, spécialité,
      structure et adresse pour les personas du seed
- [ ] Scénario E2E-MAILBOX-006 (v1 : après le rattachement d'une boîte depuis « Mes boîtes », les
      paramètres montrent l'identité d'expéditeur préremplie et les signatures contiennent
      « Signature annuaire », par défaut) ajouté dans Api/Mail/e2e/scenarios.yml, et implémenté
      dans chaque client où il est requis (mobile, angular)
- [ ] Aucune donnée de santé en clair dans les logs ; aucun RPPS en clair dans les logs du
      préremplissage
- [ ] Évènements PGSSI-S journalisés : identité d'expéditeur préremplie, signature créée, imputés à
      la personne qui rattache

## Manual Test Plan

- Poste local, source `Ldap` (task-408). Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`.
  Puis `cd Client/Mobile && npm start`, et weda2 via son hôte.
- Se connecter par Pro Santé Connect avec la carte de test du RPPS 899700622675, qui n'a encore
  aucune boîte rattachée.
- « Mes boîtes » → rattacher `virginie.medecinrpps0062267@medecin.formation.mssante.fr`.
- Paramètres → identité d'expéditeur : « Docteur », « Virginie », « MEDECIN RPPS0062267 », sans
  rien avoir saisi.
- Signatures : « Signature annuaire », par défaut, avec les cinq lignes de la décision 3. Écrire un
  message : la signature est insérée.
- Modifier l'identité et la signature, se déconnecter, se reconnecter (requalification) : les
  modifications sont conservées.
- Journal de la boîte : préremplissage et création de signature imputés à la personne de la carte.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — confort de mise en service, aucune exigence DSR nouvelle
- **Exigences DSR honorées** : référentiel socle MSSanté #2 (clients) — nom affiché du `From`
  conforme à l'identité de la boîte (ECO.1.2.9, via task-404) ; non applicable au-delà
- **INS** : non applicable — aucune donnée patient manipulée
- **Authentification PS** : PSC / e-CPS ; l'identité est lue pour le RPPS du jeton PSC, jamais pour
  un RPPS saisi
- **Habilitations** : le rôle du rattachement (task-402) décide qui préremplit l'identité de la
  boîte ; un délégataire ne la modifie jamais
- **Interop CI-SIS** : non applicable ; Annuaire Santé FHIR R4 (Practitioner, PractitionerRole) ou
  annuaire MSSanté LDAP (task-408)
- **MSSanté** : BAL personnelle (identité du titulaire), organisationnelle (raison sociale), déléguée
  (identité de la boîte inchangée) ; liste rouge → rien depuis l'annuaire
- **Tracé PGSSI-S** : identité d'expéditeur préremplie et signature créée, imputées à la personne
  réelle. Conservation inchangée (3 653 jours pour `HealthDataAccess`)
- **Consentement patient** : non applicable
- **Référentiels métier** : TRE_R257 (type de BAL) ; profession et spécialité telles que publiées
  par l'annuaire (libellés, non recodés)
- **Hébergement HDS** : inchangé
- **AIPD / impact RGPD** : à compléter — le registre conserve en plus des données professionnelles
  publiques de l'Annuaire Santé (civilité, profession, spécialité, structure), le temps du
  rattachement ; source publique, finalité : préremplissage et affichage de l'auteur
