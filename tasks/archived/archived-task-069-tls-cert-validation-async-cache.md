# todo-task-069.md — Perf certificats : suppression du sync-over-async TLS et caches OCSP/CRL/X509

**Repos**: api-mail
**Dependencies**: (aucune)
**Epic**: E011

> US mono-repo justifiée : optimisation backend pure de la chaîne de validation
> des certificats IGC Santé (TLS IMAP/SMTP, OCSP, CRL). Aucun changement de
> contrat ni d'UI.

## Objective

Éliminer les blocages synchrones (`Task.Run(...).GetAwaiter().GetResult()`)
dans les callbacks de validation de certificats TLS des connexions IMAP/SMTP —
chaque connexion utilisateur subit aujourd'hui 50 à 500 ms de blocage thread
pool pendant le handshake — et mettre en cache les artefacts stables de la
chaîne de validation (certificats émetteurs parsés, réponses OCSP/CRL) avec une
résilience correcte quand les répondeurs sont lents ou indisponibles.

## Findings adressés (audit perf 2026-06-10)

| # | Localisation | Problème | Impact |
|---|---|---|---|
| 1 | `src/Application/Services/Implementation/BackgroundImapService.cs:424` | `ValidateAsync(...).GetAwaiter().GetResult()` dans le callback TLS | Élevé |
| 2 | `src/Application/Services/Implementation/SmtpConnectionFactory.cs:221` | `Task.Run(() => ValidateAsync(...)).GetAwaiter().GetResult()` (double anti-pattern) | Élevé |
| 3 | `src/Application/Services/Implementation/ImapConnectionManager.cs:102` | Idem | Élevé |
| 4 | `src/Application/Helpers/ImapClientTlsConfigurer.cs:68` | Idem | Élevé |
| 5 | `src/Application/Services/Implementation/OcspValidationService.cs:193-241` | Le certificat émetteur est caché en `byte[]` mais re-parsé (`LoadCertificate`) à chaque usage | Moyen |
| 6 | `src/Application/Services/Implementation/OcspValidationService.cs:29-97` | Validation OCSP en ligne bloquante si cache Redis indisponible, sans fallback borné | Moyen-Élevé |
| 7 | `src/Application/Services/Implementation/CrlValidationService.cs:125-147` | Téléchargement CRL sans retry/timeout court ni fallback (timeout global 30 s) | Moyen |
| 8 | `src/Application/Services/Implementation/CrlValidationService.cs:130` + `OcspValidationService.cs:76` | Validations séquentielles certificat par certificat, parallélisables | Moyen |

## Comportement attendu

- Les callbacks TLS ne bloquent plus de thread : la validation
  asynchrone (OCSP/CRL) est effectuée **avant** ou **après** le handshake sur un
  chemin async, ou s'appuie sur un cache pré-chargé consultable de façon
  synchrone non bloquante dans le callback.
- Les certificats émetteurs sont cachés sous forme d'objets `X509Certificate2`
  (clé = thumbprint, TTL raisonnable) — plus de re-parse DER par requête.
- OCSP/CRL : timeout court explicite, retry/circuit-breaker, et stratégie de
  fallback documentée et validée (comportement en cas de répondeur injoignable —
  **décision sécurité à arbitrer, voir question ci-dessous**).
- La validation de plusieurs certificats d'un même envoi est parallélisée.

✅ **Arbitrage sécurité tranché (humain, 2026-06-11 — voir
`questions/task-069.md`)** : **Option C — hybride**. En cas d'indisponibilité
du répondeur OCSP/CRL :
- Une réponse OCSP/CRL en cache, même périmée, reste acceptée pendant une
  **fenêtre de grâce de 4 h** après son expiration. Chaque acceptation
  dégradée journalise un évènement **Warning** (PGSSI-S).
- Au-delà de 4 h sans réponse fraîche, ou sans aucun cache disponible :
  **fail-close** (connexion TLS refusée).
- La fenêtre de grâce ne s'applique **que** au statut « unknown »
  (répondeur injoignable) — un certificat **révoqué** est refusé
  immédiatement et définitivement, sans aucune fenêtre de grâce.
- Timeout court (5 s) + 1 retry sur les téléchargements OCSP/CRL,
  conformément au DOD.
- Le statu quo antérieur (fail-open de fait : `Result.Error` hétérogène +
  timeout CRL 30 s) doit être documenté dans la PR.

## Definition of Done

- [ ] Build passes : `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` (0 erreur)
- [ ] Tests pass : `dotnet test HealthPlatform.Api.Mail.sln` (0 échec)
- [ ] Plus aucun `.Result` / `.Wait()` / `.GetAwaiter().GetResult()` sur la chaîne de validation de certificats (vérifiable par grep sur les 4 fichiers concernés)
- [ ] Cache `X509Certificate2` émetteurs en place (plus de re-parse DER par validation)
- [ ] Timeout explicite <= 5 s + retry borné sur les téléchargements OCSP et CRL
- [ ] Comportement de fallback OCSP/CRL indisponible documenté dans la PR et validé par l'humain
- [ ] Validation multi-certificats parallélisée (`Task.WhenAll` ou équivalent)
- [ ] Unit tests : >= 1 test par branche du nouveau flux de validation (cache hit, cache miss, répondeur down, certificat révoqué)
- [ ] Integration test : envoi SMTP via le pipeline DI complet avec validation de certificat mockée (happy path + certificat révoqué refusé)
- [ ] La sémantique de sécurité est inchangée : un certificat révoqué reste refusé (tests le prouvant)
- [ ] Aucune donnée de santé ni détail de certificat nominatif en clair dans les logs

## Manual Test Plan

- Lancer l'API : `cd Api/Mail && docker-compose up -d && dotnet run --project src/Api`
- Depuis le client Blazor, envoyer un mail MSSanté à une adresse de test : l'envoi
  aboutit, la latence de premier envoi est mesurée puis comparée à un second
  envoi (le second doit être nettement plus rapide grâce aux caches).
- Couper l'accès réseau au répondeur OCSP de test (ou pointer vers une URL
  invalide en configuration) : l'envoi suit le comportement de fallback arbitré
  (et le log serveur trace l'évènement, sans bloquer 30 s).
- Vérifier sous charge légère (10 envois successifs) l'absence de blocage et la
  stabilité du temps de réponse.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (LPS MSSanté)
- **Vague Ségur** : hors Ségur — optimisation technique ; les exigences MSSanté existantes (IGC Santé) restent honorées à l'identique
- **Exigences DSR honorées** : MSSanté — vérification de la validité des certificats IGC Santé maintenue (non-régression, pas de nouvelle exigence)
- **INS** : non applicable — aucun traitement patient
- **Authentification PS** : inchangée
- **Habilitations** : non applicable
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : évènements de validation de certificat (échec, révocation, fallback dégradé) journalisés ; durée de conservation inchangée
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement HDS existant inchangé
- **AIPD / impact RGPD** : inchangé

## Branches
- `api-mail` (pushed) : feat/task-069-tls-cert-validation-async-cache — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-069-tls-cert-validation-async-cache
- `dtos-mss` (pushed, auto-incluse) : feat/task-069-tls-cert-validation-async-cache — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-069-tls-cert-validation-async-cache

## Develop log

- Repos touched : api-mail uniquement (dtos-mss : aucun changement de contrat, branche sans commit, pas de PR)
- DTOs published : no DTO change
- Interop published : no interop change
- Commits (api-mail, branche `feat/task-069-tls-cert-validation-async-cache`) :
  - c5d142b feat(certificates): split validator into sync pre-handshake + async revocation, refuse revoked certs
  - 5ce3b0b feat(certificates): OCSP/CRL bounded 4h grace window, 5s timeout + retry, issuer object cache
  - e373b1c feat(certificates): non-blocking TLS callbacks with post-handshake revocation on IMAP/SMTP
  - 66edad5 test(certificates): SMTP end-to-end through full DI with in-process TLS server
- Local build / test : ✓ build 0 erreur ; domain 94/94, infrastructure 346/346, api 484/484, application 1595/1595 ; integration 216/218 — les 2 échecs sont les pré-existants documentés (`ConnectAsyncWithCancellationShouldRespectTokenAsync` flaky, passe isolé ; `PatientUseCaseTests.GetMailsByInsWithPagination…` rouge sur develop vierge, vérifié via stash)
- Architecture : callback TLS = checks sync non bloquants (allowlist IGC Santé + fenêtre de validité) + capture du certificat ; révocation OCSP/CRL awaited post-handshake AVANT toute authentification, déconnexion si échec. `TlsCertificateValidationSession` + factory DI. Sémantique par site préservée via `acceptWhenNoPolicyErrors` (true : SmtpConnectionFactory, ImapClientTlsConfigurer ; false : ImapConnectionManager, BackgroundImapService).
- Option C implémentée (arbitrage humain 2026-06-11) : grâce 4 h sur cache périmé GOOD avec Warning PGSSI-S, fail-close au-delà ou sans cache, révoqué refusé immédiatement sans grâce, timeout 5 s + 1 retry (configurable via `SslTlsOptions`).
- 🔒 **Bug sécurité pré-existant corrigé** : `CertificateValidator.ValidateAsync` traitait `Success(false)` (révoqué) comme un succès — un certificat révoqué était accepté sur les chemins OCSP ET CRL. Corrigé + tests le prouvant (exigence DOD).
- ⚠️ Observation hors scope (à trier par le PO) : `AutodiscoveryHelper.GetSmtpServerConfig` mappe positionnellement `userConfig.UseStartTls → useAuth2` et `userConfig.UseOAuth2 → validateServerCertificate` — mis-mapping apparent pré-existant, non touché (règle 6).
- DOD self-check : 11/11 items commandables vérifiés (grep sync-over-async : 0 occurrence ; cache X509Certificate2 émetteurs ✓ ; timeout/retry ✓ ; fallback documenté ✓ ; Task.WhenAll ✓ ; tests par branche ✓ ; integration happy+revoked ✓ ; révoqué refusé prouvé ✓ ; logs sans donnée nominative — Subject remplacé par SerialNumber/Thumbprint dans les logs des services touchés)
- no angular change → skipped /lint-angular
- Next step : /sonar task-069 (api-mail touché)

## Sonar log

- Phase 1 (new code) : ✓ Quality Gate OK, new_violations = 0, new_security_hotspots_reviewed = 100 %, new_coverage = 82.8 % (artefact connu : new code period = baseline quasi-totale du legacy, cf. mémoire forge — le code task-069 lui-même est couvert par 33 tests unitaires + 3 intégration)
- Phase 1 — Issues fixées : 2 (S3874 CRITICAL `out` param sur ValidatePreHandshake → Result Ardalis ; CA1822 INFO membre static) — commit f0d7bb5
- Phase 1 — Tests ajoutés : 0 (les 2 fixes sont des refactors purs, filet = tests existants ; 3 tests adaptés à la nouvelle signature)
- Phase 2 (legacy) : sans objet — 0 issue ouverte sur tout le projet après Phase 1
- KPIs finaux : bugs 0, vulnérabilités 0, code smells 0, hotspots 0, ratings A/A/A, coverage projet 82.8 → **83.8 %** (+1.0 pt apporté par les tests task-069), duplication 0.7 %
- Build / tests : ✓ green (échecs résiduels = pré-existants documentés)
- Next step : /review task-069 (pas d'Angular → /lint-angular skipped)

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/101 — label `awaiting-human-merge`
- `dtos-mss` : aucun changement de contrat — branche sans commit, pas de PR
- `client-angular` : non listé dans **Repos** — aucun travail Angular

## Code Review Summary

**Verdict : APPROVED** — 26 fichiers relus (+1922/−367), 0 issue bloquante.

- ✅ Correctness : les 8 findings de l'audit perf sont adressés ; sémantique de refus préservée par site (`acceptWhenNoPolicyErrors`) ; révoqué refusé sur tous les chemins (bug pré-existant corrigé).
- ✅ Sécurité : aucun credential envoyé avant validation de révocation (prouvé par intégration) ; fail-close au-delà de la grâce ; pas de donnée nominative dans les logs (Serial/Thumbprint).
- ✅ Architecture : session par connexion + factory DI, options centralisées dans `SslTlsOptions`, pattern Ardalis Result conservé.
- ✅ Performance : zéro blocage thread dans les callbacks ; caches L1 objet + L2 Redis ; Task.WhenAll multi-certs ; timeouts courts + retry borné.
- ✅ Tests : 33 tests unitaires nouveaux/adaptés + 3 intégration ; Sonar Quality Gate OK, coverage 82.8 → 83.8 %.
- ⚠️ Suggestions (non bloquantes) : `emailForLogs="smtp"` dans SmtpConnectionFactory (pourrait être l'email réel) ; mis-mapping positionnel pré-existant dans `AutodiscoveryHelper.GetSmtpServerConfig` (hors scope, à trier PO).

## Merged

- **Date** : 2026-06-11
- **api-mail** : PR #101 squash-mergée — commit `d178561` sur `develop` (commit final de branche : `e3e96b9`, incluant le durcissement humain : révocation systématique sur connexions MSSanté UseAuth2 + télémétrie revoked/revocation_source + log level Debug)
- **dtos-mss** : aucune PR (branche sans commit) — branche remote supprimée, clone resynchronisé sur `develop`
- **CI develop** : ✅ success — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/27363982915
- Branches locales conservées pour inspection rétroactive (convention /merge)
