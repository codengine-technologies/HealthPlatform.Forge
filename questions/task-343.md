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
