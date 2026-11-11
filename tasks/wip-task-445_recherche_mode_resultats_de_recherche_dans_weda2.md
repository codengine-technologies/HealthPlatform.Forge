# todo-task-445.md — Recherche : mode « Résultats de recherche » dans weda2

**Repos**: client-angular, api-mail
**Dependencies**: done-task-442 (formulaire), done-task-440 (groupes et sections de la réponse ; 438 et 439 requises en
amont)
**Epic**: E023
**Priorité**: EPIC E023, demandée par l'humain le 2026-11-10. Le médecin doit savoir qu'il est dans une recherche,
affiner sans tout recommencer, et en sortir pour retrouver sa liste telle qu'il l'avait laissée.

> **Origine.** Analyse du 2026-11-10, sur le modèle d'Outlook 365 (mode recherche, filtres modifiables sur les
> résultats, « Fermer la recherche »). **Absorbe la part weda2 de task-441** (E022-F004, « les clients fidèles au
> serveur »), retirée sur décision de l'humain du 2026-11-10 : ses règles sont reprises ci-dessous ; sa part mobile va
> en task-450. Texte d'origine : commit `2bc52c4`. `api-mail` figure dans les Repos pour le catalogue e2e.

## Ce qui est établi

Lecture du code au 2026-11-10 (`Client/Angular/front/libs/mss/src`) :

- Les résultats remplacent le contenu de la liste du dossier (`mail-list.component`), **sous le titre du dossier** et
  avec les filtres Tous / Lus / Non lus : seul un compteur sur la barre signale la recherche.
- Repris de task-441 (campagne du 2026-11-09, `Docs/audits/recherche-campagne-bugs-weda2-mobile-20261109.md`) :
  - les résultats sont rattachés par **UID dans le dossier courant** : le dossier de chaque `hit` est ignoré ;
  - sans dossier sélectionné, l'affichage est abandonné (`mail-list.component.ts`, l.698, à confirmer à l'écran) ;
  - en cas d'erreur, **rien n'est affiché** et l'ancienne liste reste (`mail-search.component.ts`, l.579-582) ;
  - `isTruncated`, `isDegraded`, `degradedSources` ne sont pas lus ; pages côté client sur les 50 premiers ;
  - le seuil de similarité est un réglage de la personne (écran Paramètres), ignoré par le serveur depuis task-440.

## Objective

Lancer une recherche fait entrer weda2 dans un **mode « Résultats de recherche »**, distinct de la liste du dossier,
fidèle à ce que le serveur a trouvé, qu'on affine sur place et dont on sort explicitement.

Règles du mode :
- **En-tête** : « Résultats : N messages » remplace le titre du dossier (N = total rendu par le serveur, « N+ » quand
  la réponse est tronquée). Une barre d'**étiquettes** montre chaque critère actif (texte, statut, période, type de
  document…), chacune avec une croix qui la retire.
- **Affiner sur place** : retirer une étiquette, ou cocher un filtre de la barre des résultats (Non lus, Importants,
  Pièces jointes, Biologie), **relance immédiatement** la recherche avec les critères restants. Retirer la dernière
  étiquette ferme la recherche.
- **« Fermer la recherche »** (bouton explicite, remplace la croix de la barre) : rend la liste du dossier d'avant, avec
  son filtre, sa sélection vidée et sa **position de défilement**.
- **Ouvrir un message puis revenir** conserve le mode, les résultats et la position.
- **Changer de dossier** dans la barre latérale ferme la recherche.
- **Squelette de chargement** dès que la réponse tarde plus de 300 ms.

Règles reprises de task-441 (fidélité au serveur) :
- **L'ordre du serveur est l'ordre affiché** : aucun tri ni filtrage local sur les résultats.
- **Trois parties titrées**, dans l'ordre : « Tous les mots », « Une partie des mots », « Résultats proches ». Une partie
  vide n'est pas affichée. Aucun résultat : « Aucun résultat » (suivi des proches, s'il y en a).
- **« Voir plus »** demande la page suivante au serveur quand la réponse est tronquée, jusqu'au dernier résultat.
- **Panne signalée** : si `isDegraded`, un bandeau dit que les résultats peuvent être incomplets.
- **Erreur affichée** : un message clair ; l'ancienne liste n'est jamais laissée à l'écran comme résultat de la
  nouvelle recherche.
- **Requête dépassée abandonnée** : seule la réponse à la dernière recherche s'affiche.
- **Rattachement par dossier et UID** (`hits`), y compris dans un dossier d'étiquette et sans dossier sélectionné.
- **Plus de réglage de similarité** dans l'écran Paramètres ; les valeurs enregistrées sont ignorées.

### Hors périmètre

- Extraits, endroit trouvé, patients trouvés : task-446.
- Portée « tous les dossiers » et tri : task-447. Jusque-là, la portée reste celle d'aujourd'hui (dossier courant).
- Sélection de tous les résultats : task-448. Le mode sélection existant de la liste reste disponible sur la page.
- Le mobile : task-450.

## Definition of Done

- [ ] Build passes (0 errors) : weda2 (`nx build weda2`)
- [ ] Tests pass (0 failures) : `nx test weda2`, `nx test mss-lib`
- [ ] Tests de composant, chacun vu rouge par mutation : entrée dans le mode (en-tête, étiquettes) ; retrait d'une
      étiquette qui relance ; retrait de la dernière qui ferme ; « Fermer la recherche » qui restaure dossier, filtre et
      position ; retour de lecture qui conserve le mode ; changement de dossier qui ferme ; squelette au-delà de 300 ms ;
      ordre du serveur conservé ; trois parties titrées ; « Voir plus » ; bandeau de panne ; erreur affichée et liste
      vidée ; réponse dépassée ignorée ; rattachement par dossier et UID
- [ ] **Scénarios e2e** ajoutés à `Api/Mail/e2e/scenarios.yml`, clients angular requis, mobile requis avec **divergence
      temporaire** (raison : « le mobile adopte le mode résultats avec la refonte mobile de la recherche », tache :
      task-450), implémentés dans weda2, vérifiant le **contenu** de la liste, chacun vu rouge par mutation :
      - `E2E-SEARCH-004` v1 : un nom de patient tapé sans accent ni majuscule trouve ses messages sous « Tous les mots »,
        puis les messages partiels sous « Une partie des mots » ;
      - `E2E-SEARCH-005` v1 : un mot absent de la boîte affiche « Aucun résultat » ;
      - `E2E-SEARCH-006` v1 : plus de résultats qu'une page : « Voir plus » affiche la suite, jusqu'au dernier ;
      - `E2E-SEARCH-007` v1 : une recherche en échec affiche un message, et l'ancienne liste n'est plus affichée ;
      - `E2E-SEARCH-009` v1 : « Fermer la recherche » rend le dossier d'avant à la même position, et retirer une
        étiquette relance la recherche sans elle ;
      - `E2E-SEARCH-001` à `003` restent verts
- [ ] Les requêtes de référence de task-438 marquées « task-441 », s'il y en a, sont re-marquées « task-445 » (weda2) ou
      « task-450 » (mobile), et celles de weda2 sont vertes
- [ ] Réglage de similarité retiré de l'écran Paramètres de weda2 ; aucune régression des autres réglages
- [ ] `data-testid` sur chaque élément interactif ajouté (en-tête, étiquettes, « Fermer la recherche », parties,
      « Voir plus », bandeaux)
- [ ] Aucune chaîne en dur hors des conventions de libellés ; aucune donnée de santé dans les libellés
- [ ] client-angular : code-only, aucun commit
- [ ] **Prévention (règle d'or)** : consigne dans `conventions/angular.md` : un client ne retrie ni ne refiltre une
      liste ordonnée par le serveur, et lit tous les signaux de la réponse (`isTruncated`, `isDegraded`, `hits`)

## Manual Test Plan

1. Lancer le backend sur la boîte de formation de Virginie : `cd Api/Mail/src/AppHost && dotnet run`. Lancer weda2 :
   `cd Client/Angular/front && npm start`.
2. Ouvrir la Boîte de réception, faire défiler jusqu'au 30e message.
3. Rechercher `catherine bernard` avec « Pièces jointes » coché :
   - l'en-tête dit « Résultats : N messages », les étiquettes « catherine bernard » et « Pièces jointes » sont visibles ;
   - « Tous les mots » en tête, puis « Une partie des mots » ; « Voir plus » jusqu'aux plus anciens messages.
4. Retirer l'étiquette « Pièces jointes » : la recherche se relance sans elle.
5. Ouvrir un résultat, revenir : toujours dans le mode, à la même position.
6. Cliquer « Fermer la recherche » : la Boîte de réception revient, au 30e message.
7. Rechercher `zorglubine` : « Aucun résultat ». Couper le serveur et relancer une recherche : un message d'erreur
   s'affiche, aucune ancienne liste.
8. Rechercher puis cliquer sur un autre dossier dans la barre latérale : la recherche est fermée.
9. L'écran Paramètres ne propose plus de réglage de similarité.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du praticien)
- **Vague Ségur** : hors Ségur — ergonomie de la recherche
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — aucun identifiant patient affiché par cette task
- **Authentification PS** : inchangée — PSC (e-CPS), niveau eIDAS substantiel
- **Habilitations** : inchangées — verdict de l'opérateur MSSanté (règle 14)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé — chaque recherche, affinage et page suivante tracés côté serveur (`MailSearch`) au nom de
  la personne réelle, 3 653 jours
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non applicable au client — aucune donnée stockée
- **AIPD / impact RGPD** : inchangé

## Branches

- `api-mail` (pushed) : feat/task-445-recherche-mode-resultats-de-recherche — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-445-recherche-mode-resultats-de-recherche
- `client-angular` (code-only) : la forge écrit sur la branche checked out dans `Client/Angular/` (au /start : `feature/nova-mss-weda-integration`, avec des modifications non commitées de task-442) — humain gère branche, commit, push, PR TFS
