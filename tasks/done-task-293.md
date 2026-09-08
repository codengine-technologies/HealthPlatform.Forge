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

## Branches
- `api-mail` (pushed) : fix/task-293-ihe-xdm-scratch-recreate — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-293-ihe-xdm-scratch-recreate
- `dtos-mss` (pushed, auto-included) : fix/task-293-ihe-xdm-scratch-recreate — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/fix/task-293-ihe-xdm-scratch-recreate

## Timings

*(généré par `tools/timing/report.sh --task task-293 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 7.6 s | — | — | — | — |
| /develop | ok | 17 min 44 s | 5 (28 s) | 1 (1 min 26 s) | — | api-mail 5B/1T |
| /sonar | ok | 9 min 14 s | 3 (30 s) | 10 (5 min 46 s) | 2 (52 s) | 2 itération(s), api-mail 3B/10T |
| /lint-angular | skipped | 0.6 s | — | — | — | repo/écrans non touchés (task api-mail uniquement) |
| /lint-mobile | skipped | 0.5 s | — | — | — | repo/écrans non touchés (task api-mail uniquement) |
| /verify-visual | skipped | 0.5 s | — | — | — | repo/écrans non touchés (task api-mail uniquement) |
| /review | ok | 3 min 51 s | 2 (7.9 s) | 1 (1 min 28 s) | — | api-mail 2B/1T |
| /tech-writer | ok | 31 s | — | — | — | — |
| **Total cycle** | | **31 min 31 s** | **10 (1 min 06 s)** | **12 (8 min 41 s)** | **2 (52 s)** | |

## Develop log

- Repos touched : api-mail (dtos-mss : branche créée, aucun commit — aucun changement de contrat)
- DTOs published : no DTO change
- Interop published : no interop change
- Commits :
  - api-mail : 3381c8b fix(cda): un répertoire de travail supprimé ne tue plus le traitement des documents, et un échec technique n'est plus un succès (task-293)
  - api-mail : 75f920a refactor(cda): simplify pass (/simplify) — task-293
- Local build / test : ✓ build 0 erreur ; 167 + 484 + 2332 + 823 unitaires verts, intégration 460 verts / 16 skips / **5 rouges pré-existants hors périmètre** (filtres « aujourd'hui », frontière de minuit locale/UTC, cf. task-292 — aucun fichier concerné dans le diff).
- Décisions d'implémentation :
  - **Recréation à la demande** : `IheXdmScratchDirectory.CreateFile` rattrape `DirectoryNotFoundException`, recrée par `EnsureCreated` (mêmes restrictions 0700 que task-185) et rejoue **une** fois — recréation sur échec, aucun appel système ajouté sur le chemin nominal.
  - **Échec technique ≠ succès** : `IheXdmScratchSet` décompose `FailedCount` en `TechnicalFailureCount` (scratch_unavailable, io — le message **n'est pas persisté**, il reste éligible) et `InvalidArchiveCount` (propriété du message, stocké sans ce document). Classification : `DirectoryNotFoundException` → scratch_unavailable ; `FormatException` / `InvalidDataException` / `ParseException` → invalid_archive ; tout le reste → io (défaut sûr).
  - **Réponse `enrich/sync`** : `EnrichEmailsAsync` persiste le reste du lot puis lève `UnavailableException` (« N message(s) sur M restent à traiter ») → **503 `ProblemDetails`** (règle 12), plus jamais un 200 muet. Le chemin d'arrière-plan (`BackgroundEnrichmentProcessor`) applique la même règle « non persisté, reste à traiter ».
  - **Observabilité** : compteur `mssante_ihe_xdm_extraction_failures_total{cause}` ; log `Error` **dédoublonné** pour les causes techniques (une ligne par minute et par réplica, `Interlocked`, les suivantes en Debug).
- Passe qualité (/simplify) :
  - Applied & committed : api-mail : 2 files (75f920a) — recréation sur échec seulement, throttle renommé, tag calculé une fois, classification par défaut technique, avertissement doublonné rétrogradé, doc alignée.
  - Skipped (noted) : allocation paresseuse de la liste des échecs techniques (micro) ; factorisation du « skip » entre chemin synchrone et arrière-plan (types différents) ; réutilisation d'`ISyncProgressNotificationThrottle` (clé par praticien, `TimeProvider` — surdimensionné pour un instant statique) ; harnais d'intégration partagé avec `EnrichmentPartialBatchFailureTests` (helpers privés) ; `CapturingLogger` partagé (arrive avec task-292).
  - Skipped (contract/excluded) : dtos-mss
- DOD self-check : 8/9 items vérifiables satisfaits (build, tests, recréation après suppression, restrictions conservées, échec technique non marqué enrichi + distinct d'une archive invalide, intégration lot de 3 recréé + racine non inscriptible → 503 et message pendant, compteur par cause + log dédoublonné avec capture sérialisée, aucune donnée de santé dans les logs ajoutés, `DovecotBenchSmokeTests` vert). L'item « répertoire rendu non inscriptible » est simulé par une racine occupée par un fichier (portable, même classe d'échec I/O) plutôt que par `icacls`.
- Next step : /sonar task-293

## Sonar log
- Phase 1 (new code) : ✓ Quality Gate OK, 0 finding new-code dès la première analyse (post-develop), new_coverage = 87,9 % → 88,1 % après 1 test de couverture (`BackgroundEnrichmentProcessor` : branche « échec technique → message pendant », 28,6 % → couvert)
- Phase 1 — Issues fixées : 0 (rien à fixer)
- Phase 1 — Tests ajoutés : 1 (`PersistEnrichedBatchAsync_TechnicalExtractionFailure_LeavesTheMailPendingAndPersistsTheOthers`)
- Phase 1 — Hotspots new-code : 0
- Phase 2 (legacy) : itérations 0 / 5 — skippée : baseline déjà aux cibles dures (0 bug, 0 vuln, A/A/A), 59 smells legacy hors périmètre
- Itérations d'analyse : 2
- Build / tests : ✓ green (5 échecs pré-existants de frontière de minuit, cf. Develop log — hors périmètre)
- Commits : 6fbc10d test(sonar/new)

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 87,9 % | 88,1 % | +0,2 pt |
| New-code issues | 0 | 0 | → |
| Bugs | 0 | 0 | → |
| Vulnerabilities | 0 | 0 | → |
| Security hotspots | 3 (legacy) | 3 | → |
| Code smells | 59 | 59 | → |
| Coverage (projet) | 88,1 % | 88,1 % | → |
| Duplication | 0,4 % | 0,4 % | → |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

## Lint log
- /lint-angular : ⤍ skipped — `client-angular` non listé dans **Repos** (les 2 `environment.ts` modifiés dans `Client/Angular` préexistent au run, branche humaine `feature/nova-rewriting-mss`).

## Lint mobile log
- /lint-mobile : ⤍ skipped — `client-mobile` non listé dans **Repos**, `Client/Mobile` sur `develop`, arbre propre.

## Visual verify log
- /verify-visual : ⤍ skipped — aucun écran `client-mobile` touché.

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/226 — label `awaiting-human-merge`
- `dtos-mss` : aucun commit sur `fix/task-293-ihe-xdm-scratch-recreate` (pas de changement de contrat) — pas de PR

## Code Review Summary
- **APPROVED** (relecture indépendante, 0 bloquant). Vérifié : rejeu unique sur `DirectoryNotFoundException` avec chemin régénéré ; classification sûre par défaut ; throttle `Interlocked` sans double Error sous concurrence ; `UnavailableException` levée après le `finally` (pas de double dispose) ; message 503 sans UID/sujet/chemin ; symétrie du chemin d'arrière-plan ; tests déterministes (recréation, restrictions, classification, dédoublonnage, compteur, intégration PostgreSQL bout en bout, propagation contrôleur).
- Suggestion appliquée (`32f01a1`) : une `OperationCanceledException` pendant l'extraction laisse le message à traiter sans alimenter le compteur ni le log Error.
- Suggestion consignée (suivi) : throttle du log Error par cause (`scratch_unavailable` vs `io`) au lieu d'un instant partagé — un second défaut d'hôte dans la même minute n'est visible que par le compteur.
- Build 0 erreur, 3 807 tests unitaires verts, 460 tests d'intégration verts (5 flakes pré-existants de frontière de minuit, hors périmètre) ; Sonar QG OK, 0 finding new-code, new_coverage 88,1 %.
