# todo-task-412 — Poste partagé : la déconnexion ferme la boîte, l'assistant agit sur la boîte ouverte

**Repos**: api-mail, client-mobile, client-angular
**Dependencies**: task-407 (le From = boîte ouverte côté mobile), task-416 (nom PSC du délégataire)
**Epic**: E020

> **Origine** : audit du périmètre « boîte déléguée » du 2026-10-30
> (`Docs/audits/2026-10-30-audit-boite-deleguee.md`), constats M1, M8 et m6.
>
> **Re-vérifiée et découpée le 2026-10-30**, sur décision humaine : chaque constat a été relu sur le
> code (mobile `cf3505f`, weda2 sur `feature/nova-mss-weda-integration`). Cette task garde la
> **sécurité du poste partagé**. La propreté du changement de boîte passe dans **task-417**, et
> `{{SenderRPPS}}` dans **task-418**. `api-mail` porte le catalogue des scénarios e2e seulement.

## Objectif

Sur un appareil partagé, un médecin qui se connecte n'arrive jamais dans la boîte du précédent, et ne
voit rien de ce que le précédent avait chargé. Un délégataire utilise l'assistant IA dans la boîte
qu'il a ouverte.

## Constats vérifiés (2026-10-30)

- **M1 — la déconnexion mobile ne ferme pas la boîte ouverte.**
  - `LogoutService.run()` (`core/auth/logout.service.ts`) ferme la session serveur, déconnecte le proxy
    et vide le jeton, mais n'appelle jamais `MailboxSessionService.clear()`. Rien n'écoute la fin de
    session pour le faire. Seul le détachement de la dernière boîte appelle `clear()`.
  - Après une connexion e-CPS (CIBA, sans rechargement), l'écran de connexion envoie vers
    `/tabs/home`, et `mailboxGuard` laisse passer dès que `current()` est posé. La personne suivante
    arrive dans la boîte précédente, avec ses messages, dossiers et mail ouvert encore en mémoire.
  - Le serveur refuse ses requêtes (`MAILBOX_NOT_ATTACHED`, règle 14), mais le client ne compte pas ce
    code parmi les refus qui purgent l'écran (`MAILBOX_ACCESS_SUSPENDED_CODES`). Le contenu chargé
    par la première personne reste donc affiché.
- **M8 — le flux de l'assistant mobile envoie l'adresse du compte.** `buildStreamHeaders()`
  (`core/services/mss-api.service.ts`) envoie `Client-Email` = `session.userEmail`, la claim `email`
  du jeton. L'intercepteur, lui, envoie la boîte ouverte. Le flux part donc vers une autre boîte que
  la conversation : un refus, ou une réponse tirée de la boîte personnelle du délégataire.
  - weda2 n'est pas touché : son `MSS_USER_EMAIL` vaut la boîte ouverte.
- **m6 — les modales survivent à la suspension (mobile).** `MailboxAccessSuspensionService.suspend()`
  purge et navigue vers « accès suspendu », sans fermer la rédaction ni l'assistant. L'assistant vit à
  la racine de l'application.

## Règles

1. **Déconnexion (mobile)** : elle vide la boîte ouverte, la liste des boîtes et tous les états de
   boîte (`MailboxSessionService.clear()`, qui purge les porteurs d'état), et ferme toute modale ouverte.
   - La connexion suivante, y compris par e-CPS sans rechargement, repasse par la garde, donc par le
     choix de boîte.
2. **`MAILBOX_NOT_ATTACHED` sur la boîte ouverte (mobile)** : l'écran est purgé, et le médecin revient
   au choix de boîte. Il ne voit pas l'écran « accès suspendu » : la boîte n'est pas suspendue, elle
   n'est simplement pas la sienne.
3. **Flux de l'assistant (mobile)** : `Client-Email` = la boîte ouverte, comme l'intercepteur.
   - Toute adresse qui représente « d'où j'agis » est relue sur le mobile.
   - Chaque usage restant de l'adresse du compte est justifié dans le `## Develop log`, par exemple
     l'affichage du compte dans les Paramètres.
4. **Suspension (mobile)** : la rédaction et l'assistant se ferment quand l'écran « accès suspendu »
   s'affiche, et les flux temps réel se ferment.
5. **weda2** : sa déconnexion révoque le jeton et repasse par la connexion Keycloak, ce qui recharge la
   page. On le **prouve** par E2E-SESSION-004 ; s'il en allait autrement, on le corrige ici.

## Definition of Done

- [ ] Build passes (0 errors) sur `client-mobile` et `client-angular` (code-only)
- [ ] Tests pass (0 failures) sur chaque client
- [ ] Tests unitaires mobile, chacun vu rouge sur le code d'avant :
  - la déconnexion vide la boîte ouverte et la liste des boîtes, et ferme les modales ;
  - après déconnexion, `mailboxGuard` repasse par le choix de boîte ;
  - `MAILBOX_NOT_ATTACHED` sur la boîte ouverte purge l'écran et renvoie au choix ;
  - les en-têtes du flux de l'assistant portent la boîte ouverte ;
  - la suspension ferme la rédaction et l'assistant.
- [ ] Scénario **E2E-SESSION-004** v1 ajouté dans `Api/Mail/e2e/scenarios.yml` (mobile requis,
      angular requis) : une personne se déconnecte, une autre se connecte sur le même appareil sans
      recharger, et n'arrive jamais dans la boîte de la première. Il relit le `Client-Email` envoyé et
      la liste affichée. Implémenté dans chaque client.
- [ ] Scénario **E2E-AI-002** v1 ajouté (mobile requis, angular requis) : un délégataire interroge
      l'assistant dans la boîte du titulaire, et la réponse porte sur la boîte ouverte (relecture du
      `Client-Email` du flux). Implémenté dans chaque client.
- [ ] Trou du filet : M1 et M8 étaient visibles du médecin sans que `/e2e` les attrape.
      E2E-SESSION-004 et E2E-AI-002 sont prouvés rouges sur le code non corrigé, et une ligne est
      ajoutée dans `conventions/e2e.md`.
- [ ] `data-testid` sur tout élément interactif ajouté
- [ ] Aucune donnée de santé en clair dans les logs ni dans le stockage de l'appareil

## Manual Test Plan

- Backend : `cd Api/Mail && dotnet run --project src/AppHost` (profil e2e). Mobile :
  `cd Client/Mobile && npm start`. weda2 : via le faux hôte.
- **Déconnexion** :
  1. Le titulaire e2e ouvre `boite-praticien`, lit un message, puis se déconnecte.
  2. Le délégataire e2e se connecte sur le même onglet, sans recharger.
  3. Attendu : l'écran de choix de boîte, ni les messages ni les dossiers du titulaire.
- **Boîte non rattachée** : forcer en mémoire une boîte que la personne connectée n'a pas.
  Attendu : l'écran se vide et revient au choix de boîte, sans « accès suspendu ».
- **Assistant d'un délégataire** : le délégataire ouvre la boîte du titulaire et interroge
  l'assistant. Attendu : une réponse sur les messages de cette boîte, ni 403 ni 404. Le `Client-Email`
  du flux est la boîte du titulaire.
- **Suspension** : un brouillon et l'assistant sont ouverts quand l'opérateur simulé refuse le
  délégataire. Attendu : les deux se ferment sur « accès suspendu ».

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — sécurité des postes partagés
- **Exigences DSR honorées** : référentiel socle MSSanté #2 (clients), ECO.1.2.8 et ECO.1.2.11 (le
  client agit sur la BAL ouverte). PGSSI-S : confidentialité sur poste partagé.
- **INS** : non applicable
- **Authentification PS** : PSC / e-CPS. La connexion d'une autre personne repart de zéro.
- **Habilitations** : seules les données de la boîte ouverte, et seulement sous accès valide (règle 14)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé (déconnexion déjà tracée côté serveur)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — logique cliente. Aucune donnée persistée sur l'appareil.
- **AIPD / impact RGPD** : inchangé — corrige une exposition de données de santé sur poste partagé

## Branches

- `api-mail` (pushed) : fix/task-412-clients-deconnexion-et-changement-de — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-412-clients-deconnexion-et-changement-de
- `client-mobile` (pushed) : fix/task-412-clients-deconnexion-et-changement-de
- `client-angular` (code-only) : la forge écrit sur la branche checkoutée dans `Client/Angular/` (`feature/nova-mss-weda-integration` au /start) — l'humain gère branche, commit, push et PR TFS

## Develop log

### client-mobile (`ef9b9e0`, `557df67`)

- **Déconnexion (M1)** : `LogoutService.run()` vide la boîte ouverte (`MailboxSessionService.clear()`,
  qui purge aussi les porteurs d'état), puis ferme la rédaction et l'assistant, avant l'écran de
  connexion. La connexion suivante repasse par `mailboxGuard`, qui ne trouve plus de boîte ouverte et
  relance la décision d'entrée.
- **Boîte non rattachée (second filet)** : un `403 MAILBOX_NOT_ATTACHED`, sur une requête non épinglée,
  vide la boîte (`clear()`), ferme les fenêtres et mène à `/mailbox-select`, qui relit la liste.
  - Ce n'est pas une suspension : il n'y a rien à ré-authentifier.
  - Le `404 MAILBOX_NOT_ATTACHED` des écrans de gestion (ré-authentification d'une boîte disparue) et
    un refus sur une requête épinglée restent à l'écran qui les a demandés.
  - Le test de task-403, qui affirmait « ne fait rien », est remplacé : c'est le changement voulu
    (règle 2).
- **Flux de l'assistant (M8)** : `buildStreamHeaders()` envoie `Client-Email` = boîte ouverte, lue dans
  `MailboxSessionService` comme dans l'intercepteur.
- **Suspension (m6)** : `suspend()` émet `MailEventService.closeMailboxOverlays$`. La rédaction se ferme
  sans enregistrer (la boîte n'est plus accessible, et l'enregistrement automatique a déjà gardé le
  brouillon). L'assistant se ferme et oublie sa conversation.
- **Flux temps réel à la suspension** : aucun changement. Le serveur ferme lui-même les deux flux SSE
  sur un refus d'accès (verdict de l'opérateur), et les deux services réagissent à cette fermeture
  (`suspendedCodeOf`).
- **Adresse « d'où j'agis » relue sur le mobile** (règle 3) :
  - `Client-Email` de l'intercepteur et du flux : boîte ouverte ;
  - `mail-compose` (From) et `mail-detail` (« Répondre à tous ») : boîte ouverte, avec repli sur le
    compte, que la garde rend inatteignable (aucun écran de messagerie sans boîte ouverte) ;
  - Paramètres : l'adresse affichée sous « Compte » est celle du compte, voulue.
- Tests unitaires, vus rouges sur le code d'avant (7 échecs attendus, puis 1389/1389 verts) :
  - `LogoutService` : ordre complet et fermeture même quand la clôture serveur échoue ;
  - intercepteur : 403 non rattaché, requête épinglée, 404 des écrans de gestion ;
  - `MssApiService` : en-têtes du flux ;
  - `MailboxAccessSuspensionService` (nouveau spec) ;
  - `AiChatComponent` et `MailComposeComponent` : fermeture sur `closeMailboxOverlays$`.
- **Flaky Karma constaté** : `MailComposeComponent` › « suggestions de destinataires (task-388) », 4 tests.
  - Rouges sur 3 passages isolés, y compris sur `develop` non modifié : la modale Ionic reste vide
    (`<!--container-->`), et attendre plus longtemps ne change rien.
  - Verts sur la suite complète, et verts ce matin (task-407, 1381/1381). Chrome est passé en 156 ce
    matin, et `node_modules` est inchangé depuis août.
  - Sans lien avec cette task : à surveiller.
- §Q passe qualité : diff court, rien à simplifier.

### Parcours e2e (catalogue `439f62b5`, api-mail)

- **E2E-SESSION-004 v1** et **E2E-AI-002 v1** (mobile et angular requis), écrits avant les tests.
- **Mobile** : la connexion e-CPS de la seconde personne est simulée à la frontière réseau.
  `/auth/connect` et `/auth/keycloak-exchange` rendent un jeton non signé pour le délégataire, et le
  bypass prend son identité.
  - Verts sur le correctif. **Vus rouges** (`--serve-only`, `--grep`, `--retries=0`) :
    - sans `clear()` à la déconnexion, l'écran de rattachement de la seconde personne n'apparaît jamais ;
    - flux sur l'adresse du compte : `Expected "praticien@e2e.test", Received "delegataire@e2e.test"`.
  - Code restauré, `grep MUTATION` = 0.
- **weda2** (code-only, non commité sur `feature/nova-mss-weda-integration`) : les deux parcours, verts.
  - E2E-AI-002 **vu rouge** sous mutation (flux sur la claim `email` du jeton) : même message.
  - E2E-SESSION-004 : aucune mutation d'une ligne ne reproduit le défaut. La protection de weda2 est
    architecturale : la connexion est une navigation complète, et un changement d'identité recharge
    l'application (task-052). Le parcours garde cette propriété, et son équivalent mobile est prouvé
    rouge.
  - Piège rencontré : une première mutation weda2 ne compilait pas (TS6133, membre inutilisé), et le
    serveur de dev servait une application cassée (`mutation-non-servie`). Elle a été corrigée avant la
    preuve.
- Catalogue : `ScenarioCatalogTests` 17/17.
- Trous du filet : deux lignes ajoutées dans `conventions/e2e.md` (M1, M8).

### client-angular (code-only)

Fichiers modifiés, non commités, sur `feature/nova-mss-weda-integration` :
- `front/e2e/mss-e2e/specs/functional.e2e.ts` ;
- `front/e2e/mss-e2e/specs/live-ai.e2e.ts`.

Aucun code applicatif weda2 n'a changé (M8 et M1 n'existent pas sur weda2). Les specs passent le
type-check `tsc` et ont été joués.

## Sonar log

**Sonar : skipped — aucun fichier analysé.** Sur api-mail, la task ne change que le catalogue des
scénarios e2e (`e2e/scenarios.yml`). Ce fichier n'entre pas dans l'analyse C# de SonarQube, donc aucun
KPI ne peut bouger. La dernière analyse (task-416, 2026-10-30 15:57 UTC) reste la référence : Quality
Gate OK, 0 issue. Les catalogues sont validés par `ScenarioCatalogTests` (17/17).

## Lint log

- **client-angular** (`/lint-angular`) : seuls deux specs e2e de `mss-e2e` (tag `scope:mss`) ont changé.
  ESLint sur ces fichiers : **0 erreur**, et 6 warnings préexistants qui ne touchent pas les lignes de la
  task (longueur du fichier, `@example` de JSDoc sur d'anciens helpers). Aucun correctif, et aucun code
  applicatif weda2 à reconstruire.

## Lint mobile log

- **client-mobile** (`/lint-mobile`) : `npm run lint` → **All files pass linting**. Aucune itération,
  aucun commit.

## E2E log

| Voie | Jouée ? | Résultat |
|---|---|---|
| mobile (`npm run e2e:headless`) | jouée (api-mail `439f62b5`, mobile `557df67`) | ✅ 56 verts, 0 flaky, parité verte |
| angular (`npm run e2e:mss`) | jouée **deux fois** (weda2 sur `feature/nova-mss-weda-integration`, specs non commités) | run 1 : 66 verts dont **1 flaky**. Rejeu après correction du test : ✅ **67 verts, 0 flaky**, parité verte |

**Flaky du run 1, propre à cette task (défaut du test, corrigé)** : E2E-SESSION-004 sur weda2, rouge au
1er essai.
- Cause : le test guettait l'échange du jeton de la seconde personne sur `/auth/token` seulement, alors
  que weda2 peut reprendre la session du proxy par `/session/token`.
- Correction : les deux chemins sont reconnus, et le bouton de déconnexion est attendu avant le clic.
- Preuve : 5/5 verts en `--repeat-each=5`, puis voie Angular entière verte. La ligne est au registre des
  flaky de `conventions/e2e.md`.

Démontage vérifié après chaque voie : aucun port e2e à l'écoute.

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
| E2E-PATIENT-003 | 1 | headless | La fiche d'un patient ne montre pas les documents d'un autre patient du même mail | ✅ | ✅ |
| E2E-PATIENT-004 | 1 | headless | La vue « Mails du patient » reste ouverte et ses pages viennent du serveur | ✅ | — |
| E2E-CONTACT-001 | 2 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Écrire à l'adresse choisie d'un contact à plusieurs adresses, ou à son adresse par défaut | ✅ | ✅ |
| E2E-COMPOSE-005 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-MAIL-006 | 1 | headless | Glisser sur la Corbeille un message d'un fil supprime ce message, et lui seul | ✅ | — |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-DRAFT-004 | 1 | headless | Une rédaction sans texte dans le corps ne laisse ni brouillon ni question | ✅ | ✅ |
| E2E-BIO-001 | 2 | headless | Acquitter un compte rendu de biologie, à son nom | ✅ | ✅ |
| E2E-BIO-002 | 1 | headless | La puce « Bio à acquitter » montre tous les résultats en attente, sur toutes les pages | ✅ | ✅ |
| E2E-BIO-003 | 1 | headless | Lire un résultat HPRIM puis l'acquitter | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 2 | headless | Créer un contact à deux adresses, le modifier sans les perdre, puis le supprimer | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-CONTACT-004 | 1 | headless | Consulter un contact depuis le carnet et lui écrire | ✅ | ✅ |
| E2E-CONTACT-005 | 1 | headless | Une fiche modifiée ne se perd pas sans confirmation, une adresse mal formée est refusée | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 2 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ · divergence (task-395) | ✅ |
| E2E-MAILBOX-003 | 2 | headless | Rattacher ses boîtes depuis « Mes boîtes » en un geste — titulaire et membre | ✅ | ✅ |
| E2E-MAILBOX-006 | 1 | headless | Après le rattachement, l'identité d'expéditeur et la signature sont déjà là | ✅ | ✅ |
| E2E-MAILBOX-004 | 1 | headless | Ajouter une BAL déléguée par saisie — et refus de sa propre adresse | ✅ | ✅ |
| E2E-MAILBOX-005 | 1 | headless | Le délégataire refusé par l'opérateur perd l'accès, en ligne puis hors ligne ; le titulaire garde le sien | ✅ | ✅ |
| E2E-AUDIT-001 | 1 | headless | Le titulaire lit au journal le message supprimé par son délégataire, au nom du délégataire | ✅ | — |
| E2E-SHARED-001 | 1 | headless | Une boîte partagée, une base — le patient rattaché par le titulaire est vu du délégataire, la signature reste à chacun | ✅ | ✅ |
| E2E-SHARED-002 | 1 | headless | Le délégataire écrit pour le compte du titulaire — le destinataire voit qui a écrit, sa réponse revient à la boîte | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |
| E2E-SESSION-004 | 1 | headless | Sur un appareil partagé, la personne suivante n'arrive jamais dans la boîte de la précédente | ✅ | ✅ |
| E2E-AI-002 | 1 | headless | Un délégataire interroge l'assistant dans la boîte qu'il a ouverte | ✅ | ✅ |

**Divergences temporaires ouvertes** (1) :

- E2E-MAILBOX-002 [angular] — le code weda2 de task-378 (écran de panne à l'entrée et son test) n'est pas encore livré sur la branche weda2 ; divergence décidée par l'humain le 2026-10-25 — résorbée par task-395 — **à retirer** : le client est revenu à la version du catalogue

**Parité : verte** — aucun écart entre le catalogue et les suites.


## Timings

*(généré par `tools/timing/report.sh --task task-412 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 10 s | — | — | — | — |
| /develop | ok | 33 min 32 s | 1 (9.2 s) | 3 (56 s) | — | client-mobile 1B/2T, api-mail 0B/1T |
| /sonar | skipped | 0.5 s | — | — | — | api-mail : catalogue e2e (YAML) seul, aucun fichier analysé par Sonar |
| /lint-angular | ok | 0.5 s | — | — | — | e2e specs seuls : 0 erreur, 6 warnings préexistants |
| /lint-mobile | ok | 23 s | — | — | — | — |
| /e2e | ok | 31 min 34 s | — | — | — | e2e ×5 (29 min 22 s) |
| /review | ok | 6 min 34 s | 2 (17 s) | 2 (5 min 23 s) | — | client-mobile 1B/1T, api-mail 1B/1T |
| /tech-writer | ok | 0.5 s | — | — | — | — |
| **Total cycle** | | **1 h 12 min** | **3 (26 s)** | **5 (6 min 19 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : lint ×1 (15 s)

## PRs

- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/119 — label `awaiting-human-merge`
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/332 — label `awaiting-human-merge` (catalogue e2e seulement)
- `client-angular` : code-only — l'humain gère le commit, le push TFS et l'ouverture de la PR. Fichiers modifiés, non commités, sur `feature/nova-mss-weda-integration` :
  - `front/e2e/mss-e2e/specs/functional.e2e.ts` (E2E-SESSION-004)
  - `front/e2e/mss-e2e/specs/live-ai.e2e.ts` (E2E-AI-002)

## Code Review Summary

**APPROVED** — 0 bloquant, 2 suggestions :
- la rédaction fermée à la déconnexion n'enregistre pas ce qui a été tapé depuis le dernier enregistrement automatique ;
- les replis « adresse du compte » de la rédaction et de « Répondre à tous » sont devenus inatteignables.

- **Règle 1b** : sans objet. Aucun comportement atteignable par un endpoint ne change, api-mail ne porte que le catalogue.
- **Preuves** :
  - tests unitaires mobile vus rouges (7 échecs attendus), puis 1389/1389 ;
  - E2E-SESSION-004 et E2E-AI-002 vus rouges sur le mobile sans correctif ;
  - E2E-AI-002 vu rouge sur weda2 sous mutation.
- **Validation** : build et tests mobile verts, api-mail 7 248 tests 0 échec. E2E vert (mobile 56/56, Angular 67/67).
- **Sonar** : non rejoué, seul le catalogue YAML change sur api-mail.

## Merged

- **Date** : 2026-10-30 21:51, `/merge 412 417 418` (attestation de test humaine)
- api-mail : `7b83e684` (PR #332) ; client-mobile : `d654c4d` (PR #119)
- CI `develop` verte : api-mail https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/41125930372 ; mobile https://github.com/codengine-technologies/HealthPlatform.Mobile/actions/runs/41125957842
