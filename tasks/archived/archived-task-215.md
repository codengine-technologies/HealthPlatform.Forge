# todo-task-215.md — Contre-épreuve de la voie d'écriture : le coût mesuré est-il celui du correctif ou celui du banc ?

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: task-214 (**doit être mergée**) — sans elle la table par
opération reste aveugle et la contre-épreuve ne mesurerait rien de plus que le
tir du 2026-08-01 ; task-213 (mergée) — c'est son correctif qui est jugé
**Priorité**: **1** — un correctif est sur `develop` dont la vérification a
rendu NON sur trois critères de non-régression, et personne ne sait si le NON
vient du correctif ou du banc.

> **Cette US ne produit pas de code de production. Elle produit une décision.**
> Trois issues possibles, toutes acceptables : garder la voie d'écriture,
> l'assortir d'un interrupteur, la retirer. Ce qui n'est pas acceptable est de
> la laisser sur `develop` sans avoir tranché.

## Objective

Établir si la dégradation des chemins de lecture mesurée le 2026-08-01 après
task-213 (`read_list` +82 %, `folders_warm` +63 %) est **imputable à la voie
d'écriture** ou à la **configuration du banc**, et décider du sort de la voie
d'écriture en conséquence.

## L'état des lieux, en trois faits

1. **Le « NON » sur les lectures est mesuré et acquis.** Tir
   `report-mixed-mssante-60vu-164903.md`, iso-conditions avec la baseline
   `…-150216.md` : `read_list` p95 638,9 → 1 162,1 ms, `folders_warm` p95
   469,1 → 764,2 ms, contre une marge de non-régression de 20 %.
2. **Le bénéfice, lui, n'a jamais été mesuré** — la table qui devait le juger ne
   couvrait qu'un appelant sur vingt-et-un (task-214). Le gain visible sur
   `send` (p95 35,1 → 28,8 s, ratio 3,3 → 2,26) est une mesure **client**, qui
   mélange trois causes.
3. **La cause probable de la dégradation n'est pas la voie d'écriture
   elle-même mais son coût d'infrastructure** : elle double le plancher de
   sessions IMAP du banc (2 500 → 5 002 mesurées), soit 2 500 processus Dovecot
   de plus, sur un hôte où l'infra du banc partage le CPU des réplicas
   (`loadtest-dovecot` à 2,54 cœurs en pointe). Un déploiement dédié ne paierait
   pas forcément ce prix — **la conclusion du 2026-08-01 vaut pour cet hôte**.

## Le protocole — et pourquoi celui-là

Trois tirs, **même hôte, même configuration de banc** (Dovecot `service imap` à
8000 et `imap-login` en high-performance, tels que `0d4d801` et `d57953f` les
ont posés), même profil `mixed` 500 praticiens / 60 VU / budget 882 req/s.

| Tir | Binaire | Ce qu'il isole |
|---|---|---|
| **A — témoin** | `develop` avec `ImapService.WriteLane` ramené sur `userContextInfo`, sur une **branche jetable** | Le banc actuel **sans** la voie d'écriture. C'est le terme qui manquait : la baseline `…-150216` a été tirée avant les changements de conf Dovecot |
| **B — courant** | `develop` tel quel (task-213 + task-214) | Le banc actuel **avec** la voie d'écriture, et cette fois **instrumenté** |
| **C — réplication** | comme B | Écarter la variance : deux tirs du 2026-08-01 séparés d'une heure ont donné 863,1 et 821,4 req/s de plateau |

**Pourquoi une branche jetable et pas un interrupteur.** Un interrupteur de
production posé pour les besoins d'une expérience de banc est un coût permanent
— une branche de code à maintenir et à tester — pour un usage unique. La
neutralisation tient en une ligne (`WriteLane => userContextInfo`) et la branche
est détruite après le tir.

**Pourquoi le témoin A est indispensable.** La baseline citée par le DOD de
task-213 (`…-150216.md`) a été tirée **avant** `0d4d801` (Dovecot à 8000). La
comparaison publiée le 2026-08-01 confond donc « effet de la voie d'écriture »
et « effet du changement de conf du banc ». A et B partagent tout sauf la ligne
en cause : c'est la seule comparaison qui isole le correctif.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que la dégradation est réelle en production.** Elle est
  mesurée sur un hôte où l'infra du banc consomme plus de CPU que l'application.
  Si A reproduit la dégradation, la voie d'écriture est **innocentée** et c'est
  la conf du banc qui l'explique.
- **Ne pas présumer que l'inverse innocente le banc.** Si A ne la reproduit pas,
  la voie d'écriture est coupable **sur cet hôte** — ce qui ne dit toujours pas
  ce qu'elle coûterait sur un déploiement dédié. L'écrire comme tel.
- **Ne pas conclure sur le débit.** Aucun des deux tirs du 2026-08-01 n'est
  valide (8,9 % et 8,0 % d'abandons) : seules les **latences** sont lisibles par
  la règle du harnais. Si les tirs de cette task sont eux aussi invalides, la
  conclusion porte sur les latences et le dit.
- **Ne pas rejouer l'erreur de protocole du 2026-08-01.** L'ordre est
  **échauffement → purge → tir**. L'ordre inverse fait consommer par
  l'échauffement la bande d'UID de l'enrichissement : le verrou n'est alors pas
  pris, et le tir ne mesure pas la contention sous test (première tentative,
  `…-162121.md`, chiffres flatteurs et sans valeur).
- **Ne pas présumer que l'instrumentation suffit à conclure.** Vérifier
  **d'abord**, sur le rapport de B, que la table par opération porte au moins
  deux opérations dont `AppendToSent`, et que la table des voies porte un taux
  d'écriture non nul. Sans cela le tir B ne vaut pas mieux que celui d'hier.

## Contenu attendu

1. **Les trois tirs**, rapports archivés dans `reports/{date}/` et lignes
   ajoutées à `INDEX.md`.
2. **Une table de comparaison A / B / C** sur les grandeurs du DOD de
   task-213 : `send` p95 et ratio moyenne/médiane, `read_list` p95,
   `folders_warm` p95, attente et détention `imap_session` **par opération**,
   acquisitions par voie, sessions Dovecot, débit plateau et validité.
3. **La décomposition du ×5,5 sur `send`**, que task-213 laissait explicitement
   en réserve : ce qui revient à l'attente de verrou, ce qui revient au passage
   de 200 à 500 praticiens, ce qui revient à l'archivage devenu réel
   (`118c3f4`).
4. **Une décision écrite**, avec son argument : garder / interrupteur / retirer.
   Si « retirer », l'US de retrait est créée dans la foulée.
5. **Mise à jour de la ligne task-213 dans `Docs/epics/E015`** — elle porte
   aujourd'hui « mesure conduite et non concluante ».

## Hors scope

- Toute modification du code de production. Si la décision est « retirer » ou
  « interrupteur », c'est une US distincte.
- La campagne de confirmation groupée des autres correctifs (task-205, 202,
  206, 211, 201) — elle a son propre périmètre, même si elle peut réutiliser
  les tirs B et C.

## Definition of Done

- [ ] Les trois tirs sont archivés et indexés, avec leur verdict de validité
- [ ] Le tir B porte une table par opération à **au moins deux opérations**,
      dont `AppendToSent`, et un taux d'acquisitions non nul sur la voie
      d'écriture — **contrôle préalable, sans quoi les tirs ne comptent pas**
- [ ] La table de comparaison A / B / C est écrite dans le `## Bench log`
- [ ] Le ×5,5 sur `send` est décomposé, ou l'impossibilité de le décomposer est
      écrite avec sa raison
- [ ] La décision sur la voie d'écriture est écrite avec son argument
- [ ] `Docs/epics/E015` reflète la décision
- [ ] Aucune conclusion de capacité tirée d'un tir invalide

## Manual Test Plan

**Monter le banc** (skill `loadtest-skill`, profil `loadtest`) :

```powershell
cd Api/Mail/src/AppHost
$env:MSS_LOADTEST = "1"
dotnet run
```

**Pour le tir A**, sur une branche jetable :

```bash
cd Api/Mail
git checkout -b throwaway/task-215-control origin/develop
# neutraliser la voie d'écriture : ImapService.WriteLane => userContextInfo
dotnet build HealthPlatform.Api.Mail.sln
```

**Chaque tir**, dans cet ordre — l'ordre est le protocole :

```bash
cd Api/Mail/tests/loadtest-k6
./run.sh mixed          # échauffement
./reset-state.sh        # PURGE, APRÈS l'échauffement
USERS=500 VUS=60 DURATION=3m ./run.sh mixed
python report.py <run-id>
```

**Ce que l'humain doit voir**, dans le rapport de B :

- section « Verrou de session `imap_session`, par opération » : au moins deux
  lignes, dont `AppendToSent` ;
- table « Voie | Acquisitions /s » : `write` non nul ;
- section « Ressources & télémétrie » : le nombre de sessions IMAP Dovecot, à
  comparer entre A et B — c'est lui qui porte l'hypothèse.

**Données de test** : 100 % synthétiques (boîtes `loadtest-*`). Aucune donnée de
santé, aucun INS.

**Après les tirs** : détruire la branche `throwaway/task-215-control`.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville — messagerie MSSanté du praticien.
- **Vague Ségur** : hors vague — mesure de performance interne.
- **Exigences DSR honorées** : aucune. L'US ne modifie aucun comportement.
- **INS** : non manipulée. **Authentification PS** : inchangée.
- **Habilitations** : aucune clé de verrou touchée.
- **Tracé PGSSI-S** : aucun nouvel évènement. Les tirs produisent des métriques
  techniques sur données synthétiques.
- **Hébergement HDS** : non — banc de charge.
- **AIPD / impact RGPD** : inchangé.

## Branches
- `api-mail` (pushed) : chore/task-215-write-lane-counter-test — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/chore/task-215-write-lane-counter-test
- `dtos-mss` : non branché — US de mesure, aucun contrat, aucun code de production

> **Mode** : US de mesure. `/develop` n'écrit pas de code de production ; le
> livrable est le `## Bench log` (trois tirs), la décomposition du ×5,5 sur
> `send`, et une décision écrite. Seul artefact versionné attendu :
> les lignes ajoutées à `tests/loadtest-k6/reports/INDEX.md`.

## Bench log — campagne du 2026-08-02

Trois tirs, **même hôte, même configuration de banc, mêmes paramètres**
(`USERS=500 VUS=60 MESSAGES_PER_USER=100 SESSION_ROTATION=0.001
VU_TAIL_FACTOR=8 RPS=980 DURATION=3m LATENCY_PROFILE=mssante`, aucune surcharge
`ITER_SECONDS_*`), protocole **échauffement → purge → tir** pour chacun.

| Tir | Binaire | Rapport |
|---|---|---|
| **A — témoin** | `develop` avec `ImapService.WriteLane => userContextInfo` (branche jetable, détruite depuis) | `report-mixed-mssante-60vu-162811.md` |
| **B — courant** | `develop` (`b7fd92b`, task-213 + task-214) | `report-mixed-mssante-60vu-160614.md` |
| **C — réplication** | idem B | `report-mixed-mssante-60vu-161627.md` |

### La table qui manquait — contrôle préalable du DOD : ✅ PASSÉ

`imap_session`, par opération. **Cinq lignes** au lieu d'une, sur les trois tirs.

| Opération | A — attente p95 | B — attente p95 | C — attente p95 |
|---|---|---|---|
| **`AppendToSent`** | **4,345 s** | **0,005 s** | **0,005 s** |
| `EnrichEmails` | 0,239 s | 2,425 s | 0,005 s |
| `GetEmailContent` | 0,975 s | 2,275 s | 0,147 s |
| `GetFolders` | 3,683 s | 3,793 s | 1,773 s |
| `ProcessEmailUid` | 0,837 s | 2,305 s | 2,465 s |

| Voie | A | B | C |
|---|---|---|---|
| `read` | **200,89 /s** | 61,27 /s | 65,86 /s |
| `write` | **absente** | **103,48 /s** | **102,08 /s** |

La voie d'écriture est absente de A et exercée à ~102 acq/s dans B et C : **la
neutralisation du témoin est prouvée par la mesure**, pas supposée.

### Résultat 1 — la voie d'écriture fait exactement ce pour quoi elle existe

**L'attente d'archivage passe de 4,345 s à 0,005 s au p95** — un facteur ~870,
reproduit à l'identique sur B et C. C'est la première mesure du **bénéfice** de
task-213 ; le tir du 2026-08-01 ne pouvait pas la produire.

Le mécanisme décrit par task-213 est par ailleurs **confirmé par le témoin** :
sans voie d'écriture, l'archivage attend bien plusieurs secondes derrière les
lectures du même praticien.

### Résultat 2 — et pourtant l'envoi ne s'améliore pas ; il se dégrade

| `send` | A (témoin) | B | C |
|---|---|---|---|
| médiane | 2 559 ms | 2 410 ms | 2 336 ms |
| moyenne | 3 424 ms | 3 632 ms | 3 983 ms |
| **p95** | **7 874 ms** | 10 439 ms | 12 573 ms |
| **moyenne / médiane** | **1,34** | 1,51 | 1,71 |
| n | 17 267 | 16 780 | 16 857 |

Le témoin est **meilleur sur les deux critères du DOD de task-213** : p95 sous
10 s (7,87 s) et ratio sous 2 (1,34). Les tirs porteurs de la voie d'écriture
**échouent** sur le p95 (10,4 et 12,6 s) et ont un ratio plus élevé.

**Ce que la voie d'écriture retire au verrou, elle le repaie ailleurs.** La
détention d'`AppendToSent` monte de 3,974 s (A) à 4,557 s (B) et 5,287 s (C) :
l'archivage ne fait plus la queue, mais il ouvre et sert **une seconde connexion
IMAP par praticien**, et cela coûte au moins autant que l'attente supprimée.

### Résultat 3 — la dégradation des lectures n'est PAS imputable au correctif

C'était le « NON » du 2026-08-01, et c'est la question que le témoin existe pour
trancher.

| p95 | A (témoin) | B | C |
|---|---|---|---|
| `read_list` | 4 656 ms | 1 555 ms | 4 933 ms |
| `folders_warm` | 1 313 ms | 1 342 ms | 1 218 ms |
| `read_content` | 914 ms | 587 ms | 779 ms |
| `search` | 2 756 ms | 1 888 ms | 2 633 ms |

**Le témoin se dégrade autant, et sur `read_list` davantage que B.** Sur
`folders_warm`, les trois tirs sont indiscernables (1 218 à 1 342 ms). La
dégradation attribuée à la voie d'écriture le 1ᵉʳ août **ne se reproduit pas** :
elle relevait de la configuration du banc — la baseline `150216` avait été tirée
**avant** `0d4d801` (Dovecot `service imap` à 8000) et `d57953f` (`imap-login`
high-performance) — et de la variance, `read_list` variant d'un facteur 3 entre
B et C à binaire identique.

### Résultat 4 — le débit ne distingue pas les trois tirs

| Débit plateau | A | B | C |
|---|---|---|---|
| | 791,1 req/s | 796,8 req/s | 802,7 req/s |

Écart total **1,5 %**, monotone dans l'ordre A < B < C — c'est-à-dire l'ordre
chronologique, pas celui du binaire. Aucun effet mesurable.

### Validité

Aucun des trois tirs n'est valide au sens de la garde (abandons 11,9 % / 11,0 %
/ 10,5 %, seuil 1 %). **Les latences restent lisibles** — c'est sur elles que
portent les conclusions — **le débit ne l'est pas**, et la ligne du Résultat 4
n'est donnée que pour constater l'absence d'écart, pas comme mesure de capacité.
Les trois tirs partagent le même taux d'abandon à 1,4 point près, donc la
comparaison A/B/C est faite à harnais identique, ce que la garde autorise
explicitement.

### Décomposition du ×5,5 sur `send` (DOD 4)

Le DOD de task-213 laissait en réserve trois causes confondues. Deux sont
maintenant séparées, la troisième ne peut pas l'être :

| Cause | Verdict |
|---|---|
| **Attente de verrou** | **Écartée** — 4,345 s → 0,005 s, et l'envoi ne s'améliore pas pour autant |
| **Archivage devenu réel** (`118c3f4`) | **Confirmée** — les baselines `send` d'avant le 2026-08-01 mesuraient un envoi dont l'archivage échouait en `FolderNotFoundException`, donc plus court. Elles ne sont pas comparables ; c'est écrit dans le `loadtest-skill` depuis task-214 |
| **Passage de 200 à 500 praticiens** | **Non séparable ici** — les trois tirs sont tous à 500. Il faudrait un quatrième tir à 200, hors périmètre de cette task |

### Écart de protocole relevé dans la campagne du 2026-08-01

La vérification de task-213 se déclare *iso-conditions* avec
`report-mixed-mssante-60vu-150216.md`. Les deux `run context` divergent :
**baseline `duration "2m"`, vérification `duration "3m"`**. La comparaison
publiée n'était donc pas iso-conditions sur la durée de plateau. Les trois tirs
de cette campagne sont tous à `3m`, donc comparables **entre eux** — ce qui est
la comparaison dont dépend la décision.

### Manque de protocole assumé

**L'échantillonneur (`observe.ps1`) n'a pas été lancé** : aucun CSV
`observe-*.csv` pour ces trois tirs, donc **pas de comptage des sessions IMAP
Dovecot**, que le plan de test manuel demandait comme porteur de l'hypothèse. Ce
qui le remplace, en moins direct mais suffisant pour la décision : la table des
voies, qui compte 102 acquisitions/s sur la voie d'écriture dans B et C et zéro
dans A — l'attribution est faite, seul l'ordre de grandeur absolu du surcoût de
sessions manque.

### Analyse Seq (findings)

- **Erreurs / Fatal sur la fenêtre : 2**, toutes deux
  `ClientResultException: maximum input length is 8192 tokens` sur
  `EmailEmbeddingService` — défaut **connu et intermittent** de task-196, sans
  rapport avec cette campagne.
- **`Failed to parse entity headers` / `Error extracting IHE-XDM` : 0** — pas de
  régression du fetch partiel, Dovecot sert correctement `BODY[part]`.
- **`FolderNotFoundException` : 0** — l'archivage aboutit réellement, acquis de
  `118c3f4` confirmé.
- **`SecurityTokenMalformedException` : 0** — acquis de task-206 confirmé.
- **`enrich_short_circuited` : 0** sur les trois tirs (127, 152 et 119 lots
  réellement parsés) — la purge a bien fonctionné, la pipeline CDA a tourné.

### ⚠️ Défaut hors périmètre — un appel Redis SYNCHRONE sur le chemin de requête

`dotnet_exceptions_total` sur la campagne : **7 155 `RedisTimeoutException` +
4 474 `RedisConnectionException`**. La trace nomme la cause :

```
StackExchange.Redis.RedisTimeoutException: Timeout performing HMGET (5000ms) …
  sync-ops: 32879 …
  at StackExchange.Redis.RedisBase.ExecuteSync[T](…)
  at Microsoft.Extensions.Caching.StackExchangeRedis.RedisCache.GetAndRefresh(…)
  at HealthPlatform.Host.Sdk.Services.ResilientCacheService.TryGet[T](String key)
```

`ResilientCacheService.TryGet<T>` est **synchrone** et appelé depuis
`MailController.GetEmailAsync` : il parque un thread du pool jusqu'à **5
secondes** sous charge. C'est **exactement la classe de défaut que task-205 a
retirée** du chemin `read_list` (`IMailStore.GetFolder` synchrone), à ceci près
qu'elle vit dans le repo **`sdk`** et non dans `api-mail`. Candidat sérieux pour
expliquer les p95 de `read_content` et les files ThreadPool observées
(543 éléments sur un réplica du tir A). **À instruire dans une US dédiée.**

## Décision (DOD 4)

**Retirer la voie d'écriture de task-213.**

Trois éléments l'établissent, et le premier est celui qui aurait pu la sauver :

1. **Elle marche.** L'attente d'archivage tombe de 4,345 s à 0,005 s, mesuré
   deux fois. Le mécanisme décrit par task-213 était juste, et le témoin le
   confirme en le reproduisant.
2. **Elle ne sert à rien pour le praticien.** Ce qui compte est le temps que
   dure un envoi, et il est **meilleur sans elle** : p95 7,9 s contre 10,4 et
   12,6 s, ratio de file 1,34 contre 1,51 et 1,71. Le témoin **satisfait les
   deux critères du DOD de task-213**, que les tirs porteurs du correctif
   manquent. Une attente supprimée qu'on repaie intégralement en ouverture de
   connexion n'est pas un gain, c'est un déplacement.
3. **Elle coûte.** Une connexion IMAP de plus par praticien qui écrit — le
   plafond réel n'est pas la mémoire mais la **limite de connexions par boîte
   imposée par l'opérateur MSSanté**, point de vigilance que task-213 avait
   elle-même inscrit dans `ForWriteLane` et laissé à confirmer au banc.

**Ce qui n'est PAS retiré** : l'étiquette `operation`, l'étiquette `lane` et
l'instrumentation de task-214. Ce sont elles qui ont permis de trancher, et
elles servent à toute mesure ultérieure de verrou.

**Ce que le retrait ne fait pas** : il ne rétablit pas un défaut. Le problème que
task-213 visait — un envoi sur vingt au-dessus de trente secondes — **n'existe
plus sur le banc actuel sans elle** (p95 7,9 s), parce que les plafonds du banc
levés depuis (Dovecot `service imap` à 8000, `imap-login` high-performance,
dossiers `Sent`/`Drafts`/`Trash`) ont retiré la contention qui le produisait. Le
correctif répondait à une mesure prise sur un banc bridé.

**Réserve à porter au retrait** : cette conclusion vaut **pour cet hôte**, où
l'infrastructure de test partage le processeur des réplicas. Sur un déploiement
dédié, la seconde connexion pourrait coûter moins et le verdict s'inverser. Ce
qui la rend malgré tout actionnable : les deux termes de la comparaison ont subi
ce biais **à l'identique**, et c'est un écart **entre eux** qui est mesuré.

**US de retrait** : `todo-task-216.md`.

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/143 — label `awaiting-human-merge`
- `dtos-mss` : non branché (US de mesure)

## Suite
- `todo-task-216.md` — retrait de la voie d'écriture, **à arbitrer par l'humain
  avant lancement** : c'est un compromis, pas un fait.
- Défaut hors périmètre à instruire : `ResilientCacheService.TryGet<T>`
  synchrone (repo `sdk`), 11 600 exceptions Redis sur la campagne.

## Merged
- `api-mail` : **598821c** — squash de la PR #143, mergée le 2026-08-02
- `dtos-mss` : non branché (US de mesure)

Ref distant supprimé ; **branche locale conservée**.

> **Suite** : `todo-task-216.md` (retrait de la voie d'écriture, à arbitrer) et
> `todo-task-217.md` (I/O synchrones du SDK), cette dernière traitée en premier
> sur décision de l'humain.
