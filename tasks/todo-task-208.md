# todo-task-208.md — Le rapport de tir conclut encore faux de trois façons

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: task-204 (qui a livré la section, et dont l'escalier a révélé ces trois défauts)

> **Origine** : escalier de capacité du 2026-07-29 (task-204). Les trois défauts
> ci-dessous ont été trouvés **en lisant les rapports de la campagne**, pas en
> relisant le code : chacun a produit une affirmation fausse dans un `.md` livré.
>
> C'est la continuité directe de la raison d'être de task-204 : *ne jamais
> conclure en silence, et ne jamais conclure faux*. Le mécanisme d'absence de
> télémétrie est correct ; ce sont les **règles de conclusion** qui débordent.

## Objective

Que les trois verdicts que le rapport rend avec assurance — ressource épinglée,
part du budget servie, validité du tir — soient fondés sur la bonne statistique.

## Les trois défauts, chacun avec sa preuve

### 1. « Ressource épinglée » désigne PgBouncer sur un transitoire de démarrage

`report.py` (`pinned_candidates`) attribue `ratio = 1.0` — le maximum possible,
donc le rang n°1 garanti — dès que `cl_waiting > 0`, avec le commentaire « toute
attente cliente non nulle signe un pooler qui n'absorbe plus ; la borne est 0, pas
une capacité ».

L'intention est juste, la **statistique** ne l'est pas : la valeur retenue est le
`max` sur la fenêtre. Résultat sur la campagne :

| Palier | `cl_waiting` max **dans** la fenêtre | Verdict rendu |
|---|---|---|
| 486 req/s | **2** | « Ressource épinglée : PgBouncer — 100,0 % de sa borne » |
| 630 req/s | **1** | idem |
| 756 req/s | **3** | idem |

Un seul échantillon à 1 client en attente a donc désigné le pooler comme facteur
limitant de trois tirs — devant un réplica à 11 % et Postgres à 13,6 %.

Et l'échantillonnage montre que ces valeurs sont des **transitoires d'ouverture de
palier** : sur 230 échantillons de la campagne, 15 sont non nuls (6,5 %), tous dans
les ~30 s qui suivent le début d'un tir (pic à 75 mesuré **2 s avant** l'ouverture
d'une fenêtre). Dans les fenêtres, `cl_waiting` ≤ 8 avec `sv_active` ≤ 162 : le
pooler multiplexe 2 001 clients sur 153-162 serveurs, il absorbe parfaitement.

**Attendu** : juger `cl_waiting` sur une **présence soutenue** (part des
échantillons non nuls, ou p95, ou durée cumulée au-dessus de 0), pas sur le `max`.
Un transitoire d'ouverture doit être **signalé** (il est intéressant : il croît
avec la charge, 2 → 1 → 6 → 75) sans être promu verdict.

### 2. « Débit demandé vs délivré » divise par la fenêtre totale — et le même rapport publie l'autre chiffre

Dans **le même** `.md`, palier 486 req/s :

- en-tête : « **Débit plateau : 482,7 req/s** (k6 publie 413,7 req/s) » → **99,3 %**
  du budget servi ;
- table « Débit demandé vs délivré » : « total 486 → **413,6** — **85,1 % ⚠️** ».

C'est le défaut de dénominateur que task-204 a corrigé pour le chiffre d'en-tête
mais **pas** dans cette table, qui est pourtant celle qui porte les ⚠️ par
sous-scénario. Un lecteur en conclut « l'application ne tient que 85 % de la charge
à 486 req/s », alors qu'elle en tient 99,3 %.

**Attendu** : la table utilise le dénominateur **plateau**, ou nomme explicitement
son dénominateur ligne à ligne. Deux dénominateurs dans un document sans que la
différence soit dite est précisément ce que task-204 interdit.

### 3. La garde de validité compte le reliquat d'un scénario FINI comme des abandons

`mixed_enrich` est un `shared-iterations` de
`users × MESSAGES_PER_USER × ENRICH_SHARE / ENRICH_BATCH` lots. À 200 × 100 × 0,5 / 5
= **2 000 lots**, dont **424** tiennent dans un plateau de 3 min : k6 compte les
1 576 restants en `dropped_iterations`.

Le premier palier de la campagne a donc été déclaré **invalide à 4,6 %
d'abandons** alors que les scénarios à débit imposé n'en avaient que 2,6 % — et
qu'`enrich`, par construction, ne **peut pas** manquer de VU : aucun débit ne lui
est imposé.

Contournement utilisé pour la campagne : `ENRICH_SHARE=0.05` (bande de 200 lots,
épuisable dans le plateau) → `mixed_enrich = 0` abandon aux cinq paliers. C'est un
réglage d'opérateur, pas une correction.

**Attendu** : la garde **exclut** les scénarios sans débit imposé de son
numérateur, et le rapport dit combien d'itérations d'un scénario fini n'ont pas été
consommées (information utile, mais pas un signal d'invalidité).

## Hors scope

- Le modèle de dimensionnement des VUs (task-209).
- Les findings applicatifs (task-205, task-206, task-207).
- Le helper de table Markdown écarté par task-203 et task-204 : toujours candidat
  à une passe dédiée, toujours hors de celle-ci.

## Definition of Done

- [ ] Build passes (0 errors) — Tests pass (0 failures)
- [ ] Test unitaire : un `cl_waiting` non nul sur **un seul** échantillon de la
      fenêtre ne désigne **pas** PgBouncer comme ressource épinglée
- [ ] Test unitaire : un `cl_waiting` non nul **soutenu** le désigne toujours
- [ ] Test unitaire : le transitoire est **mentionné** dans le rapport même quand
      il n'est pas retenu comme verdict (jamais de silence)
- [ ] Test unitaire : « Débit demandé vs délivré » calculé sur le plateau — sur
      la fixture du palier 486 req/s, le total lit **99,3 %** et non 85,1 %
- [ ] Test unitaire : un scénario **sans débit imposé** ne contribue pas au
      `dropped_iterations` de la garde de validité ; sur les données du 1er palier
      (4,6 % brut / 2,6 % hors `enrich`), le verdict porte sur 2,6 %
- [ ] Test unitaire : le reliquat non consommé d'un scénario fini est **écrit**
      dans le rapport
- [ ] Les 3 rapports de la campagne du 2026-07-29 régénérés depuis leur JSON
      archivé : les verdicts changent dans le sens attendu, et la ligne d'INDEX
      correspondante est recalculée
- [ ] `docs/loadtest.md` : les trois règles de conclusion sont écrites (quelle
      statistique, pourquoi celle-là)

## Manual Test Plan

1. Aucun banc requis pour les 3 défauts : les JSON et le CSV d'échantillonnage de
   la campagne du 2026-07-29 sont dans `tests/loadtest-k6/reports/2026-07-29/`.
   ⚠️ **Ce répertoire est gitignoré** (`.gitignore:386` — seul `INDEX.md` est
   versionné) : les données n'existent que sur la machine de banc. **Premier geste
   de l'US** : promouvoir les fichiers nécessaires en fixtures versionnées sous
   `tests/loadtest-k6/fixtures/`, sinon les tests de la DOD sont injouables
   ailleurs. Au minimum `mixed-mssante-60vu-201816.json` (palier 486, le cas du
   dénominateur), le JSON du 1er essai (garde de validité vs `enrich`) et un
   extrait du CSV portant les transitoires `cl_waiting`.
2. Régénérer le rapport du palier 486 req/s :
   ```bash
   tests/loadtest-k6/report.sh tests/loadtest-k6/reports/2026-07-29/mixed-mssante-60vu-201816.json --expected 100
   ```
3. Vérifier dans le `.md` : (a) la table « Débit demandé vs délivré » affiche
   ~99 % et non ~85 % ; (b) la ressource épinglée n'est plus PgBouncer, le
   transitoire est mentionné ; (c) la section « Validité » raisonne hors `enrich`.
4. Rejouer les auto-tests du harnais : `tests/loadtest-k6/selftest.sh`.
