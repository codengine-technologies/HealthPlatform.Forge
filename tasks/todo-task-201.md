# todo-task-201.md — Snapshot de feature flags partagé via Redis : un pod qui démarre pendant une panne Flagsmith hérite de l'état du cluster, et le rafraîchissement passe à 5 minutes

**Repos**: api-mail
**Dependencies**: task-199 (mergée — squash `f2a93aa`)
**Epic**: E015
**Single frontend**: true

> **Origine** : suite directe de task-199 (évaluation locale des flags). Le
> snapshot introduit par task-199 est **par processus** ; en déploiement
> multi-pods il reste un trou de couverture au démarrage à froid, et
> l'intervalle de rafraîchissement (30 s) est plus agressif que nécessaire une
> fois l'appel réseau sorti du chemin de requête.

## Objective

Partager le snapshot de flags entre les instances via Redis (déjà dans la
stack), pour qu'un pod démarrant alors que Flagsmith est injoignable serve le
**dernier état connu du cluster** au lieu du repli à froid, et porter
l'intervalle de rafraîchissement à **5 minutes**.

**Ce que task-199 a déjà réglé, et qu'il ne faut pas re-livrer** : chaque pod
sert déjà ses évaluations depuis un snapshot mémoire, avec au plus un appel
réseau par intervalle (single-flight). Le gain « zéro appel réseau par requête »
est donc **déjà acquis sur tous les pods** — Redis n'y ajoute rien.

**Ce que Redis ajoute réellement** :

1. **Démarrage à froid pendant une panne Flagsmith** — aujourd'hui un pod neuf
   n'a aucun état connu : il applique `FeatureFlags.ColdStartDefault`, soit
   `ai_pipeline = false`. C'est exactement la désactivation silencieuse de
   l'étage IA que task-199 visait à supprimer, réintroduite à chaque rollout /
   scale-up / redémarrage de pod qui tombe pendant une indisponibilité. Avec un
   snapshot partagé, le pod neuf hérite de l'état du cluster.
2. **Cohérence inter-pods** — sans état partagé, deux pods peuvent divergent
   jusqu'à un intervalle entier sur la valeur d'un flag (le flip est vu par l'un
   et pas par l'autre). À 30 s c'était tolérable ; à 5 minutes la fenêtre de
   divergence est décuplée, donc cette task et le passage à 5 min vont ensemble.
3. **Charge sur Flagsmith** — N pods × 1 appel / intervalle devient, dans le cas
   nominal, l'état d'un seul rafraîchissement réutilisé. Effet secondaire
   bienvenu (Flagsmith ne suivait pas sous charge, cf. task-199), pas la
   justification principale.

**Coût assumé du passage à 5 minutes** — la propagation d'un flip de flag monte
à ~5 minutes dans le pire cas. Pour un kill-switch sur un étage IA médical,
c'est le vrai arbitrage de cette task : on échange de la réactivité contre de la
robustesse. Décision du humain, actée ici ; l'invalidation immédiate (pub/sub
Redis + webhook Flagsmith) est **hors scope** et fera une task séparée si le
délai s'avère gênant en exploitation.

**US backend-only (justification)** : mécanique d'évaluation de flags côté
serveur, aucun contrat ni écran modifié.

### Contenu attendu

1. **Trois étages de résolution, explicites et ordonnés** :
   - **L1 — mémoire du pod** : sert toutes les évaluations, zéro I/O sur le
     chemin de requête (comportement task-199, inchangé) ;
   - **L2 — snapshot Redis partagé** : lu **uniquement** lors d'un
     rafraîchissement (démarrage à froid, ou échec de l'appel Flagsmith),
     **jamais** par évaluation ;
   - **L3 — `FeatureFlags.ColdStartDefault`** : seulement si ni L1 ni L2 n'ont
     d'état, c'est-à-dire pod neuf **et** Redis vide/injoignable.
2. **Écriture du snapshot** : le pod qui réussit un rafraîchissement Flagsmith
   publie le snapshot dans Redis. Pas d'élection de « pod pollueur unique » —
   chaque pod continue de poller (12 appels/h/pod, négligeable), Redis sert de
   **partage d'état**, pas de verrou : aucun point de défaillance nouveau.
   `IDistributedLockService` (déjà présent) n'est pas utilisé ici.
3. **Horodatage dans le payload** : le snapshot sérialisé porte son `TakenAt`.
   Un pod n'adopte un snapshot Redis que s'il est **plus récent** que son état
   mémoire — un snapshot partagé périmé ne doit jamais écraser un état local
   plus frais.
4. **TTL Redis largement supérieur à l'intervalle** (ordre de grandeur : 24 h,
   à justifier dans le code) : l'objectif est précisément de survivre à une
   panne Flagsmith longue. Un TTL calé sur l'intervalle annulerait le bénéfice.
5. **Redis non bloquant, jamais fatal** : Redis injoignable ⇒ comportement
   exactement identique à task-199 (L1 + L3), aucune exception propagée, aucune
   tempête de logs (même politique « un log par fenêtre » que les échecs
   Flagsmith). La résolution de `IConnectionMultiplexer` doit être **optionnelle**
   (`GetService`, pas `GetRequiredService`) — `FlagsmithExtensionsTests` construit
   une `ServiceCollection` sans Redis et doit continuer à passer.
6. **Intervalle à 5 minutes** : `Flagsmith:RefreshIntervalSeconds` 30 → 300 dans
   `src/Api/appsettings.json` (surchargeable par
   `FLAGSMITH_REFRESH_INTERVAL_SECONDS`). Attention : cette même valeur alimente
   aussi `FlagsmithConfiguration.EnvironmentRefreshInterval` (évaluation locale
   du SDK) — vérifier que les deux usages restent cohérents à 300 s.
7. **Note à consigner sur la fenêtre de log** : avec un intervalle de 300 s, il
   y a au plus une tentative échouée toutes les 5 minutes, donc
   `FailureLogWindowSeconds = 60` ne filtre plus rien. Ce n'est **pas** une
   régression (1 warning / 5 min ≠ les 750 stacks de task-199) — le documenter
   pour que personne ne « corrige » ce réglage par erreur.
8. **Aucune donnée de santé dans Redis** : les clés ne contiennent que des noms
   de flags et des booléens, aucun identifiant praticien/patient. À auditer.

### Hors scope

- Invalidation immédiate d'un flip (pub/sub Redis, webhook Flagsmith) — task
  séparée si le délai de 5 min gêne en exploitation.
- Élection d'un poller unique / verrou distribué.
- Le dimensionnement de Flagsmith lui-même → `DevOps/DIMENSIONNEMENT-1000-PRATICIENS.md`
  §2.6, géré par le humain.
- Le dimensionnement Redis (réplication, persistance) — géré par le humain.

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés — cf. flake
      `PatientRepositoryTests` fenêtre de minuit)
- [ ] Test unitaire : pod à froid + Flagsmith injoignable + snapshot présent en
      Redis → `IsEnabledAsync` sert l'état Redis, **pas** `ColdStartDefault`
      (ce test doit échouer sur le code actuel — le vérifier)
- [ ] Test unitaire : un rafraîchissement Flagsmith réussi publie le snapshot
      dans Redis (clé + TTL attendus)
- [ ] Test unitaire : snapshot Redis **plus ancien** que l'état mémoire → ignoré
      (pas de régression de fraîcheur)
- [ ] Test unitaire : Redis injoignable (connexion qui lève) → comportement
      task-199 préservé, aucune exception remontée à l'appelant
- [ ] Test unitaire : N évaluations concurrentes ne produisent **aucun** accès
      Redis sur le chemin de requête (Redis touché seulement au rafraîchissement)
- [ ] Test unitaire de non-régression : les 10 tests Flagsmith de task-199
      restent verts sans modification de leurs assertions comportementales
- [ ] `Flagsmith:RefreshIntervalSeconds = 300` dans `appsettings.json`, et
      cohérence vérifiée avec `EnvironmentRefreshInterval`
- [ ] Audit : aucune donnée de santé dans les clés/valeurs Redis de flags
- [ ] Vérification sur le banc (15 utilisateurs, échelle de la preuve task-199) :
      zéro `FlagsmithAPIError`, traces `ai_pipeline` présentes

## Manual Test Plan

1. Monter le banc : `dotnet run --project src/AppHost --launch-profile
   https-load-test` (cf. skill `loadtest-skill`, rituel pré-vol compris —
   purge `~/.dcp/state.elevated` si l'AppHost se fige).
2. Seeder : `dotnet run --project tests/mss.mail.loadtest.seed -- --users 5
   --messages 10 --api http://127.0.0.1:5052`.
3. Déclencher un enrichissement :
   `POST /api/v1/mail/folders/INBOX/emails/enrich/sync` avec `[1,2,3,4,5]`.
   Vérifier dans Seq (`http://127.0.0.1:5341`) : zéro `FlagsmithAPIError`,
   traces de l'étage IA présentes.
4. **Snapshot partagé présent** : inspecter la clé de flags dans Redis
   (`docker exec <redis> redis-cli KEYS 'mss:featureflag*'` puis `GET`) — le
   snapshot et son `TakenAt` doivent y être après le premier rafraîchissement.
5. **Le scénario que cette task corrige** : `docker stop flagsmith-app-*`, puis
   **redémarrer l'API** (pod neuf pendant la panne). Rejouer un enrichissement
   → l'étage IA doit **toujours** tourner (état hérité de Redis), un seul log
   d'échec de rafraîchissement, compteur `mssante_featureflag_refresh_total`
   incrémenté. Sur `develop` avant cette task, le même scénario désactive
   `ai_pipeline` silencieusement.
6. **Redis absent** : `docker stop <redis>`, rejouer → l'API répond 200, les
   flags suivent l'état mémoire, aucune 500, pas de tempête de logs.
7. **Propagation à 5 min** : flipper `ai_pipeline` dans l'UI Flagsmith,
   constater la prise en compte au rafraîchissement suivant (≤ 5 min) — c'est
   le coût assumé, à valider comme acceptable au HAG.
