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

## Timings

*(généré par `tools/timing/report.sh --task task-453 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 41 s | — | — | — | — |
| **Total cycle** | | **41 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |
