# todo-task-152.md — Chat IA contextuel multi-emails sur mobile

**Repos**: client-mobile
**Dependencies**: todo-task-141
**Epic**: E012

## Objective

Porter sur `client-mobile` le **chat IA contextuel multi-emails** de
`client-angular` (`ai-chat-panel`, E009-F013) : le médecin sélectionne un ou
plusieurs messages, ouvre une conversation avec l'IA et pose des questions
ouvertes ; l'IA répond en **citant les emails sources** et refuse toute
fabrication.

1. **Entrée** : depuis le mode sélection de l'inbox (task-141), action
   « Analyser avec l'IA » ; depuis le détail d'un mail, action « Poser une
   question à l'IA » (contexte mono-mail).
2. **Écran de chat** (modale plein écran mobile) : création de conversation
   (`createConversation` avec les uids sélectionnés), messages streamés en
   SSE (`streamMessage` — mécanique fetch/SSE identique à Angular), rendu
   markdown assaini (réutiliser la chaîne de rendu de `mail-summary`),
   suppression de conversation (`deleteConversation`).
3. **Actions métier depuis le chat** (adaptation mobile des 5 actions web) :
   composer un email, répondre à un email cité, **appeler le patient**
   (`tel:`), **envoyer un SMS** (`sms:`), contacter un confrère (compose
   pré-adressé).
4. **Dégradation gracieuse** : service IA indisponible → message neutre, le
   reste de l'app n'est pas affecté (même posture que `mail-summary`).

US **frontend-only** : endpoints existants (Angular
`mss-api.service.ts:1942/1960/2061`). Aucun changement backend ni DTO.
L'IA reste **désactivable par paramètre d'établissement** (comportement
serveur existant : le mobile masque l'entrée si le service répond indisponible/désactivé).

## Definition of Done

- [ ] Build passe (`npm ci && npm run build`) — 0 erreur
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`) — 0 échec
- [ ] `MssApiService` : `createConversation` + `streamMessage` (SSE fetch) + `deleteConversation` + tests
- [ ] Entrée depuis la sélection multiple (N mails) et depuis le détail (1 mail)
- [ ] Streaming visible token par token ; interruption réseau → message d'erreur propre, conversation conservée
- [ ] Réponses avec **citations des emails sources** rendues (liens/tap → ouvre le mail cité)
- [ ] 5 actions métier opérantes (compose, répondre, `tel:`, `sms:`, confrère)
- [ ] IA indisponible → message neutre, aucune régression sur l'inbox
- [ ] Tests : création conversation, parsing du flux SSE, rendu citations, actions métier
- [ ] Libellés FR en dur ; `data-testid` sur entrée chat, champ, messages, actions
- [ ] Aucun contenu médical dans les logs client

## Manual Test Plan

- `cd Client/Mobile && npm start` ; inbox avec ≥ 3 mails d'un même patient
- Sélectionner 3 mails (appui long) → « Analyser avec l'IA »
- Poser « Quelle est l'évolution de la créatinine ? » → réponse streamée avec citations ; taper une citation → le mail s'ouvre
- Utiliser « Appeler le patient » → l'app téléphone s'ouvre avec le numéro
- Fermer/rouvrir le chat → conversation retrouvée ; la supprimer → disparue
- Couper le service IA → nouvelle question → message neutre d'indisponibilité

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors DSR nouvelle — parité web (E009-F013)
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable côté client — le contexte transmis à l'IA est assemblé côté serveur (canal existant)
- **Authentification PS** : session existante, inchangée
- **Habilitations** : inchangées — conversations cloisonnées par praticien
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : usage IA journalisé côté serveur (canal existant) ; aucun contenu médical dans les logs client
- **Consentement patient** : non applicable — aide à la lecture pour le PS, pas de nouveau partage de données
- **Référentiels métier** : aucun nouveau
- **Hébergement HDS** : oui — la posture IA d'établissement (on-premise/cloud, désactivable) est celle du backend, inchangée
- **AIPD / impact RGPD** : inchangé — même traitement IA que le web, nouveau canal d'affichage
