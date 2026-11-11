# todo-task-443.md — Recherche : critères médicaux du formulaire

**Repos**: api-mail, dtos-mss, client-angular
**Dependencies**: done-task-442 (formulaire à un seul niveau), done-task-439 (plein texte fiable, nom des pièces
jointes indexé)
**Epic**: E023
**Priorité**: EPIC E023, demandée par l'humain le 2026-11-10. Critères retenus comme prioritaires par l'humain : patient
identifié, date du document médical, biologie anormale, expéditeur (établissement, laboratoire, confrère), nom de pièce
jointe.

> **Origine.** Analyse du 2026-11-10. Le médecin ne cherche pas « un mail » : il cherche le compte rendu d'un patient,
> la biologie anormale d'hier, le courrier d'un service. Le formulaire doit parler ce langage.

## Ce qui est établi

- Le contrat de requête (`SearchFilterDto`) porte déjà : `PatientFilters` (`PatientId`, `LastName`, `Ins`),
  `DateFilters.MedicalDocumentDateFrom/To` et `BiologyResultDateFrom/To`, `ContentFilters.HasBiologyResults` et
  `MedicalDocumentType`. Le formulaire de weda2 n'expose ni le patient, ni la date du document médical.
- Aucun critère ne restreint au **nom d'une pièce jointe**, ni aux **biologies anormales**, ni à un **expéditeur
  choisi** (le champ « De » est une saisie libre).
- L'anomalie d'un résultat de biologie est l'**indicateur posé par le laboratoire** (task-392) : code d'interprétation
  du CDA, champ 8 d'une ligne `RES|` HPRIM. Il est déjà connu de la plateforme (acquittements de biologie).

## Objective

Le médecin restreint sa recherche avec les critères de son métier, dans le formulaire de task-442.

Nouveaux critères, chacun dans la section qui lui correspond :
- **Patient** : le médecin **choisit** un patient de la boîte dans une liste (recherche par nom de naissance, nom
  d'utilisation, prénom ; affichage nom de naissance, prénom, date de naissance, sexe). Jamais de saisie libre pour ce
  critère, jamais de rapprochement approximatif : le filtre porte sur l'identifiant du patient choisi, et ne rend que
  les messages rattachés à ce patient.
- **Date du document médical** : « Du … au … », distincte de la période d'envoi du message. Un message est retenu si au
  moins un de ses documents médicaux tombe dans la plage.
- **Biologie anormale** : ne retient que les messages portant au moins un résultat de biologie **marqué anormal par le
  laboratoire**. Aucune déduction à partir des bornes.
- **Expéditeur** : le médecin choisit un ou plusieurs correspondants **parmi ceux qui ont écrit à la boîte**
  (établissements, laboratoires, confrères), avec le nom de l'Annuaire Santé quand il est connu, sinon l'adresse. La
  saisie libre « De » reste disponible à côté.
- **Nom de pièce jointe** : texte cherché dans le **nom** des pièces jointes seulement, insensible aux accents et à la
  casse (même normalisation que task-439).

Règles communes :
- Les critères se combinent entre eux et avec le texte (ET). Plusieurs expéditeurs choisis se combinent en OU.
- Les critères s'appliquent aux trois parties de résultats (tous les mots, une partie, proches) : un résultat proche
  par le sens qui ne respecte pas un critère n'est pas rendu.
- Un critère seul, sans texte, est une recherche valide (ex. : tous les messages du patient X avec biologie anormale).
- Les critères sont rejoués par l'historique des recherches.
- **Règle 14** : la recherche lit la base de la boîte, après le verdict de l'opérateur ; titulaire, délégataire et
  membre voient les mêmes critères et les mêmes résultats.

### Hors périmètre

- Le mobile : task-451.
- Les patients proposés pendant la frappe : task-449.

## Definition of Done

- [ ] Build passes (0 errors) : `HealthPlatform.Api.Mail.sln`, `HealthPlatform.Dtos.Mss.csproj`, weda2 (`nx build weda2`)
- [ ] Tests pass (0 failures) : `HealthPlatform.Api.Mail.sln`, `nx test weda2`, `nx test mss-lib`
- [ ] Tests unitaires pour chaque nouveau critère et leur combinaison (≥ 1 test par critère et par branche)
- [ ] **Tests d'intégration de bout en bout (règle 1b), `POST /api/v1/Search/semantic`**, sur le corpus fictif de
      task-438 complété, lus dans la réponse réelle (`Hits`), chacun vu rouge par mutation :
      - **patient** : seuls les messages rattachés au patient choisi sont rendus ; un homonyme non rattaché ne l'est pas ;
      - **date du document médical** : un message envoyé dans la plage mais dont le document est hors plage n'est pas
        rendu, et l'inverse l'est ;
      - **biologie anormale** : un message dont le laboratoire a marqué un résultat anormal est rendu ; un message dont
        une valeur sort des bornes **sans** indicateur du laboratoire ne l'est pas ;
      - **expéditeur** : deux expéditeurs choisis rendent les messages de l'un ou de l'autre, et seulement eux ;
      - **nom de pièce jointe** : `compte rendu` sans accent trouve `Compte-rendu_écho.pdf` ; un mot présent seulement
        dans le corps n'est pas rendu ;
      - **critère et proches** : un résultat proche par le sens qui ne respecte pas le critère n'est pas rendu ;
      - **cas d'échec** : un identifiant de patient inconnu de la boîte → 400 ou 404 en `ProblemDetails`, jamais une
        liste vide trompeuse
- [ ] **Test d'intégration de bout en bout** pour la liste des expéditeurs de la boîte (route existante ou nouvelle) :
      les correspondants rendus sont ceux qui ont écrit à la boîte, avec le nom de l'Annuaire Santé s'il est connu ;
      cas d'échec : boîte sans verdict de l'opérateur → refus
- [ ] Contrat `dtos-mss` publié (rétrocompatible) et consommateurs .NET mis à jour ; types TypeScript de weda2 alignés
- [ ] Tests de composant weda2 : choix d'un patient dans la liste (aucune saisie libre acceptée comme critère patient),
      plage de dates du document, biologie anormale, choix de plusieurs expéditeurs, nom de pièce jointe ; chacun vu
      rouge par mutation
- [ ] **Scénario e2e** `E2E-SEARCH-008` v1 ajouté à `Api/Mail/e2e/scenarios.yml` : « Restreindre la recherche à un
      patient et à ses biologies anormales » — attendu : seuls les messages du patient choisi portant une biologie
      marquée anormale par le laboratoire sont affichés. Clients : angular requis, mobile requis avec **divergence
      temporaire** (raison : « les critères médicaux arrivent sur le mobile avec la refonte mobile », tache :
      task-451). Implémenté dans weda2, vu rouge par mutation
- [ ] `data-testid` sur chaque élément interactif ajouté
- [ ] Aucune donnée de santé en clair dans les logs (identifiant patient, nom, INS, nom de pièce jointe, termes compris)
- [ ] client-angular : code-only, aucun commit
- [ ] **Prévention (règle d'or)** : consigne dans `conventions/csharp.md` : un critère de recherche s'applique à toutes
      les sources de résultats (plein texte et sens), et se prouve par un test qui lit un résultat proche écarté

## Manual Test Plan

1. Lancer le backend sur le corpus fictif de task-438 : `cd Api/Mail/src/AppHost && dotnet run`, puis le seed de
   référence. Lancer weda2 : `cd Client/Angular/front && npm start`.
2. Ouvrir la fenêtre de recherche :
   - section **Patient** : taper `bern`, choisir « BERNARD Catherine, née le … » ; aucune saisie libre n'est retenue
     sans choix dans la liste ;
   - cocher **Biologie anormale**, lancer : seuls les messages de Catherine BERNARD avec un résultat marqué anormal par
     le laboratoire apparaissent.
3. Réinitialiser, choisir deux **expéditeurs** dans la liste (un laboratoire, un centre hospitalier), lancer : seuls
   leurs messages apparaissent.
4. Réinitialiser, **Date du document médical** du 01/01/2025 au 31/03/2025, lancer : seuls les messages dont un
   document date de cette période apparaissent, quelle que soit leur date d'envoi.
5. Réinitialiser, **Nom de pièce jointe** `compte rendu`, lancer : les messages dont une pièce jointe s'appelle
   « Compte-rendu… » apparaissent.
6. Rejouer une de ces recherches depuis l'historique : les critères sont restaurés.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du praticien)
- **Vague Ségur** : hors Ségur — ergonomie de la recherche
- **Exigences DSR honorées** : non applicable
- **INS** : le critère patient porte sur l'identifiant interne du patient choisi, quel que soit le statut de son INS
  (qualifiée, récupérée, provisoire). L'INS n'est **jamais affichée** dans la liste de choix ni dans les libellés ; les
  traits affichés sont nom de naissance, prénom, date de naissance, sexe (traits d'identification de l'identito-vigilance)
- **Authentification PS** : inchangée — PSC (e-CPS), niveau eIDAS substantiel
- **Habilitations** : inchangées — verdict de l'opérateur MSSanté (règle 14) ; mêmes critères pour titulaire,
  délégataire et membre
- **Interop CI-SIS** : lecture des données déjà extraites des documents CDA r2 (date du document, code d'interprétation
  des résultats de biologie) et des comptes rendus HPRIM ; aucun nouvel échange
- **Tracé PGSSI-S** : chaque recherche tracée (`MailSearch`) au nom de la personne réelle, avec son rôle, 3 653 jours ;
  la trace ne porte ni le terme, ni l'identité du patient filtré en clair ; la lecture de la liste des expéditeurs est
  tracée comme une consultation de la boîte
- **Consentement patient** : non applicable — aucune donnée nouvelle collectée ni partagée
- **Référentiels métier** : codes d'interprétation des résultats de biologie (HL7 ObservationInterpretation, champ 8 de
  `RES|` HPRIM), déjà portés par la plateforme ; aucun nouveau référentiel
- **Hébergement HDS** : oui — données lues dans la base de la boîte, inchangée
- **AIPD / impact RGPD** : inchangé — mêmes données, nouvelle façon de les filtrer

## Branches
- `api-mail` (pushed) : feat/task-443-recherche-criteres-medicaux-du — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-443-recherche-criteres-medicaux-du
- `dtos-mss` (paresseuse) : branche créée par `/develop` au premier contrat touché
- `client-angular` (code-only) : la forge écrit le code sur la branche extraite dans `Client/Angular/` (au `/start` : `feature/nova-mss-weda-integration`, propre) — l'humain gère branche, commit, push, PR TFS

## Develop log

**Repos touchés** : `dtos-mss` (branche créée par `/develop`), `api-mail`, `client-angular` (code-only, non commité).

### dtos-mss — `HealthPlatform.Dtos.Mss` 584 puis 585
- `SearchFilterFieldDto` : `FromAddresses` (expéditeurs choisis, 20 au plus, en OU), `AttachmentName`.
- `SearchFilterContentTypeDto` : `HasAbnormalBiology`.
- Nouveau `SearchSenderDto` : `Address`, `DisplayName`, `MailCount`.
- 585 : **une seule définition de « au moins un critère »**, `SearchFilterDto.HasAnyCriterion()` (une par groupe), lue
  par la validation de `SearchRequestDto`. Trois copies existaient (DTO, service, historique) et avaient divergé :
  - la validation refusait en **400** une recherche sans texte portant un critère nouveau (constaté : trois tests
    d'intégration rouges en 400 avant le correctif, verts après) ;
  - l'historique ignorait le critère patient : une recherche sur un patient seul n'était jamais enregistrée.
- Contrat rétrocompatible. Consommateurs .NET : `api-mail` porté en 585. `client-blazor` n'est pas dans les `**Repos**` :
  il garde sa version, sans incidence (champs ajoutés seulement).

### api-mail
- **Dépendances** (commit séparé) :
  - `Dtos.Mss` 585 ;
  - `Aspire.Hosting.*` 13.6.1 → 13.6.5 (CVE-2026-120006, GHSA-f7vh-h5g3-7jrh) ;
  - `Microsoft.AspNetCore.WebUtilities` transitive forcée en 2.3.14 dans les projets de test (CVE-2026-118750,
    GHSA-6527-9fp8-r4x6).

  Les deux alertes, publiées le 2026-11-10, faisaient échouer la restauration (NU1902/NU1903 en erreur) : `develop`
  cassera au prochain restore sans ce correctif.
- `SemanticSearchRepository.Criteria.cs` (partiel nouveau) :
  - `ApplyChosenSendersFilter` : adresse exacte, casse ignorée, en OU ;
  - `ApplyAttachmentNameFilter` : chaque mot significatif dans le nom d'une même pièce jointe, lu par
    `search_normalize` (fonction SQL de task-439, déclarée à EF dans `MailDataContext.Search.cs`) ;
  - `ApplyAbnormalBiologyFilter` : `IsFlagged`, posé depuis le code d'interprétation du laboratoire seulement ;
  - `PatientExistsAsync` ;
  - `ListSendersAsync` : correspondants de la boîte, les plus fréquents d'abord, avec le nom de l'Annuaire Santé quand
    un contact issu de l'annuaire (`Fhir`, `Ldap`) porte l'adresse. Brouillons et adresse de la boîte écartés.
- Le patient et la date du document médical étaient déjà filtrés par `SearchByFiltersAsync` : inchangés.
- `SemanticSearchService` :
  - un patient inconnu de la boîte → `NotFoundException` (`search_patient_unknown`, **404** `ProblemDetails`), ajoutée
    aux exceptions métier qui gardent leur code ;
  - `HasAnyCriterion()` remplace la copie locale ;
  - le journal nomme les critères (`ChosenSenders=n`, `AttachmentName`, `MedicalDocumentDate`, `HasAbnormalBiology`),
    jamais leurs valeurs.
- `SearchHistoryService` : `HasAnyCriterion()` remplace la copie locale.
- `SearchController` : `GET /api/v1/search/senders`, `[Audited(MailSearch)]`, scope d'opération `GetSenders`. Le verrou
  de la règle 14 (middleware d'enrichissement) s'y applique comme à toute route.

### Règle 1b — comportement → test d'intégration → preuve rouge
Tests de bout en bout `SearchMedicalCriteriaIntegrationTests` (vraie route, vrai service, vrai repository, PostgreSQL ;
seul le générateur d'embeddings est simulé), et `MailboxAccessLockIntegrationTests` pour le refus :

| Comportement | Test | Preuve rouge |
|---|---|---|
| Patient : ses messages seuls, pas l'homonyme | `Patient_Chosen_…`, `PatientAndAbnormalBiology_…` | B1 (2 rouges) |
| Patient inconnu → 404 `ProblemDetails` | `Patient_UnknownToTheMailbox_…` | B2 |
| Date du document, pas de l'envoi | `MedicalDocumentDate_…` | B3 |
| Biologie anormale : indicateur du laboratoire, jamais les bornes | `AbnormalBiology_…`, `PatientAndAbnormalBiology_…` | B4 (2 rouges) |
| Deux expéditeurs, en OU, casse ignorée | `ChosenSenders_…` | B5, B6 |
| Nom de pièce jointe, accents et casse ignorés, corps exclu | `AttachmentName_…` | B7 |
| Un critère écarte aussi un résultat proche | `Criterion_AppliesToTheSimilarResults_…` | B8, B5 |
| Liste des expéditeurs : fréquence, nom de l'annuaire, brouillons et boîte écartés | `Senders_…` | B9, B10, B11 |
| Liste des expéditeurs refusée sans verdict de l'opérateur | `Delegate_RefusedAtRenewal_Gets403_OnTheSearchSenders_…` | verrou existant, éprouvé |
| Recherche sans texte sur un critère nouveau acceptée | les trois tests sans texte ci-dessus | 400 avant `HasAnyCriterion` |

Tests unitaires :
- `SearchFilterCriterionTests` : chaque critère, chaque groupe, blancs et listes vides ;
- `SemanticSearchServiceMedicalCriteriaTests` ;
- `SearchHistoryServiceTests` : patient seul enregistré, critères rejoués ;
- `SemanticSearchRepositoryCriteriaTests` : motifs du nom de pièce jointe, adresses choisies.

### client-angular — `libs/mss/src/features/mail/components/mail-search/`
- Section « Critères » :
  - **Patient** : `mss-mail-search-patient-picker`, choix dans la liste uniquement (`GET /Patients/search`, après
    300 ms de frappe, `switchMap`). Libellé : nom, prénom, « né(e) le », jamais l'INS. Entrée ne retient un patient que
    s'il est le seul proposé ;
  - **Expéditeurs** : `mss-mail-search-sender-picker`, plusieurs correspondants de la boîte (`GET /search/senders`,
    chargés une fois) ;
  - **Date du document médical** : du … au … ;
  - **Nom de pièce jointe**.
- Puce **Biologie anormale** (Contenu médical).
- Instantané, rejeu et historique : patient, expéditeurs, dates, nom de pièce jointe, biologie anormale. Le nom du patient
  est relu par `getPatientById`, car l'historique ne garde que l'identifiant.
- « Réinitialiser » recrée les sélecteurs.
- Styles des champs à liste mis en commun (`_mail-search-combobox.scss`), « De » compris.
- Spec du formulaire : 42 tests. Spec du libellé du patient : 5 tests.
- Mutations A1 à A11 rouges ; A11 ne l'est devenue qu'après correction du test, qui ne la voyait pas.
- Mutations N1 à N7 du champ « De » (task-442) rejouées : rouges.

### Scénario e2e
- `E2E-SEARCH-008` v1 au catalogue (angular requis ; mobile requis, divergence temporaire task-451).
- weda2 : `recherche — restreindre à un patient et à ses biologies anormales`. Sans texte, donc sans fournisseur d'IA,
  sur le seed :
  - « Biologie anormale » rend le HPRIM (potassium « H », glycémie hors bornes sans indicateur) ;
  - elle ne rend pas le compte rendu CDA de `PAT-TROIS`, qui n'a aucun indicateur ;
  - choisir en plus `PAT-TROIS` retire le HPRIM, qui ne lui est pas rattaché.

### Passe qualité §Q (/simplify, 2 relectures)
Appliqué :
- sources de l'annuaire par `nameof(ContactSource…)` ;
- exclusion de la boîte avant le regroupement ;
- `ContactDto` projeté directement ;
- aides de test (`Embedded`, `Attachment`, route des expéditeurs) dans `SearchEndpointHarness` ;
- libellé du patient en attente à `null` (au lieu d'un texte sentinelle) ;
- `formatIsoDate` réutilisée ;
- accents pliés par `\p{Diacritic}`, une fois par liste ;
- recherche de patients après 300 ms de frappe ;
- styles communs ;
- aides du spec dédoublonnées.

Écarté :
- l'index trigramme pour le nom de pièce jointe : peu de pièces jointes par message, coût à mesurer avant de bâtir un
  second chemin SQL ;
- les noms de critères portés par le contrat (refonte des journaux et nouvelle publication NuGet, hors objet) ;
- le helper de perte de focus : trois corps de trois lignes.

### Validation (après la passe qualité)
- api-mail : build vert. Tests : domain 210, infrastructure 743, api 1 375, application 4 098, intégration 1 242
  (+16 ignorés), 0 échec, aucun plantage masqué.
- weda2 : build vert. Tests : weda2 2 683, mss-lib 1 526, 0 échec. ESLint 0 erreur ; stylelint 0.

### Écarts et suites
- La recherche de patients existante (`GET /Patients/search`) ne porte que sur le nom (`LastName`). L'objectif cite le
  nom de naissance, le nom d'utilisation et le prénom, mais la fiche n'a qu'un champ nom. Le prénom n'est pas cherché :
  à arbitrer, avec un test d'intégration sur la route des patients.
- Le champ « De » (un contact, correspondance partielle) et « Expéditeurs » (adresses exactes, en OU) filtrent tous
  deux l'expéditeur, combinés en ET : question produit à poser.

### Prévention (règle d'or)
`conventions/csharp.md` § `critere-de-recherche-sur-toutes-les-sources`.

## Timings

*(généré par `tools/timing/report.sh --task task-443 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 24 s | — | — | — | — |
| /develop | ok | 59 min 12 s | 7 (1 min 04 s) | 6 (13 min 22 s) | — | dtos-mss 1B/0T, api-mail 4B/4T, client-angular 2B/2T |
| **Total cycle** | | **59 min 37 s** | **7 (1 min 04 s)** | **6 (13 min 22 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : nuget-wait ×2 (55 s), restore ×2 (49 s)
