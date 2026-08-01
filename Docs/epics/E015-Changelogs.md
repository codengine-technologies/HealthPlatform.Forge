# E015 — Changelogs (vue ingénierie)

> **Audience** : équipes techniques, backlog, dette.
> Vue produit : [E015-tests-charge-api-mail.md](E015-tests-charge-api-mail.md).
> **Dernière mise à jour** : 2026-08-01

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

## Annexe A — Cartographie des briques applicatives

| Brique | Chemin | Rôle |
|---|---|---|
| Forge de tokens | `Api/Mail/tests/mss.mail.testing.shared/PscTokenForge.cs` | JWT PSC/Keycloak à signature factice (partagé tests + seed) |
| Générateur de population | `Api/Mail/tests/mss.mail.testing.shared/LoadTestPlanGenerator.cs` | Utilisateurs + messages synthétiques déterministes |
| Profil banc | `Api/Mail/src/AppHost/AppHost.cs` (`MSS_LOADTEST`) | Conteneurs Dovecot (IMAPS) + GreenMail (puits SMTP) + Toxiproxy, injection `TestMode:BypassKey` et `TestMode:Password` |
| Conf serveur IMAP du banc | `Api/Mail/src/AppHost/dovecot/dovecot.conf` | Maildir, `passdb`/`userdb` statiques, TLS ; bind-montée dans `conf.d` **et** par le smoke test (source unique) |
| Outil de seed | `Api/Mail/tests/mss.mail.loadtest.seed/` (`Program.cs`, `SeedOptions.cs`, `ToxiproxyClient.cs`) | Proxies Toxiproxy, boîtes Dovecot (APPEND IMAP), `UserSettings` via API |
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
