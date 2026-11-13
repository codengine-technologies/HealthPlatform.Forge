# todo-task-471.md — Accès à l'API : jeton, diagnostics, flux temps réel, journaux

**Repos**: api-mail
**Dependencies**: aucune
**Epic**: E025
**Priorité**: EPIC E025, issue de l'audit du 2026-11-12/13, validée par l'humain le 2026-11-13.

> **Action humaine avant déploiement (hors forge).** Une fois cette US livrée, l'API **refuse de démarrer hors
> Development** sans `Keycloak:Audience`. La valeur (`Keycloak__Audience`) et la liste des proxys de confiance
> (règle 7) sont à poser par l'humain dans les manifestes `DevOps/` (dépôt exclu de la forge). Sans elles, le
> déploiement suivant ne démarre pas.

> **Origine.** Audit en lecture seule du 2026-11-12/13 (agents « authentification et isolation », « données, audit,
> IA », « entrées et injections »). L'audience non validée, les routes de diagnostic et l'INS dans les journaux ont été
> relus dans le code par l'orchestrateur le 2026-11-13 ; deux audits indépendants ont relevé les routes de diagnostic,
> trois le jeton dans l'URL.

## Ce qui est établi

Lecture du code au 2026-11-13 (`Api/Mail/src`) :

- **Audience facultative.** `Api/Authentication/MssAuthenticationExtensions.cs:118` :
  `ValidateAudience = keycloak.IsConfigured && !string.IsNullOrEmpty(keycloak.Audience)`. Aucun contrôle d'`azp` ni du
  type de jeton. `DevOps/Weda/configmap.yaml` ne pose pas `Keycloak__Audience` : tout jeton signé par le realm
  `weda-realm` est accepté, y compris l'ID token ou le jeton d'accès d'une autre application. Pour un titulaire, il
  ouvre la boîte sans autre contrôle (`MailboxAccessPolicy` : le titulaire est exempté du verdict, task-403).
- **Routes de diagnostic ouvertes.** `Api/Controllers/V1/AiDiagnosticsController.cs:43-48` : ni rôle ni garde
  d'environnement, `[TraceExempt]`. `test-similarity` rend jusqu'à 200 documents médicaux (corps, titre, nom et prénom
  du patient) et 200 mails, sans trace ; `recalculate-summary` relance un appel au modèle. Le contrôleur se dit
  « réservé à l'exploitation, pas une fonction du praticien ». `BenchOperatorController` montre le modèle à suivre
  (`Program.cs:148`, `AddBenchOperator()` en Development et Testing seulement).
- **`?token=` sur toutes les routes.** `MssAuthenticationExtensions.cs:138-143` lit le jeton dans la chaîne de requête
  pour toute route, écritures comprises ; le repli n'était prévu que pour les deux flux SSE (`EventSource`).
- **Flux SSE qui échoue ouvert.** `Api/Helpers/SseHelper.cs:50-66` (`AccessWatchAsync`) n'attrape que
  `OperationCanceledException` ; `MailboxStreamAccessWatch.cs:49-63` que `TenantRegistryUnavailableException` ;
  `OperatorAccessProbe.cs:55-62` qu'`UnauthorizedException` ; `PscTokenProvider.cs:144-150` lève
  `UnavailableException` (proxy en 5xx, délai, disjoncteur). La tâche de surveillance meurt, le flux continue
  (`MailEventsController.cs:146`, `NotificationsController.cs:119` : le battement ne finit jamais) et pousse les
  événements après une révocation. Le jeton n'est vérifié qu'à l'ouverture : le flux survit à son expiration.
- **Données de santé dans les journaux.** `SmtpService.cs:103` et `:144` journalisent les adresses des destinataires
  au niveau Information ; `MssanteHeaderService.cs:68` et `:154` aussi (`{Recipients}`). Une adresse patient est
  `{INS}@patient.mssante.fr` (`PatientMessageHelper.cs:7`) : chaque envoi vers Mon Espace Santé écrit l'INS dans Seq.
  Adresses de boîte en clair aussi dans `MailEventsController.cs:109,160`, `NotificationsController.cs:103,132,163`,
  `SseNotificationBroker.cs:69,117-122`, `Hubs/BackgroundSyncNotifier.cs:24`, `BaseRepository.cs:634-705`,
  `MssAccountOnboardingService.cs:68-133`, alors que le reste du code pseudonymise (`MailboxPseudonym`).
  `RequestLoggingMiddleware.cs:102,121` étiquette chaque ligne avec l'en-tête `Client-Email`, lu avant toute
  validation. `appsettings.json:33-35` surcharge `mss.mail.infrastructure` et `mss.mail.api.Controllers` alors que les
  espaces de noms réels sont `mss.mail.Infrastructure.*` et `mss.mail.Api.Controllers.V1`.
- **Secrets de session.** `Services/Psc/PersonNameResolver.cs:100` : clé Redis `psc:person-name:{ProxySessionId}`, la
  valeur du cookie de session du proxy en clair (12 h), alors que `ProxySessionPoolKey` documente que c'est un secret
  et n'en garde qu'une empreinte. `Session/MailClientSessionManager.cs:123` : clé de pool sans la personne ;
  `UserContextEnricherMiddleware.cs:896-910` accepte un `Client-Session-Id` de forme `px-…` ; repli littéral
  `"default"` (`:816`) : deux clients qui y tombent se bloquent en 409 pendant 12 h (`SessionMailboxGuard.cs:55`).
- **Adresse IP.** Aucun `UseForwardedHeaders` : `AuditService.cs:95` enregistre l'IP de l'ingress ;
  `RequestLoggingMiddleware.cs:221-242` croit `X-Forwarded-For` sans liste de proxys ; `RateLimitingSetup.cs:138`
  partitionne les anonymes sur une IP commune ; `SecurityHeadersMiddleware.cs:56` n'émet HSTS que si
  `Request.IsHttps`, jamais vrai derrière un proxy TLS.
- **Restes.** `UserContextEnricherMiddleware.cs:281-286` et `Helpers/RequestHelper.cs:126-131,271` posent
  `userContext.Email` depuis `Client-Email` sans validation (atteint seulement hors routage aujourd'hui) ;
  `Authorize/AuthorizeApiKeyAttribute.cs` est inutilisé, à comparaison non constante ; `appsettings.json:143-160`
  déclare `gmail.com` sans OAuth avec `ValidateServerCertificate: false` ; `Domain/Entities/MailDb/UserContextInfo.cs:172-192`
  (`Reset()`) ne remet pas `MailboxId`, `MailboxRole`, `PersonFirstName`, `PersonLastName` ; une requête authentifiée
  vers une route inexistante déroule la sélection de boîte et peut rendre 403 au lieu de 404.

## Objective

Seul un jeton émis pour l'API l'ouvre ; aucune route d'exploitation ne sert de données de santé à un praticien ; un
flux temps réel se ferme dès que l'accès tombe ou que le jeton expire ; aucune donnée de santé ne finit dans les
journaux.

Règles :

1. **Jeton.** Hors Development, l'API refuse de démarrer sans `Keycloak:Audience`. Elle valide l'audience, le client
   émetteur (`azp`, liste en configuration) et le type de jeton (un ID token est refusé).
2. **Diagnostics.** Les routes `api/v1/diagnostics` ne sont enregistrées qu'en Development et Testing (décision humaine
   du 2026-11-13). Ailleurs, 404.
3. **`?token=`** n'est accepté que sur les deux routes de flux SSE.
4. **Flux SSE.** Toute exception de la revérification d'accès vaut refus : événement `ACCESS_UNVERIFIED`, puis
   fermeture. Le flux se ferme à l'échéance (`exp`) du jeton présenté.
5. **Journaux.**
   - Jamais d'adresse de destinataire : le nombre de destinataires, au plus leurs domaines.
   - Les adresses de boîte passent par `MailboxPseudonym`.
   - L'adresse de boîte d'une ligne de requête n'est lue qu'après la sélection de la boîte.
   - Les surcharges de niveau Serilog suivent la casse réelle des espaces de noms.
6. **Secrets de session.** Clé Redis du nom PSC = empreinte de (session, personne) ; clé de pool de sessions et clé de
   liaison de boîte incluant la personne ; un `Client-Session-Id` de forme `px-…` est refusé en 400 ; plus de repli
   `"default"` (un identifiant absent est refusé ou tiré au hasard, au choix du développeur, documenté).
7. **Adresse IP.** Les en-têtes transférés ne sont acceptés que des proxys déclarés en configuration ; une seule source
   d'IP pour l'audit, les journaux et le limiteur ; HSTS émis quand la requête d'origine était en HTTPS.
8. **Restes.** Le repli `Client-Email`, `AuthorizeApiKeyAttribute` et le domaine `gmail.com` sont retirés ; `Reset()`
   remet tout le contexte ; une route inconnue répond 404 sans sélectionner de boîte.

### Hors périmètre (actions humaines)

- Renouveler les secrets versionnés dans `DevOps/Prod/configmap.yaml`, `DevOps/Weda/configmap.yaml` et
  `DevOps/Weda/secrets.yaml`, et les sortir du dépôt (ils restent dans l'historique git).
- Repasser les manifestes de `ASPNETCORE_ENVIRONMENT: Staging` et `Serilog__MinimumLevel__Default: Debug` à leurs
  valeurs de production.
- Servir `/metrics` sur un port de gestion ou le restreindre au réseau du collecteur.
- Renseigner `Keycloak__Audience`, la liste des `azp` admis et celle des proxys de confiance.

## Definition of Done

- [ ] Tests unitaires : paramètres de validation du jeton ; refus de démarrer sans audience hors Development ;
      filtrage de `?token=` par route ; règle de clé Redis et de clé de pool.
- [ ] **Test d'intégration de bout en bout (règle 1b) du jeton** : un jeton signé d'une autre audience, d'un autre
      `azp`, ou de type ID, rend 401 en `ProblemDetails` sur `GET api/v1/Mail/folders` ; le jeton de l'API rend 200.
      Vu rouge.
- [ ] **Test d'intégration des diagnostics** : sur un hôte en environnement `Production`,
      `POST api/v1/diagnostics/test-similarity` rend 404 ; en `Testing`, la route répond. Vu rouge.
- [ ] **Test d'intégration de `?token=`** : un jeton passé en `?token=` sur une route d'écriture rend 401 ; sur le flux
      `GET …/events/stream` il est accepté. Vu rouge.
- [ ] **Test d'intégration du flux SSE** : la revérification qui lève une `UnavailableException` ferme le flux avec
      l'événement `ACCESS_UNVERIFIED` ; un jeton qui expire ferme le flux. Vu rouge.
- [ ] **Deux personnes sur la même boîte** (règle 14) : titulaire et délégataire ont chacun un flux ouvert ; la
      délégation est révoquée ; le flux du délégataire se ferme, celui du titulaire reste ouvert.
- [ ] **Test d'intégration des journaux** : journaux capturés pendant un envoi vers une adresse
      `@patient.mssante.fr` : aucune INS, aucune adresse de destinataire, aucune adresse de boîte en clair. Vu rouge.
- [ ] **Test d'intégration des restes** : `Client-Session-Id: px-…` rend 400 ; une route inconnue rend 404.
- [ ] Prévention (règle d'or) : `conventions/csharp.md` — « un gabarit de journal ne porte jamais `{To}`,
      `{Recipients}` ni une adresse en clair ; une boucle de surveillance d'accès échoue fermée ». Le scan des gabarits
      de journaux (task-184) refuse `{To}`, `{Recipients}` et `{Email}` hors pseudonyme.
- [ ] `appsettings.json` : aucun domaine sans OAuth ni certificat non vérifié ; aucune valeur secrète.
- [ ] Build et tests verts : `HealthPlatform.Api.Mail.sln`. Parcours e2e existants rejoués verts par `/e2e`.

## Manual Test Plan

1. Lancer le backend (`cd Api/Mail/src/AppHost && dotnet run`) avec `Keycloak:Audience` renseignée.
2. Obtenir un jeton Keycloak d'un **autre** client du realm, et un ID token ; appeler `GET api/v1/Mail/folders` avec
   chacun : 401.
3. Relancer l'API avec `ASPNETCORE_ENVIRONMENT=Staging` et sans `Keycloak:Audience` : elle refuse de démarrer, avec un
   message qui nomme la variable. La renseigner : `POST api/v1/diagnostics/test-similarity` rend 404.
4. Web : ouvrir la boîte (flux SSE actif), arrêter le proxy PSC : le flux se ferme et l'interface le signale.
5. Envoyer un message à un patient (`…@patient.mssante.fr`) ; dans Seq, aucune ligne ne porte l'adresse ni l'INS.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — socle de sécurité de l'API
- **Vague Ségur** : hors Ségur — correctif de sécurité
- **Exigences DSR honorées** : non applicable — exigences PGSSI-S (authentification, journalisation, imputabilité)
- **INS** : jamais dans les journaux ; aucune identité patient manipulée par ailleurs
- **Authentification PS** : PSC (e-CPS), eIDAS substantiel ; jeton d'accès validé complètement (signature, émetteur,
  audience, client, type, échéance)
- **Habilitations** : verdict de l'opérateur revérifié en continu sur les flux (règle 14) ; routes d'exploitation
  retirées des déploiements
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : IP source réelle dans la trace ; refus d'authentification tracés par type (inchangé) ;
  `HealthDataAccess`, 3 653 jours
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — l'API et ses journaux
- **AIPD / impact RGPD** : à mettre à jour — retrait de l'INS des journaux d'exploitation (mesure de minimisation)
