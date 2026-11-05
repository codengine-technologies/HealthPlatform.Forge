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
