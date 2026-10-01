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
