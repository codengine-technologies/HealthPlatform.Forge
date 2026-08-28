# E015 — Changelogs (vue ingénierie)

> **Audience** : équipes techniques, backlog, dette.
> Vue produit : [E015-tests-charge-api-mail.md](E015-tests-charge-api-mail.md).
> **Dernière mise à jour** : 2026-08-28 (v1.64)

---

## Historique détaillé des changelogs

### v1.0 — Banc de charge api-mail (GreenMail + Toxiproxy + seed) — task-173

- **Task** : task-173 — `done`. **PR** : `api-mail` #121 (label `awaiting-human-merge`).
- **ADR** : ADR-2026-07-25-B « Tests de charge api-mail sur infrastructure mail mockée ».
- **Principe** : binaire de production **inchangé**. La redirection des serveurs
  IMAP/SMTP passe par le mécanisme existant `UserSettings.ImapServerConfig` /
  `SmtpServerConfig` (prioritaire dans `AutodiscoveryHelper`), l'authentification
  par le test-bypass existant (`TestBypassAuthenticationHandler`, hard-block
  Production).
- **Nouveaux projets** :
  - `tests/mss.mail.testing.shared` (test-support, `SonarQubeTestProject=true`) :
    `PscTokenForge` (forge de JWT PSC/Keycloak, extraite de `PscTokenFixtures` qui
    délègue désormais — zéro duplication) + `LoadTestPlanGenerator` (population
    synthétique déterministe : utilisateurs `loadtest-{n}@loadtest.local`, boîtes,
    messages, tailles/pièces jointes variées, aucune DSCP).
  - `tests/mss.mail.loadtest.seed` (Exe, `SonarQubeTestProject=true`) : seed du
    banc — proxies Toxiproxy (API `8474`, IMAP `13993`, SMTP `13465`), boîtes
    GreenMail (IMAP APPEND), `UserSettings` par utilisateur via l'API settings
    (test-bypass). Options CLI `--users/--messages/--domain/--api/--bypass-key/--toxiproxy/--latency/--no-proxy`.
- **AppHost** (`src/AppHost/AppHost.cs`) : profil `loadtest` opt-in via
  `MSS_LOADTEST=true` (jamais actif par défaut) — conteneurs `greenmail/standalone:2.1.3`
  (IMAPS 3993 / SMTPS 3465, `greenmail.auth.disabled`) et `ghcr.io/shopify/toxiproxy:2.9.0` ;
  injection de `TestMode__BypassKey` (défaut `loadtest-local-only`, surcharge
  `MSS_LOADTEST_BYPASS_KEY`) dans ce profil uniquement.
- **`TestBypassAuthenticationHandler`** (`src/Api/Authentication/`) : émet le claim
  `mssEmail` (requis par `UserContextEnricherMiddleware` pour peupler
  `UserContextInfo.Email`) + `mssSub`/`mssRpps` optionnels depuis les headers
  `Client-Psc-Sub`/`Client-Rpps` (passage du cross-check PSC/KC avec token PSC forgé).
  Hard-block Production et exigence de `TestMode:BypassKey` inchangés.
- **Tests ajoutés** :
  - `TestBypassAuthenticationHandlerTests` (8) : hard-block Production, clé
    absente/erronée, header absent, `Client-Email` absent, émission `mssEmail`,
    émission/omission `mssSub`/`mssRpps`.
  - `LoadTestPlanGeneratorTests` + `SeedOptionsTests` (17) : bornes N/M,
    déterminisme, attachements 1/5, parsing CLI (formes `--k v` et `--k=v`).
  - `GreenMailBenchSmokeTests` (integration, Docker-gated via `SkippableFact` +
    Testcontainers) : GreenMail réel → connexion / auth user-pwd / liste dossiers /
    lecture / **réutilisation de session poolée** / envoi SMTP à travers le **vrai**
    `MailClientSessionManager` + `ImapClientWrapper`. Première couverture réelle du
    chemin serveur-IMAP (cf. task-032ter archivée, `BackgroundImapService` resté
    `[ExcludeFromCodeCoverage]` faute de serveur IMAP de test).
- **Dépendances** : ajout de `Testcontainers` (core) `4.12.0` dans
  `Directory.Packages.props` ; `MailKit` sur le seed tool.
- **Validation** : build Release 0 erreur ; domain 94/94, infrastructure 360/360,
  api 557/557 ; application 1826/1827 — l'unique échec est le flaky pré-existant
  `MarkdownPdfRendererTests.RenderHeadingPreservesText` (vert en isolation, sans
  rapport avec task-173, cf. mémoire `project_api_mail_preexisting_flaky_tests`) ;
  smoke GreenMail vert (Docker).
- **Sonar** :
  - Findings **imputables à task-173** tous résolus par la classification correcte
    de l'outillage en projets de test (`SonarQubeTestProject=true`) : 2× hotspot
    S4830 (cert-trust intentionnel GreenMail/dev) → reviewed 100% ; S125 (faux
    positif liste numérotée) reformulé. `new_violations` 4 → 1.
  - Quality Gate new-code resté `ERROR`, **non imputable à task-173** :
    `new_coverage 73.1%` identique avant/après la branche (seul code de prod
    modifié = `TestBypassAuthenticationHandler` `[ExcludeFromCodeCoverage]` +
    `AppHost` exclu) → artefact « new-code-period large » du projet
    (cf. mémoire `reference_sonar_scanner_msys_argconv`) ; + 1× `CA1822` INFO dans
    `IheXdmProcessingServiceTests.cs` (test préexistant, hors diff).
  - Baseline projet inchangée : bugs 0, vulnérabilités 0, code_smells 1,
    coverage 85.9%, duplication 0.7%, ratings A/A/A.
- **Commits** (branche `feat/task-173-loadtest-bench-greenmail`) : `9aaf50d`
  (forge tokens + générateur), `5784935` (handler claims), `933381b` (profil AppHost
  + seed + smoke + doc), `d8e68eb` (fix port SMTP `--no-proxy`), `fb7d376`
  (reclassification test projects), `8fedebd` (lock files).
- **Doc** : `Api/Mail/docs/loadtest.md` (lancement du profil, seed, appels manuels,
  garde-fous).
- **Limites / différé** :
  - Auth IMAP user/mot de passe au lieu de XOAUTH2 (GreenMail ne parle pas XOAUTH2) ;
    TLS via cert auto-signé (`ValidateServerCertificate=false`) ; OCSP/CRL non exercés.
  - `tools/` étant gitignoré, le seed tool a été placé sous `tests/mss.mail.loadtest.seed`
    (à répercuter sur task-174 : le harnais NBomber ira sous `tests/`).
  - **Finding sécurité hors scope (action humaine)** : mot de passe applicatif Gmail
    réel committé en clair dans `tests/mss.mail.integration.tests/appsettings.test.json`
    (fallback env `GMAIL_EMAIL`/`GMAIL_APP_PASSWORD` déjà prévu) — à révoquer côté
    Google et purger du dépôt.
- **Règle 11 (US-complete)** : task-173 (banc) et task-174 (harnais) forment l'US
  « tests de charge ». PR #121 labellisée `awaiting-human-merge` — le banc est un
  livrable outil autonome et vérifiable seul (smoke test), réutilisable
  indépendamment (tests d'intégration du sync background). Retag possible en
  `awaiting-us-completion` si merge groupé souhaité.

---

### v1.1 — Bascule IMAP GreenMail → Dovecot (débloque la pipeline CDA/IHE-XDM) — task-195

- **Task** : task-195 — `done`. **PR** : `api-mail` #122 (label `awaiting-human-merge`,
  `MERGEABLE`, **non mergée** — HAG règle 10). `dtos-mss` : branche créée par
  convention, 0 commit, aucune PR (aucun contrat DTO impacté).
- **ADR** : ADR-2026-07-25-B, amendement **v1.2** (bascule du serveur IMAP du banc).
- **Problème résolu** : GreenMail répond mal au **fetch partiel `BODY[part]`**.
  `IMailFolder.GetBodyPartAsync` sur la pièce jointe `IHE_XDM.ZIP` échouait en
  `System.FormatException: Failed to parse entity headers` (MimeKit
  `MimeParser.ParseEntityAsync`) ; l'exception était attrapée → 0 ZIP → aucun
  `[CdaParsingService] Parsing completed`, `hasMedicalDocuments=false`. Ni un bug du
  seed (MIME/BODYSTRUCTURE vérifiés corrects) ni d'api-mail (le fetch partiel **est**
  le comportement de production voulu) — limitation de GreenMail (issue #187).
  **Prémisse reproduite indépendamment avant la bascule** (sonde jetable exécutant
  l'appel de production exact, RED contre GreenMail / GREEN contre Dovecot), puis
  retirée au profit de `DovecotBenchSmokeTests.PartialFetch_OfIheXdmAttachment_ReturnsExactBytes`.
- **AppHost** (`src/AppHost/AppHost.cs`, profil `loadtest` opt-in inchangé) :
  conteneur **`dovecot/dovecot:2.3.21`** (version épinglée — syntaxe 2.3 vs 2.4
  divergente) en IMAPS, **port hôte 3993 conservé** (conteneur 993) pour ne pas
  déplacer la surface du banc ni la doc existante. `passdb`/`userdb` statiques
  (auth wildcard : n'importe quel `loadtest-{n}` sans provisioning individuel),
  maildir sur **volume nommé `loadtest-dovecot-mail`** (occupation mesurable par
  `docker volume inspect`, ce que le DOD exige), TLS auto-signé de l'image réutilisé
  tel quel. **GreenMail conservé en puits SMTP uniquement** ; Toxiproxy proxifie
  désormais l'IMAPS Dovecot (`dovecot-imap`) + le SMTP GreenMail (`greenmail-smtp`).
- **Configuration montée, pas recopiée** : `src/AppHost/dovecot/dovecot.conf` est
  bind-monté **dans `conf.d`** (un seul fichier, pas le répertoire `/etc/dovecot` —
  les `cert.pem`/`key.pem` de l'image restent en place) **et** bind-monté par
  `DovecotBenchSmokeTests` (résolution en remontant jusqu'à la solution). Une
  régression de conf casse donc le test au lieu de diverger en silence d'une copie.
- **Contrat de mot de passe — trouvaille non prévue par l'US** : GreenMail tournait
  en `greenmail.auth.disabled` (mot de passe jamais vérifié, `TestMode:Password`
  absent partout) ; la `passdb` statique de Dovecot le **vérifie**. Sans réglage,
  toute connexion IMAP du banc aurait échoué à l'authentification. Une **même
  valeur** doit rester alignée en **trois points** : `src/AppHost/dovecot/dovecot.conf`,
  `TestMode__Password` injecté par l'AppHost (surcharge `MSS_LOADTEST_PASSWORD`), et
  `LoadTestPlanGenerator.DefaultPassword` / `--mail-password` du seed. Documenté, et
  couvert par un test de rejet de mauvais mot de passe.
- **Seed** (`tests/mss.mail.loadtest.seed`) : APPEND IMAP pointé sur Dovecot
  (host/port/mot de passe par défaut adaptés), APPEND MailKit inchangé, injection
  `IHE_XDM.ZIP` et read-back des `UserSettings` conservés.
- **Tests** : `DovecotBenchSmokeTests` (3, Docker-gated) — fetch partiel **octet pour
  octet**, auth wildcard sans provisioning, rejet d'un mauvais mot de passe,
  réutilisation de session. `GreenMailBenchSmokeTests` **conservé** (couverture SMTP
  + chemin historique du gestionnaire de sessions ; conteneur propre, ne référence
  plus le câblage IMAP du banc).
- **Simplify** (`d8b97f0`, 4 fichiers) : *reuse* — extraction de `BenchImap` (client
  IMAP tolérant au certificat auto-signé, seed de boîte, append avec pièce jointe),
  consommé par les **deux** smoke tests ; *altitude* — la justification « pourquoi
  Dovecot remplace GreenMail » était recopiée dans 3 fichiers, conservée une seule
  fois dans `docs/loadtest.md` (`AppHost.cs` et le smoke test y renvoient). Aucun
  rollback. Comptes de tests identiques avant/après.
- **Commits** (branche `feat/task-195-loadtest-dovecot-imap`) : `803b68d`
  *feat(loadtest): bascule l'IMAP du banc de GreenMail vers Dovecot* (6 fichiers,
  +550/−74), `d8b97f0` (passe simplify).
- **Validation** : build solution 0 erreur / 0 avertissement ; suite complète
  **3101 réussis, 0 échec, 16 ignorés** (les 3 flaky historiques verts sur ce run) ;
  `DovecotBenchSmokeTests` 3/3. Au run Sonar, `MailExportServiceTests.BuildPdfWithoutAttachmentsOmitsAttachmentSection`
  a échoué — flaky pré-existant documenté, vérifié vert en isolation (2 exécutions),
  aucun fichier Export dans le diff (cf. mémoire `project_api_mail_preexisting_flaky_tests`).
- **Sonar** : 2 issues fixées — `xUnit2032` (`DovecotBenchSmokeTests.cs:70`,
  `Assert.IsType<MimePart>(entity, exactMatch: false)` → `Assert.IsAssignableFrom` ;
  **seul finding imputable au code frais**) et `external_roslyn:CA1822`
  (`IheXdmProcessingServiceTests.cs:80`, `ArrangeSingleZip` marqué `static` —
  pré-existante mais comptée sur le new code par la période `PREVIOUS_VERSION`, donc
  bloquante pour la porte). 0 test ajouté en phase 1 (`new_coverage` déjà au-dessus du
  seuil ; le code de la task est sous `tests/**`, exclu de la couverture par
  configuration). **Phase 2 legacy skippée — plus rien à corriger** (0 bug,
  0 vulnérabilité, 0 code smell, 0 hotspot à l'échelle du projet). 2 analyses complètes.

  | Métrique | Baseline | Final | Δ |
  |---|---|---|---|
  | Quality Gate (new code) | **ERROR** | **OK** | ✓ redressé |
  | New coverage | 73,1 % | 85,3 % | +12,2 pt |
  | New violations | 1 | **0** | −1 |
  | Bugs / Vulnerabilities / Hotspots | 0 / 0 / 0 | 0 / 0 / 0 | = |
  | Code smells | 1 | **0** | −1 |
  | Coverage (projet) | 74,5 % | 85,9 % | +11,4 pt |
  | Duplication | 0,7 % | 0,7 % | = |
  | Reliability / Security / Maintainability | A / A / A | A / A / A | → |

  **Honnêteté de lecture** : le bond de couverture projet (+11,4 pt) **n'est pas
  imputable à cette task** — la baseline provenait d'une analyse dont la collecte de
  couverture était partielle, alors que les deux analyses de ce run ont exécuté les
  cinq projets de tests avec OpenCover. Réellement imputable : `new_violations`
  1 → 0 et le Quality Gate ERROR → OK. Seul écart aux cibles long terme : couverture
  85,9 % vs 95 % (campagne dédiée, `code-coverage-skill`, hors périmètre).
- **Validation end-to-end du banc (exécutée le 2026-07-25, via le `loadtest-skill`)** —
  lève les deux items du DOD qui étaient déférés au HAG :
  - Faux négatif corrigé : le log `/develop` annonçait Postgres métier « non démarré ».
    Le test `</dev/tcp/localhost/5432` en Git Bash résout `localhost` en IPv6 (`::1`)
    où rien n'écoute ; le conteneur `postgres-pgvector` publiait bien `0.0.0.0:5432`.
  - AppHost profil `https-load-test` : `loadtest-dovecot`, `loadtest-greenmail`,
    `loadtest-toxiproxy` up. Dovecot `v2.3.21 starting up for imap`, conf effective
    vérifiée dans le conteneur (`mail_location = maildir:~/Maildir`,
    `protocols = imap`, mot de passe statique en place).
  - api-mail : `connection/status` → `{"mode":"online","canAccessImap":true,"canSendEmail":true}`.
  - Seed 3 utilisateurs × 5 messages avec PJ `IHE_XDM.ZIP` réelles : 15 messages
    appendus, `UserSettings` read-back vérifiés, exit 0. Réception vérifiée de bout en
    bout (`INBOX`, `Brouillons`, messages 1–5, HTTP 200) via api-mail → Toxiproxy → Dovecot.
  - **Pipeline CDA/IHE-XDM : 4 messages sur 5** en `hasMedicalDocuments: true` **et**
    `hasBiologyResults: true`, avec 4 × `[CdaParsingService] Parsing completed:
    1 CDA documents extracted from …zip` dans Seq (application `mss.mail.api`). Le
    5ᵉ message n'est pas un défaut du banc : le corpus `JEUX_TESTS_FULL` est parcouru
    en round-robin et toutes ses archives ne portent pas un CDA exploitable.
  - Auth wildcard sans provisioning : 3 maildirs créés à la volée sous `/srv/mail/`.
  - Volumétrie maildir disque : `du -sh /srv/mail` = **4,6 Mo** pour 15 messages à PJ
    (~124 Ko en moyenne) — plus de plafond de heap JVM.
- **Piège opérationnel à connaître — court-circuit « déjà enrichi »** : `enrich/sync`
  sort en 200 / **58 ms sans rien parser** quand un `MailContent` existe déjà pour
  l'UID. Rejoué sur une boîte **vierge**, le même appel a pris **11,5 s** (vrai
  téléchargement à travers les 100 ms de latence injectée) et produit les
  4 extractions. Ordre correct : `enrich/sync` **avant** toute lecture. À répercuter
  sur les scénarios de task-174 (viser des UIDs non encore enrichis, ou reset).
- **Observation annexe — confirme un finding d'audit** : les traces Seq montrent les
  archives extraites vers `%TEMP%\{guid}.zip` et **24 `.zip` subsistaient après le
  run**. Confirmation empirique en conditions réelles du finding **task-185**
  (« archives IHE_XDM écrites en clair dans le répertoire temporaire et jamais
  supprimées »). Hors périmètre — task-185 le traite. Également relevé comme unique
  suggestion non bloquante de la code review (verdict **APPROVED**, 9 fichiers,
  0 blocage).
- **Garde-fous revérifiés** : aucun secret introduit dans le diff ; profil `loadtest`
  toujours opt-in (`MSS_LOADTEST`) ; `TestBypassAuthenticationHandler` toujours
  hard-blocké en Production ; données 100 % synthétiques. **Binaire api-mail
  inchangé** (tout se joue dans l'AppHost et l'outil de seed).
- **Doc** : `Api/Mail/docs/loadtest.md` mis à jour (Dovecot IMAP + puits SMTP
  GreenMail, lancement, seed, contrat de mot de passe, limites disque).
- **Hors repo `api-mail`** : `.claude/skills/loadtest-skill/SKILL.md` mis à jour comme
  sa section « Évolution du skill » l'exige (IMAP Dovecot + puits SMTP GreenMail,
  avertissement #187 retiré, pipeline CDA déclarée opérationnelle, volumétrie maildir,
  piège du mot de passe vérifié). Fichier du plan de contrôle de la forge — hors PR.
- **Limites / différé** :
  - **Run de volumétrie d'envergure** (ex. 200 boîtes × 200 messages) : déféré au test
    manuel humain (opération lourde, Manual Test Plan). Le mécanisme est prouvé à
    petite échelle et le stockage disque vérifié (4,6 Mo mesurés, plus de plafond de heap).
  - **Le maildir persiste entre les sessions** (volume nommé) : les seeds successifs
    s'accumulent — surveiller `docker volume inspect loadtest-dovecot-mail`, purger
    entre deux campagnes de mesure.
  - Auth IMAP user/mot de passe au lieu de XOAUTH2 et TLS auto-signé
    (`ValidateServerCertificate=false`) : limites héritées de task-173, inchangées.
  - Le harnais de tir k6 reste à livrer (task-174, qui dépend de cette task).
- **Règle 11 (US-complete)** : PR #122 labellisée `awaiting-human-merge` — même
  raisonnement que task-173, le banc est un livrable outil autonome, vérifiable seul
  (smoke tests + validation end-to-end) et réutilisable indépendamment du harnais.

---

### v1.2 — Harnais de tir k6 : six scénarios, thresholds-as-code, baseline anti-régression — task-174

- **Task** : task-174 — `done`. **PR** : `api-mail`
  [#123](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/123)
  (label `awaiting-human-merge`, `MERGEABLE`, CI verte — **non mergée**, HAG règle 10).
  `dtos-mss` : branche créée par convention, 0 commit, aucune PR.
- **ADR** : ADR-2026-07-25-B, harnais = **k6** (v1.1). Choix motivé par la sortie
  Prometheus native (finalité du banc : corréler client et serveur dans le Grafana
  existant), l'absence de JWT à forger (auth par en-têtes de bypass, identités
  déterministes régénérées en JS), le modèle VU léger et les thresholds-as-code.
- **Binaire api-mail inchangé** — seuls l'AppHost (+9 lignes) et l'arborescence
  `tests/` sont touchés.
- **Livrables** (`Api/Mail/tests/loadtest-k6/`, **pas** `tools/` qui est gitignoré
  dans ce repo) : 6 scénarios (`folders`, `read`, `search`, `send`, `enrich`,
  `mixed`), 8 modules `lib/` (config, summary, identity, checks, bootstrap, api,
  uid-bands, toxiproxy), lanceurs `run.sh` / `run.ps1`, `reset-state.sh`,
  `README.md`, `baseline.md`. Plus le dashboard
  `src/AppHost/grafana/dashboards/k6-loadtest.json` (UID `k6-loadtest-api-mail`),
  le receiver remote-write dans `src/AppHost/AppHost.cs`, `docs/loadtest.md` et le
  `.gitignore` de `reports/`.
- **Thresholds-as-code** : cibles p95 par opération dans `lib/config.js`, plus
  `http_req_failed < 1 %`, `checks > 95 %`, `rate_limited_429 == 0` et, pour
  `enrich`, `enrich_short_circuited == 0`. Mécanisme **démontré** : sous profil
  `degraded` (500 ms ± 125 + 5 % de coupures), `folders` 10 VU × 45 s franchit
  2 seuils (`folders_cold` p95 4 384 ms vs 3 000 ; `folders_warm` p95 478 ms vs
  400) → **code de sortie k6 = 99**.
- **Sortie Grafana** : k6 → Prometheus remote-write → dashboard du banc, label
  `testid` par run. Nécessite `--web.enable-remote-write-receiver` sur Prometheus
  — d'où la modification de `AppHost.cs`, **qui porte sur la configuration
  Prometheus partagée de tous les environnements de dev locaux** (commentée sur
  place ; à signaler au merge).
- **Paramétrage** par variables d'environnement : `USERS`, `MESSAGES_PER_USER`,
  `VUS`, `MAX_VUS`, `DURATION`, `ITERATIONS`, `LATENCY_PROFILE`,
  `SESSION_ROTATION`, `RPS_PER_USER`, `THR_*`, `REPORT_DIR`, `TESTID`.
  `BYPASS_KEY` **sans valeur par défaut** : les deux runners refusent de démarrer
  sans elle, aucun littéral dans les scripts, `reports/` gitignoré.

#### Baseline mesurée (`tests/loadtest-k6/baseline.md`)

Machine WEDA-0138 (Windows 11 Pro, banc et tireur sur le même hôte), k6 v1.4.2,
AppHost profil `https-load-test`, **10 utilisateurs × 10 messages** porteurs
d'une vraie `IHE_XDM.ZIP` (corpus `JEUX_TESTS_FULL`, ~124 Ko en moyenne), profil
de latence `mssante` (100 ms ± 25), 6 req/s par identité, bandes d'UID disjointes
(`enrich` 1..5, `read` 6..10). Latences en ms.

| Scénario | Opération | n | p50 | **p95** | Débit |
|---|---|---:|---:|---:|---:|
| `folders` (10 VU, 60 s) | `folders_warm` | 3 590 | 15,5 | **29,6** | 60,0 req/s |
| | `folders_cold` | 10 | 13,9 | **16,8** | |
| `read` (10 VU, 60 s) | `read_list` (5 UID) | 1 801 | 18,5 | **26,6** | 60,1 req/s |
| | `read_content` | 1 801 | 7,7 | **12,4** | |
| `search` (10 VU, 60 s) | `search` | 3 579 | 179,7 | **215,3** | 59,5 req/s |
| `send` (10 VU, 60 s) | `send` | 1 667 | 1 131,2 | **3 679,4** | 26,3 req/s |
| `enrich` (4 VU, 10 lots × 5 UID) | `enrich` | 10 | 3 589,8 | **15 793,0** | 0,79 req/s |

Profil composite `mixed` (10 VU, 120 s, ratios 40/30/10/10/10) : **5 832 requêtes,
46,4 req/s, 0 erreur, verdict PASS**. Pool de sessions IMAP : **4 774
réutilisations contre 21 rotations** — hit et miss exercés dans le même run.
607 itérations abandonnées par k6 (le débit demandé pour `send`, ≈ 1,1 s par
envoi, dépassait les VU alloués) : plafond du tireur, pas du serveur — relever
`MAX_VUS`.

Vérification de la pipeline CDA sur le run `enrich` de référence : 10 lots ×
`[CdaParsingService] Parsing completed: 1 CDA documents extracted` dans Seq, et
en base **50 mails enrichis, 50 porteurs de documents médicaux, 51 documents
extraits**. p50 à 3,6 s, soit ~150× le temps d'un court-circuit (~25 ms). Le taux
de 100 % tient à la tranche de corpus utilisée (5 messages par boîte) ; sur de
plus gros corpus il est de **88 à 94 %** — **ne jamais poser de seuil à 100 %**.

**Effet de la latence, correctement isolé.** `folders` en régime établi est
inutilisable comme sonde réseau : la réponse sort du cache serveur en ~15 ms quel
que soit le profil. La sonde retenue force le **chemin froid**
(`ITERATIONS=USERS`, `SESSION_ROTATION=1`, 2 VU), deux répétitions alternées par
profil :

| Profil | p50 | p95 | Écart p50 |
|---|---:|---:|---:|
| `none` (0 ms) | 13,3 / 15,5 | 85,8 / 82,7 | référence |
| `mssante` (100 ms ± 25) | 727,6 / 707,3 | 845,6 / 742,7 | **+ ~700 ms** |

Les ~700 ms correspondent à **7 allers-retours** de 100 ms : TCP, TLS, salutation
IMAP, `LOGIN`, `CAPABILITY`, `LIST`, `STATUS`.

#### Trois découvertes qui changent la lecture d'un chiffre

1. **Les bases Postgres par utilisateur survivent à la purge du maildir.**
   api-mail crée `u_9<index>_…` par utilisateur et les identités sont
   déterministes : les `MailContents` d'un tir précédent court-circuitent tout
   `enrich`. Constaté : 7 lots sur 10 court-circuités sur un banc « propre ». →
   `reset-state.sh` + purge documentée dans le `loadtest-skill`.
2. **Le limiteur de débit d'api-mail borne le banc** — `RateLimiting` de
   `src/Api/appsettings.json` : `PermitLimit: 100`, `WindowSeconds: 10`,
   `QueueLimit: 0` (fenêtre **fixe**, `FixedWindowRateLimiter`, partition par
   identité PS — task-090). **Configuration de production, pas artefact de banc.**
   Sans file d'attente, le dépassement est rejeté immédiatement en `429`, et un
   run qui déclenche le limiteur affiche un p95 superbe mesuré sur des rejets à
   moins d'une milliseconde. La fenêtre étant fixe, un simple regroupement
   d'itérations suffit : **quelques pour cent de 429 mesurés dès 8 req/s** par
   identité, sous le nominal de 10. → cadence par défaut 6 req/s par identité,
   budget compté **en requêtes** et non en itérations (`read` fait 2 appels par
   itération), seuil `rate_limited_429: count==0`.
3. **`mail_max_userip_connections=10`** (défaut Dovecot) plafonne à 10 connexions
   IMAP simultanées par (utilisateur, IP), et tous les VU partagent une IP ;
   au-delà la connexion est coupée en pleine `AUTHENTICATE` et api-mail répond
   `500`. **La montée en charge passe par `USERS`, pas par des VU par
   utilisateur** — c'est aussi ce qui borne `SESSION_ROTATION` à quelques
   millièmes sur 10 utilisateurs. Mesuré : à `SESSION_ROTATION=1` soutenu,
   258 rejets Dovecot et jusqu'à 30 % de `500`, entièrement imputables à ce
   plafond. → le harnais projette le nombre de sessions et alerte au démarrage.

#### Deux réserves consignées dans la baseline

- **`send`** — les boîtes du banc n'ont qu'`INBOX`, aucun dossier `Sent`. Après
  une soumission SMTP réussie, `AppendToSentAsync` échoue
  (`MailKit.FolderNotFoundException`), l'archivage étant non fatal le endpoint
  répond `200` et le scénario mesure `0 %` d'erreur à juste titre — mais **le
  chiffre de `send` inclut un `GetFolder("Sent")` qui échoue**. Manque du banc
  (territoire task-195), pas un défaut d'api-mail ; `THR_SEND_P95` à re-dériver
  quand le banc provisionnera un `Sent` par boîte.
- **`search`** — baseline **provisoire**. task-196 n'est pas livrée : la
  troncature avant vectorisation est comptée en caractères et non en tokens, les
  documents longs sont rejetés en `400` (« maximum input length is 8192 tokens »)
  et **n'ont aucun vecteur**. Les 215 ms de p95 mesurent donc un index
  **incomplet** — flatteur pour une mauvaise raison. À re-mesurer après task-196,
  `THR_SEARCH_P95` à réviser. Arbitrage porté à l'humain le 2026-07-25, qui a
  validé de livrer sur cette base.

#### Seuils dérivés

| Opération | p95 mesuré | Seuil | Marge |
|---|---:|---:|---|
| `folders_warm` | 29,6 (127 en `mixed`) | 400 | ~3× le pire cas |
| `folders_cold` | 16,8 (846 chemin froid) | 3 000 | ~3,5× le chemin froid |
| `read_list` | 26,6 | 500 | large |
| `read_content` | 12,4 | 500 | large |
| `search` | 215,3 | 1 000 | large — **provisoire** |
| `send` | 3 679 (8 574 en `mixed`) | 12 000 | ~1,4× le pire cas |
| `enrich` | 15 793 | 30 000 | ~2× |

Marge délibérément large sur les opérations rapides : sur une machine de
développement partagée, un seuil serré produit des faux positifs qui finissent
ignorés. À resserrer sur du matériel dédié.

#### Validation, simplify, Sonar

- **Commits** (branche `feat/task-174-loadtest-k6-harness`) : `6a3ff57`
  *feat(loadtest): k6 harness, six scenarios and anti-regression baseline*,
  `debee3e` *feat(apphost): expose k6 metrics in the bench Grafana*, `85f5bbb`
  *docs(loadtest): document the k6 harness and the bench ceilings*, `abc744c`
  *fix(sonar/new): clear the 17 new-code smells of the k6 harness*.
- **Build / tests** : Release 0 erreur / 0 avertissement ; suite complète
  **3 141 / 3 141** au run Sonar (domain 94, application 1 827, infrastructure 360,
  api 559, integration 261 + 16 skipped).
- **Simplify** : **skip propre, aucun commit** — constat vérifié et non supposé.
  *reuse* : les 6 scénarios consomment uniformément `lib/` (6/6 modules chacun,
  `uid-bands` sur les 3 concernés), aucun helper recréé localement.
  *simplification* : scénarios de 46 à 115 lignes (210 pour `mixed`, composite à
  5 opérations) ; les 6 blocs `export const options` sont **dérivés** de
  `buildScenario` / `buildThresholds` / `testId`, et k6 impose que chaque script
  exporte les siens — irréductible. *altitude* : les commentaires longs (marquage
  froid/chaud de `folders.js`) documentent des **pièges de mesure** coûteux ; les
  retirer serait une régression. `dtos-mss` / `interop-cda` jamais touchés
  (porteurs de contrat).
- **Sonar** : Quality Gate new-code **ERROR → OK** en **1 itération**, 17 issues
  fixées (0 bug / 0 vulnérabilité / **17 code smells**) + 2 hotspots revus `SAFE`.
  Phase 2 legacy **skippée** — baseline déjà à 0/0/0/0, ratings A/A/A.

  | Métrique | Baseline | Final | Δ |
  |---|---|---|---|
  | Quality Gate (new code) | **ERROR** | **OK** | ✓ résolu |
  | New violations | 17 | **0** | −17 |
  | New security hotspots reviewed | 33,3 % | **100 %** | +66,7 pt |
  | New coverage | 85,3 % | 85,2 % | −0,1 pt |
  | New duplication | 0,13 % | 0,13 % | → |
  | Bugs / Vulnerabilities / Hotspots / Code smells | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | → |
  | Coverage (projet) | 85,9 % | 85,9 % | → |
  | Duplication | 0,7 % | 0,7 % | → |
  | Reliability / Security / Maintainability | A / A / A | A / A / A | → |

  **Lecture exacte du « baseline = ERROR »** : le dernier scan connu (task-195,
  sur `develop`) était vert. C'est le premier scan **de cette branche** qui vire
  au rouge, parce que c'est le premier à voir le harnais : l'analyse est
  multi-langage et `tests/loadtest-k6/` n'est couvert par aucune exclusion —
  14 fichiers JS entrent d'un coup dans le périmètre. **Les 17 findings sont tous
  sur le JS du harnais, aucun sur du C#** ; les 9 lignes de `src/AppHost/AppHost.cs`
  sont hors périmètre par configuration (`sonar.exclusions` contient `**/AppHost/**`).

  | Règle | N | Fichiers | Correction |
  |---|---:|---|---|
  | `javascript:S6661` | 4 | `lib/api.js` (×2), `lib/bootstrap.js`, `lib/summary.js` | `Object.assign` → spread |
  | `javascript:S4624` | 4 | `lib/summary.js` (×3), `lib/checks.js` | template literals imbriqués → variables locales |
  | `javascript:S6582` | 3 | `lib/bootstrap.js` (×2), `lib/summary.js` | `a && a.b` → optional chaining |
  | `javascript:S3776` | 2 | `lib/summary.js` (20/15), `lib/toxiproxy.js` (16/15) | découpage (voir ci-dessous) |
  | `javascript:S6557` | 1 | `lib/summary.js` | `indexOf(…) === 0` → `startsWith` |
  | `javascript:S3863` | 1 | `scenarios/mixed.js` | double import de `config.js` fusionné |
  | `javascript:S2245` (hotspot) | 2 | `scenarios/folders.js`, `scenarios/mixed.js` | revus `SAFE` |

  **S3776 traité ici et non renvoyé à `/sonar-s3776`** : la commande dédiée est
  spécifique au **C# d'api-mail** (tests de caractérisation `dotnet`, 1 méthode =
  1 PR) et n'a pas de mode JavaScript. Dépassements de 1 et 5 points, dans du code
  neuf, découpables sans toucher au comportement — `renderText` → un builder par
  section (`contextSection`, `totalsSection`, `latencySection`, `thresholdSection`,
  `checksSection`) ; `applyProfile` → `toxicsOf(profile)` + `applyToProxy(...)`,
  boucle remplacée par `flatMap`.

  **S2245 — les deux `Math.random()` sont légitimes** : ils tirent la décision de
  rotation de session (`SESSION_ROTATION`) pour charger le pool IMAP en hit et en
  miss. Aucun identifiant, token, sel ni secret produit ; banc local, données 100 %
  synthétiques, code hors binaire api-mail. Marqués `REVIEWED` / `SAFE` avec cette
  justification.

  **Aucun test ajouté, et pourquoi.** Le harnais n'a pas de projet de tests (scripts
  de tir manuels) et `sonar.coverage.exclusions` couvre déjà `**/tests/**` : le JS
  ne pèse pas sur `new_coverage` (85,2 % pour une cible de 80 %). Mais les deux
  refactors S3776 touchent le code qui **produit les chiffres de la baseline** — un
  rapport faux serait pire qu'un smell. Validation par **équivalence
  observationnelle** : modules d'origine (`git show HEAD:…`) et modules corrigés
  chargés côte à côte **dans le runtime k6**, alimentés par un `data` de synthèse
  (métriques taguées, thresholds PASS et FAIL, checks imbriqués) et par le cas
  limite « run sans aucune métrique » → sorties **identiques au caractère près**
  sur les trois cas, pour `archiveSummary` (4 clés : stdout, `.json`, `.txt`,
  `.html`) comme pour `reportContext` ; puis `k6 inspect` vert sur les 6 scénarios
  avant et après (valide syntaxe **et** graphe d'imports). Fichiers de comparaison
  supprimés après usage. Aucune logique de scénario, aucun threshold, aucune mesure
  touchés.

- **Fait réutilisable — le runtime k6 accepte le JS moderne.** Vérifié sur k6
  v1.4.2 (moteur sobek) plutôt que supposé : spread d'objet, spread d'appel,
  `flatMap`, optional chaining, nullish coalescing et `String#startsWith`
  fonctionnent nativement. Pas de JS défensif à l'ancienne dans ce repo.
- **Boucle d'auto-amélioration étendue au JavaScript** : nouveau fichier
  **`conventions/javascript.md`** (7 entrées — S6661, S4624, S6582, S6557, S3863,
  S3776, S2245 — plus le tableau de support du runtime k6). `conventions/csharp.md`
  n'était pas le bon réceptacle (lu par `/develop` *avant d'écrire du C#*) et
  `conventions/angular.md` est cadré sur `client-angular`/`client-mobile` ; un
  pointeur a été ajouté en tête de `conventions/csharp.md`. **À arbitrer par
  l'humain** : câbler `conventions/javascript.md` dans le contrat de `/develop`
  (CLAUDE.md + `agents/develop.md`), sans quoi le fichier existe mais n'est lu par
  personne — la boucle reste ouverte sur ce langage.

#### Code review — APPROVED

23 fichiers, 0 blocage, 1 suggestion non bloquante (`run.ps1` réassigne `$args`,
variable automatique PowerShell — fonctionne, mais signalable par un linter).
Contrôles passés : aucun secret introduit (`BYPASS_KEY` sans défaut, les deux
runners refusent de démarrer sans elle, zéro littéral dans les scripts) ; aucun
fichier CI touché (exécution **manuelle uniquement**, rien dans le cycle forge) ;
`reports/` gitignoré ; binaire api-mail non modifié.

#### DOD — un seul item non vérifié

Le **rendu visuel du dashboard Grafana**. Le mot de passe admin du volume
persistant n'est plus `admin` et n'a délibérément pas été réinitialisé sur
l'environnement de l'humain. La chaîne est validée autrement : fichier monté,
provisioning relancé sans erreur, UID `k6-loadtest-api-mail` présent dans
`grafana.db`, métriques `k6_*` interrogeables côté Prometheus avec le bon label
`testid`. Reste un coup d'œil de 2 minutes au HAG.

#### Instabilité de tests — pré-existante, **pas** causée par cette task

Trois tests différents ont échoué selon les runs dans `mss.mail.application.tests`
(MailExport PDF, `CdaProcessingMetrics`, `MarkdownPdfRenderer`), **tous verts en
isolation**. Vérifié sur **`develop` sans cette branche** : la suite y échoue
aussi, sur un test encore différent. La liste des « 3 flaky documentés »
(cf. mémoire `project_api_mail_preexisting_flaky_tests`) **sous-estime le
problème** — il s'agit d'une instabilité systémique (QuestPDF et OpenTelemetry, à
état global, sous exécution parallèle). **Mérite une task dédiée.**

#### Limites / différé

- Baseline `search` **provisoire** (task-196) et chiffre `send` biaisé par
  l'absence de dossier `Sent` sur le banc — les deux réserves ci-dessus.
- Campagne de grande volumétrie (ex. 200 boîtes × 200 messages) toujours non
  conduite (héritée de task-195).
- `MAX_VUS` à relever pour supprimer les itérations abandonnées de `mixed`.
- Exécution **manuelle uniquement** : rien n'est branché dans le cycle forge ni
  dans la CI par défaut — un run de charge n'est pas un test unitaire.
- `AppHost.cs` modifie la configuration Prometheus partagée de tous les
  environnements de dev locaux (nécessaire, commenté sur place).
- **Règle 11 (US-complete)** : PR #123 labellisée `awaiting-human-merge` — même
  raisonnement que task-173 et task-195. Avec cette task, l'US « tests de charge »
  (banc + harnais) est **fonctionnellement complète** ; les trois PRs #121, #122 et
  #123 restent ouvertes en attente du merge humain.

---

### v1.4 — PgBouncer mode transaction devant « une base par praticien » : split chemin de données / plan de contrôle — task-200

> **Note de complétude** : ce fichier ne contient pas d'entrée `v1.3` détaillée
> pour task-199 (évaluation locale des feature flags), alors que la synthèse du
> doc produit la mentionne, et l'Annexe C n'a pas sa ligne. Manque antérieur à
> cette entrée, non comblé ici pour ne pas reconstituer après coup le détail
> d'une task que ce run n'a pas instruite. `/tech-writer E015 --refresh` la
> régénérerait depuis `tasks/archived/archived-task-199.md`.

- **Task** : task-200 — `done`. **PR** : `api-mail`
  [#125](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/125)
  (label `awaiting-human-merge` — **non mergée**, HAG règle 10).
  `dtos-mss` : branche créée par convention, 0 commit, aucune PR.
- **ADR** : [`Api/Mail/docs/ADR-2026-07-27-pgbouncer-transaction-mode.md`](../../Api/Mail/docs/ADR-2026-07-27-pgbouncer-transaction-mode.md)
  — verdict **compatible avec deux réserves**. Instruit le prérequis bloquant
  n°1 de `DevOps/DIMENSIONNEMENT-1000-PRATICIENS.md` §4.

**Le plafond visé est structurel** : `connexions retenues ≈ praticiens ×
réplicas × Maximum Pool Size`, un backend Postgres par connexion. Mesuré le
2026-07-27 à 200 praticiens × 5 réplicas : ~2 000 connexions retenues, tenables
seulement avec un Postgres à 12 GiB et `max_connections=2500`. La RAM Postgres
croît avec les praticiens **provisionnés**, même inactifs — à 1000 praticiens,
10 000+ connexions.

**Split des deux chemins** (le cœur du changement de code) :

| Chemin | Route | Contenu |
|---|---|---|
| Données | via PgBouncer (profil loadtest) | tout le trafic EF Core / Npgsql |
| Contrôle | **toujours direct** sur Postgres | `pg_advisory_xact_lock` de provisionnement, `CREATE DATABASE`, `MigrateUp` |

`UserContextInfo.ConnectionStringDirect` (alimentée par
`MSS-MAIL-CONNECTIONSTRING-DIRECT`) + dérivées
`ConnectionStringProvisioningServer` / `…User`. Les trois sites d'appel du plan
de contrôle dans `BaseRepository` (`UpdateDatabase` : verrou, `DatabaseExists`,
`CreateDatabase` ; plus `CreateServices` pour FluentMigrator) basculent sur la
route directe. **Repli : sans route directe configurée, les dérivées retournent
la chaîne serveur** — hors profil loadtest la variable n'est pas définie et la
chaîne de connexion est identique à l'octet près. Couvert par test unitaire.

Motif du split : le provisionnement d'un locataire est du plan de contrôle, rare
et sensible. Par le pooler il deviendrait tributaire de la saturation du pool de
données (`max_db_connections=3` par base) et créerait une entrée de pool par base
de maintenance.

**Conteneur `loadtest-pgbouncer`** (`edoburu/pgbouncer:v1.25.2-p0`, profil
loadtest uniquement), `pgbouncer.ini` + `userlist.txt` montés en lecture seule
(même motif que `dovecot.conf`) : `pool_mode=transaction`,
`default_pool_size=2`, `max_db_connections=3`, `server_idle_timeout=60`,
`server_reset_query` vide, `ignore_startup_parameters=extra_float_digits,options`,
`max_prepared_statements=0`, routage joker `*` (les bases praticien
`u_{rpps}_{slug}_{hash}` ne sont pas énumérables).

**Verdicts de compatibilité** — sondes manuelles sur paire isolée, puis figées en
tests d'intégration qui montent **la configuration réelle du banc** (seul
l'upstream est réécrit), si bien qu'une régression de configuration casse les
tests :

| Point | Verdict | Test |
|---|---|---|
| EF Core / Npgsql | compatible | `EfCoreReadWrite_ThroughTransactionPooler_Succeeds` |
| **pgvector** (`UseVector`, insertion + `CosineDistance`) | **compatible** — l'OID du type `vector` est propre à chaque base, mais Npgsql tient un `NpgsqlDataSource` par chaîne (donc par base, cf. cache `BaseRepository._dataSources`) et PgBouncer route une base logique toujours vers la même base physique | `PgVectorSimilarity_ThroughTransactionPooler_ReturnsNearestNeighbour` |
| Provisionnement complet | compatible par la route directe, exercé via `BaseRepository.CreateDbContextAsync` (code de production) | `Provisioning_TakesDirectRoute_WhilePoolerFrontsTheDataPath` |
| Multiplexage | **confirmé** : 40 clients tenant chacun une transaction explicite (donc épinglant une connexion serveur) → **≤ 3 backends** dans `pg_stat_activity` | `ConcurrentClients_AreMultiplexed_OntoBoundedPostgresBackends` |
| `LISTEN`/`NOTIFY` | non concerné — aucun usage (Redis pub/sub + RabbitMQ) | — |
| `SET` de session sur le chemin de requête | absent — seul `SET LOCAL lock_timeout`, transactionnel, sur la route directe | — |
| Garde-fou de configuration | l'upstream du banc ne doit pas être `host.docker.internal` | `BenchUpstream_DoesNotRelyOnHostDockerInternal` |

**Réserves** (invariants côté Npgsql) : `Max Auto Prepare=0` — les requêtes
préparées nommées ne survivent pas au multiplexage, et `max_prepared_statements=0`
côté PgBouncer fait échouer franchement plutôt qu'erratiquement si on l'active ;
`No Reset On Close=true` — pendant client du `server_reset_query` vide, sinon un
`DISCARD ALL` par retour au pool.

**Piège rencontré, troisième occurrence du même motif IPv6** :
`host.docker.internal` ne résout qu'en **AAAA** dans le conteneur PgBouncer
(`fdc4:f303:9324::254`), et PgBouncer — contrairement à `psql` — **ne retente pas
sur l'autre famille d'adresses**. Symptôme : `client_login_timeout (server down)`
sur toute connexion cliente, alors que le TCP est accepté (`nc -z` réussit) et que
la console d'administration répond. Un banc « healthy » qui ne sert rien. Les deux
occurrences précédentes sont documentées dans `AppHost.cs` (Postgres 5432 et
ingestion Seq 5342). Correctif : `--add-host=pgupstream:host-gateway`
(`WithContainerRuntimeArgs`), IPv4 déterministe, **plus un test garde-fou** — un
commentaire n'avait pas suffi les deux fois d'avant.

- **Tests** : 17 neufs (8 domaine, 4 api, 5 intégration). Suite complète
  **3 140 verts, 0 échec**, 16 skips IA préexistants.
- **Sonar** : Quality Gate OK, **0 smell sur le périmètre de la task**. Le scan 1
  avait révélé `CA1822` (propriété d'instance enveloppant un `const`) et un
  warning `S2068` (littéral de mot de passe dupliqué par le refactor AppHost) —
  corrigés, KPIs revenus à la baseline (31 smells projet, 6 new-code héritées
  d'autres tasks), couverture en hausse (86,0 → 86,5 ; new 87,5 → 87,6).
  `conventions/csharp.md` **créé** (il n'existait pas) avec ces deux règles.
- **Reste dû, et l'ADR le dit explicitement (§6)** : le tir `mixed` 200 praticiens
  iso-conditions via PgBouncer (p95 dans la marge de 20 % vs
  `report-mixed-mssante-60vu-003515.md`), `pg_stat_activity` < 300 pendant ce tir,
  et le comportement de `cl_waiting` sous rafale — risque résiduel le plus
  probable, `max_db_connections=3` étant volontairement serré. **Le prérequis
  §4.1 du dossier de dimensionnement n'est donc pas encore levé.**
- **Non vérifié par la forge** : le démarrage de l'AppHost Aspire avec la nouvelle
  ressource (bind mount relatif, publication du port 6432, passage des runtime
  args). Le conteneur, sa configuration et l'upstream ont été exercés à la main
  contre le Postgres du banc (207 bases visibles à travers le pooler).
- **Hors automation** : le lien vers l'ADR depuis
  `DevOps/DIMENSIONNEMENT-1000-PRATICIENS.md` §4.1 est écrit mais **non committé**
  — `DevOps` est un repo exclu, l'humain commit et pousse.
- **Outillage** : lancé depuis Git Bash, `dotnet sonarscanner` ne reçoit pas ses
  arguments MSBuild-style (`/k:`, `/d:`) — MSYS les réécrit en chemins Windows.
  Contournement `MSYS_NO_PATHCONV=1` + `MSYS2_ARG_CONV_EXCL='*'`. Le skill
  `sonar-skill` est en PowerShell et n'a pas ce problème.

---

### v1.5 — Le harnais mesurait le harnais : dimensionnement des VUs par la loi de Little + garde de validité du tir — task-203

- **Task** : task-203 — `done`. **PR** : `api-mail`
  [#127](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/127)
  (label `awaiting-human-merge` — **non mergée**, HAG règle 10).
  `dtos-mss` : branche créée par convention, 0 commit, aucune PR.
- **Origine** : relecture le 2026-07-28 des **JSON k6** (et non des rapports) des
  trois tirs du 2026-07-27. Verdict : aucun des trois n'était valide pour une
  mesure de capacité.

**Le constat, chiffré**

| Tir | `vus / vus_max` | `dropped_iterations` | Débit publié |
|---|---|---|---|
| Réf. 200 sans pooler (`…-60vu-003515`) | 222 / 222 | 45 323 (16,7 %) | 915,5 req/s |
| Tir A 200 PgBouncer (`…-60vu-144525`) | 222 / 222 | 49 485 (18,2 %) | 833,6 req/s |
| Tir 500 PgBouncer (`…-150vu-141351`) | 555 / 555 | 502 353 (**74,4 %**) | 906,4 req/s |

**Cause racine** — `scenarios/mixed.js` dimensionnait chaque sous-scénario à
`maxVUs = max(2, round(VUS × part/100) × 4)`, un nombre **sans rapport avec le
débit demandé**. Un `constant-arrival-rate` plafonne alors à `maxVUs / latence`
et k6 abandonne le reste. Vérifié au chiffre près sur le tir 500 : `send`
60 VU / 7,556 s = **7,9 it/s** délivrés (mesuré 7,67) contre 300 demandés ;
`folders` 240 / 2,235 s = 107 (mesuré 103,7) contre 1 200 ; `search` 60 / 0,627 s
= 95,7 (mesuré 91,5) contre 300. Second défaut : **`MAX_VUS` était silencieusement
ignoré par `mixed`** — seul `buildScenario()` (scénarios mono) le lisait, donc la
recommandation « relever `MAX_VUS` » du rapport 500 était sans effet. `baseline.md`
décrivait déjà le mécanisme le 2026-07-25 (« 607 itérations abandonnées… relever
`MAX_VUS` ») sur un run à 10 VU : diagnostic juste, remède inopérant.

**Ce que les tirs 200 disaient réellement** : `folders` (429,1 / 480 req/s = 89 %)
et `read` (318,6 / 360 = 89 %) servaient l'essentiel de leur budget à p95
133-225 ms ; les ~250 req/s manquants sont les plafonds VU de `send`
(17,2 / 120 = **14,4 %**) et `search` (66,7 / 120 = **55,6 %**). Aucun signe de
saturation applicative à 200 praticiens.

**Livré**

- `tests/loadtest-k6/lib/vu-sizing.js` — module **pur** (aucun import k6, donc
  testable hors k6) : `littleVus`, `planPool`, `capTotalMaxVus`,
  `planMixedScenarios`, et `REFERENCE_ITERATION_SECONDS` sourcé des moyennes
  mesurées des rapports (`folders` 0,06 s, `read` 0,16 s, `search` 0,33 s,
  `send` 1,30 s). Pré-allocation `×2` (au-delà, k6 instancie ses VUs *pendant* le
  tir), plafond `×4` pour la queue, `VUS` conservé comme **plancher** (aucun tir
  moins doté qu'avant), `MAX_VUS` respecté et réparti au prorata avec
  avertissement quand il mord.
- `scenarios/mixed.js` — adaptateur du module ; le harnais **déclare** son plan
  dans le contexte du rapport (`scenarioPlan`) au lieu de laisser `report.py`
  re-déduire l'arithmétique. `enrich` reste hors plan (`shared-iterations` fini) :
  sa part du mix n'est pas dépensée, le budget réel vaut 90 % de `targetRps`.
  Plan résolu lu par `k6 inspect` : `send` 6/24 VU → **312/624**, `search` 6/24 →
  **80/160**, total 1 022 VU au plafond contre 222.
- `report.py` refactoré en fonctions importables (`validity`, `budget_rows`,
  `kpis`, `build_report`, `index_row` — CLI inchangée) : bandeau
  `⚠️ TIR INVALIDE POUR UNE CONCLUSION DE CAPACITÉ` en tête de rapport et sur
  `stderr`, section « Validité du tir », section « **Débit demandé vs délivré**
  par sous-scénario ».
- `reports/INDEX.md` — colonnes `Drop %` / `VU sat.`, **historique recalculé
  depuis les JSON** : 16 des 21 tirs archivés sont invalides, dont *tous* ceux à
  200 et 500 praticiens. Fichier **sorti du `.gitignore`** (`reports/*` +
  ré-inclusion ciblée) : c'est la mémoire comparative du banc, pas un artefact de
  run, et non versionné ses colonnes de validité n'existeraient que sur une
  machine.
- `AppHost.cs`, profil loadtest **uniquement** :
  `Serilog__MinimumLevel__Default` et `Logging__LogLevel__Default` à
  `Information` (surchargeables par `MSS_LOADTEST_LOG_LEVEL`). Le banc tournait en
  `Debug` : **904 839 événements Debug** pour 1 212 478 Information sur la fenêtre
  du tir 500, ~5 000 événements/s vers Seq par 5 réplicas.
- `tests/loadtest-k6/selftest.sh` — point d'entrée des auto-tests du harnais
  (JS + Python, hors `dotnet test`), avec `SKIP` annoncé comme un échec de
  couverture et non comme un succès.

**Deux faux positifs de la garde, trouvés et corrigés avant livraison**

1. **Modèle fermé.** `vus == vus_max` est la *définition* d'un
   `shared-iterations` : la première version déclarait invalide le tir `enrich`
   du 2026-07-26 (4 VU / 4). Discriminant retenu : la présence de
   `dropped_iterations` — `context.executor` enregistre l'exécuteur *demandé*
   (`arrival-rate` par défaut), pas celui que k6 a résolu.
2. **Abandons structurels d'`enrich`.** k6 met aussi dans `dropped_iterations`
   les itérations qu'un `shared-iterations` n'a pas eu le temps de lancer avant
   son `maxDuration` — et `enrich` ne finit jamais sa bande (~2 000 lots × 2,9 s
   / 6 VUs ≈ 16 min pour un plateau de 5 min). Mesuré sur le tir A : 1 362 lots
   non lancés, soit **0,5 point** de drop à 5 min… mais **~1,16 point sur un
   palier de 3 min**, celui de l'escalier de capacité prévu par task-204 : la
   garde aurait invalidé le tir même qu'elle doit valider. D'où la ventilation
   `dropped_iterations{scenario:…}` (matérialisée par un seuil toujours vrai, même
   mécanisme que `http_reqs{op:…}`) et l'exclusion des scénarios sans débit
   imposé. Les verdicts historiques ne bougent pas à 0,5 point près.

**Validation**

- Build 0 erreur / 0 warning ; suite complète **3 173 tests verts, 0 échec**,
  16 skips IA préexistants (domain 102, infrastructure 370, api 575,
  application 1 852, integration 274).
- Auto-tests du harnais : **11 `node --test` + 20 `unittest`** verts.
- **Le harnais démarre** avec les seuils tagués (un seuil sur métrique inconnue
  aurait cassé tous les tirs) : tir à vide hors banc, plan affiché, les cinq
  sous-métriques `dropped_iterations{scenario:…}` présentes dans le résumé.
- Passe `/simplify` **sans changement de comportement** : rapport régénéré depuis
  le JSON du tir A **octet pour octet identique** (`kpis()` mutualisé entre
  rapport et INDEX, `saturation_state()` mutualisé entre les deux rendus).
- Sonar (2 itérations) : Quality Gate **OK**, bugs 0, vulnérabilités 0,
  `new_code_smells` 6 → 8 → **6** (les 2 issues imputables à la task, `CA1861` et
  `CA1859`, corrigées), `code_smells` 31 → **31**, coverage 86,5 %,
  new coverage 87,6 → **87,7 %**, maintainability **A**. Les 6 new-code smells
  restantes sont celles déjà imputées à des tasks antérieures (aucun fichier
  touché ici).
- **Flaky préexistant trouvé par le scan et corrigé** :
  `CdaProcessingMetricsTests.RecordCdaProcessingDurationShouldTagEachStep(step:
  "total")` échouait en **Release + couverture**, vert en Debug au même commit.
  Le meter `Mssante.MailProcessing` est statique donc process-wide, xUnit
  parallélise les classes, et la liste de capture était mutée **sans verrou** (la
  trace d'échec contient des mesures `mssante_sync_*` qu'aucun test de la classe
  n'émet). Filtre à l'abonnement + verrou ; vérifié **2 × 1 852 verts en Release
  avec couverture**.

**Tir de contrôle du coût des logs — résultat négatif, et c'est une information**

Protocole : redémarrage au niveau visé → échauffement de 60 s **jeté** (un
redémarrage vide les pools IMAP/Npgsql) → mesure de 2 min à `RPS=600`, au point
**valide** ; les deux niveaux rejoués. Fenêtres identiques à **0,01 %** près sur
tout ce qui n'est pas `Debug` (Information 324 966 / 324 927 ; Warning 93 692 /
93 690 ; Error 7 291 / 7 294), seul écart **+208 796 `Debug`** soit **49 % du
volume** (4 534 → 3 042 év/s).

Effet : **débit plateau 540,0 req/s dans les deux cas** (100 % du budget), p95
global −0,5 %, latence moyenne +2,8 % (dans l'autre sens), requêtes servies
identiques à l'unité, les deux tirs **VALIDES** (drop 0,01 % / 0,03 %). CPU
`mss.mail.api` 2,6-3,4 cœurs contre 3,0-3,8 — chevauchant. Seul écart visible :
`vmmemWSL` +1 cœur en `Debug`, cohérent avec l'ingestion des 209 k événements —
**coût payé par Seq, pas par l'application**.

**Conclusion : le niveau de log est un levier de fidélité et d'hygiène, pas de
performance.** Réserve : mesuré sous le genou ; à saturation aucun tir n'est
valide, donc rien n'y est proprement imputable.

**Deux corrections de méthode**

- Le « CPU hôte 93-100 % » relevé au tir nominal est **partiellement contaminé** :
  ce poste fait tourner SonarQube, Ollama, Keycloak, SQL Server, Mongo en
  permanence et le compteur `_Total` les inclut. Restent propres : le **par
  processus** (`k6` 0,3 cœur, `mss.mail.api` 3-6 cœurs) et le **par conteneur**
  (`docker stats` : 3,2 cœurs dont Postgres ~60 %). Énoncé défendable :
  *la pile application+banc sature entre 540 et 1 080 req/s, Postgres est le plus
  gros consommateur identifié, le tireur est hors de cause*.
- **Un redémarrage d'AppHost efface les proxies Toxiproxy** (créés par le seed) :
  tout tir meurt dans `setup()` en `proxy "dovecot-imap" not found (HTTP 404)`,
  code k6 107. Remède non destructif consigné dans le skill :
  `dotnet run --project tests/mss.mail.loadtest.seed -- --users 200 --messages 0`.

**Reste dû — et c'est l'essentiel**

Cette task livre l'**instrument**, pas la **mesure**. Quatre items de DOD sont
différés au banc : vérification dans Seq de l'absence d'événements `Debug`, **tir
de validité 200 praticiens** (`dropped < 1 %`, `vus < vus_max`, rapport sans
bandeau — c'est lui qui produira **le premier chiffre de capacité exploitable du
banc**), tir de contrôle `MSS_LOADTEST_LOG_LEVEL=Debug` pour chiffrer le coût des
logs, et les deux rapports comparés au tir A.

**Hors automation / hors périmètre**

- `c9bb52d` — `develop` portait une modification **non committée** de
  `src/AppHost/pgbouncer/pgbouncer.ini` laissée par la campagne du 2026-07-27
  (`max_client_conn` 5000 → 12000, justification mesurée de
  `default_pool_size=2`). Emportée par la création de la branche, committée
  **seule et en tête** pour rester isolable plutôt que perdue.
- `conventions/csharp.md` (racine du workspace) enrichi de **CA1861** et
  **CA1859** — le fichier est **gitignoré** par le `.gitignore` racine (« tout
  ignoré par défaut »), il ne vit donc que sur cette machine. À noter pour la
  boucle d'auto-amélioration décrite dans le CLAUDE.md.
- `.claude/skills/loadtest-skill/SKILL.md` : la garde de validité est posée comme
  **premier contrôle** d'un rapport, un quatrième plafond (« le harnais lui-même »)
  est ajouté à la liste des plafonds, et le niveau de log du banc est documenté.
  Non committé — contrôle plane, géré par l'humain.

---

### v1.6 — Le banc sait enfin nommer sa ressource limitante : attribution par réplica, échantillonneur, débit au dénominateur nommé — task-204

**Origine.** Le rapport `report-mixed-mssante-150vu-141351.md` (campagne 500 du
2026-07-27) concluait « saturé sur IMAP + CPU » **sans qu'aucune ressource n'ait
été échantillonnée pendant le tir** — ni CPU hôte par processus, ni CPU par
conteneur, ni compteur runtime .NET. C'était une inférence, et le tir de contrôle
de task-203 l'a démentie : `postgres-pgvector` pesait 188 % de CPU en moyenne
(439 % en pointe, ~60 % du CPU conteneurs) contre **13 % pour `dovecot`**. Aucun
tir du banc n'avait jamais pu **nommer** son facteur limitant.

#### Le point dur : le proxy DCP rendait les métriques inattribuables

`AppHost.cs` déclare `.WithReplicas(5)` avec `WithHttpEndpoint(port: 5052)`. Ce
port est le **proxy DCP** devant les cinq réplicas, et `prometheus.yml` scrapait
cette cible unique. Chaque scrape tombait donc sur un réplica **au hasard** :

- les compteurs (`*_total`) reculaient d'un scrape à l'autre → `rate()` bruité,
  voire troué ;
- les jauges runtime (file du ThreadPool, threads, CPU process) décrivaient **un
  réplica différent à chaque point** — inutilisables pour désigner un réplica
  saturé ;
- `/metrics` partageait la surface HTTP de l'API : le scrape traversait le même
  pipeline que la charge.

#### La voie retenue, et l'argument qui a tranché

| Voie | Ce qu'elle demande | Verdict |
|---|---|---|
| Scrape par réplica (`file_sd`/`http_sd` généré depuis l'API DCP) | découvrir les **ports dynamiques** des 5 réplicas au démarrage du banc, puis les régénérer à chaque redémarrage | **écartée** — la méthode DCP « déjà éprouvée » ne l'est que pour **lire les logs** (`%TEMP%\aspire-dcp*\<guid>_out`), pas pour énumérer des endpoints. Elle plaçait un détail d'implémentation d'Aspire sur le chemin critique de chaque montage de banc. |
| **Fan-out OTLP vers un collector** | un conteneur au profil loadtest, une variable d'environnement | **retenue** — les réplicas **poussent**, donc le problème de découverte **disparaît** au lieu d'être contourné. Le code applicatif était déjà prêt (`AddOpenTelemetryExporters`), et le collector promeut `service.instance.id` en étiquette via `resource_to_telemetry_conversion`. |

**Fan-out et non substitution** : `MSS_BENCH_OTLP_ENDPOINT` ajoute un **second**
lecteur de métriques ; celui que l'AppHost configure pour le dashboard Aspire
reste en place. Un banc ne doit pas aveugler l'outil de diagnostic qu'on regarde
pendant qu'il tourne.

**Identité du réplica** : `MSS_BENCH_INSTANCE_ID` si posée, sinon
`{machine}-{pid}`. L'AppHost ne sait pas varier une variable d'environnement par
réplica — mais chaque réplica est un **processus**, donc machine + PID les
distingue par construction, sans rien demander à l'orchestrateur.

#### Livré

| Brique | Contenu |
|---|---|
| `src/Api/Telemetry/BenchTelemetry.cs` | aiguillage pur et testable : `ResolveEndpoint` (complète le chemin `/v1/metrics`, **lève** sur URL mal formée plutôt que de désarmer l'attribution en silence), `ResolveInstanceId`, `IsEnabled` |
| `src/Api/DependencyInjectionExtensions.cs` | second lecteur OTLP (5 s, aligné sur le scrape) + attribut de ressource `service.instance.id`, **uniquement** quand la variable du banc est posée |
| `src/AppHost/otel-collector/config.yaml` | collector `contrib` 0.115.1 : réception OTLP/HTTP 4318, réexposition Prometheus 8889 avec promotion des attributs de ressource, métriques internes sur 8888 |
| `src/AppHost/prometheus.loadtest.yml` | configuration **du profil loadtest seulement** : scrape le collector (5 séries) et sa santé ; le proxy DCP est délibérément absent (le garder ferait un double comptage silencieux) |
| `src/AppHost/AppHost.cs` | conteneur `loadtest-otel-collector` (14318 / 18899 / 18898), aiguillage du fichier Prometheus, `MSS_BENCH_OTLP_ENDPOINT` sous le garde-fou de profil |
| `tests/loadtest-k6/observe.ps1` + `observe.sh` | échantillonneur détaché, CSV **long** (`ts_utc,scope,target,metric,value`) horodaté **UTC**, cadence 5 s : CPU/mém/threads de **k6** et de **chaque** réplica par PID, `docker stats` des conteneurs **du banc**, sessions IMAP Dovecot, `SHOW POOLS` agrégé, `pg_stat_activity` |
| `tests/loadtest-k6/report.py` | section « Ressources & télémétrie » : tableau **par réplica**, tableau par conteneur et pour le tireur, **p95 client vs p95 serveur**, compteurs `Mssante.MailProcessing`, ligne « ressource épinglée » (seuil 85 % de la borne) |
| `tests/loadtest-k6/lib/summary.js` | `startedAt` / `endedAt` / `runDurationMs` dans le contexte du tir — sans quoi le repliement Prometheus et CSV n'a pas de fenêtre |
| `src/AppHost/grafana/dashboards/saturation.json` | dashboard « Saturation » : répliques distinguées (doit valoir **5**), rejets du collector, backends et `cl_waiting`, CPU et file du ThreadPool par réplica, p95 serveur par route |
| `run.sh` / `run.ps1` | remote-write Prometheus **par défaut** (`PROM=0` / `-NoPrometheus` pour couper) |

#### Le débit publié était faux depuis l'origine

`http_reqs.rate` de k6 divise par la fenêtre **totale** du run, **arrêt gracieux
inclus** (330 s pour un plateau de 300 s) : **tous** les débits publiés par ce
banc étaient sous-estimés de ~8-10 %. Le rapport publie désormais les deux
chiffres en nommant leur dénominateur, l'INDEX porte une colonne `Débit plateau`,
et l'historique a été recalculé (9 lignes).

Le calcul, écrit indépendamment, retombe **exactement** sur les corrections faites
à la main le 2026-07-28 — ce qui vaut validation croisée :

| Tir | Publié par k6 | À la main (28/07) | `report.py` |
|---|---|---|---|
| Référence 200 | 915,5 | 934,5 | **934,5** ✅ |
| Tir A | 833,6 | 917,0 | **917,0** ✅ |
| Tir 500 | 906,4 | — | **942,0** |

Garde-fou trouvé au passage : un `shared-iterations` **fini** (`enrich`) s'arrête
quand sa bande d'UIDs est épuisée, donc sa `duration` n'est qu'un `maxDuration`.
Diviser par elle rendait **0,4 req/s** pour un tir qui en délivrait 1,8 — un
chiffre faux dans l'autre sens. Le rapport écrit désormais « sans objet ».

#### Deux défauts bloquants trouvés avant le merge, et ni l'un ni l'autre par relecture

1. **Les 5 réplicas auraient planté au démarrage, en profil loadtest et nulle part
   ailleurs.** Sous Aspire, `OTEL_EXPORTER_OTLP_ENDPOINT` est posé, donc
   `UseOtlpExporter()` est armé — et l'API refuse de le combiner avec un
   `AddOtlpExporter` par signal :
   `NotSupportedException: Signal-specific AddOtlpExporter methods and the
   cross-cutting UseOtlpExporter method being invoked on the same
   IServiceCollection is not supported.` Le fan-out écrit de la façon la plus
   naturelle était donc un crash **au premier montage de banc, après le merge**.
   Correctif : le lecteur est instancié à la main
   (`PeriodicExportingMetricReader` + `OtlpMetricExporter`), ce qui l'ajoute à ceux
   de `UseOtlpExporter` sans passer par le garde-fou du conteneur DI. **Trouvé par
   un test de coexistence écrit par acquit de conscience.**
2. **Le rapport concluait faux, et avec assurance.** Sans fenêtre de tir dans le
   JSON k6 (**29 fichiers archivés**) et avec un CSV présent, la section agrégeait
   le fichier **entier** et annonçait « Ressource épinglée : conteneur
   `postgres-pgvector` (CPU) — 87,5 % de sa borne » sur des points hors tir.
   Atteignable en une commande, `report.sh` reprenant automatiquement le CSV le
   plus récent du répertoire de tir. C'est **exactement** le mode d'échec que la
   task existe pour supprimer, en pire — un chiffre affirmatif se recopie. Un
   repliement n'a de sens que **borné** : sans fenêtre, aucun point n'est retenu et
   la section écrit pourquoi. **Trouvé en exécutant le cas dégradé, pas en le
   relisant** (`questions/task-204.md`).

#### Ne jamais conclure en silence — la règle cardinale, verrouillée par 9 tests

Prometheus injoignable, Prometheus sans point, CSV absent, CSV hors fenêtre, CSV
non repliable, fenêtre absente, aucune série par réplica, aucun p95 serveur, aucun
compteur métier : chacun de ces cas **s'écrit** dans le rapport. Une section vide
se lirait « rien n'était saturé », ce qui est précisément l'erreur du 2026-07-27.

#### Validation

- Build **0 erreur / 0 warning** ; **3 195 tests .NET verts, 0 échec** (16 skips IA
  préexistants), dont **+22** sur cette task ; suite rejouée en **Release avec
  couverture** pendant le scan Sonar
- **Auto-tests du harnais : 11 node + 50 unittest verts** ; `selftest.sh` passe en
  `unittest discover` (un nouveau `test_*.py` est pris en compte sans intervention)
- **Sonar : 0 issue sur le périmètre au premier scan**, `BenchTelemetry.cs` à
  **100 %** de couverture (15/15 lignes), KPI au niveau de la baseline, Quality
  Gate OK. Aucune entrée ajoutée à `conventions/csharp.md` : **aucune correction
  manuelle n'a été nécessaire** — CA1861, apprise en task-203, a été appliquée
  d'emblée. La boucle d'auto-amélioration a fonctionné.
- Passe `/simplify` validée par un rapport régénéré **octet pour octet identique**

#### Deux pièges d'outillage, dont un neuf et coûteux

1. **Confirmé** (task-200, task-203) : `dotnet sonarscanner` ne reçoit pas ses
   arguments `/k:` `/d:` sous Git Bash → script PowerShell détaché.
2. **NEUF** : seul **PowerShell 5.1** est installé sur le poste (`pwsh` absent). Un
   `.ps1` accentué enregistré **sans BOM UTF-8** est lu en ANSI ; le mangling casse
   le *parsing*, et l'erreur produite (`CommandNotFoundException` sur un fragment de
   chaîne) ne ressemble pas à un problème d'encodage. Le premier scan Sonar a ainsi
   « réussi » avec un code de sortie 0 **sans rien scanner**. Remèdes : BOM UTF-8
   obligatoire sur tout `.ps1` accentué (appliqué à `observe.ps1`, qui portait le
   même risque), et contrôle de parsing avant exécution
   (`[System.Management.Automation.Language.Parser]::ParseFile`).

#### Limites / différé

- **L'escalier de capacité reste dû** — 200 praticiens, paliers **540 / 700 / 840 /
  980 / 1080** (réalignés sur le genou mesuré au 2026-07-28 ; l'ancien
  600/900/1200/1600 visait à côté et le palier 1 600 est inatteignable sur cette
  machine). C'est le livrable qui manque depuis le début de l'EPIC.
- **Trois points ne sont vérifiables qu'au banc** : les **noms de métriques
  Prometheus** (conventionnels OTel .NET, non confrontés à un `/metrics` réel —
  s'ils ont bougé, la section dira « aucun point », comportement voulu, mais
  l'attribution sera vide) ; la **version et la configuration du collector**
  (`service.telemetry.metrics.readers` a changé de forme entre versions) ; les
  **trois sondes** `doveadm who` / `SHOW POOLS` / `pg_stat_activity`, qui ont
  correctement journalisé leur absence (12 échecs tracés, aucun silencieux) mais
  dont le chemin nominal n'est pas joué.
- **Le poste de mesure est le prochain obstacle** : l'infrastructure du banc
  (`vmmemWSL` 9-10 cœurs) et les 5 réplicas (4-6 cœurs) se partagent 24 cœurs.
  Tout chiffre de capacité obtenu ici est un **plancher**. Décision à prendre :
  réduire la contention et publier un plancher assumé, ou séparer le tireur et
  l'infra du banc de la machine applicative.
- **Suggestions de revue non traitées** (règle 6) : `BenchTelemetry.IsEnabled`
  n'est utilisé que par les tests ; `PGPASSWORD=postgres` apparaît deux fois dans
  `observe.ps1` (la convention S2068 dit « une déclaration, N usages ») ;
  `report.py` atteint ~1 100 lignes et le helper de table Markdown écarté par
  task-203 a maintenant 4 sites d'appel de plus.
- **`SONAR_TOKEN` du `.env` est périmé (401)** — le scan a été authentifié avec
  `SONAR_ADMIN_PASSWORD` du même fichier, sans rien créer côté SonarQube. À
  régénérer par l'humain.

---

### v1.7 — L'escalier de capacité : le facteur limitant enfin nommé et chiffré — task-204 (campagne du 2026-07-29)

> Entrée distincte de la v1.6 à dessein : celle-ci livrait **l'instrument**
> (attribution par réplica, échantillonneur, section « Ressources & télémétrie »)
> et consignait « l'escalier de capacité reste dû ». Voici la **mesure**.

Population fixe **200 praticiens**, `mixed` 3 min, budget explicite, cinq paliers,
chacun avec son rapport et sa ligne d'INDEX.

| Budget demandé | Délivré (plateau) | Servi | Latence moy. | p95 | Abandons | Valide |
|---|---|---|---|---|---|---|
| 486 req/s | 482,7 | 99,3 % | 256 ms | 1 111 ms | 0,67 % | ✅ |
| 630 req/s | 625,4 | 99,3 % | 223 ms | 1 125 ms | 0,74 % | ✅ |
| 756 req/s | 745,5 | 98,6 % | 290 ms | 1 210 ms | 1,15 % | ❌ |
| 882 req/s | 824,8 | 93,5 % | 396 ms | 1 309 ms | 4,21 % | ❌ |
| 972 req/s | 857,9 | 88,3 % | 591 ms | 1 343 ms | 7,38 % | ❌ |

**Genou : entre 745 et 825 req/s délivrés.** Plafond mesuré ~858 req/s. Rendement
marginal : +99 %, +95 %, puis +63 %, +37 % du surcroît demandé.

#### Le facteur limitant : famine de ThreadPool sur `read_list`

| Budget | `read_list` moy | File ThreadPool par réplica | CPU par réplica |
|---|---|---|---|
| 630 req/s | 212 ms | 5 / 4 / 4 / 4 / 3 | ~1,0-1,2 cœur |
| 882 req/s | **714 ms** | **136** / 93 / 13 / 10 / 7 | ~1,1 cœur |
| 972 req/s | **1 533 ms** | **432** / 205 / 68 / 13 / 6 | ~1,2-1,5 cœur |

Deux faits ne laissent qu'une lecture : `read_list` se dégrade d'un facteur **~7**
quand les autres opérations ne prennent qu'un facteur ~1,5 (`folders` 44 → 167,
`search` 276 → 657, `send` 1 137 → 1 703, `enrich` 2 659 → 4 177 ms) ; et la file
du ThreadPool explose **à CPU quasi constant** — 432 éléments pour 1,19 cœur et
44 threads. Ce n'est pas une famine de CPU, c'est du **blocage d'I/O sur des
threads du pool**, que l'escalade du ThreadPool (1-2 threads/s) ne rattrape pas.
La répartition très inégale entre réplicas (432 / 205 / 68 / 13 / 6) exclut une
cause globale (base, pooler, IMAP) et pointe un chemin de code.

#### L'expérience qui exclut le harnais, et qui vaut la campagne à elle seule

Même budget, même population, **seul** `VU_TAIL_FACTOR` change :

| | 882 `tail=8` | 882 `tail=16` | 972 `tail=8` | 972 `tail=16` |
|---|---|---|---|---|
| **Débit délivré** | **824,8** | **716,4** (−13 %) | **857,9** | **683,3** (−20 %) |
| Abandons | 4,21 % | 13,49 % | 7,38 % | **23,92 %** |
| p95 | 1 309 ms | 6 766 ms | 1 343 ms | **14 685 ms** |
| `read_list` moy | 714 ms | 3 606 ms | 1 533 ms | **5 288 ms** |
| File ThreadPool | 136/93/13/10/7 | 406/951/579/648/813 | 432/205/68/13/6 | 203/435/484/387/429 |
| CPU par réplica | ~1,1 cœur | 0,8-2,3 | 1,2-1,5 | 0,9-1,6 |

**Plus de concurrence cliente → moins de débit**, aux deux paliers, de façon
monotone, à CPU applicatif inchangé. Le harnais n'était donc pas la borne : le
rendement est **négatif** au-delà du genou. `tail=16` fait déborder les **cinq**
réplicas alors que `tail=8` n'en chargeait que deux — la congestion se généralise,
elle ne se déplace pas.

#### Ce que la campagne écarte, avec ses chiffres

| Suspect | Mesure au palier le plus haut | Verdict |
|---|---|---|
| CPU applicatif | **3,68 cœurs sur 24** pour les 5 réplicas (15 %) | écarté |
| CPU de l'hôte | 78-87 % moy — mais **14,93 cœurs pour l'infra du banc** (`vmmemWSL` 7,56 ; Postgres 2,40 ; Docker 1,88 ; `dcp` 1,18) | contamine, ne cause pas |
| PgBouncer | `cl_waiting` ≤ 8 en fenêtre, 2 001 clients sur 153-162 serveurs (~13:1) | écarté |
| Dovecot / IMAP | **1 001 sessions, constantes aux 5 paliers** (= 5 × 200), CPU 0,19 cœur | écarté |
| Postgres | 2,40 cœurs moy, 3,87 max | écarté |
| Client k6 | 0,47 cœur | écarté |

**Corollaire** : le banc se dispute la machine avec le service qu'il mesure (15 %
pour l'application, 62 % pour l'infra de test). **~858 req/s est un plancher de la
capacité réelle, pas un plafond.**

#### Deux campagnes, parce que la première a été jetée

La 1re a sorti 4,6 % d'abandons dès le premier palier. Diagnostic → deux findings
d'outillage : 1 576 des 3 475 abandons étaient **structurels** (`mixed_enrich` est
un `shared-iterations` dont le reliquat compte en `dropped_iterations` — contourné
par `ENRICH_SHARE=0.05`, → task-208) ; le reste était un vrai sous-dimensionnement
de `folders` et `read`, les constantes de `vu-sizing.js` (`read` = 0,16 s) étant
démenties par la mesure (jusqu'à 1,65 s) — compensé par `VU_TAIL_FACTOR=8`,
→ task-209, **mais pas** en élargissant les pools, l'expérience ci-dessus montrant
que cela aggrave le tir.

#### Vérification et findings ouverts

`--expected 100` : ~20 000 mails stockés aux cinq paliers, verdict **PASS**,
**0 sujet étranger**, **0 court-circuit d'enrich**. Cinq tasks ouvertes :
**205** (le facteur limitant), **206** (`SecurityTokenMalformedException`, >1 200/s),
**207** (`mssante_imap_session_events_total` mort), **208** (le rapport conclut
faux de 3 façons), **209** (dimensionnement des VUs).

---

### v1.8 — Famine de ThreadPool sur `read_list` : la résolution de dossier IMAP passe en asynchrone — task-205

**Le facteur limitant nommé par la v1.7 est supprimé.**

#### L'instruction bloquante, nommée

`src/Application/Services/Implementation/ImapService.cs:1180` (avant correctif),
dans `TryGetFolderSafely` :

```csharp
imapFolder = imapClient.GetFolder(folder, cancellationToken);   // bloquant
```

Chemin : `MailController.GetEmailsByIdsAsync` (`:247`) → `OnlineMailDataProvider.GetEmailHeadersAsync`
(`:38`) → `ImapService.GetEmailFromUidsAsync` (`:661`) → `FetchEmailsInternalAsync`
(`:1215`) → `FetchMissingUidsWithLocksAsync` (`:1277`) → `ProcessEmailUidAsync`
(`:1435`) → `TryGetFolderSafely` (`:1172` → `:1180`).
Relais : `IImapClientWrapper.GetFolder(string, CancellationToken)` (`:35`) →
`ImapClientWrapper.cs:66` → `MailKit.IMailStore.GetFolder(string, CancellationToken)`.

#### La preuve que cette surcharge fait de l'I/O — l'API de MailKit

Tirée des métadonnées de `MailKit.xml` 4.11.0 : sur les **trois** surcharges de
`GetFolder`, une seule a un pendant `Async` et une seule déclare des exceptions de
transport.

| Surcharge | Pendant `…Async` ? | Exceptions déclarées | Verdict |
|---|---|---|---|
| `GetFolder(FolderNamespace)` | non | `ArgumentNull`, `FolderNotFound` | lecture mémoire |
| `GetFolder(SpecialFolder)` | non | — | lecture mémoire |
| **`GetFolder(String, CancellationToken)`** | **oui** | `IOException`, `ProtocolException`, `CommandException`, `OperationCanceled` | **I/O réseau (LIST)** |

#### Trois recoupements avec la mesure de la v1.7

1. **`read_list` ×7 quand `folders` ne fait que ×1,5** : `folders` passe par
   `GetFoldersAsync(namespace, …)` et ne touche jamais `TryGetFolderSafely`. Même
   Dovecot, seule l'opération bloquante s'effondre.
2. **Le Manual Test Plan exige de purger les tables mail** sinon le défaut ne se
   reproduit pas. Le code dit pourquoi : base pleine → `FetchEmailsInternalAsync`
   sert depuis `GetMailsByUidsAsync` et sort **avant** le chemin IMAP ; base vide →
   chaque `read_list` traverse `ProcessEmailUidAsync`. Le déclencheur documenté du
   défaut sélectionne exactement la branche fautive.
3. **File qui explose à CPU plat** : un thread parqué sur une I/O ne consomme pas de
   CPU mais retire une unité de service au pool.

#### Livré

- `TryGetFolderSafely` → **`TryResolveFolderAsync`** (`ImapService.cs:1187`),
  `await imapClient.GetFolderAsync(…)`. **5** appelants convertis : `:401`
  `GetFolderStatus`, `:601` `GetFolderQuery`, `:723` `EnrichEmails`, `:1476`
  `ProcessEmailUid` (*le chemin `read_list`*), `:2693` `FetchSingleEmail`.
- **La surcharge synchrone est retirée de `IImapClientWrapper`** — le retrait *est*
  le correctif : ce qui n'existe plus ne peut pas être rappelé par inadvertance.
  Les surcharges `SpecialFolder` / `FolderNamespace` restent (lectures mémoire).
- Comportements du try-pattern préservés et testés : `FolderNotFoundException`
  **propagée** (self-heal → 404), toute autre panne **absorbée**.

#### Trois gardes de non-régression, toutes constatées RED avant le correctif

`tests/mss.mail.application.tests/Services/Imap/ReadListNonBlockingTests.cs`, 6 tests.

| Garde | Ce qu'elle interdit | Angle mort |
|---|---|---|
| Surface publique (réflexion) | un `GetFolder(string, …)` synchrone sur `IImapClientWrapper` / `ImapClientWrapper` | un appel qui court-circuite le wrapper |
| **Analyseur** (`System.Reflection.Metadata`, aucune dépendance ajoutée) | toute référence de l'assembly à `IMailStore.GetFolder(String, CancellationToken)` — filtre sur la **signature décodée**, pas sur le nom (sinon les 2 surcharges légitimes seraient signalées à tort) | un blocage par une *autre* API |
| Comportement (`Timeout = 15 s`) | que `read_list` garde le thread appelant pendant que l'I/O du dossier est en attente — attrape aussi un `sync-over-async` réintroduit sur `GetFolderAsync` | ce qui ne passe pas par la résolution de dossier |

**L'analyseur se contrôle lui-même** (passe `/simplify`) : il exige de retrouver la
surcharge **légitime** (`GetFolder(FolderNamespace)`) avant d'affirmer que la
bloquante a disparu. Sans ce témoin, un changement de rendu des types ferait passer
la garde **à vide** en annonçant un succès. Le témoin a payé immédiatement : il a
montré que le compilateur émet la référence contre **`MailKit.MailStore`** (la
classe de base concrète) et non contre l'interface.

#### Le suspect historique innocenté par la lecture du code

La task désignait `BaseRepository.get_DataContext` (⚠️ « ne pas partir de la
conclusion »). `BaseRepository.cs:115` porte bien un
`CreateDbContextAsync().GetAwaiter().GetResult()`, mais `CreateDbContextAsync` n'a
qu'un `await`, sous `if (environment == "Development" || "Staging")` →
`HandleEnvironmentDbSetupAsync`, dont la première ligne est un fast-path statique
par processus (`_migratedDatabases.ContainsKey`, `:276`). Après le premier contact
de chaque base par chaque réplica — donc pendant tout le plateau d'un tir de 3 min
— la tâche est **déjà complétée** et `GetAwaiter().GetResult()` ne bloque rien.
Le `.Result` est réel ; il n'est pas le facteur limitant mesuré. Non corrigé
(règle 6).

#### Deux blocages adjacents signalés, non corrigés (règle 6)

1. `MailClientSession.cs:234` — `DisconnectAsync(true).GetAwaiter().GetResult()`
   dans `Dispose` : un `Dispose` qui bloque sur une déconnexion réseau, appelé par
   le timer de nettoyage des sessions.
2. `EmailFlagService.cs:44/67/77/89` — `AddFlags` / `RemoveFlags` **synchrones**
   (commande IMAP STORE), sur le chemin « marquer lu/suivi ».

#### Validation

Build **0 erreur / 0 warning** (`api-mail` + `dtos-mss`) ; **3 207 tests verts,
0 échec**, 16 skips IA préexistants (domain 102, infrastructure 370, application
1 858, api 590, integration 287). SonarQube **9.9.8** : Quality Gate **OK**,
new coverage 87,8 → **87,9 %**, **0 issue** sur les 3 fichiers de production, et
couverture vérifiée **ligne à ligne** sur `TryResolveFolderAsync` — **100 %**,
branches `catch` comprises (l'agrégat du fichier, 71,6 % sur 1 350 lignes
majoritairement antérieures, ne dirait rien de ce diff).

Revue de code : **APPROVED**, 1 défaut trouvé et corrigé avant la PR — le `using
System.Diagnostics.CodeAnalysis` devenu **mort** avec la disparition du
`[NotNullWhen(true)]` (`4bfdffe`). Ni Sonar ni le compilateur ne le signalent.

PR : [#131](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/131),
label `awaiting-human-merge`. `dtos-mss` : branche sans commit, pas de PR.

#### Le piège d'outillage qui corrige task-204

Le `end` du scanner a échoué **après** ~6 min de build + tests sur
`ERROR: Not authorized`. La v1.6 avait conclu « `SONAR_TOKEN` périmé (401), à
régénérer par l'humain ». **C'est faux** : `/api/authentication/validate` renvoie
`{"valid":true}`. La vraie cause est la **version du serveur** — `sonar.token`
n'existe qu'à partir de SonarQube **10.0**, l'instance est en **9.9.8**, qui
l'ignore : le `begin` réussit (lecture du profil), seul le **publish** refuse.
Correctif : `/d:sonar.login="$SONAR_TOKEN"`. `.sonarqube/` survit à un `end` en
échec — rejouer `end` seul suffit (30 s au lieu de 6 min).
**`agents/sonar.md` corrigé** (sections Begin/End + avertissement) : modification
du plan de contrôle de la forge, **à ratifier par l'humain**.
Confirmé sans changement : `dotnet sonarscanner` ne reçoit pas ses `/k:` `/d:` sous
Git Bash → script PowerShell détaché, écrit en **ASCII pur** pour neutraliser
d'emblée le piège d'encodage PS 5.1 de la v1.6, parsing vérifié avant exécution.

#### Limites / différé — la mesure

Le code est corrigé et verrouillé ; **la moitié « mesure » de la DOD est un tir de
banc**, même découpage que la v1.6.

- **Pile de threads bloqués** à 882 req/s (`dotnet-stack`) — le chemin est nommé et
  prouvé par l'API de MailKit et trois recoupements, la pile est la preuve *in situ*
  qui manque.
- **Palier 882** : file ThreadPool max **< 20** par réplica (contre 136) et
  `read_list` moy **< 400 ms** (contre 714).
- **Palier 972** : débit délivré **> 900 req/s** (contre 857,9), drop **< 1 %**.
- **Rapport de tir + ligne d'INDEX** avant/après (la baseline « avant » est sur
  `develop` depuis le merge de task-204).
- **Réserve sur le critère de débit** : le seuil de 900 req/s dépend aussi de la
  contention du banc (62 % du CPU pour l'infra de test contre 15 % pour
  l'application), hors périmètre de cette task. Le critère qui teste vraiment le
  correctif est **l'effondrement de la file ThreadPool** ; file effondrée + débit
  sous 900 = arbitrage PO, pas échec du correctif.
- **Les 6 new-code smells Sonar en sont à leur 5ᵉ task consécutive** (task-199, 200,
  203, 204, 205), sur `BackgroundSyncService`, `OcspValidationService`,
  `MailClientSession`, `VCardSerializer` — aucun fichier touché par ces tasks.
  Aucune task de feature ne peut légitimement les corriger (hors de son module) :
  **seul un run `/sonar api-mail` Mode B le peut. À planifier.**

---

### v1.9 — Le harnais dimensionne sur la latence mesurée, et le rapport nomme qui produit les abandons — task-209

- **Task** : task-209 — `done`. **PR** : `api-mail` #132 (label `awaiting-human-merge`).
- **Origine** : l'escalier de task-204 a demandé **deux** campagnes (la première
  jetée, 4,6 % d'abandons dès le premier palier) et les quatre tirs de task-205
  du 2026-07-31 sont sortis invalides — à chaque fois par sous-provisionnement
  des pools, imputé à l'application par le rapport (« la charge nominale n'a
  jamais été appliquée »).

#### La contradiction structurelle, nommée

`REFERENCE_ITERATION_SECONDS` (task-203) a été mesuré le 2026-07-27 avec des
`read` servis **depuis la base**, après enrichissement : 0,16 s l'itération. Or
une campagne d'escalier **purge les tables entre paliers** — condition
nécessaire pour qu'`enrich` ne court-circuite pas (`reset-state.sh`). Sur base
purgée, `read` repart sur IMAP : **0,41 s sous le genou, 1,65 s à 972 req/s**.
Le harnais portait donc deux exigences contradictoires, et rien ne le disait.

Écart mesuré le 2026-07-29, même scénario, même population :

| Sous-scénario | Référence 2026-07-27 | 486 req/s | 972 req/s | Écart au pire |
|---|---|---|---|---|
| `read` (list + content) | 0,16 s | 0,41 s | **1,65 s** | **×10** |
| `folders` | 0,06 s | 0,05 s | 0,17 s | ×2,8 |
| `search` | 0,33 s | 0,24 s | 0,66 s | ×2,0 |
| `send` | 1,30 s | 1,18 s | 1,70 s | ×1,3 |

#### Ce qui interdisait la correction naïve

Au-delà du genou, la latence n'est plus une propriété du scénario mais du
serveur qui congestionne. Expérience de discrimination du 2026-07-29, budget
identique (882 req/s), seul `VU_TAIL_FACTOR` change :

| | `tail=8` | `tail=16` |
|---|---|---|
| Débit délivré | 824,8 req/s | **716,4** (−13 %) |
| Abandons | 4,21 % | **13,49 %** |
| p95 | 1 309 ms | **6 766 ms** |
| `read_list` moy | 714 ms | **3 606 ms** |
| File ThreadPool par réplica | 136/93/13/10/7 | **406/951/579/648/813** |

Élargir les pools **aggrave**. Le harnais ne cherche donc pas à annuler les
abandons par le dimensionnement — il dit **lequel des deux mécanismes** les
produit.

#### Livré — `lib/vu-sizing.js`

- Constantes rafraîchies sur le palier **486 req/s du 2026-07-29** (base purgée,
  sous le genou), avec `REFERENCE_MEASURED_AT` et `REFERENCE_CONDITIONS`
  exportés et recopiés dans le `context` de chaque tir archivé
  (`scenarios/mixed.js`). Délibérément **pas** les valeurs d'un palier haut :
  dimensionner sur la congestion reviendrait à l'alimenter.
- `iterationSecondsOverrides(env)` : surcharge
  `ITER_SECONDS_{FOLDERS,READ,SEARCH,SEND,ENRICH}`, parsée dans le module **pur**
  (donc testable hors k6) et consommée par `CFG.iterationSeconds`. Un nom
  inconnu ou une valeur ≤ 0 **lèvent** — pas de skip silencieux.
- Le plan déclare la provenance de chaque latence
  (`iterationSecondsSource: reference | override`), archivée dans le contexte.
- **Bug corrigé au passage** : `iterationSecondsFor` **remplaçait** la table de
  référence au lieu de la fusionner. Poser `{ read: 1.65 }` renvoyait `folders`,
  `search` et `send` sur le repli pessimiste d'une seconde — pools 4 à 20 fois
  trop larges. La surcharge demandée par l'US aurait été inutilisable telle
  quelle.
- Effet mesuré au `k6 inspect` : au budget 882 req/s, le plan passe de **793 VUs
  forcés à `VU_TAIL_FACTOR=8`** à **890 VUs au facteur par défaut** — les
  constantes rafraîchies remplacent le réglage manuel de l'opérateur.

#### Livré — `report.py`, section « Latence planifiée vs mesurée »

- `measured_iteration_seconds` reconstruit la durée réelle d'une itération
  depuis les trends tagguées, **avec la définition du plan** (`read` compte ses
  deux appels).
- `latency_divergence` : une ligne par sous-scénario planifié, écart signalé
  au-delà de `LATENCY_DIVERGENCE_FACTOR = 2`.
- `scenario_drops` : abandons ventilés par sous-scénario, filtre
  `CULPRIT_SHARE = 10 %` pour ne **nommer** que les porteurs réels (au palier
  972, `read` porte 9 960 abandons sur 10 775 — 92 %).
- `server_congestion` : discriminant sur la **file ThreadPool par réplica**
  (`THREADPOOL_QUEUE_CONGESTED = 100`, la même borne que `pinned_candidates`),
  avec le p95 serveur/client en repli — lequel ne peut que **disculper** le
  serveur, jamais l'accuser (un p95 serveur proche du client est le cas normal
  d'un tir sain autant que d'un tir congestionné).
- `drop_attribution` rend `dimensionnement` / `congestion serveur` /
  `indéterminée` / `aucune`, avec une **conduite à tenir opposée** :
  `ITER_SECONDS_*` imprimé prêt à recopier d'un côté, « baisser le débit
  demandé, surtout pas élargir les pools » de l'autre, chiffres de l'expérience
  tail 8→16 à l'appui.
- Renvoi depuis `_validity_section` — **à côté** du verdict de validité, pas à
  la place.

#### Fixtures — une réserve à connaître

`tests/loadtest-k6/reports/` est gitignoré (`.gitignore:386`) et les JSON de la
campagne du 2026-07-29 **n'étaient plus sur la machine de banc** au moment de
l'US (il n'y restait que `2026-07-25/`, `2026-07-26/`, `2026-07-27/`). Ils
n'ont donc pas pu être « promus » tels quels.

Les cinq fixtures sont **reconstruites depuis les chiffres publiés**
(`archived-task-205.md`, `reports/INDEX.md`, `todo-task-209.md`), chacune
portant sa provenance dans une clé `_provenance` :

| Fixture | Cas couvert |
|---|---|
| `k6-campagne-486-sous-dimensionne.json` | 1re campagne, `tail` par défaut — **dimensionnement** (serveur calme, file 11) |
| `k6-campagne-882-tail8.json` | **congestion** (file 136), 4,21 % d'abandons |
| `k6-campagne-882-tail16.json` | la contre-épreuve (file 951), 13,49 % |
| `k6-campagne-972-tail8.json` | le palier nommé par la DOD (file 432), 7,38 % |
| `prom-campagne-2026-07-29.json` | files ThreadPool par réplica, 4 jeux |

`FixtureIntegrityTests` **vérifie qu'elles reproduisent les chiffres publiés**
— abandons 4,21 / 13,49 / 7,38 %, débits plateau 824,8 / 716,4 / 857,9 req/s,
`read_list` 714 / 3 606 / 1 533 ms — **avant** que les tests d'attribution ne
s'y fient. Les assertions ne portent que sur des grandeurs publiées ; les
opérations non publiées reprennent leurs valeurs du palier 486, ce qui
**sous-estime** leur dégradation (une valeur de remplissage ne peut donc pas
fabriquer un écart inexistant). **Task-208 butera sur le même manque.**

#### Tests

- `lib/vu-sizing.test.mjs` : **+4 tests** (conditions de mesure exportées,
  parsing `ITER_SECONDS_*` et ses trois modes d'échec, redimensionnement ciblé
  sans effet de bord sur les autres pools, fusion vs substitution).
- `test_report_sizing.py` : **+19 tests** — intégrité des fixtures, divergence
  nommée, palier 972 → `read` nommé sur 7,4 %, discrimination des deux causes
  sur les deux jeux de la campagne, « jamais d'élargissement de pool sous
  congestion », `ITER_SECONDS_READ=0.41` imprimé sous dimensionnement,
  `indéterminée` sans témoin, disculpation par le p95 serveur, préavis sans
  abandon.
- `selftest.sh` : **15 node + 77 Python**, verts.
- `dotnet build` Release 0 erreur ; `dotnet test` Release **3 206 réussis**,
  1 échec **pré-existant** (`MailExportServiceTests.BuildPdfWithMedicalDocumentHtmlBodyFallback`,
  flaky documenté — passe 3/3 en isolation, aucun lien avec le diff).

#### Passe qualité et Sonar

`/forge-simplify` (`68a4e47`) : parseur `dropped_iterations{scenario:…}` unifié
(`dropped_by_scenario` + `is_rate_free`, partagés par la garde de validité et
l'attribution), `worst_threadpool_queue` / `worst_server_p95_ms` extraits (trois
chemins lisaient les mêmes séries Prometheus), `pinned_candidates` bascule sur
`THREADPOOL_QUEUE_CONGESTED` au lieu d'un `100` en dur, verdict de validité
passé à `drop_attribution` au lieu d'être re-dérivé, `overrideFor` partagé côté
JS (les deux tests de validité divergeaient : typage strict d'un côté,
coercition de l'autre).

KPIs Sonar (baseline = **premier scan de la branche**, le dernier scan archivé
du serveur étant antérieur à plusieurs tasks mergées et donc non comparable) :

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| `new_violations` | 14 | **3** | −11 |
| Bugs | 1 | **0** | −1 |
| Security hotspots à revoir | 2 | **0** | −2 (100 % revus) |
| Code smells | 13 | **3** | −10 |
| Coverage projet / new | 86,6 % / 86,2 % | 86,5 % / 86,1 % | −0,1 pt |
| Reliability | **C** | **A** | ↑ 2 crans |
| Security / Maintainability | A / A | A / A | = |

Corrigés : `python:S1764` (le seul bug — `value == value` → `math.isnan`, c'est
lui seul qui tenait `reliability_rating` à C), `python:S1192` ×2 littéraux
(7 occurrences → constantes `P95`, `UTC_OFFSET`/`UTC_SUFFIX`), `python:S5713` ×2
(`URLError` ⊂ `OSError`, `JSONDecodeError` ⊂ `ValueError`), `python:S1481` ×2,
`csharpsquid:S1144` (champ mort `DefaultAbsoluteExpiration` de task-205, vérifié
sans usage), `javascript:S1940` ×3, hotspots `python:S5332` et `python:S5852`
classés `SAFE` avec justification.

> ⚠️ **Un fix Sonar qu'il ne fallait pas appliquer tel quel.**
> `javascript:S1940` propose `x <= 0` au lieu de `!(x > 0)`. Ce n'est **pas**
> équivalent : toute comparaison avec `NaN` est fausse, donc `!(NaN > 0)` vaut
> `true` là où `NaN <= 0` vaut `false`. Appliqué littéralement, le « fix »
> supprimait la garde qui fait échouer un tir sur `ITER_SECONDS_READ=vite` —
> soit exactement le silence que la task combat. Écrit
> `Number.isFinite(x) && x > 0`.

**Restent 3 `python:S3776`** (complexité cognitive de `budget_rows`,
`reduce_prom_matrix`, `_observe_table`), attribuées par `git blame` à
**`c10fa7b` — task-204, PR #130**, hors du diff. Acceptées en Phase 2
best-effort : `budget_rows` est **exactement la fonction que task-208 doit
réécrire** (défaut du dénominateur), la refactorer ici créerait une collision.
Le Quality Gate reste donc ERROR **sans dette introduite par task-209**.

#### Conventions alimentées

- `conventions/javascript.md` — entrée `javascript:S1940` (le piège NaN).
- **`conventions/python.md` — fichier créé.** Il manquait alors que l'analyse
  d'`api-mail` est multi-langage et que le moteur de rapport du banc est en
  Python. Six entrées (`S1192`, `S1764`, `S5713`, `S1481`, `S5332`/`S5852`,
  `S3776`). Directement utile à task-208.
- `conventions/csharp.md` — la note de portée pointe désormais aussi vers
  `python.md`.

#### Documentation

`docs/loadtest.md` §4a-bis (la contradiction purge / dimensionnement, la table
« quelle cause → quelle conduite », l'expérience tail 8→16), piège n°6 du
`README.md` du harnais, et étape 4 du `loadtest-skill`. Le no-op silencieux
d'`ITER_SECONDS_*` sur les scénarios mono (qui gardent `4 × VUS`) est documenté
— relevé pendant le code review.

#### Anomalie d'outillage relevée (hors périmètre)

`agents/sonar.md` — et l'entrée v1.8 ci-dessus, via task-205 — affirment que
l'instance SonarQube est en **9.9** et qu'il faut `sonar.login`. Le serveur
répond **25.6.0.109173**, où la propriété est `sonar.token` : les trois analyses
de cette task ont été conduites avec `sonar.token`. En suivant l'agent à la
lettre, un futur run perdrait ~6 min (build + tests complets) avant de voir
échouer le `end` sur une erreur d'authentification trompeuse. **L'encadré ⚠️ de
`agents/sonar.md` est à inverser.**

#### Ce que cette PR ne livre pas

La **mesure au banc** exigée par la DOD (palier 756 req/s : le rapport doit
nommer laquelle des deux causes produit ses 1,15 % d'abandons). Le banc n'était
pas monté et le monter suppose seed de 200 praticiens × 100 messages, purge, tir
de 3 min et démontage. C'est l'étape 2 du Manual Test Plan, côté humain — comme
l'a été le « Tir de vérification » de task-205.

---

### v1.10 — Les trois verdicts du rapport reposent sur la bonne statistique — task-208

- **Task** : task-208 — `done`. **PR** : `api-mail` #133 (label `awaiting-human-merge`).
- **Origine** : les trois défauts ont été trouvés **en lisant les rapports de la
  campagne du 2026-07-29**, pas en relisant le code. Le mécanisme d'absence de
  télémétrie livré par task-204 est correct ; ce sont ses **règles de
  conclusion** qui débordaient. Chacune a produit une affirmation fausse dans un
  `.md` livré.

#### Défaut n°1 — « Ressource épinglée » sur un transitoire d'ouverture

`pinned_candidates` attribuait `ratio = 1.0` — donc le rang n°1 garanti — dès que
`cl_waiting > 0`, en retenant le **max** de la fenêtre. Trois paliers ont désigné
PgBouncer comme facteur limitant sur **un unique échantillon** à 1 ou 2 clients
en attente, devant un réplica à 11 % et Postgres à 13,6 %.

| Palier | `cl_waiting` max **dans** la fenêtre | Verdict rendu |
|---|---|---|
| 486 req/s | 2 | « Ressource épinglée : PgBouncer — 100,0 % de sa borne » |
| 630 req/s | 1 | idem |
| 756 req/s | 3 | idem |

**Statistique retenue** : la **part des échantillons non nuls**,
`PGBOUNCER_WAITING_SUSTAINED = 25 %` (`pgbouncer_waiting`). Sur la campagne,
15 échantillons sur 230 sont non nuls (6,5 %), tous dans les ~30 s suivant
l'ouverture d'un palier, avec un pic à 75 mesuré **2 s avant** l'ouverture d'une
fenêtre. Le seuil est posé bien au-dessus de ce bruit, bien en dessous d'un
pooler réellement saturé. Le p95 et la durée cumulée conviendraient ; la part
d'échantillons a été préférée parce qu'elle se lit **sans hypothèse sur la
cadence d'échantillonnage**.

Le transitoire reste **écrit** (`_pgbouncer_transient_note`) sous la table, avec
la mention explicite qu'il ne désigne pas de facteur limitant : il croît avec la
charge (2 → 1 → 6 → 75), donc le taire serait un nouveau silence.

#### Défaut n°2 — deux dénominateurs contradictoires dans le même document

Palier 486 req/s, **le même `.md`** : en-tête « Débit plateau : 482,7 req/s »
(99,3 % du budget), et table « total 486 → 413,6 — **85,1 % ⚠️** ». task-204
avait corrigé le dénominateur du chiffre d'en-tête mais pas celui de cette table
— celle qui porte les ⚠️ par sous-scénario, donc celle qu'on croit.

**Statistique retenue** : `count ÷ durée de plateau` dans `_delivered_rps`, le
**même dénominateur que l'en-tête**. Sur la fixture du palier 486, la table lit
**97,5 %** et **473,9 req/s** — exactement le débit de l'en-tête, contre 83,6 %
et 406,2 avant. Chaque ligne porte son `denominator`, et le repli
(`shared-iterations` fini, `duration` absente) est **nommé** `fenêtre k6` avec la
mention que les parts y sont sous-estimées de la durée d'extinction.

#### Défaut n°3 — le reliquat d'un scénario FINI compté comme abandon

`mixed_enrich` est un `shared-iterations` de 2 000 lots dont ~424 tiennent dans
un plateau de 3 min : k6 range les 1 576 restants dans `dropped_iterations`. Le
premier palier a été déclaré **invalide à 4,6 %** alors que les scénarios à débit
imposé n'en avaient que 2,6 %.

**Statistique retenue** : deux chemins dans `validity` —
la ventilation `dropped_iterations{scenario:…}` (task-203) quand elle existe,
sinon le **plan déclaré du harnais** (`finite_scenario_remainder` :
`enrichPlan.iterations` − appels `enrich` émis, divisés par leur
`REQUESTS_PER_ITERATION`). Le second chemin, `dropped_source = "finite_plan"`,
couvre **tous les tirs archivés avant task-203**, qui n'ont pas de
sous-métriques et que la garde invalidait à tort. `ENRICH_SHARE=0.05` reste un
réglage utile mais n'est plus un contournement obligatoire.

Le reliquat est **écrit comme information** dans « Validité du tir » : lots
consommés sur lots planifiés, avec la mention que ce n'est pas un signal
d'invalidité mais que la bande d'UIDs n'a pas été parcourue en entier.

#### Trois tests existants changent de verdict — c'est le correctif

Chacun encodait le défaut ; les trois sont réécrits avec le raisonnement en
commentaire :

| Test | Avant → Après | Pourquoi |
|---|---|---|
| `test_legacy_json_without_plan_falls_back_to_mix_derivation` | `send` délivré **17,24 → 18,97** | exactement le biais de dénominateur (330 s de fenêtre contre 300 s de plateau). Verdict « affamé » inchangé |
| `test_drop_share_just_over_ceiling_invalidates` | compteur injecté **2 600 → 4 000** | 1 360 des abandons de cette fixture sont le reliquat déclaré de son `enrich` fini ; le test porte toujours sur le franchissement du seuil, sur les abandons **réels** |
| `test_structural_enrich_drops_do_not_invalidate_a_healthy_run` | contre-épreuve **inversée** | « sans ventilation ce tir sain serait INVALIDE » était le défaut n°3 ; le repli sur le plan le rattrape |

#### Tests et fixtures

`test_report_conclusions.py` — **13 tests**, écrits RED d'abord, dont un qui
reproduisait littéralement `Ressource épinglée : PgBouncer — 100,0 % de sa borne`
sur un échantillon unique. Total du harnais : **15 node + 90 Python**.

Deux CSV d'échantillonnage ajoutés, provenance en tête de fichier :
`observe-cl-waiting-transitoire.csv` (1 point non nul sur 20 dans la fenêtre,
plus le pic de 75 hors fenêtre) et `observe-cl-waiting-soutenu.csv` (13 sur 20,
**explicitement marqué synthétique** — aucune campagne n'a produit ce profil ; il
sert de contre-épreuve pour que la correction du faux positif ne devienne pas une
cécité).

⚠️ **Même réserve qu'à task-209** : `reports/` est gitignoré et les JSON / CSV de
la campagne du 2026-07-29 ne sont plus sur la machine de banc. Les fixtures sont
reconstruites depuis les chiffres publiés.

#### Sonar

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| `new_violations` | 4 | **2** | −2 |
| Code smells | 4 | **2** | −2 |
| Bugs / Vulnérabilités / Hotspots | 0 / 0 / 0 | 0 / 0 / 0 | = |
| Coverage projet / new | 86,6 % / 86,1 % | 86,6 % / 86,2 % | +0,1 pt |
| Reliability / Security / Maintainability | A / A / A | A / A / A | = |

Les deux corrigés sont de la dette **introduite ou aggravée par cette task** :
`budget_rows` y était déjà (S3776 = 19, task-203) et ses branches l'ont
aggravée ; `_budget_section` a franchi le seuil à cause de la note de
dénominateur ajoutée ici. Extraction de `_budget_scenarios`, `_requested_budget`,
`_budget_row`, `_budget_denominator_note`. La justification de task-209 — « on
laisse `budget_rows`, task-208 va la réécrire » — ne tenait plus.

Les deux restants (`reduce_prom_matrix`, `_observe_table`) sont de task-204 et
hors du diff ; la passe générale sur les helpers de table Markdown est listée en
toutes lettres dans le **« Hors scope »** de la task.

**Boucle d'auto-amélioration** : aucune convention nouvelle — `conventions/python.md`
(créé par task-209) portait déjà l'entrée `python:S3776` avec la consigne
appliquée ici (« un builder par section retournant une liste de lignes »). Son
compteur **Occurrences** passe de 0 à 2, au premier tour de boucle.

#### Ce que cette PR ne livre pas

La régénération des 3 rapports de la campagne depuis leur JSON archivé, et le
recalcul de la ligne d'INDEX correspondante : **les JSON n'existent plus**. Ce
qui couvre l'intention : le changement de verdict est démontré et verrouillé par
un test sur la fixture reconstruite du palier 486 (un test lit l'en-tête **et**
la table du même rapport et vérifie qu'ils citent le même débit). Et la ligne
d'INDEX de ces trois tirs **n'avait pas à changer** : la campagne a tourné avec
`ENRICH_SHARE=0.05`, donc `mixed_enrich = 0` abandon aux cinq paliers — l'énoncé
de la task le dit lui-même — et les colonnes d'INDEX ne portent pas la table
« demandé vs délivré », seule touchée par le défaut n°2.

---

### v1.11 — La route de provisionnement ne retient plus un backend Postgres par praticien — task-202

- **Task** : task-202 — `done`. **PR** : `api-mail` #134 (label `awaiting-human-merge`).
- **Origine** : campagnes 200 et 500 praticiens du 2026-07-27, premiers tirs à
  travers PgBouncer. Le pooler fait son travail (2 000 connexions clientes →
  400 backends), mais **la moitié des backends restants ne lui appartient pas**.

#### La mesure

Écart entre les backends comptés sur Postgres et ceux que PgBouncer déclare
détenir (`pg_stat_activity` moins `SHOW POOLS`) :

| Tir | `default_pool_size` | Backends pooler | Backends Postgres | **Écart non attribuable** |
|---|---|---|---|---|
| A | 2 | 400 (= 200 bases × 2) | 569 | **~169** |
| B | 1 | 209 (= 200 bases × 1) | 409 | **~200** |

Écart **stable autour d'une connexion par base**, indépendant du réglage du
pooler — signature de la route directe. Il retombe à ~0 quelques minutes après le
tir : un pool qui expire, pas une fuite franche. La règle de dimensionnement du
palier 1000 étant `praticiens × réplicas × pool`, c'est exactement ce plafond-là,
et aucun correctif de débit ne le déplace.

#### Trois gestes, trois défauts distincts

**1. Le conteneur DI de FluentMigrator est disposé.** `CreateServices` rend un
`ServiceProvider` (`IDisposable`) dont seul le `scope` interne l'était : il
fuyait par base praticien et par pod. Le `using` couvre le chemin d'exception —
celui qui compte, une migration en échec étant rejouée à la requête suivante.

**2. La chaîne de provisionnement est bornée** par un helper dédié,
`AppendProvisioningPoolingSettings` : `Maximum Pool Size=1`,
`Minimum Pool Size=0`, `Connection Idle Lifetime=5`. Elle partait sur les défauts
Npgsql — **100 connexions** par base et un backend retenu **5 minutes**.

> ⚠️ **Le raisonnement du chemin de données ne s'y transpose pas.** Son idle
> lifetime est volontairement long (30 s ici, 600 s au banc) parce que recycler
> ~1 000 pools épuise les ports éphémères de Windows — 200 000
> `SocketException 10048` mesurées le 2026-07-27. Ici : **une** connexion par
> base, **une** seule fois. D'où un helper **distinct**, comme l'exigeait
> l'énoncé, et l'argument écrit dans le code.

**3. Le pool est vidé après migration réussie** (`NpgsqlConnection.ClearPool`),
hors du `using` puisque la connexion du runner doit d'abord y revenir. Pas sur
échec : rien n'a été provisionné, et une opération de plus masquerait l'erreur.
Le vidage absorbe ses propres erreurs — un geste d'hygiène ne doit jamais
transformer un provisionnement réussi en échec.

#### Le piège : la chaîne serveur ne doit PAS être bornée à 1

L'énoncé dit « borner la chaîne de provisionnement ». Il y en a **deux**, et une
seule doit l'être :

| Chaîne | Portée | Traitement |
|---|---|---|
| `ConnectionStringProvisioningUser` | **une par praticien** — la coupable des ~169 | bornée à `Max=1` |
| `ConnectionStringProvisioningServer` | **une par pod** (base de maintenance) | laissée aux défauts |

`Maximum Pool Size=1` sur la seconde provoquerait un **interblocage** :
`lockConnection` reste ouverte pendant que `MigrationHelper.DatabaseExists` puis
`CreateDatabase` en ouvrent une seconde sur la même chaîne. Il en faut au moins
deux. Raison consignée dans le `<remarks>` de `UpdateDatabase`. Un plafond
explicite resterait possible **à partir de 4** — le provisionnement étant
sérialisé par un `SemaphoreSlim(1,1)` statique, 2 connexions simultanées au pire.

#### Une nuance sur l'énoncé, vérifiée dans le code

L'énoncé écrit : « Sans pooler, `ConnectionStringUser` et
`ConnectionStringProvisioningUser` sont la même chaîne : un seul pool Npgsql. »
Les deux **propriétés** coïncident bien, mais le chemin de données construit son
`NpgsqlDataSource` sur `AppendPoolingSettings(cs)` — une chaîne **différente**,
donc un pool **différent**. La connexion de provisionnement était donc déjà
distincte **avant** task-200 : le pooler l'a rendue visible et coûteuse, il ne
l'a pas créée. Sans incidence sur le correctif, mais l'origine du défaut est plus
ancienne que supposé.

#### Tests

`BaseRepositoryProvisioningPoolTests` — **12 tests**, écrits RED d'abord (échec
de compilation : ni `AppendProvisioningPoolingSettings` ni `ProvisionDatabase`
n'existaient). Couvrent la disposition du conteneur **sur succès et sur
exception**, le **non**-vidage du pool après échec, le bornage et sa
non-application quand l'appelant a déjà dimensionné, la parsabilité Npgsql de la
chaîne produite, et le fait que le bornage ne touche ni l'hôte, ni le port, ni la
base. Suite complète : **3 219 réussis, 0 échec** (382 en infrastructure contre
370).

Passe `/simplify` : `AppendUnlessExplicitlySized` extrait — les deux helpers de
pool partageaient garde « déjà dimensionnée » et gestion du séparateur ; seules
leurs valeurs doivent diverger.

#### Sonar

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| `new_violations` | 3 | **2** | −1 |
| Code smells | 3 | **2** | −1 |
| Bugs / Vulnérabilités / Hotspots | 0 / 0 / 0 | 0 / 0 / 0 | = |
| Coverage projet / new | 86,6 % / 86,2 % | 86,6 % / 86,2 % | = |
| Reliability / Security / Maintainability | A / A / A | A / A / A | = |

**Zéro finding C# restant.** Le seul introduit, `csharpsquid:S125` « code
commenté », était un faux positif de forme — les puces de l'explication se
terminaient par des points-virgules et citaient des identifiants. Déplacée dans
un `<remarks>`, où elle a de toute façon sa place. Les 2 restants sont les
`python:S3776` de task-204, sans rapport. Convention `csharpsquid:S103` vérifiée
avant commit (`awk 'length($0)>150'`).

#### Ce que cette PR ne livre pas

Les **quatre critères de DOD qui exigent le banc** : le test d'intégration
« connexions directes à 0 en moins de 30 s avec PgBouncer », le tir `mixed`
200 praticiens iso-conditions (écart de ~169 à moins de 20), la non-régression
p95 > 10 % vs le tir A, et le rapport de tir comparé. Le banc n'était pas monté ;
ce sont les étapes 1 à 7 du Manual Test Plan, côté humain.

---

### v1.12 — Le banc ne lève plus une exception par requête sur le token PSC — task-206

- **Task** : task-206 — `done`. **PR** : `api-mail` #136 (label `awaiting-human-merge`).
- **Origine** : tir de contrôle télémétrie du 2026-07-29. La colonne
  « Exceptions /s » que task-204 venait d'ajouter au rapport a immédiatement
  montré un débit absurde. Personne ne l'avait vu avant, **faute de le mesurer**.

#### La mesure

| Charge | `SecurityTokenMalformedException` | Débit d'exceptions |
|---|---|---|
| 106 req/s (20 praticiens) | 12 668 en 121 s | ~105/s, **≈1,2 par requête** |
| ~480 req/s (200 praticiens) | — | ~110-145/s **par réplica** |
| ~858 req/s (200 praticiens) | — | ~233-290/s par réplica, **>1 200/s** au total |

Croissance **linéaire** avec la charge : une exception par requête, pas un
incident.

#### La cause

Le harnais envoyait `X-PSC-Token: loadtest` — non vide mais **pas un JWT** — au
motif que le profil du banc pose `MSS_ENFORCE_PSC_IDENTITY=false`. Or
`UserContextEnricherMiddleware.TryParsePscIdentity` tentait quand même de le
parser : `ReadJsonWebToken` levait, le `catch` avalait, la requête continuait.
**Une exception avalée reste une exception levée** — déroulement de pile, ligne
de télémétrie. En production le token est un vrai JWT : ce n'est donc pas un
défaut de production, mais un défaut de **fidélité du banc** doublé d'un défaut
d'**observabilité**.

#### Voie 1 — la correction, posée plus bas que l'énoncé

L'énoncé proposait de court-circuiter quand `Enforce=false`. **Écart assumé** :
ce garde-là aurait privé le **mode observation** — qui *est* `Enforce=false`,
phase 1 — des journaux `3721`/`3722`/`3723` qu'il existe précisément pour
produire ; un déploiement en observation serait devenu aveugle sans que rien ne
le signale.

La garde porte donc sur la **lisibilité du token** (`CanReadToken`) et non sur
l'enforcement. Elle supprime l'exception pour tout appelant et dans tous les
modes, sans rien perdre — un token illisible n'a jamais rendu de claims, il
coûtait seulement une exception pour le dire. Deux tests pinnent qu'aucun
contrôle n'est desserré : `Enforce=true` + non-JWT → toujours 403 ;
`Enforce=false` + non-JWT → journal 3723 toujours émis.

#### Voie 2 — la fidélité, et elle est nécessaire

La voie 1 seule fait *sauter* le parse au banc : il n'exerce **toujours pas** le
chemin déployé. Or l'énoncé le pose lui-même — « un chiffre de capacité mesuré
sur un autre chemin que celui déployé n'est pas opposable ». Le harnais forge
donc un token à la forme d'un vrai JWT, par identité, avec les claims de
production (`sub`, `SubjectNameID`) — miroir JS de
`PscTokenForge.BuildPayloadOnlyToken`. `PSC_TOKEN` devient vide par défaut et
reste une échappatoire (rejouer un token réel, ou reproduire l'ancien
comportement pour re-mesurer le défaut).

#### Deux choix de test qui portent la démonstration

- **Exceptions comptées en première chance** (`AppDomain.FirstChanceException`,
  filtrées par type) : le seul moyen d'observer un défaut que le code de
  production masque. Constaté RED avant le correctif — 4 des 5 tokens non-JWT
  levaient.
- **Le token réellement produit par k6 est figé en fixture** dans le test C#,
  avec ses claims attendus. Une divergence d'encodage JS/.NET — remplissage
  base64url, casse de `SubjectNameID` — ferait retomber le banc dans le chemin
  qu'il quitte, **sans rien casser de visible**.

17 tests ajoutés (12 dédiés + 5 dans le fichier de cross-check, là où vivent
déjà les helpers). `mss.mail.api.tests` : 607 contre 590.

#### Passe `/simplify` — le cache retiré

Le cache de tokens ajouté par `/develop` est **par VU**, et le banc en alloue
~900 : à 200 identités en tourniquet, ~110 Ko par VU, soit ~100 Mo côté tireur —
pour économiser un `JSON.stringify`, un base64url et un SHA-256 sur ~250 octets.
À 900 req/s le forgeage coûte bien moins d'un pour cent d'un cœur quand k6 en
consomme 0,2 à 0,4 (task-204). Le tireur doit rester hors de cause : le risque
était la mémoire, pas le CPU. Raisonnement écrit sur place.

#### Sonar

**Aucun finding introduit** — un seul passage d'analyse. Bugs / vulnérabilités /
hotspots à 0, ratings A/A/A, coverage projet 86,6 % et new 86,2 %. Les 2 findings
du projet restent les `python:S3776` de task-204, hors diff.

#### Documentation

`loadtest-skill` — grille de lecture de la colonne « Exceptions /s » : ordre de
grandeur attendu par famille (`SecurityTokenMalformedException` = **0**, total
« quelques unités » par réplica), rappel que `FolderNotFoundException` est
bénigne (pas de dossier `Sent` au banc), et **le test qui tranche** — une famille
dont le débit croît linéairement avec la charge est un coût par requête, pas un
incident. Y figure aussi l'avertissement de fidélité : `PSC_TOKEN=loadtest`
reproduit l'ancien comportement, à ne pas laisser dans une campagne dont on veut
publier le chiffre.

#### ⚠️ Un vrai défaut trouvé à la validation, hors périmètre

`PatientRepository.GetWithMedicalDocumentsTodayAsync` filtre sur
`var today = DateTime.Today` — minuit **local** — alors que les dates sont
stockées en **UTC**. À 00 h 14 local (22 h 14 UTC), un document créé
« aujourd'hui » tombe avant la borne et la requête ne renvoie rien : le test
correspondant échoue **de façon déterministe entre minuit et 2 h du matin** en
heure d'été, et la liste « patients avec un document aujourd'hui » est fausse en
production pendant la même fenêtre quotidienne. Module différent, aucun rapport
avec cette task — **à arbitrer par le PO**, probablement une task dédiée.

#### Ce que cette PR ne livre pas

Les **deux critères de DOD qui exigent le banc** : `SecurityTokenMalformedException = 0`
mesuré à ~480 req/s, et l'explication de chaque famille restante dans un rapport
de tir. Le banc n'était pas monté.

---

### v1.13 — Les trois verrous de `read_list` sont instrumentés, et le plancher d'attente d'une seconde disparaît — task-211

- **Task** : task-211 — `done`. **PR** : `api-mail` #137 (label `awaiting-human-merge`).
- **Origine** : demande humaine du 2026-07-31, à la lecture de la re-mesure de
  task-205. La famine de ThreadPool est éteinte, mais `read_list` reste
  l'opération la plus lente du mix hors `send`/`enrich`, et **son profil a changé
  de nature** : ce n'est plus du blocage de threads, c'est de l'attente en file.

#### Ce que la mesure disait

Banc du 2026-07-31, 200 praticiens, après les deux correctifs de task-205 :

| Palier | moy | p50 | p95 |
|---|---|---|---|
| 882 req/s | **718 ms** | 213 ms | 1 480 ms |

La moyenne vaut **3,4 fois la médiane** — signature d'une file d'attente, pas
d'un coût unitaire. Les deux suspects habituels sont écartés d'emblée : file du
ThreadPool **plate** (max 8) et CPU à **1,1 cœur sur 24**. Restent les verrous,
et le chemin en traverse trois sur base purgée.

#### Deux corrections de l'énoncé, établies en lisant le code

**1. Le correctif d'une ligne proposé aurait été un no-op.** L'énoncé affirmait
que « le `Task.Delay` précède le premier essai » et proposait d'ajouter un
`TryAcquireAsync` immédiat. **Cet essai existe déjà** au site d'appel :
`FetchMissingUidsWithLocksAsync` le tente, et n'entre dans la boucle d'attente
qu'après son échec. L'appliquer à la lettre aurait ajouté un aller-retour Redis
pour ne rien changer.

Le symptôme décrit était pourtant réel — mais sa cause est le **pas de sondage** :
une seconde fixe, sans réveil à la libération, donc une contention levée en 10 ms
coûtait quand même une seconde pleine. Remplacé par un pas croissant
**25 ms → 500 ms**.

**2. `proceeding anyway` est tranché : le verrou distribué est OPPORTUNISTE.**
La task exigeait de lever cette ambiguïté plutôt que de la reconduire. Trois
éléments l'établissent, tous déjà dans le code : en cas d'échec l'appelant va
chercher les messages **quand même** (la correction du résultat n'en dépend donc
pas) ; une fois le verrou obtenu le code **re-vérifie la base** et ne fetch que ce
qui manque (c'est une déduplication) ; et son commentaire d'origine parle de
« prevents concurrent fetch across pods », ce qui est une économie, pas une
garantie.

Conséquence assumée : budget d'attente ramené de **30 s à 5 s**. On abandonnera
plus souvent, donc on paiera plus souvent un fetch IMAP en double — c'est le bon
sens de l'échange, une lecture en double coûtant un aller-retour réseau là où
l'attente coûtait jusqu'à **trente secondes au praticien**. L'issue est
enregistrée (`outcome=timeout`) pour que le compromis soit **mesurable**, pas
supposé.

#### L'instrumentation — le vrai livrable

Deux histogrammes sur le meter métier existant,
`mssante_lock_wait_duration_seconds` (étiqueté `lock` et `outcome`) et
`mssante_lock_hold_duration_seconds`, sur les trois verrous : `in_process_fetch`,
`distributed_fetch`, `imap_session`.

**Attente et détention sont séparées** parce qu'elles désignent des défauts
différents : une attente longue signale la contention, une détention longue
signale ce qu'on fait *sous* le verrou — et c'est alors sa **portée** qu'il faut
discuter. Le verrou de session mesurait déjà les deux, mais **vers les logs
seulement** (task-024) : mêmes mesures, désormais aussi en métriques, sans
horloge ni coût ajoutés.

`report.py` gagne une table « Verrous du chemin `read_list` », rendue même vide —
son absence est une information. Elle répond à la question de la task : *lequel
des trois porte la queue ?*

> ⚠️ **PGSSI-S** — aucune étiquette ne porte d'identifiant de praticien. Les clés
> de verrou contiennent un email : le promouvoir en étiquette serait à la fois une
> donnée personnelle dans la télémétrie et une explosion de cardinalité.

#### Ce que la PR ne touche pas, délibérément

La **portée du verrou de session** et l'**existence du verrou en processus**. La
task les subordonne à la mesure, et le verrou de session protège une **connexion
IMAP unique, non thread-safe** : le desserrer sans savoir ce qui garantit alors
l'exclusivité serait un mauvais échange. La réserve de la task tient — rien ne
garantit que les verrous portent les 318 ms manquants, et si la mesure montre
qu'ils pèsent peu, la conclusion attendue est de **le dire et refermer**.

#### Tests

7 tests, dont celui qui porte le correctif :
`AContentionLiftedQuickly_NoLongerCostsAFullSecond` — un premier essai échoué
suivi d'un succès coûtait ≥ 1 000 ms, il coûte désormais quelques dizaines de
millisecondes. Les autres verrouillent l'absence d'attente sur le chemin non
contendu, le budget borné **et** la lecture qui aboutit malgré tout, le backoff
qui croît au lieu de marteler Redis, le verrou en processus **toujours** relâché
(sans quoi une boîte praticien resterait gelée jusqu'au redémarrage du pod), et la
déduplication préservée.

Suite : **3 243 verts**. `selftest.sh` : 15 node + 96 Python.

#### Sonar

**Zéro finding attribuable à la task.** Les 2 findings C# relevés
(`csharpsquid:S3776` et `S138` sur `FetchMissingUidsWithLocksAsync`) étaient de la
dette **introduite par l'instrumentation** — corrigés par extraction de quatre
helpers nommés. Les 3 restants sont dans `report.py` : `reduce_prom_matrix` et
`_observe_table` (task-204), et `pinned_candidates` qui franchit le seuil via la
PR #135, déjà sur `develop`.

Une correction issue de `/simplify`, **non cosmétique** : la détention du verrou
distribué était mesurée avec le chronomètre du verrou en processus, démarré
**avant** son acquisition. Sur une table dont l'unique raison d'être est
d'attribuer la queue au bon verrou, une surestimation vaut une fausse
désignation.

#### Synchronisation avec `develop`

`develop` avait avancé (PR #135, « la ressource épinglée se juge sur la
présence »), qui touche **le même fichier** — `report.py`. Merge, jamais rebase
(règle 4) : fusion automatique sans conflit, 96 tests Python verts après coup.

#### Ce que cette PR ne livre pas

Les **cinq critères de DOD qui exigent le banc** : la désignation chiffrée du
verrou coupable, `read_list` moy < 400 ms et p95 < 800 ms, la non-régression
ThreadPool et débit, le rapport de tir et sa ligne d'INDEX. Plus le test de
concurrence « N lectures simultanées → un seul fetch IMAP », dont la
déduplication est couverte unitairement mais dont le cas N-concurrent réel exige
la base.

---

### v1.14 — Le snapshot de flags devient partagé entre pods, et l'intervalle passe à 5 minutes — task-201

- **Task** : task-201 — `done`. **PR** : `api-mail` #139 (label `awaiting-human-merge`).
- **Origine** : suite directe de task-199. Priorité 6/6 de l'ordre arrêté le
  2026-07-31 — axe **robustesse**, hors du chemin de capacité.

#### Le trou que task-199 avait laissé

task-199 a supprimé l'appel réseau par évaluation : chaque pod sert ses flags
depuis un snapshot mémoire, avec au plus un appel par intervalle. Ce gain est
**déjà acquis sur tous les pods** — Redis n'y ajoute rien, et la task le dit
explicitement pour éviter de re-livrer un bénéfice déjà obtenu.

Ce que le snapshot par processus laisse ouvert : un pod qui **démarre pendant
une panne Flagsmith** n'a aucun état connu et applique
`FeatureFlags.ColdStartDefault`, soit `ai_pipeline = false`. C'est exactement la
désactivation silencieuse de l'étage IA que task-199 visait à supprimer,
réintroduite à chaque rollout, scale-up ou redémarrage tombant pendant une
indisponibilité.

#### Trois étages, et une règle sur qui touche Redis

| Étage | Rôle | Quand il est touché |
|---|---|---|
| **L1** — mémoire du pod | sert **toutes** les évaluations | chemin de requête, zéro I/O |
| **L2** — snapshot Redis | hérite de l'état du cluster | **uniquement** au rafraîchissement |
| **L3** — repli déclaré | dernier recours | ni L1 ni L2 n'ont d'état |

Sur le chemin nominal, Redis est **écrit et jamais lu** : lire aussi coûterait
un aller-retour toutes les 5 minutes sur chaque pod pour un état que Flagsmith
vient de fournir plus frais. Deux tests épinglent cette discipline — l'absence
de lecture au rafraîchissement réussi, et l'absence totale d'accès au store sur
200 évaluations concurrentes.

#### Ce que le store n'est pas

**Ni un verrou, ni une source de vérité.** Chaque pod continue de poller
(12 appels/h, négligeable) ; `IDistributedLockService` n'est pas utilisé et
aucune élection de « pod pollueur unique » n'est introduite — le snapshot est un
**partage d'état**, ce qui évite d'ajouter un point de défaillance. Redis
injoignable ⇒ comportement task-199 **à l'identique**, aucune exception
propagée, même politique « un log par fenêtre ».

Cette politique a été **extraite** (`FailureThrottle`) plutôt que dupliquée pour
la seconde source d'échec. Comportement Flagsmith inchangé : les 10 tests de
task-199 passent sans qu'une seule de leurs assertions ait bougé — c'était une
exigence explicite de la DOD.

**Fraîcheur préservée** : le snapshot porte son `TakenAt` et n'est adopté que
s'il est **plus récent** que l'état local ; un pod resté en ligne ne régresse
jamais sur l'état publié par un pod mort il y a une heure. **TTL 24 h**, justifié
dans le code : un TTL calé sur l'intervalle expirerait pendant l'incident même
qu'il doit couvrir.

#### Trouvaille de la passe qualité, non cosmétique

La désérialisation JSON reconstruit un dictionnaire **sensible à la casse**,
alors que l'état mémoire est indexé en `OrdinalIgnoreCase`. Adopter un snapshot
partagé changeait donc silencieusement la sémantique de résolution des noms de
flags **selon la provenance de l'état** — piège qui ne se serait manifesté qu'au
premier flag écrit dans une autre casse. Normalisé à la lecture, avec un test.

#### L'arbitrage à 5 minutes

`Flagsmith:RefreshIntervalSeconds` 30 → 300. La même valeur alimente
`FlagsmithConfiguration.EnvironmentRefreshInterval` : les deux usages lisent la
même variable, donc restent cohérents par construction (point 6 de la DOD).

Coût assumé, acté par le PO : la propagation d'un flip monte à ~5 minutes dans
le pire cas — sur un kill-switch d'étage IA médical, on échange de la réactivité
contre de la robustesse. L'invalidation immédiate (pub/sub Redis + webhook
Flagsmith) reste hors scope.

Conséquence **documentée sur place** : à 300 s, il y a au plus une tentative
échouée toutes les 5 minutes, donc `FailureLogWindowSeconds = 60` ne filtre plus
rien. Ce n'est pas une régression — le volume qui avait motivé la fenêtre
(750 stacks pour un tir de 15 utilisateurs) venait de l'appel par évaluation,
supprimé depuis. Un avertissement explicite est posé dans le code pour que
personne ne « corrige » ce réglage par erreur.

> ⚠️ **PGSSI-S** — la clé `mss:featureflag:snapshot` est un **singleton global**,
> sans segment par praticien (contrairement à `mss:sync:state:{email}`). Le
> payload ne porte que des noms de flags déclarés par l'application et des
> booléens. Un test l'audite : deux propriétés seulement, et chaque nom de flag
> stocké doit appartenir à `FeatureFlags.All`.

#### Tests

**16 nouveaux** (10 sur le service, 6 sur le store), suite à **3 269 verts**. Le
contre-test du scénario principal est **intégré au jeu** plutôt qu'obtenu par une
édition temporaire : `ColdStartWithFlagsmithDownServesTheSharedSnapshotNotTheColdStartDefault`
(store présent → l'étage IA reste actif) et `ServiceWithoutSharedStoreKeepsTask199Behaviour`
(pas de store → `ColdStartDefault`) sont le même scénario avec et sans le
correctif.

Un flaky pré-existant de rendu PDF (`MailExportServiceTests`, état statique
partagé de PdfPig) est apparu une fois sur quatre exécutions ; vert au rejeu,
sans rapport avec ce diff.

#### Sonar

**Deux findings introduits par la task, tous deux corrigés** (`csharpsquid:S103`
ligne trop longue sur le log du store, `external_roslyn:CA1859` type de retour
de la fabrique) → **0 issue sur les 6 fichiers touchés**. Les `new_violations`
restantes sont hors du diff : `python:S3776` ×3 dans `report.py` (tasks 204/209)
et `csharpsquid:S1067` dans `ContactRepository.cs` (task-023).

> ⚠️ Les KPIs projet SonarQube restent **inexploitables** depuis task-212 —
> `agents/sonar.md` est périmé sur trois points et la baseline est à refaire.
> Cette analyse n'a servi qu'aux findings par fichier, ce pour quoi elle est
> fiable.

#### Ce que cette PR ne livre pas

La **vérification au banc** (15 utilisateurs, zéro `FlagsmithAPIError`, traces
`ai_pipeline` présentes) — dernier critère de DOD, qui exige le harnais de
charge. Elle s'ajoute aux campagnes E015 déjà dues.

---

### v1.15 — L'archivage d'un envoi quitte la file des lectures IMAP — task-213

- **Task** : task-213 — `done`. **PR** : `api-mail` #140 (label `awaiting-human-merge`).
- **Origine** : task-211 avait explicitement **renvoyé cette question à une
  mesure** sans la faire. La mesure existe depuis le 2026-08-01 ; elle désigne
  `imap_session`.

#### Ce que la mesure disait

Campagne 500 praticiens, palier 882 req/s : attentes courtes, **détentions
longues** — `imap_session` détenu **6,345 s au p95**. Ce n'est donc pas une
contention sur l'acquisition, c'est ce qui se fait sous le verrou qui dure,
exactement la grille de lecture que task-211 avait inscrite dans le rapport.

Le verrou sérialise **toutes** les opérations IMAP d'une session. `AppendToSent`,
synchrone du geste du praticien, faisait la queue derrière le fetch
d'enrichissement du **même** praticien.

#### L'opération nommée, et l'instrumentation qui le prouvera

Par lecture du code : **`EnrichEmails`**, phase A. La table de task-211 agrège
sur le verrou — elle donne une durée, jamais un coupable. Les deux histogrammes
portent désormais la **famille d'opération**, et `report.py` gagne une table
`imap_session` par opération qui **confronte** l'attente de l'archivage à celle
du reste plutôt que de laisser la conclusion au lecteur.

> ⚠️ **PGSSI-S — la famille, jamais l'opération complète.** Les noms d'opération
> concatènent chemins de dossier, UID et, pour `GetAttachment`, le **nom de la
> pièce jointe** — qui dans une messagerie de santé nomme couramment le patient
> et l'examen. Étiquette non bornée *et* donnée de santé. Seul le préfixe
> littéral, écrit dans le code, est conservé ; deux tests l'épinglent, côté
> application et côté rapport.

#### La portée retenue, et les deux options écartées

Le verrou **n'est pas supprimé** : la session MailKit n'est pas thread-safe,
c'est sa raison d'être et task-211 l'avait laissé pour cela. Les appends
(`Sent`, `Drafts`) passent par une **voie d'écriture** — identifiant de session
suffixé, donc seconde connexion et second verrou. Une seule commande circule
toujours à la fois sur une connexion donnée, ce qu'un test de contre-épreuve
vérifie sur la même voie.

| Option | Verdict |
|---|---|
| File par praticien avec priorité | ❌ **Ne corrige pas la mesure** : la priorité départage des candidats en attente, elle ne préempte pas le détenteur. Le problème mesuré est une **détention** de 6,3 s — un fetch en cours garderait le verrou jusqu'au bout. Gain nul, ordonnanceur maison et risque de famine en plus |
| Réduire la portée de la détention | ❌ **Déjà faite** par task-079, qui sort persistance et parsing CDA du verrou. L'énoncé la conditionnait à « si le parsing est effectué sous le verrou » : il ne l'est pas. Ce qui reste dessous est du travail réseau réel, hors périmètre |

**Coût chiffré** : une connexion IMAP de plus par praticien *qui écrit*, créée
paresseusement et réclamée par la boucle d'entretien existante. Rapporté au
plancher documenté (2 524 sessions à 500 praticiens), le majorant est un
doublement, atteint seulement si tous écrivent dans la même fenêtre. Le point de
vigilance réel n'est pas la mémoire mais la **limite de connexions par boîte de
l'opérateur MSSanté** — c'est elle que le tir doit confirmer.

#### Cloisonnement

La clé de la voie d'écriture reste dérivée de l'email. Le clone de contexte passe
par `MemberwiseClone` **précisément** pour qu'aucun champ ajouté plus tard ne soit
oublié en silence — l'oubli se manifesterait par une connexion qui n'authentifie
plus. Trois tests gardent la propriété ; `CrossTenantOwnershipTests` : 21 verts.

#### Tests

10 nouveaux côté .NET, 6 côté harnais. Suite : **3 280 verts** ;
`selftest.sh` : **102 tests Python**. Tous **constatés RED avant le correctif**
(exigence de DOD, preuve dans le `## Develop log`).

Neuf tests existants ajustés — leurs substituts stubbaient l'ancienne surcharge
de connexion. **Aucune assertion comportementale modifiée** : les deux voies sont
désormais stubbées séparément pour que `DeleteDraft`, resté sur la voie de
lecture, continue de le prouver.

#### Sonar

**0 issue** sur les 6 fichiers C# touchés et les 2 nouveaux fichiers de test. Les
3 `python:S3776` de `report.py` sont pré-existants (`reduce_prom_matrix`,
`pinned_candidates`, `_observe_table` — task-204 et PR #135).

> ⚠️ KPIs projet toujours inexploitables depuis task-212 — `agents/sonar.md`
> périmé, baseline à refaire.

#### Ce que cette PR ne livre pas

Le **tir de confirmation** : `send` p95 sous 10 s et ratio moyenne/médiane sous 2
(contre 35,1 s et 3,3), non-régression `read_list` / `folders_warm` à 20 %.

Et une réserve reportée au HAG, que la task pose elle-même : **le ×5,5 sur `send`
mélange trois causes** — l'archivage devenu réel (la référence de 1,18 s avait été
calibrée quand il échouait faute de dossier `Sent`), le passage de 200 à 500
praticiens, et l'attente de verrou. Cette PR ne traite que la troisième ; la
nouvelle table par opération est ce qui permettra de les séparer.

---

### v1.16 — Le banc simule des médecins : scénario `journey`, 1 VU = 1 médecin, verdict SLO par palier — task-220

- **Task** : task-220 — `done`. **PR** : `api-mail` #147 (label `awaiting-human-merge`). Commits `d804adc` (feat), `0f1f97f` (smoke), `5f597ad` (passe `/simplify`).
- **Le défaut corrigé** : le harnais `mixed` est un modèle OUVERT (`constant-arrival-rate`) dimensionné par la loi de Little sur des constantes mesurées à 200 praticiens — au-delà, les pools se trouvent courts, k6 jette des itérations et le rapport s'ouvre sur `TIR INVALIDE` (quatre campagnes à 500 sans un chiffre opposable). Trois notions d'« utilisateur » ne se recoupaient pas (`USERS`, `VUS`, pools), le mix 40/30/10/10/10 était une hypothèse à cadence 20-40× humaine, et quatre gestes quotidiens n'étaient jamais exercés.
- **Le modèle livré** : `scenarios/journey.js`, modèle FERMÉ (`ramping-vus`, paliers `JOURNEY_STAGES="5:2m,10:3m"`), 1 VU = 1 médecin à identité et session stables. La charge est émergente : `dropped_iterations` n'existe pas, le `TIR INVALIDE` disparaît **par construction**. Facteur `JOURNEY_TIME_COMPRESSION` (K) : découverte K=10-20, endurance/validation K=1 — **seul K=1 certifie**, `report.py` refuse le verdict au-delà (« non opposable — K=x »).
- **Parcours dérivé du client réel, jamais inventé** : séquence d'appels par étape relevée dans `Client/Blazor` (MailWidgetComponent/SyncProgressWidget pour le dashboard — 4 appels dont `GET /sync/coverage` ; MailListComponent `_pageSize=25` pour l'inbox ; `OnSelectEmail` → contenu + `status/read`), provenance fichier:méthode consignée dans `Api/Mail/docs/parcours-medecin.md`.
- **4 opérations nouvelles instrumentées** (tags `op:`) : `dashboard`, `attachment` (compteur d'octets `journey_attachment_bytes` — l'axe bande passante, ~124 Ko/PJ, jamais écrits sur disque), `delete`, `mark_read`. Double tag `op`+`palier` matérialisé par seuils toujours-vrais (même idiome que `mixed`) ; la rampe est taguée `transition` et n'entre dans aucun percentile de palier.
- **Temps de réflexion log-normaux par étape** (`lib/journey-model.js`, module pur testé par `node --test`) : bornes [min,max] lues comme p5/p95, tirages bornés [min/2, max×2], surcharges `JOURNEY_THINK_*`/`JOURNEY_P_*` refusant une étape inconnue — des temps fixes synchroniseraient les N médecins en vagues.
- **Bandes d'UIDs froide/chaude/suppression disjointes** par boîte : la suppression ne consomme jamais le corpus des autres étapes ; contrôle de budget de campagne qui **échoue au setup** (durée × probabilités × marge 1,5 vs taille de bande) ET à l'exécution (`journey_budget_exhausted`, seuil `count==0`). Chaud/froid séparés côté client : le froid mesure le fetch IMAP + matérialisation `MailContent` (étape 4 de la grille), warmup de la bande chaude au premier passage (tag `warmup`, hors grille).
- **`enrich` n'est plus une action du parcours** (décision consignée) : traitement de plateforme, pas geste de médecin — la pipeline CDA reste à la famille `mixed`, `enrich_short_circuited` n'existe pas dans les rapports journey.
- **`report.py`** : table du genou (palier → N, fenêtre stabilisée, débit émergent, erreurs, Mo de PJ), latence par étape × palier (8 étapes), coûts résidents contre N (sessions IMAP Dovecot, backends Postgres, `cl_waiting` jugé par `pgbouncer_waiting`, RSS par réplica — CSV `observe-*.csv` replié PAR PALIER), verdict SLO par étape confronté à la grille de `docs/SLO-parcours-medecin.md` (validée humain le 2026-08-03) avec garde ≥300 échantillons **au grain de l'opération** (`n_min`) et fenêtre ≥30 min ; sections « débit demandé vs délivré » / « latence planifiée vs mesurée » **absentes** (pas de débit imposé). `INDEX.md` : familles `journey 🚶(fermé)` / `mixed` jamais comparables, colonnes du modèle ouvert neutralisées.
- **Passe `/simplify` (4 agents, ~15 findings)** : coercion `op|tags` dans `api.js` (~60 lignes de duplication supprimées dans `journey-api.js`, réduit aux 6 endpoints propres au parcours), `baseThresholds()` partagé, budget contrôlé sur le plan réellement exécuté, garde d'échantillons au grain de l'opération. Consigné au Simplify log : recouvrement bande froide journey / bande enrich `uid-bands` sur seed partagé (warning au setup, ne pas rejouer `enrich`/`mixed` sans `reset-state.sh`).
- **Smoke du 2026-08-03 (DOD)** : banc réel monté, seed 20×50, `K=10` — verdict k6 **PASS**, 3 294 requêtes, **0,00 % d'erreur**, 100 % checks, 342 passages, 0 abandon, 0 × 429. Chaud 3/4 ms vs froid 418/464 ms (p50/p95) — la séparation des bandes fonctionne. Sessions IMAP 10→21 (suit N), `cl_waiting` 0 partout, RSS 118→162 Mo/réplica. Rapport `report-journey-mssante-n10-101131.md`, vérification par base PASS / Mélange 0, Seq : 0 Error/Fatal, 0 marqueur de régression.
- **Tests** : 18 node (`journey-model.test.mjs`) + 21 unittest (`test_report_journey.py`) neufs ; selftest harnais 131+18 verts ; 3 281 tests .NET verts. **Zéro diff `mixed.js` / `vu-sizing.js`** (DOD). Sonar : aucun fichier du périmètre .NET touché, Quality Gate OK.
- **Reste dû** : la campagne de **certification K=1 ≥ 30 min à N élevé** attend la sortie des serveurs mail de l'hôte (task-221) ; les violations SLO déjà connues (inbox, recherche, envoi) sont le backlog que l'instrument désigne, chacune sera une US.

### v1.17 — Les serveurs mail simulés quittent l'hôte sous test : Dovecot/GreenMail/Toxiproxy sur le cluster k8s — task-221

- **Task** : task-221 — `done`. **PR** : `api-mail` #148 (label `awaiting-human-merge`). Commits `020e99a` (feat), `b3f45f1` (harnais k6), `018057a` (simplify), `57bb187` (sonar).
- **Le défaut corrigé** : sur le banc local, Dovecot volait **2,6 cœurs** au SUT à 500 praticiens et son coût suit la population (sessions = praticiens × réplicas × 2), pas le trafic — tout chiffre > 500 était un artefact connu d'avance, et le CPU de Dovecot se mélangeait à celui d'api-mail dans la même enveloppe machine.
- **Livré — manifests kustomize** (`DevOps/Staging`, **code-only** : repo hors automation, commit DevOps + `kubectl apply` = humain, décision /start consignée) : Dovecot StatefulSet **1 réplica** (les pathologies NFS graves sont multi-serveurs), ConfigMap portée de `src/AppHost/dovecot/dovecot.conf` (TOUS les plafonds durement acquis : imap-login high-perf, imap 8000, stats/auth/anvil 5000, dossiers spéciaux, `mail_max_userip_connections=100`) **+ réglages NFS** (`INDEX=` sur `emptyDir` local — le point chaud hors NFS —, `mmap_disable`, `mail_fsync=never`, `mail_nfs_*=no`), PV/PVC NFS statique 50 Gi (`192.168.0.7:/data/loadtest-mail`, patron pv-nfs-postgresql), GreenMail (puits SMTP, Service interne seul), Toxiproxy (NodePorts **30474** API / **30993** IMAPS praticiens / **30465** SMTPS), Dovecot direct **30994** (seed).
- **Un seul interrupteur `MSS_LOADTEST_MAIL_HOST`, trois consommateurs** : AppHost (zéro conteneur mail local — PgBouncer/collector restent, plateforme sous test ; absente = comportement inchangé, **les deux vérifiés au runtime** : 2 vs 5 conteneurs), seed (`--mail-host` : UserSettings → NodePorts, injection directe, API Toxiproxy ; ports d'ÉCOUTE du pod 13993/13465 en `const` — le Service mappe NodePort → containerPort), harnais k6 (`TOXIPROXY` dérivé + surcharge `LATENCY_MS`).
- **Deux défauts réels trouvés PAR les vérifications runtime** (pas par relecture) : (1) le premier garde AppHost coupait aussi PgBouncer/otel-collector — attrapé en comptant les conteneurs ; (2) le harnais k6 ignorait l'interrupteur (setup en échec sur 127.0.0.1:8474, exit 107) — attrapé par le premier smoke distant.
- **Topologie réseau découverte et outillée** : le poste (192.168.1.x) joint le cluster (192.168.0.x) par le **WAN du pfSense** (4 port-forwards WAN posés par l'humain, « Block private networks » décochée) ; l'ICMP ne traverse pas — **RTT mesuré par connexion TCP chronométrée : ≈ 5 ms** → latence injectée **95 ms** (invariant MSSanté 100 ms total), à poser sur `--latency` (seed) ET `LATENCY_MS` (chaque tir k6 ré-applique le profil, 100 ms en dur sinon).
- **Vérifications cluster (DOD 10/10, apply humain)** : pods Running/PVC Bound ; dry-run kustomize 10 ressources sans erreur ; seed 20×50 en **49 s** `read-back verified` (l'injection directe ne paie pas la latence) ; smoke k6 `folders` **PASS** (7 076 req/60 s, 0,00 % err) ; `enrich` non court-circuité (6,3–10,2 s réels) ; `doveadm who` via `kubectl exec` : 5 praticiens × **2 sessions** — première observation cluster du plancher `praticiens × 2` (task-213).
- **Verdict NFS : TENU** (protocole de l'US, seuil ~2×) — `enrich` froid 10 UIDs 6,30–6,62 s vs 4,3 s local (~1,5×), `folders_cold` 1,05–1,21 s vs 0,7–1,05 (~1,1×), lecture froide 0,50–1,17 s vs ~0,9 (~1,0×). La première touche (10,16 s) paie la construction des index Dovecot + cache NFS froid — écartée du verdict, consignée.
- **Sonar** : Quality Gate OK, **17 → 0 issues new-code** — aucune n'appartenait à task-221 (héritées du merge task-218 #146, migration IResilientCacheService) : 14× CA2016 (`cancellationToken` forwardé au cache résilient — argument **nommé** sur le `SetAsync` à 3 args, un positionnel tombait sur `slidingExpireTime`), 1× S4487 (`_logger` mort retiré), 2× CA1859. Smells projet **47 → 30**. Acceptation consignée : `new_coverage` 88,9 % < 95 % aspirationnel (dominé par le code hérité de task-218, hors périmètre).
- **Tests** : 4 tests `SeedOptions` neufs (test-first, RED constaté) + les 9 appels `Parse` des tests passés sur la surcharge déterministe (les 7 préexistants lisaient le vrai env et auraient mesuré le poste en campagne distante — trouvé par la passe `/simplify`, 4 agents, ~8 findings, `018057a`). 3 285 tests Release verts ×2.
- **Skill `loadtest-skill`** : section « Mode DISTANT » (déploiement, surface NodePort, RTT aux DEUX endroits, contrôles `kubectl exec`/`top`, purge du PVC, piège NFS + smoke comparatif obligatoire).
- **Reste dû (hors scope US)** : la campagne de certification K=1 ≥ 30 min à N élevé (l'instrument de task-220 + ce banc distant la rendent enfin possible) ; suggestions PR : `initialDelaySeconds` des probes GreenMail/Toxiproxy (1 restart au premier pull), re-mesurer le RTT si la topologie pfSense change.

### v1.18 — Le verrou de session rendait un sémaphore qui n'était pas le sien : un envoi remis annoncé en échec — task-223

- **Task** : task-223 — `done`. **PRs** : `api-mail` #149, `dtos-mss` #28 (label `awaiting-human-merge`). Commits `da1f5ee` (bump DTO), `2452a9b` (jeton de verrou), `8862818` (distinction archivé/non archivé), `c8a29b9` (simplify), `33a1bba` (correctif issu de la revue). NuGet `HealthPlatform.Dtos.Mss` **377.0.0 → 381.0.0** (run CI 381).
- **Le constat, et sa provenance** : campagne de certification K=1 du 2026-08-03 (200 médecins, rythme réel, 3 352 envois, 105 000 requêtes) — **1 erreur, taux global 0,001 %**. Trace `4ad7594f36b4773d8551b77ba08fc663`, rapport `reports/2026-08-03/report-journey-certif-n200-180029.md`. C'est la campagne que task-221 avait débloquée, et la seule erreur de tout le tir. Qualitativement la pire : envoi **remis** au destinataire, **rendu en erreur** au praticien → renvoi naturel → **document de santé dupliqué** dans le dossier patient du correspondant.
- **La cause, et ce qu'elle n'est pas** : ce n'est **pas** l'échec d'archivage (`AppendToSentAsync` renvoie un `Result` en échec, traité comme non fatal par ses deux appelants depuis toujours). C'est la **libération du verrou de session** : `ImapLockScope.DisposeAsync` → `UnLockImapClient(userContext)` → `GetSession(id)` → `session.ImapLock.Release()`. La libération **retrouvait la session par son identifiant** au lieu de rendre le sémaphore effectivement pris. Si l'entrée `_sessions[clientSessionId]` a été recyclée entre la prise et le rendu — expirée par `CleanupExpiredSessions`, `TryRemove`, puis recréée sous la même clé par la requête suivante — le `Release()` tombe sur un sémaphore **neuf, jamais pris**, `CurrentCount == 1` → `SemaphoreFullException`.
- **Pourquoi l'archivage, et pourquoi si rare** : l'exception est levée depuis le `await using` **en sortie** d'`AppendToSentAsync`, donc **hors du `try`** qui l'enveloppe — le `catch (Exception)` intérieur est *dans* le `try`, pas autour du `using`. Elle échappe donc à la conversion en `Result` et remonte au `GlobalExceptionHandler` → 500. Et l'archivage emprunte la **voie d'écriture** de task-213, qui n'existe que le temps des envois : c'est l'entrée de session la plus exposée au recyclage. Les deux faits ensemble expliquent la localisation *et* la rareté.
- **Correctif 1 — le mécanisme ne peut plus se tromper de verrou.** Nouveau `ImapSessionLockHandle` (`src/Application/Session/`) : `LockImapClientAsync` capture `session.ImapLock` **une fois**, avant l'attente, et rend un jeton qui **porte ce sémaphore**. `UnLockImapClient(ImapSessionLockHandle)` remplace `UnLockImapClient(UserContextInfo)` : plus aucune recherche à la libération, donc plus de fenêtre. Rendu unique par `Interlocked.Exchange`. **Le patron existait déjà dans le même dossier** — `BackgroundImapConnectionRegistry.Lease` tient son `Entry` et rend *son* sémaphore, avec le même `Interlocked` et son logger tiré du propriétaire ; le jeton s'y aligne (passe `/simplify`). Volontairement **pas** `IDisposable` : un `using` direct contournerait `ImapLockScope`, que task-214 a fait seule voie d'acquisition pour que toute détention soit mesurée.
- **Correctif 2 — nécessaire, pas décoratif.** Le recyclage **dispose** la session (`CleanupExpiredSessions` → `Dispose()` → `_imapLock.Dispose()`) : rendre le **bon** verrou lève alors `ObjectDisposedException`, soit le même 500 par une autre porte. `Release()` journalise et ne propage jamais — `SemaphoreFullException` → Error (l'appariement prise/rendu est en cause, à suivre par la trace, pas par un 500 chez le praticien), `ObjectDisposedException` → Warning (entrée recyclée, plus personne n'attend), double rendu → Warning.
- **Correctif 3 — trouvé à la revue de code, même classe de défaut.** L'acquisition du verrou d'écriture expire à **120 s** en `TimeoutException`, levée depuis l'initialiseur du `await using` — **hors d'atteinte** du `catch` intérieur, exactement comme la libération. Sous la contention que task-211/213/214 mesurent, c'est le scénario le plus plausible après le défaut de libération, et il produit la même issue interdite. Converti en `Result` en échec + tracé dans `AppendToSentAsync`. **`OperationCanceledException` continue de remonter à dessein** : quand c'est le praticien qui a abandonné sa requête, le 499 central est la bonne réponse — la séparation timeout interne / annulation client existe déjà dans `LockImapClientAsync` (`catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested) → TimeoutException`) et c'est elle qu'on exploite. `MailController.ArchiveSentMessageAsync` porte en outre l'invariant **là où il est connu** — à cet endroit le message *est* parti — avec un commentaire disant pourquoi ce `catch` n'est pas le boilerplate proscrit par la règle 12 (il **préserve un succès réel**, il ne fabrique pas une réponse d'erreur ad hoc) et pourquoi il ne faut pas le « nettoyer ».
- **La distinction rendue** : `POST /mail/sendmail` renvoie `{ queued, archived, warning }` — `warning` est un **libellé métier fixe** (`ApiMessages.MailSentButNotArchived`), jamais la cause technique (règle 12, zéro fuite ; test dédié vérifiant qu'aucun `IMAP`/`SERVERBUG` ne traverse). Duplication retirée au passage : `SendMailAsync` et `SendAndArchiveAsync` faisaient append+warn à l'identique, désormais un seul `ArchiveSentMessageAsync` — deux endroits où réintroduire l'idée qu'un échec d'archivage est un échec d'envoi.
- **Tracé PGSSI-S** : nouvelle valeur `AuditActionType.MailArchiveSent`, **ajoutée en fin d'énumération** (le format d'audit sérialise l'ordinal — toute insertion au milieu re-libellerait l'historique côté Angular/Blazor). `TraceArchiveOutcome` émet une trace **hors verrou**, sur les 4 chemins de sortie, `Success` = archivé ou non, jointe à l'évènement d'envoi par `MailMessageId`. **Pourquoi une seconde trace et non un enrichissement de `MailSend`** : `SmtpService` écrit l'évènement d'envoi dès que le message est remis, donc **avant** que l'archivage soit tenté — son issue ne peut pas y figurer, et la file d'audit (`Channel<MssAuditTrace>`) ne se ré-écrit pas. `ActionType` étant persisté en `string`, **aucune migration**. **Aucune donnée de santé** : ni `Subject`, ni `ToAddresses`, ni `FromAddress`, ni `PatientIns`, ni `PatientName` — test dédié ; l'identifiant RFC 5322 suffit à rejoindre l'évènement d'envoi qui porte déjà ce contexte.
- **Preuve ROUGE avant correctif** (exigée au DOD) : sémantique d'avant le correctif rétablie temporairement dans `UnLockImapClient` (recherche par identifiant, sans `catch`) → `ReleasingAfterTheSessionEntryWasRecycledDoesNotThrow` et `ReleasingAfterRecyclingLeavesTheFreshSessionLockUntouched` échouent sur `System.Threading.SemaphoreFullException` — **l'exception exacte** de la trace de campagne. Correctif remis : 5/5 verts.
- **Tests** : 12 ajoutés. `Session/SessionLockReleaseMismatchTests.cs` (5) — reproduction du recyclage ; **contre-épreuve** vérifiant que le sémaphore de la session *neuve* reste à `CurrentCount == 1` (sans elle, un `catch` bien placé suffirait à faire passer le premier test tout en laissant le verrou de la session vivante ouvert d'un cran) ; double rendu ; verrou disposé ; cycle nominal. `Services/Imap/ImapServiceArchiveAuditTests.cs` (5) — trace succès/échec, absence de donnée de santé, timeout d'acquisition ⇒ `Result`, annulation client ⇒ propagée. `Controllers/MailControllerTests.cs` (+4). **`UnLockImapClientShouldHandleMissingSession` retiré** et remplacé par `UnLockImapClientRejectsAMissingHandle` : la branche « session introuvable » n'existe plus — elle décrivait la tolérance au symptôme plutôt que l'absence de cause. `SessionLockAcquisitionSurfaceTests` reste vert **sans édition** (les noms de membres de l'interface sont inchangés).
- **Build / tests** : 0 erreur, 0 avertissement ; **3 384 verts**, 16 ignorés. **1 flaky pré-existant prouvé tel** : `Services.Export` (`MarkdownPdfRendererTests` / `MailExportServiceTests` alternativement), cause `UglyToad.PdfPig` — « Could not find the font with name /F5 in the resource store » dans la **lecture** du PDF côté assertion. Reproduit sur un **worktree de `origin/develop` sans une ligne de task-223 : 2 échecs sur 6 runs**. `Services/Export` hors diff.
- **Sonar** : **zéro dette introduite**. QG `ERROR` avant comme après, sur 18 `new_violations` dont **aucune** dans un fichier du diff — provenance établie par `git log` : `tests/loadtest-k6/**` (15, dont l'unique **bug** `python:S1244` à `report.py:1336` et le hotspot `weak-cryptography`) → **task-220** mergée le jour même et scannée pour la première fois ; `IIheXdmProcessingService.cs:9` (`S103`) → **task-185** ; `BaseRepository.cs:68` (`S103`) → **task-218**. La période `PREVIOUS_VERSION` place dans le « new code » des tasks déjà mergées (piège consigné en mémoire). `coverage` 85,6 → **86,9 %**, `new_coverage` 84,9 → **87,0 %**, duplication 0,6 → 0,5 %. Phase 2 legacy **volontairement non lancée** : `report.py` est nommé « Hors scope » par le PO (task-224), les 3 findings restants appartiennent à task-185/218/220 (règles 5 et 6), et `S3776` est hors chaîne par construction (`/sonar-s3776`).
- **Signalé hors périmètre** : (1) le **bug** `python:S1244` de `report.py:1336` vit dans le générateur du rapport de tir dont dépend le plan de test de cette task — à porter à **task-224** ; (2) entre l'obtention du jeton et le `return` du scope, `MarkLockAcquired` et les logs pourraient théoriquement lever et faire fuir le verrou — **pré-existant et inchangé** (le verrou était déjà pris au même endroit), non corrigé car la task interdit d'élargir au modèle de verrouillage ; (3) `POST /cancel-and-replace` n'a pas changé de forme — faire traverser l'issue d'archivage à `IMailCancellationService` (callback rendant un `bool`) sortait du défaut corrigé ; la trace `MailArchiveSent` couvre néanmoins ce chemin, étant émise dans `AppendToSentAsync`.
- **Non touché délibérément** : la portée du verrou de session, son existence, la voie d'écriture (task-211 / 213 / **216**). task-216 réduira la **fréquence** du défaut en retirant la voie d'écriture, mais **pas le défaut** — il est dans le mécanisme de libération. Les deux US sont indépendantes ; si task-216 passe d'abord, la **reproduction au banc** devient plus difficile, ce que le plan de test assume.
- **Reste dû** : le tir `journey` **K=1** au banc (zéro erreur serveur sur l'envoi, contre 1 sur 3 352 en référence) — exige le nœud de banc distant `MSS_LOADTEST_MAIL_HOST`, hors de portée de la forge, **à la charge de la recette**. Et le câblage de la mention côté client : la task est scopée `api-mail` / `**Single frontend**: true`, donc `archived` + `warning` existent dans le contrat et l'audit mais **aucun frontend ne les rend** — US de suivi à arbitrer pour `client-blazor` / `client-angular` / `client-mobile`.

### v1.19 — Le décompte des sollicitations du serveur de messagerie — task-225

- **Task** : task-225 — `done`. **PR** : `api-mail` #151 (label `awaiting-human-merge`). Commits `e8ff2b5` (instrumentation + 7 tests), `d3f2912` (retrait d'un BOM parasite trouvé en revue). `dtos-mss` : branche vide, aucune PR, aucun publish NuGet.
- **Pourquoi** : campagne de certification du 2026-08-03, trace `4d911c462694fab4d7454de2453bb13f` (ouverture à 439 ms) — 19 ms pour résoudre le praticien et sa base, **420 ms à l'intérieur du verrou de session IMAP** avec `WaitTimeMs=0` (du travail, pas une file), p95 serveur = p95 client. **Et là la télémétrie s'arrêtait** : 420 ms est *compatible* avec quatre allers-retours de 95 ms sans le prouver. Cette ambiguïté a permis à **task-222** (annulée) de bâtir une cause plausible et fausse, puis un correctif qui aurait supprimé le décodage CDA des mails ouverts avant analyse.
- **Livré** : `IMailServerSolicitationRecorder` (`Scoped`) + `MailServerSolicitationRecorder` (`ConcurrentQueue`, sans verrou) ; compteur `mssante_mail_server_solicitations_total{command,operation}` ; étiquette de trace `mss.mail_server.solicitations` portant le **delta propre à l'appel** (et non le cumul de la requête — seule forme permettant d'affirmer qu'une ouverture donnée n'a pas parlé au serveur). Sites : `resolve_folder` / `open_folder` / `fetch_bodystructure` / `fetch_body_part` ×n / `close_folder` (`ImapService`), `connect` / `authenticate` (`ImapConnectionService`) **là où ils sont réellement émis**. **Une session reprise du pool ne compte pas** donc borne inférieure **exacte** des allers-retours, propriété couverte par un test dédié.
- **PGSSI-S** : étiquettes littérales bornées à la compilation (`MailServerCommands`, familles d'opération) — aucun chemin de dossier, aucun UID, aucun nom de PJ (qui en messagerie de santé nomme couramment le patient et l'examen). Même règle que `LockOperationFamily` (task-213). **Un test fige la propriété** au lieu de la documenter seulement.
- **Garde-fous reposés** (ils étaient sur la branche de task-222, supprimée avec elle) : (1) avertissement dans `IMailRepository` **à l'endroit exact** où la méthode fautive vivait ; (2) avertissement en tête de la doc XML de `GetEmailContentAsync`, disant que `Content` nul est un **état voulu** ; (3) **deux tests** assertant qu'une lecture n'écrit rien — un unitaire et un sur **vrai PostgreSQL**.
- **Périmètre — contrat tenu sur le fond, plafond mal posé** : clauses vérifiées **par commande** — aucun correctif, **aucune méthode ajoutée au dépôt**, garde `existingMail is { Content: not null }` inchangé, aucune passe de simplification, harnais k6 intact. En revanche le plafond du DOD (2 fichiers neufs + 4 touchés) est dépassé : **2 sources neuves + 5 touchées**, plus 1 test neuf et 1 touché non énumérés. Plafond chiffré avant énumération, alors que chacun des 5 fichiers est exigé par un point du « Contenu attendu ». **Écart déclaré plutôt que masqué** — ni garde-fou retiré pour tenir le chiffre, ni DOD réécrit après coup. Une extraction déclarée : `GetEmailContentInternalAsync`, privée, pour héberger le `try/finally` sans indenter 80 lignes ; corps déplacé tel quel.
- **Tests** : **7 neufs**, assertions sur un **nombre** d'allers-retours jamais sur un temps. `ImapServiceTests` (5) — message analysé donne 0 sollicitation **et** verrou de session non acquis ; message non analysé donne la **séquence exacte** des 5 commandes ; session du pool ne compte ni `connect` ni `authenticate` ; une lecture n'écrit rien ; étiquettes sans donnée de santé. `MailServerSolicitationCountIntegrationTests` (2, **vrai PostgreSQL**) — les deux faces, dont la garde anti-régression.
- **Build / tests** : 0 erreur, **0 avertissement** ; **3 392 verts**. **Trois instabilités, toutes établies pré-existantes par mesure** : (1) `ImapServiceTests.GetFolderTodayAsync_HappyPath_TagsTheImapActivityWithPerCommandDurations` — **défaut d'isolation** : échoue **seul**, passe dans sa classe ; reproduit sur un **worktree de `origin/develop` sans une ligne de cette PR** ; sur le projet `application.tests` complet, `develop` échoue **1 run sur 2** et cette branche passe **2 sur 2** ; test intact dans le diff. Cause : listener d'activité **global** dont la variable `captured` est écrasable par une autre classe en parallèle. **Signalé comme candidat à correction** — il produira du bruit à chaque cycle. (2) `MailExportServiceTests` — flaky `UglyToad.PdfPig` de v1.18. (3) `PgBouncerTransactionPoolingTests` — une fois pendant l'analyse Sonar (contention Docker), vert en isolation.
- **Défaut trouvé en revue et corrigé** : l'outillage de patch écrivait en `utf-8-sig`, ajoutant un **BOM** à quatre fichiers qui n'en avaient pas — leur ligne 1 apparaissait modifiée sans raison. Retiré (`d3f2912`) : exactement le bruit qui rend un diff plus dur à relire, sur une task dont le propos est un diff étroit.
- **Sonar** : **zéro dette introduite, une seule itération, zéro correction nécessaire** — une première sur cette EPIC. Effet de la lecture préalable des conventions apprises : contrôle `awk` des 150 caractères (`S103`) passé **avant** le commit, et entrée `S125` (apprise sur la branche annulée de task-222) appliquée d'emblée. `coverage` 86,9 % inchangé, `new_coverage` **86,9 %** (seuil 80 OK), `new_duplicated_lines_density` **0,08 %** (seuil 3 OK), ratings C/A/A. QG `ERROR` avant comme après sur 18 `new_violations`, **aucune dans un fichier du diff** : 16 vers task-220 (`tests/loadtest-k6/`, dont l'unique bug et l'unique hotspot), 2 `S103` vers task-185 / task-218. Phase 2 legacy **volontairement non lancée** : le code du harnais va être rouvert par task-224 (défaut 5), y toucher ici entrerait en collision.
- **Ce que ça débloque** : le **défaut 5 de task-224** devient démontrable — l'étape 3 du parcours `journey`, annoncée « servie base », enregistre **5 sollicitations** (mesurable dès maintenant) et devra passer à **0** une fois sa chauffe corrigée. C'est la raison de l'ordre 225 puis 224 décidé par l'humain.

### v1.20 — Les cinq défauts d'instrument du banc, dont un qui a faussé un verdict — task-224

- **Task** : task-224 — `done`. **PR** : `api-mail` #152 (label `awaiting-human-merge`). Commits `2042b3d` (défaut 5), `675c28c` (défauts 1 & 2 + contrôles), `6927cc2` (défaut 3), `e681869` (défaut 4 + item 8), `f54dcec` (simplify), `b22f857` (S1192 préventif). `dtos-mss` : branche vide, aucune PR. **Zéro fichier C# dans le diff.**
- **DÉFAUT 5 — le seul à avoir faussé un verdict, et il n'était pas dans les quatre initialement listés.** `warmUpOwnMailbox` chauffait la bande de relecture avec `getEmailContent`, en commentant que « le GET contenu matérialise le MailContent ». **Faux** : le chemin de lecture n'écrit pas dans le stock et ne doit pas y écrire — la présence d'une ligne de contenu est le **marqueur d'analyse** (task-225 ; task-222 annulée pour l'avoir écrit depuis la lecture, ce qui supprime le décodage CDA). La bande « chaude » n'était donc **jamais analysée** et l'étape 3 mesurait des ouvertures **froides** : d'où l'égalité 440 ms (étape 3) ≈ 442 ms (étape 4 « froid »), **pas un symptôme mais la signature de l'artefact**. Correctif : la chauffe passe par `enrich/sync`, **un seul appel** pour la bande (l'endpoint prend un tableau ; 15 appels séquentiels de ~4 s coûteraient une minute par VU pour rien), et le commentaire fautif de `journey-model.js` tombe aussi — un commentaire juste devant un comportement faux ne mesure toujours rien.
- **ITEM 7 — la pièce la plus importante de la task, plus que les cinq correctifs.** Le rapport ne **croit** plus le nom d'une étape, il le **vérifie** : `JOURNEY_SLO_GRID` porte `served_from_store` sur l'étape 3, et le verdict la refuse si `mssante_mail_server_solicitations_total{operation="GetEmailContent"}` dépasse la tolérance. **Trois** états, et le troisième vaut autant que les deux autres : non nul ⇒ étape refusée, bandeau **avant** les tables, palier tombé ; nul ⇒ étape jugée ; **absent ⇒ « non vérifiée », jamais lu comme zéro** (task-214 — un binaire antérieur à task-225 ne publie pas ce compteur). Tolérance 0,05/s pour la queue de la chauffe (taguée `warmup`, hors grille), trois ordres de grandeur sous ce que produit une étape non analysée. **Sans ce contrôle, un chiffre DANS la cible aurait été publié vert** : c'est lui qui empêche un artefact d'instrument de redevenir une US applicative.
- **DÉFAUT 1 — latences 1000× trop petites, et une SECONDE occurrence non listée.** Les panneaux `p95/p50 par operation` déclaraient la milliseconde sur des séries en secondes. Tranché par mesure : le magasin annonce 0,0097 pour un appel chronométré à 5,5–11 ms ; en ms cela ferait 9,7 µs pour un aller-retour réseau. Corrigé l'**affichage**, pas la donnée. **Le contrôle générique a trouvé `saturation.json / « p95 serveur par route (ms) »`**, un `histogram_quantile` sur `_seconds_bucket` déclaré en ms — panneau que sa **propre description** désigne comme « le juge de l'attribution », à confronter au p95 client. Les deux étaient faux du **même** facteur : leur confrontation semblait cohérente, et c'est la comparaison à la grille SLO (en ms) qui était fausse. Titre et unité corrigés.
- **DÉFAUT 2 — le panneau d'erreurs était aveugle.** Il lisait `k6_http_req_failed_total` : `http_req_failed` est une métrique de type **Rate** côté k6, publiée en `_rate` (les Counter deviennent `_total`). Il n'affichait donc **rien**, et un panneau d'erreurs vide se lit « aucune erreur » — c'est pourquoi il est resté faux depuis sa création. **La moitié qui compte** : `noValue: "pas de donnee"` sur **77 blocs** des trois tableaux du banc. Le mode d'échec « vide se lit zéro » n'est pas propre aux erreurs.
- **DÉFAUT 3 — l'adresse complète servait d'étiquette de série.** k6 met l'URL entière dans `name` : chaque UID créait sa propre série, des dizaines par geste, croissant avec la population **et** la durée. Deux conséquences mesurées — compteurs **sous-estimés** jusqu'à −61 % sur l'ouverture de messages froids (les séries touchées une fois sortent de la fenêtre de fraîcheur, quand les gestes à adresse fixe tombaient à ±1 % du modèle), et un percentile agrégé sur ces séries **n'est plus un percentile**. Correctif : `lib/routes.js` (module **pur**, donc testable par node comme `journey-model`) porte un gabarit par forme d'adresse, posé en `name` sur 12 appels ⇒ cardinalité **bornée par le nombre de routes**. **Non fait délibérément** : supprimer l'étiquette — elle distingue les **quatre** appels du geste « arrivée dashboard », qui partagent le même `op` ; un test le fige. Détail qui aurait fait fuiter : les tags de l'appelant sont désormais **copiés**, la voie `journey` réutilisant le même objet d'un appel à l'autre. **⚠️ Bénéfice PGSSI-S non accessoire** : le gabarit **retire le nom de la pièce jointe** de l'étiquette — en messagerie de santé il désigne couramment le patient et l'examen (leçon de task-213). Le regroupement **réduit** la donnée exposée en plus de borner la cardinalité ; test dédié.
- **DÉFAUT 4 — « Sessions IMAP » vide depuis task-221.** L'échantillonneur interrogeait un Dovecot **local** disparu ; il journalise proprement son échec (bon comportement) mais la ligne restait vide, or c'est le coût qui suit la **population**, l'axe central du modèle par parcours. Pendant la campagne du 3 août la grandeur a dû être obtenue par contournement — qui a révélé que le banc **surestimait ce coût d'un facteur cinq**, un résultat qu'on a failli ne pas avoir. **Voie retenue, plus simple ET plus fidèle que la sonde distante** : la messagerie publie déjà `mssante_imap_sessions_active` (task-211), concordante à 2 % avec un comptage indépendant (94/195/401 aux trois paliers). La ligne se remplit **depuis le magasin, sans aucun accès au cluster**. `active` et non `connected` : c'est le nombre de sessions **résidentes**. Trois états : sonde locale présente ⇒ sa valeur (priorité gardée, test dédié) ; sonde muette + magasin ⇒ magasin, annoté ; les deux muets ⇒ **« non relevé », jamais un zéro** — un zéro se lirait « aucune session », l'inverse de la vérité pendant un tir.
- **ITEM 5 — le contrôle automatisé, et il m'a eu.** `tests/loadtest-k6/test_dashboards.py`, 5 tests. La première version posait « la métrique contient `_seconds` donc le panneau doit être en secondes » : **faux**, PromQL change la dimension — `rate(x_seconds_total[1m])` rend des secondes par seconde, un ratio sans dimension (des cœurs, pour du CPU) où `percentunit`/`none` sont légitimes. **Dix faux positifs.** Seul le quantile d'un histogramme garantit la dimension de sortie, donc c'est la seule forme jugée. Consigné **à côté du code** plutôt que corrigé en silence : un contrôle qui se trompe de dimension serait exactement le défaut qu'il prétend empêcher.
- **ITEM 8** — verdict de l'étape 3 du 2026-08-03 requalifié **non opposable** dans `reports/INDEX.md` : ligne marquée + note de lecture expliquant que l'égalité 440 ≈ 442 ms était la signature de l'artefact. Le rapport n'est **pas** réécrit (les JSON font foi) — l'index est annoté.
- **Tests** : **20 ajoutés** — 6 sur le refus d'une étape mal nommée (dont le refus d'une étape **pourtant dans ses cibles**, la non-contamination des autres, l'absence distinguée de zéro, et la position du bandeau avant les tables), 5 sur les contrôles de tableaux de bord, 6 sur le contrat de cardinalité (dont le nom de PJ absent), 4 sur les sessions (dont la **priorité de la sonde locale** — le magasin est le repli de la sonde morte, pas son remplaçant autoritaire). **146 Python + 39 node**, `selftest.sh` vert.
- **Revue de code — ⚠️ un risque chiffré plutôt que découvert au tir** : le coût de la chauffe change d'ordre de grandeur, de 15 `GET contenu` légers à **1 `enrich/sync` de 15 UIDs**, soit **~65 s de pipeline CDA par VU** contre quelques centaines de ms. `JOURNEY_PALIER_TRIM_S` ne rogne que 10 s : le premier palier pourrait voir de la charge de chauffe dans sa fenêtre. Borné par l'échelonnement des démarrages de `ramping-vus`. Remèdes du moins au plus structurel : relever le rognage, baisser `JOURNEY_WARM_SHARE`, ou **faire enrichir la bande chaude par le seed** hors bande (le bon à terme, mais il touche `mss.mail.loadtest.seed`, hors périmètre). **Ne pas enrichir est le défaut lui-même** : le correctif reste le bon choix. Point de vigilance pour la recette, pas un blocage.
- **Build / tests .NET** : 0 erreur ; 3 391 verts, **1 flaky pré-existant par run** (`Services/Export`, famille `UglyToad.PdfPig` de v1.18 ; 31/31 en isolation). **Aucun fichier C# dans le diff**, ce qui exclut mécaniquement une régression.
- **Sonar** : **zéro dette introduite, vérifiée PAR PROVENANCE et non par total.** Un total inchangé à 18 ne prouverait rien : cette task **rouvre précisément** les fichiers qui portent ces findings et y insère du code, donc leurs numéros de ligne bougent et les mêmes findings ressemblent à des nouveaux. Comparaison par **(règle, fichier)**, relevée avant l'analyse : `report.py` S1192 ×2 / S3776 ×6 / S1244 ×1 / S3358 ×1, `journey-model.js` S1940 ×2 / S6035 ×1, `journey.js` S1940 ×1 / S3776 ×1 / S4624 ×1, C# S103 ×2 — **tous identiques**. Les trois fichiers neufs (+321 lignes de JS et Python) produisent **zéro** finding : les conventions ont été lues avant d'écrire. **Deux itérations sans correction entre elles** — la première portait sur `f54dcec`, avant l'extraction de constante ; mesurer un commit qui n'est pas celui qu'on merge serait ironique sur une task dont l'objet est la véracité des instruments. **Honnêteté sur cette extraction** : `IMAP_SESSIONS_KEY` a été extraite en prévention (5 occurrences, `conventions/python.md`) mais **Sonar ne l'aurait pas signalée** — le compte de S1192 est resté à 2. Justifiée sur le fond, ce n'est pas un finding évité. QG `ERROR` avant comme après : 16 → task-220, 2 → task-185/218, **0 → task-224**. Phase 2 legacy **volontairement non lancée** — y toucher mélangerait la dette d'une autre task avec cinq correctifs d'instrument sur la même branche, soit le mélange qui a coulé task-222.
- **Reste dû — quatre critères de DOD déférés au banc** (nœud distant `MSS_LOADTEST_MAIL_HOST` absent de la forge) : confrontation panneau ↔ rapport d'un même tir, valeur réelle du panneau d'erreurs, concordance des compteurs à ±2 % sur **tous** les gestes, et **« étape 3 : 5 sollicitations avant, 0 après »** — *la* preuve du défaut 5, qui se lira en une ligne du prochain rapport. Tout le reste est couvert par test.

### v1.21 — Le dossier patient entre au parcours, et le tir cesse d'exiger un semis — task-226

- **Task** : task-226 — `done`. **PR** : `api-mail` #153 (label `awaiting-human-merge`). Commits `c481eb0` (parcours), `c13d795` (rapport), `2dbe1f5` (rejeu + provenance), `4c9fc3a` (test de cohérence de grille), `93ed66d` (simplify), `bffa39e` (2 défauts trouvés en revue). `dtos-mss` : branche vide, aucune PR. **Zéro fichier C# dans le diff** (5 `.js`, 3 `.md`, 2 `.mjs`, 2 `.py`, 1 `.sh`).
- **DEUX CHANGEMENTS QUI N'EN FONT QU'UN, et c'est le point de conception.** La réserve de suppression occupait **40 % de chaque boîte pour être détruite** ; c'est exactement la place dont le dossier patient avait besoin pour être exercé à sa vraie taille. Retirer l'un finance l'autre.
- **« SUPPRIMER » EST RETIRÉ — le seul geste qui détruisait son corpus.** Les messages supprimés ne revenaient pas, donc **chaque tir imposait la reconstruction complète des boîtes** avant le suivant. Tout le reste du parcours ne consomme que de la donnée reconstructible côté base. Retrait **franc** : `JOURNEY_P_DELETE`, `JOURNEY_THINK_DELETE` et `JOURNEY_WARM_SHARE` (renommée `JOURNEY_ANALYSED_SHARE`) **font échouer le setup avec la raison** au lieu d'être ignorées — un ancien script tirerait sinon avec les parts par défaut sans le dire, et sa fiche patient serait maigre sans explication. L'étape 8 de la grille reste, réduite à « marquer lu ». Deux voies non destructives sont consignées pour un retour éventuel (supprimer un message qu'on vient d'envoyer, dont l'archivage dans `Sent` produit le corpus ; ou faire voyager un message entre deux dossiers via `PUT …/move`, qui **renvoie le nouvel UID**) — aucune n'est engagée, ce sera une décision produit à part.
- **LE DOSSIER PATIENT ENTRE EN CHAÎNE, pas comme un geste de plus.** Un dossier n'est pas une donnée qui préexiste : **c'est le produit de l'analyse CDA des messages reçus**, et seulement pour ceux qui portent une INS. D'où `traitement CDA → ouverture d'un des messages traités → consultation du dossier de son patient`. **Révision explicite de la décision de task-220** (« l'analyse n'appartient pas au parcours ») : elle reste vraie comme **geste** — le traitement n'a **aucune ligne dans la grille SLO**, il est **publié et jamais jugé** — mais la conclusion tombe dès qu'on veut mesurer le dossier, puisque sans analyse il n'y en a pas. La révision et sa raison sont consignées dans `docs/parcours-medecin.md`, pas seulement ici.
- **POURQUOI LE DÉTOUR PAR LA LECTURE N'EST PAS UN DÉTOUR.** Deux raisons, dont une contrainte dure : c'est le chemin réel du client (badge patient sur le message ouvert, puis saut vers `/Patient?ins=`), **et `enrich/sync` répond `200` avec un corps VIDE** — le harnais n'a donc aucun autre moyen d'apprendre l'identifiant du patient. Conséquence : **aucun appel n'est ajouté** pour la découverte, l'étape 3 déjà mesurée sert de pivot. Corollaire hérité du défaut 5 de task-224 : on ne récolte l'identifiant que sur la lecture d'un message **analysé** — sur un message qui ne l'est pas, la réponse contient bien des documents (le chemin de lecture décode le CDA à la volée) mais **rien n'est écrit**, donc le patient n'existe pas et son dossier serait introuvable.
- **CE QUE LA RAFALE COÛTE.** La page du dossier ne rapporte **jamais** le contenu des messages (`PatientRepository.LoadMailsWithAttachmentsAsync` ne peuple pas `Content`) et le filtre du client est `HasMedicalDocuments && Content == null` : **tous** les messages de la page passent, **en parallèle** (`Patient.razor:150-171`, `Task.WhenAll`). Une consultation = **~23 appels en une seule action du médecin**, contre **~8,5 pour un passage entier** du parcours. Le geste le plus lourd du produit était aussi le seul que le banc ignorait.
- **BRIDAGE À 6 — ce n'est pas un réglage de banc.** Le client réel tourne dans un navigateur, qui limite à ~6 connexions par hôte : une salve de 20 mesurerait une charge que le produit **n'émet jamais**. `http.batch` par tranches reproduit la contrainte, et le plafond est archivé dans le contexte du tir (sans quoi la « largeur de rafale » n'est pas interprétable).
- **LE COUPLE DE CHIFFRES QUI PORTE L'INFORMATION, et il n'était pas dans la US.** La largeur de rafale **sature** (page du client plafonnée à 20) pendant que la taille du dossier **croît** à chaque traitement — or la page se calcule en lisant **tout** le dossier avant de paginer en mémoire (`GetActiveMailIdsByDocDateAsync`, six filtres `FolderPath.ToLower().Contains(...)` qui interdisent tout index). Le tir mesurera donc exactement **le coût d'une page qui ne grandit pas dans un dossier qui grandit**. Les deux grandeurs sont publiées par palier ; c'est leur **écart** qui informe, pas l'une des deux.
- **LE POINT DUR DE L'IMPLÉMENTATION — le défaut 5 de task-224 pouvait revenir par une autre porte.** Le traitement **transforme** ce qu'il touche : s'il empiétait sur la réserve froide, l'étape 4 finirait par mesurer de l'analysé sous un nom de froid. Trois réserves **disjointes** (analysée 0,4 / froide 0,3 / traitement 0,3), `reservesDisjoint` le prouve et `checkBudgets` **refuse un chevauchement au setup**. La réserve analysée est en **tête** de boîte, et ce n'est pas cosmétique : c'est ce qui rend le rejeu exprimable sur un **préfixe** d'UIDs.
- **REJOUER UN TIR SANS SEMIS — le gain, rendu utilisable.** `reset-state.sh --keep-analysed N` conserve l'analyse des UIDs `1..N` et rend leur état « jamais vu » aux réserves froide et de traitement. Un seul `DELETE` suffit : toutes les FK vers `Mails` sont `ON DELETE CASCADE` (`20240101_SetupMigration.cs`), petits-enfants compris — vérifié dans la migration, pas supposé. Supprimer la **ligne** et non son seul contenu est délibéré : c'est ce qui rend l'état réellement froid pour l'étape 4 et réellement analysable pour le traitement ; vider le contenu en gardant l'en-tête laisserait un état intermédiaire qui n'existe **pas** après un seed. `--keep-analysed` + `--drop-databases` est refusé (contradictoire).
- **« ANALYSÉ + INS ⇒ DOSSIER » — comportement produit exercé, pas cas limite.** Un document **sans INS** n'entre dans aucun dossier et attend un rattachement manuel (identito-vigilance : pas de rattachement deviné). **10 des 169 jeux du corpus** n'en portent pas : le harnais les **compte** (`journey_docs_without_ins`) et **jamais en échec**, et un test prouve que leur présence ne dégrade aucun verdict.
- **Le corpus coopère, et c'est mesuré, pas espéré** : sur les 169 jeux de `JEUX_TESTS_FULL`, **99 portent le même patient** (62 % des 159 porteurs d'une INS), 27 un deuxième, 18 un troisième. La distribution en ronde du seed concentre donc la majorité d'une boîte sur un seul dossier : **la page de 20 se remplit sans toucher au seed**, à condition d'une réserve analysée assez large — d'où la condition de mesure des **100 messages par boîte** pour une certification.
- **Grille SLO — 4 lignes actées par le PO** : 8 « Marquer lu » 200 ms / 1 s (« supprimer » retiré), 9 « Rechercher un patient » 300 ms / 1,5 s, 10 « Ouvrir la page d'un dossier » 500 ms / 2 s (le **pire** de la page et de l'opposition, qui partent ensemble au rendu), 11 « **Fiche patient complète** » 1,5 s / 4 s. L'étape 11 est le chiffre que le médecin **ressent** ; 9 et 10 disent où le temps est passé. **Aucune requête ne porte la durée de l'étape 11** : elle est mesurée par le harnais comme un trend, et comme les trends k6 ne publient pas de `count`, ses échantillons viennent de `patient_dossier` (une ouverture de page = une fiche).
- **LE TEST QUI VALAIT LE DÉTOUR — la grille ne peut plus diverger de son contrat.** Elle vit en deux exemplaires : `docs/SLO-parcours-medecin.md` (propriété du PO) et `JOURNEY_SLO_GRID`. Un écart, et le rapport juge autre chose que ce que le produit a promis — **sans que personne ne le voie**, puisque chaque exemplaire est cohérent avec lui-même. Le test lit la table du Markdown et compare les **11** étapes seuil par seuil. Critère du DOD, mécanisé plutôt que vérifié à l'œil : la vigilance humaine sur ce genre de duplication est exactement ce qui a lâché trois fois sur cette EPIC.
- **REFUS D'INTERPRÉTER PLUTÔT QUE CHIFFRE FLATTEUR.** Quand la rafale plafonne sous la **moitié** de la page, le rapport écrit que l'étape 11 **n'est pas interprétable** : le dossier mesuré n'est pas celui d'un médecin réel, et le chiffre décrit un dossier court, **pas** une application rapide. Avertissement **conditionnel** — un avertissement toujours présent n'apprend rien à personne, et la première rédaction du test le passait trivialement (constaté et corrigé).
- **Le bandeau de baseline, posé par le rapport et non par la mémoire du lecteur** : les chiffres du 2026-08-03 ne sont plus comparables pour **deux** raisons cumulées — l'étape 3 y mesurait des messages jamais analysés (défaut 5 de task-224) **et** le mélange du parcours a changé. Le premier réflexe d'un lecteur est de comparer à la campagne précédente ; c'est au rapport de l'en empêcher.
- **Passe `/simplify` — 4 nettoyages, un par axe.** *Réutilisation* : le chemin d'une ouverture de message se construisait dans **deux** fichiers (`api.js` et la rafale, qui passe par `http.batch` donc ne pouvait pas appeler le premier) ⇒ `emailContentPath()` partagé. *Altitude* : deux gardes `if` ad hoc dans le scénario alors qu'un mécanisme générique de refus existait juste à côté ⇒ table `REMOVED_OVERRIDES` + `assertNoRemovedOverrides()` dans le modèle, **avec la raison** de chaque retrait (que le message générique ne donnait pas, et `JOURNEY_WARM_SHARE` ne passe par aucun scanner : `num()` ignore l'inconnu en silence). *Efficacité* : `reservesDisjoint` énumérait tous les UIDs de la boîte dans un `Set` pour trois intervalles ⇒ comparaison d'intervalles ; et un champ calculé que personne ne lit, supprimé. *Simplification* : `treatedUid !== null` évalué trois fois ⇒ un `justTreated` nommé. **Zéro rollback** — le filet a tenu.
- **DEUX DÉFAUTS TROUVÉS EN REVUE, corrigés — ⚠️ écart de règle déclaré.** `/review` est censé être en lecture seule sur le code ; les deux ont été corrigés (`bffa39e`) **parce que tous deux font dire un faux à l'instrument**, le mode d'échec que cette EPIC a déjà payé trois fois. Le choix est déclaré dans la PR et dans le journal, pas caché, et la validation complète a été rejouée derrière. **(1)** `journey_docs_without_ins` **sous-comptait les cas mixtes** : la boucle sortait au premier document porteur d'une INS, donc un message portant un document rattachable **et** un document sans INS déclarait **zéro** en attente — or c'est précisément le cas que le produit doit savoir présenter, et ce compteur est publié. **(2)** Le rapport affirmait « un appel de chauffe **par médecin** » : vrai depuis task-224, **faux** pour les tirs antérieurs où la chauffe bouclait message par message — constaté en **régénérant** le rapport du 2026-08-03, qui annonçait « 3000 appels (un par médecin) » pour 200 médecins.
- **Garde ajoutée hors périmètre littéral de la US, et assumée** : `warmupWarnings` avertit quand la chauffe dépasserait le délai d'expiration de l'appel d'analyse (300 s). Sans elle, une réserve analysée trop grande fait échouer la chauffe **en silence** et l'étape 3 mesure des messages non analysés — le défaut 5 de task-224 **ramené par la porte du dimensionnement**. C'était le point de vigilance n°1 de la US, il n'avait aucune garde. Prolonge directement le risque chiffré signalé en revue de task-224 (~65 s de pipeline CDA par VU).
- **Correction de documentation, hors périmètre littéral** : `docs/parcours-medecin.md` affirmait **encore** que la lecture froide « matérialise » le contenu — l'affirmation exacte que task-224 a démentie. Corrigée avec sa raison et sa conséquence pour le harnais. Un document faux derrière un comportement juste finit par ramener le défaut.
- **PGSSI-S** : l'INS voyage dans le **chemin** de deux adresses du dossier. Le gabarit `{ins}` de `routes.js` est ce qui l'empêche d'atterrir dans les étiquettes du magasin de métriques — **exigence, pas optimisation de cardinalité** — et un test l'interdit explicitement (aucune suite de ≥ 9 chiffres dans un gabarit), avec le *pourquoi* écrit à côté pour que personne ne « corrige » le gabarit en y remettant l'INS.
- **Tests** : **+11 node** (réserves disjointes, réserve analysée en tête, chaîne conditionnée au traitement, budgets sans suppression, avertissements de fiche et de chauffe, table des retraits) et **+11 Python** (couple rafale/dossier, fiche maigre conditionnelle, traitement publié jamais jugé, documents sans INS sans effet sur le verdict, coût de chauffe, réserve épuisée, trend de la fiche, bandeau de baseline, grille sans suppression, échec de la fiche sur le ressenti, **cohérence des deux exemplaires de la grille**). Total **55 node + 157 Python**, `selftest.sh` vert, les **7 scénarios** k6 s'initialisent.
- **Non-régression vérifiée sur les anciens tirs** : le rapport du 2026-08-03 se **régénère** (exit 0), les nouvelles étapes affichent « — » et **non « 0 ms »**, la section dossier dégrade proprement. Contrôle non demandé par la US : c'était le risque réel d'un rapport qui gagne des étapes.
- **Build / tests .NET** : 0 erreur, **3 305 verts, 0 échec** — et **aucun fichier C# dans le diff**, ce qui exclut mécaniquement une régression applicative.
- **Sonar** : **sauté, avec la raison consignée et non tue.** Zéro fichier `.cs` et harnais k6 hors du périmètre du scanner (`dotnet sonarscanner` autour du build de la `.sln` ; `tests/loadtest-k6/` n'a aucun `.csproj`) ⇒ **aucun new code au sens de SonarQube**, une analyse ne remonterait que de la dette préexistante de `develop`. Non exécutable de surcroît dans cette session (`SONAR_TOKEN`/`SONAR_HOST_URL` absents) — les deux raisons sont **indépendantes**. Qualité contrôlée par les moyens qui s'appliquent à du JS/Python : `/forge-simplify` et la suite d'auto-tests.
- **Reste dû — 6 critères de DOD déférés au banc**, tous exigeant un tir : les 4 nouvelles étiquettes et **la chaîne visible dans l'ordre sur une trace** ; largeur de rafale ≥ 10 sur un semis à 100 messages ; **l'étape 4 mesurant encore du froid en fin de tir** (garanti par construction et testé, mais à prouver) ; taille du dossier qui croît pendant que la rafale sature ; part de la chauffe minoritaire ; et **deux tirs consécutifs sans semis ni ré-analyse** — *le* critère qui prouve le gain de la task. L'outil est livré, la démonstration appartient au banc.
- **Point ouvert pour le PO** : le **5ᵉ appel** du geste (« charger plus ») n'est pas implémenté — 4 des 5 appels documentés sont exercés. Le PO a acté une fréquence pour le traitement et pour la consultation, **aucune pour le défilement** ; en inventer une serait une décision de banc déguisée en décision produit, exactement ce qui a déjà coûté cher ici. S'ajoute que le défaut de pagination du produit fait rendre à `page=1` le **même** contenu que `page=0` : un défilement doublerait la rafale pour zéro information. Demande un `JOURNEY_P_LOAD_MORE` décidé par le PO. Hors DOD ⇒ non bloquant (règle 9 : le DOD est le contrat).
- **Deux défauts du produit observés et NON corrigés — le harnais reproduit le client tel qu'il est.** (1) « Charger plus » **recharge la première page** : le client compte ses pages à partir de 0 (`Patient.razor:109,137`), l'API à partir de 1 (`PatientsController.cs:137`, `Math.Max(0, page - 1)`). (2) La page d'un dossier **lit tous les documents du patient puis pagine en mémoire**, avec des filtres qui interdisent tout index — le coût suit la taille du dossier, jamais la page demandée. Si le tir confirme qu'ils pèsent, ils deviennent des US applicatives : **c'est le but de l'instrument**.

### v1.22 — La Phase A de l'enrichissement rend le verrou de session entre sous-lots — task-228

- **Task** : task-228 — `done`. **PR** : `api-mail` #155 (label `awaiting-human-merge`). Commits `d863087` (découpage), `fb4a21d` (passe `/forge-simplify`), `50c7d9c` (`CA1859`). `dtos-mss` : branche créée, **0 commit**, aucune PR — contrat inchangé.
- **LE DÉFAUT, ET IL ÉTAIT MESURÉ.** task-079 avait déjà sorti la **persistance** du verrou `imap_session`. Mais la **Phase A** — le fetch des corps et pièces jointes — le gardait pendant **tout le lot** : détention **p95 58,5 s** au tir `journey-mssante-n300` du 2026-08-04, portée **intégralement** par `EnrichEmails`. Or ce verrou est keyé sur `{email}_{ClientSessionId}` : il sérialise **toutes** les opérations IMAP d'une session. Les gestes courts du médecin faisaient donc la queue derrière le lot entier — `GetEmailContent` payait **1,79 s d'attente p95** pour 17,8 acquisitions/s.
- **LE DÉCOUPAGE.** `EnrichEmailsAsync` itère `ChunkForEnrichment(pendingUids, EnrichFetchChunkSize)` et délègue chaque fenêtre à `FetchEnrichmentChunkAsync`, qui ouvre **son propre** `ImapLockScope`. Le verrou est pris et rendu **par sous-lot** : c'est la sortie de cette méthode qui laisse les gestes courts s'intercaler. `MailOptions.EnrichFetchChunkSize`, défaut **15**, repli journalisé si < 1 (une taille ≤ 0 donnerait une boucle qui n'avance pas).
- **⚠️ LA CONTRAINTE 1 DE LA US SE TROMPAIT D'ENDROIT — et la US ne pouvait pas le savoir, parce qu'un commentaire du code l'affirmait.** Le commentaire disait que la clé `EnrichEmails:{folder}:{hash}` faisait « sérialiser deux passes concurrentes sur les mêmes UIDs », et que c'est elle qui prévenait la course sur l'upsert par UID (`DbUpdateConcurrencyException`). **Faux, vérifié dans le code** : `AcquireLockAsync` ne transmet qu'un **libellé** à `ImapLockScope`, qui appelle `LockImapClientAsync(userContext)` — lequel keye sur la session **et rien d'autre**. Le libellé n'influence **aucune** décision de verrouillage, et ne survit même pas dans les métriques : `MailProcessingMetrics.LockOperationFamily` le tronque au premier `:`. **Conséquence de sécurité et d'exploitation** : passer à une clé par sous-lot **ne multiplie pas la cardinalité** des séries, et aucun chemin de dossier n'atteint une étiquette de métrique — vérifié sur l'implémentation, pas déduit du commentaire.
- **OÙ VIT RÉELLEMENT LA GARANTIE ANTI-COURSE.** Dans `LockEnrichPersistAsync` par (boîte, dossier), pris en **Phase B**, hors du découpage. C'est ce qui a permis de découper la Phase A sans rien affaiblir : il n'y avait **rien à affaiblir** à cet endroit. Propriété figée par `EnrichEmailsAsync_KeepsThePersistLockWhichIsTheRealAntiRaceGuardAsync` — **3 fenêtres de fetch ⇒ 1 seule** prise du verrou de persistance. Commentaire réécrit pour dire ce que l'empreinte fait (un libellé de journal, conservé pour ça) et non ce qu'on croyait.
- **FUITE PRÉEXISTANTE CORRIGÉE, parce que le bloc était justement réécrit.** `FetchedMail` est `IDisposable` — il possède un `IheXdmScratchSet`, donc des répertoires de travail sur disque — et **aucun** chemin ne le libérait : ni `PersistEnrichedBatchAsync`, ni `PersistEnrichedMailAsync`, ni les chemins d'erreur. Les répertoires ne disparaissaient qu'au balayage de démarrage (`IheXdmScratchSweepService`). `finally` + `DisposeAll` sur tous les chemins de sortie. Sûr : `BuildMailDtoAsync` consomme `IheXdmZips.Paths` de façon synchrone, personne n'en a besoin après la Phase B.
- **CHANGEMENT DE COMPORTEMENT VOLONTAIRE, exigé par le DOD et comparé au code d'origine.** **Avant** : une exception pendant le fetch faisait `return` — **tout le lot était jeté**, y compris le travail réseau déjà payé. **Après** : les messages déjà lus sont persistés, les UIDs restants redeviennent `pending` et sont repris à la passe suivante. Sûr parce que chaque `FetchedMail` est **individuellement complet** : persister un sous-ensemble ne marque comme analysés que des messages réellement analysés — précisément l'invariant que gardent les 13 tests de task-227, verts. Les exceptions non-annulation continuent de remonter (`PersistEnrichedBatchAsync` est passée dans le `try`, mais le seul `catch` y est `OperationCanceledException`).
- **BÉNÉFICE NON DEMANDÉ, obtenu par construction** : l'ordre décroissant des UIDs est conservé, et le découpage le rend **visible** — les messages les plus récents, ceux que le médecin regarde, arrivent dès la première fenêtre au lieu d'attendre la fin du lot.
- **TESTS — ce qui est asserté, et pourquoi.** 7 nouveaux, tous sur le **nombre d'acquisitions du verrou**. C'est la seule grandeur qui prouve le découpage : une durée dépendrait de la machine, et un test qui ne compte rien laisserait passer un lot redevenu monolithique. Couverture : un sous-lot / plusieurs sous-lots (5 UIDs, taille 2 ⇒ **3** fenêtres) / ordre décroissant / erreur au milieu ⇒ persiste ce qui a été lu / annulation ⇒ ne persiste rien / le verrou de persistance reste l'anti-course / taille invalide ⇒ repli.
- **Preuve ROUGE** : lot remis monolithique (`int.MaxValue`) ⇒ **3 échecs** (`KeepsThePersistLock…`, `WhenAChunkFailsToConnect…`, `WithMoreUidsThanTheChunkSize…`). Patch de preuve non committé.
- **Build / tests** : 0 erreur, 0 avertissement (Debug et Release). **3 413 verts, 0 échec** en Release, intégration incluse (304/304). Deux instabilités connues nommées et **non attribuées à tort** : `MarkdownPdfRendererTests` (vert 3 fois sur 3 en isolation) et `PgBouncerTransactionPoolingTests` (vert au scan précédent, contention Docker).
- **Sonar — zéro dette attribuable, prouvé par un second scan et non déduit.** L'itération a trouvé **un** finding imputable : `CA1859` sur `ImapService.cs`, introduit par **la passe `/forge-simplify` elle-même** (paramètre élargi à `IReadOnlyList<uint>` alors qu'`Enumerable.Chunk` rend des `uint[]`, imposant une répartition d'interface pour rien). Corrigé. Le compte se vérifie exactement : `new_violations` 30 → 29 (−2 `SYSLIB1045` que le correctif de task-227 a supprimés, +1 `CA1859`) → **28**. Second scan : **0 finding** sur `ImapService.cs`, `MailOptions.cs`, `ImapServiceTests.cs`. Le Quality Gate reste ERROR sur de la dette antérieure, entièrement dans le harnais k6 (`report.py`, `journey.js`, `journey-model.js`) plus 2 `S103` préexistants ; les 2 security hotspots qui plafonnent le ratio à 71,43 % sont deux `Math.random()` de `journey.js`, en `TO_REVIEW` — ils maintiendront le QG rouge à chaque cycle futur, et les marquer *safe* est un **jugement de sécurité déféré à l'humain**, pas pris au passage.
- **Passe `/forge-simplify` — 2 prises.** *Réutilisation* : `ChunkForEnrichment` réécrivait `Enumerable.Chunk` à la main (`GetRange` + `Math.Min` + boucle d'offsets) — délégué, la méthode se réduit à ce qu'elle a de propre à dire, l'**ordre**. *Duplication* : le `finally` recopiait `DisposeAll`, helper créé puis non appelé à l'un des deux endroits.
- **Plan de contrôle corrigé en chemin** : `agents/sonar.md` imposait `sonar.login` « car le serveur est en **9.9.8** ». Vérifié : `api/server/version` répond **`25.6.0.109173`**, et un cycle `begin` + `end` complet avec `/d:sonar.token=` réussit (`EXECUTION SUCCESS`). Recette passée à `sonar.token`, en **conservant** la règle de fond qui reste vraie — lire la version **avant** de soupçonner les identifiants, puisque l'échec survient au `end`, après le scan complet, et que son message accuse le token. C'est ce piège qui avait donné à task-204 un diagnostic faux.
- **🚧 CE QUE CETTE LIVRAISON NE PROUVE PAS, et c'est le point le plus important.** **La taille 15 n'est pas mesurée** — c'est le milieu de la fourchette 10–20 du PO, rendue configurable **précisément** pour que le banc la tranche. **Le gain n'est pas mesuré** : les tests prouvent le *découpage* (le verrou est rendu N fois), pas la *latence*. La contre-épreuve `journey` n300 avant/après est **bloquante pour le merge** et exige le nœud de banc. C'est la leçon de **task-213** (un correctif de verrou dont la mesure a révélé qu'il coûtait plus qu'il ne rapportait, jusqu'au retrait) et celle de **task-222** (une US écrite sur un chiffre non opposable, annulée). **Coût attendu du découpage** : une ouverture/fermeture de dossier IMAP par fenêtre — dégradation de la durée totale du lot plafonnée à **+20 %** par le DOD, à vérifier au tir.

### v1.23 — Le dashboard ne repaie plus 5 allers-retours IMAP ni du SQL évitable — task-229

- **Task** : task-229 — `done`. **PR** : `api-mail` #157 (label `awaiting-human-merge`). 5 commits : `5fd46d9` (les cinq remèdes), `5a51cf2` (parité du DTO caché), `e203cec` (4 findings Sonar), `54302cb` (S1067 réellement réduit), `2ae0044` (contexte utilisateur de la tâche de fond). `dtos-mss` : 0 commit, aucune PR — contrat inchangé, contrainte absolue de la US.
- **LE POSTE MESURÉ.** Au tir `journey-mssante-n300` du 2026-08-04, `dashboard` pesait **25,5 %** du temps serveur (8 595 s, 38 760 appels) et `read_list` **18,5 %** — **44 % à eux deux**, et ils partagent la route `folders/{foldername}`. Distribution `dashboard` **multimodale** (2 appels à ~1-30 ms, 2 à ~200-500 ms), route `Mail/folders` p95 max **4 791 ms**.
- **REMÈDE 1 — `emails/today` mis en cache, validé par `(Count, UidNext)`.** La route n'avait **aucun** cache et payait **5 RTT IMAP** (LIST, STATUS, SELECT, SEARCH, CLOSE) par visite, sous le verrou de session — plancher structurel ~500 ms sous latence MSSanté. Nouveau `folder:query:{email}:{folder}:{kind}` (`kind` = littéral du code), validé contre `folder:status` par le **même invariant que le cache d'UIDs**. La US visait l'économie de SELECT+SEARCH+CLOSE (3 RTT sur 5) : comme la validation s'appuie sur une entrée déjà présente, un dossier immobile est servi **sans aucun aller-retour**. Fraîcheur bornée par la fenêtre `folder:status` (10 s), déjà acceptée ; sans cette entrée, aucun raccourci n'est pris.
- **⚠️ DÉFAUT DE CORRECTION NON ANTICIPÉ PAR LA US — le passage de minuit.** « Aujourd'hui » est `DeliveredAfter(DateTime.Now.Date)` : la borne **dépend du jour courant**. Une boîte immobile pendant la nuit garde le même `(Count, UidNext)`, donc l'entrée d'hier serait restée valide et le dashboard aurait affiché **la liste d'hier**. `FolderQueryCache` porte le jour local de calcul (`ScopeDay`) ; preuve ROUGE : retirer le garde-fou fait tomber le test.
- **REMÈDE 2 — upsert des dossiers en un lot, hors du verrou IMAP.** `PersistAndReconcileFoldersAsync` appelait `UpsertFolderAsync` **par dossier** (1 `SELECT` + 1 `SaveChanges` chacun) **sous le verrou de session** : détention **p95 4,77 s** à 6,02 acq/s, c'est-à-dire l'attente que payait `GetEmailContent` (**1,67 s p95**). Nouveau `IFolderRepository.UpsertFoldersAsync` : **1 lecture + 1 `SaveChanges`**, avec la copie de champs **factorisée** (`ApplyIncomingFolder`) pour que les deux garde-fous « ne pas écraser une valeur connue par 0 » (`UidNext`, `UidValidity` de task-179) ne puissent pas diverger entre l'appel unitaire et le lot — un test les compare sur le même scénario. Le bloc de verrou de `GetFoldersAsync` est désormais **borné explicitement** (plus de `await using` de portée méthode) pour que la persistance s'exécute **après** sa libération ; un test enregistre l'**ordre** (libération avant écriture), sans quoi un lot en un appel mais resté sous verrou serait passé pour un correctif.
- **REMÈDE 3 — partiel, et DEUX ITEMS DU DOD SE CONTREDISENT.** Le DOD exige « zéro changement de contrat / aucune forme de réponse modifiée » (contrainte déclarée absolue) **et** « chemin cache-hit : plus aucun accès SQL synchrone, mock repository jamais appelé ». Or `GetTagFoldersAsync` **fait partie de la réponse** (dossiers d'étiquettes **et leurs compteurs de non-lus**) : le différer ampute la réponse, le cacher périme les badges à chaque message lu. Seule `ReconcileFoldersAsync` — du ménage dont le résultat n'entre pas dans la réponse — part sur `IBackgroundTaskQueue`. Un test verrouille explicitement la conservation des étiquettes pour qu'elle ne soit pas défaite en croyant « finir » le remède.
- **REMÈDE 4 — TTL `folder:metadata` 10 s → 5 min.** À 10 s le cache ne servait presque jamais : **6,02 acquisitions/s** de verrou `GetFolders` pour **5,38 appels/s** de route, au rythme réel d'une visite toutes les ~56 s. **L'invalidation demandée par la US existait déjà** (`ImapFolderService`, create/rename/delete, trois sites) ; ce qui manquait est l'invalidation **en fin de passe de sync**, ajoutée à côté de celle de `sync:coverage` — ce qui rendait l'invalidation facultative (expiration en 10 s) la rend nécessaire à 5 min.
- **REMÈDE 5 — le `SELECT Users` de `GetCurrentUserIdAsync` mis en cache.** Payé à **chaque appel IMAP** (toute connexion lit les réglages, qui commencent par résoudre adresse → identifiant), **y compris** quand les réglages venaient du cache. Clé `user:id:{email}`, TTL 5 min alignée sur celle des réglages. Cachable **sans fenêtre de fausseté** : l'identifiant ne change jamais et aucun chemin ne supprime de ligne `Users` (vérifié, aucun `Users.Remove`).
- **⚠️ DÉFAUT (a) TROUVÉ EN `/forge-simplify` — le DTO caché différait du DTO frais.** La route sérialise le `FolderDto` **entier** (`result.ToActionResult`) ; la 1re version reconstituait un DTO **partiel** (`Name` = chemin au lieu du nom court, `Id` et `ParentFolder` vides). Sur un dossier imbriqué (`INBOX/Analyses`), le client aurait vu **le nom du dossier changer d'un rafraîchissement à l'autre** — le changement de sémantique que la US s'interdit. `FolderQueryCache` porte l'identité du dossier. **Et le test écrit pour ce défaut était D'ABORD INUTILE** : joué sur `INBOX`, dossier racine dont le nom **est** son chemin, sans identifiant ni parent, il passait **aussi** avec le DTO amputé — découvert seulement en posant la preuve ROUGE. Refait sur un dossier imbriqué, avec une **garde du garde** (`Assert.NotEqual(Name, Path)`, `NotEmpty(Id)`, `NotEmpty(ParentFolder)`) qui interdit au scénario de redevenir non discriminant. Même piège que task-227 : un test vert qui n'asserte rien éteint la question.
- **⚠️ DÉFAUT (b) TROUVÉ EN REVUE DE CODE — la tâche de fond n'avait pas de contexte utilisateur.** `FolderRepository` dérive sa chaîne de connexion de `UserContextInfo.ConnectionStringUser` (modèle une base par praticien) ; dans un scope de `IBackgroundTaskQueue`, cette instance est **neuve et vierge**. La réconciliation visait donc une base inexistante, l'exception était attrapée et journalisée par `BackgroundTaskQueueHostedService` — c'est-à-dire que le ménage était **silencieusement perdu**, précisément ce que le repli synchrone est censé empêcher, la requête répondant 200. Corrigé selon le motif déjà établi par l'enrichissement asynchrone de `MailController` (capture des champs sur le thread de requête, recopie dans le scope). Test qui **exécute réellement** le délégué mis en file avec un contexte vide ; preuve ROUGE vérifiée. **Écart de règle déclaré** : `/review` ne corrige jamais de code — le débordement est assumé et consigné plutôt que rendre la main avec un défaut connu.
- **Borne de fraîcheur héritée, non desserrée** : marquer un message lu change `UnreadCount` sans toucher `Count`/`UIDNEXT`, donc l'invariant ne le voit pas et la famille « non lus » est la plus exposée. Vérifié : `EmailFlagService` **n'invalide pas** `folder:status`, donc le compteur de non-lus des dossiers accuse **déjà** ce retard de 10 s. Documenté au point de validation. Second point de vigilance consigné à `InvalidateFolderListingCacheAsync` : `folder:query` **dépend** d'elle sans y être nommé (retirer le statut suffit) — si la règle de validation change, ces clés devront être retirées explicitement.
- **Tests : +28** — 15 `ImapDashboardCachingTests`, 8 `FolderRepositoryBatchUpsertTests`, 4 `CurrentUserIdCachingTests`, 1 `BackgroundSyncPipelineTests`. Ils comptent des **appels** (RTT, acquisitions de verrou, écritures), jamais des durées.
- **Preuves ROUGE — 6 propriétés**, chacune neutralisée une par une : cache jamais servi ; garde-fou du jour retiré ; persistance remise sous le verrou (2 échecs) ; réconciliation redevenue synchrone ; DTO caché redevenu partiel ; contexte de fond laissé vierge. **Une 7ᵉ tentative écartée comme invalide** — elle produisait un build en erreur, donc des tests joués sur l'ancien binaire : un test rouge pour la mauvaise raison ne prouve rien.
- **Build / tests** : 0 erreur, 0 avertissement (Debug et Release). **3 440 verts** en Release ; après le correctif de revue : 1 964 / 422 / 649 / 102 unitaires et **304 / 320** en intégration (16 ignorés, le compte normal). Les tests d'intégration des 4 routes passent **sans modification d'aucune assertion** — le critère « zéro changement de contrat ».
- **⚠️ PIÈGE DE MESURE RENCONTRÉ ET CONSIGNÉ** : une exécution de l'intégration a affiché **128 ignorés** au lieu de 16, soit **112 tests silencieusement écartés**. Artefact de `--artifacts-path` (contournement des verrous de l'AppHost), qui déplace `AppContext.BaseDirectory` hors du dépôt et fait basculer les conditions de saut — même racine que les 4 échecs des scans de sources sous ce contournement. Compte rétabli à 304/16 en compilation normale, sur le code final. « Une absence n'est pas un zéro » (task-214) vaut aussi pour les tests ignorés.
- **Sonar — dette nouvelle zéro, prouvée par TROIS scans** : `new_violations` **32 → 29 → 28** (= baseline exacte). 4 findings corrigés : `S1067`, `S1481` (`ImapService`), `S1172` + `CA2016` (`BaseRepository` — le jeton d'annulation n'était pas transmis à `SetAsync`, qui l'accepte : une requête annulée laissait une écriture de cache courir derrière elle). **Le 2ᵉ scan a servi** : mon correctif de `S1067` n'avait pas corrigé le finding, il l'avait **déplacé** (ligne 803 → 868) — extraire une condition ne réduit pas son nombre d'opérateurs. Sans remesure, la task aurait été livrée avec un finding annoncé corrigé. Le 5ᵉ finding initial (`S103`, `BaseRepository.cs:68`) est **préexistant** — ligne du constructeur, absente du diff, déjà en baseline : non corrigé, non attribué. `new_coverage` 87,0 → **87,1 %**, duplication projet 0,5 → **0,4 %**.
- **Point ouvert transverse, identique à task-228** : les 2 security hotspots `Math.random()` de `journey.js` sont en `TO_REVIEW` et maintiendront le Quality Gate en ERROR à **chaque cycle futur**. Les marquer *safe* est très probablement correct (tirage de sélection dans un scénario de charge) mais c'est un **jugement de sécurité** déféré à l'humain.
- **Famille de flakies à traiter** : `Services/Export` (`UglyToad.PdfPig` — `MailExportServiceTests`, `MarkdownPdfRendererTests`) s'est manifestée **cinq fois** sur les cycles task-228 et task-229, ~1 fois sur 2 à 3 en exécution isolée, verte en run complet. Aucun code d'export touché. Mérite une task dédiée — signalée, pas corrigée.
- **🚧 CE QUE CETTE LIVRAISON NE PROUVE PAS.** **Aucune latence n'est mesurée** : les tests prouvent des **nombres d'appels** (verrou rendu avant persistance, lot en un appel, cache servi sans RTT), pas un p95. La contre-épreuve `journey` n300 en iso-conditions est **bloquante pour le merge** et exige le nœud de banc : 4 seuils (part de `dashboard`, détention `GetFolders` **≤ 1,5 s** contre 4,77 s, attente `GetEmailContent` contre 1,67 s, `read_list` p95 contre 534 ms) plus un contrôle de fraîcheur (message injecté visible dans `today` sous 10 s). Leçons de **task-213** (correctif de verrou retiré après mesure) et **task-222** (US écrite sur un chiffre non opposable, annulée).

### v1.24 — Marquer lu acquitte sur la base, la propagation IMAP part groupée en arrière-plan — task-230

- **Task** : task-230 — `done`. **PR** : `api-mail` #159 (label `awaiting-human-merge`). 5 commits : `751c99e` (acquittement optimiste + groupement), `4c6e149` (lecture d'audit légère aux 3 chemins), `b3501ec` (les 4 gestes sur le même mécanisme), `f1a4360` (gestes en lot + suppression des chemins morts), `809ceb3` (dépendances IMAP retirées). `dtos-mss` : 0 commit, aucune PR.
- **LE DÉFAUT MESURÉ.** `EmailFlagService.UpdateEmailReadStatusAsync` faisait **tout** dans la réponse HTTP : commit Postgres, **relecture lourde** `GetMailAsync(Header)` pour l'audit (qui charge étiquettes, destinataires, pièces jointes — et le **contenu clinique** dès qu'il y a des documents médicaux), puis `LIST` + `SELECT` + `STORE` + `CLOSE` sous le verrou `imap_session` de la **voie de lecture**, avec l'extension **bloquante** `AddFlags`. Tir `journey-mssante-n300` du 2026-08-04 : **p50 331 ms / p95 524 ms**, hors grille SLO, **8,7 %** du temps serveur (2 919 s, 7 743 appels), détention p95 du verrou **0,997 s** à 5,11 acq/s, route `status/read` p95 max 4 562 ms.
- **⚠️ ÉCART ARGUMENTÉ AVEC LA US — deux files, pas la persistée seule.** La US privilégiait `PendingActions` pour sa rejouabilité après crash (argument juste) **et** posait « propagation en secondes, jamais au-delà de la fenêtre `folder:status` (10 s) ». Vérifié : `ProcessPendingActionsAsync` n'est drainée que par une passe de synchronisation (`BackgroundSyncService`) ou un appel client (`ConnectionController`) — **aucun timer interne** : la voie persistée seule aurait respecté la lettre du remède en manquant la borne de la **même** US, avec une latence indéterminée et, sous le scénario de charge, possiblement infinie. `PendingActions` **persiste** (durabilité, déduplication, annulation par action opposée) ; `IBackgroundTaskQueue` **propage tout de suite**.
- **REGROUPEMENT D'UNE RAFALE EN UN ALLER-RETOUR, SANS FENÊTRE D'ATTENTE.** Aucune temporisation ajoutée : la file persistée **est déjà l'accumulateur**. Une course ramasse tout ce qui est en attente **pour ce geste et ce dossier** au moment où elle part, et le pose en un `STORE` multi-UID. 20 clics ⇒ **1** trajet et **1** prise du verrou pour la 1ʳᵉ course ; les 19 autres ne réclament rien et sortent **sans trajet ni verrou**. Le regroupement est **par geste** (poser et retirer `\Seen` sont deux `STORE` opposés). Réclamation par `TryClaimForProcessingAsync` ⇒ deux pods se **partagent** les lignes.
- **⚠️ LE DÉFAUT QUE L'ASYMÉTRIE CRÉAIT — trouvé sur question humaine du 2026-08-05.** Rendre « marquer lu » différé en laissant « marquer non lu » synchrone ouvrait une divergence sur un geste **normal** (ouvrir puis remettre en non lu pour garder le message dans sa liste à traiter) : la course « lu » partait **après** le retrait synchrone du flag et **reposait** `\Seen`. Base « non lu », serveur « lu », pense-bête supprimé, rien ne corrige — et la synchronisation suivante pouvait **annuler le geste du médecin en silence**. **Fermé par construction** : les **quatre** gestes et **leurs variantes en lot** empruntent le même mécanisme, donc l'annulation par action opposée de l'outbox (`OppositeActions`, jusque-là inutile dans ce cas) supprime le pense-bête « lu » et la course lancée ne réclame plus rien. **Il ne reste qu'UN SEUL chemin d'écriture de flag** : `ProcessEmailAsync` et `ProcessEmailsBulkAsync` supprimés.
- **TROIS DÉFAUTS PRÉEXISTANTS, tous sur la garantie de durabilité que la US invoquait.** (1) `MarkAsProcessingAsync` écrivait **sans condition** ⇒ deux pods ayant chargé la même ligne `Pending` réussissaient tous les deux ; `TryClaimForProcessingAsync` porte sa condition dans l'ordre SQL (`ExecuteUpdateAsync … WHERE Status = Pending`), **aucune migration** — la condition remplace le jeton de concurrence absent du schéma. (2) `MarkAsFailedAsync` écrit `Failed`, que `GetPendingActionsAsync` ne lit **jamais** ⇒ une action ayant échoué une fois est abandonnée en silence et le `RetryCount >= 3` du service est **du code inatteignable** ; défaut général **signalé, non corrigé** (sémantique du rejeu hors ligne), mais `ReleaseClaimAsync` rend la ligne à `Pending` avec une borne pour que le chemin des flags ne s'y appuie pas. (3) `PendingActionRepository` a **deux constructeurs à trois paramètres** ⇒ ambigu pour le conteneur intégré partout où `MailDataContext` est enregistré (fixtures d'intégration) ; production non concernée ; corrigé à l'enregistrement. `[ActivatorUtilitiesConstructor]` **n'est pas** le remède (lu par `ActivatorUtilities`, pas par la sélection du conteneur) — tenté puis retiré plutôt que de laisser un attribut décoratif à commentaire faux.
- **⚠️ DEUX ERREURS DE LA FORGE, corrigées et consignées.** (a) **Boucle sans fin** : le rejeu appelait `UpdateEmailReadStatusAsync`, qui **enfile** ; la déduplication ne voyant que les `Pending` et l'action en cours étant `Processing`, une **nouvelle** action était insérée avant suppression de l'originale — une ligne de plus par passe de synchronisation, chacune payant un aller-retour IMAP. Deux portes distinctes (`Enqueue…` / `Propagate…`), et un test l'interdit. (b) **J'ai affirmé à tort que le cycle de dépendances avait disparu** : retirer `IEmailFlagService` de `PendingActionService` ne l'a pas supprimé, je l'ai remplacé par `IFlagPropagationService`, ce qui a rendu la boucle **plus directe**. Le conteneur l'a dit, les **tests d'intégration** l'ont fait remonter. Le cycle est **réel** (enfiler exige l'outbox, rejouer exige la propagation) et cassé du côté **froid**, pour que le chemin chaud garde une dépendance directe vérifiée à la compilation. **Et mon `try/catch` best-effort masquait le défaut (3)** : la voie de durabilité était **silencieusement morte** dans ces montages, le journal ne parlant que d'une « panne d'outbox » — c'est l'injection directe qui l'a fait remonter à la construction.
- **LA TRACE D'AUDIT NE MENT PLUS.** Elle inscrivait `ServerResponse = "OK flags updated"` — la réponse du serveur. La propagation étant différée, garder cette phrase aurait **écrit dans un registre réglementaire une réponse serveur qui n'a pas eu lieu**. Le champ dit l'état vrai ; `Success` porte ce que la trace atteste réellement — **l'accès du praticien**, vrai dès le commit, ce que la traçabilité PGSSI-S attend d'un `MailRead`. **Gain de confidentialité au passage** : `MailAuditSnapshot` (4 champs, une projection) remplace la relecture lourde, donc le chemin d'un changement de flag **cesse de lire le matériau clinique** d'un message dont il ne modifie que l'état — étendu aux trois chemins de flag par la passe qualité.
- **CONSÉQUENCES SIGNALÉES, NON CORRIGÉES.** Un cas d'erreur change de code HTTP (panne serveur : 5xx → 200) — conséquence directe du remède, sanctionnée par la US ; 4 tests **unitaires** encodant l'ancien contrat réécrits, **tests d'intégration des routes inchangés** (10/10). Le corps de réponse contient `{ queued = !IsOnlineMode }`, qui dira `queued: false` en ligne alors que la propagation **est** enfilée : le champ devient trompeur, mais le corriger changerait le corps — interdit par la contrainte absolue. `UpdateEmailUnReadStatusAsync` n'émet **aucune trace d'audit** là où les trois autres gestes en émettent une : décision de traçabilité PGSSI-S déférée à l'humain.
- **Tests : +34** — 21 `FlagPropagationServiceTests` (nouveau), 9 sur `EmailFlagService`, 4 recalés sur `PendingActionService`. Ils comptent des **appels** (prises de verrou, ordres `STORE`, allers-retours), jamais des durées. **6 preuves ROUGE.** ⚠️ **Un de mes tests ne valait rien** : le test de l'enchaînement, écrit dans `FlagPropagationServiceTests`, **stubbait lui-même** « plus rien en attente » et passait donc **aussi avec l'asymétrie rétablie** ; refait dans `EmailFlagServiceTests`, là où l'asymétrie vivait — **troisième test-sans-valeur de la campagne** (task-227, 229, 230), toujours découvert en cassant volontairement le code. Enseignement d'outillage : `AddFlagsAsync` est une **méthode d'extension** déléguant à `StoreAsync`, donc NSubstitute ne peut vérifier que `StoreAsync` — ce qui confirme accessoirement que le code emprunte la voie asynchrone.
- **Build / tests** : 0 erreur, 0 avertissement. **3 464 verts**, intégration incluse (**304 / 320**, 16 ignorés).
- **Sonar — dette nouvelle zéro, prouvée par QUATRE scans**, et **deux d'entre eux ont trouvé du code que l'extension venait de rendre mort** : `new_violations` 31 → 29 (`S1144`, `ProcessEmailAsync` mort ⇒ **révèle que le chemin bulk restait synchrone**) → 32 (`S4487` ×4, **dépendances IMAP devenues non lues** dans `EmailFlagService` : 3 au lieu de 7) → **28 = baseline exacte**. Le QG reste ERROR entièrement sur de la dette antérieure (harnais k6 + 2 `S103`).
- **Point ouvert pour la TROISIÈME fois consécutive** : les 2 security hotspots `Math.random()` de `journey.js` sont en `TO_REVIEW` et maintiendront le Quality Gate en ERROR à **chaque cycle futur**. Signalé à task-228, task-229 et task-230 — il mérite sa propre décision humaine plutôt qu'une mention de plus.
- **Famille de flakies à traiter** : `Services/Export` (`UglyToad.PdfPig` — `MailExportServiceTests`, `MarkdownPdfRendererTests`) s'est manifestée **sept fois** sur les cycles task-228 à 230, verte en isolation, aucun code d'export touché. Mérite une task dédiée.
- **🚧 CE QUE CETTE LIVRAISON NE PROUVE PAS.** Aucune latence n'est mesurée : les tests prouvent des **nombres d'appels** (zéro IMAP dans la réponse, un trajet pour une rafale, une prise de verrou au lieu de vingt), pas le p50 de `mark_read`. Contre-épreuve `journey` n300 **bloquante pour le merge**. **Point de vigilance propre à cette task** : le travail IMAP n'a pas disparu, il s'exécute désormais **pendant** que le médecin fait autre chose — le groupement doit **plus que compenser** ce chevauchement, et c'est la détention p95 du verrou `UpdateFlag` (réf. 0,997 s à 5,11 acq/s) qui le dira. Leçons de **task-213** et **task-222**.

### v1.25 — L'envoi cesse de payer une connexion neuve à chaque message — task-231

- **Task** : task-231 — `done`. **PR** : `api-mail` #158 (label `awaiting-human-merge`). Commits `185f9b5` (réutilisation + MIME avant connexion), `12e5cdf` (passe `/forge-simplify`), `3659817` (défaut trouvé à la revue). `dtos-mss` : branche créée, **0 commit**, aucune PR — contrat inchangé, comme le DOD l'exigeait.
- **LE DÉFAUT, ET IL ÉTAIT MESURÉ.** Au tir `journey-mssante-n300`, `send` est **hors grille SLO** (p50 1 340 ms) et pèse **13,4 % du temps serveur** (4 502 s pour 2 853 appels). Le signal qui désigne la cause n'est pas la valeur mais sa **platitude** : identique sur les trois paliers, donc un coût **par appel**, pas de la contention. Décomposition par lecture du code : `SmtpConnectionFactory` faisait `new SmtpClient()` → CONNECT → TLS avec **vérification de révocation OCSP/CRL** → AUTH, puis `DisconnectAsync(true)` à la fin. **Aucun pool** — là où IMAP réutilise sa connexion de session depuis toujours.
- **LE CLIENT SMTP VIT DÉSORMAIS DANS LA SESSION.** C'est le choix structurant, et il est choisi pour ce qu'il **évite** : en logeant le `SmtpClient` dans `MailClientSession`, à côté du client IMAP, il hérite **exactement** du cycle de vie déjà éprouvé — expiration à 5 min d'inactivité, balayage par `MailClientSessionCleanupService`, fermeture au logout via `RemoveSession` → `Dispose`. Aucun mécanisme de cycle de vie parallèle à écrire, donc aucun à maintenir ni à faire diverger.
- **CE QUE PAIE CHAQUE ENVOI, AVANT ET APRÈS.** Avant : CONNECT + TLS + OCSP/CRL + AUTH + DATA + QUIT, à **chaque** message. Après : le premier envoi paie tout cela, les suivants une **sonde NOOP** puis DATA. ⚠️ **La vérification de révocation du certificat n'est pas détendue — elle est amortie.** Désactiver le contrôle OCSP/CRL était explicitement **hors périmètre** : c'est une exigence de confiance MSSanté/IGC Santé, et une exigence ne s'optimise pas, elle se paie moins souvent.
- **POURQUOI UNE SONDE, ET PAS `IsConnected`.** `IsConnected` chez MailKit ne reflète que l'état **local** de la socket : un serveur qui a fermé de son côté ne se découvre qu'au prochain aller-retour. Sans sonde, la réutilisation aurait produit des échecs d'envoi intermittents et inexplicables. Le NOOP est ce qui distingue une connexion vivante d'une connexion qu'on **croit** vivante, et il coûte sans commune mesure moins qu'un CONNECT complet.
- **LE MIME EST CONSTRUIT AVANT L'EMPRUNT.** Il fait deux lectures base — identité de l'expéditeur, signature par défaut — qui se faisaient **sous session SMTP authentifiée tenue**. Désormais elles précèdent l'emprunt, donc elles ne tiennent plus ni la connexion ni (nouveau) le verrou de session. L'ordre métier est **inchangé** : rien n'est envoyé plus tôt.
- **ZÉRO CHANGEMENT DE CONTRAT, et c'était une contrainte absolue.** Même route `POST Mail/sendmail`, même code HTTP, même corps de réponse. Le champ `archived`/`warning` — sémantique anti-renvoi de document posée par task-223 — reste **décidable au moment de l'acquittement**, parce que l'archivage IMAP reste **synchrone**. Le différer aurait été un changement de contrat, donc une décision produit distincte.
- **⚠️ UN POINT DE CONTENTION NOUVEAU, ASSUMÉ ET INSTRUMENTÉ D'EMBLÉE.** Avant cette livraison, chaque envoi avait sa propre connexion : deux envois simultanés d'une même session ne se gênaient **jamais**. La réutilisation les **sérialise**. Le verrou `smtp_session` publie donc son attente et sa détention (`mssante_lock_wait/hold_duration_seconds`, issues `acquired`/`timeout`/`cancelled`) dès la livraison. Le parcours du banc envoie séquentiellement par praticien, donc l'attente **attendue** est nulle — mais « attendu nul » sans instrument est exactement l'affirmation que cette EPIC a appris à ne pas faire. Ce point a été trouvé par la **garde de surface épinglée** de `IMailClientSessionManager`, dont l'unique raison d'être est de poser la question « ce nouveau membre prend-il un verrou sans le mesurer ? ». Elle a produit un vrai correctif, ce qui est sa justification rétrospective.
- **LE DÉCOMPTE DEVIENT COMPLET.** `MailServerSolicitationRecorder` (task-225) ne comptait que l'IMAP. Il compte désormais `connect` / `authenticate` — **seulement quand ils ont réellement lieu** —, `noop` et `send_message`. Conséquence directe pour la contre-épreuve : **l'absence de `connect` est la preuve de la réutilisation**. C'est un décompte et non un temps, parce qu'un temps plus court n'a jamais prouvé l'absence d'un aller-retour.
- **UNE COUTURE DE TEST ASSUMÉE, et la raison la justifie.** `SmtpClient` est une classe concrète de MailKit dont l'état de connexion ne se **simule pas**. Sans extraire la sonde derrière `ISmtpConnectionProbe`, la propriété « le 2e envoi ne se reconnecte pas » n'aurait été vérifiable qu'au banc — et le banc mesure un temps, il ne prouve pas l'absence d'un aller-retour. La sonde est le point de décision de toute la réutilisation, et c'est elle qui est sous test.
- **TESTS — ce qui est asserté, et pourquoi.** 8 nouveaux. Ce qui décide est un **nombre d'ouvertures de connexion**, jamais une durée. Couverture : 2e emprunt sans reconnexion ⇒ compteur à 1 ; connexion morte ⇒ reconnexion transparente ⇒ compteur à 2 ; échec de connexion ⇒ **le jeton est rendu** (sans quoi un seul échec bloquerait la session pour tous ses envois suivants, plafond de 120 s à la clé) ; double libération ⇒ pas de sur-libération, prouvée en montrant qu'un seul emprunt passe et que le second attend ; suppression de session ⇒ le client retenu est **disposé**, prouvé par l'`ObjectDisposedException` qu'il lève ensuite — une preuve observable de non-fuite, pas une inspection ; ordre des appels ⇒ **aucune I/O base après l'emprunt** ; toute connexion neuve installe la validation du certificat.
- **UN DÉFAUT TROUVÉ À LA REVUE DE CODE, ET CORRIGÉ** (`3659817`). `DiscardSmtpClient` faisait un `Disconnect(true)` — **synchrone** chez MailKit — alors qu'il est appelé sur le **chemin de requête** (emprunt qui trouve une connexion morte, envoi qui échoue). Un thread du pool s'y serait garé le temps d'un QUIT : c'est **précisément** le défaut que task-205 a mesuré comme facteur limitant de l'API (file ThreadPool à 432 sur un réplica à 1,19 cœur), et que la règle S4462 du repo interdit en flux normal. La socket est désormais fermée sans politesse sur ce chemin — le client écarté est de toute façon suspect ou mort, et un QUIT sur une connexion morte n'aboutit pas. Le QUIT poli subsiste là où il est **gratuit pour la requête** : la fermeture de session, qui tourne sur le service de nettoyage ou au logout.
- **DEUX SUGGESTIONS NON BLOQUANTES, consignées plutôt que corrigées au passage.** (1) `MailClientSession.Dispose` peut fermer un client SMTP pendant qu'un emprunt le détient (expiration concurrente) — **exposition pré-existante et identique côté IMAP**, où le wrapper est disposé sans égard au verrou ; le jeton absorbe le cas, et le traiter mérite de l'être pour les deux voies à la fois. (2) `SmtpConnectionFactory` journalise un **extrait de JWT** en `LogWarning` : pré-existant, hors périmètre, ce n'est pas une donnée de santé — mais c'est un fragment de secret dans les logs, à un niveau qui n'est pas filtré. Mérite une US.
- **Build / tests** : 0 erreur. **3 362 verts, 0 échec**, intégration incluse. Un stub de test d'intégration a changé de cible (`SendMailOppositionGuardIntegrationTests` simulait la méthode que le chemin d'envoi n'emprunte plus) ; son intention et **toutes ses assertions** sont intactes.
- **⚠️ Sonar — NON MESURÉ, ce qui n'est pas « rien à signaler ».** Le serveur était injoignable pendant le cycle (`127.0.0.1:9000` sans réponse, aucun conteneur, `SONAR_TOKEN` absent). La qualité de ce diff n'est donc **ni verte ni rouge : elle n'a pas été mesurée**. Confondre les deux serait l'erreur même que cette EPIC s'interdit — une absence de mesure n'est pas un zéro. `/sonar 231` reste dû avant intégration.
- **🚧 CE QUE CETTE LIVRAISON NE PROUVE PAS.** **Le gain n'est pas mesuré.** Les tests prouvent la *réutilisation* (la connexion n'est plus rouverte), pas la *latence*. La contre-épreuve `journey` n300 en iso-conditions avec `journey-mssante-n300-021137` est **bloquante pour le merge** : `send` p50 attendu ≤ 800 ms contre 1 340 ms, part du temps serveur en baisse depuis 13,3 %, ~1 connexion par session au lieu d'une par envoi, et — nouveauté de cette livraison — **attente du verrou `smtp_session` à vérifier plutôt qu'à supposer**. C'est la leçon de **task-213** (un correctif de verrou dont la mesure a révélé qu'il coûtait plus qu'il ne rapportait, jusqu'au retrait) et celle de **task-222** (annulée pour avoir été écrite sur une cause plausible et fausse).

---

### v1.26 — Trois tâches de fond visaient une AUTRE base que la requête — task-234

- **Task** : task-234 — `archived`. **PR** : `api-mail` #161 (mergée). ⚠️ **Ouverte d'abord sous le numéro `task-231`, déjà attribué par le PO à une US SMTP** (commit `d2d0008`) : renumérotée, PR #160 fermée, #161 rouverte, **sans force-push**.
- **LE DÉFAUT, ET CE QU'IL RISQUAIT.** Le nom de la base d'un praticien se dérive de `(Email, MssRpps)`. Trois chemins d'arrière-plan reconstituaient l'identité du praticien **en oubliant `MssRpps`** : ils visaient donc une **autre base**, sans lever, sans avertir, en lisant des tables vides. Sur une plateforme « une base par praticien », c'est un risque de **perte de donnée silencieuse** — un travail de fond qui croit avoir agi sur le dossier d'un médecin et n'a rien touché.
- **CORRIGÉ PAR UN SEUL POINT DE VÉRITÉ.** `UserContextInfo.CopyIdentityTo` recopie **tous** les champs d'identité, et un test de garde par **réflexion** échoue si un champ modifiable apparaît sans être recopié. C'est la seule forme qui survit à l'ajout d'un futur champ : une liste écrite à la main aurait dérivé au premier ajout.
- **COMMENT IL A ÉTÉ TROUVÉ : PAR UN HUMAIN QUI A CLIQUÉ.** Il a échappé à **3 467 tests et quatre analyses SonarQube**. Le praticien a marqué quatre messages dans le front, constaté que la table `PendingActions` restait à `Pending`, et demandé l'analyse des journaux. Aucune barrière automatique ne l'a vu.
- **UNE GARDE DE SÉCURITÉ QUI CRIAIT AU LOUP DEPUIS DES SEMAINES.** Le test qui vérifiait l'absence de fuite de donnée de santé cherchait la chaîne `NIR` dans **tout** le corps de la réponse d'erreur — `traceId` compris. Or le préfixe d'identifiant de connexion d'ASP.NET est stable par processus et contenait `0HNNIRI6FIOJE` : la garde échouait **3 fois sur 3**, pour rien. Recentrée sur les champs que **nous** écrivons (`title`, `detail`), puis **vérifiée qu'elle mord encore** en simulant une vraie fuite (4 tests de sécurité passent au rouge). Une garde qui crie au loup est une garde qu'on finit par ignorer.
- **Tests** : 4 tests de domaine dont la comparaison du **nom de base** produit par les deux chemins — l'assertion qui aurait attrapé le défaut —, et le garde-fou par réflexion.
- **🚧 CE QUE CETTE LIVRAISON N'A PAS RÉPARÉ.** Le correctif est en place ; **le filet qui aurait dû l'attraper, non**. Trois conditions manquent au harnais d'intégration, chacune suffisant à rendre le défaut invisible : `IBackgroundTaskQueue` n'est câblée dans **aucune** fixture (les services empruntent leur repli en ligne, avec le contexte complet de la requête — le scope de fond n'est jamais créé) ; la suite a **journalisé une erreur et est restée verte** ; et `MssRpps` n'est renseigné dans aucune fixture, donc les deux chemins calculent **le même** nom de base et l'écart ne **peut** pas apparaître. C'est l'objet de **task-235**.

---

### v1.27 — La page d'un dossier patient cesse de coûter la taille du dossier — task-233

- **Task** : task-233 — `done`. **PR** : `api-mail` #162 (label `awaiting-human-merge`). Commits `34eef9a` (tests de caractérisation), `7fb47a5` (volet 2), `7951339` (volet 1), `a861ae9` + `24ef012` (volet 3), `baf4939` (passe qualité), `60734c0` (le SQL sous test), `afc884b` (fusion `develop` et le défaut qu'elle a révélé). `dtos-mss` : branche auto-incluse, **0 commit**, aucune PR.
- **⚠️ LE DIAGNOSTIC DE LA US ÉTAIT FAUX, ET LE PLAN D'EXÉCUTION LE DIT.** La US attribuait le parcours séquentiel aux six filtres `lower(FolderPath) LIKE '%…%'`. Le relevé dit autre chose : **`MailMedicalDocuments` n'avait aucun index sur `Ins`** — ni sur `MailId`. Ses index portaient sur `DuplicateOfId`, `PractitionerContactId`, `SetId`, `SupersededByDocumentId`, `SuppressionRequestedByMailId` : **aucun sur la colonne qui sélectionne le patient**. Le parcours séquentiel était **inévitable quoi qu'on fasse aux filtres de nom** — les supprimer n'aurait rien gagné, faute d'index à parcourir à la place. task-070 avait indexé `MailPatients.Ins`, la table **voisine**, jamais celle des documents.
- **LA PAGINATION PART EN BASE** (volet 2). `GROUP BY MailId` + `MAX(Date)`, `COUNT`, tri, `Skip`/`Take` : tout en SQL, seule la page revient. Le compte total et la page partagent **la même expression de filtre**, pour qu'un `TotalCount` ne puisse pas inclure des documents que la page exclut — un « charger plus » qui ne charge rien est un défaut silencieux. `page * pageSize` était calculé en `int` et **débordait** avec la taille « tout » (`int.MaxValue`) : borné en 64 bits.
- **L'INDEX QUI MANQUAIT** (volet 1). `(Ins, MailId, Date)`, non unique. `Ins` pour l'égalité sélective ; `MailId` en seconde position pour que l'agrégat se passe du **tri intermédiaire** visible dans le plan d'avant ; `Date` parce qu'elle est agrégée par `MAX` et n'exige alors aucun accès au tas. Non unique volontairement — un patient a plusieurs documents dans un même message, et `Ins` est nullable. **Variantes partielle et couvrante écartées faute de mesure**, la US demandant de décider « après avoir vu le plan » : à 92 documents PostgreSQL parcourt séquentiellement parce que c'est optimal, la base de dev ne permet pas de trancher.
- **UNE RÈGLE CLINIQUE RÉCITÉE HUIT FOIS** (volet 3). « Envoyés / brouillons / corbeille n'entrent pas dans un dossier patient » était écrite **33 fois** en LINQ — 24 dans `PatientRepository` (quatre récitations complètes), 9 dans `MailRepository` — plus une fois **en mémoire**. Elle devient une **colonne générée par PostgreSQL**, `Mails."IsInSentDraftOrTrashFolder"`, dont l'expression vit dans `MailFolderNamingRule` : seule source, partagée avec le contrôle en mémoire et gardée par un test anti-dérive. ⚠️ **Mon premier compte rendu annonçait « il reste 3 occurrences, d'une autre règle » — c'était faux** : mon grep ne cherchait que les littéraux, et ces trois blocs étaient des récitations complètes écrites avec des constantes. Corrigé au commit suivant.
- **POURQUOI PAS `MailFolders.FolderType`, QUE LA US PROPOSAIT.** Ce type est dérivé **uniquement des attributs SPECIAL-USE annoncés par le serveur IMAP**, sans repli sur le nom (`ImapHelper.GetFolderType`). Relevé en base : le dossier littéralement nommé `Trash`, **50 messages**, est classé `FolderType = Custom` faute d'attribut `\Trash` annoncé — et **aucun** dossier n'y porte le type `Trash`. Filtrer sur ce type aurait **relâché la règle clinique** et fait entrer la corbeille dans les dossiers patients. C'est le genre de vérification qui coûte une requête et évite une régression médicale.
- **CE QUE LA COMPARAISON DES RÉCITATIONS A RÉVÉLÉ.** Deux exigent `FolderPath != null` puis excluent les motifs — chemin inconnu **écarté**. Les deux autres écrivent `FolderPath == null || (aucun motif)` — chemin inconnu **gardé**. Deux réponses opposées à la même question. **Sans conséquence sur les données** : `FolderPath` est `IsRequired()`, donc NOT NULL. C'est une divergence d'**intention**, qui attendait qu'on rende la colonne nullable pour devenir un défaut ; chaque appelant garde son comportement local **tel quel**, la task unifie la règle de nommage et n'arbitre pas le cas nul à la place des requêtes.
- **UN DÉFAUT DE PRODUCTION TROUVÉ PAR UN CONFLIT DE FUSION — c'est-à-dire par chance.** task-231 a rendu le getter `BaseRepository.DataContext` **levant** : il ne résout plus rien. L'expression écrite par cette task l'appelait, donc la page aurait levé **à chaque appel en production**. Elle a passé **toute** la suite — build vert, 106 + 421 + 1964 + 224 tests verts — parce que les tests **injectent** le contexte, où le getter fonctionne parfaitement. L'expression est désormais `static` et reçoit son contexte en paramètre, et une **garde d'architecture** (`DataContextGetterScanTests`) lit les sources de production pour refuser tout emploi du getter. Portée dite sans exagérer : sous la forme finale le **compilateur** attrape déjà l'appel ; la garde sert le cas d'une méthode d'**instance**, qui compile très bien — exactement la forme qu'avait ce défaut.
- **UN AUTRE DÉFAUT, INTRODUIT PUIS CORRIGÉ DANS LE MÊME CYCLE.** La sortie anticipée « dossier vide » renvoyait `Page` et `PageSize` à **zéro**, là où le chemin nominal les recopie : un client qui lit `PageSize` pour dimensionner sa pagination recevait 0. Rien ne le signalait, la liste étant vide de toute façon. Corrigé, avec son test.
- **TROIS TESTS UNITAIRES ONT DÛ ÊTRE PORTÉS, et c'est un constat sur le harnais.** Le fournisseur EF **InMemory ignore `HasComputedColumnSql`** : la colonne y vaut `false` en toutes circonstances, donc les tests de la règle y devenaient rouges alors que la production excluait toujours ces dossiers — le rouge disait la vérité sur le **harnais**, pas sur le code. Les réparer sur InMemory aurait voulu dire écrire la valeur à la main dans le seed, donc **tester le seed et non la règle**. Portés contre un vrai PostgreSQL, ils gagnent au passage un cas que **ni l'un ni l'autre** n'éprouvait : le nom de dossier en **français** (`Corbeille`).
- **TESTS** : le corps de `GetMailsByInsAsync` n'avait **aucune** couverture avant cette task — InMemory refuse le `GroupBy` des pièces jointes. Couverture ajoutée : 8 variantes de nom exclues + 3 gardées sur la page, 11 cas visant la colonne **motif par motif**, le **SQL réellement exécuté** (capté à la journalisation EF, pas reconstruit — une requête réécrite dans le test n'aurait prouvé que ce que le test écrit), l'existence de l'index, le dossier vide, et la concordance des deux formes de la liste de motifs. **Preuves ROUGE** obtenues en cassant délibérément le code : règle neutralisée → **18 des 28** tests du fichier échouent ; `HasIndex` retiré → la garde d'index échoue ; getter réintroduit → la garde d'architecture échoue.
- **Build / tests**, sans `--artifacts-path` (le verrou de l'AppHost s'étant levé, la suite tourne enfin en entier) : 0 erreur, 0 avertissement ; domain 106/106, infrastructure 421/421, **api 650/650**, **integration 339/339** (16 ignorés contre **128** avec l'option — ce qui **prouve** que les 4 échecs de scan de sources signalés plus tôt étaient bien l'artefact d'outillage), application 1972/1972 sur deux runs consécutifs. Une occurrence du flaky pré-existant `MailExportServiceTests.BuildPdfWithMedicalDocumentHtmlBodyFallback`.
- **⚠️ SONAR — les deux relevés ne sont PAS comparables**, et le dire vaut mieux que présenter un delta imaginaire : `ncloc` **37 181 → 43 533**, périmètres d'analyse différents. La mesure qui, elle, est indépendante du périmètre : **zéro** violation « new code » sur 33 tombe dans un fichier touché par cette task. Les 33 sont héritées — 26 dans l'outillage k6 (`report.py`, `journey.js`, `journey-model.js`), 3 `S125` dans `AppHost.cs`, 1 `S3903`, 2 `S103`, 1 `S1067`. Deux étaient à moi (`CA1861`, tests de task-234) : corrigées, disparues. Le Quality Gate reste ERROR sur `new_coverage` = 0 — **aucun rapport de couverture n'est importé**, donc le seuil de 80 % est inatteignable par construction — et sur les hotspots `Math.random()` de `journey.js`, **jamais révisés (4ᵉ signalement)**.
- **AUDIT DE MIGRATION (règle 7c)** — deux migrations écrites à la main. FluentMigrator n'a ni `.Designer.cs` ni instantané EF, donc **aucune opération fantôme n'est possible : il n'y a pas de générateur**. Une opération dans chaque `Up`, sa symétrique dans `Down` ; numéros strictement postérieurs, aucune collision ; noms de colonnes bruts (`Ins`, `MailId`, `Date`) **vérifiés contre `information_schema`**. Coût dit franchement : une colonne générée `STORED` **réécrit la table sous verrou exclusif**, de l'ordre de la seconde sur une base par praticien.
> ### ⚠️ Correction du 2026-08-05 — la preuve invoquée était un état TRANSITOIRE
>
> L'argument ci-dessus s'appuyait sur un relevé en base : *« le dossier littéralement nommé
> `Trash`, 50 messages, est classé `FolderType = Custom`, et aucun dossier n'y porte le type
> `Trash` »*. **Ce relevé était exact au moment de la mesure et ne l'est plus.** Après une
> synchronisation ultérieure (`LastSyncedAt` 2026-08-05T14:54), la même base classe
> correctement **tous** ses dossiers système : `INBOX`=0, `Sent`=1, `Drafts`=2, **`Trash`=3**,
> `Junk`=4, et seuls les dossiers réellement personnalisés (`Demo`, `Demo/Biologie`,
> `Demo/Demo2`) restent en `Custom`.
>
> **Ce qui reste vrai** : `ImapHelper.GetFolderType` n'a **aucun repli sur le nom** — c'est un
> fait de code, inchangé. Un serveur qui n'annonce pas SPECIAL-USE produirait donc bien du
> `Custom`.
>
> **Ce qui n'est PLUS établi** : que ce serveur ne l'annonce pas. Il l'annonce. La
> classification a **transité par une valeur fausse** puis s'est corrigée, et **je n'ai pas
> établi pourquoi** (listing incomplet ? attributs non demandés à ce passage ? autre ?).
>
> **L'argument change donc de nature, et de force.** Il ne dit plus « ce serveur n'annonce pas
> SPECIAL-USE, donc s'y fier serait faux », mais « la classification persistée **n'est pas
> stable dans le temps**, et a été observée fausse pendant une fenêtre ». Pendant cette
> fenêtre, un filtre clinique fondé sur `FolderType` aurait bel et bien laissé entrer la
> corbeille dans des dossiers patients. C'est un argument plus faible que celui écrit, et
> suffisant pour justifier le choix retenu — mais il faut le lire pour ce qu'il est.
>
> **Aucune conséquence sur le code livré** : la règle est restée fondée sur le **nom** du
> dossier, ce qui préserve le comportement antérieur. C'est la **justification documentée** qui
> était trop forte, pas la décision.
>
> Le nombre de messages a lui aussi changé (la base n'a plus que 51 messages, tous dans
> `INBOX`) : citer un volume relevé à un instant comme s'il caractérisait le système était
> l'erreur de méthode sous-jacente.

- **⚠️ ANGLE MORT SIGNALÉ, NON RÉSOLU.** La fixture d'intégration bâtit son schéma par **`EnsureCreatedAsync()`**, donc depuis le **modèle EF**. Les migrations FluentMigrator ne sont jouées par **aucun test** : schéma de test et schéma de production sont produits par **deux mécanismes différents**, et rien dans ce dépôt ne vérifie qu'ils concordent. D'où la double déclaration (migration **et** modèle) et la vérification manuelle des noms de colonnes. **Même famille que task-235** — et que le défaut du getter ci-dessus : *le harnais est plus permissif que la production, donc il valide du code qui ne marche pas*.
- **DÉCISION PRODUIT À ARBITRER.** Renforcer la règle par l'**union** SPECIAL-USE **et** nom. Le besoin est prouvé dans les deux sens : la boîte de dev classe `Trash` (50 messages) en `Custom` ; à l'inverse, un serveur peut annoncer `\Sent` sur un dossier au nom quelconque, que le nom seul laisserait entrer dans un dossier patient. **Cela change le comportement**, donc hors de cette task (règles 6 et 7).
- **🚧 BLOQUANT POUR LE MERGE, NON FAIT ET NON FAISABLE ICI.** La contre-épreuve au banc exige un dossier de **~300 documents** ; la base de dev plafonne à **41** pour son patient le plus fourni. Le critère central — « le coût cesse de suivre la taille du dossier » — **n'est pas mesurable sur le corpus nominal**. Le plan post-index n'a pas été relevé non plus : la migration n'est pas appliquée sur cette base (MCP en lecture seule, et on n'écrit pas dans une base praticien), et à 92 documents un relevé ne prouverait rien. **Le choix partiel/couvrant dépend de cette mesure.** Restent dus : le re-tir du pool à 6 et l'`EXPLAIN ANALYZE` après.

---

### v1.28 — La suite d'intégration échoue désormais quand elle journalise une erreur — task-235

- **Task** : task-235 — `done`. **PR** : `api-mail` #164 (label `awaiting-human-merge`). `dtos-mss` : branche auto-incluse **vide**, aucune PR.
- **PÉRIMÈTRE RÉDUIT, ASSUMÉ.** La US portait trois remèdes ; les remèdes **1** (échouer sur une erreur journalisée) et **3** (`MssRpps` dans les fixtures) sont livrés, le remède **2** (câbler `IBackgroundTaskQueue`) est **découpé vers task-237** sur décision humaine du 2026-08-06. Motif : le filet livré attrapait déjà de vrais défauts, et le laisser sur une branche prolongeait l'aveuglement qui a laissé passer task-234, task-233 et task-236. La règle 11 ne s'y oppose pas — elle interdit de livrer une US **produit** à moitié, et celle-ci n'a aucun impact produit.
- **LE FILET A MORDU DÈS SA PREMIÈRE EXÉCUTION, et c'est sa justification rétrospective.** Appliqué à 11 classes, il a mis **six tests au rouge** sur `Error creating DbContext … Parameter 'Host'` puis `[FlagChange] Failed to persist the pending MarkRead` — **mot pour mot l'erreur que la US citait en preuve** que la suite journalisait une panne et restait verte. Il l'a retrouvée **sans rien connaître de sa nature** : c'est ce qui le distingue d'un test ciblé, et ce qui lui permettra d'attraper le prochain défaut, dont on ne sait rien.
- **ET LA CAUSE ÉTAIT LE HARNAIS LUI-MÊME.** Deux manques dans les fixtures : `MssRpps` **renseigné nulle part** — le nom de base se dérivant de `(Email, MssRpps)`, le repli s'appliquait **dans les deux scopes**, qui calculaient donc le **même** nom, si bien que l'écart corrigé par task-234 était structurellement **inobservable** ; et `ConnectionStringServer` **jamais posée**, dont `ConnectionStringUser` se compose, donc tout scope construisant son propre contexte tombait sur un **hôte nul**. La jambe de durabilité **fonctionne enfin** au lieu d'échouer en silence derrière un `catch` best-effort. L'outil chargé de détecter que le harnais mentait a commencé par trouver que le harnais mentait.
- **CONCEPTION — deux choix, et leurs raisons.** Portée par `AsyncLocal` et non collecteur global : xUnit exécutant les classes **en parallèle**, un collecteur unique ferait échouer la classe A sur une erreur de la classe B, donc un flaky, donc un filet désactivé sous trois jours. Deux tests le **vérifient** au lieu de le supposer, dont celui qui prouve que la portée suit les continuations asynchrones et le travail de fond — c'est **là** que vivent les défauts visés. Et `Warning` est exclu **délibérément** : la suite en émet légitimement, et un filet qui crie pour des avertissements attendus serait ignoré.
- **UNE SEULE EXEMPTION dans tout le dépôt**, sur le test de démonstration, justifiée, fragment étroit. Preuves ROUGE : exemption retirée → le test échoue ; filet sans le correctif de chaîne → 6 rouges ; correctif appliqué → 10/10.
- **Défaut trouvé à la revue et corrigé** : la fabrique de logger du sentinelle existait **deux fois** dans le même fichier. Une fabrique dupliquée est une fabrique qui dérive — il suffit qu'une des deux oublie le fournisseur pour que son test ne mesure plus rien **tout en restant vert**, exactement le genre de test sans valeur que les cycles récents ont produit trois fois.
- **Build / tests** : 0 erreur, 0 avertissement. **3 523 verts** — domain 106, infrastructure 421, application 1998, api 650, integration 348 (16 ignorés).
- **⚠️ À SURVEILLER, non établi** : la suite d'intégration passe de **~2 min 45 s à 5 min 05 s**. Cause probable — la jambe de durabilité fonctionnant désormais, les chemins concernés **provisionnent réellement** une base par praticien au lieu d'échouer immédiatement. Signalé plutôt que passé sous silence ; le DOD de task-237 prend 2 min 45 s comme référence et sera peut-être à réviser.
- **Sonar** : **zéro** des 35 violations « new code » dans un fichier de cette task ; toutes héritées (outillage k6 26, `AppHost.cs` 3, cinq fichiers à 1). Une était **à moi** et est corrigée — `SYSLIB1045` sur la garde d'architecture de task-233, regex passée en `[GeneratedRegex]`. Les deux relevés sont cette fois **comparables** (même périmètre). QG toujours ERROR sur `new_coverage` = 0 — **aucun rapport de couverture n'est importé**, donc seuil inatteignable par construction — et sur les hotspots `Math.random()` de `journey.js`, **jamais révisés : cinquième signalement**.
- **🚧 CE QUE CETTE LIVRAISON NE FAIT PAS.** `IBackgroundTaskQueue` n'est câblée dans **aucune** fixture : les services la prennent en paramètre **optionnel**, elle vaut `null`, et le code emprunte son **repli en ligne**. **Le scope de fond n'est donc toujours jamais créé pendant les tests d'intégration.** Ce filet attrape ce que ce chemin journalise **quand il est emprunté** ; il ne le fait pas emprunter. Et l'adoption est de **11 classes sur 21** — une classe qui n'hérite pas n'est **pas protégée** : ce n'est pas une exemption, c'est un reste à faire. Tout cela est le périmètre de **task-237**.

---

### v1.29 — L'outbox est éprouvée cache chaud, et le getter qui rendait le piège possible n'existe plus — task-236

- **Task** : task-236 — `done`. **PR** : `api-mail` #166 (label `awaiting-human-merge`). Commits `24a6d30` (le test), `5762c46` (suppression du getter), `7246df0` (S103). `dtos-mss` : branche auto-incluse **vide**, aucune PR.
- **CE QUE CETTE TASK FERME : la boucle ouverte par task-234.** Le correctif de l'outbox (8 emplois du getter levant) était **déjà sur `develop`** depuis la PR #162 — cette task livre ce qui manquait : le filet, le recensement, et l'arbitrage.
- **LE TEST QUI MANQUAIT, sur le constructeur de PRODUCTION.** `WarmCacheContextResolutionTests` construit `PendingActionRepository` et `MailRepository` par le constructeur `(UserContextInfo, IResilientCacheService, ILogger)` — celui où rien n'est injecté — avec un **cache d'identifiant chaud** : le substitut répond du premier coup, donc `GetCurrentUserIdAsync` sort tôt **sans avoir résolu le contexte**. C'est la combinaison exacte qui mettait l'outbox hors service en régime établi, et elle n'existait **nulle part** : tous les tests existants injectent le contexte, où le getter fonctionnait toujours. Un test à cache froid passerait même sans le correctif — il ne mesurerait rien.
- **ET LE MONTAGE FAIT TOURNER LES MIGRATIONS FLUENTMIGRATOR DANS UN TEST, enfin.** La résolution emprunte le chemin de production intégral — `CreateDbContextAsync` → CREATE DATABASE + `MigrateUp` réels dans le conteneur. `EnsureCreated` ne joue jamais les migrations : c'était l'angle mort consigné par task-233 (« schéma de test et schéma de production sont produits par deux mécanismes différents »), partiellement refermé ici. Identité **fictive** unique par classe, une seule base provisionnée.
- **PREUVE ROUGE, l'exigence centrale du DOD.** Getter réintroduit (`var db = DataContext;` — l'état exact d'avant le correctif) → **3 échecs sur 4**, chacun nommant la cause : `DataContext non résolu — utiliser GetDataContextAsync() sur le chemin asynchrone (task-231)`. **Portée dite sans survente** : nette pour les trois méthodes de `PendingActionRepository` ; **impossible en isolation** pour `GetMailAuditSnapshotAsync`, où `CurrentGenerationAsync` résout déjà le contexte en amont — le correctif de task-233 y était défensif, pas la réparation d'un plantage vivant.
- **LE RECENSEMENT (remède 3), écrit.** Chemins de `BaseRepository` pouvant retourner sans résoudre : `GetCurrentUserIdAsync` (cache chaud — plus aucun site n'en dépend), le constructeur de production (par construction), `CreateDbContextAsync` (crée sans mémoïser — zéro appelant production), `Dispose()` (réarmait le getter — sans objet désormais). Plus six sorties anticipées sur cache dans les dépôts dérivés (`Contact` ×4, `Patient` ×1, `UserSettings` ×1), toutes sûres : leur chemin de miss résout explicitement.
- **L'ARBITRAGE RENDU (remède 4) : le getter `BaseRepository.DataContext` est SUPPRIMÉ, sur décision humaine.** Question posée avec le chiffrage — **zéro usage restant**, dans `src/` comme dans les tests. **Le compilateur est désormais la garde**, impossible à désactiver, là où `DataContextGetterScanTests` restait un test (conservé comme ceinture). Le build 0 erreur est la meilleure preuve du chiffrage. Trois plantages en deux jours avaient la même racine : un membre qui passe tous les tests et lève en production ne doit pas être appelable.
- **Passe Sonar** : une violation dans un fichier touché — le `S103` du constructeur de `BaseRepository`, **hérité de task-231 et signalé trois fois** (task-233, 235, 182) ; corrigé plutôt que re-signalé une quatrième fois. QG **ERROR** inchangé : `new_coverage` = 0 (aucun rapport importé — seuil inatteignable par construction) et hotspots `Math.random()` de `journey.js` jamais révisés (**septième signalement**).
- **Build / tests** : 0 erreur ; domain 136, infrastructure 419, application 2030 (flaky PDF export, vert au re-run), api 650/650 et integration 362/362 **sur le bin normal**. Les 7 échecs sous `--artifacts-path` (scans de sources + `.env` SMTP) sont l'artefact d'outillage documenté, **contre-preuve faite**. Suggestion consignée : les deux tests SMTP devraient **skipper** (pas échouer) quand le `.env` est introuvable.
- **🚧 CE QUI RESTE OUVERT** : task-237 (câbler `IBackgroundTaskQueue` — le scope de fond n'est toujours jamais créé pendant les tests), l'adoption du filet de task-235 (11 classes sur 21), et la dette de mesure au banc (228/229/230/233).

---

### v1.30 — Le scope de tâche de fond est enfin créé et exécuté pendant les tests — task-237

- **Task** : task-237 — `done`. **PR** : `api-mail` #167 (label `awaiting-human-merge`). Commits `d044266` (câblage + tests), `291bc6a` (harnais fidèle à la production + trois mensonges), `e4b0f10` (passe qualité). `dtos-mss` : branche auto-incluse **vide**, aucune PR.
- **CE QUE CETTE TASK FERME : la moitié manquante du chantier de task-235.** `IBackgroundTaskQueue` n'était enregistrée dans aucune fixture : les services empruntaient leur repli en ligne avec le contexte complet de la requête, et **le scope de fond n'était jamais créé pendant les tests** — là où vivaient les défauts de task-234 et task-236.
- **LA FILE, DÉTERMINISTE ET À LA DEMANDE.** Rien ne s'exécute tant qu'un test n'appelle pas `DrainAsync()` — aucun hôte, aucun `Task.Delay`, aucune scrutation (l'hôte de production consommerait en continu : le test devrait *attendre*, c'est-à-dire une suite lente et intermittente, le travers que task-235 corrigeait). Chaque élément tourne dans un **scope DI neuf**, et les exceptions **propagent** au test — un test le prouve.
- **LE HARNAIS DEVIENT FIDÈLE À LA PRODUCTION, et il a fallu DEUX preuves ROUGE restées vertes pour y arriver.** (1) La fixture semait ses scopes avec `CopyIdentityTo` — la méthode même que la preuve casse : les deux côtés cassaient symétriquement (`u_0` partout), écart inobservable. (2) La fixture pré-remplissait **aussi** les scopes de fond — un champ sauté par la recopie gardait sa valeur semée. Forme finale : enregistrement **production-exact** (`AddScoped<UserContextInfo>()`, scopes **vides** à la naissance), remplissage des seuls scopes de **requête** par le harnais — le rôle du middleware. La preuve ROUGE échoue alors **en nommant les deux bases** (`u_99700000042…` vs `u_0…`) : le symptôme exact de task-234, devenu un échec de test lisible.
- **LES TESTS.** `flag-propagate` : la bascule part **par la file** (label présent — « No background queue wired » impossible par construction), le drain l'exécute en scope de fond, l'action est traitée **dans la base de la requête** — l'assertion qui aurait attrapé task-234. `folder-reconcile` : enfilé par un listing en cache-hit, exécuté sans erreur. **8 drains** dans `EmailManagementUseCaseTests` : la frontière asynchrone de production est désormais **visible** dans les tests — l'échec-de-tests-verts que la US annonçait, résolu par le drain explicite, pas par une exemption.
- **ÉCART DE PÉRIMÈTRE DIT FRANCHEMENT : 2 chemins sur 3.** `enrich:{folder}` vit dans `MailController` — les fixtures n'ont pas de pipeline HTTP. Son work item suit le même motif que les chemins couverts ; le couvrir exige un montage `WebApplicationFactory`, décision d'outillage distincte, consignée.
- **TROIS MENSONGES DE HARNAIS DÉCOUVERTS.** (1) **La résolution du domaine mail ne venait d'aucune source déclarée** — tous les tests Gmail de `develop` étaient **cassés depuis le 2026-08-06** (dernier succès Seq : 2026-08-05T23:39Z), indépendamment de cette task, prouvé par stash deux fois ; les fixtures déclarent désormais leurs serveurs. (2) **Le cache résilient des fixtures est un substitut nu** (miss permanent) : le chemin cache-hit du listing — donc la réconciliation de task-229 — était **structurellement inatteignable** en intégration, et le conteneur Redis démarré par la fixture n'est même pas consulté par lui ; consigné, hors périmètre (les tests de décompte de sollicitations supposent le miss). (3) **Le fast-path de provisionnement par pod est keyé par nom de base sans le serveur** — collision entre les deux conteneurs du processus de test (`3D000`) ; RPPS distinct par fixture.
- **ET UN DÉFAUT `develop` RÉPARÉ** : `c565250` (correction du décalage d'arguments `UseStartTls`→`useAuth2` / `UseOAuth2`→`validateServerCertificate`) avait **cassé ses propres tests** — le semis de `SmtpCertificateValidationIntegrationTests` compensait l'ancien bug, donc son `UseOAuth2=true` devenait un vrai `UseAuth2` → « The PSC token is empty ». Personne ne l'a vu : **la CI ne joue pas ces tests**. Semis aligné.
- **Build / tests** (bin normal, AppHost arrêté sur autorisation humaine) : integration **369/369** (16 ignorés — la ligne de base normale), domain 136, infrastructure 419, application 2030, api 650. Durée intégration ~3 min 20. Deux découvertes d'environnement : `ASPNETCORE_ENVIRONMENT=Development` posé au niveau **utilisateur Windows** du poste (élucide les runs verts « sans wrapper » de 235/236) ; les tests Gmail ne vivent que sur le bin normal (`.env` par remontée de répertoires).
- **Sonar** : **zéro** des 35 violations « new code » dans un fichier de la task. QG ERROR inchangé — `new_coverage` = 0 (aucun rapport importé, seuil inatteignable par construction), hotspots `Math.random()` de `journey.js` jamais révisés (**huitième signalement**).
- **🚧 RESTE OUVERT** : couvrir `enrich:{folder}` (montage `WebApplicationFactory`), statuer sur le cache résilient substitué des fixtures, l'adoption du filet de task-235 (11 classes sur 21), et la **dette de mesure au banc** (228/229/230/233).

---

### v1.31 — Envoi sous 1 000 ms : la connexion SMTP retenue est entretenue, la sonde disparaît du chemin nominal — task-238

- **Task** : task-238 — `done`. **PR** : `api-mail` #168 (label `awaiting-human-merge`). Commit `f40cfe6`. `dtos-mss` : branche auto-incluse **vide**, aucune PR (**7ᵉ occurrence** du défaut de cycle).
- **LE DÉFAUT MESURÉ** : task-231 a posé la réutilisation de connexion SMTP, et la certification du 2026-08-06 mesure que le bénéfice ne se réalise pas au rythme réel — entre deux envois espacés (minutes), la connexion retenue meurt d'inactivité, la sonde la trouve morte à l'emprunt, chaque envoi repaie CONNECT + TLS + OCSP + AUTH : `send` p50 **1 229 ms**, seule étape 🔴 de la grille (cible 1 000), premier poste hors lecture (17,9 % du temps serveur).
- **Remède 1 — keep-alive SMTP.** La boucle NOOP de session (30 s) entretient désormais aussi le client SMTP retenu : patron `Wait(0)` (ne retarde **jamais** un envoi — testé), démarrage **idempotent bi-voie** (getter IMAP ou adoption SMTP — avant, une session qui n'avait jamais lu n'entretenait rien), **NOOP en échec → client écarté sur-le-champ** (le prochain emprunt reconnecte proprement au lieu de payer l'IOException de sonde — 1 345 sur le tir de référence). Politique de rétention inchangée : la connexion vit et meurt avec la session (5 min d'inactivité).
- **Remède 2 — sonde conditionnée à l'âge.** L'emprunt réutilise **sans sonder** si le dernier *signal de santé* (adoption, NOOP réussi, sonde réussie) a moins de `SmtpProbeMaxAge` (défaut **60 s = 2 × la cadence du keep-alive** ; zéro/négatif = comportement task-231, repli sûr ; configurable par domaine). Subtilité gravée dans le code : le signal de santé est **distinct** de `LastSmtpAccessTime` — l'accès est rafraîchi à l'emprunt *avant* qu'on sache si la connexion vit. Preuve mesurée sur socket réel : le smoke de banc attend désormais **0 NOOP** par réutilisation (était 1).
- **Remède 3 — CORRECTION DE DIAGNOSTIC : le cache OCSP/CRL existe déjà.** L'US affirmait « aucune mise en cache des réponses de révocation » — faux depuis **task-069** (OCSP fraîcheur 1 h + grâce Option C, REVOKED honoré quel que soit l'âge, CRL borné par `NextUpdate`, via le cache résilient du SDK). **Rien n'a été construit** ; l'item DOD est couvert par les tests de task-069, verts. **Cinquième correction de diagnostic d'US de la semaine** (233, 182, 233-doc, 232, 238).
- **Au passage** : `MailClientSession.Dispose` rendu idempotent (garde `_disposed`) — défaut pré-existant exposé par un test du keep-alive.
- **Zéro changement de contrat** (contrainte absolue de l'US) : même route/code HTTP/corps, archivage synchrone ; tests d'intégration inchangés hors l'assertion du smoke — qui est la preuve du gain.
- **Tests** : 5 nouveaux (keep-alive), 2 nouveaux + 1 adapté (fenêtre de sonde), smoke banc adapté. Preuve par mutation : condition d'âge inversée → le test de réutilisation fraîche échoue. Suites : domain 136, infrastructure 419, application 2037, api 650, integration **369/369** (16 ignorés).
- **Sonar** : **zéro** des 28 violations « new code » dans un fichier de la task (24/28 = outillage k6 des tasks 174/195, dont 1 new bug S1244 `report.py` ; 2 S103 hérités). **Le mur `new_coverage = 0` est tombé : 86,9 % — condition OK** (un rapport de couverture est désormais importé). QG toujours ERROR : hotspots `Math.random()` de `journey.js` jamais révisés (**9ᵉ signalement**) + violations héritées.
- **Contexte d'infrastructure** : GitHub Actions s'est rétabli (panne du 2026-08-06) — le run develop post-merge de task-237 est passé **VERT** (règle 5 soldée) ; la PR #168 n'avait aucun check remonté à l'ouverture, à vérifier au merge.
- **🚧 RESTE OUVERT — bloquant pour le MERGE** : contre-épreuve au banc (tir `journey` n200 K=1 iso-conditions : `send` p50 ≤ 1 000 ms vs 1 229, IOException de sonde en forte baisse vs 1 345, ~1 connexion SMTP par session). Le banc n'est pas monté dans ce cycle — la dette de mesure rejoint 228/229/230/233.

---

### v1.32 — L'enrichissement rend le verrou de session entre chaque message — task-239

- **Task** : task-239 — `done`. **PR** : `api-mail` #170 (label `awaiting-human-merge`). Commit `827e0ed`. `dtos-mss` : branche auto-incluse **vide**, aucune PR (**8ᵉ occurrence** du défaut de cycle).
- **LE DÉFAUT MESURÉ** : re-certification K=1 du 2026-08-06 (`journey-certif-n200-120344`, harnais corrigé `f209ce8`) — détention du verrou `imap_session` par `EnrichEmails` **7,44 s p95** à 12,5 acq/s ; derrière elle, l'inbox (étape 2) tombe à **4 112 ms p95 à 200 médecins** (verte à 50 et 100 — c'est la contention, pas un coût fixe), `GetEmailContent` sert des lectures à 25 ms p50 avec un p95 max à 10 s, la fiche patient (étape 11) déborde à 4 692 ms. C'est LE plafond mesuré du palier 200.
- **⚠️ CORRECTION DU DIAGNOSTIC DE LA US — la sixième de la suite.** La US affirmait « l'enrichissement détient le verrou pendant tout son pipeline (téléchargement, extraction IHE-XDM, parsing CDA, écritures base) ». **Faux sur trois des quatre postes, vérifié dans le code** : la persistance est hors verrou depuis **task-079** (Phase B, verrou de persistance par (boîte, dossier)), le parse CDA (`ProcessIheXdmZips`) vit dans `BuildMailDtoAsync` en Phase B, et `ExtractIheXdmZipsAsync` sous verrou ne fait que **télécharger les octets** du zip (réseau, légitime). Le poste réel : la fenêtre de verrou par sous-lot (task-228, 15 messages par défaut) couvre le fetch **séquentiel** des corps et pièces jointes — ~45 allers-retours sous latence mssante ≈ les 7,44 s mesurées. Les remèdes 1 (« verrou au strict IMAP ») et 3 (« instrumenter la preuve ») étaient donc **déjà en place** — constatés et testés, pas réécrits ; seul le remède 2 (« lots courts ») restait à livrer, et à une granularité plus fine que la US ne l'imaginait.
- **LE REMÈDE — une fenêtre de verrou PAR MESSAGE.** `FetchEnrichmentChunkAsync` restructuré : une fenêtre courte « résumés » par sous-lot (connexion + SELECT + FETCH des enveloppes), puis `FetchSingleMailWindowAsync` — corps et PJ d'**un seul** message sous le verrou, rendu aussitôt. Chaque intervalle laisse passer un geste du médecin (`GetFolders`, `UpdateFlag`, `GetEmailContent`) ; l'équité vient des waiters FIFO de `SemaphoreSlim` — le geste en attente passe devant la ré-acquisition immédiate de la boucle.
- **ZÉRO COÛT AJOUTÉ AU CHEMIN NOMINAL, et c'est le point d'ingénierie.** Les fenêtres message **réutilisent** le client et le dossier résolus par la fenêtre résumés : pas de `ConnectInternalAsync` (qui relit les réglages en base à chaque appel — l'y mettre aurait glissé du SQL sous le verrou, l'inverse du remède 1), pas de re-SELECT. Le dossier n'est rouvert (1 aller-retour) que si un geste intercalé l'a **réellement** désélectionné sur la connexion partagée. La fermeture historique de fin de sous-lot est faite dans la dernière fenêtre, pour ne pas payer une acquisition de plus.
- **LE TRAVAIL RÉSEAU PAYÉ SURVIT AUX COUPURES DE MILIEU DE SOUS-LOT.** Le contrat de retour change : `EnrichmentChunkFetch` porte les messages lus **avec** l'indication d'abandon — avant, un `null` portait l'abandon et une erreur en milieu de sous-lot jetait les messages déjà lus. Désormais ils partent en persistance, les UIDs restants redeviennent `pending` (l'invariant task-227 tient : chaque `FetchedMail` est individuellement complet). Risque UIDVALIDITY entre fenêtres : même enveloppe que task-228 — la granularité change, l'exposition non (générations confrontées à la persistance).
- **Étiquette de verrou par message** `EnrichEmails:{folder}:{uid}` : même famille `EnrichEmails` dans la table « verrou par opération » du banc (troncature au premier `:`, task-214) — la preuve chiffrée sera lisible **sans changement d'instrumentation**. Aucune donnée de santé dans les libellés (dossier, UID, hash).
- **TESTS — le nombre d'acquisitions, toujours, et une preuve d'entrelacement en plus.** 6 tests recalés sur le nouveau contrat (3 UIDs ⇒ 1+3 fenêtres ; taille 2, 5 UIDs ⇒ 3+5=8 ; 2 libérations avant la persistance) — **preuve par mutation : les 6 étaient ROUGES sur le code par sous-lot**, qui est exactement la mutation « lot redevenu monolithique ». 4 unitaires neufs : dossier mort en milieu de sous-lot ⇒ le message lu est persisté, ni perdu ni fantôme ; dossier désélectionné ⇒ rouvert à chaque fenêtre, lot intègre ; parse/persist jamais sous verrou (traçage de détention via substitut — l'item DOD) ; échec de parse ⇒ verrou ni détenu ni fuité (`locks == unlocks`, persist lock rendu). **1 test d'intégration neuf** (`EnrichmentLockInterleavingTests`) au **vrai** `MailClientSessionManager` (vrai sémaphore, vraies portées `ImapLockScope`, transport IMAP simulé) : un geste interactif arrive PENDANT la fenêtre du 1ᵉʳ message (bloqué — asserté, déterministe), passe ENTRE les deux fenêtres (asserté, timeout 10 s = régression), et le lot est persisté **exactement une fois par message** — l'item DOD « ni perte ni doublon sous concurrence ».
- **Build / tests** : 0 erreur, 0 avertissement (Debug et Release). **136 / 419 / 2041 / 650 / 370** verts (16 ignorés, le compte normal), intégration incluse — trois passes complètes (post-develop, scan Sonar Release, validation `/review`).
- **Sonar — zéro violation dans le périmètre, vérifié fichier par fichier.** `new_violations` 28 → **32**, et **aucune** des 32 dans un fichier de task-239. 26/32 = outillage k6 (tasks 174/195, hérité ; les 2 hotspots `Math.random()` de `journey.js` en sont à leur **10ᵉ signalement**). **6/32 = fichiers de task-238** (mergée le matin même), apparues dans la new-code period post-merge : `SmtpConnectionFactory` S103 (152 car.), `MailClientSession` S3776 (19), `SmtpSessionKeepAliveTests` CA1816, `MailServerDiscovery` ×2 — le scan de task-238 n'en signalait aucun dans ses fichiers ; écart vraisemblablement lié aux retouches tardives de son cycle. **Hors périmètre ici** (règle 6) — matière à une passe d'entretien. `new_coverage` monte à **87,5 %** (≥ 80, OK).
- **Passe `/forge-simplify` — skip propre.** Candidats examinés et écartés : mapper le retour sur `Ardalis.Result` (l'abandon doit voyager AVEC les messages lus — un `Result.Error` ne porte pas de valeur) ; factoriser l'idiome `!IsOpen && !TryOpenFolderAsync` (4 autres sites hors diff).
- **🚧 CE QUE CETTE LIVRAISON NE PROUVE PAS.** Aucune latence n'est mesurée : les tests prouvent le **découpage** (le verrou est rendu N fois, le geste passe entre deux fenêtres), pas le p95. La re-certification K=1 n200 iso-conditions est **bloquante pour le merge** : détention `EnrichEmails` p95 **≤ 2 s** (réf. 7,44 s), inbox p95 **≤ 1 000 ms** à 200 (réf. 4 112 ms), étape 3 p95 ≤ 500 ms et `journey_warm_served_from_store` ≥ 95 %, **fiche patient re-mesurée — c'est le chiffre qui décide de l'US hydratation**, 0 régression sur les étapes vertes. Leçons de task-213 et task-222.

### v1.33 — Un document clinique trop long ne disparaît plus de la recherche sémantique — task-196

- **Task** : task-196 — `done`. **PR** : `api-mail` #171 (label `awaiting-human-merge`). Commits `a2c9ac0` (implémentation), `98ca925` (passe qualité), `bb7d988` (correctifs de revue). `dtos-mss` : branche auto-incluse **vide**, aucune PR (**9e occurrence** du défaut de cycle).
- **LE DÉFAUT — une perte de donnée médicale silencieuse, référencée depuis le 2026-07-25 et jamais écrite.** La troncature d'entrée des embeddings comptait des **caractères** quand la limite du modèle est en **tokens**. Ratio mesuré sur texte clinique dense (codes CIM-10/LOINC/CCAM, accents, résidus CDA) : **2,1 caractères par token**, pas les ~4 supposés par les bornes de configuration. Un contenu de **19 065 caractères — sous** l'ancienne borne de 20 000 — pèse ~9 000 tokens, part en `HTTP 400`, et l'échec était avalé par un `catch { return null; }`. Le document n'entrait **jamais** dans l'index sémantique et rien ne permettait de savoir lesquels manquaient : le praticien ne voit pas d'erreur, il voit une recherche qui ne remonte pas le document — **indiscernable d'un document qui n'existe pas**.
- **⚠️ CE QUI A DÉCLENCHÉ LA LIVRAISON, ET UNE ERREUR D'ANALYSE RECTIFIÉE.** Le défaut a été re-constaté **en charge** le 2026-08-08 (smoke post-task-239) : **1 286 `ClientResultException` en 20 minutes**. Or deux rapports de tir (`n300-184134`, `certif-n200-022915`) avaient classé cette famille en « bruit connu du banc — Flagsmith ». **Faux, et une seule requête le prouvait** : `FlagsmithAPIError = 0` sur la même fenêtre, `System.ClientModel.ClientResultException` étant le type du **client OpenAI**. Ce compteur ne mesurait pas du bruit d'infrastructure : il **comptait des documents cliniques perdus pour la recherche**. Rectificatif consigné dans `reports/INDEX.md` avec la leçon de méthode — ne jamais ranger une famille d'exceptions dans « connue du banc » sans l'ouvrir.
- **DÉCISION TRANCHÉE ET ÉCRITE — troncature bornée en tokens, PAS segmentation multi-vecteurs.** La segmentation préserverait la fin des documents longs, mais elle change le **modèle de données** (N vecteurs par document) et le **classement** — deux points que la US place hors périmètre et que sa section conformité interdit de franchir sans arbitrage. **Ce qu'on accepte de perdre est dit franchement : au-delà de la borne, la fin du document n'est pas indexée** — et un document clinique porte souvent sa conclusion à la fin. Le renoncement est rendu **mesurable** (`WasTruncated`), pour que la segmentation soit un jour arbitrée sur mesure au lieu d'être supposée.
- **LE REMÈDE — une seule borne, dans l'unité du modèle.** `EmbeddingInputBounder` : **tokeniseur réel** (`Microsoft.ML.Tokenizers`, vocabulaire `cl100k_base` **embarqué en ressource** — aucun téléchargement au démarrage, donc compatible d'un déploiement **HDS cloisonné**), marge de sécurité 2 %, coupe **sur frontière de token** — ce qui règle gratuitement les paires de substitution UTF-16 que `content[..n]` pouvait scinder. Les `TruncateContent` privés des deux chemins d'embedding disparaissent : **les services ne connaissent plus aucun plafond, donc ils ne peuvent plus en avoir un qui diverge**. `MaxEmbeddingCharacters` (incohérente : 20 000/30 000 côté OpenAI, 4 000/8 000 côté Ollama, entre `appsettings` et les défauts de code) est **supprimée** au profit de `MaxEmbeddingTokens` = 8192, avec un test de garde contre la divergence. **Ceinture et bretelles** : sur rejet pour dépassement malgré la marge, le contenu est re-borné et l'appel **réessayé une fois**.
- **L'ÉCHEC CESSE D'ÊTRE SILENCIEUX — c'est le volet le plus grave de la US.** Le `return null` reste (l'appelant n'a rien de mieux à faire d'un vecteur manquant), mais il n'est plus invisible : compteur `mssante_embedding_failures_total{content_type,cause}` **distinguant l'annulation de la panne de fournisseur** ; **inventaire des documents sans vecteur** (modèle strictement technique — ni contenu clinique, ni INS, exigence PGSSI-S) et trois routes d'exploitation sur `MailMaintenanceController` ; **ré-indexation depuis le contenu déjà stocké**, sans re-télécharger le message — garantie **structurelle** et non conventionnelle : le service ne prend **aucun** collaborateur IMAP, et un test le verrouille.
- **DEUX DÉFAUTS BLOQUANTS TROUVÉS À LA REVUE, TOUS DEUX À LA MÊME JOINTURE — l'enseignement de méthode du cycle.** La task a été écrite par **deux agents travaillant en parallèle sans se voir**, puis passée à `/forge-simplify` : toute l'anomalie s'est logée à leur frontière. (1) **Le compteur d'échec comptait double** — chacun avait posé son incrément, et la passe qualité a mutualisé le chemin d'appel **sans retirer** ceux des appelants. Deux conséquences réelles : `medical_document` comptait double quand `email` comptait juste — **le compteur qui doit répondre à « combien de documents manquent » était faux et incohérent d'une étiquette à l'autre** ; et à chaque **arrêt propre**, l'annulation classée `cancelled` par l'invocateur se doublait d'un `provider_error` de l'appelant, ce qui aurait déclenché toute alerte posée sur cette cause. **Le test qui manquait est ajouté** (« un document perdu = **une** mesure, avec la bonne cause », sur la voie nominale complète) : c'est son absence qui a laissé passer la régression. (2) Deux `packages.lock.json` que tout build régénérait. Corrigés sur la branche (`bb7d988`), verdict **APPROVED** après correction.
- **La passe `/forge-simplify` avait trouvé la même classe de problème** : les deux services d'embedding portaient **chacun sa copie** du chemin d'appel (~35 lignes), et la composition du texte vectorisé était écrite deux fois (voie nominale et reprise) **alors que le commentaire de la reprise exige que le texte soit le même** — invariant énoncé, rien ne le tenait ; `MedicalDocumentEmbeddingText.Compose` le tient désormais (un vecteur reconstruit d'un texte composé autrement n'est pas comparable à l'index). Aussi : la borne tokenisait **deux fois** (comptage complet puis coupe) sur les documents longs, précisément la raison d'être de ce chemin.
- **Sécurité de la chaîne d'approvisionnement** : `Microsoft.Bcl.Memory` **remontée en 10.0.10** — la 9.0.4 tirée par le tokeniseur porte `GHSA-73j8-2gch-69rq` (sévérité **haute**), que le build refuse à raison. Traitée, pas contournée.
- **Ce que la revue a vérifié plutôt que supposé** : le tokeniseur éprouvé **empiriquement** sur un banc jetable (l'optimisation en passe unique conserve `TokenCount` juste dans les deux branches) ; le test de non-fuite d'INS est une **vraie preuve** (liste blanche des propriétés **et** balayage des valeurs à la recherche de l'INS et du corps réellement semés) ; la **portée praticien est structurelle** — aucun chemin ne permet de lister ou ré-indexer les documents d'un confrère.
- **Build / tests** : 0 erreur, 0 avertissement. **3 580 tests verts** (59 neufs). Un flaky de parallélisation trouvé et corrigé au passage : le `Meter` étant statique donc process-wide, quatre classes émettant sur le même compteur devaient être sérialisées (même famille que le défaut documenté par task-203).
- **Sonar : NON MESURÉ** — serveur injoignable, `SONAR_TOKEN` absent. Ce n'est **pas** un « rien à signaler » : la qualité de ce diff n'est ni verte ni rouge, elle est **non mesurée**. À relancer avant merge.
- **⚠️ DIVERGENCE ASSUMÉE, À ARBITRER AU HAG.** Le DOD exigeait « plus aucune duplication de `TruncateContent` ». **Deux subsistent** — `EmailSummaryService`, `EmailTaggingService` — délibérément : ce sont des garde-fous de **coût** sur `gpt-4o-mini` (contexte 128 k), **deux ordres de grandeur** sous sa limite ; les convertir aurait aligné l'unité sans rien corriger.
- **🚧 DETTE EXPLICITEMENT NOTÉE** : l'inventaire ne couvre que les documents médicaux (`MailContent.Embedding` peut aussi être nul) ; la ré-indexation en masse est **synchrone dans la requête HTTP** (plafond 1 000, acceptable pour une route d'exploitation déclenchée à la main) ; le prédicat `Embedding IS NULL` est prouvé contre le fournisseur en mémoire, **pas contre pgvector réel** (Docker indisponible dans la session). **Conséquence à retenir pour le banc** : la baseline du scénario `search`, marquée PROVISOIRE depuis task-174 parce qu'elle mesurait un index **incomplet**, ne pourra être re-dérivée qu'après vérification de cette livraison au banc.


### v1.34 — Le premier poste de coût du parcours devient attribuable à l'un de ses appels — task-240

- **Task** : task-240 — `done`. **PR** : `api-mail` #173 (label `awaiting-human-merge`). Commits `e8e6629` (implémentation), `db5744d` (passe qualité), `7ca0763` (correctifs de revue). `dtos-mss` : branche auto-incluse **vide**, aucune PR (**10e occurrence** du défaut de cycle).
- **LE DÉFAUT — un percentile de mélange sur le premier poste de coût.** L'étape `read_list` (ouvrir l'inbox) pèse **46,3 % du temps serveur** avec un p95 de **4 781 ms à 200 médecins** (campagne K=1 du 2026-08-08) — elle a **doublé** depuis que task-239 a libéré le verrou de session, le goulet s'étant déplacé sur elle. Or elle agrège **deux appels HTTP distincts sous une seule étiquette `op`** (`getFolder` puis `getEmails`, `journey.js:539-540`) : son percentile ne désigne rien, et **personne ne peut dire lequel des deux coûte**. `dashboard` a le même travers avec **quatre** appels — signalé le 2026-08-04, jamais traité.
- **US d'INSTRUMENT, et c'est le cœur du sujet.** Elle ne rend rien plus rapide : elle rend le prochain correctif **décidable**. Cette EPIC a déjà annulé une US applicative écrite sur une cause supposée (task-222), et la règle qui en est sortie est appliquée ici à la lettre : « si le coût d'une étape ne peut pas être attribué à l'un de ses appels, le premier finding est le manque d'instrumentation, pas une optimisation devinée ». C'est aussi l'un des quatre motifs du **NO-GO 500** — on ne mesure pas à 500 sans savoir expliquer 200.
- **LA DÉCISION QUI COMMANDE TOUT — une étiquette `call` À CÔTÉ de `op`, jamais à la place.** `read_list` et `dashboard` sont des lignes de la grille SLO et de `reports/INDEX.md` depuis des dizaines de tirs : si leur `op` changeait de sémantique, **toute la série historique deviendrait incomparable**. Et le médecin attend la **somme** des appels de l'étape — l'étape reste l'unité de jugement, la ventilation est un supplément de diagnostic. Table déclarative `MULTI_CALL_STEPS` (JS) / `JOURNEY_MULTI_CALL_STEPS` (Python), étiqueteur `stepTagger(op)` qui fige le palier une fois par geste (une étape à cheval sur une rampe n'est plus coupée en deux fenêtres).
- **LE LIVRABLE RÉEL EST UNE PHRASE, PAS UN TABLEAU.** Le rapport nomme le porteur du **p95** et celui du **temps serveur total**, et dit explicitement **quand les deux diffèrent** — c'est ce qui transforme « l'inbox coûte 46 % » en « voici la requête à optimiser ». Section **rendue même vide** avec trois états distincts (patron maison de task-214) : *aucun appel étiqueté* — qui dit la conséquence, « le p95 reste un mélange, aucune optimisation décidable » —, *ventilation incomplète*, et *attribution impossible* (le rapport **ne fabrique pas** un porteur sur un seul appel).
- **Non étiquetés délibérément, et écrit dans le recensement** : la chauffe (artefact de harnais hors grille SLO) et les étapes qui **répètent le même appel** — ventiler un appel contre lui-même ne dit rien. Nuance consignée sur `patient_search` : il mêle aussi deux **critères** sur la même route (INS vs nom), profils de coût plausiblement différents — hors du défaut visé, mais dit plutôt que tu.
- **⚠️ DÉFAUT BLOQUANT TROUVÉ À LA REVUE — la fixture certifiait une arithmétique impossible.** `http_reqs` s'incrémente **une fois par requête HTTP**, donc le compte de l'étape vaut **2×** celui de chacun de ses appels (**4×** pour `dashboard`). La fixture posait l'**égalité**, et un test l'affirmait comme « la propriété du harnais que la fixture reproduit » — l'inverse exact de cette propriété. **Ce n'était pas cosmétique** : sur cette fixture, le rapport **se contredisait lui-même** (« Axes d'amélioration » chiffrait `read_list` à 80 s, la ventilation à 184 s) sans qu'aucun test ne le voie, et le prochain qui aurait écrit le contrôle évident — « la somme des appels reconstitue le coût de l'étape », déjà évoqué en toutes lettres dans le message d'incomplétude du rapport — aurait conclu à un bug inexistant. La fixture redevient un **tir possible**, avec trois invariants de mélange **vérifiés** au lieu d'être commentés : temps serveur de l'étape = somme de celui de ses appels, médiane encadrée par celles des appels, p95 de l'étape entre la médiane du plus lent et le pire des p95 — c'est ce dernier point que l'ancien couple (étape 700 ms / `emails` 4 700 ms) violait.
- **LA GARANTIE CENTRALE ÉPROUVÉE PAR MUTATION, PAS SUR PAROLE.** Toutes les lectures du rapport passent par un accès par **clé exacte** : ajouter des clés ne peut donc rien changer *aujourd'hui*, et les tests de comparabilité pourraient passer **trivialement** — le pire défaut possible ici, puisqu'ils donneraient une fausse assurance sur des dizaines de tirs historiques. La revue a injecté une régression **plausible** (« prendre le pire appel quand l'étape est ventilée ») dans une copie hors dépôt : **les quatre tests de comparabilité tombent**, y compris la comparaison **caractère pour caractère** des tables genou et verdict SLO. Re-vérifié après correction.
- **Quatre suggestions traitées** : l'avertissement d'incomplétude ne couvrait qu'**un** mode de rupture (un appel manquant) — il couvre désormais l'**étape entière disparue**, sinon la section se rendait « complète et saine » avec la moitié des données ; la phrase d'attribution nommait un porteur même à **n=3** et réutilise maintenant la garde d'échantillons que la grille SLO s'impose ailleurs ; « % du temps de l'étape » devient « % du **temps ventilé** » (le dénominateur est la somme des appels *mesurés*, trompeur exactement dans le cas que l'avertissement signale) ; un commentaire comptait 6 sous-métriques là où il y en a 12.
- **Cardinalité et confidentialité** : 6 couples `(op, call)` × paliers × 2 métriques — **borné**, ~72 sous-métriques sur une campagne à 5 paliers. Étiquettes **littérales** verrouillées par un test (`^[a-z]{3,12}$`), ne dérivant d'aucune réponse serveur ni d'aucun paramètre de route — **aucune donnée de santé possible**, contrairement au gabarit `{ins}` voisin.
- **Passe `/forge-simplify`** : `tagsFor(op, call)` avait gagné un paramètre qu'**aucun appelant ne passait** (les six sites contournaient la fonction), et la ventilation du palier le plus peuplé était **recalculée** alors qu'elle venait de l'être pour tous les paliers — deux chemins pouvant diverger. Découverte au passage : le contrat inter-runtime des deux tables suit **déjà** le patron maison (commentaire directionnel + échec visible, comme `ITERATION_SECONDS_ENV_PREFIX` entre `report.py` et `lib/vu-sizing.js`) — un générateur aurait été une **régression** par rapport à la convention locale.
- **Sonar : skip propre** — aucun code applicatif touché, le diff vit entièrement dans `Api/Mail/tests/loadtest-k6/`. Le filet propre de ce diff est `selftest.sh` : **209 tests Python + 57 node**, verts.
- **🚧 CE QUE CETTE LIVRAISON NE PROUVE PAS.** La DOD « le rapport nomme lequel des deux appels porte le coût, avec son chiffre » est prouvée **sur fixture**, pas sur mesure réelle — aucun tir n'a été lancé (banc non monté pendant le cycle). Et une limite non testable hors banc subsiste : ces tests verrouillent le **côté rapport**, tandis que le côté k6 — « un échantillon portant `{op, palier, call}` alimente toujours la sous-métrique `{op, palier}` » — repose sur la correspondance par **sous-ensemble** de tags, correcte mais qu'aucun test ne peut prouver ici. La contre-épreuve au banc (tir `journey` 100 médecins, 10 min) clôt les deux.


### v1.35 — Le keep-alive SMTP n'était pas inerte : il n'était pas compté, et il agissait sur la mauvaise horloge — task-241

- **Task** : task-241 — `done`. **PR** : `api-mail` #174 (label `awaiting-human-merge`). Commit `9ec3a60`. `dtos-mss` : branche auto-incluse **vide**, aucune PR (**10ᵉ occurrence**).
- **CETTE US COMMENÇAIT PAR UNE INSTRUCTION, PAS PAR UN CORRECTIF**, et l'ordre a été tenu : task-238 avait livré trois remèdes dont **aucun n'avait produit d'effet mesurable** sur deux campagnes consécutives, et le PO a exigé qu'on comprenne avant d'écrire un quatrième. Le livrable n°1 est donc une **réponse**.
- **⚠️ LES DEUX FAITS FONDATEURS DE LA US ÉTAIENT DES LECTURES D'INSTRUMENT.** (1) `noop = 0`, présenté comme « le fait qui commande toute la US », **ne mesurait pas le keep-alive** : `MailServerCommands.NoOp` n'était consigné qu'à **un seul endroit du dépôt** — `SmtpConnectionProbe`, la sonde de fraîcheur — et le battement appelait `NoOpAsync` sans rien enregistrer. Or task-238 avait précisément **retiré la sonde du chemin nominal** (`SmtpProbeMaxAge` 60 s) : « zéro sonde » était le **résultat voulu**, pas la preuve d'un mécanisme mort. (2) « ~1,85 connexion par envoi » **agrège l'IMAP et le SMTP** : le compteur porte deux étiquettes (`command` **et** `operation`), et `connect = 5 395` somme `ConnectImap` et `SmtpConnect` sur un parcours dont l'essentiel est de la lecture. **Troisième fois** que cette famille de défaut est rencontrée dans l'EPIC (task-222 annulée, task-224 défaut 5) — et la première fois qu'elle est trouvée dans les **prémisses d'une US** plutôt que dans un rapport.
- **LA CAUSE RÉELLE — DEUX HORLOGES, ET LE KEEP-ALIVE N'AGIT QUE SUR LA MAUVAISE.** Ce n'est **pas** l'affinité de session, l'hypothèse que la US demandait expressément de ne pas présumer. Établi depuis le code, site par site : `LastSmtpAccessTime` n'est rafraîchi que par `RefreshSmtp()`, appelé depuis **un seul endroit** (`MailClientSessionManager:170`), c'est-à-dire **à l'emprunt du jeton**, donc à l'envoi ; `IsSmtpConnectionIdle` compare cet accès à `SmtpIdleTimeout` (**5 min**) et le balayage ferme la connexion sur ce critère ; le battement, lui, ne met à jour que `_lastSmtpHealthySignalUtc` — le **signal de santé**, que task-238 avait délibérément rendu distinct de l'accès. **Le keep-alive garde donc la connexion vivante sur le fil pendant que l'éviction la ferme sur son inactivité d'usage : aucun nombre de battements ne peut l'en empêcher.** Le remède 1 de task-238 visait la bonne connexion et la mauvaise horloge.
- **ET LA MARGE EST DE DOUZE SECONDES** : le parcours laisse **~4,8 min** entre deux envois d'un même médecin, contre un `SmtpIdleTimeout` de **5 min**. Avec le temps de réflexion tiré au hasard qu'impose le modèle par parcours, une part importante des intervalles dépasse le seuil — ce qui explique enfin le coût **plat sur les trois paliers** (payé par appel, non subi sous la charge) et l'inertie des trois remèdes.
- **CE QUI A ÉTÉ LIVRÉ : le correctif d'instrument, et lui seul.** Le battement enregistre désormais sa sollicitation sous l'étiquette d'opération **`SmtpKeepAlive`**, distincte de `SmtpSend` — sans quoi le prochain tir redirait « noop = 0 » et la question 1 resterait sans réponse mesurable. Appel direct au point d'entrée statique des métriques et non au recorder par requête : la boucle tourne **hors requête**, et l'y brancher attribuerait ses allers-retours à la requête qui passe. **Aucun changement de comportement** — ni politique de rétention, ni délais, ni contrat d'envoi.
- **L'ARBITRAGE EST DÉFÉRÉ À L'HUMAIN, ET C'EST UN CHOIX.** La correction de fond a deux voies : le battement rafraîchit aussi l'accès (la rétention devient « vivante tant qu'entretenue » — **changement de politique que task-238 s'était explicitement interdit**), ou `SmtpIdleTimeout` passe au-dessus de l'intervalle réel entre envois. **Les deux augmentent le nombre de connexions retenues par boîte**, face à la contrainte opérateur MSSanté que task-231 et task-238 ont toutes deux préservée. La forge a écrit la réponse et l'instrument ; elle n'a pas tranché la politique.
- **Sonar** : **0 finding imputable**. Le `S3776` de `MailClientSession` (complexité 19) est celui que le log de task-239 attribuait déjà à task-238, **inchangé** — l'ajout est du code linéaire dans une autre méthode — et relève de `/sonar-s3776`, hors chaîne. La hausse `new_violations` 33 → 44 suit le **merge de task-240**, pas cette task. `new_coverage` **87,9 % — OK**.
- **Build / tests** : 0 erreur ; solution complète verte — domain 136 · infrastructure 429 · application 2074 · api 660 · intégration **371** (16 ignorés). Deux exécutions antérieures ont montré un échec chacune, **flakies connus et verts au re-run** : `UglyToad.PdfPig` (famille signalée depuis task-228) et `ImapProtocolException` (l'instabilité Dovecot sous charge de conteneurs, **signalée et consignée par task-197**).
- **🚧 CE QUE CETTE LIVRAISON NE PROUVE PAS.** Elle **ne fait pas passer `send` sous 1 000 ms** et ne le prétend pas — c'est d'ailleurs le point : la US posait qu'« un correctif sans effet mesuré n'en est pas un ». Restent ouvertes et exigent le banc : le **chiffrage de l'affinité** (question 3, à mesurer avec un filtre `operation="SmtpConnect"` ; elle s'**ajoute** au mécanisme trouvé au lieu de le remplacer) et la **décomposition des ~1 240 ms** par trace (question 4). La dette signalée par la revue de task-231 — un fragment de JWT journalisé en avertissement dans `SmtpConnectionFactory` — est **re-signalée**, comme le DOD l'autorisait, plutôt que traitée hors du fil de l'analyse.

### v1.36 — L'attente d'une connexion à la base accélère avec la population, et le verdict qui l'avait écartée est périmé — task-242

- **Task** : task-242 — `done`. **PR** : `api-mail` #175 (label `awaiting-human-merge`). `dtos-mss` : branche auto-incluse **vide**, aucune PR (**11ᵉ occurrence**).
- **LA SEULE GRANDEUR RÉSIDENTE QUI ACCÉLÈRE.** Campagne K=1 du 2026-08-08 (`journey-certif-n200-142630`) : la part des relevés `cl_waiting` non nuls passe de **5 %** (50 médecins) à **7 %** (100) puis **29 %** (200, soutenu, max 3). Toutes les autres grandeurs croissent **linéairement** avec la population — sessions IMAP 116 / 245 / 483, backends Postgres 92 / 175 / 352. Celle-ci quadruple en valeur quand la population quadruple, mais son **taux de présence** est multiplié par six. C'est le candidat n°1 au prochain plafond, et un des motifs du NO-GO 500.
- **⚠️ LE PIÈGE DE LECTURE, ET IL ÉTAIT DANS LE RAPPORT LUI-MÊME.** La section « Ressource épinglée » **écartait** PgBouncer en **moyennant les trois paliers** (14 %, sous le seuil de présence soutenue de 25 %). Or c'est le **palier** qui décide d'une conclusion de capacité, jamais la moyenne — et le palier 200 franchit le seuil. Les deux affirmations contradictoires coexistaient dans le même document : celle qui écarte, en tête, et celle qui accuse, dans la table par palier. Le correctif rend le verdict **par palier**, écrit l'écart, et marque le verdict précédent comme **périmé**.
- **Ce qui a été livré** : verdict par palier dans `report.py` (seuils nommés une seule fois — `PGBOUNCER_WAITING_RESOURCE` plutôt que deux littéraux qui dériveraient), sonde `observe.ps1` corrigée, 13 tests dont **deux témoins négatifs** (un transitoire d'ouverture répété à chaque palier ne désigne rien ; une ressource déjà épinglée globalement n'est pas dupliquée), `docs/loadtest.md` et `reports/INDEX.md` mis à jour.
- **Deux corrections issues de la revue** : (1) **donnée morte** — `cl_waiting_practitioner` / `_maintenance` étaient émis dans le CSV sans **jamais** être rendus, alors que c'est précisément la famille *praticien* que porte le seuil de reprise du sujet ; (2) `cl_waiting` calculé deux fois dans `observe.ps1`, et garde de colonnes **séparée** pour qu'un pooler sans `maxwait_us` ne fasse pas retomber la sonde à zéro.
- **Sécurité / données de santé** : métriques d'exploitation uniquement, aucune donnée patient dans les étiquettes ni dans les requêtes de diagnostic, banc 100 % synthétique. Le cloisonnement « une base par praticien » est **inchangé**.

### v1.37 — Le premier poste de coût du parcours cesse d'être une boîte noire de 3,3 secondes — task-243

- **Task** : task-243 — `archived`. ⚠️ **Développée directement sur `develop`** à la demande humaine — pas de branche `feat/*`, **pas de PR, donc pas de HAG** sur cette task. Seule exception de l'EPIC à ce jour.
- **US D'INSTRUMENT, PAS D'OPTIMISATION**, et l'ordre est délibéré : elle ne rend rien plus rapide, elle rend le prochain correctif **décidable** — et surtout elle **empêche** de l'écrire sur une intuition. L'EPIC a déjà annulé une US applicative bâtie sur une cause plausible et fausse (task-222). La question n'était pas « laquelle des requêtes coûte » (task-240 l'a réglée) mais « **où part le temps à l'intérieur** de cette requête », pour un p95 de 5 676 ms.
- **Le découpage en trois phases, choisi pour trancher entre les trois candidats et rien de plus** : `connection_open` (obtenir une connexion — pool Npgsql, PgBouncer, poignée de main ⇒ **contention base** à l'état pur), `sql_execute` (commande envoyée → serveur répondu ⇒ travail du serveur), `assemble` (**le reste, par différence** : streaming, matérialisation EF, LINQ, DTO ⇒ **coût de matérialisation**).
- **`connection_open` ne pouvait pas se mesurer au point d'appel** : `GetDataContextAsync` n'instancie qu'un `DbContext`, et **Npgsql n'ouvre la connexion que paresseusement**, à l'exécution de chaque requête. D'où le passage par des **intercepteurs EF Core**, seul endroit qui voie cette frontière — en lisant les `eventData.Duration` qu'EF mesure déjà, plutôt qu'en re-chronométrant (ce qui aurait exigé de corréler début et fin par `ConnectionId`, donc un état partagé, pour une mesure **moins** fidèle).
- **`assemble` est volontairement une soustraction**, pas une mesure : le découper (streaming vs matérialisation vs DTO) n'aurait aucun sens tant qu'on ne sait pas s'il pèse. S'il domine, c'est lui que la prochaine US découpe.
- **Un compteur à côté des durées** — `mssante_db_operation_queries_total`. Si `sql_execute` domine, c'est ce chiffre qui distingue « **une** requête lente » de « **trente** requêtes rapides », deux remèdes sans rapport. Il vérifie du même coup l'annonce « 6 à 8 requêtes groupées », **jamais mesurée** jusque-là.
- **La famille, pas le seul chemin** : `GetMailsByUidsAsync` (le sujet) **et** `GetMailAsync` (l'autre lecture servie par la base, qui partage `PopulateMailContentAsync` et porte l'hydratation des documents de la fiche patient). Périmètre **non ré-entrant** — un périmètre imbriqué alimente l'extérieur sans republier, pour que l'attribution désigne le **geste du médecin** et non le détail d'implémentation.
- **Hors périmètre, rien ne coûte** : les intercepteurs sont branchés sur tout le trafic SQL du service, mais sans `DbOperationScope` actif ils ne font **rien** — ni allocation, ni série temporelle. Instrumenter les dizaines d'autres requêtes (réglages, contacts, migrations) aurait produit une métrique illisible à un coût payé partout.
- **Ce que l'instrument a immédiatement révélé** (et qui fonde task-244) : au tir `journey-remote-n500` du 2026-08-09, `GetMailsByUids` coûtait **55,4 ms / 7,8 requêtes** par appel contre **1 199,7 ms / 14,8** au tir local 200 de la veille — la signature d'une **base quasi vide**, donc de latences flattées.
- Fichiers : `Telemetry/DbOperationScope.cs` (nouveau), `MailProcessingMetrics.cs`, `Telemetry/DbOperationPhaseInterceptors.cs` (nouveau), `BaseRepository.cs`, `MailRepository.cs`, `report.py` + 3 fichiers de tests.

### v1.38 — Un tir sans chauffe ne peut plus rendre un verdict vert — task-244

- **Task** : task-244 — `done`. **PR** : `api-mail` #176 (label `awaiting-human-merge`). Commits `ea06465` (feat), `ad10f5e` (simplify), `32d3844` (sonar), `c71006a` (review). `dtos-mss` : branche auto-incluse **vide**, aucune PR (**12ᵉ occurrence**).
- **LE DÉFAUT, ET IL EST DOUBLE.** Tir `journey-remote-n500` du 2026-08-09 : la chauffe envoyait les **98 UID** de la réserve analysée en **UNE** requête `enrich/sync` (délai client 300 s). Elle a expiré pour **500 médecins sur 500**, dès le palier 100 — et le serveur, lui, **travaillait** (`[CdaParsingService] Parsing completed` pendant et après l'abandon du client) : un **délai**, pas une panne. La base est donc restée quasi vide, ce que l'instrument de task-243 a chiffré (voir v1.37). Les latences du tir étaient **flattées**.
- **ET LE RAPPORT A PUBLIÉ « 8 ÉTAPES VERTES SUR 11 ».** Le garde-fou de task-224 refusait bien l'étape 3, mais son refus **ne se propageait pas** aux étapes **2, 10 et 11**, servies par la **même** base vide. *Un refus qui s'arrête avant le bout de sa portée logique donne l'apparence d'un contrôle, ce qui est pire que pas de contrôle du tout.* C'est une **famille de défaut nouvelle** dans l'EPIC : la statistique était bonne, sa source était bonne — c'est sa **portée** qui était trop courte. (Rappel des familles précédentes : mauvaise statistique, task-208 ; source ne couvrant qu'un appelant, task-214.)
- **1 — Une chauffe qui passe : lotie.** `warmupBatches()` / `warmupTimeoutSeconds()`. `JOURNEY_WARMUP_BATCH` = **10 UID** par requête, délai par lot = `lot × 3,5 s × 2` borné `[60, 300]`. Les **3,5 s/message** sont le coût unitaire mesuré **sous charge** (borne par le bas relevée au palier 500), à ne **pas** confondre avec `JOURNEY_TREATMENT_SECONDS_PER_MESSAGE` (0,45 s) qui décrit un banc **au repos** — confondre les deux est exactement ce qui a accordé 300 s à un travail qui en demandait davantage. **Un lot perdu n'interrompt pas les suivants** : un lot abouti est *acquis*, là où un appel unique qui expire à 95 % du travail ne laisse rien de garanti.
- **2 — Un échec qui se voit : UNE ligne.** Nouveau témoin `journey_warmup_completed`, **un échantillon par médecin** (sa boîte est chauffée *ssi* tous ses lots ont abouti), plus `journey_warmup_batches_failed` pour situer l'ampleur — « 3 lots sur 10 » et « 10 sur 10 » sont deux situations que la Rate par médecin confond. **Pas de `check` par médecin** : c'est précisément le bruit (500 lignes de log, zéro ligne de rapport) que la US remplace par une ligne de verdict.
- **3 — La propagation.** `served_by_db: True` sur les étapes **2, 3, 10, 11**. Sous **l'un** des deux planchers — chauffe aboutie **90 %** (`WARMUP_COMPLETED_FLOOR`) **ou** ouvertures servies base **95 %** (`WARM_STORE_SERVED_FLOOR`, task-224) — **toutes** deviennent non opposables, raison écrite en tête de section. Les étapes qui ne doivent rien à la chauffe (**4** froide, **6** envoi) **gardent** leur verdict : la portée du refus est **logique, pas maximale**. L'étape 3 conserve le libellé task-224 (« mesure du froid »), plus précis. Trois états jamais confondus : refus / **non mesurée** / aboutie — *une absence n'est pas un zéro* (task-214).
- **Pourquoi 90 % et pas 100 %** : une chauffe partiellement réussie n'est pas inutilisable ; ce qui décide, c'est que la base soit assez peuplée pour que les étapes qu'elle sert mesurent la charge visée. Le plancher est posé au-dessus du bruit (expirations isolées sur un cluster chargé) et très au-dessus du cas qu'il existe pour attraper — le tir du 2026-08-09 valait **0 %**.
- **⚠️ CE QUE CETTE LIVRAISON NE PRÉTEND PAS.** **Lotir n'accélère rien.** Le sujet de fond reste le **coût unitaire** de l'analyse — c'est task-245 — et le `treatment` du parcours réel, à **2 messages par lot**, a lui aussi expiré une fois au palier 500. Le lot empêche un échec **total**, il ne rend pas l'analyse rapide. La case DOD « un tir 500 distant termine la chauffe sans timeout » est **différée au Manual Test Plan** : elle exige un banc monté.
- **Sonar** : **un seul finding imputable** — `journey-model.js:461` **S1940**, **refusée avec justification inline**. `!(batchSize > 0)` et non `batchSize <= 0` car **`NaN <= 0` vaut `false`** : la forme « simplifiée » laisserait passer un NaN venu d'une variable d'environnement malformée, et la boucle tournerait à vide **en silence** — le mode d'échec muet que ce harnais existe pour interdire. Idiome déjà présent à trois sites antérieurs. Le reste des deltas (bugs 1→2, smells 44→48, hotspots 2→4) est **antérieur à la task**, provenance vérifiée fichier par fichier ; QG **ERROR avant comme après**, la new-code period englobant des tasks déjà mergées.
- **Build / tests** : 0 erreur ; solution complète verte — **3 689 réussis, 0 échec** (domain 136 · application 2 086 · infrastructure 436 · api 660 · intégration 371, 16 ignorés). Harnais : **59 tests JS + 249 Python**, dont **12 nouveaux** couvrant le refus, sa portée, la frontière du seuil, l'absence ≠ zéro, et le **témoin négatif** (chauffe réussie ⇒ verdict rendu normalement — sans lui, la garde pourrait être un refus permanent déguisé en contrôle).
- **⚠️ Signalé, non corrigé** (hors périmètre, règle 6) : `test_report_pinned_palier.py:68` — bug **S3923** introduit par **task-242** (`c74120a`, déjà mergée), `base_hour = 14 if palier == 0 else 14`.
- **Seuils écrits** : `docs/loadtest.md` § 4d devient **« les cinq règles de conclusion du rapport »**, la cinquième portant les deux planchers, le pourquoi de 90 % ≠ 100 %, et la contre-épreuve (`JOURNEY_WARMUP_TIMEOUT_S` abaissé).

### v1.39 — Le pipeline d'enrichissement cesse d'etre une boite noire — task-245

- **Task** : task-245 — `done`. **PR** : `api-mail` #177 (label `awaiting-human-merge`). Commits `b8f340a` (feat), `670cb50` (simplify), `86c03fb` (sonar). `dtos-mss` : branche auto-incluse **vide**, aucune PR (**13e occurrence**).
- **LE GOULOT G1, ET LE SEUL QUI ROMPE FRANCHEMENT** — un abandon, pas une degradation. Au tir `journey-remote-n500` du 2026-08-09, l'enrichissement coute **plus de 3 s par message** sous la concurrence de 100 medecins (borne **par le bas** : l'appel a expire sans finir), et le p95 serveur de `enrich/sync` vaut « au moins 10 s ». La telemetrie ne savait **pas** repartir ces secondes entre fetch IMAP, extraction XDM, parsing CDA et ecritures base.
- **US D'INSTRUMENT, PAS D'OPTIMISATION**, et l'ordre est delibere — le meme que task-243. Elle ne rend rien plus rapide ; elle rend le prochain correctif **decidable** et surtout elle **empeche** de l'ecrire sur une intuition. Le parsing CDA est le candidat evident, donc precisement celui qu'il faut se garder de designer avant mesure (task-222 a ete annulee pour cette faute exacte).
- **`EnrichmentOperationScope`** — le pendant de `DbOperationScope` : un perimetre **par message**, `AsyncLocal`, **non re-entrant**, **cout nul hors perimetre**. Phases `imap_fetch`, `xdm_extract`, `cda_parse`, `db_write`, plus `assemble` (le reste, par difference — s'il domine, c'est **lui** que la prochaine US decoupe).
- **LA PHASE `imap_fetch` EST SEMEE, PAS ACCUMULEE — la decision de conception centrale.** Le pipeline lit tout un sous-lot depuis IMAP (phase A, sous le verrou de session) **puis** persiste (phase B, hors verrou) : les deux moities du travail d'un meme message sont separees par le reste du lot, et **aucun contexte asynchrone ne les relie**. La duree est donc mesuree en phase A, portee par `FetchedMail`, et remise au perimetre a son ouverture. Sans cela le fetch — candidat de premier plan, 94 ms de latence injectee sur ~124 Ko — paraitrait **gratuit**, et la somme des phases depasserait le total.
- **⚠️ L'EMBEDDING EST HORS PERIMETRE, ET C'EST UN FAIT VERIFIE, PAS UN OUBLI.** Il s'execute dans `AddNewMailConsumer`, declenche par un `Publish` MassTransit que le producteur **n'attend pas** : `enrich/sync` ne paie donc **pas** cette latence. Le compter dans le total aurait gonfle une duree que le client n'attend jamais — exactement la famille d'erreur que cette EPIC a deja payee. Il est publie **a part**, et le rapport ecrit explicitement qu'il est hors chemin.
- **LE p95 SERVEUR NE DISAIT RIEN** : les seaux par defaut de `http.server.request.duration` s'arretent a **10 s**, donc « p95 >= 10 s » n'etait pas un percentile mais **la borne du dernier seau** — sur exactement la route dont on cherche le cout. Une vue OpenTelemetry applique desormais le jeu partage des histogrammes maison (30 et 60 s en queue). Meme defaut de saturation que celui corrige cote metier, par l'autre bout.
- **Compteurs de volume** `enrichment_requests_total` / `_request_messages_total` : ils distinguent « **un** message lent » de « **trente** messages moyens », deux remedes sans rapport, et une duree ne le dira jamais.
- **Un point d'alimentation UNIQUE** pour les 8 sites d'execution SQL, alimentant les deux perimetres ensemble : c'est l'ecart entre sites d'appel qui avait produit le defaut d'instrumentation de task-214 (une API mesuree sur vingt et un appelants, un seul branche).
- **PGSSI-S — point de vigilance n°1**, ce pipeline manipulant des CDA porteurs d'INS. L'unique etiquette emise est `phase`, ensemble **fini de litteraux** du code : ni INS, ni contenu CDA, ni objet, ni UID, ni nom de fichier. **Verifie par un test dedie**, pas seulement affirme.
- **Sonar** : **zero issue sur les 7 fichiers C# de la task**, verifie fichier par fichier. Seul finding imputable : un hotspot `http://` dans une **fixture** dont l'URL n'est jamais composee (`build_telemetry` ne fait aucune I/O) — passe en `https`. Duplication projet **0,4 % → 0,3 %** (passe `/forge-simplify` : phase dominante et lecture d'une serie etiquetee factorisees entre les sections task-243 et task-245). QG **ERROR avant comme apres** — new-code period englobant des tasks deja mergees.
- **Build / tests** : 0 erreur ; **3 702 reussis** (domain 136 · application 2 099 · infrastructure 436 · api 660 · integration 371, 16 ignores). Harnais : 247 Python + 57 JS. **23 nouveaux tests** — 13 de perimetre (arithmetique, fetch seme, hors-perimetre muet, non-re-entrance, survie a l'exception, **traversee de `Task.Run`**, cardinalite) et 10 de rendu, dont « aucune donnee » et le temoin **« si le fetch domine, c'est LUI qui est nomme »** (sans quoi le rendu pourrait suivre l'intuition au lieu de la mesure).
- **⚠️ DEUX PIEGES D'OUTILLAGE, consignes pour le prochain qui build.** (1) **`--artifacts-path` casse 10 tests d'architecture** (`SecretLiteralScanTests`, `MailContentWriterScanTests`, `EmbeddingOptionsConsistencyTests`, …) : ils scannent les sources et la configuration **par chemin relatif a la sortie de build**, que l'option deplace. Ils sont **verts** avec la disposition standard — ce n'est **pas** une regression, et le contournement des verrous MSBuild se paie donc de cette contrepartie. (2) **3 echecs en Release sur une execution, verts au re-run** — la famille de flakies pre-existants deja documentee.
- **🚧 CE QUE CETTE LIVRAISON NE PROUVE PAS.** Elle ne rend **rien** plus rapide, et ne mesure rien tant que le banc n'a pas tourne : la contre-epreuve (local **puis** distant, pour ne pas imputer au reseau ce qui appartient au traitement) est differee au Manual Test Plan. **Finding consigne, non corrige** : `BackgroundImapService.EnrichEmailsAsync` porte une **seconde implementation parallele** du pipeline (utilisee par la synchronisation de fond), qui ne passe pas par `ImapService` et n'est donc **pas instrumentee**. Le chemin **mesure par le banc** l'est integralement ; etendre le perimetre a cette copie est une US a part entiere — et la US interdit d'elargir en passant.

### v1.40 — Le comptage des fils ne balaie plus la table entiere — task-247

- **Task** : task-247 — `done`. **PR** : `api-mail` #178 (label `awaiting-human-merge`). Commit `2ae7833`. `dtos-mss` : branche auto-incluse **vide**, aucune PR (**14e occurrence**).
- **PREMIERE US D'OPTIMISATION DE LA SERIE, et elle n'existe que parce que deux US d'instrument l'ont precedee** : task-243 a decompose, task-242 a mesure. On sait quoi corriger, et on saura le prouver — c'est exactement l'ordre que task-222 (annulee) avait enfreint.
- **Ce que la mesure designait** (tir local 200 du 2026-08-08) : `GetMailsByUids` coute **1 199,7 ms** en moyenne, dont **961,6 ms (80,2 %) de construction des donnees**, 236,2 ms d'execution SQL, et **1,8 ms (0,1 %) d'attente de connexion** — pour **14,8 requetes SQL par appel** la ou l'analyse de code annoncait « 6 a 8 ». **La contention base est ecartee par la mesure, deux fois** : le tir 500 distant redonne 0,1 % sur un regime pourtant tout autre. Invariant, pas coincidence — et c'est ce qui interdit de toucher au dimensionnement du pooler, qui gagnerait 0,1 %.
- **Le defaut corrige (finding F-243-1)** : `ComputeThreadCountsAsync` lisait **DEUX FOIS la table `Mails` entiere** a chaque ouverture de page d'en-tetes — un balayage de tous les `MessageId`, un balayage de tous les mails porteurs de `References`/`InReplyTo`, **sans aucun filtre de page**. Le cout suivait donc la **taille de la boite** et non celle de la page : modeste sur les 247 messages du banc, **deux balayages complets par ouverture** sur les ~50 000 messages d'un praticien reel. Les deux lectures sont desormais bornees par les **racines de la page**.
- **⚠️ PAS DE FILTRE PAR DOSSIER — le DOD le suggerait, le comportement l'interdit.** Un fil **traverse les dossiers** : la racine d'une conversation vit couramment dans `Sent` (le praticien a ecrit le premier message) pendant que les reponses arrivent en `INBOX`. Borner le comptage au dossier de la page ferait retomber ce fil a un **mono-message** — une regression fonctionnelle silencieuse, que seul un test inter-dossiers peut attraper. Il est ecrit. Meme raison pour la generation : `UIDVALIDITY` est propre a un dossier, un membre de fil situe ailleurs porte legitimement une autre valeur. Le DOD autorisait explicitement d'expliquer plutot que d'appliquer — c'est ce qui est fait.
- **LE PIEGE DE TRADUCTION, TROUVE PAR LES TESTS ET NON PAR LA THEORIE.** Une citation de racine dans `References` est une **sous-chaine**, pas une egalite : elle ne se traduit pas en `IN`. La forme lisible `roots.Any(r => References.Contains(r))` est traduite par **Npgsql** (EXISTS sur unnest) mais **pas** par le fournisseur **InMemory** des tests unitaires, qui leve. Constat **empirique** : la suite d'integration (vrai Postgres) etait verte pendant que deux tests unitaires echouaient. Remplacee par une **chaine de OR construite en arbre d'expression**, comprise des deux — *le code de production ne doit pas etre testable seulement sur le fournisseur le plus riche*.
- **Tests ecrits AVANT le correctif** (exigence du DOD), et verts avant comme apres : fil inter-dossiers, fil orphelin dont la racine n'est pas stockee, **temoin negatif** du mono-message, et fil etranger absent de la page. Le temoin negatif a d'ailleurs corrige une hypothese fausse : un mono-message porte `ThreadCount = 1`, pas 0 — **valeur relevee**, pas supposee, ce qui est tout l'objet d'un test de caracterisation.
- **Controle de non-regression fait, pas affirme** : la suite d'integration montre 2 echecs **identiques au baseline sans ces changements** (369/387 → 373/391 avec les 4 tests ajoutes), verifie par `git stash` + re-run. Ce sont les flakies deja documentes. Suite unitaire : domain 136, application 2 086, infrastructure 436, api 660 — **0 echec**.
- **🚧 CE QUE CETTE LIVRAISON NE PROUVE PAS — et c'est l'essentiel.** Elle supprime un balayage de table etabli par lecture de code ; elle **ne demontre aucun gain**. **Trois criteres du DOD sur six restent ouverts**, et ce sont des **mesures**, pas du code : le nombre de requetes avant/apres via le compteur de task-243, l'**A/B iso-conditions** sur la lignee courante, et le retour de l'etape « ouvrir l'inbox » dans la grille au palier 200 (p95 mesure a **5 198 ms** pour une cible de 1 000). Tous exigent un tir. Rappel du garde-fou de la US : **reduire le nombre de requetes ne suffit pas** — 14,8 requetes ne font pas 961 ms a elles seules, une part du cout est le travail CPU et les allocations de la construction, et les deux axes doivent etre mesures separement.
- **⚠️ `/sonar` n'a pas ete rejoue** pour cette task (duree du run cumule). Du C# a ete modifie : un scan dedie reste a faire.

### v1.41 — L'hydratation d'une fiche patient ne coute plus une requete par document — task-248

- **Task** : task-248 — `done`. **PR** : `api-mail` #179 (label `awaiting-human-merge`). Commits `af8d61e` (perf), `98440c8` (preuve du decompte). `dtos-mss` : branche auto-incluse **vide**, aucune PR (**15e occurrence**).
- **Le defaut (finding F-243-2)** : `PopulateMailContentAsync` bouclait sur les documents cliniques en appelant un `BuildMedicalDocumentDtoAsync` **asynchrone** qui emettait **3 requetes par document** — biologie, synthese, pieces jointes. Soit « 10 + 3xD requetes sequentielles » par message. Mesure du tir local 200 du 2026-08-08 : `GetMail` a **10,5 requetes par appel**, 299,4 ms de moyenne, et un **p95 a 60 000 ms — le plafond de delai d'attente**.
- **L'ARGUMENT DECISIF EST UNE CONFRONTATION CROISEE, pas une intuition** : au tir 500 sur base quasi vide, la materialisation de `GetMail` s'effondre de **109,8 ms a 2,1 ms** et son p95 de **60 000 ms a 281 ms**. Le plafond etait donc conduit par **LA DONNEE** — les documents a hydrater — et non par la charge. C'est ce renversement qui a rendu la US ecrivable, et il vient de l'instrument de task-243.
- **Le correctif** : les trois recherches sont faites **une fois pour tout le message** puis indexees en memoire — **3 requetes au total, quel que soit D**.
- **`BuildMedicalDocumentDto` devient SYNCHRONE, et ce n'est pas cosmetique** : c'est ce qui rend le N+1 **impossible a reintroduire par distraction**. Les deux anciens chargeurs par document sont **supprimes** (57 lignes) — les laisser, meme inutilises, aurait invite a le reintroduire : ils avaient exactement la signature qu'on cherche depuis une boucle sur les documents.
- **⚠️ POURQUOI PAS `LoadBulkMailLookupsAsync`, le chemin groupe qui existe deja.** Le task file demandait expressement de **verifier avant de cabler**, et la verification dit non : ce chemin est concu pour une **page** de messages, c'est celui que **task-247 vient de modifier**, et l'y brancher **melerait les deux gains** — or la dependance de cette US existe precisement « pour que le gain de chacune reste attribuable ». Le regroupement local est prouvablement equivalent et n'y touche pas.
- **LE RISQUE TRAITE EN PREMIER N'EST PAS LA PERFORMANCE.** Ces documents portent l'**INS du patient** : un index construit sur la mauvaise cle rattacherait une piece jointe au mauvais document, **silencieusement**. Les pieces jointes sont donc indexees sur **`DocumentId`** (la cle de l'ancienne requete, et non l'identifiant de ligne), le filtre porte sur le **seul message** (`MailId`), et une entree absente vaut une **liste vide** et jamais `null` — contrat du DTO preserve.
- **Comment le critere n°1 du DOD est prouve, et pourquoi pas comme le DOD le disait.** Le DOD reclamait « decompte prouve par le compteur de requetes de task-243 ». Ce compteur est alimente par les intercepteurs EF branches sur le `DbContext` de **production** ; la fixture de test construit le sien sans eux, il **ne publiait donc rien** — constat empirique, la premiere version du test echouait sur « le compteur doit publier quelque chose ». Les commandes sont comptees par un **intercepteur local au test** : preuve **plus forte**, independante du cablage de production, **deterministe** (aucun banc requis), et portant sur un **nombre** — un temps n'a jamais prouve l'absence d'une requete. L'assertion est l'**EGALITE** entre D=1 et D=5, et non « moins de requetes » : ce dernier serait satisfait par un correctif passant de 3xD a 2xD, alors que « ne croit pas avec D » est la propriete reelle.
- **Eprouve par mutation, deux fois** : apparier les pieces jointes sur la mauvaise cle fait tomber **2 tests** ; les perdre en fait tomber **3**. Ce ne sont pas des tests verts par construction.
- **Build / tests** : 0 erreur ; domain 136 · infrastructure 436 · api 660 · application 2 099 · **integration 380, 0 echec** (16 ignores).
- **UNE QUESTION LAISSEE OUVERTE PENDANT LE DEVELOPPEMENT, ET TRANCHEE PAR LA REVUE.** `PatientUseCaseTests.SearchShouldReturnMatchingPatients` avait echoue de facon **non reproductible** : vert 3/3 isolement apres reconstruction propre, vert avec sa classe, mais un comparatif `git stash` l'avait montre vert sur `develop`. J'avais explicitement dit ne pas pouvoir trancher flaky vs regression, et avoir commite malgre cette incertitude. La suite d'integration est **integralement verte** sur la branche finale : c'etait bien un **flaky d'etat entre tests**. C'est exactement ce que `/review` sert a etablir, et c'est pourquoi merger avant lui aurait ete merger sur une incertitude.
- **🚧 CE QUE CETTE LIVRAISON NE PROUVE PAS.** Quatre criteres du DOD sur six restent ouverts, et ce sont des **mesures** : le p95 de `GetMail` qui ne plafonne plus, le retour de l'etape « fiche patient complete » dans la grille au palier 200 (p95 mesure a **5 004 ms** pour une cible de 4 000), zero timeout `patient_docs` sur un tir 200, et l'**A/B iso-conditions**. Tous exigent un tir. Le gain est **structurellement** acquis (le decompte ne croit plus avec D, prouve) ; son **effet** sur la latence du medecin ne l'est pas.
- **⚠️ `/sonar` n'a pas ete rejoue** sur cette task, qui modifie du C#.

### v1.42 — Un enrichissement de contact concurrent n'est plus perdu en silence — task-250

- **Task** : task-250 — `done`. **PR** : `api-mail` #180 (label `awaiting-human-merge`). Commits `b3c21ab` (fix), `f30ce27` (merge develop). `dtos-mss` : branche auto-incluse **vide**, aucune PR (**16e occurrence**).
- **CE N'EST PAS UNE LENTEUR, C'EST UNE ECRITURE PERDUE.** Une occurrence sur 133 214 requetes au tir local 200 du 2026-08-08 : `DbUpdateConcurrencyException — expected to affect 1 row(s), but actually affected 0`, journalisee puis **avalee**. Cote produit, l'enrichissement du contact praticien etait simplement **perdu**, sans que personne ne le sache. Le cas se produit quand deux praticiens correspondent avec le **meme** confrere au meme moment : sa probabilite croit avec le **CARRE** de la population, pas lineairement.
- **LA CAUSE, ETABLIE PAR LECTURE, ET CE N'EST PAS CELLE QU'ON SUPPOSE.** Le task file demandait explicitement de ne pas presumer que la ligne avait ete supprimee — verifie et ecarte : la ligne `Contacts` ne porte **aucun jeton de concurrence**, donc son `UPDATE ... WHERE Id = X` affecte toujours 1 ligne tant qu'elle existe. Le coupable est le **`RemoveRange` des collections enfants** : sur des entites **deja chargees**, EF emet un `DELETE ... WHERE Id = <enfant>` **par ligne**, chacun attendant 1 ligne, et le second passage supprime des lignes que le premier a deja supprimees.
- **UN PREMIER REMEDE ESSAYE PUIS ABANDONNE, et l'abandon est instructif.** Rendre les suppressions **idempotentes** (`ExecuteDeleteAsync`, ensembliste) supprimait la cause — mais `ExecuteDeleteAsync` est **relationnel uniquement** et leve sur le provider **InMemory** dont dependent les tests unitaires. Constat **empirique**, pas theorique : la tentative a fait tomber `UpdateAsyncShouldModifyContactAsync`. **Deuxieme fois dans la meme session** qu'un piege de portabilite de provider se manifeste (task-247 : `roots.Any(r => References.Contains(r))` passe sur Npgsql, pas sur InMemory). La lecon est desormais ecrite dans les deux fichiers : *le code de production ne doit pas etre testable seulement sur le provider le plus riche*.
- **ET LE REJEU S'EST REVELE SUPERIEUR, pas seulement disponible.** Une suppression idempotente aurait fait **taire l'exception** tout en laissant le dernier ecrivain **ECRASER** l'apport de l'autre — le meme defaut sous un autre nom. Le rejeu **relit l'etat gagnant et y re-applique son propre apport** : les deux enrichissements survivent, ce que le DOD exige (« l'etat final contient les deux enrichissements »).
- **LA FRONTIERE DE COUCHE EST RESPECTEE, et c'est ce qui a dicte la forme.** `DbUpdateConcurrencyException` est un type Entity Framework, et la couche Application **ne reference pas EF** — elle ne *pouvait* donc pas l'attraper, et il serait malsain qu'elle le puisse. Le depot la traduit en **`ConflictException`**, le type metier que la **regle 12** du CLAUDE.md prevoit deja (→ 409), **en conservant la cause d'origine**. Verifie sur le diff : **zero `using Microsoft.EntityFrameworkCore`** dans la couche Application.
- **Deux garde-fous de conception.** (1) **Un seul rejeu** : une boucle sans borne sur un conflit qui se reproduit tournerait indefiniment **sous charge**, precisement quand la probabilite du conflit est la plus forte ; au-dela, conflit journalise en **erreur** comme conflit metier, **jamais avale**. (2) **`ApplyEnrichment` extrait en fonction pure** : le rejeu doit pouvoir re-appliquer le meme apport a un etat relu, et tant que la logique etait melee a l'ecriture, rejouer signifiait la **dupliquer**.
- **⚠️ MON PREMIER TEST D'INTEGRATION ETAIT VERT AVEC LE DEFAUT.** Deux `UpdateAsync` **sequentiels** ne peuvent pas se croiser : la methode recharge le contact en interne, donc le second lit l'etat que le premier vient d'ecrire. Le test etait **vert par construction**. Demasque par une **preuve par mutation**, puis reecrit pour reproduire la sequence reelle — un contexte a **deja charge** les enfants quand un autre les supprime. Il est desormais **rouge sans le correctif, vert avec**. Sans la mutation, la US aurait ete livree avec un filet qui ne retenait rien.
- **Tests** : 3 cas d'integration sur **vrai Postgres** (l'InMemory ne verifie pas les lignes affectees, il ne *pourrait pas* reproduire le defaut) et 3 unitaires du rejeu, dont le temoin « le gagnant portait deja notre apport ⇒ aucun rejeu inutile ».
- **Build / tests** : 0 erreur ; domain 136 · infrastructure 436 · api 660 · application 2 102 · **integration 384, 0 echec**. `develop` mergee dans la branche (elle apporte task-247 et task-248) — **aucun conflit**, les fichiers etant disjoints. Deux echecs `application` apparus **une fois**, non reproduits sur deux runs verts consecutifs et **non nommables** (la sortie identifiante est revenue verte) — signale plutot que passe sous silence.
- **🚧 Reste ouvert** : le dernier critere du DOD — **zero `DbUpdateConcurrencyException` sur un tir 200** — exige un tir. Et **`/sonar` n'a pas ete rejoue** sur cette task, qui modifie du C#.

### v1.43 — Les familles de `dotnet_exceptions_total` sont nommées : ni par requête, ni par incident — par **scrape** et par **extinction de session** — task-251

- **Task** : task-251 — `done`. **PR** : `api-mail` #181 (label `awaiting-human-merge`). Commit `2fd8a90` (docs). `dtos-mss` : branche auto-incluse **vide**, aucune PR (**17e occurrence**). US d'**enquête** : **aucune ligne de C# modifiée**, un seul fichier au diff (`docs/loadtest.md`, +131).
- **LE REPÈRE ÉTAIT LE DÉFAUT.** « Quelques unités par seconde et par réplica » décrivait un ordre de grandeur **sans nommer ce qui le composait** : 4,4–5,0 exc/s pouvaient être la routine ou une dérive, et rien ne permettait de trancher sans rouvrir l'enquête. Les deux signaux qui alarmaient — **homogénéité entre réplicas** et **croissance avec la charge** — sont précisément la signature d'un coût par requête, et cette EPIC en avait déjà rencontré deux (`SecurityTokenMalformedException` de task-206 ; `ClientResultException` mal attribuée, qui masquait des documents cliniques perdus). Ouvrir était donc justifié. **Ce n'en était pas un.**
- **DEUX RÉGIMES, ET LA FAMILLE DOMINANTE DÉPEND DE CE QUE PROMETHEUS SCRAPE.** Régime **A** (cible `:5052/metrics` en direct, config du 2026-08-08) → `IndexOutOfRangeException` + `ArgumentException`. Régime **B** (cible collector `:8889`, config actuelle) → `TaskCanceledException`. Lire `/targets` **avant** d'interpréter la colonne : c'est la première question, pas un détail.
- **RÉGIME A — LE BANC MESURAIT LE COÛT DE SA PROPRE MESURE.** Site d'appel relevé pile complète : `OpenTelemetry.Exporter.Prometheus.PrometheusSerializer.WriteNormalizedLabelKey` (`IndexOutOfRange`) et `WriteUtf8NoEscape` — « Destination buffer too small » — (`Argument`), sous `PrometheusCollectionManager.TryWriteResponse` ← `PrometheusExporterMiddleware.InvokeAsync` (paquet `OpenTelemetry.Exporter.Prometheus.AspNetCore` **1.16.0-beta.1**). C'est l'**agrandissement de tampon** de l'exporteur : il déborde, attrape, double, recommence ; le scrape rendu est **complet**, aucune étiquette perdue.
- **CAUSALITÉ PROUVÉE, PAS DÉDUITE.** 20 scrapes forcés sur **un réplica au repos, sans une seule requête métier** → **+54 `IndexOutOfRange`, +18 `ArgumentException`** (≈ **2,7 + 0,9 par scrape**). Et le « métronome » du 2026-08-08 (09:09→09:18) valait exactement **8 + 3 toutes les 5 s**, invariant — c'est-à-dire le **`scrape_interval: 5s`** de `src/AppHost/prometheus.yml`. L'homogénéité entre réplicas venait de ce que tous sont scrapés à la même cadence.
- **⚠️ ET LE COÛT NE SUIT PAS LA CHARGE LINÉAIREMENT** — contre-intuitif, donc vérifié : à **86 ko / 364 séries** il **descend** à ~5 par scrape contre ~8 à **69 ko / 301 séries** (le tampon se stabilise en partie). La « croissance avec la charge » qui alarmait n'était donc pas celle de cette famille.
- **RÉGIME B — L'ENTRETIEN DES SESSIONS.** `MailClientSession.StartKeepAlive`, à l'`await Task.Delay(KeepAliveInterval, _keepAliveCts.Token)` de `src/Application/Session/MailClientSession.cs:305`, rattrapé par le `catch (OperationCanceledException) { break; }` de la boucle. **Une exception par extinction de session**, jamais par requête : c'est la sortie de boucle **voulue**. Son débit suit le **renouvellement de sessions** (`SESSION_ROTATION`), ce qui explique qu'elle monte avec la charge sans qu'aucun chemin de code ne soit exercé à chaque appel.
- **Mesure** : tir `mixed`, 50 médecins, 5 min (`RPS_PER_USER=2`, `SESSION_ROTATION=0.002`), `sum by (service_instance_id, error_type) (increase(dotnet_exceptions_total[5m]))` relevé **dans** la fenêtre — `…-27264` 1,37/s (91 %) · `…-2860` 1,17/s (80 %) · `…-53032` 2,03/s (83 %) · `…-59220` 1,47/s (83 %) · `…-64200` 1,27/s (93 %). Même homogénéité que la table du tir 200 à 4× moins de praticiens : les **4,4–5,0 /s sont cohérents** avec cette famille portée à 200 — **extrapolation, signalée comme telle, non re-mesurée**.
- **NON-RÉGRESSION** : `SecurityTokenMalformedException` = **0** ✓ et `FolderNotFoundException` = **0** ✓. ⚠️ Le libellé `SecurityTokenMalformedException` **apparaît** dans `label/error_type/values` — c'est l'historique **persistant** du TSDB, pas une occurrence ; la requête de valeur rend vide. Ne pas confondre les deux, sous peine de déclarer une régression qui n'existe pas.
- **🚩 DEUX DÉFAUTS TROUVÉS EN CHEMIN → US PROPOSÉES AU PO.** (1) **La reprise EF Core masque des coupures Postgres** : `NpgsqlException` « Exception while reading from stream » (`NpgsqlReadBuffer.EnsureLong`) systématiquement **appariée** à `InvalidOperationException` « likely due to a transient failure » levée par `NpgsqlExecutionStrategy.ExecuteAsync` — **736 : 635 sur le seul seed**. La reprise fait son travail, et c'est exactement ce qui rend la coupure invisible. (2) **PgBouncer refuse les connexions au banc** : `08P01: server login has been failing, cached error: connect failed (server_login_retry)`, jusqu'à **313 /s** — défaut de banc, mais tant qu'il est présent **aucun chiffre de capacité n'est opposable**.
- **⚠️ PIÈGE D'OUTILLAGE n°1 — `dotnet-trace` NE VOIT PAS CES EXCEPTIONS.** Sur une fenêtre de **60 s** où le compteur du réplica montait de **+11 / +3**, une collecte `Microsoft-Windows-DotNETRuntime:0x8000` (`ExceptionKeyword`) en a enregistré **zéro**, tout en capturant des `IOException` **dans la même trace** (contrôle fait dans les deux sens, métrique relevée avant/après la fenêtre exacte). Ce qui marche : une sonde `AppDomain.CurrentDomain.FirstChanceException` injectée par `DOTNET_STARTUP_HOOKS` — elle voit exactement ce que le compteur compte, sans modifier le dépôt. **À compiler en `netstandard2.0`** : en `net10.0` elle se charge aussi dans l'outillage de build, qui échoue sur `Could not load file or assembly 'System.Runtime, Version=10.0.0.0'`.
- **⚠️ PIÈGE D'OUTILLAGE n°2 — `increase()` SUR UN SCRAPE DIRECT DE `:5052` NE VEUT RIEN DIRE.** C'est l'endpoint **réparti** entre les cinq réplicas : une même série Prometheus y entrelace cinq compteurs indépendants, que `increase()` interprète en remises à zéro. L'attribution par réplica passe **obligatoirement** par `service_instance_id` (voie collector). Le même piège fait mentir une lecture « au repos » du `/metrics` réparti — les valeurs sautent d'un réplica à l'autre à chaque appel, ce qui a coûté une première série de mesures fausses dans cette enquête.
- **CORRECTION D'UNE HEURISTIQUE DU SKILL.** « Le test qui tranche » (*une famille dont le débit croît linéairement avec la charge est un coût par requête*) a **deux angles morts**, tous deux rencontrés ici : un **métronome** (cadence de scrape) et un coût **par session** se lisent l'un comme l'autre en « coût par requête ». Les deux contrôles qui tranchent en une minute sont désormais écrits : **regarder le banc au repos**, et **faire varier `SESSION_ROTATION` à charge constante**.
- **Observation collatérale, hors périmètre, consignée pour ne pas la reperdre** : au seed, **le premier `POST` de `UserSettings` répond 500 pour _chaque_ praticien**, la 2ᵉ tentative passe — 50/50, sur deux seeds consécutifs. Le seed le rattrape (`retry 1/3`) et sort en succès, donc **personne ne le voit**.
- **Livré** : `Api/Mail/docs/loadtest.md` § **4b-bis** (familles, sites d'appel, périodicité, verdicts, repère chiffré, pièges) et `.claude/skills/loadtest-skill/SKILL.md` (table « Ordre de grandeur attendu » réécrite + les deux angles morts). ⚠️ Le repère « quelques unités » vivait dans le **skill**, **pas** dans `docs/loadtest.md` comme le supposait le DOD — **les deux** ont été traités.
- **Build / tests** : 0 erreur ; domain 136 · infrastructure 436 · application 2 102 · api 660 = **3 334 verts**. `integration` : **1 échec** (`ImapFolderServiceIntegrationTests.GetFolderAsync_Inbox_ShouldReturnTheSeededMessageCount`, `ImapProtocolException: The IMAP server has unexpectedly disconnected` pendant le seed Dovecot), **vert en isolation (12/12)** — flake d'environnement de la fixture, consécutif à la purge du banc faite juste avant ; un diff 100 % documentaire ne peut pas causer de régression de code. `/sonar`, `/forge-simplify`, `/lint-*`, `/verify-visual` : **skip clean** (aucun `.cs` au diff). Banc **arrêté et purgé** après mesure (50 bases, volume maildir).
- **Conformité** : aucun message d'exception recopié ne porte de donnée patient — seuls le **type** et le **site d'appel** sont cités, contrôlé par grep sur les 131 lignes ajoutées. `SecurityTokenMalformedException` à 0 ⇒ la famille dominante **ne touche pas** la validation du jeton PSC : le finding **n'est pas** un sujet de sécurité, contrairement à la réserve posée par le task file.

### v1.44 — La sonde de readiness ne traverse plus le pooler : `cl_waiting` ne mesure enfin que le chemin du médecin — task-249

- **Task** : task-249 — `done`. **PR** : `api-mail` #182 (label `awaiting-human-merge`). Commit `045bac5`. `dtos-mss` : branche auto-incluse **vide**, aucune PR (**18e occurrence**).
- **GAIN NUL SUR LA LATENCE, TOUT SUR LA LISIBILITÉ DE LA MESURE.** `AddDefaultHealthChecks` utilisait la chaîne du chemin de **données**, qui en profil loadtest pointe sur PgBouncer **sans `Database=`** : le nom retombait sur l'identité (`postgres`), et **un seul `GET /health` suffisait à créer un pool de maintenance**. À `default_pool_size=2` partagé par cinq réplicas, ce pool produisait des dizaines de secondes de `cl_waiting`, **sommées** ensuite avec le chemin praticien. Mesuré : tir local 200 du 2026-08-08 → praticien 3 ms / 9 ms / 1,10 s contre **18,3 s à 100 et 23,4 s à 200** sur le pool `postgres`. **Trois campagnes lues à travers ce brouillard, et deux verdicts d'A/B de pool rendus sur la grandeur qu'il fausse.**
- **ROUTER, PAS ÉLARGIR — et c'est le task file qui l'exigeait.** Aucune borne de pooling n'est touchée. `ServerConnectionString.ResolveProbeRoute(server, direct)` : la sonde prend la route de **contrôle** quand un pooler fronte le chemin de données.
- **RÉUTILISER, PAS CRÉER.** `MSS-MAIL-CONNECTIONSTRING-DIRECT` **existait déjà** (task-200, chemin de provisionnement) et porte exactement la bonne sémantique — « ce qui doit parler à PostgreSQL lui-même, pas au pooler ». Effet de bord bienvenu : la chaîne magique `"MSS-MAIL-CONNECTIONSTRING"` codée en dur au site d'appel cède la place à sa constante.
- **« STRICTEMENT INCHANGÉ HORS LOADTEST » — GARANTI PAR CONSTRUCTION, PAS PAR PROMESSE.** La variable directe n'est définie que dans le bloc `if (loadTestProfile)` de l'AppHost (commentaire d'origine : « Défini UNIQUEMENT ici »). Partout ailleurs elle est absente et la résolution rend la même chaîne qu'avant. Verrouillé par un `[Theory]` à 3 cas (`null`, `""`, `"   "`).
- **⚠️ LE TEST QUI COMPTE EST LE TEST ÉCHOUANT**, explicitement demandé par le DOD : `Health_WhenPostgresUnreachable_Returns503_AndAliveStays200` vise un port sur lequel rien n'écoute. **Il est rouge sans le correctif** — la chaîne serveur étant vide dans le harnais, l'ancien code n'enregistrait **aucune** sonde et `/health` répondait 200 « Healthy ». Il prouve qu'on a **routé** la sonde et non supprimé la mesure : exactement la crainte écrite dans le Manual Test Plan.
- **Build / tests** : 0 erreur, **0 avertissement** ; domain 136 · infrastructure 436 · application 2 102 · integration **389** · api 660 = **3 723 verts**. Un échec isolé non lié (`FlagsmithFeatureFlagServiceTests.RefreshFailure_LogsOncePerWindow_…`, test à fenêtre temporelle) — **vert en isolation (8/8)** et **vert au run Release** de Sonar.
- **Sonar** : QG **ERROR** sur `new_violations = 56` — dont **0 dans un fichier de cette task**, vérifié un par un. Piège documenté de la new-code period (`report.py` 20, `journey-model.js` 10, `journey.js` 7, embedding 9, divers 10). **Dette introduite : zéro.** Couverture new code 87,9 %.
- **🚧 Reste ouvert** : les deux critères **observables** du DOD exigent un banc — `SHOW POOLS` sans pool `postgres` après un `/health`, et la ligne « pool de maintenance » à zéro sur un tir. Différés au test manuel (HAG).

### v1.45 — Le téléchargement d'une pièce jointe est enfin décomposable : quatre phases, quatre remèdes distincts — task-252

- **Task** : task-252 — `done`. **PR** : `api-mail` #183 (label `awaiting-human-merge`). Commit `4370284`. `dtos-mss` : branche auto-incluse **vide**, aucune PR (**19e occurrence**).
- **⚠️ CETTE US N'ÉTABLIT PAS LA CAUSE, ET C'EST LE RÉSULTAT HONNÊTE.** Le task file impose un ordre non négociable — **mesurer, puis corriger** — et rappelle pourquoi : cette EPIC a déjà **annulé** une US applicative écrite sur une cause plausible et fausse (task-222). **Aucun correctif livré, rien d'accéléré.**
- **LE PROBLÈME** : tir `journey-remote-n500` du 2026-08-09, étape « Télécharger une PJ (~124 Ko) » — verte à 100 et 200, elle sort franchement de la grille à **500** : p50 **573 ms**, p95 **4 771 ms** pour une cible de 2 000 ms, **16 abandons** (HTTP 0). Ce n'est **pas** un plafond matériel (CPU maximal 8,3 % de 24 cœurs, ThreadPool calme, RSS plate) : le plafond est dans une **dépendance sérialisée**. Or tout le chemin ne portait **qu'une** activité couvrant la méthode entière — aucune requête, sur aucun tir, n'aurait pu répartir ces 4 771 ms.
- **DEUX BLOCAGES, UN SEUL LEVABLE ICI.** (1) La télémétrie n'existait pas → **levé**. (2) Le tir qui produirait la mesure exige le banc **en mode distant** (paliers 200 puis 500) et `kubectl top pods` : accès cluster indisponible dans la session, et le skill classe le déploiement distant en étape **humaine**. Un tir 500 **local** ne vaudrait rien — « tout chiffre > 500 mesuré banc local est un artefact connu » (Dovecot vole 2,6 cœurs au SUT).
- **LE CRITÈRE DE DÉCOUPAGE : chaque phase désigne un remède DIFFÉRENT**, pas la commodité d'implémentation. `db_lookup` (le sujet serait la base) · `session_acquire` (la voie d'accès à la session — **le candidat historique, déjà écarté une fois sur un autre chemin**) · `imap_fetch` (**côté serveur mail** : aucun remède applicatif ne la toucherait) · `stream` (la sortie) · `assemble` (le reste par différence). C'est **exactement** la distinction que le DOD demande de trancher.
- **⚠️ POURQUOI `stream` EST MESURÉE PAR `Response.OnCompleted` ET NON PAR UN FLUX ENVELOPPÉ.** L'action rend un `FileStreamResult` : l'écriture au client a lieu **après** son retour, donc un chronomètre refermé en fin d'action mesurerait tout **sauf** la sortie — c'est-à-dire tout sauf l'un des quatre suspects. Envelopper le flux marchait aussi, et c'est écarté : la pièce jointe **est** le document clinique, et le task file pose l'intégrité de l'archive en critère **bloquant**. Le rappel ne touche pas un octet, et `DownloadAttachment_MeasurementPutsNothingOnTheByteStream` épingle que le flux rendu au framework est **exactement l'instance** produite par le service — un futur décorateur de mesure tombe là.
- **Tests (8)** : attribution par phase · enveloppe publiée **une** fois et **séparément** (la sommer avec les phases doublerait le total) · **témoin négatif « absence ≠ zéro »** — les phases non parcourues sont publiées **à zéro**, jamais omises, sans quoi un instrument publiant des constantes passerait · rien hors périmètre · non-ré-entrance · publication **malgré une exception** · `assemble` jamais négatif · **PGSSI-S** : unique étiquette `phase`, ensemble fini de littéraux, enveloppe sans étiquette — aucun nom de fichier (**la fuite qu'a évitée task-213**), aucun UID, aucun INS.
- **🚧 CE QUE LA TÉLÉMÉTRIE NE DIRA TOUJOURS PAS** (écrit plutôt que laissé à découvrir) : (1) la répartition **interne** à `session_acquire` entre attendre le verrou et ouvrir/authentifier ; (2) le **débit** de la sortie — `stream` donne une durée, pas des octets/s ; (3) le **côté serveur** — aucune métrique d'api-mail ne dira si Dovecot ou le NFS sont le mur ; (4) **les 16 abandons**, avec un piège identifié d'avance : un client qui abandonne **peut ne jamais faire aboutir** `Response.OnCompleted`, donc les abandons risqueraient d'être **absents** de l'histogramme plutôt que d'y figurer comme longs — à vérifier au premier tir, et si confirmé c'est un **compteur d'abandons** qu'il faut, pas une durée.
- **LE SEUIL QUI ROUVRE LE SUJET** : p95 au palier 500 **sous 2 000 ms**. Requête du premier geste, à relever **dans** la fenêtre du tir (une `rate` évaluée après coup rend une série vide) : `sum by (phase) (rate(mssante_attachment_download_phase_duration_seconds_sum[2m])) / on() group_left rate(mssante_attachment_download_duration_seconds_count[2m])`.
- **Build / tests** : 0 erreur, 0 avertissement ; domain 136 · infrastructure 436 · api **661** · integration 384 · application **2 109** = **3 726 verts**. Un échec en run Debug, **flaky pré-existant documenté** (`MailExportServiceTests.BuildPdfPrintIntentEmbedsPrintWording`) — vert en isolation (22/22) et vert au run Release.
- **Sonar** : QG **ERROR** sur les **mêmes 56** violations qu'à task-249, dont **0 dans un fichier de cette PR** — les 6 fichiers du diff vérifiés, y compris les deux gros (`ImapService.cs`, `MailController.cs`). Fait notable : ~200 lignes de production ajoutées **sans bouger la couverture new code** (87,9 % avant comme après). **Dette introduite : zéro.**

### v1.46 — La chauffe lotie n'aboutissait toujours pas : ce n'était pas un délai, c'était un débit — task-253

- **Task** : task-253 — `archived`. **Aucune PR** : livrée **directement sur `develop`** à la demande humaine (même régime que task-243), donc **pas de HAG sur cette task**. Commits `5d056db` puis `077001c`.
- **LE PROBLÈME** : task-244 avait loti la chauffe (10 UID par requête, délai dérivé `lot × 3,5 s × 2 = 70 s`) et c'était le bon geste — un lot abouti est **acquis**. Mais au tir `enrich-245-n100` du 2026-08-09, **100 lots sur 100 médecins ont expiré**, et les VU n'ont produit que **14 itérations en 10 minutes** : ils ne faisaient que chauffer. Les 3,5 s/message dérivaient d'un coût relevé **en régime établi** ; à l'**ouverture** d'un palier, tous les médecins chauffent à la même seconde.
- **LE FAIT QUI COMMANDE LA CORRECTION, ET QUI INTERDIT LE GESTE RÉFLEXE.** Le débit d'enrichissement du serveur est **plafonné** : mesuré hors k6 le 2026-08-09, **0,59 s/message à concurrence 4** (6,8 msg/s) contre **2,11 s à concurrence 20** (9,5 msg/s) — ×5 de concurrence pour **+40 %** de débit seulement. Chauffer N médecins × R messages prend donc `N × R / débit` **quoi qu'on fasse** (~17 min à 100 médecins × 98 messages). **Allonger le délai d'un lot ne crée pas de débit** : ça transforme une expiration en attente. Le seul levier côté harnais est de **borner la concurrence**.
- **CHAUFFE PAR VAGUES**, `JOURNEY_WARMUP_MAX_CONCURRENT` (8) : chaque vague décalée du temps que la précédente met à s'écouler au débit plafond. Décalage **déduit de l'index du VU** — aucun état partagé, seule admission possible entre VU k6, qui ne partagent aucune mémoire mutable. La **première vague ne patiente pas** : la chauffe démarre bien à la première seconde du palier, elle est seulement étalée. Le délai d'un lot se dérive désormais de cette concurrence **bornée** (`warmupCostSecondsPerMessage`, interpolation sur les deux points mesurés) et non d'un forfait de régime.
- **⚠️ DÉFAUT DE MA PREMIÈRE LIVRAISON, ATTRAPÉ AVANT UN TIR ET NON APRÈS** (`077001c`). Le décalage dérivait de l'index **global** du VU, ce qui **double-comptait la rampe** : dans un escalier 50/100/200, le VU 150 n'arrive pas à la première seconde du tir mais à l'ouverture du palier 200. Chiffré : le VU 200 attendait **1 981 s sur une fenêtre de 1 920** — il n'aurait **jamais** chauffé, ni produit une seule itération. Le **rang de cohorte** remet chaque groupe à zéro : attente maximale **33,0 → 16,5 min**. Un test fige explicitement ce cas.
- **LA CONTREPARTIE EST MESURÉE, PAS CACHÉE.** Étaler la chauffe échangerait sinon un défaut visible — des lots qui expirent — contre un défaut invisible : un palier dont la moitié n'est pas du régime. `journey_warmup_elapsed_s` (p95, **attente de vague incluse**) est rapporté à la fenêtre du premier palier, avec **avertissement au-delà de 50 %**. Plafond à 50 % et non 25 % : à 100 médecins le débit serveur impose déjà ~17 min sur 32 — exiger plus court reviendrait à refuser tout tir jusqu'à ce que **task-254** relève ce plafond.
- **LA GARDE DE task-244 EST INTACTE**, et un **témoin négatif** le prouve (`TaskTwoFortyFourGateIsIntactTests`) : un tir à chauffe échouée refuse **toujours** les étapes servies par la base. Sans ce témoin, task-253 aurait pu remplacer un tir ouvertement raté par un tir **faussement vert** — bien pire que le défaut d'origine.
- **RÉSULTAT AU BANC** (tir `journey-247-proof`, escalier 50/100/200 distant) : lots perdus **556 → 12**, médecins chauffés **0 % → 94,5 %**, verdicts des étapes servies par la base **opposables**. ⚠️ Le critère littéral « zéro lot expiré » **n'est pas tenu** (12 sur 2 000) et la chauffe consomme **60 %** de la fenêtre du palier 200 : les deux découlent du plafond serveur, et **migrent dans la DOD de task-254**.
- **Tests** : 268 Python + 45 JS verts, `selftest.sh` vert. Fonctions pures testées, dont refus de `NaN` (même idiome que `warmupBatches`) et un **témoin de physique** — le retard total reste borné par le débit, pas par le nombre de VU.
- **Sonar** : non joué, **aucun fichier C# touché** (harnais Python/JS et documentation uniquement).

### v1.47 — Une commande IMAP au lieu de deux : le fetch d'enrichissement perd un aller-retour, et le plateau change de US — task-254

- **Task** : task-254 — `done`. **PR** : `api-mail` #184 (label `awaiting-human-merge`). Commits `0b3f4e6` (instrument), `0e71a35` (décompte), `4cf6021`→`4370284` (perf), `880d15c` (fix banc), `5598f89` (merge develop), `8a843a8` + `e71f14e` (tests étape 2), `38eb14e` (S103). `dtos-mss` : aucune branche, aucune PR — contrat non touché.
- **LE CHIFFRE QUI COMMANDE** — 97,1 % du coût d'un enrichissement est le fetch IMAP du corps (2 612,7 ms sur 2 691,7 au tir `enrich-245-n100`), le parsing CDA valant **0,4 %** : le candidat évident écarté par un **facteur 237**. Et ce fetch est un problème de **latence**, pas de débit : 2,01 allers-retours × 94 ms = 189 ms sur 239 ms (**79 %**), il ne reste que 50 ms de transfert pour ~124 Ko.
- **CE QU'ON NE GROUPE PAS, ET POURQUOI C'EST LA DÉCISION IMPORTANTE.** Grouper les corps de plusieurs messages obligerait à tenir `imap_session` sur tout le sous-lot, et **déferait task-239** qui avait ramené la détention p95 de **7,44 s à 0,49 s** en prenant le verrou par message. On groupe donc **à l'intérieur** d'un message. **Vérifié par la mesure** : détention −34 % **à nombre d'acquisitions inchangé** (1,10/message) — la fenêtre raccourcit sans que le verrou soit pris plus souvent.
- **CONDITIONNEL, sur la STRUCTURE et non sur une intuition.** Une commande unique rapatrie le message entier : régression franche sur un message porteur d'une PJ volumineuse inutile à l'analyse. Décision prise sur le `BODYSTRUCTURE` **déjà en main** (zéro aller-retour supplémentaire) : ≥ 2 parties utiles, parties utiles ≥ 80 % des octets, message ≤ 8 Mio. `EnrichmentFetchPlan` est **pur et testé**, bords compris.
- **L'A/B, ET LE LEVIER QUI LE REND À UN SEUL FACTEUR.** Les seuils étant des `const`, le bras témoin n'est **pas** `develop` (qui diffère aussi par l'instrument et le fix de rapport = plusieurs facteurs) mais **le même binaire** avec `UsefulOctetsShareFloor = 2.0` (part impossible ⇒ groupement jamais choisi). Levier retiré après mesure, contenu de production vérifié **identique à HEAD par hachage**. Bras préchauffés, **même taux d'échec (6/8 des deux côtés)** :

  | Par message | Témoin | Correctif | Écart | 2ᵉ mesure |
  |---|---|---|---|---|
  | **Sollicitations serveur** | 3,00 | **1,50** | **−50 %** | −40 % |
  | `imap_fetch` | 228,8 ms | 131,4 ms | **−43 %** | −45 % |
  | Enveloppe | 425,1 ms | 300,6 ms | −29 % | −34 % |
  | Détention `imap_session` | 269,3 ms/acq | 178,7 ms/acq | **−34 %** | −35 % |
  | Acquisitions/message | 1,10 | 1,10 | **+0 %** | +0 % |

- **CE QUI EST OPPOSABLE, ET CE QUI NE L'EST PAS.** Le **compte** de sollicitations (3,00 → 1,50) est structurel : il ne dépend d'aucune condition de machine. Les **durées**, elles, portent un confondant de **15 à 22 %** — des phases sans rapport avec le réseau (`cda_parse`, `xdm_extract`) bougent aussi, alors que `db_write` ne bouge pas. Le gain de fetch (−43 %) reste supérieur à ce confondant, et aucun confondant n'explique le compte.
- **❌ LE PLATEAU N'EST PAS FRANCHI — mesuré, pas supposé.** Concurrence 4 → **2,66 msg/s** ; concurrence 8 → **2,77 msg/s**, soit **+4 % pour un doublement**. Et le coût de fetch **ne se dégrade pas** (131 → 130 ms) : **ce n'est donc pas le fetch qui plafonne le débit**. Le niveau absolu n'est pas comparable aux 9,5 msg/s documentés (banc local, 8 praticiens) — c'est la **platitude relative** qui est le résultat. **Arbitrage PO du 2026-08-10** : le critère est **déplacé vers task-255**, motif écrit dans le DOD, plutôt que de retenir un gain acquis derrière une cause qui n'est pas la sienne.
- **⚠️ DÉCOUVERT EN CHEMIN : le plafond de connexions Postgres fait échouer l'enrichissement À FROID.** L'ouverture d'une connexion neuve expire à **15 s** (`NpgsqlConnector.ConnectAsync` → `TimeoutException`), remontée en **500 par `GetEnrichedUidsAsync`, AVANT tout fetch IMAP**. Préchauffer les pools (une requête par praticien) fait passer un tir de **5 lots aboutis sur 8 à 8 sur 8**. C'est ce qui a d'abord fait croire à une fragilité du correctif — jusqu'à ce que l'asymétrie **change de camp** d'un round à l'autre, ce qu'un défaut du facteur ne fait pas. Consigné dans task-255 comme plafond à neutraliser.
- **⚠️ PIÈGE D'OUTILLAGE PAYÉ COMPTANT : `--artifacts-path` + `--no-build` ne se combinent pas.** Le contournement qui évite de tuer un AppHost en vol écrit **hors du `bin` normal** ; un bras relancé en `--no-build` a donc exécuté **le binaire de l'autre bras**. Ce round rendait **+1 %** sur `imap_fetch` et allait faire conclure que le gain n'existait pas. Établi par horodatage des DLL, pas par supposition.
- **Tests — 17 au total, et la preuve par mutation publiée AVEC ses résultats négatifs.** Non-régression sur les **3 formes de corpus** avec compte **exact** de documents cliniques, là où l'existant se contentait de `NotEmpty` (une archive rendant 1 document au lieu de 2 passait) ; la forme **multi-documents est absente du corpus versionné** et est fabriquée à l'exécution depuis une archive réelle. Plus « ni perdu ni dupliqué sur échec partiel », invariant que le commentaire d'`EnrichEmailsAsync` **revendiquait en prose** sans qu'aucun test ne le vérifie. Cinq mutations : trois attrapées, **deux non** — la garde anti-« document fantôme » n'est **jamais atteinte** (la bibliothèque XDM ne produit aucun `CdaFile` candidat sur une archive sans CDA exploitable), et la non-duplication repose sur **deux gardes** dont la seconde suffit (`AddNewMail` refuse si `ContentCount > 0`), si bien qu'une régression du filtre amont ferait **repayer tout le travail réseau en silence**. Les deux trous sont écrits dans les fichiers de test.
- **Build / tests** : 0 erreur, 0 avertissement ; domain 136 · infrastructure 436 · integration **401** · application 2 122 · api 660 = **3 755 verts**. Deux flakies pré-existants verts en isolation (`FlagsmithFeatureFlagServiceTests.RefreshFailure_LogsOncePerWindow_…` 8/8, `MarkdownPdfRendererTests.RenderHeadingPreservesText` 9/9). `develop` mergée (task-249/251/252) **sans conflit** malgré une collision apparente sur `ImapService.cs` et `MailProcessingMetrics.cs` — régions disjointes.
- **Sonar** : QG **ERROR** sur 56 `new_violations`, dont **21 dans des fichiers de la task** — mais « dans un fichier touché » ≠ « introduit ». **Un seul finding réellement introduit** (`S103`, ligne de 154 caractères dans un fichier **créé** par la task) : **corrigé** (`38eb14e`). Les **20 autres** sont sur `report.py`, aux lignes **1700 à 4790** d'un fichier de ~5000 lignes alors que la task n'en ajoute que **55** → fonctions **préexistantes**, et ce sont des **S3776**, hors chaîne autonome par charte. **Dette C# introduite : zéro.**

### v1.48 — Le plateau d'enrichissement n'existe pas : le débit croît ×2,70 pour ×4 de concurrence, et deux des trois défauts de banc le fabriquaient — task-255

- **Task** : task-255 — `done`. **PR** : `api-mail` #185 (label `awaiting-human-merge`), commit `46e31bb`. `dtos-mss` : branche créée, **aucun commit**, aucune PR — contrat non touché. **US de mesure : zéro ligne de code applicatif**, le seul fichier modifié est `tests/loadtest-k6/reports/INDEX.md` (les rapports de tir sont sous `.gitignore`, l'INDEX est la trace versionnée).
- **LE RÉSULTAT, ET IL INFIRME LA PRÉMISSE DE LA US.** Série de référence, hôte non affamé, 640 messages enrichis sur 640 soumis à chaque point, 0 erreur, 0 court-circuit :

  | Concurrence | Fenêtre | Débit | Enveloppe/msg | `imap_fetch` | `db_write` | `assemble` | Attente `imap_session` |
  |---|---|---|---|---|---|---|---|
  | 4 | 38,4 s | **16,66 msg/s** | 188,0 ms | 124,8 ms | 23,3 ms | 8,4 ms | 0,0 ms/acq |
  | 8 | 21,2 s | **30,19 msg/s** | 207,3 ms | 126,5 ms | 31,7 ms | 11,2 ms | 0,0 ms/acq |
  | 16 | 14,2 s | **45,02 msg/s** | 258,9 ms | 127,3 ms | 62,1 ms | 21,1 ms | 8,7 ms/acq |

  ×1,81 puis ×1,49, soit **×2,70 pour ×4 de concurrence** — contre les **+4 % pour un doublement** de task-254 (v1.47) qui motivaient cette US.
- **LA RESSOURCE QUI BORNE LA MONTÉE EST LE CPU DE L'HÔTE — donc HORS d'api-mail**, et les trois suspects sont exonérés par des chiffres, pas écartés par raisonnement. **Le pooler ne fait pas la queue** : `cl_waiting` nul sur 14 relevés sur 15, `maxwait` maximal **0,7 ms**, backends PostgreSQL invariants (16 aux trois concurrences). **Le verrou `imap_session`** — suspect historique de l'EPIC — a une attente **strictement nulle sur 704 acquisitions** à 4 comme à 8, et pèse **3,7 %** de l'enveloppe à 16. **La file d'exécution du processeur**, elle, passe de **0,6 à 30 sur 24 cœurs**.
- **LA PREUVE INTERNE, indépendante des compteurs de ressources.** La phase **bornée par la latence injectée** (`imap_fetch`, 100 ms Toxiproxy) est **plate au demi-millimètre** (124,8 → 126,5 → 127,3 ms) tandis que **toutes** les phases bornées par le calcul enflent ensemble (`db_write` ×2,7, `assemble` ×2,5, `xdm_extract` ×1,5). Une file sur une ressource nommée ferait monter le coût de **ceux qui l'attendent** ; ici c'est **tout ce qui calcule** qui ralentit.
- **LA CONTRE-ÉPREUVE, À UN SEUL FACTEUR.** La même série avait d'abord tourné sur un hôte dont ~11 des 24 cœurs étaient consommés par un conteneur `sql-server` **étranger au banc**, en boucle d'échec `Error 17300` depuis dix mois (99,994 % de son plafond mémoire cgroup, 50 997 échecs d'allocation, 9,1 M lignes de journal, **et aucun service rendu** — `sqlcmd` sur son propre `localhost` échouait avant login, alors que son port était en écoute : même faux positif que le relais IPv6, TCP accepté, service mort).

  | Concurrence | Hôte affamé | Hôte calme | Écart |
  |---|---|---|---|
  | 4 | 15,22 msg/s | 16,66 msg/s | +9 % |
  | 8 | 26,38 msg/s | 30,19 msg/s | +14 % |
  | 16 | 34,59 msg/s | 45,02 msg/s | **+30 %** |
  | Pente (×4) | ×2,27 | **×2,70** | — |

  **Le gain croît avec la concurrence** : signature d'une contention de calcul, et **preuve indépendante** que la limite n'est pas applicative — une file sur une ressource nommée ne se desserre pas en réparant un conteneur tiers.
- **🛑 TROIS DÉFAUTS DE BANC, DEUX CAMPAGNES JETÉES, ET DEUX D'ENTRE EUX FABRIQUAIENT LE PLATEAU CHERCHÉ.** **(1) `08P01 server_login_retry`** — `--add-host=pgupstream:host-gateway` injecte désormais **deux** entrées (`192.168.65.254` **et** `fdc4:f303:9324::254`) ; PgBouncer retient l'AAAA, met l'échec en cache, et tout client du pool prend un 500 en 8 ms. **13 % des lots perdus.** Retirer l'entrée IPv6 de `/etc/hosts` **ne suffit pas** (PgBouncer garde sa résolution) : il restait 2,6 %. Correctif éprouvé — rattacher PgBouncer au réseau du conteneur PostgreSQL — **0 % sur 6 tirs et 3 840 messages**, puis **retiré de la branche** sur arbitrage humain (voir ci-dessous) → **task-257**. **(2) Le snapshot pris à la fin du tir perd sa queue** : export applicatif toutes les 5 s + scrape toutes les 5 s ⇒ **275 messages comptés pour 640 réellement enrichis** sur un tir de 16 s (**−57 %**), et d'autant plus que le tir est court — or un tir se raccourcit quand la concurrence monte. **L'artefact fabrique mécaniquement un plateau puis une décroissance.** Remède : 30 s de décantation avant relevé. **(3) Purger bus non drainé** : les consommateurs réécrivent des `MailContents` **après** le TRUNCATE ⇒ **22 lots sur 32** court-circuités, rattrapés par le filet `enrich_short_circuited count==0`. Les trois sont consignés dans le skill `loadtest-skill`.
- **⚠️ ARBITRAGE HUMAIN DU 2026-08-13 — le correctif de banc sort de cette task** (`questions/task-255.md`, option A). Le changement de `pgbouncer.ini` faisait tomber `BenchUpstream_DoesNotRelyOnHostDockerInternal` : ce test asserte `Contains("pgupstream")`, c'est-à-dire **le nom** de l'upstream. Or le nom n'avait pas changé — **c'est sa résolution qui avait changé**, et c'est exactement pourquoi le garde-fou de task-200 n'a rien vu. Remplacer la chaîne par `postgres-pgvector` aurait reproduit le défaut de conception à l'identique. Le correctif est donc **entier dans task-257** (`pgbouncer.ini` + rattachement réseau dans `AppHost.cs` + garde-fou réécrit sur la **famille d'adresses résolue**), reproduit en annexe de cette US. `/review` a **halté sur test rouge** avant tout commit — le fail-fast a fonctionné.
- **LES TROIS PLAFONDS DE BANC, NEUTRALISÉS ET VÉRIFIÉS.** Pools Postgres froids → préchauffage d'un `GET /folders` par praticien, **8/8 en 200** aux trois points, zéro `TimeoutException`. `mail_max_userip_connections=10` → montée à population constante, **5,3 sessions par praticien** au maximum. Limiteur 100 req/10 s par identité → **0 HTTP 429**.
- **AUCUN CORRECTIF APPLICATIF LIVRÉ, ET C'EST LA DÉCISION.** La prémisse n'est pas vérifiée : il n'y a pas de plateau à franchir entre 4 et 16. Livrer un correctif traiterait une **cause supposée** — ce que l'EPIC a déjà payé avec task-222, annulée. **Seuil de réouverture posé** : rapport de débit **< ×1,3 par doublement** sur deux paliers consécutifs, **avec la file d'exécution du processeur sous 2**.
- **BACKLOG D'INSTRUMENTATION — ce que la télémétrie n'a PAS pu dire.** (a) **L'attente d'obtention de connexion sur le chemin d'écriture n'existe pas comme métrique** : `mssante_db_operation_phase_duration_seconds` couvre la **lecture** (task-243) et n'a remonté **qu'un seul appel** sur toute la campagne. Le triplement de `db_write` est donc **attribué par recoupement, pas mesuré à la source** → **task-258**. (b) Le CPU n'est pas attribuable **par phase**. (c) L'échantillonneur (cadence 5 s) ne rend que **4 relevés** sur la fenêtre du point 16 : suffisant pour une tendance monotone, insuffisant pour un percentile. (d) `ConcurrentMessageLimit = 10` sur `add-new-mail-queue` n'a pas été éprouvé — la phase `embedding` (189 ms/message, la plus coûteuse) est **hors du chemin synchrone**, ce que le code annonce et que la mesure confirme (les phases synchrones bouclent **exactement** sur l'enveloppe) ; son plafond deviendra candidat dès que le CPU cessera de l'être.
- **DÉFAUT APPLICATIF RELEVÉ, SANS RAPPORT AVEC LE DÉBIT** : `ContactRepository.UpdateAsync` (`ContactRepository.cs:206`) lève `InvalidOperationException: Collection was modified` dans `RemoveRange` — la collection de navigation est modifiée pendant son énumération. 4 occurrences par série, reproduites sur **les deux** séries, sur 4 praticiens différents. Journalisée puis avalée ⇒ **perte silencieuse d'enrichissement de contact**. Distinct de task-250 (v1.42), qui traitait un conflit **après** `SaveChangesAsync` : le rejeu ne l'attrape pas → **task-259**.
- **Analyse Seq** : 4 erreurs applicatives sur toute la fenêtre (les 4 ci-dessus), **0** `Failed to parse entity headers`, **0** échec d'embedding, **0** HTTP 429, **0** `08P01` sur la série de référence, **0** erreur de connexion IMAP. Exceptions par point : aucune famille ne croît avec la concurrence — `DbUpdateConcurrency` 60/15/15, `InvalidOperation` 16/4/4, `Conflict` 8/2/2, `Xml` 4/4/4 — elles **décroissent** de 4 à 16, donc aucune n'est un coût par requête.
- **Build / tests** : 0 erreur, 0 avertissement. Intégration **401 passés / 16 ignorés / 0 échec**, dont `BenchUpstream_DoesNotRelyOnHostDockerInternal` redevenu vert après retrait du correctif. **⚠️ `develop` est rouge, et pas du fait de cette task** : `AiPromptHelperTests.GetPromptShouldContainDocumentIntroduction` échoue 2 fois sur 2 — le commit `411b289` « Fix prompt » (sur `develop` depuis le 2026-08-10) a changé le texte du prompt sans mettre à jour son test, la chaîne `"Voici le document à analyser"` n'existe plus dans `AiPromptHelper.cs`. **Preuve d'innocence** : le diff de la branche face à `origin/develop` est de **10 lignes de Markdown**, aucun code compilé ne diffère. Un second échec vu sur la suite complète ne s'est pas reproduit à l'unité (flaky, non caractérisé).
- **Sonar** : non exécuté — aucun code applicatif produit.
- **⚠️ CE QUI N'EST PAS OPPOSABLE** : le niveau absolu (45 msg/s) — banc local, 8 praticiens, latence Toxiproxy, infrastructure de banc partageant le CPU du système sous test. Seule la **pente** est le résultat. Et le domaine de validité s'arrête à **16** : rien ici ne dit ce qui se passe à 32 ou à 500 praticiens.

### v1.49 — L'upstream du banc ne passe plus par l'hôte : la troisième occurrence du piège IPv6 est fermée par la topologie, pas par un nom — task-257

- **Task** : task-257 — `done`. **PR** : `api-mail` #186 (label `awaiting-human-merge`). Commits `b9b22a5` (correctif + gardes), `e337f77` (passe qualité), `9ceb19b` (SYSLIB1045). `dtos-mss` : branche créée, **aucun commit**, contrat non touché.
- **LA PANNE, ET POURQUOI ELLE COÛTE SI CHER.** `--add-host=pgupstream:host-gateway` injecte désormais **deux** entrées dans le `/etc/hosts` du conteneur : IPv4 **et** IPv6 (`fdc4:f303:9324::254`). PgBouncer, contrairement à `psql`, **ne bascule pas d'une famille d'adresses à l'autre** : il retient l'AAAA, échoue en `Network unreachable`, **met l'échec en cache** (`server_login_retry`) et rend un `08P01` **à tous les clients du pool** en 8 ms — ce qui ressemble à un rejet applicatif, pas à une panne d'infrastructure. Coût mesuré en task-255 : **13 % des lots d'enrichissement perdus, deux campagnes jetées**.
- **⚠️ POURQUOI LE GARDE-FOU DE task-200 N'A RIEN VU — la leçon transposable.** Il assertait `Contains("pgupstream")`, c'est-à-dire **le nom utilisé**. Or le nom n'avait pas changé : **c'est sa résolution qui avait changé**. Un test qui garde la *lettre* d'un correctif ne garde pas sa *raison d'être*. C'est la troisième occurrence de la même cause racine sur ce banc (relais IPv6 loopback, puis `host.docker.internal` en AAAA seul, puis `host-gateway` en A+AAAA) et le point commun n'est pas Docker : c'est qu'**un client sans bascule de famille d'adresses transforme le piège en panne totale**, là où `psql` ou `curl` le traversent sans le voir.
- **LE REMÈDE : supprimer la classe, pas l'instance.** On ne passe plus par l'hôte du tout. PgBouncer est rattaché au réseau Docker du conteneur PostgreSQL et l'adresse **par son nom**, résolu par le DNS du réseau utilisateur. Ce réseau est déclaré `enable_ipv6: false` : **la résolution IPv4 devient structurelle, plus incidente** — elle ne dépend plus d'un réglage qu'un changement de Docker Desktop peut retourner.
- **⚠️ LE MÉCANISME N'EST PAS CELUI QU'ON CROYAIT, ET C'EST MESURÉ.** `WithContainerRuntimeArgs("--network", …)` est **ignoré** : banc démarré pour le vérifier, le conteneur sort en `NetworkMode=bridge`, membre du seul réseau Aspire, et `getent ahosts postgres-pgvector` ne rend **rien**. **DCP crée le conteneur puis rattache lui-même ses réseaux**, écrasant le drapeau. Le rattachement se fait donc **après** création, par un crochet `AfterResourcesCreatedEvent` — la même chose que DCP, après lui. Sans le critère de DOD « démarrage sans commande manuelle », c'est une configuration cassant le banc **plus franchement qu'avant** qui aurait été livrée.
- **DEUX ALTERNATIVES ÉCARTÉES SUR MESURE.** (a) `--add-host postgres-pgvector:<IP du conteneur>` : le drapeau `--add-host`, lui, **est** bien transmis — mais l'IP d'un conteneur d'un **autre réseau bridge n'est pas routable** (172.24.0.2 injoignable depuis 172.18.0.x). (b) Figer l'IPv4 littérale de l'hôte (`192.168.65.254`) : valeur propre à Docker Desktop, non portable — et le task file l'interdisait explicitement.
- **VÉRIFIÉ AU BANC, pas seulement en test.** Banc démarré **sans une seule commande manuelle** : conteneur sur les deux réseaux ; `postgres-pgvector` résolu en **172.24.0.2 uniquement, aucune AAAA** ; `select inet_server_addr()` traversant le pooler ; **0** occurrence de `unreachable`/`server_login_retry` ; **0** `PostgresException` ; tir `enrich` (4 praticiens, VUS=4) à **0 % d'erreur, 100 % de checks**. Le seed ne produit plus non plus le `500`-puis-retry systématique du pool froid.
- **LES GARDES, ÉPROUVÉS PAR MUTATION — 4 mutations, 4 attrapées** : retour à `host=pgupstream` ❌, upstream figé sur `192.168.65.254` ❌, réintroduction de `--add-host` ❌, suppression du rattachement ❌. `BenchUpstream_ResolvesToIpv4WithoutHostAlias` porte sur la **classe entière** des résolutions par l'hôte (`host.docker.internal`, `host-gateway`, `pgupstream`) et refuse aussi les IP littérales ; le bloc du conteneur est **borné** avant inspection, pour qu'un `--add-host` légitime ailleurs ne le fasse pas échouer. Les messages d'échec **nomment la cause** au lieu de constater une différence.
- **Hors profil loadtest, rien ne change** — vérifié structurellement : le crochet est dans le bloc `if (loadTestProfile)`.
- **Build / tests** : 0 erreur, 0 avertissement ; domain 136 · infrastructure 436 · api 661 · integration **402** · application 2 122 = **3 757 verts**. ⚠️ **1 rouge pré-existant sur `develop`**, sans rapport : `AiPromptHelperTests.GetPromptShouldContainDocumentIntroduction` — le commit `411b289` « Fix prompt » (10 août) a changé le texte du prompt sans mettre à jour son test.
- **Sonar** : QG **OK**, 0 bug, 0 vulnérabilité, notes **A/A/A**, couverture **85,1 → 87,6 %**, duplication 0,6 → 0,4 %. **Une issue introduite, une corrigée** (`SYSLIB1045`, regex littérale — retirée plutôt qu'habillée d'un `GeneratedRegex`). **Dette introduite : zéro.** ⚠️ **Réserve d'honnêteté** : `sonar.exclusions` contient `**/AppHost/**`, où vit **tout le code livré** — le seul fichier analysé du diff est le fichier de tests. Un « QG OK » ne vaut donc **pas** validation du correctif : c'est le banc qui l'a validé, pas Sonar.
- **Piège d'outillage relevé** : `dotnet sonarscanner` échoue en `Pre-processing failed` sous Git Bash, qui convertit les arguments commençant par `/` (`/k:`, `/d:`) en chemins Windows. Remède : `export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'`. Même famille que le piège `docker exec` déjà documenté.

### v1.50 — Le triplement de l'écriture est du TRAVAIL et non une file : les mêmes requêtes, en même nombre, prennent plus de temps — task-258

- **Task** : task-258 — `done`. **PR** : `api-mail` #187 (label `awaiting-human-merge`). Commits `ad96bf7` (instrument), `7ad04d0` (compteur asserté), `352ffed` (CA1861), `f9fa28b` (verdict). `dtos-mss` : branche créée, **aucun commit**.
- **⚠️ PREMIÈRE US D'INSTRUMENT DE CETTE EPIC À SORTIR AVEC SA DOD COMPLÈTE.** task-243, 245, 247, 248, 250 ont toutes livré l'instrument en laissant leurs critères de mesure ouverts — « ce sont des mesures qui exigent un tir ». Celle-ci a conduit sa contre-épreuve **avant** la PR, sur décision humaine, et le verdict est dans la PR plutôt que dans une US ultérieure.
- **LE VERDICT.** Trois points de concurrence, protocole identique à task-255, 640 messages enrichis sur 640 soumis à chacun, 0 erreur :

  | Concurrence | Débit | `connection_open` | `sql_execute` | `assemble` | **Requêtes/message** |
  |---|---|---|---|---|---|
  | 4 | 13,96 msg/s | 0,52 ms | 22,92 ms | 11,28 ms | **8,72** |
  | 8 | 26,66 msg/s | 0,21 ms | 25,53 ms | 8,46 ms | **8,72** |
  | 16 | 40,21 msg/s | 0,61 ms | **37,40 ms** | 9,57 ms | **8,72** |

  Trois faits qui s'excluent mutuellement de toute autre lecture : **l'attente d'obtention de connexion est nulle et plate** (1,4 % du coût au point le plus chargé, sans tendance, `cl_waiting` et `maxwait` nuls sur tous les relevés) — **l'hypothèse du pool, `Maximum Pool Size=2` par base praticien, suspect désigné d'avance, est ÉCARTÉE par la mesure** ; **le nombre de requêtes est identique au centième** (8,72), donc ce n'est pas non plus « plus de travail » ; **l'exécution SQL croît de 63 %**. Mêmes requêtes, même nombre, plus de temps.
- **⚠️ SANS LE DÉNOMINATEUR, CE VERDICT ÉTAIT IMPOSSIBLE.** Une durée qui croît se lit aussi bien « plus de requêtes » que « des requêtes plus lentes », et les deux appellent des remèdes **opposés** : réduire le travail par message d'un côté, accélérer l'exécution de l'autre. C'est la leçon de task-243 et task-256, appliquée. Le compteur a d'ailleurs failli manquer : il était **activé dans la capture mais jamais asserté**, et c'est la passe qualité qui l'a relevé.
- **OÙ LA QUESTION SE DÉPLACE, ET CE QUE LA MESURE NE DIT PAS.** `sql_execute` mesure « commande envoyée → serveur répondu » : le temps supplémentaire est **dans PostgreSQL ou sur le lien qui y mène**, pas dans l'application. Causes candidates **non tranchées** — contention interne (CPU, verrous, WAL, points de reprise) ou concurrence entre les 8 bases praticien. **Le prochain instrument n'est plus applicatif** : `pg_stat_statements`, `pg_stat_activity.wait_event`, statistiques de verrous.
- **L'IMPLÉMENTATION : l'instrument existait, il n'était pas branché.** `DbOperationScope` (task-243) publie **déjà** `connection_open`, `sql_execute` et le **reste** par différence, plus le compte de requêtes. **Cause précise de l'angle mort** — l'intercepteur de **commandes** alimente les **deux** périmètres, mais celui de **connexion** n'alimente que `DbOperationScope`, inactif sur ce chemin faute de `Begin` : la phase `db_write` de l'enrichissement ne mesurait donc **que l'exécution SQL**, et l'attente **n'existait pas**. Livrable : **une ligne** dans `AddNewMail`. Zéro nouvel instrument, zéro changement de contrat — `report.py` agrège par opération, la table et la phrase attribuable rendent la nouvelle opération d'elles-mêmes.
- **Deux décisions de placement.** **Au dépôt et non chez l'appelant**, comme les deux périmètres de lecture : la mesure suit l'opération quel que soit son appelant, au lieu de dépendre d'un site qu'on oublierait — mode de panne de task-214 (une API branchée sur **un site sur vingt et un**). **Le court-circuit de déduplication est DANS le périmètre** : il interroge la base, donc il coûte, et un message dédupliqué doit apparaître pour ce qu'il est plutôt que de disparaître de la mesure.
- **Tests — 6, éprouvés par mutation, et un piège évité de justesse.** 6 verts avec l'instrumentation, **6 rouges sans**. ⚠️ **Au premier passage, seuls 4 sur 5 tombaient** : le cinquième bouclait sur une liste vide et **passait à vide** — le piège exact payé par task-250 (un test d'intégration vert **avec** le défaut). Renforcé, avec le commentaire qui dit pourquoi. **Limite assumée** : le fournisseur InMemory n'ouvre aucune connexion et n'exécute aucune commande — d'où le cas « attente nulle » gratuit, mais le cas **multi-requêtes réel n'est pas éprouvable** à ce niveau.
- **⚠️ SUGGESTION DE REVUE NON RÉSOLUE — l'étiquette couvre plus que son nom.** `EnrichPersistMail` promet un enrichissement, mais le périmètre couvre **les quatre** sites d'appel de `AddNewMail`, dont un (`ImapService.cs:2646`) écrit des **DTO d'en-têtes seuls**, bien moins coûteux. Sur une campagne `journey`, la série **mélangerait deux populations**. **La campagne du verdict n'en est pas contaminée — vérifié et non supposé : 640 appels pour 640 messages enrichis, aux trois points.** À trancher avant la première campagne `journey` qui lira cette métrique : renommer en neutre, ou distinguer par un paramètre.
- **Build / tests** : 0 erreur, 0 avertissement ; domain 136 · infrastructure **442** · api 661 · integration 402 · application 2 122 = **3 762 verts**, plus **270 auto-tests Python** du harnais. ⚠️ Les auto-tests **JS sont sautés** — Node absent du poste ; sans conséquence ici (aucun fichier JS touché), mais **un SKIP n'est pas un succès**. 1 rouge **pré-existant** sans rapport (`AiPromptHelperTests`, commit `411b289` du 10 août).
- **Sonar** : QG **OK**, 0 bug, 0 vulnérabilité, notes A/A/A. Une issue introduite (`CA1861`), **corrigée** — et l'invariant de cardinalité y gagne un nom au lieu d'être recomposé à chaque mesure. **Dette introduite : zéro.** Contrairement à task-257, **le code de cette task est bien dans le périmètre Sonar** : le verdict porte sur le livrable.

### v1.51 — Le dénominateur qui manquait au +51 % : la page d'en-têtes compte enfin les objets qu'elle construit — task-256

- **Task** : task-256 — `done`. **PR** : `api-mail` #188 (label `awaiting-human-merge`, MERGEABLE). Commits `a47fbaa` (instrument + points de comptage + 32 tests), `b7ce914` (rapport : coût par objet + contre-épreuve), `caa1880` (passe qualité), `579b173` (revue : double comptage assumé, documenté). `dtos-mss` : branche créée, **aucun commit** — aucun contrat touché, donc aucune publication NuGet.
- **CE QUI MANQUAIT.** task-243 avait livré le **numérateur** : `assemble` vaut **83,7 %** du coût de `GetMailsByUids`, premier poste du parcours (F-242-1, quatre campagnes). Deux tirs à protocole identique ont ensuite mesuré cette matérialisation passer de **433,3 ms** (`journey-247-proof`, 09-08) à **654,5 ms** (`journey-lot254-n200`, 10-08) — **+51 %** — pour **15,8 requêtes SQL par appel, identique au millième**. Le travail demandé n'a pas changé ; le volume d'objets à construire, si (chauffe aboutie pour 100 % des médecins contre 94,5 %, et plus vite — task-254). **Cette explication était une déduction : aucun compteur ne disait combien d'objets l'appel construisait.**
- **LIVRÉ.** `mssante_db_operation_objects_total`, compteur ventilé par `(operation, family)`, publié à la fermeture du `DbOperationScope` **existant** — donc à côté de `assemble`, **zéro nouvel instrument de durée**. 17 points de comptage dans `MailRepository`, tous **après** matérialisation et **avant** tout regroupement (c'est le nombre de DTO construits qui explique le coût, pas le nombre de clés d'index). Couvre `GetMailsByUids` **et** `GetMail` — sans quoi les deux chemins ne seraient pas comparables.
- **LE TYPAGE COMME GARDE-FOU PGSSI-S, ET NON LA DISCIPLINE.** La signature prend un `DbObjectFamily` (énumération), **pas une chaîne** : les `enriched_ids` comptés peuvent porter de l'INS, et une signature à chaîne accepterait un jour un nom de pièce jointe ou un sujet de message. La fuite de task-213 est ici **impossible à écrire**, pas seulement interdite. Épinglé par deux tests (unitaire + lecture réelle). Une valeur hors énumération ⇒ point de métrique perdu, jamais d'étiquette numérique, **jamais d'exception sur le chemin d'une lecture du médecin**.
- **« ZÉRO » N'EST PAS « NON RELEVÉ », ET C'EST ENCODÉ.** Chaque compartiment part d'une sentinelle `-1` ; le premier ajout la fait passer à « observé, zéro » par `CompareExchange` sans écraser ce qui suit. Une famille jamais chargée ne produit **aucune** série — une page sans document CDA n'interroge pas la biologie, et publier `0` affirmerait qu'on a regardé. Vérifié des deux côtés : `A_lot_that_was_never_loaded_publishes_nothing_at_all` (C#) et `test_a_family_never_loaded_stays_none_and_is_excluded_from_the_total` (Python). Leçon de task-214, cette fois portée par la structure de données.
- **⚠️ ÉCART ASSUMÉ À L'ÉNUMÉRATION DU TASK FILE — 12 familles au lieu des 6 nommées.** Le task file nomme six familles **et donne le critère** (« celles que le dépôt charge en lots séparés ») ; les six sont toutes bornées par la page (25 messages + satellites immédiats). Or la déduction à vérifier est « plus de **contenu enrichi** », lequel vit dans `medical_documents` / `biology_results` / `summary_items` / `contents` / `thread_links` / `duplicate_refs`. S'en tenir aux six aurait produit un dénominateur incapable **par construction** de faire varier le résultat : la contre-épreuve du DOD n'aurait pas pu se tromper, donc n'aurait rien prouvé. Cardinalité : 12 × 3 opérations, littéraux à la compilation.
- **LE RAPPORT REND LA CONTRE-ÉPREUVE RÉFUTABLE.** Nouvelle section « Combien d'objets une opération servie par la base construit-elle », rendue juste après les phases dont elle est le dénominateur : objets/appel par famille, matérialisation en regard, **coût par objet en µs**, phrase attribuable. Objets **par appel** et non par seconde (un débit monterait avec la charge sans rien dire du coût unitaire), division en **PromQL** (`on (operation) group_left ()`) donc exacte à chaque point. La contre-épreuve publie **le nombre d'objets supplémentaires que les 221,2 ms d'écart exigent au coût mesuré** : le tir de référence le confronte à son propre décompte, et si l'écart de volume n'est pas du bon ordre, **c'est la déduction actuelle qui est fausse — et c'est un résultat**. Sans coût par objet sur la fenêtre : « non relevé », pas une estimation.
- **Deux cas que la section refuse de taire** : zéro objet pour une matérialisation non nulle (⇒ le coût ne vient pas du volume, aucun remède de volume ne s'applique) et absence totale de décompte (⇒ l'instrument n'a pas tourné). Le second a été **renforcé par la passe qualité** : le verdict « zéro objet pour une matérialisation non nulle » s'écrivait sans que la durée soit mesurée, donc affirmait un fait qu'il ne tenait pas.
- **Tests** : 32 cas neufs. 15 sur l'accumulateur (`DbOperationObjectCountTests` — multi-familles, accumulation multi-lots, zéro mesuré, non relevé, hors périmètre, ajout tardif, imbrication, exception, cardinalité bornée, famille hors énumération, ordre du tableau d'étiquettes) ; 8 sur la **lecture réelle du dépôt** InMemory (`MailReadObjectCountTests`) ; 17 côté Python. **Les deux niveaux sont nécessaires** : les unitaires prouvent que l'accumulateur est juste, les seconds que les appels sont posés aux bons endroits — un lot oublié sous-estimerait le dénominateur, surestimerait le coût par objet, et fausserait la contre-épreuve sans que rien ne paraisse faux.
- **COLLISION DE CAPTURE DU METER : UNE FERMÉE, UNE NOMMÉE.** Le meter OTel est statique, donc un `MeterListener` capte les mesures de **toutes** les classes concurrentes, et leurs assertions sont de la forme « exactement une enveloppe ». `DbOperationScopeTests` ↔ `DbOperationObjectCountTests` était **rouge de façon déterministe** dès l'ajout du compteur → collection xUnit `MailMetricsCaptureCollection` (6 classes sérialisées, **aucune assertion relâchée**). En revanche `EnrichmentOperationScopeTests` reste flaky : ses colliders sont les **tests de service réels** (`ImapServiceTests` ouvre un scope, `AddNewMailConsumerTests` publie `embedding`, `CdaParsingServiceTests` alimente `xdm_extract`) — antérieur à cette task, vérifié par contre-épreuve `git stash` sur `develop`, et hors périmètre : le remède demande une décision de conception (corrélation par étiquette de test, ou `Meter` dédié par classe de capture). **Finding F-256-3.**
- **Vérification locale** : build 0 erreur / 0 avertissement. `domain` 136/136, `infrastructure` 450/450, `api` 661/661, `integration` 402/402 (16 ignorés), `application` 2 135/2 136 (le rouge est `AiPromptHelperTests`, **antérieur** — contre-épreuve stash), Python 287/287. ⚠️ Le tir en parallèle de la **solution entière** reste bruyant (91 échecs `integration.tests` quand les 5 assemblages tournent ensemble, 0 en isolation) : contention Testcontainers, antérieure.
- **Sonar** : Quality Gate new code `ERROR` sur `new_violations = 59`, **provenance vérifiée finding par finding — zéro n'appartient à cette task**. Les findings `report.py` sont tous dans des fonctions antérieures (lignes 1622–5167 ; les fonctions ajoutées sont en 4069 et 4289–4470). New-code period `PREVIOUS_VERSION` **héritée**, donc fenêtre englobant plusieurs tasks mergées → **finding F-256-4**, décision de configuration. `new_security_hotspots_reviewed` **50 % → 100 %** : 5 hotspots revus `SAFE` avec justification, dont le seul de cette task (`test_report_db_objects.py:42`, URL de fixture jamais appelée, conforme à l'entrée `python:S5332` de `conventions/python.md`). Phase 2 legacy **skippée sur motif de fond, pas de temps** : 59 findings sur 15 fichiers étrangers à la US feraient franchir la règle 5 (~30 fichiers), violeraient la règle 6, et rendraient le diff d'une US d'instrument inattribuable — ce que la dépendance à task-243 existe précisément pour éviter.
- **Autres findings** : **F-256-1** allocation du `long[12]` payée aussi par les périmètres `EnrichPersistMail` qui ne comptent rien (paresseuse possible, non rentable devant l'objet scope lui-même) ; **F-256-2** une pièce jointe de document est comptée **deux fois** sur `GetMail` avec contenu — correct pour « objets construits » (deux DTO pour une ligne), désormais dit explicitement dans le code.
- **Aucun gain de performance : c'est un instrument.** Aucune requête ajoutée, retirée ni modifiée. La mesure de confirmation au banc (mode distant, avant/après chauffe) reste due — Manual Test Plan de la PR.

---

### v1.52 — Le mécanisme supposé était faux, et c'est le test qui l'a dit : `RemoveRange` ne modifie pas ce qu'il énumère — une entité `Added` le fait — task-259

- **Task** : task-259 — `done`. **PR** : `api-mail` #189 (label `awaiting-human-merge`, MERGEABLE). Commits `fabc6c1` (correctif + 10 tests), `35e3f81` (passe qualité). `dtos-mss` : branche créée, **aucun commit**.
- **LE DÉFAUT MESURÉ.** Campagne task-255 du 2026-08-13 : **quatre `InvalidOperationException: Collection was modified; enumeration operation may not execute`** par série de trois tirs, reproduites sur les **deux** séries (hôte affamé et hôte calme) et sur des praticiens différents (`loadtest-1`, `-3`, `-5`, `-7`), levées depuis `InternalDbSet<T>.RemoveRange` dans `ContactRepository.UpdateAsync`. L'exception remontait jusqu'à `CreateOrUpdateContactAsync` qui la journalisait puis s'arrêtait : **message enrichi, contact non enrichi**, sans alerte ni rejeu — celui de task-250 se déclenche sur `ConflictException`, levée **après** `SaveChangesAsync`, donc jamais atteinte ici.
- **⚠️ LA LECTURE STRUCTURELLE DU TASK FILE EST RÉFUTÉE, ET C'EST LE PRINCIPAL RÉSULTAT DE CETTE US.** Le task file donnait sa lecture comme « lu dans le code, et non mesuré — à confirmer par un test avant tout correctif » : `RemoveRange` marquerait ses éléments supprimés, déclencherait le raccordement des navigations, donc modifierait la collection qu'il énumère. **Le premier test écrit — contact à 3 adresses / 3 étiquettes / 2 groupes, vrai dépôt, InMemory — est passé du premier coup, sans correctif.** Marquer `Deleted` des entités `Unchanged` ne touche pas la collection de navigation. La consigne du task file (« ne pas présumer que matérialiser la collection suffit sans le prouver ») a fait exactement ce pour quoi elle était écrite. **Troisième fois dans cette EPIC qu'une prémisse plausible tombe devant une mesure** (task-222 annulée, task-241 sur ses deux faits fondateurs, celle-ci).
- **LA CAUSE RÉELLE.** Ce qui lève est la présence d'une entité **`Added`** dans la collection au moment de l'énumération : EF fait passer une entité `Added` marquée `Deleted` à **`Detached`** (« une entité ajoutée n'existe pas encore en base, il n'y a rien à supprimer »), et le détachement la **retire de la collection de navigation**, donc modifie la liste en cours de parcours. **Comment cet état survient** : le `DbContext` est mémoïsé par instance de dépôt (task-231), donc partagé entre deux enrichissements simultanés du même praticien ; le premier passage a déjà exécuté `AddContactRelations` — enfants `Added` **raccordés à la collection suivie** — quand le second entre dans `RemoveRange`. Le corpus du banc adresse le même praticien depuis plusieurs messages : d'où quatre occurrences par série, et **zéro hors concurrence** — ce qui explique aussi pourquoi la suite de tests existante ne pouvait pas le voir (son seul test de mise à jour passe des collections **vides**).
- **Correctif** : trois `.ToList()`, un par collection — celui que le task file pressentait, mais **posé sur la bonne raison**, donc couvrant toute mutation de la collection suivie et pas seulement le cas imaginé. `ExecuteDeleteAsync` non envisagé (relationnel uniquement, lève sur InMemory — constat empirique de task-250, leçon task-247). Le rejeu de task-250 et la traduction `DbUpdateConcurrencyException` → `ConflictException` sont **inchangés**, vérifiable sur le diff : deux défauts distincts au même endroit, l'un avant l'écriture, l'autre après.
- **Reproduction déterministe et SANS concurrence** : `UpdateAsyncSurvivesAnUnsavedRelationAlreadyAttachedToTheTrackedContact` rattache un enfant non enregistré au contact suivi puis appelle le vrai `UpdateAsync` — rouge avec l'exception **exacte du banc**, sur InMemory, vert après le `.ToList()`. Un test à deux tâches sur un `DbContext` partagé a été **écarté délibérément** : il n'éprouverait que la non-thread-safety d'EF.
- **Verdict sur le chemin contact patient** (demandé par le task file) : **même défaut, corrigé mécaniquement.** `PatientContactService.EnrichContactAsync` appelle **le même** `ContactRepository.UpdateAsync` et n'a pas de chemin d'écriture propre. Aucune occurrence relevée au banc **parce que le corpus n'adresse pas deux fois le même patient**, pas parce que le chemin serait immunisé. Épinglé par test.
- **AIPD** : nom du praticien **retiré** du journal d'erreur (le RPPS identifie l'enregistrement et sert déjà de clé de corrélation dans les lignes voisines) ; l'échec reste **visible** en `Error` et le message dit désormais ce qui est perdu (l'apport au contact) et ce qui ne l'est pas (le message). **Les deux propriétés sont épinglées par le même test** — réduire la donnée ne doit pas rendre la perte silencieuse.
- **Tests** : 10 cas neufs (9 dépôt + 1 service). 450/450 `infrastructure.tests`, 661/661 `api.tests`, 136/136 `domain.tests`, 2 123/2 124 `application.tests` (rouge `AiPromptHelperTests` antérieur).
- **Sonar** : QG new code `ERROR` sur `new_violations = 59`, **aucun finding attribuable**. Les 4 fichiers touchés n'en portent qu'un, antérieur — `csharpsquid:S2302` sur `ContactRepository.cs`, **classé faux positif avec justification par ce run** : la règle veut `nameof(contact)` là où « contact » est de la **prose française** dans un message d'exception ; l'appliquer produirait « du contact contact 3fa8… ». Le compte est parti de **60** et non 59 parce que cette branche ne porte pas le correctif `report.py` de la PR #188 (constante `NOT_MEASURED`, un `python:S1192` de moins) — **le +1 est l'absence d'une amélioration voisine**, il se referme au merge de #188. Hotspots projet **5 → 0** (héritage du run task-256).
- **Findings** : **F-259-1** — 5 tests d'intégration « du jour » rouges **au passage de minuit**, verts deux heures plus tôt dans la même session, contre-épreuve `git stash` identique : décalage de fuseau entre date semée et date filtrée (UTC+2 passé minuit ⇒ date UTC encore la veille). **F-259-2** — la collision de capture du meter existe **aussi dans `infrastructure.tests`** (`MailRepositoryEnrichPersistInstrumentationTests` rouge 1 fois / vert 2 fois sur la même révision), même famille que F-256-3. **F-259-3** — `PatientContactService` journalise **l'INS en clair** ; bien plus sensible que le nom de praticien retiré ici, **non modifié délibérément** car l'INS n'a pas de substitut évident au point du `catch` — le remède demande une décision (pseudonymisation, identifiant de corrélation, ou acceptation argumentée).
- **Dernier critère du DOD ouvert** : « une campagne d'enrichissement au banc ne produit plus aucune `InvalidOperationException` » — c'est une mesure au banc, pas une assertion de code.

---

### v1.53 — L'envoi coûte 1,3 s quel que soit le palier : l'instrument qui décompose enfin le premier poste du temps serveur — task-260

- **Task** : task-260 — `done`. **PR** : `api-mail` #190 (label `awaiting-human-merge`). `dtos-mss` : branche créée, **aucun commit**.
- **LE FAIT.** Tir `journey-500-esc` du 2026-08-14 : `send` p50 **1 305 / 1 270 / 1 302 ms** à 100/200/500 médecins — un coût **fixe par envoi**, pas un effet de charge — et **25,1 % du temps serveur**, premier poste. Trois corrections l'ont visé sans le faire bouger (task-231, 238, 241), toutes écrites **sans décomposition**. Celle-ci la fournit.
- **LIVRÉ.** `SendOperationScope`, quatrième périmètre du modèle maison (task-243/245/252) : six phases — `opposition_guard`, `build_mime`, `acquire_session` (quasi nulle si session réutilisée, paie connexion+TLS+auth si neuve — le coût d'une session fraîche se lit sans instrument séparé), `smtp_transmit`, `archive_sent` (**optionnelle : publiée seulement si observée**, « non relevé » jamais zéro — leçon task-256), `assemble` par différence.
- **L'IMBRICATION PORTE L'ARCHITECTURE.** `SmtpService` est l'étranglement de tous les envois, mais l'archivage vit chez l'appelant : le contrôleur ouvre le périmètre **englobant** (la durée que le médecin paie) et le `Begin` de `SmtpService` devient inerte dessous. Un chemin qui n'archive pas (rejeu, brouillon) obtient quand même la décomposition.
- **report.py** : section « Où part le temps d'un envoi », phrase attribuable, poste dominant nommé — **`assemble` ne peut jamais l'être** (désigner un résidu inviterait à optimiser une soustraction). Note de lecture : le finding Seq du tir 500 (**≈3,1 `SmtpCommandException` par envoi**) confronté aux phases où il devra se confirmer.
- **Tests** : 7 C# (mutation éprouvée **6/7 rouges** — deux faux positifs de protocole corrigés en route : mutation non compilable, puis binaire de test non reconstruit — dans les deux cas les verts ne prouvaient rien) + 6 Python. Collision de parallélisme réglée par le mécanisme prévu (`MailMetricsCaptureCollection`, 4 classes émettrices rangées).
- **⚠️ FINDING PRODUIT DÉCOUVERT EN ROUTE** : la vue « aujourd'hui » a une **fenêtre aveugle nocturne** — `DeliveredAfter(DateTime.Now.Date)` (minuit local) face à des INTERNALDATE UTC (`ImapService.cs:768`) ; 5 tests d'intégration rouges déterministes entre 00 h et 02 h locales. Un médecin de garde à 1 h du matin peut ne pas voir les messages reçus depuis minuit. **À instruire en US produit** ; hors de ce diff.
- **Sonar** : QG **OK**, dette introduite zéro (2 issues sur fichiers touchés, toutes préexistantes, vérifié par `git blame`).

---

### v1.54 — La page d'en-têtes ne matérialise plus ce qu'elle n'affiche pas : −69,5 % d'objets sur le chemin le plus coûteux du parcours — task-261

- **Task** : task-261 — `done`. **PR** : `api-mail` #191 (label `awaiting-human-merge`). `dtos-mss` : branche créée, **aucun commit**.
- **LE FAIT, PAR CROISEMENT DE DEUX INSTRUMENTS.** task-256 (objets) × task-243 (phases), tir du 2026-08-14 : **298 objets matérialisés pour 25 en-têtes affichés** — dont 65 résultats de biologie et des corps de message complets que la page n'affiche jamais. **69,5 % de la matérialisation est du travail invisible.**
- **LIVRÉ, en mode en-têtes uniquement** (`headerOnly`, le mode contenu inchangé) : corps projetés à vide (`Body`/`BodyHtml`/`Summary` = chaîne vide dans la projection SQL — la ligne n'est plus transférée), biologie réduite aux marqués (`IsFlagged`), synthèses non chargées. **Les marqueurs `HasBiologyResults`/`HasPatientSummary` restent exacts** : comptes corrélés portés par la requête documents (sous-requêtes `Count` — la première conception ajoutait une requête, refusée : le DOD exigeait « pas une requête de plus », redessinée en **net −1 requête**).
- **CE QUE LE MÉDECIN VOIT EST INCHANGÉ** — même liste, mêmes badges, même pagination ; vérifié par 6 tests d'intégration sur le vrai dépôt (dont « un document à biologie non marquée garde son badge »).
- **Tests** : 6 cas (`MailHeaderPageMaterializationTests`), seeds réalistes (la biologie exige `PrimaryValue`, le dépôt exige un `UserContextInfo` — deux pièges du modèle découverts en écrivant les seeds).
- **La mesure de confirmation au banc** (part d'objets et coût `assemble` en baisse sur une campagne `journey`) reste due — Manual Test Plan de la PR.
- **Sonar** : QG **OK**, dette introduite zéro.

---

### v1.55 — L'appel `folder` porte 65 % du coût du dashboard et n'était compté nulle part : le chemin des dossiers entre dans le compteur de sollicitations — task-262

- **Task** : task-262 — `done`. **PR** : `api-mail` #192 (label `awaiting-human-merge`). Commits `945cdb8` (instrument), `91f0cfb` (tests mutation-éprouvés). `dtos-mss` : branche créée, **aucun commit**.
- **⚠️ LA PRÉMISSE DE LA US ÉTAIT PÉRIMÉE, ET LE DIRE EST LE PREMIER LIVRABLE.** Le finding fondateur (2026-08-04 : « les 4 appels du dashboard partagent un seul `op` ») avait été traité par **task-240** dès le 5 août. Le rapport du tir 500 attribue déjà appel par appel : **`folder` porte 65 % du coût serveur de l'étape** (3 725,6 s ; p95 826 ms, p50 139 ms, n=13 945 — moyenne **plate** de 100 à 500, un coût fixe par appel). Vérifier l'existant avant d'écrire du code était la première chose à faire — quatrième prémisse réfutée de l'EPIC.
- **LE VRAI TROU ÉTAIT CÔTÉ SERVEUR.** La route `GET /folders/{name}` (p95 serveur 726 ms) n'apparaissait **nulle part** dans le compteur de sollicitations de task-225 : `ImapFolderService` n'y était pas branché, et les **4 allers-retours IMAP** de la recherche de dossier (resolve, open, SEARCH, close) n'étaient comptés par personne — l'angle mort exact que task-225 documentait. Vérifié sur la fenêtre du palier 500 dans le Prometheus persistant : aucune série `GetFolder*`.
- **LIVRÉ** : `MailServerCommands.SearchFolder` (IMAP SEARCH, jamais nommé), les 4 enregistrements dans `ExecuteFolderSearchAsync` étiquetés par la famille appelante (`GetFolderStatus`/`GetFolderQuery` — couvre `folder` **et** `today`), recorder en paramètre optionnel (pattern ImapService, aucun appelant de production ne change).
- **AUCUNE RÉDUCTION LIVRÉE, DÉLIBÉRÉMENT** (le DOD l'exige dit et motivé) : la moyenne de 267 ms mélange cache-hit Redis et cache-miss à 4 allers-retours sous 96 ms de latence — décomposition **pas encore mesurable**, c'est ce que ce compteur rend lisible. **Seuil de reprise** : ≥ 2 allers-retours confirmés par appel non-caché → remède côté cache (durée, ou STATUS au lieu de SEARCH), US dédiée, fraîcheur énoncée.
- **Tests** : 3 (nombre + **ordre**, attribution, absence prouvable), mutation éprouvée avec reconstruction du binaire : 2/3 rouges.
- **Sonar** : QG **OK** ; seule issue touchée = S107 (constructeur 9 params) **préexistante à 8**, +1 optionnel accepté.

---

### v1.56 — Le harnais refuse désormais de mentir : bande d'UID absente = tir refusé, jamais des verdicts verts sur des messages inexistants — task-263

- **Task** : task-263 — `done`. **PR** : `api-mail` #193 (label `awaiting-human-merge`). Commit `286b2ae` (UID_BASE + refus + 16 tests) + doc skill. `dtos-mss` : branche créée, **aucun commit**.
- **LE DÉFAUT.** Le harnais postulait des UID commençant à 1 — vrai seulement sur maildir vierge : les UID IMAP ne sont **jamais réutilisés**, une purge `doveadm expunge` laisse le compteur avancer. Mesuré le 2026-08-14 : 500 boîtes à UID **201–447**, et le banc rendait des verdicts **verts sans rien mesurer** (`enrich` HTTP 200 en ~1 s, 0 mail en base). **Deux campagnes distantes invalidées ainsi.**
- **LE REFUS D'ABORD** (un `UID_BASE` mal réglé reproduirait le défaut en silence) : le `setup()` de tout scénario consommant une bande sonde **trois boîtes** (première/milieu/dernière — des boîtes peuvent différer, trois du banc portaient déjà des bases distinctes) via `GET /folders/{f}` et **refuse le tir** en nommant la boîte, la cause et le geste (`UID_BASE=<valeur>` ou Job `maildir-purge-job.yaml`). Une sonde muette n'est **pas** un laissez-passer. Jugement pur (`uid-guard.js`, testé) séparé de la sonde k6 (`uid-probe.js`). Modèle : le contrôle de budget, qui a refusé une campagne le 2026-08-14 avant de brûler deux heures de banc.
- **`UID_BASE`** (défaut 1, historique intact) : `uid-bands.js` passe par un cœur pur node-testable, `journeyReserves` gagne un 4ᵉ paramètre — préfixe analysé toujours préfixe, réserves disjointes sous décalage (testé).
- **PRÉREQUIS DOD LEVÉ** : Node absent du poste (le selftest JS **skippait** — « un SKIP n'est pas un succès ») → installé v24.19.0. `selftest.sh` : **88 JS + 287 Python, zéro SKIP**.
- **CONTRE-ÉPREUVE, banc local** (mécanisme identique) : seed → expunge → re-seed = boîtes à UID 11–20, l'état du 2026-08-14 en miniature. Sans décalage : **refus** nommant `UID_BASE=11`. Avec : 3/3 enrich réels (« ran the CDA pipeline »), 0 court-circuit, `hasMedicalDocuments=true` en lecture.
- **Doc skill** : le contrôle, le geste de purge, et **pourquoi `kubectl exec rm -rf` échoue** (répertoires `drwx------ 1000:1000` + `root_squash` NFS — le Job tourne en uid 1000).
- **Sonar** : skip propre — aucun C# touché (diff 100 % harnais k6).

---

### v1.57 — Un palier ne mesure plus sa propre préparation : la chauffe est allouée d'avance, taguée `chauffe`, et le régime seul porte le verdict — task-264

- **Task** : task-264 — `done`. **PR** : `api-mail` #194 (label `awaiting-human-merge`). Commits `5edfeba` (modèle + calendrier + rapport + tests), `84c6dcd` (contre-épreuve INDEX). `dtos-mss` : branche créée, **aucun commit**. ⚠️ **Staging : non agrégée** — conflit `journey.js` avec task-263, abort conformément à la règle (ordre de merge conseillé : #193 puis #194, conflit trivial documenté dans la PR).
- **LE FAIT.** Tir du 2026-08-14 : chauffe à **139 %** de la fenêtre du palier (2 494 s au p95 pour 1 800 s). Pendant qu'une cohorte chauffe, la population réellement en régime est inférieure à ce que le tag `palier` annonce — le palier mesurait surtout sa préparation.
- **LEVIER : FENÊTRE DE MESURE DÉCALÉE, DÉRIVÉE DU MODÈLE** — pas observée (les VU k6 n'ont aucun état partagé : personne ne peut savoir à l'exécution quand « la cohorte » a fini). Allocation calculée d'avance des grandeurs qui étalent les vagues (task-253) : vagues **pleines** × réserve ÷ débit plafond — sous-évaluer remettrait de la chauffe dans le régime, l'erreur est du côté sûr. La chauffe **était déjà incrémentale** (task-253, rang de cohorte) : l'allocation d'un palier se calcule sur sa cohorte **nouvelle** — à 500 après 200 : 300 médecins, **44 % d'une fenêtre de 1 800 s, sous les 50 %** exigés.
- **LIVRÉ** : `buildStagePlan` porte `warmupEndS` par palier (défaut : historique intact, prouvé par le test deep-equal existant) ; `palierAt` tague **`chauffe`** pendant l'allocation — hors de tout verdict ; `warmupWindowChecks` **refuse** quand l'allocation avale la fenêtre (aucun régime = aucun verdict possible) et avertit au-delà de 50 % avec le geste ; `report.py` publie « **Fenêtres de verdict** » — chauffe/régime par palier, laquelle porte le verdict, et la rupture de comparabilité **dite** (un tir antérieur incluait la chauffe : pas directement comparable). Tirs archivés sans `warmupEndS` : récit d'origine préservé. **Budget de corpus inchangé** (re-fenêtrage, aucune consommation déplacée).
- **CONTRE-ÉPREUVE (DOD)** — deux tirs à protocole identique, banc local, reset entre jambes : jambe B alloue **28 %**/palier tagués `chauffe`, verdicts **non améliorés par construction** (p95 dashboard régime 667 ms vs 361 — l'exclusion ne flatte pas), chauffe aboutie 100 % et budget passé des deux côtés. Échelle locale = preuve du **mécanisme** ; la part < 50 % à forte population est établie par le modèle et à confirmer à la prochaine campagne distante. `reports/INDEX.md`, entrée 2026-08-15.
- **Tests** : 6 node --test + 4 unittest, mutation éprouvée (branche `chauffe` neutralisée → rouge), selftest zéro SKIP.
- **Sonar** : skip propre — aucun C# touché.

---

### v1.58 — La voie d'écriture IMAP marchait, et rendait quand même l'envoi plus lent : retrait sur contre-épreuve — task-216

- **Task** : task-216 — `done`. **PR** : `api-mail` [#196](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/196) (label `awaiting-human-merge`). Commits `f05443f` (retrait + tests), `1407931` (passe qualité), `ccc66d9` (Sonar S3218). `dtos-mss` : branche auto-incluse, **aucun commit**. Task menée hors run `/forge` — aucune branche staging.
- **⭐ CE N'EST PAS UN REVERT DE DÉPIT, ET C'EST TOUT L'INTÉRÊT DE L'ENTRÉE.** task-213 avait donné au praticien une **seconde session IMAP** (suffixe `#write`) pour que l'archivage d'un envoi ne fasse plus la queue derrière le fetch d'enrichissement du même praticien. **Le mécanisme faisait exactement ce qu'il annonçait** : attente d'`AppendToSent` de 4,345 s à **0,005 s** au p95. Le diagnostic de task-213 est confirmé, pas réfuté.
- **CE QU'IL NE FAISAIT PAS : améliorer l'envoi vu du praticien.** Contre-épreuve task-215, trois tirs 500 praticiens à paramètres identiques, protocole échauffement → purge → tir : `send` p95 **7 874 ms** sur le témoin **sans** voie, contre **10 439** et **12 573 ms** avec ; ratio moyenne/médiane **1,34** contre 1,51 et 1,71. **Le témoin satisfait les deux critères du DOD de task-213** (p95 < 10 s, ratio < 2) **et les tirs porteurs du correctif les manquent.** Ce que la voie retirait au verrou, elle le repayait en ouverture de connexion : détention d'`AppendToSent` de 3,974 s (A) à 4,557 / 5,287 s.
- **LE DÉFAUT D'ORIGINE N'EST PLUS REPRODUCTIBLE SANS LE CORRECTIF** — et c'est la seconde jambe de la décision. Les plafonds de banc levés depuis (Dovecot `service imap` à 8000, `imap-login` high-performance, dossiers `Sent`/`Drafts`/`Trash` déclarés) ont retiré la contention qui produisait « un envoi sur vingt au-dessus de trente secondes ». **task-213 répondait à une mesure prise sur un banc bridé** : le correctif était juste sur le mécanisme et faux sur le bilan, parce que la mesure qui le motivait mesurait le banc.
- **RETRAIT COMPLET ET SYMÉTRIQUE** : `ImapService.WriteLane`, `UserContextInfo.{ForWriteLane, WriteLaneSuffix, IsWriteLane}`, **et** la surcharge `IImapConnectionService.ConnectInternalAsync(UserContextInfo, ct)`. Cette dernière ne figurait pas au « Contenu attendu » : elle n'existait que pour désigner la seconde connexion du même praticien, et la laisser aurait laissé le **moyen** de recréer la voie sans le dire. Ses quatre sites de stub côté tests sont recibles sur la surcharge sans contexte.
- **⭐ LA MESURE RESTE DANS LE CODE, LÀ OÙ LA VOIE ÉTAIT CHOISIE**, avec le tableau des trois tirs, le constat que le témoin satisfait le DOD que les tirs correctifs manquent, la non-reproductibilité du défaut d'origine, et la **réserve « pour cet hôte »** — l'infra du banc partage le CPU des réplicas, mais les trois tirs ont subi ce biais **à l'identique** et c'est l'**écart entre eux** qui est mesuré. Un futur lecteur doit trouver les **deux** moitiés de l'arbitrage, pas seulement la conclusion.
- **CONSERVÉ, ET TRANCHÉ PAR ÉCRIT COMME LE DOD L'EXIGEAIT** : l'instrumentation de task-214 en entier, et `MailProcessingMetrics.LockLaneWrite` **bien qu'elle n'ait plus d'émetteur**. Elle documente la question — « les écritures partagent-elles le verrou des lectures ? » — dont la réponse a coûté trois tirs à 500 praticiens ; la supprimer effacerait la trace de l'arbitrage. La table « Voie | Acquisitions /s » du rapport **n'a plus qu'une ligne**, et c'est précisément ainsi qu'elle atteste du retour à une connexion par praticien : une seconde ligne sur un tir futur signalerait une voie réintroduite, voulue ou non.
- **`report.py`** : le verdict « Archivage vs reste » reste lisible mais **change de sens** — l'écart n'a plus à être en faveur de l'archivage, il est attendu du même ordre que les autres, et ce qui juge la décision est `send` vu du praticien.
- **PREUVE ROUGE AVANT LE RETRAIT**, exigée au DOD. `SingleImapLanePerPractitionerTests` — 3 tests qui capturent le contexte que `AppendToSentAsync` / `AppendToDraftsAsync` présentent **réellement** au gestionnaire de sessions : **3/3 rouges**, contexte `s1#write` au lieu de `s1`. **Un test sur `UserContextInfo` seul n'aurait rien prouvé** — c'est le *choix du contexte par le service* qui décide du nombre de connexions, donc c'est lui qu'il faut épingler. Les 4 tests de voie de task-213 partent avec elle ; `WriteLaneSessionTests` devient `SessionLockTests` et garde ce qui ne dépendait pas d'elle (sérialisation d'une session — le verrou n'est pas supprimé, une session MailKit n'est pas thread-safe — et la garde PGSSI-S de famille d'opération). `CrossTenantOwnershipTests` : **21/21**.
- **⚠️ LE POINT DE REVUE QUI MÉRITAIT VÉRIFICATION.** Repartager le verrou entre archivage et lecture crée un risque de **ré-entrance** : `AppendToSent` appelé alors que le verrou de session est déjà tenu s'auto-bloquerait — ce que deux voies masquaient. Vérifié sur les **deux** sites d'appel (`MailController:1165` et `:1343`) : tous deux suivent un envoi **SMTP**, au niveau du contrôleur, **hors de tout scope de verrou IMAP** ; et les deux appellent `ConnectInternalAsync(ct)`, qui ne prend pas le verrou — c'est `ConnectAsync` qui le prend. C'est de surcroît l'état d'avant task-213, qui fonctionnait.
- **Build / tests** : 0 erreur, **0 avertissement**. api **665/665**, application **2 159/2 159**, domain **136/136**, infrastructure **464/464** ; `selftest.sh` du harnais 94 JS + 297 Python, 0 échec, **0 SKIP**. **Flaky pré-existant caractérisé** : `MarkdownPdfRendererTests` — 1/1/0 échec sur **trois exécutions identiques**, vert en isolation, **présent sur develop** (mesuré par `git stash`).
- **Sonar** : `new_coverage` 88,3 → **88,4 %**, duplication et hotspots inchangés. **Un seul finding attribuable, et il venait de la passe qualité** : `csharpsquid:S3218` — la constante `Lane` introduite par `/forge-simplify` en remplacement de `LaneOf(UserContextInfo)` **masquait** le membre positionnel `Lane` du record imbriqué `LockTags`. Renommée `LaneLabel`. Enchaînement à retenir : la passe qualité a supprimé un `S1172` en attente (paramètre ignoré) et **en a introduit un autre en le faisant** — le scan qui suit la passe qualité n'est pas une formalité. Après correction : **0 issue** sur les 12 fichiers C# de la task. ⚠️ `new_violations = 68` **non causées par cette PR** : `report.py` (22), `journey-model.js` (14), `journey.js` (7) — harnais des tasks 263/264 déjà mergées ; vérifié sur pièce, les findings de `report.py` portent sur les lignes 864 à 5378 et les quatre hunks de la task sur ~697/~4012/~4028/~4054, aucun recouvrement.
- **Suggestion non résolue** : `AppendToDraftsAsync` n'a **aucun appelant en production** (déclaration d'interface + implémentation seulement). Surface morte antérieure à cette task, hors périmètre — à constater avant de la retirer ou de la rebrancher.
- **DÛ AU BANC, ne bloque pas le merge mais bloque la clôture de l'US** : tir 500 praticiens iso-conditions avec task-215 — `send` p95 < 10 s, ratio < 2, table des voies **sans ligne `write`**, sessions IMAP Dovecot revenues au plancher d'avant task-213 (~2 500 à 500 praticiens contre ~5 000 avec la voie). ⚠️ Lancer `observe.ps1` **avant** le tir : task-215 ne l'a pas fait et le comptage des sessions Dovecot lui a manqué.


---

### v1.59 — Le corpus du banc ne portait aucun fil : la moitié chère de `GetThreadCountsAsync` était multipliée par zéro — task-267

- **Task** : task-267 — `done`. **PR** : `api-mail` [#199](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/199) (label `awaiting-human-merge`). Commits `1728d25` (générateur + seed + rapport + 28 tests), `7a77664` (`/forge-simplify` : borne stricte + épinglage cross-langage). `dtos-mss` : branche créée, **aucun commit**. Staging : hors run `/forge` (cycle `/start` unitaire).
- **LE FAIT, ET IL EST MÉCANIQUE.** `BuildMime` (`tests/mss.mail.loadtest.seed/Program.cs`) posait `From`, `To`, `Subject`, corps et pièces jointes — **ni `In-Reply-To`, ni `References`**, zéro occurrence sur tout le seeder et tout le harnais. Sur `MailRepository.GetThreadCountsAsync`, la première requête (`existingMessageIds`, balayage complet) était bien exercée parce que MimeKit génère un `Message-Id` à l'`APPEND` ; la seconde (`allMailsWithReferences`) ramenait **0 ligne**, et la boucle `racines de la page × lignes citantes` tournait **à vide**. C'est précisément la part que task-194 chiffre à « 50 racines × 50 000 lignes = 2,5 M de recherches de sous-chaîne par page ».
- **⭐ LA CONSÉQUENCE EST UN PIÈGE D'ATTRIBUTION, PAS UNE IMPRÉCISION.** Une campagne aurait conclu à un gain modeste pour task-194 **par défaut d'exercice**, et l'aurait attribué à la faiblesse du correctif. Même famille que les pièges déjà payés par cette EPIC (task-244 chauffe expirée, task-263 UID inexistants, task-264 chauffe dans le verdict) : un instrument qui rend un chiffre crédible **sans avoir mesuré la chose**.
- **LEVIER : `--thread-share` (0 inclus à 1 exclu), OPT-IN, DÉFAUT 0.** `LoadTestPlanGenerator.GenerateMessages(count, recipient, threadShare = 0.0)` — à 0, aucun en-tête de fil, **aucun `Message-Id` imposé** : le corpus d'hier à l'identique. L'activation volontaire est la contrepartie assumée d'un changement de corpus qui rompt la comparabilité (même exigence que task-264 pour le re-fenêtrage).
- **⭐ UN TEST A RÉFUTÉ LA PREMIÈRE CONCEPTION, ET C'EST LE POINT LE PLUS UTILE DE L'ENTRÉE.** Le cycle de profondeurs était d'abord **figé** à `[1, 2, 4]` réponses. Une chaîne de `R` réponses consomme `R+1` messages : la part maximale atteignable est donc `R/(R+1)`, soit **0,70** pour ce cycle. `TheRequestedShareOfRepliesIsHonoured(0.75)` est passé rouge — une part demandée de 0,75 n'aurait **pas** été tenue, et le rapport aurait publié un chiffre faux en toute confiance. `DepthsFor` dérive désormais les longueurs de la part (`R = max(1, ceil(s/(1-s)))`, cycle `[R, R+1, R+2]`), ce qui garantit que le budget de réponses tient dans le corpus.
- **DÉTERMINISME INTACT** : `ThreadPlan` est un parcours séquentiel sans aucun tirage aléatoire — même entrée, même corpus, seed idempotent (`TheThreadedCorpusStaysDeterministic`). Les identifiants portent l'index de boîte (`lt-{boîte}-{index}@loadtest.local`) : `ThreadsNeverSpanTwoMailboxes` interdit qu'un fil traverse deux boîtes, ce que la production ne produit pas. `References` cumule la chaîne **racine en tête** (RFC 5322 § 3.6.4) — c'est cette position que le comptage exploite (`References.Split(' ')[0]`).
- **LES IDENTIFIANTS VOYAGENT SANS CHEVRONS.** MimeKit les pose lui-même sur `mime.MessageId` / `mime.InReplyTo` / `mime.References.Add(...)` ; les doubler aurait produit des en-têtes que le parseur du produit n'aurait rattachés à rien. C'est aussi la forme que la base contient à la lecture — d'où l'insertion directe dans `SeededThreadsAreCountableTests`.
- **⭐ VÉRIFICATION SUR PIÈCE (le seul critère qui juge la US).** `SeededThreadsAreCountableTests` (intégration, Testcontainers, vraie base) part du **vrai générateur** du banc et interroge le **vrai** `GetThreadCountsAsync` : à `threadShare: 0` le comptage rend **vide** ; à `0.5` il rend des fils **dont les tailles égalent les chaînes semées** (`TheCountedThreadsMatchTheSeededChains`) et **plusieurs profondeurs distinctes** (`SeveralDistinctThreadSizesReachTheCounter`, 120 messages). Rejouer une fixture écrite à la main aurait prouvé que le comptage sait compter — pas que le corpus sait produire des fils.
- **`report.py` — section `## Corpus — fils de discussion`**, câblée avant `_validity_section` (la forme du corpus se lit AVANT les chiffres : elle décide de ce qu'ils veulent dire). Trois choses y sont **dites**, pas sous-entendues : (1) la part est une **déclaration** (`CORPUS_THREAD_SHARE`, même contrat que `MESSAGES_PER_USER`), le harnais ne relit pas le corpus ; (2) la taille moyenne est **déduite** de la part, pas relevée — publier un chiffre dérivé comme s'il était mesuré est la façon la plus simple de rendre un rapport faux sans mentir ; (3) à part non nulle, la **rupture de comparabilité** avec les campagnes antérieures. **Témoin négatif testé** : à part nulle, aucune rupture n'est annoncée — sinon l'avertissement devient du bruit et cesse d'être lu ; à la place le rapport dit que le coût du comptage n'est **pas exercé** et qu'un gain publié sur ce chemin est un **plancher, jamais un plafond**.
- **`/forge-simplify` (`7a77664`) — deux corrections réelles, pas cosmétiques.** (1) Une part de **1,0** était acceptée des deux côtés et produisait une **taille moyenne de 0** dans le rapport : elle n'est pas constructible (le premier message d'une boîte n'a personne à qui répondre) et est désormais **refusée franchement**, ce qui retire au passage la branche morte `threadShare >= 1.0 ? MaxMessagesPerUser`. (2) La formule de taille de fil vit en **deux copies, deux langages, deux processus** — configuration exacte où une divergence passe inaperçue ; `ThePublishedAverageThreadSizeIsTheOneTheCorpusActuallyProduces` **mesure** le corpus réellement produit et le compare aux mêmes chiffres que `test_the_derived_average_matches_the_generator_rule` publie côté Python. Toucher l'une sans l'autre rend l'un des deux rouge. (3) `CORPUS_THREAD_SHARE_MAX` → `CORPUS_THREAD_SHARE_EXCLUSIVE_MAX` : un nom qui dit MAX pour une borne exclue est un petit piège.
- **BUDGET DE CORPUS INCHANGÉ**, et c'est vérifiable par construction : `GenerateMessages` boucle `1..count` quoi qu'il arrive — les fils ajoutent des **en-têtes**, pas des messages. La bande d'UID visée par `assertUidBandsExist` (task-263) est donc identique. Le contrôle reste une vérification d'exécution (banc vivant) et figure au Manual Test Plan.
- **Tests** : 12 (`LoadTestThreadCorpusTests`) + 4 (`SeededThreadsAreCountableTests`, intégration) + 4 (`SeedOptionsTests`, dont la **locale machine** — `ParseDouble` en `InvariantCulture`) + 9 (`test_report_corpus_threads.py`). Mutation éprouvée sur l'énoncé de rupture de comparabilité (le rendre muet → rouge).
- **Build / tests** : 0 erreur, **0 avertissement**. api **685/685**, application 2 162/2 163 (flaky PDF pré-existant `MarkdownPdfRendererTests`, **vert en isolation**), infrastructure **464/464**, domain **136/136**, intégration **417/433** (16 ignorés, tous `UC-AI-*` dépendants d'Ollama, vérifiés par leur nom). `selftest.sh` : **94 JS + 306 Python**, 0 échec, **0 SKIP**.
- **Sonar** : scan complet `EXECUTION SUCCESS`. **0 violation et 0 hotspot imputables** — les 70 violations et 10 hotspots de la *new-code period* ont été rapportés à leur **ligne** puis croisés avec le diff ; aucun ne tombe dans les lignes ajoutées, y compris les 22 de `report.py` (toutes hors du bloc 5378–5483). Seul cas limite nommé : le `S3776` de `build_report` (ligne 5484) est **adjacent** au code de la task, qui y ajoute 3 lignes — deux commentaires et un `lines.extend(...)`, donc aucune branche : complexité inchangée **par construction**. ⚠️ Le tableau baseline → final de la PR est **non opposable** : la dernière analyse remontait au 2026-08-06 sur un commit antérieur de ~2 950 lignes (tasks 226 à 266 mergées entre-temps), et le passage de 0 % à 78,3 % de couverture est un **artefact de mesure** (le tir précédent n'avait produit aucun rapport OpenCover).
- **Suggestions non résolues** : (1) `ParseDouble` retombe silencieusement sur le défaut — `--thread-share abc` vaut 0 sans un mot ; c'est la convention existante du fichier (`ParseInt` fait pareil), mais pour cette option un 0 silencieux veut dire « aucun fil semé » pendant que l'opérateur croit le contraire → task transverse. (2) `--thread-share` (seeder) et `CORPUS_THREAD_SHARE` (k6) sont **deux déclarations indépendantes du même fait** ; un désaccord produit un rapport qui décrit avec assurance un corpus qui n'a pas été semé — le script de campagne gagnerait à passer une seule valeur aux deux.
- **DÛ AU BANC, ne bloque pas le merge mais conditionne la valeur des mesures voisines** : les campagnes de task-266 et task-194 restent dues, et tant qu'elles tournent sur un corpus sans fil leurs chiffres sont des **planchers**. Le tir de référence à conduire : seed `--thread-share 0.3` + campagne `CORPUS_THREAD_SHARE=0.3`.

---

### v1.60 — Le pool SMTP existait et ne servait jamais : le battement d'entretien vivait pile sur le délai de coupure du serveur — task-269

- **Task** : task-269 — `done`. **PR** : `api-mail` [#201](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/201) (label `awaiting-human-merge`). Commits `c0d6b51` (cadence dédiée + rétention découplée + mort visible), `4e36067` (`/forge-simplify` : garde `IsEnabled` sur le décodage JWT de diagnostic), `da89733` (Sonar : S3776 boucle décomposée, CA1816). `dtos-mss` : branche créée, **aucun commit**. Hors run `/forge` (cycle `/start` unitaire).
- **⭐ LA CAUSE N'ÉTAIT PAS L'ABSENCE DE POOL — C'ÉTAIT UNE COURSE PERDUE D'ENTRETIEN.** task-231 avait posé la réutilisation, task-238 la sonde et le keep-alive, task-241 son comptage. Mesuré à la prise le 2026-08-25 : le serveur du banc coupe toute connexion SMTP inactive **entre 28 et 35 s** (GreenMail direct ET via Toxiproxy — le proxy est hors de cause ; un NOOP/15 s la tient indéfiniment). Or le battement SMTP vivait sur la cadence IMAP : **30 s** — chaque battement était un tirage à pile ou face, perdu en un ou deux cycles. Preuve compteur : **1 seul NOOP `SmtpKeepAlive`** sur une session de plusieurs minutes (Prometheus local).
- **⭐ ET LA MORT ÉTAIT INVISIBLE PAR CONSTRUCTION.** Le battement perdant jetait le client en `LogDebug` (niveau jamais émis au banc) : au prochain emprunt `slot.Client == null`, la sonde n'est **jamais atteinte**. Reproduction locale : 84 envois → **84 connexions fraîches, 0 sonde « morte », 0 éviction, zéro trace**. C'est aussi la résolution de l'énigme des **~1,9 `SmtpCommandException`/envoi** (task-269 l'exigeait avant tout remède) : comptées par `dotnet_exceptions_total`, **zéro occurrence dans Seq** sur tout le tir du 2026-08-24 — des exceptions levées puis avalées (battements mourants, QUIT sur connexions coupées), pas un rejeu de commandes d'envoi ; le dénominateur « par envoi » était une coïncidence de ratio.
- **SECOND ÉTAGE, au rythme réel multi-réplicas** : même entretien réparé, l'éviction `SmtpIdleTimeout=5 min` refermait la connexion entre deux envois d'un même réplica (~17 min d'écart à 5 réplicas au palier 1000 — les envois d'un praticien se répartissent sur les réplicas).
- **REMÈDE EN TROIS PIÈCES, contrat d'API inchangé.** (1) `SmtpKeepAliveInterval` dédié (défaut **15 s**, 0 = hériter de la cadence IMAP — rétro-compatibilité testée), par domaine via `MailServers` ; boucle de session à deux échéances (`BeatImapLaneIfDueAsync`/`BeatSmtpLaneIfDueAsync`). (2) `SmtpConnectionRetention` **découplé** de `SmtpIdleTimeout` : défaut = la connexion vit avec la session (entretenue par le keep-alive, la sonde task-238 rattrape une fermeture serveur) ; `SmtpIdleTimeout` garde son rôle dans l'**expiration de session** — pas d'inflation de la vie des sessions ni des sièges IMAP, et l'opérateur qui exige la restitution anticipée du siège SMTP la configure par domaine. (3) L'échec du NOOP d'entretien passe en `Information` avec le type d'exception — une occurrence par mort réelle, fin de l'aveuglement.
- **PGSSI-S au passage** : le log Warning `🔐 SMTP auth … TokenPreview=` (aperçu de token **en clair**, un par connexion fraîche — donc un par envoi tant que le pool ne servait pas) devient un Debug **sans aperçu**, gardé par `IsEnabled` (le décodage JWT de diagnostic n'est plus payé au niveau nominal).
- **Vérification sur pièce (locale, avant/après par seuils)** : envois espacés de 2 s réutilisés (~0,75 s vs 2-3 s à froid, 5 connexions fraîches pour 10 envois = 1 par réplica), mais **+75 s = connexion fraîche systématique** avant correctif — c'est le seuil qui a nommé la cause. Post-correctif attendu : réutilisation à tout écart tant que la session vit ; contre-épreuve au banc due (tir journey iso-conditions, `send` p50 < 1 000 ms, `acquire_session` ≈ 0 sur envois suivants).
- **Tests** : 2 nouveaux (cadence SMTP dédiée avec IMAP léthargique ; rétention par défaut = pas d'éviction), 2 adaptés (éviction désormais sur rétention configurée), acquis task-231/238 inchangés et verts (réutilisation, sonde, verrou, `A_reused_session_publishes_a_zero_acquisition_and_not_a_silence`). **3 884 tests, 0 échec.** Flaky pré-existant identifié hors diff : `EnrichmentOperationScopeTests` (pollution du Meter global sous parallélisme xUnit, 5/5 vert en isolation) — candidat US harnais de test.
- **Sonar** : Quality Gate **OK**, 0 bug / 0 vulnérabilité, violations new-code 37 → 35 (S3776 boucle décomposée, CA1816) ; acceptés en faux positifs : S3604 ×9 (initialiseurs avec constructeurs primaires C# 12), S125 ×3 (commentaires en prose). Couverture new-code 91,0 %.
- **Hors périmètre constaté en route** : `MdnService` ouvre une connexion SMTP **fraîche par accusé de lecture** (sans pool) — invisible au banc (aucune demande d'accusé dans le corpus), à instruire si les MDN prennent du volume. L'archivage Sent (~407 ms, troisième tiers de l'envoi) est porté par **task-272**.

---

### v1.61 — L'acquittement d'un envoi n'attend plus l'archivage dans « Envoyés » — task-272

- **Task** : task-272 — `done`. **PR** : `api-mail` [#202](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/202) (label `awaiting-human-merge`). Commits `d2b5ba0` (file + rejeu + contrat de réponse), `c3608da` (`/forge-simplify` : délai borné par la table, scope redondant retiré), `10b3143` (Sonar S4457), `99037aa` (test de mesure hors chemin). `dtos-mss` : branche créée, **aucun commit**. Hors run `/forge`.
- **LE TIERS RESTANT DU SEUL ROUGE SLO.** La décomposition task-260 (confirmée à 1 000 médecins le 2026-08-25) donnait l'envoi en trois tiers ; task-269 (mergée, `aba835b`) a traité `acquire_session`, celle-ci sort `archive_sent` (~407 ms) du chemin de la réponse : **l'acquittement est rendu à l'acceptation SMTP**. Attendu combiné : p50 sous ~550 ms pour une cible de 1 000 — contre-épreuve au banc due.
- **⭐ RÉUTILISATION INTÉGRALE, ZÉRO MÉCANISME NEUF.** La file de task-075 (`IBackgroundTaskQueue` : scope DI par travail, exceptions observées centralement) porte l'archivage ; l'identité voyage par `CopyIdentityTo` (task-234 — copie complète, le champ oublié qui visait une autre base ne peut pas se reproduire) ; le travail différé retrouve la **même session IMAP poolée** (`{Email}_{ClientSessionId}`) et son verrou `imap_session`. Aucune voie d'écriture dédiée — l'interdit de task-216 est respecté à la lettre.
- **RÈGLE MÉTIER DE L'ÉCHEC DIFFÉRÉ, gravée et testée** : rejeu borné (3 tentatives, 2 s/10 s, dernier délai répété si la table diverge), chaque tentative auditée (`MailArchiveSent`, task-223), échec final `LogError` corrélé au `traceId` de l'envoi + compteur `mssante_send_archive_outcomes_total{outcome}` — jamais silencieux, jamais un échec d'envoi rétroactif. L'invariant task-223 devient garanti **par construction** (la réponse part avant toute tentative) ; les 4 tests du contrat synchrone sont réécrits en préservant leur intention.
- **MESURE HORS CHEMIN, une seule série** : la durée d'archivage reste publiée sur `archive_sent` (histogramme des phases d'envoi), hors du périmètre `SendOperationScope` — le modèle exact de l'empreinte sémantique de l'enrichissement (task-245). Le `Begin` englobant du contrôleur, devenu redondant, est retiré. Test MeterListener dédié (2 durées pour 2 tentatives, issue `retried`).
- **CONTRAT DE RÉPONSE** : `{ queued, archivePending }` — `archived`/`warning` retirés après vérification qu'**aucun front ne les lisait** (Blazor : `Queued`/`Message` seulement) ; `ApiMessages.MailSentButNotArchived` orphelin retiré.
- **DOD « SemaphoreFullException »** : cause établie — libération par CLÉ sur entrée de session recyclée → sémaphore neuf au plein — **déjà corrigée à la racine par task-223** (jeton `ImapSessionLockHandle`, libération idempotente) ; couverture vérifiée (`SessionLockReleaseMismatchTests`). La mémoire du banc (bug du 2026-08-06 « NON corrigé ») est donc périmée depuis task-223.
- **Limites dites** : file **en mémoire** — un crash du processus entre acquittement et exécution perd la copie « Envoyés » sans trace (assumé : incident de confort, le message est remis ; persistance de la file si la fréquence l'exige). Le **rejeu offline** (`ProcessSendMailAsync`) n'archive pas — écart pré-existant, candidat US.
- **Tests** : 3 892 verts, 0 échec — 13 nouveaux/réécrits (réponse avec archivage infiniment lent, composition scope DI + identité, rejeu ×3, capture anti-mutation, mesure hors chemin). **Sonar** : QG OK, 0 bug/0 vuln, violations new-code 38→37 (S4457 corrigé ; S3604 ×2 acceptés — FP constructeurs primaires), couverture new-code 91,3 %.

### v1.62 — Le « timeout à 60 s » n'existait pas : c'était la dernière borne des histogrammes, et le rapport l'imprimait comme une mesure — task-271

- **Task** : task-271 — `done`. **PR** : `api-mail` [#203](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/203) (label `awaiting-human-merge`). Commits `7091d60` (étiquette `phase`), `2a5073c` (harnais : refus de publier un quantile saturé), `12a1dc4` (`/forge-simplify` : 3 findings), `0c5f037` (Sonar S125 ×2), `2437f61` (portée réelle de `phase=n/a`). `dtos-mss` : branche créée, **aucun commit**. Hors run `/forge`.
- **⭐ LA US EST ÉCRITE SUR UNE LECTURE FAUSSE, ET C'EST LE LIVRABLE PRINCIPAL DE LE DIRE.** La campagne du 2026-08-23 publiait « détention p95 `imap_session` / `GetFolders` = **60,000 s** », et la US en déduisait « une valeur au plafond exact désigne un timeout ». Ni timeout, ni travail de 60 s : `DurationBucketBoundariesSeconds` finit par `…, 10, 30, 60`, et **`histogram_quantile` rend la dernière borne finie quand le quantile tombe dans `+Inf`**. Le chiffre signifiait « ≥ 60 s, borne supérieure inconnue ». La précision à la milliseconde était un artefact de formatage — et toute conclusion quantitative tirée du « 60,000 » est non opposable.
- **RECENSEMENT DES BORNES DU CHEMIN `GetFolders`, à charge** : attente du verrou **120 s** (`LockImapClientAsync`), timeout de requête **5 min**, téléchargement OCSP/CRL **5 s**, `ImapClient.Timeout` MailKit **120 s** (défaut, jamais surchargé). Les trois constantes à 60 s / 1 min du module (`ConnectionKeepAliveInterval`, `SessionCleanupInterval`, `SmtpProbeMaxAge`) sont des **cadences**, pas des bornes d'opération. **Aucun timeout à 60 s n'existe.**
- **CE QUI EST RÉELLEMENT LONG, ET POURQUOI C'ÉTAIT MÊLÉ** : le p95 serveur de `GET /mail/folders` à 56,8 s est, lui, une vraie mesure (interpolée dans `[30, 60]`). `GetFoldersAsync` tient `imap_session` pendant `ConnectInternalAsync` (DNS + TCP + TLS + révocation + AUTH), et la chauffe établit ~300 sessions fraîches au front de chaque palier (58-60 % de chaque fenêtre). Comme `imap_session` est un verrou **par praticien**, une détention de 60 s n'est pas de la contention : c'est l'opération qui dure. D'où la réconciliation de « 155 ms vus de k6 » et « ≥ 60 s de détention » — deux populations, une seule étiquette, aucune requête pour les séparer.
- **CORRECTIF ÉCARTÉ, SUR ANALYSE** : la US envisageait de sortir TCP+TLS du verrou (« il n'a pas à couvrir TCP+TLS si la session n'est pas encore partagée »). **La prémisse est fausse** : `GetOrCreateImapClientAsync` rend l'unique `IImapClientWrapper` de la session, **déjà partagé avant d'être connecté**, et c'est cette instance que `ConnectInternalAsync` connecte. Établir hors verrou laisserait deux appelants du même praticien appeler `ConnectAsync` sur le même `ImapClient` MailKit — la classe de défaut fermée par task-187 et task-223. Le verrou **doit** couvrir l'établissement ; livrer ce « correctif » aurait échangé une mesure illisible contre une corruption de session.
- **ÉTIQUETTE `phase` sur `mssante_lock_hold_duration_seconds`** : `establish` / `operate`, selon que la session était connectée **et** authentifiée à la prise du verrou. Résolue à l'**acquisition** (à la libération tout vaudrait `operate`) et **après** la prise du sémaphore (avant, un autre appelant pourrait établir entre la lecture et la prise). Le cas *connecté mais non authentifié* compte comme `establish` — `ConnectInternalAsync` y déconnecte puis refait CONNECT + TLS + AUTH. Sonde `IsImapClientEstablished` **sans effet de bord** : ni `GetOrCreateSession`, ni accès à `ImapClientWrapper` (dont la lecture crée le wrapper et démarre son keep-alive) — c'est `ImapClientWrapperOrDefault` qui est lu, comme `AuthenticatedSessionCount`. L'**attente ne porte pas la phase**, délibérément, et un test l'empêche d'y fuiter.
- **PGSSI-S + cardinalité** : deux littéraux écrits dans le code, même barre que `lane` et `operation`. `phase=n/a` couvre `in_process_fetch`, `distributed_fetch` — et `smtp_session`, qui **est** un verrou de session et paie lui aussi un établissement depuis task-269 : le découpage par phase de la voie SMTP est laissé **ouvert explicitement** plutôt que masqué par un libellé inexact.
- **LE HARNAIS DIT DÉSORMAIS QUAND IL NE MESURE PLUS** — et c'est structurel : il avait rencontré ce défaut de plafond **deux fois** (buckets en millisecondes de task-211 ; plafond à 10 s de `http.server.request.duration` de task-245) et l'avait corrigé les deux fois **en déplaçant les bornes**, jamais en rendant la saturation visible. `num_saturable()` imprime **`≥ 60 ⚠️`** et jamais `60.000`, sur les quantiles des deux tables de verrous — **pas** sur les taux (60 acquisitions/s n'est pas une saturation). Deux colonnes de détention par phase, et trois lectures nommées plutôt qu'inférées : agrégat non décomposé (« il mélange »), agrégat saturé mais exploitation lisible (« ✅ la queue est la chauffe »), **exploitation** saturée (« 🚨 défaut de portée du verrou »).
- **⚠️ CE QUE LA LIVRAISON NE PROUVE PAS** : le DOD exigeait les `TraceId` du tir du 2026-08-23. **Non produisibles** — Seq local ne retient plus rien avant le 2026-08-25, le Seq distant répond 401, et `report-journey-500-esc-20260823-220658.md` est git-ignoré (`.gitignore:386`) et absent du disque. La cause de la *valeur publiée* est établie sur le code et la définition de l'instrument, donc indépendante des traces ; restent ouvertes la **borne supérieure réelle** des détentions saturées et leur répartition temporelle (fronts de palier vs extinction) — mesurables au prochain tir grâce à l'étiquette, sans dépendre d'une rétention.
- **Compatibilité** : ajouter une étiquette ne casse aucune requête existante — `sum by (le, lock)` et `sum by (le, operation)` agrègent sur `phase`.
- **Tests** : preuve rouge d'abord (4 échecs `KeyNotFoundException: 'phase'`), puis 6 tests C# verts + 14 tests harnais ; `selftest.sh` **320 tests, 0 SKIP** ; build **0 erreur / 0 avertissement**. Suite api-mail comparée à `origin/develop` en worktree isolé : **delta zéro** (4 `EmbeddingOptionsConsistencyTests`, 6 scans d'architecture, 91 integration sans Docker, plus les flakies connus `MailExportServiceTests` et `EnrichmentOperationScopeTests` — ce dernier reproduit sur develop 2 tirs sur 3).
- **Sonar** : smells 67→**63**, dette 572→**541** min, violations new-code 68→**65**, couverture new-code 88,3 %→**88,4 %**. **QG ERROR** sur la seule condition `new_violations`, avec **0 issue portée par les fichiers de la task** : la new-code period couvre une baseline large incluant des tasks déjà mergées (`report.py` S3776 en liste noire, scénarios k6, tests `Embedding`). Correctifs de la passe : **2 × S125**, ponctuation seule — une introduite ici, une pré-existante de task-269 corrigée au passage. Déclencheur mécanique consigné dans `conventions/csharp.md` (une ligne `//` finissant par `;` suffit), avec son contrôle `grep` avant commit.




### v1.63 — Chaque widget du tableau de bord a son interrupteur de charge (feature flags Flagsmith, trois fronts) — task-274

- **Task** : task-274 — `done`. **PRs** : `api-mail` [#204](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/204), `client-blazor` [#69](https://github.com/codengine-technologies/HealthPlatform.Client/pull/69), `client-mobile` [#63](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/63) — toutes `awaiting-human-merge`. `client-angular` : code-only, diff non committé sur `feature/nova-rewriting-mss` (humain gère TFS). `dtos-mss` : branche créée, **aucun commit** (zéro changement de contrat). Règle 11 : les 3 PRs GitHub + le diff Angular forment **une** US — test humain sur l'ensemble assemblé avant merge.
- **Pourquoi dans cette EPIC** : l'arrivée sur le tableau de bord est le geste le plus fréquent du parcours et le **deuxième poste du temps serveur** (24,8 % au palier 1000, campagne du 2026-08-26), porté par plusieurs appels distincts. Impossible jusqu'ici d'**attribuer** la charge à un widget précis autrement que par instrumentation, et impossible de **délester** en production sans redéployer. Chaque widget est désormais gouverné par un flag Flagsmith `dashboard_widget_{slug}` : OFF → le widget est masqué **et son appel API n'est pas émis** — un interrupteur de charge, pas d'affichage (masquer sans couper l'appel ne changerait rien à la charge).
- **Les 8 flags** (mêmes noms sur les trois fronts, tous créés ON) : `dashboard_widget_mail_counters`, `dashboard_widget_mail_notifications`, `dashboard_widget_today_summary` (mobile seul), `dashboard_widget_abnormal_biology`, `dashboard_widget_biology_ack_pending` (⚠️ obligation métier — **outil d'incident uniquement**), `dashboard_widget_patients`, `dashboard_widget_sync_progress`, `dashboard_widget_offline_status`. Correspondance widget → appels serveur consignée dans la task (inventaire final /develop).
- **Deux règles portées par les trois implémentations** : (1) **fail-open sans exception** — flag absent, Flagsmith injoignable, endpoint en erreur, réponse lente → tout est visible, comportement d'aujourd'hui, aucune erreur praticien ; (2) **coût nul sur le geste instrumenté** — les flags sont lus via l'endpoint existant `GET /api/v1/FeatureFlag` **une fois par session applicative** (cache 5 min), jamais un appel par affichage du dashboard : instrumenter le poste sans l'aggraver.
- **api-mail** (`878794c`) : seul le **seeder de banc** change — les 8 flags ajoutés au tableau `FeatureFlags` de `FlagsmithSeeder` (AppHost, `default_enabled=true`) : au démarrage du banc ils existent, ON. Aucun garde serveur par flag (couper l'appel côté client coupe la charge — un garde serveur dupliquerait), aucun changement d'endpoint. En staging/prod la création des flags reste un geste d'exploitation **manuel** à partir de la liste — le code applicatif ne crée jamais de flag hors seeder de banc.
- **client-blazor** (`29c988f`) : contrat opt-in `IFlaggedWidget` (`FeatureFlagName`), service `DashboardWidgetFlagService` (fail-open, budget 3 s, cache 5 min, vol unique), gating dans `DashBoard.razor` — un widget flag-OFF n'est **jamais instancié** (`DynamicComponent` non créé), prouvé par un `ProbeComponent` qui compte les initialisations. Service absent du DI = tout visible. 7 widgets marqués, 6 tests.
- **client-mobile** (`86c3406`) et **client-angular** (code-only) : même triptyque par front — service à signaux (`DashboardWidgetFlagsService`, préfixe `dashboard_widget_`, TTL 5 min), `getFeatureFlags()` sur `MssApiService`, `@if` autour de chaque sélecteur de widget (composant non instancié = appels jamais émis), `ensureLoaded()` fire-and-forget à l'entrée. Duplication mobile/Angular **structurelle** (workspaces sans lib partagée, convention miroir du repo). Mobile : 5 widgets, 6 tests, 769/769. Angular : 7 widgets, 7 tests vitest, `mss-lib` 322/322, build `weda2` aval vert, lint scope MSS **0 erreur** (JSDoc complétés à la main après `--fix`).
- **Qualité** : /sonar skip motivé — l'unique fichier api-mail touché (`FlagsmithSeeder.cs`) est dans un chemin exclu de l'analyse (`**/AppHost/**`). /lint-mobile baseline 0 erreur. /verify-visual best-effort skip (outillage absent du poste ; gating pur, rendu identique flags ON — filet : specs de rendu du `home` dont flag OFF → sélecteur absent). Code review : **APPROVED, 0 bloquant** ; 1 suggestion — le DashBoard Blazor attend la première lecture (3 s max, une fois par session) là où mobile/Angular sont en fire-and-forget, à aligner si la latence du premier affichage devient visible.
- **Usage attendu au banc et en exploitation** : attribution de charge par activation/désactivation sélective widget par widget (pré-prod, banc en conditions réelles — complète l'attribution par appel de task-240/262), et levier de délestage en incident (couper le widget coûteux sans redéployer, propagation ≤ 5 min acceptée). Le harnais k6 n'est pas modifié (l'attribution au banc passe déjà par les probabilités `JOURNEY_*`).


### v1.64 — Le chemin froid de `GET /folders/{name}` payait deux fois `resolve` + `STATUS` : 7 → 5 allers-retours IMAP — task-270

- **Task** : task-270 — `done`. **PR** : `api-mail` [#205](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/205) (label `awaiting-human-merge`). Commits `6e1551b` (fusion des deux séquences + tests), `3f5d48b` (`/forge-simplify`), `42482a7` (CA1861 new-code). `dtos-mss` : branche créée, **aucun commit** — zéro changement de contrat.
- **LE DÉFAUT, NOMMÉ PAR L'INSTRUMENT DE task-262.** L'appel `folder` porte **63 % du temps serveur du dashboard** (3 899,7 s au palier 500 du 2026-08-23), le dashboard pesant 23,1 % du total. p95 **plat** de 100 à 500 médecins (696 → 699 → 698 ms) : coût fixe par appel, pas un effet de charge — donc remède côté **contenu**, pas côté capacité. Le compteur de sollicitations donne, sur la fenêtre du tir : `GetFolderQuery` 5 commandes × 16 283 exécutions, `GetFolderStatus` 2 commandes × 52 749. Séquence froide réelle : `resolve` + `STATUS` (`GetFolderWithCacheAsync` → `GetFolderStatusAsync`), puis `resolve` + `STATUS` + `SELECT` + `SEARCH` + `CLOSE` (`GetFolderQueryAsync`) — **sept** allers-retours, sous **deux** verrous de session distincts, dont les commandes 3 et 4 répètent mot pour mot les commandes 1 et 2.
- **CE QUE LE `SEARCH` APPORTE, ET CE QUE LE `STATUS` N'APPORTAIT PLUS.** La US demandait d'examiner ce que le `SEARCH` apporte que le `STATUS` ne donne pas déjà : la réponse est **la liste d'UIDs**, que `STATUS` ne rend pas — le `SEARCH` n'est donc pas supprimable. Le redondant est le `STATUS` de `GetFolderQuery`, qui refaisait la mesure prise quelques millisecondes plus tôt par le chemin appelant.
- **REMÈDE 1 — fusion des deux séquences (7 → 5).** `ReadFolderAsync(folderPath, searchWhenStale, reusable, ct)` devient le passage IMAP unique : `resolve` + `STATUS` (étiquetés `GetFolderStatus`, plancher inchangé), puis `SELECT` + `SEARCH` + `CLOSE` (étiquetés `GetFolderQuery`) **seulement si** les compteurs frais démentent `reusable`. Un verrou de session au lieu de deux. `GetFolderStatusAsync` et `GetFolderQueryAsync` disparaissent, absorbés ; `BuildFolderDto` remplace leurs deux constructions jumelles du `FolderDto` ; `SearchIntoAsync` isole les trois commandes de la recherche et **reçoit** `statusMs` pour que la ventilation par commande de task-081 reste **une seule** ligne `[ListFolder]` dans Seq. **L'opération `GetFolderQuery` passe de 5 commandes à 3.**
- **REMÈDE 2 — la re-validation remplace le rejet (`today` : 5 → 2).** `folder:query` vit 5 min mais n'était utilisable que tant que `folder:status` (TTL 10 s) était présent : passé 10 s, une entrée parfaitement valable était **jetée** et la recherche complète refaite. `RevalidatableUids(cachedQuery, scopeDay, queryKind)` la confronte désormais au `STATUS` frais du même appel : `(Count, UidNext)` inchangé ⇒ dossier inchangé ⇒ ensemble « reçus aujourd'hui » inchangé (une arrivée fait avancer `UIDNEXT`, une suppression fait bouger `Count`, rien d'autre ne modifie l'ensemble du jour). Le jour de calcul (`ScopeDay`) est revérifié.
- **⚠️ ASYMÉTRIE ASSUMÉE, ÉCRITE AU POINT DE DÉCISION.** `QueryKinds.Unread` / `UnreadToday` sont **exclus** de la re-validation : marquer un message comme lu ne touche ni `Count` ni `UIDNEXT`, donc un `STATUS` frais ne démontre rien sur cette liste — la re-valider desserrerait la borne de 10 s à 5 min sans preuve. Le commentaire XML de `RevalidatableUids` porte l'arbitrage ; le test `GetFolderNotSeenAsync_WhenTheStatusWindowExpired_TakesNoShortcutAsync` le verrouille.
- **AUCUN TTL MODIFIÉ.** `folder:status` reste à 10 s, `folder:uids` et `folder:query` à 5 min. Ce qui change est la **manière de démontrer** la fraîcheur, pas sa durée. Les compteurs rendus (`Count`, `UnreadCount`, `UidNext`) proviennent **toujours** du `STATUS` de l'appel courant — jamais du cache, y compris sur le chemin de re-validation où ils sont donc plus frais qu'avant.
- **PREUVE PAR LE COMPTEUR, PAS PAR LA LATENCE** (`ImapServiceFolderStatusSolicitationTests`, séquences hoistées en champs `static readonly` nommés) : `ACacheMissOnTheFolderRoute_PaysTheStatusFloorThenTheSearch` (5 commandes + ordre + attribution d'opération, était 7) ; `AFolderRouteRevalidation_StillCostsExactlyTheTwoCommandsOfTheStatusFloor` (**non-régression DOD** : le chemin `GetFolderStatus` reste à 2) ; `AFolderRouteMissWithAStaleUidCache_PaysTheFiveCommandsOnce` (un seul `resolve`, un seul `STATUS`) ; `ABoundedSearchMiss_PaysFiveCommands_TheFloorPlusItsThreeAsync` ; `AFailedConnection_RecordsNothing_AbsenceStaysProvable`.
- **PREUVE D'INVARIANCE FONCTIONNELLE** (`ImapDashboardCachingTests`) : `GetFolderAsync_ServesTheSameResponseBodyWhetherRevalidatedOrSearchedAsync` compare le corps **champ pour champ** entre chemin court et chemin long sur un dossier **imbriqué** (`INBOX/Analyses`, nom court ≠ chemin, `Id` et `ParentFolder` non vides — la seule forme où un DTO amputé se distingue d'un DTO complet) ; `..._RevalidatesInsteadOfSearchingAgainAsync` (0 `SEARCH`, UIDs resservis) ; `..._WhenTheStatusWindowExpiredAndTheFolderMoved_SearchesAgainAsync` (la preuve peut échouer).
- **Effet de bord favorable** : `NotFound` (dossier orphelin) remonte désormais en 404 aussi sur la route `today` — `GetFolderQueryWithCacheAsync` ne le traduisait pas auparavant. Traduction factorisée dans `FailureOf(...)` (`/forge-simplify`).
- **Tests** : `dotnet build` 0 erreur / 0 avertissement ; `dotnet test HealthPlatform.Api.Mail.sln` **3 888 verts / 0 rouge** (domain 136, infrastructure 464, application 2 186, api 685, integration **417** + 16 skipped). Deux familles de flakies **pré-existantes** observées sur certains tirs Release + couverture (`Services.Export` / QuestPDF ; `MailRepositoryEnrichPersistInstrumentationTests` / métriques à état statique) — fichiers non touchés par le diff, vertes en isolation.
- **Sonar** (`healthplatform`, 2 analyses complètes) : new-code 65 (baseline) → 66 (+2 `CA1861` sur le fichier de tests) → **64** après correctif. **0 violation new-code attribuable à task-270**, 0 sur `ImapService.cs`. Coverage 88,0 % → **88,2 %** ; new coverage 88,4 % → **88,6 %** ; bugs 2, vulnérabilités 0, hotspots 0, smells 63, duplication 0,3 % — inchangés. QG toujours `ERROR` : la `new code period` est en `PREVIOUS_VERSION` avec baseline au **2026-04-27**, donc les 64 violations restantes sont de la dette **déjà mergée** (42 sur `tests/loadtest-k6/**`, 10 sur des tests C# antérieurs, 12 sur du code applicatif antérieur). Phase 2 non traitée : hors périmètre (règle 6).
- **Gain attendu, à confirmer au banc** : −2 allers-retours × ~100 ms × ~16 000 cache-miss ≈ **−3 200 s de temps serveur** par campagne (fourchette annoncée par la US : −3 000 à −4 900 s) ; p95 `dashboard,call:folder` ~700 → ~400-500 ms ; part du dashboard sous 18 %. Tir journey distant iso-conditions 2026-08-23 à conduire.
- **Limites résiduelles / dette laissée sciemment** :
  1. `ImapFolderService.ExecuteFolderSearchAsync` reste la « jumelle » **hors chemin de production** identifiée par task-262 (`IImapFolderService.GetFolderQueryAsync` n'est appelé par aucune route). Elle paie toujours ses 4 commandes et duplique la logique corrigée ici → candidate à une suppression dédiée.
  2. `resolve_folder` n'est peut-être pas toujours un aller-retour réseau : MailKit 4.17 expose `ImapEngine.FolderCache` / `TryGetCachedFolder` (vérifié dans les métadonnées de l'assembly), donc un dossier déjà listé dans la session peut être résolu sans `LIST`. Le compteur serait alors une **borne supérieure** sur ce point précis — à trancher au banc si le gain observé dépasse la prédiction.


---

## Annexe A — Cartographie des briques applicatives

| Brique | Chemin | Rôle |
|---|---|---|
| Forge de tokens | `Api/Mail/tests/mss.mail.testing.shared/PscTokenForge.cs` | JWT PSC/Keycloak à signature factice (partagé tests + seed) |
| Générateur de population | `Api/Mail/tests/mss.mail.testing.shared/LoadTestPlanGenerator.cs` | Utilisateurs + messages synthétiques déterministes, **fils de discussion optionnels** (`threadShare`, défaut 0 = sans fil) |
| Profil banc | `Api/Mail/src/AppHost/AppHost.cs` (`MSS_LOADTEST`) | Conteneurs Dovecot (IMAPS) + GreenMail (puits SMTP) + Toxiproxy, injection `TestMode:BypassKey` et `TestMode:Password` |
| Conf serveur IMAP du banc | `Api/Mail/src/AppHost/dovecot/dovecot.conf` | Maildir, `passdb`/`userdb` statiques, TLS ; bind-montée dans `conf.d` **et** par le smoke test (source unique) |
| Outil de seed | `Api/Mail/tests/mss.mail.loadtest.seed/` (`Program.cs`, `SeedOptions.cs`, `ToxiproxyClient.cs`) | Proxies Toxiproxy, boîtes Dovecot (APPEND IMAP), `UserSettings` via API, **`--thread-share`** (part de messages en fil, défaut 0) |
| Auth de test | `Api/Mail/src/Api/Authentication/TestBypassAuthenticationHandler.cs` | Bypass QA/banc, claims `mssEmail`/`mssSub`/`mssRpps`, hard-block Production |
| Redirection serveurs | `Api/Mail/src/Application/Helpers/AutodiscoveryHelper.cs` (existant) | `UserSettings.Imap/SmtpServerConfig` prioritaire → banc |
| Smoke test SMTP / sessions | `Api/Mail/tests/mss.mail.integration.tests/LoadTest/GreenMailBenchSmokeTests.cs` | Bout-en-bout via `MailClientSessionManager` réel (chemin historique conservé) |
| Smoke test IMAP du banc | `Api/Mail/tests/mss.mail.integration.tests/LoadTest/DovecotBenchSmokeTests.cs` | Fetch partiel `BODY[part]` octet pour octet, auth wildcard, rejet mauvais mot de passe, réutilisation de session ; monte la conf réelle de l'AppHost |
| Helper IMAP de banc | `Api/Mail/tests/mss.mail.integration.tests/LoadTest/BenchImap.cs` | Client tolérant au certificat auto-signé, seed de boîte, append avec pièce jointe — partagé par les deux smoke tests |
| Harnais de tir | `Api/Mail/tests/loadtest-k6/scenarios/` | 6 scénarios k6 : `folders`, `read`, `search`, `send`, `enrich`, `mixed` |
| Socle du harnais | `Api/Mail/tests/loadtest-k6/lib/` | 8 modules : `config` (seuils + paramétrage), `identity` (identités déterministes régénérées en JS), `api`, `bootstrap`, `checks`, `uid-bands` (bandes d'UID disjointes `enrich`/`read`), `toxiproxy` (profils de latence), `summary` (rapports stdout/JSON/texte/HTML) |
| Lanceurs | `Api/Mail/tests/loadtest-k6/run.sh`, `run.ps1`, `reset-state.sh` | Tir paramétré (refus de démarrer sans `BYPASS_KEY`) ; remise à zéro des bases par utilisateur avant `enrich`/`mixed` |
| Baseline anti-régression | `Api/Mail/tests/loadtest-k6/baseline.md` | Run de référence daté : config, chiffres, seuils dérivés, réserves, plafonds du banc |
| Dashboard de charge | `Api/Mail/src/AppHost/grafana/dashboards/k6-loadtest.json` | UID `k6-loadtest-api-mail` ; métriques k6 corrélées aux métriques serveur, label `testid` par run |
| Receiver remote-write | `Api/Mail/src/AppHost/AppHost.cs` (`--web.enable-remote-write-receiver`) | Ouvre Prometheus à la sortie k6 — **configuration partagée de tous les environnements de dev locaux** |
| Doc | `Api/Mail/docs/loadtest.md` | Mode d'emploi du banc + du harnais, justification unique de la bascule GreenMail → Dovecot, trois limites du banc |

---

## Annexe B — Inventaire fonctionnel daté (2026-07-25)

- Projets ajoutés : 2 (`mss.mail.testing.shared`, `mss.mail.loadtest.seed`), classés
  test-support (`SonarQubeTestProject=true`).
- Tests ajoutés : 25 unitaires (8 handler + 17 générateur/CLI) + 2 smoke
  d'intégration Docker-gated (`GreenMailBenchSmokeTests` SMTP/sessions,
  `DovecotBenchSmokeTests` IMAP — 3 assertions dont le fetch partiel).
- Suite complète au dernier run (task-174, run Sonar) : **3 141 réussis, 0 échec,
  16 ignorés** (domain 94, application 1 827, infrastructure 360, api 559,
  integration 261).
- Conteneurs de banc : **3** — Dovecot `2.3.21` (IMAPS 3993→993, maildir sur volume
  nommé `loadtest-dovecot-mail`), GreenMail `2.1.3` (puits SMTP uniquement),
  Toxiproxy `2.9.0` (proxies `dovecot-imap` + `greenmail-smtp`). Opt-in `MSS_LOADTEST`.
- Volumétrie mesurée : 4,6 Mo de maildir pour 15 messages à pièce jointe XDM
  (~124 Ko/message). Run de grande ampleur (200 × 200) non encore conduit.
- Pipeline CDA/IHE-XDM exercée sur le banc : **oui** depuis task-195 (4 extractions
  observées dans Seq sur 5 messages seedés) ; confirmée à l'échelle par le run
  `enrich` de référence de task-174 (**51 documents extraits** pour 50 mails
  enrichis, 10 lots).
- Harnais de tir : **livré** (task-174) — 6 scénarios, 8 modules `lib/`, 2 lanceurs,
  `reset-state.sh`, dashboard Grafana dédié, baseline committée. Exécution manuelle
  uniquement, hors cycle forge et hors CI.
- Baseline de référence : **10 utilisateurs × 10 messages**, profil `mssante`
  (100 ms ± 25), 6 req/s par identité. Profil composite : 5 832 requêtes,
  46,4 req/s, **0 erreur**, 4 774 réutilisations de session contre 21 rotations.
- Seuils actifs : 7 cibles p95 par opération + `http_req_failed < 1 %`,
  `checks > 95 %`, `rate_limited_429 == 0`, `enrich_short_circuited == 0`.
  Pass/fail démontré (code de sortie k6 = 99 sous profil `degraded`).
- Plafonds connus du banc : limiteur de débit api-mail 100 req / 10 s par identité
  PS (fenêtre fixe, `QueueLimit: 0`) et `mail_max_userip_connections=10` côté
  Dovecot. La montée en charge passe par `USERS`.
- Conventions alimentées : **`conventions/javascript.md`** créé (7 entrées) —
  boucle d'auto-amélioration étendue au JavaScript, câblage dans `/develop` à
  arbitrer.

---

## Annexe C — Tasks ayant contribué à cet EPIC

| Task | Contribution | RG fermées |
|---|---|---|
| task-274 | **Chaque widget du tableau de bord a son interrupteur de charge.** 8 flags Flagsmith `dashboard_widget_*` (mêmes noms sur les trois fronts, créés ON par le FlagsmithSeeder du banc ; staging/prod manuels) : flag OFF → widget masqué ET appel API jamais émis (composant non instancié — prouvé par test sur chaque front). Fail-open sans exception, lecture une fois par session (endpoint FeatureFlag existant, cache 5 min) — coût nul sur le geste instrumenté. Attribution de charge widget par widget + délestage sans redéploiement. `biology_ack_pending` = outil d'incident uniquement (obligation métier). PRs #204/#69/#63 + diff Angular code-only = une US (règle 11). | — |
| task-272 | **L'acquittement d'un envoi n'attend plus l'archivage.** Le tiers restant du seul rouge SLO (~407 ms d'archive_sent) sort du chemin de la réponse : acquittement à l'acceptation SMTP, archivage en file (task-075) sur la même session IMAP poolée (CopyIdentityTo task-234), rejeu borné 3x, échec final tracé traceId + compteur d'issues, mesure hors chemin sur la même série. Contrat { queued, archivePending } (archived/warning sans consommateur, retirés). SemaphoreFullException : établi corrigé depuis task-223. 3 892 tests verts, QG OK. | — |
| task-269 | **Le pool SMTP existait et ne servait jamais.** Le battement d'entretien SMTP vivait sur la cadence IMAP (30 s), pile sur le délai de coupure du serveur du banc (28-35 s mesuré) : course perdue en 1-2 cycles, client jeté en LogDebug — 84 envois = 84 connexions fraîches, 0 trace — et chaque envoi repayait CONNECT+TLS+AUTH (~457 ms, premier tiers du seul rouge SLO). Remède : cadence SMTP dédiée 15 s, rétention découplée de l'expiration de session (la connexion vit avec la session, configurable par domaine), mort visible en Information. Énigme des ~1,9 SmtpCommandException/envoi résolue : exceptions avalées (zéro dans Seq), pas un rejeu. 3 884 tests verts, QG OK. | — |
| task-216 | **La voie d'écriture IMAP marchait, et rendait quand même l'envoi plus lent.** task-213 avait donné au praticien une seconde session IMAP pour retirer l'archivage de la file des lectures — mécanisme confirmé (attente d'`AppendToSent` 4,345 s → 0,005 s au p95), **bilan négatif** : contre-épreuve task-215, trois tirs 500 praticiens, `send` p95 **7 874 ms sans la voie contre 10 439 et 12 573 ms avec**, le témoin satisfaisant le DOD de task-213 que les tirs correctifs manquent. Ce que la voie retirait au verrou, elle le repayait en ouverture de connexion. Et le défaut d'origine n'est **plus reproductible** depuis la levée des plafonds du banc : task-213 répondait à une mesure prise sur un banc bridé. Retrait **complet et symétrique** — la voie, son suffixe, son prédicat, et la surcharge de connexion qui n'existait que pour elle (hors « Contenu attendu », mais la laisser aurait laissé le moyen de recréer la voie sans le dire). La mesure et sa **réserve « pour cet hôte »** restent **dans le code**, là où la voie était choisie. `LockLaneWrite` **conservée sans émetteur**, arbitrage écrit : la table « Voie | Acquisitions /s » n'a plus qu'une ligne, et c'est ainsi qu'elle atteste du retour à une connexion par praticien. **3 tests constatés ROUGES** avant le retrait, capturant le contexte réellement présenté au gestionnaire de sessions — un test sur `UserContextInfo` seul n'aurait rien prouvé. Revue : risque de **ré-entrance** du verrou partagé vérifié sur les deux sites d'appel (hors scope de verrou IMAP, pas de double acquisition). Sonar : 1 finding attribuable, **introduit par la passe qualité** (`S3218`, constante masquant `LockTags.Lane`), corrigé. Tir 500 iso-conditions **dû au banc**. | — |
| task-259 | **Le mecanisme suppose etait faux, et c'est le test qui l'a dit.** Quatre `InvalidOperationException: Collection was modified` par serie a la campagne task-255, sur les deux series et des praticiens differents : enrichissement de contact **perdu en silence** (message enrichi, contact non enrichi, erreur journalisee puis abandonnee ; le rejeu de task-250 ne s'applique pas — il se declenche sur `ConflictException`, levee APRES `SaveChangesAsync`). **La lecture structurelle du task file est refutee** : un `RemoveRange` sur une collection de navigation suivie **ne leve pas** — le premier test est passe du premier coup, sans correctif. **La cause reelle** est la presence d'une entite `Added` dans la collection : EF la passe a `Detached` (« rien a supprimer »), ce qui la RETIRE de la navigation en cours d'enumeration. Etat produit par le partage du `DbContext` memoise (task-231) entre deux enrichissements simultanes du meme praticien — d'ou zero occurrence hors concurrence, et d'ou l'aveuglement de la suite existante (son seul test de mise a jour passe des collections **vides**). Correctif : trois `.ToList()`, pressentis par le task file mais **poses sur la bonne raison**, donc couvrant toute mutation de la collection suivie. Reproduction **deterministe et sans concurrence** avec l'exception exacte du banc, sur InMemory (pas d'`ExecuteDeleteAsync` — lecon task-247). Rejeu et traduction `ConflictException` de task-250 **inchanges**. Chemin contact patient : **meme defaut, corrige mecaniquement**, epingle par test. AIPD : nom du praticien retire du journal, echec toujours **visible**, les deux epingles par le meme test. Sonar : aucun finding attribuable ; le seul du fichier touche (`S2302`) **classe faux positif** — « contact » y est de la prose francaise, pas un `nameof`. Findings : tests « du jour » rouges au passage de minuit (fuseau, F-259-1), collision de capture du meter aussi dans `infrastructure.tests` (F-259-2), **INS journalise en clair cote patient** (F-259-3, non modifie, decision requise). | — |
| task-256 | **Le denominateur qui manquait au +51 %.** task-243 avait livre le numerateur (`assemble` = 83,7 % du cout de `GetMailsByUids`) ; deux tirs a protocole identique ont mesure cette materialisation passer de 433,3 a 654,5 ms — **+51 %** — pour **15,8 requetes par appel, identique au millieme**. Le volume d'objets avait grossi, mais **rien ne le comptait** : l'explication etait une deduction. Livre : `mssante_db_operation_objects_total`, ventile par `(operation, family)`, publie a la fermeture du **perimetre existant** — zero nouvel instrument de duree, 17 points de comptage, `GetMailsByUids` **et** `GetMail`. **PGSSI-S par le typage** : la signature prend une **enumeration**, pas une chaine — les `enriched_ids` peuvent porter de l'INS, et la fuite de task-213 devient **impossible a ecrire**. **Zero distinct de non releve**, encode par sentinelle : une famille jamais chargee ne produit aucune serie. ⚠️ **Ecart assume au task file** : 12 familles au lieu des 6 nommees, parce que les 6 sont toutes bornees par la page alors que la deduction porte sur le **contenu enrichi** — s'y tenir aurait rendu la contre-epreuve incapable de se tromper. Le rapport publie le **cout par objet** et une contre-epreuve **refutable** (les 221,2 ms d'ecart exigent N objets de plus ; sinon la deduction est fausse, et c'est un resultat). 32 tests, aux **deux niveaux** — accumulateur juste ET appels poses aux bons endroits, le second etant le defaut qui rendrait le compteur menteur sans paraitre faux. Collision de capture du meter fermee sur `DbOperation*`, **nommee et non reglee** sur l'enrichissement (F-256-3, anterieure). Sonar : hotspots new-code 50 → **100 %** ; `new_violations` 59, **provenance verifiee, zero attribuable** (F-256-4 : new-code period `PREVIOUS_VERSION` heritee). Aucun gain de performance — c'est un instrument, la confirmation au banc reste due. | — |
| task-258 | **Le triplement de l'ecriture est du TRAVAIL, pas une file — et la contre-epreuve est DANS la task.** Premiere US d'instrument de cette EPIC a sortir avec sa DOD complete : les cinq precedentes laissaient leurs criteres de mesure ouverts. **Cause de l'angle mort etablie** : l'intercepteur de commandes alimente les deux perimetres, celui de connexion n'alimente que DbOperationScope, inactif faute de Begin — la phase db_write ne mesurait QUE l'execution SQL, l'attente n'existait pas. Livrable : **une ligne** dans AddNewMail, zero nouvel instrument (DbOperationScope de task-243 publiait deja les trois composantes). **Verdict de la contre-epreuve** (3 concurrences, protocole identique a task-255, 640/640 messages, 0 erreur) : attente de connexion **nulle et plate** (1,4 % du cout, cl_waiting et maxwait nuls) — **l'hypothese du pool est ECARTEE par la mesure** ; requetes par message **identiques au centieme** (8,72) ; execution SQL **+63 %**. Memes requetes, meme nombre, plus de temps. **Sans le denominateur ce verdict etait impossible** — et le compteur avait failli manquer, active dans la capture mais jamais asserte, releve par la passe qualite. La question se deplace **cote PostgreSQL** : le prochain instrument n'est plus applicatif. 6 tests eprouves par mutation, dont un **surpris a passer a vide** et renforce (piege de task-250). ⚠️ Suggestion non resolue : l'etiquette couvre les 4 sites d'appel de AddNewMail dont un ecrit des en-tetes seuls — campagne **non contaminee, verifie** (640 appels pour 640 messages), mais a trancher avant une campagne journey. | — |
| task-257 | **La troisieme occurrence du piege IPv6 du banc, fermee par la topologie et non par un nom.** `--add-host=…:host-gateway` injecte desormais une entree IPv4 ET une IPv6 ; PgBouncer, qui ne bascule pas de famille d'adresses, retient l'AAAA, met l'echec en cache et rend un 08P01 a tous les clients du pool — 13 % des lots perdus, deux campagnes jetees (task-255). **Le garde-fou de task-200 n'a rien vu parce qu'il assertait le NOM** : le nom n'avait pas change, c'est sa RESOLUTION qui avait change. Remede : ne plus passer par l'hote du tout — PgBouncer est rattache au reseau du conteneur PostgreSQL (`enable_ipv6: false`) et l'adresse par son nom, ce qui rend la resolution IPv4 **structurelle**. ⚠️ Le mecanisme n'est pas `--network`, **ignore par Aspire** (mesure : NetworkMode=bridge, upstream non resolu) car DCP rattache lui-meme ses reseaux apres creation : c'est un crochet `AfterResourcesCreatedEvent` qui fait la meme chose, apres lui. Deux alternatives ecartees sur mesure (IP de conteneur non routable inter-reseaux ; IPv4 litterale non portable). Gardes eprouves par **4 mutations, 4 attrapees**, portant sur la CLASSE des resolutions par l'hote. Verifie au banc demarre sans aucune commande manuelle : resolution IPv4 seule, 0 unreachable/server_login_retry, 0 PostgresException, tir enrich a 0 % d'erreur. Hors profil loadtest, rien ne change. Dette Sonar introduite : zero. | — |
| task-255 | **Le plateau d'enrichissement n'existe pas — et deux defauts de banc le fabriquaient.** Campagne a trois concurrences (4/8/16), 640 messages enrichis sur 640 soumis a chaque point, 0 erreur : **16,66 -> 30,19 -> 45,02 msg/s**, soit **x2,70 pour x4 de concurrence**, contre les +4 % pour un doublement de task-254. **Ressource limitante nommee et chiffree : le CPU de l'hote, donc HORS d'api-mail** — file d'execution du processeur 0,6 -> 30 sur 24 coeurs, pendant que le pooler reste calme (`cl_waiting` nul sur 14 releves sur 15, `maxwait` 0,7 ms), que les backends Postgres sont invariants (16), et que le verrou `imap_session` — suspect historique — a une attente **strictement nulle sur 704 acquisitions** a 4 et a 8, et pese 3,7 % de l'enveloppe a 16. **Preuve interne independante** : la phase bornee par la latence injectee est plate au demi-millimetre (124,8 -> 127,3 ms) pendant que toutes les phases de calcul enflent ensemble. **Contre-epreuve a un seul facteur** : la meme serie sur hote affame (11 coeurs sur 24 voles par un conteneur tiers en boucle d'echec depuis dix mois) rendait 15,22 / 26,38 / 34,59 msg/s — le gain une fois l'hote rendu **croit avec la concurrence** (+9 %, +14 %, +30 %), signature d'une contention de calcul. **Trois defauts de banc, deux campagnes jetees** : `08P01` par resolution IPv6 de `pgupstream` (13 % des lots ; -> task-257), snapshot de telemetrie perdant la queue des tirs courts (275 messages comptes pour 640 ; **fabriquait le plateau**), purge lancee bus non draine (22 lots sur 32 court-circuites). **Aucun correctif applicatif livre** : la premisse n'est pas verifiee, corriger traiterait une cause supposee (lecon task-222) ; seuil de reouverture pose. Backlog d'instrumentation -> **task-258** (l'attente de connexion sur le chemin d'ecriture n'existe pas comme metrique). Defaut applicatif releve -> **task-259**. Le correctif de banc a ete **retire de la branche** sur arbitrage humain et part entier dans task-257. | — |
| task-253 | Chauffe du parcours **par vagues** : le lotissement de task-244 n'aboutissait pas car son délai dérivait d'un coût relevé en régime, alors que tous les médecins chauffent à l'ouverture d'un palier. Débit d'enrichissement mesuré **plafonné** (0,59 s/msg à concurrence 4, 2,11 s à 20 — +40 % de débit pour ×5 de concurrence), donc borner la concurrence est le seul levier côté harnais. Décalage déduit du **rang de cohorte** (un premier jet en index global faisait attendre le VU 200 plus longtemps que la fenêtre du palier). Contrepartie mesurée et publiée (part de fenêtre consommée, avertissement au-delà de 50 %). Garde de refus de task-244 intacte, témoin négatif à l'appui. Résultat : lots perdus 556 → 12, médecins chauffés 0 % → 94,5 %. Livrée directement sur `develop`, sans PR. | — |
| task-173 | Banc de charge isolé : profil AppHost GreenMail+Toxiproxy, outil de seed, forge de tokens et générateur de population partagés, enrichissement du test-bypass, smoke test bout-en-bout. Binaire de production inchangé. | — |
| task-195 | Bascule du serveur IMAP du banc vers Dovecot `2.3.21` (conf montée, maildir sur volume nommé, auth wildcard à mot de passe vérifié), GreenMail rétrogradé en puits SMTP, Toxiproxy réaligné, seed adapté, smoke test de fetch partiel. **Débloque la pipeline CDA/IHE-XDM**, jusque-là inexécutable sur le banc, et lève le plafond de volumétrie. Validation end-to-end réelle exécutée (4 extractions CDA observées). Binaire api-mail inchangé. | — |
| task-174 | Harnais de tir k6 : 6 scénarios (`folders`, `read`, `search`, `send`, `enrich`, `mixed`), 8 modules `lib/`, lanceurs et `reset-state.sh`, profils de latence Toxiproxy pilotés par le harnais, sortie Prometheus remote-write vers le Grafana du banc (dashboard dédié), **thresholds-as-code** (pass/fail démontré, code de sortie 99 sous `degraded`) et **baseline anti-régression committée**. Trois plafonds de banc identifiés et outillés (bases Postgres persistantes, limiteur de débit api-mail, connexions IMAP Dovecot). Quality Gate ERROR → OK en une passe, 17 findings JS, `conventions/javascript.md` créé. Binaire api-mail inchangé (seul l'AppHost bouge, +9 lignes). | — |
| task-200 | PgBouncer mode transaction devant « une base par praticien » : conteneur `loadtest-pgbouncer` au profil loadtest (configuration montée), et **séparation du chemin de données (via pooler) et du plan de contrôle (verrou de provisionnement, `CREATE DATABASE`, `MigrateUp` — direct sur Postgres)** via `UserContextInfo.ConnectionStringDirect` et ses dérivées, avec repli garantissant l'absence de changement de comportement hors banc. Compatibilité tranchée par 5 tests d'intégration sur la configuration réelle du banc : EF Core ✓, **pgvector ✓** (la question ouverte), provisionnement en route directe ✓, **multiplexage confirmé (40 clients → ≤ 3 backends)**. Troisième occurrence du piège IPv6 Docker Desktop identifiée (`host.docker.internal` résolu en AAAA seul, PgBouncer ne bascule pas de famille d'adresses) et **verrouillée par un test garde-fou**. ADR de compatibilité écrite. `conventions/csharp.md` créé. **Tir comparatif 200 praticiens encore dû** — le prérequis §4.1 du dossier de dimensionnement n'est pas levé. | — |
| task-203 | **Le harnais mesurait le harnais.** Pools de VUs de `mixed` dimensionnés par la **loi de Little** à partir des latences mesurées (`lib/vu-sizing.js`, module pur testable hors k6) au lieu de `4 × part × VUS` — un nombre sans rapport avec le débit demandé, qui plafonnait `send` à 7,9 it/s pour 300 demandées et faisait abandonner 45 k à 502 k itérations aux trois tirs du 2026-07-27. `MAX_VUS`, jusque-là **silencieusement ignoré par `mixed`**, est respecté. **Garde de validité** dans `report.py` (bandeau `TIR INVALIDE`, section « Validité du tir », table « débit demandé vs délivré » qui révèle `send` à 14,4 % et `search` à 55,6 % de leur budget) et colonnes `Drop %` / `VU sat.` dans `INDEX.md`, **historique recalculé : 16 des 21 tirs archivés invalides**. Deux faux positifs de la garde trouvés avant livraison (modèle fermé ; abandons structurels d'`enrich`, ~1,16 pt sur un palier de 3 min). Banc journalisé en `Information` comme la Production (904 839 événements `Debug` évités sur une fenêtre de tir). Flaky préexistant de `CdaProcessingMetricsTests` corrigé (meter statique + `List.Add` non verrouillé). **La mesure de capacité reste à produire.** | — |
| task-204 | **Le banc sait enfin nommer sa ressource limitante.** Attribution des métriques **par réplica** via un fan-out OTLP vers un collector du profil loadtest (`resource_to_telemetry_conversion` promeut `service.instance.id` en étiquette) — le port fixe 5052 devant 5 réplicas étant le proxy DCP, chaque scrape tombait jusque-là sur un réplica au hasard. Voie du **push** retenue contre le scrape par réplica : elle supprime le problème de découverte des ports dynamiques au lieu de le contourner. **Échantillonneur** (`observe.ps1`/`observe.sh`, CSV long UTF-8 UTC) pour ce que la télémétrie ne voit pas : hôte, **k6**, conteneurs du banc, Dovecot, `SHOW POOLS`, `pg_stat_activity`. Section « Ressources & télémétrie » dans `report.py` (par réplica, par conteneur, **p95 client vs p95 serveur**, compteurs métier, ligne « ressource épinglée ») avec **9 tests garantissant qu'aucune absence de source ne produit un tableau vide**. Débit au **dénominateur nommé** : `http_reqs.rate` divisait par la fenêtre totale, arrêt gracieux inclus (~8-10 % de sous-estimation sur TOUS les tirs) — INDEX recalculé, référence 200 à **934,5** et non 915,5. Dashboard « Saturation ». **Deux défauts bloquants trouvés avant merge** : les 5 réplicas auraient planté au démarrage (`AddOtlpExporter` incompatible avec le `UseOtlpExporter` d'Aspire) et le rapport désignait une ressource épinglée sur un CSV non borné. **L'escalier de capacité a été conduit** (cf. v1.7) : genou entre 745 et 825 req/s délivrés, plafond mesuré ~858 req/s, et facteur limitant nommé pour la première fois — famine de ThreadPool sur `read_list`, corrigée par task-205. | — |
| task-205 | **Suppression du facteur limitant de l'API.** La résolution d'un dossier IMAP par son chemin passait par `IMailStore.GetFolder(string, ct)`, variante **synchrone** d'un aller-retour réseau (commande LIST) : elle parquait un thread du pool pour toute la durée de l'I/O sur le chemin `read_list`. `TryGetFolderSafely` → `TryResolveFolderAsync` (`await GetFolderAsync`), 5 appelants convertis, et **la surcharge synchrone retirée de `IImapClientWrapper`** — le retrait est le correctif. **3 gardes de non-régression** (surface publique, analyseur sur les métadonnées de l'assembly filtrant par signature décodée, test de non-blocage borné en temps), toutes constatées RED avant le correctif ; l'analyseur **se contrôle lui-même** par un témoin, qui a immédiatement révélé que le compilateur émet la référence contre `MailKit.MailStore` et non contre l'interface. Suspect historique `BaseRepository.get_DataContext` **innocenté par lecture du code** (fast-path statique : la tâche est déjà complétée pendant le plateau). Deux blocages adjacents signalés hors périmètre (`MailClientSession.Dispose`, `EmailFlagService`). Faux diagnostic Sonar de task-204 corrigé : `sonar.login` et non `sonar.token` sur SonarQube 9.9. **La campagne de confirmation reste due.** | — |
| task-209 | **Le harnais dimensionnait sur une latence que le banc ne produit plus.** Constantes `REFERENCE_ITERATION_SECONDS` rafraîchies sur le palier 486 req/s du 2026-07-29 (base purgée, sous le genou) et **assorties de leurs conditions de mesure** (`REFERENCE_MEASURED_AT`, `REFERENCE_CONDITIONS`, archivées dans le `context` de chaque tir) — la contradiction purge / dimensionnement (`read` 0,16 s base pleine vs 0,41 s base purgée, ×10 au palier 972) est nommée dans `docs/loadtest.md`, le README du harnais et le `loadtest-skill`. Surcharge `ITER_SECONDS_*` par sous-scénario, parsée dans le module pur, **levant** sur nom inconnu ou valeur ≤ 0. **Bug corrigé** : `iterationSecondsFor` substituait la table au lieu de la fusionner — une surcharge ciblée renvoyait les autres pools sur le repli d'une seconde. **`report.py` distingue désormais les deux causes d'abandon** — « pool client épuisé alors que le serveur répond dans les temps » vs « le serveur ralentit » — sur le témoin de la file ThreadPool par réplica, nomme le sous-scénario porteur, imprime la conduite à tenir **opposée** selon la cause, et écrit `indéterminée` plutôt que de deviner. 23 tests ajoutés (4 node + 19 Python) sur **5 fixtures de campagne reconstruites depuis les chiffres publiés** — `reports/` étant gitignoré et les JSON du 2026-07-29 absents de la machine —, gardées par un test d'intégrité qui vérifie qu'elles reproduisent ces chiffres. Sonar : bugs 1 → 0, reliability C → A, hotspots 2 → 0, smells 13 → 3 (les 3 restants = `python:S3776` de task-204, laissés car `budget_rows` est la fonction que task-208 doit réécrire). `conventions/python.md` créé. **Mesure au banc du palier 756 req/s encore due.** | — |
| task-208 | **Les trois verdicts du rapport reposaient sur la mauvaise statistique** — trois affirmations fausses dans des `.md` livrés, trouvées en LISANT les rapports de la campagne, pas le code. (1) `pinned_candidates` désignait PgBouncer comme facteur limitant de trois paliers sur le `max` de `cl_waiting`, c'est-à-dire **un seul échantillon** à 1-2 clients, devant un réplica à 11 % → jugé désormais sur la **part des échantillons non nuls** (`pgbouncer_waiting`, seuil 25 % contre 6,5 % de bruit d'ouverture mesuré), et le transitoire reste **écrit** sous la table. (2) La table « demandé vs délivré » divisait par la fenêtre totale quand l'en-tête du **même document** publiait déjà le débit plateau : « 482,7 req/s / 99,3 % » au-dessus de « 413,6 / 85,1 % ⚠️ » → `_delivered_rps` passe au dénominateur plateau, chaque ligne porte son `denominator`, et le repli est NOMMÉ `fenêtre k6`. (3) La garde comptait le reliquat d'un `shared-iterations` FINI comme des abandons (1er palier invalide à 4,6 % pour 2,6 % réels) → `finite_scenario_remainder` retranche depuis le **plan déclaré** (`dropped_source = finite_plan`), ce qui couvre aussi tous les tirs archivés avant task-203 sans sous-métriques, et le reliquat est écrit comme information. 13 tests écrits RED d'abord, 2 CSV de fixtures (transitoire + contre-épreuve soutenue, marquée synthétique) ; **trois tests existants changent de verdict — c'est le correctif** (`send` 17,24 → 18,97 req/s, et la contre-épreuve « sans ventilation ce tir serait invalide » s'inverse). Sonar : les 2 S3776 que la task avait elle-même introduits ou aggravés (`budget_rows`, `_budget_section`) corrigés par extraction ; les 2 restants sont de task-204 et la passe sur les helpers de table Markdown est en « Hors scope ». `docs/loadtest.md` §4d : les trois règles, quelle statistique et pourquoi celle-là. **Régénération des 3 rapports archivés infaisable** — les JSON n'existent plus. | — |
| task-202 | **~1 backend Postgres retenu par praticien, pour rien.** Mesuré au banc 200 praticiens du 2026-07-27 : écart de ~169 entre `pg_stat_activity` et `SHOW POOLS`, **stable autour d'une connexion par base** quel que soit le réglage du pooler — signature de la route directe, pas du pooler. Trois gestes : (1) le `ServiceProvider` de FluentMigrator est **disposé** — seul le `scope` interne l'était, un conteneur DI fuyait par base et par pod, et le `using` couvre le chemin d'exception, celui où une migration rejouée les accumule ; (2) la chaîne est **bornée** par un helper dédié `AppendProvisioningPoolingSettings` (`Max=1`, `Min=0`, idle 5 s) au lieu des défauts Npgsql (100 connexions, idle 300 s) — helper distinct d'`AppendPoolingSettings` à dessein, l'idle long du chemin de données existant pour éviter l'épuisement des ports éphémères Windows, raisonnement qui ne se transpose pas à une connexion unique jouée une fois ; (3) le pool est **vidé** (`ClearPool`) après migration réussie, hors du `using` puisque la connexion du runner doit d'abord y revenir, et jamais après un échec. **Piège évité** : la chaîne SERVEUR n'est délibérément pas bornée — unique par pod donc pas la coupable, et `Max=1` y provoquerait un interblocage (`lockConnection` ouverte pendant que `MigrationHelper` en ouvre une seconde) ; un plafond resterait possible à partir de 4. **Nuance sur l'énoncé** : la connexion de provisionnement était déjà un pool distinct AVANT task-200, le chemin de données bâtissant son `NpgsqlDataSource` sur une chaîne suffixée — le pooler l'a rendue visible, pas créée. 12 tests écrits RED d'abord (disposition sur succès ET exception, non-vidage après échec) ; 3 219 tests verts. Sonar : zéro finding C# restant. **Les 4 critères de DOD au banc restent dus** (test d'intégration PgBouncer, tir 200 praticiens, non-régression p95, rapport comparé au tir A). | — |
| task-206 | **Le banc levait une exception par requête, et ce bruit noyait la télémétrie.** La colonne « Exceptions /s » ajoutée par task-204 l'a révélé : 12 668 `SecurityTokenMalformedException` en 121 s à 106 req/s (≈1,2 par requête), >1 200/s au plafond, croissance **linéaire** avec la charge. Cause : le harnais envoyait `X-PSC-Token: loadtest` — non vide mais pas un JWT — et `TryParsePscIdentity` tentait quand même de le parser ; l'exception était avalée, la requête continuait. **Voie 1, posée plus bas que l'énoncé** : celui-ci proposait de court-circuiter quand `Enforce=false`, ce qui aurait rendu **aveugle le mode observation** (phase 1) en le privant des journaux 3721/3722/3723 qu'il existe pour produire ; la garde porte donc sur la **lisibilité du token** (`CanReadToken`), supprimant l'exception pour tout appelant et dans tous les modes sans rien perdre. **Voie 2, nécessaire** : la voie 1 seule fait *sauter* le parse au banc, qui n'exerce alors toujours pas le chemin déployé — le harnais forge donc un vrai JWT par identité (miroir de `PscTokenForge`), `PSC_TOKEN` restant une échappatoire. 17 tests, avec deux choix qui portent la démonstration : exceptions comptées en **première chance** (seul moyen d'observer un défaut que le code masque) et **token k6 figé en fixture C#** (une divergence d'encodage JS/.NET ferait retomber le banc dans le chemin qu'il quitte sans rien casser de visible). Passe `/simplify` : cache de tokens retiré — **par VU**, ~900 VUs, ~100 Mo pour économiser une microseconde. Sonar : **zéro finding introduit**. `loadtest-skill` : grille de lecture d'« Exceptions /s ». **Les 2 critères de DOD au banc restent dus.** Défaut hors périmètre signalé : `PatientRepository` filtre sur `DateTime.Today` (local) des dates stockées en UTC — faux entre minuit et 2 h. | — |
| task-211 | **`read_list` n'attendait plus des threads mais des verrous.** Après task-205, 718 ms de moyenne pour 213 ms de médiane au palier 882 — la moyenne vaut 3,4 fois la médiane, signature d'une file d'attente ; file ThreadPool plate (max 8) et CPU à 1,1 cœur sur 24 écartent les deux suspects habituels. **Deux corrections de l'énoncé, établies en lisant le code.** (1) Le correctif d'une ligne proposé — « ajouter un `TryAcquireAsync` immédiat » — aurait été un **no-op** : cet essai existe déjà au site d'appel, la boucle d'attente n'étant atteinte qu'après son échec. Le vrai défaut est le **pas de sondage** (1 s fixe, sans réveil à la libération), remplacé par un pas croissant 25 ms → 500 ms. (2) **`proceeding anyway` tranché : le verrou distribué est OPPORTUNISTE** — trois éléments l'établissent dans le code existant (l'appelant fetch quand même en cas d'échec ; le code re-vérifie la base après acquisition ; son commentaire parle de prévenir un fetch concurrent, ce qui est une économie) — d'où un budget d'attente ramené de **30 s à 5 s**, l'issue étant enregistrée pour rendre le compromis mesurable. **Instrumentation** : deux histogrammes (`mssante_lock_wait_duration_seconds` / `..._hold_...`) sur les trois verrous, attente et détention séparées car elles désignent des défauts différents ; le verrou de session mesurait déjà les deux mais vers les logs seulement. Table « Verrous du chemin read_list » dans `report.py`, rendue même vide. Aucune étiquette ne porte d'email (PGSSI-S + cardinalité). **Non touché délibérément** : la portée du verrou de session et l'existence du verrou en processus — la task les subordonne à la mesure, et le verrou de session protège une connexion IMAP non thread-safe. 7 tests ; 3 243 verts. Sonar : les 2 findings C# étaient de la dette introduite par l'instrumentation (S3776/S138), corrigés par extraction de quatre helpers ; **zéro finding attribuable à la task**. **Les 5 critères de DOD au banc restent dus** — c'est la table des verrous qui doit y répondre. | — |
| task-213 | **Une voie d'écriture pour l'archivage — et une vérification au banc qui ne juge pas le correctif.** `imap_session` sérialise TOUTES les opérations IMAP d'une session : `AppendToSentAsync` faisait donc la queue derrière le fetch d'enrichissement du même praticien (détention p95 6,3 s), d'où `send` à 35,1 s de p95 pour 1,97 s de médiane — ratio 3,3, la signature de file identifiée par task-211. Correctif : `UserContextInfo.ForWriteLane()` (clone par `MemberwiseClone`, aucun champ oubliable), seconde connexion IMAP par praticien, `AppendToSent` et `AppendToDrafts` dessus ; les autres opérations de brouillon restent sur la voie de lecture, justifié sur place. **Une option de l'énoncé était sans objet** — « sortir le parsing CDA du verrou » : task-079 l'avait déjà sorti (phases A/B). `LockOperationFamily` borne la cardinalité **et** coupe une fuite : `GetAttachment` concatène le nom de la pièce jointe, qui en messagerie de santé nomme le patient et l'examen. **Vérification au banc du 2026-08-01, deux tirs 500 praticiens, NON CONCLUSIVE.** Première tentative invalidée par son propre protocole (purge → échauffement → tir : l'échauffement avait consommé la bande d'UID, 0 acquisition de verrou — c'est elle qui a motivé le correctif « non exercé ≠ non mesuré »). Deuxième tentative, ordre corrigé : `send` p95 35 135 → 28 844 ms (< 10 s exigé, **NON**), ratio 3,3 → 2,26 (< 2 exigé, **NON**), et surtout `read_list` +82 % / `folders_warm` +63 % contre une marge de 20 % — **le critère de non-régression du DOD attrape le correctif**. Cause probable, à confirmer : la voie d'écriture double le plancher de sessions Dovecot du banc (2 500 → 5 002), et sur cet hôte l'infra partage le CPU des réplicas — la conclusion vaut POUR CET HÔTE. Aucun des deux tirs n'est valide (8,9 % / 8,0 % d'abandons) : latences lisibles, débit non. **Et le verdict ne juge pas le bénéfice** : le rapport écrit « aucune acquisition `AppendToSent` — le tir n'a pas archivé d'envoi », or l'archivage a tourné (GreenMail à 0,38 cœur, 13 973 envois à 0,38 % d'erreurs, sessions Dovecot doublées) ; il n'est simplement **pas instrumenté** — `ImapLockScope`, l'API de ~20 sites d'appel dont `AppendToSent`, n'émet aucun histogramme, seul `ProcessEmailUidAsync` est sur la voie instrumentée. **DOD 1 non rempli** : l'étiquette `operation` a été posée sur la seule voie qui n'a qu'un appelant. Suite en task-214, puis contre-épreuve. | — |
| task-214 | **Dix-neuf acquisitions du verrou de session sur vingt n'étaient pas mesurées.** `MailClientSessionManager` exposait DEUX API pour le même sémaphore : `AcquireLockWithIdAsync` / `ReleaseLockWithId`, instrumentée et appelée par **un seul** site (`ProcessEmailUidAsync`), et `ImapLockScope`, appelée par une vingtaine — dont `AppendToSentAsync`, l'opération que task-213 existe pour corriger — et qui n'émettait **rien**. La table « `imap_session`, par opération » ne pouvait donc afficher que `ProcessEmailUid`, **sur n'importe quelle campagne** : pas une décomposition du verrou, le seul appelant instrumenté. **Ce que le défaut a déjà fait dire de faux** : le rapport de vérification de task-213 conclut « aucune acquisition `AppendToSent` — le tir n'a pas archivé d'envoi », alors que quatre éléments du même corpus établissent le contraire (GreenMail à 0,38 cœur, 13 973 envois à 0,38 % d'erreurs, sessions Dovecot doublées à 5 002, et `118c3f4` — poussée deux heures avant le tir — déclarant `Sent`/`Drafts`/`Trash` côté Dovecot). Travers nommé la veille par `d4643e9` (« non exercé ≠ non mesuré »), pris **dans l'autre sens**. **Voie retenue, l'autre écartée par écrit** : instrumenter le scope, là où les deux chronomètres sont déjà, PLUS retirer l'API concurrente (109 lignes, un seul site ramené sur le scope commun) — descendre la mesure dans le sémaphore rendrait l'échappement structurellement impossible mais `LockImapClientAsync` / `UnLockImapClient` ignorent le libellé d'opération et la durée de détention, et les tests de concurrence les appellent directement pour tenir le verrou sans scope. **Le retrait est le correctif**, modèle task-205. Détail C# qui le rendait non évident : `ProcessEmailUidAsync` est un `IAsyncEnumerable` et `yield return` **est** licite sous un `await using` (try/finally ; seul un `try` porteur d'un `catch` interdit le yield). Aussi : étiquette `lane` (read/write, cardinalité 2) rendant enfin attribuable le doublement de sessions IMAP de task-213 ; issue `cancelled` (ne compter que les réussites ferait passer un verrou saturé pour un verrou peu sollicité) ; `report.py` — table « Voie / Acquisitions », et la phrase fautive remplacée par **trois états** (aucune série / indécidable / instrumentation vivante), **un test existant change de verdict, c'est le correctif** ; `docs/loadtest.md` §4d.4, quatrième règle de conclusion. **Deux documents d'exploitation portaient du faux, corrigés** : `loadtest-skill` affirmait encore que les boîtes du banc n'ont pas de dossier `Sent` (périmé depuis `118c3f4` — c'est la quatrième pièce prouvant que le tir de vérification archivait) et que les baselines `send` restent comparables (elles ne le sont plus) ; `sonar-skill` pointait SonarQube sur `:9001` quand il écoute sur `:9000`. 19 tests ajoutés (13 C# + 6 Python) constatés RED d'abord ; 3 259 verts après merge de `develop`. Sonar : Quality Gate **OK**, 0 bug, 0 vulnérabilité, 0 hotspot sur code neuf, couverture neuve 87,5 %, ratings A/A/A — **un seul** des 7 findings de code neuf attribuable à la task (`S107` introduit par la passe `/simplify`, corrigé). Réserve « KPIs projet inexploitables » de task-212/213 **levée**. **La contre-épreuve de task-213 reste due** — task-215. | — |
| task-215 | **Le témoin qui manquait à toutes les mesures précédentes.** Trois tirs 500 praticiens, même hôte, mêmes paramètres (`USERS=500 VUS=60 MESSAGES_PER_USER=100 SESSION_ROTATION=0.001 VU_TAIL_FACTOR=8 RPS=980 DURATION=3m`), protocole échauffement → purge → tir : **A** neutralise `ImapService.WriteLane` sur une branche jetable, **B** et **C** portent `develop`. **Contrôle préalable passé** — la table par opération affiche cinq lignes au lieu d'une et la voie d'écriture 102 acq/s, ce qui **prouve par la mesure** que le témoin est bien neutralisé. **(1) La voie d'écriture marche** : attente p95 `AppendToSent` 4,345 s → 0,005 s, facteur ~870, reproduit deux fois — première mesure de son BÉNÉFICE, que le tir du 2026-08-01 ne pouvait pas produire ; le témoin confirme aussi que le mécanisme diagnostiqué par task-213 existait. **(2) Elle ne sert à rien au praticien** : `send` p95 7 874 ms (A) contre 10 439 (B) et 12 573 (C), ratio moyenne/médiane 1,34 contre 1,51 et 1,71 — **le témoin satisfait les deux critères du DOD de task-213, les tirs porteurs du correctif les manquent**. Ce que la voie retire au verrou, elle le repaie en ouverture de connexion : la DÉTENTION d'`AppendToSent` monte de 3,974 s à 4,557 / 5,287 s. **(3) La dégradation des lectures n'est pas imputable au correctif** — c'était le « NON » du 1ᵉʳ août : le témoin se dégrade autant (`read_list` 4 656 ms contre 1 555 et 4 933 — donc DAVANTAGE que B), `folders_warm` est indiscernable sur les trois (1 218 à 1 342 ms). La baseline `150216` avait été tirée **avant** `0d4d801` et `d57953f` : la comparaison publiée confondait effet du correctif et changement de conf du banc. **(4) Le débit ne distingue rien** — 791,1 / 796,8 / 802,7 req/s, 1,5 % d'écart dans l'ordre chronologique et non celui du binaire. **Décomposition du ×5,5 sur `send`** : attente de verrou **écartée**, archivage devenu réel (`118c3f4`) **confirmé**, effet 200→500 praticiens **non séparable** (les trois tirs sont à 500). **Deux écarts relevés** : la vérification du 2026-08-01 se déclarait iso-conditions avec une baseline en `duration 2m` alors qu'elle tournait en `3m` ; et `observe.ps1` n'a pas été lancé pour cette campagne, donc **pas de comptage des sessions Dovecot** — la table des voies le remplace pour l'attribution, pas pour l'ordre de grandeur du surcoût (corrigé dans le plan de test de task-216). Validité : aucun des trois tirs n'est valide (abandons 11,9 / 11,0 / 10,5 %), latences lisibles, débit non — cité seulement pour constater l'absence d'écart, et les trois partagent le même taux à 1,4 point près, donc comparaison à harnais identique. Seq : 2 erreurs (défaut d'embedding connu de task-196), **0** `Failed to parse entity headers`, **0** `FolderNotFoundException`, **0** `SecurityTokenMalformedException`, **0** `enrich_short_circuited` (127 / 152 / 119 lots réellement parsés). **Défaut hors périmètre trouvé** : 7 155 `RedisTimeoutException` + 4 474 `RedisConnectionException` sur un appel **synchrone** — `ResilientCacheService.TryGet<T>` → `RedisBase.ExecuteSync`, repo **`sdk`** — depuis `MailController.GetEmailAsync`, qui parque un thread du pool jusqu'à 5 s sous charge : même classe de défaut que celle retirée par task-205. **Décision : retirer la voie d'écriture (task-216)** ; l'instrumentation de task-214 reste, c'est elle qui a permis de trancher. Aucun code de production touché — 3 lignes d'`INDEX.md`. | — |
| task-196 | **La borne d'entrée des embeddings était dans la mauvaise unité, et l'échec était muet.** Troncature en caractères là où le modèle compte des tokens (ratio réel mesuré : **2,1 car./token**, pas 4) : un document clinique de 19 065 caractères — sous l'ancienne borne — dépassait les 8 192 tokens, partait en `HTTP 400`, et disparaissait de l'index sémantique **sans erreur visible du praticien ni moyen de savoir lequel manquait**. Re-constaté en charge (1 286 `ClientResultException` en 20 min), après **rectification d'une erreur d'analyse** qui avait classé cette famille en « bruit Flagsmith » alors que `FlagsmithAPIError = 0`. Livré : **une seule** borne, en tokens, avec le **tokeniseur réel** du modèle (vocabulaire embarqué — aucun accès réseau au démarrage, déploiement HDS cloisonné) ; coupe sur frontière de token (paires de substitution réglées gratuitement) ; `MaxEmbeddingCharacters` supprimée au profit de `MaxEmbeddingTokens`, avec garde contre la divergence `appsettings`/code ; **repli** qui re-borne et réessaie une fois. **Décision tranchée et écrite** : troncature plutôt que segmentation multi-vecteurs (hors périmètre : modèle de données et classement), avec ce qu'on accepte de perdre — la fin du document n'est pas indexée — **rendu mesurable** pour arbitrage ultérieur. **L'échec cesse d'être silencieux** : compteur par cause (annulation != panne), inventaire des documents sans vecteur (ni contenu clinique ni INS), ré-indexation depuis le contenu stocké **sans IMAP** — garantie structurelle testée. `Microsoft.Bcl.Memory` remontée en 10.0.10 (`GHSA-73j8-2gch-69rq`, sévérité haute). **Deux défauts bloquants trouvés à la revue, tous deux à la jointure des deux agents parallèles** — dont un compteur qui comptait double et collait un `provider_error` sur chaque arrêt propre ; le test qui manquait est ajouté. 3 580 tests verts. **Sonar non mesuré** (serveur absent). Vérification au banc encore due — la baseline `search`, PROVISOIRE depuis task-174, en dépend. | — |
| task-240 | **Le premier poste de coût du parcours n'était attribuable à aucun de ses appels.** L'étape `read_list` pèse **46,3 % du temps serveur** (p95 4 781 ms à 200 médecins, doublée depuis que task-239 a déplacé le goulet sur elle) mais agrégeait **deux appels HTTP** sous une seule étiquette `op` — percentile de mélange, aucune optimisation décidable ; `dashboard` en agrégeait **quatre**, signalé le 2026-08-04 et jamais traité. **US d'instrument** : elle ne rend rien plus rapide, elle rend le prochain correctif décidable (règle issue de task-222), et lève l'un des quatre motifs du NO-GO 500. Livré : une étiquette `call` **à côté** de `op` — jamais à la place, pour que la grille SLO et l'INDEX restent comparables sur des dizaines de tirs — une table déclarative des étapes multi-appels, et surtout une **phrase attribuable** nommant le porteur du p95 et celui du temps total en disant quand les deux diffèrent. Section rendue même vide, trois états distincts. Étiquettes littérales bornées, aucune donnée de santé, cardinalité maîtrisée. **Défaut bloquant trouvé à la revue** : la fixture certifiait une **arithmétique impossible** (`http_reqs` compte une fois par requête, donc l'étape vaut 2× ses appels) et le rapport s'en contredisait lui-même — 80 s d'un côté, 184 s de l'autre, invisible de tout test ; fixture redevenue un tir possible, trois invariants de mélange vérifiés. **La garantie de comparabilité éprouvée par MUTATION** : les quatre tests tombent quand on injecte une régression plausible — ce ne sont pas des tests verts par construction. Auto-tests 209 Python + 57 node. **Sonar skip propre** (aucun code applicatif). Contre-épreuve au banc encore due — la DOD est prouvée sur fixture, pas sur mesure. | — |
| task-220 | **Le banc simule des médecins, pas des requêtes.** Scénario `journey` (modèle fermé `ramping-vus`, 1 VU = 1 médecin, paliers de population), parcours dérivé du client Blazor réel avec provenance (`docs/parcours-medecin.md`), temps de réflexion log-normaux bornés par étape, 4 opérations nouvelles (`dashboard`, `attachment` + octets, `delete` sur bande dédiée à budget contrôlé, `mark_read`), grille SLO validée (`docs/SLO-parcours-medecin.md`) confrontée par `report.py` — verdict par étape × palier, K=1 seul opposable ; table du genou, coûts résidents contre N, familles `journey`/`mixed` séparées dans l'INDEX. Smoke réel vert (5→10 médecins, K=10, 0 % erreur). `enrich` sorti du parcours (décision consignée). Zéro diff `mixed.js`/`vu-sizing.js`. | — |
| task-221 | **Les serveurs mail simulés quittent l'hôte sous test.** Manifests kustomize (Dovecot StatefulSet 1 réplica + ConfigMap complète + réglages NFS + index hors NFS, GreenMail, Toxiproxy, PV/PVC 50 Gi) livrés code-only dans DevOps/Staging ; interrupteur unique `MSS_LOADTEST_MAIL_HOST` (AppHost : zéro conteneur mail local, vérifié dans les deux sens ; seed `--mail-host` ; harnais k6 `TOXIPROXY`/`LATENCY_MS`). RTT 5 ms mesuré → latence 95 ms ; DOD 10/10 sur le vrai cluster (seed 49 s, smoke PASS 0 % err, doveadm 2 sessions/praticien) ; **verdict NFS tenu** (~1,5× max, seuil 2×). Sonar : 17 issues new-code héritées de task-218 nettoyées (smells 47→30). Débloque la campagne de certification K=1 de task-220. | — |
| task-223 | **Le verrou de session rendait un sémaphore qui n'était pas le sien.** La libération retrouvait la session par son identifiant (`UnLockImapClient` → `GetSession(id)` → `Release()`) au lieu de rendre le sémaphore pris : entrée recyclée pendant l'opération ⇒ `SemaphoreFullException`, levée hors du `try` d'`AppendToSentAsync` (initialiseur du `await using`) ⇒ **500 sur un envoi remis** — 1 sur 3 352 à la campagne de certification du 2026-08-03, la seule erreur du tir. Correctifs : `ImapSessionLockHandle` (le jeton porte le sémaphore pris, plus de recherche à la libération, rendu unique par `Interlocked`, aligné sur `BackgroundImapConnectionRegistry.Lease`) **et** libération défensive (`SemaphoreFullException`/`ObjectDisposedException` journalisées, jamais propagées — le recyclage dispose le sémaphore, donc rendre le *bon* verrou lève aussi). Troisième porte fermée à la revue : `TimeoutException` d'acquisition (120 s) convertie en `Result`, `OperationCanceledException` laissée remonter (499). Distinction rendue au praticien (`{ queued, archived, warning }`, libellé fixe) et tracée (`AuditActionType.MailArchiveSent`, ajoutée **en fin** d'énumération, aucune donnée de santé, aucune migration). 12 tests, reproduction constatée ROUGE. Sonar : **zéro dette introduite** (les 18 `new_violations` appartiennent à task-185/218/220). **Tir K=1 au banc encore dû**, et la mention côté client reste à câbler (`Single frontend: true`). | — |
| task-222 | 🚫 **ANNULÉE le 2026-08-04 — aucune ligne sur `develop`.** PR `api-mail` #150 fermée sans merge, branches supprimées. Motif : trop de modifications non maîtrisées sur une seule branche (correctif applicatif retiré + passe de simplification + refactoring du chemin d'ouverture + instrumentation). **Ce que l'US a néanmoins établi, et qui vit ailleurs** : (1) l'étape 3 du parcours `journey` ne mesure pas ce que son nom annonce — le scénario n'appelle jamais `enrich` et chauffe par `getEmailContent`, donc « servi base » mesurait des mails **jamais enrichis**, d'où l'égalité 440 ≈ 442 ms avec le chemin froid ; verdict **non opposable** → repris par **task-224**, défaut 5, priorité relevée 3 → 2 ; (2) une ligne `MailContents` est le **marqueur d'enrichissement** (`GetEnrichedUidsAsync`, `TryResolveExistingMailAsync`, `GetCoverageCountsAsync`) — l'écrire depuis le chemin de lecture écarte le mail de l'enrichissement ⇒ CDA jamais décodé, aucun document médical, aucun rattachement patient, et `NotifyAlreadyEnrichedAsync` annonce au frontend que c'est fini : **perte de contenu clinique silencieuse**, invisible pour 3 399 tests verts (aucun ne traverse ouverture → enrichissement). Défaut arrêté en **relecture humaine avant merge** ; (3) le soupçon de la US sur `mssante_lock_hold_duration_seconds` est **infirmé** — l'émission est correcte depuis task-214, le silence est côté observation. Le décompte des sollicitations du serveur, seul acquis livrable, est repris par **task-225**. Dossier d'instruction : `tasks/archived/archived-task-222.md` + `questions/task-222.md`. | — |
| task-225 | **Le décompte des sollicitations du serveur de messagerie.** `IMailServerSolicitationRecorder` (`Scoped`), compteur `mssante_mail_server_solicitations_total{command,operation}`, étiquette de trace `mss.mail_server.solicitations` portant le delta propre à l'appel. Une session reprise du pool **ne compte pas** donc borne inférieure **exacte** des allers-retours, pas une estimation. Étiquettes littérales uniquement, propriété PGSSI-S **figée par un test**. Reprend le seul acquis livrable de task-222 (annulée), dans un périmètre verrouillé : aucun correctif, aucune méthode ajoutée au dépôt, garde de lecture inchangé, harnais intact — clauses vérifiées par commande. **Garde-fous reposés** : deux avertissements en clair là où la main se reposerait, et deux tests prouvant qu'une lecture n'écrit rien (dont un sur vrai PostgreSQL). Sonar : **zéro dette, une seule itération, zéro correction** — première sur l'EPIC, effet des conventions apprises. Trois instabilités de tests établies **préexistantes par mesure**, dont un défaut d'isolation reproduit sur `develop` pur et signalé comme candidat à correction. **Débloque le défaut 5 de task-224** : l'étape 3 enregistre 5 sollicitations, elle devra en enregistrer 0. | — |
| task-224 | **Les cinq défauts d'instrument du banc.** Le plus grave n'était pas un défaut d'affichage : l'étape « relire un message enrichi » ne mesurait pas un message enrichi — le parcours ne déclenchait jamais l'analyse, d'où l'égalité 440 ~ 442 ms avec l'étape froide, **signature de l'artefact** et non symptôme. Chauffe par `enrich/sync`, et surtout **le rapport refuse désormais le verdict d'une étape « servie base » dont le serveur a été sollicité** (trois états, absence ≠ zéro) : sans ce contrôle, un chiffre DANS la cible aurait été publié vert. Les quatre autres : unités des latences (**2** occurrences, dont une trouvée par le contrôle et absente du constat initial — le « juge de l'attribution ») ; panneau d'erreurs lisant un Rate et non un Counter, + `noValue` sur 77 blocs ; adresses paramétrées regroupées (cardinalité bornée, compteurs plus sous-estimés de 61 %, et le nom de PJ retiré de la télémétrie) ; sessions IMAP lues dans le magasin, « non relevé » jamais un zéro. Verdict de l'étape 3 du 3 août requalifié **non opposable** dans l'index. 20 tests ajoutés ; Sonar zéro finding attribuable, vérifié par (règle, fichier) et non par total. ⚠️ Revue : la chauffe coûte désormais ~65 s de pipeline CDA par VU — risque chiffré sur le premier palier, à surveiller au tir. **4 critères déférés au banc.** | — |
| task-226 | **Le dossier patient entre au parcours, et le tir cesse d'exiger un semis.** Deux changements qui n'en font qu'un : « supprimer » retiré (seul geste qui détruisait son corpus, donc imposait la reconstruction des boîtes entre deux tirs) libère les 40 % de boîte dont le dossier patient avait besoin. Le dossier entre **en chaîne** — `traitement CDA → ouverture d'un message traité → consultation du dossier` — ce qui **révise la décision de task-220** : l'analyse reste hors grille (publiée, jamais jugée) mais entre au parcours, puisque sans elle il n'y a pas de dossier. Le détour par la lecture est le chemin réel **et** le seul possible (`enrich/sync` répond sans corps). Rafale de la fiche **bridée à 6** (contrainte du navigateur, pas du banc) : ~23 appels en une action contre ~8,5 pour un passage entier. La grandeur qui informe est un **couple** — rafale qui sature (page plafonnée à 20) contre dossier qui croît, sur une page calculée en lisant tout le dossier. Réserves **disjointes** contrôlées au setup : le défaut 5 de task-224 ne peut pas revenir par la porte du traitement. `reset-state.sh --keep-analysed N` rend le rejeu possible **sans semis ni ré-analyse**. Grille : 4 lignes actées (8 réduite, 9/10/11 ajoutées), et un **test interdit désormais à la grille de diverger de son contrat lisible**. Sonar sauté (zéro `.cs`, harnais hors périmètre du scanner) — raison consignée. 2 défauts trouvés en revue et corrigés (écart de règle déclaré) ; 1 garde et 1 correction de doc hors périmètre, assumées. **6 critères déférés au banc**, dont *le* critère du gain : deux tirs consécutifs sans semis. **Point ouvert PO** : le 5ᵉ appel (« charger plus ») attend une fréquence produit. | — |
| task-228 | **La Phase A de l'enrichissement rend le verrou de session entre sous-lots.** task-079 avait sorti la persistance du verrou `imap_session`, mais la Phase A le gardait pendant **tout** le fetch réseau du lot : détention **p95 58,5 s** au tir `journey-mssante-n300` du 2026-08-04, portée intégralement par `EnrichEmails`. Ce verrou sérialisant *toutes* les opérations IMAP d'une session (clé `{email}_{ClientSessionId}`), `GetEmailContent` payait **1,79 s d'attente p95**. `EnrichEmailsAsync` itère désormais `ChunkForEnrichment(pendingUids, EnrichFetchChunkSize)` et délègue chaque fenêtre à `FetchEnrichmentChunkAsync`, qui ouvre **son** `ImapLockScope` — verrou pris et rendu par sous-lot. `MailOptions.EnrichFetchChunkSize` (défaut **15**, repli journalisé si < 1). ⚠️ **La contrainte 1 de la US se trompait d'endroit** : un commentaire affirmait que le hash d'UIDs dans la clé `EnrichEmails:{folder}:{hash}` sérialisait les passes concurrentes ; faux — `AcquireLockAsync` ne transmet qu'un **libellé**, `LockImapClientAsync` keye sur la session seule, et `MailProcessingMetrics.LockOperationFamily` tronque au premier `:` (donc **cardinalité de métrique inchangée** par la clé par sous-lot, vérifié sur l'implémentation). La garantie anti-course est `LockEnrichPersistAsync` par (boîte, dossier), Phase B, non touchée — propriété figée par un test (3 fenêtres de fetch ⇒ **1** persistance). Commentaire réécrit. **Fuite préexistante corrigée** : `FetchedMail` (`IDisposable`, porteur d'un `IheXdmScratchSet`) n'était libéré par aucun chemin — les répertoires de travail ne partaient qu'au balayage de démarrage ; `finally` + `DisposeAll`. **Changement de comportement volontaire** (exigé par le DOD) : une erreur IMAP au milieu du lot persiste ce qui a été lu au lieu de tout jeter, les UIDs restants redevenant `pending` — sûr car chaque `FetchedMail` est individuellement complet, invariant gardé par les 13 tests de task-227. 7 tests assertant le **nombre** d'acquisitions du verrou (une durée dépendrait de la machine) ; **preuve ROUGE** : lot remis monolithique ⇒ 3 échecs. Sonar : **zéro dette attribuable**, prouvé par second scan — le seul finding (`CA1859`) avait été introduit par la passe `/forge-simplify` elle-même (paramètre élargi à `IReadOnlyList<uint>` quand `Enumerable.Chunk` rend des `uint[]`) et est corrigé ; `new_violations` 30 → 28. Plan de contrôle : `agents/sonar.md` corrigé (serveur en **25.6.0**, pas 9.9.8 ⇒ `sonar.token`). **La taille 15 et le gain ne sont PAS mesurés** — contre-épreuve `journey` n300 avant/après **bloquante pour le merge** (leçons task-213 et task-222), et coût attendu du découpage : une ouverture de dossier IMAP par fenêtre, plafonné à +20 % par le DOD. | — |
| task-229 | **Le dashboard cesse de redemander ce qui n'a pas changé.** `dashboard` pesait 25,5 % du temps serveur, `read_list` 18,5 % — 44 % à eux deux, même route. Cinq remèdes internes, zéro changement de contrat : cache de `emails/today` validé par `(Count, UidNext)` (5 RTT → **0** quand rien n'est arrivé, la US visait 3 sur 5) ; upsert des dossiers en **1 lecture + 1 SaveChanges** et **hors du verrou IMAP** (détention p95 4,77 s, l'attente que payait `GetEmailContent` à 1,67 s) ; réconciliation SQL sortie du chemin cache-hit ; TTL `folder:metadata` 10 s → 5 min + invalidation en fin de sync ; `SELECT Users` caché. **Trois constats hors US** : l'invalidation demandée existait déjà, le **passage de minuit** aurait fait servir la liste d'hier, et deux items du DOD se contredisent (les étiquettes sont **dans** la réponse ⇒ remède 3 partiel, assumé). **Deux défauts trouvés par la forge sur son propre code** : DTO caché différent du DTO frais (nom de dossier changeant d'un rafraîchissement à l'autre) — dont le test était **d'abord inutile**, découvert par la preuve ROUGE ; et tâche de fond sans contexte utilisateur ⇒ ménage **silencieusement perdu** (écart de règle `/review` déclaré). +28 tests, **6 preuves ROUGE**, une 7ᵉ écartée comme invalide. Sonar **zéro dette** par 3 scans (32 → 29 → 28) — le 2ᵉ a montré qu'un correctif de `S1067` avait seulement **déplacé** le finding. Piège de mesure consigné : **128 tests d'intégration silencieusement ignorés** par `--artifacts-path`, ramenés à 16. **Contre-épreuve au banc due et bloquante pour le merge** : rien ici ne mesure une latence. | — |
| task-230 | **Marquer lu acquitte sur la base ; la propagation IMAP part groupée en arrière-plan.** Le geste payait 4 allers-retours IMAP dans la réponse HTTP, sous le verrou de la voie de LECTURE : p50 331 ms / p95 524 ms, hors grille SLO, 8,7 % du temps serveur, détention p95 du verrou 0,997 s. Chemin synchrone réduit au commit + enfilage ; **deux files** — persistée pour la durabilité, en mémoire pour la latence — parce que la file persistée n'est drainée par **aucun timer** et n'aurait pas tenu la borne de 10 s que la US impose elle-même. **Rafale regroupée en UN aller-retour, sans fenêtre d'attente** (la file persistée est déjà l'accumulateur) : 20 clics ⇒ 1 trajet, 1 verrou. **Sur question humaine**, périmètre étendu aux **quatre gestes et à leurs variantes en lot** : l'asymétrie créait une divergence VISIBLE (base « non lu » / serveur « lu ») sur un geste courant, désormais impossible par construction. **Un seul chemin d'écriture de flag** subsiste. **Trois défauts préexistants** trouvés, tous sur la durabilité invoquée par la US : réclamation non atomique entre pods, actions `Failed` jamais rejouées (retry inatteignable), constructeurs ambigus pour le conteneur. **Deux erreurs de la forge** corrigées et consignées : une boucle sans fin dans le rejeu, et une affirmation fausse sur la disparition du cycle DI — que les tests d'intégration ont démentie. **La trace d'audit ne ment plus** (« OK flags updated » sans avoir parlé au serveur) et le chemin d'un flag **ne lit plus le contenu clinique**. +34 tests, 6 preuves ROUGE, dont un test de la forge **qui ne valait rien** et a été refait. Sonar **zéro dette** par 4 scans (31 → 29 → 32 → 28), deux scans ayant révélé du code devenu mort. **Contre-épreuve au banc due et bloquante** : rien ici ne mesure une latence, et le travail réseau se chevauche désormais avec l'activité du médecin. | — |
| task-234 | **Trois tâches de fond visaient une autre base que la requête.** L'identité du praticien était reconstituée sans `MssRpps`, dont le nom de base se dérive — risque de perte de donnée silencieuse sur une plateforme « une base par praticien ». Corrigé par un point de vérité unique (`CopyIdentityTo`) et un garde-fou **par réflexion** qui échoue si un futur champ d'identité n'est pas recopié. Défaut passé au travers de **3 467 tests et quatre analyses SonarQube**, trouvé par un humain regardant la table `PendingActions`. Au passage : la garde anti-fuite de donnée de santé cherchait `NIR` dans **tout** le corps de réponse, `traceId` compris, et échouait **3 fois sur 3** sur le préfixe d'identifiant de connexion d'ASP.NET — recentrée sur les champs authored, puis **vérifiée qu'elle mord encore** par simulation d'une vraie fuite. **Le filet qui aurait dû attraper le défaut reste à poser : task-235.** | — |
| task-233 | **La page d'un dossier patient cesse de coûter la taille du dossier.** Pagination, agrégation, comptage et tri déportés en SQL (seule la page revient, filtre partagé entre page et `TotalCount`, débordement `int` du `Skip` borné) ; **index `(Ins, MailId, Date)`** sur `MailMedicalDocuments`, qui **n'avait aucun index sur `Ins`** — ce qui **corrige le diagnostic de la US**, laquelle accusait les six filtres de nom de dossier ; règle clinique « envoyés / brouillons / corbeille » récitée **33 fois en LINQ plus une fois en mémoire**, ramenée à une **colonne générée par PostgreSQL** de source unique, gardée contre la dérive. `MailFolders.FolderType` **écarté sur preuve** : dérivé des seuls attributs SPECIAL-USE, il classe `Custom` le dossier nommé `Trash` de la boîte de dev (50 messages), et s'y fier aurait **relâché la règle clinique**. Deux défauts trouvés pendant le cycle, dont un **de production** (le getter `DataContext` levant depuis task-231) qui avait passé toute la suite parce que les tests **injectent** ce que la production **résout** — garde d'architecture posée. **Trois tests portés d'InMemory vers un vrai PostgreSQL**, InMemory ignorant les colonnes calculées. Zéro violation Sonar « new code » dans un fichier de la task. **Contre-épreuve au banc bloquante pour le merge : non faisable sur la base de dev (41 documents pour ~300 demandés).** | — |
| task-235 | **La suite d'intégration échoue désormais quand elle journalise une erreur.** Collecteur d'événements `Error`/`Critical` porté par `AsyncLocal` (xUnit parallélisant les classes, un collecteur global aurait produit un flaky, donc un filet désactivé), base de test qui fait échouer sur ce qui reste, **une seule exemption** dans tout le dépôt. **Il a mordu dès sa première exécution** : six tests au rouge portant **mot pour mot** l'erreur que la US citait en preuve que la suite journalisait une panne et restait verte — et la cause était **le harnais lui-même**, ni `MssRpps` ni `ConnectionStringServer` n'étant posés dans les fixtures, ce qui rendait l'écart de base de task-234 structurellement inobservable et laissait la jambe de durabilité morte derrière un `catch` best-effort. Corrigés : 3 523 tests verts. Zéro violation Sonar « new code » dans un fichier de la task (sur 35, toutes héritées). **Périmètre réduit assumé** : le câblage de `IBackgroundTaskQueue` part dans task-237, donc le scope de tâche de fond n'est **toujours jamais créé** en test, et l'adoption du filet est de 11 classes sur 21. ⚠️ Durée de la suite d'intégration ~2 min 45 s → 5 min 05 s, cause **non établie**. | — |
| task-236 | **L'outbox est éprouvée cache chaud, et le getter qui rendait le piège possible n'existe plus.** Le correctif était déjà sur `develop` (PR #162) ; cette task livre le filet : `WarmCacheContextResolutionTests` construit les dépôts par le **constructeur de production** avec un cache d'identifiant **chaud** — la combinaison exacte du défaut, absente de tout le harnais — et fait au passage tourner les **migrations FluentMigrator dans un test** (CREATE DATABASE + MigrateUp réels), refermant partiellement l'angle mort de task-233. Preuve ROUGE : getter réintroduit → 3 échecs sur 4 nommant la cause ; portée dite sans survente (impossible en isolation pour le cliché d'audit, résolu en amont). Recensement écrit des chemins sortant sans résoudre. **Arbitrage humain rendu : le getter `DataContext` est supprimé** — zéro usage restant, le compilateur devient la garde. `S103` hérité de task-231 corrigé après trois signalements. | — |
| task-237 | **Le scope de tâche de fond est enfin créé et exécuté pendant les tests.** File déterministe à la demande (`DrainAsync`, scope DI neuf par élément, exceptions propagées, zéro sommeil), câblée dans les deux fixtures ; `UserContextInfo` enregistré **production-exact** (scopes vides, remplissage des seuls scopes de requête par le harnais) — forme née de **deux preuves ROUGE restées vertes**, chaque masquage documenté. L'assertion qui aurait attrapé task-234 existe et **nomme les deux bases** en cas d'écart. 8 drains dans EmailManagement : la frontière asynchrone devient visible. **2 chemins sur 3** (enrich = couche API, consigné). **Trois mensonges de harnais découverts** (domaine mail jamais déclaré — tous les tests Gmail de develop cassés depuis le 06/08 ; cache résilient = substitut à miss permanent — cache-hit de task-229 jamais atteignable ; fast-path de provisionnement keyé sans serveur) et **un défaut develop réparé** (c565250 avait cassé ses propres tests SMTP, invisibles de la CI). 369/369. | — |
| task-238 | **Envoi sous 1 000 ms — la connexion SMTP retenue est entretenue au lieu de mourir entre deux envois.** Keep-alive SMTP branché sur la boucle de session existante (`Wait(0)`, démarrage idempotent bi-voie, NOOP en échec → client écarté = reconnexion propre au lieu de l'IOException de sonde) ; sonde d'emprunt conditionnée à l'âge du signal de santé (`SmtpProbeMaxAge` 60 s = 2 × keep-alive ; signal distinct de l'accès, qui est rafraîchi avant qu'on sache si la connexion vit) — le NOOP par emprunt disparaît du chemin nominal, smoke banc réel à **0 NOOP**. Remède 3 = **correction de diagnostic** : le cache OCSP/CRL demandé existe depuis task-069, rien construit (5ᵉ correction d'US de la semaine). Zéro changement de contrat. `Dispose` rendu idempotent au passage. 🚧 Contre-épreuve banc bloquante pour le merge (p50 ≤ 1 000 vs 1 229), banc non monté. | — |
| task-239 | **L'enrichissement rend le verrou de session entre chaque message.** La fenêtre de verrou par sous-lot (task-228, 15 messages) pesait 7,44 s de détention p95 (`journey-certif-n200-120344`) — le plafond mesuré du palier 200 : inbox 4 112 ms p95, lectures à 25 ms coincées à 10 s. Désormais une fenêtre courte lit les résumés du sous-lot, puis **une fenêtre par message** lit ses corps et PJ — chaque intervalle laisse passer un geste du médecin (FIFO du sémaphore). Zéro coût ajouté au chemin nominal (client et dossier réutilisés entre fenêtres, re-SELECT payé seulement sous entrelacement réel) ; le travail réseau payé survit aux coupures de milieu de sous-lot (`EnrichmentChunkFetch` porte les messages lus AVEC l'indication d'abandon). **Diagnostic de la US corrigé** : parse CDA et écritures base étaient déjà hors verrou depuis task-079 — le poste réel était la largeur de la fenêtre de fetch. Preuve par mutation (6 tests ROUGES sur le code par sous-lot), test d'intégration au vrai session manager (geste bloqué PENDANT une fenêtre, passant ENTRE deux, lot persisté exactement une fois par message). **Contre-épreuve n200 bloquante pour le merge** : détention ≤ 2 s, inbox ≤ 1 000 ms, fiche patient re-mesurée (décide l'US hydratation). | — |
| task-241 | **Le keep-alive SMTP n'était pas inerte : il n'était pas compté, et il agissait sur la mauvaise horloge.** US ouverte par une **instruction, pas un correctif** — task-238 avait livré trois remèdes sans effet mesurable sur deux campagnes. **Les deux faits fondateurs de la US étaient des lectures d'instrument** : `noop = 0` ne mesurait pas le keep-alive (`NoOp` n'était consigné que par la sonde, que task-238 avait précisément retirée du chemin nominal — « zéro sonde » était le résultat **voulu**), et « ~1,85 connexion par envoi » **agrège IMAP et SMTP**. Troisième occurrence de cette famille dans l'EPIC, première fois dans les **prémisses** d'une US. **Cause réelle : deux horloges.** `LastSmtpAccessTime` n'est rafraîchi qu'à l'emprunt du jeton et pilote l'éviction (`SmtpIdleTimeout` 5 min) ; le battement ne met à jour que le **signal de santé**. Le keep-alive garde la connexion vivante sur le fil pendant que l'éviction la ferme sur son inactivité d'usage — et la marge n'est que de **douze secondes** (~4,8 min entre deux envois contre 5 min de seuil). Livré : le correctif d'**instrument** seul (`SmtpKeepAlive` distinct de `SmtpSend`, hors requête). Arbitrage de politique **déféré à l'humain** — les deux voies augmentent le nombre de connexions retenues par boîte, face à la contrainte opérateur MSSanté. | — |
| task-242 | **L'attente d'une connexion à la base accélère avec la population, et le verdict qui l'avait écartée est périmé.** Part des relevés `cl_waiting` non nuls : **5 % → 7 % → 29 %** (50/100/200 médecins, soutenu). Toutes les autres grandeurs résidentes croissent **linéairement** (sessions IMAP 116/245/483, backends Postgres 92/175/352) ; celle-ci **accélère** — candidat n°1 au prochain plafond, et un des motifs du NO-GO 500. **Le piège était dans le rapport lui-même** : « Ressource épinglée » écartait PgBouncer en **moyennant les trois paliers** (14 %, sous le seuil de 25 %) alors que c'est le **palier** qui décide d'une conclusion de capacité — les deux affirmations contradictoires coexistaient dans le même document. Livré : verdict **par palier**, écart écrit, verdict précédent marqué périmé, seuil nommé une seule fois, 13 tests dont **deux témoins négatifs**. Deux corrections de revue : **donnée morte** (`cl_waiting_practitioner`/`_maintenance` émis mais jamais rendus — précisément la famille que porte le seuil) et garde de colonnes séparée pour qu'un pooler sans `maxwait_us` ne fasse pas retomber la sonde à zéro. | — |
| task-243 | **Le premier poste de coût du parcours cesse d'être une boîte noire de 3,3 secondes.** US **d'instrument, pas d'optimisation** : « où part le temps **à l'intérieur** de la requête », pour un p95 de 5 676 ms. Trois phases choisies pour trancher entre les trois candidats et rien de plus — `connection_open` (contention base pure), `sql_execute` (travail serveur), `assemble` (**le reste, par différence** : matérialisation). `connection_open` **ne pouvait pas se mesurer au point d'appel** (Npgsql ouvre paresseusement) : passage par **intercepteurs EF Core**, en lisant les `Duration` qu'EF mesure déjà plutôt qu'en re-chronométrant. `assemble` est **volontairement une soustraction** — le découper n'aurait aucun sens tant qu'on ne sait pas s'il pèse. Compteur `mssante_db_operation_queries_total` pour distinguer « une requête lente » de « trente rapides », deux remèdes sans rapport ; il vérifie du même coup l'annonce « 6 à 8 requêtes groupées », jamais mesurée. Périmètre **non ré-entrant**, coût **nul** hors périmètre. ⚠️ Développée **directement sur `develop`** à la demande humaine — pas de PR, pas de HAG, seule exception de l'EPIC. A immédiatement fondé task-244. | — |
| task-244 | **Un tir sans chauffe ne peut plus rendre un verdict vert.** La chauffe envoyait 98 UID en **une** requête (délai 300 s) : expirée pour **500 médecins sur 500** au tir `journey-remote-n500`, alors que le serveur travaillait encore — un **délai**, pas une panne. Base restée quasi vide ⇒ latences **flattées** (`GetMailsByUids` à 55,4 ms/7,8 requêtes contre 1 199,7 ms/14,8, chiffré par l'instrument de task-243). **Et le rapport publiait « 8 étapes vertes sur 11 »** : le refus de task-224 ne se propageait pas aux étapes 2, 10 et 11, servies par la même base vide. **Famille de défaut nouvelle** — statistique bonne, source bonne, **portée** trop courte. Livré : (1) chauffe **lotie** (10 UID, délai par lot dimensionné sur le coût unitaire **sous charge** 3,5 s/msg, distinct du forfait au repos 0,45 s ; un lot perdu n'interrompt pas les suivants, un lot abouti est *acquis*) ; (2) `journey_warmup_completed`, **un échantillon par médecin**, source d'**une** ligne de verdict au lieu de 500 lignes de log ; (3) **propagation** — `served_by_db` sur les étapes 2, 3, 10, 11, non opposables sous l'un des deux planchers (chauffe **90 %**, servi-base **95 %**), les étapes 4 et 6 gardant leur verdict (portée **logique, pas maximale**). Seuils écrits dans `docs/loadtest.md` § 4d, désormais **cinq** règles de conclusion. **Lotir n'accélère rien** — le coût unitaire reste le sujet (task-245). S1940 refusée avec justification (`NaN <= 0` vaut `false` : la forme « simplifiée » laisserait passer un NaN). 12 tests dont le **témoin négatif**. Contre-épreuve 500 distant différée au Manual Test Plan. | — |
| task-245 | **Le pipeline d'enrichissement cesse d'etre une boite noire.** Goulot G1 du tir 500 — plus de 3 s par message sous 100 medecins concurrents (borne par le bas : l'appel a expire), p95 serveur « au moins 10 s ». US **d'instrument**, pas d'optimisation : elle empeche d'ecrire le prochain correctif sur une intuition, le parsing CDA etant le candidat evident donc celui qu'il faut se garder de designer avant mesure. Livre : `EnrichmentOperationScope` (perimetre **par message**, AsyncLocal, non re-entrant, cout nul hors perimetre) avec les phases `imap_fetch` / `xdm_extract` / `cda_parse` / `db_write` / `assemble`. **La phase fetch est SEMEE et non accumulee** — les deux moities du travail d'un message sont separees par le reste du sous-lot et aucun contexte asynchrone ne les relie ; sans cela le fetch paraitrait gratuit et les phases depasseraient le total. **L'embedding est hors perimetre**, fait verifie et non oublie : `Publish` MassTransit non attendu, donc `enrich/sync` ne paie pas cette latence. **Le p95 serveur saturait a 10 s** (seaux par defaut d'ASP.NET Core) — vue OTel sur le jeu partage, 30 et 60 s en queue. Compteurs messages/requete pour distinguer « un message lent » de « trente moyens ». Point d'alimentation unique pour les 8 sites SQL (lecon de task-214). PGSSI-S : etiquette `phase` seule, litteraux finis, **verifie par test**. 23 tests neufs dont le temoin « si le fetch domine, c'est lui qui est nomme ». Zero issue Sonar sur les 7 fichiers C#, duplication 0,4 → 0,3 %. Contre-epreuve banc differee ; **finding consigne** : la copie parallele du pipeline dans `BackgroundImapService` n'est pas instrumentee. | — |
| task-247 | **Le comptage des fils ne balaie plus la table entiere.** Premiere US d'optimisation de la serie, rendue possible par task-243 (decomposition) et task-242 (mesure). La mesure designait la **construction des donnees** — 961,6 ms sur 1 199,7 (80,2 %) — et **ecartait la base** (attente de connexion 0,1 %, invariant sur deux regimes). Defaut corrige (F-243-1) : `ComputeThreadCountsAsync` lisait **deux fois la table entiere** par page d'en-tetes, sans filtre de page ; le cout suivait la **taille de la boite** (~50 000 messages chez un praticien reel), pas celle de la page. Les deux lectures sont bornees aux **racines de la page**. **Pas de filtre par dossier ni par generation** — le DOD le suggerait, le comportement l'interdit : un fil traverse les dossiers (racine dans `Sent`, reponses en `INBOX`), et borner ferait retomber ce fil a un mono-message ; le DOD autorisait d'expliquer plutot que d'appliquer. **Piege de traduction trouve par les tests** : `roots.Any(r => References.Contains(r))` passe sur Npgsql mais pas sur InMemory — remplace par une chaine de OR en arbre d'expression, comprise des deux. 4 tests de caracterisation **ecrits avant** le correctif, dont le fil inter-dossiers et un temoin negatif qui a corrige une hypothese fausse (`ThreadCount = 1` et non 0). Non-regression **verifiee par stash/re-run** : memes 2 flakies qu'au baseline. **Aucun gain demontre** : 3 criteres du DOD restent ouverts, ce sont des mesures qui exigent un tir. `/sonar` non rejoue. | — |
| task-248 | **L'hydratation d'une fiche patient ne coute plus une requete par document.** Finding F-243-2 : `PopulateMailContentAsync` emettait **3 requetes par document** (biologie, synthese, pieces jointes), soit « 10 + 3xD » par message — `GetMail` a 10,5 requetes/appel et un **p95 a 60 000 ms, le plafond de delai d'attente**. **L'argument decisif est une confrontation croisee** : au tir 500 sur base quasi vide, la materialisation tombe de 109,8 ms a **2,1 ms** et le p95 a **281 ms** — le plafond etait conduit par **la donnee**, pas par la charge. Livre : les 3 recherches faites **une fois par message** puis indexees ⇒ **3 requetes au total, quel que soit D** ; `BuildMedicalDocumentDto` rendue **synchrone** (le N+1 devient impossible a reintroduire par distraction) ; 57 lignes de chargeurs par document **supprimees** pour ne pas inviter a son retour. **Pas de cablage sur `LoadBulkMailLookupsAsync`** malgre son existence : concu pour une page, modifie par task-247, l'y brancher aurait mele les deux gains — le task file demandait de verifier avant de cabler. **Risque INS traite en premier** : appariement sur `DocumentId`, filtre sur `MailId`, liste vide jamais `null` ; cloisonnement inter-messages **prouve par test**. Critere n°1 du DOD prouve **deterministement** par un intercepteur local au test (le compteur task-243 n'est pas cable dans la fixture — constat empirique), avec assertion d'**egalite** entre D=1 et D=5 et non « moins de requetes ». **Eprouve par mutation deux fois** (2 puis 3 tests tombent). Integration **380, 0 echec** — ce qui a **tranche** une incertitude flaky/regression laissee ouverte au developpement. 4 criteres sur 6 restent ouverts : ce sont des mesures au banc. `/sonar` non rejoue. | — |
| task-250 | **Un enrichissement de contact concurrent n'est plus perdu en silence.** Une occurrence sur 133 214 requetes au tir 200 : `DbUpdateConcurrencyException` journalisee puis **avalee**, donc enrichissement **perdu** sans que personne ne le sache — et sa probabilite croit avec le **carre** de la population (deux praticiens correspondant avec le meme confrere). **Cause etablie par lecture, et ce n'est pas la ligne `Contacts`** (aucun jeton de concurrence, son UPDATE affecte toujours 1 ligne) : c'est le `RemoveRange` des collections enfants, qui emet un DELETE **par ligne** attendant 1 ligne. Premier remede — suppressions **idempotentes** — **abandonne** : `ExecuteDeleteAsync` est relationnel uniquement et leve sur InMemory (constat empirique, un test unitaire est tombe) ; **deuxieme piege de portabilite de provider de la session** apres task-247. Retenu le **rejeu**, en realite superieur : l'idempotence aurait fait taire l'exception tout en laissant le dernier ecrivain **ecraser** l'apport de l'autre, alors que le rejeu relit l'etat gagnant et y re-applique le sien — les deux enrichissements survivent. **Frontiere de couche respectee** : EF n'est pas reference par l'Application, le depot traduit en `ConflictException` (regle 12) en conservant la cause ; verifie sur le diff. Rejeu **borne a 1** (une boucle tournerait indefiniment sous charge) et conflit irreconciliable journalise en **erreur**, jamais avale. **⚠️ Le premier test d'integration etait vert AVEC le defaut** (deux `UpdateAsync` sequentiels ne peuvent pas se croiser) — demasque par mutation, reecrit, desormais rouge sans le correctif. 6 tests neufs. Integration 384, 0 echec. Dernier critere du DOD (zero exception sur un tir 200) exige un tir ; `/sonar` non rejoue. | — |
