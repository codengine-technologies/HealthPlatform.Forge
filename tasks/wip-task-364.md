# todo-task-364.md — Lecture d'un message : le contenu d'abord, les actions dans un panneau latéral masquable

**Repos**: api-mail, client-angular
**Dependencies**: — (aucune bloquante ; ordre recommandé : **après le merge de task-363**, dont l'import Weda
est déplacé dans le panneau par cette US)
**Epic**: E009
**Single frontend**: true
**Priorité**: **2** — ergonomie de lecture d'un courrier médical. Aucune donnée n'est perdue, mais le
praticien doit faire défiler l'écran pour lire le résultat qu'il est venu lire, sur chaque message
porteur d'actions.

> **Origine.** Demande de l'humain du 2026-10-10, sur une capture de la lecture d'un compte rendu de
> biologie dans `client-angular` : « le mail est trop bas dans la logique de lecture ». Les axes
> d'amélioration viennent d'une maquette **Stitch**, et les règles métier ont été arbitrées par
> l'humain le même jour : panneau déplié à chaque message, masquable, réduit au rail sur écran étroit,
> et les quatre blocs d'action déplacés dans le panneau.
>
> **Pourquoi un seul front.** La demande porte sur `client-angular`.
> - `client-mobile` : sa lecture en 390 px empile déjà les actions dans un autre écran, et un panneau
>   latéral n'y a pas de sens fonctionnel.
> - `client-blazor` : hors demande. À reprendre dans une US distincte si l'humain le souhaite.
> - `api-mail` est listé **uniquement pour le catalogue e2e** (`Api/Mail/e2e/scenarios.yml`). Aucun
>   code backend ne change.

## Ce qui existe (constaté dans le code le 2026-10-10)

Racine : `Client/Angular/front/libs/mss/src/features/mail/` (projet `mss-lib`).

- **Empilement** — `components/mail-detail/mail-detail.component.html` empile, **au-dessus** du corps du
  message, jusqu'à 13 blocs, dans cet ordre :
  1. barre d'outils (l.3-201) ;
  2. en-tête (l.203-259) ;
  3. bandeau « PATIENT » (l.261) ;
  4. bandeau « Rattachement en attente » (l.268) ;
  5. `manual-attachment-panel` (l.303) ;
  6. `weda-patient-panel` + `weda-import` (l.311) ;
  7. `biology-ack-panel`, **répété pour chaque document** (l.315) ;
  8. bandeau de doublon (l.323) ;
  9. bandeaux de suppression (l.507, l.572) ;
  10. `mail-tag` (l.645) ;
  11. `mail-attachment` (l.653) ;
  12. aperçu de pièce jointe (l.663, jusqu'à 70vh) ;
  13. enfin `.mail-detail-body` (l.773).
- **Mesure sur la capture** (fenêtre de 768 px de haut, un compte rendu de biologie avec acquittement,
  1 étiquette et 1 pièce jointe) : le premier résultat ne commence qu'à **~480 px**. Les blocs d'action
  prennent donc **60 % de la hauteur** avant la première ligne utile.
- **Double défilement** — tous les blocs du haut sont fixes (`overflow: hidden`,
  `mail-detail.component.scss:1-13`). `.mail-detail-body` défile (scss:275-279), et
  `mail-body` › `.mail-body-content` ouvre un **second** conteneur de défilement (mail-body.scss:7-16,
  48-51). La capture montre bien deux barres de défilement.
- **Aucun panneau latéral** n'existe dans la lecture. Seul modèle repliable du module :
  `features/layout/mss-layout.component` (`sidebarCollapsed`, `toggleSidebar()`, chevron).

## Référence de design (Stitch)

- **Projet Stitch** `HealthPlatform` (DESKTOP), id `4321689327130998790`, système de design
  « L'Éclat Médical ».
- **Écran** `mail-detail-sidebar — Vue de lecture MSSanté`, id `4f429a1cc1834f7c88ba858dfc274aea`.
- **Captures** :
  - avant : `Docs/epics/img/design/task-364/mail-detail-avant.png` ;
  - après, panneau ouvert : `Docs/epics/img/design/task-364/mail-detail-stitch-panneau-ouvert.png`.
- **Ce que la maquette prouve** : avec le panneau ouvert, les onglets du contenu sont à **~130 px**
  du haut, au lieu de ~480 px.
- **C'est une référence, pas du code.** `/develop` en traduit la **structure** (en-tête compact,
  zone de lecture, panneau droit) dans les composants et le style **existants** de `mss-lib`. Il ne
  reprend ni la palette, ni les polices, ni le HTML de Stitch.
- **À NE PAS reprendre** — ajouts inventés par Stitch, faux ou interdits :
  - l'INS / le NIR affichés en clair : **interdit**, garde-fou santé ;
  - « Certifié MSSanté v2 », « DMP & Dossier synchronisés », l'identifiant « #MSS-2026-… » ;
  - le badge « Alerte INR bas » et le bloc « Recommandation du biologiste » : le document CDA est
    rendu **tel quel**, sans ajout ni réinterprétation ;
  - les lignes de résultats supplémentaires (TP, fibrinogène, créatininémie…) : ce sont des données
    d'illustration.

## Objective

À l'ouverture d'un message, le praticien lit **le contenu d'abord**. Tout ce qui sert à **agir** sur le
message est rangé dans un **panneau latéral droit**, déplié par défaut et masquable.

### 1. En-tête compact

- L'en-tête tient sur **deux lignes** :
  - ligne 1 : le sujet, et à droite les actions du message ;
  - ligne 2 : expéditeur → destinataires, puis la date.
- La **barre d'outils actuelle fusionne** avec la ligne du sujet.
  - Restent visibles en icônes avec infobulle : Répondre, Répondre à tous, Transférer, Imprimer,
    Synthèse IA.
  - Les actions moins fréquentes passent dans un menu **« Plus d'actions »** : Exporter, Déplacer vers,
    Supprimer, et les autres icônes actuelles.
  - **Aucune action ne disparaît.**
- Sous l'en-tête, une rangée de **puces de synthèse**, chacune cliquable :
  - **« Acquittement à traiter »** (orange), seulement si un acquittement est en attente ;
  - **« N pièce(s) jointe(s) »** ;
  - les **étiquettes** du message.
  - Un clic sur une puce ouvre le panneau sur la section correspondante.

### 2. Zone de lecture

- Les onglets (Mail / document(s) / Biologie) suivent **immédiatement** l'en-tête.
- Il n'y a **qu'un seul défilement** pour le contenu : le double conteneur disparaît.
- Les onglets restent **visibles en haut** pendant le défilement.
- Seules **deux alertes**, qui portent sur le message lui-même, restent au-dessus du contenu, sous
  forme de **ligne fine** (une ligne de texte avec son action) : le **doublon** et le message
  **supprimé ailleurs**.
- L'**aperçu d'une pièce jointe** s'ouvre dans la zone de lecture, à la place du contenu, avec un
  retour au message. Il ne s'ouvre plus au-dessus du corps.
- La Synthèse IA continue de remplacer le corps dans la zone de lecture. Le panneau reste en place.

### 3. Panneau latéral « Actions & dossier »

Le panneau, d'environ 320 px, contient **quatre sections**. Chacune peut être repliée par son
en-tête, et les sections vides ne s'affichent pas.

1. **Acquittement biologique**
   - Elle n'apparaît que si le message porte un compte rendu de biologie à acquitter.
   - Elle est **en premier**, avec le badge « À TRAITER ».
   - Elle reprend les mêmes actions qu'aujourd'hui : Pris connaissance, Rappel patient, Convocation,
     Adressage confrère, Marquer comme résolu.
   - Plusieurs documents à acquitter donnent **une entrée par document**, titrée par le titre du
     document. Les bandeaux répétés au-dessus du contenu disparaissent.
2. **Patient** — elle regroupe :
   - le patient détecté ;
   - le rattachement en attente ;
   - le rattachement manuel (task-331) ;
   - le dossier patient Weda et l'import Weda (task-357, task-363).

   Comportements et règles inchangés : rattachement à un patient **existant** uniquement, jamais de
   création.
3. **Pièces jointes (N)** — les cartes actuelles (nom, taille, badge « Document médical »,
   téléchargement). Un clic sur une carte ouvre l'aperçu dans la zone de lecture.
4. **Étiquettes** — les puces et l'ajout d'une étiquette, avec le même comportement qu'aujourd'hui.

### 4. Afficher / masquer le panneau

Règles arbitrées par l'humain le 2026-10-10.

- **Déplié à chaque ouverture de message.** Le masquer ne vaut que pour le message en cours. Ce choix
  n'est **pas mémorisé** d'un message à l'autre.
- **Masqué**, le panneau devient un **rail** d'environ 48 px, collé au bord droit :
  - un bouton « Afficher le panneau » ;
  - une icône par section présente, avec infobulle ;
  - une **pastille orange** sur l'icône Acquittement s'il est à traiter ;
  - un **compteur** sur l'icône Pièces jointes.
  - Un clic sur une icône rouvre le panneau sur cette section.
- **Écran étroit** : quand la largeur disponible pour la lecture (zone de lecture + panneau) est
  **inférieure à 1 000 px**, le message s'ouvre **panneau réduit au rail**. C'est le cas d'un portable
  1366 px avec la liste des messages ouverte, ou de l'iframe Weda. Un clic ouvre alors le panneau
  **par-dessus** le contenu. Il se referme par un clic à l'extérieur, par Échap ou par son bouton.
- **Masquer le panneau ne vaut jamais acquittement.** L'état « à traiter » reste signalé par la puce
  de l'en-tête et par la pastille du rail.
- Clavier : le bouton afficher / masquer est atteignable au clavier, et il annonce son état
  (déplié / masqué) aux technologies d'assistance.

### Hors périmètre

- Les règles métier de l'acquittement (task-028), du rattachement (task-012, task-331) et de l'import
  Weda (task-357, task-363) sont **inchangées** : seul leur emplacement change.
- Le rendu du document CDA (`medical-html-frame`), le contenu des onglets et l'impression du message
  sont inchangés.
- La rédaction (`mss-mail-compose`) et l'assistant (`mss-ai-chat-panel`), qui remplacent la lecture en
  entier, sont inchangés.
- `client-mobile` et `client-blazor` : voir « Pourquoi un seul front ».

## Definition of Done

- [ ] `client-angular` : `npm ci && npm run build` (0 erreur) et `npm test` (0 échec, hors flaky
  préexistants documentés). Le lint `scope:mss` ne compte aucune nouvelle erreur.
- [ ] **Règle 1b — test d'intégration** : non applicable. **Aucun comportement atteignable par un
  endpoint ne change** : aucune route, aucun contrat, aucun appel nouveau. Le test d'intégration du
  parcours est son scénario e2e (ci-dessous).
- [ ] **Tests de composant Angular**, vus rouges d'abord :
  - [ ] panneau **déplié** à l'ouverture d'un message, avec une largeur disponible ≥ 1 000 px ;
  - [ ] « Masquer le panneau » → rail affiché, sections masquées. **Ouvrir un autre message** → le
    panneau est de nouveau déplié ;
  - [ ] largeur disponible < 1 000 px → ouverture **en rail**. Un clic sur une icône ouvre le panneau
    par-dessus, sur la section visée, et Échap le referme ;
  - [ ] acquittement à traiter → la section Acquittement est en premier, la puce « Acquittement à
    traiter » est dans l'en-tête et la pastille est sur l'icône du rail une fois le panneau masqué ;
    aucun acquittement → aucune des trois n'apparaît ;
  - [ ] deux documents à acquitter → deux entrées dans la section, et **aucun** bandeau
    d'acquittement au-dessus du contenu ;
  - [ ] un clic sur la puce « N pièce(s) jointe(s) » (ou « Acquittement à traiter ») ouvre le panneau,
    même masqué, sur la section correspondante ;
  - [ ] un clic sur une pièce jointe → aperçu dans la zone de lecture, puis retour au message ;
  - [ ] les actions de « Plus d'actions » (Exporter, Déplacer vers, Supprimer…) déclenchent le même
    comportement qu'avant ;
  - [ ] les sections vides (aucun patient, aucune pièce jointe, aucune étiquette) ne s'affichent pas.
- [ ] **Un seul conteneur de défilement** pour le contenu : `mail-body` n'ouvre plus de second
  conteneur. Un test de composant affirme qu'il n'y a qu'un élément défilant dans la zone de lecture.
- [ ] Scénario **E2E-DETAIL-004** ajouté en **v1** dans `Api/Mail/e2e/scenarios.yml`, puis implémenté
  dans `client-angular` :
  - titre : « Lire un message avec le panneau d'actions, le masquer puis le retrouver au message
    suivant » ;
  - `clients` : `angular: requis`, `mobile: non-applicable`. Raison fonctionnelle : la lecture mobile
    n'a pas de panneau latéral ;
  - seed : `cr-bio-a-acquitter`. Si ce seed ne porte ni pièce jointe ni étiquette, en ajouter une au
    seed ou en créer un dédié ;
  - attendu, assertion **mesurée** : en fenêtre 1366×768, le haut des onglets du contenu est à
    **≤ 160 px** du haut de la zone de lecture, avec acquittement, étiquette et pièce jointe présents.
    La section Acquittement est visible dans le panneau. « Masquer le panneau » affiche le rail avec
    la pastille. Ouvrir le message suivant redéplie le panneau.
- [ ] **Non-régression e2e côté Angular** : E2E-BIO-001, E2E-ATTACH-001, E2E-PATIENT-002 (v2),
  E2E-WEDA-002, E2E-DETAIL-001/002/003 et E2E-MAIL-005 restent **verts**, à **version inchangée**.
  Le comportement attendu ne change pas, seul l'emplacement des actions change. Si une implémentation
  Angular doit être adaptée (ouvrir le panneau, menu « Plus d'actions »), l'adaptation ne doit
  **jamais affaiblir l'assertion** (`conventions/e2e.md`). La largeur de la fenêtre des suites
  Angular est vérifiée : sous 1 000 px de lecture, le panneau s'ouvre en rail.
- [ ] `data-testid` **existants conservés** sur tous les boutons et blocs déplacés (`reply-btn`,
  `biology-ack-*`, `weda-import-open`, `manual-attachment-row-*`, `move-mail-dropdown`…). Nouveaux
  `data-testid` en kebab-case : `mail-side-panel`, `mail-side-panel-toggle`, `mail-side-panel-rail`,
  `mail-side-panel-section-{ack|patient|attachments|tags}`, `mail-rail-icon-{…}`,
  `mail-summary-chip-{ack|attachments}`, `mail-more-actions`.
- [ ] Libellés FR en dur, comme le reste de `mss-lib` (pas d'i18n dans ce projet) : « Actions &
  dossier », « Masquer le panneau », « Afficher le panneau », « Plus d'actions », « Acquittement à
  traiter ».
- [ ] **Aucune INS / NIR / NIA affichée** dans le panneau. La section Patient affiche les mêmes traits
  d'identité qu'aujourd'hui, ni plus ni moins.
- [ ] Captures avant / après (panneau ouvert, panneau masqué, écran étroit) jointes au `## Develop log`.

## Manual Test Plan

1. Backend : `cd Api/Mail && dotnet run --project src/AppHost`.
   - Angular : `cd Client/Angular/front && npm start`, sur la branche choisie par l'humain (code-only).
2. **Lecture d'abord.** Fenêtre de 1366×768, liste des messages affichée. Ouvrir un **compte rendu de
   biologie à acquitter** qui porte une étiquette et une pièce jointe.
   - Attendu : l'en-tête tient sur deux lignes, puis viennent les puces « Bio », « Acquittement à
     traiter » et « 1 pièce jointe ».
   - Les onglets et le **début du compte rendu** sont visibles **sans faire défiler**.
   - À droite, le panneau « Actions & dossier » montre dans l'ordre : Acquittement (À TRAITER),
     Patient, Pièces jointes (1), Étiquettes.
3. **Un seul défilement.** Faire défiler un compte rendu long : une seule barre de défilement, et les
   onglets restent visibles en haut.
4. **Masquer.** Cliquer « Masquer le panneau ».
   - Attendu : le rail apparaît avec la pastille orange sur l'icône Acquittement, et la lecture
     s'élargit.
   - Cliquer l'icône Pièces jointes du rail : le panneau se rouvre sur cette section.
5. **Message suivant.** Masquer de nouveau, puis ouvrir un autre message : le panneau est **déplié**.
6. **Acquitter depuis le panneau.** Choisir « Rappel patient », puis « Marquer comme résolu ».
   - Attendu : même confirmation qu'avant, puis la puce « Acquittement à traiter » et la pastille
     disparaissent.
7. **Plusieurs documents.** Ouvrir un message portant deux comptes rendus de biologie : deux entrées
   dans la section Acquittement, et aucun bandeau au-dessus du contenu.
8. **Pièce jointe.** Cliquer la carte de la pièce jointe : l'aperçu s'affiche dans la zone de lecture.
   « Retour au message » ramène le compte rendu.
9. **Patient / Weda.** Sur un message à rattacher : le rattachement en attente et le rattachement
   manuel sont dans la section Patient. Avec le flag Weda actif, le dossier Weda et l'import sont
   dans la même section, avec le même comportement qu'avant.
10. **Écran étroit.** Réduire la fenêtre (ou ouvrir la messagerie dans Weda) : le message s'ouvre en
    rail. Cliquer une icône : le panneau s'ouvre **par-dessus** le contenu, et Échap le referme.
11. **Actions.** Répondre, Transférer, Imprimer et Synthèse IA sont visibles. Exporter, Déplacer vers
    et Supprimer sont dans « Plus d'actions ». Chacune fait la même chose qu'avant.
12. **Alertes du message.** Sur un doublon ou un message supprimé ailleurs, l'alerte reste au-dessus
    du contenu, en ligne fine.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — messagerie MSSanté intégrée au logiciel
- **Exigences DSR honorées** : non applicable. Réorganisation de l'écran de lecture : aucune exigence
  DSR nouvelle, et les fonctions existantes (acquittement, rattachement, import) restent conformes à
  leurs US d'origine.
- **INS** : non applicable. Aucune INS manipulée ni ajoutée. La section Patient reprend **à
  l'identique** les traits affichés aujourd'hui. L'affichage de l'INS proposé par la maquette Stitch
  est **explicitement écarté**.
- **Authentification PS** : inchangée — PSC / e-CPS de la session
- **Habilitations** : inchangées (boîte sélectionnée du praticien)
- **Interop CI-SIS** : non applicable. Le rendu du CR de biologie (CDA r2, volet CR-BIO) est inchangé,
  sans ajout ni réinterprétation du contenu.
- **Tracé PGSSI-S** : inchangé. Les actions d'acquittement, de rattachement et d'import sont
  journalisées comme aujourd'hui. Afficher ou masquer le panneau n'est pas un évènement métier et
  n'est **pas** journalisé.
- **Consentement patient** : non applicable — aucun partage nouveau
- **Référentiels métier** : aucun nouveau. Les codes LOINC du CR restent ceux du document.
- **Hébergement HDS** : inchangé — aucune donnée nouvelle stockée ni transmise. Aucun état du panneau
  n'est persisté.
- **AIPD / impact RGPD** : inchangée — aucune finalité nouvelle

## Branches
- `api-mail` (pushed) : feat/task-364-lecture-panneau-actions — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-364-lecture-panneau-actions (catalogue e2e uniquement)
- `client-angular` (code-only) : la forge écrit le code sur la branche checked out dans `Client/Angular/` — instantané au `/start` (2026-10-10) : `feature/nova-rewriting-mss-weda-integration`. L'humain gère branche, commit, push, PR TFS.

## Timings

*(généré par `tools/timing/report.sh --task task-364 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 17 s | — | — | — | — |
| /develop | ok | 30 min 50 s | 4 (47 s) | 4 (1 min 27 s) | — | client-angular 4B/2T, api-mail 0B/2T |
| /sonar | skipped | 0.4 s | — | — | — | diff api-mail = e2e/scenarios.yml seul, aucun C# |
| /lint-angular | ok | 20 s | — | — | — | — |
| /lint-mobile | skipped | 0.4 s | — | — | — | client-mobile non touché |
| /e2e | failed | 0.4 s | — | — | — | outillage : ports 5052 et 4200 tenus par la session de dev |
| **Total cycle** | | **31 min 30 s** | **4 (47 s)** | **4 (1 min 27 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : lint ×1 (9.1 s)

## Develop log

- **Repos touchés** : `api-mail` (catalogue e2e seulement), `client-angular` (code-only).
- **DTOs / interop / sdk** : aucun changement.
- **Commits** :
  - api-mail : `941f9c4a` test(e2e): catalogue E2E-DETAIL-004 (poussé sur `feat/task-364-lecture-panneau-actions`).
  - client-angular : **non commité**, sur `feature/nova-rewriting-mss-weda-integration`, à commiter et pousser sur TFS par l'humain.
    - Nouveaux : `components/mail-side-panel/` (composant, gabarit, styles, spec), `components/mail-detail/mail-detail.side-panel.spec.ts`.
    - Modifiés : `mail-detail.component.{ts,html,scss}`, `mail-body.component.scss`, `mail-tag.component.html` (2 `data-testid`), `manual-attachment-panel.component.ts` (export de `isAttachedByHand`), `services/mail-state.service.ts` (helper `withBiologyAck`), `e2e/mss-e2e/specs/functional.e2e.ts`, `e2e/mss-e2e/support/weda.ts`.
- **Ce qui est fait** :
  - en-tête compact sur deux lignes, barre d'outils fusionnée (icônes avec infobulle), menu « Plus d'actions » (annuler et remplacer, exporter, déplacer, signaler, texte brut, supprimer) ;
  - puces de synthèse (acquittement à traiter, pièces jointes, étiquettes), chacune ouvre sa section ;
  - panneau `mss-mail-side-panel` (acquittement, patient, pièces jointes, étiquettes), déplié à chaque message, rail quand il est masqué, rail puis superposition sous 1 000 px de lecture, Échap et clic dans la lecture pour le refermer ;
  - aperçu de pièce jointe dans la zone de lecture (« Retour au message ») ;
  - un seul défilement : `min-height: 60vh` / `70vh` retirés, chaîne flex `min-height: 0`.
- **Build / tests locaux** : `nx build weda2` ✓ ; `nx run-many -t test` ✓ (11 projets, 0 échec) ; ESLint des fichiers touchés : 0 erreur. api-mail : `ScenarioCatalogTests` 17/17 ✓ (en `-c Release` : `bin/Debug` verrouillé par la session de dev de l'humain).
- **Preuves par mutation (tests de composant)**, chacune rouge sur l'assertion visée puis restaurée (marqueur `MUTATION` compté à 1, puis 0) :
  - M1, pas de redéploiement par message → 2 tests du panneau rouges ;
  - M2, Échap qui replie toujours → « Échap ne replie pas un panneau déplié » rouge ;
  - MD1b, acquittement non recopié dans le contenu → « Marquer comme résolu fait disparaître la puce » rouge ;
  - MD3b, seuil `<=` → « le seuil de lecture étroite est 1 000 px » rouge ;
  - MD4, clic dans la lecture sans effet → test de lecture étroite rouge ;
  - MA1, section Pièces jointes jamais présente → test « une pièce jointe » rouge ;
  - MT1, un bandeau d'acquittement remis dans la lecture → « rien au-dessus du contenu » rouge.
- **E2E (Step 6b)** :
  - catalogue d'abord : E2E-DETAIL-004 v1 (`angular: requis`, `mobile: non-applicable`) ;
  - test Angular ajouté (`functional.e2e.ts`) ;
  - parcours existants adaptés **sans affaiblir leurs assertions** : BIO-001, ATTACH-001, PATIENT-002, WEDA-002, DRAFT-002 ouvrent la section du panneau (helper `openSidePanelSection`) ; MAIL-004, MAIL-005, DETAIL-002 passent par le menu (helper `moreAction`) ;
  - `npx tsc -p e2e/mss-e2e/tsconfig.json` ✓.
  - **Preuve par mutation du parcours E2E-DETAIL-004 : à faire au lancement de la voie par `/e2e`**. Elle n'est pas jouable en `/develop` : la suite exige le backend e2e et ses ports, tenus par la session de dev de l'humain (AppHost + `nx serve weda2`).
- **Passe qualité (/simplify)** :
  - appliquée (code-only, non commitée) sur client-angular :
    - `mergedAttachments` calculé une fois (`computed`) au lieu de quatre fois par rendu ;
    - la largeur de lecture mesurée par le panneau, un booléen qui ne réagit qu'au seuil ;
    - l'acquittement recopié dans le contenu chargé via `withBiologyAck`, partagé avec `applyBiologyAck`, au lieu d'un état parallèle ;
    - libellés et icônes des sections centralisés (`SIDE_PANEL_SECTION_META`) ;
    - helper e2e `openPendingBiologyReport` ;
    - style `.export-menu-container` et classe d'hôte inutilisés retirés ;
  - revalidé ensuite : build ✓, 11 projets ✓, lint 0 erreur, mutations rejouées ;
  - écarté :
    - la migration du menu vers `ds-dropdown-menu` : change le comportement clavier et de superposition, à traiter dans une US dédiée ;
    - le double propriétaire du remplissage du corps (CSS) : demande une vérification visuelle ;
  - api-mail : aucune simplification (diff YAML seul).
- **Écarts à la DOD, pour arbitrage en revue** :
  1. **Section Étiquettes toujours présente**, même sans étiquette : elle porte le bouton d'ajout. La masquer empêcherait d'ajouter une première étiquette (« même comportement qu'aujourd'hui » de l'objectif).
  2. **Pas de repli section par section.** Les sections Acquittement et Pièces jointes portent déjà leur propre en-tête (l'acquittement a son bouton de masquage), et un second en-tête doublerait les titres.
  3. **E2E-DETAIL-004 en 1366×768 joue le mode rail.** La lecture y fait environ 690 px, sous le seuil de 1 000 px de l'objectif §4. La partie « panneau déplié, masqué puis redéplié » se joue donc en 1920×1080. L'assertion « contenu ≤ 160 px » est faite en 1366×768.
  4. **« Un seul défilement » est prouvé par le parcours e2e**, qui compte les régions défilantes dans un vrai navigateur, et non par un test de composant : jsdom ne calcule pas la mise en page.
  5. **Fenêtre e2e 1440 px** : le panneau y est en rail, et les parcours ouvrent la section voulue comme le ferait le praticien.
- **Incident outillage** : un `git add -N` (intention d'ajout) a été lancé par erreur sur `client-angular` pendant la passe qualité, puis annulé aussitôt (`git reset` des deux chemins). Index vérifié vide, arbre inchangé.
- **DOD self-check** : build/tests ✓ ; tests de composant listés ✓ (sauf écarts 2 et 4) ; scénario catalogué + implémenté ✓ (preuve par mutation e2e en attente de `/e2e`) ; `data-testid` existants conservés ✓ ; libellés FR en dur ✓ ; aucune INS affichée dans le panneau ✓ ; captures avant / après : différées à `/e2e` et au HAG (serveurs de dev).
- **Next step** : `/sonar task-364`

## Sonar log

- **Mode** : A (chaîné).
- **Diff api-mail vs `develop`** : `e2e/scenarios.yml` seul, **aucun fichier C#**. Le new code Sonar est vide, donc la phase 1 (new code bloquant) est sans objet.
- **Phase 2 (dette legacy, optionnelle)** : non lancée. Une analyse complète (build + tests OpenCover + scanner) ne porterait sur aucune ligne de la task. Elle buterait aussi sur `src/Api/bin/Debug`, verrouillé par la session de dev de l'humain (5 `mss.mail.api` sous AppHost).
- **KPIs qualité** : non mesurés sur ce cycle, puisqu'aucune analyse n'a été lancée. Quality Gate : inchangée par la task (aucun code analysé modifié).
- **Itérations** : 0 / 5 (skipped — aucun code C# touché).
- **Conventions** : aucune entrée `conventions/csharp.md` (rien corrigé).
- **Next step** : `/lint-angular task-364`

## Lint log

- **Mode** : A (chaîné). Branche `feature/nova-rewriting-mss-weda-integration`, base `origin/next`, périmètre lint `tag:scope:mss`.
- **État de départ** : `nx affected -t lint` → **0 erreur**, avertissements seulement (1 + 50 + 14 + 43 sur les projets lintés). Ce sont les avertissements déjà présents du module, dont `jsdoc/require-example` et `max-lines`. Aucun ne porte sur `mail-side-panel`.
- **Itérations** : 0 / 5. La condition d'arrêt « zéro erreur » est atteinte d'emblée, sans `--fix`. Aucun fichier hors périmètre n'a été touché.
- **Build / test** : déjà verts sur l'arbre courant, revalidés après la passe qualité (`nx build weda2` ✓, `nx run-many -t test` ✓ 11 projets). Arbre inchangé depuis.
- **Conventions** : aucune entrée `conventions/angular.md` (rien corrigé à la main).
- **Git** : aucune opération hors `git fetch origin next`.
- **Next step** : `/lint-mobile task-364`

## Lint mobile log

- no client-mobile change → skipped /lint-mobile : `client-mobile` absent des `**Repos**`, arbre propre sur `develop`.
- **Next step** : `/e2e task-364`

## E2E log

| Voie | Déclenchée par | Résultat |
|---|---|---|
| mobile | api-mail touché | **non jouée — outillage** : port 5052 tenu par l'AppHost de dev (dcp PID 51296) |
| angular | api-mail + client-angular touchés | **non jouée — outillage** : ports 5052 (AppHost de dev) et 4200 (`nx serve weda2` PID 8716) tenus |

- **Verdict** : 🔴 **bloqué (outillage)**. La non-régression n'est pas prouvée. Porte `gate` non lancée (aucun rapport exécuté).
- **Dépendances** : `@playwright/test` présent dans les deux clients ; mobile aligné sur `origin/develop` (0 commit de retard). Aucun `npm ci` lancé, puisque votre serveur Angular tourne.
- **Démontage** : rien n'a été monté, aucun conteneur e2e créé.
- **Suite** : `questions/task-364.md`. Arrêter la session de dev, puis relancer `/e2e task-364`.
