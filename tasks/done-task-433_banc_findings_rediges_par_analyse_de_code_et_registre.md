# todo-task-433.md — Chaque tir de banc produit des findings rédigés par analyse de code, suivis dans un registre

**Repos**: forge *(plan de contrôle `HealthPlatform.Forge` : racine du workspace, hors table des repos de code)*
**Dependencies**: task-431, task-432 (leurs signaux et leurs sites alimentent l'analyse ; sans eux, l'étape tourne en
mode dégradé : recherche du code par noms de tables)
**Epic**: E015
**Single frontend**: true
**Priorité**: **2**. Étage 3 de l'amélioration « le banc comme outil d'exploration » (2026-11-06). Il transforme un
rapport de mesure en liste de défauts confirmés, chacun avec sa cause dans le code, son gain chiffré et le test qui
prouverait sa correction.

> **Origine.** Demande de l'humain du 2026-11-06 : « comment faire du loadtest un outil d'exploration des axes
> d'amélioration, afin que le rapport rédige les findings issus d'une analyse de code ». Préfiguration faite le même
> jour à la main sur le tir `pgstats-journey-193047.tsv` : 6 candidats, 3 confirmés (task-429, task-430 F-A et F-B),
> 1 écarté (le registre, coût normal), 1 mineur à confirmer (document médical chargé avec `Embedding`), 1 non exploré
> (chargement des types Npgsql).

## Ce qui est établi

- **L'exploration de code se fait aujourd'hui au fil de l'attention.** Elle est rigoureuse quand elle a lieu (F1 et F2
  du tir du 2026-11-05), absente sinon : le défaut des pièces jointes a traversé tous les rapports.
- **La préfiguration du 2026-11-06 a suivi une méthode reproductible** :
  1. classer les formes par signal (task-431) ;
  2. lire le texte SQL complet ;
  3. retrouver le site dans le code (task-432) ;
  4. `EXPLAIN (ANALYZE, BUFFERS)` sur une base du banc ;
  5. juger la cause ;
  6. chiffrer le gain à partir des mesures ;
  7. proposer le correctif et son test.

  Elle a aussi produit un faux positif (le registre). La lecture du code et du plan doit donc pouvoir **écarter** un
  candidat, pas seulement le confirmer.
- **Un même défaut peut réapparaître d'un tir à l'autre** tant qu'il n'est pas corrigé. Sans registre, il est rejugé à
  chaque fois. Une récidive (même classe qu'un défaut corrigé) n'est pas distinguée d'un défaut neuf.

## Objective

Après chaque tir, une étape `/loadtest-findings {rapport}` explore les traitements coûteux et ajoute au rapport une
section « Findings — analyse de code ». Chaque finding porte :
- la forme SQL et ses chiffres ;
- la route et le `fichier:ligne` ;
- la cause, et le plan d'exécution qui la montre ;
- le gain calculé à partir des mesures du tir ;
- le correctif proposé et le test qui le prouverait (règle 1b) ;
- un verdict : **confirmé**, **plausible** ou **écarté**, avec sa raison.

Un registre suit chaque finding d'un tir à l'autre.

Règles :
- **Candidats** : au plus 8 par tir.
  - Ce sont les formes signalées par les détecteurs de task-431, puis les plus coûteuses en temps et en pages lues.
  - Un finding déjà au registre avec le statut « task » ou « écarté » n'est pas ré-exploré. Il est seulement remesuré.
- **Chaque finding cite ses preuves** :
  - chiffres tirés du `pgstats-*.tsv` du tir, jamais estimés au jugé ;
  - site du code (commentaire `site=` de task-432, sinon recherche documentée) ;
  - plan d'exécution sur une base du banc.
  - Sans plan ni site retrouvé, le verdict est au mieux **plausible**.
- **Gain** : borné par ce que la forme coûte sur le tir (temps SQL, pages, lectures disque). Jamais un gain sur le
  temps de réponse sans mesure : il est annoncé comme « à mesurer par A/B ».
- **Registre** `Docs/audits/findings-registry.md`. Chaque finding a :
  - un identifiant `FND-{NNN}` ;
  - sa classe (celle des détecteurs de task-431) ;
  - le premier tir où il apparaît ;
  - un statut : ouvert, task, corrigé et mesuré, écarté avec raison ;
  - la task et la mesure d'après.
  - Un finding de la même classe qu'un finding déjà corrigé est marqué **récidive**, et le rapport dit quelle prévention
    a manqué.
- **L'humain décide** : la forge ne rédige aucune task d'elle-même. Le rapport propose, l'humain choisit, puis `/po`.
- **Boucle d'amélioration (règle d'or)** : un défaut trouvé hors du banc, ou trouvé plus tard, alors qu'il était
  visible dans un tir passé, ajoute un détecteur à task-431 et un cas au corpus.
- **Invocation** :
  - le skill de banc l'appelle après `report.sh`, pour tout tir dont le rapport est copié dans `Docs/audits/` ;
  - elle est aussi lançable seule sur un rapport existant ;
  - elle n'est jamais dans la chaîne `/start` → `/review` (règle 13 inchangée).

### Hors périmètre

- Les détecteurs eux-mêmes : task-431. La remontée vers le code : task-432.
- Corriger un finding : chaque correctif est une task, rédigée par `/po` sur décision humaine.

## Definition of Done

- [x] Commande `.claude/commands/loadtest-findings.md` et playbook `agents/loadtest-findings.md`, qui décrivent :
      - les candidats ;
      - les preuves exigées par verdict ;
      - le modèle de finding ;
      - le registre et la récidive ;
      - la mesure du coût de l'étape (`Tools/timing/step.sh`, `--step loadtest-findings`) ;
      - le mode dégradé sans task-431 ni task-432.
- [x] Modèle de section « Findings — analyse de code » et `Docs/audits/findings-registry.md` créé, amorcé avec les
      findings du 2026-11-06 :
      - FND pièces jointes du dossier patient → task-429 ;
      - F-A biologie → task-430 ;
      - F-B étiquettes → task-430 ;
      - registre → écarté, coût normal d'une recherche indexée ;
      - document médical avec `Embedding` → plausible, gain mineur ;
      - chargement des types Npgsql → ouvert, non exploré ;
      - les findings F1 (task-427) et F2 (task-426) du 2026-11-05 → corrigé et mesuré.
- [x] **Rejeu sur le tir du 2026-11-06 (`…-apres`)** : la commande produit une section qui retrouve **au moins** les
      trois findings confirmés à la main (pièces jointes, F-A, F-B) et écarte le registre, avec site et plan. Résultat
      recopié dans le task file
- [x] **Contrôle de non-confabulation** : chaque chiffre d'un finding du rejeu est retrouvé dans le `pgstats-*.tsv` du
      tir, et chaque `fichier:ligne` existe au commit du tir. Vérification consignée
- [x] `.claude/skills/loadtest-skill/SKILL.md` appelle l'étape après `report.sh`
- [x] `CLAUDE.md` : la commande est ajoutée au tableau des commandes, hors chaîne autonome
- [ ] Changements du plan de contrôle relus par l'humain avant le push (règle d'or, point 7)

## Manual Test Plan

- [ ] Lancer `/loadtest-findings Docs/audits/api-mail-loadtest-journey-courte-1400-1996-ab-findings-apres-20261106.md`.
- [ ] Lire la section ajoutée : chaque finding a ses chiffres, sa route, son `fichier:ligne`, son plan et son verdict.
- [ ] Ouvrir `Docs/audits/findings-registry.md` : les findings du 2026-11-05 et du 2026-11-06 y sont, avec leur statut.
- [ ] Relancer la commande sur le même rapport : aucun doublon dans le registre, les findings connus sont remesurés et
      non ré-explorés.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — outillage de la forge
- **Vague Ségur** : hors Ségur — outillage
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — l'étape lit des textes SQL normalisés et des plans d'exécution sur des bases de banc
  synthétiques
- **Authentification PS** : non applicable
- **Habilitations** : non applicable
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : non applicable — aucun acte. Garde-fou : aucun finding ne recopie une valeur de ligne, seulement
  des textes SQL normalisés, des plans et des compteurs
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — bases de banc synthétiques. Interdit : jouer `EXPLAIN ANALYZE` sur une base réelle de
  production
- **AIPD / impact RGPD** : inchangée

## Develop log

**Livré** (plan de contrôle). Rien n'est commité : tout attend la relecture humaine (règle d'or, point 7).

| Fichier | Rôle |
|---|---|
| `.claude/commands/loadtest-findings.md` | la commande, hors chaîne autonome |
| `agents/loadtest-findings.md` | le playbook : entrées, candidats, preuves exigées par verdict, modèle de section, récidive, registre, mode dégradé, mesure de l'étape, limites |
| `Tools/loadtest-findings/findings.py` + `test_findings.py` | l'outillage mécanique : `candidates`, `explain`, `column-sizes`, `check` (25 tests) |
| `Docs/audits/findings-registry.md` | le registre, amorcé : FND-001 à FND-010 |
| `Docs/audits/findings/plans/20261106-apres/` | les 11 plans et mesures par colonne du rejeu |
| `Docs/audits/api-mail-loadtest-journey-courte-1400-1996-ab-findings-apres-20261106.md` | la section « Findings — analyse de code » du rejeu |
| `.claude/skills/loadtest-skill/SKILL.md` | § 5b-quater : l'étape après `report.sh`, avant l'arrêt du banc |
| `CLAUDE.md` | la commande au tableau, hors chaîne |
| `.gitignore` | `Tools/loadtest-findings/` suivi |

### Conception

- **L'outil fait le mécanique, le playbook le jugement.**
  - `findings.py` choisit les candidats, formate les mesures, joue les plans et contrôle les preuves.
  - Le site, la cause, le verdict et le correctif relèvent de l'agent. Le contrôle vérifie après coup ce qu'il cite.
- **Candidats** :
  - d'abord les formes signalées par task-431, au plus 6 ;
  - puis les plus coûteuses en temps, puis en pages, jusqu'à 8 ;
  - une variante (même début de texte) n'occupe pas de place ;
  - une forme réglée au registre est remesurée, pas ré-explorée ; `--full` ré-explore tout.
- **Plans** :
  - `EXPLAIN (ANALYZE, BUFFERS)` dans une transaction **annulée**, en plan générique : les paramètres sont tirés de la
    base et jamais affichés ;
  - `--setup` reconstitue le schéma du commit du tir, en retirant un index ajouté depuis ;
  - l'outil refuse toute base qui n'est pas du banc.
- **PostgreSQL 16 ne détoaste pas sous `EXPLAIN ANALYZE`.**
  - Découvert en cours de route : le plan de FND-007 montrait 2 pages, là où le tir en lisait 18 par appel.
  - Pour la classe `colonne-volumineuse`, la preuve est donc le poids de chaque colonne (`column-sizes`,
    `pg_column_size`). C'est écrit au playbook.
- **Récidive** : un finding de même classe de défaut (D1 à D4) qu'un finding corrigé.
  - Le poids dans le tir (D5) n'en fonde pas une.
  - La première version marquait FND-007 comme récidive de la recherche (FND-002), au seul titre de leur poids.
- **Contrôle de non-confabulation** :
  - chaque mesure d'un finding et du tableau de synthèse est comparée, au caractère près, au `pgstats` reformaté ;
  - chaque `fichier:ligne` est lu par `git show {commit}:{fichier}` ;
  - chaque ligne de plan citée est cherchée dans le plan sauvegardé ;
  - le registre ne doit avoir ni identifiant ni forme en double.

### Rejeu sur le tir du 2026-11-06 (`…-apres`) — résultat

- **Mode** : complet (`--full`).
- **Code tiré** : api-mail `f50f2ae5`, d'après le journal du tir.
- **Candidats** : 8.
- **Base des plans** : `u_l9l_b27c2b6f659b50f6240b3481927d0381`, la base de banc la plus volumineuse.
- **Site** : en mode dégradé. Le tir précède task-432, chaque site est donc retrouvé par `git grep` au commit du tir.

| Finding | Verdict | Temps SQL | Lu sur disque | Preuve |
|---|---|---|---|---|
| FND-007 Document médical chargé entier à l'ouverture d'un message | **confirmé — récidive** | 165.7 s | 5.4 Go | `MailRepository.cs:1263` ; `Embedding` 6 148 o/ligne jamais affiché |
| FND-004 Comptage de biologie (F-A) | **confirmé** | 113.7 s | 0.1 Go | `MailRepository.cs:1967` ; `Seq Scan` par document, index retiré |
| FND-003 Pièces jointes du dossier patient | **confirmé** | 67.6 s | 5.1 Go | `PatientRepository.cs:700` ; `Content` 184 586 o/ligne |
| FND-005 Comptages d'étiquettes (F-B) | **confirmé** | 62.9 s | 0.0 Go | `MailRepository.cs:3461-3462` ; deux `SubPlan` identiques |
| FND-010 Recherche vectorielle sans index | **plausible** | 43.1 s | 1.5 Go | `Seq Scan` + distance sur chaque document ; défaut seulement à plus grande échelle |
| FND-009 Contenu du message avec son vecteur | **confirmé — récidive** | 42.4 s | 0.3 Go | `MailRepository.cs:1326` ; `Embedding` 68 % des octets |
| FND-002 Recherche plein texte, forme d'après task-427 | **écarté** | 167.8 s | 0.2 Go | correctif en place (`Memoize` sur `lower(Body)`) |
| FND-006 Registre, la boîte de la personne | **écarté** | 67.9 s | 0.0 Go | deux index uniques, 12 pages, 0,3 ms |

- **Les trois findings confirmés à la main sont retrouvés**, avec site et plan : pièces jointes, F-A, F-B. **Le
  registre est écarté.**
- **Le rejeu va plus loin que la lecture manuelle.**
  - FND-007 était jugé « plausible, gain mineur ». Il pèse en réalité 13,0 % du temps SQL et 33,1 % des lectures
    disque du tir : c'est la première forme du tir en lectures disque.
  - `Embedding` et `MetadataJson` y sont lus et jamais affichés, alors que le chemin groupé les écarte depuis task-322.
  - FND-009, son pendant sur `MailContents`, n'avait pas été vu.
- **Récidive, et la prévention qui a manqué** :
  - la consigne `groupby-final-materialise-l-entite` de `conventions/csharp.md` interdit déjà ce chargement ;
  - mais sa garde `AttachmentBytesReadEndToEndTests` ne couvre que `Content` ;
  - proposition à l'humain : une task FND-007 + FND-009, avec la garde « aucune route de lecture ne sélectionne
    `Embedding` ».

### Contrôle de non-confabulation — consigné

```
python Tools/loadtest-findings/findings.py check --section Docs/audits/api-mail-loadtest-journey-courte-1400-1996-ab-findings-apres-20261106.md \
    --pgstats Api/Mail/tests/loadtest-k6/reports/2026-11-06/pgstats-journey-193047.tsv --commit f50f2ae5 \
    --plans Docs/audits/findings/plans/20261106-apres --registry Docs/audits/findings-registry.md
101 élément(s) contrôlé(s), 0 écart(s)
```

- **Le contrôle voit rouge.** Vérifié sur la section réelle par trois falsifications :
  - `Temps SQL` passé de 165.7 à 160.7 s → « le pgstats dit 165.7 s » ;
  - `MailRepository.cs:99999` → « au-delà de la fin (5487 lignes) au commit f50f2ae5 » ;
  - « Rows Removed by Filter: 42 » → « ligne de plan absente du plan sauvegardé ».
- **Le tableau de synthèse est désormais contrôlé.** Il échappait au contrôle lors de cette vérification ; il y est
  entré ensuite, et sa falsification (165.7 → 150.0 s) est vue.
- **Chaque mutation de l'outil est vue rouge par un test** :

  | Mutation | Test qui échoue |
  |---|---|
  | M1 `--full` ignoré | `test_select_Full_IgnoresTheRegistry` |
  | M2 garde des bases du banc ouverte | `test_runExplain_RefusesAnyBaseThatIsNotABenchBase` |
  | M3 mesures non comparées | `test_check_AMeasureThatIsNotThePgstats_IsReported` |
  | M4 D5 fonde une récidive | `test_select_TheWeightInTheTir_NeverFoundsARecidive` |

- **Aucune valeur de ligne dans les plans sauvegardés.** Recherche d'UUID, de littéraux et de longs nombres : rien.

### Relance sur le même rapport (Manual Test Plan, point 4)

Mode normal, registre amorcé :
- FND-001 à FND-006 sont **remesurés, non ré-explorés** ;
- FND-007, FND-009 et FND-010 (`ouvert`) reviennent en candidats avec leur identifiant ;
- `check --registry` ne trouve aucun doublon.

### Passe qualité (§Q)

Sans objet : le plan de contrôle n'est pas un repo de la table. J'ai relu le code à la main pendant l'écriture, et
corrigé deux défauts : la récidive fondée sur D5 et le tableau de synthèse hors contrôle (voir plus haut).

### Pièges rencontrés

- **Un `\b` dans un script Python est devenu un retour arrière** une fois écrit dans le fichier : le regex des md5 ne
  trouvait rien.
  - La mémoire « Write/Edit : échappements et CRLF » le disait déjà, mais le piège est passé par un script, pas par
    Write/Edit.
  - Un test l'aurait vu : `test_readRegistry_ReadsEveryFormOfARow_AndItsStatus`, écrit après coup.
- **`EXECUTE` sur un plan générique affiche `$1`**, jamais la valeur du paramètre : c'est ce qui permet de tirer les
  paramètres de la base sans les exposer.

## E2E log

| Voie | Déclenchée par | Résultat |
|---|---|---|
| mobile | — | skipped : ni `api-mail`, ni `client-mobile`, ni `dtos-mss` touché |
| angular | — | skipped : ni `api-mail`, ni `client-angular`, ni `dtos-mss` touché |

**E2E : skipped** — aucune voie touchée. La task ne modifie que le plan de contrôle (commande, playbook, outillage du banc, registre, documentation d'audit). Aucun parcours médecin n'est concerné.

## Branches
- `forge` (plan de contrôle, racine du workspace) : **aucune branche**. La modification se fait sur `develop`, dans la session, et le diff des fichiers de la chaîne (`.claude/commands/`, `agents/`, `CLAUDE.md`, `SKILL.md`) est **relu par l'humain avant le push** (règle d'or, point 7 ; règle 5).
- Aucun repo de code n'est touché par cette task.

## Timings

*(généré par `tools/timing/report.sh --task task-433 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 17 s | — | — | — | — |
| /develop | ok | 18 min 00 s | — | — | — | — |
| /e2e | skipped | 0.5 s | — | — | — | aucune voie touchée (plan de contrôle seul) |
| /review | ok | 35 s | — | 1 (0.2 s) | — | forge 0B/1T |
| /tech-writer | ok | 0.6 s | — | — | — | — |
| **Total cycle** | | **18 min 55 s** | **0 (0.0 s)** | **1 (0.2 s)** | **0 (0.0 s)** | |

## PRs
- `forge` (plan de contrôle) : **pas de PR** (règle 5). Les livrables sont **dans l'arbre de travail de `develop`,
  non commités**, en attente de la relecture humaine (règle d'or, point 7 ; DoD, dernier point). Après relecture :
  commit puis push sur `develop`.
  - suivis, modifiés : `.claude/skills/loadtest-skill/SKILL.md` (§ 5b-quater), `CLAUDE.md` (tableau des commandes),
    `.gitignore` (`Tools/loadtest-findings/`),
    `Docs/audits/api-mail-loadtest-journey-courte-1400-1996-ab-findings-apres-20261106.md` (section du rejeu) ;
  - nouveaux : `.claude/commands/loadtest-findings.md`, `agents/loadtest-findings.md`,
    `Tools/loadtest-findings/findings.py`, `Tools/loadtest-findings/test_findings.py`,
    `Docs/audits/findings-registry.md`, `Docs/audits/findings/plans/20261106-apres/` (11 fichiers).
- Aucun repo de code n'est touché.

## Code Review Summary

**APPROVED** — 9 fichiers revus, 0 point bloquant, 2 suggestions.

- **Validation** :
  - `python -m unittest Tools/loadtest-findings/test_findings.py` : 25 tests verts ;
  - `findings.py check` sur la section du rejeu : 101 éléments, 0 écart ;
  - 4 mutations de l'outil, chacune vue rouge par un test.
- **Règle 1b** : sans objet, aucun comportement atteignable par un endpoint ne change. **E2E** : skipped, aucune voie
  touchée.
- **DoD** :
  - 6 points sur 7 sont cochés et vérifiés ;
  - le 7ᵉ, « relu par l'humain avant le push », revient à l'humain.
- `findings.py` — ✅
  - les plans se jouent en transaction annulée, en plan générique, et sur les seules bases du banc (garde testée) ;
  - le contrôle compare les mesures au caractère près, après le même formatage ;
  - mode dégradé sans task-431.
- `agents/loadtest-findings.md` — ✅ preuves exigées par verdict, et limite PostgreSQL 16 (pas de détoast sous
  `EXPLAIN`) écrite.
- Registre — ✅ une forme par ligne, contrôlé ; récidives nommées avec leur prévention manquante.
- **Suggestions (non bloquantes)** :
  - ⚠️ `select` considère deux fois les formes non signalées (classements par temps puis par pages). Une variante
    peut donc être listée deux fois dans le dossier des candidats. C'est cosmétique : aucune place n'est consommée.
  - ⚠️ Le squelette de variante (60 premiers caractères) peut réunir deux tables différentes qui commencent par les
    mêmes colonnes : c'est le cas des deux recherches vectorielles, jugées ensemble à juste titre. Y inclure la table
    du `FROM` le rendrait sûr.
