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
