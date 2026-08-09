# todo-task-242.md — L'attente d'une connexion à la base accélère avec la population, et le verdict qui l'avait écartée est périmé

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: **task-240** (`todo`) — **coordination forte, pas blocage
technique**. Tant que `read_list` n'est pas ventilé par appel, on ne peut pas
relier une attente de connexion à un geste précis du médecin ; la mesure de
celle-ci sera donc plus pauvre. Peut démarrer avant, gagne à démarrer après.
**Priorité**: **2** — pas un incident aujourd'hui (les valeurs restent faibles),
mais **la seule grandeur du banc qui accélère au lieu de croître linéairement**.
C'est le candidat n°1 au prochain plafond, et c'est un des motifs du NO-GO 500.

## Objective

Savoir si le multiplexeur de connexions à la base devient le prochain facteur
limitant quand la population de praticiens grandit — et si oui, le dimensionner
sur une mesure, pas sur une intuition.

## La mesure — campagne K=1 du 2026-08-08 (`journey-certif-n200-142630`)

| Palier | Relevés `cl_waiting` non nuls | Valeur max |
|---|---|---|
| 50 médecins | 19 / 372 — **5 %** | — |
| 100 médecins | 27 / 370 — **7 %** | — |
| 200 médecins | 100 / 345 — **29 %** ⚠️ soutenu | **3** |

**Toutes les autres grandeurs résidentes croissent linéairement** avec la
population — sessions IMAP 116 / 245 / 483, backends Postgres 92 / 175 / 352.
Celle-ci **accélère** : elle quadruple entre 50 et 200 quand la population
quadruple, mais son taux de présence, lui, est passé de 5 % à 29 %.

⚠️ **Piège de lecture à connaître avant d'ouvrir le rapport** : la section
« Ressource épinglée » **écarte** PgBouncer en moyennant les trois paliers
(14 %, sous le seuil de présence soutenue de 25 %). C'est le **palier** qui
décide d'une conclusion de capacité, pas la moyenne — le palier 200 franchit le
seuil. Les deux affirmations coexistent dans le même document.

## Pourquoi le verdict précédent ne vaut plus

Un A/B a été conduit le **2026-08-05** sur exactement cette question
(`default_pool_size` 2 → 6) et a conclu **« écarté »** : latences identiques au
bruit près, `cl_waiting` amélioré mais jamais nul, +43 % de backends Postgres en
pointe.

**Ce verdict est périmé, et pour une raison précise** : il a été mesuré quand la
détention du verrou `imap_session` par l'enrichissement valait **7,44 s p95** —
autrement dit quand le verrou IMAP masquait la pression sur la base. task-239 a
supprimé ce masque (détention tombée à 0,49 s), et le profil de charge de la
base n'est plus le même.

C'est la **deuxième fois** dans cette EPIC qu'un verdict de banc est périmé par
une livraison ultérieure — task-233 avait déjà périmé l'A/B précédent du même
réglage. La leçon est constante : **un verdict de banc est daté par les
conditions qui le portaient**, pas seulement par ses paramètres.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer qu'il faut élargir le pool.** C'est le geste réflexe et le
  banc a déjà mesuré qu'il **aggrave** au-delà du genou (task-209 : même budget,
  pools élargis de 8 à 16 → débit −13 %, abandons ×3, p95 ×5). Élargir un pool
  devant un backend saturé dégrade ; il faut d'abord établir **qui** attend et
  **pourquoi**.
- **Ne pas présumer que 29 % de relevés non nuls = un plafond.** La valeur max
  est **3** : c'est une attente présente, pas une file qui déborde. Le sujet est
  la **tendance**, et ce que devient cette tendance à 500 — pas l'urgence.
- **Ne pas présumer que la cause est le dimensionnement.** Une attente qui
  accélère peut venir d'un nombre d'allers-retours SQL par requête qui augmente,
  d'une requête devenue plus lente, ou d'un chemin qui garde une connexion plus
  longtemps. **Regarder d'où viennent les emprunts** avant de toucher au pool.
- **Ne pas conclure d'un tir 500 local.** Au-delà de ~500 praticiens en local,
  Dovecot vole ~2,6 cœurs au système sous test et le chiffre devient un
  artefact connu. Si l'extrapolation exige une mesure à 500, elle exige le
  **mode distant** (task-221) — c'est un prérequis, pas une option.

## Definition of Done

- [ ] **La cause de l'accélération est établie**, pas supposée : d'où viennent
      les emprunts de connexion qui attendent, et pourquoi leur nombre croît
      plus vite que la population. Consignée avec les requêtes qui l'établissent.
- [ ] Projection chiffrée à 500 praticiens à partir des trois paliers mesurés,
      avec ses hypothèses **écrites** (et ce qui la rendrait fausse)
- [ ] Si un réglage change : A/B iso-conditions sur la lignée **actuelle**, un
      seul facteur, configuration effective **vérifiée avant le tir**
      (`SHOW CONFIG`) — le protocole durci du 2026-08-05
- [ ] Si rien ne change : le **dire** et écrire pourquoi, avec le seuil qui
      déclencherait une reprise du sujet
- [ ] La note de campagne de l'INDEX est mise à jour avec le verdict, et le
      verdict périmé du 2026-08-05 est **marqué comme tel** (il est encore lisible
      dans l'INDEX et pourrait être re-cité de bonne foi)
- [ ] Correctif du rapport : la section « Ressource épinglée » ne doit plus
      pouvoir écarter par la moyenne une ressource qu'un **palier** désigne —
      ou, si le comportement est voulu, l'écart doit être **écrit** dans le
      rapport plutôt que laissé à la sagacité du lecteur
- [ ] Aucune donnée de santé dans les métriques ou requêtes d'exploitation

## Manual Test Plan

- Monter le banc : skill `loadtest-skill`
- Pendant un tir `journey` (escalier 50/100/200), relever à intervalles réguliers :
  `SHOW POOLS` sur PgBouncer (`cl_active`, `cl_waiting`, `maxwait`) et
  `pg_stat_activity` sur Postgres **en direct** (le pooler ne se mesure pas
  lui-même)
- Vérifier que le nombre de backends réels reste sous le plafond du serveur, et
  que `maxwait` ne croît pas d'un palier à l'autre
- Lire la section « Ressource épinglée » du rapport **et** la table des coûts
  résidents par palier : les deux doivent raconter la même histoire

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — dimensionnement d'infrastructure interne
- **Exigences DSR honorées** : aucune — aucun changement fonctionnel
- **INS** : non applicable
- **Authentification PS** : inchangée
- **Habilitations** : non applicable — ⚠️ le cloisonnement « une base par
  praticien » ne doit pas être affaibli par un réglage de multiplexage : le
  pooler tourne en mode **transaction**, et toute évolution doit préserver
  l'isolation par base
- **Interop CI-SIS** : non applicable
- **MSSanté** : non applicable
- **Tracé PGSSI-S** : non applicable — métriques d'exploitation, aucune donnée
  patient dans les étiquettes ni dans les requêtes de diagnostic
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : le dimensionnement retenu devra être **transposable** à
  l'environnement HDS cible (le banc local n'est pas la cible) — à noter dans la
  conclusion
- **AIPD / impact RGPD** : inchangé

## Branches

- `api-mail` (pushed) : `feat/task-242-attente-connexion-base` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-242-attente-connexion-base
- `dtos-mss` (pushed, auto-inclus) : `feat/task-242-attente-connexion-base` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-242-attente-connexion-base

Pré-flight : `api-mail`, `client-blazor`, `dtos-mss`, `sdk`, `interop-cda` sur
`develop`. `client-mobile` : répertoire `Client/Mobile/` **absent du workspace**
— hors périmètre de cette US (aucune branche à créer), noté pour mémoire.

Dépendance `task-240` : le corps de cette US la déclare `todo`, elle est en
réalité **archivée** (mergée le 2026-08-08). La coordination annoncée est donc
acquise — `read_list` est ventilé par appel.

## Ce qui a été livré et mesuré (2026-08-08)

### Code (branche `feat/task-242-attente-connexion-base`)

1. **`report.py` — la moyenne du tir n'écarte plus ce qu'un palier désigne.** C'était
   le défaut nommé par la DOD. `pinned_candidates_by_palier` juge sur les fenêtres
   internes de l'escalier, `palier_designated_resources` publie ce que la moyenne
   dilue, et le verdict est rendu **sur le palier** avec l'écart **écrit**
   (« Désignée par un palier, écartée par la moyenne du tir »). Le CPU et l'attente
   cliente seuls sont jugés par palier — la file ThreadPool vient de Prometheus, dont
   les payloads couvrent le tir entier et ne sont donc pas rattachables à un palier.
   Deux garde-fous : la porte de task-208 reste fermée (témoin négatif : un
   transitoire d'ouverture répété à chaque palier ne désigne rien) et une ressource
   déjà épinglée globalement n'est pas dupliquée. **12 tests neufs**, suite complète
   **233 verte**.
2. **`observe.ps1` — `maxwait` relevé**, la *profondeur* de la file là où
   `cl_waiting` n'en disait que la *présence*. Agrégation par MAX entre pools
   (sommer des attentes concurrentes n'a pas de sens physique) et garde de colonnes
   séparée, pour qu'un pooler sans `maxwait_us` ne fasse pas retomber à zéro
   `cl_waiting`, déjà acquis.
3. **`observe.ps1` + `report.py` — attente VENTILÉE** entre bases **praticien**
   (`u_9…`) et pool de **maintenance**. C'est la ventilation qui a rendu la grandeur
   lisible : le total sommait deux phénomènes sans rapport.
4. **INDEX** — le verdict du 2026-08-05 est **marqué périmé** avec sa raison, et la
   note de campagne du tir est écrite.

### Le tir — `journey-lot-n200-205342`, iso-conditions

Escalier 50/100/200 × 32 min, K=1, 200 boîtes × 247 messages **re-seedées à vierge**
(49 400 messages, read-back vérifié), 500 bases purgées avant tir. 133 214 requêtes,
**0,013 % d'erreurs**, 0 abandon, 0 mélange, verify **PASS**.

### DOD — la cause, établie et non supposée

**L'attente existe, elle accélère, et elle ne coûte presque rien sur le chemin du
médecin.** Les deux affirmations sont mesurées et ne se contredisent pas : l'une
porte sur la *présence* d'une file, l'autre sur son *coût*.

| Ce qui est mesuré | Valeur |
|---|---|
| Attente de connexion dans `GetMailsByUids` (page d'en-têtes) | **1,8 ms — 0,1 %** du total |
| Attente de connexion dans `GetMail` | 12,3 ms — 4,1 % |
| Poste dominant de la page d'en-têtes | **matérialisation : 961,6 ms — 80,2 %** |
| Requêtes SQL par appel | **14,8** (et non les « 6 à 8 » annoncées par lecture de code) |

**D'où viennent les emprunts qui attendent** — ventilation par pool (`SHOW POOLS`
direct, pas 5-10 s mais 2 min ; le pooler ne se mesure pas lui-même) :

| Palier | Pools praticien en attente | profondeur max | Pool `postgres` | profondeur max |
|---|---|---|---|---|
| 50 | 1 relevé | 3 ms | 0 | — |
| 100 | 1 relevé | 9 ms | 3 relevés | 18,3 s |
| 200 | **22 relevés** | **1,10 s** | 2 relevés | **23,4 s** |

⇒ **La grandeur qui « accélérait » confondait deux populations.** Les bases praticien
attendent peu profondément mais de plus en plus souvent ; le pool de maintenance
`postgres` attend rarement mais des dizaines de secondes. Ce dernier existe parce que
**la sonde de readiness traverse le pooler sans `Database=`**
(`DependencyInjectionExtensions.cs:211`) — établi par lecture **et vérifié au banc** :
un seul `GET /health` recrée le pool `postgres`.

**Réserve honnête** : la profondeur de 18-62 s est **compatible** avec une entrée de
file abandonnée (Npgsql abandonne à 5 s, PgBouncer continue de compter ; profil en
dents de scie observé) mais **non prouvée** — l'état des sockets clientes n'a pas été
relevé. Ne pas la lire comme « un médecin a attendu 62 s ».

### DOD — décision de réglage : AUCUN, et pourquoi

`default_pool_size` **reste à 2**, non pas au nom du verdict périmé du 2026-08-05,
mais parce que la mesure **désigne un autre remède** : élargir les pools praticien ne
toucherait pas le pool `postgres` (qui porte les attentes profondes) et gagnerait
**0,1 %** là où la matérialisation pèse **80,2 %** — au prix de +43 % de backends en
pointe, déjà mesuré. **Aucun A/B n'était donc justifié** ; en faire un aurait été
mesurer un réglage devant une cause qu'on venait d'écarter.

**Seuil de reprise du sujet** : attente des pools **praticien** (ventilée, pas le
total) > **1 % du temps** de `GetMailsByUids`, ou profondeur **p95 > 100 ms** à un
palier. Les deux se lisent désormais directement dans le rapport.

### Findings ouverts — à NE PAS corriger ici

- **F-242-1** — matérialisation de la page d'en-têtes (80,2 %, 14,8 requêtes/appel) ;
  inclut les deux scans complets de `Mails` de F-243-1. **Candidat US n°1.**
- **F-242-2** — la sonde de readiness traverse le pooler sur une base de maintenance :
  gain **nul** sur la latence, **tout** sur la lisibilité de la mesure (elle a masqué
  la vraie tendance pendant trois campagnes). Finding d'**instrument**, prioritaire.
- **F-242-3** — `DbUpdateConcurrencyException` sur `PractitionerContactService` :
  **une écriture perdue**, rare (1/133 214) mais silencieuse et croissante avec N.
- **F-242-4** — 4,4 à 5,0 exceptions/s par réplica, famille non identifiée ; le débit
  croît avec la charge ⇒ coût par requête (signature de task-206).

### Verdict SLO du tir

50 et 100 médecins : **10/11 vertes** (seul `send`, coût fixe connu). 200 médecins :
**6/11** — sortent l'inbox (p95 5 198 ms), le message servi base (1 297), l'envoi
(2 199), la page dossier (2 008) et la fiche patient (5 004).

### Projection 500 praticiens

Backends **~880** (linéaire, 1,76/médecin), sessions IMAP **~1 200** (2,4/médecin),
attente praticien **> 1 s en régime** (super-linéaire, ×122 entre 100 et 200).
Hypothèses et invalidants écrits dans le rapport — dont celui-ci, dirimant : **toute
mesure réelle à 500 exige le mode distant** (task-221), le banc local devenant un
artefact au-delà de ~500 (Dovecot vole ~2,6 cœurs au système sous test).

### Aucune donnée de santé

Métriques d'exploitation et requêtes de diagnostic uniquement (`SHOW POOLS`,
`pg_stat_activity`, compteurs Prometheus). Données du banc 100 % synthétiques.
Le cloisonnement « une base par praticien » est inchangé — aucun réglage de
multiplexage n'a été touché.

## Simplify log

- `api-mail` — passe qualité sur le code frais (Python/PowerShell du harnais ; aucun
  C# touché par cette task). Une seule simplification retenue :
  `palier_designated_resources` construisait son entrée en deux branches
  (« premier palier » / « palier suivant ») qui dupliquaient les affectations et
  auraient divergé au premier champ ajouté → un `setdefault` avec un `share`
  sentinelle et **un seul** jeu d'affectations. Re-validé : **236 tests verts**.
- Repos non éligibles ou non touchés : `dtos-mss` (porteur de contrat, exclu par
  principe — aucun commit sur sa branche), `client-blazor`, `client-angular`,
  `client-mobile`, `sdk`, `host`, `interop-cda`.

## Sonar log

**Skip propre — zéro fichier C# touché.** Le diff de la task porte exclusivement sur
le harnais de banc (`report.py`, `observe.ps1`, ses tests) et de la documentation :
`git diff --name-only origin/develop...HEAD | grep '\.cs$'` renvoie **0**. Le périmètre
de `/sonar` est la solution .NET `HealthPlatform.Api.Mail.sln` — une analyse aurait
mesuré du code que cette task n'a pas modifié, et consommé ~20 min de build +
couverture pour un delta nul. Les KPI Sonar de `develop` restent donc ceux du dernier
tir d'analyse, inchangés par cette task.

Filet de non-régression effectivement appliqué : la suite du harnais, **236 tests
verts** (`python -m unittest discover -s tests/loadtest-k6`), rejouée après chaque
commit — c'est la garde pertinente pour du code Python/PowerShell.

## Lint log

- `/lint-angular` — **skip propre** : `client-angular` non touché (aucune branche
  créée, aucun fichier au diff).
- `/lint-mobile` — **skip propre** : `client-mobile` non touché.
- `/verify-visual` — **skip propre** : aucun écran mobile touché, donc aucune capture
  à pairer.

## PRs

- `api-mail` (pushed) : **https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/175** — label `awaiting-human-merge`
- `dtos-mss` (pushed, auto-inclus) : **aucune PR** — 0 commit sur la branche, aucun
  contrat touché (`git log origin/develop..HEAD` = 0). La branche
  `feat/task-242-attente-connexion-base` existe et reste vide, comme prévu.
- Repos non concernés : `client-blazor`, `client-angular`, `client-mobile`, `sdk`,
  `host`, `interop-cda`. `devops`, `psc-proxy-*` : gérés manuellement par l'humain.

## Code Review Summary

**APPROVED** — 5 fichiers revus, 0 blocage, 2 corrections appliquées pendant la revue.

| Fichier | Verdict |
|---|---|
| `tests/loadtest-k6/report.py` | ✅ verdict par palier, écart écrit, seuils nommés une seule fois (`PGBOUNCER_WAITING_RESOURCE` plutôt que deux littéraux qui dériveraient) |
| `tests/loadtest-k6/observe.ps1` | ⚠️→✅ deux corrections : `cl_waiting` calculé deux fois (dédupliqué), garde de colonnes **séparée** pour qu'un pooler sans `maxwait_us` ne fasse pas retomber la sonde à zéro |
| `tests/loadtest-k6/test_report_pinned_palier.py` | ✅ 13 tests, dont **deux témoins négatifs** (un transitoire d'ouverture répété à chaque palier ne désigne rien ; une ressource déjà épinglée globalement n'est pas dupliquée) |
| `docs/loadtest.md`, `reports/INDEX.md` | ✅ défaut, cause et garde-fous écrits ; verdict périmé marqué |

**Corrections issues de la revue** : (1) donnée morte — `cl_waiting_practitioner` /
`_maintenance` étaient émis dans le CSV sans jamais être rendus, alors que c'est
précisément la famille **praticien** que porte le seuil de reprise du sujet ; ils sont
désormais lus par le rapport ; (2) calcul dupliqué dans `observe.ps1`.

**Sécurité / données de santé** : métriques d'exploitation uniquement, aucune donnée
patient dans les étiquettes ni dans les requêtes de diagnostic, banc 100 % synthétique.
Le cloisonnement « une base par praticien » est inchangé — aucun réglage de
multiplexage n'a été touché.

**Validation** : build **0 erreur**, tests .NET **371 passés / 0 échec**, harnais
**237 tests verts**.

## Merged

Mergée le **2026-08-09** après validation humaine de bout en bout (HAG, règle 10 —
`/merge task-242 --i-tested`).

| Repo | PR | Squash | CI `develop` |
|---|---|---|---|
| `api-mail` | [#175](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/175) | **`c74120a9`** | ✅ verte |
| `dtos-mss` | aucune PR — branche vide (aucun contrat touché) | — | — |

Portes de sécurité au moment du merge : `mergeable=MERGEABLE`, `mergeState=CLEAN`,
label `awaiting-human-merge`, CI de la PR verte (`build` succès, `publish` sauté),
aucune revue en `CHANGES_REQUESTED`, aucun commit local non poussé, arbres de
travail propres. Branches distantes supprimées sur les deux repos ; clones locaux
revenus sur `develop`.

**Ce que ce merge met sur `develop`** — deux campagnes et leurs correctifs
d'instrument : la section « Ressource épinglée » ne peut plus écarter par la
moyenne du tir ce qu'un **palier** désigne, `maxwait` est relevé, l'attente du
pooler est **ventilée** entre bases praticien et pool de maintenance, et le seed
est devenu **reprenable**. Les findings ouverts par ces campagnes sont instruits
par les US **task-244 à task-252**.
