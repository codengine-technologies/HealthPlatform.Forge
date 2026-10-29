# todo-task-409 — Rattachement : identité du praticien préremplie

**Repos**: api-mail, client-mobile, client-angular
**Dependencies**: task-408 (source FHIR ou LDAP ; cartes de test dans l'annuaire), task-405 (nom PSC enregistré sur le rattachement)
**Epic**: E020

> **Mise en service du médecin, de bout en bout.** Le serveur préremplit le registre, l'identité
> d'expéditeur et la signature. Sur mobile et sur weda2 :
> - la première boîte se rattache **en un geste** (décision 5) ;
> - le médecin **voit** ce qui a été prérempli (décision 6).
>
> Les médecins déjà en service en profitent à leur prochaine connexion (décision 7).

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
5. **Premier rattachement en un geste.** Sur l'écran d'accueil de la première boîte, toutes les BAL
   que l'annuaire publie sont **précochées**, et un seul bouton « Rattacher » les rattache. La
   personne choisit toujours (règle 14) : elle peut décocher, mais elle n'a plus à rattacher BAL par
   BAL. Pas de rattachement sans geste.
6. **Montrer ce qui a été prérempli.** Après le rattachement, l'écran de confirmation affiche :
   - « Vos destinataires vous verront ainsi : {nom affiché} » ;
   - l'aperçu de la signature ;
   - un lien « Modifier » vers chacun des deux réglages.
7. **Les médecins déjà en service en profitent.** À la prochaine connexion, une boîte déjà
   rattachée dont l'identité d'expéditeur est vide, ou dont la personne n'a aucune signature, est
   préremplie, **une seule fois**. Une signature que le médecin a supprimée volontairement ne
   revient pas.

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
     nom de la **personne qui rattache**, ou de la personne qui se connecte (règle 9) ;
   - ces actes suivent le rattachement ou la connexion, mais restent des actes de la personne, pas
     des actes système.
7. **Rattachement en un geste** (décision 5) :
   - **où** : écran d'accueil de la première boîte (mobile `mailbox-onboarding`, son équivalent
     weda2) ;
   - **précochage** : les BAL de « Mes boîtes » non encore rattachées ; une BAL applicative n'y
     figure jamais ;
   - **vérification** : chaque BAL cochée passe la sonde IMAP avec le jeton PSC de la personne,
     comme aujourd'hui ;
   - **échec partiel** : une BAL en échec n'empêche pas les autres. L'écran dit, pour chacune,
     « rattachée » ou la raison de l'échec (même libellé qu'aujourd'hui), et propose de réessayer
     celles en échec ;
   - le découpage en appels serveur relève du développement. Le rôle de chaque BAL reste décidé
     par l'annuaire ;
   - l'écran de gestion des boîtes garde le rattachement BAL par BAL.
8. **Écran de confirmation** (décision 6), après le rattachement en un geste et après tout
   rattachement depuis l'écran de gestion :
   - **titulaire, ou membre sans titulaire** : « Vos destinataires vous verront ainsi : {nom
     affiché} », c'est-à-dire le nom que produit l'identité d'expéditeur, avec « Modifier » vers ce
     réglage ;
   - **délégataire** : « Cette boîte écrit au nom de {nom affiché}, réglé par son titulaire », sans
     « Modifier » ;
   - **signature** : l'aperçu de la signature par défaut de la personne, avec « Modifier » vers
     les signatures ;
   - **rien de prérempli** (annuaire indisponible, liste rouge) : la confirmation le dit et propose
     de compléter les réglages ;
   - le contenu vient des réglages **réellement enregistrés**, relus après le rattachement, jamais
     d'une reconstruction côté client.
9. **Préremplissage des boîtes déjà rattachées** (décision 7) :
   - **quand** : à la requalification qui suit la connexion, pour chaque boîte rattachée de la
     personne ;
   - **règles** : les mêmes qu'au rattachement (règles 3 et 4), et seulement si c'est vide ;
   - **une fois** : le rattachement mémorise que le préremplissage a été fait, au rattachement ou à
     cette connexion. Il ne se refait jamais ensuite, même si le médecin vide son identité ou
     supprime toutes ses signatures ;
   - **best-effort** : un échec n'empêche jamais la connexion. Le préremplissage sera retenté à la
     connexion suivante tant qu'il n'a pas été fait.

## Definition of Done

- [ ] Build passes (0 errors) sur `api-mail`, `client-mobile`, `client-angular` (code-only)
- [ ] Tests pass (0 failures) sur chaque repo listé
- [ ] Migration du registre : civilité d'exercice, profession, spécialité, structure et marque « préremplissage fait » sur le
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
- [ ] Test d'intégration de bout en bout, boîte rattachée **avant** cette task (marque absente,
      identité vide, aucune signature) :
      - la connexion la préremplit et pose la marque ;
      - signatures supprimées puis nouvelle connexion → rien n'est recréé ;
      - annuaire injoignable → connexion réussie, marque absente, préremplissage retenté à la
        connexion suivante ;
      - vu rouge (règle 1b).
- [ ] Test d'intégration de bout en bout, rattachement de plusieurs BAL en un geste :
      - deux BAL publiées rattachées, chacune avec le rôle que décide l'annuaire ;
      - une BAL en échec de sonde n'empêche pas l'autre, et l'échec est lu dans la réponse ;
      - vu rouge (règle 1b).
- [ ] UI component tests, mobile et weda2 :
      - écran d'accueil : BAL précochées, décochage, un seul bouton, échec partiel avec « réessayer » ;
      - confirmation : nom affiché et aperçu de signature lus des réglages enregistrés, variantes
        délégataire et « rien de prérempli », liens « Modifier ».
- [ ] `data-testid` sur chaque case de BAL, le bouton unique, le nom affiché, l'aperçu de signature
      et les liens « Modifier »
- [ ] Faux annuaire e2e (`FakeAnnuaireServer`) : il publie civilité, profession, spécialité,
      structure et adresse pour les personas du seed
- [ ] Scénario **E2E-MAILBOX-003 v2** versionné dans Api/Mail/e2e/scenarios.yml, et implémenté dans
      chaque client où il est requis (mobile, angular) :
      - praticienne-nouvelle voit sa BAL personnelle et celle du cabinet précochées ;
      - un seul « Rattacher » les rattache, en titulaire et en membre ;
      - relus côté serveur : Holder et Member.
- [ ] Scénario **E2E-MAILBOX-006 v1** ajouté dans Api/Mail/e2e/scenarios.yml, et implémenté dans
      chaque client où il est requis (mobile, angular) :
      - après le rattachement, la confirmation montre « Vos destinataires vous verront ainsi : … »
        et l'aperçu de « Signature annuaire » ;
      - les paramètres et les signatures portent les mêmes valeurs.
- [ ] Aucune donnée de santé en clair dans les logs ; aucun RPPS en clair dans les logs du
      préremplissage
- [ ] Évènements PGSSI-S journalisés : identité d'expéditeur préremplie, signature créée, imputés à
      la personne qui rattache

## Manual Test Plan

- Poste local, source `Ldap` (task-408). Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`.
  Puis `cd Client/Mobile && npm start`, et weda2 via son hôte.
- Se connecter par Pro Santé Connect avec la carte de test du RPPS 899700622675, qui n'a encore
  aucune boîte rattachée.
- Écran d'accueil : `virginie.medecinrpps0062267@medecin.formation.mssante.fr` est déjà cochée.
  Un seul clic sur « Rattacher ».
- Confirmation : « Vos destinataires vous verront ainsi : … » avec le nom du Docteur Virginie
  MEDECIN RPPS0062267, l'aperçu de la signature et deux liens « Modifier ».
- Paramètres → identité d'expéditeur : « Docteur », « Virginie », « MEDECIN RPPS0062267 », sans
  rien avoir saisi.
- Signatures : « Signature annuaire », par défaut, avec les cinq lignes de la décision 3. Écrire un
  message : la signature est insérée.
- Modifier l'identité et la signature, se déconnecter, se reconnecter (requalification) : les
  modifications sont conservées.
- Journal de la boîte : préremplissage et création de signature imputés à la personne de la carte.
- Médecin déjà en service : sur une boîte rattachée avant la task, vider l'identité d'expéditeur et
  supprimer les signatures **en base**, pour simuler l'état d'avant. Se reconnecter : identité et
  signature préremplies. Supprimer la signature, se reconnecter : elle ne revient pas.

## Hors périmètre (proposé, non retenu pour cette task)

- Lecture de l'annuaire anticipée dès la connexion PSC, mise en cache pour la session, et liste en
  squelette au lieu du spinner.
- Proposition de mettre la signature à jour quand l'annuaire change, par exemple un changement de
  structure.
- Écran vide explicatif quand l'annuaire ne publie rien (liste rouge, carte absente de la source),
  avec accès direct à la saisie de l'adresse.

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

## Branches

> **Empilée sur task-408** (dépendance non encore mergée) : les branches api-mail et mobile partent de
> `feat/task-408-annuaire-source-fhir-ou-ldap-choisie`, comme 404 sur 403. Merger task-408 d'abord.

- `api-mail` (pushed) : feat/task-409-rattachement-identite-du-praticien — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-409-rattachement-identite-du-praticien
- `client-mobile` (pushed) : feat/task-409-rattachement-identite-du-praticien — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-409-rattachement-identite-du-praticien
- `client-angular` (code-only) : branche checkout au /start : `feature/nova-mss-weda-integration` — humain gère branche, commit, push, PR TFS
