# questions/task-082.md — Checkpoint campagne couverture 90 % (pas un blocage métier)

**Task** : `tasks/wip-task-082-coverage-90-campaign.md`
**Étape** : `/develop` itération 1 — checkpoint (pas un échec technique, pas une question métier)
**Date** : 2026-06-14
**Branche** : `feat/task-082-coverage-90-campaign` (api-mail) — incrément +57 tests déjà poussé

## Situation

`/start task-082` a enchaîné `/develop`. La première itération a livré un
incrément réel (couverture **84,4 % → 85,4 %**, +57 tests, build + suite verts,
`git diff -- src/` vide). Mais la **cible ≥ 90 % du DOD n'est pas atteignable
en une seule passe `/develop`** — c'est un chantier multi-itérations, comme la
task le scope explicitement.

Plutôt que de faire un hand-off `/review` mensonger (le DOD exige ≥ 90 %, on est
à 85,4 %), la passe s'arrête proprement ici en checkpoint. La task reste en
`wip-*`.

## Ce qui reste (le vrai gisement)

Pour passer de 85,4 % à 90 %, il faut réduire le total (lignes+conditions) non
couvertes de ~3 416 à ≤ 2 336, soit **~1 080 à couvrir (~250-300 tests)**. Le
restant n'est **pas** couvrable en pur unitaire mocké :

| Fichier | Couv. | Lignes non couv. | Moyen |
|---|---|---|---|
| `MailRepository.cs` | 85,2 % | 207 | **Intégration Testcontainers** |
| `BaseRepository.cs` | 22,5 % | 131 | **Intégration Testcontainers** |
| `SemanticSearchRepository.cs` | 80,7 % | 79 | **Intégration Testcontainers + pgvector** |
| `ImapService.cs` | 72,3 % | 332 | Unitaire plafonné (extension methods MailKit) + intégration |
| `AiDiagnosticsController.cs` | 67,2 % | 57 | Intégration TestServer |
| Autres | < 90 % | ~290 | Mixte |

Les surfaces unitaires mockables faciles sont **déjà largement couvertes**
(rendement marginal faible) — le levier 90 % est l'**intégration Docker**.

## Pour débloquer / reprendre

Aucune décision métier requise. Deux options :

1. **Relancer `/develop task-082`** (ou itérer manuellement via le
   `code-coverage-skill`) pour continuer la campagne — en sachant que c'est
   long (Docker + cycles SonarQube de ~7 min). Cibler en priorité les 3
   repositories en intégration Testcontainers (harnais `PostgreSqlFixture` +
   pattern `MailRepositoryTagDraftCoverageTests` déjà en place).
2. **Merger l'incrément acquis** (85,4 %) via `/review task-082` en abaissant
   la cible du DOD à la valeur atteinte, si on préfère figer le gain maintenant
   et planifier le reste séparément. (Choix humain.)

Quand la couverture ≥ 90 % est mesurée et `git diff -- src/` toujours vide →
`/review task-082` ouvre la PR `awaiting-human-merge` (HAG).

## Itération 2 (2026-06-14) — finding dispositif sur les repositories

Tentative option 1 (repositories Testcontainers) : **12 tests d'intégration
`MailRepository`** ajoutés (read/unread, flag/unflag, GetMail, ResolveMailId,
UpdateEmailSummary, MarkAsCancelled, DeleteMail, GetExistingUids/EnrichedUids,
GetAttachment/UpdateAttachment) — tous **verts**, contre la vraie Postgres.

**Résultat mesuré : couverture projet 85,4 % → 85,4 % (uncovered_lines
1805 → 1803, +2 lignes seulement). `MailRepository` reste à 207 lignes non
couvertes.**

Analyse OpenCover ligne par ligne (preuve) : les méthodes ciblées étaient
**déjà couvertes transitivement** par les suites d'intégration existantes
(ex. `GetExistingUidsAsync` visited=6, `GetMailAsync` appelé en interne par de
nombreux tests). Le cross-référencement par *nom de test* était trompeur. Seule
~1 méthode (`UpdateEmailReadStatus`) a ajouté ~2 lignes nettes.

### Conclusion (données à l'appui)

Les **surfaces faciles des repositories sont déjà couvertes**. Le restant
(207 lignes `MailRepository`, 131 `BaseRepository`, etc.) est concentré dans :
- des **branches difficiles** (handlers d'erreur, variantes de requêtes,
  chemins embeddings / documents médicaux, concurrence) — couvrables seulement
  par des tests **chirurgicaux ciblant chaque branche** identifiée ligne par
  ligne dans le rapport OpenCover (effort énorme, ~2 lignes / 12 tests au
  rythme actuel) ;
- le **bootstrap per-tenant de `BaseRepository`** (création de la base
  `u_{rpps}_…` + migrations FluentMigrator sous `ASPNETCORE_ENVIRONMENT=
  Development`) — un seul gros bloc (~100 lignes) mais à haut risque de mise
  en place ;
- les chemins IMAP via **extension methods MailKit non-mockables**.

**Atteindre 90 % n'est pas réalisable par ajout de tests « happy path »** —
il faut soit accepter une cible réaliste inférieure, soit engager une campagne
chirurgicale de couverture de branches (très longue, ~milliers de décisions).

### Bug latent découvert (à traiter hors task-082, tests-only)

`MarkReadReceiptSentAsync` : la colonne `ReadReceiptSentAt` est mappée
`timestamptz` par le **modèle EF** (`EnsureCreated`) alors que le schéma de
production **FluentMigrator** la déclare `timestamp without time zone`
(task-078). Discrépance de schéma EF↔migrations — write `Kind=Unspecified`
échoue sur le harnais d'intégration. À corriger séparément (touche le modèle
EF, hors périmètre tests-only).
