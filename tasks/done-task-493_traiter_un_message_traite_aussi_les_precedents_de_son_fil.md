# todo-task-493.md — Traiter un message traite aussi les précédents de son fil

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
**Reprises**: 1
**Dependencies**: task-454, task-492
**Epic**: E024

> Demande humaine du 2026-11-22 : « lorsque je filtre par à traiter, [s']il s'agit d'une liste de messages issue
> d'une conversation, le fait de traiter le message doit traiter tous ceux qui s'y rattachent dans le fil de
> conversation. »
>
> Arbitrages de l'humain, le même jour :
> - **portée** : partout où « Traité » se propose (liste, détail, vue conversation, balayage mobile), pas seulement
>   dans la liste « À traiter » ;
> - **quels messages** : le message traité **et ceux arrivés avant lui** dans le fil. Une réponse plus récente reste
>   à traiter : on ne clôt jamais un message que le praticien n'a peut-être pas vu ;
> - **attribution** : un message du fil attribué à **une autre personne** n'est pas touché ; il reste dans son
>   « Pour moi » ;
> - **clients** : weda2 et mobile.
>
> `task-492` (puces à compteur) est en attente de merge et touche les mêmes écrans : cette task part de son état.

## Objectif

Quand le praticien marque « Traité » un message d'une conversation, il a traité l'échange jusque-là : les messages
précédents du même fil, encore à traiter, sortent avec lui de « À traiter ». Il n'a plus à cliquer « Traité » sur
chaque message d'un fil qu'il vient de lire en entier, et la liste « À traiter » ne garde que ce qui l'attend encore.

### Ce qui est établi

- **Le fil existe côté serveur** : `ThreadMessageIds.CollectAsync`
  (`Api/Mail/src/Infrastructure/Repositories/MailDb/ThreadMessageIds.cs`) réunit, de proche en proche, les messages
  liés par `Message-ID`, `In-Reply-To` et `References`. La vue conversation (task-487, `ConversationRepository`) s'en
  sert, en écartant les brouillons.
- **L'état « traité » est celui de la boîte, par `Message-ID`** (task-454) : `MailHandlingService`.
  - `MarkHandledAsync` (bouton, un message) refuse un compte rendu de biologie en attente d'acquittement
    (`PendingBiology`).
  - `HandleBulkAsync` (traitement groupé) ne touche que les messages **à traiter**, écarte la biologie en attente
    (`ExcludedBiology`), rend la liste des messages traités et de ceux à remettre (`Handled`, `PutBack`), que
    `UndoHandledAsync` (« Annuler ») sait défaire.
  - Chaque changement est tracé (`MailMarkedHandled`) au nom de la personne réelle, avec son geste, et publié en temps
    réel aux personnes de la boîte.
- **L'attribution** (task-457) : traiter un message clôt son attribution ; `MailAssignmentService` connaît la personne
  attribuée de chaque message.
- **api-mcp** ne lit pas les routes de traitement (`grep status/handled Api/Mcp` : rien).

### Règles

1. **« Traité » sur un message traite aussi ses précédents dans le fil**, où que le geste soit fait : liste (bouton de
   ligne), détail, vue conversation, balayage mobile, « Traité » sur une sélection.
2. **Les précédents** sont les messages du même fil **envoyés avant** le message traité (date d'envoi), dans tous les
   dossiers sauf la Corbeille, brouillons exclus. Les messages **plus récents** du fil ne sont jamais touchés.
3. **Seuls les messages à traiter changent d'état** : un message déjà traité (par une autre personne, avec son auteur)
   ou hors « À traiter » (historique, « Pour info », envoyé par la boîte) reste tel quel.
4. **Un message attribué à une autre personne n'est pas touché** : il reste à traiter, dans son « Pour moi ». Un message
   attribué à la personne qui agit est traité, et son attribution close, comme aujourd'hui.
5. **Biologie** : un compte rendu de biologie en attente d'acquittement reste à traiter. « Traité » n'écrit jamais
   d'acquittement. L'avis le dit (« 1 compte rendu de biologie reste à acquitter »), comme le traitement groupé.
6. **Le message sur lequel on agit** garde les refus d'aujourd'hui (biologie en attente : « Traité » refusé, rien
   d'autre n'est traité).
7. **L'avis dit ce qui a été fait** : « Traité » seul quand un seul message change ; « Traité — 3 messages du fil »
   sinon. **« Annuler »** (pendant la même fenêtre qu'aujourd'hui) remet **tous** ces messages dans l'état d'avant.
   **« Remettre à traiter »** sur un message ne remet que lui.
8. **Traçabilité** (règle 14) : chaque message traité porte sa propre trace `MailMarkedHandled`, au nom de la personne
   réelle et de son rôle, avec un geste qui distingue « traité avec son fil » du bouton. Le détail d'un message traité
   avec son fil dit « Traité par {personne} le … (avec le fil) ».
9. **Temps réel** : les autres personnes de la boîte voient sortir de « À traiter » tous les messages traités, et les
   compteurs (dossiers, tags, puces « À traiter » / « Pour moi ») baisser d'autant.

### Hors périmètre

- Les **gestes naturels** (répondre, transférer, ranger, rattacher à un patient) gardent leur effet sur le seul message
  concerné. Les étendre au fil serait une autre US, à décider par l'humain.
- « Traiter les N messages affichés » (vue par tag, liste « À traiter ») garde sa règle : il traite les messages
  affichés, sans remonter leurs fils.

## Definition of Done

- [ ] Build passes : api-mail, dtos-mss (si le contrat change), `nx build weda2`, client-mobile (0 erreur).
- [ ] Tests pass : api-mail, `nx test mss-lib`, `nx test weda2`, client-mobile (0 échec).
- [ ] Tests unitaires de la règle « précédents du fil à traiter » (service d'api-mail) : précédents seuls, plus récent
      exclu, déjà traité intact, attribué à un autre exclu, biologie en attente exclue, Corbeille et brouillons exclus,
      message hors fil (sans `References`) traité seul ; chacun vu rouge.
- [ ] Test d'intégration de bout en bout pour `PUT …/emails/{uid}/status/handled` : sur un fil de 4 messages reçus
      (A, B, C, puis D plus récent) dont B attribué à une autre personne et un compte rendu de biologie en attente,
      « Traité » sur C rend traités A et C (relus du serveur : `handling` de chaque message), B et D restent à
      traiter, la biologie reste à acquitter ; la réponse liste les messages traités et la biologie écartée ; une
      trace `MailMarkedHandled` par message traité, au nom de la personne réelle. Cas d'échec : C en biologie en
      attente → refus, aucun autre message touché. Vu rouge (règle 1b).
- [ ] Test d'intégration de bout en bout pour « Annuler » (`PUT …/emails/status/handled/undo`) appliqué à la réponse
      ci-dessus : A et C reviennent à leur état d'avant, relus du serveur. Vu rouge (règle 1b).
- [ ] Test d'intégration où **deux personnes agissent sur la même boîte** : la délégataire traite C ; la trace de A et
      de C porte la délégataire (RPPS, rôle), jamais le titulaire ; le titulaire voit A et C traités par elle.
- [ ] Tests de composant weda2 et mobile, chacun vu rouge : l'avis « Traité — N messages du fil » ; les messages du
      fil traités quittent la liste « À traiter » ; « Annuler » les remet ; le détail dit « (avec le fil) ».
- [ ] `data-testid` sur tout élément ajouté ; aucun texte en dur hors de la convention de chaque client.
- [ ] Contrat : si la réponse de « Traité » ou le geste changent, dtos-mss publié, consommateurs adaptés ;
      `contract_impact.py check` sans impact non adapté.
- [ ] Scénario **E2E-TRIAGE-008** (version 1, `mobile: requis`, `angular: requis`) ajouté à
      `Api/Mail/e2e/scenarios.yml` et implémenté dans les deux clients : le test dépose un fil de trois messages
      d'un confrère (le troisième en réponse aux deux premiers, puis un quatrième plus récent), tous à traiter ; le
      praticien marque « Traité » le troisième depuis la liste « À traiter » ; relu du serveur, les trois premiers
      sont traités par lui, le quatrième reste à traiter ; l'avis dit « 3 messages du fil » ; « Annuler » les remet à
      traiter, relus du serveur.
- [ ] Aucune donnée de santé dans les journaux ni dans l'avis (l'avis ne cite ni objet ni contenu).

## Manual Test Plan

- Backend : `cd Api/Mail && dotnet run --project src/AppHost` (profil de développement habituel).
- weda2 : `cd Client/Angular/front && npm run start:weda2`, ouvrir la messagerie.
- Mobile : `cd Client/Mobile && npm start`, ouvrir la boîte.
- Données : depuis une autre boîte, envoyer à la boîte de test un message M1, puis M2 en réponse à M1, puis M3 en
  réponse à M2 ; attendre qu'ils soient à traiter. Envoyer ensuite M4 en réponse à M3.

1. weda2, Boîte de réception, puce « À traiter » : M1, M2, M3, M4 y sont. Noter le compteur.
2. Marquer M3 « Traité » (bouton de la ligne) : l'avis dit « Traité — 3 messages du fil » ; M1, M2, M3 quittent la
   liste, M4 reste ; le compteur baisse de 3.
3. « Annuler » : M1, M2, M3 reviennent, le compteur aussi.
4. Ouvrir M2 et le marquer « Traité » depuis le détail : M1 et M2 sortent, M3 et M4 restent.
5. Ouvrir M1 : le détail dit « Traité par {vous} le … (avec le fil) ».
6. Attribuer M3 à une autre personne de la boîte, puis marquer M4 « Traité » : M3 reste à traiter (dans le « Pour
   moi » de la personne), M1, M2 et M4 sont traités.
7. Refaire 1 à 3 sur le mobile, avec le balayage « Traité ».

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du cabinet).
- **Vague Ségur** : hors Ségur — organisation du travail sur des messages déjà reçus, aucune exigence DSR nouvelle.
- **Exigences DSR honorées** : non applicable — aucun échange ni document nouveau.
- **INS** : non applicable — aucun patient manipulé ni identifié par ce geste.
- **Authentification PS** : inchangée — session PSC (e-CPS) de la messagerie ; le geste exige la session en ligne,
  comme « Traité » aujourd'hui.
- **Habilitations** : inchangées. Titulaire, délégataire et membre traitent comme aujourd'hui ; un délégataire ou un
  membre sans verdict récent de l'opérateur ne voit ni ne traite rien (règle 14). Les messages attribués à une autre
  personne ne sont pas touchés.
- **Interop CI-SIS** : non applicable — le fil est lu des en-têtes MSSanté standard (`Message-ID`, `In-Reply-To`,
  `References`), aucun document CDA produit.
- **Tracé PGSSI-S** : une trace `MailMarkedHandled` **par message traité**, au nom de la personne réelle (RPPS, nom
  PSC, rôle), avec la boîte, l'instant, le message et le geste « avec le fil » ; « Annuler » trace `MailMarkedToHandle`
  par message. Conservation inchangée : famille `HealthDataAccess`, 3 653 jours.
- **Consentement patient** : non applicable.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : oui — l'état de traitement est stocké dans la base de la boîte, environnement HDS existant ;
  aucune donnée nouvelle de santé.
- **AIPD / impact RGPD** : inchangée — même traitement (état de travail des messages), étendu à plusieurs messages par
  geste.

## Branches
- `api-mail` (pushed) : feat/task-493-traiter-un-message-traite-aussi-les — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-493-traiter-un-message-traite-aussi-les
- `client-mobile` (pushed) : feat/task-493-traiter-un-message-traite-aussi-les — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-493-traiter-un-message-traite-aussi-les
- `dtos-mss` (pushed, branche paresseuse créée par /develop : contrat `MailHandlingGesture.Thread` et `MailHandlingResultDto`) : feat/task-493-traiter-un-message-traite-aussi-les — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-493-traiter-un-message-traite-aussi-les
- `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` (au /start : `feature/nova-mss-weda-integration`) — humain gère branche, commit, push, PR TFS

## Develop log

- **Repos touchés** : `dtos-mss` (branche paresseuse créée ici), `api-mail`, `client-mobile`, `client-angular` (code seul).
- **DTOs publiés** : `HealthPlatform.Dtos.Mss` 627.0.0 → **632.0.0** (run CI 45580351081, succès) — geste `MailHandlingGesture.Thread = 8`
  (ajouté en fin, valeurs existantes inchangées) et `MailHandlingResultDto : MailHandlingDto { Thread }` (réponse du bouton
  « Traité », corps de « Annuler »). Bump d'`api-mail` seulement : `client-blazor` n'est pas dans la task et ne lit pas ces
  types (ajout pur, il compile sur 627).
- **Interop publié** : aucun changement.
- **Commits** :
  - dtos-mss : `504ca8f` feat(dto): geste Thread et réponse de « Traité » portant les messages du fil
  - api-mail : `569d51fd` chore(deps) bump 632.0.0 ; `ae26bb38` feat(handling) ; `54229a36` test(e2e) catalogue ; `499a6fa6` refactor simplify pass
  - client-mobile : `a551bc7` feat(mobile) ; `556be05` refactor simplify pass
  - client-angular : **non commité** (code seul), voir la liste plus bas.
- **Conception** :
  - api-mail : `MailHandlingService.MarkHandledAsync` (bouton) et `MarkHandledBulkAsync(…, withThread)` (« Traité » sur une
    sélection, `PUT …/bulk/status/handled?thread=true`) traitent les **précédents** du fil : envoyés avant le message
    (`MailThreadHandlingRule.IsPredecessor` : date d'envoi strictement antérieure, ni brouillon ni Corbeille), **à traiter**,
    pas attribués à une autre personne (attribution ouverte, `AssigneeTenantId` ≠ la personne qui agit) ; un compte rendu de
    biologie en attente est écarté et rendu dans `ExcludedBiology`. Geste `Thread`, une trace `MailMarkedHandled` par message
    au nom de la personne réelle. Le message lui-même garde ses refus (biologie en attente : 409, rien d'autre n'est touché).
    L'import Weda et « Traiter les N messages affichés » (sans `thread`) restent des gestes sur les seuls messages désignés.
  - Lecture des fils : `MailHandlingRepository.GetThreadsAsync` — une collecte pour tous les messages
    (`ThreadMessageIds.CollectAsync` à plusieurs départs), puis séparation en mémoire (`ThreadMessageIds.Roots`, union-find
    sur `In-Reply-To` / `References`), génération courante, biologie en attente en une requête.
  - Clients : l'avis dit « Traité — N messages du fil » (N > 1), sinon « Message traité » ; les précédents prennent l'état
    du message (même personne, même instant, geste `Thread`) et quittent « À traiter » / « Pour moi » ; « Annuler » renvoie
    `thread` tel quel au serveur ; le détail dit « Traité par … le … (avec le fil) ». weda2 : « Traité » sur la sélection
    passe `thread=true`, « Traiter les N messages affichés » non. Mobile : pas de « Traité » sur sélection (seulement les
    messages affichés), inchangé.
- **Contrat (Step 4c)** : `contract_impact.py check` →
  - api-mcp : aucun impact.
  - client-mobile : IMPACT « énumération MailHandlingGesture modifiée » → adapté : `Thread = 8` dans
    `src/app/core/models/mail.model.ts`, libellé dans `core/utils/mail-handling.util.ts`, `MailHandlingResultDto` lu par
    `mss-api.service.ts` / `mail-handling.service.ts`. L'impact reste listé (le contrat change bel et bien).
  - client-angular : même IMPACT → adapté de même (`libs/mss/src/core/models/mail.model.ts`, `core/utils/mail-handling.util.ts`).
- **Tests et preuves rouges (règle 1b)** :
  - Unitaires `MailHandlingServiceTests` (12 nouveaux) : précédents seuls, plus récent exclu, déjà traité intact, attribué à
    une autre personne exclu, attribué à soi traité, biologie en attente écartée, Corbeille et brouillons exclus, message hors
    fil traité seul, biologie sur le message lui-même (rien du fil), import Weda sans fil, « remis à traiter » rendu par
    `PutBack`, sélection avec / sans fil. **10 vus rouges** sur le service avant implémentation (stubs) ; les 2 gardes
    (« biologie sur le message », « sans fil ») vues rouges par mutation (M8, M9).
  - Intégration `FolderOperationsEndToEndTests.ThreadHandling` (vraie pile HTTP, service, dépôts, PostgreSQL, Dovecot) :
    - `HandlingAMessage_HandlesItsEarlierMessagesToHandle_ButNeitherTheLaterOne_NorSomeoneElses_NorThePendingBiology` —
      fil A, CR biologie signalé, B (attribué à la délégataire), C, D ; refus 409 sur le CR sans toucher A ; « Traité » sur C
      → réponse `thread.handled = [C, A]`, `excludedBiology = [CR]`, A relu traité (geste Thread, par le titulaire), B, D et
      le CR à traiter, B toujours dans le « Pour moi » de la délégataire, aucun acquittement, une trace par message traité
      (A : Thread, C : Button, au RPPS du titulaire), temps réel publié pour A et C.
    - `TheDelegateHandlesTheThread_TheJournalNamesHer_TheHolderSeesIt_AndUndoRestoresTheMessagesBefore` — la délégataire
      traite C : A, B, C relus « par » elle (RPPS, rôle), traces à son nom ; « Annuler » avec `thread` → A remis à traiter (il
      l'avait été), B et C sans état.
    - `TheBulkHandling_RaisesTheThreadOnlyWhenAsked` — `bulk` sans `thread` : B seul ; avec `thread=true` sur C : C et A
      (Thread), CR écarté, D à traiter.
  - **Mutations (toutes rouges, source restaurée, binaires recompilés ensuite)** : M1 bouton sans fil, M2 attribution
    ignorée, M3 plus récent traité, M4 sélection sans fil (contrôleur), M5 biologie traitée, M6 « Annuler » ne porte que le
    message, M7 Corbeille/brouillon traités, M8 biologie du message non refusée, M9 « affichés » avec fil, M10 dépôt sans
    fil. M1, M2, M4, M5, M6 rejouées rouges après la passe qualité. Limite : M6 rougit sur l'assertion de `thread.handled`
    (première affirmée), avant celle de la relecture après « Annuler ».
  - weda2 (vus rouges avant le code, 8) : `mail-handling.service.spec` (avis « Traité — 3 messages du fil », « Annuler »
    renvoie `thread`, précédents quittant « À traiter », précédents marqués « avec le fil » hors filtre, avis biologie,
    sélection avec / affichés sans fil), `mail-handling.util.spec` et `mail-detail.handled.spec` (« (avec le fil) »),
    `mail-list.gestures.spec` (les deux points d'entrée).
  - mobile (vus rouges avant le code, 6 ; « un seul message » = garde) : `mail-handling.service.spec`,
    `mail-handling.util.spec`, `mail-detail.handling.spec`.
  - **E2E-TRIAGE-008** (catalogue v1, mobile requis, angular requis) écrit avant les tests, implémenté dans
    `Client/Mobile/e2e/specs/functional.spec.ts` et `Client/Angular/front/e2e/mss-e2e/specs/functional.e2e.ts`, type-check
    vert. Banc `--serve-only` :
    - mobile : vert sur le code non muté (11 s) ; **rouge sous mutation client** (le client ignore `thread`) sur
      « l'avis compte les messages du fil » (le toast a dit « Message traité », capture vérifiée) ; restauré.
    - weda2 : **vert sur le code non muté** (14 s). **Preuve par mutation non obtenue** : `nx serve weda2` est tombé (code 1,
      sans message) à la recompilation de la mutation, puis le remontage a trouvé 5052/4200/8100 tenus par l'environnement
      de recette de l'humain (lancé à 10:47:11 : AppHost, `nx serve weda2`, `ng serve` mobile, proxy de développement). Rien
      n'a été arrêté. La mutation, restée dans l'arbre weda2 que la recette sert, a été retirée dans la minute ; l'arbre est
      revenu exactement à l'état validé (marqueur vert intact). Le piège est consigné (`conventions/e2e.md`,
      mutation-non-servie, variante « serveur tombé »). La mutation client est la même que celle prouvée rouge côté mobile.
- **Build / tests locaux** :
  - dtos-mss : build 0 erreur.
  - api-mail : build 0 erreur 0 avertissement ; suite complète verte deux fois (avant et après la passe qualité) :
    domaine 368, infrastructure 749, application 4 358, api 1 388, intégration 1 375 (+16 ignorés), 0 échec.
  - client-mobile : build vert ; suite complète **1 711/1 711**. Note : un passage antérieur, joué pendant la suite
    d'intégration api-mail, avait rendu 4 rouges dans `MailComposeComponent` (suggestions task-388, attente de 1 s d'un
    `ion-modal`) ; même rouge sur `develop` sous la même charge, vert au calme : flaky de charge, sans lien avec la task
    (mémoire de session).
  - client-angular : `nx build weda2` vert ; `nx test mss-lib` 1 948/1 948 (178 fichiers) ; `nx test weda2` 2 683/2 683 ;
    ESLint 0 erreur sur les fichiers touchés (spec e2e compris).
- **Passe qualité (/simplify)** :
  - Appliquée et commitée : api-mail 3 fichiers (`499a6fa6` : une seule passe « lu » et une seule publication temps réel
    pour le message et son fil, partie commune bouton / sélection factorisée, variantes de Message-ID réutilisées) ;
    client-mobile 1 fichier (`556be05` : suffixe du libellé porté par la table des gestes).
  - Appliquée, code seul non commité : client-angular 1 fichier (`mail-handling.util.ts`, même suffixe).
  - Écartés : repli client quand `thread` est absent (sert un client plus récent qu'un serveur), copie des champs dans le
    contrôleur, filtres Corbeille/Brouillons (règle affirmée par les tests de la DOD), partage des variantes avec
    `MailReplyRepository` (hors du diff).
  - Sautés (porteurs de contrat) : dtos-mss.
- **Prévention (règle d'or)** : `conventions/csharp.md` S125 → 37 (un « ; » de commentaire attrapé par le contrôle
  mécanique avant le commit) ; `conventions/e2e.md` mutation-non-servie → 9 (serveur weda2 tombé ; ne jamais laisser une
  mutation dans l'arbre Angular servi par la recette).
- **client-angular — fichiers à commiter sur TFS** (branche extraite : `feature/nova-mss-weda-integration`) :
  - `front/libs/mss/src/core/models/mail.model.ts` — `MailHandlingGesture.Thread = 8` (impact contract_impact
    « énumération MailHandlingGesture modifiée ») et `MailHandlingResultDto`.
  - `front/libs/mss/src/core/services/mss-api.service.ts` — `markHandled` rend `MailHandlingResultDto` ;
    `bulkMarkHandled(…, withThread)` (`?thread=true`).
  - `front/libs/mss/src/core/utils/mail-handling.util.ts` — libellé « (avec le fil) » (impact contract_impact).
  - `front/libs/mss/src/features/mail/services/mail-handling.service.ts` — avis « Traité — N messages du fil », précédents
    traités dans la liste, « Annuler » avec `thread`, sélection avec fil.
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.ts` — « Traité » sur la sélection avec fil.
  - Specs : `core/utils/mail-handling.util.spec.ts`, `features/mail/services/mail-handling.service.spec.ts`,
    `features/mail/components/mail-detail/mail-detail.handled.spec.ts`,
    `features/mail/components/mail-list/mail-list.gestures.spec.ts`.
  - E2E : `front/e2e/mss-e2e/specs/functional.e2e.ts` — E2E-TRIAGE-008.
- **DOD self-check** : build et tests des quatre dépôts ✓ ; tests unitaires du service (7 cas de la DOD + gardes) ✓ vus
  rouges ; intégration `status/handled` (fil A/B/C/D, B attribué, biologie, traces, échec 409) ✓ vu rouge ; intégration
  « Annuler » ✓ vu rouge (M6) ; deux personnes sur la boîte ✓ ; composants weda2 et mobile ✓ vus rouges ; aucun élément
  d'interface ajouté (libellés dans la convention de chaque client) ✓ ; contrat publié, consommateurs adaptés ✓ ;
  E2E-TRIAGE-008 au catalogue et dans les deux clients ✓ (preuve par mutation weda2 manquante, voir plus haut) ; aucune
  donnée de santé dans l'avis (compte de messages seulement) ni dans les journaux (UID, geste, nombre) ✓.
- **Vert marqué** : api-mail `499a6fa6`, client-mobile `556be05`, client-angular (arbre final) — `Tools/green/green.py`.
- **Étape suivante** : `/review task-493 --code`.

### Reprise 1 après /review

- **B1 (mobile, « Traité » sur une sélection sans fil)** : `MssApiService.bulkMarkHandled(…, withThread)` envoie
  `?thread=true` ; `MailHandlingService.handleMany(mails, withThread = false)` le transmet ; `InboxPage.bulkHandle()`
  passe `true`, « Traiter les N messages affichés » (`mail-list.component.ts`) reste sans fil. Points d'entrée recensés
  sur tout `src/` des deux clients, sans filtre : mobile `inbox.page.ts:1079` (sélection), `mail-list.component.ts:199`
  (affichés) ; weda2 `mail-list.component.ts` `bulkMarkHandled` (sélection, déjà adapté) et `handleDisplayed` (affichés).
  Specs vus rouges (paramètres ajoutés sans effet d'abord : 4 FAILED sur les assertions d'URL et d'arguments), puis
  verts : `mss-api.service.spec` (`?thread=true`), `mail-handling.service.spec` (sélection avec / affichés sans fil,
  et l'existant passé à `false` explicite), `inbox.page.spec` (`handleMany(…, true)`) ; `mail-list.handling.spec`
  (affichés, sans fil) inchangé et vert.
- **B2 (api-mail, CR sélectionné compté deux fois)** : les messages **désignés** par le geste (tous, pas seulement ceux
  traités) ne sont jamais candidats précédents (`HandlingPlan.Designated`). Test
  `MarkHandledBulkAsync_WithThread_ASelectedPendingReportThatIsAlsoAPredecessor_IsExcludedOnce` vu rouge
  (`[5, 5]` au lieu de `[5]`), puis vert ; mutation M12 (filtre retiré) rouge.
- **B3 (api-mail, « traité implique lu » des précédents non prouvé)** : `HandlingAMessage_…` affirme désormais, en
  précondition, que les cinq messages ne sont pas lus, puis que A (précédent) et C sont lus et D (plus récent) ne l'est
  pas ; `TheBulkHandling_RaisesTheThreadOnlyWhenAsked` relit A traité **et** lu. Mutation M11 (passe « lu » limitée aux
  messages désignés) : rouge sur « le précédent traité avec le fil est lu » et sur le tuple geste/lu de la sélection.
- **S1 (api-mail, dédoublonnage avant le filtre)** : `IsToHandle` filtre avant `DistinctBy(Message-ID)`. Test
  `MarkHandledAsync_APredecessorInTwoCopies_TheCopyToHandleIsKept` vu rouge (copie « Corbeille » gardée, INBOX
  ignorée), puis vert ; mutation M13 (ordre inversé) rouge.
- **S4 (e2e, fenêtre d'annulation de 6 s)** : dans les deux parcours E2E-TRIAGE-008, les quatre relectures serveur sont
  faites en une fois (`Promise.all`), puis « Annuler » est affirmé visible juste avant le clic. Type-check vert dans les
  deux suites, ESLint 0 erreur. **Rejeu `--serve-only` non fait** : 5052/4200/8100 sont tenus par la recette de
  l'humain (AppHost, `nx serve weda2`, `ng serve` mobile, lancés à 10:47:11), qui n'est pas arrêtée. La voie complète
  reste à `/e2e`.
- **S5** : le commentaire du cas d'échec dit qu'il est joué sur le compte rendu du fil, qui a A pour précédent.
- **Auto-contrôle du correctif** (ce que la reprise casse ailleurs) : `PredecessorsAsync` n'a que deux appelants
  (bouton : désignés = le message, comme avant ; sélection : désignés = toute la sélection) ; `handleMany` garde
  `false` par défaut, donc « messages affichés » (mobile et weda2) inchangé ; `bulkMarkHandled` sans `withThread`
  envoie la même URL qu'avant (spec existant vert).
- **Validation** : la recette de l'humain verrouille `Api/Mail/src/Api/bin` (5 processus `mss.mail.api`, non arrêtés) :
  build et suites d'api-mail joués dans un worktree détaché du même commit, patch de la reprise appliqué, contenu
  vérifié identique (`diff` des deux `git diff`). Mutations M11 à M13 jouées dans ce worktree.
- **Prévention** : `conventions/angular.md` `action-a-deux-entrees` → 2 (recenser les points d'entrée sur tout `src/` de
  chaque client, sans `head`) ; `conventions/csharp.md` S125 → 38.
- **Commits** : api-mail `22468e59` ; client-mobile `ba360d0` ; client-angular : `front/e2e/mss-e2e/specs/functional.e2e.ts`
  (S4) s'ajoute à la liste TFS, non commité.
- **Build / tests** : api-mail (worktree) build 0 erreur, suite complète 7 881 verts et **1 rouge d'environnement**
  (`AiDiagnosticsControllerIntegrationTests.DebugVectorSearchAsync_…`, « different vector dimensions 3 and 1536 », AppHost
  de recette en marche ; vert seul 2/2 — mémoire `integration-semantic-search-rouge-apphost-dev`) : **vert non marqué**,
  à rejouer par `/review`. client-mobile build vert, suite **1 713/1 713**, vert marqué. client-angular `nx build weda2`
  vert, mss-lib 1 948/1 948, weda2 2 683/2 683, vert marqué (arbre final).
- **Passe qualité** : aucune nouvelle (correctifs ciblés de la revue, sans code à simplifier).

## Sonar log

- Mode A (chaîné), serveur SonarQube 9.9.8 (`sonar.login`), conteneurs redémarrés (arrêtés depuis 40 h).
- Analyse en **Release** : la recette de l'humain verrouille les DLL `Debug` d'`Api/Mail/src/Api` (non arrêtée).
- Itérations : 2.
- Phase 1 (new code) : ✓ Quality Gate OK, new_coverage = 95,9 %.
- Phase 1 — Issues fixées : 1 smell (S125, `MailRepository.cs:2238`, « ; » en fin de commentaire venu du correctif
  `6bd1a610` du 2026-11-20, hors task-493) — `c6f6abde`. Aucun test ajouté (correction de commentaire).
- Phase 1 — Hotspots : 0.
- Phase 2 (legacy) : rien à traiter (0 bug, 0 vulnérabilité, 0 smell).
- Build / tests : ✓ vert aux deux itérations (Release, couverture OpenCover) — domaine 368, application 4 360,
  infrastructure 749, api 1 388, intégration 1 375 (+16 ignorés), 0 échec. Vert marqué (`--by sonar`).
- `conventions/csharp.md` : S125 → 39.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 95,7 % | 95,9 % | +0,2 pt |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 0 | 0 | 0 |
| Coverage (projet) | 97,5 % | 97,5 % | 0 |
| Duplication | 0,3 % | 0,3 % | 0 |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

Baseline : dernière analyse du projet (2026-11-21), avant la branche de la task.

## Lint log

- **client-angular** (code seul, branche `feature/nova-mss-weda-integration`, base `origin/next`) : lint clean → no work.
  - `nx run-many -t lint --projects=mss-lib` : 0 erreur (49 avertissements préexistants sur le projet). Contournement
    task-367 appliqué (`nx affected --projects=tag:scope:mss` ne restreint pas ; sortie JSON par `eslint` direct).
  - Fichiers de la task (`mail.model.ts`, `mss-api.service.ts`, `mail-handling.util.ts`, `mail-list.component.ts`,
    `mail-handling.service.ts`, `e2e/mss-e2e/specs/functional.e2e.ts`) : 0 erreur, 12 avertissements, **aucun sur une ligne
    ajoutée** (`git diff -U0 HEAD`).
  - Itérations : 0. Arbre inchangé : le vert marqué par `/develop` reste valide (`green.py check`).

## Lint mobile log

- **client-mobile** (`feat/task-493-traiter-un-message-traite-aussi-les`, `ba360d0`) : `npm run lint` → « All files pass
  linting ». Lint clean → no work, aucun commit. Itérations : 0. Le vert marqué par `/develop` (reprise 1) reste valide.

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail, client-mobile, dtos-mss touchés | ✅ verte (rejouée après correctif d'E2E-CONV-003) | 79 verts, 0 flaky, 0 rouge, 0 quarantaine | ~15 min |
| angular | api-mail, client-angular, dtos-mss touchés | ✅ verte | 100 verts, 1 flaky (E2E-SEARCH-004), 0 rouge, 1 quarantaine (E2E-COMPOSE-002, task-350) | ~15 min |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task (`feat/task-493-…`, E2E-TRIAGE-008 v1).
- **Premier passage mobile rouge** : E2E-CONV-003 (vue Conversation), rouge aux deux essais, sans lien avec le diff de la
  task — le fil était formé (chip « 2 messages » affiché à l'échec), c'est le test qui lisait l'écran par `isVisible()`
  juste après chaque rechargement. **Corrigé sur demande de l'humain** (`d748346`, client-mobile) : lecture par
  `isShown(…, 10 s)`, choix de la vue rejoué jusqu'à ce que le segment soit coché ; vert deux fois seul, **rouge sous
  mutation** (chip de fil masqué) sur « les deux messages forment un fil », témoin restauré vert ; voie complète
  rejouée verte. Prévention : `conventions/e2e.md` (`fil-depose-a-la-seconde` → 4, cause établie ;
  `isvisible-sans-attente` → 2). Le parcours weda2 a la même forme, vert ce jour, non modifié.
- Quarantaines : E2E-COMPOSE-002 [angular] (task-350), passé.
- Divergences ouvertes : celles du catalogue (recherche mobile, task-450 / task-451), inchangées.
- Parcours touchés sans spec e2e modifié : aucun (E2E-TRIAGE-008 ajouté dans les deux suites).
- Démontage : complet pour ce run (ports libres) ; deux conteneurs `e2e-greenmail-gcgjbrzp` / `e2e-dovecot-kgrndjwd`
  arrêtés depuis le 2026-10-14, antérieurs au run, laissés en place.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**Flaky (vert au second essai, non bloquant)** (1) :

- [angular] « recherche — un nom de patient sans accent trouve ses messages, puis les messages partiels » (E2E-SEARCH-004)

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-PATIENT-003 | 1 | headless | La fiche d'un patient ne montre pas les documents d'un autre patient du même mail | ✅ | ✅ |
| E2E-PATIENT-004 | 1 | headless | La vue « Mails du patient » reste ouverte et ses pages viennent du serveur | ✅ | — |
| E2E-CONTACT-001 | 2 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Écrire à l'adresse choisie d'un contact à plusieurs adresses, ou à son adresse par défaut | ✅ | ✅ |
| E2E-COMPOSE-005 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-MAIL-006 | 1 | headless | Glisser sur la Corbeille un message d'un fil supprime ce message, et lui seul | ✅ | — |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-DRAFT-004 | 1 | headless | Une rédaction sans texte dans le corps ne laisse ni brouillon ni question | ✅ | ✅ |
| E2E-BIO-001 | 2 | headless | Acquitter un compte rendu de biologie, à son nom | ✅ | ✅ |
| E2E-BIO-002 | 1 | headless | La puce « Bio à acquitter » montre tous les résultats en attente, sur toutes les pages | ✅ | ✅ |
| E2E-BIO-003 | 1 | headless | Lire un résultat HPRIM puis l'acquitter | ✅ | ✅ |
| E2E-BIO-004 | 1 | headless | Un compte rendu acquitté puis déplacé depuis un autre client garde son acquittement | ✅ | ✅ |
| E2E-BIO-007 | 1 | headless | Un compte rendu arrivé avant la date de début du suivi ne réclame rien, et s'acquitte quand même | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-DETAIL-006 | 1 | headless | Après une réponse, le message d'origine dit « Vous avez répondu à ce message le… » | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SETTINGS-004 | 1 | headless | Paramètres indisponibles : rien n'est écrasé | ✅ | — |
| E2E-SEARCH-001 | 2 | headless | Composer ses critères puis lancer la recherche | ✅ | ✅ (v1) · divergence (task-450) |
| E2E-SEARCH-002 | 1 | headless | Un mot rare et accentué trouve le message qui le contient | ✅ | ✅ |
| E2E-SEARCH-003 | 1 | headless | Un numéro de dossier trouve son message, et un seul | ✅ | ✅ |
| E2E-SEARCH-004 | 1 | headless | Un nom de patient tapé sans accent ni majuscule trouve ses messages, puis les messages partiels | ⚠️ flaky | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-005 | 1 | headless | Un mot absent de la boîte affiche « Aucun résultat » | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-006 | 1 | headless | Plus de résultats qu'une page — « Voir plus » affiche la suite, jusqu'au dernier | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-007 | 1 | headless | Une recherche en échec affiche un message, et l'ancienne liste n'est plus affichée | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-009 | 1 | headless | Fermer la recherche rend le dossier à la même position ; retirer une étiquette relance sans elle | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-010 | 1 | headless | Reconnaître un résultat et ouvrir le dossier du patient | ✅ | ⛔ non joué · divergence (task-451) |
| E2E-SEARCH-012 | 1 | headless | Traiter tous les résultats d'une recherche | ✅ | ⛔ non joué · divergence (task-451) |
| E2E-SEARCH-015 | 1 | headless | Le détail surligne ce qui a été cherché | ✅ | — |
| E2E-SEARCH-008 | 1 | headless | Restreindre la recherche à un patient et à ses biologies anormales | ✅ | ⛔ non joué · divergence (task-451) |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 2 | headless | Créer un contact à deux adresses, le modifier sans les perdre, puis le supprimer | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-CONTACT-004 | 1 | headless | Consulter un contact depuis le carnet et lui écrire | ✅ | ✅ |
| E2E-CONTACT-005 | 1 | headless | Une fiche modifiée ne se perd pas sans confirmation, une adresse mal formée est refusée | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 2 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ | ✅ |
| E2E-MAILBOX-003 | 2 | headless | Rattacher ses boîtes depuis « Mes boîtes » en un geste — titulaire et membre | ✅ | ✅ |
| E2E-MAILBOX-006 | 1 | headless | Après le rattachement, l'identité d'expéditeur et la signature sont déjà là | ✅ | ✅ |
| E2E-MAILBOX-004 | 1 | headless | Ajouter une BAL déléguée par saisie — et refus de sa propre adresse | ✅ | ✅ |
| E2E-MAILBOX-005 | 1 | headless | Le délégataire refusé par l'opérateur perd l'accès, en ligne puis hors ligne ; le titulaire garde le sien | ✅ | ✅ |
| E2E-AUDIT-001 | 1 | headless | Le titulaire lit au journal le message supprimé par son délégataire, au nom du délégataire | ✅ | — |
| E2E-AUDIT-002 | 1 | headless | Le journal d'audit montre chaque action sur un mail | ✅ | — |
| E2E-SHARED-001 | 1 | headless | Une boîte partagée, une base — le patient rattaché par le titulaire est vu du délégataire, la signature reste à chacun | ✅ | ✅ |
| E2E-SHARED-002 | 1 | headless | Le délégataire écrit pour le compte du titulaire — le destinataire voit qui a écrit, sa réponse revient à la boîte | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |
| E2E-SESSION-004 | 1 | headless | Sur un appareil partagé, la personne suivante n'arrive jamais dans la boîte de la précédente | ✅ | ✅ |
| E2E-AI-002 | 1 | headless | Un délégataire interroge l'assistant dans la boîte qu'il a ouverte | ✅ | ✅ |
| E2E-MAILBOX-007 | 1 | headless | Après un changement de boîte, l'onglet Patients ne montre plus rien de la précédente | ✅ | ✅ |
| E2E-ERROR-001 | 1 | headless | Une erreur affiche un code et une référence à transmettre au support | ✅ | ✅ |
| E2E-TAG-001 | 1 | headless | Choisir un tag de la boîte dans la liste, créer un tag de plusieurs mots | ✅ | ✅ |
| E2E-TAG-002 | 2 | headless | Les tags système classent la Boîte de réception : Biologie, Patient, Pour info | ✅ | ✅ |
| E2E-TAG-003 | 1 | headless | Combiner deux tags et retrouver le filtre « Non lus » | ✅ | ✅ |
| E2E-TAG-004 | 1 | headless | Une combinaison de tags où rien n'est à traiter s'ouvre sur « Tous », le réglage reste « À traiter » | ✅ | ✅ |
| E2E-TRIAGE-001 | 2 | headless | Traiter un message le retire de « À traiter », le compteur baisse, « Annuler » le remet | ✅ | ✅ |
| E2E-TRIAGE-002 | 1 | headless | Traiter les messages affichés laisse le compte rendu de biologie à acquitter | ✅ | ✅ |
| E2E-TRIAGE-006 | 1 | headless | Dans la vue « Biologie », « Traiter les résultats sans anomalie » laisse le résultat anormal à traiter | ✅ | ✅ |
| E2E-TRIAGE-007 | 1 | headless | Répondre à un message le fait sortir de « À traiter », libellé « — répondu » | ✅ | ✅ |
| E2E-TRIAGE-008 | 1 | headless | « Traité » sur un message d'un fil traite aussi ses précédents, jamais le plus récent ; « Annuler » les remet | ✅ | ✅ |
| E2E-SHARED-003 | 1 | headless | Le délégataire traite un message, le titulaire le voit traité « par » le délégataire | ✅ | ✅ |
| E2E-ASSIGN-001 | 2 | headless | Le titulaire attribue un message à la secrétaire délégataire, qui le trouve dans « Pour moi » | ✅ | ✅ |
| E2E-ASSIGN-002 | 1 | headless | Traiter un message attribué le retire de « Pour moi », et le détail dit « traité par » | ✅ | ✅ |
| E2E-ASSIGN-003 | 1 | headless | La puce « Pour moi » porte son compteur, n'apparaît pas à zéro et reste affichée quand on traite le dernier | ✅ | ✅ |
| E2E-CONV-001 | 1 | headless | Lire un fil en vue chat et y répondre en une ligne, à tous les participants | ✅ | ✅ |
| E2E-CONV-002 | 1 | headless | Joindre un fichier depuis la vue chat | ✅ | ✅ |
| E2E-CONV-003 | 1 | headless | La vue chat s'ouvre d'elle-même sur un fil engagé, et n'existe qu'en mode Conversation | ✅ | ✅ |

**Divergences temporaires ouvertes** (9) :

- E2E-SEARCH-001 [mobile] — le mobile adopte le formulaire à un seul niveau avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-004 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-005 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-006 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-007 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-009 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-010 [mobile] — la lecture enrichie arrive sur le mobile avec la refonte mobile — résorbée par task-451
- E2E-SEARCH-012 [mobile] — la sélection de tous les résultats arrive sur le mobile avec la refonte mobile — résorbée par task-451
- E2E-SEARCH-008 [mobile] — les critères médicaux arrivent sur le mobile avec la refonte mobile — résorbée par task-451

**Parité : verte** — aucun écart entre le catalogue et les suites.

## Code Review Summary

### Passage 1 (revue anticipée) — CHANGES REQUESTED

Revue du diff de `dtos-mss` (`504ca8f`), `api-mail` (`499a6fa6`), `client-mobile` (`556be05`) et de l'arbre non commité de
`client-angular` (`feature/nova-mss-weda-integration`), par un relecteur indépendant (code seul, sans le `## Develop log`),
puis vérification de chaque constat dans le code.

**4c — consommateurs du contrat** (`contract_impact.py check`) :
- api-mcp : aucun impact.
- client-mobile : IMPACT « énumération MailHandlingGesture modifiée » → adapté (`Thread = 8`, libellé, `MailHandlingResultDto`).
- client-angular : IMPACT « énumération MailHandlingGesture modifiée » → adapté (arbre non commité, liste TFS au `## Develop log`).

**4b — clause DOD du parcours** : E2E-TRIAGE-008 v1 au catalogue (`Api/Mail/e2e/scenarios.yml`), v1 dans les deux clients ✓.

**4a — comportement → test d'intégration → preuve rouge** :

| Comportement (endpoint) | Test d'intégration | Preuve rouge |
|---|---|---|
| `PUT …/{uid}/status/handled` : précédents à traiter traités, geste Thread, plus récent intact | `HandlingAMessage_HandlesItsEarlierMessagesToHandle_…` | M1, M3, M10 |
| idem : attribué à une autre personne intact, reste dans son « Pour moi » | même test | M2 |
| idem : CR de biologie du fil écarté, rendu dans `thread.excludedBiology`, aucun acquittement | même test | M5 |
| idem : refus 409 sur un CR en attente, précédent intact | même test | M8 (unitaire) |
| idem : une trace par message, au nom de la personne réelle (délégataire) | même test + `TheDelegateHandlesTheThread_…` | M1 |
| `PUT emails/status/handled/undo` avec `thread` : tous les messages remis | `TheDelegateHandlesTheThread_…` | M6 (rouge sur `thread.handled`, avant la relecture) |
| `PUT …/bulk/status/handled?thread=true` / sans `thread` | `TheBulkHandling_RaisesTheThreadOnlyWhenAsked` | M4, M9 |
| idem : **les précédents traités sont marqués lus** (« traité implique lu ») | **aucun** | **aucune** → B3 |

**Constats vérifiés** :
- ❌ **B1** — `client-mobile` : « Traité » sur une sélection ne traite jamais le fil. `inbox.page.ts:1079` (`bulkHandle()`)
  appelle `handleMany(mails)`, et ni `MailHandlingService.handleMany` ni `MssApiService.bulkMarkHandled` ne savent envoyer
  `?thread=true`. Règle 1 (« Traité » sur une sélection, dans les deux clients). weda2 a été adapté, le mobile non : le
  recensement des appelants de `/develop` a été tronqué (`| head`).
- ❌ **B2** — `api-mail` `MailHandlingService.HandleBulkAsync` / `PredecessorsAsync` : un compte rendu de biologie
  **sélectionné** (donc dans `excluded`) qui est aussi un précédent d'un autre message sélectionné revient dans
  `thread.ExcludedBiology` (`seedIds` ne contient que les messages traités) ; `Concat` ne dédoublonne pas. Sélection {CR, C}
  avec `thread=true` → `ExcludedBiology = [CR, CR]`, avis « 2 comptes rendus de biologie restent à acquitter » pour un seul
  (règles 5 et 7).
- ❌ **B3** — règle 1b : « traité implique lu » est un comportement nouveau pour les précédents du fil (une passe « lu »
  pour le message et son fil, `HandleAsync`), atteignable par `PUT …/status/handled` et `bulk?thread=true`, et aucun test
  d'intégration ne relit `isRead` d'un précédent.
- ⚠️ **S1** — `PredecessorsAsync` : `DistinctBy(MessageId)` passe **avant** le filtre `IsToHandle`. Deux copies d'un même
  précédent : la copie gardée peut être celle qui n'est pas à traiter (Corbeille reconnue à son seul nom, dossier
  d'auto-action), et la copie de la Boîte de réception reste à traiter. Filtrer, puis dédoublonner.
- ⚠️ **S4** — e2e E2E-TRIAGE-008 (mobile `functional.spec.ts`, weda2 `functional.e2e.ts`) : entre la réponse de « Traité » et
  le clic « Annuler », les deux tests attendent l'avis, la sortie de 3 lignes et font 4 relectures serveur ; la fenêtre
  d'annulation est de 6 s. Rouges intermittents à prévoir (convention `fenetre-annulation`). Relire les états serveur
  en parallèle, et affirmer que « Annuler » est encore visible juste avant le clic.
- ⚠️ S2 — aucune preuve d'intégration de l'exclusion Corbeille / brouillons (couverte par l'exclusion « À traiter » des
  dossiers d'auto-action, et par les tests unitaires). Non bloquant.
- ⚠️ S3 — performance : chaque « Traité » lance la collecte du fil (`References LIKE` sans index, au moins deux passes) ; une
  sélection sans borne avec `thread=true` porte N motifs par passe. À mesurer au banc (boîte cible ~10 000 messages) ; non
  bloquant pour cette task.
- ⚠️ S5 — le cas d'échec de la DOD (« C en biologie en attente ») est joué sur le CR, qui a A pour précédent : équivalent, à
  dire dans le commentaire du test.
- ✅ Vérifié correct : états d'avant lus avant toute écriture ; attribution comparée par `TenantId` (même clé que
  `MailAssignmentService`), traiter clôt l'attribution et « Annuler » la rouvre ; une trace `MailMarkedHandled` par
  précédent, geste Thread, au nom de la personne ; refus en problem+json ; import Weda et « messages affichés » ne remontent
  pas le fil ; `Thread = 8` ajouté en fin, tables des clients complètes ; `MailHandlingResultDto` additif ; aucune donnée de
  santé dans les journaux ni dans l'avis.

#### À corriger par la reprise
1. **B1** — `client-mobile` : `bulkMarkHandled(…, withThread)` (`?thread=true`), `handleMany(mails, withThread = false)`,
   `inbox.page.ts` `bulkHandle()` passe `true`, `handleDisplayed()` reste sans fil ; un spec par point d'entrée, vus rouges.
   Prévention : `conventions/angular.md` `action-a-deux-entrees` (récidive : un point d'entrée d'un client oublié), et le
   recensement des appelants se fait sans `| head`.
2. **B2** — `api-mail` : les messages désignés (tous, pas seulement ceux traités) ne sont jamais candidats précédents, et
   `ExcludedBiology` est dédoublonné ; test unitaire vu rouge (sélection {CR, C}, `thread=true` → un seul CR écarté).
3. **B3** — `api-mail` : test d'intégration qui relit `isRead` des précédents traités (non lus avant le geste), vu rouge par
   mutation (passe « lu » limitée au message).
4. **S1** — `api-mail` : filtrer `IsToHandle` avant le dédoublonnage par `Message-ID` ; test unitaire vu rouge (deux copies,
   la première hors « À traiter »).
5. **S4** — e2e des deux clients : relectures serveur des messages traités en parallèle (`Promise.all`), puis « Annuler »
   affirmé visible avant le clic ; parcours mobile rejoué vert (`--serve-only`), weda2 au type-check si ses ports sont pris.

#### Arbitrage humain
- Aucun.

### Passage 2 (revue anticipée) — APPROVED

**Approved at** : dtos-mss `504ca8f` · api-mail `22468e59` · client-mobile `ba360d0` · client-angular `feature/nova-mss-weda-integration`
(`b5add4e3` + arbre non commité, marqueur vert de l'arbre final).

Relecture indépendante du **diff de la reprise d'abord** (api-mail `499a6fa6..22468e59`, mobile `556be05..ba360d0`, spec e2e
weda2), à la recherche de ce qu'elle a cassé : appelants de `PlanAsync` / `HandlingPlan` / `PredecessorsAsync` (vue par tag
sans fil, bouton après le refus `NoMessageId`, gestes naturels hors plan), comparateur de `Designated` (ordinal, comme
avant), assertions existantes (aucune affaiblie : `toHaveBeenCalledWith(…, false)` plus strict, « affichés » toujours gardé
par `mail-list.handling.spec`), précondition « non lu » (lecture `GET emails/{uid}` sans effet de lecture, messages déposés
par un autre client IMAP), lectures en parallèle e2e (aucune convention ne les interdit). Rien de cassé.

**4c** inchangé : api-mcp aucun impact ; client-mobile et client-angular IMPACT « énumération MailHandlingGesture modifiée »,
adaptés. **4b** : E2E-TRIAGE-008 v1. **4a** : la ligne « précédents marqués lus » a désormais son test
(`HandlingAMessage_…`, `TheBulkHandling_…`) et sa preuve rouge (M11).

| Constat | Statut | Preuve |
|---|---|---|
| B1 mobile, sélection sans fil | corrigé | `inbox.page.spec` (`handleMany(…, true)`), `mail-handling.service.spec`, `mss-api.service.spec` (`?thread=true`), vus rouges |
| B2 CR sélectionné compté deux fois | corrigé | `…_IsExcludedOnce` vu rouge (`[5, 5]`), M12 |
| B3 « lu » des précédents | corrigé | précondition non lus, A et C lus, D non lu ; M11 rouge |
| S1 copie à traiter gardée | corrigé | `…_TheCopyToHandleIsKept` vu rouge, M13 |
| S4 fenêtre d'annulation e2e | corrigé (non borné) | relectures en une fois, « Annuler » affirmé visible |
| S5 commentaire du cas d'échec | corrigé | — |

**Suggestions (non bloquantes, pour la PR)** :
- ⚠️ Mobile `applyBulk` : les précédents rendus par `?thread=true` sont posés localement avec le geste `Bulk` et sans auteur
  (« (avec le fil) » absent jusqu'au temps réel ou au rechargement). Appliquer `Thread` aux clés traitées non sélectionnées.
- ⚠️ Sélection sur deux dossiers (mobile et weda2 : une requête par dossier) : un message sélectionné dans un dossier peut
  être précédent d'un message sélectionné dans l'autre ; il serait traité deux fois et un CR compté deux fois. Dédoublonner
  les résultats fusionnés par clé (`mergeResults`, `handleBulk`). Cas rare (fil dont les messages sont rangés dans deux
  dossiers et sélectionnés ensemble).
- ⚠️ E2E-TRIAGE-008 : borner le temps entre la réponse de « Traité » et le clic « Annuler » (convention `geste-differe`),
  ou relire les quatre messages en un seul `GET emails/{u1,…,u4}`.
- ⚠️ `TheBulkHandling_RaisesTheThreadOnlyWhenAsked` : affirmer A non lu avant le geste, dans le test même.
- ⚠️ (passage 1, S2, S3) preuve d'intégration Corbeille / brouillons ; coût de la collecte du fil au banc (boîte cible
  ~10 000 messages).

#### Arbitrage humain
- Aucun.

### Validation finale — APPROVED

- Build + tests : api-mail vert de `/sonar` réutilisé (`c6f6abde`) ; client-angular vert de `/develop` réutilisé (arbre
  final) ; dtos-mss build rejoué (0 erreur) ; client-mobile rejoué après le correctif d'E2E-CONV-003 : build vert,
  **1 713/1 713**.
- Revue du diff postérieur à l'approbation : `c6f6abde` (S125, commentaire seul) ✅ ; `d748346` (E2E-CONV-003 : lecture
  par attente bornée, choix de la vue rejoué ; rouge sous mutation, témoin vert) ✅.
- 4a : table du passage 1 complétée par M11 (passage 2) ✅. 4b : `## E2E log` **vert** ✅, E2E-TRIAGE-008 v1 ✅.
  4c : inchangé (impacts adaptés) ✅.
- DOD : build et tests des quatre dépôts ✓ ; tests unitaires du service ✓ (vus rouges) ; intégration `status/handled`,
  « Annuler », deux personnes sur la boîte ✓ (vus rouges) ; composants weda2 et mobile ✓ ; aucun élément d'interface
  ajouté ✓ ; contrat publié (632.0.0) et consommateurs adaptés ✓ ; E2E-TRIAGE-008 au catalogue et dans les deux clients,
  vert dans les deux voies ✓ ; aucune donnée de santé dans l'avis ni les journaux ✓. Observables (étapes 1 à 7 du plan
  de test) : au test manuel (HAG).
- Branches à jour avec `develop` (aucun retard), PR ouvertes, label `awaiting-human-merge`.

## PRs

- dtos-mss : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/73 — `awaiting-human-merge`
- api-mail : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/380 — `awaiting-human-merge`
- client-mobile : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/134 — `awaiting-human-merge`
- client-angular : code-only — humain gère commit/push TFS et ouverture PR, sur `feature/nova-mss-weda-integration`.
  Liste des fichiers modifiés :
  - `front/e2e/mss-e2e/specs/functional.e2e.ts`
  - `front/libs/mss/src/core/models/mail.model.ts`
  - `front/libs/mss/src/core/services/mss-api.service.ts`
  - `front/libs/mss/src/core/utils/mail-handling.util.spec.ts`
  - `front/libs/mss/src/core/utils/mail-handling.util.ts`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.handled.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.gestures.spec.ts`
  - `front/libs/mss/src/features/mail/services/mail-handling.service.spec.ts`
  - `front/libs/mss/src/features/mail/services/mail-handling.service.ts`
- Ordre de merge (règle 11, US complète) : dtos-mss, puis api-mail, puis client-mobile, avec le commit TFS de weda2.

## Timings

*(généré par `tools/timing/report.sh --task task-493 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 27 s | — | — | — | — |
| /develop | ok | 19 min 12 s | 13 (2 min 59 s) | 29 (37 min 32 s) | — | dtos-mss 1B/0T, api-mail 6B/20T, client-mobile 3B/3T, client-angular 3B/6T, reprise 1 |
| /review-code | ok | 3 min 05 s | — | — | — | — |
| /sonar | ok | 23 min 02 s | 2 (1 min 56 s) | 10 (16 min 35 s) | 4 (1 min 40 s) | 2 itération(s), api-mail 2B/10T |
| /lint-angular | ok | 56 s | — | — | — | lint clean |
| /lint-mobile | ok | 16 s | — | — | — | lint clean |
| /e2e | ok | 49 min 47 s | — | — | — | e2e ×4 (42 min 26 s) |
| /review | ok | 2 min 26 s | 2 (10 s) | 1 (20 s) | — | dtos-mss 1B/0T, client-mobile 1B/1T |
| **Total cycle** | | **1 h 39 min** | **17 (5 min 06 s)** | **40 (54 min 28 s)** | **4 (1 min 40 s)** | |

Autres commandes mesurées : lint ×2 (19 s), nuget-wait ×1 (15 s)
