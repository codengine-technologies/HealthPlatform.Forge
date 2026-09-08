# todo-task-193.md — CDA sans identifiant de document : marqué doublon d'un document d'un autre patient, puis masqué

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axe métier MSSanté).

> ### Re-vérification du 2026-08-23 — **toujours pertinente, intégralement**
>
> Chaque preuve rejouée sur `develop`. Les numéros de ligne du bloc « Preuve »
> datent du 2026-07-25 ; **la colonne « au 2026-08-23 » fait foi**.
>
> | Preuve | 2026-07-25 | Au 2026-08-23 | État |
> |---|---|---|---|
> | Identifiant fabriqué `"_"` | `CdaParsingService.cs:181` | **`:202`** — `DocumentId = $"{…id?.root}_{…id?.extension}"`, inconditionnel | inchangé |
> | Bon patron déjà voisin | `:171-177` (`SetId` laissé nul) | **`:203`** — `SetId = setId`, calculé nul quand ses deux parties sont vides, **une ligne plus bas** | inchangé |
> | Doublon sans prédicat de patient | `MailRepository.cs:2765-2776`, `:2807-2822` | **`:3763`** — `.Where(d => d.DocumentId == documentId && d.Version == version && d.Mail != null)`, **toujours aucun** prédicat de patient ni d'INS | inchangé |
> | Masquage des doublons | `PatientRepository.cs:208`, `:406`, `:883` | **`:516`** (`ActiveDocumentsForPatient`, prédicat désormais **centralisé** par task-233) et **`:1022`** | inchangé |
>
> **Un point qui simplifie la livraison** : task-233 a factorisé le prédicat
> « documents actifs de ce patient » dans `ActiveDocumentsForPatient`
> (`PatientRepository.cs:511-516`). Les trois sites de filtrage cités en 2026-07-25
> n'en font plus que **deux**, dont un centralisé — le point 3 (« ne pas masquer en
> cas de doute ») se règle donc à **un** endroit au lieu de trois.

## Objective

Empêcher que deux documents cliniques **de patients différents** soient déclarés
doublons l'un de l'autre — et donc que l'un disparaisse du dossier patient.

Quand un émetteur non conforme omet l'identifiant du document CDA, l'identifiant
est construit par interpolation et vaut la chaîne littérale `"_"`. Cette valeur
franchit le garde-fou de non-vacuité, et la détection de doublons compare les
identifiants **sans aucun critère de patient ni d'INS**. Le second document reçu est
donc marqué comme doublon du premier — et toutes les requêtes du dossier patient
filtrent les doublons : le document est **absent du dossier** et du tableau de bord,
jusqu'à ce que le praticien le retrouve dans sa boîte et rejette manuellement un
signal de doublon qui référence… le document d'un autre patient.

**US backend-only (justification)** : parsing et détection côté serveur.

### Preuve (état actuel du code)

- `src/Application/Services/Implementation/CdaParsingService.cs:181` — construction
  inconditionnelle :
  ```csharp
  DocumentId = $"{cda.ClinicalDocument.id?.root}_{cda.ClinicalDocument.id?.extension}"
  ```
  Si l'`id` est absent (ou `<id root="" extension=""/>`), le résultat est `"_"`, qui
  passe le test `!string.IsNullOrWhiteSpace(documentId)`.
- Contraste dans le même fichier : `SetId` (`:171-177`) est **délibérément laissé
  nul** quand ses deux parties sont vides. Le bon patron est donc déjà connu, à
  quelques lignes.
- `src/Infrastructure/Repository/MailRepository.cs:2765-2776` et `:2807-2822` —
  `FindExactDuplicateIdAsync` compare `d.DocumentId == documentId && d.Version == version`
  **sans aucun prédicat de patient ni d'INS** (`Version` étant nul des deux côtés,
  l'égalité est satisfaite).
- Le masquage : les requêtes patient filtrent
  `d.DuplicateOfId == null || d.DuplicateRejected`
  (`src/Infrastructure/Repository/PatientRepository.cs:208`, `:406`, `:883`).

### Contenu attendu

1. **Pas d'identifiant fabriqué** : un document sans identifiant exploitable doit
   avoir un identifiant **nul**, jamais une chaîne dégénérée. Aligner le traitement
   sur celui déjà appliqué à `SetId`.
2. **Détection de doublons bornée au patient** : deux documents ne peuvent être
   déclarés doublons que s'ils concernent le **même** patient. Un identifiant absent
   ne doit jamais suffire à conclure au doublon.
3. **Repli explicite** : pour un document sans identifiant, définir la règle de
   détection retenue (empreinte de contenu ? aucune détection ?) et la documenter.
   Le principe : en cas de doute, **ne pas masquer** le document — un doublon affiché
   est un désagrément, un document masqué est un risque clinique.
4. **Inventaire des documents déjà masqués** : requête de lecture seule recensant
   les documents marqués doublons dont le patient (ou l'INS) **diffère** de celui du
   document référencé — signature du défaut. La remédiation touche des données de
   santé : arbitrage humain, task dédiée si l'inventaire remonte des cas.

### Hors scope

- La détection de doublons pour les documents **correctement** identifiés
  (comportement conservé).
- Le rattachement patient lui-même → task-176.
- Le versionnement de documents (`SetId` / `Version`), non concerné.

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test unitaire : CDA sans `id` (absent, ou `root`/`extension` vides) ⇒
      identifiant **nul**, jamais `"_"` (ce test doit échouer sur le code actuel — le
      vérifier explicitement)
- [ ] Test unitaire : deux documents sans identifiant, de **patients différents**,
      ne sont pas déclarés doublons ; les deux sont visibles dans leur dossier
      patient respectif
- [ ] Test unitaire : deux documents de **même** identifiant et **même** patient
      sont toujours détectés comme doublons (non-régression)
- [ ] Test unitaire : deux documents de même identifiant mais de patients
      **différents** ne sont pas déclarés doublons
- [ ] Test d'intégration : un document sans identifiant apparaît bien dans le dossier
      patient et dans le tableau de bord
- [ ] Requête d'inventaire des documents masqués à tort livrée et documentée
- [ ] Aucune donnée de santé en clair dans les logs ni dans la requête d'inventaire

## Manual Test Plan

1. Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
2. Préparer **deux** CDA de patients **différents** (données de test anonymisées),
   tous deux **sans** identifiant de document (`<id>` absent, ou `root` et
   `extension` vides) — la forme émise par certains producteurs non conformes.
3. Envoyer le premier vers la boîte de test, synchroniser → il apparaît dans le
   dossier de son patient.
4. Envoyer le second, synchroniser. **Attendu** : il apparaît dans le dossier de
   **son** patient. Avant correctif, il est marqué doublon du premier et **absent**
   du dossier ; il n'est visible qu'en boîte de réception, avec un signal de doublon
   pointant sur le document d'un autre patient.
5. **Non-régression** : envoyer deux fois le **même** CDA (identifiant renseigné,
   même patient) → le second est bien signalé comme doublon, comme aujourd'hui.
6. **Non-régression versionnement** : envoyer une version supérieure d'un document
   (même `SetId`, `Version` incrémentée) → la chaîne de versions fonctionne comme
   avant.
7. Exécuter la requête d'inventaire sur une base antérieure au correctif → elle
   remonte les documents masqués à tort.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — volet documents de santé (CDA)
- **Exigences DSR honorées** : correctif de conformité — complétude du dossier
  patient et robustesse face à des documents non conformes reçus
- **INS** : **directement concerné** — la détection de doublons doit être bornée au
  patient, donc à son identité ; c'est l'absence de ce prédicat qui provoque le
  défaut
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : CDA r2 — le défaut se déclenche sur des documents **non
  conformes** au volet (identifiant de document obligatoire). Le correctif ne doit
  pas relâcher la validation Schematron de `interop-cda`, mais garantir que la
  non-conformité d'un émetteur ne fasse pas disparaître un document
- **Tracé PGSSI-S** : journaliser la réception d'un document sans identifiant
  exploitable (évènement technique, sans contenu) — utile pour identifier les
  émetteurs non conformes
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : **à mettre à jour** — inexactitude/incomplétude du
  dossier patient (art. 5.1.d) : des documents cliniques ont pu être masqués.
  Qualifier la portée via l'inventaire, avec le DPO.


## Branches

Créées par `/start` le 2026-09-08 depuis `origin/develop`.
Nom unique : `fix/task-193-cda-sans-identifiant-doublon-inter-patients`.

- `api-mail` (pushed) : `fix/task-193-cda-sans-identifiant-doublon-inter-patients` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-193-cda-sans-identifiant-doublon-inter-patients
- `dtos-mss` (pushed) : `fix/task-193-cda-sans-identifiant-doublon-inter-patients` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/fix/task-193-cda-sans-identifiant-doublon-inter-patients — **auto-incluse** (règle CLAUDE.md : toute US touchant `api-mail` peut avoir besoin d'un changement de contrat). Restera sans commit et sans PR si le contrat ne bouge pas.

Préfixe `fix/` : correctif d'un défaut constaté, pas une capacité nouvelle.

**Repos non concernés** : les trois frontends ne sont pas listés
(`**Single frontend**: true`) — le défaut est entièrement serveur (parsing CDA et
détection de doublons). Le masquage qu'il provoque est visible côté client, mais
sa cause et sa correction sont dans les requêtes du dossier patient.

### Note de pré-flight

`wip-task-291` coexiste : elle est **parquée sur un fail-fast documenté**
(non-déterminisme de la suite de tests), état que le protocole `/forge` produit
lui-même. Elle ne touche aucun des fichiers de cette task.

## Timings

*(généré par `tools/timing/report.sh --task task-193 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 59 s | — | — | — | — |
| /develop | ok | 21 min 13 s | — | — | — | — |
| /sonar | ok | 8 min 15 s | 1 (21 s) | 5 (3 min 58 s) | 1 (1 min 48 s) | api-mail 1B/5T |
| /lint-angular | skipped | 17 s | — | — | — | client-angular hors Repos, aucune ligne ecrite par /develop |
| /lint-mobile | skipped | 2.5 s | — | — | — | client-mobile hors Repos, arbre vide |
| /verify-visual | skipped | 2.1 s | — | — | — | aucun ecran client-mobile touche |
| /review | ok | 4 min 45 s | 2 (16 s) | 1 (1 min 35 s) | — | dtos-mss 1B/0T, api-mail 1B/1T |
| **Total cycle** | | **35 min 36 s** | **3 (38 s)** | **6 (5 min 34 s)** | **1 (1 min 48 s)** | |

## Develop log — 2026-09-08

### Ce qui est livré

| Point attendu | État | Où |
|---|---|---|
| 1 — pas d'identifiant fabriqué | **fait** | `CdaParsingService.ComposeIdentifier`, partagé avec `SetId` |
| 2 — détection bornée au patient | **fait** | `FindExactDuplicateIdAsync` **et** `LoadActiveSetVersionsAsync` |
| 3 — repli explicite documenté | **fait** | sans INS ⇒ aucune détection ; sans identifiant ⇒ aucune détection exacte |
| 4 — inventaire des documents masqués | **fait** | `Docs/task-193-inventaire-doublons-inter-patients.sql` + test d'intégration |

**Contrat** : `dtos-mss` republié en **458.0.0** (`DocumentId` → `string?`),
`api-mail` bumpé. `client-blazor` **non bumpé** — il n'est pas dans `**Repos**`
et cette task ne le touche pas ; il restera sur 454.0.0 jusqu'à une task qui le
concerne.

### La règle de repli, tranchée et dite

- **Sans identifiant** (émetteur non conforme) ⇒ **aucune détection exacte**.
  L'empreinte de contenu a été écartée : elle **devine**, et se tromper ici
  masque un document clinique.
- **Sans INS** ⇒ **aucune détection du tout**, sur les deux chemins. Comparer
  sur le seul identifiant rétablirait le défaut sous une autre forme — deux
  patients inconnus confondus. C'est aussi la règle que task-176 a posée sur le
  rattachement : ne jamais deviner un patient sans INS.
- **Deux documents non identifiés d'un MÊME patient** ne sont pas non plus
  déclarés doublons : il n'y a rien à comparer, et deux comptes rendus distincts
  du même patient émis par un producteur non conforme ne sont pas le même
  document.

### Une migration, non prévue par la task mais inévitable

`MailMedicalDocuments.DocumentId` était `NOT NULL` (et `IsRequired()` côté EF) :
un identifiant nul était donc **impossible à stocker** — c'est d'ailleurs
pourquoi le parseur en fabriquait un. `SetId`, lui, est nullable depuis le
schéma initial. La migration `20260908100000` aligne les deux.

Relue (règle 7c) : une seule altération de colonne, aucune opération fantôme.
PostgreSQL retire une contrainte `NOT NULL` par mise à jour de catalogue — pas
de réécriture de table. Le `Down` est **volontairement lossy et commenté** : il
restaure `"_"` sur les lignes nulles, donc il **re-crée la collision** — c'est
ce que revenir en arrière signifie ici, et le dire vaut mieux que le cacher.

**Les lignes existantes portant `"_"` sont laissées telles quelles** : les
réécrire serait une modification de données de santé. Les identifier est l'objet
de l'inventaire ; les remédier est une décision humaine (task dédiée si
l'inventaire remonte des cas).

### Deux tests existants assertaient le défaut

- `MailRepositoryTests.AddNewMailWithDuplicateDocumentIdShouldFlagAsync` semait
  **deux INS différents** et son commentaire disait *« prove that DocumentId
  alone is enough to trigger the duplicate flag »*. Il bénissait exactement le
  comportement à corriger. Inversé, et **doublé** d'un test même-patient pour ne
  pas perdre la couverture de non-régression.
- `CdaParsingServiceTests.BuildCdaDocumentDto_EmptyDocument_MapsSafeDefaults`
  assertait `Equal("_", DocumentId)` en annotant `// "{null}_{null}"` — sans
  relever que la ligne **suivante** attend `null` sur `SetId`. L'asymétrie était
  écrite noir sur blanc, deux lignes l'une sous l'autre, depuis task-034.

Les 10 tests INT.18 ne posaient **aucun INS** : ils décrivaient deux documents
d'un même patient sans le dire, parce que le modèle ne l'exigeait pas. Le décor
le dit maintenant.

### Tests

| Assembly | Résultat |
|---|---|
| `application` | 2311 verts |
| `infrastructure` | 475 verts |
| `api` | 818 verts |
| `integration` | 448 verts (16 ignorés) |

Nouveaux : 7 sur l'identifiant (`CdaDocumentIdentifierTests`, **prouvés rouges
sur le code d'avant** — 4 échecs, 3 non-régressions vertes), 8 sur la détection
inter-patients, 5 d'intégration sur vrai PostgreSQL (dont la migration exercée
et l'inventaire asserté sur des données réelles, pas seulement livré en fichier).

### Rouge restant, non imputable

`MarkdownPdfRendererTests.RenderHeadingPreservesText` — famille PDF, et **un test
différent à chaque exécution** (`MailExportServiceTests` puis
`EnrichmentOperationScopeTests` puis celui-ci sur trois passes). Signature exacte
de **task-291** (non-déterminisme sur trois assemblies, parquée sur fail-fast).

### Passe qualité §Q

`api-mail` : relecture du diff — **aucun cleanup appliqué**, donc pas de commit
vide ni de re-validation. `ComposeIdentifier` factorise déjà les deux
identifiants, et le prédicat de patient est posé identiquement sur les deux
requêtes. `dtos-mss` : exclu (porteur de contrat).


## Sonar log — 2026-09-08

Conteneurs déjà UP (démarrés au cycle task-186). Un scan complet sur la branche
(build Release + 5 passes OpenCover).

### KPI

| Métrique | Valeur |
|---|---|
| bugs | 2 |
| vulnerabilities | 0 |
| code_smells | 73 |
| security_hotspots | 15 |
| coverage | 88,0 % |
| duplicated_lines_density | 0,3 % |
| reliability / security / sqale rating | 3.0 / 1.0 / 1.0 |
| issues totales projet | 75 |

### Findings sur les fichiers touchés : **1, non imputable**

| Règle | Fichier | Verdict |
|---|---|---|
| `S138` méthode de 106 lignes | `MailRepository.cs:1416` (`LoadBulkContentLookupsAsync`) | **non imputable** — présente à la **même ligne** sur `origin/develop`, et **zéro occurrence** dans mon diff (mes modifications sont toutes entre les lignes 3715 et 3819). Sonar attribue au fichier, pas à la méthode. |

**Aucun cleanup appliqué** : il n'y avait rien à corriger de mon fait.
**Zéro itération consommée** sur les cinq autorisées.

### Quality Gate : ERROR — et pourquoi ce n'est pas cette task

| Condition | État | Valeur |
|---|---|---|
| `new_coverage` | OK | 88,0 % (seuil 80) |
| `new_duplicated_lines_density` | OK | 0,049 % (seuil 3) |
| `new_security_hotspots_reviewed` | **ERROR** | 0 % (seuil 100) |
| `new_violations` | **ERROR** | 74 (seuil 0) |

Les deux conditions rouges sont **antérieures** : la *new-code period* du projet
inclut des tasks déjà mergées, constat déjà consigné. Les 15 *security hotspots*
non revus n'ont pas bougé depuis task-186. Le total projet passe de 73 (mesuré
sur la branche task-186) à 75, l'écart venant de ce qui a été mergé sur `develop`
entre-temps — pas de mon diff, dont un seul fichier porte une issue, et elle est
pré-existante.

### Note sur la suite de tests

Un rouge, `MarkdownPdfRendererTests.RenderHeadingPreservesText`, et c'est **un
test différent à chaque exécution** (`MailExportServiceTests`, puis
`EnrichmentOperationScopeTests`, puis celui-ci). Signature de **task-291**.
Les quatre autres assemblies sont vertes.


## Lint log — client-angular — 2026-09-08

**Skip propre.** `client-angular` n'est pas listé dans `**Repos**`
(`**Single frontend**: true`) et `/develop` n'y a écrit aucune ligne : le défaut
est entièrement serveur — parsing CDA et détection de doublons.

Les deux seuls fichiers modifiés dans `Client/Angular/` sont
`apps/mss/src/environments/environment.ts` et son équivalent `weda2` : **WIP
humain**, antérieur à cette task et laissé strictement intact (code-only, la
forge n'y touche jamais).

Skip **mesuré** (`--status skipped`) plutôt que silencieux.


## Lint mobile log — 2026-09-08

**Skip propre.** `client-mobile` n'est pas dans `**Repos**`, aucune branche n'y a
été créée par `/start`, son arbre de travail est vide et il est resté sur
`develop`. Rien à linter.

Skip **mesuré** (`--status skipped`).


## Visual verify log — 2026-09-08

**Skip propre.** Aucun écran `client-mobile` touché, aucun `## Stitch design
log` dans la task. Ni serveur `ng serve` démarré, ni capture Playwright.

Le défaut corrigé est **invisible à une capture d'écran** : ce qui manquait,
c'était un document *absent* d'une liste. La preuve qu'il y est de nouveau est
un test d'intégration contre un vrai PostgreSQL
(`UnidentifiedDocumentVisibilityIntegrationTests`), pas une image. Le plan de
test manuel demande la vérification à l'œil côté praticien, sur les deux
frontends.

Skip **mesuré** (`--status skipped`).


## PRs — 2026-09-08

| Repo | PR | Label |
|---|---|---|
| `dtos-mss` | https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/31 | `awaiting-human-merge` |
| `api-mail` | https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/221 | `awaiting-human-merge` |

**Ordre de merge** : `dtos-mss` → `api-mail`. Le paquet **458.0.0** est consommé
par le second.

**Repos non concernés** : les trois frontends (`**Single frontend**: true`) — le
défaut est entièrement serveur. `client-angular` porte deux `environment.ts`
modifiés, WIP humain antérieur, laissés intacts.

## Code Review Summary — APPROVED

12 fichiers relus, **0 blocage**, 2 suggestions non bloquantes (factorisation
éventuelle des quatre `.Where` communs aux deux requêtes de détection ; volume du
`Warning` PGSSI-S sur un émetteur systématiquement non conforme). Détail dans le
body de la PR #221.

**Validation finale** : builds verts sur les deux repos, **4193 tests, zéro
échec** — la suite est redevenue déterministe, le correctif de task-291 (PR #220)
ayant été mergé sur `develop` et intégré ici pendant la synchronisation.
