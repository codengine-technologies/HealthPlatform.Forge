# todo-task-350.md — Répondre et transférer : jamais sans le message d'origine, même cliqué avant son chargement

**Repos**: api-mail, client-angular, client-mobile, client-blazor
**Dependencies**: — (aucune ; ordre recommandé : avant la reprise de task-349, voir « Lien avec task-349 »)
**Epic**: E009
**Single frontend**: false
**Priorité**: **1** — intégrité d'un courrier médical. Un transfert part chez le confrère **sans le
message d'origine**, sans aucune erreur visible : le praticien croit avoir transmis un compte rendu,
une biologie ou un courrier, et n'a envoyé qu'une ligne.

> **Origine.** Trouvé par `/e2e` sur task-349, le 2026-10-01. E2E-COMPOSE-002 a échoué au premier
> essai : le message reçu ne portait plus la citation. La trace Playwright montre une requête d'envoi
> réduite au texte du praticien, et le cas se reproduit 1 fois sur 5 au premier passage à froid.
> C'est un **trou du filet** : E2E-DETAIL-001 vérifie seulement que Répondre et Transférer
> « ouvrent la rédaction », jamais ce qu'elle contient. Les règles métier ont été arbitrées par
> l'humain le même jour : boutons inactifs tant que le message d'origine n'est pas chargé, refus
> avec message si son chargement échoue, et les trois fronts sont couverts.

## Ce qui existe (constaté dans le code le 2026-10-01)

- **client-angular** — `mail-detail.component.ts` : `reply()`, `replyAll()` et `forward()` sont
  cliquables dès que le mail est sélectionné, avant que `mailContent()` soit chargé.
  `mail-compose.component.ts` › `initializeFromPrefill` ne construit la citation que
  `if (prefill.content)`. Un clic rapide (80 ms après l'ouverture, dans la trace) ouvre donc une
  rédaction **sans citation ni en-tête**.
- **client-mobile** — `mail-detail.component.ts` passe `content: this.content`, qui peut encore valoir
  `null`. `mail-compose.component.ts` › `openFor` construit alors l'en-tête de citation avec un corps
  **vide** (`req.content?.bodyHtml || … || ''`). Même défaut, sous une forme voisine.
- **client-blazor** — `MailDetailComponent.razor` › `ReplyEmail` et `ForwardEmail` **attendent**
  `GetEmailContentAsync` quand le contenu manque. Le cas nominal est protégé. Mais si ce chargement
  échoue, `GetOriginalBody` rend un corps vide et la rédaction s'ouvre quand même, sans l'original.

## Objective

Le praticien ne peut **jamais** répondre ni transférer un message sans le message d'origine.

1. **Pendant le chargement** : Répondre, Répondre à tous et Transférer sont **inactifs** (grisés,
   avec une infobulle « Chargement du message… ») tant que le contenu du message n'est pas chargé.
   Ils deviennent actifs dès qu'il l'est.
2. **Échec du chargement** : les trois actions restent inactives, et un message clair s'affiche :
   « Le message d'origine n'a pas pu être chargé : réessayez. » Aucune rédaction ne s'ouvre sans
   l'original.
3. **Garde à l'ouverture** : la rédaction ouverte en réponse ou en transfert **contient toujours** le
   message d'origine. C'est une défense en profondeur, même si un autre chemin l'appelait trop tôt.
   Si l'original manque, elle ne s'ouvre pas et le même message s'affiche.
4. Rien ne change pour un nouveau message ni pour la reprise d'un brouillon.

**Hors périmètre** : la mise en forme de la citation et la liste des pièces jointes transférées
(task-170 et suivantes), inchangées.

## Lien avec task-349

- task-349 (correction orthographique) est en `wip` avec 6 points bloquants, et ne doit pas absorber
  ce défaut : il touche le transfert et la réponse, pas la correction.
- La **précondition de E2E-COMPOSE-002** (« la citation est dans l'éditeur avant de demander la
  correction », cf. `conventions/e2e.md` › `precondition-du-negatif`) est ajoutée **dans task-349**,
  car le scénario n'existe que sur sa branche. Elle est consignée dans `questions/task-349.md`.
- Une fois task-350 mergée, E2E-COMPOSE-002 n'a plus de premier essai rouge.

## Definition of Done

- [ ] Build passes (0 errors) sur les 4 repos ; Tests pass (0 failures, hors flaky préexistants documentés)
- [ ] **Angular** — tests de composant, rouges d'abord :
  - [ ] Répondre / Répondre à tous / Transférer inactifs tant que le contenu n'est pas chargé, actifs ensuite
  - [ ] échec du chargement → actions inactives + message « Le message d'origine n'a pas pu être chargé : réessayez. »
  - [ ] la rédaction ouverte en transfert sans contenu ne s'ouvre pas (garde de `initializeFromPrefill`)
  - [ ] la rédaction ouverte en transfert et en réponse contient le message d'origine
- [ ] **Mobile** — mêmes tests de composant que l'Angular (`mail-detail`, `mail-compose` › `openFor`)
- [ ] **Blazor** — tests bUnit :
  - [ ] chargement du contenu en échec → aucune rédaction, message affiché
  - [ ] le cas nominal (contenu chargé à la demande) reste inchangé
- [ ] Scénario **E2E-DETAIL-001** versionné en **v2** dans `Api/Mail/e2e/scenarios.yml`
  (`mobile: requis`, `angular: requis`), et implémenté dans les deux clients. Attendu v2 :
  « Répondre et Transférer ouvrent la rédaction **avec le message d'origine** ; le message transféré,
  relu côté serveur, porte la citation d'origine. » L'assertion porte sur ce qui est **reçu**, pas
  sur l'éditeur (`conventions/e2e.md` › `etat-optimiste`).
- [ ] Trou du filet : scénario E2E-DETAIL-001 durci, **prouvé rouge sur le bug non corrigé**. Pour
  cela, on retire la garde et on clique Transférer avant la fin du chargement : le test doit tomber.
  Ligne « Trous du filet » de `conventions/e2e.md` complétée avec cette task.
- [ ] `data-testid` inchangés sur les boutons existants (`reply-btn`, `reply-all-btn`, `forward-btn`) ;
  libellés FR en dur (Angular, mobile) / Localizer (Blazor) pour le nouveau message
- [ ] Aucune donnée de santé dans les logs : l'échec de chargement est journalisé sans contenu
  (identifiant technique du message seulement)

## Manual Test Plan

1. Backend : `cd Api/Mail && dotnet run --project src/AppHost`.
   - Angular : `cd Client/Angular/front && npm start`.
   - Mobile : `cd Client/Mobile && npm start`.
   - Blazor : `cd Client/Blazor && dotnet run --project <projet Shell>`.
2. **Clic avant chargement** (Angular, mobile) : outils de développement › Réseau › « 3G lente ».
   Ouvrir un message reçu, puis cliquer **aussitôt** sur Transférer.
   - Attendu : le bouton est grisé (infobulle « Chargement du message… ») jusqu'à l'affichage du corps.
   - Une fois actif, le transfert ouvre la rédaction **avec** l'en-tête « Message transféré » et le
     corps d'origine.
3. **Envoi du transfert** : transférer à sa propre adresse, envoyer, puis rouvrir le message reçu.
   La citation d'origine est présente.
4. **Répondre / Répondre à tous** : même parcours que l'étape 2. La citation « Le …, … a écrit : » est
   présente.
5. **Échec du chargement** (les trois fronts) : outils de développement › Réseau › bloquer la requête
   du contenu du message (`…/emails/content/…`), puis ouvrir un message.
   - Attendu : les trois actions restent inactives, et le message « Le message d'origine n'a pas pu
     être chargé : réessayez. » s'affiche.
   - Débloquer, puis rouvrir le message : les actions redeviennent actives.
6. **Non-régression** : nouveau message et reprise d'un brouillon, inchangés.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — messagerie MSSanté intégrée au logiciel
- **Exigences DSR honorées** : non applicable — correctif d'intégrité du contenu transmis. Aucune
  exigence DSR nouvelle n'est couverte, et le contenu MSSanté émis redevient complet.
- **INS** : non applicable — aucune INS manipulée. Le message d'origine transféré peut en contenir une,
  elle est transmise telle quelle comme aujourd'hui.
- **Authentification PS** : inchangée — PSC / e-CPS de la session. L'envoi reste soumis aux contrôles
  MSSanté existants.
- **Habilitations** : inchangées (boîte sélectionnée du praticien)
- **Interop CI-SIS** : non applicable — aucun document CDA produit. Les pièces jointes transférées
  (dont l'IHE_XDM.ZIP) sont hors périmètre et inchangées.
- **Tracé PGSSI-S** : inchangé. L'échec de chargement du contenu est journalisé techniquement, sans
  contenu.
- **Consentement patient** : non applicable — aucun partage nouveau. Le correctif empêche un envoi
  incomplet, il n'en crée aucun.
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé — aucune donnée nouvelle n'est stockée ni transmise
- **AIPD / impact RGPD** : inchangé — aucune finalité nouvelle

## Branches
- `api-mail` (pushed) : fix/task-350-repondre-transferer-avec-message-origine — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-350-repondre-transferer-avec-message-origine
- `client-blazor` (pushed) : fix/task-350-repondre-transferer-avec-message-origine — https://github.com/codengine-technologies/HealthPlatform.Client/tree/fix/task-350-repondre-transferer-avec-message-origine
- `client-mobile` (pushed) : fix/task-350-repondre-transferer-avec-message-origine — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/fix/task-350-repondre-transferer-avec-message-origine
- `client-angular` (code-only) : la forge écrit le code sur la branche checked out dans `Client/Angular/` — instantané au `/start` (2026-10-11) : `feature/nova-rewriting-mss-weda-integration`. L'humain gère branche, commit, push, PR TFS.

## Timings

*(généré par `tools/timing/report.sh --task task-350 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 27 s | — | — | — | — |
| /develop | ok | 57 min 33 s | 4 (55 s) | 5 (4 min 25 s) | — | client-mobile 1B/1T, client-blazor 1B/2T, api-mail 1B/1T, client-angular 1B/1T |
| **Total cycle** | | **58 min 00 s** | **4 (55 s)** | **5 (4 min 25 s)** | **0 (0.0 s)** | |

## Develop log

- **Repos touchés** : `api-mail` (catalogue e2e seulement), `client-mobile`, `client-blazor`, `client-angular` (code-only).
- **DTOs / interop / sdk** : aucun changement.
- **Commits** :
  - api-mail : `4647a8c3` test(e2e) — catalogue E2E-DETAIL-001 v2 (`seed: [mail-lu]`, mobile et angular requis).
  - client-mobile :
    - `3bd444a` fix(mobile) — boutons inactifs tant que l'original n'est pas chargé, message d'échec, garde de `openFor` ;
    - `2c73c1a` test(e2e) — E2E-DETAIL-001 v2.
  - client-blazor : `9d92a61` fix(mss) — `EnsureOriginalLoadedAsync` (Répondre, Transférer, repli d'Annuler et remplacer), clé `OriginalNotLoaded` (fr/en).
  - client-angular : **non commité**, sur `feature/nova-rewriting-mss-weda-integration`. Fichiers listés ci-dessous.
- **Ce qui est fait** :
  - **Angular** :
    - `mail-detail` :
      - `originalLoaded` : le contenu chargé est celui du message affiché, même `uid` et même dossier. Pendant le chargement du message suivant, le contenu du précédent n'est jamais cité.
      - `replyBlockedReason` (« Chargement du message… », ou « Le message d'origine n'a pas pu être chargé : réessayez. »).
      - `contentLoadFailed` (sauf message disparu, task-353).
      - Boutons `[disabled]` avec infobulle, bandeau `mail-original-load-failed`.
      - Gardes dans `reply` / `replyAll` / `forward`.
    - `mail-compose.openCompose` : refuse une réponse ou un transfert sans `content`, par un snackbar, en défense en profondeur.
    - Constantes `ORIGINAL_LOADING_MESSAGE` et `ORIGINAL_NOT_LOADED_MESSAGE` dans `core/utils/quoted-body.util.ts`.
  - **Mobile** :
    - `core/utils/original-message.util.ts` (`isOriginalLoaded`, `replyBlockedReason`), partagé par la page et le composant.
    - La page grise les boutons de l'en-tête et affiche le message d'échec à la place du texte technique.
    - Le composant garde `reply` / `replyAll` / `forward`.
    - `mail-compose.openFor` refuse sans contenu (toast).
  - **Blazor** — **constat qui contredit « Ce qui existe »** : `ReplyEmail` et `ForwardEmail` appelaient `GetEmailContentAsync` **sans rattacher le résultat** au message. Le cas nominal n'était donc **pas** protégé : un clic avant le chargement ouvrait déjà la rédaction sans l'original.
    - Le contenu est maintenant rattaché.
    - En cas d'échec, aucune rédaction ne s'ouvre, une notification s'affiche, et l'échec est journalisé avec `Uid` et `Status` seulement.
- **Tests (rouges d'abord)** :
  - Angular :
    - `mail-detail.component.spec` : 3 tests (inactifs puis actifs ; contenu du message précédent ; échec 500) ;
    - `mail-compose.component.spec` : 3 tests (réponse et transfert sans original refusés ; nouveau message inchangé) ;
    - 5 rouges avant le correctif, puis verts.
    - Tests DOM `mail-detail.side-panel.spec` : 2 tests. **Mutation** : `[disabled]` retiré de Transférer, les 2 rouges, puis restauré.
  - Mobile :
    - `original-message.util.spec` ;
    - `mail-compose.component.spec` : refus pour reply, reply-all et forward ; new inchangé ;
    - `mail-detail.component.spec` : rien n'est émis avant le contenu, ni avec le contenu d'un autre message ;
    - `mail-detail.page.spec` : échec suivi du message clair ; chargement, puis actif.
    - 4 rouges (compose ×3, composant), la page rouge à la compilation, puis 108/108.
    - Les tests de compose qui ouvraient un transfert sans contenu reçoivent `content: original()`.
  - Blazor bUnit `MailDetailComponentTests` :
    - réponse et transfert chargés à la demande, contenu transmis ;
    - échec de chargement suivi d'aucune rédaction et de la notification (theory reply/forward).
    - 4 rouges sur l'assertion visée (une fois les `data-testid` posés), puis verts.
- **Build / tests complets** :
  - api-mail : build ✓, 6 468 verts (0 échec, 16 ignorés) ;
  - client-blazor : build 0 erreur 0 avertissement, 427 verts ;
  - client-mobile : build ✓, 1 021 verts ;
  - client-angular : build ✓, 11 projets ✓ (mss 715).
- **E2E (Step 6b)** :
  - catalogue d'abord : E2E-DETAIL-001 **v2** ;
  - tests v2 dans les deux suites :
    - réseau ralenti par **latence CDP de 3 s**, Transférer cliqué aussitôt, envoi à « Robert » (soi-même) ;
    - le message **reçu**, relu côté serveur, porte le corps seedé de `mail-lu` ;
    - Répondre cite l'original dans l'éditeur ;
  - type-check ✓ dans les deux suites.
  - **Trou du filet prouvé rouge sur le bug** (`--serve-only`, test seul, `--retries=0`). La garde est retirée (méthode `forward`, `[disabled]`, garde de la rédaction) :
    - Angular : rouge sur « le message transféré, relu côté serveur, porte le message d'origine » (corps reçu vide), vert une fois restauré (16,9 s) ;
    - mobile : rouge sur la même assertion (reçu « Le …, Dr Marie Leroy a écrit : » sans le corps), vert une fois restauré (1,7 min).
  - Code restauré après chaque mutation (marqueur `MUTATION task-350` à 0, `git status` propre).
  - Outillage rencontré :
    - `page.route` + `continue` court-circuite l'authentification des fixtures mobiles (401, « session expirée ») ;
    - une requête retardée, abandonnée par l'app, fait lever « already handled ».
    - D'où la latence CDP, consignée dans `conventions/e2e.md` › `retarder-une-requete-sans-casser-l-authentification`.
  - Ligne « Trous du filet » de task-350 complétée.
- **Passe qualité (/simplify)** :
  - relecture manuelle du diff de chaque repo (réutilisation : le snackbar existant côté Angular, le toast côté mobile, la règle factorisée côté mobile) ;
  - **aucune simplification appliquée**, donc pas de revalidation ni de commit de passe ;
  - contrôles mécaniques C# (S125, xUnit1045, S4457, xUnit2032) sur client-blazor : aucun résultat.
- **client-angular, fichiers modifiés (non commités)** :
  - `front/e2e/mss-e2e/specs/functional.e2e.ts`. Il porte **aussi** les trois corrections de tests de task-364, déjà non commitées avant cette task.
  - `front/libs/mss/src/core/utils/quoted-body.util.ts`
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose.component.{ts,spec.ts}`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.{ts,html,scss,spec.ts}`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.side-panel.spec.ts`
- **Pour l'humain** :
  - E2E-COMPOSE-002 est toujours en **quarantaine (task-350)**, dans `live-ai.e2e.ts` (Angular). Elle se lève une fois cette task mergée : **seul l'humain** retire la quarantaine.
  - Côté mobile, E2E-COMPOSE-002 n'est pas en quarantaine.
- **Journalisation** :
  - Blazor : l'échec est journalisé avec l'identifiant technique seulement (`Uid`, `Status`) ;
  - Angular et mobile : pas de journal client nouveau. L'échec du contenu reste journalisé côté api-mail, comme aujourd'hui.
- **DOD self-check** :
  - build et tests ✓ sur les 4 repos ;
  - tests Angular, mobile et bUnit demandés présents ✓ ;
  - E2E-DETAIL-001 v2 catalogué et implémenté dans les 2 clients ✓ ;
  - prouvé rouge sur le bug ✓, ligne « Trous du filet » ✓ ;
  - `data-testid` existants inchangés ✓, nouveaux : `mail-original-load-failed`, `mail-detail-reply`, `mail-detail-forward` ;
  - libellés FR en dur (Angular, mobile) et Localizer (Blazor) ✓ ;
  - aucune donnée de santé dans les journaux ✓.
- **Next step** : `/sonar task-350`
