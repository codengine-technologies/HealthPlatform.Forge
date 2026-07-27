# todo-task-199.md — Flagsmith en évaluation locale : l'étage IA de la pipeline se désactive silencieusement dès que le service de flags faiblit

**Repos**: api-mail
**Dependencies**: —
**Epic**: E015
**Single frontend**: true

> **Origine** : tirs de charge des 2026-07-26/27 (banc task-173/174/195).
> Défaut **observé en exécution réelle** à deux échelles différentes, pas déduit
> d'une lecture de code — voir « Preuve ».

## Objective

Garantir que l'évaluation des feature flags ne dépend plus d'un appel réseau
par requête, et qu'une indisponibilité de Flagsmith soit **visible** au lieu de
désactiver silencieusement des fonctionnalités.

Aujourd'hui, chaque évaluation de flag interroge l'API Flagsmith en HTTP. Sous
charge, Flagsmith ne suit pas ; l'exception est attrapée et le flag retombe sur
`disabled` (« defaulting to disabled »). Concrètement : pendant un tir de
**15 utilisateurs seulement**, le flag `ai_pipeline` a échoué **750 fois sur
750 évaluations** — l'étage IA de la pipeline d'enrichissement n'a jamais
tourné, sans une seule erreur visible côté praticien ni côté API (HTTP 200
partout). En production, ce comportement ferait basculer une fonctionnalité
médicale sans alerte.

**US backend-only (justification)** : mécanique d'évaluation de flags côté
serveur, aucun contrat ni écran modifié.

### Preuve (relevés Seq / logs réplicas, tirs 2026-07-26/27)

Tir 15 utilisateurs × 100 mails (fenêtre 20:42→20:48 UTC), warning répété
**750 fois** — exactement 1 par UID enrichi :

```
[FeatureFlag] Failed to evaluate feature flag 'ai_pipeline', defaulting to disabled
Flagsmith.FlagsmithAPIError: Unable to get valid response from Flagsmith API
   at Flagsmith.FlagsmithClient.GetFeatureFlagsFromApi()
   at Flagsmith.FlagsmithClient.GetEnvironmentFlags()
   at mss.mail.api.Extensions.FlagsmithFeatureFlagService.IsEnabledAsync(...)
Operation=ProcessNewMail  FeatureName=ai_pipeline
```

Conséquence mesurable : les KPIs `enrich` de ce tir (p50 4,3 s à froid)
couvrent la pipeline CDA **sans** l'étage IA — la mesure de charge elle-même
est faussée par la défaillance du service de flags. Le conteneur
`flagsmith-app` était pourtant « Up (healthy) » au sens Docker pendant tout le
tir : c'est bien la capacité à répondre sous charge qui est en cause, pas la
disponibilité du processus.

### Contenu attendu

1. **Évaluation locale** : passer le client Flagsmith en mode *local
   evaluation* (téléchargement périodique du document d'environnement +
   évaluation en mémoire), ou à défaut mettre un cache avec TTL court devant
   `IsEnabledAsync`. Zéro appel réseau sur le chemin de requête.
2. **Politique d'échec explicite et par flag** : quand le document
   d'environnement n'est pas rafraîchissable, chaque flag doit avoir un
   comportement de repli **déclaré** (dernier état connu vs valeur par défaut),
   et non un `disabled` implicite uniforme. Pour `ai_pipeline`, le repli
   attendu est **le dernier état connu**.
3. **Échec visible** : l'impossibilité de rafraîchir les flags doit produire un
   signal d'exploitation (métrique/compteur + log **une fois par fenêtre**,
   pas 750 lignes), distinct du bruit applicatif.
4. **Pas de tempête de logs** : le pattern actuel (1 warning + stack complète
   par évaluation échouée) doit disparaître avec le cache — à vérifier.

### Hors scope

- Le dimensionnement du service Flagsmith lui-même (réplicas, Postgres dédié)
  → `DevOps/DIMENSIONNEMENT-1000-PRATICIENS.md` §2.6, géré par l'humain.
- Le choix des flags et leur gouvernance produit.
- La pipeline IA elle-même (contenu de l'étage, fournisseur).

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test unitaire : Flagsmith indisponible → `IsEnabledAsync` répond depuis
      l'état local sans appel réseau, avec la politique de repli déclarée du
      flag (ce test doit échouer sur le code actuel — le vérifier)
- [ ] Test unitaire : N évaluations concurrentes du même flag ne déclenchent
      au plus qu'un rafraîchissement réseau (pas d'appel par requête)
- [ ] Test unitaire : l'échec de rafraîchissement incrémente un compteur dédié
      et ne loggue qu'une fois par fenêtre de temps
- [ ] Test unitaire de non-régression : flag activé côté Flagsmith → activé en
      local après rafraîchissement
- [ ] Vérification sur le banc (15 utilisateurs suffisent — c'est l'échelle de
      la preuve) : **zéro** `FlagsmithAPIError` pendant un tir `enrich`, et
      l'étage IA de la pipeline s'exécute (traces `ai_pipeline` présentes)
- [ ] Aucune donnée de santé transmise à Flagsmith (identités/attributs
      d'évaluation audités)

## Manual Test Plan

1. Monter le banc : `dotnet run --project src/AppHost --launch-profile
   https-load-test` (cf. skill `loadtest-skill`, rituel pré-vol compris).
2. Seeder : `dotnet run --project tests/mss.mail.loadtest.seed -- --users 5
   --messages 10 --api http://127.0.0.1:5052`.
3. Déclencher l'enrichissement d'une boîte non lue :
   `POST /api/v1/mail/folders/INBOX/emails/enrich/sync` avec `[1,2,3,4,5]`.
4. Vérifier dans Seq (`http://127.0.0.1:5341`) : zéro `FlagsmithAPIError`,
   présence des traces de l'étage IA.
5. **Test de panne** : `docker stop flagsmith-app-*`, rejouer un enrichissement
   → l'API répond 200, le flag suit la politique de repli, **un seul** log de
   rafraîchissement échoué + compteur incrémenté. `docker start` → retour à
   l'état Flagsmith au rafraîchissement suivant.

## Branches

- `api-mail` (pushed) : `feat/task-199-flagsmith-local-evaluation` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-199-flagsmith-local-evaluation
- `dtos-mss` (pushed, auto-inclus) : `feat/task-199-flagsmith-local-evaluation` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-199-flagsmith-local-evaluation

## Develop log

- Repos touched : api-mail (dtos-mss : branche créée par /start, **aucun commit** — pas de changement de contrat, aucune PR à ouvrir)
- DTOs published : no DTO change
- Interop published : no interop change
- Commits (api-mail, `feat/task-199-flagsmith-local-evaluation`) :
  - 355e465 feat(featureflags): serve flags from a local snapshot with declared per-flag fallback
  - 2b8e8b1 test(featureflags): cover snapshot, single-flight, throttling and failure telemetry
  - 32573c3 test(loadtest): bind bench smoke tests to 127.0.0.1 instead of localhost
- Local build / test : ✓ build 0 erreur ; 8/8 nouveaux tests verts ; suite complète verte **sauf** :
  - `PatientRepositoryTests.GetWithMedicalDocumentsToday…` — flaky préexistant de
    fenêtre de minuit (données `DateTime.UtcNow` vs « aujourd'hui » local ; échoue
    entre 00h et 02h locales, il est ~01h). Sans rapport avec la task — candidat
    fix séparé.
  - `mss.mail.application.tests` — 1 échec transitoire, **1829/1829 verts au re-run**.
  - Les 2 `BenchSmokeTests` (LoadTest) échouaient en `SslHandshakeException` via
    `localhost`/::1 (relais IPv6 Docker gelé — cause racine documentée au banc) —
    **corrigés dans cette task** (127.0.0.1), 4/4 verts en 16 s.
- Note RED test-first : le test « dernier état connu » cible une surface qui
  n'existait pas (l'ancien code faisait `catch → return false`, défaut prouvé au
  banc par 750/750 évaluations en échec) — RED constaté à la compilation puis au
  comportement lors de la mise au point (bug single-flight corrigé, itération 2/5).
- DOD self-check : 8/10 vérifiés par commande ; « zéro FlagsmithAPIError pendant
  un tir enrich » **différé au banc/HAG** (test de panne décrit dans le Manual
  Test Plan) ; « aucune donnée de santé vers Flagsmith » vérifié — seule
  `GetEnvironmentFlags()` est utilisée, aucune API d'identité.
- Next step : /forge-simplify task-199

## Simplify log

- Repos éligibles touchés : api-mail (dtos-mss : aucun commit — hors scope simplify de toute façon)
- Simplifications appliquées (quality only, zéro changement de comportement) :
  1. `FlagsmithFeatureFlagService` — extraction de `Resolve(snapshot, flag)` :
     la logique « état connu sinon repli déclaré » était dupliquée dans
     `IsEnabledAsync` et `GetAllFeaturesAsync`.
  2. `FlagsmithExtensions` — extraction de `ReadIntSetting(env, config, défaut)` :
     motif `int.TryParse(env ?? config)` répété (intervalle + fenêtre de log).
- Re-validation : build 0 erreur, 10/10 tests Flagsmith verts.
- Commit : `refactor(featureflags): extract flag resolution and int-setting helpers` (pushé)
- Next step : /sonar task-199 (api-mail touché)

## Sonar log

| KPI | Baseline (scan 1) | Final (scan 2) | Cible new-code |
|---|---|---|---|
| Quality Gate | OK | **OK** | OK ✅ |
| Bugs / New bugs | 0 / 0 | **0 / 0** | 0 ✅ |
| Vulnérabilités / New | 0 / 0 | **0 / 0** | 0 ✅ |
| New code smells | 10 | **6** | 0 ⚠️ (voir note) |
| Code smells (projet) | 35 | 31 | — |
| Coverage / New coverage | 74,6 % / 80,9 % | **86,0 % / 87,5 %** | ≥95 ⚠️ (voir note) |
| Maintainability | A | **A** | A ✅ |

- **Périmètre task-199 : 0 smell restant.** Les 4 issues imputables à la task
  (3× S3604 — FP connu des constructeurs primaires, réglé par dé-sucrage en
  constructeur explicite ; 1× CA1822 test) sont corrigées
  (commit `refactor(featureflags): explicit constructor and static test stub`).
- **Les 6 new-code smells restants proviennent d'autres tasks déjà mergées**
  (période new-code = 6 semaines depuis la dernière analyse) :
  `BackgroundSyncService` S107, `OcspValidationService` S3604+S1168,
  `MailClientSession` S3604×2, `VCardSerializer` S1643. Hors périmètre de
  cette PR (règle 6, scopes isolés) — candidats à un run standalone
  `/sonar api-mail` (Mode B).
- New coverage 87,5 % < 95 : même cause — la période couvre 6 semaines de
  code d'autres tasks. Le code de la task-199 est couvert par 10 tests dédiés.
- Outillage : SonarQube était arrêté depuis 6 semaines (redémarré) et
  `SONAR_HOST_URL=localhost` échouait sur le relais IPv6 Docker gelé —
  corrigé en `127.0.0.1` dans `.env` (même cause racine que le banc).
- Itérations : 2/5. Next : /review task-199 (lint-angular, lint-mobile,
  verify-visual : skip — repos non touchés).

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/124 — label `awaiting-human-merge`
- `dtos-mss` : aucun changement de contrat — branche sans commit, pas de PR

## Code Review Summary

**APPROVED** — 8 fichiers relus, 1 suggestion non bloquante (tout nouveau flag
Flagsmith doit être ajouté à `FeatureFlags.All`), 0 issue bloquante.
Validation : build 0 erreur ; 3 130 tests — 1 seul échec = flake préexistant
`PatientRepositoryTests` (fenêtre de minuit, re-run vert à 02:01, fichiers non
touchés par la task). Sonar : Quality Gate OK, 0 smell restant sur le périmètre.

## Merged

- `api-mail` : squash `f2a93aa` — feat(featureflags): local snapshot evaluation with declared fallback (task-199) (#124) — CI develop : ✅ success (run 30252360356)
- `dtos-mss` : branche vide supprimée (remote), clone resynchronisé sur develop
- Merge attesté par l'humain (`--i-tested`) le 2026-07-27
