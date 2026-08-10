# todo-task-249.md — La sonde de bonne santé fausse la mesure sur laquelle on dimensionne la base

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune
**Priorité**: **2** — gain **nul** sur la latence du médecin, **tout** sur la
lisibilité de la mesure. Elle a masqué la vraie tendance pendant trois campagnes,
et deux verdicts d'A/B de pool ont été rendus sur la grandeur qu'elle contamine.

## Objective

Que la sonde de readiness cesse de traverser le multiplexeur de connexions, pour
que `cl_waiting` ne mesure plus que le **chemin du médecin**.

## Ce qui est établi

**Par lecture de code** : `AddNpgSql(postgresConnectionString)`
([DependencyInjectionExtensions.cs:211](../Api/Mail/src/Api/DependencyInjectionExtensions.cs#L211))
utilise la chaîne **serveur**, qui en profil loadtest pointe sur PgBouncer **sans
`Database=`** — le nom de base retombe alors sur l'identité, soit `postgres`.

**Par contre-épreuve au banc** (2026-08-08) : le pool `postgres` avait disparu par
expiration ; **un seul `GET /health` l'a recréé** (`cl_active=1`). Le chemin de
contrôle (provisionnement) est bien en direct, comme l'ADR le prescrit — c'est la
**sonde de santé** qui traverse le pooler.

**Effet mesuré**, avec la ventilation livrée par task-242 :

| Tir | Attente sur bases **praticien** | Attente sur le pool **`postgres`** |
|---|---|---|
| Local 200, 2026-08-08 | 3 ms à 50, 9 ms à 100, 1,10 s à 200 | **18,3 s** à 100, **23,4 s** à 200 |
| Distant 500, 2026-08-09 | 3,1 / 62,9 / **53,3 ms** | 1 relevé à **400 ms** |

Le total publié pendant trois campagnes **sommait ces deux populations sans
rapport**. Un pool de maintenance à `default_pool_size=2`, partagé par les cinq
réplicas, produisait des attentes de plusieurs dizaines de secondes qui n'ont
**rien à voir** avec le chemin de données du médecin.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que la profondeur de 18 à 62 s est une attente réelle.** Elle
  est **compatible** avec une entrée de file abandonnée — Npgsql renonce à 5 s de
  délai, PgBouncer continue de compter l'attente du plus vieux client tant que la
  socket n'est pas fermée, et le profil en dents de scie observé va dans ce sens —
  mais elle **n'est pas prouvée** : l'état des sockets clientes n'a pas été relevé.
  Ne pas la lire comme « un médecin a attendu 62 s ».
- **Ne pas présumer qu'il faut élargir le pool de maintenance.** Le remède est de
  **router** la sonde, pas de lui faire de la place.

## Definition of Done

- [ ] La sonde de readiness emprunte la chaîne **directe** (celle du chemin de
      contrôle, déjà disponible) ou cible sa propre base — plus jamais le pooler
- [ ] Contre-épreuve au banc : après un `GET /health`, **aucun** pool `postgres`
      n'apparaît dans `SHOW POOLS`
- [ ] La sonde continue de faire son travail : elle échoue toujours quand Postgres
      est réellement indisponible (test explicite, pas seulement le cas passant)
- [ ] Hors profil loadtest, le comportement est **strictement inchangé**
- [ ] Sur un tir, la ligne « pool de maintenance » de la table des coûts résidents
      est à **zéro** — c'est le critère observable

## Manual Test Plan

- Monter le banc, appeler `GET /health` puis `SHOW POOLS` sur PgBouncer :
  aucun pool `postgres` ne doit être créé
- Arrêter Postgres et rappeler `/health` : la sonde doit **échouer** (sinon on a
  supprimé la mesure au lieu de la router)
- Lancer un tir court et vérifier que `maxwait` du pool de maintenance vaut 0

Données de test synthétiques uniquement.

## Branches

- `api-mail` (pushed) : `feat/task-249-health-probe-direct-route`
- `dtos-mss` (pushed, auto-inclus) : même nom — aucun changement de contrat attendu

## Develop log

- Repos touchés : `api-mail`. `dtos-mss` : branche vide.
- DTOs / interop : aucun changement de contrat, aucun publish.
- Commit : `045bac5` — `fix(health): router la sonde de readiness sur la route directe, jamais par le pooler`.

### Le correctif, et pourquoi c'est celui-là

`ServerConnectionString.ResolveProbeRoute(serverValue, directValue)` — la sonde
prend la **route de contrôle** quand elle existe, la chaîne serveur sinon. Le
site d'appel (`AddDefaultHealthChecks`) passe désormais par cette règle au lieu
de lire la chaîne de données en dur.

Le task file demandait explicitement de **router**, pas d'élargir le pool de
maintenance — c'est ce qui est fait : aucune borne de pooling n'est touchée.
La route directe (`MSS-MAIL-CONNECTIONSTRING-DIRECT`) **existait déjà**
(task-200, chemin de provisionnement) ; cette US ne crée pas de configuration,
elle **réutilise** celle qui porte déjà exactement la bonne sémantique.

Effet de bord bienvenu : la chaîne magique `"MSS-MAIL-CONNECTIONSTRING"` codée
en dur au site d'appel disparaît au profit de
`ServerConnectionString.EnvironmentVariableName`.

### « Hors profil loadtest, strictement inchangé » — comment c'est garanti

`MSS-MAIL-CONNECTIONSTRING-DIRECT` n'est défini **que** dans le bloc
`if (loadTestProfile)` de l'AppHost (`AppHost.cs:342`, commentaire d'origine :
« Défini UNIQUEMENT ici »). Partout ailleurs la variable est absente, donc
`ResolveProbeRoute` retombe sur la chaîne serveur et enregistre **exactement**
la même sonde qu'avant. Verrouillé par un `[Theory]` à 3 cas (`null`, `""`,
`"   "`).

### Tests (test-first, rouge vérifié avant implémentation)

- `ProbeRoute_WhenPoolerFrontsTheDataPath_UsesTheDirectRoute` — le routage.
- `ProbeRoute_WhenNoDirectRouteConfigured_FallsBackToServerString` — 3 cas,
  l'invariant hors loadtest.
- `Health_WhenPostgresUnreachable_Returns503_AndAliveStays200` — **le cas
  échouant exigé par le DOD**. Il vise un port sur lequel rien n'écoute et
  vérifie que `/health` passe bien à 503 pendant que `/alive` reste 200.
  ⚠️ **Ce test est rouge sans le correctif** : la chaîne serveur étant vide dans
  le harnais, l'ancien code n'enregistrait aucune sonde et `/health` répondait
  200 « Healthy ». Il prouve donc qu'on a **routé** la sonde, pas supprimé la
  mesure — la crainte écrite noir sur blanc dans le Manual Test Plan.
- Rouge constaté avant implémentation (`CS0117: ResolveProbeRoute` absent),
  vert après.

### Validation

- Build : **0 erreur, 0 avertissement**.
- Tests : domain 136 · infrastructure 436 · application 2 102 · integration
  **389** (405 − 16 ignorés) · api 660 → **3 723 verts**.
  Un échec isolé, non lié : `FlagsmithFeatureFlagServiceTests.RefreshFailure_LogsOncePerWindow_…`
  (test à fenêtre temporelle) lors du run Debug — **vert en isolation (8/8)** et
  **vert au run Release** de l'analyse Sonar. Aucun rapport avec le diff
  (Flagsmith ≠ sondes de santé).
- Next step : `/forge-simplify 249`

## Simplify log

- **Skip clean.** Le diff de production fait **4 lignes effectives** et va déjà
  dans le sens de la passe qualité : il **réutilise** l'abstraction existante
  (`ServerConnectionString`) et remplace une chaîne magique par sa constante.
  Rien à factoriser, rien à simplifier, aucune re-validation nécessaire.
- Next step : `/sonar 249`

## Sonar log

Analyse complète relancée (`api-mail` **modifie du C#** cette fois) :
build Release + 5 projets de tests avec couverture OpenCover + scanner.
`EXECUTION SUCCESS`, 5 rapports de couverture.

### KPIs qualité

| Métrique | Valeur |
|---|---|
| Quality Gate (new code) | **ERROR** — voir la lecture ci-dessous |
| Couverture projet | **87,6 %** (new code **87,9 %**, seuil 80 ✅) |
| Duplication (new code) | 0,06 % (seuil 3 ✅) |
| Bugs / Vulnérabilités / Hotspots / Smells | 2 / 0 / 4 / 55 |
| Ratings (fiabilité / sécurité / maintenabilité) | **C / A / A** |
| Lignes de code | 46 514 |

### ⚠️ Lecture du Quality Gate — l'ERROR n'est PAS imputable à task-249

Le QG échoue sur `new_violations = 56` et
`new_security_hotspots_reviewed = 55,6 %`. **Aucune** de ces 56 violations
n'est dans un fichier de cette task — vérifié fichier par fichier :

| Fichier de task-249 | Issues ouvertes |
|---|---|
| `src/Api/Configuration/ServerConnectionString.cs` | **0** |
| `src/Api/DependencyInjectionExtensions.cs` | **0** |
| `tests/mss.mail.integration.tests/Health/HealthEndpointsTests.cs` | **0** |

Les 56 se répartissent sur du code de tasks **déjà mergées** encore dans la
new-code period : `tests/loadtest-k6/report.py` (20), `lib/journey-model.js`
(10), `scenarios/journey.js` (7), tests d'embedding (9), divers (10). C'est
exactement le piège documenté « la new-code period inclut des tasks déjà
mergées ». Les corriger ici ferait exploser le périmètre d'une US de 4 lignes
et violerait la règle 6 (une task ne touche que son module).

**Dette introduite par task-249 : zéro.**
- Next step : `/lint-angular 249` → skip → `/review 249`

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — exploitation
- **Exigences DSR honorées** : aucune
- **INS / Consentement / Interop CI-SIS / MSSanté** : non applicable
- **Authentification PS** : inchangée — la sonde reste non authentifiée comme
  aujourd'hui, et ne doit **rien** exposer de plus qu'un état
- **Habilitations** : ⚠️ le cloisonnement « une base par praticien » ne doit pas
  être affaibli : la sonde ne doit atteindre **aucune** base praticien
- **Sécurité** : aucun secret de chaîne de connexion dans les journaux
- **Tracé PGSSI-S** : non applicable
- **Hébergement HDS** : le routage retenu doit être transposable à la cible
- **AIPD / impact RGPD** : inchangé

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/182 — label `awaiting-human-merge`
- `dtos-mss` : aucune PR — 0 commit (branche auto-incluse vide, 18e occurrence)
- Staging du run : `forge/staging-task-249-252-20260809` (api-mail) — task-249 agrégée

## Code Review Summary

**Verdict : APPROVED** — 3 fichiers, 0 blocage, 0 suggestion.

- `ServerConnectionString.cs` — ✅ la règle de routage est une fonction pure,
  testable isolément, documentée par le *pourquoi* (le coût de mesure qu'elle
  supprime) et non par le *quoi*. Placement correct : la classe modélise déjà
  les deux routes, la décision lui appartient.
- `DependencyInjectionExtensions.cs` — ✅ le site d'appel délègue au lieu de
  dupliquer la règle, et perd au passage une chaîne magique. Aucune autre
  sonde n'est affectée (Redis, bus MassTransit inchangés).
- `HealthEndpointsTests.cs` — ✅ le harnais gagne un point d'extension
  (`configureConfiguration`) appliqué **après** le blanchiment des chaînes, ce
  qui permet de réactiver une seule dépendance sans que la machine hôte
  n'influence le résultat — la propriété que le fichier revendiquait déjà.
- **Sécurité / habilitations** : la sonde reste au niveau serveur, n'atteint
  aucune base praticien, reste anonyme et n'expose qu'un état agrégé.
- **Régression hors loadtest** : impossible par construction (variable absente
  ⇒ repli), et verrouillée par test.

## Merged

- **Mergée le 2026-08-10** par l'humain (HAG, règle 10), attestation `--i-tested`.
- `api-mail` : PR #182 **squash-mergée** → `db37379` sur `develop`.
  Branche distante supprimée ; **branche locale conservée**.
- `dtos-mss` : aucune PR (0 commit). Branche distante supprimée, locale conservée.
- Clone local resynchronisé sur `develop` (`api-mail` en `db37379`).
- ⚠️ **Mergée APRÈS task-252** (`e893fcd`) bien qu'ouverte avant : GitHub a
  recalculé la mergeabilité (`UNKNOWN` → `MERGEABLE`/`CLEAN`) et les deux diffs
  sont **disjoints** — task-249 touche `ServerConnectionString.cs` /
  `DependencyInjectionExtensions.cs`, task-252 `MailController.cs` /
  `ImapService.cs` / `MailProcessingMetrics.cs`. Aucun conflit, aucun rebase.
- **CI `develop` verte sur la combinaison des deux tasks** (run `31364762340`,
  « Build and Publish », `success`) — c'est cette exécution, et non celle de la
  PR (rendue sur une base antérieure à task-252), qui valide le résultat.
- **Staging supprimée** : `forge/staging-task-249-252-20260809` (distante **et**
  locale) — le run 249-252 est désormais entièrement mergé.

> ⚠️ **Ce qui reste dû sur cette US.** Les deux critères **observables** du DOD
> exigent un banc et n'ont pas été vérifiés par le merge : après un `GET /health`,
> **aucun pool `postgres`** dans `SHOW POOLS` ; et sur un tir, la ligne « pool de
> maintenance » de la table des coûts résidents à **zéro**. C'est ce second point
> qui prouvera que la contamination de `cl_waiting` a bien disparu — donc que les
> prochains verdicts d'A/B de pool sont lisibles.
