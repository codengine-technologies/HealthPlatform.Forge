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

## Timings

*(généré par `tools/timing/report.sh --task task-332 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 21 s | — | — | — | — |
| **Total cycle** | | **21 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |
