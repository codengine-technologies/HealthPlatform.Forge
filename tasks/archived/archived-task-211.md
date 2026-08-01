# todo-task-211.md — `read_list` est sérialisé par trois verrous imbriqués, et le premier coûte une seconde sèche

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: task-205 — **satisfaite** (PR #131 mergée le 2026-07-31, squash `06f8a62`)
**Priorité**: **5/6** — Gain applicatif (ordre arrêté le 2026-07-31, objectif montée en charge)
> read_list a 718 ms, serialise par trois verrous. Le plus gros reliquat de latence -- avec la reserve, ecrite dans la task, que rien ne garantit que les verrous portent les 318 ms manquants.

> **Origine** : demande humaine du 2026-07-31, à la lecture de la re-mesure de
> task-205. La famine de ThreadPool est éteinte, mais `read_list` reste
> l'opération la plus lente du mix hors `send`/`enrich`, et **son profil de
> latence a changé de nature** : ce n'est plus du blocage de threads, c'est de
> l'attente en file derrière des verrous.

## Objective

Réduire la latence de `read_list`
(`GET /api/v1/mail/folders/{folder}/emails/{ids}`) en supprimant ou en
resserrant la **sérialisation** de son chemin, sans jamais affaiblir les
garanties de cohérence que ces verrous protègent.

Cible chiffrée héritée de task-205, **non atteinte** par elle et reprise ici :
`read_list` moyenne **< 400 ms** au palier 882 req/s, contre **718 ms** mesurés.

## Ce qui est mesuré

Banc du 2026-07-31, 200 praticiens, `mixed` 3 min, **après** les deux correctifs
de task-205, bases mail purgées (le chemin IMAP est donc réellement exercé) :

| Palier | moy | p50 | p90 | p95 | max |
|---|---|---|---|---|---|
| 882 req/s | **718 ms** | 213 ms | 1 324 ms | 1 480 ms | 60 004 ms |
| 972 req/s | **641 ms** | 478 ms | 1 507 ms | 1 650 ms | 11 764 ms |

**La médiane est saine, la queue est énorme** : au palier 882, une lecture sur
deux tient en 213 ms, mais la moyenne est 3,4 fois plus haute. C'est la
signature d'une **file d'attente**, pas d'un coût unitaire élevé. À comparer aux
autres opérations du même tir, dont la moyenne reste proche de leur médiane.

Contexte de saturation, pour écarter d'emblée deux fausses pistes :
la file du ThreadPool est **plate** (max 8 sur 5 réplicas) et le CPU par réplica
est de 1,1 à 1,4 cœur sur 24. **Ni famine de threads, ni pénurie de CPU.**

> ⚠️ **Les max à 60 004 ms ne sont pas un timeout serveur.** `getEmails` est le
> seul appel du harnais sans `timeout` explicite (`tests/loadtest-k6/lib/api.js`
> — `enrich` est à 300 s, `search` et `send` à 120 s), il hérite donc du **défaut
> k6 de 60 s**. Ne pas chercher une borne à 60 s dans le code applicatif : elle
> est côté client. La borne réelle du serveur est inconnue.

## Le chemin, et ses trois verrous

`ImapService.FetchMissingUidsWithLocksAsync` puis `ProcessEmailUidAsync`. Sur
base purgée — c'est-à-dire au premier accès à un UID, le cas que le banc exerce
et que vit un praticien devant un message jamais ouvert — **une lecture traverse
les trois** :

| # | Verrou | Où | Portée | Coût observé |
|---|---|---|---|---|
| 1 | `LockEmailFetchAsync` — `SemaphoreSlim(1,1)` | `ImapService.cs:1297` | par **(boîte, dossier)** | attente, borne 3 min |
| 2 | Verrou distribué Redis (`TryAcquireAsync`) | `ImapService.cs:1318` | par **(boîte, dossier)**, inter-réplicas | expiration 3 min |
| 3 | Verrou IMAP de **session** (`AcquireLockWithIdAsync`) | `ImapService.cs:1462` | par **(email, ClientSessionId)** | sérialise **toutes** les opérations IMAP de la session |

Le n°3 est le plus large : il ne protège pas `read_list` contre `read_list`, il
sérialise `read_list` **avec** `folders`, `send` et `enrich` de la même session.
Dans le mix du banc, quatre scénarios frappent les mêmes praticiens.

### Le défaut le plus net, et il est chiffrable à la lecture

`ImapService.WaitForDistributedLockAsync` (`:1412`) :

```csharp
for (var attempt = 0; attempt < 30; attempt++)
{
    await Task.Delay(1000, cancellationToken);   // ← AVANT le premier essai
    if (await distributedLockService.TryAcquireAsync(lockKey, TimeSpan.FromMinutes(3), cancellationToken))
        return true;
}
logger.LogWarning("Timeout waiting for distributed lock on {Folder}, proceeding anyway");
return false;
```

Trois problèmes distincts dans onze lignes :

1. **Le `Task.Delay` précède le premier essai.** Toute contention, même levée en
   1 ms, coûte **une seconde pleine**. Un `TryAcquireAsync` immédiat avant la
   boucle supprimerait ce plancher.
2. **Attente par sondage à pas fixe d'une seconde**, jusqu'à **30 secondes**.
   Aucun réveil sur libération.
3. **`proceeding anyway`** — au bout de 30 s, le code continue **sans le
   verrou**. Soit le verrou est nécessaire et c'est un défaut de cohérence
   potentiel, soit il ne l'est pas et l'attente est gratuite. **Cette
   ambiguïté doit être tranchée par cette US**, pas reconduite.

## Contenu attendu

### 1. Mesurer la contention avant de la corriger

Ne pas partir de la conclusion (même consigne que task-205, où le suspect
désigné s'est révélé innocent). **Instrumenter d'abord** : durée d'attente et
durée de détention pour chacun des trois verrous, en histogramme, par opération.

Le meter métier `Mssante.MailProcessing` et la section « Ressources &
télémétrie » de `report.py` (task-204) sont les véhicules existants — les
réutiliser, ne pas créer un canal parallèle. Le rapport de tir doit pouvoir
répondre : **lequel des trois verrous porte les 500 ms de queue ?**

### 2. Corriger ce que la mesure désigne

Pistes identifiées, à confirmer ou écarter par le n°1 — l'ordre reflète le
rapport gain/risque estimé, pas une obligation :

- **Essai immédiat avant la boucle d'attente** (`:1412`). Correction d'une ligne,
  supprime un plancher d'une seconde sur toute contention. Faible risque.
- **Trancher `proceeding anyway`** : soit le verrou distribué est nécessaire à la
  cohérence et l'expiration doit produire une erreur franche, soit il est
  opportuniste et l'attente de 30 s doit être drastiquement réduite. Décision à
  documenter dans la task.
- **Réduire la portée du verrou n°3.** Un verrou par session sérialise des
  opérations qui n'entrent pas en conflit. Piste : un verrou par
  **(session, dossier)**, ou une distinction lecture/écriture. ⚠️ C'est le
  changement le plus risqué : le verrou de session protège une **connexion IMAP
  unique** par session, qui n'est pas thread-safe. Ne pas le desserrer sans
  établir ce qui garantit alors l'exclusivité de la connexion.
- **Réexaminer la nécessité du n°1** quand le n°2 couvre déjà la même clé
  (boîte, dossier) : deux verrous de même portée, l'un en processus, l'autre
  distribué. Le premier est peut-être un raccourci d'optimisation qui a
  survécu — ou une protection réelle contre le coût du Redis. À dire.

### 3. Verrouiller par test

- Test de **concurrence** : N lectures simultanées des **mêmes** UIDs par la même
  boîte ne doivent produire qu'**un** aller-retour IMAP (la déduplication est la
  raison d'être de ces verrous — elle ne doit pas disparaître avec l'attente).
- Test de **non-régression de latence** sur le chemin non contendu : une lecture
  seule ne doit traverser **aucun** `Task.Delay`.
- Les garanties existantes restent vertes : `CrossTenantOwnershipTests` en
  particulier — un verrou mal reporté est une **fuite inter-praticiens**.

### 4. Re-mesurer au banc

Palier 882 req/s, mêmes paramètres que la campagne de référence. Critère
ci-dessous.

## Hors scope

- **La famine de ThreadPool** — éteinte par task-205, file max 8. Ne pas la
  rouvrir.
- **Le cache synchrone du SDK** — task-210, en cours de cadrage. Les deux US
  touchent `ImapService` : **risque de conflit réel**, voir « Ordonnancement ».
- **`MailClientSession.Dispose`** et **`EmailFlagService`** — blocages adjacents
  signalés par task-205, une task chacun.
- **Le timeout k6 de `read_list`** — le max à 60 s est un artefact du harnais.
  Lui donner un `timeout` explicite relève de l'outillage du banc (task-208/209),
  pas de cette US.
- **La localisation du nouveau genou** et **l'axe population** — campagnes de
  banc, pas du code.
- **`send` (1,7 s) et `enrich` (4,2 s)** — plus lentes encore, mais elles
  dégradent normalement sous charge et ne présentent pas ce profil de queue.

## Ordonnancement avec task-210

Les deux US modifient `ImapService` (13 sites de cache pour task-210, le bloc de
verrous pour celle-ci) et `ImapFolderService`. **Elles ne devraient pas être
menées en parallèle.**

Recommandation : **task-210 d'abord** — son diff est massivement mécanique et
mal placé pour absorber un conflit, quand celui de task-211 est localisé et
réfléchi. À trancher par le PO ; le point est signalé, pas décidé.

## Definition of Done

- [ ] Build passes (0 erreur)
- [ ] Tests pass (0 échec) — baseline 3 207 tests verts
- [ ] **Les trois verrous sont instrumentés** : attente et détention, par
      opération, lisibles dans le rapport de tir
- [ ] **La mesure désigne nommément** le ou les verrous responsables de la
      queue, avec les chiffres — avant toute correction
- [ ] Le sort de `proceeding anyway` est **tranché et justifié** dans la task
      (nécessaire → erreur franche, ou opportuniste → attente réduite)
- [ ] Test de concurrence : N lectures simultanées des mêmes UIDs → **un seul**
      aller-retour IMAP
- [ ] Test : une lecture non contendue ne traverse aucun `Task.Delay`
- [ ] Test unitaire par méthode dont la sémaphore change (>= 1)
- [ ] `CrossTenantOwnershipTests` vert — aucune clé de verrou réécrite au passage
- [ ] **Mesure au banc**, palier 882 req/s : `read_list` moyenne **< 400 ms**
      (contre 718) et p95 **< 800 ms** (contre 1 480)
- [ ] **Non-régression** : file ThreadPool max **< 20** par réplica (elle est à 8
      — cette US ne doit pas la rouvrir) et débit plateau **>= 863 req/s**
- [ ] Rapport de tir + ligne d'INDEX pour l'avant/après

## Manual Test Plan

### A — Non-régression fonctionnelle

1. `cd Api/Mail && dotnet run --project src/Api`, puis Blazor, connexion PSC.
2. Ouvrir un dossier, ouvrir un message **jamais lu** (chemin IMAP), revenir,
   le rouvrir (chemin base). Les deux doivent afficher le même contenu.
3. **Deux onglets sur la même boîte**, ouvrir **simultanément** le même message
   jamais lu. Attendu : les deux affichent le message, **aucune erreur**, et le
   journal ne montre **qu'un** fetch IMAP.
4. Ouvrir deux messages **différents** jamais lus, simultanément, depuis deux
   onglets. Attendu : pas de sérialisation perceptible de l'un derrière l'autre.

### B — Résilience du verrou distribué

5. `docker stop` Redis, puis rejouer l'étape 2.
6. Attendu : l'application **reste fonctionnelle**. Le comportement retenu pour
   `proceeding anyway` doit être **celui décidé et documenté**, pas une surprise.

### C — Re-mesure au banc (c'est ici que se juge l'US)

7. Banc en profil loadtest (skill `loadtest-skill`), 200 praticiens, **tables
   mail purgées** — `YES=1 tests/loadtest-k6/reset-state.sh --keep-maildir`
   (le drapeau préserve le corpus de 3,3 Go, cf. task-205).
8. `tests/loadtest-k6/observe.sh start 900`
9. ```bash
   BYPASS_KEY=loadtest-local-only USERS=200 MESSAGES_PER_USER=100 \
   SESSION_ROTATION=0.001 RPS=980 VU_TAIL_FACTOR=8 ENRICH_SHARE=0.05 \
     tests/loadtest-k6/run.sh mixed --env VUS=60 --env DURATION=3m
   ```
10. `tests/loadtest-k6/report.sh <json> --expected 100`, table de latence par
    opération, ligne `read_list`.

**Baseline opposable** (post-task-205, banc du 2026-07-31, palier 882) :

| Grandeur | Baseline | Cible |
|---|---|---|
| `read_list` moy | 718 ms | **< 400 ms** |
| `read_list` p95 | 1 480 ms | **< 800 ms** |
| File ThreadPool | 8 / 6 / 6 / 5 / 4 | reste < 20 |
| Débit plateau | 863,0 req/s | >= 863 |

## Ce que le cycle autonome peut livrer, et ce qui restera dû

| Item | `/develop` | Banc / HAG |
|---|---|---|
| Instrumentation des trois verrous | ✅ | — |
| Correctifs + tests de concurrence | ✅ | — |
| Build / tests verts | ✅ | — |
| Désignation chiffrée du verrou coupable | — | ✅ |
| `read_list` < 400 ms, p95 < 800 ms | — | ✅ |
| Non-régression file ThreadPool / débit | — | ✅ |

Précédent explicite : task-204 et task-205 ont toutes deux séparé la moitié
« code » de la moitié « mesure ».

**Réserve honnête.** La cible de 400 ms est héritée de task-205, où elle a été
posée **avant** de savoir ce qui ralentissait `read_list` — elle visait alors une
famine de threads qui n'est plus le sujet. Rien ne garantit que la sérialisation
porte les 318 ms manquants : une partie peut venir du fetch IMAP lui-même, que
cette US ne touche pas. **Si l'instrumentation du n°1 montre que les verrous
pèsent peu, il faut le dire et refermer l'US sur ce constat** plutôt que
desserrer des verrous pour rien — desserrer un verrou de cohérence sans gain
mesuré serait un mauvais échange.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville — messagerie MSSanté du praticien.
- **Vague Ségur** : hors vague — optimisation technique interne, aucune exigence
  de référencement créée ni modifiée.
- **Exigences DSR honorées** : aucune nouvelle. L'US **préserve** MSSanté-2.4
  (lecture des messages), chemin qu'elle optimise sans en changer la sémantique.
- **INS** : non manipulée directement. `read_list` rend des en-têtes ; aucune clé
  de verrou ne dérive d'une INS.
- **Authentification PS** : inchangée — PSC / e-CPS, eIDAS substantiel.
- **Habilitations** : **c'est le point de vigilance de cette US.** Les clés de
  verrou portent le cloisonnement par praticien (`fetch:{email}:{folder}`,
  `{email}_{ClientSessionId}`, `RedisKeys.Lock.MailFetch`). Élargir une portée
  ou réécrire une clé peut produire une **fuite inter-praticiens** : deux
  praticiens partageant un verrou, donc potentiellement une connexion IMAP.
  `CrossTenantOwnershipTests` est la garde existante et doit rester verte.
  **Aucune clé ne doit être réécrite sans que le test correspondant soit
  explicitement renforcé.**
- **Interop CI-SIS** : non applicable.
- **Tracé PGSSI-S** : aucun **nouvel** évènement métier. L'instrumentation du
  contenu attendu n°1 produit des **métriques techniques** (durées de verrou),
  sans donnée de santé ni identifiant patient — la clé de verrou contient un
  email de praticien, qui ne doit **pas** être promu en étiquette de métrique
  (cardinalité et donnée personnelle). Agréger par opération, pas par praticien.
- **Consentement patient** : non applicable.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : périmètre inchangé. Aucun changement de donnée stockée,
  de TTL ni de rétention.
- **AIPD / impact RGPD** : inchangée — aucune nouvelle finalité, donnée,
  destinataire ni durée de conservation.

## Branches

- `api-mail` (pushed) : `fix/task-211-read-list-lock-contention` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-211-read-list-lock-contention
- `dtos-mss` (pushed, auto-inclus) : `fix/task-211-read-list-lock-contention` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/fix/task-211-read-list-lock-contention
  (aucun changement de contrat attendu — branche créée proactivement, pas de PR si aucun commit)

### Ordonnancement avec task-210 — tranché par le lancement

`task-210` **n'existe pas encore** (aucun `tasks/*-task-210.md`) : elle est « en
cours de cadrage ». Il n'y a donc aucun conflit à l'instant du `/start`. En
lançant task-211 d'abord, le PO inverse la recommandation de la task : c'est
task-210 qui devra absorber ce diff. Il est localisé (le bloc de verrous de
`ImapService`), là où celui de task-210 serait massivement mécanique — le coût
de l'inversion est donc réel mais borné.

### Ce que `/develop` peut livrer, et ce qu'il ne doit PAS faire

La task exige **de mesurer avant de corriger** (contenu attendu n°1), et le banc
n'est pas monté. Le périmètre autonome se limite donc à ce qui se justifie
**sans** la mesure :

| Item | Autonome ? |
|---|---|
| Instrumentation des trois verrous (attente + détention) | ✅ — c'est le prérequis de la mesure |
| Essai immédiat avant la boucle d'attente (`:1412`) | ✅ — un plancher d'une seconde sur toute contention est du gaspillage, quel que soit le coupable |
| Trancher `proceeding anyway` | ✅ — décision de conception, se lit dans le code |
| Tests de concurrence et de non-contention | ✅ |
| **Réduire la portée du verrou n°3 (session)** | ❌ — la task l'exige **après** la mesure, et prévient que c'est le changement le plus risqué (fuite inter-praticiens) |
| **Supprimer le verrou n°1** | ❌ — même raison |
| Désignation chiffrée du coupable, cibles 400 ms / 800 ms | ❌ — banc |

> ⚠️ **La réserve honnête de la task s'applique** : rien ne garantit que les
> verrous portent les 318 ms manquants. Si la mesure montre qu'ils pèsent peu, la
> conclusion attendue est de **le dire et refermer**, pas de desserrer un verrou
> de cohérence sans gain établi.

## Develop log

- **Repos touchés** : `api-mail`. `dtos-mss` : aucun commit → pas de PR.
- **Commits** : `ce36566` (instrumentation + backoff), `d2641bf` (`/simplify`),
  `2300ee8` (S3776/S138), `d5d9ac8` (merge `develop`).
- **Build / tests** : Release 0 erreur ; **3 243 réussis** ; `selftest.sh` vert
  (15 node + 96 Python après synchronisation).

### Deux corrections de l'énoncé, établies en lisant le code

1. **Le correctif d'une ligne proposé aurait été un no-op.** L'essai
   `TryAcquireAsync` immédiat **existe déjà** au site d'appel ; la boucle
   d'attente n'est atteinte qu'après son échec. Le vrai défaut est le **pas de
   sondage** — une seconde fixe, sans réveil à la libération. Remplacé par un pas
   croissant 25 ms → 500 ms.
2. **`proceeding anyway` tranché : le verrou distribué est OPPORTUNISTE.** Trois
   éléments l'établissent dans le code existant (l'appelant fetch quand même en
   cas d'échec ; le code re-vérifie la base après acquisition ; le commentaire
   parle de prévenir un fetch concurrent, ce qui est une économie). Budget ramené
   de **30 s à 5 s**, issue enregistrée pour rendre le compromis mesurable.

### Ce qui n'a PAS été touché, délibérément

La portée du verrou de session (n°3) et l'existence du verrou en processus (n°1).
La task les subordonne à la mesure, et le n°3 protège une connexion IMAP unique,
non thread-safe. **La réserve de la task tient** : si la mesure montre que les
verrous pèsent peu, la conclusion attendue est de le dire et refermer.

## Sonar log

**Zéro finding attribuable à cette task.**

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| `new_violations` | 4 | **3** | −1 |
| **Findings C#** | **2** | **0** | **−2** |
| Bugs / Vulnérabilités / Hotspots | 0 / 0 / 0 | 0 / 0 / 0 | = |
| Coverage projet / new | 86,7 % / 86,5 % | 85,6 % / 84,9 % | −1,1 / −1,6 pt |
| Reliability / Security / Maintainability | A / A / A | A / A / A | = |

Les 2 findings C# (`S3776`, `S138` sur `FetchMissingUidsWithLocksAsync`) étaient
de la dette **introduite par cette task** — l'instrumentation avait fait franchir
les deux plafonds. Corrigés par extraction de quatre helpers nommés.

Les 3 restants sont dans `report.py`, aucun dans ce diff : `reduce_prom_matrix`
et `_observe_table` (task-204), et `pinned_candidates` — qui franchit le seuil via
la **PR #135**, déjà sur `develop` et intégrée ici par la synchronisation. La
baisse de couverture vient de la même synchronisation.

## PRs

- `api-mail` : **https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/137**
  — label `awaiting-human-merge`, `MERGEABLE`, 4 commits.
- `dtos-mss` : aucune PR — branche sans commit, ref distant supprimé.

## Code Review Summary

Verdict : **APPROVED** — 0 blocage. Une correction issue de `/simplify`, non
cosmétique : la détention du verrou distribué était mesurée avec le chronomètre
du verrou en processus, démarré **avant** son acquisition — sur une table dont
l'unique raison d'être est d'attribuer la queue au bon verrou, une surestimation
vaut une fausse désignation.

**Synchronisation** : `develop` avait avancé (PR #135, même fichier `report.py`).
Merge sans conflit, 96 tests Python verts après coup.

## Reste à faire par le humain

1. **Tester puis merger la PR #137** — HAG, règle 10.
2. **Cinq critères de DOD restent au banc** : désignation chiffrée du verrou
   coupable, `read_list` < 400 ms et p95 < 800 ms, non-régression ThreadPool et
   débit, rapport + ligne d'INDEX. La table « Verrous du chemin `read_list` » du
   rapport est faite pour y répondre.
3. Le test de concurrence « N lectures simultanées → un seul fetch IMAP » reste
   dû : la déduplication est couverte par un test unitaire, mais le cas
   N-concurrent réel exige la base et le banc.

## Merged

- **Date** : 2026-08-01
- `api-mail` : squash `cabc1a4` — PR
  [#137](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/137)
  fermée. Ref distant supprimé, **branche locale conservée**.
- `dtos-mss` : aucune PR (branche sans commit) — ref distant déjà supprimé au
  `/review`, repo sur `develop`.
- `client-angular`, `client-mobile`, `devops`, `psc-proxy-*` : hors périmètre.
- **Staging** : `forge/staging-task-176-196-20260728` conservée — 211 est hors de
  sa plage `[176, 196]`, et ce run n'est pas drainé.
