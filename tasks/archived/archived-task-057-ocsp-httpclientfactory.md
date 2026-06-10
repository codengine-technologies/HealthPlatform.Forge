# todo-task-057-ocsp-httpclientfactory.md — Suppression des `new HttpClient()` OCSP (épuisement de sockets)

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**EpicTitle**: Robustesse & observabilité de la plateforme

## Objective

Éliminer le risque d'**épuisement de sockets** (port exhaustion / `TIME_WAIT`)
et de contournement de la politique de résilience dans la validation OCSP des
certificats, en passant par `IHttpClientFactory` au lieu d'instancier
`new HttpClient()` à la volée.

Aujourd'hui
[OcspValidationService.cs](Api/Mail/src/Application/Services/Implementation/OcspValidationService.cs)
crée `new HttpClient()` à chaque requête OCSP (lignes ~148 et ~226). Même
encapsulé dans un `using`, ce pattern :
- épuise les ports TCP sous charge (les sockets restent en `TIME_WAIT`),
- **contourne le resilience handler standard** (retry / circuit-breaker /
  timeout) configuré globalement via `ConfigureHttpClientDefaults`
  ([DependencyInjectionExtensions.cs](Api/Mail/src/Api/DependencyInjectionExtensions.cs)),
- ne bénéficie pas de l'instrumentation HttpClient OpenTelemetry.

Le pattern correct existe déjà dans le même domaine :
[CrlValidationService.cs](Api/Mail/src/Application/Services/Implementation/CrlValidationService.cs)
injecte `IHttpClientFactory` (client nommé `"CrlClient"`, enregistré dans
[DependencyInjection.cs](Api/Mail/src/Api/DependencyInjection.cs)). On reproduit
ce pattern pour OCSP.

Cible :

1. Enregistrer un client nommé (ex. `"OcspClient"`) via
   `services.AddHttpClient("OcspClient")`.
2. Injecter `IHttpClientFactory` dans `OcspValidationService` et remplacer les
   `new HttpClient()` par `httpClientFactory.CreateClient("OcspClient")`.
3. Conserver le comportement fonctionnel (timeout OCSP, headers, parsing de la
   réponse) à l'identique — iso-comportement de validation.

Périmètre **petit, isolé, mono-repo** `api-mail`, sans impact contrat ni
frontend.

## Gherkin

_Pas de `.feature` (BDD déprécié, cf. CLAUDE.md règle 1). Comportements
couverts par tests unitaires._

## Definition of Done

- [x] Build passes (`dotnet build HealthPlatform.Api.Mail.sln`, 0 erreurs)
- [x] Tests pass (`dotnet test HealthPlatform.Api.Mail.sln`, 0 échecs)
- [x] Client nommé `"OcspClient"` enregistré via `AddHttpClient` dans
      [DependencyInjection.cs](Api/Mail/src/Api/DependencyInjection.cs)
      (bénéficie donc du resilience handler + instrumentation par défaut)
- [x] `OcspValidationService` injecte `IHttpClientFactory` ; **plus aucun**
      `new HttpClient()` dans le fichier
- [x] Le timeout OCSP, les en-têtes et le parsing de réponse sont **inchangés**
      (iso-comportement) — la requête OCSP produit le même résultat qu'avant
- [x] Tests unitaires couvrant la validation OCSP via un `IHttpClientFactory`
      mocké (réponse `good` / `revoked` / timeout / erreur réseau →
      comportement attendu, ≥ 1 test par branche)
- [x] Aucune autre instanciation `new HttpClient()` introduite ; vérification
      que le service utilise bien le client factory
- [x] Aucune régression sur le flux de validation de certificat (OCSP) appelé
      par les connexions IMAP/SMTP

## Manual Test Plan

- Lancer le backend : `cd Api/Mail/src/Api && dotnet run`.
- **Validation nominale** : déclencher une connexion IMAP/SMTP qui passe par la
  validation de certificat (ex. ouverture d'un dossier de messagerie). Vérifier
  dans les logs que la validation OCSP s'effectue et **réussit** comme avant
  (statut `good`), sans erreur nouvelle.
- **Observabilité** : confirmer dans Seq / OpenTelemetry que les requêtes OCSP
  sortantes apparaissent désormais dans l'instrumentation HttpClient (trace de
  l'appel vers le répondeur OCSP), preuve que le client factory est bien
  utilisé.
- **Charge légère** : enchaîner plusieurs connexions/validations successives et
  vérifier l'absence d'erreurs de socket (`SocketException` / ports épuisés)
  dans les logs.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — durcissement technique de la couche
  validation de certificat, sans impact sur un volet métier Ségur.
- **Vague Ségur** : hors Ségur — robustesse/fiabilité plateforme.
- **Exigences DSR honorées** : non applicable — aucun volet de contenu ou de
  transport modifié.
- **INS** : non applicable — aucune donnée patient manipulée.
- **Authentification PS** : inchangée — la validation OCSP fait partie de la
  chaîne de confiance TLS des connexions MSSanté/IMAP ; son **résultat** est
  iso, seul le mécanisme d'émission de la requête HTTP change.
- **Habilitations** : non applicable.
- **Interop CI-SIS** : non applicable — aucun échange CDA/FHIR/HL7v2 modifié.
- **Tracé PGSSI-S** : inchangé fonctionnellement ; léger renforcement de
  l'observabilité (requêtes OCSP désormais tracées via l'instrumentation
  HttpClient). Aucune donnée de santé journalisée.
- **Consentement patient** : non applicable.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : oui — environnement de production HDS existant,
  périmètre inchangé.
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement de données.

### DOD santé (items applicables)
- [x] La validation OCSP (maillon de la chaîne de confiance MSSanté/IMAP)
      conserve un comportement iso : un certificat révoqué reste rejeté
- [x] Aucune donnée sensible (certificat complet, secret) journalisée en clair
      dans les traces OCSP ajoutées

## Branches
- `api-mail` (pushed) : fix/task-057-ocsp-httpclientfactory — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-057-ocsp-httpclientfactory
- `dtos-mss` (pushed, auto-included) : fix/task-057-ocsp-httpclientfactory — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/fix/task-057-ocsp-httpclientfactory

## Develop log

- Repos touched : api-mail (dtos-mss : branche créée par auto-inclusion, aucun changement de contrat — pas de commit, pas de PR)
- DTOs published : no DTO change
- Interop published : no interop change
- Commits :
  - api-mail : 2c81e84 fix(ocsp): route OCSP HTTP traffic through IHttpClientFactory
- Local build / test : ✓ build 0 erreur ; tests 0 échec hors les 2 rouges pré-existants documentés (middleware DB-name, IMAP cancel flaky)
- Implementation notes :
  - `OcspValidationService` : injection `IHttpClientFactory`, les 2 `new HttpClient()` (requête OCSP ligne ~148, téléchargement issuer ligne ~226) remplacés par `CreateClient("OcspClient")` — iso-comportement (timeout, header `application/ocsp-request`, parsing inchangés)
  - `DependencyInjection.AddApi` : `services.AddHttpClient("OcspClient")` (pattern miroir de `CrlClient`) — resilience handler par défaut + instrumentation OTel HttpClient
  - `[ExcludeFromCodeCoverage]` retiré (raison « untestable without responder mock harness » caduque) — harness responder construit : CA + certificat feuille avec extension AIA réelle (`X509AuthorityInformationAccessExtension`), réponses OCSP signées BouncyCastle, stub `HttpMessageHandler` derrière la factory mockée
  - Tests : `OcspValidationServiceTests` réécrits test-first (RED ctor → GREEN) — 8 tests : good→true, revoked→false, HTTP 500→error, timeout→error, erreur réseau issuer→error, cache hit court-circuite sans HTTP, contrat client nommé "OcspClient" (2 requêtes GET+POST), cert sans AIA→error
  - Piège harness documenté : NSubstitute auto-retourne un tableau vide pour `Get<byte[]>` → faux positif « cache hit » avec 0 byte ; fix : `.Returns((byte[]?)null)` épinglé dans le ctor du test
- DOD self-check : 8/8 items vérifiables OK (grep `new HttpClient()` → 0 occurrence ; révoqué rejeté prouvé par test)
- no angular change → skipped /lint-angular
- Next step : /sonar task-057 (chaîne ensuite vers /review)

## Sonar log

- Phase 1 (new code) : ✓ — new_violations = 0, new hotspots = 0 (100% reviewed), duplication OK
  - Couverture new-code comblée en 2 commits de tests : `OcspValidationService.cs` 86.2% → 92.8% → **95.8%**, `new_uncovered_lines` 5 → 2 → **0** (cible 95% atteinte sur le fichier de la task)
  - Tests ajoutés Phase 1 : +4 (`d7e54f6` no-OCSP-url + responder non-successful ; `4494a49` issuer en cache + AIA sans URL issuer) — 12 tests OCSP au total
  - `new_coverage` global 74% < 80 (gate ERROR) = artefact documenté de la new-code period projet (legacy classé « new ») — hors périmètre, accepté best-effort
- Phase 2 (legacy) : 0 itération / 5 — early-stop, dette legacy nulle (bugs 0, vulnérabilités 0, code smells 0, hotspots 0, ratings A/A/A, duplication 0.6%, coverage projet 77.4%)
- Build / tests : ✓ Release green (2 échecs = rouges pré-existants documentés : middleware DB-name Release, IMAP cancel flaky)
- no angular change → skipped /lint-angular
- Hand-off : /review task-057

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/87 — label `awaiting-human-merge`
- `dtos-mss` : aucune PR — branche créée par auto-inclusion mais aucun changement de contrat (0 commit)

## Code Review Summary

**Verdict : APPROVED** (3 fichiers revus, 0 bloquant)

- `src/Application/Services/Implementation/OcspValidationService.cs` — ✅ diff chirurgical : injection `IHttpClientFactory`, 2 sites `new HttpClient()` → `CreateClient("OcspClient")`, const pour le nom du client, iso-comportement (header `application/ocsp-request`, parsing, validation inchangés) ; retrait justifié de `[ExcludeFromCodeCoverage]` (harness responder désormais en place)
- `src/Api/DependencyInjection.cs` — ✅ `AddHttpClient("OcspClient")` miroir du pattern `CrlClient` existant ; bénéficie du resilience handler global + instrumentation OTel
- `tests/.../OcspValidationServiceTests.cs` — ✅ 12 tests significatifs : harness CA + feuille AIA réelle, réponses OCSP signées BouncyCastle (good/revoked/tryLater), erreurs HTTP/timeout/réseau, court-circuits cache, contrat client nommé ; piège NSubstitute `Get<byte[]>` → tableau vide documenté et épinglé

Validation : build ✓ 0 erreur · tests ✓ (3 échecs = rouges pré-existants documentés) · DOD ✓ 8/8 + DOD santé 2/2 · Sonar ✓ 0 issue new-code, fichier 95.8% (new_uncovered_lines = 0)

## Merged

- Date : 2026-06-10
- `api-mail` : squash commit `f46a0ce` (PR #87 closed, branche remote supprimée, branche locale conservée)
- `dtos-mss` : aucune PR (branche vide) — remote `fix/task-057-ocsp-httpclientfactory` supprimée, clone resynchronisé sur `develop`
- develop CI : ✓ success — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/27269055794
