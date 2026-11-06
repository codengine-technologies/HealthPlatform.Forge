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

## Sonar log

- **Mode A (chaîné)**, `api-mail` sur `feat/task-424-banc-chauffe-et-etape-servie-base-jugees`, 1 itération.
- **Portée réelle de l'analyse** : la task ne change que le harnais de charge (Python et JS de `tests/loadtest-k6/`)
  et de la documentation. L'analyse .NET n'indexe aucun de ces fichiers : 0 fichier `loadtest-k6` dans le projet
  Sonar. Elle confirme donc seulement que le code C# n'a pas bougé. La qualité du harnais repose sur ses tests
  (`selftest.sh`) et sur la revue.
- **Résultat** : 0 issue sur le nouveau code, Quality Gate OK, 0 hotspot. Rien à corriger.
- **Tests sous couverture** : domain 202, application 4 003, infrastructure 700, api 1 357, intégration 1 114
  (+16 ignorés), **0 échec**.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | = |
| Issues new code | 0 | 0 | = |
| New coverage | 96,0 % | 96,0 % | = |
| Bugs / Vulnérabilités / Code smells | 0 / 0 / 0 | 0 / 0 / 0 | = |
| Security hotspots | 0 | 0 | = |
| Coverage projet | 97,8 % | 97,8 % | = |
| Duplication | 0,4 % | 0,4 % | = |
| Ratings fiabilité / sécurité / maintenabilité | A / A / A | A / A / A | = |

## Lint log

- `/lint-angular` : **skipped** — `client-angular` n'est pas dans les `**Repos**` de la task.
- `/lint-mobile` : **skipped** — `client-mobile` n'est pas dans les `**Repos**` de la task.

## E2E log

| Voie | Déclenchée par | Résultat |
|---|---|---|
| mobile (`npm run e2e:headless`) | `api-mail` touché | ✅ 58 verts, 0 flaky, 0 rouge, parité verte |
| angular (`npm run e2e:mss`) | `api-mail` touché | ✅ 71 verts, 0 flaky, 0 rouge, parité verte (port 47399 vérifié libre avant la voie) |

La task ne touche que le harnais de charge et sa documentation : aucun code joué par ces parcours n'a changé. Les deux
voies sont rejouées parce que `api-mail` est dans les `**Repos**` (règle de `agents/e2e.md`).

**Porte** (`mss.mail.e2e gate`, catalogue `Api/Mail/e2e/scenarios.yml` inchangé face à `origin/develop`) :

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-PATIENT-003 | 1 | headless | La fiche d'un patient ne montre pas les documents d'un autre patient du même mail | ✅ | ✅ |
| E2E-PATIENT-004 | 1 | headless | La vue « Mails du patient » reste ouverte et ses pages viennent du serveur | ✅ | — |
| E2E-CONTACT-001 | 2 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Écrire à l'adresse choisie d'un contact à plusieurs adresses, ou à son adresse par défaut | ✅ | ✅ |
| E2E-COMPOSE-005 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-MAIL-006 | 1 | headless | Glisser sur la Corbeille un message d'un fil supprime ce message, et lui seul | ✅ | — |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-DRAFT-004 | 1 | headless | Une rédaction sans texte dans le corps ne laisse ni brouillon ni question | ✅ | ✅ |
| E2E-BIO-001 | 2 | headless | Acquitter un compte rendu de biologie, à son nom | ✅ | ✅ |
| E2E-BIO-002 | 1 | headless | La puce « Bio à acquitter » montre tous les résultats en attente, sur toutes les pages | ✅ | ✅ |
| E2E-BIO-003 | 1 | headless | Lire un résultat HPRIM puis l'acquitter | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SETTINGS-004 | 1 | headless | Paramètres indisponibles : rien n'est écrasé | ✅ | — |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 2 | headless | Créer un contact à deux adresses, le modifier sans les perdre, puis le supprimer | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-CONTACT-004 | 1 | headless | Consulter un contact depuis le carnet et lui écrire | ✅ | ✅ |
| E2E-CONTACT-005 | 1 | headless | Une fiche modifiée ne se perd pas sans confirmation, une adresse mal formée est refusée | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 2 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ | ✅ |
| E2E-MAILBOX-003 | 2 | headless | Rattacher ses boîtes depuis « Mes boîtes » en un geste — titulaire et membre | ✅ | ✅ |
| E2E-MAILBOX-006 | 1 | headless | Après le rattachement, l'identité d'expéditeur et la signature sont déjà là | ✅ | ✅ |
| E2E-MAILBOX-004 | 1 | headless | Ajouter une BAL déléguée par saisie — et refus de sa propre adresse | ✅ | ✅ |
| E2E-MAILBOX-005 | 1 | headless | Le délégataire refusé par l'opérateur perd l'accès, en ligne puis hors ligne ; le titulaire garde le sien | ✅ | ✅ |
| E2E-AUDIT-001 | 1 | headless | Le titulaire lit au journal le message supprimé par son délégataire, au nom du délégataire | ✅ | — |
| E2E-AUDIT-002 | 1 | headless | Le journal d'audit montre chaque action sur un mail | ✅ | — |
| E2E-SHARED-001 | 1 | headless | Une boîte partagée, une base — le patient rattaché par le titulaire est vu du délégataire, la signature reste à chacun | ✅ | ✅ |
| E2E-SHARED-002 | 1 | headless | Le délégataire écrit pour le compte du titulaire — le destinataire voit qui a écrit, sa réponse revient à la boîte | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |
| E2E-SESSION-004 | 1 | headless | Sur un appareil partagé, la personne suivante n'arrive jamais dans la boîte de la précédente | ✅ | ✅ |
| E2E-AI-002 | 1 | headless | Un délégataire interroge l'assistant dans la boîte qu'il a ouverte | ✅ | ✅ |
| E2E-MAILBOX-007 | 1 | headless | Après un changement de boîte, l'onglet Patients ne montre plus rien de la précédente | ✅ | ✅ |
| E2E-ERROR-001 | 1 | headless | Une erreur affiche un code et une référence à transmettre au support | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

- Démontage vérifié : port 47399 libre, aucun conteneur e2e laissé par ce run.

## Branches

- `api-mail` (pushed) : feat/task-424-banc-chauffe-et-etape-servie-base-jugees — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-424-banc-chauffe-et-etape-servie-base-jugees
  - Créée depuis `origin/develop` (`6e43b6f8`).

## Timings

*(généré par `tools/timing/report.sh --task task-424 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 13 s | — | — | — | — |
| /develop | ok | 29 min 44 s | — | 1 (9.9 s) | — | api-mail 0B/1T, report.py par palier, harnais ventilé, tir de contrôle K=10 |
| /sonar | ok | 10 min 38 s | 1 (51 s) | 5 (7 min 56 s) | 2 (47 s) | 1 itération(s), api-mail 1B/5T, QG OK, 0 issue ; harnais Python/JS non indexé |
| /lint-angular | skipped | 0.5 s | — | — | — | repo non listé dans Repos |
| /lint-mobile | skipped | 0.5 s | — | — | — | repo non listé dans Repos |
| /e2e | ok | 19 min 36 s | — | — | — | e2e ×3 (19 min 03 s), mobile 58, angular 71, parité verte |
| **Total cycle** | | **1 h 00 min** | **1 (51 s)** | **6 (8 min 06 s)** | **2 (47 s)** | |
