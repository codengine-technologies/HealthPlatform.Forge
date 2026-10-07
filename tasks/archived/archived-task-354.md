# todo-task-354.md — Remonter une connexion SMTP / IMAP après un refus du jeton PSC par la messagerie MSSanté

**Repos**: api-mail, client-mobile, client-angular
**Dependencies**: — (aucune)
**Epic**: E013
**Single frontend**: false
**Priorité**: **1** — un envoi de courrier médical échoue sans raison compréhensible, et un nouvel
essai immédiat échoue aussi, à coup sûr. Le praticien ne peut rien faire d'autre qu'attendre deux
à trois minutes sans savoir pourquoi.

> **Origine.** Constaté le 2026-10-05 dans Seq, entre 19:48 et 19:53 UTC (boîte de formation
> `robert.specialiste…@medecin.formation.mssante.fr`).
>
> - Deux envois successifs (`POST /drafts/{id}/send`, 19:48:59 et 19:49:35) sont refusés par le
>   serveur SMTP MSSanté. Il coupe la connexion après le challenge XOAUTH2 et renvoie
>   `{"status":"401","schemes":"bearer","scope":"mail"}` (en base64).
> - Le jeton refusé à 19:48:59 sortait d'un refresh PSC réussi 6 s plus tôt, sans erreur côté proxy.
> - Au second essai, api-mail **n'a même pas appelé le proxy** : il a ressorti de son cache le jeton
>   qu'on venait de lui refuser.
> - Les envois de 19:51:59 et 19:53:39 réussissent, uniquement parce que le cache a expiré entre-temps.
>   La navigation du praticien n'y est pour rien.
> - À la même période, l'opérateur était instable : `MOVE` répondu « Internal error », `AppendToSent`
>   à 8 s, lectures IMAP à 58 s. Un rejet transitoire côté opérateur est plausible, sans pouvoir être
>   prouvé : les logs ne portent aucune claim de jeton, par conception.
>
> Arbitrages de l'humain, le 2026-10-05 :
> - refus persistant après la reprise → **503 réessayable**, brouillon conservé ;
> - **SMTP et IMAP** traités dans la même US ;
> - **fronts mobile et Angular** inclus, avec un message dédié.

## Ce qui existe (constaté dans le code le 2026-10-05)

- **`SmtpConnectionFactory.AuthenticateAsync`** (`Api/Mail/src/Application/Services/Implementation/SmtpConnectionFactory.cs`)
  - Résout le jeton par `IPscTokenProvider.GetAccessTokenAsync`, puis s'authentifie en
    `SaslMechanismOAuth2NoIr`.
  - Le refus MSSanté n'arrive **pas** sous forme d'`AuthenticationException`, mais d'une
    `SmtpProtocolException` (« The SMTP server has unexpectedly disconnected: {base64} »).
  - Il tombe donc dans le `catch` générique (l. 261) → `Result.Error("SMTP connection failed: …")` →
    **502** côté client, sans aucune reprise.
- **`PscTokenProvider`** (`Api/Mail/src/Application/Services/Psc/PscTokenProvider.cs`)
  - Le jeton reste en cache jusqu'à `exp − TokenRefreshMarginSeconds` (30 s).
  - **Aucune API d'éviction** : un jeton que la messagerie vient de refuser est resservi tel quel
    jusqu'à son expiration.
- **`ImapConnectionService`** (`…/ImapConnectionService.cs`, l. 155 et 328-342)
  - Le refus IMAP sort bien en `AuthenticationException`, mais il est converti en
    `Result.Error(...)` **sans éviction ni reprise**.
  - Même défaut, sous une forme voisine : le jeton refusé est resservi à la connexion suivante.

## Objective

Quand la messagerie MSSanté refuse le jeton PSC à l'authentification (SMTP ou IMAP), api-mail
**remonte la connexion lui-même**, une fois, avec un jeton frais. Le praticien ne voit rien quand
la reprise réussit. Quand elle échoue, il voit un message clair, et son brouillon est intact.

1. **Détecter le refus du jeton**, sur les deux protocoles :
   - SMTP : la forme `SmtpProtocolException` + charge base64 `{"status":"401",…}` comme la forme
     `AuthenticationException` ;
   - IMAP : la forme `AuthenticationException` ;
   - seul un **refus du jeton** est concerné. Un échec réseau, TLS ou un timeout garde son traitement
     actuel.
2. **Évincer le jeton refusé** du cache de `PscTokenProvider` (session + sujet, portée RG-L1
   inchangée). Le prochain appel repasse obligatoirement par le proxy.
3. **Une seule reprise** :
   - nouvelle connexion, avec le jeton frais obtenu du proxy ;
   - jamais plus d'une reprise par opération, pour qu'une messagerie qui refuse tout ne provoque pas
     de rafale d'appels au proxy ni à PSC.
4. **Issue de la reprise** :
   - **la reprise réussit** → l'opération aboutit normalement (envoi parti, dossier lu) ;
   - **le proxy déclare la session PSC expirée** → comportement actuel inchangé, **401** « reconnectez-vous » ;
   - **le jeton frais est encore refusé** → **503** `ProblemDetails` (RFC 7807, règle 12) avec un code
     d'erreur dédié (ex. `mail-server-auth-refused`). `detail` : « La messagerie MSSanté a refusé
     la connexion. Réessayez dans quelques instants. » Jamais de 502, jamais le base64 ni le message
     MailKit brut dans le `detail`.
5. **Brouillon conservé** : un envoi refusé ne supprime ni n'altère le brouillon (vérifié par test).
6. **Fronts** (`client-mobile`, `client-angular`) — sur ce 503 d'envoi :
   - message dédié : « La messagerie MSSanté a refusé l'envoi. Votre brouillon est conservé,
     réessayez dans quelques instants. » ;
   - la rédaction reste ouverte avec son contenu ;
   - le bouton Envoyer reste actif pour un nouvel essai ;
   - les autres erreurs d'envoi gardent leur message actuel.

## Hors scope

- **La cause du refus côté opérateur.** Cette US rend api-mail résilient au refus, elle ne
  l'explique pas.
- **Le proxy PSC (`psc-auth-proxy`)** : aucun changement.
- **`client-blazor`** : non listé par arbitrage humain. Il reçoit le même 503 `ProblemDetails`,
  qu'il affiche avec son mapping générique.

## Definition of Done

- [ ] Build passes on every listed repo (0 errors)
- [ ] Tests pass on every listed repo (0 failures, hors rouges pré-existants identifiés sur `develop`)
- [ ] `IPscTokenProvider` expose l'éviction du jeton d'une session. Tests unitaires : l'éviction
      force un nouvel appel au proxy, et l'éviction d'une session ne touche pas une autre session ni
      un autre sujet (RG-L1).
- [ ] SMTP : tests unitaires de la détection du refus. Sont un refus du jeton :
      `SmtpProtocolException` + base64 `status 401`, et `AuthenticationException`. Ne le sont pas :
      une déconnexion sans charge 401, une `SocketException`, un timeout.
- [ ] SMTP : tests unitaires de la reprise :
  - une seule reprise, avec éviction préalable ;
  - jeton frais accepté → succès ;
  - jeton frais refusé → erreur typée 503 ;
  - session PSC expirée → 401 inchangé.
- [ ] IMAP : mêmes tests unitaires de détection et de reprise sur `ImapConnectionService`
- [ ] Test d'intégration de bout en bout pour `POST /api/v1/mail/drafts/{id}/send` (règle 1b), avec
      un serveur SMTP de test qui refuse XOAUTH2 en renvoyant la charge MSSanté réelle (`334` +
      base64 `{"status":"401",…}` puis déconnexion) et un proxy PSC simulé (fournisseur externe) :
  - nominal : le premier jeton est refusé, le second accepté → **200**, message reçu par le serveur
    de test, proxy appelé **exactement 2 fois** ;
  - échec : les deux jetons sont refusés → **503** `application/problem+json`, code d'erreur dédié lu
    dans la réponse, `detail` sans base64 ni message MailKit, proxy appelé exactement 2 fois,
    **brouillon toujours présent en base et inchangé** ;
  - vu rouge par mutation : sans l'éviction, le cas nominal échoue.
- [ ] Test d'intégration de bout en bout pour une route IMAP authentifiée (ex. `GET /api/v1/mail/folders`,
      avec la session IMAP absente du pool), avec un serveur IMAP de test qui refuse XOAUTH2 au
      premier jeton :
  - nominal → 200 et dossiers lus ;
  - échec (deux refus) → 503 `ProblemDetails` ;
  - vu rouge par mutation.
- [ ] `/send` ne répond plus jamais **502** sur un refus du jeton (assertion explicite dans le test
      d'intégration d'échec).
- [ ] client-mobile : test de composant de la rédaction sur le 503 d'envoi : message dédié affiché,
      contenu conservé, bouton Envoyer actif. Une autre erreur garde son message actuel.
- [ ] client-angular : même test de composant
- [ ] `data-testid` sur le message d'erreur d'envoi (mobile et Angular)
- [ ] Scénario **E2E-COMPOSE-003** v1 ajouté dans `Api/Mail/e2e/scenarios.yml` et implémenté dans
      chaque client où il est requis (`mobile: requis`, `angular: requis`). Titre : « Un envoi refusé
      par la messagerie laisse le brouillon intact et peut être renvoyé ». Le profil e2e doit
      pouvoir simuler le refus de l'opérateur au premier envoi : moyen technique au choix de
      `/develop`, sinon `questions/task-354.md`.
- [ ] Trou du filet : E2E-COMPOSE-003 prouvé rouge sur le bug non corrigé (envoi en échec générique),
      ligne ajoutée dans `conventions/e2e.md`.
- [ ] Évènements PGSSI-S journalisés :
  - refus du jeton par la messagerie (protocole, boîte, horodatage) ;
  - reprise tentée, et son issue (succès / échec) ;
  - via le journal d'audit existant (`AuditActionType`). Si un membre est ajouté, mettre à jour le
    miroir TS de `client-angular` (valeur explicite).
- [ ] Aucune donnée de santé en clair dans les logs, et **aucun jeton** : ni le jeton PSC, ni la
      charge base64 renvoyée par le serveur ne sont journalisés en entier. Le statut décodé seul est
      autorisé.

## Manual Test Plan

- **Lancer le backend** : `cd Api/Mail && dotnet run --project src/AppHost` (profil standard,
  boîte de formation MSSanté connectée par PSC).
- **Lancer le mobile** : `cd Client/Mobile && npm start` → http://localhost:4200, connexion PSC.
- **Lancer Angular** : `cd Client/Angular/front && npm start`, module MSS, connexion PSC.
- **Cas nominal (reprise invisible)** :
  1. Dans Seq, repérer l'expiration du jeton en cours. Ou, en local, forcer un refus au premier
     essai par la bascule de test fournie par `/develop` (documentée dans le `## Develop log`).
  2. Rédiger un message à soi-même et l'envoyer.
  3. Attendu : le message part et arrive dans la boîte de réception. Dans Seq, on voit un refus du
     jeton, une reprise, puis « Email sent successfully ». Aucune erreur à l'écran.
- **Cas d'échec (refus persistant)** :
  1. Forcer le refus des deux jetons (même bascule de test), puis envoyer.
  2. Attendu sur mobile et sur Angular : le message « La messagerie MSSanté a refusé l'envoi. Votre
     brouillon est conservé, réessayez dans quelques instants. »
  3. La rédaction reste ouverte avec son contenu, et le brouillon figure dans Brouillons.
  4. Lever la bascule, renvoyer : le message part.
- **IMAP** : forcer le refus au premier jeton, attendre la fin de la session IMAP (5 min) ou
  redémarrer l'API, puis ouvrir la boîte de réception. Attendu : les dossiers s'affichent, et Seq
  montre une reprise.
- **Contrôle des logs** : dans Seq, ni jeton, ni base64 complet, ni contenu de message sur ces
  évènements.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur. Robustesse technique d'un flux existant, aucune nouvelle
  fonctionnalité référencée.
- **Exigences DSR honorées** : non applicable, aucune exigence nouvelle. Les exigences MSSanté
  existantes sont conservées à l'identique :
  - authentification XOAUTH2 par jeton PSC ;
  - TLS conforme ANS (`TlsCipherSuiteValidator`) ;
  - contrôle de révocation OCSP/CRL.
- **INS** : non applicable. La reprise de connexion ne lit ni ne transmet d'identité patient.
  L'INS éventuellement présente dans les en-têtes du message envoyé est inchangée.
- **Authentification PS** : PSC (e-CPS), niveau eIDAS substantiel, inchangé. La reprise utilise
  **exclusivement** un jeton PSC frais obtenu du proxy. Aucun repli vers un mot de passe, aucune
  réutilisation d'un jeton refusé.
- **Habilitations** : inchangées. La liaison session ↔ sujet Keycloak (RG-L1) s'applique aussi à
  l'éviction.
- **Interop CI-SIS** : non applicable. Transport MSSanté existant, aucun document produit ou
  modifié.
- **Tracé PGSSI-S** : refus d'authentification par la messagerie, reprise tentée, et issue de la
  reprise. Journal d'audit en base, durée de conservation du journal d'audit existant (inchangée).
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui. Environnement de la plateforme inchangé, aucune nouvelle donnée stockée.
- **AIPD / impact RGPD** : inchangé. Aucun nouveau traitement : les évènements tracés sont des
  évènements d'authentification déjà couverts par le journal d'audit.

## Branches
- `api-mail` (pushed) : fix/task-354-reprise-refus-jeton-psc — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-354-reprise-refus-jeton-psc
- `client-mobile` (pushed) : fix/task-354-reprise-refus-jeton-psc — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/fix/task-354-reprise-refus-jeton-psc
- `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` (snapshot au /start : `feature/nova-rewriting-mss`) — humain gère branche, commit, push, PR TFS

## Develop log

- **Repos touchés** : `dtos-mss` (branche créée paresseusement, contrat d'audit), `api-mail`, `client-mobile`, `client-angular` (code-only, non commité).
- **DTOs publiés** : `HealthPlatform.Dtos.Mss` 517.0.0 → **521.0.0** (deux membres d'audit, ordinaux explicites : `MailServerTokenRefused = 39`, `MailServerAuthRetry = 40`). Consommateur bumpé : `api-mail` seul. `client-blazor` **non bumpé** : hors `**Repos**` (arbitrage humain), ajout d'enum additif sans effet de compilation ; son `AuditActionLabels.cs` n'aura pas de libellé pour ces deux actions tant qu'une task Blazor ne le reprend pas.
  - ⚠️ **Incident GitHub Actions** (« degraded availability », 2026-10-05, ~20:20 → 21:02 UTC) : le run CI 521 a été annulé deux fois sans obtenir de runner (aucune étape exécutée), relancé, vert au 3ᵉ essai. Pendant l'attente, le code a été compilé contre un paquet 521.0.0 empaqueté **localement depuis le même commit** (source NuGet temporaire, hors dépôt). Ce paquet a été purgé du cache, puis la solution restaurée depuis le flux GitHub (`.nupkg.metadata` : source `nuget.pkg.github.com`) et **re-validée** (build + suite complète) avant le commit.
- **`develop` d'api-mail ne compilait pas** (conflit sémantique task-341 / task-344). Le correctif PR #280 (ouverte, en attente de merge humain, 2 lignes de test) a été **fusionné dans la branche** (`git merge`, règle 4) pour pouvoir construire et tester. Son diff disparaît de la PR task-354 dès que #280 est mergée.

### Conception (api-mail)
- `MailServerTokenRefusal` (Session) : un refus du jeton = `MailKit.Security.AuthenticationException`, **ou** `SmtpProtocolException` dont la charge base64 finale décode en JSON `status: 401`. Forme réelle MSSanté reproduite par expérience (`334 <base64>` puis coupure → « The SMTP server has unexpectedly disconnected: eyJ… »). Jamais : déconnexion nue, socket, délai, rejet TLS (`System.Security.Authentication.AuthenticationException`, type distinct). La description journalisée porte le **statut décodé seul**.
- `IPscTokenProvider.EvictAccessToken` : retire le jeton du cache, portée RG-L1 (session + sujet), verdict de mode intact.
- `MailServerTokenRetry` (Psc) : orchestrateur commun SMTP / IMAP. Refus → trace `MailServerTokenRefused` + éviction → **une** reprise sur connexion neuve → trace `MailServerAuthRetry` (issue lue sur le `Result` réel) → second refus = éviction + `UnavailableException(MAIL_SERVER_AUTH_REFUSED)` → 503 `ProblemDetails`. Session PSC expirée à la reprise : 401 inchangé.
- `SmtpConnectionFactory` / `ImapConnectionService` : branchés sur l'orchestrateur pour les domaines OAuth2 seulement ; l'authentification par mot de passe garde son traitement.
- `DraftService` : ce 503 typé n'est plus replié en 502 ; il remonte, brouillon rendu à la rédaction, jamais supprimé.
- **Chemin jumeau** (consigne « un correctif vaut pour ses chemins jumeaux ») : `BackgroundImapService` évince aussi le jeton refusé (sans reprise : le cycle suivant la fait), sinon la synchro de fond resservait le même jeton.
- `AuditRetentionPolicy` : les deux actions sont **techniques** (365 j), comme `ConnectionError`.
- **Bascule de test du Manual Test Plan** — Development uniquement (câblée dans `Program` sous `IsDevelopment()`) : `PscProxy:Testing:ForcedTokenRefusals=N`. Pour les N premières authentifications du processus, un jeton inutilisable est présenté à la messagerie : c'est la **vraie** messagerie MSSanté qui refuse, et la **vraie** reprise qui s'exécute (le proxy est appelé comme en production).
  - Nominal : `N=1` (reprise invisible). Échec : `N=2` (503, puis l'envoi suivant part, le compteur étant consommé — c'est le « lever la bascule »).
  - Poser la variable `PscProxy__Testing__ForcedTokenRefusals=1` sur la ressource API de l'AppHost (ou dans un `appsettings.Development.json` local, non commité), puis redémarrer l'API.

### Commits
- dtos-mss : `8218593` feat(dto): audit des refus de jeton PSC par la messagerie et de la reprise
- api-mail : `05abd6a7` merge PR #280 (compilation de develop) ; `be001d51` bump DTO 521.0.0 ; `821ebe8c` fix(mail): reprise unique de la connexion SMTP/IMAP ; `80d6a9ce` lock files du bump
- client-mobile : `f9c3a89` fix(mobile): message dédié quand la messagerie refuse l'envoi, brouillon conservé
- client-angular (code-only, **non commité**, branche `feature/nova-rewriting-mss`) :
  - `front/libs/mss/src/core/utils/problem-details.utils.ts` (+ `.spec.ts`)
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose.component.ts` / `.html` / `.spec.ts`
  - `front/e2e/mss-e2e/specs/functional.e2e.ts` — ⚠️ **test du scénario requis E2E-COMPOSE-003 : à commiter sur TFS AVANT le merge de la PR api-mail** (convention `test-angular-non-commite`)
  - `front/libs/mss/src/core/models/audit.model.ts` (+ `audit.model.spec.ts`) — miroir TS des deux membres d'audit (39, 40, libellés). **Complément ajouté au moment de `/review`** : la clause de DOD « mettre à jour le miroir TS de client-angular » avait été oubliée par `/develop`. Build weda2 et `npm test` (11 projets) rejoués verts après l'ajout. Prévention : `agents/develop.md`, Step 2.
  - WIP humain préexistant laissé intact : `front/apps/mss/src/environments/environment.ts`, `front/apps/weda2/src/environments/environment.ts`

### Preuves (règle 1b, preuve par mutation)
- **Tests d'intégration** `MailServerTokenRefusalEndpointIntegrationTests`. Réel : pile HTTP, middleware PSC, `AddApplication`, `PscTokenProvider` et son cache, brouillons dans Redis (Testcontainers). Simulé (fournisseurs externes) : le proxy PSC (handler HTTP, nouveau jeton par appel, compté), l'opérateur MSSanté (serveurs TLS in-process SMTP `XOAuth2SmtpServer` et IMAP `MinimalTlsImapServer`, refus **par valeur de jeton**), OCSP.
  - `SendDraft_TheFirstTokenRefused_IsSentWithAFreshOne_AndTheProxyIsAskedExactlyTwice` : 200, message reçu, jetons présentés `[psc-token-1, psc-token-2]`, proxy ×2.
  - `SendDraft_BothTokensRefused_Is503ProblemJson_WithItsCode_AndTheDraftIsUntouched` : 503 `problem+json`, `code` lu, `detail` sans base64 ni MailKit, **≠ 502**, proxy ×2, brouillon relu dans Redis (scope neuf) inchangé et en rédaction.
  - `Quota_TheFirstTokenRefused_IsReadWithAFreshOne` (IMAP, `GET /api/v1/account/quota`, session absente du pool) : 200, `UsedBytes` lu ; `Quota_BothTokensRefused_Is503ProblemJson_WithItsCode`.
- **Mutations**, toutes rouges sur l'assertion prévue, puis restaurées (`cp` + `touch`) :
  - M1, éviction retirée de `MailServerTokenRetry` : les 4 tests d'intégration rouges (nominal : 503 au lieu de 200 ; échec : proxy ×1 au lieu de ×2), plus 7 tests unitaires.
  - M2, détection SMTP neutralisée (le code d'avant) : tests SMTP rouges en **502**, le bug d'origine reproduit.
  - M3, filtre de `DraftService` retiré : test d'échec rouge (502), plus `DraftServiceTests`.
  - M4, `EvictAccessToken` sans effet dans `PscTokenProvider` : 4 tests d'intégration et `EvictAccessToken_ForcesTheNextTokenThroughTheProxy` rouges.
  - Un premier essai de M1 (build en erreur) puis de M4 (projet d'intégration non recompilé) avait tourné sur l'ancien binaire : invalides, rejoués. Leçon consignée dans `conventions/e2e.md` (`mutation-non-servie`).
  - Mobile : chemin brouillon remis à `extractProblemDetail` → test de composant rouge (« Http failure response … 503 »).
  - Angular : message dédié neutralisé (`Date.now() < 0 && …`) → test de composant rendu rouge (« Erreur lors de l'envoi du message »).
- **E2E-COMPOSE-003** (catalogue v1, mobile et Angular requis) : vert sur les deux clients contre le backend e2e (`--serve-only`) ; **rouge** sous la mutation « message générique » sur les deux (mobile : « Http failure response for …/send: 503 Service Unavailable » ; Angular : « Erreur lors de l'envoi du message ») ; vert de nouveau après restauration (nouveau bundle attendu avant chaque passe). Le refus est simulé une fois à la frontière réseau du client, au contrat exact de l'API, car le backend e2e n'a pas de voie XOAUTH2 ; le renvoi passe par le vrai backend et le message est relu dans la boîte. Limite consignée : `conventions/e2e.md`, `refus-simule-a-la-frontiere`.
- **Journaux** contrôlés pendant les tests d'intégration : ni jeton, ni charge base64 ; le refus est journalisé par son statut décodé (« disconnected after the XOAUTH2 challenge, status 401 »).

### Passe qualité (/simplify)
- api-mail : contrôles mécaniques §Q 2b — **1 S125** attrapé avant commit (« … a registry ; »), corrigé, récidive comptée dans `conventions/csharp.md`. Un S3604 évité d'emblée (`ForcedTokenRefusalPscTokenProvider`, constructeur explicite). Revue reuse / simplification : un orchestrateur unique pour les deux protocoles, un détecteur unique ; aucun autre nettoyage.
- client-mobile : aucun nettoyage (3 fichiers de production).
- client-angular : aucun nettoyage ; `prettier --write` limité aux fichiers propres en HEAD (template et spec de rédaction formatés à la main).
- Ignorée (porteur de contrat) : dtos-mss.

### Reste connu (non bloquant)
- weda2 (`apps/weda2/.../error.interceptor.ts`, hôte, hors module MSS) affiche aussi son toast générique « Service temporairement indisponible » sur tout 5xx : le message dédié de la rédaction s'affiche **en plus**. Non modifié : hors périmètre MSS, arbre de l'humain.

### Validation locale (dernière, après restauration depuis le flux)
- dtos-mss : build ✓ ; CI run 521 ✓ (3ᵉ essai, incident GitHub)
- api-mail : build 0 erreur ; suite complète 6 439 tests, 0 échec (domain 190, infrastructure 683, application 3 544, api 1 173, intégration 829 + 16 ignorés préexistants)
- client-mobile : build ✓ ; 1 011/1 011 ✓ ; lint ciblé ✓ ; `tsc` e2e ✓
- client-angular : `npm run build` (weda2) ✓ ; `npm test` 11 projets ✓ (mss-lib 588) ; lint ciblé 0 erreur ; `tsc` e2e ✓
- DOD auto-contrôle : 15/15 critères outillés couverts (tests nommés ci-dessus) ; observation humaine des journaux Seq → HAG

- Next step : `/sonar task-354`

## Sonar log

- Mode A (chaîné), serveur SonarQube 9.9.8 (`sonar.login`), new code period : 30 jours.
- Phase 1 (new code) : ✓ Quality Gate OK, new_coverage = 97,6 % ; 1 itération.
- Phase 1 — Issues fixées : 1 (CA1859, smell, `SmtpConnectionFactoryTokenRefusalTests.MssanteRefusal` typé `SmtpProtocolException`).
- Phase 1 — Tests ajoutés : 8 (bascule de test : enregistrements instance / fabrique / type et « armée sans fournisseur » ; détection : charge JSON tableau, `status` objet, charge vide, message sans séparateur). Couverture new code : `MailServerTokenRefusal` 90,9 → 100 %, `ForcedTokenRefusalPscTokenProvider` 79,2 → 93,8 %, `MailServerTokenRetry` 100 %, `SmtpConnectionFactory` / `ImapConnectionService` / `DraftService` 100 %.
- Phase 1 — Constat restant, **hors code de la task** : S107 sur `SemanticSearchService.cs:395` (créé le 2026-10-02 par task-329), déjà présent dans la baseline et laissé par task-351, 352 et 353 pour le même motif.
- Phase 2 (legacy) : non jouée — les cibles projet sont déjà atteintes (0 bug, 0 vulnérabilité, A/A/A, couverture 97,9 % ≥ 95 %).
- Build / tests : ✓ verts (Release, 5 suites OpenCover : 190 + 3 552 + 683 + 1 173 + 829/16 ignorés).
- `conventions/csharp.md` : CA1859 → 7 occurrences.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 97,5 % | 97,6 % | +0,1 pt |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 13 | 13 | 0 |
| Coverage (projet) | 97,9 % | 97,9 % | 0 pt |
| Duplication | 0,4 % | 0,4 % | 0 pt |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

## Lint log

- Mode : A (chaîné). Branche Angular : `feature/nova-rewriting-mss` (code-only, aucun geste git hors `git fetch origin next`).
- Base : `origin/next` (rafraîchie). Portée lint : `tag:scope:mss` → projets `mss`, `mss-lib`, `mss-e2e`.
- Écart d'outillage constaté : `nx affected -t lint --projects=tag:scope:mss` a lancé 12 projets (le filtre n'est pas appliqué par `affected`), et un `--output-file` absolu est concaténé au répertoire de travail (ENOENT). Lint relancé par `nx run {projet}:lint` sur les trois projets MSS, sortie JSON en chemin relatif.
- Baseline : **0 erreur** (`mss` 0/0, `mss-lib` 0 erreur / 42 avertissements, `mss-e2e` 0 erreur / 38 avertissements). Aucun avertissement sur les lignes ajoutées par la task ; ceux des fichiers touchés sont antérieurs (`jsdoc/require-example` sur `problem-details.utils.ts` l.43 et 58, `max-lines` et `complexity` sur `mail-compose.component.ts`).
- Final : identique — lint clean, aucune correction, aucune itération.
- Build / tests : non rejoués (aucun fichier modifié depuis la validation de `/develop` : `npm run build` ✓, `npm test` 11 projets ✓).
- `conventions/angular.md` : rien à alimenter.

## Lint mobile log

- Branche : `fix/task-354-reprise-refus-jeton-psc` (arbre propre).
- Commandes : `npm run lint` (ng lint).
- Baseline : 0 erreur, 0 avertissement (« All files pass linting »). Le spec e2e modifié (`e2e/specs/functional.spec.ts`, hors cible `ng lint`) a été linté à part pendant `/develop` (`ESLINT_USE_FLAT_CONFIG=false npx eslint`) : propre.
- Itérations : 0 / 5 ; aucun commit de lint.
- Build / tests : non rejoués (aucune modification depuis la validation de `/develop` : build ✓, 1 011/1 011 ✓).

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail, client-mobile, dtos-mss touchés | ✅ verte | 31 verts, 0 flaky, 0 rouge, 0 quarantaine | 5 min 35 s |
| angular | api-mail, client-angular, dtos-mss touchés | ✅ verte | 31 verts, 0 flaky, 0 rouge, 0 quarantaine | 4 min 32 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ `fix/task-354-reprise-refus-jeton-psc` (ajout de **E2E-COMPOSE-003** v1, mobile et Angular requis)
- Quarantaines : aucune
- Divergences ouvertes : aucune
- Parcours touchés sans spec e2e modifié : aucun (les deux specs portent E2E-COMPOSE-003)
- Démontage : complet (ports libres, aucun conteneur e2e résiduel)
- ⚠️ Le test Angular d'E2E-COMPOSE-003 (`front/e2e/mss-e2e/specs/functional.e2e.ts`) est **non commité** (code-only) : à commiter sur TFS **avant** le merge de la PR api-mail, sinon toute task suivante bloquera sur `MissingRequired [angular] E2E-COMPOSE-003`.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 1 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 1 | headless | Créer puis supprimer un contact | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/43 — label `awaiting-human-merge`
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/281 — label `awaiting-human-merge` (embarque le correctif #280 tant qu'il n'est pas mergé)
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/89 — label `awaiting-human-merge`
- `client-angular` : code-only — humain gère commit/push TFS et ouverture PR. Branche `feature/nova-rewriting-mss`. Fichiers modifiés (`git diff --name-only`, dont 2 de WIP humain préexistant : `apps/*/environments/environment.ts`) :
  - `front/apps/mss/src/environments/environment.ts`
  - `front/apps/weda2/src/environments/environment.ts`
  - `front/e2e/mss-e2e/specs/functional.e2e.ts`
  - `front/libs/mss/src/core/models/audit.model.spec.ts`
  - `front/libs/mss/src/core/models/audit.model.ts`
  - `front/libs/mss/src/core/utils/problem-details.utils.spec.ts`
  - `front/libs/mss/src/core/utils/problem-details.utils.ts`
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose.component.html`
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose.component.ts`
  - ⚠️ **à commiter sur TFS AVANT le merge de la PR api-mail** : `front/e2e/mss-e2e/specs/functional.e2e.ts` (test du scénario requis E2E-COMPOSE-003).
- Ordre de merge : dtos-mss #43 (paquet 521.0.0 déjà publié), puis api-mail #281 (après #280, ou avec), puis client-mobile #89 ; Angular committé sur TFS avant api-mail.

## Code Review Summary

- **Verdict : APPROVED** — 0 bloquant, 3 suggestions.
- Validation `/review` (3ᵉ passe) : dtos-mss build ✓ ; api-mail build ✓ + 6 447 tests (190 / 683 / 3 552 / 1 173 / 829 + 16 ignorés) ✓ ; client-mobile build ✓ + 1 011/1 011 ✓ ; client-angular `npm ci` + `npm run build` ✓ + `npm test` 11 projets ✓.
- **DOD** : 16/16. Un point manquait à l'entrée de `/review` — le miroir TS des membres d'audit dans `client-angular` (`audit.model.ts`) — ajouté puis revalidé (build + tests Angular), prévention dans `agents/develop.md` Step 2.
- **Règle 1b** : comportement → test → preuve rouge (voir PR api-mail) — envoi de brouillon (reprise réussie / 503 typé, brouillon intact, jamais 502) et route IMAP `/account/quota`, prouvés par M1–M4.
- **E2E** : double verrou vert (31 + 31, parité verte, E2E-COMPOSE-003 ✅ des deux côtés).
- Suggestions : (1) IMAP — la fermeture de la connexion refusée précède la reprise hors du bloc qui reconnaît le refus : un socket déjà mort à cet instant rend l'erreur générique ; (2) le proxy PSC (hors scope) pourrait resservir le même jeton après éviction — la reprise échoue alors proprement en 503 ; (3) `client-blazor` non bumpé, sans libellé pour les deux actions d'audit.

## Timings

*(généré par `tools/timing/report.sh --task task-354 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 19 s | — | — | — | — |
| /develop | ok | 53 min 56 s | 8 (1 min 23 s) | 11 (5 min 33 s) | — | dtos-mss 1B/0T, api-mail 5B/7T, client-mobile 1B/1T, client-angular 1B/3T |
| /sonar | ok | 28 min 57 s | 2 (48 s) | 10 (8 min 08 s) | 4 (1 min 09 s) | 1 itération(s), api-mail 2B/10T |
| /lint-angular | ok | 1 min 30 s | — | — | — | lint clean (0 erreur sur mss, mss-lib, mss-e2e) |
| /lint-mobile | ok | 16 s | — | — | — | lint clean |
| /e2e | ok | 11 min 01 s | — | — | — | e2e ×3 (10 min 15 s), 2 voies vertes (31+31), porte verte |
| /review | ok | 7 min 34 s | 5 (41 s) | 4 (3 min 55 s) | — | dtos-mss 1B/0T, api-mail 1B/1T, client-mobile 1B/1T, client-angular 2B/2T |
| /tech-writer | ok | 2 min 08 s | — | — | — | — |
| **Total cycle** | | **1 h 45 min** | **15 (2 min 54 s)** | **25 (17 min 36 s)** | **4 (1 min 09 s)** | |

Autres commandes mesurées : lint ×5 (44 s), nuget-wait ×3 (41 min 43 s), restore ×3 (38 s)

## Merged

- **Date** : 2026-10-07 — `/merge task-354 --i-tested` (HAG attesté par l'humain)
- `dtos-mss` : PR #43 → squash `68eb85ff` (pas de CI déclenchée sur `develop` pour ce dépôt ; paquet 521.0.0 publié par la CI de la PR)
- `api-mail` : PR #281 → squash `b66dee8f` — CI `develop` ✓ https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/37662027481 (`develop` était rouge depuis #278 : le correctif #280 arrive avec ce squash)
- `client-mobile` : PR #89 → squash `ff75eb94` — CI `develop` ✓ https://github.com/codengine-technologies/HealthPlatform.Mobile/actions/runs/37662063480
- `client-angular` : géré manuellement par l'humain (TFS)
- Branches `fix/task-354-reprise-refus-jeton-psc` supprimées (distante et locale) sur les trois dépôts ; label `awaiting-human-merge` retiré.
- Staging : aucune branche staging (task lancée hors `/forge`).
- ⚠️ PR api-mail **#280** (`fix/task-344-develop-build`) reste ouverte : son contenu est désormais sur `develop` via #281. À fermer par l'humain.
