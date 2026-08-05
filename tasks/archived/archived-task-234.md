# archived-task-234.md — Les tâches de fond visaient une autre base que la requête

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune
**Priorité**: **0 — correctif** : risque de perte de données sur `develop`, et travail
de fond silencieusement jamais exécuté.

> ⚠️ **Task créée après coup.** Ce correctif est né d'un **essai manuel humain** pendant
> le cycle de task-230, pas d'une US du PO. La forge l'a traité directement en hotfix
> depuis `develop`, puis a régularisé le plan de contrôle ici — le plan de contrôle est
> le journal de la forge, un correctif mergé sans trace y serait une lacune.

> ⚠️ **Renumérotation.** Ouvert d'abord sous `task-231`, numéro **déjà attribué** par le
> PO à une US sur le chemin SMTP (lot 229-232, commit `d2d0008`). La forge avait pris ce
> numéro **sans vérifier les numéros libres** — faute déclarée. Renuméroté en `task-234`
> (premier libre, 233 étant prise aussi), PR d'origine #160 fermée sans merge, aucune
> réécriture d'historique poussé.

## Objectif

Que le travail confié à une tâche de fond s'exécute **dans la base du praticien**, et
non dans une base de repli où il ne trouve rien et ne dit rien.

## Comment le défaut a été trouvé

Essai manuel : ouverture de `client-angular`, passage de 3 messages en non lu et 1 en
suivi depuis `INBOX`. Les 4 actions en attente ont bien été créées en base — puis
**rien**. Elles sont restées `Pending`, `RetryCount = 0`, **sans une erreur ni un
avertissement** dans Seq.

L'analyse Seq a été **décisive par ce qu'elle ne contenait pas** :

| Observation | Ce qu'elle élimine |
|---|---|
| Aucun `Error` `[BackgroundQueue] Background work … failed` | La course **n'a pas planté** |
| Aucun `Error` `[FlagChange] Failed to persist…` | L'écriture de l'outbox a **réussi** |
| Les 4 lignes intactes (`Pending`, `RetryCount = 0`) | **Rien n'a été réclamé** |

Les logs de propagation sont en `Debug`, or l'API journalise à partir d'`Information` :
leur absence ne prouvait rien. **C'est l'état de la base qui a tranché.**

## La cause

`UserDatabaseName` se dérive de **`(Email, MssRpps)`**.

Trois endroits recopiaient l'identité du praticien vers un scope de tâche de fond en
énumérant **six champs à la main** — `Email`, `Password`, `JwtToken`,
`ConnectionStringServer`, `ClientSessionId`, `UserName` — et **tous les trois oubliaient
`MssRpps`**. Sans le RPPS, `NormalizeRpps` retombe sur sa valeur de repli et la tâche
construit le nom d'une **autre base**.

**Et l'échec est silencieux, ce qui est le pire** : la tâche ne lève pas, elle lit une
base aux tables vides, `GetCurrentUserIdAsync` y **crée** même un utilisateur à la
volée, puis la requête ne trouve « rien à faire » et se termine normalement.

## Les trois sites

| Site | Origine | Conséquence |
|---|---|---|
| `MailController.EnrichEmailsBackgroundAsync` | **préexistant** (task-075) | L'enrichissement asynchrone visait lui aussi la base de repli |
| `ImapService.ReconcileFoldersOffHotPathAsync` | **task-229, déjà mergée** | `ReconcileFoldersAsync` **supprime** les dossiers absents du jeu valide : inoffensif dans une base vide, **chemin de perte de données** si elle contient des dossiers d'un autre contexte |
| `FlagPropagationService` | task-230 | Corrigé sur sa branche (`9bde164`) |

> Le premier site n'était pas dans le diagnostic initial : la forge croyait suivre un
> motif de référence sain. **Il était déjà incomplet** — elle a reproduit fidèlement un
> oubli antérieur.

## Le correctif

`UserContextInfo.CopyIdentityTo(target)` — méthode unique, **pendant exact de
`Reset()`**, transportant les **neuf** champs d'identité. La recopie champ-par-champ est
désormais interdite : c'est elle qui a produit le même oubli trois fois.

`MailController` capture en outre un **instantané détaché** : le contexte de requête est
`scoped` et peut être réinitialisé une fois la réponse partie, donc capturer l'instance
elle-même serait une course.

## Pourquoi les tests existants ne pouvaient pas l'attraper

Ils **substituent les dépôts**, donc la chaîne de connexion n'est **jamais construite**.
Et le test de repeuplement du contexte (task-229 / 230) vérifiait `Email`,
`ConnectionStringServer` et `ClientSessionId` — c'est-à-dire **tout sauf le champ qui
choisit la base**.

> C'est un **angle mort structurel** des tests à dépôts substitués, pas un oubli
> ponctuel. Le défaut a échappé à 3 467 tests et à quatre scans Sonar ; il n'a été
> trouvé que parce qu'un humain a cliqué dans le front et regardé la table.

## Les tests ajoutés

| Test | Ce qu'il fige |
|---|---|
| `ReproducesTheSameDatabase` | **L'assertion centrale** : `UserDatabaseName` et `ConnectionStringUser` identiques — la grandeur qui décide où l'on écrit |
| `WithoutTheRppsWouldTargetAnotherDatabase` | La démonstration du défaut : à RPPS près, une **autre** base |
| `CarriesEverySettableIdentityField` | **Garde-fou par réflexion** : les champs sont **découverts**, pas listés — un champ ajouté demain fait échouer le test tant qu'il n'est pas recopié |
| `CoversExactlyWhatResetClears` | `CopyIdentityTo` et `Reset` ne peuvent plus diverger |

Le garde-fou par réflexion est délibéré : comparer une liste écrite à la main aurait
**reproduit le défaut d'origine**, en vérifiant les champs auxquels on a pensé.

**Preuve ROUGE** : en retirant la recopie de `MssRpps`, **2 tests tombent** — celui qui
compare la base et le garde-fou par réflexion.

## Second défaut trouvé en chemin — un garde-fou de sécurité qui criait au loup

`GlobalExceptionHandlerTests` et son pendant d'intégration (**task-055**, jamais touchés
par cette task) faisaient `Assert.DoesNotContain("NIR", payload)` sur le corps JSON
**entier**, `traceId` compris. Or `traceId` est l'identifiant ASP.NET
(`{ConnectionId}:{RequestNumber}`), une chaîne base32 dont le **préfixe est stable
pendant toute la vie du processus** : s'il contient les trois lettres « NIR » — observé :
`0HNNIRI6FIOJE` — le test échoue sur **toutes** les exécutions de la période, puis
redevient vert au redémarrage suivant. **Reproduit 3 fois sur 3**, ce qui écarte la
coïncidence par requête.

Un garde-fou de **sécurité** qui crie au loup finit désactivé ou ignoré — pire que pas de
garde-fou. La recherche porte désormais sur les champs que le serveur **rédige**
(`title`, `detail`), où un identifiant de santé n'a effectivement rien à faire ; le
message d'exception reste cherché dans **tout** le corps.

**Vérifié que le garde-fou mord toujours** : une fuite d'identifiant simulée dans
`Detail` fait tomber **4 tests de sécurité**. Recentré, pas désarmé.

## Validation

| Contrôle | Résultat |
|---|---|
| Build | **0 erreur, 0 avertissement** |
| `domain` | **106 / 106** (+4) |
| `application` | 1 964 / 1 964 |
| `infrastructure` | 422 / 422 |
| `api` | **649 / 649**, 3 exécutions sur 3 |
| `integration` | 304 / 320 (16 ignorés — le compte normal) |
| Preuves ROUGE | 2 (recopie sans RPPS ; fuite simulée dans `Detail`) |

## PRs

- **`api-mail`** : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/161 — **mergée**
  Branche `fix/task-234-background-scope-identity`, 1 commit (`699f210`).
- **PR abandonnée** : #160 (`fix/task-231-…`), fermée sans merge pour collision de numéro.

## Merged

**Mergée le 2026-08-05**, après attestation humaine `--i-tested` et confirmation
explicite du périmètre (correctif de base **+** garde-fou de sécurité dans la même PR).

| Repo | PR | Commit squash | Ref distante |
|---|---|---|---|
| `api-mail` | [#161](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/161) | `ac814e1` | supprimée (locale conservée) |

Garde-fous vérifiés : CI `build` verte (attendue jusqu'au `mergeState=CLEAN`, la PR étant
d'abord `UNSTABLE`), label `awaiting-human-merge`, aucune revue `CHANGES_REQUESTED`,
arbre de travail propre.

## Ce qui reste à vérifier

- [ ] **Relancer l'essai manuel** : marquer un message lu / non lu depuis le front, et
  vérifier que l'action en attente **disparaît en quelques secondes** au lieu de rester
  `Pending`. C'est la seule preuve de bout en bout — aucun test automatisé ne construit
  de chaîne de connexion réelle.
- [ ] **Chercher une base parasite** dans PostgreSQL (`\l`, nom au RPPS de repli).
  L'enrichissement asynchrone préexistant a pu en créer une **et y écrire une ligne
  `Users`** (`GetCurrentUserIdAsync` crée l'utilisateur à la volée). Si elle existe,
  c'est la trace de ce défaut, et elle **date d'avant task-229/230**.

## Point ouvert — l'angle mort qui a permis ce défaut

Aucun test de ce dépôt ne construit une **chaîne de connexion réelle** depuis un
`UserContextInfo` reconstitué : les dépôts sont substitués partout. Un test d'intégration
qui exercerait une tâche de fond **de bout en bout** (scope réel, base réelle) est le seul
qui aurait attrapé ce défaut sans intervention humaine. Signalé pour arbitrage : c'est une
lacune de **stratégie de test**, pas un test à ajouter à la va-vite.
