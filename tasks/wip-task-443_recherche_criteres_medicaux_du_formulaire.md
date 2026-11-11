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

## Sonar log

**Mode A** (chaîné depuis `/develop`), `api-mail`, branche `feat/task-443-…`, build `Release`, 2 itérations.

### KPIs qualité (baseline → final)

| KPI | Baseline (analyse de task-442) | Itération 1 | Final |
|---|---|---|---|
| Quality Gate | OK | OK | **OK** |
| Bugs / Vulnérabilités | 0 / 0 | 0 / 0 | 0 / 0 |
| Code smells | 0 | 4 | **0** |
| Hotspots à revoir | 0 | 0 | 0 |
| Couverture globale | 97,8 % | 97,8 % | **97,8 %** |
| Couverture du nouveau code | — | 96,0 % | **96,0 %** |
| Duplication | 0,4 % | 0,4 % | 0,4 % |
| Ratings (fiabilité / sécurité / maintenabilité) | A / A / A | A / A / A | A / A / A |

**Phase 1 — nouveau code** : 4 issues, toutes corrigées à la main.
- **CA1862** (`SemanticSearchRepository.Criteria.cs`, ×1) : `m.FromAddress.ToLower() != own` dans une requête EF.
  `string.Equals(…, OrdinalIgnoreCase)` ne se traduit pas en SQL : l'adresse de la boîte se compare désormais sur la
  clé du regroupement, déjà en minuscules. Comportement prouvé par la mutation B11 (rouge).
- **xUnit1045** (×3, `SemanticSearchServiceMedicalCriteriaTests`, `SearchFilterCriterionTests`) : théories en
  `TheoryData<string, SearchFilterDto>`. Elles prennent maintenant le nom du cas, et un dictionnaire `static readonly`
  donne le DTO.

**Phase 2 — dette ancienne** : 0 issue ouverte sur le projet.

**Incident d'outillage** (sans effet sur le code) : une première relance de l'itération 2, faite avec `&`, a tourné en
même temps que la relance suivante. Les deux ont produit 26 échecs parasites et une couverture mêlée, publiée à 90,1 %.
L'analyse a été refaite d'un seul tenant, `TestResults` et `.sonarqube` vidés : ce sont les chiffres ci-dessus. Le piège
est consigné en mémoire de session.

**Tests de l'analyse finale** : domain 210, application 4 098, infrastructure 743, api 1 375, intégration 1 242
(+16 ignorés), 0 échec, aucun plantage masqué.

**Conventions** :
- `xUnit1045` : compteur porté à 3 ; récidive sur du code frais, donc entrée non relue avant d'écrire la théorie.
- `CA1862` : compteur porté à 2, avec la variante EF (comparer une valeur déjà en minuscules ou `EF.Functions.ILike`).

## Lint log

**Mode A** (chaîné depuis `/sonar`), `client-angular` code-only, branche extraite `feature/nova-mss-weda-integration`,
base `origin/next`. Aucune opération git d'écriture.

Lint par le contournement du playbook (task-367) : `nx run-many -t lint -p mss-lib`, puis `eslint --format json` sur les
fichiers `.ts` de la task (le `.html` et le `.spec.ts` sont hors d'ESLint), puis `stylelint` sur le SCSS.

| Mesure | Résultat |
|---|---|
| Erreurs ESLint (mss-lib + fichiers de la task) | **0** |
| Avertissements mss-lib | 48, inchangés |
| `mail-search.component.ts` | 1 avertissement `max-lines`, déjà présent avant la task |
| `mss-api.service.ts` | 5 avertissements antérieurs (`max-lines`, `jsdoc/require-example` sur d'autres méthodes) ; `getSearchSenders` a sa JSDoc complète |
| `functional.e2e.ts` | 5 avertissements antérieurs ; le test `E2E-SEARCH-008` n'en porte aucun |
| Sélecteurs patient et expéditeurs | 0 |
| `stylelint` (`mail-search/**/*.scss`) | 0 |

**Itérations** : 0. Aucune erreur, et aucun avertissement sur une ligne ajoutée.

**Conventions** : aucune règle corrigée à la main, aucune entrée.

## Lint mobile log

- skipped — client-mobile non touché (absent des `**Repos**`). `E2E-SEARCH-008` déclare la divergence temporaire du
  mobile (task-451).

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail et dtos-mss touchés | ✅ verte (rejouée après la retouche du catalogue) | 60 verts, 0 flaky, 0 rouge, 0 quarantaine | ~9 min |
| angular | api-mail, dtos-mss et client-angular touchés | ✅ verte (3ᵉ passage) | 74 verts, 0 flaky, 0 rouge, 1 quarantaine (E2E-COMPOSE-002, verte) | ~10 min |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ `feat/task-443-…`. `E2E-SEARCH-008` v1 est ajouté : angular requis, mobile
  en divergence temporaire jusqu'à task-451.
- Nouveau parcours weda2 : `recherche — restreindre à un patient et à ses biologies anormales @E2E-SEARCH-008`, vert en
  2,9 s.
- **Deux passages rouges, corrigés dans le test, pas dans le code** :
  1. **Premier passage** : la ligne du HPRIM était cherchée par l'objet du message, alors qu'elle affiche le titre de
     son document (« Résultats de biologie »). C'est une récidive de la consigne `conventions/e2e.md` « ligne-de-cda »,
     élargie au HPRIM, compteur porté à 3. Les lignes se désignent désormais par leur uid.
  2. **Deuxième passage** : le test supposait que le compte rendu CDA de `PAT-TROIS` ne portait aucun indicateur. Il
     en porte un : thyroxine libre basse, marquée par le laboratoire. La recherche rendait donc, à raison, les deux
     biologies anormales. Le scénario est réécrit sur la réalité du seed :
     - « Biologie anormale » rend les deux biologies, et pas un message ordinaire ;
     - le choix de `PAT-TROIS` retire le HPRIM, qui ne lui est pas rattaché, et garde son compte rendu.

     L'attendu et le seed du catalogue suivent. La valeur hors bornes sans indicateur est prouvée par le test
     d'intégration (mutation B4).
- Parcours touchés sans spec e2e modifié : aucun (le spec de la recherche est modifié).
- Démontage : complet (ports 5052 et 47399 libres, aucun conteneur e2e résiduel).

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
| E2E-SEARCH-001 | 2 | headless | Composer ses critères puis lancer la recherche | ✅ | ✅ (v1) · divergence (task-450) |
| E2E-SEARCH-002 | 1 | headless | Un mot rare et accentué trouve le message qui le contient | ✅ | ✅ |
| E2E-SEARCH-003 | 1 | headless | Un numéro de dossier trouve son message, et un seul | ✅ | ✅ |
| E2E-SEARCH-008 | 1 | headless | Restreindre la recherche à un patient et à ses biologies anormales | ✅ | ⛔ non joué · divergence (task-451) |
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

**Divergences temporaires ouvertes** (2) :

- E2E-SEARCH-001 [mobile] — le mobile adopte le formulaire à un seul niveau avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-008 [mobile] — les critères médicaux arrivent sur le mobile avec la refonte mobile — résorbée par task-451

**Parité : verte** — aucun écart entre le catalogue et les suites.

## Timings

*(généré par `tools/timing/report.sh --task task-443 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 24 s | — | — | — | — |
| /develop | ok | 59 min 12 s | 7 (1 min 04 s) | 6 (13 min 22 s) | — | dtos-mss 1B/0T, api-mail 4B/4T, client-angular 2B/2T |
| /sonar | ok | 32 min 42 s | 4 (1 min 59 s) | 20 (32 min 07 s) | 7 (2 min 15 s) | 2 itération(s), api-mail 4B/20T, 4 issues de nouveau code corrigées (CA1862, xUnit1045 x3) |
| /lint-angular | ok | 33 s | — | — | — | 0 erreur ; avertissements antérieurs |
| /lint-mobile | skipped | 0.4 s | — | — | — | client-mobile non touché |
| /e2e | ok | 52 min 03 s | — | — | — | e2e ×6 (48 min 46 s), 2 voies vertes ; test E2E-SEARCH-008 corrigé deux fois |
| **Total cycle** | | **2 h 24 min** | **11 (3 min 03 s)** | **26 (45 min 30 s)** | **7 (2 min 15 s)** | |

Autres commandes mesurées : lint ×1 (10 s), nuget-wait ×2 (55 s), restore ×2 (49 s)
