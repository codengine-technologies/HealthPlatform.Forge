# todo-task-193.md — CDA sans identifiant de document : marqué doublon d'un document d'un autre patient, puis masqué

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axe métier MSSanté).

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
