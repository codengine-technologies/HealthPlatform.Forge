---
name: loadtest-skill
description: >-
  Orchestration du banc de test de charge d'api-mail (EPIC E015,
  ADR-2026-07-25-B). Lance le backend avec le profil « loadtest » (AppHost
  Aspire : GreenMail/Dovecot + Toxiproxy), injecte des emails synthétiques
  porteurs de pièces jointes IHE_XDM.ZIP réelles, puis déclenche/vérifie le
  traitement (pipeline CDA), puis tire la charge avec le harnais k6
  (task-174). Utiliser pour : monter le banc de charge, seeder des boîtes de
  test, lancer un test de charge api-mail, exercer la pipeline de traitement
  des emails. INVOKES : dotnet CLI (AppHost + seed), Docker (GreenMail/Dovecot/
  Toxiproxy), curl (API + bypass), k6 (tir), Seq (vérification).
allowed-tools: Read, Bash
---

# Load-test bench skill — api-mail

Orchestre le banc de charge d'`api-mail` : **binaire de production inchangé**,
l'écosystème MSSanté est remplacé par un serveur mail mocké + injection de
latence, piloté par le profil `loadtest` de l'AppHost. Chemins relatifs à
`Api/Mail/`.

> **Ce skill évolue avec le banc.** Voir « Évolution du skill » en fin de
> document pour ce qui reste à tenir à jour.

## État d'avancement du banc

| Brique | Statut | Task |
|---|---|---|
| Profil AppHost `loadtest` + seed + injection IHE_XDM.ZIP | ✅ livré | task-173 (mergée) |
| Endpoint bypass + profil `https-load-test` (enforce off) | ✅ livré | develop |
| Serveur IMAP **Dovecot** (débloque le parsing CDA) | ✅ livré | task-195 |
| Harnais **k6** (scénarios, thresholds, Grafana) | ✅ livré | task-174 |
| Vérification par base + rapport MD comparable + analyse Seq | ✅ livré | develop (task-198) |
| **Palier 200 utilisateurs validé** (915 req/s, 0,02 % err, verify PASS) | ✅ mesuré 2026-07-27 | rapport `reports/2026-07-27/report-mixed-mssante-60vu-003515.md` |
| **PgBouncer mode transaction** au profil loadtest (multiplexage mesuré) | ✅ livré, **tir comparatif 200 encore dû** | task-200 (PR #125, non mergée) |

> ⚠️ **Le palier 200 exige une configuration précise** (3 causes de crash
> mesurées sinon : gel du relais IPv6 Docker, OOM-kill Postgres, épuisement des
> ports éphémères Windows) : chaîne de connexion `Host=127.0.0.1` + `Maximum
> Pool Size=2;Connection Idle Lifetime=600` dans l'AppHost, et Postgres
> `max_connections=2500` / 12 GiB (encodé dans
> `DevOps/Dev/PostgreSQL/docker-compose.yml`). Détails et formules :
> `DevOps/DIMENSIONNEMENT-POSTGRESQL-API-MAIL.md`. La règle de fond :
> **connexions retenues ≈ praticiens × réplicas × Max Pool Size** — la demande
> suit le nombre de praticiens, pas le trafic.

> **IMAP = Dovecot, SMTP = GreenMail** (depuis task-195). Le blocage du fetch
> partiel `BODY[part]` est levé : le scénario **pipeline CDA** est pleinement
> exerçable. Reproduit et verrouillé par
> `tests/mss.mail.integration.tests/LoadTest/DovecotBenchSmokeTests.cs` — la même
> assertion échoue contre GreenMail (`System.FormatException: Failed to parse
> entity headers`) et passe contre Dovecot.

> ⚠️ **Nouveau depuis task-195 — le mot de passe IMAP est vérifié.** GreenMail
> tournait en `auth.disabled` (tout mot de passe passait) ; la `passdb` statique de
> Dovecot le contrôle. Une seule valeur (`loadtest` par défaut), alignée en trois
> endroits : `src/AppHost/dovecot/dovecot.conf`, `TestMode__Password` de l'AppHost
> (surcharge `MSS_LOADTEST_PASSWORD`), et le seed (`--mail-password` /
> `LoadTestPlanGenerator.DefaultPassword`). Un désalignement = échec
> d'authentification IMAP sur tout le banc.

## Prérequis

- **Docker Desktop** démarré (conteneurs GreenMail/Dovecot + Toxiproxy).
- **Postgres métier** joignable sur `127.0.0.1:5432` (base d'api-mail — **pas**
  orchestrée par l'AppHost). Sans elle, api-mail ne démarre pas. C'est aussi
  l'upstream de PgBouncer, atteint depuis le conteneur par `pgupstream`
  (`--add-host=…:host-gateway`) et **jamais** par `host.docker.internal` — voir
  les pièges d'environnement.
- **.NET 10** (`dotnet`).
- **k6** (binaire local ou image `grafana/k6`) — pour l'étape 4.
- **Python 3** — prérequis **dur** de l'étape 5 (`report.py`, stdlib seule).
  Sans lui, `report.sh` ne produit **ni rapport ni ligne d'INDEX**, tout en
  annonçant trois chemins : panne silencieuse. Installé le 2026-07-27
  (3.13.14, `winget install Python.Python.3.13 --scope user`). Contrôle :
  `python --version` doit répondre `Python 3.x` — s'il répond « Python was not
  found », c'est le stub Microsoft Store qui masque l'installation (ordre du
  PATH, ou terminal ouvert avant l'installation).

## Mode DISTANT — serveurs mail sur le cluster k8s (task-221)

Depuis task-221, les serveurs mail simulés peuvent quitter l'hôte sous test :
Dovecot/GreenMail/Toxiproxy tournent sur le cluster (manifests
`DevOps/Staging/LoadtestMail/`, namespace `healthplatform`, PV NFS
`persistentvolumes/pv-nfs-loadtest.yaml`). **Obligatoire au-delà de ~500
praticiens** : en local, Dovecot vole 2,6 cœurs au SUT et son coût suit la
population — tout chiffre > 500 mesuré banc local est un artefact connu.

**Déploiement (humain — accès cluster)** :

```bash
# pré-requis : /data/loadtest-mail existe sur le serveur NFS 192.168.0.7
kubectl apply -k DevOps/Staging --dry-run=client   # contrôle
kubectl apply -k DevOps/Staging
kubectl -n healthplatform get pods,pvc             # 3 pods Ready, PVC Bound
```

**Lancement du banc en mode distant** — une seule variable, lue par l'AppHost
(aucun conteneur mail local ne démarre) ET par le seed (défaut de `--mail-host`) :

```bash
cd Api/Mail
MSS_LOADTEST_MAIL_HOST=<ip-noeud> dotnet run --project src/AppHost --launch-profile https-load-test
dotnet run --project tests/mss.mail.loadtest.seed -- --mail-host <ip-noeud>   --users 20 --messages 50 --api http://127.0.0.1:5052 --latency <100-RTT>
```

Surface NodePort (pendants exacts des Services k8s — `SeedOptions.Remote*`) :

| NodePort | Rôle |
|---|---|
| 30993 | IMAPS des praticiens (via Toxiproxy — latence injectée) |
| 30465 | SMTPS des praticiens (via Toxiproxy) |
| 30994 | IMAPS **direct** (seed uniquement — l'injection ne passe JAMAIS par la latence) |
| 30474 | API d'administration Toxiproxy |

**Les pièges du mode distant** :

- **RTT à soustraire, aux DEUX endroits** : mesurer le RTT poste ↔ cluster en
  début de campagne (connexion TCP chronométrée — le ping ICMP ne traverse pas
  les port-forwards), puis poser `100 − RTT` sur `--latency` du seed **ET** sur
  `LATENCY_MS` des tirs k6 (le `setup()` de chaque tir ré-applique le profil,
  qui vaut 100 ms en dur sinon). Consigner RTT et latence dans le rapport.
- **Un seul monde à la fois** : `MSS_LOADTEST_MAIL_HOST` posée → l'AppHost ne
  démarre AUCUN conteneur mail local ; sinon les UserSettings désigneraient
  tantôt le banc local, tantôt le cluster.
- **Un redémarrage du pod Toxiproxy perd les proxies** (mêmes causes qu'en
  local) : rejouer le seed avec `--messages 0 --mail-host <ip-noeud>`.
- **`doveadm` passe par kubectl**, plus par un port :
  `kubectl -n healthplatform exec statefulset/loadtest-dovecot -- doveadm who`
  (idem pour les contrôles boîte témoin). Le fond des contrôles ne change pas.
- **Purge du maildir distant** : plus de `docker volume rm` — vider le PVC :
  `kubectl -n healthplatform exec statefulset/loadtest-dovecot -- sh -c 'rm -rf /srv/mail/*'`
  (ou recréer le pod après nettoyage côté NFS). `reset-state.sh` (bases
  Postgres) reste inchangé — Postgres est resté local.
- **CPU de Dovecot enfin attribuable** : `kubectl top pods -n healthplatform`
  donne le coût des serveurs mail séparément du SUT — le relever dans le
  rapport à chaque palier.
- ⚠️ **Dovecot sur NFS est un cas de dégradation documenté** (maildir
  metadata-heavy). Atténuations en place : 1 seul pod, index sur `emptyDir`
  local, `mmap_disable`/`mail_fsync=never` dans la ConfigMap. **Verdict par
  smoke comparatif obligatoire** (mêmes opérations local vs cluster :
  `folders_cold`, `enrich` 10 UIDs, lecture froide) ; si la dégradation
  dépasse ~2× sur les chemins IMAP, s'arrêter et demander à l'humain un
  stockage local-path — ne pas adopter des chiffres qu'on sait faussés.
- **Mot de passe IMAP : toujours trois endroits**, dont un sur le cluster
  désormais — la `passdb` de la ConfigMap (`DevOps/Staging/LoadtestMail/dovecot.yaml`),
  `TestMode__Password` de l'AppHost, `--mail-password` du seed.
- La conf Dovecot du cluster est **portée depuis**
  `src/AppHost/dovecot/dovecot.conf` : toute évolution de l'un doit être
  reportée dans l'autre (plafonds de concurrence, dossiers spéciaux…).

## Étape 1 — Lancer le backend + le banc

**Rituel pré-vol obligatoire** (deux états résiduels font échouer ou figer le
démarrage, tous deux mesurés) :

```bash
taskkill /F /IM dcp.exe /T 2>/dev/null          # dcp.exe SURVIT à l'AppHost et
                                                # verrouille l'état DCP (Device or resource busy)
rm -rf ~/.dcp/state.elevated ~/.dcp/mruPorts.elevated.list   # état DCP élevé corrompu
                                                # = AppHost figé sans erreur (cf. mémoire)
```

Depuis `Api/Mail/`, utiliser le **profil de lancement dédié** (il pose
`MSS_LOADTEST=true` **et** `MSS_ENFORCE_PSC_IDENTITY=false`, ce qui évite d'avoir
à forger un token PSC cohérent — un `X-PSC-Token` non vide suffit alors) :

```bash
cd Api/Mail
dotnet run --project src/AppHost --launch-profile https-load-test
```

Variante équivalente qui rend l'AppHost **visible au MCP `aspire`** (le MCP ne
détecte pas un AppHost lancé par `dotnet run`) :

```bash
MSS_LOADTEST=true MSS_ENFORCE_PSC_IDENTITY=false aspire run --project src/AppHost
```

> **Niveau de log du banc : `Information`, comme la Production (task-203).**
> Le profil loadtest tourne en `ASPNETCORE_ENVIRONMENT=Development`, donc
> `appsettings.json` s'appliquerait avec `MinimumLevel: Debug` — mesuré sur la
> fenêtre du tir 500 praticiens : **904 839 événements Debug** pour 1 212 478
> Information, ~5 000 événements/s expédiés à Seq par 5 réplicas. L'AppHost
> surcharge donc `Serilog__MinimumLevel__Default` et `Logging__LogLevel__Default`
> à `Information` en profil loadtest **uniquement**.
> Pour refaire un tir bavard (mesure du coût de l'observabilité) :
> `MSS_LOADTEST_LOG_LEVEL=Debug` avant de lancer l'AppHost.
> Contrôle en une requête Seq : `select count(*) from stream where @Level = 'Debug'`
> sur la fenêtre du tir → **0** en configuration nominale.
>
> **Mesuré le 2026-07-28, ne pas re-débattre** : à 540 req/s (point valide),
> couper `Debug` retire **49 % du volume** (208 796 événements sur 140 s) et ne
> change **rien** au débit (540,0 req/s dans les deux cas) ni au p95 (−0,5 %).
> Le seul coût visible est ~1 cœur d'ingestion **côté Seq**, pas côté application.
> Le niveau de log est donc un levier de **fidélité et d'hygiène**, pas de
> performance. Protocole du contrôle : redémarrage → échauffement de 60 s **jeté**
> → mesure de 2 min, les deux niveaux rejoués (jamais comparés à un tir antérieur :
> un redémarrage vide les pools de sessions IMAP et Npgsql).

> ### ⚠️ Un redémarrage de l'AppHost EFFACE les proxies Toxiproxy
>
> Les proxies `dovecot-imap` / `greenmail-smtp` sont créés par l'outil de **seed**,
> pas par l'AppHost. Après tout redémarrage, `GET http://127.0.0.1:8474/proxies`
> renvoie `{}` et **tout tir meurt dans `setup()`** :
> `Toxiproxy profile "mssante" could not be applied — proxy "dovecot-imap" not
> found (HTTP 404) — run the seed tool first` (code de sortie k6 **107**).
>
> Remède **non destructif** — recrée les proxies et revérifie les `UserSettings`
> sans toucher au maildir ni aux bandes d'UID (donc sans re-seeder 20 000 messages) :
>
> ```bash
> dotnet run --project tests/mss.mail.loadtest.seed -- \
>   --users 200 --messages 0 --api http://127.0.0.1:5052
> ```
>
> Le maildir vit dans le volume nommé `loadtest-dovecot-mail` et survit, lui, au
> redémarrage (vérifié : 3,3 Go intacts).

Ce que le profil démarre (en plus des dépendances habituelles) :

| Conteneur | Rôle | Ports (proxy Aspire) |
|---|---|---|
| `loadtest-dovecot` | **IMAP** de test — auth wildcard, maildir **disque** | IMAPS 3993 (→ 993 conteneur) |
| `loadtest-greenmail` | **Puits SMTP** de test | SMTPS 3465 |
| `loadtest-toxiproxy` | Latence réseau devant les serveurs mail | API 8474, IMAP 13993, SMTP 13465 |
| `loadtest-pgbouncer` | **Multiplexeur de connexions PostgreSQL**, mode transaction (task-200) | 6432 (→ 6432 conteneur) |

> **PgBouncer — deux routes vers Postgres depuis task-200.** En profil loadtest,
> le **chemin de données** d'api-mail passe par PgBouncer
> (`MSS-MAIL-CONNECTIONSTRING` → `127.0.0.1:6432`) tandis que le **chemin de
> contrôle** — verrou consultatif de provisionnement, `CREATE DATABASE`,
> `MigrateUp` — reste en direct sur Postgres
> (`MSS-MAIL-CONNECTIONSTRING-DIRECT` → `127.0.0.1:5432`). Hors profil loadtest,
> la variable directe **n'est pas définie** et tout retombe sur la chaîne
> serveur : comportement identique à l'avant-task-200.
>
> Le mapping `docker ps` affiche un port hôte **aléatoire** (`…->6432/tcp`) :
> c'est normal, comme pour Dovecot. C'est le **proxy Aspire** qui écoute sur
> `127.0.0.1:6432`. Contrôle : `netstat -ano | grep LISTENING | grep ':6432\b'`.
>
> Configuration montée depuis `src/AppHost/pgbouncer/` (`pgbouncer.ini` +
> `userlist.txt`). Verdict de compatibilité, réserves et pièges :
> `Api/Mail/docs/ADR-2026-07-27-pgbouncer-transaction-mode.md`.

**Attendre que api-mail réponde** (boot ~30-90 s : migrations DB + Flagsmith).
**Point clé — l'endpoint d'api-mail sous l'AppHost est `http://127.0.0.1:5052`**
(l'endpoint « metrics » sert toutes les routes). Ce n'est **ni 7012** (dev
standalone) **ni 17254** (= dashboard Aspire, qui redirige vers `/login`).
Sonder jusqu'à obtenir 200 :

```bash
for i in $(seq 1 20); do
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 \
    "http://127.0.0.1:5052/api/v1/connection/status" \
    -H "X-Test-Bypass: loadtest-local-only" \
    -H "Client-Email: loadtest-1@loadtest.local" \
    -H "Client-Psc-Sub: 00000000-0000-4000-8000-000000000001" \
    -H "Client-Rpps: 90000000001" \
    -H "X-PSC-Token: loadtest")
  echo "poll $i: connection/status=$code"; [ "$code" = "200" ] && break; sleep 8
done
```

`{"mode":"online",...}` en 200 = banc prêt.

> ⚠️ **`Client-Rpps` et `Client-Psc-Sub` ne sont PAS décoratifs dans cette
> sonde.** Sans eux, `UserContextInfo` retombe sur `FallbackRpps = "0"` et
> **provisionne une base distincte** `u_0_{slug}_{hash}` au lieu de
> `u_9{index}_…`. Ces bases parasites **échappent au filtre `u_9%`** de
> `reset-state.sh` (filtre volontairement étroit pour protéger les bases des
> utilisateurs de dev réels) : elles ne sont **jamais purgées** et s'accumulent
> — 3 constatées le 2026-07-27. La version ci-dessus les évite. Inventaire :
> `select datname from pg_database where datname like 'u\_0\_%'`. Ne pas les
> supprimer en masse sans vérifier qu'aucune n'appartient à un utilisateur de dev
> sans claim RPPS.

## Étape 2 — Injecter les emails (seed)

```bash
cd Api/Mail
dotnet run --project tests/mss.mail.loadtest.seed -- \
  --users 20 --messages 50 --api http://127.0.0.1:5052
```

Le seed, dans l'ordre : (1) configure les proxies Toxiproxy (`dovecot-imap`
13993→Dovecot 993, `greenmail-smtp` 13465→GreenMail 3465) ; (2) injecte dans
chaque boîte `loadtest-{n}@loadtest.local` des messages synthétiques **portant
une vraie PJ `IHE_XDM.ZIP`** (round-robin sur `Tools/EmailSender.Console/
JEUX_TESTS_FULL`) ; (3) écrit les `UserSettings` par utilisateur via l'API
(IMAP → Dovecot, SMTP → GreenMail, via Toxiproxy), **avec read-back de
vérification**.

**Marqueur de propriété dans l'objet** (task-198) : chaque objet d'email
commence par `[loadtest-{n}]` (`LoadTestPlanGenerator.OwnerMarker`), où `n` est
l'index de l'utilisateur destinataire. Ce marqueur — placé en tête pour survivre
à la troncature à 512 caractères, terminé par `]` pour que `[loadtest-1]` ne
préfixe jamais `[loadtest-10]` — permet à l'étape de vérification (`verify.sh`)
de prouver, base par base, (1) que tous les emails ont bien été stockés et
(2) qu'aucune boîte ne contient l'email d'un autre utilisateur (non-mélange).

Options utiles : `--users N`, `--messages M`, `--api <url>`, `--latency <ms>`,
`--xdm-dir <path>`, `--no-xdm` (mails texte simples), `--no-proxy`,
`--bypass-key <clé>`, `--mail-password <mdp>`.

> 💡 **`--messages 0` = re-câblage sans injection.** Les proxies Toxiproxy
> vivent en mémoire du conteneur : **tout redémarrage de l'AppHost les perd**,
> et le tir k6 suivant échoue en setup (`proxy "dovecot-imap" not found (HTTP
> 404) — run the seed tool first`). Rejouer le seed avec `--messages 0`
> reconfigure les proxies et ré-écrit/vérifie les `UserSettings` **sans
> ajouter un seul message** au maildir — c'est le geste standard après tout
> redémarrage d'AppHost entre deux tirs.

**Le seed sort en erreur (exit ≠ 0) et liste les utilisateurs fautifs** si un
`UserSettings` n'a pas pu être posé/relu — ne jamais considérer un seed
« réussi » sans le message final `settings written AND read-back verified for N
users`. (Le seed ne suit plus les redirections : une mauvaise `--api` échoue
franchement au lieu d'un faux succès.)

**Volumétrie & disque** (task-195) : les messages vivent sur le maildir **disque**
de Dovecot (volume nommé `loadtest-dovecot-mail`), plus dans un heap JVM — les gros
corpus sont donc possibles. Deux conséquences : mesurer l'occupation avec
`docker volume inspect loadtest-dovecot-mail`, et savoir que le contenu **persiste
entre les sessions** — les seeds successifs **s'accumulent**. Repartir vierge :
`docker volume rm loadtest-dovecot-mail` (conteneur arrêté).

## Étape 3 — Déclencher / vérifier le traitement

### Identités virtuelles (déterministes)

Pour l'utilisateur `n` :
- `Client-Email: loadtest-{n}@loadtest.local`
- `Client-Psc-Sub: 00000000-0000-4000-8000-{n:000000000000}` (n sur 12 chiffres)
- `Client-Rpps: 9{n:0000000000}` (9 + n sur 10 chiffres)
- `X-Test-Bypass: loadtest-local-only`
- `X-PSC-Token: loadtest` (n'importe quelle valeur non vide, enforce=false)

### Lecture simple (folders / mode online)

```bash
curl -s "http://127.0.0.1:5052/api/v1/mail/folders" \
  -H "X-Test-Bypass: loadtest-local-only" \
  -H "Client-Email: loadtest-1@loadtest.local" \
  -H "Client-Psc-Sub: 00000000-0000-4000-8000-000000000001" \
  -H "Client-Rpps: 90000000001" \
  -H "Client-Session-Id: sess-1" -H "X-PSC-Token: loadtest"
```

Un `Client-Session-Id` **stable** par utilisateur virtuel réutilise la session
IMAP poolée (chaud ~0,2 s vs froid ~1,3 s) — c'est le comportement à charger.

### Pipeline CDA (opérationnelle depuis task-195 / Dovecot)

```bash
curl -s -X POST "http://127.0.0.1:5052/api/v1/mail/folders/INBOX/emails/enrich/sync" \
  -H "Content-Type: application/json" \
  -H "X-Test-Bypass: loadtest-local-only" \
  -H "Client-Email: loadtest-1@loadtest.local" \
  -H "Client-Psc-Sub: 00000000-0000-4000-8000-000000000001" \
  -H "Client-Rpps: 90000000001" \
  -H "Client-Session-Id: sess-1" -H "X-PSC-Token: loadtest" \
  -d '[1,2,3]'
```

`enrich/sync` prend un **corps JSON = liste d'UIDs**.

> ### ⚠️ ORDRE DES APPELS — la règle qui fait rater la mesure
>
> **`enrich/sync` AVANT toute lecture.** Dès qu'un `MailContent` existe pour un
> UID — et **une simple lecture le crée** — les enrichissements suivants sont
> ignorés. L'endpoint répond alors `200` en ~25 ms **sans rien parser**, ce qui
> ressemble à un succès.
>
> Écart mesuré, même banc, mêmes UIDs : **4,3 s** (travail réel, 10 UIDs) contre
> **0,024 s** (court-circuit). Un facteur ~180. Si votre `enrich` répond en
> dizaines de millisecondes, il n'a rien fait.
>
> Cette erreur a été commise deux fois malgré la présence de l'avertissement en
> prose — d'où le squelette de tir plus bas, qui impose l'ordre.

**Vérification du parsing** via Seq (MCP `seq-local` si dispo, sinon UI Seq) —
la pipeline a tourné si l'on voit `[CdaParsingService] Parsing completed` et que
`GET .../emails/{uid}` renvoie `hasMedicalDocuments: true`. Filtre Seq utile :
`@MessageTemplate like '%Parsing completed%'`.

### Squelette de tir multi-utilisateurs (en attendant k6)

Ordre imposé : `folders` froid → **`enrich` froid** → lecture → `folders` chaud.
Sur boîtes vierges (volume fraîchement supprimé, cf. étape 6).

```bash
API="http://127.0.0.1:5052"; VU=5          # 127.0.0.1, PAS localhost (cf. pièges)
hdr() {
  printf -v R "9%010d" "$1"; printf -v S "00000000-0000-4000-8000-%012d" "$1"
  echo "-H|X-Test-Bypass: loadtest-local-only|-H|Client-Email: loadtest-$1@loadtest.local|-H|Client-Psc-Sub: $S|-H|Client-Rpps: $R|-H|Client-Session-Id: $2|-H|X-PSC-Token: loadtest"
}
call() { # user session scenario method path [body]
  local IFS='|'; read -ra H <<< "$(hdr "$1" "$2")"
  local x=(); [ "$4" = POST ] && x=(-X POST -H "Content-Type: application/json" -d "$6")
  echo "$3,$1,$(curl -s -o /dev/null -w '%{http_code} %{time_total}' --max-time 900 "${H[@]}" "${x[@]}" "$API$5")" >> raw.csv
}
for u in $(seq 1 $VU); do call $u cold-$u-$RANDOM folders_cold GET /api/v1/mail/folders & done; wait
for u in $(seq 1 $VU); do call $u tir-$u enrich_froid POST /api/v1/mail/folders/INBOX/emails/enrich/sync '[1,2,3,4,5,6,7,8,9,10]' & done; wait
for u in $(seq 1 $VU); do call $u tir-$u read GET /api/v1/mail/folders/INBOX/emails/1,2,3,4,5 & done; wait
for p in 1 2 3; do for u in $(seq 1 $VU); do call $u tir-$u folders_chaud GET /api/v1/mail/folders & done; wait; done
```

**Route de liste** : `GET .../emails/{ids}` avec des UIDs séparés par des virgules.
Il n'existe **pas** de `?page=&pageSize=` sur ce contrôleur (renvoie 404).

## Résultats de référence (mesurés le 2026-07-25, banc Dovecot)

Ordres de grandeur pour juger un run — machine de dev, latence Toxiproxy 100 ms,
corpus `JEUX_TESTS_FULL`. Un écart marqué signale un problème, pas une variation.

| Scénario | p50 | Lecture |
|---|---|---|
| `folders` session **froide** | 0,7 – 1,05 s | connexion IMAP + ouverture de session |
| `folders` session **chaude** | **0,011 – 0,014 s** | pooling actif — ~95× moins cher qu'à froid |
| `read` après enrichissement | 0,06 s | servi depuis la base |
| `read` avant enrichissement | ~0,9 s | va chercher sur IMAP |
| `enrich` **froid** (10 UIDs) | **4,3 s** | travail réel : téléchargement + parsing CDA |
| `enrich` court-circuité | 0,024 s | **n'a rien fait** — cf. l'avertissement ci-dessus |

Repères de volumétrie et de résultat :

- **~88 à 94 % des messages** produisent des documents médicaux. Les autres sont
  des archives du corpus **sans CDA exploitable** — ne pas viser 100 %.
  Relevés : 44/50 (tir 5 VU), 94/100 (tir 20 VU).
- **Maildir** : ~8 Mo pour 50 messages, ~71 Mo pour 400 (≈ 124 Ko de PJ par message).
- **Seed** : ~1 min pour 5 × 10, ~5 min pour 20 × 20 (APPEND séquentiel sous latence).
- **0 erreur HTTP** attendu à ces échelles ; toute erreur est un signal.

## Étape 4 — Tir k6 (livré par task-174)

Harnais dans `tests/loadtest-k6/`. Six scénarios : `folders`, `read`, `search`,
`send`, `enrich` (pipeline CDA), `mixed`. Mode d'emploi complet dans
`tests/loadtest-k6/README.md`, chiffres de référence dans
`tests/loadtest-k6/baseline.md`.

```bash
cd Api/Mail
export BYPASS_KEY=loadtest-local-only

tests/loadtest-k6/run.sh folders                                  # smoke 10 VU / 60 s
PROM=1 tests/loadtest-k6/run.sh mixed --env VUS=50 --env DURATION=5m
tests/loadtest-k6/run.sh enrich --env VUS=4                       # pipeline CDA
```

`run.sh` (ou `run.ps1`) crée le répertoire de rapport daté — k6 ne crée pas de
répertoire et perd son résumé sans le dire — et branche la sortie Prometheus
remote-write quand `PROM=1`. Tableau de bord **« k6 — tests de charge
api-mail »** dans le Grafana du banc (`http://localhost:3001`).

Tout se pilote par variables d'environnement (`USERS`, `VUS`, `DURATION`,
`RPS_PER_USER`, `LATENCY_PROFILE`, `SESSION_ROTATION`, seuils `THR_*`…).
`BYPASS_KEY` n'a **aucun défaut** dans les scripts.

Un run sous la cible sort en **code non nul** (thresholds k6) : la baseline est
une garde anti-régression, pas un rapport.

Le harnais a ses propres auto-tests (JS + Python, donc hors `dotnet test`), à
rejouer après toute modification de `lib/`, `scenarios/` ou `report.py` :

```bash
tests/loadtest-k6/selftest.sh     # aucune dépendance, aucun banc requis
```

### Quatre plafonds à connaître avant d'interpréter un chiffre

| Plafond | Symptôme | Conduite |
|---|---|---|
| **Le harnais lui-même** (task-203) : un scénario à débit imposé ne délivre que `maxVUs / latence` | débit qui plafonne quel que soit `USERS`, `dropped_iterations` par centaines/s, `vus == vus_max` | pools dimensionnés par la loi de Little (`lib/vu-sizing.js`) ; **lire d'abord la section « Validité du tir » du rapport** — 16 des 21 tirs archivés avant le 2026-07-28 sont invalides |
| **Limiteur api-mail** : 100 req / 10 s **par identité PS** (task-090, fenêtre fixe) | HTTP 429, p95 superbe mesuré sur des rejets | le harnais se cadence à 6 req/s par identité et échoue sur le moindre 429 (`rate_limited_429: count==0`) |
| **`mail_max_userip_connections=10`** (défaut Dovecot) : 10 connexions IMAP par (utilisateur, IP), tous les VU partageant une IP | HTTP 500, `IOException` en pleine `AUTHENTICATE` | **monter en charge par `USERS`, pas par VU par utilisateur** ; borne aussi `SESSION_ROTATION` à quelques millièmes sur 10 utilisateurs |
| **Bases Postgres par utilisateur persistantes** | tout `enrich` court-circuite (voir étape 6) | `tests/loadtest-k6/reset-state.sh` — ⚠️ purger change le coût de `read`, donc le dimensionnement : voir juste en dessous |

### ⚠️ La contradiction purge / dimensionnement (task-209)

**Deux exigences du banc se contredisent, et il faut la connaître AVANT
d'imputer des abandons à l'application.**

Une campagne d'escalier **purge les tables entre paliers** (sinon `enrich`
court-circuite). Or les latences de référence qui dimensionnent les pools de VUs
(`lib/vu-sizing.js`, loi de Little) avaient été mesurées **base pleine** : `read`
y valait 0,16 s l'itération. Sur base purgée, `read` repart sur IMAP et coûte
**0,41 s** sous le genou. Le pool ne peut alors pas offrir le débit demandé, k6
jette la différence, et le rapport disait « la charge nominale n'a jamais été
appliquée » — une phrase qui accuse l'application d'un défaut du harnais. C'est
ce qui a rendu la première campagne du 2026-07-29 et les quatre tirs du
2026-07-31 inexploitables.

Depuis task-209, le rapport porte une section **« Latence planifiée vs
mesurée »** qui compare l'hypothèse du plan à la mesure et **nomme la cause
candidate des abandons**. La lire avant toute conclusion :

| Ce que dit le rapport | Ce qu'on fait |
|---|---|
| *cause : dimensionnement* (écart > 2× et file ThreadPool calme, ou abandons sans écart) | re-tirer avec la latence observée — le rapport imprime la ligne exacte, du type `ITER_SECONDS_READ=0.41 tests/loadtest-k6/run.sh mixed …` |
| *cause : congestion serveur* (écart > 2× **et** file ThreadPool ≥ 100) | **baisser le débit demandé. Ne PAS élargir les pools** |
| *cause indéterminée* (aucun témoin serveur sur la fenêtre) | monter le banc en profil loadtest (collector `loadtest-otel-collector`) et régénérer le rapport — les deux remèdes sont opposés |

**Élargir les pools aggrave — mesuré, ne pas re-débattre.** Même budget
(882 req/s), seul `VU_TAIL_FACTOR` change, 8 → 16 : débit délivré 824,8 →
716,4 req/s (−13 %), abandons 4,21 % → 13,49 %, p95 1 309 → 6 766 ms, files
ThreadPool 136 → 951. Au-delà du genou, plus de concurrence cliente alimente une
file bloquante côté serveur.

Corollaire pour re-mesurer les constantes : **toujours nommer les conditions**.
Un chiffre pris base pleine ne remplace pas un chiffre pris base purgée. Les
constantes portent désormais leur date et leurs conditions
(`REFERENCE_MEASURED_AT`, `REFERENCE_CONDITIONS`), recopiées dans le contexte de
chaque tir archivé. Elles décrivent le régime **sous le genou** — dimensionner
sur la latence d'un palier haut reviendrait à nourrir la congestion.

### Lire la colonne « Exceptions /s » du rapport (task-206)

La colonne « Exceptions /s » de la table **« Par réplica api-mail »** (ajoutée
par task-204) n'était pas lisible : le banc levait **une exception par requête**,
et ce bruit noyait tout le reste.

**Cause, corrigée depuis.** Le harnais envoyait `X-PSC-Token: loadtest` — une
valeur non vide mais **pas un JWT** — au motif que le profil du banc pose
`MSS_ENFORCE_PSC_IDENTITY=false`. api-mail tentait quand même de la parser :
`SecurityTokenMalformedException`, avalée, requête poursuivie. Mesuré le
2026-07-29 : **12 668 occurrences en 121 s** à 106 req/s (≈1,2 par requête), et
**plus de 1 200/s** au plafond de charge, le débit croissant linéairement.

**Ordre de grandeur attendu après correction** :

| Famille | Attendu | Lecture |
|---|---|---|
| `SecurityTokenMalformedException` | **0** | toute occurrence = régression. Le harnais forge un vrai JWT par identité, et api-mail contrôle la forme avant de parser |
| Total « Exceptions /s » par réplica | **quelques unités**, pas des centaines | au-delà de ~10/s soutenus, chercher la famille avant de conclure quoi que ce soit sur la capacité |
| `FolderNotFoundException` | **0** depuis `118c3f4` (2026-08-01) | les boîtes du banc déclarent désormais `Sent` / `Drafts` / `Trash` et l'archivage aboutit réellement (`doveadm` : Sent messages=1). Toute occurrence = régression de la conf Dovecot. ⚠️ Cette ligne annonçait « non nulle, bénigne » jusqu'à task-214 : c'était vrai avant `118c3f4`, où l'archivage échouait après **chaque** envoi (~73/s) |
| `HttpRequestException`, `FlagsmithAPIError` | ponctuelles | dépendances externes du banc |
| `IOException`, `XmlException` | ponctuelles | à regarder si elles croissent avec la charge |

**Le test qui tranche** — une famille dont le débit croît **linéairement avec la
charge** est un coût par requête, pas un incident. C'est le signe qu'un chemin de
code est exercé à chaque appel ; le chercher avant d'interpréter un chiffre de
capacité.

```bash
curl -s --get 'http://127.0.0.1:9090/api/v1/query' \
  --data-urlencode 'query=sum by (error_type) (increase(dotnet_exceptions_total[2m]))'
```

⚠️ **Fidélité du banc** : `PSC_TOKEN` est désormais **vide par défaut**, ce qui
fait forger au harnais un token à la forme d'un vrai JWT (claims `sub` /
`SubjectNameID` par identité). Poser `PSC_TOKEN=loadtest` reproduit l'ancien
comportement — utile pour re-mesurer le défaut, à ne pas laisser dans une
campagne dont on veut publier le chiffre : un débit mesuré sur un autre chemin
d'authentification que celui déployé n'est pas opposable.

### Lire la table « `imap_session`, par opération » (task-214)

**Une étiquette absente n'établit pas qu'une opération n'a pas eu lieu.** Le
2026-08-01, cette table a imprimé *« Aucune acquisition `AppendToSent` — le tir
n'a pas archivé d'envoi »*. C'était faux : l'archivage tournait (GreenMail à
0,38 cœur, 13 973 envois à 0,38 % d'erreurs, sessions Dovecot doublées à 5 002),
il n'était simplement **pas instrumenté** — `ImapLockScope`, l'API de vingt
sites d'appel sur vingt-et-un, n'émettait aucun histogramme. La table ne pouvait
donc afficher que `ProcessEmailUid`, **sur n'importe quelle campagne**.

| Ce que montre la table | Lecture | Geste |
|---|---|---|
| Aucune série | Instrumentation absente ou collector muet | Vérifier le binaire déployé (task-214 mergée ?) et le collector |
| Séries présentes, `AppendToSent` absent, **voie d'écriture à 0** | **Indécidable** | Regarder la ligne `send` de « Débit demandé vs délivré » : débit d'envoi non nul ⇒ défaut d'instrumentation, pas un tir sans archivage |
| Séries présentes, voie d'écriture non nulle | Instrumentation vivante | L'absence d'`AppendToSent` désigne bien une opération non exercée |

La table **« Voie | Acquisitions /s »** répond à la question que le banc du
2026-08-01 ne pouvait pas poser : *le doublement des sessions IMAP est-il
imputable à la voie d'écriture de task-213 ?*

### Deux réserves sur les baselines livrées

- **`send`** : réserve **levée** par `118c3f4` (2026-08-01) — les boîtes
  déclarent `Sent` / `Drafts` / `Trash` et l'archivage aboutit. ⚠️ En
  contrepartie, **les baselines antérieures ne sont plus comparables** : elles
  mesuraient un envoi dont l'archivage échouait, donc plus court. Toute
  comparaison de `send` avec un tir d'avant cette date est à écarter.
- **`search`** : baseline **provisoire** tant que task-196 n'est pas livrée —
  les documents longs n'ont pas de vecteur, l'index sémantique est incomplet.

## Étape 5 — Vérification par base + rapport de tir (OBLIGATOIRE, AVANT le nettoyage)

> **L'ordre est impératif : rapport AVANT nettoyage.** La vérification par base
> lit les bases Postgres synthétiques `u_9…` — l'étape 6 les supprime
> (`reset-state.sh`). Produire le rapport une fois le banc nettoyé donnerait
> « aucune base trouvée / 0 mail ». On exécute donc l'étape 5 **immédiatement
> après le dernier tir k6, banc encore debout**, sans la proposer.

Un tir n'est pas mesuré tant qu'il n'a pas produit (1) la preuve d'intégrité
des données par utilisateur et (2) un rapport MD comparable, complété par
l'analyse Seq. Trois sous-étapes.

### 5a — Rapport déterministe (vérification + KPI + index)

```bash
cd Api/Mail
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'
K6JSON=$(ls -t tests/loadtest-k6/reports/*/*.json | head -1)   # dernier résumé k6
tests/loadtest-k6/report.sh "$K6JSON" --expected 10            # cf. l'encadré ci-dessous
```

> ### ⚠️ `--expected` = `MESSAGES_PER_USER` du harnais, PAS `--messages` du seed
>
> Corrigé le 2026-07-27 — la consigne précédente (« `--expected` = `--messages`
> du seed ») est **fausse dès que les deux valeurs diffèrent**. `verify.sh` compte
> les lignes de la table `"Mails"`, or **seuls les UIDs que le scénario touche**
> y arrivent. Le scénario `mixed` n'en exerce que **10** par boîte (enrichBand
> 1..5, readBand 6..10, défaut `MESSAGES_PER_USER=10`), quel que soit le nombre
> de messages seedés.
>
> Mesuré : seed à `--messages 50`, vérification à `--expected 50` → les
> 20 boîtes ressortent « incomplètes » (⚠️) alors que le tir est parfaitement
> sain. Avec `--expected 10` : 10/10 partout, verdict PASS.
>
> **Règle** : `--expected` = la valeur de `MESSAGES_PER_USER` passée au harnais
> (10 par défaut), pas celle du seed. Le seed peut sur-provisionner sans risque.

> ### 🛑 Le PREMIER contrôle d'un rapport : sa section « Validité du tir » (task-203)
>
> Avant de citer un débit, de comparer à un tir antérieur ou de conclure quoi que
> ce soit sur la capacité, lire la section **« Validité du tir »** du `.md` (et la
> table **« Débit demandé vs délivré »** juste après les KPI).
>
> Un tir est **invalide pour une conclusion de capacité** si l'une de ces
> conditions est vraie — le rapport s'ouvre alors sur
> `⚠️ TIR INVALIDE POUR UNE CONCLUSION DE CAPACITÉ` et le dit aussi sur `stderr` :
>
> - plus de **1 %** des itérations abandonnées (`dropped_iterations`) ;
> - pic de VU au plafond du harnais (`vus == vus_max`) sur un tir à débit imposé ;
> - `MAX_VUS` a mordu sur le dimensionnement calculé.
>
> Ce qui reste lisible dans un tir invalide : les **latences** (elles décrivent
> les requêtes réellement exécutées) et une comparaison A/B **à harnais
> identique**. Ce qui ne l'est pas : le **débit**, qui est alors celui du client.
>
> Pourquoi c'est en tête de cette étape : les trois tirs du 2026-07-27 ont publié
> 833 à 915 req/s comme s'il s'agissait d'un plafond applicatif, alors que k6
> tournait au plafond de son propre pool et jetait 45 k à 502 k itérations. À 200
> praticiens, `send` n'a servi que **14 %** de son budget et `search` **56 %** —
> faute de VU, pas faute de serveur. L'INDEX porte désormais les colonnes
> `Drop %` et `VU sat.`, recalculées pour tout l'historique.

> **Toujours vérifier que le `.md` existe** après coup. `report.sh` affiche
> « → Rapport : … », « → Index : … » et « → Dump Seq … » **avant** de savoir si
> l'écriture a réussi : les trois lignes annoncent des chemins, elles ne prouvent
> rien. Contrôle : `test -f <le .md>` et `tail -2 reports/INDEX.md`.
>
> **Python est un prérequis dur de cette étape** (`report.py`, stdlib seule).
> Absent le 2026-07-27, `report.sh` produisait **zéro fichier et zéro ligne
> d'INDEX** tout en affichant ses trois chemins — panne parfaitement silencieuse.
> Installé depuis : **Python 3.13.14** (`winget install Python.Python.3.13
> --scope user`), placé avant `WindowsApps` dans le PATH utilisateur. Attention,
> le stub Microsoft Store `WindowsApps/python` répond « Python was not found » et
> **masque** un vrai Python placé après lui dans le PATH ; et un terminal ouvert
> **avant** l'installation garde l'ancien PATH.
> Corollaire : `verify.sh` (bash + docker) ne dépend **pas** de Python — en cas
> de panne de `report.py`, la preuve de non-mélange reste récupérable, seuls les
> KPI sont à écrire à la main (percentiles globaux :
> `sed -n '/"http_req_duration"/,/^    },/p' <json>`).
>
> *Corrigé le 2026-07-26 (`10b8666` sur `develop`)* — le script n'écrivait aucun
> rapport dès qu'on le lançait depuis `Api/Mail`, l'usage que prescrit pourtant son
> propre en-tête. Deux pièges empilés, à connaître car ils reviendront ailleurs :
> `report.py` était appelé sans préfixe `$HERE/`, **et** `python` est un binaire
> natif Windows qui ne sait pas ouvrir un chemin MSYS — or le script exporte
> `MSYS_NO_PATHCONV=1` en tête pour docker, ce qui désactive la conversion
> automatique. Trois arguments étaient touchés : le script, le `mktemp`
> (`/tmp/…`) et `INDEX_MD`. Conversion explicite par `cygpath` désormais.

`report.sh` enchaîne :

1. **`verify.sh`** — pour **chaque** base `u_9<index>…`, lit la table `"Mails"`
   et compte : total stocké, sujets **possédés** (`"Subject" like '[loadtest-<idx>]%'`),
   sujets **étrangers** (marqueur d'un autre utilisateur), sujets **sans marqueur**.
   Deux objectifs — **complétude** (tous les emails stockés, vs `--expected`) et
   **non-mélange** (aucune boîte ne contient l'email d'un autre). **Un seul sujet
   étranger fait échouer le tir** (`exit 1`, verdict `FAIL_COMMINGLING`) — c'est
   l'assertion critique de sécurité.
2. **`report.py`** — extrait du JSON k6 un **schéma KPI stable** (identique à
   chaque tir, donc un tir 10 users est directement comparable à un tir 50
   users) : débit req/s, **latence moyenne + p50/p95/p99/max globales**, taux
   d'erreur, checks, 429, table de latence par opération. Écrit le rapport
   `reports/{date}/report-<testid>.md` (KPI + section vérification par base +
   placeholder Seq) et **ajoute une ligne à `reports/INDEX.md`** — le tableau
   inter-tirs qui permet de repérer la dégradation d'un volume à l'autre.

Repères de lecture : **latence moyenne et p95** sont les deux nombres à comparer
d'un tir à l'autre ; une hausse marquée à volume croissant = dégradation.
`enrich_short_circuited` doit valoir 0 (sinon le parsing CDA n'a pas tourné —
piège n°1). `Mélange` (`foreign`) doit valoir 0.

### 5a-bis — Relever le multiplexage PgBouncer (depuis task-200)

Deux chiffres à relever **pendant** le tir, et un **après**. Ni l'un ni l'autre
n'est produit par `report.py` : à consigner à la main dans le rapport.

```bash
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'
B=$(docker ps --filter "name=loadtest-pgbouncer" --format '{{.Names}}')

# pools, connexions clientes et FILE D'ATTENTE (cl_waiting) — le chiffre qui compte
docker exec "$B" env PGPASSWORD=pgbouncer \
  psql -h 127.0.0.1 -p 6432 -U pgbouncer pgbouncer -c 'SHOW POOLS'

# backends RÉELS — toujours sur Postgres EN DIRECT, le pooler ne se mesure pas lui-même
docker exec postgres-pgvector psql -U postgres -tAc \
  "select count(*) as total, count(*) filter (where datname like 'u\_%') as praticien
   from pg_stat_activity"
```

`PGPASSWORD` est **nécessaire** (`auth_type = plain`, identité `pgbouncer`
déclarée dans `userlist.txt`) — une commande `SHOW POOLS` sans elle échoue.

Repères mesurés le 2026-07-27, tir `mixed` 20 utilisateurs / 20 VU
(`report-mixed-mssante-20vu-130917.md`) :

| Grandeur | Valeur | Lecture |
|---|---|---|
| Connexions clientes par base praticien | 8 à 10 | demande de 20 praticiens × 5 réplicas |
| **Backends réels pendant le tir** | **71** (61 sur bases praticien) | ≈ 3 par base = `max_db_connections=3` |
| **Backends après le tir** | **6** | relâchés par `server_idle_timeout=60` |
| **`cl_waiting`** | **0** partout | ⚠️ **le chiffre à surveiller** — non nul = pooler sous-dimensionné |

À comparer aux **~2 000 connexions retenues** de la campagne 200 praticiens
**sans** pooler. `cl_waiting > 0` soutenu est le risque résiduel n°1 identifié
par l'ADR (`max_db_connections=3` par base est volontairement serré) : il ne se
manifeste pas à 20 praticiens, il reste à éprouver à 200.

### 5b — Analyse Seq systématique + dump (OBLIGATOIRE, jamais silencieuse)

**Toujours**, en fin de tir, interroger le MCP `seq-local` sur la fenêtre du tir
et **remplir la section « ## Analyse Seq (findings) »** du rapport `.md` généré
en 5a. En parallèle, écrire le **dump brut** des événements à côté du rapport :
`reports/{date}/seq-<testid>.jsonl` (le nom est imprimé par `report.sh`).

Requêtes Seq minimales à couvrir (via `mcp__seq-local__get_events`) :

- Erreurs / warnings hors bruit de boot : `@Level in ['Error','Fatal','Warning']`.
- Parsings CDA réussis : `@MessageTemplate like '%Parsing completed%'` (compter —
  doit approcher le nombre de PJ enrichies).
- Régression connue du fetch partiel : `@MessageTemplate like '%Failed to parse entity headers%'`
  (doit être **0** sous Dovecot — sa présence = retour de GreenMail côté IMAP).
- 429 (limiteur) et erreurs de connexion IMAP (`IOException` en `AUTHENTICATE`).
- Corrélation `UserEmail` : vérifier que les logs de traitement bus la portent
  (enrichissement task-198 `develop`, filtre `UserContextLogEnricherFilter`).

**Consigner les findings dans le rapport**, pas seulement à l'écran : le rapport
MD est le livrable comparable entre tirs, l'IA le relit d'un run à l'autre. Une
absence d'erreur est elle-même un finding (« RAS hors bruit de boot »).

> Si le MCP `seq-local` est indisponible, écrire explicitement dans la section
> « Analyse Seq (findings) » : « seq-local indisponible — analyse non faite »,
> plutôt que de laisser le placeholder. Ne jamais rendre un rapport avec la
> section Seq vide.

### 5b-bis — Télémétrie fine : établir les CAUSES (OBLIGATOIRE — consigne humaine du 2026-08-03)

`report.py` produit les **symptômes** (latence par étape, coûts résidents,
verdict SLO). Il ne dit **jamais pourquoi**. Cette sous-étape est la
contrepartie : pour **chaque étape hors grille**, établir la cause par la
télémétrie, et l'écrire dans le rapport sous « Télémétrie fine ».

**⚠️ À préparer AVANT le tir si l'on veut le MCP `aspire`** : il ne détecte pas
un AppHost lancé par `dotnet run` et n'expose rien une fois l'AppHost arrêté.
Lancer alors `MSS_LOADTEST=true MSS_ENFORCE_PSC_IDENTITY=false aspire run
--project src/AppHost`. Sinon l'analyse retombe sur seq-local seul — ce qui
suffit souvent, mais **doit être dit** dans le rapport.

**1. Décomposer UNE requête représentative de chaque étape hors grille**
(MCP `seq-local`) — c'est ce qui transforme un symptôme en cause :

```
filtre : RequestPath like '%<la route>%' and SourceContext = 'mss.mail.api.Middleware.RequestLoggingMiddleware'
→ relever le TraceId d'une requête dont ElapsedMs est proche du p50
filtre : TraceId = '<le trace id>'
→ dérouler les évènements et calculer les Δ entre eux
```

Ce que ça a donné le 2026-08-03 sur l'ouverture d'un message (439 ms) : 19 ms de
contexte, puis **420 ms dans le verrou de session IMAP avec `WaitTimeMs=0`** —
donc du travail, pas une file. Un re-tir n'aurait pas donné cette information.

**2. Confronter le temps client au temps serveur** (Prometheus). Écart nul ⇒ le
temps est **dans** l'application ; écart large ⇒ file hors d'elle (client, proxy,
réseau) :

```promql
histogram_quantile(0.95, sum by (le, http_route) (rate(http_server_request_duration_seconds_bucket[10m])))
```

**3. Chercher la métrique à la source AVANT tout contournement.** Lister
`/api/v1/label/__name__/values` et regarder ce qui existe déjà. Exemple vécu :
les sessions IMAP ont été comptées par `netstat` alors que
`mssante_imap_sessions_active` / `_connected` / `_authenticated` existaient.

**4. Écrire ce que la télémétrie n'a PAS pu dire.** C'est le backlog
d'instrumentation de l'US de correctif. Exemple : le décompte des allers-retours
IMAP **par requête** manque, donc « 420 ms ≈ 4 allers-retours » reste compatible
et non prouvé.

> ### ⚠️ Deux pièges de lecture, rencontrés le 2026-08-03
>
> - **Une `rate[...]` évaluée « maintenant » rend une série VIDE** après la fin du
>   tir. Toujours passer `time=<instant DANS la fenêtre du tir>` à l'API
>   Prometheus — sinon on conclut « aucune donnée » sur une campagne parfaitement
>   instrumentée.
> - **Après l'arrêt de l'AppHost, Prometheus survit mais son port n'est plus
>   proxifié** (le proxy DCP meurt avec lui) : `127.0.0.1:9090` répond `000`
>   alors que le conteneur est sain. Retrouver le port réattribué par
>   `docker port <conteneur-prometheus>`, ou requêter par
>   `docker exec <conteneur> wget -qO- 'http://localhost:9090/api/v1/query?...'`.

### 5c — Enchaîner le nettoyage

Une fois le rapport écrit, l'index mis à jour, le dump Seq sauvegardé et les
findings consignés → passer à l'étape 6 (arrêt + purge).

## Étape 6 — Arrêter et nettoyer le banc (OBLIGATOIRE, pas optionnelle)

> **Un tir n'est pas terminé tant que le banc n'est pas rendu.** L'étape 6 fait
> partie du run, au même titre que le seed : on l'exécute sans la proposer et sans
> attendre qu'on la demande.
>
> Une fois le tir fini, le backend ne fait **rien d'utile** — vérifié : zéro
> événement applicatif dans Seq après la dernière requête, pas de synchronisation,
> pas d'enrichissement. Il retient seulement des connexions IMAP poolées, ses
> écouteurs HTTP, de la mémoire, et il continue d'accumuler des archives CDA en
> clair dans `%TEMP%`. Le laisser tourner n'apporte rien et coûte des ressources.
>
> Exception unique : l'humain a explicitement demandé à garder le banc debout pour
> l'inspecter lui-même.

### Identifier le bon processus (trois candidats, un seul est le bon)

Un banc en marche présente **trois** processus qui ressemblent à l'AppHost. Tuer
le mauvais ne l'arrête pas :

```bash
netstat -ano | grep LISTENING | grep -E ':(22234|17254|5052)\b'   # -> PID Windows
ps -W | awk '$4==<PID> {print $NF}'                                # -> identité
```

| Processus | Rôle | À tuer ? |
|---|---|---|
| `mss.mail.AppHost.exe` | **le vrai AppHost** (port 22234) | **oui**, avec `/T` |
| `dotnet.exe` (`dotnet run`) | simple lanceur | meurt avec son enfant |
| `dcp.exe` | orchestrateur Aspire (proxie 5052/17254) | **oui, explicitement** — *contrairement à ce que ce skill affirmait*, il **survit** au kill de l'AppHost et garde `~/.dcp/state.elevated` verrouillé (`Device or resource busy` à la purge). Mesuré le 2026-07-26. |

```bash
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'
taskkill /T /F /PID <PID de mss.mail.AppHost.exe>
sleep 8
taskkill /F /IM dcp.exe /T          # sinon la purge DCP du prochain démarrage échoue
```

Aspire détruit alors **tout seul** ses conteneurs `Session` (`loadtest-*`).
Vérifier que 5052 / 17254 / 22234 sont libres.

### Purger les données

```bash
docker volume rm loadtest-dovecot-mail          # maildir : ~71 Mo apres un tir 20 VU
find "$LOCALAPPDATA/Temp" -maxdepth 1 -regextype posix-extended \
     -regex '.*/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.zip' -delete
```

> ### ⚠️ Le volume maildir NE SUFFIT PAS — les bases par utilisateur survivent
>
> api-mail crée **une base Postgres par utilisateur** (`u_9<index sur 10
> chiffres>_…`). Les identités virtuelles étant déterministes, ces bases
> reviennent **identiques** d'un tir à l'autre : leurs `MailContents`
> court-circuitent **tout `enrich` ultérieur**, qui répond alors `200` en
> ~25 ms sans rien analyser — exactement le piège n°1, mais déclenché par un
> banc « propre » en apparence.
>
> Constaté le 2026-07-25 : maildir fraîchement supprimé et re-seedé, et
> pourtant 7 lots d'enrichissement sur 10 court-circuités, parce que les bases
> du tir précédent étaient encore là.
>
> ```bash
> cd Api/Mail
> YES=1 tests/loadtest-k6/reset-state.sh   # mode PURGE (défaut) : TRUNCATE des tables mail
> ```
>
> **Deux modes depuis le 2026-07-26 — ne pas appliquer les anciens contrôles :**
>
> - **PURGE (défaut)** : vide les tables mail (`TRUNCATE … RESTART IDENTITY`),
>   **garde les bases, leur schéma et le cache setupdb**. C'est le mode normal
>   entre deux tirs. ⚠️ Le compte de bases `u_9%` reste donc **inchangé** après
>   purge — l'ancien contrôle « doit renvoyer 0 » est **périmé**. Le bon
>   contrôle : `select count(*) from "Mails"` = 0 dans une base témoin. Pas de
>   redémarrage d'AppHost nécessaire.
> - **DROP (`--drop-databases`)** : supprime les bases. À réserver aux
>   changements de schéma — le tir suivant repaie **~16 s de `MigrateUp()` par
>   praticien** (~53 min pour 200). Et deux pièges mesurés :
>   1. **Purger les clés `setupdb:u_9*` du Redis persistant** (TTL 1 jour) —
>      sinon api-mail *saute le provisionnement* des bases supprimées et répond
>      `3D000 database does not exist` en ~20 ms pour toujours, même après
>      redémarrage :
>      `docker exec mss-mail-redis-* sh -c 'redis-cli -p 6380 -a "$REDIS_PASSWORD" --no-auth-warning --scan --pattern "setupdb:u_9*" | xargs -r redis-cli -p 6380 -a "$REDIS_PASSWORD" --no-auth-warning DEL'`
>      (6380 = port interne non-TLS du conteneur).
>   2. **Redémarrer l'AppHost ensuite** (cache DataSource + dictionnaire
>      `_migratedDatabases` in-process).
>
> **`YES=1` n'est pas optionnel en usage automatisé.** Sans lui, le script demande
> confirmation ; en shell non interactif le `read` reçoit EOF, le script répond
> « abandon. » et **sort en code 1 sans rien supprimer** — tout en affichant
> `(aucune)` et code 0 quand il n'y a rien à purger, ce qui le fait *paraître*
> fonctionner.
>
> Le filtre de noms est étroit (RPPS = `9` + 10 chiffres) : les bases des
> utilisateurs de dev réels ne matchent pas — vérifié, 4 bases de dev préservées.
>
> **Contrepartie du filtre étroit : les bases `u_0_…` ne sont jamais purgées.**
> Toute requête sans en-tête `Client-Rpps` fait retomber `UserContextInfo` sur
> `FallbackRpps = "0"` et provisionne `u_0_{slug}_{hash}`, hors du filtre `u_9%`.
> Elles s'accumulent (3 constatées le 2026-07-27). Inventaire :
> `select datname from pg_database where datname like 'u\_0\_%'`. **Ne pas les
> supprimer en masse** : une base `u_0_…` peut appartenir à un utilisateur de dev
> réel dépourvu de claim RPPS. La prévention est côté appelant — envoyer
> `Client-Rpps` (la sonde de santé de l'étape 1 le fait désormais).

La seconde commande retire les archives IHE-XDM laissées par la pipeline
(**task-185**) : un tir 20 VU en produit ~90, soit ~18 Mo de CDA **en clair** sur
disque. Le filtre sur motif GUID est délibéré — `%TEMP%` contient d'autres `.zip`
légitimes (p. ex. `cmdline-tools.zip`) qu'une suppression en bloc détruirait.

### Ne pas conclure trop vite qu'un banc est mort

Un `curl` isolé qui renvoie `000` **ne prouve rien**. Vérifier qui tient le port
22234 **avant** d'arrêter quoi que ce soit : arrêter les conteneurs d'un AppHost
encore vivant casse le banc sans le dire (l'API répond encore, mais sans serveur
IMAP). Symptôme d'un AppHost déjà en place : le redémarrage échoue sur
`Failed to bind to address https://127.0.0.1:22234: address already in use`.

## Garde-fous — non négociables

- **Jamais en Production** : le bypass est hard-blocké si
  `ASPNETCORE_ENVIRONMENT=Production` ; le profil `loadtest` n'est jamais actif
  par défaut. Ne jamais lancer ce banc sur un environnement HDS.
- **Données 100 % synthétiques** : boîtes `loadtest-*`, contenus générés, PJ
  issues de `JEUX_TESTS_FULL` (documents de test). Aucune DSCP, aucun INS réel.
- **Aucun secret en clair** dans les logs/commandes ; la clé de bypass vient du
  profil de lancement, pas d'un dur dans un script partagé.
- **Endpoint** : toujours `http://127.0.0.1:5052` (pas 7012, pas 17254).
- **Rendre le banc en fin de tir** : arrêt de l'AppHost + suppression du volume +
  purge des `.zip` de `%TEMP%` (étape 6). Un banc laissé debout n'est pas un banc
  « disponible », c'est un banc oublié : il consomme des ressources, garde des
  connexions IMAP ouvertes, et laisse des documents CDA en clair sur disque.

## Pièges connus (retours de terrain)

- **api-mail = 5052**, pas 7012/17254 (17254 = dashboard Aspire → `/login`).
- **Seed silencieux** corrigé : exige le message `read-back verified` + exit 0.
- **enforce** : le profil `https-load-test` pose `MSS_ENFORCE_PSC_IDENTITY=false`
  → un `X-PSC-Token` non vide suffit. Hors ce profil, il faut un token PSC forgé
  cohérent (`sub`/`SubjectNameID` = `Client-Psc-Sub`/`Client-Rpps`).
- **GreenMail + parsing CDA** : *résolu par task-195*. GreenMail répondait mal au
  fetch partiel `BODY[part]` → `System.FormatException: Failed to parse entity
  headers`. Ne pas réintroduire GreenMail côté IMAP ; il ne reste que le SMTP.
- **Mot de passe IMAP vérifié** (task-195) : un désalignement entre `dovecot.conf`,
  `TestMode__Password` et `--mail-password` produit un échec d'authentification sur
  tout le banc, pas un message clair. Premier réflexe si « tout casse » après un
  changement de conf.
- **Maildir persistant** (task-195) : re-seeder **ajoute** des messages. Un
  décompte inattendu = volume non purgé.
- **Court-circuit « déjà enrichi »** sur `enrich/sync` : UIDs frais requis, et
  **enrichir avant de lire** (voir l'encadré de l'étape 3 — piège n°1 du banc).

### Pièges d'environnement (Windows / Git Bash)

- **`127.0.0.1` partout, jamais `localhost` — règle générale, pas seulement
  Git Bash.** Élargie le 2026-07-27 : sous orage de connexions, le **relais
  IPv6 loopback de Docker Desktop se fige par port** (TCP accepté, données
  jamais relayées — panne 100 % silencieuse). Mesuré sur **5432** (Postgres :
  NpgsqlTimeout 15 s sur tout, y compris après redémarrages) **et 5342**
  (ingestion Seq : perte de logs totale sans une seule erreur). Or .NET résout
  `localhost` en `::1` d'abord. Donc : chaînes de connexion, `SEQ_URL`, sondes
  shell, `curl` — **tout client d'un port publié Docker cible `127.0.0.1`**.
  Diagnostic en une commande : parler le protocole sur les deux adresses
  (`SSLRequest` PG ou POST CLEF) — `127.0.0.1` répond, `::1` trou noir.
- **Troisième occurrence du même piège, côté PgBouncer (2026-07-27, task-200) :
  `host.docker.internal` est inutilisable comme upstream.** Dans le conteneur
  PgBouncer, ce nom ne résout qu'en **AAAA** (`fdc4:f303:9324::254`), et
  PgBouncer — **contrairement à `psql`** — ne retente pas sur l'autre famille
  d'adresses : son résolveur retient l'IPv6 et s'y tient. Symptôme :
  `client_login_timeout (server down)` sur **toute** connexion cliente, alors
  que le conteneur est « healthy », que le TCP est accepté (`nc -z` réussit) et
  que `SHOW POOLS` répond parfaitement. Un banc qui démarre sain et ne sert rien.
  Correctif en place : l'AppHost injecte `--add-host=pgupstream:host-gateway`
  (IPv4 déterministe, `192.168.65.254` sur Docker Desktop) et `pgbouncer.ini`
  cible `pgupstream`. **Verrouillé par un test** —
  `BenchUpstream_DoesNotRelyOnHostDockerInternal` échoue si quelqu'un rétablit
  `host.docker.internal`. Leçon générale : un client qui ne fait pas de fallback
  d'adresse transforme ce piège en panne totale, pas en lenteur.
- **Conversion de chemins MSYS.** Avant tout `docker exec`, `taskkill` ou
  argument commençant par `/` : `export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'`.
  Sans ça, `/etc/dovecot/dovecot.conf` devient `C:/Program Files/Git/etc/...` et
  `taskkill //T` est rejeté. **⚠️ Réciproque pour k6** : `run.sh` passe le chemin
  du scénario à `k6.exe`, binaire **Windows natif** — avec `MSYS_NO_PATHCONV=1`
  il reçoit `/d/TechWatch/…/folders.js` et échoue en `moduleSpecifier couldn't
  be found`. **Faire `unset MSYS_NO_PATHCONV MSYS2_ARG_CONV_EXCL` avant tout
  `run.sh`.** Les deux exports sont donc à poser/retirer par commande, jamais
  globalement.
- **Logs des réplicas api-mail** : la sortie console est dans
  `%TEMP%\aspire-dcp*\<guid>_out` (un fichier par réplica) — c'est **la**
  source pour stacks et erreurs, notamment quand Seq ne reçoit rien. Les
  `resource-executable-*.log` du même répertoire ne contiennent que la trace
  DCP. Le MCP `aspire` ne voit que les AppHost lancés par `aspire run`.
- **Python est natif Windows.** Il ne sait pas lire `/tmp/x.json` (chemin MSYS).
  Piper directement (`curl … | python -c …`) ou utiliser un chemin Windows.
- **Route de liste des messages** : `/emails/{uid1,uid2,…}`. Pas de
  `?page=&pageSize=` — cette forme renvoie **404**.

### Lire les logs du banc — bénin vs réel

Attendu et **sans gravité** pendant un run :

| Trace | Pourquoi c'est normal |
|---|---|
| `[PscKcCrossCheck] mismatch … Enforce=false` | le profil désactive l'enforcement, aucune identité PSC forgée n'est censée concorder |
| `[CdaParsingService] Missing values: … in …` | le document de test n'a pas de valeur dans cette section — preuve que le parseur descend dans le CDA |
| `[MailClientSession] ♻️ Session expired` | recyclage nominal après ~5 min d'inactivité, en fin de tir |
| `RedisConnectionException … ConnectTimeout` **au démarrage** | conteneur Redis pas encore prêt ; disparaît une fois le banc établi |
| ~~`[AppendToSentAsync] Failed to append message to Sent folder`~~ | ⛔ **N'est plus bénin depuis `118c3f4` (2026-08-01)** — les boîtes déclarent `Sent`/`Drafts`/`Trash`. Une occurrence est désormais une **régression de la conf Dovecot**, pas un comportement attendu (déplacé dans la table « à prendre au sérieux » par task-214) |

À prendre au sérieux :

| Trace | Signification |
|---|---|
| `Error extracting IHE-XDM ZIP` + `FormatException: Failed to parse entity headers` | **régression** : le serveur IMAP ne sert plus correctement `BODY[part]`. C'était la panne GreenMail que task-195 a corrigée — ne doit plus jamais apparaître avec Dovecot |
| `Failed to generate … embedding` + `maximum input length is 8192 tokens` | **task-196** : troncature en caractères et non en tokens ; le document n'entre pas dans l'index sémantique. **Intermittent** — dépend de la longueur des documents : observé sur un tir 20 VU (400 messages), absent sur un tir 5 VU (50 messages). Ne pas conclure « corrigé » sur un petit tir |

## Évolution du skill

Mettre à jour les sections 🔧 quand :
- ~~**task-195 (Dovecot)**~~ — ✅ fait : IMAP Dovecot + SMTP GreenMail,
  avertissement #187 retiré, étape 3 (pipeline CDA) opérationnelle, volumétrie
  maildir disque documentée, mot de passe IMAP vérifié signalé.
- ~~**task-174 (k6)**~~ — ✅ fait : étape 4 remplie (scénarios
  `tests/loadtest-k6/`, `run.sh`/`run.ps1`, dashboard Grafana « k6 — tests de
  charge api-mail »), plafonds limiteur/Dovecot documentés, purge des bases par
  utilisateur ajoutée à l'étape 6.
- ~~**Campagne 200 utilisateurs (2026-07-27)**~~ — ✅ fait : palier 200 validé
  et prérequis de config documentés ; rituel pré-vol DCP + kill `dcp.exe` ;
  règle `127.0.0.1` généralisée (relais IPv6 Docker) ; `unset MSYS_NO_PATHCONV`
  avant k6 ; modes PURGE/DROP de `reset-state.sh` + clés `setupdb:` Redis ;
  `--messages 0` pour re-câbler Toxiproxy ; logs réplicas via `*_out` DCP.
  ⚠️ Les réglages AppHost (127.0.0.1, pooling, SEQ_URL) sont **en attente de
  commit** sur api-mail — si un tir échoue en NpgsqlTimeout 15 s uniforme,
  vérifier d'abord que ces changements sont bien présents dans `AppHost.cs`.
- ~~**PgBouncer au profil loadtest**~~ — ✅ fait (task-200, 2026-07-27) :
  conteneur `loadtest-pgbouncer` à l'étape 1 + encadré des deux routes
  (données via pooler / provisionnement en direct), relevé du multiplexage à
  l'étape 5a-bis avec ses repères, `PGPASSWORD` requis pour `SHOW POOLS`,
  base parasite `u_0_…` documentée à l'étape 6, sonde de santé corrigée
  (`Client-Rpps` + `Client-Psc-Sub`), `--expected` redressé, Python promu
  prérequis dur. Tir de validation :
  `reports/2026-07-27/report-mixed-mssante-20vu-130917.md`.
- **À venir — tir comparatif 200 praticiens VIA PgBouncer** : c'est le critère
  qui reste dû à task-200 et qui déverrouille le prérequis §4.1 de
  `DevOps/DIMENSIONNEMENT-1000-PRATICIENS.md`. Iso-conditions avec
  `report-mixed-mssante-60vu-003515.md` (200 users, 60 VU, `mixed`, 5 min) :
  critère p95 dans la marge de 20 %, `pg_stat_activity` < 300, `cl_waiting`
  nul ou marginal. Mettre à jour les résultats de référence ensuite.
- **À venir — tir 500 praticiens** (cf. `DIMENSIONNEMENT-1000-PRATICIENS.md`),
  une fois le comparatif 200 vert.
- ~~**task-221 (serveurs mail sur le cluster)**~~ — ✅ fait : section « Mode
  DISTANT » ajoutée (déploiement kustomize, surface NodePort, RTT à soustraire,
  contrôles kubectl, purge du PVC, piège NFS + smoke comparatif obligatoire).
  Le `kubectl apply` et le smoke comparatif restent des actes humains/au banc.
- Tout changement d'endpoint/port, d'options du seed, de clé de bypass, ou du
  mot de passe IMAP du banc.
