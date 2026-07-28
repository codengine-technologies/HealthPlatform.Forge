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
