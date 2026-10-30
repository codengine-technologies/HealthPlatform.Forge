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

## Timings

*(généré par `tools/timing/report.sh --task task-412 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 10 s | — | — | — | — |
| /develop | ok | 33 min 32 s | 1 (9.2 s) | 3 (56 s) | — | client-mobile 1B/2T, api-mail 0B/1T |
| **Total cycle** | | **33 min 43 s** | **1 (9.2 s)** | **3 (56 s)** | **0 (0.0 s)** | |
