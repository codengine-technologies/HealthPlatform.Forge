# todo-task-332.md — Les messages internes de la plateforme ne transportent plus aucun secret : ni mot de passe de base, ni jeton, ni session PSC

**Repos**: api-mail
**Dependencies**: — (aucune)
**Epic**: E016
**Single frontend**: true
**Priorité**: **1** — chaque message RabbitMQ contient la **chaîne de connexion Postgres** (mot de passe), le **jeton Keycloak**, le mot de passe IMAP et la **session du proxy PSC** du praticien ; ils sont stockés dans des files durables, visibles en console d'administration et conservés indéfiniment dans les files d'erreur.

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, **AUD-10**, contre-vérifié).

## Ce qui est établi (develop @ `14d58398`)

- `Application/Messages/AddNewMailMessage.cs:14` : `public required UserContextInfo UserContext` —
  l'objet **complet**, sérialisé par System.Text.Json ; même chose pour
  `CreatePatientContactMessage` et `CreatePractitionerContactMessage`. Publiés par
  `BackgroundEnrichmentProcessor.cs:362` et `ImapService.cs:4673`.
- `Domain/Entities/MailDb/UserContextInfo.cs` : **aucun `[JsonIgnore]`** ; porte `ConnectionStringServer`
  (`:104`) et les chaînes calculées qui en dérivent, `KeycloakToken` (`:73`), `Password`, `ProxySessionId` (`:48`,
  qui permet d'obtenir un jeton PSC auprès du proxy).
- Les consommateurs n'utilisent que quelques champs d'identité (e-mail, RPPS, contexte de base).
- `AddNewMailMessage` transporte en outre le **corps** du mail (`Body`) et son sujet.
- Au passage : le spill d'audit Redis (`RedisAuditSpillStore.cs:75`) sérialise encore
  `TransportConnectionStringServer` / `TransportConnectionStringDirect`, devenus inutiles depuis task-312.

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
- La copie d'identité en tâche de fond (task-334).

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
