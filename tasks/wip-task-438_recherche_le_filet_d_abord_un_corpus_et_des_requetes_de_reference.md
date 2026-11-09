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
