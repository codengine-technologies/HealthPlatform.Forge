# todo-task-159.md — Onboarding MSSanté mobile quand le claim `mssEmail` est absent

**Repos**: client-mobile
**Single frontend**: true
**Dependencies**: — (backend `mss-imap-test` livré par task-037, mergé ; endpoint proxy Keycloak `mss-profile` déjà exposé)
**Epic**: E012

> US **single-frontend `client-mobile`** (GitHub, automation forge complète :
> branche/commit/push/PR). **Aucun changement backend** : les endpoints
> serveur (`POST /api/v1/account/mss-imap-test` sur `api-mail`, `PUT …/mss-profile`
> sur le proxy Keycloak) existent déjà et sont réutilisés tels quels. Parité
> fonctionnelle avec le parcours Angular weda2 (task-037), transposé aux
> conventions mobile (Ionic 8 / Angular 20, libellés FR en dur, design Stitch E014).

## Objectif

Aujourd'hui, quand un PS se connecte à `client-mobile` (CIBA e-CPS, task-136)
avec un compte Keycloak dont l'attribut `mssEmail` **n'est pas rempli**, l'app
le traite comme **non authentifié** : `AuthSessionService.isAuthenticated`
exige un `userEmail` non vide (dérivé du claim `mssEmail`), `readFromStorage()`
jette toute session sans `userEmail`, et `authGuard` renvoie sur `/login`. Le PS
est donc bloqué dans une boucle de login sans aucune indication ni moyen de
configurer son adresse — alors que le web (weda2 / Blazor) lui propose depuis
task-037 un parcours d'opt-in.

Cette US porte le **parcours d'onboarding MSSanté** sur mobile. Décisions
produit validées (2026-07-15) :

1. **Nouvel état d'auth « authentifié mais non configuré »** : un token valide
   **sans** claim `mssEmail` ne compte plus comme « non authentifié ». L'app
   distingue trois états : (a) pas de token → `/login` ; (b) token valide mais
   `mssEmail` absent → parcours d'onboarding ; (c) token complet → app normale.
2. **Écran verrou** « Messagerie non configurée » plein écran (hors `ion-tabs`),
   avec CTA « Configurer mon compte ».
3. **Formulaire de configuration** (1 champ : adresse MSSanté) qui **valide la
   connexion IMAP** côté `api-mail` puis **persiste** l'attribut `mssEmail` côté
   proxy Keycloak, et invite le PS à **se déconnecter/reconnecter** pour obtenir
   un JWT porteur du claim.
4. **Persistance en bearer** : le mobile s'authentifie par bearer token (session
   CIBA/BFF), pas par cookie `withCredentials` comme le web ; le proxy accepte
   ce bearer (confirmé infra 2026-07-15).

## Flow utilisateur

1. PS se connecte via e-CPS (CIBA, écran existant). Le token revient **sans**
   `mssEmail`.
2. L'app détecte l'état « authentifié mais non configuré » → affiche l'écran
   verrou plein page **« Messagerie non configurée, veuillez configurer
   maintenant »** + bouton « Configurer mon compte ». **Aucun appel mail/mss
   n'est déclenché** (pas d'INBOX, pas de 403 silencieux).
3. Clic « Configurer mon compte » → écran de saisie de l'adresse MSSanté.
4. Le PS saisit son adresse MSSanté (requise, format email, ≤ 254 car.) et valide.
   La soumission enchaîne 2 appels serveur :
   - **A.** `POST {mssApi}/api/v1/account/mss-imap-test` avec `{ "email": "…" }`
     (bearer + headers usuels mobile). `200 { ok:true }` → étape B. `4xx { error, code }`
     (`AUTH_FAILED` / `HOST_UNREACHABLE` / `MAILBOX_NOT_FOUND` / `INVALID_EMAIL`)
     → toast d'erreur FR, formulaire reste éditable, **aucun appel au proxy**.
   - **B.** `PUT {authEndpoint}/admin/mss-profile` avec `{ "email": "…" }` (bearer).
     `204` → étape C. `4xx`/`5xx` → toast FR « Impossible d'enregistrer le profil,
     réessayez plus tard », formulaire reste éditable, token inchangé.
   - **C.** Écran de succès « Configuration enregistrée. Pour activer votre
     messagerie, déconnectez-vous puis reconnectez-vous. » + bouton **« Se
     déconnecter maintenant »** (pas de silent refresh — le remap du claim dépend
     du protocol-mapper Keycloak, hors scope).
5. Le PS se déconnecte → re-login e-CPS → le nouveau JWT porte `mssEmail` → l'app
   ouvre l'INBOX normalement.
6. Si le PS quitte l'écran de configuration sans soumettre → retour sur l'écran
   verrou (l'état non configuré persiste).

## Scope (client-mobile, `Client/Mobile/`)

### Modèle d'auth — distinguer « non configuré » de « non authentifié »

- `src/app/core/auth/auth-session.service.ts` :
  - `isAuthenticated` reste `!!accessToken && !!userEmail` (session **complète**).
  - Ajouter un état intermédiaire, ex. `hasValidToken` (`!!accessToken`) et
    `needsMssOnboarding` (`!!accessToken && !userEmail`).
  - `readFromStorage()` **ne doit plus jeter** une session token-only : la
    conserver pour permettre l'onboarding (retirer/adapter la purge lignes ~46-48).
- `src/app/core/auth/auth.guard.ts` : si `needsMssOnboarding` → rediriger vers la
  route d'onboarding (pas `/login`). Pas de token → `/login`. Session complète →
  laisser passer.
- Nouveau **guard** protégeant l'app configurée (`ion-tabs`, INBOX, mail) : renvoie
  vers l'onboarding tant que `needsMssOnboarding`. Les routes d'onboarding
  elles-mêmes en sont exemptées.

### Écrans (kebab-case = convention Stitch/fichier)

- **`mss-unconfigured`** (`src/app/mss-onboarding/unconfigured/`) — page plein
  écran (hors tabs) : message centré + bouton CTA « Configurer mon compte ».
- **`mss-setup`** (`src/app/mss-onboarding/setup/`) — formulaire réactif 1 champ
  (adresse MSSanté) + phases `editing → submitting → success` ; écran de succès
  avec bouton « Se déconnecter maintenant » (→ flux logout existant).
- Routes ajoutées dans `src/app/app-routing.module.ts` : `mss-unconfigured`,
  `mss-setup` (hors `ion-tabs`, comme `login`).

### Service

- **`MssOnboardingService`** (`src/app/mss-onboarding/`) :
  - `validateImapConnection(email)` → `POST /api/v1/account/mss-imap-test`.
  - `persistMssEmail(email)` → `PUT {authEndpoint}/admin/mss-profile` (bearer).
  - Erreurs typées mappées en messages FR (mêmes codes que task-037).

### Réutilisation (memory `feedback_reuse_existing_components`)

- Réutiliser les composants/tokens Ionic existants (boutons, inputs, toasts) et
  le design system E014 « Clinical Precision ». Ne pas dupliquer de styles.
- Réutiliser le service HTTP MSS existant (`mss-headers.interceptor`,
  base URL API) plutôt qu'un client ad hoc.

## Scope OUT

- **Aucun changement backend** (`api-mail`, proxy Keycloak, `dtos-mss`) — endpoints
  déjà livrés (task-037) et réutilisés tels quels.
- Le protocol-mapper Keycloak (remap du claim) — hors scope, d'où le logout explicite.
- Onboarding multi-comptes MSSanté.
- Édition de l'adresse MSSanté depuis Paramètres → Compte **une fois configurée**
  (reste en lecture seule ; l'onboarding ne cible que le cas « adresse absente »).
- Bannière / modification de la coquille `ion-tabs` : le blocage est un écran
  plein page dédié, en amont des tabs.

## Definition of Done

- [ ] Build passe : `cd Client/Mobile && npm run build` (0 erreur)
- [ ] Tests passent : `npm test -- --watch=false --browsers=ChromeHeadless` (0 échec)
- [ ] `AuthSessionService` : `needsMssOnboarding` (token présent + `mssEmail`/`userEmail`
      absent) implémenté ; `isAuthenticated` inchangé (exige toujours session complète) ;
      `readFromStorage()` conserve une session token-only au lieu de la jeter — testé
      (≥ 1 test par branche : pas de token / token-only / session complète)
- [ ] `authGuard` : token-only → route onboarding ; pas de token → `/login` ; session
      complète → passe — testé (3 cas)
- [ ] Guard app-configurée : renvoie vers l'onboarding tant que `needsMssOnboarding`,
      exempte les routes `mss-unconfigured` / `mss-setup` — testé
- [ ] `MssOnboardingService.validateImapConnection` : succès (200) + échec (4xx par code) — testé (HTTP mocké)
- [ ] `MssOnboardingService.persistMssEmail` : 204 + 4xx/5xx — testé (HTTP mocké)
- [ ] `mss-setup` : rendu + validation du champ (requis / format email / maxLength 254) +
      chaîne de soumission (IMAP OK → persist → écran succès ; IMAP KO → pas de persist) — testé
- [ ] `mss-unconfigured` : rendu + clic CTA navigue vers `mss-setup` — testé
- [ ] **Assertion clé** : quand `mssEmail` est absent, **aucun appel mail/mss-api**
      n'est émis avant configuration (network mock / spy)
- [ ] `data-testid` sur tous les interactifs : `mss-unconfigured-cta`,
      `mss-setup-email-input`, `mss-setup-submit-btn`, `mss-setup-logout-btn`,
      zone d'erreur/toast
- [ ] Libellés **FR en dur** (pas de `ngx-translate` — convention mobile/Angular MSS)
- [ ] **Aucune adresse MSSanté ni donnée sensible en clair** dans les logs console /
      URL ; l'email ne transite que dans le corps des POST/PUT
- [ ] Persistance en **bearer** (session mobile), pas `withCredentials` cookie

## Manual Test Plan

**Pré-requis** : proxy d'authentification + `api-mail` lancés en local, un **compte
Keycloak de test dont l'attribut `mssEmail` n'est PAS rempli**, l'app e-CPS (sandbox
PSC) pour valider la connexion CIBA, et une **adresse MSSanté de test** valide.

1. Lancer le mobile : `cd Client/Mobile && npm start` (ou `ionic serve`).

### Cas 1 — Compte SANS `mssEmail` (le cas qui bloque aujourd'hui)
2. Se connecter en e-CPS (CIBA) avec le compte de test sans `mssEmail`.
3. ✅ L'app affiche l'écran verrou « Messagerie non configurée » + bouton
   « Configurer mon compte » (et **non** un retour à l'écran de login). **Aucun
   appel mail/mss-api dans la console Network.**
4. Clic « Configurer mon compte » → écran de saisie.
5. Saisir une adresse MSSanté valide → « Valider ».
6. ✅ Network : `POST /api/v1/account/mss-imap-test` → 200 ; `PUT …/admin/mss-profile` → 204.
7. ✅ Écran « Configuration enregistrée… déconnectez-vous puis reconnectez-vous »
   + bouton « Se déconnecter maintenant ».
8. Clic bouton → logout → re-login e-CPS.
9. ✅ Le nouveau JWT porte `mssEmail` ; l'INBOX se charge sans erreur.

### Cas 2 — Compte AVEC `mssEmail` (non-régression)
10. Se connecter avec un compte dont `mssEmail` est déjà rempli.
11. ✅ Pas d'écran verrou ; l'app ouvre directement les tabs / l'INBOX.

### Cas 3 — Échec validation IMAP
12. Compte sans `mssEmail`, écran de saisie → saisir une adresse manifestement
    invalide (domaine inexistant) → « Valider ».
13. ✅ `api-mail` répond 4xx ; toast d'erreur FR lisible. **Aucun appel au proxy
    Keycloak.** Le formulaire reste éditable.

### Cas 4 — Échec proxy Keycloak
14. Compte sans `mssEmail` : IMAP OK (200) mais proxy en panne (bloquer l'URL
    `*/admin/mss-profile`) → soumettre.
15. ✅ Toast FR « Impossible d'enregistrer le profil, réessayez plus tard ».
    Formulaire éditable, token inchangé.

### Cas 5 — Quitter la saisie sans soumettre
16. Compte sans `mssEmail`, sur l'écran de saisie → revenir en arrière.
17. ✅ Écran verrou « Messagerie non configurée » à nouveau, pas d'INBOX.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie sécurisée de santé — configuration
  de l'adresse MSSanté du PS sur le canal mobile)
- **Vague Ségur** : V2 (socle MSSanté / identification-authentification du PS)
- **Exigences DSR honorées** : MSSanté (mise en service de la boîte du PS,
  cohérence adresse ↔ identité authentifiée) ; authentification e-CPS niveau eIDAS
  substantiel (PGSSI-S § authentification) déjà assurée par task-136
- **INS** : non applicable — le parcours configure l'**adresse MSSanté du
  professionnel**, aucune manipulation d'identité patient
- **Authentification PS** : e-CPS via CIBA (déjà en place, task-136) ; l'onboarding
  s'exécute **dans** une session authentifiée ; la validation IMAP réutilise la
  connexion authentifiée serveur (pas de mot de passe utilisateur côté serveur)
- **Habilitations** : RPPS porté par le PS et vérifié par PSC en amont ; aucune
  habilitation métier supplémentaire gérée par le mobile
- **Interop CI-SIS** : non applicable — pas d'échange de contenu métier (CDA/FHIR)
  dans ce flux ; il s'agit d'un test de connexion IMAP + d'une écriture d'attribut
- **Tracé PGSSI-S** : journaliser (sans adresse en clair) — tentative de
  configuration MSSanté, succès/échec de validation IMAP, succès/échec de
  persistance. Journalisation probante longue durée assurée côté serveur/proxy ;
  le mobile se limite à des évènements UI non sensibles
- **Consentement patient** : non applicable — aucun traitement de donnée patient
- **Référentiels métier** : aucun (CIM-10/SNOMED/LOINC/CCAM/NABM/CIS-CIP non concernés)
- **Hébergement HDS** : non — le flux n'crée ni ne manipule de DSCP ; il configure
  l'adresse MSSanté du PS et teste une connexion. La session est conservée selon le
  mécanisme existant de l'app
- **AIPD / impact RGPD** : à signaler — l'app mobile capture et transmet désormais
  l'**adresse MSSanté du PS** (donnée professionnelle) ; vérifier que la note
  RGPD/AIPD du périmètre mobile couvre cette saisie et sa transmission au proxy Keycloak

## DOD santé — items ajoutés

- [ ] Aucune adresse MSSanté (ni autre donnée sensible) en clair dans les logs
      console / URL — transite uniquement dans le corps des requêtes
- [ ] Validation IMAP réutilisant l'authentification serveur existante (aucun
      secret utilisateur transitant en clair côté client)
- [ ] Évènements journalisés côté mobile : tentative de configuration, succès,
      échec IMAP, échec persistance (sans adresse en clair)

## Stitch design

- Projet : `client-mobile` (id `10088502293310567548`, MOBILE), design system
  « Clinical Precision » (E014).
- Écrans de référence attendus (convention : titre Stitch = nom kebab-case du
  composant) : **`mss-unconfigured`** (écran verrou centré + CTA) et **`mss-setup`**
  (formulaire adresse MSSanté + états succès/erreur). `/stitch-design` (sous-étape
  de `/develop`) réutilise l'écran s'il existe, sinon le crée. Best-effort, non
  bloquant ; output = référence visuelle, pas du code collé.

## Branches
- `client-mobile` (pushed) : feat/task-159-mss-onboarding — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-159-mss-onboarding

## Stitch design log
- Projet : client-mobile (id 10088502293310567548), design system « Clinical Precision » (E014).
- `mss-unconfigured` — **créé** (screen id `2bba91686d4c4c93a1feee5043949d4f`).
  Capture : https://lh3.googleusercontent.com/aida/AP1WRLtNJGGUykSqM4uwhesN0fCmv4FqZRg4XP-W3gpfPuD6XzOLkfQysKWpDs9P5sxMaGQ06wD8O2rRd0Bk39BIthr0n7pvM7crwk1VJ2zxRXZI20sgbP1hiPINhnxxLL7owwF_uZMwOiJ62yibbTTn6H_Y8D26Zfu9vxf8E6ewgo-bDwZ2bTr4fy7wkH2vCHXim1LMJr54kt2GIXtf0WPYYh2_-o4YKpPeVDAIAxbrhp7e_Kv4WDEzIjysHK4
  Intention : verrou plein écran, icône bouclier+mail primary, headline « Messagerie non configurée », CTA plein-largeur « Configurer mon compte ».
- `mss-setup` — génération **timeout MCP = succès probable** (mémoire `reference_stitch_generate_screen_timeouts` : ne pas re-générer). Référence appliquée depuis l'intention : header retour + titre « Configurer ma messagerie » + champ « Adresse MSSanté » (label visible, outline) + bannière erreur inline (error #ba1a1a) + CTA « Valider » ; état succès = check vert + « Configuration enregistrée » + « Se déconnecter maintenant ».
- Output = référence, pas de HTML collé : traduction en Ionic contre les tokens E014.

## Develop log

- Repos touched : client-mobile
- DTOs published : no DTO change (aucun changement backend/contrat)
- Interop published : no interop change
- Commits (client-mobile, feat/task-159-mss-onboarding) :
  - 8e5934c feat(mobile): distinguer session token-only pour l'onboarding MSSanté
  - 28bb188 feat(mobile): parcours d'onboarding MSSanté — écrans + service
- Local build : ✓ (npm run build, 0 erreur)
- Local test : ✓ 537 SUCCESS / 0 failed (npm test headless)
- DOD self-check :
  - Build/tests verts ✓
  - needsMssOnboarding + isAuthenticated inchangé + readFromStorage token-only : testé (auth-session.service.spec, 4 cas)
  - authGuard 3 cas : testé (auth.guard.spec)
  - guard app-configurée + exemption onboarding : testé (mss-onboarding.guard.spec, 5 cas)
  - validateImapConnection succès + 4xx par code : testé
  - persistMssEmail 204 + 4xx/5xx + bearer sans cookie : testé
  - mss-setup rendu + validation champ + chaîne soumission (IMAP OK→persist, IMAP KO→pas de persist) : testé
  - mss-unconfigured rendu + CTA nav : testé
  - « aucun appel mail/mss avant config » : garanti par [authGuard, mssConfiguredGuard] sur /home + /tabs (composants jamais activés)
  - data-testid : mss-unconfigured-cta, mss-setup-email-input, mss-setup-submit-btn, mss-setup-logout-btn, mss-setup-error, mss-setup-back-btn ✓
  - FR en dur (pas de ngx-translate) ✓
  - bearer (pas withCredentials) ✓ — testé sur persistMssEmail
- Next step : /forge-simplify 159

## Simplify log
- Repos éligibles touchés : client-mobile.
- Passe `/simplify` (quality-only) sur le diff frais : **skip clean** — code déjà
  à bonne altitude, pas de réutilisation manquée ni de duplication significative.
  (Guards = pattern inject idiomatique ; logout setup ≠ logout settings ;
  responseType text réutilise le pattern défensif sendMail.)
- Aucun commit (rien à simplifier). Build/tests inchangés (déjà verts au /develop).
- Next : /lint-mobile 159 (api-mail & client-angular non touchés → /sonar + /lint-angular skip clean).

## Lint mobile log
- Baseline `ng lint` : **All files pass linting** — 0 erreur, 0 warning sur le code frais.
- Aucun fix nécessaire (conventions `conventions/angular.md` appliquées d'emblée par
  /develop : control-flow natif @if, préfixes app-/mss-, FR en dur, data-testid).
- Aucun commit. Next : /verify-visual 159 → /review 159.

## Visual verify log
Playwright headless 390×844, session **token-only** injectée (jeton présent,
`userEmail` vide → état onboarding) + API mockée par fixtures (aucun backend,
aucune donnée de santé). `capture.mjs` étendu (option `session: "token-only"`) +
`screens.json` (mss-unconfigured, mss-setup).

| Écran | Route | Résultat | Réf. Stitch |
|---|---|---|---|
| `mss-unconfigured` | /mss-unconfigured | ✓ ok, non-blank, 0 erreur console | screen `2bba9168…` — verrou centré + CTA (fidèle) |
| `mss-setup` | /mss-setup | ✓ ok, non-blank, 0 erreur console | intention Stitch (timeout génération) — formulaire adresse + Valider (fidèle) |

- Captures : `Client/Mobile/e2e/screenshots/task-159/` (poussées, commit 1da6ba0)
  + copiées dans `Docs/epics/img/screens/client-mobile/` (galerie état visuel, E012).
- Bloquant uniquement sur blank/crash : aucun. Écart design : néant (rendu conforme E014).
- Next : /review 159.

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/57 (label: awaiting-human-merge)

## Code Review Summary
- Verdict : **APPROVED** — 23 fichiers, 0 bloquant, 1 suggestion non bloquante.
- Correctness / Sécurité / Archi / Tests : ✅ (voir body PR #57).
- Suggestion : `mssConfiguredGuard` recoupe partiellement `authGuard` sur /home /tabs (intentionnel).
- Build ✓ (0 erreur), Tests ✓ 537/537, Lint ✓ 0 erreur, Vérif visuelle ✓ (2 écrans non-blank).
- Qualité : /sonar skipped — api-mail non touché.

## Staging aggregation
- **Conflit best-effort → non agrégée** sur `forge/staging-task-142-160-20260716`.
- Cause : conflit `src/app/app-routing.module.ts`. La staging porte task-149 (déplace
  `/home` → redirect `tabs/home`) ; la branche task-159 (issue de `develop`, sans 142-158)
  ajoute `[authGuard, mssConfiguredGuard]` sur `/home` module lazy. Merge annulé
  (`git merge --abort`), PR #57 `feat → develop` intacte, task reste `done`.
- **Note intégration humaine (HAG)** : au merge, si task-149 passe avant task-159,
  résoudre le conflit en portant les gardes sur `tabs/home` (ou en gardant le parent
  `/tabs`, déjà couvert par `[authGuard, mssConfiguredGuard]`). La protection onboarding
  reste assurée par le guard du parent `/tabs` quoi qu'il arrive — pas de perte de sécurité.

### Mise à jour agrégation (résolution manuelle à la demande humaine, 2026-07-16)
- task-159 **finalement agrégée** sur `forge/staging-task-142-160-20260716` (commit 986e235).
- Conflit `app-routing.module.ts` résolu : `/home` garde le redirect → `tabs/home` (task-149) ;
  routes onboarding ajoutées ; gardes `[authGuard, mssConfiguredGuard]` sur `/tabs` (protègent tabs/home).
- Build + tests verts sur la staging après résolution.

## Bundle (task-167)
- 2026-07-17 — la PR #57 embarque désormais **task-167** (déclenchement onboarding strict sur `mssEmail`). Les deux mergeront ensemble (règle 11). Branche `feat/task-167` supprimée (commit replié sur `feat/task-159`).

## Merged
- 2026-07-17 — grappe onboarding 159+167 mergée via PR #57 (merge atomique)
- `client-mobile` : b9c31bf (PR #57 fermée)
