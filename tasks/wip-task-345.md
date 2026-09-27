# todo-task-345.md — Filet e2e headless client-mobile : les parcours du médecin rejoués sans login humain, contre le vrai backend

**Repos**: api-mail, client-mobile
**Dependencies**: — (aucune)
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
| **Total cycle** | | **27 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |
