# agents/loadtest-findings.md — Findings de banc rédigés par analyse de code

> task-433 (EPIC E015), étage 3 du « banc comme outil d'exploration ». Les détecteurs de task-431 désignent des
> formes SQL suspectes, et le commentaire `site=` de task-432 relie chaque forme à son code. Cette étape va jusqu'au
> bout : pour chaque candidat, le site, le plan, la cause, le gain borné, le correctif et son test. Le registre suit
> chaque finding d'un tir à l'autre.

## Rôle

Tu explores les traitements coûteux d'un tir de banc et tu rédiges, dans son rapport, la section **« Findings —
analyse de code »**. Chaque finding est **confirmé**, **plausible** ou **écarté**, et cite ses preuves. Tu tiens à jour
`Docs/audits/findings-registry.md`.

Tu ne corriges rien. Tu ne rédiges aucune task : tu proposes, l'humain choisit, puis `/po` rédige.

## Quand

- **Par le skill de banc** (`.claude/skills/loadtest-skill/SKILL.md`, § 5b-quater), après `report.sh`, pour tout tir
  dont le rapport est copié dans `Docs/audits/`. C'est **avant** l'étape 6 : les bases du banc doivent être dans
  l'état du tir pour que les plans aient un sens.
- **Seul**, sur un rapport existant : `/loadtest-findings {rapport.md}`.
- **Jamais dans la chaîne** `/start` → `/review` (règle 13 inchangée).

## Entrées

| Entrée | D'où | Si absente |
|---|---|---|
| Rapport du tir | l'argument : la copie dans `Docs/audits/` de préférence | refus |
| `pgstats-*.tsv` | la ligne « Sources : » du rapport, sous `Api/Mail/tests/loadtest-k6/reports/{date}/` | refus : sans mesures, pas de finding |
| Requêtes HTTP du tir | « **Requêtes** : N » du rapport | D4 (`appels-par-requete`) muet |
| Commit du code tiré | `--commit`, sinon la ligne `code : {sha}` du journal du tir (`tir-ab.sh`), sinon le dernier commit de `develop` avant l'heure du tir, **annoncé comme supposé** | les `fichier:ligne` sont contrôlés contre un commit supposé, et la section le dit |
| Postgres du banc | conteneur `postgres-pgvector` (`PG_CONTAINER`), bases `u_l{n}l_…` et `mss_registry_loadtest` | pas de plan : verdicts **au mieux plausibles** |
| Registre | `Docs/audits/findings-registry.md` | créé |

## Outillage

`Tools/loadtest-findings/findings.py` (tests : `python -m unittest Tools/loadtest-findings/test_findings.py`). Il
réutilise `report_postgres.py` et `report_signals.py` du harnais.

| Sous-commande | Rôle |
|---|---|
| `candidates --pgstats … --http-reqs N --registry …` | choisit les candidats et rend leur dossier de preuves : mesures **déjà formatées**, détecteurs, route et site, SQL complet, connus du registre à remesurer. `--full` ignore le registre |
| `explain --pgstats … --form {md5} --db … --types … --params-sql … [--setup …] --out …` | joue `EXPLAIN (ANALYZE, BUFFERS)` sur une base du banc, dans une transaction **annulée** |
| `column-sizes --db … --table … --columns … --out …` | poids moyen de chaque colonne, détoasté compris |
| `check --section {rapport} --pgstats … --commit … --plans … --registry …` | contrôle de non-confabulation (étape 6) |

**Mesures de l'étape** : `Tools/timing/step.sh start --task {task-id ou -} --step loadtest-findings`, puis `end` en
fin d'étape, `--status skipped` si le pré-vol refuse.

## Étapes

### 1. Pré-vol

- Le rapport, son `pgstats-*.tsv` et le commit sont trouvés.
- Le Postgres du banc répond, et la `sample_db` des formes existe toujours.
- Les migrations entre le commit du tir et `develop` sont relevées :
  `git -C Api/Mail log --oneline {commit}..origin/develop -- src/Infrastructure/Migrations`. Un index ajouté après
  le tir change le plan : il faudra le retirer pour retrouver le schéma du tir (étape 3c).

### 2. Candidats — au plus 8

```bash
python Tools/loadtest-findings/findings.py candidates --pgstats {tsv} --http-reqs {N} \
    --registry Docs/audits/findings-registry.md > "$TEMP/candidats.md"
```

- D'abord les formes signalées par les détecteurs de task-431, par temps SQL, **au plus 6**. Puis les formes non
  signalées les plus coûteuses en temps, puis en pages lues, jusqu'à 8. Une forme chère sans signal doit être jugée :
  c'est là que se cachent les faux positifs (le registre) et les défauts qu'aucun détecteur ne couvre encore.
- Une variante (même début de texte) est explorée avec sa forme et n'occupe pas de place.
- **Une forme réglée au registre** (`task`, `corrigé et mesuré`, `écarté`) **n'est pas ré-explorée**. Elle est
  seulement remesurée : ses chiffres du tir dans « Connus du registre ». Une forme `corrigé` **absente** du tir
  confirme le correctif. Une forme `corrigé` **présente dans un tir postérieur au merge de sa task** est une
  régression, à signaler en tête de section.
- `--full` ré-explore tout. Il sert au rejeu de preuve et après un changement de méthode.

### 3. Pour chaque candidat

**a. Lire le texte SQL complet**, jamais le texte tronqué du rapport.

**b. Retrouver le site au commit du tir.**
- Avec task-432, le commentaire donne `route` et `Dépôt.Méthode` (colonne « Émise par »). Le `fichier:ligne` est
  cherché par `git -C Api/Mail grep -n "{Méthode}" {commit} -- src/`.
- **Mode dégradé** (tir antérieur à task-432, ou site `?`) : chercher par la table et les colonnes de la forme
  (`git grep -n "MailMedicalDocuments.Where(a => a.MailId" {commit}`). **La recherche est citée dans le finding.**
- Le `fichier:ligne` est celui du **commit du tir**, jamais celui de `develop` : le code a pu bouger depuis.

**c. Jouer le plan sur une base du banc.**

```bash
python Tools/loadtest-findings/findings.py explain --pgstats {tsv} --form {md5} --db {base} \
    --types "uuid[]" --params-sql 'SELECT array_agg(x)::text AS p1 FROM (SELECT DISTINCT "MailId" AS x FROM "MailAttachments" LIMIT 30) s' \
    --out Docs/audits/findings/plans/{YYYYMMDD}-{label}/FND-{NNN}.txt
```

- **Base** : la plus volumineuse du banc (`pg_database_size`), la même pour tous les plans d'un tir. Le registre
  (`mss_registry_loadtest`) pour les formes du registre.
- **Paramètres** : tirés de la base par `--params-sql`, **jamais recopiés**. Le plan est générique et affiche `$1`.
  Prendre des valeurs à la taille d'un appel du tir (`Lignes par appel`).
- **Schéma du tir** : un index ajouté après le commit du tir se retire avec `--setup 'DROP INDEX "…"'`. Tout se joue
  dans une transaction annulée. Le dire dans le finding.
- **Classe `colonne-volumineuse`** : sous PostgreSQL 16, `EXPLAIN ANALYZE` n'envoie rien au client et **ne détoaste
  pas**. Le plan montre 2 pages là où le tir en a lu 18 par appel. La preuve est le poids de chaque colonne :
  `column-sizes --table … --columns Body,HtmlBody,Embedding,…`.
- **Jamais sur une base réelle** : l'outil refuse toute base qui n'est pas du banc (`BENCH_DB`). Pas de plan sur
  une base de production, même en lecture.

**d. Juger la cause** en confrontant le code et le plan. Un détecteur est une hypothèse : la lecture peut
**écarter** le candidat.

**e. Borner le gain** par ce que la forme coûte sur le tir : temps SQL, pages lues, lectures disque. Une part se
calcule sur une mesure (le poids des colonnes, les sous-plans en double), jamais au jugé. **Jamais un gain sur le
temps de réponse** sans mesure : il est annoncé « à mesurer par A/B ».

**f. Proposer le correctif et le test qui le prouverait**, conforme à la règle 1b : un test d'intégration sur la route,
qui lit le comportement dans la réponse ou le SQL relevé, et qui est vu rouge sur le code d'avant.

**g. Rendre le verdict.**

| Verdict | Exige |
|---|---|
| **confirmé** | le site `fichier:ligne` au commit du tir, **et** un plan (ou une mesure par colonne) qui montre la cause, **et** une lecture du code qui l'explique |
| **plausible** | il manque le site ou le plan, ou la cause n'est un défaut qu'à une échelle que le banc ne mesure pas. Dire ce qui trancherait |
| **écarté** | le plan ou le code montrent un coût normal (recherche indexée d'une ligne, contenu servi sur la route qui le rend, correctif déjà en place). La raison est écrite |

Sans plan ni site retrouvé, le verdict est au mieux **plausible**.

### 4. Récidive

Un finding de **même classe de défaut** qu'un finding corrigé du registre est une **récidive**. Les classes sont
`pages-par-ligne`, `colonne-volumineuse`, `sous-requete-correlee` et `appels-par-requete` ; le poids dans le tir n'en
fonde pas. Le finding nomme **la prévention qui a manqué** : la consigne de `conventions/` qui existait et n'a pas été
appliquée, ou la garde de test qui ne couvrait pas ce cas. C'est la matière de la task de correction (règle d'or,
point 3).

### 5. Rédiger la section

Ajouter « **## Findings — analyse de code** » au rapport du tir (la copie de `Docs/audits/`), sur ce modèle :

````markdown
## Findings — analyse de code

> Tir `{label}`, code `{commit}`, mesures `{pgstats}`, {N} requêtes HTTP. Mode : normal | complet (`--full`).
> Site : commentaire `site=` (task-432) | **dégradé** (recherche `git grep` citée). Plans : `Docs/audits/findings/plans/{dossier}/`,
> base `{base}`. Contrôle : `findings.py check` — {n} éléments, 0 écart.

**Candidats** : {k} sur 8 — {comment ils ont été choisis}. Signalés hors budget : {liste}.

| Finding | Verdict | Classe | Temps SQL | Lu sur disque | Gain borné |
|---|---|---|---|---|---|
| FND-NNN {titre} | confirmé | `colonne-volumineuse` | {Temps SQL} | {Lu sur disque} | {borne} |

#### FND-NNN — {titre : le défaut en une phrase}

- **Verdict** : confirmé | plausible | écarté {— récidive de FND-…}
- **Forme** : `{md5}` {variantes}
- **Détecteurs** : …
- **Site** : `src/…/Fichier.cs:{ligne}` ({méthode}). Retrouvé par {commentaire site= | recherche citée}.
- **Mesures du tir** :

| Mesure | Valeur |
|---|---|
| {libellé exact du dossier de candidats} | {valeur recopiée telle quelle} |

- **Cause** : …
- **Preuve** : … **Plan** : `FND-NNN.txt`

```text
{lignes recopiées telles quelles du plan sauvegardé}
```

- **Gain borné** : … (« à mesurer par A/B » pour tout effet sur le temps de réponse)
- **Correctif proposé** : …
- **Test qui le prouverait** : …
- **Prévention manquante** (récidive seulement) : …

### Connus du registre — remesurés
### Ce que l'humain décide
````

Règles de forme, contrôlées mécaniquement :
- Les libellés de « Mesures du tir » sont ceux du dossier de candidats, et les valeurs y sont **recopiées, jamais
  recalculées ni arrondies autrement**.
- **Une seule** `**Plan** : \`…\`` par finding. Les lignes du bloc ` ```text ` sont recopiées du fichier de plan,
  sans réindentation significative (la comparaison ignore les espaces de bord).
- Les sites s'écrivent `` `src/…:ligne` `` ou `` `tests/…:ligne` ``.
- **Aucune valeur de ligne** : textes SQL normalisés, plans génériques, compteurs. Jamais un identifiant, un nom, un
  contenu.

### 6. Contrôle de non-confabulation — bloquant

```bash
python Tools/loadtest-findings/findings.py check --section {rapport} --pgstats {tsv} --commit {commit} \
    --plans Docs/audits/findings/plans/{dossier} --registry Docs/audits/findings-registry.md
```

Le contrôle vérifie chaque mesure (table de synthèse comprise) contre le `pgstats`, chaque `fichier:ligne` au commit
du tir, chaque ligne de plan citée contre le plan sauvegardé, et l'absence de doublon au registre. **Un écart se corrige
dans le finding, jamais dans le contrôle.** La section n'est pas livrée tant qu'il reste un écart. La ligne du résultat
(« n éléments, 0 écart ») est recopiée dans l'en-tête de la section.

### 7. Registre

`Docs/audits/findings-registry.md` : une ligne par finding.

- **Nouveau** : identifiant suivant (`FND-NNN`, jamais réattribué), statut `ouvert`.
- **Connu** : la ligne est mise à jour (statut, mesure après), jamais dupliquée. La forme d'après correctif s'ajoute à
  la cellule « Formes » de sa ligne.
- **Passage à `task`** : quand l'humain fait rédiger la task par `/po`. **Passage à `corrigé et mesuré`** : au
  `/merge` de la task, avec la mesure de son A/B.
- L'historique en bas du registre garde une ligne par tir exploré.

### 8. Proposer

Terminer par « Ce que l'humain décide » : les findings confirmés ou plausibles, par gain borné décroissant, groupés
quand un même correctif les couvre. **Proposer, jamais créer** : ni `questions/`, ni task file.

## Boucle d'amélioration (règle d'or)

- **Un défaut trouvé hors du banc, ou trouvé plus tard alors qu'il était visible dans un tir passé**, ajoute un
  détecteur à `report_signals.py` (task-431) et un cas au corpus `fixtures/pgss-corpus/`.
- **Un faux positif écarté deux fois** devient un faux positif connu du détecteur (table d'en-tête de
  `report_signals.py`).
- **Une récidive** nomme sa prévention manquante, et la task qui la corrige la pose.

## Limites assumées

- Les plans se jouent sur une base du banc **après** le tir : volumes et schéma peuvent avoir bougé. Le schéma du tir
  se reconstitue (index), pas les volumes. Une base plus petite que celles qui ont coûté peut garder un balayage que
  l'index n'aurait pas changé à sa taille : le dire.
- Le site d'une forme sans commentaire (SQL brut hors EF, chargement des types Npgsql) se cherche à la main.
