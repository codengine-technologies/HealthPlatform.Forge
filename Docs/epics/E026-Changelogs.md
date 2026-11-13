# E026 — Messagerie depuis un assistant IA (MCP) — Changelogs

> **Audience** : équipes techniques (ingénierie, backlog, dette)
> **Vue produit** : [E026-messagerie-depuis-un-assistant-ia-mcp.md](E026-messagerie-depuis-un-assistant-ia-mcp.md)
> **Dernière mise à jour** : 2026-11-13

---

## Historique détaillé des changelogs

### v0.1 — task-478 : serveur MCP, connexion e-CPS et lecture des en-têtes (api-mcp)

- **État** : `done` — PR ouverte, en attente du merge humain (HAG).
- **PR** : api-mcp [#1](https://github.com/codengine-technologies/HealthPlatform.Api.Mcp/pull/1), label
  `awaiting-human-merge`, head `5a07884`. Nouveau dépôt `HealthPlatform.Api.Mcp` (`Api/Mcp`). Aucun NuGet publié :
  api-mail est lu par des contrats locaux minimaux (`ApiMail/ApiMailContracts.cs`).
- **Pile** : .NET 10 ; `ModelContextProtocol.AspNetCore` 2.3.1, en transport Streamable HTTP sans état ; OpenIddict
  7.7.2 (serveur et validation locale) ; EF Core + Npgsql ; Data Protection persistée en base et chiffrée par
  certificat.
- **Authentification** :
  - CIBA via psc-auth-proxy : `POST {Ciba}/auth/connect`, puis `POST {Auth}/auth/keycloak-exchange` (rotation du
    `proxy_session_id`), puis `POST {Auth}/auth/refresh`.
  - Jeton Keycloak et session du proxy chiffrés dans `doctor_grants`.
  - Code + PKCE S256 seul ; clients pré-enregistrés (`Mcp:Clients`), aucun `registration_endpoint`.
  - Ressource RFC 8707 `{PublicBaseUrl}/mcp`, métadonnées RFC 9728 servies par le handler `AddMcp`.
  - Jeton d'accès de 15 min au plus ; rotation stricte du rafraîchissement (`RefreshTokenReuseLeeway = 0`).
  - Limitation CIBA par RPPS et par IP (`CibaThrottle`).
- **Outils** : `list_mailboxes`, `list_folders`, `list_messages`, `search_messages`.
  - Liste blanche de routes api-mail (`ApiMailRoutes`, `ReadOnlyGuardHandler`).
  - Erreurs ProblemDetails traduites sur les codes réels de `MailboxErrorCodes`.
- **Tests** : 91/91. Dont tests d'intégration WebApplicationFactory + PostgreSQL Testcontainers + WireMock (proxy,
  api-mail), avec un certificat de test (chemin de production). 26 mutations de preuve, toutes rouges. Migration
  `InitialCreate` auditée (règle 7c).
- **Revue** :
  - passage 1 interrompu (403 de l'API sur les sous-agents) ;
  - passage 2 CHANGES REQUESTED (B1 trousseau en clair, B2 codes inventés, B3 extrait relayé, B4 borne non prouvée) ;
  - reprise 1 ;
  - passage 3 APPROVED à `5a07884`.
- **Défauts trouvés en route** :
  - `tools/` du `.gitignore` (repris d'api-mail) excluait `src/…/Tools/` sous Windows ;
  - une récursion `AddSessionCookie` née d'un remplacement global (consigne `remplacement-global-recursion`).
- **Ouvert** :
  - arbitrage N1 (rotation stricte) ;
  - S2 (`ForwardedHeaders`), S3 (purge des sessions et des jetons), S9 (performance sur une grosse boîte) ;
  - suggestions N2 (journal des refus OpenIddict), N3 (`/login` avec client inconnu), N4 (rotation du certificat) ;
  - arbitrage DPO / RSSI avant toute production.
- **Plan de contrôle** : `api-mcp` est enregistré dans `CLAUDE.md` et les playbooks, avec l'exception « pré-flight
  limité aux Repos ». Non poussé, en attente de relecture humaine.

### v0.2 — task-478 : choix du canal CIBA, application e-CPS ou carte CPS (api-mcp)

- **État** : `done` — évolution demandée par l'humain avant le merge, sur la même PR
  [#1](https://github.com/codengine-technologies/HealthPlatform.Api.Mcp/pull/1) (head `b89db38`, corps mis à jour).
- **Contenu** :
  - page de connexion à boutons radio `MOBILE` (par défaut) et `CARD`, transmis à `POST {Ciba}/auth/connect` ;
  - `Proxy:AllowedChannels`, liste vide = les deux (vide par défaut, à cause du binder qui ajoute aux listes
    remplies) ;
  - `ProxyOptions.Canonical` ignore la casse ; `ChannelConfigurationErrors` arrête le démarrage sur une valeur
    inconnue ;
  - page d'attente et messages d'échec selon le canal (`PendingLogin.Channel`).
- **Tests** : 108/108. `CibaChannelTests`, dont un hôte dérivé restreint à MOBILE et un hôte « CARTE » qui ne démarre
  pas ; `ChannelChoiceTests`. Mutations M27 à M33, toutes rouges.
- **Revue** :
  - passage 4 CHANGES REQUESTED (B1 : restriction par configuration non prouvée ; S1 à S3) ;
  - reprise 2 ;
  - passage 5 APPROVED à `b89db38`.
- **Incident** : un vert marqué sur une suite rouge (un `grep` dans une chaîne `&&`), corrigé.
  - Cause du rouge : un test qui laissait sa connexion CIBA tourner en arrière-plan.
  - Consigne ajoutée : `travail-de-fond-attendu` (`conventions/csharp.md`).
  - Mémoire de session ajoutée.
- **Ouvert** : suggestions du passage 5, à savoir un test de `/login/complete` en CARD, et le commentaire XML
  d'`AllowedChannels`, périmé.

---

## Annexe A — Cartographie des briques applicatives

| Brique | Rôle |
|---|---|
| `Authorization/` (`AuthorizationEndpoints`, `StartupInitializer`, `McpClaims`) | Endpoints OAuth en mode passthrough, synchronisation des clients, scopes |
| `Login/` (`CibaLoginService`, `CibaThrottle`, `LoginEndpoints`, `LoginPages`) | Page de connexion, CIBA en arrière-plan, limitation |
| `Proxy/PscProxyClient` | Client de psc-auth-proxy (connect, échange, rafraîchissement) |
| `Grants/` (`DoctorGrantStore`, `DoctorSessionProvider`) | Sessions des médecins chiffrées, rafraîchissement, révocation |
| `ApiMail/` (`ApiMailClient`, `ApiMailRoutes`, `ApiMailContracts`) | Lecture d'api-mail avec les droits du médecin, liste blanche |
| `Tools/` (`MailTools`, `ToolViews`, `ToolErrors`) | Outils MCP, projections, messages d'erreur |
| `Persistence/` (`McpDbContext`, migration `InitialCreate`) | OpenIddict, `doctor_grants`, `DataProtectionKeys` |

---

## Annexe B — Inventaire fonctionnel (2026-11-13)

- 4 outils MCP, tous en lecture seule.
- 2 projets : serveur et tests.
- 108 tests, dont 35 méthodes de test d'intégration (cas de théorie comptés une fois).
- 2 moyens de validation : application e-CPS, carte CPS.

---

## Annexe C — Tasks ayant contribué à cet EPIC

| Task | Contribution | État |
|---|---|---|
| task-478 | Serveur MCP : connexion CIBA e-CPS, serveur d'autorisation, quatre outils de lecture des en-têtes | done (PR #1) |
| task-479 | Lecture du contenu d'un message, tracée au nom du médecin, jamais marqué lu (api-mail + api-mcp) | todo (attend task-466) |
