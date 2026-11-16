# todo-task-456.md — Tags système et vues par tag : biologie, patient, professionnel de santé, pour info

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
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
- `dtos-mss` (paresseuse) : aucune branche au /start — créée par /develop au premier changement de contrat (`TagDto`, `FolderDto`)
- `client-angular` (code-only) : la forge écrit sur la branche checked out dans `Client/Angular/` (au /start : `feature/nova-mss-weda-integration`) — humain gère branche, commit, push, PR TFS. ⚠️ L'arbre porte encore les 9 fichiers non commités de task-486 (saisie des tags) : task-456 les modifie à son tour ; les commiter vers TFS avant celles de task-456 garde deux lots lisibles.

## Timings

*(généré par `tools/timing/report.sh --task task-456 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 28 s | — | — | — | — |
| **Total cycle** | | **28 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |
