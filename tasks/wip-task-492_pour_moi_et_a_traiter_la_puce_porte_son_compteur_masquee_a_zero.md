# todo-task-492.md — « Pour moi » et « À traiter » : la puce porte son compteur, masquée à zéro

**Repos**: client-angular, client-mobile, api-mail
**Reprises**: 1
**Dependencies**: task-454, task-457
**Epic**: E024

> Demande humaine du 2026-11-22, avec une capture de l'entrée « Pour moi » du menu de gauche de weda2 :
> « je voudrais retirer ce menu, et conserver uniquement le filtre "Pour moi" qui se trouve en haut de la liste
> des email, incluant le compteur. Si 0 dans ce cas "Pour moi" ne s'affiche pas. Il faut suivre la même logique
> pour "A traiter". »
>
> Arbitrages de l'humain, le même jour :
> - **Clients** : weda2 **et** mobile ;
> - **compteur qui tombe à 0 pendant que la puce est active** : la puce reste affichée, avec 0, tant que le
>   praticien est dessus, et disparaît dès qu'il change de filtre ;
> - **vues de tag** : la règle s'applique aussi à leur puce « À traiter » ;
> - **sélecteur « Compteurs : À traiter / Non lus »** du menu de gauche (task-454) : **conservé**.
>
> `api-mail` n'est listé que pour le catalogue des scénarios e2e (`Api/Mail/e2e/scenarios.yml`) : aucun code
> serveur ne change.

## Objectif

Le praticien trouve « Pour moi » et « À traiter » au seul endroit où il filtre sa liste : les puces en haut de la
liste des messages. Chaque puce dit combien de messages l'attendent, et n'apparaît que s'il y en a. Le menu de
gauche de weda2 ne porte plus d'entrée « Pour moi », qui doublait la puce.

### Ce qui est établi

- **weda2** (`libs/mss/src/features/mail`) :
  - le menu de gauche porte l'entrée « Pour moi » avec son compteur
    (`mail-folder-list.component.html`, `data-testid="folder-for-me"`, task-457). Elle est le **seul** émetteur de
    `MailEventService.forMeRequested$`, que `MssMailComponent` écoute pour ouvrir « Pour moi »
    (`grep -rn forMeRequested libs --include=*.ts` : un émetteur, un abonné) ;
  - les puces de la liste (`mail-list.component.html`) : « Tous / Non lus / Lus / À traiter / Pour moi » sur un
    dossier, « Tous / Non lus / À traiter » sur une vue de tag. **Aucune ne porte de compteur** ;
  - `MailStateService.forMeCount` lit `forMeCount` sur la Boîte de réception ; `badgeCount` lit `toHandleCount`
    sur un dossier ou un tag.
- **Mobile** (`Client/Mobile/src/app/inbox/inbox.page.html`) : les segments « À traiter » (dossier et vue de tag)
  n'ont pas de compteur ; « Pour moi » porte déjà le sien (`inbox-for-me-count`) mais reste affiché à 0. Le mobile
  n'a pas d'entrée « Pour moi » dans son menu.
- **Serveur** : les nombres existent déjà et sont calculés par api-mail. `toHandleCount` est servi pour chaque
  dossier IMAP **et** chaque tag (`MailHandlingService`, lignes 66 et 72) ; `forMeCount` sur la Boîte de
  réception, pour la personne connectée (`MailAssignmentService`, ligne 160). **Aucun changement de contrat.**
- **Tuiles d'accueil** « À traiter » et « Pour moi » (tableau de bord weda2 et mobile) : hors périmètre,
  inchangées.

### Règles

1. **weda2 : l'entrée « Pour moi » du menu de gauche est retirée**, avec ce qui ne servait qu'à elle (plus aucun
   émetteur ni abonné orphelin). Le sélecteur « Compteurs : À traiter / Non lus » et les compteurs des dossiers et
   des tags ne changent pas.
2. **La puce « Pour moi »** porte le nombre de messages attribués à la personne et non traités, pour **toute la
   boîte** (le nombre que le serveur calcule), quel que soit le dossier affiché.
3. **La puce « À traiter »** porte le nombre de messages à traiter **de ce qu'elle filtre** : le dossier affiché,
   ou le tag affiché dans une vue de tag. C'est le nombre que le serveur calcule, le même que celui du menu de
   gauche en mode « À traiter ».
4. **À 0, la puce n'est pas affichée.**
5. **Exception — la puce active** : si le compteur tombe à 0 pendant que le praticien est sur cette puce (il vient
   de traiter le dernier message), la puce reste affichée, avec **0**, tant qu'il est dessus. « Annuler » dans le
   toast peut ainsi remettre le message sous ses yeux. Elle disparaît dès qu'il choisit un autre filtre ou un
   autre dossier.
6. **Compteur inconnu** (aucun nombre servi : hors-ligne, vue « Mails du patient », serveur qui ne le fournit pas) :
   la puce reste affichée, **sans chiffre**. Un filtre qui marche n'est jamais masqué faute d'information.
   *(Choix du PO, à corriger au merge si besoin.)*
7. **Le compteur suit la liste** : il est relu quand les dossiers sont relus (actualisation périodique, nouveau
   message, geste « Traité », « Annuler », attribution). Aucun calcul local ne le remplace.
8. **Un lien ou un réglage qui ouvrait « Pour moi » ou « À traiter » alors que la puce est masquée** (filtre gardé
   d'une session précédente, retour arrière) : la liste s'ouvre sur « Tous ». *(Choix du PO, à corriger au merge
   si besoin.)*
9. Les deux clients appliquent les mêmes règles. Le libellé reste « Pour moi » / « À traiter », le compteur à
   côté, dans le style de compteur déjà utilisé par chaque client.

## Definition of Done

- [ ] Build passes : weda2 (`nx build weda2`) et client-mobile (`npm run build`), 0 erreur.
- [ ] Tests pass : `nx test mss-lib`, `nx test weda2`, et la suite client-mobile, 0 échec.
- [ ] weda2 : l'entrée « Pour moi » du menu de gauche n'existe plus (`folder-for-me` absent du code et des tests),
      et `forMeRequested$` est retiré avec elle si plus rien ne l'émet.
- [ ] Tests de composant de la liste weda2, chacun **vu rouge** (sur le code actuel ou par mutation) :
  - [ ] « Pour moi » affiche le nombre servi, et n'est pas rendue à 0 ;
  - [ ] « À traiter » affiche le nombre du dossier affiché, et celui du tag dans une vue de tag ; non rendue à 0 ;
  - [ ] une puce active dont le compteur tombe à 0 reste affichée avec 0, puis disparaît au changement de filtre ;
  - [ ] compteur inconnu : puce affichée sans chiffre ;
  - [ ] filtre « Pour moi » ou « À traiter » demandé alors que la puce est masquée : la liste s'ouvre sur « Tous ».
- [ ] Mêmes tests côté mobile (page de la boîte), chacun vu rouge.
- [ ] `data-testid` sur chaque compteur de puce (weda2 et mobile).
- [ ] Aucun texte en dur hors de la convention de libellés de chaque client.
- [ ] Scénario **E2E-ASSIGN-001 passé en version 2** dans `Api/Mail/e2e/scenarios.yml`, et implémenté dans les
      deux clients : la délégataire trouve le message sous la puce « Pour moi », qui porte **1** ; dans weda2, le
      menu de gauche n'a pas d'entrée « Pour moi ». (Le test weda2 actuel clique `folder-for-me` : il est réécrit.)
- [ ] Scénario **E2E-TRIAGE-001 passé en version 2**, implémenté dans les deux clients : la puce « À traiter » de
      la Boîte de réception porte le nombre que le serveur compte, et baisse de un quand le message est traité.
- [ ] Nouveau scénario **E2E-ASSIGN-003** (version 1, `mobile: requis`, `angular: requis`) : une personne à qui
      rien n'est attribué ne voit pas la puce « Pour moi » ; on lui attribue un message, la puce apparaît avec 1 ;
      elle l'ouvre et le traite, la puce reste affichée avec 0 ; elle passe sur « Tous », la puce disparaît. Le
      scénario part d'un compteur connu : si le jeu de données partagé ne garantit pas 0, il utilise sa propre
      boîte ou solde les attributions restantes avant de commencer.
- [ ] `contract_impact.py check` : aucun impact (aucun code d'api-mail ni de dtos-mss ne change).

## Manual Test Plan

- Backend : `cd Api/Mail && dotnet run --project src/AppHost` (profil de développement habituel).
- weda2 : `cd Client/Angular/front && npm run start:weda2`, ouvrir la messagerie.
- Mobile : `cd Client/Mobile && npm start`, ouvrir la boîte.
- Données : une boîte avec au moins un message à traiter, et une seconde personne rattachée à la boîte
  (délégataire) à qui rien n'est attribué.

1. **weda2, menu de gauche** : l'entrée « Pour moi » a disparu ; le sélecteur « Compteurs : À traiter / Non lus »
   est toujours là.
2. **« À traiter »** : sur la Boîte de réception, la puce affiche « À traiter » avec le même nombre que le menu de
   gauche en mode « À traiter ». Ouvrir un dossier sans message à traiter : la puce n'apparaît pas. Ouvrir une
   vue de tag : sa puce « À traiter » porte le nombre du tag.
3. **« Pour moi »**, connecté en délégataire sans attribution : la puce « Pour moi » n'apparaît pas.
4. En titulaire, attribuer un message à la délégataire (« À traiter par »).
5. En délégataire, après l'actualisation : la puce « Pour moi » apparaît avec **1**. Cliquer dessus, ouvrir le
   message, le marquer « Traité » : la puce reste affichée avec **0**. Cliquer « Annuler » dans le toast : le
   message revient, la puce repasse à 1. Le traiter à nouveau, puis cliquer « Tous » : la puce disparaît.
6. Refaire 2 à 5 sur le mobile.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du cabinet).
- **Vague Ségur** : hors Ségur — ergonomie de filtres d'une liste existante, aucune exigence DSR nouvelle.
- **Exigences DSR honorées** : non applicable — aucun échange, aucune donnée nouvelle.
- **INS** : non applicable — aucun patient manipulé ; seuls des nombres de messages sont affichés.
- **Authentification PS** : inchangée — session PSC (e-CPS) existante de la messagerie.
- **Habilitations** : inchangées. « Pour moi » compte les messages attribués à **la personne connectée**
  (titulaire, délégataire ou membre), calculé par le serveur ; un délégataire ou un membre sans verdict récent de
  l'opérateur ne voit rien, comme aujourd'hui (règle 14).
- **Interop CI-SIS** : non applicable — aucun échange.
- **Tracé PGSSI-S** : aucun évènement nouveau. Filtrer une liste n'est pas un acte sur la boîte ; les actes
  (traiter, annuler, attribuer) restent tracés à leur auteur réel comme le font task-454 et task-457.
- **Consentement patient** : non applicable.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : inchangé — aucune donnée nouvelle stockée ; les compteurs viennent du serveur existant.
- **AIPD / impact RGPD** : inchangée — aucun traitement nouveau.

## Branches
- `api-mail` (pushed) : feat/task-492-pour-moi-et-a-traiter-la-puce-porte-son — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-492-pour-moi-et-a-traiter-la-puce-porte-son (catalogue e2e seulement)
- `client-mobile` (pushed) : feat/task-492-pour-moi-et-a-traiter-la-puce-porte-son — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-492-pour-moi-et-a-traiter-la-puce-porte-son
- `client-angular` (code-only) : la forge écrit sur la branche extraite dans `Client/Angular/` (au /start : `feature/nova-mss-weda-integration`) — humain gère branche, commit, push, PR TFS.
  ⚠️ L'arbre de travail porte déjà des changements non commités de task-491 (jauge) et du correctif « Pour moi » du 2026-11-22 (`mail-list.component.ts`, `mail-state.service.ts`, …) : les changements de task-492 s'y ajoutent, à séparer au commit TFS.

## Timings

*(généré par `tools/timing/report.sh --task task-492 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 26 s | — | — | — | — |
| /develop | ok | 9 min 24 s | 4 (56 s) | 7 (10 min 42 s) | — | client-angular 1B/4T, api-mail 1B/1T, client-mobile 2B/2T, reprise 1 |
| /review-code | ok | 4 min 07 s | — | — | — | — |
| **Total cycle** | | **13 min 58 s** | **4 (56 s)** | **7 (10 min 42 s)** | **0 (0.0 s)** | |

## Develop log

- Repos touched : client-angular (code seul, non commité), client-mobile, api-mail (catalogue e2e seulement).
- DTOs published : no DTO change. Interop published : no interop change. `contract_impact.py` : aucun code d'api-mail ni de dtos-mss modifié.
- Commits :
  - api-mail : 73bcb503 test(e2e): E2E-TRIAGE-001 et E2E-ASSIGN-001 en v2, E2E-ASSIGN-003
  - client-mobile : d8609e3 feat(mobile): « À traiter » et « Pour moi » : la puce porte son compteur, masquée à zéro
- **client-angular — fichiers à commiter sur TFS** (branche `feature/nova-mss-weda-integration`, non commités) :
  - `mail-list/mail-list.component.ts|html|scss` : compteur sur les puces « À traiter » (dossier et vue par tag) et « Pour moi », puce masquée à 0 sauf active, retour sur « Tous » quand le compteur d'arrivée est nul ; `data-testid` sur Tous / Non lus / Lus.
  - `services/mail-state.service.ts` : `toHandleChipCount`, `forMeChipCount` (remplace `forMeCount`), repli de la vue par tag sur « Tous » sans toucher au réglage. ⚠️ Ce fichier porte aussi les changements non commités de task-491 et du correctif « Pour moi » du 2026-11-22.
  - `mail-folder-list/mail-folder-list.component.ts|html|scss` : entrée « Pour moi » retirée du menu de gauche, avec ses styles.
  - `services/mail-event.service.ts`, `mss-mail.component.ts` : `forMeRequested$` et `openForMe()` retirés (plus aucun émetteur).
  - `mail-list/mail-list.chip-counters.spec.ts` (nouveau), `mail-folder-list/mail-folder-list.for-me.spec.ts` (réécrit), `services/mail-state.service.handling.spec.ts` (`forMeChipCount`).
  - `e2e/mss-e2e/specs/functional.e2e.ts`, `e2e/mss-e2e/support/e2e-backend.ts` : E2E-TRIAGE-001 v2, E2E-ASSIGN-001 v2, E2E-ASSIGN-003 v1 (**à commiter sur TFS avant le merge de la PR api-mail**, conventions/e2e.md « test-angular-non-commite »).
- Local build / test :
  - api-mail : build 0 erreur ; 8 222 tests verts (dont `ScenarioCatalogTests`), 0 FATAL.
  - client-mobile : `ng lint` propre ; build OK ; 1 693 tests verts.
  - client-angular : `nx build weda2` OK ; mss-lib 177 fichiers / 1 921 tests ; weda2 107 fichiers / 2 683 tests ; ESLint 0 erreur sur les fichiers touchés (warnings préexistants) ; `tsc` de la suite e2e propre.
- Preuves rouges :
  - weda2, `mail-list.chip-counters.spec.ts` : 15/19 rouges sur le code d'avant (les 4 verts décrivent le compteur inconnu, déjà vrai). Mutations, chacune rouge sur l'assertion visée : M1 jamais collante (4 tests), M2 aucun retour sur « Tous » (4), M3 « Pour moi » toujours affichée (3), M4 compteur de la boîte pour tout dossier (3), M5 repli qui enregistre le réglage (1), M7/M8/M8b/M9 compteur inconnu lu comme 0 (1 chacun). `mail-folder-list.for-me.spec.ts` : M6 entrée « Pour moi » remise au menu → rouge.
  - mobile, `inbox.page.chip-counters.spec.ts` : 11/14 rouges sur le code d'avant (stash), les 3 verts sont les cas « compteur inconnu ». Mutations MM1 à MM6 (collante, retour sur « Tous », inconnu lu comme 0 ×3, repli qui enregistre) : rouges sur l'assertion visée.
  - e2e, bancs `--serve-only` : TRIAGE-001, ASSIGN-001, ASSIGN-002, ASSIGN-003 verts sur les deux clients (4/4 chacun). Mutations servies (bundle relu, marqueur compté) : « Pour moi » toujours affichée → ASSIGN-003 rouge « compteur nul : pas de puce » ; jamais collante → ASSIGN-003 rouge « la puce active reste affichée avec 0 » ; compteur « À traiter » absent → TRIAGE-001 rouge « la puce porte le nombre du serveur ». Mêmes trois rouges sur mobile (ME1-ME3) et weda2 (MW1-MW3). Bancs démontés (ports libres, aucun conteneur e2e).
- Passe qualité (/simplify) : diff relu (weda2, mobile) — aucun nettoyage retenu : logique de puce identique dans les deux clients (pas de code partagé entre eux), aucune duplication interne. Contrôles mécaniques §Q 2b : aucune minuterie ni clé sur l'UID seul ajoutée ; fins de ligne cohérentes (un `sed -i` a converti `functional.spec.ts` mobile en LF, CRLF rétablis avant le commit).
  - Skipped (contract/excluded) : dtos-mss, interop-cda, sdk.
- Choix d'implémentation à relire : la vue par tag ramenée sur « Tous » (règle 8) l'est pour cette combinaison seulement, sans enregistrer le réglage ; une combinaison de plusieurs tags et la vue « Mails du patient » n'ont pas de nombre servi, leur puce s'affiche sans chiffre (règle 6).
- DOD self-check : 13/13 lignes vérifiables par commande ; observations du Manual Test Plan → HAG.
- Green marked : api-mail, client-mobile, client-angular (`Tools/green/green.py`).
- Next step : /review task-492 --code

## Code Review Summary

### Passage 1 (revue anticipée) — CHANGES REQUESTED

Relecteur indépendant (sous-agent, code seul). Règle 1b : aucun comportement atteignable par un endpoint ne change (api-mail : catalogue e2e seulement) — sans objet. Contrat (`contract_impact.py check`) :
- api-mcp : aucun impact
- client-mobile : aucun impact
- client-angular : aucun impact

Clause DOD e2e : E2E-TRIAGE-001 v2, E2E-ASSIGN-001 v2, E2E-ASSIGN-003 v1 au catalogue, mêmes versions déclarées par les tests des deux clients.

#### À corriger par la reprise

- **B1 (bloquant)** — la puce « À traiter » d'un **sous-dossier** n'a pas de nombre et n'est jamais masquée : `toHandleChipCount` cherche le dossier affiché au seul premier niveau de `folders()` (weda2 `mail-state.service.ts`, mobile `mail-state.service.ts`), alors que le serveur rend un arbre (`folder.folders`) et compte chaque nœud. Patients/Dupont à 0 → puce affichée sans chiffre ; à 3 → menu 3, puce sans chiffre ; la règle 8 ne s'y applique pas. Correctif : chercher dans l'arbre, dans les deux clients ; specs avec un sous-dossier à 0 et un à 3, vus rouges.
- **S2 (défaut réel)** — weda2 : la mémoire de la puce active (`countedChipSeen`) vit dans `MailListComponent`, démonté quand un message, une rédaction ou l'assistant occupe l'écran (volet de lecture absent). Un compteur relu pendant ce temps (actualisation 30 s, retour de rédaction) fait repasser la liste sur « Tous » alors que le praticien n'a pas quitté la puce. Correctif : la mémoire dans `MailStateService` (conventions/angular.md « service-propre-au-composant »), spec qui démonte et remonte la liste.
- **S1 (défaut réel)** — mobile : la clé de vue de la puce n'inclut pas la boîte ; après un changement de boîte (filtre conservé), une boîte sans message à traiter garde la puce à 0 au lieu de repasser sur « Tous » (règle 8). Correctif : la génération de la session de boîte dans la clé (ou mémoire effacée au changement), spec.
- **S3 (défaut réel, e2e)** — `settleForMe` ne solde que les attributions de l'INBOX (`forMeUids` filtre INBOX, `markHandledAs` code `folders/INBOX`) alors que `forMeCount` compte toute la boîte : une attribution restée dans un autre dossier fait échouer E2E-ASSIGN-003 à chaque run. Correctif : parcourir les clés (dossier, UID) de « Pour moi », `markHandledAs` avec le dossier, dans les deux suites.
- **S4 (tests mobile)** — combler les cas présents côté weda2 : le réglage « À traiter » réappliqué au tag suivant qui a des messages à traiter après un repli (par `onTagToggled`), la puce de vue par tag active qui reste à 0, « À traiter » qui disparaît au changement de filtre.

#### Arbitrage humain

Aucun.

Vérifié sans constat : aucun reste des membres retirés (`forMeRequested$`, `openForMe`, `forMeCount()`, `folder-for-me`, `inbox-for-me-count`) ; chaque clic e2e sur une puce se fait après qu'elle a un compteur non nul ; les absences sont lues après chargement ; effets sans boucle, chargement précédent abandonné ; aucun repli n'enregistre le réglage ; jetons SCSS existants avec repli ; `data-testid` sur chaque compteur.


### Reprise 1 (passage 1 de la revue anticipée)

- **B1** — recherche du dossier affiché dans l'arbre : `findFolderByPath` (`core/utils/folder-tree.util.ts`, weda2 et mobile, avec spec), utilisé par `toHandleChipCount` des deux clients. Specs « B1 — sous-dossier » (×2 par client) : rouges sur le code revu (« Expected undefined to be '3' », puce présente à 0), verts après.
- **S2** (weda2) — mémoire de la puce active dans `MailStateService.countedChipSeen` (plus dans `MailListComponent`). Spec « S2 — la liste démontée puis remontée » : rouge sur le code revu (repli sur « Tous »), vert après.
- **S1** (mobile) — la génération de la session de boîte entre dans la clé de vue. Spec « S1 — changement de boîte » : rouge sans le correctif (stash de `inbox.page.ts`), vert avec. Le test sert les dossiers de la nouvelle boîte par l'API simulée : un premier jet qui posait les dossiers à la main était réécrit par le rechargement asynchrone de la page.
- **S3** (e2e, deux suites) — `settleForMe` solde les attributions de **tous** les dossiers : `forMeKeys` (clés dossier + UID), `markHandledAs` prend la clé. `tsc` des deux suites propre. Voies complètes rejouées par `/e2e`.
- **S4** (mobile) — 3 cas ajoutés : réglage « À traiter » relu après un repli (par `onTagToggled`), puce de vue par tag active qui reste à 0, « À traiter » qui disparaît sur « Non lus ». Verts dès l'écriture, prouvés par mutation : MS4a relecture du réglage retirée → rouge ; MS4b jamais collante → 4 rouges ; MS4c « À traiter » toujours affichée → 5 rouges.
- Commits : client-mobile `38cdb89` ; client-angular non commité (nouveaux fichiers : `core/utils/folder-tree.util.ts` et `.spec.ts`, à ajouter à la liste TFS).
- Suites : mss-lib 178 fichiers / 1 927 tests ; weda2 build OK, 2 683 tests ; mobile `ng lint` propre, build OK, 1 702 tests. ESLint weda2 0 erreur.
- Prévention : `conventions/angular.md` — nouvelle entrée `dossier-cherche-dans-l-arbre` (deux autres sites de même forme relevés, hors task) ; `service-propre-au-composant` passe à 2 occurrences. `agents/develop.md` §Q 2b : contrôle mécanique ajouté, vérifié (attrape le code d'origine, rien après la reprise).
- Green marked : client-mobile, client-angular ; api-mail inchangé (vert de /develop valide).

### Passage 2 (revue anticipée) — APPROVED

Relecteur indépendant, diff de la reprise lu en premier. Rien de cassé par la reprise : `markHandledAs` n'a qu'un appelant par suite (`settleForMe`), passé à la clé ; `countedChipSeen` vit dans le `MailStateService` fourni par l'écran mail, recréé au changement de boîte (aucune fuite) ; la génération dans la clé mobile suit l'ordre réel purge → génération. B1, S1, S2, S3, S4 corrigés. Contrat : api-mcp, client-mobile, client-angular — aucun impact.

- approved at : api-mail `73bcb503` ; client-mobile `38cdb89` ; client-angular arbre de travail (empreinte du vert marqué par /develop, reprise 1).

#### Suggestions (non bloquantes)

- **S-a** — `forMeKeys` ne lit que la première page de 100 : au-delà de 100 attributions ouvertes pour la délégataire dans la boîte partagée de test, `settleForMe` ne solderait pas tout (improbable avec le seed actuel).
- **S-b** — weda2 : la mémoire survivant au démontage de la liste, rechoisir le même dossier dans le menu pendant qu'un message est ouvert garde une puce active à 0. Conforme à la règle 5 (le praticien n'a pas quitté la puce).
