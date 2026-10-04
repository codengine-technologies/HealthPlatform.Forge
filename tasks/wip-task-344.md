# todo-task-344.md — Un mail ouvert sur deux appareils à la fois n'est analysé qu'une fois : fin des comptes rendus en double dans le dossier patient

**Repos**: api-mail
**Dependencies**: — (aucune)
**Epic**: E011
**Single frontend**: true
**Priorité**: **2** — deux appareils du même praticien, servis par deux réplicas, qui ouvrent le même mail non encore analysé produisent **deux fois** son contenu, ses documents médicaux et ses résultats de biologie ; le dossier patient montre alors des comptes rendus en double.

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, **AUD-18 b**). Issue du découpage de l'ancienne task-336,
> validé par l'humain le 2026-09-27 (task-336 : boîte suivie par le flux ; task-343 : backplane et conversations ;
> task-344 : ce fichier).

## Ce qui est établi (develop @ `14d58398`)

- `MailClientSessionManager.cs:456-473` : la promotion d'une ligne « en-têtes seuls » est sérialisée par un
  `SemaphoreSlim` **local au processus** (`enrich:{email}:{folder}`) — deux réplicas ne se voient pas.
- `MailRepository.UpdateExistingMailWithContentAsync` (`:574-660`) : ajoute la ligne `MailContents`, les documents
  médicaux et la biologie ; aucun jeton de concurrence.
- `MailDataContext.cs:166` : `IX_MailContents_MailId` est un index **non unique** — la base ne refuse pas deux lignes
  de contenu pour un même mail.
- Rappel : la ligne `MailContents` est le **marqueur d'enrichissement** (mémoire, tasks 222/225/293) — en avoir deux
  ne fait pas qu'afficher un doublon, cela double aussi les documents rattachés au patient.
- Un **verrou distribué Redis** existe déjà pour le fetch (`ImapService.FetchMissingUidsWithLocksAsync`, ~`:2787-2832`),
  opportuniste et correctement libéré (jugé sain par l'audit).

## Objective

Qu'un mail ne puisse être promu (contenu, documents, biologie) **qu'une seule fois**, quel que soit le nombre
d'appareils et de réplicas qui l'ouvrent en même temps — garanti par la base, et sans travail inutile.

### Périmètre

1. **Garantie en base** : contrainte **unique** sur `MailContents(MailId)`. Le perdant de la course reçoit une
   violation d'unicité (23505), traitée comme « déjà promu » : aucune erreur rendue au praticien, le contenu
   existant est servi.
2. **Atomicité** — condition de la garantie : contenu, documents et biologie de la promotion sont écrits dans **une
   seule transaction**, sinon le perdant laisserait ses documents alors que son contenu est refusé. `/develop`
   **vérifie d'abord** le comportement actuel de `UpdateExistingMailWithContentAsync` et le consigne dans le task file.
3. **Économie** : avant de fetcher et d'analyser, la promotion prend un verrou distribué par (boîte, dossier, UID)
   en réutilisant le mécanisme du fetch — le second réplica n'effectue ni le fetch IMAP ni l'analyse CDA. Le verrou
   n'est **pas** la garantie (il peut expirer) : la contrainte l'est.
4. **Migration** (bases praticien, migrées à la demande) : d'abord **dédoublonner** les `MailContents` existants
   (conserver la ligne la plus ancienne, et ses documents ; supprimer les doublons et leurs documents / biologie
   rattachés, en préservant les accusés biologiques posés), puis créer l'index unique. Requête d'inventaire des
   doublons fournie dans le task file, exécutée avant et après sur une base de banc.

### Hors périmètre

- La diffusion des événements entre réplicas (task-343) et la boîte suivie par le flux (task-336).
- Les doublons de **fiches patient** pour une même identité (task-191) — sujet distinct.

## Definition of Done

- [ ] Build passes (0 errors) — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` ; Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Comportement transactionnel actuel de la promotion **consigné** dans le task file avant correctif
- [ ] **Test rouge d'abord** (intégration Postgres, log du run rouge dans le task file) : deux promotions **concurrentes** de la même ligne « en-têtes seuls » par deux contextes indépendants (simulant deux réplicas) → sur le code actuel **deux** lignes de contenu et des documents en double ; après correctif **une** ligne et un seul jeu de documents
- [ ] Test : le perdant de la course ne rend aucune erreur et sert le contenu existant
- [ ] Test : échec en milieu de promotion → **rien** n'est écrit (ni contenu, ni documents, ni biologie)
- [ ] Test : le second réplica, verrou tenu, ne déclenche ni fetch IMAP ni analyse CDA
- [ ] Migration auditée selon la **règle 7c** : fichier lu, aucune opération fantôme, companion / snapshot présents, « has pending changes » vide
- [ ] Test de migration : base avec doublons existants → dédoublonnée (ligne la plus ancienne conservée, accusés biologiques préservés), index unique créé
- [ ] Non-régression : tests d'enrichissement existants (task-079, task-228, task-293) verts
- [ ] Aucune INS, contenu CDA ni corps de mail dans les logs

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` (5 réplicas) ; seeder une boîte avec des mails porteurs d'`IHE_XDM.ZIP` (skill `loadtest-skill`).
2. Afficher la liste de la boîte sur mobile **et** sur Blazor sans ouvrir les mails.
3. Ouvrir **au même moment** le même mail non encore analysé sur les deux appareils → le compte rendu apparaît **une seule fois** dans le dossier patient. Avant : deux fois.
4. Requête d'inventaire des doublons (fournie dans le task file) sur la base du praticien de test → 0 doublon.
5. Sur une base de banc contenant des doublons historiques, lancer l'application (migration à la demande) → doublons résorbés, accusés biologiques conservés.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville, biologie
- **Vague Ségur** : V2
- **Exigences DSR honorées** : intégration des documents CDA reçus par MSSanté — un document reçu apparaît une seule fois dans le dossier patient
- **INS** : inchangé — les rattachements patient existants sont conservés ; la déduplication ne modifie aucune identité
- **Authentification PS** : PSC / e-CPS inchangée
- **Habilitations** : inchangées — opérations limitées à la base du praticien
- **Interop CI-SIS** : CDA r2 / IHE-XDM via `interop-cda` (chemin existant, non modifié)
- **Tracé PGSSI-S** : `MedicalDocumentProcess` tracé une fois par document effectivement intégré ; suppressions de doublons par la migration journalisées (nombre, sans contenu)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement inchangé
- **AIPD / impact RGPD** : inchangé — suppression de copies en double de données déjà détenues

## Branches
- `api-mail` (pushed) : feat/task-344-promotion-unique-mail — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-344-promotion-unique-mail
- `dtos-mss` : aucune branche — créée paresseusement par `/develop` seulement si un contrat bouge

## Timings

*(généré par `tools/timing/report.sh --task task-344 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 16 s | — | — | — | — |
| **Total cycle** | | **16 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |
