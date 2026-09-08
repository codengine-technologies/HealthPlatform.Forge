# todo-task-293.md — Un répertoire de travail supprimé tue le traitement des documents CDA jusqu'au redémarrage, en silence pour le médecin

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true
**Priorité**: **2** — robustesse. Une classe d'incident de production
**silencieuse** (HTTP 200, documents jamais constitués), déclenchable par un
simple nettoyage de fichiers temporaires. Correctif à risque nul.

> **Origine** : campagne de charge du 2026-09-08, premier lancement du tir 1000
> (`Docs/audits/api-mail-loadtest-campagne-post-lot-20260908.md`, finding
> **F-SCRATCH-1**). Cause **mesurée** dans Prometheus et Seq, localisée dans le
> code ; auteur de la suppression non attribué.

## Objective

Que la perte du répertoire de travail des archives IHE-XDM soit **sans effet**
sur le traitement des documents : le répertoire est recréé à la demande, et si
le traitement échoue malgré tout, le médecin (et l'exploitation) le **voient**.

### Ce qui a été mesuré

- 16h38 → 17h02 : documents CDA créés normalement (~800 par minute en chauffe).
- 17h02 : le répertoire `%TEMP%\mss-ihe-xdm` disparaît (acteur externe non
  identifié : aucune autre session, aucun test en cours, Storage Sense non
  configuré ; un fichier `.tmp` de 1,26 Mo apparaît dans `%TEMP%` à la même
  minute).
- 17h03 → 17h10 (arrêt du tir) : **0 document créé**, ~**900
  `DirectoryNotFoundException` par minute** —
  `IheXdmScratchDirectory.CreateFile()` (`src/Application/Helpers/IheXdmScratch.cs:73`),
  appelé depuis `IheXdmProcessingService.ExtractIheXdmZipsAsync` ; log
  `Error extracting IHE-XDM ZIP for UID={UID}` en `Error`.
- Pendant tout cet intervalle, `POST …/emails/enrich/sync` répond **200** : le
  médecin voit un traitement « réussi », son dossier patient ne se constitue
  pas, et rien ne le lui dit.

**Mécanique établie (lecture du code).** `IheXdmScratchDirectory` est un
singleton (`task-185`) qui crée le répertoire **une seule fois**, à sa
construction (`EnsureCreated()`), et dont le `Sweep()` de démarrage ne fait
que supprimer des fichiers résiduels — il ne recrée rien. Toute suppression
externe du répertoire pendant la vie du processus rend l'extraction
définitivement inopérante jusqu'au redémarrage de **chaque** réplica. Un
nettoyage de `%TEMP%` par un outil système, un opérateur ou un script de
maintenance suffit à provoquer l'incident en production.

### Contenu attendu

1. **Recréation à la demande.** `CreateFile()` garantit l'existence du
   répertoire avant d'ouvrir le fichier (ou rattrape
   `DirectoryNotFoundException` par une recréation suivie d'**un seul**
   rejeu). Le coût d'un `Directory.Exists`/`CreateDirectory` par extraction
   est négligeable devant le téléchargement IMAP qui précède ; s'il est jugé
   non nul, une recréation sur échec seulement est acceptable.
2. **Les permissions restrictives de `task-185` sont conservées** à la
   recréation (répertoire et fichiers accessibles au seul compte du service —
   les archives contiennent des documents de santé en clair, le temps de
   l'extraction).
3. **Un échec d'extraction n'est plus un succès.** Quand l'extraction d'une
   archive échoue pour une cause **technique** (répertoire, disque plein, droits),
   par opposition à une archive **invalide** (déjà traitée comme telle), la
   réponse du traitement le dit : le message n'est **pas** marqué comme enrichi
   (il reste éligible à un nouveau traitement), et le résultat renvoyé au
   client distingue « traité », « archive invalide » et « échec technique,
   à rejouer ». La forme exacte de cette distinction revient à `/develop`, dans
   le respect de la règle 12 (erreurs typées, `ProblemDetails`).
4. **L'incident s'observe.** Un compteur d'échecs d'extraction par cause
   (`scratch_unavailable`, `io`, `invalid_archive`) et un log de niveau
   `Error` **dédoublonné** (une ligne par minute et par réplica quand la cause
   est le répertoire, pas 900) : 900 lignes identiques par minute ont noyé
   le signal utile le 08/09.

### Hors périmètre (explicite)

- Identifier **qui** a supprimé le répertoire sur le poste de banc — hors
  produit. La garde du banc (recréation + horodatage) reste en place côté
  outillage jusqu'à la livraison de cette US.
- Déplacer le scratch hors de `%TEMP%` (répertoire dédié à l'application) —
  décision d'infrastructure, non requise ici : la recréation à la demande
  suffit, quel que soit l'emplacement.

## Definition of Done

- [ ] Build passes on api-mail (0 errors)
- [ ] Tests pass (0 failures)
- [ ] Test unitaire : répertoire supprimé **après** la construction du
      singleton → `CreateFile()` réussit (répertoire recréé) — le cas exact du
      08/09
- [ ] Test unitaire : le répertoire recréé porte les mêmes restrictions d'accès
      que celui créé au démarrage (`task-185`)
- [ ] Test unitaire : échec technique d'extraction → le message n'est **pas**
      marqué enrichi et le résultat du lot le classe « échec technique », distinct
      d'une archive invalide
- [ ] Test d'intégration `enrich/sync` : lot de 3 UIDs avec répertoire supprimé
      juste avant → 3 documents constitués (recréation) ; et, répertoire rendu
      non inscriptible → réponse qui expose l'échec technique en `ProblemDetails`
      ou en statut par UID, jamais un 200 muet (rule 1b : happy path + 1 mode
      d'échec)
- [ ] Compteur d'échecs d'extraction par cause exposé, log `Error` dédoublonné
      (test de capture de métriques, classe sérialisée — `task-291`)
- [ ] Aucune donnée de santé en clair dans les logs ajoutés (ni chemin de
      fichier contenant un identifiant patient, ni contenu CDA — le chemin
      `…\mss-ihe-xdm\<guid>.zip` est acceptable)
- [ ] `tests/mss.mail.integration.tests/LoadTest/DovecotBenchSmokeTests.cs`
      toujours vert (le chemin d'extraction est celui qu'il verrouille)

## Manual Test Plan

- **Lancer le backend** : `cd Api/Mail && dotnet run --project src/AppHost --launch-profile https-load-test`
  puis seed 5 boîtes / 10 messages (skill `loadtest-skill`, étape 2).
- **Nominal** : `POST /api/v1/mail/folders/INBOX/emails/enrich/sync` avec
  `[1,2,3]` pour `loadtest-1` → Seq `[CdaParsingService] Parsing completed` ×3,
  `GET …/emails/1` → `hasMedicalDocuments: true`.
- **Reproduire l'incident** : supprimer `%LOCALAPPDATA%\Temp\mss-ihe-xdm`
  **sans redémarrer**, puis enrichir `[4,5,6]`.
  - **Avant la US** : 200 en ~30 ms, Seq `Error extracting IHE-XDM ZIP` ×3,
    `hasMedicalDocuments: false` — le défaut.
  - **Après la US** : le répertoire réapparaît, 3 documents constitués, aucun
    `Error`.
- **Échec technique visible** : rendre le répertoire non inscriptible
  (`icacls … /deny`) puis enrichir `[7,8]` → réponse qui dit l'échec technique
  (jamais 200 muet), les UIDs 7 et 8 restent traitables une fois les droits
  rétablis (rejouer → documents constitués).
- **Observabilité** : Prometheus, compteur d'échecs d'extraction par cause ;
  Seq : **une** ligne `Error` par minute et par réplica pendant l'indisponibilité,
  pas une par message.
- **Rendre le banc** (étape 6 du skill).
- **Données de test** : `JEUX_TESTS_FULL` uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors exigence DSR directe — robustesse du traitement des
  documents reçus par MSSanté (volet réception CI-SIS déjà couvert)
- **Exigences DSR honorées** : non applicable — aucune exigence DSR ne décrit le
  cycle de vie d'un répertoire temporaire ; la US protège la constitution du
  dossier documentaire, qui sert les exigences de réception
- **INS** : non applicable directement — l'extraction précède le parsing CDA
  qui porte l'INS ; la US ne touche ni à la lecture ni à la qualification de
  l'INS
- **Authentification PS** : inchangée (PSC, traitement déclenché en session PS)
- **Habilitations** : inchangées
- **Interop CI-SIS** : le contenu extrait est un CDA r2 traité par
  `interop-cda` + Schematron **en aval**, inchangé
- **Tracé PGSSI-S** : l'échec technique d'extraction devient un évènement
  journalisé (trace `MedicalDocumentProcess` avec `Success=false` et cause,
  journal `task-186`), conservation de la famille « traitement de document »
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun (LOINC/CIM-10 lus en aval, inchangés)
- **Hébergement HDS** : oui — le scratch contient des documents de santé en
  clair le temps de l'extraction (`task-185`) ; la recréation conserve les
  permissions restrictives, aucun nouvel emplacement
- **AIPD / impact RGPD** : inchangée — aucun traitement ni flux nouveau
