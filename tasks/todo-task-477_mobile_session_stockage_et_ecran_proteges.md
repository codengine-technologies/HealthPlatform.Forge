# todo-task-477.md — Mobile : session, stockage et écran protégés

**Repos**: client-mobile, client-angular, api-mail
**Dependencies**: aucune
**Epic**: E025
**Priorité**: EPIC E025, issue de l'audit du 2026-11-12/13, validée par l'humain le 2026-11-13. Dernière du lot.

> **Origine.** Audit en lecture seule du 2026-11-12/13 (agent « sécurité mobile »). Constats confirmés à la lecture du
> code, aucun rejoué sur appareil.
>
> **client-angular** et **api-mail** ne sont listés que pour le scénario e2e `E2E-SESSION-005` (catalogue et test web) :
> la purge de fin de session existe déjà côté web, le scénario la prouve sur les deux clients.

## Ce qui est établi

Lecture du code au 2026-11-13 (`Client/Mobile`) :

- **Jeton en clair, sauvegardable, jamais purgé.** `src/app/core/auth/auth-session.service.ts:44` :
  `localStorage.setItem(STORAGE_KEY, …)` (jeton Keycloak, RPPS, nom, adresse, identifiant de session) ;
  `auth.service.ts:254` mémorise le RPPS, jamais effacé. `android/app/src/main/AndroidManifest.xml:5` :
  `android:allowBackup="true"`, sans `dataExtractionRules` ni `fullBackupContent` : la sauvegarde Google et le transfert
  d'appareil emportent `localStorage` et le magasin de cookies de la WebView (cookie `proxy_session_id`, qui permet
  `/auth/refresh`). L'application redémarre sur `/login` sans tester la session (`app-routing.module.ts:146-149`) :
  fermer l'application sans « Se déconnecter » laisse un jeton et un cookie valides au repos, indéfiniment. Si le proxy
  est injoignable à la déconnexion, le cookie n'est ni révoqué ni effacé (`auth.service.ts:116-122`).
- **Fin de session incomplète.** `core/http/mss-headers.interceptor.ts:219-224` : sur échec du rafraîchissement,
  `authSession.logout()` puis navigation vers `/login?expired=1`, sans `MailboxSessionService.clear()` ni fermeture des
  fenêtres et des flux, que `LogoutService` fait (`logout.service.ts:67-72`). `mailboxGuard` laisse passer dès que
  `current()` est posé (`mailbox.guard.ts:24-26`) : une autre personne qui se connecte sur le téléphone prêté, sans
  tuer l'application, entre dans la boîte de la précédente. Les requêtes en attente du rafraîchissement ne sont jamais
  libérées (`:205-208`).
- **Rejeu dans la mauvaise boîte.** `mss-headers.interceptor.ts:150` rejoue après `Retry-After` ; `:241` relit
  `pinned?.email || mailboxSession.currentEmail()` à chaque rejeu. Une suppression non épinglée qui reçoit un 429, suivie
  d'une bascule, repart avec `Client-Email: B` sur le mail de même UID. `isSessionExpired` (`:292-300`) déclenche un
  rejeu sur tout statut dont le détail contient « expired ».
- **Rafraîchissement qui ressuscite la session.** `auth.service.ts:176-181` enregistre la réponse sans vérifier que la
  session existe encore : une déconnexion pendant un `/auth/refresh` est annulée par sa réponse. Une connexion qui suit
  une session périmée hérite de son `Client-Session-Id`.
- **Écran non protégé.** `android/app/src/main/java/fr/healthplatform/mobile/MainActivity.java:5` : `BridgeActivity`
  sans `FLAG_SECURE`. Comptes rendus et biologie apparaissent dans l'aperçu des applications récentes, les captures et
  l'enregistrement d'écran.
- **Écrans sans garde de boîte.** `app-routing.module.ts:116-131`, `:140-143` : `mail-search`, `signatures`,
  `contacts`, `mail/:folderPath/:uid` n'ont que `authGuard` (présence d'un jeton, `auth.guard.ts:18`).
- **Configuration de production sur des hôtes de dev.** `src/environments/environment.prod.ts:3-9` :
  `authEndpoint: 'https://auth-proxy.dev.k8s.office.weda.fr/v1'`, `cibaClientId: 'weda-edc-bas'`, `mssApiUrl` sur un
  hôte de bac à sable. `mss-headers.interceptor.ts:86` reconnaît l'API par `startsWith` ;
  `auth-session.service.ts:68` relit l'URL de l'API dans `localStorage` : une valeur réécrite (après un XSS) détournerait
  durablement le jeton.
- **Partage de fichiers.** `android/app/src/main/res/xml/file_paths.xml:3` : `external-path path="."` (gabarit
  Capacitor), sans effet tant que l'application ne partage aucun fichier.

## Objective

Un téléphone perdu, prêté ou sauvegardé ne livre pas la session du médecin ; une session qui se termine ne laisse rien
derrière elle ; une requête rejouée vise la boîte du geste ; l'écran ne montre pas de données de santé hors de
l'application.

Règles :

1. **Jeton en mémoire seulement.** Le cookie du proxy suffit à le refrapper ; à défaut, il est conservé dans le Keystore
   Android. Aucune donnée de session dans `localStorage`. La sauvegarde Android est désactivée, ou exclut le stockage de
   la WebView et ses cookies. Toute trace de session est purgée au démarrage à froid.
2. **Toute fin de session passe par la purge de la déconnexion** (expiration, refus de rafraîchissement, révocation) :
   session de boîte vidée, fenêtres et flux fermés, génération avancée, requêtes en attente libérées. Le RPPS mémorisé
   est effacé à la déconnexion.
3. **Rejeu.** Boîte et identifiant de session figés à la première émission de la requête ; rejeu abandonné si la
   génération a changé ; seul un 401 déclenche le rafraîchissement et le rejeu.
4. **Rafraîchissement.** Sa réponse n'est enregistrée que si la session de départ est encore en place. Chaque connexion
   tire un identifiant de session neuf.
5. **`FLAG_SECURE`** sur l'activité principale.
6. **Garde de boîte** (`mailboxGuard`) sur `mail-search`, `signatures`, `contacts` et `mail/:folderPath/:uid`.
7. **Configuration.** Le build de production échoue si un hôte de développement ou de bac à sable figure dans sa
   configuration. L'API est reconnue par son origine exacte, et son URL n'est jamais relue du stockage.
8. **Partage de fichiers** restreint au répertoire de cache de l'application.

### Hors périmètre

- **Connexion PSC par le navigateur** (« Autre moyen de connexion », `login.page.html:92`, sans `state` ni PKCE, retour
  non capté par un App Link) : décision humaine du 2026-11-13, non traitée dans ce lot.
- Un verrou biométrique au retour au premier plan : fonctionnalité produit, à proposer en US distincte.
- Les hôtes de production réels (`authEndpoint`, `mssApiUrl`, `cibaClientId`) : à fournir par l'humain ; cette US pose la
  garde qui empêche un build de production sur des hôtes de dev.

## Definition of Done

- [ ] Tests unitaires et de composant, vus rouges par mutation :
      - aucune donnée de session dans `localStorage` ; purge au démarrage à froid ; RPPS effacé à la déconnexion ;
      - échec de rafraîchissement : même purge que la déconnexion, requêtes en attente libérées ;
      - rejeu figé sur la boîte du geste, abandonné après une bascule ; un 403 dont le détail contient « expired » n'est
        pas rejoué ;
      - réponse de rafraîchissement sans effet après la déconnexion ; identifiant de session neuf à la connexion ;
      - garde de boîte sur les quatre routes ;
      - intercepteur : une URL au préfixe trompeur ne reçoit pas le jeton ; URL de l'API jamais lue du stockage ;
      - garde de build : configuration de production contenant `.dev.` ou `-bas` refusée.
- [ ] Android : `FLAG_SECURE` posé dans `MainActivity` ; `allowBackup` désactivé ou règles d'exclusion présentes ;
      `file_paths.xml` restreint au cache. Vérifiés par un test ou une vérification documentée dans le `## Develop log`.
- [ ] **Scénario e2e** `E2E-SESSION-005` v1 ajouté à `Api/Mail/e2e/scenarios.yml`, mobile et angular requis : « une
      session expirée ramène à la connexion ; une nouvelle connexion n'affiche rien de la boîte précédente ».
- [ ] Trou du filet : scénario `E2E-SESSION-005` prouvé rouge sur le mobile non corrigé, ligne ajoutée dans
      `conventions/e2e.md`. Parcours `E2E-SESSION-001` à `004` rejoués verts.
- [ ] Prévention (règle d'or) : `conventions/angular.md` — « jamais de jeton, d'identifiant de session ni d'URL d'API
      dans `localStorage` » ; « toute fin de session passe par la purge de la déconnexion » ; « un rejeu fige sa boîte
      à la première émission ».
- [ ] Aucune donnée de santé ni jeton dans `console.*`.
- [ ] Build et tests verts : client-mobile (`npm run build`, `npm test -- --watch=false --browsers=ChromeHeadless`),
      lint ; APK de dev construit et installé ; weda2 (`nx test mss-lib`) pour le scénario.
- [ ] client-angular : code-only, aucun commit.

## Manual Test Plan

1. Lancer le backend (`cd Api/Mail/src/AppHost && dotnet run`) ; construire et installer l'APK de dev
   (`cd Client/Mobile && npm run build && npx cap sync android`, puis Android Studio).
2. Se connecter (CIBA e-CPS), ouvrir la boîte, tuer l'application, la relancer : retour à la connexion ; dans le
   débogueur de la WebView (build de dev), `localStorage` ne contient aucune donnée de session.
3. Ouvrir un compte rendu, afficher les applications récentes : l'aperçu est masqué. Tenter une capture d'écran :
   refusée.
4. Faire expirer la session (attendre l'échéance, ou révoquer côté proxy) : retour à la connexion ; se connecter avec un
   autre compte sans tuer l'application : aucune donnée ni adresse de la boîte précédente.
5. Mode avion pendant une suppression (429 ou 401 simulé), basculer de boîte, rétablir le réseau : la suppression vise
   la boîte d'origine ou est abandonnée, jamais l'autre boîte.
6. Construire en configuration de production avec un hôte `.dev.` : le build échoue avec un message clair.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — sécurité du poste mobile
- **Vague Ségur** : hors Ségur — correctif de sécurité
- **Exigences DSR honorées** : non applicable — PGSSI-S (authentification, protection des secrets au repos,
  confidentialité de l'affichage)
- **INS** : non applicable
- **Authentification PS** : PSC CIBA (e-CPS), eIDAS substantiel, inchangée ; jeton gardé en mémoire ou au Keystore ;
  flux navigateur hors périmètre (décision humaine)
- **Habilitations** : aucune boîte accessible après la fin d'une session (règle 14)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé côté serveur
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non applicable — aucune donnée de santé persistée sur l'appareil
- **AIPD / impact RGPD** : inchangée — réduction du risque de fuite au repos et à l'écran
