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

## Timings

*(généré par `tools/timing/report.sh --task task-443 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 24 s | — | — | — | — |
| **Total cycle** | | **24 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |
