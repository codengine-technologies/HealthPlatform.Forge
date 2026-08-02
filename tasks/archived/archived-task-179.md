# todo-task-179.md — Identité d'un mail sans UIDVALIDITY : un message peut être servi avec le contenu d'un autre

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axe sessions IMAP).
> Finding vérifié sur pièces par le PO — voir « Preuve » ci-dessous.

## Objective

Rendre l'identité locale d'un message MSSanté **fiable dans le temps**. Un mail
est aujourd'hui identifié par `(FolderPath, Uid)` — sans la **UIDVALIDITY** du
dossier IMAP. Or les UID ne sont uniques que **pour une UIDVALIDITY donnée** :
c'est exactement le rôle de ce marqueur dans IMAP (RFC 3501) que de signaler
« les UID que tu connais ne sont plus valides ».

Conséquence : après recréation d'un dossier de même nom, ou après un changement de
UIDVALIDITY côté serveur MSSanté (restauration ou migration de boîte), les lectures
— faites **base d'abord** — renvoient le contenu d'**anciens** messages sous les
UID de **nouveaux** messages. Le praticien ouvre un compte-rendu et lit celui d'un
autre patient.

**US backend-only (justification)** : identité et synchronisation côté serveur.
Les frontends consomment l'API inchangée.

### Preuve (état actuel du code)

- `src/Infrastructure/Migrations/20240101_SetupMigration.cs:108` — l'index unique
  qui porte l'identité d'un mail est `IX_Mails_FolderPath_Uid_Unique` sur
  `(FolderPath, Uid)` : **aucune** composante UIDVALIDITY.
- **`UidValidity` est du code mort.** Les trois seules occurrences dans tout
  `src/` :
  - `src/Domain/Entities/MailFolder.cs:16` — la propriété est déclarée ;
  - `src/Infrastructure/Migrations/20240101_SetupMigration.cs:512` — la colonne
    existe, défaut `0` ;
  - `src/Infrastructure/Repository/FolderRepository.cs:52` — une recopie
    `existing.UidValidity = folder.UidValidity`.
  **Aucune lecture, nulle part.** La valeur n'est jamais confrontée à celle du
  serveur, donc un changement d'UIDVALIDITY est structurellement indétectable.
- `src/Infrastructure/Repository/FolderRepository.cs:85-95` —
  `DeleteFolderByPathAsync` supprime **uniquement** la ligne `MailFolders` ; les
  lignes `Mails` du dossier (avec sujets, corps et documents CDA) subsistent, et
  restent adressables par la chaîne de chemin.
- Lectures **base d'abord** qui font confiance à cette clé :
  `src/Application/Services/Implementation/ImapService.cs:2651`
  (« First try to get from database »), le lookup par lot à `:1223`, et
  `GetEmailContentAsync` à `:1668`.
- La synchronisation cimente l'état : `missingUids = imapUidSet.Except(existingUids)`
  (`src/Application/Services/Implementation/BackgroundSyncService.cs:264`) est vide
  quand les UID « existent déjà » — rien n'est jamais re-téléchargé.

### Contenu attendu

1. **UIDVALIDITY réellement lue et persistée** : à chaque ouverture de dossier,
   comparer l'UIDVALIDITY du serveur à celle en base.
2. **Invalidation sur changement** : si l'UIDVALIDITY diffère de la valeur connue,
   les UID mémorisés pour ce dossier ne sont plus valides — les données locales du
   dossier doivent être invalidées et re-synchronisées, jamais servies telles
   quelles. C'est le comportement prescrit par IMAP.
3. **Suppression de dossier = purge des mails du dossier** : `DeleteFolderByPathAsync`
   et la réconciliation de dossiers ne doivent pas laisser de mails orphelins
   adressables. Vérifier la cohérence avec la règle métier existante « Corbeille ⇒
   cascade du lien patient et des documents rattachés » : une purge doit suivre les
   mêmes cascades, sans sur-supprimer.
4. **Identité complète** : faire porter l'identité locale d'un mail par une clé
   incluant l'UIDVALIDITY (ou tout mécanisme équivalent garantissant qu'un UID
   d'une génération ne peut pas résoudre vers une autre). Toute évolution de
   schéma passe par une migration FluentMigrator (le repo n'utilise **pas** les
   migrations EF Core) et par l'audit de migration de la règle 7c.
5. **Cohérence des chemins de lecture** : les trois lectures base-d'abord doivent
   toutes appliquer la nouvelle identité — pas de chemin résiduel qui résout sur
   `(FolderPath, Uid)` seul.

### Hors scope

- Refonte du modèle de synchronisation ou du pooling IMAP (autres tasks du lot).
- Renommage de dossier IMAP (`RENAME`) — à traiter séparément s'il s'avère
  présenter la même faiblesse d'adressage par chemin.

## Definition of Done

- [x] Build passes (0 errors) — 0 erreur / 0 avertissement, build normal
- [x] Tests pass (0 failures, hors flaky pré-existants documentés) — 3073 unitaires
      + 298 d'intégration, 0 échec
- [x] Test unitaire : UIDVALIDITY du serveur **différente** de la valeur connue ⇒
      les UID locaux du dossier sont invalidés (aucun contenu local servi pour ces
      UID) — ce test doit échouer sur le code actuel, le vérifier explicitement
- [x] Test unitaire : UIDVALIDITY **inchangée** ⇒ le cache local est utilisé
      normalement (pas de re-synchronisation inutile — pas de sur-correction)
- [x] Test unitaire : suppression d'un dossier ⇒ aucun mail du dossier ne reste
      adressable ; les cascades (lien patient, documents) respectent la règle
      Corbeille existante
- [x] Test d'intégration **anti-collision** : dossier `Analyses` peuplé, supprimé,
      recréé avec les mêmes UID côté serveur ⇒ les lectures renvoient les **nouveaux**
      messages, jamais les anciens contenus
- [x] Test d'intégration : après changement d'UIDVALIDITY, la synchronisation
      re-télécharge bien les messages (le calcul de UID manquants ne les considère
      plus comme déjà présents)
- [x] Les trois chemins de lecture base-d'abord appliquent la nouvelle identité
      (vérifié par test ou revue explicite listée dans la task)
- [x] Migration FluentMigrator relue selon la règle 7c (pas d'opération fantôme,
      pas de perte de données non voulue), et stratégie de reprise documentée pour
      les bases existantes — voir la réserve : la migration n'est exercée par aucun test
- [x] Aucune donnée de santé en clair dans les logs — les évènements de génération
      ne portent qu'un compte, jamais un chemin de dossier, un sujet ni un identifiant

**Ajouté hors DOD, exigé par les constats du 2026-08-02** : la détection doit être
**effective en runtime**, pas seulement testable — vérifié en base réelle
(0 dossier sans génération, `UidNext` conforme à l'annonce serveur). Le DOD
d'origine ne le demandait pas, et c'est précisément ce qui a permis à un socle
inerte de passer tous ses contrôles.

## Manual Test Plan

1. Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
2. **Scénario collision (le cœur du bug)** — données de test anonymisées :
   a. Créer un dossier `Analyses` dans la boîte MSSanté de test, y déposer 3
      messages identifiables (sujets distincts, un avec CDA) ; synchroniser ;
      vérifier l'affichage correct.
   b. Supprimer le dossier `Analyses` via l'API, puis le **recréer** avec le même
      nom et y déposer 3 **nouveaux** messages différents ; synchroniser.
   c. **Attendu** : la liste et l'ouverture de chaque message affichent les
      **nouveaux** contenus. Avant correctif, les anciens contenus (dont les
      documents CDA d'un autre patient) réapparaissent sous les nouveaux UID.
3. **Scénario UIDVALIDITY serveur** : provoquer un changement d'UIDVALIDITY sur la
   boîte de test (restauration de boîte, ou serveur de test permettant de la
   forcer) → à la synchronisation suivante, les messages sont re-téléchargés et
   les contenus affichés correspondent au serveur.
4. **Non-régression** : sur une boîte stable (UIDVALIDITY inchangée), vérifier
   qu'une synchronisation incrémentale ne re-télécharge **pas** tout (les
   performances et le volume de trafic IMAP restent comparables à l'existant).
5. Vérifier qu'après suppression d'un dossier, aucun mail de ce dossier n'est
   accessible par l'API, et que les liens patients associés ont suivi la règle
   Corbeille.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — volet MSSanté
- **Exigences DSR honorées** : correctif de conformité — intégrité et exactitude
  des documents de santé restitués au praticien (PGSSI-S intégrité)
- **INS** : non applicable en tant que traitement nouveau — mais l'erreur fait
  apparaître le document d'un patient sous l'identité d'un autre message, ce qui
  relève de l'identito-vigilance au sens large (le rattachement patient lui-même
  est traité par task-176)
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : documents CDA r2 concernés en tant que **contenu servi** ;
  parsing et validation Schematron via `interop-cda` inchangés
- **Tracé PGSSI-S** : journaliser la détection d'un changement d'UIDVALIDITY et
  l'invalidation de cache associée (évènement technique, sans donnée de santé) —
  c'est une information d'exploitation précieuse
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement HDS cible de `api-mail`
- **AIPD / impact RGPD** : **à mettre à jour** — risque d'inexactitude des données
  (art. 5.1.d) et de divulgation d'un document au titre d'un autre message.
  Qualifier avec le humain si des dossiers de production ont pu être affectés
  (dossiers supprimés puis recréés, boîtes restaurées).

## Branches
- `api-mail` (pushed) : fix/task-179-uidvalidity-identity — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-179-uidvalidity-identity
- `dtos-mss` (pushed, auto-inclus) : fix/task-179-uidvalidity-identity — aucun contrat attendu (US backend-only)

## Develop log — ARRÊT EN COURS, task laissée en `wip-*`

**La task n'est pas terminée.** Le socle est poussé sur la branche (`975d085`),
mais **la détection n'est pas branchée** : sans elle, la migration livrerait un
changement de schéma sans le mécanisme qui le justifie. Je préfère le dire que
le laisser croire.

### Livré et validé (build 0 erreur / 0 avertissement, suite complète verte)

1. **Migration FluentMigrator** `20260802_AddMailUidValidity` — colonne
   `Mails.UidValidity`, index unique `(FolderPath, UidValidity, Uid)` remplaçant
   `(FolderPath, Uid)`. L'ancien index est **remplacé et non complété** : il
   interdirait la coexistence de deux générations du même dossier. Le `Down()`
   peut légitimement échouer sur une base ayant connu un changement — assumé et
   documenté, plutôt qu'un `Down` qui choisirait en silence quelles lignes
   sacrifier.
2. **Stratégie de reprise** (exigence de DOD) : `UidValidity = 0` vaut
   « génération inconnue ». Elle est **adoptée sans purge** à la première
   ouverture, et les mails existants sont estampillés. Traiter le 0 comme un
   changement aurait purgé **toutes** les boîtes au premier démarrage après
   déploiement — la colonne `MailFolders.UidValidity` n'ayant jamais été
   alimentée, elle vaut 0 partout.
3. **`SyncUidValidityAsync`** → `Unknown` / `Unchanged` / `Adopted` /
   `Invalidated`. La purge et la mise à jour de la génération sont **atomiques**
   (même `SaveChangesAsync`), donc pas de fenêtre mono-processus incohérente.
4. **`DeleteFolderByPathAsync` purge désormais les mails du dossier.** Documents
   médicaux et rattachement patient suivent par la cascade FK existante
   (`FK_MailMedicalDocuments_Mails`, `OnDelete(Cascade)`) — même effet que la
   règle Corbeille.
5. **Estampillage à l'insertion** depuis la ligne dossier. Le DTO ne porte pas la
   génération : **choix délibéré**, il évite un changement de contrat `dtos-mss`
   pour une donnée purement locale.
6. **Prédicat de génération** sur `GetMailAsync` et `GetMailsByUidsAsync` — les
   deux lectures base-d'abord derrière les trois sites nommés par l'énoncé
   (`ImapService` lecture unitaire, lookup par lot, `GetEmailContentAsync`).
   Justifié même avec la purge atomique : il couvre la course **multi-pods**
   (un pod insérant un mail de l'ancienne génération pendant qu'un autre purge).
7. **Garde-fou `UpsertFolderAsync`** — piège trouvé en chemin : la méthode
   écrasait `UidValidity` avec la valeur du DTO, soit **0**, à chaque
   synchronisation. Sans ce garde-fou, la génération adoptée était perdue au
   cycle suivant et la détection n'aurait plus jamais rien détecté.

### Ce qui reste — le cœur du correctif

- **Brancher `SyncUidValidityAsync` sur l'ouverture de dossier.** Blocage
  identifié : `FolderDto` ne porte pas la UIDVALIDITY, et le point de
  synchronisation (`BackgroundSyncService.PersistFolderMetadataAsync`, juste
  avant le diff d'UID) ne dispose que du DTO, pas de l'`IMailFolder` MailKit qui
  l'expose. **Trois voies**, à trancher :
  1. ajouter `UidValidity` à `FolderDto` — additif et non cassant, mais c'est un
     changement de contrat `dtos-mss` (publication NuGet + bump des
     consommateurs), alors que l'US est déclarée backend-only ;
  2. transporter la valeur hors DTO (paramètre dédié depuis `ImapFolderService`,
     qui a l'`IMailFolder` en main) ;
  3. relire la UIDVALIDITY par un `STATUS` dédié au point de synchronisation —
     un aller-retour IMAP de plus par dossier et par cycle.
  La voie 2 semble la meilleure (aucun contrat touché, aucun coût réseau) mais
  demande d'être vérifiée sur le chemin d'arrière-plan, qui ouvre ses dossiers
  ailleurs.
- **Toute la suite de tests du DOD**, dont le test qui doit être **constaté RED**
  et les deux tests d'intégration (anti-collision dossier recréé, re-téléchargement
  après changement).
- **Audit de migration règle 7c** sur une base réelle.
- `/sonar`, `/review`, `/tech-writer`.

### Découverte utile hors task

`--artifacts-path` (contournement des verrous MSB3021) fait **échouer**
`SecretLiteralScanTests.TrackedSources_ContainNoSecretShapedLiteral`, livré par
task-177 : l'assembly sort du repo et son `RepoRoot()` rend `null`. Vert en build
normal. Ce n'est pas une régression, mais le contournement et ce test sont
incompatibles — à savoir avant de conclure à un échec.

## Develop log — voie 1 retenue, détection branchée (`e7a0705`)

**Arbitrage humain du 2026-08-02** : ajouter `UidValidity` à `FolderDto`, avec le
changement de contrat que cela implique.

- **`dtos-mss`** : champ ajouté (`fc86f75`), **publié en 372.0.0** par la CI
  (le workflow publie sur toute branche, version = `github.run_number`).
- **`api-mail`** : `Directory.Packages.props` bumpé 343.0.0 → **372.0.0**.
  `client-blazor` **non bumpé** — il n'est pas dans les `**Repos**:` de l'US et
  l'ajout est additif, donc 343.0.0 continue de fonctionner. À bumper lors de sa
  prochaine intervention.
- **`ImapHelper`** renseigne la valeur depuis l'`IMailFolder` MailKit, dans les
  deux fabriques (`CreateFolderDtoFromStatus` et `MapToMailFolderEntity`).
- **`BackgroundSyncService.ApplyServerUidValidityAsync`** confronte **avant** le
  diff d'UID. L'ordre n'est pas cosmétique : `missingUids` se calcule par
  différence avec ce que la base contient **encore**, donc invalider après aurait
  produit une purge suivie d'aucun re-téléchargement.
- Une UIDVALIDITY serveur à **0** (dossier non ouvert, statut servi depuis le
  cache) est **ignorée** plutôt qu'adoptée : l'adopter écraserait la génération
  connue par « inconnue ».

**8 tests, tous verts** (`UidValidityIdentityTests`) : invalidation, non-régression
sur boîte stable, adoption sans purge des bases d'avant migration, dossier
inconnu, purge à la suppression de dossier, course multi-pods sur les **deux**
lectures base-d'abord, et le garde-fou d'upsert. Suite : infrastructure 401 verts,
application 1 914, api 638.

### Ce qui reste avant la PR

> ⚠️ **Section périmée**, conservée pour la trace. Les deux tests d'intégration
> réclamés ici **existaient déjà** au moment où elle a été écrite
> (`ARecreatedFolderServesTheNewMessagesNeverTheOldContent` et
> `AfterInvalidationTheSyncSeesEveryUidAsMissingAgain`). Le taux d'ignorés
> alarmant (128) était l'environnement, pas la suite : elle tourne à
> **298 ✓ / 16 ignorés** AppHost arrêté. Voir « le socle était inerte ».

- ~~**Test d'intégration anti-collision**~~ — déjà présent.
- ~~**Re-téléchargement après changement**~~ — déjà présent.
- **Audit de migration règle 7c** — fait, voir la section dédiée.
- `/sonar`, `/review` (PR), `/tech-writer`.

### Rappel d'outillage

`--artifacts-path` fait échouer `SecretLiteralScanTests` (livré par task-177) :
l'assembly sort du repo et son `RepoRoot()` rend `null`. Vert en build normal.
Ce n'est pas une régression.

## Develop log — le socle était inerte, corrigé (`f72fe5f`, 2026-08-02 soir)

**Vérification en base réelle** (`u_899700622675_vmm_c9e6ca8101453ceff74a38098a6223c9`,
boîte de formation) après le déploiement du socle : migration appliquée, index
`IX_Mails_FolderPath_UidValidity_Uid_Unique` en place — et **`UidValidity = 0`
sur les 7 dossiers et les 10 mails**, alors que Seq montrait le serveur annoncer
`UidNext=4880` pour INBOX. La détection ne s'était jamais déclenchée.

### Cinq défauts, une seule famille : une génération qui n'atteint pas son point d'usage

| # | Défaut | Correction |
|---|---|---|
| 1 | `BackgroundImapService.GetFolderAsync` construisait son `FolderDto` **à la main, sans `UidValidity`**, alors qu'il a l'`IMailFolder` ouvert. C'est **le** DTO que consomme `ApplyServerUidValidityAsync`, qui ignore un 0 ⇒ `SyncUidValidityAsync` **jamais appelée** | fabrique partagée `CreateFolderDtoFromStatus` |
| 2 | Le listing ne demandait **ni `UIDNEXT` ni `UIDVALIDITY`** dans ses `StatusItems`, et `MapToFolderDto` ne les portait pas | constante `ImapHelper.FolderListingStatusItems` sur les 3 sites de listing |
| 3 | `UpsertFolderAsync` écrasait `UidNext` avec 0 — le garde-fou task-179 ne couvrait que `UidValidity` | garde-fou symétrique |
| 4 | `RekeyMovedMailsAsync` déplaçait `FolderPath` + `Uid` en laissant la génération **de la source** | estampillage de la génération cible, abstention si inconnue, collision jugée sur l'identité complète, + balayage des fantômes |
| 5 | `LastSyncedAt` écrite en **heure locale** ici et en **UTC** dans `UpdateFolderStatsAsync` | UTC **sans `Kind`** (motif `MailRepository.NormalizeUtc`) |

**Le défaut n°1 explique tout le reste** : task-179 avait instrumenté
`CreateFolderDtoFromStatus` (chemin HTTP interactif) et `MapToMailFolderEntity`,
mais pas la **troisième fabrique**, inline dans le chemin d'arrière-plan — le
seul qui alimente la détection. Les 8 tests unitaires étaient verts parce qu'ils
appelaient `SyncUidValidityAsync` directement ou fabriquaient un DTO déjà
porteur d'une valeur. **Aucun ne traversait le chemin réel.**

### Le fantôme — pourquoi le défaut n°4 est le plus grave

Constaté sur un glisser-déposer INBOX → `Demo/Demo2` : la ligne portait la
génération d'INBOX dans `Demo/Demo2`. Une telle ligne est **écartée par les
lectures** (prédicat de génération) **et comptée comme présente par le diff de
synchronisation** (`GetExistingUidsAsync`, qui ne filtre pas). Protégée d'un
côté, invisible de l'autre : le vrai message n'est **jamais** re-téléchargé.

Le balayage (`ReconcileForeignGenerationMailsAsync`) tourne désormais **y compris
à génération inchangée** — seul cas où le dégât déjà en base se répare. Une ligne
à **0 est adoptée, pas purgée** : « on ne savait pas » n'est pas « ça vient
d'ailleurs », et purger coûterait le rattachement patient et les documents.

### Régression introduite puis corrigée dans la même passe — à connaître

Le correctif n°5 a d'abord été écrit `DateTime.UtcNow` **brut**. Npgsql
**refuse** un `Kind=Utc` dans un `timestamp without time zone` : toute
persistance de dossier levait, donc **tout le listing tombait en 500**. Six
tests d'intégration rouges, et l'humain l'a rencontré en direct sur son
instance (Seq, 16:59). Causalité vérifiée en remisant le diff : baseline verte
16/16.

**Les tests unitaires ne pouvaient pas l'attraper** — provider InMemory, qui
accepte n'importe quel `Kind`. C'est la suite d'intégration sur PostgreSQL réel
qui l'a vue. À retenir avant de considérer qu'une passe unitaire verte suffit
sur ce repo.

Effet de bord utile : `UpdateFolderStatsAsync` écrivait **déjà** `UtcNow` brut
dans la même colonne. Mine posée, jamais rencontrée parce que la méthode **n'a
aucun appelant**. Corrigée au passage.

### Tests

**11 ajoutés** — 8 unitaires, **3 d'intégration sur PostgreSQL réel** ;
**6 constatés RED** avant correctif, dont deux échouant sur exactement le
symptôme observé en base (`Expected: 4880 / Actual: 0`).

**5 tests task-094 adaptés** : leur fixture ne créait aucune ligne
`MailFolders`, état devenu non représentatif depuis que l'identité d'un mail
inclut la génération de son dossier. En production, la cible d'un déplacement
est toujours un dossier que le listing a persisté — c'est lui qui alimente le
sélecteur de l'interface.

| Suite | Résultat |
|---|---|
| `domain` | 102 ✓ |
| `application` | 1925 ✓ |
| `infrastructure` | 407 ✓ |
| `api` | 639 ✓ (`SecretLiteralScanTests` inclus) |
| **`integration` (PostgreSQL réel)** | **298 ✓ / 0 ✗ / 16 ignorés** |

Build **0 erreur / 0 avertissement**, build normal (pas d'`--artifacts-path`).

### Vérification de bout en bout en base

Après correctif, base recréée et repeuplée par l'application :

| Contrôle | Avant | Après |
|---|---|---|
| Dossiers sans génération | 7 / 7 | **0 / 7** |
| Dossiers sans `UidNext` | 7 / 7 | **0 / 7** |
| Générations distinctes | 1 (le zéro) | **7** |
| Mails en génération inconnue | 10 / 10 | **0 / 10** |
| Mails divergents de leur dossier | — | **0** |

`INBOX.UidNext = 4880` correspond exactement à la valeur annoncée par le serveur
dans Seq. Les générations (1735566573…599) sont horodatées et croissantes dans
l'ordre de création des boîtes — ce ne sont pas des valeurs fabriquées localement.

### Risque résiduel — non traité, à arbitrer

Les trois requêtes du diff de synchronisation — `GetExistingUidsAsync`,
`GetEnrichedUidsAsync`, `DeleteMailsByUidsAsync` — **ne filtrent pas par
génération**, alors que les lectures le font. C'est cette asymétrie qui
transforme n'importe quelle ligne périmée en fantôme **permanent** plutôt qu'en
anomalie transitoire. Le balayage colmate la conséquence à chaque cycle ; il ne
supprime pas la cause. Correction de fond = toucher le cœur du diff, avec un
risque réel de re-téléchargement massif ⇒ **task dédiée**.

### Audit des autres écrivains de la génération

Surface complète vérifiée : **un seul** site d'insertion
(`MapDtoToMail`, qui lit `CurrentGenerationAsync(mailDto.FolderPath)` — la
génération du dossier **du mail lui-même**, correct) et **une seule** mutation
de `Mail.FolderPath` dans tout `src/` (le rekey). Les ~30 autres `FolderPath =`
sont des DTO ou des traces d'audit, jamais l'entité. Les deux déplacements
possibles (déplacement explicite et mise à la Corbeille) passent tous deux par
`TryRekeyMovedMailsAsync`, donc tous deux couverts.

## Audit de migration — règle 7c

Opérations énumérées et relues une à une :

- **`Up()`** : `Alter.Table` (ajout de colonne), `Delete.Index` (ancien),
  `Create.Index` (nouveau). **Aucune suppression de table ni de colonne.**
- **`Down()`** : le miroir exact.
- **Une seule table touchée** (`Mails`). **Aucune opération fantôme.**
- **Les deux sources de vérité de schéma concordent** : la migration
  FluentMigrator (production) et le mapping EF `HasIndex` — qu'utilise
  `EnsureCreatedAsync` en test — déclarent le même nom d'index, les mêmes
  colonnes et la même unicité. Les tests d'intégration valident la forme
  résultante sur PostgreSQL réel.
- Fichiers compagnons : **sans objet** (FluentMigrator, pas EF Core). Commande
  « pending changes » : **sans objet** pour le même motif.

> ⚠️ **Limite de l'audit** : la migration elle-même n'est **exécutée par aucun
> test** — aucune migration de ce repo ne l'est. Lacune pré-existante, non
> introduite ici, mais elle signifie que l'audit repose sur la relecture et la
> concordance EF, pas sur un `MigrateUp` observé.

## Sonar log

**0 issue sur les 10 fichiers touchés.** Aucun finding introduit, aucune
correction nécessaire.

> ⚠️ KPIs projet toujours inexploitables depuis task-212 — `agents/sonar.md`
> périmé, baseline à refaire.

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/144 — label `awaiting-human-merge`
- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/27 — label `awaiting-human-merge` (**372.0.0 déjà publié** par la CI de branche)

⚠️ **Ordre de merge imposé** : `dtos-mss` **avant** `api-mail`. Le paquet est déjà
publié, donc `api-mail` compile ; mais merger api-mail seul laisserait `develop`
de `dtos-mss` sans le champ que son consommateur référence.

### ⚠️ Piège de version DTO — 374.0.0 est un retour en arrière

`api-mail` épingle **372.0.0**, publiée depuis la branche `fix/task-179` de
`dtos-mss` (= `develop` **+** le champ `FolderDto.UidValidity`). Un bump vers
**374.0.0** est réapparu **deux fois** dans le working tree le 2026-08-02 et
casse la compilation : 374.0.0 a été publiée par la CI de
`fix/task-217-sdk-async-cache`, branche **strictement identique à `develop`**
(`git diff` vide), donc **sans le champ**.

Le numéro est un `github.run_number`, pas un semver : « 374 > 372 » ressemble à
une mise à jour et n'en est pas une. **372.0.0 est un sur-ensemble strict de
374.0.0.** La collision se rejouera à chaque publication d'une autre branche
tant que la PR #27 n'est pas sur `develop` — c'est la vraie raison de l'ordre de
merge, au-delà de la cohérence de contrat.

## Code Review Summary

**APPROVED** — 12 fichiers, 0 blocage.

- `20260802_AddMailUidValidity` — ✅ index **remplacé** et non complété (il
  interdirait la coexistence de deux générations) ; `Down()` qui s'arrête plutôt
  que de choisir en silence quelles lignes sacrifier.
- `FolderRepository` — ✅ purge et bascule **atomiques** ; `UnknownGeneration`
  adoptée sans purge (sinon toutes les boîtes purgées au premier démarrage) ;
  garde-fou d'upsert.
- `MailRepository` — ✅ prédicat de génération sur les deux lectures
  base-d'abord, estampillage à l'insertion sans toucher au contrat interne.
- `BackgroundSyncService` — ✅ confrontation **avant** le diff d'UID ; best-effort
  mais journalisé en erreur, car ne pas avoir pu invalider n'est pas ordinaire.
- `DotEnvLoader` — ✅ les **deux** fixtures câblées ; l'environnement prime sur le
  fichier ; absence de fichier = silence.
- Tests — ✅ 8 unitaires + 4 d'intégration sur moteur réel.

### Réserve consignée
La migration n'est exercée par aucun test (voir audit 7c) — vrai de toutes les
migrations de ce repo, mais à connaître avant de déployer.

> ⚠️ **Cette revue portait sur un socle inerte.** Elle a validé la logique, la
> migration et les tests — tous corrects — sans détecter que le mécanisme ne
> s'exécutait jamais, faute d'un DTO porteur de la génération sur le chemin
> d'arrière-plan. La revue de code lit ce qui est écrit ; elle ne constate pas ce
> qui tourne. Le contrôle qui a manqué est une vérification **en base après
> exécution réelle** — désormais consignée dans le develop log et ajoutée au DOD.

## Merge — 2026-08-02, sur instruction explicite de l'humain

| Étape | Résultat |
|---|---|
| `dtos-mss` PR #27 | **MERGED** 17:56 → `cc6876e` sur `develop` |
| Publication CI `develop` | `run_number 377` → **377.0.0** (contient le champ) |
| Re-pin `api-mail` | 372.0.0 → **377.0.0** (`d429282`) — la dépendance ne pointe plus sur un artefact de branche |
| Merge `origin/develop` | conflit sur `Directory.Packages.props` résolu **par merge** (règle 4) : `Dtos.Mss 377.0.0` de la branche, `Host.Sdk 10.0.0` de develop (bump à ne pas régresser) — `bd4956d` |
| `api-mail` PR #144 | **MERGED** 18:11 → `f7c970b` sur `develop` |
| CI `develop` api-mail | ✓ **success** (règle 5) |
| Branches distantes | supprimées ; **locales conservées** (piège `--delete-branch`) |

Validations avant merge : build **0 erreur / 0 avertissement**, domain 102 ✓,
application 1925 ✓, infrastructure 407 ✓, api 639 ✓, **intégration 298 ✓ / 16
ignorés**.

Deux échecs intermittents observés, **flaky pré-existants confirmés** :
`MailExportServiceTests` et `MarkdownPdfRendererTests.RenderHeadingPreservesText`
(`Could not find the font with name /F5 in the resource store` — course sur les
ressources de police PdfPig en exécution parallèle). Verts en isolation (9/9 ×3),
et le diff ne touche ni l'export ni le PDF.

### ⚠️ Ce qui n'a PAS été fait, et que le merge n'a pas attendu

1. **Test manuel HAG (règle 10)** — scénarios 2 (collision) et 3 (changement
   d'UIDVALIDITY serveur) du Manual Test Plan : **jamais exercés en réel**. Ce qui
   est vérifié en base, c'est le **chemin nominal** — la génération circule,
   estampille, et le déplacement réattribue correctement. L'**invalidation** n'est
   prouvée que par les tests (unitaires et intégration sur Postgres réel).
2. **`/sonar` sur le nouveau diff** — non passé. Le diff ajoute ~577 lignes non
   analysées.

Le merge a été fait **sur instruction explicite de l'humain**, qui a la main sur
cette décision (règle 10). Ces deux points sont consignés ici plutôt que
présentés comme couverts.

## Suites ouvertes

1. **Task dédiée — risque résiduel** : `GetExistingUidsAsync`,
   `GetEnrichedUidsAsync` et `DeleteMailsByUidsAsync` ne filtrent pas par
   génération alors que les lectures le font. C'est cette asymétrie qui transforme
   toute ligne périmée en fantôme **permanent**. Le balayage colmate la
   conséquence à chaque cycle, pas la cause.
2. **`/sonar`** sur le diff mergé, à rattraper.
3. **Scénarios 2 et 3 du Manual Test Plan**, à exercer sur la boîte de formation.
