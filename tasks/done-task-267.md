# todo-task-267.md — Le corpus du banc n'a aucun fil de discussion : on ne peut pas mesurer ce qu'on optimise

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune. **Sert de préalable de mesure** à **task-194**
(comptage de fils borné) et, accessoirement, à **task-266** (gating du calcul).
Aucune des deux n'est bloquée par celle-ci — elles sont livrables avant, avec
une mesure partielle qu'elles doivent alors **déclarer comme telle**.
**Priorité**: **3** — outillage de banc. Aucun impact produit, aucun risque
patient.

> **Origine** : constat du 2026-08-20, en instruisant task-266 sur question
> humaine (« comment le test k6 consomme le chargement des listes ? »).

## Objective

Que le corpus semé sur le banc contienne des **fils de discussion**, pour que le
coût du comptage de fils — celui que task-194 optimise — soit réellement exercé
par une campagne.

## Ce qui est établi — état du code au 2026-08-20

`BuildMime` (`tests/mss.mail.loadtest.seed/Program.cs:312-334`) construit chaque
message synthétique avec **`From`, `To`, `Subject`, corps et pièces jointes**, et
rien d'autre. Ni `In-Reply-To`, ni `References`. Une recherche de ces deux
en-têtes sur le seeder et sur le harnais k6 ne renvoie **aucune** occurrence.

Conséquence sur `MailRepository.GetThreadCountsAsync` (`:4039`), le chemin que
task-194 vise :

| Étape de la requête | Sur le banc actuel | Sur une boîte réelle |
|---|---|---|
| `existingMessageIds` — tous les `MessageId` de la base | **exercée** (scan complet, N lignes matérialisées) | exercée |
| `allMailsWithReferences` — lignes porteuses de `References`/`InReplyTo` | **0 ligne** | N lignes |
| Boucle `racines de la page × allMailsWithReferences` avec `Contains` sur `dynamic` | **à vide** — 0 itération | **le coût dominant** |

`MimeKit` génère automatiquement un `Message-Id` à l'envoi, donc la première
requête ramène bien N lignes : **la moitié du coût est mesurée**. La seconde
moitié — celle que task-194 chiffre à « 50 racines × 50 000 lignes = 2,5 millions
de recherches de sous-chaîne à répartition dynamique par page » — ne l'est pas
du tout.

**Ce que ça implique** : une campagne conclurait aujourd'hui à un gain modeste
pour task-194, non parce que le correctif est modeste, mais parce que le banc
n'exerce pas ce qu'il corrige.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que le défaut est neutre.** Semer des fils **change le
  corpus**, donc rompt la comparabilité stricte avec toutes les campagnes
  antérieures. C'est acceptable, mais cela doit être **dit** — même exigence que
  task-264 pour le re-fenêtrage de la chauffe. Une mesure dont l'instrument a
  changé sans le dire n'est pas une mesure.
- **Ne pas présumer qu'il faut semer beaucoup.** Une part trop élevée de
  réponses rendrait le corpus atypique dans l'autre sens : une boîte MSSanté
  réelle n'est pas majoritairement composée de fils. La part doit être
  **paramétrable** et son défaut **justifié**, pas choisi au hasard.
- **Ne pas présumer que le défaut du paramètre peut être non nul.** Le
  comportement par défaut du seeder doit rester **exactement** celui
  d'aujourd'hui, sinon toute campagne relancée sans y penser change de nature en
  silence.
- **Ne pas présumer que c'est cosmétique.** Sans fils, un futur régresseur du
  comptage de fils passerait inaperçu sur le banc : le coût qu'il réintroduirait
  serait multiplié par zéro.
- **Ne pas confondre avec task-266.** Celle-ci ne parle pas du calcul ni de son
  déclenchement — uniquement du corpus.

## Ce que la US doit livrer

1. **Des fils dans le corpus semé** : une part paramétrable des messages répond
   à un message précédent de la **même boîte**, avec `In-Reply-To` et
   `References` conformes RFC 5322 (`References` cumulant la chaîne, pas
   seulement le parent).
2. **Défaut rétro-compatible** : sans réglage explicite, le seeder produit
   exactement le corpus d'aujourd'hui (aucun fil). L'activation est **opt-in**.
3. **Des fils de profondeur variée**, pas uniquement des paires — le coût du
   comptage dépend de la longueur des chaînes, et une chaîne de deux ne
   ressemble pas à une chaîne de six.
4. **Le rapport dit ce qu'il a semé** : part de messages en fil et profondeur
   moyenne apparaissent dans le rapport de campagne, au même titre que les
   autres paramètres de corpus. Une campagne dont on ne peut pas relire le
   corpus n'est pas rejouable.
5. **La rupture de comparabilité est énoncée** dans le rapport quand la part est
   non nulle : « ce tir n'est pas comparable aux campagnes à corpus sans fil ».
6. **Un contrôle de budget qui tient** : les fils consomment des UID comme les
   autres messages ; le contrôle de budget de corpus (tasks 253/264) doit
   continuer de passer, ou refuser explicitement.

### Hors scope

- **L'optimisation du comptage** → task-194.
- **Le gating du calcul** → task-266.
- La représentativité clinique du contenu des messages : on sème des en-têtes de
  fil, pas des échanges médicaux vraisemblables.
- Les fils **inter-boîtes** (un message et sa réponse dans deux boîtes
  différentes) : la mesure porte sur le comptage intra-base, une boîte à la fois.

## Definition of Done

- [ ] Build passe (`dotnet build HealthPlatform.Api.Mail.sln`, 0 erreur)
- [ ] Tests passent (0 échec, hors flaky pré-existants documentés)
- [ ] Auto-tests du harnais verts (`selftest.sh`), **tests JS compris**
- [ ] Test : sans réglage explicite, le corpus produit est **identique** à celui
      d'aujourd'hui — aucun `In-Reply-To`, aucun `References`
- [ ] Test : avec une part non nulle, les messages en fil portent un
      `In-Reply-To` **et** un `References` cumulant la chaîne complète, et les
      `Message-Id` référencés **existent** dans la même boîte
- [ ] Test : la profondeur des fils varie (au moins deux profondeurs distinctes
      sur un corpus semé)
- [ ] Test : le rapport de campagne publie la part de messages en fil et la
      profondeur moyenne
- [ ] Test : quand la part est non nulle, le rapport **énonce** la rupture de
      comparabilité
- [ ] Le contrôle de budget de corpus continue de passer (ou refuse
      explicitement, avec un message nommant le geste)
- [ ] **Vérification sur pièce** : après un semis avec fils, la seconde requête
      de `GetThreadCountsAsync` ramène un nombre de lignes **non nul** —
      constaté, pas déduit. C'est le seul critère qui prouve que la US atteint
      son but
- [ ] Aucune donnée de santé : corpus 100 % synthétique, aucun INS, aucun
      contenu clinique réel

## Manual Test Plan

1. Monter le banc local : `cd Api/Mail && dotnet run --project src/AppHost`
   avec le profil « loadtest ».
2. **Semis de référence** — lancer le seeder **sans** réglage de fil.
   **Attendu** : corpus identique à d'habitude. Vérifier en base que la colonne
   `References` est vide sur l'ensemble des messages.
3. **Semis avec fils** — relancer le seeder avec une part non nulle sur une
   boîte neuve. **Attendu** : une partie des messages porte `In-Reply-To` et
   `References` ; les identifiants référencés existent dans la même boîte.
4. Ouvrir la boîte de réception dans le front legacy, **basculer le mode
   d'affichage sur « Conversation »**. **Attendu** : des fils apparaissent, avec
   des badges « N messages » cohérents avec ce qui a été semé.
5. Lancer une campagne courte et ouvrir le rapport. **Attendu** : la part de
   messages en fil et la profondeur moyenne y figurent, et la mention de rupture
   de comparabilité est présente.
6. Vérifier que le contrôle de budget de corpus ne refuse pas la campagne.

**Données de test** : corpus synthétique uniquement, aucun patient réel, aucun
INS.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — outillage de banc, aucune exigence produit
- **Exigences DSR honorées** : aucune — aucun changement fonctionnel
- **INS** : sans objet — outillage de test, données 100 % synthétiques
- **Authentification PS** : inchangée — hors périmètre
- **Habilitations** : sans objet
- **Interop CI-SIS** : sans objet — les en-têtes posés sont des en-têtes de
  transport RFC 5322 (`In-Reply-To`, `References`), pas du contenu métier
- **Tracé PGSSI-S** : inchangé
- **Consentement patient** : sans objet
- **Référentiels métier** : aucun
- **Hébergement HDS** : sans objet — environnement de banc
- **AIPD / impact RGPD** : inchangé — aucun traitement nouveau, aucune donnée
  personnelle

## Branches

- `api-mail` (pushed) : feat/task-267-corpus-fils-de-discussion — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-267-corpus-fils-de-discussion
- `dtos-mss` (pushed, auto-inclus) : feat/task-267-corpus-fils-de-discussion — aucune modification attendue (outillage de banc, aucun contrat)

Préfixe `feat/` : ajout d'une capacité au seeder, opt-in et rétro-compatible.

> **Contexte au lancement** : task-266 est mergée, sa mesure banc **reste due**
> et sera **minorée** tant que ce corpus n'existe pas. task-194 est révisée et
> attend, sa mesure étant dans le même cas — c'est elle que ce corpus sert
> d'abord, puisqu'elle optimise précisément la part de coût aujourd'hui vide.

## Develop log (2026-08-22)

Livré en `1728d25`.

### Ce que la task change, et ce qu'elle préserve

**Opt-in et rétro-compatible** : défaut `--thread-share 0` = corpus d'hier à
l'identique — aucun en-tête de fil, aucun `Message-Id` imposé (MimeKit continue
d'en générer un à l'`APPEND`). Semer des fils **rompt la comparabilité** avec les
campagnes antérieures ; l'activation doit donc être un geste explicite, jamais un
effet de bord d'une mise à jour du harnais.

### ⭐ Le test a réfuté ma première conception avant la livraison

Premier jet : un cycle **figé** de longueurs de fil (1, 2, 4 réponses). Le test
« la part demandée est tenue » a échoué à **0,75**, et la raison est arithmétique :
une chaîne de `R` réponses consomme `R+1` messages, donc la part maximale
atteignable est `R/(R+1)` — soit **0,70** avec ce cycle. Une part de 0,75 demandée
n'aurait pas été tenue, **et le rapport aurait publié un chiffre faux**.

Les longueurs **dérivent** désormais de la part : `R ≥ part/(1−part)`, avec trois
longueurs consécutives pour que le corpus ne soit pas fait que de paires — le coût
du comptage dépend de la longueur des chaînes, et un corpus de paires mesurerait
un cas particulier en le faisant passer pour la règle.

### Le rapport dit de quel corpus le tir parle

Nouvelle section « **Corpus — fils de discussion** » :

- la **part semée**, déclarée au tir (`CORPUS_THREAD_SHARE`) au même titre que
  `MESSAGES_PER_USER` — le harnais ne relit pas le corpus, et le commentaire du
  code le dit : *c'est une déclaration, pas une mesure* ;
- la **taille moyenne d'un fil**, **déduite** de la part et **nommée comme telle**.
  Publier un chiffre dérivé comme s'il était relevé est la façon la plus simple de
  rendre un rapport faux sans mentir ;
- quand la part est non nulle, l'**énoncé explicite de la rupture de
  comparabilité** ;
- **à part nulle**, l'inverse : ce que le tir **ne peut pas** mesurer, pour qu'un
  gain publié sur ce chemin soit lu comme un **plancher**. C'est ce qui rend
  lisible, rétroactivement, la mesure due de task-266.

### Vérification sur pièce — le critère qui juge la US

`SeededThreadsAreCountableTests` part du **vrai générateur**, insère ses messages
tels que l'ingestion les stockerait (identifiants **sans chevrons** — ce que
MimeKit rend à la lecture, donc ce que la base contient), et interroge le **vrai**
comptage :

| Part semée | Résultat de `GetThreadCountsAsync` |
|---|---|
| `0` | **vide** — aucun fil comptable |
| `0,5` | fils comptables, tailles **égales aux chaînes semées**, plusieurs profondeurs distinctes |

**Constaté, pas déduit.** Rejouer une fixture écrite à la main aurait prouvé que
le comptage sait compter — pas que le corpus sait produire des fils.

### Contrôle de budget de corpus : inchangé, et vérifiable

`checkBudgets` **ne lit pas** la part de fil (grep : 0 occurrence), et le nombre
de messages semés ne bouge pas — donc les réserves d'UID non plus. Le remède ne
se paie pas en refus de campagne.

### Tests

| Niveau | Nombre |
|---|---|
| Générateur (`LoadTestThreadCorpusTests`) | **12** |
| Option CLI (`SeedOptionsTests`) | **4** |
| Intégration, vrai comptage | **4** |
| Rapport (`test_report_corpus_threads`) | **8** |

Dont un test que je signale parce qu'il a failli manquer : la part est lue en
**culture invariante**. Sur un poste français, `double.TryParse` par défaut refuse
`0.3` et le réglage retomberait **silencieusement à 0** — un corpus non fileté
qu'on croirait fileté, et une campagne qui ne mesure pas ce qu'elle annonce.

**Mutation vérifiée** sur l'énoncé de rupture de comparabilité : le rendre muet →
rouge.

### État des suites

api **681/681**, application **2 163/2 163**, domain **136/136**,
infrastructure **464/464**, integration **416/433** (17 ignorés = les `UC-AI-*`
dépendants d'Ollama, sans rapport — vérifié nommément).
`selftest.sh` : **94 JS + 305 Python**, 0 échec, **0 SKIP** (297 → 305).
Build 0 erreur, **0 avertissement**.

### Ce qui reste à la main de l'humain

Le corpus **existe** désormais ; l'**exercer** demande une campagne. Concrètement :
semer avec `--thread-share 0.3` (par exemple), lancer le tir avec
`CORPUS_THREAD_SHARE=0.3` pour que le rapport le dise, et **refaire** les mesures
de task-266 — et de task-194 quand elle sera livrée — pour remplacer leurs
planchers par des chiffres représentatifs.

## Simplify log (2026-08-22)

Passe qualité `/forge-simplify` sur `api-mail` — commit `7a77664`.
Repos éligibles touchés : `api-mail` seul (pas de `dtos-mss`/`interop-cda`,
porteurs de contrat, ni de frontend).

### Ce qui a été corrigé

| # | Constat | Correction |
|---|---|---|
| 1 | Une part de fils de **1,0** était acceptée des deux côtés, et produisait une **taille moyenne de 0** dans le rapport — un chiffre absurde publié sans broncher. | Borne haute rendue **stricte**. Le générateur lève (`Thread share must be in [0, 1)`), le rapport dit « déclaration incohérente ». La branche morte `threadShare >= 1.0 ? MaxMessagesPerUser` de `DepthsFor` disparaît avec elle. |
| 2 | La formule de taille de fil vit en **deux copies**, dans deux langages et deux processus — la configuration exacte où une divergence passe inaperçue et où le rapport finit par publier une taille que le corpus n'a pas. | Les deux copies sont **épinglées l'une à l'autre**. Côté C#, `ThePublishedAverageThreadSizeIsTheOneTheCorpusActuallyProduces` **mesure** le corpus réellement produit (il ne re-dérive pas la formule) et le compare aux mêmes chiffres que `test_the_derived_average_matches_the_generator_rule` publie côté Python. Toucher l'une sans l'autre rend l'un des deux rouge. |
| 3 | `CORPUS_THREAD_SHARE_MAX` était utilisé comme borne **exclue**. | Renommé `CORPUS_THREAD_SHARE_EXCLUSIVE_MAX`. |

**Une part de 1 n'est pas constructible** : le premier message d'une boîte n'a
personne à qui répondre. La refuser franchement vaut mieux que la servir avec un
chiffre faux — c'est la même règle que le reste de l'EPIC applique aux mesures.

### Ce qui n'a PAS été touché

- `dtos-mss` / `interop-cda` — porteurs de contrat, hors charte de l'étape.
- Le comportement du corpus à part utile (`0 < s < 1`) : identique au commit
  `1728d25`. Les tests existants sont le filet, et ils sont restés verts sans
  être réécrits.
- `S138` sur `LoadBulkContentLookupsAsync` — pré-existant, prouvé identique à
  `develop` (md5sum), délibérément non corrigé ici.

### Validation

| Suite | Résultat |
|---|---|
| Build solution | **0 erreur, 0 warning** |
| `mss.mail.api.tests` | **685 / 685** (+4 : 3 cas du pin cross-langage, 1 cas borne stricte) |
| `mss.mail.application.tests` | 2162 / 2163 — l'échec est le flaky PDF pré-existant `MailExportServiceTests.BuildPdfWithoutAttachmentsOmitsAttachmentSection`, **vert en isolation** (22/22) |
| `mss.mail.infrastructure.tests` | **464 / 464** |
| `mss.mail.domain.tests` | **136 / 136** |
| Intégration fils (`SeededThreadsAreCountable` + `ThreadCountConvergence`) | **15 / 15** |
| `selftest.sh` du harnais | **94 JS + 306 Python**, 0 échec, 0 SKIP |

## Sonar log (2026-08-22)

Scan complet sur `feat/task-267-corpus-fils-de-discussion` (commit `7a77664`) —
`begin` → build Release → tests avec couverture OpenCover → `end`,
`EXECUTION SUCCESS`. Projet `healthplatform-api-mail`.

### KPIs qualité (baseline → final)

| Métrique | Baseline (analyse du 2026-08-06) | Final (task-267) | Δ |
|---|---|---|---|
| **Quality Gate (new code)** | ERROR | **ERROR** | inchangé |
| `new_violations` | 37 | 70 | +33 — **non imputable** (voir ci-dessous) |
| `new_coverage` | 0,0 % | 78,6 % | **artefact de mesure**, pas un gain |
| `new_duplicated_lines_density` | 0,073 % | 0,055 % | OK |
| `new_security_hotspots_reviewed` | 0 % | 0 % | inchangé |
| Bugs / Vulnérabilités / Smells (projet) | 2 / 0 / 38 | 2 / 0 / 70 | +32 smells, non imputables |
| Coverage projet | 0,0 % | 78,3 % | artefact de mesure |
| Duplication projet | 0,4 % | 0,3 % | — |
| Ratings (Reliab. / Sec. / Maint.) | 3,0 / 1,0 / 1,0 | **3,0 / 1,0 / 1,0** | inchangés |
| `ncloc` | 44 527 | 47 477 | +2 950 |

### ⚠️ Deux chiffres de ce tableau ne veulent pas dire ce qu'ils ont l'air de dire

1. **La ligne baseline ne décrit pas `develop` d'aujourd'hui.** La dernière
   analyse remontait au **2026-08-06**, sur un commit antérieur de ~2 950 lignes
   (44 527 → 47 477 ncloc). Entre les deux, les tasks 226 à 266 ont mergé. Le
   `+33` de `new_violations` mesure donc **deux mois de merges**, pas le diff de
   task-267. C'est le piège déjà consigné pour cette EPIC : la *new-code period*
   est `PREVIOUS_VERSION` datée du **2026-04-17**, elle englobe des dizaines de
   tasks déjà mergées.

2. **Le passage de 0 % à 78,3 % de couverture n'est pas un gain.** Le tir du
   2026-08-06 n'avait produit aucun rapport OpenCover ; celui-ci en a produit 4.
   On est passé de « non mesuré » à « mesuré », ce qui n'est pas la même chose
   que « amélioré ».

### Attribution ligne à ligne — ce que task-267 introduit vraiment

Les 70 violations et les 10 hotspots de la *new-code period* ont été rapportés à
leur fichier **et à leur ligne**, puis croisés avec le diff de la task
(`git diff origin/develop...HEAD`).

| Fichier de la task | Findings Sonar dedans |
|---|---|
| `tests/mss.mail.testing.shared/LoadTestPlanGenerator.cs` | **0** |
| `tests/mss.mail.loadtest.seed/SeedOptions.cs`, `Program.cs` | **0** |
| `tests/loadtest-k6/lib/config.js`, `lib/summary.js` | **0** |
| `tests/loadtest-k6/report.py` — **bloc ajouté, lignes 5378–5483** | **0** |
| `tests/loadtest-k6/test_report_corpus_threads.py` | **0** |
| `tests/mss.mail.api.tests/LoadTest/*.cs` | **0** |
| `tests/mss.mail.integration.tests/Repository/SeededThreadsAreCountableTests.cs` | **0** |

**Total imputable à task-267 : 0 violation, 0 hotspot.**

Les 22 findings de `report.py` sont tous **hors** du bloc ajouté (lignes 864 à
5334, plus le S3776 de `build_report` à la ligne 5484). Ce dernier mérite d'être
nommé parce que c'est le seul cas limite : `build_report` est bien **adjacent**
au code de la task, et task-267 y a ajouté 3 lignes — deux commentaires et un
`lines.extend(corpus_threads_lines(ctx))`. Aucune branche, aucune boucle, aucun
opérateur booléen : la complexité cognitive de 22 est inchangée par
construction, pas par mesure indirecte.

### Aucune itération de nettoyage

L'étape est un **no-op propre** : il n'y a rien à nettoyer qui appartienne à
cette task. Les 70 violations restantes sont de la dette antérieure, et les
corriger ici ferait exploser le périmètre de la PR (règle 5 : ~30 fichiers max)
en mélangeant deux sujets. Elles restent visibles pour un `/sonar` dédié.

### Tests pendant le scan (Release)

| Suite | Résultat |
|---|---|
| `domain` | 136 / 136 |
| `application` | 2162 / 2163 — flaky PDF pré-existant (`MarkdownPdfRendererTests.RenderHeadingPreservesText`, PdfPig) |
| `infrastructure` | 464 / 464 |
| `api` | **685 / 685** |

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/199
  — label `awaiting-human-merge`, état MERGEABLE.
- `dtos-mss` : branche `feat/task-267-corpus-fils-de-discussion` créée par
  `/start` (auto-inclusion), **aucun commit** — outillage de banc, aucun contrat
  touché. Pas de PR.
- `client-angular`, `client-mobile`, `client-blazor` : hors périmètre
  (`**Repos**: api-mail`, `**Single frontend**: true`).
- `devops`, `psc-proxy-*` : managed manually by the human.

## Code Review Summary

**Verdict : APPROVED** — 10 fichiers revus, 2 suggestions non bloquantes,
0 blocage.

| Fichier | Verdict |
|---|---|
| `tests/mss.mail.testing.shared/LoadTestPlanGenerator.cs` | ✅ `ThreadPlan` déterministe (aucun aléa), `References` racine-en-tête conforme RFC 5322 § 3.6.4, identifiants portant l'index de boîte — un fil ne peut pas traverser deux boîtes |
| `tests/mss.mail.loadtest.seed/Program.cs` | ✅ en-têtes posés **uniquement** quand le corpus est fileté ; identifiants sans chevrons (MimeKit les pose lui-même) |
| `tests/mss.mail.loadtest.seed/SeedOptions.cs` | ✅ `ParseDouble` en `InvariantCulture`, testé contre la locale machine |
| `tests/loadtest-k6/lib/config.js`, `lib/summary.js` | ✅ la forme du corpus voyage avec le tir |
| `tests/loadtest-k6/report.py` | ✅ section + témoin négatif ; le chiffre dérivé est nommé comme tel |
| Tests (4 fichiers, 31 cas) | ✅ portent sur des faits mesurés, pas sur des intentions |

### Suggestions (non bloquantes)

1. **`ParseDouble` retombe silencieusement sur le défaut.** `--thread-share abc`
   vaut 0 sans un mot. C'est la convention existante du fichier (`ParseInt` fait
   pareil), donc pas une régression introduite ici — mais pour cette option-là un
   0 silencieux veut dire « aucun fil semé » pendant que l'opérateur croit le
   contraire. Un refus franc sur option numérique illisible mérite une task
   transverse, pas un traitement particulier ici.
2. **Deux déclarations indépendantes du même fait** : `--thread-share` (seeder)
   et `CORPUS_THREAD_SHARE` (k6). Rien ne les relie ; un désaccord produit un
   rapport qui décrit avec assurance un corpus qui n'a pas été semé. C'est le
   contrat déjà assumé par `MESSAGES_PER_USER` et c'est documenté aux deux
   endroits — le script de campagne gagnerait à passer une seule valeur aux deux.

### Sécurité / données de santé

Corpus 100 % synthétique (`lt-{boîte}-{index}@loadtest.local`), aucun INS, aucun
contenu clinique, aucun secret. Les en-têtes posés sont des en-têtes de transport
RFC 5322, pas du contenu métier. Rien de nouveau n'est journalisé.

## DOD — vérification

| Critère | Verdict |
|---|---|
| Build 0 erreur | ✅ 0 erreur, **0 warning** |
| Tests 0 échec (hors flaky documentés) | ✅ api 685/685, infra 464/464, domain 136/136, intégration 417/433 (16 ignorés `UC-AI-*`/Ollama) ; application 2162/2163 — flaky PDF pré-existant, **vert en isolation** |
| `selftest.sh` vert, **JS compris** | ✅ 94 JS + 306 Python, 0 échec, 0 SKIP |
| Sans réglage → corpus identique | ✅ `WithoutAnyShareTheCorpusCarriesNoThreadHeaderAtAll` |
| Part non nulle → `In-Reply-To` + `References` cumulés, identifiants existants | ✅ `EveryReplyPointsAtAMessageThatExistsInTheSameMailbox`, `ReferencesAccumulateTheWholeChainWithTheRootFirst` |
| Profondeurs variées | ✅ `ThreadsHaveSeveralDistinctDepths`, `SeveralDistinctThreadSizesReachTheCounter` |
| Rapport publie part + profondeur | ✅ `test_a_threaded_corpus_publishes_its_share`, `test_the_average_thread_size_is_published_and_named_as_derived` |
| Rapport énonce la rupture de comparabilité | ✅ `test_a_threaded_corpus_states_the_comparability_break` (+ témoin négatif) |
| Contrôle de budget de corpus | ⏳ **différé au Manual Test Plan** — `assertUidBandsExist` est un garde d'exécution k6 qui exige un banc vivant. Statiquement, le nombre de messages semés est **indépendant** de la part (`GenerateMessages` boucle `1..count` quoi qu'il arrive) : les fils ajoutent des en-têtes, pas des messages, donc la bande d'UID visée est inchangée |
| **Vérification sur pièce** — 2ᵉ requête de `GetThreadCountsAsync` non vide | ✅ `AThreadedCorpusProducesCountableThreads` + `TheCountedThreadsMatchTheSeededChains` (intégration, vraie base, vrai générateur) |
| Aucune donnée de santé | ✅ corpus synthétique, aucun INS, aucun contenu clinique |

## Étapes de la chaîne

| Étape | Résultat |
|---|---|
| `/develop` | ✅ `1728d25` |
| `/forge-simplify` | ✅ `7a77664` — borne stricte + épinglage cross-langage |
| `/sonar` | ✅ scan complet, **0 finding imputable** |
| `/lint-angular` | ⏭️ skip — `client-angular` non touché |
| `/lint-mobile` | ⏭️ skip — `client-mobile` non touché |
| `/verify-visual` | ⏭️ skip — aucun écran mobile touché |
| `/review` | ✅ APPROVED, PR #199 ouverte |

