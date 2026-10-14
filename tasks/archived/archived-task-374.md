# todo-task-374.md — Changer de messagerie ne laisse rien de la précédente : actions en attente, écran, notifications et compteurs

**Repos**: client-angular, client-mobile, api-mail (catalogue e2e `Api/Mail/e2e/scenarios.yml` seulement)
**Dependencies**: — (aucune). À coordonner avec task-365 (session partagée, empilement IMAP), qui touche au même `MailboxSessionStore`.
**Epic**: E016
**Single frontend**: false (client-mobile ajouté au /start)
**Priorité**: **1** — après un changement de messagerie, une suppression part sur un mail de l'autre boîte ; embarqué dans Weda, l'écran mêle les deux boîtes et les gestes portent sur d'autres messages que ceux affichés.

> **Origine.** Audit de détection de bugs du client Angular du 2026-10-13
> (`Docs/audits/client-angular-audit-bugs-20261013.md`, **ANG-10 ✔, ANG-11 ✔, ANG-25, ANG-27, ANG-77**).

## Ce qui est établi

- **Cause commune** : `MailboxSessionStore.switchTo` annonce un contrat (« les consommateurs réagissent à `switching` et `generation` »). **Aucun consommateur n'existe** : `generation()` n'est lu nulle part hors du store ; `MSS_RESETTABLE_STORES` n'enregistre que les deux services SSE.
- **ANG-10** — `mail-pending-delete.service.ts:56-78, 102-126` : une suppression « annulable » (6 s) ne fige pas sa boîte ; `mss-headers.interceptor.ts:44-51` lit la boîte courante à l'émission. Glisser vers la Corbeille puis changer de boîte : le mail de même UID de **l'autre boîte** part à la corbeille (définitivement si la source est la corbeille), celui de la première réapparaît.
- **ANG-11** — `mailbox-switcher.component.ts:152` navigue vers la même URL (`MSS_HOME_PAGE = 'mail'` en embarqué) sans `onSameUrlNavigation` : `MssMailComponent` et son état ne sont ni détruits ni purgés. Dossiers, liste, mail ouvert et rédaction restent ceux de A sous l'en-tête B ; le rafraîchissement ajoute les UID de B ; une réponse rédigée dans A part de B ; le temps réel est coupé.
- **ANG-25** — `notification-stream.service.ts` : pas de `?mailbox=` (le serveur retient la boîte par défaut) ; `reset()` coupe le flux pour de bon. En embarqué avec une boîte désignée ≠ défaut, les alertes « biologie anormale » de la boîte ouverte n'arrivent jamais.
- **ANG-27** — le compteur « N messages prêts à partir » est lu avant `open()` et jamais relu à la bascule : il compte ceux d'une autre boîte.
- **ANG-77** — `open()` sans fermeture ni purge quand une boîte est déjà ouverte ; bascules non sérialisées ; statut de connexion jamais relu.

## Objective

Que changer de messagerie **ferme proprement la précédente** — ses actions en attente sont exécutées dans **sa** boîte ou abandonnées — et **ouvre la suivante sur un écran neuf** : liste, dossiers, mail ouvert, rédaction, flux temps réel et compteurs sont ceux de la nouvelle boîte, en mode autonome comme embarqué.

### Périmètre

1. **Opérations différées figées sur leur boîte** : la boîte (et la session) est capturée à l'`enqueue` ; avant la bascule, les opérations en attente sont validées avec les en-têtes de la boîte sortante (ou abandonnées, avec retour visuel).
2. **Contrat du store respecté** : la vue mail est recréée sur `generation` (clé sur l'outlet ou navigation `reload`), les réponses d'une génération périmée sont ignorées, l'état mail est inscrit à la purge.
3. **Flux temps réel par boîte** : `?mailbox=` sur le flux de notifications ; flux rouverts à la fin de la bascule ; flux mail fermé à la destruction de la liste.
4. **Compteurs relus** à `open()` et `switchTo()`, remis à zéro à la purge.
5. **Bascules sérialisées** ; `open()` délègue à `switchTo` quand une boîte est déjà ouverte.

## Definition of Done

- [ ] Build et tests weda2 verts
- [ ] Tests unitaires et de store rouges d'abord :
  - [ ] suppression différée dans A, bascule vers B avant la fin : la requête part avec `Client-Email = A` (ou est abandonnée), jamais avec B
  - [ ] après la bascule, l'état mail (dossiers, liste, mail ouvert) est vide puis rechargé pour B ; une réponse de A arrivée après la bascule est ignorée
  - [ ] l'URL du flux de notifications porte `mailbox=` ; après la bascule, les deux flux sont rouverts pour B
  - [ ] le compteur d'envois en attente est relu après `open()` et `switchTo()`
  - [ ] deux bascules rapprochées : A fermée une fois, B ouverte une fois, dans l'ordre
- [ ] Scénario E2E-MAILBOX-001 « Changer de messagerie depuis l'écran mail, embarqué » ajouté (angular `requis` ; mobile : `requis` si le mobile offre le changement de boîte depuis la liste — à confirmer au `/start`), implémenté dans weda2 avec un praticien à deux boîtes : la liste est celle de B, une suppression faite juste avant n'atteint pas B
- [ ] Trou du filet : ligne dans `conventions/e2e.md` (le filet joue un praticien à une seule boîte)
- [ ] Aucune adresse ni identifiant de session ajouté aux journaux

## Manual Test Plan

1. Praticien à deux boîtes, Weda Échanges : glisser un mail de A vers la Corbeille, changer aussitôt de boîte vers B → aucun mail de B ne disparaît ; le mail de A est supprimé dans A (ou reste, avec un message).
2. Toujours embarqué, changer de boîte depuis l'écran mail → la liste, les dossiers et l'en-tête sont ceux de B ; aucun mail de A n'apparaît, même après 30 s.
3. Recevoir dans B (boîte non par défaut) un mail de biologie anormale → l'alerte s'affiche.
4. Laisser un message « prêt à partir » dans B, ouvrir A → le bandeau n'annonce pas le message de B.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif du socle multi-boîtes
- **Exigences DSR honorées** : non applicable — rétablit le cloisonnement entre boîtes (personnelle, organisationnelle)
- **INS** : non applicable
- **Authentification PS** : inchangée ; chaque boîte reste accédée sous la session PSC du praticien
- **Habilitations** : le cloisonnement par boîte (registre compte × adresse) est respecté côté client comme il l'est côté serveur
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : ouverture et fermeture de session de boîte tracées comme aujourd'hui (une fermeture par bascule)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangé

## Branches
- `api-mail` (pushed) : feat/task-374-mailbox-switch-clean-reset — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-374-mailbox-switch-clean-reset (catalogue e2e `Api/Mail/e2e/scenarios.yml` seulement)
- `client-mobile` (pushed) : feat/task-374-mailbox-switch-clean-reset — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-374-mailbox-switch-clean-reset (ajouté au /start sur arbitrage humain)
- `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` (snapshot au /start : `feature/nova-rewriting-mss-weda-integration`) — humain gère branche, commit, push, PR TFS

> **Constat au /start (colonne mobile de E2E-MAILBOX-001)** : `client-mobile` offre le changement de boîte depuis la liste (`Client/Mobile/src/app/inbox/inbox.page.html` → `mailbox-switcher`). Selon la DOD, la colonne mobile serait donc `requis`, mais `client-mobile` n'est pas dans `**Repos**` (aucune branche créée, règle « jamais de repo non déclaré »). **Arbitrage humain (2026-10-14) : ajouter `client-mobile`** — colonne mobile `requis`, `client-mobile` ajouté aux `**Repos**`, branche créée ; `/develop` implémente le correctif et le scénario côté mobile aussi.

## Timings

*(généré par `tools/timing/report.sh --task task-374 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 1 min 06 s | — | — | — | — |
| /develop | ok | 2 h 35 min | 7 (6 min 03 s) | 11 (26 min 20 s) | — | client-angular 2B/2T, client-mobile 2B/6T, api-mail 3B/3T |
| /develop-mobile | ok | 1 h 23 min | — | — | — | borne ouverte par le sous-agent mobile, mesure incluse dans develop |
| /sonar | ok | 23 min 48 s | 3 (2 min 12 s) | 10 (12 min 05 s) | 4 (5 min 05 s) | 1 itération(s), api-mail 3B/10T |
| /lint-angular | ok | 12 min 33 s | 1 (1 min 32 s) | 1 (5 min 09 s) | — | 1 itération(s), client-angular 1B/1T |
| /lint-mobile | ok | 1 min 02 s | — | — | — | baseline propre |
| /e2e | ok | 17 min 32 s | — | — | — | e2e ×3 (15 min 55 s) |
| /review | ok | 12 min 40 s | 3 (1 min 29 s) | 3 (7 min 23 s) | — | api-mail 1B/1T, client-mobile 1B/1T, client-angular 1B/1T |
| /tech-writer | ok | 2 min 18 s | — | — | — | — |
| **Total cycle** | | **5 h 10 min** | **14 (11 min 18 s)** | **25 (50 min 58 s)** | **4 (5 min 05 s)** | |

Autres commandes mesurées : lint ×3 (2 min 01 s)

## Develop log

- Repos touched : client-angular (code-only), client-mobile, api-mail (outillage e2e + catalogue + correctif de dépendance)
- DTOs published : no DTO change — Interop published : no interop change
- Commits :
  - api-mail : `2762dfb4` chore(deps) Pkcs 10.0.13 · `a585ee3f` test(e2e) seconde boîte + E2E-MAILBOX-001 · `1d478149` refactor(e2e) simplify pass
  - client-mobile : `1104d05` fix(mobile) bascule propre · `5df3115` test(mobile) E2E-MAILBOX-001 · `2cda97e` refactor(mobile) simplify pass
  - client-angular : **non commité** sur `feature/nova-rewriting-mss-weda-integration` (code-only, l'humain commite et pousse vers TFS) — 23 fichiers modifiés + 4 nouveaux : `apps/weda2/…/mss-headers.interceptor{,.spec}.ts`, `e2e/mss-e2e/{specs/functional.e2e.ts,support/e2e-backend.ts,support/session.ts}`, `libs/mss/src/core/{guards/mailbox.guard.ts,index.ts,services/mail-events-stream.service{,.spec}.ts,services/mss-api.service.ts,services/notification-stream.service{,.spec}.ts,stores/mailbox-session.store{,.spec}.ts,tokens/mss-mailbox-pin.token.ts}`, `libs/mss/src/features/{layout/mss-layout.component.{html,ts,spec.ts,switch.spec.ts},mail/mss-mail.component.ts,mail/mss-mail.component.initial-folder.spec.ts,mail/components/mail-list/mail-list.component{,.spec}.ts,mail/services/mail-pending-delete.service{,.spec}.ts,mailbox-onboarding/…component.ts,mailbox-select/…component.ts}`
- Ce qui a changé (les deux clients) :
  - **ANG-10** suppression différée figée sur sa boîte (`MSS_MAILBOX_PIN`, `HttpContext` lu par l'intercepteur) et **soldée avant la clôture** de la session sortante (`registerOutgoingDrain`) ; mobile : un lot non soldé est abandonné à la purge.
  - **ANG-11** web : l'écran routé est clé sur `generation` (`@for` autour du `router-outlet`), donc détruit et recréé à chaque bascule (état, rédaction, requêtes en vol) ; mobile : l'onglet Messages, gardé vivant par Ionic, recharge sur `generation` et ignore les réponses périmées ; les porteurs d'état racine sont inscrits à la purge (`MAILBOX_SCOPED_STATES` était vide).
  - **ANG-25** flux de notifications : `?mailbox=` (web ; déjà présent sur mobile), `reset()` ferme sans désactiver, rouvert pour la nouvelle boîte ; flux mail relâché à la destruction de la liste (bail).
  - **ANG-27** compteur « prêts à partir » relu après `open()` et `switchTo()` (non bloquant), remis à zéro à la purge, réponse d'une génération périmée jetée.
  - **ANG-77** bascules sérialisées (file), `open()` délègue à la bascule quand une boîte est ouverte.
  - **Constaté par le e2e, corrigé** : l'écran neuf s'ouvrait sur `folders[0]` (« Sent », « Trash ») quand les dossiers arrivaient avant les réglages — repli sur INBOX (`mss-mail.component.ts`, test `…initial-folder.spec.ts` vu rouge sur « Sent »).
- Tests unitaires vus rouges puis verts (web) : store 8 (`open_AfterInitialize_RereadsTheCounter…`, `switchTo_RereadsTheCounter…`, `refreshConnectionStatus_AnsweredAfterASwitch_IsIgnored`, `open_WhileAMailboxIsOpen_Switches…`, `switchTo_TwoCloseSwitches_ClosesAOnceAndOpensBOnceInOrder`, `switchTo_DrainsPendingOperations…BeforeClosing`, `registerOutgoingDrain_Unregistered…`, `switchTo_ADrainThatFails_StillSwitches`), suppression différée 5, intercepteur 1, flux notifications 2, flux mail 2 + liste 1, vue clé sur la génération 1, premier dossier 1. Mobile : 15 tests, 10 rouges sur le code d'avant + 4 par mutation (détail dans le rapport du sous-agent, repris en revue).
- Seed e2e (api-mail) : seconde boîte `cabinet@e2e.test` rattachée au **même compte** (même sub, même RPPS), non par défaut, avec son message, ses réglages et sa propre session ; relue (deux boîtes listées, la praticien par défaut). Reset : ses bases supprimées.
- **Preuve par mutation E2E-MAILBOX-001** (serveur de dev relu : marqueur compté, nouveau bundle + 20 s, témoin restauré rejoué vert à chaque fois) :
  - Angular MA1 (vue non recréée) → rouge sur « la liste est celle de la seconde boîte » ; MA2 (épinglage + solde retirés) → rouge sur « le message supprimé a quitté l'INBOX de la boîte praticien (relu côté serveur) ».
  - Mobile MM1 (onglet non rechargé sur `generation`) → rouge sur « la liste est celle de la seconde boîte » ; MM2 (épinglage + solde retirés) → rouge sur la relecture serveur.
  - Témoin : vert 4/4 d'affilée sur le même backend (web), 2/2 (mobile).
  - **Vert qui ment trouvé et corrigé** : la première version supprimait depuis le détail, chemin IMMÉDIAT — MA2 restait vert. Le parcours emprunte désormais le geste différé (glisser vers la Corbeille / balayage « Supprimer ») et pose sa précondition (bascule achevée en < 6 s).
- Trous du filet (`conventions/e2e.md`) : ligne task-374 ; consignes `en-tete-force-par-le-banc` (le bypass écrasait `client-email`, puis faisait payer ~4 s de jeton simulé refusé à chaque requête) et `geste-differe`.
- **Hors périmètre fonctionnel, mais bloquant — à valider en revue** : `chore(deps)` api-mail. Les avis GHSA-2fmv-rv2c-59x7 / GHSA-846f-f764-76mx (NU1902/NU1903 en erreur) sur `System.Security.Cryptography.Pkcs` 10.0.0, transitif via MimeKit 4.17.0, cassaient toute restauration d'api-mail, develop compris. Épinglé 10.0.13, référencé dans `mss.mail.application`.
- Local build / test : ✓
  - api-mail : build 0 erreur 0 avertissement ; 6 647 tests verts (195 + 690 + 3 642 + 1 233 + 887, 16 ignorés en intégration).
  - client-angular : build weda2 ✓ (avertissement de budget initial 2,01 Mo / 2 Mo, dépassé de 12,8 ko — non comparé à develop : le store de session, modifié, est dans le bundle initial ; à vérifier en revue) ; 11 projets verts (mss-lib 846).
  - client-mobile : build ✓ ; 1 067 tests verts. Un passage à 3 rouges transitoires dans `MailboxSwitcherComponent` (internes Ionic `onAriaChanged`/`apply` indéfinis), verts aux deux rejeux, spec non touchée par la passe : flaky signalé.
- Passe qualité (/simplify, 4 relecteurs) :
  - Applied & committed : client-mobile (`2cda97e` : relecture du compteur non bloquante comme sur le web, `takePending()`) ; api-mail (`1d478149` : protocole de dépôt IMAP commun aux deux boîtes, ce qui restaure `Flagged` perdu par la copie ; registre résolu une fois ; doc XML replacée ; paramètre requis).
  - Applied (code-only, uncommitted) : client-angular, 1 fichier (`e2e/mss-e2e/support/e2e-backend.ts`, commentaire en double).
  - Écartés, à juger en revue : (1) attendre réglages ET dossiers (`combineLatest`) plutôt que le repli INBOX, qui ignore un défaut non-INBOX quand les dossiers arrivent les premiers ; (2) bail du flux mail jugé superflu (fournir le service au niveau de l'écran) ; (3) garde de génération centralisée dans l'intercepteur plutôt que fil à fil (mobile `isStale`, ~12 sites) ; (4) l'épinglage serait redondant avec le solde, mais gardé : la DOD exige `Client-Email = A` ; divergence web/mobile dans le cas `outgoingAlreadyClosed` (web : le lot part épinglé vers la boîte détachée ; mobile : abandonné) ; (5) mobile : double chargement possible (effet de génération + `ionViewWillEnter`) quand la bascule ne part pas de l'onglet Messages ; (6) factorisation du réchauffage, réemploi du provisionneur, parallélisme du seed, stub de session dupliqué 5× dans les specs mobile.
  - Skipped (contract/excluded) : dtos-mss, interop-cda, sdk.
- Logs : aucune adresse ni identifiant de session ajouté aux journaux (seuls nouveaux logs : messages d'erreur génériques du store).
- DOD self-check : build/tests ✓ ; 5 tests DOD ✓ (deux clients) ; E2E-MAILBOX-001 ✓ catalogue + deux suites + mutations ; trou du filet ✓ ; logs ✓.
- Next step : /sonar task-374

## Sonar log

- Serveur 25.6.0 (`sonar.token`), port 9001 mesuré ; 2 analyses complètes sur `feat/task-374-…` (Release, 5 passes OpenCover, 6 647 tests verts à chaque passe).
- Phase 1 (new code de la task) : ✓ — **0 finding sur les fichiers touchés par task-374** après correction.
  - Issue fixée : 1 (CA1068 sur `E2eSeed.SettingsPersistedAsync`, introduite par la passe qualité en rendant requis un paramètre placé après le jeton) — commit `582db253`. `conventions/csharp.md` CA1068 : Occurrences 3.
  - Hotspots new code sur les fichiers de la task : 0.
  - Tests ajoutés : 0 (new_coverage 98,1 % ≥ 95 %).
- Quality Gate du projet : **ERROR, non imputable à la task** — `new_violations` 70 et `new_security_hotspots_reviewed` 0 % (13 hotspots), tous sur des fichiers que la task ne touche pas (la new-code period couvre des tasks déjà mergées, cf. mémoire projet). Vérifié par croisement fichier à fichier avec `git diff --name-only origin/develop`.
- Phase 2 (legacy) : non jouée (optionnelle, best-effort).
- Build / tests : ✓ green

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | ERROR | ERROR | → (hors task) |
| New coverage | 98,1 % | 98,1 % | 0 |
| Bugs | 2 | 2 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 15 | 15 | 0 |
| Code smells | 73 | 68 | −5 |
| Coverage (projet) | 98,0 % | 97,9 % | −0,1 pt |
| Duplication | 0,3 % | 0,3 % | 0 |
| Reliability / Security / Maintainability | D/A/A | D/A/A | → |

## Lint log (client-angular)

- Outil : `npx eslint` sur les 27 fichiers de la task (contournement consigné task-367 : `nx affected --projects=tag:scope:mss` ne restreint pas le lint sur ce workspace, et `--output-file` absolu casse en ENOENT).
- Baseline : 3 erreurs (2 `prettier/prettier`, 1 `jsdoc/require-param`), 50 warnings (35 `jsdoc/require-example`, 10 fichiers ignorés par la config (specs, html), 5 `max-lines`).
- Itération 1 (auto-fix) : 0 erreur. Fix manuels : `@example` d'un helper e2e (`support/session.ts`), description du `@param mailbox` posé vide par l'auto-fixer (`notification-stream.service.ts`). Seul warning attribuable à la task, après attribution ligne à ligne (`git diff -U0 HEAD`), il est corrigé ; les autres `require-example` sont sur des lignes antérieures.
- Accepté (best-effort) : `max-lines` sur `mailbox-session.store.ts`, que la task fait passer de 475 à 594 lignes (au-dessus du seuil de 500) ; le découpage du store sort du périmètre. Les 4 autres `max-lines` sont antérieurs.
- Build (pipeline, `nx affected -t build --base=origin/next`) : **1 échec antérieur et hors task** : `mss:build:production` (application autonome `apps/mss`), `apps/mss/src/environments/environment.prod.ts` déclaré dans les `fileReplacements` mais absent de la branche de l'humain (`feature/nova-rewriting-mss-weda-integration`, présent sur `origin/next`). Les 10 autres builds sont verts, dont weda2 (avertissement de budget initial 2,01 Mo / 2 Mo, non comparé à develop).
- Tests (pipeline, `nx affected -t test`) : 11 projets verts.
- Itérations : 1 / 5. Aucune opération git sur client-angular (seul `git fetch origin next`).

## Lint mobile log

- `npm run lint` (ng lint, `lintFilePatterns` de `angular.json`) sur `feat/task-374-…` : **All files pass linting** — 0 erreur, 0 warning. Rien à corriger, aucun commit.
- Itérations : 0 / 5 (baseline propre).

## E2E log

| Voie | Jouée | Résultat | Rapport |
|---|---|---|---|
| mobile | oui (`npm run e2e:headless`, client-mobile + api-mail touchés) | 36 verts, 0 flaky, 0 rouge, parité verte | report.json copié |
| angular | oui (`npm run e2e:mss`, client-angular + api-mail touchés) | 40 verts, 0 flaky, 0 rouge, parité verte | report.json copié |

- Catalogue : celui de la branche api-mail de la task (`Api/Mail/e2e/scenarios.yml`, E2E-MAILBOX-001 v1 ajouté).
- Porte `gate` : code 0. Démontage vérifié : ports 4200/8100/5052/3993/3465/3143 libres, aucun conteneur e2e résiduel.
- Écrans modifiés sans spec e2e modifiée : aucun (les deux suites portent E2E-MAILBOX-001).

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
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/297 — label `awaiting-human-merge`
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/95 — label `awaiting-human-merge`
- `client-angular` : code-only — humain gère commit/push TFS et ouverture PR. Branche `feature/nova-rewriting-mss-weda-integration`, fichiers modifiés (non commités) :
  - front/apps/weda2/src/app/core/interceptors/mss-headers.interceptor.spec.ts
  - front/apps/weda2/src/app/core/interceptors/mss-headers.interceptor.ts
  - front/e2e/mss-e2e/specs/functional.e2e.ts
  - front/e2e/mss-e2e/support/e2e-backend.ts
  - front/e2e/mss-e2e/support/session.ts
  - front/libs/mss/src/core/guards/mailbox.guard.ts
  - front/libs/mss/src/core/index.ts
  - front/libs/mss/src/core/services/mail-events-stream.service.ts
  - front/libs/mss/src/core/services/mss-api.service.ts
  - front/libs/mss/src/core/services/notification-stream.service.spec.ts
  - front/libs/mss/src/core/services/notification-stream.service.ts
  - front/libs/mss/src/core/stores/mailbox-session.store.spec.ts
  - front/libs/mss/src/core/stores/mailbox-session.store.ts
  - front/libs/mss/src/features/layout/mss-layout.component.html
  - front/libs/mss/src/features/layout/mss-layout.component.spec.ts
  - front/libs/mss/src/features/layout/mss-layout.component.ts
  - front/libs/mss/src/features/mail/components/mail-list/mail-list.component.spec.ts
  - front/libs/mss/src/features/mail/components/mail-list/mail-list.component.ts
  - front/libs/mss/src/features/mail/mss-mail.component.ts
  - front/libs/mss/src/features/mail/services/mail-pending-delete.service.spec.ts
  - front/libs/mss/src/features/mail/services/mail-pending-delete.service.ts
  - front/libs/mss/src/features/mailbox-onboarding/mss-mailbox-onboarding.component.ts
  - front/libs/mss/src/features/mailbox-select/mss-mailbox-select.component.ts
  - front/libs/mss/src/core/services/mail-events-stream.service.spec.ts
  - front/libs/mss/src/core/tokens/mss-mailbox-pin.token.ts
  - front/libs/mss/src/features/layout/mss-layout.component.switch.spec.ts
  - front/libs/mss/src/features/mail/mss-mail.component.initial-folder.spec.ts

## Code Review Summary

**APPROVED** — 0 bloquant. Build + tests revalidés sur l'état fusionné avec `origin/develop` (api-mail 6 647 verts ; mobile 1 101 verts ; Angular build ✓, 11 projets verts).

- Règle 1b : aucun comportement atteignable par un endpoint d'api-mail n'est modifié (outillage e2e, catalogue, épinglage Pkcs) → pas de test d'intégration d'endpoint requis. Le `?mailbox=` ajouté côté web vise une route déjà marquée `[MailboxFromQuery]` (`NotificationsController.cs:58`).
- Comportements clients → preuves : épinglage + solde → tests store/pending-delete/intercepteur (rouges d'abord) + E2E-MAILBOX-001 MA2/MM2 rouges ; vue recréée → `mss-layout.component.switch.spec.ts` (rouge d'abord) + MA1/MM1 rouges ; flux → tests notification/mail-events (rouges d'abord) ; compteurs + sérialisation → tests store (rouges d'abord).
- Double verrou E2E : `## E2E log` vert (mobile 36/36, angular 40/40, parité verte).
- Merge `origin/develop` : api-mail sans conflit ; mobile, conflit d'imports e2e résolu par union mécanique (aucun arbitrage), type-check ✓.
- Signal hors task : **E2E-DETAIL-005 (task-371, mergée sur develop) est `requis` sur Angular, mais aucun test ne l'implémente dans le clone weda2 de ce poste** (branche de l'humain) — si le code-only de task-371 n'y est pas reporté, la prochaine voie Angular jouée sur le catalogue de develop rendra une parité rouge, imputable à task-371.
- Suggestions (non bloquantes) : voir le corps des PRs (solde d'un commit en vol + délai, masquage `mailbox` dans les journaux d'api-mail, négatif côté seconde boîte, cas `outgoingAlreadyClosed`, taille du store, budget weda2, double chargement mobile, rédaction non sauvegardée perdue).

## Merged

- Mergé le 2026-10-14 par l'humain (`/merge task-374 --i-tested`, plan de test manuel attesté).
- `api-mail` : PR #297 squash → `cf040c22` — CI develop ✓ https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/38603662369
- `client-mobile` : PR #95 squash → `e74b8d58` — CI develop ✓ https://github.com/codengine-technologies/HealthPlatform.Mobile/actions/runs/38603696237
- Branches `feat/task-374-mailbox-switch-clean-reset` supprimées (distante et locale) sur les deux dépôts ; label `awaiting-human-merge` retiré.
- `client-angular` : managed manually by the human.
