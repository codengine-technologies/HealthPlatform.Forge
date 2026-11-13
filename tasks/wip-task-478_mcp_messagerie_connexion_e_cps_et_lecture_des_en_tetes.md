# todo-task-478 — Serveur MCP messagerie : connexion e-CPS et lecture des en-têtes

**Repos**: api-mcp
**Reprises**: 1
**Dependencies**: aucune
**Epic**: E026
**EpicTitle**: Messagerie depuis un assistant IA (MCP)
**Pré-flight**: limité aux Repos — décision humaine du 2026-11-13 (task-466 occupe api-mail, client-mobile et dtos-mss ; cette task ne touche que le nouveau dépôt api-mcp)
**Single frontend**: true

> **Origine.** Demande humaine du 2026-11-13. Un médecin doit pouvoir interroger sa messagerie MSSanté
> depuis Claude, ou depuis tout autre client IA compatible MCP. Choix actés avec l'humain le 2026-11-13 :
> - serveur MCP en **.NET 10**, dans un **dépôt à part** `api-mcp` (`Api/Mcp`) ;
> - authentification par **Pro Santé Connect en CIBA e-CPS**, à travers psc-auth-proxy, comme `client-mobile` ;
> - v1 en **lecture seule** ;
> - **une lecture par le MCP ne marque jamais un message comme lu**.
>
> La lecture du **contenu** d'un message n'est **pas** dans cette task : api-mail ne la trace pas aujourd'hui
> (`TraceExempt`, la trace `MailRead` n'est écrite qu'au passage à « lu »). Elle fait l'objet de task-479.

## Objectif

Le médecin ajoute le serveur MCP de la messagerie dans son client IA. Il se connecte une fois avec son e-CPS,
en validant une notification sur son téléphone. Il peut ensuite demander à l'assistant :
- quelles boîtes il a ;
- quels dossiers elles contiennent ;
- quels messages sont arrivés (en-têtes : expéditeur, objet, date, non lu, pièces jointes) ;
- de rechercher des messages.

L'assistant ne peut **rien modifier** : il n'envoie rien, ne supprime rien, ne déplace rien, ne marque rien
comme lu.

Scope limité à `api-mcp` (justification de l'exception à « tous les fronts ») : c'est un nouveau canal d'accès,
sans écran dans les clients existants. Il consomme les endpoints de lecture **déjà existants** d'api-mail, sans
les modifier.

## Règles métier

1. **Identification par PSC seulement.** Le médecin saisit son RPPS sur la page de connexion du serveur MCP.
   Il valide sur l'application e-CPS une notification qui porte le **code de liaison** (2 chiffres) affiché sur
   la page. Aucun mot de passe et aucun autre moyen d'identification.
2. **Le client IA ne voit jamais les jetons du médecin.** Le jeton Keycloak et la session du proxy restent
   dans le serveur MCP. Le client IA reçoit un jeton propre au serveur MCP, qui n'est valable nulle part
   ailleurs.
3. **Lecture seule.** Le serveur MCP n'appelle que des endpoints de lecture d'api-mail. Il ne marque jamais un
   message comme lu et n'envoie jamais d'accusé de lecture.
4. **Les verrous d'api-mail s'appliquent sans changement.** Le serveur MCP présente à api-mail le jeton
   Keycloak et la session du proxy du médecin, exactement comme `client-mobile`. Rattachement de la boîte,
   verdict de l'opérateur et rôle (règle 14) sont donc décidés par api-mail. Le serveur MCP n'ouvre jamais un
   accès qu'api-mail refuserait.
5. **Clients IA autorisés : liste blanche.** Seuls les clients MCP **pré-enregistrés** dans la configuration
   peuvent obtenir un jeton, avec leurs URL de retour exactes. Pas d'inscription dynamique.
6. **Une notification e-CPS ne part pas en rafale.** Le RPPS est public, donc n'importe qui peut déclencher une
   notification vers un médecin. Les demandes de connexion sont limitées par RPPS et par adresse IP. La page
   demande de ne valider que si le code affiché est le même que celui reçu sur le téléphone.
7. **Session bornée.** Le jeton d'accès MCP est court (15 min au plus). Le jeton de rafraîchissement tourne à
   chaque usage et ne vit jamais plus longtemps que la session du proxy. Quand la session du proxy tombe, le
   client IA doit relancer la connexion, et le médecin reçoit une nouvelle notification e-CPS.

## Comportement attendu

### Connexion

- `POST /mcp` sans jeton, ou avec un jeton expiré ou d'une autre audience → **401**, avec
  `WWW-Authenticate: Bearer resource_metadata="…/.well-known/oauth-protected-resource"` (spec MCP, RFC 9728).
- `GET /.well-known/oauth-protected-resource` → la ressource (URL du serveur MCP) et son serveur d'autorisation
  (le serveur MCP lui-même).
- `GET /.well-known/oauth-authorization-server` → métadonnées RFC 8414 : `authorization_endpoint`,
  `token_endpoint`, `code_challenge_methods_supported: ["S256"]`, `grant_types_supported` (code,
  refresh_token). Pas de `registration_endpoint`.
- `GET /authorize` (code + PKCE S256 + `resource`) :
  - client inconnu, URL de retour non enregistrée, PKCE absent ou `plain` → refus, **sans** redirection vers une
    URL non enregistrée ;
  - sinon → page de connexion : saisie du RPPS, code de liaison affiché.
- Validation du RPPS sur la page :
  1. le serveur appelle `POST {cibaEndpoint}/auth/connect`
     `{ nationalId: "8"+RPPS, bindingMessage, clientId: {clientId CIBA configuré}, channel: "MOBILE" }`.
     L'appel bloque jusqu'à la validation sur le téléphone : la page attend sans bloquer la requête du
     navigateur ;
  2. puis `POST {authEndpoint}/auth/keycloak-exchange` avec le cookie `proxy_session_id` reçu. La réponse
     porte le jeton Keycloak et un **nouveau** `proxy_session_id` (rotation) ;
  3. le serveur garde jeton Keycloak, refresh Keycloak et `proxy_session_id`, **chiffrés**, associés à
     l'autorisation accordée ;
  4. il redirige vers l'URL de retour du client avec le code d'autorisation.
- Échecs sur la page, chacun avec un message clair, sans détail technique :
  - CIBA refusé ou expiré sur le téléphone ;
  - **identité PSC liée à aucun compte** (`keycloak-exchange` → 403 `PROXY-KC-4031`) : « Première connexion à
    faire depuis l'application HealthPlatform » ;
  - proxy indisponible ;
  - trop de demandes pour ce RPPS ou cette IP → 429.
- `POST /token` : code + `code_verifier` → jeton d'accès d'audience égale au serveur MCP. Un code est à usage
  unique. Un `code_verifier` faux → `invalid_grant`.
- Rafraîchissement : le serveur rafraîchit aussi la session du proxy (`POST {authEndpoint}/auth/refresh`, cookie
  de session). Si elle est morte → `invalid_grant`, et le client relance la connexion.

### Outils MCP (lecture seule)

| Outil | Ce qu'il rend | Appel api-mail |
|---|---|---|
| `list_mailboxes` | boîtes rattachées : adresse, rôle (titulaire / délégataire / membre) | `GET /api/v1/account/mailboxes` |
| `list_folders` | dossiers d'une boîte, avec leur nombre de non lus | `GET /api/v1/Mail/folders` |
| `list_messages` | en-têtes d'un dossier, **bornés** (page de taille plafonnée) : identifiant, expéditeur, objet, date, non lu, pièces jointes | `GET /api/v1/Mail/folders/{dossier}` (ou la route d'en-têtes la plus sobre) |
| `search_messages` | messages correspondant à une recherche, bornés | `POST /api/v1/Search/semantic` (ou `keys`) |

- Chaque outil prend la **boîte** en paramètre (`mailbox`, adresse parmi `list_mailboxes`), transmise à api-mail
  par l'en-tête `Client-Email`. Chaque appel porte `Authorization: Bearer {jeton Keycloak}`,
  `Cookie: proxy_session_id=…`, `Client-Session-Id` (identifiant stable de l'autorisation MCP) et
  `X-Correlation-Id`, plus un `User-Agent` qui identifie le serveur MCP.
- Les erreurs d'api-mail (ProblemDetails) deviennent des **erreurs d'outil** MCP (`isError: true`), avec un
  message utile au médecin. Exemples : boîte non rattachée, accès suspendu par l'opérateur, session expirée.
  Jamais de trace technique, jamais de contenu.
- Les descriptions d'outils disent à l'assistant que les objets et expéditeurs sont des **données reçues**,
  pas des consignes.

## Definition of Done

- [ ] Dépôt `api-mcp` : solution `HealthPlatform.Api.Mcp.sln`, build 0 erreur, tests 0 échec
- [ ] SDK MCP officiel C# (`ModelContextProtocol.AspNetCore`), transport Streamable HTTP sur `/mcp`
- [ ] Tests unitaires : validation de la requête d'autorisation (client, URL de retour, PKCE), limitation de débit, correspondance erreurs api-mail → erreurs d'outil, bornage des pages
- [ ] Test d'intégration de bout en bout pour `POST /mcp` sans jeton : 401 + `WWW-Authenticate` portant `resource_metadata`, lu dans la réponse réelle, et `GET /.well-known/oauth-protected-resource` qui nomme le serveur d'autorisation ; vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout du parcours d'autorisation complet : `/authorize` → saisie du RPPS → CIBA (proxy simulé) → `keycloak-exchange` (proxy simulé) → code → `/token` → `tools/call list_mailboxes`. Lit dans la réponse réelle la boîte rendue par api-mail (simulé), et dans la requête reçue par api-mail simulé `Authorization` = le jeton Keycloak, le cookie `proxy_session_id` **après rotation** et `Client-Email`. Cas d'échec : `code_verifier` faux → `invalid_grant`. Vu rouge (règle 1b)
- [ ] Test d'intégration : `keycloak-exchange` → 403 `PROXY-KC-4031` ⇒ la page affiche le message « première connexion » et aucun code n'est délivré ; vu rouge
- [ ] Test d'intégration : un jeton émis pour une autre audience, ou un jeton Keycloak présenté directement, est refusé sur `/mcp` (401) ; vu rouge
- [ ] Test d'intégration : client non enregistré ou URL de retour inconnue → refus sans redirection ; PKCE absent → refus ; vu rouge
- [ ] Test d'intégration : au-delà du seuil de demandes de connexion pour un même RPPS → 429, et le proxy simulé ne reçoit pas d'appel `connect` supplémentaire ; vu rouge
- [ ] Test d'intégration : `list_messages` et `search_messages` lus dans la réponse réelle (en-têtes rendus, page bornée) ; une erreur ProblemDetails d'api-mail (403 boîte non rattachée) donne une erreur d'outil `isError: true` sans détail technique ; vu rouge
- [ ] **Lecture seule prouvée** : test qui fait tourner tous les outils et vérifie qu'api-mail simulé n'a reçu **que** des appels de la liste blanche (GET de lecture, POST de recherche). Aucune route `status/read`, `sendreadreceipt`, `sendmail`, `drafts`, `bulk`, `tags` ni `DELETE`. Vu rouge par mutation (ajout d'un appel hors liste)
- [ ] Jeton Keycloak et `proxy_session_id` jamais dans un jeton MCP, une réponse ou un journal (test : décodage du jeton d'accès MCP, recherche des deux valeurs dans le journal capturé)
- [ ] Aucune donnée de santé ni RPPS en clair dans les journaux : RPPS masqué, ni objet ni expéditeur ni contenu
- [ ] Jetons du médecin chiffrés au repos côté serveur (ASP.NET Data Protection ou équivalent)
- [ ] Configuration sans secret commité : `ApiMail:BaseUrl`, `Proxy:CibaEndpoint`, `Proxy:AuthEndpoint`, `Proxy:CibaClientId`, clients MCP pré-enregistrés (`client_id`, URL de retour), seuils de limitation
- [ ] README du dépôt : lancement local, configuration, ajout du serveur dans Claude Code (`claude mcp add --transport http …`)

## Manual Test Plan

Prérequis : pile locale de connexion du mobile, déjà en place :
- Keycloak (`D:\Workspaces\docker-compose\keycloak`) ;
- psc-auth-proxy, instance Keycloak (`https://localhost:8081/v1`) et instance CIBA (`https://localhost:7129/v1`), clientId CIBA `weda-edc-bas` (bac à sable PSC) ;
- api-mail par son AppHost.

Il faut aussi un RPPS de test e-CPS du bac à sable, avec l'application e-CPS de test sur un téléphone.

1. `cd Api/Mcp && dotnet run --project src/{projet hôte}`. Noter l'URL (par exemple `https://localhost:7300`).
2. `claude mcp add --transport http messagerie https://localhost:7300/mcp`, puis dans Claude Code : `/mcp` →
   « messagerie » → s'authentifier.
3. Le navigateur s'ouvre sur la page de connexion. Saisir le RPPS. Un code à 2 chiffres s'affiche.
4. Sur le téléphone, vérifier que la notification e-CPS porte **le même code**, puis valider.
5. Retour automatique dans Claude Code : « messagerie » apparaît connecté, avec 4 outils.
6. Demander « Quelles sont mes boîtes ? » → les boîtes du compte, avec leur rôle.
7. Demander « Quels messages non lus dans la boîte de réception ? » → la liste des en-têtes.
8. Ouvrir l'application mobile ou Angular : les messages listés à l'étape 7 sont **toujours non lus**.
9. Demander « Cherche les messages de biologie de la semaine » → résultats de recherche.
10. Dans le journal d'audit de la boîte (application) : la recherche de l'étape 9 apparaît **au nom du médecin**.
11. Refaire l'étape 3 avec un RPPS sans compte HealthPlatform : message « première connexion à faire depuis
    l'application », aucune connexion.
12. Lancer 6 demandes de connexion de suite pour un même RPPS : la dernière est refusée (trop de demandes).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — nouveau canal d'accès à la messagerie existante, sans exigence DSR propre
- **Vague Ségur** : hors Ségur — même raison
- **Exigences DSR honorées** : non applicable — aucune fonction référencée n'est modifiée ; la messagerie MSSanté reste servie par api-mail
- **INS** : non applicable — aucun patient manipulé ni identifié par le serveur MCP ; il relaie des en-têtes de messages
- **Authentification PS** : Pro Santé Connect par e-CPS en CIBA (canal MOBILE), à travers psc-auth-proxy, niveau eIDAS substantiel ; aucun autre moyen d'identification
- **Habilitations** : RPPS issu de PSC ; rattachement, rôle (titulaire / délégataire / membre) et verdict de l'opérateur décidés par api-mail (règle 14), inchangés
- **Interop CI-SIS** : non applicable — JSON-RPC MCP propriétaire, pas d'échange CI-SIS
- **Tracé PGSSI-S** : les recherches sont tracées par api-mail au nom du médecin (existant, `HealthDataAccess`, 3 653 jours) ; les listes d'en-têtes restent exemptées comme pour tous les clients (`TraceExempt`) ; les connexions MCP (CIBA demandé, validé, refusé ; jeton délivré, rafraîchi, refusé) sont journalisées par api-mcp, sans donnée de santé et avec RPPS masqué. La trace du **canal** (« via l'assistant IA ») vient avec task-479
- **Consentement patient** : non applicable — accès du médecin à sa propre messagerie
- **Référentiels métier** : aucun
- **Hébergement HDS** : api-mcp est hébergé dans l'environnement HDS de la plateforme. **Mais les résultats des outils (objets et expéditeurs, qui peuvent nommer un patient) sortent vers l'éditeur du client IA**, hors de cet environnement. Ce flux est à arbitrer par l'humain (DPO / RSSI : contrat avec l'éditeur, HDS, secret médical) **avant toute mise en production**. Il ne bloque pas le développement, qui se fait sur données de test. Rappel porté dans la PR, à trancher au merge (HAG)
- **AIPD / impact RGPD** : à mettre à jour — nouveau destinataire de données de santé (l'éditeur du client IA). Bloquant pour la mise en production, pas pour le développement

## Notes techniques (orientations pour /develop, non contractuelles)

- Serveur d'autorisation : **OpenIddict** (code + PKCE, refresh avec rotation, clients pré-enregistrés). Spec MCP
  « Authorization » (2025-06-18 et suivantes) : métadonnées de ressource protégée (RFC 9728), paramètre
  `resource` (RFC 8707), pas de transmission du jeton reçu.
- Le comportement du proxy est celui que consomme `client-mobile` :
  `Client/Mobile/src/app/core/auth/auth.service.ts` (`connectCiba`, `/auth/keycloak-exchange`, `/auth/refresh`) ;
  côté proxy, `D:\Workspaces\psc-auth-proxy\src\Api\Controllers\AuthController.cs` (`Connect`) et
  `TokenExchangeController.cs` (`KeycloakExchange`).
- En-têtes attendus par api-mail : `Client/Mobile/src/app/core/http/mss-headers.interceptor.ts` (`addHeaders`).
  api-mail tire le jeton PSC du proxy à partir du cookie : voir `Api/Mail/src/Application/Services/Psc/PscTokenProvider.cs`.
- Tests d'intégration : `WebApplicationFactory` du serveur MCP (vraie pile HTTP, DI, OpenIddict, stockage réel
  du serveur). Proxies et api-mail simulés (WireMock.Net) : ce sont les fournisseurs externes d'api-mcp.
  Client MCP de test : le client du SDK officiel.

## Branches
- `api-mcp` (pushed) : feat/task-478-mcp-messagerie-connexion-e-cps-et — https://github.com/codengine-technologies/HealthPlatform.Api.Mcp/tree/feat/task-478-mcp-messagerie-connexion-e-cps-et
- Pré-flight limité à `api-mcp` (champ **Pré-flight**, décision humaine du 2026-11-13) : `api-mail`, `client-mobile`, `dtos-mss` sur feat/task-466, ni contrôlés ni touchés.

## Develop log

- Repos touched : api-mcp (seul — pré-flight limité, décision humaine du 2026-11-13)
- DTOs published : no DTO change (api-mcp lit api-mail par des contrats locaux minimaux : un champ non déclaré n'est jamais relayé, en particulier l'INS de `MailDto`)
- Interop published : no interop change
- Commits (api-mcp, branche `feat/task-478-mcp-messagerie-connexion-e-cps-et`, poussée) :
  - `0397b4a` feat(mcp): serveur MCP messagerie — connexion CIBA e-CPS et lecture des en-têtes
  - `f8ec587` fix(mcp): versionne le dossier Tools, ignoré par la règle « tools/ » du .gitignore
  - `a2f459a` refactor(mcp): simplify pass (/simplify)
- Local build / test : ✓ `dotnet build` 0 erreur (TreatWarningsAsErrors), `dotnet test` 74/74 (12 tests d'intégration, 62 unitaires), total vérifié, aucun FATAL
- Migration (règle 7c) : `InitialCreate` relue — 6 tables créées (OpenIddict ×4, `doctor_grants`, `DataProtectionKeys`), 6 suppressions dans `Down`, `.Designer.cs` et snapshot présents, `has-pending-model-changes` : aucune dérive
- Passe qualité (/simplify) : 4 relectures (réutilisation, simplification, efficacité, altitude)
  - Applied & committed : api-mcp, 18 fichiers (`a2f459a`) — helpers HTTP partagés, scopes et GrantId en une définition, verrous de rafraîchissement en tableau fixe (fuite du dictionnaire statique), session gardée le temps de la requête, test d'existence sans déchiffrement, `PendingLogin` immuable, constantes du parcours de connexion
  - Re-validation : **rouge d'abord** — un remplacement global a rendu `AddSessionCookie` récursif (dépassement de pile, « Passed! 54/74 » + FATAL) ; corrigé, puis 74/74
  - Écartés (changeraient le comportement, laissés à /review) : purge des jetons OpenIddict et des `doctor_grants` révoqués ; `TaskCanceledException` du délai d'api-mail non traduite en erreur d'outil ; rafraîchissements concurrents sans double vérification ; en-têtes de la recherche lus en série ; double lecture de configuration (`Get<T>()` + `Configure<T>`), qui impose `UseSetting` dans la fixture
- Preuves rouges (règle 1b) — 20 mutations injectées dans le code de production, toutes **rouges**, restaurées, build final OK :

  | Mutation | Test d'intégration vu rouge |
  |---|---|
  | M01 challenge sans `resource_metadata` | `DiscoveryTests.PostMcp_WithoutToken_Returns401PointingToResourceMetadata` |
  | M02 `/mcp` sans autorisation | `DiscoveryTests.PostMcp_WithKeycloakTokenPresentedDirectly_Returns401` |
  | M03 PKCE `plain` annoncé | `DiscoveryTests.AuthorizationServerMetadata_AdvertisesS256Only_AndNoDynamicRegistration` |
  | M04 session du proxy non renouvelée après l'échange | `AuthorizationFlowTests.FullFlow_ListMailboxes_RelaysTheDoctorsOwnCredentialsToApiMail` |
  | M05 `code_verifier` non vérifié (handler OpenIddict retiré) | `AuthorizationFlowTests.RedeemCode_WithWrongCodeVerifier_ReturnsInvalidGrant` |
  | M06 identité non liée traitée en panne | `AuthorizationFlowTests.Login_WhenPscIdentityIsLinkedToNoAccount_ShowsFirstLoginMessage_AndIssuesNoCode` |
  | M07 refus e-CPS traité en panne | `AuthorizationFlowTests.Login_WhenTheDoctorRefusesOnThePhone_ShowsRefusal_AndIssuesNoCode` |
  | M08 URL de retour d'attaquant admise / M19 client inconnu admis | `AuthorizationFlowTests.Authorize_UnknownClientOrRedirect_IsRefusedWithoutRedirect` (les deux cas) |
  | M09 PKCE facultatif / M20 `plain` admis / M10 ressource étrangère admise | `AuthorizationFlowTests.Authorize_WithoutS256PkceOrForAnotherResource_IsRefusedWithoutRedirect` (les trois cas) |
  | M11 aucune limitation par RPPS | `AuthorizationFlowTests.Login_BeyondTheLimitForOneRpps_Returns429_AndSendsNoFurtherNotification` |
  | M12 rafraîchissement sans contrôle de la session du proxy | `AuthorizationFlowTests.Refresh_WhenTheProxySessionIsDead_ReturnsInvalidGrant_AndTheSessionCannotBeUsed` |
  | M13 jetons rafraîchis non enregistrés | `AuthorizationFlowTests.Refresh_WhenTheProxySessionIsAlive_IssuesNewTokens_AndRefreshesTheProxySession` |
  | M14 page des plus anciens | `MailToolsTests.ListMessages_ReturnsTheMostRecentHeaders_BoundedByThePageSize_WithoutContentOrIns` |
  | M15 extrait de recherche perdu | `MailToolsTests.SearchMessages_ReturnsHeadersAndExcerpts_ForTheHitsOfApiMail` |
  | M16 erreur technique relayée | `MailToolsTests.ApiMailRefusal_BecomesAToolError_WithoutTechnicalDetail` |
  | M17 écriture `status/read` ajoutée, garde de lecture seule retirée | `MailToolsTests.EveryTool_CallsOnlyReadRoutesOfApiMail` |
  | M18 jeton Keycloak journalisé | `MailToolsTests.DoctorCredentials_NeverAppearInTheMcpToken_TheToolResults_OrTheLogs` |

  La garde seule (sans retrait) est prouvée par le test unitaire `ReadOnlyGuardTests.EnsureAllowed_ThrowsBeforeAWriteLeaves`.
- DOD self-check : 15/15 items vérifiables par commande — tests nommés ci-dessus présents ; README (lancement, configuration, `claude mcp add --client-id … --callback-port …`, options vérifiées sur la CLI) ; configuration sans secret (`appsettings.Development.json` non versionné, exemple fourni). Manual Test Plan (e-CPS réelle, bac à sable PSC) : différé au test humain (HAG).
- Écart de taille : 46 fichiers dans la PR (repère de la règle 5 : ~30) — dépôt neuf, dont 3 fichiers de migration générés et 6 de configuration de solution.
- Green marked : api-mcp `a2f459a` (`Tools/green/green.py`)
- Amélioration continue :
  - Le `.gitignore` repris d'api-mail ignore `tools/`, et git ignore la casse sous Windows : `src/…/Tools/` n'était pas versionné (vu par les 4 relectures de la passe qualité). Corrigé par une réinclusion explicite.
  - Récidive « remplacement global → récursion » (task-349, task-478) : entrée `remplacement-global-recursion` ajoutée à `conventions/csharp.md`.
  - Python sous Windows : `subprocess.run(["bash", …])` lance le bash WSL de System32 (18 « BUILD KO » sans erreur de compilation) : consigné en mémoire de session.
- Next step : /review task-478 --code

## Code Review Summary

### Passage 1 (revue anticipée) — INTERROMPU (panne d'outillage, 2026-11-13)

Revue de code indépendante (étape 5) **non faite** : le relecteur (sous-agent) a échoué trois fois avant tout constat,
sur `API Error: 403 Attention Required! | Cloudflare (authentication_failed)`. Deux essais avec claude-opus-5-5, un avec
claude-sonnet-5-5. Aucun verdict n'est rendu. Voir `questions/task-478.md`.

Fait avant la panne :
- **4b** : non applicable, aucun parcours médecin sur `client-mobile` ni `client-angular`, aucun dépôt de voie touché.
- **4a (règle 1b)** : chaque comportement atteignable par un endpoint a un test d'intégration sur la vraie pile, avec sa
  preuve rouge par mutation (table M01 à M20 du `## Develop log`). Le contrôle a trouvé un trou : la borne de page de
  `list_messages` n'avait pas de preuve propre. **M21** (plafond retiré, `Math.Max(1, limit)`) a été ajoutée :
  `ListMessages_ReturnsTheMostRecentHeaders_BoundedByThePageSize_WithoutContentOrIns` passe **rouge**, et l'arbre est
  restauré à l'identique.

### Passage 2 (revue anticipée) — CHANGES REQUESTED (2026-11-13)

Relecteur indépendant (sous-agent, revue sur `a2f459a`) : 4 bloquants, 10 suggestions. Les codes d'api-mail et la nature
de l'extrait de recherche ont été vérifiés dans `Dtos/MailboxDto.cs` et `Dtos/SearchResultDto.cs`.

Vérifié sain : liste blanche des redirections, PKCE S256 seul, `returnUrl` borné, antiforgery, cookies (`mcp_pending`
Strict, identité de connexion à usage unique), aucun jeton du médecin dans le jeton MCP, garde de lecture seule
effective, HTML encodé et CSP à nonce, règle 14 (api-mail appelé avec les droits du médecin, liaison de session par
boîte active), rotation de la session du proxy suivie.

#### À corriger par la reprise

- **B1 — clé de chiffrement en clair à côté des jetons.** Le trousseau Data Protection est écrit dans la même base que
  les `doctor_grants`, sans protection. Correctif : `ProtectKeysWithCertificate`, obligatoire hors
  développement et tests (même garde que les certificats des jetons).
- **B2 — messages d'erreur sur des codes inventés.** `ToolErrors` cherche « OPERATOR », alors qu'api-mail renvoie
  `MAILBOX_ACCESS_REFUSED`. Le test unitaire stube un code qui n'existe pas. Correctif : correspondance exacte sur
  `MAILBOX_NOT_ATTACHED`, `MAILBOX_ACCESS_REFUSED`, `MAILBOX_PSC_SESSION_REQUIRED` (session expirée) et
  `MAILBOX_ACCESS_UNVERIFIED` (indisponible). Tests avec les codes réels, dont un en intégration, vus rouges.
- **B3 — extraits du contenu envoyés à l'assistant.** `search_messages` relaie `Excerpt` (jusqu'à 200 caractères du
  corps ou d'une pièce jointe), alors que l'US limite la v1 aux en-têtes et renvoie le contenu à task-479. Correctif :
  retirer l'extrait de la vue, de la description de l'outil et du test ; un test affirme son absence.
- **B4 — bornage de la recherche non prouvé.** Correctif : un test d'intégration qui demande plus que le plafond, lit
  `maxResults` plafonné dans la requête reçue par api-mail et au plus `MaxSearchResults` résultats dans la réponse, vu
  rouge par mutation.
- Corrigés dans la même passe (défauts réels, règles déjà tranchées) :
  - **S1** : le test de lecture seule se compare à `ApiMailRoutes.IsAllowed`, la fonction qu'il contrôle. Il faut une
    liste attendue écrite en dur dans le test, et affirmer que chaque appel d'outil réussit.
  - **S5** : le nom du dossier apparaît en clair dans les journaux (`AbsolutePath`) et dans le message de la garde. Il
    faut journaliser le gabarit de route, car un dossier peut nommer un patient.
  - **S6** : la page de connexion doit nommer le client IA et dire de ne continuer que si le médecin a lancé la
    connexion lui-même.
  - **S8** : un délai dépassé, un corps illisible ou une route refusée par la garde doivent donner le message
    « momentanément indisponible », pas l'erreur générique du SDK.
  - **S10** : la durée du jeton d'accès est à plafonner à 15 minutes (règle 7 de l'US) et le dossier virtuel des
    brouillons à retirer de `list_folders`.
  - **S4** : journaliser les jetons délivrés, rafraîchis et refusés, avec RPPS masqué, autorisation et `client_id`,
    comme le promet la section Conformité.
  - **S7** : affirmer en intégration que le code d'autorisation est à usage unique et que l'ancien jeton de
    rafraîchissement est refusé après rotation.

#### Arbitrage humain

- **S2 — mandataire inverse devant le serveur.** Sans `ForwardedHeaders`, le plafond par IP devient global derrière
  une entrée, et un TLS terminé en amont est refusé. La topologie de déploiement (entrée, proxies de confiance) n'est
  pas fixée. Recommandation : `UseForwardedHeaders` avec la liste des proxies de confiance en configuration, à décider
  avec le déploiement.
- **S3 — purge des sessions et des jetons.** Les `doctor_grants` non consommés ou expirés, et les jetons OpenIddict, ne
  sont jamais purgés. Recommandation : une task dédiée (échéance de la session alignée sur le jeton de
  rafraîchissement, et purge périodique).
- **S9 — performance sur une grosse boîte.** `list_messages` et `list_folders` lisent toutes les UID. Acceptable en v1,
  à mesurer sur une boîte de 10 000 messages.
- **Extrait de recherche (B3)** : s'il doit revenir, c'est avec task-479 (contenu tracé), après arbitrage DPO/RSSI.

## Timings

*(généré par `tools/timing/report.sh --task task-478 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 16 s | — | — | — | — |
| /develop | ok | 52 min 31 s | 38 (1 min 25 s) | 30 (6 min 49 s) | — | api-mcp 38B/30T |
| /review-code | changes | 8 min 57 s | — | — | — | reprise 1 |
| **Total cycle** | | **1 h 01 min** | **38 (1 min 25 s)** | **30 (6 min 49 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : restore ×3 (8.5 s)
