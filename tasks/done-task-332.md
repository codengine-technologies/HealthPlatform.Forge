# todo-task-332.md — Les messages internes de la plateforme ne transportent plus aucun secret : ni mot de passe de base, ni jeton, ni session PSC

**Repos**: api-mail
**Dependencies**: — (aucune)
**Epic**: E016
**Single frontend**: true
**Priorité**: **1** — chaque message RabbitMQ contient la **chaîne de connexion Postgres** (mot de passe), le **jeton Keycloak**, le mot de passe IMAP et la **session du proxy PSC** du praticien ; ils sont stockés dans des files durables, visibles en console d'administration et conservés indéfiniment dans les files d'erreur.

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, **AUD-10**, contre-vérifié).

## Ce qui est établi (develop @ `14d58398`, **re-vérifié le 2026-10-13 sur develop @ `87e972a5`**)

> **Re-vérification du 2026-10-13** : 43 commits plus tard, dont task-334, task-342, task-344 et
> task-325, **le défaut est intact**. Les trois messages portent toujours le `UserContextInfo` complet,
> et `UserContextInfo` n'a toujours aucun `[JsonIgnore]`. Seuls les points de publication ont bougé
> (corrigés ci-dessous). Les numéros de ligne de `UserContextInfo.cs` sont inchangés.

- `Application/Messages/AddNewMailMessage.cs:14` : `public required UserContextInfo UserContext` —
  l'objet **complet**, sérialisé par System.Text.Json ; même chose pour
  `CreatePatientContactMessage` et `CreatePractitionerContactMessage` (`:8`). Publiés par
  `EnrichedMailPersistence.cs:240` (`AddNewMailMessage`, `UserContext = userContextInfo`),
  `PatientContactPublisher.cs:38` et `PractitionerContactPublisher.cs:46`.
  *(Le 2026-09-27, la publication de `AddNewMailMessage` se faisait dans `BackgroundEnrichmentProcessor.cs:362`
  et `ImapService.cs:4673`. Depuis task-334 et task-344, elle passe par `EnrichedMailPersistence`.)*
- `Domain/Entities/MailDb/UserContextInfo.cs` : **aucun `[JsonIgnore]`** ; porte `ConnectionStringServer`
  (`:104`), `ConnectionStringDirect` (`:117`) et les chaînes calculées qui en dérivent, `KeycloakToken` (`:73`),
  `Password` (`:101`), `ProxySessionId` (`:48`, qui permet d'obtenir un jeton PSC auprès du proxy).
- **Côté consommateur, le contexte est réhydraté par `UserContextInfo.CopyIdentityTo`** (task-234) :
  `AddNewMailConsumer.cs:171`, et `ConfigureUserContext` dans `CreatePatientContactConsumer.cs:33` et
  `CreatePractitionerContactConsumer.cs:35`. Cette copie recopie **aussi** les secrets (`:206-217`), et un
  test par réflexion impose qu'elle reste le miroir exact de `Reset()`. Le scan
  `tests/mss.mail.api.tests/Architecture/UserContextIdentityCopyScanTests.cs` (task-334) interdit la
  copie champ par champ. **Le contrat minimal doit donc passer par une réhydratation dédiée, sans
  casser ces deux garde-fous.** Il ne doit pas non plus perdre `MssRpps` : c'est la leçon de task-234,
  sans le RPPS le consommateur construit le nom d'une **autre base**, en silence.
- `IUserScopedMessage` (`Application/Messages/IUserScopedMessage.cs`) type sa propriété en
  `UserContextInfo`. Le filtre `UserContextLogEnricherFilter.cs:26` n'en lit que l'`Email`. **L'interface
  change donc avec le contrat.**
- Les consommateurs n'utilisent que quelques champs d'identité (e-mail, RPPS, contexte de base). Aucun
  fichier de `Application/Consumers/` ne lit `KeycloakToken`, `ProxySessionId` ni `Password` directement.
  Ces champs n'y arrivent que par la copie ci-dessus, et leurs usages en aval restent à vérifier
  (périmètre §2).
- `AddNewMailMessage` transporte en outre le **corps** du mail (`Body`) et son sujet.
  **Élément nouveau pour le §3** : depuis task-344, `AiTaggingRecoveryService.cs:92` reconstruit la même
  matière d'étiquetage **depuis la base** (`candidate.Body` / `BodyHtml`, via `AiTaggingMaterial`). Le
  consommateur peut donc relire le contenu au lieu de le recevoir, et le chemin existe déjà.
- Au passage : le spill d'audit Redis (`RedisAuditSpillStore.cs:76` et `:97`, sérialisation du
  `MssAuditTrace` entier) emporte encore `TransportConnectionStringServer` / `TransportConnectionStringDirect`.
  Elles sont toujours renseignées par `AuditService.cs:101-102`, mais **aucun code de `src/` ne les relit** :
  elles sont inutiles depuis task-312. Deux tests y font encore référence et seront à ajuster :
  `AuditBackgroundServiceBatchingTests.cs:85` et `AuditBackgroundServiceFallbackTests.cs:113-114`.

## Objective

Qu'**aucun secret** (mot de passe, chaîne de connexion, jeton, identifiant de session) ne quitte le
processus API par le bus ou par le spill d'audit ; que les messages ne portent que ce dont le
consommateur a besoin pour retrouver son contexte, les secrets étant résolus **côté consommateur**.

### Périmètre

1. **Contrat de message minimal** pour les trois messages : identité nécessaire (e-mail de la boîte,
   RPPS, tenant, nom de base **enregistré**) — sans chaîne de connexion, jeton, mot de passe ni session.
2. **Résolution côté consommateur** : la chaîne de connexion est reconstruite à partir de la
   configuration de la plateforme et du nom de base enregistré ; aucun consommateur n'a besoin d'un
   jeton (vérifier et documenter chaque usage).
3. **Corps du mail** : évaluer si le consommateur peut relire le contenu depuis la base au lieu de le
   recevoir ; si le corps reste nécessaire dans le message, le justifier dans le task file.
4. **Garde-fou** : un test d'architecture qui échoue si un type publié sur le bus expose une propriété
   de secret (chaîne de connexion, jeton, mot de passe, session).
5. **Spill d'audit Redis** : retrait des chaînes de transport inutiles.
6. **Messages déjà en file** au déploiement : le consommateur accepte l'ancien et le nouveau format
   pendant la transition, ou la procédure de vidange est documentée.

### Hors périmètre

- La purge des files `_error` existantes et la rotation des secrets déjà exposés : **actions humaines**,
  à décrire dans le task file (quelles files, quels secrets à faire tourner).
- La copie d'identité en tâche de fond (task-334, **mergée et archivée** ; ses garde-fous sont à respecter, voir plus haut).

## Definition of Done

- [ ] Build passes (0 errors) — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] **Test rouge d'abord** (log du run rouge dans le task file) : sérialiser un `AddNewMailMessage` construit avec un contexte complet →
      sur le code actuel le JSON **contient** la chaîne de connexion, le jeton et la session PSC ; après correctif, aucun
- [ ] Même vérification pour `CreatePatientContactMessage` et `CreatePractitionerContactMessage`
- [ ] Test d'architecture : aucun type publié sur le bus n'expose de propriété de secret
- [ ] Tests des trois consommateurs : ils retrouvent leur contexte (bonne base, bon tenant) à partir du message minimal
- [ ] Test : un message à l'ancien format (déjà en file) est traité ou rejeté proprement selon la stratégie retenue
- [ ] Spill d'audit Redis : les chaînes de transport ne sont plus sérialisées (test)
- [ ] Procédure humaine rédigée dans le task file : files à purger, secrets à faire tourner
- [ ] Aucune donnée de santé ni secret dans les logs

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` ; ouvrir la console RabbitMQ de l'AppHost.
2. Recevoir un mail de test (corpus du banc) et déclencher son enrichissement.
3. Dans la console RabbitMQ, lire un message `AddNewMailMessage` (file de test, ou `_error` après une panne simulée du consommateur) → **Attendu** : ni `ConnectionString`, ni `KeycloakToken`, ni `ProxySessionId`, ni `Password`. Avant : tous présents en clair.
4. Vérifier que le traitement aval a bien eu lieu (tags, embedding, contacts) dans la bonne base.
5. Humain : appliquer la procédure de purge des files `_error` et de rotation des secrets sur les environnements concernés.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — sécurité de la plateforme
- **Exigences DSR honorées** : non applicable — PGSSI-S (protection des secrets et des moyens d'authentification)
- **INS** : non applicable — aucun trait d'identité ajouté ; le corps de mail éventuellement retiré du message réduit la circulation de données de santé
- **Authentification PS** : PSC / e-CPS inchangée ; la session PSC et le jeton Keycloak cessent de circuler hors du processus
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé ; la rotation des secrets exposés est tracée par l'exploitation
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — le bus RabbitMQ fait partie du périmètre HDS ; la US réduit les données sensibles qui y transitent
- **AIPD / impact RGPD** : à informer le DPO — secrets et contenus exposés dans des files durables avant correctif

## Branches
- `api-mail` (pushed) : fix/task-332-bus-messages-without-secrets — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-332-bus-messages-without-secrets

## Corps du mail — décision (périmètre §3)

**Retiré du message, avec l'objet.** Le consommateur `AddNewMailConsumer` relit l'objet et le corps
dans la base du praticien (`IMailRepository.GetAiMaterialAsync`, même projection que la reprise des
étiquetages de task-344, `AiTaggingCandidate`). Ce n'est possible que parce que la publication suit
l'écriture : `EnrichedMailPersistence.AfterWriteAsync` publie après `AddNewMail`, la ligne de contenu
existe donc toujours au moment où le message est consommé.

- Un mail disparu entre la publication et la consommation (mis à la Corbeille, par exemple) n'a plus
  de matière : le consommateur journalise un avertissement et acquitte, **sans appel au modèle** et sans
  trois essais voués à l'échec.
- La matière n'est chargée que si l'embedding ou l'étiquetage est actif : avec les deux sous-flags
  éteints, aucune lecture en base.
- Restent dans `AddNewMailMessage` : l'identifiant du mail, son dossier, son UID, l'adresse de
  l'expéditeur (une adresse professionnelle), le type de document et le drapeau « documents médicaux ».

**Ce qui reste sur le bus, hors périmètre** : `CreatePatientContactMessage` porte toujours les traits
du patient extraits du CDA (INS, nom, prénom, naissance, téléphones, adresse). C'est la matière même du
contact à créer. Le retirer demanderait au consommateur de relire le document médical en base. Ce serait
une US à part entière, à arbitrer par l'humain si la présence de l'INS dans une file durable est jugée
inacceptable.

## Procédure humaine — après le merge et le déploiement

> La forge ne touche ni aux files ni aux secrets d'un environnement. Ces gestes sont ceux de
> l'exploitation, sur **chaque** environnement où api-mail a tourné avec un bus (Staging, Production,
> weda-dev, postes de développement avec RabbitMQ partagé).

**1. Laisser se vider les files actives, sans les purger.** Le nouveau consommateur accepte l'ancien
format : la propriété `userContext` garde son nom, ses champs secrets sont ignorés à la
désérialisation, et le contexte est reconstruit depuis la configuration du processus (prouvé par
`AMessageAtTheFormerFormat_StillInTheQueue_IsProcessedInThePractitionersDatabase_IgnoringItsSecrets`).
Aucune perte de traitement au déploiement.

**2. Purger les files d'erreur et de rebut**, qui conservent indéfiniment les messages à l'ancien
format, secrets compris :

| File | Contenu exposé |
|---|---|
| `add-new-mail-queue_error`, `add-new-mail-queue_skipped` | contexte complet + objet + corps du mail |
| `create-practitioner-contact-queue_error`, `create-practitioner-contact-queue_skipped` | contexte complet |
| `create-patient-contact-queue_error`, `create-patient-contact-queue_skipped` | contexte complet + traits patient (INS) |

Avant la purge, exporter si besoin l'**inventaire** des messages (identifiants, dates, adresse de boîte)
pour la notification au DPO, **jamais** leur contenu. Après la purge, `rabbitmqctl list_queues name
messages` doit rendre 0 sur ces six files.

**3. Faire tourner les secrets exposés**, en partant du principe qu'une file d'erreur non vide en a
contenu :

| Secret | Où il vit | Action |
|---|---|---|
| Mot de passe du rôle PostgreSQL de la plateforme | `MSS-MAIL-CONNECTIONSTRING` (et `-DIRECT` si un pooler est en place) | **Rotation obligatoire** : nouveau mot de passe du rôle, mise à jour des deux variables, redémarrage des réplicas |
| Mots de passe IMAP des praticiens (`Password`) | renseigné pour les boîtes authentifiées par mot de passe | Inviter les praticiens concernés, identifiés par l'inventaire de l'étape 2, à changer leur mot de passe de messagerie |
| Sessions du proxy PSC (`ProxySessionId`) | cookie `proxy_session_id`, sessions tenues par psc-auth-proxy | Révoquer les sessions de l'inventaire, ou attendre leur expiration naturelle si elle est plus courte que le délai de purge |
| Jetons Keycloak (`KeycloakToken`) | jetons d'accès, durée de vie de quelques minutes | Aucune action : expirés. Les jetons de rafraîchissement n'ont jamais transité |

**4. Informer le DPO** (AIPD) : secrets et contenus cliniques dans des files durables avant correctif,
avec l'inventaire de l'étape 2.

## Develop log

- Repos touched : api-mail (`fix/task-332-bus-messages-without-secrets`)
- DTOs published : no DTO change (`dtos-mss` non touché, aucune branche créée)
- Interop published : no interop change
- Commits (api-mail) :
  - `30371c48` refactor(audit): an audit trace no longer takes the practitioner's connection strings
  - `211d236b` fix(mail): bus messages carry no secret, nor the mail's body
  - `fe3951ec` refactor(mail): simplify pass (/simplify)
- Local build / test : ✓ 0 erreur, **6 568 tests verts, 0 échec** (domain 195, infrastructure 683,
  application 3 624, api 1 201, integration 865 + 16 ignorés pré-existants), joués deux fois : après la
  feature, puis après la passe qualité.
- **Contrat retenu** : `MessageUserIdentity` (Domain) = e-mail, RPPS, tenant, nom de base enregistré.
  Reconstruit côté consommateur par `UserContextInfo.RestoreFromMessage`, qui repart de `Reset()` et prend
  les chaînes de connexion de `IServerConnectionStrings`. Cette interface (Application) est implémentée par
  `ServerConnectionString` (Api) et enregistrée comme la même instance que celle du middleware. La propriété
  garde le nom `UserContext` : les messages à l'ancien format restent désérialisables.
- **Aucun consommateur n'a besoin d'un jeton** (§2, vérifié) : les trois consommateurs lisent et écrivent la
  base du praticien et appellent le fournisseur d'IA. Aucun ne touche IMAP ni SMTP, ni `IPscTokenProvider`.
  L'audit émis depuis ces scopes perd `UserSessionId` (`ClientSessionId` ne voyage plus) : il trace sous la
  boîte et le tenant, comme toute tâche de fond.
- **Preuve rouge d'abord** : `BusMessageSecretsTests`, 4 tests rouges sur le code d'avant (secrets et corps
  présents dans le JSON MassTransit des trois messages), verts après. Le 5ᵉ, qui vérifie l'identité restante,
  était vert dès le départ, comme prévu.
- **Test d'intégration (règle 1b)** : `BusMessageMinimalIdentityEndToEndTests`, dont la chaîne est la
  suivante :
  1. le vrai publieur part d'un contexte de requête complet, dont la chaîne serveur désigne un hôte
     **injoignable** ;
  2. le message passe par le JSON MassTransit ;
  3. le vrai `AddNewMailConsumer` travaille dans un vrai conteneur, sur une vraie base PostgreSQL ;
  4. les messages de contact qu'il publie repassent par le fil ;
  5. les vrais consommateurs de contact les traitent.

  Le test lit l'embedding, l'étiquette, le contact praticien, le contact patient et le lien document → contact,
  dans la base du praticien. Le cas « ancien format encore en file » est couvert par le second test.
- **Mutations vues rouges** (copie avant mutation, restauration depuis la copie, `git diff --stat` relu) :
  - M1, `RestoreFromMessage` oublie `RegisteredDatabaseName` : 2 tests d'intégration et 2 tests de domaine
    rouges (autre base, matière introuvable).
  - M2, l'embedding n'utilise plus le corps relu : intégration et `Consume_EmbedsAndTagsTheMaterialReadBackFromTheDatabase`
    rouges sur l'appel attendu au fournisseur.
  - M3, `ToMessageIdentity` perd le tenant : intégration rouge (`Expected 0192f0a4-… / Actual null`) et
    `BusMessageSecretsTests…StillCarriesTheIdentity` rouge.
  - M4, un message réembarque un `UserContextInfo` imbriqué : `BusMessageSecretPropertyTests` rouge, qui liste
    `Legacy.ProxySessionId`, `.KeycloakToken`, `.Password`, `.ConnectionStringServer`…
  - M5, la trace d'audit reprend la chaîne serveur derrière `[JsonIgnore]` :
    `The_trace_never_carries_the_connection_strings_of_its_context` rouge.
- **Spill d'audit (§5)** : l'audit du 2026-09-27 disait que le spill « sérialise encore » les chaînes de
  transport. C'est **inexact sur develop** : elles portaient `[JsonIgnore]` depuis task-292, et une trace
  rejouée n'en contenait aucune. Elles restaient en revanche copiées sur chaque trace en mémoire, sans
  lecteur depuis task-312. Elles sont retirées de la trace.
  - `AuditSpillIntegrationTests` prouve désormais de bout en bout, sur un vrai Redis, qu'un contexte qui
    porte les deux chaînes (mots de passe compris) n'en laisse aucune dans le spill.
  - Le test qui exigeait la présence de la route directe sur la trace (task-292, caduc depuis task-312)
    est remplacé par son inverse.
- **Corps du mail (§3)** : retiré, avec l'objet. Voir la section « Corps du mail — décision ».
- Contrôles mécaniques §Q 2b : S125 ×5 relevés puis réécrits avant le commit (compteur porté à 17 dans
  `conventions/csharp.md`) ; xUnit1045, S4457, xUnit2032 : rien.
- Passe qualité (/simplify) :
  - Applied & committed : api-mail, 4 fichiers (`fe3951ec`). Conversion HTML → texte faite une seule fois
    pour les deux étapes. Suppression des trois enveloppes `ConfigureUserContext`, qui ne faisaient que
    déléguer. Retrait d'un commentaire-pierre tombale dans `MssAuditTrace`.
  - Écartés, car ils changent le comportement ou sortent du diff :
    - réduire `AddNewMailMessage` à `MailId` et à l'identité, en lisant dossier, UID, expéditeur et type
      de document en base (changement de contrat) ;
    - partager `AiTaggingRecoveryService.ToRequest` (même raison) ;
    - requête dédiée plus légère que la projection partagée ;
    - flags lus en parallèle.
  - **Piste d'altitude à arbitrer, hors de cette task** : `UserContextInfo` reste un sac à secrets, et
    seuls la convention et le test d'architecture empêchent qu'il revoyage. La correction de fond serait
    que les dépôts lisent les chaînes de connexion dans `IServerConnectionStrings` au lieu du contexte
    praticien. Cela toucherait `BaseRepository`, le middleware et `RequestHelper`, ce dernier lisant
    encore l'environnement directement.
  - Skipped (contract/excluded) : dtos-mss, interop-cda, sdk, devops, psc-proxy-*.
- **Taille de PR** : 44 fichiers, au-delà du repère de ~30. 26 sont des tests existants adaptés au nouveau
  contrat de message, que le compilateur impose tous. Découper ferait merger un contrat à moitié migré
  (règle 11).
- DOD self-check : 10/10 critères vérifiables par commande couverts (build, tests, rouge d'abord, trois
  messages, test d'architecture, trois consommateurs, ancien format, spill, procédure humaine, logs sans
  secret). Points 3–4 du plan de test manuel (console RabbitMQ, traitement aval réel) : deferred to manual
  test (HAG).
- Next step : /sonar task-332

## Sonar log

- Serveur SonarQube 25.6.0.109173 (`sonar.token`), port 9001 mesuré. Conteneurs `sonarqube_db` puis
  `sonarqube` redémarrés (arrêtés depuis 8 jours).
- Analyse complète de la branche au commit `fe3951ec` : begin, build Release, 5 passes OpenCover (6 568 tests
  verts, 0 échec), end.
- **Phase 1 (new code)** : 71 issues dans la période de nouveau code, dont 10 sur des fichiers de la task.
  **Une seule est de task-332**, d'après `git blame` ligne par ligne :
  - `CA1859` (INFO), `BusMessageMinimalIdentityEndToEndTests.cs:216` : fixée (`3e9d61a9`). Test rejoué vert,
    build 0 erreur.
  - Les 9 autres sont sur des lignes antérieures que la task n'a pas modifiées :
    - `S103` ×2 dans `IMailRepository` (task-334, 2026-10-09) ;
    - `S103` ×3 dans `AddNewMailConsumer` (task-325, 2026-09-30) ;
    - `S4462` ×3 dans `AuditService` (task-292, 2026-09-11, attente synchrone volontaire de la contre-pression) ;
    - `S138` sur `LoadBulkContentLookupsAsync` (2026-06-02).
  - Hotspots : 13 `TO_REVIEW` dans la période de nouveau code, **aucun** sur un fichier de la task.
  - **Quality Gate (new code) : ERROR, déjà en ERROR à la baseline**. Les conditions en échec sont
    `new_violations` (68 → 71) et `new_security_hotspots_reviewed` (0 %). Toutes deux viennent de tasks
    déjà mergées, la période de nouveau code du projet étant une baseline large (mémoire « new-code period
    inclut des tasks déjà mergées »). La baseline date de l'analyse du 2026-10-04 ; entre-temps, 43 commits
    ont été mergés sur develop. L'écart de +3 n'est donc pas attribuable à cette task : sa seule issue est
    corrigée.
- Phase 1 — Tests ajoutés par `/sonar` : 0. La couverture du nouveau code était déjà à 98,1 %, au-dessus
  de la cible de 95 %.
- Phase 2 (legacy) : **non jouée**. Elle est optionnelle, et les candidates évidentes du fichier touché
  (`S4462` dans `AuditService`) sont comportementales : remplacer l'attente synchrone par un `await`
  changerait la sémantique de contre-pression du journal d'audit. C'est hors du périmètre d'une task de
  secrets.
- Build / tests : ✓ green.

### KPIs qualité (baseline → final)

| Métrique | Baseline (2026-10-04) | Final (branche, 2026-10-13) | Δ |
|---|---|---|---|
| Quality Gate (new code) | ERROR | ERROR | → (pré-existant, aucune issue de la task restante) |
| New coverage | 98.1 % | 98.1 % | 0 |
| Bugs | 2 | 2 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 15 | 15 | 0 |
| Code smells | 70 | 73 (72 après `3e9d61a9`) | +2, issues de develop, aucune de task-332 |
| Coverage (projet) | 97.9 % | 98.0 % | +0.1 pt |
| Duplication | 0.3 % | 0.3 % | 0 |
| Reliability / Security / Maintainability | D/A/A | D/A/A | → |

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail touché | ✅ verte | 34 verts, 0 flaky, 0 rouge, 0 quarantaine | 7 min 39 s |
| angular | api-mail touché | ✅ verte | 38 verts, 0 flaky, 0 rouge, 1 quarantaine (E2E-COMPOSE-002) | rejouée, voir Timings |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ `fix/task-332-bus-messages-without-secrets` (inchangé par la task)
- Clone mobile : `develop` @ `f992de7`, aligné sur `origin/develop`. Le rapport mobile est celui du premier
  passage, au même commit api-mail `3e9d61a9`, avec le clone mobile inchangé : la voie n'a pas été
  rejouée.
- Clone Angular : `feature/nova-rewriting-mss-weda-integration` @ `84c2e6ac`, arbre propre.
- **Premier passage rouge, en parité seulement.** Les scénarios E2E-RECEIPT-001/002/003 (task-340)
  étaient absents de la suite Angular, parce que le travail Angular de task-340 n'était pas sur le
  checkout. L'humain a mis client-angular à jour, et la voie Angular a été rejouée : verte, parité
  verte.
- Quarantaines : E2E-COMPOSE-002 (angular), correction : task-350
- Divergences ouvertes : aucune
- Parcours touchés sans spec e2e modifié : aucun (task backend-only)
- Démontage : complet (ports libres, aucun conteneur e2e résiduel)

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

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
| E2E-DETAIL-001 | 2 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
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
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
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
| E2E-WEDA-001 | 1 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 1 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 1 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/292, label
  `awaiting-human-merge`. Branche synchronisée avec `develop` (`fa21fe1a`, merge de task-326) puis
  revalidée : 6 623 tests verts, 0 échec.

## Code Review Summary

**APPROVED** : 0 bloquant, 4 suggestions.

| Comportement | Test | Preuve rouge |
|---|---|---|
| Aucun secret ni contenu clinique dans le JSON des trois messages | `BusMessageSecretsTests` | 4 rouges sur le code d'avant |
| Bonne base et bon tenant à partir du message minimal ; embedding, étiquettes, contacts, lien document → contact | `BusMessageMinimalIdentityEndToEndTests` (publieur → JSON MassTransit → consommateurs → PostgreSQL) | M1, M2, M3 |
| Ancien format traité, secrets ignorés | `AMessageAtTheFormerFormat_…` | M1, M2 |
| Aucun type du bus n'expose de secret | `BusMessageSecretPropertyTests` | M4 |
| Trace d'audit sans chaîne de connexion ; spill Redis sans secret | `The_trace_never_carries_…`, `AuditSpillIntegrationTests` | M5 |

**Règle 1b** : aucune réponse HTTP ne change. Le comportement asynchrone (bus) est prouvé par le test
d'intégration sur la vraie pile et la vraie base, avec RabbitMQ remplacé par son sérialiseur.

**Suggestions** :
1. Le cas « mail disparu » est compté `Success` dans la métrique de pipeline.
2. `AddNewMailMessage` peut encore maigrir : expéditeur, dossier, UID et type sont relisibles en base.
3. `UserContextInfo` reste un sac à secrets. La correction de fond est que les dépôts lisent
   `IServerConnectionStrings`.
4. Les traits du patient restent dans `CreatePatientContactMessage`.

## Vérifications complémentaires (2026-10-13, après la revue)

**1. Câblage de production prouvé par un test d'intégration** (`1b9cb74f`).
- L'enregistrement des chaînes de connexion quitte `Program.Main` pour `AddServerConnectionStrings`.
- `UnderTheProductionComposition_TheConsumersResolveAndWorkInThePractitionersDatabase` compose le processus comme
  `Program` : `AddApi` (consommateurs MassTransit), `AddApplication`, `AddInfrastructure`, `AddServerConnectionStrings`.
  Les trois consommateurs sont résolus par le conteneur, et le test vérifie en base PostgreSQL l'embedding,
  l'étiquette et les deux contacts.
- Mutation : sans l'enregistrement de `IServerConnectionStrings`, le test est rouge (« Unable to resolve service for
  type IServerConnectionStrings while attempting to activate AddNewMailConsumer »).
- Suite complète verte : domain 195, infrastructure 690, application 3 624, api 1 230, integration 885
  (+16 ignorés). Le testhost d'`api.tests` s'est figé une fois pendant la suite complète ; relancé seul avec
  `--blame-hang`, il passe (1 230 en 22 s), sans test bloqué identifié.

**2. Essai réel sur RabbitMQ** : AppHost en profil `https-load-test`, registre `mss_registry_loadtest`,
chat et embeddings sur OpenAI, corpus synthétique ANS, sans aucune donnée de patient réelle.
- Seed : 1 boîte (`loadtest-1`), 3 mails porteurs d'un IHE_XDM. `enrich/sync` → 3 analysés.
- Trois files espion, liées aux échanges `mss.mail.application.Messages:*`, ont reçu une copie des messages réels
  sans gêner les consommateurs : **3 `AddNewMailMessage`, 4 `CreatePractitionerContactMessage`,
  4 `CreatePatientContactMessage`**.
- Dans les 11 enveloppes MassTransit, aucun `password`, `connectionString`, `keycloak`, `proxySession`,
  `clientSession` ni `token`, aucun `Host=`, aucun `subject` ni `body`. Le message ne porte que
  `userContext` = { e-mail, RPPS, tenant, nom de base enregistré }, plus l'identifiant du mail, le dossier,
  l'UID, l'expéditeur, le type de document et le drapeau « documents médicaux ». Les en-têtes sont vides.
  Le bloc `host` ne contient que des métadonnées de processus (machine, versions).
- Files de travail vidées par les 5 consommateurs de chaque file, **aucune file `_error` créée**.
- Base praticien `u_90000000001_…` : 3 mails embeddés ; 2 documents sur 4 embeddés, soit exactement ceux qui ont
  un corps ; 6 étiquettes IA ; 2 contacts praticien et 2 contacts patient ; 4 documents liés à leur contact
  praticien.
- Seq : 14 événements des consommateurs sur la fenêtre (3 « Processing / Completed », 4 + 4 contacts), **0 erreur**.
- Démontage : AppHost arrêté, conteneurs de session retirés, volume du maildir du banc conservé.

Reste au plan de test manuel : le contrôle visuel dans l'application (étiquettes, recherche, contacts).

## Timings

*(généré par `tools/timing/report.sh --task task-332 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /e2e | ok | 7 min 33 s | — | — | — | e2e ×2 (7 min 02 s), rerun angular apres mise a jour humaine de client-angular |
| /review | ok | 6 min 33 s | 1 (17 s) | 1 (4 min 15 s) | — | api-mail 1B/1T |
| /tech-writer | ok | 1 min 20 s | — | — | — | — |
| **Total cycle** | | **15 min 27 s** | **1 (17 s)** | **1 (4 min 15 s)** | **0 (0.0 s)** | |
