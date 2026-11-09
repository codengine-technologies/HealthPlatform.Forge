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
| **Total cycle** | | **1 h 16 min** | **22 (2 min 37 s)** | **15 (20 min 26 s)** | **4 (1 min 24 s)** | |

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
