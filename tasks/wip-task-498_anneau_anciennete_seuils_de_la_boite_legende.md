# todo-task-498.md — Anneau : ancienneté, seuils de la boîte, préférences et légende

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
**Dependencies**: task-497
**Epic**: E027
**Reprises**: 1

> **Origine.** Demande humaine du 2026-11-27 (« le médecin voit ce qui n'est pas bouclé et ce qui traîne »), phase de
> conception validée le même jour : `Docs/specs/anneau-de-traitement/` (spécification § 6 et § 10, maquettes
> variante D, section 5). Décisions acceptées : ancienneté en **compteur J+N** plutôt qu'en cernes (14), seuils par
> catégorie réglés **au niveau de la boîte** (5, 8), **heures** pour une valeur critique (16), date de référence =
> ouverture de la boucle, jours calendaires (13), un réglage d'affichage par élément (17).

## Objectif

Une boucle ouverte montre **depuis combien de temps** elle l'est. Passé un premier seuil, la ligne affiche « J+N » ;
au dernier seuil, la boucle est **en retard** et le compteur passe en fond plein. Les seuils sont ceux de la boîte.
Chaque personne règle ce qu'elle veut voir, et une **légende** dessinée par le composant réel explique chaque signe.

### Ce qui est établi

Lecture du code au 2026-11-27 :

- **Aucune notion d'ancienneté, de retard ou d'échéance** n'existe dans `api-mail` ni dans les clients.
- **La date d'arrivée réelle** est sur la ligne : `MailDto.ArrivalDate` (task-466).
- **« Remettre à traiter »** date son geste : `MailHandlingStates.At`, rendu par `MailDto.Handling.At`.
- **Réglage de boîte, modèle à suivre** : la date de début du suivi (`MailboxTrackingStart`,
  `GET|PUT api/v1/account/mailboxes/current/tracking-start`, acte `MailboxTrackingStartChanged` tracé avec l'ancienne
  et la nouvelle valeur ; toute personne rattachée à la boîte peut la changer).
- **Réglages de la personne** : `UserSettingsDto`, sauvegardé en entier par les deux clients.
- **Écrans de réglages** : weda2 `libs/mss/src/features/settings/mss-settings.component.html` (sections « Lecture »
  avec cartes illustrées, « Boîte aux lettres » avec la date de suivi) ; mobile `src/app/settings/settings.page.html`
  (section « Suivi »). Aucune légende n'existe.
- **L'anneau et ses pastilles** sont posés par task-497.

### Règles

1. **Date de référence** d'une boucle ouverte : sa date d'arrivée réelle ; si le message a été remis à traiter, la
   date de ce geste.
2. **Catégorie** d'une boucle, pour ses seuils :
   - **biologie critique** : un compte rendu à valeur critique est à acquitter ;
   - **biologie** : un compte rendu avec anomalie est à acquitter ;
   - **courrier** : tout le reste.
3. **Seuils par défaut**, trois par catégorie, strictement croissants :

   | Catégorie | 1er seuil | 2e seuil | En retard |
   |---|---|---|---|
   | Biologie critique | 4 h | 24 h | 72 h |
   | Biologie | 1 j | 3 j | 7 j |
   | Courrier | 3 j | 7 j | 14 j |

4. **Les seuils appartiennent à la boîte.** Toute personne rattachée et active peut les changer, comme la date de
   début du suivi. Valeurs entières, strictement croissantes dans une catégorie, de 1 à 720 heures et de 1 à 365
   jours ; un refus est expliqué en français sous le champ. Chaque changement est **tracé** au nom de son auteur réel,
   avec les anciennes et les nouvelles valeurs.
5. **Compteur.** À partir du 1er seuil, la ligne affiche « J+N », N étant le nombre de jours entiers écoulés. Pour la
   biologie critique : « H+N » en heures jusqu'à 72 heures, « J+N » au-delà. Au dernier seuil, le compteur passe en
   **fond plein** et le libellé de l'anneau ajoute « en retard ». Avant le 1er seuil, rien ne s'affiche.
6. **Calcul à l'affichage.** L'ancienneté se calcule sur le poste, à partir de la date de référence et des seuils lus
   une fois avec les réglages. **Aucune écriture périodique en base**, aucun champ d'ancienneté stocké.
7. Un anneau fermé ou hors suivi n'affiche jamais d'ancienneté.
8. **Détail** : le bloc de l'anneau dit « Ouvert depuis N jours », et « en retard » au dernier seuil.
9. **Préférences de la personne**, toutes actives par défaut : affectation (initiales, « Non affecté »), attente
   d'un tiers, gravité, ancienneté, animations. Plus « Contraste renforcé », inactif par défaut (traits plus épais et
   plus sombres ; le contraste par défaut est déjà conforme). La couleur de gravité masquée laisse le badge
   d'acquittement ⚠ existant : une anomalie à acquitter reste toujours visible.
10. **Légende.** Une page « Légende des anneaux » dessine chaque état avec le **composant réel** : étapes, boucle
    fermée, hors suivi, initiales (collègue, soi, accès retiré), « Non affecté », attente d'un tiers, gravité,
    compteur. Elle cite les **seuils en vigueur** de la boîte et suit les préférences de la personne. Elle dit que les
    messages « Pour info », les accusés et les messages antérieurs au suivi n'ouvrent pas de boucle.
    - weda2 : section « Anneau de traitement » des Paramètres, après « Lecture » ; les seuils dans « Boîte aux
      lettres », à côté de la date de suivi.
    - Mobile : entrée « Anneau de traitement » des Paramètres, qui ouvre une page ; les seuils dans « Suivi ».

### Hors périmètre

- Les compteurs « en retard » du tableau de bord et le filtre de liste « En retard » : task-499.
- Les messages envoyés et leur seuil : non retenus (décision 9).
- Des règles par personne pour classer un message « sans action attendue » : non retenues (décision 1).

## Definition of Done

- [ ] Build passes : api-mail, dtos-mss, `nx build weda2`, client-mobile (0 erreur).
- [ ] Tests pass : api-mail, `nx test mss-lib`, `nx test weda2`, client-mobile (0 échec).
- [ ] Tests unitaires (api-mail) de la validation des seuils : valeurs par défaut sans ligne en base ; non croissants,
      nuls, négatifs, au-delà des bornes (refusés, message en français) ; chacun vu rouge.
- [ ] Test d'intégration de bout en bout pour la lecture et l'écriture des seuils de la boîte : sans réglage, la
      lecture rend les valeurs par défaut de la règle 3 ; après écriture, la lecture rend les nouvelles valeurs,
      relues dans la réponse réelle et en base. Cas d'échec : seuils non croissants → 400 en `problem+json`, rien
      d'écrit. Vu rouge (règle 1b).
- [ ] Test d'intégration en boîte partagée (règle 14) : le délégataire change un seuil ; le titulaire relit les
      seuils et obtient la nouvelle valeur ; la trace porte le délégataire en auteur, son rôle, l'ancienne et la
      nouvelle valeur. Vu rouge.
- [ ] Test d'intégration : les réglages d'affichage de la personne sont rendus et retenus, et ne sont **pas** partagés
      avec une autre personne de la même boîte. Vu rouge.
- [ ] Migration des seuils en ajout seul : aucune donnée existante modifiée ni supprimée ; descente qui retire ce
      qu'elle a ajouté ; relue (règle 7c).
- [ ] dtos-mss : contrats ajoutés publiés, api-mail bumpé ; `python Tools/contracts/contract_impact.py check` sans
      impact non adapté.
- [ ] Tests unitaires du calcul d'ancienneté, weda2 et mobile, à horloge fixée, vus rouges : avant le 1er seuil
      (rien) ; au 1er, au 2e, au dernier seuil ; biologie critique en heures puis en jours au-delà de 72 h ; message
      remis à traiter (la date du geste commande) ; anneau fermé ou hors suivi (rien) ; seuils modifiés pris en compte.
- [ ] Tests de composant, weda2 et mobile, vus rouges : « J+N » et « H+N » sur la ligne, fond plein et « en retard »
      dans le libellé au dernier seuil ; chaque préférence masque son élément et lui seul ; la gravité masquée laisse
      le badge ⚠ ; contraste renforcé ; la légende reprend les seuils de la boîte et les préférences.
- [ ] Aucune écriture périodique : aucun job, aucune colonne d'ancienneté (relu en revue).
- [ ] `data-testid` sur le compteur, chaque champ de seuil, chaque préférence et chaque entrée de légende ; aucun
      texte en dur hors de la convention de chaque client.
- [ ] Mobile : références Stitch des écrans `settings` et de la page de légende créées ou mises à jour
      (`/stitch-design`, best-effort).
- [ ] Scénario **E2E-RING-004** (version 1, `mobile: requis`, `angular: requis`) ajouté à
      `Api/Mail/e2e/scenarios.yml` et implémenté dans les deux clients : le test dépose un courrier à traiter arrivé
      il y a 8 jours et un autre arrivé aujourd'hui. Avec les seuils par défaut, le premier porte « J+8 », le second
      rien. Le praticien règle les seuils du courrier à 2, 5 et 8 jours : relus du serveur, ils sont enregistrés, et
      la ligne porte « J+8 » en fond plein avec « en retard » dans son libellé.
- [ ] Scénario **E2E-SETTINGS-006** (version 1, `mobile: requis`, `angular: requis`) : le praticien ouvre la légende ;
      elle montre les états et cite les seuils de la boîte. Il désactive « Ancienneté » : le compteur disparaît de la
      liste ; après rechargement, le choix est retenu ; il le réactive.
- [ ] Aucune donnée de santé dans les journaux ni dans la trace du changement de seuils (elle ne porte que des
      nombres).

## Manual Test Plan

- Backend : `cd Api/Mail && dotnet run --project src/AppHost` (profil de développement habituel).
- weda2 : `cd Client/Angular/front && npm run start:weda2`. Mobile : `cd Client/Mobile && npm start`.
- Données : une boîte partagée avec un délégataire ; un courrier à traiter arrivé il y a plus de 14 jours, un autre
  il y a 4 jours, un autre aujourd'hui ; un compte rendu de biologie à valeur critique arrivé il y a quelques heures.
- Référence visuelle : `Docs/specs/anneau-de-traitement/maquettes.html`, variante D, sections 2 et 5.

1. weda2, Boîte de réception : le courrier de 4 jours porte « J+4 » ; celui de plus de 14 jours porte son compteur en
   fond plein, et son libellé au survol dit « en retard » ; celui du jour ne porte rien. La biologie critique porte
   « H+N ».
2. Marquer « Traité » le courrier en retard : le compteur disparaît. « Remettre à traiter » : le compteur repart de
   zéro.
3. Paramètres, « Boîte aux lettres » : passer le 1er seuil du courrier à 5 jours ; « J+4 » disparaît de la liste.
   Saisir des seuils non croissants : refus expliqué sous le champ.
4. Se connecter en délégataire : les seuils sont ceux que le titulaire a réglés. Journal d'audit : le changement est
   au nom du titulaire, avec l'ancienne et la nouvelle valeur.
5. Paramètres, « Anneau de traitement » : la légende dessine chaque état et cite les seuils de la boîte. Désactiver
   « Ancienneté » : plus de compteur dans la liste, la légende le reflète. Le délégataire, lui, le voit toujours.
6. Activer « Contraste renforcé » : traits plus épais et plus sombres.
7. Refaire 1 à 6 sur le mobile.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du cabinet).
- **Vague Ségur** : hors Ségur — aide à l'organisation du cabinet, aucune exigence DSR nouvelle.
- **Exigences DSR honorées** : non applicable.
- **INS** : non applicable — aucun patient identifié ni manipulé.
- **Authentification PS** : inchangée — session PSC (e-CPS) de la messagerie.
- **Habilitations** : toute personne rattachée à la boîte et active (titulaire, membre, délégataire) lit et change les
  seuils, comme la date de début du suivi ; sans verdict récent de l'opérateur, ni lecture ni écriture (règle 14).
- **Interop CI-SIS** : non applicable. La catégorie « biologie critique » reprend le code d'interprétation posé par le
  laboratoire.
- **Tracé PGSSI-S** : un acte nouveau, **changement des seuils d'ancienneté de la boîte**, tracé au nom de la personne
  réelle (RPPS, nom PSC, rôle, boîte, instant, anciennes et nouvelles valeurs), conservé comme le changement de la
  date de suivi. Les réglages d'affichage de la personne ne sont pas tracés.
- **Consentement patient** : non applicable.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : oui — les seuils sont une donnée de la boîte, dans sa base, environnement HDS existant ; les
  réglages d'affichage sont une donnée de la personne. Aucune donnée de santé nouvelle.
- **AIPD / impact RGPD** : inchangée — un réglage d'organisation, aucune donnée de santé ni décision automatisée.

## Timings

*(généré par `tools/timing/report.sh --task task-498 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 31 s | — | — | — | — |
| /develop | ok | 20 min 31 s | 13 (1 min 55 s) | 59 (26 min 48 s) | — | dtos-mss 1B/0T, api-mail 7B/56T, client-mobile 3B/3T, client-angular 2B/0T, reprise 1 |
| /review-code | ok | 4 min 15 s | — | — | — | passage 2 |
| /sonar | ok | 11 min 52 s | 1 (49 s) | 5 (8 min 19 s) | 2 (47 s) | 1 itération(s), api-mail 1B/5T |
| /lint-angular | ok | 26 s | — | — | — | — |
| /lint-mobile | ok | 16 s | — | — | — | — |
| /e2e | failed | 32 min 12 s | — | — | — | e2e ×3 (30 min 00 s), RING-004 mobile rouge : dates serveur sans Z lues en heure locale |
| **Total cycle** | | **1 h 10 min** | **14 (2 min 45 s)** | **64 (35 min 07 s)** | **2 (47 s)** | |

Autres commandes mesurées : lint ×2 (17 s), nuget-wait ×1 (11 s), restore ×1 (3.6 s)

## Branches

- `api-mail` (pushed) : feat/task-498-anneau-anciennete-seuils-de-la-boite — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-498-anneau-anciennete-seuils-de-la-boite
- `client-mobile` (pushed) : feat/task-498-anneau-anciennete-seuils-de-la-boite — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-498-anneau-anciennete-seuils-de-la-boite
- `dtos-mss` (pushed, paresseuse) : aucune branche au /start — `/develop` la crée depuis `origin/develop` s'il touche un contrat
- `client-angular` (code-only) : la forge écrit sur la branche extraite dans `Client/Angular/` (au /start :
  `feature/nova-mss-weda-integration`, arbre propre, après `3f6e9119` « Anneau ajustement ») — l'humain gère branche,
  commit, push, PR TFS

## Develop log

Contrat commun fixé par l'orchestrateur avant le code (DTOs, route `aging-thresholds`, erreurs, calcul de
l'ancienneté, catalogue, option `--arrived-days-ago`, précondition de RING-004 sur la date de suivi), puis trois agents
en parallèle. Validation complète jouée ensuite par l'orchestrateur, une suite à la fois :

- **api-mail** `61aadb25` (poussé) : build 0 erreur ; domain 388, infrastructure 749, application 4 396, api 1 396,
  intégration 1 396 (+16 ignorés), tous verts. Un rouge à la première suite complète :
  `ErrorCatalogDocumentTests` — document `docs/codes-erreur.md` non régénéré après l'ajout de
  `MAILBOX_AGING_THRESHOLDS_INVALID` ; régénéré (`61aadb25`), prévention `conventions/csharp.md`
  `catalogue-erreur-document-regenere`.
- **dtos-mss** `158d4e46` (poussé) : `HealthPlatform.Dtos.Mss` 641.0.0 publié par la CI, api-mail bumpé (`82340632`).
- **client-mobile** `c968cf7` (poussé) : build OK, suite complète 2 081 verts (avant et après la passe §Q).
- **client-angular** (arbre, non commité) : `nx build weda2` OK, mss-lib 2 312 verts, weda2 2 683 verts.
- `contract_impact.py check` : IMPACT client-angular (`AuditActionType` décodé par rang, valeur 77) → adapté dans
  `audit.model.ts` + spec (vu rouge) ; api-mcp et client-mobile : aucun impact.
- e2e E2E-RING-004 et E2E-SETTINGS-006 : écrits dans les deux clients, **non joués** ici (joués par `/e2e`).

### api-mail + dtos-mss

### task-498 — Develop log, agent api-mail + dtos-mss

État : **fini** (api-mail commité en local, **non poussé**, comme demandé).

#### dtos-mss (`Dtos/`)

- Branche paresseuse `feat/task-498-anneau-anciennete-seuils-de-la-boite`, créée depuis `origin/develop`, poussée.
- Commit `158d4e46` — `feat(dto): seuils d'ancienneté de la boîte, préférences d'affichage de l'anneau (task-498)`.
  - `MailboxDto.cs` : `AgingThresholdsDto`, `MailboxAgingThresholdsDto` (défauts 4/24/72 h, 1/3/7 j, 3/7/14 j), `MailboxErrorCodes.AgingThresholdsInvalid = "MAILBOX_AGING_THRESHOLDS_INVALID"`.
  - `UserSettingsDto.cs` : `RingDisplayPreferencesDto` (tout à `true` sauf `HighContrast`), `UserSettingsDto.RingDisplay = new()`.
  - `AuditActionType.cs` : `MailboxAgingThresholdsChanged = 77`, en fin d'énumération.
- CI run 46075247408 vert (attente mesurée, `--kind nuget-wait`) → **NuGet `HealthPlatform.Dtos.Mss` 641.0.0**.
- Pas de passe qualité (porteur de contrat, §Q niveau 3).

#### api-mail (`Api/Mail`, branche `feat/task-498-anneau-anciennete-seuils-de-la-boite`)

Commits locaux :

| SHA | Message |
|---|---|
| `82340632` | chore(deps): bump HealthPlatform.Dtos.Mss to 641.0.0 (`Directory.Packages.props` et 13 `packages.lock.json`) |
| `c61a727a` | test(e2e): message --create --arrived-days-ago N, scénarios E2E-RING-004 et E2E-SETTINGS-006 |
| `b568314c` | feat(mailbox): seuils d'ancienneté de la boîte et préférences d'affichage de l'anneau |

Fichiers :

- Route : `src/Api/Controllers/V1/MailboxAgingThresholdsController.cs`. Modèle de `MailboxTrackingStartController` : pas `[MailboxNotRequired]`, donc boîte sélectionnée et verdict de l'opérateur par le middleware. GET `[TraceExempt]`, PUT `[TracedInCode(MailboxAgingThresholdsChanged)]`.
- Service : `src/Application/Services/Mailboxes/MailboxAgingThresholdsService.cs` (+ interface). Il trace dans le code, au nom de l'auteur réel, les anciennes valeurs en vigueur (les défauts s'il n'y a pas de ligne) et les nouvelles. La trace ne porte que des nombres.
- Règle : `src/Application/Services/Mailboxes/MailboxAgingThresholdsRule.cs`.
  - Bornes, puis ordre, catégorie par catégorie, dans l'ordre de l'écran.
  - Une catégorie à `null` est refusée (« Les seuils … sont requis. »). Un corps absent lève une `ValidationException`.
- Exception : `src/Application/Exceptions/MailboxAgingThresholdsInvalidException.cs` (`ValidationException`, `IErrorCoded`, `IFieldScopedError`).
- `src/Application/Exceptions/IFieldScopedError.cs` (nouveau). `GlobalExceptionHandler` pose l'extension `field` pour toute erreur qui implémente l'interface, et `IheXdmPackagingRefusedException` l'implémente : c'est le même mécanisme que task-367, généralisé.
- Stockage : entité `src/Domain/Entities/MailDb/MailboxAgingThresholds.cs` (une ligne, 9 entiers), dépôt `src/Infrastructure/Repositories/MailDb/MailboxAgingThresholdsRepository.cs` et `IMailboxAgingThresholdsRepository`, mapping dans `MailDataContext`, DI (Api et Infrastructure) et fixture `UseCaseHttpHost`.
- Migration `src/Infrastructure/Migrations/MailDb/20261127120000_AddMailboxAgingThresholds.cs`. **FluentMigrator, pas EF Core** : il n'y a donc ni `.Designer.cs` ni snapshot, contrairement à ce que supposait le brief.
  - Montée : ajout seul, `Create.Table`, aucune ligne posée, aucune donnée existante touchée.
  - Descente : `Delete.Table`. Relue (règle 7c).
- Réglages de la personne : `UserSettings` est stocké en **JSON**, une ligne par personne et `UserId` dans la base de la boîte. Aucune migration n'est donc nécessaire.
  - `RingDisplay` est rendu et retenu dès le bump.
  - `UserSettingsRepository` normalise `RingDisplay ??= new()`, pour une ligne enregistrée avec `"ringDisplay": null`. Une ligne d'avant la task tient déjà par l'initialiseur du contrat.
- `ErrorCatalog` : entrée `MAILBOX_AGING_THRESHOLDS_INVALID`.
- Tests de contrat : `AuditActionTypeContractTests` (77, total 79), `AuditRetentionPolicyTests` (famille HealthDataAccess, par défaut).
- Outil e2e (`tests/mss.mail.e2e`) :
  - `E2eMessageShape.ArrivedDaysAgo`, `E2eMessage.AppendAsync` (APPEND avec `INTERNALDATE` = maintenant − N et en-tête `Date:` aligné), `E2eMessage.ParseArrivedDaysAgo` (un entier ≥ 0, sinon `ArgumentException`, jamais de repli silencieux) ;
  - `Program.cs` lit `--arrived-days-ago` et l'ajoute à la ligne d'usage.
- Catalogue `e2e/scenarios.yml` : `E2E-RING-004` v1 et `E2E-SETTINGS-006` v1, `mobile: requis`, `angular: requis`, `origine: task-498`.
- Tests ajoutés :
  - `tests/mss.mail.application.tests/Services/Mailboxes/MailboxAgingThresholdsServiceTests.cs` (22) ;
  - `tests/mss.mail.api.tests/E2e/E2eMessageArrivalTests.cs` (8) ;
  - `tests/mss.mail.integration.tests/UseCases/FolderOperationsEndToEndTests.AgingThresholds.cs` (7) ;
  - `tests/mss.mail.integration.tests/Repository/MailboxAgingThresholdsMigrationTests.cs` (3).

##### D'où vient `MailDto.ArrivalDate` (vérifié)

- En ligne : `EmailBuildingService` le lit sur `summary.InternalDate` (l'`INTERNALDATE` IMAP).
- En base : colonne `Mails.ArrivalDate`, écrite depuis la même valeur (`MailRepository`).

L'APPEND de l'outil avec une date commande donc le champ. C'est prouvé de bout en bout (voir plus bas, test 7).

#### Comportement → test d'intégration → preuve rouge (règle 1b)

Toutes les preuves sont des mutations : copie, mutation, test filtré, restauration depuis la copie avec mtime rafraîchi. Le script est `scratchpad/t498/api/mutate.py` ; résultats dans `mutations.json` et `mut-*.log`. Les 20 mutations ont rougi sur une assertion, après une compilation réussie. La M10 initiale ne compilait pas : elle a été écartée, puis refaite sous une forme compilable.

| # | Comportement | Test d'intégration (FolderOperationsEndToEndTests.*, sauf mention) | Mutation (rouge vu) |
|---|---|---|---|
| 1 | GET sans ligne → défauts de la règle 3 | `WithoutASetting_TheDefaultsAreRead_AndWrittenThresholdsAreReadBack_InTheResponseAndInTheBase` (+ unitaire `WithoutARow_…`) | M1 : défaut du service remplacé par un courrier à 0/0/0 |
| 2 | PUT puis relecture : réponse, GET et ligne en base | idem | M2 : `repository.SetAsync` retiré du service. M3 : `SaveChangesAsync` retiré du dépôt. M4 : Second et Late du courrier inversés dans le mapping |
| 3 | Non croissants → 400 problem+json, `code`, `field`, détail français, rien d'écrit (sans ligne, et avec une ligne existante) | `NonIncreasingThresholds_AreRefusedWith400ProblemJson_NamingTheCategory_AndNothingIsWritten` | M6 : contrôle d'ordre neutralisé (`First < 0`). M5 (égalités acceptées) : rouge sur les unitaires `Refused…` |
| 4 | Bornes 1..720 h et 1..365 j | idem (721 h, 0 j) + unitaires | M7 : `value >= 0`. M8 : `value <= max + 1` |
| 5 | Extension `field` dans la réponse | idem | M9 : le gestionnaire revient au seul `IheXdmPackagingRefusedException` |
| 6 | Corps absent → 400 problem+json, rien d'écrit | idem (corps `null`) + unitaire `NoThresholds_…` | M10 : la règle remplace un corps absent par les défauts au lieu de le refuser |
| — | Seuil non entier (2.5) → 400 problem+json | idem | Garanti par le model binding d'ASP.NET (`[ApiController]`), pas par notre code : aucune mutation possible, comportement seulement constaté |
| 7 | Boîte partagée : le délégataire écrit, le titulaire relit, la trace porte le délégataire (RPPS, nom, rôle `Delegate`), les anciennes et les nouvelles valeurs, et seulement des nombres | `TheDelegateChangesAThreshold_TheHolderReadsIt_AndTheJournalNamesTheDelegate_WithTheOldAndNewValues` (vrai AuditService → PostgresAuditSink → `GET /audit/traces`) | M11 : trace supprimée. M12 : anciennes valeurs lues après l'écriture |
| 8 | Préférences de la personne : défauts, retenues (réponse, JSON brut, ligne en base), non partagées avec le délégataire de la même boîte | `TheRingDisplayPreferences_AreDefaultsForAPerson_AreKept_AndAreNotSharedWithAnotherPersonOfTheBox` | M13 : `SaveSettingsAsync` écrit sous l'utilisateur de la boîte au lieu de la personne |
| 9 | Ligne de réglages sans `ringDisplay`, ou avec `null` → défauts | `ARingDisplayAbsentFromTheStoredSettings_IsReadWithTheDefaults` (théorie à 2 cas) | M14 : `RingDisplay ??= new()` retiré, le cas `null` rougit. Le cas « absent » reste vert par construction (initialiseur du contrat) |
| 10 | Outil e2e : `--arrived-days-ago 8` → `MailDto.ArrivalDate` et `SentDate` ≈ maintenant − 8 j dans la liste servie ; sans l'option, maintenant | `TheE2eToolArrivedDaysAgo_DatesTheMessageOnTheMailServer_AndTheListServesThatArrivalDate` (Dovecot réel, `E2eMessage.AppendAsync` de l'outil) | M15 : APPEND sans `INTERNALDATE`. M16 : en-tête `Date:` non posé. M17 (unitaire `E2eMessageArrivalTests`) : `NumberStyles.Integer` accepte « -1 » |
| 11 | Migration : ajout seul (table vide, messages et date de suivi inchangés), descente qui ne retire que sa table, modèle EF ↔ schéma de production | `Repository/MailboxAgingThresholdsMigrationTests` (3) | M18 : `Down()` vide. M19 : la montée efface la ligne de suivi |

Dernier passage vert, après la passe qualité :
- unitaires application : 101/101 (filtres seuils, audit, catalogue d'erreurs, exceptions typées, suivi) ;
- api.tests : 775/775 (filtres E2e, GlobalExceptionHandler, Audit, catalogue, contrôleurs) ;
- intégration : 25/25 (les 10 tests de la task, plus les voisins `MailboxTrackingStartMigrationTests`, `IheXdmEnvelopeSendEndToEndTests`, `TheListMarker…`, `TheDelegateChangesTheStart…`, `AStartInTheFuture…`).

Build de la solution : 0 erreur, 0 avertissement. **Aucune suite complète jouée** (consigne).

#### `python Tools/contracts/contract_impact.py check` (sortie 1)

```
api-mcp        : aucun impact
client-mobile  : avertissement — 14 champ(s) lu(s) absent(s) de origin/develop (lecture tolérante, sans effet) : AbnormalBiologyValueDto.iscritical, AttachmentDto.ismedical, ContactDto.iscomplete, ContactDto.primarymssaddress, PagedResultDto.hasmore, PatientAbnormalBiologyDto.emailfolderpath, … (+8)
client-mobile  : aucun impact
client-angular : avertissement — 13 champ(s) lu(s) absent(s) de origin/develop (lecture tolérante, sans effet) : AbnormalBiologyValueDto.iscritical, AttachmentDto.ismedical, AuditTraceFilterDto.sortby, AuditTraceFilterDto.sortdirection, ContactDto.iscomplete, ContactDto.primarymssaddress, … (+7)
client-angular : IMPACT — la task doit adapter client-angular (modèles, services, tests ; code seul, fichiers listés pour l'humain) :
  - dtos-mss : énumération AuditActionType modifiée : client-angular la décode par rang
```

→ À adapter par l'agent weda2 : reporter `MailboxAgingThresholdsChanged = 77` et son libellé dans `libs/mss/src/core/models/audit.model.ts` et `audit.model.spec.ts`. Signalé à l'orchestrateur.

#### Passe qualité §Q (api-mail)

Diff relu par rapport à `origin/develop` : réutilisation, simplification, efficacité.
- **Appliqué** : le contrôle du corps absent était en double (contrôleur et règle). Celui du contrôleur est retiré. Le service accepte `MailboxAgingThresholdsDto?`, et `EnsureValid` porte `[NotNull]`. Appliqué avant le commit de la fonctionnalité, puis tests ciblés rejoués au vert. M10 est refaite sur ce code.
- **Généralisé** : extension `field` via `IFieldScopedError`, au lieu d'un deuxième `if` par type dans le gestionnaire.
- **Corrigé** : une ligne de test au-delà de 150 caractères (S103).
- Contrôles mécaniques 2b (S125, xUnit1045, S4457, xUnit2032, CA1068, xUnit1051, CA1861, S1905, CA1826) : rien.
- Aucune autre simplification retenue. Les helpers `Thresholds` / `Of` sont dupliqués entre le test unitaire et le test d'intégration, mais dans deux projets distincts : la duplication est acceptée.

#### Points ouverts

1. **Précondition d'E2E-RING-004** (validée par l'orchestrateur, écrite au catalogue) : le seed pose la date de début du suivi à J-1. Un courrier arrivé il y a 8 jours serait alors « hors suivi », donc sans compteur (`AMessageArrivedBeforeTheTrackingStart_IsNotToHandle`).
   - Le parcours lit `tracking-start`, le recule à maintenant − 10 jours, et le restaure dans le `finally` avec les seuils par défaut.
   - Le seed n'est pas modifié.
2. **Miroir `AuditActionType` sur weda2** : à faire par l'agent weda2 (impact ci-dessus).
3. **client-blazor** (hors task) : ni bump de `Dtos.Mss` 641.0.0, ni miroir `AuditActionLabels.cs`. À reprendre à la prochaine task Blazor.
4. Une catégorie envoyée à `null` dans le corps est refusée (« Les seuils … sont requis. », `field` = la catégorie). Une catégorie **absente** du JSON garde la valeur par défaut du DTO : c'est une mise à jour partielle de fait. Le contrat ne le tranche pas ; les clients envoient les trois catégories.
5. Pas de garde de concurrence sur la première écriture (deux premières écritures simultanées, conflit de clé primaire, 500). Même choix que `MailboxTrackingRepository` ; risque jugé négligeable.
6. `Tools/timing/step.sh start --step develop` a été appelé par cet agent au début. Le `step.sh end` est laissé à l'orchestrateur.
7. 40 fichiers dans le diff api-mail, dont 13 `packages.lock.json` du bump : 27 hors fichiers de verrouillage.

### client-angular (weda2)

### task-498 — weda2 (client-angular), develop log

Mode code-only : **aucune opération git**. Branche extraite au départ : `feature/nova-mss-weda-integration`
(arbre propre, HEAD `3f6e9119`). Tous les fichiers sont en CRLF, comme le reste du dépôt.

#### Fichiers à commiter sur TFS (41)

Chemins relatifs à `Client/Angular/`.

##### Modifiés (26)

| Fichier | Raison |
|---|---|
| `front/libs/mss/src/core/models/user-settings.model.ts` | Modèles du contrat : `AgingThresholdsDto`, `MailboxAgingThresholdsDto`, `AgingCategory`, `RingDisplayPreferencesDto`, valeurs par défaut (règles 3 et 9), `ringDisplayOf` (préférences absentes ou incomplètes = défauts), `UserSettingsDto.ringDisplay`. |
| `front/libs/mss/src/core/models/audit.model.ts` | **Adaptation de contrat** (`contract_impact.py`) : `AuditActionType.MailboxAgingThresholdsChanged = 77`, libellé « Seuils d'ancienneté de la boîte modifiés ». |
| `front/libs/mss/src/core/models/audit.model.spec.ts` | **Adaptation de contrat** : ordinal 77 figé, libellé vérifié (vu rouge). |
| `front/libs/mss/src/core/services/mss-api.service.ts` | `getMailboxAgingThresholds` / `saveMailboxAgingThresholds` (`GET|PUT api/v1/account/mailboxes/current/aging-thresholds`). |
| `front/libs/mss/src/core/utils/mail-ring.util.ts` | Contexte de l'anneau : `display` (préférences). Initiales et gravité masquées via `shownRing` ; « Attente » masquée dans `mailRingChips`. L'état en clair reste complet. |
| `front/libs/mss/src/core/utils/mail-ring.util.spec.ts` | Tests des préférences (affectation, gravité, attente, ⚠ atténué indépendant). |
| `front/libs/mss/src/core/utils/mail-ring-row.util.ts` | La mémoire d'une ligne compare aussi les préférences (sinon un changement de préférence ne redessinait pas la ligne). |
| `front/libs/mss/src/core/utils/mail-ring-row.util.spec.ts` | Test : la mémoire suit les préférences. |
| `front/libs/mss/src/ui/mail-ring/mail-ring.component.ts` | Entrées `late` (« , en retard » après la nature dans le libellé lu et l'infobulle), `animated`, `highContrast` ; attributs `data-late`, `data-contrast`. |
| `front/libs/mss/src/ui/mail-ring/mail-ring.component.html` | Classe `mss-mail-ring--contrast`. |
| `front/libs/mss/src/ui/mail-ring/mail-ring.component.scss` | Contraste renforcé : teintes plus sombres (rapports mesurés en commentaire), traits plus épais. |
| `front/libs/mss/src/ui/mail-ring/mail-ring.component.spec.ts` | Tests retard / animations / contraste. |
| `front/libs/mss/src/features/mail/components/mail-header/mail-header.component.ts` | Ancienneté de la ligne (`ringAging`, `ageChip`), préférences passées au contexte et à l'anneau ; `hasRingMentions` sorti de `collapsesTypeLine` (complexité 21 > 20 avec le compteur, convention `complexity`). |
| `front/libs/mss/src/features/mail/components/mail-header/mail-header.component.html` | Mention « J+N » / « H+N » dans la rangée des mentions (`data-testid="mail-row-age-{uid}"`, `aria-label` = phrase entière) ; entrées `late`, `animated`, `highContrast` de l'anneau. |
| `front/libs/mss/src/features/mail/components/mail-header/mail-header.component.scss` | `.mail-ring-chip--late` (fond plein, 14,6:1) ; s'efface au survol avec les autres mentions. |
| `front/libs/mss/src/features/mail/components/mail-header/mail-header.light-row.spec.ts` | Horloge figée (`MSS_CLOCK`) le jour de la date d'envoi du jeu : sinon un compteur qui vieillit change la ligne (convention `spec-qui-lit-une-ligne-de-liste…`). |
| `front/libs/mss/src/features/mail/components/mail-header/mail-header.ring.spec.ts` | Même horloge figée (l'état en clair attendu ne dépend plus du calendrier). |
| `front/libs/mss/src/features/mail/components/mail-ring-panel/mail-ring-panel.component.ts` | Ancienneté par unité (message : catégorie du message ; compte rendu : catégorie de sa gravité, date du message), préférences au contexte et aux anneaux. |
| `front/libs/mss/src/features/mail/components/mail-ring-panel/mail-ring-panel.component.html` | Ligne « Ouvert depuis N jours. » (`data-testid="mail-ring-aging"`, `data-late`) ; entrées de l'anneau. |
| `front/libs/mss/src/features/mail/components/mail-ring-panel/mail-ring-panel.component.scss` | Style de la ligne d'ancienneté (gras au dernier seuil). |
| `front/libs/mss/src/features/mail/mss-mail.component.ts` | Seuils lus une fois avec les réglages ; préférences posées depuis les réglages lus. |
| `front/libs/mss/src/features/settings/mss-settings.component.ts` | Section « Anneau de traitement » (6 préférences, enregistrées par la sauvegarde des réglages existante) ; seuils (saisie, validation locale, enregistrement différé 300 ms, refus serveur sous la catégorie, saisie redevenue invalide jamais envoyée). |
| `front/libs/mss/src/features/settings/mss-settings.component.html` | Section « Anneau de traitement » après « Lecture » (toggles + légende) ; seuils dans « Boîte aux lettres » après la date de suivi (`settings-aging-{catégorie}-{first|second|late}`, `settings-aging-{catégorie}-error`). |
| `front/libs/mss/src/features/settings/mss-settings.component.scss` | Grille des seuils. |
| `front/e2e/mss-e2e/support/e2e-backend.ts` | Option `arrivedDaysAgo` → `--arrived-days-ago` ; `E2eMail.arrivalDate` ; `OtherDevice.saveTrackingStart`, `agingThresholds`, `saveAgingThresholds` ; `DEFAULT_E2E_AGING_THRESHOLDS`. |
| `front/e2e/mss-e2e/specs/functional.e2e.ts` | E2E-RING-004 v1 et E2E-SETTINGS-006 v1 (+ aides `useDefaultRingDisplay`, `trackTenDaysBack`, `restoreRingState`, `calendarDaysSince`) ; et, à la demande du coordinateur, formatage prettier de 4 lignes de RING-005 (task-500, recette), sans changement de logique. |

##### Créés (15)

| Fichier | Raison |
|---|---|
| `front/libs/mss/src/core/utils/mail-aging.util.ts` | Calcul pur de l'ancienneté (§ 3), horloge passée en paramètre ; `lateRingLabel` ; validation locale des seuils ; lecture du refus serveur (`agingThresholdsRefusal`). |
| `front/libs/mss/src/core/utils/mail-aging.util.spec.ts` | Tests du calcul à horloge fixée (DoD), de la validation et du refus. |
| `front/libs/mss/src/core/utils/mail-ring-display.util.ts` | `shownRing` : préférences appliquées à la vue (initiales, gravité). Fichier à part pour garder `mail-ring.util.ts` sous 500 lignes (avertissement `max-lines`). |
| `front/libs/mss/src/core/services/ring-settings.service.ts` | Service racine : seuils de la boîte (lus, relus après PUT réussi, lecture dépassée ignorée, échec = défauts) et préférences de la personne, partagés liste / détail / Paramètres. |
| `front/libs/mss/src/core/services/ring-settings.service.spec.ts` | Tests du service. |
| `front/libs/mss/src/core/services/mss-api.aging-thresholds.service.spec.ts` | Route et corps prouvés jusqu'à la requête HTTP. |
| `front/libs/mss/src/core/tokens/mss-clock.token.ts` | `MSS_CLOCK` : horloge injectée (tests à horloge figée). |
| `front/libs/mss/src/features/mail/components/mail-header/mail-header.aging.spec.ts` | Tests composant de la ligne : J+N, H+N, fond plein, « en retard », chaque préférence. |
| `front/libs/mss/src/features/mail/components/mail-ring-panel/mail-ring-panel.aging.spec.ts` | Tests du bloc du détail : « Ouvert depuis… », retard, préférences. |
| `front/libs/mss/src/features/mail/mss-mail.component.ring-settings.spec.ts` | Seuils lus avec les réglages, préférences posées. |
| `front/libs/mss/src/features/settings/mss-settings.ring.spec.ts` | Tests des Paramètres (section, préférences, seuils, refus). |
| `front/libs/mss/src/features/settings/ring-legend/ring-legend.component.ts` | Légende (règle 10) : chaque état dessiné par `mss-mail-ring` + `mailRingView` réels sur des messages d'exemple ; seuils cités ; préférences suivies. |
| `front/libs/mss/src/features/settings/ring-legend/ring-legend.component.html` | Gabarit (`ring-legend-entry-{clé}`, `ring-legend-thresholds-{catégorie}`, `ring-legend-age`). |
| `front/libs/mss/src/features/settings/ring-legend/ring-legend.component.scss` | Styles de la légende. |
| `front/libs/mss/src/features/settings/ring-legend/ring-legend.component.spec.ts` | Tests de la légende. |

#### Choix faits là où la US est muette

Alignés avec l'agent mobile (t498-mobile, message du 2026-11-27) :

1. **Libellé accessible en retard** : « , en retard » inséré **après la nature**, pas en fin. Exemple : « Courrier, en retard. Étape 2 sur 3 … ». En fin, on aurait lu « Non affecté., en retard ».
2. **Détail** : la phrase s'affiche pour toute boucle ouverte, même avant le 1er seuil.
   - En jours : « Ouvert aujourd'hui », « Ouvert depuis 1 jour », « Ouvert depuis N jours ».
   - Biologie critique avant 72 h : « Ouvert depuis moins d'une heure », « … 1 heure », « … N heures ».
   - « , en retard » au dernier seuil. Masquée si « Ancienneté » est désactivée.
3. **Compteur de la ligne** : mention texte dans la rangée des mentions, à côté de « Attente patient », comme dans la maquette D. Pas de pastille sur l'anneau : « J+14 » ne tient pas dans la gouttière de 19 px. `aria-label` « Ouvert depuis 8 jours, en retard ». Fond plein au dernier seuil.
4. **Compte rendu dans le détail** : catégorie selon sa gravité (critique → heures, anomalie → biologie). Date de référence : celle du message.
5. **Écoulé négatif** (horloge du poste en retard) : ramené à 0.
6. **Les préférences masquent l'élément visuel seulement.** L'état en clair de l'anneau reste complet : initiales, attente et gravité y sont dites, et le retard reste dans le libellé même si le compteur est masqué.
7. **Icône classique** (pas d'anneau) : pas de compteur. Le compteur suit les mentions du mode anneau.
8. **Seuils** :
   - enregistrés au changement de champ (`change`), 300 ms après la dernière saisie, seulement si les trois catégories sont valides ; une saisie redevenue invalide pendant l'attente n'est jamais envoyée ;
   - après un PUT réussi, les seuils sont **relus par un GET** (« relus du serveur ») ;
   - lecture en échec : seuils par défaut, jamais ceux d'une autre boîte ;
   - un refus local ou serveur s'affiche sous sa catégorie ; tout autre échec est annoncé une fois sous les seuils.
9. **Légende quand une préférence masque un élément** : l'entrée reste, sans le dessin masqué, avec « Masqué par vos réglages d'affichage. » (`data-hidden="true"`). Les seuils restent cités même si l'ancienneté est masquée.
10. **Lecture des seuils dans `RingSettingsService`** : elle passe par `defer`, pour qu'une exception levée à l'appel lui-même devienne une erreur de lecture (seuils par défaut). Effet de bord voulu : les doubles d'API des specs existants de `MssMailComponent` (une quinzaine), qui n'ont pas cette méthode, ne cassent pas.
11. **e2e** :
    - le début du suivi passe à maintenant − 10 jours en tête de parcours (ajout du coordinateur au contrat § 5), et est restauré dans le `finally`. Je l'applique aussi à E2E-SETTINGS-006, qui a besoin d'un courrier compté (J+5) ;
    - le `finally` remet aussi les seuils par défaut et les préférences par défaut, par l'API.

#### Preuves rouges

Un spec écrit avant le code a été **vu rouge**, ou une **mutation** l'a fait échouer (réinjectée, vue rouge, restaurée). Le script `mutate.py` restaure toujours le fichier, et `git status` a été vérifié après chaque série. Journaux : `scratchpad\t498\weda2\mut-*.log`.

| Preuve | Spec | Résultat |
|---|---|---|
| Spec avant code | `mail-aging.util.spec.ts` | rouge (module absent), puis 20/20 |
| M1 « remis à traiter » ignoré | aging | 1 rouge |
| M2 jours non calendaires (24 h) | aging | 2 rouges |
| M3 critique toujours en heures | aging | 1 rouge |
| M4 fermé / hors suivi comptés | aging | 1 rouge |
| M5 seuils de la mauvaise catégorie | aging | 3 rouges |
| M26 catégorie inconnue acceptée dans le refus serveur | aging | 1 rouge |
| M6 / M6b affectation non masquée | ring util + row | 2 rouges |
| M7 / M7b gravité non masquée | ring util | 2 rouges |
| M8 attente non masquée | ring util | 1 rouge |
| M9 mémoire de ligne aveugle aux préférences | row | 1 rouge |
| Spec avant code | `mss-api.aging-thresholds.service.spec.ts` | 2 rouges (méthodes absentes) |
| M10 pas de relecture après PUT | service | 1 rouge |
| M11 lecture dépassée appliquée | service | 1 rouge |
| M12 échec de lecture garde l'ancienne boîte | service | 1 rouge |
| Spec avant code | `mail-ring.component.spec.ts` (task-498) | 3 rouges |
| Spec avant code | `mail-header.aging.spec.ts` | 10 rouges |
| M13 préférence « Ancienneté » ignorée | header | 1 rouge |
| M14 « en retard » absent du libellé de l'anneau | header | 2 rouges |
| M15 ligne du type repliée malgré le compteur | header | 6 rouges |
| M16 pas de fond plein | header | 2 rouges |
| M17 contraste non transmis | header | 1 rouge |
| M18 animations non transmises | header | 1 rouge |
| M19 préférences absentes du contexte | header | 3 rouges |
| Spec avant code | `mail-ring-panel.aging.spec.ts` | 6 rouges |
| M20 détail ignore « Ancienneté » | panel | 1 rouge |
| M21 compte rendu compté comme courrier | panel | 1 rouge |
| M22 détail sans « en retard » dans l'anneau | panel | 1 rouge |
| M23 détail sans préférences | panel | 1 rouge |
| M24 seuils non lus par l'écran mail | mss-mail | 1 rouge |
| M25 préférences non posées par l'écran mail | mss-mail | 1 rouge |
| Spec avant code | `ring-legend.component.spec.ts` | rouge (module absent) |
| M27 légende cite les seuils par défaut au lieu de ceux de la boîte | legend | 1 rouge |
| M28 légende aveugle aux préférences | legend | 2 rouges |
| M29 compteur dessiné malgré « Ancienneté » masquée | legend | 1 rouge |
| M30 contraste non transmis à la légende | legend | 1 rouge |
| Spec avant code | `mss-settings.ring.spec.ts` | 10 rouges |
| M31 saisie redevenue invalide envoyée | settings | 1 rouge (défaut réel trouvé par le spec et corrigé : un enregistrement différé partait avec un seuil vide) |
| M32 préférence non posée pour la liste | settings | 1 rouge |
| M33 refus serveur non affiché sous la catégorie | settings | 1 rouge |
| M34 seuils non lus aux Paramètres | settings | 2 rouges |
| M35 aucun enregistrement des seuils | settings | 3 rouges |
| Spec avant code (adaptation de contrat) | `audit.model.spec.ts` | 3 rouges |

#### Vérifications jouées

- **Vitest**, specs ciblés uniquement : `src/core`, `src/ui/mail-ring`, mail-header, mail-ring-panel, mail-detail, mail-list, `mss-mail*`, settings et audit. **111 fichiers, 1 279 tests verts, aucune erreur non gérée.** Ni la suite complète ni `nx build` n'ont été joués (laissés à l'orchestrateur).
- **ESLint**, fichiers touchés :
  - 0 erreur ;
  - avertissements restants tous antérieurs : `max-lines` de fichiers déjà au-delà de 500 lignes, et un `require-example` sur `loadMailServer` ;
  - `mail-ring.util.ts` reste à 499 lignes ;
  - la complexité de `collapsesTypeLine` est ramenée sous 20.
- **Stylelint**, SCSS touchés : 0 erreur. Les 2 avertissements de `mail-header.component.scss` (lignes 439 et 446) sont antérieurs.
- **tsc** : `npx tsc --noEmit -p e2e/mss-e2e/tsconfig.json` sort à 0. Le `tsconfig.spec` de la lib ne relève aucune erreur dans les fichiers de la task (le bruit restant vient de fichiers antérieurs).
- **ESLint e2e** : aucune erreur ni avertissement sur les lignes ajoutées. Les 4 erreurs prettier de `functional.e2e.ts` (lignes 9462 à 9470) appartiennent à RING-005 (task-500) et sont antérieures.

#### Passe qualité §Q (2026-11-27)

Lecture du diff : `git diff`, plus les fichiers non suivis de `Client/Angular`. Contrôles mécaniques 2b :
- fins de ligne homogènes ;
- aucune `interval(` / `timer(` ajoutée ;
- aucune clé sur `.uid` seul ;
- aucun `folders().find` sur un chemin.

- **Appliqué** : `ring-legend.component.ts`, les deux mentions d'attente dupliquées sont sorties en constante
  `WAITING_CHIPS`. Comportement inchangé : `features/settings` rejoué, 3 fichiers et 54 tests verts, ESLint 0.
- **Formatage demandé** : prettier sur `functional.e2e.ts`, lignes 9462 à 9470 (RING-005, task-500). ESLint e2e :
  0 erreur. `tsc -p e2e/mss-e2e/tsconfig.json` sort à 0.
- **Écarté**, gain trop faible ou hors du diff :
  - l'ancienneté de la ligne est calculée 2 à 3 fois par rendu (`ageChip`, `collapsesTypeLine`, gabarit) : quelques
    opérations de date ;
  - le même calcul de jours calendaires existe dans `conversation.util.ts` (`chatDayLabel`). Le factoriser
    toucherait du code hors de la task ;
  - les styles des mentions sont dupliqués entre la ligne et la légende : styles propres à chaque composant ;
  - `localThresholdErrors` pourrait être un `computed`, sans gain réel.

#### Reste à faire

- **Les e2e n'ont pas été joués** (banc partagé) : E2E-RING-004 et E2E-SETTINGS-006 sont à jouer par `/e2e`. Leur preuve rouge par mutation (convention `preuve-par-mutation`) reste à faire au banc. Mutations proposées :
  - RING-004 : retirer `[class.mail-ring-chip--late]` ;
  - SETTINGS-006 : ignorer `showAging` dans `ageChip`.
- Elles dépendent de l'option `--arrived-days-ago` de l'outil e2e et de la route `aging-thresholds` (agent api-mail).
- `nx build weda2` : contrôle de types des gabarits (`strictTemplates`) non joué ici.

### client-mobile

### task-498 — client-mobile — Develop log

Branche `feat/task-498-anneau-anciennete-seuils-de-la-boite` (`Client/Mobile`), **4 commits locaux, non poussés**.
Journaux de tests et de lint : ce dossier (`*.log`, `*.clean.log`).

#### Commits

| SHA | Message |
|---|---|
| `2374241` | feat(mail): ancienneté de la boucle, seuils de la boîte et préférences de l'anneau |
| `ded3406` | feat(mail): compteur J+N / H+N, « en retard » et préférences de l'anneau, liste et détail |
| `e9e39a7` | feat(settings): seuils de la boîte dans « Suivi », page « Anneau de traitement » (préférences et légende) |
| `71a95fb` | test(mobile): E2E-RING-004 et E2E-SETTINGS-006 — ancienneté, seuils de la boîte, légende |

44 fichiers, +3153 / −44 par rapport à `origin/develop`.

#### Fichiers touchés

**Cœur (contrat, services, calcul)**
- `src/app/core/models/user-settings.model.ts` — `AgingThresholdsDto`, `MailboxAgingThresholdsDto`,
  `DEFAULT_AGING_THRESHOLDS`, `MAILBOX_AGING_THRESHOLDS_INVALID`, `RingDisplayPreferencesDto`,
  `DEFAULT_RING_DISPLAY`, `UserSettingsDto.ringDisplay?` (camelCase, recopie exacte du contrat § 1).
- `src/app/core/services/mss-api.service.ts` — `getMailboxAgingThresholds` / `saveMailboxAgingThresholds`
  (`GET|PUT api/v1/account/mailboxes/current/aging-thresholds`).
- `src/app/core/services/mailbox-aging-thresholds.service.ts` (nouveau) — seuils de la BOÎTE : lus au changement de
  boîte (effect sur `currentEmail`, comme `MailboxTrackingService`), relus après un PUT réussi, réponse d'une boîte
  quittée ignorée ; un refus rend `{ ok:false, field, detail }` lu dans le problem+json. Défauts tant que non lus.
- `src/app/core/services/user-settings.service.ts` — `ringDisplay` (fusion avec les défauts) et
  `updateRingDisplay(key, value)` par la sauvegarde des réglages existante (spread, rien avant la lecture).
- `src/app/core/utils/treatment-ring-aging.util.ts` (nouveau) — calcul pur à horloge passée (§ 3) :
  `ringAgingReference`, `mailRingAging`, `reportRingAging`, `withAgingLabel`, `agingThresholdsOf`.
- `src/app/core/utils/aging-thresholds.util.ts` (nouveau) — catégories, validation locale (mêmes bornes et messages
  que le serveur), citation des seuils pour la légende.
- `src/app/core/utils/clock.ts` (nouveau) — `CLOCK`, horloge de l'affichage injectable (figée dans les specs).

**Liste et détail**
- `features/mail/components/treatment-ring/*` — entrée `display` : initiales, gravité, animations masquées chacune
  seule ; `data-contrast="high"` + classe `ring--contrast` (traits 7 / 2,6 / coche 4, neutre et traits fins en
  `--app-on-surface-variant`, ≥ 4,5:1 sur les 4 fonds de ligne). Libellé accessible inchangé.
- `features/mail/components/ring-chip/*` (nouveau, `mss-ring-chip`) — la pastille de texte de l'anneau
  (« Attente patient », compteur « J+N »), partagée par la ligne et la légende. Styles déplacés de mail-header.
- `features/mail/components/mail-header/*` — entrées `ringDisplay`, `agingThresholds` ; compteur
  `data-testid="mail-age-{uid}"` (`data-level`, `aria-label` « Ouvert depuis 8 jours, en retard »), fond plein au
  dernier seuil (`mail-ring-age--late`) ; « , en retard » dans le libellé de l'anneau (appui long) ; « Attente »
  masquable ; cache recalculé à la minute (horloge `CLOCK`).
- `features/mail/components/mail-list/*` — passe `ringDisplay` (réglages) et `agingThresholds` (service).
- `features/mail/components/treatment-ring-steps/*` — entrées `aging` et `display` ; ligne
  `data-testid="detail-ring-aging"` (« Ouvert depuis N jours », `ring-aging--late`).
- `features/mail/components/mail-detail/mail-detail.component.{ts,html}` — ancienneté par bloc (message ou compte
  rendu), libellé « en retard », préférence « Ancienneté » ; cache incluant seuils, préférence et minute.

**Paramètres et légende**
- `src/app/settings/settings.page.{ts,html,scss}` — section « Suivi » : 3 catégories × 3 `ion-input`
  (`settings-aging-{criticalBiologyHours|biologyDays|correspondenceDays}-{first|second|late}`), erreur sous la
  catégorie (`settings-aging-error-{catégorie}`), refus général (`settings-aging-error`), bouton
  `settings-aging-save`, avis `settings-aging-saved`, `settings-aging-unavailable` si non lus. Section
  « Organisation » : entrée `settings-ring-nav` « Anneau de traitement » → `/treatment-ring-legend`.
- `src/app/treatment-ring-legend/*` (nouveau, page autonome `app-treatment-ring-legend`) — bascules
  `ring-pref-{assignment|waiting|severity|aging|animations|contrast}` ; légende `ring-legend` avec entrées
  `ring-legend-{steps|report|closed|untracked|assignment|unassigned|waiting|severity|aging}`, seuils cités
  `ring-legend-thresholds`, mentions `ring-legend-{assignment|waiting|severity|aging}-hidden`.
- `src/app/app-routing.module.ts` — route `treatment-ring-legend` (`loadComponent`).

**Specs**
- Nouveaux : `treatment-ring-aging.util.spec.ts`, `aging-thresholds.util.spec.ts`,
  `mailbox-aging-thresholds.service.spec.ts`, `mss-api.aging-thresholds.spec.ts`, `treatment-ring.display.spec.ts`,
  `mail-header.aging.spec.ts`, `treatment-ring-legend.page.spec.ts`.
- Étendus : `user-settings.service.spec.ts`, `treatment-ring-steps.component.spec.ts`, `mail-detail.ring.spec.ts`
  (+ `CLOCK` figé au 27/11/2026 09:00 : ses dates fixes ne vieillissent plus), `settings.page.spec.ts` (doubles
  `MailboxAgingThresholdsService` et `Router`), `mail-list.ring.spec.ts` (double `ringDisplay`).

**e2e** (`e2e/`)
- `support/e2e-backend.ts` — `CreateMessageOptions.arrivedDaysAgo` → `--arrived-days-ago` ; `E2eMail.arrivalDate` ;
  `OtherDevice.agingThresholds / setAgingThresholds / setTrackingStart / ringDisplaySetting / setRingDisplaySetting`
  (`trackingStart()` existait déjà, task-466) ; `E2E_DEFAULT_AGING_THRESHOLDS`, `E2E_DEFAULT_RING_DISPLAY`.
- `specs/functional.spec.ts` — `E2E-RING-004` v1 et `E2E-SETTINGS-006` v1 (fin de fichier), avec `isolateAging`
  (début du suivi reculé à maintenant − 10 jours : le seed le pose à J-1, ajout au contrat § 5 par le coordinateur)
  et `restoreAging` dans le `finally` (seuils par défaut, préférences par défaut, date de suivi lue au départ,
  messages supprimés ; chaque remise tentée même si une autre échoue).
- **Non joués** (banc partagé, consigne). `npx tsc -p e2e/tsconfig.json --noEmit` : 0 erreur (`e2e-tsc.log`) ; eslint
  des deux fichiers : 0 erreur.

#### Vérifications

- Passe ciblée finale (`final-targeted.log`) : utils de l'anneau, `core/services/`, treatment-ring, steps,
  mail-header, mail-list, mail-detail, settings, légende → **749/749 SUCCESS**. Suite complète et `npm run build`
  non joués (consigne : l'orchestrateur les joue).
- Lint ciblé (`lint.log`, `ESLINT_USE_FLAT_CONFIG=false npx eslint` sur les 36 fichiers `src/**/*.{ts,html}` touchés) :
  0 erreur, 0 avertissement.
- `data-testid` : compteur, chaque champ de seuil, chaque préférence, chaque entrée de légende (DoD).
- Aucune couleur en dur : jetons du thème seulement (`--app-outline`, `--app-on-surface(-variant)`, `--app-flag`,
  `--ion-color-tertiary`, `--ion-color-danger`, `--app-surface-container-lowest`).

#### Preuves rouges

1. `core/utils/treatment-ring-aging.util.spec.ts` écrit avant le code : rouge à la compilation
   (`TS2307: Cannot find module './treatment-ring-aging.util'`, `red-aging-util.log`). Vert 26/26
   (`green-aging-util.log`). Mutation (`mut-aging-util.log`) : référence sans « remis à traiter », `>` au lieu de
   `>=` au dernier seuil, biologie critique toujours en heures → 6 FAILED (remis à traiter, dernier seuil courrier /
   biologie / critique J+N, libellé « en retard », seuils modifiés). Restauré.
2. Services (`mss-api.aging-thresholds.spec.ts`, `mailbox-aging-thresholds.service.spec.ts`, ajouts à
   `user-settings.service.spec.ts`) écrits avant le code : rouges à la compilation (`red-services.log` : module
   `mailbox-aging-thresholds.service` introuvable, `getMailboxAgingThresholds` inexistant). Verts 38/38
   (`green-services.log`). Mutation (`mut-services.log`) : pas de relecture après PUT, `field` perdu, préférences
   sans fusion des défauts (`showAging` forcé), route PUT erronée → 5 FAILED. Restauré.
3. Anneau (`treatment-ring.display.spec.ts`) écrit avant le code : 7/10 rouges (`red-ring-display.log`), verts 51/51
   avec la spec existante (`green-ring.log`, contrastes inclus).
4. Ligne (`mail-header.aging.spec.ts`) écrite avant le code : 10/14 rouges (`red-header.log`) ; verts 158/158 avec
   les specs mail-header et mail-list (`green-header.log`, puis `green-header2.log` après correction d'une lecture
   de style vivante dans le test).
5. Mutation anneau + ligne (`mut-header-ring.log`) : attente non masquée, libellé sans « en retard », fond plein retiré,
   initiales et gravité non masquées, classe de contraste neutralisée, animations ignorées → 12 FAILED. Restauré.
6. Détail (`treatment-ring-steps.component.spec.ts`, `mail-detail.ring.spec.ts` « ancienneté (task-498) », à travers
   le parent, horloge `CLOCK` figée) écrits avant le code : 6 rouges (`red-detail.log`) ; verts 141/141
   (`green-detail.log`). Mutation (`mut-detail.log`) : compteur de ligne non masqué par « Ancienneté », détail non
   masqué, libellé du détail sans « en retard », préférences non transmises au grand anneau → 4 FAILED. Restauré.
7. Paramètres, seuils, légende (`aging-thresholds.util.spec.ts`, ajouts à `settings.page.spec.ts`,
   `treatment-ring-legend.page.spec.ts`) écrits avant le code : rouges à la compilation (`red-settings.log` :
   module `aging-thresholds.util` introuvable, `onAgingInput` / `saveAgingThresholds` / `onPreferenceChange`
   inexistants). Verts 168/168 avec les specs mail-header (`green-settings.log`, extraction de `mss-ring-chip`
   comprise). Mutation (`mut-settings.log`) : refus serveur non affiché, enregistrement malgré la validation locale,
   préférences non transmises aux anneaux de la légende, seuils cités en dur, compteur de la légende non masqué →
   7 FAILED. La mutation `2e <= dernier` n'était pas vue : cas (1, 7, 7) ajouté, puis rouge (`mut-atu.log`, 1 FAILED)
   et vert (`green-atu.log`). Restauré.
8. e2e RING-004 / SETTINGS-006 : **non vus rouges** (non joués, consigne du banc partagé). À prouver à `/e2e`.

#### Choix faits là où la US est muette (alignés avec l'agent weda2, qui confirme les 6 points)

1. **Libellé « en retard »** inséré après la tête : « Courrier, en retard. Étape 1 sur 3 : … » (un « , en retard »
   après le point final donnerait « Non affecté., en retard »). Seulement au dernier seuil.
2. **Détail** : « Ouvert depuis N jours » pour toute boucle ouverte (pas seulement après le 1er seuil) ; « Ouvert
   aujourd'hui » (0 jour), « depuis 1 jour » ; biologie critique < 72 h : « depuis N heures », « depuis 1 heure »,
   « depuis moins d'une heure » ; « , en retard » au dernier seuil.
3. **Compteur de la ligne** : pastille texte dans la rangée des mentions, à côté de « Attente patient » (maquette D,
   « le reste est écrit à droite »), pas sur l'anneau lui-même (déjà chargé de deux pastilles depuis task-500 R3).
4. **Compte rendu du détail** : catégorie tirée de sa gravité (critique → heures, anomalie → biologie), date de
   référence = celle du message.
5. Écoulé négatif (horloge du poste en retard) → 0. « Icône classique » → aucun compteur (pas d'anneau).
6. **Préférences = visuel seulement** : le libellé en clair de l'anneau (appui long, lecteur d'écran) reste complet
   (« À traiter par … », « Biologie, valeur critique »).
7. Seuils : enregistrement **d'un bloc** par un bouton « Enregistrer les seuils » (actif si modifié et valide), pas
   d'enregistrement à chaque champ (une saisie montante passerait par des états non croissants). Champ vidé = 0 →
   refus « de 1 à … ». Seuils non lus → pas de champs, message « n'ont pas pu être lus » (rien de faux proposé) ;
   l'ancienneté se calcule alors sur les défauts.
8. Légende : entrées des éléments masqués conservées, échantillon retiré et mention « Masqué dans vos préférences »
   (la gravité masquée garde le badge ⚠ et le dit). Seuils toujours cités (donnée de la boîte, pas une préférence).
9. Le calcul de la ligne et du détail est recalculé au plus une fois par minute (cache) ; aucune écriture, aucun
   minuteur : un écran resté ouvert des heures se met à jour au prochain rendu.

#### Stitch (best-effort)

- `settings` : **réutilisé**, écran `34d145c4e04d48ebab80ff05afb709af` (titre `settings`, instance encore sans
  label — à labelliser dans l'interface). Capture :
  `https://stitch.googleapis.com/v1/projects/10088502293310567548/files/9236e00c390a4175931000f0ec4b7b74:download` ;
  HTML : `https://stitch.googleapis.com/v1/projects/10088502293310567548/files/00db0533d359454eb3f5301692aa2d7e:download`.
  Non regénéré : `edit_screens` n'aboutit pas sur timeout (mémoire du 2026-10-24) ; les seuils dans « Suivi » sont
  un ajout de bloc à l'écran existant.
- `treatment-ring-legend` : **généré une fois** (`generate_screen_from_text`, MOBILE, design system
  `assets/9aca84edc31f42798fd98bd24e151040`) → timeout, comme attendu. Résultat du diff de `screenInstances` : voir
  ci-dessous. Jamais regénéré.

#### Leçons (amélioration continue)

- **Piège d'outillage** : dans l'outil Bash de la session, un heredoc qui contient des accents graves (littéraux de
  gabarit TypeScript) échoue avant exécution (« unexpected EOF while looking for matching `'` ») — deux fois.
  Contournement : écrire le script d'édition dans un fichier (Write), puis `python fichier.py`. À consigner en
  mémoire de session (pas une consigne de code).
- **Prévention appliquée d'emblée** (consigne `spec-qui-lit-une-ligne-de-liste-cible-l-objet`) : l'ancienneté rend
  dépendante de l'horloge toute spec dont le jeu de test porte une date fixe et un anneau ouvert. `mail-detail.ring.spec.ts`
  (arrivée au 26/11/2026) aurait viré au rouge le 10/12/2026 (« en retard » dans l'état en clair). Horloge injectée
  `CLOCK`, figée dans cette spec et dans les nouvelles. Les autres specs de la liste ont des dates déjà anciennes
  (janvier/mars 2026) ou aucune date : stables.

##### Résultat Stitch `treatment-ring-legend`

**Génération non matérialisée** : deux diffs de `screenInstances` (après la passe de specs de ~2 min, puis après
la rédaction de ce journal) → aucune instance nouvelle (64 avant et après). Non regénéré (risque de doublon).
Prompt pour l'humain, à lancer dans l'interface Stitch (projet `client-mobile`, MOBILE, design system
`assets/9aca84edc31f42798fd98bd24e151040`) :

> treatment-ring-legend — écran mobile « Anneau de traitement », ouvert depuis Paramètres (en-tête avec bouton
> retour), même style que l'écran « settings » (cartes blanches à coins de 8 px, titres de section en majuscules
> gris, rangées de 56 px, Public Sans, palette Clinical Precision). Section « ÉLÉMENTS AFFICHÉS » : cinq bascules
> avec une ligne d'aide (Affectation, Attente d'un tiers, Gravité — « le badge ⚠ reste toujours », Ancienneté,
> Animations), toutes activées. Section « ACCESSIBILITÉ » : « Contraste renforcé — traits plus épais et plus
> sombres », désactivée. Section « LÉGENDE DES ANNEAUX » : questions en petites capitales (« Où en est-on ? »,
> « À qui le tour ? », « Depuis combien de temps ? », « Est-ce grave ? », « Sans boucle »), chaque entrée = petit
> anneau segmenté de 32 px à gauche + titre gras et explication à droite ; pastilles « J+4 », « J+15 » (fond plein
> gris foncé), « H+15 » et la phrase des seuils de la boîte ; anneaux ambre et rouge avec badge ⚠ ; cercle pointillé
> « Pour info, accusés et messages antérieurs au suivi n'ouvrent pas de boucle ». Aucune donnée patient.

L'écran a été codé sans référence Stitch, d'après la maquette `maquettes.html` (variante D, section 5) et l'écran
`settings` existant.

#### Passe qualité §Q

Commit `refactor(mail): simplify pass (/simplify) — task-498` : `clockMinute()` partagé (ligne + détail),
catégories du service lues dans `AGING_CATEGORIES`. Comportement inchangé. Specs ciblées 269/269 (`simplify.log`),
lint propre. Écartés : styles carte/section de la légende recopiés de l'écran Paramètres (une extraction
globale toucherait d'autres écrans) ; `calendarDaysAgo` de l'e2e (suite hors de `src`, sans import de l'app).


### Reprise 1

Validation de l'orchestrateur après la reprise :
- **api-mail** `459e5769` (local) : build 0 erreur ; domain 388, infrastructure 749, application 4 397, api 1 398 verts ;
  intégration 1 395 verts + **3 rouges « du jour »** (`FilterTodayEmails…`, `GetFolderTodayAsync…`,
  `GetFolderNotSeenTodayAsync…`) : suite jouée à 00 h 25 heure locale (23 h 25 UTC), piège connu de la fenêtre de minuit
  (corpus en heure locale, Dovecot compare `SINCE` en UTC) — rejoués après 00 h 05 UTC.
- **client-mobile** `1f490eb` (poussé) : build OK, suite complète 2 094 verts.
- **client-angular** (arbre) : `nx build weda2` OK, mss-lib 2 326 verts, weda2 2 684 verts.
- Prévention B5 : `conventions/angular.md`, `spec-qui-lit-une-ligne-de-liste-cible-l-objet` (récidive, corollaire de
  l'horloge injectée).

#### api-mail

##### Reprise 1 (revue anticipée : APPROVED côté api-mail, trois défauts S-A1 à S-A3)

Commits locaux, non poussés, sur `feat/task-498-anneau-anciennete-seuils-de-la-boite` (après `61aadb25`, la fiche d'erreur régénérée par l'orchestrateur) :

| SHA | Message |
|---|---|
| `fc077f80` | test(mailbox): les réglages de la boîte exigent le verdict de l'opérateur (S-A2) |
| `459e5769` | fix(mailbox): seuils d'ancienneté — catégorie absente refusée, écritures simultanées sérialisées (S-A1, S-A3) |

| Défaut | Correctif | Test | Preuve rouge |
|---|---|---|---|
| **S-A1** : une catégorie absente prenait la valeur par défaut, et un PUT partiel remettait les autres catégories aux défauts | Le PUT lit `MailboxAgingThresholdsRequest` (dans le fichier du contrôleur) : même JSON, catégories nullables, sans initialiseur. Une catégorie absente arrive `null` à la règle, qui la refuse : 400 problem+json, `field` = la première catégorie absente, « Les seuils … sont requis. », rien d'écrit. Le contrat dtos-mss ne change pas. | `FolderOperationsEndToEndTests.APartialBody_IsRefusedNamingTheFirstMissingCategory_AndNothingIsWritten` : PUT `{"biologyDays":…,"correspondenceDays":…}` après un réglage → 400, `field` = `criticalBiologyHours`, valeurs relues (GET et base) inchangées | **Code d'avant** : rouge (`r1-red-before.log`, statut 200 au lieu de 400). **Mutation R1** : `ToDto` remplace la catégorie absente par les défauts → rouge |
| **S-A2** : aucun test ne gardait l'absence de `[MailboxNotRequired]` (verdict de l'opérateur, règle 14) | Test d'architecture, sur le modèle de `BuildInfoControllerTests` | `tests/mss.mail.api.tests/Controllers/V1/MailboxDataRoutesRequireTheOperatorVerdictTests.cs` : théorie sur `MailboxAgingThresholdsController` et `MailboxTrackingStartController`, attribut absent du contrôleur et de chaque action publique | **R2a** : attribut posé sur la classe `MailboxAgingThresholdsController` → rouge. **R2b** : attribut posé sur `PUT` de `MailboxTrackingStartController` → rouge |
| **S-A3** : deux premières écritures simultanées violaient la clé `Id=1` (500), et la trace pouvait porter de fausses anciennes valeurs | `IMailboxAgingThresholdsRepository.ReplaceAsync` remplace `SetAsync` et rend les valeurs remplacées. Le tout dans **une transaction** : (1) `INSERT … VALUES (défauts) ON CONFLICT ("Id") DO NOTHING`, (2) `SELECT … FOR UPDATE` des valeurs remplacées, (3) écriture, (4) validation. Le service trace ces valeurs-là. | `FolderOperationsEndToEndTests.TwoFirstWritesAtTheSameTime_BothSucceed_TheLastWins_AndTheirTracesChain` : 8 tours de deux PUT parallèles (titulaire et délégataire). Tours pairs sur une boîte sans ligne, tours impairs sur une ligne existante. Deux 200 ; la dernière valeur gagne ; 16 traces dont les anciennes valeurs s'enchaînent (première = ce qui était en vigueur, seconde = valeur de la première). Unitaire `TheTrace_CarriesTheValuesTheWriteReplaced`. | **Code d'avant** : rouge, 500 réel (`r1-red-before.log`, violation de clé). **R3** (pose de la ligne retirée) : 500, aucune ligne à verrouiller. **R4** (`FOR UPDATE` retiré) : chaîne rompue, les deux écritures lisent la même ancienne valeur `1/2/10`. **R5** (anciennes valeurs relues hors verrou par le service) : rouge en unitaire et en intégration |

Notes :
- **Pourquoi `ON CONFLICT DO NOTHING` + `FOR UPDATE` plutôt qu'un seul `INSERT … ON CONFLICT DO UPDATE`** : sur une boîte sans ligne, un `FOR UPDATE` ne verrouille rien. Les deux écritures liraient « aucune ligne » et traceraient toutes deux les défauts en anciennes valeurs : la chaîne serait rompue. Poser d'abord la ligne aux défauts fait attendre la seconde sur la clé jusqu'à la validation de la première. Elle relit ensuite les valeurs écrites. L'écriture finale est un `UPDATE` sur la ligne verrouillée. La ligne par défaut n'est jamais visible seule, puisqu'elle reste dans la même transaction.
- **Stabilité du test de concurrence** : 3 passages consécutifs verts sur le code corrigé. Sur le code d'avant et sous R4, il a rougi au premier essai : TestServer fait bien se chevaucher deux requêtes en `Task.WhenAll`, et les 8 tours multiplient les occasions.
- **Catalogue d'erreurs** : la cause et l'action de `MAILBOX_AGING_THRESHOLDS_INVALID` couvrent désormais les seuils incomplets. `docs/codes-erreur.md` est régénéré (`MSS_WRITE_ERROR_CATALOG_DOC=1 … ErrorCatalogDocumentTests`) et commité avec le changement.
- **Mutations restaurées depuis une copie, mtime rafraîchi** (script `mutate.py`, ids R1 à R5). Toutes ont compilé et rougi sur une assertion, ou sur le 500 visé pour R3.
- **Tests verts après la reprise** : application 37/37 (seuils, catalogue d'erreurs) ; api.tests 38/38, puis 3/3 (catalogue, document d'erreurs, architecture) ; intégration 12/12 (les 9 tests de la task, plus 3 de migration). Build : 0 erreur, 0 avertissement. Pas de suite complète.
- **Contrôles mécaniques 2b** sur le diff de la reprise : rien.
- **`contract_impact.py check`** : api-mcp et client-mobile sans impact. client-angular reste en IMPACT sur `AuditActionType`, décodé par rang : c'est le miroir `audit.model.ts`, côté agent weda2.

#### client-angular (weda2)

##### Reprise 1 (revue anticipée, passage 1 — CHANGES REQUESTED)

##### Fichiers TFS ajoutés par la reprise (5 ; total : 46, dont 31 modifiés et 15 créés)

| Fichier | Raison |
|---|---|
| `front/apps/weda2/src/app/app.config.ts` | S-W4 : `RingSettingsService` inscrit dans `MSS_RESETTABLE_STORES`, donc purgé à la bascule de boîte. |
| `front/apps/weda2/src/app/app.config.spec.ts` | S-W4 : test de l'inscription (vu rouge). |
| `front/libs/mss/src/core/index.ts` | S-W4 : `RingSettingsService` exporté par `@weda/mss` (nécessaire à `app.config.ts`). |
| `front/libs/mss/src/features/mail/components/mail-ring-panel/mail-ring-panel.component.spec.ts` | B5 : horloge figée (`MSS_CLOCK`) le soir de l'arrivée du jeu. |
| `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.ring.spec.ts` | B5 : même horloge figée. |

Fichiers déjà listés et retouchés : `ring-settings.service(.spec).ts`, `mail-aging.util(.spec).ts`, `mss-settings.component.{ts,html,scss}`, `mss-settings.ring.spec.ts`, `mail-header.component.{ts,html}`, `mail-header.aging.spec.ts`, `ring-legend.component.{html,spec.ts}`, `functional.e2e.ts`.

##### Correctif → test → preuve rouge

| Constat | Correctif | Test | Preuve rouge |
|---|---|---|---|
| **B3** | Les brouillons des seuils ne prennent une valeur lue ou relue que si la saisie est encore intacte : égale aux seuils en vigueur d'avant, ou aux seuils envoyés (`linkedSignal` à source et valeur précédente, `sameAgingThresholds`). Après succès, les refus sont recalculés sur la saisie gardée. | `mss-settings.ring.spec.ts` : « une saisie faite pendant l'enregistrement n'est pas écrasée… », « une relecture qui arrive après une saisie ne l'écrase pas ; sans saisie, elle s'applique », « sans saisie pendant l'aller-retour, les valeurs relues remplacent celles envoyées » | Écrits avant le code, rouges (`'7'` au lieu de `'9'`, `'4'` au lieu de `'2'`). Mutations R1 (toujours la valeur du serveur) : 2 rouges ; R2 (clause « seuils envoyés » retirée) : 1 rouge. |
| **B4** | Le service expose `thresholdsStatus` (`unread` / `read` / `failed`). Sans lecture réussie : champs désactivés, aucun enregistrement (garde à la saisie et filtre avant l'envoi), « Les seuils de la boîte n'ont pas pu être lus. » et un bouton « Réessayer » (`settings-aging-retry`). En échec de relecture, la dernière valeur lue de la boîte est gardée. | `mss-settings.ring.spec.ts` « B4 — seuils non lus… » ; `ring-settings.service.spec.ts` (état non lu / lu / en échec, valeur gardée) | Rouges avant le code. R3 (`thresholdsReady` toujours vrai) : 1 rouge ; R11 (état « en échec » jamais posé) : 2 rouges. |
| **B5** | `MSS_CLOCK` figé dans `mail-ring-panel.component.spec.ts` et `mail-detail.ring.spec.ts`. **Recherche** : horloge par défaut forcée au 2026-12-15, puis au 2028-06-01, sur les 198 fichiers de specs de `src/features`, `src/ui` et `src/core` (qui rendent la ligne, le bloc du détail, le détail et la légende). Seuls ces deux fichiers tombent ; la légende utilise un « maintenant » d'exemple fixe. | — | Mutation B5-horloge-2026-12-15 : 2 rouges (« Courrier, en retard. » au lieu de « Courrier. »). B5-horloge-2028 : les mêmes 2 rouges, aucun autre. Après correctif : B5-apres-correctif-2028, 3 fichiers et 30 tests verts. |
| **B6** | E2E-RING-004 : le courrier reste aux défauts (le scénario l'exige). La biologie (2, 4, 9) et la biologie critique (6, 30, 80) sont posées à des valeurs distinctes, que les champs doivent citer. La relecture finale vérifie que les autres catégories sont inchangées. E2E-SETTINGS-006 : seuils distincts posés par l'API (courrier 4, 9, 20 ; critique 6, 30, 80) ; la légende cite « Courrier : 4 j, 9 j, en retard à 20 j. » et « Biologie critique : 6 h, 30 h, en retard à 80 h. », avec les pastilles J+4, J+20 et H+6 ; les champs citent 4, 20 et 6. Les défauts sont remis dans le `finally`. | — | **Non joués** (banc partagé). `tsc` e2e : 0. ESLint : 0 erreur. **Mutation proposée à /e2e** : `ring-legend.component.ts`, `thresholdLines` lit `DEFAULT_AGING_THRESHOLDS` au lieu de `this.thresholds()` → SETTINGS-006 rouge sur le texte de la légende ; pour les champs, `thresholdDrafts` sur `DEFAULT_AGING_THRESHOLDS` → RING-004 et SETTINGS-006 rouges. |
| **S-W1** | `saveThresholds` rend une issue `{ thresholds, reread }`. PUT réussi mais relecture en échec : les valeurs envoyées entrent en vigueur, et l'écran dit « Les seuils sont enregistrés, mais n'ont pas pu être relus. » (`settings-aging-reread-error`), jamais « non enregistrés ». | service et settings (« S-W1 — enregistré mais non relu… ») | Rouges avant le code. R9 (relecture en échec propagée) : 1 rouge ; R4 (issue ignorée par l'écran) : 1 rouge. |
| **S-W2** | Nouveau getter `showsAssigneeChip` : en mode sélection, la pastille d'initiales suit la préférence « Affectation » ; en icône classique elle reste (arbitrage A1, recommandation retenue). Utilisé par le gabarit et `collapsesTypeLine`. | `mail-header.aging.spec.ts` : « en mode sélection… », « en icône classique… (arbitrage A1) » | Rouge avant le code (pastille présente). R5 (préférence ignorée) : 1 rouge ; R6 (icône classique masquée aussi) : 1 rouge. |
| **S-W3** | Aucun changement de code (`Math.round` était déjà en place). | `mail-aging.util.spec.ts` : « à travers le passage à l'heure d'été, deux jours restent J+2 » (2026-03-28 10 h → 2026-03-30 10 h) | R7 (`Math.floor`) : 1 rouge, sur un poste à Paris (heure d'été ; consigne `fuseau-fige-sous-vmthreads`). |
| **S-W4** | `RingSettingsService.reset()` : seuils par défaut et non lus, préférences par défaut (les réglages de la personne vivent dans la base de la boîte), lecture en vol ignorée. Le service est inscrit dans `MSS_RESETTABLE_STORES` et exporté par `@weda/mss`. | service (« reset() à la bascule… ») ; `app.config.spec.ts` (« RingSettingsService est inscrit… ») | `app.config.spec.ts` rouge avant l'inscription (`[{}, {}]`). R10 (`reset` laisse passer la lecture en vol) : 1 rouge. |
| **S-W5** | Légende : `track chip.text` devient `track $index`. | — | Pas de test : deux mentions de même texte ne peuvent pas se produire aujourd'hui. Changement défensif. |
| **S-L1** | Déjà en place : les pastilles d'exemple de weda2 sont tirées des seuils en vigueur (1er et dernier seuil du courrier, 1er seuil de la biologie critique). Le test les lie maintenant aussi à la biologie critique modifiée. | `ring-legend.component.spec.ts` : « suit les seuils modifiés… : texte et pastilles » (attend J+2, J+8, H+6) | R8 (pastilles calculées sur les seuils par défaut) : 1 rouge. |

##### Vérifications

- **Vitest**, specs ciblés (`src/core`, `src/ui/mail-ring`, mail-header, mail-ring-panel, mail-detail, mail-list, `mss-mail*`, settings, audit, layout) : 113 fichiers, 1 300 tests verts. `apps/weda2` `app.config.spec.ts` : 6/6.
- **ESLint**, fichiers touchés : 0 erreur. Les avertissements restants sont antérieurs : `max-lines`, et `require-example` de `loadMailServer`.
- **Stylelint** des Paramètres : 0.
- **Prettier** : seules les lignes ajoutées sont formatées. `app.config.spec.ts` garde deux lignes non formatées antérieures (`userActivity`, lignes 142 et 155), hors task.
- **e2e** : `tsc -p e2e/mss-e2e/tsconfig.json` sort à 0 ; ESLint : 0 erreur.

##### Hors de mon périmètre, noté

- S-M2 est relevé pour le mobile, mais weda2 a la même forme : si les seuils ne sont pas lus, la légende cite les seuils par défaut comme ceux de la boîte. Le bloc « Boîte aux lettres » dit bien l'échec de lecture ; la légende, elle, ne le dit pas. Non corrigé, car ce n'est pas dans la liste de la reprise. À trancher par la revue.

##### Fichiers à commiter sur TFS (état réel de l'arbre, `git status -uall`, après la reprise 1) — 31 modifiés, 15 créés

Modifiés :
- `front/apps/weda2/src/app/app.config.spec.ts`
- `front/apps/weda2/src/app/app.config.ts`
- `front/e2e/mss-e2e/specs/functional.e2e.ts`
- `front/e2e/mss-e2e/support/e2e-backend.ts`
- `front/libs/mss/src/core/index.ts`
- `front/libs/mss/src/core/models/audit.model.spec.ts`
- `front/libs/mss/src/core/models/audit.model.ts`
- `front/libs/mss/src/core/models/user-settings.model.ts`
- `front/libs/mss/src/core/services/mss-api.service.ts`
- `front/libs/mss/src/core/utils/mail-ring-row.util.spec.ts`
- `front/libs/mss/src/core/utils/mail-ring-row.util.ts`
- `front/libs/mss/src/core/utils/mail-ring.util.spec.ts`
- `front/libs/mss/src/core/utils/mail-ring.util.ts`
- `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.ring.spec.ts`
- `front/libs/mss/src/features/mail/components/mail-header/mail-header.component.html`
- `front/libs/mss/src/features/mail/components/mail-header/mail-header.component.scss`
- `front/libs/mss/src/features/mail/components/mail-header/mail-header.component.ts`
- `front/libs/mss/src/features/mail/components/mail-header/mail-header.light-row.spec.ts`
- `front/libs/mss/src/features/mail/components/mail-header/mail-header.ring.spec.ts`
- `front/libs/mss/src/features/mail/components/mail-ring-panel/mail-ring-panel.component.html`
- `front/libs/mss/src/features/mail/components/mail-ring-panel/mail-ring-panel.component.scss`
- `front/libs/mss/src/features/mail/components/mail-ring-panel/mail-ring-panel.component.spec.ts`
- `front/libs/mss/src/features/mail/components/mail-ring-panel/mail-ring-panel.component.ts`
- `front/libs/mss/src/features/mail/mss-mail.component.ts`
- `front/libs/mss/src/features/settings/mss-settings.component.html`
- `front/libs/mss/src/features/settings/mss-settings.component.scss`
- `front/libs/mss/src/features/settings/mss-settings.component.ts`
- `front/libs/mss/src/ui/mail-ring/mail-ring.component.html`
- `front/libs/mss/src/ui/mail-ring/mail-ring.component.scss`
- `front/libs/mss/src/ui/mail-ring/mail-ring.component.spec.ts`
- `front/libs/mss/src/ui/mail-ring/mail-ring.component.ts`

Créés :
- `front/libs/mss/src/core/services/mss-api.aging-thresholds.service.spec.ts`
- `front/libs/mss/src/core/services/ring-settings.service.spec.ts`
- `front/libs/mss/src/core/services/ring-settings.service.ts`
- `front/libs/mss/src/core/tokens/mss-clock.token.ts`
- `front/libs/mss/src/core/utils/mail-aging.util.spec.ts`
- `front/libs/mss/src/core/utils/mail-aging.util.ts`
- `front/libs/mss/src/core/utils/mail-ring-display.util.ts`
- `front/libs/mss/src/features/mail/components/mail-header/mail-header.aging.spec.ts`
- `front/libs/mss/src/features/mail/components/mail-ring-panel/mail-ring-panel.aging.spec.ts`
- `front/libs/mss/src/features/mail/mss-mail.component.ring-settings.spec.ts`
- `front/libs/mss/src/features/settings/mss-settings.ring.spec.ts`
- `front/libs/mss/src/features/settings/ring-legend/ring-legend.component.html`
- `front/libs/mss/src/features/settings/ring-legend/ring-legend.component.scss`
- `front/libs/mss/src/features/settings/ring-legend/ring-legend.component.spec.ts`
- `front/libs/mss/src/features/settings/ring-legend/ring-legend.component.ts`

#### client-mobile

##### Reprise 1 (revue anticipée, CHANGES REQUESTED)

Commits : `6122e22` fix(settings) (B1, S-M1 à S-M4, S-L1, S-W3), `1f490eb` test(mobile) (B2). Non poussés.

Preuves : specs écrits avant le correctif. D'abord rouges à la compilation (`r1-red.log` : `routes` non exporté,
`ensureLoaded` inexistant). Puis `routes` exporté et `ensureLoaded` posé vide, sans comportement : 12 rouges à
l'exécution (`r1-red2.log`). Après le correctif, vert 95/95 (`r1-green.log`). Quatre tests passaient déjà sur le
code d'avant ; ils ont été prouvés par mutation (`r1-mut.log`, 4 FAILED, restauré). Passe ciblée finale **1098/1098**
(`r1-final.log`). Lint des fichiers touchés : 0. `tsc` e2e : 0 (`r1-e2e-tsc.log`).

| Constat | Correctif | Test | Preuve rouge |
|---|---|---|---|
| B1 — échec de lecture figé pour la session | `ensureLoaded()` (lit si non lus), appelé à l'entrée des Paramètres (`ionViewWillEnter`) et de la légende | service « échec puis entrée → relu » ; Paramètres « l'entrée demande la lecture » ; légende « la page demande la lecture » | `r1-red2.log` (3 rouges) |
| B1 — relecture en échec efface les valeurs connues | `load()` ne pose que ce qu'il a lu ; `save()` pose la réponse du PUT avant de relire | « relecture en échec garde la dernière valeur » ; « PUT accepté puis relecture en échec : valeur du PUT gardée » | `r1-red2.log` (2 rouges) |
| B1 — pas de relecture inutile | `ensureLoaded` ne relit pas des seuils lus | « déjà lus ne sont pas relus » | mutation (garde `!loaded()` retirée) → rouge |
| S-M1 — bascules actives avant la lecture | `[disabled]="!settingsLoaded()"` | « bascules inactives tant que les réglages ne sont pas lus » | `r1-red2.log` |
| S-M1 — route sans gardes | `canActivate: [authGuard, mailboxGuard]` (comme `pending-emails`, `conversation`) | `app-routing.module.spec.ts` | `r1-red2.log` |
| S-M2 — défauts cités comme ceux de la boîte | mention `ring-legend-thresholds-unread` | « seuils non lus : la légende le dit » | `r1-red2.log` + mutation (`@if (false)`) → rouge |
| S-M3 — champ vidé réaffiche 0 | saisie brute `agingInput` (texte), convertie par `agingDraft` (vide = NaN, refusé) | « un champ vidé reste vide, et la validation le refuse » | `r1-red2.log` |
| S-M4 — test non discriminant | le serveur simulé relit 21 pour une saisie de 20 | « les champs reprennent les seuils relus » | mutation `linkedSignal` → `signal` pris une fois → rouge |
| S-W3 — changement d'heure | (code déjà juste, `Math.round`) | « 28/03 10 h → 30/03 10 h = J+2 » | mutation `Math.round` → `Math.floor` → rouge (poste en Europe/Paris) |
| S-L1 — pastilles d'exemple figées | `agingSamples()` : calcul réel (`mailRingAging`) au 1er et au dernier seuil du courrier, au 1er seuil critique, horloge `CLOCK` | « aux défauts : J+3, J+14, H+4 » ; « courrier 4/9/20, critique 6/30/80 : J+4, J+20, H+6 » ; « 1er seuil critique 96 h : J+4 » | `r1-red2.log` (3 rouges) |
| B2 — e2e vert qui ment | SETTINGS-006 : seuils distincts posés par l'API (critique 6/30/80, biologie 2/4/9, courrier 4/9/20) avant les Paramètres et la légende ; les 9 champs, la phrase et les pastilles (J+4, J+20, H+6) sont affirmés ; défauts remis dans le `finally`. RING-004 : champs relus 2/5/8 après rechargement | e2e non joués (banc partagé) | **mutation à jouer à `/e2e`** : dans `treatment-ring-legend.page.html`, remplacer `{{ thresholdsSummary() }}` par la phrase des défauts → SETTINGS-006 rouge (« la légende cite les seuils de la boîte ») |

Horloge figée partout où une spec rend la ligne, le détail ou la légende avec une date fixe : `mail-detail.ring.spec.ts`,
`mail-header.aging.spec.ts` et `treatment-ring-legend.page.spec.ts` l'étaient ou le sont maintenant ;
`mail-list.component.spec.ts` (envois de 2026-01 et 2026-03) a désormais `CLOCK` figé. Recherche faite sur toutes les
specs qui rendent `MailHeaderComponent`, `MailListComponent`, `MailDetailComponent` ou la page de légende avec une date
littérale : il n'en reste aucune sans horloge figée.

Non fait, et pourquoi :
- **Relecture au retour en ligne** : `MailboxSessionService` expose `offline()`, mais beaucoup de specs le remplacent
  par des doubles sans ce signal (`{ currentEmail }`). Un effet de plus dans le service racine les ferait tomber sans
  qu'on le voie en specs ciblées. La relecture à l'entrée des deux écrans suffit pour B1.
- **B4 (weda2)** : déjà vrai sur mobile. Sans lecture réussie, aucun champ n'est proposé (`settings-aging-unavailable`),
  donc aucun PUT n'est possible.

## Code Review Summary

### Passage 1 (revue anticipée) — CHANGES REQUESTED

Trois relecteurs indépendants (api-mail + dtos, weda2, mobile), code seul. Contrôles préalables :
- `contract_impact.py check` : api-mcp aucun impact ; client-mobile aucun impact ; client-angular IMPACT
  (`AuditActionType` décodé par rang) → **adapté** (`audit.model.ts` valeur 77 + libellé, spec vu rouge).
- Catalogue : `E2E-RING-004` v1 et `E2E-SETTINGS-006` v1 (`mobile: requis`, `angular: requis`), implémentés en v1 dans
  les deux clients.
- Règle 1b (api-mail) : 11 comportements prouvés par des tests d'intégration sur la vraie pile, preuves rouges par
  mutation crédibles (M1-M19) ; seul trou : le verdict opérateur de la route n'a pas de test propre (S-A2 ci-dessous).

#### À corriger par la reprise

Bloquants :
- **B1 (mobile)** — une lecture des seuils en échec fige les défauts pour la session (`mailbox-aging-thresholds.service.ts`
  ne relit qu'au changement de boîte, l'écran promet « Revenez dans un instant ») ; et une relecture en échec après un PUT
  réussi efface les valeurs connues. Relire à l'entrée des Paramètres et de la légende si non lus ; garder la dernière
  valeur connue (ou celle du PUT) quand la relecture échoue. Test « échec puis entrée → relu ».
- **B2 (mobile) / B6 (weda2)** — E2E-SETTINGS-006 compare la légende aux seuils par défaut qu'il vient de poser : vert
  qui ment (`assertion-sans-cas-declencheur`). Poser par l'API des seuils distincts des défauts avant d'ouvrir la légende
  et les Paramètres, et affirmer que la légende **et** les champs les citent (même faiblesse sur les champs de RING-004,
  `toHaveValue('3')`). Mutation à consigner : légende sur les défauts en dur → rouge.
- **B3 (weda2)** — la relecture après PUT (et la lecture initiale) remet toute la saisie aux valeurs du serveur : une
  modification faite pendant l'aller-retour est écrasée en silence (`reponse-sur-instantane`). N'appliquer la relecture
  que si la saisie est encore celle envoyée ; test « saisie pendant l'enregistrement », rouge sur le code actuel.
- **B4 (weda2)** — une lecture des seuils en échec pose les défauts, affichés et modifiables comme ceux de la boîte : le
  PUT des trois catégories écrase les réglages d'un collègue (donnée partagée, règle 14, trace au nom de quelqu'un qui ne
  l'a pas voulu). Sans lecture réussie : aucun PUT, champs désactivés, « Les seuils de la boîte n'ont pas pu être lus » et
  « Réessayer ». Test.
- **B5 (weda2)** — `mail-ring-panel.component.spec.ts` et `mail-detail.ring.spec.ts` (fixture `arrivalDate`
  2026-11-26) montent un composant qui injecte `MSS_CLOCK` sans la figer : rouges à partir du 2026-12-10 (passage en
  retard). Figer l'horloge ; chercher tout autre spec qui rend `mss-mail-header` / `mss-mail-ring-panel` avec une date
  fixe. Prévention : consigne `conventions/angular.md`.

Défauts réels corrigés dans la même passe :
- **S-A1 (api-mail)** — une catégorie **absente** du corps prend la valeur par défaut du DTO : un PUT partiel remet en
  silence les autres catégories aux défauts, tracé comme voulu. Refuser une catégorie absente comme une catégorie `null`
  (400, `field`), test d'intégration vu rouge. Contrat § 2 mis à jour.
- **S-A2 (api-mail)** — test d'architecture : `MailboxAgingThresholdsController` (et `MailboxTrackingStartController`)
  ne portent pas `[MailboxNotRequired]` (le verdict opérateur, règle 14, est alors exigé par le middleware). Vu rouge.
- **S-A3 (api-mail)** — deux premières écritures simultanées violent la clé `Id=1` (500) et la trace peut porter de
  fausses anciennes valeurs : écriture en `INSERT … ON CONFLICT DO UPDATE`, lecture des anciennes valeurs verrouillée dans
  la même transaction.
- **S-W1 (weda2)** — PUT réussi mais relecture en échec : l'écran dit « non enregistrés ». Distinguer les deux échecs.
- **S-W2 (weda2)** — en mode sélection, la pastille d'initiales revient même si « Affectation » est masquée : appliquer la
  préférence.
- **S-W3 (weda2)** — aucun test de changement d'heure (`Math.round` → `Math.floor` survit) : ajouter le cas
  2026-03-28 10 h → 2026-03-30 10 h = J+2 (consigne `fuseau-fige-sous-vmthreads`). Même cas côté mobile.
- **S-W4 (weda2)** — `RingSettingsService` (état de boîte) absent de `MSS_RESETTABLE_STORES` : les seuils de la boîte A
  s'appliquent à la boîte B jusqu'à la relecture. `reset()` + inscription.
- **S-W5 (weda2)** — légende `track chip.text` → `track $index` (clé dupliquée possible).
- **S-M1 (mobile)** — bascules de la légende actives avant la lecture des réglages (appui perdu en silence) et route
  `/treatment-ring-legend` sans `authGuard` / `mailboxGuard` : conditionner aux réglages chargés, gardes comme les routes
  voisines.
- **S-M2 (mobile)** — la légende cite les défauts comme seuils de la boîte quand ils ne sont pas lus : le dire.
- **S-M3 (mobile)** — un champ de seuil vidé réaffiche « 0 » pendant la saisie : garder la saisie brute, convertir à la
  validation.
- **S-M4 (mobile)** — test « les champs reprennent les seuils relus » non discriminant : le serveur simulé doit rendre
  une valeur différente de la saisie.
- **S-L1 (les deux clients)** — les pastilles d'exemple de la légende (« J+4 », « J+15 ») sont fixes et peuvent contredire
  des seuils modifiés : les dériver des seuils en vigueur de la boîte.

#### Arbitrage humain

- **A1** — en **icône classique**, la préférence « Affectation » doit-elle aussi masquer la pastille d'initiales de la
  ligne (et « Attente » ses mentions) ? La US parle des préférences de l'anneau. Recommandation : non — la personne qui
  choisit l'icône classique garde les mentions écrites de la ligne.

Notes sans suite : réglages d'affichage rangés par personne dans la base de la boîte, comme tous les réglages de la
personne (N6 mobile) ; client-blazor non bumpé, un enregistrement depuis Blazor remettrait `RingDisplay` aux défauts
(hors task, N2 api) ; refus d'un seuil non entier par la liaison ASP.NET, sans `field` (N1 api) ; horloge non réactive à
minuit (calcul à l'affichage, S5 weda2) ; « Ouvert depuis » dans l'`<ol>` des étapes (forme existante, N3 weda2).

### Passage 2 (revue anticipée, après la reprise 1) — APPROVED

Relecteurs du passage 1, diff de la reprise lu en premier (ce qu'il a cassé), puis chaque constat vérifié.
- **api-mail** : APPROVED — corps local `MailboxAgingThresholdsRequest` sans effet sur les clients ni api-mcp ; transaction
  `INSERT … ON CONFLICT DO NOTHING` + `FOR UPDATE` sans interblocage, annulée proprement ; test de concurrence
  déterministe (3 verts) et rouge sur l'ancien code ; S-A1 (rouge : 200 au lieu de 400, critique écrasée), S-A2 (R2a, R2b),
  S-A3 (500 `23505`, R3, R4, R5) corrigés.
- **client-mobile** : APPROVED — `ensureLoaded()` sans fuite entre boîtes, valeur gardée sur échec, gardes de route,
  saisie brute, pastilles calculées ; B1, B2, S-M1 à S-M4, S-W3, S-L1 corrigés (rouges et mutations consignés).
- **client-angular** : code APPROVED (aucune régression ; B3 à B6, S-W1 à S-W6, S-L1 corrigés, mutations R1 à R12). Un
  bloquant de **traçabilité** du plan de contrôle : la sous-section weda2 de la « Reprise 1 » ne portait pas la table
  correctif → test → preuve, et la liste TFS omettait 5 fichiers (`app.config.ts`, `app.config.spec.ts`, `core/index.ts`,
  specs `mail-ring-panel` et `mail-detail.ring`). **Corrigé par l'orchestrateur** (recopie du journal de reprise, liste
  TFS régénérée depuis `git status -uall` : 31 modifiés, 15 créés), sans changement de code.
- `contract_impact.py check` : api-mcp aucun impact ; client-mobile aucun impact ; client-angular IMPACT adapté (77).

**Approved at** : api-mail `459e5769` ; dtos-mss `158d4e46` ; client-mobile `1f490eb` ; client-angular arbre de
`feature/nova-mss-weda-integration` (base `3f6e9119`, 46 fichiers listés).

Suggestions sans suite (non bloquantes, pour une task ultérieure ou le merge) :
- api-mail : test par réflexion « `MailboxAgingThresholdsRequest` = propriétés de `MailboxAgingThresholdsDto` » (une
  catégorie ajoutée au contrat sans la requête serait remise aux défauts) ; nom de table en dur dans deux requêtes SQL.
- weda2 : la légende dit « non lus » quand une **relecture** échoue après une lecture réussie (les vraies valeurs sont
  affichées), et la mention clignote pendant le chargement ; une saisie jetée par un échec de lecture n'est pas renvoyée
  après « Réessayer » (fenêtre de 300 ms).
- mobile : bascules de la légende grisées sans explication si les réglages n'ont pas pu être lus ; champs de seuils
  modifiables pendant l'enregistrement (`reponse-sur-instantane`).

## Sonar log

Analysé à api-mail `459e5769` (2026-11-28, SonarQube 9.9.8, projet `healthplatform-api-mail`, période de nouveau code :
30 jours depuis le 2026-10-29). Une analyse complète : begin → build Release → cinq suites avec couverture OpenCover → end.

- Phase 1 (new code) : ✓ Quality Gate OK, new_coverage = 96,1 % (lignes 98,4 %, branches 90,7 %)
- Phase 1 — Issues : 1 code smell `csharpsquid:S3925` sur `MailboxAgingThresholdsInvalidException` (l. 10). Triplet de
  constructeurs présent d'emblée ; la règle réclame ensuite le constructeur de sérialisation `ISerializable`, obsolète
  sur .NET 8+ (SYSLIB0051) : **FALSE-POSITIVE** avec ce motif, comme les exceptions voisines (`conventions/csharp.md`,
  S3925, occurrence 11). 0 bug, 0 vulnérabilité, 0 hotspot.
- Phase 1 — Tests ajoutés : 0 (cible de couverture du nouveau code atteinte)
- Phase 2 (legacy) : itérations 0 / 5 — non jouée : toutes les cibles projet sont tenues (0 bug, 0 vulnérabilité,
  maintenabilité A, couverture 97,5 % ≥ 95 %)
- Aucun commit : HEAD inchangé (`459e5769`)
- Build / tests (Release, couverture) : domain 388, application 4 397, infrastructure 749, api 1 398, integration 1 395
  (+ 16 ignorés) ; **3 rouges « du jour »** (`FilterTodayEmails…`, `GetFolderTodayAsync…`, `GetFolderNotSeenTodayAsync…`)
  : suite jouée entre 00 h 30 et 00 h 45 heure locale (avant minuit UTC), piège connu de la fenêtre de minuit (corpus en
  heure locale, Dovecot compare `SINCE` en UTC) ; rejoués après 00 h 05 UTC.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 96,1 % | 96,1 % | 0 pt |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 0 | 0 (1 faux positif S3925 marqué) | 0 |
| Coverage (projet) | 97,6 % | 97,5 % | −0,1 pt |
| Duplication | 0,3 % | 0,3 % | 0 pt |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

## Lint log

- `npx nx affected -t lint --base=origin/next --head=HEAD --parallel=3 --projects=tag:scope:mss` (arbre de
  `feature/nova-mss-weda-integration`) : **0 erreur**, 13 cibles réussies. Aucune itération de correction, aucun fichier
  modifié ; le vert de `/develop` (reprise 1 : `nx build weda2`, mss-lib 2 326, weda2 2 684) tient.

## Lint mobile log

- `npm run lint` sur `feat/task-498-anneau-anciennete-seuils-de-la-boite` (`1f490eb`) : **All files pass linting**.
  Aucune itération, aucun commit ; le vert de `/develop` (reprise 1 : build OK, 2 094 verts) tient.

## E2E log

| Voie | Commit / arbre | Résultat |
|---|---|---|
| mobile | client-mobile `1f490eb`, api-mail `459e5769` | **rouge** — E2E-RING-004 rouge (deux essais) ; E2E-SETTINGS-006 vert au second essai |
| angular | weda2 (arbre, base `3f6e9119`), api-mail `459e5769` | vert — 110 verts, 0 flaky, 0 rouge, parité verte |

**Cause (diagnostic de l'orchestrateur)** : la voie mobile a tourné vers 23 h 50 UTC (00 h 50 heure locale). api-mail
stocke `ArrivalDate` / `SentDate` en `timestamp without time zone` (UTC, `DateTimeKind.Unspecified`) et les sert **sans
`Z`** ; le calcul d'ancienneté des deux clients (`readDate` / `agingReference`) et le helper e2e `calendarDaysAgo` lisent
ces chaînes comme des heures **locales**. Un courrier arrivé il y a 8 jours exactement est alors compté J+9 entre minuit
local et minuit UTC, et le compteur « H+N » de la biologie critique est faux d'une heure (deux en été) **à toute heure**.
La voie Angular a tourné après minuit UTC : verte, mais le défaut y est le même.

**E2E : ROUGE** — 1 motif(s) de blocage.

**Bloquant** (1) :

- [mobile] rouge : « anneau — une boucle ouverte porte son ancienneté « J+N », en fond plein et « en retard » au dernier seuil de la boîte » (E2E-RING-004)

**Flaky (vert au second essai, non bloquant)** (1) :

- [mobile] « réglages — la légende des anneaux cite les seuils de la boîte ; masquer l’ancienneté est retenu pour la personne » (E2E-SETTINGS-006)

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
| E2E-BIO-001 | 3 | headless | Acquitter un compte rendu de biologie, à son nom | ✅ | ✅ |
| E2E-BIO-002 | 1 | headless | La puce « Bio à acquitter » montre tous les résultats en attente, sur toutes les pages | ✅ | ✅ |
| E2E-BIO-003 | 2 | headless | Lire un résultat HPRIM puis l'acquitter | ✅ | ✅ |
| E2E-BIO-004 | 1 | headless | Un compte rendu acquitté puis déplacé depuis un autre client garde son acquittement | ✅ | ✅ |
| E2E-BIO-007 | 2 | headless | Un compte rendu arrivé avant la date de début du suivi ne réclame rien, et s'acquitte quand même | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 2 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
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
| E2E-SEARCH-015 | 1 | headless | Le détail surligne ce qui a été cherché | ✅ | — |
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
| E2E-SHARED-004 | 1 | headless | Dans la conversation, un message écrit par un délégataire pour le compte de son expéditeur le dit | ✅ | ✅ |
| E2E-SHARED-005 | 1 | headless | Dans la fiche patient, l'aperçu d'un message écrit par un délégataire le dit sous « De » | ✅ | — |
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
| E2E-TAG-004 | 1 | headless | Une combinaison de tags où rien n'est à traiter s'ouvre sur « Tous », le réglage reste « À traiter » | ✅ | ✅ |
| E2E-TRIAGE-001 | 2 | headless | Traiter un message le retire de « À traiter », le compteur baisse, « Annuler » le remet | ✅ | ✅ |
| E2E-TRIAGE-002 | 1 | headless | Traiter les messages affichés laisse le compte rendu de biologie à acquitter | ✅ | ✅ |
| E2E-TRIAGE-006 | 1 | headless | Dans la vue « Biologie », « Traiter les résultats sans anomalie » laisse le résultat anormal à traiter | ✅ | ✅ |
| E2E-TRIAGE-007 | 1 | headless | Répondre à un message le fait sortir de « À traiter », libellé « — répondu » | ✅ | ✅ |
| E2E-TRIAGE-008 | 1 | headless | « Traité » sur un message d'un fil traite aussi ses précédents, jamais le plus récent ; « Annuler » les remet | ✅ | ✅ |
| E2E-SHARED-003 | 1 | headless | Le délégataire traite un message, le titulaire le voit traité « par » le délégataire | ✅ | ✅ |
| E2E-ASSIGN-001 | 3 | headless | Le titulaire attribue un message à la secrétaire délégataire, qui le trouve dans « Pour moi » | ✅ | ✅ |
| E2E-ASSIGN-002 | 1 | headless | Traiter un message attribué le retire de « Pour moi », et le détail dit « traité par » | ✅ | ✅ |
| E2E-ASSIGN-003 | 1 | headless | La puce « Pour moi » porte son compteur, n'apparaît pas à zéro et reste affichée quand on traite le dernier | ✅ | ✅ |
| E2E-CONV-001 | 1 | headless | Lire un fil en vue chat et y répondre en une ligne, à tous les participants | ✅ | ✅ |
| E2E-CONV-002 | 1 | headless | Joindre un fichier depuis la vue chat | ✅ | ✅ |
| E2E-CONV-003 | 1 | headless | La vue chat s'ouvre d'elle-même sur un fil engagé, et n'existe qu'en mode Conversation | ✅ | ✅ |
| E2E-RING-001 | 1 | headless | L'anneau d'un courrier se remplit de « reçu » à « lu » puis se ferme à « traité » | ✅ | ✅ |
| E2E-RING-002 | 1 | headless | L'anneau d'un compte rendu de biologie à acquitter suit ses acquittements, jusqu'à « résolu » | ✅ | ✅ |
| E2E-RING-003 | 2 | headless | En boîte partagée, « Non affecté » puis les initiales de la personne attribuée dans l'anneau | ✅ | ✅ |
| E2E-RING-004 | 1 | headless | Une boucle ouverte porte son ancienneté « J+N », en fond plein et « en retard » au dernier seuil de la boîte | ✅ | ❌ |
| E2E-RING-005 | 1 | headless | L'anneau porte le nombre de messages de la conversation et l'icône d'une réponse envoyée | ✅ | ✅ |
| E2E-SETTINGS-005 | 1 | headless | Choisir « Icône classique » pour la liste, le retrouver après rechargement, revenir à l'anneau | ✅ | ✅ |
| E2E-SETTINGS-006 | 1 | headless | La légende des anneaux cite les seuils de la boîte ; masquer l'ancienneté est retenu pour la personne | ✅ | ⚠️ flaky |

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
