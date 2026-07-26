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
