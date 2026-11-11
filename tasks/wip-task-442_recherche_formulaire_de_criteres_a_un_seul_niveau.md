# todo-task-442.md — Recherche : formulaire de critères à un seul niveau

**Repos**: client-angular, api-mail
**Dependencies**: aucune
**Epic**: E023
**EpicTitle**: Expérience de recherche
**Priorité**: EPIC E023, demandée par l'humain le 2026-11-10. Première marche de la refonte de la recherche : un
formulaire de critères simple, qu'on remplit puis qu'on lance, et qui se ferme pour laisser voir les résultats.

> **Origine.** Analyse du 2026-11-10 avec l'humain, à partir de la recherche d'Outlook 365 : toutes les propositions
> ont été acceptées. weda2 d'abord ; le mobile suit le même modèle (task-450). `api-mail` figure dans les Repos pour le
> catalogue e2e.

## Ce qui est établi

Lecture du code au 2026-11-10 (`Client/Angular/front/libs/mss/src/features/mail/components/mail-search/`) :

- La fenêtre sous la barre de recherche empile l'historique, des filtres rapides (Statut, Contenu médical, Période),
  puis un **second panneau** « Recherche avancée » (De, À ou Cc, Objet, Type de document), atteint par un bouton et
  quitté par une flèche retour.
- Le bouton « Rechercher » n'existe que dans le panneau avancé. Ailleurs, la recherche part sur Entrée ou au clic d'un
  filtre : le médecin ne sait pas quand elle part.
- Rien ne remet le formulaire à vide sans effacer aussi la recherche affichée : la croix de la barre fait les deux.
- Les boutons sont des `<button>` stylés localement, pas les composants du design system (`ds-*`).

## Objective

Le médecin ouvre la fenêtre de recherche, compose ses critères dans **un seul formulaire**, puis lance la recherche.
La fenêtre se ferme et laisse voir les résultats.  
Si le médecin clique en dehors de cette fenètre, elle se ferme automatiquelent.

Règles :
- **Un seul niveau** : les filtres rapides et les critères avancés (De, À ou Cc, Objet, Type de document, Période,
  Statut, Contenu médical) sont dans le même formulaire, groupés par sections titrées. Plus de second panneau ni de
  flèche retour.
- **Deux boutons en bas du formulaire**, composants du design system :
  - **« Lancer la recherche »** (bouton principal) ;
  - **« Réinitialiser les paramètres »** (bouton secondaire).
- **Rien ne part avant « Lancer »** : un clic sur un filtre le coche ou le décoche, sans lancer de recherche. La touche
  Entrée dans le champ de saisie équivaut à « Lancer la recherche ».
- **Lancer ferme la fenêtre** et affiche les résultats.
- **« Lancer » sans aucun critère** : le bouton est inactif tant que ni texte ni critère n'est saisi.
- **« Réinitialiser les paramètres »** vide le texte et tous les critères du formulaire. Il ne ferme pas la fenêtre,
  ne lance rien, et ne touche pas aux résultats déjà affichés.
- **Rouvrir la fenêtre** après une recherche montre les critères de la recherche affichée, pour les modifier.
- **Fermer sans lancer** (Échap, clic en dehors) : les critères modifiés et non lancés sont abandonnés ; la recherche
  affichée ne change pas.
- **Historique des recherches** : inchangé, en tête de la fenêtre, jusqu'à task-449 qui le déplace dans les
  suggestions.
- La croix de la barre garde son rôle actuel (effacer la recherche affichée) jusqu'à task-445, qui la remplace par
  « Fermer la recherche ».

### Hors périmètre

- Les nouveaux critères médicaux : task-443.
- Le mode « Résultats de recherche » : task-445.
- Le mobile : task-450.

## Definition of Done

- [ ] Build passes (0 errors) : weda2 (`nx build weda2`)
- [ ] Tests pass (0 failures) : `nx test weda2`, `nx test mss-lib` (ligne « Tests » lue : des specs ont bien tourné)
- [ ] Tests de composant : un filtre cliqué ne lance aucune recherche ; « Lancer » lance une recherche portant
      **tous** les critères cochés et ferme la fenêtre ; Entrée équivaut à « Lancer » ; « Lancer » inactif sans critère ;
      « Réinitialiser » vide tout sans fermer ni lancer, et laisse les résultats affichés ; fermer sans lancer abandonne
      les critères modifiés ; rouvrir montre les critères de la recherche affichée ; chacun vu rouge par mutation
- [ ] Boutons « Lancer la recherche » et « Réinitialiser les paramètres » réalisés avec les composants `ds-*` du design
      system (aucun bouton stylé localement pour ces deux actions)
- [ ] **Scénario e2e** : `E2E-SEARCH-001` passe en **version 2** dans `Api/Mail/e2e/scenarios.yml` — titre « Composer
      ses critères puis lancer la recherche », attendu : cocher un filtre ne lance rien ; « Lancer la recherche » ferme
      la fenêtre et affiche les résultats ; « Réinitialiser les paramètres » vide le formulaire. Clients : angular
      requis, mobile requis avec **divergence temporaire** (raison : « le mobile adopte le formulaire à un seul niveau
      avec la refonte mobile de la recherche », tache : task-450). Implémenté dans weda2, vu rouge par mutation ;
      `E2E-SEARCH-002` et `003` restent verts
- [ ] `data-testid` sur chaque élément interactif ajouté ou déplacé (`mail-search-launch`, `mail-search-reset`, sections)
- [ ] Aucune chaîne en dur hors des conventions de libellés de weda2 ; aucune donnée de santé dans les libellés
- [ ] client-angular : code-only, aucun commit (l'humain gère la branche et TFS)
- [ ] **Prévention (règle d'or)** : consigne dans `conventions/angular.md` : un formulaire de critères ne déclenche
      rien avant son bouton d'action ; ses boutons d'action sont ceux du design system

## Manual Test Plan

1. Lancer le backend : `cd Api/Mail/src/AppHost && dotnet run`. Lancer weda2 : `cd Client/Angular/front && npm start`.
2. Se connecter avec la CPS de test, ouvrir la Boîte de réception, cliquer dans la barre de recherche.
3. Vérifier :
   - un seul formulaire, sans bouton « Recherche avancée » ni flèche retour ; les champs De, À ou Cc, Objet et Type de
     document sont dans le formulaire ;
   - en bas, « Lancer la recherche » et « Réinitialiser les paramètres », au style du design system ;
   - « Lancer » est grisé tant que rien n'est saisi.
4. Cocher « Non lus » puis « Pièces jointes » : la liste ne change pas.
5. Taper `psoriasis`, cliquer « Lancer la recherche » : la fenêtre se ferme, les résultats s'affichent.
6. Rouvrir la fenêtre : `psoriasis`, « Non lus » et « Pièces jointes » sont présents. Cliquer « Réinitialiser les
   paramètres » : le formulaire est vide, la fenêtre reste ouverte, les résultats derrière n'ont pas changé.
7. Appuyer sur Échap : la fenêtre se ferme, les résultats de `psoriasis` sont toujours là.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du praticien)
- **Vague Ségur** : hors Ségur — ergonomie de la recherche
- **Exigences DSR honorées** : non applicable — aucune exigence DSR ne porte sur la forme du formulaire
- **INS** : non applicable — aucun identifiant patient manipulé par le formulaire
- **Authentification PS** : inchangée — PSC (e-CPS), niveau eIDAS substantiel
- **Habilitations** : inchangées — accès à la boîte ouvert par le verdict de l'opérateur MSSanté (règle 14)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé — chaque recherche lancée est tracée côté serveur (`MailSearch`) au nom de la personne
  réelle, 3 653 jours ; cocher un filtre sans lancer n'est pas un acte et n'est pas tracé
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non applicable au client — aucune donnée stockée
- **AIPD / impact RGPD** : inchangé

## Branches
- `api-mail` (pushed) : feat/task-442-recherche-formulaire-de-criteres-a-un — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-442-recherche-formulaire-de-criteres-a-un (catalogue e2e)
- `client-angular` (code-only) : la forge écrit le code sur la branche extraite dans `Client/Angular/` (au `/start` : `feature/nova-mss-weda-integration`, propre) — l'humain gère branche, commit, push, PR TFS

## Sonar log

**Mode A** (chaîné depuis `/develop`), `api-mail`, branche `feat/task-442-…`, 1 analyse (build `Release`).
La branche ne porte qu'un changement de `e2e/scenarios.yml`. Ce fichier n'appartient à aucun projet MSBuild, et le
scanner .NET ne l'indexe pas. L'analyse est jouée quand même : le playbook ne prévoit le skip que pour une branche
sans commit. Son coût est mesuré pour décider plus tard d'un skip propre dans ce cas (voir le rapport de fin de cycle).

SonarQube local était arrêté (conteneurs `sonarqube` et `sonarqube_db` sortis en 255, sans doute au redémarrage de
Docker). Ils ont été relancés avant l'analyse.

### KPIs qualité (baseline → final)

| KPI | Baseline (analyse du 2026-11-10, task-437) | Final |
|---|---|---|
| Quality Gate | OK | **OK** |
| Bugs / Vulnérabilités | 0 / 0 | 0 / 0 |
| Code smells | 0 | **0** |
| Hotspots à revoir | 0 | 0 |
| Couverture globale | 97,8 % | **97,8 %** |
| Couverture du nouveau code | — | **96,0 %** (période de référence du projet, pas la task) |
| Duplication | 0,4 % | 0,4 % |
| Ratings (fiabilité / sécurité / maintenabilité) | A / A / A | A / A / A |

**Phase 1 — nouveau code** : 0 issue. Rien à corriger, aucune itération supplémentaire.

**Phase 2 — dette ancienne** : 0 issue ouverte sur le projet.

**Tests de l'analyse** : domain 210, application 4 054, infrastructure 737, api 1 375, intégration 1 232
(+ 16 ignorés), 0 échec, aucun plantage masqué (`FATAL` / `Test Run Aborted` absents).

**Coût** : 11 min 25 s (build 47 s, tests 8 min 25 s, scans 47 s), pour une branche dont aucun fichier n'est analysé.

**Conventions** : aucune règle Sonar corrigée à la main, aucune entrée.

## Lint log

**Mode A** (chaîné depuis `/sonar`), `client-angular` code-only, branche extraite
`feature/nova-mss-weda-integration`, base `origin/next`. Aucune opération git d'écriture.

Lint lancé par le contournement consigné au playbook (task-367) : `nx run-many -t lint -p mss-lib`, puis
`eslint --format json` sur les fichiers `.ts` de la task. Les `.html` et `.spec.ts` sont hors du périmètre
d'ESLint. Le SCSS passe par `stylelint`.

| Mesure | Résultat |
|---|---|
| Erreurs ESLint (mss-lib + fichiers de la task) | **0** |
| Avertissements mss-lib | 48, dont 1 sur un fichier de la task |
| `mail-search.component.ts` | 1 avertissement `max-lines` (789 lignes ; **723 avant la task**, déjà au-dessus de 500) |
| `e2e/mss-e2e/specs/functional.e2e.ts` | 5 avertissements, tous antérieurs (`max-lines`, `jsdoc/require-example` lignes 800, 828, 3663, 3674 ; le test de la task est vers la ligne 1150) |
| `stylelint` sur `mail-search.component.scss` | 0 |

**Itérations** : 0. Aucune erreur, et aucun avertissement sur une ligne ajoutée. Les 8 avertissements que
l'auto-fixer saurait corriger sont dans des fichiers hors de la task : les corriger ajouterait au diff TFS
de l'humain des changements sans rapport avec la recherche.

**Conventions** : aucune règle corrigée à la main, aucune entrée. Le dépassement `max-lines` du composant
(+66 lignes) est signalé au rapport de fin de cycle ; le découpage du composant est hors de l'objet de la task.

## Lint mobile log

- skipped — client-mobile non touché (absent des `**Repos**`). Le parcours mobile de `E2E-SEARCH-001` reste en v1 sous divergence temporaire (task-450).

## Timings

*(généré par `tools/timing/report.sh --task task-442 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 14 s | — | — | — | — |
| /develop | ok | 21 min 02 s | 3 (1 min 30 s) | 2 (1 min 02 s) | — | client-angular 2B/2T, api-mail 1B/0T |
| /sonar | ok | 11 min 25 s | 1 (47 s) | 5 (8 min 25 s) | 2 (47 s) | 1 itération(s), api-mail 1B/5T, api-mail touché par e2e/scenarios.yml seul : analyse complète jouée, rien à indexer |
| /lint-angular | ok | 58 s | — | — | — | 0 erreur ; avertissements antérieurs |
| /lint-mobile | skipped | 0.4 s | — | — | — | client-mobile non touché |
| **Total cycle** | | **33 min 40 s** | **4 (2 min 17 s)** | **7 (9 min 27 s)** | **2 (47 s)** | |

Autres commandes mesurées : lint ×1 (9.7 s)

## Develop log

**Repos touchés** : `client-angular` (code-only, non commité), `api-mail` (catalogue e2e seulement).

### client-angular — `libs/mss/src/features/mail/components/mail-search/`
- `mail-search.component.ts` : le panneau « Recherche avancée » disparaît (`showAdvanced`,
  `openAdvanced`, `closeAdvanced`, `applyAdvancedAndSearch` retirés). Les bascules de filtres ne
  lancent plus rien. `launch()` lance avec tous les critères puis ferme ; `canLaunch` le désactive
  sans critère ; Entrée appelle `launch()`. `resetParameters()` vide sans fermer ni lancer.
  Un instantané `appliedCriteria` (type `SearchCriteria`) retient les critères de la recherche
  affichée : `closeDropdown()` y revient, ce qui abandonne le brouillon. Les requêtes persistées
  (rejeu de l'historique, recherche retrouvée par une liste recréée) passent par la fonction pure
  `criteriaFromRequest`.
- `mail-search.component.html` / `.scss` : un seul formulaire (historique, statut, médical,
  période, critères De / À ou Cc / Objet / Type de document sur 15 types), pied collant avec deux
  `ds-button` : `mail-search-reset` (stroke) et `mail-search-launch` (default, icône search,
  inactif sans critère). Les puces portent `aria-pressed`.
- `mail-search.component.spec.ts` : réécrit, **18 tests** (10 neufs task-442, plus date exclusive,
  `clearAll`, course `switchMap`, tests task-377).
- `e2e/mss-e2e/specs/functional.e2e.ts` : `recherche — composer ses critères puis lancer la
  recherche`, `scenario('E2E-SEARCH-001', 2)`. Il compte toutes les requêtes sémantiques émises :
  rien après deux puces ; exactement une après « Lancer », qui porte le texte, `hasAttachments`
  et `isRead:false` ; le formulaire se ferme ; à la réouverture, « Non lus » est pressé ;
  « Réinitialiser » vide sans fermer ni relancer.

### Preuve par mutation (spec du composant, 18 tests)
| Mutation | Résultat |
|---|---|
| M1 un filtre lance la recherche | 5 rouges |
| M2 Lancer ne ferme pas | 2 rouges |
| M3 Entrée ne lance pas | 1 rouge |
| M4 Lancer toujours actif | 1 rouge |
| M5 Réinitialiser efface les résultats | 1 rouge |
| M6 fermer garde le brouillon | 2 rouges |
| M7 rouvrir vide le formulaire | 1 rouge |

Code restauré : 18/18 verts. Mutations rejouées **après** la passe qualité.

### Passe qualité §Q (/simplify, 2 relectures)
Appliqué :
- `criteriaFromRequest` (fonction pure) remplace `applyCriteria` : une seule liste de setters
  (`restoreCriteria`), plus d'aller-retour par `snapshotCriteria` au rejeu ;
- `canLaunch` porte seul le prédicat (`isCriteriaEmpty` retiré) ;
- `restoreCriteria` ne recopie plus les objets (les signaux ne sont jamais mutés) ;
- `onHistoryReplay` ferme sans restaurer un instantané qui vient d'être fixé ;
- e2e : plus d'attente fixe de 500 ms ni de `waitForRequest` qui doublait l'écouteur ;
  `expect.poll(() => sent.length).toBe(1)` ;
- commentaire périmé du catalogue des types.

Écarté :
- puces statut et médical en catalogue `@for` : refonte du gabarit hors de l'objet de la task ;
- style sur `[aria-pressed]` au lieu de la classe `--active` : la classe reste la convention du
  composant ;
- `id` des `ds-button` : requis par la convention `ds-button-id-requis`.

### Validation (après la passe qualité)
- `nx build weda2` : vert.
- `nx run-many -t test -p weda2 mss-lib` : **weda2 2683 tests**, **mss-lib 1497 tests**, 0 échec.
- ESLint : 0 erreur (avertissement `max-lines` préexistant sur le composant).
- Prettier : conforme ; fichiers en CRLF.

### api-mail
- `e2e/scenarios.yml` : `E2E-SEARCH-001` en **version 2**, « Composer ses critères puis lancer la
  recherche » ; divergence temporaire `mobile` (raison : le mobile adopte le formulaire à un seul
  niveau avec la refonte mobile de la recherche ; tache : task-450).

### Règle 1b
Aucun comportement atteignable par un endpoint ne change : le contrat de `POST /search/semantic`
et le service sont intacts. Le parcours frontend est prouvé par son scénario e2e (`E2E-SEARCH-001` v2).

### Prévention (règle d'or)
`conventions/angular.md` § `formulaire-qui-lance-avant-son-bouton`.
