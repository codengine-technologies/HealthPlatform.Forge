# todo-task-273.md — L'arrivée sur le tableau de bord ne coûte plus un quart du temps serveur

**Repos**: api-mail
**Dependencies**: —
**Epic**: E015

## Objectif

L'arrivée sur le tableau de bord est **verte au SLO** (p50 11 ms, p95 476 ms
pour 300/1 500) et c'est précisément pour ça que personne ne la regarde :
c'est pourtant le **deuxième poste du temps serveur du palier 1000** —
**24,8 %** (14 615 s), juste derrière l'envoi
(`Api/Mail/tests/loadtest-k6/reports/2026-08-25/report-journey-1000-solo-postimap-20260825-151054.md`,
section « Axes d'amélioration » : « vert au SLO mais gros consommateur —
invisible d'un rapport qui ne lit que les percentiles »).

La ventilation multi-appels attribue le coût : sur les quatre appels du
geste, **`GET /mail/folders/{folder}` porte 59 % du temps de l'étape**
(8 630 s, p50 133 ms, p95 596 ms, n=40 655), devant `today` (3 393 s, p50
6 ms mais p95 469 ms — dispersion énorme), `folders` (2 324 s) et `coverage`
(267 s, négligeable). Dispersion p95/p50 de l'étape : **×45** — un coût qui
dépend de la charge ou de la donnée, pas un coût fixe.

C'est le geste **le plus fréquent du parcours** (162 620 appels sur le tir,
4 requêtes à chaque passage) : chaque milliseconde gagnée ici est multipliée
par un volume qu'aucune autre étape n'approche.

**⚠️ La cause n'est PAS encore établie — l'établir fait partie de l'US,
avant tout remède.** Cette EPIC a déjà payé une US écrite sur une cause
supposée (task-222, annulée). Faits mesurés disponibles pour démarrer :
`GetFolderQuery` attend 0,45 s (p95) sur le verrou `imap_session` et le
détient 1,7 s ; `GetFolderStatus` le détient 3,2 s ; à l'inverse la mémoire
du banc (2026-08-08) mesurait « l'ouverture du dossier est gratuite (7 ms) »
sur le chemin inbox — les deux lectures doivent être réconciliées par la
télémétrie (décomposition d'une requête représentative par `TraceId`,
task-243/256 pour la part base, verrous task-211 pour la part session).

**Pistes de remède à arbitrer une fois la cause établie** (aucune n'est
acquise) : mémoïsation courte des compteurs de dossier par praticien
(le dashboard relit des compteurs que `today`/`folder` viennent de calculer),
regroupement côté serveur des quatre appels en un, réduction du travail
IMAP sous le verrou de session. Un remède qui change le contrat des routes
impliquerait les frontends — **ce découpage-là repasserait par le PO**
(cette US est volontairement scopée backend, contrat d'API inchangé).

**Gain attendu** : l'appel `folder` pèse 8 630 s serveur sur le tir — une
division par deux du geste dashboard rend ~12 % du temps serveur total de la
plateforme, sans changer une ligne de front.

**Hors périmètre** : la page d'en-têtes de l'inbox (`GetMailsByUids`,
matérialisation dominée par les objets de fil — finding distinct, US à part
si le PO le décide) ; tout changement de contrat d'API ou de front.

## Definition of Done

- [ ] Build passes (0 errors), tests pass (0 failures) sur api-mail
- [ ] La cause du coût de `GET /mail/folders/{folder}` au volume du dashboard
      est **établie et écrite dans la task** (décomposition par phase :
      verrou / IMAP / base / matérialisation), AVANT le choix du remède
- [ ] Le remède retenu est appliqué **sans changement de contrat d'API**
      (mêmes routes, mêmes DTO) — les frontends ne sont pas touchés
- [ ] Un test d'intégration fige le comportement optimisé (ex. : deux
      arrivées dashboard successives du même praticien → la seconde ne
      repaie pas le travail identifié comme dominant ; adapter l'assertion
      à la cause établie)
- [ ] Si une mise en cache est retenue : sa péremption est bornée et testée
      (un nouveau message reçu est visible dans les compteurs au plus tard
      à l'expiration — la valeur du TTL est un choix PO à faire valider,
      proposer ≤ 30 s), et l'invalidation sur action du praticien
      (lecture, envoi, suppression) est testée
- [ ] `DbOperationScope`/verrous (task-211/243) continuent de mesurer le
      chemin optimisé — la prochaine campagne peut chiffrer le gain
- [ ] Unit tests pour tout nouveau service/handler (>= 1 par méthode publique)
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

- Lancer le banc local : `cd Api/Mail && dotnet run --project src/AppHost --launch-profile https-load-test`
- Seeder : `dotnet run --project tests/mss.mail.loadtest.seed -- --users 5 --messages 20 --api http://127.0.0.1:5052`
- Rejouer deux fois de suite le quatuor du dashboard pour la même identité
  (`GET /mail/folders`, `GET /mail/folders/INBOX`, `GET .../emails/today`,
  `GET /sync/coverage`, en-têtes loadtest-1, `Client-Session-Id` stable) :
  la seconde passe est sensiblement plus rapide sur l'appel identifié comme
  dominant
- Envoyer un message vers loadtest-1 (seed ou `sendmail`), rejouer le
  quatuor : les compteurs reflètent le nouveau message (pas de cache menteur)
- **Au banc (clôture de l'US, non bloquant pour le merge)** : tir journey
  distant iso-conditions avec `report-journey-1000-solo-postimap-20260825` —
  part du dashboard dans le temps serveur < 15 % (aujourd'hui 24,8 %),
  étape 1 toujours verte au SLO

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — optimisation de performance interne, aucun
  changement fonctionnel ni de contrat d'API
- **Exigences DSR honorées** : non applicable — comportement fonctionnel inchangé
- **INS** : non applicable — aucun traitement patient modifié
- **Authentification PS** : inchangée (PSC en amont)
- **Habilitations** : inchangées — un cache éventuel est strictement par
  praticien (clé = identité PS), jamais partagé entre praticiens
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé — aucun accès nouveau, mêmes évènements
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — inchangé
- **AIPD / impact RGPD** : un cache par praticien de compteurs de dossiers ne
  crée pas de nouveau traitement ; contenu limité à des dénombrements, TTL
  court, pas de contenu de message — impact nul

## Branches
- `api-mail` (pushed) : feat/task-273-dashboard-folder-cost — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-273-dashboard-folder-cost
- `dtos-mss` (pushed, auto-inclus) : feat/task-273-dashboard-folder-cost — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-273-dashboard-folder-cost

## Cause établie (/develop, 2026-08-29 — AVANT remède, DOD item 2)

**Sources** : lecture de chemin `ImapService.cs` (sites vérifiés ligne à ligne),
tir `report-journey-1000-solo-postimap-20260825-151054.md` (ventilation par
`call` + table des verrous par opération), réconciliation avec la mémoire du
banc 2026-08-08.

### Décomposition par phase de `GET /mail/folders/{folder}` à l'arrivée dashboard

| Phase | Constat | Preuve |
|---|---|---|
| **Verrou** | Le chemin froid paie **2 acquisitions successives** de `imap_session` (`GetFolderStatus:{path}` puis `GetFolderQuery:{path}`), avec une **fenêtre de préemption entre les deux** : tout détenteur concurrent du même verrou de session (l'enrichissement en détient 6,29 s p95, 34,2 acq/s) peut s'intercaler. Attente p95 mesurée : 5 ms (status) / **450 ms** (query). | `ImapService.cs:584` et `:1019` ; table « Verrou de session par opération » du tir |
| **IMAP** | Chemin froid = **7 allers-retours** : resolve+STATUS (GetFolderStatus) puis resolve+STATUS+SELECT+SEARCH+CLOSE (GetFolderQuery) — resolve et STATUS payés **deux fois**. Constaté de longue date dans le code (`p95 726 ms sous 96 ms de latence : ~7 RTT`, commentaire task-262 `ImapService.cs:1035`). La détention `GetFolderStatus` p95 = **3,2 s pour 2 RTT** : la détention est dominée par le re-établissement de session (connect+TLS+auth sous le verrou, `ConnectInternalAsync`) quand la connexion poolée est retombée, pas par les commandes. | `ImapService.cs:580-627`, `:1015-1102` ; solicitations `resolve_folder`/`status_folder` ×2 |
| **Base** | **Aucune requête SQL sur ce chemin** en régime nominal : l'id praticien et les réglages lus par `ConnectInternalAsync` sous le verrou sont cachés Redis depuis task-229/074 (`BaseRepository.GetCurrentUserIdAsync`, `UserSettingsRepository.GetSettingsAsync`). La base est hors de cause — cohérent avec l'absence de `DbOperationScope` sur ce chemin. | `BaseRepository.cs:134-163`, `UserSettingsRepository.cs:98-137` |
| **Matérialisation** | Négligeable : un `FolderDto` + liste d'UIDs (reversed). Pas de N+1, pas d'objets de fil (contrairement à la page d'en-têtes, hors périmètre). | `ImapService.cs:1056-1074` |

### Pourquoi le dashboard et pas l'inbox (réconciliation des deux lectures)

La même route coûte **p50 133 ms / p95 596 ms** à l'étape dashboard et
**p50 7 ms / p95 151 ms** à l'étape inbox du même passage (tir 1000, n=40 655
chacun). Le mécanisme : `folder:status` a un **TTL de 10 s** — à l'arrivée
dashboard (premier geste après des minutes d'inactivité) il est **toujours
expiré**, alors qu'à l'ouverture d'inbox (3-10 s après) il vient d'être réécrit
par le quatuor. « L'ouverture du dossier est gratuite (7 ms) » (mémoire
2026-08-08) décrit le chemin **cache-hit** ; le dashboard paie le chemin froid.
Les deux lectures sont réconciliées : même route, deux populations.

De plus, à charge la boîte bouge en continu → `(Count, UidNext)` a changé →
le chemin froid dégénère presque toujours en 2 verrous + 7 RTT, et `today`
(même invariant, p95 469 ms) repaie un SEARCH complet de son côté. Dispersion
×45 de l'étape = bimodalité cache-hit/froid × attente de verrou.

### Remède retenu (contrat d'API inchangé)

1. **Fusionner le chemin froid en une seule acquisition** (`GetFolderRead:{path}`) :
   connect + resolve + STATUS, et SELECT+SEARCH+CLOSE **sous le même verrou**
   seulement si `(Count, UidNext)` invalide le cache d'UIDs. 7 RTT → 5 RTT,
   2 attentes de verrou → 1, fenêtre de préemption supprimée.
2. **Pollinisation LIST-STATUS** : `GetFoldersAsync` obtient déjà
   Count/Unread/UidNext de **tous** les dossiers en un aller-retour ; il écrit
   désormais les entrées `folder:status:{email}:{path}` correspondantes (hors
   verrou, TTL 10 s inchangé) — l'appel `folders` du quatuor arme la validation
   de `folder/{name}` et `today` quel que soit l'ordre d'émission des fronts.
3. **Aucun nouveau cache, aucun TTL modifié** : les fenêtres existantes
   (status 10 s, uids/query 5 min) restent la borne de fraîcheur déjà acceptée
   par le produit — le point « cache menteur » du Manual Test Plan reste régi
   par l'invariant `(Count, UidNext)` actuel.

Télémetrie : la nouvelle famille de verrou `GetFolderRead` et les solicitations
`operation=GetFolderRead` remplacent les familles `GetFolderStatus`/`GetFolderQuery`
sur cette route (celles-ci subsistent sur le chemin `today`/`unread` pour
`GetFolderQuery`) — la prochaine campagne lit le gain directement dans la table
des verrous par opération.

## Develop log

- Repos touched : api-mail (dtos-mss : branche sans commit, aucun changement de contrat)
- DTOs published : no DTO change
- Interop published : no interop change
- Commits :
  - api-mail : 18a857c feat(imap): task-273 — chemin froid de GET /folders/{name} fusionné sous un seul verrou de session
- Local build / test : ✓ build 0 erreur ; suites toutes vertes en isolation
  (application 2186/2186, api 692, infrastructure 464, domain 136, intégration
  420 + 16 skips préexistants). ⚠️ Flaky préexistant observé en run solution
  parallèle uniquement : 1 échec baladeur parmi les tests d'instrumentation
  d'enrichissement (EnrichmentOperationScopeTests, MailRepositoryEnrichPersist-
  InstrumentationTests — hors diff task-273), vert 3/3 en isolation.
- DOD self-check : cause établie et consignée (section « Cause établie ») ✓ ;
  remède sans changement de contrat ✓ ; test d'intégration DOD
  (DashboardArrivalCostIntegrationTests : 2e arrivée = zéro sollicitation,
  nouveau message servi à l'expiration de la fenêtre, pollinisation) ✓ ;
  clause cache : N/A — aucun nouveau cache, aucun TTL modifié (fenêtres
  existantes 10 s / 5 min inchangées), consigné ✓ ; verrous/solicitations
  continuent de mesurer le chemin optimisé (nouvelle famille `GetFolderRead`) ✓ ;
  aucune donnée de santé dans les logs (mêmes gabarits qu'avant) ✓. Item
  « part dashboard < 15 % au banc » : clôture de l'US au tir, non bloquant
  pour le merge (dit par le Manual Test Plan).
- Next step : /forge-simplify task-273

## Simplify log (/forge-simplify, 2026-08-29)

- Scope : api-mail seul (dtos-mss sans commit — jamais touché par simplify).
- 3 retouches quality-only sur le code frais (`c0a2f7f`) : invariant
  `(Count, UidNext)` factorisé en `UidsCacheMatches` (2 lecteurs),
  `GetFolderQueryAsync` réutilise `MapLiveFolderToDto` (DTO redéclaré champ
  par champ supprimé), commentaire task-262 remis au vrai.
- Re-validation : build 0 erreur, application 2186/2186,
  DashboardArrivalCostIntegrationTests 3/3. Commit + push.

## Sonar log (/sonar, 2026-08-29)

Analyse complète (Release + coverage OpenCover) sur la branche
`feat/task-273-dashboard-folder-cost`, serveur redémarré par la forge
(conteneur arrêté depuis 2 j).

| Métrique | Baseline (avant scan branche) | Final | Cible |
|---|---|---|---|
| Bugs | 0 | 0 | 0 ✅ |
| Vulnerabilities | 0 | 0 | 0 ✅ |
| Security hotspots | 3 | 3 (préexistants) | — |
| Code smells | 64 | 63 | best-effort |
| Coverage | 88,0 % | 88,2 % | ≥ 95 (long terme) |
| New coverage | — | 90,9 % | ≥ 95 (fenêtre new-code, best-effort) |
| Ratings R/S/M | A/A/A | A/A/A | A ✅ |
| **Quality Gate** | — | **OK** ✅ | OK |

- New-code : 36 issues dans la fenêtre new-code, dont **1 seule attribuable au
  diff task-273** — CA1861 (tableaux littéraux en argument d'Assert.Equal),
  corrigée à la main (`759abac`) ; récidive consignée dans
  `conventions/csharp.md` (Occurrences : 2). Les 35 autres appartiennent aux
  tasks antérieures de la fenêtre (S3604/S107/S125 sur SentArchiveService,
  MailClientSession, FlagPropagationService, embedding…) — hors périmètre,
  best-effort accepté.
- Tests Release du scan : mêmes 3-4 échecs baladeurs préexistants
  (EnrichmentOperationScopeTests, MailReadObjectCountTests,
  SeededThreadsAreCountableTests) — verts en isolation, hors diff task-273.

## Lint log (/lint-angular, 2026-08-29)

- Skip clean : `client-angular` non listé dans **Repos** et aucun code Angular
  écrit par la task (backend seul). Chaîne vers /lint-mobile.

## Lint mobile log (/lint-mobile, 2026-08-29)

- Skip clean : `client-mobile` non listé dans **Repos**, aucun code mobile
  écrit par la task (backend seul). Chaîne vers /verify-visual.

## Visual verify log (/verify-visual, 2026-08-29)

- Skip clean : aucun écran `client-mobile` touché (task backend seule, pas de
  `## Stitch design log`). Chaîne vers /review.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/206 — label `awaiting-human-merge`
- `dtos-mss` : aucun commit (pas de changement de contrat) — pas de PR ; branche à supprimer au /merge

## Code Review Summary

APPROVED — 0 bloquant, 4 fichiers revus (1 src + 3 tests). 1 suggestion non
bloquante : `folder:status` n'est plus écrit quand la SEARCH échoue à mi-chemin
(sans effet produit — l'absence d'entrée vaut re-lecture). Contrat d'API
strictement inchangé (aucun DTO, aucune route touchés) ; parité de forme du
FolderDto centralisée dans MapLiveFolderToDto et testée. DOD 8/8 vérifiables
verts ; l'item « part dashboard < 15 % au banc » est un critère de clôture
d'US au prochain tir, non bloquant pour le merge (dit par la task).
