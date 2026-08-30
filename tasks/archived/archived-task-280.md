# todo-task-280.md — L'arrivée dashboard sans attente est retirée : elle dégradait

**Repos**: api-mail
**Dependencies**: task-278 (mergée — c'est elle qu'on retire)
**Epic**: E015

## Objectif

task-278 servait l'arrivée sur le tableau de bord depuis un instantané et
rafraîchissait hors du chemin de réponse (*stale-while-revalidate*), sur
arbitrage produit du 2026-08-30. **Le tir du même jour la mesure comme une
régression, et il faut la retirer.**

Iso-conditions strictes avec le tir du 29/08 (même base hydratée, mêmes réserves,
mêmes fenêtres, latence appariée) :

| `dashboard,call:folder` | 29/08 (sans) | 30/08 (avec) | |
|---|---|---|---|
| moyenne | 358,4 ms | **730,2 ms** | **×2** |
| p50 | 140,3 | 134,9 | inchangé |
| p95 | 928,3 | **4 650,8** | **×5** |
| part du temps serveur | 34,9 % | **53,7 %** | **+19 pts** |
| attente moyenne du verrou (`ReadFolder`) | 82,8 ms | **202,5 ms** | ×2,4 |

Le critère de clôture fixé par task-278 elle-même était « moyenne < 250 ms, p95
< 600 ms ». On est à **730 et 4 651**.

**La médiane est intacte** (135 ms) : ce sont les **queues** qui explosent. La
prédiction faite au moment de l'arbitrage (~215 ms de moyenne, −40 %) était
fausse d'un facteur 3,4, et dans le mauvais sens.

### ⚠️ Le mécanisme n'est PAS établi, et on ne le cherchera pas

Les acquisitions de `ReadFolder` n'ont **pas** augmenté (11,6/s contre 12,98/s) :
l'explication « le rafraîchissement ajoute des lectures » ne tient pas telle
quelle. Établir la cause exacte demanderait un tir de plus.

**Ce n'est pas un bon investissement.** La fonctionnalité a déjà coûté deux
allers-retours de conception, deux relectures humaines (dont une qui a trouvé un
défaut bloquant — l'instantané survivait aux invalidations et faisait
réapparaître un message supprimé), et elle dégrade là où elle devait améliorer.
Le précédent est **task-216**, qui a retiré la voie d'écriture IMAP sur le même
raisonnement : le mécanisme marchait, le bilan était négatif, on retire.

### Contenu attendu — retrait chirurgical

**Retirer** : `RedisKeys.Folder.Snapshot` et `CacheDurations.FolderSnapshot` ;
`RefreshFolderSnapshotMessage` et son consommateur ; `PublishRefreshFolderSnapshotAsync` ;
`IImapService.RefreshFolderAsync` et le paramètre `serveStale` ; la lecture,
l'écriture et les quatre invalidations de l'instantané ; l'endpoint MassTransit ;
les tests unitaires et le filet d'intégration de la fonctionnalité.

**CONSERVER, et c'est le point le plus important de cette task** :

1. **L'étiquette `holder` sur `mssante_lock_wait_duration_seconds`** et son test
   de cardinalité. C'est le seul acquis de task-278, et il est considérable :
   **il a nommé la cause des 82,8 ms** que trois US n'avaient pas su établir.
   Le tir du 30/08 le montre — `ReadFolder` attend **3,938 s au p95 médian
   (max 20,4 s) derrière `AppendToSent`**, l'archivage des messages envoyés.
2. Le retour de `ImapFolderServiceSuccessTests` à trois suppressions de cache.

**Ce qui n'est PAS dans le périmètre** : task-277 et task-279, mergées dans la
même vague et **conservées intégralement** ; le remède à la contention
`AppendToSent`, qui fait l'objet d'une US distincte.

## Definition of Done

- [ ] Build passes (0 erreur)
- [ ] Tests pass (0 échec)
- [ ] Aucune trace de `Snapshot`, `RefreshFolder` ou `serveStale` sur le chemin
      des dossiers — vérifiable par `grep`
- [ ] L'étiquette `holder` et `LockWaitHolderTests` sont **intacts**
- [ ] task-277 (`DeadSessionPolicy`) et task-279 (`AttachmentOperation`) sont
      **intacts** dans `ImapService`
- [ ] `ImapFolderServiceSuccessTests` re-épingle **trois** suppressions
- [ ] Le nombre de tests revient au niveau d'avant task-278, moins les siens

## Manual Test Plan

- [ ] Banc : `dotnet run --project src/AppHost --launch-profile https-load-test`
- [ ] Seed 2 utilisateurs, ouvrir `INBOX`, attendre > 10 s, rouvrir
- [ ] **Vérifier** : la réponse repasse par le serveur de messagerie (journal
      `[ListFolder]`), **aucun** journal `SNAPSHOT SERVED`
- [ ] **Vérifier** : la file `refresh-folder-snapshot-queue` n'existe plus
- [ ] Supprimer un message, rouvrir le dossier : il ne réapparaît pas
- [ ] **Clôture au banc, tir suivant** : `dashboard,call:folder` revient à
      ~358 ms de moyenne et ~930 ms de p95 ; part du dashboard de retour à
      ~35 % ; attente moyenne de `ReadFolder` de retour à ~83 ms ; 11/11 vertes

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — retrait d'une optimisation de performance
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé
- **Consentement patient** : non applicable — **le retrait REND au praticien la
  fraîcheur** que l'arbitrage du 2026-08-30 lui avait fait céder
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — inchangé
- **AIPD / impact RGPD** : inchangé

## Branches

- `api-mail` (pushed) : `feat/task-280-revert-dashboard-swr`
- `dtos-mss` : non concerné (retrait sans changement de contrat)

## Develop log

**Retrait chirurgical**, vérifié par `grep` plutôt que par confiance :

| Contrôle | Attendu | Constaté |
|---|---|---|
| `holder` dans `ImapLockScope` / `MailProcessingMetrics` | conservé | **20 / 3** occurrences ✅ |
| `DeadSessionPolicy` + `AttachmentOperation` dans `ImapService` | conservés | **6** occurrences ✅ |
| `Snapshot` / `RefreshFolder` / `serveStale` sur le chemin dossier | **0** | **0** ✅ |

**Méthode** : `ImapService.cs` restauré depuis `b7cfe52^` — le merge de task-279,
donc l'état portant task-277 **et** task-279 sans task-278. `ImapLockScope.cs` et
`MailProcessingMetrics.cs` **non touchés**, pour préserver l'étiquette `holder`.

**Vérification** : build 0 erreur / 0 avertissement ; domain 136, infrastructure
464, api 692, integration 419 (+16 skips), application 2 209 — **3 920 verts**.
Un rouge unique sur `infrastructure`, **non reproduit sur deux exécutions**
(flaky d'état statique partagé déjà documenté).

⚠️ **Deux builds de cette task ont d'abord échoué sur des VERROUS de fichiers**
— cinq réplicas `mss.mail.api` du banc de charge tournaient encore. Ce n'était
pas du code, et il ne faut pas le lire comme tel : c'est la deuxième fois en deux
jours. Le banc a été rendu avant de conclure.

## PRs

- `api-mail` — **[PR #211](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/211)** — label `awaiting-human-merge`

## Code Review Summary

**APPROVED** — 13 fichiers (2 supprimés en source, 2 en tests, 9 modifiés), 0 bloquant.

Le risque d'un retrait n'est pas d'en faire trop, c'est d'en faire **trop peu ou
trop** : emporter l'instrument, ou laisser une bribe de la fonctionnalité. Les
trois `grep` du Develop log couvrent exactement ces deux sens.

**DOD** : 7/7 verts.

## Merged

**Date** : 2026-08-30 — `/merge 280 --i-tested` (HAG, règle 10).

| Repo | PR | Squash sur `develop` |
|---|---|---|
| `api-mail` | [#211](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/211) closed | `041cd91` |

**Portes** : `--i-tested`, label `awaiting-human-merge`, `MERGEABLE`/`CLEAN`,
CI de PR verte (`build` pass), aucun `CHANGES_REQUESTED`. La task était encore en
`wip-` — elle a été régularisée en `done-` (PR ouverte sans passer formellement
par `/review`, dont le fond avait pourtant été fait : build, suite complète, revue).

**Validation post-merge sur `develop`** : build 0 erreur, **3 920 tests verts /
0 rouge** (domain 136, infrastructure 464, api 692, integration 419 + 16 skips,
application 2 209).

**Branche** : ref distante supprimée ; branche locale conservée.

## Ce que cette task laisse derrière elle

**L'aller-retour complet de task-278 se solde par un retrait**, et c'est un
résultat, pas un échec — mais il a coûté cher : deux conceptions, deux relectures
humaines (dont une qui a trouvé un défaut bloquant non couvert par les tests), un
tir de 2 h.

**Ce qui reste acquis, et le justifie** : l'étiquette `holder` a nommé la cause
des 82,8 ms d'attente que task-276, 277 et 278 n'avaient pas su établir —
**`ReadFolder` attend 3,938 s au p95 médian (max 20,4 s) derrière
`AppendToSent`**, l'archivage des messages envoyés. C'est le chantier de capacité
suivant, il ne demande aucun arbitrage produit, et il était invisible avant.

**Leçon de méthode** : la prédiction faite au moment de l'arbitrage produit
(~215 ms, −40 %) reposait sur un **modèle**, pas sur une mesure. Elle était fausse
d'un facteur 3,4 dans le mauvais sens. Un modèle qui sert à décider d'un
arbitrage produit doit être annoncé comme tel — ce qu'il avait été — mais il ne
remplace pas un tir, et l'écart observé doit servir de calibrage aux suivants.
