# todo-task-319.md — Une messagerie que l'opérateur refuse cesse d'être utilisable : la re-validation continue est câblée

**Repos**: api-mail
**Dependencies**: —
**Epic**: E016
**Single frontend**: true

> Remédiation n°2 de l'audit sécurité du registre du 2026-09-16 (écart élevé).
> Voir aussi task-318 (jeton PSC vérifié et lié au compte) et task-320 (hors ligne
> en lecture seule côté serveur).

## Objectif

task-303 a posé trois garanties pour justifier que la boîte vienne du registre et
non plus d'un claim signé. La troisième dit : *« Re-validation continue. Chaque
login IMAP réussi re-valide de fait le rattachement. Une boîte dont
l'authentification échoue durablement est marquée `AuthFailing` (donc non
compatible) — jamais détachée silencieusement, remise `Active` au premier succès. »*

**Cette garantie n'est pas tenue.** Le registre sait enregistrer l'issue d'une
authentification (`MarkAuthenticationOutcomeAsync`), mais **personne ne l'appelle** :
l'état `AuthFailing` n'est jamais posé, et la date de dernière connexion réussie
(`LastSuccessfulLoginAt`) n'est jamais écrite. Un rattachement, une fois accepté,
est **acquis pour toujours**.

Conséquence : un professionnel que son opérateur MSSanté ne reconnaît plus — carte
révoquée, départ de la structure, boîte organisationnelle retirée — garde une boîte
sélectionnable, et donc **l'accès hors ligne à tout le contenu synchronisé**, sans
limite de durée. C'est exactement le cas que la règle devait fermer.

Après cette US, chaque authentification XOAUTH2 auprès de l'opérateur, sur le
chemin de requête comme en synchronisation d'arrière-plan, **nourrit le registre** :
un succès remet la boîte `Active` et date la connexion ; des refus répétés de
l'opérateur la basculent en `AuthFailing`, ce qui la retire des boîtes utilisables
— y compris hors ligne, comme le code de compatibilité le prévoit déjà.

**US backend uniquement (justification)** : les états `AuthFailing` et la date de
dernière connexion sont **déjà** dans le contrat `MailboxDto` et **déjà** affichés
par les trois fronts (raison d'indisponibilité, date). Aucun écran ne change ; il
se met enfin à afficher quelque chose de vrai.

## Constat établi par lecture du code (2026-09-16)

- `Api/Mail/src/Infrastructure/Repositories/TenantDb/PostgresTenantRegistryClient.cs`
  — `MarkAuthenticationOutcomeAsync(accountId, adresse, succeeded, at)` existe,
  invalide le cache, pose `Active` + `LastSuccessfulLoginAt` ou `AuthFailing`.
  **Zéro appelant** dans `src/`.
- `Api/Mail/src/Application/Services/Implementation/ImapConnectionService.cs` —
  chemin de requête : `AuthenticateAsync(SaslMechanismOAuth2)` ; un jeton expiré
  est détecté **localement avant** l'appel (task-165, 401) ; un refus de l'opérateur
  sort en `AuthenticationException` et n'est rapporté à personne.
- `Api/Mail/src/Application/Services/Implementation/BackgroundImapService.cs` —
  chemin de synchronisation : même mécanisme, même silence.
- `Api/Mail/src/Application/Services/Implementation/BackgroundSyncManager.cs` — le
  contexte reconstruit pour le worker copie l'adresse, le RPPS et le jeton, mais
  **ni `TenantId` ni `RegisteredDatabaseName`**. Deux effets : le worker ne sait
  pas quel rattachement il authentifie, et **toutes ses traces d'audit** (connexion,
  réception, déplacement, suppression) partent dans le tenant système `Guid.Empty`
  — invisibles du praticien, mélangées à l'échelle du parc.
- `Api/Mail/src/Domain/Entities/TenantDb/MailboxCompatibility.cs` — `AuthFailing`
  rend `Selectable = false` avant toute considération de session : le comportement
  aval est **déjà écrit**, il attend son signal.
- Contexte à garder en tête (mémoire `psc-token-2min-vs-kc-5min-imap-gap`) : le
  jeton PSC vit ~2 min contre ~5 min pour Keycloak. Des **échecs pour jeton expiré
  sont normaux et fréquents** ; ils ne disent rien du rattachement et ne doivent
  **jamais** compter.

## Règles métier

**RG-1 — Chaque authentification auprès de l'opérateur est rapportée au registre.**
Sur le chemin de requête et sur le chemin de synchronisation, une authentification
XOAUTH2 réussie appelle `MarkAuthenticationOutcomeAsync(succeeded: true)` ; un refus
de l'opérateur (`AuthenticationException`) l'appelle avec `succeeded: false`. Au
meilleur effort, comme toute écriture du registre : une panne du registre ne casse
jamais la connexion du praticien.

**RG-2 — Seul un refus de l'opérateur sur un jeton non expiré compte comme échec.**
Ne comptent **pas** : jeton absent (hors ligne), jeton expiré selon la vérification
locale, hôte injoignable, erreur TLS, délai dépassé, annulation. Ces cas ne disent
rien de l'habilitation du professionnel sur la boîte.

**RG-3 — `AuthFailing` après échecs consécutifs, pas au premier.** Un compteur par
rattachement, tenu dans le cache partagé (donc à travers les réplicas), déclenche
le passage en `AuthFailing` au **N‑ième refus consécutif dans une fenêtre W**. Un
succès remet le compteur à zéro. Valeurs par défaut proposées : N = 3, W = 15 min,
configurables.

**RG-4 — Retour à `Active` au premier succès.** Comportement déjà écrit dans le
registre ; l'US le rend atteignable. Aucune intervention humaine, aucun re-rattachement.

**RG-5 — `AuthFailing` retire la boîte des boîtes utilisables, hors ligne compris.**
Comportement déjà écrit dans `MailboxCompatibility`. La liste des boîtes continue
de la montrer (`state = AuthFailing`, raison affichée) pour que le praticien
comprenne ; elle n'est plus sélectionnable et aucune route de messagerie ne l'ouvre.

**RG-6 — Le contexte de synchronisation porte le rattachement.** Le worker
d'arrière-plan reçoit `TenantId` et `RegisteredDatabaseName` du contexte de la
requête qui l'a lancé. Ses traces d'audit rejoignent le tenant de la boîte, et il
utilise le nom de base **enregistré**, jamais recalculé.

**RG-7 — Trace d'audit.** Le passage en `AuthFailing` et le retour en `Active` sont
tracés sous un type **existant** (`ConnectionError` en échec pour le premier, `ImapConnect`
en succès pour le second, avec un `ErrorMessage`/détail explicite). **Aucun nouveau
membre `AuditActionType`** : le type est miroité à la main côté Angular et Blazor.

> ⚠️ **Arbitrage humain requis — non bloquant pour démarrer.**
>
> 1. **Seuil et fenêtre** de RG-3 (défauts proposés : 3 refus en 15 min). Un seuil
>    trop bas bascule des boîtes sur un incident passager chez l'opérateur ; trop
>    haut, il laisse la fenêtre d'accès ouverte plus longtemps.
> 2. **Hors ligne et `AuthFailing`** : le code actuel retire aussi la **lecture
>    hors ligne**. C'est le comportement voulu par task-303, et c'est celui que
>    l'US câble. Confirmez, ou dites si la lecture locale doit survivre à un refus
>    de l'opérateur (ce serait un affaiblissement, à documenter dans l'AIPD).
>
> Sans réponse, l'US part avec les défauts proposés et le comportement task-303.

## Definition of Done

- [ ] Build passes (0 errors) — `dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) — `dotnet test HealthPlatform.Api.Mail.sln`
- [ ] `MarkAuthenticationOutcomeAsync` est appelé sur succès et sur refus opérateur depuis le chemin de requête (`ImapConnectionService`) **et** le chemin de synchronisation (`BackgroundImapService`)
- [ ] Un jeton expiré, absent, ou une erreur réseau/TLS/délai **ne** produit **aucun** appel en échec
- [ ] Compteur d'échecs consécutifs par rattachement dans le cache partagé ; `AuthFailing` au N‑ième refus dans la fenêtre W ; N et W configurables avec défauts documentés dans `appsettings.json`
- [ ] Un succès remet le compteur à zéro et la boîte `Active` ; `LastSuccessfulLoginAt` est écrit
- [ ] Une boîte `AuthFailing` est refusée par la sélection de boîte (403 `PscMismatch`, comportement existant) et apparaît dans `GET /api/v1/account/mailboxes` avec `state = AuthFailing`, `selectable = false`, raison `AuthFailing`, `lastSuccessfulLoginAt` renseigné
- [ ] Le contexte du worker de synchronisation porte `TenantId` et `RegisteredDatabaseName` ; ses traces d'audit portent le tenant de la boîte (plus aucune trace de synchronisation en `Guid.Empty` sur un scénario nominal)
- [ ] Traces sous types existants uniquement ; aucun nouveau membre `AuditActionType`
- [ ] Aucune donnée de santé ni jeton dans les logs ajoutés ; adresse anonymisée comme dans le middleware
- [ ] Tests unitaires : classification des issues (succès / refus / expiré / réseau / annulé), compteur (N‑1 refus → `Active`, N → `AuthFailing`, succès → remise à zéro, fenêtre expirée → remise à zéro), propagation du tenant au contexte de synchronisation
- [ ] Tests d'intégration : après N refus simulés de l'opérateur, `GET /api/v1/mail/folders` avec `Client-Email` sur cette boîte → 403 ; `GET /api/v1/account/mailboxes` la montre `AuthFailing` ; après un succès, elle redevient ouvrable
- [ ] Le document d'EPIC E016 (`/tech-writer`) décrit la re-validation continue comme livrée, plus comme promise

## Manual Test Plan

- **Lancer** en profil banc (opérateur Dovecot local, pilotable) :
  `cd Api/Mail && aspire run --project src/AppHost` avec le profil loadtest (voir
  `Docs/epics/E015-tests-charge-api-mail.md`), puis un front (mobile : `cd Client/Mobile && npm start`).
- **Nominal** : se connecter, ouvrir la boîte. Vérifier le registre :
  `docker exec postgres-pgvector psql -U postgres -d mss_registry -c "select mailbox_address, state, last_successful_login_at from mss_accounts;"`
  **Attendu** : `state = 0` (Active) et `last_successful_login_at` **renseignée** à l'instant de la
  connexion (aujourd'hui elle reste vide).
- **Refus de l'opérateur** : rendre le compte Dovecot du praticien de test invalide (mot de
  passe ou utilisateur retiré côté Dovecot, ou pointer son domaine `MailServers` vers un
  compte inexistant), puis recharger la boîte **N fois** (défaut 3) en moins de W.
  **Attendu** : à partir du N‑ième refus, les routes de messagerie rendent `403` avec un
  `ProblemDetails` « Cette messagerie n'est pas utilisable avec la session en cours » ; la liste
  des boîtes montre l'état **Échec d'authentification** ; la lecture **hors ligne** (sans jeton PSC)
  est elle aussi refusée ; le registre porte `state = 2`.
- **Faux positifs** : couper le réseau vers l'opérateur (ou laisser le jeton PSC expirer sans
  rafraîchir) et recharger plusieurs fois. **Attendu** : `401`/`503` selon le cas, **mais** le registre
  reste `Active` — aucun basculement.
- **Retour** : restaurer le compte Dovecot, recharger. **Attendu** : la boîte redevient
  utilisable au premier succès, `state = 0`, `last_successful_login_at` mise à jour.
- **Audit du sync** : lancer une synchronisation manuelle, puis ouvrir l'écran d'audit du
  praticien. **Attendu** : les traces de connexion et de réception de la synchronisation
  sont **visibles** (elles partaient auparavant dans le tenant système).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — tenue d'une garantie de sécurité déjà promise (task-303)
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — aucune donnée patient manipulée ; l'US touche l'état des rattachements
- **Authentification PS** : Pro Santé Connect via XOAUTH2 auprès de l'opérateur MSSanté ; l'US fait de **chaque** authentification une re-vérification de l'habilitation du professionnel sur sa boîte (PGSSI-S — révocation effective des accès)
- **Habilitations** : resserrées. Une habilitation retirée chez l'opérateur se traduit, après N refus, par le retrait de la boîte des boîtes utilisables, hors ligne compris
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : passage en `AuthFailing`, retour en `Active`, sous types existants ; **rattachement correct des traces de synchronisation à leur tenant** (imputabilité). Conservation alignée sur le journal existant
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement inchangé
- **AIPD / impact RGPD** : à mettre à jour — la mesure « révocation d'accès effective » devient réelle ; noter que la lecture hors ligne cesse avec l'habilitation opérateur
