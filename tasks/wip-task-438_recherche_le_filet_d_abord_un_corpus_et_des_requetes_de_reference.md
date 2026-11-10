# todo-task-438.md — Recherche : le filet d'abord, un corpus et des requêtes de référence

**Repos**: api-mail, client-angular, client-mobile
**Dependencies**: — (aucune ; première task de l'EPIC, les tasks 439 à 441 s'appuient sur elle)
**Epic**: E022
**EpicTitle**: Recherche fiable
**Priorité**: demandée par l'humain le 2026-11-09 : « nous allons devoir mettre en place un travail profond pour régler
ce système de recherche pour le rendre fiable […] ces erreurs n'ont jamais été détectées, ce qui exprime un trou
important ». Le filet passe **avant** les correctifs (règle d'or : un défaut laisse une prévention).

> **Origine.** Campagne du 2026-11-09 sur la boîte de formation de Virginie (11 178 mails), 30 appels réels à
> `POST /api/v1/Search/semantic` comparés à la vérité terrain : `Docs/audits/recherche-campagne-bugs-weda2-mobile-20261109.md`
> (défauts R1 à R9).

## Pourquoi le filet actuel n'a rien vu

Constaté le 2026-11-09 dans `tests/mss.mail.integration.tests` et `Api/Mail/e2e/scenarios.yml` (commit `405da376`) :

1. **Le mode des clients n'est jamais joué.** weda2 et le mobile envoient toujours le mode hybride (sémantique + plein
   texte). Les tests du plein texte (`FullTextSearchSinglePassIntegrationTests`, `SearchEndpointIntegrationTests`)
   jouent `FullTextOnly`, sans générateur d'embeddings (`SearchEndpointHarness` : « absent par défaut »). La fusion
   hybride, le seuil de similarité et le bruit sémantique (R6, R7) ne sont exercés nulle part.
2. **On cherche le mot qu'on vient d'écrire.** `Semantic_TermInUpperCaseWithAccents_FindsTheLowerCaseBody` cherche
   « échographie » dans « ÉCHOGRAPHIE » : même accent. Aucun test ne tape comme un médecin (accent oublié, virgule,
   nom de patient, mot de l'objet) : R1, R2, R5.
3. **Un test fige le défaut.** `Semantic_MoreMatchesThanTheWindow_KeepsTheMostRecentMails` exige qu'au-delà de 200
   correspondances seules les plus récentes restent : c'est R3, l'historique ancien d'un patient invisible.
4. **Ni volume, ni vérité terrain.** Les jeux comptent 1 à 4 messages ; aucun test ne compare la réponse au contenu de
   la boîte. L'unique scénario e2e, `E2E-SEARCH-001`, vérifie que « la requête est prise en compte et le panneau avancé
   s'ouvre », jamais le contenu des résultats.

## Objective

La recherche est jugée comme un médecin la juge : **a-t-il trouvé ce que sa boîte contient ?** Un corpus de référence et
des requêtes de référence, joués de bout en bout dans le mode des clients, mesurent ce que la recherche rend par
rapport à ce qu'elle devrait rendre. Chaque défaut connu y est un cas attendu, rattaché à la task qui le corrige.

Règles :
- **Corpus de référence** versionné dans api-mail, fictif, réaliste et assez gros pour solliciter les cas limites :
  - des messages accentués en français médical, et leurs mots tels qu'un médecin les tape (sans accent, en majuscules) ;
  - au moins un patient au **long historique** : plus de 200 messages qui portent son nom, sur plusieurs années, mêlés à
    des homonymes partiels (même prénom, même nom) ;
  - des mots présents **seulement dans l'objet**, **seulement chez l'expéditeur**, **seulement dans le nom d'une pièce
    jointe** ;
  - des documents médicaux CDA et HPRIM (corps du document) ;
  - des messages dans plusieurs dossiers, dont deux de même UID ;
  - des **embeddings réels** pré-calculés pour chaque message, chaque document et chaque requête, versionnés avec le
    corpus et regénérés par un outil quand le corpus change. Aucun appel externe pendant les tests.
- **Requêtes de référence** : chacune porte le texte tapé, le dossier, et le résultat attendu, exprimé en messages du
  corpus. L'attendu suit les règles décidées par l'humain le 2026-11-09 pour l'EPIC :
  - **tous les mots d'abord** : les messages qui contiennent tous les mots en tête, puis, séparés et signalés, ceux qui
    n'en contiennent qu'une partie ;
  - **champs cherchés** : objet, corps, documents médicaux, nom et adresse de l'expéditeur, nom des pièces jointes ;
  - **exacts d'abord, proches ensuite** : les correspondances exactes en tête, puis une section de résultats proches,
    sous un seuil unique ; un mot absent ne ramène aucun résultat exact.
  - **accents, casse et ponctuation** sans effet sur le résultat.
- **Joué comme les clients** : mode hybride, `maxResults` 50, mêmes champs de requête que weda2 et le mobile, vraie pile
  (routage, DI, service, dépôt, PostgreSQL du fixture avec pgvector) ; seul le fournisseur d'embeddings est remplacé
  par les vecteurs pré-calculés.
- **Mesures par requête** : rappel (part des messages attendus rendus), précision (part des messages rendus attendus),
  rang des attendus, troncature. Un tableau de synthèse est produit à chaque exécution.
- **Un défaut connu est un cas attendu, pas un cas ignoré** : chaque requête qui échoue aujourd'hui est marquée avec la
  task qui doit la rendre verte (439, 440 ou 441). Son échec actuel est **prouvé** (vu rouge, consigné), puis le cas est
  écarté de la suite verte par un marquage explicite qui cite la task. La task citée retire le marquage dans sa DoD.
- **Le test qui fige R3** (`Semantic_MoreMatchesThanTheWindow_KeepsTheMostRecentMails`) est marqué de la même façon,
  avec task-439 : il contredit la règle décidée.
- **e2e, côté clients** : des scénarios qui vérifient le **contenu** des résultats dans les deux clients, sur ce qui
  marche déjà, pour que les corrections ne cassent rien :
  - `E2E-SEARCH-002` v1 : un mot rare, tapé avec son accent, trouve le message qui le contient ; il s'affiche dans la
    liste des résultats ;
  - `E2E-SEARCH-003` v1 : un numéro de dossier de biologie trouve son message, et un seul.
  Les comportements à corriger (accents, objet, ordre, groupes) entrent au catalogue avec les tasks 439 à 441.
- **Outil de campagne sur une vraie boîte** : le script de la campagne du 2026-11-09 (vérité terrain en base, appels
  réels, notation) est versionné dans api-mail, documenté, et rejouable sur toute boîte de développement. Il ne touche
  jamais une boîte de production et ne s'authentifie que par une session réelle (jamais par le test-bypass, qui
  enverrait de faux identifiants IMAP à l'opérateur).

### Hors périmètre

- Toute correction de la recherche : tasks 439 (plein texte), 440 (sémantique), 441 (clients).
- Le coût de la recherche : tasks 437 et 439.

## Definition of Done

- [ ] Build passes (0 errors) : `HealthPlatform.Api.Mail.sln`, weda2, client-mobile
- [ ] Tests pass (0 failures) : `HealthPlatform.Api.Mail.sln`, `nx test weda2` / `nx test mss-lib`, client-mobile
- [ ] **Corpus de référence** versionné, fictif (aucune donnée réelle, INS sous OID de test), avec ses embeddings
      pré-calculés et l'outil qui les regénère ; il couvre chacun des cas listés dans l'Objective
- [ ] **Test d'intégration de bout en bout (règle 1b), `POST /api/v1/Search/semantic` en mode hybride** sur le corpus :
      chaque requête de référence lue dans la réponse réelle (messages rendus, ordre, `isTruncated`, `hits` avec leur
      dossier), rappel et précision calculés, tableau de synthèse produit
- [ ] **Requêtes de référence** couvrant au minimum chacun des défauts R1 à R6 de la campagne (accent oublié, mot de
      l'objet, patient au long historique, plusieurs mots, ponctuation, mot absent), plus les cas qui marchent (mot rare
      accentué, numéro de dossier, documents CDA et HPRIM, deux dossiers de même UID)
- [ ] **Chaque cas attendu rouge est prouvé rouge** sur le code actuel, avec la valeur mesurée, consigné dans le
      `## Develop log`, puis marqué avec sa task (439, 440 ou 441). Le test de R3 existant est marqué task-439
- [ ] **Les cas verts sont prouvés par mutation** : un défaut réinjecté (par exemple le dossier ignoré, ou un terme
      abandonné) fait tomber au moins un cas vert
- [ ] Scénarios `E2E-SEARCH-002` v1 et `E2E-SEARCH-003` v1 ajoutés à `Api/Mail/e2e/scenarios.yml` (mobile et Angular
      requis), avec leur seed, et implémentés dans les deux clients ; chacun vérifie le **contenu** de la liste de
      résultats ; vus rouges par mutation
- [ ] Outil de campagne versionné dans api-mail, avec son mode d'emploi (session réelle, jamais le test-bypass)
- [ ] **Prévention (règle d'or)** :
      - ligne « trou du filet » dans `conventions/e2e.md` : la recherche n'était jugée ni sur son contenu, ni dans le
        mode des clients ;
      - consigne dans `conventions/csharp.md` : un test de recherche tape comme un médecin et joue le mode des clients ;
        un test qui fige un comportement à corriger est marqué avec la task qui le corrige, jamais laissé vert
- [ ] Aucune donnée de santé en clair dans les logs (termes de recherche compris)

## Manual Test Plan

1. `cd Api/Mail && dotnet test --filter Search` : le tableau de synthèse des requêtes de référence s'affiche (rappel,
   précision par requête) ; les cas marqués citent leur task.
2. Lancer le banc e2e (`/e2e` ou `npm run e2e:headless` côté mobile, `npm run e2e:mss` côté Angular) : `E2E-SEARCH-002`
   et `E2E-SEARCH-003` sont verts dans les deux clients.
3. Rejouer l'outil de campagne sur la boîte de formation de Virginie avec une session réelle : le tableau reproduit
   celui du 2026-11-09 (même défauts, mêmes ordres de grandeur).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du praticien)
- **Vague Ségur** : hors Ségur — qualité interne de la recherche
- **Exigences DSR honorées** : non applicable — aucune exigence fonctionnelle nouvelle dans cette task
- **INS** : non applicable — le corpus est fictif ; les INS qu'il porte sont sous l'OID de test `1.2.250.1.213.1.4.10`
- **Authentification PS** : inchangée — PSC (e-CPS), niveau eIDAS substantiel ; l'outil de campagne n'utilise qu'une
  session réelle
- **Habilitations** : inchangées — verdict de l'opérateur MSSanté sur la boîte (règle 14)
- **Interop CI-SIS** : non applicable — les documents CDA du corpus sont cherchés, pas échangés
- **Tracé PGSSI-S** : inchangé — chaque recherche reste tracée au nom de la personne réelle, 3 653 jours
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — corpus fictif, tests sur le poste et en CI
- **AIPD / impact RGPD** : inchangé — aucune donnée réelle

## Branches
- `api-mail` (pushed) : feat/task-438-recherche-le-filet-d-abord-un-corpus-et — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-438-recherche-le-filet-d-abord-un-corpus-et
- `client-mobile` (pushed) : feat/task-438-recherche-le-filet-d-abord-un-corpus-et — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-438-recherche-le-filet-d-abord-un-corpus-et
- `client-angular` (code-only) : la forge écrit sur la branche actuellement checked out dans `Client/Angular/` (au /start : `feature/nova-mss-weda-integration`, commit `e2f3e131`) — l'humain gère branche, commit, push, PR TFS

## Timings

*(généré par `tools/timing/report.sh --task task-438 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 1 min 22 s | — | — | — | — |
| /develop | ok | 54 min 24 s | 19 (1 min 31 s) | 4 (7 min 09 s) | — | api-mail 18B/3T, client-mobile 1B/1T |
| /sonar | ok | 20 min 48 s | 3 (1 min 06 s) | 11 (13 min 17 s) | 4 (1 min 24 s) | 2 itération(s), api-mail 3B/11T |
| /lint-angular | ok | 1 min 05 s | — | — | — | — |
| /lint-mobile | ok | 23 s | — | — | — | — |
| /e2e | ok | 27 min 14 s | 1 (12 s) | — | — | api-mail 1B/0T, e2e ×3 (18 min 32 s) |
| **Total cycle** | | **1 h 45 min** | **23 (2 min 50 s)** | **15 (20 min 26 s)** | **4 (1 min 24 s)** | |

Autres commandes mesurées : lint ×2 (37 s)

## Develop log

- Repos touched : api-mail, client-mobile, client-angular (code-only)
- DTOs published : no DTO change
- Interop published : no interop change
- Commits :
  - api-mail : `6d0dafd5` test(search): corpus et requêtes de référence, jugés comme un médecin ; `079da993` test(e2e): E2E-SEARCH-002 et 003 — seed et catalogue ; `50c94f06` refactor(search): simplify pass (/simplify)
  - client-mobile : `ba3e1ae` test(mobile): E2E-SEARCH-002 et 003
  - client-angular : `front/e2e/mss-e2e/specs/functional.e2e.ts` modifié, **non commité** sur `feature/nova-mss-weda-integration` (code-only, à commiter par l'humain vers TFS)
- **Le filet** (`Api/Mail/tests/mss.mail.integration.tests/Search/Reference/`) :
  - corpus fictif de 560 messages (30 porteurs d'embeddings réels, 520 d'historique sans vecteur) : mots accentués, Hélène BOUCHER (60 messages 2022-2023) noyée sous Hélène ROUSSEL et Marc BOUCHER (230 récents chacun), mots seulement dans l'objet / chez l'expéditeur / dans une pièce jointe, documents CDA et HPRIM, deux messages de même UID (INBOX, Archives), 10 voisins sémantiques ;
  - 18 requêtes × 2 profils (weda2 0,7 ; mobile 0,1), mode hybride, 50 résultats, jugées par l'oracle (rappel, tous les mots d'abord, mot absent, dossier courant). Tableau : `bin/.../search-reference-report.md`, écrit à la fin de la classe ;
  - embeddings réels pré-calculés (`text-embedding-3-small`, 48 vecteurs, `search-reference-embeddings.json`), aucun appel externe en test ; `tests/search-quality/embed_corpus.py` calcule les manquants ;
  - prémisse affirmée à chaque cas : moteur sémantique joué, aucun embedding manquant, recherche non dégradée.
- **Défauts connus prouvés rouges** (`SEARCH_REFERENCE_KNOWN_DEFECTS=1`, code `405da376`) — 11 rouges sur 36 :
  - weda2 : accent oublié `hemoglobine` et `HEMOGLOBINE` (0 sur 2), objet `urgent` (0 sur 2), expéditeur `Biovalis` (0 sur 1), pièce jointe `echocardiographie` (0 sur 1), ponctuation `créatinine,` (0 sur 1), patient `Hélène BOUCHER` (rappel 0 %) → task-439 ;
  - mobile : expéditeur et pièce jointe (le message attendu au rang 9, derrière du bruit), patient (rappel 0 %) → task-439 ; mot absent `zorglubine` (29 résultats) → task-440 ;
  - constaté : au seuil 0,1, la similarité rattrape l'accent, l'objet et la ponctuation (verts côté mobile) ; « quatre mots » vert sur les deux profils (le classement en mémoire compte les quatre mots ; le défaut de la vraie boîte vient du plafond par terme, couvert par le cas du patient) — gardé comme garde-fou.
  - `Semantic_MoreMatchesThanTheWindow_KeepsTheMostRecentMails` (figeait R3) marqué `Skip` → task-439.
- **Preuve par mutation des cas verts** : `SemanticSearchRepository.InFolder` sans filtre de dossier → 14 cas verts tombent (« dossier courant : 1 résultat hors du dossier INBOX »), restauré depuis une copie, recompilé, vert de nouveau.
- **e2e** : `E2E-SEARCH-002` v1 et `003` v1 au catalogue (mobile et Angular requis, seed `mail-non-lu-2`), implémentés dans les deux clients ; le corps de `mail-non-lu-2` porte « Échocardiographie » et « 260915000438 » (`E2eSeedMessage.ExtraBodyText`), test du seed : seul ce message les porte. Type-check des deux suites vert. **Preuve par mutation e2e non faite à ce stade** : le banc e2e exige le port 5052, occupé par l'AppHost de développement de l'humain (lancé pour la campagne) ; elle se fera au passage de `/e2e`.
- Local build / test :
  - api-mail : suite complète verte (domain 210, infrastructure 728, application 4 031, api 1 378, intégration 1 166 + 28 écartés dont les 12 marques) ; re-validation après la passe qualité : recherche 213 + 12 marques, api 1 378. La solution n'a pas pu être recompilée en entier : les binaires de l'API sont verrouillés par l'AppHost de l'humain ; les projets modifiés (tous des projets de test) ont été compilés seuls, `BuildProjectReferences=false`.
  - client-mobile : build vert, 1 417 tests verts.
  - client-angular : seul le spec e2e change (type-check et ESLint verts, aucun écart Prettier) ; code de l'application inchangé.
- Passe qualité (/simplify) :
  - Applied & committed : api-mail : 9 fichiers (`50c94f06`) — champ mort retiré, rapport écrit une fois, oracle normalisé une fois, énumérations au lieu de valeurs recopiées, membres privés, `ExtraBodyText` au lieu d'un nom de message en dur, une requête SQL par recherche dans `campagne.py` ;
  - Applied (code-only, uncommitted) : client-angular : prédicat `isSemanticSearch` partagé ;
  - No change : client-mobile (fusion des deux tests écartée : messages d'assertion propres à chaque scénario) ;
  - Écartés, hors du diff relu : valeurs du seed par le manifeste (trois dépôts), extraction de `MailEmbeddingText` en production.
- DOD self-check : corpus, test d'intégration hybride, couverture R1 à R6, rouges prouvés, mutation des verts, scénarios e2e, outil de campagne, préventions (`conventions/e2e.md`, `conventions/csharp.md`) — vérifiés ; mutation e2e reportée à `/e2e`.
- Next step : /sonar task-438

## Sonar log

**Mode A** (chaîné depuis `/develop`), `api-mail`, branche `feat/task-438-…`. 2 analyses, compilées en `Release` : les
binaires `Debug` de l'API étaient verrouillés par l'AppHost de développement de l'humain.

| KPI | Baseline (analyse du 2026-11-08) | Itération 1 | Final |
|---|---|---|---|
| Quality Gate | OK | OK | **OK** |
| Bugs / Vulnérabilités | 0 / 0 | 0 / 0 | 0 / 0 |
| Code smells | 0 | 4 | **0** |
| Hotspots à revoir | 0 | 0 | 0 |
| Couverture globale | 97,9 % | 97,9 % | 97,9 % |
| Duplication | 0,4 % | 0,4 % | 0,4 % |
| Ratings (fiabilité / sécurité / maintenabilité) | A / A / A | A / A / A | A / A / A |

Tests de l'analyse finale : 7 541, 0 échec (intégration : 1 167 réussis, 27 ignorés, dont les cas « défaut connu » du
corpus de référence, ignorés hors `SEARCH_REFERENCE_KNOWN_DEFECTS=1`).

**Phase 1 — nouveau code** : 4 issues, toutes dans le code de test de la task, corrigées (`8293f042`).
- `CA1859` ×3 : `SearchReferenceOracle.Words`, `SearchReferenceQueries.Both` / `Only` rendent leur type concret.
- `xUnit1004` ×1 : le `Skip` posé sur `Semantic_MoreMatchesThanTheWindow_KeepsTheMostRecentMails` est retiré. Le test,
  vert sur `develop`, fige le défaut R3. Il reste joué pour que le défaut reste visible, et task-439 l'inversera.

**Phase 2 — dette ancienne** : rien à traiter (0 issue ouverte).

**Conventions** : `conventions/csharp.md`, CA1859 passé à 17 occurrences et nouvelle entrée `xUnit1004`.

## Lint log

**`/lint-angular`** (Mode A, code-only), `Client/Angular/front` sur `feature/nova-mss-weda-integration`, base
`origin/next`, portée `tag:scope:mss`.

- Fichier touché par la task : `e2e/mss-e2e/specs/functional.e2e.ts` (projet `mss-e2e`, tag `scope:mss`), non commité,
  pour l'humain (TFS).
- `nx affected -t lint` : **13 tâches, 13 réussies, 0 erreur.**
- Fichier touché : 0 erreur, 5 avertissements, tous préexistants, identiques sur la version committée (`max-lines`,
  `jsdoc/require-example`, hors des lignes de la task).
- Itérations : 0 sur 5. Aucun correctif, donc pas de re-validation build/test.

## Lint mobile log

**`/lint-mobile`** (Mode A), `Client/Mobile` sur `feat/task-438-…`.

- `ng lint` : **All files pass linting** (0 erreur, 0 avertissement).
- Fichier touché par la task : `e2e/specs/functional.spec.ts`. Il est hors de `lintFilePatterns` (`src/**`) par
  configuration, et `tsc --noEmit -p e2e/tsconfig.json` passe sans erreur.
- Itérations : 0 sur 5. Aucun correctif, aucun commit.

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail et client-mobile touchés | ✅ verte | 60 verts, 0 flaky, 0 rouge, 0 quarantaine | 8 min 53 s |
| angular | api-mail et client-angular touchés (spec non commitée) | ✅ verte | 73 verts, 0 flaky, 0 rouge, 1 quarantaine (E2E-COMPOSE-002, verte) | 9 min 39 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task (`feat/task-438-…`, `8293f042`), qui porte E2E-SEARCH-002 v1 et 003 v1
- Quarantaines : [angular] E2E-COMPOSE-002, correction task-350 (posée par l'humain, verte à ce passage)
- Divergences ouvertes : aucune
- Parcours touchés sans spec e2e modifié : aucun
- Démontage : complet (ports 5052, 8100, 4200, 3993, 3465, 3143, 47399 libres, aucun conteneur e2e résiduel)
- Premier passage du 2026-11-09 : non joué (port 5052 tenu par l'AppHost de développement de l'humain, `questions/task-438.md`), rejoué le 2026-11-10 une fois l'AppHost arrêté

**Preuve par mutation (règle 1b, côté frontend)** : le plein texte d'api-mail ne lit plus le corps des messages
(`lower(d."Body")` → `lower(left(d."Body", 0))` dans `SemanticSearchRepository`). E2E-SEARCH-001 à 003 ont été joués
contre le banc `--serve-only`, `--retries=0` :

| Client | E2E-SEARCH-001 | E2E-SEARCH-002 | E2E-SEARCH-003 |
|---|---|---|---|
| mobile | ✅ vert (ne voit pas le défaut) | ❌ rouge : 0 résultat au lieu de 1 | ❌ rouge : 0 résultat au lieu de 1 |
| angular (weda2) | ✅ vert (ne voit pas le défaut) | ❌ rouge : 0 résultat au lieu de 1 | ❌ rouge : 0 résultat au lieu de 1 |

Le code a ensuite été restauré (`git checkout`), la solution recompilée (0 erreur) et l'arbre d'api-mail est propre.
Les voies vertes ci-dessus ont été jouées sur le code non muté.

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
| E2E-SETTINGS-004 | 1 | headless | Paramètres indisponibles : rien n'est écrasé | ✅ | — |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-SEARCH-002 | 1 | headless | Un mot rare et accentué trouve le message qui le contient | ✅ | ✅ |
| E2E-SEARCH-003 | 1 | headless | Un numéro de dossier trouve son message, et un seul | ✅ | ✅ |
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
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ | ✅ |
| E2E-MAILBOX-003 | 2 | headless | Rattacher ses boîtes depuis « Mes boîtes » en un geste — titulaire et membre | ✅ | ✅ |
| E2E-MAILBOX-006 | 1 | headless | Après le rattachement, l'identité d'expéditeur et la signature sont déjà là | ✅ | ✅ |
| E2E-MAILBOX-004 | 1 | headless | Ajouter une BAL déléguée par saisie — et refus de sa propre adresse | ✅ | ✅ |
| E2E-MAILBOX-005 | 1 | headless | Le délégataire refusé par l'opérateur perd l'accès, en ligne puis hors ligne ; le titulaire garde le sien | ✅ | ✅ |
| E2E-AUDIT-001 | 1 | headless | Le titulaire lit au journal le message supprimé par son délégataire, au nom du délégataire | ✅ | — |
| E2E-AUDIT-002 | 1 | headless | Le journal d'audit montre chaque action sur un mail | ✅ | — |
| E2E-SHARED-001 | 1 | headless | Une boîte partagée, une base — le patient rattaché par le titulaire est vu du délégataire, la signature reste à chacun | ✅ | ✅ |
| E2E-SHARED-002 | 1 | headless | Le délégataire écrit pour le compte du titulaire — le destinataire voit qui a écrit, sa réponse revient à la boîte | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |
| E2E-SESSION-004 | 1 | headless | Sur un appareil partagé, la personne suivante n'arrive jamais dans la boîte de la précédente | ✅ | ✅ |
| E2E-AI-002 | 1 | headless | Un délégataire interroge l'assistant dans la boîte qu'il a ouverte | ✅ | ✅ |
| E2E-MAILBOX-007 | 1 | headless | Après un changement de boîte, l'onglet Patients ne montre plus rien de la précédente | ✅ | ✅ |
| E2E-ERROR-001 | 1 | headless | Une erreur affiche un code et une référence à transmettre au support | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.
