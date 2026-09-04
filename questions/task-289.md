# questions/task-289.md — revue de code : CHANGES REQUESTED

**Écrit par** `/review` le 2026-09-04. **Chaîne arrêtée avant l'ouverture de la
PR** (playbook `/review` : la forge ne corrige pas le code en revue).

**État** : `tasks/wip-task-289.md`, branche
`fix/task-289-flag-absent-isole-du-snapshot` poussée sur `api-mail`
(4 commits, `be1ba41`). Build 0 erreur, **4023 tests verts**, Quality Gate
SonarQube **OK**, 0 issue sur les 13 fichiers de la task.

Le **correctif de production est bon** et les points à risque ont été vérifiés,
pas supposés :

- pas de deadlock — l'ordre des verrous a été vérifié **dans les deux sens** ;
- pas de fuite de l'identité praticien (adresse MSSanté) dans les logs ;
- filtre d'exception exact — l'héritage `FlagsmithAPIError : FlagsmithClientError`
  confirmé par réflexion sur l'assembly 9.0.0, et les messages d'exception
  énumérés pour établir ce qui peut réellement passer le filtre ;
- initialisation statique de `FeatureFlags` correcte (ordre textuel, échec
  bruyant si on la casse) ;
- l'amorce ne peut ni bloquer ni tuer le démarrage du pod ;
- l'invariant task-199 « le dernier état connu prime » est préservé, et
  **mesuré** : annuler le correctif fait tomber 6 tests sur 16.

Ce qui bloque, ce sont **trois corrections mécaniques**, dont deux établies par
**mutation expérimentale** — c'est-à-dire en cassant le code et en constatant
que les tests restaient verts. Aucune n'est architecturale.

---

## Bloquant 1 — `FeatureFlagsConventionTests.cs:41` : le test reste vert quand le signal disparaît

**Mesuré** : en remplaçant `FeatureFlags.FailClosedAtColdStart` par une liste
vide, `FeatureFlagsConventionTests` passe **2/2 vert**.

Les deux assertions de `FailClosedList_MatchesTheDeclaredFallbacks` sont
satisfaites **à vide** : `string.Join(", ", [])` vaut bien `""`, et
`Assert.All([], …)` ne vérifie rien.

**Pourquoi c'est grave, et pas cosmétique.** Ce champ n'est pas décoratif : il
alimente `{FailClosedFlags}` dans le message de panne à froid
(`FlagsmithFeatureFlagService.cs:602`). Vide, le pod journalise

> `applying declared cold-start defaults:  stay DISABLED`

et **ne nomme plus jamais `ai_pipeline`**. C'est la disparition exacte du signal
que cette US existe pour créer, et le test censé le garder ne la voit pas.

**Correction** — asserter la **complétude**, pas seulement la cohérence entre
deux dérivés de la même source :

```csharp
Assert.Equal(
    FeatureFlags.All.Where(f => !FeatureFlags.ColdStartDefault(f)).ToList(),
    FeatureFlags.FailClosedAtColdStart);
Assert.Contains(FeatureFlags.AiPipeline, FeatureFlags.FailClosedAtColdStart);
```

La seconde ligne est celle qui compte : elle ancre le test sur le flag dont
l'extinction est un incident **produit et de confidentialité**.

---

## Bloquant 2 — `FlagsmithMissingFlagIsolationTests.cs:147` : test décoratif

**Mesuré** : en retirant le `try/catch` de `EvaluateDeclaredFlagsAsync` — le
correctif exact — `MissingFlag_TakesItsDeclaredColdStartDefault` **reste vert**.

**Cause.** Les deux flags choisis sont assertés **à leur valeur de repli**
(`DashboardWidgetPatients` fail-open `true`, `AiAutoTagging` fail-closed
`false`). Or quand le rafraîchissement avorte entièrement — l'incident
lui-même — `Resolve` rend justement les replis. Le test ne peut donc pas
distinguer « chaque flag absent prend SON repli » de « tous les flags sont
retombés sur leur repli ». Son intention est juste, sa formulation ne la teste
pas.

**Correction** — stubber les flags **présents** à une valeur qui contredit leur
repli :

```csharp
StubEnvironment(defaultValue: false,
    FeatureFlags.DashboardWidgetPatients, FeatureFlags.AiAutoTagging);
…
Assert.False(all[FeatureFlags.DashboardWidgetMailCounters]); // présent et OFF ≠ son repli true
```

Même remarque, plus douce, sur `:110`
`OneDeclaredFlagMissing_OtherFlagsStillCarryTheirFlagsmithValue` : deux de ses
trois assertions sont vacuoses (valeurs assertées égales aux replis), seule
`Assert.True(all[AiEmbedding])` fait échouer le test. Il tombe bien, mais son
titre promet plus qu'il ne vérifie. Même remède.

---

## Bloquant 3 — `FeatureFlagWarmUpService.cs:56` : l'amorce affirme un succès qu'elle n'a pas vérifié

```csharp
var flags = await featureFlagService.GetAllFeaturesAsync(stoppingToken);
logger.LogInformation(
    "[FeatureFlag] Startup flag state loaded — {EnabledCount}/{DeclaredCount} declared flag(s) enabled", …);
```

`GetAllFeaturesAsync` **ne lève jamais** — c'est son contrat, rappelé deux
lignes plus haut. Donc quand Flagsmith est injoignable au boot, elle rend les
onze **replis déclarés**, et l'amorce journalise en `Information` :

> `[FeatureFlag] Startup flag state loaded — 8/11 declared flag(s) enabled`

Aucun état n'a été chargé, et l'étage IA est éteint.

**C'est mot pour mot le défaut que `LogRefreshFailure` vient de corriger**
(« serving last known flag state » affirmé à froid) — réintroduit à l'endroit le
plus lu du journal, celui où cette US demande précisément qu'on regarde. Le
warning de panne est bien émis en parallèle par le service, donc le signal n'est
pas perdu ; il est **contredit sur la ligne suivante**.

**Correction** — distinguer les deux cas sans nouvelle API :

```csharp
var noStateLoaded = FeatureFlags.All.All(f => flags[f] == FeatureFlags.ColdStartDefault(f));
```

et choisir le libellé en conséquence (ou neutraliser l'affirmation :
« startup flag evaluation ready »). **Ajouter le test manquant** : « Flagsmith
injoignable au boot » n'est couvert par aucun test de
`FeatureFlagWarmUpServiceTests` — c'est ce trou qui a laissé passer le libellé.

---

## Non bloquants (à trancher, pas exigés)

1. **La dérive n'a pas de log de résolution.** `_flagsmithFailures` a son
   `TryConsumeRecovery` (« refresh recovered »), `_driftReports` n'a **aucun**
   pendant. Un opérateur qui crée les huit flags manquants n'obtient donc
   **aucune confirmation** que la dérive est résorbée — et le silence est
   indistinguable d'un throttle en cours de fenêtre. C'est la moitié fermante de
   l'histoire d'observabilité que cette US revendique. ~5 lignes.
2. **Un invariant de verrou devenu porteur n'est pas écrit.** Le chemin de
   succès du rafraîchissement d'identité prend maintenant `slot.Gate` **puis**
   `_gate` (avant, seul le `catch` touchait `_gate`) : c'est une imbrication
   **nouvelle sur le chemin nominal**. L'ordre inverse n'existe nulle part
   (vérifié), donc pas de deadlock — mais « `slot.Gate` avant `_gate`, jamais
   l'inverse » mérite d'être écrit dans le XML de `ReportRefreshOutcome`.
   *Effet de bord à mesurer un jour* : pendant une dérive persistante — le
   scénario de l'incident, huit flags absents pendant des heures — **chaque**
   rafraîchissement d'identité prend `_gate`, le verrou global sous lequel un
   appel réseau Flagsmith peut s'exécuter. À 500 praticiens, les refresh
   d'identité se sérialisent derrière ce réseau. La dette est pré-existante
   (task-199 a mis le réseau sous `_gate`) mais task-289 **en élargit
   l'exposition**.
3. **`RefreshStatusCounter.cs:24`** — `Dictionary<string, long>` sans
   synchronisation. Le raisonnement « callbacks synchrones + collection xUnit
   sérialisée » vaut *entre* classes, mais les rafraîchissements sont des
   continuations fire-and-forget : une task résiduelle d'un test antérieur de la
   **même** classe peut émettre pendant le test suivant. Fenêtre étroite, mais
   les assertions `Assert.Equal(0, counters["failure"])` sont exactement celles
   qui deviendraient un rouge inexplicable. `ConcurrentDictionary` coûte une
   ligne.
4. **Direction de fragilité du filtre d'exception**, à connaître : il est
   *ouvert par défaut*. Un `FlagsmithClientError` nu **nouveau** apparaissant un
   jour sur ce chemin (montée de version du paquet) serait classé « flag
   absent » et publierait un snapshot de replis — l'acquis task-199 détruit en
   silence. Toute autre exception avorte le rafraîchissement, ce qui est la
   direction sûre. Rien à corriger aujourd'hui ; la garde serait un test qui
   échoue quand la hiérarchie d'exceptions du paquet change.

---

## Reprise

Les trois bloquants sont dans **deux fichiers de test et un libellé de log** —
aucun ne touche la logique du correctif. Reprise :

```
/develop 289      # applique les 3 corrections + le test manquant
```

puis la chaîne reprend son cours (`/sonar` → … → `/review`). Le `## Sonar log`
et le `## Develop log` de la task sont à jour et n'ont pas à être refaits ; seule
la re-validation build + tests est nécessaire.
