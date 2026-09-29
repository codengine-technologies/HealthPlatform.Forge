# todo-task-346.md — Filet e2e headless client-angular : les écrans de messagerie de weda2 rejoués contre le vrai backend

**Repos**: client-angular, api-mail *(catalogue `Api/Mail/e2e/scenarios.yml` et contrôle de parité uniquement — aucun code applicatif api-mail)*
**Dependencies**: done-task-345
**Epic**: E018
**Single frontend**: true
**Priorité**: **2**

> **Contexte.** `client-angular` n'a **aucun** outillage e2e : pas de Playwright, Cypress ni
> Protractor, seulement Vitest pour l'unitaire. Le module messagerie (`@weda/mss`, projets
> `scope:mss`) n'est servi que par l'app hôte **`weda2`**, sur la route `/messagerie`. L'app
> autonome `apps/mss` n'est pas utilisable en l'état : nom de projet incohérent, providers
> manquants, `environment.prod.ts` absent. Elle n'est **pas** la cible.
>
> **Repo code-only** : la forge écrit le code sur la branche actuellement checked out dans
> `Client/Angular/`. **L'humain** crée la branche, commite, pousse vers TFS et ouvre la PR.

## Objective

Doter le module messagerie de `weda2` d'une suite Playwright **headless** qui rejoue les parcours
principaux du médecin contre le **même backend `e2e`** que la task-345 (profil AppHost, seed
déterministe, bypass api-mail), **sans modifier le code applicatif**.

L'authentification de l'hôte `weda2` est simulée au niveau réseau par Playwright :
- les appels au psc-auth-proxy (`session/has-session`, `session/token`, `auth/refresh`, logout) sont
  servis avec un jeton non signé à échéance lointaine, ce que le client accepte puisqu'il ne vérifie
  jamais la signature ;
- les appels du shell vers le back weda (`:7249`) sont bouchonnés.

Les appels vers api-mail sont, eux, **réels** : Playwright y pose les en-têtes du bypass
(`X-Test-Bypass`, `Client-Email` toujours présent, `Client-Psc-Sub`, `Client-Rpps`) et conserve le
`Client-Session-Id` de l'app.

### Règles

1. **Emplacement** : un projet e2e dans le workspace Nx, **tagué `scope:mss`**, par exemple
   `mss-e2e`, pour que `/lint-angular` le couvre.
2. **Cible** : `weda2` servi en HTTPS local ; `mssApiUrl` pointe sur l'API du profil `e2e` par
   surcharge d'exécution (`assets/config.json` ou équivalent de test). **Aucune modification des
   `environment.*.ts` versionnés.**
3. **Périmètre fixé par le catalogue**, pas par cette task. Angular implémente **tout scénario
   `angular: requis`** de `Api/Mail/e2e/scenarios.yml` en `mode: headless`, chacun avec son tag
   `@E2E-…` et son annotation `version`.
   - **Confirmation de la colonne `angular`**, pré-remplie par la task-345. Un scénario ne peut passer
     `non-applicable` qu'avec une raison **fonctionnelle** : l'écran ou le geste n'existe pas dans
     `weda2`. « Plus difficile à tester » n'en est pas une.
   - Tout reclassement se fait **dans le catalogue**, dans la PR api-mail de cette task, jamais par une
     simple absence de test.
   - **Socle attendu à titre indicatif** : ouverture de la boîte par défaut ; filtres et recherche de
     l'inbox ; lecture, y compris d'un mail avec PJ ; lu / non lu et flag ; déplacement vers Archive
     et retour ; brouillons ; envoyer puis recevoir ; acquittement d'un compte rendu de biologie ;
     contacts.
   - Un parcours qui n'existe **qu'en Angular** entre au catalogue avec `mobile: non-applicable —
     {raison}`.
4. **Mêmes exclusions que la task-345** : pas de login PSC, pas de refresh par cookie, pas d'Annuaire
   Santé national, aucune dépendance réseau externe.
5. **Commande unique** depuis `Client/Angular/front/`, par exemple `npm run e2e:mss`. Elle réutilise
   le script de montage et de démontage du backend `e2e` livré par la task-345, au lieu de le
   dupliquer. Code retour non nul sur échec, et un rapport JSON au **même format** que celui du
   mobile.
6. **Stabilité** : `retries: 1`, flaky signalé ; rouge deux fois = run en échec.
7. **Aucun code de test, aucune clé ni aucun intercepteur de bypass dans `apps/` ou `libs/`.**

### Hors périmètre

- La réparation de l'app autonome `apps/mss`.
- Le pipeline Azure / TFS : l'intégration du run e2e dans la CI TFS est une décision de l'humain.
- Les écrans hors messagerie de `weda2`.

## Definition of Done

- [ ] Build passes (0 errors) — `cd Client/Angular/front && npm ci && npm run build`
- [ ] Tests pass (0 failures) — `npm test`
- [ ] `@playwright/test` ajouté en devDependency ; projet e2e tagué `scope:mss`
- [ ] Faux psc-auth-proxy et bouchons du back weda implémentés dans le support e2e uniquement — `grep` sur `apps/` et `libs/` : aucune occurrence de `X-Test-Bypass`
- [ ] `npm run e2e:mss` : **tous les scénarios `angular: requis` / `mode: headless`** du catalogue verts en headless contre le backend `e2e` — log consigné dans le task file
- [ ] Colonne `angular` du catalogue confirmée : chaque `non-applicable` porte une raison fonctionnelle ; reclassements faits dans la PR api-mail
- [ ] Contrôle de parité étendu au rapport Angular et **vert sur les deux colonnes** ; matrice mobile × Angular consignée dans le task file
- [ ] Rendu du rapport Angular au format accepté par le contrôle de parité (tags et annotation `version`)
- [ ] **Preuve que le filet mord** : une régression volontaire dans `libs/mss` fait échouer au moins un test, puis est annulée ; log rouge consigné
- [ ] Run vert deux fois de suite sur un état vierge, sans flaky
- [ ] Rapport JSON au même format que le mobile (task-345)
- [ ] Démontage garanti après un run vert comme après un run rouge
- [ ] `ng lint` du projet e2e sans erreur (scope `scope:mss`)
- [ ] README e2e du module messagerie : prérequis, commande, périmètre et exclusions
- [ ] **Code-only respecté** : aucune opération git dans `Client/Angular/`, liste des fichiers modifiés remise à l'humain

## Manual Test Plan

1. Docker démarré. Dans `Client/Angular/`, se placer sur la branche de travail voulue (humain).
2. `cd Client/Angular/front && npm run e2e:mss`.
3. Attendu : le backend `e2e` monte, `weda2` est servi, la suite tourne sans fenêtre ni login et
   atteint `/messagerie` directement. Tous les tests passent, code retour 0.
3 bis. Lancer le contrôle de parité sur les rapports mobile et Angular : la matrice montre chaque
   scénario sur les deux colonnes, sans trou, et chaque `non-applicable` avec sa raison.
4. Aucun conteneur, `dotnet` ni serveur de dev résiduel après le run.
5. Casser volontairement un filtre de l'inbox dans `libs/mss`, relancer : test rouge, code retour ≠ 0.
   Annuler.
6. `npm start` classique (vrai login) : l'app `weda2` se comporte exactement comme avant.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville, biologie — protège des parcours existants
- **Vague Ségur** : hors Ségur — outillage de non-régression
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — données synthétiques du seed e2e uniquement
- **Authentification PS** : inchangée en production. La session de l'hôte est simulée **dans le navigateur de test seulement** ; le bypass api-mail reste bloqué en Production et activé par une clé fournie à l'exécution (task-345).
- **Habilitations** : praticien synthétique ; aucun RPPS réel
- **Interop CI-SIS** : CDA r2 CR de biologie des jeux de test, via la pipeline existante
- **Tracé PGSSI-S** : inchangé — journal dans le registre isolé `mss_registry_e2e`, détruit avec le run
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — poste de développement ; interdiction d'exécution sur un environnement HDS
- **AIPD / impact RGPD** : inchangé

## Branches
- `api-mail` (pushed) : feat/task-346-filet-e2e-headless-angular — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-346-filet-e2e-headless-angular
- `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` (au /start : `feature/nova-rewriting-mss`, avec 2 réglages locaux non commités dans `apps/{mss,weda2}/src/environments/environment.ts` — laissés intacts) — humain gère branche, commit, push, PR TFS

## Timings

*(généré par `tools/timing/report.sh --task task-346 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 25 s | — | — | — | api-mail, client-angular (code-only) |
| /develop | ok | 15 min 05 s | 2 (27 s) | 13 (37 min 56 s) | — | client-angular 2B/12T, client-mobile 0B/1T, reprise après review : 5 bloquants, 4 mutations → 4 rouges, 22/22 ×2 |
| /sonar | skipped | 0.4 s | — | — | — | api-mail : e2e/README.md + commentaires scenarios.yml, aucun code |
| /lint-angular | ok | 21 s | — | — | — | 0 erreur (re-lint après reprise) |
| /lint-mobile | skipped | 0.5 s | — | — | — | client-mobile non touché |
| /verify-visual | skipped | 0.4 s | — | — | — | client-mobile non touché |
| /review | ok | 3 min 07 s | 4 (14 s) | 4 (4 min 18 s) | — | api-mail 2B/2T, client-angular 2B/2T, APPROVED (2e passage), PR api-mail #260, angular code-only |
| **Total cycle** | | **19 min 01 s** | **6 (42 s)** | **17 (42 min 14 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : lint ×3 (59 s), restore ×2 (1 min 18 s)

## Develop log

- Repos touched : client-angular (code-only, aucune opération git), api-mail (documentation du catalogue)
- DTOs published : no DTO change — Interop : no change
- **Projet `mss-e2e`** (`Client/Angular/front/e2e/mss-e2e/`, tags `scope:mss`, `type:e2e`, cibles `e2e` et `lint`) : placé **hors d'`apps/` et de `libs/`**, pour que la règle 7 et le `grep` de la DOD tiennent à la lettre. `@playwright/test` 1.61.1 en devDependency (même version que le mobile). Commande : `npm run e2e:mss`.
- **Réutilisation, sans duplication (règle 5)** : `run.mjs` délègue le cycle de vie du backend e2e (AppHost `https-e2e`, reset, seed relu, démontage borné au run) au mode `--serve-only` de l'orchestrateur de la task-345. Il se limite à servir weda2 en HTTPS local, avec le proxy `/api` → backend e2e (évite le contenu mixte). Il joue ensuite la suite, contrôle la parité sur la colonne `angular`, puis dépose `STOP`. Rapport `out/summary.json` au format du mobile.
- **Auth simulée** (`support/session.ts`, Playwright uniquement) :
  - à froid, weda2 part au login ; le faux `/auth/login` redirige aussitôt vers le callback `/authentication` avec un code et le `state` reçu ;
  - l'échange `POST /auth/token` rend un JWT **non signé** portant le `nonce` reçu ; weda2 le lit sans le vérifier ;
  - les réponses simulées portent les en-têtes CORS : le proxy est cross-origin et appelé `withCredentials` ;
  - `assets/config.json` est servi surchargé (`mssApiUrl` = origine de l'app) ; le back weda `:7249` est bouchonné ; tout hôte extérieur est coupé ;
  - les en-têtes du bypass ne visent que `origine/api/**`.
- **Navigation** : weda2 ne conserve pas ses jetons entre deux chargements. Chaque `goto` rejoue donc le login simulé, puis la navigation se fait **dans l'app** (`pushState` + `popstate`). « Relu après rechargement » signifie un rechargement complet.
- **Couverture** : les 22 scénarios `angular: requis` / `mode: headless` du catalogue ; les 3 `mode: humain` sont « non joués ». Les états optimistes (lu, signalé, acquittement, suppressions) sont jugés sur la **réponse du serveur**, puis relus après rechargement.
- **Colonne `angular` confirmée, aucun reclassement** : tous les écrans existent dans weda2. Deux réalisations propres à weda2, consignées dans `Api/Mail/e2e/README.md` sans changer le scénario :
  - `E2E-INBOX-001` : filtres rapides « Tous / Non lus / Lus », pas de « Signalés » ;
  - `E2E-SETTINGS-002` : la vue conversation se règle dans les Paramètres.
- **Runs `npm run e2e:mss`** : 22/22 verts, 0 flaky, parité verte, ~2 min 30 par run, `docker ps -a` identique avant/après.
  - 1 run initial, 2 après la passe qualité, **2 consécutifs après le déplacement hors d'`apps/`**.
- **Preuve que le filet mord** — 6 no-ops plantés dans `libs/mss/src/core/services/mss-api.service.ts` : `updateReadStatus`, `updateFlagStatus`, `recordBiologyAck`, `deleteSignature`, `deleteContact`, `deleteFolder`.
  - Résultat : **exactement les 6 parcours visés rouges** (MAIL-001, MAIL-003, BIO-001, FOLDER-002, CONTACT-002, SIGNATURE-001), 16 verts, code retour 1.
  - Contact et signature disparaissent de l'écran de façon optimiste : seule la relecture après rechargement les attrape.
  - Fichier restauré, `libs/` intact.
- **Matrice de parité mobile × Angular** (suite mobile rejouée pour un rapport frais, 22/22) : **verte sur les deux colonnes**.
  - 22 scénarios headless ✅ ✅ ; CONTACT-001, AUTH-001, AUTH-002 « 👤 non joué (humain) » sur les deux colonnes.
- **Build / test Angular** : `npm ci` ✓ ; `npm run build` ✓ (deux fois, dont après le déplacement) ; `npm test` ✓ (11 projets : 131 fichiers de tests verts, 1 sauté préexistant).
- `ng lint` du projet e2e : **0 erreur**. Restent 23 avertissements `jsdoc/require-example`, règle optionnelle du workspace. `tsconfig.json` racine : `e2e/**/*.ts` ajouté à `include`, pour le parser ESLint.
- `grep -i x-test-bypass` sur `apps/` et `libs/` : **aucune occurrence**.
- Passe qualité (§Q, sans git sur client-angular) : les prédicats « toutes les lignes lues / non lues » (×3) et `rowAction` sont extraits dans `support/weda.ts`. Re-validés par 2 runs verts. api-mail : documentation seulement, rien à simplifier.
- Commits api-mail poussés : `70dac50f`, `19bc3b58` (`e2e/README.md`).
- **client-angular — code-only, fichiers à commiter par l'humain** (branche `feature/nova-rewriting-mss`) :
  - `front/e2e/mss-e2e/` : nouveau projet (`.gitignore`, `README.md`, `playwright.config.ts`, `project.json`, `proxy.e2e.conf.json`, `run.mjs`, `specs/functional.e2e.ts`, `support/{fixtures,session,weda}.ts`, `tsconfig.json`) ;
  - `front/package.json` et `front/package-lock.json` : devDependency `@playwright/test`, script `e2e:mss` ;
  - `front/tsconfig.json` : `include` étendu à `e2e/**/*.ts` ;
  - à **ne pas** inclure : `front/apps/{mss,weda2}/src/environments/environment.ts`, réglages locaux de l'humain, antérieurs au `/start`, laissés intacts.
- **Constat pour le PO** : weda2 ne conserve pas sa session d'un rechargement à l'autre ; chaque F5 repasse par le login PSC, même si le SSO le rend transparent. Et comme sur le mobile, une suppression de mail est différée de 6 s (fenêtre d'annulation).
- Next step : `/sonar task-346`

### Reprise du 2026-09-29 (après /review CHANGES REQUESTED)

- **5 bloquants corrigés** :
  - DRAFT-001 : réponse du `DELETE` exigée ; `openFolder` attend désormais la fin du chargement de la liste, donc une absence n'est plus lue pendant le spinner, et cela vaut pour tous les parcours ;
  - SIGNATURE-001 : ancre `.sig-empty`, liste vide chargée, en cours de parcours puis après rechargement ;
  - `run.mjs` : `session.env` et `STOP` périmés supprimés avant le lancement du backend ;
  - INBOX-001 : la recherche s'ouvre (`mail-search-dropdown`), et les réalisations weda2 sont portées en commentaire dans `scenarios.yml` sans monter la version (INBOX-001, SETTINGS-002) ;
  - DETAIL-002 : le corps est lu dans l'iframe HTML, puis dans le texte brut, puis de nouveau en HTML.
- **Suggestions appliquées** :
  - SETTINGS-001/002 restaurent le réglage en `finally` ;
  - SEARCH-001 exige la requête `/api/v1/search/` portant les termes saisis ;
  - code 2 quand Playwright ne produit aucun rapport ;
  - README : `npm ci` du mobile requis.
- **Suggestion écartée** : retries sur les tests qui mutent l'état seedé. Un rejeu ne peut pas « sauver » un parcours qui a déjà muté l'état ; c'est accepté : un rouge au 1er essai reste un rouge.
- **Preuve par mutation** : 4 no-ops (`deleteDraft`, `deleteSignature`, `semanticSearch`, `togglePlainText`). **Exactement DETAIL-002, SEARCH-001, DRAFT-001 et SIGNATURE-001 rouges**, chacun sur sa nouvelle assertion ; 18 verts. `libs/` restauré (`git status front/libs` vide).
- **Runs** : 22/22 verts **deux fois de suite**, 0 flaky, parité verte, conteneurs intacts.
- Commit api-mail poussé : `52c5b662` (`scenarios.yml` commentaires + README).
- client-angular : mêmes fichiers à commiter par l'humain que ci-dessus (`front/e2e/mss-e2e/**`, `front/package.json`, `front/package-lock.json`, `front/tsconfig.json`).
- Next step : `/sonar task-346`

## Sonar log

- `/sonar` : **skipped** — la branche api-mail ne touche que `e2e/README.md`, sans aucun code C# à analyser.
- Qualité : /sonar skipped — api-mail sans changement de code.

## Lint log

- `/lint-angular` : ✓ **0 erreur** dès la baseline sur `tag:scope:mss` (`mss`, `mss-lib`, `mss-e2e`) — 0 itération, aucun fichier modifié.
  - 23 avertissements sur `mss-e2e` (`jsdoc/require-example`, règle optionnelle) et 41 avertissements préexistants ailleurs dans le périmètre.
  - Code-only : aucune opération git.
- `/lint-mobile` : skipped — client-mobile non touché par la task.

## Visual verify log

- `/verify-visual` : **skipped** — client-mobile non touché, aucun écran redessiné.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/260 — label `awaiting-human-merge` (documentation du catalogue).
- `client-angular` : **code-only**. L'humain gère le commit, le push TFS et l'ouverture de la PR, sur la branche `feature/nova-rewriting-mss`. Fichiers à commiter :
  - `front/package-lock.json`
  - `front/package.json`
  - `front/tsconfig.json`
  - `front/e2e/mss-e2e/.gitignore`
  - `front/e2e/mss-e2e/README.md`
  - `front/e2e/mss-e2e/playwright.config.ts`
  - `front/e2e/mss-e2e/project.json`
  - `front/e2e/mss-e2e/proxy.e2e.conf.json`
  - `front/e2e/mss-e2e/run.mjs`
  - `front/e2e/mss-e2e/specs/functional.e2e.ts`
  - `front/e2e/mss-e2e/support/fixtures.ts`
  - `front/e2e/mss-e2e/support/session.ts`
  - `front/e2e/mss-e2e/support/weda.ts`
  - `front/e2e/mss-e2e/tsconfig.json`
  - **À ne pas inclure** : `front/apps/{mss,weda2}/src/environments/environment.ts`, réglages locaux de l'humain, antérieurs au `/start`.

## Code Review Summary

- Verdict : **APPROVED** au 2e passage (revue indépendante), le 2026-09-29.
- 1er passage : CHANGES REQUESTED, 5 bloquants, tous corrigés :
  - verts lus pendant un chargement (brouillons, signatures) ;
  - `session.env` périmé ;
  - INBOX-001 : recherche non ouverte, écarts absents du catalogue ;
  - DETAIL-002 : corps non vérifié.
- Preuve : 6 + 4 no-ops dans `libs/mss` font échouer exactement les 10 parcours visés, puis 22/22 verts deux fois de suite ; matrice mobile × Angular verte.
- Validation :
  - api-mail : 5 849/5 849 (16 ignorés préexistants) ;
  - Angular : `npm ci`, build et tests verts (11 projets) ;
  - lint `scope:mss` : 0 erreur ;
  - aucune occurrence du bypass dans `apps/` ni `libs/`.
- Suggestions restantes, non bloquantes :
  - protéger le `finally` de SETTINGS-001/002 contre une page qui n'est pas sur les Paramètres ;
  - attendre `.mail-list-empty` dans Brouillons.
