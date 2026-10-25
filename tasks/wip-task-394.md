# todo-task-394.md — Une rédaction sans texte dans le corps ne laisse ni brouillon ni question (weda2 et mobile)

**Repos**: api-mail, client-angular, client-mobile
**Dependencies**: aucune
**Epic**: E009
**Single frontend**: false
**Priorité**: **3** — défaut visible du médecin : fermer un message vide pose une question inutile (weda2), et des
brouillons sans contenu s'accumulent dans « Brouillons ».

> **Origine.** Signalement de l'humain, 2026-10-24 : « lorsque je compose un nouvel email, et que je ne saisis rien
> dans le corps du message, que je quitte par la croix, je ne devrais pas avoir de message de confirmation concernant
> le brouillon puisque rien n'a été saisi. Idem, assure-toi qu'un brouillon ne s'enregistre pas si dans le corps rien
> n'a été saisi. »

## Ce qui est établi

- **weda2** (`libs/mss/src/features/mail/components/mail-compose/mail-compose.component.ts`) :
  - la croix appelle **toujours** `requestDiscard()`, qui affiche « abandonner le brouillon ? », même pour une
    rédaction vide ;
  - l'enregistrement (automatique toutes les 30 s, en quittant, avant d'ouvrir une autre rédaction) passe par
    `hasUnsavedContent()` → `hasContent()`. Un objet, un destinataire ou une pièce jointe y suffisent ; pour le corps,
    `hasOwnText` exclut déjà la signature.
- **mobile** (`src/app/features/mail/components/mail-compose/mail-compose.component.ts`) :
  - la croix enregistre le brouillon sans rien demander, si `hasDraftContent()` ;
  - `hasDraftContent()` compte l'objet, les destinataires et **tout** le texte du corps (`htmlToText`), signature
    comprise. `splitOwnText` (`core/utils/spelling-correction.util.ts`) sait déjà isoler le texte du médecin.

## Décisions actées (humain, 2026-10-24)

1. **Un brouillon n'existe que si le médecin a écrit dans le corps du message.** Le « texte du médecin » est le corps
   **sans la signature et sans la citation** du message d'origine (réponse, transfert). Un objet, un destinataire ou
   une pièce jointe, sans texte, ne suffisent pas : la rédaction se ferme sans brouillon, et ils sont abandonnés.
2. **Périmètre : weda2 et mobile**, même règle.

## Objective

Fermer une rédaction où le médecin n'a rien écrit dans le corps ne pose aucune question et ne crée aucun brouillon. Une
rédaction où il a écrit se comporte comme aujourd'hui.

### Règles

- **Sans texte du médecin dans le corps** :
  - **weda2** : la croix ferme la rédaction tout de suite, sans « abandonner le brouillon ? » ;
  - **mobile** : la croix et le geste de fermeture ferment sans enregistrer ;
  - **les deux** : l'enregistrement automatique (30 s), l'enregistrement en quittant la rédaction (autre message, autre
    dossier) et celui qui précède l'ouverture d'une autre rédaction n'enregistrent rien ;
  - l'alerte du navigateur à la fermeture de l'onglet (weda2, `beforeunload`) ne se déclenche pas.
- **Avec du texte du médecin** : comportement inchangé (weda2 : confirmation à la croix ; mobile : enregistrement à la
  croix ; enregistrement automatique et en quittant).
- **Réponse et transfert** : la citation du message d'origine n'est pas du texte du médecin. Ouvrir « Répondre » puis
  fermer sans écrire ne laisse rien.
- **Brouillon déjà enregistré, rouvert depuis « Brouillons »** (décision PO, cohérente avec la règle 1) : s'il porte du
  texte du médecin, rien ne change. Si le médecin efface tout son texte puis ferme, le brouillon existant n'est **ni
  supprimé ni écrasé en silence** : weda2 garde la confirmation d'abandon (qui supprime le brouillon) ; le mobile ne
  l'enregistre pas vide et le laisse tel qu'il était.
- **La signature seule n'est pas du texte** (déjà le cas sur weda2, nouveau sur le mobile).

### Hors périmètre

- Côté API, l'enregistrement d'un brouillon vide reste accepté : la règle est une règle de saisie, portée par les
  clients. Blazor.

## Gherkin

Voir `tests/Features/Mss/EmptyComposeLeavesNoDraft.feature`.

## Parcours e2e

| Scénario | Version | Comportement | mobile | angular |
|---|---|---|---|---|
| `E2E-DRAFT-004` (nouveau) | 1 | « Nouveau message », destinataire et objet saisis, corps vide, fermeture par la croix : aucune question (weda2), et aucun brouillon côté serveur (relu par l'API, liste des brouillons inchangée). Seed `boite-praticien`. | requis | requis |
| `E2E-DRAFT-001`, `E2E-DRAFT-002` | inchangée | Comportement attendu identique. Les aides mobiles saisissent désormais du texte dans le corps (elles créaient un brouillon avec un objet seul). | requis | requis |
| `E2E-DRAFT-003` | inchangée | Le parcours écrit déjà un texte : inchangé. | requis | requis |

## Definition of Done

- [ ] Build et tests verts : client-angular (weda2, `mss-lib`), client-mobile ; api-mail (`ScenarioCatalogTests`)
- [ ] Scénario E2E-DRAFT-004 ajouté (version 1) dans `Api/Mail/e2e/scenarios.yml`, et implémenté dans le mobile et dans
      weda2, prouvé rouge par mutation sur chaque client
- [ ] E2E-DRAFT-001, 002 et 003 verts sur les deux clients, sans montée de version
- [ ] weda2 — tests de composant, rouges d'abord : croix sans texte → aucune confirmation, rédaction fermée, aucun appel
      d'enregistrement ; objet + destinataire + pièce jointe sans texte → idem ; signature seule → idem ; réponse ou
      transfert sans texte → idem ; avec texte → confirmation inchangée ; enregistrement automatique, en quittant et
      avant une autre rédaction : aucun appel sans texte ; brouillon rouvert vidé de son texte → confirmation d'abandon
      gardée ; `beforeunload` sans texte → pas d'alerte
- [ ] mobile — tests de composant, rouges d'abord : croix et geste sans texte → aucun enregistrement ; objet et
      destinataire sans texte → idem ; signature seule → idem ; réponse ou transfert sans texte → idem ; avec texte →
      enregistrement inchangé ; enregistrement automatique sans texte → aucun appel ; brouillon rouvert vidé de son texte
      → aucun enregistrement vide
- [ ] Trou du filet : ligne ajoutée dans « Trous du filet » de `conventions/e2e.md` (défaut vu par l'humain, non vu par
      `/e2e`), E2E-DRAFT-004 prouvé rouge sur le comportement d'avant
- [ ] `data-testid` existants conservés ; aucune chaîne en dur hors libellés du client

## Manual Test Plan

- weda2 : banc e2e (`Client/Angular/front`, weda2 en `--serve-only`) ou weda2 local ; mobile : `cd Client/Mobile && npm
  start`.

1. « Nouveau message », ne rien saisir, fermer par la croix : weda2 ne pose aucune question ; rien dans « Brouillons »
   (les deux clients).
2. « Nouveau message », saisir un destinataire et un objet, corps vide, fermer : aucune question (weda2), rien dans
   « Brouillons ».
3. Même chose en attendant plus de 30 s avant de fermer : rien dans « Brouillons ».
4. Ouvrir un message, « Répondre », ne rien écrire, fermer : aucune question, aucun brouillon.
5. « Nouveau message », écrire une phrase dans le corps, fermer : weda2 demande « abandonner le brouillon ? » comme
   avant ; le mobile enregistre le brouillon, qui apparaît dans « Brouillons ».
6. Rouvrir ce brouillon, effacer tout le texte, fermer : weda2 demande la confirmation d'abandon ; le mobile ferme sans
   écraser le brouillon, qui garde son texte.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur. Correctif d'ergonomie de la rédaction, aucun échange modifié.
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable. Aucune donnée d'identité n'est manipulée.
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : aucun nouvel évènement ; moins de brouillons vides stockés
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui, stockage des brouillons inchangé
- **AIPD / impact RGPD** : inchangé. La règle réduit les données conservées (brouillons sans contenu).

## Branches
- `api-mail` (pushed) : fix/task-394-redaction-vide-sans-brouillon — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-394-redaction-vide-sans-brouillon (catalogue e2e)
- `client-mobile` (pushed) : fix/task-394-redaction-vide-sans-brouillon — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/fix/task-394-redaction-vide-sans-brouillon
- `client-angular` (code-only) : la forge écrit le code sur la branche checkée dans `Client/Angular/` (au `/start` :
  `feature/nova-mss-weda-integration`, arbre propre) ; humain gère commit, push et PR TFS

## Timings

*(généré par `tools/timing/report.sh --task task-394 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 21 s | — | — | — | — |
| /develop | ok | 34 s | 1 (14 s) | 2 (33 s) | — | api-mail 0B/1T, client-angular 1B/1T, e2e ×1 (8 min 20 s), reprise : COMPOSE-003 mobile écrit un texte |
| /sonar | skipped | 0.5 s | — | — | — | reprise : api-mail limité au catalogue (YAML) |
| /lint-angular | skipped | 0.4 s | — | — | — | reprise : weda2 inchangé depuis le lint propre |
| /lint-mobile | ok | 6.6 s | — | — | — | reprise : propre |
| /e2e | ok | 15 min 10 s | — | — | — | e2e ×10 (1 h 01 min), reprise : mobile 45/45, angular 53/53, parité verte |
| /review | failed | 4 min 53 s | 3 (19 s) | 2 (18 s) | — | client-mobile 1B/1T, client-angular 1B/1T, api-mail 1B/0T, CHANGES REQUESTED : perte de texte (mobile signature par défaut, weda2 sous la citation) ; règle à confirmer |
| **Total cycle** | | **21 min 08 s** | **4 (34 s)** | **4 (52 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : lint ×3 (22 s)

## Develop log

**2026-10-24 — `/develop` (forge).** api-mail `2400a7df` (catalogue) ; client-mobile `21de5b4` + `5775dbd` ; weda2 en code
seul, non commité sur `feature/nova-mss-weda-integration`. Deux forks en parallèle, un par client ; les bancs e2e ont été
joués à la suite, une voie à la fois.

- **Catalogue** : E2E-DRAFT-004 v1, mobile et Angular requis, `headless`. `ScenarioCatalogTests` : 23 verts.
- **weda2** (`mail-compose.component.ts`) :
  - `hasContent()` ne compte plus que `hasOwnText(body)`, c'est-à-dire le corps sans signature ni citation, ce qui
    était déjà testé ;
  - cinq points d'entrée suivent : enregistrement automatique, quitter pour un autre message, ouverture d'une autre
    rédaction, fermeture de l'onglet, croix ;
  - la croix (`requestDiscard`) ferme directement sans texte, sans brouillon enregistré et hors intention de l'hôte ;
  - une rédaction d'intention de l'hôte garde toujours la confirmation, puisqu'elle porte le document du dossier.
- **mobile** :
  - nouveau `core/utils/compose-body.util.ts` (`hasOwnText`), qui retire la signature et la citation `<blockquote>` ;
  - `splitOwnText` n'est pas réutilisé : il ignore ce qui suit la signature, alors qu'un texte tapé sous la signature
    compte ;
  - `hasDraftContent()` ne compte plus que ce texte. Ses deux appelants : `saveDraftNow` et `closeCompose` (croix,
    geste, ouverture différée).
- **Preuves rouges, tests unitaires** :
  - weda2 : 9 tests rouges avant le code (croix vide, objet + destinataire + pièce jointe, signature seule, réponse,
    enregistrement automatique, quitter, « Nouveau message » pendant une rédaction, brouillon rouvert vidé,
    fermeture de l'onglet). 3 tests verts d'emblée sont prouvés par mutation : M1, la croix ferme sans condition ;
    M2, l'exception de l'intention est retirée ;
  - mobile : 11 tests rouges contre un bouchon (7 sur le composant, 4 sur l'utilitaire). Puis 2 mutations : M1, le
    texte après la signature ou la citation est ignoré ; M2, `hasDraftContent` est toujours faux.
- **Tests existants adaptés**, sans changer ce qu'ils vérifient : du texte est ajouté dans le corps.
  - weda2 : 3 tests de composant (toolbar, safety ANG-15, intent auto-save) ;
  - mobile : 9 tests de mécanique de brouillon, et les aides e2e de E2E-DRAFT-001 et 002.
- **E2E-DETAIL-001 (weda2) adapté** : sa réponse sans texte se fermait par la croix puis cliquait la confirmation
  d'abandon, qui n'apparaît plus. Le test vérifie désormais que la réponse se ferme sans question. Le fork ne l'avait
  pas vu, c'est la voie Angular qui l'a révélé. Prévention : `conventions/e2e.md` › `comportement-retire-encore-traverse`.
- **Preuves par mutation e2e** (banc `--serve-only`, code restauré puis rejoué vert) :

  | Mutation | Client | Assertion tombée |
  |---|---|---|
  | MA1 : ancien critère (objet, destinataire, pièce jointe comptent) | weda2 | « la croix ferme la rédaction » (la question la garde ouverte) |
  | MA3 : la croix ferme sans question mais enregistre selon l'ancien critère | weda2 | « aucun enregistrement de brouillon n'est parti » |
  | M1 : ancien critère dans `hasDraftContent` | mobile | « relu côté serveur : aucun brouillon ne porte cet objet » |

- **Bancs** :
  - weda2 : E2E-DRAFT-004 et DETAIL-001 verts, la voie complète ayant d'abord révélé DETAIL-001 ;
  - mobile : DRAFT-001, 002, 003, 004 et DETAIL-001 verts.
- **Tests** : weda2 `mss-lib` 1 226 ; mobile 1 257. Builds verts, 0 erreur de lint.
- **Défaut indépendant relevé (mobile)** : le spec de la rédaction lancé seul (`--include`) fait tomber 4 tests
  « suggestions de destinataires » (task-388). C'était déjà le cas sur `develop` ; la suite complète est verte.
- **Trou du filet** : ligne ajoutée dans `conventions/e2e.md`.

**2026-10-24 — `/develop`, reprise après `/e2e` rouge** (`questions/task-394.md`) : E2E-COMPOSE-003 (mobile) écrit
désormais un texte dans le corps avant d'attendre l'enregistrement automatique, comme DRAFT-001 et 002. Ce qu'il
vérifie ne change pas. `tsc -p e2e` OK, lint propre. Vérification : c'était le seul test mobile restant à attendre un
brouillon sans texte.

## Sonar log

**Skipped (2026-10-24).** api-mail n'est touché que par `e2e/scenarios.yml` (catalogue e2e, YAML), hors du périmètre
d'analyse Sonar (C#). Aucun code C# modifié, donc le new code est vide. Qualité : /sonar skipped — api-mail sans code
C# modifié.

## Lint log

**client-angular (2026-10-24)** — `npx nx run-many -t lint --projects=tag:scope:mss` : 0 erreur, aucune itération de
correction. Les avertissements restants sont antérieurs.

## Lint mobile log

**client-mobile (2026-10-24)** — `npm run lint` : « All files pass linting ». Aucune itération, rien à commiter.

## E2E log

Run du 2026-10-25, après la reprise — **VERT**. Il remplace le run rouge du 2026-10-24 (E2E-COMPOSE-003 mobile).

| Voie | Déclencheur | Résultat | Tests |
|---|---|---|---|
| mobile | api-mail et client-mobile touchés | ✅ verte | 45 verts, 0 flaky, 0 rouge |
| angular | api-mail et client-angular touchés (code seul) | ✅ verte | 53 verts, 0 flaky, 1 quarantaine |

- Voies jouées par `Tools/e2e/lane_cache.py` (aucune réutilisée).
- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task ; E2E-DRAFT-004 v1 prouvé rouge par mutation sur les deux
  clients (`## Develop log`).
- Quarantaines : E2E-COMPOSE-002 (angular, task-350), passée
- Divergences ouvertes : aucune
- Démontage : complet (ports libres)

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
| E2E-DRAFT-004 | 1 | headless | Une rédaction sans texte dans le corps ne laisse ni brouillon ni question | ✅ | ✅ |
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

**Verdict : CHANGES REQUESTED** — 2 bloquants (perte de texte du médecin). Détail et règle de remplacement proposée :
`questions/task-394.md`. Relecture indépendante (agent neuf, lecture seule) ; le cas mobile est confirmé à la lecture
par l'orchestrateur (`injectSignature`).

**Validation** :
- weda2 : build ✓, `mss-lib` 1 226 ;
- mobile : build ✓, 1 257/1 257 sur deux rejeux, après un premier passage à 4 échecs. Ces 4 tests « suggestions de
  destinataires » (task-388) dépendent de l'ordre, et le défaut existe déjà sur `develop` ;
- api-mail : build ✓ ; 6 764 verts. 3 échecs, tous des tests « du jour » (`FilterTodayEmails…`, `GetFolderToday…`,
  `GetFolderNotSeenToday…`), lancés à 00:05 : c'est la fenêtre 00:00-02:00 connue (corpus en heure locale, Dovecot en
  UTC), aussi rouge sur `develop`. Pas une régression : la task ne change aucun C# ;
- e2e : vert (mobile 45/45, Angular 53/53).

**Bloquants** :
1. mobile : nouveau message avec signature par défaut. Le texte tapé entre dans les marqueurs de signature : aucun
   brouillon, et le texte est perdu à la fermeture.
2. weda2 : le texte écrit sous la citation ou sous la signature est ignoré. Une réponse écrite sous la citation est
   perdue à la croix, alors qu'elle était enregistrée avant la task.

**Suite à ouvrir** : les 4 tests mobiles « suggestions de destinataires » (task-388) dépendent de l'ordre d'exécution.

**Prévention** : `conventions/e2e.md` › `html-construit-a-la-main`.

