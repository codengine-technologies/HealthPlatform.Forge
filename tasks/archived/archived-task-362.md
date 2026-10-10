# todo-task-362.md — Intégration Weda : weda2 embarqué s'ouvre sur la messagerie que Weda désigne

**Repos**: client-angular, api-mail (catalogue e2e seulement : `Api/Mail/e2e/scenarios.yml`)
**Dependencies**: done-task-356 (pont v1, `EmbeddedHostService.request()`)
**Epic**: E019
**Single frontend**: true — seul weda2 (client-angular) est embarqué dans Weda. Blazor et mobile
n'ont pas d'hôte Weda (raison fonctionnelle).
**Priorité**: **1** — un compte Keycloak peut porter plusieurs boîtes, et weda2 ouvre aujourd'hui sa
boîte « par défaut ». Embarqué dans Weda, il peut donc afficher une autre boîte que celle que Weda
connaît et que WMickey synchronise. L'import à la demande (task-363) s'appuie sur cette tâche.

> **Origine.** Décision de l'humain du 2026-10-10, consignée dans l'amendement 3 de l'ADR-007 (dépôt
> Weda, décision B6) et dans l'amendement 3 de l'ADR client
> (`Client/Angular/docs/ADR-2026-10-09-integration-weda-mode-embarque.md`, § 1 et 2) :
> - en mode embarqué, **c'est Weda qui transmet l'adresse** de la boîte à ouvrir ;
> - weda2 ouvre cette boîte **à chaque entrée**, même si le praticien a mis une autre boîte « par
>   défaut » dans weda2 ;
> - si elle n'est pas rattachée au compte, weda2 **propose de la rattacher**, avec son écran de
>   rattachement pré-rempli, puis l'ouvre ;
> - après l'ouverture, le changement de boîte reste **libre**.
>
> **Hors flag, et c'est voulu** (ADR client, amendement 3, § 1) : api-mail évalue `weda_integration`
> sur l'identité de la boîte ouverte, et `GET /api/v1/FeatureFlag` exige une boîte. Le flag ne peut
> donc pas décider quelle boîte ouvrir. La désignation rejoint « l'adaptation à l'iframe », comme la
> connexion déléguée. Côté Weda, l'iframe n'est affichée que pour un cabinet où `weda_integration`
> est active.

## Ce qui existe (constaté dans le code le 2026-10-10)

- **client-angular** :
  - `libs/mss/src/core/guards/mailbox.guard.ts` appelle `store.initialize()` (liste des boîtes et
    statut de session), puis applique la table de décision. Pour `OpenDirectly`, il ouvre la boîte
    `selectable && isDefault`, sinon il renvoie à l'écran de choix.
  - `MailboxSessionStore` (`core/stores/mailbox-session.store.ts`) : `open()` refuse une boîte non
    sélectionnable ; `clear()` remet tout à zéro.
  - `features/mailbox-onboarding/mss-mailbox-onboarding.component.ts` est l'écran de rattachement,
    adossé à `ui/attach-mailbox-form`. Le champ `email` y est un signal local, vidé par `reset()`.
    Après le rattachement, « Ouvrir » ouvre la boîte rattachée.
  - `apps/weda2/src/lib/embedded/` : `EmbeddedHostService.request()` (pont v1 ; délai par défaut
    30 s ; `unsupported` hors mode embarqué). `WedaIntegrationService` lit `weda_integration`
    **après** l'ouverture d'une boîte.
- **api-mail** : une boîte demandée par `Client-Email` et non rattachée au compte est refusée
  (`403`, code `NOT_ATTACHED`) sur toute route qui exige une boîte (`UserContextEnricherMiddleware`).
- **e2e** : `front/e2e/mss-e2e/support/session.ts` simule le proxy d'authentification par
  `page.route` (`/session/has-session`, `/session/token`). Aucun hôte embarquant n'existe.
- **Weda** (hors forge) : la boîte de l'utilisateur est celle que WMickey synchronise,
  `IMailBoxService.GetMailBoxAsync(UserID, CabinetID)` → `ASP_Select_MailBoxById` (base Mickey,
  `T_Mailbox_Box.Box_Address`). Elle n'est pas dans `CustomPrincipal`.

## Objective

1. **libs/mss** :
   - un jeton optionnel dans `core/tokens/`, par exemple `MSS_DESIGNATED_MAILBOX`
     (`() => Promise<string | null>`), exporté par `core/index.ts` ;
   - `mailboxGuard` l'interroge à l'entrée, quand aucune boîte n'est ouverte, en parallèle de
     `store.initialize()`, puis décide :

     | Situation | Résultat |
     |---|---|
     | Une boîte sélectionnable du compte porte l'adresse (sans casse, sans espaces autour) | elle est ouverte, quel que soit `isDefault` |
     | La boîte existe mais n'est pas sélectionnable | écran de choix, qui en donne la raison |
     | Le compte ne la porte pas | écran de rattachement, pré-rempli |
     | Pas d'adresse : jeton absent, `null`, rejet | table de décision inchangée |

     `PscRequired` reste prioritaire : sans session PSC, aucun rattachement n'est possible ;
   - l'adresse désignée est gardée **en mémoire** dans `MailboxSessionStore` (signal), et `clear()`
     la remet à zéro. **Jamais dans l'URL** : elle finirait dans l'historique du navigateur et dans
     les journaux du serveur web ;
   - l'écran de rattachement pré-remplit le champ avec l'adresse désignée, et l'annonce : « La
     messagerie {adresse} n'est pas encore rattachée à votre compte. » Sans adresse désignée,
     l'écran est inchangé. Il ne nomme pas Weda.
2. **apps/weda2** : fournit le jeton **en mode embarqué seulement**.
   - Il envoie `EmbeddedHostService.request<{ email: string }>('get-mailbox')`, avec un délai de
     10 s.
   - Une erreur, une adresse vide ou mal formée donnent `null`.
   - `'get-mailbox'` rejoint `EmbeddedHostRequestType`.

   Hors mode embarqué, le jeton n'est pas fourni : weda2 autonome est inchangé.
3. **Faux hôte de test**, réutilisé par task-363 :
   - une page servie par Playwright (`page.route`), sur une origine dédiée déclarée dans les
     origines autorisées de l'environnement e2e ;
   - elle embarque weda2 dans une iframe, et répond au pont v1 avec des données fixes, contrôles
     d'origine compris ;
   - ici, elle répond à `host-capabilities` et `get-mailbox`.
4. **Journaux** : weda2 journalise l'issue de l'entrée (`designated`, `attach-proposed`, `fallback`),
   **jamais l'adresse**.

## Partie Weda (hors forge, faite en dehors de `/develop`)

Elle est nécessaire pour que la tâche soit complète (règle 11).

> **Repère `nova-mss`** (ADR-007, amendement 4) : tout le code Weda de cette partie vit sous
> `Weda/api/NovaMss/` (namespace `Weda.api.NovaMss`, classes préfixées `NovaMss`, route
> `api/nova-mss`) ou sous `Weda/FolderMedical/WedaEchanges/NovaMss/` (préfixe DOM et CSS `nova-mss-`).
> Chaque fichier porte l'en-tête `nova-mss — …`. **Aucun fichier Mickey ou de l'ancien écran n'est
> modifié** : une règle à reprendre est **copiée** dans `NovaMss`, avec un commentaire qui cite sa
> source. Hors de ces dossiers, seuls changent `Weda.csproj` et, au besoin, l'inclusion dans
> `Default.aspx`.

- **`GET /api/nova-mss/mailbox`** dans `NovaMssController` (`Weda/api/NovaMss/`, repère `nova-mss`, ADR-007 amendement 4) :
  - `[Authorize]`, et `HasWmss` exigé ;
  - refusé (`403`) à un secrétaire (`IsSecretary()`) ;
  - rend `{ email }` depuis `GetMailBoxAsync(UserID, CabinetID)`, ou `404` si l'utilisateur n'a pas
    de boîte ;
  - n'écrit pas l'adresse dans les journaux.
- **Gestionnaire `get-mailbox`** dans `Weda/FolderMedical/WedaEchanges/NovaMss/nova-mss-host.js`, par `callApi`, avec les codes d'erreur
  existants.
- **Switch** : il n'est pas proposé aux secrétaires (ADR-007, B7). La règle vit dans
  `NovaMssHost.ascx.cs` (le contrôle ne s'affiche pas), pas dans `Default.aspx.cs`.

## Definition of Done

- [ ] Build passes (0 errors) sur client-angular ; Tests pass (0 failures, hors flaky préexistants
  documentés)
- [ ] **Angular — garde**, tests rouges d'abord, une ligne par cas de la table :
  - [ ] la boîte désignée est ouverte alors qu'une **autre** boîte est `isDefault` ;
  - [ ] la comparaison ignore la casse ;
  - [ ] boîte désignée non sélectionnable → écran de choix ;
  - [ ] boîte désignée absente du compte → écran de rattachement, et l'adresse est dans le store ;
  - [ ] jeton absent, `null` ou rejeté → table de décision inchangée (non-régression de weda2
    autonome) ;
  - [ ] sans session PSC et sans boîte → `psc-required`, même avec une adresse désignée.
- [ ] **Angular — écran de rattachement** : avec une adresse désignée, le champ est pré-rempli et
  l'annonce s'affiche ; sans adresse, l'écran est inchangé. Après le rattachement, « Ouvrir » ouvre
  la boîte désignée.
- [ ] **Angular — shell** :
  - [ ] le jeton n'est fourni qu'en mode embarqué ;
  - [ ] `get-mailbox` est envoyé à l'hôte ;
  - [ ] délai dépassé, `not-found`, `forbidden` ou adresse vide → `null`.
- [ ] **Entrée suivante** : après un changement de boîte puis une nouvelle entrée (store vidé), la
  boîte désignée est rouverte.
- [ ] Scénario **E2E-WEDA-001**, version 1, ajouté dans `Api/Mail/e2e/scenarios.yml` :
  - titre : « Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne » ;
  - attendu : weda2, embarqué par le faux hôte, s'ouvre sur `boite-praticien`, que l'hôte désigne.
    Si l'hôte désigne une adresse que le compte ne porte pas, weda2 affiche l'écran de
    rattachement, pré-rempli avec cette adresse ;
  - clients : `angular: requis`, `mobile: non-applicable — l'application mobile n'est pas embarquée
    dans Weda` ;
  - seed : `boite-praticien` ;
  - implémenté dans client-angular, avec le faux hôte.
- [ ] `data-testid` sur l'annonce de l'écran de rattachement ; libellés FR en dur
- [ ] Aucune adresse de messagerie dans les journaux de weda2, et aucune donnée de santé
- [ ] **Weda — repère `nova-mss`** : `git diff --stat` de la partie Weda ne montre que des fichiers sous
  `NovaMss/`, plus `Weda.csproj` (et l'inclusion dans `Default.aspx`). Aucun fichier sous
  `Weda/api/WMickey/`, `WMickey/` ou `WedaGlobal/WCommunication/` n'est modifié.
- [ ] Partie Weda faite et validée (règle 11) : voir le Manual Test Plan

## Manual Test Plan

1. Lancer le backend (`cd Api/Mail && dotnet run --project src/AppHost`) et weda2
   (`cd Client/Angular/front && .\serve-weda2.ps1`). Weda tourne en `https://localhost:44300`, avec
   un utilisateur qui a une boîte V2 (WMickey), dans un cabinet où le switch est proposé.
2. Prendre un compte qui porte **deux** boîtes. Dans weda2 autonome
   (`https://localhost:4200/messagerie`), mettre « par défaut » la boîte qui **n'est pas** celle de
   Weda.
3. Dans Weda › Échanges, activer la nouvelle expérience : weda2 s'ouvre sur la boîte de Weda, pas
   sur la boîte par défaut de weda2.
4. Changer de boîte dans weda2 : la bascule fonctionne. Recharger la page Échanges : la boîte de
   Weda est rouverte.
5. Détacher la boîte de Weda dans weda2 (gestion des messageries), puis recharger Échanges. L'écran
   de rattachement s'affiche, pré-rempli avec l'adresse de Weda. Rattacher, puis « Ouvrir » : la
   boîte s'ouvre.
6. Ouvrir weda2 hors iframe, dans un onglet : la boîte par défaut de weda2 s'ouvre, comme avant.
7. Avec un compte secrétaire : le switch n'est pas proposé.
8. Dans les journaux du navigateur et du serveur Weda, aucune adresse de messagerie n'apparaît.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — messagerie MSSanté intégrée au logiciel
- **Exigences DSR honorées** : aucune nouvelle. C'est un préalable de RG-E009-034 (classer depuis le
  logiciel métier) : la messagerie affichée dans Weda est celle que Weda connaît.
- **INS** : non concerné, aucune donnée de patient
- **Authentification PS** : PSC / e-CPS, inchangée. La désignation n'accorde aucun droit : api-mail
  vérifie que la boîte est rattachée au compte, et seul le titulaire d'une boîte peut la rattacher
  (identité PSC).
- **Habilitations** : la boîte ouverte appartient au compte connecté (registre d'api-mail). Weda ne
  rend l'adresse qu'à l'utilisateur lui-même, pour le cabinet de sa session.
- **Interop CI-SIS** : non concerné
- **Tracé PGSSI-S** : l'ouverture de la boîte est tracée comme aujourd'hui (session de boîte
  d'api-mail). Aucune adresse dans les journaux techniques de weda2.
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé
- **AIPD / impact RGPD** : l'adresse MSSanté professionnelle du praticien passe de Weda à weda2 dans
  le navigateur (`postMessage`, origine vérifiée des deux côtés). Ce n'est pas une donnée de santé.
  Elle n'est ni stockée ni journalisée.

## Branches
- `api-mail` (pushed) : feat/task-362-weda-designated-mailbox — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-362-weda-designated-mailbox
- `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` (snapshot au /start : `feature/nova-rewriting-mss-weda-integration`) — humain gère branche, commit, push, PR TFS
- Partie Weda : hors forge, faite par l'humain (règle 11)

## Develop log

- Repos touched : `api-mail` (catalogue e2e seul), `client-angular` (code-only)
- DTOs published : no DTO change — Interop published : no interop change
- Commits :
  - api-mail : `d7af41e2` test(e2e): add E2E-WEDA-001 — weda2 embedded opens the mailbox Weda designates
  - client-angular : **non commité** (code-only) sur `feature/nova-rewriting-mss-weda-integration`, à
    commiter sur TFS par l'humain **avant** le merge de la PR api-mail (convention
    `test-angular-non-commite` : le scénario E2E-WEDA-001 est `requis` côté angular) :
    - `libs/mss/src/core/tokens/mss-designated-mailbox.token.ts` (nouveau) — `MSS_DESIGNATED_MAILBOX`,
      exporté par `core/index.ts`
    - `libs/mss/src/core/guards/mailbox.guard.ts` (+ spec) — interrogation de l'hôte en parallèle de
      `store.initialize()`, table de la task, `PscRequired` prioritaire, journal
      `[MailboxEntry] designated-mailbox outcome=…` (jamais l'adresse)
    - `libs/mss/src/core/stores/mailbox-session.store.ts` (+ spec) — signal `designatedEmail`,
      `setDesignatedEmail()`, remis à zéro par `clear()` ; jamais dans l'URL
    - `libs/mss/src/core/utils/mailbox-address.util.ts` (+ spec, nouveau) — comparaison sans casse
      ni espaces, partagée par la garde et l'écran
    - `libs/mss/src/features/mailbox-onboarding/*` (+ spec, nouveau) — annonce
      `data-testid="mailbox-onboarding-designated"` et pré-remplissage, tant que le compte ne porte
      pas l'adresse
    - `libs/mss/src/ui/attach-mailbox-form/attach-mailbox-form.component.ts` — entrée `initialEmail`
      (`linkedSignal`), `reset()` inchangé
    - `apps/weda2/src/lib/embedded/designated-mailbox.provider.ts` (+ spec, nouveau) — fourni en mode
      embarqué seulement, `get-mailbox` à 10 s, erreur / adresse vide ou mal formée → `null`
    - `apps/weda2/src/lib/embedded/embedded-host.model.ts` — `'get-mailbox'` ajouté à
      `EmbeddedHostRequestType`
    - `apps/weda2/src/app/app.config.ts` — `MSS_DESIGNATED_MAILBOX` via `designatedMailboxFactory`
    - `e2e/mss-e2e/support/weda-host.ts` (nouveau) — faux hôte Weda (origine
      `https://localhost:44399`, pont v1 `host-capabilities` / `get-mailbox`, contrôles d'origine),
      réutilisable par task-363 ; `support/session.ts` déclare cette origine dans
      `embeddedHostOrigins` de la configuration e2e
    - `e2e/mss-e2e/specs/functional.e2e.ts` — test E2E-WEDA-001 v1
- Local build / test :
  - client-angular : `npm run build` ✓ (weda2) ; `nx run-many -t test` ✓ (11 projets, 0 échec) ;
    `npx tsc --noEmit -p e2e/mss-e2e/tsconfig.json` ✓ ; `eslint` sur les fichiers touchés : 0 erreur
    (avertissements `@example` du style existant) ; Prettier : fichiers neufs formatés, fichiers propres
    en HEAD toujours propres. `mailbox.guard.spec.ts`, `mailbox-session.store.spec.ts` et
    `mss-mailbox-onboarding.component.html` n'étaient pas propres en HEAD : non reformatés.
  - api-mail : `dotnet test HealthPlatform.Api.Mail.sln` ✓ (domain 190, infrastructure 683, api 1 186,
    application 3 569, integration 838 + 16 skip ; aucun FATAL) ; `ScenarioCatalogTests` 17/17
- Tests rouges d'abord (vus rouges avant implémentation) : 9 cas de garde + 1 store + 2 cas de l'écran
  de rattachement.
- Preuve par mutation (code restauré, `grep -c MUTATION` = 0 après chaque) :
  - MG1 garde qui ignore l'adresse désignée → 7 tests de garde rouges (dont « ouvre la boîte désignée
    alors qu'une autre est le défaut », « entrée suivante… rouverte », « journalise… »)
  - MG2 `PscRequired` non prioritaire → « sans session PSC… psc-required » rouge
  - MG3 comparaison sensible à la casse → « compare les adresses sans la casse… » rouge
  - MO1 formulaire sans pré-remplissage → « pré-remplit le champ et l'annonce » et « Ouvrir ouvre la
    boîte désignée » rouges
  - M1 fournisseur fourni hors mode embarqué → « hors mode embarqué, ne fournit pas le jeton » rouge
  - M2 délai par défaut au lieu de 10 s → « envoie get-mailbox… avec un délai de 10 s » rouge
  - M3 validation d'adresse retirée → 4 cas « adresse vide / blanche / mal formée / sans point » rouges
- **E2E-WEDA-001 : non joué pendant le premier passage de `/develop`.** Le backend e2e exige le
  port 5052, alors tenu par l'AppHost de développement de l'humain. La forge ne l'a pas arrêté, et
  l'humain l'a arrêté ensuite. Le port est codé en dur dans `Client/Mobile/e2e/headless/run.mjs` et
  dans `proxy.e2e.conf.json`.
- **Reprise `/develop` pendant `/e2e`** : au premier passage de la voie Angular, E2E-WEDA-001 était
  rouge, aux deux essais. Cause : la page du faux hôte était servie par `route.fulfill`. Chrome la
  classait donc « publique », et son contrôle d'accès au réseau local bloquait l'iframe
  `https://localhost:4200` (« The connection is blocked because it was initiated by a public
  page… »). Le défaut venait du test neuf, pas de weda2.
  - Correctif : le faux hôte est un vrai serveur HTTPS loopback (`startFakeHost`, certificat de
    dev de `run.mjs`), comme le vrai Weda (`https://localhost:44300`).
  - Port `47399` : la plage 44300-44399 est réservée par `http.sys` aux liaisons SSL d'IIS Express.
  - Le test arrête le serveur en `finally`.
  - Vert seul en `--serve-only` (2-3 s).
- Preuve par mutation e2e (`--serve-only`, nouveau bundle servi et 0 `[ERROR]` avant chaque jeu,
  code restauré, `grep -c MUTATION` = 0, vert rejoué après restauration) :
  - ME1 `designatedMailboxFactory` jamais fourni → rouge sur « weda2 a demandé à l'hôte la boîte à
    ouvrir » (aucune demande reçue par l'hôte) ;
  - ME2 garde qui ignore la désignation → rouge sur « l'écran de rattachement annonce la boîte
    désignée » (élément absent : weda2 a ouvert le défaut du compte).
- Passe qualité (/simplify) :
  - client-angular : revue reuse / simplification / efficacité / altitude faite à la main sur le diff.
    Comparaison d'adresses factorisée (`mailbox-address.util.ts`), segments d'écran repris de
    `DECISION_SEGMENTS`. Aucun cleanup restant à appliquer, donc aucune re-validation.
  - api-mail : no simplification applied (catalogue YAML seul)
  - Skipped (contract/excluded) : dtos-mss, interop-cda, sdk, devops, psc-proxy-*
- Partie Weda (hors forge) : `GET /api/nova-mss/mailbox`, gestionnaire `get-mailbox` de
  `nova-mss-host.js`, switch masqué aux secrétaires — **à faire par l'humain** (règle 11).
- DOD self-check : garde (6 lignes de la table) ✓, écran de rattachement ✓, shell ✓ (embarqué
  seulement, `get-mailbox`, délai / not-found / forbidden / adresse vide → null), entrée suivante ✓,
  catalogue E2E-WEDA-001 v1 ✓, `data-testid` sur l'annonce ✓, libellés FR en dur ✓, aucune adresse
  journalisée ✓ (test « journalise l'issue… sans jamais l'adresse »). Différés : parcours e2e joué
  (`/e2e`), partie Weda et Manual Test Plan (HAG).
- Next step : `/sonar task-362`

## Sonar log

- **Skipped** : le diff api-mail vs `develop` se limite à `e2e/scenarios.yml` (catalogue), aucun
  code C# analysable. Même traitement que task-346. KPIs inchangés, aucune analyse lancée.

## Lint log

- Commande : `npx nx affected -t lint --base=origin/next --head=HEAD --parallel=3 --projects=tag:scope:mss`
  (12 projets exécutés).
- Baseline : **0 erreur**, avertissements seuls (préexistants, surtout `jsdoc/require-example`).
- Itérations : 0. Aucun `--fix` lancé, pour ne pas toucher au WIP humain. Aucune modification, donc
  pas de re-build : l'arbre n'a pas bougé depuis le vert de `/develop`.
- Fichiers weda2 (`apps/weda2`, hors `tag:scope:mss`) et e2e : `npx eslint` ciblé pendant `/develop`,
  0 erreur.
- Conventions : aucune règle corrigée à la main, donc `conventions/angular.md` inchangé.

## Timings

*(généré par `tools/timing/report.sh --task task-362 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 17 s | — | — | — | — |
| /develop | ok | 21 min 54 s | 1 (28 s) | 3 (4 min 45 s) | — | client-angular 1B/1T, api-mail 0B/2T, e2e non joué : port 5052 tenu par l'AppHost de l'humain |
| /sonar | skipped | 0.5 s | — | — | — | api-mail : catalogue e2e/scenarios.yml seul, aucun code analysable |
| /lint-angular | ok | 35 s | — | — | — | baseline 0 erreur (warnings seuls), aucun fix |
| /lint-mobile | skipped | 0.5 s | — | — | — | client-mobile non listé ni touché |
| /e2e | ok | 26 min 40 s | — | — | — | e2e ×5 (18 min 36 s), porte verte ; DCP élevé purgé (outillage 1er essai mobile) ; WEDA-001 corrigé en reprise (faux hôte loopback) |
| /review | ok | 4 min 49 s | 2 (13 s) | 2 (4 min 00 s) | — | client-angular 1B/1T, api-mail 1B/1T, APPROVED ; api-mail 1B/1T, client-angular 1B/1T ; PR #285 (awaiting-human-merge) ; client-angular code-only |
| /tech-writer | ok | 52 s | — | — | — | — |
| **Total cycle** | | **55 min 10 s** | **3 (42 s)** | **5 (8 min 45 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : lint ×1 (27 s)

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail touché (catalogue) | ✅ verte | 31 verts, 0 flaky, 0 rouge, 0 quarantaine | 5 min 29 s |
| angular | api-mail + client-angular touchés | ✅ verte à la porte | 31 verts, 0 flaky, 1 rouge **en quarantaine** (E2E-COMPOSE-002, task-350) | 4 min 53 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task (`feat/task-362-weda-designated-mailbox`, `d7af41e2`)
- Quarantaines : E2E-COMPOSE-002 (angular), posée le 2026-10-09 (1 jour), correction task-350
- Divergences ouvertes : aucune
- Parcours touchés sans spec e2e modifié : aucun (`functional.e2e.ts` modifié avec l'écran de rattachement)
- Démontage : complet (ports 5052, 8100, 4200, 3993, 3465, 3143 et 47399 libres, aucun conteneur e2e résiduel)
- Incidents du run :
  - **outillage, 1er essai de la voie mobile** (code 2, 71 s) : l'API DCP d'Aspire refusait les
    connexions (`127.0.0.1:50061`), et le magasin d'état DCP élevé portait un `migrate.lock` de
    0 octet. Purge de `~/.dcp/state.elevated` (état scratch, reconstruit au démarrage), puis voie
    verte ;
  - **1er passage de la voie Angular** (code 1) : E2E-WEDA-001 était rouge, à cause d'un défaut du
    test neuf (faux hôte bloqué par le contrôle d'accès au réseau local de Chrome). Corrigé en
    reprise `/develop`, prouvé par mutation, puis voie rejouée. Voir le Develop log.
  - Le rapport mobile vient du passage vert de ce run. api-mail n'a pas bougé depuis : seul le
    support e2e Angular a changé.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Failed — correction : task-350

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
| E2E-DETAIL-001 | 1 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ❌ | ✅ |
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

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/285 — label `awaiting-human-merge`
- `client-angular` (code-only) : l'humain gère le commit, le push TFS et la PR. Branche
  `feature/nova-rewriting-mss-weda-integration`. **À commiter avant le merge de la PR #285** (test
  E2E-WEDA-001 requis côté angular). Fichiers modifiés (`git diff --name-only` + non suivis) :
  - `front/apps/weda2/src/app/app.config.ts`
  - `front/apps/weda2/src/lib/embedded/embedded-host.model.ts`
  - `front/apps/weda2/src/lib/embedded/designated-mailbox.provider.ts` (nouveau)
  - `front/apps/weda2/src/lib/embedded/designated-mailbox.provider.spec.ts` (nouveau)
  - `front/e2e/mss-e2e/specs/functional.e2e.ts`
  - `front/e2e/mss-e2e/support/session.ts`
  - `front/e2e/mss-e2e/support/weda-host.ts` (nouveau)
  - `front/libs/mss/src/core/guards/mailbox.guard.ts` + `.spec.ts`
  - `front/libs/mss/src/core/index.ts`
  - `front/libs/mss/src/core/stores/mailbox-session.store.ts` + `.spec.ts`
  - `front/libs/mss/src/core/tokens/mss-designated-mailbox.token.ts` (nouveau)
  - `front/libs/mss/src/core/utils/mailbox-address.util.ts` + `.spec.ts` (nouveaux)
  - `front/libs/mss/src/features/mailbox-onboarding/mss-mailbox-onboarding.component.{ts,html,scss}`
  - `front/libs/mss/src/features/mailbox-onboarding/mss-mailbox-onboarding.component.spec.ts` (nouveau)
  - `front/libs/mss/src/ui/attach-mailbox-form/attach-mailbox-form.component.ts`
- Partie Weda (hors forge) : à faire par l'humain (règle 11), validée par le Manual Test Plan.

## Code Review Summary

**Verdict : APPROVED**, 0 bloquant, 2 suggestions.

| Repo | Build | Tests | Re-validation `/review` |
|---|---|---|---|
| api-mail | ✓ 0 erreur | ✓ domain 190, infrastructure 683, api 1 186, application 3 569, integration 838 (+16 skip), 0 échec, aucun FATAL | identique à `/develop` |
| client-angular | ✓ `nx build weda2` | ✓ 11 projets, 0 échec | identique à `/develop` |

- **Règle 1b** : côté api-mail, seul le catalogue `e2e/scenarios.yml` change, aucun endpoint.
  Côté frontend, le parcours est prouvé par E2E-WEDA-001 sur le vrai backend : vert à la porte,
  rouge sous ME1 (fournisseur absent) et sous ME2 (garde qui ignore la désignation).
- **DOD** :
  - ✓ garde (6 cas de la table) ;
  - ✓ écran de rattachement (pré-remplissage, annonce, « Ouvrir » ouvre la boîte désignée) ;
  - ✓ shell (embarqué seulement, `get-mailbox` à 10 s, erreurs et adresses invalides → `null`) ;
  - ✓ entrée suivante ;
  - ✓ E2E-WEDA-001 v1 au catalogue et implémenté côté angular ;
  - ✓ `data-testid` sur l'annonce, libellés FR en dur ;
  - ✓ aucune adresse dans les journaux de weda2 (test dédié) ;
  - différés au HAG : partie Weda, repère `nova-mss` (`git diff --stat` du dépôt Weda) et Manual
    Test Plan.
- Revue par fichier (client-angular) :
  - `mailbox.guard.ts` ✅ :
    - demande parallèle à l'hôte ;
    - `PscRequired` prioritaire ;
    - adresse en mémoire seulement, jamais dans l'URL ;
    - journal sans adresse ;
    - fonctions courtes, JSDoc complet.
  - `mailbox-session.store.ts` ✅ : `clear()` remet l'adresse à zéro.
  - `designated-mailbox.provider.ts` ✅ : ne rejette jamais, valide la forme de l'adresse, n'est
    fourni qu'en mode embarqué.
  - `attach-mailbox-form` / `mss-mailbox-onboarding` ✅ : `linkedSignal` pour le pré-remplissage,
    et l'annonce disparaît dès que le compte porte l'adresse.
  - `weda-host.ts` ✅ : vrai serveur loopback avec contrôles d'origine, fermé en `finally`.
- ⚠️ Suggestions (non bloquantes, décision produit) :
  1. **Aucune sortie depuis l'écran de rattachement d'une boîte désignée.** Si le rattachement
     échoue (refus de l'opérateur, identité non concordante), toute entrée dans le module ramène
     sur cet écran : le praticien embarqué n'atteint plus ses autres boîtes. La task ne le prévoit
     pas. Weda ne désigne que la boîte de l'utilisateur lui-même, donc le cas devrait rester rare.
     Piste : un lien « Choisir une autre messagerie » vers `/select`.
  2. Le titre de l'écran reste « Rattachez votre première messagerie MSSanté », même quand le
     compte porte déjà d'autres boîtes.

## Merged

- **Date** : 2026-10-10, par `/merge task-362 --i-tested` (validation manuelle attestée par l'humain).
- `api-mail` : PR #285 squash-mergée dans `develop`, commit `f1eeb6e6ee84b970c3914909f66622316e0c9ac1`
  (catalogue e2e : E2E-WEDA-001). Label `awaiting-human-merge` retiré. Branche
  `feat/task-362-weda-designated-mailbox` supprimée (distante et locale).
- CI `develop` : verte (build, publish) —
  https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/38047028036
- `client-angular` : géré manuellement par l'humain (TFS).
- Partie Weda (hors forge), branche `lotus/segur/17546-enveloppe-segur-v2-with-mss-api` :
  - `1fcc554f69` — périphérique « Expérience Nova » (9892), `NovaMssHost.ascx` et `api/nova-mss` fermés sans lui ;
  - `d1208993c4` — `GET api/nova-mss/mailbox` et gestionnaire `get-mailbox` du pont, bandeau refusé aux secrétaires ;
  - `868d1a24f2` — fichiers `nova-mss` en UTF-8 avec BOM.
