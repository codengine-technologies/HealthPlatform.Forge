# todo-task-176.md — Documents médicaux sans INS agrégés sur un patient arbitraire (commingling de dossiers)

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axe accès données).
> Finding vérifié sur pièces par le PO — voir « Preuve » ci-dessous.

## Objective

Empêcher le **mélange de dossiers patients** lors de l'ingestion de documents
médicaux dépourvus d'INS. Aujourd'hui, tout document sans INS est rangé sous la
clé `""` d'un dictionnaire de patients, et **le premier patient sans INS trouvé en
base lui est attribué** : deux documents concernant deux patients différents,
tous deux sans INS, sont rattachés au **même** dossier. Le praticien ouvrant ce
dossier voit les documents cliniques d'un autre patient.

Le chemin d'ingestion frère (« promote ») se garde correctement — les deux
chemins sont donc **incohérents entre eux**, ce qui confirme que le bucketing sur
`""` n'est pas un choix métier assumé mais un défaut.

**US backend-only (justification)** : défaut d'ingestion serveur. Aucun contrat
ni écran modifié — mais voir la remédiation des données existantes ci-dessous,
qui a un impact métier visible.

### Preuve (état actuel du code)

- `src/Infrastructure/Repository/MailRepository.cs:260-273` — les patients **sans
  INS** sont délibérément chargés puis regroupés sous la clé vide, dont on ne
  garde qu'un représentant arbitraire :
  ```csharp
  var hasMissingIns = medicalDocuments.Exists(d => string.IsNullOrEmpty(d.PatientIns));
  var patients = await DataContext.MailPatients
      .Where(p => (p.Ins != null && insValues.Contains(p.Ins)) || (hasMissingIns && p.Ins == null))
      .ToListAsync();
  return patients.GroupBy(p => p.Ins ?? string.Empty)
                 .ToDictionary(g => g.Key, g => g.First());   // <-- g.First() sur la clé ""
  ```
- `src/Infrastructure/Repository/MailRepository.cs:280-283` — la résolution
  retourne ce patient arbitraire pour tout document sans INS :
  ```csharp
  var key = medicalDocument.PatientIns ?? string.Empty;
  if (patientsByIns.TryGetValue(key, out var patient)) { return patient; }
  ```
- `src/Infrastructure/Repository/MailRepository.cs:556` — le chemin « promote »,
  lui, **ne rattache aucun patient** quand l'INS est absente :
  `if (!string.IsNullOrWhiteSpace(medicalDocument.PatientIns)) { … }`

### Règle métier retenue (décision PO)

**Un document médical sans INS n'est jamais rattaché automatiquement à un
dossier patient.** Il est ingéré avec un lien patient **absent**, et reste
rattachable **manuellement** par le praticien au workflow existant de
rattachement (task-012), qui ne rattache qu'à un patient **existant**.

Justification identito-vigilance : sans INS (ou avec une INS non qualifiée), il
n'existe **aucun trait d'appariement fiable** autorisant un rattachement
automatique. Un rattachement par nom + date de naissance est explicitement
**écarté** : le risque d'attribuer un document au mauvais patient est
inacceptable au regard du référentiel INS / identito-vigilance HAS. Cette règle
aligne le chemin d'ingestion sur le chemin « promote » déjà conforme, et sur le
garde-fou projet « pas de création de patient depuis un workflow de
rattachement ».

### Contenu attendu

1. **Correctif d'ingestion** : ne plus charger ni bucketiser les patients sans
   INS ; un document sans INS est persisté sans lien patient. Les documents
   **avec** INS conservent strictement le comportement actuel (appariement sur
   INS, réutilisation intra-lot d'une entité non encore sauvegardée).
2. **Visibilité praticien** : les documents sans lien patient doivent rester
   **trouvables** (ils ne doivent pas devenir invisibles au profit d'un silence).
   Vérifier le comportement des vues et agrégats qui joignent le patient
   (documents du jour, dossier patient, widgets) et documenter ce que voit le
   praticien pour un document non rattaché.
3. **Inventaire des données déjà mélangées** : fournir une **requête
   d'inventaire** (lecture seule, documentée) recensant par base praticien les
   dossiers patients à INS nulle portant des documents dont les traits d'identité
   (`PatientLastName` / `PatientFirstName` / `Birthday`) **divergent** — signature
   d'un mélange déjà survenu.
4. **Remédiation : hors code, arbitrage humain.** La correction des données
   existantes (détachement des documents mal rattachés) **n'est pas automatisée
   par cette task** : elle touche des données de santé en production et exige un
   arbitrage humain sur pièces, base par base. Livrable ici : l'inventaire + une
   note de remédiation. Si l'inventaire révèle des cas, ouvrir une task dédiée.

### Hors scope

- Tout appariement patient sur des traits autres que l'INS.
- La récupération d'INS via INSi (téléservice non appelé dans ce flux).
- La déduplication des patients **avec** INS (défaut distinct : lecture-écriture
  non atomique sans contrainte d'unicité → task séparée de cette exploration).
- L'exécution d'une remédiation de données en production.

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test unitaire **anti-commingling** : deux documents sans INS, de patients
      aux traits différents, ingérés successivement → **deux** entités documents
      sans lien patient, et **aucun** partage de `PatientId` (ce test doit échouer
      sur le code actuel — le vérifier explicitement)
- [ ] Test unitaire : un document sans INS ingéré alors qu'un patient à INS nulle
      **préexiste** en base → aucun rattachement à ce patient
- [ ] Test unitaire de non-régression : deux documents portant la **même** INS
      dans le même lot partagent bien un unique dossier patient (comportement
      actuel préservé)
- [ ] Test unitaire de non-régression : un document avec INS s'apparie bien à un
      patient existant portant cette INS
- [ ] Test d'intégration d'ingestion : un mail porteur d'un CDA sans INS est
      ingéré sans erreur, le document est présent et interrogeable, sans lien
      patient
- [ ] Cohérence des deux chemins d'ingestion vérifiée (ingestion nominale et
      « promote » traitent l'absence d'INS de façon identique)
- [ ] Requête d'inventaire des mélanges déjà en base livrée et documentée
      (lecture seule, exécutable par le humain, résultat interprété dans la note)
- [ ] Note de remédiation rédigée (ce qui a pu être mélangé, comment le détecter,
      quelles options de correction, quel arbitrage humain requis)
- [ ] Aucune donnée de santé en clair dans les logs (aucun INS, nom, ni contenu
      CDA journalisé par le nouveau code ni par la requête d'inventaire)

## Manual Test Plan

1. Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
2. **Préparer deux documents sans INS de patients différents** : deux messages
   MSSanté porteurs d'un CDA (ou d'un IHE_XDM) **dépourvu d'INS**, avec des
   identités patient nettement distinctes (noms, dates de naissance
   différentes) — données de test anonymisées uniquement.
3. Déposer le premier message dans la boîte, synchroniser, ouvrir le document
   côté praticien : le document est visible, **non rattaché** à un dossier
   patient (le rattachement manuel reste proposé).
4. Déposer le second message, synchroniser.
5. **Attendu** : les deux documents restent **séparés et non rattachés**. Avant
   correctif, le second document apparaît dans le dossier du premier patient —
   un praticien ouvrant ce dossier lit les données d'un autre patient.
6. **Non-régression INS** : déposer deux messages porteurs de CDA avec la **même**
   INS (patient unique) → un seul dossier patient, les deux documents dedans, la
   chronologie et l'historique de versions corrects.
7. **Rattachement manuel** : depuis un document non rattaché, exécuter le
   workflow de rattachement à un patient **existant** → le document rejoint le
   bon dossier, et aucune création de patient n'est proposée.
8. Exécuter la requête d'inventaire sur une base de test contenant des documents
   ingérés **avant** correctif → elle remonte bien les dossiers suspects.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — volets MSSanté et documents de santé (CDA)
- **Exigences DSR honorées** : correctif de conformité identito-vigilance —
  interdiction d'un rattachement de document à un patient sans identifiant
  fiable (référentiel INS / identito-vigilance HAS). Aucune nouvelle exigence
  adressée
- **INS** : **cœur du sujet**. Règle retenue : rattachement automatique
  **uniquement** sur INS présente ; absence d'INS ⇒ aucun rattachement, reprise
  manuelle par le praticien. Aucun appariement sur traits nom/naissance. Le
  statut de l'INS (qualifié / récupéré / provisoire) et la vérification de l'OID
  ne sont **pas** durcis par cette task — à traiter dans l'axe interop dédié
- **Authentification PS** : inchangée (PSC / e-CPS, niveau eIDAS substantiel)
- **Habilitations** : inchangées
- **Interop CI-SIS** : CDA r2 (volets documents de santé) — parsing inchangé,
  seule la règle de rattachement patient évolue ; validation Schematron via
  `interop-cda` inchangée
- **Tracé PGSSI-S** : journaliser l'ingestion d'un document **sans** rattachement
  patient (évènement technique, sans donnée de santé) afin de rendre la reprise
  manuelle traçable ; conservation selon la politique existante du repo
- **Consentement patient** : non applicable — aucun échange DMP / Mon Espace
  Santé déclenché par le correctif
- **Référentiels métier** : aucun code terminologique modifié
- **Hébergement HDS** : oui — environnement HDS cible de `api-mail`
- **AIPD / impact RGPD** : **à mettre à jour** — le défaut a pu provoquer une
  divulgation de données de santé entre patients au sein du dossier d'un même
  praticien, et une inexactitude de données au sens du RGPD (art. 5.1.d).
  Qualifier la portée réelle via l'inventaire, avec le DPO, avant toute
  remédiation.

## Branches
- `api-mail` (pushed) : `feat/task-176-medical-doc-no-ins-no-patient-link` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-176-medical-doc-no-ins-no-patient-link
- `dtos-mss` (pushed, auto-included) : même nom de branche — aucun changement de contrat attendu, branche créée proactivement

## Develop log

- **Repos touched** : `api-mail` uniquement. `dtos-mss` : branche créée
  (auto-inclusion) mais **0 commit** — aucun contrat modifié, pas de publication
  NuGet, pas de PR.
- **DTOs published** : no DTO change · **Interop published** : no interop change

### Ce qui a été fait

| Fichier | Changement |
|---|---|
| `src/Infrastructure/Repository/MailRepository.cs` | `LoadPatientsByInsAsync` ne charge plus que les patients porteurs d'une INS du lot (le bucket `""` disparaît) ; `GetOrCreateMedicalDocumentPatient` → `ResolveMedicalDocumentPatient`, désormais **nullable**, retourne `null` sans INS (vide/espaces inclus) ; le document est persisté sans lien patient et l'ingestion non rattachée est journalisée (DocumentId + dossier uniquement) |
| `tests/mss.mail.infrastructure.tests/Repository/MailRepositoryPatientComminglingTests.cs` *(nouveau)* | 7 tests unitaires InMemory |
| `tests/mss.mail.integration.tests/Repository/MailRepositoryNoInsIngestionTests.cs` *(nouveau)* | 4 tests d'intégration PostgreSQL réel |
| `docs/task-176-inventaire-commingling.md` *(nouveau)* | requête d'inventaire SQL (lecture seule) + note de remédiation + grille de qualification DPO |

**Décision de conception** — aucun appariement sur nom + date de naissance. Sans
INS il n'existe aucun trait d'appariement fiable ; classer un document sous le
mauvais patient est inacceptable (référentiel INS / identito-vigilance HAS). Le
correctif aligne le chemin nominal sur le chemin « promote », **déjà conforme**
(`if (!string.IsNullOrWhiteSpace(medicalDocument.PatientIns))` — vérifié, il ne
rattachait déjà rien sans INS). Les deux chemins sont désormais cohérents.

**Visibilité du document non rattaché** — vérifié : `PatientId == null` est déjà
la condition de `PendingIntegrationsCount`
(`MailRepository.cs`, 2 sites). Un document sans INS apparaît donc comme
« intégration en attente » et reste pris en charge par le workflow de
rattachement manuel (task-012). Le correctif ne crée pas de silence : il
transforme un faux rattachement en tâche explicite.

### Pourquoi des tests d'intégration en plus des unitaires

Les deux ont attrapé des choses que l'autre ne voyait pas :

1. Mes tests InMemory passaient avec `DateTimeKind.Utc` ; **PostgreSQL réel les a
   refusés** (`timestamp without time zone` n'accepte pas Kind=Utc). Le provider
   InMemory ne valide ni la nullabilité de colonne ni les FK — un schéma où
   `PatientId` serait `NOT NULL` aurait passé les unitaires et cassé en prod.
2. EF ne sait pas traduire `COUNT(DISTINCT (composite))` — d'où la livraison de
   la requête d'inventaire **en SQL** et non en LINQ. Le test d'intégration
   exécute désormais le **SQL du runbook verbatim**, ce qui valide la requête
   livrée contre le schéma réel au lieu d'une paraphrase EF.

### Commits

- `2c1ec17` fix(mail): never attach a medical document to a patient without an INS
- `9e70308` refactor(mail): simplify pass (/simplify) — task-176

### Preuve de non-vacuité

Bucketing `""` d'avant la task temporairement restauré, puis annulé : **5 des 7
tests unitaires échouent** (`AddNewMail_TwoDocumentsWithoutIns_AreNeverAttachedToTheSamePatient`,
`AddNewMail_DocumentWithoutIns_IsNotAttachedToAPreexistingInslessPatient`,
`AddNewMail_DocumentWithoutIns_CreatesNoPatientRecordAtAll`,
`AddNewMail_DocumentWithBlankIns_IsTreatedAsMissingIns`,
`AddNewMail_MixedBatch_AttachesOnlyTheDocumentCarryingAnIns`). Les **2 tests de
non-régression INS restent verts** — le correctif est bien ciblé.

### Build / tests

Build **0 erreur / 0 avertissement**.

| Projet | Résultat |
|---|---|
| `mss.mail.domain.tests` | 102 ✓ |
| `mss.mail.application.tests` | 1852 ✓ |
| `mss.mail.infrastructure.tests` | 377 ✓ (+7) |
| `mss.mail.api.tests` | 575 ✓ |
| `mss.mail.integration.tests` | 274 ✓ (+4) / 16 ignorés |

### DOD self-check

| Critère | État |
|---|---|
| Build 0 erreur | ✓ |
| Tests 0 échec | ✓ |
| Test anti-commingling (échoue sur le code actuel — vérifié) | ✓ |
| Document sans INS vs patient à INS nulle préexistant | ✓ |
| Non-régression même INS dans un lot | ✓ |
| Non-régression appariement sur INS existante | ✓ |
| Test d'intégration d'ingestion CDA sans INS | ✓ |
| Cohérence des deux chemins d'ingestion | ✓ (promote déjà conforme, vérifié sur pièce) |
| Requête d'inventaire livrée et documentée | ✓ `docs/task-176-inventaire-commingling.md`, exécutée par un test |
| Note de remédiation rédigée | ✓ même document (3 options, interdits, grille DPO) |
| Aucune donnée de santé dans les logs ni dans l'inventaire | ✓ log = DocumentId + dossier ; inventaire = ids + compteurs uniquement |

**Hors périmètre forge** : l'exécution de l'inventaire sur les bases de
production et la qualification **AIPD / CNIL** avec le DPO sont des livrables
humains (art. 5.1.d RGPD — inexactitude de données, + divulgation entre
patients).

- **Next step** : /sonar task-176

## Sonar log

Projet `healthplatform` — 1 itération d'analyse.

### KPIs qualité

| Métrique | Valeur | Cible | État |
|---|---|---|---|
| Bugs | **0** | 0 | ✓ |
| Vulnerabilities | **0** | 0 | ✓ |
| Security hotspots | **0** | revue humaine | ✓ |
| Code smells | **4** (→ 3 après fix, cf. ci-dessous) | — | — |
| Reliability / Security / Maintainability | **A / A / A** | A | ✓ |
| Coverage | **86.5 %** | 95.0 % | ✗ (cible long terme) |
| Line coverage | **90.3 %** | — | — |
| New coverage | **86.2 %** | — | QG OK |
| Duplication | **0.7 %** | — | — |
| Dette technique | **12 min** | — | — |

**Quality Gate : `ERROR`** — unique condition en échec `new_violations = 4`.
Les 3 autres sont `OK` (`new_coverage` 86.2, `new_duplicated_lines_density`
0.12 %, `new_security_hotspots_reviewed` 100 %).

### Finding introduit par task-176 — corrigé

| Règle | Fichier | Correction |
|---|---|---|
| `csharpsquid:S103` | `src/Infrastructure/Repository/MailRepository.cs:235` | le message de log de l'ingestion non rattachée faisait 169 caractères → scindé sur deux lignes (commit `d54fb1b`) |

⚠️ **Récidive de convention** : l'entrée `S103` de `conventions/csharp.md` avait
été créée par task-175 **la veille**, avec le contrôle `awk` à passer avant
commit. Il n'a pas été appliqué ici, d'où un finding évitable. Compteur incrémenté
à **5 occurrences** et consigne renforcée dans le fichier de conventions.

**Correction non re-scannée** : le fix a été poussé **après** l'analyse. Il n'a
pas été re-scanné (une analyse complète coûte ~20 min de build Release + coverage
+ scan). L'inférence est sûre et vérifiable sans Sonar : S103 est une règle
purement mécanique (longueur de ligne > 150), et le contrôle
`awk 'length($0)>150'` sur **tous** les fichiers du diff ne remonte plus aucune
ligne. Le prochain scan doit donc afficher **3** smells.

### Findings restants — dette antérieure, hors module

| Règle | Fichier | Ligne |
|---|---|---|
| `python:S1481` | `tests/loadtest-k6/report.py` | 62 |
| `python:S1481` | `tests/loadtest-k6/report.py` | 64 |
| `python:S3457` | `tests/loadtest-k6/report.py` | 121 |

Identiques à task-175 : fichier **absent du diff**, dernier commit `134647b`
(task-174) **déjà sur `develop`**, remontés comme « new code » du fait de la
baseline large de la new-code period. Non corrigés — autre module (règle 6) et
bruit sur la relecture (règle 5). **Ils rendront le Quality Gate rouge sur
chaque PR api-mail** jusqu'à la task de housekeeping proposée.

### Conventions alimentées

`conventions/csharp.md` — entrée `S103` : **4 → 5 occurrences**, consigne
renforcée (contrôle `awk` avant commit, pas après le finding).

- **Itérations** : 1 / 5 (arrêt : plus aucun finding corrigeable dans le
  périmètre de la task)
- **Next step** : /review task-176

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/128 — label `awaiting-human-merge`
- `dtos-mss` : **aucune PR** — branche créée par `/start` (auto-inclusion), 0 commit (aucun contrat modifié). À supprimer au `/merge`.
- `client-angular` / `client-mobile` / `client-blazor` : non touchés (US backend-only)
- `devops`, `psc-proxy-*` : managed manually by the human

## Staging

- `api-mail` : `forge/staging-task-176-196-20260728` (fraîche depuis `develop`),
  `feat/task-176-...` agrégée par `git merge --no-ff` — sans conflit. Pousse-la
  pour tester le lot du run.

## Code Review Summary

**Verdict : APPROVED** — 4 fichiers relus, 0 blocage.

| Axe | Verdict |
|---|---|
| Correctness | ✓ le bucket `""` disparaît côté requête **et** côté résolution ; INS blanche traitée comme absente ; comportement INS strictement préservé (réutilisation intra-lot incluse) |
| Sécurité / conformité | ✓ règle identito-vigilance respectée (aucun appariement hors INS) ; log = DocumentId + dossier, aucune donnée de santé ; inventaire = ids + compteurs |
| Architecture | ✓ correctif au point de résolution, pas un filtre périphérique ; aligne le chemin nominal sur « promote » déjà conforme |
| Qualité | ✓ méthode renommée pour refléter la nullabilité (`GetOrCreate…` → `Resolve…`) ; pas de code mort |
| Performance | ✓ **gain** : la requête ne charge plus tous les patients à INS nulle de la base — elle est strictement plus étroite qu'avant |
| Tests | ✓ 7 unitaires + 4 intégration ; non-vacuité prouvée (5 échecs sur le code pré-fix, 2 non-régressions restant vertes) |

**Point de vigilance non bloquant** : la déduplication des patients **avec** INS
reste un défaut distinct (lecture-écriture non atomique sans contrainte
d'unicité) — explicitement hors scope de cette task, `g.First()` conservé sur la
clé INS. Task séparée à prévoir.

## Validation finale

- Build : ✓ 0 erreur / 0 avertissement
- Tests : ✓ 3179 ✓ / 16 ignorés — 1 échec **flaky pré-existant documenté** en
  Release (`MailExportServiceTests` / `MarkdownPdfRendererTests`, « font /F5 »),
  vérifié indépendant de cette PR
- Sync `develop` : ✓ `Already up to date` (aucun conflit)
- DOD : ✓ tous les items vérifiables par commande satisfaits ; items
  observationnels reportés au Manual Test Plan de la PR
- Code review : ✓ APPROVED
- Quality Gate : `ERROR` sur `new_violations = 4` → 1 finding task-176 corrigé
  (`d54fb1b`), 3 restants **antérieurs** hors diff (`tests/loadtest-k6/report.py`)
