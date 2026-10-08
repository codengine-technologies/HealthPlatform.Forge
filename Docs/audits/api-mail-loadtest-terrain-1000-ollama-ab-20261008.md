# Banc de charge — terrain 1000, chat Ollama contre OpenAI (2026-10-07 → 08)

> Campagne demandée après ~30 commits api-mail depuis le tir de référence du 2026-09-26
> (`develop dff07dce`), dont task-325 : le **chat** (étiquetage, résumé, assistant) passe sur
> **Ollama local** (`qwen2.5:14b`, RTX 5070 Ti), les **embeddings** restent chez OpenAI.
> Rapports bruts : `Api/Mail/tests/loadtest-k6/reports/2026-10-07/` et `2026-10-08/`.

## Conditions

| | |
|---|---|
| Code sous test | api-mail `develop b66dee8f` (branche `chore/loadtest-report-ai-metrics` = develop + harnais seul) |
| Scénario | `terrain`, 1000 praticiens inscrits, 3 h, K=1, `MESSAGES_PER_USER=247`, `UID_BASE=365`, `CORPUS_THREAD_SHARE=0.3` |
| Banc mail | cluster (`192.168.1.69`), `LATENCY_MS=96` ; RTT poste↔cluster mesuré **1,7 ms** (connexion établie) |
| Tireur | **k6bench** (`192.168.1.101`) via relais `netsh portproxy` du poste (`192.168.1.170`) — ⚠️ la référence du 26/09 tirait **depuis le poste** |
| Population | **bases neuves** (supprimées le 2026-09-30, recréées par le seed en 10 min 12 s, ~0,6 s/praticien grâce à la consolidation des migrations) |
| Réplicas api-mail | 5 |

Déroulé : chauffe hybride (cold, 3 h) → vidage de la file IA en tout-OpenAI → `reset-state.sh
--keep-analysed 462` → **tir A hybride** → `reset-state.sh --keep-analysed 462` → **tir B
tout-OpenAI, conteneur Ollama arrêté**. A et B partent du même état de réserves ; B profite
seulement des caches remplis pendant A (voir étape 7).

## Verdict

**SLO 11/11 dans les deux tirs. Ollama ne change pas ce que le médecin attend** : aucune étape
de la grille n'appelle le chat. L'écart A/B est de +2 à +4 % sur la latence moyenne et le p95, et
s'explique pour l'essentiel par le cache des PJ (âge de la base), pas par Ollama.

**En revanche, Ollama est à saturation dès le régime terrain 1000** : il étiquette ~45 mails/min et
il en arrive ~44/min. La plateforme tient, mais **sans aucune marge**, avec une attente de ~60 s par
étiquetage, des timeouts à 180 s et 6 % de réponses illisibles.

| | Réf. 26/09 (OpenAI, base âgée, tireur poste) | **A — hybride (Ollama)** | **B — tout-OpenAI** |
|---|---|---|---|
| Actifs moyens | 95 | 93 | 95 |
| Latence moy. / p50 / p95 (ms) | 115 / 32 / 484 | **154 / 55 / 711** | **149 / 51 / 695** |
| Erreurs HTTP | 0,01 % | 0,00 % | 0,00 % |
| SLO | 11/11 | **11/11** | **11/11** |

### Latence par étape (p50 / p95, ms)

| # | Étape | Réf. 26/09 | A hybride | B tout-OpenAI |
|---|---|---|---|---|
| 1 | Arrivée dashboard | 18 / 792 | 60 / 745 | 59 / 743 |
| 2 | Inbox | 31 / 64 | 34 / 67 | 33 / 56 |
| 3 | Message enrichi | 29 / 45 | 33 / 57 | 30 / 50 |
| 4 | Message froid | 435 / 503 | 452 / 513 | 448 / 511 |
| 5 | Recherche | 265 / 360 | 289 / 344 | 284 / 335 |
| 6 | Envoi | 844 / 944 | 820 / 921 | 822 / 921 |
| 7 | PJ | 28 / 361 | **393 / 962** | 40 / 740 |
| 8 | Marquer lu | 24 / 33 | 32 / 77 | 28 / 72 |
| 9 | Rechercher un patient | 14 / 19 | 56 / 64 | 55 / 61 |
| 10 | Page dossier patient | 38 / 69 | 58 / 65 | 56 / 62 |
| 11 | Fiche patient complète | 217 / 342 | 293 / 415 | 268 / 371 |

## Ce que mesure chaque écart

1. **A contre B (Ollama seul)** — quasi nul côté médecin. CPU api-mail identique (0,09 cœur par
   réplica), coût SQL identique (4,3 / 4,0 ms par requête). Seule l'étape 7 diverge (393 → 40 ms au
   p50) : le contenu des `IHE_XDM.ZIP` se remplit à la première demande, et B relit ce que A a
   téléchargé. C'est l'effet « âge de la base » déjà documenté, pas un effet du fournisseur.
2. **A et B contre la référence (+40 ms sur les appels rapides)** — **artefact de transport, pas
   régression**. Côté serveur (OpenTelemetry), `GET /sync/coverage`, `…/emails/today` et
   `POST /Patients/search/advanced` valent ~18 ms au p50 dans A **et** B ; le client k6 en mesure
   56-60. À vide, le relais `portproxy` n'ajoute rien (14 vs 15 ms) ; sous charge, il ajoute ~40 ms
   par requête. La référence tirait depuis le poste. **Une comparaison avec le 26/09 n'est
   recevable qu'en retranchant ce biais, multiplié par le nombre d'appels de l'étape.**
3. **Écritures Postgres ×10** depuis le 26/09 (16 → 155 lignes/s, WAL 0,03 → 0,35 Mo/s), dans A et
   B : effet du code livré depuis (ingestion atomique task-191, marqueur d'étiquetage task-344,
   `UniqueMailContentPerMail`). Sans effet de latence mesurable à ce palier.

## Ollama — chiffres

| | Chauffe (cold, 3 h) | A — régime terrain | B (OpenAI, pour mémoire) |
|---|---|---|---|
| Étiquetages | 8 085 (44,6/min) | 7 717 (42,6/min) | 8 002 (44,2/min) |
| Durée vue par l'API (moy.) | 66,8 s | **61,3 s** | **1,1 s** |
| Échecs (timeouts 180 s) | 19 | 42 (0,5 %) | 3 |
| Réponses illisibles (`JsonException`, mail laissé sans étiquette) | 523 | **479 (≈ 6 %)** | 0 |
| File `add-new-mail-queue` en fin de fenêtre | **93 952** | 111 (oscille 0-354) | 0 |
| GPU moy. / VRAM | 80 % / 11,3 Go | 79 % / 11,3 Go | — |
| Conteneur Ollama : CPU / RAM | 1,2 cœur / 17 Go | 1,14 cœur / 18 Go | arrêté |
| Tokens de chat envoyés à OpenAI | 0 ✅ | 0 ✅ | 19,0 M |

- **`OLLAMA_NUM_PARALLEL=1`** (défaut, non posé par l'AppHost) : un étiquetage à la fois
  (~1,4 s de calcul), pour 50 demandes simultanées possibles (5 réplicas × `ConcurrentMessageLimit`
  10). L'attente de ~60 s est de la **file**, pas du calcul.
- **La capacité d'Ollama (~45/min) égale le débit d'arrivée du terrain 1000 (~44/min)** : ρ ≈ 1.
  Au-delà de 1000 inscrits, ou avec un rythme réel plus dense que les profils, la file diverge.
- **Arrivée en masse : intenable.** Une chauffe (≈ première synchronisation de 1000 boîtes) produit
  94 000 messages, soit ~35 h de vidage à ce débit. Les **embeddings sont bridés pareil** : le
  consommateur attend étiquetage **et** embedding (`Task.WhenAll`), donc les nouveaux mails restent
  hors de la recherche aussi longtemps.
- **Qualité** : ~6 % des réponses de `qwen2.5:14b` ne sont pas un JSON lisible ; le mail reste sans
  étiquette (0 avec gpt-4o-mini).

## Défauts produit révélés (à instruire — proposition de tasks `/po`, rien n'est créé)

| # | Constat | Mesure / lecture | Proposition |
|---|---|---|---|
| D1 | **Ollama saturé à 1000 inscrits** (`NUM_PARALLEL=1`) | 45/min pour 44/min d'arrivée ; attente 61 s ; 42 timeouts. **Micro-banc du 2026-10-08** (`Docs/audits/ollama-bench-20261008/`) : `NUM_PARALLEL` seul plafonne à +12 % ; le bloc « Contexte » placé avant la grille casse le cache de préfixe. Déplacé + P=4 : **76,4/min (+87 %)**, 13,6 Go de VRAM | **task-355** rédigée (`tasks/todo-task-355.md`) |
| D2 | **L'étiquetage bride les embeddings** (`Task.WhenAll` dans `AddNewMailConsumer`) | file 94 k → recherche en retard d'autant | Découpler embedding et étiquetage (deux consommateurs, ou acquitter l'embedding sans attendre le chat) |
| D3 | **Réponses illisibles de qwen2.5:14b** | 479/7 717 (≈ 6 %) | Mode JSON / grammaire Ollama (`format: json`), ou prompt durci ; compter le cas dans une métrique |
| D4 | **Les consommateurs du bus provisionnent par PgBouncer** : `ConfigureUserContext` ne recopie que `ConnectionStringServer`, la route directe de task-200 est perdue | après redémarrage, pool `postgres` (taille 2) saturé, `08P01 query_wait_timeout`, messages en `_error`, vidage tombé à 7/min ; le sémaphore statique bloque aussi les requêtes HTTP (> 2 min) | Recopier les chaînes de provisionnement dans le contexte du message (lu dans le code ; mesuré au vidage) |
| D5 | **La reprise d'étiquetage (task-344) prend des mails encore en file** (candidat = en attente > 15 min) | lu dans le code ; aucune passe observée cette nuit | Distinguer « en file » d'« échoué » (horodater l'échec, pas l'enregistrement) |
| D6 | **TTL effectif des clés `setupdb:*` ≈ 17-20 min**, pas 1 jour | `TTL` Redis mesuré 940-973 s sur des clés fraîches ; implémentation dans le SDK (`AddSdk`) | Instruire l'implémentation du cache du SDK |
| D7 | `CONFLIT METIER — enrichissement du contact RPPS abandonné` | 6 occurrences dans B (0 dans A) : concurrence plus forte quand le pipeline va vite | Vérifier la reprise de conflit du contact praticien |

## Incidents de banc (hors système sous test)

- **Boîte `loadtest-600` vidée sur le cluster** pendant la chauffe (INBOX 0, UIDNEXT 612 → 613),
  sans aucune opération IMAP d'api-mail entre 22:21:07 et 22:53:41. Cause non établie (pas de
  `kubectl` sur le poste). Effet : 3 à 6 HTTP 404 par tir, identiques en A et B. Le contrôle d'UID du
  harnais sonde 8 boîtes et ne pouvait pas le voir ; un scan IMAP complet (~1 min) le voit.
- **`dial: i/o timeout`** k6bench → poste (1 à 3 par tir) : même relais `portproxy` que le biais de
  +40 ms.
- **Adresse du poste passée en `.170`** (carte 10 GbE) : relais k6bench reposés, défauts du harnais
  corrigés (commit `0195c24f`).
- **RabbitMQ du banc en durée `Session`** : un redémarrage d'AppHost détruit la file. Le vidage
  tout-OpenAI a exigé de la mettre à l'abri (shovel vers un RabbitMQ temporaire, aller-retour,
  93 036 messages, 0 perte hors 5 messages réinjectés depuis `_error`), et d'élargir **à chaud** le
  pool PgBouncer pendant le seul vidage (D4). Rien de cela n'a touché les tirs A et B (PgBouncer
  recréé à sa configuration d'origine, vérifiée au pré-vol).

## Ce qui a été ajouté au harnais

- `report_ai.py` + section « IA — fournisseurs, étiquetage, file du bus » du rapport : tokens par
  fournisseur et garde « chat chez OpenAI = 0 », pipeline par étape (p50/p95), file du bus, GPU et
  conteneur Ollama, garde « envois mis en attente = 0 » (task-320). 12 tests, rouge prouvé par
  mutation.
- `observe.ps1` : sondes GPU (`nvidia-smi`) et file `add-new-mail-queue` (`rabbitmqctl`).

## Suites proposées

1. Décider D1 (et D2) avant tout palier > 1000 inscrits en hybride : à ce jour, **la réserve de
   l'IA locale est nulle**.
2. Rejouer un A/B **tireur sur le poste** si une comparaison stricte avec le 26/09 est nécessaire ;
   sinon, ce couple A/B est la nouvelle référence (bases neuves du 2026-10-07, tireur k6bench).
3. Instruire la boîte 600 côté cluster (journaux Dovecot), et ajouter un scan IMAP complet au
   pré-vol.
