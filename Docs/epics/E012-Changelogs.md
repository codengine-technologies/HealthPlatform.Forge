# E012 — Changelogs (vue ingénierie)

> **Audience** : équipes techniques, backlog, dette.
> **Vue produit** : [E012-client-mobile-mssante.md](E012-client-mobile-mssante.md)
> **Dernière mise à jour** : 2026-08-30

---

## Historique détaillé des changelogs

> ⚠️ **Entrées manquantes (retard de documentation, constaté le 2026-08-30).**
> Sept tasks E012 ont atteint `done-*`/`archived-*` sans entrée ici :
> **task-147** (tags depuis le détail d'un mail, [Mobile#51](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/51)),
> **task-148** (carnet de contacts + annuaire, [Mobile#52](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/52)),
> **task-152** (chat IA contextuel multi-emails, [Mobile#54](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/54)),
> **task-154** (opposition patient : garde-fou serveur à l'envoi),
> **task-161** (dashboard : robustesse au chargement),
> **task-162** (dashboard : casser la boucle de rétroaction),
> **task-167** (onboarding MSSanté : déclenchement de l'opt-in).
> Elles sont **antérieures** à `v1.28` : les insérer imposerait de renuméroter
> des entrées existantes, ce que le writer s'interdit (append-only). À combler
> par un `/tech-writer E012 --refresh` délibéré, qui reconstruit l'historique
> complet dans le bon ordre.

### v1.29 — task-275 — Compatibilité verrouillée au modèle « token Keycloak jetable » (2026-08-30)

- **PR** : [HealthPlatform.Mobile#64](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/64) — label `awaiting-human-merge`. Branche `feat/task-275-mobile-psc-horizon`, commit `4c9c663`. Repo `client-mobile` uniquement (pas d'auto-inclusion `dtos-mss` : ni `api-mail` ni `client-blazor` listés). **Dépendance** : `psc-auth-proxy/task-015` (autre forge, PR `!9039`, état `done-*`).
- **Contexte** : `psc-auth-proxy/task-015` bascule le refresh mobile — le seul refresh token consommé est celui de **PSC**, et le jeton Keycloak n'est plus rafraîchi mais **re-frappé** à chaque `/auth/refresh` (JWT Authorization Grant RFC 7523, `KeycloakTokenExchangeService`). Plus de session ni de refresh token Keycloak : l'agrégat rendu au mobile a un `refreshToken` **vide** et un `refreshTokenExpirationDateUtc` qui porte l'horizon du refresh token PSC.
- **Nature** : **aucun code de production modifié.** Diff 100 % test — 3 fichiers de specs, +204 lignes, 6 tests. L'analyse préalable (`psc-auth-proxy/questions/task-014-session-persistante.md` §7.6) concluait que `client-mobile` était déjà compatible ; cette US **verrouille** la conclusion au lieu de la supposer.
- **Invariants épinglés** : (1) `refreshToken` vide → session pleinement valide (`accessToken`, `mssEmail`, `accessTokenExpiresAt`) ; (2) l'échéance provient de la claim `exp` du JWT et **non** des champs de date de l'agrégat — verrouillé par un agrégat aux dates volontairement incohérentes ; (3) absence d'`exp` → préventif désactivé, le réactif reste le filet ; (4) `refreshSession()` re-dérive `accessTokenExpiresAt` **et** `mssEmail` du jeton re-frappé et les **persiste** ; (5) le tour suivant est piloté par l'`exp` du jeton re-frappé, sans dépendance à `refreshTokenExpirationDateUtc` ; (6) un échec `/auth/refresh` en `ProblemDetails` porteur du code de re-échange suit le chemin existant purge + `/login?expired=1`, sans traitement particulier.
- **Fichiers** : `src/app/core/auth/session.model.spec.ts` (+56), `src/app/core/auth/auth.service.spec.ts` (+30), `src/app/core/http/mss-headers.interceptor.spec.ts` (+119).
- **Point technique** : l'invariant (5) exige un **stub de session mutable**. Les `describe` voisins utilisent `jasmine.createSpyObj<AuthSessionService>` dont la propriété `session` est **figée** — elle masquerait précisément ce qu'on vérifie (l'intercepteur doit *relire* une session différente après re-frappe). D'où un `describe` autonome avec un getter sur une variable réassignée par le `callFake` du refresh.
- **Simplify (`/forge-simplify`)** : skip clean, aucun commit. Deux factorisations examinées puis écartées, motifs consignés : mutualiser la configuration `TestBed` (le fichier porte **déjà 5 blocs** indépendants, un par `describe` — factoriser le seul nouveau serait incohérent, factoriser les cinq est un refactor hors périmètre d'une US « aucun changement de comportement ») ; réutiliser `validSession()`/`expiredSession()` (valeurs figées + spy immuable, incompatibles avec l'invariant 5). Réutilisation effective là où elle valait : `session.model.spec.ts` s'appuie sur le helper `tokens()` déjà présent.
- **Sonar** : skippé — `api-mail` non touché.
- **Lint (`/lint-mobile`)** : baseline `ng lint` **All files pass linting** — 0 erreur, 0 warning, 0 itération, aucun fix.
- **Verify-visual (`/verify-visual`)** : skip clean — 0 fichier d'écran modifié (`*.html`, `*.scss`, `*.component.ts`, `*.page.ts`), aucun `## Stitch design log`. État visuel global inchangé.
- **Code review** : verdict **APPROVED** — 3 fichiers, 0 bloquant, 1 suggestion non bloquante (le stub de session est un littéral non typé là où les `describe` voisins passent par `jasmine.createSpyObj<AuthSessionService>` ; `useValue` étant `any`, sans effet fonctionnel). Aucun secret, aucune donnée de santé : adresses et jetons entièrement fictifs. Échéances figées en constantes plutôt que dérivées de `Date.now()` → tests déterministes, pas de flaky temporel.
- **Tests** : **780 / 780** verts (774 → 780, +6). Build vert. Merge `origin/develop` : already up to date, aucun conflit.
- **Limite connue, hors périmètre** : le point 2 du plan de test manuel (« laisser l'app ouverte > 5 min puis ouvrir un mail avec PJ ») **ne peut pas passer aujourd'hui**. L'auth IMAP/SMTP d'`api-mail` s'appuie sur le **jeton PSC** (`UserContextInfo.JwtToken` est un alias de `PscToken`), qui vit ~2 min, alors que le mobile ne déclenche son préventif que sur l'`exp` du jeton **Keycloak** (5 min) — soit ~3 min sur 5 avec un `X-PSC-Token` périmé (mesure du 2026-08-30 : HTTP 500 corps vide sur `GET /api/v1/mail/folders/INBOX`, 2 min 20 d'indisponibilité). C'est le périmètre de **task-283**, pas une régression de cette US, et la compatibilité annoncée reste vraie **du côté Keycloak** — qui est bien ce que change task-015.

### v1.29 — task-282 — La clé du pool de sessions suit le client, plus le jeton (2026-08-30)

- **Task** : task-282 — `done`. **PRs** : `api-mail` [#212](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/212) et `client-mobile` [#65](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/65), toutes deux `awaiting-human-merge`. **Une seule US, deux PRs à merger ENSEMBLE** (règle 11) : séparément, chacune laisse le défaut entier — l'une envoie un en-tête que l'autre ignore encore, ou l'inverse.
- **Le défaut** : `api-mail` recréait un **pool IMAP+SMTP complet** (TCP + TLS + validation de certificat IGC-Santé + XOAUTH2) **à chaque refresh de jeton**, alors que rien dans la session du praticien n'avait changé. Le pool abandonné mourait ensuite sur son timeout d'inactivité.
- **La cause, établie sur pièce et non déduite** : la clé du pool vaut `{Email}_{ClientSessionId}`, et `ClientSessionId` venait du jeton — `sid`, puis `jti`, puis un `Guid.NewGuid()` **par requête**. Or le proxy **ne rafraîchit pas** le jeton, il le **re-frappe** (JWT Authorization Grant, RFC 7523) : **aucun `sid`**, et un `jti` neuf à chaque fois comme la RFC 7519 l'impose. Vérifié en décodant un jeton réel (`jti = "trrtag:ebead400-…"`, exactement le format des clés de pool vues dans Seq) et corroboré côté trafic : **1 420 requêtes à `ClientSessionId=unknown`**, le mobile conditionnant la pose de l'en-tête à une claim `sid` inexistante.
- **⭐ Aucun réglage serveur ne pouvait corriger ça** : `jti` est unique par jeton *par spécification*. **Seul un identifiant fourni par le client peut être stable** — c'est tout l'objet de l'US.
- **client-mobile** : identifiant tiré au **login** (`crypto.randomUUID`, repli pour contexte non sécurisé) et persisté avec la session. **Le point délicat** : `mintSessionFromCookie` est **partagé entre le login CIBA et le refresh** — y laisser générer un identifiant neuf aurait refait le défaut côté client. L'identifiant est donc **repris** de la session en cours. **Tolérance à la mise à jour** : une session persistée par une version antérieure en reçoit un à la volée **sans être invalidée** — la refuser aurait déconnecté tous les praticiens au déploiement.
- **api-mail** : l'en-tête passe **avant** les claims ; les claims restent en repli pour `client-angular` et `client-blazor`, **inchangés**. Le repli aléatoire disparaît au profit d'un littéral déterministe — deux requêtes sans en-tête ni claim partagent un pool au lieu d'en ouvrir un chacune.
- **La divergence qui rendait le défaut illisible est fermée** : le middleware de journalisation lisait l'en-tête (→ `unknown`) pendant que celui d'identité lisait les claims (→ `trrtag:…`) ; les journaux et le pool racontaient deux histoires. Le nom de l'en-tête, écrit en dur à **cinq endroits**, est désormais déclaré une fois (`ClientHeaders.ClientSessionId`) — la justification n'est pas esthétique, c'est ce qui a caché le bug.
- **Finding de sécurité trouvé PAR la code review** : la valeur vient désormais du **client**, là où elle venait d'un jeton validé. Frontière d'entrée, entrant dans la clé du pool **et** dans les champs journalisés. Bornée à 64 caractères, avec **repli sur les claims plutôt que troncature** — tronquer ferait collisionner deux clients qui ne diffèrent qu'au-delà de la borne. **Ce qu'un en-tête forgé ne permet pas, et c'est testé** : atteindre le pool d'un autre praticien, l'e-mail de la clé venant de la claim `mssEmail` du jeton validé.
- **Tests** : 16 neufs (9 backend, 7 mobile). `api-mail` **3 929 verts / 0 rouge** ; `client-mobile` **781/781** ; `ng lint` propre dès la baseline.
- **Sonar** : **Quality Gate OK**, new coverage 90,7 %, ratings A/A/A, **0 violation attribuable** (vérifiée fichier par fichier ; les 35 new-code sont de la dette héritée d'une *new code period* remontant au 2026-04-27).
- **Clôture au banc, non couverte par l'unitaire** : sur 10 min et ≥ 3 refresh, **une seule** valeur de `ClientSessionId`, et `New ImapClient` **≤ 5** (le nombre de réplicas) au lieu des ~27 relevés le 2026-08-30.

---

### v1.28 — task-166 — Rendu des tableaux Markdown (GFM) dans le chat IA et la synthèse (2026-07-17)

- **PR** : [HealthPlatform.Mobile#60](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/60) — label `awaiting-human-merge`. Branche `fix/task-166-markdown-tables`. Repo `client-mobile` uniquement. **Frontend-only** : aucun changement DTO/backend, aucune dépendance externe.
- **Cause racine** : le rendu Markdown mobile passe par l'util maison `src/app/core/utils/markdown.util.ts` (`markdownToHtml`), un mini-parser regex **escape-first (anti-XSS)** couvrant titres/gras/italique/listes/paragraphes mais **pas les tableaux GFM** — une syntaxe `| a | b |` / `|---|---|` retombait dans le remplacement `\n → <br>` et s'affichait en texte brut (pipes visibles). L'util est **partagée** par le chat IA (`mss-ai-chat`) et la synthèse IA (`mss-mail-summary`) → un seul fix corrige les deux surfaces.
- **Fix** : parsing GFM (en-tête + séparateur `|---|:--:|` + corps) exécuté **avant** le collapsing des sauts de ligne. Chaque tableau est extrait vers une **sentinelle NUL** isolée dans son propre bloc, son HTML est construit (`<table><thead>…</thead><tbody>…</tbody></table>`) avec formatage inline (`**`/`*`) et alignement (`:---`/`:--:`/`---:`) par cellule, puis **ré-injecté par remplacement fonction** — jamais dans un `<p>`, jamais cassé par des `<br>`. Approche escape-first conservée : le HTML de tableau est produit par l'util, jamais injecté depuis la source IA ; l'alignement provient d'un ensemble fermé (`left`/`center`/`right`) → aucune injection via l'attribut `style`.
- **Style** : `.md-table` + `overflow-x: auto` (défilement horizontal borné sur mobile 390 px, sans casser la bulle de chat), bordures et en-têtes, `data-testid="markdown-table"` — ajouté aux deux surfaces (`ai-chat.component.scss`, `mail-summary.component.scss`, suivant la convention existante de styles markdown par composant).
- **Simplify (`/forge-simplify`)** : skip clean — util déjà factorisée en helpers unitaires (`extractTables`/`splitRow`/`alignmentOf`/`buildTable`/`renderInline`), aucune extraction SCSS (romprait la convention par-composant). Aucun commit.
- **Lint (`/lint-mobile`)** : baseline `ng lint` **All files pass linting** — 0 erreur, 0 warning (code frais 100 % TS/SCSS, aucun template Angular). Aucun fix.
- **Verify-visual (`/verify-visual`)** : skip clean — aucun écran créé/réécrit (fix d'util partagée + style de deux composants existants, pas de `## Stitch design log`). Rendu réel des tableaux vérifié au test manuel (HAG).
- **Code review** : verdict **APPROVED** — 4 fichiers, 1 bloquant attrapé **et corrigé pendant la review** : la ré-injection utilisait une string de remplacement (`String.replace` interprète `$&`/`$$`/`$'`) → une cellule contenant un `$` corrompait le rendu, voire ré-injectait la sentinelle. Corrigé par un remplacement fonction (insertion littérale) + test de régression.
- **Tests** : 17 nouvelles specs (`markdown.util.spec.ts`) — `<table>` thead/tbody, formatage inline en cellule, alignements, faux positifs (`|` sans séparateur, séparateur invalide), anti-XSS y compris dans un tableau, normalisation du nombre de cellules, motifs `$`, non-régression titres/gras/italique/listes. Total suite : **761/761** verts.
- **Build / lint** : `npm run build` ✓ 0 erreur ; `npm test … ChromeHeadless` ✓ 761/761.
- **Commits** : `e7348b8` (feat rendu GFM + tests + styles), `a485c03` (fix motifs `$` + test régression).
- **Qualité** : `/sonar` skipped — `api-mail` non touché.
- **Conformité** : aucune donnée de santé en clair dans les logs client (aucun log ajouté) ; rendu 100 % côté client, aucun échange réseau ; anti-XSS escape-first préservé.

---

### v1.27 — task-159 — Onboarding MSSanté mobile (compte sans adresse configurée) (2026-07-16)

- **PR** : [HealthPlatform.Mobile#57](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/57) — label `awaiting-human-merge`. Branche `feat/task-159-mss-onboarding`. Repo `client-mobile` uniquement (`**Single frontend**: true`). **Frontend-only** : endpoints existants réutilisés tels quels (`POST /api/v1/account/mss-imap-test` sur `api-mail`, task-037 ; `PUT {authEndpoint}/admin/mss-profile` sur le proxy Keycloak) ; aucun changement DTO/backend. Dépend fonctionnellement de task-136 (connexion CIBA e-CPS) et task-037 (parité web).
- **Modèle d'auth** (`src/app/core/auth/auth-session.service.ts`) : nouvel état intermédiaire `needsMssOnboarding` (`!!accessToken && !userEmail`), distinct de `isAuthenticated` (inchangé, exige toujours la session complète) ; `readFromStorage()` ne jette plus une session token-only (conservée pour l'onboarding). `authGuard` : token-only → route onboarding, pas de token → `/login`, session complète → passe. Nouveau `mssConfiguredGuard` protège les routes `ion-tabs`/INBOX tant que `needsMssOnboarding`, exempte `mss-unconfigured`/`mss-setup`.
- **Écrans** (`src/app/mss-onboarding/`) : `mss-unconfigured` (verrou plein écran, CTA « Configurer mon compte ») et `mss-setup` (formulaire 1 champ adresse MSSanté, phases `editing → submitting → success`, bouton « Se déconnecter maintenant »). Routes ajoutées hors `ion-tabs` dans `app-routing.module.ts` (comme `login`).
- **`MssOnboardingService`** : `validateImapConnection(email)` → `POST /api/v1/account/mss-imap-test` (mêmes codes d'erreur que task-037 : `AUTH_FAILED`/`HOST_UNREACHABLE`/`MAILBOX_NOT_FOUND`/`INVALID_EMAIL`, mappés en FR) ; `persistMssEmail(email)` → `PUT {authEndpoint}/admin/mss-profile`, bearer (pas `withCredentials` — divergence assumée vs web, session mobile).
- **Réutilisation** : composants/tokens Ionic + design system E014 « Clinical Precision » réutilisés tels quels (boutons, inputs, toasts) ; `mss-headers.interceptor`/base URL API MSS réutilisés (pas de client HTTP ad hoc).
- **Assertion clé DOD** : aucun appel mail/mss-api avant configuration — garanti structurellement par `[authGuard, mssConfiguredGuard]` sur `/home` et `/tabs` (les composants concernés ne sont jamais activés tant que `needsMssOnboarding`).
- **Simplify (`/forge-simplify`)** : skip clean — code déjà à bonne altitude (guards en pattern `inject` idiomatique, logout setup ≠ logout settings, `responseType: 'text'` réutilise le pattern défensif de `sendMail`). Aucun commit.
- **Lint (`/lint-mobile`)** : baseline `ng lint` **All files pass linting** — 0 erreur, 0 warning sur le code frais. Aucun fix nécessaire (conventions `conventions/angular.md` appliquées d'emblée : `@if` natif, préfixes `app-`/`mss-`, FR en dur, `data-testid`).
- **Verify-visual (`/verify-visual`)** : 2/2 écrans capturés (390×844, session **token-only** injectée — jeton présent, `userEmail` vide), aucun écran blanc, aucune erreur console. `capture.mjs` étendu (option `session: "token-only"`) + `screens.json` (`mss-unconfigured`, `mss-setup`). Captures : `Client/Mobile/e2e/screenshots/task-159/` (commit `1da6ba0`) + copiées dans `Docs/epics/img/screens/client-mobile/` (galerie E012). Réf. Stitch : `mss-unconfigured` (screen `2bba91686d4c4c93a1feee5043949d4f`, fidèle) ; `mss-setup` (génération en timeout MCP — intention appliquée, pas de re-génération, mémoire `reference_stitch_generate_screen_timeouts`).
- **Code review** : verdict **APPROVED** — 23 fichiers, 0 bloquant, 1 suggestion non bloquante (`mssConfiguredGuard` recoupe partiellement `authGuard` sur `/home`/`/tabs`, intentionnel).
- **Tests** : 25 nouvelles specs — `auth-session.service` (needsMssOnboarding + isAuthenticated inchangé + readFromStorage token-only, 4 cas), `auth.guard` (3 cas), `mss-onboarding.guard` (5 cas, guard app-configurée + exemption onboarding), `MssOnboardingService.validateImapConnection` (succès + 4xx par code), `MssOnboardingService.persistMssEmail` (204 + 4xx/5xx + bearer), `mss-setup` (rendu, validation champ requis/format/maxLength 254, chaîne IMAP OK→persist / IMAP KO→pas de persist), `mss-unconfigured` (rendu + CTA nav). Total suite : **537/537** verts.
- **Build / lint** : `npm run build` ✓ 0 erreur ; `npm test … ChromeHeadless` ✓ 537/537.
- **Commits** : `8e5934c` (feat auth token-only), `28bb188` (feat écrans + service onboarding), `1da6ba0` (captures verify-visual).
- **Qualité** : `/sonar` skipped — `api-mail` non touché par cette task.
- **Staging aggregation** : **non agrégée** sur `forge/staging-task-142-160-20260716` — conflit best-effort sur `src/app/app-routing.module.ts` avec task-149 (déplacement `/home` → redirect `tabs/home`) ; `git merge --abort`, PR #57 `feat → develop` intacte, task reste `done`. Note d'intégration humaine (HAG) : au merge, si task-149 précède task-159, porter les gardes `[authGuard, mssConfiguredGuard]` sur `tabs/home` (ou conserver le parent `/tabs`, déjà gardé) — pas de perte de sécurité, la protection reste assurée par le garde du parent `/tabs`.
- **Conformité** : aucune adresse MSSanté ni donnée sensible en clair dans les logs console/URL (transite uniquement dans le corps des POST/PUT) ; validation IMAP réutilise l'authentification serveur existante (aucun secret utilisateur en clair côté client) ; persistance en **bearer** (session mobile), pas de cookie `withCredentials` ; événements journalisés côté mobile (tentative, succès, échec IMAP, échec persistance) sans adresse en clair ; authentification PS (e-CPS/CIBA, task-136) inchangée ; AIPD à signaler — vérifier que la note RGPD/AIPD du périmètre mobile couvre la saisie et la transmission de l'adresse MSSanté du PS au proxy Keycloak.

---

### v1.26 — task-145 — Signatures (CRUD + injection compose) (2026-07-11)

- **PR** : [HealthPlatform.Mobile#49](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/49) — label `awaiting-human-merge`. Branche `feat/task-145-mobile-signatures`. Repo `client-mobile` uniquement. **Frontend-only** : endpoints backend existants (`GET /api/v1/Signature`, `GET /Signature/default`, `POST /Signature`, `PUT /Signature/{id}`, `DELETE /Signature/{id}`, `PUT /Signature/{id}/default` — parité `client-angular` `mss-api.service.ts:672-752`, E009-F014, backend task-023) ; aucun changement DTO. Pas de dépendance. Epic E012.
- **`signature.model.ts`** : `SignatureDto`, `CreateSignatureDto`, `UpdateSignatureDto` (= alias `CreateSignatureDto`, DRY), `EditableSignature` + `createEmptySignature`/`signatureFromDto`.
- **`MssApiService`** : 6 méthodes — `getSignatures`, `getDefaultSignature`, `createSignature`, `updateSignature` (`encodeURIComponent(id)`), `deleteSignature`, `setDefaultSignature`. Tests unitaires succès + erreur (10 cas ; encodage id vérifié).
- **Écran Signatures** (`signatures/` — page module lazy `standalone:false`, route `/signatures` déclarée dans `app-routing.module.ts`, poussée au-dessus des onglets comme `mail-search`) : liste `ion-list` (badge `Par défaut`), éditeur en `ion-modal` (nom `ion-input`, contenu `mss-html-editor` réutilisé, toggle `ion-toggle` défaut, suppression `AlertController` + confirmation), `loadSignatures` après save/delete, erreurs en toast (`extractProblemDetail`). `canSave` (nom non vide). Spec : 9 tests (load, erreur, création, update PUT, toggle défaut + reload, nom vide, suppression confirmée).
- **`SettingsPage`** : section « Rédaction » → item `settings-signatures-nav` → `router.navigateByUrl('/signatures')`.
- **`mail-compose`** : signaux `signatures`/`selectedSignatureId` ; `loadSignatures(inject)` — injecte la signature par défaut à l'ouverture d'un message frais (new/reply/forward) via `injectSignature` (helper module pur : place la signature avant le marqueur `<blockquote` en réponse/transfert, sinon en fin de corps ; encadrée par `<!-- signature -->…<!-- /signature -->`), gardée par `!bodyHtml().includes(SIGNATURE_OPEN)` ; reprise de brouillon = `loadSignatures(false)` (corps authoritatif, pas de réinjection). Sélecteur `ion-select` (Aucune + signatures) → `onSignatureChanged` (`stripSignature` regex puis réinjection — jamais d'empilement). `reset()` nettoie les signaux. +6 tests (injection new/reply/forward au bon emplacement, swap sélecteur + « Aucune », non-réinjection brouillon).
- **Simplify (`/forge-simplify`)** : skip clean — reuse déjà appliqué (`mss-html-editor`, `extractProblemDetail`, confirmation `AlertController`, alias de type, helpers purs) ; écran en modale mobile-idiomatique (pas de calque du two-panel Angular) ; service toast/erreur partagé = hors scope isolé (règle 6).
- **Lint (`/lint-mobile`)** : `ng lint` **All files pass** — 0 erreur.
- **Verify-visual (`/verify-visual`)** : 2/2 écrans (`signatures`, `mail-compose`) capturés, aucun écran blanc, aucune erreur console — commit `28d83e6`. Outillage : mapping `signatures` (`screens.json`) + fixtures `/api/v1/Signature` & `/default` (`capture.mjs`). Captures SHA-pinnées : `e2e/screenshots/task-145/{signatures,mail-compose}.png`. La capture compose confirme l'injection automatique de la signature par défaut + le sélecteur.
- **Build / tests** : `npm run build` ✓ (0 erreur) · `npm test … ChromeHeadless` **506 SUCCESS** (+37 vs baseline 469).
- **Commits** : `857066c` (feat signatures), `28d83e6` (captures verify-visual).
- **Conformité** : aucune donnée de santé en log ; toasts via `ProblemDetails` (RFC 7807) ; signatures cloisonnées par praticien (backend task-023).
- **Limite / follow-up** : `setDefaultSignature` exposé et testé mais non câblé à une action rapide de liste (le défaut se règle via le toggle de l'éditeur → create/update `isDefault`, exclusivité backend) — action « définir par défaut » one-tap depuis la liste = amélioration UX future.

### v1.25 — task-143 — Dossiers personnalisés (CRUD) + jauge de quota (2026-07-11)

- **PR** : [HealthPlatform.Mobile#48](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/48) — label `awaiting-human-merge`. Branche `feat/task-143-custom-folders-mailbox-quota`. Repo `client-mobile` uniquement. **Frontend-only** : endpoints backend existants (`POST /api/v1/mail/folders`, `PUT …/folders/{path}/rename`, `DELETE …/folders/{path}`, `GET /api/v1/account/quota` — parité `client-angular` `mss-api.service.ts:246-284/187`, task-087) ; aucun changement `api-mail`/DTO. Pas de dépendance. Epic E012.
- **`MssApiService`** : 4 méthodes — `createFolder({name, parentPath?})` (POST), `renameFolder(path, {newName})` (PUT `…/{encoded}/rename`), `deleteFolder(path)` (DELETE `…/{encoded}`), `getMailboxQuota()` (GET `/api/v1/account/quota`). `encodeURIComponent` sur les chemins. Tests unitaires succès + erreur (création racine {name} / sous-dossier {name,parentPath}, 409 conflit, rename encodé, delete + relais `ProblemDetails` dossier non vide, quota succès + 500).
- **`mailbox-quota.model.ts`** : miroir TS de `MailboxQuotaDto` (`usedBytes`, `totalBytes`, `usagePercentage`, `available`).
- **`mss-mailbox-quota-widget`** (nouveau composant standalone, OnPush) : charge son propre quota en `ngOnInit` (`takeUntilDestroyed`), computed `level` (normal < 80 % / warning ≥ 80 % / critical ≥ 90 %), `percentage` bornée [0,100], `usageText` formaté FR (`toLocaleString('fr-FR')`, Go ≥ 1 Gio sinon Mo). Échec réseau → `available=false` (état « Quota non disponible », pas d'erreur remontée). Littéraux ambre `#f59e0b`/`#b45309` (socle sans token ambre) ; critique = `--ion-color-danger`. 6 tests (3 niveaux + non disponible + échec réseau + format Go/borne).
- **`mss-mail-folder-item`** : getter `isCustom` (`FolderType.Custom`), `@Output() folderMenu`, bouton `⋯` rendu `@if (isCustom)`, appui long (pointer events + `setTimeout` 450 ms + `@capacitor/haptics`, drapeau `longPressFired` avalant le clic) **gardé sur `isCustom`** (retour anticipé sinon), propagation récursive `onChildMenu`. Dossiers système/tags : aucun menu. +6 tests (isCustom, rendu bouton Custom vs système, `openMenu` émet folderMenu pas folderClick, long-press Custom-only, système jamais, propagation enfant).
- **`mss-mail-folder-list`** : bouton « + » en tête de section Dossiers (`createRootFolder`), `openFolderMenu` → `ActionSheetController` (Nouveau sous-dossier / Renommer / Supprimer), saisie via `AlertController` (handlers retournant `false` pour garder l'alerte ouverte sur nom vide/inchangé), `confirmDeleteFolder` (alerte destructive), `refreshFolders` via `getFolders` → `state.setFolders` (pas de reload complet), erreurs relayées en toast via `extractProblemDetail`, bascule sur Inbox si le dossier supprimé était sélectionné. Jauge `mss-mailbox-quota-widget` épinglée en pied (flex column + `margin-top:auto`). Spec (nouveau) : 10 tests (rendu +/items/quota, sélection, create racine + nom vide, create sous-dossier avec parentPath, rename + nom inchangé, delete + fallback Inbox, échec serveur sans throw).
- **Simplify (`/forge-simplify`)** : skip clean — reuse déjà appliqué (`extractProblemDetail`, récursion folder-item, pattern long-press de `mail-header`, jauge miroir Angular) ; `formatFileSize.util` écarté (plafonne Mo + décimale anglaise, le quota exige Go + FR) ; extraction d'un directive long-press partagé notée hors périmètre (règle 6).
- **Lint (`/lint-mobile`)** : `ng lint` **All files pass** — 0 erreur (code frais conforme `conventions/angular.md`).
- **Verify-visual (`/verify-visual`)** : 1/1 écran `mail-folder-list` capturé (390×844), aucun écran blanc, aucune erreur console — commit `3b3d0ba`. Outillage enrichi : `capture.mjs` (route `/api/v1/account/quota`) + `fixtures/folders.json` (dossier Custom « Suivi » + sous-dossier) pour matérialiser le menu ⋯ et la jauge. Capture SHA-pinnée : `e2e/screenshots/task-143/mail-folder-list.png`.
- **Build / tests** : `npm run build` ✓ (0 erreur) · `npm test … ChromeHeadless` **469 SUCCESS** (+31 vs baseline 438).
- **Commits** : `cfaf0bc` (feat dossiers + quota), `3b3d0ba` (captures verify-visual).
- **Conformité** : aucune donnée de santé en log ; toasts d'erreur via `ProblemDetails` (RFC 7807, `detail`/`title`) ; CRUD limité aux dossiers de la boîte du titulaire (habilitations inchangées).

### v1.24 — task-141 — Sélection multiple + actions en masse sur l'inbox (2026-07-08)

- **PR** : [HealthPlatform.Mobile#45](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/45) — label `awaiting-human-merge`. Branche `feat/task-141-mobile-bulk-actions`. Repo `client-mobile` uniquement. **Frontend-only** : endpoints bulk existants (`…/emails/bulk/status/{read|unread|flagged|unflagged}`, `…/emails/bulk/move`, `DELETE …/emails/bulk` — parité `client-angular` `mss-api.service.ts:322/1448-1590`) ; aucun changement `api-mail`/DTO. Pas de dépendance. L'état de sélection (`selectedMailUids`, `isSelectionMode`) était posé depuis task-099 sans UI ; cette task l'exploite.
- **`MssApiService`** : 6 méthodes bulk — `bulkUpdateReadStatus`, `bulkUpdateUnreadStatus`, `bulkUpdateFlagStatus`, `bulkUpdateUnflagStatus` (PUT, body = `uids[]`), `bulkMoveEmails` (PUT, body `{uids, targetFolderPath}`), `bulkDeleteEmails` (DELETE avec body `uids[]` via `http.request`). Renvoient le nombre d'emails traités. Tests unitaires succès + erreur + assertion du compte retourné.
- **`MailStateService`** : `enterSelectionMode(uid?)`, `selectAllVisible()` (coche tous les `conversationList()`), `deselectAll()`, computed `selectedCount`, `isAllSelected` (faux sur liste vide). Réutilise `toggleMailSelection`/`clearSelection` existants.
- **`MailActionsService`** : orchestration en masse **optimiste + rollback** miroir des méthodes unitaires — `bulkMarkRead`/`bulkMarkUnread` (décrément/incrément du compteur non-lus limité aux mails qui basculent réellement), `bulkFlag`, `bulkDelete`/`bulkMove` (retrait immédiat + `restoreMails` en rollback). Helper `folderOf(mails)` = `mails[0].folderPath` (invariant liste mono-dossier mobile).
- **`mss-mail-header`** : appui long (450 ms, `@capacitor/haptics` `ImpactStyle.Medium`) via pointer events (`pointerdown`/`up`/`leave`/`cancel` + `setTimeout`, drapeau `longPressFired` avalant le clic synthétique) → `@Output() longPress` ; case `ion-checkbox` visuelle (`pointer-events:none`) affichée en mode sélection.
- **`mss-mail-list`** : `onLongPress` (entre en sélection / coche), `onMailClick` coche-décoche en mode sélection au lieu d'ouvrir, `ion-item-sliding [disabled]` en sélection (pas de conflit swipe). Lecture réactive `isChecked(uid)`.
- **`InboxPage`** : barre d'actions contextuelle dans le header (`@if (isSelectionMode())`) — Annuler (`close`), compteur « N sélectionné(s) », Tout sélectionner (bascule `checkbox`/`checkbox-outline`), et actions Lu/Non lu/Flag/Déplacer/Supprimer (icon buttons, `[disabled]` si 0). `runBulk()` factorise les 3 handlers sans confirmation (résout `selectedMails()` **avant** `clearSelection()`, dispatch, toast d'erreur via `extractProblemDetail`). Déplacement = action sheet des dossiers (hors dossier courant) ; suppression = alerte de confirmation (cascade lien patient, copie pluralisée de l'unitaire).
- **Simplify (`/forge-simplify`, commit `cba85a4`)** : retrait du code mort `MailActionsService.bulkUnflag` (la barre n'expose que Flag ; l'endpoint `bulkUpdateUnflagStatus` reste côté API — parité contrat + DOD) ; `toggleSelectAll` passe par `MailStateService.deselectAll()` au lieu de muter le signal brut. Findings écartés : symétrie read/unread & flag/unflag écrite explicitement (idiome des actions unitaires existantes), long-press inline (consommateur unique — directive prématurée), **extraction d'un `MailPromptsService`** pour les prompts « Déplacer »/« Supprimer » désormais dupliqués 3× (mail-list/mail-detail/inbox) → **noté en follow-up** (toucherait 2 composants pré-existants testés, hors périmètre d'une passe simplify).
- **Lint (`/lint-mobile`)** : baseline `ng lint` « All files pass linting » (0 error / 0 warning), 0 itération — code frais déjà conforme (`@if`/`@for`, préfixes `mss-`/`app-`, FR en dur, `data-testid`).
- **Vérification visuelle (`/verify-visual`, commit `b70deb1`)** : capture Playwright headless de `inbox` + `mail-list` (fixtures fictives, aucun backend) — **aucun écran blanc, aucune erreur console**. Smoke ciblé : le header de l'inbox ayant été restructuré (`@if isSelectionMode`), la capture confirme la non-régression du rendu par défaut (non couvert par `inbox.page.spec` qui n'instancie pas le template). Captures SHA-pinnées : [`inbox`](https://github.com/codengine-technologies/HealthPlatform.Mobile/blob/b70deb1216eee7dfc334a6571a4ef532d06a5c4e/e2e/screenshots/task-141/inbox.png), [`mail-list`](https://github.com/codengine-technologies/HealthPlatform.Mobile/blob/b70deb1216eee7dfc334a6571a4ef532d06a5c4e/e2e/screenshots/task-141/mail-list.png). Le mode sélection (état d'interaction par appui long) n'est pas scripté par la capture → validation ergonomique au HAG.
- **Code review** : verdict **APPROVED** (0 blocking). Correctness (invariant mono-dossier `folderOf`, décrément non-lus ciblé sur les mails qui basculent, `selectedMails()` capturé avant `clearSelection`), Security (`folderPath` encodé, uids numériques, erreurs via `ProblemDetails` — aucune donnée de santé loguée), Architecture (miroir du pattern optimiste unitaire, `data-testid` partout), Test coverage — tous ✓.
- **Tests** : +29 (399→428) — api (6 méthodes bulk succès/erreur/compte), mail-actions (bulkMarkRead optimiste + compteur + rollback, bulkFlag rollback, bulkDelete retrait+réinsertion+compteur, bulkMove payload), mail-state (enterSelectionMode, toggle, selectAllVisible, isAllSelected vide/partiel, clearSelection), mail-list (onLongPress, onMailClick toggle, second long-press), mail-header (longPress après seuil + avalage du clic, relâchement avant seuil, checkbox en mode sélection), inbox (toggleSelectAll, cancelSelection, bulkMarkRead dispatch + sortie, no-op sélection vide, toast d'erreur). Total suite : **428/428** verts.
- **Build / lint** : `npm run build` ✓ 0 erreur (warnings budget SCSS préexistants) ; `ng lint` ✓ 0/0.
- **Fix post-HAG (commit `dc29dc4`)** : régression signalée par le praticien — en mode sélection, les lignes s'affichaient **vides**. Cause : `ion-checkbox` (display:block, label-placement) s'étirait à 100 % de la ligne (mesuré 358 px), écrasant avatar + contenu à largeur nulle. `innerText` restait non vide (contenu clippé, pas absent) → le smoke `/verify-visual` initial ne l'avait pas détecté. Correctif : `.mail-select-check { width: 26px }`. **Prévention** : `capture.mjs` gagne une action `longPress` et un écran mappé `inbox-selection` — l'état de sélection est désormais capturé à chaque cycle (screenshot `inbox-selection.png` : lignes complètes + case + barre contextuelle).
- **Commits** : 5ee53a8 (feat + tests), cba85a4 (simplify), b70deb1 (captures verify-visual), dc29dc4 (fix case de sélection + capture inbox-selection).
- **Conformité** : US de parité d'une capacité web existante (hors DSR nouvelle) ; opérations bulk journalisées côté `api-mail` (canal PGSSI-S existant) ; suppression en masse = cascade lien patient + docs rattachés (voulu, reconstruit à la restauration — cohérent avec l'unitaire) ; **aucune donnée de santé loguée** côté client (0 `console.*`, erreurs via `ProblemDetails`) ; auth PSC/e-CPS et habilitations inchangées. INS non applicable.

---

### v1.23 — task-140 — Écran Paramètres mobile réel (fin du placeholder) (2026-07-07)

- **PR** : [HealthPlatform.Mobile#44](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/44) — label `awaiting-human-merge`. Branche `feat/task-140-mobile-settings`. Repo `client-mobile` uniquement. **Frontend-only** : endpoints existants (`GET /api/v1/Settings/getsettings`, `POST /api/v1/Settings` — parité Angular `mss-api.service.ts:624/638`) ; aucun changement `api-mail`/DTO. Pas de dépendance.
- **`MssApiService`** : `saveUserSettings(dto)` ajouté (POST du DTO complet — l'endpoint remplace l'objet en bloc). Tests succès + erreur pour `getUserSettings` et `saveUserSettings`.
- **Contrat partagé web↔mobile (point central)** : `UserSettingsDto` mobile étendu en **sous-ensemble typé** (defaultFolder, `SettingsInboxFilter`/`SettingsMailViewMode` int serveur ≠ enums string locaux, minSimilarity, `SenderIdentityDto`, `NotificationPreferencesDto`, maxAttachmentSizeBytes). Les champs desktop non transposés (thème, densité, volet, IMAP/SMTP, full-sync…) **transitent tels quels au POST** : toute mutation spread l'objet chargé, et **aucun POST tant que le GET n'a pas réussi** (un POST from scratch écraserait les réglages web) → écran en état d'erreur + « Réessayer » sinon. Passthrough vérifié par test dédié.
- **`UserSettingsService`** (nouveau store racine signals) : `ensureLoaded()` mémoïsé (`loadPromise ??=`, GET unique/session, retry sur échec), auto-save **debouncée 300 ms** (parité mss-settings Angular) + `switchMap` (annulation sans perte — le POST suivant porte l'objet accumulé), `saved$` one-shot → toast « Préférences enregistrées », computeds `senderDisplayName`, `newMailToastsEnabled`/`abnormalBiologyToastsEnabled` (**absent = actif** — pas de coupure silencieuse), `consumeInboxDefaults()` one-shot session. Utils purs de modèle `senderIdentityFromDisplayName` (split au 1er espace) / `getSenderDisplayName` (précédent patient.model.ts).
- **`settings.page`** (placeholder remplacé, réf. Stitch `settings`) : sections Identité (nom affiché) / Organisation (dossier à l'ouverture via `ion-select` sur les dossiers IMAP, segments Tous·Non lus et Liste·Conversation) / Recherche (`ion-range` % → `SearchSettingsService` + serveur) / Notifications (2 toggles) / Lecture (limite PJ lecture seule via `formatFileSize`) / Compte (adresse MSSanté + déconnexion conservée verbatim avec confirmation) / À propos (`environment.appVersion`). FR en dur, `data-testid` sur chaque contrôle (17).
- **Branchements effectifs** : inbox applique filtre + mode d'affichage par défaut **une fois par session** (`consumeInboxDefaults`, les bascules manuelles priment ensuite) et sélectionne le **dossier préféré** au chargement (repli INBOX) ; GET settings et GET folders **parallélisés** à la première entrée ; gating des toasts SSE dans `handleNotification` (toast + insertion coupés si préférence désactivée) ; `mail-compose` migré sur le store partagé (suppression du GET dupliqué) et **`from.name`** posé depuis l'identité au `sendMail`. Limite connue : le chemin `sendDraft` (SaveDraftDto sans `from`) ne transporte pas le nom — gap contrat, noté pour follow-up backend éventuel.
- **Divergence assumée vs web** : le web **n'applique pas** son inboxFilter persisté à l'ouverture et ne consomme pas ses préférences de notifications (gaps Angular connus) — le mobile les branche réellement (exigence DOD). Filtre « Lus » (serveur) sans équivalent mobile → mappé sur Tous.
- **Simplify (`/forge-simplify`, commit `bb73937`)** : parallélisation settings/folders inbox (2 RTT → 1) ; machine d'états `saveStatus` (4 états + timer) → émission one-shot `saved$` (seule transition observée) ; fusion des 2 handlers de toggles en `onNotificationToggle(key, ev)` ; `formatFileSize` réutilisé (formatteur homogène avec la jauge compose) ; transformations nom↔identité extraites en utils de modèle. Skips motivés : `ensureFoldersLoaded` partagé (state container sans IO, consommateur unique), logout dupliqué inbox/settings (préexistant, hors diff), prédicat `shouldNotify` (2 ifs lisibles).
- **Lint (`/lint-mobile`)** : baseline 5 errors `prefer-control-flow` (\*ngIf/\*ngFor introduits) → conversion manuelle `@if` / `@for (…; track folder.path) @empty` (commit `294bda2`) → 0 error / 0 warning.
- **Code review** : verdict **APPROVED** (0 blocking) — passthrough des champs non typés vérifié (POST toujours superset de l'objet serveur), debounce/switchMap corrects, once-per-session, gating par défaut, pas de course settings/dossier préféré. Suggestions non bloquantes : asymétrie dossier (ré-appliqué à chaque entrée, parité comportement antérieur) vs filtre/mode (une fois/session) — à éyeballer au HAG ; surbrillance `ion-segment` à valeurs numériques à confirmer sur device ; cache settings non purgé au logout (neutralisé par le full reload du login).
- **Tests** : +32 (367→399) — service settings (load mémoïsé + retry, debounce 299/1 ms, passthrough champs non typés, `saved$` succès/échec silencieux, split du nom, sync similarité, défauts notifications, one-shot inbox), api (POST/GET succès+erreur), settings.page (rendu des sections + testids, état d'erreur + retry, save debouncée, toast, toggles, options dossiers), inbox.page (nouvelle spec : défauts appliqués/une-fois, dossier préféré + repli, gating on/off par kind), compose (`from.name` posé/omis). Total suite : **399/399** verts.
- **Build / lint** : `npm run build` ✓ 0 erreur (warning budget SCSS `settings.page.scss` +145 o, pattern préexistant) ; lint ✓ 0/0.
- **Stitch** : écran **`settings` créé** (id `34d145c4e04d48ebab80ff05afb709af`, titre exact obtenu — timeout MCP attendu, matérialisation détectée par diff `get_project` ~4 min). Bonus : la génération `mail-draft-list` de task-139 (réputée non matérialisée) a fini par atterrir (id `f9001616b2064b4a837a61e37a053345`, titre exact) — le rejeu manuel noté en task-139 n'est plus nécessaire ; labelliser les 2 instances dans l'UI.
- **Commits** : 5678615 (feat + tests), bb73937 (simplify), 294bda2 (lint control flow).
- **Conformité** : préférences stockées **côté serveur** (HDS), aucune persistance locale de donnée de santé (seul le seuil de recherche vit en localStorage — réglage d'ergonomie) ; settings cloisonnés par praticien (backend task-023) ; déconnexion inchangée (purge session locale, tracée serveur) ; **aucune donnée de santé loggée** (0 `console.*`) ; auth PSC/e-CPS inchangée. INS non applicable.

---

### v1.22 — task-139 — Brouillons sur mobile : auto-save, dossier Brouillons, reprise, envoi (2026-07-06)

- **PR** : [HealthPlatform.Mobile#43](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/43) — label `awaiting-human-merge`. Branche `feat/task-139-mobile-drafts`. Repo `client-mobile` uniquement. **Frontend-only** : endpoints existants (`saveDraft`, `updateDraft`, `getDrafts`, `getDraft`, `deleteDraft`, `sendDraft` — parité `client-angular` `mss-api.service.ts:2077-2148`) ; modèles TS déjà posés (`core/models/draft.model.ts`, task-095) ; aucun changement `api-mail`/DTO. Pas de dépendance.
- **`MssApiService`** : 6 méthodes brouillons — `saveDraft` (POST création), `updateDraft(id)` (PUT), `getDrafts()` (liste), `getDraft(id)` (unitaire), `deleteDraft(id)` (DELETE), `sendDraft(id)` (envoi + nettoyage serveur atomique) — verbes/URLs alignés sur l'API consommée par `client-angular`. Tests unitaires succès + erreur par méthode.
- **Auto-save 30 s (`mail-compose`)** : sauvegarde périodique dès que le compose porte du contenu (destinataire/objet/corps non vides) — **création** (POST) au premier cycle, **update** (PUT) ensuite, factorisée en `persistDraft(notify)`. Pas de save à vide, garde de réentrance `isSavingDraft`, auto-save **inhibé pendant l'envoi**, désabonnement explicite + `takeUntilDestroyed`. Fermeture du compose avec contenu non envoyé → brouillon conservé. Testé en `fakeAsync` (`tick(30000)`, création-puis-update, pas de doublon).
- **Dossier Brouillons** : `imapFolders` admet `FolderSource.Drafts` → entrée « Brouillons » dans `mail-folder-list` avec badge = compteur total. Dossier **virtuel** servi par `getFolders()` (Redis côté serveur) — feature atteignable.
- **`mail-draft-list`** (nouvel écran dédié) : liste des brouillons (objet, destinataires, date via `formatRowDate`), tap → réouverture du compose **pré-rempli fidèlement** (To/Cc/Cci, objet, corps HTML, PJ serveur en `carriedOver`), suppression par **swipe** avec confirmation `AlertController` (confirm/cancel/erreur testés). `data-testid` : `draft-item`, `draft-delete`, `draft-date`, `draft-list-empty`, `compose-draft-saved`.
- **Envoi & anti-orphelin** : envoi d'un brouillon via `sendDraft` (nettoyage serveur atomique) ; envoi normal d'un compose auto-sauvegardé → brouillon intermédiaire nettoyé. **Chemin PJ locale (base64)** : repli `sendMail` + `deleteDraft` (le `SaveDraftDto` ne transporte pas les PJ — `sendDraft` seul les perdrait, gap présent côté Angular) ; sans PJ locale : `sendDraft`. Pas d'orphelin dans les deux cas. Suppression externe d'un brouillon → pas de résurrection (testé).
- **Choix** : composant dédié `mail-draft-list` (Angular réutilise `mail-list` avec des `MailDto` synthétiques ; sur mobile `mail-list` est couplé aux actions IMAP par uid → composant dédié plus sûr, colle à la convention Stitch « 1 écran = 1 composant ») ; `formatRowDate` extrait de `mail-header` vers `core/utils/row-date.util.ts` (réutilisé par `mail-draft-list`, +tests).
- **Parité assumée (gap connu)** : les PJ ne sont **pas** persistées dans le brouillon (`buildSaveDraftDto` sans `attachmentIds`) ; la reprise restaure ce que le serveur renvoie (`draft.attachments`, en pratique vide) — gap présent côté `client-angular`, non corrigé ici (hors scope US).
- **Simplify (`/forge-simplify`, commit `ec0f1de`)** : `persistDraft(notify)` factorise la règle POST-création/PUT-update en un seul endroit (simplification/altitude) ; `fetchDraftsInto(folderPath)` partagé par `loadDraftsFolder`/`refreshDrafts` (inbox) ; **efficiency** : `draftSent$` émis à la **création** et à la **fermeture** seulement (plus à chaque PUT du cycle 30 s — le badge ne changeait pas), supprime un `GET /drafts` par tick d'auto-save par compose ouvert (+test dédié). Skips motivés : **PUT-upsert systématique sans POST** (dépend du contrat backend non vérifié, romprait la parité Angular — noté pour plus tard) ; split `draftSent$` en deux évènements (le gating suffit) ; extraction `buildFallbackGuid` (consommateur unique). Rollback : aucun.
- **Code review** : verdict **APPROVED** (0 blocking, 22 fichiers reviewés). Validés : parité endpoints Angular, cycle de vie des subscriptions (`takeUntilDestroyed` + désabonnement explicite de l'auto-save, garde `isSavingDraft`, auto-save inhibé pendant l'envoi), dossier virtuel servi par `getFolders()`, aucun trait/contenu de courrier loggé. Suggestions non bloquantes : commentaire POST/PUT imprécis dans `persistDraft` (PUT backend = upsert, comportement correct) ; course théorique faible si réouverture d'un compose pendant la persistance de fermeture (best-effort accepté) ; scintillement cosmétique possible du badge sur le chemin `sendMail`+`deleteDraft`.
- **Tests** : +32 (335→367) — service (6 méthodes drafts succès/erreur), `mail-compose` auto-save (`fakeAsync` `tick(30000)`, création-puis-update, pas de doublon, pas de save à vide), reprise pré-remplie, envoi `sendDraft` + nettoyage, fermeture → conservation, suppression externe → pas de résurrection, suppression swipe confirm/cancel/erreur, `row-date.util`. Total suite : **367/367** verts.
- **Build / lint** : `npm run build` ✓ 0 erreur ; `/lint-mobile` baseline 0 error / 0 warning (« All files pass linting »), 0 itération.
- **Stitch** : `mail-folder-list` réutilisé (entrée Brouillons + badge, id `84138523de2c40c1aa866c64bb5ef84d`), `mail-compose` réutilisé (indicateur auto-save discret, id `340f18be9395435f8fc472e0c476f736`). Écran `mail-draft-list` : `generate_screen_from_text` en **timeout MCP** puis **aucun nouvel écran matérialisé** (diff `get_project` après 2 tentatives ~3 et ~20 min) → **pas de re-génération** (anti-doublon), implémenté sans référence à partir des conventions « Clinical Precision » (listes denses 56 px, séparateurs 1 px, Public Sans). Prompt de génération consigné dans la task pour rejeu manuel dans l'UI Stitch.
- **Commits** : d4994ba (feat + tests), ec0f1de (simplify `/forge-simplify`).
- **Conformité** : brouillons **stockés côté serveur** (Redis backend HDS), **aucune persistance locale mobile** ; cloisonnement par praticien (garantie backend task-023) ; cycle de vie des brouillons géré côté serveur (canal existant) ; **aucun contenu de courrier loggé** côté client (0 `console.*`) ; auth PSC/e-CPS inchangée ; envoi/suppression tracés côté `api-mail` (PGSSI-S). INS non applicable (pas de manipulation d'INS spécifique aux brouillons).

---

### v1.21 — task-138 — Garde-fous d'envoi conformes (INS, opposition, PJ) (2026-07-06)

- **PR** : [HealthPlatform.Mobile#42](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/42) — label `awaiting-human-merge`. Branche `feat/task-138-compose-send-guards`. Repo `client-mobile` uniquement. **Frontend-only** : endpoints existants (`validate-ins`, `opposition`, `getsettings`, champ `blockPatientReply` du DTO d'envoi) ; aucun changement `api-mail`/DTO. Pas de dépendance.
- **`MssApiService`** : `validatePatientIns(ins)` (GET `/api/v1/Patients/ins/{ins}/validate-ins` → `InsValidationResultDto`, DTO déjà posé en task-095) ; `getUserSettings()` (GET `/api/v1/Settings/getsettings` → `UserSettingsDto` transposé en sous-ensemble mobile : `maxAttachmentSizeBytes`). `OutgoingMailDto` : + `blockPatientReply?`.
- **`mail-compose` — chaîne de garde-fous dans `send()`** (ordre Angular) : (1) rappel PJ oubliée (task-084 — `attachment-reminder.util` porté tel quel : hints ci-joint/pièce jointe/en annexe/veuillez trouver + `\bpj\b`, NFD accent-insensible, strip HTML) → dialog « Envoyer quand même ? » ; (2) par INS destinataire MES (`mss-address.util`) : `validatePatientIns` → non qualifiée = **blocage** (bandeau FR exact Angular, 8 s, timer suivi) ; qualifiée → dialog d'identité (Nom via `getPatientByIns`→`getPatientFullName`, date fr-FR, sexe via `getPatientGenderLabel`) annulable ; erreur API → l'envoi continue (parité — backend garde-fou final). Dialogs = overlay Promise-based (signal `confirmDialog` + resolver), libéré défensivement sur remplacement/close/reset.
- **Opposition** : bandeau **non bloquant** (divergence volontaire vs confirm Angular — contrat DOD PO), rafraîchi par effect mémoïsé (`computed patientInsKey`), fetchs parallèles (Promise.all), dédoublonné (Set — clés `@for` uniques), jeton de version anti-réponses tardives.
- **Case « Bloquer la réponse du patient »** (task-026) : visible `@if (hasPatientRecipient())`, auto-reset par effect quand plus de destinataire MES, transmise dans le payload.
- **Limite PJ** : `maxAttachmentSize` computed (settings > 0 sinon 10 Mo), jauge (`warning ≥ 0.8`, `danger ≥ 1`), blocage à l'ajout avec `runningTotal` local (FileReader async), message FR parité Angular, `reader.onerror`.
- **Simplify (`/forge-simplify`, commit `6eb8e0e`)** : `formatFileSize` extrait en `core/utils` (doublon avec `mail-attachment.formatSize`) ; `mss-address.util` (+3 tests) ; clé d'opposition en computed ; parallélisation opposition ; resolver défensif. Skips motivés : réécriture AlertController (DOD data-testid + pre-line + mécanisme testé — candidat d'harmonisation), parallélisation validate+fiche (fetch inutile si bloqué).
- **Code review (blocking corrigé, commit `df07810`)** : **course au double envoi** — send() sans garde anti-réentrance sur la chaîne asynchrone ; un double-tap pendant la validation INS pouvait envoyer 2× le même email médical (chemin fallback « validation indisponible »). Fix : `sendGuardActive` + try/finally + **test de réentrance** (Subject en vol, 2 taps → 1 `sendMail`). Durcissements : dédoublonnage warnings (NG0955), jeton de version, libération des dialogs sur close()/reset(), timer INS suivi, `maxAttachmentSizeBytes ≤ 0` → défaut, `reader.onerror`.
- **Tests** : +32 (303→335) — util rappel PJ (7 corps + objet + casse/accents + HTML + token `pj` + non-warn), service (validate-ins encodé, 404, getsettings), mss-address (3), compose (blocage INS, dialog identité confirm/cancel, API down → envoi, **réentrance double-tap**, rappel PJ 2 branches, visibilité case MES, auto-reset, bandeau opposition non bloquant + envoi possible, limite settings/défaut, blocage fichier, jauge). Total suite : **335/335** verts.
- **Build / lint** : `npm run build` ✓ 0 erreur ; `npm run lint` ✓ All files pass linting (baseline déjà propre).
- **Stitch** : écran `mail-compose` existant réutilisé (id 340f18be9395435f8fc472e0c476f736) — pas de nouvel écran, dialogs conformes aux patterns modaux « Clinical Precision ». Premier run du protocole corrigé (get_project/labels, pas de re-génération) : aucun incident.
- **Commits** : 2b3e3a0 (feat + tests), 6eb8e0e (simplify), df07810 (fix review).
- **Conformité** : identito-vigilance à l'envoi — **INS qualifiée exigée** pour adresser un patient MES (blocage sinon), confirmation d'identité explicite (DSR, parité web) ; opposition patient matérialisée au moment de l'envoi (bandeau) ; `X-MSS-MES: FIN` piloté par `blockPatientReply` (Référentiel socle MSSanté #2 §3.4.2.3 — ECO.2.2.8) ; **aucun trait/INS dans les logs client** (0 `console.*`) ni dans une route (INS en chemin d'API = contrat backend existant) ; envoi journalisé côté `api-mail` (PGSSI-S).

---

### v1.20 — task-137 — Rattachement email→patient par comparaison visuelle (2026-07-06)

- **PR** : [HealthPlatform.Mobile#41](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/41) — label `awaiting-human-merge`. Branche `feat/task-137-patient-attachment-mobile`. Repo `client-mobile` uniquement. **Frontend-only** : consomme `GET /api/v1/Patients/match` et `POST /api/v1/medical-documents/{documentId}/attach-patient` (déjà livrés pour client-angular task-012) ; aucun changement `api-mail`/DTO. Pas de dépendance.
- **`MssApiService`** : `matchPatientByTraits(lastName?, firstName?, birthDate?, gender?)` (HttpParams conditionnels, mêmes signatures qu'Angular `mss-api.service.ts:1252`) → `PatientMatchCandidateDto[]` ; `attachDocumentToPatient(documentId, patientId)` (body `AttachPatientRequestDto`, 204/404). DTOs déjà présents dans `patient.model.ts` (posés en task-095, activés ici).
- **`mss-patient-attachment-dialog`** (miroir Angular task-012, ré-ergonomie Ionic) : `ion-modal` inline (`[isOpen]`), inputs signaux `document`/`visible`, outputs `attached(patientId)`/`dismissed`. `effect` → chargement des candidats à l'ouverture (traits du `MailMedicalDocumentDto`), tri défensif score décroissant, score « NN% », libellés sexe via `getPatientGenderLabel` (cohérence patient-card/search). Erreurs (400 sans trait / 404 / réseau) → `extractProblemDetail` en toast danger + bloc inline **sans masquer la liste** (retry sans re-matching). **Aucune action de création de patient** ; un document à la fois.
- **`mail-detail`** : bandeau « Document non rattaché » quand `isPendingAttachment` (patientId null + ≥1 trait), un CTA par document (`Rattacher pour {NOM Prénom}` / fallback « Ouvrir la comparaison visuelle »), MAJ optimiste au succès : patch immutable `content.medicalDocuments[].patientId`, décrément `pendingIntegrationsCount` (copie locale + liste via `MailStateService.applyPatientAttachment`), toast succès — le bandeau disparaît sans rechargement.
- **Simplify (`/forge-simplify`)** : `pendingAttachmentDocs` mémoïsé sur la référence de `content` (getter filtrant évalué 4×/cycle CD) ; `MailStateService.applyPatientAttachment(uid)` en miroir d'`applyBiologyAck` (clamp ≥ 0, +test) ; labels sexe partagés (commit `640ac08`, +48/−7). Findings écartés : boucle sur HttpParams (style existant + parité Angular), suppression du tri défensif (garantit l'item DOD « triés par score décroissant »), élargissement `getPatientFullName` (hors périmètre de type), extraction ToastService (5 composants hors diff).
- **Code review (blocking corrigé, commit `e9439e5`)** : dismiss backdrop de l'`ion-modal` pendant un POST en vol → désync `visible`/modale (didDismiss avalé → bouton bandeau mort). Fix : `[backdropDismiss]="!isAttaching()"` + `onDidDismiss()` notifie **inconditionnellement** le parent ; l'erreur de rattachement n'efface plus la liste des candidats. Suggestions non bloquantes tracées : course « réponse tardive » sur `matchPatientByTraits` en réouverture rapide (héritée d'Angular task-012 — candidate au backport commun via `switchMap`) ; assertion spec « pas de Créer » aveugle au portal `ion-modal` (garde-fou couvert au niveau état + template).
- **Tests** : +23 (280→303) — `mss-api.service.spec` (params conditionnels/omis, 400 sans trait, POST body, 204, 404, erreur réseau) ; `patient-attachment-dialog.spec` (pas de chargement invisible, chargement traits, tri desc, rendu score %, état « Aucun candidat », toast erreur match, attached au succès, 404 → dialog ouverte + liste conservée, fallback réseau, dismissed, garde bouton pendant POST, didDismiss inconditionnel) ; `mail-detail.spec` (bandeau affiché/caché, libellé CTA, ouverture dialog, MAJ optimiste + disparition bandeau, annulation sans effet) ; `mail-state.service.spec` (décrément clampé). Total suite : **303/303** verts.
- **Build / lint** : `npm run build` ✓ 0 erreur (warnings budget SCSS pré-existants) ; `npm run lint` ✓ All files pass linting (0 fix — baseline déjà propre).
- **Stitch** : génération de l'écran `patient-attachment-dialog` en **timeout MCP (2×, best-effort non bloquant)** — implémentation sur la référence Angular task-012 + tokens « Clinical Precision » (`variables.scss`) ; écran `mail-detail` existant réutilisé pour le bandeau. Si des écrans générés apparaissent a posteriori dans le projet Stitch, vérifier titre/doublon dans l'UI (pas de rename MCP).
- **Commits** : a70d49d (feature + tests), 640ac08 (simplify), e9439e5 (fix review).
- **Conformité** : traits issus d'un CDA à INS **non qualifiée** ; rattachement à un patient **existant** uniquement (aucune création, aucune récupération INSi) ; **aucun trait patient** (INS/NIR/nom/date de naissance) dans les logs client (0 `console.*`) ni dans une route mobile (traits en query GET côté API = contrat backend existant, identique à client-angular) ; action de rattachement journalisée côté `api-mail` (type d'audit existant) ; erreurs `ProblemDetails` sans fuite ; cascade Corbeille → suppression du lien patient inchangée (reconstruit à la restauration).

---

### v1.19 — task-136 — Connexion CIBA e-CPS (RPPS + validation découplée) (2026-06-29)

- **PR** : [HealthPlatform.Mobile#39](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/39) — label `awaiting-human-merge`. Branche `feat/task-136-mobile-ciba-ecps-login`. Repo `client-mobile` uniquement (`**Single frontend**: true`). **Frontend-only** : l'endpoint proxy `POST /v1/auth/connect` est **déjà livré** (repos `psc-proxy-*` gérés manuellement, hors automation) ; aucun changement `api-mail`/DTO. Pas de dépendance.
- **`AuthService.connectCiba(rpps)`** : génère le binding message, valide le RPPS côté client (aucun appel réseau si invalide → `RppsValidationError`), `POST /auth/connect` `{ nationalId, bindingMessage, clientId: environment.authClientId, channel: 'MOBILE' }` en `withCredentials` (requête longue — polling serveur ≈ 2 min), puis `switchMap` → récupération du `TokenAggregate` via le cookie de session BFF et `tap` → mémorisation du RPPS. Retourne `CibaConnectHandle { bindingMessage, session$ }` (binding exposé **synchroniquement** pour l'affichage pendant l'attente).
- **`ciba.util.ts`** (helpers purs) : `CIBA_CHANNEL='MOBILE'`, `RPPS_REGEX=/^8\d{11}$/`, `RppsValidationError`, `isValidRpps`, `formatBindingMessage`/`generateBindingMessage` (bornes 00–99, normalisation modulo), `mapCibaError` (status → FR : 0 injoignable / 400 invalide / 404 inconnu / 408·504 timeout-non-validé / 409 déjà en cours / 503 IdP indisponible / défaut générique ; **ne réexpose jamais `detail`/`title`**).
- **`login.page`** : machine d'états `form`/`waiting`. Vue `form` = champ RPPS (pré-rempli via `authService.lastRpps`, modifiable) + bouton **principal** « Se connecter avec e-CPS » + lien **secondaire** « Autre moyen de connexion » (→ `loginPsc`). Vue `waiting` = binding code en grand + spinner + bouton **Annuler** (`unsubscribe` → interrompt le polling, retour `form`). `data-testid` sur tous les interactifs ; libellés FR en dur ; `FormsModule` ajouté au `LoginPageModule` (ngModel). Pré-remplissage RPPS persistant (`mobile_last_rpps` localStorage).
- **Réutilisation / altitude** : RPPS jamais loggé ni en URL (corps du POST uniquement). Mutualisation du pipeline `/auth/token`→session entre `refreshSession` et la connexion CIBA.
- **Simplify (`/forge-simplify`)** : extraction de `mintSessionFromCookie(mssApiUrl, emptyTokenError)` (réutilisé par `refreshSession` + connexion CIBA, axe reuse/altitude) ; suppression de l'état `submitting` write-only (la vue `form`/`waiting` pilote l'UI) ; fusion des règles SCSS dupliquées `.login-error`/`.session-expired` (commit `36aa64e`, −57/+27). Findings écartés : refactor `authentication.page`/`$exchangeCodeForToken` (hors diff) ; déplacement persistance RPPS vers `AuthSessionService` (ripple hors diff, nit marginal) ; suppression `formatBindingMessage` (gagne ses tests de bornes 00–99 exigés par la DOD) ; branche défensive `RppsValidationError` côté page (fallback bon marché).
- **Tests** : +18 → **263/263** verts. `ciba.util.spec` (bornes binding 00/05/99/overflow, `generateBindingMessage` toujours 2 chiffres + bornes via spy `Math.random`, `isValidRpps` valide/non-8/longueur/non-numérique/trim, `mapCibaError` par status + non-fuite) ; `auth.service.spec` connectCiba (succès e2e POST connect MOBILE→token cookie, RPPS invalide **sans réseau**, timeout 408, IdP 503, conflit 409, prefill) ; `login.page.spec` (prefill, RPPS invalide sans appel, succès→`/home`, mapping erreur→`form`, Annuler, lien secondaire PSC).
- **Build / lint** : `npm run build` ✓ 0 erreur (warning budget `login.page.scss` non bloquant, cohérent avec d'autres composants) ; `npm run lint` ✓ All files pass linting (0 fix nécessaire).
- **Stitch** : écran de référence `login` réutilisé + design system « Clinical Precision » ; génération d'un écran dédié `login-ecps` en timeout MCP (best-effort, non bloquant) — intention traduite en Ionic depuis la référence existante.
- **Commits** : 1da9212 (feature CIBA + tests), 36aa64e (simplify).
- **Conformité** : authentification PS via **e-CPS / CIBA** (canal `MOBILE`, validation découplée, eIDAS substantiel — Ségur V2 / PGSSI-S) ; `clientId` restreint à l'allowlist proxy ; **aucun RPPS en clair** (logs/URL/messages) ; erreurs `ProblemDetails` mappées en FR sans fuite ; journalisation probante longue durée assurée côté proxy/IdP. INS/contenu patient non applicables (authentification professionnelle).

---

### v1.18 — task-135 — Vue patient : synthèse clinique & antécédents (2026-06-29)

- **PR** : [HealthPlatform.Mobile#38](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/38) — label `awaiting-human-merge`. Branche `feat/task-135-mobile-clinical-synthesis`. Repo `client-mobile` uniquement. **Frontend-only** : les `MailMedicalDocumentSummaryDto` sont déjà fournis structurés (agrégés depuis les documents chargés en task-133), aucun changement `api-mail`/DTO. Dépend de task-133. **4/4 — clôt le portage de la vue patient mobile.**
- **`mss-clinical-synthesis`** (miroir fidèle de client-angular `ClinicalSynthesisComponent`) : `@Input` setter→signal (`summaryItems`, `ipsDocumentsCount`, `ipsLastUpdate`). Catégorisation par `sectionType` portée fidèlement via `filter(sectionTypes)` (Set lowercase) : `allergies` (Allergy/AllergyIntolerance), `mainCard` (allergies), `priorityCards` (ActiveProblem/Condition/Problem + Medication/MedicationStatement), `secondaryCards` (MedicalHistory/SurgicalHistory/PastIllness, Immunization/Vaccination, LifestyleFactor/SocialHistory, FamilyHistory) — cartes vides filtrées. Détection de criticité `isCritical` via `CRITICAL_SEVERITY_KEYWORDS` (severe/critical/high/grave/sévère/critique) → `criticalAllergies` + bannière. `ipsBanner` (compteur documents IPS), `severityClass` (danger/warning/info/neutral), `formatItemMeta` (dosage/fréquence/voie/dates onset-abatement/statut), `itemDisplayName` (fallback displayName→originalText→code), `formatDateFr`.
- **`mss-medical-history`** (miroir fidèle de client-angular `MedicalHistoryComponent`) : `@Input` setter→signal (`summaryItems`). `groupedItems` (regroupement par `sectionType`, tri `SECTION_ORDER` ActiveProblem→LifestyleFactor), `SECTION_LABELS`/`SECTION_ICONS` (icônes design-system desktop → ionicons), `getStatusClass`/`getSeverityClass` (heuristiques FR/EN), `isMedication`/`hasDosage`/`isFamilyHistory`, `formatDate`. **Sections repliables** via `ion-accordion-group` (mode `single` → une seule ouverte à la fois) ; `selectedSection` signal + `toggleSection`/`onAccordionChange`.
- **Ré-ergonomie mobile** : grille asymétrique multi-colonnes desktop → **empilement d'`ion-card`** (bannière critique + carte allergies + cartes prioritaires/secondaires colorées par sévérité via tokens `--app-*` + couleurs cliniques) ; détail antécédents → **accordéon Ionic**. Libellés FR en dur.
- **`mss-patient-timeline`** : onglet **Synthèse** câblé conditionnellement — `allSummaryItems` (agrégation des `summaryItems` des documents), `dynamicTabs` (Documents toujours ; Biologie si résultats ; Synthèse si éléments de synthèse), `ion-segment` Documents/Biologie/Synthèse ; l'onglet rend `mss-clinical-synthesis` + `mss-medical-history`.
- **Réutilisation (non duplication)** : `mss-medical-document-modal` réutilise `mss-clinical-synthesis` pour la **vue structurée de synthèse** — `structuredKind` retourne `'synthesis'` (prioritaire sur html/raw) quand le document porte des `summaryItems` ; nouveau `@case ('synthesis')` rendant le composant. Pas de duplication de la logique de synthèse.
- **Simplify (`/forge-simplify`)** : `otherCards` computed (`[...priorityCards, ...secondaryCards]`) → une seule boucle `@for` au lieu de deux blocs de markup byte-identiques (commit `6bc2337`, −31/+9 lignes, iso-rendu). Findings écartés : extraction d'utils date/section partagés (formatDateFr/formatDate/SECTION_* — casse l'auto-suffisance/parité du miroir Angular, même arbitrage que task-134) ; fusion de la carte allergies dans la boucle commune (divergence réelle : branche empty-message + classe `--critical` par item).
- **Tests** : +18 (213→231) — `mss-clinical-synthesis` (catégorisation par carte, cartes vides écartées, criticité + mots-clés sévérité, classes de sévérité, `formatItemMeta`, fallback nom, bannière IPS, état vide) ; `mss-medical-history` (regroupement/ordre, toggle accordéon, sync ionChange, labels/icônes, classes statut/sévérité, médication+dosage / parenté familiale, `formatDate` + fallback nom, classe item allergie/problème) ; `mss-patient-timeline` (onglet Synthèse affiché si éléments / `selectTab`) ; `mss-medical-document-modal` (vue `synthesis` prioritaire sur html). Total suite : **231/231** verts.
- **Build / lint** : `npm run build` ✓ 0 erreur ; `npm run lint` ✓ All files pass linting.
- **Commits** : 27389a1 (synthèse + antécédents + tests), 6bc2337 (simplify).
- **Conformité** : éléments de synthèse issus de **CDA (VSM / synthèses)** parsés en amont (`api-mail`/`interop-cda`) — le mobile **ne parse aucun CDA**, il affiche le `MailMedicalDocumentSummaryDto` structuré ; sections/codes (SNOMED CT/CIM-10) **affichés tels quels** ; **aucune donnée de synthèse ni INS loggée** côté client ; consultation tracée backend (PGSSI-S) ; auth PSC/e-CPS inchangée.

---

### v1.17 — task-134 — Vue patient : timeline biologie matricielle (2026-06-28)

- **PR** : [HealthPlatform.Mobile#37](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/37) — label `awaiting-human-merge`. Branche `feat/task-134-mobile-biology-timeline`. Repo `client-mobile` uniquement. **Frontend-only** : les `MailMedicalDocumentBiologyDto` sont déjà fournis structurés (agrégés depuis les documents chargés en task-133). Dépend de task-133. 3/4 de la vue patient.
- **`mss-biology-timeline`** (miroir fidèle de client-angular `BiologyTimelineComponent`, lui-même portage de Blazor `BiologyTimeline.razor`) : grille matricielle biomarqueurs (lignes, groupés par section ordonnée `SECTION_ORDER`) × dates (colonnes). **Calculs portés fidèlement** : `buildGridModel` (parse dates/valeurs `parseNumeric` rejetant `<>≤≥`, groupement code|nom, tri desc), `getTrend` (delta vs valeur précédente relatif à l'amplitude de référence → flèche/angle/couleur), `getStability` (≥3 valeurs → Stable/En hausse/En baisse), `buildSparkline` (SVG : segments + points + bande de référence, scaleX/scaleY), `getInterpretationClass` (N/L/H/LL/HH), `getTooltip`. Toolbar : filtre biomarqueur, bascule `showAbnormalOnly`, sélecteur de période (`BiologyPeriod` 3/6/12/0) avec **auto-sélection** selon l'étendue des données.
- **Ré-ergonomie mobile** (point délicat de la task) : `@Input` setter→signal (`biologyResults`), grille en **scroll horizontal** (`overflow-x:auto`) avec **colonne biomarqueur figée** (`position:sticky; left:0`), toolbar Ionic (`ion-searchbar` filtre, `ion-segment` période, bouton « Anormaux »), sparklines SVG conservées, variables CSS de couleur biologie (`--bio-color-*`). Libellés FR en dur.
- **`mss-patient-timeline`** : onglet **Biologie** câblé conditionnellement — `allBiologyResults` (agrégation des `biologyResults` des documents), `dynamicTabs` (Documents toujours ; Biologie si résultats), `activeTab`/`selectTab`, `ion-segment` Documents/Biologie affiché quand >1 onglet.
- **Simplify (`/forge-simplify`)** : `visibleDateSet` computed (le `Set` était reconstruit dans 5 méthodes/cycle CD) ; `getTrend` en `.find` sur tableau trié desc (au lieu de filter+sort) ; `getEntryForDate` en O(1) via Map `entriesByDate` par ligne ; helper `countAbnormalInRows` (commit `e64fe18`). Findings écartés : conversion setter→`effect()` (suggestion incorrecte — `effect()` ne trace pas un `@Input` non-signal) ; extraction d'utils date/biologie partagés (touche task-098/mail-header, casse l'auto-suffisance du miroir) ; constante `BIO_COLORS` (cosmétique).
- **Tests** : +12 (201→213) — `mss-biology-timeline` (classes d'interprétation, `formatRef`, build/ordre des sections, filtre nom, anormaux-uniquement, filtrage période, tendance baissière, stabilité Stable, modèle sparkline, toggle sparkline) ; `mss-patient-timeline` (onglet Biologie affiché si résultats / masqué sinon, `selectTab`). Total suite : **213/213** verts.
- **Build / lint** : `npm run build` ✓ 0 erreur ; `npm run lint` ✓ All files pass linting.
- **Commits** : 0c78742 (timeline biologie), e64fe18 (simplify).
- **Conformité** : résultats de biologie issus de **CDA CR-BIO** parsés en amont (`api-mail`/`interop-cda`) — le mobile **ne parse aucun CDA**, il affiche le `MailMedicalDocumentBiologyDto` structuré ; codes LOINC + interprétation HL7 (N/L/H/LL/HH) **affichés tels quels** ; **aucune valeur biologique ni INS loggée** côté client ; consultation tracée backend (PGSSI-S) ; auth PSC/e-CPS inchangée.

---

### v1.16 — task-133 — Vue patient : timeline documents médicaux + viewer (2026-06-28)

- **PR** : [HealthPlatform.Mobile#36](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/36) — label `awaiting-human-merge`. Branche `feat/task-133-mobile-patient-timeline`. Repo `client-mobile` uniquement. **Frontend-only** : endpoints déjà en production (`GET /api/v1/Patients/ins/{ins}/medical-documents` paginé, `getEmailContent`, `downloadAttachment`). Dépend de task-132 (socle). 2/4 de la vue patient.
- **`mss-api.getMailsByInsPaged(ins, page, pageSize)`** → `GET /api/v1/Patients/ins/{ins}/medical-documents?page=&pageSize=` → `PagedResultDto<MailDto>` (INS encodé). `getEmailContent` + `downloadAttachment` **réutilisés** (déjà présents, reuse before create).
- **`mss-patient-timeline`** (conteneur, miroir Angular) : `@Input patientIns` (charge sur changement, garde `lastLoadedIns`) ; pagination 10/page (`loadDocuments`/`loadMore` + `ion-infinite-scroll`) ; `mailIndex` (document→mail pour le PDF) ; computeds `allDocuments`/`filteredDocuments`/`documentGroups` (groupage par période, tri desc) ; `typeCounts`/`filterOptions` (chips de filtre, types présents seulement) ; `classifyDocument` (heuristiques catégorie/LOINC/titre, miroir Angular) **mise en cache** dans un computed Map (évite le double calcul typeCounts+matchesFilter) ; `loadMailsContent` via `forkJoin` (contenu des mails en parallèle). Seul l'onglet **Documents** est câblé (Biologie task-134, Synthèse task-135).
- **`mss-timeline-document-group`** : liste de documents sous un libellé de période, repliable (groupe + par document) ; icône/libellé de catégorie, badge version CDA (≠ « 1 »), praticien, badge « Biologie », bouton d'ouverture ; aperçu du corps `[innerHTML]` **assaini par Angular** (pas de bypass).
- **`mss-timeline-period-separator`** : séparateur de période (template inline).
- **`mss-medical-document-modal`** : `ion-modal` plein écran, `@Input document/visible/folderPath/mailUid`, `ngOnChanges` + garde `loadedPdfKey` ; **PDF** récupéré en blob (`downloadAttachment`), rendu en `<iframe>` via `bypassSecurityTrustResourceUrl` (sur notre propre blob), **Object URL révoqué** à la fermeture/au masquage/au `ngOnDestroy`/après téléchargement ; vue structurée HTML assaini (`[innerHTML]`) / texte brut / aucun. Téléchargement via l'util partagé `downloadBlob`. Biologie/synthèse détaillées = task-134/135.
- **Réutilisation (`/forge-simplify`)** : util `downloadBlob` extrait dans `core/utils/blob-download.util.ts` (dédup du `triggerDownload` du modal **et** du `mail-attachment` existant) ; `classifyDocument` mise en cache (commit `4728af6`). Findings écartés : conversion en signal-inputs+effect (convention mobile = `@Input`/`ngOnChanges`), extraction helpers blob-URL/date (large, pré-existant), `typeLabels` au modèle (consommateur unique), factorisation `loadDocuments`/`loadMore` (différences sémantiques).
- **Câblage** : `mss-patient-timeline` ajouté sous la fiche dans `mss-patient`.
- **Tests** : +15 (186→201) — `mss-api` (params page/pageSize) ; `patient-timeline` (groupement par période, filtre par type + filterOptions, pagination page 2, ouverture/fermeture du modal) ; `medical-document-modal` (vue structurée html/raw/none, fetch PDF + URL sûre, révocation du blob à la fermeture/au masquage) ; `timeline-document-group` (toggles, émission open, badge version, catégorie). Total suite : **201/201** verts.
- **Build / lint** : `npm run build` ✓ 0 erreur ; `npm run lint` ✓ All files pass linting.
- **Commits** : 8da8323 (timeline + viewer), 4728af6 (simplify).
- **Conformité** : documents = CDA parsés **côté `api-mail`/`interop-cda`** (le mobile ne parse aucun CDA) ; HTML de document **assaini** avant rendu (`[innerHTML]` Angular) ; **PDF en blob mémoire, Object URL révoqué** (pas de persistance disque non maîtrisée) ; INS clé d'appel API over HTTPS, **jamais loggée ni en route** ; consultation tracée côté backend (PGSSI-S) ; auth PSC/e-CPS inchangée.

---

### v1.15 — task-132 — Vue patient : socle recherche + fiche + opposition (2026-06-28)

- **PR** : [HealthPlatform.Mobile#35](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/35) — label `awaiting-human-merge`. Branche `feat/task-132-mobile-patient-socle`. Repo `client-mobile` uniquement. **Frontend-only** : endpoints `/api/v1/Patients/...` déjà en production (consommés par `client-angular`), aucun changement `api-mail`/DTO. 1/4 du portage de la vue patient.
- **`MssApiService`** : `getPatientsWithDocsToday()`, `getPatientByIns(ins)`, `searchPatients(lastName)`, `getPatientOpposition(ins)`, `updatePatientOpposition(ins, dto)` (endpoints `/api/v1/Patients/...`, INS encodé, `HttpParams` pour `lastName`). DTOs patient déjà présents dans `core/models/patient.model.ts`.
- **`mss-patient`** (`features/patient/`, conteneur, miroir Angular) : tant qu'aucun patient n'est sélectionné → recherche ; sinon → fiche. État (`selectedPatient`) tenu par **`PatientStateService`** (signal), **jamais dans l'URL** (le deep-link `?ins=` d'Angular est volontairement omis — garde-fou INS mobile).
- **`mss-patient-search`** : `ion-searchbar` + flux RxJS `Subject` `debounceTime(300)`/`distinctUntilChanged`/`switchMap` (saisie vide → docs du jour, sinon `searchPatients`) ; chargement initial des patients du jour ; liste `ion-item` (avatar initiales, nom, âge, sexe, INS) ; émet `patientSelected`.
- **`mss-patient-card`** : fiche démographique (`getPatientFullName`/`getPatientAge`/`getPatientGenderLabel`/`getPatientInitials` réutilisés) + bandeau de statut d'opposition ; **réutilise `mss-patient-consent`** pour l'édition (pas de duplication de la logique load/save, contrairement à Angular qui la dupliquait dans la carte).
- **`mss-patient-consent`** : charge l'opposition par INS (`ngOnChanges`, garde `lastLoadedIns`), deux `ion-toggle`, persiste chaque changement par le **`PUT` opposition** (canal unique tracé serveur), toast succès/erreur (`extractProblemDetail`), émet `oppositionChanged`. `takeUntilDestroyed` sur les souscriptions.
- **Onglet Patients** : `patients.page` passe d'écran placeholder à hôte mince projetant `mss-patient` (`PatientsPageModule` importe le composant standalone).
- **Helpers partagés** ajoutés à `patient.model.ts` : `getPatientGenderLabel`, `getPatientInitials` (dédup search/card, rejoignent `getPatientFullName`/`getPatientAge`).
- **Tests** : +28 (158→186) — `mss-api` (5 méthodes patient + propagation d'erreur) ; `PatientStateService` (sélection/clear/reset) ; `patient-search` (chargement initial, recherche debouncée `fakeAsync`, fallback docs-du-jour, sélection, helpers) ; `patient-card` (démographie, libellé sexe, bandeau opposition, close) ; `patient-consent` (load + emit, garde re-load, save PUT + toast, RAZ date, toast d'erreur). Total suite : **186/186** verts.
- **Build / lint** : `npm run build` ✓ 0 erreur ; `npm run lint` ✓ All files pass linting.
- **Simplify (`/forge-simplify`)** : extraction `getPatientGenderLabel`/`getPatientInitials` (reuse), helper `setResults()` dans patient-search, `takeUntilDestroyed` ajouté à patient-consent (commit `fced432`). Findings écartés : suppression de `reset()` (diverge dès task-133), fusion des handlers clear (outputs distincts), routage du clear via le subject (debounce indésirable), remontée de l'opposition dans le state (spéculatif).
- **Commits** : 430b8b9 (socle + tests), fced432 (simplify).
- **Conformité** : données patient = DSCP servies par l'`api-mail` (HDS), transit HTTPS, pas de persistance disque mobile ; **INS jamais loggée ni en route mobile** (sélection en state) ; opposition (mécanisme d'opposition du patient) modifiée uniquement via le `PUT` tracé serveur ; auth PSC/e-CPS inchangée ; consultation/modification tracées côté backend (PGSSI-S). Hors socle : timeline documents (task-133), biologie (task-134), synthèse clinique (task-135).

---

### v1.14 — task-131 — Synthèse IA d'un email (panneau détail) (2026-06-28)

- **PR** : [HealthPlatform.Mobile#34](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/34) — label `awaiting-human-merge`. Branche `feat/task-131-mobile-ai-email-summary`. Repo `client-mobile` uniquement. **Frontend-only** : endpoint backend déjà en production (consommé par `client-angular`), aucun changement `api-mail`/DTO.
- **`mss-api.getEmailSummary(folderPath, uid)`** → `GET /api/v1/mail/folders/{folder}/emails/summary/{uid}` → `MailSummaryDto` (`uid`, `folderPath`, `from`, `markdownSummary`). Nouveau modèle `core/models/mail-summary.model.ts` (miroir TS du `MailSummaryDto` C#).
- **`mss-mail-summary`** (`features/mail/components/mail-summary/`, miroir du composant Angular) : `@Input` `mail` + `content` (l'identité patient vient de `content.medicalDocuments[0]`, le contenu étant chargé séparément côté mobile, ≠ Angular où il est porté par `mail.content`). Signaux `isLoading`/`summary`/`error`/`notAvailable` ; chargement sur changement d'`uid` (garde `lastLoadedUid`) ; `retry()`. En-tête : `displayTitle` (titre doc médical sinon sujet), `patientDisplay` (réutilise le helper `getPatientAge`), `practitionerDisplay`, `senderDisplay`. Corps : `markdownToHtml` (échappement `&`/`<`/`>` **avant** substitution markdown → anti-XSS) puis `DomSanitizer.bypassSecurityTrustHtml`.
- **Cas 404** (`ProblemDetails` « AI summary is not available », pipeline IA désactivé) → état neutre `notAvailable` (« Synthèse IA non disponible »), **pas** d'alerte d'échec. Autres erreurs → message via `extractProblemDetail` + bouton « Réessayer ».
- **`mss-mail-detail`** : déclencheur « Synthèse IA » (icône `sparkles-outline`, `data-testid="detail-summary-toggle"`) + panneau repliable (`showSummary`/`toggleSummary`) rendu via `@if`. `data-testid` : `detail-summary-toggle`, `detail-summary-panel`, `summary-content`/`summary-loading`/`summary-unavailable`/`summary-error`/`summary-retry`.
- **Tests** : 12 nouveaux — `mss-api` (GET summary endpoint encodé ; propagation 404) ; `mail-summary` (succès, 404→neutre, erreur non-404, rechargement sur uid, retry, fallback titre, patient/praticien, échappement markdown anti-XSS). Total suite : **162/162** verts.
- **Build / lint** : `npm run build` ✓ 0 erreur ; `npm run lint` ✓ All files pass linting.
- **Simplify (`/forge-simplify`)** : réutilisation du helper existant `getPatientAge` au lieu d'un `calculateAge` privé dupliqué (commit `8f4314d`). Findings écartés : retrait du `DatePipe` (faux positif — pipe `| date` utilisé dans le template), extraction du 404 vers le service / de `markdownToHtml` en util (design spéculatif, consommateur unique).
- **Commits** : 8a37dcb (feature + tests), 8f4314d (simplify).
- **Conformité** : synthèse = donnée de santé produite/hébergée par l'`api-mail` (HDS) ; transit HTTPS, pas de persistance disque mobile ; **aucune donnée de santé loggée** côté client (synthèse, patient, INS) ; consultation tracée côté backend (PGSSI-S) ; auth PSC/e-CPS inchangée. Markdown IA assaini avant rendu (anti-XSS).

---

### v1.13 — task-108 — Vue Conversations (threads) (2026-06-19)

- **PR** : [HealthPlatform.Mobile#13](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/13) — label `awaiting-human-merge`. Branche `feat/task-108-mobile-conversation-threads`. Repo `client-mobile` uniquement. Clôt le batch issu de l'analyse différentielle angular↔mobile.
- **`mss-api.getThread(messageId)`** → `GET /api/v1/mail/thread/{messageId}` → `MailThreadInfoDto`.
- **`mail-state`** : `MailViewMode` (List/Conversation) ; `conversationList` (computed : en Conversation, racines uniquement = `isThreadRoot` ou mails hors fil) ; `expandedThreadId` + `threadChildren` ; `expandThread`/`collapseThread`/`isThreadExpanded` ; `setMailViewMode` replie le fil ouvert.
- **`mss-mail-header`** : inputs `threadCount`/`isExpanded`/`isThreadChild`, output `toggleThread` ; chip « N messages » + chevron sur une racine à plusieurs messages (mode Conversation) ; indentation des enfants.
- **`mss-mail-list`** : rend `conversationList` ; en Conversation, dépliage d'une racine affiche ses enfants (`getThread` à la demande, pas de reload au repliage) ; enfants ouverts via `MailEventService.requestSelectByUid$` (→ navigation détail par uid+dossier).
- **Inbox** : segment **Liste / Conversation** (`onViewModeChange`) ; abonnement `requestSelectByUid$` → navigation `/mail/{folder}/{uid}`.
- **Tests** : 6 nouveaux — `mss-api.getThread` (GET messageId encodé) ; `mail-state` (conversationList roots, expand/collapse + children, changement de mode replie) ; `mss-mail-header` (chip/chevron sur racine multi-messages, émission `toggleThread`). Total suite : **106/106** verts.
- **Build / lint** : `npm run build` ✓, `npm run lint` ✓ clean.
- **Commit** : a707509.
- **Conformité** : regroupement par en-têtes RFC-5322 (In-Reply-To/References) ; aucune donnée de santé en clair.

---

### v1.12 — task-107 — Notifications nouveaux mails (SSE in-app) (2026-06-19)

- **PR** : [HealthPlatform.Mobile#12](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/12) — label `awaiting-human-merge`. Branche `feat/task-107-mobile-new-mail-notifications`. Repo `client-mobile` uniquement. Issu de l'analyse différentielle.
- **Périmètre** : notification **in-app** (parité angular `NotificationStreamService`). Les **push natives Capacitor** (FCM/APNs + enregistrement device backend + `devops`) sont un **suivi infra hors US**.
- **`NotificationStreamService`** : `EventSource` `…/api/v1/mail/notifications/stream?token=` **scope-utilisateur** (distinct du folder-scoped de task-104), `connect`/`disconnect`, flux `notification$`, ré-entrée `NgZone`, **connexion unique** (anti même-URL), fermeture au `ngOnDestroy`, reconnexion native sur coupure. Lit token/baseURL depuis `AuthSessionService`.
- **Modèle** : `NotificationPayloadDto` (`NotificationKind` NewMail/AbnormalBiology, `UrgencyLevel`, title/body/mailUid/folderPath/receivedAt/playSound/showDesktop).
- **Inbox** : `connect()` à l'entrée ; **toast** à chaque notification (rouge si biologie anormale) ; sur un `NewMail` du **dossier courant** (hors recherche), `getEmails([mailUid])` + `appendEmails` (dédup + re-tri récent en tête, sans saut de scroll) ; `disconnect()` au destroy.
- **Tests** : 4 nouveaux — `NotificationStreamService` (URL+token, parsing `notification`, connexion unique, close au disconnect) via `FakeEventSource`. Total suite : **100/100** verts.
- **Build / lint** : `npm run build` ✓, `npm run lint` ✓ clean.
- **Commit** : 685cfda.
- **Conformité** : stream authentifié (JWT en `?token=`, jamais loggé) ; aucune donnée de santé dans le toast/les logs.

---

### v1.11 — task-106 — Recherche d'emails (2026-06-19)

- **PR** : [HealthPlatform.Mobile#11](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/11) — label `awaiting-human-merge`. Branche `feat/task-106-mobile-email-search`. Repo `client-mobile` uniquement. Issu de l'analyse différentielle.
- **`mss-api.semanticSearch(request)`** → `POST /api/v1/search/semantic` → `SearchResponseDto` (uids). Modèles `SearchRequestDto`/`SearchResponseDto`/`SearchFilterDto` (miroir).
- **`mss-mail-search`** : `ion-searchbar` + chips de filtres rapides (Non lus, Pièces jointes, Document médical, Biologie), **debounce 300ms** ; émet `searchResults` (uids) / `searchCleared` / `searchFailed`. Requête : `maxResults 50`, `minSimilarity 0.1`, `searchType/searchMode 3`, `folderPath` courant (parité angular).
- **Inbox** : héberge la recherche ; charge les uids résultats dans la liste en **mode recherche** qui suspend la pagination scroll (`mail-state.isSearchActive` → `hasMore` faux) ; `searchCleared` restaure la vue dossier paginée ; `searchFailed` → bandeau d'erreur.
- **Tests** : 6 nouveaux — `mss-api.semanticSearch` (POST endpoint) ; `mss-mail-search` (recherche debouncée + émission uids, filtres dans la requête, `searchCleared` sur critères vides, `clear()`) ; `mail-state` (pagination suspendue si recherche active). Total suite : **96/96** verts.
- **Build / lint** : `npm run build` ✓, `npm run lint` ✓ clean.
- **Commit** : 3385011.
- **Conformité** : la requête de recherche **n'est jamais loggée** (peut contenir un nom/identité patient) ; recherche scope-utilisateur ; aucun INS en clair.

---

### v1.10 — task-105 — Accusé de lecture : réponse sur consentement (2026-06-19)

- **PR** : [HealthPlatform.Mobile#10](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/10) — label `awaiting-human-merge`. Branche `feat/task-105-mobile-read-receipt-response`. Repo `client-mobile` uniquement. Issu de l'analyse différentielle angular↔mobile.
- **`mss-api.sendReadReceipt(folder, uid)`** → `POST /api/v1/mail/folders/{folder}/emails/{uid}/sendreadreceipt`.
- **`mss-mail-detail`** : getter `showReadReceiptPrompt` (mail reçu avec `requestReadReceipt`, hors « Envoyés » et brouillon, non déjà acquitté dans la session) ; bandeau + bouton « Envoyer l'accusé » ; `sendReadReceipt()` émet **uniquement sur action du PS** (consentement), toast au succès, `ProblemDetails` à l'échec, idempotent via un `Set<uid>` de session.
- **Tests** : 3 nouveaux — `mss-api.sendReadReceipt` (POST endpoint) ; `mss-mail-detail` (prompt visible seulement sur mail reçu demandeur / masqué sur sent/draft/sans-demande ; envoi → POST + masquage). Total suite : **90/90** verts.
- **Build / lint** : `npm run build` ✓, `npm run lint` ✓ clean.
- **Commit** : 571a876.
- **Conformité** : accusé MSSanté émis sur consentement explicite (jamais auto) ; imputé au PS authentifié (PSC) ; émission tracée backend (PGSSI-S) ; aucun RPPS dans les en-têtes ; aucune donnée de santé en clair.

---

### v1.9 — task-104 — Enrichissement + mises à jour live SSE (2026-06-19)

- **PR** : [HealthPlatform.Mobile#9](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/9) — label `awaiting-human-merge`. Branche `feat/task-104-mobile-enrichment-sse-parity`. Repo `client-mobile` uniquement. Dépend de task-100, task-102.
- **`mss-api.enrichEmailsSync(folder, uids)`** → `POST /api/v1/mail/folders/{folder}/emails/enrich/sync` (body = UIDs, `responseType: 'text'` → void).
- **`MailEventsStreamService`** (core, parité Angular) : `EventSource` folder-scoped vers `…/api/v1/mail/events/stream?folder=&token=` (JWT en query, EventSource ne pose pas d'en-tête) ; `connect`/`disconnect`/`setFolder` ; flux `emailsEnriched$` / `tagsUpdated$` ; ré-entrée `NgZone` (callbacks hors zone) ; **reconnexion** au changement de dossier, **anti double-connexion** (même URL ignorée), `close()` au `ngOnDestroy`. Lit le token/baseURL depuis `AuthSessionService`.
- **Modèle** : `core/models/mail-event.model.ts` (`EmailsEnrichedEvent` {folder, emails[]}, `TagsUpdatedEvent` {folder, uid, tags[]}).
- **`inbox.page`** : enrichit les UIDs de chaque lot chargé ; `setFolder`+`connect` du stream sur le dossier courant ; **patch in-place** de la liste sur `EmailsEnriched` (`updateMailInList` par uid, garde sur le dossier) et `TagsUpdated` ; `stream.disconnect()` au destroy.
- **`mail-detail.page`** : si le mail ouvert est inclus dans un `EmailsEnriched` (même dossier+uid), recharge son contenu (`getEmailContent`) sans navigation.
- **Tests** : 6 nouveaux — `MailEventsStreamService` (URL folder-scoped + token, parsing `EmailsEnriched`/`TagsUpdated`, reconnexion au changement de dossier, pas de réouverture même dossier, close au disconnect) via un `FakeEventSource` ; `mss-api.enrichEmailsSync` (POST body UIDs, responseType text). Total suite : **87/87** verts.
- **Build / lint** : `npm run build` ✓, `npm run lint` ✓ clean.
- **Commit** : ff624ca.
- **Conformité** : flux SSE authentifié (JWT en `?token=`, jamais loggé) ; identité récupérée serveur-side ; aucune donnée de santé en clair.

---

### v1.8 — task-103 — Pagination inbox orientée scroll (2026-06-19)

- **PR** : [HealthPlatform.Mobile#8](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/8) — label `awaiting-human-merge`. Branche `feat/task-103-mobile-inbox-pagination-scroll`. Repo `client-mobile` uniquement.
- **Étude** : `getFolder` renvoie déjà **tous** les UIDs du dossier → pagination **côté client** sur la liste triée desc, **sans évolution backend**. UX retenue : infinite scroll + fin-de-liste + retry. Lot = 30.
- **`mail-state`** : `pagedUids` + `pageCursor` (privés), `PAGE_SIZE=30`, `hasMore` (computed), `isLoadingMore` ; `startPaging(sortedUids)` (RAZ emails+curseur), `nextUidPage()` (lot suivant + avance), `appendEmails(mails)` (dédup par `uid`), `rewindPage(count)` (rollback du curseur sur échec).
- **`inbox.page`** : `loadEmailsForFolder` charge tous les UIDs triés → `startPaging` → 1er lot ; `loadNextPage()` (append, garde `isLoadingMore`, rollback `rewindPage` sur erreur) ; `ion-infinite-scroll [disabled]="!hasMore()"` (anti-double-trigger) ; état « Fin de la liste » ; bandeau d'erreur + **bouton Réessayer** (rejoue le même lot, pas de saut/doublon).
- **Tests** : 4 nouveaux (mail-state) — pagination par lots + fin de liste, append+dédup, **rollback erreur→retry refetch le même lot**, `startPaging` réinitialise. Total suite : **81/81** verts.
- **Build / lint** : `npm run build` ✓, `npm run lint` ✓ clean.
- **Commit** : 10d9149.
- **Conformité** : pas de changement d'auth ; aucune donnée de santé loggée ; amélioration ergonomique de consultation.

---

### v1.7 — task-102 — Refresh de session JWT + rejeu (2026-06-18)

- **PR** : [HealthPlatform.Mobile#7](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/7) — label `awaiting-human-merge`. Branche `feat/task-102-mobile-refresh-session-jwt`. Repo `client-mobile` uniquement. Dépend de task-100.
- **Décision (humain)** : refresh = **re-POST `/auth/token` (withCredentials, sans `code`)** → `TokenAggregate`, le BFF d'auth (hors workspace) mintant un nouvel access token via le cookie de session.
- **`MssHeadersInterceptor`** : détection centralisée d'expiration (`isSessionExpired` = `401` OU détail ProblemDetails « expired / refresh your session ») sur les requêtes API MSS ; **single-flight refresh** (`isRefreshing` + `BehaviorSubject<AuthSession|null>`), rejeu de la requête initiale avec en-têtes frais, **file d'attente** des requêtes concurrentes (un seul refresh effectif), **anti-boucle** via `HttpContextToken RETRIED` (max 1 rejeu). Échec refresh → `authSession.logout()` + `router.navigateByUrl('/login?expired=1')`. `AuthService` résolu paresseusement via `Injector` (évite le cycle HttpClient↔interceptor).
- **`AuthService.refreshSession()`** : `POST /auth/token` (FormData vide, `withCredentials`) → reconstruit la session (`mssApiUrl` courant conservé, JWT redécodé) et la persiste.
- **`login.page`** : bannière « Votre session a expiré. Veuillez vous reconnecter. » sur `?expired=1`.
- **Tests** : 7 nouveaux — interceptor (en-tête bearer, refresh ok→rejeu avec nouveau token, refresh ko→logout+redirect, **concurrence = 1 seul refresh**, anti-boucle), `AuthService.refreshSession` (re-POST `/auth/token` sans `code`, cookie, rebuild+save ; erreur si pas de session). Total suite : **77/77** verts.
- **Build / lint** : `npm run build` ✓, `npm run lint` ✓ clean.
- **Commit** : 850ef64.
- **Conformité** : aucun token ni donnée de santé loggé ; gestion d'expiration centralisée ; PSC/e-CPS inchangé (continuité de session).

---

### v1.6 — task-101 — HTML CDA responsive mobile (interop-cda) (2026-06-18)

- **PR** : [interop.cda.parser#6](https://github.com/codengine-technologies/interop.cda.parser/pull/6) — label `awaiting-human-merge`. Branche `feat/task-101-cda-html-responsive-mobile`. Repo `interop-cda` uniquement (mono-repo justifié : le rendu HTML vit dans le package, pas d'API/DTO modifié).
- **Feuille réellement modifiée** : `src/Interop.Cda/resources/html/cda_asip.xsl` — confirmée active via `Properties/Resources.resx` (`ResXFileRef` → `Resources.cda_asip`), écrite en tempDir et chargée par `CDAHtmlTransformer` (l.648) ; `xsl:output` HTML 4.01 + seul `<head>`/`<style>`/viewport du rendu. `cda_custom.xsl` (même contenu, non chargé) et `resources/html/cda.css` (jamais lu au runtime) écartés.
- **CSS responsive** (bloc `<style>` embarqué) :
  - `.cda-table/.cda-narr_table` ≤1200px : `display: block` + `overflow-x: auto` (le `display:block` est **requis** pour qu'`overflow-x` s'applique à une `<table>` — sinon débordement viewport) ; `max-width:100%` + `box-sizing`.
  - cellules : `overflow-wrap: anywhere` + `word-break` (longs jetons).
  - global : `img { max-width:100% }`, `box-sizing: border-box` sur conteneurs CDA.
  - nouveau `@media (max-width: 480px)` (densité réduite, lisible ~320px).
  - correction d'un `@media (max-width:1200px)` dont l'accolade fermante manquait.
  - viewport meta : déjà présent (inchangé).
- **Test** : `CdaHtmlResponsiveTests` — transforme un CDA à **tableau large (8 colonnes)** et vérifie viewport + `display: block` + `overflow-wrap` + `@media max-width:480px` dans le HTML, rendu du tableau, et **absence de `<script>`**.
- **Build / tests** : `dotnet build interop.cda.parser.sln` ✓ ; `dotnet test` ✓ **384 réussis / 5 ignorés / 0 échec**.
- **Piège build documenté** : `GenerateResource` est incrémental sur le timestamp du `.resx`, pas du `.xsl` ciblé par `ResXFileRef` → en build incrémental local, l'édition du `.xsl` n'est pas ré-embarquée tant que `Resources.resx` n'est pas touché (un build propre/CI régénère correctement).
- **Commit** : aad3013.
- **Suivi (rule 11)** : pour l'effet end-to-end, bumper `api-mail` (`Directory.Packages.props`) vers la nouvelle version NuGet d'`interop.cda.parser` après merge + publication — hors périmètre mono-repo de cette US.
- **Conformité** : aucun changement CDA r2 sur le fond ni d'API/DTO ; aucune exécution de script dans le HTML généré ; aucun log de données de santé ajouté.

---

### v1.5 — task-100 — Compose / envoi : mail-compose + html-editor (2026-06-18)

- **PR** : [HealthPlatform.Mobile#6](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/6) — label `awaiting-human-merge`. Branche `feat/task-100-mobile-compose-send`. Repo `client-mobile` uniquement. Dépend de task-096 (mergé @5086a82).
- **Composants miroir** :
  - `mss-mail-compose` — `ion-modal` ouverte via `MailEventService.openCompose$` (`ComposeRequest` typé : new/reply/forward). Champs To/Cc/Cci (Cc/Cci repliables), objet, corps HTML, **upload de pièces jointes** (FileReader → base64), case **accusé de lecture**. `send()` : validation ≥ 1 destinataire, construction `OutgoingMailDto`, POST, toast succès + fermeture, échec → message **ProblemDetails** (brouillon conservé). Reply : To = expéditeur, objet « Re: », corps cité, threading In-Reply-To/References. Forward : objet « Fwd: », corps cité, PJ d'origine reprises par référence (guid).
  - `mss-html-editor` — éditeur léger `contenteditable` (gras, italique, listes, liens via `execCommand`).
- **Intégration** : modale hébergée globalement dans `app.component` (atteignable depuis l'inbox et le détail) ; FAB « Nouveau » dans l'inbox ; boutons Répondre / Transférer dans `mss-mail-detail`.
- **`mss-api`** : `sendMail(OutgoingMailDto)` → `POST /api/v1/mail/sendmail` → `SendMailResultDto`. Nouveau DTO `OutgoingMailDto` (sous-ensemble de MailDto suffisant pour l'émission).
- **Tests** : 7 nouveaux — `mail-compose` (prefill reply/forward, refus sans destinataire, build payload + envoi + fermeture), `html-editor` (rendu initial + émission), `mss-api` (POST sendmail). Total suite : **70/70** verts.
- **Build / lint** : `npm run build` ✓, `npm run lint` ✓ clean.
- **Commit** : 53e0687.
- **Conformité** : envoi MSSanté = action sensible → PSC/e-CPS (en place) ; adresse émettrice = boîte du PS connecté ; **jamais de RPPS dans l'objet/en-têtes** ; aucune donnée de santé en clair ; envoi tracé côté backend (PGSSI-S).
- **Hors scope (décision PO)** : signatures, templates, éditeur HTML riche complet, suggestions de contacts, brouillons auto-sauvegardés, cancel-and-replace.

---

### v1.4 — task-099 — Actions message : lu/non-lu, flag, supprimer, déplacer (2026-06-18)

- **PR** : [HealthPlatform.Mobile#5](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/5) — label `awaiting-human-merge`. Branche `feat/task-099-mobile-message-actions`. Repo `client-mobile` uniquement. Dépend de task-096 (mergé @c94fa90).
- **Service** : `mail-actions.service` — orchestrateur MAJ optimiste + API + **rollback** : `toggleRead` (+ compteur non-lus dossier), `markRead` (idempotent, à l'ouverture), `toggleFlag`, `deleteMail` (retrait + réinsertion sur échec), `moveMail`.
- **`mss-mail-list`** : actions par **swipe** (`ion-item-sliding` enveloppant `mss-mail-header` dans un `ion-item`) — Lu/Non lu, Flag, Déplacer, Supprimer ; confirmation de suppression (`AlertController`), choix du dossier cible (`ActionSheetController` sur `imapFolders`).
- **`mss-mail-detail`** : barre d'actions (lu/flag/déplacer/supprimer), **mark-read à l'ouverture** (une fois par uid), émission `mailRemoved` après suppression/déplacement → `mail-detail.page` revient à `/inbox`.
- **Inbox** : segment de filtre **Tous / Non lus / Flaggés** (`mail-state.inboxFilter`).
- **`mss-api`** : `updateReadStatus`/`updateUnreadStatus`/`updateFlagStatus`/`updateUnflagStatus` (PUT `…/status/{read|unread|flagged|unflagged}`), `deleteEmail` (DELETE), `moveEmail` (PUT `…/move` `{targetFolderPath}`). Erreurs consommées au format **ProblemDetails** (`core/utils/http-error.util`).
- **`mail-state`** : `addMailToList` (rollback).
- **Tests** : 7 nouveaux — `mail-actions.service` (optimiste + rollback sur read/flag/delete, move), `mss-api` (PUT statuts, DELETE, PUT move). Total suite : **63/63** verts.
- **Build / lint** : `npm run build` ✓, `npm run lint` ✓ clean.
- **Commits** : fc281fe, a987f82.
- **Conformité** : suppression = action tracée côté backend ; rappel cascade Corbeille → lien patient (cf. mémoire projet) gérée backend, le mobile ne fait qu'appeler l'API ; aucune donnée de santé en clair.
- **Hors scope (rappel)** : compose/envoi (task-100). Bulk / multi-sélection volontairement hors scope (mono-action mobile).

---

### v1.3 — task-098 — Biologie : affichage + acquittement (2026-06-18)

- **PR** : [HealthPlatform.Mobile#4](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/4) — label `awaiting-human-merge`. Branche `feat/task-098-mobile-biology-ack`. Repo `client-mobile` uniquement. Dépend de task-096 (mergé @e59d54d).
- **Composants miroir** (`features/mail/components/`) :
  - `mss-biology` — tableau des résultats groupés par document médical, mise en évidence des valeurs flaggées (critiques LL/HH/AA rouge, anormales L/H/A orange + flèche), filtre « hors norme », plage de référence.
  - `mss-biology-ack-panel` — 5 actions (Acknowledged/PatientCalled/PatientSummoned/ReferredToColleague/MarkResolved, libellés FR), pastille de statut (À TRAITER / EN COURS / RÉSOLU), dernière action, dismiss. Toutes les actions passent par la modale (friction médico-légale).
  - `mss-biology-ack-confirm-dialog` — `ion-modal` : action choisie, **valeurs critiques** listées le cas échéant, code LOINC, note clinique optionnelle (max 500), Confirmer/Annuler.
  - `mss-biology-ack-badge` — badge ligne inbox (compteur `pendingBiologyAcksCount`, rouge si `hasCriticalPendingBiologyAck`).
  - `mss-inbox-biology-ack-chip` — chip de filtre « Bio à acquitter » (récupère les UIDs via l'API, émet l'ensemble / null).
- **Intégration** : onglet « Biologie » dans `mss-mail-body` (table + un `mss-biology-ack-panel` par CDA à biologie flaggée) ; badge dans `mss-mail-header` ; chip dans l'inbox (barre de filtre). `mss-mail-detail` relaie `ackPosted` → `mail-state.applyBiologyAck`.
- **État** (`mail-state`) : `biologyAckFilterUids` (filtre `displayedMails`) + `applyBiologyAck(uid, ack)` (décrément optimiste sur MarkResolved).
- **`mss-api`** : `recordBiologyAck(documentId, {action, note})` → `POST /api/v1/medical-documents/{id}/biology-ack` ; `getBiologyAckPendingMailUids(folderPath)` → `GET /api/v1/biology-acks/pending-mail-uids?folderPath=`.
- **Tests** : 17 nouveaux — `biology` (groupes, niveaux/flèches, filtre, format), `biology-ack-panel` (visibilité flagged, critique, record→dialog→post, MarkResolved→Resolved, annulation), `biology-ack-badge` (visibilité/compteur/critique), `inbox-biology-ack-chip` (fetch+emit set / null), `mss-api` (POST ack + GET pending uids), `mail-state` (filtre bio + applyBiologyAck). Total suite : **56/56** verts.
- **Build / lint** : `npm run build` ✓, `npm run lint` ✓ clean.
- **Commit** : ac8cc9b.
- **Conformité** : couloir biologie médicale (CR-BIO CI-SIS) ; codes LOINC + interprétation HL7 affichés tels quels ; acquittement = action médecin tracée côté backend (PGSSI-S, imputabilité) ; PSC/e-CPS ; aucune valeur de biologie / INS en clair dans les logs.
- **Hors scope (rappel)** : actions message lu/flag/suppression/déplacement (task-099), compose/envoi (task-100).

---

### v1.2 — task-097 — Pièces jointes : mail-attachment + prévisualisation inline (2026-06-18)

- **PR** : [HealthPlatform.Mobile#3](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/3) — label `awaiting-human-merge`. Branche `feat/task-097-mobile-attachments`. Repo `client-mobile` uniquement. Dépend de task-096 (mergé @8764368).
- **Composant** : `mss-mail-attachment` (Ionic) — liste des PJ avec icône par type, taille formatée, badge « Document médical » ; `select()` (preview si previewable sinon download), `download()` par fichier, `downloadAllZip()` (≥ 2 PJ).
- **Intégration `mss-mail-detail`** : getter `mergedAttachments` (PJ MIME `mail.attachments` + PJ des documents médicaux `content.medicalDocuments[].attachments` taguées `isMedical`, dédoublonnées par `guid || fileName`) ; **prévisualisation inline** via `ion-modal` — image (`<img>`), PDF (`<iframe>` blob), texte (`<pre>`) ; object URLs révoquées (`releasePreview` + `ngOnDestroy`).
- **`mss-api`** : `downloadAttachment(folderPath, uid, fileName)` → `GET …/emails/{uid}/download/attachment/{fileName}` (blob) ; `downloadAttachmentsZip(folderPath, uid)` → `GET …/emails/{uid}/attachments/download/zip` (blob). Endpoints existants (parité Angular). La génération ZIP reste **côté backend** (cf. `reference_ziparchive_kestrel_sync_io`) — le mobile consomme le flux.
- **Tests** : 7 nouveaux — `mail-attachment` (emit preview si previewable, download direct sinon, ZIP, formatSize/getIcon/rowKey), `mss-api` (URLs download + zip, responseType blob), `mail-detail` (mergedAttachments dédup + flag isMedical). Total suite : **39/39** verts.
- **Build / lint** : `npm run build` ✓, `npm run lint` ✓ clean.
- **Commit** : a8c6c03.
- **Hors scope (rappel)** : biologie + acquittement (task-098), actions message (task-099), compose/envoi (task-100).

---

### v1.1 — task-096 — Parité consultation email : mail-detail + mail-body + medical-html-frame (2026-06-18)

- **PR** : [HealthPlatform.Mobile#2](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/2) — label `awaiting-human-merge`. Branche `feat/task-096-mobile-mail-detail`. Repo `client-mobile` uniquement. Dépend de task-095 (mergé @f456a09).
- **Composants miroir** (`features/mail/components/`) :
  - `mss-mail-detail` — orchestrateur présentational (@Input mail/content/isLoading/isPlainText). En-tête à parité : `displaySubject` (titre doc médical sinon objet, préfixe XDM retiré), identité patient (nom + INS), destinataires To + Cc, date, badges (marqué, document médical, à rattacher, biologie/critique, non lu), n° de version CDA.
  - `mss-mail-body` — onglets (`ion-segment`) : corps mail + un onglet par document médical. Corps HTML assaini, bascule texte brut, **blocage des images distantes** (`blockRemoteContent`, task-089 parité) + bouton « Afficher les images ». Documents médicaux rendus via `mss-medical-html-frame`. Onglet biologie et mode PDF externe explicitement différés (task-098 / task-097).
  - `mss-medical-html-frame` — rendu du HTML CDA dans une **iframe `sandbox="allow-same-origin"` + blob** (isolation CSS, tokens design injectés, pas d'exécution de script).
  - `core/utils/remote-content.util.ts` — neutralisation des ressources distantes (miroir TS).
- **Hôte** : `mail-detail.page` refactorée en hôte mince — charge mail + contenu depuis les params de route, toggle texte brut en barre d'outils, projette `mss-mail-detail`. `core/mss` déjà supprimé en task-095.
- **Sécurité** : corps du mail via `[innerHTML]` **assaini par Angular** (scripts/handlers retirés → XSS bloqué) ; HTML CDA en **iframe sandbox** (pas d'exécution). Images distantes bloquées par défaut, révélation this-mail-only sans persistance.
- **Tests** : 12 nouveaux — `medical-html-frame` (blob safeUrl set/clear, pas de rebuild si html identique), `mail-body` (onglets mail+docs, blocage/révélation images distantes, priorité 1er doc, plain toggle, fallback plain), `mail-detail` (displaySubject doc médical, identité patient + To/Cc, badges bio/médical, rendu DOM du sujet). Total suite : **32/32** verts (Chrome Headless).
- **Build / lint** : `npm run build` ✓ (warning NG8107 de l'ancien template supprimé). `npm run lint` ✓ clean.
- **Commit** : dec408a.
- **Hors scope (rappel)** : PJ téléchargeables (task-097), biologie + acquittement (task-098), actions message (task-099), compose/envoi (task-100).

---

### v1.0 — task-095 — Socle features/mail miroir + parité Inbox + sélection de répertoire (2026-06-18)

- **PR** : [HealthPlatform.Mobile#1](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/1) — label `awaiting-human-merge`. Branche `feat/task-095-mobile-inbox-folders`. Repo `client-mobile` uniquement (full git automation, GitHub).
- **Refonte structurelle** (miroir `client-angular/front/libs/mss/src`) :
  - `core/models/` : `mail.model.ts`, `folder.model.ts`, `patient.model.ts`, `biology-ack.model.ts`, `draft.model.ts` (+ `index.ts`) — transposition TS des DTO Angular. `biology-ack`/`draft` posés pour task-098/task-100.
  - `core/utils/xdm-subject.utils.ts` (`stripXdmPrefix`).
  - `core/services/mss-api.service.ts` — déplacé depuis `core/mss/`, périmètre folders + emails (getFolders, getFolder, getEmails, getEmailContent).
  - `features/mail/services/` : `mail-state.service.ts` (signals : folders, imap/tagFolders computed, selectedFolder, emails, displayedMails trié+filtré, selectedMail, selection multi, InboxFilter) ; `mail-event.service.ts` (RxJS : mailSelected$, folderChanged$, refreshMailList$, openCompose$).
  - `features/mail/components/` (standalone, sélecteurs miroir) : `mss-mail-list`, `mss-mail-header`, `mss-mail-folder-list`, `mss-mail-folder-item`.
  - `inbox.page` refactorée en **hôte mince** : `ion-split-pane` (menu dossiers `mss-mail-folder-list` + liste `mss-mail-list`), orchestration chargement folders/emails + relais d'évènements.
  - `mail-detail.page` : imports re-câblés vers `core/models` + `core/services`.
  - Suppression de `core/mss/{models,mss-api.service}.ts`.
- **Parité ligne (`mss-mail-header`)** : `displaySubject` (titre du document médical sinon objet, préfixe XDM retiré), identité patient (nom + INS matricule), badges PJ / document médical / biologie (drapeaux serveur `hasMedicalDocuments`/`hasAbnormalBiology`/`attachmentCount`), badge critique bio, n° de version CDA (≠ 1), tags couleur, état lu/non-lu, flag, sujet barré si annulé. `data-testid` sur les éléments interactifs.
- **Sélection de répertoire** : `mss-mail-folder-list` lit `imapFolders` (computed) ; `mss-mail-folder-item` récursif (sous-dossiers dépliables), compteurs non-lus, émission `folderChanged$` → rechargement de la liste.
- **Tests** : 16 nouveaux (Jasmine/Karma) — `mail-header` (displaySubject doc médical / XDM, identité patient, badges DOM, émission mailClick), `mail-folder-item` (sélection, enfants, émission folderClick, toggle), `mail-state.service` (computed imap/tag, tri récent, filtre lu/flaggé, update/remove optimiste, compteur non-lus ≥ 0), `mss-api.service` (URLs folders/emails/content encodées, erreur sans session). Total suite : **20/20** verts (Chrome Headless).
- **Build / lint** : `npm run build` ✓ (1 warning NG8107 pré-existant dans `mail-detail.page.html`, hors scope — à traiter en task-096). `/lint-mobile` : 4 erreurs `@angular-eslint/component-selector` (préfixe `mss`) → règle eslint alignée sur `client-angular` (`prefix: ["app", "mss"]`) ; lint **clean** ensuite.
- **Commits** : 228b2e1 (refonte structure + inbox + dossiers), 5301647 (eslint préfixe `mss`).
- **Conformité** : aucune donnée de santé en clair (INS/identité/contenu) dans logs/URL ; affichage uniquement, consultation tracée côté backend.
- **Hors scope (rappel)** : consultation détail (task-096), PJ (task-097), biologie+ack (task-098), actions message (task-099), compose/envoi (task-100).

---

## Annexe C — Tasks ayant contribué à cet EPIC

> Recense les tasks dont l'entrée figure dans l'Historique ci-dessus. Les
> tasks E012 déjà passées en `done-*` mais pas encore reflétées ici (ex. lot
> en cours de traitement par la forge) rejoindront cette annexe à leur propre
> passage `/tech-writer`.

| Task | PR | Contribution | RGs fermés |
|---|---|---|---|
| task-095 | Mobile#1 | Socle features/mail miroir : parité Inbox + sélection de répertoire | — |
| task-096 | Mobile#2 | Parité consultation email : mail-detail, mail-body, medical-html-frame | — |
| task-097 | Mobile#3 | Pièces jointes : liste unifiée + prévisualisation inline | — |
| task-098 | Mobile#4 | Biologie : affichage + acquittement tracé | — |
| task-099 | Mobile#5 | Actions message : lu/non-lu, flag, suppression, déplacement | — |
| task-100 | Mobile#6 | Compose / envoi : mail-compose + éditeur HTML léger | — |
| task-101 | interop.cda.parser#6 | HTML CDA responsive mobile (feuille XSL) | — |
| task-102 | Mobile#7 | Continuité de session : refresh JWT + rejeu | — |
| task-103 | Mobile#8 | Pagination inbox orientée scroll infini | — |
| task-104 | Mobile#9 | Enrichissement + mises à jour live SSE | — |
| task-105 | Mobile#10 | Accusé de lecture sur consentement explicite | — |
| task-106 | Mobile#11 | Recherche d'emails (sémantique + filtres rapides) | — |
| task-107 | Mobile#12 | Notifications nouveaux mails (SSE in-app) | — |
| task-108 | Mobile#13 | Vue Conversations (regroupement par fil) | — |
| task-131 | Mobile#34 | Synthèse IA d'un email (panneau détail) | — |
| task-132 | Mobile#35 | Vue patient : socle recherche + fiche + opposition | — |
| task-133 | Mobile#36 | Vue patient : timeline documents médicaux + viewer | — |
| task-134 | Mobile#37 | Vue patient : timeline biologie matricielle | — |
| task-135 | Mobile#38 | Vue patient : synthèse clinique & antécédents | — |
| task-136 | Mobile#39 | Connexion CIBA e-CPS (RPPS + validation découplée) | — |
| task-137 | Mobile#41 | Rattachement email → patient par comparaison visuelle | — |
| task-138 | Mobile#42 | Garde-fous d'envoi conformes (INS, opposition, PJ) | — |
| task-139 | Mobile#43 | Brouillons : auto-save, dossier dédié, reprise, envoi | — |
| task-140 | Mobile#44 | Écran Paramètres mobile réel, préférences partagées | — |
| task-141 | Mobile#45 | Sélection multiple + actions en masse sur l'inbox | — |
| task-143 | Mobile#48 | Dossiers personnalisés (CRUD) + jauge de quota | — |
| task-145 | Mobile#49 | Signatures (CRUD + injection automatique au compose) | — |
| task-159 | Mobile#57 | Onboarding MSSanté (compte sans adresse configurée) | — |
| task-166 | Mobile#60 | Rendu des tableaux Markdown (GFM) dans le chat IA et la synthèse | — |
| task-275 | Mobile#64 | Compatibilité verrouillée au modèle « token Keycloak jetable » (6 tests, aucun code de production) | — |
