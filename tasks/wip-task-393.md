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

## Branches
- `api-mail` (pushed) : feat/task-393-carnet-adresses-refonte — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-393-carnet-adresses-refonte (catalogue e2e)
- `client-mobile` (pushed) : feat/task-393-carnet-adresses-refonte — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-393-carnet-adresses-refonte
- `client-angular` (code-only) : la forge écrit le code sur la branche checkée dans `Client/Angular/` (au `/start` :
  `feature/nova-mss-weda-integration`, arbre propre) ; humain gère commit, push et PR TFS
- `dtos-mss` : non listé, aucun changement de contrat prévu (branche paresseuse si `/develop` en a besoin)

## Develop log

**2026-10-24 — `/develop` (forge).** api-mail `c5435b79` (catalogue) ; client-mobile `9f69335` + `35c83f5` + `2deceb3` ;
weda2 en code seul, non commité sur `feature/nova-mss-weda-integration`. Deux forks en parallèle, un par client, sur un
contrat de `data-testid` commun ; les bancs e2e ont été joués à la suite, une voie à la fois.

- **Catalogue** (`Api/Mail/e2e/scenarios.yml`) : E2E-CONTACT-004 v1 et E2E-CONTACT-005 v1, mobile et Angular requis,
  `headless`. `ScenarioCatalogTests` : 23 verts.
- **Règle commune aux deux clients** : la pastille et le filtre « Annuaire », le RPPS verrouillé et le badge
  « RPPS Certifié » valent pour une source **FHIR ou LDAP** seulement, pas pour « source ≠ locale ». Sinon un contact
  importé d'un CSV ou enrichi par un CDA serait marqué « Annuaire », ce qui serait faux. « Sans adresse MSSanté » =
  `isComplete` faux.
- **weda2** :
  - liste en trois colonnes (filtres, liste avec en-têtes de lettre et index vertical, aperçu à droite) ;
  - menu « ⋯ » pour l'import et l'export vCard ; « Écrire » et favori au survol ;
  - « Écrire un message » passe par un service racine (`ContactComposeHandoffService`), qui garde le destinataire
    jusqu'à ce que `mss-mail` le prenne, une seule fois (consigne `service-propre-au-composant`) ;
  - fiche : type par sélecteur, adresses ligne par ligne avec bouton radio et « Aucune », contrôle de format au blur et
    à l'enregistrement, RPPS verrouillé pour l'annuaire ;
  - confirmation de sortie : « Annuler », et garde de route `leaveConfirmationGuard` sur `contacts` ;
  - nouveaux fichiers : `contact-card.util`, `contact-compose-handoff.service`, `leave-confirmation.guard`, et leurs
    specs.
- **mobile** :
  - liste avec pastilles et filtres ;
  - fiche de consultation plein écran, partagée avec l'éditeur dans la même fenêtre ;
  - « Écrire un message » via `openCompose$` (rédaction montée globalement), avec une feuille d'actions pour choisir
    l'adresse ;
  - éditeur ligne par ligne, avec segment de type, bouton radio et « Aucune » ;
  - confirmation par « Annuler » et par la garde `canDismiss` (retour matériel, glissement) ;
  - nouveau `contact-editor.util`.
- **Stitch (mobile)** : les deux générations ont expiré sans produire d'écran (voir `## Stitch design log`). Le code
  suit les écrans weda2 et la task. **À reprendre par l'humain dans Stitch** si une référence mobile est voulue.
- **Preuves rouges, tests unitaires** :
  - weda2 : 36 tests rouges avant le code. Les tests verts d'emblée sont prouvés par 8 mutations (espaces tolérés,
    domaine imposé, CSV compté comme annuaire, « Annuler » qui demande toujours, `take()` qui ne vide plus, garde
    toujours ouverte, livraison sans condition, nom sans repli organisation), toutes rouges sur l'assertion visée ;
  - mobile : 25 tests rouges contre des stubs. Deux témoins positifs sont prouvés par mutation (domaine
    `.mssante.fr` imposé, `onTypeChange` inopérant).
- **Preuves par mutation e2e** (banc `--serve-only`, une mutation à la fois, code restauré puis rejoué vert) :

  | Mutation | Client | Test | Assertion tombée |
  |---|---|---|---|
  | M1 / MA1 : « Écrire » ne fait rien (`writeToViewed` / `writeTo`) | mobile / weda2 | E2E-CONTACT-004 | « la rédaction s'ouvre sur l'adresse de Robert » |
  | M2 / MA2 : la sortie ne demande plus confirmation (`confirmDiscard` / `cancelEdit`) | mobile / weda2 | E2E-CONTACT-005 | « l'abandon des modifications est demandé » |
  | M3 / MA3 : l'erreur s'affiche mais l'enregistrement part (`save` / `saveContact`) | mobile / weda2 | E2E-CONTACT-005 | « aucun enregistrement n'est parti » (compteur de PUT) |

- **Voies e2e complètes** : mobile 44/44 (CONTACT-002, 003, 004, 005 et COMPOSE-004 verts, aides adaptées) ; Angular
  52/52 ; parité verte sur chaque colonne.
- **Contrôle visuel weda2 (DOD)** : spec temporaire de mesure, supprimée après usage.
  - Premier passage : la fiche **défilait** à 1366×768 avec trois adresses (966 px de contenu pour 680 px visibles),
    les deux colonnes coupées.
  - Après compaction (champs `small`, type dans l'en-tête de la carte Identité, adresses sans boîte, « Aucune » et
    « Ajouter » sur une ligne, aides retirées, notes sur deux lignes), plus aucun défilement à 1366×768 ni à 1440×900.
  - Deux défauts corrigés au même passage : icône favori barrée (`star-off`) remplacée par `star` ; « Fiche mise à
    jour » avec une majuscule.
  - Captures : `C:/Users/pasca/AppData/Local/Temp/forge-e2e/task-393-dev-ng1/shots/`.
- **Tests** : weda2 `mss-lib` 1 202 (110 fichiers) ; mobile 1 238.
- **Build** :
  - weda2 vert ; bundle initial à 2,10 Mo pour 2 Mo de budget (2,08 Mo à la revue de la 388) ;
  - SCSS du carnet à 21,97 kB, au-dessus du seuil d'avertissement de 20 kB (l'erreur est à 40 kB) ;
  - mobile vert.
- **Lint** : 0 erreur sur les fichiers touchés, e2e compris, sur les deux clients.
- **Passe qualité (§Q)** :
  - mobile : `2deceb3` ;
  - weda2 : faite à la main (`contactFullName` partagé, alias `editRppsCertified` retiré, `@if … as`), sans git.
- **Écarts assumés** :
  - weda2 : la fermeture de l'onglet et le rechargement ne demandent pas confirmation (pas de `beforeunload`) ;
  - mobile : la fenêtre couvre la liste, donc le cas « autre contact » n'existe pas ;
  - mobile : les styles de l'avatar typé sont recopiés depuis `mail-compose` (factorisation hors du diff).
- **Bruit de poste** : 3 échecs `HtmlEditorComponent` (mobile, sélection de texte) pendant que l'autre fork lançait sa
  suite Vitest, non reproduits ensuite. Deux suites de tests navigateur en parallèle sur le poste perturbent la
  sélection de texte.
- **Leçons** :
  - `conventions/angular.md` : `chainage-optionnel-qui-ment` (récidive, variante `toContain`) et
    `ds-button-id-requis` ;
  - `conventions/e2e.md` : `testid-prefixe-d-un-autre` et `confirmation-attendue-avant-le-clic`.

## Sonar log

**Skipped (2026-10-24).** api-mail n'est touché que par `e2e/scenarios.yml` (catalogue e2e, YAML), hors du périmètre
d'analyse Sonar (C#). Aucun code C# nouveau ou modifié, donc le new code est vide et la Quality Gate du new code reste
inchangée. Qualité : /sonar skipped — api-mail sans code C# modifié.

## Lint log

**client-angular (2026-10-24)** — `npx nx run-many -t lint --projects=tag:scope:mss` : **0 erreur**, aucune itération
de correction. Les avertissements restants (57 et 46 sur les deux projets) sont antérieurs, sauf deux `max-lines` dans
des fichiers de la task : `mss-contacts.component.ts` passe à 1 803 lignes (1 343 avant), et `mss-mail.component.ts`
en a 939. Le découpage du carnet (liste, aperçu, fiche) est laissé en suggestion. Build et tests : validés par
`/develop` après la dernière modification (`mss-lib` 1 202, build `weda2` vert).

## Lint mobile log

**client-mobile (2026-10-24)** — `npm run lint` : « All files pass linting », 0 erreur et 0 avertissement. Aucune
itération de correction, rien à commiter.

## Timings

*(généré par `tools/timing/report.sh --task task-393 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 19 s | — | — | — | — |
| /develop | ok | 1 h 02 min | 2 (15 s) | 5 (1 min 23 s) | — | api-mail 0B/1T, client-mobile 2B/4T, e2e ×2 (15 min 04 s), weda2 (code seul) + mobile 3 commits + catalogue ; e2e mobile 44/44, angular 52/52, 6 mutations rouges ; fiche weda2 compactée (1366×768 sans défilement) |
| /sonar | skipped | 0.5 s | — | — | — | api-mail touché par le seul catalogue e2e (YAML), aucun C# modifié |
| /lint-angular | ok | 40 s | — | — | — | 0 erreur (tag:scope:mss) ; 2 max-lines dans les fichiers de la task |
| /lint-mobile | ok | 12 s | — | — | — | All files pass linting |
| /e2e | ok | 15 min 44 s | — | — | — | e2e ×3 (15 min 17 s), vert : mobile 44/44, angular 52/52, 0 flaky, parité verte |
| /review | failed | 8 min 32 s | 3 (32 s) | 3 (4 min 47 s) | — | client-mobile 1B/1T, client-angular 1B/1T, api-mail 1B/1T, CHANGES REQUESTED : weda2 « Écrire » depuis une ligne (choix d'adresse rendu sous le contact sélectionné) ; questions/task-393.md |
| **Total cycle** | | **1 h 27 min** | **5 (48 s)** | **8 (6 min 10 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : lint ×2 (16 s)

## Stitch design log

`/stitch-design task-393` (Mode A, 2026-10-24) — projet Stitch `client-mobile` (`10088502293310567548`), design
system `assets/7f352f2521964c6dacc9c7df62922990`.

| Écran (titre = composant) | Action | Résultat |
|---|---|---|
| `contacts` (liste + filtres) | aucune correspondance → `generate_screen_from_text` ×1 (MOBILE) | ⚠️ **non matérialisé** : timeout MCP attendu, mais aucune nouvelle instance dans `get_project` ~40 min plus tard (66 instances avant et après ; seul `updateTime` a bougé, 15:16 UTC) |
| `contact-editor` (édition, confirmation de sortie) | aucune correspondance → `generate_screen_from_text` ×1 (MOBILE) | ⚠️ **non matérialisé** (même constat) |

- Pas de relance (règle : jamais de seconde génération après un timeout). `/develop` a codé les écrans Ionic d'après
  les deux écrans weda2 de la task et le périmètre (a)-(e) ; best-effort, non bloquant.
- **À relancer à la main dans l'interface Stitch** (titres exacts `contacts` et `contact-editor`) :
  - `contacts` : liste groupée par lettre, index A–Z, recherche, segment Tous/Favoris/Récents, puces de type,
    filtres rapides « Sans adresse MSSanté · n » et « Annuaire · n » + « Réinitialiser » (passage à la ligne, pas
    de défilement horizontal), lignes avec avatar typé, nom, spécialité, adresse par défaut « Par défaut » « +N »,
    pastilles explicites, étoile favori.
  - `contact-editor` : Annuler / « Modifier le contact » / Enregistrer, « Modifications non enregistrées », segment
    Professionnel / Structure / Patient, cartes Identité, Activité (RPPS verrouillé « Fourni par l'Annuaire santé —
    non modifiable »), Adresses MSSanté (une ligne par adresse : radio par défaut, champ, retrait ; ligne « Aucune —
    proposer toutes les adresses » ; erreur sous un champ mal formé ; « + Ajouter une adresse MSSanté »), Notes et
    groupes, « Supprimer le contact » ; alerte « Abandonner les modifications ? » (« Continuer la saisie » /
    « Abandonner »). Aucun compteur de notes, aucune date de naissance, aucun indice de domaine.

## E2E log

Run du 2026-10-24 — **VERT**.

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail et client-mobile touchés | ✅ verte | 44 verts, 0 flaky, 0 rouge, 0 quarantaine | voir `## Timings` |
| angular | api-mail et client-angular touchés (code seul, non commité) | ✅ verte | 52 verts, 0 flaky, 0 rouge, 1 quarantaine | voir `## Timings` |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task (à jour avec `develop`). Il porte E2E-CONTACT-004 v1 et
  E2E-CONTACT-005 v1, tous deux prouvés rouges par mutation sur les deux clients (`## Develop log`).
- Quarantaines : E2E-COMPOSE-002 (angular, task-350), passée
- Divergences ouvertes : aucune
- Parcours touchés sans spec e2e modifié : aucun (les specs mobile et weda2 bougent avec la task)
- Démontage : complet (ports libres). Deux conteneurs `e2e-*` arrêtés depuis le 2026-10-14, antérieurs à ce run,
  laissés en place.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-PATIENT-003 | 1 | headless | La fiche d'un patient ne montre pas les documents d'un autre patient du même mail | ✅ | ✅ |
| E2E-CONTACT-001 | 2 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Écrire à l'adresse choisie d'un contact à plusieurs adresses, ou à son adresse par défaut | ✅ | ✅ |
| E2E-COMPOSE-005 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 2 | headless | Créer un contact à deux adresses, le modifier sans les perdre, puis le supprimer | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-CONTACT-004 | 1 | headless | Consulter un contact depuis le carnet et lui écrire | ✅ | ✅ |
| E2E-CONTACT-005 | 1 | headless | Une fiche modifiée ne se perd pas sans confirmation, une adresse mal formée est refusée | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 1 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## Code Review Summary

**Verdict : CHANGES REQUESTED** — 1 bloquant (weda2), 4 points à corriger dans la même reprise, suggestions. Détail :
`questions/task-393.md`. Relecture indépendante (agent neuf, lecture seule), bloquant confirmé à la lecture par
l'orchestrateur.

**Validation (verte)**

| Repo | Build | Tests |
|---|---|---|
| api-mail | ✓ | ✓ 6 767 (16 ignorés) ; seul changement : `e2e/scenarios.yml` |
| client-mobile | ✓ | ✓ 1 238/1 238 |
| client-angular (code seul) | ✓ `weda2` | ✓ `mss-lib` 1 202 |

**E2E** : vert (mobile 44/44, Angular 52/52), mais aucun test n'emprunte « Écrire » depuis une ligne weda2.

**Règle 1b** : aucun comportement atteignable par un endpoint n'est ajouté ni modifié. api-mail ne change que le
catalogue e2e, et les deux clients consomment les routes existantes.

**Bloquant** : weda2, « Écrire » depuis une ligne pour un contact à plusieurs adresses sans adresse par défaut.
Le choix d'adresse n'est rendu que dans l'aperçu du contact sélectionné, et la ligne ne sélectionne pas. Résultat :
rien ne s'affiche, ou le choix apparaît sous un autre contact (risque de mauvais destinataire).

**Prévention** : `conventions/angular.md` › `action-a-deux-entrees`.

