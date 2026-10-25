# todo-task-398.md — Délégation de BAL : les BAL déléguées, visibles et utilisables dans le mobile et weda2

**Repos**: dtos-mss, api-mail, client-mobile, client-angular
**Dependencies**: task-397 (lecture directe des BAL déléguées, règle 14, banc de délégation)
**Epic**: E009
**Priorité**: **2** — après la task-397, la BAL déléguée est sûre mais apparaît comme un dossier
racine nommé par une adresse. Ses Envoyés et sa Corbeille ressemblent à des dossiers ordinaires,
et rien ne dit au délégataire dans quelle BAL il agit.

> **Analyse** : [Docs/audits/delegation-bal-mailiz-analyse-20261025.md](../Docs/audits/delegation-bal-mailiz-analyse-20261025.md).
> **Règle 14** (CLAUDE.md) : rien d'une BAL déléguée n'est persisté chez le délégataire. Elle vaut
> pour toutes les routes et tous les écrans de cette task.

## Décisions actées (humain, 2026-10-25)

1. **Mobile et weda2**, avec la parité e2e.
2. **Libellé : l'adresse du délégant, seule.** Pas d'appel à l'annuaire.
3. **Jamais de déplacement entre BAL.** Les déplacements se font à l'intérieur d'une même BAL :
   propre à propre, ou déléguée A à déléguée A. L'API le refuse (posé par task-397). Les
   sélecteurs ne proposent que les dossiers de la BAL courante.
4. **Répondre, Répondre à tous et Transférer sont masqués** sur un message délégué jusqu'à la
   task-399 (envoi « de la part de »). Une réponse partirait sinon de la propre adresse du
   délégataire.
5. **Gestion seule** (task-397) : pas de « à intégrer », pas d'acquittement de biologie.

## Objective

Le délégataire voit les BAL qu'on lui délègue dans une section à part, avec des dossiers
reconnaissables : Réception, Envoyés, Brouillons, Spam, Corbeille. Il les parcourt et les gère en
sachant toujours dans quelle BAL il se trouve. Aucun geste ne peut faire sortir un message de la
BAL du délégant, et rien n'est conservé chez lui.

## Règles

- **Contrat** : un dossier porte son **propriétaire** (adresse du délégant, vide pour la propre
  BAL) et son **rôle** (réception, envoyés, brouillons, spam, corbeille, dossier personnel). Pour
  un dossier délégué, le rôle se déduit de sa position sous `shared/<adresse>/`, puisque Mailiz ne
  pose pas d'attribut SPECIAL-USE.
  - Le type actuel des dossiers personnels ne change pas, pour qu'aucune logique « première
    réception », « premiers Envoyés » ou « dossier système » ne bascule sur un dossier délégué.
- **Section « Boîtes déléguées »** :
  - placée sous les dossiers personnels, dans les deux clients, avec une entrée par délégant,
    libellée par son **adresse** ;
  - repliable, et repliée par défaut ;
  - en dessous : Réception, Envoyés, Brouillons, Spam, Corbeille, avec les icônes et libellés
    système des dossiers personnels, puis les sous-dossiers du délégant.
- **Contexte visible** :
  - le titre de la liste indique `<adresse> — <dossier>` ;
  - le détail d'un message délégué porte le bandeau « Boîte de `<adresse>` (délégation) ».
- **Actions sur les dossiers** :
  - pas de Renommer / Supprimer sur les dossiers système du délégant ;
  - sur ses sous-dossiers, création, renommage et suppression sont permis, comme dans Mailiz.
- **Actions sur les messages délégués** :
  - lire, marquer lu ou non lu, déplacer **dans la même BAL**, supprimer vers la corbeille du
    délégant ;
  - dans sa corbeille : **Restaurer**, vers la réception du délégant, et **Supprimer
    définitivement** ;
  - masqués : Répondre, Répondre à tous, Transférer, la proposition d'accusé de lecture,
    l'invitation « à intégrer », l'acquittement de biologie ;
  - le glisser-déposer (weda2) n'accepte que les dossiers de la même BAL.
- **Sélecteurs** : « Déplacer vers… » propose **tous les niveaux** de dossiers de la BAL courante,
  et non plus les seuls dossiers racine. Ce correctif vaut aussi pour la propre BAL.
- **Compteurs** :
  - non lus de chaque dossier délégué lus sur le serveur ;
  - cumul des non lus de la boîte déléguée affiché sur son entrée repliée ;
  - widgets du tableau de bord et « aujourd'hui » limités à la réception personnelle, inchangés.
- **Dossier d'ouverture** : un chemin `shared/…` n'est **jamais** proposé ni accepté. L'API refuse
  de l'enregistrer (règle 14).
- **Hors ligne** : la section n'apparaît pas.
- **Recherche** : dans une BAL déléguée, la recherche n'est pas disponible, et un message le dit.
- **Révocation** : si la BAL déléguée disparaît de la liste pendant que l'utilisateur y est, le
  message « Cette boîte ne vous est plus déléguée » s'affiche et l'on revient à la propre réception.
- **Règle 14 côté clients** : aucune donnée d'une BAL déléguée dans un stockage du navigateur ou
  de l'appareil (local, session, IndexedDB, préférences Capacitor).

## Definition of Done

- [ ] `dtos-mss` : le contrat de dossier porte le propriétaire et le rôle ; paquet publié, consommateurs
      .NET mis à jour ; types TypeScript des deux clients alignés.
- [ ] Test d'intégration de bout en bout pour la liste des dossiers (banc de délégation de task-397) :
      - les dossiers de `shared/<A>` sont renvoyés avec propriétaire = adresse de A et le bon rôle ;
      - les dossiers personnels de B sont renvoyés avec propriétaire vide et leur type inchangé.

      Lu dans la réponse réelle, vu rouge (règle 1b).
- [ ] Test d'intégration : enregistrer un dossier d'ouverture `shared/<A>/…` → **400**
      ProblemDetails, rien d'écrit.
- [ ] Test d'intégration « rien de persisté » (règle 14) rejoué sur chaque route nouvelle ou modifiée
      par cette task.
- [ ] Tests de composants, sur mobile et weda2 :
      - section « Boîtes déléguées » et libellés système ;
      - bandeau et titre ;
      - menus absents sur les dossiers système délégués ;
      - Répondre, Transférer, accusé de lecture, « à intégrer » et acquittement absents sur un
        message délégué ;
      - Restaurer et Supprimer définitivement dans la corbeille déléguée ;
      - sélecteur de déplacement limité à la BAL courante et ouvert à tous les niveaux ;
      - cumul des non lus ;
      - retour à la propre réception à la révocation.
- [ ] Contrôle : aucun accès à un stockage du navigateur ou de l'appareil avec une donnée de BAL
      déléguée, dans les deux clients (test ou revue outillée consignée).
- [ ] **Banc e2e** : le Dovecot e2e reçoit la délégation (espace `shared`, ACL, état lu propre à
      chacun), en reprenant la configuration du banc d'intégration de task-397.
- [ ] Scénarios E2E-DELEG-001 à 004 ajoutés dans `Api/Mail/e2e/scenarios.yml`, et implémentés dans
      chaque client où ils sont requis (mobile et angular) :
      - **E2E-DELEG-001** : voir la BAL déléguée dans sa section, ouvrir un compte rendu, lire le
        document décodé ;
      - **E2E-DELEG-002** : supprimer un message délégué → il est dans la corbeille de la BAL
        déléguée, pas dans la sienne ; le restaurer ;
      - **E2E-DELEG-003** : les dossiers système délégués n'ont ni Renommer ni Supprimer ; un
        message délégué n'a ni Répondre ni Transférer ; « Déplacer vers… » ne propose que la BAL
        déléguée ;
      - **E2E-DELEG-004** : la délégation est retirée pendant la consultation → message, puis
        retour à la propre réception.
- [ ] Build et tests verts sur les quatre dépôts ; `/e2e` vert, avec parité verte.

## Manual Test Plan

Comptes de formation : Cyril, délégataire de Virginie. Lancer l'AppHost, puis le mobile
(`cd Client/Mobile && npm start`) et weda2. Se connecter en Cyril par PSC.

1. Une section « Boîtes déléguées » contient la boîte de
   `virginie.medecinrpps0062267@medecin.formation.mssante.fr`, repliée, avec son nombre de non lus.
   La déplier : Réception, Envoyés, Brouillons, Spam, Corbeille avec leurs icônes, puis `Demo`.
2. Ouvrir Envoyés : le titre dit `<adresse> — Envoyés`. Ouvrir un message : le bandeau « Boîte de
   … (délégation) » est visible, sans Répondre ni Transférer.
3. Ouvrir un compte rendu de biologie : il est décodé, et aucune action « à intégrer » ni
   d'acquittement n'est proposée.
4. « Déplacer vers… » : seuls les dossiers de la boîte de Virginie sont proposés, sous-dossiers
   compris. Déplacer le message vers `Demo/Biologie2026` : il y est.
5. Supprimer un message : il est dans la Corbeille de la boîte de Virginie. Le restaurer : il
   revient dans sa Réception.
6. Appui long (mobile) ou menu (weda2) sur les Envoyés de Virginie : ni Renommer ni Supprimer. Sur
   `Demo` : les actions sont proposées.
7. Réglages : le dossier d'ouverture ne propose aucun dossier de la boîte déléguée.
8. Couper le réseau : la section disparaît.
9. Virginie retire la délégation dans le webmail Mailiz pendant que Cyril est dans sa boîte : au
   rafraîchissement, le message « Cette boîte ne vous est plus déléguée » s'affiche, puis le retour
   à sa propre réception.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — fonctionnalité Mailiz sans exigence DSR publiée
- **Exigences DSR honorées** : non applicable. Le mode opératoire Mailiz est suivi (mêmes droits sur
  les messages, gestion des délégations réservée au délégant). Le choix de la BAL est rendu visible,
  ce que Mailiz exige pour l'envoi « pour éviter les pertes de données de santé ou les erreurs de
  traitement ».
- **INS** : non applicable — lecture seule, rien n'est stocké (règle 14)
- **Authentification PS** : inchangée — PSC / e-CPS du délégataire
- **Habilitations** : droits tenus par les ACL Mailiz, lues en direct. L'interface retire les gestes
  réservés au délégant ou reportés à la task-399 : réponse, actes cliniques, dossiers système.
- **Interop CI-SIS** : non applicable — affichage des documents décodés par task-397
- **Tracé PGSSI-S** : inchangé — l'audit réduit de task-397 couvre les actes. L'imputabilité
  acteur / propriétaire relève de la task-400.
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé — rien d'une BAL déléguée n'est stocké
- **AIPD / impact RGPD** : couvert par la mise à jour demandée en task-397 (accès en lecture
  directe, sans copie)

## Notes de cadrage

- **Constats clients** (analyse, §3.2), à corriger ici :
  - la BAL déléguée apparaît en racine, sous son adresse, avec une icône générique ;
  - menus Renommer et Supprimer sur ses dossiers système ;
  - « Sent » détecté par sous-chaîne `includes('sent')` dans les deux clients (une adresse
    contenant « sent » ferait passer toute la réception pour des Envoyés) : le rôle du contrat
    remplace ces détections ;
  - sélecteurs de déplacement limités aux dossiers racine ;
  - réglage du dossier d'ouverture limité à la racine (mobile) ou à une liste figée (weda2).
- **Hors périmètre** : envoi « de la part de », brouillons délégués et accusés de lecture
  (task-399) ; traçabilité acteur / propriétaire (task-400) ; gestion des délégations (webmail
  Mailiz seul).
