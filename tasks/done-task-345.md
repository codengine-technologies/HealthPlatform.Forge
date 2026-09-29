# todo-task-345.md — Filet e2e headless client-mobile : les parcours du médecin rejoués sans login humain, contre le vrai backend

**Repos**: api-mail, client-mobile
**Dependencies**: — (aucune) · **reprise bloquée par AUD-27 (task-342, lot C)** — voir `questions/task-345.md`
**Epic**: E018
**EpicTitle**: Filet de non-régression fonctionnel — parcours e2e headless
**Single frontend**: true
**Priorité**: **1** — socle des tasks 346 (Angular) et 347 (étape `/e2e` bloquante de la chaîne).

> **Origine.** Constat du 2026-09-27 : le seul filet qui rejoue des **parcours** du médecin
> (`Client/Mobile/e2e/specs/functional.spec.ts`, 24 tests, task-170) exige un login Pro Santé
> Connect **fait à la main**. Il ne tourne donc que par `/qa`, jamais dans la chaîne. Il n'a pas été
> modifié depuis le 2026-07-25 et on ne sait pas quand il a tourné pour la dernière fois. Les tests
> unitaires et d'intégration protègent les **règles** ; rien d'automatique ne protège les **parcours**
> (enchaînement client → API → IMAP/SMTP → base).

## Objective

Rendre la suite fonctionnelle mobile **exécutable sans humain, en headless**, contre le **vrai
backend** api-mail (API, Postgres, Redis, IMAP, SMTP, pipeline CDA), sur un jeu de données
**synthétique et déterministe** remis à zéro à chaque run.

Seule l'**authentification** est contournée. On réutilise le schéma de bypass qu'api-mail possède
déjà (`TestBypassAuthenticationHandler`, en-têtes `X-Test-Bypass` + `Client-Email` + `Client-Psc-Sub`
+ `Client-Rpps`, bloqué en dur en Production). La session est simulée comme le fait déjà
`/verify-visual` : une fausse session injectée dans le stockage du navigateur. Les en-têtes du bypass
sont posés **par Playwright** sur les appels API, **jamais par l'application**.

**Aucun code de test ni aucune clé ne doit entrer dans le code applicatif mobile ni dans un artefact
de build.**

### Ce qui est contourné, ce qui ne l'est pas

| Réel (exercé) | Contourné (hors de ce filet) |
|---|---|
| Toutes les routes api-mail, gardes de boîte (`mailboxGuard`), SSE | Login PSC / e-CPS, CIBA |
| IMAP (Dovecot) et SMTP (GreenMail) à mot de passe | XOAUTH2 vers un vrai opérateur MSSanté |
| Postgres, Redis, registre des tenants, pipeline CDA | Refresh de jeton par cookie `proxy_session_id`, logout serveur |
| Barrière d'envoi task-320 (session « en ligne » du bypass) | Annuaire Santé national et fournisseur IA **externes** |

Les parcours de la colonne de droite **restent couverts par `/qa`**, avec un login humain.

### Règles

1. **Profil AppHost dédié `e2e`**, dérivé du banc de charge (Dovecot, GreenMail, bypass actif), avec :
   - un **registre de tenants dédié** (`mss_registry_e2e`), distinct de `mss_registry` (comptes de
     dev) et de `mss_registry_loadtest` (banc de charge) ;
   - une **clé de bypass propre au run**, fournie par variable d'environnement, **sans valeur par
     défaut écrite en dur** ;
   - `ASPNETCORE_ENVIRONMENT` différent de `Production`.
2. **Seed e2e déterministe.** Au moins une boîte praticien rattachée **et par défaut** dans le registre,
   pour que `mailboxGuard` l'ouvre sans passer par `/onboarding`. Son contenu est connu d'avance et
   couvre ce que les parcours attendent :
   - des mails lus et non lus, flaggés et non flaggés ;
   - au moins un mail avec pièce jointe et un mail porteur d'un **compte rendu de biologie CDA à
     acquitter** (issu de `JEUX_TESTS_FULL`) ;
   - les dossiers Archive et Corbeille ;
   - au moins un contact local.

   Chaque donnée porte un **nom stable** (`mail-non-lu`, `mail-avec-pj`, `cr-bio-a-acquitter`…),
   déclaré dans le seed et **référencé par le catalogue** (règle 9). Un test ne s'appuie jamais sur une
   donnée que le catalogue ne nomme pas.

   **État vierge à chaque run** : volumes Postgres et maildir neufs, jamais un état hérité d'un run
   précédent.
3. **Projet Playwright headless** dans `Client/Mobile/e2e/`, **à côté** du projet humain existant et
   sans le remplacer. Il ne dépend pas du `setup` PSC, il injecte la fausse session et il pose les
   en-têtes du bypass sur **toutes** les requêtes api-mail, SSE comprises. `Client-Email` est
   **toujours** présent, et le `Client-Session-Id` de l'app est conservé.
4. **Réutilisation de `functional.spec.ts`**. Les mêmes specs tournent dans les deux projets. Les
   tests qui dépendent d'un élément contourné sont **étiquetés et exclus** du projet headless, mais
   restent dans le projet humain :
   - `auth — token expiré rafraîchi silencieusement` ;
   - `zz-logout` ;
   - tout test qui interroge l'Annuaire Santé national.
5. **Envoyer puis recevoir.** Le parcours « compose → envoyer → recevoir → lire → supprimer » doit
   rester **bout en bout**. GreenMail est un puits SMTP : `/develop` choisit entre faire livrer le
   SMTP du profil `e2e` dans Dovecot et vérifier la réception par l'API de GreenMail. Le parcours ne
   peut pas être simplement retiré.
6. **Aucune dépendance réseau externe.** Le run headless doit passer **machine hors ligne** vis-à-vis
   d'Internet : ni Annuaire Santé, ni OpenAI, ni psc-auth-proxy.
7. **Une commande unique**, par exemple `npm run e2e:headless` depuis `Client/Mobile/`. Elle
   s'appuie sur un script qui monte le backend `e2e`, seede, sert l'app, lance la suite, puis
   **démonte tout**, y compris en cas d'échec. Elle rend un code retour **non nul si un test
   échoue** et produit un rapport JSON exploitable par la task-347.
8. **Stabilité.** `retries: 1`. Un test vert au second essai est **signalé flaky** dans le rapport ;
   un test rouge deux fois fait échouer le run.
9. **Catalogue de scénarios : la référence commune à tous les clients.** Il vit dans api-mail, à côté
   du profil `e2e` : `Api/Mail/e2e/scenarios.yml`, avec son schéma documenté dans
   `Api/Mail/e2e/README.md`.
   - **Pourquoi là.** C'est le seul repo commun aux deux clients. Mobile est sur GitHub et Angular sur
     TFS : aucun des deux ne peut servir de référence à l'autre. Toute modification du catalogue passe
     ainsi par une PR api-mail, donc par le HAG.
   - **Ce que porte chaque scénario** :
     - `id` stable, au format `E2E-{DOMAINE}-{NNN}` ;
     - `version` entière, montée dès que le comportement attendu change ;
     - `titre` et `attendu`, en langage métier ;
     - `seed`, les données nommées de la règle 2 ;
     - `clients`, avec pour chaque client `requis` ou `non-applicable — {raison}` ;
     - `mode`, `headless` ou `humain` (joué seulement par `/qa`) ;
     - `origine`, la task qui l'a créé.
   - **Portée du catalogue initial** : les 24 tests de `functional.spec.ts`, y compris les 3 exclusions
     de la règle 4, inscrites en `mode: humain`. La colonne `angular` est **pré-remplie** à `requis`,
     sauf non-applicabilité justifiée. Elle sera confirmée par la task-346.
   - **Ce que n'est pas le catalogue** : ni Gherkin, ni `.feature`, ni step definitions. C'est un
     registre de référence, pas un exécutable (règle 1 de CLAUDE.md).
10. **Chaque test déclare le scénario qu'il implémente**, par le tag Playwright `@E2E-…` et une
    annotation `version`. Les deux ressortent dans le rapport JSON.
11. **Contrôle de parité**, livré ici et exécutable seul, dans `Api/Mail/e2e/`. Il confronte le
    catalogue au **rapport exécuté** d'une suite cliente, pas à son code source. Il sort en échec si :
    - un scénario `requis` pour ce client est absent ou non joué ;
    - un test n'a pas d'identifiant, ou porte un identifiant inconnu du catalogue ;
    - un test implémente une version périmée de son scénario.

    Il produit une **matrice** : scénario × client, avec version, résultat et mode. La task-346 y
    branche Angular ; la task-347 le rend bloquant dans la chaîne.

### Hors périmètre

- **Rattrapage des parcours livrés depuis juillet** (mode sans carte task-320, messagerie détachée,
  frise patient, messagerie indisponible, cookie PSC task-171…). Ce sera une US de suivi, rédigée
  quand ce socle sera vert.
- L'intégration à la chaîne de la forge : c'est la **task-347**.
- Angular : c'est la **task-346**.
- La CI GitHub. Le run est local ; une exécution en CI sera instruite plus tard.

## Definition of Done

- [ ] Build passes (0 errors) — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` et `cd Client/Mobile && npm ci && npm run build`
- [ ] Tests pass (0 failures) — `dotnet test HealthPlatform.Api.Mail.sln` et `npm test -- --watch=false --browsers=ChromeHeadless`
- [ ] Profil AppHost `e2e` livré : registre `mss_registry_e2e`, clé de bypass lue depuis l'environnement (aucune valeur par défaut dans le code ni dans `launchSettings.json`), Dovecot et GreenMail
- [ ] Test unitaire : le profil `e2e` refuse de démarrer, ou n'active pas le bypass, si la clé est absente
- [ ] Test existant `HandleAuthenticate_ProductionEnvironment_NeverAuthenticates` toujours vert
- [ ] Seed e2e déterministe : boîte par défaut rattachée, contenu décrit en règle 2, relecture de contrôle en fin de seed (exit ≠ 0 sinon) ; test d'intégration du provisioning du registre e2e
- [ ] Projet Playwright headless ajouté dans `Client/Mobile/e2e/playwright.config.ts`, sans dépendance au `setup` PSC ; le projet humain existant reste inchangé dans son comportement
- [ ] `npm run e2e:headless` : **au moins 21 des 24 tests** de `functional.spec.ts` verts en headless (tous sauf les 3 exclusions de la règle 4, chacune étiquetée et justifiée dans le spec) — log du run consigné dans le task file
- [ ] Parcours envoyer → recevoir → lire → supprimer vert **bout en bout** en headless
- [ ] **Preuve que le filet mord** : une régression introduite volontairement (par ex. le filtre « Non lus » qui renvoie tout) fait échouer au moins un test ; la régression est annulée et le log rouge consigné
- [ ] Run vert **deux fois de suite** sur un état vierge, sans aucun flaky
- [ ] Run vert réseau Internet coupé (règle 6)
- [ ] Démontage garanti : après un run rouge comme après un run vert, aucun conteneur, `dotnet` ou `ng serve` résiduel
- [ ] Rapport JSON produit (tests passés, échoués, flaky, durée) à un chemin stable documenté
- [ ] Catalogue `Api/Mail/e2e/scenarios.yml` livré, avec les 24 scénarios initiaux et son schéma documenté dans `Api/Mail/e2e/README.md` ; données du seed nommées et référencées
- [ ] Les 24 tests de `functional.spec.ts` portent leur tag `@E2E-…` et leur annotation `version`
- [ ] Contrôle de parité : vert sur la colonne `mobile` avec le rapport du run headless (plus le rapport `/qa` pour les scénarios `mode: humain`, ou mention « non joué » explicite)
- [ ] Tests du contrôle de parité : scénario requis manquant, test sans identifiant, identifiant inconnu, version périmée → chacun fait sortir le contrôle en échec
- [ ] Durée du run mesurée et consignée — cible indicative ≤ 10 min, sans blocage si elle est dépassée
- [ ] `grep` sur `Client/Mobile/src` : aucune occurrence de `X-Test-Bypass` ni de la clé
- [ ] `Client/Mobile/e2e/README.md` mis à jour : les deux modes (humain `/qa`, headless) et leurs périmètres respectifs
- [ ] Aucune donnée de santé réelle ; captures et traces d'échec git-ignorées

## Manual Test Plan

1. Poste avec Docker démarré. `cd Client/Mobile && npm run e2e:headless` (la clé est exportée par le
   script, ou suivre le README).
2. Attendu : le backend `e2e` monte, le seed annonce sa relecture vérifiée, puis la suite tourne sans
   ouvrir de fenêtre et sans demander de login. Fin avec « ≥ 21 passed » et code retour 0.
3. Vérifier que `docker ps` ne montre plus aucun conteneur du profil `e2e`, et qu'aucun process
   `dotnet` ni `ng serve` ne reste.
4. Casser volontairement une ligne, par exemple le filtre « Non lus » de l'inbox, puis relancer :
   au moins un test rouge et un code retour ≠ 0. Annuler la modification.
5. Lancer `/qa` (login PSC humain) : le projet humain fonctionne toujours, y compris le refresh de
   jeton et le logout.
6. Relancer l'AppHost **sans** la variable de clé : aucune requête ne passe par le bypass (401).
7. Ouvrir `Api/Mail/e2e/scenarios.yml` : les 24 scénarios se lisent en langage métier. Lancer le
   contrôle de parité sur le rapport du run : matrice verte pour le mobile. Monter la version d'un
   scénario dans le catalogue sans toucher au test, puis relancer : le contrôle signale une version
   périmée. Annuler.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville, biologie — protège des parcours existants, sans en créer
- **Vague Ségur** : hors Ségur — outillage de non-régression
- **Exigences DSR honorées** : non applicable — aucune fonctionnalité produit nouvelle
- **INS** : non applicable — données synthétiques uniquement, aucune INS réelle ; les CDA de test proviennent de `JEUX_TESTS_FULL`
- **Authentification PS** : **inchangée en production** (PSC / e-CPS). Le bypass reste **bloqué en dur en Production** et n'est activé que par une clé fournie à l'exécution dans le profil `e2e`, jamais par défaut, jamais sur un environnement HDS. L'authentification réelle reste couverte par `/qa`.
- **Habilitations** : praticien simulé (RPPS et `sub` synthétiques) déclaré par en-têtes ; aucun RPPS réel
- **Interop CI-SIS** : CDA r2 CR de biologie (jeux de test) exercé via la pipeline existante, sans modification
- **Tracé PGSSI-S** : inchangé. Les actions faites sous bypass sont journalisées comme les autres, **dans le registre isolé `mss_registry_e2e` uniquement**, et détruites avec le run.
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — poste de développement, données synthétiques ; **interdiction de lancer ce profil sur un environnement HDS**
- **AIPD / impact RGPD** : inchangé — aucun traitement de données réelles

## Branches
- `api-mail` (pushed) : feat/task-345-filet-e2e-headless-mobile — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-345-filet-e2e-headless-mobile
- `client-mobile` (pushed) : feat/task-345-filet-e2e-headless-mobile — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-345-filet-e2e-headless-mobile

## Timings

*(généré par `tools/timing/report.sh --task task-345 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 27 s | — | — | — | api-mail, client-mobile |
| /develop | ok | 13 min 03 s | 11 (2 min 26 s) | 19 (42 min 22 s) | — | api-mail 7B/6T, client-mobile 4B/13T, 2e reprise : lu/flag relus du serveur, 5 mutations → 3 rouges visés, 22/22 ×2 |
| /sonar | ok | 7 min 19 s | 4 (1 min 26 s) | 16 (11 min 44 s) | 6 (1 min 48 s) | api-mail 4B/16T, re-analyse post-reprise : Phase 1 0 finding, QG OK, Phase 2 skip (structurel) |
| /lint-angular | skipped | 0.4 s | — | — | — | client-angular non touché |
| /lint-mobile | ok | 30 s | — | — | — | 0 erreur baseline |
| /verify-visual | skipped | 0.4 s | — | — | — | aucun écran redessiné (reprise limitée à e2e/) |
| /review | failed | 6 min 34 s | 4 (27 s) | 4 (4 min 37 s) | — | api-mail 2B/2T, client-mobile 2B/2T, CHANGES REQUESTED : lu/flag vérifiés sur l'état optimiste (MAIL-001/002/003) |
| **Total cycle** | | **27 min 56 s** | **19 (4 min 19 s)** | **39 (58 min 44 s)** | **6 (1 min 48 s)** | |

Autres commandes mesurées : lint ×2 (32 s), restore ×1 (2.2 s)

## Develop log

- Repos touched : api-mail, client-mobile
- DTOs published : no DTO change — Interop : no change
- Commits (locaux, **non poussés** — arrêt sur arbitrage, voir `questions/task-345.md`) :
  - api-mail : `1d5d9e45` feat(e2e) backend du filet e2e headless ; `61e18424` fix(mail) compteur de pièces jointes (chemin en-têtes IMAP)
  - client-mobile : `3004950` feat(mobile) filet e2e headless ; `bca017d` fix(mobile) fermeture du menu des dossiers
- Local build / test : ✓ api-mail (5 735 verts, 16 ignorés préexistants), ✓ client-mobile (943/943)
- Filet headless `npm run e2e:headless` — 4 runs complets, démontage complet à chaque fois (y compris après échec du seed, run 1) :
  - run 4 : **20 verts, 1 flaky (E2E-DETAIL-002), 1 rouge (E2E-BIO-001)** — parité **verte** (22 scénarios headless couverts à la bonne version, 3 humains « non joués »)
  - rouge et flaky = **AUD-27** (réponse du repli IMAP mise en cache 15 min) → arbitrage humain
- Défauts trouvés par le filet et corrigés (test rouge d'abord) : compteur de pièces jointes à 0 sur la liste servie par IMAP (badge trombone jamais affiché) ; menu des dossiers resté ouvert sur téléphone
- Défauts de la suite elle-même corrigés : `isVisible({ timeout })` n'attend pas (29 occurrences), test d'acquittement antérieur aux onglets du corps de mail, état « vide » de chargement pris pour une réponse
- Preuve que le filet mord : mutations du contrôle de parité (version, requis absent, test sans identifiant) toutes détectées ; défauts réels ci-dessus
- Passe qualité (/simplify) : **différée à la reprise** (avant le push)
- DOD self-check : non tenu sur « run vert deux fois de suite » tant que E2E-BIO-001 est rouge
- Next step : **arrêt — `questions/task-345.md`**

### Reprise du 2026-09-28 (après merge de task-342)

- Synchro : `origin/develop` mergé dans les deux branches (sans conflit). AUD-27 (task-342) ne suffisait PAS : la vraie cause de `E2E-BIO-001` rouge était la **génération UIDVALIDITY 0** — `AddNewMail` estampille les mails seedés en génération 0 quand la ligne `MailFolders` n'existe pas encore ; dès la vraie génération persistée, la lecture en base les ignore et le détail retombe sur IMAP, sans document CDA. Correctif **harnais** (même remède que la chauffe du banc, `f209ce8`) : le seed liste les dossiers avant le premier enrichissement, et vérifie que le CR de biologie est servi par la base.
- Tests adaptés : le CR de biologie hors normes, désormais servi enrichi, est **épinglé en tête** de l'inbox → en headless chaque parcours désigne son message seedé par son objet ; la réception attend SON objet ; gestes amenés à l'écran.
- **Filet : 2 runs consécutifs verts, 22/22, 0 flaky, parité verte**, ~3 min par run (159 s après la passe qualité).
- **Preuve que le filet mord** : régression plantée dans l'app (filtre « Non lus » qui renvoie tout) → `E2E-INBOX-001` rouge, code 1 ; mutation annulée.
- Suites des repos : api-mail **5 849 verts**, 0 échec (16 ignorés préexistants) ; mobile **947/947** (un flaky préexistant identifié, `MailboxSwitcherComponent`, fichier non touché — rouge seul, vert en suite complète).
- Passe qualité (/simplify), deux repos : appliquée et re-validée — mobile `ba01ecf` + `67f7f02`, api-mail `c0fe8524` (détail dans les messages de commit). Écartés : déplacer `BenchImap` / écriture des réglages / en-têtes de bypass vers `testing.shared` (hors diff), connexions persistantes du relais, état de chargement de l'app (changement de comportement).
- Commits poussés : api-mail `…c0fe8524`, client-mobile `…67f7f02`.
- **Constats à router vers le PO** (hors périmètre) : (1) `AddNewMail` estampille la génération 0 en silence — le seed le contourne, un scénario « inbox ouverte sans lister les dossiers » le ferait voir ; (2) règle de `AttachmentCount` différente selon le chemin (en-têtes IMAP vs base) et deux constructeurs de `MailDto` qui ne la posent pas (`BackgroundEnrichmentProcessor.cs:314`, `MailRepository.cs:3295`) ; (3) dates : `SentDate = envelope.Date?.LocalDateTime` (famille AUD-28) ; (4) « Aucun contenu disponible » affiché pendant le chargement du détail.
- Next step : `/sonar task-345`

### Reprise du 2026-09-29 (après /review CHANGES REQUESTED)

- **Bloquant corrigé — démontage de `run.mjs`** : il retirait tout conteneur aux préfixes `mss-mail-redis-`/`mss-mail-rabbitmq-`/`rediscommander-`, donc aussi ceux d'un AppHost de dev lancé à côté. Désormais : instantané des conteneurs **avant** le démarrage de l'AppHost, retrait des **seuls** conteneurs apparus pendant le run, rien si l'AppHost n'a jamais démarré ; `SIGTERM`/`SIGHUP`/`SIGBREAK` gérés comme `SIGINT` ; contrôle final des ports du filet. Vérifié sur 4 runs (2 de mutation, 2 verts) : liste `docker ps -a` identique avant/après (64 conteneurs du poste, dont psc-auth-proxy, sonarqube, flagsmith, intacts).
- **Parcours durcis** (un vert ne ment plus) : BIO-001 (réponse du POST + état relu après rechargement — le panneau bascule de façon optimiste, son libellé ne prouvait rien), DETAIL-002 (HTML → brut → HTML), SEARCH-001 (bascule avancée et filtre requis ; résultats non assertés : la recherche sémantique dépend du fournisseur d'IA), CONTACT-002/003, SIGNATURE-001, FOLDER-002 (suppression requise puis disparition), et avant compaction FOLDER-001, MAIL-001, COMPOSE-001, MAIL-003, MAIL-004, DRAFT-001.
- **Défauts de la suite trouvés en rejouant** : titre de dossier ambigu (celui du menu latéral), suppression de brouillon sous une option de swipe, suppression de mail **différée de 6 s** (fenêtre d'annulation) que le rechargement du test annulait.
- **Preuve par mutation** — 7 no-ops plantés dans `MssApiService` (suppression contact / signature / groupe / dossier / mail / brouillon, acquittement bio) : **exactement les 7 parcours visés rouges**, chacun sur son assertion, les 15 autres verts, parité verte. Mutations annulées.
- **Suggestions de la review appliquées** : en-têtes du bypass limités à l'origine de l'app (`BASE_URL` partagé) ; catalogue qui refuse un scénario muet sur un client du catalogue (+ test, rouge vérifié par mutation) ; sondes du seed tolérantes au délai HTTP ; interruption et délai distingués dans `Program.cs` ; réponse du POST contact disposée ; `MSS_E2E_PASSWORD` retiré (la passdb statique ne suivait pas).
- **Filet : 22/22 verts deux fois de suite, 0 flaky, parité verte.** Suites : api-mail **5 849 verts** (un flaky préexistant sous charge parallèle, `SeededThreadsAreCountableTests`, fichier non touché — vert 3/3 seul puis en suite d'intégration rejouée), mobile build OK + **947/947**.
- Passe qualité (§Q) : déjà faite une fois par repo à la reprise du 2026-09-28 ; ces correctifs réutilisent les helpers existants (`swipeRowOpen` extrait de `swipeReveal`, qui supprime le geste dupliqué de CONTACT-003).
- Commits poussés : api-mail `f8b44271`, client-mobile `9d591af`.
- **2e review (même jour) — CHANGES REQUESTED, corrigé** : MAIL-001/002/003 ne jugeaient lu/non-lu et flag que sur l'état optimiste de la ligne. Ils exigent désormais la réponse de l'appel de statut puis relisent l'état après rechargement. Preuve : no-op sur les 4 appels de statut unitaires + le « tout marquer lu » → **exactement MAIL-001/002/003 rouges**, 19 verts ; puis **22/22 ×2**. Suggestions appliquées : instantané des conteneurs fermé par défaut si `docker ps -a` échoue, `MOBILE_BASE_URL` épinglé, DASH-001 n'accepte plus un widget en chargement. Commit client-mobile `76db234` (seul `e2e/` touché : `src/` inchangé depuis le 947/947).
- **Constat à router vers le PO** (hors périmètre, changement de comportement) : `MailPendingDeleteService` ne flushe ni au déchargement ni à la destruction, contrairement à son commentaire (« teardown → FLUSH ») — une app fermée ou rechargée dans les 6 s qui suivent une suppression la perd, et le mail réapparaît.

## Sonar log

Mode A (chaîné depuis `/develop`), serveur SonarQube **9.9.8.100196** (`sonar.login`, port 9000 — conteneurs `sonarqube_db` puis `sonarqube` redémarrés au pré-vol), projet `healthplatform-api-mail`. 2 analyses complètes (begin → build Release → 5 passes OpenCover → end).

**Provenance** : la new-code period du projet est `PREVIOUS_VERSION` ; Phase 1 = les findings posés sur des lignes **ajoutées par cette branche** (`git diff origin/develop...HEAD`), comme task-342. Le code applicatif (`src/`) de la branche se réduit à une ligne (`EmailBuildingService`, compteur de pièces jointes) ; l'outillage `tests/mss.mail.e2e` est analysé avec le jeu de règles de test et exclu de la couverture ; l'AppHost est exclu de l'analyse.

- Phase 1 (lignes de task-345) : ✓ **0 finding restant**. Quality Gate **OK**, new_coverage = **98,3 %**
- Phase 1 — Issues fixées : **1** code smell — CA1859 ×1 (`PlaywrightReport.ArrayOf`, type concret). Commit `5997a86b`
- Phase 1 — Tests ajoutés : 0 (la ligne applicative de la branche est déjà couverte par `BuildHeaderOnlyMailDto_WithAttachments_CountsThem`)
- Phase 2 (legacy) : itérations **0 / 5** — aucun lot traitable en batch : S107 ×8 (constructeurs et méthodes à 8-11 paramètres : structurel), S3604 ×2 (`ImapService`, `OfflineMailDataProvider`, code de task-342 : le corriger selon la convention rend `timeProvider` obligatoire, donc change les signatures et tous les appelants, hors périmètre)
- Phase 2 — Issues fixées : 0 — Issues restantes : **10** (acceptation best-effort)
- Hotspots : **0**
- Build / tests : ✓ green (domain 190, application 3 267, infrastructure 665, api 1 084, integration 643 + 16 ignorés), sous instrumentation OpenCover, deux fois
- `conventions/csharp.md` : CA1859 → occurrence 5 (variante task-345)

**Re-analyse du 2026-09-29** (après la reprise `/develop`, commit `f8b44271`) : 1 analyse complète, serveur 9.9.8 sur le port 9000. Phase 1 : **0 finding** sur les fichiers de la branche ; Quality Gate **OK** ; new_coverage **98,3 %** ; Phase 2 : 0 itération (mêmes 10 findings legacy structurels). Build Release + 5 passes OpenCover vertes (domain 190, application 3 267, infrastructure 665, api 1 084, integration 643 + 16 ignorés). KPIs identiques à la colonne « Final » ci-dessous.

### KPIs qualité (baseline → final)

Baseline = analyse 1 de cette branche (serveur 9.9.8, 2026-09-28). Le serveur a rebasculé de 25.6 (task-342) vers 9.9 : ses chiffres ne sont pas comparables à ceux du log de task-342 (analyseurs python/javascript absents en 9.9).

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 98,3 % | 98,3 % | ±0 pt |
| New violations | 3 | 2 | −1 |
| Bugs | 0 | 0 | ±0 |
| Vulnerabilities | 0 | 0 | ±0 |
| Security hotspots | 0 | 0 | ±0 |
| Code smells | 11 | 10 | −1 |
| Coverage (projet) | 98,2 % | 98,2 % | ±0 pt |
| Duplication | 0,5 % | 0,5 % | ±0 pt |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

## Lint log

- `/lint-angular` : **skipped** — `client-angular` non listé dans `**Repos**:` (task-346 le couvrira), non touché par la task.
- `/lint-mobile` : ✓ **0 erreur, 0 avertissement** dès la baseline (`ng lint`, périmètre `src/**/*.ts|html`) — 0 itération, aucun commit. Les fichiers `src/` touchés par la branche : `inbox.page.ts` (+ spec), `mail-folder-list.component.*` (ramenés à l'état de develop).
- `/lint-mobile` (re-passe du 2026-09-29, après la reprise) : ✓ **0 erreur** dès la baseline — la reprise n'a touché que `e2e/`, hors du périmètre `ng lint` ; 0 itération, aucun commit.

## Visual verify log

- `/verify-visual` : **skipped** — aucun écran `client-mobile` redessiné (aucun `.html`/`.scss` touché sous `src/` ; seul changement applicatif : la page inbox ferme le menu des dossiers après un choix), aucun `## Stitch design log`, et `Tools/visual-verify/` absent du poste. Les parcours eux-mêmes sont vérifiés par le filet headless de cette task (22/22).
