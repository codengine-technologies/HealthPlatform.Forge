# todo-task-486.md — Saisie des tags : espaces acceptés et liste de choix

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
**Reprises**: 2
**Dependencies**: aucune
**Epic**: E024

**Priorité**: EPIC E024, demandée par l'humain le 2026-11-16, en réécrivant task-456 (les vues par nature deviennent
des vues par tag). Plus les tags servent à lire la boîte, plus leur saisie doit être rapide et sans refus
incompréhensible. Peut passer avant ou après task-456 : la liste de choix propose les tags qui existent.

> **Constat humain du 2026-11-16** : un tag qui contient un espace est refusé. Le refus vient du serveur :
> `MailController.cs:1805`, `if (request.TagName.Contains(' ')) throw new ValidationException("Tag name must not
> contain spaces.")`. Le nom est aussi plafonné à 20 caractères (`:1800`), alors que le tag système
> « Professionnel de santé » de task-456 en compte 22.

## Ce qui est établi

- `POST api/v1/Mail/folders/{foldername}/emails/{emailid}/tags` (`AddTagRequest.TagName`) pose un tag ; tracé
  `TagAdded` au nom de la personne.
- Le code d'un tag est `NormalizeTagCode(nom)` : majuscules, sans accents. Un tag de même code est réutilisé, jamais
  dupliqué.
- **Des codes avec espace existent déjà** : les tags IA « Très urgent » (code `TRES URGENT`) passent par
  `EmailTaggingService`, sans la validation du contrôleur. Les routes `tags/{tagcode}/…` les servent (le contrôleur
  décode le code avec `Uri.UnescapeDataString`).
- **Aucune route ne liste les tags de la boîte** : `GetTagFoldersAsync` ne rend que les tags qui ont un non lu.
- Saisie actuelle : un champ libre sans suggestion, dans weda2 (`mail-tag.component`, `data-testid="mail-tag-input"`)
  et sur mobile (`mail-detail.component`).
- Les tags appartiennent à la **boîte** (règle 14) : toutes les personnes de la boîte partagent la même liste.

## Objective

Poser un tag se fait en quelques touches : on tape le début d'un nom, la liste propose les tags de la boîte, on
choisit. Un nom de plusieurs mots est accepté.

Règles :
- **Espaces acceptés** : le nom est nettoyé (espaces de début et de fin retirés, espaces internes consécutifs réduits
  à un seul) et garde sa casse et ses accents à l'affichage. « Courrier urgent », «  courrier   URGENT  » et
  « Courrier Urgent » désignent le **même** tag (même code).
- **Longueur** : 40 caractères au plus après nettoyage. Refusés : un nom vide, un caractère de contrôle. Refus en
  `ProblemDetails` (400), avec un `detail` en français lisible par le praticien.
- **Liste de choix** à l'ouverture de la saisie :
  - elle propose **tous les tags de la boîte** : système, IA, utilisateur ;
  - elle se filtre à la frappe, sans tenir compte de la casse ni des accents ; les tags qui **commencent** par le
    texte saisi d'abord, puis ceux qui le **contiennent** ;
  - les tags déjà posés sur le message n'y figurent pas ;
  - clavier : flèches pour parcourir, Entrée pour choisir, Échap pour fermer ;
  - si aucun tag n'a exactement ce nom, la dernière ligne propose « Créer le tag « … » » ;
  - sur mobile, la même liste sous le champ, au toucher.
- **Liste des tags de la boîte** servie par le serveur (par exemple `GET api/v1/Mail/tags`), avec nom, code, type et
  couleur, triée : système, IA, utilisateur, puis alphabétique.

### Hors périmètre

- Renommer, recolorer ou supprimer un tag de la boîte.
- Les vues par tag, les tags système et la combinaison de tags : task-456.

## Definition of Done

- [ ] Validation du nom de tag : espaces acceptés, nettoyage, 40 caractères, caractères de contrôle refusés ;
      `detail` en français. Tests unitaires de la normalisation (espaces multiples, casse, accents → même code).
- [ ] Route de liste des tags de la boîte ; `TagDto` (dtos-mss) publié si le contrat change ; miroirs TypeScript.
- [ ] **Test d'intégration de bout en bout (règle 1b)** : poser « Courrier urgent » → 200, le tag est relu sur le
      message et dans la liste des tags ; poser «  courrier   URGENT  » sur un autre message → même tag, pas de
      doublon dans la liste ; un nom de 41 caractères → 400 en `ProblemDetails` ; la liste rend les tags système, IA
      et utilisateur dans l'ordre. Vu rouge (le refus actuel des espaces fait échouer le premier cas).
- [ ] Tests de composant (weda2 et mobile), vus rouges par mutation : liste ouverte à la saisie, filtre sans
      casse ni accents, tags déjà posés exclus, Entrée choisit, « Créer le tag » quand aucun nom exact.
- [ ] **Scénario e2e**, mobile et angular requis, vu rouge :
      - `E2E-TAG-001` v1 : sur un message, taper « cour », choisir « Courrier urgent » dans la liste ; créer un tag
        « Avis cardio » avec un espace ; les deux tags apparaissent sur le message.
- [ ] `data-testid` sur la liste et ses lignes, conventions de libellés, aucune donnée de santé dans les libellés
      ni les logs.
- [ ] Build et tests verts (api-mail, weda2, mobile) ; client-angular : code-only.

## Manual Test Plan

1. Backend et weda2 lancés sur la boîte de formation de Virginie.
2. Ouvrir un message, cliquer sur « + » des tags : la liste des tags de la boîte s'affiche.
3. Taper « urg » : « Urgent », « Très urgent » et les tags utilisateur qui contiennent « urg » ; Entrée pose le
   premier.
4. Taper « Avis cardio » : la dernière ligne propose « Créer le tag « Avis cardio » » ; le choisir : le tag est posé.
5. Sur un autre message, taper « avis CARDIO » : la liste propose « Avis cardio » existant, pas de doublon créé.
6. Mobile : même parcours depuis le détail d'un message.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — organisation du travail
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : inchangée — PSC (e-CPS), eIDAS substantiel
- **Habilitations** : titulaire, membre, délégataire, sous verdict de l'opérateur (règle 14)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : `TagAdded` au nom de la personne, inchangé ; la lecture de la liste des tags n'est pas un accès
  à une donnée de santé
- **Consentement patient** : non applicable
- **Référentiels métier** : non applicable
- **Hébergement HDS** : oui — base de la boîte
- **AIPD / impact RGPD** : inchangé

## Branches
- `api-mail` (pushed) : feat/task-486-saisie-des-tags-espaces-et-liste-de — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-486-saisie-des-tags-espaces-et-liste-de
- `client-mobile` (pushed) : feat/task-486-saisie-des-tags-espaces-et-liste-de — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-486-saisie-des-tags-espaces-et-liste-de
- `dtos-mss` (paresseuse) : aucune branche au /start — créée par /develop s'il touche un contrat (`TagDto`)
- `client-angular` (code-only) : la forge écrit sur la branche checked out dans `Client/Angular/` (au /start : `feature/nova-mss-weda-integration`) — humain gère branche, commit, push, PR TFS

## Develop log

- Repos touched : `api-mail`, `client-mobile` (pushés), `client-angular` (code-only, non commité sur
  `feature/nova-mss-weda-integration`). `dtos-mss` : **aucune branche** — `TagDto` portait déjà `Name`,
  `Code`, `Type`, `ColorCode` : contrat inchangé, rien à publier.
- DTOs published : no DTO change. Interop published : no interop change.
- api-mcp : aucun impact (`python Tools/contracts/mcp_impact.py check` → 0).
- Commits :
  - api-mail : `c667a523` feat(mail): saisie des tags — espaces acceptés, 40 caractères, liste des tags de la boîte ;
    `39533f9a` test(e2e): E2E-TAG-001 — jeton propre à l'essai ;
    `0956bcad` test(mail): bases neuves du test de migration des tags sans pool Npgsql
  - client-mobile : `bbd68f3` feat(mobile): saisie des tags — liste des tags de la boîte sous le champ ;
    `2690b9c` test(e2e): E2E-TAG-001 — jeton propre à l'essai
  - client-angular (non commité, à commiter par l'humain vers TFS) :
    `libs/mss/src/core/utils/tag-suggestions.util.ts` (+ `.spec.ts`), `libs/mss/src/core/services/mss-api.service.ts`
    (`getMailboxTags`), `libs/mss/src/core/services/mss-api.tags.service.spec.ts`,
    `libs/mss/src/features/mail/components/mail-tag/mail-tag.component.{ts,html,scss,spec.ts}`,
    `e2e/mss-e2e/specs/functional.e2e.ts` (E2E-TAG-001 ; commentaire périmé « pas d'espace » de E2E-DETAIL-004 corrigé).

### api-mail
- **`TagNameRule`** (`src/Domain/Rules`) : nom nettoyé (bords retirés, espaces internes réduits à un seul, casse et
  accents gardés), 40 caractères au plus **après nettoyage**, caractère de contrôle refusé ; refus en français
  (« Le nom du tag est obligatoire. », « … ne doit pas dépasser 40 caractères. », « … contient un caractère non
  autorisé. ») ; `Code` = nom nettoyé, majuscules, sans accents (même calcul qu'avant, `NormalizeTagCode` y délègue,
  pour le praticien, l'IA et l'analyse des documents) ; `KindRank` : SYSTEM et CATEGORY 0, AI 1, USER 2, autre 3.
- **`POST …/emails/{uid}/tags`** : l'ancien refus des espaces et le plafond de 20 sont remplacés par la règle ; le
  service reçoit le nom nettoyé ; refus 400 `ProblemDetails` via `ValidationException` (règle 12).
- **`GET api/v1/Mail/tags`** (`GetMailboxTagsAsync`, `[TraceExempt]` : noms de classement, aucune donnée de santé) :
  tous les tags de la boîte (règle 14 : une base par boîte), triés système → IA → utilisateur → code (casse et accents
  ignorés). Pas de `catch` : une panne de base remonte au `GlobalExceptionHandler`.
- **Défaut découvert** : `Tags.Name` / `Tags.Code` étaient des `varchar(20)` (`SetupMigration`). Sans élargissement,
  tout nom de 21 à 40 caractères accepté par la validation finissait en **500**. Migration
  **`WidenTagNames` (20261116203100**, heure réelle, postérieure à `20261113130000`, dernière d'`origin/develop`) :
  les deux colonnes passent à 40 ; descente : suppression des tags > 20 caractères puis retour à 20. Audit 7c : un
  seul `ALTER` par colonne, aucune opération fantôme, `MailDataContext` déclare `HasMaxLength(TagNameRule.MaxLength)`
  (FluentMigrator : pas de snapshot ni de `.Designer`). Le tag système « Professionnel de santé » (22) de task-456
  en dépendait.
- **Catégorie CATEGORY** rangée avec les tags système (posés par l'analyse des documents, sans geste du praticien) —
  task-456 introduira `SYSTEM`, déjà classé en tête.

### Tests et preuves rouges (règle 1b)
- Unitaires : `TagNameRuleTests` (29 cas : nettoyage, même code pour espaces / casse / accents, 40 vs 41, contrôle,
  messages FR, rang des types) ; `MailControllerTests` (refus FR avant tout appel au service, nom nettoyé transmis,
  liste rendue).
- Intégration de bout en bout (`FolderOperationsEndToEndTests.TagEntry.cs`, vraie pile HTTP, vrais services, base
  PostgreSQL de la boîte construite par le coureur FluentMigrator, Dovecot) :
  - `ATagOfSeveralWords_IsSet_ReadOnTheMessage_AndListedOnceForTheMailbox` : « Courrier urgent » → 200 ; «  courrier
    URGENT  » sur un autre message → **même `Id`** ; relu sur les deux messages (`GET …/emails/{uid}`) ; **une seule**
    ligne dans `GET /tags` et en base ;
  - `ANameOfFortyOneCharacters_IsRefusedWith400ProblemJson_InFrench_AndNothingIsCreated` : 41 → 400
    `application/problem+json`, `detail` français, rien créé ; 40 après réduction des espaces → 200 ;
  - `TheMailboxTags_AreListedSystemFirst_ThenAi_ThenUser_ThenAlphabetically` : SYSTEM, AI, USER puis alphabétique,
    nom / type / couleur lus dans la réponse.
- Migration : `WidenTagNamesMigrationTests` (coureur de production sur base neuve : 40 stocké après, refusé avant,
  descente sans les tags longs puis remontée).
- **Mutations** (fichier copié, restauré, rebuild ; résultats dans la réponse réelle) :
  | Mutation | Rouges |
  |---|---|
  | refus des espaces réinjecté dans le contrôleur | les 3 tests e2e d'intégration (400 « must not contain spaces » au lieu de 200) |
  | tri remplacé par un ordre quelconque | `TheMailboxTags…` (attendu BIOLOGIE, reçu COURRIER URGENT) |
  | migration rendue vide | `ANameOfFortyOne…` (500 sur 40 caractères), 2 tests de migration |
  | plafond de 40 neutralisé | `ANameOfFortyOne…` (500 au lieu de 400) |
  | nom brut transmis + code sans nettoyage | `ATagOfSeveralWords…` (`Id` différent : doublon), `ANameOfFortyOne…` |
- Code restauré → 6/6 verts.

### client-angular (weda2, code-only)
- `MailTagComponent` passe en `input()` / `output()` ; à l'ouverture de la saisie, `GET /tags` ; liste de choix
  (`role="listbox"`, `data-testid="mail-tag-suggestions"`, lignes `mail-tag-suggestion` + `data-tag-code`, ligne
  `mail-tag-create`) filtrée à la frappe par `tagChoices` (sans casse ni accents, « commence par » puis « contient »,
  tags posés exclus, « Créer le tag « … » » sans nom exact) ; flèches / Entrée / Échap ; la première ligne est
  désignée dès qu'un texte est saisi (Entrée pose « le premier », plan de test) ; clic principal sans modificateur
  seulement (`conventions/angular.md`, suggestions-de-saisie-choisies-visibles) ; une réponse arrivée après la
  fermeture est ignorée.
- Tests : `tag-suggestions.util.spec.ts` (7), `mail-tag.component.spec.ts` (10), `mss-api.tags.service.spec.ts` (2).
  Mutations (5) : exclusion des posés, repli des accents, ligne « Créer », Entrée sur la ligne désignée, chargement à
  l'ouverture — chacune rouge sur ses tests (3 à 7 rouges), restauré vert.
- Build `nx build weda2` vert ; `nx test mss-lib` **150 fichiers, 1 689 tests** verts ; ESLint des fichiers touchés :
  0 erreur (avertissements préexistants) ; Prettier : fichiers neufs formatés, HTML propre en HEAD donc `--write`
  limité à la task ; CRLF partout.

### client-mobile
- `mail-detail` : la liste sous le champ remplace les « suggestions » d'avant (qui ne venaient que des dossiers de
  tags **ayant un non-lu**) ; source `GET /tags` ; même logique (`core/utils/tag-suggestions.util.ts`) ; lignes de
  44 px au toucher ; doublon jugé sur la clé du code serveur. `/stitch-design` non appelé : aucun écran créé ni
  réécrit (bloc de saisie d'un écran existant).
- Tests : util (6), composant (8 nouveaux + 3 existants adaptés, `identity.spec` adapté). Mutations (5) : exclusion,
  accents, « Créer », Entrée, chargement — chacune rouge (2 à 5), restauré vert.
- Build vert ; Karma **1 467 / 1 467** ; ESLint 0 erreur.

### Parcours e2e — E2E-TAG-001 v1 (catalogue `Api/Mail/e2e/scenarios.yml`, mobile et angular requis)
- Deux messages déposés hors application ; « Courrier urgent <jeton> » créé sur le premier ; sur le second, « cour »
  propose le tag existant (`data-tag-code`) et « Créer le tag « cour » », on le choisit ; « Avis cardio <jeton> » créé
  par la dernière ligne ; chaque POST lu (200, corps envoyé, tag rendu) ; **relu du serveur** (mobile :
  `OtherDevice.mailBySubject(...).tags` ; weda2 : puces de l'en-tête après réouverture).
- Le jeton propre à l'essai rend le test **rejouable** (retries: 1) : les tags créés restent en base jusqu'au reset du
  run. Vérifié en rejouant le test sur une base qui portait déjà les tags du premier passage.
- Rejoué seul, backend e2e monté (`--serve-only`) : mobile vert, weda2 vert ; `E2E-DETAIL-004` (pose d'une étiquette
  au clavier) toujours vert.
- Mutations côté client, app servie : sans ligne « Créer » → rouge « « Créer le tag » est proposé » ; sans « commence
  par » → rouge « la liste propose le tag de la boîte qui commence par « cour » », sur **les deux** voies ;
  restauré → vert.

### Passe qualité (§Q)
- Relecture des trois diffs (réutilisation, simplification, efficacité, altitude) : **aucune simplification
  retenue**. Le doublon de projection `Tag → TagDto` du dépôt (4 sites, dont 3 antérieurs) est laissé tel quel :
  le factoriser toucherait des chemins hors task. La logique de liste est dupliquée entre weda2 et mobile par
  construction (deux dépôts).
- Skipped (contract/excluded) : dtos-mss (non touché).

### Suites complètes
- api-mail : deux suites complètes de suite avec **6 rouges `MailboxPrefillIntegrationTests` en `53300: too many
  clients`**, verts seuls. Rouge identique deux fois = une cause, pas un flaky : les 3 bases neuves de
  `WidenTagNamesMigrationTests` étaient ouvertes avec le pool Npgsql par défaut dans la collection `PostgreSql`
  (même conteneur que `MailboxPrefill`). Correctif `0956bcad` (`Pooling = false`) → **suite complète verte sur l'état
  poussé** : domaine 302, infra 750, application 4 262, API 1 383, intégration 1 314 (16 sautés, préexistants).
- client-mobile : build vert ; Karma 1 467 / 1 467 au 1ᵉʳ passage ; 2ᵉ passage 4 rouges **sans rapport**
  (`HtmlEditorComponent` sélection ×3, `MailboxSwitcherComponent` fermeture de feuille), `src/` identique au 1ᵉʳ ;
  3ᵉ passage 1 467 / 1 467 — instables, non liés à la task.
- client-angular : `nx build weda2` vert, `nx test mss-lib` 150 fichiers / 1 689 tests. Seule la spec e2e
  (`functional.e2e.ts`, hors de cette suite, type-checkée) a bougé depuis.

### Amélioration continue (règle d'or)
- `conventions/csharp.md` : nouvelle entrée **borne-de-saisie-egale-a-la-colonne** (une borne de saisie et la
  longueur de sa colonne lisent la même constante ; preuve au plafond exact et au-delà).
- `conventions/csharp.md` : nouvelle entrée **base-neuve-de-test-sans-pool** (Occurrences 2 : task-331 puis
  task-486 — le piège a été reproduit en copiant un test de migration existant qui garde son pool).
- Mémoire de session : 5ᵉ récidive du `53300`, avec sa cause.

### DOD self-check
- [x] Validation du nom (espaces, nettoyage, 40, contrôle, `detail` français) + tests unitaires de normalisation —
  `TagNameRuleTests`, `MailControllerTests`.
- [x] Route de liste `GET api/v1/Mail/tags` ; `TagDto` inchangé (pas de publication) ; miroirs TS : `getMailboxTags`
  (weda2, mobile), `TagDto` TS déjà complets.
- [x] Intégration de bout en bout règle 1b, vue rouge (refus des espaces réinjecté → rouge) — `…TagEntry.cs`.
- [x] Tests de composant weda2 et mobile, vus rouges par mutation (liste ouverte, filtre, exclus, Entrée, Créer).
- [x] E2E-TAG-001 v1, mobile et angular, vu rouge par mutation sur les deux voies.
- [x] `data-testid` sur la liste et ses lignes ; libellés FR ; aucune donnée de santé dans libellés ni journaux
  (le contrôleur ne journalise pas le nom du tag).
- [x] Build et tests verts (api-mail, weda2, mobile) ; client-angular code-only, non commité.
- Manuel (HAG) : plan de test 1-6 sur la boîte de formation.
- Green marked : api-mail `0956bcad`, client-mobile `2690b9c`, client-angular (arbre courant) — `Tools/green/green.py`.
- Next step : /review task-486 --code

### Reprise 1 après /review

Périmètre : « À corriger par la reprise » du passage 1 (B1, B2, B3, B4, S1). Arbitrages A1 et A2 non touchés.

| Constat | Correctif | Test | Preuve rouge |
|---|---|---|---|
| **B1** refus contrôle / vide et accents prouvés en unitaire seulement | aucun code : preuves ajoutées | `ARefusedName_Is400ProblemJson_WithItsFrenchDetail_AndNothingIsCreated` (tab, saut de ligne, espaces, vide) ; `ANameThatDiffersOnlyByItsAccents_DesignatesTheSameTag` | mutations : contrôle neutralisé → 200 au lieu de 400 (2 cas) ; message vide remis en anglais → `detail` « Tag name is required. » (2 cas) ; accents conservés → code `TRÈS URGENT T486` |
| **B4** création / pose concurrente → erreur | `AddTagToMailAsync` : `CreateTagOrReadWinnerAsync` (déjà là pour IA et catégorie) et `PoseMailTagOrKeepWinnerAsync` (nouveau, sur `IX_MailTags_MailId_TagId`) | `MailRepositoryUserTagRaceTests` (gagnant inséré hors bande juste avant l'`INSERT`, intercepteur extrait du test AUD-36 vers `Fixtures/BeforeCommandInterceptor.cs`) ; `ConcurrentPosesOfTheSameNewTag_AllSucceed_OnASingleTag` (8 POST concurrents par la route) | **rouges avant correctif** : 23505 `IX_Tags_Code`, 23505 `IX_MailTags_MailId_TagId`, 500 par la route |
| **B2** Entrée / ✓ posait un autre tag que le nom exact | `tagChoices` : tri stable, la correspondance exacte en tête (weda2 et mobile) | util et composant, « imp » avec « Important » (IA) et « Imp » → `Imp` | mutation tri neutralisé : 2 rouges weda2, 2 rouges mobile |
| **B3** weda2 : refus jamais affiché, puce en double, double envoi | `MailTagComponent.post` : `detail` du ProblemDetails sous le champ (`mail-tag-error`, effacé à la frappe), rien envoyé pour un tag déjà posé (saisie fermée), second envoi ignoré pendant la pose (✓ désactivé) | 3 tests de composant | 3 mutations, chacune rouge sur son test |
| **S1** flèche haut depuis « aucune ligne » | départ à 0 quand l'index vaut −1 (weda2 et mobile) | un test par client | mutation : rouge dans chaque client |

- Relecture du correctif comme correctif : `AddTagToMailAsync` n'a qu'un appelant (`ImapService`) ; `CreateTagOrReadWinnerAsync`
  inchangé (ses tests AUD-36 rejoués verts avec l'intercepteur déplacé) ; le tri de `tagChoices` ne change l'ordre
  que pour la correspondance exacte ; `post` (weda2) reste le seul chemin d'envoi (Entrée, ✓, clic). Rien d'autre
  touché.
- Suites complètes sur l'état poussé : api-mail domaine 302, infra 750, application 4 262, API 1 383, intégration
  1 322 (16 sautés préexistants) ; weda2 `nx build weda2` vert, `nx test mss-lib` 150 fichiers / 1 695 tests ;
  mobile build vert, Karma 1 470 / 1 470 au second passage. Le premier passage mobile avait 4 rouges
  `MailComposeComponent` (suggestions de destinataires, task-388), aussi rouges en lancement isolé du dossier
  `mail-compose` ; aucun fichier de la task dans ce périmètre ; non tranché sur `origin/develop` (un worktree ne
  résout pas les ressources des `node_modules` partagés). Instables, hors task.
- Lint / format : ESLint 0 erreur (weda2, mobile), Prettier propre, fins de ligne CRLF homogènes.
- Commits : api-mail `4c28314b` ; client-mobile `a1fe177` ; client-angular non commité (mêmes fichiers que la passe 0).
- Prévention (règle d'or) : `conventions/csharp.md` — `unicite-garantie-par-la-base` Occurrences 2 (écrivain de
  `Tags` oublié), `borne-de-saisie-egale-a-la-colonne` (chaque refus a son cas d'intégration) ;
  `conventions/angular.md` — `suggestions-de-saisie-choisies-visibles` Occurrences 4 (nom exact en tête, flèche
  haut, refus affiché et double envoi).
- Green marked : api-mail `4c28314b`, client-mobile `a1fe177`, client-angular (arbre courant).
- Next step : /review task-486 --code

### Reprise 2 après /review

Autorisée par l'humain le 2026-11-16 (B2 revenu au passage 2, règle 13). Périmètre : « À corriger par la reprise » du
passage 2.

| Constat | Correctif | Test | Preuve rouge |
|---|---|---|---|
| **B2 (reste)** nom exact d'un tag **déjà posé** : la première ligne restante (un autre tag) était désignée | `namesAppliedTag` (util weda2 et mobile) : aucune ligne désignée d'office quand le texte désigne un tag déjà posé ; Entrée / ✓ referment sans rien poser (garde « déjà posé » existante) | « le nom exact d'un tag déjà posé ne désigne aucun autre tag » (weda2, mobile) : posé « Urgent », boîte avec « Très urgent » et « Courrier urgent », « urgent » + Entrée → aucun POST | **rouge avant correctif** dans les deux clients ; mutation (condition retirée) rouge dans chacun |
| **S2** weda2 : refus réapparu à la réouverture | `startAdding` remet l'erreur à zéro | « un refus reçu après la fermeture ne réapparaît pas » | rouge avant correctif ; mutation rouge |
| **S3** test HTTP de concurrence | commentaire : il ne force pas la course, la preuve rouge est `MailRepositoryUserTagRaceTests` | — | — |

- Relecture du correctif comme correctif : `onQueryChange` / `onTagNameInput` n'ont pas d'autre appelant ; la flèche bas
  depuis « aucune ligne » désigne toujours la première (choix délibéré possible) ; ✓ suit le même chemin qu'Entrée.
- Suites complètes sur l'état poussé, vertes au premier passage : api-mail (302 / 750 / 4 262 / 1 383 / intégration 1 322),
  mobile build + Karma 1 471 / 1 471, weda2 build + `mss-lib` 150 fichiers / 1 697 tests. ESLint 0 erreur, Prettier
  propre, CRLF homogènes.
- Commits : api-mail `444aeb06` ; client-mobile `e58fc40` ; client-angular non commité.
- Prévention : `conventions/angular.md`, `suggestions-de-saisie-choisies-visibles` Occurrences 5 (élément exclu de la
  liste : aucune désignation d'office ; le test met un élément qui contient le texte).
- Green marked : api-mail `444aeb06`, client-mobile `e58fc40`, client-angular (arbre courant).
- Next step : /review task-486 --code

## Code Review Summary

### Passage 1 (revue anticipée) — CHANGES REQUESTED

Revue du diff `origin/develop...HEAD` d'api-mail (`0956bcad`) et de client-mobile (`2690b9c`), et de l'arbre de
travail de client-angular (`feature/nova-mss-weda-integration`), par un relecteur indépendant (le code, sans le
`## Develop log`), croisée avec la table 4a.

- **4b (clause DOD)** : `E2E-TAG-001` v1 au catalogue, déclaré v1 par les deux suites (mobile `functional.spec.ts`,
  weda2 `functional.e2e.ts`). Le `## E2E log` sera vérifié en validation finale.
- **4c** : api-mcp : aucun impact (`mcp_impact.py check` → 0).
- **4a — comportement → test d'intégration → preuve rouge** :
  | Comportement (endpoint) | Test d'intégration | Preuve rouge |
  |---|---|---|
  | POST tags : plusieurs mots acceptés, nom nettoyé | `ATagOfSeveralWords_IsSet_ReadOnTheMessage_AndListedOnceForTheMailbox` | refus des espaces réinjecté |
  | même tag pour espaces / casse | idem (même `Id`, une ligne) | nom brut + code non nettoyé |
  | 40 caractères après nettoyage ; 41 → 400 ProblemDetails FR | `ANameOfFortyOneCharacters_IsRefusedWith400ProblemJson_InFrench_AndNothingIsCreated` | plafond neutralisé ; migration vide |
  | GET tags : contenu, ordre système → IA → utilisateur → alpha | `TheMailboxTags_AreListedSystemFirst_ThenAi_ThenUser_ThenAlphabetically` | tri remplacé |
  | colonnes élargies à 40 | `WidenTagNamesMigrationTests` | migration vide |
  | caractère de contrôle refusé, nom vide refusé (detail désormais en français), accents | **aucun** (unitaires seulement) | — |

- Conformes (relecteur) : règle et contrôleur (`ValidationException` → 400 ProblemDetails), autres appelants de
  `NormalizeTagCode` (IA, CATEGORY) sans régression, migration limitée aux deux colonnes, tests d'intégration sur la
  vraie pile, e2e relus du serveur et rejouables, aucune injection ni XSS, aucun nom de tag dans les journaux.

#### À corriger par la reprise
- **B1 (règle 1b, bloquant)** — le refus d'un **caractère de contrôle**, le refus d'un **nom vide** (dont le `detail`
  est passé de l'anglais au français) et l'**équivalence des accents** (« Très urgent » / « tres URGENT » → même tag)
  ne sont prouvés qu'en unitaire. Ajouter les cas d'intégration (400 `problem+json`, `detail` FR lu, rien créé ; même
  `Id` pour la variante accentuée), vus rouges.
- **B2 (bloquant)** — Entrée / ✓ peut poser un autre tag que le nom **exact** tapé : les lignes « commence par »
  gardent l'ordre du serveur, la correspondance exacte n'est pas en tête. Boîte avec « Important » (IA) et « Imp »
  (utilisateur), saisie « imp » + Entrée → « Important » posé. Mettre la correspondance exacte en première ligne
  (weda2 et mobile, `tag-suggestions.util.ts`), test vu rouge dans les deux clients.
- **B3 (bloquant)** — weda2 : `MailTagComponent.post()` n'a pas de gestion d'erreur ; un refus du serveur (400,
  `detail` français) n'est jamais montré, la saisie reste ouverte sans message. Afficher le `detail` sous le champ.
  Même composant : taper le nom exact d'un tag **déjà posé** donne une liste vide, Entrée envoie quand même le POST et
  la puce apparaît en double (`onTagAdded`). Ne rien envoyer (ou fermer) quand le tag est déjà posé, comme le mobile.
- **B4 (bloquant)** — `MailRepository.AddTagToMailAsync` crée le tag utilisateur sans la reprise sur conflit de
  `IX_Tags_Code` que les voies IA et CATEGORY ont déjà (`CreateTagOrReadWinnerAsync`) : deux créations simultanées du
  même nom (double clic, deux personnes de la boîte, règle 14) → la seconde échoue en erreur générique anglaise.
  Réutiliser la reprise, preuve par deux poses concurrentes du même nouveau nom (deux contextes) : 200 et un seul tag.
  Côté weda2, bloquer un second envoi pendant la requête.
- **S1 (même passe)** — flèche haut depuis « aucune ligne désignée » (index −1) désigne l'avant-dernière ligne au
  lieu de la dernière (`(−1 − 1 + n) % n`), weda2 et mobile ; test de la flèche haut.

#### Arbitrage humain
- **A1** — « Avis cardio » tapé quand « Avis cardiologie » existe : Entrée (et ✓ sur mobile) pose « Avis cardiologie »,
  la ligne « Créer le tag » est la dernière. C'est le comportement du plan de test (« Entrée pose le premier »).
  *Recommandation de la forge* : garder ; créer le nom exact se fait en touchant (ou désignant) la ligne « Créer ».
- **A2** — les clients posent un tag existant **par son nom**, ce qui suppose `Code == TagNameRule.Code(Name)`. Vrai
  pour tous les producteurs actuels. Si task-456 sème des tags système au code non dérivé du nom (`PRO_SANTE`),
  choisir ce tag créerait un homonyme utilisateur. *Recommandation* : task-456 dérive ses codes du nom par la règle
  (un test le fige), plutôt qu'une pose par code ajoutée ici.

### Passage 2 (revue anticipée, après reprise 1) — CHANGES REQUESTED, chaîne arrêtée

Relecture indépendante du diff de la reprise d'abord (api-mail `0956bcad..4c28314b`, client-mobile
`2690b9c..a1fe177`, fichiers weda2 de la saisie), puis des constats du passage 1. api-mcp : aucun impact.

- **Rien de cassé par la reprise** : `AddTagToMailAsync` n'a qu'un appelant ; `CreateTagOrReadWinnerAsync` inchangé
  (voies IA et catégorie intactes) ; l'intercepteur déplacé reste utilisé par le test AUD-36 ; les tests de course
  nettoient la base partagée ; `sending` est remis à zéro au succès comme à l'échec ; Échap et ✕ passent par
  `cancelAdding`.
- **B1 corrigé** (refus et accents prouvés par la route, rouges par mutation). **B4 corrigé** (reprise sur
  `IX_Tags_Code` et `IX_MailTags_MailId_TagId`, course forcée). **S1 corrigé** (deux clients). **B3 corrigé dans son
  périmètre** (refus affiché, double envoi bloqué ; la garde « déjà posé » ne joue que si la liste est vide, voir B2).
- **B2 partiellement corrigé — revient** : le nom exact passe bien en tête, sauf quand il désigne un tag **déjà
  posé** sur le message. Ce tag est exclu de la liste, `exists` (qui compte les tags posés) retire la ligne
  « Créer », et la ligne 0 — un autre tag — est désignée d'office. Message portant « Urgent », saisie « urgent » +
  Entrée (ou ✓ sur mobile) → **« Très urgent » posé**. Le test « nom exact d'un tag déjà posé » utilise « Avis
  cardio », que nul autre tag ne contient : il ne voit pas le cas. Fichiers : `tag-suggestions.util.ts` (weda2 :80,
  mobile :64), `mail-tag.component.ts:104`, `mail-detail.component.ts:867`.

#### À corriger par la reprise
- **B2 (reste)** — quand le texte saisi désigne exactement un tag déjà posé, ne désigner aucune ligne (index −1) :
  Entrée et ✓ referment la saisie sans rien envoyer. Test vu rouge dans les deux clients : message portant
  « Urgent », boîte avec « Très urgent » et « Courrier urgent », « urgent » + Entrée → aucun POST.
- **S2 (suggestion)** — weda2 : `startAdding` ne remet pas `error` à zéro ; un refus arrivé après une fermeture
  réapparaît à la réouverture. `error.set(null)` à l'ouverture.
- **S3 (suggestion)** — `ConcurrentPosesOfTheSameNewTag_AllSucceed_OnASingleTag` ne force pas la course (il peut
  rester vert sans la reprise ; il a été rouge ici, mais par chance d'ordonnancement) : dire dans son commentaire que
  la preuve rouge est `MailRepositoryUserTagRaceTests`.

#### Arbitrage humain
- **A1, A2** : inchangés (passage 1).
- **A3 (nouveau, issu de la règle 13)** — B2 est un bloquant **revenu** après la reprise 1. La règle 13 arrête la
  chaîne dans ce cas. Le correctif est connu, local et testable (ci-dessus) ; une reprise 2 reste dans le plafond.
  *Recommandation de la forge* : autoriser la reprise 2 (`/develop task-486 --reprise`).

## Timings

*(généré par `tools/timing/report.sh --task task-486 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 32 s | — | — | — | — |
| /develop | ok | 10 min 36 s | 16 (2 min 41 s) | 14 (33 min 56 s) | — | api-mail 9B/5T, client-mobile 4B/6T, client-angular 3B/3T, reprise 2 |
| /review-code | failed | 5 min 21 s | — | — | — | B2 revenu apres reprise 1 (regle 13) |
| **Total cycle** | | **16 min 30 s** | **16 (2 min 41 s)** | **14 (33 min 56 s)** | **0 (0.0 s)** | |
