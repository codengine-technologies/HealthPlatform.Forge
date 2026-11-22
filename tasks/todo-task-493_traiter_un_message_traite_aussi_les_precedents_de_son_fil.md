# todo-task-493.md — Traiter un message traite aussi les précédents de son fil

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
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
