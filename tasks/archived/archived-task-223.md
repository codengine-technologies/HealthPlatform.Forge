# todo-task-223.md — Un message parti ne doit jamais être annoncé en échec au médecin

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune stricte. **Interaction à connaître avec task-216**
(retrait de la voie d'écriture d'archivage) : ce retrait réduira beaucoup la
**fréquence** du défaut, mais **ne le supprime pas** — le défaut est dans le
mécanisme de libération du verrou de session, pas dans la voie d'écriture. Les
deux US sont indépendantes et peuvent être menées dans n'importe quel ordre ;
celle-ci ne doit pas être classée sans suite si task-216 passe d'abord.
**Priorité**: **1** — c'est le seul des trois constats de la campagne du
2026-08-03 qui **trompe le médecin** : il lit « échec » sur un message que son
correspondant a bien reçu. Rare, mais la conséquence est une duplication de
document de santé chez le destinataire.

## Objective

Qu'un envoi remis au destinataire soit **toujours** annoncé comme réussi au
médecin, même quand une étape secondaire (l'archivage dans les messages
envoyés) échoue.

## Le constat — mesuré

Campagne de certification du **2026-08-03** (200 médecins, rythme réel,
3 352 envois) : **un envoi sur 3 352 a été rendu au médecin en erreur alors
que le message était parti et remis**. C'est la seule erreur de toute la
campagne — 105 000 requêtes, taux d'erreur global 0,001 %.

Ce qui s'est réellement passé sur cet envoi (trace
`4ad7594f36b4773d8551b77ba08fc663`, rapport
`reports/2026-08-03/report-journey-certif-n200-180029.md`) :

1. le message **est envoyé et remis** — l'envoi lui-même réussit ;
2. l'archivage dans le dossier des messages envoyés échoue ;
3. **cet échec-là est déjà traité comme non fatal** par le code — il n'est pas
   la cause de l'erreur rendue ;
4. c'est **la libération du verrou de session, à la sortie de l'archivage**,
   qui lève une exception non rattrapée (`SemaphoreFullException`) et transforme
   le tout en erreur serveur.

Mécanisme établi par lecture du code et par élimination : le verrou est relâché
**en retrouvant la session par son identifiant**, et non en relâchant celui qui
a effectivement été pris. Si l'entrée de session est recyclée pendant
l'opération, la libération tombe sur un verrou neuf et lève. L'archivage passe
par une **voie de session dédiée** (task-213) qui n'existe que le temps des
envois : c'est elle qui est la plus exposée à ce recyclage, ce qui explique la
localisation et la rareté. Détail complet dans la section « Analyse Seq » du
rapport cité.

## Pourquoi la conséquence est plus grave que sa rareté

Le médecin voit « échec d'envoi » sur un compte rendu **effectivement remis**.
Le geste naturel est de **le renvoyer** : le destinataire reçoit alors **deux
fois le même document de santé**, sans moyen simple de savoir lequel est le bon.
Dans une messagerie de santé, un document dupliqué dans le dossier d'un patient
n'est pas un désagrément d'ergonomie.

## Ce qu'il ne faut PAS présumer

- **Ne pas se contenter d'avaler l'exception.** Rendre l'envoi « réussi » en
  masquant la panne de libération laisserait un verrou dans un état indéterminé.
  Les deux choses sont à traiter : **le mécanisme de libération** (qu'il ne
  puisse pas se tromper de verrou) **et** la robustesse (qu'un défaut de
  comptage ne devienne jamais une erreur rendue au médecin).
- **Ne pas présumer que task-216 règle le sujet.** Le retrait de la voie
  d'écriture réduit l'exposition ; le mécanisme fautif reste. Si task-216 passe
  d'abord, cette US garde tout son objet — mais sa **reproduction** au banc
  devient plus difficile, ce que le plan de test doit assumer.
- **Ne pas transformer un échec d'archivage en succès silencieux.** Le médecin
  doit être informé que son message est parti **et** que sa copie dans les
  messages envoyés manque : ce sont deux informations distinctes, et la seconde
  a une valeur d'imputabilité (retrouver ce qu'on a envoyé, et à qui).
- **Ne pas élargir au verrou de session en général.** Sa portée et son
  existence sont des sujets ouverts depuis task-211/213/216 ; ici on corrige un
  défaut de **libération**, pas le modèle de verrouillage.

## Contenu attendu

1. **Le mécanisme de libération rendu incapable de se tromper de verrou** —
   quelle que soit la vie de l'entrée de session pendant l'opération.
2. **Une libération défensive** : un défaut de comptage se journalise et
   n'atteint jamais le médecin sous forme d'erreur.
3. **La distinction rendue au médecin** entre « message parti » et « message
   parti mais non archivé », et la trace correspondante côté exploitation.
4. **Un test qui reproduit le scénario** — recyclage de l'entrée de session
   pendant l'opération d'archivage — et qui échoue avant le correctif.

## Hors scope

- La portée du verrou de session, son existence, la voie d'écriture (task-211,
  task-213, **task-216**).
- Les autres dépassements SLO de la campagne (**task-222**, et l'étape 8).
- L'outillage de mesure (**task-224**).

## Definition of Done

- [ ] Build passe (0 erreur)
- [ ] Tests passent (0 échec)
- [ ] Test unitaire reproduisant le **recyclage de l'entrée de session pendant
      l'archivage**, constaté **ROUGE avant** le correctif (preuve dans le
      `## Develop log`)
- [ ] Test unitaire : un défaut de libération du verrou **ne remonte jamais** en
      erreur serveur au médecin
- [ ] Test unitaire / intégration : envoi remis + archivage en échec ⇒ le médecin
      reçoit un **succès**, et l'absence d'archivage est **journalisée** de façon
      distinguable
- [ ] Aucune régression sur le chemin d'envoi nominal (envoi + archivage OK)
- [ ] Évènement PGSSI-S d'envoi toujours journalisé, avec la distinction
      « archivé / non archivé »
- [ ] Aucune donnée de santé en clair dans les traces ajoutées (contenu du
      message, INS, RPPS dans les sujets)
- [ ] Tir `journey` **K=1** au banc : **zéro erreur serveur sur l'envoi**
      (la campagne de référence en avait 1 sur 3 352)

## Manual Test Plan

```bash
# Banc distant, campagne d'envoi soutenue au rythme réel
cd Api/Mail
MSS_LOADTEST_MAIL_HOST=<ip-noeud> dotnet run --project src/AppHost --launch-profile https-load-test
dotnet run --project tests/mss.mail.loadtest.seed -- --users 200 --messages 150 \
  --api http://127.0.0.1:5052 --mail-host <ip-noeud> --latency 95
export BYPASS_KEY=loadtest-local-only MSS_LOADTEST_MAIL_HOST=<ip-noeud>
# part d'envoi relevée pour multiplier les occasions, fenêtre longue
LATENCY_MS=95 USERS=200 MESSAGES_PER_USER=150 JOURNEY_P_SEND=0.8 \
  JOURNEY_STAGES="200:35m" JOURNEY_TIME_COMPRESSION=1 \
  tests/loadtest-k6/run.sh journey
tests/loadtest-k6/report.sh <dernier json> --expected 0
```

**Ce que l'humain doit voir** :
- dans le rapport, **taux d'erreur 0,00 %** et le check « send: accepted »
  à **100 %** (la campagne du 2026-08-03 était à 99,963 %) ;
- dans Seq sur la fenêtre du tir : **aucune** `SemaphoreFullException`, et
  **aucune** erreur serveur sur `/mail/sendmail` ;
- dans le client, sur un envoi dont l'archivage échoue (à provoquer en retirant
  le dossier des messages envoyés de la boîte de test) : le médecin voit son
  message **parti**, avec une mention distincte indiquant que la copie dans les
  messages envoyés manque — et le message est bien présent chez le destinataire ;
- côté serveur de messagerie, le message est bien remis au destinataire.

**Données de test** : boîtes `loadtest-*`, corpus synthétique, aucune donnée de
santé réelle, destinataire = puits de test.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville — messagerie MSSanté du praticien.
- **Vague Ségur** : hors vague — correction d'un défaut de restitution sur un
  geste déjà référencé ; aucun contrat d'interopérabilité modifié.
- **Exigences DSR honorées** : aucune nouvelle. La US **restaure** en revanche la
  fiabilité de l'information rendue au PS sur l'aboutissement de son envoi, qui
  conditionne l'imputabilité de l'échange.
- **INS** : non manipulée — le défaut est dans la libération d'un verrou
  technique, en aval de toute logique patient.
- **Authentification PS** : inchangée (PSC / e-CPS pour l'envoi MSSanté, niveau
  eIDAS substantiel au moins). Rappel du garde-fou : un envoi MSSanté n'est
  jamais autorisé sur simple mot de passe.
- **Habilitations** : inchangées.
- **Interop CI-SIS** : MSSanté (volet transport). Le message émis n'est pas
  modifié par cette US — ni son contenu, ni ses en-têtes, ni son enveloppe.
- **MSSanté** : adresse émettrice et certificat IGC Santé inchangés. ⚠️ **Le
  garde-fou « jamais de RPPS dans les sujets ou en-têtes » s'applique aux
  traces ajoutées** : l'adresse seule identifie l'émetteur.
- **Tracé PGSSI-S** : évènement « envoi d'un document de santé par un PS »
  — **à enrichir** d'une issue distinguant « remis et archivé » de « remis, non
  archivé ». Durée de conservation inchangée. C'est cette trace qui permettra au
  support de trancher, sans que le médecin ait à renvoyer.
- **Consentement patient** : non applicable — échange entre professionnels dans
  le cadre de la prise en charge.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : oui en production (le message est une DSCP). Banc local
  et synthétique.
- **AIPD / impact RGPD** : inchangé — pas de nouveau traitement ; l'enrichissement
  de trace porte sur l'issue technique de l'envoi, pas sur son contenu.

## Branches

- `api-mail` (pushed) : `fix/task-223-semaphore-release-mismatch` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-223-semaphore-release-mismatch
- `dtos-mss` (pushed, auto-inclus) : `fix/task-223-semaphore-release-mismatch` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/fix/task-223-semaphore-release-mismatch — pas de changement de contrat attendu ; branche créée proactivement, aucune PR si aucun commit

Pré-flight `/start` : tous les repos forge-automatisés sur `develop` (`api-mail`,
`client-blazor`, `client-mobile`, `dtos-mss`, `sdk`, `interop-cda`). `host` non
mesurable (pas de `.git`, cf. CLAUDE.md).

`**Single frontend**: true` → aucun frontend touché : pas de branche
`client-blazor`/`client-mobile`, et `/lint-angular`, `/lint-mobile`,
`/verify-visual` skipperont clean.

## Develop log

- **Repos touchés** : `dtos-mss` (contrat), `api-mail`. Aucun frontend
  (`**Single frontend**: true`).
- **DTOs publiés** : `HealthPlatform.Dtos.Mss` 377.0.0 → **381.0.0**
  (run CI 381, `success`). Consommateur bumpé : `api-mail` uniquement.
  `client-blazor` **non bumpé** — la task ne le liste pas, il n'a donc pas de
  branche et la forge ne commite pas sur son `develop`. L'ajout étant purement
  additif (valeur d'enum en fin de liste), il n'en a pas besoin ; il le prendra
  à sa prochaine task.
- **Interop publié** : aucun changement.
- **Commits** :
  - `dtos-mss` : `0095362` feat(dto): trace PGSSI-S distincte pour l'archivage d'un envoi (MailArchiveSent)
  - `api-mail` : `da1f5ee` chore(deps): bump HealthPlatform.Dtos.Mss to 381.0.0
  - `api-mail` : `2452a9b` fix(session): rendre le verrou qui a été pris, pas celui retrouvé par identifiant
  - `api-mail` : `8862818` feat(mail): distinguer un envoi archivé d'un envoi non archivé

### Le défaut, et où il était

`ImapLockScope.DisposeAsync` appelait `UnLockImapClient(userContext)`, qui
**retrouvait la session par son identifiant** (`GetSession(id)` →
`ImapLock.Release()`). Entre la prise et le rendu, l'entrée de session peut être
recyclée : expirée, retirée par `CleanupExpiredSessions`, puis recréée sous la
même clé par la requête suivante. La libération tombait alors sur un sémaphore
**neuf, jamais pris**, déjà au plein → `SemaphoreFullException`. Levée à la
sortie du `await using` d'`AppendToSentAsync`, elle **échappait au `catch`
intérieur** (qui est dans le `try`, pas autour du `using`) et devenait un 500 sur
un message pourtant remis.

Les **deux** volets demandés par la US sont livrés, et les deux sont porteurs :

1. **Le mécanisme ne peut plus se tromper de verrou** — `LockImapClientAsync`
   rend un `ImapSessionLockHandle` qui porte le sémaphore pris ; plus aucune
   recherche à la libération, donc plus de fenêtre. Le recyclage de l'entrée
   devient sans effet.
2. **Libération défensive** — la session recyclée est *disposée* avec son
   sémaphore : rendre le **bon** verrou lève alors `ObjectDisposedException`,
   c'est-à-dire le même 500 par une autre porte. `Release` journalise
   (`SemaphoreFullException` → Error, `ObjectDisposedException` → Warning, double
   rendu → Warning) et ne propage jamais.

### Preuve ROUGE avant correctif (DOD)

Sémantique de libération d'avant le correctif rétablie temporairement dans
`MailClientSessionManager.UnLockImapClient` (recherche par identifiant, sans
`catch`), les nouveaux tests relancés :

```
[FAIL] SessionLockReleaseMismatchTests.ReleasingAfterTheSessionEntryWasRecycledDoesNotThrow
       Assert.Null() Failure: Value is not null
       Actual: System.Threading.SemaphoreFullException: Adding the specified count
               to the semaphore would cause it to exceed its maximum count.
[FAIL] SessionLockReleaseMismatchTests.ReleasingAfterRecyclingLeavesTheFreshSessionLockUntouched
       System.Threading.SemaphoreFullException: Adding the specified count to the
               semaphore would cause it to exceed its maximum count.
Échoué!  - échec : 2, réussite : 3, total : 5
```

C'est **l'exception exacte** de la trace `4ad7594f36b4773d8551b77ba08fc663`.
Correctif remis, les 5 passent.

### Tests ajoutés

| Fichier | Couvre |
|---|---|
| `Session/SessionLockReleaseMismatchTests.cs` (5) | recyclage de l'entrée pendant l'archivage (reproduction) ; verrou de la session **neuve** intact (contre-épreuve du « bon verrou ») ; double rendu avalé + journalisé ; verrou disposé avalé + journalisé ; cycle nominal prise/rendu |
| `Services/Imap/ImapServiceArchiveAuditTests.cs` (3) | trace `MailArchiveSent` `Success=true` / `Success=false` ; **aucune donnée de santé** dans la trace ajoutée |
| `Controllers/MailControllerTests.cs` (+3) | archivage en échec ⇒ 200 `archived=false` + mention ; nominal ⇒ `archived=true` sans mention ; le libellé ne fuit aucun détail technique |

`UnLockImapClientShouldHandleMissingSession` a été **remplacé** par
`UnLockImapClientRejectsAMissingHandle` : la branche « session introuvable »
n'existe plus, elle décrivait la tolérance au symptôme plutôt que l'absence de
cause.

### Build / tests

`dotnet build HealthPlatform.Api.Mail.sln` → **0 erreur, 0 avertissement**.
`dotnet test HealthPlatform.Api.Mail.sln` → **3 382 réussis, 0 échec**, 16 ignorés :

| Projet | Résultat |
|---|---|
| `mss.mail.domain.tests` | 102 / 0 |
| `mss.mail.infrastructure.tests` | 407 / 0 |
| `mss.mail.application.tests` | 1 930 / 0 |
| `mss.mail.api.tests` | 645 / 0 |
| `mss.mail.integration.tests` | 298 / 0 (16 ignorés) |

À noter : les 3 tests rouges intermittents connus de la suite complète sont
passés sur ce run.

### DOD self-check

| Critère | État |
|---|---|
| Build 0 erreur | ✅ |
| Tests 0 échec | ✅ |
| Test reproduisant le recyclage, ROUGE avant | ✅ (trace ci-dessus) |
| Défaut de libération ne remonte jamais en erreur serveur | ✅ |
| Envoi remis + archivage en échec ⇒ succès + absence journalisée distinguable | ✅ |
| Aucune régression sur le chemin nominal | ✅ |
| Évènement PGSSI-S d'envoi toujours journalisé, distinction archivé / non archivé | ✅ |
| Aucune donnée de santé en clair dans les traces ajoutées | ✅ (test dédié) |
| Tir `journey` K=1 au banc, zéro erreur serveur | ⏭️ **différé au test manuel (HAG)** — exige le nœud de banc distant (`MSS_LOADTEST_MAIL_HOST=<ip-noeud>`), hors de portée de `/develop` |

### Deux points à l'attention de l'humain au HAG

1. **La mention à l'écran reste à câbler côté client.** La task est scopée
   `**Repos**: api-mail` / `**Single frontend**: true` : le backend livre la
   distinction dans le **contrat** (`archived` + `warning` sur
   `POST /mail/sendmail`) et dans la trace PGSSI-S, mais aucun frontend ne la
   *rend* encore. Le point du Manual Test Plan « dans le client, le médecin voit
   son message parti avec une mention distincte » n'est donc **pas observable en
   l'état** — il le devient dès qu'un frontend consomme `archived`. Le reste du
   plan (rapport k6, absence de `SemaphoreFullException` dans Seq, message bien
   remis) est observable tel quel. À arbitrer : une US de suivi pour
   `client-blazor` / `client-angular` / `client-mobile`.
2. **`POST /cancel-and-replace` n'a pas changé de forme.** Son `warning` porte
   déjà l'issue du marquage « annulé » de l'original ; y ajouter l'issue
   d'archivage demandait de la faire traverser `IMailCancellationService`
   (la callback `SendAndArchiveAsync` rend un `bool`), ce qui sort du défaut
   corrigé ici. La **trace** `MailArchiveSent` couvre néanmoins ce chemin aussi,
   puisqu'elle est émise dans `AppendToSentAsync`.

- **Next step** : `/forge-simplify task-223`

## Simplify log

- **Repos passés** : `api-mail` (seul repo touché éligible).
- **Appliqué & committé** : `api-mail` — 4 fichiers (`c8a29b9`).
  1. **Réutilisation du patron déjà en place.**
     `BackgroundImapConnectionRegistry.Lease` (même dossier) est déjà un jeton
     qui tient sa référence et rend *son* sémaphore sans le rechercher, avec
     `Interlocked` pour le rendu unique — et il **tire son logger de son
     propriétaire** au lieu de le recevoir en paramètre.
     `ImapSessionLockHandle` s'aligne : `Release()` sans argument, le jeton
     porte son `ILogger`. Les deux types ne fusionnent pas (un bail porte en
     plus le client en réserve, et son cycle de vie est celui d'un cycle de
     fond) — mais ils ont désormais la même forme, et le commentaire le dit
     pour que la question « pourquoi deux jetons ? » ait sa réponse sur place.
  2. **Duplication retirée** : `MailController.ArchiveSentMessageAsync` extrait.
     `SendMailAsync` et `SendAndArchiveAsync` (annule-et-remplace) faisaient
     append + warn à l'identique, à la casse du message près. Deux endroits où
     réintroduire l'idée qu'un échec d'archivage est un échec d'envoi — c'est-à-
     dire le quiproquo même que cette US corrige.
  3. **Règle du repo appliquée d'emblée** : `.GetAwaiter().GetResult()` retiré
     du helper de recyclage (S4462, `Api/Mail/.github/instructions/`), helper
     passé en `async Task`. Deux `perTestLogger` devenus inertes depuis que le
     jeton détient son logger ont été retirés — l'assertion porte maintenant sur
     le logger du gestionnaire, le seul réellement branché. Sans ce nettoyage
     l'assertion de journalisation aurait été **vide de sens**.
- **Aucun changement** : —
- **Rollback (validation ROUGE)** : aucun.
- **Ignorés (contrat / exclus)** : `dtos-mss` et `interop-cda` (porteurs de
  contrat — une passe cosmétique y déclencherait un republish NuGet pour rien),
  `devops`, `psc-proxy-*`.
- **`client-angular` non passé** : son arbre porte du WIP humain **antérieur et
  étranger** à cette task (`front/apps/mss/src/environments/environment.ts`,
  `front/apps/weda2/…/environment.ts`). La task ne le liste pas dans
  `**Repos**:` et `/develop` n'y a rien écrit : simplifier le travail en cours
  de l'humain serait hors mandat. Arbre laissé intact.
- **`client-mobile` non passé** : arbre propre, aucun diff — non touché.
- **Build / tests** : ✅ vert — `0 erreur, 0 avertissement`, **3 382 tests
  réussis, 0 échec** (16 ignorés), suite complète relancée *après* la passe.
- **Note de méthode** : le playbook `/simplify` prévoit un fan-out sur 4 agents
  de revue. La consigne de session interdit d'appeler l'outil Agent sans demande
  explicite de l'humain ; les quatre axes (réutilisation, simplification,
  efficacité, altitude) ont donc été passés séquentiellement en direct. Même
  livrable, aucun agent lancé.
- **Next step** : `/sonar task-223` (api-mail touché)

## Sonar log

**Mode A** (chaîné, branche `fix/task-223-semaphore-release-mismatch`, pas de PR
Sonar séparée). Infra relancée après reboot (`sonarqube_db` puis `sonarqube`,
`status:UP` en ~20 s). Analyse complète : build Release + 5 projets de tests avec
couverture OpenCover (5 rapports), `EXECUTION SUCCESS`, traitement serveur
`SUCCESS`.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | |
|---|---|---|---|
| `bugs` | 0 | **1** | ⚠️ pré-existant, cf. ci-dessous |
| `vulnerabilities` | 0 | 0 | = |
| `code_smells` | 3 | 18 | ⚠️ pré-existants |
| `security_hotspots` | 0 | 1 | ⚠️ pré-existant |
| `coverage` | 85,6 % | **86,9 %** | ▲ +1,3 pt |
| `new_coverage` | 84,9 % | **87,0 %** | ▲ +2,1 pt (cible 80 % — OK) |
| `duplicated_lines_density` | 0,6 % | **0,5 %** | ▲ |
| `reliability_rating` | A (1.0) | C (3.0) | ⚠️ pré-existant |
| `security_rating` | A (1.0) | A (1.0) | = |
| `sqale_rating` | A (1.0) | A (1.0) | = |
| `new_violations` | 3 | 18 | ⚠️ pré-existants |
| **Quality Gate** | **ERROR** | **ERROR** | inchangé — `new_violations` + `new_security_hotspots_reviewed` |

### Phase 1 — new code : **zéro dette introduite par task-223**

**Aucun** des 18 findings du new code period ne porte sur un fichier touché par
cette task. Provenance établie fichier par fichier, par `git log` :

| Finding(s) | Fichier | Dernier commit | Propriétaire |
|---|---|---|---|
| `python:S1244` (**l'unique BUG**), `python:S1192` ×2, `python:S3776` ×6, `python:S3358`, `javascript:S3776`, `javascript:S1940` ×3, `javascript:S6035`, `javascript:S4624` | `tests/loadtest-k6/**` | `c8c6838` (2026-08-03) | **task-220** (banc parcours médecin), mergé **aujourd'hui** |
| `csharpsquid:S103` | `src/Application/Services/Interfaces/IIheXdmProcessingService.cs:9` | `5393eb6` (2026-08-01) | **task-185**, mergé |
| `csharpsquid:S103` | `src/Infrastructure/Repository/BaseRepository.cs:68` | `5317516` (2026-08-02) | **task-218**, mergé |
| hotspot `weak-cryptography` | `tests/loadtest-k6/scenarios/journey.js:225` | `c8c6838` | **task-220** — PRNG pour façonner du trafic de banc, pas de la crypto |

Le saut baseline → final (3 → 18 violations, A → C) s'explique **entièrement**
par le merge de **task-220** sur `develop` aujourd'hui, postérieur à la dernière
analyse Sonar : son harnais k6 (Python + JS) est scanné pour la première fois.
C'est le piège consigné dans la mémoire
`project_sonar_new_code_baseline_includes_prior_tasks` — la période
`PREVIOUS_VERSION` place dans le « new code » des tasks déjà mergées. **La
dégradation n'est pas imputable à cette PR** ; elle décrit l'état de `develop`.

Les fichiers modifiés par task-223 (`Session/*`, `ImapService`,
`MailController`, `ApiMessages`, tests) ne portent **aucun** finding, et la
couverture du new code **progresse** (84,9 → 87,0 %).

### Phase 2 — dette legacy : **skippée, à dessein**

Explicitement optionnelle et best-effort dans `agents/sonar.md`. Non lancée ici,
pour trois raisons qui se cumulent :

1. **`report.py` est hors scope par décision du PO.** La section « Hors scope »
   de cette US nomme « l'outillage de mesure (**task-224**) ». Or 15 des 18
   findings — dont l'unique bug — y vivent. Les corriger ici contredirait
   l'arbitrage du PO.
2. **Règle 6 (scopes isolés) et règle 5 (~30 fichiers max).** Les 3 findings
   restants appartiennent à task-185, task-218 et task-220. Les embarquer
   mêlerait du code étranger à une PR de correction priorité 1 que l'humain doit
   tester de bout en bout au HAG.
3. **`S3776` est hors chaîne par construction** (`agents/sonar-blacklist.yml` :
   commande dédiée `/sonar-s3776`, 1 méthode = 1 PR). C'est la règle dominante
   ici (7 occurrences sur 18).

Findings legacy **acceptés**, conformément au principe best-effort.

### À signaler à l'humain

**`develop` porte actuellement un Quality Gate ERROR et une note de fiabilité C
qui ne viennent pas de cette PR** — ils viennent de **task-220**, mergée
aujourd'hui : un vrai bug `python:S1244` (comparaison d'égalité entre flottants)
dans `tests/loadtest-k6/report.py:1336`, c'est-à-dire **dans le générateur du
rapport de tir dont dépend le Manual Test Plan de cette US** (`report.sh
--expected 0`). Cela mérite d'atterrir dans **task-224** (outillage de mesure),
qui est déjà le réceptacle prévu.

### Note sur la suite de tests

Le run Release sous scanner a montré **1 échec** :
`MailExportServiceTests.BuildPdfWithoutAttachmentsOmitsAttachmentSection`.
Rejoué seul : **vert**. `MailExportService` n'est pas dans le diff de task-223.
C'est l'un des flakies Release déjà consignés
(mémoire `project_api_mail_preexisting_flaky_tests`) — pas une régression.
Les suites Debug complètes sont passées **deux fois** à 3 382/3 382.

- **Itérations** : 0 fix appliqué (rien à corriger sur le new code de la task).
- **Next step** : `/review task-223` (`client-angular` et `client-mobile` non
  touchés → `/lint-angular`, `/lint-mobile` et `/verify-visual` skippent clean).

## PRs

| Repo | PR | Label | État |
|---|---|---|---|
| `api-mail` | https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/149 | `awaiting-human-merge` | MERGEABLE |
| `dtos-mss` | https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/28 | `awaiting-human-merge` | MERGEABLE |

Ordre de merge conseillé : **`dtos-mss` #28 puis `api-mail` #149**. Le paquet
`381.0.0` est déjà publié sur le flux NuGet (CI run 381) et `api-mail` le
consomme déjà, donc l'ordre inverse ne casse rien — mais merger le contrat
d'abord garde `develop` cohérent avec son propre historique.

**Repos non concernés** : `client-blazor`, `client-angular`, `client-mobile`
(`**Single frontend**: true` — aucun frontend touché) ; `devops`, `psc-proxy-*`
(hors automation).

## Code Review Summary

**Verdict : APPROVED** — 7 fichiers source revus, **1 issue bloquante trouvée et
corrigée**, 1 remarque non bloquante consignée.

### L'issue bloquante trouvée à la revue

Le correctif initial fermait la porte de la **libération** du verrou, et laissait
**la porte voisine ouverte** : l'acquisition du verrou de la voie d'écriture
expire au bout de 120 s en `TimeoutException`, levée depuis l'initialiseur du
`await using` — donc **hors d'atteinte** du `catch` intérieur de
`TryAppendToSentAsync`. Sous la contention que toute cette série mesure
(task-211 / 213 / 214), c'est le scénario le plus plausible après la libération
fautive, et il produisait **exactement** l'issue interdite par l'objectif de la
US : « Qu'un envoi remis au destinataire soit **toujours** annoncé comme réussi au
médecin, même quand une étape secondaire échoue. »

C'était donc dans le périmètre de l'objectif, pas à côté. Corrigé (commit
`33a1bba`) plutôt que consigné en `questions/` : le correctif est petit, sans
ambiguïté, et livrer l'US avec ce trou aurait reproduit le travers que le PO
signalait lui-même — « ne pas se contenter d'avaler l'exception », « les deux
choses sont à traiter ».

- `ImapService.AppendToSentAsync` convertit `TimeoutException` en `Result` en
  échec, et la trace. `OperationCanceledException` **continue de remonter à
  dessein** : quand c'est le praticien qui a abandonné sa requête, il n'y a plus
  personne à informer et le 499 central est la bonne réponse.
- `MailController.ArchiveSentMessageAsync` porte l'invariant **là où il est
  connu** : à cet endroit du code le message *est* parti. Ce `catch` préserve un
  succès réel — il ne fabrique pas une réponse d'erreur ad hoc, ce n'est donc pas
  le boilerplate proscrit par la règle 12. Un commentaire le dit explicitement
  pour qu'une passe qualité ultérieure ne le « nettoie » pas.
- 3 tests ajoutés pour verrouiller les trois comportements.

### Par fichier

| Fichier | Verdict |
|---|---|
| `Session/ImapSessionLockHandle.cs` | ✅ jeton correct, rendu unique (`Interlocked`), ne lève jamais, aligné sur `BackgroundImapConnectionRegistry.Lease` |
| `Session/MailClientSessionManager.cs` | ✅ sémaphore capturé une fois avant l'attente ; `ArgumentNullException.ThrowIfNull` sur le jeton |
| `Session/IMailClientSessionManager.cs` | ✅ surface épinglée inchangée (noms de membres identiques → `SessionLockAcquisitionSurfaceTests` reste vert) |
| `Session/ImapLockScope.cs` | ✅ `LockRelease` groupe jeton + gestionnaire, constructeur maintenu sous 7 paramètres (S107) |
| `Services/Implementation/ImapService.cs` | ✅ trace émise hors verrou, sur les 4 chemins de sortie ; conversion du timeout documentée |
| `Api/Controllers/V1/MailController.cs` | ✅ duplication append+warn retirée ; invariant « remis ⇒ succès » à la frontière HTTP |
| `Api/Constants/ApiMessages.cs` | ✅ libellé métier fixe, aucune fuite technique |
| `Dtos/AuditActionType.cs` | ✅ valeur ajoutée **en fin** d'énumération, conforme au contrat de sérialisation par ordinal |

### Remarque non bloquante

Entre l'obtention du jeton et le `return` du scope, `MarkLockAcquired` et les
appels de log pourraient théoriquement lever et faire fuir le verrou.
**Pré-existant et inchangé par cette PR** — le verrou était déjà pris au même
endroit avant — et aucun de ces appels ne lève en pratique. Consigné, non
corrigé : hors périmètre de cette US (et la US dit explicitement de ne pas
élargir au modèle de verrouillage).

### Sécurité

Aucun secret. Le `warning` rendu au client est un libellé fixe (aucune cause
technique). La trace d'audit ajoutée ne porte **ni sujet, ni adresses, ni INS, ni
RPPS** — vérifié par un test dédié.

## Validation finale

| | Résultat |
|---|---|
| Build `api-mail` | ✅ 0 erreur, 0 avertissement |
| Build `dtos-mss` | ✅ 0 erreur, 0 avertissement |
| Tests `api-mail` | ✅ **3 384 réussis**, 16 ignorés, 1 flaky PdfPig **prouvé pré-existant** (2 échecs / 6 runs sur un worktree de `origin/develop` sans une ligne de task-223) |
| Sync `develop` | ✅ « Already up to date » sur les deux repos (merge, pas rebase) |
| DOD | 8 / 9 vérifiés ; le **tir `journey` K=1 au banc** reste à la charge de la recette (nœud de banc distant requis) |

## HAG (règle 10)

Les deux PRs attendent le **merge humain**. Rien n'a été mergé par la forge.

## Merged

Mergé le **2026-08-03** après validation humaine de bout en bout (`/merge task-223
--i-tested`, HAG règle 10). Squash-merge, historique linéaire.

| Repo | Commit squash sur `develop` | PR | CI `develop` |
|---|---|---|---|
| `dtos-mss` | `dbda7a3` | #28 fermée | ✅ [run 30843650059](https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/actions/runs/30843650059) |
| `api-mail` | `98eb1dc` | #149 fermée | ✅ [run 30843684398](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/30843684398) |

Ordre de merge respecté : contrat (`dtos-mss`) avant consommateur (`api-mail`).

Branches distantes `fix/task-223-semaphore-release-mismatch` supprimées sur les
deux repos ; **branches locales conservées** (pas de `--delete-branch`, qui
supprime aussi le ref local).

Aucune branche staging à nettoyer : la task a été lancée par `/start` direct, pas
par un run `/forge`.

### Ce qui reste ouvert après ce merge

- **Tir `journey` K=1 au banc** — dernier item du DOD, non joué : exige le nœud de
  banc distant (`MSS_LOADTEST_MAIL_HOST`). Doit rendre **zéro erreur serveur sur
  l'envoi**, là où la campagne de référence du 2026-08-03 en comptait 1 sur 3 352.
- **Mention à l'écran** — le backend livre `archived` + `warning` sur
  `POST /mail/sendmail` et la trace `MailArchiveSent`, mais aucun frontend ne les
  rend (`**Single frontend**: true`). US de suivi à arbitrer pour
  `client-blazor` / `client-angular` / `client-mobile`.
- **Bug `python:S1244`** dans `tests/loadtest-k6/report.py:1336` (égalité entre
  flottants), propriété de task-220 — porte le Quality Gate de `develop` en ERROR
  et la note de fiabilité en C. À traiter dans **task-224** (outillage de mesure).
- **task-216** (retrait de la voie d'écriture) reste pertinente et indépendante :
  elle réduira la **fréquence** du défaut corrigé ici, jamais le défaut lui-même.
