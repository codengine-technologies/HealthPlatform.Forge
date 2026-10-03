# todo-task-339.md — Ranger, renommer, déplacer ou supprimer ne détruit rien d'autre et ne laisse rien derrière : opérations de dossiers fiables

**Repos**: api-mail
**Dependencies**: — (aucune)
**Epic**: E009
**Single frontend**: true
**Priorité**: **2** — mettre un message à la Corbeille peut **détruire définitivement** d'autres messages ; renommer un dossier laisse des documents orphelins qui masquent les nouveaux dans le dossier patient ; la vue par étiquette mélange des mails de dossiers différents.

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, **AUD-29**, **AUD-30**, **AUD-35**, **AUD-49**, **AUD-50**).

## Ce qui est établi (develop @ `14d58398`)

1. **Expunge collatéral (AUD-29)** — `ImapService.cs:3815, 3929, 4074, 4118-4121` : après le MOVE (ou le
   COPY + `UID EXPUNGE` ciblé), `sourceFolder.CloseAsync(true)` envoie un CLOSE qui **expurge tous** les
   messages marqués `\Deleted` du dossier source — y compris ceux qu'un autre client MSSanté a marqués sans
   les expurger. Destruction irréversible, sans copie en Corbeille.
2. **Renommage (AUD-30)** — `FolderRepository.cs:472-484` (`RenameFolderAsync`) ne réécrit que la ligne
   `MailFolders` ; les `Mails.FolderPath` (et les sous-dossiers) gardent l'ancien chemin ;
   `ReconcileFoldersAsync` (`:437-464`) supprime les dossiers disparus **sans purger leurs mails**
   (contrairement à `DeleteFolderByPathAsync`, task-179). Le dossier renommé est retéléchargé ;
   `FindExactDuplicateIdAsync` (`MailRepository.cs:4129`) marque chaque nouveau document « doublon » de
   l'orphelin, que le dossier patient garde → actions IMAP impossibles, bandeaux « doublon », accusés
   biologiques perdus, caches de l'ancien chemin non invalidés. Permanent. (`SyncCoverageService.cs:69-72`
   suppose à tort que les orphelins sont réconciliés.)
3. **Vue par étiquette (AUD-35)** — `MailRepository.cs:3161-3187` (`GetMailsByTagAsync`) : jointure
   `MailTags × Mails` sur `uids.Contains(m.Uid)` sans `FolderPath == INBOX` ni génération (contrairement à
   `GetEmailsByTagAsync`, `:3125-3139`) ; les UID recommencent à 1 par dossier → mails en trop, risque
   d'afficher le mauvais, contexte de l'assistant IA (`AiConversationService.cs:323-336`) pouvant inclure le mail d'un autre patient.
4. **Déplacements (AUD-49)** — `ImapFolderService.cs:523-527, 627-631, 647` : seul `folder:uids` est
   invalidé (compteurs et listes du jour périmés) ; en déplacement groupé, l'audit est lu après la
   ré-indexation → traces `MailMove` sans sujet ni MessageId.
5. **Sans UIDPLUS (AUD-50)** — `ImapMoveHelper.cs:79-89, 118-128` : COPY réussi, `\Deleted` posé, puis
   `ExpungeAsync(uids)` lève `NotSupportedException` → 503 alors que la copie existe ; un nouvel essai duplique.

## Objective

Que chaque opération de dossier **n'affecte que les messages visés**, laisse la base alignée sur le
serveur (chemins, sous-dossiers, orphelins), et que les vues et l'audit reflètent l'état réel.

### Périmètre

1. **Expunge ciblé** : `CloseAsync(false)` après déplacement ; suppression définitive par `UID EXPUNGE` ciblé uniquement.
2. **Renommage** : `Mails.FolderPath` (préfixe compris pour les sous-dossiers) réécrit dans la même
   opération, sur le modèle de `RekeyMovedMailsAsync` ; caches de l'ancien chemin invalidés.
3. **Réconciliation** : les mails d'un dossier disparu du serveur sont purgés comme par `DeleteFolderByPathAsync`.
4. **Reprise** : les orphelins existants sont détectés et purgés (ou réaffectés) une fois ; les marquages
   « doublon » d'un orphelin sont levés.
5. **Vue par étiquette** : filtre `INBOX` + génération, comme `GetMailsByUidsAsync`.
6. **Déplacements** : invalidation complète des caches du dossier (équivalent `InvalidateFolderListingCacheAsync`) ;
   lecture de l'audit **avant** la ré-indexation.
7. **UIDPLUS** : capacité testée avant la stratégie COPY ; sans UIDPLUS, stratégie qui ne duplique pas
   (ou succès partiel rendu explicitement).

### Hors périmètre

- La cascade voulue Corbeille → suppression du lien patient (mémoire « Email Corbeille → cascade ») — inchangée.

## Definition of Done

- [ ] Build passes (0 errors) — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` ; Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] **Tests rouges d'abord** (log des runs rouges dans le task file), rouges sur le code actuel :
  - [ ] (intégration Dovecot) un message A marqué `\Deleted` par un autre client + mise à la Corbeille d'un message B → A **existe toujours**
  - [ ] renommage de `Archives` en `Archives 2026` avec sous-dossier → tous les mails ré-indexés, aucun orphelin, aucun document marqué « doublon »
  - [ ] vue par étiquette : deux mails UID 120 dans INBOX et dans un dossier archivé, seul l'archivé étiqueté → la vue ne rend pas le mail d'INBOX
  - [ ] serveur sans UIDPLUS : déplacement → aucun doublon dans la destination après un nouvel essai
- [ ] Test : dossier supprimé depuis un autre client → ses mails purgés à la réconciliation
- [ ] Test : reprise des orphelins existants (données de test) → dossier patient débarrassé des doublons
- [ ] Test : déplacement → caches de statut et listes du jour invalidés ; trace `MailMove` avec sujet et MessageId
- [ ] Tests d'intégration endpoints (règle 1b) : renommage et déplacement de bout en bout
- [ ] Aucune donnée de santé dans les logs

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` (profil banc, Dovecot) ; Blazor ou mobile + un client IMAP tiers (Thunderbird) sur la même boîte de test.
2. **Expunge** : dans Thunderbird (mode « marquer comme supprimé »), marquer le message A supprimé sans compacter ; dans l'application, mettre B à la Corbeille → A est toujours présent. Avant : A détruit.
3. **Renommage** : renommer un dossier porteur de comptes rendus rattachés à un patient → le dossier patient montre les documents une seule fois, sans bandeau « doublon », et répondre / déplacer depuis le dossier patient fonctionne.
4. **Vue étiquette** : ouvrir la vue « BIO » → seuls les mails réellement étiquetés s'affichent.
5. **Déplacement** : déplacer un mail du jour → la tuile « reçus aujourd'hui » se met à jour immédiatement ; l'écran d'audit montre le sujet du mail déplacé.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville, biologie
- **Vague Ségur** : V2
- **Exigences DSR honorées** : non applicable — intégrité des opérations de messagerie existantes
- **INS** : non applicable — les rattachements patient existants sont conservés et dé-doublonnés
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : `MailMove`, suppression et renommage tracés avec leurs métadonnées (sujet, MessageId), sans contenu
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement inchangé
- **AIPD / impact RGPD** : inchangé — supprime une destruction de données non voulue

## Branches

- `api-mail` (pushed) : fix/task-339-operations-dossiers-fiables — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-339-operations-dossiers-fiables
- `dtos-mss` : aucune branche à ce stade (branche paresseuse, créée par /develop si un contrat bouge)
