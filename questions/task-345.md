# questions/task-345.md — /review : CHANGES REQUESTED (revue indépendante du 2026-09-29)

**Étape** : `/review` (étape 5, revue de code). Build et tests verts (api-mail 5 849/5 849, mobile
947/947), DOD vérifiable par commande tenue. Aucune PR ouverte, aucun commit : la chaîne est arrêtée.

## BLOQUANT

**1. `Client/Mobile/e2e/headless/run.mjs` — le démontage supprime des conteneurs qui ne sont pas les
siens.** `SESSION_CONTAINERS` contient `mss-mail-redis-`, `mss-mail-rabbitmq-`, `rediscommander-`,
préfixes communs à tous les profils de l'AppHost ; `teardown()` (dans `finally`, sur tout chemin de
sortie) fait `docker rm -f` sur tout ce qui correspond, arrêté ou non.
- Pré-vol refusé « port 5052 occupé » (un AppHost dev ou banc tourne) → le `finally` supprime le Redis /
  RabbitMQ de CET AppHost vivant.
- Chaque run supprime le Redis **Persistent** du banc de charge (cache `setupdb:`, ~40 min de migrations
  épargnées par campagne).
- **Correctif** : ne retirer que les conteneurs créés par ce run (instantané des noms avant le démarrage
  de l'AppHost, retrait des seuls nouveaux) ; rien du tout si l'AppHost n'a jamais été démarré.

## FORTEMENT RECOMMANDÉ — des verts qui ne vérifient pas leur scénario

Le mode headless tient sa promesse sur les données seedées (`requireData`), mais plusieurs parcours
restent des « verts qui mentent » hérités de la suite humaine :
- `E2E-MAIL-001` agit sur un message DÉJÀ lu et ne contrôle aucun état (il finit non lu) ;
- `E2E-MAIL-003` ne contrôle pas `mail-row--flagged` ;
- « puis disparaît » jamais vérifié : `E2E-DRAFT-001`, `E2E-CONTACT-002`, `E2E-SIGNATURE-001`,
  `E2E-CONTACT-003`, `E2E-FOLDER-002` (suppression sous `if`, sautée en silence) ;
- `E2E-SEARCH-001` ne contrôle ni les résultats ni l'ouverture du panneau si le bouton disparaît ;
- `E2E-FOLDER-001` ne prouve pas que le dossier s'est ouvert ; `E2E-MAIL-004` ne vérifie pas le retour
  en INBOX ; `E2E-BIO-001` ne vérifie pas que l'acquittement est enregistré ;
- `E2E-COMPOSE-001` : au second essai, l'objet fixe peut retrouver le message du premier.

## SUGGESTIONS (non bloquantes)

- `ParityCheck` : un client absent d'un scénario est dispensé en silence (devrait être un écart).
- `run.mjs` : seul SIGINT déclenche le démontage (ni SIGTERM/SIGHUP/SIGBREAK) ; contrôler en fin de
  run que 5052/8100/3993 sont libres.
- Outil .NET : `TaskCanceledException` (timeout HttpClient) non rattrapée dans le seed et `Program.cs` ;
  réponse du POST contact non disposée ; `MSS_E2E_PASSWORD` ne peut que casser (passdb Dovecot fixe).
- `headless.ts` : restreindre la route du bypass à l'origine de l'app.

## Décision attendue

Reprendre `/develop task-345` pour corriger le bloquant **et** durcir les parcours ci-dessus (chacun
vérifié par mutation), puis rejouer `/sonar` → `/review`. Recommandé : traiter bloquant + « verts qui
mentent » + les suggestions à coût quasi nul ; laisser le reste en suite.
