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


---

## Develop log

**Commit** : `751c99e` — `perf(mail): task-230 — marquer lu acquitte sur la base, la gommette IMAP part en arriere-plan groupee`
**Branche** : `fix/task-230-mark-read-async-propagation` (`api-mail`)
**Base** : `develop` @ `61900e3` (task-229 mergée)
`dtos-mss` : 0 commit — contrat inchangé.

### Ce qui a changé

| Fichier | Nature |
|---|---|
| `Services/Implementation/FlagPropagationService.cs` (nouveau) | Enfilage + propagation groupée hors requête |
| `Services/Interfaces/IFlagPropagationService.cs` (nouveau) | Deux portes distinctes : `Enqueue…` (requête) et `Propagate…` (rejeu) |
| `Services/Repository/MailAuditSnapshot.cs` (nouveau) | Les 4 champs d'audit, et rien d'autre |
| `EmailFlagService.cs` | Chemin synchrone sans IMAP, lecture d'audit minimale, trace rendue véridique |
| `PendingActionService.cs` | Réclamation atomique ; rejeu branché sur la propagation directe |
| `PendingActionRepository.cs` + interface | `TryClaimForProcessingAsync`, `GetPendingMarkReadAsync`, `ReleaseClaimAsync` |
| `MailRepository.cs` + interface (+ mock) | `GetMailAuditSnapshotAsync` — une projection |

### Le remède, et l'écart argumenté avec la US

La US privilégiait la file persistée (`PendingActions`) pour sa rejouabilité après
un crash — **argument juste** — mais posait aussi une borne : propagation
« attendue en secondes », « jamais au-delà de la fenêtre du `folder:status` (10 s) ».

**Vérifié dans le code** : `ProcessPendingActionsAsync` n'est drainée que par une
passe de synchronisation (`BackgroundSyncService`) ou un appel explicite du client
(`ConnectionController`) — **aucun timer interne**. La voie persistée seule aurait
donc respecté la *lettre* du remède en manquant la borne que la **même US** impose,
avec une latence indéterminée et, sous le scénario de charge, potentiellement
infinie.

**Les deux briques sont donc utilisées pour ce que chacune sait faire** :
`PendingActions` **persiste** (durabilité, déduplication, annulation par action
opposée — tout ce que le PO voulait), `IBackgroundTaskQueue` **propage tout de
suite**.

### Le groupement d'une rafale — demandé par la US, et sans fenêtre d'attente

La US l'autorisait : *« en cas de rafale, les propagations peuvent être regroupées
(la voie bulk `AddFlagsAsync` existe déjà) mais jamais retardées au-delà de 10 s »*.

Dépiler sa boîte est le geste **normal** : 20 clics faisaient 20 trajets et
**20 prises du verrou de session** — celui dont cette campagne cherche précisément à
réduire la contention. Sortir le travail de la réponse HTTP ne l'aurait pas réduit,
seulement déplacé.

**Aucune temporisation n'a été ajoutée**, et c'est le point de conception : la file
persistée **est déjà l'accumulateur**, puisque chaque marquage y écrit sa ligne. Une
course ramasse donc tout ce qui est en attente **pour ce dossier au moment où elle
part**, et le pose en **un** `STORE` multi-UID (IMAP l'accepte nativement).

| Situation | Coût |
|---|---|
| 20 clics — la 1ʳᵉ course | **1** trajet, **1** prise du verrou, 20 UID dans un `STORE` |
| Les 19 courses suivantes | **0** trajet, **0** verrou — rien à réclamer, elles sortent |
| Un seul message | 1 trajet, et **rien n'attend** |

Le groupement est **opportuniste** : il se produit exactement quand une rafale se
chevauche.

### Trois défauts trouvés en chemin

**a) Une boucle sans fin — de ma conception.**
Le rejeu appelait `UpdateEmailReadStatusAsync`, qui **enfile**. Or la déduplication
ne voit que les actions `Pending`, et celle en cours de rejeu vient de passer à
`Processing` : une **nouvelle** action était donc insérée avant que l'originale ne
soit supprimée. **Une ligne de plus par passe de synchronisation**, chacune payant
un aller-retour IMAP, une file qui ne se vide jamais. Corrigé par deux portes
distinctes ; un test interdit au rejeu d'appeler la méthode qui enfile.

**b) Deux pods pouvaient traiter la même action — préexistant.**
`MarkAsProcessingAsync` écrivait **sans condition** : deux pods ayant chargé la même
ligne `Pending` réussissaient tous les deux. `TryClaimForProcessingAsync` porte
désormais sa condition dans l'ordre SQL (`WHERE Status = Pending`) : **la base
arbitre**, exactement un appelant obtient la ligne. **Aucune migration** — la
condition remplace le jeton de concurrence absent du schéma (règle 7c non
déclenchée). La duplication était bénigne tant que les actions rejouées étaient
idempotentes (`STORE +FLAGS` l'est) ; elle cesse de dépendre de cette propriété.

**c) Une action `Failed` n'est jamais rejouée — préexistant.**
`MarkAsFailedAsync` écrit `Failed`, mais `GetPendingActionsAsync` ne lit que les
`Pending` : une action ayant échoué **une fois** est abandonnée en silence, et le
`RetryCount >= 3` de `HandleActionFailureAsync` est **du code inatteignable** (on ne
dépasse jamais 1). Cela **vidait de son sens l'argument** qui justifiait la voie
persistée. Le défaut général est **signalé et non corrigé** (il porte la sémantique
du rejeu hors ligne, hors périmètre), mais le chemin des flags ne peut pas s'y
appuyer : `ReleaseClaimAsync` rend la ligne à `Pending` avec une borne de
tentatives.

### La trace d'audit ne ment plus

Elle inscrivait `ServerResponse = "OK flags updated"` — **la réponse du serveur**.
La propagation étant différée, garder cette phrase aurait **écrit dans un registre
réglementaire une réponse serveur qui n'a pas eu lieu**. Le champ dit l'état vrai
(« queued for background propagation »), et `Success` porte ce que la trace atteste
réellement : **l'accès du praticien au message**, vrai dès le commit — ce que la
traçabilité PGSSI-S attend d'un `MailRead`.

### Hygiène du même chemin

- **Lecture d'audit minimale.** `GetMailAsync(Header)` chargeait étiquettes,
  destinataires, pièces jointes — et le **contenu clinique** dès que le message
  portait des documents médicaux, pour renseigner un objet et trois adresses. Un
  changement d'état de flag n'a **aucune raison** de lire ce matériau.
- **`AddFlagsAsync`** (extension asynchrone déléguant à `StoreAsync`) au lieu de
  l'extension **bloquante** `AddFlags`, qui immobilisait un thread du pool pendant
  un aller-retour réseau sous latence MSSanté.
- **Invalidation de `folder:status`** après propagation : avant, `mark_read`
  n'invalidait **rien**, le compteur de non-lus restait faux jusqu'à 10 s.

### Deux conséquences signalées, non corrigées

**Un cas d'erreur change de code HTTP.** Une panne du serveur de messagerie ne fait
plus échouer la requête (5xx → 200). C'est la conséquence **directe** du remède — on
ne peut pas rapporter un échec qu'on n'attend plus — et la US la sanctionne
(« en dernier recours le flag reste posé en base »). Deux tests **unitaires** du
service qui encodaient l'ancien contrat synchrone ont été réécrits ; **les tests
d'intégration des routes, que le DOD protège, ne sont pas touchés**.

**Un glissement de sens dans la réponse.** Le corps contient
`{ queued = !IsOnlineMode }` : en ligne il dira `queued: false` alors que la
propagation **est** désormais enfilée. Le champ devient trompeur — mais le corriger
changerait le corps de réponse, ce que la contrainte absolue de la US interdit.

### Tests

| Fichier | Nb | Objet |
|---|---|---|
| `FlagPropagationServiceTests` (nouveau) | **11** | Aucun IMAP dans la requête / ordre persisté / outbox en panne / repli sans file / **groupement d'une rafale en 1 trajet** / courses surnuméraires à coût nul / partage entre pods / invalidation du compteur / relâchement de la réclamation sur échec / contexte praticien repeuplé / rejeu n'enfile rien |
| `EmailFlagServiceTests` (étendu) | +5 | Chemin synchrone sans IMAP, pas de lecture clinique pour l'audit, acquittement malgré panne serveur |
| `PendingActionServiceTests` (recalé) | 3 | Rejeu via la propagation directe, réclamation atomique attendue |

Ils comptent des **appels** — prises du verrou, ordres `STORE`, allers-retours —
jamais des durées.

**Preuve ROUGE du groupement** : en revenant à un UID par course,
`GroupsAWholeBurstIntoASingleRoundTrip` tombe.

Un enseignement de test : `AddFlagsAsync` est une **méthode d'extension** de MailKit
qui délègue à `StoreAsync`. NSubstitute ne peut donc pas la vérifier — les
assertions visent `StoreAsync`. Accessoirement, c'est ce qui **confirme** que le
code emprunte la voie asynchrone et non `AddFlags`.

### Validation

| Contrôle | Résultat |
|---|---|
| Build | **0 erreur, 0 avertissement** |
| Suite complète | **3 453 verts**, intégration incluse (**304 / 320**, 16 ignorés — le compte normal) |
| Flaky rencontré | `MarkdownPdfRendererTests.RenderHeadingPreservesText` — famille `Services/Export` (`UglyToad.PdfPig`), **6ᵉ occurrence** sur ces cycles, **vert 3 fois sur 3 en isolation**, aucun code d'export touché |

### 🚧 Ce que ce commit ne prouve PAS

**Aucune latence n'est mesurée.** Les tests prouvent des **nombres d'appels** : zéro
IMAP dans la réponse, un trajet pour une rafale, une prise de verrou au lieu de
vingt. Ils ne disent rien du p50 réel de `mark_read` (référence 331 ms).

La contre-épreuve `journey` n300 en iso-conditions est **bloquante pour le merge** et
exige le nœud de banc. C'est la leçon de **task-213** (correctif de verrou retiré
après mesure) et de **task-222** (US écrite sur un chiffre non opposable, annulée).

Un point demandera une attention particulière au tir : le travail IMAP n'a pas
disparu, il s'exécute désormais **pendant** que le médecin fait autre chose. Le
groupement doit plus que compenser ce chevauchement — c'est précisément ce que la
détention p95 du verrou `UpdateFlag` (référence 0,997 s à 5,11 acq/s) dira.
