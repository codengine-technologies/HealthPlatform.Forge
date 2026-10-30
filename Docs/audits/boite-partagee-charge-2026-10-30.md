# Charge d'une boîte partagée — N personnes sur une boîte contre N boîtes (task-406, 2026-10-30)

> **Question** : depuis task-404, toutes les personnes d'une boîte (titulaire, délégataires, membres)
> partagent **une** base. La règle qui a fixé les bornes du pool (« connexions retenues ≈ praticiens ×
> réplicas × Max Pool Size ») change de sens : moins de bases, chacune plus chargée. Tiennent-elles ?
> Et la copie des traitements par personne a-t-elle disparu ?
>
> **Réponse courte** :
> - **Les bornes du pool Postgres tiennent** jusqu'à 10 personnes par boîte : attente de connexion
>   ≈ 0,1 ms, aucun pool épuisé, aucune erreur.
> - **La copie par personne a disparu** : un message est analysé (CDA) et étiqueté par l'IA **une fois**,
>   quel que soit N.
> - **Le coût du partage est ailleurs**, dans les **sessions et verrous de la boîte**, pas dans Postgres.
>   À 10 personnes, l'ouverture d'un message double (p50 0,45 → 1,05 s), l'envoi double (0,42 → 0,88 s),
>   et l'attente des verrous de récupération passe de 3 s à **520 s** cumulées sur le tir.
>   Deux tasks de suite sont proposées.

## Conditions

| Élément | Valeur |
|---|---|
| Tireur | local (poste `DESKTOP-DEV-X2C`), k6 v2.1.0 |
| Banc mail | **cluster** (`MSS_LOADTEST_MAIL_HOST=192.168.1.69`), Toxiproxy `LATENCY_MS=96` |
| Registre | `mss_registry_loadtest`, recréé (les bases locales du banc avaient été supprimées le 2026-09-30) |
| Population | boîtes `loadtest-1..10`, maildir du cluster (247 messages par boîte, `UID_BASE=365`) ; bases praticien **neuves**, purgées (`reset-state.sh --users 10`) avant chaque tir |
| Scénario | `mixed` 3 min, `RPS_PER_USER=6` (charge totale identique entre les deux profils d'un même N), `VUS=10×N` |
| IA | tout-OpenAI (`AiProvider__Chat=OpenAI`) — Ollama étiquette ~45 mails/min et aurait faussé le comptage |
| Profil « référence » | N personnes, chacune sur **sa** boîte (`SHARED_BOX=0`) |
| Profil « boîte partagée » | N personnes sur la boîte de la première : une titulaire, N−1 délégataires, chacune sous sa propre identité PSC et son nom (`seed --shared-box N`, `SHARED_BOX=N`) |
| Code | api-mail `feat/task-406-…` @ `2f936031` (+ correctifs du harnais de ce tir) |

**Validité** : chaque tir abandonne 2 à 3 % de ses itérations (`dropped_iterations`). Le rapport
l'impute au **dimensionnement du harnais** : la file ThreadPool est restée à 1 au plus. Les **débits ne sont donc pas des plafonds**.
Les comparaisons tiennent, à harnais identique, sur les latences, les compteurs et les verrous. Rapports
individuels : `Api/Mail/tests/loadtest-k6/reports/2026-10-30/report-mixed-mssante-{20,50,100}vu-*.md`.

## Résultats

### 1. Traitements par message — la copie par personne a disparu

| N | Profil | Requêtes | Docs CDA analysés | Messages traités | `enrich` court-circuités | IA `classement-auto` | IA `embedding-document` | IA `embedding-recherche` |
|---|---|---|---|---|---|---|---|---|
| 2 | référence | 2 000 | 244 | 243 | 0 | 248 | 493 | 141 |
| 2 | partagée | 2 035 | 124 | 124 | 23 | 124 | 247 | 181 |
| 5 | référence | 5 049 | 595 | 594 | 0 | 614 | 1 220 | 424 |
| 5 | partagée | 4 996 | **123** | **123** | **96 / 120** | **123** | **244** | 438 |
| 10 | référence | 9 757 | 1 225 | 1 222 | 0 | 1 222 | 2 426 | 875 |
| 10 | partagée | 9 613 | **124** | **124** | **210** | **124** | **247** | 932 |

Lecture :
- **Une analyse CDA et une étiquette IA par message, quel que soit N** en boîte partagée : ~124 contre
  N × ~122 en référence.
- Le court-circuit de l'`enrich` est le mécanisme : un message déjà analysé dans la base de la boîte n'est
  pas ré-analysé quand une autre personne le demande. Exemple à N = 5 : 96 appels sur 120 (24 = 120 / 5).
- Seul `embedding-recherche` suit la charge dans les deux profils. C'est un appel par **recherche**, pas
  par message, donc c'est attendu.

### 2. Latences par opération (p50 / p95, ms)

| N | Profil | ouverture (`read_content`) | liste (`read_list`) | envoi (`send`) | recherche | `enrich` | dossiers (chaud) |
|---|---|---|---|---|---|---|---|
| 2 | référence | 443 / 1 006 | 27 / 664 | 416 / 842 | 284 / 1 187 | 1 515 / 3 572 | 18 / 24 |
| 2 | partagée | 445 / 1 067 | 31 / 493 | 450 / 875 | 307 / 739 | 911 / 2 171 | 21 / 28 |
| 5 | référence | 438 / 832 | 329 / 958 | 419 / 864 | 288 / 504 | 1 560 / 3 024 | 18 / 25 |
| 5 | partagée | **1 014** / 1 130 | 32 / 47 | **864** / 950 | 304 / 557 | 19 / 3 311 | 21 / 27 |
| 10 | référence | 448 / 1 026 | 37 / 863 | 424 / 866 | 297 / 7 351 | 1 700 / 2 862 | 22 / 43 |
| 10 | partagée | **1 046** / 1 154 | 32 / 51 | **879** / 952 | 307 / 1 465 | 21 / 2 043 | 22 / 29 |

- **Ouverture et envoi doublent dès 5 personnes par boîte.** La liste et l'`enrich` deviennent au contraire plus
  rapides : leur résultat est déjà en base grâce à une autre personne.
- Aucune erreur HTTP (0 %), aucun 429, sur les six tirs.

### 3. Où part le temps : verrous de la boîte et sessions

| N | Profil | attente `in_process_fetch` (moy. / p95) | attente `distributed_fetch` (moy. / p95) | délais dépassés | attente `imap_session` p95 | attente cumulée des verrous de récupération |
|---|---|---|---|---|---|---|
| 5 | référence | 0,0 / 0,005 s | 0,003 / 0,005 s | 0 | 0,25 s | 1,9 s |
| 5 | partagée | **2,8 / 11,0 s** | **1,0 / 6,3 s** | **3** | 0,44 s | **138,9 s** |
| 10 | référence | 0,0 / 0,005 s | 0,005 / 0,005 s | 0 | 0,22 s | 3,0 s |
| 10 | partagée | **7,1 / 26,8 s** | **1,8 / 7,0 s** | **9** | 0,54 s | **520,3 s** |

Phases de l'envoi (moyennes, N = 10) :

| Phase | Référence | Partagée |
|---|---|---|
| acquisition de la session SMTP | 52 ms | **380 ms** |
| archivage dans « Envoyés » (IMAP) | 469 ms | **923 ms** |
| transmission SMTP | 393 ms | 395 ms |

Causes :
- **Le verrou de récupération d'un message est par boîte.** Il est là pour ne récupérer qu'une fois ce
  qu'on lit, et c'est précisément ce qui supprime la copie par personne. En contrepartie, N personnes qui
  ouvrent les mêmes messages font la queue derrière une seule récupération. L'attente croît plus vite que N :
  139 s à 5 personnes, 520 s à 10.
- **Les sessions IMAP et SMTP sont plafonnées par boîte** (`MaxSessionsPerMailbox`, 3 par défaut), pas par
  personne. À 5 et 10 personnes, l'acquisition d'une session SMTP passe de 52 à 380 ms. L'archivage
  dans « Envoyés » attend la session IMAP de la boîte, partagée par tous. C'est le constat de l'audit du
  2026-10-30, désormais **mesuré**.

### 4. Postgres

| N | Profil | attente d'une connexion (`GetMail`, moy.) | backends max (bases praticien / total) | pool épuisé |
|---|---|---|---|---|
| 10 | référence | 0,0 ms (0,2 %) | 20 / 31 | 0 |
| 10 | partagée | 0,1 ms (1,2 %) | 20 / 39 | 0 |

- **Les bornes du pool tiennent.** La part de l'attente de connexion reste marginale (≤ 1,2 %), et Seq ne
  montre ni `53300` ni pool épuisé sur l'ensemble de la campagne.
- Les backends sont échantillonnés toutes les 5 s, tous chemins confondus (PgBouncer et chemin direct
  de contrôle). Ils ne divergent pas entre les profils : la mutualisation ne crée pas de pression
  Postgres à ces échelles.

## Verdict

| Borne ou mécanisme | Verdict |
|---|---|
| Pool Npgsql et PgBouncer par base (`Max Pool Size`, `max_db_connections`) | **Garder.** Aucune contention jusqu'à 10 personnes par base. |
| Analyse CDA et IA par message | **Conforme.** 1 par message, quel que soit N. |
| Synchronisation | **Conforme.** Une synchro par boîte. Effet de bord connu : les préférences de notification sont celles de la personne qui l'a lancée (task-414). |
| `MaxSessionsPerMailbox` (sessions IMAP et SMTP par boîte) | **À changer.** Il faut le passer par personne : à 5 personnes, l'acquisition SMTP est ×7 et l'archivage ×2. |
| Verrou de récupération d'un message | **À instruire.** Les lecteurs d'un message en cours de récupération attendent jusqu'à 27 s au p95 à 10 personnes. |

## Tasks de suite proposées (à arbitrer par le PO, non créées)

1. **Sessions par personne sur une boîte partagée.** Était couvert par **task-411** (abandonnée par décision humaine le 2026-10-30), règle 6
   (`MaxSessionsPerMailbox` par personne). La mesure le justifie : envoi ×2 à 5 personnes.
   - **Gain attendu** : envoi et archivage ramenés à la référence (~420 ms).
   - **Contrôle** : rejouer `n5-shared` et `n10-shared`.
2. **Lecture concurrente d'un même message.** Quand un message est déjà en cours de récupération par une
   autre personne, l'attendre puis relire la base, ou servir les en-têtes déjà connus, au lieu de faire
   la queue sur le verrou.
   - **Gain attendu** : ouverture ramenée de ~1 s à ~0,45 s à 5 et 10 personnes.
   - **À instrumenter d'abord** : la profondeur de file par message. La métrique n'existe pas : on ne
     voit aujourd'hui que l'attente cumulée par verrou.

## Outillage corrigé pendant le tir (règle d'or)

- **`reset-state.sh` et `verify.sh` ne voyaient plus aucune base depuis task-404.** Le nom de base ne
  porte plus le RPPS. La purge répondait « (aucune) » et la vérification « aucun mail », sans erreur.
  Les deux scripts recalculent désormais les noms depuis les identités du banc, et
  `reset-state.sh --users N` limite la purge. `pg-statements.sh` et `pg-connections.sh` filtraient
  aussi l'ancien motif.
- **Le profil « boîte partagée » réutilisait les sessions du tir de référence.** Sa sonde a reçu un 409
  (garde de task-365 : une session est liée à une boîte). L'identifiant de session porte désormais la
  boîte ouverte quand ce n'est pas celle de la personne.

## Données brutes

- `Docs/audits/boite-partagee-charge-2026-10-30.json` (extraction : k6, Prometheus, échantillonneur
  Postgres). Les rapports par tir restent dans `Api/Mail/tests/loadtest-k6/reports/2026-10-30/`,
  répertoire non versionné ; leur ligne est dans `reports/INDEX.md`.
- Fenêtres des tirs (UTC) :

  | Tir | Fenêtre |
  |---|---|
  | n2-ref | 10:52:24–10:55:31 |
  | n2-partagée | 11:12:40–11:15:46 |
  | n5-ref | 10:57:00–11:00:10 |
  | n5-partagée | 11:00:50–11:04:00 |
  | n10-ref | 11:04:41–11:07:55 |
  | n10-partagée | 11:08:39–11:11:52 |
- Le premier `n2-partagée` (10:56) a été refusé au `setup()` (409, sessions réutilisées) puis rejoué
  après le correctif. Le compteur de sessions IMAP actives de ce rejeu inclut les sessions résiduelles
  du tir précédent : il n'est pas exploité.
