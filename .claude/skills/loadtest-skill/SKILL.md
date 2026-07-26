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
- **Postgres métier** joignable sur `localhost:5432` (base d'api-mail — **pas**
  orchestrée par l'AppHost). Sans elle, api-mail ne démarre pas.
- **.NET 10** (`dotnet`).
- **k6** (binaire local ou image `grafana/k6`) — pour l'étape 4.

## Étape 1 — Lancer le backend + le banc

Depuis `Api/Mail/`, utiliser le **profil de lancement dédié** (il pose
`MSS_LOADTEST=true` **et** `MSS_ENFORCE_PSC_IDENTITY=false`, ce qui évite d'avoir
à forger un token PSC cohérent — un `X-PSC-Token` non vide suffit alors) :

```bash
cd Api/Mail
dotnet run --project src/AppHost --launch-profile https-load-test
```

Ce que le profil démarre (en plus des dépendances habituelles) :

| Conteneur | Rôle | Ports (proxy Aspire) |
|---|---|---|
| `loadtest-dovecot` | **IMAP** de test — auth wildcard, maildir **disque** | IMAPS 3993 (→ 993 conteneur) |
| `loadtest-greenmail` | **Puits SMTP** de test | SMTPS 3465 |
| `loadtest-toxiproxy` | Latence réseau devant les serveurs mail | API 8474, IMAP 13993, SMTP 13465 |

**Attendre que api-mail réponde** (boot ~30-90 s : migrations DB + Flagsmith).
**Point clé — l'endpoint d'api-mail sous l'AppHost est `http://localhost:5052`**
(l'endpoint « metrics » sert toutes les routes). Ce n'est **ni 7012** (dev
standalone) **ni 17254** (= dashboard Aspire, qui redirige vers `/login`).
Sonder jusqu'à obtenir 200 :

```bash
for i in $(seq 1 20); do
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 \
    "http://localhost:5052/api/v1/connection/status" \
    -H "X-Test-Bypass: loadtest-local-only" \
    -H "Client-Email: loadtest-1@loadtest.local" -H "X-PSC-Token: loadtest")
  echo "poll $i: connection/status=$code"; [ "$code" = "200" ] && break; sleep 8
done
```

`{"mode":"online",...}` en 200 = banc prêt.

## Étape 2 — Injecter les emails (seed)

```bash
cd Api/Mail
dotnet run --project tests/mss.mail.loadtest.seed -- \
  --users 20 --messages 50 --api http://localhost:5052
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
curl -s "http://localhost:5052/api/v1/mail/folders" \
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
curl -s -X POST "http://localhost:5052/api/v1/mail/folders/INBOX/emails/enrich/sync" \
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

### Trois plafonds à connaître avant d'interpréter un chiffre

| Plafond | Symptôme | Conduite |
|---|---|---|
| **Limiteur api-mail** : 100 req / 10 s **par identité PS** (task-090, fenêtre fixe) | HTTP 429, p95 superbe mesuré sur des rejets | le harnais se cadence à 6 req/s par identité et échoue sur le moindre 429 (`rate_limited_429: count==0`) |
| **`mail_max_userip_connections=10`** (défaut Dovecot) : 10 connexions IMAP par (utilisateur, IP), tous les VU partageant une IP | HTTP 500, `IOException` en pleine `AUTHENTICATE` | **monter en charge par `USERS`, pas par VU par utilisateur** ; borne aussi `SESSION_ROTATION` à quelques millièmes sur 10 utilisateurs |
| **Bases Postgres par utilisateur persistantes** | tout `enrich` court-circuite (voir étape 6) | `tests/loadtest-k6/reset-state.sh` |

### Deux réserves sur les baselines livrées

- **`send`** : les boîtes du banc n'ont **pas de dossier `Sent`**. L'envoi SMTP
  réussit, puis `AppendToSentAsync` échoue en `FolderNotFoundException` — le
  endpoint répond `200` (archivage non fatal par conception), mais la latence
  mesurée inclut cet échec. À re-mesurer si le banc provisionne un `Sent`.
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
tests/loadtest-k6/report.sh "$K6JSON" --expected 50            # --expected = --messages du seed
```

> **Toujours vérifier que le `.md` existe** après coup. `report.sh` affiche
> « → Rapport : … » **avant** de savoir si l'écriture a réussi : la ligne annonce
> un chemin, elle ne prouve rien.
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
| `dcp.exe` | orchestrateur Aspire (proxie 5052/17254) | non — suit l'AppHost |

```bash
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'
taskkill /T /F /PID <PID de mss.mail.AppHost.exe>
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
> YES=1 tests/loadtest-k6/reset-state.sh   # bases synthétiques + volume maildir
> ```
>
> **`YES=1` n'est pas optionnel en usage automatisé.** Sans lui, le script demande
> `Supprimer ces bases ? [y/N]` ; en shell non interactif le `read` reçoit EOF,
> le script répond « abandon. » et **sort en code 1 sans rien supprimer**. Piège
> vicieux : quand il n'y a rien à purger il affiche `(aucune)` et sort en 0, donc
> il *paraît* fonctionner — et ce n'est qu'au tir suivant, avec des bases
> présentes, qu'il abandonne silencieusement et que tout `enrich` se retrouve
> court-circuité. **Toujours vérifier le compte après purge** :
> `docker exec postgres-pgvector psql -U postgres -tAc "select count(*) from pg_database where datname like 'u\_9%'"`
> doit renvoyer 0.
>
> Le filtre de noms est étroit (RPPS = `9` + 10 chiffres) : les bases des
> utilisateurs de dev réels ne matchent pas — vérifié, 4 bases de dev préservées.
>
> **Après suppression, redémarrer l'AppHost** : api-mail garde en cache le nom
> de base et répond `500` au seed sinon (« settings not confirmed (POST
> status=500) » sur tous les utilisateurs). Puis rejouer le seed.

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
- **Endpoint** : toujours `http://localhost:5052` (pas 7012, pas 17254).
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

- **`localhost` ≠ `127.0.0.1` dans Git Bash.** `localhost` y résout en IPv6
  (`::1`), où les conteneurs Docker n'écoutent pas. Un
  `</dev/tcp/localhost/5432` renvoie « fermé » alors que Postgres tourne très
  bien. **Toujours `127.0.0.1`** dans les sondes shell et les `curl`. (Ce faux
  négatif a fait conclure à tort que le prérequis Postgres manquait.)
- **Conversion de chemins MSYS.** Avant tout `docker exec`, `taskkill` ou
  argument commençant par `/` : `export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'`.
  Sans ça, `/etc/dovecot/dovecot.conf` devient `C:/Program Files/Git/etc/...` et
  `taskkill //T` est rejeté.
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
| `[AppendToSentAsync] Failed to append message to Sent folder` + `MailKit.FolderNotFoundException` | les boîtes du banc n'ont **qu'`INBOX`** — pas de dossier `Sent`. L'envoi SMTP a réussi ; seul l'archivage échoue, traité comme non fatal (le endpoint répond `200`). À savoir : la latence mesurée de `send` inclut cet échec (task-174, baseline.md) |

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
- Tout changement d'endpoint/port, d'options du seed, de clé de bypass, ou du
  mot de passe IMAP du banc.
