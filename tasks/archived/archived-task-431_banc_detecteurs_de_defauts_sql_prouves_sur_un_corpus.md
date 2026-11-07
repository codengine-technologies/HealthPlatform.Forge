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
| /sonar | ok | 9 min 21 s | 1 (29 s) | 5 (7 min 35 s) | 2 (43 s) | api-mail 1B/5T |
| /lint-angular | skipped | 0.5 s | — | — | — | angular non touché |
| /lint-mobile | skipped | 0.4 s | — | — | — | mobile non touché |
| /e2e | ok | 19 min 12 s | — | — | — | e2e ×5 (37 min 35 s) |
| /review | ok | 15 min 52 s | 1 (13 s) | 2 (11 min 07 s) | — | api-mail 1B/2T |
| /tech-writer | ok | 22 s | — | — | — | — |
| **Total cycle** | | **58 min 59 s** | **3 (1 min 01 s)** | **8 (24 min 15 s)** | **2 (43 s)** | |

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

## E2E log

Voies jouées le 2026-11-07 : `api-mail` à `ff4bc122` (branche de la task), `client-mobile` à `develop`, `client-angular`
sur la branche du poste (code-only).

| Voie | Déclenchée par | Jouée / réutilisée | Résultat |
|---|---|---|---|
| mobile (`npm run e2e:headless`) | `api-mail` touché | jouée | ✅ 58 verts, 0 flaky, 0 rouge, parité verte |
| angular (`npm run e2e:mss`) | `api-mail` touché | jouée | ✅ 71 verts, 0 flaky, 0 rouge, parité verte |

Porte `gate` : code 0. Démontage vérifié : aucun conteneur e2e résiduel, aucun port du jeu e2e ouvert.

Aucun écran modifié : aucun scénario ajouté ni versionné (harnais de banc seulement).

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

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/350 — label `awaiting-human-merge`
  (commit `ff4bc122`). CI de la PR verte (run 42381593472), étape « Harness tests » comprise.
- **Plan de contrôle, en attente de relecture humaine** : `.claude/skills/loadtest-skill/SKILL.md` (étape 5a) est
  modifié en local, ni commité ni poussé (règle d'or, point 7).

## Code Review Summary

**APPROVED** — `/review` du 2026-11-07. Build : 0 erreur, 0 avertissement. Tests : domain 210, infrastructure 705, api
1 361, application 4 028, intégration 1 133 (+16 ignorés), **0 échec**.
- Au premier passage, `SemanticSearchRepositoryIntegrationTests` (famille connue) a été rouge une fois, sans AppHost
  en écoute. Il est vert seul (24/24), et la suite rejouée est verte. Aucun code C# n'est modifié par la task.
- `selftest.sh` : vert (426 tests Python). Sonar : Quality Gate OK, 0 issue. E2E : vert.

- **Règle 1b** : sans objet, aucun comportement atteignable par un endpoint ne change.
- **DoD** :
  - 5 détecteurs documentés (module et README) ;
  - corpus minimal présent (task-426, task-427, task-429 et task-430, avant et après, plus le faux positif du
    registre) ;
  - un test par cas, vu rouge par mutation (6 mutations) ;
  - section régénérée sur le tir du 2026-11-06 ;
  - diagnostic mémoire retiré sur les formes signalées ;
  - aucun littéral SQL ;
  - SKILL.md écrit, **en attente de relecture**.
- **Suggestion** : D2 liste aussi les chemins qui servent légitimement un contenu. task-432, qui portera la route de
  chaque forme, permettra de les distinguer.

## Merged

- `api-mail` : PR #350 squash-mergée le 2026-11-07 — `18f9c9fb` sur `develop`, CI develop verte (run 42382608374 : build + publish).
- Branche `feat/task-431-banc-detecteurs-de-defauts-sql-prouves` supprimée (distante et locale).
- Reste en attente de relecture humaine (règle d'or, point 7) : l'étape 5a du skill `loadtest-skill` (« Lire la section Signaux de défaut »), modifiée localement, non commitée.
