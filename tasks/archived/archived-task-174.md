# todo-task-174.md — Banc de charge api-mail : harnais k6, scénarios et KPIs

**Repos**: api-mail
**Dependencies**: done-task-195
**Epic**: E015
**Single frontend**: true

> **Référence** : ADR-2026-07-25-B « Tests de charge api-mail sur infrastructure
> mail mockée » (décision harnais = **k6**, v1.1 ; banc IMAP = **Dovecot**, v1.2).
> Prérequis : task-195 (banc Dovecot + puits SMTP GreenMail) mergée — le harnais
> tire sur ce banc. task-173 (profil AppHost + seed + injection XDM) déjà mergée.

## Objective

Construire le **harnais de tir** au-dessus du banc posé par task-173 : des
scripts **k6** qui rejouent des scénarios de charge représentatifs du trafic
MSSanté, mesurent les KPIs (p95/p99, RPS, taux d'erreur) et **remontent leurs
métriques dans le Grafana déjà debout** (via la sortie Prometheus remote-write
de k6, AppHost task-173), pour corréler latence côté client et consommation
côté serveur (sessions IMAP, GC, threads, DB) sur un seul dashboard. Une
baseline documentée sert de référence anti-régression.

**Choix k6 (vs NBomber initialement pressenti)** : (1) sortie Prometheus native
→ corrélation dans le Grafana existant, ce qui est la finalité même du banc ;
(2) le banc s'authentifie par **en-têtes de bypass** (aucun JWT à forger) et les
identités virtuelles sont **déterministes** — la réutilisation du C# n'apporte
donc rien ; (3) modèle VU léger (forte concurrence par machine) et
**thresholds-as-code** (pass/fail net pour la baseline). Le banc étant agnostique
du tireur, ce choix ne touche rien de task-173.

**US backend-only (justification)** : outillage de test pur, aucun frontend ni
contrat impacté. Aucune modification du binaire api-mail.

### Contenu

1. **Scripts k6** rangés sous `tests/loadtest-k6/` (**pas** `tools/` — gitignoré
   dans ce repo, cf. task-173) : scénarios en JS, config partagée (base URL,
   clé de bypass, N utilisateurs, profils de latence).
2. **Authentification par bypass** : chaque requête porte
   `X-Test-Bypass: {clé}`, `Client-Email: loadtest-{n}@loadtest.local`,
   `Client-Psc-Sub`, `Client-Rpps` et un `Client-Session-Id` par VU. Les
   identités sont **régénérées en JS** à partir des mêmes formules déterministes
   que `LoadTestPlanGenerator` (`loadtest-{n}@loadtest.local`, RPPS `9{n:D10}`,
   sub `00000000-0000-4000-8000-{n:D12}`) — aucun JWT à forger, aucun secret.
3. **Scénarios** (paramétrables — VUs, durée, rampe) :
   - `folders` : liste des dossiers (ouvre/réutilise les sessions IMAP — vise
     `MailClientSessionManager`) ;
   - `read` : liste + lecture de messages (corps + pièces jointes) ;
   - `search` : recherches plein texte ;
   - `send` : envoi SMTP (vers le puits SMTP GreenMail) ;
   - `enrich` : `POST /folders/{f}/emails/enrich/sync` (body `[uids]`) sur des
     mails porteurs d'`IHE_XDM.ZIP` → **exerce la pipeline CDA/IHE-XDM réelle**
     (parsing, extraction des documents médicaux) — le scénario le plus lourd,
     rendu possible par le banc Dovecot (task-195). Attention au court-circuit
     « déjà enrichi » : viser des UIDs non encore enrichis (ou reset).
   - `mixed` : profil composite réaliste (ratios lecture/envoi/enrich/navigation)
     avec réutilisation de session (`Client-Session-Id` stable par VU — clé du
     pool) **et** rotation d'une fraction des sessions (exerce ouverture/expiration).
4. **Profils de latence Toxiproxy** pilotés par le harnais (via l'API Toxiproxy
   `8474` au démarrage) : `none` (0 ms, debug), `mssante` (~100 ms ± jitter,
   défaut), `degraded` (500 ms + coupures).
5. **KPIs, sortie Grafana et thresholds** :
   - k6 → **Prometheus remote-write** → Grafana existant (AppHost task-173) :
     latence p50/p95/p99, RPS, taux d'erreur, **corrélés** aux métriques serveur
     (sessions IMAP actives, threads, GC, DB) ;
   - **thresholds k6** en pass/fail (ex. `http_req_failed: rate<0.01`,
     `http_req_duration: p(95)<{cible}`) — le code de sortie non nul fait
     échouer un run sous la cible, socle de la baseline anti-régression ;
   - résumé JSON/HTML archivé par run (`tests/loadtest-k6/reports/{date}/`,
     git-ignoré).
6. **Baseline** : un run de référence documenté (config machine, N utilisateurs,
   profil `mssante`, chiffres p50/p95/p99 + seuils) committé en Markdown — la
   référence anti-régression.
7. **Exécution** : commande unique documentée (binaire k6 local **ou** image
   `grafana/k6`), **manuelle uniquement** (jamais dans le cycle forge ni la CI
   par défaut — un run de charge n'est pas un test unitaire).

### Hors scope

- Toute modification du binaire api-mail ou du banc (task-173).
- Tests de charge sur les environnements déployés/HDS.
- Le levier « TTL access token Keycloak » et l'ADR refresh PSC (backlog E013,
  on hold) — le banc contourne l'authentification réelle.

## Definition of Done

- [ ] Les 5 scénarios (`folders`, `read`, `search`, `send`, `mixed`) s'exécutent
      contre le profil loadtest et se terminent sans erreur d'outillage
- [ ] Identités virtuelles régénérées en JS, cohérentes avec `LoadTestPlanGenerator`
      (mêmes emails/RPPS/sub) — vérifié par un run qui atteint bien les boîtes seedées
- [ ] Paramétrage effectif : VUs, durée, rampe, profil de latence — modifiables
      sans éditer le script (variables d'environnement / options k6)
- [ ] `mixed` exerce le pool de sessions : réutilisation (`Client-Session-Id`
      stable) **et** rotation — visible dans Grafana (sessions actives vs créées)
- [ ] Profils Toxiproxy appliqués par le harnais (vérifié : p95 de `folders`
      croît de ~la latence injectée entre `none` et `mssante`)
- [ ] Métriques k6 visibles dans le **Grafana existant** (sortie Prometheus
      remote-write) sur le même intervalle que les métriques serveur
- [ ] Thresholds k6 définis et fonctionnels : un run sous la cible sort en code
      non nul (pass/fail exploitable)
- [ ] Résumé archivé par run + baseline committée (Markdown, config + chiffres + seuils)
- [ ] Smoke run court (ex. 10 VU × 60 s) documenté comme vérification rapide
- [ ] Aucun token/clé en clair dans les scripts, rapports et logs (la clé de
      bypass vient d'une variable d'environnement, pas du script)
- [ ] Exécution manuelle uniquement : rien n'est branché dans le cycle forge ni
      dans la CI par défaut
- [ ] Documentation de lancement (mise à jour de `docs/loadtest.md`)

## Manual Test Plan

Prérequis : banc lancé — `MSS_LOADTEST=true dotnet run --project src/AppHost`
puis seed (task-173, ex. N=50, M=100). Binaire k6 disponible (local ou
`docker run grafana/k6`).

1. **Smoke run** : lancer le scénario `folders`, 10 VU × 60 s, profil `mssante`,
   avec la clé de bypass en variable d'environnement → run vert, résumé généré
   dans `tests/loadtest-k6/reports/{date}/`.
2. **Grafana** : ouvrir le dashboard (AppHost, port 3001) → les latences k6
   (p95, RPS, erreurs) apparaissent, alignées temporellement avec les métriques
   serveur (sessions IMAP, GC).
3. **Effet latence** : rejouer en `none` → p95 baisse d'environ la latence
   injectée ; en `degraded` → erreurs/timeouts comptés, threshold `http_req_failed`
   franchi → code de sortie non nul.
4. **Profil mixte** : `mixed`, 50 VU × 5 min → dans Grafana, plateau de sessions
   IMAP actives (réutilisation) + créations liées à la rotation ; retour au calme
   après le run (aucune fuite de session).
5. **Baseline** : rejouer la config de référence committée, comparer les ordres
   de grandeur (écart raisonnable documenté).

Voir `docs/loadtest.md`.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — outillage interne de test de performance
- **Vague Ségur** : hors Ségur — aucune exigence DSR concernée
- **Exigences DSR honorées** : non applicable — contribue indirectement à la
  robustesse/performance du LPS sur le volet MSSanté
- **INS** : non applicable — données 100 % synthétiques (banc task-173)
- **Authentification PS** : contournée sur le banc uniquement (en-têtes de bypass
  de task-173, hard-block Production) — PSC/e-CPS inchangés partout ailleurs
- **Habilitations** : non applicable — utilisateurs virtuels fictifs
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : non applicable au banc ; scripts, rapports et logs sans
  token ni clé (clé de bypass via variable d'environnement)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — exécution locale/CI manuelle uniquement, jamais
  sur les environnements HDS
- **AIPD / impact RGPD** : inchangé — aucune donnée personnelle

## Branches

- `api-mail` (pushed) : `feat/task-174-loadtest-k6-harness` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-174-loadtest-k6-harness
- `dtos-mss` (pushed, auto-inclus) : `feat/task-174-loadtest-k6-harness` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-174-loadtest-k6-harness
  (convention ; aucun contrat DTO attendu — restera probablement sans commit ni PR)

Pré-vol `/start` du 2026-07-25 : `api-mail`, `client-blazor`, `client-mobile`,
`dtos-mss`, `sdk`, `interop-cda` tous sur `develop` et propres ; `host` n'est pas
un dépôt git. Dépendance `done-task-195` satisfaite — la task est **archivée**
(`tasks/archived/archived-task-195.md`), état terminal postérieur à `done` : PR #122
mergée en `5f22334`, CI verte sur `develop`.

### Apports des tirs manuels du 2026-07-25 (à réutiliser)

Deux tirs (5 et 20 utilisateurs) ont été conduits à la main sur le banc Dovecot
avant cette task. Leurs enseignements sont consignés dans
`.claude/skills/loadtest-skill/SKILL.md` et doivent alimenter le harnais :

| Scénario | p50 mesuré | Usage pour les thresholds |
|---|---|---|
| `folders` session froide | 0,7 – 1,05 s | seuil de départ crédible |
| `folders` session chaude | **0,011 – 0,014 s** | ~95× moins cher — c'est le pooling qu'il faut charger |
| `read` après enrichissement | 0,06 s | servi depuis la base |
| `enrich` froid (10 UIDs) | **4,3 s** | scénario le plus lourd |
| `enrich` court-circuité | 0,024 s | **ne mesure rien** — voir ci-dessous |

- **Ordre imposé dans `enrich`** : enrichir **avant** toute lecture. Une simple
  lecture crée le `MailContent` et court-circuite l'enrichissement, qui répond
  alors `200` en ~25 ms sans rien parser — facteur **180** avec le travail réel.
  Piège tombé deux fois malgré l'avertissement en prose : le harnais doit
  l'imposer par construction, pas le documenter.
- **Taux de succès attendu : 88 à 94 %** de messages produisant des documents
  médicaux (44/50 et 94/100 mesurés). Un threshold à 100 % échouerait toujours —
  le corpus contient des archives sans CDA exploitable.
- **0 erreur HTTP** attendu à ces échelles ; toute erreur est un signal.

### Réserve sur le scénario `search` (arbitrage porté à l'humain, qui a dit go)

`search` sollicite la recherche sémantique, or **task-196** (non livrée) montre que
les documents longs n'ont **aucun vecteur** : leur embedding est rejeté en `400`
(troncature en caractères vs limite de 8192 tokens). Charger `search` maintenant
mesure donc un index **incomplet**, avec des résultats flatteurs pour de mauvaises
raisons. Conduite retenue : livrer le scénario, mais **marquer sa baseline comme
provisoire** et la re-mesurer après task-196. À ne pas oublier au moment d'écrire
la baseline anti-régression.

## Develop log

- Repos touched : `api-mail` (`dtos-mss` left empty — no contract change, as expected)
- DTOs published : no DTO change · Interop published : no interop change
- Commits (branche `feat/task-174-loadtest-k6-harness`) :
  - `6a3ff57` feat(loadtest): k6 harness, six scenarios and anti-regression baseline
  - `debee3e` feat(apphost): expose k6 metrics in the bench Grafana
  - `85f5bbb` docs(loadtest): document the k6 harness and the bench ceilings
- Local build : ✓ 0 erreur / 0 avertissement.
  Tests : ✓ domain 94, api 559, infrastructure 360, integration 261 (16 skipped) ;
  application 1826/1827 — l'unique échec est
  `MarkdownPdfRendererTests.RenderHeadingPreservesText`, **flaky pré-existant**
  (passe en isolation, 9/9), sans rapport avec cette task.

### Livrables

`tests/loadtest-k6/` : 6 scénarios (`folders`, `read`, `search`, `send`,
`enrich`, `mixed`), 8 modules `lib/`, lanceurs `run.sh` / `run.ps1`,
`reset-state.sh`, `README.md`, `baseline.md`. Plus le tableau de bord Grafana
`src/AppHost/grafana/dashboards/k6-loadtest.json`, le receiver remote-write
dans `src/AppHost/AppHost.cs`, `docs/loadtest.md` et le `.gitignore`.

### Trois découvertes qui changent la façon de lire un chiffre

1. **Les bases Postgres par utilisateur survivent à la purge du maildir.**
   api-mail crée `u_9<index>_…` par utilisateur, les identités sont
   déterministes, donc les `MailContents` d'un tir précédent court-circuitent
   tout `enrich`. Constaté : 7 lots sur 10 court-circuités sur un banc
   « propre ». → `reset-state.sh` + purge documentée dans le skill.
2. **Le limiteur de débit d'api-mail borne le banc** à 100 req / 10 s par
   identité PS (task-090). Un run qui le déclenche affiche un p95 superbe
   mesuré sur des rejets. → cadence par défaut à 6 req/s par identité, budget
   compté en requêtes, seuil `rate_limited_429: count==0`.
3. **`mail_max_userip_connections=10`** (défaut Dovecot) plafonne à 10 sessions
   IMAP simultanées par utilisateur ; au-delà api-mail répond `500`
   (`IOException` en pleine `AUTHENTICATE`). La montée en charge passe par
   `USERS`, pas par des VU par utilisateur. → projection + alerte au démarrage.

### Deux réserves consignées dans la baseline

- **`search`** : baseline **provisoire** — task-196 non livrée, les documents
  longs n'ont pas de vecteur, l'index sémantique est incomplet. À re-mesurer.
- **`send`** : les boîtes du banc n'ont pas de dossier `Sent` ; l'envoi SMTP
  réussit mais `AppendToSentAsync` échoue (`FolderNotFoundException`, non
  fatal, `200` renvoyé). La latence mesurée inclut cet échec. Manque du banc
  (territoire task-195), à reprendre.

- Next step : /forge-simplify task-174

## Simplify log

- **Repos passés** : `api-mail` (seul touché ; `dtos-mss` sans commit).
- **Appliqué** : **rien** — skip propre, aucun commit vide.
- **Constat** (vérifié, pas supposé) :
  - *reuse* : les 6 scénarios consomment uniformément `lib/` (config, summary,
    identity, checks, bootstrap, api — 6/6 chacun ; `uid-bands` sur les 3
    concernés). Aucun helper recréé localement.
  - *simplification* : scénarios de 46 à 115 lignes (210 pour `mixed`, composite
    à 5 opérations). Les blocs `export const options` présents 6 fois sont
    **dérivés** de `buildScenario` / `buildThresholds` / `testId`, pas recopiés —
    et k6 impose que chaque script exporte les siens : irréductible.
  - *efficacité* : sans objet (scripts de tir).
  - *altitude* : les commentaires longs (ex. en-tête de `folders.js` sur le
    marquage froid/chaud) documentent des **pièges de mesure** qui ont coûté du
    temps — ils sont à leur place, les retirer serait une régression.
- **Rollback** : aucun.
- **Skippés (contrat / exclus)** : `dtos-mss`, `interop-cda`, `devops`, `psc-proxy-*`.
- **Étape suivante** : `/sonar task-174` (api-mail touché).

## Sonar log

- Phase 1 (new code) : ✓ Quality Gate **OK**, `new_coverage` = 85,2 %
- Phase 1 — Issues fixées : **17** (0 bug / 0 vulnérabilité / 17 code smells)
  \+ **2 security hotspots** revus `SAFE`
- Phase 1 — Tests ajoutés : 0 — voir « Pourquoi aucun test ajouté » ci-dessous
- Phase 2 (legacy) : **skippée** — baseline déjà à 0 bug / 0 vuln / 0 smell /
  0 hotspot, ratings A/A/A. Rien à nettoyer, aucune campagne de couverture
  (hors scope de cette task).
- Build / tests : ✓ green — build Release 0 erreur, suite complète
  **3 141 / 3 141** verte (domain 94, application 1 827, infrastructure 360,
  api 559, integration 261 + 16 skipped).
- Itérations : 1 (une seule passe a suffi à vider le new code)

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | ERROR | **OK** | ✓ résolu |
| New violations | 17 | **0** | −17 |
| New security hotspots reviewed | 33,3 % | **100 %** | +66,7 pt |
| New coverage | 85,3 % | 85,2 % | −0,1 pt |
| New duplication | 0,13 % | 0,13 % | → |
| Bugs | 0 | 0 | → |
| Vulnerabilities | 0 | 0 | → |
| Security hotspots | 0 | 0 | → |
| Code smells | 0 | 0 | → |
| Coverage (projet) | 85,9 % | 85,9 % | → |
| Duplication | 0,7 % | 0,7 % | → |
| Reliability / Security / Maintainability | A / A / A | A / A / A | → |

> La ligne « Quality Gate baseline = ERROR » mérite une lecture exacte : le
> **dernier scan connu** (task-195, sur `develop`) était vert. C'est le premier
> scan **de cette branche** qui a viré au rouge, parce que c'est le premier à
> voir le harnais k6 : l'analyse est multi-langage et `tests/loadtest-k6/`
> n'est couvert par aucune exclusion. 14 fichiers JS sont entrés dans le
> périmètre d'un coup, et SonarJS a rendu son verdict. Les 9 lignes de C# de
> la task (`src/AppHost/AppHost.cs`) sont, elles, hors périmètre par
> configuration (`sonar.exclusions` contient `**/AppHost/**`).

### Les 17 findings, par règle — tous sur `tests/loadtest-k6/`

| Règle | N | Fichiers | Correction |
|---|---|---|---|
| `javascript:S6661` | 4 | `lib/api.js` (×2), `lib/bootstrap.js`, `lib/summary.js` | `Object.assign({...}, extra \|\| {})` → spread `{ ..., ...extra }` |
| `javascript:S4624` | 4 | `lib/summary.js` (×3), `lib/checks.js` | template literals imbriqués → variables locales (`verdictOf`, `pctOrDash`, `cause`) |
| `javascript:S6582` | 3 | `lib/bootstrap.js` (×2), `lib/summary.js` (×2 lignes) | `a && a.b` → optional chaining `a?.b` |
| `javascript:S3776` | 2 | `lib/summary.js` (20/15), `lib/toxiproxy.js` (16/15) | découpage — voir ci-dessous |
| `javascript:S6557` | 1 | `lib/summary.js` | `indexOf('http_reqs{') === 0` → `startsWith` |
| `javascript:S3863` | 1 | `scenarios/mixed.js` | `config.js` importé deux fois → import fusionné |
| `javascript:S2245` (hotspot) | 2 | `scenarios/folders.js`, `scenarios/mixed.js` | revus `SAFE` — voir justification |

**S3776 — traité ici, et non renvoyé à `/sonar-s3776`.** La commande dédiée
est spécifique au **C# d'`api-mail`** (tests de caractérisation `dotnet`, une
méthode = une PR) ; elle n'a pas de mode JavaScript. Les deux fonctions
dépassaient de 1 et 5 points, dans du code neuf de cette task, et se
découpent sans toucher au comportement :
- `summary.js` `renderText` (20) → un builder par section du rapport
  (`contextSection`, `totalsSection`, `latencySection`, `thresholdSection`,
  `checksSection`), concaténés par spread.
- `toxiproxy.js` `applyProfile` (16) → extraction de `toxicsOf(profile)` et
  `applyToProxy(proxy, profile)`, boucle remplacée par `flatMap`.

**S2245 — les deux `Math.random()` sont légitimes.** Ils tirent la décision de
rotation de session (`SESSION_ROTATION`), pour charger le pool IMAP en *hit*
et en *miss*. Le tirage ne produit ni identifiant, ni token, ni sel, ni
secret ; il choisit entre un `Client-Session-Id` stable et un id rotatif, sur
un banc local à données 100 % synthétiques, dans du code de test hors binaire
`api-mail`. Marqués `REVIEWED` / `SAFE` dans SonarQube avec cette
justification.

### Pourquoi aucun test ajouté — et comment les refactors ont été validés

Le harnais k6 n'a pas de projet de tests : ce sont des scripts de tir exécutés
manuellement, et `sonar.coverage.exclusions` couvre déjà `**/tests/**`, donc
le JS ne pèse pas sur `new_coverage` (85,2 %, cible 80 % — verte sans
intervention). Aucun trou de couverture new-code à combler.

Les deux refactors S3776 touchent néanmoins du code qui **produit les
chiffres de la baseline anti-régression** : un rapport faux serait pire qu'un
smell. Ils ont donc été validés par équivalence observationnelle plutôt que
par des tests écrits pour l'occasion —

1. **Diff de sortie contre la version d'avant.** Les modules d'origine
   (`git show HEAD:…`) et les modules corrigés ont été chargés côte à côte
   **dans le runtime k6**, alimentés par un `data` de synthèse (métriques
   taguées, thresholds PASS et FAIL, checks imbriqués) et par le cas limite
   « run sans aucune métrique ». Sorties **identiques au caractère près** sur
   les trois cas, pour `archiveSummary` (les 4 clés : stdout, `.json`, `.txt`,
   `.html`) comme pour `reportContext`. Fichiers de comparaison supprimés
   après usage — rien de temporaire n'est committé.
2. **Les 6 scénarios se chargent toujours** : `k6 inspect` sur chacun (exécute
   le contexte d'init — valide syntaxe **et** graphe d'imports), vert avant et
   après.
3. **Aucune logique de scénario, aucun threshold, aucune mesure touchés.**

### Un fait à réutiliser : le runtime k6 accepte le JS moderne

Vérifié sur k6 v1.4.2 (moteur sobek) plutôt que supposé, parce que « corriger »
un smell avec une syntaxe que le runtime refuse casserait le harnais :
spread d'objet, spread d'appel, `flatMap`, optional chaining, nullish
coalescing et `String#startsWith` fonctionnent tous nativement. Aucun besoin
d'écrire du JS défensif à l'ancienne dans ce repo. Consigné dans
`conventions/javascript.md`.

### Conventions alimentées

Nouveau fichier **`conventions/javascript.md`** (7 entrées : S6661, S4624,
S6582, S6557, S3863, S3776, S2245 + le tableau de support du runtime k6).
`conventions/csharp.md` n'était pas le bon réceptacle — il est explicitement
lu par `/develop` *avant d'écrire du C#*, or ces règles concernent du
JavaScript ; et `conventions/angular.md` est cadré sur
`client-angular` / `client-mobile`. Un pointeur a été ajouté en tête de
`conventions/csharp.md` pour router vers le nouveau fichier.
**À arbitrer par l'humain** : câbler `conventions/javascript.md` dans le
contrat de `/develop` (CLAUDE.md + `agents/develop.md`), sans quoi le fichier
existe mais n'est lu par personne — la boucle d'auto-amélioration reste
ouverte sur ce langage.

### Commits

- `abc744c` fix(sonar/new): clear the 17 new-code smells of the k6 harness
  — poussé sur `feat/task-174-loadtest-k6-harness`

- **Étape suivante** : `/review task-174` (`client-angular` et `client-mobile`
  non touchés → `/lint-angular` et `/lint-mobile` sans objet).

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/123
  — label `awaiting-human-merge`, `MERGEABLE`, CI verte (build SUCCESS).
- `dtos-mss` : **aucune PR** — 0 commit, comme anticipé au `/start`.

## Code Review Summary

**Verdict : APPROVED** — 23 fichiers, 0 blocage, 1 suggestion non bloquante.

Points de contrôle passés : aucun secret introduit (`BYPASS_KEY` sans défaut, les
deux runners refusent de démarrer sans elle, zéro littéral dans les scripts) ;
aucun fichier CI touché (exécution manuelle uniquement) ; `reports/` gitignoré ;
binaire api-mail non modifié.

Suggestion : `run.ps1` réassigne `$args`, variable automatique PowerShell —
fonctionne, mais signalable par un linter.

À signaler au merge : `src/AppHost/AppHost.cs` (+9) modifie la configuration
**Prometheus partagée** de tous les environnements de dev locaux. Le changement est
nécessaire (sans `--web.enable-remote-write-receiver`, la sortie k6 est refusée et
l'item de DOD Grafana est inatteignable) et commenté sur place.

### DOD — un seul item non vérifié

Le **rendu visuel du dashboard Grafana**. Le mot de passe admin du volume
persistant n'est plus `admin` ; il n'a délibérément pas été réinitialisé sur
l'environnement de l'humain. La chaîne est validée autrement : fichier monté,
provisioning relancé sans erreur, UID `k6-loadtest-api-mail` présent dans
`grafana.db`, métriques `k6_*` interrogeables côté Prometheus avec le bon label
`testid`. Reste un coup d'œil de 2 minutes au HAG.

### Instabilité de tests — pré-existante, pas une régression

Trois tests différents ont échoué selon les runs dans `mss.mail.application.tests`
(MailExport PDF, CdaProcessingMetrics, MarkdownPdfRenderer), **tous verts en
isolation**. Vérifié sur `develop` **sans cette branche** : la suite y échoue
aussi, sur un test encore différent.

*Correction après vérification* : la mémoire projet documente en réalité **5**
sources d'échec pré-existantes, dont exactement ces tests. C'est le raccourci
« 3 flaky » qui circule dans les tasks et les PR qui est inexact, pas la
connaissance du projet. Ce que ce run ajoute : la confirmation que l'instabilité
est **systémique** à `mss.mail.application.tests` (QuestPDF et OpenTelemetry, à
état global sous exécution parallèle xUnit) plutôt qu'un jeu figé de tests nommés.
Mémoire corrigée en ce sens.

## Merged

Mergée le 2026-07-25 par l'humain (`/merge task-174 --i-tested` — HAG, règle 10).

| Repo | PR | Commit squash | Branche distante |
|---|---|---|---|
| `api-mail` | [#123](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/123) | `346624a` | supprimée |
| `dtos-mss` | aucune (0 commit) | — | supprimée |

- Portes de sécurité : `--i-tested` fourni, label `awaiting-human-merge`, CI PR
  verte (`build=SUCCESS`), aucune revue bloquante, `MERGEABLE`/`CLEAN`, clones
  propres et à jour avec `develop`.
- Merge **squash**. `--delete-branch` volontairement non utilisé (il supprimerait
  aussi le local) : refs distantes retirées via `git push origin --delete`,
  branches locales conservées.
- `develop` synchronisé sur les deux repos ; **CI verte** sur `346624a`.
- Aucune branche staging `forge/staging-*` — task lancée hors `/forge`.
- `client-angular` hors périmètre — aucune opération git.

### EPIC E015 — fonctionnellement complète

task-173 (banc GreenMail + Toxiproxy), task-195 (IMAP Dovecot, débloque le parsing
CDA) et task-174 (harnais k6) sont mergées. Le banc mesure désormais réellement ce
qu'il devait mesurer.

### Suites ouvertes

- **task-196** — embedding tronqué en caractères et non en tokens. Bloque la
  re-mesure de la baseline `search`, marquée provisoire.
- **Dossier `Sent` absent du banc** (territoire task-195) : le chiffre de `send`
  inclut un archivage qui échoue. Seuil `THR_SEND_P95` à re-dériver ensuite.
- **`500` générique sur indisponibilité IMAP** au lieu d'un `503` typé (règle 12) —
  à rattacher à task-189 ou à sortir en task dédiée.
- **Instabilité systémique de `mss.mail.application.tests`** (état global QuestPDF /
  OpenTelemetry sous exécution parallèle) — reproduite sur `develop`, mérite une
  task.
- **Vérification visuelle du dashboard Grafana** — seul item de DOD non couvert par
  la forge.
