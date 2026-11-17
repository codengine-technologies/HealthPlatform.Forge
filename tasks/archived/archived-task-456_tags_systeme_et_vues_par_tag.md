# todo-task-456.md — Tags système et vues par tag : biologie, patient, professionnel de santé, pour info

**Repos**: api-mail, dtos-mss, client-angular, client-mobile, api-mcp
**Reprises**: 5 (la 3e hors plafond, autorisée par l'humain le 2026-11-17, limitée au test e2e weda2 ; la 4e ordonnée par l'humain le 2026-11-17 : tags de catégorie rétablis sauf la biologie ; la 5e ordonnée par l'humain le 2026-11-17 : un tag sans message n'est pas affiché)
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
  - **tout tag** (système, catégorie, IA, utilisateur) est affiché tant qu'il porte au moins un message de la Boîte
    de réception, lu ou non. Un tag sans aucun message n'est pas affiché. *(Décision humaine du 2026-11-17 : elle
    remplace « un tag système est toujours affiché, même à zéro ». Les tags système restent en tête quand ils sont
    affichés.)*
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
  > ⚠️ **Corrigé par la reprise 4 (retour humain du 2026-11-17).** Ce retrait était une erreur : seule la surcharge
  > publique `IMailRepository.AddCategoryTagsToMailAsync` (et son double d'`Infrastructure.Mock`) était sans
  > appelant. `AddDocumentCategoryTagsAsync` posait les tags de catégorie à l'insertion et à la promotion depuis
  > task-344. La pose est rétablie, sans le type Bio ; voir « Reprise 4 ».
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
- **Dossiers de tag** (`GET folders`) : les tags système en tête, dans l'ordre de la règle, puis les tags de catégorie,
  IA et utilisateur ; chacun n'est listé que s'il porte au moins un message de la Boîte de réception, lu ou non
  (reprise 5, décision humaine du 2026-11-17 : avant, les quatre tags système étaient listés même à zéro). `Count` = total,
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

### Reprise 1 (revue anticipée, passage 1)

Correctifs de la liste « À corriger par la reprise ». Chacun a été vu rouge : avant le correctif, ou par mutation.

- **Commits** :
  - api-mail : `dd90c9dc` fix(mail) ;
  - client-mobile : `7e3860f` fix(mobile) ;
  - client-angular : non commité (code-only), voir la liste plus bas.

**Backend (api-mail)**

- **B4** : `Decide` et `SystemTagDecision` passent dans la règle du domaine (`SystemTagRule.Decide`). L'insertion, la
  promotion et le rattrapage l'appellent.
  - 6 tests unitaires ajoutés : laboratoire + biologie → Biologie + Professionnel de santé ; patient + biologie →
    Biologie + Patient ; confrère sans document → Professionnel de santé seul ; en-têtes seuls → Biologie reste à
    décider ; en-têtes déjà décidés → jamais redécidés, ni même relus ; tout décidé → rien.
  - Le Develop log du premier passage annonçait ces deux combinaisons comme testées dans `SystemTagRuleTests` : à tort.
    Corrigé ici.
- **B1 / B3** : nouveau test d'intégration
  `AMailListedInHeadersOnly_GetsBiologyWhenItsContentArrives_AndATagRemovedByHandStaysRemoved`. Il passe par la vraie
  pile de bout en bout :
  1. compte rendu HPRIM, la boîte seulement en copie, d'abord persisté en en-têtes seuls par le chemin de la liste ;
  2. marque = `HeaderBits` ; « Pour info » posé, Biologie pas encore ;
  3. le praticien retire « Pour info » (route) ;
  4. enrichissement par `POST …/emails/enrich/sync` (promotion) ;
  5. marque = `AllBits` ; vues Biologie et Biologie + Professionnel de santé = le message ; « Pour info » non reposé.
- **B2** : le rattrapage est désormais prouvé déclenché par l'ouverture de la boîte.
  - La fixture d'intégration compose le **vrai** `SystemTagsRecoveryScheduler` (et `SystemTagsRecoveryService`), comme
    `Api/DependencyInjection`. Son créneau Redis est fermé par défaut : les autres tests ne voient rien changer. Un test
    l'ouvre pour sa boîte (`OpenSystemTagsRecoverySlot`).
  - Test `TheFirstOpeningAfterTheUpdate_SchedulesTheCatchUp_InTheBackground_UnderTheMailbox` :
    1. le message reçu en copie est ramené à l'état d'avant la mise à jour ;
    2. enrichissement par la route : rien n'est posé pendant la requête ;
    3. drainage de la file de fond : « Pour info » (l'adresse de la boîte a suivi la recopie d'identité) et
       « Professionnel de santé » sont reposés, et le journal **de la boîte** porte une pose de plus, en acte système.
  - Tests unitaires `SystemTagsRecoverySchedulerTests` (3) : créneau pris → rien ; Redis en panne → rien, sans
    exception ; créneau libre → passe en file `system-tags-recovery`, sous l'identité recopiée (adresse, RPPS,
    `MailboxId`), créneau jamais relâché.
- **S1** : le rattrapage pose chaque tag par une seule instruction par tag.
  - L'instruction est gardée par le bit **encore libre au moment de l'écriture** et passe `ON CONFLICT DO NOTHING` ;
    la marque est écrite dans la même transaction.
  - La trace dit ce qui a été réellement posé (`RETURNING`).
  - Tests `SystemTagsRecoveryRaceTests` (base isolée, intercepteur avant `INSERT INTO "MailTags"`) :
    - pose concurrente du même tag → lot réussi, une seule ligne ;
    - décision concurrente puis retrait à la main → le tag n'est pas reposé.
- **S2** : index partiel `IX_Mails_SystemTagsPending` limité à `"FolderPath" = 'INBOX'` (migration non mergée, filtre
  partagé avec `MailDataContext`).
- **S4** : `MailDto.IsAutomatic` recopié dans les trois projections de lecture (vue par tag, liste, message).
  L'assertion ajoutée au test d'arrivée était **rouge avant le correctif** (`(False, False)` au lieu de
  `(True, False)`).
- **S6** : la migration écrit noms, codes, couleurs, type et bits en littéraux (règle 7c). Elle ne lit plus
  `SystemTagRule`.
- Le harnais enrichit désormais par la route `enrich/sync`, et non plus par un appel direct au service.

**Mutations de la reprise** (source muté, build, test visé, source restauré, rebuild) — toutes rouges :

| # | Mutation | Test rouge |
|---|---|---|
| R1 | la promotion ne décide rien | AMailListedInHeadersOnly (« Values differ ») |
| R2 | `Decide` redécide les en-têtes quand le contenu arrive | AMailListedInHeadersOnly (« Pour info » reposé) |
| R3 | rattrapage jamais programmé par l'enrichissement | TheFirstOpeningAfterTheUpdate |
| R4 | pose du rattrapage sans `ON CONFLICT` | TheSameTagPosedConcurrently (23505) |
| R5 | pose du rattrapage non gardée par le bit | ATagDecidedConcurrently_ThenRemovedByHand |

**Clients**

- **C1, mobile** : `inbox.page.ts:383`, un abandon (`EmptyError`) n'est plus une panne.
  - Deux specs : relâcher la dernière puce, ou changer de dossier, pendant qu'une page est en vol.
  - Rouges avant le correctif ; mutation de la garde → rouges.
- **Libellé, mobile** : l'en-tête affiche « N message(s) » (le `totalCount` du serveur) quel que soit le filtre, comme
  weda2. Rouge en réinjectant l'ancien suffixe.
- **C2, weda2** : `mss-mail.component.ts`, `onUserSettingsLoaded`. Si le filtre change à l'arrivée des réglages pendant
  une vue par tag, la page repart du filtre retenu, et `isLoading` finit toujours.
  - Spec `mss-mail.component.tag-view-settings.spec.ts` (3 cas) : ordre « dossiers, page en vol, réglages »,
    réglages après la réponse, réglages « Tous » sans double chargement.
  - Rouges avant le correctif ; mutation → rouges.
- **C3, e2e** :
  - E2E-TAG-002, mobile et weda2 : les quatre premiers tags affichés sont BIOLOGIE, PATIENT, PROFESSIONNEL DE SANTE,
    POUR INFO, comparés au serveur relu au même moment, avec leur compteur de non lus.
  - E2E-TAG-003, mobile : `tag-view-count` = `totalCount` du serveur, en « Tous » et en « Non lus ».
  - weda2 : présence avant absence (convention `precondition-du-negatif`), nettoyage protégé (`try` par suppression),
    compteur relu jusqu'à égalité.
  - `scenario(…, 1)` inchangé, `tsc` des deux suites propre. Jamais joués ici, faute de backend e2e : leur rouge et
    leur vert reviennent à `/e2e`.
- **Hors liste, weda2** : 9 specs de `mail-list` (dont `search-mode` de task-445) étaient rouges depuis le 2026-11-17.
  Cause : une date d'envoi figée dans les données de test. Ils lisent désormais `.mail-subject-text`. Prévention :
  `conventions/angular.md` § `spec-qui-lit-une-ligne-de-liste-cible-l-objet`.
- **client-angular, fichiers touchés par la reprise** (s'ajoutent à la liste du premier passage) :
  - `mss-mail.component.ts` ;
  - `mss-mail.component.tag-view-settings.spec.ts` (nouveau) ;
  - `mail-list.tag-view.spec.ts`, `mail-list.search-mode.spec.ts` ;
  - `e2e/mss-e2e/specs/functional.e2e.ts`, `e2e/mss-e2e/support/e2e-backend.ts`.

**Suites**

- **api-mail** : build vert.

  | Projet | Résultat |
  |---|---|
  | domaine | 331/331 |
  | infrastructure | 749/749 |
  | application | 4 263/4 263 |
  | api | 1 382/1 382 |
  | intégration | 1 324/1 327 (+16 ignorés) |

  - Les 3 rouges sont, de nouveau, les tests « du jour » de la fenêtre de minuit (00:37 heure locale). Vert non marqué.
- **client-mobile** : build vert, Karma 1 504/1 504, lint sans erreur ; vert marqué (`7e3860f2`).
- **weda2** : `nx build weda2` vert ; `nx test mss-lib` 157 fichiers, 1 743 tests ; ESLint et Prettier propres.
- **api-mcp** : inchangé depuis le premier passage (109/109, vert marqué).

### Reprise 2 (revue anticipée, passage 2)

- **Commits** : api-mail `b58d71c0` ; client-mobile `62cf9ba`. weda2 n'a pas changé depuis la reprise 1.

**Backend (api-mail)**

- **B5 — Interblocage entre le rattrapage et la promotion** (introduit par la reprise 1). La transaction du rattrapage
  verrouille d'abord les lignes `Mails` du lot (`SELECT 1 … ORDER BY "Id" FOR UPDATE`), puis écrit les `MailTags`.
  - C'est le même ordre que la promotion (`Mails`, puis `MailTags`).
  - La garde « bit encore libre » est relue dans un instantané pris après l'attente du verrou.
  - Test `APromotionOfTheSameMailInFlight_NeitherDeadlocks_NorFailsTheBatch` (base isolée) :
    1. une transaction de promotion a écrit la ligne `Mails` ;
    2. le rattrapage démarre et attend un verrou (constaté dans `pg_stat_activity`, sinon le test échoue : il
       n'éprouverait rien) ;
    3. la promotion pose le même tag, marque sa décision et valide ;
    4. ni la promotion ni le rattrapage n'échouent, et la ligne du tag est unique.
  - Les deux tests de course de la reprise 1 injectent maintenant leur écriture concurrente juste **avant** le
    verrou : après, elle l'attendrait.
- **Trace** : un tag écarté par le conflit n'est pas tracé.
  - Le premier test de course reçoit un service d'audit, par une nouvelle surcharge du constructeur
    `MailRepository(context, logger, auditService)`, sur le modèle des surcharges de test existantes.
  - Il affirme qu'aucun `Trace` n'est émis.
- **UUID v7** : les identifiants des poses du rattrapage sont générés côté .NET (`Guid.CreateVersion7()`) et passés par
  `unnest`, comme le reste du modèle (task-019).
- **`IsAutomatic`** :
  - la page de messages (`BuildBulkMailDto`, route `GET …/emails/{uid}`) est maintenant affirmée dans le test
    d'arrivée ;
  - la copie de `GetMailAsync` ne sert que des chemins internes (contenu `MailContentDto`, mode hors ligne) : aucune
    route ne l'expose en `MailDto`, et la mutation A1 y survit.

**Mutations de la reprise 2** :

| # | Mutation | Test |
|---|---|---|
| B5 | verrou des lignes du lot retiré | APromotionOfTheSameMailInFlight : **rouge** (`Assert.Null`, interblocage) |
| T | trace de la décision au lieu des poses réelles | TheSameTagPosedConcurrently : **rouge** |
| A2 | `IsAutomatic` retiré de `BuildBulkMailDto` | ArePosedAtArrival : **rouge** |
| A1 | `IsAutomatic` retiré de `GetMailAsync` | survit (chemin interne, voir plus haut) |

**Client mobile**

- **Fenêtre après un abandon** (`inbox.page.ts`) : un compteur d'abandons (`tagViewAbortSeq`, `abandonTagView()`).
  - Un `loadTagView` abandonné ne termine plus rien : pas de fin de chargement, et le flux n'est ni rebranché ni
    reconnecté.
  - `replaced()` en tient compte.
  - Deux specs, avec le `getFolder` suivant laissé en attente (`Subject`) : rouges avant le correctif (2 sur 42),
    vertes après (42/42).

**Suites**

- **api-mail** : build vert.

  | Projet | Résultat |
  |---|---|
  | domaine | 331/331 |
  | infrastructure | 749/749 |
  | application | 4 263/4 263 |
  | api | 1 382/1 382 |
  | intégration | 1 325/1 328 (+16 ignorés) |

  - Les 3 rouges sont toujours les tests « du jour », joués entre 00:54 et 01:00 heure locale (fenêtre de minuit).
    Vert non marqué.
- **client-mobile** : build vert ; Karma 1 506/1 506 au second passage (le premier avait 3 rouges dans
  `HtmlEditorComponent`, le flaky connu) ; lint sans erreur ; vert marqué (`62cf9ba4`).

### Reprise 3 (hors plafond, autorisée par l'humain — `/e2e` rouge en voie Angular)

- **Portée** : le seul correctif de test décrit dans `questions/task-456.md`. Aucun code produit ne change ; api-mail,
  api-mcp, dtos-mss et client-mobile sont inchangés.
- **Cause** : l'aide weda2 `waitForTagView` attendait la vue BIOLOGIE côté serveur sans demander l'analyse du
  message. Le tag Biologie n'est décidé qu'à l'analyse : l'attente de 180 s s'épuisait.
- **Correctif** (weda2, code-only, non commité) :
  - `e2e/mss-e2e/support/e2e-backend.ts` : `OtherDevice.analyse(uid)`, qui demande `POST …/emails/enrich/sync`
    pour ce message, comme l'app qui l'affiche ;
  - `e2e/mss-e2e/specs/functional.e2e.ts` : `waitForTagView` relit le message, puis demande son analyse avant
    de lire la vue.
- **Vu rouge, puis vert** :
  - rouge : `/e2e` sur le code d'avant le correctif, E2E-TAG-002 et E2E-TAG-003 rouges aux deux essais
    (« … est dans la vue BIOLOGIE, côté serveur », 180 s) ;
  - vert : backend monté par `node e2e/mss-e2e/run.mjs --serve-only`, puis
    `npx playwright test --grep "E2E-TAG-00[23]" --retries 0` : **2 passed (25,8 s)**. Démontage par `out/STOP`,
    aucun conteneur résiduel, port 47399 libre.
- **Lint** : aucun avertissement ESLint sur les lignes ajoutées (les 19 avertissements des deux fichiers sont
  antérieurs).
- **Marqueur vert** : weda2 non re-marqué (seuls des scénarios ciblés ont tourné) ; `/review` rejouera build et
  tests sur cet arbre. Les voies complètes restent jouées par `/e2e`.
- **Prévention** : déjà écrite, `conventions/e2e.md` § `etat-decide-a-l-analyse-attendu-cote-serveur`.

### Reprise 4 (ordonnée par l'humain le 2026-11-17 — tags de catégorie rétablis sauf la biologie)

Portée : la liste « À corriger par la reprise » du passage 5.

- **R1 — Tags de catégorie rétablis** (api-mail, `MailRepository`) :
  - `AddDocumentCategoryTagsAsync` (privée) rejouée dans la transaction de l'insertion (`PersistNewMailAsync`) et de
    la promotion, au même endroit qu'avant la task ;
  - un tag `CATEGORY` par type de document, couleur `#3B82F6`, création concurrente rattrapée par
    `CreateTagOrReadWinnerAsync` ;
  - le type de biologie est écarté par `SystemTagRule.IsBiology`, la règle qui décide le tag système, casse
    indifférente ;
  - la surcharge publique `AddCategoryTagsToMailAsync` n'est pas rétablie : elle n'avait pas d'appelant.
  - **Test d'intégration** `TheDocumentCategoryTags_ArePosedAtInsertionAndPromotion_ButBiologyIsOnlyTheSystemTag`
    (vraie pile HTTP, Dovecot, PostgreSQL, CDA ANS imagerie 18748-4 et microbiologie 11502-2). Il vérifie :
    - le tag `IMAGERIE` (`CATEGORY`) est posé à l'insertion et à la promotion, et lu dans `GET …/emails/{uid}` ;
    - le dossier `tag:IMAGERIE` est listé, et sa vue rend les deux messages ;
    - le message de biologie porte `BIOLOGIE` (`SYSTEM`), jamais `BIO` ;
    - aucun dossier `tag:BIO` n'est listé.
  - **Vu rouge** : sur le code d'avant le correctif, 404 « Ce tag n'existe pas dans la boîte » (`IMAGERIE`).
    Par mutation : exclusion de Bio retirée → `Assert.DoesNotContain` échoue sur `TagDto { Code = "BIO", Type =
    "CATEGORY" }`. Les deux mutants ont été restaurés, puis le code recompilé.
  - `MailRepositoryCategoryTagRaceTests` rétabli (ses deux cas de course ; le troisième, l'atomicité, reste prouvé
    par `MailIngestionWriteOrderTests`) : vert.
- **R2 — Migration `AddSystemTags`** : `DELETE FROM "Tags" WHERE "Type" = 'CATEGORY' AND "Code" = 'BIO'`.
  Documentation de la migration mise à jour.
  - **Audit 7c** : la migration a été relue. Une seule opération destructive, bornée au tag `BIO` de type `CATEGORY`,
    avec ses poses en cascade. La descente ne la restaure pas, et sa documentation le dit.
  - **Test** `AddSystemTagsMigrationTests` (coureur de production, base neuve sans pool). Avant la montée :
    `BIO`, `IMAGERIE` et `CONSULTATION`, plus des poses de `BIO` et `IMAGERIE`. Après : `CONSULTATION` et
    `IMAGERIE` restent, et seule la pose d'`IMAGERIE` reste. **Vu rouge par mutation** (ancien `DELETE` de tous
    les `CATEGORY`) : `Expected ["CONSULTATION", "IMAGERIE"]`.
- **R3 — Miroirs TypeScript** : `TagKind` du mobile porte `'CATEGORY'`. Le commentaire de `tagType` (weda2) est
  aligné. Aucune logique cliente ne dépend du type, qui ne sert qu'à l'attribut `data-tag-type` : les dossiers
  arrivent déjà ordonnés par le serveur, et `TagNameRule.KindRank` range `CATEGORY` avec les tags système.
- **R4** : le paragraphe « Code mort retiré » est corrigé ci-dessus.
- **Hors reprise** (décision humaine) : aucun script de repose sur les bases déjà migrées.
- **Auto-contrôle du correctif** : la pose est écrite avant le commit de la transaction, comme avant la task. Une
  panne pendant cette pose annule donc le message entier, ce que `MailIngestionWriteOrderTests` prouve déjà. Les
  tags système ne dépendent pas de cette pose. La vue par tags et le compteur traitent un tag `CATEGORY` comme un
  tag IA ou utilisateur : il est listé tant qu'il porte un message de la Boîte de réception.
- **Test encodant l'erreur, rétabli** : `MailRepositoryTagDraftCoverageTests` (renommé par la task en
  `…_WithoutCategoryTags`, assertion inversée) retrouve son nom et son assertion de `develop`
  (`…PromotesContentDocumentsAndCategoryTags`, le tag Consultation est posé à la promotion). Il était le seul rouge
  de la première suite complète. Deux commentaires devenus faux sont corrigés (`MailRepositoryBranchCoverageTests`,
  `MailIngestionWriteOrderTests`).
- **Build et suites** :
  - **api-mail** : build Release 0 erreur ; suite complète verte, 8 055 tests et 16 ignorés (domaine 331,
    infrastructure 749, application 4 263, api 1 382, intégration 1 332 + 16 ignorés). Commit `a9859b87`, poussé,
    vert marqué ;
  - **client-mobile** : `npm run build` vert ; 1 506 tests sur 1 506. Commit `71dc3b2b`, poussé, vert marqué ;
  - **weda2** : seul un commentaire change, aucun build rejoué, pas de marqueur vert. `/review` rejoue son build ;
  - **api-mcp** : `mcp_impact.py check` signale toujours l'impact de `MailController.cs`, celui de la task, déjà
    adapté (PR #2). La reprise ne touche pas cette surface.
- **Banc local** : cinq processus `mss.mail.api` (AppHost de l'humain) verrouillaient les binaires Debug ; build et
  suites joués en **Release**, sans les arrêter.

### Reprise 5 (ordonnée par l'humain le 2026-11-17 — un tag sans message n'est pas affiché)

Portée : la liste « À corriger par la reprise » du passage 8.

- **R5 — api-mail, `GetTagFoldersAsync`** : un tag système n'est plus listé que s'il porte au moins un message de la
  Boîte de réception, lu ou non, comme les autres tags. Quand il est listé, il reste en tête, dans l'ordre de
  `SystemTagRule.All`. La documentation de la méthode est alignée.
  - **Test d'intégration** `ASystemTagWithoutMail_IsNotListed_AndOneWhoseOnlyMailIsRead_StaysListed` (vraie pile
    HTTP, Dovecot, PostgreSQL). Un message de patient, lu : seul `tag:PATIENT` est listé, en (1 message, 0 non lu).
    Le praticien retire « Patient » : plus aucun dossier de tag.
  - **Vus rouges** sur le code d'avant le correctif :
    - ce test : `Assert.Single() Failure: The collection contained 4 items` (Biologie, Professionnel de santé et
      Pour info listés à 0) ;
    - `CountingQueriesEndToEndTests.AMailboxWithoutTags_ListsItsFolders_AndNoTagFolder`, renommé depuis
      `…OnlyTheFourSystemTagsAtZero` : `Assert.DoesNotContain() Failure` (les quatre dossiers à zéro).
  - Test unitaire `MailRepositoryTests.GetTagFoldersAsyncShouldReturnNoFolder_WhenNothingIsTaggedAsync`, qui
    remplace `…TheFourSystemTagsAtZero…`.
- **Catalogue e2e** : **E2E-TAG-002 passe en v2**, attendu réécrit (« un tag sans aucun message n'est pas affiché »).
  Les deux clients déclarent la v2. Leurs assertions ne changent pas : le parcours dépose lui-même un message pour
  chacun des quatre tags système. La disparition d'un tag sans message est prouvée par le test d'intégration.
- **Clients** : ils affichent la liste rendue par le serveur, sans filtre local. Seuls des commentaires et des titres
  de spec qui disaient « système toujours, même à zéro » sont corrigés : `messaging-counters-widget` (mobile),
  `mail-state.service`, `mail-widget` et `mail-folder-list.tags.spec` (weda2).
- **Build et suites** :
  - **api-mail** : build Release 0 erreur ; 8 059 tests verts et 16 ignorés (intégration 1 334). Commit `3ee8c973`,
    poussé, vert marqué ;
  - **client-mobile** : build vert ; 1 506 tests sur 1 506 au **second** passage. Au premier,
    `MailboxSwitcherComponent` est tombé sur `onAriaChanged` : c'est l'aléa connu, et `conventions/angular.md`
    passe de 4 à 5 occurrences. Commit `7aefb357`, poussé, vert marqué ;
  - **weda2** : ESLint 0 erreur (3 avertissements antérieurs) ; `nx build weda2` vert ; `nx test mss-lib` 157
    fichiers, 1 743 tests. Vert marqué ;
  - **api-mcp** : `mcp_impact.py check` signale toujours l'impact de `MailController.cs`, celui de la task, déjà
    adapté (PR #2). `list_folders` écarte déjà les dossiers de tag.
- **Auto-contrôle du correctif** :
  - si l'on retire d'une vue par tag le dernier message, le dossier disparaît de la liste, mais la vue ouverte
    reste lisible : le tag existe toujours en base, donc la route rend une page vide, pas un 404 ;
  - le rattrapage et la pose des tags système ne lisent pas la liste des dossiers : ils ne changent pas.

## Sonar log

- **Phase 1 (new code)** : ✓ Quality Gate OK, new_coverage = 96,7 %.
  - Issues fixées : **1** code smell, `CA1862`, sur la requête du rattrapage
    (`d.Category!.ToUpper() == …` → `EF.Functions.ILike`). Commit `b95ce350`.
  - Test : le rattrapage de Biologie est ajouté à `TheCatchUp_…`, vu rouge par mutation (comparaison sensible à la
    casse).
  - Hotspots du new code : 0.
- **Phase 2 (legacy)** : rien à traiter (0 bug, 0 vulnérabilité, 0 code smell sur le projet). 0 itération.
- **Analyses** : 2 (initiale, puis après correctif). Serveur SonarQube 9.9.8 (`sonar.login`).
- **Build / tests** (Release, couverture OpenCover) : ✓ vert à la seconde analyse.

  | Projet | Résultat |
  |---|---|
  | domaine | 331/331 |
  | application | 4 263/4 263 |
  | infrastructure | 749/749 |
  | api | 1 382/1 382 |
  | intégration | 1 328/1 328 (+16 ignorés) |

  Vert marqué sur `b95ce350`.
- **Amélioration continue** : `conventions/csharp.md` § CA1862, occurrences 3 → 4. C'est une récidive de la variante
  EF, écrite pendant la reprise 1 sans relire le fichier. La convention citait un `SearchQueryHelper.ToExactPattern`
  qui n'existe pas : corrigé.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 96,6 % | 96,7 % | +0,1 pt |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 0 | 0 (1 en cours de run, corrigé) | 0 |
| Coverage (projet) | 97,8 % | 97,8 % | 0 |
| Duplication | 0,4 % | 0,4 % | 0 |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

### Reprise 4 (2026-11-17) — nouvelle analyse sur `9c6f6a43`

- **Phase 1 (new code)** : ✓ Quality Gate OK, new_coverage = 96,7 %. **0 issue** sur le nouveau code : aucun
  correctif, 0 itération. Hotspots : 0.
- **Phase 2 (legacy)** : 0 issue ouverte sur le projet. Rien à traiter.
- **Analyse** : 1, sur SonarQube 9.9.8 (`sonar.login`).
- **Build et tests** (Release, couverture OpenCover) : verts.

  | Projet | Tests |
  |---|---|
  | domaine | 331/331 |
  | application | 4 263/4 263 |
  | infrastructure | 749/749 |
  | api | 1 382/1 382 |
  | intégration | 1 333/1 333 (+16 ignorés) |

  Vert marqué sur `9c6f6a43`.
- **KPIs** : identiques à la colonne « Final » ci-dessus (QG OK, new coverage 96,7 %, 0/0/0, coverage 97,8 %,
  duplication 0,4 %, A/A/A).
- **Amélioration continue** : aucune leçon Sonar (aucune issue).

### Reprise 5 (2026-11-17) — analyses sur `3ee8c973` puis `9697e4f6`

- **Phase 1 (new code)** : 1 code smell, **S3267** à `MailRepository.cs:3535`. C'était la boucle `foreach … if …
  folders.Add(…)` de `GetTagFoldersAsync`, écrite pendant la reprise. Réécrite en `Select(…).Where(…).Select(…).ToList()`,
  commit `9697e4f6`. C'est un pur refactor, couvert par `ASystemTagWithoutMail_IsNotListed_…` et
  `TheSystemTags_ArePosedAtArrival_…`. Seconde analyse : **0 issue**, Quality Gate OK, new_coverage 96,7 %.
- **Phase 2 (legacy)** : 0 issue ouverte. Rien à traiter.
- **Analyses** : 2, sur SonarQube 9.9.8.
- **Build et tests** (Release, OpenCover) : verts aux deux analyses. Domaine 331, application 4 263, infrastructure
  749, api 1 382, intégration 1 334 (+16 ignorés). Vert marqué sur `9697e4f6`.
- **KPIs** : QG OK, new coverage 96,7 %, 0 bug, 0 vulnérabilité, 0 smell, coverage 97,8 %, duplication 0,4 %, A/A/A.
- **Amélioration continue** : `conventions/csharp.md` § S3267, occurrences 4 → 5. C'est une récidive sur du code
  frais, écrit en reprise sans relire le fichier.

## Lint log

- **Périmètre** : `client-angular` (code-only, branche `feature/nova-mss-weda-integration`), fichiers de task-456
  seulement. ESLint lancé directement sur les 16 fichiers de la task : les 13 `.ts`, et les 3 `.html`, que la
  configuration ignore. C'est le contournement documenté depuis task-367 : `nx affected --projects=tag:scope:mss` ne
  restreint pas le périmètre sur ce workspace.
- **Résultat** : **0 erreur**. 34 avertissements (`max-lines`, `jsdoc/require-example`), dont **aucun** sur une ligne
  ajoutée par la task (attribution par `git diff -U0 HEAD`). Les specs sont exclues par la configuration ESLint.
- Lint propre pour la task : aucune itération, aucun auto-fix, aucun fichier modifié.
- **Validation de l'arbre final** :
  - `nx build weda2` vert ;
  - `nx test mss-lib` : 157 fichiers, **1 743 tests** verts (sortie statique, ligne « Tests » lue) ;
  - vert marqué (`lint-angular`).

### Reprise 4 (2026-11-17)

- Seul `libs/mss/src/core/models/folder.model.ts` change (commentaire de `tagType`) : ESLint sur ce fichier, **0 erreur, 0
  avertissement**. Aucune itération.
- Arbre final : `nx build weda2` vert ; `nx test mss-lib` (sortie statique) **157 fichiers, 1 743 tests** verts. Vert
  marqué (`lint-angular`).

### Reprise 5 (2026-11-17)

- ESLint sur les fichiers `.ts` touchés (`mail-state.service.ts`, `mail-widget.component.ts`, `folder.model.ts`) :
  **0 erreur**, 3 avertissements antérieurs (`max-lines`, `jsdoc`), aucun sur une ligne modifiée. Les specs et l'e2e
  sont exclus par la configuration. Aucune itération.
- Vert de `/develop` toujours valide sur l'arbre final (`nx build weda2`, `nx test mss-lib` 1 743).

## Lint mobile log

- **Périmètre** : `client-mobile`, branche `feat/task-456-…` (`62cf9ba`).
- **Résultat** : `npm run lint` → **All files pass linting** (0 erreur, 0 avertissement).
- Aucune itération, aucun auto-fix, aucun commit.
- **Build et Karma** : 1 506 / 1 506 verts sur ce code exact (marqueur vert de la reprise 2 de `/develop`, vérifié par
  `green.py check`).

### Reprise 4 (2026-11-17)

- `npm run lint` sur `71dc3b2b` : **All files pass linting**. Aucune itération, aucun fichier modifié, rien à commiter.
- Vert de `/develop` toujours valide sur ce code exact (`green.py check`).

### Reprise 5 (2026-11-17)

- `npm run lint` sur `f3069875` : **All files pass linting**. Aucune itération, rien à commiter.
- Vert de `/develop` toujours valide sur ce code exact.

## E2E log

Rejoué après la reprise 5 (ordonnée par l'humain le 2026-11-17 : un tag sans message n'est pas affiché ; E2E-TAG-002
passe en v2). api-mail (`9697e4f6`) et client-mobile (`f3069875`) ont changé : les deux voies sont jouées en entier.

| Voie | Jouée / réutilisée | Dépôts couverts (HEAD) | Résultat |
|---|---|---|---|
| mobile | jouée | api-mail `9697e4f6`, client-mobile `f3069875` | ✅ 66 verts, 0 flaky, 0 rouge, parité verte |
| angular | jouée | api-mail `9697e4f6`, client-angular `f0e9ee95` + arbre de travail, client-mobile/e2e `f3069875` | ✅ 87 verts, 0 flaky, 0 rouge, parité verte |

- **Porte** : code 0, sur le catalogue de la branche. E2E-TAG-002 v2 est vert sur les deux clients.
- **Démontage** vérifié : aucun conteneur e2e résiduel, ports 5052, 3993, 3465, 3143 et 47399 libres.
- **Écrans touchés sans spec e2e** : la vue par tag mobile (relâche d'une puce disparue) est couverte par les specs
  unitaires de `MailStateService` et `MailFolderListComponent`. Aucun scénario ne retire le dernier message d'une vue
  par tag : suggestion de la revue, non bloquante.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-PATIENT-003 | 1 | headless | La fiche d'un patient ne montre pas les documents d'un autre patient du même mail | ✅ | ✅ |
| E2E-PATIENT-004 | 1 | headless | La vue « Mails du patient » reste ouverte et ses pages viennent du serveur | ✅ | — |
| E2E-CONTACT-001 | 2 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Écrire à l'adresse choisie d'un contact à plusieurs adresses, ou à son adresse par défaut | ✅ | ✅ |
| E2E-COMPOSE-005 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-MAIL-006 | 1 | headless | Glisser sur la Corbeille un message d'un fil supprime ce message, et lui seul | ✅ | — |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-DRAFT-004 | 1 | headless | Une rédaction sans texte dans le corps ne laisse ni brouillon ni question | ✅ | ✅ |
| E2E-BIO-001 | 2 | headless | Acquitter un compte rendu de biologie, à son nom | ✅ | ✅ |
| E2E-BIO-002 | 1 | headless | La puce « Bio à acquitter » montre tous les résultats en attente, sur toutes les pages | ✅ | ✅ |
| E2E-BIO-003 | 1 | headless | Lire un résultat HPRIM puis l'acquitter | ✅ | ✅ |
| E2E-BIO-004 | 1 | headless | Un compte rendu acquitté puis déplacé depuis un autre client garde son acquittement | ✅ | ✅ |
| E2E-BIO-007 | 1 | headless | Un compte rendu arrivé avant la date de début du suivi ne réclame rien, et s'acquitte quand même | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-DETAIL-006 | 1 | headless | Après une réponse, le message d'origine dit « Vous avez répondu à ce message le… » | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SETTINGS-004 | 1 | headless | Paramètres indisponibles : rien n'est écrasé | ✅ | — |
| E2E-SEARCH-001 | 2 | headless | Composer ses critères puis lancer la recherche | ✅ | ✅ (v1) · divergence (task-450) |
| E2E-SEARCH-002 | 1 | headless | Un mot rare et accentué trouve le message qui le contient | ✅ | ✅ |
| E2E-SEARCH-003 | 1 | headless | Un numéro de dossier trouve son message, et un seul | ✅ | ✅ |
| E2E-SEARCH-004 | 1 | headless | Un nom de patient tapé sans accent ni majuscule trouve ses messages, puis les messages partiels | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-005 | 1 | headless | Un mot absent de la boîte affiche « Aucun résultat » | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-006 | 1 | headless | Plus de résultats qu'une page — « Voir plus » affiche la suite, jusqu'au dernier | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-007 | 1 | headless | Une recherche en échec affiche un message, et l'ancienne liste n'est plus affichée | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-009 | 1 | headless | Fermer la recherche rend le dossier à la même position ; retirer une étiquette relance sans elle | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-010 | 1 | headless | Reconnaître un résultat et ouvrir le dossier du patient | ✅ | ⛔ non joué · divergence (task-451) |
| E2E-SEARCH-012 | 1 | headless | Traiter tous les résultats d'une recherche | ✅ | ⛔ non joué · divergence (task-451) |
| E2E-SEARCH-008 | 1 | headless | Restreindre la recherche à un patient et à ses biologies anormales | ✅ | ⛔ non joué · divergence (task-451) |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 2 | headless | Créer un contact à deux adresses, le modifier sans les perdre, puis le supprimer | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-CONTACT-004 | 1 | headless | Consulter un contact depuis le carnet et lui écrire | ✅ | ✅ |
| E2E-CONTACT-005 | 1 | headless | Une fiche modifiée ne se perd pas sans confirmation, une adresse mal formée est refusée | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 2 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ | ✅ |
| E2E-MAILBOX-003 | 2 | headless | Rattacher ses boîtes depuis « Mes boîtes » en un geste — titulaire et membre | ✅ | ✅ |
| E2E-MAILBOX-006 | 1 | headless | Après le rattachement, l'identité d'expéditeur et la signature sont déjà là | ✅ | ✅ |
| E2E-MAILBOX-004 | 1 | headless | Ajouter une BAL déléguée par saisie — et refus de sa propre adresse | ✅ | ✅ |
| E2E-MAILBOX-005 | 1 | headless | Le délégataire refusé par l'opérateur perd l'accès, en ligne puis hors ligne ; le titulaire garde le sien | ✅ | ✅ |
| E2E-AUDIT-001 | 1 | headless | Le titulaire lit au journal le message supprimé par son délégataire, au nom du délégataire | ✅ | — |
| E2E-AUDIT-002 | 1 | headless | Le journal d'audit montre chaque action sur un mail | ✅ | — |
| E2E-SHARED-001 | 1 | headless | Une boîte partagée, une base — le patient rattaché par le titulaire est vu du délégataire, la signature reste à chacun | ✅ | ✅ |
| E2E-SHARED-002 | 1 | headless | Le délégataire écrit pour le compte du titulaire — le destinataire voit qui a écrit, sa réponse revient à la boîte | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |
| E2E-SESSION-004 | 1 | headless | Sur un appareil partagé, la personne suivante n'arrive jamais dans la boîte de la précédente | ✅ | ✅ |
| E2E-AI-002 | 1 | headless | Un délégataire interroge l'assistant dans la boîte qu'il a ouverte | ✅ | ✅ |
| E2E-MAILBOX-007 | 1 | headless | Après un changement de boîte, l'onglet Patients ne montre plus rien de la précédente | ✅ | ✅ |
| E2E-ERROR-001 | 1 | headless | Une erreur affiche un code et une référence à transmettre au support | ✅ | ✅ |
| E2E-TAG-001 | 1 | headless | Choisir un tag de la boîte dans la liste, créer un tag de plusieurs mots | ✅ | ✅ |
| E2E-TAG-002 | 2 | headless | Les tags système classent la Boîte de réception : Biologie, Patient, Pour info | ✅ | ✅ |
| E2E-TAG-003 | 1 | headless | Combiner deux tags et retrouver le filtre « Non lus » | ✅ | ✅ |

**Divergences temporaires ouvertes** (9) :

- E2E-SEARCH-001 [mobile] — le mobile adopte le formulaire à un seul niveau avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-004 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-005 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-006 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-007 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-009 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-010 [mobile] — la lecture enrichie arrive sur le mobile avec la refonte mobile — résorbée par task-451
- E2E-SEARCH-012 [mobile] — la sélection de tous les résultats arrive sur le mobile avec la refonte mobile — résorbée par task-451
- E2E-SEARCH-008 [mobile] — les critères médicaux arrivent sur le mobile avec la refonte mobile — résorbée par task-451

**Parité : verte** — aucun écart entre le catalogue et les suites.

## Code Review Summary

### Passage 1 (revue anticipée) — CHANGES REQUESTED

Revue indépendante en deux relecteurs : backend (api-mail, dtos-mss, api-mcp) et clients (mobile, weda2, e2e). Ils
ont reçu le code et la US, pas les conclusions de `/develop`.

- **4b (clause DOD)** : E2E-TAG-002 et E2E-TAG-003 v1 sont au diff du catalogue, avec mobile et angular requis. Les deux
  suites déclarent `scenario('E2E-TAG-00x', 1)`.
- **4c** : `mcp_impact.py check` → 1, une seule raison (forme JSON dans `MailController.cs`).
  - C'est un faux positif : la ligne vient des options locales de la route en flux supprimée, qu'api-mcp n'appelle
    pas.
  - La branche `api-mcp` répond à l'impact réel : dossiers `tag:` écartés de `list_folders`, test vu rouge, suite
    109/109.

**4a — règle 1b**

| Comportement | Test d'intégration | Preuve rouge |
|---|---|---|
| Tags posés à l'arrivée | `TheSystemTags_ArePosedAtArrival…` | M1, M2 |
| Vue all / unread, ordre, pagination | idem | M3 |
| Intersection | idem | M4 |
| Dossiers : système toujours ; Count / UnreadCount | idem + `CountingQueriesEndToEndTests` | M5 |
| 404 / 400 en ProblemDetails | `AnUnknownTagIs404…` | M6 |
| Rattrapage (service appelé à la main) | `TheCatchUp…` | M8 |
| Rattrapage déclenché à l'ouverture de la boîte | **aucun** | ❌ B2 |
| Tag retiré non reposé | `TheCatchUp…`, cas `AllBits` seulement | M7 faible, ❌ B3 |
| Biologie et en-têtes à la promotion | **aucun** (unitaire en mémoire seulement) | ❌ B1 |
| Réglage par personne | `TheTagViewFilter…` | M9 |
| Retrait par le délégataire, journal, actes système | `TheDelegateRemoves…` | M10 |
| api-mcp : `list_folders` sans dossiers de tag | `ListFolders_HidesTheVirtualTagFolders…` | oui |

#### À corriger par la reprise

**Backend (api-mail)**

- **B1 — Promotion sans test d'intégration (règle 1b).** `ApplySystemTagsOnPromotionAsync` décide Biologie (et les
  tags d'en-têtes d'un message d'avant la migration), mais seul un test unitaire en mémoire la couvre.
  - Test de bout en bout attendu :
    1. message HPRIM d'abord enregistré en en-têtes seuls dans la Boîte de réception ;
    2. retrait à la main d'un tag d'en-têtes ;
    3. enrichissement par la route réelle ;
    4. assertions : « Biologie » est servi par `GET tags/emails`, et le tag retiré n'est pas reposé.
  - Mutation ciblée sur `Decide` (`alreadyDecided` ignoré), à consigner.
- **B2 — Le déclenchement du rattrapage n'est pas prouvé.** Le test construit `SystemTagsRecoveryService` à la main.
  L'appel dans `EnrichEmailsAsync`, le créneau Redis, la file de fond, la recopie d'identité (adresse de la boîte,
  `MailboxId`) et l'enregistrement DI ne sont pas couverts.
  - Test d'intégration attendu :
    1. message ramené à l'état d'avant la mise à jour ;
    2. enrichissement de la Boîte de réception par la route réelle ;
    3. attente de la file de fond ;
    4. lecture de `GET tags/emails` et du journal : pose tracée en acte système, dans la boîte.
  - Plus un test unitaire du planificateur : créneau pris → mis en file ; créneau refusé ou Redis en panne → rien.
  - Preuve rouge consignée.
- **B3 — La garde par tag de `Decide` n'est jamais exercée.** Le message dont on retire « Pour info » est à `AllBits` :
  le filtre des candidats l'écarte avant toute décision.
  - Retirer le tag d'un message dont les en-têtes sont décidés mais pas Biologie, lui donner son contenu, puis lancer
    le rattrapage.
  - Mutation ciblée sur `Decide`. Peut se fusionner avec B1.
- **B4 — Deux tests unitaires de la DOD manquent.** « Laboratoire → Biologie + Professionnel de santé » et « patient
  porteur d'une biologie → Biologie + Patient » ne sont pas testés : la combinaison se fait dans `Decide`, sans test
  unitaire. Tester la composition, et corriger le Develop log, qui les annonçait.

**Clients**

- **C1 — Mobile : faux bandeau d'erreur.** Relâcher la dernière puce (ou changer de dossier) pendant le chargement
  d'une page de vue par tag fait échouer la promesse coupée (`EmptyError`). Le `catch` de `loadNextTagPage`
  (`inbox.page.ts:377-388`) la traite comme une panne : « Les messages de ces tags n'ont pas pu être chargés »
  s'affiche sur la Boîte de réception.
  - Correctif : ignorer l'abandon dans le `catch`.
  - Test : relâcher la puce pendant qu'une page est en vol n'affiche aucune erreur.
- **C2 — weda2 : lien profond vers un tag, filtre ignoré ou liste bloquée.** Réglages et dossiers sont chargés en
  parallèle (`mss-mail.component.ts:316/356`, `mail-state.service.ts:288/665`). Avec « Non lus » retenu, la première
  page peut partir en `filter=all`. Ensuite :
  - si les réglages arrivent avant la réponse, la clé change, la réponse est jetée et rien ne relance le chargement :
    la liste tourne sans fin ;
  - s'ils arrivent après, « Non lus » est affiché alors que la liste montre aussi les lus.
  - Correctif : attendre les réglages avant la première page d'une vue par tag, ou relancer le chargement quand le
    filtre change.
  - Test sur l'ordre « dossiers, puis page en vol, puis réglages ».
- **C3 — e2e en deçà du catalogue.**
  - E2E-TAG-002, mobile et weda2 : ne vérifie ni la présence ni l'ordre des quatre tags système, « Professionnel de
    santé » compris. À comparer aux quatre premiers dossiers relus du serveur.
  - E2E-TAG-003, mobile : ne lit jamais `tag-view-count`, alors que le catalogue dit « avec leur nombre ».

**Défauts réels à corriger dans la même passe**

- **S1 — Course entre rattrapage et promotion.** Le `SaveChanges` du lot ne tolère pas la violation d'unicité sur
  `MailTags` : si une promotion concurrente pose le même tag, les 200 messages du lot échouent. De plus, les lectures
  de `present` et de `Decided` peuvent être périmées.
  - Correctif : insertion tolérante au conflit, gardée par le bit non décidé (`INSERT … SELECT … WHERE` bit libre
    `ON CONFLICT DO NOTHING`), puis la marque, dans une transaction.
- **S2 — Index partiel sans fin.** Hors Boîte de réception, la marque reste 0 : tous les messages des autres dossiers
  entrent dans `IX_Mails_SystemTagsPending`. Ajouter `AND "FolderPath" = 'INBOX'` au filtre (migration non mergée,
  avec `MailDataContext`).
- **S4 — `MailDto.IsAutomatic` publié mais jamais rempli à la lecture.** Le champ vaut toujours `false` dans les
  réponses : le recopier depuis l'entité dans les projections.
- **S6 — La migration lit du code de domaine** (`SystemTagRule`, `TagNameRule`). Un renommage futur changerait ce
  qu'insère une migration déjà jouée (règle 7c) : figer noms, codes et couleurs en littéraux.
- **Mobile — libellé de l'en-tête de vue** : « N messages non lus » sur le mobile, « N messages » sur weda2, avec le
  même filtre. À aligner sur le nombre servi par le serveur.

#### Arbitrage humain (non bloquant, à trancher au merge)

- **« Pour info » et copie cachée** (`SystemTagRule.cs:141`) : une boîte en copie cachée (absente de « À » et de
  « Cc ») ne passe pas en « Pour info », alors que la US dit « absente de « À » ».
  - Recommandation de la forge : garder « Cc seulement » en v1. Un Cci n'est pas visible dans les en-têtes reçus ; il
    tomberait sous « absente de À », mais sans certitude sur l'adresse.
- **Adresse de la boîte absente du contexte** : la règle « en copie » est alors muette, mais les tags d'en-têtes sont
  marqués décidés, définitivement.
  - Recommandation : ne marquer les bits d'en-têtes décidés que si l'adresse est connue. Cela change le comportement :
    à faire par `/develop` si l'humain l'accepte.
- **Choix d'interface pris par `/develop`** (voir le Develop log, « Décisions prises ») :
  - weda2 : recherche et puce « Bio à acquitter » masquées en vue par tag ; décocher le dernier tag ramène à la Boîte
    de réception ; tableau de bord en non lus ;
  - mobile : puces de l'Accueil reprises du widget ; « Flaggés », « Bio à acquitter » et la vue conversation masqués
    en vue par tag ; un mail reçu en direct n'est pas inséré dans une vue par tag ;
  - api-mcp : dossiers de tag écartés de `list_folders`.

#### Suggestions (non bloquantes, pour la PR)

- **S3** : `GetTagFoldersAsync` regroupe maintenant toutes les lignes `MailTags` de la Boîte de réception, et plus les
  seuls non lus. À vérifier par un plan d'exécution sur une boîte de 10 000 messages.
- **Mobile** : en filtre « Non lus », les pages sont ajoutées avec un décalage. Marquer un message lu avant de charger
  la page 2 peut en faire sauter un : recharger depuis la page 1 après une mutation.
- **Un tag supprimé ailleurs alors que sa vue est ouverte** (les deux clients) : le 404 se rejoue sans fin. Relire les
  dossiers et relâcher le code.
- **weda2 E2E-TAG-003** : l'absence de la ligne du confrère n'est précédée d'aucune présence à l'écran (convention
  `precondition-du-negatif`).
- **weda2 E2E-TAG-002** : nettoyage sans `try` ; compteur comparé sans relance.
- **`SystemTagsRecoveryScheduler`** recopie `AiTaggingRecoveryScheduler` : une base commune, en task dédiée.

### Passage 2 (revue anticipée, après la reprise 1) — CHANGES REQUESTED

Deux relecteurs indépendants ont lu **d'abord le diff de la reprise** (api-mail `d5454ba7..dd90c9dc`, mobile
`66018c5..7e3860f`, weda2 dans l'arbre de travail), puis vérifié chaque constat du passage 1.

- **Constats du passage 1**, tous corrigés et prouvés par un test qui échouerait sans le correctif :
  - backend : B1, B2, B3, B4, S2, S4 (vue par tag), S6 ;
  - clients : C1, C2, C3 et le libellé de l'en-tête ;
  - S1 aussi, mais son correctif crée la régression ci-dessous.
- **Clients : APPROVED.**
- **4b, 4c** : inchangés depuis le passage 1 (catalogue en v1 ; api-mcp adapté, faux positif de forme JSON analysé).

#### À corriger par la reprise

- **B5 — Interblocage entre le rattrapage et la promotion**, introduit par le correctif S1 de la reprise 1
  (`MailRepository.SystemTags.cs:214-250`).
  - Les deux transactions prennent leurs verrous en ordre inverse :
    - le rattrapage insère d'abord ses `MailTags`, puis met à jour `Mails` ;
    - la promotion met à jour `Mails` dans son `SaveChanges` (champs toujours modifiés), puis insère ses `MailTags`.
  - Scénario : à la première ouverture de la boîte après la mise à jour, l'enrichissement programme le rattrapage puis
    promeut la page. Les deux transactions se bloquent mutuellement et PostgreSQL en annule une (40P01) :
    - soit le lot de 200 messages échoue (rejoué 10 min plus tard), ce que S1 devait justement éviter ;
    - soit la promotion échoue et le message n'est pas enrichi.
  - Correctif : verrouiller d'abord les lignes `Mails` du lot, dans l'ordre (`SELECT … ORDER BY "Id" FOR UPDATE`),
    puis faire les insertions. L'ordre devient le même que celui de la promotion, et la garde « bit encore libre » se
    lit après l'attente du verrou.
  - Test d'interblocage vu rouge (40P01) sur le code actuel.
- **Défauts réels à corriger dans la même passe** :
  - **Trace du rattrapage non testée** : affirmer qu'aucun `TagAdded` n'est tracé pour un tag écarté par le conflit ou
    par la garde (service d'audit dans le test de course).
  - **Identifiants en UUID v4** (`gen_random_uuid()`) : la convention task-019 veut des UUID v7 générés côté .NET pour
    la localité de l'index. Générer les `Id` en .NET et les passer en tableau.
  - **`IsAutomatic` dans la liste et dans le message** (`MailRepository.cs:1186`, `:2618`) : ces deux projections ne
    sont pas testées. Ajouter une assertion par route.
  - **Mobile, fenêtre après un abandon** (`inbox.page.ts:346-352`) : après l'abandon d'une page de vue par tag, la fin
    de `loadTagView` s'exécute quand même : chargement éteint, liste vide affichée un instant, flux rebranché sur INBOX
    même si l'on part vers un autre dossier.
    - Correctif : traiter l'abandon comme un remplacement.
    - Spec : `getFolder` laissé en attente (`Subject`), et `isLoading()` reste vrai.

#### Arbitrage humain (non bloquant, à trancher au merge)

- **weda2, choix « Non lus » non enregistré** (réglages en panne) : il est perdu quand « Réessayer » relit des réglages
  « Tous », et la vue repasse en « Tous » sans prévenir.
  - Recommandation de la forge : accepter en v1. La liste et le filtre affiché restent cohérents ; le cas suppose une
    panne des réglages.
- Les arbitrages du passage 1 restent ouverts.

### Passage 3 (revue anticipée, après la reprise 2) — APPROVED

Relecteur indépendant. Il a lu **d'abord le diff de la reprise 2** (api-mail `dd90c9dc..b58d71c0`, mobile
`7e3860f..62cf9ba`) et n'y a trouvé aucune régression :
- ordre des verrous vérifié face à la promotion, à l'ingestion et à la suppression par lot ;
- `FOR UPDATE` tenu jusqu'au commit ;
- `unnest` de deux `uuid[]` correct ;
- test d'interblocage valide, ni vide ni bloquant ;
- compteur d'abandons mobile sans effet sur la pagination, le filtre, le tirage ni C1.

B5 et les défauts du passage 2 sont corrigés et prouvés. La survie de la mutation A1 est jugée acceptable : le `MailDto`
de `GetMailAsync` ne sort par aucune route.

**Approved at** :
- api-mail `b58d71c0` ;
- api-mcp `ac95965` ;
- dtos-mss `ea1af9f` ;
- client-mobile `62cf9ba` ;
- client-angular : arbre de travail de `feature/nova-mss-weda-integration` au 2026-11-17 (fichiers listés dans les
  reprises 1 et 2 du Develop log).

#### Suggestions (non bloquantes, pour la PR)

- **S-1** — Le `FOR UPDATE` du rattrapage est plus fort que nécessaire. Il bloque aussi le verrou de clé étrangère des
  insertions enfants : un passage à « lu » ou un marquage peut attendre une promotion lourde. Une piste :
  `FOR NO KEY UPDATE SKIP LOCKED`, avec un lot restreint aux lignes réellement verrouillées.
- **S-2** — La promotion rattrape une violation d'unicité dans une transaction déjà annulée par PostgreSQL. Si le
  praticien pose à la main un tag système pendant la promotion du message, la promotion échoue en `25P02` et sera
  rejouée. Antérieur à la reprise 2. Une piste : `ON CONFLICT DO NOTHING` dans la promotion.
- **S-3** — Dans le test de course « garde », l'absence de trace n'est pas affirmée. Le mécanisme est le même que dans
  le cas du conflit, déjà prouvé par la mutation T.

### Passage 4 (revue anticipée, après la reprise 3 hors plafond) — APPROVED

Un relecteur indépendant a lu le diff de la reprise 3 : deux fichiers e2e weda2, `OtherDevice.analyse(uid)` et son
appel dans `waitForTagView`.

- **Ce que le correctif pourrait casser** : rien de constaté.
  - L'analyse (`enrich/sync`) ne pose jamais `\Seen`. Les états lu / non lu que TAG-002 et TAG-003 affirment
    (filtre « Non lus », clic sur le compte rendu non lu) restent discriminants.
  - Les compteurs sont comparés à la valeur relue du serveur.
- **Pas de vert qui ment** : les scénarios affirment le classement et son affichage, pas le déclenchement de
  l'analyse par weda2. L'attente précédait déjà `openInbox`. L'aide mobile `waitForTags` fait les mêmes appels.
- **Coût** : une analyse déjà faite se court-circuite (`ComputePendingEnrichmentAsync` nul) ; un appel concurrent
  est absorbé par `MailPromotionClaim`.
- **4a, 4b, 4c** : inchangés depuis le passage 3. Aucun code produit ne change. api-mcp : impact (code 1) déjà
  adapté (`ac95965`).
- **approved at** : api-mail `b95ce350`, api-mcp `ac95965`, dtos-mss `ea1af9f`, client-mobile `62cf9ba`, weda2 arbre
  de travail (reprise 3).
- **Suite de la chaîne** : `/sonar`, `/lint-angular` et `/lint-mobile` ont déjà tourné sur ces SHA, et rien n'a
  changé depuis hors des deux fichiers e2e weda2, sans nouvel avertissement ESLint. La chaîne reprend donc à
  `/e2e`, qui rejoue les voies complètes.

#### Suggestions (non bloquantes, à la PR)

- **S-4** : `functional.e2e.ts:6637` — `.catch(() => null)` jette le statut HTTP. Une analyse en 503 durable
  finirait en « … est dans la vue BIOLOGIE » après 180 s, qui se lit comme une régression du classement. Garder la
  dernière erreur dans le `message` du poll. L'aide mobile a le même trou.

#### Arbitrage humain (non bloquant, à trancher au merge)

- **Trou du filet weda2** : aucun scénario Angular ne prouve que weda2 lui-même déclenche l'analyse d'un message de
  la boîte. Le seul appel `enrichEmailsSync` de `libs/mss` est dans `mail-notification-widget.component.ts:111`.
  - Si la boîte weda2 n'analyse jamais un message, la vue Biologie reste vide pour un médecin qui n'utilise que
    weda2, et la suite resterait verte.
  - Recommandation de la forge : vérifier au test manuel (Manual Test Plan, vue Biologie depuis weda2 seul). Si le
    trou est confirmé, ouvrir une task avec son scénario e2e.

### Validation finale — APPROVED

- **Build et tests** : vert réutilisé, sans rejeu, pour api-mail, api-mcp et client-mobile (marqueurs de
  `/sonar`, `/develop` et `/lint-mobile` sur ces SHA exacts).
  - **dtos-mss** : rejoué, build vert.
  - **weda2** : rejoué, son arbre ayant changé à la reprise 3. `nx build weda2` vert ; `nx test mss-lib` vert,
    157 fichiers et **1 743 tests**.
- **DoD** : vérifiée point par point :
  - migration auditée (7c) ;
  - code mort retiré ;
  - anciennes routes retirées ;
  - contrat publié (614.0.0) ;
  - tests de règle, d'intégration (règle 1b) et de composant vus rouges ;
  - E2E-TAG-002 et E2E-TAG-003 au catalogue et dans les deux clients.
- **E2E** : vert. Voie Angular 87/87, voie mobile réutilisée (66), parité verte.
- **api-mcp** : impact adapté (PR #2).
- **Diff depuis l'approbation** : aucun commit. Les branches étaient déjà à jour avec `develop`, aucune fusion.

### Passage 5 (retour humain après la validation finale, 2026-11-17) — CHANGES REQUESTED

> **Décision humaine du 2026-11-17.** L'humain constate la disparition des tags de classification (Consultation,
> Courrier…) après la task. Il demande leur retour, sauf pour la biologie : « on ne garde que le tag système pour la
> biologie ». Pas de script de repose pour les bases déjà migrées : ce sont des bases de test, des mails seront
> réinjectés. Reprise 4, hors plafond, ordonnée par l'humain.

**Cause** : le task file affirmait que `AddCategoryTagsToMailAsync` était du « code mort, sans appelant ». C'était
faux : `AddDocumentCategoryTagsAsync` l'appelait à l'insertion et à la promotion d'un message (task-344,
`MailRepository.cs:689` et `:819` sur `origin/develop`). `/develop` a retiré toute la chaîne, et la migration
`AddSystemTags` a supprimé tous les tags `CATEGORY` (`DELETE FROM "Tags" WHERE "Type" = 'CATEGORY'`). C'est un choix
produit qu'aucune décision humaine ne portait. Les quatre passages de revue ne l'ont pas relevé.

#### À corriger par la reprise

- **R1 — Tags de catégorie de document rétablis, sauf la biologie** (bloquant, régression produit) :
  - rétablir leur pose dans la transaction de l'insertion et de la promotion d'un message (un tag `CATEGORY` par
    type de document, couleur `#3B82F6`, création concurrente tolérée par `CreateTagOrReadWinnerAsync`) ;
  - **sans** le type de biologie (`SystemTagRule.BiologyDocumentType`, casse indifférente) : la biologie n'est
    portée que par le tag système « Biologie » ;
  - **test d'intégration (règle 1b)**, vu rouge : un message porteur d'un document Consultation et d'un document
    Bio porte `CONSULTATION` (type `CATEGORY`) et `BIOLOGIE` (type `SYSTEM`), jamais `BIO`. Le dossier
    `tag:CONSULTATION` figure dans la liste des dossiers de tags, et sa vue rend le message ;
  - rétablir le test de course `MailRepositoryCategoryTagRaceTests`, adapté à un type autre que Bio.
- **R2 — Migration `AddSystemTags`** : le `DELETE` ne retire plus que le tag de catégorie de la biologie (`Code` =
  `BIO`, `Type` = `CATEGORY`), avec ses poses en cascade. Les autres tags `CATEGORY` restent. Mettre à jour la
  documentation de la migration et refaire l'audit 7c.
- **R3 — Miroirs TypeScript** : le type de tag `CATEGORY` existe de nouveau dans les dossiers de tags. Ajouter
  `CATEGORY` à `TagKind` (client-mobile) et au commentaire de `tagType` (weda2).
- **R4 — Develop log** : corriger le paragraphe « Code mort retiré » (seule la surcharge publique
  `IMailRepository.AddCategoryTagsToMailAsync`, et son double dans `Infrastructure.Mock`, étaient sans appelant).
- **Hors reprise** : aucun script de repose des tags de catégorie sur les bases déjà migrées (décision humaine).

### Passage 6 (revue anticipée, après la reprise 4) — CHANGES REQUESTED, comblé dans la reprise 4

Relecteur indépendant, sur `a9859b87` (api-mail) et `71dc3b2` (client-mobile). Il a d'abord cherché ce que le
correctif pouvait casser :
- les décisions des tags système, le rattrapage et ses verrous : rien de cassé ;
- les dossiers, vues et compteurs : rien de cassé ;
- le mobile : rien de cassé.

La conformité à la décision du 2026-11-17 est vérifiée : insertion et promotion dans la transaction, exclusion de
Bio par le prédicat du tag système, idempotence, création concurrente, migration.

- ❌ **Atomicité de la pose de catégorie sans preuve** (corrigeable) : la reprise n'avait rétabli que deux des
  trois cas de `MailRepositoryCategoryTagRaceTests`, en invoquant `MailIngestionWriteOrderTests`. Or celui-ci
  provoque sa panne sur `MailMedicalDocuments`, dans l'écriture principale. Si la pose de catégorie passait après le
  commit (le défaut AUD-36), plus aucun test ne rougissait.
  **Comblé dans le périmètre de la reprise 4**, puisque R1 demandait de rétablir ce test. Ce n'est donc pas une
  5e reprise. Commit `9c6f6a43` :
  - le cas `AddNewMail_WhenAStepAfterTheMailInsertFails_LeavesNoMailBehind` est rétabli à l'identique de `develop` ;
  - **vu rouge par mutation** : pose déplacée après `transaction.CommitAsync()` → `Assert.False` échoue (un message
    reste en base). Restauré ; les 78 tests des classes touchées sont verts.
- ⚠️ Commentaire faux (`MailIngestionWriteOrderTests`, son document est de type « Biologie », pas « Bio ») et
  documentation de `GetTagFoldersAsync` périmée : corrigés dans `9c6f6a43`.
- ⚠️ La mutation de l'appel de **promotion** n'est pas consignée. L'assertion existe pourtant : le test vérifie que
  la vue IMAGERIE ne rend que le premier message avant la promotion, puis les deux après.
- **Règle 1b** : chaque comportement a son test et sa preuve rouge. Pose de catégorie à l'insertion et à la
  promotion, et exclusion de Bio → `TheDocumentCategoryTags_…` (404, puis mutation de l'exclusion). Migration →
  `AddSystemTagsMigrationTests` (mutation). Atomicité → test AUD-36 (mutation).
- **api-mcp (4c)** : `mcp_impact.py check` rend 1 sur `MailController.cs`, surface que la reprise ne touche pas.
  L'impact est celui de la task, déjà adapté (PR api-mcp #2).
- **Scénario e2e (4b, clause DoD)** : la reprise ne crée ni ne change aucun parcours.

#### Arbitrage humain
- **Pose des tags de catégorie non tracée au journal.** Comme sur `develop`, et comme les tags IA, la pose n'est pas
  tracée en acte système, alors que les tags système le sont (`TraceSystemTags`). Ce n'est pas une régression : la
  décision était « comme avant ». La règle 14 veut cependant que tout acte sans personne soit tracé comme acte
  système. *Recommandation de la forge* : une task séparée qui trace la pose des tags de catégorie et IA, pour ne
  pas rouvrir task-456.
- **Un tag « BIO » de type IA survit à la migration.** Si l'IA a créé un tag de code `BIO` avant toute catégorie,
  la migration le garde, avec ses poses, puisque le `DELETE` vise le type `CATEGORY`. Le code ne le pose plus en
  catégorie. *Recommandation* : accepter, le cas est rare et ne touche que d'anciens messages de bases de test.

### Passage 7 (revue anticipée, complément de la reprise 4) — APPROVED

Le même relecteur indépendant a vérifié `9c6f6a43`. Le test AUD-36 est rétabli à l'identique de `develop`, et il
provoque bien sa panne sur la pose de catégorie. Le seul changement de `src` est un commentaire, et les
commentaires sont exacts. Restent les ⚠️ et les arbitrages du passage 6, non bloquants.

- **approved at** : api-mail `9c6f6a43`, client-mobile `71dc3b2b`. weda2 : arbre de travail, seul le commentaire de
  `folder.model.ts` change. api-mcp et dtos-mss : inchangés depuis la validation finale.

### Validation finale après la reprise 4 — APPROVED

- **Build et tests** : vert réutilisé sur le code exact, sans rejeu :
  - api-mail `9c6f6a43` (`/sonar`, 8 058 tests) ;
  - client-mobile `71dc3b2b` (`/develop`, 1 506 tests) ;
  - weda2 `f0e9ee95` + arbre de travail (`/lint-angular`, 1 743 tests) ;
  - api-mcp `ac959658` et dtos-mss `ea1af9f0`, inchangés.
- **Diff depuis l'approbation** (`9c6f6a43`, `71dc3b2b`) : aucun commit. Branches à jour avec `develop`, aucune fusion.
- **DoD** : inchangée et tenue. La ligne « code mort retiré » est corrigée par la reprise 4 : seule la surcharge
  publique sans appelant reste retirée.
- **Règle 1b** : la table comportement → test → preuve rouge est au passage 6.
- **E2E** : vert. Mobile 66/66, Angular 87/87, parité verte, porte en code 0.
- **api-mcp** : impact inchangé, déjà adapté (PR #2).
- **PRs** : les quatre corps sont mis à jour (section « Reprise 4 », arbitrages ouverts, nouveau « Parcours e2e »).
  Le label `awaiting-human-merge` est conservé.

### Passage 8 (retour humain, 2026-11-17) — CHANGES REQUESTED

> **Décision humaine du 2026-11-17** : « si un tag a 0 éléments, il ne s'affiche pas ». La règle « un tag système est
> toujours affiché, même à zéro » est retirée de l'Objectif. Reprise 5, hors plafond, ordonnée par l'humain.
> Lecture retenue : « 0 élément » veut dire aucun message de la Boîte de réception, ni lu ni non lu. Un tag dont
> tous les messages sont lus reste affiché, puisque sa vue « Tous » n'est pas vide.

#### À corriger par la reprise

- **R5 — Un tag système sans message n'est pas listé** (api-mail, `GetTagFoldersAsync`) :
  - les quatre tags système ne sont listés que s'ils portent au moins un message de la Boîte de réception, lu ou
    non, comme les autres tags. Quand ils sont listés, ils restent en tête, dans l'ordre de la règle ;
  - **test d'intégration (règle 1b)**, vu rouge : une boîte où seul « Patient » porte un message ne liste que
    `tag:PATIENT` parmi les tags système. Un tag système dont le seul message est lu reste listé ;
  - les tests qui affirment l'ancienne règle passent à la nouvelle : `CountingQueriesEndToEndTests`
    (`…OnlyTheFourSystemTagsAtZero`) et `MailRepositoryTests` (`…TheFourSystemTagsAtZero…`) ;
  - les clients relisent la liste au serveur (weda2 par `tagCountChanged$`, mobile par `tagFolders`). Vérifier
    qu'aucun spec client ni scénario e2e n'attend un tag système à zéro.
- **Doc** : commentaire de `GetTagFoldersAsync` et develop log (« Dossiers de tag ») alignés.

### Passage 9 (revue anticipée, après la reprise 5) — CHANGES REQUESTED, comblé dans la reprise 5

Relecteur indépendant, sur `3ee8c973` (api-mail), `7aefb357` (mobile) et l'arbre weda2.
- ✅ **Serveur** : conforme à la décision.
  - La route `GET tags/emails?tag=X` rend une page vide en 200 pour un tag sans message : la ligne `Tags` reste.
  - Les autres consommateurs de la liste (dossiers, tableau de bord, hors ligne) ne supposent pas quatre tags
    système.
- ✅ **Tests serveur** : rouges si l'on annule le changement. E2E-TAG-002 est en v2 dans les deux clients.
- ❌ **Mobile, vue par tag orpheline** (corrigeable) : `setFolders` ne relâchait pas une puce active dont le tag
  avait disparu de la liste.
  - Scénario : le praticien archive le dernier message de la vue « Pour info », puis rafraîchit. La vue restait
    ouverte, sans nom, sur « 0 message ». Choisir « Boîte de réception » dans le menu ne la relâchait pas.
  - La reprise étend ce défaut, préexistant pour les tags IA et utilisateur, aux quatre tags système.
  **Comblé dans la reprise 5**, puisqu'il naît de la décision qu'elle applique. Commit `f3069875` :
  - `MailStateService.setFolders` relâche les puces dont le tag n'est plus listé, et rend `true` quand il en a
    relâché ;
  - le menu latéral rouvre alors la Boîte de réception par `folderChanged$`. La page, elle, la recharge déjà après
    `setFolders` ;
  - **vu rouge** : 3 specs sur le code d'avant. `releases an active chip…` (« Expected undefined to be true »),
    `keeps the active chips…` et `reopens the whole inbox…` (« Expected true to be false »). Après le correctif :
    1 510/1 510, build vert, lint propre.
- ⚠️ **weda2, même situation, sans blocage** : « Boîte de réception » ferme la vue par tag (`closeTagView`), mais
  l'en-tête montre le code brut (« POUR INFO ») avec « 0 message ». Non corrigé dans cette reprise : suggestion
  reportée dans la PR.
- ⚠️ Corrigés : commentaires et donnée de test weda2 (`mail-widget.component.spec.ts`, un tag système listé a
  désormais au moins un message), commentaire de `functional.e2e.ts`, ligne « Dossiers de tag » du develop log.
  Weda2 : `nx test mss-lib` 1 743 et build verts, vert marqué.
- ⚠️ Suggestions non retenues :
  - un test d'ordre `[PATIENT, IMAGERIE]` ;
  - une assertion « page vide en 200 » après le retrait du tag, dans le test d'intégration.

#### Arbitrage humain
- **weda2 — vue par tag dont le tag disparaît** : faut-il aussi la refermer automatiquement, comme sur mobile ?
  *Recommandation de la forge* : oui, dans une task courte, pour que les deux clients se comportent pareil.

### Passage 10 (revue anticipée, complément de la reprise 5) — APPROVED

Le même relecteur indépendant a vérifié `f3069875`. Le bloquant est levé, et les autres appelants de `setFolders`
ne sont pas cassés :
- `inbox.page` `loadFolders` et `onFolderGone` : les puces sont relâchées avant le rechargement ;
- les Paramètres n'appellent `setFolders` que sur une liste vide ;
- le menu latéral rouvre la Boîte de réception.

Les nouveaux tests ne mentent pas. Suggestion : un test de `inbox.page` sur le tirer-pour-rafraîchir en vue par tag
quand le tag a disparu.

- **approved at** : api-mail `3ee8c973`, client-mobile `f3069875`, weda2 `f0e9ee95` + arbre de travail. api-mcp
  et dtos-mss : inchangés.

### Validation finale après la reprise 5 — APPROVED

- **Build et tests** : vert réutilisé sur le code exact :
  - api-mail `9697e4f6` (`/sonar`, 8 059 tests) ;
  - client-mobile `f3069875` (`/develop`, 1 510) ;
  - weda2 `f0e9ee95` + arbre (`/develop`, 1 743) ;
  - api-mcp `ac959658` et dtos-mss `ea1af9f0`, inchangés.
- **Diff depuis l'approbation** (`3ee8c973` → `9697e4f6`) : le correctif S3267 de `/sonar`. C'est un pur passage en
  LINQ, au comportement identique (même ordre, même filtre ; `tag.Code` égal à `system.Code`) : ✅. Branches à jour
  avec `develop`.
- **DoD et Objectif** : la règle d'affichage des tags est amendée par la décision humaine du 2026-11-17 (Objectif,
  section « Vues par tag »). Le reste est inchangé.
- **Règle 1b** : `ASystemTagWithoutMail_IsNotListed_…` et `AMailboxWithoutTags_…_AndNoTagFolder`, vus rouges.
- **E2E** : vert. Mobile 66/66, Angular 87/87, porte en code 0, E2E-TAG-002 v2 au catalogue et dans les deux
  clients.
- **api-mcp** : impact inchangé, déjà adapté (PR #2).
- **PRs** : les quatre corps sont mis à jour (section « Reprise 5 », arbitrage weda2, nouveau « Parcours e2e ») ;
  le label `awaiting-human-merge` est conservé.

## PRs

Corps mis à jour le 2026-11-17 après la reprise 4 (tags de catégorie rétablis sauf la biologie).

À merger ensemble (même US, règle 11), dans cet ordre : dtos-mss → api-mail → api-mcp → client-mobile. Label
`awaiting-human-merge`.

- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/68
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/372
- `api-mcp` : https://github.com/codengine-technologies/HealthPlatform.Api.Mcp/pull/2
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/127
- `client-angular` (code-only) : l'humain gère le commit, le push vers TFS et l'ouverture de la PR, sur la branche
  `feature/nova-mss-weda-integration`. L'arbre porte aussi les fichiers non commités de task-486 (saisie des tags) :
  les commiter d'abord garde deux lots lisibles. Fichiers modifiés (task-486 et task-456 mêlés) :
  - `front/e2e/mss-e2e/specs/functional.e2e.ts`
  - `front/e2e/mss-e2e/support/e2e-backend.ts`
  - `front/libs/mss/src/core/models/folder.model.ts`
  - `front/libs/mss/src/core/models/mail.model.ts`
  - `front/libs/mss/src/core/models/user-settings.model.ts`
  - `front/libs/mss/src/core/services/mss-api.service.ts`
  - `front/libs/mss/src/features/mail/components/mail-folder-item/mail-folder-item.component.html`
  - `front/libs/mss/src/features/mail/components/mail-folder-list/mail-folder-list.component.html`
  - `front/libs/mss/src/features/mail/components/mail-folder-list/mail-folder-list.component.scss`
  - `front/libs/mss/src/features/mail/components/mail-folder-list/mail-folder-list.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.html`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.scss`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.search-mode.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-tag/mail-tag.component.html`
  - `front/libs/mss/src/features/mail/components/mail-tag/mail-tag.component.scss`
  - `front/libs/mss/src/features/mail/components/mail-tag/mail-tag.component.ts`
  - `front/libs/mss/src/features/mail/mss-mail.component.ts`
  - `front/libs/mss/src/features/mail/services/mail-event.service.ts`
  - `front/libs/mss/src/features/mail/services/mail-state.service.ts`
  - `front/libs/mss/src/ui/mail-widget/mail-widget.component.html`
  - `front/libs/mss/src/ui/mail-widget/mail-widget.component.ts`
  - non suivis :
    - `front/libs/mss/src/core/services/mss-api.tag-view.service.spec.ts`
    - `front/libs/mss/src/core/services/mss-api.tags.service.spec.ts`
    - `front/libs/mss/src/core/utils/tag-suggestions.util.spec.ts`
    - `front/libs/mss/src/core/utils/tag-suggestions.util.ts`
    - `front/libs/mss/src/features/mail/components/mail-folder-list/mail-folder-list.tags.spec.ts`
    - `front/libs/mss/src/features/mail/components/mail-list/mail-list.tag-view.spec.ts`
    - `front/libs/mss/src/features/mail/components/mail-tag/mail-tag.component.spec.ts`
    - `front/libs/mss/src/features/mail/mss-mail.component.tag-view-settings.spec.ts`
    - `front/libs/mss/src/features/mail/mss-mail.component.tag-view.spec.ts`
    - `front/libs/mss/src/features/mail/services/mail-state.service.tag-view.spec.ts`
    - `front/libs/mss/src/ui/mail-widget/mail-widget.component.spec.ts`

## Timings

*(généré par `tools/timing/report.sh --task task-456 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 28 s | — | — | — | — |
| /develop | ok | 13 min 10 s | 16 (1 min 38 s) | 29 (53 min 59 s) | — | api-mail 8B/20T, api-mcp 2B/2T, client-mobile 4B/5T, client-angular 2B/2T, e2e ×1 (1 min 16 s) |
| /review-code | ok | 13 min 42 s | — | — | — | — |
| /sonar | ok | 20 min 18 s | 5 (2 min 44 s) | 25 (38 min 56 s) | 10 (3 min 55 s) | 1 itération(s), api-mail 5B/25T |
| /lint-angular | ok | 42 s | 2 (20 s) | 4 (2 min 13 s) | — | client-angular 2B/4T |
| /lint-mobile | ok | 24 s | — | — | — | — |
| /e2e | ok | 23 min 01 s | — | — | — | e2e ×18 (2 h 47 min) |
| /review | ok | 50 s | 2 (14 s) | 1 (30 s) | — | dtos-mss 1B/0T, client-angular 1B/1T |
| /tech-writer | ok | 13 s | — | — | — | — |
| **Total cycle** | | **1 h 12 min** | **25 (4 min 57 s)** | **59 (1 h 35 min)** | **10 (3 min 55 s)** | |

Autres commandes mesurées : lint ×8 (2 min 13 s), nuget-wait ×1 (40 s)

## Merged

Mergé le 2026-11-17 par `/merge task-456 --i-tested` (test humain attesté), en squash, dans l'ordre dtos-mss →
api-mail → api-mcp → client-mobile. Branches `feat/task-456-tags-systeme-et-vues-par-tag` supprimées (distantes et
locales), label `awaiting-human-merge` retiré.

| Repo | PR | Commit squash sur `develop` | CI `develop` |
|---|---|---|---|
| dtos-mss | #68 | `af229d42` | ✅ [.NET](https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/actions/runs/44083982858) |
| api-mail | #372 | `fe801f26` | ✅ [Build and Publish](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/44084010089) |
| api-mcp | #2 | `34469f10` | — (aucune CI sur ce dépôt) |
| client-mobile | #127 | `124578ab` | ✅ [Android Build](https://github.com/codengine-technologies/HealthPlatform.Mobile/actions/runs/44084075773) |

client-angular (weda2) : managed manually by the human (code-only, TFS).
