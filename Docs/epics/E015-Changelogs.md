# E015 — Changelogs (vue ingénierie)

> **Audience** : équipes techniques, backlog, dette.
> Vue produit : [E015-tests-charge-api-mail.md](E015-tests-charge-api-mail.md).
> **Dernière mise à jour** : 2026-07-25

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
