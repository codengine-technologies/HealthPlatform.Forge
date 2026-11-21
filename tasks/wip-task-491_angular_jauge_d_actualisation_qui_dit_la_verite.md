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
