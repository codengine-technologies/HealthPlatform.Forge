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


## Develop log

- Repos touched : `api-mail` (catalogue e2e + seed), `client-angular` (code-only, non commité)
- DTOs published : no DTO change (le contrat de task-439/440/444 porte déjà `hits`, `isTruncated`, `isDegraded`, `offset`)
- Interop published : no interop change
- Commits :
  - api-mail : `1faf4813` test(e2e): task-445 — scénarios E2E-SEARCH-004 à 009, seed du patient cherché
  - client-angular : **aucun commit** — fichiers modifiés sur `feature/nova-mss-weda-integration`, à commiter par l'humain (TFS) :
    - nouveaux : `libs/mss/src/features/mail/services/mail-search-session.ts` (+ spec), `services/mail-search-tags.ts` (+ spec),
      `components/mail-search-results/` (ts, html, scss), `components/mail-list/mail-list.search-mode.spec.ts`
    - modifiés : `core/models/search.model.ts`, `services/mail-state.service.ts`, `components/mail-list/` (ts, html, scss,
      `mail-list.list-sources.spec.ts`), `components/mail-search/` (ts, html, scss, spec), `mss-mail.component.list-sources.spec.ts`,
      `features/settings/mss-settings.component.*` (ts, html, scss, spec), `e2e/mss-e2e/specs/functional.e2e.ts`,
      `e2e/mss-e2e/support/e2e-backend.ts`
    - ⚠️ l'arbre portait déjà le travail non commité de task-442/443 (formulaire, sélecteurs patient/expéditeurs,
      `mss-api.service.ts`) : il est conservé tel quel, et task-445 s'appuie dessus.
- Conception :
  - `MailSearchSession` (tenue par `MailStateService`) : la recherche affichée vit **à part** de la liste du dossier, qui
    reste intacte dessous. Requête, lignes dans l'ordre du serveur, rattachement par **dossier et UID** (`hits`, lecture
    des messages dans LEUR dossier), parties (« Tous les mots », « Une partie des mots », « Résultats proches », titrées
    seulement avec un texte), « N+ », « Voir plus » (offset = résultats rendus par le serveur, dédoublonné), panne
    (`isDegraded`), erreur qui vide la liste, réponse dépassée abandonnée (désabonnement + numéro de recherche), squelette
    au-delà de 300 ms.
  - `mss-mail-search-results` : étiquettes (une par critère, croix qui relance ; la dernière ferme), filtres d'affinage
    (Non lus, Importants, Pièces jointes, Biologie), bandeau de panne, erreur + réessai, parties, « Voir plus ». Les lignes
    sont celles de la liste (gabarit transmis) : lire, marquer, signaler, supprimer, glisser, cocher marchent sur un résultat.
  - `mss-mail-list` : en mode recherche, l'en-tête dit « Résultats : N messages » et porte « Fermer la recherche » ; les
    filtres Tous / Lus / Non lus et la pagination du dossier disparaissent. Fermer rend le dossier avec son filtre, sa page
    et sa **position de défilement**, la sélection vidée, sans rechargement. Changer de dossier ferme la recherche
    (`prepareFolderSwitch` → `clearSearch`), sans rendre la position.
  - Barre de recherche : plus de croix ; elle lance la session (pages de la taille de la liste, plus de `minSimilarity`
    envoyé), et suit la recherche affichée (étiquette retirée, affinage, fermeture, retour de lecture).
  - Paramètres : section « Avancé » (sensibilité de la recherche) retirée ; `minSimilarity` reste lu/écrit tel quel dans
    les réglages, et n'est plus envoyé.
  - Requêtes de référence de task-438 marquées « task-441 » : **aucune** (recherche `task-441` vide dans `Api/Mail`) —
    rien à re-marquer.
- Local build / test :
  - api-mail : build 0 erreur ; `dotnet test` 7 788 verts, 0 échec (domain 210, infra 743, api 1 376, application 4 193,
    intégration 1 250 + 16 ignorés). Nouveau test de seed `The_search_patient_name_is_carried_by_the_expected_bodies_only`.
  - client-angular : `nx test mss-lib` 1 573 verts (140 fichiers, 0 erreur non gérée) ; `nx test weda2` 2 683 verts ;
    `nx build weda2` vert (avertissements NG8107 préexistants, aucun dans les composants touchés) ;
    `tsc -p e2e/mss-e2e/tsconfig.json` vert ; ESLint ciblé : 0 erreur (avertissements préexistants seulement).
- Preuve par mutation — tests de composant (Vitest, chacun rouge sur le test prévu, puis restauré) :
  - M1 en-tête du mode remplacé par le nom du dossier → 3 rouges (entrée dans le mode, « N+ », retour de lecture)
  - M2 étiquettes absentes → 3 rouges ; M3 retrait sans relance → 2 ; M4 dernière étiquette ne ferme pas → 1
  - M5 « Fermer » ne rend pas la position → 1 ; M6 position des résultats perdue au retour de lecture → 1
  - M7 changement de dossier ne ferme pas → 4 (dont `mss-mail.component.list-sources`)
  - M8 squelette jamais affiché → 2 ; M9 tri local par UID → 2 ; M10 parties sans titre → 3
  - M11 « Voir plus » redemande la première page → 4 ; M16 page suivante comptée sur les lignes affichées → 1
  - M12 panne non lue → 2 ; M13 nouvelle recherche garde l'ancienne liste → 1 ; M13b erreur non affichée → 3
  - M14 réponse dépassée appliquée (garde + désabonnement retirés) → 2 ; M15 rattachement par le dossier de la recherche → 5
  - Paramètres : section « Sensibilité » remise → 1 rouge (`task-445 — ne propose plus de réglage…`)
- Preuve par mutation — parcours e2e (banc `--serve-only`, marqueur `String('MUTATION-Ex')` relu dans le bundle servi avant
  de jouer, retiré après restauration) :
  - E1 parties confondues → E2E-SEARCH-004 rouge (« Une partie des mots » introuvable)
  - E2 « Aucun résultat » jamais affiché → E2E-SEARCH-005 rouge
  - E3 « Voir plus » sans effet → E2E-SEARCH-006 rouge (aucune page suivante demandée)
  - E4 erreur qui garde l'ancienne liste et ne se dit pas → E2E-SEARCH-007 rouge (message d'erreur absent)
  - E5 « Fermer » ne rend pas la position → E2E-SEARCH-009 rouge (`Expected: 295, Received: 0`) — premier essai invalide
    (rechargement à chaud encore en cours, rouge sur la navigation), rejoué après 40 s : rouge sur l'assertion prévue
  - E6 retrait d'étiquette sans relance → E2E-SEARCH-009 rouge
  - Témoin restauré : E2E-SEARCH-001 à 009, 9/9 verts.
- Passe qualité (/simplify) :
  - Applied (code-only, uncommitted) : client-angular — clé (dossier, UID) par `mailKeyString` au lieu d'une copie locale ;
    filtres d'affinage lus une fois par requête (`computed`) ; CSS morte de la croix retirée ; indentation du gabarit ;
    « Voir plus » compté sur les résultats rendus par le serveur (avec dédoublonnage, test + mutation M16) ;
    « Fermer la recherche » sur une ligne (`white-space: nowrap`).
  - No change : api-mail (catalogue et seed de test seulement)
  - Skipped (contract/excluded) : dtos-mss, interop-cda
- Prévention (règle d'or) : `conventions/angular.md` « liste-ordonnee-par-le-serveur » (aucun tri ni filtre local sur une
  liste du serveur, rattachement par tout l'identifiant, lecture de `isTruncated` / `isDegraded` / groupes, erreur qui
  vide la liste).
- DOD self-check : 10/10 critères commandables vérifiés (build, tests, tests de composant prouvés rouges, scénarios
  catalogue + weda2 prouvés rouges, 001-003 verts, requêtes de référence : aucune à re-marquer, réglage retiré,
  `data-testid` sur en-tête / étiquettes / « Fermer » / parties / « Voir plus » / bandeaux, libellés en dur sans donnée de
  santé, client-angular non commité, consigne). Manual Test Plan : HAG.
- ⚠️ À commiter sur TFS **avant** le merge de la PR api-mail : `functional.e2e.ts` (E2E-SEARCH-004 à 009) et
  `support/e2e-backend.ts` (conventions/e2e.md « test-angular-non-commite »).
- Next step : /sonar task-445

## Timings

*(généré par `tools/timing/report.sh --task task-445 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 21 s | — | — | — | — |
| /develop | ok | 43 min 46 s | 3 (43 s) | 6 (7 min 57 s) | — | client-angular 2B/5T, api-mail 1B/1T |
| **Total cycle** | | **44 min 07 s** | **3 (43 s)** | **6 (7 min 57 s)** | **0 (0.0 s)** | |
