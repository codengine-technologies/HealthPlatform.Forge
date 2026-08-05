# todo-task-230.md — Marquer lu paie 4 allers-retours IMAP dans la réponse HTTP : acquitter sur la base, propager le flag en arrière-plan

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune (indépendante de task-228/229 dans le code ; les
contre-épreuves au banc se lisent mieux si chaque task passe séparément)
**Priorité**: **1** — `mark_read` est hors grille SLO (p50 331 ms pour poser un
flag) et pèse 8,7 % du temps serveur. Le remède est celui au meilleur rapport
gain/risque de la campagne : l'infrastructure porteuse existe déjà.

> ⚠️ **Contrainte absolue — aucun impact frontend.** Même route
> (`PUT Mail/folders/{foldername}/emails/{emailid}/status/read`), même code
> HTTP, même corps de réponse. Seul le moment où le flag IMAP est
> physiquement posé change (différé de quelques secondes au plus).

## Objective

Que « marquer lu » coûte le prix d'un commit en base (~10-20 ms), pas celui de
4 allers-retours IMAP sous latence MSSanté. L'analyse de code a établi le
chemin actuel (`EmailFlagService.UpdateEmailReadStatusAsync` →
`ProcessEmailAsync`) — **tout est synchrone dans la réponse HTTP** :

1. `UPDATE Mails SET IsRead = true` + `SaveChangesAsync` (Postgres) ;
2. une **relecture DB lourde** `GetMailAsync(folderPath, uid, Header)`
   uniquement pour alimenter la trace d'audit — génération, mail, tags,
   destinataires, pièces jointes, et `PopulateMailContentAsync` si documents
   médicaux : plusieurs requêtes avant le premier octet IMAP ;
3. puis, **sous le verrou `imap_session` de la voie de lecture** (le même que
   les listings/lectures) : `LIST`, `SELECT`, `UID STORE +FLAGS (\Seen)`,
   `CLOSE` — 4 allers-retours ≈ 400 ms sous latence injectée, dont le `STORE`
   via l'extension MailKit **bloquante** `AddFlags` (pas `AddFlagsAsync`) ;
4. et **aucune invalidation** des caches Redis de compteurs de non-lus
   (`folder:status` TTL 10 s, `folder:metadata`) — la cohérence forte n'est
   déjà pas garantie aujourd'hui.

## Remède demandé — acquittement optimiste

1. **Chemin synchrone réduit à** : commit Postgres (`IsRead = true`) +
   enfilage de la propagation IMAP + réponse HTTP (corps inchangé).
2. **Propagation IMAP en arrière-plan**, portée par l'infrastructure
   existante — deux briques déjà en place, au choix argumenté de `/develop` :
   - `PendingActionService` / table `PendingActions` : le type
     `PendingActionTypes.MarkRead` est **déjà branché** sur
     `UpdateEmailReadStatusAsync` au rejeu (utilisé aujourd'hui en mode
     offline uniquement) — c'est une outbox persistée, avec déduplication et
     annulation par action opposée ;
   - `IBackgroundTaskQueue` + le patron de capture du contexte praticien hors
     requête déjà utilisé par `MailController.EnrichEmailsBackgroundAsync`.
   La voie persistée (`PendingActions`) est préférée : un flag jamais posé
   suite à un crash de pod reste rejouable.
3. **Échec IMAP** : retry via le mécanisme choisi ; en dernier recours le flag
   reste posé en base (état déjà atteignable aujourd'hui : l'échec IMAP après
   commit DB n'est pas compensé — le remède ne dégrade rien, il rend l'état
   transitoire au lieu de définitif).
4. **Correctifs d'hygiène sur le même chemin** :
   - remplacer la relecture `GetMailAsync(Header)` d'audit par une lecture
     minimale (les champs réellement tracés) ;
   - `AddFlagsAsync` au lieu de l'extension bloquante `AddFlags` ;
   - invalider `folder:status` du dossier après la propagation IMAP (le
     compteur de non-lus converge au lieu d'attendre l'expiration du TTL).

## Cohérence — bornes explicites

Les compteurs de non-lus et les listes `unread/*` sont servis par IMAP avec
des caches TTL 10 s / 5 min **jamais invalidés par `mark_read` aujourd'hui** :
la propagation différée n'introduit **aucune classe d'incohérence nouvelle**,
elle doit seulement rester dans la même enveloppe. Contraintes :
- l'enfilage est immédiat (pas de batch horaire) : propagation attendue en
  secondes ;
- en cas de rafale « marquer lu » sur le même dossier, les propagations
  peuvent être regroupées (la voie bulk `AddFlagsAsync` existe déjà) mais
  jamais retardées au-delà de la fenêtre du `folder:status` (10 s) en régime
  nominal.

## La mesure — tirs `journey-mssante-n300` du 2026-08-04

| Signal | Valeur (tir 17:05) |
|---|---|
| `mark_read` p50 / p95 (palier 300) | 331 / 524 ms — hors grille SLO |
| Part du temps serveur | 8,7 % (2 919 s, 7 743 appels) |
| Verrou `imap_session` / `UpdateFlag` | détention p95 0,997 s, 5,11 acq/s — sur la voie de lecture |
| Route serveur `status/read` p95 max | 4 562 ms |

## Definition of Done

- [ ] Build passes (0 errors) — `dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) — `dotnet test HealthPlatform.Api.Mail.sln`
- [ ] **Zéro changement de contrat** : route, code HTTP et corps de réponse identiques — les tests d'intégration existants passent sans modification de leurs assertions
- [ ] Le chemin synchrone de la réponse ne contient plus aucun appel IMAP — test unitaire (mock IMAP jamais appelé avant la réponse)
- [ ] Propagation asynchrone : unit tests — enfilage à chaque marquage, rejeu après échec IMAP, déduplication (marquer lu deux fois = une propagation), pas de perte au crash (si voie `PendingActions`)
- [ ] Relecture d'audit allégée : plus de `PopulateMailContentAsync` sur ce chemin — la trace d'audit reste complète (mêmes champs tracés qu'avant)
- [ ] `AddFlagsAsync` (non bloquant) sur la propagation
- [ ] Invalidation `folder:status` après propagation — unit test
- [ ] Aucune donnée de santé en clair dans les logs ni dans le payload de l'action différée (folder + uid uniquement, jamais de contenu)
- [ ] **Contre-épreuve au banc (bloquante pour le merge, pas pour la PR)** : tir `journey` n300 iso-conditions avant/après :
  - `mark_read` p50 **≤ 50 ms** (référence : 331 ms) et p95 dans la grille SLO
  - acquisitions `imap_session`/`UpdateFlag` déplacées hors du chemin de réponse (la famille peut subsister, portée par le worker)
  - vérification par base toujours PASS ; en fin de tir, l'état lu/non-lu IMAP a convergé avec la base (zéro action `MarkRead` en souffrance)

## Manual Test Plan

- Monter le banc : skill `loadtest-skill`
- Tir de contre-épreuve : `journey`, 300 médecins, latence `mssante`,
  iso-conditions avec `journey-mssante-n300-170512`
- Comparer : latence étape 8 « Marquer lu », table des verrous (`UpdateFlag`)
- Contrôle fonctionnel : marquer un message lu via l'API, vérifier
  (1) réponse immédiate, (2) `IsRead` en base, (3) flag `\Seen` visible côté
  IMAP (doveadm/GreenMail) en ≤ 10 s, (4) compteur de non-lus du dossier
  décrémenté après invalidation
- Contrôle de panne : couper Dovecot, marquer lu → réponse OK, action en
  attente ; relancer Dovecot → flag posé au rejeu

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — optimisation interne
- **Exigences DSR honorées** : non applicable — pas de changement fonctionnel
- **INS** : non applicable
- **Authentification PS** : inchangée — le contexte praticien est capturé/réhydraté par le patron existant, pas de contournement d'authentification
- **Habilitations** : non applicable — la propagation différée agit sur la boîte du praticien qui a fait le geste, cloisonnement inchangé
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé — la trace d'audit du marquage est conservée à l'identique (champs identiques, écriture déjà asynchrone via `AuditBackgroundService`)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé — le payload différé (folder + uid) ne contient aucune DSCP
- **AIPD / impact RGPD** : inchangé — aucun traitement nouveau


---

## Branches

- `api-mail` (pushed) : `fix/task-230-mark-read-async-propagation` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-230-mark-read-async-propagation
- `dtos-mss` (pushed, auto-inclus) : même nom de branche — **aucun changement de contrat attendu**, la contrainte absolue de la US étant l'identité de la route, du code HTTP et du corps de réponse. Pas de PR si aucun commit.

**Base** : `develop` d'`api-mail` au commit `61900e3` — **task-229 y est mergée**
(squash de la PR #157). La US se déclare indépendante de task-228/229 dans le code ;
partir d'un `develop` où elles sont mergées est néanmoins ce qui permettra de lire
la contre-épreuve au banc sans mélanger les effets.

**Dépendances** : aucune déclarée.

**Préfixe `fix/`** : la US corrige un défaut **mesuré** (`mark_read` p50 331 ms /
p95 524 ms au palier 300, hors grille SLO, 8,7 % du temps serveur), pas une
amélioration spéculative.

**Pré-flight** : les 6 repos automatisés vérifiables sont sur `develop`. Le chemin
d'`interop-cda` corrigé dans CLAUDE.md à task-229 est validé — plus de faux négatif.
