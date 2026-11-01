# Rapport de tir — read-mssante-50vu

> Banc de charge api-mail (EPIC E015). Source k6 : `read-mssante-50vu-233259.json`.

## 🟢 VERT — tir réussi, rien à signaler

Le tir s'est déroulé correctement, aucune demande n'a échoué, les temps de réponse attendus sont tenus et aucun traitement ne ressort comme candidat à l'optimisation. Rien à instruire.

## Contexte

- **Scénario** : read
- **Utilisateurs** : 50 — **VUs** : 50 — **Durée** : 5m — **Latence** : mssante
- **Requêtes** : 90012 — **Débit plateau** : 300.0 req/s (k6 publie 294.4 req/s)

## Corpus — fils de discussion

Corpus **sans aucun fil de discussion** — c'est le défaut du seed (`--thread-share 0`).

> ⚠️ **Ce que ce tir ne peut pas mesurer.** Sans `In-Reply-To` ni `References`, la requête des lignes citant une racine ramène **0 ligne** et la boucle de comptage tourne **à vide**. Le coût du comptage de fils n'est donc **pas exercé** : seul le balayage l'est. Un gain publié ici sur ce chemin est un **plancher**, jamais un plafond.

## Validité du tir

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 2 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 44999 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 31 / 52 | pic < plafond |
| Pool de VUs saturé | non | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 50 | 50 | read | **300.0** | 294.4 | **37.0** | 39.1 | **57.9** | — | 1130.5 | 0.00 | 100.0 | 0 | 0 | 172802/— |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

**Deux dénominateurs, et c'est important** :

- **Débit plateau** = 90012 requêtes ÷ 300 s de plateau = **300.0 req/s**. C'est le chiffre à citer.
- **Débit k6** (`http_reqs.rate`) = 90012 ÷ 306 s de fenêtre **totale, arrêt gracieux inclus** = 294.4 req/s, soit 1.9 % de moins. C'est ce biais qui a fait publier 915,5 req/s pour la référence 200 alors qu'elle valait 934,5.

## Débit demandé vs délivré (par sous-scénario)

| Sous-scénario | Budget req/s | Délivré req/s | Servi | VU plan (pre/max) | Little | Source |
|---|---|---|---|---|---|---|
| `read` | non imposé | 300.0 | — | — | — | — |
| **total** | **0** | **300.0** | — | | | |

- Débits délivrés calculés sur la **durée de plateau**, comme le débit de l'en-tête — et non sur la fenêtre totale du run, arrêt gracieux inclus.

## Latence planifiée vs mesurée — et ce qui produit les abandons

⚠️ **Aucun plan de latence déclaré par le harnais** (`context.scenarioPlan`) : tir antérieur à task-203. La confrontation entre l'hypothèse de dimensionnement et la mesure — donc l'attribution des abandons — n'est pas possible sur ce tir.

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| read_content | 44999 | 27.8 | 22.5 | 41.8 | 49.2 | 234.2 |
| read_list | 44999 | 46.1 | 43.6 | 56.0 | 63.0 | 271.9 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-11-01T22:27:53.950000+00:00 → 2026-11-01T22:32:59.738000+00:00 (306 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-172346.csv`) | ⚠️ **aucun point dans la fenêtre du tir** (13232 lignes lues hors fenêtre) |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-10388` | 0.82 | 1 | 10 | 0.011 | 1.75 |
| `DESKTOP-DEV-X2C-18308` | 0.74 | 1 | 11 | 0.010 | 1.96 |
| `DESKTOP-DEV-X2C-24136` | 0.62 | 1 | 9 | 0.009 | 2.27 |
| `DESKTOP-DEV-X2C-26124` | 0.92 | 4 | 12 | 0.012 | 2.40 |
| `DESKTOP-DEV-X2C-66820` | 0.76 | 0 | 10 | 0.010 | 2.33 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur

⚠️ **Échantillonneur absent de la fenêtre** — le CPU des conteneurs, celui de k6 et celui de l'hôte ne sont pas mesurés. Impossible, sur ce tir, d'écarter le tireur comme facteur limitant.

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 2387.5 | 14 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 67.9 | 62 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 98.2 | 62 |

- **p95 client global (k6)** : 57.9 ms
- **p95 serveur le plus élevé** : 2387.5 ms
- **Écart** : -2329.6 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Événements de session IMAP /s | 0.15 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `GetMail` | 12.2 | 20.7 | 48 | 0.0 (0.1 %), p95 5 | 17.6 (85.1 %), p95 45 | 3.1 (14.8 %), p95 9 |
| `GetMailsByUids` | 14.3 | 23.1 | 58 | 0.1 (0.3 %), p95 5 | 19.3 (83.6 %), p95 47 | 3.7 (16.1 %), p95 14 |

- **`GetMail`** — sur 20.7 ms en moyenne (12.2 requête(s) SQL par appel) : 0.0 ms attente d'une connexion, 17.6 ms exécution SQL, 3.1 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 23.1 ms en moyenne (14.3 requête(s) SQL par appel) : 0.1 ms attente d'une connexion, 19.3 ms exécution SQL, 3.7 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est la contention base à l'état pur (pool Npgsql, PgBouncer) ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 13.9 | 3.1 | 221.2 | 1.0 | 1.0 | 1.0 | 3.2 | non relevé | 0.0 | 1.0 | 5.5 | 0.0 | 1.0 | non relevé | 0.2 |
| `GetMailsByUids` | 53.6 | 3.7 | 69.3 | 5.0 | 5.0 | 5.0 | 8.2 | 5.0 | 0.0 | 5.0 | 1.5 | 0.0 | 5.0 | 13.0 | 0.9 |

- **`GetMail`** — sur 3.1 ms de matérialisation, l'appel a construit 13.9 objets, dont 1.0 messages, 1.0 étiquettes, 1.0 destinataires, 3.2 pièces jointes, 0.0 acquittements, 1.0 documents médicaux, 5.5 résultats de biologie, 0.0 éléments de synthèse, 1.0 corps de messages, 0.2 références de doublon. **Famille dominante : résultats de biologie.**
  - Coût par objet : **221.2 µs**.

- **`GetMailsByUids`** — sur 3.7 ms de matérialisation, l'appel a construit 53.6 objets, dont 5.0 messages, 5.0 étiquettes, 5.0 destinataires, 8.2 pièces jointes, 5.0 identifiants enrichis, 0.0 acquittements, 5.0 documents médicaux, 1.5 résultats de biologie, 0.0 éléments de synthèse, 5.0 corps de messages, 13.0 objets de fil, 0.9 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **69.3 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **3190.9 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

⚠️ **Aucune décomposition sur la fenêtre.** Les instruments `mssante_enrichment_message_duration_seconds` / `..._phase_...` (task-245) n'ont produit aucun point : soit le binaire déployé est antérieur à leur ajout, soit le collector n'a pas tourné, soit aucun message n'a été enrichi. Sans eux, le **goulot G1** du tir 500 reste une boîte noire — et cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222).

### Où part le temps d'un envoi

⚠️ **Aucune décomposition sur la fenêtre.** Les instruments `mssante_send_message_duration_seconds` / `..._phase_...` (task-260) n'ont produit aucun point : binaire antérieur, collector muet, ou aucun envoi. Sans eux, la seule étape hors grille du parcours reste une boîte noire — et task-238 a déjà corrigé deux fois à l'aveugle.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `imap_session` | 0.005 | 2.368 | 0.15 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `ReadFolder` | 0.005 | 2.368 | 2.406 | 0.243 | 0.15 |

> ⚠️ **Table calculée sur TOUTES les fenêtres du tir, chauffe comprise** — aucun repliement disponible (Prometheus absent, ou tir sans allocation de chauffe). Une détention élevée peut donc appartenir à l'établissement des sessions au front du palier plutôt qu'au parcours jugé : **ne pas écrire d'US de correctif sur ces chiffres seuls** (task-271, task-276).

| Voie | Acquisitions /s |
|---|---|
| `read` | 0.15 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

⚠️ **Aucune série `AppendToSent`, et aucune acquisition sur la voie d'écriture — ce rapport ne peut pas trancher.** Deux causes produisent cette même absence : l'archivage n'a pas tourné, ou il a tourné **sans être mesuré**. La métrique ne les distingue pas.

> Le 2026-08-01, cette table a conclu « le tir n'a pas archivé d'envoi ». C'était faux : l'archivage tournait, il n'était pas instrumenté (task-214). **Contrôle avant de conclure** : la ligne `send` de « Débit demandé vs délivré » ci-dessus. Un débit d'envoi non nul avec cette ligne absente désigne un défaut d'**instrumentation**, pas un tir sans archivage — vérifier alors que le binaire déployé porte bien task-214.

### Ressource épinglée

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| file ThreadPool du réplica `DESKTOP-DEV-X2C-26124` | 4.00 éléments | 100 éléments | 4.0 % | 0.0 % — transitoire |

**Aucune ressource épinglée — le plafond est ailleurs.** La plus sollicitée (file ThreadPool du réplica `DESKTOP-DEV-X2C-26124`) monte à 4.0 % de sa borne, mais sur 0.0 % des échantillons seulement — sous le seuil de présence de 25 %, c'est un transitoire et non une saturation. Chercher du côté des dépendances sérialisées (sessions IMAP, verrous de provisionnement) plutôt que d'une ressource matérielle.

## IA — fournisseurs, étiquetage, file du bus

> Aucune étape de la grille SLO n'appelle le chat : le fournisseur IA agit **à côté** du médecin. `AddNewMailConsumer` attend l'étiquetage et l'embedding ensemble (10 messages simultanés) : un étiquetage lent bride aussi les embeddings, donc retarde l'entrée des nouveaux mails dans la recherche. Ollama partage en outre l'hôte du système sous test. Ces chiffres sont **publiés, jamais jugés** par la grille.

_Aucune série IA dans Prometheus sur la fenêtre du tir — pipeline IA désactivé (drapeaux `ai_pipeline` / `ai_auto_tagging`), Prometheus non branché, ou binaire antérieur à task-325. Non relevé, pas zéro._

### File `add-new-mail-queue` (échantillonneur)

_Non relevée — échantillonneur antérieur à la sonde `bus`, ou RabbitMQ injoignable._

### GPU et conteneur Ollama (échantillonneur)

_Non relevés — pas de sonde GPU (`nvidia-smi`) ni de conteneur `mss-mail-ollama` sur la fenêtre (tir tout-OpenAI, ou échantillonneur antérieur)._

## Postgres — réaction du serveur et requêtes

> Trois photos `pg-statements.sh` (compteurs serveur début/fin, `pg_stat_statements` par forme de requête, tables d'une base praticien échantillon). Les grandeurs « par seconde » et « par requête HTTP » se comparent d'un tir à l'autre à N constant ; le top 20 dit **sur quoi** le serveur a travaillé. Les pistes sont des hypothèses dérivées de compteurs : le plan (`explain (analyze, buffers)`) tranche, pas ce tableau.

### Réaction du serveur au tir (comparable inter-tirs)

| Grandeur | Valeur | Lecture |
|---|---|---|
| Durée couverte (reset → photo) | **5.2 min** | chauffe incluse — le régime seul exige un delta sur `snapshot warmup` |
| Transactions validées / s | **7 458.4** | annulées : 0.0 % |
| Backends actifs (équivalent) | **0.57** | temps SQL actif ÷ durée : requêtes simultanément en exécution, en moyenne |
| Coût SQL par requête HTTP | **2.0 ms** | sur 90 012 requêtes HTTP k6 |
| Taux de cache (blocs) | **100.00 %** | ✅ ≥ 99 % |
| Lecture disque | **0.00 Mo/s (0 blocs/s)** | attente disque : 0.0 % du temps SQL actif |
| Lignes balayées / renvoyées par index, par s | **944 023 / 10 504** | rapport 89.9 ⚠️ balayages dominants |
| Écritures de lignes / s (ins+upd+del) | **0.0** |  |
| Fichiers temporaires | **0 (0.0 Mo)** | ✅ aucun tri sur disque |
| WAL | **0.00 Mo/s** | `wal_buffers_full` : 0 |
| Checkpoints programmés / forcés | **1 / 0** | blocs écrits par les backends eux-mêmes : 0 % |
| Sessions ouvertes / s | **0.58** | abandonnées 0, fatales 0 ; `idle in transaction` : 0.0 % du temps de session |
| Interblocages | **0** | 0 attendu |
| Croissance des bases praticien | **0.0 Mo** | 1 000 bases |
| Backends (échantillonneur, moy / max) | **non relevé** | `max_connections` = 2 500 |
| Login Postgres (sonde, p50 / p95 / max) | **non relevé** | < 1 000 ms attendu |
| cgroup mémoire (moy / max) | **non relevé** |  |

Réglages au moment de la photo : PostgreSQL 16.11, `shared_buffers` 12 288 Mo, `effective_cache_size` 36 864 Mo, `work_mem` 4 096 Ko, `random_page_cost` 4.0, `max_connections` 2 500, autovacuum on.

### Top 20 des requêtes par temps serveur cumulé

37 formes de requête, 2 315 666 appels, **2.0 min** de temps serveur cumulé — soit **1.3 ms de SQL par requête HTTP**.

| # | Part | Cumul | Appels | /req HTTP | ms/appel | Lignes/appel | Blocs/appel | Disque | Temp | Bases | Piste | Requête |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **14.1 %** | 14 % | 44 999 | 0.50 | 0.38 | 5.0 | 82 | 0 % | 0 | 50 | — | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 2 | **11.6 %** | 26 % | 18 899 | 0.21 | 0.74 | 1.0 | 22 | 0 % | 0 | 21 | — | `SELECT m."Id", m."Body", m."Category", m."ContentFingerprint", m."CreatedAt", m."Date", m."DocumentId", m."DuplicateCon…` |
| 3 | **6.5 %** | 32 % | 89 998 | 1.00 | 0.09 | 4.0 | 6 | 0 % | 0 | 50 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 4 | **6.3 %** | 39 % | 270 018 | 3.00 | 0.03 | 1.0 | 3 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT m.validated_by_psc_subject AS "ValidatedByPscSubject", m.validated_by_rpps AS "ValidatedByRpps" FROM mss_account…` |
| 5 | **5.7 %** | 44 % | 63 898 | 0.71 | 0.11 | 1.3 | 13 | 0 % | 0 | 50 | — | `SELECT m."MedicalDocumentId", m."InterpretationCode" FROM "MailMedicalDocumentBiology" AS m WHERE m."IsFlagged" AND m."…` |
| 6 | **5.6 %** | 50 % | 270 018 | 3.00 | 0.03 | 1.0 | 3 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT a.id, a.authentication_subject, a.created_at, a.email, a.last_activity_at, a.last_authentication_at, a.username …` |
| 7 | **5.6 %** | 55 % | 629 882 | 7.00 | 0.01 | 0.0 | 0 | — | 0 | 1 | **Infra** — cycle de connexion/transaction, pas une requête métier : coût du login et du pooler (`server_idle_timeout`, `Minimum Pool Size`) | `DISCARD ALL` |
| 8 | **5.3 %** | 61 % | 44 999 | 0.50 | 0.14 | 6.0 | 6 | 0 % | 0 | 50 | — | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 9 | **5.0 %** | 66 % | 89 998 | 1.00 | 0.07 | 5.0 | 6 | 0 % | 0 | 50 | — | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 10 | **4.7 %** | 71 % | 89 998 | 1.00 | 0.06 | 4.0 | 6 | 0 % | 0 | 50 | — | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 11 | **4.1 %** | 75 % | 44 999 | 0.50 | 0.11 | 1.5 | 13 | 0 % | 0 | 50 | — | `SELECT m."MedicalDocumentId", m."Section", m."Name", m."PrimaryValue", m."PrimaryUnit", m."PrimaryMinValue", m."Primary…` |
| 12 | **3.6 %** | 78 % | 44 999 | 0.50 | 0.10 | 5.0 | 6 | 0 % | 0 | 50 | — | `SELECT m."Id", m."AiTaggingPendingSince", m."FolderPath", m."FromAddress", m."FromName", m."HasBiologyResults", m."HasM…` |
| 13 | **3.0 %** | 81 % | 90 006 | 1.00 | 0.04 | 1.0 | 6 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT m.id, m.account_id, m.address_type, m.attached_at, m.database_name, m.detached_at, m.is_default, m.last_successf…` |
| 14 | **2.8 %** | 84 % | 18 899 | 0.21 | 0.18 | 1.0 | 8 | 0 % | 0 | 21 | — | `SELECT m."Id", m."Body", m."BodyHtml", m."ContentType", m."Embedding", m."EmbeddingModel", m."MailId", m."Summary" FROM…` |
| 15 | **2.5 %** | 86 % | 44 999 | 0.50 | 0.07 | 8.2 | 7 | 0 % | 0 | 50 | — | `SELECT m."Id", m."MailId", m."DocumentId", m."Guid", m."FileName", m."ContentType", m."Size" FROM "MailAttachments" AS …` |
| 16 | **2.1 %** | 89 % | 63 898 | 0.71 | 0.04 | 0.7 | 10 | 0 % | 0 | 50 | — | `SELECT m."Id" AS "DocId", m."DuplicateOfId" AS "OriginalDocId", m0."Title" AS "DocumentTitle", m0."Date" AS "DocumentDa…` |
| 17 | **1.8 %** | 90 % | 44 999 | 0.50 | 0.05 | 5.0 | 3 | 0 % | 0 | 50 | — | `SELECT m."MailId", t."Id", t."Name", t."Code", t."Type", t."ColorCode", m."UrgencyLevel"::int AS "UrgencyLevel", m."Urg…` |
| 18 | **1.6 %** | 92 % | 18 899 | 0.21 | 0.10 | 5.5 | 13 | 0 % | 0 | 21 | — | `SELECT m."MedicalDocumentId", m."Section", m."Name", m."PrimaryValue", m."PrimaryUnit", m."PrimaryMinValue", m."Primary…` |
| 19 | **1.6 %** | 94 % | 44 999 | 0.50 | 0.04 | 5.0 | 8 | 0 % | 0 | 50 | — | `SELECT DISTINCT m."MailId" FROM "MailContents" AS m WHERE m."MailId" = ANY ($1)` |
| 20 | **1.4 %** | 95 % | 44 999 | 0.50 | 0.04 | 5.0 | 7 | 0 % | 0 | 50 | — | `SELECT m."Id", m."MailId", m."ContentType", $2 AS "Body" FROM "MailContents" AS m WHERE m."MailId" = ANY ($1)` |

Colonnes : **Part** = part du temps serveur cumulé de toutes les formes ; **/req HTTP** = appels SQL par requête HTTP du tir (> 3 sur une forme légère = N+1 probable) ; **Blocs/appel** = pages de 8 Ko touchées par exécution ; **Disque** = part de ces blocs lus hors cache ; **Bases** = nombre de bases où la forme a tourné (1 = base commune).

| Répartition | Part du temps | Part des appels |
|---|---|---|
| SELECT | 94.4 % | 72.8 % |
| INSERT | 0.0 % | 0.0 % |
| UPDATE | 0.0 % | 0.0 % |
| AUTRE | 5.6 % | 27.2 % |
| bases : praticien (N bases) | 79.5 % | 45.6 % |
| bases : unique (1 base) | 20.5 % | 54.4 % |

Les plus lentes **par appel** (≥ 100 appels) — ce que le praticien attend :

| ms/appel | max ms | Appels | Part | Requête |
|---|---|---|---|---|
| **0.7** | 13 | 18 899 | 11.6 % | `SELECT m."Id", m."Body", m."Category", m."ContentFingerprint", m."CreatedAt", m."Date", m."Document…` |
| **0.4** | 6 | 44 999 | 14.1 % | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", …` |
| **0.2** | 23 | 18 899 | 2.8 % | `SELECT m."Id", m."Body", m."BodyHtml", m."ContentType", m."Embedding", m."EmbeddingModel", m."MailI…` |
| **0.1** | 7 | 44 999 | 5.3 % | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" …` |
| **0.1** | 2 | 63 898 | 5.7 % | `SELECT m."MedicalDocumentId", m."InterpretationCode" FROM "MailMedicalDocumentBiology" AS m WHERE m…` |

### Tables et index de la base échantillon

Base `u_l9l_174a6f60f979139e3c0f65bc3bdc2a52` (la plus volumineuse du banc), compteurs fin − début.

✅ aucun balayage séquentiel sur la base échantillon pendant le tir.

### Pistes d'optimisation (hypothèses à confirmer par le plan)

| Cible | Gravité | Piste |
|---|---|---|
| Infra | 🟠 | requête n°4 (6.3 % du temps SQL) — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien |
| Infra | 🟠 | requête n°7 (5.6 % du temps SQL) — cycle de connexion/transaction, pas une requête métier : coût du login et du pooler (`server_idle_timeout`, `Minimum Pool Size`) |
| Schéma | 🟠 | 90 lignes balayées par ligne renvoyée par index : les balayages séquentiels dominent — voir les tables balayées |
| Schéma | 🟠 | requête n°3 (6.5 % du temps SQL) — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) |

Cibles : **Postgres** = réglage serveur (`shared_buffers`, `work_mem`, bgwriter…), **Schéma** = index à ajouter ou retirer (migration EF), **Code** = forme de la requête EF Core (projection, `Include`, lot, portée du `DbContext`), **Infra** = pool, login, provisionnement. Prochain geste pour chaque ligne : `explain (analyze, buffers)` de la forme sur une base praticien hydratée, puis un A/B au banc à N constant.

Sources : `pgstats-read-233301.tsv`, `pgserver-read-debut-232751.tsv`, `pgserver-read-fin-233301.tsv`, `pgtables-read-debut-232753.tsv`, `pgtables-read-fin-233304.tsv`.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 1000
- **Mails stockés (total)** : 172802 — dont **172802** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Verdict propriété** : PASS

✅ **1000 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-read-mssante-50vu-233259.jsonl`.

_À COMPLÉTER par l'analyse systématique seq-local (voir le skill). Lister ici : erreurs/warnings hors bruit de boot, nombre de parsings CDA (`[CdaParsingService] Parsing completed`), échecs d'embedding (task-196), 429, erreurs de connexion IMAP, reprises d'étiquetage IA (`[TaggingRecovery]`), et tout marqueur de régression (`Failed to parse entity headers`)._
