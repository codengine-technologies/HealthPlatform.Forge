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


---

## Simplify log

**Repos éligibles touchés** : `api-mail` seul (`dtos-mss` : 0 commit, et hors
périmètre de cette étape).

**Commit** : `4c6e149` — `refactor(mail): task-230 — les trois chemins de flag partagent la lecture d'audit legere`

### Une prise, sur l'axe réutilisation — et c'est un défaut, pas un embellissement

J'avais créé `GetMailAuditSnapshotAsync` et ne l'avais utilisé qu'à **un endroit sur
trois**. `UpdateEmailFlaggedStatusAsync` et `UpdateEmailUnFlaggedStatusAsync`
payaient encore `GetMailAsync(Header)` — qui charge étiquettes, destinataires,
pièces jointes, et **le contenu clinique** dès que le message porte des documents
médicaux — pour renseigner un objet et trois adresses.

`TraceFlagChange` prend désormais un `MailAuditSnapshot`. **Les champs tracés sont
inchangés**, format `;` des destinataires compris : deux stubs de test ont été
recalés sur la nouvelle source, pas les assertions.

> **Extension du périmètre littéral de la task, déclarée.** Le défaut mesuré était
> « marquer lu ». Mais c'est **littéralement le même défaut**, le remplacement est
> mécanique, et un changement d'état de flag n'a aucune raison de lire le matériau
> clinique — où que ce soit. Le même motif (helper créé puis non appelé à l'un des
> endroits) avait déjà été attrapé à task-228 : c'est précisément ce que cette étape
> est là pour voir.

### Une asymétrie constatée et NON corrigée

`UpdateEmailUnReadStatusAsync` (« marquer non lu ») n'émet **aucune trace d'audit**,
là où « marquer lu » et les deux « suivi / non suivi » en émettent une. Ce n'est pas
un oubli que la forge doit combler seule : ajouter ou non une trace réglementaire est
une **décision de traçabilité PGSSI-S**, pas un choix d'implémentation. Signalé pour
arbitrage.

### Re-validation

| Suite | Résultat |
|---|---|
| Build solution | **0 erreur, 0 avertissement** |
| `application` | **1 977 / 1 977** |
| `infrastructure` | 422 / 422 |
| `domain` | 102 / 102 |
| `api` | 649 / 649 en compilation normale |

Les 4 échecs de `api` observés sous `--artifacts-path` sont l'artefact d'environnement
connu (les scans de sources remontent au `RepoRoot()` depuis `AppContext.BaseDirectory`,
déplacé hors du dépôt par ce contournement de verrous).

Le flaky `Services.Export.MarkdownPdfRendererTests.RenderHeadingPreservesText` s'est
manifesté une fois de plus (famille `UglyToad.PdfPig`), vert en isolation.

**Routage** : `api-mail` touché ⇒ `/sonar 230`.


---

## Develop log — extension du périmètre aux quatre gestes

**Commit** : `b3501ec` — `fix(mail): task-230 — les quatre gestes de flag sur le meme mecanisme, une divergence visible en moins`

**Origine** : question humaine du 2026-08-05 — *« je ne comprends pas pourquoi dans
`ProcessActionAsync`, seul `PendingActionTypes.MarkRead` a été touché. Est-ce que ton
implémentation est bien sur tout le périmètre des pending action ou seulement sur
MarkRead ? »*

### La réponse en deux temps

**Le correctif de ré-entrance était correctement borné.** Seule
`UpdateEmailReadStatusAsync` était devenue une méthode **qui enfile** ; les trois
autres faisaient l'IMAP en direct, donc les appeler depuis le rejeu ne créait aucune
boucle. Sur ce point précis, rien à étendre.

**Mais l'asymétrie créait une divergence visible pour le médecin**, et c'est le vrai
sujet. Le geste est normal — ouvrir un message puis le remettre en non lu pour le
garder dans sa liste à traiter :

| # | Ce qui se passait |
|---|---|
| 1 | Ouverture → `IsRead = true` en base, pense-bête `MarkRead` écrit, course lancée |
| 2 | Clic « non lu » → `IsRead = false` en base, et **IMAP synchrone** retire `\Seen` |
| 3 | La course `MarkRead` part **ensuite** → elle **repose** `\Seen` |

**Base « non lu », serveur « lu ».** Le pense-bête supprimé, rien ne corrige, et la
synchronisation suivante pouvait **annuler le geste du médecin en silence**.

### Ce qui le ferme, par construction

Les quatre gestes empruntent le même mécanisme, chacun sous son propre nom d'action.
L'annulation par action opposée de l'outbox (`OppositeActions`) — qui **ne servait à
rien dans ce cas** — fait alors son travail : enfiler « non lu » **supprime** le
pense-bête « lu », et la course déjà lancée ne trouve plus rien à réclamer (zéro
aller-retour, zéro verrou). Plus aucune règle à « penser à respecter ».

`FlagChangeKind` porte les quatre gestes, et une table de correspondance unique dit
pour chacun l'ordre IMAP et s'il change le compteur de non-lus :

| Geste | Ordre | Invalide `folder:status` ? |
|---|---|---|
| `MarkRead` | pose `\Seen` | oui |
| `MarkUnread` | retire `\Seen` | oui |
| `MarkFlagged` | pose `\Flagged` | **non** |
| `MarkUnflagged` | retire `\Flagged` | **non** |

« Suivi » ne l'invalide pas : `folder:status` ne porte que `Count`, `Unread` et
`UidNext`, que ce geste ne touche pas — invalider ferait relire le dossier au serveur
pour rien.

Le regroupement est **par geste** et non seulement par dossier : poser et retirer
`\Seen` sont deux ordres `STORE` opposés, qu'on ne peut pas mêler. Deux gestes en
attente sur le même dossier font donc deux trajets — le minimum, non une
inefficacité. `RemoveFlagsAsync` (asynchrone) remplace `RemoveFlags` (bloquante),
comme pour l'ajout.

### ⚠️ Trois corrections, dont une où je m'étais trompé en l'affirmant

**a) J'ai affirmé à tort que le cycle de dépendances avait disparu.**
Retirer `IEmailFlagService` de `PendingActionService` ne l'a **pas** supprimé : je
l'ai remplacé par `IFlagPropagationService`, ce qui a rendu la boucle **plus
directe**. Le conteneur l'a dit (`A circular dependency was detected`) et **les tests
d'intégration l'ont fait remonter**. Le cycle est **réel et inévitable** : enfiler
exige l'outbox, rejouer exige la propagation. Il est cassé du côté **froid** (le
rejeu résout paresseusement) pour que le chemin **chaud** — la réponse du praticien —
garde une dépendance directe vérifiée à la compilation. C'est mieux que la version
initiale, mais **pas pour la raison que j'avais donnée** ; le commentaire du code
porte la correction explicite.

**b) Mon `try/catch` best-effort masquait un défaut de résolution DI.**
`PendingActionRepository` a **deux constructeurs à trois paramètres** ; dans les
montages où `MailDataContext` est enregistré (fixtures d'intégration), le conteneur
ne sait pas choisir. L'exception était **avalée** par le `catch` : la voie de
**durabilité était donc silencieusement morte** là, le journal ne parlant que d'une
« panne d'outbox ». **Production non concernée** — `MailDataContext` n'y est pas
enregistré, un seul constructeur est satisfaisable. Corrigé à l'enregistrement dans
les deux fixtures, avec la raison écrite.

> Au passage : `[ActivatorUtilitiesConstructor]` **n'est pas** le remède — cet
> attribut n'est lu que par `ActivatorUtilities`, pas par la sélection du conteneur
> intégré. Tenté puis **retiré**, plutôt que de laisser un attribut décoratif
> accompagné d'un commentaire faux. (`FolderRepository` le porte, mais son second
> constructeur a deux paramètres : c'est l'**arité** qui le sauve, pas l'attribut.)

**c) Mon test de l'enchaînement ne valait rien.**
Écrit dans `FlagPropagationServiceTests`, il **stubbait lui-même** « plus rien en
attente » : il passait donc **aussi avec l'asymétrie rétablie**, ne testant que la
propriété déjà couverte (une course sans rien à réclamer ne fait rien). Découvert
**seulement en posant la preuve ROUGE**. L'asymétrie vivait dans `EmailFlagService` :
le test y est désormais, en `Theory` sur les trois gestes, et **rétablir l'asymétrie
fait tomber 2 tests**. L'ancien est renommé pour ce qu'il prouve, avec mention
explicite de ce qu'il ne prouve pas.

> Troisième test-sans-valeur de la campagne (task-227, task-229, celui-ci), et
> toujours découvert de la même façon : **en cassant volontairement le code**. Le
> constat mérite d'être noté tel quel — la preuve ROUGE n'est pas une formalité de
> DOD, c'est le seul moment où un test vert est mis en cause.

### Tests

**+13** : 4 de périmètre (un par geste, nom d'action attendu), 4 de correspondance
poser/retirer, 1 sur la non-invalidation du compteur pour « suivi », 3 de rejeu
recalés, 1 sur l'enchaînement.

**4 tests unitaires** encodant l'ancien contrat synchrone ont été réécrits — et
**les tests d'intégration des routes passent sans modification d'aucune assertion**
(10/10 sur `EmailManagementUseCaseTests`), ce qui est le critère du DOD.

### Validation

| Contrôle | Résultat |
|---|---|
| Build | **0 erreur, 0 avertissement** |
| Suite complète | **3 467 / 3 467 verts**, intégration incluse (304/320, 16 ignorés) |
| Preuve ROUGE de l'asymétrie | ✅ 2 tests tombent quand « non lu » redevient synchrone |

La contre-épreuve au banc reste due et **bloquante pour le merge** — elle mesurera
désormais les **quatre** gestes d'un coup.


---

## Sonar log

**Quatre analyses complètes**, et chacune a servi à quelque chose de différent — la
première à mesurer, les trois autres à vérifier qu'une correction portait, et deux
d'entre elles à **révéler du code devenu mort** par l'extension du périmètre.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| **Quality Gate (new code)** | **ERROR** | **ERROR** | inchangé — *dette antérieure* |
| `new_violations` | 28 | **28** | **0 — retour exact à la baseline** |
| `new_coverage` | 87,1 % | 86,9 % | −0,2 pt (seuil 80 — OK) |
| `new_duplicated_lines_density` | 0,081 % | **0,0795 %** | −0,001 pt (seuil 3 — OK) |
| `new_security_hotspots_reviewed` | 71,43 % | 71,43 % | = (seuil 100 — **ERROR**) |
| Bugs / Vulnérabilités / Smells | 1 / 0 / 27 | 1 / 0 / **27** | = |
| Coverage projet / Duplication | 86,9 % / 0,4 % | 86,9 % / 0,4 % | = |
| Reliability / Security / Maintainability | 3,0 / 1,0 / 1,0 | 3,0 / 1,0 / 1,0 | = |

### Dette nouvelle attribuable à task-230 : **zéro**, mesurée

| Scan | `new_violations` | Sur les fichiers de task-230 | Ce qu'il a appris |
|---|---|---|---|
| 1 — après `/develop` + `/forge-simplify` | 31 | **3** | `S1067` (dépôt), `S3267` (boucle), `CA1822` (test) |
| 2 — après extension aux 4 gestes | 29 | **1** | `S1144` — `ProcessEmailAsync` **devenu code mort** |
| 3 — après extension aux gestes en lot | 32 | **4** | `S4487` ×4 — **dépendances IMAP devenues non lues** |
| 4 — après nettoyage | **28** (= baseline) | **0** | — |

**Les scans 2 et 3 n'ont pas seulement validé, ils ont trouvé.** Chacun a signalé du
code que l'extension venait de rendre inutile, et que j'aurais laissé sinon :

- **Scan 2** — `S1144` : `ProcessEmailAsync` n'était plus appelé. En le regardant, j'ai
  vu que les quatre méthodes **en lot** s'appuyaient encore sur son cousin
  `ProcessEmailsBulkAsync` — donc qu'il restait un **second chemin d'écriture de
  flag**, synchrone, portant une version plus étroite du défaut qu'on venait de
  fermer. Les gestes en lot ont rejoint le mécanisme ; les deux méthodes ont été
  supprimées. **Il ne reste qu'un seul chemin d'écriture de flag.**
- **Scan 3** — `S4487` ×4 : `EmailFlagService` portait encore
  `IImapConnectionService`, `IMailClientSessionManager`, `UserContextInfo` et un
  logger — tout le nécessaire pour poser un flag lui-même — alors qu'aucun n'était
  plus lu. Les garder aurait été **pire qu'inutile** : ils auraient suggéré à tout
  lecteur futur que le travail IMAP se fait là. **Trois dépendances au lieu de
  sept.**

Les trois findings du scan 1 : `S1067` (cinq conditions dans une expression du dépôt —
posées en deux temps, même requête pour la base), `S3267` (boucle remplaçable par
`Select`) et `CA1822` (helper de test rendu `static`).

### Pourquoi le Quality Gate reste ERROR

Piège documenté de la *new-code period* (`PREVIOUS_VERSION`), qui englobe des tasks
déjà mergées. Les 28 violations sont **toutes antérieures** : harnais k6
(`report.py`, `journey.js`, `journey-model.js` — task-174/224) plus 2 `S103`
préexistants. Et les **2 security hotspots** qui plafonnent le ratio à 71,43 % sont
les deux `Math.random()` de `journey.js`.

> ⚠️ **Le même point ouvert qu'à task-228 et task-229, pour la troisième fois** : ces
> 2 hotspots sont en `TO_REVIEW` et maintiendront le Quality Gate en ERROR à **chaque
> cycle futur**. Les marquer *safe* est très probablement correct (tirages
> pseudo-aléatoires de sélection dans un scénario de charge, aucun rôle
> cryptographique), mais c'est un **jugement de sécurité** que la forge ne prend pas
> au passage dans le cycle d'une autre task. Trois cycles consécutifs l'ont signalé —
> il mérite sa propre décision.

### Suites de tests pendant les scans (Release)

| Scan | Résultat |
|---|---|
| 1 | **3 453 / 3 453** verts |
| 2 | **3 467 / 3 467** verts |
| 3 | 1 échec — `MailExportServiceTests.BuildPdfWithoutAttachmentsOmitsAttachmentSection` |
| 4 | 1 échec — `PgBouncerTransactionPoolingTests.ConcurrentClients_AreMultiplexed_OntoBoundedPostgresBackends` |

Les deux échecs appartiennent à des familles de flakies **connues et préexistantes** :
`Services/Export` (`UglyToad.PdfPig`) et la contention Docker de PgBouncer. Aucun code
d'export ni de pooling n'est touché par ce diff, et chacun est vert aux autres scans
sur le même code.

> **La famille `Services/Export` s'est manifestée sept fois** au cours des cycles
> task-228, 229 et 230. Signalée à chaque fois, jamais corrigée : elle mérite une task
> dédiée plutôt qu'une mention de plus.

**Routage** : `client-angular` et `client-mobile` non touchés ⇒ `/lint-angular`,
`/lint-mobile` et `/verify-visual` skippent ⇒ `/review 230`.


---

## PRs

- **`api-mail`** : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/159 — label `awaiting-human-merge`
  Branche `fix/task-230-mark-read-async-propagation`, **5 commits** :
  `751c99e` (acquittement optimiste + groupement), `4c6e149` (lecture d'audit légère
  aux 3 chemins), `b3501ec` (les 4 gestes sur le même mécanisme), `f1a4360` (gestes en
  lot + suppression des chemins morts), `809ceb3` (dépendances IMAP retirées).
- **`dtos-mss`** : branche créée (auto-inclusion), **0 commit** ⇒ **aucune PR**. Contrat
  inchangé — la contrainte absolue de la US.

Repos non touchés : `client-blazor`, `client-angular`, `client-mobile` ⇒ `/lint-angular`,
`/lint-mobile` et `/verify-visual` ont skippé proprement.

## Code Review Summary

**Verdict : APPROVED** — 16 fichiers revus, **0 blocage**, 3 suggestions.

### Ce que la revue a vérifié plutôt que supposé

| Question | Réponse |
|---|---|
| La file de fond est-elle bornée ? | **Non** — `CreateUnbounded`, lecteur unique. Un lot de 1 000 enfile 1 000 éléments : ils ne bloquent pas la requête, et 999 sont des non-événements sérialisés derrière celui qui fait le trajet |
| Le chemin bulk a-t-il perdu son unique `STORE` ? | **Non** — le regroupement le reproduit : N actions ⇒ la 1ʳᵉ course les réclame toutes ⇒ 1 `STORE` |
| `AddFlagsAsync` est-elle bien la variante non bloquante ? | **Oui** — méthode d'extension déléguant à `StoreAsync` (c'est d'ailleurs pourquoi NSubstitute ne peut vérifier qu'elle, et non l'extension) |
| Une donnée de santé peut-elle atteindre un libellé ? | **Non** — libellés de tâche littéraux, logs limités au dossier et à des comptes |

### ⚠️ Suggestions non bloquantes

1. **Le chemin en lot fait N enfilages, donc jusqu'à 3N requêtes de déduplication** dans
   la requête (recherche d'action existante + recherche d'action opposée + insertion, par
   UID). L'ancien chemin faisait N mises à jour + **1** trajet IMAP. Le travail **réseau**
   disparaît, mais le travail **base** est multiplié — local et rapide, donc probablement
   gagnant net, mais un `QueueActionsAsync` par lot le réduirait à quelques requêtes.
   **À mesurer au banc plutôt qu'à supposer.**
2. File de fond non bornée à lecteur unique (voir ci-dessus).
3. `UpdateEmailUnReadStatusAsync` n'émet **aucune trace d'audit**, là où les trois autres
   gestes en émettent une. Ce n'est pas à la forge de combler : ajouter une trace
   réglementaire est une **décision de traçabilité PGSSI-S**. Signalé pour arbitrage.

## Validation

| Contrôle | Résultat |
|---|---|
| Build | **0 erreur, 0 avertissement** |
| Suite complète | **3 464 / 3 464 verts**, intégration incluse (304 / 320, 16 ignorés) |
| Tests d'intégration des routes de flag | ✅ **10/10 sans modification d'aucune assertion** — le critère du DOD |
| Preuves ROUGE | **6 propriétés**, chacune neutralisée et rattrapée |
| Dette Sonar nouvelle | **zéro**, prouvée par 4 scans (31 → 29 → 32 → 28 = baseline) |
| Sync `develop` | ✅ already up to date |

### DOD

| Critère | État |
|---|---|
| Build 0 erreur | ✅ |
| Tests 0 échec | ✅ |
| **Zéro changement de contrat** | ✅ route, code HTTP et corps identiques ; tests d'intégration inchangés |
| Chemin synchrone sans aucun appel IMAP | ✅ test « le service de connexion n'est pas sollicité » |
| Propagation asynchrone : enfilage, rejeu après échec, déduplication, pas de perte au crash | ✅ les quatre, plus le partage entre pods |
| Relecture d'audit allégée, trace complète | ✅ `MailAuditSnapshot`, mêmes champs, format `;` conservé |
| `AddFlagsAsync` non bloquant | ✅ (et `RemoveFlagsAsync` pour les gestes inverses) |
| Invalidation `folder:status` après propagation | ✅ et **seulement** pour les gestes qui changent ce compteur |
| Aucune donnée de santé en clair | ✅ vérifié sur logs, clés et libellés |
| **Contre-épreuve au banc** | ⏳ **bloquante pour le merge, pas pour la PR** — nœud de banc requis |

### Au-delà du DOD

La US bornait le remède à `mark_read`. Sur question humaine, le périmètre a été étendu
aux **quatre gestes et à leurs variantes en lot** — non par souci de symétrie, mais parce
que l'asymétrie créait une **divergence visible** (base « non lu » / serveur « lu ») sur
un geste normal. Il ne reste qu'**un seul chemin d'écriture de flag** dans le code.

**Trois défauts préexistants** ont été trouvés en chemin : réclamation non atomique entre
pods, actions `Failed` jamais rejouées (code de retry inatteignable), constructeurs
ambigus pour le conteneur. Les deux premiers touchent directement la garantie de
durabilité que la US invoquait.

**Deux de mes propres erreurs** ont été corrigées et sont consignées : une boucle sans fin
dans le rejeu, et une affirmation fausse sur la disparition du cycle de dépendances.
