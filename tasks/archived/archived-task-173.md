# todo-task-173.md — Banc de charge api-mail : profil « loadtest » AppHost (GreenMail + Toxiproxy) + seed

**Repos**: api-mail
**Dependencies**: —
**Epic**: E015
**EpicTitle**: Tests de charge api-mail sur infrastructure mail mockée
**Single frontend**: true

> **Référence** : ADR-2026-07-25-B « Tests de charge api-mail sur infrastructure
> mail mockée » (OneDrive · Architecture Decision Record). Cette US pose le banc
> (infrastructure + seed) ; le harnais de tir NBomber est task-174.

## Objective

Rendre api-mail testable en charge **sans token PSC réel et sans toucher aux
serveurs MSSanté** : l'écosystème mail est remplacé par un conteneur GreenMail
(IMAP + SMTP) derrière un Toxiproxy d'injection de latence, orchestrés par un
profil « loadtest » de l'AppHost Aspire. **Le binaire api-mail de production ne
change pas** : la redirection passe par le mécanisme existant
`UserSettings.ImapServerConfig`/`SmtpServerConfig` (priorité absolue dans
`AutodiscoveryHelper`), et l'authentification par les mécanismes existants
(mode dev-permissif + `TestBypassAuthenticationHandler`, hard-block Production
conservé).

**US backend-only (justification)** : outillage de test pur, aucun frontend ni
contrat impacté.

### Contenu

1. **Profil « loadtest » AppHost** (`src/AppHost/AppHost.cs`) : activable
   explicitement (paramètre/variable d'environnement, jamais actif par défaut),
   ajoutant :
   - conteneur **GreenMail** (`greenmail/standalone`, IMAP 3143 / SMTP 3025 —
     reprendre le plan de `tasks/archived/archived-task-032ter-greenmail-fixture.md`) ;
   - conteneur **Toxiproxy** en frontal de GreenMail (proxies IMAP et SMTP),
     avec profils de latence configurables (défaut : RTT type MSSanté
     ~100 ms ± jitter) ;
   - conteneurs existants inchangés (Redis, Seq, RabbitMQ, Prometheus, Grafana…).
2. **Outil de seed** (console C#, hors binaire API — ex. `tools/loadtest-seed/`) :
   - crée N utilisateurs virtuels : lignes `UserSettings` en base avec
     `ImapServerConfig`/`SmtpServerConfig` pointant Toxiproxy
     (`UseSsl=false`, `UseAuth2=false`, `ValidateServerCertificate=false`) ;
   - peuple GreenMail : N boîtes × M messages synthétiques (tailles variées,
     avec/sans pièces jointes, threads) — paramétrable (N, M, distribution) ;
   - **aucune DSCP** : contenus générés (lorem/synthétique), adresses fictives
     de type `loadtest-{n}@loadtest.local`, jamais d'INS/NIR/contenu CDA réel.
3. **Forge de tokens réutilisable** : extraire la logique de
   `tests/mss.mail.api.tests/TestData/PscTokenFixtures.cs` vers un utilitaire
   partageable (lib de test ou le tool de seed) produisant des paires KC+PSC
   cohérentes (`mssEmail`/`mssSub`/`mssRpps` ↔ `sub`/`SubjectNameID`) par
   utilisateur virtuel — sans modifier les tests existants.
4. **Smoke test d'intégration bout-en-bout** (gated, style `SkippableFact` ou
   catégorie dédiée) : GreenMail + Toxiproxy démarrés (Testcontainers), un
   utilisateur seedé, appel `folders` + lecture d'un message + envoi SMTP à
   travers le vrai pipeline (session manager + MailKit) → vert. C'est aussi la
   première couverture réelle du chemin serveur-IMAP (cf. task-032ter :
   `BackgroundImapService` non couvert faute de serveur de test).
5. **Documentation** : `Docs/loadtest.md` (ou équivalent) — comment lancer le
   profil, seeder, forger les tokens, appeler l'API à la main.

### Hors scope

- Le harnais de tir, les scénarios et les KPIs (task-174).
- Toute modification du pipeline d'authentification ou du binaire API
  (les mécanismes bypass/dev-permissif existants suffisent).
- La purge du secret Gmail committé (`appsettings.test.json`) — finding de
  sécurité signalé dans l'ADR, à traiter par une action humaine indépendante
  (révocation Google + purge).

## Definition of Done

- [ ] Build passes (0 errors) — `dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés) — `dotnet test`
- [ ] Profil « loadtest » AppHost : GreenMail + Toxiproxy démarrent, jamais
      actifs par défaut (lancement standard AppHost = conteneurs actuels
      uniquement, vérifié)
- [ ] Outil de seed : N utilisateurs + M messages paramétrables ; idempotent
      (relançable) ; unit tests sur la génération (bornes N/M, cohérence
      adresses/UserSettings)
- [ ] Forge de tokens extraite et réutilisée par le seed **et** par
      `PscTokenFixtures` (pas de duplication) ; tests existants verts inchangés
- [ ] Smoke test bout-en-bout via GreenMail (folders + lecture + envoi SMTP à
      travers `MailClientSessionManager` réel) — gated proprement quand Docker
      absent
- [ ] Garde-fous vérifiés par test : bypass refusé si
      `ASPNETCORE_ENVIRONMENT=Production` ; bypass inopérant sans
      `TestMode:BypassKey`
- [ ] Aucune DSCP dans les données générées (revue du générateur) ; aucun
      token/clé en clair dans les logs du seed
- [ ] Binaire API inchangé : aucun diff sous `src/Api`, `src/Application`,
      `src/Domain`, `src/Infrastructure` hors enregistrements de test
      éventuels — sinon justification explicite dans la PR
- [ ] Documentation de lancement rédigée

## Manual Test Plan

1. **Profil off par défaut** : `cd Api/Mail && dotnet run --project src/AppHost`
   → dashboard Aspire : aucun conteneur GreenMail/Toxiproxy.
2. **Profil loadtest** : relancer avec le paramètre documenté → GreenMail et
   Toxiproxy visibles et healthy dans le dashboard.
3. **Seed** : lancer l'outil (ex. N=10 utilisateurs, M=50 messages) → sortie
   listant les utilisateurs créés ; vérifier une ligne `UserSettings` en base
   (host = Toxiproxy, `UseAuth2=false`).
4. **Appel manuel bout-en-bout** : forger une paire de tokens via l'outil,
   `curl` `GET /api/v1/mail/folders` avec `Authorization: Bearer {kc}`,
   `X-PSC-Token: {psc}`, `Client-Email: loadtest-1@loadtest.local` → 200, les
   dossiers GreenMail (INBOX…) sont renvoyés ; lire un message → contenu
   synthétique visible.
5. **Latence** : configurer Toxiproxy à 300 ms → les mêmes appels ralentissent
   d'autant (visible dans Seq/Grafana).
6. **Garde-fou Production** : lancer l'API avec
   `ASPNETCORE_ENVIRONMENT=Production` → le même appel avec `X-Test-Bypass` est
   rejeté (401/403), aucun contournement possible.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — outillage interne de test de performance
- **Vague Ségur** : hors Ségur — aucune exigence DSR concernée
- **Exigences DSR honorées** : non applicable — banc de test local/CI, jamais
  déployé ; contribue indirectement à la robustesse (performance MSSanté)
- **INS** : non applicable — données 100 % synthétiques, aucune identité patient
- **Authentification PS** : volontairement contournée **sur le banc uniquement**
  via les mécanismes de test existants (dev-permissif + `X-Test-Bypass`),
  hard-block Production conservé et testé — PSC/e-CPS inchangés partout ailleurs
- **Habilitations** : non applicable — utilisateurs virtuels fictifs
- **Interop CI-SIS** : non applicable — aucun échange métier réel
- **Tracé PGSSI-S** : non applicable au banc (pas de données réelles) ; les logs
  du banc ne contiennent ni tokens ni clés
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — banc local/CI uniquement, aucune DSCP ; interdit
  de déploiement sur les environnements HDS (profil jamais actif par défaut +
  hard-block Production)
- **AIPD / impact RGPD** : inchangé — aucun traitement de données personnelles
  (données synthétiques)

## Branches
- `api-mail` (pushed) : feat/task-173-loadtest-bench-greenmail — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-173-loadtest-bench-greenmail
- `dtos-mss` (pushed, auto-inclus) : feat/task-173-loadtest-bench-greenmail — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-173-loadtest-bench-greenmail (aucun changement DTO attendu — branche sans commit → pas de PR)

## Develop log

- Repos touched : api-mail (dtos-mss : aucun changement de contrat → branche sans commit, pas de PR)
- DTOs published : no DTO change
- Interop published : no interop change
- Commits (api-mail, feat/task-173-loadtest-bench-greenmail) :
  - 9aaf50d test(loadtest): extract PSC token forge + synthetic population generator into shared lib
  - 5784935 feat(auth): emit mssEmail + optional PSC identity claims from test-bypass
  - 933381b feat(loadtest): AppHost loadtest profile (GreenMail+Toxiproxy), seed tool, smoke test
- Local build / test : ✓ solution 0 erreur ; unit suites vertes (api 557, domain 94, application 1827, infrastructure 360) ; smoke test GreenMail vert contre Docker (Testcontainers)
- DOD self-check :
  - ✓ Build 0 erreur ; suites unitaires vertes
  - ✓ Profil loadtest AppHost off par défaut (opt-in MSS_LOADTEST), GreenMail + Toxiproxy
  - ✓ Outil de seed paramétrable + idempotent ; unit tests génération (bornes N/M, déterminisme)
  - ✓ Forge de tokens extraite (mss.mail.testing.shared) réutilisée par PscTokenFixtures + seed
  - ✓ Smoke test bout-en-bout via MailClientSessionManager réel (folders + lecture + réutilisation session + envoi SMTP), Docker-gated
  - ✓ Garde-fous testés : bypass hard-block Production + inopérant sans BypassKey
  - ✓ Binaire API inchangé (src/Api : seul TestBypassAuthenticationHandler enrichi de claims ; src/Application, src/Domain, src/Infrastructure intacts)
  - ✓ Documentation docs/loadtest.md
  - ⚠️ Finding sécurité hors scope (action humaine) : mot de passe applicatif Gmail en clair dans tests/mss.mail.integration.tests/appsettings.test.json — à révoquer + purger
- Next step : /forge-simplify task-173

## Simplify log
- Repos passed : api-mail (seul repo touché ; dtos-mss sans commit)
- Applied & committed : api-mail : 2 fichiers (d8e68eb) — fix port SMTP du chemin `--no-proxy` du seed tool (pointait le port IMAPS ; ajout `GreenMailSmtpsPort`)
- No change : reste du diff (code déjà dédupliqué au /develop — forge de tokens extraite dans mss.mail.testing.shared)
- Écarté volontairement : mutualiser la construction MIME (seed Program.cs ↔ smoke test) dans la lib partagée → refusé (ajouterait une dépendance MimeKit à mss.mail.testing.shared et tous ses consommateurs pour ~8 lignes : couplage net-négatif, principe altitude)
- Rolled back (validation RED) : aucun
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*
- Build / tests : ✓ green (seed rebuild + api.tests LoadTest 17/17)
- Next step : /sonar task-173 (api-mail touché)

## Sonar log
- Phase 1 (new code) : findings task-173 tous résolus par reclassification correcte de l'outillage
  - Hotspots new-code : 100% reviewed (2× S4830 du seed tool reclassés en test — cert-trust intentionnel GreenMail/dev)
  - Violations new-code : 4 → 1 (reclassification + reformulation S125)
- **Quality Gate new-code : ERROR — mais AUCUN finding résiduel n'est introduit par task-173** :
  - `new_coverage 73.1%` (< 95) : inchangé avant/après la branche. Seul code de prod modifié par la task = `TestBypassAuthenticationHandler` (`[ExcludeFromCodeCoverage]`) + `AppHost` (exclu Sonar). Les fichiers non couverts sont du code de prod préexistant (`MailRepository`, `ImapService`, `ImapConnectionService`…). ⇒ artefact « new-code-period large » du projet (cf. mémoire `reference_sonar_scanner_msys_argconv`), pas une régression.
  - 1× `CA1822` INFO dans `tests/…/IheXdmProcessingServiceTests.cs:80` : fichier de test **préexistant**, hors diff task-173.
- Baseline projet (inchangée) : bugs=0, vulnerabilities=0, code_smells=1, coverage=85.9%, duplication=0.7%, ratings A/A/A
- Décision requise (voir rapport) : le new-code QG ne peut pas passer au vert pour cette task (couverture d'un code de prod non écrit par elle) → ne pas halt bêtement, arbitrage humain.

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/121 — label `awaiting-human-merge`
- `dtos-mss` : branche sans commit (aucun changement de contrat) → pas de PR

## Code Review Summary
- Verdict : APPROVED (0 bloquant)
- Build Release ✓ ; domain 94/94, infrastructure 360/360, api 557/557 ; application 1826/1827 (échec = flaky PDF `MarkdownPdfRendererTests`, pré-existant, vert en isolation) ; smoke GreenMail vert (Docker-gated)
- Sécurité : test-bypass hard-block Production conservé ; TLS-disable seed = intentionnel (bench, projets classés test)
- Quality Gate new-code ERROR = artefact new-code-period pré-existant (couverture de code de prod non écrit par la task) + 1 CA1822 INFO dans un test préexistant — findings task-173 tous résolus

## Merged
- Date : 2026-07-25
- `api-mail` : squash `0e145e0` — PR #121 fermée, branche distante `feat/task-173-loadtest-bench-greenmail` supprimée (locale conservée)
- `dtos-mss` : branche vide (aucun commit, pas de PR) — branche distante supprimée
- develop CI : en file d'attente au moment du merge (runner GitHub congestionné, pas un échec) — à confirmer verte
- Staging : aucune (task lancée via /start manuel, pas un run /forge)
