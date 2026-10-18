# questions/task-365.md — `/review` : CHANGES REQUESTED

**Validation** : build et tests verts (api-mail 6 675, weda2 2 732), porte e2e verte (mobile 37, angular 45),
Sonar Quality Gate OK. **Code review : CHANGES REQUESTED** — aucune PR ouverte, task laissée en `wip-*`.

Les points bloquants viennent tous de la même cause : avec la piste D, **une seule session de messagerie
est partagée** par Weda, l'iframe, l'onglet weda2 et chaque rechargement. Plusieurs mécanismes écrits
pour une session par chargement ne tiennent plus.

## Bloquants

### R1 — api-mail : une session rouverte après une déconnexion n'écrit plus « ouverte »
`SessionMailboxGuard.cs` (liaison par boîte) et `SyncController.LogoutCleanupAsync`.
- Le marqueur `session:proxy-mailbox:{px}:{boîte}` vit 12 h, et `/sync/logout` ne le retire pas.
- Scénario : A ouvert (`Opened A`) → bascule vers B (`Closed A`, `Opened B`) → retour sur A. La
  liaison existe encore, donc `Allowed`, et l'activité de A reprend **sans** `Opened`. Le journal
  d'imputabilité perd une frontière (règle de task-303).
- **Correctif proposé** : `/sync/logout` supprime le marqueur (clé, boîte), sans condition. Ce n'est
  pas `ReleaseAsync`, qui ne supprime que la valeur posée par le même réplica. Test d'intégration :
  bascule → déconnexion → retour → deux `Opened`.

### R2 — weda2 : la fermeture au `pagehide` (piste B) contredit la session partagée
`page-exit-mail-session.service.ts`.
- En autonome, fermer l'onglet ferme la session **de l'iframe Weda** ouverte à côté. Le nettoyage
  côté serveur peut aussi arrêter la synchronisation de fond de la boîte.
- Un F5 en autonome rejoue la course qui a fait exclure le mode embarqué : la requête keepalive de
  l'ancienne page ferme la session que la nouvelle vient de reprendre.
- `rotateSessionId()` au `pageshow` est sans effet côté serveur quand le cookie est présent.
- **Proposition (arbitrage humain, B étant ta décision du 2026-10-11)** : **retirer B**. Avec D, la
  borne est assurée par C (plafond par boîte) et l'expiration (5 à 6 min). La surveillance du § 3
  ferme à la déconnexion de Weda.

### R3 — weda2 : au changement de praticien, l'ordre de fermeture vise la mauvaise session
`shared-session-watch.service.ts`, sortie « utilisateur différent ».
- Quand le changement est détecté, le navigateur porte déjà le cookie du Dr B. L'ordre ferme
  `{boîte de A}_{px(B)}`, pas la session réelle de A. Il écrit en plus un `MailboxSessionClosed` qui
  associe la boîte de A à la session de B : c'est faux pour l'imputabilité.
- **Correctif proposé** : ne rien fermer sur ce chemin (purge, puis rechargement). La session de A
  expire seule (C et l'expiration bornent).

### R4 — weda2 et banc : après la déconnexion de Weda, l'ordre de fermeture part peut-être sans cookie
`shared-session-watch.service.ts` (sortie « session absente »), `e2e/mss-e2e/support/session.ts`.
- Si le vrai proxy **efface** `proxy_session_id` au `DELETE /auth/logout` (le JSDoc de `$logout` de
  weda2 le dit), l'ordre de fermeture repart sur la clé d'en-tête et ne ferme rien.
- Le faux proxy du banc garde le cookie : `E2E-SESSION-003` serait alors **vert alors que la
  fonctionnalité échoue**.
- **À vérifier** : le comportement du vrai proxy (hors forge).
- **Si le cookie est effacé**, deux options :
  - (a) api-mail renvoie la clé de pool dans un en-tête de réponse, et weda2 la renvoie à la
    fermeture ;
  - (b) accepter l'expiration (5 à 6 min, bornée par C) comme seule fermeture après une déconnexion
    de Weda.
- Dans tous les cas, le faux proxy doit faire comme le vrai.

## Suggestions (non bloquantes)
- Surveillance : espacer les vérifications « retour sur l'onglet ». En mode embarqué, chaque clic
  dans l'iframe déclenche `focus`. `/auth/userinfo` n'est ni silencieux ni borné dans le temps : s'il
  ne répond pas, `checking` reste vrai et la surveillance s'arrête.
- api-mail : la liaison par boîte ne passe pas par le disjoncteur du cache. Pendant une panne Redis,
  chaque requête attend le délai du multiplexeur.
- `RequestLoggingMiddleware` journalise l'en-tête `Client-Session-Id`, pas la clé du pool : les
  journaux et le pool racontent deux histoires (défaut de task-282).
- Plafond : deux créations concurrentes peuvent s'évincer mutuellement (rare, borné).
- e2e : exiger un résultat précis (`/logout` **ou** l'écran de connexion, pas l'un des deux) et un
  seul `session-expired` ; vérifier qu'aucune ligne ne reste dans l'iframe.
- Architecture : exposer `closeMailSession` et `redirectToLoginOnSessionLoss` par le barrel de
  `lib/auth` plutôt que par leurs chemins internes.

## Décision attendue
1. **R2** : retirer la piste B (recommandé) ou la garder en connaissant sa limite ?
2. **R4** : peux-tu confirmer si le proxy efface `proxy_session_id` au `DELETE /auth/logout` ? Selon la
   réponse : (a) renvoyer la clé de pool ou (b) s'en remettre à l'expiration.
3. R1 et R3 : correctifs proposés ci-dessus, à appliquer avec `/develop`.

## Réponse (2026-10-18)

- R2 : piste B retirée.
- R4 : psc-auth-proxy efface le cookie ; on s'en remet à l'expiration (pas d'ordre de fermeture à la sortie ni au changement de praticien).
- R1, R3 : correctifs proposés, appliqués par /develop.
