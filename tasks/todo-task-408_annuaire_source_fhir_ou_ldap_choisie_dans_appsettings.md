# todo-task-408 — Annuaire : source FHIR ou LDAP choisie dans appsettings.json

**Repos**: api-mail
**Dependencies**: task-402 (« Mes boîtes » et le rôle décidé par l'Annuaire Santé)
**Epic**: E020

> **Backend seul, justifié** : aucun écran ne change. « Mes boîtes », le rattachement et la
> requalification gardent leur parcours et leur contrat. Seule change **la source** qui publie les
> BAL d'un RPPS.

## Ce qui est établi (2026-10-29)

- **Les cartes de test ne sont pas dans la passerelle FHIR de production.** Toutes les configurations
  pointent sur `https://gateway.api.esante.gouv.fr/fhir/v2`. Le RPPS d'une carte de test n'y a
  aucune BAL : « Mes boîtes » est vide, et aucune carte de test ne peut devenir titulaire (règle 14).
- **Elles sont dans l'annuaire national MSSanté de test « partenaires ».**
  - Accès : `ldap://partenaires.annuaire.sante.fr:389`, base `ou=bal,o=mssante,c=fr`, connexion
    anonyme acceptée (sondé le 2026-10-29).
  - Exemple : RPPS 899700622675 → `virginie.medecinrpps0062267@medecin.formation.mssante.fr`,
    `typebal: PER`.
  - Attributs utiles :
    - `psidnat` : « 8 » + RPPS, l'identifiant national ;
    - `typebal` : PER / ORG / APP, les codes TRE_R257 que `FhirBundleParser` traduit déjà ;
    - `mail`.
- **Un seul point d'entrée** : `IAnnuaireSanteService.GetPractitionerMailboxesAsync(rpps)`. Il sert le
  rattachement en mode Directory, la liste « Mes boîtes » (`GET /account/mailboxes/directory`) et la
  requalification à chaque ré-authentification (`MailboxManagementService`).
- **Les environnements ne se distinguent pas par `ASPNETCORE_ENVIRONMENT`.** Tous les environnements
  déployés sont en « Staging », et le poste local est en « Development ».

## Décisions actées (humain, 2026-10-29)

1. **La source est activée explicitement dans `appsettings.json`** : FHIR ou LDAP, avec les adresses
   d'hôte de la source choisie.
   - FHIR : l'adresse de base, comme aujourd'hui.
   - LDAP : l'hôte, le port et la base DN.

   La source n'est **jamais** déduite de l'environnement.
2. **Périmètre : les BAL d'un RPPS seulement.** La recherche de destinataires, les spécialités et
   les professions restent servies par la passerelle FHIR, quelle que soit la source choisie.
3. **Pas de garde par domaine.** L'activation explicite est la seule barrière : une source LDAP rend
   les BAL que l'annuaire visé publie, quel que soit leur domaine.

## Objective

Un développeur ou un testeur qui se connecte avec une **carte de test** voit sa BAL de test dans
« Mes boîtes » et la rattache en **titulaire**, comme un médecin réel avec sa BAL de production.
C'est la configuration de l'environnement qui le permet, pas un faux annuaire.

## Règles

1. **Choix de la source** : une clé de configuration, valeur `Fhir` ou `Ldap`.
   - `appsettings.json` la porte **explicitement**, à `Fhir`, ce qui laisse le comportement actuel
     inchangé partout.
   - Le poste local et weda-dev passent à `Ldap` par leur configuration.
2. **Configuration invalide = démarrage refusé**, avec un message qui nomme la clé :
   - une valeur inconnue ;
   - `Ldap` sans hôte ou sans base DN ;
   - un port hors bornes.

   Il n'y a ni repli silencieux sur FHIR, ni valeur par défaut cachée.
3. **Source LDAP** : les BAL d'un RPPS sont les entrées dont `psidnat` vaut « 8 » + RPPS. Le
   développement vérifie la forme du RPPS reçu, aujourd'hui transmise à la passerelle FHIR, et
   normalise.
   - **Traduction du type, identique à la source FHIR** : `PER` → personnelle (titulaire) ; `ORG`
     et `CAB` → organisationnelle (membre) ; `APP` → écartée ; type absent → organisationnelle.
     **La traduction vit à un seul endroit, partagé par les deux sources.**
   - Une adresse vue deux fois suit la même règle que la source FHIR.
   - Connexion anonyme, en lecture seule. La recherche est bornée en taille et en durée.
4. **Annuaire LDAP injoignable ou en erreur** : même comportement, même problem+json et même trace
   que la passerelle FHIR indisponible aujourd'hui. Aucun rattachement, aucune requalification ne
   s'écrit.
5. **Le rôle et l'imputation sont inchangés** (règle 14). Le titulaire n'existe que par la liste de
   l'annuaire configuré. Le rattachement reste tracé au nom de la personne réelle (task-405).
6. **Le profil e2e est inchangé** : il garde son faux annuaire FHIR (`FakeAnnuaireServer`) et la source
   `Fhir`.

## Hors périmètre

- **BAL organisationnelles par structure.** Dans l'annuaire LDAP, une BAL ORG est rattachée à une
  structure, pas au RPPS d'un membre. Avec la source LDAP, une carte de test ne trouve donc que les
  BAL qui portent son `psidnat`, en pratique sa BAL personnelle.
  - Pour un membre de BAL organisationnelle de test, la voie reste la délégation, par saisie libre.
  - À rouvrir si le besoin de tester la voie « membre » sur cartes de test apparaît.
- **Ouverture du port 389 sortant depuis weda-dev et configuration de weda-dev** : dépôt `devops`,
  géré à la main par l'humain.

## Definition of Done

- [ ] Build passes (0 errors) sur `api-mail`
- [ ] Tests pass (0 failures) sur `api-mail`
- [ ] `appsettings.json` porte la clé de source **explicitement** à `Fhir` et une section LDAP
      (hôte, port, base DN, délai) ; aucune configuration existante n'est modifiée par effet de bord
- [ ] Unit tests de la validation au démarrage : valeur inconnue, `Ldap` sans hôte, `Ldap` sans base
      DN, port hors bornes → démarrage refusé, message nommant la clé ; `Fhir` et `Ldap` complets
      → acceptés
- [ ] Unit tests de la source LDAP :
      - `psidnat` = « 8 » + RPPS ;
      - traduction PER / ORG / CAB / APP / absent, la même que la source FHIR (un seul code) ;
      - adresse vue deux fois ;
      - aucune entrée → liste vide ;
      - échappement du RPPS dans le filtre LDAP (RFC 4515), y compris pour un RPPS malformé.
- [ ] Test d'intégration de bout en bout pour `GET /account/mailboxes/directory`, source `Ldap`, contre
      un vrai serveur LDAP de test (conteneur) peuplé d'entrées au format de l'annuaire
      « partenaires » :
      - la BAL `PER` du RPPS est lue dans la réponse réelle, en personnelle ;
      - la BAL `APP` et la BAL d'un autre RPPS n'y sont pas ;
      - LDAP injoignable → même problem+json que la passerelle FHIR indisponible ;
      - vu rouge (règle 1b).
- [ ] Test d'intégration de bout en bout pour `POST /account/mailboxes` en mode Directory, source
      `Ldap` :
      - le rattachement de la BAL `PER` fait un **titulaire** (rôle lu en base) ;
      - la trace du rattachement porte la personne réelle ;
      - vu rouge (règle 1b).
- [ ] Test d'intégration : source `Fhir`, comportement actuel inchangé (les tests existants restent
      verts sans modification)
- [ ] Aucune donnée de santé en clair dans les logs ; le RPPS n'apparaît pas en clair dans les logs
      de la source LDAP (même règle de masquage que la source FHIR)
- [ ] Évènements PGSSI-S journalisés : indisponibilité de l'annuaire (comme aujourd'hui) ; la source
      active est journalisée au démarrage

## Manual Test Plan

- Poste local, `Api/Mail/src/Api/appsettings.json` ou user-secrets : source = `Ldap`, hôte
  `partenaires.annuaire.sante.fr`, port `389`, base DN `ou=bal,o=mssante,c=fr`.
- Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost` ; puis
  `cd Client/Mobile && npm start`.
- Se connecter par Pro Santé Connect avec la carte de test du RPPS 899700622675.
- Ouvrir « Mes boîtes » : `virginie.medecinrpps0062267@medecin.formation.mssante.fr` est proposée.
  Rattacher : le rôle affiché est **titulaire**.
- Dans le journal de la boîte : le rattachement est imputé à la personne de la carte de test.
- Remettre la source à `Fhir` et relancer : « Mes boîtes » interroge de nouveau la passerelle de
  production (vide pour une carte de test).
- Mettre une valeur inconnue (`Ldp`) : le backend refuse de démarrer, et le message nomme la clé.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — outillage de test et de recette, aucune exigence DSR nouvelle
- **Exigences DSR honorées** : non applicable — la source de production reste la passerelle FHIR
  de l'Annuaire Santé
- **INS** : non applicable — aucune donnée patient manipulée
- **Authentification PS** : PSC / e-CPS, inchangée ; le RPPS vient du jeton PSC
- **Habilitations** : le rôle reste décidé par la liste de l'annuaire **configuré** (règle 14) ;
  activer l'annuaire de test en production ouvrirait le rôle de titulaire sur la base de données de
  test — la configuration est la barrière, décision humaine n°3
- **Interop CI-SIS** : non applicable ; annuaire MSSanté LDAP (schéma ANS, attributs `psidnat`,
  `typebal`, `mail`) et FHIR R4 Annuaire Santé, nomenclature TRE_R257 pour le type de BAL
- **MSSanté** : types d'adresse personnelle / organisationnelle / applicative ; une BAL en liste
  rouge n'est publiée ni par l'une ni par l'autre source (conséquence assumée de la règle 14)
- **Tracé PGSSI-S** : rattachement et requalification imputés comme aujourd'hui (task-402, task-405) ;
  indisponibilité de l'annuaire ; source active au démarrage. Conservation inchangée (3 653 jours
  pour `HealthDataAccess`)
- **Consentement patient** : non applicable
- **Référentiels métier** : TRE_R257 (type de BAL MSSanté)
- **Hébergement HDS** : inchangé — l'annuaire est une donnée publique, aucune donnée de santé
- **AIPD / impact RGPD** : inchangé — l'annuaire de test ne contient que des identités fictives ;
  en production, la source et les données lues sont celles d'aujourd'hui
