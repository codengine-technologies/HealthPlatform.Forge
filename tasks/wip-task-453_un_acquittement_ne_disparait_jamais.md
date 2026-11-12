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

## Timings

*(généré par `tools/timing/report.sh --task task-453 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 41 s | — | — | — | — |
| /develop | ok | 2 h 01 min | 21 (3 min 54 s) | 19 (19 min 34 s) | — | dtos-mss 1B/0T, api-mail 19B/18T, client-mobile 1B/1T, contrat 591, ancrage + re-liaison, E2E-BIO-004 rouge puis vert |
| /sonar | ok | 29 min 53 s | 3 (1 min 38 s) | 11 (17 min 27 s) | 4 (5 min 30 s) | 2 itération(s), api-mail 3B/11T, S3776 corrigée, aucune issue imputable |
| **Total cycle** | | **2 h 32 min** | **24 (5 min 33 s)** | **30 (37 min 01 s)** | **4 (5 min 30 s)** | |

Autres commandes mesurées : nuget-wait ×1 (24 s), restore ×3 (2 min 15 s)
