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
  jeton PSC présenté au serveur en OAuth2. → allowlist exploitant, refus des IP privées / loopback.
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
- [ ] AUD-42 : `SaveSettings` avec un hôte hors allowlist ou une IP privée → 400 ; aucune connexion tentée
- [ ] AUD-33 : test sur **Postgres réel** (Testcontainers) — B → A et détachement de la boîte par défaut réussissent
- [ ] AUD-36 : deux mails introduisant la même catégorie en parallèle → les deux complètement traités
- [ ] AUD-41 : deux pièces homonymes → téléchargeables séparément, ZIP avec deux contenus distincts
- [ ] AUD-28 : mail reçu à 00 h 30 heure de Paris sur un hôte UTC → présent dans « reçus aujourd'hui »
- [ ] Tests d'intégration endpoints (règle 1b) pour les routes modifiées (`settings`, rattachement de boîte, téléchargement de pièce jointe, `test-similarity`)
- [ ] Migration éventuelle (AUD-33) auditée selon la règle 7c
- [ ] Aucune donnée de santé ni adresse en clair ajoutée dans les logs

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` ; Blazor et mobile connectés à des boîtes de test.
2. **Lot A** : enregistrer un serveur IMAP personnalisé `redis:6379` → refus ; détacher la boîte courante sur mobile puis recharger la gestion des boîtes → la liste s'affiche (plus de 403) ; télécharger en ZIP un mail dont une pièce s'appelle `..\x.bat` → entrée assainie.
3. **Lot B** : praticien à deux boîtes, définir B par défaut puis revenir à A → succès ; recevoir un mail avec deux `resultat.pdf` → les deux s'ouvrent, distincts.
4. **Lot C** : ouvrir un mail avant la fin de son analyse, attendre l'enrichissement, rouvrir → les documents CDA apparaissent ; mail de test daté de 00 h 30 → visible dans « reçus aujourd'hui ».
5. **Lot D** : `POST /api/v1/diagnostics/test-similarity` sur une boîte non vide → 200 ; forcer une erreur sur la route des tags → réponse `application/problem+json`.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville, biologie
- **Vague Ségur** : V2
- **Exigences DSR honorées** : non applicable — fiabilité et sécurité de fonctionnalités existantes
- **INS** : non applicable
- **Authentification PS** : PSC / e-CPS inchangée ; le jeton PSC n'est plus présenté à un serveur hors allowlist (AUD-42)
- **Habilitations** : inchangées ; routes de gestion des boîtes accessibles même avec une boîte courante devenue invalide
- **Interop CI-SIS** : Annuaire Santé FHIR R4 (`PractitionerRole`) — lecture de tous les rôles (AUD-64)
- **Tracé PGSSI-S** : inchangé ; les erreurs rendues passent par `ProblemDetails` sans donnée
- **Consentement patient** : non applicable
- **Référentiels métier** : Annuaire Santé (RPPS)
- **Hébergement HDS** : oui — environnement inchangé
- **AIPD / impact RGPD** : inchangé
