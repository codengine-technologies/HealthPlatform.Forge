# todo-task-251.md — Cinq exceptions par seconde et par réplica, et personne ne sait de quelle famille

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune
**Priorité**: **3** — aucun symptôme utilisateur connu, mais c'est la **signature
exacte** d'un défaut déjà rencontré, et le banc ne peut pas l'écarter sans l'ouvrir.

## Objective

Nommer la famille d'exceptions qui représente **4,4 à 5,0 exceptions par seconde
et par réplica** sur un tir nominal, et décider ensuite — pas avant — s'il faut la
corriger.

## Ce qui est établi

Tir local 200 du 2026-08-08, table « Par réplica api-mail », **cinq réplicas** :

| Réplica | Exceptions /s |
|---|---|
| `…-122332` | 4,53 |
| `…-87892` | 4,58 |
| `…-89828` | 4,87 |
| `…-97668` | 4,96 |
| `…-99488` | 4,36 |

Le repère documenté est « **quelques unités**, pas des centaines » — on y est, mais
**l'homogénéité entre réplicas et la croissance avec la charge** sont la signature
d'un **coût par requête**, pas d'incidents.

**C'est exactement le profil de deux défauts déjà trouvés dans cette EPIC** :
`SecurityTokenMalformedException` (task-206, ~1,2 exception **par requête**, 12 668
occurrences en 121 s), et `ClientResultException` classée à tort chez Flagsmith
alors qu'elle venait d'OpenAI et signalait des documents cliniques **perdus pour la
recherche**. Dans les deux cas, la famille n'avait pas été ouverte.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que c'est bénin parce que le total est faible.** La leçon de
  `ClientResultException` est précisément celle-là : une famille non ouverte peut
  masquer une perte fonctionnelle silencieuse.
- **Ne pas présumer que c'est encore `SecurityTokenMalformedException`.** Elle est
  censée valoir **0** depuis task-206 — si elle est revenue, c'est une régression à
  traiter comme telle, et c'est un résultat en soi.

## Definition of Done

- [ ] La ou les familles dominantes sont **nommées**, avec leur part respective,
      établies par `sum by (error_type) (increase(dotnet_exceptions_total[2m]))`
      sur la fenêtre d'un tir
- [ ] Pour chaque famille : le **chemin de code** qui la lève, et si elle est levée
      **une fois par requête** ou par incident
- [ ] Verdict écrit par famille : bénigne (avec la raison), ou défaut → **US
      dédiée** proposée au PO
- [ ] `SecurityTokenMalformedException` est **vérifiée à 0** — sinon régression
- [ ] Le repère « quelques unités par seconde » de `docs/loadtest.md` est **remplacé
      par un chiffre attendu et sa famille**, pour que le prochain tir puisse
      détecter une dérive au lieu de hausser les épaules

## Manual Test Plan

- Monter le banc, lancer un tir court (`journey`, 50 médecins, 5 min)
- Relever `sum by (error_type) (increase(dotnet_exceptions_total[2m]))` **à un
  instant situé dans la fenêtre du tir** (une `rate` évaluée après coup rend une
  série vide — piège documenté)
- Croiser avec Seq : pour la famille dominante, dérouler une trace complète et
  identifier le site d'appel

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — hygiène d'exploitation
- **Exigences DSR honorées** : aucune
- **INS** : non applicable — ⚠️ aucun message d'exception recopié dans le rapport ne
  doit contenir de donnée patient ; ne citer que le **type** et le site d'appel
- **Authentification PS** : ⚠️ si la famille dominante touche la validation du
  jeton PSC, le finding devient un sujet de **sécurité** et change de priorité
- **Habilitations / Consentement / Interop CI-SIS / MSSanté** : non applicable
- **Tracé PGSSI-S** : non applicable
- **Hébergement HDS** : sans objet
- **AIPD / impact RGPD** : inchangé

## Branches

- `api-mail` (pushed) : `chore/task-251-exception-family-triage` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/chore/task-251-exception-family-triage
- `dtos-mss` (pushed, auto-included) : `chore/task-251-exception-family-triage` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/chore/task-251-exception-family-triage — aucun changement de contrat attendu, branche créée proactivement

## Develop log

- Repos touchés : `api-mail` (`docs/loadtest.md` uniquement) + plan de contrôle
  (`.claude/skills/loadtest-skill/SKILL.md`). **Aucun code C# modifié** —
  US d'enquête. `dtos-mss` : aucun commit, pas de PR.
- DTOs publiés : aucun changement de contrat. Interop : aucun.
- Banc : monté (`https-load-test`), seedé 50 praticiens, **3 tirs**, puis
  arrêté et purgé (`reset-state.sh` mode PURGE : 50 bases purgées, volume
  maildir supprimé).

### La réponse, en une phrase

Les deux familles qui composaient les 4,4–5,0 exc/s **ne sont pas un coût par
requête** : l'une est le **sérialiseur Prometheus d'OpenTelemetry** qui déborde
son tampon **à chaque scrape**, l'autre est le **keep-alive de session IMAP** qui
sort de sa boucle **à chaque extinction de session**. Les deux sont bénignes ;
ce qui ne l'était pas, c'est que la colonne les additionnait sans les nommer.

### Ce qui a été établi, et comment

**1. La famille dominante dépend de ce que Prometheus scrape.** Deux régimes :

| Régime | Cible du scrape | Famille dominante | Part |
|---|---|---|---|
| A (config du 2026-08-08) | `:5052/metrics` en direct | `IndexOutOfRangeException` + `ArgumentException` | ~73 % / ~27 % |
| B (config actuelle) | voie collector `:8889` | `TaskCanceledException` | **80–93 %** |

**2. Régime A — `PrometheusSerializer` d'OpenTelemetry** (paquet
`OpenTelemetry.Exporter.Prometheus.AspNetCore` 1.16.0-beta.1).
Sites d'appel relevés (pile complète) : `WriteNormalizedLabelKey`
(`IndexOutOfRangeException`) et `WriteUtf8NoEscape` — « Destination buffer too
small » — (`ArgumentException`), sous `PrometheusCollectionManager.TryWriteResponse`
← `PrometheusExporterMiddleware.InvokeAsync`. C'est l'**agrandissement de tampon**
de l'exporteur : il déborde, attrape, double, recommence ; le scrape rendu est
complet.

**Fréquence : par _scrape_.** Causalité prouvée par l'expérience directe —
20 scrapes forcés sur un réplica **au repos, sans une seule requête métier** :
**+54 `IndexOutOfRange`, +18 `ArgumentException`** (≈ 2,7 + 0,9 par scrape).
Et la « signature » qui avait alerté s'explique entièrement : `scrape_interval:
5s` produit, au relevé du 2026-08-08 09:09→09:18, exactement **8 + 3 toutes les
5 s**, invariant — un **métronome**, sur une session de navigation manuelle.

⚠️ Contre-intuitif et vérifié : le coût **ne suit pas** la charge linéairement —
à 86 ko / 364 séries il **descend** à ~5 par scrape contre ~8 à 69 ko / 301 séries.

**3. Régime B — keep-alive de session**, `MailClientSession.StartKeepAlive`,
`await Task.Delay(KeepAliveInterval, _keepAliveCts.Token)`
(`src/Application/Session/MailClientSession.cs:305`), rattrapé par le
`catch (OperationCanceledException) { break; }` de la boucle. **Une exception par
extinction de session**, jamais par requête ; le débit suit `SESSION_ROTATION`.

Tir `mixed`, 50 médecins, 5 min (`RPS_PER_USER=2`, `SESSION_ROTATION=0.002`),
`sum by (service_instance_id, error_type) (increase(dotnet_exceptions_total[5m]))`
relevé **dans** la fenêtre :

| Réplica | Exceptions /s | dont `TaskCanceledException` |
|---|---|---|
| `…-27264` | 1,37 | 374 / 412 (91 %) |
| `…-2860`  | 1,17 | 280 / 352 (80 %) |
| `…-53032` | 2,03 | 506 / 608 (83 %) |
| `…-59220` | 1,47 | 365 / 441 (83 %) |
| `…-64200` | 1,27 | 355 / 381 (93 %) |

Même homogénéité entre réplicas que la table du tir 200 — à 4× moins de
praticiens, 4× moins d'exceptions. Les 4,4–5,0 /s du 2026-08-08 sont **cohérents**
avec cette famille portée à 200 praticiens (extrapolation, non re-mesurée).

### Verdicts par famille (DOD)

| Famille | Une fois par… | Verdict |
|---|---|---|
| `IndexOutOfRangeException` | **scrape** | **Bénigne** — contrôle de flux d'une dépendance, scrape complet, zéro impact fonctionnel. Coût de l'**instrument**, pas du produit |
| `ArgumentException` | **scrape** | **Bénigne** — même cause |
| `TaskCanceledException` | **extinction de session** | **Bénigne** — sortie de boucle intentionnelle |
| `IOException` | fermeture de connexion IMAP | **Bénigne** — `SslStream` sur socket avortée |
| `ImapProtocolException` | fin de session | **Bénigne** |
| `NpgsqlException` + `InvalidOperationException` | **appariées** (736 : 635) | ⚠️ **Défaut → US proposée** (ci-dessous) |
| `PostgresException 08P01 … server_login_retry` | — | ⚠️ **Défaut de banc → US proposée** (ci-dessous) |

### Contrôles de non-régression

| Famille | Attendu | Relevé |
|---|---|---|
| `SecurityTokenMalformedException` | **0** | **0** ✓ — aucune occurrence sur les 3 tirs ni au repos. (Le libellé apparaît dans `label/error_type/values`, qui est l'historique **persistant** du TSDB ; la requête de valeur rend vide.) |
| `FolderNotFoundException` | **0** | **0** ✓ |

### Deux US proposées au PO

1. **La reprise EF Core masque des coupures de connexion Postgres.**
   `NpgsqlException` « Exception while reading from stream »
   (`NpgsqlReadBuffer.EnsureLong`) systématiquement **appariée** à
   `InvalidOperationException` « An exception has been raised that is likely due
   to a transient failure. » levée par `NpgsqlExecutionStrategy.ExecuteAsync`.
   736 : 635 relevées **sur le seul seed**. La reprise fait son travail — et c'est
   précisément ce qui rend la coupure invisible. À rapprocher du plafond « un pool
   Npgsql par base praticien ».
2. **PgBouncer refuse les connexions au banc** (`08P01: server login has been
   failing, cached error: connect failed (server_login_retry)`, jusqu'à
   **313 /s**). Défaut de configuration du banc, pas d'api-mail : tant qu'il est
   présent, **aucun chiffre de capacité du tir n'est opposable**.

### Observation collatérale (hors périmètre, à ne pas perdre)

Au seed, **le premier `POST` de `UserSettings` répond 500 pour _chaque_
praticien**, et la 2ᵉ tentative passe — 50 fois sur 50, deux seeds de suite. Le
seed le rattrape (`retry 1/3`) et sort en succès, donc personne ne le voit.

### Livré

- `Api/Mail/docs/loadtest.md` § **4b-bis** (nouveau) : les familles nommées, leur
  site d'appel, leur périodicité, les verdicts, le repère chiffré qui remplace
  « quelques unités », et les deux pièges d'outillage.
- `.claude/skills/loadtest-skill/SKILL.md` : table « Ordre de grandeur attendu »
  réécrite (c'est **là** que vivait le repère « quelques unités », pas dans
  `docs/loadtest.md` — le DOD visait le bon texte au mauvais fichier ; les deux
  sont traités), et « Le test qui tranche » complété de ses **deux angles morts**.

### Deux pièges d'outillage, payés en les découvrant

- **`dotnet-trace` ne voit pas ces exceptions.** Sur 60 s où le compteur montait
  de +11 / +3, une collecte `Microsoft-Windows-DotNETRuntime:0x8000`
  (`ExceptionKeyword`) en a enregistré **zéro**, tout en capturant des
  `IOException` dans la même trace. Ce qui marche : une sonde
  `FirstChanceException` injectée par `DOTNET_STARTUP_HOOKS` — elle voit
  exactement ce que le compteur compte. À compiler en **`netstandard2.0`** :
  en `net10.0` elle se charge aussi dans l'outillage de build et le casse.
- **`increase()` sur un scrape direct de `:5052` ne veut rien dire** : endpoint
  **réparti** entre 5 réplicas, une série entrelace 5 compteurs. L'attribution
  passe par `service_instance_id`.

### Validation

- Aucun code C# modifié → aucun test à ajouter, aucune régression possible.
  `dtos-mss` : branche vide, pas de PR.
- Les chiffres ci-dessus sont **relevés**, pas estimés ; les deux extrapolations
  (tir 200, et le lien avec la table du 2026-08-08) sont signalées comme telles.
- Le banc a été **arrêté et purgé** après mesure (étape 6 du skill).

- Next step : `/forge-simplify 251`

## Simplify log

- **Skip clean** — aucun repo éligible. Le diff de `api-mail` vs `develop` est
  `docs/loadtest.md` uniquement (130 lignes ajoutées, **0 fichier de code** :
  `git diff --name-only origin/develop...HEAD | grep -cE '\.(cs|ts|html|scss|csproj)$'`
  → `0`). `dtos-mss` : branche vide. Rien à simplifier, aucune re-validation
  nécessaire (pas de comportement modifiable par une passe qualité).
- Next step : `/sonar 251`

## Sonar log

- **Skip clean — aucune analyse lancée, et ce n'est pas un silence.** Le diff
  d'`api-mail` vs `develop` ne contient **aucun fichier `.cs`** (un seul
  fichier : `docs/loadtest.md`). SonarQube n'analyse que du code : il n'y a ni
  new code à qualifier, ni dette introduite possible.
- **KPIs qualité** : inchangés par construction — cette task n'a pas modifié une
  ligne de C#. Aucune baseline → final à consigner, aucun Quality Gate à
  réévaluer. Le dernier état publié reste celui de la task précédente
  (`/review` le restituera comme tel dans le body de la PR).
- ⚠️ Rappel indépendant de cette task : la new-code period du projet inclut des
  tasks déjà mergées — un QG rouge ultérieur ne serait pas imputable à task-251.
- Next step : `/lint-angular 251`

## Lint log

- **`/lint-angular` — skip clean.** `client-angular` n'est pas dans
  `**Repos**:` (api-mail seul) et cette task n'a écrit aucune ligne d'Angular.
  Aucune commande lint/build/test lancée.
  ⚠️ Le working tree de `Client/Angular/` porte **2 fichiers modifiés**
  (`front/apps/mss/src/environments/environment.ts`,
  `front/apps/weda2/src/environments/environment.ts`, branche
  `feature/nova-rewriting-mss`) : c'est du **WIP humain préexistant**, étranger à
  task-251. Laissé intact — mode code-only, la forge ne touche pas à git côté
  Angular.
- **`/lint-mobile` — skip clean.** `client-mobile` n'est pas dans `**Repos**:`,
  working tree propre, toujours sur `develop`. Aucun écran touché.
- **`/verify-visual` — skip clean.** Aucun écran `client-mobile` touché, donc
  aucune capture à produire ni à apparier à une référence Stitch.
- Next step : `/review 251`

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/181 — label `awaiting-human-merge`
- `dtos-mss` : **aucune PR** — 0 commit vs `develop` (branche créée
  proactivement par la règle d'auto-inclusion, aucun changement de contrat).
  Branche `chore/task-251-exception-family-triage` à supprimer au `/merge`.
- `client-angular` / `client-mobile` / `devops` / `psc-proxy-*` : hors périmètre
  (`**Repos**: api-mail`).

## Code Review Summary

**Verdict : APPROVED** — 1 fichier revu, 0 blocage, 0 suggestion.

- `Api/Mail/docs/loadtest.md` (+131, −0) — ✅ ajout d'une section `## 4b-bis`.
  Documentation pure : aucun `.cs`, `.ts`, `.csproj` au diff, donc **aucune
  surface de régression** (correctness / sécurité / archi / perf sans objet).
  Contrôles réellement applicables :
  - **Exactitude** : chaque chiffre publié est un relevé daté, et les deux
    extrapolations (tir 200 ; lien avec la table du 2026-08-08) sont explicitement
    marquées comme telles plutôt que présentées comme mesurées.
  - **Non-fuite** (exigence du task file) : sur les 131 lignes ajoutées, aucun
    identifiant PS/patient, aucune adresse, aucun secret — seuls le **type**
    d'exception et le **site d'appel** sont cités. Contrôlé par grep sur les
    lignes ajoutées seules.
  - **Cohérence** : la nouvelle section corrige aussi l'heuristique « le test qui
    tranche » du skill, qui est précisément ce qui avait envoyé l'enquête sur une
    fausse piste (un métronome se lisait comme un coût par requête).

## Validation

- Build `api-mail` : ✓ 0 erreur.
- Tests : 136 + 436 + 2 102 + 660 = **3 334 verts, 0 échec**.
  `integration` : **1 échec** (`GetFolderAsync_Inbox_ShouldReturnTheSeededMessageCount`,
  `ImapProtocolException: The IMAP server has unexpectedly disconnected` pendant
  le seed Dovecot) — **vert en isolation (12/12)**. Flake d'environnement de la
  fixture Dovecot, consécutif à la purge du banc faite juste avant ; un diff
  100 % documentaire ne peut pas causer de régression de code.
- Qualité : `/sonar` skipped — aucun `.cs` au diff.
