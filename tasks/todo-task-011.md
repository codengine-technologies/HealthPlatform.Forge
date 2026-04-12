# todo-task-011.md — Indicateur document deja integre

**Repos**: client-blazor, client-angular
**Dependencies**: aucune
**Single frontend**: false

## Objectif

Le systeme doit informer le professionnel lorsqu'un document medical recu par MSSante
a deja ete rattache au dossier patient, afin d'eviter les doublons et de savoir d'un
coup d'oeil quels documents restent a traiter.

## Contexte

Le modele `MailMedicalDocument` possede un champ `EnrichmentStatus` qui trace l'etat
du traitement et un champ `PatientId` (nullable) qui indique le rattachement a un
patient. Le rattachement se fait via l'INS extrait du `METADATA.XML` de l'archive
IHE_XDM (conformement a ECO.2.1.2 du Ref#2).

Il manque un indicateur visuel dans l'interface pour que le professionnel distingue,
dans la liste des messages, ceux dont les documents ont deja ete traites de ceux qui
restent en attente.

## Critere d'integration

Un document est considere comme "integre" si `MailMedicalDocument.PatientId` est
non null (le document est rattache a un patient dans la base).

## Gherkin

See `tests/mss.mail.bdd.tests/Features/Mss/IndicateurDocumentIntegre.feature`

## Exigence Segur couverte

- LGC.MDV.06 — Informer que le document a deja ete integre

## References reglementaires

- REM Segur LGC.MDV.06
- Referentiel socle MSSante #2 v1.0.1 — ECO.2.1.2 (identification du patient par
  `patientId` dans METADATA.XML)

## Definition of Done

- [ ] Build passes (0 errors) sur `client-blazor`, `client-angular`
- [ ] Tests pass (0 failures)
- [ ] Indicateur visuel dans la liste des messages : distinguer les messages dont
  tous les documents sont rattaches (integres) de ceux qui ont des documents
  en attente
- [ ] Indicateur visuel par document dans le detail du message : rattache / en attente
- [ ] Critere d'integration : `MailMedicalDocument.PatientId` non null
- [ ] L'indicateur se met a jour dynamiquement apres un rattachement patient
- [ ] Blazor : indicateur dans la liste des messages + par document dans le detail
- [ ] Angular : indicateur dans la liste des messages + par document dans le detail
- [ ] >= 1 test d'integration par scenario Gherkin
- [ ] Aucune regression

## Manual Test Plan

- Lancer backend + Blazor + Angular
- Recevoir un message avec un document CDA rattache automatiquement a un patient
  (INS connu dans `MailPatient`)
  - Verifier dans la liste : indicateur "integre" (icone, badge vert, etc.)
  - Ouvrir le message → verifier l'indicateur sur le document
- Recevoir un message avec un document CDA dont le patient n'est pas identifie
  - Verifier dans la liste : indicateur "en attente" (icone, badge orange, etc.)
- Recevoir un message avec 2 documents : 1 rattache, 1 non rattache
  - Verifier dans le detail : indicateurs differents par document
  - Rattacher manuellement le 2e document → verifier que l'indicateur se met a jour
- Repeter sur les deux frontends (Blazor et Angular)
