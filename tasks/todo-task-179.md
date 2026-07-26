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

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test unitaire : UIDVALIDITY du serveur **différente** de la valeur connue ⇒
      les UID locaux du dossier sont invalidés (aucun contenu local servi pour ces
      UID) — ce test doit échouer sur le code actuel, le vérifier explicitement
- [ ] Test unitaire : UIDVALIDITY **inchangée** ⇒ le cache local est utilisé
      normalement (pas de re-synchronisation inutile — pas de sur-correction)
- [ ] Test unitaire : suppression d'un dossier ⇒ aucun mail du dossier ne reste
      adressable ; les cascades (lien patient, documents) respectent la règle
      Corbeille existante
- [ ] Test d'intégration **anti-collision** : dossier `Analyses` peuplé, supprimé,
      recréé avec les mêmes UID côté serveur ⇒ les lectures renvoient les **nouveaux**
      messages, jamais les anciens contenus
- [ ] Test d'intégration : après changement d'UIDVALIDITY, la synchronisation
      re-télécharge bien les messages (le calcul de UID manquants ne les considère
      plus comme déjà présents)
- [ ] Les trois chemins de lecture base-d'abord appliquent la nouvelle identité
      (vérifié par test ou revue explicite listée dans la task)
- [ ] Migration FluentMigrator relue selon la règle 7c (pas d'opération fantôme,
      pas de perte de données non voulue), et stratégie de reprise documentée pour
      les bases existantes
- [ ] Aucune donnée de santé en clair dans les logs

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
