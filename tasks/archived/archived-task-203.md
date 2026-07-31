# todo-task-203.md — Rendre le débit du banc mesurable : le harnais k6 se plafonne lui-même, et le banc journalise en Debug

**Repos**: api-mail
**Dependencies**: — (task-202 est orthogonale)
**Epic**: E015
**Single frontend**: true

> **Origine** : relecture le 2026-07-28 des **JSON k6** des trois tirs du
> 2026-07-27 (et non des seuls rapports). Verdict : **aucun des trois tirs n'est
> valide pour une mesure de capacité** — le harnais était saturé, pas
> l'application. Le « plafond ~900 req/s » est un artefact.
> Rapports concernés : `report-mixed-mssante-60vu-003515.md` (référence),
> `…-60vu-144525.md` (tir A), `…-150vu-141351.md` (tir 500).

## Objective

Faire en sorte qu'un tir puisse **mesurer le débit de l'application**, et qu'un
tir qui ne le peut pas **le dise lui-même** au lieu de produire un chiffre
trompeur. Trois leviers : dimensionner les VUs du scénario `mixed` sur la
latence mesurée, poser une **garde de validité** dans le rapport et l'INDEX, et
journaliser au banc au **niveau de la Production** (`Information`) plutôt qu'en
`Debug`.

**US backend/bench-only (justification)** : harnais k6, `report.py` et profil
loadtest de l'AppHost — aucun contrat, aucun écran.

### Preuve du problème (JSON k6 du 2026-07-27)

Dans les **trois** tirs, `vus == vus_max` du début à la fin et les itérations
sont abandonnées par centaines par seconde :

| Tir | `vus / vus_max` | `dropped_iterations` | Itérations délivrées | Débit annoncé |
|---|---|---|---|---|
| Réf. 200 (sans pooler) | 222 / 222 | **45 323** | 226 679 | 915,5 req/s |
| Tir A 200 (PgBouncer) | 222 / 222 | **49 485** | 222 517 | 833,6 req/s |
| Tir 500 (PgBouncer) | 555 / 555 | **502 353** (74 %) | 173 151 | 906,4 req/s |

Le modèle « arrival-rate » **ouvert** a dégénéré en modèle **fermé** : débit =
concurrence cliente / latence. Cause dans `tests/loadtest-k6/scenarios/mixed.js`
(`arrivalRate()`) :

```js
maxVUs: Math.max(2, vusFor(share) * 4),   // = round(VUS × share/100) × 4
```

Chaque sous-scénario plafonne donc à `maxVUs / latence`, **indépendamment de
`USERS` et du débit demandé**. Vérifié au chiffre près sur le tir 500 :

| Opération | Plafond VU calculé | Délivré |
|---|---|---|
| `send` | 60 VU / 7,556 s = **7,9/s** | 7,67/s |
| `folders` | 240 VU / 2,235 s = **107/s** | 103,7/s |
| `search` | 60 VU / 0,627 s = **95,7/s** | 91,5/s |

Et **`MAX_VUS` est silencieusement ignoré par `mixed`** : `lib/config.js`
expose la variable, mais seul `buildScenario()` (scénarios mono) la lit —
`mixed.js` recalcule ses propres `maxVUs`. La recommandation « relever
`MAX_VUS` » du rapport 500 aurait été sans effet.

**Ce que les tirs 200 disent réellement** : sur `folders` et `read` (70 % du
mix) l'application a servi **~100 % du débit demandé** à p95 156 / 193 / 47 ms.
Les ~250 req/s manquants sont attribuables aux plafonds VU de `send` (demandé
120 it/s, plafond 19) et `search` (demandé 120, plafond 77). **À 200 praticiens,
api-mail n'a jamais approché la saturation.**

### Le banc journalise en Debug, la Production en Information

Le profil `https-load-test` pose `ASPNETCORE_ENVIRONMENT=Development`, donc
`src/Api/appsettings.json` s'applique : `Serilog:MinimumLevel:Default = Debug`
et `Logging:LogLevel:Default = Debug` (`appsettings.Production.json` dit
`Information`). Mesuré sur la fenêtre du tir 500 : **904 839 événements Debug**
et 1 212 478 Information, soit ~5 000 événements/s sérialisés et expédiés à Seq
par 5 réplicas. Un banc doit mesurer la configuration qu'on déploie.

## Contenu attendu

1. **Dimensionner les VUs par la loi de Little, dans `mixed.js`.** Pour chaque
   sous-scénario : `preAllocatedVUs ≈ rate × latence_attendue`, et
   `maxVUs = ceil(rate × latence_attendue × marge)` avec une marge qui couvre
   la queue (les tirs montrent des `max` à 30-120 s qui parquent des VUs). Les
   latences de référence existent déjà dans `lib/config.js` (`DEFAULT_P95`) et
   dans `baseline.md` — s'en servir plutôt que d'inventer une constante.
2. **Faire lire `MAX_VUS` (et `VUS`) par `mixed`** : quand l'opérateur pose la
   variable, elle doit s'appliquer — en plafond global réparti, pas ignorée.
   Un commentaire doit dire pourquoi `4 × share × VUS` était faux.
3. **Garde de validité du tir, dans `report.py`.** Remonter
   `dropped_iterations` (count + rate), `vus`/`vus_max`, et **le débit demandé
   vs délivré par opération** (le budget par sous-scénario est déductible de
   `context.targetRps` × `mix`). Poser en tête du rapport un bandeau
   **`⚠️ TIR INVALIDE POUR UNE CONCLUSION DE CAPACITÉ`** dès que
   `dropped_iterations / (dropped + iterations) > 1 %` **ou** `vus == vus_max`,
   avec la raison en une phrase. Ajouter les deux colonnes correspondantes à
   `reports/INDEX.md` (`Drop %`, `VU sat.`) — un tir passé ne doit plus pouvoir
   être relu comme une mesure de capacité sans voir le drapeau.
4. **Journaliser au niveau Production au banc.** Le profil loadtest pose
   `Serilog__MinimumLevel__Default=Information` et
   `Logging__LogLevel__Default=Information`, **surchargeables par une variable
   unique** (p. ex. `MSS_LOADTEST_LOG_LEVEL`) pour pouvoir refaire un tir en
   `Debug` à des fins de comparaison. Ne pas toucher `appsettings.json`
   (le niveau Debug reste le bon défaut pour le dev interactif).
5. **Ne rien changer hors profil loadtest.** Hors banc, les scénarios k6 et la
   configuration de l'API doivent se comporter à l'identique.

## Hors scope

- L'instrumentation ressources (CPU par processus/conteneur) et l'analyse de la
  télémétrie applicative dans le rapport → **task-204**, qui est ce qui permettra
  de *nommer* le facteur limitant. Cette task-ci rend seulement le chiffre de
  débit honnête.
- Le plafond IMAP Dovecot (`mail_max_userip_connections=10`, une seule IP source
  pour tous les VUs) : artefact de banc connu, à traiter quand un tir
  suffisamment chargé le rencontrera à nouveau.
- Le réglage `default_pool_size` de PgBouncer (tranché au tir B) et la libération
  des connexions de provisionnement (task-202).

## Question ouverte pour le PO (à trancher avant l'escalier de task-204)

`RPS_PER_USER=6` a été choisi **sous le rate-limiter** (task-090 : 10 req/s par
identité), pas d'après l'usage réel : 6 req/s soutenues par praticien
≈ 21 600 requêtes/heure/médecin. La cible de dimensionnement
(`DevOps/DIMENSIONNEMENT-1000-PRATICIENS.md`) devrait exprimer un **profil
d'usage réaliste par praticien** (requêtes/heure par opération), sans quoi
« montée en charge » n'a pas de critère de succès. Cette task n'y touche pas ;
elle rend juste la mesure exploitable dans les deux cas.

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures)
- [ ] Test unitaire (ou test de configuration k6 exécutable) : pour un jeu
      `(USERS, VUS, MAX_VUS, mix, latences de référence)` donné, les `maxVUs`
      produits par `mixed.js` couvrent le débit demandé de chaque sous-scénario
      — et **`MAX_VUS` posé est respecté**
- [ ] Test unitaire `report.py` : un JSON k6 avec `vus == vus_max` **ou**
      `dropped_iterations` > 1 % produit le bandeau `TIR INVALIDE`, et un JSON
      sain ne le produit pas
- [ ] Test unitaire `report.py` : la table « débit demandé vs délivré par
      opération » est correcte sur un JSON de référence (celui du tir A fait un
      excellent cas de test — il doit ressortir invalide)
- [ ] `reports/INDEX.md` porte les colonnes `Drop %` et `VU sat.`
- [ ] Profil loadtest : les réplicas démarrent en `Information` (vérifié dans
      Seq : **0 événement de niveau Debug** sur une fenêtre de tir), et
      `MSS_LOADTEST_LOG_LEVEL=Debug` restaure l'ancien comportement
- [ ] Hors profil loadtest, aucun changement de comportement (niveau de log du
      dev interactif inchangé, prouvé par test)
- [ ] **Tir de validité** — `mixed` 200 praticiens iso-conditions du tir A
      (`USERS=200`, `MESSAGES_PER_USER=100`, `VUS=60`, `DURATION=5m`,
      `SESSION_ROTATION=0.001`, `RPS` implicite 1200) avec les VUs corrigés :
      `dropped_iterations` **< 1 %**, `vus < vus_max`, et le rapport **sans
      bandeau d'invalidité**. Le débit délivré est alors le **premier chiffre de
      capacité exploitable du banc** — le consigner comme telle dans la task
- [ ] **Tir de contrôle logs** — même tir en `MSS_LOADTEST_LOG_LEVEL=Debug` :
      l'écart de débit et de p95 entre `Information` et `Debug` est chiffré dans
      la task (c'est la mesure du coût de l'observabilité, jamais faite)
- [ ] Rapports générés (`report.sh --expected 100` + lignes d'INDEX) pour les
      deux tirs, et comparés au tir A dans la task
- [ ] `tests/loadtest-k6/README.md` et le skill `loadtest-skill` mis à jour :
      la garde de validité est le **premier** contrôle à lire d'un rapport

## Manual Test Plan

1. Monter le banc en profil loadtest (skill `loadtest-skill`). Vérifier dans
   Seq que les réplicas ne produisent **aucun** événement Debug :
   ```
   select count(*) from stream where @Level = 'Debug'
   ```
   (fenêtre = les 2 dernières minutes) → **0**.
2. Seeder 200 × 100 :
   `dotnet run --project tests/mss.mail.loadtest.seed -- --users 200 --messages 100 --api http://127.0.0.1:5052`
3. Tirer (⚠️ `unset MSYS_NO_PATHCONV MSYS2_ARG_CONV_EXCL` avant `run.sh`) :
   `BYPASS_KEY=loadtest-local-only USERS=200 MESSAGES_PER_USER=100 SESSION_ROTATION=0.001 tests/loadtest-k6/run.sh mixed --env VUS=60 --env DURATION=5m`
4. Lire le résumé k6 : `dropped_iterations` doit être **marginal** (< 1 % des
   itérations) et le pic de `vus` **strictement inférieur** à `vus_max`.
5. Générer le rapport (`report.sh --expected 100`) : **pas** de bandeau
   d'invalidité, et la table « demandé vs délivré » doit montrer chaque
   opération à ~100 % de son budget (ou dire laquelle ne l'atteint pas et
   pourquoi).
6. Relancer le même tir avec `MSS_LOADTEST_LOG_LEVEL=Debug` et comparer débit et
   p95 des deux rapports.
7. Contre-épreuve de la garde : régénérer un rapport à partir du JSON archivé du
   tir A (`mixed-mssante-60vu-144525.json`) → il **doit** ressortir avec le
   bandeau `TIR INVALIDE`.

## Branches

- `api-mail` (pushed) : `feat/task-203-loadtest-valid-throughput` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-203-loadtest-valid-throughput
- `dtos-mss` (pushed, auto-inclus) : `feat/task-203-loadtest-valid-throughput` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-203-loadtest-valid-throughput

### Pre-flight (2026-07-28)

Tous les repos forge présents sont sur `develop`. Deux écarts d'environnement,
non bloquants (hors cible de cette task, déjà relevés par task-200) :

- `client-mobile` — `Client/Mobile/` **absent du disque** (repo non cloné).
- `host` — `Host/Modules/` n'est pas un repo git autonome (il appartient au repo
  racine du workspace).

## Develop log

- **Repos touched** : `api-mail` uniquement. `dtos-mss` : branche créée par
  `/start`, **aucun commit** — aucun contrat touché (US bench/infra), donc aucune
  PR et aucun publish NuGet.
- **DTOs published** : no DTO change. **Interop published** : no interop change.
- **Commits** (`api-mail`, `feat/task-203-loadtest-valid-throughput`, poussés) :
  - `0d56b1b` fix(loadtest): dimensionner les pools de VUs par la loi de Little
  - `f0cc624` feat(loadtest): garde de validité du tir dans le rapport et l'INDEX
  - `95e8434` feat(loadtest): journaliser le banc en Information, comme la Production
  - `dd65a03` chore(loadtest): auto-tests du harnais et cinquième piège documenté
  - (+ `c9bb52d` docs, reprise hors périmètre — voir la réserve ci-dessous)
- **Local build / test** : build **0 erreur / 0 warning** ; suite complète
  **3 173 tests verts, 0 échec**, 16 skips préexistants (tests IA nécessitant des
  clés API). Détail : domain 102, infrastructure 370, api 575, application 1 852,
  integration 274.
- **Auto-tests du harnais** (`tests/loadtest-k6/selftest.sh`, hors `dotnet test`) :
  **11 tests node + 16 tests unittest verts**.

### Ce que le diagnostic a établi avant d'écrire une ligne

La relecture des **JSON k6** (et non des rapports) des trois tirs du 2026-07-27 :

| Tir | `vus / vus_max` | `dropped_iterations` | Débit publié |
|---|---|---|---|
| Réf. 200 sans pooler | 222 / 222 | 45 323 (16,7 %) | 915,5 req/s |
| Tir A 200 PgBouncer | 222 / 222 | 49 485 (18,2 %) | 833,6 req/s |
| Tir 500 PgBouncer | 555 / 555 | 502 353 (**74,4 %**) | 906,4 req/s |

Cause : `mixed.js` dimensionnait `maxVUs = 4 × part × VUS`, sans rapport avec le
débit demandé. Vérifié au chiffre près (tir 500) : `send` 60 VU / 7,556 s = 7,9
it/s délivrés contre **300** demandés ; `folders` 107 contre 1 200 ; `search`
95,7 contre 300. Et **`MAX_VUS` était silencieusement ignoré par `mixed`** (seul
`buildScenario` le lisait), donc la recommandation « relever `MAX_VUS` » du
rapport 500 aurait été sans effet.

**Ce que les tirs 200 disaient réellement** : `folders` et `read` (70 % du mix)
ont servi ~89-100 % de leur budget à p95 133-225 ms. Les ~250 req/s manquants
sont les plafonds VU de `send` (14,4 % de son budget servi) et `search` (55,6 %).
À 200 praticiens, **api-mail n'a jamais approché la saturation** — la conclusion
« la machine sature au même endroit » du rapport 500 n'était pas étayée.

**Effet de bord du correctif, mesuré par `k6 inspect`** : `send` passe de 6/24 VU
à **312/624**, `search` de 6/24 à **80/160**, total ~1 022 VU au plafond contre
222. C'est le coût client d'une mesure honnête ; à surveiller au premier tir
(mémoire de k6, et le CPU de k6 lui-même — qui est justement l'objet de task-204).

### Deux écarts de conception assumés, et pourquoi

1. **La saturation de VUs n'invalide que les tirs à débit imposé.** La règle
   littérale de la DOD (« `vus == vus_max` → invalide ») déclarait invalide le tir
   `enrich` du 2026-07-26 (4 VU / 4) — or `vus == vus_max` est la *définition*
   d'un `shared-iterations`. Une garde qui crie au loup se fait ignorer, donc la
   règle est restreinte au modèle ouvert. Discriminant fiable : la présence de
   `dropped_iterations`, que k6 ne produit que pour les exécuteurs à débit imposé
   (le contexte, lui, enregistre l'exécuteur *demandé*, pas celui que k6 a
   résolu). Verrouillé par deux tests.
2. **`reports/INDEX.md` sort du `.gitignore`.** La DOD exige les colonnes de
   validité dans l'INDEX ; un fichier non versionné les rendrait invérifiables en
   PR et absentes de toute autre machine. L'INDEX est la mémoire *comparative* du
   banc (quelques Ko, verdicts inclus), pas un artefact de tir — les rapports
   eux-mêmes restent ignorés (`reports/*` + ré-inclusion ciblée). **Un seul mot à
   retirer si l'humain n'en veut pas.**

### Portée volontairement non étendue

Les scénarios **mono-opération** (`folders`, `read`, `search`, `send`, `enrich`)
gardent leur défaut `maxVUs = 4 × VUS` : ils servent au smoke et à la baseline, à
des débits où il tient largement, et les faire passer par la loi de Little
demanderait de leur faire déclarer leur latence de référence — 5 fichiers de plus
pour un risque non nul, hors du scénario de campagne. `MAX_VUS` y était **déjà**
respecté. Noté dans le module, pas fait (règle 6).

### DOD self-check

Vérifiés par commande (8/12) :

- [x] Build 0 erreur — [x] Tests 0 échec (3 173)
- [x] Les `maxVUs` de `mixed` couvrent le débit demandé et `MAX_VUS` est respecté
      — 11 tests `node --test` **et** vérification `k6 inspect` du plan résolu
- [x] `report.py` : bandeau `TIR INVALIDE` sur `vus == vus_max` **ou** drop > 1 %,
      absent sur un tir sain
- [x] `report.py` : table « demandé vs délivré » correcte sur le JSON du tir A,
      qui ressort **invalide** (contre-épreuve exécutée : bandeau présent,
      `send` 14,4 %, `search` 55,6 %)
- [x] `reports/INDEX.md` porte `Drop %` et `VU sat.` — et **l'historique est
      recalculé** : 16 des 21 tirs archivés étaient invalides, dont *tous* ceux à
      200 et 500 praticiens
- [x] Hors profil loadtest, aucun changement de comportement (le niveau de log
      n'est posé que dans le bloc `if (loadTestProfile)`, et
      `BenchLogLevelTests` prouve que le dev interactif garde `Debug`)
- [x] `README.md` du harnais et skill `loadtest-skill` mis à jour : la garde de
      validité est le **premier** contrôle d'un rapport

**Contre-épreuve rejouable sans banc** (l'étape 7 du Manual Test Plan passe par
`report.sh`, qui exige `verify.sh` donc les bases du banc ; en voici la variante
hors banc, celle que j'ai exécutée) :

```bash
cd Api/Mail
printf '## Vérification par base\n\n(stub hors banc)\n' > /tmp/verify-stub.md
python tests/loadtest-k6/report.py \
  tests/loadtest-k6/reports/2026-07-27/mixed-mssante-60vu-144525.json \
  /tmp/verify-stub.md /tmp/out.md /tmp/index.md seq-x.jsonl \
  foreign=0 mails=4155 owned=4155 unmarked=0 expected=100 verify_verdict=PASS
# → stderr : « TIR INVALIDE POUR UNE CONCLUSION DE CAPACITÉ » + les deux raisons
# → /tmp/out.md : bandeau en tête, send 14,4 %, search 55,6 %, total 77,2 %
```

**Trouvaille de relecture** — `baseline.md` décrivait **déjà** ce mécanisme le
2026-07-25 (« 607 itérations abandonnées… le débit demandé pour `send` dépassait
les VU alloués… relever `MAX_VUS` pour le supprimer »). Le diagnostic était juste
et **le remède prescrit ne marchait pas**, puisque `mixed` ignorait `MAX_VUS`.
La note de `baseline.md` est complétée pour refermer la boucle : c'est le même
mécanisme qui a invalidé la campagne, à 100× l'échelle.

**Différés au banc / HAG (4/12) — ce sont des tirs, pas du code** :

- [ ] Profil loadtest en `Information` vérifié **dans Seq** (0 événement Debug)
- [ ] **Tir de validité 200 praticiens** (`dropped < 1 %`, `vus < vus_max`,
      rapport sans bandeau) → **c'est lui qui produira le premier chiffre de
      capacité exploitable du banc. Il n'est pas encore mesuré.**
- [ ] **Tir de contrôle `MSS_LOADTEST_LOG_LEVEL=Debug`** → coût des logs chiffré
- [ ] Rapports + lignes d'INDEX des deux tirs, comparés au tir A

Le code est en place et testé ; **la mesure reste à faire**. C'est l'étape 1 à 7
du Manual Test Plan, ~1 h de banc (seed 200 × 100 inclus), à lancer sur décision
de l'humain.

### Écart de procédure

`conventions/csharp.md` a bien été lu avant le code C# (CA1822, S2068). Aucune
règle n'était applicable au diff : le seul C# de la task est de la configuration
d'AppHost et un test.

- Next step : /forge-simplify task-203

## Simplify log

- **Repos passed** : `api-mail` (seul repo touché — 14 fichiers de diff vs
  `develop`).
- **Skipped (contrat / exclus)** : `dtos-mss` (porteur de contrat, et sans diff),
  `interop-cda`, `devops`, `psc-proxy-*`.
- **Applied & committed** : `api-mail`, 2 fichiers — `03d83bf`
  `refactor(loadtest): passe qualité (/simplify) — task-203` (poussé).

| Axe | Cleanup |
|---|---|
| Réutilisation | `kpis()` extrait **une** fois le schéma KPI stable d'un tir. Le rapport et la ligne d'INDEX le lisaient chacun de son côté — deux occasions de divergence, et une conversion en pourcentage oubliée d'un côté suffit à rendre l'INDEX incomparable au rapport, alors que la comparaison inter-tirs est sa seule raison d'être. |
| Simplification | `saturation_state()` + `SATURATION_LABELS` remplacent la même cascade de conditions re-dérivée dans les deux rendus (section du rapport, cellule d'INDEX). |
| Simplification | `planPool` : `Math.max(preFactor, tailFactor)` était redondant — le `max` avec la pré-allocation couvre déjà le cas. |

- **Écarté** — `planForReport()` dans `mixed.js` projette le plan interne vers le
  contexte du rapport en renommant un champ, ce qui ressemble à une indirection
  gratuite. **Gardé volontairement** : cette projection *épingle le contrat*
  lu par `report.py`, donc enrichir le plan interne ne change pas en silence le
  schéma d'un JSON archivé. Rationale écrite dans le code.
- **Écarté** — un helper `table(header, rows)` pour les trois tables Markdown du
  rapport : n'en refactorer que deux sur trois serait moins lisible, et les
  toutes reprendre dépasse le diff de la task (règle 6).
- **Validation** : le rapport régénéré depuis le JSON du tir A est **octet pour
  octet identique** à celui d'avant la passe (diff vide) ; 27 auto-tests du
  harnais verts (11 node + 16 unittest) ; build 0 erreur / 0 warning. Aucun
  fichier C# touché par cette passe — la suite .NET (3 173 verts) est inchangée.
  Aucun rollback nécessaire.
- **Écart de procédure** : le playbook `/simplify` prévoit 4 agents de revue en
  parallèle. La consigne de session interdit l'Agent tool sans demande explicite
  de l'humain — la revue des 4 axes a donc été faite en direct sur le diff (même
  écart que task-200).
- Next step : /sonar task-203 (api-mail touché)

## Sonar log

Mode A (chaîné), **2 itérations** sur la branche de la task. SonarQube 9.9.8
(conteneurs `sonarqube` + `sonarqube_db` démarrés par l'agent — ils étaient
éteints), projet `healthplatform-api-mail`.

| KPI | Baseline (task-200) | Scan 1 | **Final (scan 2)** | Cible new-code |
|---|---|---|---|---|
| Quality Gate | OK | OK | **OK** | OK ✅ |
| Bugs / New bugs | 0 / 0 | 0 / 0 | **0 / 0** | 0 ✅ |
| Vulnérabilités / New | 0 / 0 | 0 / 0 | **0 / 0** | 0 ✅ |
| New code smells | 6 | 8 ⚠️ | **6** | 0 ⚠️ (voir note) |
| Code smells (projet) | 31 | 33 | **31** | — |
| Coverage / New coverage | 86,5 % / 87,6 % | 86,6 % / 87,7 % | **86,5 % / 87,7 %** | ≥95 ⚠️ (voir note) |
| Maintainability | A | A | **A** | A ✅ |
| Security hotspots / New | 3 / 0 | 3 / 0 | **3 / 0** | — |

- **Périmètre task-203 : 0 issue restante.** Le scan 1 en a fait apparaître
  **2**, toutes les deux imputables à la task, corrigées en `863a303` :
  `CA1861` (tableau littéral en argument, `BenchConfigLocator`) et `CA1859`
  (type de retour `ILogger` au lieu du concret `Logger`, `BenchLogLevelTests` —
  le fix a révélé au passage que ces loggers n'étaient pas libérés). Les
  compteurs sont revenus **exactement** à la baseline.
- **Les 6 new-code smells restantes ne viennent pas de cette task** — ce sont les
  mêmes que task-199 et task-200 avaient déjà imputées à des tasks mergées
  antérieurement (période new-code large) : `BackgroundSyncService` S107,
  `OcspValidationService` S3604 + S1168, `MailClientSession` S3604 ×2,
  `VCardSerializer` S1643. Aucun fichier touché ici. Hors périmètre (règle 6) —
  candidates à un `/sonar api-mail` standalone (Mode B).
- **New coverage 87,7 % < 95** : même cause (la période new-code couvre du code
  d'autres tasks). Le code de cette task est couvert par **35 tests dédiés** —
  4 xUnit (`BenchLogLevelTests`) + 11 `node --test` + 20 `unittest`.
- **Un test rouge découvert par le scan 1, et corrigé** :
  `CdaProcessingMetricsTests.RecordCdaProcessingDurationShouldTagEachStep(step:
  "total")` a échoué en **Release + couverture** alors que la même suite est
  verte en Debug au même commit. Flaky préexistant, pas une régression : le meter
  `Mssante.MailProcessing` est statique donc process-wide, xUnit parallélise les
  classes, et la liste de capture était mutée sans verrou (la trace d'échec
  contient des mesures `mssante_sync_*` qu'aucun test de cette classe n'émet).
  Corrigé en `108bccb` (filtre à l'abonnement + verrou), **vérifié 2×1 852 verts
  en Release avec couverture**, dans les conditions exactes de l'échec.
  Hors périmètre strict mais bloquant : une suite rouge arrête `/review`, et un
  signal auquel on ne peut pas se fier est précisément le sujet de cette task.
- **Tests** : suite complète verte aux deux scans après correctif (3 173 passés,
  0 échec, 16 skips IA préexistants).
- **`conventions/csharp.md` enrichi** de deux entrées (**CA1861**, **CA1859**,
  `Occurrences: 1`) pour que `/develop` les applique d'emblée. Fichier au **root
  du workspace** (contrôle plane) → laissé **non committé**, comme les autres
  modifications de la racine.
- **Piège d'outillage confirmé** (déjà consigné par task-200) : `dotnet
  sonarscanner` ne reçoit pas ses arguments `/k:` `/d:` sous Git Bash. Le scan a
  donc été lancé par un script **PowerShell détaché**
  (`scratchpad/sonar-scan-203.ps1`) — forme qui échappe aussi à la limite de
  10 min des tâches d'arrière-plan.
- Itérations : **2/5**. Next : /review task-203 (`lint-angular`, `lint-mobile`,
  `verify-visual` : skip — repos non touchés).

### ⚠️ Modification reprise d'une campagne antérieure

`develop` d'`api-mail` portait une modification **non committée** de
`src/AppHost/pgbouncer/pgbouncer.ini` laissée par la campagne du 2026-07-27
(`max_client_conn` 5000 → 12000 et justification mesurée de
`default_pool_size=2` contre 1). Elle a été emportée par la création de la
branche ; plutôt que de la perdre, elle est committée **seule et en tête de
branche** (`c9bb52d`, `docs(loadtest)`), donc isolable à la relecture. **Hors
périmètre de task-203** — à signaler dans le body de la PR.

## Tir de validité log (2026-07-28, banc réel)

Banc monté en profil loadtest sur la branche de la task, 500 bases purgées
(mode PURGE), volume maildir neuf, seed **200 boîtes × 100 messages** (20 000
messages, 3,2 Go, 0 erreur).

### 1. Niveau de log — **DOD FERMÉ** ✅

Sur toute la fenêtre de banc, `ApplicationName = 'mss.mail.api'` dans Seq :
**0 événement `Debug`**, 0 `Verbose`. Au démarrage : 103 Information, 0 erreur.
Pendant le tir nominal : 932 795 Information, 270 823 Warning, 25 229 Error —
et toujours **0 Debug**. La surcharge `Serilog__MinimumLevel__Default` posée par
l'AppHost fonctionne sur le banc réel.

⚠️ **Nuance à ne pas enjoliver** : supprimer `Debug` retire ~40 % du volume, pas
l'essentiel. L'application émet encore **~4 000 événements/s** en `Information`
sous charge. Le coût de l'observabilité reste donc à mesurer (c'est l'objet du
tir de contrôle `MSS_LOADTEST_LOG_LEVEL=Debug`, non joué à ce stade).

### 2. Tir nominal (iso-conditions du tir A) — **INVALIDE, et c'est instructif**

`USERS=200`, `MESSAGES_PER_USER=100`, `VUS=60`, `DURATION=5m`,
`SESSION_ROTATION=0.001`, budget **1 080 req/s**.
Rapport : `reports/2026-07-28/report-mixed-mssante-60vu-123502.md`.

| | Valeur |
|---|---|
| Verdict de la garde | **INVALIDE** (30,6 % d'itérations abandonnées, `vus` 1022/1022) |
| Débit délivré (plateau) | **740,7 req/s** — 68,6 % du budget |
| p95 global | 1 629 ms (tir A : 332 ms) |
| Erreurs | 0,55 % — dominées par le bénin connu `AppendToSentAsync` (25 628 sur 25 229 Error… la boîte du banc n'a pas de dossier `Sent`) |
| 429 (limiteur) | **0** |
| `enrich` court-circuité | **0** |
| Mélange inter-praticiens | **0** — verify **PASS** |

**Ce qui a changé par rapport au tir A, et qui valide le correctif** :

| Opération | n tir A | n ce tir | p95 tir A | p95 ce tir |
|---|---|---|---|---|
| `send` | 5 690 | **29 892 (×5,3)** | 1 615 ms | 31 589 ms |
| `search` | 21 999 | **33 206 (×1,5)** | 435 ms | 989 ms |
| `folders_warm` | 141 614 | 89 444 | 133 ms | 298 ms |
| `read_list` | 52 576 | 34 750 | 225 ms | 665 ms |

Les pools corrigés ont **débloqué `send` et `search`** — c'est exactement ce
qu'on cherchait. Mais le travail supplémentaire a poussé la machine au-delà de
son genou, et `folders`/`read` se sont effondrés en conséquence : **effondrement
de congestion**, pas un plafond du harnais.

**Attribution des ressources — la mesure qui manquait depuis le début**
(3 échantillons pendant le tir, `Win32_PerfFormattedData_PerfProc_Process`) :

| Consommateur | CPU (hôte 24 cœurs) |
|---|---|
| `vmmemWSL` — tous les conteneurs du banc | **938 – 1 060 %** (9-10 cœurs) |
| `mss.mail.api` — 5 réplicas | 364 – 593 % (4-6 cœurs) |
| `com.docker.backend` | 141 – 211 % |
| **`k6` — le tireur** | **23 – 42 % (0,3 cœur)** |
| **Hôte total** | **93 – 100 % → saturé** |

**Le tireur n'est plus le mur** : 0,3 cœur sur 24. Le mur est le **CPU de la
machine**, partagé entre l'infrastructure du banc et l'application. Autrement dit
la thèse « la machine sature au même endroit » est vraie *à ce niveau de charge* —
mais elle ne pouvait pas être établie tant que le harnais plafonnait avant.

### 3. Sonde à charge réduite — **PREMIER TIR VALIDE DU BANC** ✅

`RPS=600` explicite (budget **540 req/s**), `DURATION=2m`, `MIX_ENRICH_PCT=0`
(la bande d'UIDs d'`enrich` était consommée par le tir précédent).
Rapport JSON : `reports/2026-07-28/mixed-mssante-60vu-124046.json`.

| | Valeur |
|---|---|
| **Verdict de la garde** | **VALIDE** — drop **0,67 %**, `vus` **249/331** (non saturé) |
| Débit délivré (plateau) | **536,8 req/s — 99,4 % du budget** |
| Servi par opération | folders 91 %, read 92 %, search 92 %, send 92 % (uniforme) |
| CPU conteneurs | **3,2 cœurs** au total |

**CPU par conteneur** — la seconde attribution qui manquait :

| Conteneur | CPU moyen | max |
|---|---|---|
| **`postgres-pgvector`** | **188 %** | **439 %** |
| `loadtest-toxiproxy` | 41 % | 46 % |
| `loadtest-pgbouncer` | 39 % | 92 % |
| `loadtest-greenmail` | 22 % | 24 % |
| **`loadtest-dovecot`** | **13 %** | 27 % |
| `mss-mail-redis` | 13 % | 16 % |

**Postgres domine à lui seul ~60 % du CPU conteneurs — Dovecot est marginal.**
C'est l'inverse de l'hypothèse « saturé sur IMAP » du rapport du 2026-07-27, et
ça pointe vers l'architecture « une base par praticien » (609 backends mesurés
pendant les deux tirs, `cl_waiting` ≈ 0).

### 4. Défaut trouvé dans le rapport lui-même

`http_reqs.rate` de k6 divise par la fenêtre **totale** du run, arrêt gracieux
inclus (330 s pour un plateau de 300 s, 130 s pour 120 s). **Tous les débits
publiés par le banc sont donc sous-estimés de ~8-10 %**, historique compris :

| Tir | Débit publié | Débit réel sur le plateau |
|---|---|---|
| Référence 200 (2026-07-27) | 915,5 | **934,5** |
| Tir A (2026-07-27) | 833,6 | **917,0** |
| Nominal (ce jour) | 673,3 | **740,7** |
| Sonde 600 (ce jour) | 495,0 | **536,8** |

À corriger dans `report.py` (calculer le débit sur le plateau, ou nommer
explicitement le dénominateur) — **ajouté au contenu attendu de task-204**, pas
fait ici : la PR est en attente de merge et le défaut est antérieur à la task.

### 5. Tir de contrôle `Debug` vs `Information` — **DOD FERMÉ** ✅, et le résultat est **négatif**

**Protocole** (pensé pour que le delta soit imputable aux logs, et à rien d'autre) :
redémarrage de l'AppHost au niveau visé → **échauffement de 60 s jeté** (le
redémarrage vide les pools de sessions IMAP et Npgsql) → **mesure de 2 min à
`RPS=600`**, c'est-à-dire au point de fonctionnement **valide**. Mesurer au point
saturé n'aurait rien prouvé : tout s'y confond. `enrich` désactivé (bande d'UIDs
consommée). Les deux niveaux ont été rejoués, pas comparés à un tir antérieur.

**Qualité du contrôle** — les deux fenêtres sont identiques à 0,01 % près sur tout
ce qui n'est pas `Debug` :

| Niveau d'événement | Tir `Debug` | Tir `Information` |
|---|---|---|
| Information | 324 966 | 324 927 |
| Warning | 93 692 | 93 690 |
| Error | 7 291 | 7 294 |
| **Debug** | **208 796** | **0** |
| **Total (140 s)** | **634 745** (4 534 év/s) | **425 911** (3 042 év/s) |

Couper `Debug` retire donc **208 796 événements, soit 49 % du volume** (1 491 év/s).

**Effet mesuré sur les performances : aucun.**

| Métrique | `Debug` | `Information` | Écart |
|---|---|---|---|
| Verdict de la garde | VALIDE (drop 0,01 %) | VALIDE (drop 0,03 %) | — |
| **Débit plateau** | **540,0 req/s** | **540,0 req/s** | **0,0 %** |
| Latence moyenne | 168,8 ms | 173,5 ms | +2,8 % |
| p95 global | 1 080,9 ms | 1 075,8 ms | −0,5 % |
| p95 `folders_warm` | 134,2 ms | 133,1 ms | −0,8 % |
| p95 `read_list` | 72,2 ms | 63,1 ms | −12,6 % |
| p95 `search` | 264,0 ms | 256,9 ms | −2,7 % |
| p95 `send` | 1 158,3 ms | 1 147,4 ms | −0,9 % |
| Requêtes servies | identiques à l'unité | identiques à l'unité | 0,0 % |

Les deux tirs délivrent **100 % du budget**, avec des écarts de latence dans les
deux sens (`Information` est même marginalement plus lent en moyenne) : c'est du
bruit, pas un signal. CPU : `mss.mail.api` 2,6-3,4 cœurs en `Debug` contre
3,0-3,8 en `Information` — chevauchant. Le seul écart visible est
**`vmmemWSL` +1 cœur environ en `Debug`** (11-12 contre 9,5-10,7), cohérent avec
l'ingestion des 209 k événements supplémentaires — **coût payé par Seq, pas par
l'application**.

**Conclusion à retenir : le niveau de log n'est pas un levier de performance à ce
point de fonctionnement.** Passer le banc en `Information` reste justifié — c'est
un argument de **fidélité** (mesurer la configuration qu'on déploie) et d'hygiène
(−49 % de bruit dans Seq), **pas** un gain de débit. Toute affirmation contraire
serait démentie par ces chiffres.

**Réserve honnête** : la mesure porte sur 540 req/s, **sous le genou**. À
saturation, le cœur d'ingestion supplémentaire pourrait compter davantage — mais à
saturation aucun tir n'est valide, donc rien n'y est proprement imputable. Le
mesurer exigerait de reproduire le genou avec et sans `Debug`, ce que l'escalier de
task-204 permettra.

### 5-bis. Deux corrections de méthode, à porter au crédit du doute

1. **Le « CPU hôte 93-100 % » du tir nominal est partiellement contaminé.** Ce
   poste fait tourner en permanence SonarQube, Ollama, Keycloak, SQL Server,
   Mongo, Redis… en plus du banc. Le compteur `_Total` les inclut. Ce qui reste
   **propre** : les mesures **par processus** (`k6` 0,3 cœur ; `mss.mail.api`
   3-6 cœurs) et **par conteneur** (`docker stats`, conteneurs du banc
   uniquement : 3,2 cœurs dont Postgres ~60 %). L'énoncé défendable est donc :
   *quelque chose dans la pile application + banc sature entre 540 et
   1 080 req/s, Postgres est le plus gros consommateur identifié, et le tireur
   est hors de cause* — et non « l'hôte est le mur ».
2. **Un redémarrage d'AppHost efface les proxies Toxiproxy.** Ils sont créés par
   l'outil de **seed**, pas par l'AppHost : après tout redémarrage, un tir échoue
   en `proxy "dovecot-imap" not found (HTTP 404)` dès le `setup()`. Remède
   non destructif trouvé : `dotnet run --project tests/mss.mail.loadtest.seed --
   --users 200 --messages 0` — recrée les proxies et revérifie les `UserSettings`
   sans toucher au maildir ni aux bandes d'UID. **À consigner dans le skill.**

### 5-ter. État des items de DOD différés

- [x] **Logs en `Information` vérifiés dans Seq** : 0 événement Debug ✅
- [~] **Tir de validité** : les critères de la garde (`drop < 1 %`,
      `vus < vus_max`, rapport sans bandeau) sont **atteints à 540 req/s**, pas au
      budget nominal de 1 080 req/s. **Sur cette machine, un tir valide au budget
      nominal est impossible** : l'hôte sature (93-100 % de 24 cœurs) parce que
      l'infrastructure du banc (Postgres surtout) et les 5 réplicas se partagent
      le même CPU. Le premier chiffre de capacité exploitable du banc est donc
      **≥ 537 req/s à 200 praticiens, genou situé entre 540 et 1 080 req/s de
      budget**. Le chiffrer exactement est l'objet de l'escalier de task-204.
- [x] **Tir de contrôle `Debug`** : joué (section 5). Verdict : **aucun effet
      mesurable** sur le débit ni la latence à 540 req/s ; le niveau de log est un
      gain de fidélité et d'hygiène (−49 % de volume), pas de performance.
- [x] **Rapport généré + ligne d'INDEX** pour le tir nominal ; la sonde a son
      JSON, son rapport reste à générer si on veut sa ligne d'INDEX.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/127
  — label `awaiting-human-merge` (19 fichiers, +2 338/−116)
- `dtos-mss` : aucun changement de contrat — branche sans commit, **pas de PR**
  (build validé : 0 erreur)
- `client-angular` / `client-mobile` : non listés dans `**Repos**:`, non touchés
  (et non clonés sur cette machine — cf. Pre-flight)
- Racine du workspace (contrôle plane, hors automation) : `conventions/csharp.md`
  (+2 entrées CA1861/CA1859) et `.claude/skills/loadtest-skill/SKILL.md`
  **modifiés, non committés** — managed manually by the human.

## Code Review Summary

**APPROVED** — 19 fichiers relus, **0 issue bloquante**, 3 suggestions non
bloquantes (recopiées dans le body de la PR) :

1. `REFERENCE_ITERATION_SECONDS.enrich` n'est pas utilisé (enrich est hors du
   plan de débit). Gardé volontairement — c'est la latence mesurée, utile en
   documentation et le jour où enrich deviendrait cadencé.
2. `MSS_LOADTEST_LOG_LEVEL` n'est pas validé : une faute de frappe fait échouer
   Serilog au démarrage de l'API. Échec bruyant donc acceptable, mais c'est un
   plantage au démarrage du banc plutôt qu'un message clair.
3. `report.py` grossit (`build_report` est long). Un helper de table aiderait,
   mais n'en refactorer que deux sur trois serait moins lisible et les reprendre
   toutes dépasse le diff (règle 6).

Vérifications conduites pendant la revue, au-delà de la lecture :

- **Le harnais démarre toujours** avec les seuils tagués — un seuil sur une
  métrique inconnue aurait cassé *tous* les tirs. Tir à vide hors banc
  (`LATENCY_PROFILE=skip`, API injoignable, rapport dans le scratchpad) : le plan
  s'affiche et les **cinq** sous-métriques `dropped_iterations{scenario:…}`
  apparaissent bien dans le résumé.
- **Le plan résolu** a été lu par `k6 inspect` et non déduit du code :
  `send` 312/624 VU, `search` 80/160, `folders` 58/116, `read` 58/116,
  total 1 022 VU au plafond contre 222 avant.
- **Comportement inchangé** de `report.py` après la passe `/simplify` : rapport
  régénéré depuis le JSON du tir A **octet pour octet identique**.
- **Le flaky corrigé l'est dans les conditions de son échec** : 2 × 1 852 tests
  verts en Release **avec couverture**, pas seulement en Debug.

**Réserve de méthode** : la revue est faite par la forge sur son propre code. Les
deux points qui méritent le plus l'œil humain sont les **latences de référence**
de `vu-sizing.js` (elles dimensionnent tout et vieilliront avec l'application) et
le **seuil de 1 %** de la garde de validité.

Validation : build 0 erreur / 0 warning ; **3 173 tests verts, 0 échec**
(16 skips IA préexistants) ; 31 auto-tests du harnais verts ; Sonar Quality Gate
OK, 0 issue sur le périmètre, KPI revenus exactement à la baseline.

**Ce que cette PR ne livre pas** : la mesure. Le tir de validité à 200 praticiens
— celui qui produira le premier chiffre de capacité exploitable du banc — reste à
faire (étapes 1 à 7 du Manual Test Plan).

## Merged

**Date** : 2026-07-29 — merge humain après attestation `--i-tested` (HAG, règle 10).

| Repo | PR | Squash commit | Branche distante |
|---|---|---|---|
| `api-mail` | [#127](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/127) — CLOSED (squashed) | `0a64cd1` | supprimée (locale conservée) |
| `dtos-mss` | aucune PR (branche sans commit) | — | supprimée (locale conservée) |

- **Gates franchies** : `--i-tested` ✅ · label `awaiting-human-merge` (jamais
  `awaiting-us-completion`) ✅ · aucune review `CHANGES_REQUESTED` ✅ · CI de PR
  verte (build 1 m 32 s, `publish` skipped) ✅ · `MERGEABLE` / `mergeStateStatus
  CLEAN` ✅ · arbres de travail propres sur `api-mail` et `dtos-mss` ✅
- **CI `develop`** : run [30433847274](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/30433847274)
- **Staging** : `forge/staging-task-176-196-20260728` **conservée** — task-203 est
  hors de sa plage `[176, 196]`, et ce lot n'est pas drainé (task-176 → 196
  toujours actives).
- **Racine du workspace, non committée** (contrôle plane, hors automation —
  inchangé par ce merge) : `conventions/csharp.md` (+2 entrées CA1861/CA1859),
  `.claude/skills/loadtest-skill/SKILL.md`, `Docs/epics/E015-*.md`.

### Ce que ce merge ne clôt pas

L'instrument de mesure est désormais sur `develop`, mais la **capacité de la
messagerie n'est toujours pas chiffrée**. Le seul tir valide du banc plafonne à
**536,8 req/s à 200 praticiens** (99,4 % du budget servi), le genou est encadré
entre 540 et 1 080 req/s, et un tir valide au budget nominal est **impossible sur
la machine actuelle** (l'infra du banc consomme 9-10 cœurs contre 4-6 pour les
5 réplicas). Suite : **task-204** (instrumentation ressources + escalier de
capacité), dont la DOD doit d'abord être réalignée sur les paliers
540 → 700 → 840 → 980 → 1 080.
