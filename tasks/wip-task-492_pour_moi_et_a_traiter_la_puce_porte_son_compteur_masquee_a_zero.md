# todo-task-492.md — « Pour moi » et « À traiter » : la puce porte son compteur, masquée à zéro

**Repos**: client-angular, client-mobile, api-mail
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
