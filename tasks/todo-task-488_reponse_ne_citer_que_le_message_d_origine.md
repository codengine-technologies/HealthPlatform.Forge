# todo-task-488.md — Réponse : ne citer que le message d'origine

**Repos**: api-mail, dtos-mss, client-mobile, client-angular
**Dependencies**: task-487
**Epic**: E024
**Priorité**: EPIC E024, demandée par l'humain le 2026-11-18, pendant la recette de task-487. Une réponse recopie
aujourd'hui tout l'historique du fil, données de santé comprises, à chaque échange et vers chaque destinataire, y
compris un confrère qui n'était pas dans l'échange. Ce n'est pas conforme à la minimisation (RGPD art. 5.1.c) ni au
secret partagé (CSP L.1110-4 : seulement les informations strictement nécessaires, aux professionnels qui prennent en
charge le patient).

## Décisions humaines (2026-11-18)

1. **Une réponse ne cite que le texte propre du message auquel on répond**, sans l'historique que ce message citait
   lui-même. S'applique à la réponse classique (weda2, mobile : Répondre, Répondre à tous) et à la réponse de la vue
   chat (task-487).
2. **Au moindre doute du découpage, la citation reprend tout le message** (comportement d'aujourd'hui, dans ce seul
   cas). Même règle que l'affichage de la vue chat (task-487) : rien ne manque au destinataire.
3. **Vers un destinataire qui n'était pas dans l'échange, la citation est retirée et le médecin en est averti** :
   « Citation retirée : {nom} ne faisait pas partie de l'échange. » Un bouton « Remettre la citation » la rétablit :
   le médecin garde la décision.
4. **Une case « Inclure le message d'origine », cochée par défaut, dans chaque saisie de réponse** (weda2, mobile, vue
   chat). Pas de réglage persistant.
5. **Le transfert est inchangé** : il envoie le message entier, par un acte volontaire, sans avertissement.

## Ce qui est établi

- **weda2** : `buildQuotedBody` (`libs/mss/src/core/utils/quoted-body.util.ts:245`) place après le repère
  `<!-- quote -->` l'en-tête « Le …, {expéditeur} a écrit : » puis, dans un `<blockquote>`, les mentions de pièces
  jointes et `originalBodyHtml(content)` : **le corps entier**, historique imbriqué compris. Le transfert passe par la
  même fonction (`kind: 'forward'`) avec l'en-tête « Message transféré ».
- **Mobile** : `buildQuote(orig.from, orig.sentDate, quotedBody)` (`mail-compose.component.ts:475-497`, `:1700`) cite
  `bodyHtml || body` : le corps entier.
- **Vue chat** : `ConversationReplyComposer` (api-mail, task-487) cite le dernier message du fil de la même façon
  (`blockquote`, « Le …, {nom} a écrit : »).
- **Le découpage existe côté serveur** : `ConversationQuoteSplitter` (task-487) sépare le texte propre d'un message de
  l'historique qu'il cite, en ne repliant que le texte retrouvé dans son parent, avec un indicateur « découpage sûr ».
  La vue chat le rend déjà par message (`NewText`, `IsSplitSafe`, `HasRichContent`). C'est la règle à réutiliser :
  **une seule règle, côté serveur**, jamais une seconde heuristique dans chaque client.
- **Les participants du fil sont connus côté serveur** : `ConversationParticipants.Of` (task-487, corrigé en recette
  pour la note à soi-même). La rédaction classique ne connaît que le message d'origine (De, À, Cc).
- **La signature** s'insère avant le repère de citation (weda2) : inchangé.
- **Les pièces jointes d'origine ne sont jamais renvoyées** par une réponse, seulement mentionnées (« [Pièce jointe :
  …] ») : inchangé.
- **api-mcp** : l'US ajoute une route et un champ de requête optionnel ; elle ne retire rien. À confirmer par
  `python Tools/contracts/mcp_impact.py check` au `/develop`.

## Objective

Quand le médecin répond, la citation ne reprend que ce que son correspondant vient d'écrire : le texte propre du
message auquel il répond. Le fil reste relié par les en-têtes `In-Reply-To` et `References`, et le logiciel du
correspondant le regroupe. Quand un destinataire nouveau entre dans l'échange, la citation n'y part pas sans que le
médecin l'ait voulu.

### Règles

- **Texte propre** : le texte du message auquel on répond, sans la citation qu'il porte, tel que le rend le découpage
  serveur. Sa mise en forme est celle du texte (paragraphes et retours à la ligne).
- **Doute** : découpage non sûr, ou texte propre porteur d'une mise en forme riche (un tableau, par exemple des
  résultats) → la citation reprend **tout le message**, en HTML, comme aujourd'hui.
- **Message sans parent dans le fil** (premier message) : son texte propre est son corps entier.
- **Destinataire nouveau** : une adresse (À, Cc) absente des participants du fil, la boîte exclue. Le contrôle se fait
  à chaque changement de destinataires et juste avant l'envoi. Retirer le destinataire nouveau rétablit la citation,
  sauf si le médecin a décoché la case.
- **Case « Inclure le message d'origine »** : la décocher retire le bloc cité (en-tête « a écrit » compris), la
  recocher le remet. Le texte saisi par le médecin et sa signature ne sont jamais touchés.
- **Transfert** : inchangé (message entier, en-tête « Message transféré »).
- **Vue chat** : la réponse cite le texte propre du dernier message du fil (règle de doute incluse) ; la case est
  sous la saisie. Les destinataires de la vue chat sont les participants du fil : aucun destinataire nouveau possible.

### Contrat (proposé, à confirmer au `/develop`)

- `GET api/v1/mail/{messageId}/reply-quote` → `ReplyQuoteDto` : expéditeur, date, `Text` (texte propre),
  `IsWholeMessage` (vrai = doute, citer `Html`), `Html` (corps entier, rempli seulement quand `IsWholeMessage`),
  `Participants` (participants du fil, boîte exclue). Erreurs en `ProblemDetails` (règle 12) : 404 message inconnu.
- `ConversationReplyRequestDto.IncludeOriginal` (booléen, vrai par défaut) : faux → aucune citation dans la réponse
  composée par le serveur.

## Definition of Done

- [ ] Build passes on every listed repo (0 errors).
- [ ] Tests pass on every listed repo (0 failures).
- [ ] **dtos-mss** : `ReplyQuoteDto`, `ConversationReplyRequestDto.IncludeOriginal` ; paquet publié, consommateurs
      .NET montés ; miroirs TypeScript sur les deux clients.
- [ ] **api-mail** : route de citation de réponse ; `ConversationReplyComposer` cite le texte propre et respecte
      `IncludeOriginal`. Le découpage réutilise `ConversationQuoteSplitter` (aucune règle dupliquée).
- [ ] Tests unitaires : texte propre d'une réponse Thunderbird, Outlook, Mailiz et plateforme (corpus anonymisé de
      task-487) ; doute → message entier ; tableau dans le texte propre → message entier ; premier message du fil →
      corps entier ; `IncludeOriginal` faux → aucune citation.
- [ ] **Test d'intégration de bout en bout (règle 1b)** pour `GET api/v1/mail/{messageId}/reply-quote` : un fil de
      trois messages déposé dans GreenMail ; pour la dernière réponse du confrère, qui cite l'historique,
      `Text` ne contient que son texte propre (aucune ligne de l'historique) et `IsWholeMessage` est faux ;
      `Participants` porte les participants du fil sans la boîte ; un message dont la citation n'est pas retrouvée
      rend `IsWholeMessage` vrai et `Html` complet. Cas d'échec : identifiant inconnu → 404 en `ProblemDetails`.
      Vu rouge.
- [ ] **Test d'intégration de bout en bout (règle 1b)** pour `POST …/conversation/{messageId}/reply` : le message reçu
      par GreenMail cite le texte propre du dernier message et **aucune ligne de l'historique imbriqué** ; avec
      `IncludeOriginal` faux, il ne porte ni en-tête « a écrit » ni `blockquote`, et garde `In-Reply-To` et
      `References`. Vu rouge.
- [ ] **weda2 (`client-angular`)** : Répondre / Répondre à tous citent le texte propre (ou le message entier en cas de
      doute) ; case « Inclure le message d'origine » ; retrait de la citation vers un destinataire nouveau, message
      « Citation retirée : … » et « Remettre la citation » ; transfert inchangé ; vue chat : case sous la saisie.
      Tests de composant : citation du texte propre, doute, case décochée puis recochée sans toucher au texte saisi ni
      à la signature, destinataire nouveau ajouté puis retiré, « Remettre la citation », transfert intact.
- [ ] **Mobile (`client-mobile`)** : même comportement dans la rédaction et dans la vue chat. Tests de composant
      équivalents.
- [ ] Scénario **E2E-QUOTE-001** ajouté dans `Api/Mail/e2e/scenarios.yml` (version 1, mobile : requis, angular :
      requis) et implémenté dans les deux clients : répondre à un message qui cite un historique ; la réponse relue du
      serveur ne contient que le texte propre du message d'origine.
- [ ] Scénario **E2E-QUOTE-002** ajouté (version 1, mobile : requis, angular : requis) et implémenté dans les deux
      clients : ajouter en copie un confrère absent de l'échange ; « Citation retirée » s'affiche ; la réponse relue
      du serveur ne porte aucune citation ; puis « Remettre la citation » la rétablit.
- [ ] Scénario **E2E-QUOTE-003** ajouté (version 1, mobile : requis, angular : requis) et implémenté dans les deux
      clients : dans la vue chat, décocher « Inclure le message d'origine » ; la réponse relue du serveur ne porte
      aucune citation.
- [ ] Libellés en français ; `data-testid` sur la case, le message de retrait et « Remettre la citation ».
- [ ] Aucune donnée de santé en clair dans les logs : ni corps, ni citation, ni texte saisi.

## Manual Test Plan

1. Backend : `cd Api/Mail && dotnet run` (ou l'AppHost). weda2 : `cd Client/Angular/front && npm run start:weda2`.
   Mobile : `cd Client/Mobile && npm start`.
2. Préparer un fil avec un confrère : un message reçu, votre réponse, puis sa réponse depuis Thunderbird ou Outlook,
   qui cite tout l'historique.
3. weda2, ouvrir la dernière réponse du confrère, « Répondre » : la citation ne contient que ce qu'il vient d'écrire,
   pas votre message précédent ni le premier. Envoyer ; dans la boîte du confrère, la réponse est rangée dans le fil.
4. « Répondre à tous », ajouter en copie un confrère qui n'était pas dans l'échange : « Citation retirée : … ne faisait
   pas partie de l'échange » s'affiche et la citation disparaît. Retirer ce destinataire : la citation revient.
   Le rajouter, puis « Remettre la citation » : elle revient malgré lui.
5. Décocher « Inclure le message d'origine » : la citation disparaît, votre texte et votre signature restent.
   Recocher : elle revient.
6. Répondre à un message dont le logiciel cite l'historique d'une façon inconnue (ou mal formée) : la citation reprend
   tout le message.
7. « Transférer » : le message entier part, comme avant.
8. Vue chat (weda2 et mobile) : répondre, puis dans la boîte du confrère, la citation ne reprend que son dernier
   message. Décocher la case sous la saisie, répondre : aucune citation.
9. Mobile : refaire 3 à 5 dans la rédaction.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — minimisation des données échangées, sans exigence DSR nouvelle
- **Exigences DSR honorées** : non applicable — la réponse reste un message MSSanté ordinaire, déjà conforme
- **INS** : non applicable — aucune identité patient manipulée
- **Authentification PS** : inchangée — PSC (e-CPS), eIDAS substantiel ; hors ligne sans carte, l'envoi attend la
  confirmation par la carte (task-320)
- **Habilitations** : personnes rattachées à la boîte sous verdict récent de l'opérateur (règle 14) ; la route de
  citation lit la boîte de la personne, comme la lecture d'un message
- **Interop CI-SIS** : non applicable pour le contenu ; transport inchangé (`In-Reply-To`, `References`, RFC 5322)
- **Tracé PGSSI-S** : aucun acte nouveau — le choix de citer n'est pas tracé ; l'envoi reste tracé au nom de la
  personne réelle (trace `MailReply`, famille `HealthDataAccess`, 3 653 jours)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — base de la boîte ; aucune donnée nouvelle stockée
- **AIPD / impact RGPD** : à mettre à jour — mesure de minimisation (RGPD art. 5.1.c) et de secret partagé (CSP
  L.1110-4) : moins de données de santé recopiées, aucune vers un destinataire nouveau sans choix du médecin
