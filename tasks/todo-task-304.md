# todo-task-304.md — Gestion des comptes de messagerie dans les fronts (vague 2/2) : choix de la boîte à la connexion, avatar → bascule en direct entre les boîtes compatibles avec l'identité PSC, chaque bascule = fin de session + nouvelle session — parité Blazor / Angular / mobile

**Repos**: client-blazor, client-angular, client-mobile
**Dependencies**: **task-303** (backend : `GET /account/mailboxes` avec `compatibleWithSession`
et `isDefault`, `POST/DELETE /account/mailboxes`, `PUT …/default`, SSE `?mailbox=`,
`POST /sync/logout` comme fin de session de boîte, garde `SESSION_MAILBOX_MISMATCH`, codes
`MAILBOX_*` / `PSC_IDENTITY_CONFLICT`, `AuditActionType` + 5 membres publiés dans `dtos-mss`).
**Epic**: E016
**LintProjects**: weda2, mss, mss-lib

> **Vague 2 de la US « comptes multi-messageries »** (vague 1 = task-303). C'est **cette** vague
> qui porte la valeur pour le médecin, et c'est sur la US **assemblée** (303 + 304) que se fait le
> test humain (règle 11) : les PRs de 303 attendent en `awaiting-us-completion` que celles de 304
> soient prêtes.
>
> `client-angular` est en **code-only** : la forge écrit le code sur la branche que l'humain a
> checkout dans `Client/Angular/` (intégration vivante `next`), sans commit ni push.
> `client-mobile` est en automation git complète ; ses écrans passent par `/stitch-design` puis
> `/verify-visual`.

## Objective

Le parcours voulu, mot pour mot (demande humaine du 2026-09-13) :

> Le médecin se connecte via proxy / Keycloak / PSC. On détecte dans la base centrale qu'il a
> N boîtes compatibles avec son identité PSC. **Boîte par défaut absente ⇒ écran de sélection**
> (avec la possibilité de définir la boîte par défaut) ; **boîte par défaut présente ⇒ on s'y
> connecte directement.** Dans l'interface, le médecin voit **son avatar** ; en cliquant dessus il
> peut choisir une autre adresse : cela le fait **basculer** sur une nouvelle boîte — **toutes les
> données disparaissent** (mails, tableau de bord, etc.) et celles de la boîte choisie se chargent.
> Côté backend, la bascule est **une fin de session puis une nouvelle session**.

Un médecin = N BAL MSSanté, chez un ou plusieurs opérateurs, une seule connexion PSC.

### Règles reprises de task-303 (le front les applique, ne les évalue pas)

- **Compatible** = le backend le dit (`compatibleWithSession: true`) : rattachement actif validé
  par la **même identité PSC** (`sub`, `SubjectNameID`) que le `X-PSC-Token` de la session. Les
  fronts **n'évaluent jamais** cette règle : ils affichent ce que le backend rend et n'envoient
  `Client-Email` que pour une boîte compatible.
- **« Même jeton PSC » = même identité**, pas même chaîne : le jeton tourne toutes les ~2 min
  (task-283). Un refresh PSC ne change **ni** la liste **ni** la boîte courante.
- **Bascule = fin de session + nouvelle session** : `POST /sync/logout` avec les en-têtes de la
  session sortante (fermeture IMAP/SMTP sur tous les pods, arrêt de la synchro de fond, contexte
  vidé), puis **nouvel identifiant de session** et nouvelle boîte. Le backend **refuse** (409
  `SESSION_MAILBOX_MISMATCH`) un identifiant réutilisé avec une autre boîte : la nouvelle session
  n'est pas une convention de front, elle est imposée.
- **Aucune ré-authentification** : bearer Keycloak et `X-PSC-Token` conservés ; aucune navigation
  vers Keycloak / PSC ; aucun rechargement de page.
- **Non compatible** = affichée **grisée** avec la raison rendue par le backend, jamais masquée
  (`AuthFailing` → « Authentification à cette boîte en échec », `PscIdentityMismatch` → « Cette
  boîte relève d'une autre identité Pro Santé Connect », `NoPscToken` → « Hors ligne — lecture
  locale seulement »).

### Ce qui existe aujourd'hui dans les fronts — vérifié

| Front | Source de la boîte | Onboarding | Verrou | Fin de session |
|---|---|---|---|---|
| `client-blazor` | `AuthService.ExtractMssEmailFromJwt` → `UserSessionService.UserEmail` → `HttpRequestService.UpdateClientEmailHeader` (`Client-Email`, `Client-Session-Id`) | `MailSetup.razor` (`/Mail/setup`) → `MssOnboardingService.ValidateImapConnectionAsync` puis `PersistMssEmailAsync` (proxy) → « déconnectez-vous » | `MssOnboardingGuard` (claim absent) → `MssUnconfigured.razor` ; `Mss403Handler` | `Logout.razor` → `SyncProgressService.LogoutCleanupAsync` → `POST /sync/logout` |
| `client-angular` (weda2 + `libs/mss`) | `mssHeadersInterceptor` : `Client-Email` ← `jwtDecoded.mssEmail`, `Client-Session-Id` ← `sid` | `MssOnboardingService.validateImapConnection` puis `persistMssEmail` (proxy) ; `/mss/setup` | `mss-onboarding.guard.ts` → `/unconfigured` ; `mail-events-stream.service.ts` (SSE) | `mss-api.service.ts:183` → `POST /sync/logout` |
| `client-mobile` | `AuthSession.mssEmail` ← `jwtPayload['mssEmail']` ; `sessionId` = `newClientSessionId()` au login (task-282) → `MssHeadersInterceptor`, `mss-api.service.ts:760` | `mss-onboarding.service.ts` (A puis B proxy) ; `/mss-setup`, `/mss-unconfigured` | `mssConfiguredGuard` (task-167) ; onglets Messages / Patients / Paramètres | `logout.service.ts` + `mss-api.service.ts:94` → `POST /sync/logout` |

Dans les trois : la boîte vient du **jeton**, l'ajout passe par le **proxy**, l'activation exige
une **déconnexion**, et la fin de session n'est appelée qu'à la **déconnexion**. Le mécanisme de
fin de session existe et est le bon — il est simplement **réutilisé à chaque bascule**.

## Comportement commun — parité stricte sur les trois fronts

### A. À la connexion

1. Après l'authentification (proxy / Keycloak / PSC), le front appelle `GET /account/mailboxes`.
2. Décision, **dans cet ordre** :
   - **0 boîte active** ⇒ écran verrou existant → « Configurer ma messagerie » (onboarding, §D).
   - **une boîte par défaut compatible** ⇒ **connexion directe** à cette boîte, aucun écran.
   - **sinon** (pas de défaut, ou défaut non compatible, ou plusieurs boîtes sans défaut) ⇒
     **écran de sélection** `mailbox-select` : liste des boîtes (adresse, opérateur, état ;
     non compatibles grisées avec raison), une case **« Toujours ouvrir cette messagerie »**
     (⇒ `PUT /account/mailboxes/{id}/default`), bouton « Ouvrir ». Une seule boîte compatible
     sans défaut ⇒ l'écran s'affiche quand même, pré-sélectionnée — c'est là que le médecin pose
     son défaut.
3. **Aucune persistance de la sélection sur l'appareil** : le défaut vit dans l'annuaire, donc il
   suit le médecin d'un poste à l'autre (décision de PO, alignée sur la demande : « si BAL par
   défaut présente, on s'y connecte directement »). La sélection sans défaut vaut pour la session
   en cours seulement.

### B. Avatar et sélecteur

4. **L'avatar** du médecin (en-tête web, en-tête de l'onglet Messages sur mobile) est le point
   d'entrée : initiales ou image, avec l'adresse de la boîte courante en libellé. Un clic ouvre
   le **sélecteur** `mailbox-switcher` : identité du PS (nom, RPPS), boîte courante cochée,
   autres boîtes (adresse, opérateur, état ; non compatibles grisées avec raison), actions
   **« Ajouter une messagerie »** et **« Gérer mes messageries »** (défaut / détacher).
5. Choisir une autre boîte compatible déclenche la **bascule** (§C). Choisir une boîte non
   compatible est impossible (élément désactivé, raison affichée).

### C. Bascule — fin de session, page blanche, nouvelle session

6. **Séquence, dans cet ordre, sans étape optionnelle** :
   1. **Gel** de l'interface (indicateur « Changement de messagerie… ») et **annulation** de toutes
      les requêtes en vol de la boîte sortante ; fermeture du flux SSE.
   2. `POST /sync/logout` avec les en-têtes de la session **sortante** (`Client-Email` ancienne
      boîte, `Client-Session-Id` ancien identifiant). Best-effort : un échec est journalisé côté
      front et **ne bloque pas** la bascule (le filet d'expiration serveur reprend la main, comme
      à la déconnexion).
   3. **Purge totale de l'état applicatif** : stores / signaux / caches de mails, dossiers,
      compteurs, tableau de bord, recherche, dossiers patients, contacts, brouillons non
      envoyés (avec confirmation préalable s'il en reste un), réglages et signature, pièces
      jointes en cache, notifications affichées. **Rien de la boîte sortante ne doit survivre** —
      c'est le critère d'acceptation central. Le bearer, le jeton PSC et l'identité du PS sont
      **conservés**.
   4. **Nouvel identifiant de session** (`crypto.randomUUID()` — `newClientSessionId()` côté
      mobile, équivalent web) et nouvelle boîte courante.
   5. Réabonnement SSE avec `?mailbox=` nouvelle boîte ; navigation vers la racine de la
      messagerie (INBOX) ; chargement des données de la nouvelle boîte.
7. **Aucun rechargement de page**, aucun `forceLoad`, aucune redirection vers Keycloak / PSC.
   Dans l'onglet réseau : `Client-Email` et `Client-Session-Id` changent, `Authorization` et
   `X-PSC-Token` **ne changent pas**.
8. Un 409 `SESSION_MAILBOX_MISMATCH` reçu après une bascule est un **bug de front** (identifiant
   non rotaté) : il est journalisé comme erreur et déclenche une nouvelle rotation — jamais
   silencieux.

### D. Onboarding « ajouter une messagerie »

9. L'écran verrou existant s'affiche quand le compte a **zéro** boîte active ; le formulaire
   `/setup` existant devient **« Ajouter une messagerie »**, appelle `POST /account/mailboxes`,
   affiche l'erreur de sonde par `code` (mapping existant + `PSC_IDENTITY_CONFLICT` → « Cette
   boîte relève d'une autre identité Pro Santé Connect »), et **enchaîne sur la boîte** par une
   bascule (§C) — **plus de déconnexion / reconnexion**. Depuis le sélecteur, le même formulaire.
   Première boîte du compte ⇒ le backend la pose par défaut ; le formulaire propose la case
   « Toujours ouvrir cette messagerie » pour les suivantes.
10. **« Gérer mes messageries »** : liste, définir par défaut, détacher (confirmation explicite ;
    détacher la boîte courante ⇒ bascule vers la boîte par défaut ou l'écran de sélection ;
    détacher la dernière ⇒ écran verrou).

### E. Ce qui disparaît des fronts

11. `persistMssEmail` / `PersistMssEmailAsync` et l'appel `PUT {proxy}/v1/admin/mss-profile`,
    ainsi que leur configuration (`MSS_KEYCLOAK_PROXY_URL`, `Oidc:ApiServerUrl` pour cet usage,
    exclusion de l'`auth.interceptor` Angular).
12. **Toute lecture de claim MSS** (`mssEmail`, `mssSub`, `mssRpps`) : le backend absorbe les
    jetons hérités (`LegacyClaimsMigration`, task-303). `Client-Session-Id` n'est **plus jamais**
    la claim `sid` (Angular) — c'est un identifiant applicatif tiré au login et à chaque bascule,
    comme le mobile le fait déjà (task-282).

### F. Erreurs

13. `MAILBOX_NOT_ATTACHED` / `MAILBOX_PSC_MISMATCH` ⇒ recharger la liste, bascule (§C) vers la
    boîte par défaut compatible ou écran de sélection, toast « Cette messagerie n'est plus
    disponible pour votre session » ; `MAILBOX_REQUIRED` ⇒ écran de sélection ou verrou. Les
    gestionnaires 403 existants (`Mss403Handler`, équivalents) sont mis à jour — le message
    « stale Client-Email or missing mssEmail claim » n'est plus vrai.

## Par front

### `client-blazor`
- Nouveau `MailboxSessionService` (liste, courante, compatibilité, défaut, **bascule §C**,
  rotation de `ClientSessionId`) ; `AuthService` cesse d'alimenter `UserSessionService.UserEmail`
  depuis le JWT (`ExtractMssEmailFromJwt` retiré) ; `HttpRequestService.UpdateClientEmailHeader`
  lit la session de boîte courante ; `SyncProgressService.LogoutCleanupAsync` réutilisé pour la
  bascule ; `MssOnboardingGuard` : « 0 boîte active » ; nouvelle page `MailboxSelect.razor`
  (`/Mail/select`) ; `MailSetup.razor` réutilisé en « ajouter » (fin du `NavigateTo("/",
  forceLoad: true)`) ; composant avatar + menu `MailboxSwitcher` dans l'en-tête du module Mss ;
  `Mss403Handler` mis à jour. Réutiliser les composants existants (consigne). `Localizer`,
  `data-testid` partout.

### `client-angular` (code-only)
- `mssHeadersInterceptor` : `Client-Email` et `Client-Session-Id` ← store de session de boîte
  (plus `jwtDecoded.mssEmail` / `sid`) ; `mss-onboarding.guard.ts` : « 0 boîte active » + garde
  « boîte choisie » redirigeant vers `/mss/select` ; `MssOnboardingService` : `persistMssEmail`
  supprimé, `attachMailbox` / `listMailboxes` / `detachMailbox` / `setDefaultMailbox` ajoutés,
  `MSS_KEYCLOAK_PROXY_URL` retiré ; `mail-events-stream.service.ts` : `?mailbox=`, fermeture à la
  bascule, réabonnement ; **store de session de boîte** (signal) dont la bascule remet à zéro tous
  les stores dépendants (méthode `reset()` obligatoire sur chaque store MSS, appelée en séquence)
  et annule les requêtes en vol (garde de version) ; page `/mss/select` ; avatar + `mailbox-switcher`
  dans le shell MSS ; libellés FR en dur (norme MSS). **Miroir TS de `AuditActionType`**
  (`libs/mss/src/core/models/audit.model.ts`) : **5** nouveaux membres, **valeurs ordinales écrites
  explicitement** ; libellés dans l'écran d'audit.

### `client-mobile`
- `session.model.ts` : `mssEmail` → `currentMailbox` + `mailboxes[]` ; `sessionFromTokenAggregate`
  **ne lit plus `mssEmail`** ; `sessionId` **rotaté à chaque bascule** (`newClientSessionId()`
  existant) ; `MssHeadersInterceptor` et `mss-api.service.ts` lisent la session de boîte ;
  `logout.service.ts` : la séquence de fin de session est extraite en `closeMailboxSession()`,
  réutilisée par la bascule ; `mssConfiguredGuard` : « 0 boîte active » + redirection
  `/mailbox-select` ; `/mss-setup` réutilisé en « ajouter » ; `mss-onboarding.service.ts` : B
  supprimé, `attachMailbox` ajouté. Purge des stores à la bascule (mails, dossiers, patients,
  contacts, réglages, brouillons). `POST Settings` reste un remplacement en bloc — muter par
  spread, **par boîte**.
- **Écrans Stitch** (titre = nom kebab-case du composant) : **`mailbox-select`** (plein écran
  post-connexion : liste, grisées + raison, case « Toujours ouvrir cette messagerie », bouton
  Ouvrir), **`mailbox-switcher`** (feuille d'action depuis l'avatar de l'en-tête Messages : identité
  du PS, boîtes, « Ajouter », « Gérer »), **`settings-mailboxes`** (page « Messageries » de l'onglet
  Paramètres : défaut, détacher, état). `/stitch-design` avant de coder, `/verify-visual` capture les
  trois.

## Definition of Done

### Transverse
- [ ] Build passes on **every** listed repo (0 errors) ; tests pass (0 failures)
- [ ] `client-blazor` bumpé aux versions `dtos-mss` / `sdk` publiées par task-303
- [ ] Sur les **trois** fronts : plus aucune lecture de `mssEmail` / `mssSub` / `mssRpps` / `sid`
      (pour `Client-Session-Id`) ni aucun appel à `mss-profile` dans le code de production —
      vérifié par grep dans le DOD de chaque repo
- [ ] Aucune évaluation locale de la compatibilité PSC (spec/test qui échoue si un front compare
      lui-même un `sub`) ; aucune persistance de boîte sur l'appareil
- [ ] Aucune chaîne en dur côté Blazor (Localizer) ; FR en dur côté Angular MSS et mobile ;
      `data-testid` sur tous les éléments interactifs (avatar, sélecteur, écran de sélection,
      formulaires)

### Tests communs aux trois fronts (une spec / un test par front, mêmes cas)
- [ ] **Connexion** : 0 boîte ⇒ verrou ; défaut compatible ⇒ connexion directe **sans** écran ;
      N boîtes sans défaut ⇒ écran de sélection ; défaut **non** compatible ⇒ écran de sélection
      avec le défaut grisé et sa raison ; case « Toujours ouvrir » ⇒ `PUT …/default` puis
      connexion
- [ ] **Bascule — séquence** : requêtes en vol annulées → SSE fermé → `POST /sync/logout` avec les
      **anciens** en-têtes → purge → **nouveau** `Client-Session-Id` → nouvelle `Client-Email` →
      SSE `?mailbox=` → chargement. Test qui échoue si l'ordre change ou si une étape manque
- [ ] **Bascule — page blanche** : après la purge et avant le premier chargement, **tous** les
      stores/états MSS sont à leur valeur initiale (test qui énumère les stores et échoue si l'un
      d'eux garde une donnée de la boîte sortante) ; une réponse tardive de la boîte sortante
      arrivant après la bascule est **ignorée** (garde de version)
- [ ] **Bascule — identité conservée** : `Authorization` et `X-PSC-Token` identiques avant/après ;
      aucune navigation Keycloak / PSC ; aucun rechargement (`forceLoad` / `location.reload`
      absents — grep)
- [ ] **Bascule — échec de `/sync/logout`** (500 / réseau) ⇒ journalisé, la bascule **aboutit**
      quand même
- [ ] 409 `SESSION_MAILBOX_MISMATCH` ⇒ erreur journalisée + rotation de l'identifiant + rejeu, jamais
      silencieux
- [ ] Refresh du jeton PSC (rotation simulée) ⇒ liste et boîte courante **inchangées**
- [ ] Sélecteur : non compatibles grisées, raison affichée, **non cliquables** ; « Ajouter » ⇒ `POST`
      puis bascule ; « Détacher » la courante ⇒ bascule vers le défaut ou l'écran de sélection ;
      détacher la dernière ⇒ verrou
- [ ] `MAILBOX_PSC_MISMATCH` / `MAILBOX_NOT_ATTACHED` en cours de session ⇒ rechargement de la
      liste + bascule de repli + toast

### `client-blazor`
- [ ] bUnit : `MailboxSelect`, `MailboxSwitcher` (avatar), `MailSetup` en mode « ajouter » ;
      `MssOnboardingGuardTests` (« 0 boîte active », redirection `/Mail/select`) ;
      `MssOnboardingServiceTests` : `PersistMssEmailAsync` **supprimé**, `AttachMailboxAsync`
      (succès + codes) ; `MailboxSessionService` : séquence de bascule (mocks ordonnés)

### `client-angular` (code-only)
- [ ] Specs : intercepteur (`Client-Email`/`Client-Session-Id` ← store, jamais du JWT), gardes,
      service, flux SSE, store de session (bascule ⇒ `reset()` de chaque store dépendant, garde de
      version), page `/mss/select`, avatar + sélecteur ; spec de contrat du miroir
      `AuditActionType` (5 valeurs ordinales)
- [ ] `npm run build` + `npm test` verts sur la branche courante ; `/lint-angular` scope `scope:mss`

### `client-mobile`
- [ ] Specs : `session.model` (`currentMailbox`, rotation de `sessionId` à la bascule, spec qui
      échoue si `mssEmail` est lu), intercepteur, `mss-api.service`, gardes, `closeMailboxSession()`
      partagée logout / bascule, service d'onboarding (B absent), pages `mailbox-select`,
      `mailbox-switcher`, `settings-mailboxes`
- [ ] Écrans Stitch des trois pages référencés dans le task file ; captures `/verify-visual` des
      trois, sans écran blanc
- [ ] `npm run build` + `npm test -- --watch=false --browsers=ChromeHeadless` verts

## Manual Test Plan

- **Pré-requis** : task-303 déployée ; un PS de test disposant de **deux boîtes MSSanté** ouvertes
  à son RPPS chez l'opérateur de test (idéalement chez **deux** opérateurs) ; un **second** PS de
  test pour l'étape 10. À défaut, le banc Dovecot `--users 2 --mailboxes-per-user 2` avec le
  `TestAuthService` Blazor / en-têtes bypass. Seq ouvert sur `api-mail` pour observer les
  fermetures/ouvertures de session (`Logout close order received`, ouverture de pool).
- **Lancer** : `cd Api/Mail && aspire run --project src/AppHost` ; Blazor : `dotnet run` du Shell ;
  Angular : `npx nx serve weda2` ; mobile : `npm start` (ou l'AVD, cf. mémoire projet).
- **Parcours identique sur les trois fronts** :
  1. Connexion PSC avec un compte **sans** boîte → verrou → « Configurer » → boîte 1 → **elle
     s'ouvre immédiatement, sans déconnexion**. En annuaire : boîte 1 `isDefault`.
  2. Avatar → « Ajouter une messagerie » → boîte 2 (case « Toujours ouvrir » **décochée**) →
     bascule automatique sur la boîte 2 ; l'INBOX affichée est **celle de la boîte 2**.
  3. **Bascule** avatar → boîte 1 : indicateur bref, **écran vide** puis contenu de la boîte 1 ;
     **aucun** mail, compteur, dossier patient, brouillon ou signature de la boîte 2 ne reste
     visible, même une fraction de seconde après le chargement. Onglet réseau :
     `POST /sync/logout` avec les anciens en-têtes, puis `Client-Email` et `Client-Session-Id`
     **nouveaux**, `Authorization` et `X-PSC-Token` **identiques**, aucune navigation Keycloak /
     PSC. Seq : fermeture de `boîte2_S2` diffusée, ouverture de `boîte1_S3`. Écran d'audit :
     `MailboxSessionClosed` (boîte 2) puis `MailboxSessionOpened` (boîte 1).
  4. Répéter 3 cinq fois en alternance → toujours propre ; aucun 409 dans la console.
  5. Se **déconnecter puis se reconnecter** : boîte 1 est le défaut ⇒ **connexion directe**, aucun
     écran de sélection. Avatar → « Gérer mes messageries » → retirer le défaut (ou le mettre sur
     aucune) → déconnexion / reconnexion ⇒ **écran de sélection** avec les deux boîtes ; cocher
     « Toujours ouvrir » sur la boîte 2 → ouverte ; reconnexion ⇒ boîte 2 directement.
  6. Attendre un refresh du jeton PSC (~2 min) → liste et boîte courante inchangées.
  7. Envoyer un mail à la boîte 2 depuis un tiers pendant qu'elle est affichée → notification
     temps réel ; basculer sur la 1, envoyer à la 2 → **rien** ne s'affiche sur la 1.
  8. Saisir une boîte **qui n'est pas la sienne** → refus avec le code de la sonde, rien en annuaire.
  9. « Détacher » la boîte courante → bascule vers l'autre ; détacher la dernière → verrou.
  10. Second PS de test sur le même appareil → sa propre liste, aucune boîte du premier ; si le
      premier avait posé un défaut, il ne s'applique évidemment pas au second.
  11. Couper le réseau / jeton PSC absent → boîtes « Hors ligne — lecture locale », bascule possible
      sur les données déjà synchronisées, aucune ouverture IMAP dans Seq.
- **Mobile en plus** : captures `/verify-visual` de `mailbox-select`, `mailbox-switcher`,
  `settings-mailboxes` conformes à Stitch ; l'avatar est dans l'en-tête de l'onglet Messages, la
  gestion dans Paramètres.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — ergonomie de la messagerie ; aucune exigence DSR nouvelle
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — aucune donnée patient manipulée par l'US ; les dossiers patients
  restent **par boîte**, et la **purge totale à la bascule** garantit qu'aucun dossier d'une boîte
  ne s'affiche dans le contexte d'une autre (étape 3 du plan de test — critère central)
- **Authentification PS** : inchangée — PSC via proxy / Keycloak, eIDAS substantiel. **La bascule
  ne déclenche aucune authentification** et n'est possible qu'entre boîtes de la même identité
  PSC, telle que le backend l'évalue (task-303)
- **Habilitations** : rendues par le backend (`compatibleWithSession`) ; les fronts ne décident
  rien, n'évaluent rien, et affichent la raison d'une incompatibilité sans la contourner
- **Interop CI-SIS** : non applicable
- **MSSanté** : boîtes personnelles et organisationnelles, un ou plusieurs opérateurs, affichage
  du domaine d'opérateur par boîte
- **Tracé PGSSI-S** : la bascule est tracée côté backend comme une **clôture puis une ouverture de
  session de boîte** (`MailboxSessionClosed` / `MailboxSessionOpened`, task-303) ; les fronts en
  affichent les libellés dans l'écran d'audit (miroir TS Angular, DTO Blazor)
- **Consentement patient** : non applicable
- **Sécurité / confidentialité** : aucune donnée de boîte persistée sur l'appareil (pas même la
  sélection) ; purge totale de l'état à chaque bascule ; identifiant de session rotaté et refusé
  par le backend s'il est réutilisé ; aucun jeton journalisé côté front
- **Référentiels métier** : RPPS ; adresses MSSanté
- **Hébergement HDS** : inchangé
- **AIPD / impact RGPD** : couverte par la mise à jour de task-303 ; cette vague n'ajoute aucun
  traitement ni aucune donnée locale
