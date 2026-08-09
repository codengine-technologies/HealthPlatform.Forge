# todo-task-244.md — Un tir sans chauffe ne doit plus pouvoir rendre un verdict vert

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune (outillage de banc, indépendant du code applicatif)
**Priorité**: **1 — bloquante.** Tant qu'elle n'est pas livrée, **aucune campagne
500 ne produit de latence comparable**, et le rapport peut publier « 8 étapes
vertes sur 11 » sur un tir qui n'a rien mesuré.

## Objective

Que la chauffe du parcours passe à 500 praticiens, et que **si elle échoue quand
même, le rapport refuse le verdict de toutes les étapes servies par la base** —
au lieu de les rendre vertes.

## Ce qui est établi — tir `journey-remote-n500` du 2026-08-09

- La chauffe envoie les **98 UID de la réserve analysée en UNE requête**
  `enrich/sync` (`tests/loadtest-k6/lib/api.js`, délai client **300 s**). Elle a
  expiré pour **500 médecins sur 500**, dès le palier 100.
- Le serveur, lui, **travaillait** : `[CdaParsingService] Parsing completed`
  pendant et après l'abandon du client. Ce n'est pas une panne, c'est un délai.
- Conséquence mesurée par l'instrument de task-243 : base quasi vide, donc
  `GetMailsByUids` à **55,4 ms / 7,8 requêtes par appel** contre **1 199,7 ms /
  14,8** au tir local 200 de la veille. Les latences du tir sont **flattées**.
- Le garde-fou de task-224 a bien refusé l'**étape 3** (« ⛔ étape mal nommée »).
  Il **ne propage pas** ce refus aux étapes 2, 10 et 11, qui sont pourtant
  servies par la même base vide et sont passées **vertes**.

## Ce que la US doit livrer

1. **Une chauffe qui passe** : lotir l'appel (N UID par requête, N à déterminer
   par la mesure, pas par intuition), avec un délai cohérent avec le coût
   unitaire réel.
2. **Un échec de chauffe qui se voit** : compté comme un **refus explicite**
   (une ligne de verdict), pas comme 500 lignes d'erreur noyées dans le log.
3. **La propagation du refus** : si la part de chauffe réussie est sous un seuil,
   **toute étape servie par la base** est rendue non opposable dans le rapport,
   avec la raison écrite. Le même principe que task-224, étendu à sa portée
   logique.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que réduire le lot suffit.** Le `treatment` du parcours réel
  — **2 messages par lot** — a lui aussi expiré une fois au palier 500. Le coût
  unitaire est le sujet ; le lot n'est que le déclencheur. C'est task-245 qui
  l'établira, et cette US **n'attend pas** son résultat pour lotir.
- **Ne pas présumer que le seuil de refus est 100 %.** Une chauffe partiellement
  réussie n'est pas forcément inutilisable — c'est la part servie par la base
  (`warm_served`) qui décide, et le seuil doit être posé et écrit.

## Definition of Done

- [ ] La chauffe est lotie ; un tir 500 en mode distant la termine sans timeout
- [ ] Un échec de chauffe produit **une** ligne de verdict lisible, pas N erreurs
- [ ] Sous le seuil de chauffe servie, le rapport marque **toutes** les étapes
      servies par la base comme non opposables, avec la raison
- [ ] Le seuil retenu est **écrit** dans le rapport et dans `docs/loadtest.md`
- [ ] Tests du harnais : un cas « chauffe échouée → aucune étape base opposable »
      et son **témoin négatif** « chauffe réussie → verdict rendu normalement »
- [ ] `tests/loadtest-k6/selftest.sh` vert, suite Python verte

## Manual Test Plan

- Monter le banc en mode distant : `MSS_LOADTEST_MAIL_HOST=192.168.1.69`
- Tir court (`JOURNEY_STAGES="100:5m"`, K=1) : la chauffe doit se terminer
- Forcer l'échec (délai client abaissé) et régénérer le rapport : vérifier que
  les étapes 2, 3, 10 et 11 portent toutes le refus, pas seulement la 3
- Lire le bandeau de tête : il doit dire que le tir ne mesure pas la capacité

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS) — **Vague** : hors Ségur
- **Exigences DSR honorées** : aucune — outillage de banc, aucun changement fonctionnel
- **INS / Authentification PS / Habilitations / Consentement / Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : non applicable — métriques de banc, données synthétiques
- **Sécurité** : aucun contenu CDA ni identifiant patient dans les journaux du harnais
- **Hébergement HDS** : sans objet (banc de test)
- **AIPD / impact RGPD** : inchangé

## Branches
- `api-mail` (pushed) : feat/task-244-warmup-batched-verdict-gate
- `dtos-mss` (pushed, auto-included) : feat/task-244-warmup-batched-verdict-gate — no DTO change expected

## Develop log

- **api-mail** `feat/task-244-warmup-batched-verdict-gate` @ea06465 — poussé.
- **dtos-mss** — branche créée, **aucun commit** (aucun changement de contrat) → pas de PR.

### Ce qui a été livré

**Harnais (`tests/loadtest-k6/`)**

- `lib/journey-model.js` — `warmupBatches()` (lots d'UID, dernier lot partiel),
  `warmupTimeoutSeconds()` (délai par lot = `lot × 3,5 s × 2`, borné `[60, 300]`),
  constantes `DEFAULT_WARMUP_BATCH=10`, `WARMUP_SECONDS_PER_MESSAGE_AT_LOAD=3.5`.
  `warmupWarnings()` recentré sur le **lot** (l'avertissement sur la réserve
  entière était devenu structurellement vrai, donc inaudible).
- `lib/api.js` — `enrichSync()` prend un `timeoutSeconds` paramétré ; le
  traitement du parcours garde 300 s, la chauffe dimensionne le sien.
- `scenarios/journey.js` — chauffe lotie ; un lot perdu **n'interrompt pas** les
  suivants ; nouveaux témoins `journey_warmup_completed` (Rate, **un échantillon
  par médecin**) et `journey_warmup_batches_failed` (Counter). Pas de `check` par
  médecin : c'est précisément le bruit que la US remplace par une ligne de verdict.
  Env : `JOURNEY_WARMUP_BATCH`, `JOURNEY_WARMUP_TIMEOUT_S`.

**Rapport (`report.py`)**

- `served_by_db: True` sur les étapes **2, 3, 10, 11** de `JOURNEY_SLO_GRID`.
- `warmup_completed_rate()` / `journey_warmup_starved()` — deux témoins, il suffit
  qu'un refuse : chauffe aboutie < `WARMUP_COMPLETED_FLOOR` (**0,90**) **ou**
  ouvertures servies base < `WARM_STORE_SERVED_FLOOR` (0,95, task-224).
- Propagation dans `journey_slo_verdicts()` : toute étape `served_by_db` devient
  non opposable. Les étapes 4 (froide) et 6 (envoi) gardent leur verdict — la
  portée du refus est **logique**, pas maximale.
- `_journey_warmup_verdict_lines()` — **une** ligne de verdict en tête de section,
  dans les trois états (refus / non mesurée / aboutie), jamais confondus.
- L'étape 3 conserve le libellé task-224 (« mesure du froid »), plus précis ; le
  nouveau libellé sert les étapes 2, 10, 11 qui n'avaient **aucun** refus.

**Documentation**

- `docs/loadtest.md` § 4d — cinquième règle de conclusion, avec les **deux seuils
  écrits** (0,90 / 0,95), le pourquoi de 90 % ≠ 100 %, et la contre-épreuve.
- `tests/loadtest-k6/README.md` — les deux nouvelles variables d'environnement.

### Validation

- `tests/loadtest-k6/selftest.sh` : **vert** — 59 tests JS, 249 tests Python.
- Nouveau `test_report_warmup_gate.py` : **12 cas** — refus + portée, **témoin
  négatif** (chauffe réussie → verdict rendu normalement), absence ≠ zéro,
  frontière du seuil dérivée de la constante.
- Aucun fichier C# touché → build .NET inchangé par construction.

### Régression traitée

Le test préexistant `test_the_report_names_the_refusal_before_the_tables` est
tombé : le nouveau libellé de cellule masquait celui de task-224 sur l'étape 3.
Ordre inversé — le diagnostic le plus **précis** gagne. Les deux refusent
également le verdict, seul le libellé diffère.

## Simplify log

- **api-mail** @ad10f5e — 1 findings, axe **réutilisation**.
  `warmup_completed_rate()` et `warm_store_served_rate()` lisaient chacune leur
  Rate k6 à l'identique (10 lignes dupliquées). Factorisées en `sampled_rate()`,
  qui porte désormais **une seule fois** la règle qui compte : une Rate sans
  échantillon vaut `None`, jamais `0 %` — sinon une absence se lit comme un refus
  (task-214). Re-validé : selftest vert (59 JS, 249 Python).
- **dtos-mss** — hors périmètre (porteur de contrat).

## Sonar log

Analyse complète relancée (conteneurs `sonarqube_db` + `sonarqube` redémarrés,
build Release + 5 projets de tests avec couverture OpenCover + scanner).

### KPIs

| Indicateur | Baseline (scan précédent) | Final | Δ |
|---|---|---|---|
| Bugs | 1 | 2 | +1 — **task-242**, pas task-244 (voir provenance) |
| Vulnérabilités | 0 | 0 | 0 |
| Code smells | 44 | 48 | +4 — antérieurs à task-244 |
| Security hotspots | 2 | 4 | +2 — antérieurs |
| Couverture | 87,5 % | 87,6 % | +0,1 |
| Duplication | 0,4 % | 0,4 % | 0 |
| **Quality Gate** | **ERROR** | **ERROR** | inchangé |

Quality Gate : `new_security_hotspots_reviewed` 55,6 % (seuil 100) et
`new_violations` 49 (seuil 0). **Déjà ERROR avant ce tir** — la new-code period
du projet englobe des tasks déjà mergées (piège connu, `reports/INDEX.md`).

### Tests .NET (Release, avec couverture)

3 689 réussis, **0 échec** (domain 136, application 2 086, infrastructure 436,
api 660, integration 371 + 16 ignorés). Les 3 rouges pré-existants connus ne se
sont pas manifestés sur ce tir.

### Provenance des findings — vérifiée fichier par fichier

| Fichier | Issues | Origine |
|---|---|---|
| `test_report_warmup_gate.py` (nouveau) | **0** | — |
| `lib/api.js` | **0** | — |
| `lib/journey-model.test.mjs` | **0** | — |
| `lib/journey-model.js` | 5 | **1 de task-244** (S1940 L461), 4 antérieures |
| `scenarios/journey.js` | 7 | toutes antérieures |
| `report.py` | 19 | toutes antérieures (S3776 **blacklisté** → `/sonar-s3776`) |

**Un seul finding imputable à task-244** : `journey-model.js:461` **S1940**
(« utiliser l'opérateur opposé `<=` »).

### Décision — S1940 refusée, avec justification inline (@32d3844)

`!(batchSize > 0)` et **non** `batchSize <= 0` : `NaN <= 0` vaut **false**, donc
la forme proposée par Sonar **laisserait passer un NaN**. Or `batchSize` vient de
`num('JOURNEY_WARMUP_BATCH', …)`, qui rend NaN sur une variable d'environnement
malformée — la boucle tournerait à vide **en silence**, précisément le mode
d'échec muet que ce harnais existe pour interdire. Idiome déjà présent à trois
sites antérieurs (`parseRange`, `JOURNEY_TIME_COMPRESSION`). Commentaire posé
pour qu'il ne soit pas « corrigé » plus tard.

### ⚠️ Signalé à l'humain, non corrigé (hors périmètre — règle 6)

`tests/loadtest-k6/test_report_pinned_palier.py:68` — **bug S3923** introduit par
**task-242** (`c74120a`, déjà mergée) : `base_hour = 14 if palier == 0 else 14`
rend la même valeur dans les deux branches. Non corrigé ici : le fichier
n'appartient pas à cette US. Mérite une task dédiée.

## PRs

- **api-mail** : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/176 — label `awaiting-human-merge`
- **dtos-mss** : aucun commit (aucun changement de contrat) → **pas de PR**. Branche `feat/task-244-warmup-batched-verdict-gate` créée par `/start`, vide.
- **Staging** : `forge/staging-task-244-252-20260809` (api-mail) — task-244 agrégée.

## Code Review Summary

**APPROVED** — 8 fichiers, 0 blocage, 2 corrections appliquées pendant la review.

| Fichier | Verdict |
|---|---|
| `lib/journey-model.js` | ✅ fonctions pures, testées, bornes explicites |
| `lib/api.js` | ✅ paramètre par défaut = comportement historique préservé |
| `scenarios/journey.js` | ✅ un lot perdu n'interrompt pas les suivants |
| `report.py` | ✅ trois états distingués, propagation bornée aux `served_by_db` |
| `test_report_warmup_gate.py` | ✅ 12 cas dont le témoin négatif et la frontière |
| `lib/journey-model.test.mjs` | ✅ couverture exacte des lots, lot partiel inclus |
| `docs/loadtest.md`, `README.md` | ✅ seuils écrits |

Corrigés en review : commentaire replacé au-dessus de la boucle qu'il décrit
(`c71006a`) ; lecture des Rate k6 factorisée en `sampled_rate()` (`ad10f5e`).

### DOD

| Critère | État |
|---|---|
| Chauffe lotie | ✅ |
| Échec = **une** ligne de verdict | ✅ |
| Refus propagé à **toutes** les étapes servies base | ✅ (2, 3, 10, 11) |
| Seuil écrit (rapport + `docs/loadtest.md`) | ✅ 0,90 / 0,95 |
| Test « chauffe échouée » + **témoin négatif** | ✅ 12 cas |
| `selftest.sh` vert, suite Python verte | ✅ 59 JS / 249 Python |
| **Tir 500 distant sans timeout** | ⏳ **différé au Manual Test Plan** — exige le banc |

Commits : `ea06465` (feat), `ad10f5e` (simplify), `32d3844` (sonar), `c71006a` (review).

## Merged

- **api-mail** : PR #176 squash-mergée sur `develop` — commit **`a87946d`** (2026-08-09).
- Branche distante `feat/task-244-warmup-batched-verdict-gate` supprimée ; **branche locale conservée**.
- **dtos-mss** : branche `feat/task-244-...` restée vide (aucun contrat touché), aucune PR — non supprimée.
- **CI `develop`** : ✅ verte après merge.
- Attestation humaine `--i-tested` fournie le 2026-08-09.

> ⚠️ La validation réelle de cette US **est le prochain tir 500** : son Manual Test
> Plan exige un banc, et le tir a besoin d'elle (elle ne touche aucun code de
> production — uniquement `tests/loadtest-k6/` et `docs/`). À lire dans le rapport :
> le **bandeau de chauffe** doit refuser les étapes 2/3/10/11 si la chauffe échoue.
