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

- [ ] Build passes (`dotnet build HealthPlatform.Api.Mail.sln`, 0 erreurs)
- [ ] Tests pass (`dotnet test HealthPlatform.Api.Mail.sln`, 0 échecs)
- [ ] Client nommé `"OcspClient"` enregistré via `AddHttpClient` dans
      [DependencyInjection.cs](Api/Mail/src/Api/DependencyInjection.cs)
      (bénéficie donc du resilience handler + instrumentation par défaut)
- [ ] `OcspValidationService` injecte `IHttpClientFactory` ; **plus aucun**
      `new HttpClient()` dans le fichier
- [ ] Le timeout OCSP, les en-têtes et le parsing de réponse sont **inchangés**
      (iso-comportement) — la requête OCSP produit le même résultat qu'avant
- [ ] Tests unitaires couvrant la validation OCSP via un `IHttpClientFactory`
      mocké (réponse `good` / `revoked` / timeout / erreur réseau →
      comportement attendu, ≥ 1 test par branche)
- [ ] Aucune autre instanciation `new HttpClient()` introduite ; vérification
      que le service utilise bien le client factory
- [ ] Aucune régression sur le flux de validation de certificat (OCSP) appelé
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
- [ ] La validation OCSP (maillon de la chaîne de confiance MSSanté/IMAP)
      conserve un comportement iso : un certificat révoqué reste rejeté
- [ ] Aucune donnée sensible (certificat complet, secret) journalisée en clair
      dans les traces OCSP ajoutées
