# todo-task-402 — Rattachement guidé par l'Annuaire Santé : titulaire, membre ou délégataire

**Repos**: dtos-mss, api-mail, client-mobile, client-angular
**Dependencies**: aucune
**Epic**: E020
**EpicTitle**: Boîte partagée : une base par boîte, tout acte imputé

> **Cadre** : CLAUDE.md règle 14, réécrite le 2026-10-28 (commit `ca0adaf`). Analyse d'origine :
> le nom de base `u_{rpps}_{slug}_{hash(adresse)}` donne au délégataire une **seconde base**, copie
> des données de santé du délégant. L'EPIC E020 passe à « une boîte = une base », l'accès ouvert par
> l'opérateur, tout acte imputé à son auteur réel. Cette task pose la **qualification du rôle** dont
> dépendent le verrou d'accès et le hors-ligne du titulaire (task-403).
>
> Ordre de l'EPIC : 402 (rattachement guidé) → 403 (accès subordonné à l'opérateur) → 404 (une base
> par boîte) → 405 (tout acte imputé) → 406 (mesure de charge d'une boîte partagée).
>
> **Aucune reprise** (humain, 2026-10-28) : rien n'est en production ; le registre et les bases
> praticien de dev sont supprimés au déploiement de l'EPIC. Tout rattachement naît qualifié.

## Ce qui est établi

- **Rattachement** : `POST /api/v1/account/mailboxes` → `MailboxManagementService.AttachAsync`
  (`Api/Mail/src/Application/Services/Mailboxes/MailboxManagementService.cs`). Ordre « sonder, puis
  persister » : sonde IMAP XOAUTH2 avec le jeton PSC, puis `ITenantRegistryClient.AttachMailboxAsync`.
- **Registre** : `mss_accounts` (rattachement compte × messagerie) porte `validated_by_psc_subject`
  et `validated_by_rpps` (NOT NULL), mais **aucun rôle**. Clé unique `(account_id, mailbox_address)` :
  deux comptes peuvent rattacher la même adresse.
- **Annuaire Santé** : api-mail interroge déjà l'API FHIR R4 **par RPPS**
  (`DirectorySearchEngine.cs:63`) et lit les adresses de `Practitioner.telecom` et
  `PractitionerRole.telecom` (`FhirBundleParser.cs:142`), avec une limite de débit
  (`AnnuaireSanteService.RequestsPerSecond`, `RedisAnnuaireQuotaGate`). Il **ne lit pas** le type de
  la BAL (personnelle / organisationnelle / applicative).
- **Clients** : écrans de rattachement `mailbox-onboarding` et `mailbox-management` (mobile, et weda2
  `features/mailbox-onboarding`, `features/mailbox-management`), formulaire partagé
  `attach-mailbox-form.component.ts` côté mobile.
- **Banc e2e** : aucun Annuaire dans le profil e2e. Dovecot accepte toute identité (`passdb static`).
  `E2eSeedPlan` n'a qu'une personne (le praticien e2e, deux boîtes).

## Décisions actées (humain, 2026-10-28)

1. Le rattachement se fait par **deux voies, et deux seulement** :
   - **« Mes boîtes »** : la liste des BAL que l'Annuaire Santé publie pour le RPPS du jeton PSC. Le PS
     **choisit**, il ne saisit pas ;
   - **« Ajouter une BAL déléguée »** : saisie libre, **réservée à la délégation**. Elle n'ouvre jamais
     le rôle de titulaire.
2. Une adresse organisationnelle n'a pas de titulaire : ses PS sont **membres**.
3. Une BAL personnelle en **liste rouge** n'est rattachable qu'en délégation : conséquence assumée.
4. Une boîte **« à requalifier »** garde l'accès en ligne avec les droits d'un délégataire (pas de
   hors-ligne), avec un bandeau « rattachez-la de nouveau depuis Mes boîtes ».

## Objective

Après sa connexion PSC, le PS rattache une messagerie soit en la **choisissant** dans la liste que
l'Annuaire Santé publie pour son RPPS, soit en **saisissant** l'adresse d'une BAL qui lui est
déléguée. Chaque rattachement porte un **rôle** — titulaire, membre ou délégataire — calculé par le
serveur, jamais déclaré par le client. Cette task **ne change aucun accès** : elle pose la
qualification que la task-403 (verrou, hors-ligne du titulaire) et la task-406 (résorption)
utilisent.

## Règles

1. **La liste vient du serveur.** Le RPPS est celui de la **session PSC**, jamais une valeur du client.
   Pour chaque BAL : l'adresse, le type (personnelle ou organisationnelle, lu dans les métadonnées
   MSSanté de l'Annuaire) et l'indicateur « déjà rattachée ». Les BAL **applicatives** ne sont pas
   proposées.
2. **Le rôle est fixé par le serveur, au rattachement.**
   - **« Mes boîtes »** : le serveur **revérifie** que l'adresse est dans la liste du RPPS de la
     session. BAL personnelle → **titulaire** ; BAL organisationnelle → **membre**. Une adresse
     absente de la liste est refusée.
   - **Saisie libre** : une adresse qui figure dans la liste du PS est **refusée** (« choisissez-la
     dans Mes boîtes »). Sinon → **délégataire**.
   - Dans les deux cas : **sonder, puis persister**. Rien n'est écrit sans sonde IMAP réussie avec
     le jeton PSC de la personne.
3. **Annuaire indisponible** : « Mes boîtes » rend une erreur `application/problem+json` 503 et
   l'écran affiche « Annuaire Santé momentanément indisponible, réessayez ». La saisie libre reste
   ouverte, **pour la délégation seulement** — elle ne remplace jamais la liste.
4. **Requalification à chaque ré-authentification** : le rôle est recalculé contre l'Annuaire.
   - Un titulaire ou un membre dont l'adresse n'est plus publiée pour son RPPS passe **« à
     requalifier »**. Il ne devient **jamais délégataire automatiquement**.
   - « À requalifier » : accès en ligne inchangé, droits d'un délégataire (pas de hors-ligne une fois
     la task-403 livrée), bandeau « rattachez-la de nouveau depuis Mes boîtes ».
   - Annuaire injoignable à ce moment : le rôle enregistré est **gardé**.
5. **Aucun rattachement existant à reprendre** : le registre de dev repart vide. Le rôle est
   **obligatoire** sur tout rattachement (contrainte NOT NULL), il n'existe pas d'état « non qualifié ».
6. **Weda désigne une adresse** (E2E-WEDA-001) : présente dans « Mes boîtes » → présélectionnée ;
   sinon → formulaire de délégation pré-rempli.
7. **Liste rouge** : aucun contournement proposé à l'écran (décision 3).
8. **Traces (règle 14)** : `MailboxAttached`, `MailboxAttachRefused` et la requalification portent le
   **rôle**, le **RPPS de la personne qui agit** et le motif de refus. La consultation de l'Annuaire
   n'est pas tracée au journal : elle ne touche aucune donnée de santé.

## Definition of Done

- [ ] Build passes (0 errors) sur `dtos-mss`, `api-mail`, `client-mobile`, `client-angular` (code-only)
- [ ] Tests pass (0 failures) sur chaque repo listé
- [ ] Contrat `dtos-mss` : rôle et type d'adresse sur la boîte rattachée, DTO « BAL proposée », mode
      de rattachement dans la requête — package publié, consommateurs .NET bumpés, types TypeScript
      mobile et Angular régénérés
- [ ] Registre : migration (rôle et type d'adresse sur le rattachement), auditée (règle 7c : fichier
      relu, aucune opération fantôme, aucune dérive)
- [ ] Unit tests du parseur FHIR : type de BAL personnelle, organisationnelle, applicative écartée,
      métadonnée absente
- [ ] Unit tests du calcul de rôle : chaque branche des règles 2 et 4
- [ ] Test d'intégration de bout en bout pour la lecture de « Mes boîtes » : liste du RPPS de la
      session lue dans la réponse réelle (type et « déjà rattachée »), 503 problem+json si l'Annuaire
      est indisponible, refus sans session PSC — vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout pour `POST /account/mailboxes` via « Mes boîtes » : rôle
      `titulaire` lu dans la réponse et dans `GET /account/mailboxes` ; adresse hors liste refusée et
      rien de persisté — vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout : BAL organisationnelle → rôle `membre` lu dans la réponse —
      vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout pour la saisie libre : rôle `délégataire` ; l'adresse de la
      propre liste du PS refusée avec son code, rien de persisté — vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout pour `POST /account/mailboxes/{id}/reauthenticate` : titulaire
      dont l'adresse a quitté l'Annuaire → état « à requalifier » lu dans la réponse ; Annuaire
      injoignable → rôle gardé — vu rouge (règle 1b)
- [ ] Test d'intégration : rôle et RPPS de la personne qui agit lus dans le journal d'audit réel
      (rattachement, refus, requalification) — vu rouge (règle 1b)
- [ ] Mobile et weda2 : écran de rattachement à deux voies, badge de rôle sur chaque boîte, bandeau
      « à requalifier », `data-testid` sur tous les éléments interactifs
- [ ] UI component tests : écran à deux voies (rendu + choix dans la liste + saisie libre refusée),
      badge de rôle
- [ ] **Banc e2e** : un Annuaire FHIR simulé dans le profil e2e publie, pour le RPPS e2e,
      `boite-praticien` (personnelle) et `boite-secondaire` (organisationnelle) ; une seconde
      identité PSC « délégataire e2e » est au seed ; `E2eSeed` enregistre les rôles
- [ ] Scénario E2E-MAILBOX-003 (v1, rattachement via « Mes boîtes », badges titulaire et membre)
      ajouté dans Api/Mail/e2e/scenarios.yml, et implémenté dans chaque client où il est requis
      (mobile, angular)
- [ ] Scénario E2E-MAILBOX-004 (v1, délégation par saisie libre, refus de sa propre adresse) ajouté
      dans Api/Mail/e2e/scenarios.yml, et implémenté dans chaque client où il est requis (mobile,
      angular)
- [ ] Scénario E2E-WEDA-001 versionné (v2 : adresse désignée par Weda présélectionnée ou pré-remplie)
      dans Api/Mail/e2e/scenarios.yml, et implémenté dans chaque client où il est requis (angular ;
      mobile non applicable — l'application mobile n'est pas embarquée dans Weda)
- [ ] Aucune donnée de santé en clair dans les logs ; aucun RPPS ni adresse complète en clair
      (adresses masquées)
- [ ] Évènements PGSSI-S journalisés : rattachement, refus de rattachement, requalification — avec
      la personne, le rôle et la boîte
- [ ] Authentification PS via PSC testée bout-en-bout (sonde XOAUTH2 avant toute écriture)
- [ ] AIPD mise à jour (nouvelle source : Annuaire Santé ; rôle de délégataire)

## Manual Test Plan

- Backend e2e : `cd Api/Mail && dotnet run --project src/AppHost` (profil `e2e`)
- Mobile : `cd Client/Mobile && npm start` → http://localhost:4200
- weda2 : via le faux hôte du profil e2e (cf. `agents/e2e.md`)
- Se connecter avec l'identité PSC e2e. Écran de rattachement : « Mes boîtes » liste les deux BAL.
  - Choisir la BAL personnelle → badge **Titulaire**.
  - Choisir la BAL organisationnelle → badge **Membre**.
- « Ajouter une BAL déléguée » : saisir l'adresse personnelle → refus « choisissez-la dans Mes
  boîtes », aucune boîte ajoutée.
- Se connecter avec l'identité « délégataire e2e », saisir l'adresse de `boite-praticien` → badge
  **Délégation**.
- Arrêter l'Annuaire simulé → « Mes boîtes » affiche l'indisponibilité et « Réessayer » ; la saisie
  libre reste disponible.
- Retirer `boite-praticien` de l'Annuaire simulé, puis ré-authentifier la boîte → bandeau « à
  requalifier », la messagerie reste lisible en ligne.
- Écran Audit de weda2 : les rattachements portent le rôle et le RPPS de la personne.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — qualification de rattachement, sans exigence DSR publiée
- **Exigences DSR honorées** : non applicable — aucune exigence DSR ne porte sur le rôle d'un
  rattachement de BAL
- **INS** : non applicable — aucun patient n'est manipulé
- **Authentification PS** : PSC / e-CPS, eIDAS substantiel. Le RPPS vient du jeton PSC ; l'accès est
  validé par XOAUTH2 auprès de l'opérateur MSSanté avant toute écriture
- **Habilitations** : rôle issu de l'Annuaire Santé (titulaire, membre) ou de la délégation (saisie
  libre validée par l'opérateur). Le client ne déclare jamais son rôle
- **Interop CI-SIS** : API FHIR R4 de l'Annuaire Santé (Practitioner, PractitionerRole, métadonnées
  MSSanté de `telecom`)
- **Tracé PGSSI-S** : rattachement, refus de rattachement, requalification — personne (RPPS, nom),
  rôle, boîte. Conservation selon la famille de trace en vigueur, inchangée
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé — le registre ne reçoit aucune donnée de santé
- **AIPD / impact RGPD** : à mettre à jour — nouvelle source (Annuaire Santé, données publiques des
  PS), rôle de délégataire ; la mention « accès au nom d'un délégant » suspendue par task-401 est à
  reprendre

## Branches

- `api-mail` (pushed) : feat/task-402-rattachement-guide-par-l-annuaire — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-402-rattachement-guide-par-l-annuaire
- `client-mobile` (pushed) : feat/task-402-rattachement-guide-par-l-annuaire — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-402-rattachement-guide-par-l-annuaire
- `dtos-mss` (pushed, lazy) : feat/task-402-rattachement-guide-par-l-annuaire — créée par `/develop` au contrat (6719eeb)
- `client-angular` (code-only) : la forge écrit sur la branche courante de `Client/Angular/` — `feature/nova-mss-weda-integration` au /start (2026-10-28) ; humain gère branche, commit, push, PR TFS

## Timings

*(généré par `tools/timing/report.sh --task task-402 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 23 s | — | — | — | — |
| /develop | ok | 3 h 23 min | 15 (12 min 57 s) | 11 (19 min 56 s) | — | dtos-mss 1B/0T, api-mail 12B/7T, client-mobile 2B/2T, client-angular 0B/2T |
| /sonar | ok | 41 min 33 s | 3 (4 min 30 s) | 10 (20 min 32 s) | 4 (9 min 43 s) | 2 itération(s), api-mail 3B/10T |
| /lint-angular | ok | 13 min 45 s | 1 (1 min 39 s) | 1 (2 min 53 s) | — | 2 itération(s), client-angular 1B/1T |
| /lint-mobile | ok | 1 min 28 s | — | — | — | baseline propre |
| /e2e | ok | 27 min 20 s | — | — | — | e2e ×3 (24 min 29 s) |
| /review | skipped | 8 min 06 s | 3 (1 min 53 s) | 2 (7 min 00 s) | — | dtos-mss 1B/0T, api-mail 1B/1T, client-mobile 1B/1T, pause demandée par l'humain — validation faite (api-mail, dtos, mobile verts), revue APPROVED, PR non ouvertes |
| **Total cycle** | | **4 h 56 min** | **22 (21 min 01 s)** | **24 (50 min 22 s)** | **4 (9 min 43 s)** | |

Autres commandes mesurées : lint ×2 (2 min 03 s), nuget-wait ×1 (2.5 s), restore ×1 (10 s)

## Develop log

- Repos touched : dtos-mss, api-mail, client-mobile, client-angular (code-only)
- DTOs published : `HealthPlatform.Dtos.Mss` 548.0.0 → **551.0.0** (run 40681867625) — rôle et type d'adresse
  sur `MailboxDto`, `DirectoryMailboxDto`, `AttachMailboxRequest.Mode` (défaut `Delegation`), codes
  `MAILBOX_NOT_IN_DIRECTORY` / `MAILBOX_LISTED_USE_DIRECTORY`
- Interop published : no interop change
- Commits :
  - dtos-mss : 6719eeb feat(dto): rôle et type d'adresse de la boîte, BAL de l'Annuaire, mode de rattachement
  - api-mail : 7494367e chore(deps) bump 551.0.0 · 437f8d3f feat(mailboxes) · a5cf9187 test(e2e) faux Annuaire,
    seed, catalogue · f4719f4d fix(mailboxes) bypass sans jeton proxy · ca4db22e test(e2e) BAL publiée non
    rattachée + budget 30 s du seed rétabli · 593bd96b refactor simplify pass
  - client-mobile : eea646a feat(mobile) rattachement à deux voies · 0e1c008 test(e2e) E2E-MAILBOX-003/004
  - client-angular : **non commité** sur `feature/nova-mss-weda-integration` (code-only, l'humain commite et pousse
    vers TFS) — `libs/mss/src/core/models/mailbox.model.ts`, `core/models/mss-probe.model.ts`,
    `core/services/mailbox-accounts.service.ts` (+ spec), `ui/attach-mailbox-form/*` (+ nouveau spec),
    `features/mailbox-management/*` (+ spec), `features/mailbox-onboarding/*` (html + spec),
    `e2e/mss-e2e/specs/functional.e2e.ts`, `e2e/mss-e2e/support/e2e-backend.ts`, `e2e/mss-e2e/support/session.ts`
- Local build / test :
  - dtos-mss : build ✓
  - api-mail : build ✓ ; suite complète domain 195 ✓, api 1 290 ✓, application 3 776 (1 instable isolé ✓),
    infrastructure 695 (1 instable isolé ✓), integration 1 038 (16 ignorés) ✓. Instables, verts isolément et sans
    lien avec la task : `BackgroundSyncServiceCoverageTests.StartSyncAsync_WhenLeaseRenewalFails…` (course sur une
    `List` du test), `PostgresTenantRegistryClientTests.AttachingAnAddress_NormalisesItsCaseAndSpaces` (budget 3 s
    du registre sous charge parallèle), `E2eUnattachedXdmTests…`, `SeededThreadsAreCountableTests…` (vus une fois)
  - client-mobile : build ✓, tests 1 316 → +7 ✓ (ChromeHeadless)
  - client-angular : `nx test mss-lib` 1 312 → +12 ✓ (le build complet et le lint restent à `/lint-angular`)
- **Tests d'intégration (règle 1b)** — `MailboxAttachRoleIntegrationTests` (11 tests : vrai pipeline HTTP, vrai
  `MailboxManagementService`, vrai registre PostgreSQL, vrai `AnnuaireSanteService` sur `FakeAnnuaireSante`, vrai
  `AuditService` relu dans son canal ; seuls la sonde de l'opérateur et le proxy PSC sont simulés). Chacun vu rouge
  par mutation, restauration depuis copie + `touch` :
  - M1 BAL organisationnelle qualifiée titulaire → `AttachFromDirectory_OrganizationalMailbox_IsMember` rouge
  - M2 adresse hors Annuaire acceptée → `AttachFromDirectory_OfAnAddressNotPublished_Is400…` rouge
  - M3 sa propre adresse acceptée en délégation → `AttachByTyping_OneOfTheOwnMailboxes_Is400…` rouge
  - M4 pas de requalification → `Reauthenticate_HolderWhoseAddressLeftTheAnnuaire_TurnsToRequalify` rouge
  - M5 Annuaire indisponible propagé à la ré-authentification → `Reauthenticate_WhenTheAnnuaireDoesNotAnswer…` rouge
  - M6 rôle absent de la réponse → `AttachFromDirectory_PersonalMailbox_IsHolder…` rouge
  - M7 RPPS absent de la trace → `Journal_CarriesTheRoleAndTheRppsOfThePersonWhoActs…` rouge
  - M8 « déjà rattachée » jamais posé → `Directory_ListsTheMailboxesPublishedForTheSessionRpps…` rouge
  - M9 type PER ignoré par le parseur → `Directory_ListsTheMailboxesPublishedForTheSessionRpps…` rouge
  - M10 délégation qualifiée titulaire → `AttachByTyping_AnotherProfessionalsAddress_IsADelegation` rouge
  - M11 Annuaire incomplet rendu en liste courte → `Directory_WhenTheAnnuaireDoesNotAnswer_Is503…` rouge
  - M12 « Mes boîtes » sans session PSC → `Directory_WithoutAPscSession_IsRefused401` rouge
- **Parcours e2e (Step 6b)** — catalogue écrit avant les tests : E2E-MAILBOX-003 v1, E2E-MAILBOX-004 v1,
  E2E-WEDA-001 v2. Joués sur le banc réel (`--serve-only`) : mobile 2/2 ✓, weda2 3/3 ✓. Preuves par mutation côté
  client (serveur de dev rechargé à chaud), toutes rouges sur l'assertion prévue puis vertes après restauration :
  - mobile : choix « Mes boîtes » envoyé en délégation → 003 rouge ; saisie envoyée en « Mes boîtes » → 004 rouge
  - weda2 : idem 003 et 004 ; présélection supprimée (`data-preselected`) → E2E-WEDA-001 v2 rouge
- **Défauts trouvés par le banc, corrigés dans la task** :
  - « Mes boîtes » restait « en chargement » à l'arrivée directe sur la gestion des messageries (session pas encore
    en ligne à l'initialisation) : lecture déclenchée au passage en ligne (`effect`), test unitaire ajouté sur les
    deux clients — consigne `conventions/angular.md`.
  - weda2 envoie le cookie de session du proxy : sous bypass de test, le rattachement demandait un jeton à un proxy
    absent. Le contrôleur ne le demande plus sous bypass (test unitaire ajouté).
  - Le budget 30 s du registre au seed (task-399) avait été retiré par le revert de task-401 : rétabli.
- Écarts assumés, à arbitrer en revue :
  - la trace porte voie, rôle et RPPS dans `ServerRequest` (`mailbox-attach mode=… role=… actor-rpps=…`) ; les
    colonnes dédiées à la personne arrivent avec task-405 ;
  - la sonde s'authentifie par mot de passe sur un serveur sans OAuth2 (banc) : chemin absent de la production.
- Passe qualité (/simplify) :
  - Applied & committed : api-mail : 1 fichier (593bd96b, constante du bypass réutilisée)
  - No change : client-mobile, client-angular (la duplication mobile / weda2 est voulue : deux dépôts)
  - Skipped (contract) : dtos-mss
- DOD self-check : build et tests ✓ (4 repos) ; contrat publié et miroirs TS ✓ ; migration auditée (règle 7c : une
  migration additive, `role` NOT NULL défaut délégataire, `address_type` nullable, descente symétrique, aucune
  opération fantôme) ✓ ; tests unitaires parseur et rôle ✓ ; 6 lignes d'intégration ✓ (mutations M1-M12) ;
  écrans et badges + `data-testid` ✓ ; tests de composant ✓ ; banc (faux Annuaire, identités, rôles) ✓ ; 3 scénarios
  ✓ ; aucun RPPS ni adresse dans les journaux applicatifs (journal d'audit seulement) ✓. **AIPD** : à mettre à jour
  par l'humain (déféré au HAG).
- Next step : /sonar task-402

## Sonar log

- Serveur 25.6.0.109173 (`sonar.token`), clé `healthplatform-api-mail`, 2 analyses complètes (build Release +
  5 passes OpenCover).
- Phase 1 (new code) : **aucune dette introduite par la task**. Les 74 violations et 15 hotspots de la période de
  nouveau code ont été croisés avec les lignes modifiées par task-402 (`git diff origin/develop...HEAD`) :
  **0** ne porte sur une ligne de la task. Ils viennent de tasks déjà mergées (scripts Python et k6 du banc de
  charge, `Dockerfile`, `BaseRepository`) — la Quality Gate reste donc en ERROR sur des conditions héritées.
- Phase 1 — couverture : lignes nouvelles non couvertes trouvées sur 3 fichiers de la task (branche mot de passe de
  la sonde, requalification d'une boîte inconnue au registre, route « Mes boîtes » sans compte) + branches
  défensives : **15 tests ajoutés** (`test(sonar/new)`), new_coverage 97,3 % → **98,1 %**.
- Phase 1 — issues fixées : 0 (aucune issue sur le code de la task).
- Phase 2 (legacy) : non jouée (optionnelle) — la dette restante est hors task.
- Build / tests : ✓ vert. Instable vu en analyse, vert isolément : `SeededThreadsAreCountableTests` (collision
  d'UID du seed partagé, préexistant).

### KPIs qualité (baseline → final)

| Métrique | Baseline (26/10) | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | ERROR | ERROR (conditions héritées, 0 finding de la task) | → |
| New coverage | 97,3 % | 98,1 % | +0,8 pt |
| Bugs | 2 | 2 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 15 | 15 | 0 |
| Code smells | 79 | 72 | −7 |
| Coverage (projet) | 97,5 % | 98,0 % | +0,5 pt |
| Duplication | 0,3 % | 0,3 % | 0 |
| Reliability / Security / Maintainability | D / A / A | D / A / A | → |

## Lint log

- Mode : ciblé sur les fichiers de la task (contournement consigné par task-367 : `--projects=tag:scope:mss` ne
  restreint pas `nx affected` sur ce workspace) — `npx eslint --format json <15 fichiers>`, messages attribués aux
  lignes ajoutées par `git diff -U0 HEAD`
- Scope : `tag:scope:mss` (libs/mss) + support e2e weda2 touché par la task
- Pipeline fidelity : build `nx build weda2`, test `nx test mss-lib` (plugins Nx non isolés :
  `NX_ISOLATE_PLUGINS=false NX_DAEMON=false`, cf. mémoire du banc)
- Baseline (lignes de la task) : 33 errors / 6 warnings (fichiers entiers : 37 / 42, dette e2e préexistante :
  `max-lines`, JSDoc de fonctions anciennes)
- Final (lignes de la task) : **0 errors / 0 warnings** (fichiers entiers : 0 / 28 préexistants)
- Iterations : 2 / 5
- Build / tests : ✓ green (`weda2` build OK, `mss-lib` 1 313 tests)

| Iter | Errors before | Errors after | Build | Tests |
|------|---------------|--------------|-------|-------|
| 1 (auto-fix ×2) | 33 | 2 | — | — |
| 2 (manuel : JSDoc `openAs`, `mailboxRow`, constructeur, 3 `@example`) | 2 | 0 | ✓ | ✓ |

- Fichiers weda2 toujours **non commités** sur `feature/nova-mss-weda-integration` (code-only).
- Convention alimentée : `jsdoc/require-jsdoc` (Occurrences 12 → 13).

## Lint mobile log

- Branche : `feat/task-402-rattachement-guide-par-l-annuaire` (Client/Mobile)
- Baseline : `npm run lint` → **All files pass linting** (0 error / 0 warning)
- Iterations : 0 / 5 — rien à corriger, aucun commit
- Build / tests : ✓ green (validés par /develop après le dernier commit mobile : build OK, tests ChromeHeadless verts)

## E2E log

| Voie | Déclencheur | Résultat | Mode |
|---|---|---|---|
| mobile | api-mail, client-mobile, dtos-mss touchés | 49 verts, 0 flaky, 0 rouge — parité verte, démontage complet | rejouée |
| angular (weda2) | api-mail, client-angular, dtos-mss touchés | 57 verts, 1 flaky (E2E-SEARCH-001), 0 rouge — parité verte, démontage complet | rejouée (`NX_ISOLATE_PLUGINS=false NX_DAEMON=false NX_PLUGIN_NO_TIMEOUTS=true`) |

Porte `gate` : code 0. Ports 5052/3993/3465/3143/11535 libres, aucun conteneur e2e résiduel.
Flaky E2E-SEARCH-001 consigné au registre de `conventions/e2e.md` (14ᵉ occurrence, task de stabilisation déjà demandée).
Divergence E2E-MAILBOX-002 [angular] signalée « à retirer » par la porte (décision humaine, task-395).

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**Flaky (vert au second essai, non bloquant)** (1) :

- [angular] « recherche — requête et recherche avancée » (E2E-SEARCH-001)

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
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-BIO-003 | 1 | headless | Lire un résultat HPRIM puis l'acquitter | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ⚠️ flaky | ✅ |
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
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ · divergence (task-395) | ✅ |
| E2E-MAILBOX-003 | 1 | headless | Rattacher ses boîtes depuis « Mes boîtes » — titulaire et membre | ✅ | ✅ |
| E2E-MAILBOX-004 | 1 | headless | Ajouter une BAL déléguée par saisie — et refus de sa propre adresse | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |

**Divergences temporaires ouvertes** (1) :

- E2E-MAILBOX-002 [angular] — le code weda2 de task-378 (écran de panne à l'entrée et son test) n'est pas encore livré sur la branche weda2 ; divergence décidée par l'humain le 2026-10-25 — résorbée par task-395 — **à retirer** : le client est revenu à la version du catalogue

**Parité : verte** — aucun écart entre le catalogue et les suites.

## Review log — EN PAUSE (2026-10-28, demande de l'humain)

> **Point de reprise.** Le run `/forge 402, 403, 404, 405` est arrêté après task-402, à la demande de
> l'humain : task-403, task-404 et task-405 ne sont **pas** lancées (toujours `todo-*`). Reprendre par
> `/review task-402` : l'étape se rejoue entière, elle est idempotente jusqu'à l'ouverture des PR.

**Déjà fait à /review (2026-10-28) :**
- Branches `feat/task-402-rattachement-guide-par-l-annuaire` sur Dtos, api-mail et mobile : propres, poussées,
  à jour avec `origin/develop` (0 commit de retard).
- Build et tests verts :
  - `dtos-mss` : build, 0 erreur ;
  - `api-mail` : build 0 erreur ; tests verts (domain 195, infrastructure 697, application 3 783,
    api 1 295, intégration 1 022 dont 16 ignorés) ;
  - `client-mobile` : build OK, 1 317 tests verts.
- Verrou règle 1b : les 12 comportements atteignables par un endpoint ont chacun leur test d'intégration
  (`MailboxAttachRoleIntegrationTests`), vu rouge par mutation (M1–M12, `## Develop log`).
- Verrou e2e : `## E2E log` vert.
- Revue de code : **APPROVED**, aucun point bloquant. Deux suggestions :
  - la sonde à mot de passe (`MssAccountOnboardingService`) réutilise le mot de passe du contexte sur un
    serveur sans OAuth2. Absent de la production (tout en XOAUTH2), mais à garder hors de tout serveur
    réel à mot de passe ;
  - à la ré-authentification, un Annuaire injoignable garde le rôle : ce choix est voulu, il n'est pas
    tracé autrement que dans les journaux.

**Reste à faire :**
1. `client-angular` (code-only, branche `feature/nova-mss-weda-integration`, 17 fichiers non commités) :
   build et tests weda2 (`nx affected`, comme `/lint-angular`). La dernière validation verte remonte à
   `/lint-angular` (1 313 tests).
2. Ouvrir les PR Dtos, api-mail et mobile, avec le label `awaiting-human-merge`. Le corps de chaque PR
   reprend : KPIs Sonar (api-mail), `## E2E log`, revue de code et Manual Test Plan.
3. `## PRs` : liste des fichiers Angular à commiter par l'humain sur TFS.
4. `task-file.sh move task-402 done`, puis `/tech-writer E020`.
5. Agréger sur `forge/staging-task-402-405-20261028` (Dtos, api-mail, mobile). Le nom de la branche
   staging reste à décider à la reprise, puisque le run ne couvre plus que task-402.
6. Rapport de fin de cycle (Sonar, e2e, `## Timings`, « Amélioration continue »).
