# todo-task-408 — Annuaire : source FHIR ou LDAP choisie dans appsettings.json

**Repos**: api-mail, client-mobile, client-angular
**Dependencies**: task-402 (« Mes boîtes » et le rôle décidé par l'Annuaire Santé)
**Epic**: E020

> **Fronts : indication d'attente seulement.** « Mes boîtes », le rattachement et la requalification
> gardent leur parcours et leur contrat. Le backend change **la source** qui publie les BAL d'un
> RPPS. Les deux fronts montrent un indicateur d'attente partout où l'annuaire peut faire attendre le
> médecin (décision humaine n°5).

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

   La source n'est **jamais** déduite de l'environnement par le code : ce sont les fichiers de
   configuration qui la déclarent.
4. **La configuration est injectée dans les fichiers `appsettings`** (humain, 2026-10-29) :
   - `appsettings.json` porte les **deux** sections complètes, avec leurs valeurs réelles. FHIR garde
     son adresse actuelle. LDAP reçoit `partenaires.annuaire.sante.fr`, port `389`, base DN
     `ou=bal,o=mssante,c=fr` ;
   - `appsettings.json` active `Fhir`. La production et tous les environnements déployés gardent
     ainsi la passerelle de production, sauf surcharge explicite ;
   - un `appsettings.Development.json` active `Ldap` sur le poste local. Le poste local se lance en
     `Development`.
5. **Un spinner d'attente pendant le rattachement** (humain, 2026-10-29), parce que l'appel LDAP peut
   durer. État constaté sur le formulaire de rattachement (`attach-mailbox-form`) :
   - **mobile** : la lecture de « Mes boîtes » a un spinner ; le clic sur « Rattacher » ne fait que
     désactiver les boutons, **sans spinner** ;
   - **weda2** : la lecture de « Mes boîtes » n'affiche qu'un texte, **sans spinner** ; le clic sur
     « Rattacher » a déjà son spinner dans le bouton.
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
     inchangé partout. Il porte aussi la section LDAP remplie (décision 4).
   - Le poste local passe à `Ldap` par `appsettings.Development.json`, et weda-dev par sa
     configmap (`devops`, à la main).
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
7. **Attente visible, sur mobile et sur weda2** :
   - **lecture de « Mes boîtes »** : spinner avec le texte « Lecture de l'Annuaire Santé… », jusqu'à
     la liste, la liste vide ou le message « Annuaire Santé momentanément indisponible, réessayez » ;
   - **rattachement** (« Rattacher » d'une BAL de la liste, ou de la BAL déléguée saisie) : spinner
     dans le bouton cliqué ; toutes les actions du formulaire restent désactivées jusqu'à la réponse,
     ce qui empêche un double rattachement ;
   - **l'attente est bornée** : le délai de la source, configuré dans `appsettings.json`, termine
     toujours le spinner, sur la liste ou sur le message d'indisponibilité. Il ne tourne jamais sans
     fin.

## Hors périmètre

- **BAL organisationnelles par structure.** Dans l'annuaire LDAP, une BAL ORG est rattachée à une
  structure, pas au RPPS d'un membre. Avec la source LDAP, une carte de test ne trouve donc que les
  BAL qui portent son `psidnat`, en pratique sa BAL personnelle.
  - Pour un membre de BAL organisationnelle de test, la voie reste la délégation, par saisie libre.
  - À rouvrir si le besoin de tester la voie « membre » sur cartes de test apparaît.
- **Ouverture du port 389 sortant depuis weda-dev et configuration de weda-dev** : dépôt `devops`,
  géré à la main par l'humain.

## Definition of Done

- [ ] Build passes (0 errors) sur `api-mail`, `client-mobile`, `client-angular` (code-only)
- [ ] Tests pass (0 failures) sur chaque repo listé
- [ ] UI component tests du formulaire de rattachement, mobile et weda2 :
      - spinner et texte pendant la lecture de « Mes boîtes », remplacés par la liste ou par le
        message d'indisponibilité ;
      - spinner dans le bouton cliqué pendant le rattachement, actions désactivées, rien après la
        réponse (succès ou erreur) ;
      - un second clic pendant l'attente n'envoie pas de second rattachement.
- [ ] `data-testid` sur chaque spinner (`attach-mailbox-directory-loading` conservé,
      `attach-mailbox-submitting` ajouté)
- [ ] Aucun scénario e2e versionné : les étapes et l'issue des parcours E2E-MAILBOX-00x ne changent
      pas. L'état d'attente, transitoire, est prouvé par les tests de composant. `/e2e` rejoue les
      parcours existants.
- [ ] `appsettings.json` porte la clé de source **explicitement** à `Fhir`, et la section LDAP
      remplie : hôte `partenaires.annuaire.sante.fr`, port `389`, base DN `ou=bal,o=mssante,c=fr`,
      délai. Aucune configuration existante n'est modifiée par effet de bord
- [ ] `appsettings.Development.json` créé : il active `Ldap` et ne surcharge que la source
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

- Poste local : rien à saisir. `appsettings.Development.json` active `Ldap`, et `appsettings.json`
  porte les adresses de l'annuaire « partenaires ».
- Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost` ; puis
  `cd Client/Mobile && npm start`.
- Se connecter par Pro Santé Connect avec la carte de test du RPPS 899700622675.
- Ouvrir « Mes boîtes » : un spinner « Lecture de l'Annuaire Santé… » s'affiche, puis
  `virginie.medecinrpps0062267@medecin.formation.mssante.fr` est proposée. Cliquer « Rattacher » :
  un spinner apparaît dans le bouton, les autres actions sont désactivées, puis le rôle affiché est
  **titulaire**. Refaire le parcours dans weda2, avec les mêmes attentes.
- Ralentir l'annuaire, par exemple avec un hôte LDAP injoignable dans `appsettings.Development.json` :
  le spinner tourne pendant le délai configuré, puis « Annuaire Santé momentanément indisponible,
  réessayez » s'affiche.
- Dans le journal de la boîte : le rattachement est imputé à la personne de la carte de test.
- Remettre la source à `Fhir` dans `appsettings.Development.json` et relancer : « Mes boîtes » interroge de nouveau la passerelle de
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

## Branches

- `api-mail` (pushed) : feat/task-408-annuaire-source-fhir-ou-ldap-choisie — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-408-annuaire-source-fhir-ou-ldap-choisie
- `client-mobile` (pushed) : feat/task-408-annuaire-source-fhir-ou-ldap-choisie — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-408-annuaire-source-fhir-ou-ldap-choisie
- `client-angular` (code-only) : la forge écrit sur la branche checkout dans `Client/Angular/` (au /start : `feature/nova-mss-weda-integration`) — humain gère branche, commit, push, PR TFS

## Timings

*(généré par `tools/timing/report.sh --task task-408 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 10 s | — | — | — | — |
| /develop | ok | 21 min 03 s | 6 (1 min 10 s) | 5 (5 min 46 s) | — | api-mail 4B/1T, client-mobile 1B/1T, client-angular 1B/3T |
| /sonar | ok | 9 min 10 s | 1 (18 s) | 5 (6 min 56 s) | 2 (40 s) | 1 itération(s), api-mail 1B/5T |
| /lint-angular | ok | 4 min 16 s | 1 (19 s) | 1 (1 min 39 s) | — | 1 itération(s), client-angular 1B/1T |
| **Total cycle** | | **34 min 40 s** | **8 (1 min 48 s)** | **11 (14 min 22 s)** | **2 (40 s)** | |

Autres commandes mesurées : lint ×2 (42 s)

## Develop log

- **Repos touchés** : `api-mail`, `client-mobile`, `client-angular` (code-only). Aucun DTO ni interop changé.
- **Commits** :
  - api-mail : `89837885` feat(annuaire) source FHIR ou LDAP ; `7c9797ec` test(annuaire) source LDAP sur un vrai OpenLDAP ;
  - client-mobile : `0b8b98b` feat(mobile) attente visible au rattachement ;
  - client-angular (weda2) : non commité sur `feature/nova-mss-weda-integration`, fichiers
    `libs/mss/src/ui/attach-mailbox-form/attach-mailbox-form.component.{html,scss,spec.ts,ts}`.
- **Ce qui est livré (api-mail)** :
  - `AnnuaireOptions` (section `Annuaire`) : `Source` = `Fhir` | `Ldap`, et `Ldap` (hôte, port, base DN, délai, taille).
    `AnnuaireOptionsValidator` + `ValidateOnStart` refusent le démarrage sur une source absente ou inconnue, ou sur
    une section LDAP incomplète, avec la clé dans le message ;
  - `LdapAnnuaireSanteService` : décorateur qui ne remplace que `GetPractitionerMailboxesAsync`. La recherche, les
    spécialités et les professions restent sur la passerelle FHIR (décision n°2). Lecture anonyme bornée en
    durée et en taille, filtre `(psidnat=8{RPPS})` échappé (RFC 4515, `LdapFilters`). Injoignable → la même
    `UnavailableException` `DIRECTORY_UNAVAILABLE` que FHIR. Un évènement de journal par lecture, sans RPPS ;
  - `DirectoryMailboxes` : la traduction PER / ORG / CAB / APP / absent et la règle « une adresse vue deux fois
    reste personnelle », **un seul code** pour FHIR (`FhirBundleParser`) et LDAP ;
  - `AnnuaireSourceStartupLogger` : la source active et son adresse sont journalisées au démarrage ;
  - `appsettings.json` : `Annuaire:Source = Fhir` explicite, section LDAP remplie
    (`partenaires.annuaire.sante.fr`, 389, `ou=bal,o=mssante,c=fr`, 10 s, 50) ;
  - bibliothèque **Novell.Directory.Ldap.NETStandard 4.0.0**, entièrement managée : aucune `libldap` native à
    installer dans l'image Docker (System.DirectoryServices.Protocols l'aurait exigée sous Linux).
- ⚠️ **Écart à la décision n°4, à arbitrer** : `appsettings.Development.json` **n'est pas versionnable**. Le
  `.gitignore` d'api-mail l'exclut (task-045 : « secrets stay local, never commit this file »). Pour garder
  l'intention (le poste local lit l'annuaire de test, activation explicite et versionnée), c'est l'**AppHost**
  qui pose `Annuaire__Source=Ldap` pour le poste local ; les profils `e2e` et `loadtest` reposent `Fhir`.
  Les adresses LDAP restent dans `appsettings.json`. Si tu préfères un fichier d'appsettings dédié, il faut
  lever l'exclusion de task-045 ou choisir un autre nom de fichier chargé explicitement.
- **Vérifié contre le vrai annuaire « partenaires »** (lecture anonyme, même appel Novell que la production) :
  RPPS 899700622675 → `virginie.medecinrpps0062267@medecin.formation.mssante.fr`, `typeBal: PER`. Le serveur
  rend `typeBal` en casse mixte ; le jeu d'attributs Novell est insensible à la casse (contrôlé).
- **Tests** :
  - unitaires (`LdapDirectorySourceTests`, 26) : validation de la configuration (chaque clé), filtre et échappement,
    traduction du type, déduplication, délégation à FHIR, LDAP injoignable → `DIRECTORY_UNAVAILABLE` ;
  - intégration sur un **vrai OpenLDAP** en conteneur (`OpenLdapFixture`, schéma `psidnat`/`typebal`, lecture
    anonyme), dans `MailboxAttachRoleIntegrationTests` (pile réelle : HTTP, middleware, RFC 7807, registre
    PostgreSQL, journal d'audit) :
    - `Directory_LdapSource_…` : BAL PER et ORG (type absent) du RPPS de session lues dans la réponse, ni l'APP ni
      la BAL d'un autre RPPS ;
    - `Directory_LdapUnreachable_…` : 503 problem+json `DIRECTORY_UNAVAILABLE` ;
    - `AttachFromDirectory_LdapSource_…` : rôle **Holder** relu dans la liste du compte, trace
      `mailbox-attach mode=Directory role=Holder actor-rpps=…` ;
    - `Start_WithoutADeclaredSource_…` : démarrage refusé, message nommant `Annuaire:Source` ;
  - source `Fhir` : tous les tests existants restent verts, harnais seulement complétés de `Source = Fhir`.
- **Règle 1b — mutations vues rouges** :

  | # | Mutation | Test rouge |
  |---|---|---|
  | M1 | la source LDAP est ignorée (FHIR toujours) | `Directory_LdapSource_…`, `AttachFromDirectory_LdapSource_…` |
  | M2 | la BAL `APP` n'est plus écartée | `Directory_LdapSource_…` (collections différentes) |
  | M3 | l'erreur LDAP n'est plus traduite en indisponibilité | `Directory_LdapUnreachable_…` (500 au lieu de 503) |
  | M4 | une source absente est acceptée | `Start_WithoutADeclaredSource_…` (aucune exception) |

- **Fronts — attente visible** (mobile et weda2, `attach-mailbox-form`) :
  - lecture de « Mes boîtes » : spinner + « Lecture de l'Annuaire Santé… » (`attach-mailbox-directory-loading`
    conservé) ;
  - rattachement : spinner dans le **seul** bouton cliqué (`attach-mailbox-submitting` sur mobile, `aria-busy` du
    `ds-button` sur weda2), toutes les actions désactivées, garde contre le second clic ;
  - weda2 affichait jusqu'ici le spinner sur **tous** les boutons « Rattacher » à la fois : corrigé ;
  - tests de composant : mobile 5, weda2 5 (lecture, indisponibilité, bouton cliqué, saisie déléguée, double clic).
- **Validation locale** :
  - api-mail : build OK ; tests domain 202, infrastructure 699, api 1 306, application 3 865, integration 1 059 (16 ignorés) — 0 échec ;
  - client-mobile : build OK ; 1 348 / 1 348. Un premier passage avait 7 échecs sans lien (HtmlEditorComponent…)
    sous la charge CPU de la suite .NET lancée en parallèle ; second passage vert ;
  - client-angular : `nx build weda2` OK ; `npm test` vert (mss-lib 1 374 dont 5 nouveaux, weda2 3 301, …).
- **Passe qualité** : relecture du diff selon les axes de `/simplify` (réutilisation, simplification, efficacité,
  niveau d'abstraction) sur api-mail, mobile et weda2 : aucune simplification à appliquer. La traduction du type
  de BAL est déjà factorisée entre FHIR et LDAP. Contrôles mécaniques §Q 2b (S125, xUnit1045, S4457, xUnit2032) :
  aucun résultat.
- **Scénarios e2e** : aucun versionné (DoD) ; aucune spec e2e ne référence le balisage modifié.
- **DOD self-check** : 11 / 12 lignes vérifiées par commande ; la ligne `appsettings.Development.json` est remplacée
  par l'activation dans l'AppHost (écart ci-dessus, à arbitrer).
- **Next step** : `/sonar task-408`

## Sonar log

- Serveur 9.9.8.100196 (`sonar.login`), projet `healthplatform-api-mail`, branche `feat/task-408-…` (`7c9797ec`).
- **Phase 1 (new code)** : ✓ Quality Gate OK dès la première analyse, **0 issue**, 0 hotspot à revoir,
  new_coverage 96,9 % (cible 95 %). Aucune correction, aucun test ajouté.
  - Couverture des fichiers de la task : `AnnuaireOptions` 100 %, `DirectoryMailboxes` 100 %,
    `AnnuaireSourceStartupLogger` 92,3 %, `LdapAnnuaireSanteService` 92,6 %. Les lignes non couvertes sont
    l'abandon par le médecin (annulation de l'appelant) et la coupure sur dépassement de taille.
- **Phase 2 (legacy)** : 0 itération — le projet n'a ni bug, ni vulnérabilité, ni code smell ouvert.
- Build Release + 5 suites OpenCover : ✓ (domain 202, application 3 865, infrastructure 699, api 1 306,
  integration 1 059 / 16 ignorés).
- `conventions/csharp.md` : inchangé (aucune règle corrigée à la main).

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 96,8 % | 96,9 % | +0,1 pt |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 0 | 0 | 0 |
| Coverage (projet) | 98,0 % | 98,0 % | 0 |
| Duplication | 0,4 % | 0,4 % | 0 |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

## Lint log

- `client-angular` (code-only, branche `feature/nova-mss-weda-integration`), base `origin/next`, lint `tag:scope:mss`.
- **Baseline** : 1 erreur, 145 avertissements (tous antérieurs : `max-lines`, `jsdoc/require-example`).
  L'erreur était la nôtre : `prettier/prettier`, appel `attach(...)` trop long dans
  `attach-mailbox-form.component.ts`.
- **Itération 1** (`--fix`) : 0 erreur. Le fixer a aussi passé en `import type` deux imports Playwright de
  `e2e/mss-e2e/support/weda-host.ts` et `weda.ts` (code de l'humain, dans le périmètre MSS, sans effet à
  l'exécution) : laissés non commités, à relire avec le reste.
- **Build** (`nx affected -t build`) : `weda2` ✓ ; `mss:build:production` et `prescription:build:production` ✗ sur
  le budget de bundle initial (+264 ko, +1,01 Mo) — **préexistant**, sans lien avec la task (mémoire
  `angular-mss-build-production-rouge-preexistant`).
- **Tests** (`nx affected -t test`) : ✓ 12 projets.
- **Final** : 0 erreur, 144 avertissements (préexistants). Itérations : 1 / 5.
- `conventions/angular.md` : inchangé (correction faite par l'auto-fixer, gratuite).

## Lint mobile log

- `client-mobile`, branche `feat/task-408-annuaire-source-fhir-ou-ldap-choisie` (`0b8b98b`).
- **Baseline** : `All files pass linting` — 0 erreur, 0 avertissement. Aucune itération, aucun commit.
- Build / tests : inchangés depuis la validation de `/develop` (1 348 / 1 348), arbre identique, pas de rebuild.
