# todo-task-321.md — Le banc mesure des praticiens inscrits, pas des VUs en boucle : scénario `terrain` (absence → session → geste), profils de médecins, concurrence émergente

**Repos**: api-mail
**Dependencies**: — (aucune ; `task-254` reste distincte, voir « Frontière avec task-254 »)
**Epic**: E015
**Priorité**: **2** — sans lui, tout verdict de capacité en « N praticiens » désigne une charge, pas une population, et le plan de montée en charge se décide sur un chiffre qui n'a pas d'unité terrain.

> **Origine** : tir `journey-1000-hydrate-20260917`, premier palier 1000 sur population
> entièrement hydratée. Rapport : `Docs/audits/api-mail-loadtest-journey-1000-hydrate-20260917.md`.
> Le rythme réellement injecté a été **mesuré** : un passage complet toutes les
> **87 s** par médecin, **8,2 requêtes/minute**, pour **1 000 médecins tous actifs
> en même temps, sans interruption, pendant 3 h 30**. Soit 41 ouvertures de
> messagerie par heure et par praticien. Ce n'est pas un rythme de médecin, c'est un
> rythme de robot.

## Objective

Que le banc réponde à la question produit — **« combien de praticiens inscrits
peut-on servir ? »** — au lieu de la question qu'il pose aujourd'hui — « tient-on
N praticiens simultanément actifs en boucle ? » — qui n'a pas d'équivalent terrain.

Un médecin **n'est pas dans sa messagerie**. Il consulte. Il ouvre la messagerie
quelques fois par jour, y passe quelques minutes selon ce qu'il y trouve, et
repart pour une demi-heure, une heure, deux heures. Ce que le banc doit modéliser,
c'est **cette absence**, qui domine tout, et **la variabilité entre praticiens** :
un occasionnel qui regarde deux fois par jour, un intensif qui trie dix fois.

Le modèle actuel (`journey`) a déjà la bonne granularité **au niveau du geste** :
le temps de lire un message (5-30 s), de rédiger (30-120 s), de consulter un
dossier (10-60 s) est modélisé et tiré d'une log-normale. Il ne manque **rien à
cette couche**. Ce qui manque, c'est la couche au-dessus : le VU enchaîne les
passages en boucle sans jamais quitter la messagerie. Cette US ajoute cette couche.
Elle ne touche pas aux gestes.

### Ce que ça change dans ce qu'on mesure

Avec ce modèle, **N VUs redevient « N praticiens inscrits »**, et la concurrence
réelle **émerge** du modèle au lieu d'être fixée à 100 % : à un instant donné, une
fraction seulement des inscrits est en session. La grille SLO par geste
(`docs/SLO-parcours-medecin.md`) **reste identique** — on ne change pas ce qu'on
juge, on change **qui frappe à la porte, et quand**.

Deux grandeurs nouvelles doivent être publiées, sans quoi le verdict n'a pas
d'unité : la **concurrence active moyenne** (praticiens en session à un instant
donné) et les **sessions par praticien et par heure**.

### Le modèle — trois couches, du plus lent au plus rapide

| Couche | Ce qu'elle modélise | Existe ? | Cette US |
|---|---|---|---|
| **Absence** | le praticien n'est pas dans la messagerie (il consulte) | non | log-normale, **dominante** — c'est elle qui fait le rythme |
| **Session** | il ouvre la messagerie et fait 1 à N passages, le temps qu'il a devant lui | non | durée de session log-normale ; les passages s'enchaînent tant qu'elle n'est pas épuisée (au moins un) |
| **Geste** | dashboard, lecture, rédaction, dossier… | ✅ `JOURNEY_THINK_*` | **inchangé** |

Et des **profils de praticiens**, tirés **de façon déterministe depuis l'index du
VU** (un tir est rejouable ; deux tirs à mêmes paramètres ont la même population) :

| Profil | Part | Sessions / journée | Durée moyenne de session |
|---|---|---|---|
| `occasionnel` | 30 % | 2 | 3 min |
| `regulier` | 50 % | 5 | 6 min |
| `intensif` | 20 % | 10 | 12 min |

L'absence moyenne d'un profil se **déduit** : `journée ÷ sessions − durée de session`
(journée par défaut : 8 h). Un `regulier` s'absente donc ~90 min entre deux sessions.

> ⚠️ **Ces valeurs sont construites par cohérence, pas mesurées.** Une journée de
> médecine générale, c'est ~25 consultations de 15-20 min ; 5 sessions de 6 min,
> c'est déjà un praticien qui s'occupe sérieusement de sa messagerie. Elles sont
> documentées **comme hypothèses** dans le code et dans le rapport, et
> **surchargeables** (`TERRAIN_PROFILES`, `TERRAIN_DAY_HOURS`). Elles ne sont pas
> une décision produit gravée : elles sont la valeur d'attente en attendant la
> mesure (voir « Calibration »).

### Calibration — la sortie de l'hypothèse est déjà instrumentée

Le journal d'audit de la plateforme (`audit_traces`, task-300/301) porte
**exactement** les grandeurs de ce modèle, par praticien et horodatées :
`MailboxSessionOpened` (début de session), `MailRead`, `MailSend`,
`AttachmentDownload` (contenu de la session), et le silence entre deux (absence).

Le jour où l'audit tourne en production, une requête sur ce journal remplace les
trois profils inventés par les profils **observés**. Le scénario doit donc être
écrit pour que **ses paramètres soient directement ces distributions** : sessions
par jour, durée de session, part de chaque profil. C'est une exigence de forme
sur `TERRAIN_PROFILES`, pas une fonctionnalité de plus.

### Ce que le modèle fermé implique — à écrire dans le rapport

Le modèle reste **fermé** (1 VU = 1 praticien). Conséquence, déjà mesurée sur
`journey` : **la lenteur du serveur réduit la charge injectée** (28 s d'attente
serveur sur un passage de 87 s au tir du 17/09 ; sur un serveur sain, le même
modèle aurait produit 40 % de passages en plus). Le rapport doit publier **le
rythme obtenu** (passages/h/praticien, sessions/h/praticien) à côté du rythme
**attendu par le modèle**, pour que l'écart soit lisible.

### La chauffe sur population hydratée — ce qui a coûté 78 % du tir

La chauffe alloue sa fenêtre et étale ses vagues **a priori**, sur un débit
d'analyse plafond de **9,5 messages/s** (`WARMUP_THROUGHPUT_MESSAGES_PER_SECOND`,
task-253/264) et **8 médecins simultanés**. Ces constantes décrivent une
population **froide**, dont chaque message doit être analysé. Sur une population
**déjà hydratée**, l'analyse court-circuite en **~25 ms par lot** (mesuré le
17/09 : 106 130 UIDs sur 118 270 déjà analysés) — et l'allocation reste celle
d'une population froide : **9 807 s de chauffe pour 12 018 messages réellement
analysés**, 78 % de la fenêtre, attente de vague comprise.

Cette US ajoute une **déclaration de population hydratée** (`JOURNEY_WARMUP_HYDRATED=1`) :
la chauffe devient une **vérification** et non une préparation — concurrence non
bornée par le plafond d'analyse, allocation et vagues dérivées du coût du
court-circuit. Le rapport **dit** que la chauffe a tourné en mode hydraté. Sans
cette déclaration, le comportement actuel est **inchangé**.

### Frontière avec task-254

`task-254` relève le **portillon de concurrence de l'analyse réelle** (une
population froide qui doit être analysée). Cette US ne le touche pas : elle ne
fait que **cesser d'appliquer ce portillon à une population qui n'en a pas besoin**.
Les deux sont complémentaires, aucune n'inclut l'autre.

### Un défaut de restitution, corrigé au passage

Le rapport du 17/09 annonce **24,66 req/s** pour le palier 1000. C'est
`310 766 ÷ 12 600` — les requêtes du **régime** divisées par la fenêtre **totale**,
chauffe comprise, alors que `palierAt` garantit qu'aucune requête taguée
`palier:N` n'a lieu pendant la chauffe. Le débit réel du régime est **136 req/s**.
`report.py` doit diviser par la **fenêtre de régime** (`holdEndS − warmupEndS`).
Ce n'est pas anecdotique pour cette US : c'est le chiffre qui, rapporté aux
inscrits, donne le coût d'un praticien.

## Gherkin

```gherkin
Fonctionnalité : le banc mesure des praticiens inscrits

  Scénario : un praticien s'absente entre deux sessions
    Étant donné un praticien de profil « regulier »
    Quand sa session de messagerie se termine
    Alors il ne fait aucune requête pendant une absence tirée autour de 90 minutes
    Et sa session suivante commence par l'arrivée sur le dashboard

  Scénario : la population est hétérogène et rejouable
    Étant donné 1 000 praticiens inscrits
    Quand le tir démarre
    Alors environ 300 sont occasionnels, 500 réguliers et 200 intensifs
    Et le même tir relancé attribue le même profil au même praticien

  Scénario : la concurrence active émerge du modèle
    Étant donné 1 000 praticiens inscrits et les profils par défaut
    Quand le tir est en régime
    Alors le rapport publie la concurrence active moyenne
    Et cette valeur est très inférieure à 1 000

  Scénario : la chauffe d'une population hydratée ne prend pas le temps d'une analyse
    Étant donné une population dont toutes les boîtes sont déjà analysées
    Et la déclaration « population hydratée »
    Quand la chauffe s'exécute
    Alors elle ne consomme qu'une petite part de la fenêtre du palier
    Et le rapport indique que la chauffe a tourné en mode hydraté

  Scénario : le budget de campagne tient compte de l'absence
    Étant donné un tir terrain de 3 heures à 1 000 praticiens
    Quand le contrôle de budget s'exécute
    Alors il n'exige pas les réserves d'un praticien qui ferait 41 passages par heure
    Et le tir est accepté avec les réserves d'un seed standard

  Scénario : le débit d'un palier est rapporté à sa fenêtre de régime
    Étant donné un palier dont la chauffe a consommé une partie de la fenêtre
    Quand le rapport calcule le débit émergent du palier
    Alors il divise les requêtes du palier par la seule fenêtre de régime
```

## Definition of Done

### Modèle (`tests/loadtest-k6/lib/`)
- [ ] Un module pur `terrain-model.js` (importable par `node --test`) porte : le parseur de `TERRAIN_PROFILES` (`nom:part:sessions_par_jour:minutes_de_session,…`, parts sommant à 1 ± 0,01, refus franc sinon), l'attribution déterministe du profil depuis l'index de VU (respecte les parts sur une population de 1 000 à ± 2 %), le tirage log-normal de l'absence et de la durée de session (bornés, jamais négatifs, `K` ne les divise **pas** — K comprime la réflexion dans un geste, pas la journée du médecin), et `expectedTerrainIterationSeconds` (passage moyen **absence comprise**, pondéré par les profils).
- [ ] Tests `terrain-model.test.mjs` : parseur (nominal, parts fausses, profil illisible), déterminisme de l'attribution (deux appels, même résultat), respect des parts, bornes des tirages, valeur attendue du passage moyen (cas calculable à la main), et **le contrôle de budget accepte** un tir 1000 × 3 h aux réserves du seed standard (`MESSAGES_PER_USER=247`).
- [ ] `checkBudgets` reçoit le passage moyen **terrain** quand le modèle est actif : `iterationsPerDoctor` chute d'un facteur ≥ 10 par rapport à `journey` aux mêmes paramètres, et un test le prouve.

### Scénario (`tests/loadtest-k6/scenarios/`)
- [ ] `run.sh terrain` est une commande valide ; elle active le modèle de session sur le parcours `journey` existant (**les gestes et leurs tags `op`/`call`/`palier` sont inchangés** — la grille SLO et `report.py` continuent de les lire).
- [ ] La boucle d'un VU devient : `absence → session (≥ 1 passage, tant que la durée tirée n'est pas épuisée) → absence …` ; la **première** action d'un VU est une absence tirée **sur [0, absence moyenne]** (les praticiens n'arrivent pas tous à la seconde 0 — sinon la première session est une rafale de 1 000 dashboards qui n'existe pas sur le terrain).
- [ ] Métriques k6 nouvelles, taguées `palier` : `terrain_session_seconds` (Trend), `terrain_absence_seconds` (Trend), `terrain_sessions` (Counter), `terrain_passages_per_session` (Trend) ; et un tag `profile` sur `terrain_session_seconds` **uniquement** (3 valeurs littérales, cardinalité bornée — jamais sur `http_req_duration`).
- [ ] La chauffe est **inchangée** dans son principe (préalable, taguée `chauffe`, hors verdict) et s'exécute au **premier passage de la première session** ; `JOURNEY_WARMUP_HYDRATED=1` substitue au débit plafond d'analyse un coût de court-circuit (constante documentée, ≈ 25 ms/lot, source : tir du 17/09) pour **l'allocation** (`warmupWindowSeconds`) **et les vagues** (`warmupWaveDelaySeconds`), et lève le plafond de concurrence à la cohorte entière ; sans la variable, **rien ne change** (test : mêmes valeurs qu'aujourd'hui).
- [ ] Le contexte archivé avec le tir (`handleSummary`) porte `sessionModel: 'terrain'`, les profils effectifs, `dayHours`, et `warmupHydrated`.
- [ ] Un tir `journey` classique (sans `terrain`) produit **exactement** le même comportement qu'avant cette US : aucune absence, aucune métrique `terrain_*`, contexte sans `sessionModel`.

### Rapport (`tests/loadtest-k6/report.py`)
- [ ] `report.py` reconnaît la famille `terrain` (`ctx.sessionModel == 'terrain'`) et publie une section **« Terrain — praticiens inscrits, concurrence active »** : profils et parts effectives, **concurrence active moyenne** (= Σ `terrain_session_seconds` du palier ÷ fenêtre de régime, en praticiens), **sessions par praticien et par heure** (obtenu **et** attendu par le modèle), **passages par praticien et par heure** (obtenu et attendu), absence moyenne obtenue.
- [ ] Le verdict SLO de la famille `terrain` est titré « **N praticiens inscrits — M actifs en moyenne** », jamais « N médecins » seul.
- [ ] `reports/INDEX.md` : `terrain` est une **famille distincte**, non comparable à `journey` (même principe que `journey` vis-à-vis de `mixed`) ; la ligne d'INDEX porte la concurrence active moyenne.
- [ ] **Débit émergent du palier** : divisé par la fenêtre de **régime** (`holdEndS − warmupEndS`), plus par la fenêtre totale. Un test Python (ou un cas de `journey-model.test.mjs` si le calcul est côté JS) reproduit le cas du 17/09 : `310 766` requêtes, fenêtre 12 600 s, chauffe 10 316 s → **136 req/s**, pas 24,66.
- [ ] Quand `warmupHydrated` est vrai, le rapport l'écrit en une ligne dans « Coût de la chauffe ».

### Documentation
- [ ] `docs/SLO-parcours-medecin.md` : nouvelle section « **Mode terrain** » — N désigne des **inscrits**, le verdict est publié avec la concurrence active, les profils par défaut sont des **hypothèses** et leur source de calibration est `audit_traces` ; la grille et les cibles par geste sont **inchangées**.
- [ ] `docs/loadtest.md` (ou le README du harnais) : `run.sh terrain`, les variables `TERRAIN_PROFILES`, `TERRAIN_DAY_HOURS`, `JOURNEY_WARMUP_HYDRATED`, et la phrase de comparabilité.
- [ ] Le skill `.claude/skills/loadtest-skill/SKILL.md` mentionne le scénario `terrain` et la déclaration de population hydratée dans le pré-vol (une ligne chacun, avec renvoi à la doc).

### Standard
- [ ] Build passes (0 errors) — `dotnet build HealthPlatform.Api.Mail.sln` (le harnais vit dans le repo : le build doit rester vert même s'il n'est pas touché)
- [ ] Tests pass (0 failures) — `dotnet test` **et** `node --test lib/*.test.mjs` depuis `tests/loadtest-k6/`
- [ ] Aucune donnée de santé dans les tags de métriques : les seules valeurs de `profile` sont trois littéraux ; aucun UID, INS, nom de dossier ou identifiant patient n'apparaît dans un tag (même garde que `routes.js`).

## Manual Test Plan

**Préalable** : banc distant monté selon `.claude/skills/loadtest-skill/SKILL.md`
(AppHost `https-load-test` avec `MSS_LOADTEST_MAIL_HOST=192.168.1.69` et
`MSS_TENANT_REGISTRY_DB=mss_registry_loadtest`, seed `--messages 0` pour les
proxies, population **déjà hydratée** — celle du 17/09 l'est).

1. **Tir court de forme** (10 min, 50 praticiens) :
   ```bash
   cd Api/Mail
   MSS_LOADTEST_MAIL_HOST=192.168.1.69 BYPASS_KEY=loadtest-local-only PROM=1 \
   USERS=50 UID_BASE=365 MESSAGES_PER_USER=247 LATENCY_MS=96 \
   JOURNEY_STAGES=50:600s JOURNEY_RAMP_S=10 JOURNEY_WARMUP_HYDRATED=1 \
   TERRAIN_DAY_HOURS=1 TESTID=terrain-forme \
   tests/loadtest-k6/run.sh terrain
   ```
   (`TERRAIN_DAY_HOURS=1` comprime la **journée** — pas les gestes — pour voir
   plusieurs sessions par praticien en 10 min ; c'est un réglage de test de
   forme, à ne jamais utiliser pour un verdict.)
   - **Voir** dans le log de `setup()` : `modèle terrain`, les trois profils et
     leurs parts, `chauffe : population hydratée`, passage moyen attendu
     **absence comprise** (plusieurs minutes, pas ~80 s).
   - **Voir** la chauffe terminer en **moins d'une minute** (population hydratée).
   - **Voir** dans le résumé k6 : `terrain_sessions` > 50, `terrain_absence_seconds`
     avec un p50 de l'ordre de la minute.
2. **Rapport** : `tests/loadtest-k6/report.sh <json> --expected 247`
   - **Voir** la section « Terrain — praticiens inscrits, concurrence active » ;
     la concurrence active moyenne est **nettement inférieure à 50** ; sessions/h
     obtenues et attendues sont du même ordre.
   - **Voir** le titre du verdict : « 50 praticiens inscrits — M actifs en moyenne ».
   - **Voir** la ligne « chauffe en mode population hydratée ».
   - **Voir** dans `reports/INDEX.md` la ligne `terrain`, marquée famille distincte.
3. **Non-régression `journey`** : relancer un `journey` de 5 min à 20 praticiens
   sans aucune variable `TERRAIN_*` ni `JOURNEY_WARMUP_HYDRATED`.
   - **Voir** qu'aucune métrique `terrain_*` n'apparaît, que le log de `setup()`
     est celui d'aujourd'hui, et que le rapport n'a pas de section Terrain.
4. **Contre-épreuve du débit** : sur le rapport du 17/09
   (`reports/2026-09-17/journey-1000-hydrate-20260917-231713.json`), relancer
   `report.sh` — **voir** le débit du palier 1000 passer de 24,66 à **~136 req/s**.
5. **Refus franc** : `TERRAIN_PROFILES="a:0.5:2:3,b:0.6:5:6"` (parts > 1) — **voir**
   le tir refusé en `setup()` avec un message qui nomme la somme des parts.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — outillage de banc de charge, aucune fonctionnalité produit
- **Vague Ségur** : hors Ségur — idem
- **Exigences DSR honorées** : non applicable — outillage
- **INS** : non applicable — les patients du banc sont synthétiques (`JEUX_TESTS_FULL`), aucun INS réel ; le scénario ne fabrique aucun identifiant patient (il lit ceux que l'API rend, comme le client réel — task-226)
- **Authentification PS** : non applicable — bypass de banc (`X-Test-Bypass`, profil `https-load-test`, `MSS_ENFORCE_PSC_IDENTITY=false`), jamais actif hors banc
- **Habilitations** : non applicable — identités virtuelles `loadtest-{n}` (RPPS synthétiques `9000000000{n}`)
- **Interop CI-SIS** : non applicable — le scénario exerce la chaîne existante sans la modifier
- **Tracé PGSSI-S** : non applicable au scénario ; le journal d'audit existant (task-300/301) trace normalement ce que le banc déclenche, et c'est **lui** qui servira de source de calibration (voir « Calibration »)
- **Consentement patient** : non applicable — données synthétiques
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — banc local et cluster de test, données synthétiques uniquement
- **AIPD / impact RGPD** : inchangé — aucune donnée personnelle réelle ; les tags de métriques ne portent que des littéraux (garde-fou DOD)

## Branches
- `api-mail` (pushed) : feat/task-321-scenario-terrain — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-321-scenario-terrain

## Develop log

- Repos touched : api-mail (harnais k6 + docs — aucun C# touché)
- DTOs published : no DTO change
- Interop published : no interop change
- Commits :
  - api-mail : 5bf8e912 feat(loadtest): scenario terrain — praticiens inscrits, concurrence emergente (task-321)
- Local build / test : ✓ api-mail — dotnet build 0 erreur ; dotnet test 4 493 verts (16 skips pré-existants) ; selftest.sh : 121 node + 373 unittest verts ; k6 inspect : 14 seuils terrain_* en mode terrain, 0 en journey, refus franc des parts fausses
- Passe qualité (/simplify) :
  - Applied (avant commit, fondu dans le commit feature) : api-mail: 1 file — ITERATION_S dérivé de TERRAIN_RHYTHM au lieu d'un second calcul du rythme, import inutile retiré
  - No change : docs, report.py, terrain-model.js
  - Skipped (contract/excluded) : dtos-mss, interop-cda, sdk
- DOD self-check : 20/23 items vérifiables par commande vérifiés (build, tests node/python/.NET, run.sh terrain, seuils, refus, débit régime 136, non-régression journey, docs présentes) ; 3 items observationnels (tir de forme, section Terrain sur un tir réel, chauffe < 1 min) → Manual Test Plan
- Next step : /sonar task-321

## Timings

*(généré par `tools/timing/report.sh --task task-321 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 4.4 s | — | — | — | — |
| /develop | ok | 19 min 13 s | 1 (4.1 s) | 1 (1 min 36 s) | — | api-mail 1B/1T |
| /sonar | skipped | 0.4 s | — | — | — | api-mail touche sans C# : rien a scanner |
| /lint-angular | skipped | 0.4 s | — | — | — | repo non touche (Repos: api-mail) |
| /lint-mobile | skipped | 0.4 s | — | — | — | repo non touche (Repos: api-mail) |
| /verify-visual | skipped | 0.4 s | — | — | — | repo non touche (Repos: api-mail) |
| /review | ok | 2 min 32 s | 1 (18 s) | 1 (1 min 30 s) | — | api-mail 1B/1T |
| /tech-writer | ok | 3 min 08 s | — | — | — | — |
| **Total cycle** | | **25 min 00 s** | **2 (22 s)** | **2 (3 min 06 s)** | **0 (0.0 s)** | |

## Sonar log

**Skipped — api-mail touché, mais aucun fichier C# dans le diff** (`git diff --name-only origin/develop...HEAD | grep '\.cs$'` → 0). Le scanner SonarScanner for .NET n'analyse que le C# : sur ce new code (k6 JavaScript, Python du rapport, Markdown), il n'aurait rien à lire, et un scan complet (build + couverture OpenCover + analyse serveur) coûterait ~15 min pour un tableau de KPIs identique à la baseline. Skip explicite, jamais silencieux (règle du playbook) : la qualité du harnais est portée par ses propres auto-tests — `selftest.sh` : 121 node + 373 unittest verts.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | sans objet — 0 fichier C# | idem | — |
| New coverage | sans objet | idem | — |
| Bugs / Vulnérabilités / Smells (new code) | 0 / 0 / 0 | 0 / 0 / 0 | 0 |
| Coverage projet / Duplication / Ratings | inchangés (aucun C# touché) | inchangés | 0 |

## Lint log

Skipped — `client-angular` non listé dans **Repos**. L'arbre `Client/Angular` porte 2 fichiers non commités **antérieurs à cette task** (travail code-only de task-315, commit TFS à la main de l'humain) : ils ne relèvent pas de task-321, le lint ne les touche pas.

## Lint mobile log

Skipped — `client-mobile` non listé dans **Repos** et arbre `Client/Mobile` inchangé.

## Visual verify log

Skipped — aucun écran mobile touché.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/245 — label `awaiting-human-merge`

## Code Review Summary

**APPROVED** — 12 fichiers relus, 2 suggestions non bloquantes, 0 bloquant.

- `lib/terrain-model.js` — ✅ module pur, refus francs à la frontière, K tenu à 1 sur absence/session, profil déterministe
- `lib/journey-model.js` — ✅ override optionnel (défaut null : journey inchangé), constantes hydratées sourcées, frontière task-254 écrite
- `scenarios/journey.js` — ✅ bifurcation en tête de `doctor()`, chemin journey textuellement l'ancien ; tag `profile` posé une fois, jamais sur `http_req_duration`
- `report.py` — ✅ None quand la métrique manque ; régime = plateau entier sans `warmupEndS` — ⚠️ helper `minutes()` souhaitable ; ⚠️ factorisation possible avec la fenêtre de régime Prometheus (~l.3360)
- Tests — ✅ témoins négatifs systématiques ; cas réel du 17/09 rejoué chiffre pour chiffre

Validation /review : build 0 erreur, 4 493 tests .NET verts (16 skips pré-existants), selftest 121 node + 373 unittest, DOD 23/23 (3 observationnels → Manual Test Plan).
