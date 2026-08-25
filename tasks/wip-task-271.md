# todo-task-271.md — Une détention de session à 60 s est un timeout qui a un nom, pas un p95 qu'on subit

**Repos**: api-mail
**Dependencies**: —
**Epic**: E015

## Objectif

La campagne du 2026-08-23 montre une anomalie **invisible du médecin mais au
plafond de l'instrument** : la détention du verrou `imap_session` par
`GetFolders` atteint **60,000 s au p95** (une valeur au plafond exact désigne
un timeout, pas un travail de 60 s), et la route serveur `GET /mail/folders`
publie un p95 OpenTelemetry de **56,8 s** — alors que la même étape vue du
client k6 vaut 155 ms au p95. L'écart dit que ces occurrences vivent hors du
parcours jugé : vraisemblablement dans la **chauffe** (établissement de ~300
sessions fraîches au front de chaque palier) et l'extinction (4 034
`TaskCanceledException` sur le tir, ~1 par rotation de session — nominal).

**Le problème n'est pas (encore) une lenteur, c'est un angle mort.** Tant que
ces détentions à 60 s ne portent ni cause ni étiquette, elles polluent trois
lectures : le p95 serveur de la route (inutilisable pour un SLO interne), la
table des verrous (un p95 au plafond écrase tout), et toute campagne future
qui voudrait juger `GetFolders`. Le précédent est connu : « une étiquette
absente n'établit pas qu'une opération n'a pas eu lieu » (task-214) — ici,
une valeur au plafond n'établit pas ce qui l'a produite.

**Contenu attendu — caractériser, puis étiqueter ; corriger seulement si la
cause le réclame** :

1. **Établir sur pièce** ce qui détient `imap_session` 60 s sous `GetFolders` :
   quel timeout expire (connexion IMAP ? TLS ? le budget du verrou lui-même ?),
   sur quel chemin (première connexion d'une session fraîche ? reconnexion
   après péremption ?), à quels moments du tir (fronts de palier ? extinction ?).
   Les traces Seq du tir 2026-08-23 (`TraceId` des requêtes `folders` >10 s)
   et le code du gestionnaire de sessions suffisent — pas besoin d'un nouveau
   tir pour instruire.
2. **Rendre la lecture honnête** : si la cause est l'établissement de session
   (chauffe), la détention d'établissement doit être **distinguable** de la
   détention d'exploitation (étiquette dédiée sur l'histogramme du verrou, ou
   exclusion motivée), pour que le p95 de `GetFolders` redevienne lisible.
3. **Si un vrai défaut apparaît** (timeout mal dimensionné, verrou tenu
   pendant une connexion réseau qui n'en a pas besoin — le verrou n'a pas à
   couvrir TCP+TLS si la session n'est pas encore partagée) : le corriger fait
   partie de la US, avec la preuve rouge d'abord.

**Gain attendu** : un p95 `GetFolders` opposable ; au mieux, un établissement
de session qui ne tient plus le verrou pendant le handshake (moins de
contention aux fronts de palier — là où la chauffe consomme déjà 56-60 % des
fenêtres).

## Definition of Done

- [ ] Build passes (0 errors), tests pass (0 failures) sur api-mail
- [ ] La cause des détentions à 60 s est **écrite dans la task** avec les
      `TraceId` à l'appui (traces du tir 2026-08-23) et le timeout nommé
      (valeur + endroit du code)
- [ ] La détention d'établissement de session est distinguable de la détention
      d'exploitation dans la télémétrie du verrou (nouvelle étiquette testée),
      OU son exclusion est motivée par écrit si l'analyse montre qu'elle n'a
      pas sa place dans cet histogramme
- [ ] Si un correctif est livré : preuve rouge d'abord (test qui capture le
      comportement fautif avant le fix), puis vert
- [ ] Si aucun correctif n'est justifié : la task le **dit** avec la mesure à
      l'appui — « caractérisé, bénin, étiqueté » est un livrable recevable
- [ ] `report.py` : la table des verrous reste correcte avec la nouvelle
      étiquette (selftest du harnais vert, zéro SKIP)
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

- Rejouer l'analyse sur les traces existantes : Seq, fenêtre
  2026-08-23T17:32→20:07 UTC, filtre
  `RequestPath like '%/mail/folders' and ElapsedMs > 10000` → dérouler 2-3
  `TraceId` et confronter aux détentions du verrou
- Banc local, tir court avec rotation de session forcée
  (`SESSION_ROTATION` élevé) : vérifier que les détentions d'établissement
  portent la nouvelle étiquette et que le p95 d'exploitation de `GetFolders`
  reste < 1 s
- Vérifier `tests/loadtest-k6/selftest.sh` : 0 échec, 0 SKIP

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — observabilité/caractérisation interne
- **Exigences DSR honorées** : non applicable — aucun changement fonctionnel
- **INS** : non applicable
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé — les histogrammes de verrou ne portent aucune donnée de santé
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — inchangé
- **AIPD / impact RGPD** : inchangé

## Branches

- `api-mail` (pushed) : `feat/task-271-imap-session-lock-hold` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-271-imap-session-lock-hold
- `dtos-mss` (pushed, auto-included) : `feat/task-271-imap-session-lock-hold` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-271-imap-session-lock-hold

## Journal d'implémentation (/develop, 2026-08-25)

### 1. La cause, établie sur pièces — et elle contredit la prémisse de la US

La US pose : « une valeur au plafond exact désigne un timeout, pas un travail
de 60 s ». **Les deux branches sont fausses.** Ce n'est ni un timeout, ni un
travail de 60 s : c'est **le plafond de l'instrument**.

`MailProcessingMetrics.DurationBucketBoundariesSeconds`
(`src/Application/Telemetry/MailProcessingMetrics.cs:54`) se termine par
`…, 10, 30, 60`. **60 s est la dernière borne finie**, et `histogram_quantile`
de Prometheus **rend cette borne** quand le quantile tombe dans le bucket
`+Inf`. Un p95 publié à exactement `60,000` ne dit donc pas « soixante
secondes » — il dit « **au moins 60 s, et je ne sais pas combien** ». La
précision à la milliseconde était un artefact de formatage.

**Le timeout nommé, comme le DOD l'exige : il n'y en a aucun.** Recensement
exhaustif des bornes du chemin `GetFolders` :

| Borne | Valeur | Endroit |
|---|---|---|
| Budget d'attente du verrou de session | **120 s** | `MailClientSessionManager.LockImapClientAsync` (`src/Application/Session/MailClientSessionManager.cs:149`) |
| Timeout total de requête HTTP | **5 min** | `src/Api/DependencyInjectionExtensions.cs:48` |
| Téléchargement OCSP/CRL | **5 s** | `SslTlsOptions.RevocationDownloadTimeoutSeconds` |
| `ImapClient.Timeout` (MailKit) | **120 s** (défaut, jamais surchargé) | `ImapClientWrapper` — aucune affectation |

Les trois seules constantes à 60 s / 1 min du module
(`ConnectionKeepAliveInterval`, `SessionCleanupInterval`, `SmtpProbeMaxAge`)
sont des **cadences**, pas des bornes d'opération : aucune ne peut arrêter un
`GetFolders`. **Chercher un timeout à 60 s était une chasse au fantôme née du
formatage du rapport.**

Corollaire à ne pas manquer : puisque la valeur est saturée, la détention
réelle est **≥ 60 s, borne supérieure inconnue** — elle peut valoir 70 s comme
300 s. Toute conclusion quantitative tirée du « 60,000 » d'origine est non
opposable.

### 2. Ce qui est réellement long, et pourquoi c'est mêlé

Le p95 serveur de `GET /mail/folders` à **56,8 s**, lui, est une vraie mesure :
il tombe dans le bucket `[30, 60]`, donc interpolé — grossier, mais mesuré. Il
existe donc bien des requêtes `folders` de plusieurs dizaines de secondes.

`GetFoldersAsync` (`src/Application/Services/Implementation/ImapService.cs:198-235`)
tient `imap_session` pendant **`ConnectInternalAsync`** — DNS, TCP, TLS,
contrôle de révocation, AUTH — puis le LIST-STATUS. Or `imap_session` est un
verrou **par praticien** : une détention de 60 s n'est donc **pas** de la
contention entre médecins, c'est l'opération elle-même qui dure. Au front de
chaque palier la chauffe établit ~300 sessions fraîches simultanément (58-60 %
de chaque fenêtre au tir du 2026-08-23) : ces établissements-là forment la
queue, et le p95 agrégé est le leur.

D'où la réconciliation des deux chiffres qui semblaient s'exclure : **155 ms au
p95 vu de k6** (population dominée par le régime établi, cache Redis chaud) et
**≥ 60 s de détention** (population des établissements). Les deux sont vrais ;
ils ne décrivent pas la même chose, et **aucune requête ne les séparait**.

### 3. ⚠️ Les `TraceId` demandés par le DOD ne sont pas produisibles

Le DOD exige les `TraceId` des traces du tir du 2026-08-23. **Elles n'existent
plus** — dit franchement plutôt que comblé :

- Seq local (`localhost:5341`) : l'évènement le plus ancien retenu date du
  **2026-08-25T14:01Z**. La fenêtre du tir (2026-08-23T17:32→20:07Z) est sortie
  de la rétention.
- Seq distant (`log.xsd2code.com`, où partaient les logs du tir « distant ») :
  la clé d'API configurée répond **401**. Non contournable ici.
- Le rapport de campagne `report-journey-500-esc-20260823-220658.md` n'est pas
  dans le dépôt : `.gitignore:386` exclut `tests/loadtest-k6/reports/*` sauf
  `INDEX.md`, et le répertoire `2026-08-23/` est absent du disque.

**Ce que cela change, et ce que cela ne change pas.** La cause de la *valeur
publiée* (§1) est établie **sur le code et la définition de l'instrument**, pas
sur les traces : elle est démontrable et le reste sans Seq. Ce que les traces
auraient apporté en plus, c'est la **borne supérieure réelle** des détentions
saturées et leur **répartition temporelle** (fronts de palier vs extinction).
Cette part-là reste ouverte, et c'est précisément ce que l'étiquette livrée
ci-dessous rend mesurable **au prochain tir** — sans dépendre d'une rétention.

### 4. Correctif livré — l'étiquette, pas la portée du verrou

**Ce qui n'a PAS été fait, et pourquoi.** La US envisageait de sortir TCP+TLS du
verrou (« le verrou n'a pas à couvrir TCP+TLS si la session n'est pas encore
partagée »). **Écarté, sur analyse : la prémisse est fausse.** Le wrapper IMAP
est **déjà partagé** avant d'être connecté — `GetOrCreateImapClientAsync` rend
l'unique `IImapClientWrapper` de la session
(`MailClientSessionManager.cs:100-127`), et c'est **cette instance-là** que
`ConnectInternalAsync` connecte et authentifie. Établir hors verrou laisserait
deux appelants du même praticien appeler `ConnectAsync` sur le même
`ImapClient` MailKit en parallèle — exactement la classe de défaut que task-187
et task-223 ont fermée. **Le verrou doit couvrir l'établissement.** Livrer ce
« correctif » aurait échangé une mesure illisible contre une corruption de
session.

Le livrable est donc celui que le DOD prévoit en second : **rendre les deux
populations adressables.**

- **Étiquette `phase` sur `mssante_lock_hold_duration_seconds`** — deux valeurs
  littérales, `establish` / `operate`, selon que la session était déjà
  connectée **et** authentifiée quand le verrou a été pris. Résolue à
  l'**acquisition** (à la libération tout vaudrait `operate`) et **après** la
  prise du sémaphore (avant, un autre appelant pourrait établir entre la
  lecture et la prise).
- **Sonde sans effet de bord** `IMailClientSessionManager.IsImapClientEstablished` :
  lit `ImapClientWrapperOrDefault`, ne crée ni session ni wrapper. Une sonde qui
  créerait ce qu'elle observe répondrait toujours la même chose.
- **L'attente ne porte pas la phase** — délibéré, et verrouillé par un test :
  `report.py` lit l'attente sur `operation` seul.
- **PGSSI-S** : deux littéraux écrits dans le code. Aucune donnée de santé,
  aucune cardinalité non bornée — même barre que `lane` et `operation`.

### 5. Le harnais dit désormais quand il ne mesure plus

C'est la moitié qui manquait au diagnostic, et elle est structurelle : le
harnais avait déjà rencontré **deux fois** ce défaut de plafond (buckets en
millisecondes de task-211, plafond à 10 s de task-245) et l'avait corrigé les
deux fois **en déplaçant les bornes**, jamais **en rendant la saturation
visible**. Le nombre continuait de s'imprimer comme n'importe quel autre — et
c'est ce qui a produit cette US.

- `num_saturable()` : une valeur qui atteint `DURATION_HISTOGRAM_TOP_BUCKET_S`
  (60 s, aligné sur le backend et épinglé par un test) s'imprime **`≥ 60 ⚠️`**,
  jamais `60.000`. Appliquée aux cellules de quantile des deux tables de
  verrous ; **pas** aux taux (un débit de 60 acq/s n'est pas saturé).
- Deux colonnes ajoutées à « `imap_session`, par opération » : **Détention p95
  établ.** et **Détention p95 exploit.** Seule `operate` est opposable à un SLO
  interne ; `establish` mesure un coût d'entrée, pas une latence de travail.
- Trois lectures nommées explicitement plutôt que laissées à l'inférence :
  binaire non étiqueté → « l'agrégat **mélange** » ; agrégat saturé mais
  exploitation lisible → « **lecture rétablie**, la queue appartient à la
  chauffe » ; **exploitation** saturée → « 🚨 défaut de portée du verrou », qui
  ne se cache plus derrière la chauffe.

### 6. Vérification

| Contrôle | Résultat |
|---|---|
| `dotnet build HealthPlatform.Api.Mail.sln` | **0 erreur, 0 avertissement** |
| Preuve rouge d'abord (`SessionLockPhaseInstrumentationTests`) | **4 échecs** (`KeyNotFoundException: 'phase'`), puis **6/6 vert** |
| Tests de verrou existants (task-214, buckets) | 24/24 vert — aucune étiquette perdue |
| `selftest.sh` du harnais | **320 tests, OK, 0 SKIP** (dont 14 nouveaux) |
| Suite complète api-mail vs `origin/develop` | **delta zéro** — mêmes échecs des deux côtés |

**Échecs pré-existants, mesurés sur `origin/develop` en worktree isolé** (aucun
n'est une régression, aucun ne touche le verrou de session) :

- `mss.mail.application.tests` : 4 × `EmbeddingOptionsConsistencyTests` (dérive
  `appsettings.json` ↔ défauts du code) — **identiques sur develop**.
- `mss.mail.api.tests` : 6 × scans d'architecture / `SecretLiteralScanTests` —
  **identiques sur develop** (le secret Gmail committé est un connu à purger).
- `mss.mail.integration.tests` : **91 des deux côtés** — infrastructure Docker
  (Postgres/Redis) absente sur ce poste.
- `MailExportServiceTests.BuildPdfWithoutAttachmentsOmitsAttachmentSection` :
  flaky connu, **3/3 vert** en réexécution isolée.

**Un garde-fou a fait son travail** :
`SessionLockAcquisitionSurfaceTests.TheSessionManagerSurfaceIsPinned` a échoué à
l'ajout de `IsImapClientEstablished` — c'est exactement ce que cette garde
existe pour provoquer (« le moment où l'on se demande si le nouveau membre prend
le verrou sans le mesurer »). Réponse consignée dans le test : non, c'est une
lecture pure, appelée sémaphore déjà en main.

### 7. Ce que le prochain tir doit montrer

L'US est **caractérisée + étiquetée**, pas « corrigée » — et c'est le livrable
recevable que le DOD prévoit. Ce qui reste à confirmer au banc, en une ligne :
la colonne **exploitation** de `GetFolders` doit tenir sous la seconde pendant
que la colonne **établissement** porte la queue. Si l'exploitation sature à son
tour, le rapport le criera de lui-même (🚨) — et *là* il y aura un vrai défaut
de portée de verrou à instruire.

## Simplify log (/forge-simplify, 2026-08-25)

Repos éligibles touchés : `api-mail` uniquement. `dtos-mss` a une branche mais
aucun commit (aucun changement de contrat n'était nécessaire — la US est
purement observabilité), et il est de toute façon hors scope de cette étape
(porteur de contrat).

Trois findings appliqués, **qualité seulement** (aucun changement de
comportement) :

| Axe | Finding | Correctif |
|---|---|---|
| Réutilisation | `num_saturable()` redisait les deux replis de `num()` (`None`, valeur non numérique) | Elle les lui **délègue** : un seul chemin de sortie, et plus deux occasions de diverger sur le rendu d'une valeur absente |
| Simplification | `_session_lock_phase_lines()` construisait `saturated_aggregate`, liste triée qui ne servait qu'à en dériver une autre | Supprimée ; l'appartenance se lit sur un `set`, le tri se fait là où l'on rend |
| Réutilisation | L'écouteur de métriques `LockObservations` était sur le point d'exister en **double** — classe imbriquée privée de task-214, plus la copie que task-271 venait d'en faire | Extrait en helper partagé du projet de tests (`tests/.../Session/LockObservations.cs`). Les noms d'instruments y vivent aussi : deux écouteurs à garder d'accord sur le même contrat de fil, c'est une divergence qui attend son heure |

**Re-validation (filet anti-régression)** :

- `dotnet build HealthPlatform.Api.Mail.sln` → **0 erreur, 0 avertissement**
- Tests de session (`FullyQualifiedName~Session`) → **183/183 vert**
- `mss.mail.application.tests` complet → **4 échecs, tous pré-existants**
  (`EmbeddingOptionsConsistencyTests`, identiques sur `origin/develop`)
- `selftest.sh` du harnais → **320 tests, OK, 0 SKIP**

Commit : `refactor(telemetry): passe qualite sur le diff de task-271`, poussé.

## Sonar log (/sonar, 2026-08-25)

Infra : conteneurs `sonarqube_db` puis `sonarqube` redémarrés (ils étaient
`exited`), SonarQube **25.6.0**, token valide
(`/api/authentication/validate` → `{"valid":true}`). Projet `healthplatform`,
3 analyses complètes (build Release + couverture OpenCover sur les 5 projets de
tests + scan).

### KPIs qualité — baseline → final

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| `code_smells` | 67 | **63** | −4 |
| `sqale_index` (dette, min) | 572 | **541** | −31 |
| `new_violations` | 68 | **65** | −3 |
| `bugs` | 2 | 2 | = |
| `vulnerabilities` | 0 | 0 | = |
| `security_hotspots` | 0 | 0 | = |
| `coverage` | 88,0 % | 88,0 % | = |
| `new_coverage` | 88,3 % | **88,4 %** | +0,1 |
| `duplicated_lines_density` | 0,3 % | 0,3 % | = |
| `reliability_rating` | C (3) | C (3) | = |
| `security_rating` | A (1) | A (1) | = |
| `sqale_rating` | A (1) | A (1) | = |

**Quality Gate : ERROR** — une seule condition en échec, `new_violations`
(65 > 0). Les trois autres (`new_coverage`, `new_duplicated_lines_density`,
`new_security_hotspots_reviewed`) sont **OK**.

### ⚠️ Le QG ERROR n'est pas de la dette introduite par cette task

**Issues en new-code period portées par les fichiers de task-271 : 0** (vérifié
sur les 65 restantes, après correctifs). La new-code period du projet couvre
une **baseline large** qui inclut des tasks déjà mergées — travers déjà
constaté et documenté. Les 65 restantes se répartissent ainsi :

| Fichier | Nb | Nature |
|---|---|---|
| `tests/loadtest-k6/report.py` | 21 | `python:S3776` (complexité cognitive — **liste noire**, relève de `/sonar-s3776`), `S1192`, `S3358` — dette du harnais, tasks 174/208/244… |
| `tests/loadtest-k6/lib/journey-model.js` + `scenarios/journey.js` | 21 | `javascript:S1940`, `S2486`, `S6582` — scénarios k6, tasks antérieures |
| Tests + sources `Embedding` / divers | 23 | `CA1861`, `S3267`, `CA1816`, `xUnit2032`… — tasks antérieures |

Aucune n'est dans le périmètre de cette US, et `S3776` est explicitement hors
chaîne autonome (`agents/sonar-blacklist.yml`).

### Correctifs livrés par cette passe

**`csharpsquid:S125` — 2 occurrences, ponctuation seule, zéro changement de
comportement.**

La leçon vaut plus que le correctif : l'heuristique « code commenté » **ne
demande ni interface ni liste à puces**. Il suffit qu'une ligne `//` **se
termine par `;`** pour qu'elle soit prise pour une instruction.

1. `MailProcessingMetrics.cs:273` — **introduite par task-271**, prose ordinaire
   au fil du texte (`… does not shrink the hold;`). Corrigée en virgule.
2. `MailClientSessionManager.cs:616` — **pré-existante (task-269)**, même règle,
   même déclencheur. Corrigée au passage (`;` → tiret) : le fichier était déjà
   dans le périmètre de la task, et le coût est nul.

**Boucle d'auto-amélioration fermée** : `conventions/csharp.md`, entrée S125
généralisée (elle ne couvrait que les blocs de contrat d'interface — d'où la
récidive), compteur porté à **2 occurrences**, avec le contrôle mécanique à
passer sur le diff avant commit :

```bash
git diff --cached -U0 -- '*.cs' | grep -nE "^\+\s*//.*;\s*$"
```

### Arrêt

Best-effort atteint en **1 itération de correctifs** : les issues restantes
n'appartiennent pas à cette US, et la seule règle qui les domine (`S3776`) est
en liste noire. Poursuivre reviendrait à traiter la dette d'autres tasks dans
la PR de celle-ci — ce que la règle « 1 US = 1 PR » interdit.
