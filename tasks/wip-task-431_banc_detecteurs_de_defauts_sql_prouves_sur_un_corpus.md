# todo-task-431.md — Le rapport de banc détecte les défauts SQL par classe, et chaque détecteur est prouvé sur un défaut passé

**Repos**: api-mail
**Dependencies**: — (aucune ; task-429 et task-430 fournissent deux cas du corpus, sans bloquer)
**Epic**: E015
**Single frontend**: true
**Priorité**: **2**. Étage 2 de l'amélioration « le banc comme outil d'exploration » (2026-11-06). Sans lui, un
défaut n'est trouvé que si quelqu'un le remarque : celui des pièces jointes (task-429) figurait au rang 6 de tous les
rapports, sans jamais être relevé.

> **Origine.** Question de l'humain du 2026-11-06 : « que se fait-il que tu n'aies jamais trouvé ce défaut ? ».
> Analyse : la mémoire de session `feedback-lire-le-texte-sql-pas-seulement-les-parts`. Un seul nouveau critère, appliqué
> à la main au tir `pgstats-journey-193047.tsv`, a fait remonter task-429, task-430, et un faux positif (le registre).

## Ce qui est établi

- **`report.py` ne juge une requête que sur sa part du temps serveur.** Le seuil des pistes d'amélioration est
  `IMPROVEMENT_SHARE_THRESHOLD = 0.15`. Une requête qui coûte en volume lu, en lectures disque ou en répétition, mais
  pas en temps, reste sous la barre. Celle des pièces jointes faisait 5,3 % du temps et 31 % des lectures disque.
- **Ses diagnostics de requête sont génériques**, et parfois trompeurs : « jeu de travail hors `shared_buffers` ou
  cache froid » pour une requête qui sélectionnait un contenu binaire.
- **Les quatre derniers défauts SQL trouvés relèvent chacun d'une classe reconnaissable dans `pg_stat_statements`** :

  | Défaut | Classe | Signature mesurable |
  |---|---|---|
  | task-322, task-429 | colonnes volumineuses lues pour rien | pages lues par ligne rendue élevées, colonne `Content`/`Body`/`HtmlBody`/`Embedding` dans le texte |
  | task-430 | sous-requête corrélée sans index | pages lues par ligne rendue très élevées, `(SELECT count(*) … WHERE … = outer."Id")` dans le texte |
  | task-426 | relectures et surcoût de session | appels par requête HTTP ≥ 1 sur une même forme, `DISCARD ALL` par requête HTTP |
  | task-427 | traitement coûteux par appel | temps par appel × appels, ou part du temps |

- **Faux positif connu** : une recherche indexée sur une seule ligne lit environ 3 pages par accès. La lecture du
  registre (9 pages par appel, 1 ligne) n'est pas un défaut. Un détecteur « pages par ligne » sans plancher la signale
  à tort.
- **Les fichiers `pgstats-*.tsv` des tirs ne sont pas versionnés** (seuls `INDEX.md` et `POSTGRES-INDEX.md` le sont).
  Le corpus doit être extrait en fixtures réduites et versionné.

## Objective

Chaque rapport de banc porte une section « Signaux de défaut ». Chaque requête y est classée par des détecteurs, et
chaque détecteur est prouvé sur un défaut réel : il le signale sur le tir d'avant son correctif, et ne le signale plus
sur le tir d'après.

Règles :
- **Détecteurs**, chacun nommé, documenté (classe, signature, seuil, faux positifs connus) et indépendant de la part
  du temps :
  1. **pages lues par ligne rendue**, avec un plancher qui écarte la recherche indexée d'une ligne : par exemple, plus
     de 16 pages par ligne **et** plus de 1 Go lu sur le tir. Le seuil est fixé par le corpus, pas au jugé ;
  2. **colonne volumineuse sélectionnée** : `Content`, `Body`, `HtmlBody`, `BodyHtml`, `Embedding`, `MetadataJson`, sur
     une route autre que celle qui la sert. Avant task-432, ce détecteur se contente de lister les formes concernées ;
  3. **sous-requête corrélée** (`(SELECT count(*)` ou `EXISTS` sur une colonne de la requête englobante) avec un nombre
     de pages par ligne élevé ;
  4. **appels par requête HTTP** d'une même forme ≥ 1, et surcoût de session (`DISCARD ALL`, chargement des types
     Npgsql) par requête HTTP ;
  5. **part des lectures disque** ≥ 15 %, en plus de la part du temps.
- **Diagnostic** : le rapport ne conclut plus au manque de mémoire (« jeu de travail hors `shared_buffers` ») pour une
  forme qu'un détecteur 1 à 3 signale. Il renvoie au détecteur.
- **Corpus versionné**, sous `tests/loadtest-k6/fixtures/pgss-corpus/` : des extraits réduits des `pgstats-*.tsv`, sans
  donnée de santé (le texte normalisé n'a que des `$n`). Chaque cas a sa paire avant/après et son verdict attendu :
  - task-429 : la forme des pièces jointes du dossier patient. Avant : tir du 2026-11-06 ; après : tir de mesure de
    task-429 ;
  - task-430 : F-A et F-B. Avant : tir du 2026-11-06 ; après : tir de mesure de task-430 ;
  - task-426 : relectures du registre et `DISCARD ALL`. Avant : tir task-422 du 2026-11-05 ; après : 2026-11-06 ;
  - task-427 : recherche. Avant : 2026-11-05 ; après : 2026-11-06 ;
  - le faux positif du registre (forme `mss_accounts … LEFT JOIN LATERAL`) : jamais signalé ;
  - task-322, si un `pgstats-*.tsv` d'avant son correctif est retrouvé dans `reports/` ; sinon, le dire.
  - Un cas « après » qui n'existe pas encore, parce que la task n'est pas mergée, est ajouté par la task elle-même :
    sa DoD le demande.
- **Tests** : un test Python par cas du corpus, joué avec les tests existants du harnais (`test_dashboards.py`) :
  « signalé sur l'avant, silencieux sur l'après ». Un détecteur sans cas au corpus n'entre pas.

### Hors périmètre

- La remontée de la requête vers son code : task-432.
- La rédaction des findings par analyse de code, et le registre : task-433.
- Les seuils SLO et la grille des étapes : inchangés.

## Definition of Done

- [ ] Tests du harnais verts : `node --test tests/loadtest-k6/lib/*.test.mjs` et les tests Python de `tests/loadtest-k6`
- [ ] Build et tests de la solution verts (`HealthPlatform.Api.Mail.sln`), même si aucun code applicatif ne change
- [ ] Les 5 détecteurs, documentés en tête de leur code et dans `tests/loadtest-k6/README.md` (classe, signature,
      seuil, faux positifs connus)
- [ ] Corpus versionné : au minimum les cas task-429 (avant), task-430 (avant), task-426 (avant et après), task-427
      (avant et après) et le faux positif du registre
- [ ] **Un test par cas, vu rouge** : chaque test échoue quand on retire son détecteur (mutation consignée dans le
      `Develop log`), et le faux positif échoue quand on retire le plancher
- [ ] Le rapport régénéré du tir `journey-courte-1400-1996-20261106-apres` porte la section « Signaux de défaut ». Elle
      signale les pièces jointes du dossier patient, F-A et F-B, et ne signale pas la lecture du registre. Extrait
      recopié dans le `Develop log`
- [ ] Le diagnostic « jeu de travail hors `shared_buffers` » n'apparaît plus sur une forme signalée par un détecteur 1
      à 3
- [ ] Aucune donnée de santé dans le corpus ni dans le rapport : contrôle mécanique, aucun littéral dans les textes
      SQL, seulement des `$n`
- [ ] Section « Méthode » du skill de banc (`.claude/skills/loadtest-skill/SKILL.md`) : lire la section « Signaux de
      défaut » à chaque tir. Changement du plan de contrôle, relu par l'humain avant le push (règle d'or, point 7)

## Manual Test Plan

- [ ] `cd Api/Mail/tests/loadtest-k6 && python report.py reports/2026-11-06/<json du tir apres>` (commande exacte dans
      le `Develop log`) : ouvrir le rapport et lire la section « Signaux de défaut ».
- [ ] Vérifier que chaque signal cite sa classe, ses chiffres (pages par ligne, appels par requête HTTP, part disque) et
      le texte de la requête.
- [ ] Régénérer un rapport ancien (2026-11-05) : les signaux du registre et de la recherche y apparaissent.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — outillage de banc
- **Vague Ségur** : hors Ségur — outillage
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — le corpus ne contient que des textes SQL normalisés, sans valeur
- **Authentification PS** : non applicable — aucune route, aucun code applicatif
- **Habilitations** : non applicable
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : non applicable — aucun acte
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — données de banc synthétiques, aucune donnée de santé réelle
- **AIPD / impact RGPD** : inchangée

## Branches

- `api-mail` (pushed) : feat/task-431-banc-detecteurs-de-defauts-sql-prouves — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-431-banc-detecteurs-de-defauts-sql-prouves

> Pré-flight du /start (2026-11-07) : `api-mail`, `client-blazor`, `client-mobile`, `dtos-mss`, `sdk` sur `develop`.

## Timings

*(généré par `tools/timing/report.sh --task task-431 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 7.6 s | — | — | — | — |
| /develop | ok | 14 min 02 s | 1 (17 s) | 1 (5 min 32 s) | — | api-mail 1B/1T |
| **Total cycle** | | **14 min 10 s** | **1 (17 s)** | **1 (5 min 32 s)** | **0 (0.0 s)** | |

## Develop log

**Livré** (`api-mail`, `tests/loadtest-k6/`) :
- **`report_signals.py`** (nouveau) : cinq détecteurs nommés, documentés en tête du module (classe, signature, seuil,
  faux positif connu). Ils passent **toutes** les formes de `pg_stat_statements`, pas seulement le top 20.
- **`report_postgres.py`** :
  - la section « Signaux de défaut (détecteurs prouvés sur le corpus) » est rendue entre « Réaction du serveur » et le
    top 20 ;
  - `classify_query` ne pose plus « jeu de travail hors `shared_buffers` » sur une forme signalée par D1 à D3, et
    renvoie aux signaux.
- **`fixtures/pgss-corpus/`** : 8 cas, une paire avant/après pour chacun des défauts task-426, task-427, task-429 et
  task-430, plus `build_corpus.py`, l'extracteur versionné.
  - Chaque cas porte les totaux du tir entier (temps SQL, lectures disque) et le nombre de requêtes HTTP.
  - Le script refuse une forme absente ou ambiguë, et un texte SQL portant un littéral.
- **`test_report_signals.py`** : 7 tests.
  - Détecteurs attendus pour chaque forme de chaque cas.
  - Défaut signalé avant et silencieux après.
  - Chaque détecteur prouvé par au moins un cas « avant ».
  - Faux positif du registre jamais signalé.
  - Corpus sans littéral.
  - Section du rapport.
  - Diagnostic mémoire retiré sur une forme signalée.
- **`README.md`** : § « Signaux de défaut ».

**Seuils, fixés par le corpus et non au jugé** (chiffres par forme, tirés des photos) :

| Détecteur | Seuil | Avant correctif | Après | Faux positif |
|---|---|---|---|---|
| D1 `pages-par-ligne` | ≥ 10 pages par ligne, ≥ 50 par appel, ≥ 1 Go | PJ dossier 15,3 / 468 · biologie 11,8 / 213 · étiquettes 24,6 / 248 | biologie 6,8 · étiquettes 1,0 | registre 9,0 / 9 · téléchargement PJ 22,8 / 23 |
| D2 `colonne-volumineuse` | `Content`, `Body`… dans la liste du SELECT, ≥ 1 Go | PJ dossier (`Content`) · recherche d'avant task-427 (`Body`) | formes disparues | téléchargement : listé, attendu. Distance pgvector exclue |
| D3 `sous-requete-correlee` | `count(*)` / `EXISTS` corrélé, et D1 | biologie, étiquettes | — | — |
| D4 `appels-par-requete` | ≥ 1,5 par requête HTTP | compte du registre 2,96, ancre 2,96, `DISCARD ALL` 7,13 | 0,01 à 0,03 | registre boîte + ancre 1,00 |
| D5 `poids-dans-le-tir` | ≥ 15 % du disque ou ≥ 20 % du temps, par forme | PJ dossier 30,9 % du disque · recherche 25,9 % et 24,7 % du temps | recherche 10,7 % et 10,2 % | — |

- **Deux seuils prévus par la task, corrigés par le corpus** :
  - D1 « pages par appel » : 20 → **50**, parce que le téléchargement d'une PJ lit 23 pages par appel (le TOAST d'un
    contenu servi en entier) ;
  - D5 temps : 35 % → **20 %**, parce que la recherche d'avant task-427 se répartissait sur deux formes de 25 %.
- **D2 affiné** : une distance pgvector (`m."Embedding" <=> $1 AS "Distance"`) rend un nombre, pas le vecteur. Elle
  n'est plus comptée comme une colonne rendue. Cas « recherche vectorielle » ajouté au corpus : D1 seul.

**Preuve rouge** (mutations jouées sur `report_signals.py`, `python -B`, `__pycache__` effacé, fichier restauré
depuis une copie et vérifié par `cmp`) :

| Mutation | Tests rouges |
|---|---|
| M1 D1 coupé | formes attendues, avant/après, section du rapport |
| M2 D2 coupé | formes attendues |
| M3 D3 coupé | formes attendues |
| M4 D4 coupé | formes attendues, avant/après |
| M5 D5 coupé | formes attendues |
| MF planchers de D1 retirés (5 pages par ligne, 0 par appel) | formes attendues, avant/après, **faux positif du registre** |

**Rapport régénéré** : la section Postgres est reconstruite par `report_postgres.postgres_section` à partir de la photo
du tir « après » de l'A/B/A (`pgstats-journey-193047.tsv`, 760 903 requêtes HTTP). La régénération complète
demanderait Prometheus et la vérification du tir. Formes signalées, par temps SQL :

| Temps SQL | Détecteurs | Forme |
|---|---|---|
| 165,7 s | `colonne-volumineuse`, `poids-dans-le-tir` | document médical chargé en entier (`Body`, `HtmlBody`, `Embedding`), plausible |
| 113,7 s | `pages-par-ligne`, `sous-requete-correlee` | comptage de biologie (task-430) |
| 67,6 s | `pages-par-ligne`, `colonne-volumineuse`, `poids-dans-le-tir` | pièces jointes du dossier patient (task-429) |
| 62,9 s | `pages-par-ligne`, `sous-requete-correlee` | dossiers d'étiquettes (task-430) |
| 43,1 s et 37,1 s | `pages-par-ligne` | recherches vectorielles, à juger (task-433) |
| 42,4 s | `colonne-volumineuse` | contenu de message chargé (`Body`, `BodyHtml`, `Embedding`), plausible |
| 22,9 s | `colonne-volumineuse` | téléchargement d'une PJ, chemin qui sert le contenu |

- Le registre n'apparaît pas dans la section.
- Dans le top 20, la forme des PJ du dossier patient porte maintenant « voir Signaux de défaut, pas la mémoire du
  serveur ».

**Tests** : `bash selftest.sh` vert (426 tests Python, Node vert). `test_report_postgres` inchangé, vert.

**Piège retrouvé** : un `\b` écrit par un heredoc est devenu le caractère 0x08 dans une regex Python, invisible à
l'œil, et la regex ne trouvait plus rien. Corrigé par écriture d'octets. Mémoire existante
`script-node-backslash-b-backspace-invisible`. Contrôle : aucun 0x08 dans les fichiers de la task.

**Plan de contrôle, relu par l'humain avant le push (règle d'or, point 7)** :
`.claude/skills/loadtest-skill/SKILL.md`, étape 5a : « Lire la section Signaux de défaut à chaque tir ». La
modification est écrite mais **non commitée** : elle attend la relecture humaine.

## Sonar log

Analyse de la branche `feat/task-431-banc-detecteurs-de-defauts-sql-prouves` (HEAD `ff4bc122`), 2026-11-07 13:53 UTC :
- build Release, tests avec couverture OpenCover sur les 5 projets, **0 échec** ;
- traitement serveur `SUCCESS`, 0 itération (aucun code C# modifié).

### KPIs qualité (baseline → final)

| Métrique | Baseline (task-428) | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | = |
| Issues new code | 0 | 0 | = |
| New coverage | 96,0 % | 96,1 % | +0,1 |
| Bugs / Vulnérabilités / Code smells | 0 / 0 / 0 | 0 / 0 / 0 | = |
| Security hotspots | 0 | 0 | = |
| Coverage projet | 97,9 % | 97,9 % | = |
| Duplication | 0,4 % | 0,4 % | = |
| Ratings fiabilité / sécurité / maintenabilité | A / A / A | A / A / A | = |

## Lint log

Skipped — `client-angular` non touché par la task (`**Repos**: api-mail`).

## Lint mobile log

Skipped — `client-mobile` non touché par la task.
