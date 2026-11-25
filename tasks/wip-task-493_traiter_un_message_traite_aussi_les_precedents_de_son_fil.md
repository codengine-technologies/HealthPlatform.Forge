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

## Timings

*(généré par `tools/timing/report.sh --task task-493 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 27 s | — | — | — | — |
| /develop | ok | 19 min 12 s | 13 (2 min 59 s) | 29 (37 min 32 s) | — | dtos-mss 1B/0T, api-mail 6B/20T, client-mobile 3B/3T, client-angular 3B/6T, reprise 1 |
| /review-code | changes | 5 min 13 s | — | — | — | reprise 1 |
| **Total cycle** | | **24 min 53 s** | **13 (2 min 59 s)** | **29 (37 min 32 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : nuget-wait ×1 (15 s)
