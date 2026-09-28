# todo-task-342.md — Durcissement de la messagerie : dix-huit défauts ponctuels de sécurité, de cohérence et de fiabilité relevés par l'audit du 2026-09-27

**Repos**: api-mail
**Dependencies**: — (aucune)
**Epic**: E009
**Single frontend**: true
**Priorité**: **3** — défauts de gravité majeure à mineure sans cause commune suffisante pour une US dédiée. **À redécouper** si la taille dépasse la règle de ~30 fichiers par PR (voir « Arbitrage »).

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, ligne 17 du regroupement : **AUD-22, 27, 28, 31, 33, 36,
> 41, 42, 47, 51, 53, 54, 56, 57, 59, 62, 64, 66**). Chaque constat y est décrit avec son scénario et ses
> preuves ; ce task file en reprend l'essentiel.

> **⚠️ Arbitrage humain requis — découpage.** Cette task regroupe 18 constats indépendants, répartis en
> quatre lots ci-dessous. Deux options : (a) la lancer telle quelle — `/develop` traite les lots dans
> l'ordre A → D, un commit par constat ; (b) la redécouper en quatre tasks (une par lot) via `/po` avant
> `/start`. **Recommandation : (b)**, pour garder des PR relisibles et des HAG courts.

## Lot A — Sécurité et accès

- **AUD-42 — SSRF par serveur de messagerie choisi par l'utilisateur** (Majeur, Probable) —
  `SettingsController.cs:53-66`, `MailServerDiscovery` (`FromUserConfig` prioritaire),
  `SmtpConnectionFactory.cs:60-61`, `ImapConnectionService.cs:87` : `Host: "redis"` ou IP interne accepté ;
  jeton PSC présenté au serveur en OAuth2. → ~~allowlist exploitant~~ **retiré de cette task le 2026-09-28** (arbitrage humain) : repris par **task-348** (serveur résolu côté api-mail uniquement, plus de saisie utilisateur). Commits `b052826a` et `a592b5f2` revertés (`e4543409`, `07209bf4`).
- **AUD-59 — La politique de débit « sensitive » n'est appliquée nulle part** (Mineur) —
  `RateLimitingSetup.cs:60-76` : rattachement de boîte (connexion XOAUTH2 à chaque appel), routes IA,
  diagnostics sous le seul plafond global. → `[EnableRateLimiting]` sur ces routes.
- **AUD-62 — Noms d'entrées du ZIP de pièces jointes non assainis** (Mineur) — `AttachmentZipNameDisambiguator.cs`,
  `MailController.cs:868` : `..\..\…\x.bat` écrit tel quel. → `Path.GetFileName`, retrait de `..`, `:` et séparateurs, nom de repli.
- **AUD-22 — Un `Client-Email` périmé bloque en 403 les routes de gestion des boîtes** (Majeur) —
  `UserContextEnricherMiddleware.cs:658-686`, `MailboxSelectionService.cs:48-65` : boîte `Detached` ou
  `AuthFailing` → 403 sur lister / rattacher / détacher / défaut / logout / statut. → sur les routes
  `[MailboxNotRequired]`, `NotAttached` / `NotCompatible` traités comme « aucune boîte ».

## Lot B — Cohérence des données

- **AUD-33 — Registre : revenir à une ancienne boîte par défaut viole l'index unique partiel** (Majeur, Probable) —
  `PostgresTenantRegistryClient.cs:608-682, 898-912` : ordre des deux `UPDATE` par clé Guid v7 → 23505 rendu
  « registre injoignable ». → deux `SaveChanges` en transaction, ou contrainte `DEFERRABLE`, ou index déclaré au modèle ; **test sur Postgres réel**.
- **AUD-36 — Écritures non atomiques après la première `SaveChanges` d'`AddNewMail` ; course sur les tags de catégorie** (Majeur, Probable) —
  `MailRepository.cs:511-572, 3459-3490, 4234-4260` : 23505 sur `IX_Tags_Code` non rattrapé → mail validé sans
  embedding, tags, contacts ni notification, jamais rejoué ; chaînage de version perdu sur échec transitoire.
  → transaction, ou étapes rejouables ; rattrapage 23505 comme `ResolveOrCreateAiTagAsync`.
- **AUD-41 — Pièces jointes adressées par nom de fichier** (Majeur) — `ImapService.cs:3564, 3654-3669`,
  `MailController.cs:862-871` : deux `resultat.pdf` → la seconde inaccessible, le ZIP contient deux fois la première.
  → adressage par identifiant de partie MIME (`PartSpecifier`) ou index.
- **AUD-51 — Pagination non déterministe** (Mineur) — `PatientRepository.cs:502-507`, `PostgresAuditReader.cs:111-114, 188-202`. → critère de départage (`ThenBy` sur l'identifiant).
- **AUD-64 — Annuaire FHIR : seul le premier `PractitionerRole` est gardé** (Mineur, Probable) —
  `FhirBundleParser.cs:21-26, 124-130, 208`. → fusion des e-mails de tous les rôles.

## Lot C — Affichage et fraîcheur

- **AUD-27 — Le cache `Mail.Email` fige la version d'avant l'analyse pendant 15 min** (Majeur) —
  `MailController.cs:649-667`, `ImapService.cs:3373-3459, 2140-2203`. → ne pas mettre en cache une réponse
  issue du repli IMAP, ou évincer `Mail.Email` / `Mail.Summary` à l'enrichissement (premier plan et fond).
- **AUD-28 — « Aujourd'hui » suit l'horloge de l'hôte** (Majeur) — `ImapService.cs:1334, 1370, 1504-1505`,
  `OfflineMailDataProvider.cs:206-212, 242-246` : conteneur UTC → mails de 00 h-02 h (Paris) absents des tuiles du jour ;
  hors ligne faux même à Paris. → bornes dérivées de `PractitionerDay`, `InternalDate` / `SentDate` convertis.
- **AUD-31 — Le compte rendu d'enrichissement annonce « analysés » des messages non persistés** (Majeur) —
  `ImapService.cs:1733-1735, 2057-2077, 2209-2217`. → compter les succès réels, le reste en `Unreachable` / 503.
- **AUD-57 — Résumé IA d'un mail non enrichi jamais persisté, refacturé à chaque ouverture** (Mineur, Probable) —
  `EmailSummaryService.cs:90-123`, `MailRepository.cs:2834-2848`. → cache propre au mail (sans créer de ligne `MailContents`).

## Lot D — Fiabilité mineure et conformité règle 12

- **AUD-47 — Archivage « Envoyés » rejoué de façon non idempotente** (Mineur) — `ImapService.cs:4389-4403`,
  `SentArchiveService.cs:52-88` : APPEND réussi puis `CloseAsync` en échec → jusqu'à 3 copies. → archivage acquis dès l'APPEND, fermeture best-effort.
- **AUD-53 — `POST diagnostics/test-similarity` toujours 500** (Mineur) — `AiDiagnosticsController.cs` (`BuildResultObject`, Guid déballé en `int`), charge toute la boîte. → projection typée, pagination.
- **AUD-54 — Consommation de tokens fausse** (Mineur) — `AiConversationService.cs:167` (`promptTokens` toujours 0). → lecture de l'usage réel du fournisseur.
- **AUD-56 — Comparaison des tags IA sensible à la casse** (Mineur, Probable) — `EmailTaggingService.cs:21-26, 265`. → `OrdinalIgnoreCase` et normalisation vers le libellé canonique.
- **AUD-66 — Retours hors `ProblemDetails` restants** (Mineur) — `MailController.cs:1722-1729` (500 sans corps),
  `DraftController.cs:153` (`StatusCode(500)` nu), `BadRequest(ModelState)` en `SerializableError`. → règle 12.

## Objective

Corriger chacun de ces défauts **sans changer le comportement nominal**, chaque correctif précédé d'un
test qui le reproduit.

### Hors périmètre

- Les défauts couverts par les tasks 326 à 341 et par les tasks 189 / 191 / 192 / 290.

## Definition of Done

- [ ] Build passes (0 errors) — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` ; Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] **Pour chacun des 18 constats** : un test qui échoue sur le code actuel (log du run rouge consigné dans le task file) puis passe après correctif — un commit par constat
- [x] ~~AUD-42 : `SaveSettings` avec un hôte hors allowlist ou une IP privée → 400 ; aucune connexion tentée~~ — **sorti du périmètre, repris par task-348**
- [ ] AUD-33 : test sur **Postgres réel** (Testcontainers) — B → A et détachement de la boîte par défaut réussissent
- [ ] AUD-36 : deux mails introduisant la même catégorie en parallèle → les deux complètement traités
- [ ] AUD-41 : deux pièces homonymes → téléchargeables séparément, ZIP avec deux contenus distincts
- [ ] AUD-28 : mail reçu à 00 h 30 heure de Paris sur un hôte UTC → présent dans « reçus aujourd'hui »
- [ ] Tests d'intégration endpoints (règle 1b) pour les routes modifiées (`settings`, rattachement de boîte, téléchargement de pièce jointe, `test-similarity`)
- [ ] Migration éventuelle (AUD-33) auditée selon la règle 7c
- [ ] Aucune donnée de santé ni adresse en clair ajoutée dans les logs

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` ; Blazor et mobile connectés à des boîtes de test.
2. **Lot A** : détacher la boîte courante sur mobile puis recharger la gestion des boîtes → la liste s'affiche (plus de 403) ; télécharger en ZIP un mail dont une pièce s'appelle `..\x.bat` → entrée assainie.
3. **Lot B** : praticien à deux boîtes, définir B par défaut puis revenir à A → succès ; recevoir un mail avec deux `resultat.pdf` → les deux s'ouvrent, distincts.
4. **Lot C** : ouvrir un mail avant la fin de son analyse, attendre l'enrichissement, rouvrir → les documents CDA apparaissent ; mail de test daté de 00 h 30 → visible dans « reçus aujourd'hui ».
5. **Lot D** : `POST /api/v1/diagnostics/test-similarity` sur une boîte non vide → 200 ; forcer une erreur sur la route des tags → réponse `application/problem+json`.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville, biologie
- **Vague Ségur** : V2
- **Exigences DSR honorées** : non applicable — fiabilité et sécurité de fonctionnalités existantes
- **INS** : non applicable
- **Authentification PS** : PSC / e-CPS inchangée (AUD-42 sorti du périmètre → task-348)
- **Habilitations** : inchangées ; routes de gestion des boîtes accessibles même avec une boîte courante devenue invalide
- **Interop CI-SIS** : Annuaire Santé FHIR R4 (`PractitionerRole`) — lecture de tous les rôles (AUD-64)
- **Tracé PGSSI-S** : inchangé ; les erreurs rendues passent par `ProblemDetails` sans donnée
- **Consentement patient** : non applicable
- **Référentiels métier** : Annuaire Santé (RPPS)
- **Hébergement HDS** : oui — environnement inchangé
- **AIPD / impact RGPD** : inchangé

## Branches

> **Arbitrage découpage** : `/start 342` lancé directement sans redécoupage `/po` → option (a) retenue — `/develop` traite les lots A → D dans l'ordre, un commit par constat.

- `api-mail` (pushed) : fix/task-342-durcissement-messagerie — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-342-durcissement-messagerie

## Develop log

- Repos touched : api-mail (branche `fix/task-342-durcissement-messagerie`)
- DTOs published : no DTO change · Interop : no change · SDK : no change
- **Taille** : 86 fichiers, +3 944 / −287 — au-delà du repère ~30 fichiers par PR. L'humain a lancé `/start 342` sans redécoupage (option (a) de l'arbitrage) : 1 commit par constat pour garder la PR relisible commit par commit.
- Commits (18 constats, 1 commit chacun, + 2 suites + passe qualité) :
  - `b052826a` fix(settings): serveur IMAP/SMTP personnalisé restreint à la liste d'autorisation de l'exploitant (AUD-42)
  - `9acbcb7d` fix(api): politique de débit « sensitive » appliquée au rattachement de boîte, à l'IA et aux diagnostics (AUD-59)
  - `0469ef66` fix(mail): noms d'entrées du ZIP de pièces jointes réduits à un nom de fichier sûr (AUD-62)
  - `95a6b39e` fix(middleware): un Client-Email périmé ne bloque plus en 403 les routes de gestion des boîtes (AUD-22)
  - `983e9542` fix(registry): changer ou détacher la boîte par défaut ne heurte plus l'index unique partiel (AUD-33)
  - `8cd971fd` fix(mail): AddNewMail atomique et course sur les tags de catégorie rattrapée (AUD-36)
  - `cff10eb2` fix(mail): pièces jointes homonymes adressées par rang, téléchargement unitaire et ZIP (AUD-41)
  - `27cfcb7d` fix(pagination): critère de départage sur l'identifiant pour le dossier patient et l'écran d'audit (AUD-51)
  - `9014aa10` fix(annuaire): e-mails MSSanté fusionnés sur tous les PractitionerRole du praticien (AUD-64)
  - `2db8b707` fix(mail): le contenu servi avant l'analyse n'est plus figé en cache, et l'enrichissement l'évince (AUD-27)
  - `1cb416c2` fix(mail): « aujourd'hui » suit la journée du praticien, plus l'horloge de l'hôte, en ligne comme hors ligne (AUD-28)
  - `a4f9aa8d` fix(mail): le compte rendu d'enrichissement ne compte « analysés » que les messages persistés, le reste est injoignable et repris (AUD-31)
  - `1ad4f2fe` fix(ai): le résumé IA d'un mail non enrichi est mémorisé par mail, plus refacturé à chaque ouverture (AUD-57)
  - `079769c6` fix(mail): archivage « Envoyés » acquis dès l'APPEND, la fermeture du dossier est best-effort (AUD-47)
  - `33401ca2` fix(diagnostics): test-similarity rend 200 sur une boîte non vide — projection typée, lecture bornée (AUD-53)
  - `fb9f8c12` fix(ai): consommation de tokens lue sur le décompte du fournisseur, résumés compris (AUD-54)
  - `74c048b1` fix(ai): étiquette IA comparée sans la casse et posée sous son libellé canonique (AUD-56)
  - `51b43d19` fix(api): dernières erreurs hors ProblemDetails — GetMailsByTag avant flush, issue d'envoi inconnue, ModelState invalide en problem+json (AUD-66)
  - `36a3a6bf` fix(ai): le mémo de résumé ne journalise plus le sujet du mail (AUD-57)
  - `a592b5f2` test(settings): serveurs de test locaux inscrits dans la liste d'autorisation (AUD-42)
  - `368ba75b` refactor(mail): simplify pass (/simplify)
- Passe qualité (/simplify) : Applied & committed : api-mail, 5 fichiers (`368ba75b`) — éviction par mail factorisée (`MailCacheEviction`), recherche de tag canonique simplifiée, XML docs de `MailController` remises en place. Skipped (contract) : dtos-mss, interop-cda, sdk.
- Migration (règle 7c) : **aucune**. AUD-33 déclare l'index `ux_mss_accounts_one_default_per_account` dans le modèle EF (descriptif) ; le schéma du registre est porté par FluentMigrator (`20260913120000_CreateTenantRegistry.cs`, qui crée déjà l'index) — pas de migration EF, pas de snapshot à vérifier.
- Logs : aucune donnée de santé, INS ni adresse ajoutée. Le seul log ajouté qui portait le sujet du mail (AUD-57, `EmailSummaryService`) a été corrigé (`36a3a6bf`, Uid au lieu du sujet). Les lignes préexistantes de ce fichier qui loguent `Subject` restent sur develop — hors périmètre, à router.

- **Validation finale** (suite complète après la passe qualité) : build 0 erreur ; tests **5 842 verts, 0 échec**, 16 ignorés préexistants (domain 190, infrastructure 665, application 3 295, api 1 031, integration 645 + 16 ignorés).
- DOD self-check : 10/10 items commandables vérifiés (build, tests, 18 × RED→GREEN consignés, AUD-42 400 sans connexion, AUD-33 Postgres réel, AUD-36 parallèle, AUD-41 homonymes + ZIP, AUD-28 00 h 30 Paris sur hôte UTC, tests d'intégration settings / rattachement / pièce jointe / test-similarity, 7c sans migration, logs sans donnée de santé).
- Next step : /sonar task-342

### Points d'attention pour la revue / le HAG

- **AUD-42 — ⚠️ REVERTÉ le 2026-09-28** (`e4543409` revert de `a592b5f2`, `07209bf4` revert de `b052826a`, conflit sur `UserMailServerHostPolicyTests.cs` résolu par suppression) : arbitrage humain, allowlist abandonnée, repris par **task-348**. Le paragraphe suivant ne s'applique plus. ~~Changement de comportement~~ : un hôte IMAP/SMTP personnalisé hors liste d'autorisation → 400 à l'enregistrement, et repli silencieux sur le serveur du domaine à la connexion. **La production doit renseigner `MailServers:AllowedUserServerHosts`** pour tout serveur personnalisé légitime (vide par défaut ; les hôtes de `MailServers.Domains` sont toujours autorisés). Profil loadtest de l'AppHost : `localhost` + `$MSS_LOADTEST_MAIL_HOST` autorisés.
- **AUD-59** : la politique `sensitive` (10 req / 60 s par utilisateur, configurable) est partagée par rattachement de boîte, test IMAP, IA, chat (création + stream) et diagnostics.
- **AUD-41 — suivi fronts** : paramètre optionnel `?occurrence=k` sur `GET …/download/attachment/{name}` (rang parmi les homonymes, 0 par défaut = comportement historique). Le ZIP est correct sans changement front ; **le téléchargement unitaire du 2ᵉ homonyme demande que Blazor / Angular / mobile passent `occurrence`** — hors `**Repos**:` de cette task, à router vers le PO.
- **AUD-36** : `AddNewMail` devient transactionnel — un échec après l'insert ne laisse plus de mail à moitié traité ; il est rejoué au passage suivant.
- **AUD-27 / task-345** : le repli IMAP n'est plus mis en cache, et l'enrichissement évince `Mail.Email` / `Mail.Summary`. Hypothèse non vérifiée : le passage « 1 document → 0 » observé par task-345 pourrait aussi venir d'un changement de génération UIDVALIDITY dans le seed e2e (`TryResolveExistingMailAsync` / `UpdateEmailSummaryAsync` ignorent la génération, `GetMailAsync` la filtre). Si `E2E-BIO-001` reste rouge à la reprise de 345, regarder là.
- **AUD-28** : INTERNALDATE n'est pas stockée en base — hors ligne, l'en-tête `Date` reste utilisé (désormais converti en journée Paris). `EmailBuildingService.MapHeaderFields` (`SentDate = envelope.Date?.LocalDateTime`) reste hors périmètre (change ce que reçoivent les fronts).
- **AUD-57** : mémo par mail (Redis, 24 h, clé = hash du contenu, donc jamais servi après enrichissement), sans ligne `MailContents`. Garde défensive : aucun chemin nominal reproduit.
- **AUD-66** : sur `ContactController`, le 400 passe par `ValidationException` (le `[Produces("application/json")]` du contrôleur réécrivait le content-type de `ValidationProblem`) — pas d'objet `errors` par champ, le `detail` nomme les champs sans leurs valeurs.
- Régressions de fixtures dues à AUD-42 (9 tests SMTP/sync pointant un serveur local) corrigées côté tests (`a592b5f2`).

### Runs RED → GREEN par constat

#### AUD-42 — SSRF par serveur IMAP/SMTP choisi par l'utilisateur
Tests : `tests/mss.mail.application.tests/Services/Settings/UserMailServerHostPolicyTests.cs` (IsAllowed_HostOutsideAllowlist_ReturnsFalse x10, IsAllowed_HostInAllowlist_ReturnsTrue x6, EnsureAllowedAsync_* x16, DiscoveryImap/Smtp_StoredHostOutsideAllowlist_* x3) ; `tests/mss.mail.integration.tests/Api/SettingsMailServerAllowlistIntegrationTests.cs` (SaveSettings_HostOutsideAllowlist_Returns400ProblemAndStoresNothing x3, SaveSettings_AllowlistedHost_Returns200AndStores, SaveSettings_NoCustomServer_Returns200).
RED (politique stub + code d'origine) :
```
Échoué UserMailServerHostPolicyTests.EnsureAllowedAsync_BareInternalName_ThrowsValidationWithoutResolving
   Assert.Throws() Failure: No exception was thrown
Échoué UserMailServerHostPolicyTests.DiscoveryImap_StoredHostOutsideAllowlist_FallsBackToDomainServer
   Expected: "imap.gmail.com"  Actual: "redis"
Échoué!  - échec : 25, réussite : 11, total : 36 - mss.mail.application.tests.dll
Échoué SettingsMailServerAllowlistIntegrationTests.SaveSettings_HostOutsideAllowlist_Returns400ProblemAndStoresNothing(imapHost: "redis", ...)
   Expected: BadRequest  Actual: OK
Échoué!  - échec : 3, réussite : 2, total : 5 - mss.mail.integration.tests.dll
```
GREEN : application.tests (policy + discovery + SMTP/IMAP factories + onboarding + background IMAP) 169/169 ; integration SettingsMailServerAllowlist 5/5 ; api.tests Settings/Architecture/Configuration 56/56 ; build 0 erreur.
Commit : b052826a

#### AUD-59 — Politique de débit « sensitive » appliquée nulle part
Tests : `tests/mss.mail.api.tests/Configuration/SensitiveRateLimitBindingTests.cs` (SensitiveAction_IsBoundToSensitivePolicy x12, ConversationReads_StayUnderGlobalLimitOnly x3).
RED :
```
Échoué SensitiveRateLimitBindingTests.SensitiveAction_IsBoundToSensitivePolicy(controller: typeof(AccountController), action: "AttachMailboxAsync")
   Expected: "sensitive"  Actual: null
Échoué ...(AiController, "CorrectTextAsync")  Expected: "sensitive"  Actual: null
Échoué ...(AiDiagnosticsController, "TestSimilarityAsync")  Expected: "sensitive"  Actual: null
(12 échecs sur 15)
```
GREEN : api.tests (binding + RateLimiting + Account/Ai/AiChat/AiDiagnostics + Architecture) 123/123 ; integration (AiDiagnostics, AccountController, RateLimiting, PscSession, Settings) 26/26.
Commit : 9acbcb7d

#### AUD-62 — Noms d'entrées du ZIP de pièces jointes non assainis
Tests : `tests/mss.mail.application.tests/Helpers/AttachmentZipNameDisambiguatorTests.cs` (Disambiguate_UnsafeName_KeepsOnlyASafeFileName x8, Disambiguate_NameEmptyOnceSanitised_FallsBackToAttachment x5, Disambiguate_NamesCollidingOnceSanitised_AreStillDisambiguated, Disambiguate_AnyName_NeverProducesPathSeparatorOrParentSegment) ; `tests/mss.mail.api.tests/Controllers/MailControllerTests.cs` (DownloadAttachmentsZip_AttachmentNameWithParentSegments_WritesSanitisedEntryName).
RED :
```
Échoué AttachmentZipNameDisambiguatorTests.Disambiguate_UnsafeName_KeepsOnlyASafeFileName(raw: "../../etc/cron.d/x.sh", expected: "x.sh")
   Expected: "x.sh"  Actual: "../../etc/cron.d/x.sh"
Échoué ...Disambiguate_NameEmptyOnceSanitised_FallsBackToAttachment(raw: "..")  Expected: "attachment"  Actual: ".."
Échoué ...Disambiguate_NamesCollidingOnceSanitised_AreStillDisambiguated  Expected: "resultat.pdf"  Actual: "a\resultat.pdf"
Échoué MailControllerTests.DownloadAttachmentsZip_AttachmentNameWithParentSegments_WritesSanitisedEntryName
   Expected: "x.bat"  Actual: "..\..\Startup\x.bat"
```
GREEN : AttachmentZipNameDisambiguatorTests 21/21 ; api.tests DownloadAttachmentsZip + AttachmentAuditLogFrontier 12/12.
Commit : 0469ef66

#### AUD-22 — Un Client-Email périmé bloque en 403 les routes de gestion des boîtes
Tests : `tests/mss.mail.integration.tests/Api/StaleClientEmailMailboxManagementIntegrationTests.cs` (ManagementRoute_WithStaleClientEmail_IsServedAsIfNoMailboxWasSelected x8 — list/attach/detach/default × Detached/AuthFailing ; ManagementRoute_WithStaleClientEmail_DoesNotOpenTheStaleMailbox ; MailboxRequiringRoute_WithStaleClientEmail_KeepsItsRefusal x2, verts avant et après = non-régression).
RED :
```
Échoué ...ManagementRoute_WithStaleClientEmail_IsServedAsIfNoMailboxWasSelected(staleMailbox: "detachee@...", method: "GET", path: "/api/v1/account/mailboxes")
   GET /api/v1/account/mailboxes with a stale Client-Email answered 403.
Échoué ...(staleMailbox: "authfailing@...", method: "POST", path: "/api/v1/account/mailboxes")  answered 403.
Échoué ...ManagementRoute_WithStaleClientEmail_DoesNotOpenTheStaleMailbox  Expected: OK  Actual: Forbidden
Échoué!  - échec : 9, réussite : 2, total : 11
```
GREEN : integration StaleClientEmail + PscSession + MailEventsStreamIsolation 26/26 ; api.tests Middleware/Account/Sync/Connection 114/114 ; build solution 0 erreur.
Commit : 95a6b39e

#### AUD-33 — Registre : changer / détacher la boîte par défaut viole l'index unique partiel

Tests (Postgres réel, collection `PostgreSql`) — `tests/mss.mail.integration.tests/TenantRegistry/TenantRegistryIntegrationTests.cs` :
- `SetDefaultMailboxAsync_BackToAnOlderMailbox_Succeeds`
- `DetachMailboxAsync_OfTheDefault_WithAnOlderHeir_Succeeds`

RED :
```
Échoué ...TenantRegistryIntegrationTests.SetDefaultMailboxAsync_BackToAnOlderMailbox_Succeeds [132 ms]
  TenantRegistryUnavailableException : Le registre est injoignable. Opération=SetDefaultMailboxAsync
  ---- DbUpdateException ... -------- Npgsql.PostgresException : 23505: duplicate key value violates unique constraint "ux_mss_accounts_one_default_per_account"
Échoué!  - échec :     2, réussite :    12, total :    14
```
GREEN : `--filter TenantRegistry` integration 54/54, infrastructure 74/74 ; build 0 erreur.
Commit : 983e9542

#### AUD-36 — AddNewMail non atomique ; course sur les tags de catégorie

Tests (Postgres réel) — `tests/mss.mail.integration.tests/Repository/MailRepositoryCategoryTagRaceTests.cs` :
- `AddNewMail_WhenTheCategoryTagIsCreatedConcurrently_LinksTheWinnersTag` (intercepteur : le tag est créé hors bande juste avant notre INSERT)
- `AddNewMail_TwoMailsIntroducingTheSameCategoryInParallel_AreBothFullyProcessed` (DOD — Barrier : les deux lisent « tag absent » avant d'insérer)
- `AddNewMail_WhenAStepAfterTheMailInsertFails_LeavesNoMailBehind` (panne simulée sur INSERT MailTags)

RED :
```
Échoué ...AddNewMail_TwoMailsIntroducingTheSameCategoryInParallel_AreBothFullyProcessed [3 s]
   DbUpdateException ... ---- Npgsql.PostgresException : 23505: duplicate key value violates unique constraint "IX_Tags_Code"
Échoué ...AddNewMail_WhenTheCategoryTagIsCreatedConcurrently_LinksTheWinnersTag [302 ms]
   ---- Npgsql.PostgresException : 23505: duplicate key value violates unique constraint "IX_Tags_Code"
Échoué ...AddNewMail_WhenAStepAfterTheMailInsertFails_LeavesNoMailBehind [86 ms]
   Assert.False() Failure
Échoué!  - échec :     3, réussite :     0, total :     3
```
GREEN : 3/3 ; régression integration `Repository|Enrichment` 288/288, infrastructure `MailRepository` 179/179, api `Architecture` 23/23 ; build 0 erreur.
Commit : 8cd971fd

#### AUD-41 — Pièces jointes adressées par nom de fichier (homonymes)

Tests d'intégration endpoint (TestServer, vrai MailController + ServiceImplementation + ImapService, IMAP simulé à deux parties `resultat.pdf`) — `tests/mss.mail.integration.tests/Controllers/MailAttachmentDownloadIntegrationTests.cs` :
- `DownloadAttachment_WithoutOccurrence_ReturnsTheFirstHomonym` (non-régression, vert avant/après)
- `DownloadAttachment_WithOccurrenceOne_ReturnsTheSecondHomonym`
- `DownloadAttachment_WithAnOccurrenceBeyondTheHomonyms_Returns404`
- `DownloadAttachmentsZip_WithTwoHomonyms_HoldsTwoDistinctContents`
Complément (écrits avec le correctif, API nouvelle) : `MailRepositoryHomonymAttachmentTests.AttachmentCache_WithTwoHomonyms_KeepsOneContentPerOccurrence` (Postgres), `MailControllerTests.DownloadAttachment_WithANegativeOccurrence_ThrowsValidation`, `MailControllerTests.RankHomonyms_RanksEachNameAmongItsHomonyms` ; `DownloadAttachmentsZip_MultipleAttachments_StreamsZipWithDisambiguatedNames` adapté (contenus distincts asserts).

RED (sur le code actuel, relais 5-arg retiré du harnais) :
```
Échoué ...DownloadAttachmentsZip_WithTwoHomonyms_HoldsTwoDistinctContents [1 s]
   Assert.Contains() Failure: Filter not matched in collection
Échoué ...DownloadAttachment_WithAnOccurrenceBeyondTheHomonyms_Returns404 [50 ms]
   Expected: NotFound  Actual: OK
Échoué ...DownloadAttachment_WithOccurrenceOne_ReturnsTheSecondHomonym [66 ms]
   Expected: [115, 101, 99, ...] ("second…")  Actual: [112, 114, 101, ...] ("premier…")
Échoué!  - échec :     3, réussite :     1, total :     4
```
GREEN : endpoint + repository 5/5 ; integration `Repository.MailRepository` 78/78 ; api `MailController|Attachment` 198/198 ; application `Imap|ServiceImplementation|MailDataProvider` 728/728 ; infrastructure `MailRepository` 179/179 ; build 0 erreur.
Commit : cff10eb2

#### AUD-51 — Pagination non déterministe (dossier patient, écran d'audit)

Tests (Postgres réel, 40 ex æquo, pages de 3) :
- `tests/mss.mail.integration.tests/Repository/PatientRepositoryPaginationTieTests.cs` — `GetMailsByInsAsync_WithTiedDocumentDates_PagesCoverEveryMailExactlyOnce`
- `tests/mss.mail.integration.tests/TenantRegistry/AuditReaderSortIntegrationTests.cs` — `Les_ex_aequo_pagines_apparaissent_chacun_une_seule_fois(null | "actiontype")`

RED :
```
Échoué ...AuditReaderSortIntegrationTests.Les_ex_aequo_pagines_apparaissent_chacun_une_seule_fois(sortBy: "actiontype") [363 ms]
   Expected: 40  Actual: 35   (5 traces doublées / omises)
Échoué ...PatientRepositoryPaginationTieTests.GetMailsByInsAsync_WithTiedDocumentDates_PagesCoverEveryMailExactlyOnce [5 s]
   Expected: 40  Actual: 35
Échoué!  - échec :     2, réussite :     1, total :     3
```
(le cas tri par défaut — horodatage — passait déjà sur ce jeu, le départage le rend garanti.)
GREEN : integration `PatientRepository|AuditReader` 47/47, infrastructure `PatientRepository|Audit` 77/77 ; build 0 erreur.
Commit : 27cfcb7d

#### AUD-64 — Annuaire FHIR : seul le premier PractitionerRole est gardé

Tests — `tests/mss.mail.application.tests/Services/AnnuaireSante/FhirBundleParserMultiRoleTests.cs` :
- `ParsePractitionerBundle_WithTwoRoles_MergesTheMailboxesOfBothRoles`
- `ParsePractitionerRoleBundle_WithTwoRoles_MergesTheMailboxesOfBothRoles`
- `ParseTwoStepBundle_WithTwoRoles_MergesTheMailboxesOfBothRoles`

RED :
```
Échoué ...ParsePractitionerRoleBundle_WithTwoRoles_MergesTheMailboxesOfBothRoles [82 ms]
   Expected: ["dupont@cabinet.mssante.fr", "dupont@clinique.mssante.fr"]
   Actual:   ["dupont@cabinet.mssante.fr"]
Échoué ...ParseTwoStepBundle_WithTwoRoles_MergesTheMailboxesOfBothRoles — idem
Échoué ...ParsePractitionerBundle_WithTwoRoles_MergesTheMailboxesOfBothRoles — idem
Échoué!  - échec :     3, réussite :     0, total :     3
```
GREEN : application `AnnuaireSante` 177/177 (dont `ParseTwoStepBundle_FirstRoleOnly_StopsAtFirstMatch` : toujours un seul DTO) ; build 0 erreur.
Commit : 9014aa10

#### AUD-27 — Le cache `Mail.Email` fige la version d'avant l'analyse

Tests :
- `MailControllerTests.GetEmail_ContentRebuiltFromTheMailServerBeforeEnrichment_IsNotCached` (+ contre-épreuve `GetEmail_ContentServedByTheEnrichedCopy_IsCached`)
- `ImapServiceCoverageTests.GetEmailContentAsync_WhenTheMailIsNotAnalysedYet_FlagsTheRebuiltContentAsNotYetEnrichedAsync` (+ `GetEmailContentAsync_WhenTheEnrichedCopyExists_IsCacheableAsync`)
- `ImapServiceEnrichmentCoverageTests.EnrichEmailsAsync_WhenTheMailIsPersisted_EvictsItsContentAndSummaryCachesAsync` (premier plan)
- `BackgroundEnrichmentProcessorTests.PersistEnrichedBatchAsync_MailPersisted_EvictsItsContentAndSummaryCaches` (+ `PersistEnrichedBatchAsync_MailLeftPending_KeepsTheCacheUntouched`) (fond)

RED :
```
Échoué ...ImapServiceEnrichmentCoverageTests.EnrichEmailsAsync_WhenTheMailIsPersisted_EvictsItsContentAndSummaryCachesAsync
Échoué ...BackgroundEnrichmentProcessorTests.PersistEnrichedBatchAsync_MailPersisted_EvictsItsContentAndSummaryCaches
   NSubstitute.Exceptions.ReceivedCallsException : Expected to receive exactly 1 call matching: RemoveAsync(...) — Actually received no matching calls.
Échoué ...ImapServiceCoverageTests.GetEmailContentAsync_WhenTheMailIsNotAnalysedYet_FlagsTheRebuiltContentAsNotYetEnrichedAsync
   Assert.Equal() Failure: Strings differ — Expected: "mail-content:not-yet-enriched" Actual: ""
Échoué ...MailControllerTests.GetEmail_ContentRebuiltFromTheMailServerBeforeEnrichment_IsNotCached
   NSubstitute.Exceptions.ReceivedCallsException : Expected to receive no calls matching: SetAsync(...) — Actually received 1 matching call
```
GREEN : application.tests filtre BackgroundEnrichmentProcessor|ImapServiceEnrichmentCoverageTests|ImapServiceCoverageTests|ImapServiceTests → 202/202 ; api.tests `MailControllerTests` → 176/176. Build 0 erreur.
Commit : `2db8b707`

#### AUD-28 — « Aujourd'hui » suit l'horloge de l'hôte

Horloge injectée (`TimeProvider` figé à 2026-07-14T22:35Z = 15/07 00 h 35 à Paris), aucune lecture de l'horloge machine.
Tests :
- `ImapServiceCoverageTests.GetFolderTodayAsync_MailDeliveredAtHalfPastMidnightParisOnAUtcHost_IsReceivedTodayAsync` (DOD : mail reçu à 00 h 30 Paris → « reçus aujourd'hui »)
- `ImapServiceCoverageTests.GetFolderTodayAsync_TheScopeDayOfTheCachedQuery_IsThePractitionerDayAsync`
- `OfflineMailDataProviderTests.GetFolderTodayAsync_MailReceivedAtHalfPastMidnightParis_IsReceivedTodayAsync`
- `OfflineMailDataProviderTests.GetFolderNotSeenTodayAsync_MailReceivedAtHalfPastMidnightParis_IsUnreadTodayAsync`

RED :
```
Échoué ...ImapServiceCoverageTests.GetFolderTodayAsync_MailDeliveredAtHalfPastMidnightParisOnAUtcHost_IsReceivedTodayAsync
   Assert.Equal() Failure: Collections differ — Expected: [2] Actual: []
Échoué ...OfflineMailDataProviderTests.GetFolderTodayAsync_MailReceivedAtHalfPastMidnightParis_IsReceivedTodayAsync
   Assert.Equal() Failure: Collections differ — Expected: [2] Actual: []
Échoué ...OfflineMailDataProviderTests.GetFolderNotSeenTodayAsync_MailReceivedAtHalfPastMidnightParis_IsUnreadTodayAsync
   Assert.Equal() Failure: Collections differ — Expected: [2] Actual: []
Échoué ...ImapServiceCoverageTests.GetFolderTodayAsync_TheScopeDayOfTheCachedQuery_IsThePractitionerDayAsync
   NSubstitute.Exceptions.ReceivedCallsException : Expected to receive a call matching SetAsync(ScopeDay == "2026-07-15") — Actually received no matching calls.
```
(Note : un premier jeu daté du 2026-09-27 passait sur l'hôte Paris le 2026-09-28 par coïncidence de date — dates déplacées au 14/07 pour un RED indépendant du jour d'exécution.)
GREEN : application.tests filtre OfflineMailDataProvider|ImapServiceCoverageTests|PractitionerDay|ImapServiceTests|FolderQuery|Today → 223/223. Build 0 erreur.
Commit : `1cb416c2`

#### AUD-31 — Le compte rendu d'enrichissement annonce « analysés » des messages non persistés

Tests (`ImapServiceEnrichmentCoverageTests`) :
- `EnrichEmailsAsync_WhenTheDatabaseRejectsTheMail_ReportsItUnreachableNotAnalysedAsync`
- `EnrichEmailsAsync_WhenTheBodyCannotBeBuilt_ReportsItUnreachableNotAnalysedAsync`
- `EnrichEmailsAsync_WhenPersistenceIsCancelled_ReportsTheMailUnreachableNotAnalysedAsync`
- `EnrichEmailsAsync_WhenTheMailIsPersisted_ReportsItAnalysedAsync` (contre-épreuve nominale)

RED :
```
Échoué ...EnrichEmailsAsync_WhenTheDatabaseRejectsTheMail_ReportsItUnreachableNotAnalysedAsync
   Expected: EnrichmentOutcome { Requested = 1, AlreadyAnalysed = 0, Analysed = 0, Unreachable = 1, NothingReachable = True }
   Actual:   EnrichmentOutcome { Requested = 1, AlreadyAnalysed = 0, Analysed = 1, Unreachable = 0, NothingReachable = False }
Échoué ...EnrichEmailsAsync_WhenTheBodyCannotBeBuilt_ReportsItUnreachableNotAnalysedAsync   (même écart)
Échoué ...EnrichEmailsAsync_WhenPersistenceIsCancelled_ReportsTheMailUnreachableNotAnalysedAsync   (même écart)
```
GREEN : application.tests filtre Enrich|ImapService → 343/343. Build 0 erreur.
Commit : `a4f9aa8d`

#### AUD-57 — Résumé IA d'un mail non enrichi jamais persisté, refacturé à chaque ouverture

Tests (`EmailSummaryServiceTests`, cache d'essai `RecordingCache` sérialisant en JSON) :
- `ProcessEmailSummariesAsync_NonEnrichedMailOpenedTwice_CallsTheAiOnce` (reproduction)
- `ProcessEmailSummariesAsync_WhenTheContentChanges_SummarizesItAgain` (clé liée à l'empreinte du texte résumé)
- `ProcessEmailSummariesAsync_WhenSummaryPersistenceFails_CachesNothing` (pas d'échec en cache)
- `ProcessEmailSummariesAsync_WhenTheAiAnswersNothing_CachesNothing` (pas d'échec en cache)

RED (constructeur étendu au préalable, sans comportement) :
```
Échoué ...EmailSummaryServiceTests.ProcessEmailSummariesAsync_NonEnrichedMailOpenedTwice_CallsTheAiOnce
   Assert.Single() Failure: The collection contained 2 items
```
GREEN : application.tests filtre EmailSummaryService|PromptTemplateInjection → 35/35 ; api.tests MailSummaryTemplateInjection|MailControllerTests → 180/180. Build 0 erreur.
Commit : `1ad4f2fe`

#### AUD-47 — Archivage « Envoyés » rejoué de façon non idempotente

Tests (`tests/mss.mail.application.tests/Services/Imap/ImapServiceSentArchiveIdempotenceTests.cs`) :
- `AppendToSentAsync_CloseFailsAfterSuccessfulAppend_ReturnsSuccess`
- `ArchiveWithRetryAsync_CloseFailsAfterSuccessfulAppend_AppendsExactlyOnce`

RED :
```
Échoué ...AppendToSentAsync_CloseFailsAfterSuccessfulAppend_ReturnsSuccess
   Assert.True() Failure — Expected: True  Actual: False
Échoué ...ArchiveWithRetryAsync_CloseFailsAfterSuccessfulAppend_AppendsExactlyOnce
   NSubstitute.Exceptions.ReceivedCallsException : Expected to receive exactly 1 call matching:
	AppendAsync(any FormatOptions, any IAppendRequest, any CancellationToken)
   Actually received 3 matching calls
```
GREEN : 2/2 ; zone `ImapService|SentArchive` 263/263 verts. Build sln 0 erreur.
Commit : 079769c6

#### AUD-53 — `POST diagnostics/test-similarity` toujours 500

Tests :
- `tests/mss.mail.integration.tests/Api/TestSimilarityEndpointIntegrationTests.cs` (Postgres Testcontainers, pipeline DI + GlobalExceptionHandler, règle 1b) :
  `TestSimilarity_OnNonEmptyMailbox_Returns200WithTheDocuments`, `TestSimilarity_WithMaxResults_ReadsABoundedNumberOfRows`
- `tests/mss.mail.api.tests/Controllers/V1/AiDiagnosticsControllerCoverageTests.cs` : `TestSimilarity_WithHugeMaxResults_ReadsAtMostTheDiagnosticRowCap`

RED :
```
Échoué ...TestSimilarity_OnNonEmptyMailbox_Returns200WithTheDocuments
   Assert.Equal() Failure: Values differ  Expected: OK  Actual: InternalServerError
Échoué ...TestSimilarity_WithMaxResults_ReadsABoundedNumberOfRows
   Assert.Equal() Failure: Values differ  Expected: OK  Actual: InternalServerError
```
(le test de plafond unitaire ne compilait pas avant correctif : le paramètre `maxRows` n'existait pas)
GREEN : integration `TestSimilarity|SemanticSearchRepository` 38/38 ; api `AiDiagnostics` 17/17 ; application `RepositoryTests` 47/47. Build sln 0 erreur.
Commit : 33401ca2

#### AUD-54 — Consommation de tokens fausse

Tests (`tests/mss.mail.application.tests/Services/Ai/AiConversationTokenUsageTests.cs`) :
- `StreamChatAsync_WhenProviderReportsUsage_FinalEventCarriesTheProviderCounts`
- `StreamChatAsync_WithoutReportedUsage_EstimatesAPositivePromptCount`
- `CreateConversationAsync_InitialSummaryUsage_IsCountedInTotalTokensUsed`
- `StreamChatAsync_RunningSummaryUsage_IsCountedInTotalTokensUsed`

RED :
```
Échoué ...StreamChatAsync_WhenProviderReportsUsage_FinalEventCarriesTheProviderCounts
   Assert.Equal() Failure: Values differ  Expected: 1234  Actual: 0
Échoué ...StreamChatAsync_WithoutReportedUsage_EstimatesAPositivePromptCount
   Assert.True() Failure  Expected: True  Actual: False
Échoué ...CreateConversationAsync_InitialSummaryUsage_IsCountedInTotalTokensUsed
   Assert.Equal() Failure: Values differ  Expected: 340  Actual: 0
Échoué ...StreamChatAsync_RunningSummaryUsage_IsCountedInTotalTokensUsed
   Assert.Equal() Failure: Values differ  Expected: 2910  Actual: 10
```
GREEN : 4/4 ; zone application `Services.Ai` 86/86 ; api `AiChat|Architecture` 39/39. Build sln 0 erreur.
Commit : fb9f8c12

#### AUD-56 — Comparaison des tags IA sensible à la casse

Tests (`tests/mss.mail.application.tests/Ai/EmailTaggingCaseInsensitiveTests.cs`) :
- `SuggestTagsAsync_TagInAnotherCase_ReturnsTheCanonicalLabel` (Theory ×5 : urgent, URGENT, très urgent, TRÈS URGENT, important)
- `SuggestTagsAsync_UnknownTag_ReturnsNoTag`
Test existant ajusté : `EmailTaggingServiceTests.ParseTagsFromResponseWithInvalidTagVariantsShouldReturnEmpty` — retrait des cas "urgent"/"URGENT" (ils figeaient le défaut).

RED :
```
Échoué ...SuggestTagsAsync_TagInAnotherCase_ReturnsTheCanonicalLabel(modelTag: "urgent", canonicalTag: "Urgent", expectedLevel: Urgent)
   Assert.Single() Failure: The collection was empty
(idem pour URGENT, très urgent, TRÈS URGENT, important — 5/5 rouges)
```
GREEN : zone `Tagging|PromptTemplateInjection|AddNewMailConsumer` 69/69. Build sln 0 erreur.
Commit : 74c048b1

#### AUD-66 — Retours hors ProblemDetails restants

**Tests** (RED obtenu en stashant uniquement les 5 contrôleurs `src/Api/Controllers/V1/{AiChat,Contact,Draft,Mail,Search}Controller.cs`) :
- Intégration (pipeline DI réel + GlobalExceptionHandler) — `tests/mss.mail.integration.tests/Api/RuleTwelveRemainingResponsesIntegrationTests.cs` :
  `GetMailsByTag_WhenReadFailsBeforeStreaming_Returns500ProblemJson`, `SendDraft_WithAnUnmappedOutcome_Returns500ProblemJson`,
  `InvalidContactModel_Returns400ProblemJson_NamingOnlyTheField` (×4), `InvalidModel_Returns400ValidationProblemJson` (×3 : ai/conversations, search/semantic, search/patient).
- Unitaires (mss.mail.api.tests) : `MailControllerTests.GetMailsByTag_{FailureBeforeFirstFlush_PropagatesForTheGlobalHandler,CancelledBeforeFirstFlush_PropagatesForTheCentral499}`,
  `DraftControllerCoverageTests.SendDraft_UnknownOutcome_ThrowsForTheGlobalHandler`, `ContactControllerTests.{Create,CreateGroup}_WithInvalidModelState_ThrowsValidation`,
  `ContactControllerCoverageTests.{Update,UpdateGroup}_WithInvalidModelState_ThrowsValidationWithoutReading`,
  `SearchControllerTests.{SemanticSearch,SearchByPatient}_WhenModelInvalid_ReturnsValidationProblem`, `AiChatControllerTests.CreateConversation_WhenModelInvalid_ReturnsValidationProblem`.

**RED** (ancien code) :
```
Intégration : Échoué! - échec : 8, réussite : 1, total : 9
  Échoué ...InvalidContactModel_Returns400ProblemJson_NamingOnlyTheField(POST /api/v1/contact ...)   (×4 routes contact)
  Échoué ...InvalidModel_Returns400ValidationProblemJson(POST /api/v1/ai/conversations ...)         (×3 routes)
  Échoué ...GetMailsByTag_WhenReadFailsBeforeStreaming_Returns500ProblemJson
   Assert.Equal() Failure: Strings differ
   Expected: "application/problem+json"
   Actual:   "application/json"
Unitaires : Échoué! - échec : 10, réussite : 62, total : 72 (les 10 tests ci-dessus)
```
Note : `SendDraft_WithAnUnmappedOutcome_Returns500ProblemJson` était déjà vert sur l'ancien code — le `StatusCode(500)` nu
(`IClientErrorActionResult`) est converti en ProblemDetails par le mapping client-error MVC. Le correctif (issue non mappée →
`InvalidOperationException` → GlobalExceptionHandler) aligne la voie sur la règle 12 ; le RED est porté par le test unitaire.

**GREEN** : build 0 erreur ; intégration 9/9 ; api.tests contrôleurs touchés (Mail/AiChat/Contact/Search/Draft) 259/259 ;
Filters/ErrorHandling/Account/Guard/Architecture 141/141.

**Commit** : `51b43d19`

## Sonar log

Mode A (chaîné depuis `/develop`), serveur SonarQube 25.6.0 (`sonar.token`), projet
`healthplatform-api-mail`. 4 analyses complètes (begin → build Release → 5 passes
OpenCover → end), dont une rejouée (voir « Incident » plus bas).

**Provenance** : la new-code period du projet est `PREVIOUS_VERSION` depuis le
2026-04-17. **Toutes** les issues ouvertes du projet tombent donc dans le new code
au sens Sonar. Phase 1 = les findings posés sur des lignes **ajoutées par cette
branche** (`git diff -U0 origin/develop...HEAD`, puis `git blame` sur les cas limites).
Phase 2 = tout le reste, blacklist appliquée.

- Phase 1 (lignes de task-342) : ✓ **0 finding restant** sur les lignes de la branche. Couverture des lignes et conditions ajoutées = **96,5 %** (434/439 lignes, 175/192 conditions), au-dessus de la cible de 95 % (94,4 % avant les nouveaux tests)
- Phase 1 — Issues fixées : **9**, toutes des code smells (0 bug, 0 vulnérabilité, 0 hotspot sur les lignes de la branche) :
  S2302 ×1, S125 ×1, S3267 ×1, S4136 ×2, xUnit1045 ×2, S2699 ×2. Commits `460bf032` et `029575bf`
- Phase 1 — Tests ajoutés : **22 cas** (7 + 15) — `AiTokenUsageReaderTests` (7), et `UserMailServerHostPolicyTests` (plages internes restantes, voisins publics, résolution vide ou `ArgumentException`, hôte absent). Commit `a164a56a`
- Phase 2 (legacy) : itérations **2 / 5**, arrêt faute de lot traitable en batch (voir le reliquat)
  - Itération 1 : S103 ×11, S125 ×2, S4027 ×2, S113, S2302 (C#), plus les bugs python S3923 et S1244. Commits `deabebc0`, `ad18486c`, `27c68358`. Issues **94 → 75** (−20 %)
  - Itération 2 : python S1192 ×7, S3358 ×4, S1172 ×2 ; javascript S6582 ×3, S6035, S4624 ×2. Commits `be405b08`, `796474f9`, `01ccff57`. Issues **75 → 56** (−25 %)
- Phase 2 — Issues fixées : **38**
- Phase 2 — Issues restantes : **56** (acceptation best-effort) :
  - python/javascript S3776 ×24 : complexité cognitive, relève de `/sonar-s3776`
  - javascript S1940 ×20 : `!(x > 0)` est une **garde volontaire contre NaN/undefined**. `x <= 0` changerait le comportement, donc non corrigé
  - C# S4462 ×3 (`AuditService`, sync-over-async), S2952 ×2 (`MailClientSession` : disposition des verrous dans la fermeture asynchrone de task-335, pas dans `Dispose`), S138 ×3 (méthodes longues antérieures), S1067 ×1 : structurel ou comportemental, hors batch
  - javascript S2486 ×3 : `catch` volontairement muets, commentés
- Hotspots : 13 `TO_REVIEW` dans la new-code period, **aucun sur une ligne de task-342** (k6 PRNG S2245, `http://` des tests python S5332, regex S5852, Dockerfile S6504, logger S4792). Leur statut est laissé à la revue humaine
- Build / tests : ✓ green. Dernière analyse : domain 190, application 3 317, infrastructure 665, api 1 031, integration 645 (+16 ignorés) ; python `unittest` 390 OK ; `node --test` 121 OK. Poussé jusqu'à `01ccff57` (pre-push vert)
- Incident (analyse 3) : passe d'intégration OpenCover **figée ~20 min**. Seul le conteneur dovecot était monté, sans Postgres, et le testhost ne consommait pas de CPU. Arbre tué par l'orchestrateur. Rejouée avec `--blame-hang-timeout 8m` : **aucun test figé** (645/645, deux fois de suite). Il s'agit d'un démarrage testcontainers bloqué, transitoire, sans lien avec un test de la branche. Aucune exclusion `--filter` nécessaire
- Rouge isolé (analyse 1) : `PgBouncerTransactionPoolingTests.ConcurrentClients_AreMultiplexed_OntoBoundedPostgresBackends`, vert seul (7/7) et vert aux analyses suivantes. Fichier non touché par la branche : flaky de charge

### KPIs qualité (baseline → final)

Baseline = analyse 1 de cette branche (368ba75b, 2026-09-28 18:44 UTC). Pour
mémoire, la dernière analyse du serveur avant le run portait sur une autre
révision (64e36465, 2026-09-27) : bugs 2, code smells 89, couverture 91,6 %,
new_coverage 92,6 %, fiabilité C.

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | ERROR | ERROR | → (`new_violations` 103 → 56, `new_security_hotspots_reviewed` 0 %) |
| New coverage | 98,4 % | 98,4 % | ±0 pt |
| Couverture des lignes de task-342 | 94,4 % | 96,5 % | +2,1 pt |
| Bugs | 4 | 2 | −2 |
| Vulnerabilities | 0 | 0 | ±0 |
| Security hotspots | 15 | 15 | ±0 |
| Code smells | 99 | 54 | −45 |
| Coverage (projet) | 98,2 % | 98,2 % | ±0 pt |
| Duplication | 0,4 % | 0,4 % | ±0 pt |
| Reliability / Security / Maintainability | D/A/A | D/A/A | → (D = S2952 legacy de `MailClientSession`) |

Le QG reste ERROR à cause de la dette antérieure de la période
`PREVIOUS_VERSION` (issues listées au reliquat, et hotspots non revus). La
branche n'y contribue plus aucune issue.

## Lint log

- `/lint-angular` : **skipped** — `client-angular` non listé dans `**Repos**:`, non touché par la task.
- `/lint-mobile` : **skipped** — `client-mobile` non listé dans `**Repos**:`, non touché par la task.

## Visual verify log

- `/verify-visual` : **skipped** — aucun écran `client-mobile` touché (task api-mail uniquement).

## Timings

*(généré par `tools/timing/report.sh --task task-342 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 6 min 56 s | — | — | — | — |
| /develop | ok | 5 h 31 min | 20 (5 min 18 s) | 97 (37 min 46 s) | — | api-mail 20B/97T |
| /sonar | ok | 1 h 11 min | 8 (3 min 58 s) | 28 (36 min 02 s) | 4 (8 min 12 s) | 3 itération(s), api-mail 8B/28T |
| /lint-angular | skipped | 1.9 s | — | — | — | client-angular non listé dans Repos, non touché |
| /lint-mobile | skipped | 2.9 s | — | — | — | client-mobile non listé dans Repos, non touché |
| /verify-visual | skipped | 1.6 s | — | — | — | aucun écran client-mobile touché |
| **Total cycle** | | **6 h 49 min** | **28 (9 min 16 s)** | **125 (1 h 13 min)** | **4 (8 min 12 s)** | |
