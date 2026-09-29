# E018 — Changelogs (vue ingénierie)

> **Audience** : équipes techniques, backlog, dette.
> Vue produit : [E018-filet-de-non-regression-fonctionnel.md](E018-filet-de-non-regression-fonctionnel.md).
> **Dernière mise à jour** : 2026-09-29 (v1.2)

---

## Historique détaillé des changelogs

### v1.0 — Filet e2e headless client-mobile, backend e2e et catalogue de scénarios — task-345

- **Task** : task-345, statut `archived` (mergée le 2026-09-29).
- **PRs** : `api-mail` #259 et `client-mobile` #81, label `awaiting-human-merge`, branche
  `feat/task-345-filet-e2e-headless-mobile`.
- **Backend e2e (api-mail)** :
  - Profil AppHost `https-e2e` (`MSS_E2E=true`), résolu par `src/AppHost/E2eProfile.cs`.
  - La clé `MSS_E2E_BYPASS_KEY` est obligatoire et n'a aucune valeur par défaut.
  - Le profil est exclusif du profil `MSS_LOADTEST` et utilise le registre dédié `mss_registry_e2e`.
  - Dovecot et GreenMail sont factorisés avec le banc de charge (`AddBenchDovecot` / `AddBenchGreenMail`), sans volume.
  - Relais SMTP→IMAP `e2e-relay`, déclaré par chemin : les autres profils ne compilent pas l'outillage.
  - `MSS_E2E_PASSWORD` retiré, car la passdb statique de Dovecot ne suivait pas une surcharge.
- **Outillage `tests/mss.mail.e2e`** : sous-commandes `reset`, `seed`, `relay` et `parity`.
  - Codes retour : 0 succès, 1 échec vérifié, 2 outillage ou interruption.
  - Seed déterministe (`E2eSeedPlan`) : 7 messages, dont le CR de biologie TSH du corpus ANS, un dossier Archive et un contact.
  - Le seed relit tout ce qu'il écrit : boîte sélectionnable, CR servi par la base avec son document CDA.
  - Le seed liste les dossiers avant l'enrichissement, pour contourner la génération UIDVALIDITY 0 d'`AddNewMail` (même remède que la chauffe du banc, `f209ce8`).
- **Catalogue** : `Api/Mail/e2e/scenarios.yml` contient 25 scénarios `E2E-{DOMAINE}-{NNN}`, requis pour `mobile` et `angular`.
  - 3 scénarios sont en `mode: humain` : CONTACT-001, AUTH-001 et AUTH-002.
  - Le chargement est strict. Depuis la 2e review, il refuse aussi un scénario muet sur un client du catalogue.
  - Le contrôle de parité confronte ce catalogue au rapport Playwright **exécuté** et produit une matrice Markdown.
- **Client-mobile** : la commande `npm run e2e:headless` lance l'orchestrateur `e2e/headless/run.mjs`, qui enchaîne :
  pré-vol → build → `ng serve` (proxy e2e) → reset → AppHost → seed → Playwright → parité → démontage.
  - Le projet Playwright `headless` utilise le canal `chrome`, sans vidéo, avec 1 retry (un flaky reste visible).
  - La session est simulée dans le stockage du navigateur. Les en-têtes du bypass ne visent que l'origine de l'app.
  - Aucune occurrence du bypass sous `src/`.
- **Défauts produit corrigés** (test rouge d'abord) :
  - `EmailBuildingService.MapHeaderFields` pose maintenant `AttachmentCount`, ce qui rétablit le badge trombone sur la liste servie par IMAP.
  - La page inbox ferme le menu des dossiers après un choix.
- **Reviews** : 2 CHANGES REQUESTED, puis APPROVED au 3e passage.
  - Démontage : il ne retire que les conteneurs apparus pendant le run, et échoue fermé si `docker ps -a` échoue.
  - Signaux gérés : SIGTERM, SIGHUP et SIGBREAK.
  - 15 parcours durcis. Lu, flag et acquittement bio sont désormais relus du serveur, car l'UI est optimiste.
- **Preuve par mutation** : 12 no-ops plantés dans `MssApiService` font échouer exactement les 10 parcours visés.
  - Les no-ops portent sur les suppressions (contact, signature, groupe, dossier, mail, brouillon), l'acquittement et les statuts lu/non-lu/flag.
  - Ensuite, **22/22 verts deux fois de suite**, 0 flaky, parité verte, environ 3 min par run.
  - `docker ps -a` est identique avant et après chacun des 7 runs.
- **Tests** : api-mail 5 849 verts (16 ignorés préexistants), client-mobile 947/947.
- **Sonar** : Quality Gate OK, new_coverage 98,3 %, 0 finding sur les lignes de la branche (1 CA1859 corrigé).
- **Limites et constats routés au PO** :
  - `MailPendingDeleteService` ne vide pas sa file au déchargement de la page : une suppression est perdue si l'app est rechargée dans les 6 s.
  - `AddNewMail` estampille la génération 0 sans le signaler.
  - `AttachmentCount` n'est pas posé par `BackgroundEnrichmentProcessor.cs:314` ni `MailRepository.cs:3295`.
  - `SentDate` utilise `LocalDateTime` (famille AUD-28).
  - « Aucun contenu disponible » s'affiche pendant le chargement du détail.
  - DOD « run vert réseau Internet coupé » reportée au test humain.

### v1.1 — Filet e2e headless client-angular (module messagerie de weda2) — task-346

- **Task** : task-346, statut `archived` (mergée le 2026-09-29 ; code Angular à pousser sur TFS par l'humain).
- **PRs** :
  - `api-mail` #260, label `awaiting-human-merge` : documentation seulement, `e2e/README.md` et commentaires dans `scenarios.yml`.
  - `client-angular` : **code-only**. L'humain commite et pousse vers TFS sur `feature/nova-rewriting-mss` ; liste des fichiers dans le task file.
- **Projet Nx `mss-e2e`** : `Client/Angular/front/e2e/mss-e2e/`, tags `scope:mss` et `type:e2e`, cibles `e2e` et `lint`.
  - Placé **hors d'`apps/` et `libs/`** : aucune occurrence du bypass dans le code applicatif.
  - `@playwright/test` 1.61.1 en devDependency ; `tsconfig.json` racine avec `include` étendu à `e2e/**/*.ts`.
  - Commande `npm run e2e:mss`.
- **`run.mjs`** : délègue le backend e2e au mode `--serve-only` de `Client/Mobile/e2e/headless/run.mjs` (task-345), sans duplication.
  - Sert weda2 en HTTPS `:4200`, avec le proxy `/api` → `:5052` qui évite le contenu mixte.
  - Contrôle la parité sur la colonne `angular`.
  - Démonte par `STOP` : attente synchrone par `process.kill(pid, 0)`, car la boucle d'événements est bloquée.
  - Purge les `session.env` et `STOP` périmés ; sort en code 2 si Playwright ne produit aucun rapport.
- **Auth simulée** (`support/session.ts`) :
  - faux psc-auth-proxy : `/auth/login` en 302 vers `/authentication?code&state`, puis `POST /auth/token` rend un JWT `alg: none` qui recopie le `nonce` ;
  - en-têtes CORS sur les réponses simulées, car le proxy est appelé en cross-origin avec `withCredentials` ;
  - `assets/config.json` surchargé (`mssApiUrl` = origine) ;
  - back weda `:7249` en 204 ; hôtes extérieurs coupés ; en-têtes du bypass sur `origine/api/**` seulement.
- **Navigation** (`support/weda.ts`) : `pushState` + `popstate`, car weda2 ne persiste pas ses jetons.
  - `openFolder` attend la fin du chargement (`.mail-list-loading` à zéro) ;
  - états optimistes relus du serveur : réponse de l'appel, puis rechargement.
- **Couverture** : 22 scénarios `angular: requis` en `mode: headless`, aucun reclassement.
  - Réalisations weda2 notées en commentaire dans le catalogue, sans montée de version : INBOX-001 (filtres Tous / Non lus / Lus) et SETTINGS-002 (vue conversation dans les Paramètres).
- **Preuves** — 10 no-ops dans `libs/mss`, en deux lots, font échouer exactement les 10 parcours visés :
  - lot 1 : `updateReadStatus`, `updateFlagStatus`, `recordBiologyAck`, `deleteSignature`, `deleteContact`, `deleteFolder` ;
  - lot 2 : `deleteDraft`, `deleteSignature`, `semanticSearch`, `togglePlainText`.
- **Résultats** : **22/22 verts deux fois de suite**, 0 flaky, environ 2 min 30 par run ; `docker ps -a` identique avant et après chaque run.
  - Matrice de parité mobile × Angular **verte sur les deux colonnes**.
- **Tests** : api-mail 5 849 verts (16 ignorés préexistants) ; Angular `npm ci`, build et tests verts (11 projets, 131 fichiers) ; lint `scope:mss` 0 erreur.
- **Revue** : 1 CHANGES REQUESTED, 5 bloquants corrigés, puis APPROVED.
  - Bloquants : verts lus pendant un chargement, `session.env` périmé, recherche non ouverte, corps non vérifié, écarts absents du catalogue.
  - Suggestions restantes : protéger le `finally` de SETTINGS-001/002 ; attendre `.mail-list-empty` dans Brouillons.
- **Constat PO** : weda2 ne conserve pas sa session d'un rechargement à l'autre, chaque rechargement repasse par le login PSC. Suppression de mail différée de 6 s, comme sur le mobile.

### v1.2 — Étape `/e2e` bloquante dans la chaîne autonome, porte `gate` — task-347

- **Task** : task-347, statut `archived` (mergée le 2026-09-29, `f8e3bef0`).
- **PRs** : `api-mail` #262, label `awaiting-human-merge`, branche `feat/task-347-etape-e2e-bloquante`. Plan de contrôle poussé sur `develop` sans PR (règle 5), `bad1a7a` puis `b44830c`.
- **Chaîne** : `/start → /develop → /sonar → /lint-angular → /lint-mobile → /e2e → /review → /tech-writer`.
  - `/verify-visual` **sort de la chaîne** (décision humaine) : 66 logs, jamais bloquant, outillage absent depuis environ task-274. Il reste disponible à la demande.
- **Étape `/e2e`** (`agents/e2e.md`, `.claude/commands/e2e.md`) :
  - voie mobile si `api-mail`, `client-mobile` ou `dtos-mss` est touché ; voie Angular si `api-mail`, `client-angular` ou `dtos-mss` est touché ;
  - un client non touché est **listé** (`playwright test --list`), sans être rejoué ;
  - bloquante sans exemption ; seul l'humain pose une quarantaine (tag `@quarantaine` + annotation citant la task) ;
  - la porte qui sort en 2 (outillage) bloque aussi ; démontage vérifié ; mesure `--kind e2e`.
- **Double verrou** : `/review` refuse d'ouvrir une PR sans `## E2E log` vert quand une voie est touchée, et recopie le log dans chaque PR (`## Parcours e2e`).
- **Porte `gate`** (`tests/mss.mail.e2e/Parity/E2eGate.cs`) : codes 0 vert, 1 rouge, 2 outillage.
  - Bloque sur un écart de parité, un test rouge hors quarantaine, ou une quarantaine sans `task-NNN`.
  - Liste sans bloquer les flaky, les quarantaines et les divergences (y compris « à retirer »).
  - Valide ses entrées : au moins un rapport exécuté, et un listing qui ne contient aucun test joué.
- **Parité** : état `Listed` (📋) ; divergences temporaires au catalogue (`divergences: { client: { raison, tache } }`), limitées à un client requis, qui tolèrent une version périmée ou un test absent pour ce client seul.
- **Règle d'or** « la forge s'améliore toujours », gravée en tête de CLAUDE.md :
  - `conventions/e2e.md` : 10 conventions, registres des flaky, des quarantaines et des trous du filet ;
  - `/develop` Step 6b : lecture des conventions, catalogue avant les tests, preuve par mutation ;
  - `/review` : section « Amélioration continue » au rapport ; `/po` : clause de DOD e2e et ligne « trou du filet ».
- **Preuves** (tasks jetables 990 à 992, supprimées ensuite) :
  - skip mesuré ;
  - régression (filtre « Non lus » cassé) : E2E-INBOX-001 rouge, chaîne arrêtée, aucune PR ;
  - parité (catalogue v2, seul le mobile suit) : `[angular] StaleVersion`, chaîne arrêtée.
- **Tests** : api-mail 5 872 verts (16 ignorés préexistants), dont 17 tests de porte.
- **Sonar** : Quality Gate OK, new_coverage 98,3 %, 0 finding sur la branche.
- **Revue** : 1 CHANGES REQUESTED (porte verte sans rapport, listing masquant des rouges, tolérance non testée), corrigé dans `040862b6`, puis APPROVED.
- **`/e2e` du cycle** : mobile 22/22 ; Angular 21 + **1 flaky** (E2E-FOLDER-001, 1re occurrence, inscrite au registre) ; parité verte ; aucune quarantaine ni divergence.

#### Matrice de parité — source task-347, 2026-09-29

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ⚠️ flaky | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 1 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
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
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |

**Parité : verte** — aucun écart entre le catalogue et les suites.

- **Reporté** : la répétition sur une task mobile réelle (DOD), jouée après le merge de #262.

---

## Annexe A — Cartographie des briques applicatives

| Brique | Emplacement | Rôle |
|---|---|---|
| Profil AppHost e2e | `Api/Mail/src/AppHost/E2eProfile.cs`, `AppHost.cs` | Backend du filet (Dovecot, GreenMail, relais, registre dédié, clé de bypass) |
| Outillage e2e | `Api/Mail/tests/mss.mail.e2e/` | Reset, seed, relais, contrôle de parité |
| Plan de seed | `Api/Mail/tests/mss.mail.testing.shared/E2eSeedPlan.cs` | Jeu de données déterministe, partagé seed et tests |
| Catalogue | `Api/Mail/e2e/scenarios.yml`, `Api/Mail/e2e/README.md` | Référence commune des scénarios, divergences temporaires |
| Porte `gate` | `Api/Mail/tests/mss.mail.e2e/Parity/E2eGate.cs`, `ParityCheck.cs`, `Program.cs` | Verdict unique de `/e2e` et corps du `## E2E log` |
| Étape `/e2e` | `agents/e2e.md`, `.claude/commands/e2e.md`, `conventions/e2e.md` | Filet bloquant de la chaîne, registres flaky / quarantaines / trous du filet |
| Orchestrateur | `Client/Mobile/e2e/headless/run.mjs` | Run headless de bout en bout, démontage |
| Suite mobile | `Client/Mobile/e2e/specs/functional.spec.ts`, `e2e/support/*` | Parcours taggés `@E2E-…` + annotation `version` |
| Suite web (weda2) | `Client/Angular/front/e2e/mss-e2e/` (`specs/functional.e2e.ts`, `support/{session,weda,fixtures}.ts`, `run.mjs`) | Mêmes parcours ; auth simulée dans Playwright ; backend via l'orchestrateur mobile |

---

## Annexe B — Inventaire fonctionnel (2026-09-29)

- Scénarios au catalogue : 25, dont 22 headless et 3 humains.
- Suite mobile headless : 22 tests joués, 22 verts.
- Suite web headless (weda2) : 22 tests joués, 22 verts.
- Matrice de parité : 22 scénarios verts sur les deux colonnes (dont 1 flaky web, E2E-FOLDER-001).
- Tests unitaires de l'outillage e2e (api-mail) : 53 à task-346, puis porte, divergences et quarantaine en plus (task-347, dont 17 tests de porte).
- Flaky au registre : 1 (E2E-FOLDER-001, web, 1 occurrence). Quarantaines : 0. Divergences ouvertes : 0.

---

## Annexe C — Tasks ayant contribué à cet EPIC

| Task | Statut | Contribution | RGs |
|---|---|---|---|
| task-345 | archived (mergée) | Backend e2e, outillage, catalogue, filet mobile headless | RG-E018-01, 02, 03 (mobile), 04 |
| task-346 | archived (mergée ; Angular à pousser sur TFS) | Filet web weda2 sur le même backend et le même catalogue | RG-E018-03 (web) |
| task-347 | archived (mergée) | Étape `/e2e` bloquante, porte `gate`, clause de DOD, règle d'or | RG-E018-03 (contrôle continu), 05 |
