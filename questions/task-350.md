# questions/task-350.md — /review : CHANGES REQUESTED, régression sur la réponse de l'assistant IA (mobile)

**Étape** : `/review task-350`. La validation est verte : build et tests des 4 repos, `## E2E log`
vert. Mais la revue de code relève **un point bloquant**. Aucune PR ouverte, task laissée en `wip`.

## Validation (verte)

| Repo | Build | Tests |
|---|---|---|
| api-mail | ✓ | 6 468 verts (0 échec, 16 ignorés) |
| client-blazor | ✓ (0 erreur, 0 avertissement) | 427 verts |
| client-mobile | ✓ | 1 021 verts |
| client-angular | ✓ (`npm ci && npm run build`) | 11 projets ✓ |

E2E : vert. Mobile 31/31, Angular 34/34, E2E-DETAIL-001 v2 vert sur les deux clients.

## ❌ Bloquant — mobile : « Répondre » depuis l'assistant IA ne s'ouvre plus

- `Client/Mobile/src/app/features/mail/components/ai-chat/ai-chat.component.ts:330`
  (`replyToCited`) ouvre la rédaction par `{ mode: 'reply', mail }`, **sans `content`**.
- La nouvelle garde de `mail-compose.openFor`, défense en profondeur de task-350, refuse toute
  réponse sans contenu. L'action « Répondre » de l'assistant affiche donc **toujours** « Le message
  d'origine n'a pas pu être chargé : réessayez. », et la rédaction ne s'ouvre plus.
- Avant task-350, cette action ouvrait une réponse avec une citation vide. C'est le défaut même de
  task-350, par un autre chemin, qui n'avait pas été recensé dans « Ce qui existe ».
- Pourquoi aucun test n'est rouge : `ai-chat.component.spec.ts:251` vérifie seulement l'émission
  `{ mode: 'reply', mail: target }`, pas l'ouverture de la rédaction. Les tests de compose, eux,
  prouvent le refus.

## Correction proposée (à faire par `/develop`, pas par `/review`)

1. `replyToCited` charge le contenu du message cité (`api.getEmailContent(folderPath, uid)`) avant
   d'émettre `{ mode: 'reply', mail, content }`. Sur échec, il affiche le même message
   (`ORIGINAL_NOT_LOADED_MESSAGE`) et n'ouvre rien.
2. Tests, rouges d'abord :
   - `ai-chat.component.spec` : l'émission porte le `content` du message cité ; un échec de
     chargement n'émet rien et affiche le message ;
   - le test existant de la ligne 251 est mis à jour en conséquence.
3. Côté Angular, rien à faire : l'assistant n'ouvre que des **nouveaux** messages (`openComposeWith`,
   sans `quoted`). Le brouillon d'« Annuler et remplacer » ne porte pas de citation. Leur repli
   « réponse » passe par `replyPrefill`, avec le contenu affiché.

## Suggestions (non bloquantes)

- Angular : le bandeau `mail-original-load-failed` n'offre pas de bouton « Réessayer ». Le
  praticien doit rouvrir le message. Acceptable selon l'objectif (« réessayez »), à envisager.
- Mobile : sur un message repris de la liste dont le contenu échoue, `error` affiche désormais le
  message clair à la place du texte technique. C'est voulu, et cela vaut pour toute panne du contenu.

## Reprise

Corriger le point bloquant (`/develop task-350`, ou à la main), puis relancer `/review task-350`.
L'`## E2E log` reste valable si seul `ai-chat` change. Un `/e2e` de contrôle reste prudent, car
la voie mobile est touchée.
