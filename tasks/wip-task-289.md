# todo-task-289.md — Un feature flag absent de l'environnement Flagsmith désactive silencieusement l'étage IA de toute l'application

**Repos**: api-mail
**Dependencies**: —
**Epic**: E015
**Single frontend**: true

> **Origine** : incident **observé en exécution réelle** sur le déploiement
> Staging (Kubernetes, namespace `healthplatform`) le **2026-09-02 à 17:44**,
> pas déduit d'une lecture de code — voir « Preuve ».
>
> Cette US est la suite directe de `task-199` (évaluation locale + repli
> déclaré par flag) et de `task-201` (snapshot partagé Redis). Toutes deux
> couvraient le cas **« Flagsmith injoignable »**. Le cas
> **« Flagsmith joignable mais incomplet »** n'était pas couvert — c'est
> précisément celui qui s'est produit.

## Objective

Garantir qu'un feature flag déclaré par l'application mais **absent de
l'environnement Flagsmith** dégrade **ce flag seul**, et jamais l'état des
autres flags. Et rendre cet écart **visible dès le démarrage**, au lieu de le
laisser se manifester des heures plus tard par la disparition inexpliquée
d'une fonctionnalité médicale.

Aujourd'hui, le rafraîchissement du snapshot évalue les onze flags de
`FeatureFlags.All` dans une seule boucle. Le client Flagsmith **lève** sur un
flag inconnu de l'environnement ; comme l'appel est dans la boucle, la
première absence avorte le rafraîchissement **entier**. Aucun snapshot n'est
jamais publié, donc les onze flags retombent sur leur repli de démarrage à
froid. Or ce repli n'est pas neutre : les widgets de tableau de bord sont en
fail-open (`true`), mais les flags `ai_*` sont en fail-closed (`false`).

**Conséquence médicale mesurée** : parce que huit flags de widgets créés par
`task-274` n'existaient pas dans l'environnement Staging, l'étage IA de la
pipeline d'enrichissement était éteint pour **tous** les praticiens, et
**chaque** demande de résumé d'un mail clinique répondait « résumé non
disponible ». Le praticien ne voit aucune erreur : il voit une fonctionnalité
absente.

**US backend-only (justification)** : mécanique interne d'évaluation de flags
côté serveur. Aucun contrat d'API, aucun DTO et aucun écran ne changent — le
comportement observable côté frontends est le **retour** du comportement
nominal, pas un comportement nouveau.

### Preuve (logs des réplicas api-mail, Staging, 2026-09-02)

Le warning de `task-199` (un log par fenêtre, pas une stack par évaluation)
nomme le flag fautif :

```
17:44:16 [WRN] [FeatureFlag] Flagsmith refresh failed (3 failure(s) since last report)
                — serving last known flag state
Flagsmith.FlagsmithClientError: Feature does not exist: dashboard_widget_mail_counters
   at Flagsmith.Flags.GetFlag(String featureName)
   at Flagsmith.Flags.IsFeatureEnabled(String featureName)
   at mss.mail.api.Extensions.FlagsmithFeatureFlagService.RefreshAsync()
```

Et, dans la même seconde, la conséquence sur le chemin métier — répétée pour
chaque UID demandé par le praticien (`4816`, `4821`, `4825`, `4826`, `4890`, …) :

```
17:44:16 [WRN] ⚠️ Handled 404 - GET /api/v1/mail/folders/INBOX/emails/summary/4821
mss.mail.application.Exceptions.NotFoundException: AI summary is not available.
   at mss.mail.api.Controllers.V1.MailController.GetEmailSummaryAsync(...)
```

Deux faits qui établissent la chaîne de causalité, et non une simple
corrélation :

1. **Le message « serving last known flag state » est trompeur** : aucun état
   n'a jamais été connu. `_snapshot` n'est jamais affecté puisque
   l'affectation suit la boucle qui lève. Ce sont donc les replis de démarrage
   à froid qui s'appliquent, pas un dernier état connu.
2. **Les flags `ai_*` sont en tête de `FeatureFlags.All`** : leurs valeurs
   avaient déjà été lues **avec succès** auprès de Flagsmith avant que la
   boucle ne lève sur le premier flag de widget. Elles sont jetées avec le
   reste. L'étage IA est donc éteint par un flag **sans aucun rapport avec
   lui**.

Fichiers concernés (localisation du défaut, à titre de repère — l'implémentation
reste le choix de `/develop`) :

- `Api/Mail/src/Api/Extensions/FlagsmithFeatureFlagService.cs` — `RefreshAsync()`,
  la boucle sur `FeatureFlags.All` ; même motif à re-vérifier sur le chemin
  d'identité praticien introduit par `task-274`.
- `Api/Mail/src/Application/Constants/FeatureFlags.cs` — `All` et
  `ColdStartDefault`.
- `Api/Mail/src/Application/Telemetry/FeatureFlagMetrics.cs` — compteur
  `mssante_featureflag_refresh_total{status}`.

### Contenu attendu

1. **Isolation par flag.** L'échec d'évaluation d'**un** flag ne doit plus
   empêcher la publication du snapshot. Le flag fautif prend son repli déclaré
   (`FeatureFlags.ColdStartDefault`), tous les autres prennent la valeur
   réellement servie par Flagsmith. Le snapshot est publié.
2. **Un statut de rafraîchissement distinct.** Le compteur
   `mssante_featureflag_refresh_total` gagne un statut **`partial`** :
   « Flagsmith a répondu, mais des flags déclarés manquent ». Il ne doit ni
   être compté en `success` (l'exploitation doit voir l'écart) ni en `failure`
   (le service répond, et le snapshot est valide pour les autres flags —
   les confondre rend l'alerte inexploitable).
3. **Contrôle de dérive contrat / environnement.** Au **démarrage** et à
   chaque rafraîchissement partiel, journaliser **la liste nommée** des flags
   déclarés par `FeatureFlags.All` et absents de l'environnement, sous la
   politique « un log par fenêtre » déjà en place — pas un log par flag et par
   cycle. C'est le signal qui manquait le 2026-09-02.
4. **Le message de repli doit dire la vérité.** « serving last known flag
   state » ne doit être écrit que lorsqu'un état a effectivement été connu.
   Sans aucun snapshot, le log doit dire que les **replis de démarrage à
   froid** s'appliquent, et lesquels des flags concernés sont en fail-closed.
5. **Symétrie du chemin d'identité.** Le rafraîchissement par identité
   praticien (`task-274`) itère la même liste : il doit recevoir le même
   traitement, sans quoi un praticien avec des overrides retombe sur le
   snapshot d'environnement pour une raison invisible.
6. **Régression verrouillée par les tests.** Le cas « Flagsmith répond mais un
   flag déclaré est absent » doit être couvert, en vérifiant nommément que la
   valeur des flags `ai_*` **survit** à l'absence d'un flag de widget. C'est
   l'assertion qui aurait attrapé cet incident.

### Hors périmètre (explicite)

- **La création des huit flags `dashboard_widget_*` dans les environnements
  réels** est un geste d'exploitation, pas du code (le seeder
  `src/AppHost/FlagsmithSeeder.cs` ne sert que le banc, et son commentaire le
  dit). Il est mené indépendamment de cette US, et **ne la remplace pas** :
  la prochaine US qui déclarera un flag sans l'avoir créé reproduirait
  l'incident à l'identique.
- **Le rattrapage des mails passés à côté de l'étage IA** pendant la panne
  (aucun résumé, aucun embedding, aucun tag — ils le resteront après
  réactivation du flag) fait l'objet de `todo-task-290.md`.

## Definition of Done

- [ ] Build passes on api-mail (0 errors)
- [ ] Tests pass (0 failures)
- [ ] Test : Flagsmith répond, **un** flag déclaré est absent → le snapshot est
      publié, et les flags présents portent la valeur servie par Flagsmith
- [ ] Test : ce même cas avec un flag de widget absent → `ai_pipeline` conserve
      la valeur servie par Flagsmith (**assertion nommée** — la régression de
      l'incident du 2026-09-02)
- [ ] Test : le flag absent, lui, prend bien la valeur de
      `FeatureFlags.ColdStartDefault`
- [ ] Test : `mssante_featureflag_refresh_total{status=partial}` est incrémenté
      dans ce cas, et **ni** `success` **ni** `failure`
- [ ] Test : Flagsmith injoignable → comportement de `task-199`/`task-201`
      **inchangé** (dernier état connu, puis snapshot Redis, puis repli
      déclaré) — non-régression explicite
- [ ] Test : le chemin d'identité praticien isole le flag absent de la même
      façon que le chemin d'environnement
- [ ] Test : le log de dérive nomme les flags absents, et respecte la politique
      « un log par fenêtre » (pas un log par flag ni par cycle)
- [ ] Test : sans aucun snapshot connu, le log ne prétend pas servir un
      « dernier état connu »
- [ ] Aucune donnée de santé en clair dans les logs (les logs de cette US ne
      portent que des noms de flags — à vérifier, y compris sur le chemin
      d'identité où l'identifiant est l'adresse MSSanté du praticien)
- [ ] `GET /api/v1/FeatureFlag` a au moins 1 test d'intégration couvrant le cas
      partiel (rule 1b)

## Manual Test Plan

- **Lancer le backend** : `cd Api/Mail && dotnet run --project src/AppHost`
  (le profil AppHost démarre Flagsmith et le seed via `FlagsmithSeeder`).
- **Reproduire l'incident** : dans l'UI Flagsmith (`http://localhost:8000`,
  projet `HealthPlatform.Mss`, environnement `Development`), **archiver ou
  supprimer** le flag `dashboard_widget_mail_counters` — un seul suffit. Poser
  `ai_pipeline` à **`true`** dans la même UI, pour que le contrôle soit
  discriminant.
- **Écran / URL à ouvrir** : `GET http://localhost:<port>/api/v1/FeatureFlag`
  (l'état complet des flags tel que l'API le voit).
- **Ce que l'humain doit voir** :
  - `ai_pipeline` ressort **`true`** (avant correctif : `false`) ;
  - `dashboard_widget_mail_counters` ressort à son repli déclaré (`true`) ;
  - dans les logs, **une** ligne nommant le flag absent, et **aucune**
    mention de « serving last known flag state » ;
  - le compteur `mssante_featureflag_refresh_total{status=partial}` avance sur
    l'endpoint de métriques Prometheus.
- **Vérifier la conséquence métier** — le seul contrôle qui prouve la valeur
  pour le praticien : ouvrir un mail clinique porteur d'un document, puis
  `GET /api/v1/mail/folders/INBOX/emails/summary/{uid}` → **200 avec un
  résumé**, alors qu'avant correctif la même requête répondait 404 « AI summary
  is not available ».
- **Remettre le flag** dans l'UI Flagsmith et vérifier le retour au nominal :
  le log `[FeatureFlag] Flagsmith refresh recovered … flag state is live again`
  doit apparaître.
- **Données de test** : aucune donnée de santé réelle. Les mails du banc
  (`loadtest-skill`) sont synthétiques.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors exigence DSR directe — mécanique interne de
  robustesse ; elle **protège** en revanche des fonctionnalités du couloir
  (résumé et indexation des documents cliniques reçus par MSSanté)
- **Exigences DSR honorées** : non applicable — aucune exigence DSR ne porte
  sur le pilotage interne des feature flags
- **INS** : non applicable — aucun identifiant patient n'est manipulé ; le
  service n'échange que des noms de flags booléens
- **Authentification PS** : inchangée — PSC / e-CPS, niveau eIDAS substantiel,
  déjà en place sur les endpoints concernés (`PscIdentity__Enforce: true` en
  Staging). Cette US ne touche pas la chaîne d'authentification
- **Habilitations** : inchangées — le chemin d'identité de `task-274` utilise
  l'adresse MSSanté du praticien comme identifiant Flagsmith, sans contrôle
  d'habilitation supplémentaire
- **Interop CI-SIS** : non applicable — aucun échange métier. Effet **indirect**
  à noter : l'étage IA éteint prive d'indexation les documents CDA reçus, dont
  le traitement lui-même (via `interop-cda` + Schematron) reste inchangé
- **Tracé PGSSI-S** : évènements à journaliser — (a) rafraîchissement partiel
  avec la liste nommée des flags absents, (b) application des replis de
  démarrage à froid, (c) retour au nominal. Ce sont des évènements
  d'**exploitation**, sans donnée de santé : conservation alignée sur la
  politique de logs technique de la plateforme, et non sur la durée de 6 ans
  des traces d'accès au dossier
- **Consentement patient** : non applicable — aucun traitement de donnée
  patient n'est créé ni modifié
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — Staging et Production de la plateforme. Sans
  objet pour cette US, qui n'ajoute aucun stockage de DSCP
- **AIPD / impact RGPD** : inchangé — aucun traitement nouveau, aucune donnée
  personnelle supplémentaire collectée. À noter tout de même : l'identifiant
  Flagsmith du chemin d'identité **est** une donnée personnelle du praticien
  (adresse MSSanté nominative) ; le DOD exige qu'elle ne fuite pas dans les
  logs de dérive

## Branches

- `api-mail` (pushed) : `fix/task-289-flag-absent-isole-du-snapshot` —
  https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-289-flag-absent-isole-du-snapshot
- `dtos-mss` (pushed, auto-inclus) : `fix/task-289-flag-absent-isole-du-snapshot` —
  https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/fix/task-289-flag-absent-isole-du-snapshot
  (branche créée proactivement par convention ; aucun changement de contrat
  n'est attendu pour cette US — sans commit, aucune PR ne sera ouverte)

Pré-flight du 2026-09-04 : les 7 repos automatisés sont sur `develop`.

## Timings

*(généré par `tools/timing/report.sh --task task-289 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 40 s | — | — | — | — |
| /develop | ok | 9 min 02 s | 5 (29 s) | 22 (11 min 26 s) | — | api-mail 5B/22T |
| /sonar | ok | 28 min 57 s | 4 (49 s) | 21 (9 min 47 s) | — | 3 itération(s), api-mail 4B/21T |
| /lint-angular | skipped | 0.5 s | — | — | — | client-angular non listé dans **Repos** (US backend-only, Single frontend: true) — aucun code Angular écrit |
| /lint-mobile | skipped | 0.5 s | — | — | — | client-mobile non listé dans **Repos** (US backend-only) — repo resté sur develop, aucun code mobile écrit |
| /verify-visual | skipped | 0.5 s | — | — | — | aucun écran client-mobile touché (US backend-only, pas de ## Stitch design log) |
| /review | failed | 10 min 28 s | 1 (5.5 s) | 1 (1 min 22 s) | — | api-mail 1B/1T, code review CHANGES REQUESTED — 3 bloquants (2 tests vacuos établis par mutation, 1 libellé de log trompeur) ; questions/task-289.md écrit |
| **Total cycle** | | **49 min 10 s** | **10 (1 min 25 s)** | **44 (22 min 36 s)** | **0 (0.0 s)** | |

## Develop log

### Implémentation (api-mail)

Test-first : 11 tests unitaires écrits d'abord, **RED vérifié à 10/11** — le 11e
(`TransportFailureMidEvaluation_IsNotTreatedAsAMissingFlag`) était vert avant
tout code, et c'est normal : il verrouille l'invariant de task-199, qui n'était
pas encore cassé. Puis GREEN 11/11.

Fichiers touchés : `FlagsmithFeatureFlagService.cs` (isolation par flag, statut
`partial`, log de dérive, log de panne véridique), `FeatureFlags.cs`
(`FailClosedAtColdStart`, `HasDeclaredColdStartDefault`),
`FeatureFlagMetrics.cs` (statut `partial`), `FeatureFlagWarmUpService.cs`
(nouveau), `FlagsmithExtensions.cs` (enregistrement).

### Deux trouvailles qui ont changé l'implémentation

1. **`FlagsmithAPIError` hérite de `FlagsmithClientError`** (vérifié par
   réflexion sur le paquet Flagsmith 9.0.0). Un `catch (FlagsmithClientError)`
   attrape donc aussi les pannes réseau : le premier jet publiait un snapshot de
   replis à chaque hoquet de transport, ce qui **détruisait l'invariant « dernier
   état connu » de task-199**. Le filtre est
   `when (error is not FlagsmithAPIError)`. C'est le test de non-régression qui
   l'a attrapé, pas la relecture.
2. **`await Task.Yield()` en tête de `ExecuteAsync`.** Sans lui,
   `BackgroundService` n'attend `ExecuteAsync` que jusqu'au premier `await`
   réellement incomplet : en évaluation locale Flagsmith tout se complète de
   façon synchrone, et l'appel réseau serait payé par le thread de démarrage du
   pod, sous le verrou du service — exactement ce que l'amorce prétend éviter.
   Même motif que `BackgroundTaskQueue`.

### Passe qualité `/simplify` — appliquée

Quatre revues en parallèle (reuse / simplification / efficacité / altitude).
Cleanups appliqués :

- **Discipline de verrou** : `LogRefreshFailure` prend `_gate` lui-même, comme
  `ReportRefreshOutcome` et `LogSharedStoreFailure`. Deux blocs `lock` chez les
  appelants supprimés, et un invariant qui ne tenait que par un commentaire.
- **Vocabulaire de scope unifié** : constantes `EnvironmentScope` /
  `IdentityScope` partagées par le log de dérive et le log de panne, au lieu de
  quatre littéraux pour deux chemins. Le log de panne d'environnement est
  désormais scopé, ce qu'il n'était pas.
- **`FailClosedAtColdStartLabel`** pré-calculé (immuable pour la vie du process).
- **Test de convention** `FeatureFlagsConventionTests` : tout flag de
  `FeatureFlags.All` doit avoir un repli **explicitement déclaré**.
  `ColdStartDefault` rendait `false` aussi bien pour « déclaré désactivé » que
  pour « jamais déclaré » — un flag ajouté sans sa politique aurait été annoncé
  « stay DISABLED » sans que personne n'ait pris la décision. C'est l'oubli de
  task-274 rejoué un cran plus loin, et c'est le seul finding d'altitude qui
  généralise au lieu d'empiler.
- **Helpers de test promus** : `MutableTimeProvider` →
  `mss.mail.testing.shared` (elle existait en 3 copies nested dans le seul
  répertoire `Extensions/`) ; `RefreshStatusCounter` et `CapturingLogger<T>` →
  `tests/mss.mail.api.tests/TestInfrastructure/`. Le bloc `MeterListener` inline
  de `FlagsmithFeatureFlagServiceTests` et son inspection réflexive
  `GetArguments()[2]` disparaissent au profit de ces helpers.
- **Duplications de test** : `StubEnvironment(defaultValue, …)` remplace trois
  montages manuels de substitut ; la liste des huit flags de widgets est
  déclarée une fois par fichier au lieu d'être énumérée verbatim.
- **`IReadOnlyList<string>`** pour le paramètre `missing` (le helper ne mute
  rien).

### Un flake que la passe qualité a introduit, puis corrigé

Le `Task.Yield()` de l'amorce a rendu les deux tests du warm-up non
déterministes, de deux façons distinctes :

- sous le **contexte de synchronisation de xUnit**, la continuation du yield ne
  s'exécute pas avant la fin du test — mesuré : le service n'avait alors *rien*
  fait, et le test « l'amorce appelle Flagsmith » passait pourtant, parce que
  c'était l'évaluation suivante du test qui déclenchait l'appel. **Un test vert
  qui ne gardait rien** ;
- `StopAsync` **annule le jeton d'arrêt avant** d'attendre `ExecuteAsync` : si
  l'annulation gagnait la course, l'amorce sortait par son
  `catch (OperationCanceledException)` sans jamais interroger Flagsmith.

Correctif : `Task.Run` (pas de contexte de synchronisation) + attente de
`BackgroundService.ExecuteTask` au lieu de `StopAsync`. 3 × 720/720 verts.

### Findings écartés (et pourquoi)

- **Tag `scope` sur `mssante_featureflag_refresh_total`** — utile pour
  distinguer une dérive d'environnement d'une dérive d'identité, mais c'est un
  changement du **contrat de télémétrie**, hors du périmètre « quality only »
  d'une passe qualité. À instruire si l'exploitation en a besoin.
- **Throttle de dérive clé par scope** — aujourd'hui `_driftReports` est unique
  pour les deux chemins, donc une dérive d'environnement peut étouffer le
  premier log d'une dérive d'identité dans la même fenêtre. C'est un changement
  de **comportement**, pas un cleanup. Signalé ici pour arbitrage `/review`.
- **`WarmUpAsync` sur `IFeatureFlagService`** — l'amorce chauffe par effet de
  bord d'une lecture ; un membre dédié dirait l'intention. Changement de
  contrat d'interface : écarté. Le risque signalé (une optimisation du chemin à
  froid qui viderait l'amorce en silence) est couvert autrement, par le test
  `WarmUp_ActuallyRefreshesTheSnapshotFromFlagsmith` qui assert l'appel réseau
  **réel**.
- **Renommage `FailureThrottle` → `WindowedReportThrottle`** — juste sur le
  fond (le type sert désormais à journaliser un non-échec), mais du churn sur un
  type pré-existant au milieu d'un diff de correctif.
- **Health check `feature-flags` en `Degraded`** — la dérive contrat/environnement
  est sur le fond une condition de *readiness de configuration*, et le repo a
  l'infrastructure (`AddDefaultHealthChecks`, tag `ready`). Bien plus
  exploitable qu'une ligne de log au boot : interrogeable en continu, survit à
  la rotation des logs. **Hors périmètre** (dépasse le diff, et implique une
  décision produit : ne surtout pas sortir un pod du service pour un flag de
  widget). À instruire en US.
- **Migration des 3 copies nested de `CapturingLogger<T>` dans `Middleware/`** —
  hors du périmètre du diff.

## Sonar log

**Phase 1 (new code) — VERTE. Phase 2 (dette legacy) — skippée, explicitement.**

### KPIs qualité

| Métrique | Baseline (2026-09-01) | Final (2026-09-04) | Cible | Verdict |
|---|---|---|---|---|
| **Quality Gate** | OK | **OK** (5/5 conditions) | OK | ✅ |
| bugs | 0 | 0 | 0 | ✅ |
| vulnerabilities | 0 | 0 | 0 | ✅ |
| sqale_rating (maintenabilité) | A | A | A | ✅ |
| reliability_rating | A | A | — | ✅ |
| security_rating | A | A | — | ✅ |
| code_smells | 62 | 65 | — | ⚠️ voir note |
| security_hotspots (TO_REVIEW) | 3 | 3 | — | inchangé, legacy |
| coverage | 88,2 % | 88,2 % | 95 % | ❌ dette legacy |
| line_coverage | 91,4 % | 91,5 % | — | +0,1 |
| duplicated_lines_density | 0,4 % | 0,4 % | — | inchangé |
| new_coverage | — | **91,0 %** | 80 % (QG) | ✅ |
| new_bugs / new_vulnerabilities | — | **0 / 0** | 0 | ✅ |
| new_security_hotspots | — | **0** | 0 | ✅ |

### Issues sur les 13 fichiers de task-289 : **0**

Un seul finding a été trouvé et corrigé — et il est instructif :

- **CA1859** (INFO) sur `ReportRefreshOutcome(IReadOnlyList<string> missing, …)`.
  Corrigé en `List<string>` : helper **privé** dont l'unique appelant construit
  déjà une liste concrète. **C'est la passe qualité `/simplify` qui l'avait
  introduit**, sur recommandation d'une revue (« le helper ne mute rien » — vrai,
  mais hors sujet ici). Récidive d'une règle documentée depuis task-203 →
  `conventions/csharp.md` incrémenté à 2 occurrences, consigne étendue aux
  **paramètres** et non plus aux seules valeurs de retour.

### Couverture du code AJOUTÉ par la task — mesurée fichier par fichier

| Fichier | line_coverage | Lignes non couvertes |
|---|---|---|
| `FeatureFlagWarmUpService.cs` | **100 %** | 0 |
| `FeatureFlags.cs` | **100 %** | 0 |
| `FeatureFlagMetrics.cs` | **100 %** | 0 |
| `FlagsmithFeatureFlagService.cs` | 92,6 % | 16, **toutes pré-existantes** |

La première mesure donnait `FeatureFlagWarmUpService.cs` à 87,5 % : les 2 lignes
manquantes étaient la branche `catch (OperationCanceledException)` de l'amorce
(arrêt de l'hôte pendant le warm-up). Un test l'a couverte, et vérifie en plus
qu'elle est **silencieuse** — un arrêt de pod est normal, y journaliser un
warning salirait chaque redéploiement.

Les 16 lignes non couvertes de `FlagsmithFeatureFlagService.cs` ont été
**inspectées ligne à ligne** (`api/sources/lines`) : ce sont le chemin frais du
snapshot d'identité (278), l'adoption du snapshot Redis d'identité (350-369) et
le log de reprise (486-488) — task-199/201/274. **Aucune n'appartient à
task-289.**

### Deux réserves de méthode, à ne pas lire comme des succès

1. **La cible `new_coverage ≥ 95 %` du playbook n'est pas opposable sur ce
   serveur.** `new_lines` vaut **45 025** pour un diff de ~800 lignes — plus que
   le `ncloc` total du projet (39 687). La période « new code » de cette
   instance ne délimite donc rien d'utile, et `new_coverage` mesure en réalité
   ~tout le projet. C'est pourquoi la couverture du code neuf a été établie
   **fichier par fichier** ci-dessus, ce qui est opposable, plutôt que par un
   agrégat qui ne l'est pas. Le seuil du Quality Gate (80 %) est respecté dans
   les deux lectures.
2. **`code_smells` 62 → 65 (+3) n'est pas attribuable à task-289** : les issues
   sur les fichiers de la task sont à 0. La baseline datait du **2026-09-01**,
   donc d'un `develop` antérieur au merge de task-285 (`83fcaa6`) dont ma
   branche part. Les +3 viennent de ce code déjà mergé, pas d'ici. Une baseline
   prise sur le vrai merge-base l'aurait montré — c'est une limite du protocole,
   signalée et non masquée.

### Phase 2 (dette legacy) — skippée

`coverage` global reste à 88,2 % contre 95 % visés. L'atteindre demanderait
d'écrire des tests sur du code sans rapport avec cette US, hors périmètre
(règle 6, scopes isolés). Le playbook autorise explicitement ce skip : Phase 2
est best-effort et ne bloque jamais le cycle. Les 3 security hotspots
`TO_REVIEW` (`Program.cs` ×2, `BaseRepository.cs`) restent en attente de revue
humaine — aucun n'est sur du code de task-289.

### Coût mesuré

3 analyses complètes (build Release + 5 passes OpenCover chacune). ⚠️ **Les
`begin`/`end` du scanner ne sont pas dans le journal de mesure** : mon script
n'a instrumenté que les `build` et les `test`. C'est un trou d'instrumentation
de ce run, pas une mesure à zéro — le `--kind scan` du playbook attend d'être
posé autour du scanner lui-même.

### Incident d'outillage du pré-flight (corrigé dans le playbook)

`docker start sonarqube` rend la main **sans erreur**, puis le serveur s'arrête
seul sur `UnknownHostException: sonarqube_db` et repasse en `Exited (0)` — code
de sortie 0, donc aucun signe de panne. Le poll de 90 s du pré-flight expirait
intégralement en concluant « serveur pas prêt ». L'installation de ce poste est
un **couple** `sonarqube` + `sonarqube_db` (postgres:15) ; le pré-flight ne
démarrait que le premier. Corrigé dans `agents/sonar.md` (commit `2472b07`).

Par ailleurs, la version du conteneur a **rebasculé de 25.6.0 à 9.9.8 en deux
jours** (donc `sonar.login` et non `sonar.token`) : cinquième bascule du
tableau du playbook, et la première *descendante*. Aucune tendance à
extrapoler ; le `curl` de contrôle reste le seul geste fiable (commit `6972864`).

## Develop log — reprise après CHANGES REQUESTED

Les trois bloquants de `questions/task-289.md` sont levés. Chacun est vérifié
par **contre-épreuve de mutation**, pas par relecture — c'était le reproche
adressé à la première passe.

| Bloquant | Contre-épreuve | Avant | Après |
|---|---|---|---|
| 1 — test de convention vacuo | `FailClosedAtColdStart` vidée | restait **vert** | **tombe** |
| 2 — test décoratif | correctif d'isolation annulé | restait **vert** | **tombe** (7/11 de la classe) |
| 3 — libellé de l'amorce | test « Flagsmith injoignable au boot » | n'existait pas | RED puis GREEN |

### Ce qui a changé

1. **`FailClosedList_IsCompleteAndAnchoredOnTheAiPipeline`** (renommé) : assertion
   de **complétude** (projection exacte de `All`, ordre compris) plus un
   **ancrage** sur `AiPipeline`. L'ancienne version n'assertait qu'une identité
   algébrique entre deux dérivés de la même source, satisfaite par le vide.
2. **`MissingFlag_TakesItsDeclaredColdStartDefault_WhileOthersStayLive`**
   (renommé) : `defaultValue: false`, donc les flags **présents** portent une
   valeur qui **contredit** leur repli. Sans cela le test ne pouvait pas
   distinguer « chaque absent prend SON repli » de l'incident lui-même. Même
   correction sur `OneDeclaredFlagMissing_…`, dont 2 des 3 assertions étaient
   vacuoses.
3. **`FeatureFlagWarmUpService`** : `NoStateCameBack()` distingue « état chargé »
   de « replis appliqués ». **Limite assumée et documentée** : ce contrôle
   **sur-avertit sans jamais sous-avertir** — si Flagsmith rend par coïncidence
   exactement les valeurs de repli, on annonce à tort qu'aucun état n'est revenu ;
   mais dès qu'une valeur diffère, un état est certainement revenu. Le contrôle
   exact demanderait au service d'exposer l'existence de son snapshot, soit un
   changement de contrat d'interface — écarté, comme la revue le recommandait.

### Passe qualité

Le montage du service réel était recopié 3 fois dans les tests du warm-up
(duplication introduite par les 2 tests du bloquant 3) → factorisé en
`RealFlagServiceOver(client)`.

### Note sur l'historique de la branche

La branche a été **squashée en un commit** (`6dfa5d3`) entre la revue et cette
reprise, hors forge. Contrôlé avant de reprendre : rien n'a été perdu — les 13
fichiers sont présents, CA1859 et `Task.Yield` appliqués, local et distant
alignés. La branche porte maintenant 3 commits.

Build 0 erreur / 0 warning, **4025 tests verts**.

### Non bloquants de la revue, toujours écartés

Le log de résolution de dérive (symétrique de `TryConsumeRecovery`), l'invariant
d'ordre `slot.Gate → _gate` à écrire dans le XML, `ConcurrentDictionary` dans
`RefreshStatusCounter`, et le health check `feature-flags` — inchangés, motifs
au `## Develop log` initial.

## Sonar log — reprise

**Phase 1 (new code) — VERTE.** Phase 2 (dette legacy) skippée, même motif.

| Métrique | 1er passage | Reprise | Cible | Verdict |
|---|---|---|---|---|
| **Quality Gate** | OK | **OK** (5/5) | OK | ✅ |
| new_bugs / new_vulnerabilities | 0 / 0 | **0 / 0** | 0 | ✅ |
| new_security_hotspots | 0 | **0** | 0 | ✅ |
| new_coverage | 91,0 % | **91,0 %** | 80 % (QG) | ✅ |
| bugs / vulnerabilities | 0 / 0 | 0 / 0 | 0 | ✅ |
| sqale_rating | A | A | A | ✅ |
| code_smells | 65 | 66 | — | ⚠️ non attribuable (voir note) |
| coverage projet | 88,2 % | 88,2 % | 95 % | ❌ dette legacy |

**Issues sur les 15 fichiers du diff : 0.** Aucun finding à corriger cette fois
(le premier passage en avait un, CA1859, déjà corrigé).

### Couverture du code de la task

| Fichier | line_coverage | Non couvertes |
|---|---|---|
| `FeatureFlagWarmUpService.cs` | **100 %** | 0 |
| `FeatureFlags.cs` | **100 %** | 0 |
| `FeatureFlagMetrics.cs` | **100 %** | 0 |
| `FlagsmithFeatureFlagService.cs` | 92,6 % | 16, **inchangées** |

Les 16 lignes non couvertes sont exactement les mêmes qu'au premier passage —
la reprise n'a ajouté aucun code à ce fichier. Elles avaient été inspectées
ligne à ligne (`api/sources/lines`) et appartiennent toutes à task-199/201/274 :
chemin frais du snapshot d'identité, adoption du snapshot Redis d'identité, log
de reprise.

### Deux réserves, reconduites

1. **`code_smells` 65 → 66 n'est pas attribuable à task-289** : les issues sur
   les fichiers de la task sont à **0**, mesuré sur les 15 fichiers du diff. Le
   +1 vit ailleurs et n'a pas été chassé — hors périmètre (règle 6).
2. **La cible `new_coverage ≥ 95 %` du playbook n'est pas opposable** sur ce
   serveur : `new_lines` dépasse le `ncloc` total du projet, la période « new
   code » ne délimite donc rien d'utile. La couverture du code neuf est
   établie fichier par fichier ci-dessus, ce qui l'est.

### Flaky pré-existant rencontré

`MailReadObjectCountTests.AContentReadReportsAMeasuredZeroForTheLotsItDidEnter`
a échoué une fois pendant les passes OpenCover. Même famille (tests de
télémétrie sensibles à la charge) que celle attribuée ce matin à `origin/develop`
par contre-épreuve sur worktree vierge — deux runs, dont un rouge sur d'autres
tests de la même famille, à code identique. Ce test n'est dans aucun fichier du
diff de task-289.
