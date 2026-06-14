# todo-task-081.md — Observabilité : timing par commande IMAP dans GetFolderQuery

**Repos**: api-mail
**Dependencies**: aucune
**Epic**: E009

> US mono-repo justifiée : pur ajout d'observabilité (télémétrie) sur le
> chemin IMAP de listage de dossier. Aucun changement de contrat, d'UI ni de
> comportement fonctionnel.

## Objective

Permettre de diagnostiquer précisément quelle commande IMAP consomme le temps
lors des listages de dossier lents (jusqu'à ~68 s observées en production sur
`GetFolderQuery:INBOX`). Aujourd'hui les logs n'émettent qu'un total agrégé
après les 4 commandes, ce qui permet d'affirmer que le coût est dans
STATUS/SELECT/SEARCH/CLOSE (et **pas** dans un FETCH — `GetFolderQueryAsync`
n'en fait aucun) mais **pas** d'identifier la commande coupable.

On instrumente donc chaque commande IMAP de `GetFolderQueryAsync` avec un
chronomètre dédié, exposé en tags d'`Activity` (OpenTelemetry) et en log
structuré, afin que la prochaine reproduction lente révèle immédiatement le
suspect (SEARCH vs SELECT vs STATUS vs CLOSE).

## Contexte (audit Seq 2026-06-11)

- Trace `e80b0a9a…` : `HoldTimeMs=68071` ≈ `ElapsedMs=68716` → quasi aucune
  attente de verrou ; le temps est passé **à exécuter** les commandes IMAP.
- La requête SEARCH (`NotSeen AND DeliveredAfter(today)`) a renvoyé **0 UID**
  sur un INBOX de **354 messages** → le coût n'est ni la sérialisation ni le
  volume de données, mais le round-trip IMAP contre le serveur MSSanté.
- Aucun `IProtocolLogger` MailKit ni timing par commande n'existe actuellement
  (vérifié dans le code).

## Localisation

`src/Application/Services/Implementation/ImapService.cs` — méthode
`GetFolderQueryAsync` (~ligne 580), séquence sous le verrou :

```csharp
await imapFolder.StatusAsync(StatusItems.Count | StatusItems.Unread | StatusItems.UidNext, ct); // STATUS
await imapFolder.OpenAsync(FolderAccess.ReadOnly, ct);                                            // SELECT/EXAMINE
var uids = await imapFolder.SearchAsync(query, ct);                                               // SEARCH
await imapFolder.CloseAsync(false, ct);                                                           // CLOSE
```

## Comportement attendu

- Chaque commande IMAP (`STATUS`, `SELECT`/`OPEN`, `SEARCH`, `CLOSE`) est
  chronométrée individuellement via un `Stopwatch`.
- Les durées sont exposées en tags sur l'`Activity` Imap déjà ouverte par
  `TelemetryExtensions.StartImapActivity("GetFolderQuery", folderPath)` :
  `imap.status_ms`, `imap.select_ms`, `imap.search_ms`, `imap.close_ms`.
- Le log `[ListFolder]` existant est enrichi des 4 durées (en plus de
  `Count`/`StatusCount`/`UidNext`/`Sample` déjà présents), de sorte que la
  ventilation soit requêtable dans Seq sans dépendre du tracing.
- Aucun changement de comportement : mêmes commandes, même ordre, même
  résultat fonctionnel. Le chronométrage n'altère pas le flux (pas de
  court-circuit, pas de nouvelle exception).
- Pas de `IProtocolLogger` MailKit activé par défaut (volume + risque de fuite
  de données). On reste sur des durées agrégées par commande.

## Definition of Done

- [x] Build passes : `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` (0 erreur)
- [x] Tests pass : `dotnet test HealthPlatform.Api.Mail.sln` (0 échec hors flaky IMAP cancel documenté)
- [x] 4 tags d'Activity ajoutés (`imap.status_ms`, `imap.select_ms`, `imap.search_ms`, `imap.close_ms`) dans `ActivityTags` et posés dans `GetFolderQueryAsync`
- [x] Log `[ListFolder]` enrichi des 4 durées par commande
- [x] Unit test : `GetFolderQueryAsync` happy path vérifiant que les 4 commandes sont appelées et que le log/tags de durée sont émis (via wrappers/mocks IMAP)
- [x] Unit test : chemin d'échec (folder non ouvrable) ne casse pas le chronométrage
- [x] Aucun changement de signature publique ni de contrat DTO
- [x] Aucune donnée de santé en clair dans les logs (uniquement durées et compteurs)

## Manual Test Plan

- Lancer l'API : `cd Api/Mail && docker-compose up -d && dotnet run --project src/Api`
- Se connecter avec un compte MSSanté de test (données anonymisées) disposant
  d'un INBOX volumineux.
- Ouvrir la boîte de réception dans l'application (déclenche les endpoints
  `GetFolderToday` / `GetFolderNotSeenToday` → `GetFolderQuery:INBOX`).
- Dans Seq, ouvrir l'évènement `[ListFolder] IMAP SEARCH for INBOX …` et
  vérifier la présence des 4 nouvelles propriétés de durée
  (`imap.status_ms`, `imap.select_ms`, `imap.search_ms`, `imap.close_ms`).
- Confirmer que la somme des 4 durées est cohérente avec le `HoldTimeMs` du
  verrou IMAP de la même trace, et identifier la commande dominante lors d'un
  listage lent.
- Vérifier qu'aucune donnée de santé n'apparaît dans les nouvelles propriétés.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (LPS MSSanté)
- **Vague Ségur** : hors Ségur — observabilité technique
- **Exigences DSR honorées** : non applicable — comportement MSSanté inchangé
- **INS** : non applicable
- **Authentification PS** : inchangée
- **Habilitations** : non applicable
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : ajout de métriques techniques (durées de commandes IMAP) — aucune donnée de santé
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement HDS existant inchangé
- **AIPD / impact RGPD** : inchangé — seules des durées et compteurs sont journalisés

## Branches
- `api-mail` (pushed) : feat/task-081-imap-command-timing — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-081-imap-command-timing
- `dtos-mss` (pushed, auto-incluse) : feat/task-081-imap-command-timing — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-081-imap-command-timing

## Develop log

- Repos touched : api-mail (dtos-mss : branche auto-incluse, 0 commit, pas de PR)
- DTOs / Interop published : no change
- Commits :
  - api-mail : 7374a37 feat(telemetry): per-command IMAP timing in GetFolderQuery
- Local build / test : ✓ build 0 erreur ; ImapServiceTests 50/50 verts (dont les 4 nouveaux, RED→GREEN) ; suite complète verte hors flaky pré-existants documentés — y compris les nouveaux flaky parallèles `CdaProcessingMetricsTests`/`MarkdownPdfRendererTests` issus du commit humain « Add metrics » (vérifiés verts en isolation ET sur re-run, intermittents en suite parallèle, mémoire mise à jour)
- Implementation notes :
  - 4 constantes `ActivityTags` (`imap.status_ms`, `imap.select_ms`, `imap.search_ms`, `imap.close_ms`) + tags posés sur l'Activity `GetFolderQuery` existante
  - `GetFolderQueryAsync` : un seul `Stopwatch` redémarré entre les 4 commandes (STATUS → SELECT → SEARCH → CLOSE), mesures hors construction du DTO et hors boucle UIDs ; aucun changement de flux ni d'ordre, aucune nouvelle exception possible (le timer est local, les tags posés après CLOSE uniquement sur le chemin succès)
  - Log `[ListFolder] IMAP SEARCH …` enrichi de `Timings: STATUS={ImapStatusMs}ms, SELECT=…, SEARCH=…, CLOSE=…` — ventilation requêtable dans Seq sans tracing
  - Pas d'`IProtocolLogger` MailKit (exigence US : volume + risque de fuite)
- Tests : 4 nouveaux test-first — happy path (4 commandes reçues + 4 durées dans le log), tags d'Activity capturés via `ActivityListener` sur la source Imap, folder non ouvrable (erreur propre, aucune commande émise), commande qui throw en milieu de séquence (erreur mappée, pas de masquage par le chronométrage)
- DOD self-check : 8/8 — build ✓, tests ✓, 4 tags ✓, log enrichi ✓, unit test happy ✓, unit test échec ✓, aucune signature publique ni DTO modifiée ✓ (diff = ImapService.cs + ActivitySources.cs + tests), uniquement durées/compteurs dans les nouveaux logs ✓
- no angular change → skipped /lint-angular
- Next step : /sonar task-081 (chaîne ensuite vers /review)

## Sonar log

- Phase 1 (new code) : ✓ Quality Gate **OK** après 1 itération — 1 seule issue new-code : S138 sur `CdaParsingService.ParseCdaDocument` (88 lignes — héritée du commit humain « Add metrics » squashé avec task-076, pas du code task-081) → extraction `BuildCdaDocumentDto` (refactor pur, tests CdaParsing verts), commit `c13532d`
- Phase 2 (legacy) : 0 itération / 5 — early-stop, dette nulle
- État final projet : 0 bug / 0 vulnérabilité / 0 smell / 0 hotspot, coverage **84,4 %**, Quality Gate OK
- Build / tests : ✓ Release 0 erreur ; seul échec du run = IMAP cancel flaky documenté
- no angular change → skipped /lint-angular
- Hand-off : /review task-081

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/103 — label `awaiting-human-merge`
- `dtos-mss` : aucune PR — branche auto-incluse, 0 commit

## Code Review Summary

**Verdict : APPROVED** (3 fichiers revus, 1 suggestion non-bloquante, 0 bloquant)

- `src/Application/Services/Implementation/ImapService.cs` — ✅ un seul `Stopwatch` redémarré entre les 4 commandes (STATUS → SELECT → SEARCH → CLOSE), mesures hors construction du DTO et hors boucle UIDs (attribution propre), tags posés après CLOSE sur le chemin succès uniquement ; flux, ordre et mapping d'erreur strictement inchangés. ⚠️ suggestion : une commande qui throw en milieu de séquence n'émet pas de durée partielle — le `HoldTimeMs` du verrou encadre toujours le total, acceptable pour l'objectif diagnostique
- `src/Application/Telemetry/ActivitySources.cs` — ✅ 4 constantes `ActivityTags` conformes au nommage de la US
- `src/Application/Services/Implementation/CdaParsingService.cs` — ✅ extraction de mapping pure (S138 hérité du commit « Add metrics »), commentaires task-034 préservés
- Tests — ✅ 4 significatifs : Received sur les 4 commandes + propriétés du log, capture des tags via ActivityListener, 2 chemins d'échec

Validation : build ✓ 0 erreur · tests ✓ (seul échec = IMAP cancel flaky documenté ; patient INS pagination même verte sur ce run) · DOD ✓ 8/8 · Sonar ✓ Quality Gate OK, 0 issue projet, coverage 84,4 %

## Merged

- Date : 2026-06-13
- `api-mail` : squash commit `d54d696` (PR #103 closed, branche remote supprimée, branche locale conservée)
- `dtos-mss` : aucune PR (0 commit task-081) — branche remote supprimée, clone resynchronisé sur `develop`
- develop CI : ✓ success — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/27468075420
