# task-194 — A/B `read_list` avec comptage de fils, corpus fileté hydraté (2026-09-08)

Mesure avant/après demandée par le §4 et le DOD de `tasks/done-task-194.md`
(« Mesures avant/après consignées »), restée ouverte au `/review`. Banc local
(`Api/Mail/docs/loadtest.md`), protocole du `## Manual Test Plan` de la task.

## Verdict

**Le correctif tient sa promesse et ne change pas les réponses.** À corpus,
base, paramètres et charge identiques :

| Grandeur (route `GET /mail/folders/INBOX/emails/{ids}`, comptage activé) | Avant (`develop` `da2f2b6`) | Après (`fix/task-194` `98f207c`) | Δ |
|---|---|---|---|
| `read_list` p50 (client k6) | 29,5 ms | 27,3 ms | −7 % |
| `read_list` p95 (client k6) | 47,2 ms | **32,7 ms** | **−31 %** |
| `read_list` p99 / max | 58,2 / 128,4 ms | 32,7 / 54,7 ms | −44 % / −57 % |
| p50 / p95 serveur (`http_server_request_duration`) | 38,5 / 61,2 ms | 35,9 / 48,6 ms | −7 % / −21 % |
| **Allocations GC** (tous réplicas, fenêtre du tir) | **44,35 Go** | **3,44 Go** | **−92 %** |
| Allocations par page | 8,2 Mo | 0,63 Mo | ÷13 |
| Collections gen0 / gen1 / gen2 | 489 / 104 / 74 | 231 / 0 / 9 | gen2 ÷8 |
| CPU api-mail (`process_cpu_time`) | 131,1 s | 77,8 s | **−41 %** |
| Phase `sql_execute` (somme, `GetMailsByUids`) | 65,5 s | 71,3 s | +9 % |
| Phase `assemble` (somme) | 8,7 s | 8,8 s | = |
| Requêtes SQL par page (`queries_total` / appels) | 9,0 | 9,0 | = |
| Postgres, base témoin : `seq_tup_read` sur `"Mails"` | 27,05 M | 27,20 M | = |
| Postgres, base témoin : `seq_scan` sur `"Mails"` | 2 705 | 2 720 | = |
| Erreurs HTTP / 429 / itérations abandonnées | 0 / 0 / 0 | 0 / 0 / 0 | — |
| Réponses fonctionnelles (42 captures, 3 boîtes × 7 pages × 2 modes) | référence | **identiques octet pour octet** | — |

Lecture :

- **Ce qui a disparu** est la matérialisation côté .NET de tous les
  `MessageId` et de toutes les lignes porteuses de `References`/`InReplyTo` de
  la boîte à chaque page : 8,2 Mo alloués par page avant, 0,63 Mo après, et la
  pression GC gen2 divisée par huit. C'est exactement le défaut décrit par la
  task ; c'est aussi ce qui explique la baisse de CPU (−41 %) et l'écrasement de
  la queue de latence (p95 −31 %, max −57 %) alors que la médiane bouge peu :
  sur ce banc à 10 praticiens la page était déjà rapide, le coût se payait en
  mémoire et en pauses GC, pas en médiane.
- **Ce qui n'a pas changé, et que la task annonçait** : le nombre de parcours
  séquentiels Postgres. Le filtrage par sous-chaîne (`References LIKE`) reste un
  scan de `"Mails"` côté base (5 `seq_scan` par page avec comptage, 2 sans,
  mesuré sur les deux binaires) ; `sql_execute` monte même de 9 % parce que le
  filtre s'exécute désormais dans Postgres au lieu d'en mémoire. « La tâche ne
  garantit ni l'absence de scan physique ni une latence indépendante de la
  taille de la boîte » — confirmé. Le coût PostgreSQL résiduel est **mesuré
  séparément** (ligne `seq_tup_read`), comme demandé au point 7 du plan de test.
- **Lignes matérialisées** : le banc n'expose pas le nombre de lignes rendues par
  la base par requête (le compteur `mssante_db_operation_objects_total{family=
  "thread_links"}` compte les objets de fil **après** filtrage : 77 231 avant,
  78 357 après, soit 14,3 par page dans les deux cas, ce qui confirme l'identité
  fonctionnelle mais pas la matérialisation). La preuve ligne à ligne est celle
  de l'intercepteur du test d'intégration `ThreadCountsScopedLoadTests` livré par
  la task ; sur le banc, la grandeur qui la reflète est l'allocation GC par page.

## Conditions du tir (iso-conditions entre les deux jambes)

| Paramètre | Valeur |
|---|---|
| Machine | poste de dev, banc local (Dovecot + GreenMail + Toxiproxy + PgBouncer en profil `https-load-test`), Postgres local `postgres-pgvector` |
| Code avant | `api-mail` `develop` @ `da2f2b6` (task-183 mergée) |
| Code après | `fix/task-194-thread-counts-scoped-load` @ `98f207c` (merge de ce même `develop`) |
| Corpus | seed `--users 10 --messages 10000 --thread-share 0.3 --no-xdm`, 100 000 messages, 17 min |
| Corpus **vérifié en base** (pas seulement déclaré) | 10 bases × 10 000 lignes `"Mails"`, **3 000 réponses** (`InReplyTo` non vide) et 10 000 `MessageId` par base ; fils concentrés en tête de boîte (chaînes de 1, 2, 3 réponses, UID 1 à ~4 500) |
| Hydratation | pages de 50 UID `?includeThreadCounts=false`, 10 travailleurs, 200 pages par boîte, 3 min 08 s, 0 erreur — base hydratée **une fois**, partagée par les deux jambes (aucune purge entre les jambes) |
| Harnais k6 `read` | `USERS=10 MESSAGES_PER_USER=100 ENRICH_SHARE=0 READ_BATCH=5 VUS=50 JOURNEY_THREAD_COUNTS=1 CORPUS_THREAD_SHARE=0.3 PROM=1 DURATION=3m` — bande lue UID 1..100 (zone filetée), 30 itérations/s = 30 `read_list` + 30 `read_content` par seconde, 6 req/s par identité |
| Latence réseau simulée | Toxiproxy 100 ms (profil `mssante`), sans effet ici : les pages sont servies depuis la base |
| Chauffe | par jambe : redémarrage AppHost → tir `read` 60 s **jeté** → relevé → tir mesuré 3 min → décantation 30 s → relevé |
| Fenêtres mesurées (heure locale) | avant 15:19:37–15:22:40 ; après 15:38:18–15:41:18 |
| Validité (rapport k6) | PASS × 2, 0 abandon, VU pic 1/50 (charge servie par un seul VU : la page est courte), `vus_max` jamais atteint |
| Écarts déclarés au protocole | (a) `--no-xdm` : messages texte, pas de pipeline CDA — le comptage de fils ne dépend pas des pièces jointes et l'hydratation des en-têtes aurait sinon déclenché 100 000 analyses CDA hors sujet ; (b) 10 praticiens et non un palier de population : la question posée est le coût **par page** à boîte hydratée, pas la capacité ; (c) les 1 000 bases `u_9…` d'une campagne antérieure étaient présentes et vides — hors chemin ; (d) garde anti-veille armée avec preuve (`KEEP-AWAKE ARMED … previous state: 0x80000000`) |

Rapports k6 par jambe : `report-read-mssante-50vu-152239.md` (avant) et
`report-read-mssante-50vu-154118.md` (après), dumps Seq `seq-read-mssante-50vu-*.jsonl`.

## Analyse Seq

Fenêtres des deux tirs, MCP `seq-local` : **0 événement `Error`/`Fatal`** dans
les deux jambes. Warnings de deux familles seulement, toutes deux du banc :
`[RefreshSession] session not found for Session=…` (cache de session, sur
`GetEmailsByIds`) et `[TlsCertificateValidationSession] Allowing untrusted
certificate … due to configuration` (certificat auto-signé du Dovecot du banc,
sur `GetEmail`). Aucune trace applicative nouvelle sur la jambe après.

## Télémétrie fine — où passe la page

Décomposition serveur d'une page avec comptage (moyennes sur la fenêtre,
`GetMailsByUids`) : durée totale 13,7 ms avant → 14,6 ms après par appel, dont
`sql_execute` 12,1 → 13,0 ms et `assemble` 1,6 → 1,6 ms. **Le temps serveur
par page est stable ; le gain est ailleurs** — dans ce qui se passait autour de
l'opération instrumentée : allocation puis libération de ~8 Mo de chaînes par
page, et les pauses GC qui en découlent (gen1 104 → 0, gen2 74 → 9), visibles
dans la queue de latence HTTP et dans le CPU total, pas dans les phases SQL.

Ce que la télémétrie n'a **pas** pu dire : le nombre de lignes rendues par
Postgres par requête (pas de `pg_stat_statements` sur ce Postgres, et le
compteur d'objets ne compte qu'après filtrage). C'est le manque
d'instrumentation à retenir si une prochaine US veut suivre la matérialisation
en production autrement que par les allocations GC.

## Axes d'amélioration — ce que ce tir révèle

- **Aucun candidat mécanique nouveau** sur `read_list` à cette échelle : 27 ms
  de médiane, servis depuis la base.
- **Le coût Postgres résiduel du comptage est réel et proportionnel à la
  boîte** : 3 des 5 parcours séquentiels de `"Mails"` par page viennent du
  comptage de fils (`LIKE` sur `References`), soit 30 000 tuples lus par page
  pour 10 000 messages. Il est invisible en latence à 10 praticiens ; il est le
  candidat naturel du palier 1 000 sur base hydratée (mémoire
  `loadtest-palier-1000-chauffe-aboutie-requalifie` : page d'en-têtes 7,6 s
  dont 6,6 s de matérialisation). Lecture de code, pas mesure : un index
  trigram ou une table de liens de fil normalisée (`InReplyTo` indexé, plus
  `References` en sous-chaîne) supprimerait le scan. **À proposer en US,
  pas à faire ici.**
