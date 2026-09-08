# todo-task-183.md — `X-MSS-INS: O` annoncé pour une INS non qualifiée (NIA, OID de test) ; l'OID est perdu à la persistance

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axe métier MSSanté).
> **Sujet d'identito-vigilance — arbitrage humain requis, voir point 4.**

> ### Re-vérification du 2026-08-23 — **toujours pertinente, intégralement**
>
> Chaque preuve rejouée sur `develop` après merge des tasks 226 à 267. Les
> numéros de ligne du bloc « Preuve » ci-dessous datent du 2026-07-25 ; **la
> colonne « au 2026-08-23 » fait foi**.
>
> | Preuve | 2026-07-25 | Au 2026-08-23 | État |
> |---|---|---|---|
> | Qualification par non-vacuité seule | `MssanteHeaderService.cs:185-194` | **`:192-198`** (`hasInsIdentifiers` 192-193, `hasIdentityTraits` 194, `return` 198) | inchangé |
> | OID jamais persisté | « aucune colonne `PatientOid` » | **inchangé** — `PatientOid` n'est écrit qu'en mémoire (`CdaParsingService.cs:219`) et n'existe dans aucune entité | inchangé |
> | Aucune constante d'OID | — | **confirmé** : les quatre OID (`…1.4.8/.9/.10/.11`) n'apparaissent **nulle part** dans le source d'`api-mail` — la valeur n'est donc jamais examinée, ni pour qualifier ni pour rejeter | inchangé |
>
> L'arbitrage humain du point 4 (NIA, OID de test, fusion rétroactive) **reste
> ouvert** et reste le vrai préalable. Le point 1 demeure livrable seul.

## Objective

Rétablir la vérité de l'annonce d'identité INS dans les messages MSSanté émis, et
conserver le **domaine d'identification** (OID) au-delà du parsing.

Deux défauts se composent :

1. **Annonce fausse** — l'en-tête `X-MSS-INS: O`, qui déclare au LPS destinataire
   que le document porte une **INS qualifiée**, est émis dès qu'un identifiant et
   un OID sont *non vides*, sans jamais regarder **quel** OID. Un NIA
   (`1.2.250.1.213.1.4.9`, identité **provisoire**) ou même un OID de **test**
   (`.10` / `.11`) déclenche donc la même annonce qu'un NIR qualifié.
2. **Perte de l'OID** — aucune colonne ne porte l'OID patient (`MailPatient` et
   `MailMedicalDocument` n'ont qu'un `PractitionerOid`). L'identité patient est
   donc clé sur le **matricule nu**, sans son domaine.

**US backend-only (justification)** : conformité d'émission et modèle de données.

### Preuve (état actuel du code)

- `src/Application/Services/Implementation/MssanteHeaderService.cs:185-194`
  (utilisé en `:124-126`) — la « qualification » ne teste que la non-vacuité :
  ```csharp
  var hasInsIdentifiers = !string.IsNullOrWhiteSpace(document.PatientIns)
                       && !string.IsNullOrWhiteSpace(document.PatientOid);
  ```
  La **valeur** de l'OID n'est jamais examinée.
- Côté parsing (`interop-cda`), `INSCode` est renseigné pour les OID NIR **et**
  NIA **et** les OID de test — le dernier identifiant rencontré l'emporte quand le
  document en porte plusieurs.
- Aucune colonne `PatientOid` dans le modèle : l'OID s'arrête au parsing.

Conséquence d'identito-vigilance : deux documents du **même** patient, l'un clé
NIA, l'autre clé NIR, produisent **deux dossiers patients distincts** — l'histoire
du patient est coupée en deux. À l'inverse, un matricule de test identique à un
matricule de production **fusionne deux personnes**.

### Contenu attendu

1. **Qualification par l'OID** : n'annoncer `X-MSS-INS: O` que pour une INS
   réellement **qualifiée** au sens du référentiel — OID NIR
   `1.2.250.1.213.1.4.8`, à l'exclusion du NIA (`.9`, provisoire) et des OID de
   test (`.10`, `.11`). Les traits d'identité restent exigés en complément.
2. **Persistance de l'OID** : porter l'OID patient jusqu'en base et l'inclure dans
   la clé d'identité patient, de sorte qu'un matricule ne soit jamais interprété
   hors de son domaine. Migration FluentMigrator + audit règle 7c.
3. **Refus des OID de test en production** : un document porteur d'un OID de test
   ne doit pas être traité comme une identité réelle. Comportement exact à
   arbitrer (point 4).
4. **Arbitrage humain requis — ouvrir `questions/task-183.md`** :
   - Que doit-il advenir d'un document porteur d'une **INS NIA** (provisoire) :
     rattachement au dossier avec mention du statut, ou reprise manuelle comme
     pour l'absence d'INS (règle task-176) ?
   - Que doit-il advenir d'un document porteur d'un **OID de test** en
     environnement de production : rejet, quarantaine, ou ingestion marquée ?
   - Faut-il **fusionner** rétroactivement les dossiers déjà scindés
     NIA/NIR, et selon quel protocole d'identito-vigilance ?
   Le point 1 (ne plus mentir sur `X-MSS-INS`) est livrable **indépendamment** de
   ces réponses : c'est un correctif de conformité d'émission sans ambiguïté.

### Hors scope

- L'appel au téléservice **INSi** pour qualifier une INS (fonctionnalité absente,
  US produit distincte).
- Le rattachement des documents **sans** INS → task-176.
- La clé de contrôle NIR (Corse `2A`/`2B`, pivot de siècle) → task-193.

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test unitaire paramétré sur l'annonce : OID NIR + traits ⇒ `X-MSS-INS: O` ;
      OID **NIA** ⇒ **pas** `O` ; OID de **test** ⇒ **pas** `O` ; OID inconnu ⇒
      **pas** `O` (ces cas doivent échouer sur le code actuel — le vérifier)
- [ ] Test unitaire : traits d'identité incomplets ⇒ pas d'annonce qualifiée, même
      avec un OID NIR
- [ ] Test unitaire : l'OID patient est persisté et relu (aller-retour complet)
- [ ] Test unitaire : deux documents de même matricule mais d'OID **différents** ne
      sont pas fusionnés dans un même dossier patient
- [ ] Test unitaire : deux documents de même matricule et **même** OID sont bien
      rattachés au même dossier (non-régression)
- [ ] Migration FluentMigrator relue selon la règle 7c ; stratégie de reprise des
      données existantes (OID inconnu rétroactivement) documentée
- [ ] `questions/task-183.md` ouvert avec les 3 arbitrages du point 4
- [ ] Aucune donnée de santé en clair dans les logs (ni matricule INS, ni OID
      associé à un patient identifiable)

## Manual Test Plan

1. Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
2. **Émission — INS qualifiée** : préparer un envoi avec document CDA porteur d'un
   OID **NIR** et des traits complets (données de test anonymisées). Envoyer,
   inspecter les en-têtes du message émis (copie dans Envoyés, ou capture SMTP) →
   `X-MSS-INS: O`.
3. **Émission — NIA** : même envoi avec un OID **NIA** → l'en-tête n'annonce
   **pas** une INS qualifiée. Avant correctif, il annonce `O` à tort.
4. **Émission — OID de test** : même envoi avec un OID de test → pas d'annonce
   qualifiée.
5. **Réception / scission de dossier** : ingérer deux documents du même patient,
   l'un clé NIA, l'autre clé NIR → vérifier le comportement retenu après arbitrage
   (au minimum : les deux ne sont pas silencieusement confondus, et le praticien
   comprend ce qu'il voit).
6. **Non-régression** : un flux nominal NIR de bout en bout (réception,
   rattachement, émission) fonctionne comme avant.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — volets MSSanté et identito-vigilance
- **Exigences DSR honorées** : correctif de conformité sur l'annonce d'identité
  INS dans les échanges MSSanté et sur la gestion du domaine d'identification
- **INS** : **cœur du sujet**. Statut (qualifié / récupéré / provisoire) et OID
  (NIR `1.2.250.1.213.1.4.8`, NIA `1.2.250.1.213.1.4.9`, OID de test) doivent être
  distingués. Aucune annonce de qualification sans OID NIR **et** traits validés
- **Authentification PS** : inchangée (PSC / e-CPS)
- **Habilitations** : inchangées
- **Interop CI-SIS** : CDA r2 en réception ; en émission, en-têtes MSSanté du
  volet transport. Le parsing reste dans `interop-cda`
- **Tracé PGSSI-S** : journaliser le refus d'annonce qualifiée et la détection d'un
  OID de test (évènement technique, **sans** matricule)
- **Consentement patient** : non applicable
- **Référentiels métier** : OID d'autorité d'attribution INS
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : **à mettre à jour** — un LPS destinataire peut avoir
  classé automatiquement un document au titre d'une INS annoncée qualifiée qui ne
  l'était pas. Qualifier avec le humain la portée (volume de messages émis avec
  `X-MSS-INS: O` sur un OID non-NIR) et l'éventuelle information des destinataires.

## Branches

- `api-mail` (pushed) : `fix/task-183-ins-oid-qualification` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-183-ins-oid-qualification
- `dtos-mss` (pushed, auto-inclus) : `fix/task-183-ins-oid-qualification` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/fix/task-183-ins-oid-qualification

> Créées depuis `origin/develop` le 2026-09-08 par `/start`. Pré-flight vert
> (7 repos automatisés sur `develop`).

## Timings

*(généré par `tools/timing/report.sh --task task-183 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 39 s | — | — | — | — |
| /develop | ok | 30 min 01 s | 7 (48 s) | 4 (4 min 35 s) | — | api-mail 7B/4T |
| /sonar | ok | 14 min 30 s | 3 (30 s) | 11 (7 min 40 s) | — | 2 itération(s), api-mail 3B/11T |
| /lint-angular | skipped | 0.5 s | — | — | — | client-angular non liste dans Repos (US backend-only) et arbre Angular inchange |
| /lint-mobile | skipped | 0.5 s | — | — | — | client-mobile non liste dans Repos (US backend-only), repo sur develop et arbre propre |
| /verify-visual | skipped | 0.5 s | — | — | — | aucun ecran client-mobile touche (US backend-only, pas de Stitch design log) |
| /review | ok | 5 min 49 s | 1 (4.9 s) | 1 (1 min 34 s) | — | api-mail 1B/1T |
| /tech-writer | ok | 4 min 10 s | — | — | — | — |
| **Total cycle** | | **55 min 13 s** | **11 (1 min 24 s)** | **16 (13 min 50 s)** | **0 (0.0 s)** | |

## Develop log

**Périmètre livré** : points 1 et 2 du « Contenu attendu ». Le point 3 (refus des
OID de test en production) est **suspendu** à l'arbitrage humain — le comportement
attendu *et* la définition de « production » (flag d'environnement ? Flagsmith ?
par praticien ?) sont des décisions produit. Voir `questions/task-183.md`.

`dtos-mss` : **aucun changement**. `MailMedicalDocumentDto.PatientOid` existait
déjà — l'OID était porté par le contrat, il n'était que perdu à la persistance.
Aucune publication NuGet, aucun bump de consommateur. La branche existe (créée
par `/start`, auto-inclusion) et reste sans commit.

### Point 1 — l'annonce ne mente plus (`X-MSS-INS`)

- `src/Domain/Rules/InsIdentityDomain.cs` (nouveau) : l'unique lecture du
  référentiel — `Classify(oid)` → `InsDomainKind` (Absent / QualifiedNir /
  ProvisionalNia / Test / Unknown), dont dérivent `IsQualifying` et le libellé de
  journal `Describe`. Normalisation de l'OID (`urn:oid:`, espaces) pour que la
  qualification ne dépende pas de la graphie de l'émetteur.
- `MssanteHeaderService.IsQualifiedIns` exige désormais l'OID **NIR**
  (`1.2.250.1.213.1.4.8`), traits d'identité conservés en complément.
- Refus journalisé par **classification** du domaine, jamais par le matricule ni
  l'OID d'un patient identifiable (tracé PGSSI-S), et seulement si le niveau
  Information est actif (`N` est l'issue ordinaire).

**ROUGE constaté sur `develop` avant correctif** (exigence du DOD) : 8 échecs —
les 3 cas NIA/test à l'annonce, les 4 cas de qualification (NIA, 2× test,
inconnu) et le tracé du refus. Seul `urn:oid:` NIR passait déjà, par non-vacuité.

### Point 2 — l'OID entre en base et dans la clé d'identité

- `MailPatients.Oid` et `MailMedicalDocuments.PatientOid` (migration
  `20260908160000_AddPatientInsOid`, colonnes **nullable**).
- Appariement par `(matricule, domaine)` — `MatchPatientOnDomain` — sur les
  **deux** chemins d'ingestion : le chemin nominal et le chemin promote, qui
  réutilise désormais le même résolveur au lieu d'une recherche par matricule nu.
- OID stocké sous forme canonique (normalisé à l'écriture).

**Stratégie de reprise des données existantes.** Les lignes antérieures portent
`Oid = NULL` (« domaine inconnu ») : la valeur n'a jamais été stockée et **ne peut
pas être reconstituée** — écrire l'OID NIR par défaut aurait été une affirmation
fausse sur des données de santé. Un dossier de domaine inconnu **adopte** le
domaine du premier document qui en porte un ; sans cette adoption, la mise en
service aurait ouvert un second dossier pour **chaque** patient déjà connu (une
scission de masse, soit exactement le défaut corrigé). Une fois le domaine adopté,
un document de même matricule et d'**autre domaine connu** obtient son propre
dossier. Un document **sans** OID continue de rejoindre le dossier du matricule
(comportement d'avant la task, délibérément conservé) et n'écrase pas son domaine.

**ROUGE constaté sur `develop` avant correctif** : 8 des 9 tests d'identité ; seul
le cas de non-régression même-domaine passait.

### Audit migration — règle 7c

Les migrations FluentMigrator **ne sont exercées par aucun test** (les tests
d'intégration passent par `EnsureCreated()` sur le modèle EF). L'audit a donc été
fait en jouant réellement la migration sur un PostgreSQL jetable :

- `MigrateUp` : deux opérations, exactement celles voulues — `MailPatients.Oid` et
  `MailMedicalDocuments.PatientOid`. **Aucune opération fantôme.**
- `MigrateDown` : les deux colonnes retirées, rejoué sans dérive.
- Schéma constaté : `character varying(64)`, `is_nullable = YES` des deux côtés,
  cohérent avec `HasMaxLength(64)` du `MailDataContext` et avec la colonne `Ins`.
- Aucune collision : ni `Oid` sur `MailPatients`, ni `PatientOid` sur
  `MailMedicalDocuments` n'existaient (vérifié dans `20240101_SetupMigration`).
- Fichiers compagnons : sans objet (FluentMigrator, pas de snapshot EF, donc
  aucune dérive de snapshot possible).
- Index : aucun ajout. `IX_MailPatients_Ins` (task-070) sert toujours la
  recherche — les candidats sont chargés par matricule, le domaine départage en
  mémoire.

### Passe qualité `/simplify` (§Q)

Appliquée à `api-mail` (`dtos-mss` exclu — porteur de contrat), quatre axes.
Cleanups appliqués, re-validation build + suite complète **verte** (commit
`refactor(mail): simplify pass`) :

- classification du référentiel ramenée dans `InsIdentityDomain` (`Classify` +
  `Describe`) ; le service d'en-têtes re-dérivait la taxonomie en enchaînant
  4 prédicats qui re-normalisaient chacun l'OID ; `IsProvisional`/`IsTest`/
  `IsKnown` supprimés (sans appelant) ;
- **chemin promote** : ma première version ouvrait une requête **par document**
  (le court-circuit par le change tracker était perdu — un mail de 5 documents
  d'une même INS payait 5 `SELECT` au lieu de 1) et recopiait l'initialiseur
  `MailPatient` de 10 champs. Il réutilise maintenant le résolveur nominal avec
  un chargement groupé unique ;
- `MatchPatientOnDomain` : une passe au lieu de deux ;
- journal du refus : charge construite seulement si le niveau est actif ;
- tests : `MedicalDocumentMailBuilder` (le graphe `MailDto` était recopié dans
  3 classes), OID par constantes plutôt que littéraux, deux tests de non-fusion
  fusionnés en une théorie sur les paires de domaines.

Un rouge est apparu pendant la re-validation et a été corrigé : le garde
`IsEnabled` rendait le test de tracé faux (le `ILogger` substitué répond `false`
par défaut) — c'est le test qui déclare le niveau actif, pas la production qui
recule.

**Non appliqué** (le DOD l'exige explicitement) : réduire la théorie
`ApplyHeaders_CdaCarryingANonQualifyingDomain_SetsInsN` à un seul cas. Le DOD
demande un test **paramétré sur l'annonce** couvrant NIA, test et inconnu.

### Écarts relevés hors périmètre — pour arbitrage de `/review`

La passe qualité est *quality-only* ; ces constats sont des **écarts de
comportement** hors du diff, donc consignés sans être corrigés :

1. **`PatientRepository.cs` — `HasQualifiedIns = hasIns`** : le jumeau exact du
   défaut corrigé au point 1 (« la présence prouve la qualification »), sur
   l'écran que le praticien lit. Rien ne projette `Oid`. Corriger changerait
   l'affichage pour les patients NIA — décision produit, pas cleanup.
2. **Détection de doublons — `MailMedicalDocuments.PatientOid` n'a aucun lecteur** :
   `DetectDuplicateAsync` filtre encore `d.Ins == ins`. Deux documents de même
   matricule et de domaines différents peuvent donc encore se déclarer doublons
   ou se superséder — sur un chemin dont l'effet est de **masquer** un document.
   Le correctif propre passe par `d.PatientId` (que cette task vient de rendre
   porteur du couple matricule+domaine).
3. **Modèle de lecture clé sur le matricule nu** : `PatientRepository`
   (`ActiveDocumentsForPatient`, `PatientCacheKey`, `UpdateOppositionAsync` —
   une donnée de **consentement**), `BiologyRepository`, `PatientHandleResolver`,
   et l'entrée publique `POST /patients/resolve` (dont le DTO `InsRequestDto` ne
   porte pas d'OID → changement de contrat `dtos-mss`). Deux dossiers peuvent
   désormais répondre au même matricule ; le chantier propre est de clé ces
   lectures sur `PatientId`. Hors périmètre d'une task de conformité d'émission.

## Sonar log

Deux itérations sur la branche de la task (`api-mail`), analyse complète à
chaque fois (begin → build Release → 5 passes OpenCover → end).

### KPIs qualité — baseline → final

| Métrique | Baseline | Final | Cible |
|---|---|---|---|
| Bugs | 0 | **0** | 0 ✅ |
| Vulnerabilities | 0 | **0** | 0 ✅ |
| Security hotspots | 3 | 3 | revue humaine (hors cible `/sonar`) |
| Code smells | 67 | **59** | — |
| Coverage | 88,0 % | **88,1 %** | 95 % ❌ (dette legacy) |
| Duplication | 0,4 % | 0,4 % | < 3 % ✅ |
| Reliability rating | A | **A** | A ✅ |
| Security rating | A | **A** | A ✅ |
| Maintainability rating | A | **A** | A ✅ |
| **Quality Gate** | OK | **OK** | OK ✅ |

### Phase 1 — new code : verte

**Aucun des 8 findings new-code n'appartenait aux fichiers de task-183.** La
période de new code du projet est `PREVIOUS_VERSION`, donc elle agrège plusieurs
tasks ; ces findings venaient d'autres livraisons. Traités quand même :

- **2 corrigés** (mécaniques) : `CA1822` — `CreateRepository` n'accède à aucun
  état d'instance → `static` ; `CA1859` — `_multiplexer` déclarait l'interface
  alors qu'il ne porte que du `ConnectionMultiplexer` concret. Les deux règles
  ont déjà leur entrée dans `conventions/csharp.md`.
- **6 marqués faux positifs** : `S3604` (« Remove the member initializer, all
  constructors set an initial value ») sur `RevocationDownloadCoordinator`,
  `SentArchiveService` et `MailClientSession` — trois classes à **constructeur
  primaire**. Elles n'ont **aucun autre constructeur** : l'initialiseur est le
  seul assignement, et le retirer laisserait le membre à `null`/`0`, cassant le
  comportement. Limite connue de l'analyseur C# 8.51 sur les constructeurs
  primaires. Marqués `falsepositive` dans SonarQube avec justification, plutôt
  que « corrigés » — un fix aurait été une régression.

**Findings new-code restants : 0.** Quality Gate `OK` sur les 5 conditions.

**Couverture du code de la task** : `InsIdentityDomain.cs` **100 %** ;
`MssanteHeaderService.cs` 90,3 % — les 3 lignes non couvertes sont un `catch`
**préexistant** sur la suppression du fichier temporaire, pas du code de la
task ; `MailRepository.cs` — **aucune ligne non couverte** dans la plage du
résolveur et de l'appariement par domaine (lignes 355-470).

### Phase 2 — dette legacy : skippée, délibérément

Bugs, vulnérabilités et les trois ratings sont déjà à leur cible ; le seul écart
restant est la couverture globale (88,1 % vs 95 %), qui est de la dette
antérieure sur des fichiers étrangers à cette US. La combler ici gonflerait une
PR de conformité MSSanté bien au-delà de la règle 5 (~30 fichiers) et mêlerait
du travail sans rapport à une PR relue au HAG. Phase 2 est best-effort et ne
bloque jamais le cycle (`agents/sonar.md`).

## PRs

- **`api-mail`** : [#222 — fix(mssante): X-MSS-INS n'annonce plus une INS non qualifiée, et l'OID entre dans la clé d'identité patient](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/222) — label `awaiting-human-merge`
- **`dtos-mss`** : **aucune PR**. `MailMedicalDocumentDto.PatientOid` existait déjà — l'OID était porté par le contrat, seulement perdu à la persistance. La branche `fix/task-183-ins-oid-qualification` a été créée par `/start` (auto-inclusion) et reste sans commit.

### Pourquoi `awaiting-human-merge` et non `awaiting-us-completion` (règle 11)

Le point 3 de la US n'est pas livré, mais ce n'est **pas** une « wave 1 de
plomberie » en attente d'enrichissement. Les points 1 et 2 délivrent chacun une
valeur complète et autonome — l'annonce cesse de mentir, le domaine est persisté
et entre dans la clé d'identité — et le task file déclare explicitement le
point 1 « livrable **indépendamment** » de l'arbitrage. Le point 3 est
**inspécifiable** sans les réponses humaines (comportement *et* définition de
« production »). Rien de « faussement v1 » n'atterrirait sur `develop`. Le
périmètre non livré est affiché en tête du body de la PR pour que le merge se
fasse en connaissance de cause.

## Code Review Summary

**APPROVED** — 10 fichiers relus, **0 point bloquant**, 3 suggestions
(toutes hors périmètre, détaillées dans le body de la PR) :

1. `AddPatientMessageDocumentAsync` duplique le mécanisme de résolution au lieu
   d'appeler le résolveur partagé (comportement identique — ce chemin ne reçoit
   aucun OID).
2. `MailMedicalDocuments.PatientOid` n'a **aucun lecteur** : la détection de
   doublons filtre encore `d.Ins == ins`, sur un chemin qui **masque** un
   document. Correctif propre : `d.PatientId`.
3. Le modèle de **lecture** reste clé sur le matricule nu, et
   `PatientRepository.HasQualifiedIns` est calculé par non-vacuité de l'INS —
   le jumeau du défaut corrigé ici, côté écran.

Build vert (0 erreur, 0 avertissement), **4247 tests passés / 0 échec** /
16 skipped préexistants, DOD intégralement vérifié (dont le ROUGE constaté
avant correctif, et l'audit de migration règle 7c joué sur une vraie base).

## Merged

Mergée le **2026-09-08** par l'humain (HAG, règle 10), après test manuel
attesté par `--i-tested`.

| Repo | PR | Merge | Squash SHA |
|---|---|---|---|
| `api-mail` | [#222](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/222) | squash sur `develop` | `da2f2b6` |
| `dtos-mss` | — (aucune PR) | — | — |

**Garde-fous passés avant merge** : `--i-tested` présent ; label
`awaiting-human-merge` (pas `awaiting-us-completion`) ; aucune revue en
`CHANGES_REQUESTED` ; CI de la PR verte (`build` pass, `publish` skipping) ;
`mergeable = MERGEABLE`, `mergeStateStatus = CLEAN` ; arbres de travail propres
sur les deux repos.

**Après merge** : CI de `develop` **verte** sur le commit de squash (vérifiée
dans les 2 min, règle 5). Refs distantes `fix/task-183-ins-oid-qualification`
supprimées sur `api-mail` **et** sur `dtos-mss` (cette dernière n'avait aucun
commit — branche créée par auto-inclusion, jamais utilisée). **Branches locales
conservées** sur les deux repos, pour inspection rétroactive. Aucune branche
staging à nettoyer (task lancée par `/start` direct, hors run `/forge`).

**Ce qui reste ouvert après ce merge** : les trois arbitrages
d'identito-vigilance de `questions/task-183.md` — statut du NIA, OID de test en
production (point 3 de la US, **non livré**), et fusion rétroactive des dossiers
déjà scindés. Le merge de cette PR ne les tranche pas et n'en dépendait pas.

