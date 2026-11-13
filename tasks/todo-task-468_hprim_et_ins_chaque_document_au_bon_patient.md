# todo-task-468.md — HPRIM et INS : chaque document au bon patient

**Repos**: api-mail, client-angular, client-mobile
**Dependencies**: aucune
**Epic**: E025
**Priorité**: EPIC E025, issue de l'audit du 2026-11-12/13, validée par l'humain le 2026-11-13. Deuxième du lot :
un document ou une identité au mauvais patient est un risque d'identitovigilance.

> **Origine.** Audit en lecture seule du 2026-11-12/13 (agents « données, audit, IA » et « bugs mobile »). Le défaut
> du PDF HPRIM et celui des dates ont été relus dans le code par l'orchestrateur ; ceux de l'INS et de la fenêtre de
> rattachement mobile aussi, le 2026-11-13.

## Ce qui est établi

Lecture du code au 2026-11-13 :

- **PDF HPRIM attaché à tous les documents.** `IheXdmProcessingService.cs:317` appelle
  `HprimMedicalDocuments.FromFiles(contents, pdfFiles.FirstOrDefault()?.Content)` ; `HprimMedicalDocuments.cs:68` et
  `:107-110` attachent ce **premier** PDF à chaque résultat (le commentaire le dit : « le PDF du message est associé à
  chaque document »). Un mail de laboratoire avec `A.hpm`, `B.hpm`, `A.pdf`, `B.pdf`, ou un seul `.hpm` à plusieurs
  résultats (jusqu'à 100), range le PDF de A dans le dossier de B une fois les documents rattachés.
- **Dates HPRIM.** `HprimReader.cs:93-94` essaie `ddMMyyyy` avant `yyyyMMdd` : `20050314` est lu le 20/05/0314. Tout
  patient né entre 2001 et 2012 (ou 1901-1912) dont le laboratoire écrit `AAAAMMJJ` a une date de naissance fausse ;
  la suggestion de rattachement par traits (task-391) échoue ou propose un autre patient.
  `ParseBirthDate` (`:209-213`) ne corrige que les dates futures.
- **Séparateur à trois étoiles.** Un fichier est reconnu HPRIM sur `***FIN***` (`HprimReader.cs:79-80`), mais un
  résultat n'est clos que par `****FIN****` exact (`:74`). Un fichier à séparateurs trois étoiles est lu comme un seul
  résultat : les lignes `RES|` de tous les patients vont sous l'en-tête du premier.
- **INS corse refusée.** `InsValidationService.cs:31` lit le NIR par `long.TryParse` : un NIR portant `2A` ou `2B`
  (nés en Corse depuis 1976) échoue, `IsQualified = false`. Les deux clients bloquent alors l'envoi vers Mon Espace
  Santé (`mail-compose.component.ts:1122` mobile, `:1323` web).
- **Date de naissance déduite du NIR.** `InsValidationService.cs:64-91` fabrique une date au 1er du mois, avec un
  siècle deviné (`year <= année courante → 20xx`) : un patient né en 1925 est présenté né en 2025. Les deux clients
  l'affichent dans la confirmation d'identité avant envoi (`mail-compose.component.ts:1133-1134` mobile, `:1339-1340`
  web), par `new Date(chaîne)` qui recule d'un jour dans les fuseaux négatifs.
- **INS à l'ingestion.** `CdaParsingService.cs:331-332` reprend `INSCode.Extension` et `.Key` du CDA reçu ;
  `MailRepository.cs:463-501` s'en sert comme clé de rattachement automatique, sans contrôle de clé, sans rognage, sans
  comparer les traits à la fiche trouvée. Une INS fautive ou de remplissage d'un émetteur range le document dans la
  fiche d'un autre patient, sans alerte.
- **Fenêtre de rattachement mobile.** `patient-attachment-dialog.component.ts:219-239` (`loadCandidates`) souscrit
  sans annuler la requête précédente ; l'instance est unique dans le détail du mail. Fermer la fenêtre de DUPONT puis
  ouvrir celle de MARTIN : la réponse tardive de DUPONT remplace les candidats de MARTIN, et un toucher rattache le
  document de MARTIN à la fiche de DUPONT (`expectedCurrentPatientId` ne protège pas un document sans patient).

## Objective

Un compte rendu, son PDF et l'identité affichée du patient correspondent toujours au bon patient. Le rattachement
automatique n'a lieu que sur une identité sûre ; le doute va à l'intégration manuelle.

Règles :

1. **PDF HPRIM.**
   - Un mail portant **un seul** résultat HPRIM et **un seul** PDF : le PDF est associé à ce document.
   - Plusieurs résultats : un PDF n'est associé à un document que s'il s'apparie **sans ambiguïté** par son nom de
     fichier à ce résultat.
   - Sinon le PDF reste une pièce jointe du message, associée à aucun document.
2. **Dates HPRIM** : `AAAAMMJJ` est essayé avant `JJMMAAAA` ; une année hors de 1880 à l'année courante est rejetée
   (date absente plutôt que fausse).
3. **Séparateur HPRIM** : `***FIN***` et `****FIN****` closent un résultat de la même façon.
4. **Validation de l'INS** (`POST patients/validate-ins`) :
   - `2A` vaut 19 et `2B` vaut 18 pour le calcul de la clé (règle NIR) ;
   - **aucune date de naissance n'est déduite du NIR** : il ne porte ni le jour ni le siècle. Le champ est rendu vide ;
   - la confirmation d'identité avant envoi affiche la date de naissance de la fiche patient quand elle est connue,
     sinon aucune date ;
   - une date de naissance s'affiche sans conversion de fuseau, sur les deux clients.
5. **INS à l'ingestion** (identitovigilance, validée par l'humain le 2026-11-13) : le rattachement automatique par INS
   exige, pour les OID NIR (`1.2.250.1.213.1.4.8`) et NIA (`1.2.250.1.213.1.4.9`) :
   - une clé de contrôle valide ;
   - des traits du document (nom de naissance, date de naissance) qui **ne contredisent pas** la fiche trouvée. Un
     trait absent ne contredit pas.

   Sinon le document va dans la file « à intégrer », sans rattachement automatique **ni création de fiche**. Le
   médecin l'intègre à la main.
6. **Fenêtre de rattachement (mobile)** : une réponse qui ne concerne plus le document affiché est ignorée.

### Hors périmètre

- Les règles de signalement de la biologie (task-467).
- Le téléservice INSi et le statut « qualifié » au sens du RNIV : le champ `IsQualified` garde son nom et son sens
  actuel (clé valide) ; le renommer demanderait une publication de `dtos-mss` sans gain pour le médecin.

## Definition of Done

- [ ] Tests unitaires : association du PDF (1 résultat / 1 PDF ; plusieurs résultats appariés par nom ; ambiguïté →
      aucune association) ; dates HPRIM (`20050314`, `14032005`, `14/03/2005`, année 0314 rejetée) ; séparateur à
      trois étoiles (deux résultats lus) ; clé INS `2A` / `2B` ; aucune date de naissance déduite du NIR ; règle de
      concordance des traits (contradiction, trait absent, concordance).
- [ ] **Test d'intégration de bout en bout (règle 1b)** : un mail HPRIM à deux patients et deux PDF nommés est ingéré ;
      `GET patients/{id}/medical-documents` de chaque patient lit **son** document et **son** PDF, jamais celui de
      l'autre. Cas d'échec : deux résultats et un seul PDF non appariable → aucun document ne porte de PDF, la pièce
      reste au message. Vu rouge.
- [ ] **Test d'intégration** `POST patients/validate-ins` : un INS corse valide rend `IsControlKeyValid = true` et
      `BirthDate` vide ; un INS à clé fausse rend `IsControlKeyValid = false`. Vu rouge.
- [ ] **Test d'intégration de l'ingestion** : un CDA dont la clé INS est fausse, et un CDA dont la date de naissance
      contredit la fiche existante, ne sont pas rattachés et figurent dans la file « à intégrer » ; aucune fiche n'est
      créée. Cas nominal : clé valide et traits concordants → rattaché. Vu rouge.
- [ ] **Deux personnes sur la même boîte** (règle 14) : le délégataire intègre un document de la file ; le titulaire
      le relit dans la fiche ; la trace d'audit porte le délégataire (RPPS, nom, rôle) et le patient choisi.
- [ ] Tests de composant, vus rouges par mutation : fenêtre de rattachement mobile (réponse d'un autre document
      ignorée) ; confirmation d'identité avant envoi sans date déduite du NIR (web et mobile) ; date de naissance
      affichée sans décalage de fuseau (web et mobile).
- [ ] **Scénario e2e** `E2E-PATIENT-005` v1 ajouté à `Api/Mail/e2e/scenarios.yml`, mobile et angular requis : « un
      mail de laboratoire à deux patients range chaque compte rendu et son PDF dans la bonne fiche ». Le seed du banc
      porte un HPRIM à deux patients et deux PDF.
- [ ] Trou du filet : scénario `E2E-PATIENT-005` prouvé rouge sur le code non corrigé, ligne ajoutée dans
      `conventions/e2e.md`.
- [ ] Prévention (règle d'or) :
      - `conventions/csharp.md` : « une pièce jointe n'est associée à un document que si l'appariement est univoque » ;
        « jamais de date de naissance déduite du NIR » ; « un rattachement automatique exige une identité sûre, le
        doute va à la file à intégrer » ;
      - `conventions/angular.md` : « une réponse asynchrone se vérifie contre l'objet encore affiché avant d'être
        appliquée » ; « une date sans heure ne passe jamais par `new Date(chaîne)` ».
- [ ] Aucune INS, aucun nom de patient dans les logs ; `data-testid` sur chaque élément interactif ajouté.
- [ ] Build et tests verts : `HealthPlatform.Api.Mail.sln`, weda2 (`nx build weda2`, `nx test weda2`,
      `nx test mss-lib`), client-mobile (`npm run build`, `npm test -- --watch=false --browsers=ChromeHeadless`).
- [ ] client-angular : code-only, aucun commit.

## Manual Test Plan

1. Lancer le backend (`cd Api/Mail/src/AppHost && dotnet run`), weda2 (`cd Client/Angular/front && npm start`) et le
   mobile (`cd Client/Mobile && npm start`).
2. Injecter un mail de laboratoire HPRIM à deux patients, avec deux PDF nommés d'après chaque patient
   (`Tools/EmlFactory`, `--verify` avant injection ; `.hpm` seulement). Ouvrir chaque fiche (web, mobile) : chacune a
   son compte rendu et son PDF.
3. Injecter un HPRIM dont la date de naissance est écrite `AAAAMMJJ` (patient né en 2005) : la date affichée est
   juste.
4. Rédiger un message à un patient né en Corse (INS valide portant `2A`) : l'envoi n'est pas bloqué ; la confirmation
   d'identité ne montre pas de date inventée.
5. Injecter un CDA dont la clé INS est fausse : le document n'est rattaché à aucune fiche et figure dans « à
   intégrer ». L'intégrer à la main.
6. Mobile : ouvrir le rattachement d'un document, fermer aussitôt, ouvrir celui d'un autre document du même mail : les
   candidats affichés sont toujours ceux du document ouvert.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville / biologie médicale (réception des comptes rendus)
- **Vague Ségur** : V2 — intégration des comptes rendus au dossier patient
- **Exigences DSR honorées** : renforce l'identitovigilance (référentiel national d'identitovigilance, RNIV : INS et
  traits stricts) ; prolonge LGC.MDV.08 et 09 ; à confirmer dans le DSR du couloir médecin de ville
- **INS** : rattachement automatique seulement sur une INS NIR / NIA à clé valide et des traits concordants ; sinon
  intégration manuelle. Aucune date déduite du NIR. Aucune création de fiche depuis un rattachement
- **Authentification PS** : inchangée — PSC (e-CPS), eIDAS substantiel ; envoi vers Mon Espace Santé sous PSC
- **Habilitations** : personnes de la boîte sous verdict de l'opérateur (règle 14)
- **Interop CI-SIS** : CDA R2 (en-tête `recordTarget`, INS et OID) ; HPRIM (en-tête et `RES|`), lecture corrigée
- **Tracé PGSSI-S** : intégration manuelle imputée à la personne réelle, patient choisi ; `HealthDataAccess`,
  3 653 jours
- **Consentement patient** : non applicable (envoi vers Mon Espace Santé inchangé)
- **Référentiels métier** : OID INS (NIR `1.2.250.1.213.1.4.8`, NIA `1.2.250.1.213.1.4.9`), LOINC inchangé
- **Hébergement HDS** : oui — base de la boîte
- **AIPD / impact RGPD** : inchangée — aucune donnée nouvelle ; moins de rattachements erronés
