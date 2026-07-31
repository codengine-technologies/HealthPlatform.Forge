# todo-task-209.md — Le dimensionnement des VUs suppose des latences que le banc ne produit plus

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: task-203 (qui a introduit le modèle), task-204 (l'escalier qui l'a mis en défaut)

> **Origine** : escalier de capacité du 2026-07-29 (task-204). Deux campagnes ont
> été nécessaires — la première a été jetée — parce que le modèle de
> dimensionnement sous-provisionne les pools dès que la latence réelle s'écarte de
> ses constantes de référence.

## Objective

Que le harnais cesse de produire des abandons qu'on impute à l'application, et
qu'il **dise** quand son propre modèle est démenti par la mesure.

## Le défaut

`lib/vu-sizing.js` dimensionne chaque pool par la loi de Little à partir de
`REFERENCE_ITERATION_SECONDS`, constantes **mesurées le 2026-07-27**. Écart
constaté le 2026-07-29, même scénario, même population :

| Sous-scénario | Référence du modèle | Mesuré à 486 req/s | Mesuré à 972 req/s | Écart au pire |
|---|---|---|---|---|
| `read` (list + content) | **0,16 s** | 0,41 s | **1,65 s** | **×10** |
| `folders` | 0,06 s | 0,05 s | 0,17 s | ×2,8 |
| `search` | 0,33 s | 0,24 s | 0,66 s | ×2,0 |
| `send` | 1,30 s | 1,18 s | 1,70 s | ×1,3 |

Le facteur de queue (`DEFAULT_TAIL_FACTOR = 4`) est censé absorber la variance,
pas un facteur 10 sur la moyenne. Conséquences mesurées :

- **1re campagne** (`tailFactor` par défaut) : 4,6 % d'abandons **au premier
  palier**, dont 1 076 sur `folders` et 763 sur `read`. Campagne jetée.
- **2e campagne** (`VU_TAIL_FACTOR=8`) : paliers 486 et 630 valides (0,67 % et
  0,74 %), puis abandons croissants **concentrés sur `read`** (783 → 4 916 →
  9 960), jusqu'à 7,4 % au palier 972.

**La cause de l'écart est double, et l'ordre compte.** D'abord structurelle : les
constantes ont été mesurées avec des `read` servis **depuis la base** (après
enrichissement), alors qu'une campagne d'escalier **purge les tables entre
paliers** — condition nécessaire pour que les `enrich` ne court-circuitent pas.
`read` part donc sur IMAP, et rien dans le harnais ne dit que ces deux exigences
se contredisent.

Ensuite — et c'est ce qui interdit la correction naïve — **au-delà du genou la
latence n'est plus une propriété du scénario mais du serveur qui congestionne**.

> ### ⚠️ Élargir les pools AGGRAVE le tir — mesuré, ne pas re-débattre
>
> Expérience de discrimination du 2026-07-29, budget identique de 882 req/s, seul
> `VU_TAIL_FACTOR` change (8 → 16) :
>
> | | `tail=8` | `tail=16` |
> |---|---|---|
> | Débit délivré | 824,8 req/s | **716,4** (−13 %) |
> | Abandons | 4,21 % | **13,49 %** |
> | p95 | 1 309 ms | **6 766 ms** |
> | `read_list` moy | 714 ms | **3 606 ms** |
> | File ThreadPool par réplica | 136/93/13/10/7 | **406/951/579/648/813** |
>
> Plus de concurrence cliente → **moins** de débit. Au-delà du genou, agrandir le
> pool ne « libère » rien : il alimente une file bloquante côté serveur
> (task-205). Le harnais ne doit donc pas chercher à annuler les abandons par le
> dimensionnement — il doit **dire lequel des deux mécanismes** les produit.

⚠️ **Le piège est celui que task-203 a créé en le corrigeant** : un pool
sous-dimensionné produit « un tir invalide qui a l'air valide » — et ici, mieux : un
tir dont l'invalidité est **imputée à l'application** (« la charge nominale n'a
jamais été appliquée ») alors qu'elle vient du client. C'est la même erreur
d'attribution que task-204 combat, d'un cran en amont.

## Contenu attendu

1. **Fermer la boucle sur la mesure** : dimensionner sur une latence **observée**
   plutôt que sur une constante figée — au minimum une surcharge par variable
   d'environnement (`ITER_SECONDS_READ=…`) qui manque aujourd'hui, au mieux une
   phase d'échauffement courte qui mesure puis dimensionne.
2. **Rendre le démenti visible** : en fin de tir, comparer la latence réelle par
   sous-scénario à celle utilisée pour le plan et **écrire** l'écart. Un écart > 2×
   doit apparaître dans le rapport comme cause candidate des abandons, à côté du
   verdict de validité — pas à la place, mais jamais en silence.
3. **Rafraîchir les constantes** avec les mesures du 2026-07-29, en **nommant les
   conditions** de mesure (tables purgées ou non — c'est ce qui change tout pour
   `read`).
4. **Documenter la contradiction** purge / dimensionnement dans
   `docs/loadtest.md` et dans le skill `loadtest-skill`, avec la conduite à tenir.

## Hors scope

- Les règles de conclusion du rapport (task-208).
- Le facteur limitant applicatif (task-205) — c'est lui qui fait monter la latence
  réelle ; cette task ne corrige que la façon dont le harnais y réagit.

## Definition of Done

- [ ] Build passes (0 errors) — Tests pass (0 failures)
- [ ] Test unitaire : une surcharge de latence par sous-scénario est prise en
      compte par le plan (pool dimensionné en conséquence)
- [ ] Test unitaire : un écart > 2× entre latence planifiée et latence mesurée est
      **écrit** dans le rapport, avec le sous-scénario nommé
- [ ] Test unitaire : sur les données du palier 972 req/s de la campagne
      (`read` planifié à 0,16 s, mesuré à 1,65 s), le rapport nomme `read` comme
      cause candidate des 7,4 % d'abandons
- [ ] Les constantes de référence sont à jour et **leurs conditions de mesure sont
      écrites** dans le module
- [ ] **Le rapport DISTINGUE les deux causes d'abandon** — c'est le cœur de la
      task, et l'expérience ci-dessous interdit de se contenter d'élargir les
      pools : « pool client épuisé alors que le serveur répond dans les temps »
      (dimensionnement) vs « le serveur ralentit, la concurrence cliente
      s'accumule » (congestion serveur). Test unitaire sur les deux jeux de
      données de la campagne
- [ ] **Mesure au banc** : au palier 756 req/s, le rapport nomme laquelle des deux
      causes produit ses 1,15 % d'abandons, et l'argumente par un chiffre
      (latence planifiée vs mesurée, file ThreadPool serveur)
- [ ] `docs/loadtest.md` + `loadtest-skill` : la contradiction purge /
      dimensionnement est documentée

## Manual Test Plan

1. Sans banc : `tests/loadtest-k6/selftest.sh` (les nouveaux tests portent sur des
   fixtures, dont celles de la campagne du 2026-07-29).
   ⚠️ **`tests/loadtest-k6/reports/` est gitignoré** (`.gitignore:386`) : les JSON
   de la campagne n'existent que sur la machine de banc. Promouvoir en fixtures
   versionnées ceux dont la DOD a besoin — au minimum les paliers 882 et 972 req/s
   aux deux `VU_TAIL_FACTOR` (8 et 16), qui portent la comparaison
   « dimensionnement » vs « congestion serveur ».
2. Avec banc, pour la DOD de mesure : monter le banc, 200 praticiens re-câblés,
   purger les tables, puis
   ```bash
   BYPASS_KEY=loadtest-local-only USERS=200 MESSAGES_PER_USER=100 \
   SESSION_ROTATION=0.001 RPS=840 ENRICH_SHARE=0.05 \
     tests/loadtest-k6/run.sh mixed --env VUS=60 --env DURATION=3m
   ```
   sans forcer `VU_TAIL_FACTOR` : le plan doit se dimensionner seul et le tir sortir
   valide.
3. Lire la section « Validité du tir » et la nouvelle comparaison
   latence planifiée / latence mesurée.
