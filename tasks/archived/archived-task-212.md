# todo-task-212.md — « Ressource épinglée » juge encore sur un max : deux familles de candidats sur trois désignent un transitoire

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: task-208 — **satisfaite** (mergée le 2026-07-31, PR #133), qui a posé la règle de présence soutenue sur **une** famille de candidats
**Priorité**: **1** — Instrument, bloquant pour la campagne de capacité (phase 2)
> Sans ce correctif, chaque palier de la campagne risque de désigner une ressource épinglée sur son transitoire d'ouverture — soit exactement le verdict que la campagne doit produire honnêtement.

> **Origine** : soak de 30 min conduit le 2026-07-31 après le merge de task-205.
> Premier tir long de l'EPIC, et **premier tir formellement valide** de la
> journée (0,6 % d'abandons, VUs 679/704 sous plafond). Il a rendu un verdict
> faux que 3 minutes de tir n'auraient pas permis de démasquer.

## Objective

Que le verdict « ressource épinglée » repose sur une **présence soutenue** pour
**toutes** les familles de candidats, et non pour une seule.

task-208 a posé la règle — `PGBOUNCER_WAITING_SUSTAINED = 0.25`, la part des
échantillons de la fenêtre portant une attente non nulle. Elle ne l'a appliquée
qu'à PgBouncer. Les deux autres familles jugent toujours sur un `max`.

## La preuve

Soak de **30 minutes** à 625 req/s délivrés, 200 praticiens, 1 125 056 requêtes,
0,02 % d'erreurs, 0 mélange. Quatre réplicas sur cinq à une file ThreadPool
maximale de **≤ 8**. Le cinquième :

```
replica 46192 : max=244
                > 50 sur 2 échantillons / 75  →  2,7 % de la fenêtre
                fenêtres concernées : 20:55:32 et 20:56:02
                (le tir a démarré à 20:54:5x — c'est la première minute)
```

Verdict rendu par le rapport :

> **Ressource épinglée : file ThreadPool du réplica `DESKTOP-DEV-X2C-46192`** —
> 244.0 % de sa borne au débit maximal atteint.

Sur un tir de trente minutes plat à ≤ 8 pendant vingt-neuf d'entre elles. Le
transitoire d'ouverture est présenté comme le facteur limitant du service.

## Le défaut, dans le code

`tests/loadtest-k6/report.py`, fonction `pinned_candidates` — **trois** familles
de candidats, **une seule** corrigée par task-208 :

| # | Famille | Statistique utilisée | État |
|---|---|---|---|
| 1 | **CPU** (conteneurs + processus) | `entry["max"]` | ❌ max |
| 2 | **PgBouncer** `cl_waiting` | `waiting["sustained"]` | ✅ corrigé (task-208) |
| 3 | **File ThreadPool** | `queue_max` | ❌ max |

Et le commentaire de la famille 3 décrit une règle que le code n'applique pas :

```python
# File du ThreadPool au-delà de laquelle un réplica est déclaré congestionné. Même
# borne que `pinned_candidates` : une file durablement > 100 signe la famine de
# threads, pas une pointe.
THREADPOOL_QUEUE_CONGESTED = 100
...
"value": queue_max,
"ratio": queue_max / float(THREADPOOL_QUEUE_CONGESTED),
```

« durablement » et « pas une pointe » sont écrits ; `queue_max` est exécuté.
**Un commentaire qui décrit l'intention correcte à côté d'un code qui fait
l'inverse est pire qu'un commentaire absent** : il désarme la relecture.

## Pourquoi 3 minutes ne suffisaient pas à le voir

Sur une fenêtre de 3 min, un transitoire d'ouverture de 30 s représente **17 %**
de la fenêtre — il se confond avec le régime. Sur 30 min, il en représente
**1,7 %** et devient indiscutable. Tous les tirs de cet EPIC font 3 minutes.

Corollaire à consigner : **la durée de fenêtre change le verdict**. Une règle de
présence soutenue exprimée en *part d'échantillons* est robuste à cela, un `max`
ne l'est pas.

## Contenu attendu

### 1. Généraliser la présence soutenue

- Appliquer la même mécanique que `PGBOUNCER_WAITING_SUSTAINED` aux familles
  **CPU** et **file ThreadPool** : un candidat n'est retenu que si la part des
  échantillons au-delà de sa borne dépasse un seuil.
- **Un seuil unique et nommé** pour les trois familles plutôt que trois
  littéraux — c'est l'écart qui a produit ce défaut. Si une famille doit dévier,
  la déviation est justifiée en commentaire à côté de sa valeur.
- La valeur retenue (0,25 pour PgBouncer) est à **reprendre telle quelle** sauf
  argument mesuré : elle a été posée par task-208 sur la campagne du 2026-07-29
  (15 échantillons non nuls sur 230, tous dans les ~30 s d'ouverture).

### 2. Ne pas faire disparaître l'information

Un transitoire écarté du verdict **doit rester visible** dans le rapport —
task-208 l'exige déjà pour PgBouncer (« le transitoire est mentionné même quand
il ne déclenche pas le verdict »). Étendre cette garantie aux deux autres
familles : le lecteur doit pouvoir lire « pic à 244 sur 2,7 % de la fenêtre,
écarté du verdict » plutôt que ne rien voir du tout.

### 3. Corriger le commentaire de `THREADPOOL_QUEUE_CONGESTED`

Qu'il décrive la règle réellement appliquée.

### 4. Verrouiller par test

Sur le modèle des tests de task-208, avec un **témoin positif** (leçon de la
passe `/simplify` de task-205 — un scanner qui ne trouve plus rien annonce un
succès à vide) :

- un pic de file ThreadPool sur **un seul** échantillon de la fenêtre **ne**
  déclenche **pas** le verdict ;
- une file **soutenue** au-delà de la borne le déclenche **toujours** ;
- idem pour un pic CPU ;
- le transitoire écarté est **mentionné** dans le rapport ;
- **fixture issue du soak réel** du 2026-07-31 (244 sur 2/75) : le verdict rendu
  doit être « aucune ressource épinglée », pas « file ThreadPool ».

## Hors scope

- **Le seuil `THREADPOOL_QUEUE_CONGESTED = 100` lui-même** — c'est la borne, pas
  la statistique. Elle n'est pas en cause ici.
- **Les autres verdicts du rapport** (validité, débit demandé vs délivré) —
  traités par task-208.
- **Le fond d'erreurs 5xx à 0,1-0,3/s** relevé pendant le soak sur 22 minutes
  (0,02 % au total, sous le seuil) — non investigué, à ouvrir si la campagne le
  confirme.
- **Le pic lui-même** : pourquoi un réplica sur cinq monte à 244 à l'ouverture
  n'est pas l'objet de cette task. C'est un comportement de démarrage, il n'a pas
  de conséquence mesurée sur un tir long. À ouvrir séparément s'il se reproduit
  en régime.

## Definition of Done

- [ ] Build passes (0 erreur) — les auto-tests du harnais passent
      (`tests/loadtest-k6/selftest.sh`)
- [ ] Les **trois** familles de candidats jugent sur une présence soutenue
- [ ] **Un seuil unique nommé**, ou une déviation justifiée en commentaire
- [ ] Le commentaire de `THREADPOOL_QUEUE_CONGESTED` décrit la règle appliquée
- [ ] Un transitoire écarté reste **mentionné** dans le rapport (les 3 familles)
- [ ] Test : pic sur 1 échantillon → pas de verdict ; soutenu → verdict
- [ ] Test : **fixture du soak réel du 2026-07-31** (244 sur 2/75) → verdict
      « aucune ressource épinglée »
- [ ] Tests **constatés RED avant le correctif** (preuve dans le `## Develop log`)
- [ ] Le rapport du soak
      (`reports/2026-07-31/report-mixed-mssante-60vu-212459.md`) régénéré depuis
      son JSON ne désigne plus la file ThreadPool

## Manual Test Plan

1. `cd Api/Mail && tests/loadtest-k6/selftest.sh` → tout vert.
2. Régénérer le rapport du soak depuis son JSON archivé :
   ```bash
   export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'
   tests/loadtest-k6/report.sh \
     tests/loadtest-k6/reports/2026-07-31/mixed-mssante-60vu-212459.json --expected 100
   ```
3. Lire la section « Ressource épinglée » : elle doit dire **aucune**, et
   mentionner le pic de 244 comme transitoire (2,7 % de la fenêtre).
4. Contrôle de non-régression sur un tir réellement saturé — régénérer
   `reports/2026-07-31/report-mixed-mssante-60vu-162917.md` (file à 131/132/159
   **soutenue** au palier 882) : le verdict « file ThreadPool » doit être
   **conservé**. C'est le témoin positif : sans lui, on aurait pu rendre la règle
   si stricte qu'elle n'accuse plus jamais rien.

## Ce que le cycle autonome peut livrer, et ce qui restera dû

| Item | `/develop` | Banc / HAG |
|---|---|---|
| Généralisation de la règle + tests | ✅ | — |
| Régénération des deux rapports témoins | ✅ | — |
| Verdicts fiables sur la campagne de capacité | — | ✅ (phase 2) |

Aucun tir n'est nécessaire pour valider cette task : les deux rapports témoins
sont **déjà archivés** avec leur JSON, l'un sans saturation réelle, l'autre avec.
C'est une task entièrement vérifiable hors banc — rare dans cet EPIC.

## Branches

- `api-mail` (pushed) : `fix/task-212-pinned-resource-sustained` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-212-pinned-resource-sustained
- `dtos-mss` (pushed, auto-inclus) : `fix/task-212-pinned-resource-sustained` — aucun contrat attendu, la branche restera probablement sans commit
- `client-angular` / `client-mobile` : non listés (`Single frontend: true`), et absents du disque

### Pre-flight (2026-07-31)

Tous les repos forge présents sur `develop`, arbres propres. `client-mobile`
absent du disque (repo non cloné), `host` non autonome — écarts connus, non
bloquants.

**Coordination** : un autre agent travaille sur `fix/task-206-psc-token-speculative-parse`
(code applicatif `api-mail`). Cette task ne touche que
`tests/loadtest-k6/report.py` et ses tests — **aucun recouvrement de fichiers**.

## Develop log

- **Repos touched** : `api-mail` uniquement, et **Python uniquement** —
  `report.py` + un fichier de tests. Zéro `.cs`. `dtos-mss` : branche sans commit.
- **Commits** : `aa86a5a` (correctif + 6 tests), `ec530b6` (passe qualité).
- **Validation** : **96 auto-tests du harnais verts** ; build de contrôle
  api-mail **0 erreur / 0 warning**. Suite .NET non rejouée — aucun `.cs` au
  diff (même raisonnement que task-204).
- **`/sonar` non exécuté** : aucun delta C#, l'analyse porte sur la solution
  .NET. 6 min de scan sur un diff Python n'auraient rien mesuré.

### Ce que les tests ont attrapé, et que la relecture n'aurait pas vu

1. **Les deux cas négatifs passaient à vide au premier run.** `sustained`
   n'existait pas encore, la liste filtrée était donc vide — pour la mauvaise
   raison. Sans les deux **témoins positifs**, j'aurais pu croire la règle
   implémentée alors qu'elle n'existait pas. C'est la leçon de la passe
   `/simplify` de task-205, appliquée en amont cette fois.
2. **Une incohérence d'unités, attrapée par un test de task-208.** Ma première
   version comptait le CPU au-delà de **85 %** de la borne et la file ThreadPool
   au-delà de **100 %**. Le test `test_the_pinned_resource_is_named_when_one_is`
   (fixture à 96 sur une borne de 100) est tombé : à 96, la file était
   « épinglée » sur la hauteur et « transitoire » sur la durée. Le seuil de
   présence se mesure désormais au **même endroit** que le seuil d'épinglage.

### Écart de DOD — deux items non honorés, et pourquoi

Les items « régénérer les deux rapports témoins » **ne sont pas tenus**. Le banc
est arrêté : Prometheus est injoignable, et un rapport régénéré perd sa section
« Ressources & télémétrie ». Le rapport du soak régénéré dit bien « aucune
ressource épinglée » — **mais parce que la donnée a disparu**, pas parce que la
règle s'applique. Témoin inconcluant, non compté.

**Et j'ai détruit un artefact en le vérifiant** : la régénération a écrasé
`reports/2026-07-31/report-mixed-mssante-60vu-212459.md` avec une version privée
de sa télémétrie. Les rapports sont gitignorés — le rapport du soak est perdu en
local. Ses chiffres survivent dans la PR et dans ce log. Le second témoin
(`…-162917.md`) n'a volontairement pas été régénéré.

**Leçon** : ne jamais régénérer un rapport sans vérifier d'abord que Prometheus
répond. Le rapport déclare correctement « ⚠️ injoignable » — le mécanisme de
task-204 a fonctionné, c'est mon geste qui était faux.

### Adjacence signalée, non corrigée (règle 6)

`server_congestion_state` (`report.py:721`) juge lui aussi la file ThreadPool
sur un `max`, pour **attribuer les abandons**. Verdict différent (territoire de
task-209), même travers. À ouvrir séparément si la campagne le confirme.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/135
  — label `awaiting-human-merge`
- `dtos-mss` : aucun changement, branche sans commit, pas de PR

## Merged

**Mergé le 2026-08-01** par `/merge task-212 --i-tested` (HAG, règle 10 — le
humain a attesté avoir joué le Manual Test Plan).

| Repo | PR | Squash SHA | Suite |
|---|---|---|---|
| `api-mail` | [#135](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/135) (closed) | `1cc1ba9` | `develop` fast-forward, remote `fix/task-212-pinned-resource-sustained` supprimée, branche locale conservée |
| `dtos-mss` | — (aucune PR, branche sans commit) | — | branche remote vide supprimée, clone remis sur `develop` |

- **Gates franchies** : label `awaiting-human-merge` (pas
  `awaiting-us-completion`), aucun `CHANGES_REQUESTED`, CI PR verte
  (build ✓ 1m29s, `publish` skipped), `mergeable=MERGEABLE` /
  `mergeStateStatus=CLEAN`, arbres de travail propres sur les deux repos.
- **CI `develop` api-mail** : ✅ **verte** — run
  [30693497507](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/30693497507)
  sur `1cc1ba9` (`completed / success`), dans les 2 min de la règle 5.
- **Branche staging** : `forge/staging-task-176-196-20260728` **conservée** —
  hors range de task-212, et son run n'est pas drainé (tasks 176 → 196 encore
  actives).

### Dette reportée à l'ouverture de la campagne

Deux items de DOD restent dus, documentés dans le `## Develop log` et acceptés au
HAG : la **régénération des deux rapports témoins** n'a pas pu être conclusive
(banc arrêté, Prometheus injoignable) — et la régénération a **écrasé**
`reports/2026-07-31/report-mixed-mssante-60vu-212459.md`, gitignoré, perdu en
local (chiffres survivants dans la PR et le log). Le témoin positif
(`…-162917.md`, file soutenue) n'a volontairement pas été régénéré : la
non-régression sur un tir réellement saturé reste **verrouillée par test**, pas
par rapport régénéré.

Adjacence signalée non corrigée (règle 6) : `server_congestion_state`
(`report.py:721`) juge encore la file ThreadPool sur un `max` pour attribuer les
abandons — territoire de task-209, à ouvrir si la campagne le confirme.
