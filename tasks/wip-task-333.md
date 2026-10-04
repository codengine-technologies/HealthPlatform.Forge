# todo-task-333.md — Un mail n'est marqué « analysé » que si ses documents médicaux ont réellement pu être lus : fin des pertes silencieuses de comptes rendus

**Repos**: api-mail, interop-cda
**Dependencies**: — (aucune)
**Epic**: E009
**Single frontend**: true
**Priorité**: **2** — un incident technique (disque, répertoire de travail, archive supprimée entre écriture et lecture) peut faire enregistrer un mail **sans ses comptes rendus CDA, définitivement** : plus de document, plus de rattachement patient, plus de biologie, sans aucun signal.

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, **AUD-09** et **AUD-16**). Rappel : la ligne
> `MailContents` est le **marqueur d'enrichissement** — une ligne écrite à tort écarte le mail de toute
> analyse future (mémoire « MailContents = marqueur d'enrichissement », tasks 222/225/293).

## Ce qui est établi (develop @ `14d58398`)

**Repli de lecture (AUD-09, ouvert par `14d58398`)** — `ImapService.cs:3253-3292, 4573-4576, 4613-4621` :
depuis ce commit, toute lecture `WithContent` d'un mail « en-têtes seuls » passe par un repli qui
fetche le message, extrait les archives IHE-XDM, construit le DTO et **écrit `MailContents`**
(`mailRepository.AddNewMail`). Appelants : liste des noms de pièces jointes (`ServiceImplementation.cs:178`),
export PDF (`MailExportController.cs:109`), résumé IA (`EmailSummaryService.cs:52`), annule-et-remplace
(`MailCancellationService.cs:95`). Ce chemin **ne teste pas `HasTechnicalFailure`** (contrairement à
`ImapService.cs:2048` et `BackgroundEnrichmentProcessor.cs:130`) et **ne prend pas `LockEnrichPersistAsync`**
— course possible avec une Phase B d'enrichissement sur le même UID (`IX_MailContents_MailId` non unique).
Il coûte aussi un fetch complet et une analyse CDA pour une simple liste de noms.

**Panne hôte pendant l'extraction (AUD-16)** — `CdaParsingService.cs:40-90`, `interop/…/XDM.cs:27-140` :
`XDM.Load` attrape **toute** exception et rend `false` (disque plein pendant `ExtractToDirectory`, droits,
zip supprimé entre l'écriture et l'analyse) → `ParseIheXdmZip` rend `[]` → mail persisté avec sa ligne
de contenu et `HasMedicalDocuments = false`. task-293 ne classe comme technique que **l'écriture** du zip.
Aggravants : aucune borne de taille ni de ratio de décompression (bombe zip saturant le répertoire de
travail partagé par tous les praticiens) ; `IheXdmScratchDirectory.Sweep()` ne purge pas les
sous-répertoires `Root/{guid}/` ; avec plusieurs réplicas sur un hôte, le balayage au démarrage de l'un
peut supprimer le zip d'un autre entre écriture et lecture.

## Objective

Que le marqueur « analysé » ne soit posé **que si** les archives médicales du mail ont été lues sans
incident technique ; qu'un incident technique laisse le mail **à traiter** (et le signale) ; qu'une
lecture ne déclenche jamais d'écriture d'enrichissement hors des gardes et du verrou existants ; et
qu'une archive anormale ne puisse pas saturer l'hôte.

### Périmètre

1. **Repli de lecture** : soit il ne persiste plus rien (lecture pure, le contenu servi sans écrire le
   marqueur), soit il applique **exactement** la garde task-293 (`HasTechnicalFailure` → pas de
   persistance, indisponibilité 503) **et** prend le verrou de persistance d'enrichissement. Choix
   justifié par `/develop` ; la liste des noms de pièces jointes ne doit pas déclencher d'analyse CDA.
2. **`interop-cda`** : `XDM.Load` / `ParseIheXdmZip` distinguent **archive invalide** (contenu : le mail
   est analysé, sans document) de **panne hôte** (disque, droits, fichier absent : remontée comme
   échec technique). Publication NuGet et bump du consommateur.
3. **Bornes d'archive** : taille décompressée totale, nombre d'entrées et ratio de compression bornés
   (valeurs configurables, défauts documentés) ; dépassement → mail signalé, non marqué « analysé ».
4. **Répertoire de travail** : le balayage purge aussi les sous-répertoires d'extraction ; il ne
   supprime jamais une archive en cours d'usage par un autre réplica (âge minimal, ou répertoire propre au processus).

### Hors périmètre

- La libération des archives par la synchro de fond (task-334).
- Le rejeu des mails déjà marqués à tort (à évaluer après correctif : inventaire des mails porteurs
  d'un `IHE_XDM.ZIP` sans document — requête à rédiger dans le task file, reprise par une US dédiée si nécessaire).

## Definition of Done

- [ ] Build passes (0 errors) — `api-mail` et `interop-cda` ; Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] **Tests rouges d'abord** (log des runs rouges dans le task file) :
  - [ ] lecture `WithContent` d'un mail « en-têtes seuls » dont l'extraction échoue pour cause technique → sur le code actuel `MailContents` est écrit ; après correctif **aucune** écriture, le mail reste à enrichir
  - [ ] `XDM.Load` sur une panne hôte simulée (répertoire en lecture seule / fichier supprimé) → sur le code actuel `false` indistinct ; après correctif échec technique distinct
- [ ] Test : archive invalide (zip corrompu) → le mail est analysé sans document (comportement actuel conservé)
- [ ] Test : archive dépassant la borne de taille décompressée ou de ratio → refusée, mail non marqué, événement journalisé
- [ ] Test : liste des noms de pièces jointes d'un mail non enrichi → aucune analyse CDA déclenchée
- [ ] Test : repli de lecture concurrent d'une Phase B sur le même UID → une seule ligne de contenu
- [ ] Test : le balayage purge un sous-répertoire d'extraction orphelin et épargne une archive récente
- [ ] `interop-cda` publié via la CI, `api-mail` bumpé
- [ ] Non-régression task-293 : tests existants de classement technique verts ; test d'intégration `GetEmailAsync_WithFullContent_ShouldReturnCompleteEmailAsync` vert
- [ ] Aucun contenu CDA, INS ni nom de fichier patient dans les logs

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` (profil banc) ; seeder une boîte avec des mails porteurs d'`IHE_XDM.ZIP` réels (skill `loadtest-skill`).
2. Afficher la liste de la boîte sans ouvrir les mails (lignes « en-têtes seuls »).
3. Rendre le répertoire de travail IHE-XDM non inscriptible, puis ouvrir un de ces mails → **Attendu** : message « réessayez » (503), le mail n'est **pas** marqué analysé. Rétablir les droits, rouvrir → les documents CDA apparaissent et le patient est rattaché. Avant : le mail reste définitivement sans document.
4. Déposer (banc) un mail avec une archive anormalement volumineuse à la décompression → refus journalisé, les autres mails continuent d'être traités.
5. Vérifier qu'exporter en PDF un mail non enrichi ne crée pas de ligne d'enrichissement (requête SQL de contrôle fournie dans le task file).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville, biologie
- **Vague Ségur** : V2
- **Exigences DSR honorées** : intégration des documents CDA reçus par MSSanté — aucun document reçu ne doit être perdu sans signal
- **INS** : inchangé — l'INS est lue du CDA par le chemin existant ; la US évite qu'un document soit perdu avant cette lecture
- **Authentification PS** : PSC / e-CPS inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : IHE-XDM (`IHE_XDM.ZIP`), CDA r2 — lecture par `interop-cda` ; distinction archive invalide / panne hôte
- **Tracé PGSSI-S** : échec technique d'extraction et archive hors bornes journalisés (sans contenu ni nom patient) ; `MedicalDocumentProcess` inchangé
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — répertoire de travail des archives dans le périmètre HDS ; purge renforcée
- **AIPD / impact RGPD** : inchangé

## Branches

- `api-mail` (pushed) : fix/task-333-marqueur-analyse-garde-technique — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-333-marqueur-analyse-garde-technique (depuis `origin/develop` @ `9452245c`)
- `interop-cda` (pushed) : fix/task-333-marqueur-analyse-garde-technique — https://github.com/codengine-technologies/interop.cda.parser/tree/fix/task-333-marqueur-analyse-garde-technique (depuis `origin/develop` @ `8f40526`)

## Timings

*(généré par `tools/timing/report.sh --task task-333 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 27 s | — | — | — | — |
| **Total cycle** | | **27 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |
