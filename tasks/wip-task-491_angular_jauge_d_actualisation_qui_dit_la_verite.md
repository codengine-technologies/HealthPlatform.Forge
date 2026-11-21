# todo-task-491.md — Angular : la jauge d'actualisation dit la vérité

**Repos**: client-angular
**Dependencies**: aucune
**Single frontend**: true

> Constat humain du 2026-11-21 : la jauge ronde affichée à côté du dossier sélectionné (« INBOX ») annonce 30 s,
> mais passe de 30 à 0 en 5 s chronométrées. Correction choisie par l'humain : l'option 2, une jauge qui affiche
> l'échéance réelle de la prochaine actualisation, plutôt qu'un simple arrêt de la minuterie qui fuit (option 1).
>
> **Une seule couche, justifiée** : la jauge n'existe que dans weda2. client-mobile n'en a pas (aucune occurrence d'un
> compte à rebours d'actualisation dans `Client/Mobile/src`), et le rythme d'actualisation côté api-mail ne change pas.
>
> task-462, d'abord posée en dépendance (arbre de weda2 partagé), a été annulée le 2026-11-21 : l'arbre de weda2 est
> revenu à son dernier commit, la dépendance est levée.

## Objectif

La jauge du dossier sélectionné montre le temps qui reste réellement avant la prochaine actualisation automatique de la
liste. Elle décompte une seconde par seconde, quel que soit le nombre de changements de dossier, et ne s'affiche que là
où une actualisation automatique a lieu.

### Ce qui est établi

- **La jauge a sa propre minuterie, sans lien avec l'actualisation**
  (`libs/mss/src/features/mail/components/mail-folder-item/mail-folder-item.component.ts`, `startRefreshTimer`) : un
  `interval(1000)` par ligne de dossier, lancé à la sélection et remis à `refreshIntervalSeconds` (30 s,
  `MSS_SYNC_INTERVAL_MS`) à chaque sélection.
- **Cause de l'accélération** : `stopRefreshTimer` ne fait que lever `timerRunning = false`. L'abonnement à
  `interval(1000)` n'est jamais résilié : il ne tombe qu'à la destruction de la ligne (`takeUntilDestroyed`), qui
  n'arrive pas puisque la liste suit `folder.path`. À chaque retour sur le dossier, `timerRunning` repasse à `true` :
  un nouvel abonnement s'ajoute, et les anciens se remettent à décompter. Après N retours, la jauge perd N+1 par
  seconde (30 → 0 en 5 s : 6 abonnements).
- **L'actualisation réelle est ailleurs** (`libs/mss/src/features/mail/mss-mail.component.ts`, `startPeriodicRefresh`) :
  `merge(interval(syncIntervalMs), newMailInSelectedFolder$())` avec `exhaustMap`, démarré **une fois** à
  l'initialisation de l'écran. Son rythme est fixe depuis ce démarrage ; il ne repart pas à la sélection d'un dossier.
  Une notification « nouveau mail » ajoute une actualisation sans décaler les suivantes.
- **Certains dossiers ne sont jamais actualisés** (`refreshSelectedFolder`) : les tags, les brouillons virtuels
  (`FolderSource.Drafts`) et la vue « Mails du patient » rendent `EMPTY`. La jauge s'y affiche pourtant aujourd'hui pour
  les dossiers non-tags.
- Aucun test ne couvre la jauge : pas de `mail-folder-item.component.spec.ts`, aucun scénario e2e.

### Règles

1. **Une seule horloge** : l'échéance de la prochaine actualisation périodique est tenue par l'écran mail, là où vit
   `interval(syncIntervalMs)`. Elle est exposée en lecture (un signal `nextRefreshAt`, instant absolu), remise à jour à
   chaque tick de la minuterie réelle. La ligne de dossier n'a plus de minuterie d'actualisation propre.
2. **Le chiffre affiché** est `ceil((nextRefreshAt − maintenant) / 1000)`, borné à `[0, intervalle]`. Le
   rafraîchissement de l'affichage chaque seconde est fait par **un seul** ticker pour tout l'écran, jamais un par
   ligne, et il est résilié à la destruction de l'écran.
3. **Le rythme d'actualisation ne change pas** : même intervalle, même `exhaustMap`, même déclenchement par
   notification. Une actualisation déclenchée par un nouveau message ne remet pas la jauge à 30 (elle ne décale pas
   l'échéance périodique). Changer de dossier ne la remet pas à 30 non plus : l'échéance est celle de l'écran.
4. **La jauge ne s'affiche que là où une actualisation automatique a lieu** : dossier IMAP sélectionné, hors tags, hors
   brouillons virtuels, hors vue « Mails du patient ». La condition est celle de `refreshSelectedFolder`, **écrite une
   seule fois** et lue par les deux.
5. L'infobulle (`Refresh dans {n}s`) suit le même chiffre. Son libellé passe en français : « Actualisation dans
   {n} s ».

## Definition of Done

- [ ] Build passes (`nx build weda2`, 0 erreur).
- [ ] Tests pass (`nx test mss-lib`, `nx test weda2` : 0 échec ; lancer `mss-lib` via PowerShell, cf. mémoire
      « Vitest mss-lib »).
- [ ] Tests de composant de `mail-folder-item` (Vitest, horloge simulée), chacun **vu rouge** sur le code d'avant
      (consigné au `## Develop log`) :
  - [ ] après 5 allers-retours de sélection sur le même dossier, la jauge perd **exactement 1** par seconde
        (rouge aujourd'hui : elle perd 6) ;
  - [ ] la jauge affiche le temps restant jusqu'à `nextRefreshAt` fourni, et non 30 à la sélection ;
  - [ ] aucune jauge sur un tag, sur les brouillons virtuels, ni dans la vue « Mails du patient ».
- [ ] Tests unitaires de l'écran mail (`mss-mail.component`) : `nextRefreshAt` avance d'un intervalle à chaque tick de
      la minuterie réelle ; une actualisation déclenchée par une notification ne le modifie pas ; le ticker d'affichage
      est unique et résilié à la destruction.
- [ ] La condition « ce dossier est actualisé automatiquement » n'existe qu'à un endroit (lue par
      `refreshSelectedFolder` et par la jauge).
- [ ] Plus aucun `interval(` dans `mail-folder-item.component.ts`.
- [ ] Libellé de l'infobulle en français : « Actualisation dans {n} s ».
- [ ] **Pas de scénario e2e** : la jauge est un indicateur, pas un geste du médecin, et une assertion sur un décompte
      en secondes dans Playwright serait instable (`conventions/e2e.md`). Le filet est le test de composant à horloge
      simulée ci-dessus. La voie Angular de `/e2e` est rejouée comme pour toute task client-angular.
- [ ] Prévention (règle d'or) : une entrée dans `conventions/angular.md` — « un abonnement lancé à chaque activation
      est résilié à chaque désactivation ; un drapeau ne suffit pas » — avec le contrôle mécanique associé.

## Manual Test Plan

- Lancer l'AppHost api-mail, puis weda2 : `cd Client/Angular/front && npm run start:weda2`, ouvrir la messagerie.
- Sélectionner INBOX : la jauge décompte une seconde par seconde (chronométrer 10 s).
- Cliquer sur un autre dossier puis revenir sur INBOX, cinq fois de suite : la jauge décompte toujours une seconde par
  seconde, et ne repart pas à 30 au retour.
- Quand la jauge atteint 0, la liste s'actualise (un message envoyé à la boîte entre-temps apparaît, ou une requête
  `GET …/folders/INBOX` part dans l'onglet réseau).
- Sélectionner un tag, puis « Brouillons » : aucune jauge.
- Survoler la jauge : l'infobulle dit « Actualisation dans {n} s », avec le même chiffre.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — indicateur d'interface de la messagerie, sans exigence DSR
- **Exigences DSR honorées** : non applicable — affichage côté client seulement
- **INS** : non applicable — aucun patient manipulé
- **Authentification PS** : inchangée — session PSC existante de weda2
- **Habilitations** : non applicable — aucun nouvel accès aux données
- **Interop CI-SIS** : non applicable — aucun échange
- **Tracé PGSSI-S** : aucun nouvel évènement — l'actualisation périodique ne change pas
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — aucune donnée de santé nouvelle, rien ne quitte le navigateur
- **AIPD / impact RGPD** : inchangé — aucun traitement nouveau

## Branches
- `client-angular` (code-only) : la forge écrit le code sur la branche extraite dans `Client/Angular/` (au /start : `feature/nova-mss-weda-integration`, arbre propre) — humain gère branche, commit, push, PR TFS

## Timings

*(généré par `tools/timing/report.sh --task task-491 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 12 s | — | — | — | — |
| /develop | ok | 12 min 01 s | 1 (19 s) | 2 (1 min 03 s) | — | client-angular 1B/2T |
| /review-code | ok | 4 min 25 s | — | — | — | — |
| **Total cycle** | | **16 min 39 s** | **1 (19 s)** | **2 (1 min 03 s)** | **0 (0.0 s)** | |

## Develop log

- **Repos touchés** : client-angular seul (code seul, branche `feature/nova-mss-weda-integration`, non commité). Aucun DTO,
  aucune interop, aucun dépôt poussé.
- **Conception** :
  - `MailStateService` (vit et meurt avec l'écran mail) tient `nextRefreshAt`, l'horloge de la jauge et
    `refreshSecondsLeft` (calculé). `startRefreshCountdown` arme **une** horloge d'une seconde, protégée contre un
    second appel, résiliée par `takeUntilDestroyed`. `scheduleNextRefresh` pose l'échéance et l'horloge au même
    instant : le décompte part de 30, jamais de 31.
  - `MssMailComponent.startPeriodicRefresh` démarre la jauge et repose l'échéance **à chaque tour de
    `interval(syncIntervalMs)`**, et seulement là : un rafraîchissement par notification ne la décale pas (règle 3).
    Le rythme d'actualisation est inchangé.
  - `isAutoRefreshed(folder)` (état) est la seule écriture de la règle « actualisé automatiquement » : lue par
    `refreshSelectedFolder`, par le filtre des notifications « nouveau mail » et par la jauge (règle 4).
  - `mail-folder-item` n'a plus de minuterie, ni `ngOnInit` / `ngOnChanges` : `refreshCountdown()` lit l'état,
    `showRefreshGauge()` exige dossier sélectionné, non-tag, actualisé automatiquement. Infobulle « Actualisation dans
    {n} s ».
- **Fichiers à commiter sur TFS** (client-angular, code seul) :

  | Fichier | Raison |
  |---|---|
  | `libs/mss/src/features/mail/services/mail-state.service.ts` | échéance, horloge unique, règle `isAutoRefreshed` |
  | `libs/mss/src/features/mail/mss-mail.component.ts` | échéance reposée à chaque tour de la minuterie réelle ; règle lue dans l'état |
  | `libs/mss/src/features/mail/components/mail-folder-item/mail-folder-item.component.ts` | plus de minuterie par ligne ; jauge lue dans l'état |
  | `libs/mss/src/features/mail/components/mail-folder-item/mail-folder-item.component.html` | `@if (showRefreshGauge())` |
  | `libs/mss/src/features/mail/components/mail-folder-item/mail-folder-item.component.spec.ts` (nouveau) | 7 tests de la jauge |
  | `libs/mss/src/features/mail/mss-mail.component.refresh-gauge.spec.ts` (nouveau) | 4 tests de l'échéance |

- **Preuves rouges** :

  | Test | Preuve |
  |---|---|
  | jauge : 5 allers-retours, 1 par seconde | code d'avant : `expected '24' to be '29'` (le constat humain : 6 par seconde) |
  | jauge : temps restant de l'écran, pas 30 à la sélection | code d'avant : `expected '30' to be '20'` |
  | une ligne n'arme aucune minuterie | code d'avant : `setInterval` appelé 2 fois |
  | infobulle en français, même chiffre | code d'avant : `'Refresh dans 28s'` |
  | pas de jauge sur les brouillons virtuels / la vue patient | code d'avant : jauge présente (×2) ; mutation M6 (condition `isAutoRefreshed` retirée de la ligne) : rouge ×2 |
  | pas de jauge sur un tag | vert sur le code d'avant (garde de non-régression) |
  | échéance : +1 intervalle à chaque tour | mutation M1 (`tap` de l'échéance neutralisé) : rouge |
  | notification : l'échéance ne bouge pas | mutation M2 (échéance reposée à chaque rafraîchissement) : rouge |
  | une seule horloge, arrêtée avec l'écran | M3 (`takeUntilDestroyed` retiré) : rouge ; M4 (garde du second appel retirée) : rouge |
  | brouillons et vue patient non actualisés, règle partagée | M5 (`isAutoRefreshed` réduit aux tags) : rouge |

  Mutations jouées par script, chaque source restaurée octet pour octet et vérifiée.
- **Build / tests** : `nx build weda2` vert ; mss-lib 176 fichiers, **1 901 tests verts** (Vitest via PowerShell,
  `--pool=forks`) ; weda2 107 fichiers verts.
- **Lint** : `npx eslint` des fichiers touchés : 0 erreur. Restent des avertissements antérieurs (`max-lines` des deux
  gros fichiers, deux `@example` sans description hors du diff). Prettier appliqué au seul spec créé ; le `.html`
  existant n'était déjà pas au format de Prettier, il n'est pas reformaté (`prettier-fichier-existant`).
- **Contrôles mécaniques (§Q 2b)** : fins de ligne homogènes (CRLF partout) ; nouveau contrôle `interval(` / `timer(` :
  2 occurrences, toutes deux souscrites une fois à l'initialisation avec `takeUntilDestroyed`.
- **Passe qualité** : relue à la main sur un diff de 4 fichiers : aucune simplification appliquée.
- **Scénario e2e** : aucun, comme le décide la DOD (indicateur, pas un geste ; le test de composant à horloge simulée
  est le filet).
- **Prévention (règle d'or)** : `conventions/angular.md`, nouvelle entrée `abonnement-resilie-a-la-desactivation` ;
  `agents/develop.md` §Q 2b, contrôle mécanique des minuteries ajoutées.
- **Vert marqué** : client-angular (`Tools/green/green.py`, arbre final).
- **Étape suivante** : `/review task-491 --code`.

## Code Review Summary

### Passage 1 (revue anticipée) — APPROVED

- **Relecteur indépendant** (sous-agent, code et task seulement, sans le `## Develop log`) : APPROVED, aucun bloquant.
- **approved at** : client-angular — arbre de travail non commité sur `feature/nova-mss-weda-integration` (HEAD
  `f8164238`), état marqué vert par `/develop`.
- **Règle 1b** : non applicable — aucun dépôt backend touché, aucun comportement atteignable par un endpoint.
- **4c, consommateurs du contrat** (`contract_impact.py check`) : api-mcp aucun impact ; client-mobile aucun impact ;
  client-angular aucun impact (avertissements de lecture tolérante préexistants, sans effet).
- **4b, clause DOD** : pas de scénario e2e, décidé par la DOD (indicateur, pas un geste). Les tests de composant à
  horloge simulée sont le filet.
- **Règles 1 à 5** : toutes tenues (horloge unique tenue par l'état de l'écran ; décompte lu par la ligne ; rythme
  inchangé, la notification ne décale pas l'échéance ; règle `isAutoRefreshed` lue par l'actualisation, le filtre des
  notifications et la jauge ; infobulle en français).
- **Filtre des notifications** : il exige désormais aussi l'absence de vue « Mails du patient ». Sans effet pratique :
  la vue patient sélectionne un pseudo-dossier, que le filtre par chemin écartait déjà.

#### Suggestions (non bloquantes)

- **S1** `mail-folder-item.component.ts` : `!this.isTag` répète une partie de la règle (un tag a `source === Tag`).
- **S2** `mail-state.service.ts` : la borne haute `[0, intervalle]` n'est pas appliquée. Avec un intervalle qui n'est
  pas un nombre entier de secondes (2 500 ms), la progression dépasserait 100 %. Sans effet avec les 30 000 ms réels.
- **S3** : à l'échéance, l'horloge d'une seconde peut passer avant la minuterie de 30 s. La jauge disparaît alors une
  fraction de seconde (cosmétique).
- **S4** : `nextRefreshAt` est un signal public modifiable. `.asReadonly()` le réserverait à `scheduleNextRefresh`.
- **S5** : le test « arrêtée avec l'écran » détruit tout l'injecteur de TestBed, pas le seul composant.
- **S6** : le test « aucune jauge sur un tag » caractérise l'existant : il était déjà vert sur le code d'avant, ce que
  le Develop log dit. Le cas « vue patient avec INBOX sélectionné » est une combinaison que l'application ne produit
  pas ; il éprouve la règle, pas un parcours.

#### À corriger par la reprise

Aucun.

#### Arbitrage humain

Aucun.

## Lint log

- `npx nx affected -t lint --base=origin/next --head=HEAD --parallel=3 --projects=tag:scope:mss` : **0 erreur**,
  13 projets. Seuls restent des avertissements antérieurs à la task (`max-lines` des deux gros fichiers, deux `@example`
  sans description, hors du diff).
- Aucune correction : itération 1 sans objet, arbre inchangé. Build et tests non rejoués : le vert de `/develop` porte
  sur ce même arbre.
- Aucune règle corrigée à la main : `conventions/angular.md` inchangé par cette étape.
