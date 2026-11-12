# todo-task-453.md — Un acquittement ne disparaît jamais

**Repos**: api-mail, client-angular, client-mobile
**Dependencies**: aucune
**Epic**: E024
**EpicTitle**: Messagerie premium : traiter, déléguer, boucler
**Priorité**: EPIC E024, demandée par l'humain le 2026-11-11. **À passer en premier** : c'est un défaut médico-légal, et
les tasks 454 à 463 ancrent leurs états de travail sur le modèle fixé ici.

> **Origine.** Analyse fonctionnelle du 2026-11-11 (`Docs/analyse-fonctionnelle-manques-messagerie-2026-11.md`) et
> lecture du code du même jour. `client-angular` et `client-mobile` figurent dans les Repos pour le scénario e2e du trou
> du filet ; aucun écran ne change.

## Ce qui est établi

Lecture du code au 2026-11-11 (`Api/Mail/src`) :

- La chaîne de clés étrangères est **en cascade de bout en bout** (`Infrastructure/Migrations/MailDb/20240101_SetupMigration.cs`) :
  - `Mails` → `MailMedicalDocuments` (`FK_MailMedicalDocuments_Mails`, `Rule.Cascade`, l.395) ;
  - `MailMedicalDocuments` → `BiologyAcks` (`FK_BiologyAcks_MailMedicalDocuments`, `Rule.Cascade`, l.612-615) ;
  - de même pour `MailTags`, `MailMedicalDocumentBiology` et `MailMedicalDocumentSummary`.
- Une ligne `Mails` est **supprimée puis recréée sous un nouveau `Id`** dans trois cas :
  - un déplacement fait **hors de la plateforme** (webmail de l'opérateur, autre client IMAP) : la synchro supprime les
    UID disparus (`MailRepository.DeleteMailsByUidsAsync`), puis ré-ingère le message dans son nouveau dossier ;
  - un **changement d'UIDVALIDITY** : `FolderRepository.SyncUidValidityAsync` purge le dossier ;
  - une suppression puis une restauration hors plateforme.
- Seul le déplacement fait **dans** la plateforme conserve l'`Id` (`MailRepository.RekeyMovedMailsAsync`).
- `BiologyAck` est pourtant **en ajout seul** : c'est la trace de la prise de connaissance d'un résultat. Après
  ré-ingestion, le même compte rendu revient « à acquitter », sans son historique. La trace d'audit (`audit_traces`,
  base commune) survit ; l'état visible du médecin, non.
- Le **rattachement manuel** d'un document à un patient (`MailMedicalDocument.ManualAttachedBy*`) est perdu de la même
  façon. Le rattachement automatique par INS se refait seul ; le rattachement manuel, non.

**Défaut plausible, à prouver d'abord par un test** : il n'a pas été vu en recette.

## Objective

Un acquittement de biologie et un rattachement manuel **survivent** à tout ce qui fait disparaître puis revenir un
message : déplacement hors plateforme, purge d'UIDVALIDITY, suppression puis restauration. Quand le même document
revient, il retrouve son historique d'acquittement, son état et son patient, avec les auteurs d'origine.

Règles :
- **Ancrage** : un acquittement et un rattachement manuel ne dépendent plus de la ligne `Mails`. Ils sont rattachés à
  une **identité stable du document** : le `Message-ID` du message plus l'identité du document (`DocumentId`/`SetId`
  et `Version` pour un CDA, `ContentFingerprint` pour un HPRIM), au choix de `/develop`, à justifier dans l'ADR.
- **Re-liaison** : quand un message ré-ingéré porte un document déjà connu, ses acquittements et son rattachement
  manuel sont **re-liés** au nouveau document, à l'identique : actions, notes, auteurs, horodatages.
- **Jamais de perte silencieuse** : un message supprimé pour de bon (corbeille vidée) ne détruit pas ses
  acquittements. Ils restent conservés, rattachés à l'identité du document, et invisibles tant que le document ne
  revient pas.
- **Rien d'inventé** : la re-liaison ne crée aucun acte. Si l'identité du document est ambiguë (deux documents
  candidats), aucune re-liaison n'est faite et l'évènement est journalisé (doctrine task-193 : dans le doute, ne pas
  rattacher).
- **Modèle commun** : cet ancrage est **le modèle obligatoire** des états de travail ajoutés par les tasks 454 à 463
  (traité, report, attribution, notes, suivis). L'ADR le dit.

### Hors périmètre

- Les étiquettes (`MailTags`) : elles se recalculent à la ré-ingestion.
- La réconciliation des drapeaux IMAP (lu, signalé) posés par un autre client : sujet distinct.

## Definition of Done

- [ ] **Preuve du défaut d'abord** : un test d'intégration rouge sur le code actuel. Message avec compte rendu de
      biologie, acquitté « Pris connaissance » puis « Résolu », déplacé directement en IMAP (hors plateforme), puis
      synchronisé : l'acquittement a disparu. Sortie rouge consignée dans le `## Develop log`.
- [ ] ADR `Docs/adr/ADR-2026-11-xx-ancrage-etats-de-travail.md` : clé d'identité du document retenue, re-liaison,
      cas ambigus, modèle imposé aux états de travail des tasks 454 à 463.
- [ ] Migration FluentMigrator : les clés étrangères des acquittements et du rattachement manuel ne sont plus en
      cascade vers `Mails` ; reprise des lignes existantes. Audit de migration (règle 7c) : pas d'opération fantôme,
      modèle EF (`MailDataContext.OnModelCreating`) identique à la migration.
- [ ] Tests unitaires de la re-liaison : document CDA identique, nouvelle version (`SetId` identique, `Version`
      supérieure : **pas** de re-liaison, c'est un nouveau document), HPRIM identique, deux candidats (aucune
      re-liaison).
- [ ] **Test d'intégration de bout en bout (règle 1b)** sur `GET api/v1/Mail/folders/{f}/emails/{ids}` après les trois
      chemins (déplacement IMAP direct, purge d'UIDVALIDITY, suppression puis restauration) : `LastBiologyAck` et
      `BiologyAckState` lus dans la réponse réelle, identiques à avant, avec l'auteur d'origine (RPPS, nom, rôle).
      Patient rattaché manuellement retrouvé. Cas d'échec : document ambigu, aucune re-liaison, état « à acquitter ».
      Vu rouge (premier point).
- [ ] **Deux personnes sur la même boîte** (règle 14) : un acquittement posé par le délégataire, re-lié après
      déplacement hors plateforme par le titulaire, garde le délégataire pour auteur.
- [ ] **Trou du filet** : scénario `E2E-BIO-004` v1 ajouté à `Api/Mail/e2e/scenarios.yml` (« un compte rendu acquitté
      puis déplacé depuis un autre client garde son acquittement »), mobile et angular requis, prouvé rouge sur le
      code non corrigé. Si le banc e2e ne sait pas déplacer un message hors plateforme : `questions/task-453.md`. Ligne
      ajoutée dans `conventions/e2e.md`.
- [ ] **Prévention (règle d'or)** : consigne dans `conventions/csharp.md` : « une trace ou un état métier (acquittement,
      rattachement manuel, état de travail) ne se rattache jamais en cascade à la ligne `Mails`, qui est un miroir
      IMAP jetable ».
- [ ] Aucune donnée de santé dans les logs de re-liaison (ni INS, ni contenu) : identifiants techniques seulement.
- [ ] Build et tests verts : `HealthPlatform.Api.Mail.sln`, weda2 (`nx build weda2`, `nx test weda2`,
      `nx test mss-lib`), client-mobile (`npm run build`, `npm test -- --watch=false --browsers=ChromeHeadless`).
- [ ] client-angular : code-only, aucun commit.

## Manual Test Plan

1. Lancer le backend sur la boîte de formation : `cd Api/Mail/src/AppHost && dotnet run`, puis weda2
   (`cd Client/Angular/front && npm start`).
2. Ouvrir un compte rendu de biologie, l'acquitter « Pris connaissance », avec la note « contrôle dans 1 mois ».
3. Depuis le webmail de l'opérateur (Mailiz formation), déplacer ce message dans un autre dossier.
4. Dans weda2, actualiser les dossiers et ouvrir le message dans son nouveau dossier : l'acquittement est là, avec la
   note, l'auteur et l'heure d'origine. La tuile « Bio à acquitter » n'a pas augmenté.
5. Recommencer avec un document rattaché à la main à un patient : le patient est toujours rattaché.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (LGC, biologie reçue)
- **Vague Ségur** : V2 — intégrité du suivi des comptes rendus de biologie
- **Exigences DSR honorées** : non applicable directement ; renforce l'imputabilité (PGSSI-S)
- **INS** : inchangé — la re-liaison ne lit ni n'écrit l'INS ; le rattachement manuel conservé reste celui choisi par le
  praticien
- **Authentification PS** : inchangée — PSC (e-CPS), niveau eIDAS substantiel
- **Habilitations** : inchangées — verdict de l'opérateur (règle 14)
- **Interop CI-SIS** : CDA R2 (`SetId`/`Version` du volet) et HPRIM (empreinte) comme identité du document
- **Tracé PGSSI-S** : nouvel acte système « re-liaison d'un acquittement » (et « re-liaison ambiguë écartée »), sans
  personne, famille `HealthDataAccess`, 3 653 jours
- **Consentement patient** : non applicable
- **Référentiels métier** : LOINC (inchangé)
- **Hébergement HDS** : oui — base de la boîte, environnement HDS de production
- **AIPD / impact RGPD** : inchangé — aucune donnée nouvelle, durée de conservation des acquittements inchangée

## Branches
- `api-mail` (pushed) : feat/task-453-un-acquittement-ne-disparait-jamais — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-453-un-acquittement-ne-disparait-jamais
- `client-mobile` (pushed) : feat/task-453-un-acquittement-ne-disparait-jamais — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-453-un-acquittement-ne-disparait-jamais
- `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` (snapshot au /start : `feature/nova-mss-weda-integration`) — humain gère branche, commit, push, PR TFS

## Develop log

- **Repos touchés** : `dtos-mss` (branche paresseuse, contrat d'audit), `api-mail`, `client-mobile`, `client-angular`
  (code-only).
- **DTOs publiés** : `HealthPlatform.Dtos.Mss` 588.0.0 → **591.0.0** (`AuditActionType.DocumentWorkStateRelinked = 70`,
  `DocumentWorkStateRelinkSkipped = 71`, actes système). Bump `api-mail` seul (`client-blazor` non listé : bump à faire
  quand il consommera ces membres).
- **Interop publié** : aucun changement.
- **Commits** :
  - dtos-mss : `5ad659d` feat(dto): audit actions for document work-state relink
  - api-mail : `aeee2ba2` chore(deps) bump 591.0.0 · `c163598c` fix(mail) ancrage + re-liaison · `5ab2414f` test(e2e)
    E2E-BIO-004, `message --move`, `--kind bio-hprim` · `bfb20d4c` refactor(mail) simplify pass
  - client-mobile : `8320106` test(mobile) E2E-BIO-004
  - client-angular (code-only, **non commité**, branche `feature/nova-mss-weda-integration`) :
    `front/e2e/mss-e2e/specs/functional.e2e.ts`, `front/e2e/mss-e2e/support/e2e-backend.ts`,
    `front/libs/mss/src/core/models/audit.model.ts`, `front/libs/mss/src/core/models/audit.model.spec.ts`
  - plan de contrôle : ADR, consignes `conventions/csharp.md` et `conventions/e2e.md`
- **Conception** (ADR `Docs/adr/ADR-2026-11-11-ancrage-etats-de-travail.md`) :
  - clé `DocumentAnchor` = `v1:` + SHA-256(`Message-ID` + saut de ligne + identité) ; identité = empreinte (HPRIM) ou
    `DocumentId|SetId|Version` (CDA) ; pas de clé pour un message de patient (`EMAIL`) ni sans `Message-ID` ;
  - `BiologyAcks.MedicalDocumentId` nullable, FK **SET NULL** (plus CASCADE) + `AnchorKey` ; nouvelle table
    `ManualPatientAttachments` (une ligne par clé, patient en CASCADE, document en SET NULL) ;
  - `DocumentWorkStateRelinker` : re-liaison à l'identique **à l'ingestion** (nouveau message et promotion d'un
    en-tête) **et après la purge** de `DeleteMailsByUidsAsync` (le message a pu être lu dans son nouveau dossier
    avant la purge de l'ancien) ; plusieurs documents de même clé → rien n'est re-relié, avertissement et trace ;
  - traces système après validation de la transaction ; `AuditService.Impute` laisse système un acte déclaré
    système par l'appelant (jamais imputé à la personne qui a ouvert le dossier) ;
  - migration `20261111120000_AnchorDocumentWorkStates` avec reprise (clé SQL identique à la clé C#).
- **Fait métier découvert** : un document **porteur d'INS** ne se rattache pas à la main (409 « its patient follows
  the reference identity »). Le rattachement manuel ne concerne donc que les documents sans INS (CDA « à intégrer »,
  HPRIM) ; les tests l'éprouvent sur ces deux cas.
- **Preuve du défaut d'abord (règle 1b)** — sur `aeee2ba2` (code d'avant, contrat bumpé seulement), les 8 tests
  d'intégration de `FolderOperationsEndToEndTests.WorkStateAnchoring` sont **rouges** :
  - déplacement IMAP direct (CDA « Pris connaissance » puis « Résolu ») : `Assert.NotNull() Failure: Value is null`
    sur `after.LastBiologyAck` (`AssertSameAcknowledgement`) ;
  - corbeille puis restauration, HPRIM : même assertion ; délégataire : `Expected ("99000004536", "Cyril",
    "DELEGUE", "Delegate") Actual (null, null, null, null)` ; rattachement manuel : `Expected <patientId> Actual null`
    sur `after.PatientId` ;
  - message détruit pour de bon, cas ambigu : `Assert.Single() Failure: The collection was empty` sur les
    acquittements en base (détruits en cascade) ;
  - UIDVALIDITY : rouge au harnais sur ce passage (ligne `MailFolders` absente), puis prouvé par mutation (M1).
- **Tests d'intégration de bout en bout** (`GET api/v1/mail/folders/{f}/emails/{uid}`, vraie pile, PostgreSQL, Dovecot,
  second client IMAP), tous verts après correctif :
  - `ACdaAcknowledgedThenMovedByAnotherClient_KeepsItsAcknowledgements` — deux actes re-reliés à l'identique (Id,
    action, note, instant, RPPS), trace système `DocumentWorkStateRelinked` sans personne ni INS ;
  - `AFolderPurgedOnAUidValidityChange_GetsItsAcknowledgementBack` ;
  - `AMessageDeletedThenRestoredByAnotherClient_GetsItsAcknowledgementBack` ;
  - `AMessageDestroyedForGood_KeepsItsAcknowledgementsUnseen_UntilTheSameMessageComesBack` ;
  - `AMessageReadInItsNewFolderBeforeItsOldRowIsPurged_GetsItsAcknowledgementAtThePurge` (ordre inverse) ;
  - `ACdaWithoutInsAttachedByHandThenMovedByAnotherClient_KeepsItsPatientAndItsAuthor` ;
  - `ADocumentDetachedByHandThenMovedByAnotherClient_ComesBackUnattached` (route `detach-patient`) ;
  - `AnHprimAcknowledgedAndAttachedByHandThenMovedByAnotherClient_KeepsBoth` ;
  - `WhenTheDocumentIdentityPointsToTwoDocuments_NothingIsRelinked_AndTheResultIsStillToAcknowledge` (cas d'échec :
    état « à acquitter », acte conservé orphelin, trace `DocumentWorkStateRelinkSkipped`) ;
  - `TheDelegatesAcknowledgement_RelinkedAfterTheHoldersMoveElsewhere_KeepsTheDelegateAsAuthor` (règle 14).
- **Migration (règle 7c)** : `AnchorDocumentWorkStatesMigrationTests` sur le coureur FluentMigrator de production
  (base neuve, lignes semées à la version précédente, montée) : clé SQL = `DocumentAnchor.Compute` (CDA, HPRIM ;
  `EMAIL` et sans `Message-ID` → null), acquittement repris avec sa clé, rattachement repris (délégataire),
  `confdeltype = 'n'` (SET NULL), suppression du `Mails` → acquittement et rattachement conservés, descente et
  remontée. Lecture de la migration : aucune opération fantôme ; `MailDataContext` déclare les mêmes FK
  (`SetNull`), index partiels et noms. FluentMigrator n'a pas de commande « pending changes » : l'équivalence modèle ↔
  migration est vérifiée par ces tests et par la lecture.
- **Preuves par mutation** (copie, mutation, exécution, restauration depuis la copie) :
  - M1 `RelinkWorkStatesAsync` neutralisée → rouges dont UIDVALIDITY (`AssertSameAcknowledgement`) ;
  - M2b garde d'ambiguïté (`keyCandidates.Count == 0`) → `WhenTheDocumentIdentity…` rouge sur
    `Assert.Null(copyDocument.LastBiologyAck)` ;
  - M3 ancrage du rattachement manuel neutralisé → `ACdaWithoutIns…` et `AnHprim…` rouges sur `after.PatientId` ;
  - M4 clé SQL (`'cda:'` → `'cdx:'`) → `TheBackfill_…` rouge (`Strings differ`) ;
  - M5 re-liaison à la purge neutralisée → `AMessageReadInItsNewFolderBeforeItsOldRow…` rouge
    (`AssertSameAcknowledgement`) ;
  - traces : sans service d'audit dans la fixture, `Assert.Single` des traces rouge (vu avant d'aligner
    `UseCaseFixture` sur la composition de production).
- **Tests unitaires** : `DocumentAnchorTests` (CDA identique, nouvelle version = autre clé, HPRIM identique par
  empreinte, autre message, pas de clé) ; `DocumentWorkStateRelinkerTests` (CDA identique re-relié à l'identique,
  nouvelle version : rien, HPRIM + rattachement manuel, deux candidats : rien, sans clé, acquittement encore relié
  jamais déplacé) ; `AuditServiceSystemActTests` ; contrat d'audit figé (70, 71) et rétention `HealthDataAccess`.
- **Trou du filet — E2E-BIO-004 v1** (mobile et angular requis) : catalogue d'abord, puis les deux suites. Outil :
  `message --move` et `--kind bio-hprim`. **Prouvé rouge** sur le backend sans re-liaison (mutation M6 dans
  `DocumentWorkStateRelinker`, équivalente au code d'avant pour ce que voit le médecin) : mobile et Angular rouges aux
  deux essais sur « la dernière action relue du serveur » (après rangement puis retour) ; **vert** sur le correctif
  (mobile 18,0 s, Angular 19,7 s, sans retry). Durcissements faits pendant la preuve : attente serveur de l'analyse
  du document (`enrich/sync` puis contenu) avant l'ouverture ; acquittement « Résolu » et message retiré en fin de
  parcours (la puce « Bio à acquitter » des autres parcours n'est pas touchée) ; sur weda2, l'état résolu se lit au
  titre du bandeau replié (`biology-ack-title`), sans pastille de statut. Ligne ajoutée dans « Trous du filet ».
- **Prévention (règle d'or)** : `conventions/csharp.md` → `etat-metier-hors-du-miroir-imap` ; `conventions/e2e.md` →
  ligne « Trous du filet » E2E-BIO-004.
- **Données de santé** : journaux de re-liaison = extrait de clé (11 caractères), identifiant de document, nombres ;
  ni INS, ni contenu, ni `Message-ID`. Traces d'audit sans INS ni nom de patient (assertées).
- **Outillage** : `client-angular` — `node_modules` en retard sur la branche de l'humain (TypeScript 5.9 installé
  pour `~6.0.3`, `@ngrx-toolkit/core` absent) : weda2 ne compilait plus pour le banc e2e. `npm ci` relancé (aucune
  opération git).
- **Local build / test** :
  - api-mail : build 0 erreur ; tests domain 221, infrastructure 749, application 4 197, api 1 376 verts ;
    integration 1 260 verts, **3 rouges pré-existants** « du jour » (`GetFolderTodayAsync_Inbox…`,
    `GetFolderNotSeenTodayAsync_Inbox…`, `FilterTodayEmailsShouldReturnOnlyToday…`), rouges aussi sur `develop`
    entre 00:00 et 02:00 (suite jouée vers 00:30, bascule UTC) — sans lien avec la task ;
  - client-mobile : `npm run build` vert, `npm test` 1 417/1 417 ; `tsc` de la suite e2e vert ;
  - client-angular : `tsc` de la suite e2e vert ; build/test weda2 laissés à `/lint-angular` (pipeline-aligné).
- **Passe qualité (/simplify)** — quatre revues (réutilisation, simplification, efficacité, altitude) :
  - appliqué (api-mail) : plus d'état mutable `_relinksAwaitingCommit` (les re-liaisons remontent par valeur et sont
    tracées après validation) ; **une seule requête** « clés en attente » au lieu de deux sur le chemin chaud de
    l'ingestion ; projection et boucle du relinker simplifiées (`ToLookup`, un seul constructeur de résultat) ;
    `FindAnchoredAsync` factorise l'ancrage et l'oubli du rattachement ; `DocumentAnchor.Short` dérivé du préfixe ;
    alias de test inutile retiré. Re-validé : build vert, suite complète identique (mêmes totaux, mêmes 3 rouges « du jour »).
  - écarté (hors qualité ou hors périmètre, à juger par `/review`) :
    - *altitude* : seule la purge `DeleteMailsByUidsAsync` re-relie ; les autres chemins de suppression
      (`PurgeMailsOfFoldersNotOnServerAsync`, renommage, `DeleteMailAsync`, rekey) ne le font pas — un état rendu
      orphelin par eux n'est re-relié qu'au **prochain** retour du même document. Piste générale : re-lier tous les
      orphelins en fin de passe de synchronisation ;
    - *altitude* : `IsSystemAct` posé par l'appelant plutôt qu'une surcharge `IAuditService.TraceSystem` (évite de
      casser les faux d'`IAuditService` existants) ; `IAuditService` optionnel dans `MailRepository` ;
    - *efficacité* : `FindAsync` du patient par rattachement ré-appliqué (cas rare), lecture séparée des clés avant
      purge, lecture de la clé à l'écriture d'un acquittement (action utilisateur) ;
    - *réutilisation* (tests) : réécriture d'entrée de zip proche de `TrappedXdmArchive`, harnais de rattachement
      proche de `HprimServer`, message HPRIM et création de dossier de l'outil e2e proches du seed.
  - client-mobile : diff = spec e2e, rien à simplifier ; dtos-mss : exclu (porteur de contrat).
- **DOD self-check** : preuve rouge ✓ · ADR ✓ · migration + audit 7c ✓ · unitaires de re-liaison ✓ · intégration 1b
  (trois chemins, auteur, patient, cas d'échec) ✓ · deux personnes ✓ · E2E-BIO-004 + ligne conventions ✓ · consigne
  csharp ✓ · aucune donnée de santé dans les journaux ✓ · builds/tests ✓ (3 rouges pré-existants) · Angular non
  commité ✓.
- **Next step** : `/sonar task-453`

## Sonar log

- Serveur : SonarQube 25.6.0 sur `localhost:9001` (conteneurs `sonarqube_db` puis `sonarqube` redémarrés, arrêtés
  depuis deux semaines) ; propriété `sonar.token` ; clé `healthplatform-api-mail`.
- **Phase 1 (new code de la task)** : ✓ — après correction, **aucune issue** sur les lignes écrites par task-453.
  - Itération 1 : 1 issue imputable à la task, **S3776** (`DocumentWorkStateRelinker.RelinkAsync`, complexité 16 > 15),
    corrigée en extrayant `RelinkKeyAsync` (`ffc49e23`). Tests du relinker, build et suite complète verts.
  - Itération 2 (re-analyse) : S3776 résolue ; plus aucune issue imputable.
  - Couverture new code des fichiers source de la task : `DocumentAnchor` 100 %, `MailRepository.WorkStates` 100 %,
    `BiologyAckRepository` 100 %, `BiologyAckService` 100 %, `PatientRepository` 98,8 %, `AuditService` 98,5 %,
    `MailRepository` 98,2 %, `DocumentWorkStateRelinker` 97,4 % (une ligne défensive : document disparu entre la
    lecture des candidats et la ré-application) ; `new_coverage` projet 97,8 % (cible 95 %).
  - **Issues restantes sur des fichiers touchés, toutes antérieures** (vérifié par `git blame`) : S103 ×5
    (`MailRepository` l.1374, 2729, 3710 et `PatientRepository` l.326 — task-405 ; `PatientRepository` l.56 —
    task-410), S4462 ×3 (`AuditService` l.214/235/257 — journal PGSSI-S), S138 (`LoadBulkContentLookupsAsync` — « Fix
    Sonar #77 »). Elles comptent dans la période « new code » du serveur (`PREVIOUS_VERSION`, depuis le 2026-04-17), qui
    englobe des tasks déjà mergées.
  - Hotspots « à revoir » de la période : 14, aucun sur un fichier de la task (`Dockerfile`, `BaseRepository`,
    scripts du banc de charge).
- **Phase 2 (legacy)** : non jouée (facultative, best-effort) — la dette restante est antérieure à la task.
- **Quality Gate (projet, new code)** : ERROR, inchangé dans sa cause : `new_violations` 98 et
  `new_security_hotspots_reviewed` 0 % portent sur du code antérieur à la task ; `new_coverage` 97,8 % OK,
  `new_duplicated_lines_density` 0,08 % OK.
- **Build / tests** : ✓ build Release 0 erreur ; domain 221, application 4 197, infrastructure 749, api 1 376,
  integration 1 263 (16 ignorés) — **tous verts** (passe de couverture de la re-analyse, hors de la fenêtre UTC des
  tests « du jour »).
- **Itérations** : 2 (Phase 1).
- **Prévention** : `conventions/csharp.md` — S3776, Occurrences 6 → 7 (task-453 : corps de boucle à deux issues, à
  extraire dès l'écriture).

### KPIs qualité (baseline → final)

La baseline est la dernière analyse présente sur le serveur (2026-10-28, `develop` de l'époque) : l'écart sur les
métriques projet inclut les tasks mergées depuis, pas seulement task-453.

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | ERROR | ERROR | → (causes antérieures) |
| New coverage | 98,1 % | 97,8 % | −0,3 pt |
| Bugs | 2 | 2 | 0 |
| Vulnerabilities | 0 | 2 | +2 (`tests/search-quality/campagne.py`, créé le 2026-11-10, hors task) |
| Security hotspots | 15 | 16 | +1 (hors fichiers de la task) |
| Code smells | 72 | 94 | +22 (aucune sur le code de la task) |
| Coverage (projet) | 98,0 % | 97,8 % | −0,2 pt |
| Duplication | 0,3 % | 0,3 % | 0 |
| Reliability / Security / Maintainability | D/A/A | D/D/A | sécurité D par les deux vulnérabilités du script Python |

## Lint log

- **client-angular** (code-only, branche `feature/nova-mss-weda-integration`, rien de commité) — 1 itération.
- Portée : les 4 fichiers de la task, par le contournement de task-367 (`npx eslint --format json` sur les fichiers,
  findings attribués à la task par `git diff -U0 HEAD`) : `nx affected` contre `origin/next` couvrirait toute la
  branche de l'humain.
- Baseline (findings imputables) : 2 erreurs — `prettier/prettier` (`audit.model.ts`, libellés d'audit trop longs),
  `jsdoc/require-param` (`createMessageElsewhere` sans `@param kind`) — et 2 avertissements `jsdoc/require-example`
  (helpers `waitForUidOtherThan`, `acknowledgeThenMoveBack`).
- Itération 1 : `eslint --fix` sur `audit.model.ts` (prettier) ; `@param kind` et trois `@example` renseignés à la
  main. **Final : 0 erreur** sur les fichiers de la task.
- Restant accepté : `max-lines` sur `e2e/mss-e2e/support/e2e-backend.ts` (fichier déjà à ~1 300 lignes avant la
  task) et les avertissements `jsdoc/require-example` antérieurs des deux fichiers e2e.
- Build / test : `nx build weda2` ✓ (30 s) ; `nx run-many -t test --projects=mss-lib,weda2 --skipNxCache` ✓
  (2 tâches réussies) ; `tsc` de la suite e2e Angular ✓.
- Règles corrigées à la main : `jsdoc/require-param` sur un paramètre ajouté à une fonction déjà documentée — déjà
  couvert par la doctrine JSDoc du dépôt (`front/CLAUDE.md`), pas de nouvelle entrée dans `conventions/angular.md`.
- Fichiers modifiés (non commités) : `front/libs/mss/src/core/models/audit.model.ts`,
  `front/e2e/mss-e2e/specs/functional.e2e.ts`, `front/e2e/mss-e2e/support/e2e-backend.ts`.

## Lint mobile log

- **Skip propre** : le diff `client-mobile` ne touche que `e2e/specs/functional.spec.ts` et
  `e2e/support/e2e-backend.ts`, hors de la portée de `ng lint` (`lintFilePatterns` : `src/**/*.ts`, `src/**/*.html`).
  Aucun fichier lintable modifié, aucun commit. La suite e2e est vérifiée par `tsc -p e2e/tsconfig.json` (vert), et
  le build (`npm run build`) et les tests (1 417/1 417) sont verts depuis `/develop`.

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail, client-mobile touchés | ♻️ réutilisée (verte task-453, 2026-11-12 01:39) | 61 verts, 0 flaky, 0 rouge | 0 s |
| angular | api-mail, client-angular touchés | ✅ verte (rejouée) | 78 verts, 3 flaky, 0 rouge, 1 quarantaine (verte) | 13 min (suite) |

- **Catalogue** : celui du **merge à venir** de la branche dans `origin/develop`, calculé sans toucher l'arbre
  (`git merge-tree --write-tree origin/develop HEAD`, sans conflit) : la branche de la task porte E2E-BIO-004, et
  `develop` porte depuis E2E-SEARCH-010 (task-446, PR #362 mergée après la création de la branche). La porte sur le
  seul catalogue de la branche relevait un `UnknownIdentifier [angular] E2E-SEARCH-010` — le test weda2 de task-446 —,
  levé par la synchronisation que `/review` fait par merge. **À `/review`** : la synchronisation de `develop` apporte
  le backend de task-446, que ces voies n'ont pas joué (le test weda2 E2E-SEARCH-010 est vert contre le backend de la
  task).
- **1er passage (rouge)** : parité angular E2E-SEARCH-004…009 (tests de task-445 non commités, perdus). Levée par
  l'humain : tests restaurés et commités sur TFS (commit « Task 446 » de `feature/nova-mss-weda-integration`).
  `questions/task-453.md` marquée résolue.
- **E2E-BIO-004 v1** (scénario de la task) : ✅ mobile, ✅ angular.
- Flaky (non bloquants) : E2E-SEARCH-001 [angular] (16), **E2E-LIVE-001 [angular] (4) — flaky récurrent, task de
  stabilisation à ouvrir**, **E2E-SESSION-004 [angular] (2) — récidive après le correctif du test de task-412**.
- Quarantaines : E2E-COMPOSE-002 [angular] (task-350), verte.
- Divergences ouvertes : 8 (mobile, recherche — task-450, task-451).
- Parcours touchés sans spec e2e modifié : aucun.
- Démontage : complet (ports libres, aucun conteneur e2e résiduel).

<details><summary>Verdict de la porte (gate --out)</summary>

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**Flaky (vert au second essai, non bloquant)** (3) :

- [angular] « recherche — composer ses critères puis lancer la recherche » (E2E-SEARCH-001)
- [angular] « session — après la déconnexion, la personne suivante n’arrive jamais dans la boîte de la précédente » (E2E-SESSION-004)
- [angular] « temps réel — un compte rendu arrive, notifié et affiché sans rechargement » (E2E-LIVE-001)

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
| E2E-BIO-004 | 1 | headless | Un compte rendu acquitté puis déplacé depuis un autre client garde son acquittement | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SETTINGS-004 | 1 | headless | Paramètres indisponibles : rien n'est écrasé | ✅ | — |
| E2E-SEARCH-001 | 2 | headless | Composer ses critères puis lancer la recherche | ⚠️ flaky | ✅ (v1) · divergence (task-450) |
| E2E-SEARCH-002 | 1 | headless | Un mot rare et accentué trouve le message qui le contient | ✅ | ✅ |
| E2E-SEARCH-003 | 1 | headless | Un numéro de dossier trouve son message, et un seul | ✅ | ✅ |
| E2E-SEARCH-004 | 1 | headless | Un nom de patient tapé sans accent ni majuscule trouve ses messages, puis les messages partiels | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-005 | 1 | headless | Un mot absent de la boîte affiche « Aucun résultat » | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-006 | 1 | headless | Plus de résultats qu'une page — « Voir plus » affiche la suite, jusqu'au dernier | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-007 | 1 | headless | Une recherche en échec affiche un message, et l'ancienne liste n'est plus affichée | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-009 | 1 | headless | Fermer la recherche rend le dossier à la même position ; retirer une étiquette relance sans elle | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-010 | 1 | headless | Reconnaître un résultat et ouvrir le dossier du patient | ✅ | ⛔ non joué · divergence (task-451) |
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
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ⚠️ flaky | ✅ |
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
| E2E-SESSION-004 | 1 | headless | Sur un appareil partagé, la personne suivante n'arrive jamais dans la boîte de la précédente | ⚠️ flaky | ✅ |
| E2E-AI-002 | 1 | headless | Un délégataire interroge l'assistant dans la boîte qu'il a ouverte | ✅ | ✅ |
| E2E-MAILBOX-007 | 1 | headless | Après un changement de boîte, l'onglet Patients ne montre plus rien de la précédente | ✅ | ✅ |
| E2E-ERROR-001 | 1 | headless | Une erreur affiche un code et une référence à transmettre au support | ✅ | ✅ |

**Divergences temporaires ouvertes** (8) :

- E2E-SEARCH-001 [mobile] — le mobile adopte le formulaire à un seul niveau avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-004 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-005 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-006 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-007 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-009 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-010 [mobile] — la lecture enrichie arrive sur le mobile avec la refonte mobile — résorbée par task-451
- E2E-SEARCH-008 [mobile] — les critères médicaux arrivent sur le mobile avec la refonte mobile — résorbée par task-451

**Parité : verte** — aucun écart entre le catalogue et les suites.

</details>

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/364 — label `awaiting-human-merge`
- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/63 — label `awaiting-human-merge`
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/123 — label `awaiting-human-merge`
- `client-angular` : code-only — humain gère commit/push TFS et ouverture PR. **À commiter avant le merge de la PR
  api-mail** (`test-angular-non-commite`). Fichiers modifiés, non commités sur `feature/nova-mss-weda-integration` :
  - `front/e2e/mss-e2e/specs/functional.e2e.ts`
  - `front/e2e/mss-e2e/support/e2e-backend.ts`
  - `front/libs/mss/src/core/models/audit.model.spec.ts`
  - `front/libs/mss/src/core/models/audit.model.ts`
- Validation de `/review` : api-mail synchronisé avec `develop` par merge (`7f8ddc82`, seul le catalogue e2e de
  task-446 arrive) ; build + suite complète **tous verts** (domain 221, infrastructure 749, application 4 197, api
  1 376, integration 1 263) ; dtos-mss build ✓ ; client-mobile build ✓, tests 1 417/1 417 ; client-angular
  `nx build weda2` ✓, tests `mss-lib` + `weda2` ✓ (branche de l'humain, après son commit « Task 446 »).

## Code Review Summary

**Verdict : APPROVED** — 0 bloquant, 6 suggestions.

### Preuve par test d'intégration (règle 1b)

| Comportement atteignable par un endpoint | Test d'intégration (vraie pile, PostgreSQL, Dovecot) | Preuve rouge |
|---|---|---|
| `GET …/folders/{f}/emails/{uid}` : acquittement re-relié après déplacement hors plateforme (actes, notes, auteurs, instants) | `ACdaAcknowledgedThenMovedByAnotherClient_KeepsItsAcknowledgements` | rouge sur le code d'avant |
| idem après purge UIDVALIDITY | `AFolderPurgedOnAUidValidityChange_GetsItsAcknowledgementBack` | mutation M1 |
| idem après corbeille puis restauration | `AMessageDeletedThenRestoredByAnotherClient_GetsItsAcknowledgementBack` | rouge sur le code d'avant |
| corbeille vidée : acte conservé invisible, re-relié au retour | `AMessageDestroyedForGood_…` | rouge sur le code d'avant |
| `GET /mail/folders/{f}` (purge) : re-liaison quand le nouveau dossier a été lu avant | `AMessageReadInItsNewFolderBeforeItsOldRowIsPurged_…` | mutation M5 |
| `POST …/attach-patient` : rattachement manuel ré-appliqué (CDA sans INS, HPRIM) | `ACdaWithoutInsAttachedByHand…`, `AnHprimAcknowledgedAndAttachedByHand…` | rouge sur le code d'avant + mutation M3 |
| `POST …/detach-patient` : le détachement n'est plus ré-appliqué | `ADocumentDetachedByHandThenMovedByAnotherClient_ComesBackUnattached` | mutation M7 (faite à la revue) |
| identité ambiguë : rien n'est re-relié, acte système « écarté » tracé | `WhenTheDocumentIdentityPointsToTwoDocuments_…` | mutation M2b |
| délégataire : l'auteur re-relié reste le délégataire (règle 14) | `TheDelegatesAcknowledgement_RelinkedAfterTheHoldersMoveElsewhere_…` | rouge sur le code d'avant |
| `POST …/biology-ack` : l'acquittement porte la clé de son document | couvert par tous les cas ci-dessus (acquittement posé par la route, relu après re-liaison) | idem |
| migration : clé SQL = clé C#, `SET NULL`, aller-retour | `AnchorDocumentWorkStatesMigrationTests` | mutation M4 |

### api-mail

- `Domain/Rules/DocumentAnchor.cs` — ✅ clé versionnée, hachée (ni `Message-ID` ni identifiant de document dans un journal) ; nouvelle version CDA = nouvelle clé.
- `Infrastructure/Repositories/MailDb/DocumentWorkStateRelinker.cs` — ✅ une seule requête dans le cas courant, re-liaison à l'identique, refus sur ambiguïté (doctrine task-193).
- `MailRepository.cs` / `MailRepository.WorkStates.cs` — ✅ re-liaison dans la transaction d'ingestion, trace après validation ; DTO resynchronisés (patient re-lié compris).
- `Migrations/MailDb/20261111120000_AnchorDocumentWorkStates.cs` — ✅ règle 7c : aucune opération fantôme, index partiels et FK identiques au modèle EF, reprise testée.
- `PatientRepository.cs` — ✅ ancrage et oubli du rattachement manuel.
- `AuditService.cs` — ✅ un acte déclaré système n'est jamais imputé à la personne de la requête.
- ⚠️ **Suggestion** — seule la purge `DeleteMailsByUidsAsync` relance la re-liaison ; les autres chemins de suppression (dossier supprimé ailleurs, renommage, `DeleteMailAsync`, rekey) laissent des orphelins re-reliés seulement au prochain retour du même document. Piste : re-lier tous les orphelins en fin de passe de synchronisation.
- ⚠️ **Suggestion** — la re-liaison après purge s'exécute après le `SaveChanges` de la suppression, hors transaction : une exception y remonterait à la synchronisation alors que la suppression est validée (les orphelins attendraient le prochain retour).
- ⚠️ **Suggestion** — `ManualPatientAttachments.AnchorKey` est unique : deux rattachements simultanés de deux copies du même message produiraient une violation d'unicité (500). Cas très rare ; un upsert SQL le fermerait.
- ⚠️ **Suggestion** — `IsSystemAct` devient à la fois une entrée et une sortie d'`Impute` ; une surcharge `IAuditService.TraceSystem` serait plus explicite (écartée pour ne pas casser les faux existants).
- ⚠️ **Suggestion** — la copie des quatre champs d'auteur (`ManualAttachedBy*` ↔ `AttachedBy*`) existe en trois endroits.
- ⚠️ **Suggestion** — l'écriture d'un acquittement lit la clé du document dans une requête de plus ; elle pourrait venir de `DocumentExistsAsync`.

### dtos-mss

- `AuditActionType.cs` — ✅ deux membres appendus avec valeurs explicites (70, 71) ; contrat figé par `AuditActionTypeContractTests` ; miroir TypeScript weda2 à jour ; rétention `HealthDataAccess`.

### client-mobile

- `e2e/specs/functional.spec.ts`, `e2e/support/e2e-backend.ts` — ✅ E2E-BIO-004 juge l'état relu du serveur (preuve positive avant le « pas À TRAITER »), attend l'analyse côté serveur, rend la boîte comme trouvée.

### client-angular (code-only, non commité)

- `audit.model.ts` / `.spec.ts` — ✅ miroir à l'identique ; `functional.e2e.ts` / `e2e-backend.ts` — ✅ E2E-BIO-004, état résolu lu au titre du bandeau replié.

### Données de santé

Aucune dans les journaux de re-liaison (extrait de clé, identifiants techniques) ni dans les traces d'audit système (INS et nom du patient vides, assertés).

## Timings

*(généré par `tools/timing/report.sh --task task-453 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 41 s | — | — | — | — |
| /develop | ok | 2 h 01 min | 21 (3 min 54 s) | 19 (19 min 34 s) | — | dtos-mss 1B/0T, api-mail 19B/18T, client-mobile 1B/1T, contrat 591, ancrage + re-liaison, E2E-BIO-004 rouge puis vert |
| /sonar | ok | 29 min 53 s | 3 (1 min 38 s) | 11 (17 min 27 s) | 4 (5 min 30 s) | 2 itération(s), api-mail 3B/11T, S3776 corrigée, aucune issue imputable |
| /lint-angular | ok | 7 min 08 s | 1 (47 s) | 1 (2 min 05 s) | — | 1 itération(s), client-angular 1B/1T, 0 erreur sur les fichiers de la task |
| /lint-mobile | skipped | 14 s | — | — | — | diff e2e uniquement, hors portée de ng lint |
| /e2e | ok | 17 min 18 s | — | — | — | e2e ×7 (38 min 57 s), 2e passage : mobile réutilisée, angular 78 verts, porte verte sur le catalogue du merge |
| /review | ok | 15 min 21 s | 5 (2 min 21 s) | 3 (9 min 24 s) | — | api-mail 2B/1T, dtos-mss 1B/0T, client-mobile 1B/1T, client-angular 1B/1T, APPROVED, PR api-mail #364, dtos #63, mobile #123 |
| **Total cycle** | | **3 h 12 min** | **30 (8 min 41 s)** | **34 (48 min 32 s)** | **4 (5 min 30 s)** | |

Autres commandes mesurées : lint ×3 (1 min 41 s), nuget-wait ×1 (24 s), restore ×3 (2 min 15 s)
