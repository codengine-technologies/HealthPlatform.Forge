# Coût CPU de l'analyse d'un mail — phase 0 du 2026-10-31

> Banc api-mail.
> - Code : `develop 3e3ae9ce`, 5 réplicas, **build Debug** (voir § Banc).
> - Tireur : k6bench. Banc mail : cluster, latence IMAP 96 ms.
> - IA : tout OpenAI, **étiquetage désactivé** pendant le tir, vectorisation active.
> - Scénario `enrich` : 16 médecins, boîtes 1..250, lots de 10 UID jamais analysés (463..611), 8 min.
>   Réserves remises à zéro par `reset-state.sh --keep-analysed 462 --users 250`.
> - Résultat k6 : 2 128 lots, 0 erreur, 0 court-circuit, lot p50 3,54 s, identique au palier 16 de
>   l'escalier ([plafond d'enrichissement](api-mail-loadtest-plafond-enrichissement-20261031.md)).
> - **Fenêtre propre de 180 s** (t+75 s à t+255 s, aucun profileur attaché) : **7 987 mails, soit 44,4 mails/s**.
>   Le profil de piles a été pris ensuite, 90 s, sur une seule réplique.

## Question

Où partent les ~100 ms de CPU API par mail, et pourquoi l'hôte en consomme-t-il ~4 fois plus ?
C'est la phase 0 du plan de réduction du coût CPU : mesurer avant d'optimiser.

## 1. Le CPU de l'hôte, attribué en entier (19,0 cœurs)

Échantillonneur Windows `\Process(*)\% Processor Time` toutes les 5 s, 28 échantillons dans la fenêtre propre.

| Poste | Cœurs | ms par mail | En production ? |
|---|---|---|---|
| VM WSL (`vmmemWSL`) | 6,23 | 140 | — |
| … dont Postgres | 1,44 | 32 | **oui** |
| … dont PgBouncer, RabbitMQ, Redis, Flagsmith, Seq, collecteur OTel | 1,02 | 23 | en partie |
| … dont virtualisation et réseau de la VM (non attribués aux conteneurs) | ~3,8 | ~85 | non |
| **API, 5 réplicas** (Prometheus : 114,6 ms par mail) | 5,37 | 121 | **oui** |
| **Defender (`MsMpEng`)** | **2,04** | **46** | non |
| Docker Desktop (`com.docker.backend`, relais réseau hôte ↔ conteneurs) | 1,54 | 35 | non |
| `wmiprvse` (sondes de l'échantillonneur) | 0,61 | 14 | non |
| Tableau de bord Aspire (reçoit l'OTLP) | 0,58 | 13 | non |
| dcp (capture la console des réplicas) | 0,46 | 10 | non |
| System, wsl, svchost, divers | ~1,4 | ~31 | non |

**Ce qui va en production** : ~120 ms d'API et ~32 ms de Postgres par mail, plus une part de PgBouncer,
de RabbitMQ et de Redis. Le reste (~60 % du CPU du poste) est le prix du banc Windows : Defender,
Docker Desktop, la VM WSL, Aspire.

## 2. Le CPU de l'API, par famille (profil de piles, une réplique, 90 s)

Seuls les échantillons où le thread exécutait du code managé sont gardés (21 077 échantillons utiles).
C'est une borne basse : le travail natif (GC, TLS, zlib) n'y figure pas. Les pourcentages se lisent en
part du CPU managé utile.

| Famille | Part | Détail mesuré |
|---|---|---|
| **Chaîne CDA** | **~34 %** | PDF → texte (PdfPig) 6,2 %, assainissement HTML du document 5,8 %, extraction du zip **sur disque** 5,4 %, `CdaValidator` 4,9 %, `XDM.Load` 4,2 %, XSLT 2,4 %, détection du style embarqué 2,3 %, HTML → Markdown 1,3 % |
| Réseau, TLS et clients hors code applicatif | ~22 % | TLS 10,1 %, Npgsql 5,3 %, RabbitMQ 2,7 %, Redis 2,5 %, sockets 1,8 % |
| **Relais SSE par Redis** | **~10 %** | `RedisSseBackplane.Receive` 8,9 %, en quasi-totalité de la désérialisation JSON |
| Vectorisation (consommateur asynchrone) | ~6 % | relecture du mail, borne d'entrée, deux `UPDATE` d'embedding |
| Écriture du mail (EF Core) | ~4 % | persistance, étiquette de catégorie, doublons, prédécesseurs |
| Contacts patient et praticien | ~4 % | recherches par INS et par RPPS, mises à jour |
| Journalisation (Serilog, `ILogger`) | ~2 à 3 % | 32 événements par mail, contention sur la sortie console |

**Hors travail utile**, sur l'ensemble des échantillons managés :
- 23 % de threads arrêtés pour le GC (`PollGC`) ;
- 20 % de threads du pool qui tournent à vide ;
- 9 % d'attente active sur des verrous (`Monitor.Enter`).

### Ce que le détail désigne

1. **PDF → texte (PdfPig)** :
   - la moitié du temps est de l'**attente sur un verrou interne de PdfPig** (`OperatorToken.Create`) : les
     extractions parallèles se gênent ;
   - le PDF est d'abord décodé depuis le base64 puis décompressé.
2. **Assainissement HTML du document** :
   - l'essentiel part dans l'analyse d'URL d'AngleSharp sur des **URI `data:`** (images en base64 dans le
     rendu du CDA), dont les `StringBuilder` grossissent à chaque attribut.
3. **`CdaValidator.Validate`** (interop-cda) :
   - construit un `XmlSchemaSet` **par document, jamais utilisé** ;
   - charge le CDA dans un `XmlDocument` **deux fois** (`HasEmbeddedStyle`, puis `LoadXml`), puis une
     troisième fois par `LoadFromFile`.
4. **Extraction du zip sur disque** :
   - création de répertoire, écriture, relecture, suppression récursive ;
   - c'est ce que Defender scanne : 2 cœurs du poste.
5. **Relais SSE** :
   - chaque mail analysé publie sur Redis un événement qui porte le `MailDto` **entier**, contenu et
     documents compris, **encodé en chaîne JSON dans le JSON de l'enveloppe** ;
   - **chaque réplique** reçoit et désérialise chaque enveloppe (`Receive`), avant que `Deliver` ne constate
     qu'aucun client n'écoute cette boîte ;
   - ce coût **croît avec le nombre de réplicas × le débit total**, pas avec le travail de la réplique.
     C'est un défaut d'échelle.
6. **GC** :
   - 286 collectes gen2 pour 258 gen0 en 180 s : plus de gen2 que de gen0, signature d'une pression sur le
     tas des gros objets (messages ~124 Ko, PDF, chaînes JSON entières) ;
   - pauses : 10,1 s cumulées sur 5 réplicas.

## 3. SQL par mail (`pg_stat_statements`, fenêtre propre)

- **58,5 requêtes par mail**, dont 11,6 contrôles internes de clé étrangère, soit **46,9 allers-retours
  client par mail**.
- Postgres : 10 ms d'exécution par mail, mais 32 ms de CPU par mail. L'écart est le coût fixe par requête.

| Famille | Par mail |
|---|---|
| Transactions (`BEGIN`, `COMMIT`, `SAVEPOINT`) | 9,99 |
| Lectures de `MailMedicalDocuments` | 7,73 |
| Audit (`SET LOCAL ROLE` + `INSERT`, avec sa transaction) | 3,93 |
| Lectures de `MailContents` | 3,10 |
| **`DISCARD ALL`** (remise à zéro de connexion par Npgsql, inutile derrière PgBouncer en mode transaction) | 2,66 |
| Biologie, documents, pièces jointes, destinataires, contenu, mail (`INSERT`) | ~8,3 |
| Embeddings (`UPDATE` du contenu et des documents) | 3,04 |
| Contacts (`SELECT`) | 1,98 |
| Étiquette de catégorie (`SELECT` + `INSERT`) | 3,0 |

## 4. Banc : deux constats qui faussent les chiffres absolus

- **L'API tourne en build Debug** (`bin\Debug\net10.0`, `--configuration Debug`). Le code applicatif n'est
  pas optimisé par le JIT. Les comparaisons entre tirs restent valables (même build), mais le CPU par mail
  est surestimé par rapport à la production. **Écart non mesuré.**
- **Defender scanne les fichiers temporaires de l'extraction XDM** : 2 cœurs, 46 ms par mail.

## Conclusion — priorités révisées

| Rang | Lot | Dépôt | Ce qui est visé | Gain borné par la mesure |
|---|---|---|---|---|
| 1 | Chaîne CDA : schéma inutile, triple lecture, URI `data:` dans l'assainissement, verrou PdfPig (extraction hors chemin synchrone ou en série), zip en mémoire | interop-cda, api-mail | ~34 % du CPU managé de l'API, et Defender sur le poste | jusqu'à ~1/3 du CPU API |
| 2 | Relais SSE : enveloppe filtrable sans désérialiser la charge, charge allégée (identifiants, pas le contenu) | api-mail | ~10 %, croissant avec le nombre de réplicas | ~10 % à 5 réplicas |
| 3 | SQL : `No Reset On Close`, audit regroupé, lectures de documents dédoublonnées, prédécesseurs seulement si remplacement | api-mail | 46,9 allers-retours par mail | CPU API (Npgsql), PgBouncer, Postgres |
| 4 | Tas des gros objets : tampons poolés, pas de chaînes de charge entière | api-mail | gen2 > gen0, 23 % de threads suspendus | à mesurer après 1 et 2 |
| 5 | Journalisation : 32 → ≤ 3 événements par mail, console hors Development | api-mail, interop-cda | ~2 à 3 % de l'API, dcp et Aspire sur le poste | faible pour l'API |

**Banc** :
- jambe A/B en **Release** pour chiffrer l'écart avec la production ;
- exclusion Defender du répertoire temporaire de l'API ;
- garder `observe.ps1` aveugle à MsMpEng n'est plus acceptable : l'échantillonneur par processus de cette phase 0
  doit rejoindre le harnais.

Sources (`Api/Mail/tests/loadtest-k6/reports/2026-10-31/`) :
- `phase0-cpu-c16-20261031-183917.{txt,json}` ;
- `observe-183058.csv`, `phase0-procs-183058.csv` ;
- `pgstats-phase0-183522.tsv` ;
- `phase0-profil-api-51676.txt`, `phase0-profil-utile-api-51676.txt` ;
- Prometheus du banc (`dotnet_process_cpu_time_seconds_total`, `mssante_enrichment_*`, `dotnet_gc_*`) ;
- Seq (`/api/data`).
