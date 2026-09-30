# questions/task-343.md — plus de blocage ; suites à ouvrir

Les blocages de `/review` du 2026-09-30 sont levés. Détail dans `tasks/done-task-343.md`, sections Develop log et Code Review Summary.

## Suites à ouvrir (PO) — hors périmètre de task-343

1. **Tests dépendants de l'horloge du poste**
   - Tests : `EmailReadingUseCaseTests.FilterTodayEmailsShouldReturnOnlyTodayAsyncAsync`, `ImapFolderServiceIntegrationTests.GetFolderTodayAsync_…` et `GetFolderNotSeenTodayAsync_…`.
   - Ils sont rouges entre 00:00 et 02:00 à Paris : la date locale et la date UTC diffèrent.
   - Prouvé sur `origin/develop` (`f8e3bef0`).
2. **Redis figé** (connecté mais muet) : chaque publication du backplane attend `asyncTimeout` (5 s par défaut). L'opération aboutit, mais elle est ralentie.
3. **Résumé courant de l'assistant** : un résumé tardif peut écraser un plus récent. Le défaut est antérieur à la task, et il devient possible entre réplicas.
4. **Taille des charges diffusées par le backplane** (listes de `MailDto` enrichis) face à `client-output-buffer-limit pubsub` : ajouter une métrique de taille et une note d'exploitation. L'alternative « UIDs seuls, relus en base » reste ouverte.
5. **AIPD** : la conformité de la task demande sa mise à jour. Les conversations (extraits de mails) passent de la mémoire du processus à Redis (HDS), avec une expiration de 8 h.
6. **Revue de l'extension e2e** (4e passage, suggestions non bloquantes) :
   - « Signalement absent à l'arrivée de la ligne » : vérifié seulement après le retour de `synchronize()`. Si la synchronisation dépasse 5 s, le tag peut déjà être là (rouge à tort). Remède : surveiller la ligne avant d'attendre la synchronisation, ou porter le délai du faux fournisseur à 15 s.
   - Nettoyage : si `waitForNewUid` échoue, le message remis n'est pas supprimé, et le nouvel essai en remet un second. L'effet reste dans le run, puisque le backend repart d'un reset.
   - weda2 : une erreur de `setReadingPane` dans le `finally` masque l'erreur d'origine.
   - Délai de classification de 5 s appliqué à tous les mails classés, seed compris : le limiter au seul message du parcours.
   - Notifications activées par le seed pendant COMPOSE-001 : surveiller les instabilités sur mobile.
   - Faux fournisseur : lire `content` par `?.ToString()` ; `DistinctQuestions` compte mal une question posée deux fois.
