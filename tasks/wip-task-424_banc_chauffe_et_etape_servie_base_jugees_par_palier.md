# todo-task-424.md — Banc de charge : la chauffe et l'étape « servie base » jugées palier par palier

**Repos**: api-mail
**Dependencies**: — (aucune)
**Epic**: E015
**Single frontend**: true
**Priorité**: **2**. Outillage du banc. Tant que ce n'est pas corrigé, un escalier qui trouve sa limite rend
**non probants** les paliers sains qui la précèdent, c'est-à-dire précisément ceux qu'il faut lire.

> **Origine.** Campagne « limites » du 2026-11-05, itération 1 (escalier `journey`, IA simulée). Rapport :
> `Api/Mail/tests/loadtest-k6/reports/2026-11-05/report-journey-escalier-1996-20261104-ia-simulee-013324.md`,
> finding **F4**.

## Ce qui est établi

- Le rapport marque « ⛔ non opposable — chauffe insuffisante » les étapes 2, 3, 10 et 11 de **tous** les paliers,
  200 à 1996, parce que la chauffe a abouti pour **88,3 %** des médecins (plancher 90 %).
- Les 666 chauffes échouées datent **toutes** de l'effondrement du palier 1400 : 1 à 00:56, 133 à 00:57, puis
  617 entre 01:14 et 01:16, au début du palier 1996 (journal k6 `k6-log-k6-journey-20261104-234134.txt`). Aux
  paliers 200 à 1000, la chauffe avait réussi.
- Même défaut pour l'étape 3 « servie base » : la part de 91,0 % (plancher 95 %) est calculée sur tout le tir.
  Elle mélange les paliers sains et les paliers où la base refusait les connexions.
- Cause dans le harnais : `journey_warmup_completed` et `journey_warm_served_from_store`
  (`Api/Mail/tests/loadtest-k6/scenarios/journey.js`) ne sont pas ventilés par palier.
  `journey_warmup_starved` et `journey_step_mislabelled` (`Api/Mail/tests/loadtest-k6/report.py`) les lisent
  donc tous paliers confondus, et appliquent le même verdict à chaque palier.

## Objective

Que chaque palier soit jugé sur **sa** chauffe et **sa** part servie par la base. Un palier qui s'effondre perd
ses verdicts ; ceux qui le précèdent gardent les leurs.

Règles :
- **La chauffe d'un palier** est celle de sa cohorte : les médecins qui arrivent à ce palier. Le plancher de
  90 % s'applique par cohorte.
- **Un palier dont la cohorte a réussi sa chauffe** garde ses verdicts sur les étapes 2, 10 et 11, même si un
  palier suivant échoue. Les médecins des cohortes précédentes, déjà chauffés, restent servis par la base.
- **L'étape 3** est jugée sur la part servie par la base **pendant la fenêtre de régime du palier**.
- **Un tir sans ventilation** (harnais antérieur, métrique absente) garde le verdict global d'aujourd'hui, et le
  rapport le dit, comme pour les autres métriques absentes : « on ne sait pas », jamais 0.
- **Rien ne s'assouplit** : le plancher de 90 % et celui de 95 % sont inchangés.

## Definition of Done

- [ ] `journey.js` étiquette `journey_warmup_completed` par cohorte de palier et `journey_warm_served_from_store`
      par palier, et déclare les seuils `>= 0` nécessaires pour que k6 exporte ces sous-métriques dans le résumé
      JSON
- [ ] `report.py` juge la chauffe et l'étape 3 palier par palier. Le verdict global reste le repli quand les
      sous-métriques sont absentes, et le rapport le dit
- [ ] Le bandeau « Chauffe insuffisante » et la ligne « Étape 3 refusée » nomment le ou les paliers touchés, avec
      leurs chiffres, au lieu d'un chiffre global
- [ ] Tests Python (`tests/loadtest-k6/test_report_warmup_gate.py` ou voisin) : ≥ 1 test par branche
      - paliers sains suivis d'un palier en échec : les paliers sains gardent leurs verdicts ;
      - échec de chauffe au premier palier : tous les paliers suivants qui en dépendent sont non opposables ;
      - sous-métriques absentes : verdict global, et mention « on ne sait pas » ;
      - étape 3 sous 95 % sur un seul palier : seul ce palier est refusé.
- [ ] Preuve par mutation consignée dans le `## Develop log` : réintroduire le jugement global fait échouer le
      premier test. Pendant la preuve, effacer le `__pycache__` ou lancer `python -B` : un `.pyc` de même taille
      et de même seconde survit à la restauration
- [ ] Tests du harnais JS verts (`node --test` sur `lib/*.test.mjs`). Toute fonction pure ajoutée dans `lib/`
      pour la ventilation a son test
- [ ] Rapport de l'escalier du 2026-11-05 **régénéré** depuis son JSON existant, sans nouveau tir. Il garde le
      verdict global (le JSON ne porte pas encore les sous-métriques) et le dit explicitement. Le task file cite
      ce passage du rapport régénéré
- [ ] Un tir court de contrôle, 2 paliers de 3 min à K = 10, IA simulée, montre les sous-métriques par palier dans
      le JSON et les verdicts par palier dans le rapport. Rapport relié dans le task file
- [ ] `tests/loadtest-k6/README.md` et `.claude/skills/loadtest-skill/SKILL.md` décrivent le jugement par palier
- [ ] Aucun changement du code de l'API (`Api/Mail/src`) : la task ne touche que `Api/Mail/tests/loadtest-k6/` et
      la documentation du banc
- [ ] Aucune donnée de santé : le banc n'emploie que des données synthétiques

## Manual Test Plan

1. **Tests** : depuis `Api/Mail/tests/loadtest-k6`, `python -B -m unittest discover -p "test_report*.py"` puis
   `node --test lib/`. Tout est vert.
2. **Rapport existant** : `VERIFY_MAX_USERS=2000 tests/loadtest-k6/report.sh tests/loadtest-k6/reports/2026-11-05/journey-escalier-1996-20261104-ia-simulee-013324.json`
   depuis `Api/Mail`. Le rapport dit que la ventilation par palier n'est pas disponible pour ce tir et garde le
   verdict global.
3. **Tir de contrôle** (skill `loadtest-skill`, banc lancé avec `MSS_LOADTEST_AI=fake`) :
   `JOURNEY_STAGES="20:3m,40:3m" JOURNEY_TIME_COMPRESSION=10 JOURNEY_WARMUP_HYDRATED=1`, scénario `journey`.
   Dans le rapport, chaque palier porte sa propre ligne de chauffe et sa propre part servie par la base.
4. **Cas d'échec** : relancer le même tir avec `JOURNEY_WARMUP_TIMEOUT_S=1` sur le second palier seulement, ou
   tout autre moyen documenté de faire échouer la chauffe d'une cohorte. Seul le second palier est marqué non
   opposable.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir. Outillage de mesure interne
- **Vague Ségur** : hors Ségur. Aucun comportement du produit ne change
- **Exigences DSR honorées** : non applicable. Outillage de test
- **INS** : non applicable. Données synthétiques uniquement
- **Authentification PS** : non applicable. Le banc emploie le contournement de test du profil `loadtest`, inchangé
- **Habilitations** : non applicable
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : non applicable. Aucun évènement de l'application n'est ajouté ni retiré
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non. Banc local, données synthétiques
- **AIPD / impact RGPD** : inchangé, aucun traitement nouveau

## Develop log

- **Harnais k6** (`tests/loadtest-k6/scenarios/journey.js`, `lib/journey-model.js`) :
  - `warmupCohortPalier(vuIndex, paliers)`, fonction pure : le palier où un médecin arrive, `null` hors plan
    (2 tests `node --test`) ;
  - `journey_warmup_completed` étiqueté `{cohort:N}`, `journey_warm_served_from_store` étiqueté `{palier:N}` (le palier
    de la requête : `chauffe` et `transition` n'entrent dans aucun verdict) ;
  - seuils `rate>=0` par palier pour que k6 exporte ces sous-métriques. Vérifié par `k6 inspect` et dans le JSON du
    tir de contrôle.
- **Rapport** (`tests/loadtest-k6/report.py`) :
  - `journey_palier_gates` juge chaque palier. Sa population est sa cohorte et les cohortes d'avant : une cohorte
    sous 90 % refuse son palier et les suivants. L'étape 3 se juge sur la part servie par la base pendant le régime
    du palier. Un palier sans mesure est « non vérifié », jamais un zéro ;
  - sans sous-métriques, chaque palier reçoit le verdict global, et le rapport l'écrit : « Ventilation par palier
    non disponible… palier par palier, **on ne sait pas** lequel a échoué » ;
  - les bandeaux « Chauffe insuffisante » et « Étape 3 « servi base » refusée » nomment les paliers touchés, avec
    leur part et leur effectif, et ceux qui gardent leurs verdicts. Quand tout tient, une ligne par palier ;
  - planchers inchangés (90 %, 95 %).
- **Écart de conception, constaté au tir de contrôle et corrigé** : à K ≠ 1, la section « Verdict SLO » s'arrêtait
  sur « non opposable » avant tout bandeau de chauffe. Le tir de contrôle à K = 10 exigé par la DoD n'aurait donc
  montré aucun verdict par palier. Les bandeaux de la base sont désormais écrits **à tout K** : l'état de la base ne
  dépend pas de la compression, et un tir de découverte qui désigne des goulets sur une base mal peuplée doit le dire.
  Le verdict SLO, lui, reste réservé à K = 1. Effet de bord assumé : la synthèse d'un tir K > 1 cite désormais une
  étape 3 refusée.
- **Tests Python** (`test_report_warmup_by_palier.py`, 9 tests) : paliers sains suivis d'un palier en échec, bandeau
  qui nomme le palier, échec au premier palier qui refuse les suivants, tir sain (une ligne par palier), étape 3 sous
  95 % sur un seul palier, palier sans ouverture mesurée, tir sans ventilation, bandeaux à K = 10.
- **Preuve par mutation** (`python -B`, `__pycache__` effacé avant chaque passage, fichier restauré et comparé par
  `cmp`), rejouée sur la version finale :

  | Mutation | Tests qui échouent |
  |---|---|
  | M1, chauffe jugée globalement (`starved = out["warmup_starved"]`) | `test_les_paliers_sains_gardent_leurs_verdicts_quand_un_palier_suivant_echoue` (le premier), + 2 |
  | M2, étape 3 jugée globalement | `test_etape_3_sous_95_sur_un_seul_palier_seul_ce_palier_est_refuse`, `test_un_palier_sans_ouverture_mesuree_n_est_pas_un_zero` |
  | M3, cohortes d'avant oubliées (`cohorts[-1:]`) | `test_echec_au_premier_palier_rend_non_opposables_les_paliers_qui_suivent` |
  | M4, bandeaux absents à K > 1 | `test_a_k10_le_bandeau_de_chauffe_par_palier_est_ecrit` |
- **Passe qualité §Q** (`/simplify`, 4 relectures) :
  - **appliqué** : `journey_warmup_starved` / `journey_step_mislabelled` réécrits sur les mêmes helpers que le
    jugement par palier (une seule source de la règle des trois états) ; une seule liste de cohortes par palier
    (`failed_cohorts` dérivé à la lecture) ; refus de chauffe par `_either_refuses` ; repli global porté par une
    pseudo-cohorte « tout le tir » (plus de raison vide si seule l'étape 3 était ventilée) ; causes connues de l'étape
    3 écrites une fois et citées aussi par le bandeau par palier (elles y manquaient) ; `kept_note` en bloc simple ;
    `PALIER_TARGETS` dans `journey.js` ; fixture `metrics_with_warmup` réutilisée.
  - **écarté** : un seul moteur de rendu pour les tirs ventilés et anciens (changerait le texte des rapports déjà
    publiés et les tests de task-244) ; fusion de `warmupCohortPalier` et `warmupCohortRank` (comportements hors plan
    différents, `null` contre rang brut) ; double appel préexistant de `journey_slo_verdicts` (coût négligeable).
- **Validation** : `node --test lib/*.test.mjs` 133/133. Python 417 tests, **1 échec préexistant hors périmètre** :
  `test_dashboards.test_every_queried_panel_says_when_it_has_no_data`, rouge à l'identique sur `develop` (panneaux
  sans `noValue` du tableau de bord `mssante-ai-consumption.json`, task-385). Non corrigé ici.
  - Le Manual Test Plan écrit `node --test lib/` : sur le Node du poste, cette forme ne lance aucun test.
    `node --test lib/*.test.mjs` (la forme de `selftest.sh`) est la bonne.
- **Rapport de l'escalier du 2026-11-05 régénéré** depuis son JSON, sans nouveau tir, avec les mêmes entrées
  (Prometheus encore servi, `observe-233500.csv`, `pgstats-journey-013350.tsv`, photos `fin`). Seule la section
  « Verdict SLO » diffère du rapport d'origine. Elle a été reportée dans le rapport du tir et dans sa copie
  versionnée `Docs/audits/api-mail-loadtest-journey-escalier-ia-simulee-20261105.md`. Le reste est inchangé :
  l'analyse écrite à la main après le tir ne se régénère pas. Passage cité :

  > ⓘ **Ventilation par palier non disponible pour ce tir** (harnais antérieur à task-424) : la chauffe et la part
  > servie par la base sont jugées sur tout le tir, et ce verdict global s'applique à chaque palier. Palier par
  > palier, **on ne sait pas** lequel a échoué.

  Le bandeau global « Chauffe insuffisante… 88.3 % » est conservé au-dessus.
- **Tir de contrôle** (2026-11-06, 10:05 → 10:13, poste local, IA simulée, `JOURNEY_STAGES="20:3m,40:3m"`,
  `JOURNEY_TIME_COMPRESSION=10`, `JOURNEY_WARMUP_HYDRATED=1`) : rapport
  `Docs/audits/api-mail-loadtest-journey-controle-20-40-task424-20261106.md`.
  - JSON : `journey_warmup_completed{cohort:20}` 20/20, `{cohort:40}` 20/20 ;
    `journey_warm_served_from_store{palier:20}` 99,2 % (361), `{palier:40}` 99,2 % (749).
  - Rapport : « ✅ Chauffe aboutie à chaque palier mesuré », puis une ligne par palier (cohorte, part servie par la
    base). 0 erreur, vérification par base PASS.
  - Le cas d'échec (Manual Test Plan, étape 4) n'a pas été joué au banc : il est couvert par les tests M1 et M3.

## Branches

- `api-mail` (pushed) : feat/task-424-banc-chauffe-et-etape-servie-base-jugees — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-424-banc-chauffe-et-etape-servie-base-jugees
  - Créée depuis `origin/develop` (`6e43b6f8`).

## Timings

*(généré par `tools/timing/report.sh --task task-424 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 13 s | — | — | — | — |
| /develop | ok | 29 min 44 s | — | 1 (9.9 s) | — | api-mail 0B/1T, report.py par palier, harnais ventilé, tir de contrôle K=10 |
| **Total cycle** | | **29 min 58 s** | **0 (0.0 s)** | **1 (9.9 s)** | **0 (0.0 s)** | |
