# todo-task-393.md — Carnet d'adresses refondu : voir un contact, lui écrire, le modifier sans erreur (weda2 et mobile)

**Repos**: api-mail, client-angular, client-mobile
**Dependencies**: task-388 (mergée — la fiche weda2 redessinée en (k) est le point de départ)
**Epic**: E009
**Single frontend**: false
**Priorité**: **3** — aucun défaut bloquant ; le carnet actuel fait perdre du temps (largeur perdue, icônes
inexpliquées, adresse par défaut choisie à deux endroits) et laisse perdre une saisie sans prévenir.

> **Origine.** Séance du 2026-10-24 : refonte demandée par l'humain à partir de deux captures de weda2 (liste du carnet,
> fiche « Modifier le contact »), maquettes produites dans Stitch puis arbitrées (voir « Décisions actées »).

## Références de design (Stitch)

- **weda2** — projet Stitch desktop `HealthPlatform` (`4321689327130998790`) :
  - `mss-contacts — carnet d'adresses (liste + aperçu)` — écran `713f604d76c34810af0aeda665cb8106`
  - `mss-contacts — fiche contact (modification)` — écran `20699fd485f047abab87a861d85d9de5`
- **mobile** — aucun écran contacts dans le projet Stitch `client-mobile` (`10088502293310567548`) : `/stitch-design`
  les crée pendant `/develop` (titres `contacts` et `contact-editor`), en transposant les deux écrans weda2.
- Les maquettes sont une **référence visuelle, pas une spécification**. En cas d'écart, **ce task file fait foi**. Les
  maquettes contiennent encore des éléments **exclus** (ci-dessous) : ne pas les coder.

## Décisions actées (humain, 2026-10-24)

1. **Retirés de la refonte** : « derniers échanges » avec le contact, date de naissance pour départager les homonymes,
   date de dernière synchronisation avec l'annuaire. Aucun changement de contrat ni d'API n'est donc nécessaire.
2. **Contrôle d'une adresse MSSanté saisie : format d'adresse seul.** Aucun contrôle de domaine : l'Espace de Confiance
   MSSanté compte des domaines hors `.mssante.fr` (ex. `…@interop-mssante.apicrypt.org`), et seul l'annuaire fait foi.
3. **Pas d'indice de domaine** sous les adresses (« Apicrypt », « Médecin », région…) : il supposerait une table de
   correspondance qui n'existe pas.
4. **Quitter une fiche modifiée et non enregistrée demande confirmation** (« Abandonner les modifications ? » —
   Abandonner / Continuer la saisie). Rien n'est demandé si rien n'a changé.
5. **Périmètre : weda2 et mobile.** Blazor garde son écran (voir Objective).

## Objective

Le médecin trouve un contact, voit qui il est et lui écrit en deux gestes, sans quitter son carnet ; il modifie une fiche
sans pouvoir perdre sa saisie ni enregistrer une adresse mal formée. Même comportement sur weda2 et sur le mobile, chacun
avec la disposition de son écran.

**Pourquoi pas Blazor** : les maquettes et la demande portent sur weda2 et le mobile. Le comportement attendu des
scénarios e2e existants ne change pas (voir § Parcours e2e), donc aucune divergence entre clients n'est créée.

### Périmètre

**(a) Liste du carnet (weda2 et mobile)**
- Chaque contact : avatar à l'icône de son type (task-388 (f)), nom, spécialité à défaut profession (task-388 (h)),
  adresse par défaut (à défaut la première) et « +N » s'il en a d'autres.
- **Marques explicites** à la place des icônes inexpliquées : pastille « Sans adresse MSSanté » pour un contact sans
  adresse (`isComplete` faux — c'est la définition actuelle du contrat), pastille « Annuaire » pour un contact importé
  de l'annuaire national (`source` ≠ local). Weda2 : l'icône ⚠ et le bouclier seuls disparaissent.
- **Filtres rapides** « Sans adresse MSSanté » et « Annuaire », chacun avec son nombre, combinables avec la vue (tous,
  favoris, récents), le type et la recherche ; « Réinitialiser » rend la liste entière.
- **weda2** : la barre A–Z horizontale est remplacée par des en-têtes de lettre dans la liste et un index vertical à
  droite. Import / export vCard passent dans un menu « ⋯ » à côté du tri. Actions au survol d'une ligne : « Écrire »,
  favori. La suppression quitte la ligne et passe dans le menu « ⋯ » de l'aperçu.
- **Mobile** : l'index alphabétique existant est conservé ; la vue, le type et les filtres restent accessibles sans
  défilement horizontal à 390 px de large.

**(b) Aperçu d'un contact**
- **weda2** : sélectionner un contact l'affiche dans un **panneau à droite de la liste**. La liste et la sélection
  restent en place. Le panneau montre : avatar, nom, badge « RPPS certifié » (règle de task-388 (k) inchangée),
  spécialité, organisation ; les adresses MSSanté, la par défaut en premier avec « Par défaut » ; profession,
  spécialité, RPPS, téléphone ; étiquettes et notes. Actions : **« Écrire un message »**, « Modifier », favori, et
  « Supprimer » dans un menu « ⋯ » (avec la confirmation actuelle).
- **Mobile** : toucher un contact ouvre la même fiche de consultation, en plein écran, avec retour à la liste et les
  mêmes actions.
- **Copier une adresse** : une action par adresse ; un message bref confirme la copie.
- Sans contact sélectionné (weda2), le panneau invite à en choisir un.

**(c) « Écrire un message »**
- Ouvre la rédaction avec l'**adresse par défaut** du contact dans « À », via le pré-remplissage de rédaction existant
  (`ComposePrefill`, weda2 ; équivalent mobile).
- **Sans adresse par défaut et avec plusieurs adresses** : le médecin choisit l'adresse avant l'ouverture de la
  rédaction (décision PO, cohérente avec task-379 : aucune adresse n'est imposée quand le médecin n'en a pas désigné).
- Une seule adresse : elle est utilisée. **Aucune adresse** : l'action est absente et la fiche propose « Ajouter une
  adresse MSSanté ».

**(d) Fiche de modification et de création**
- **Type de contact** choisi par trois boutons côte à côte (Professionnel / Structure / Patient), en remplacement de la
  liste déroulante. Les champs propres au type restent ceux d'aujourd'hui (INS pour un patient, RPPS pour un
  professionnel).
- **Adresses MSSanté** : une ligne par adresse (le mobile abandonne la zone de texte unique). Chaque ligne a un choix
  « par défaut » (bouton radio) et une action « Retirer ». Le choix **« Aucune — proposer toutes les adresses »** est
  conservé (task-379). La liste déroulante « Adresse par défaut » de weda2 disparaît, car le bouton radio la remplace.
  Retirer l'adresse par défaut ramène à « Aucune ».
- **Contrôle de format** à la saisie et à l'enregistrement : une adresse qui n'est pas une adresse électronique (sans
  `@`, sans domaine, avec espace) est signalée **sous le champ**, et l'enregistrement est refusé tant qu'elle reste. Une
  ligne vide est ignorée. Aucun contrôle de domaine (décision 2).
- **RPPS d'un contact importé de l'annuaire** : affiché en lecture seule, avec la mention « Fourni par l'Annuaire santé —
  non modifiable ». Les autres champs restent modifiables (un import ultérieur les remplace, règle de task-388 (i)).
- **Modifications non enregistrées** : une mention discrète près de « Enregistrer ». Quitter la fiche (Annuler, autre
  contact, autre module, retour mobile) déclenche la confirmation de la décision 4. « Continuer la saisie » garde les
  valeurs saisies.
- **Notes** : pas de compteur de caractères. `ContactDto.Notes` n'a pas de longueur maximale, et la US n'en crée pas
  (le « 0 / 500 » de la maquette est exclu).
- Weda2 : la fiche reste une page avec fil d'Ariane et un seul bouton d'enregistrement en haut (`#save-contact-btn`,
  task-388 (k)), et tient sans défilement à 1366×768 pour un contact à trois adresses.

**(e) Identifiants e2e**
- Les identifiants déjà utilisés par les suites e2e sont **conservés** ; les nouveaux éléments interactifs reçoivent un
  `data-testid`. Les aides e2e qui ouvrent une fiche ou choisissent l'adresse par défaut
  (`createContactWithTwoAddresses`, `saveEditedContact`, et l'étape « marquer par défaut » de E2E-COMPOSE-004) sont
  adaptées au nouveau geste dans `Client/Angular/front/e2e/mss-e2e/specs/functional.e2e.ts` et
  `Client/Mobile/e2e/specs/functional.spec.ts`, **sans changer ce qu'elles vérifient**.

### Hors périmètre

- Derniers échanges avec un contact, date de naissance, date de synchronisation annuaire (décision 1).
- Contrôle du format d'adresse **par l'API** : les contacts existants peuvent porter des adresses mal formées. Les
  refuser côté serveur bloquerait leur enregistrement. Ce point est à instruire séparément.
- Indice de domaine des adresses (décision 3). Blazor.

## Gherkin

Voir `tests/Features/Mss/ContactManagementRedesign.feature`.

## Parcours e2e

| Scénario | Version | Comportement | mobile | angular |
|---|---|---|---|---|
| `E2E-CONTACT-004` (nouveau) | 1 | Ouvrir un contact depuis le carnet : sa fiche montre ses adresses, la par défaut en premier ; « Écrire un message » ouvre la rédaction avec l'adresse par défaut dans « À ». Seed `contact-robert`. | requis | requis |
| `E2E-CONTACT-005` (nouveau) | 1 | Modifier un contact puis vouloir le quitter : la confirmation est demandée, « Continuer la saisie » garde la valeur. Une adresse mal formée est signalée et l'enregistrement est refusé. Seed `boite-praticien`. | requis | requis |
| `E2E-CONTACT-002`, `E2E-CONTACT-003`, `E2E-COMPOSE-004` | inchangée | Comportement attendu identique ; seul le geste change (aides adaptées, § (e)). | requis | requis |

Les deux nouveaux scénarios sont joués en `mode: headless` : aucun tiers externe n'intervient.

## Definition of Done

- [ ] Build et tests verts : client-angular (weda2, projet `mss`), client-mobile ; api-mail (tests du catalogue
      `ScenarioCatalogTests` verts)
- [ ] Scénario E2E-CONTACT-004 ajouté (version 1) dans `Api/Mail/e2e/scenarios.yml`, et implémenté dans le mobile et
      dans weda2
- [ ] Scénario E2E-CONTACT-005 ajouté (version 1) dans `Api/Mail/e2e/scenarios.yml`, et implémenté dans le mobile et
      dans weda2
- [ ] E2E-CONTACT-002, E2E-CONTACT-003 et E2E-COMPOSE-004 verts sur les deux clients, **sans montée de version**
- [ ] weda2 et mobile — tests de composant, rouges d'abord : pastilles « Sans adresse MSSanté » et « Annuaire » selon
      `isComplete` et `source` ; filtres rapides (nombre affiché, combinaison avec vue / type / recherche,
      réinitialisation)
- [ ] weda2 et mobile — « Écrire un message » : adresse par défaut dans « À » ; choix préalable sans adresse par
      défaut et avec plusieurs adresses ; action absente sans adresse (un test par cas)
- [ ] weda2 et mobile — adresse par défaut par bouton radio, « Aucune » conservé, retrait de l'adresse par défaut →
      « Aucune » ; le contact enregistré porte le choix (test sur le contact envoyé au service)
- [ ] weda2 et mobile — contrôle de format : `abc`, `a@`, `a b@x.fr` refusées avec message sous le champ et **aucun
      appel d'enregistrement** ; `x@interop-mssante.apicrypt.org` acceptée ; ligne vide ignorée
- [ ] weda2 et mobile — RPPS en lecture seule pour un contact importé de l'annuaire, modifiable pour un contact local
- [ ] weda2 et mobile — confirmation à la sortie d'une fiche modifiée (Annuler, changement de contact, navigation) ;
      aucune confirmation sans modification ; « Continuer la saisie » garde les valeurs
- [ ] weda2 — sélection d'un contact → panneau d'aperçu, liste et sélection conservées ; copie d'une adresse
      confirmée ; import / export vCard toujours fonctionnels depuis le menu « ⋯ »
- [ ] weda2 — fiche sans défilement à 1366×768 pour un contact à trois adresses (contrôle visuel consigné dans le
      `## Develop log`)
- [ ] mobile — écrans `contacts` et `contact-editor` créés dans Stitch par `/stitch-design`, références consignées
- [ ] `data-testid` sur chaque nouvel élément interactif ; identifiants e2e existants conservés
- [ ] Aucune chaîne en dur hors des libellés du client (convention de chaque client)
- [ ] Aucune adresse, aucun nom de contact ni INS dans les journaux du navigateur ou de l'application

## Manual Test Plan

- **weda2** : banc e2e (`Client/Angular/front`, weda2 servi en `--serve-only` contre le backend `e2e`), ou weda2 local
  contre l'API de développement. Ouvrir Messagerie › Carnet d'adresses.
- **mobile** : `cd Client/Mobile && npm start`, puis ouvrir Réglages › Contacts dans un navigateur à 390×844.

1. Carnet : un contact sans adresse porte « Sans adresse MSSanté », un contact importé de l'annuaire porte « Annuaire ».
   Activer le filtre « Sans adresse MSSanté » : seuls ces contacts restent, et leur nombre est juste. Réinitialiser.
2. weda2 : cliquer un professionnel importé (trois adresses). La fiche s'affiche à droite, la liste ne bouge pas.
   Copier une adresse et la coller ailleurs. Mobile : toucher le même contact, puis revenir.
3. « Écrire un message » sur ce contact : la rédaction s'ouvre avec l'adresse par défaut dans « À ». Sur un contact à deux
   adresses sans adresse par défaut, le choix de l'adresse est demandé d'abord.
4. Modifier : le RPPS est en lecture seule avec sa mention. Marquer une autre adresse « par défaut », enregistrer,
   rouvrir : le choix est conservé. Choisir « Aucune », enregistrer : la rédaction propose toutes les adresses.
5. Ajouter l'adresse `abc` : message sous le champ, enregistrement refusé. La remplacer par
   `test@interop-mssante.apicrypt.org` : enregistrement accepté.
6. Modifier le téléphone, puis cliquer « Annuler » (mobile : retour) : la confirmation apparaît. « Continuer la
   saisie » garde la valeur. Recommencer avec « Abandonner » : la valeur d'origine revient. Ouvrir puis fermer une
   fiche sans rien changer : aucune confirmation.
7. weda2 à 1366×768 : la fiche d'un contact à trois adresses tient sans défilement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur. La refonte est ergonomique et ne change aucun échange.
- **Exigences DSR honorées** : non applicable. Aucune exigence DSR ne porte sur la présentation du carnet. Le contrôle
  de format n'invente aucune règle de domaine MSSanté (décision 2).
- **INS** : non applicable. Le champ INS d'un contact patient reste tel qu'aujourd'hui, sans nouveau traitement ni
  changement de statut. L'adresse MSSanté d'un patient (`{INS}@patient.mssante.fr`) reste affichée comme aujourd'hui.
  L'action « Copier » ne la journalise pas.
- **Authentification PS** : inchangée (session weda2 / PSC du mobile). L'envoi lancé par « Écrire un message » suit le
  circuit d'envoi existant.
- **Habilitations** : inchangées. Le RPPS issu de l'annuaire devient non modifiable, car l'annuaire fait foi.
- **Interop CI-SIS** : non applicable. Aucun échange de document n'est créé ni modifié.
- **Tracé PGSSI-S** : aucun nouvel évènement. La création, la modification et la suppression de contact restent
  tracées comme aujourd'hui.
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun (profession et spécialité en libellés, task-388)
- **Hébergement HDS** : oui. Le stockage du carnet est inchangé.
- **AIPD / impact RGPD** : inchangé. Aucune nouvelle donnée n'est collectée, et les trois éléments qui en auraient
  demandé ont été retirés (décision 1).
