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

## Extension — reprise des étiquettes IA manquantes (demande humaine du 2026-10-04)

> Demandée par l'humain après la revue, **sur la branche de task-344** : « si le calcul du tag est en échec à cause
> d'une API IA, que se passera-t-il ? » — réponse : le mail restait **définitivement** sans étiquette IA (« Urgent »),
> l'échec étant avalé sans relance ni reprise. « Fais-le directement sur cette branche. »

### Objectif
Un mail analysé dont l'étiquetage IA a échoué (fournisseur indisponible, délai dépassé, message de bus non publié)
est **repris automatiquement**, sans retéléchargement, tant qu'il est récent — et sans marteler un fournisseur en panne.

### Definition of Done (extension)
- [ ] Le service de suggestion distingue « aucune étiquette » de « échec » (contrat `TagSuggestionOutcome`)
- [ ] Deux marqueurs par mail : étiquetage **demandé** (posé à l'enregistrement du contenu et à chaque reprise) et étiquetage **fait** (posé quand l'IA a répondu, même sans étiquette)
- [ ] Reprise par boîte en fin de synchronisation de fond : mails reçus depuis moins de 7 jours, analysés, jamais étiquetés, demande de plus de 15 minutes ; arrêt au premier échec ; flags `ai_pipeline` + `ai_auto_tagging` respectés ; brouillons, envoyés, corbeille exclus
- [ ] Migration : colonnes ajoutées, **historique marqué étiqueté** (aucune rafale d'appels IA au déploiement), index partiel des mails en attente ; règle 7c
- [ ] Tests d'intégration PostgreSQL (coureur de production) : mail en échec repris et étiqueté ; mail étiqueté sans étiquette non repris ; fenêtre, délai et exclusions ; arrêt au premier échec ; migration ; preuves rouges par mutation consignées
- [ ] Tests unitaires par branche (service de suggestion, étiqueteur, reprise, accroche de la synchronisation)
- [ ] Une panne de la reprise ne fait jamais échouer la synchronisation ; aucune donnée de santé dans les journaux

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
| /develop | ok | — | 4 (22 s) | 23 (21 min 52 s) | — | api-mail 4B/23T, extension reprise etiquetage IA; no start marker |
| /sonar | ok | 7 min 40 s | 4 (55 s) | 18 (19 min 45 s) | 6 (1 min 48 s) | 1 itération(s), api-mail 4B/18T, extension |
| /lint-angular | skipped | 0.4 s | — | — | — | repo non touche (extension) |
| /lint-mobile | skipped | 0.4 s | — | — | — | repo non touche (extension) |
| /e2e | ok | 9 min 43 s | — | — | — | e2e ×6 (18 min 37 s), rejeu extension |
| /review | ok | 14 min 21 s | 2 (21 s) | 3 (6 min 24 s) | — | api-mail 2B/3T, e2e ×2 (8 min 49 s), extension |
| /tech-writer | ok | 0.5 s | — | — | — | v1.20 |
| **Total cycle** | | **32 min 03 s** | **10 (1 min 38 s)** | **44 (48 min 03 s)** | **6 (1 min 48 s)** | |

## Comportement transactionnel actuel de la promotion (relevé avant correctif, develop @ `1a36fcbc`)

`MailRepository.UpdateExistingMailWithContentAsync` (appelée par `TryResolveExistingMailAsync` quand la ligne est
« en-têtes seuls », et par le repli de `PersistNewMailAsync` sur violation d'unicité) :

1. **Lecture suivie** de la ligne `Mails` avec `MailContents` et `MailMedicalDocuments` (`Include`). Si un contenu
   existe déjà → rend l'Id, n'écrit rien. C'est le **seul** garde, et il est lu **avant** l'écriture : deux
   réplicas qui lisent tous deux « en-têtes seuls » passent tous deux.
2. Ajout au suivi : la ligne `MailContents`, les `MailMedicalDocuments` (détection doublon/version, patient),
   leur biologie, leurs items de synthèse, leurs pièces jointes, les drapeaux du mail.
3. `SavePromotedContentAsync` : **un seul `SaveChangesAsync`**, donc une transaction **implicite** EF qui couvre
   contenu + documents + biologie + pièces jointes + patients + UPDATE du mail. Ces écritures-là sont atomiques
   entre elles.
4. **Hors de cette transaction** :
   - `ApplyPendingSupersedureAsync` — `ExecuteUpdate` en autocommit, après le `SaveChanges` ;
   - `AddCategoryTagsToMailAsync` — écritures séparées des étiquettes de catégorie.
   Un échec à ce stade laisse le contenu **committé** (le mail est désormais « analysé » et ne sera jamais
   rejoué) avec un chaînage de versions ou des étiquettes manquants.
5. Aucun jeton de concurrence : le `catch (DbUpdateConcurrencyException)` ne se déclenche pas sur la course
   (rien n'est mis à jour à zéro ligne). `IX_MailContents_MailId` est **non unique** : la base accepte la
   seconde ligne de contenu, et le second jeu de documents qui l'accompagne.

Contraste : `PersistNewMailAsync` (insertion d'un mail neuf) ouvre une transaction explicite depuis task-342
(AUD-36) qui couvre aussi le chaînage et les étiquettes ; la promotion n'en a pas.

## Develop log

- Repos touched : api-mail (seul repo de la task) — branche `feat/task-344-promotion-unique-mail`, poussée
- DTOs published : no DTO change (`EnrichmentOutcome` vit dans `Application/Models`, pas dans `dtos-mss` ; champ ajouté, optionnel)
- Interop published : no interop change
- Commits (api-mail) :
  - `b99c17c3` fix(mail): un mail n'est promu qu'une fois, garanti par la base
  - `79b05cbc` feat(enrich): le second réplica laisse l'analyse au premier
  - `503540c0` refactor(mail): simplify pass (/simplify)
- Ce qui change :
  1. **Garantie en base** — index unique `UX_MailContents_MailId` (remplace `IX_MailContents_MailId`), migration
     FluentMigrator `UniqueMailContentPerMailMigration` (20261005120000), déclaré aussi dans `MailDataContext`.
  2. **Atomicité** — `PersistPromotionAsync` : contenu, documents, biologie, pièces jointes, chaînage de versions
     et étiquettes dans **une** transaction (forme de `PersistNewMailAsync`, AUD-36). Le perdant reçoit la
     violation nommée (`IsContentAlreadyPromoted`), annule tout, rend le mail sans erreur, journalise en Information.
  3. **Économie** — `MailPromotionClaim` : revendication Redis par (boîte, dossier, UID), `lock:mail-promotion:…`,
     3 min, prise dans `ImapService.EnrichEmailsAsync` **avant** le fetch. Revendication tenue ailleurs → ni fetch
     IMAP ni analyse CDA, compté `InProgressElsewhere` (nouveau compte d'`EnrichmentOutcome`, ni échec ni
     injoignable : pas de relance). Redis indisponible → analyse sans revendication (la garantie reste l'index).
     Seules les revendications prises sont rendues.
  4. **Migration** — résorption restreinte aux mails à plusieurs lignes de contenu : copie la plus ancienne de
     chaque (DocumentId, Version) conservée, **accusés biologiques reportés** sur elle, liens doublon/version
     reportés, copies et pièces jointes en double supprimées, contenu le plus ancien conservé ; nombres
     journalisés, sans contenu. Sonde `EXISTS` d'abord : sans doublon, aucune table temporaire.
- Preuves rouges (règle 1b) :
  - `MailPromotionUniquenessTests.TwoReplicasPromotingTheSameHeaderOnlyMail_WriteOneContentAndOneSetOfDocuments`
    — rouge sur develop : `Actual: PromotionFootprint { Contents = 2, Documents = 2, Biology = 4, DocumentAttachments = 2 }`
    (run sans catégorie) ; avec catégorie, le perdant lève `23505 IX_MailTags_MailId_TagId` (erreur rendue).
  - `TheLoserOfThePromotionRace_IsServedTheWinnersContent` — rouge sur develop (perdant en erreur, même 23505).
  - `APromotionFailingAfterItsDocuments_WritesNothing_AndTheMailStaysPending` — rouge sur develop :
    `Expected { 0, 0, 0, 0 } / Actual { Contents = 1, Documents = 1, Biology = 2, DocumentAttachments = 1 }`.
  - Mutations (restaurées par `cp` + `touch`) :
    - M1 accusés non reportés → `Sequence contains no elements` (accusé perdu) ;
    - M2 liens doublon non reportés → `Expected …f9f6 / Actual null` ;
    - M3 aucune résorption → `23505 could not create unique index "UX_MailContents_MailId"` ;
    - M4 perdant non reconnu → `23505 UX_MailContents_MailId` remonte au praticien ;
    - M5 revendication ignorée (HTTP, `ArchiveAnalysisMarkerEndToEndTests.EnrichingAMail_WhoseAnalysisAnotherReplicaHasClaimed_…`)
      → `analysed Expected 0 / Actual 1` (le mail a été fetché et analysé).
  - **Pourquoi la course elle-même est prouvée au dépôt, pas par HTTP** : deux requêtes sur un même hôte de test
    sont sérialisées par le verrou de persistance **en processus** — la course n'existe qu'entre deux processus.
    Le test la reproduit avec deux contextes indépendants (deux réplicas) sur une base bâtie par le coureur de
    migrations de production, comme l'exige la DOD. Le comportement atteignable par l'endpoint (`enrich/sync`,
    second réplica) est prouvé par HTTP sur la vraie pile (Dovecot, extraction, PostgreSQL).
- Inventaire (`Api/Mail/docs/task-344-inventaire-doublons-contenu.sql`, exécuté tel que livré par les tests) :
  - base de test avant migration : `1 / 1 / 1` (mail / contenu / document surnuméraires) ; après : `0 / 0 / 0`.
  - base de banc locale `u_899700622675_vmm_c9e6…` (version de schéma 20261004120000, **avant** migration) :
    `0 / 0 / 0`. Le « après » sur cette base se fera au premier démarrage de l'application (Manual Test Plan, étape 5) :
    la base n'est pas migrée hors de l'application.
- Règle 7c : fichier de migration relu ; aucune opération fantôme (DROP/CREATE de l'index de `MailContents`
  seulement, données touchées restreintes aux mails promus plusieurs fois) ; FluentMigrator n'a ni `.Designer.cs`
  ni snapshot ; « has pending changes » : `HasMigrationsToApplyUp() == false` affirmé par
  `Migration_OnACleanBase_InstallsTheUniqueIndex_AndTheInventoryReportsNothing`.
- Tests ajustés (données invalides désormais refusées par l'index, sans changer leur sujet) :
  `AddEmbeddingModelColumnsMigrationTests`, `PgBouncerTransactionPoolingTests` (deux contenus sur deux mails) ;
  substituts de verrou des tests d'enrichissement déclarés « sans concurrence »
  (`MockFactory.WithUncontendedPromotionClaims`, `PromotionClaims.Uncontended`) — un substitut nu répond « tenu ailleurs ».
- Local build / test : ✓ — 0 erreur ; 6 315 réussis, 16 ignorés (identiques sur develop), 0 échec
  (domain 190, infrastructure 683, api 1 176, application 3 451, integration 815 + 16 ignorés).
- Passe qualité (/simplify) :
  - Applied & committed : api-mail — 9 fichiers (`503540c0`) : helper d'étiquettes de catégorie partagé par les
    deux chemins, `IsUniqueViolationOn` commun aux deux prédicats nommés, compte `alreadyAnalysed` capturé avant la
    revendication, `MailPromotionClaim` en `Where` indexé, préfixe de clé unique (`RedisKeys.Lock.MailPromotionPrefix`),
    migration : sonde `EXISTS`, liens auto-référents annulés par `NULLIF` (deux balayages complets de moins), index
    unique créé **avant** la suppression de l'ancien (lectures non bloquées pendant la construction).
  - Écartés (notés pour `/review`) : revendications groupées en un script Lua (nouvelle API de verrou, à mesurer au
    banc) ; transaction de persistance factorisée entre les deux chemins ; constante de 3 min partagée avec le verrou
    de fetch (hors diff) ; revendication sur le chemin de fond (`BackgroundImapService`) — extension de périmètre ;
    effets de bord du perdant (bus, notification, audit, compte `Analysed`) — `AddNewMail` rend un `Guid`, un résultat
    typé changerait le contrat ; fusion des deux branches « course perdue » et retrait du verrou de persistance en processus.
  - Skipped (contract/excluded) : dtos-mss, interop-cda, sdk (non touchés)
- Conventions : nouvelle entrée `unicite-garantie-par-la-base` dans `conventions/csharp.md` ; contrôles mécaniques §Q 2b vides.
- DOD self-check : 9/10 vérifiables par commande ✓ ; « aucune INS, contenu CDA ni corps dans les logs » ✓ (journaux : UID,
  dossier, MailId, nombres) ; le test manuel multi-appareils reste au HAG.
- Next step : /sonar task-344

### Extension — reprise des étiquetages IA manqués (demande humaine du 2026-10-04)

- Commits (api-mail) : `8c52c6f0` feat(tagging) reprise des étiquetages IA manqués ; `577c3f4b` fix(tagging) reprise
  programmée par l'enrichissement, attente en un seul marqueur (passe qualité).
- **Contrat** : `IEmailTaggingService.SuggestTagsAsync` rend `TagSuggestionOutcome(Tags, Failed)` — l'échec n'est plus
  confondu avec « aucune étiquette ».
- **Marqueur** : `Mails.AiTaggingPendingSince`, posé à l'enregistrement du contenu (mail neuf ou promotion ; hors
  brouillons, envois, corbeille), effacé quand le modèle répond, redaté à chaque essai de reprise. Migration
  `AddAiTaggingPendingMigration` (20261005130000) : colonne nullable sans défaut (aucune réécriture de l'historique, aucune
  rafale d'appels IA au déploiement), index partiel `IX_Mails_AiTaggingPending` des seuls mails en attente.
- **Étiqueteur** `MailAutoTagger` : partagé par le consommateur du bus et la reprise ; matière composée par
  `AiTaggingMaterial` (type de document du premier LOINC, corps texte sinon HTML converti), partagée avec la publication.
- **Reprise** `AiTaggingRecoveryService` : mails analysés, reçus depuis moins de 7 jours, en attente depuis plus de
  15 min, 20 par passe, arrêt au premier échec ; flags `ai_pipeline` + `ai_auto_tagging`.
- **Déclencheur** `AiTaggingRecoveryScheduler` : chaque enrichissement programme une passe **en tâche de fond**, au plus
  une toutes les 10 min par boîte, tous réplicas confondus (clé Redis `lock:ai-tagging-recovery:{boîte}` non rendue).
  ⚠️ Première version accrochée à la synchronisation complète : **défaut trouvé par la passe qualité** (angle
  « altitude ») — la synchronisation complète ne part que du bouton du praticien (`EnableFullSync=false` par défaut),
  la reprise n'aurait presque jamais tourné. Corrigé avant le push.
- **Compteur** : le consommateur compte désormais l'échec du modèle comme une erreur d'étiquetage (il comptait un succès).
- Preuves (intégration PostgreSQL, coureur de production, seul le fournisseur d'IA simulé) — `AiTaggingRecoveryTests` :
  mail en échec repris après le délai ; mail répondu sans étiquette jamais repris ; arrêt au premier échec puis reprise
  de tous après un nouveau délai ; fenêtre et exclusions (ancien, envoyé, brouillon, en-têtes seuls — ces trois derniers
  jamais mis en attente) ; même matière que la voie nominale ; migration sans réécriture et index partiel.
- Mutations (restaurées par écriture des octets d'origine + `touch`), toutes rouges sur leur assertion :
  M6 échec marqué étiqueté → `Tagged = 2` au lieu de `Failed = 1` ; M7 pas d'arrêt au premier échec → `Failed = 0` ;
  M8 délai ignoré → `Expected 0 / Actual 1` ; M9 historique non marqué (première version) → `Assert.NotNull` ;
  M9′ envois mis en attente → `Assert.Null` sur la date d'attente ; M10 envois non exclus → `Candidates = 2` ;
  M11/M12 déclencheur absent → `ScheduleAsync` jamais reçu.
- Tests unitaires : `AiTaggingRecoveryServiceTests` (8), `MailAutoTaggerTests` (3), `AiTaggingRecoverySchedulerTests` (4),
  `ImapServiceEnrichmentCoverageTests` (+1), `AddNewMailConsumerTests` (+1, marqueur affirmé sur 3 tests) ; tests du
  service de suggestion durcis (`Failed` affirmé).
- Effet de bord sur les tests de task-344 : `MailPromotionUniquenessTests` arrêtait la base avant sa migration puis
  écrivait avec le modèle EF courant (colonnes des migrations suivantes absentes) — montage refait : schéma complet,
  état antérieur recréé en SQL, migration rejouée seule. M3 re-prouvée rouge sur ce montage.
- Local build / test : ✓ — 6 338 réussis, 16 ignorés, 0 échec.
- Passe qualité (/simplify, 4 angles) : appliqué — déclencheur, marqueur unique, matière partagée, paramètre resserré,
  horloge de test partagée (`MutableTimeProvider`), compteur. Écarté (noté pour `/review`) : simplification du compte
  rendu `AiTaggingRecoveryReport` ; mise en ligne de `ProcessAutoTaggingAsync` ; alignement de
  `BackgroundEnrichmentProcessor` (n'envoie ni type de document ni corps HTML converti — écart antérieur, l'aligner
  changerait les consignes envoyées au modèle) ; relance propre au tagging dans le consommateur (les relances du bus
  rejouent l'étiquetage quand l'embedding échoue).
- Contrôles mécaniques §Q 2b : S125 ×2 attrapés et réécrits (commentaires « … ; … ») — compteur incrémenté.

## Sonar log

- Mode A (chaîné), branche `feat/task-344-promotion-unique-mail`, serveur SonarQube 9.9.8 (`sonar.login`), période de nouveau code : 30 jours.
- **Analyse 1** (`503540c0`) : Quality Gate **OK**, aucun constat sur le code de la task. Deux constats « nouveau code » hors task :
  - **S3925** `IheXdmTechnicalFailureException` (task-333) — triplet de constructeurs présent ; marqué **FALSE-POSITIVE**
    avec motif, selon la consigne S3925 de `conventions/csharp.md` (la règle réclame le constructeur `ISerializable`, obsolète SYSLIB0051).
  - **S107** `SemanticSearchService:395` — antérieur (task-329), hors du code de la task, accepté comme aux cycles précédents.
  - Couverture : une condition non couverte **du diff** — `m.Category?.Type` dans le helper d'étiquettes extrait par la passe
    qualité : branche morte (la catégorie est déjà lue par `CreateMedicalDocumentEntity`). Retirée → `c1a2dc9b`
    `fix(sonar/new)`. Les autres lignes non couvertes de `MailRepository` / `ImapService` sont hors des hunks de la task.
- **Analyse 2** (`c1a2dc9b`) : Quality Gate **OK** ; nouveau code : seul S107 (antérieur) ; `MailPromotionClaim` 100 %.
- Phase 1 (new code) : ✓ — 1 itération, 1 correction (condition morte), 1 faux positif documenté, 0 test ajouté.
- Phase 2 (legacy) : **0 itération** — les 13 constats restants sont structurels et antérieurs (S107, CA1829 dans des
  tests de 2026-03), comme aux cycles précédents ; acceptés en best-effort.
- Build / tests : ✓ green — Debug 6 315 réussis / 16 ignorés ; sous OpenCover (Release) : analyse 1 toute verte,
  analyse 2 **un rouge intermittent dans `mss.mail.integration.tests` (814/815), non identifié** : le script d'analyse ne
  gardait que les lignes de synthèse. Deux rejeux de la suite d'intégration (Release, puis Release + OpenCover) : 815/815.
  Aucun nom de test n'est avancé faute de trace. Le script garde désormais les lignes `[FAIL]`.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 97,5 % | 97,5 % | 0 |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 13 | 13 | 0 |
| Coverage (projet) | 97,9 % | 97,9 % | 0 |
| Duplication | 0,4 % | 0,4 % | 0 |
| Reliability / Security / Maintainability | A / A / A | A / A / A | → |

### Extension — analyse 3 (`577c3f4b`, reprise des étiquetages IA)

- Quality Gate **OK** ; nouveau code : seul S107 `SemanticSearchService:395` (antérieur, task-329) ; aucun point chaud.
- KPIs inchangés : bugs 0, vulnérabilités 0, code smells 13, coverage 97,9 %, new coverage 97,5 %, duplication 0,4 %, A/A/A.
- Couverture des fichiers ajoutés : `AiTaggingRecoveryScheduler`, `MailAutoTagger`, `AiTaggingMaterial` 100 % ;
  `AiTaggingRecoveryService` 96,2 % — deux conditions (`??` sur objet et expéditeur absents) couvertes par
  `RecoverAsync_AMailWithoutSubjectNorSender_IsTaggedOnItsBodyAlone` (`ce3ea356`, test seul : pas de réanalyse, aucun
  code de production modifié).
- Suites sous OpenCover (Release) : toutes vertes (821 + 16 ignorés en intégration).

## Lint log

- `/lint-angular` : **skipped** — `client-angular` absent des `**Repos**`, aucun code Angular écrit par la task. L'arbre
  `Client/Angular` (`feature/nova-rewriting-mss`) porte 5 modifications non commitées **antérieures et étrangères à
  task-344** (2 `environment.ts` locaux, et les fichiers de réglages de la part code-only de task-351, en attente du
  commit TFS humain) : non lintées ici, non touchées.
- `/lint-mobile` : **skipped** — `client-mobile` absent des `**Repos**`, arbre `Client/Mobile` propre sur `develop`.

## E2E log

### Rejeu sur le code final (`657d19cc`, reprise des étiquetages IA comprise)

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail touché | ✅ verte | 30 verts, 0 flaky, 0 rouge, 0 quarantaine | ~4 min |
| angular | api-mail touché | ✅ verte | 30 verts, 0 flaky, 0 rouge, 0 quarantaine | ~4 min |

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte (porte `gate` code 0, catalogue de la branche).
Joué deux fois après l'extension (`ce3ea356` puis `657d19cc`), vert les deux fois. Démontage complet. Matrice identique au premier passage ci-dessous.

### Premier passage (`c1a2dc9b`)

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail touché | ✅ verte | 30 verts, 0 flaky, 0 rouge, 0 quarantaine | 5 min 04 s |
| angular | api-mail touché | ✅ verte | 30 verts, 0 flaky, 0 rouge, 0 quarantaine | 4 min 12 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task (`feat/task-344-promotion-unique-mail`, inchangé par la task)
- Backend e2e construit depuis le checkout courant d'`Api/Mail` (branche de la task) ; `Client/Mobile` sur `develop`, à jour d'`origin/develop` ; `Client/Angular` sur `feature/nova-rewriting-mss` (branche de l'humain)
- Quarantaines : aucune
- Divergences ouvertes : aucune
- Parcours touchés sans spec e2e modifié : aucun (aucun écran touché — task backend)
- Démontage : complet (ports 5052/8100/4200/3993/3465/3143 libres, aucun conteneur `e2e-dovecot-*` / `e2e-greenmail-*` résiduel)

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
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
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
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/278 — label `awaiting-human-merge`
  (commits `b99c17c3`, `79b05cbc`, `503540c0`, `c1a2dc9b` ; `develop` n'avait pas bougé : aucun merge nécessaire)
  — extension (reprise des étiquetages IA) : `8c52c6f0`, `577c3f4b`, `ce3ea356`, `657d19cc` ; titre et corps de la PR mis à jour
- `dtos-mss` : aucune branche (aucun contrat touché)

## Code Review Summary

**Verdict : APPROVED** — 0 bloquant, 6 suggestions. Validation `/review` : build 0 erreur ; tests 6 315 réussis,
16 ignorés (identiques sur develop), 0 échec.

### DOD

| Critère | Statut | Preuve |
|---|---|---|
| Build + tests | ✓ | 0 erreur ; 190 / 683 / 1 176 / 3 451 / 815 (+16 ignorés) |
| Comportement transactionnel actuel consigné | ✓ | section dédiée, relevée avant correctif |
| Test rouge d'abord, course de deux réplicas | ✓ | `TwoReplicasPromotingTheSameHeaderOnlyMail_…` — rouge consigné (2/2/4/2) |
| Perdant sans erreur, contenu existant servi | ✓ | `TheLoserOfThePromotionRace_IsServedTheWinnersContent` (rouge sur develop : 23505 remonté) |
| Échec en milieu de promotion → rien écrit | ✓ | `APromotionFailingAfterItsDocuments_…` (rouge sur develop) |
| Second réplica, verrou tenu → ni fetch ni analyse | ✓ | HTTP `EnrichingAMail_WhoseAnalysisAnotherReplicaHasClaimed_…` (mutation : mail analysé) |
| Migration auditée (7c) | ✓ | relue, sans opération fantôme, `HasMigrationsToApplyUp() == false` affirmé |
| Test de migration (doublons, plus ancien gardé, accusés préservés, index unique) | ✓ | `Migration_OnABaseWithHistoricalDuplicates_…` + 3 mutations rouges |
| Non-régression task-079 / 228 / 293 | ✓ | `EnrichmentLockInterleavingTests`, `EnrichmentPartialBatchFailureTests`, `EnrichmentScratchFailureTests`, suites d'`ImapService` vertes |
| Aucune INS, contenu CDA ni corps dans les logs | ✓ | journaux ajoutés : UID, dossier, MailId, nombres |

### Verrou intégration (règle 1b) — comportement → test → preuve rouge

| Comportement | Test | Preuve rouge |
|---|---|---|
| Une seule promotion sous course de deux réplicas | `MailPromotionUniquenessTests.TwoReplicasPromoting…` (dépôt réel + PostgreSQL du coureur de production) | develop : 2 contenus, 2 documents |
| Le perdant ne rend pas d'erreur, sert le contenu du gagnant | `TheLoserOfThePromotionRace_…` (relu par `GetMailsByUidsAsync`) | develop : 23505 ; mutation M4 : 23505 |
| Promotion atomique | `APromotionFailingAfterItsDocuments_…` | develop : contenu committé |
| Le second réplica ne fetche ni n'analyse ; `inProgressElsewhere` dans la réponse | `ArchiveAnalysisMarkerEndToEndTests.EnrichingAMail_WhoseAnalysisAnotherReplicaHasClaimed_…` (HTTP, Dovecot, extraction, PostgreSQL) | mutation M5 : `analysed` 1 au lieu de 0 |
| Résorption des doublons historiques | `Migration_OnABaseWithHistoricalDuplicates_…` (coureur de production) | M1 accusé perdu, M2 lien perdu, M3 index impossible |

⚠️ **Écart assumé, soumis à l'humain** : les trois premiers comportements sont prouvés **au dépôt** sur la vraie
base, pas à travers HTTP. Deux requêtes sur un même hôte de test sont sérialisées par le verrou de persistance en
processus : la course n'existe qu'entre deux processus, et l'atomicité exige d'injecter une panne entre deux
commandes SQL. La DOD prescrit explicitement ce test à deux contextes. Rien n'est simulé de la couche modifiée.
Le comportement exposé par l'endpoint (`enrich/sync`, second réplica) est, lui, prouvé par HTTP.

### Revue de code (api-mail)

- `Migrations/MailDb/20261005120000_UniqueMailContentPerMail.cs` — ✅ résorption restreinte aux mails promus plusieurs
  fois, sonde `EXISTS` sans table temporaire dans le cas courant, index unique créé avant suppression de l'ancien.
- `Repositories/MailDb/MailRepository.cs` — ✅ transaction unique ; violation reconnue par **nom** d'index, jamais par
  heuristique ; journal d'erreur supprimé pour la seule course perdue.
- `Services/Implementation/MailPromotionClaim.cs` — ✅ ne libère que ce qu'il a pris ; Redis en panne n'arrête rien.
- `Services/Implementation/ImapService.cs`, `Models/EnrichmentOutcome.cs`, `MailController.cs` — ✅ revendication
  rendue sur tous les chemins (`await using`), compte distinct, non relancé.
- Brouillons (`UpdateDraftMailAsync`, troisième écrivain de `MailContents`) — ✅ lit puis met à jour, n'ajoute qu'en
  l'absence de ligne : compatible avec l'index.
- Arrivée cross-réplica : le backplane SSE Redis de task-343 est sur develop — l'événement d'analyse du réplica A
  atteint l'appareil servi par B.

### Suggestions (non bloquantes)

1. **Effets de bord du perdant** dans la course résiduelle (revendication expirée, chemin de fond) : `AddNewMail` rend
   un `Guid`, l'appelant publie sur le bus, notifie, audite et compte `Analysed` comme s'il avait promu. Un résultat
   typé (`Inserted | Promoted | AlreadyPresent`) le corrigerait — changement de contrat, à instruire par une task.
2. **Chemin de synchronisation de fond** (`BackgroundImapService` → `BackgroundEnrichmentProcessor`) : ni
   revendication ni verrou de persistance ; la garantie en base le couvre, pas l'économie.
3. **Brouillons** : deux enregistrements automatiques simultanés du même brouillon sont désormais refusés par
   l'index (avant : seconde ligne silencieuse). La migration garde la ligne la plus ancienne d'un brouillon dédoublé.
4. **Revendications groupées** en un script Lua (2 commandes Redis par lot au lieu de 2 N) — à mesurer au banc.
5. **Rouge intermittent non identifié** dans `mss.mail.integration.tests` sous OpenCover (1 run sur 4, nom perdu) :
   à surveiller ; le script d'analyse garde désormais les lignes `[FAIL]`.
6. Constante de 3 minutes non partagée avec le verrou de fetch.

### Amélioration continue

- Leçon : un verrou de processus pris pour une garantie entre réplicas, et un correctif d'atomicité (AUD-36) posé sur
  un chemin d'écriture sans son jumeau → **`conventions/csharp.md`, entrée `unicite-garantie-par-la-base`**.
- Leçon d'outillage : un script d'analyse qui ne garde que les lignes de synthèse perd le nom d'un rouge
  intermittent → filtre `[FAIL]` ajouté au script de la session ; à reporter dans `agents/sonar.md` (commande de test
  sous couverture : garder `[FAIL]`).

### Extension — reprise des étiquetages IA (revue du 2026-10-04)

**Verdict : APPROVED** — 0 bloquant. Validation : build 0 erreur ; 6 340 réussis, 16 ignorés, 0 échec (`657d19cc`).

| Critère (DOD extension) | Statut | Preuve |
|---|---|---|
| La suggestion distingue « aucune étiquette » de « échec » | ✓ | `TagSuggestionOutcome` ; tests du service durcis (`Failed` affirmé) |
| Marqueur d'attente posé à l'enregistrement, effacé à la réponse du modèle | ✓ | un seul marqueur `AiTaggingPendingSince` (passe qualité : remplace les deux marqueurs prévus, même contrat) ; `AiTaggingRecoveryTests` |
| Reprise : < 7 jours, analysés, > 15 min, arrêt au premier échec, flags, exclusions | ✓ | `AiTaggingRecoveryTests` (5) + `AiTaggingRecoveryServiceTests` (9) ; mutations M6–M10 rouges |
| Migration : historique **non** repris, index partiel, 7c | ✓ | `Migration_LeavesTheHistoryAlone_AndInstallsThePendingIndex` ; aucune réécriture de ligne ; `HasMigrationsToApplyUp() == false` |
| Une panne de la reprise ne casse rien | ✓ | planification hors requête (file de fond), Redis en panne → rien de programmé (`AiTaggingRecoverySchedulerTests`) |
| Aucune donnée de santé dans les journaux | ✓ | journaux : identifiant technique, nombres, type d'exception |

**Écart par rapport à la DOD de l'extension, à faire valider** : la DOD disait « reprise en fin de synchronisation de
fond ». La passe qualité a montré que la synchronisation complète ne part que du bouton du praticien ; la reprise est
donc **programmée par chaque enrichissement** (au plus une passe par boîte toutes les 10 min). Le but de la DOD — que
la reprise ait lieu — n'était pas atteignable avec le déclencheur qu'elle nommait.

**Revue de code** : ✅ `MailAutoTagger` (best-effort, annulation propagée) ; ✅ `AiTaggingRecoveryService` (matière
partagée, arrêt au premier échec) ; ✅ `AiTaggingRecoveryScheduler` (identité recopiée avant construction de la portée —
durci en revue, `657d19cc`) ; ✅ requête de reprise servie par l'index partiel dans son ordre ; ✅ migration sans
réécriture.

**Suggestions (non bloquantes)** :
1. `BackgroundEnrichmentProcessor` publie sans type de document ni corps HTML converti : les mails analysés par la
   synchronisation complète reçoivent une consigne moins précise que ceux de la voie interactive (écart antérieur).
2. Les relances du bus rejouent l'étiquetage quand l'embedding échoue (un appel au modèle et une notification de plus) ;
   l'étiquetage gagnerait à avoir son propre message.
3. Un mail dont l'étiquetage échoue durablement reste en attente après la fenêtre de 7 jours (hors reprise, mais dans
   l'index) : borné aux échecs, à purger si la mesure le demande.


## Merged

- **Date** : 2026-10-04, `/merge task-344 --i-tested` (validation humaine attestée).
- `api-mail` : PR #278 squash-mergée sur `develop` → `cbe15a2397828c5a5bfe4934975f2fccd5a05c8e`. Label `awaiting-human-merge`
  retiré, branche `feat/task-344-promotion-unique-mail` supprimée (distante et locale), clone revenu sur `develop`.
  Aucune branche `dtos-mss` (aucun contrat touché).
- CI `develop` : ❌ **rouge** — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/37233705234
  - Cause : conflit **sémantique** avec task-341 (#279, mergée 18 min avant). Elle a ajouté
    `TaggingInvalidResponseLogHygieneTests` sur l'ancien contrat de `SuggestTagsAsync`, que #278 remplace par
    `TagSuggestionOutcome` → `CS1503` ×2. Aucun fichier commun : aucun conflit git, PR annoncée `CLEAN` / `MERGEABLE`
    avec un commit de retard.
  - Correctif : PR [#280](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/280)
    (`awaiting-human-merge`), deux lignes de test ; validé sur `develop` + correctif : 6 368 réussis, 0 échec.
  - Détail et prévention proposée : `questions/merge-task-344.md`.
- Branche staging : aucune (task lancée par `/start`, hors run `/forge`).
