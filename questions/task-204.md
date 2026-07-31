# questions/task-204.md — blocage trouvé au `/review`, corrigé puis levé

**Statut** : ✅ **levé** (correctif `9e4ea3f`, cf. « Résolution » en bas).
Conservé comme trace : c'est un défaut que la revue a trouvé dans le code de la
forge elle-même, et le motif mérite d'être relu.

## Étape

`/review task-204`, § 5.1 Correctness — revue du diff de `api-mail`.

## Le blocage

`report.py` — quand le JSON k6 **ne porte pas de fenêtre de tir**
(`startedAt`/`endedAt`, absents de tout tir archivé avant task-204) **et** qu'un
CSV d'échantillonnage est présent, la section « Ressources & télémétrie »
**désigne une ressource épinglée avec aplomb** en agrégeant **tout le fichier**,
y compris des points qui n'appartiennent pas au tir.

Reproduction (fixtures du repo, sans banc) :

```python
t = report.build_telemetry({}, observe_text=<fixtures/observe-sample.csv>,
                           observe_path="observe.csv")
"\n".join(report._resources_section(t, {}))
# → « **Ressource épinglée : conteneur `postgres-pgvector` (CPU)** »
```

La fixture porte **exprès** des points hors fenêtre à des valeurs absurdes
(×5). Sans fenêtre pour les écarter, `postgres-pgvector` ressort à 87,5 % de sa
borne — au-dessus du seuil de 85 % — et le rapport **conclut**.

## Pourquoi c'est bloquant, et pas une simple suggestion

C'est **exactement le mode d'échec que task-204 existe pour supprimer**. La task
demande « ne jamais conclure en silence » ; ici le rapport fait pire que
conclure en silence : il conclut **faux, et avec assurance**. Un avertissement
« fenêtre absente » figure bien dans le tableau des sources, mais trois tableaux
plus haut — un lecteur ne le rattache pas au verdict, et c'est le verdict qu'il
recopiera.

Atteignable en pratique : **29 JSON archivés** sont sans fenêtre, et `report.sh`
reprend **automatiquement** le CSV le plus récent du répertoire de tir. Il suffit
donc de régénérer un rapport archivé pendant qu'un `observe-*.csv` traîne dans le
même répertoire daté.

Le précédent qui rend ce défaut inacceptable : la campagne du 2026-07-27 a
conclu « saturé sur IMAP + CPU » sans mesure, et cette phrase a orienté deux
tasks avant d'être démentie. Un banc qui fabrique une attribution est plus
nuisible qu'un banc qui n'en fabrique aucune.

## Résolution

Traitée **en étape de développement** et non dans `/review` (la revue est en
lecture seule sur le code, règle du playbook) :

**Sans fenêtre de tir, le CSV n'est pas attribuable au tir — il n'est donc pas
replié du tout**, et la section le **dit** à la place du verdict. Le repliement
n'a de sens que borné : c'était déjà l'argument du filtrage temporel, il est
maintenant appliqué jusqu'au bout.

- `build_telemetry` : fenêtre absente + CSV présent → `observe_agg` vide et
  `observe_unusable` renseigné avec la raison.
- `_sources_table` : « ⚠️ **présent mais non repliable** — fenêtre du tir absente ».
- `_pinned_section` : aucun candidat → « on ne sait pas », jamais un nom.
- 3 tests ajoutés, dont la contre-épreuve exacte ci-dessus.
