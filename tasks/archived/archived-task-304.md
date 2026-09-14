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

### A bis. Les sept états d'entrée — table de décision exhaustive

> Demande humaine du 2026-09-13 : « 1re connexion Keycloak seulement ⇒ on fait quoi ? […] Ces cas
> doivent être soigneusement étudiés. »

Deux axes seulement : **la session porte-t-elle un jeton PSC**, et **combien de BAL sélectionnables
le compte a-t-il**. Les fronts n'ont aucune autre information à interpréter — le backend rend
`selectable` et `capabilities` par boîte (task-303, règles 4 et 5).

| # | Session | BAL rattachées | Écran | Actions d'écriture |
|---|---|---|---|---|
| **1** | **KC seul** | **0** | **`mailbox-psc-required`** — écran dédié : « Aucune messagerie n'est rattachée à votre compte. Le rattachement d'une messagerie MSSanté exige une connexion Pro Santé Connect. » + bouton **Se connecter avec Pro Santé Connect**. **Aucun formulaire.** | — |
| **2** | KC + PSC | 0 | **Onboarding** (§B) — rattachement de la 1re BAL, sonde IMAP XOAUTH2, `isDefault = true` | complètes |
| **3** | KC + PSC | 1, sélectionnable | **Connexion directe**, aucun écran | complètes |
| **4** | KC + PSC | N, défaut sélectionnable | **Connexion directe** au défaut | complètes |
| **5** | KC + PSC | N, pas de défaut **ou** défaut non sélectionnable | **`mailbox-select`** | complètes |
| **6** | **KC seul** | **≥ 1** | **Connexion directe au défaut** (arbitrage humain du 2026-09-13), sinon `mailbox-select`. **Toutes les BAL actives sont cliquables.** Bandeau persistant « Hors ligne — lecture locale » | **désactivées** |
| **7** | KC + PSC | ≥ 1 mais **aucune** sélectionnable (toutes `AuthFailing` / `Detached`) | `mailbox-select`, toutes grisées avec leur raison, **+ « Ajouter une messagerie » actif** — jamais une impasse | complètes |

**Le cas 1 est le cas neuf**, et il est le seul qui n'existait pas avant : jusqu'ici le claim
`mssEmail` garantissait qu'une session authentifiée avait toujours une boîte. Ce n'est plus vrai.
Ce n'est **pas** une erreur ni un blocage — c'est l'état normal d'un compte Keycloak qui n'a pas
encore joué l'onboarding. L'écran l'explique et propose la seule action utile.

**Le cas 6 est celui qui porte l'exigence hors ligne** : un compte déjà provisionné, connecté sans
Pro Santé Connect, **choisit sa messagerie et la consulte**. Voir §D pour les affordances.

> **Arbitrage du 2026-09-13 : hors ligne, on va directement au défaut** — même comportement qu'en
> ligne, pas d'écran intercalé. La question posée était : afficher le sélecteur rendrait la lecture
> seule visible **avant** toute tentative d'écriture, alors que la connexion directe laisse le
> praticien découvrir la dégradation en cliquant sur « Répondre ».
>
> **La fluidité l'emporte, donc le bandeau porte seul la charge d'informer.** Conséquence
> non négociable : il est **présent au premier rendu**, persistant, et **au-dessus** de la liste
> des messages — jamais un toast, jamais un état qui n'apparaît qu'à l'échec d'une action. Les
> commandes d'écriture sont désactivées **visiblement** (grisées, pas masquées) dès l'ouverture,
> avec l'infobulle « Hors ligne — lecture locale ».

### A ter. Transitions — ce qui fait passer d'un état à l'autre

| Depuis | Événement | Vers |
|---|---|---|
| 1 | connexion Pro Santé Connect | 2 (onboarding) |
| 2 | 1re BAL rattachée | 3 |
| 3 / 4 / 5 | « Ajouter une messagerie » (§C) | 4 ou 5 |
| 4 / 5 | suppression d'une BAL non dernière | 4 ou 5 |
| 3 / 4 / 5 | suppression de la **dernière** BAL | **2** (onboarding), pas 1 — la session porte PSC |
| 6 | connexion Pro Santé Connect | 3 / 4 / 5 selon le compte |
| 3..7 | expiration / absence du jeton PSC en cours de session | **6** — bascule en lecture locale, **sans déconnexion** |

### D. Hors ligne — ce qui reste possible, ce qui ne l'est pas

**Gestion des comptes = en ligne uniquement.** Rattacher exige une sonde IMAP XOAUTH2 ; détacher et
changer le défaut sont des actes d'administration du compte. Les trois sont **désactivés** hors
ligne, avec l'explication « Connexion Pro Santé Connect requise », jamais masqués.

| | Hors ligne (cas 6) |
|---|---|
| Consulter la liste, lire un message, ouvrir une PJ déjà synchronisée | ✅ |
| Recherche locale | ✅ |
| Basculer d'une BAL à l'autre | ✅ (fin de session + nouvelle session, comme en ligne) |
| Composer, répondre, transférer | ❌ désactivé |
| Marquer lu/non lu, déplacer, supprimer | ❌ désactivé |
| Ajouter / supprimer une BAL, changer le défaut | ❌ désactivé |

Aucune de ces désactivations n'est une nouveauté fonctionnelle : le backend les refuse déjà
(`CanAccessImap`, `CanSendEmail`, `CanModifyFlags` valent `false` hors ligne). Les fronts cessent
simplement de proposer une action qui finirait en erreur.

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
- [ ] **Les sept états d'entrée (§A bis) sont couverts par un test chacun, sur les trois fronts** —
      c'est la table de décision, pas une liste d'exemples
- [ ] **Cas 1 — compte Keycloak seul, 0 BAL** : écran `mailbox-psc-required` avec explication et
      bouton Pro Santé Connect, **aucun formulaire de rattachement**, aucune erreur technique
      affichée. C'est l'état neuf que le claim `mssEmail` rendait impossible jusqu'ici
- [ ] **Cas 6 — hors ligne avec défaut : ouverture directe du défaut**, aucun écran intercalé
      (arbitrage du 2026-09-13). Le bandeau « Hors ligne — lecture locale » est visible **au
      premier rendu**, persistant, au-dessus de la liste — test qui échoue s'il n'apparaît qu'après
      une tentative d'écriture. Composer / répondre / transférer / drapeaux **grisés et visibles**
      dès l'ouverture. Sur les **trois** fronts
- [ ] **Cas 6 sans défaut** : `mailbox-select`, les BAL actives **cliquables**, l'ouverture réussit
      en lecture locale. Sur les **trois** fronts
- [ ] **Cas 7 — aucune BAL sélectionnable** : toutes grisées avec raison **et** « Ajouter une
      messagerie » actif ⇒ jamais d'impasse
- [ ] Transition « perte du jeton PSC en cours de session » ⇒ bascule en cas 6 **sans
      déconnexion** ni perte de la boîte ouverte
- [ ] Suppression de la **dernière** BAL avec session PSC ⇒ retour à l'**onboarding** (cas 2),
      jamais à l'écran `mailbox-psc-required`
- [ ] Gestion des comptes (ajouter / supprimer / défaut) **désactivée hors ligne** avec
      l'explication, jamais masquée
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

## Timings

*(généré par `tools/timing/report.sh --task task-304 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 35 s | — | — | — | — |
| /develop | ok | 1 h 03 min | 20 (2 min 49 s) | 17 (2 min 48 s) | — | client-blazor 14B/6T, client-angular 2B/3T, client-mobile 4B/8T |
| /lint-angular | ok | 4 min 08 s | 1 (17 s) | 1 (21 s) | — | 2 itération(s), client-angular 1B/1T |
| /lint-mobile | ok | 25 s | — | — | — | — |
| /verify-visual | skipped | 18 s | — | — | — | Tools/visual-verify absent du poste (non versionne) |
| /review | ok | 5 min 20 s | 5 (45 s) | 5 (44 s) | — | client-blazor 2B/2T, client-mobile 1B/1T, client-angular 2B/2T |
| /tech-writer | ok | 2 min 08 s | — | — | — | — |
| **Total cycle** | | **1 h 16 min** | **26 (3 min 52 s)** | **23 (3 min 54 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : lint ×4 (50 s)

## Branches

Nom unique sur tous les repos : `feat/task-304-selection-et-bascule-de-boite`

- `client-blazor` (pushed) : https://github.com/codengine-technologies/HealthPlatform.Client/tree/feat/task-304-selection-et-bascule-de-boite
- `client-mobile` (pushed) : https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-304-selection-et-bascule-de-boite
- `dtos-mss` (pushed, auto-inclus) : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-304-selection-et-bascule-de-boite — sans commit si aucun contrat ne bouge (les contrats de la vague 1 sont déjà publiés en **474.0.0**)
- `client-angular` (code-only) : la forge écrit sur la branche checked out dans `Client/Angular/` — snapshot au `/start` : `feature/nova-rewriting-mss`. Humain gère branche, commit, push, PR TFS.

> **Contexte vague 2/2 (règle 11)** — les PRs de **task-303** (api-mail #236, dtos #32) sont
> ouvertes en `awaiting-us-completion`. Le paquet DTO **474.0.0** est publié ; `client-blazor`
> est épinglé en **454.0.0** sur `develop` et doit être bumpé pour voir les contrats de la
> vague 1. `api-mail` n'est **pas** dans le scope de cette task : le backend vit sur
> `feat/task-303-*`, dont la PR est en conflit avec `develop` (à résoudre avant le merge final).

## Stitch design log

Projet `client-mobile` (id `10088502293310567548`), design system « Clinical Precision »
(Public Sans, primaire `#005eb8`, rayons 4/8/12 px, listes ≥ 56 px, cibles tactiles ≥ 44 px).
Aucun des quatre écrans n'existait : les quatre ont été **créés** (convention : titre Stitch =
nom kebab-case du composant).

| Écran | Statut | Id Stitch | Capture |
|---|---|---|---|
| `mailbox-select` | créé | `3f84e49c6242414880e6bffa7036127b` | rendue par le MCP |
| `mailbox-switcher` | créé | `8da2543c595f494d990094223e74ed3e` | rendue par le MCP |
| `mailbox-management` | créé | `d0d02a1abf344d589119bf5b34fdec2c` | rendue par le MCP |
| `mailbox-onboarding` | **timeout de génération** | à relever | — |

> ⚠️ **`mailbox-onboarding` : timeout de `generate_screen_from_text`.** C'est le piège connu du
> connecteur — un timeout signale un **succès probable côté Stitch**, jamais un échec. L'écran
> n'a donc **pas** été re-généré (une re-génération est la source des doublons) ; son
> identifiant reste à relever dans l'UI Stitch par diff des `screenInstances`.

**Ce que la référence a apporté au code** (traduit en Ionic, jamais collé) : bandeau hors ligne
ambre **persistant et au-dessus de la liste** plutôt qu'un toast ; boîtes non sélectionnables
**grisées à ~55 %, raison en italique dessous, jamais masquées** ; actions de gestion **visibles
et désactivées** hors ligne avec leur explication ; identité du PS en **texte non éditable** dans
l'onboarding ; sélecteur en **bottom sheet** (rayon 12 px) depuis l'avatar de l'en-tête Messages.

## Develop log

| Repo | Mode | Build | Tests | Push |
|---|---|---|---|---|
| `dtos-mss` | pushable | — | — | **aucun commit** — les contrats de la vague 1 sont déjà publiés en **474.0.0** ; task-304 n'ajoute aucun DTO. Pas de PR. |
| `client-blazor` | pushable | ✅ 0 erreur | ✅ **228** (2 skipped pré-existants) | `ca767a2` |
| `client-angular` | **code-only** | ✅ `nx build weda2` | ✅ **2 572** (weda2+mss) + **343** (mss-lib) | **non commité** — l'humain gère git/TFS |
| `client-mobile` | pushable | ✅ 0 erreur | ✅ **819** | `1d886f3` |

**`client-blazor` bumpé** `454.0.0` → **`474.0.0`** (DOD transverse). Pas de `sdk` :
task-305 en a retiré la référence.

### Ce que la passe qualité `/simplify` a trouvé

- **`client-blazor`** — quatre composants répétaient le même trio « s'abonner à
  `OnChanged`, redessiner, se désabonner ». Quatre copies d'un abonnement ne
  dérivent pas bruyamment : c'est le **désabonnement** qu'on oublie, et la fuite
  ne se voit qu'en cumulant les navigations. Extrait en
  `MailboxAwareComponentBase` (`ca767a2`).
- **`client-mobile`** — `isAuthenticated` et `hasValidToken` sont devenus le même
  test une fois la claim retirée. Deux noms pour un prédicat finissent toujours
  par diverger ; un seul reste (`0a892f2`).
- **`client-angular`** — rien d'appliqué : le store, le service et la garde sont
  neufs et sans doublon, et `MailboxListItemComponent` était déjà partagé entre
  le sélecteur et l'écran de choix.

### Deux constats à porter au HAG

**1. Lacune du contrat task-303 — les deux 409 du rattachement n'ont pas de code.**
`AttachMailbox` rend `Problem(409, …)` pour « déjà rattachée » **et** pour
« identité non concordante », sans `instance` ni `code`. Les 403 d'appartenance,
eux, portent bien leur code dans `instance`. Les trois fronts ne peuvent donc pas
distinguer les deux conflits autrement qu'en lisant le message — ce que la règle 12
proscrit. Ils affichent le `detail` du serveur tel quel (spécifique et déjà rédigé
pour le praticien dans les deux cas) plutôt que de deviner. **Le correctif est
d'une ligne côté api-mail** (`instance: MailboxErrorCodes.PscIdentityConflict`),
mais `api-mail` n'est pas dans le `**Repos**:` de cette task — règle 6. La PR #236
de task-303 étant **encore ouverte**, c'est l'endroit naturel pour le poser.

**2. Outillage visuel absent du poste** — `Tools/visual-verify/` n'existe pas et
n'est pas versionné (`.gitignore` l'exclut délibérément, seul `Tools/timing/` est
réintroduit). Les quatre critères « Outillage visuel » de la DOD restent non
satisfaits, et les captures des écrans mobiles ne peuvent pas être produites.
Détail, cause et options : `questions/task-304.md`. La suite `/qa`, elle, est
traitée : `Client/Mobile/e2e/README.md` documente le ré-alignement (`1d886f3`).

## Lint log — `client-angular`

**Mode A** (chaîné), portée `weda2, mss, mss-lib` (`**LintProjects**:` du task
file, qui élargit le défaut `tag:scope:mss`). **2 itérations** sur les 5
autorisées.

> **Divergence assumée sur la portée** : `nx affected --base=origin/next
> --head=HEAD` compare des **commits**, or le travail Angular est en code-only,
> donc **non commité** — `affected` ne l'aurait pas vu et aurait linté un diff
> vide. Les trois projets nommés sont donc lintés par `run-many`. C'est plus
> large que le pipeline, jamais plus étroit.

| | Erreurs | Avertissements |
|---|---|---|
| Baseline | **57** | 38 |
| Après itération 1 (auto-fix) | 2 | 78 |
| **Final** | **0** | **55** |

- **Itération 1 — auto-fix.** 55 erreurs `prettier/prettier` corrigées
  gratuitement. L'auto-fixer a aussi inséré **23 squelettes JSDoc vides**, ce
  qui a fait *monter* le nombre d'avertissements : il satisfait
  `jsdoc/require-jsdoc` sans rien documenter.
- **Itération 2 — manuelle.** Les 23 squelettes remplis par le sens réel de
  chaque méthode, et les 2 erreurs `jsdoc/require-returns` résiduelles (que le
  squelette ne couvre pas) traitées. Un stub vide passe la règle sans rien
  dire : c'est pire qu'une absence, parce qu'il fait croire que la méthode est
  documentée.
- **Re-validation** : `nx build weda2` ✅, tests **2 572** (weda2+mss) + **343**
  (mss-lib) ✅.

**55 avertissements acceptés** (best-effort) : `complexity`, `max-lines` et
`jsdoc/require-example` sur du code **pré-existant** du module MSS, hors périmètre
de cette US.

**Convention apprise** → `conventions/angular.md`, entrée
`jsdoc/require-jsdoc` : écrire le JSDoc en même temps que la méthode, ne jamais
s'en remettre à `--fix` pour ça.

**Code-only** : aucune opération git sur `client-angular`. Les fixes de lint sont
dans le worktree avec le reste du travail Angular, en attente du commit humain.

## Lint mobile log

**Mode A** (chaîné), `Client/Mobile/` sur `feat/task-304-selection-et-bascule-de-boite`.
**0 itération consommée** sur les 5 autorisées : `npm run lint` rend
**« All files pass linting »** dès la baseline — 0 erreur, 0 avertissement.

Aucun commit, aucun push : il n'y avait rien à corriger.

> **Pourquoi le contraste avec `client-angular`** (57 erreurs à la baseline) : la
> config ESLint de `client-mobile` ne porte **ni `prettier/prettier` ni la famille
> `jsdoc/*`**, qui représentaient la totalité des erreurs Angular. Le code mobile
> de cette US a par ailleurs été écrit d'emblée avec le control flow natif
> (`@if`/`@for`), les sélecteurs préfixés `app-`, `ChangeDetectionStrategy.OnPush`
> et un `data-testid` par élément interactif — les quatre consignes de
> `conventions/angular.md` qui s'appliquent aux deux repos.

## Visual verify log

**SKIP — panne d'outillage, best-effort, non bloquant.**

`Tools/visual-verify/` **n'existe pas sur ce poste** et n'est pas versionné :
`.gitignore` exclut `Tools/` en bloc et ne réintroduit que `Tools/timing/`
(« only the timing harness is forge infrastructure and must survive a fresh
clone »). Le harnais de capture Playwright vit donc sur le poste qui l'a écrit.

```
$ ls Tools/visual-verify/
ls: cannot access 'Tools/visual-verify/': No such file or directory
$ git ls-files | grep visual-verify      # (rien)
```

C'est bien la sévérité **« panne outillage »** du playbook, pas la sévérité
bloquante : celle-ci est réservée à l'**écran blanc / crash de navigation**, une
régression runtime que seule une capture révèle. Ici aucune capture n'a pu être
tentée — il n'y a donc rien à conclure sur les écrans, ni en bien ni en mal.

| Écran | Référence Stitch | Capture | Verdict |
|---|---|---|---|
| `mailbox-onboarding` | timeout de génération, id à relever | — | non capturé |
| `mailbox-select` | `3f84e49c6242414880e6bffa7036127b` | — | non capturé |
| `mailbox-switcher` | `8da2543c595f494d990094223e74ed3e` | — | non capturé |
| `mailbox-management` | `d0d02a1abf344d589119bf5b34fdec2c` | — | non capturé |

**Conséquences à porter au HAG :**

1. **La galerie porte deux captures périmées** —
   `Docs/epics/img/screens/client-mobile/mss-setup.png` et `mss-unconfigured.png`
   documentent des écrans **supprimés par cette US**. Elles ne peuvent pas être
   remplacées sans le harnais.
2. **Le premier geste au retour du harnais est la fixture `mailboxes.json`**, pas
   une capture. Le mock `**/api/**` rend `[]` sur tout `GET` non mappé : sans
   elle, `GET /account/mailboxes` rendrait « zéro boîte » et **toute la galerie
   mobile deviendrait l'écran d'onboarding**.
3. La vérification visuelle des quatre écrans revient donc à l'humain, au HAG.

Détail, cause et options (dont : versionner `Tools/visual-verify/` au même titre
que `Tools/timing/`) → **`questions/task-304.md`**.

## PRs

- `client-blazor` : https://github.com/codengine-technologies/HealthPlatform.Client/pull/74 — label **`awaiting-human-merge`**
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/70 — label **`awaiting-human-merge`**
- `dtos-mss` : **aucune PR** — branche créée par `/start` (auto-inclusion), **zéro commit**. Les contrats de la vague 1 sont déjà publiés en `474.0.0` ; task-304 n'ajoute aucun DTO.
- `client-angular` : **code-only** — l'humain gère commit/push TFS et l'ouverture de la PR. Fichiers modifiés (worktree, branche `feature/nova-rewriting-mss`) listés ci-dessous.

> **Règle 11 — la US est désormais COMPLÈTE.** Les PRs de **task-303** ont été
> rebasculées de `awaiting-us-completion` vers `awaiting-human-merge` : les deux
> vagues sont en PR prête, et laisser l'ancien label aurait laissé croire que la
> US attend encore quelque chose. Le test humain porte sur la **US assemblée**.
>
> **Ordre de merge** : `dtos-mss` #32 → `api-mail` #236 → `client-blazor` #74 et
> `client-mobile` #70.
>
> ⚠️ **`api-mail` #236 est en conflit avec `develop`** (`mergeable: CONFLICTING`,
> constaté le 2026-09-13). À résoudre par `git merge origin/develop` sur
> `feat/task-303-*` (règle 4 — jamais de rebase) avant le merge.

### `client-angular` — fichiers modifiés, non commités
- `front/apps/mss/src/environments/environment.ts` (M)
- `front/apps/weda2/src/app/app.config.ts` (M)
- `front/apps/weda2/src/app/core/interceptors/mss-headers.interceptor.ts` (M)
- `front/apps/weda2/src/app/features/booking/daily/mappers/patient-alert.mapper.ts` (M)
- `front/apps/weda2/src/app/features/booking/daily/mappers/preparation-summary.mapper.ts` (M)
- `front/apps/weda2/src/app/features/booking/daily/services/daily-agenda.service.ts` (M)
- `front/apps/weda2/src/app/features/booking/daily/store/daily-agenda.store.ts` (M)
- `front/apps/weda2/src/app/features/booking/daily/store/helpers/daily-agenda-resource-sync.helper.ts` (M)
- `front/apps/weda2/src/environments/environment.ts` (M)
- `front/apps/weda2/src/lib/auth/interceptors/utils/auth-interceptor.utils.ts` (M)
- `front/apps/weda2/src/lib/auth/models/jwt-payload.model.ts` (M)
- `front/apps/weda2/src/lib/auth/store/utils/store-helpers.utils.ts` (M)
- `front/libs/mss/src/core/guards/mss-onboarding.guard.spec.ts` (D)
- `front/libs/mss/src/core/guards/mss-onboarding.guard.ts` (D)
- `front/libs/mss/src/core/index.ts` (M)
- `front/libs/mss/src/core/models/audit.model.spec.ts` (M)
- `front/libs/mss/src/core/models/audit.model.ts` (M)
- `front/libs/mss/src/core/models/mss-onboarding.model.ts` (D)
- `front/libs/mss/src/core/services/mail-events-stream.service.ts` (M)
- `front/libs/mss/src/core/services/mss-onboarding.service.spec.ts` (D)
- `front/libs/mss/src/core/services/mss-onboarding.service.ts` (D)
- `front/libs/mss/src/core/services/notification-stream.service.ts` (M)
- `front/libs/mss/src/features/index.ts` (M)
- `front/libs/mss/src/features/setup/mss-setup.component.html` (D)
- `front/libs/mss/src/features/setup/mss-setup.component.scss` (D)
- `front/libs/mss/src/features/setup/mss-setup.component.spec.ts` (D)
- `front/libs/mss/src/features/setup/mss-setup.component.ts` (D)
- `front/libs/mss/src/features/unconfigured/mss-unconfigured.component.html` (D)
- `front/libs/mss/src/features/unconfigured/mss-unconfigured.component.scss` (D)
- `front/libs/mss/src/features/unconfigured/mss-unconfigured.component.spec.ts` (D)
- `front/libs/mss/src/features/unconfigured/mss-unconfigured.component.ts` (D)
- `front/libs/mss/src/index.ts` (M)
- `front/libs/mss/src/ui/index.ts` (M)
- `front/libs/mss/src/core/guards/mailbox.guard.ts` (??)
- `front/libs/mss/src/core/models/mailbox.model.ts` (??)
- `front/libs/mss/src/core/models/mss-probe.model.ts` (??)
- `front/libs/mss/src/core/services/mailbox-accounts.service.spec.ts` (??)
- `front/libs/mss/src/core/services/mailbox-accounts.service.ts` (??)
- `front/libs/mss/src/core/stores/` (??)
- `front/libs/mss/src/core/tokens/mss-practitioner-identity.token.ts` (??)
- `front/libs/mss/src/core/tokens/mss-psc-sign-in.token.ts` (??)
- `front/libs/mss/src/features/mailbox-management/` (??)
- `front/libs/mss/src/features/mailbox-onboarding/` (??)
- `front/libs/mss/src/features/mailbox-psc-required/` (??)
- `front/libs/mss/src/features/mailbox-select/` (??)
- `front/libs/mss/src/ui/attach-mailbox-form/` (??)
- `front/libs/mss/src/ui/mailbox-list-item/` (??)
- `front/libs/mss/src/ui/mailbox-switcher/` (??)

## Code Review Summary

**Verdict : APPROVED.** Revue du diff complet des trois fronts (42 fichiers Blazor,
55 mobile, 48 entrées Angular).

### Ce qui a été corrigé pendant la revue

| Fichier | Constat | Correctif |
|---|---|---|
| `Mail.razor` (Blazor) | `First()` sur le défaut ouvrable **levait** si l'invariant calculé par `Decide()` évoluait — un crash du module comme mode d'expression d'une évolution de la table de décision | `FirstOrDefault` + repli sur l'écran de choix |
| `MailboxSelect.razor` (Blazor) | le verrou `_opening` n'était **jamais relâché** : un échec de pose du défaut laissait « Ouvrir » grisé définitivement, sans message | `try/finally` |
| `jwt-payload.model.ts` (Angular) | `mssEmail` encore **déclaré** dans le type de payload — plus rien ne le lisait, mais un type qui annonce la claim invite à la relire | champ et doc retirés |

### Ce qui a été jugé sain

- **Sécurité / données de santé** — aucun jeton journalisé ; la purge à la bascule
  est énumérée depuis le conteneur (`IMailboxScopedState` / `MSS_RESETTABLE_STORES`
  / `MAILBOX_SCOPED_STATES`) plutôt qu'écrite en dur, donc un porteur d'état ajouté
  plus tard s'y inscrit explicitement ; aucune persistance de boîte sur l'appareil.
- **Architecture** — la compatibilité PSC n'est **jamais** évaluée côté front
  (aucune comparaison de `sub` : vérifié par grep). Les fronts affichent
  `selectable` / `capabilities` tels que le backend les rend.
- **Couverture** — la table de décision à sept états est couverte **par un test
  par cas et par front** ; la séquence de bascule par un test d'**ordre** qui
  échoue si une étape bouge.
- **Cycles de dépendances** — `MailboxAccountsService` utilise `HttpClient`
  directement et non `HttpRequestService` : ce dernier pose `Client-Email` en
  lisant la session de boîte, qui a besoin du registre. Passer par lui fermerait
  un cycle de construction. Les routes du registre sont d'ailleurs
  `[MailboxNotRequired]` côté backend.

### Suggestion non bloquante

Le mobile n'enregistre **aucun** porteur d'état dans `MAILBOX_SCOPED_STATES` (tableau
vide, documenté) : son état de boîte vit dans les pages, détruites par la navigation
vers l'onglet Messages qui suit chaque bascule. C'est correct aujourd'hui ; ça cesse
de l'être le jour où un service racine cachera des données de boîte.

## Merged

Mergée le **2026-09-14** par `/merge 304 --i-tested` (HAG, règle 10 — attestation humaine
du test de la US assemblée 303 + 304).

| Repo | PR | Commit de squash sur `develop` | CI `develop` |
|---|---|---|---|
| `client-blazor` | #74 | `fe2ab36` | ✅ [run 34874362502](https://github.com/codengine-technologies/HealthPlatform.Client/actions/runs/34874362502) |
| `client-mobile` | #70 | `158d3a4` | ✅ [run 34874388058](https://github.com/codengine-technologies/HealthPlatform.Mobile/actions/runs/34874388058) |
| `dtos-mss` | aucune PR | — | branche vide (0 commit), supprimée localement |
| `client-angular` | code-only | — | géré manuellement par l'humain |

Branches distantes `feat/task-304-selection-et-bascule-de-boite` supprimées sur `client-blazor`
et `client-mobile` ; branches **locales conservées** pour inspection rétroactive.

> **Staging** : aucune branche `forge/staging-task-*` — task-304 n'a pas été produite par un
> run `/forge` multi-tasks. Rien à nettoyer.
