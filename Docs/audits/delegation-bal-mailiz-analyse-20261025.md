# Délégation de BAL Mailiz — analyse (2026-10-25)

> **Objet.** Mailiz (opérateur MSSanté de l'ANS) ouvre la **délégation de boîte aux lettres** : un
> professionnel (le *délégant*) donne à d'autres porteurs de RPPS (les *délégataires*) l'accès à sa
> BAL personnelle. Le serveur IMAP de formation l'expose déjà à notre application. Ce document
> rassemble :
> - ce que dit le mode opératoire Mailiz ;
> - ce que fait réellement le serveur ;
> - ce que fait aujourd'hui notre plateforme, avec les dégâts constatés ;
> - les décisions à prendre et un découpage en US.
>
> **Sources.**
> - *Mailiz – Mode opératoire Délégation de BAL – Novembre 2025 v1.0* (ANS), à la racine du plan de
>   contrôle.
> - Bases tenant de la délégante et du délégataire de formation, et journal d'audit `mss_registry`.
> - Lecture du code d'api-mail, du client mobile et de weda2 (module MSS).
>
> **Cas observé.** `cyril.toubib0072344@medecin.formation.mssante.fr` (base
> `u_899700723440_ctm_…`) est délégataire de la BAL de
> `virginie.medecinrpps0062267@medecin.formation.mssante.fr` (base `u_899700622675_vmm_…`). Cyril
> s'est connecté le 2026-10-25 à 10:10.

---

## 1. Les règles Mailiz (mode opératoire)

| Sujet | Règle |
|---|---|
| Qui délègue | Le titulaire d'une **BAL personnelle (PER)**. Il est propriétaire et **responsable** des accès ouverts, notamment du secret professionnel. |
| À qui | Un professionnel identifié par un **RPPS valide et actif**, avec ou sans BAL Mailiz. Les assistants et secrétaires médicaux en ont un via RPPS+. |
| Authentification du délégataire | **Pro Santé Connect**, avec une **e-CPS sur téléphone**. La CPE n'est pas acceptée. La délégation tient tant que le délégant ne la retire pas **et** que l'e-CPS du délégataire est valide. |
| Périmètre | **Toute** la BAL, sans délégation partielle d'un sous-dossier : réception, envoyés, brouillons, spam, corbeille, sous-dossiers. Le **carnet d'adresses n'est pas partagé**. |
| Plafond | **10 délégations** par BAL. |
| Droits du délégataire | **Les mêmes que le délégant sur les messages** : lire, gérer, supprimer, déplacer, créer et supprimer des sous-dossiers, **envoyer « de la part de »** le délégant. |
| Interdits au délégataire | Gérer les délégations, modifier les règles de messagerie, poser un message d'absence, changer les paramètres de la BAL. |
| Envoi | Le champ **De** porte **l'adresse du délégant**. Le libellé affiché est « *Nom du délégataire*, de la part de *adresse du délégant* ». Le message va dans les **Envoyés du délégant**, visible du délégant et des autres délégataires. |
| Plusieurs délégations | Le délégataire **choisit la BAL émettrice** à chaque message, « pour éviter les pertes de données de santé ou les erreurs de traitement ». |
| Gestion | Ajout et suppression par le délégant **seul**, depuis le webmail : Paramètres, puis Dossiers & Délégations. Une notification par mail part au délégant et à tous les délégataires. Certains comptes voient « *Vous n'êtes pas autorisé à créer de délégation. Merci de prendre contact avec l'éditeur du logiciel professionnel* ». L'ouverture sera généralisée « d'ici fin 2026 ». |
| Logiciels métier | « L'accès par un délégataire à une BAL déléguée n'est **actuellement possible que depuis le webmail** et pas encore depuis des logiciels métier. » |

Le dernier point est contredit dans les faits : le serveur IMAP expose **déjà** la BAL déléguée à
notre application (§2). Nous sommes donc concernés dès maintenant, sans contrat publié pour les
logiciels métier.

## 2. Ce que fait le serveur IMAP (constaté)

- **Espace de noms partagé.** La BAL de la délégante apparaît chez le délégataire sous
  `shared/<adresse du délégant>`, qui est sa boîte de réception. En dessous viennent `Sent`, `Drafts`,
  `Trash`, `Junk` et ses sous-dossiers (`Demo`, `Demo/Biologie2026`…). L'URL du webmail Mailiz le
  confirme : `_mbox=shared%2F<adresse>`. Le conteneur `shared` lui-même n'est pas sélectionnable.
- **Même boîte, pas une copie.** Les dossiers ont les mêmes `UidValidity` et `UidNext` côté
  délégante et côté délégataire (réception : 1735566573 / 4933).
- **Aucun attribut SPECIAL-USE** sur les dossiers partagés : `\Sent`, `\Trash`, `\Drafts` et
  `\Junk` sont absents. Notre code les classe donc tous en **type 7 (Custom)**.
- **État lu / non lu propre à chaque utilisateur.**

  | Dossier | Non lus côté Virginie | Non lus côté Cyril |
  |---|---|---|
  | Réception | 149 / 234 | 232 / 232 |
  | Envoyés | 0 / 83 | 83 / 83 |

  Lire un message en délégation ne le marque donc pas lu pour le délégant, et inversement.
  *Inféré des compteurs* : la configuration exacte du serveur, sans doute `INDEXPVT` de Dovecot,
  reste à confirmer.
- **Non vérifié** (aucun accès au serveur hors application) :
  - la réponse `NAMESPACE` ;
  - les droits ACL (`MYRIGHTS`) ;
  - le comportement SMTP quand un délégataire envoie avec `From` = délégant : acceptation, ajout
    d'un `Sender`, réécriture, classement dans les Envoyés du délégant.

## 3. Ce que fait notre plateforme aujourd'hui

**Aucune notion de délégation n'existe**, ni dans api-mail, ni dans les clients, ni dans les tests :
le Dovecot de test n'a qu'un espace de noms personnel. Les dossiers partagés remontent pour une
raison simple. La liste « espace personnel » d'api-mail est en réalité un `LIST "" "*"`, qui ramène
tout l'arbre. Ensuite, chaque règle traite ces dossiers comme ceux du délégataire.

### 3.1 Dégâts constatés sur le cas de formation (2026-10-25, entre 10:10 et 10:19)

| # | Constat | Preuve |
|---|---|---|
| D1 | **Une suppression par le délégataire fait sortir le message de la BAL du délégant.** Cyril a supprimé 2 messages de la réception de Virginie. Ils sont dans la **corbeille personnelle de Cyril**, pas dans celle de Virginie. | Audit `MailDelete` sur `shared/<V>`, UID 4617 et 4618. Corbeille de Cyril : UID 1 et 2, mêmes `Message-ID`. Réception de Virginie côté serveur passée de 234 à **232**, sa corbeille inchangée (38). |
| D2 | **La BAL du délégant est copiée et traitée dans la base du délégataire.** On y trouve 101 messages avec leur contenu, **64 documents médicaux** extraits, **106 étiquettes IA**, des embeddings et des contacts publiés au nom du délégataire. | Base de Cyril : `Mails`, `MailContents`, `MailMedicalDocuments` et `MailTags` sur `shared/%`. Audit : 103 `MailReceive` et 66 `MedicalDocumentProcess` sur des dossiers partagés. |
| D3 | **La liste de patients du délégataire contient ceux du délégant.** Les 7 patients de la base de Cyril viennent **tous** des documents de Virginie. Rien n'indique leur provenance. | `MailPatients` liés aux documents de `shared/%` : 7 sur 7. |
| D4 | **Les actions du délégataire sur la BAL du délégant ne sont tracées que chez le délégataire.** `user_id` est une adresse de BAL, pas une personne. Seul le chemin `shared/…` trahit l'acte en délégation. Le délégant ne voit rien. | `audit_traces` : `MailRead` et `MailDelete` de Cyril sur `shared/<V>`. |

> **Remédiation des 2 messages (D1).** Ils doivent revenir dans la réception de Virginie. Depuis
> le webmail Mailiz de Cyril : Corbeille, puis déplacer les deux messages du 2026-06-10 vers la boîte
> déléguée de Virginie. Rien n'est perdu : la corbeille de Cyril les garde.

### 3.2 Défauts par domaine (code)

**Gravité 1 — atteinte à la BAL du délégant**
- **Suppression vers la mauvaise corbeille** : D1. La corbeille est résolue par l'attribut
  `\Trash` de la session (`SpecialFolder.Trash`), donc celle du délégataire. Concerne
  `ImapService.cs:3814-3818`, `:3916`, `:4055`, `:4157`. Dans `shared/<adr>/Trash`, une
  « suppression définitive » **recopie** chez le délégataire au lieu de supprimer. La suppression
  d'un dossier fait de même (`ImapFolderService.cs:436`).
- **Les dossiers système du délégant ne sont pas protégés.** La garde `IsSystemFolder` repose sur
  le type, et sa réception, ses Envoyés, sa Corbeille, ses Brouillons et son Spam sont Custom. Les
  clients proposent donc **Renommer / Supprimer / Créer un sous-dossier** sur eux. Seules les ACL
  du serveur protègent encore.
- **Aucun contrôle des chemins.** Toutes les routes de déplacement, suppression, marquage et
  création acceptent n'importe quel chemin IMAP.

**Gravité 2 — données de santé et confidentialité**
- **D2 et D3** : extraction CDA, rattachement patient, étiquetage IA, embeddings, contacts et
  notifications ne filtrent pas les dossiers partagés.
  - L'ingestion passe par l'enrichissement à l'ouverture d'un dossier
    (`POST …/enrich/async` → `ImapService.EnrichEmailsAsync`).
  - La synchronisation en arrière-plan ne descend pas au-delà du premier niveau.
- **Logique de doublons, versions et suppressions inter-BAL** (`MailRepository.cs:4555-4611`,
  `:4733-4766`). Un même CDA présent dans les deux BAL peut masquer la copie du délégataire comme
  « doublon ». Une nouvelle version ou une demande de suppression dans la BAL du délégant peut
  remplacer ou signaler le document du délégataire.
- **Le Spam du délégant est traité comme du courrier reçu**, et ses sous-dossiers aussi.
- **Recherche sémantique globale** : elle inclut les messages délégués.
- **Révocation** : quand le délégant retire la délégation, les dossiers disparaissent et les
  messages sont purgés par cascade. Mais les patients créés, les contacts publiés et les étiquettes
  émises **restent** chez l'ex-délégataire.

**Gravité 2 — envoi « de la part de »**
- **Le `From` est pris tel quel du client**, sans contrôle (`SmtpService.cs:299-302`) :
  - le libellé est toujours l'identité du délégataire ;
  - il n'y a ni « de la part de » ni en-tête `Sender` ;
  - les deux clients forcent `From` = adresse de la session et n'offrent **aucun choix de BAL
    émettrice**.
- **Copie dans les Envoyés** : toujours dans les Envoyés **du délégataire**. Si Mailiz classe déjà
  l'envoi délégué chez le délégant, cela fait un doublon au mauvais endroit.
- **Brouillons** : ils vivent dans Redis, indexés et forcés sur l'adresse de session. Un brouillon
  « pour » le délégant est donc impossible, et `shared/<adr>/Drafts` s'affiche comme un dossier
  quelconque.
- **Accusés de lecture** : ils partiraient de l'adresse du délégataire.
- **Répondre à tous** garde le délégant parmi les destinataires.
- **La signature** et ses variables (`{{SenderName}}`, `{{SenderRPPS}}`) sont celles du délégataire.

**Gravité 3 — expérience**
- **Présentation** : la BAL déléguée apparaît comme un **dossier racine nommé par l'adresse**.
  - Il porte une icône de dossier générique et aucune mention « délégation ».
  - Il est replié par défaut sur mobile.
  - On voit deux « Sent » et deux « Trash », sans savoir à qui ils appartiennent.
- **Comportements d'un dossier quelconque** : pas de « Restaurer » ni de suppression définitive
  dans la corbeille déléguée, et pas de règles de glisser-déposer propres aux Envoyés et Brouillons
  (weda2).
- **Compteurs** : tableau de bord, widgets « aujourd'hui », étiquettes et alertes biologiques sont
  **limités à `INBOX`**. Le courrier délégué non lu n'est compté nulle part, et aucun cumul ne
  remonte sur le dossier replié.
- **Notifications** : des notifications « Nouveau message » partent pour la réception, le spam et
  les sous-dossiers du délégant.
- **Sélecteurs de dossier** : « Déplacer vers… » et le dossier d'ouverture ne listent que les
  dossiers racine. Les sous-dossiers du délégant sont inaccessibles.
- **Confusion possible** avec les « messageries rattachées » (task-304/374), un autre mécanisme.

### 3.3 Ce qui ne colle pas au modèle existant

Le registre des tenants gère déjà **plusieurs BAL par compte** : `mss_accounts`, avec une BAL par
défaut. Mais rattacher la BAL du délégant comme tenant **ne marche pas** :
- la sonde XOAUTH2 se connecte « en tant que » l'adresse du délégant, alors que Mailiz expose la
  délégation **à l'intérieur de la BAL du délégataire** ;
- même si la sonde passait, on créerait une base `u_<RPPS délégataire>_<adresse délégant>`, soit
  une seconde copie de la BAL du délégant.

**La délégation est un ensemble de dossiers dans la session du délégataire**, pas un nouveau tenant.

## 4. Inconnues à lever auprès de Mailiz / ANS

1. Le **contrat pour les logiciels métier**. Le mode opératoire ne le couvre pas encore, alors que
   le serveur expose déjà les dossiers. Faut-il un agrément éditeur ? Le message « contactez
   l'éditeur de votre logiciel » le suggère.
2. Les réponses `NAMESPACE` et `MYRIGHTS` : peut-on **découvrir les délégations et leurs droits** de
   façon fiable, sans deviner à partir du nom `shared/…` ?
3. L'**envoi SMTP délégué** :
   - `From` = délégant accepté pour une session XOAUTH2 du délégataire ?
   - en-tête `Sender` attendu ou posé par le serveur ?
   - libellé « de la part de » construit par qui ?
   - classement automatique dans les Envoyés du délégant ?
4. Les **attributs SPECIAL-USE** absents des dossiers partagés : est-ce voulu, ou corrigeable côté
   serveur ?
5. L'**état lu propre à chaque utilisateur** : est-ce confirmé, et voulu ?
6. La **signature MSSanté** et l'**accusé de lecture** en délégation : qui signe, au nom de qui ?
7. Les **notifications** d'ajout et de retrait de délégation : un signal exploitable par un
   logiciel métier ?

Une partie se mesure sans attendre Mailiz, par une **caractérisation instrumentée** sur les comptes
de formation (§6, US 0).

## 5. Décisions métier à prendre

| # | Question | Options |
|---|---|---|
| Q1 | Que faire **d'ici la livraison** de la délégation ? | (a) masquer les dossiers `shared/` ; (b) les afficher, mais confinés (corbeille correcte, dossiers système protégés, aucun traitement clinique) ; (c) livrer directement la fonctionnalité complète |
| Q2 | Les messages délégués sont-ils **traités cliniquement** (CDA, patients, IA, recherche) ? | (a) non : lecture et gestion seulement ; (b) oui, mais cloisonnés par BAL propriétaire, sans mélange avec les patients du délégataire ; (c) traités une seule fois dans la base du délégant, ce qui ouvre un accès inter-tenant |
| Q3 | **Envoi « de la part de »** dans la première version ? | inclus / lot suivant |
| Q4 | **Traçabilité** : le délégant doit-il voir les actes de ses délégataires ? | oui (PGSSI-S, imputabilité) / plus tard |
| Q5 | **Lu / non lu** : suivre le serveur (état propre à chacun), ou indiquer aussi l'état du délégant ? | serveur seul / double état |
| Q6 | **Clients** concernés | mobile et weda2 (règle de parité e2e) / un seul, avec divergence |
| Q7 | **Gestion des délégations** (ajout et retrait) depuis nos clients ? | hors périmètre (webmail Mailiz seul, comme aujourd'hui) / à instruire si Mailiz ouvre une API |

### Décisions actées (humain, 2026-10-25)

- **Q1 — Confiner.** Les dossiers délégués restent affichés, sous ces conditions :
  - la suppression va dans la corbeille du propriétaire ;
  - les dossiers système du délégant sont protégés ;
  - aucun traitement clinique, IA, contact, notification ni recherche ;
  - ce qui a déjà été produit est purgé.
- **Q2 — Gestion seule, définitivement.** Les messages délégués ne sont **jamais** traités
  cliniquement dans la base du délégataire : ni CDA, ni patients, ni IA, ni embeddings, ni
  contacts. L'US 5 disparaît.
- **Q3 — Envoi « de la part de » au lot suivant.** Il est conditionné à la caractérisation SMTP
  Mailiz.
- **Q6 — Mobile et weda2**, avec la parité e2e.
- **Q4, Q5 et Q7 restent ouvertes.** Défauts retenus d'ici leur arbitrage :
  - Q5 : on suit l'état lu du serveur, propre à chacun ;
  - Q7 : la gestion des délégations reste hors périmètre.

## 6. Découpage proposé (avant arbitrage — voir la version révisée au §7)

| US | Contenu | Dépôts | Priorité |
|---|---|---|---|
| **0 — Banc de délégation** | Dovecot de test avec espace `shared`, plugin ACL et état lu propre à chacun, reproduisant Mailiz. Caractérisation instrumentée sur les comptes de formation (NAMESPACE, MYRIGHTS, SMTP délégué). Prérequis des tests d'intégration (règle 1b). | api-mail | 0 |
| **1 — Confinement** | Suppression vers la corbeille **du propriétaire**. Dossiers système du délégant reconnus par leur nom sous `shared/<adr>/` et protégés. Aucun traitement clinique, IA, contact, notification ni recherche sur `shared/`. Purge de ce qui a déjà été produit. **Ou** masquage, selon Q1. | api-mail (+ clients si affichage) | **1** |
| **2 — BAL déléguées visibles** | Le modèle expose le propriétaire et les droits ; types système par rôle. Section « Boîtes déléguées » libellée « Boîte de Dr X » dans les deux clients, compteurs, sélecteurs de dossiers complets. | dtos-mss, api-mail, mobile, weda2 | 2 |
| **3 — Envoyer de la part du délégant** | Choix de la BAL émettrice, `From` contrôlé sur la liste des identités autorisées, en-tête et libellé selon le contrat Mailiz. Envoyés et brouillons au bon endroit, réponse depuis un dossier délégué en délégation par défaut, accusés de lecture, signature. | dtos-mss, api-mail, mobile, weda2 | 3 |
| **4 — Traçabilité** | Audit acteur + propriétaire (RPPS du délégataire, BAL du délégant), consultable par le délégant (Q4). | api-mail (+ clients) | 3 |
| **5 — Traitement clinique cloisonné** | Seulement si Q2 = (b) ou (c). | api-mail | 4 |
| **6 — Révocation** | Retrait de la délégation : purge complète de ce qui a été produit chez l'ex-délégataire, et message clair à l'utilisateur. | api-mail, clients | 2 |

Hors périmètre en l'état : la **gestion des délégations** (Q7) et l'accès par un **non-titulaire
de BAL**. Un délégataire sans BAL Mailiz ne peut pas se connecter à notre application, faute de
tenant.

## 7. Découpage révisé après arbitrage

| Task | US | Dépôts | Dépend de |
|---|---|---|---|
| **task-397** | **Confinement des BAL déléguées.** Banc Dovecot avec espace `shared`, ACL et état lu propre à chacun. Suppression et vidage vers la corbeille **du propriétaire**. Dossiers système du délégant protégés côté API. Aucun traitement clinique, IA, contact, notification ni recherche sur `shared/`. Purge de ce qui a déjà été produit dans les bases des délégataires. | api-mail | — |
| **task-398** | **BAL déléguées visibles et gérables.** Le contrat porte le propriétaire et le rôle des dossiers. Section « Boîtes déléguées » dans les deux clients, libellés et icônes système, compteurs, sélecteurs de dossiers complets, message à la révocation. | dtos-mss, api-mail, client-mobile, client-angular | task-397 |
| **task-399** | **Envoyer de la part du délégant** (lot suivant). Caractérisation SMTP Mailiz, choix de la BAL émettrice, `From` contrôlé, Envoyés et brouillons au bon endroit, accusés de lecture, signature. | dtos-mss, api-mail, client-mobile, client-angular | task-398 |
| **task-400** | **Traçabilité acteur / propriétaire** (Q4 à arbitrer). | api-mail (+ clients) | task-397 |
