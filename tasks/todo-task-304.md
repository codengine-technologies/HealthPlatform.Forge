# todo-task-304.md — Gestion des comptes de messagerie dans les fronts (vague 2/2) : onboarding par le registre, choix de la boîte à la connexion, avatar → bascule en direct et gestion des comptes (ajouter / supprimer / défaut), chaque bascule = fin de session + nouvelle session — parité Blazor / Angular / mobile

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

Le parcours voulu, mot pour mot (demandes humaines du 2026-09-13) :

> Le médecin se connecte via proxy / Keycloak / PSC. On détecte dans la base centrale qu'il a
> N boîtes compatibles avec son identité PSC. **Boîte par défaut absente ⇒ écran de sélection**
> (avec la possibilité de définir la boîte par défaut) ; **boîte par défaut présente ⇒ on s'y
> connecte directement.** Dans l'interface, le médecin voit **son avatar** ; en cliquant dessus il
> peut choisir une autre adresse : cela le fait **basculer** sur une nouvelle boîte — **toutes les
> données disparaissent** (mails, tableau de bord, etc.) et celles de la boîte choisie se chargent.
> Côté backend, la bascule est **une fin de session puis une nouvelle session**.
>
> **0 boîte ⇒ nouveau parcours d'onboarding, basé sur la base centrale et non plus sur
> proxy / Keycloak.** Depuis l'avatar, le médecin doit pouvoir **ajouter et supprimer des comptes
> de messagerie** : il y a une **gestion des comptes de messagerie** à prévoir.

Un médecin = N BAL MSSanté, chez un ou plusieurs opérateurs, une seule connexion PSC.

Quatre capacités, une par section du comportement commun :

| Capacité | Quand | Écran |
|---|---|---|
| **Onboarding** | 0 boîte rattachée | `mailbox-onboarding` — parcours neuf, porté par le registre |
| **Choix à la connexion** | N boîtes, pas de défaut compatible | `mailbox-select` |
| **Bascule** | avatar → autre adresse | `mailbox-switcher` (+ séquence de bascule) |
| **Gestion des comptes** | avatar → « Gérer mes messageries » | `mailbox-management` — ajouter, supprimer, défaut, états |

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
  `SESSION_MAILBOX_MISMATCH`) un identifiant réutilisé avec une autre boîte.
- **Aucune ré-authentification** : bearer Keycloak et `X-PSC-Token` conservés ; aucune navigation
  vers Keycloak / PSC ; aucun rechargement de page.
- **Deux notions distinctes, à ne surtout pas confondre** (corrigé le 2026-09-13, clarification
  humaine) :
  - **`selectable = false`** — un défaut du **rattachement** : `AuthFailing` → « Authentification
    à cette boîte en échec », `PscIdentityMismatch` → « Cette boîte relève d'une autre identité
    Pro Santé Connect », `Detached`. Affichée **grisée**, raison visible, **non cliquable**,
    jamais masquée.
  - **`capabilities` réduites** — un état de la **session**, pas de la boîte. Hors ligne (pas de
    `X-PSC-Token`), toutes les boîtes actives restent **cliquables et ouvrables** ; le front
    affiche un bandeau « Hors ligne — lecture locale » et **désactive** composer, répondre,
    transférer, marquer lu/non lu, déplacer, supprimer. La consultation, la recherche locale et
    l'ouverture des pièces jointes déjà synchronisées restent disponibles.

  > ⚠️ La rédaction précédente rangeait `NoPscToken` parmi les raisons d'incompatibilité. Composée
  > avec « non compatible ⇒ grisée, non cliquable », elle aurait rendu **toutes** les boîtes
  > inaccessibles hors ligne — l'inverse exact du comportement voulu : *« si un compte Keycloak a
  > déjà été provisionné avec des comptes MSS et qu'on s'y connecte sans Pro Santé Connect, il
  > peut choisir la messagerie qu'il pourra consulter en mode hors ligne »*.
- **Rattacher une boîte = un seul appel** `POST /account/mailboxes` : le backend sonde l'opérateur
  avec le jeton PSC du médecin puis persiste. Le front **n'orchestre plus** « sonde puis
  persistance », et **n'appelle plus jamais le proxy**.

### Ce qui existe aujourd'hui dans les fronts — vérifié, et ce qui en reste

| Front | Aujourd'hui | Devenir |
|---|---|---|
| `client-blazor` | Boîte ← `AuthService.ExtractMssEmailFromJwt` → `UserSessionService.UserEmail` → `HttpRequestService` (`Client-Email`, `Client-Session-Id`). Onboarding task-037 : `MssUnconfigured.razor` (écran de blocage) → `MailSetup.razor` (`/Mail/setup`) → `ValidateImapConnectionAsync` puis `PersistMssEmailAsync` (proxy) → « déconnectez-vous ». `MssOnboardingGuard` sur le claim. Fin de session : `Logout.razor` → `SyncProgressService.LogoutCleanupAsync` | Boîte ← session de boîte (registre). `MssUnconfigured` **remplacé** par le parcours `MailboxOnboarding` ; `MailSetup` **absorbé** par le formulaire d'ajout de la gestion des comptes ; `PersistMssEmailAsync` **supprimé** ; garde sur la liste ; `LogoutCleanupAsync` **réutilisé** à chaque bascule |
| `client-angular` (weda2 + `libs/mss`) | `mssHeadersInterceptor` : `Client-Email` ← `jwtDecoded.mssEmail`, `Client-Session-Id` ← `sid`. Onboarding : `/mss/unconfigured` → `/mss/setup` → `validateImapConnection` puis `persistMssEmail` (proxy, `MSS_KEYCLOAK_PROXY_URL`). `mss-onboarding.guard.ts` sur le claim. SSE `mail-events-stream.service.ts`. Fin de session : `mss-api.service.ts:183` | Idem : `/mss/unconfigured` et `/mss/setup` **remplacés** par `/mss/onboarding`, `/mss/select`, `/mss/accounts` ; `persistMssEmail` et `MSS_KEYCLOAK_PROXY_URL` **supprimés** ; `Client-Session-Id` applicatif, plus jamais `sid` |
| `client-mobile` | `AuthSession.mssEmail` ← `jwtPayload['mssEmail']` ; `sessionId` = `newClientSessionId()` au login (task-282). Onboarding task-159/167 : `/mss-unconfigured`, `/mss-setup`, `mss-onboarding.service.ts` (A puis B proxy). `mssConfiguredGuard`. Fin de session : `logout.service.ts` → `mss-api.service.ts:94` | `mss-onboarding/` **refondu** en `mailbox-onboarding` ; B **supprimé** ; `sessionId` rotaté à chaque bascule ; `closeMailboxSession()` partagée logout / bascule |

Dans les trois : la boîte venait du **jeton**, l'ajout passait par le **proxy**, l'activation
exigeait une **déconnexion**, la fin de session n'était appelée qu'à la **déconnexion**. Seul ce
dernier mécanisme est conservé — et généralisé à la bascule.

## Comportement commun — parité stricte sur les trois fronts

### A. À la connexion

1. Après l'authentification (proxy / Keycloak / PSC), le front appelle `GET /account/mailboxes`.
2. Décision, **dans cet ordre** :
   - **0 boîte active** ⇒ **parcours d'onboarding** (§B). Pas d'écran de blocage : c'est un
     parcours d'entrée, pas une impasse.
   - **une boîte par défaut compatible** ⇒ **connexion directe** à cette boîte, aucun écran.
   - **sinon** (pas de défaut, défaut non compatible, ou plusieurs boîtes sans défaut) ⇒
     **écran de sélection** `mailbox-select` : liste des boîtes (adresse, opérateur, état ;
     non compatibles grisées avec raison), une case **« Toujours ouvrir cette messagerie »**
     (⇒ `PUT /account/mailboxes/{id}/default`), bouton « Ouvrir ». Une seule boîte compatible
     sans défaut ⇒ l'écran s'affiche quand même, pré-sélectionnée — c'est là que le médecin pose
     son défaut.
3. **Aucune persistance de la sélection sur l'appareil** : le défaut vit dans l'annuaire et suit
   le médecin d'un poste à l'autre. La sélection sans défaut vaut pour la session en cours.

### B. Onboarding — 0 boîte, parcours neuf porté par le registre

4. **Écran d'accueil** `mailbox-onboarding` : identité du PS telle que l'authentification l'a
   établie (nom, RPPS — lus de la session, jamais saisis), texte « Rattachez votre première
   messagerie MSSanté », champ adresse MSSanté, bouton « Rattacher ». Validation de forme locale
   (RFC), rien d'autre côté front.
5. « Rattacher » ⇒ **un seul appel** `POST /account/mailboxes {email}`. Le backend sonde
   l'opérateur avec le jeton PSC du médecin et persiste ; la première boîte est **par défaut**
   automatiquement. Erreurs par `code` (`AUTH_FAILED`, `HOST_UNREACHABLE`, `MAILBOX_NOT_FOUND`,
   `INVALID_EMAIL`, `PSC_IDENTITY_CONFLICT`), le formulaire reste éditable. **Aucun appel au proxy,
   aucune écriture Keycloak, aucune déconnexion.**
6. Succès ⇒ écran « Messagerie rattachée » avec deux boutons : **« Ouvrir ma messagerie »** (⇒
   ouverture de session sur la boîte) et **« Rattacher une autre messagerie »** (retour au champ,
   la boîte suivante n'est pas par défaut). Le médecin qui a deux boîtes chez deux opérateurs les
   rattache toutes dès l'onboarding, en une fois.
7. Hors ligne (pas de `X-PSC-Token`) : l'onboarding est **impossible** (la sonde exige le jeton) ;
   message explicite « Connexion Pro Santé Connect requise pour rattacher une messagerie », pas de
   formulaire.

### C. Avatar et sélecteur

8. **L'avatar** du médecin (en-tête web ; en-tête de l'onglet Messages sur mobile) est le point
   d'entrée unique : initiales ou image, adresse de la boîte courante en libellé. Un clic ouvre le
   **sélecteur** `mailbox-switcher` : identité du PS (nom, RPPS), boîte courante cochée, autres
   boîtes (adresse, opérateur, état ; non compatibles grisées avec raison), puis deux actions :
   **« Ajouter une messagerie »** (⇒ formulaire d'ajout de la gestion, §E) et **« Gérer mes
   messageries »** (⇒ `mailbox-management`, §E).
9. Choisir une autre boîte compatible déclenche la **bascule** (§D). Une boîte non compatible est
   désactivée, sa raison affichée.

### D. Bascule — fin de session, page blanche, nouvelle session

10. **Séquence, dans cet ordre, sans étape optionnelle** :
    1. **Gel** de l'interface (indicateur « Changement de messagerie… ») et **annulation** de toutes
       les requêtes en vol de la boîte sortante ; fermeture du flux SSE.
    2. `POST /sync/logout` avec les en-têtes de la session **sortante** (`Client-Email` ancienne
       boîte, `Client-Session-Id` ancien identifiant). Best-effort : un échec est journalisé côté
       front et **ne bloque pas** la bascule (filet d'expiration serveur, comme à la déconnexion).
    3. **Purge totale de l'état applicatif** : stores / signaux / caches de mails, dossiers,
       compteurs, tableau de bord, recherche, dossiers patients, contacts, brouillons non envoyés
       (confirmation préalable s'il en reste un), réglages et signature, pièces jointes en cache,
       notifications affichées. **Rien de la boîte sortante ne doit survivre.** Le bearer, le jeton
       PSC et l'identité du PS sont **conservés**.
    4. **Nouvel identifiant de session** (`crypto.randomUUID()` — `newClientSessionId()` côté
       mobile, équivalent web) et nouvelle boîte courante.
    5. Réabonnement SSE avec `?mailbox=` ; navigation vers la racine de la messagerie (INBOX) ;
       chargement des données de la nouvelle boîte.
11. **Aucun rechargement de page**, aucun `forceLoad`, aucune redirection Keycloak / PSC. Onglet
    réseau : `Client-Email` et `Client-Session-Id` changent, `Authorization` et `X-PSC-Token`
    **ne changent pas**.
12. Un 409 `SESSION_MAILBOX_MISMATCH` reçu après une bascule est un **bug de front** (identifiant
    non rotaté) : journalisé comme erreur, nouvelle rotation, rejeu — jamais silencieux.

### E. Gestion des comptes de messagerie — `mailbox-management`

13. Page dédiée, accessible depuis l'avatar (« Gérer mes messageries ») et, sur mobile, depuis
    l'onglet Paramètres (entrée « Messageries »). Elle présente **toutes** les boîtes du compte, y
    compris les non compatibles (avec raison) et, sur demande (« Afficher les messageries
    détachées »), les `Detached` avec leur date.
14. Par boîte : adresse, opérateur (domaine), état, `attachedAt`, dernier login réussi, badge
    **« Par défaut »**, badge **« Courante »** ; actions :
    - **« Définir par défaut »** ⇒ `PUT /account/mailboxes/{id}/default` (un seul défaut ; le
      badge se déplace).
    - **« Supprimer »** ⇒ confirmation explicite qui rappelle ce que ça fait et ne fait pas
      (« La messagerie ne sera plus accessible depuis ce compte. Vos données ne sont pas
      supprimées immédiatement et restent soumises aux règles de conservation. ») ⇒
      `DELETE /account/mailboxes/{id}`. Supprimer la **courante** ⇒ bascule (§D) vers le défaut,
      sinon écran de sélection ; supprimer la **dernière** ⇒ retour au parcours d'onboarding (§B).
    - **« Ré-essayer l'authentification »** sur une boîte `AuthFailing` ⇒ simple tentative
      d'ouverture (le backend remet `Active` au premier succès XOAUTH2).
15. **« Ajouter une messagerie »** : le même formulaire qu'en onboarding (champ adresse, un seul
    appel `POST`, erreurs par code), avec la case « Toujours ouvrir cette messagerie » ; succès ⇒
    proposition d'y basculer maintenant.
16. La page se rafraîchit après chaque action et au retour au premier plan ; toute action est
    reflétée dans le sélecteur sans rechargement.

### F. Ce qui disparaît des fronts

17. `persistMssEmail` / `PersistMssEmailAsync`, l'appel `PUT {proxy}/v1/admin/mss-profile` et sa
    configuration (`MSS_KEYCLOAK_PROXY_URL`, `Oidc:ApiServerUrl` pour cet usage, exclusion de
    l'`auth.interceptor` Angular) ; les écrans de blocage `MssUnconfigured` / `/mss/unconfigured` /
    `/mss-unconfigured` ; les messages « déconnectez-vous puis reconnectez-vous ».
18. **Toute lecture de claim MSS** (`mssEmail`, `mssSub`, `mssRpps`) : le backend absorbe les jetons
    hérités (`LegacyClaimsMigration`, task-303). `Client-Session-Id` n'est **plus jamais** la claim
    `sid` (Angular) — identifiant applicatif tiré au login et à chaque bascule, comme le mobile le
    fait déjà (task-282).

### G. Erreurs

19. `MAILBOX_NOT_ATTACHED` / `MAILBOX_PSC_MISMATCH` en cours de session ⇒ recharger la liste,
    bascule (§D) vers le défaut compatible ou écran de sélection, toast « Cette messagerie n'est
    plus disponible pour votre session » ; `MAILBOX_REQUIRED` ⇒ écran de sélection ou onboarding.
    Les gestionnaires 403 existants (`Mss403Handler`, équivalents) sont mis à jour.

## Par front

### `client-blazor`
- Nouveau `MailboxSessionService` (liste, courante, compatibilité, défaut, **bascule §D**,
  rotation de `ClientSessionId`) ; `AuthService` cesse d'alimenter `UserSessionService.UserEmail`
  depuis le JWT (`ExtractMssEmailFromJwt` retiré) ; `HttpRequestService.UpdateClientEmailHeader`
  lit la session de boîte ; `SyncProgressService.LogoutCleanupAsync` réutilisé pour la bascule ;
  `MssOnboardingGuard` remplacé par une garde « boîte ouverte » qui route vers `/Mail/onboarding`,
  `/Mail/select` ou laisse passer. Pages : `MailboxOnboarding.razor` (`/Mail/onboarding`, remplace
  `MssUnconfigured` + `MailSetup`), `MailboxSelect.razor` (`/Mail/select`), `MailboxManagement.razor`
  (`/Mail/accounts`) ; composant `MailboxSwitcher` (avatar + menu) dans l'en-tête du module Mss ;
  formulaire d'ajout partagé onboarding / gestion. `Mss403Handler` mis à jour. Réutiliser les
  composants existants (consigne). `Localizer`, `data-testid` partout.

### `client-angular` (code-only)
- `mssHeadersInterceptor` : `Client-Email` et `Client-Session-Id` ← store de session de boîte ;
  garde de route unique remplaçant `mss-onboarding.guard.ts` (route vers `/mss/onboarding`,
  `/mss/select`, ou passe) ; `MssOnboardingService` renommé `MailboxAccountsService` :
  `listMailboxes` / `attachMailbox` / `detachMailbox` / `setDefaultMailbox`, `persistMssEmail` et
  `MSS_KEYCLOAK_PROXY_URL` supprimés ; `mail-events-stream.service.ts` : `?mailbox=`, fermeture à la
  bascule, réabonnement ; **store de session de boîte** (signal) dont la bascule appelle `reset()`
  sur chaque store MSS (méthode obligatoire) et annule les requêtes en vol (garde de version) ;
  pages `/mss/onboarding`, `/mss/select`, `/mss/accounts` ; avatar + `mailbox-switcher` dans le
  shell MSS ; formulaire d'ajout partagé ; libellés FR en dur (norme MSS). **Miroir TS de
  `AuditActionType`** (`libs/mss/src/core/models/audit.model.ts`) : **5** nouveaux membres, valeurs
  ordinales explicites ; libellés dans l'écran d'audit.

### `client-mobile`
- `session.model.ts` : `mssEmail` → `currentMailbox` + `mailboxes[]` ; `sessionFromTokenAggregate`
  **ne lit plus `mssEmail`** ; `sessionId` **rotaté à chaque bascule** ; `MssHeadersInterceptor` et
  `mss-api.service.ts` lisent la session de boîte ; `logout.service.ts` : séquence extraite en
  `closeMailboxSession()`, réutilisée par la bascule ; `mssConfiguredGuard` remplacé par la garde
  unique (`/mailbox-onboarding`, `/mailbox-select`, ou passe) ; module `mss-onboarding/` refondu :
  pages `mailbox-onboarding`, `mailbox-select`, `mailbox-management` (aussi depuis Paramètres →
  « Messageries »), feuille `mailbox-switcher` depuis l'avatar de l'en-tête Messages ; formulaire
  d'ajout partagé ; B supprimé. Purge des stores à la bascule. `POST Settings` reste un
  remplacement en bloc — muter par spread, **par boîte**.
- **Écrans Stitch** (titre = nom kebab-case du composant) : **`mailbox-onboarding`**,
  **`mailbox-select`**, **`mailbox-switcher`**, **`mailbox-management`**. `/stitch-design` avant de
  coder, `/verify-visual` capture les quatre.

## Definition of Done

### Transverse
- [ ] Build passes on **every** listed repo (0 errors) ; tests pass (0 failures)
- [ ] `client-blazor` bumpé à la version `dtos-mss` publiée par task-303 (**pas `sdk`** : task-305 en a retiré la référence, et le contrat du registre a quitté le SDK le 2026-09-13)
- [ ] Sur les **trois** fronts : plus aucune lecture de `mssEmail` / `mssSub` / `mssRpps` / `sid`
      (pour `Client-Session-Id`), aucun appel à `mss-profile`, aucune URL de proxy Keycloak, aucun
      écran « non configurée / déconnectez-vous » dans le code de production — vérifié par grep
- [ ] Aucune évaluation locale de la compatibilité PSC (spec qui échoue si un front compare un
      `sub`) ; aucune persistance de boîte sur l'appareil
- [ ] Aucune chaîne en dur côté Blazor (Localizer) ; FR en dur côté Angular MSS et mobile ;
      `data-testid` sur tous les éléments interactifs (avatar, sélecteur, onboarding, sélection,
      gestion, formulaires)

### Tests communs aux trois fronts (une spec / un test par front, mêmes cas)
- [ ] **Connexion** : 0 boîte ⇒ onboarding ; défaut compatible ⇒ connexion directe **sans**
      écran ; N boîtes sans défaut ⇒ sélection ; défaut **non** compatible ⇒ sélection avec le
      défaut grisé et sa raison ; case « Toujours ouvrir » ⇒ `PUT …/default` puis connexion
- [ ] **Onboarding** : identité du PS affichée depuis la session (non éditable) ; « Rattacher » ⇒
      **exactement un** appel `POST /account/mailboxes`, **aucun** appel à une autre origine ;
      erreurs par code (les 5) ⇒ formulaire éditable, rien d'autre ; succès ⇒ écran « rattachée »
      avec « Ouvrir » (⇒ session ouverte sur la boîte) et « Rattacher une autre » (⇒ champ vide,
      boîte suivante non défaut) ; hors ligne ⇒ formulaire absent, message explicite
- [ ] **Gestion des comptes** : liste complète avec états et badges ; « Définir par défaut » ⇒
      `PUT`, badge déplacé ; « Supprimer » ⇒ confirmation puis `DELETE` ; supprimer la courante ⇒
      bascule vers le défaut ou sélection ; supprimer la dernière ⇒ onboarding ; « Afficher les
      détachées » ⇒ `?includeDetached=true` ; « Ajouter » ⇒ même formulaire qu'en onboarding, case
      défaut, proposition de bascule
- [ ] **Bascule — séquence** : requêtes en vol annulées → SSE fermé → `POST /sync/logout` avec les
      **anciens** en-têtes → purge → **nouveau** `Client-Session-Id` → nouvelle `Client-Email` →
      SSE `?mailbox=` → chargement. Test qui échoue si l'ordre change ou si une étape manque
- [ ] **Bascule — page blanche** : après la purge et avant le premier chargement, **tous** les
      stores/états MSS sont à leur valeur initiale (test qui énumère les stores) ; une réponse
      tardive de la boîte sortante est **ignorée** (garde de version)
- [ ] **Bascule — identité conservée** : `Authorization` et `X-PSC-Token` identiques avant/après ;
      aucune navigation Keycloak / PSC ; aucun rechargement (`forceLoad` / `location.reload`
      absents — grep)
- [ ] **Bascule — échec de `/sync/logout`** (500 / réseau) ⇒ journalisé, la bascule **aboutit**
- [ ] 409 `SESSION_MAILBOX_MISMATCH` ⇒ erreur journalisée + rotation + rejeu, jamais silencieux
- [ ] Refresh du jeton PSC (rotation simulée) ⇒ liste et boîte courante **inchangées**
- [ ] **Hors ligne, le sélecteur reste utilisable** : session sans `X-PSC-Token`, compte à
      2 boîtes actives ⇒ les deux sont **cliquables**, l'ouverture réussit, bandeau « Hors ligne —
      lecture locale », actions d'écriture désactivées. Sur les **trois** fronts
- [ ] Sélecteur : `selectable = false` grisées, raison affichée, **non cliquables** ; « Ajouter » et
      « Gérer » mènent aux bons écrans
- [ ] `MAILBOX_PSC_MISMATCH` / `MAILBOX_NOT_ATTACHED` en cours de session ⇒ rechargement de la
      liste + bascule de repli + toast

### `client-blazor`
- [ ] bUnit : `MailboxOnboarding`, `MailboxSelect`, `MailboxManagement`, `MailboxSwitcher`
      (avatar), formulaire d'ajout partagé ; garde de route (trois issues) ; `MailboxSessionService`
      : séquence de bascule (mocks ordonnés) ; tests `MssUnconfigured*` / `MailSetupPageTests` /
      `MssOnboardingServiceTests` **remplacés** (pas laissés en place sur du code supprimé)

### `client-angular` (code-only)
- [ ] Specs : intercepteur (jamais du JWT), garde unique, `MailboxAccountsService`, flux SSE, store
      de session (bascule ⇒ `reset()` de chaque store, garde de version), pages `/mss/onboarding`,
      `/mss/select`, `/mss/accounts`, avatar + sélecteur, formulaire partagé ; spec de contrat du
      miroir `AuditActionType` (5 valeurs ordinales)
- [ ] `npm run build` + `npm test` verts sur la branche courante ; `/lint-angular` scope `scope:mss`

### Outillage visuel et QA — **sans quoi cette US casse la chaîne autonome**

`/verify-visual` est une étape de la chaîne (règle 13), et il capture les écrans mobiles avec une
API **mockée par fixtures**. Trois ruptures certaines, toutes à traiter **dans cette US** :

- [ ] **`Tools/visual-verify/capture.mjs` — fixture des boîtes.** Le mock `**/api/**` rend
      `[]` par défaut sur tout `GET` non mappé : après cette US, `GET /account/mailboxes` rendrait
      `[]` ⇒ **0 boîte ⇒ écran d'onboarding pour *toutes* les captures mobiles**. Ajouter une
      fixture `mailboxes.json` (une boîte `Active`, `isDefault`, `compatibleWithSession: true`)
      et son entrée dans `API_ROUTES`
- [ ] **Sessions factices.** `FAKE_SESSION` et `TOKEN_ONLY_SESSION` (`capture.mjs`) sont façonnées
      sur `userEmail` / claim `mssEmail` — le modèle que cette US remplace. `FAKE_SESSION` passe à
      `currentMailbox` ; `TOKEN_ONLY_SESSION`, qui n'existait que pour capturer `mss-unconfigured`
      et `mss-setup`, est **remplacée** par une session « 0 boîte » servant `mailbox-onboarding`
- [ ] **`Tools/visual-verify/screens.json`** : entrées `mss-unconfigured` et `mss-setup`
      **retirées** (écrans supprimés), entrées `mailbox-onboarding`, `mailbox-select`,
      `mailbox-switcher`, `mailbox-management` **ajoutées** avec leurs routes et actions
- [ ] **Galerie de documentation** : `Docs/epics/img/screens/client-mobile/mss-setup.png` et
      `mss-unconfigured.png` sont périmés ⇒ remplacés par les captures des quatre nouveaux écrans
      (`/verify-visual` les produit ; `/tech-writer` les intègre au doc d'EPIC)
- [ ] **Suite `/qa`** (`Client/Mobile/e2e/`, Playwright **headed**, login PSC réel) : le parcours
      post-connexion change (écran de sélection conditionnel). Les specs concernées sont mises à
      jour **ou** explicitement marquées à ré-aligner dans `e2e/README.md`. `/qa` est
      human-triggered : le tir de validation est un acte humain, pas un critère de `/review`

### `client-mobile`
- [ ] Specs : `session.model` (`currentMailbox`, rotation, spec qui échoue si `mssEmail` est lu),
      intercepteur, `mss-api.service`, garde unique, `closeMailboxSession()` partagée, service
      comptes (B absent), pages `mailbox-onboarding`, `mailbox-select`, `mailbox-management`,
      feuille `mailbox-switcher`, formulaire partagé
- [ ] Écrans Stitch des quatre pages référencés dans le task file ; captures `/verify-visual` des
      quatre, sans écran blanc
- [ ] `npm run build` + `npm test -- --watch=false --browsers=ChromeHeadless` verts

## Manual Test Plan

- **Pré-requis** : task-303 déployée ; un PS de test disposant de **deux boîtes MSSanté** ouvertes
  à son RPPS chez l'opérateur de test (idéalement chez **deux** opérateurs) ; un **second** PS de
  test pour l'étape 11. À défaut, le banc Dovecot `--users 2 --mailboxes-per-user 2` avec le
  `TestAuthService` Blazor / en-têtes bypass. Seq ouvert sur `api-mail`.
- **Lancer** : `cd Api/Mail && aspire run --project src/AppHost` ; Blazor : `dotnet run` du Shell ;
  Angular : `npx nx serve weda2` ; mobile : `npm start` (ou l'AVD, cf. mémoire projet).
- **Parcours identique sur les trois fronts** :
  1. **Onboarding** — connexion PSC avec un compte **sans** boîte → écran d'accueil avec nom et
     RPPS du PS → saisir la boîte 1 → « Rattacher » → écran « Messagerie rattachée ». Onglet
     réseau : **un seul** appel `POST /account/mailboxes`, **aucun** appel vers le proxy / Keycloak.
     « Rattacher une autre » → boîte 2 → puis « Ouvrir ma messagerie » → boîte 1 (défaut) s'ouvre,
     **sans déconnexion**. Dans le registre : deux rattachements, boîte 1 `isDefault`.
  2. Saisir dans le formulaire une boîte **qui n'est pas la sienne** → refus avec le code de la
     sonde, formulaire éditable, rien en registre.
  3. **Bascule** — avatar → boîte 2 : indicateur bref, **écran vide** puis contenu de la boîte 2 ;
     **aucun** mail, compteur, dossier patient, brouillon ou signature de la boîte 1 ne reste
     visible. Onglet réseau : `POST /sync/logout` avec les anciens en-têtes, puis `Client-Email` et
     `Client-Session-Id` **nouveaux**, `Authorization` et `X-PSC-Token` **identiques**. Seq :
     fermeture de `boîte1_S1`, ouverture de `boîte2_S2`. Audit : `MailboxSessionClosed` puis
     `MailboxSessionOpened`.
  4. Répéter 3 cinq fois en alternance → toujours propre ; aucun 409 dans la console.
  5. **Connexion directe** — déconnexion / reconnexion : boîte 1 est le défaut ⇒ ouverte
     directement, aucun écran.
  6. **Gestion des comptes** — avatar → « Gérer mes messageries » : deux boîtes, badges « Par
     défaut » (1) et « Courante » ; « Définir par défaut » sur la 2 → badge déplacé ; déconnexion /
     reconnexion ⇒ boîte 2 directement.
  7. **Sélection** — dans la gestion, retirer le défaut (ou le mettre sur une boîte rendue
     `AuthFailing` par le banc) → déconnexion / reconnexion ⇒ **écran de sélection**, défaut grisé
     avec raison le cas échéant ; cocher « Toujours ouvrir » sur la 1 → ouverte.
  8. **Suppression** — gestion → « Supprimer » la courante → confirmation (texte sur la
     conservation) → bascule vers le défaut ; « Afficher les détachées » → elle apparaît avec sa
     date ; en base, sa base `u_…` **existe toujours**. Supprimer la dernière → retour au parcours
     d'onboarding.
  9. Attendre un refresh du jeton PSC (~2 min) → liste et boîte courante inchangées.
  10. Envoyer un mail à la boîte 2 depuis un tiers pendant qu'elle est affichée → notification temps
      réel ; basculer sur la 1, envoyer à la 2 → **rien** ne s'affiche sur la 1.
  11. Second PS de test sur le même appareil → sa propre liste (ou son onboarding), aucune boîte du
      premier.
  12. Hors ligne (jeton PSC absent) → boîtes « Hors ligne — lecture locale », bascule possible sur
      les données synchronisées ; onboarding et ajout **indisponibles** avec message explicite.
  13. Écran d'audit : `MailboxAttached` ×2, `MailboxDefaultChanged`, `MailboxDetached` ×2,
      `MailboxSessionClosed` / `MailboxSessionOpened` par bascule — libellés lisibles.
- **Mobile en plus** : captures `/verify-visual` de `mailbox-onboarding`, `mailbox-select`,
  `mailbox-switcher`, `mailbox-management` conformes à Stitch ; l'avatar est dans l'en-tête de
  l'onglet Messages, la gestion aussi accessible depuis Paramètres → « Messageries ».
- **Non-régression de l'outillage visuel** : relancer `/verify-visual` sur **un écran déjà
  documenté** (`inbox`, `mail-detail`) → la capture montre bien la boîte de démonstration, **pas**
  l'écran d'onboarding. C'est la preuve que la fixture `mailboxes.json` est en place ; sans elle,
  toute la galerie devient l'écran d'onboarding.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — ergonomie et parcours d'entrée de la messagerie ; aucune exigence
  DSR nouvelle
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — aucune donnée patient manipulée par l'US ; les dossiers patients
  restent **par boîte**, et la **purge totale à la bascule** garantit qu'aucun dossier d'une boîte
  ne s'affiche dans le contexte d'une autre (étape 3 du plan de test — critère central)
- **Authentification PS** : inchangée — PSC via proxy / Keycloak, eIDAS substantiel. L'onboarding
  **ne touche plus à l'identité** (aucune écriture Keycloak, aucun appel proxy) : il rattache des
  boîtes à un compte déjà authentifié. **La bascule ne déclenche aucune authentification** et n'est
  possible qu'entre boîtes de la même identité PSC, telle que le backend l'évalue (task-303)
- **Habilitations** : rendues par le backend (`compatibleWithSession`, sonde opérateur au
  rattachement) ; les fronts ne décident rien, n'évaluent rien, et affichent la raison d'une
  incompatibilité sans la contourner
- **Interop CI-SIS** : non applicable
- **MSSanté** : boîtes personnelles et organisationnelles, un ou plusieurs opérateurs, affichage du
  domaine d'opérateur par boîte ; le rattachement passe par l'authentification XOAUTH2 chez
  l'opérateur, jamais par une simple déclaration
- **Tracé PGSSI-S** : rattachement / détachement / défaut et frontières de session tracés côté
  backend (task-303) ; les fronts en affichent les libellés dans l'écran d'audit (miroir TS Angular,
  DTO Blazor). La suppression d'une boîte est présentée au médecin pour ce qu'elle est : un
  détachement, pas un effacement — les règles de conservation s'appliquent
- **Consentement patient** : non applicable
- **Sécurité / confidentialité** : aucune donnée de boîte persistée sur l'appareil (pas même la
  sélection) ; purge totale de l'état à chaque bascule ; identifiant de session rotaté et refusé
  par le backend s'il est réutilisé ; aucun jeton journalisé côté front
- **Référentiels métier** : RPPS ; adresses MSSanté
- **Hébergement HDS** : inchangé
- **AIPD / impact RGPD** : couverte par la mise à jour de task-303 ; cette vague n'ajoute aucun
  traitement ni aucune donnée locale
