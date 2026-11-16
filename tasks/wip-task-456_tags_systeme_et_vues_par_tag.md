# todo-task-456.md — Tags système et vues par tag : biologie, patient, professionnel de santé, pour info

**Repos**: api-mail, dtos-mss, client-angular, client-mobile, api-mcp
**Dependencies**: aucune
**Epic**: E024

> **Mise à jour du 2026-11-12 (décision humaine)** : task-465 (mesure de charge) est **abandonnée** — traitement jugé trop lourd pour l'API. La dépendance et les indicateurs de tableau de bord qu'elle portait sont retirés. L'extraction des usages sera reprise plus tard par un **cron job hors de l'API**, sur la base d'un rapport journalier.

> **Réécriture du 2026-11-16 (décision humaine).** La « nature » (une colonne, une valeur par message, une vue
> par nature) est **abandonnée au profit des tags**, qui existent déjà : table `MailTags` posée sur le mail, vues
> `tag:XXX` avec compteur SQL, actes d'audit `TagAdded` / `TagRemoved`, affichage dans les deux clients. Ajouter
> une notion parallèle aurait doublé le modèle, les routes, le contrat et l'interface. Décisions :
> - **plusieurs tags par message** : un compte rendu de biologie d'un laboratoire porte « Biologie » et
>   « Professionnel de santé » ;
> - **les vues par tag montrent aussi les messages lus**, avec un filtre « Tous / Non lus » dont le dernier choix
>   est retenu dans les réglages de la personne ;
> - **plusieurs tags se combinent** : « Urgent » + « Professionnel de santé » montre les messages qui portent les
>   deux ;
> - un tag système **« Professionnel de santé »** isole les messages des professionnels, par opposition aux
>   patients ;
> - « Courriers et comptes rendus » disparaît : c'est la Boîte de réception sans « Pour info », ou le tag
>   « Professionnel de santé ».
>
> La saisie des tags (espaces acceptés, liste de choix) est sortie dans **task-486**.
> Fichier renommé le 2026-11-16 sur demande humaine (ancien titre : « vues par nature biologie courriers patients
> pour info »), par exception à la règle du titre fixé à la création.
> Maquette : https://claude.ai/artifact/ShvbxicNzVTzK3EdyG1u7V

**Priorité**: EPIC E024, demandée par l'humain le 2026-11-11. Douleur n° 7 (2/5). Ce sont les messages générés
par des machines qui pèsent le plus sur la charge du médecin (Tai-Seale, Health Affairs 2019).

> **Origine.** `Docs/analyse-fonctionnelle-manques-messagerie-2026-11.md`, manques B1 et B2 (HEY Imbox / Feed / Paper
> Trail, onglets Gmail, Apple Mail, Superhuman Split Inbox). Nom « Pour info » validé par l'humain le 2026-11-11.
>
> **Reprise du 2026-11-12 (décision humaine).** Cette US passe **avant** task-454 : le tag « Pour info » décide quels
> messages entrent dans « À traiter ». Ses vues portent un compteur de **non lus** ; le compteur « à traiter » par vue
> et le traitement groupé passent à task-454.

## Ce qui est établi

- **Les tags sont posés sur le mail** : `MailTags` (`MailId`, `TagId`, contrainte unique sur le couple), `Tags`
  (`Code` unique, `Name`, `Type`, `ColorCode`). Un mail porte plusieurs tags.
- Trois types aujourd'hui : `USER` (posé à la main), `AI` (priorité clinique « Très urgent » / « Urgent » /
  « Important », posée par `EmailTaggingService` avec `UrgencyLevel`), `CATEGORY` (**code mort** :
  `AddCategoryTagsToMailAsync`, sans appelant, `MailRepository.cs:3940`).
- **La biologie n'est pas un tag** : elle est portée par le **document**, `MailMedicalDocument.Category` (`DocumentType`
  Bio…), calculée à l'ingestion (`CdaParsingService`, `HprimMedicalDocuments`).
- Un message patient se reconnaît à l'expéditeur `@patient.mssante.fr` (`PatientMessageHelper`). `MailDto.IsFromPatient`
  est calculé à la volée, sans colonne. L'espace de confiance MSSanté est le suffixe `.mssante.fr`
  (`AutoconfigService.TrustedDomainSuffix`).
- **Vues par tag** : `GetTagFoldersAsync` compte les non lus par tag en une requête groupée (task-430) ;
  `GET tags/{tagcode}/emails` rend les UID **non lus seulement**, puis `GET tags/{tagcode}/emails/{uids}` les hydrate.
  Un tag sans non lu n'a pas de dossier.
- `AddTagToMailAsync` réutilise un tag existant de même code (`NormalizeTagCode` : majuscules, sans accents). Un tag
  saisi « patient » avant la création du tag système deviendrait un tag `USER`.
- Ajout et retrait d'un tag sont tracés au nom de la personne : `[Audited(TagAdded)]`, `[Audited(TagRemoved)]`
  (`MailController.cs:1776`, `:1826`).
- Les deux clients ont déjà un filtre « Tous / Non lus » sur la liste (mobile : `ion-segment` d'`inbox.page` ;
  weda2 : bouton « Non lus » de la liste). Les réglages de la personne vivent dans `UserSetting.SettingsJson`.

## Objective

La Boîte de réception se lit **par tags**. Quatre tags système sont posés à l'arrivée de chaque message ; le
praticien ouvre une vue par tag, y voit les messages lus et non lus, filtre sur les non lus s'il le veut, et combine
plusieurs tags pour affiner. Le tag « Pour info » est aussi le critère de sortie de « À traiter » (task-454).

Règles :
- **Quatre tags système**, de type `SYSTEM`, créés par la migration (donc présents avant tout tag utilisateur de
  même code) :
  1. **Biologie** : le message porte au moins un document de biologie (CDA LOINC 11502-2 ou HPRIM).
  2. **Patient** : l'expéditeur est un patient (`@patient.mssante.fr`, Mon espace santé).
  3. **Professionnel de santé** : l'expéditeur est une adresse de l'espace de confiance MSSanté (suffixe
     `.mssante.fr`) qui n'est pas une adresse patient. Une BAL organisationnelle (établissement, service) en fait
     partie en v1.
  4. **Pour info** : la boîte n'est qu'**en copie** (absente de « À ») ; ou message **automatique** (`Auto-Submitted`
     autre que `no`, `List-Id`, `Precedence: bulk` ou `list`) ; ou avis technique (rapport de distribution, accusé de
     lecture, jusqu'à task-460 qui les rangera sous le message d'origine).
- **Plusieurs tags par message**, sans ordre de priorité. Exemples : laboratoire → Biologie + Professionnel de santé ;
  patient qui envoie un résultat de biologie → Biologie + Patient ; compte rendu reçu en copie → Professionnel de
  santé + Pour info ; lettre d'information de l'Assurance Maladie hors MSSanté → Pour info seul.
- **Calcul une fois par message**, à l'arrivée (`AddNewMailConsumer` ; le tag Biologie au chemin d'enrichissement,
  qui parse les documents), tracé en **acte système**. Le message garde la marque de ce calcul : **un tag système
  retiré à la main ne revient jamais**, ni au rattrapage, ni à un ré-enrichissement.
- **Messages existants** : rattrapage à la première ouverture de la boîte après la mise à jour, sans action du
  praticien, sur les seuls messages jamais calculés ; acte système.
- **Le praticien corrige** en retirant ou en posant un tag système comme n'importe quel tag. Le geste est imputé
  (`TagAdded` / `TagRemoved`) et se lit dans le journal de la boîte, au nom de son auteur (règle 14).
- **Vues par tag**, pour **tous** les tags (système, IA, utilisateur) :
  - elles montrent les messages **lus et non lus** de la Boîte de réception, en pages servies par le serveur, du plus
    récent au plus ancien ;
  - un filtre **« Tous / Non lus »** en tête de liste. **Un seul réglage pour toutes les vues par tag**, retenu
    dans les réglages de la **personne** (`UserSetting`) : le dernier choix revient à la prochaine ouverture. Défaut :
    « Tous » ;
  - le **compteur** d'un tag reste celui des **non lus**, quel que soit le filtre ;
  - un tag système est toujours affiché, même à zéro ; un tag IA ou utilisateur est affiché tant qu'il porte au
    moins un message de la Boîte de réception, lu ou non.
- **Combinaison** : le praticien sélectionne plusieurs tags ; la vue montre les messages qui portent **tous** les
  tags sélectionnés (intersection). L'en-tête de la vue nomme la combinaison et son nombre de messages.
- **Où** :
  - weda2 : les quatre tags système en tête de la section « Tags », dans l'ordre Biologie, Patient, Professionnel
    de santé, Pour info, puis les tags IA, puis les tags utilisateur. Un clic sur un tag ouvre sa vue ; une case à
    cocher à côté de chaque tag l'ajoute à la combinaison ;
  - mobile : une rangée de puces de tags au-dessus de la liste de l'Accueil et de la Boîte de réception (tags
    système d'abord, défilement horizontal). Une puce s'active et se relâche au toucher ; plusieurs puces actives se
    combinent. Aucune puce active = toute la Boîte de réception. Elles **remplacent** le regroupement local
    « BIOLOGIE À VALIDER / AUTRES MESSAGES » d'`inbox.page`.

### Hors périmètre

- La saisie des tags (espaces, longueur, liste de choix) : task-486.
- Distinguer un professionnel (BAL personnelle) d'un établissement (BAL organisationnelle) par l'Annuaire Santé.
- La combinaison en « OU » ; les règles de tri définies par l'utilisateur.
- Les autres dossiers de réception : la v1 couvre la Boîte de réception.
- Le regroupement visuel des notifications d'un même expéditeur sur une ligne.
- L'état « traité », le compteur « à traiter » par vue et le traitement groupé : task-454.

## Definition of Done

- [ ] Migration FluentMigrator : les quatre tags `SYSTEM` créés ; marque de calcul des tags système par message ;
      audit de migration (règle 7c).
- [ ] Calcul à l'ingestion (`AddNewMailConsumer` et chemin d'enrichissement) et rattrapage des messages existants,
      en acte système ; un tag système retiré à la main n'est pas reposé.
- [ ] Code mort `AddCategoryTagsToMailAsync` réutilisé ou retiré (justifié dans le `## Develop log`).
- [ ] Contrat : `TagDto.Type` porte `SYSTEM` ; vue paginée par tag(s) avec filtre `all` / `unread` (par exemple
      `GET api/v1/Mail/tags/emails?tag=…&tag=…&filter=all&page=…`) ; réglage du filtre dans les réglages de la
      personne ; `TagDto` et `FolderDto` (dtos-mss) publiés (`/publish-dtos`) ; miroirs TypeScript (weda2, mobile). Les anciennes routes `tags/{tagcode}/emails` et
      `tags/{tagcode}/emails/{uids}` retirées une fois les deux clients migrés ; impact api-mcp vérifié
      (`Tools/contracts/mcp_impact.py check`).
- [ ] Tests unitaires de la règle des tags système : un test par tag ; copie seule → Pour info ;
      `Auto-Submitted: auto-generated` → Pour info ; laboratoire → Biologie + Professionnel de santé ; patient
      porteur d'une biologie → Biologie + Patient ; confrère sans document → Professionnel de santé seul ; expéditeur
      hors `.mssante.fr` → ni Patient ni Professionnel de santé.
- [ ] **Test d'intégration de bout en bout (règle 1b)** sur la vue par tags : un jeu de messages lus et non lus ;
      la vue d'un tag rend lus et non lus avec `filter=all`, les seuls non lus avec `filter=unread` ; la combinaison
      de deux tags rend l'intersection ; le compteur du dossier `tag:` reste celui des non lus ; un tag système retiré
      n'est pas reposé par le rattrapage. Cas d'échec : tag inconnu → 404, filtre inconnu → 400, en `ProblemDetails`.
      Vu rouge.
- [ ] **Test d'intégration du réglage** : la personne choisit « Non lus », relit son réglage ; une autre personne de
      la même boîte garde « Tous ».
- [ ] **Deux personnes sur la même boîte** : le délégataire retire « Pour info » d'un message, le titulaire ne le
      voit plus dans la vue « Pour info », et le journal impute `TagRemoved` au délégataire.
- [ ] Tests de composant (weda2 et mobile), vus rouges par mutation : vues par tag, filtre retenu, combinaison,
      puces mobiles.
- [ ] **Scénarios e2e**, mobile et angular requis, vus rouges :
      - `E2E-TAG-002` v1 : le compte rendu de biologie est dans « Biologie », le message du patient dans « Patient »,
        une copie dans « Pour info », chacun avec son compteur de non lus ; un message lu reste dans sa vue ;
      - `E2E-TAG-003` v1 : « Biologie » + « Professionnel de santé » combinés ne montrent que les messages portant
        les deux ; le filtre « Non lus » choisi revient à la réouverture.
- [ ] `data-testid`, conventions de libellés, aucune donnée de santé dans les libellés ni les logs.
- [ ] Build et tests verts (api-mail, weda2, mobile) ; client-angular : code-only.

## Manual Test Plan

1. Backend et weda2 lancés sur la boîte de formation de Virginie (corpus réel : comptes rendus, biologie, copies).
2. Section « Tags » : Biologie, Patient, Professionnel de santé, Pour info en tête, avec leurs compteurs de non lus,
   puis les tags IA et utilisateur.
3. Ouvrir « Biologie » : les comptes rendus de biologie lus et non lus. Passer le filtre sur « Non lus » : seuls les
   non lus restent. Fermer weda2, le rouvrir, rouvrir « Biologie » : le filtre est toujours sur « Non lus ».
4. Ouvrir « Pour info » : seuls des messages où la boîte est en copie, des messages automatiques ou des avis
   techniques.
5. Cocher « Urgent » puis « Professionnel de santé » : seuls les messages portant les deux tags ; l'en-tête nomme
   la combinaison.
6. Sur un message de « Pour info », retirer le tag « Pour info » : il quitte la vue ; le journal de la boîte dit qui
   l'a retiré. Rouvrir la boîte : le tag n'est pas revenu.
7. Mobile : les puces au-dessus de la liste, mêmes compteurs que weda2 ; activer deux puces combine les tags.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — organisation du travail
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : inchangée — PSC (e-CPS), eIDAS substantiel
- **Habilitations** : titulaire, membre, délégataire, sous verdict de l'opérateur (règle 14)
- **Interop CI-SIS** : lecture des catégories de documents CDA R2 (LOINC du type de document) et HPRIM, inchangée
- **Tracé PGSSI-S** : `TagAdded` / `TagRemoved` au nom de la personne ; calcul des tags système et rattrapage en
  acte système ; `HealthDataAccess`, 3 653 jours
- **Consentement patient** : non applicable
- **Référentiels métier** : LOINC (types de documents)
- **Hébergement HDS** : oui — base de la boîte (tags et vues) ; réglage du filtre dans les réglages de la personne
- **AIPD / impact RGPD** : inchangé — aucune donnée nouvelle sur le patient

## Branches
- `api-mail` (pushed) : feat/task-456-tags-systeme-et-vues-par-tag — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-456-tags-systeme-et-vues-par-tag
- `client-mobile` (pushed) : feat/task-456-tags-systeme-et-vues-par-tag — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-456-tags-systeme-et-vues-par-tag
- `dtos-mss` (paresseuse, créée par /develop) : feat/task-456-tags-systeme-et-vues-par-tag — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-456-tags-systeme-et-vues-par-tag (NuGet 614.0.0)
- `api-mcp` (paresseuse, créée par /develop, `mcp_impact.py check` Step 4c) : feat/task-456-tags-systeme-et-vues-par-tag — https://github.com/codengine-technologies/HealthPlatform.Api.Mcp/tree/feat/task-456-tags-systeme-et-vues-par-tag
- `client-angular` (code-only) : la forge écrit sur la branche checked out dans `Client/Angular/` (au /start : `feature/nova-mss-weda-integration`) — humain gère branche, commit, push, PR TFS. ⚠️ L'arbre porte encore les 9 fichiers non commités de task-486 (saisie des tags) : task-456 les modifie à son tour ; les commiter vers TFS avant celles de task-456 garde deux lots lisibles.

## Develop log

- Repos touched : `dtos-mss` (branche paresseuse, NuGet 614.0.0), `api-mail`, `api-mcp` (branche paresseuse, Step 4c),
  `client-mobile` (pushés), `client-angular` (code-only, non commité sur `feature/nova-mss-weda-integration`).
- Commits :
  - dtos-mss : `ea1af9f` feat(dto): `MailDto.IsAutomatic`, `FolderDto.TagType`, `UserSettingsDto.TagViewFilter`
    (`TagViewFilterType { All, Unread }`, défaut `All`), publié par la CI en **614.0.0** ;
  - api-mail : `d5e8959d` bump Dtos 614.0.0 ; `d5454ba7` feat(mail): tags système et vues par tag (passe qualité
    incluse) ;
  - api-mcp : `ac95965` feat(mcp): list_folders écarte les dossiers de tag ;
  - client-mobile : `7457f06` feat, `1b6a90b` test(e2e) E2E-TAG-002/003, `66018c5` refactor (passe qualité) ;
  - client-angular (non commité, à commiter par l'humain vers TFS, **après** les 9 fichiers de task-486) : modèles
    `folder` / `mail` / `user-settings`, `mss-api.service.ts` (`getTagViewPage` ; `getEmailsByTag` et `getMailsByTag`
    retirés), services `mail-state` / `mail-event`, composants `mail-list`, `mail-folder-list`, `mail-folder-item`,
    `mss-mail`, `mail-widget` ; specs créées `mss-api.tag-view.service.spec.ts`, `mail-state.service.tag-view.spec.ts`,
    `mail-list.tag-view.spec.ts`, `mail-folder-list.tags.spec.ts`, `mss-mail.component.tag-view.spec.ts`,
    `mail-widget.component.spec.ts` ; e2e `functional.e2e.ts` (E2E-TAG-002/003) et `e2e-backend.ts`.

### api-mail
- **`SystemTagRule`** (Domain) : les quatre tags (`BIOLOGIE` #0E7490, `PATIENT` #7C3AED, `PROFESSIONNEL DE SANTE`
  #15803D, `POUR INFO` #6B7280), un bit chacun.
  - Patient : adresse en `@patient.mssante.fr`.
  - Professionnel de santé : suffixe `.mssante.fr`, hors adresse patient.
  - Pour info : la boîte n'est qu'en copie, ou le message est automatique (`Auto-Submitted` ≠ `no`, `List-Id`,
    `Precedence: bulk|list`), ou c'est un avis technique.
  - Biologie : un document de type « Bio », casse indifférente (ingestion et rattrapage comparent de la même façon).
- **Migration `AddSystemTags` (20261116232800)** : heure réelle, après `20261116203100` (WidenTagNames, dernière
  d'`origin/develop`).
  - Colonnes `Mails.SystemTagsDecided int` (marque de décision, un bit par tag) et `Mails.IsAutomatic bool` ; index
    partiel `IX_Mails_SystemTagsPending` (`SystemTagsDecided <> 15`).
  - Les quatre tags `SYSTEM` posés par upsert sur `Code` (un tag utilisateur de même code devient système) ; tags
    `CATEGORY` supprimés.
  - Descente : colonnes et index retirés, `SYSTEM` → `USER`.
  - Audit 7c : migration lue, aucune opération fantôme ; `MailDataContext` déclare colonnes et index (FluentMigrator :
    ni snapshot ni `.Designer`). « Professionnel de santé » (22 caractères) tient grâce au `varchar(40)` de task-486.
- **Décision une fois par message**, sur la Boîte de réception seulement :
  - à l'insertion : Patient, Professionnel de santé et Pour info depuis les en-têtes ; Biologie si le contenu est là ;
  - à la promotion d'un message lu d'abord en en-têtes seuls : Biologie.
  - Un bit décidé ne se redécide jamais : **un tag retiré à la main ne revient pas**. La marque s'écrit par un `OU` bit
    à bit en SQL (atomique face au rattrapage), avec un repli par suivi d'entités pour le fournisseur en mémoire des
    tests unitaires.
  - Chaque pose est tracée `TagAdded` en **acte système** (`IsSystemAct`), sans donnée de santé : UID, dossier,
    Message-Id, codes des tags.
- **Rattrapage** : `SystemTagsRecoveryService` (lots de 200, 50 lots au plus), planifié par
  `SystemTagsRecoveryScheduler` (verrou Redis par boîte, toutes les 10 min, file `system-tags-recovery`) après
  l'ouverture de la boîte, comme le rattrapage du marquage IA (task-344). Candidats : messages de la génération
  courante de la Boîte de réception dont un bit reste à décider **et** peut l'être.
- **Code mort retiré** (DOD) : `AddCategoryTagsToMailAsync`, `AddDocumentCategoryTagsAsync`, `AddTagsToMailAsync`,
  `TryAddCategoryMailTagAsync`. Les tags de catégorie de document sont remplacés par les tags système.
  - `MailRepositoryCategoryTagRaceTests` est retiré avec eux : la course qu'il gardait (création concurrente d'un tag
    de catégorie à l'ingestion) n'existe plus, les tags système étant posés par la migration.
  - Son invariant d'atomicité reste prouvé par `MailIngestionWriteOrderTests`, dont l'injection de panne passe de
    `INSERT INTO "MailTags"` à `INSERT INTO "MailMedicalDocuments"`.
- **Vue par tag(s)** : `GET api/v1/mail/tags/emails?tag=…&tag=…&filter=all|unread&page=…&pageSize=…`
  (`[TraceExempt]` : liste d'en-têtes de la boîte, comme les dossiers).
  - Intersection des tags, du plus récent au plus ancien, pages servies par le serveur.
  - Tag inconnu → 404 ; aucun tag, filtre inconnu ou page invalide → 400 `ProblemDetails` (`ValidationException`,
    règle 12).
  - Les routes `tags/{tagcode}/emails` et `tags/{tagcode}/emails/{uids}` sont retirées : les deux clients sont migrés
    dans la même task.
- **Dossiers de tag** (`GET folders`) : les quatre tags système toujours, dans l'ordre de la règle, même à zéro ; puis
  les tags IA et utilisateur qui portent au moins un message de la Boîte de réception, lu ou non. `Count` = total,
  `UnreadCount` = non lus, `TagType` renseigné.
- **Réglage du filtre** : `UserSettingsDto.TagViewFilter`, rangé dans les réglages de la **personne** (clé `UserId` du
  dépôt existant).
- **Outil e2e** (`mss.mail.e2e message --create`) : options `--from`, `--cc-only`, `--unread`.

### api-mcp — impact (Step 4c)
- `python Tools/contracts/mcp_impact.py check` → **1**, avec une seule raison : « forme du JSON modifiée dans
  `MailController.cs` (`PropertyNamingPolicy`) ».
- **Faux positif analysé** : les lignes retirées sont les options de sérialisation locales de l'action en flux
  `GET tags/{tag}/emails/{uids}`, supprimée. api-mcp n'appelle aucune route de tag : ses 5 routes sont intactes et les
  champs qu'il lit sont inchangés (`surface`). L'outil compare les jetons de forme JSON par fichier, pas par route.
- **Impact réel trouvé en l'analysant** : `list_folders` aurait listé en permanence les quatre dossiers virtuels
  `tag:` (source `Tag`), que `list_messages` ne sait pas lire.
  - Adaptation : `ToolViews.Flatten` écarte la source `Tag` (1 ou « Tag »), comme il écartait déjà `Drafts`.
  - Test d'intégration MCP `ListFolders_HidesTheVirtualTagFolders_SystemTagsIncluded` : stub WireMock qui reproduit la
    nouvelle liste, source en nombre et en chaîne. **Vu rouge par mutation** (filtre `Tag` retiré → « Collections
    differ »).
  - Suite api-mcp : 109/109.

### Tests et preuves rouges (règle 1b)
- **Unitaires** :
  - `SystemTagRuleTests` (23) : un test par tag, copie seule, `Auto-Submitted`, laboratoire, patient porteur d'une
    biologie, confrère sans document, expéditeur hors `.mssante.fr`, rang ;
  - `MailControllerTests` : combinaison, filtre et page transmis au service ; 404 ; 4 requêtes invalides refusées
    avant le service ;
  - tests des services et du dépôt migrés vers la nouvelle vue.
- **Intégration de bout en bout** (`FolderOperationsEndToEndTests.SystemTags.cs`) : vraie pile HTTP ; vrais
  `ImapService` → `EmailBuildingService` → `MailRepository` ; base PostgreSQL de la boîte construite par FluentMigrator ;
  Dovecot. Les messages sont déposés en IMAP avec leurs vrais en-têtes, dont une pièce HPRIM.
  - `TheSystemTags_ArePosedAtArrival_AndTheTagViewsServeReadAndUnreadMails_ByIntersection` : ordre et type des
    dossiers, `Count` / `UnreadCount`, chaque vue, « Non lus », intersection, pagination ;
  - `AnUnknownTagIs404_AndAnUnknownFilterAMissingTagOrABadPageAre400_InProblemJson` ;
  - `TheCatchUp_TagsTheMailsStoredBefore_AndNeverPutsBackATagRemovedByHand` ;
  - `TheTagViewFilter_IsKeptForThePerson_AnotherPersonOfTheBoxKeepsAll` : le titulaire passe à « Non lus », le
    délégataire garde « Tous » ;
  - `TheDelegateRemovesForInformation_TheHolderNoLongerSeesItThere_AndTheJournalNamesTheDelegate` : `TagRemoved` au
    nom du délégataire, poses de l'arrivée en actes système.
- **Mutations** (source muté, build, test visé, source restauré, rebuild) — toutes rouges :

  | # | Mutation | Test rouge |
  |---|---|---|
  | M1 | Pour info ignore la copie | ArePosedAtArrival (« Values differ ») |
  | M2 | Biologie jamais posée à l'arrivée | ArePosedAtArrival |
  | M3 | filtre « Non lus » ignoré | ArePosedAtArrival |
  | M4 | union au lieu de l'intersection | ArePosedAtArrival |
  | M5 | `Count` = non lus | ArePosedAtArrival |
  | M6 | tag inconnu servi en 200 | 404/400 (« Attendu 404, reçu 200 ») |
  | M7 | le rattrapage redécide tout (tag retiré reposé) | TheCatchUp |
  | M8 | le rattrapage ne pose rien | TheCatchUp |
  | M9 | filtre des vues non enregistré | TheTagViewFilter |
  | M10 | pose système imputée à la personne | TheDelegateRemoves (4 traces sur 4) |

- **Défaut du harnais trouvé par M10** : à la première passe, M10 **survivait**.
  - Cause : l'enrichissement des tests tournait dans un scope sans `MailboxId`. Aucune trace de pose n'atteignait le
    journal de la boîte, et `Assert.All(... TagAdded ..., IsSystemAct)` restait vrai sur une collection vide.
  - Correction : enrichissement sous l'identité de la requête (comme `CopyIdentityTo` en production), et
    `Assert.NotEmpty` avant l'`Assert.All`.
  - Prévention : `conventions/csharp.md` § `assert-all-jamais-sur-du-vide`.
- **Tests existants adaptés au nouveau comportement** :
  - `CountingQueriesEndToEndTests` : un tag dont le seul message est lu garde son dossier, en (1, 0) ; une boîte sans
    tag montre les quatre tags système à zéro ; un seul comptage groupé de `MailTags` ;
  - `AttachmentBytesReadEndToEndTests` : nouvelle route ;
  - `WidenTagNamesMigrationTests` : ne lit plus que ses propres tags ;
  - `MailRepositoryTagDraftCoverageTests` et `MailRepositoryBranchCoverageTests` : plus de tag de catégorie ; Biologie
    posée à la promotion ;
  - `FolderOperationsEndToEndTests.TagEntry` : « Biologie » est désormais posé par la migration.

### Build et suites
- **api-mail** : build vert. Suite complète :

  | Projet | Résultat |
  |---|---|
  | domaine | 325/325 |
  | infrastructure | 749/749 |
  | application | 4 260/4 260 |
  | api | 1 382/1 382 |
  | intégration | 1 320/1 323 (+16 ignorés) |

  - Les **3 rouges** de l'intégration sont les tests « du jour » : `FilterTodayEmails…`, `GetFolderTodayAsync…`,
    `GetFolderNotSeenTodayAsync…`. Ils ont été joués à 00:10 heure locale (23:10 UTC), dans la fenêtre de minuit connue
    où « aujourd'hui » est calculé en UTC. Ils sont sans lien avec la task.
  - **Vert non marqué** : `/review` rejouera la suite hors de cette fenêtre.
- **api-mcp** : 109/109, vert marqué (`ac959658`).
- **client-mobile** : build vert, Karma 1 502/1 502, `tsc` e2e propre, lint sans erreur sur les fichiers touchés ;
  vert marqué (`66018c5d`).
- **client-angular** : `nx build weda2` vert ; `nx test mss-lib` 156 fichiers, 1 740 tests ; 22 mutations rouges ;
  ESLint sans erreur, Prettier propre, CRLF. Ces chiffres viennent du rapport de l'implémentation : vert non marqué.
- **Scénarios e2e** E2E-TAG-002 et E2E-TAG-003 (v1, mobile et angular requis) : au catalogue et dans les deux suites.
  Ils n'ont jamais été joués, aucun backend e2e n'étant monté en `/develop` : leur preuve rouge et leur vert reviennent
  à `/e2e`.

### Passe qualité (§Q)
- **api-mail**, re-validé par la suite complète ci-dessus :
  - décision « une fois » factorisée dans `Decide`, partagée par l'ingestion et le rattrapage ;
  - garde « aucun tag » placée avant la lecture des tags ;
  - page vide servie sans hydratation ;
  - `using` et commentaires périmés retirés ; S125, S103.
- **api-mcp** : rien à nettoyer.
- **client-mobile** : lecture des réglages factorisée dans le support e2e ; deux commentaires périmés (regroupement
  biologie retiré).
- **client-angular** : rien à nettoyer.
- **Non appliqué**, à proposer : `SystemTagsRecoveryScheduler` recopie `AiTaggingRecoveryScheduler` (task-344). Une
  base commune toucherait du code hors task.

### Décisions prises (à arbitrer au merge)
- **weda2** :
  - la recherche et la puce « Bio à acquitter » sont masquées dans une vue par tag : une combinaison n'a pas de dossier
    à fournir à la recherche ;
  - décocher le dernier tag ramène à la Boîte de réception ;
  - le compteur du tableau de bord passe du total aux non lus, selon la règle de la DOD.
- **mobile** :
  - les tags du widget Messagerie de l'Accueil servent de puces, l'Accueil n'ayant pas de liste ; un toucher ouvre
    Messages avec cette seule puce active ;
  - dans une vue par tag, « Flaggés », « Bio à acquitter » et le choix liste / conversation sont masqués ;
  - un mail reçu en direct n'est pas inséré dans une vue par tag : il arrive au rechargement suivant.
- **api-mcp** : les dossiers de tag sont écartés de `list_folders`. Pas de vue par tag côté client IA en v1.

### Amélioration continue
- **Test qui affirmait sur du vide** (mutation survivante) : consigne `assert-all-jamais-sur-du-vide` dans
  `conventions/csharp.md`.
- **Étape qui bloque à tort** : `mcp_impact.py` signale la forme JSON au fichier, pas à la route. Prévention proposée,
  par une task du plan de contrôle à relire par l'humain avant le push (règle d'or 7) : ne retenir un jeton de forme
  JSON retiré d'un contrôleur que s'il appartient à une action dont la route est dans la surface d'api-mcp.
- **Récidive** du piège de la mémoire « Mutation restaurée : code muté qui survit » : la mutation api-mcp a été
  restaurée sans recompiler, et la suite est d'abord partie sur la DLL mutée (1 rouge). Recompilé avant de marquer le
  vert.

## Timings

*(généré par `tools/timing/report.sh --task task-456 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 28 s | — | — | — | — |
| /develop | ok | 58 min 11 s | 6 (31 s) | 6 (14 min 33 s) | — | api-mail 3B/3T, api-mcp 2B/2T, client-mobile 1B/1T |
| **Total cycle** | | **58 min 40 s** | **6 (31 s)** | **6 (14 min 33 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : nuget-wait ×1 (40 s)
