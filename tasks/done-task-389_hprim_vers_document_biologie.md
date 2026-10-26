# todo-task-389.md — Un résultat de laboratoire reçu au format HPRIM devient un document de biologie

**Repos**: api-mail
**Dependencies**: task-397 (lecture directe des messages d'une BAL déléguée sans stockage, banc de délégation)
**Epic**: E009
**Single frontend**: true
**Priorité**: **2** — les labos qui n'envoient pas encore de CR-BIO en CDA (ou un CDA invalide) arrivent aujourd'hui dans la nouvelle messagerie comme un mail portant un fichier technique illisible : le résultat n'existe ni dans la biologie du patient ni dans les alertes.

> **Origine.** Demande de l'humain du 2026-10-23 : le parsing HPRIM existe dans Weda (WMickey) mais pas dans api-mail. Arbitrages rendus le même jour en séance `/po` (voir « Décisions actées »).
>
> **Suite de l'EPIC** : task-390 (résultats structurés `RES|`), task-391 (file « à intégrer » + suggestion de patient), task-392 (affichage + acquittement + E2E-BIO-003).

## Ce qui est établi

- **api-mail ne lit que l'archive IHE-XDM.** `EnrichmentFetchPlan.IheXdmFileName = "ihe_xdm.zip"` est « la seule pièce jointe utile à l'analyse » ; `IheXdmProcessingService.ExtractIheXdmZipsAsync` (les deux surcharges : IMAP et message en main) ne retient que ce nom. Un `.hpm` n'est ni récupéré ni lu.
- **Modèle d'accueil existant.** `MailMedicalDocument` (patient, traits, `Format`, `Category`, `Body`/`HtmlBody`, PDF associé `HasExternalPdf`/`PdfAttachmentGuid`, doublon `DuplicateOfId` task-013) et `MailMedicalDocumentBiology` (valeur, unité, normes, interprétation, `IsFlagged`).
- **Règle task-176** (`MailRepository.cs`) : un document **sans INS** n'est jamais rattaché automatiquement à un patient ; il va dans la file « à intégrer » (`PatientId == null`). Le HPRIM ne porte pas d'INS.
- **Règle task-193** (`MailRepository.DetectDuplicateAsync`) : **aucune détection de doublon ni de remplacement de version pour un document sans INS** — les requêtes du dossier patient écartent doublons et versions remplacées, et « un document masqué est un risque clinique ». Un HPRIM n'ayant jamais d'INS, il n'est rapproché de rien à la réception (décision 6).
- **Circuit d'écriture existant** : `EmailBuildingService.BuildMailDtoAsync` réunit les `MailMedicalDocumentDto` produits par l'analyse (aujourd'hui `IheXdmProcessingService.ProcessIheXdmZips` → `CdaParsingService`), puis `MailRepository` les persiste (`CreateMedicalDocumentEntity`, `DetectDuplicateAsync`, `AddBiologyResultsToDocument`). Le document HPRIM emprunte **ce même circuit** : pas de nouvelle table, pas de nouveau chemin d'écriture.
- **Référence fonctionnelle Weda** (dépôt `D:\Workspaces\WD`, lecture seule — on copie les règles, on ne dépend pas du code) :
  - `WedaGlobal/Services/Hprim/HprimService.Main.cs` › `PrepareText` : au moins 13 lignes ; en-tête de 12 lignes à positions fixes (`HprimFields` : labo, nom, prénom, adresse 1, adresse 2, ville, date de naissance, NIS, n° de dossier, date du résultat, expéditeur, destinataire) ; corps jusqu'à `****FIN****` ; plusieurs résultats (100 au plus) jusqu'à `****FINFICHIER****` ; rejet d'un contenu commençant par `<!doctype`/`<html` ; données parasites entre `****FIN****` et `****FINFICHIER****` → résultats déjà lus conservés (`HprimInvalidTrailingResultException`).
  - `HprimService.Static.cs` › `IsHprim` (une ligne contient `***FIN***` ou `****FINFICHIER****`), `GetLines` (découpe `\n`, sinon `\r`), `GetEncoding` (BOM UTF-16 BE/LE, UTF-8 ; sinon comptage des `é` puis `è` en 1252 / Mac 10000 / 850 ; défaut ASCII).
  - `WMickey/WMickey.Infrastructure/Mail/MailKitExtensions.cs` › `GetAllAttachments` : le `.hpm` arrive souvent **intégré au corps, sans `Content-Disposition: attachment`** — il faut le récupérer par son nom.
  - Weda PR 9267 (#19121, branches lotus, pas encore dans `next`) : détection sur l'extension `.hpm` seule ; le texte HPRIM ne doit jamais servir de corps du mail.
  - Jeux de cas réels à anonymiser : `Tests/WedaTests/Hprim/` (`GetLinesTests`, `GetEncodingTests`, `PrepareTextTests`, `HprimCommon`), `Tests/Mickey.Application.Tests/Parser/IheXdmParser.cs/HprimParserTests.cs`.

## Décisions actées (humain, 2026-10-23)

1. **Finalité : vue de la nouvelle messagerie uniquement.** L'injection HPRIM dans le dossier Weda reste à WMickey ; E019 inchangé (l'import à la demande continue d'exclure les messages HPRIM).
2. **Identité : file « à intégrer » + suggestion.** Jamais de rattachement automatique (task-176) ; la suggestion de patient par traits est livrée par task-391. Cette US conserve les traits de l'en-tête.
3. **Profondeur : texte + lignes `RES|`.** Cette US crée le document (texte) ; les résultats structurés sont livrés par task-390.
4. **CDA prioritaire, HPRIM en secours.** Le HPRIM n'est lu que si le mail ne porte pas de CR de biologie CDA valide.
5. **Reconnaissance : pièce `.hpm` + marqueurs de fin.** Ni l'objet (`HNET.1/MSG/`) ni le type MIME ne sont regardés.
6. **Doublons : rien n'est rapproché ni masqué à la réception** (règle task-193, arbitrage du 2026-10-23). Le rapprochement — signal doublon existant (task-013) pour un même fichier, remplacement d'un partiel par le complété — se fait **au rattachement**, contre les HPRIM du dossier choisi par le médecin : livré par task-391.
7. **Historique : nouveaux messages seulement.** Pas de rattrapage des messages déjà synchronisés.
8. **BAL déléguée : affichage seul, aucune injection en base** (humain, 2026-10-25, délégation de
   BAL Mailiz — voir task-397 et `Docs/audits/delegation-bal-mailiz-analyse-20261025.md`). Un HPRIM
   porté par un message d'une BAL déléguée (dossier sous `shared/…`) est **lu pour être affiché**,
   à l'ouverture du message, sans rien conserver. Le répertoire de travail transitoire du décodage
   est accepté (task-397, décision 4).
   - **Rien n'est stocké** chez le délégataire, ni en base ni dans Redis : aucun document, aucun
     trait patient, aucune entrée dans la file « à intégrer ».
   - Hors ligne, il n'est pas consultable.
   - Même règle que pour le CDA délégué (task-397).

## Objective

Quand un mail porte un fichier HPRIM, api-mail en tire un **document médical de biologie** par résultat, en attente de rattachement, au lieu d'un mail avec un fichier technique illisible.

**US backend-only (justification)** : la création du document et sa présence dans la file « à intégrer » sont lues par le test d'intégration ; ce que le médecin voit (suggestion, affichage, acquittement) est livré par task-391 et task-392, qui portent le scénario e2e.

### Règles métier

- **Reconnaissance** : une pièce dont le nom finit par `.hpm` (casse ignorée), **y compris intégrée au corps sans en-tête de pièce jointe**, dont le contenu porte les marqueurs de fin. Un `.hpm` sans marqueurs reste une simple pièce jointe, sans document.
- **Lecture** : règles de Weda ci-dessus (en-tête 12 lignes, plusieurs résultats, encodage détecté, données parasites tolérées, HTML rejeté, fichier trop court rejeté). **Un document par résultat.**
- **Document créé** : catégorie biologie, format HPRIM, date = date du résultat, émetteur = labo/expéditeur, traits patient de l'en-tête (nom, prénom, date de naissance), **sans INS**, **non rattaché**.
- **PDF** : un PDF joint au même mail est associé au document (comme le PDF externe d'un CDA). Plusieurs résultats et un seul PDF : le PDF est associé à chacun.
- **CDA prioritaire** : un mail portant un CR de biologie CDA valide ne produit aucun document HPRIM ; si le CDA est absent ou illisible, le HPRIM est lu.
- **Doublon** : à la réception, **aucun** rapprochement — un HPRIM reçu deux fois donne deux documents à intégrer, aucun n'est masqué (task-193). Le rapprochement se fait au rattachement (task-391).
- **Circuit** : le document HPRIM est produit sous la même forme que le document issu d'un CDA et persisté par le même circuit (voir « Ce qui est établi »).
- **Corps du mail** : le texte HPRIM n'est jamais retenu comme corps.
- **Échec de lecture** : le mail reste un mail normal avec sa pièce jointe ; aucun document partiel, sauf le cas des données parasites (résultats déjà lus conservés).
- **Seuls les messages synchronisés après la mise en service** sont traités.
- **BAL déléguée** (décision 8) : pour un message sous `shared/…`, le HPRIM est lu à l'affichage du
  détail, et ses documents sont renvoyés dans la réponse (texte, PDF associé, traits de l'en-tête
  affichés). **Aucun** n'est persisté ni ajouté à la file « à intégrer ».
  - Le lecteur HPRIM est branché sur le **chemin de lecture directe** des messages délégués
    livré par task-397, pas seulement sur le circuit d'écriture.
  - Le test de convention de task-397 (« aucune écriture issue d'une pièce médicale pour un message
    délégué ») couvre le HPRIM.

## Gherkin

Voir `tests/Features/Mss/HprimReception.feature`.

## Definition of Done

- [ ] Build et tests verts : api-mail
- [ ] ≥ 1 test unitaire par règle de lecture : marqueurs présents/absents, fichier trop court, plusieurs résultats, encodages (UTF-8 BOM, UTF-16 BE/LE, 1252, 850, Mac 10000), données parasites après `****FIN****`, contenu HTML, découpe `\r` seule
- [ ] ≥ 1 test unitaire de reconnaissance : `.hpm` en pièce jointe, `.hpm` intégré au corps sans `Content-Disposition`, `.txt` en `text/plain` non retenu, extension en majuscules
- [ ] Jeu d'exemples HPRIM **anonymisés** (aucun trait réel) dérivé des cas de Weda, versionné avec les tests
- [ ] Test d'intégration de bout en bout (règle 1b) : un mail portant un `.hpm` + PDF, synchronisé, donne un document de biologie au format HPRIM, non rattaché, avec PDF associé, **lu dans la réponse réelle** de la liste des documents à intégrer (cas nominal) ; un `.hpm` sans marqueurs ne donne aucun document (cas d'échec) ; vu rouge
- [ ] Test d'intégration : un mail CDA de biologie valide + HPRIM donne **un seul** document, celui du CDA ; un CDA illisible + HPRIM donne le document HPRIM
- [ ] Test d'intégration : le même HPRIM reçu deux fois → deux documents à intégrer, aucun signalé doublon ni masqué (task-193)
- [ ] Le document HPRIM est persisté par le circuit existant (`MailRepository`), sans nouvelle table ni écriture parallèle
- [ ] Test : le corps d'un mail ne portant qu'un HPRIM n'est pas le texte HPRIM
- [ ] La récupération du message va chercher le `.hpm` en plus de `ihe_xdm.zip` ; aucune régression mesurée sur le banc de charge (E015) pour les mails sans HPRIM
- [ ] Métrique : HPRIM lus, rejetés (par cause), signalés doublons
- [ ] Aucune donnée de santé en clair dans les logs : ni nom, ni prénom, ni date de naissance, ni NIS, ni n° de dossier, ni contenu HPRIM
- [ ] Mails déjà synchronisés avant la mise en service non retraités
- [ ] **BAL déléguée — test d'intégration de bout en bout** (banc de délégation de task-397) : un
      mail portant un `.hpm` + PDF dans `shared/<A>`, ouvert par le délégataire B.
      - Le détail renvoie le document HPRIM décodé, lu dans la réponse réelle.
      - La base de B contient **zéro** ligne `MailMedicalDocuments` pour ce message.
      - Le document est absent de la liste « à intégrer » de B.
      - Aucune clé Redis de B ne contient le texte HPRIM.
      - Vu rouge (règle 1b).
- [ ] Le test de convention de task-397 inclut le chemin HPRIM, prouvé rouge par mutation

## Manual Test Plan

1. Banc de charge / boîte de test : envoyer un mail avec un `.hpm` intégré au corps et un PDF → un document de biologie apparaît dans la file « à intégrer », avec son PDF ; le corps du mail n'affiche pas le texte HPRIM.
2. Renvoyer le même mail → deux documents à intégrer, aucun bandeau doublon (le rapprochement se fait au rattachement, task-391).
3. Envoyer un HPRIM contenant deux résultats → deux documents.
4. Envoyer un mail CDA de biologie valide + HPRIM → un seul document, issu du CDA.
5. Envoyer un `.hpm` sans marqueurs de fin → mail normal, pièce jointe intacte, aucun document.
6. Vérifier dans Seq qu'aucun trait patient ni contenu HPRIM n'apparaît.
7. **BAL déléguée.** Envoyer un HPRIM à Virginie, puis se connecter en Cyril, son délégataire, et
   ouvrir le message dans la boîte déléguée.
   - Le résultat est **lisible**.
   - Aucun document n'apparaît dans la file « à intégrer » de Cyril, et sa base ne contient aucun
     document pour ce message.
   - Hors ligne, le message s'affiche avec sa pièce jointe seule.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : biologie médicale (réception en médecine de ville)
- **Vague Ségur** : hors Ségur — le HPRIM est un format historique hors CI-SIS ; le CR-BIO CDA exigé par le Ségur reste prioritaire (décision 4)
- **Exigences DSR honorées** : identito-vigilance — aucun rattachement d'un document sans INS ; le document structuré CI-SIS prime sur le format historique
- **INS** : non disponible dans le format ; traits de l'en-tête conservés pour une suggestion (task-391), jamais pour un rattachement automatique (task-176)
- **Authentification PS** : inchangée — traitement serveur à la synchronisation de la boîte
- **Habilitations** : documents de la boîte du médecin. Pour une BAL déléguée, lecture seule
  sans stockage chez le délégataire (décision 8, task-397).
- **Interop CI-SIS** : non applicable — HPRIM Santé (format historique propriétaire, texte libre + lignes `RES|`)
- **Tracé PGSSI-S** : aucun nouvel évènement d'imputabilité (création automatique à la réception, comme un CDA) ; journal technique sans donnée identifiante
- **Consentement patient** : non applicable — aucun envoi vers le DMP ni Mon Espace Santé
- **Référentiels métier** : aucun dans cette US (codes labo locaux traités en task-390)
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangé — même traitement (réception de résultats de biologie), nouveau format d'entrée

## Branches
- `api-mail` (pushed) : feat/task-389-hprim-vers-document-biologie — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-389-hprim-vers-document-biologie
- `dtos-mss` (lazy) : aucune branche au /start — créée par /develop depuis `origin/develop` au premier contrat touché (CLAUDE.md, « Repo à branche PARESSEUSE »)
- Run `/forge` `forge-20261026-389-390` (staging `forge/staging-task-389-390-20261026`)

## Timings

*(généré par `tools/timing/report.sh --task task-389 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 19 s | — | — | — | — |
| /develop | ok | 10 min 21 s | 7 (51 s) | 35 (21 min 21 s) | — | api-mail 7B/35T, reprise revue : DocumentId HPRIM + test vu rouge |
| /sonar | ok | 8 min 32 s | 4 (1 min 25 s) | 16 (20 min 07 s) | 6 (2 min 07 s) | 1 itération(s), api-mail 4B/16T, re-scan 6998e4fa : QG OK, 0 issue |
| /lint-angular | skipped | 0.5 s | — | — | — | client-angular non touché |
| /lint-mobile | skipped | 0.5 s | — | — | — | client-mobile non touché |
| /e2e | ok | 16 min 22 s | — | — | — | e2e ×8 (48 min 56 s), rejeu après reprise de revue : 2 voies vertes, porte 0 |
| /review | ok | 46 min 06 s | 1 (10 s) | 1 (4 min 18 s) | — | api-mail 1B/1T, APPROVED 2e passe, PR #315 |
| /tech-writer | ok | 1 min 20 s | — | — | — | — |
| **Total cycle** | | **1 h 23 min** | **12 (2 min 27 s)** | **52 (45 min 47 s)** | **6 (2 min 07 s)** | |

## Develop log

> Journal de progression (point de reprise en cas de compaction).

- **Repos touched** : `api-mail` seul (US backend, justifiée dans la task). **Aucun contrat** `dtos-mss` changé : le document HPRIM emprunte `MailMedicalDocumentDto` tel quel (`Format = "HPRIM"`, `Loinc = 11502-2` → catégorie biologie). Pas de branche `dtos-mss` (création paresseuse non déclenchée).
- **Gherkin** : la task cite `tests/Features/Mss/HprimReception.feature`. Le BDD est retiré du workspace (CLAUDE.md, règle 1) : les scénarios sont couverts par des tests unitaires et d'intégration, aucun `.feature` n'est créé.

**Conception** (moindre churn, aucun nouveau chemin d'écriture) :
- `src/Application/Hprim/HprimReader.cs` : lecture pure, sur les règles de Weda (`HprimService` : `PrepareText`, `GetLines`, `GetEncoding`, `IsHprim`). L'en-tête fait 12 lignes ; il y a 13 lignes au minimum et 100 résultats au plus. La découpe se fait sur `\n`, sinon sur `\r`. L'encodage est détecté par le BOM UTF-16 ou UTF-8, puis par un UTF-8 strict, puis par le comptage des `é` et des `è` en 1252, Mac 10000 ou 850 ; ASCII est le défaut. Les données parasites après le dernier `****FIN****` sont tolérées et les résultats déjà lus gardés. Le HTML est rejeté. Les pages de codes passent par `CodePagesEncodingProvider.Instance`, sans enregistrement global.
- `src/Application/Hprim/HprimMedicalDocuments.cs` : un `MailMedicalDocumentDto` par résultat.
  - Format HPRIM, catégorie biologie, date = date du résultat.
  - Émetteur = laboratoire (organisation) et expéditeur (nom).
  - Traits de l'en-tête : nom, prénom, naissance. **Sans INS ni identifiant**, donc ni rattachement (task-176) ni rapprochement (task-193).
  - Le premier PDF du message est associé à chaque document, comme le PDF externe d'un CDA.
  - CDA prioritaire : `IsCdaBiologyReport`.
- `src/Application/Helpers/MedicalSourceParts.cs` : reconnaissance par l'extension `.hpm` seule, **aussi parmi les parties intégrées au corps** (`BodyParts`, pas seulement `Attachments`).
  - `TextBodyOf` : le corps texte n'est jamais un HPRIM.
  - `VisibleAttachments` : un `.hpm` intégré reste listé en pièce jointe. Le téléchargement le retrouve déjà par `BodyParts`.
- **Circuit** :
  - le `.hpm`, puis les PDF du message (seulement s'il y a un HPRIM), rejoignent l'archive dans le lot transitoire `IheXdmScratchSet`, avec leur extension (`CreateFile(extension)`). La règle 14 accepte explicitement ce répertoire de travail ;
  - `IheXdmProcessingService.ProcessIheXdmZips` répartit par extension. Les signatures existantes de `BuildMailDtoAsync` et `ProcessIheXdmZips` sont inchangées, et 90 tests y font référence ;
  - la persistance reste `MailRepository` : aucune table, aucune écriture parallèle.
- **Récupération** :
  - `ExtractArchivesIfAnyAsync` (`HasAnalysableParts`, comptage des allers-retours) ;
  - les deux voies : message entier et par partie ;
  - `ReadEmailWithoutPersistingAsync`, le contenu à la demande ;
  - `BackgroundImapService` ;
  - `EnrichmentFetchPlan.UsefulParts` (`.hpm`, et PDF si HPRIM) ;
  - lecture directe d'une BAL déléguée (`ImapService.Delegation` : corps, `HasMedicalDocuments` de l'en-tête).
- `EmailBuildingService` : le texte d'un document HPRIM n'est jamais ajouté au corps.
- **Métrique** : `mssante_hprim_files_total{outcome}`. Valeurs : `read`, `cda_priority`, `trailing_data_ignored`, `too_short`, `not_hprim`, `html`, `unreadable`.
  - « Signalés doublons » : toujours 0 à la réception, par règle (task-193). Le rapprochement se fait au rattachement (task-391), qui portera son compteur.
- **Historique** (décision 7) : seuls les messages analysés après la mise en service sont traités. Le marqueur d'analyse (ligne de contenu, task-333) écarte déjà de l'enrichissement un message analysé avant : pas de rattrapage, par construction.

**Tests et preuves**
- Unitaires (`tests/mss.mail.application.tests/Hprim/`, 55 tests) :
  - lecteur : marqueurs, trop court, plusieurs résultats, 6 encodages, données parasites, HTML, découpe `\r`, borne de 100, dates ;
  - reconnaissance : pièce jointe, intégré au corps, `.txt` refusé, casse ;
  - documents et PDF, priorité CDA, CDA illisible ;
  - corps jamais HPRIM ;
  - aucune donnée de santé dans les journaux (journal capturé).
- Jeu d'exemples **synthétique et anonymisé** : `tests/mss.mail.testing.shared/HprimSamples.cs`, structure des cas Weda, aucun trait réel.
- **Intégration bout en bout (règle 1b)** — `HprimReceptionEndToEndTests` : Dovecot, API, `enrich/sync`, réponse réelle de `emails/content/{uid}` et `emails/{uid}`, puis relecture en base. Sept tests :
  - `.hpm` intégré + PDF → document HPRIM, catégorie biologie, non rattaché, PDF relu par son identifiant, corps intact, `PendingIntegrationsCount = 1` ;
  - `.hpm` sans marqueurs → aucun document, pièce jointe listée ;
  - CDA de biologie valide + HPRIM → le seul document CDA ;
  - CDA illisible + HPRIM → le document HPRIM ;
  - même HPRIM reçu deux fois → deux documents à intégrer, aucun doublon ;
  - deux résultats → deux documents ;
  - voie de récupération par partie (grosse pièce sans rapport) → `.hpm` et PDF récupérés.
- **BAL déléguée** — `DelegationEndToEndTests.ADelegatedHprim_IsDecodedForDisplay_AndNothingOfItLandsInTheDelegateBaseNorRedis` :
  - le document HPRIM est décodé dans la réponse réelle ;
  - la base du délégataire compte 0 `Mails` sous `shared/`, 0 `MailMedicalDocuments`, 0 `MailPatients`, et aucune ligne portant le nom ;
  - hors du cache J (exception de la règle 14, TTL de 5 min au plus), aucune clé ni valeur Redis ne porte les traits.
- **Convention règle 14** — `DelegatedPersistenceGuardScanTests.TheHprimPathWritesNothing` : le dossier `src/Application/Hprim/` ne référence aucun écrivain (dépôt, contexte EF, cache, Redis, bus, fichier, audit).
- **Mutations** (le défaut est réinjecté, l'assertion visée passe au rouge, puis le fichier est restauré par copie) :

  | # | Mutation | Test rouge | Assertion |
  |---|---|---|---|
  | M1 | l'analyse ignore les fichiers HPRIM | 4 tests de réception | `Single` vide, `Collections differ` |
  | M2 | la récupération ne va chercher que l'archive | voie par partie + BAL déléguée | `Single` vide |
  | M3 | le CDA de biologie ne prime plus | CDA valide + HPRIM | 2 documents au lieu d'1 |
  | M4 | le texte HPRIM rejoint le corps | nominal | corps « …résultat.*** NUMERATION… » |
  | M5 | les PDF ne sont plus récupérés avec le HPRIM (voie par partie) | voie par partie | `HasExternalPdf` faux |
  | MC | un écrivain (`IAuditService`) dans `src/Application/Hprim/` | `TheHprimPathWritesNothing` | rouge |
  - M2 et M5 ont d'abord **survécu** : les tests ne prenaient que la voie « message entier », un petit message étant récupéré en une commande. Le test de la voie par partie a été ajouté pour les tuer.
- **Suites** : application 3 736 et API 1 347 verts ; intégration HPRIM 7 et délégation HPRIM 1 verts. La suite d'intégration complète sera rejouée avant le push.
- Commit feature : `93cfa221`.

### Passe qualité §Q (`/simplify`, 4 relectures : réutilisation, simplification, efficacité, altitude)

- **Appliqué** (`c2a12219`) :
  - **une règle unique** de récupération du HPRIM, `MedicalSourceParts.HprimSourceParts` : les fichiers `.hpm`, puis le premier PDF, ou rien. Elle était écrite quatre fois (extraction IMAP, extraction du message en main, plan de récupération, compte des allers-retours) : les quatre restent désormais d'accord par construction ;
  - seul le **premier PDF**, le seul associé, est récupéré. C'est un aller-retour IMAP de moins par PDF supplémentaire ;
  - `IsIheXdm` remplace trois prédicats écrits en ligne ; extensions et type PDF ne sont définis qu'une fois ;
  - `ExternalPdf.Attach` est partagé par le PDF associé d'un CDA (`CdaParsingService`) et celui d'un HPRIM ;
  - **aucune allocation** dans `MedicalSourceParts` pour un message sans HPRIM ;
  - UTF-8 vérifié par `Utf8.IsValid` (sans exception) ; `Array.IndexOf` remplace une boucle ;
  - `HprimResult.FileNumber` retiré : rien ne le lisait. task-391 le reprendra si la suggestion en a besoin ;
  - `RecordHprimFile(outcome, count)` ; `FromFiles(files, byte[]? pdf)` au lieu d'une liste dont seul le premier élément servait ;
  - contrat d'`IIheXdmProcessingService` documenté : archives, HPRIM, PDF ;
  - tests d'intégration : les constructeurs de messages HPRIM sont partagés (`Fixtures/HprimMessages`).
- **Re-validation** : build vert ; application 3 736, API 1 347, intégration ciblée 39 (HPRIM, délégation, marqueur d'analyse, pipeline documents), tous verts.
- **Écartés** :
  - **stocker le PDF une seule fois** pour les N résultats : le nom du PDF porte les traits du patient (`PdfFileNameGenerator`), et un PDF partagé nommerait le premier patient sur le document des autres. La spécification associe le PDF à chaque résultat : une copie par document est conservée ;
  - **renommer `IheXdm*` / `zips`** : environ 220 occurrences, dont 60 fichiers de tests. Hors périmètre d'une PR (≈ 30 fichiers) ; à prévoir dans une task dédiée si le contrat s'élargit encore ;
  - **factoriser le triplet « texte, HTML, archives »** des quatre lectures de corps (`ImapService`, délégation, arrière-plan) : dette antérieure à la task, refactor séparé ;
  - **fusionner `FetchPartIntoAsync` / `CopyPartIntoAsync`** : gain modeste, la seconde est déjà réduite à un essai ;
  - **compromis accepté** : le HPRIM d'un message qui porte aussi un CDA de biologie est récupéré avant de savoir que le CDA prime. Décider demande d'analyser le CDA ; le coût est borné à un fichier et un PDF.

- **Suite complète avant le push** : 7 061 tests verts. Domaine 264, infrastructure 701, API 1 347, application 3 736, intégration 1 013 (+ 16 sautés).
- **Poussé** : `api-mail` `feat/task-389-hprim-vers-document-biologie` (`93cfa221`, `c2a12219`).
- **DoD — auto-contrôle**
  - Couverts par des tests :
    - build et tests ;
    - règles de lecture et encodages ;
    - reconnaissance ;
    - jeu d'exemples anonymisé ;
    - intégration nominale et cas d'échec, vue rouge (M1) ;
    - CDA prioritaire et CDA illisible (M3) ;
    - doublon reçu deux fois ;
    - circuit de persistance existant ;
    - corps jamais HPRIM (M4) ;
    - `.hpm` récupéré sur les deux voies (M2, M5) ;
    - métrique ;
    - aucune donnée de santé journalisée ;
    - BAL déléguée de bout en bout (M2) ;
    - convention de la règle 14 (MC).
  - Par construction : mails déjà synchronisés non retraités (marqueur d'analyse, task-333).
  - Différé au banc E015 / HAG : « aucune régression mesurée sur le banc de charge pour les mails sans HPRIM ». Pour un tel mail, le plan de récupération rend les mêmes parties qu'avant, aucun aller-retour ni écriture n'est ajouté, et `MedicalSourceParts` n'alloue rien. Un tir de comparaison reste à faire par l'humain s'il le souhaite.
- **Étape suivante** : `/sonar task-389`.

### Reprise après la 1ʳᵉ revue de `/review` (CHANGES REQUESTED)

La revue indépendante a trouvé un défaut **bloquant** qu'aucun outil n'avait vu.

- **Le défaut** : le document HPRIM n'avait pas de `DocumentId`. Or `MailRepository` range les pièces d'un document par cet identifiant. Avec deux résultats et un PDF dans le même message :
  - les copies du PDF devenaient des pièces jointes **du message** ;
  - dans la liste, chaque document montrait aussi le PDF nommé au patient de l'**autre** ;
  - dans le contenu, aucun document ne montrait de pièce alors que `HasExternalPdf` était vrai.
- **Pourquoi les tests ne le voyaient pas** :
  - le test à deux résultats n'avait pas de PDF ;
  - le test nominal relisait le PDF en base par son GUID ;
  - un test unitaire affirmait même `Assert.Null(document.DocumentId)`, ce qui figeait le défaut.
- **Correction** : `DocumentId = "HPRIM-" + Guid` (`HprimMedicalDocuments.DocumentIdPrefix`), unique par document. Sans INS, aucun rapprochement n'est déclenché : task-193 sort avant la comparaison.
- **Test d'intégration ajouté** : `AnHprimWithTwoResults_AndAPdf_EachDocumentShowsOnlyItsOwnPdf_AndTheMailKeepsItsOwnAttachments`. Il lit dans les réponses réelles :
  - les pièces de chaque document : une seule, son propre PDF, nommé à son patient ;
  - les pièces du message : exactement `resultat.hpm` et `compte-rendu.pdf`.
  - **Vu rouge sur le code d'avant la correction** : `Assert.Single() Failure: The collection was empty`.
- **Unitaires** :
  - `FromFiles_EveryDocument_HasItsOwnDocumentId` ;
  - l'assertion `Assert.Null(DocumentId)` est remplacée.
- **Suggestions de la revue, traitées** :
  - **date de naissance sur deux chiffres** : `HprimReader.ParseBirthDate` ramène une année future au siècle précédent (« 12/03/45 » donne 1945). Trois cas unitaires ;
  - **métrique** : la description dit qu'elle compte des **lectures** (lecture déléguée hors cache, lecture sans persistance, rejeu), pas des fichiers distincts ;
  - **voie par partie** : le test affirme aussi que le corps n'est pas le texte HPRIM. La mutation MB (`TextBodyOf(summary)` rend toujours `TextBody`) **survit** : c'est un mutant équivalent pour ce message, où le corps précède le `.hpm` et où MailKit choisit déjà le bon corps. La règle reste couverte par `MedicalSourcePartsTests` ;
  - **Redis, BAL déléguée** : le test lit les chaînes, les hachages, les listes et les ensembles, et cherche aussi un extrait du texte HPRIM. **Mutation MR** : le cache délégué écrit hors de sa famille exemptée, et le test passe au rouge (`Assert.DoesNotContain() Failure: Sub-string found`).
- **Prévention (règle d'or)** : `conventions/csharp.md`, entrée `document-medical-identifiant-propre` :
  - tout producteur de `MailMedicalDocumentDto` renseigne `DocumentId` ;
  - son test d'intégration a plusieurs documents **et** une pièce.
- **Non traité ici, à arbitrer par l'humain au HAG** :
  - la mesure du banc E015 sur les mails sans HPRIM. Le raisonnement reste valable : pour un mail sans HPRIM, le plan de récupération rend les mêmes parties et le même nombre d'allers-retours. La mesure est un point du test manuel ;
  - le compteur « signalés doublons » : il vaut 0 par construction (décision 6, task-193). Le compteur viendra avec le rapprochement au rattachement, en task-391.

## Sonar log

Analyse complète `healthplatform-api-mail` (SonarQube 9.9.8 local, `sonar.login`), sur la branche `feat/task-389-…`.

- **1ʳᵉ analyse** (`c2a12219`) : Quality Gate OK, **3 issues** sur le nouveau code, une commande par règle :
  - `S3267` (`EnrichmentFetchPlan`, boucle `foreach … if … yield return`) → `Where`, `21a13515` ;
  - `S4136` (des helpers insérés entre les deux surcharges d'`ExtractIheXdmZipsAsync`) → déplacés sous la seconde, `ff0954fb` ;
  - `CA1861` (tableaux littéraux passés à `Concat` dans `HprimSamples.Html`) → champs `static readonly`, `14ceb579`.
- **2ᵉ analyse** (`14ceb579`) : **QG OK, 0 issue** sur le nouveau code, aucun hotspot, new coverage 95,0 %. Les cinq suites sont vertes.
- **3ᵉ analyse** (`6998e4fa`, correctif de la revue de `/review`) : **QG OK, 0 issue** sur le nouveau code, new coverage 95,0 %, KPIs inchangés. Les cinq suites sont vertes (7 067).
- Phase 1 (new code) : ✓ 3 issues corrigées ; aucun test ajouté : la couverture tient le seuil.
- Phase 2 (legacy) : rien à faire (0 bug, 0 vulnérabilité, 0 smell sur le projet).

### KPIs qualité (baseline → final)

| Métrique | Baseline (`a120684f`, develop) | Final (`6998e4fa`) | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | = |
| New coverage | 95,1 % | 95,0 % | −0,1 pt (seuil tenu) |
| New bugs / vulnérabilités / smells | 0 / 0 / 0 | 0 / 0 / 0 | = |
| Bugs / Vulnérabilités / Smells (projet) | 0 / 0 / 0 | 0 / 0 / 0 | = |
| Security hotspots | 0 | 0 | = |
| Coverage projet | 97,5 % | 97,5 % | = |
| Duplication | 0,3 % | 0,3 % | = |
| Ratings fiabilité / sécurité / maintenabilité | A / A / A | A / A / A | = |

- **Conventions** (`conventions/csharp.md`) : `S3267` → 4 (variante itérateur), `S4136` → 2 (helper glissé entre deux surcharges), `CA1861` → 5 (données de test).
- **Règle d'or, point 3 — la récidive signale la lecture.** Les trois règles étaient déjà consignées. En début de `/develop`, la lecture de `conventions/csharp.md` s'est arrêtée aux titres et aux premières lignes des consignes ; les variantes (itérateur, données de test, placement des helpers) étaient dans le corps des entrées. Prévention : chaque variante est désormais en tête de son compteur, là où une lecture rapide la voit.

## Lint log
- skipped — `client-angular` non listé dans `**Repos**:` et aucun fichier Angular écrit par `/develop` pour cette task (l'arbre Angular peut porter le travail en cours de l'humain : il n'est pas touché, règle 6).

## Lint mobile log
- skipped — `client-mobile` non touché par la task.

## E2E log

> ⚠️ **Quarantaine de plus de 14 jours** : E2E-COMPOSE-002 [angular], posée le 2026-10-09 (17 jours), correction due par **task-350**.
> ⚠️ **Divergence à retirer** : E2E-MAILBOX-002 [angular] (task-395). Le client weda2 est revenu à la version du catalogue ; la décision appartient à l'humain.

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail touché (`6998e4fa`, après la reprise de revue) ; client-mobile sur `develop` à jour | ✅ verte (rejouée) | 50 verts, 0 flaky, 0 rouge, 0 quarantaine | 7 min 55 s |
| angular | api-mail touché (`6998e4fa`) ; weda2 sur son checkout courant | ✅ verte (rejouée) | 59 verts, 0 flaky, 0 rouge, 1 quarantaine (verte) | 8 min 4 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task (inchangé par la task : US backend, aucun parcours médecin modifié)
- Porte : **code 0**, rendue par ce run
- Historique : première passe verte sur `14ceb579` (8 min 11 s et 8 min 16 s). Les deux voies ont été **rejouées** sur `6998e4fa`, le correctif de la revue, pour que `/review` valide exactement le code testé.
- Quarantaines : E2E-COMPOSE-002 [angular] — task-350 (verte à ce run)
- Divergences ouvertes : E2E-MAILBOX-002 [angular] — task-395, **à retirer**
- Flaky : aucun
- Parcours touchés sans spec e2e modifié : aucun (aucun écran touché)
- Démontage : complet. Les ports 5052, 8100, 4200, 3993, 3465 et 3143 sont libres, aucun conteneur e2e ne tourne.

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
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
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
| E2E-WEDA-001 | 1 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ · divergence (task-395) | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |
| E2E-DELEG-001 | 1 | headless | Voir la BAL déléguée dans sa section, repliée sous la BAL principale, et lire un compte rendu | ✅ | ✅ |
| E2E-DELEG-002 | 1 | headless | Supprimer un message délégué vers la corbeille de la délégante, puis le restaurer | ✅ | ✅ |
| E2E-DELEG-003 | 1 | headless | Dans une BAL déléguée, seuls les gestes de gestion sont proposés | ✅ | ✅ |
| E2E-DELEG-004 | 1 | headless | La délégation retirée pendant la consultation ramène à sa propre réception | ✅ | ✅ |

**Divergences temporaires ouvertes** (1) :

- E2E-MAILBOX-002 [angular] — le code weda2 de task-378 (écran de panne à l'entrée et son test) n'est pas encore livré sur la branche weda2 ; divergence décidée par l'humain le 2026-10-25 — résorbée par task-395 — **à retirer** : le client est revenu à la version du catalogue

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/315 — label `awaiting-human-merge` (head `6998e4fa`)
- `dtos-mss` : aucune branche, aucun contrat changé (branche paresseuse non déclenchée)

## Code Review Summary

**Verdict : APPROVED en 2ᵉ passe** (revue indépendante, en lecture seule).

- **1ʳᵉ passe : CHANGES REQUESTED, ❌ 1.** Le document HPRIM n'avait pas de `DocumentId`, alors que `MailRepository` range les pièces d'un document par cet identifiant.
  - Conséquence : avec deux résultats et un PDF, les copies du PDF devenaient des pièces du message, et chaque document montrait le PDF nommé au patient de l'autre.
  - Correction : `6998e4fa`, un test d'intégration vu rouge sur le code d'avant, et la prévention `conventions/csharp.md#document-medical-identifiant-propre`.
- **2ᵉ passe : APPROVED.**
  - Le défaut est corrigé sur l'écriture, les pièces du mail, la voie liste, la voie contenu et le dossier patient.
  - L'identifiant aléatoire ne touche aucune route, puisqu'elles prennent l'Id de ligne, ni la détection de doublon, qui sort faute d'INS.
- **Suggestions non bloquantes restantes** :
  - `ParseBirthDate` ramène aussi une coquille sur quatre chiffres au siècle précédent ;
  - mutant équivalent sur `TextBodyOf(summary)` ;
  - pas de test d'intégration propre à `ReadEmailWithoutPersistingAsync`, qui emprunte la règle partagée.
- **À arbitrer par l'humain au HAG** (encadré dans la PR) :
  - la mesure E015 sur les mails sans HPRIM ;
  - le compteur « signalés doublons », qui vaut 0 par construction (décision 6).

| Comportement atteignable par un endpoint | Test d'intégration | Rouge |
|---|---|---|
| `.hpm` intégré + PDF → document HPRIM non rattaché, PDF, corps intact, `PendingIntegrationsCount` | `HprimReceptionEndToEndTests.AnHpmEmbeddedInTheBody_…` | M1, M4 |
| `.hpm` sans marqueurs → aucun document, pièce listée | `AnHpmWithoutEndMarkers_…` | M1 |
| CDA valide + HPRIM → CDA seul | `AValidCdaBiologyReport_…` | M3 |
| CDA illisible + HPRIM → HPRIM | `AnUnreadableCda_…` | M1 |
| Reçu deux fois → deux documents, aucun doublon | `TheSameHprimReceivedTwice_…` | M1 |
| Deux résultats → deux documents | `AnHprimWithTwoResults_GivesTwoDocuments` | M1 |
| Deux résultats + PDF → chaque document a son seul PDF, le mail ses seules pièces | `AnHprimWithTwoResults_AndAPdf_…` | code d'avant le correctif |
| Voie par partie → `.hpm` et PDF récupérés, corps intact | `OnThePartByPartFetchPath_…` | M2, M5 (corps : mutant équivalent) |
| BAL déléguée → décodé, rien en base ni dans Redis hors cache J | `DelegationEndToEndTests.ADelegatedHprim_…` | M2, MR |
| Convention règle 14 | `DelegatedPersistenceGuardScanTests.TheHprimPathWritesNothing` | MC |
