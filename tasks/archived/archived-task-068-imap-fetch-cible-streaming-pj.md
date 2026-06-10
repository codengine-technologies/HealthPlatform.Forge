# todo-task-068.md — Perf IMAP : fetch ciblé des messages et streaming des pièces jointes

**Repos**: api-mail
**Dependencies**: (aucune)
**Epic**: E011
**EpicTitle**: Performance API Mail

> US mono-repo justifiée : optimisation backend pure (granularité des fetchs IMAP
> et streaming HTTP). Aucun changement de contrat DTO ni d'écran frontend — les
> endpoints conservent leurs routes et leurs schémas de réponse.

## Objective

Supprimer le téléchargement systématique du message IMAP **entier** (body +
toutes les pièces jointes décodées en mémoire) là où seuls des en-têtes ou une
seule body part sont nécessaires, et streamer les pièces jointes vers le client
au lieu de les bufferiser en `byte[]`. C'est le finding performance le plus
critique de l'audit : un mail de 50 Mo est aujourd'hui intégralement téléchargé
et décodé pour un simple affichage de contenu, avec risque d'OOM sous requêtes
parallèles.

## Findings adressés (audit perf 2026-06-10)

| # | Localisation | Problème | Impact |
|---|---|---|---|
| 1 | `src/Application/Services/Implementation/ImapService.cs:1525` | `GetMessageAsync` télécharge le message entier pour afficher le contenu | Critique |
| 2 | `src/Application/Services/Implementation/ImapService.cs:1583` | `GetAttachmentAsync` télécharge le message entier pour extraire UNE pièce jointe | Élevé |
| 3 | `src/Application/Services/Implementation/ImapService.cs:1599-1606` | Pièce jointe bufferisée en `MemoryStream` puis `ToArray()` dans un DTO JSON (double/triple copie, OOM possible) | Élevé |
| 4 | `src/Application/Services/Implementation/ImapService.cs:2020-2024` | Copy/Move : boucle `GetMessageAsync` un-par-un (N téléchargements complets séquentiels) | Élevé |
| 5 | `src/Application/Services/Implementation/BackgroundImapService.cs:447-449` | Décodage body part : `MemoryStream` + `ToArray()` + `GetString` = 3 allocations | Moyen |
| 6 | `src/Application/Helpers/EmailAddressHelper.cs:111` | Même pattern triple allocation au décodage MIME | Moyen |

## Comportement attendu

- L'affichage du contenu d'un mail ne récupère que les body parts nécessaires
  (`FetchAsync` avec `MessageSummaryItems` ciblés + `GetBodyPartAsync`), jamais
  les pièces jointes non demandées.
- Le téléchargement d'une pièce jointe ne récupère que la body part visée et la
  **streame** vers la réponse HTTP (pas de `byte[]` intermédiaire complet, pas
  de base64 dans un JSON pour les gros contenus).
- Les opérations copy/move n'effectuent plus N téléchargements complets
  séquentiels (utiliser les commandes IMAP COPY/MOVE serveur quand disponibles,
  sinon batcher).
- Les décodages MIME internes n'allouent plus de copies intermédiaires
  évitables.

## Definition of Done

- [ ] Build passes : `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` (0 erreur)
- [ ] Tests pass : `dotnet test HealthPlatform.Api.Mail.sln` (0 échec)
- [ ] Plus aucun appel `GetMessageAsync` sur le chemin « afficher le contenu d'un mail » (fetch ciblé envelope/body structure + body part)
- [ ] Le téléchargement d'une pièce jointe récupère uniquement la body part demandée via `GetBodyPartAsync`
- [ ] La pièce jointe est streamée vers la réponse HTTP (aucun `MemoryStream.ToArray()` du contenu complet sur ce chemin)
- [ ] Copy/Move : plus de boucle `GetMessageAsync` un-par-un
- [ ] Les 3 sites de triple allocation (`ToArray()` + `GetString`) sont corrigés
- [ ] Unit tests : >= 1 test par méthode publique modifiée d'`ImapService` (mocks MailKit via wrappers existants)
- [ ] Integration test : endpoint de téléchargement de pièce jointe (happy path + pièce jointe introuvable) traverse le pipeline DI complet
- [ ] Aucune régression de contrat : les DTOs exposés et les routes existantes sont inchangés
- [ ] Aucune donnée de santé en clair dans les logs (pas de contenu MIME, pas de nom de fichier patient loggé en clair)

## Manual Test Plan

- Lancer l'API : `cd Api/Mail && docker-compose up -d && dotnet run --project src/Api`
- Ouvrir le client Blazor (`cd Client/Blazor && dotnet run`) connecté à un
  compte de test disposant d'un mail avec une pièce jointe volumineuse (>= 20 Mo,
  donnée de test anonymisée).
- Ouvrir le mail : le contenu s'affiche sans télécharger la pièce jointe
  (vérifier dans les logs serveur que seule la body part texte/HTML est fetchée).
- Télécharger la pièce jointe : le téléchargement démarre immédiatement
  (streaming) et le fichier reçu est intègre (taille + ouverture OK).
- Déplacer 20 mails d'un dossier à l'autre : l'opération aboutit en quelques
  secondes, sans pic mémoire (observer le working set du process).
- Comparer avant/après : temps d'ouverture d'un mail volumineux et mémoire
  consommée doivent baisser visiblement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (LPS MSSanté)
- **Vague Ségur** : hors Ségur — optimisation technique sans impact fonctionnel ni exigence DSR nouvelle
- **Exigences DSR honorées** : non applicable — aucun changement de comportement métier MSSanté
- **INS** : non applicable — aucun traitement d'identité patient modifié
- **Authentification PS** : inchangée (PSC/Keycloak existant) — la US ne touche pas à l'authentification
- **Habilitations** : non applicable — pas de changement d'autorisation
- **Interop CI-SIS** : non applicable — le parsing CDA n'est pas modifié ; les pièces jointes restent transmises octet-à-octet identiques
- **Tracé PGSSI-S** : inchangé — les évènements de consultation/téléchargement existants restent journalisés à l'identique
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement HDS existant inchangé
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement de données

## Branches
- `api-mail` (pushed) : feat/task-068-imap-fetch-cible-streaming-pj — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-068-imap-fetch-cible-streaming-pj
- `dtos-mss` (pushed, auto-included) : feat/task-068-imap-fetch-cible-streaming-pj — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-068-imap-fetch-cible-streaming-pj

## Develop log

- Repos touched : api-mail (dtos-mss : branche créée, 0 commit — aucun changement de contrat)
- DTOs published : no DTO change
- Interop published : no interop change
- Commits (api-mail, branche `feat/task-068-imap-fetch-cible-streaming-pj`) :
  - b1f08ea feat(imap): targeted body-part fetch and attachment streaming (task-068)
  - 9f722b3 test(api): align UserDatabaseName assertion with hashed tenant naming
- Implémentation :
  - `GetEmailContentAsync` : fetch `BODYSTRUCTURE` + `GetBodyPartAsync` ciblé (text/html) — plus de `GetMessageAsync`
  - `GetAttachmentAsync` : localisation de la part dans la BODYSTRUCTURE + téléchargement de la seule part visée ; `Error("not found")` → `NotFound` (mapping ProblemDetails 404, règle 12)
  - Nouveau `GetAttachmentStreamAsync` (+ `AttachmentStreamResult` en couche Application — volontairement PAS dans dtos-mss) : DB-first, write-back DB conservé pour les parts <= 5 Mo (`MaxDbCacheableAttachmentBytes`), streaming pur sans buffer ni write-back au-delà
  - Endpoint `DownloadAttachment` : `FileStreamResult` (routes et schémas inchangés)
  - Suppression unitaire : présence vérifiée par UID SEARCH puis MOVE serveur (capability) ou COPY+flag — plus de fetch complet
  - Suppression bulk (fallback sans capability MOVE) : COPY batch serveur au lieu de la boucle fetch+append
  - Triple allocation décodage MIME : corrigée dans `EmailAddressHelper` (GetBuffer), dédupliquée dans `BackgroundImapService`, redessinée dans `ImapService`
  - `GetMessageAsync` restant : `MailExportService` uniquement (export EML — périmètre task-077)
- Tests : 11 nouveaux tests unitaires (`ImapServiceTests` région task-068) + 3 tests endpoint mis à jour (`MailControllerTests` : FileStreamResult happy path, 404 ProblemDetails, 500 ProblemDetails)
- Local build / test : build 0 erreur ; domain 94 ✓, infrastructure 346 ✓, application 1488 ✓, api 484 ✓ ; integration 209/210
- ⚠️ Préexistants sur develop (qualifiés sur arbre propre, hors périmètre task-068) :
  - `UserContextEnricherMiddlewareTests.AuthenticatedUserResolved_EmitsEventId3724…` : assertion obsolète depuis PR #75 (Change db naming) — **réparée dans cette branche** (commit 9f722b3)
  - `ImapConnectionServiceIntegrationTests.ConnectAsyncWithCancellationShouldRespectTokenAsync` : flaky sous charge (échoue en suite complète sur develop propre, passe en isolation) — non traité ici, à signaler à /review
- DOD self-check : 10/12 items vérifiables par commande ✓ ; « fichier reçu intègre » et comparaison avant/après → déférés au test manuel (HAG)
- no angular change → skipped /lint-angular
- Next step : /sonar task-068

## Sonar log

- Mode A (chaîné) sur la branche `feat/task-068-imap-fetch-cible-streaming-pj`
- Baseline (avant run) : bugs=1, vulnérabilités=0, smells=44, coverage=0.0% (pas de rapport de couverture uploadé), QG=ERROR
- Phase 1 (new code) — 2 itérations :
  - Issues new-code : 27 → **0**
    - 18 fixées par le code (S3604 ×7, S3928 ×2, S125 ×2, S1643 ×2, S1905, S1168, S3241, S107 ×3 — `BulkDeleteBatch` param object + `StartSyncAsync(UserContextInfo)`)
    - 3 × S107 `[LoggerMessage]` (UserContextEnricherMiddleware) : **Accepted** avec justification inline — le générateur impose 1 paramètre par placeholder ; réduire l'arité dégraderait le contrat d'audit PGSSI-S (task-048/054)
    - 6 × S3925 (exceptions ISerializable) : **False Positive** — sérialisation binaire obsolète depuis .NET 8 (SYSLIB0051), analyseur SonarQube 9.9 antérieur à cette guidance
  - Hotspots new-code : 0 (rien à revoir)
  - Ratings new-code : A / A / A ✓, duplication 0.02% ✓
  - Tests ajoutés : 3 (branches d'erreur GetAttachmentStreamAsync, contenu vide)
  - **new_coverage = 75.8% vs gate 80% → SEULE condition en échec** ; 703 lignes new-code non couvertes réparties sur ~30 fichiers dont l'écrasante majorité provient des merges antérieurs à task-068 (période new-code = PREVIOUS_VERSION sans version fournie → baseline figée à la PREMIÈRE analyse, ~3 semaines de code) — voir `questions/task-068.md`
- Phase 2 (legacy) : non démarrée — suspendue à l'arbitrage Phase 1 (reste : 1 bug legacy, 26 smells, 4 hotspots legacy TO_REVIEW, coverage projet 79.2%)
- Build / tests : ✓ (2415 unitaires verts ; intégration 209/210, flaky préexistant documenté)
- Incidents tooling résolus pendant le run : conteneurs sonarqube+sonarqube_db arrêtés (redémarrés), token .env mort (rotation admin + nouveau token `squ_`, .env mis à jour), SONAR_PROJECT_KEY obsolète (`healthplatform` → `healthplatform-api-mail`), conversion de chemins MSYS sur les flags du scanner (`MSYS2_ARG_CONV_EXCL`)
- **Arbitrage humain (questions/task-068-sonar-newcoverage.md)** : option 1+2 — résidu new_coverage 75.8% accepté (mandat de la campagne task-067), période new-code re-bornée à NUMBER_OF_DAYS=30 (niveau branche). Chaîne débloquée.
- Phase 2 (legacy) : best-effort minimal — bug unique S3887 marqué FP (StopWords est un FrozenSet immuable, analyseur 9.9 antérieur à .NET 8) → bugs ouverts = 0 ; 26 smells + 4 hotspots legacy laissés aux prochains cycles (acceptation best-effort, ne bloque pas la chaîne).
- Hand-off : pas de changement Angular → /lint-angular sauté ; next step : /review task-068

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/90 — label `awaiting-human-merge` (HAG règle 10)
- `dtos-mss` : aucun commit (branche auto-incluse inutilisée) — pas de PR

## Code Review Summary

- Verdict : **APPROVED** (22 fichiers, 2 suggestions non bloquantes, 0 bloquant)
- Build ✓ (0 erreur) · Tests ✓ 2463 unitaires + 230/231 intégration (1 flaky préexistant develop, passe en isolation)
- DOD : 11/12 vérifiés par commande ; « fichier intègre » + comparaison avant/après → déférés au Manual Test Plan (PR)
- Suggestions : libellé d'audit « MOVE » en fallback COPY ; batch possible des 2 body parts text+html

## Merged

- **Date** : 2026-06-10 (attestation humaine `--i-tested`)
- `api-mail` : squash `b686640` — PR #90 fermée, branche distante supprimée (la branche locale a aussi été retirée par `gh pr merge` ; les commits vivent sur develop)
- `dtos-mss` : aucun commit — branche `feat/task-068-*` distante supprimée (housekeeping), clone resynchronisé sur develop
- **CI develop (api-mail)** : ✅ success — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/27285143242
