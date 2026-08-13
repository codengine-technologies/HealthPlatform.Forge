# todo-task-256.md — La page d'en-têtes coûte 51 % de plus sans émettre une requête de plus : on déduit pourquoi, on ne le mesure pas

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: **task-243** (`archived`) — sa décomposition en phases a isolé
`assemble` ; celle-ci compte **ce que cette phase construit**. Aucune dépendance
bloquante ; **task-255** est indépendante (elle traite le débit, pas le coût par
appel).
**Priorité**: **1** — c'est la **seule étape du parcours encore hors grille à 200
praticiens** hors envoi, et son remède n'est pas décidable en l'état. Sans ce
compteur, la prochaine US d'optimisation devinerait.

## Objective

Que le coût de la page d'en-têtes soit attribuable à un **volume**, et pas seulement
à une durée. Aujourd'hui on sait **combien de temps** la matérialisation prend, et
**combien de requêtes** l'appel émet. On ne sait pas **combien d'objets il
construit** — donc on ne sait pas si le remède est « moins d'objets », « des objets
moins chers », ou « ne pas les construire ici ».

C'est une US **d'instrument, pas d'optimisation**. Elle ne rend rien plus rapide.

## Ce qui est établi — et qui rend cette US nécessaire

Deux tirs à protocole identique (escalier 50/100/200 distant, mêmes boîtes, chauffe
intégrée), `journey-247-proof` du 2026-08-09 puis `journey-lot254-n200` du
2026-08-10 :

| `GetMailsByUids` | 09-08 | 10-08 | |
|---|---|---|---|
| **Requêtes SQL par appel** | **15,8** | **15,8** | identique au millième |
| Matérialisation | 433,3 ms | **654,5 ms** | **+51 %** |
| Attente d'une connexion | 0,1 ms (0,0 %) | 0,1 ms (0,0 %) | négligeable, deux fois |
| Étape « ouvrir l'inbox », p95 à 200 | 1 380 ms ❌ | **3 154 ms** ❌ | +129 % |

**Le travail demandé n'a pas changé** — même nombre de requêtes, même code de
lecture. Ce qui a changé est le **volume de données à construire** : la chauffe
aboutit désormais pour **100 %** des médecins contre 94,5 %, et **plus vite**
(961 s contre 1 156 s), grâce à task-254. La fenêtre de régime contient donc plus de
contenu enrichi.

**Cette explication est une déduction, pas une mesure.** Elle est solide — trois
indices concordants — mais **aucun compteur ne dit combien d'objets l'appel a
construits**. Tant qu'il manque, « il y a plus de contenu » ne peut ni être vérifié,
ni être chiffré, ni servir à dimensionner un remède.

**Rappel du poids de l'enjeu** : la matérialisation vaut **83,7 %** du coût de cet
appel, et cet appel est le **premier poste du parcours du médecin** (finding
F-242-1, confirmé sur quatre campagnes).

## Ce que la US doit livrer

Le pendant, pour les **objets**, de ce que task-243 a fait pour les **requêtes** :
un compteur par appel, **ventilé par famille d'objet**, publié à côté de la durée de
la phase — de sorte que le rapport puisse rendre un **coût par objet**.

Les familles à distinguer sont celles que le dépôt charge en lots séparés : les
**messages** eux-mêmes, leurs **étiquettes**, leurs **destinataires**, leurs **pièces
jointes**, leurs **identifiants enrichis**, leurs **acquittements de biologie**. Ce
découpage n'est pas de la commodité : chacune désigne un remède différent, et c'est
le critère de découpage qu'a retenu task-252.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que le coût est proportionnel au nombre d'objets.** Il peut être
  dominé par **une seule** famille, par le suivi de changements d'EF, ou par une
  allocation par objet indépendante de sa taille. C'est précisément ce que la
  ventilation doit trancher.
- **Ne pas présumer que ce sont les messages.** La page en affiche 25 ; ce sont
  probablement les familles satellites qui font le volume. Le supposer d'emblée
  reviendrait à choisir le remède avant la mesure.
- **Ne pas optimiser en passant.** Si une évidence saute aux yeux, la consigner comme
  finding et la traiter dans une US suivante — mesurée. Cette EPIC a déjà annulé une
  US applicative écrite sur une cause plausible et fausse (task-222).
- **Ne pas re-mesurer ce qui l'est déjà** : le nombre de requêtes par appel (15,8) et
  la durée de la phase sont acquis. Cette US ajoute **le dénominateur qui manque**.

## Definition of Done

- [ ] Un compteur donne le **nombre d'objets matérialisés par appel** de
      `GetMailsByUids`, **ventilé** par famille (messages, étiquettes, destinataires,
      pièces jointes, identifiants enrichis, acquittements)
- [ ] Le même compteur couvre `GetMail`, l'autre lecture servie par la base — sans
      quoi on ne pourra pas comparer les deux chemins
- [ ] `report.py` publie le **coût par objet** et la **phrase attribuable** : « sur
      les X ms de matérialisation, l'appel a construit N objets, dont … »
- [ ] **Hors périmètre, rien ne coûte** : sans scope actif, ni allocation ni série
- [ ] Une absence de donnée écrit **« non relevé »**, jamais un zéro
- [ ] **Contre-épreuve chiffrée** : à corpus identique, le compteur explique-t-il
      l'écart de **+51 %** observé entre les deux tirs ? Si non, le rapport le **dit**
      — et c'est alors la déduction actuelle qui est fausse, ce qui est un résultat
- [ ] Tests unitaires du compteur, dont un cas « aucun objet » et un cas
      multi-familles
- [ ] **Aucune donnée de santé dans les étiquettes** : ni INS, ni objet de message,
      ni nom de fichier — seulement des noms de familles pris dans un ensemble fini

## Manual Test Plan

- Monter le banc (skill `loadtest-skill`), en mode **distant** — c'est la seule
  configuration honnête depuis le constat du 9 août
- Purger les tables, chauffer une boîte, puis ouvrir la boîte de réception depuis
  l'application : la liste doit afficher **exactement** les mêmes messages, avec les
  mêmes compteurs de fils, étiquettes et marqueurs de pièce jointe qu'avant
- Lire la section « Où part le temps d'une lecture servie par la base » : le nombre
  d'objets et le coût par objet doivent y figurer
- Ouvrir la même boîte **avant** puis **après** chauffe : le compteur d'objets doit
  augmenter, et la durée de matérialisation suivre — c'est la contre-épreuve
- Vérifier dans Seq qu'aucune étiquette ne porte de donnée patient

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — observabilité interne
- **Exigences DSR honorées** : aucune — aucun changement fonctionnel
- **INS** : ⚠️ les identifiants enrichis comptés par ce compteur **peuvent porter de
  l'INS**. Le compteur ne doit publier qu'un **nombre** et un **nom de famille** :
  aucune valeur d'identifiant, aucun sujet de message, aucun nom de fichier. C'est le
  point de vigilance n°1 de cette US, et un test doit l'épingler.
- **Authentification PS / Habilitations** : inchangées — le cloisonnement « une base
  par praticien » n'est pas touché
- **Consentement patient / Interop CI-SIS / MSSanté** : non applicable
- **Tracé PGSSI-S** : métriques d'exploitation uniquement, corrélées par `traceId`
- **Hébergement HDS** : l'instrument doit être transposable à l'environnement cible
- **AIPD / impact RGPD** : inchangé — aucune donnée nouvelle collectée, seulement des
  décomptes

## Branches
- `api-mail` (pushed) : feat/task-256-compteur-objets-materialises — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-256-compteur-objets-materialises
- `dtos-mss` (pushed, auto-included) : feat/task-256-compteur-objets-materialises — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-256-compteur-objets-materialises

## Develop log

- **Repos touchés** : `api-mail` (`dtos-mss` branché par auto-inclusion, **aucun
  commit** — cette US ne change aucun contrat, donc pas de publication NuGet et
  pas de PR DTO).
- **DTOs publiés** : aucun changement de contrat.
- **Interop publié** : aucun changement.
- **Commits** :
  - `api-mail` a47fbaa `feat(telemetry): compter les objets qu'une lecture servie par la base construit`
  - `api-mail` b7ce914 `feat(bench): publier le coût par objet, et rendre la contre-épreuve du +51 % falsifiable`

### Ce qui a été livré

**L'instrument** — `mssante_db_operation_objects_total`, un compteur ventilé par
`(operation, family)`, publié à la fermeture du périmètre `DbOperationScope`
existant (task-243). Il vient donc **à côté** de la durée de la phase `assemble`,
sur le même périmètre, sans nouvel instrument de durée.

- `src/Application/Telemetry/DbObjectFamily.cs` (nouveau) — l'énumération des
  familles et leurs étiquettes.
- `DbOperationScope` — un compartiment par famille, cumulatif, publié à la
  fermeture ; sentinelle « non observé » distincte de zéro.
- `MailProcessingMetrics.RecordDbOperationObjects` — la publication.
- `MailRepository` — les points de comptage, un par lot chargé.

**Le typage comme garde-fou de confidentialité.** La signature prend un
`DbObjectFamily`, **pas une chaîne** : la fuite d'un nom de fichier, d'un sujet de
message ou d'un INS dans une étiquette n'est pas seulement interdite, elle est
impossible à écrire. C'est le point de vigilance n°1 du task file, traité par le
compilateur plutôt que par la discipline.

**Les familles.** Le task file en nomme six et donne le critère : « celles que le
dépôt charge en lots séparés ». Les six sont livrées — `messages`, `tags`,
`recipients`, `attachments`, `enriched_ids`, `biology_acks` — **et les six autres
lots que le même critère désigne** : `medical_documents`, `biology_results`,
`summary_items`, `contents`, `thread_links`, `duplicate_refs`.

> ⚠️ **C'est un écart assumé à l'énumération littérale du task file, et il est
> nécessaire.** Les six familles nommées sont toutes bornées par la page (25
> messages et leurs satellites immédiats). Or la déduction que cette US doit
> vérifier est « la fenêtre de régime contient plus de **contenu enrichi** » — et
> ce contenu vit précisément dans les six autres lots. S'en tenir aux six nommées
> aurait produit un dénominateur incapable, par construction, de faire varier le
> résultat : la contre-épreuve chiffrée du DOD n'aurait pas pu se tromper, donc
> n'aurait rien prouvé. Cardinalité : 12 familles × 3 opérations, littéraux
> connus à la compilation.

**Le rapport** — nouvelle section « Combien d'objets une opération servie par la
base construit-elle », rendue juste après la décomposition des phases (dont elle
est le dénominateur) : décompte par famille, matérialisation en regard, **coût par
objet en µs**, phrase attribuable, et la **contre-épreuve** sous forme falsifiable
— au coût par objet mesuré, les 221,2 ms d'écart entre les deux tirs exigent N
objets de plus par appel ; le tir de référence confronte ce nombre à son propre
décompte.

### Vérification locale

| Suite | Résultat |
|---|---|
| `dotnet build HealthPlatform.Api.Mail.sln` | ✓ 0 erreur, 0 avertissement |
| `mss.mail.domain.tests` | ✓ 136 / 136 |
| `mss.mail.infrastructure.tests` | ✓ 450 / 450 (dont 8 nouveaux) |
| `mss.mail.application.tests` | 2 134 / 2 136 — **2 rouges pré-existants**, cf. ci-dessous |
| `mss.mail.api.tests` | ✓ 661 / 661 |
| `mss.mail.integration.tests` | ✓ 402 / 402 (16 ignorés) |
| `python -m unittest discover` (loadtest-k6) | ✓ 286 / 286 (dont 16 nouveaux) |

**Les 2 rouges d'`application.tests` sont pré-existants, vérifié par contre-épreuve**
(`git stash` du travail de la task, même commande, même machine) :
`AiPromptHelperTests.GetPromptShouldContainDocumentIntroduction` (rouge
systématique) et `MailExportServiceTests.BuildPdfWithoutAttachmentsOmitsAttachmentSection`
(flaky PDF connu, cf. mémoire `project_api_mail_preexisting_flaky_tests`).

**Une collision de capture a été supprimée, une autre est nommée et reste ouverte.**
Le meter d'OpenTelemetry est statique : un `MeterListener` capte les mesures de
toutes les classes de test qui tournent au même instant, et les assertions de ces
classes sont de la forme « exactement une enveloppe publiée ». Les six classes qui
capturent ce meter partagent désormais une collection xUnit
(`MailMetricsCaptureCollection`) qui les sérialise. Aucune assertion n'a été
relâchée — « exactement une enveloppe par opération » est précisément la propriété
qui rend les décompositions lisibles.

- **Réglé** : la collision `DbOperationScopeTests` ↔ `DbOperationObjectCountTests`,
  apparue dès l'ajout du compteur et rouge de façon déterministe. Les deux classes
  sont dans la collection ; elles ne se croisent plus.
- **Nommé mais non réglé** : `EnrichmentOperationScopeTests` reste rouge par
  intermittence (constaté sur `develop` **avant** cette task, par contre-épreuve,
  et encore sur le tir Release avec collecte de couverture). La cause est plus
  large que la précédente : ce ne sont pas seulement les classes de capture qui
  émettent sur les instruments d'enrichissement, mais **les tests de service
  réels** — `ImapServiceTests` ouvre un `EnrichmentOperationScope`,
  `AddNewMailConsumerTests` publie la phase `embedding`, `CdaParsingServiceTests`
  alimente `xdm_extract`. Les sérialiser toutes reviendrait à mettre une part
  notable de la suite dans une collection unique. **Hors périmètre de cette
  task** : c'est un défaut d'outillage de test antérieur, et le remède demande
  une décision de conception (corrélation par étiquette de test, ou capture par
  `Meter` dédié) qui mérite sa propre US.

> ⚠️ **Le tir en parallèle de toute la solution reste bruyant** (91 échecs
> d'`integration.tests` quand les cinq assemblages tournent ensemble, 0 quand
> `integration.tests` tourne seul) : contention sur les conteneurs Testcontainers,
> antérieure à cette task et hors de son périmètre.

### DOD — auto-contrôle

- [x] Compteur d'objets par appel de `GetMailsByUids`, ventilé par famille
- [x] Le même compteur couvre `GetMail`
- [x] `report.py` publie le coût par objet et la phrase attribuable
- [x] Hors périmètre, rien ne coûte : ni allocation ni série (test
      `Outside_any_scope_counting_objects_publishes_nothing`)
- [x] Une absence de donnée écrit « non relevé », jamais un zéro (tests des deux
      côtés : C# `A_lot_that_was_never_loaded_publishes_nothing_at_all`, Python
      `test_a_family_never_loaded_stays_none_and_is_excluded_from_the_total`)
- [x] Contre-épreuve chiffrée publiée sous forme falsifiable, et « non relevé »
      quand la fenêtre ne permet pas de conclure
- [x] Tests unitaires du compteur, dont « aucun objet » et multi-familles
- [x] Aucune donnée de santé dans les étiquettes — garanti par le typage énuméré,
      épinglé par deux tests (unitaire et sur la lecture réelle)
- [ ] **Différé au test manuel (HAG)** : la lecture au banc en mode distant, la
      comparaison avant/après chauffe, et la vérification dans Seq. Ce sont des
      observations d'exploitation, pas des assertions de code.

- **Étape suivante** : `/forge-simplify task-256`

## Simplify log

- **Repos éligibles touchés** : `api-mail` (`dtos-mss` : aucun commit, et de toute
  façon hors périmètre — porteur de contrat).
- **Commit** : `api-mail` caa1880 `refactor(telemetry): un seul prédicat pour « famille connue », un seul verdict vrai`
- **Re-validation** : build ✓ 0 erreur / 0 avertissement ; `application.tests`
  2 135 / 2 136 (le seul rouge est `AiPromptHelperTests`, pré-existant) ;
  `infrastructure.tests` ✓ 450 / 450 ; `python -m unittest discover` ✓ 287 / 287.

Trois corrections, toutes sur le code frais de cette task :

| Axe | Correction |
|---|---|
| Réutilisation | `DbObjectFamilies.IsKnown` — l'accumulateur et la publication bornaient le même indice avec deux copies du prédicat, susceptibles de diverger à l'ajout d'une famille |
| Simplification | `db_object_counts` — le total somme les familles mesurées via une liste, au lieu d'un accumulateur à deux branches ; la règle « `None` n'est pas zéro » s'écrit une fois |
| Altitude | `_db_object_verdict_lines` — le verdict « zéro objet pour une matérialisation non nulle » s'écrivait sans que la durée soit mesurée, donc affirmait un fait qu'il ne tenait pas. Il exige désormais les deux mesures, et l'absence de coût par objet se lit « non relevé » |

Un test ajouté par correction (2 en Python, la première étant déjà couverte par
`A_family_outside_the_enumeration_is_dropped_rather_than_labelled_with_a_number`).

- **Étape suivante** : `/sonar task-256`

## Sonar log

Run **Mode A** (chaîné), `api-mail` sur `feat/task-256-compteur-objets-materialises`.
Analyse complète (build Release + 5 projets de tests avec couverture OpenCover +
scanner), conteneurs `sonarqube_db` puis `sonarqube` démarrés par l'agent —
ils étaient arrêtés depuis 29 h.

### KPIs qualité — baseline → final

| Métrique | Baseline (avant run) | Final | Cible |
|---|---|---|---|
| Bugs | 2 | **2** | 0 |
| Vulnérabilités | 0 | **0** | 0 ✓ |
| Code smells | 58 | **58** | — |
| Security hotspots | 4 | 5 | — |
| Couverture globale | 87,6 % | **87,6 %** | ≥ 95 % |
| Duplication | 0,3 % | **0,3 %** | < 3 % ✓ |
| Fiabilité | C | **C** | A |
| Sécurité | A | **A** | A ✓ |
| Maintenabilité | A | **A** | A ✓ |

### Quality Gate (new code) — `ERROR`, et **aucun finding attribuable à task-256**

| Condition | Avant | Après | Verdict |
|---|---|---|---|
| `new_coverage` | 88,0 % | **88,0 %** | ✓ OK (seuil 80 %) |
| `new_duplicated_lines_density` | 0,06 % | **0,06 %** | ✓ OK (seuil 3 %) |
| `new_security_hotspots_reviewed` | 50,0 % | **100,0 %** | ✓ **passé au vert par ce run** |
| `new_violations` | 59 | **59** | ✗ ERROR (seuil 0) |

**Provenance des 59 violations : vérifiée finding par finding, zéro n'appartient
au code écrit par cette task.** La new-code period du projet est
`PREVIOUS_VERSION` (héritée), donc sa fenêtre englobe plusieurs tasks déjà
mergées — piège déjà rencontré et consigné en mémoire
(`project_sonar_new_code_baseline_includes_prior_tasks`). Détail :

| Fichier | Findings | Appartient à |
|---|---|---|
| `report.py` | 12 × S3776, 3 × S1192, 2 × S3358, S1172, S1244 | fonctions **antérieures** (`_journey_*`, `reduce_prom_matrix`, `db_phase_decomposition`, `run_verdict`, `build_report`…) — lignes 1622 à 5167, **aucune** dans les fonctions ajoutées par task-256 (4069, 4289–4470) |
| `scenarios/journey*.js` | 8 × S1940, 2 × S3776, 2 × S2486, S6582 ×2, S6035, S4624 | harnais k6 (task-174/247) |
| tests C# divers | 12 × CA1861, xUnit2032, CA1816 | tasks antérieures |
| `MailClientSession*.cs`, `MailServerDiscovery.cs`, `IheXdmProcessingService.cs`, `EnrichmentFetchPlan.cs`, `SmtpConnectionFactory.cs`, `EmbeddingInputBounderFactory.cs` | S125 ×3, S3267 ×2, S4457, S4456, S103, CA1859 | tasks antérieures |
| `ContactRepository.cs` | S2302 | **périmètre de task-259** (task suivante du run) |

### Ce que le run a corrigé

**Les 5 security hotspots `TO_REVIEW` du new code ont été revus et classés `SAFE`
avec justification** — c'est la seule condition du Quality Gate que ce run pouvait
légitimement faire passer, et elle est passée de 50 % à 100 %.

- `test_report_db_objects.py:42` — **le seul hotspot du code de cette task** : URL
  `http://prom` d'une fixture de test unitaire. Jamais appelée — le test remet à la
  fonction de rendu un payload Prometheus déjà construit, aucun octet ne transite.
  Traitement conforme à l'entrée `python:S5332` de `conventions/python.md`.
- `test_report_db_phases.py:41` et `:196` — même motif, code antérieur.
- `scenarios/journey.js:414` et `:587` — `Math.random()` modélise le temps de
  réflexion d'un médecin et le nombre de rafales de frappe au clavier dans le
  harnais k6. Aucun usage cryptographique : la valeur ne protège rien, ne génère ni
  jeton ni identifiant, et n'entre dans aucune donnée persistée.

### Phase 2 (dette legacy) — **skippée délibérément**

Best-effort par définition, et ici elle est refusée sur un motif de fond, pas de
temps : corriger 59 findings répartis sur 15 fichiers **sans lien avec cette US**
ferait franchir à la PR la limite de la règle 5 (~30 fichiers) et violerait la
règle 6 (périmètre isolé). Surtout, cette EPIC tient tout entière sur
l'**attribution** — mêler à une US d'instrument des corrections de dette venues
d'ailleurs rendrait son diff illisible et son gain inattribuable, exactement ce
que la dépendance à task-243 existe pour éviter.

Les 14 findings S3776 (12 Python + 2 JS) sont de toute façon hors du périmètre de
`/sonar` : règle blacklistée, traitée par `/sonar-s3776`, une méthode par PR.

> **Finding pour le PO** — la new-code period `PREVIOUS_VERSION` héritée rend le
> Quality Gate structurellement rouge tant que la dette des tasks mergées depuis
> la dernière « version » n'est pas soldée, et elle empêche toute task de savoir si
> *elle* a introduit de la dette sans faire l'analyse de provenance à la main
> (faite ici). Deux remèdes possibles : solder ce lot dans une US de dette dédiée,
> ou passer la new-code period à `NUMBER_OF_DAYS` / référence sur `develop`. C'est
> une décision de configuration, pas de code.

- **Étape suivante** : `/lint-angular task-256`

## Lint log (client-angular)

⤍ **Skippé proprement** — `**Repos**: api-mail`, aucun code Angular écrit par
cette task. Aucun fichier de `Client/Angular/front/` touché, donc rien à
auto-fixer et rien à valider. Le filet des frontends appairés est désactivé, donc
`client-angular` n'a pas été ajouté implicitement.

- **Étape suivante** : `/lint-mobile task-256`

## Lint mobile log

⤍ **Skippé proprement** — `**Repos**: api-mail`, aucun code mobile écrit par cette
task. `Client/Mobile/` est sur `develop`, arbre propre, aucun commit depuis la
base : rien à linter, rien à committer.

- **Étape suivante** : `/verify-visual task-256`

## Visual verify log

⤍ **Skippé proprement** — aucun écran `client-mobile` touché (`**Repos**: api-mail`,
aucun `## Stitch design log` sur cette task). Rien à capturer, aucune référence
Stitch à apparier.

- **Étape suivante** : `/review task-256`

## PRs

- `api-mail` — **#188** https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/188
  (label `awaiting-human-merge`, mergeable, `feat/task-256-compteur-objets-materialises` → `develop`)
- `dtos-mss` — **aucune PR** : la branche a été créée par auto-inclusion mais ne
  porte aucun commit. Cette US ne change aucun contrat, donc aucune publication
  NuGet et aucun consommateur à bumper.
- `client-angular`, `client-mobile`, `client-blazor` — non listés, non touchés.
- `devops`, `psc-proxy-*` — hors automation, gérés manuellement par l'humain.

## Code Review Summary

**Verdict : APPROVED** — 15 fichiers revus, **0 blocage**, 2 suggestions non
bloquantes. Détail complet recopié dans le body de la PR #188.

| Axe | Verdict |
|---|---|
| Correctness | ✅ aucune requête ajoutée, retirée ni modifiée — le diff **observe**. Vérifié à la lecture des 17 points d'insertion ; 402 tests d'intégration et 450 tests de dépôt inchangés et verts |
| Sécurité / PGSSI-S | ✅ aucune étiquette ne **peut** porter de donnée de santé (typage énuméré, pas discipline) ; aucun secret, aucune entrée externe |
| Architecture | ✅ réutilise le périmètre `DbOperationScope` de task-243 plutôt que d'ajouter un instrument concurrent ; `Application` porte la télémétrie, `Infrastructure` l'alimente |
| Qualité de code | ✅ passe `/forge-simplify` appliquée (prédicat unique, total sans accumulateur à branches, verdict qui n'affirme que le mesuré) |
| Performance | ✅ un `long[12]` par périmètre, `Interlocked.Add`, aucun parcours de collection ajouté — chaque comptage lit un `.Count` déjà matérialisé |
| Couverture de test | ✅ 32 cas : l'accumulateur **et** la lecture réelle du dépôt. Les premiers prouvent la justesse, les seconds que les appels sont posés aux bons endroits — c'est le défaut qui rendrait le compteur menteur sans paraître faux |

### Suggestions (non bloquantes, consignées comme findings)

1. **F-256-1 — allocation du tableau de compartiments.** Les 96 octets par
   périmètre sont payés aussi par `EnrichPersistMail`, qui ne compte aucun objet.
   Une allocation paresseuse l'éviterait, au prix d'un `CompareExchange` sur la
   référence du tableau. Non rentable devant l'objet `DbOperationScope` lui-même ;
   à reconsidérer si l'écriture devient un point chaud d'allocation.
2. **F-256-2 — double comptage assumé des pièces jointes de document.** Sur
   `GetMail` avec contenu, une pièce jointe rattachée à un document est
   matérialisée par les deux lectures, donc comptée deux fois. Correct pour
   « objets construits » (ce sont bien deux DTO), désormais dit explicitement dans
   le code — mais un lecteur pressé du tableau pourrait y lire un nombre de lignes.
3. **F-256-3 — collision de capture du meter, non réglée.** Voir le `## Develop
   log` : `EnrichmentOperationScopeTests` reste rouge par intermittence en
   collision avec les tests de service réels. Antérieur, plus large que cette task,
   remède = décision de conception (corrélation par étiquette de test, ou `Meter`
   dédié par classe de capture).
4. **F-256-4 — new-code period `PREVIOUS_VERSION` héritée.** Rend le Quality Gate
   structurellement rouge et empêche une task de savoir si *elle* a introduit de la
   dette sans analyse de provenance manuelle. Décision de configuration.
