# todo-task-216.md — Retirer la voie d'écriture IMAP : elle supprime bien l'attente, mais l'envoi est plus lent avec elle que sans

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: task-215 (la contre-épreuve qui fonde la décision) — voir son
`## Bench log` et son `## Décision`
**Priorité**: **2** — pas d'urgence fonctionnelle (rien n'est cassé), mais une
connexion IMAP par praticien est un coût permanent qu'on paie pour rien, et le
plafond de connexions par boîte imposé par l'opérateur MSSanté n'est pas
éprouvé.

> **Ce n'est pas un revert de dépit.** Le correctif de task-213 fait exactement
> ce qu'il annonçait — c'est mesuré. Ce qu'il ne fait pas, c'est améliorer
> l'expérience du praticien, et il coûte une connexion par praticien.

## Objective

Que `AppendToSentAsync` et `AppendToDraftsAsync` repassent sur la voie de
lecture, et que la seconde connexion IMAP par praticien disparaisse.

## Ce que la mesure établit (task-215, 2026-08-02)

Trois tirs 500 praticiens, mêmes paramètres, protocole
échauffement → purge → tir. Le témoin A neutralise la voie d'écriture.

| | A — témoin | B | C |
|---|---|---|---|
| Attente p95 `AppendToSent` | 4,345 s | **0,005 s** | **0,005 s** |
| **`send` p95** | **7 874 ms** | 10 439 ms | 12 573 ms |
| **`send` moyenne / médiane** | **1,34** | 1,51 | 1,71 |
| Débit plateau | 791,1 req/s | 796,8 req/s | 802,7 req/s |

Le témoin **satisfait les deux critères du DOD de task-213** (p95 < 10 s, ratio
< 2) ; les tirs porteurs du correctif les manquent. Ce que la voie d'écriture
retire au verrou, elle le repaie en ouverture de connexion : la **détention**
d'`AppendToSent` monte de 3,974 s (A) à 4,557 / 5,287 s (B / C).

Le problème d'origine — un envoi sur vingt au-dessus de trente secondes — **n'est
plus reproductible sans le correctif** : les plafonds de banc levés depuis
(Dovecot `service imap` à 8000, `imap-login` high-performance, dossiers
`Sent`/`Drafts`/`Trash` déclarés) ont retiré la contention qui le produisait.
task-213 répondait à une mesure prise sur un banc bridé.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer qu'il faut tout défaire.** L'instrumentation de task-214
  (étiquettes `operation` et `lane`, mesure dans `ImapLockScope`, retrait de
  l'API dupliquée) **reste** — c'est elle qui a permis de trancher, et elle sert
  à toute mesure de verrou ultérieure. Seule la **voie** disparaît.
- **Ne pas présumer que le mécanisme décrit par task-213 était faux.** Il est
  confirmé : sans voie d'écriture, l'archivage attend 4,3 s au p95 derrière les
  lectures. C'est l'arbitrage coût/bénéfice qui bascule, pas le diagnostic.
- **Ne pas présumer que la conclusion vaut en production.** Elle vaut **pour cet
  hôte**, où l'infra du banc partage le CPU des réplicas. Ce qui la rend
  actionnable : les deux termes ont subi ce biais à l'identique, et c'est
  l'écart **entre eux** qui est mesuré. À écrire dans le code, pas seulement ici.
- **Ne pas présumer qu'un interrupteur serait plus prudent.** Il ferait porter à
  la production un chemin non exercé par défaut, donc non testé, pour un gain
  mesuré négatif. Si le besoin revient, la mesure et l'arbitrage sont écrits :
  la voie se re-crée en quelques lignes.

## Contenu attendu

1. `ImapService.WriteLane` et `UserContextInfo.ForWriteLane()` retirés, avec
   `WriteLaneSuffix` et `IsWriteLane` si plus aucun appelant.
2. **La mesure qui a tranché reste dans le code**, en commentaire là où la voie
   vivait : l'arbitrage de task-213 était juste sur le mécanisme et faux sur le
   bilan, et il faut qu'un futur lecteur trouve les deux, pas seulement le
   second. Réserve « pour cet hôte » incluse.
3. `MailProcessingMetrics.LockLaneWrite` : à **conserver** — l'étiquette `lane`
   n'a plus qu'une valeur utilisée, mais la garder documente la question et
   évite un aller-retour si la voie revient. À justifier par écrit dans un sens
   ou dans l'autre.
4. `report.py` : la table « Voie | Acquisitions /s » reste, elle n'affichera
   plus qu'une ligne. Le verdict « Archivage vs reste » doit rester lisible
   quand `AppendToSent` est de nouveau sur la voie de lecture.
5. Les tests de task-213 (`WriteLaneSessionTests`) : ceux qui portent sur la
   voie disparaissent avec elle ; **`CrossTenantOwnershipTests` et le test de
   famille d'opération restent**.

## Hors scope

- L'instrumentation de task-214, dans son intégralité.
- Le défaut Redis synchrone signalé par task-215
  (`ResilientCacheService.TryGet<T>`, repo `sdk`) — US distincte.
- Toute nouvelle tentative de réduire l'attente d'archivage : elle se
  rediscutera sur une mesure, si le besoin réapparaît.

## Definition of Done

- [ ] Build passes (0 erreur) — Tests pass (0 échec)
- [ ] Plus aucune occurrence de `ForWriteLane` dans le code de production
- [ ] Une seule connexion IMAP par praticien : test prouvant que l'archivage et
      la lecture partagent la même clé de session
- [ ] La mesure qui a tranché est **écrite dans le code**, réserve « pour cet
      hôte » comprise
- [ ] Le sort de `LockLaneWrite` est tranché par écrit
- [ ] `CrossTenantOwnershipTests` verte
- [ ] Tests **constatés RED avant le retrait** (preuve dans le `## Develop log`)

### Dû au banc (ne bloque pas la PR, bloque la clôture de l'US)

- [ ] Tir 500 praticiens iso-conditions avec les tirs de task-215 : `send` p95
      **sous 10 s** et ratio **sous 2** — c'est-à-dire reproduire le témoin A
- [ ] Table des voies : plus aucune acquisition sur `write`

## Manual Test Plan

```powershell
cd Api/Mail/src/AppHost
$env:MSS_LOADTEST = "1"
dotnet run
```

```bash
cd Api/Mail/tests/loadtest-k6
./run.sh mixed          # échauffement
./reset-state.sh        # PURGE, APRÈS l'échauffement
USERS=500 VUS=60 MESSAGES_PER_USER=100 SESSION_ROTATION=0.001 \
VU_TAIL_FACTOR=8 RPS=980 DURATION=3m ./run.sh mixed
python report.py <run-id>
```

⚠️ **Lancer aussi l'échantillonneur** (`observe.ps1`) avant le tir — task-215 ne
l'a pas fait et le comptage des sessions IMAP Dovecot lui a manqué. C'est ici
qu'il doit montrer le retour au plancher simple.

**Ce que l'humain doit voir** :
- `send` p95 **sous 10 s**, ratio moyenne/médiane **sous 2** ;
- table « Voie | Acquisitions /s » : ligne `write` **absente** ;
- sessions IMAP Dovecot revenues au plancher d'avant task-213 (~2 500 à 500
  praticiens, contre ~5 000 avec la voie d'écriture).

**Données** : 100 % synthétiques (boîtes `loadtest-*`). Aucune donnée de santé.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville — messagerie MSSanté du praticien.
- **Vague Ségur** : hors vague — optimisation technique interne.
- **Exigences DSR honorées** : aucune nouvelle. Le retrait **restaure** le
  comportement d'avant task-213, dont MSSanté-2.4 et le chemin d'émission
  n'avaient de toute façon pas la sémantique altérée.
- ⚠️ **Imputabilité** : l'archivage dans le dossier d'envois est la **trace
  métier** de l'émission. Le retrait le remet sur la voie de lecture, où il
  attend — il ne doit **jamais** le rendre « au mieux ». La vérification
  d'archivage effectif reste exigée, comme dans task-213.
- **INS** : non manipulée. **Authentification PS** : inchangée.
- **Habilitations** : le retrait **simplifie** le cloisonnement — une clé de
  session par praticien au lieu de deux. `CrossTenantOwnershipTests` reste la
  garde.
- **Tracé PGSSI-S** : aucun évènement métier touché.
- **Hébergement HDS** : non — banc de charge, données synthétiques.
- **AIPD / impact RGPD** : inchangé.

## Branches

- `api-mail` (pushed) : chore/task-216-retrait-voie-ecriture — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/chore/task-216-retrait-voie-ecriture
- `dtos-mss` (pushed, auto-inclus) : chore/task-216-retrait-voie-ecriture — aucune modification attendue (aucun contrat touché)

Préfixe `chore/` : retrait d'un mécanisme dont la mesure a établi le bilan
négatif — ni fonctionnalité, ni correction de défaut.

## Develop log (2026-08-20)

Retrait livré en `f05443f`. La voie fonctionnait — ce n'est pas un revert de
dépit, et le code le dit maintenant à l'endroit où la voie était choisie.

### Preuve ROUGE avant le retrait (exigée par le DOD)

`SingleImapLanePerPractitionerTests` — 3 tests qui capturent le contexte que
`AppendToSentAsync` / `AppendToDraftsAsync` présentent réellement au
gestionnaire de sessions. **3/3 rouges** avant le retrait : contexte
`s1#write` au lieu de `s1`. Un test sur `UserContextInfo` seul n'aurait rien
prouvé — c'est le **choix du contexte par le service** qui décide du nombre de
connexions, et c'est donc lui qu'il faut épingler.

### Retiré

- `ImapService.WriteLane`
- `UserContextInfo.ForWriteLane()`, `WriteLaneSuffix`, `IsWriteLane`
- **et** `IImapConnectionService.ConnectInternalAsync(UserContextInfo, ct)` —
  surcharge ajoutée par task-213, dont le seul rôle était de désigner la
  seconde connexion du même praticien. La laisser aurait laissé le **moyen** de
  recréer la voie sans le dire. Ses 4 sites de stub côté tests sont recibles sur
  la surcharge sans contexte.

### Conservé, et l'arbitrage est écrit

- **L'instrumentation de task-214 en entier**, comme le demandait la task.
- **`MailProcessingMetrics.LockLaneWrite`**, bien qu'elle n'ait plus d'émetteur.
  Le DOD demandait de trancher par écrit : elle **reste**. C'est elle qui a
  permis d'attribuer le doublement des sessions IMAP (2 500 → 5 002) et donc de
  trancher task-215 ; la supprimer effacerait la trace de l'arbitrage, et la
  table « Voie | Acquisitions /s » perdrait sa dimension.
- **La mesure dans le code** (`ImapService`, là où la voie vivait) : le tableau
  des trois tirs, le constat que le témoin satisfait le DOD de task-213 alors
  que les tirs porteurs du correctif le manquent, le fait que le défaut
  d'origine n'est plus reproductible depuis la levée des plafonds du banc, et
  la **réserve « pour cet hôte »** — les trois tirs ont subi le même biais de
  CPU partagé, c'est l'écart entre eux qui est mesuré.

### `report.py`

Table « Voie | Acquisitions /s » **conservée** : c'est en n'ayant plus qu'une
ligne (`read`) qu'elle atteste du retour à une connexion par praticien, et une
seconde ligne sur un tir futur signalerait une voie réintroduite. Le verdict
« Archivage vs reste » reste lisible mais **change de sens** : l'écart n'a plus
à être en faveur de l'archivage, il est attendu du même ordre que les autres, et
ce qui juge la décision est `send` vu du praticien.

### Tests

| Suite | Résultat |
|---|---|
| `mss.mail.api.tests` | **665 / 665** ✅ |
| `mss.mail.application.tests` | **2 159 / 2 159** ✅ |
| `mss.mail.domain.tests` | **136 / 136** ✅ |
| `mss.mail.infrastructure.tests` | **464 / 464** ✅ |
| `CrossTenantOwnershipTests` (exigé au DOD) | **21 / 21** ✅ |
| `selftest.sh` du harnais | 94 JS + 297 Python, 0 échec, **0 SKIP** ✅ |

Les 4 tests de voie de task-213 partent avec la voie ; `WriteLaneSessionTests`
devient `SessionLockTests` et garde ce qui ne dépendait pas d'elle (sérialisation
d'une session, garde PGSSI-S de famille d'opération). Deux tests
d'instrumentation sont recibles sur la voie unique.

**Flaky pré-existant caractérisé** : `MarkdownPdfRendererTests` échoue par
intermittence en suite complète (1 / 1 / 0 échec sur **trois exécutions
identiques**), passe systématiquement en isolation, et est **présent sur
develop** (mesuré par `git stash`). Sans rapport avec cette task.

### Reste dû au banc — ne bloque pas la PR, bloque la clôture de l'US

Le tir 500 praticiens iso-conditions avec task-215 (`send` p95 < 10 s, ratio
< 2, table des voies sans ligne `write`, sessions Dovecot revenues au plancher)
est un livrable **humain** : il demande le banc distant et l'échantillonneur
`observe.ps1`. Le Manual Test Plan de la PR le porte.

## Simplify log (2026-08-20)

Passe qualité sur `api-mail` — `1407931`. Trois axes, aucun changement de
comportement :

- **Altitude / signature honnête** — `ImapLockScope.LaneOf(UserContextInfo)`
  n'ouvrait plus son paramètre depuis le retrait de la voie : devient la
  constante `Lane`. Un paramètre qu'on ignore ferait croire à une dérivation qui
  n'existe plus, et c'était un `S1172` en attente pour `/sonar`.
- **Simplification** — `SessionLockTests` : `using System.Diagnostics`
  (`Stopwatch`) et le paramètre `session` de l'usine de contexte partaient avec
  les quatre tests de voie.
- **Simplification** — `SingleImapLanePerPractitionerTests` : deux usings
  hérités du modèle copié, jamais utilisés.

Re-validation : build 0 erreur / **0 avertissement** ; api **665/665**,
application **2159/2159**, domain **136/136**, infrastructure **464/464**.
`dtos-mss` non touché (et hors périmètre — porteur de contrat).

## Sonar log (2026-08-20)

Deux analyses complètes sur la branche (conteneurs redémarrés — ils étaient
arrêtés).

### KPIs qualité — baseline → final

| Condition | Baseline | Final | Seuil | Verdict |
|---|---|---|---|---|
| `new_coverage` | 88,3 % | **88,4 %** | ≥ 80 | ✅ |
| `new_duplicated_lines_density` | 0,058 % | **0,058 %** | ≤ 3 | ✅ |
| `new_security_hotspots_reviewed` | 100 % | **100 %** | 100 | ✅ |
| `new_violations` | 69 | **68** | 0 | ❌ |
| **Quality Gate** | **ERROR** | **ERROR** | — | inchangé |

### Un seul finding attribuable, et il venait de la passe qualité

`csharpsquid:S3218` sur `ImapLockScope.cs` — la constante `Lane` que
`/forge-simplify` avait introduite en remplacement de `LaneOf(UserContextInfo)`
**masquait le membre positionnel `Lane`** du record imbriqué `LockTags`.
Renommée `LaneLabel` (`ccc66d9`). Après correction, l'attribution par fichier
renvoie **0 issue** sur les 12 fichiers C# de la task.

C'est un enchaînement à retenir : la passe qualité a supprimé un `S1172` en
attente (paramètre ignoré) et introduit un `S3218` en le faisant. Le scan qui
suit la passe qualité n'est pas une formalité.

### Attribution des 68 restantes — aucune n'est de cette task

`report.py` (22), `journey-model.js` (14), `journey.js` (7) — le harnais de banc
des tasks 263/264, déjà mergées ; puis quelques fichiers backend antérieurs.
**Vérifié sur pièce** : les 22 findings de `report.py` portent sur les lignes
864 à 5378, alors que les quatre hunks de cette task sont aux lignes ~697,
~4012, ~4028 et ~4054. Aucun recouvrement. Le `CA1861` sur
`ImapServiceFolderStatusSolicitationTests.cs` porte sur un fichier que la task
ne touche pas (`git diff --name-only` le confirme).

Même phénomène que pour task-265 : la new-code period inclut des tasks déjà
mergées, donc la QG peut rougir sans dette introduite.

### Suites en Release (configuration du scan)

Second scan : domain **136/136**, application **2159/2159**,
infrastructure **464/464**, api **665/665** — les quatre suites unitaires
entièrement vertes sur cette exécution.

**Deux flaky pré-existants observés** au fil des exécutions, aucun lié à cette
task : `MarkdownPdfRendererTests` (application — 1/1/0 échec sur trois
exécutions identiques, vert en isolation, **présent sur develop**) et un échec
unique côté intégration au premier scan, absent au second.

## Lint Angular log (2026-08-20)

Skip propre — `client-angular` n'est pas dans `**Repos**` (`api-mail` seul,
`**Single frontend**: true`) et aucun fichier de `Client/Angular/` n'a été
touché. Aucune commande lancée, aucune opération git (mode code-only).

## Lint mobile log (2026-08-20)

Skip propre — `client-mobile` hors périmètre, aucun fichier de `Client/Mobile/`
touché. Aucune commande, aucun commit, aucun push.

## Visual verify log (2026-08-20)

Skip propre — aucun écran `client-mobile` touché (task backend, aucun
`## Stitch design log`). Aucun serveur lancé, aucune capture.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/196 — label `awaiting-human-merge`
- `dtos-mss` : aucune modification, pas de PR (branche auto-incluse restée vide)
- Staging : task menée hors run `/forge` — aucune branche staging.

## Code Review Summary

**APPROVED** — 0 blocage.

**Le point qui méritait vérification, et sa réponse.** Repartager le verrou entre
archivage et lecture crée un risque de **ré-entrance** : si `AppendToSent` était
appelé alors que le verrou de session est déjà tenu, il s'auto-bloquerait — ce
que deux voies masquaient. Vérifié sur les **deux** sites d'appel
(`MailController:1165` et `:1343`) : tous deux suivent un envoi **SMTP**, au
niveau du contrôleur, **hors de tout scope de verrou IMAP**. Et les deux chemins
appellent `ConnectInternalAsync(ct)`, qui ne prend pas le verrou — c'est
`ConnectAsync` qui le prend. Pas de double acquisition. C'est de surcroît l'état
d'avant task-213, qui fonctionnait.

Le retrait est complet et symétrique : la voie, son suffixe, son prédicat, et la
surcharge de connexion qui n'existait que pour elle. La mesure qui a tranché est
dans le code avec sa réserve, et le sort de `LockLaneWrite` est tranché par écrit
comme le DOD l'exigeait.

Suggestion non bloquante : `AppendToDraftsAsync` n'a **aucun appelant en
production** (déclaration d'interface + implémentation seulement). Surface morte
antérieure à cette task, hors périmètre — à constater avant de la retirer ou de
la rebrancher.

### DOD

| Critère | État |
|---|---|
| Build 0 erreur, tests 0 échec | ✅ (0 avertissement aussi) |
| Plus aucun `ForWriteLane` en production | ✅ (seuls des commentaires historiques le nomment) |
| Test : archivage et lecture partagent la clé de session | ✅ `SingleImapLanePerPractitionerTests`, 3 tests |
| Mesure écrite dans le code, réserve « pour cet hôte » | ✅ dans `ImapService` |
| Sort de `LockLaneWrite` tranché par écrit | ✅ conservée, justifiée |
| `CrossTenantOwnershipTests` verte | ✅ 21/21 |
| Tests constatés RED avant le retrait | ✅ 3/3, `s1#write` au lieu de `s1` |
| **Dû au banc** (tir 500, table sans ligne `write`) | ⏳ **humain** — Manual Test Plan de la PR |

## Merged (2026-08-20)

**Date** : 2026-08-20 — `/merge 216 --i-tested` (HAG, règle 10).

| Repo | PR | Commit squash sur `develop` |
|---|---|---|
| `api-mail` | [#196](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/196) | `99c2ff3` |
| `dtos-mss` | aucune PR — branche auto-incluse sans commit | — |

**Gates** : `--i-tested` présent ; label `awaiting-human-merge` ; aucune review
`CHANGES_REQUESTED` ; `build` pass (1m40s) ; `MERGEABLE` / `CLEAN` ; arbres de
travail propres.

**Nettoyage** : refs distantes supprimées sur `api-mail` **et** `dtos-mss` ;
**branche locale conservée** sur `api-mail`. Aucune branche staging (task menée
hors run `/forge`).

**CI `develop`** : ✅ verte —
[run 32511233045](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/32511233045).

### ⚠️ L'US n'est pas close — la confirmation au banc reste due

Le code est sur `develop`, mais le DOD porte une section « **Dû au banc** » qui
ne bloquait pas la PR et **bloque la clôture** :

- tir 500 praticiens iso-conditions avec task-215 : `send` p95 **sous 10 s**,
  ratio moyenne/médiane **sous 2** ;
- table « Voie | Acquisitions /s » : ligne `write` **absente** ;
- sessions IMAP Dovecot revenues au plancher d'avant task-213 (~2 500 à 500
  praticiens contre ~5 000 avec la voie) ;
- ⚠️ lancer `observe.ps1` **avant** le tir — task-215 ne l'a pas fait et le
  comptage des sessions Dovecot lui a manqué.

Tant que ce tir n'a pas été conduit, le retrait est **justifié par la mesure de
task-215** mais **non confirmé après coup**. C'est la même exigence que celle
que cette task reproche à task-213 ; ne pas l'oublier au motif que la PR est
mergée.

### Suggestion non résolue, reportée

`AppendToDraftsAsync` n'a **aucun appelant en production** (déclaration
d'interface + implémentation seulement) — surface morte antérieure à cette task.
À constater avant de la retirer ou de la rebrancher.
