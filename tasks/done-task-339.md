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
   ⚠️ **Infirmé par /develop (2026-10-04)** : MailKit 4.17 ne lève pas sans UIDPLUS, il expurge par UID en
   protégeant les autres messages marqués. Test vert sur le code d'avant ; gardé en non-régression (Develop log).

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

## Timings

*(généré par `tools/timing/report.sh --task task-339 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 13 s | — | — | — | — |
| /develop | ok | 52 min 41 s | 8 (44 s) | 21 (11 min 26 s) | — | api-mail 8B/21T, api-mail : AUD-29/30/35/49, AUD-50 non reproduit ; 10 mutations rouges |
| /sonar | ok | 12 min 36 s | 3 (38 s) | 11 (8 min 23 s) | 4 (1 min 10 s) | 1 itération(s), api-mail 3B/11T |
| /lint-angular | skipped | 0.4 s | — | — | — | client-angular non listé, aucun fichier de la task |
| /lint-mobile | skipped | 0.4 s | — | — | — | client-mobile non touché |
| /e2e | ok | 9 min 04 s | — | — | — | e2e ×3 (8 min 32 s) |
| /review | ok | 55 min 01 s | 1 (14 s) | 5 (5 min 01 s) | — | api-mail 1B/5T, PR #272, APPROVED, suites vertes à 02:05 |
| **Total cycle** | | **2 h 09 min** | **12 (1 min 38 s)** | **37 (24 min 51 s)** | **4 (1 min 10 s)** | |

## Develop log

**Repos touchés** : `api-mail` seul. Aucun contrat ne change (`dtos-mss` sans branche).

### Ce qui change
- **AUD-29 — expunge ciblé.**
  - Après un MOVE vers la Corbeille (unitaire ou groupé), le dossier source se ferme **sans expunge** (`CloseAsync(false)`).
  - La suppression définitive (Corbeille, unitaire et groupée) et le remplacement ou la suppression d'un brouillon expurgent **par UID** les seuls messages visés.
  - Un message marqué supprimé par un autre client, sans être expurgé, n'est plus détruit.
  - `ReplaceDraftAsync` et `DeleteDraftAsync` ne sont appelés par aucun endpoint (code mort) : corrigés quand même, couverts par leurs tests unitaires.
- **AUD-30 — renommage.**
  - `FolderRepository.RenameFolderAsync` réécrit, dans une transaction :
    - le dossier et ses sous-dossiers (chemin, parent, nom) ;
    - leurs mails (`ExecuteUpdate`, préfixe + séparateur IMAP) ;
    - les actions en attente.
  - Il rend les anciens chemins, dont `ImapFolderService` invalide la liste d'UID et le statut.
  - Les lignes qu'une liste concurrente aurait écrites sous le nouveau chemin sont retirées : les lignes renommées, enrichies, font foi.
- **Réconciliation et reprise.**
  - `PurgeMailsOfFoldersNotOnServerAsync` (nouvelle) purge les mails de **tout** dossier absent de la liste du serveur. Cela couvre un dossier supprimé ou renommé ailleurs, ainsi que les orphelins déjà laissés par l'ancien renommage.
  - Les marquages « doublon » qui pointaient sur les documents purgés tombent par `ON DELETE SET NULL`. La reprise se fait donc d'elle-même, à la première liste des dossiers.
  - La purge n'est appelée qu'après un `LIST` réel du serveur (`ImapService`, `ImapFolderService`), jamais sur l'instantané en cache : il peut ignorer un dossier créé ailleurs depuis.
  - Une liste sans `INBOX` est tenue pour fausse : rien n'est purgé.
  - Les chemins distincts sont lus par un balayage d'index par saut (CTE récursive sur `IX_Mails_FolderPath_UidValidity_Uid_Unique`) : une sonde par dossier, quelle que soit la taille de la boîte.
- **Synchronisation de fond.**
  - Elle ne réconcilie plus. Sa liste ne porte que le premier niveau (`GetSubfoldersAsync` non récursif) : la réconciliation retirait les lignes des sous-dossiers à chaque passe, et avec la purge elle aurait vidé leurs mails.
  - La réconciliation reste faite par la liste des dossiers, sur la liste complète.
- **AUD-35 — vue par étiquette.** `GetMailsByTagAsync`, `GetEmailsByTagAsync` et les badges (`GetTagFoldersAsync`) sont limités à `INBOX` et à sa génération courante, par une seule requête de base (`CurrentInboxMailsAsync`). Le contexte de l'assistant IA, qui lit la même méthode, est corrigé du même coup.
- **AUD-49 — déplacements.**
  - Un déplacement, unitaire ou groupé, invalide la liste d'UID **et le statut** des deux dossiers, ainsi que les caches propres aux messages quittés. Retirer le statut neutralise aussi les listes du jour (`folder:query`).
  - Le déplacement groupé lit le contexte de la trace `MailMove` (sujet, MessageId) **avant** la ré-indexation.
- **AUD-50 — non reproduit.** Constat, puis aucun changement de code :
  - MailKit 4.17 n'échoue pas sur `ExpungeAsync(uids)` sans UIDPLUS : il retire `\Deleted` aux autres messages marqués, expurge, puis les remarque (documentation du paquet, et test vert sur le code d'avant).
  - Le repli COPY n'a donc jamais rendu de 503, et ne duplique pas sur un nouvel essai.
  - Le test reste comme garde de non-régression, avec sa prémisse vérifiée (aucun UID de destination rendu) et une mutation prouvée.

### Tests et preuves rouges (règle 1b)
| Comportement | Test d'intégration (vraie pile HTTP, Dovecot, base praticien) | Preuve rouge |
|---|---|---|
| Mettre B à la Corbeille garde A, marqué par un autre client | `MovingAMessageToTrash_KeepsAMessageAnotherClientMarkedDeletedWithoutExpunging` | rouge sur le code d'avant (A détruit) |
| Supprimer définitivement B garde A en Corbeille | `DeletingFromTrash_DestroysOnlyTheTargetedMessage` | rouge sur le code d'avant |
| Renommer `Archives` (avec `2025` et un CDA) : tout suit, aucun orphelin, aucun doublon après relecture | `RenamingAFolderWithASubfolder_MovesEveryMailAlong_LeavesNoOrphan_AndNoDocumentMarkedDuplicate` | rouge sur le code d'avant (`Archives`, `Archives/2025` restés) |
| Vue étiquette : UID 120 d'INBOX et d'un dossier archivé, fantôme d'une autre génération | `TheTagView_ReturnsOnlyTaggedInboxMailsOfTheCurrentGeneration` | rouge sur le code d'avant (3 mails au lieu d'1) ; M4 (sans filtre de génération) rouge |
| Sans UIDPLUS ni MOVE : deux déplacements, une copie, le message marqué ailleurs épargné | `OnAServerWithoutUidPlus_MovingTwice_LeavesOneCopy_AndSparesMessagesOthersMarkedDeleted` | M3 (expunge complet dans le repli COPY) rouge |
| Dossier supprimé par un autre client : ses mails partent à la liste suivante | `AFolderDeletedByAnotherClient_LosesItsMailsAtTheNextFolderListing` | rouge sur le code d'avant |
| Un déplacement groupé retire liste et statut des deux dossiers et le cache du message ; sa trace `MailMove` porte sujet et MessageId | `MovingMessages_InvalidatesTheListingAndStatusOfBothFolders_AndTracesTheMoveWithItsSubject` (traces lues dans le canal d'audit de la fixture ; prémisse : ligne ré-indexée relue) | rouge sur le code d'avant (statut gardé) ; M10 (destination non invalidée) rouge ; M2 au niveau HTTP (contexte lu après la ré-indexation) rouge, sujet nul. Vert sous M2 avant l'ajout de la garde de prémisse : cf. `conventions/csharp.md` › `premisse-de-test-integration` |
| Orphelins existants purgés, dossier patient sans doublon | `ExistingOrphans_ArePurgedAtTheNextFolderListing_AndTheirDuplicateMarksAreLifted` | rouge sur le code d'avant |

- **Dépôt sur PostgreSQL** (`FolderRepositoryReconcileRenameIntegrationTests`, 7 tests) : il remplace les tests InMemory, qui ne savent exécuter ni `ExecuteUpdate`, ni la transaction, ni la requête SQL. Mutations rouges :
  - M5 : préfixe sans séparateur, le frère `ArchivesX` est renommé ;
  - M6 : actions en attente oubliées ;
  - M7 : INBOX non protégée (devenu, après la passe qualité, « une liste sans INBOX ne purge rien », même test) ;
  - M8 : lignes concurrentes gardées, violation d'index unique.
- **Unitaires** :
  - `BackgroundSyncServiceTests.StartSyncAsync_NeverReconcilesFoldersAgainstItsTopLevelListing` (M1 rouge) ;
  - `ImapFolderServiceSuccessTests.BulkMoveEmailsAsync_TracesSubjectAndMessageId_ReadBeforeTheRowsLeaveTheSourceFolder` : dépôt à état, qui ne rend plus le mail une fois ré-indexé, comme le vrai ; M2 (lecture après la ré-indexation) rouge ;
  - sept tests existants réalignés : expunge ciblé, `CloseAsync(false)`, invalidation complète des déplacements.
- **Harnais** : `CapabilityStrippingImapClientWrapperFactory` retire UIDPLUS et MOVE après authentification, pour les seules boîtes qu'un test inscrit.
- **Test existant corrigé** : `MailRepositoryTagDraftCoverageTests.AddNewMail_WithMedicalDocumentContent_PersistsTheDocumentAndMapsItInTagListing` semait dans un dossier non-INBOX et ne passait que grâce à AUD-35. Il est désormais dans INBOX, sur une base isolée.
- **Prévention (règle d'or)** : `ImapExpungeIsTargetedScanTests` (api.tests/Architecture) échoue sur tout `CloseAsync(true)` ou `ExpungeAsync()` sans UID dans `src/`. Mutation M9 (un `CloseAsync(true)` réintroduit) : rouge, la ligne fautive est nommée.

### Passe qualité (/simplify, 4 revues : réutilisation, simplification, efficacité, altitude)
- **Appliqué** (`refactor(folders): simplify pass`) :
  - **purge séparée de la réconciliation.** La revue d'altitude a relevé un vrai risque : purger sur l'instantané en cache (TTL 5 min) vidait, à chaque lecture, un dossier créé ailleurs depuis et déjà synchronisé, rattachements patient compris ;
  - garde `INBOX` portée par toute la purge, et non plus par le seul chemin `INBOX` ;
  - **une seule éviction de liste de dossier**, `MailCacheEviction.RemoveFolderListingEntriesAsync`, qui porte désormais la règle task-229 (`folder:query`). Elle est utilisée par `ImapService`, `ImapFolderService` (déplacements, renommage, suppression, auto-réparation) ;
  - les retraits d'un déplacement partent ensemble (`Task.WhenAll`), au lieu de 4 + 2N appels séquentiels sous le verrou `imap_session` ;
  - badges d'étiquettes sur la génération courante (même définition que la vue) ;
  - harnais : le wrapper sans UIDPLUS dérive du vrai `ImapClientWrapper`, assertions explicites, paramètre mort retiré ; commentaires AUD-29 dédoublonnés.
- **Écarté** :
  - `ExecuteDelete` sur les lignes `MailFolders` (réconciliation, renommage) : elles peuvent être suivies par le contexte juste après un upsert (`executeupdate-copie-suivie-perimee`) ;
  - prédicat de plage au lieu de `StartsWith` dans le renommage (renommage rare) ;
  - génération en sous-requête dans les vues étiquette (gain sub-milliseconde) ;
  - extraction d'un hôte HTTP commun aux trois suites `UseCases` et d'une `OpenPractitionerBase` partagée (touche deux suites existantes : suivi) ;
  - aide « UID × génération » pour toutes les lectures par UID de `MailRepository` (trop large : suivi).
- **Re-validation** : domain 190, infrastructure 683, application 3 384, api 1 170, integration 786 (+16 ignorés), 0 échec propre à la task (voir ci-dessous).

### Vérifications
- **Rouges préexistants, hors task** : `GetFolderTodayAsync_Inbox_…`, `GetFolderNotSeenTodayAsync_Inbox_…`, `FilterTodayEmailsShouldReturnOnlyToday…`.
  - Rejoués à 00:48 (heure locale) sur `origin/develop` en worktree : rouges aussi.
  - Le corpus date le message « du jour » en heure locale, et Dovecot compare `SINCE` en UTC : entre 00:00 et 02:00 (heure d'été), le message tombe la veille.
  - Consigné en mémoire. Suivi proposé : semer à midi local.
- Avertissement de build unique : `ASPIRE010` (AppHost, `AspireUseCliBundle=false`), préexistant.
- Aucune donnée de santé dans les journaux ajoutés : comptes seulement, ni chemin de dossier, ni sujet.
- Branche `fix/task-339-operations-dossiers-fiables` poussée (5 commits).

### Suivis proposés
1. `BackgroundImapService.GetFoldersAsync` liste le seul premier niveau : les sous-dossiers ne sont jamais synchronisés en fond. Une liste récursive partagée par les trois implémentations rendrait aussi la réconciliation de fond possible.
2. Lectures par UID de `MailRepository` sans filtre de génération (une douzaine) : une requête de base « mails du dossier dans sa génération », comme `CurrentInboxMailsAsync`.
3. Hôte HTTP commun aux suites `UseCases` (`ForwardedServices` de `MailController`, `OpenPractitionerBase`, `Server`) : trois copies.
4. Corpus de test : message « du jour » daté à midi local (fenêtre 00:00-02:00).
5. `ReplaceDraftAsync` / `DeleteDraftAsync` d'`ImapService` : aucun appelant (code mort), à retirer.

- Next step : `/sonar task-339`

## Sonar log

**Analyse** : deux passes complètes sur `fix/task-339-operations-dossiers-fiables` (serveur 9.9.8, `sonar.login`), avec la couverture des cinq suites.
- Résultats : domain 190, application 3 384, infrastructure 683, api 1 170, integration 787 (+16 ignorés).
- Seuls rouges : les trois tests « du jour », dans la fenêtre 00:00–02:00 (préexistant, rouges aussi sur develop, cf. Develop log).

**Itération 1** (`refactor(folders): CA1869 …, CA1845 …`) :
- **CA1869** sur `FolderOperationsEndToEndTests.ReadTagViewAsync` : `JsonSerializerOptions` hissé en `static readonly`.
  - **Récidive** (3ᵉ occurrence) d'une consigne lue avant de coder, consignée dans `conventions/csharp.md`.
- **CA1845** ×2 sur `FolderRepository.RenameFolderAsync` : faux positif, car ce sont des expressions `ExecuteUpdate` traduites en SQL, qui ne peuvent pas porter `AsSpan`.
  - Suspendu localement, raison écrite au-dessus.
  - Nouvelle entrée dans `conventions/csharp.md`.

### KPIs qualité (baseline → final)

| Métrique | Baseline (analyse task-331, 2026-10-03) | Final (task-339) | Δ |
|---|---|---|---|
| Quality Gate | OK | **OK** | = |
| New coverage | 97,5 % | 97,5 % (FolderRepository 98,6 %, ImapFolderService 100 %, MailCacheEviction 100 %) | = |
| Coverage projet | 98,0 % | 98,0 % | = |
| Bugs / Vulnérabilités | 0 / 0 | 0 / 0 | = |
| Code smells | 13 | 13 | = (16 à la première passe, 3 traités) |
| Duplication | 0,4 % (nouveau code 0,15 %) | 0,4 % (nouveau code 0,15 %) | = |
| Ratings fiabilité / sécurité / maintenabilité | A / A / A | A / A / A | = |

- **Constat restant** : S107 sur `SemanticSearchService:395`, antérieur (task-329), hors du code de la task.

## Lint log

- **Skipped** — `client-angular` n'est pas dans les `**Repos**` de la task. Son arbre ne porte que les deux `environment.ts` de l'humain, hors task.

## Lint mobile log

- **Skipped** — `client-mobile` n'est pas dans les `**Repos**` de la task (arbre propre, sur `develop`).

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | `api-mail` touché | ✅ verte | 27 verts, 0 flaky, 0 rouge, 0 quarantaine | 4 min 23 s |
| angular | `api-mail` touché | ✅ verte | 27 verts, 0 flaky, 0 rouge, 0 quarantaine | 4 min 09 s |

- Backend joué : `api-mail` @ `fix/task-339-operations-dossiers-fiables`. Clients : `client-mobile` @ `develop`, `client-angular` @ `feature/nova-rewriting-mss`, checkout de l'humain, sans opération git.
- Catalogue : `Api/Mail/e2e/scenarios.yml` inchangé par la task, qui ne crée ni ne modifie aucun parcours médecin (`**Single frontend**`, API seule).
- Porte `gate` : code 0. Quarantaines : aucune. Flaky : aucun. Divergences ouvertes : aucune.
- Parcours touchés sans spec e2e modifié : aucun (aucun écran modifié).
- Démontage : complet (aucun conteneur e2e résiduel).
- Amélioration continue (`conventions/e2e.md`) : aucune leçon sur ce passage.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 1 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 1 | headless | Créer puis supprimer un contact | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/272 — label `awaiting-human-merge`. Corps : changements, table règle 1b, revue, KPIs Sonar, parcours e2e, plan de test.
- `dtos-mss` : aucune branche, aucun contrat ne change.
- `client-angular`, `client-blazor`, `client-mobile` : non concernés (task API seule, `**Single frontend**: true`).

## Code Review Summary

**Verdict : APPROVED** (0 bloquant, 3 suggestions).

- **DOD** :
  - [x] Build et tests : domain 190, infrastructure 683, application 3 384, api 1 170, integration 790 (+16 ignorés), 0 échec, rejoué à 02:05, hors de la fenêtre des tests « du jour »
  - [x] Tests rouges d'abord (Develop log) : expunge collatéral (Corbeille et suppression définitive) ; renommage `Archives` → `Archives 2026` avec sous-dossier, sans orphelin ni doublon ; vue par étiquette (UID 120 de deux dossiers) ; serveur sans UIDPLUS, sans doublon après un nouvel essai.
    - Le dernier était vert sur le code d'avant : AUD-50 n'est pas reproduit avec MailKit 4.17 (voir Develop log). Le test est gardé en non-régression, prémisse et mutation prouvées.
  - [x] Dossier supprimé par un autre client : ses mails partent à la liste suivante.
  - [x] Reprise des orphelins : dossier patient débarrassé du doublon.
  - [x] Déplacement : statut et listes du jour invalidés, trace `MailMove` avec sujet et MessageId, éprouvés par HTTP.
  - [x] Tests d'intégration endpoints : renommage et déplacement de bout en bout.
  - [x] Aucune donnée de santé dans les journaux : comptes seulement, ni chemin, ni sujet.
- **Verrou 4a (règle 1b)** : les huit comportements atteignables par un endpoint ont chacun leur test HTTP sur la vraie pile (Dovecot, base praticien, Redis substitué sous le décorateur), lu dans la réponse, sur le serveur IMAP ou en base, et vu rouge (table ci-dessus).
- **Verrou 4b** : `## E2E log` vert sur les deux voies (27/27), parité verte.
- **Revue par zone** :
  - ✅ Expunge : plus aucun `CloseAsync(true)` ni `ExpungeAsync()` sans UID dans `src/`. Une garde de convention le maintient.
  - ✅ Renommage : une transaction, préfixe avec séparateur (le frère `ArchivesX` est épargné, mutation M5), lignes concurrentes sous le nouveau chemin retirées (M8).
  - ✅ Purge :
    - réservée à une liste lue à l'instant sur le serveur ;
    - une liste sans INBOX ne purge rien ;
    - coût borné, une sonde d'index par dossier.
  - ✅ Synchronisation de fond : sa réconciliation sur une liste de premier niveau est retirée, et le test le garde.
  - ✅ Vue et badges par étiquette : une seule requête de base, INBOX et génération courante.
  - ⚠️ **Course résiduelle** : une liste des dossiers lue avant un renommage, mais persistée après lui, porte encore l'ancien nom.
    - Sa purge retirerait alors les mails tout juste renommés. Ils seraient re-téléchargés, mais leurs rattachements manuels et accusés perdus.
    - Fenêtre de quelques dizaines de millisecondes.
    - La même course existait déjà pour les lignes de dossier (réconciliation), sans perte de données.
    - Suivi proposé : un numéro de version de l'arborescence, relu avant la persistance.
  - ⚠️ `CA1845` suspendu localement dans les deux `ExecuteUpdate` du renommage : expressions traduites en SQL, raison écrite.
  - ⚠️ La purge s'exécute en ligne sur le chemin « cache manquant » de la liste des dossiers : une requête par dossier présent en base, hors du verrou IMAP.

**Suivis à ouvrir** (Develop log) :
1. Liste récursive des dossiers partagée, dont la synchronisation de fond.
2. Lectures par UID sans génération dans `MailRepository`.
3. Hôte HTTP commun aux suites `UseCases`.
4. Message « du jour » semé à midi local.
5. Méthodes de brouillon mortes d'`ImapService`.
6. Version de l'arborescence contre la course liste périmée / renommage.
