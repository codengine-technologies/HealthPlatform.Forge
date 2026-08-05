# todo-task-235.md — La suite d'intégration ne peut pas voir un travail de fond qui échoue : câbler la file, distinguer les bases, échouer sur une erreur journalisée

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: task-234 (mergée) — c'est son défaut qui a révélé les trois angles morts
traités ici ; le correctif est en place, il manque le filet qui aurait dû l'attraper.
**Priorité**: **2** — n'apporte aucune fonction au médecin, mais conditionne la
crédibilité de tout ce que la suite d'intégration affirme sur les chemins asynchrones.
Le prochain défaut du même genre passera aussi.

> ⚠️ **Aucun impact produit.** Cette US ne touche que le harnais de test : fixtures
> d'intégration et infrastructure de journalisation de test. Aucun code de production
> n'est modifié — si un correctif de production s'avérait nécessaire, il ferait l'objet
> d'une task distincte.

## Objective

Que la suite d'intégration soit capable de **voir échouer** un travail de fond. Elle en
est structurellement incapable aujourd'hui, et ce n'est pas une lacune de couverture
— c'est une lacune de **conception du harnais** : trois conditions manquent, chacune
suffisant à rendre un défaut invisible.

## Ce qui a été constaté, et comment

task-234 a corrigé un défaut qui a échappé à **3 467 tests et quatre analyses
SonarQube** : trois chemins de tâche de fond reconstituaient l'identité du praticien en
oubliant `MssRpps`, donc visaient une **autre base de données** — sans lever, sans
avertir, en lisant des tables vides. Il n'a été trouvé que parce qu'un humain a cliqué
dans le front et **regardé la table `PendingActions`**.

Les tests d'intégration existants sont réels et utiles — **vrai serveur IMAP** (boîte
Gmail de test), **vrai PostgreSQL**. Ils n'ont rien vu pour trois raisons empilées, et
la troisième est la plus gênante.

### 1. Ils n'entrent jamais dans le chemin défectueux

`IBackgroundTaskQueue` **n'est enregistrée dans aucune fixture d'intégration**
(`ImapServicesFixture`, `UseCaseFixture`). Les services de production la prennent en
paramètre **optionnel** : elle vaut donc `null` et le code emprunte son **repli en
ligne**, qui utilise le contexte **de la requête** — complet.

Trace de ce constat, dans les journaux de la suite elle-même :

```
[FlagChange] No background queue wired — propagating MarkUnread inline for INBOX/4277
```

Le scope de fond n'est donc **jamais créé** pendant les tests d'intégration.

### 2. Ils ont émis une erreur et sont restés verts

Dans ce même run, la suite a journalisé :

```
[FlagChange] Failed to persist the pending MarkUnread for INBOX/4277
System.InvalidOperationException: Error creating DbContext for user <compte de test>
 ---> ArgumentNullException: Value cannot be null. (Parameter 'Host')
```

**Niveau `Error`. La suite est passée.** Parce que le `catch` best-effort rend la panne
d'outbox non fatale (par conception), que le test asserte le flag sur le serveur — posé
par le repli en ligne — et qu'**aucun test n'asserte l'absence d'erreur journalisée**.

La jambe de durabilité était cassée dans la fixture, elle le **disait**, et personne ne
regardait. C'est le signal le moins cher du dépôt, et il est jeté.

### 3. Et même la file câblée, le défaut serait resté invisible

`MssRpps` **n'est renseigné dans aucune fixture d'intégration** (seul
`PgBouncerTransactionPoolingTests` le fait, pour autre chose). Or le nom de la base se
dérive de `(Email, MssRpps)` : sans RPPS, `NormalizeRpps` retombe sur sa valeur de repli
**dans les deux scopes**, requête et tâche de fond. Les deux calculent donc **le même
nom de base**, et l'écart ne peut pas apparaître — indépendamment de la file.

C'est exactement le piège que task-230 avait identifié pour son test unitaire, avec ce
commentaire : *« sans RPPS, l'assertion ne discriminerait rien »*. Le même piège
s'appliquait à l'intégration et n'a pas été vu.

## Remèdes demandés

### 1. Échouer sur une erreur journalisée inattendue — **le plus rentable**

Un filet qui aurait attrapé **ce défaut ET l'ambiguïté de constructeurs de task-230**,
sans rien connaître de leur nature.

- Collecter les événements de niveau `Error` (et `Critical`) émis pendant chaque test
  d'intégration, via un `ILoggerProvider` de test branché sur la fixture.
- **Faire échouer le test** s'il en reste à la fin, en affichant le message et
  l'exception — c'est le diagnostic, pas juste l'échec.
- **Liste d'exemptions explicite et courte**, chaque entrée portant sa justification :
  certains tests provoquent une erreur *délibérément* (chemins d'échec IMAP, gestion
  d'exception). Une exemption est une **décision**, pas une commodité — même exigence que
  la liste d'écrivains de `MailContents` (task-227).

### 2. Câbler `IBackgroundTaskQueue` dans les fixtures d'intégration

Pour que le scope de fond soit **réellement créé et exécuté**.

- Enregistrer la file **et** son hôte, ou fournir un exécuteur de test **synchrone** qui
  déroule les éléments à la demande (préférable : rend les tests déterministes, sans
  attente ni sommeil).
- Au moins **un test par chemin de fond existant** — enrichissement asynchrone,
  réconciliation de dossiers, propagation de flags — vérifiant que le travail **a
  réellement eu lieu**, pas seulement que la requête a répondu 200.

### 3. Renseigner `MssRpps` dans les fixtures

Pour que requête et tâche de fond **puissent** désigner des bases différentes, donc que
l'écart soit observable.

- RPPS de test dans les fixtures partagées, avec un commentaire disant **pourquoi** :
  sans lui, toute assertion sur la base est muette.
- Et l'assertion qui ferme le sujet : le travail de fond doit s'exécuter sur la base
  **du praticien de la requête** — comparaison du nom de base, pas de la liste des
  champs recopiés.

## Cohérence — bornes explicites

- **Aucun code de production modifié.** Si le câblage révèle un défaut de production,
  il est **signalé** et traité par une task dédiée : cette US livre le filet, pas les
  poissons qu'il attrape.
- Le remède 1 peut faire **échouer des tests aujourd'hui verts** — c'est son objet. Chaque
  échec ainsi révélé est soit un vrai défaut (task dédiée), soit une exemption justifiée.
  **Ni l'un ni l'autre ne se règle en désactivant le filet.**
- Le remède 2 ne doit **pas** introduire d'attente ni de sommeil : un exécuteur synchrone
  à la demande, sinon la suite devient lente et intermittente — ce qui la ferait ignorer,
  exactement le travers que cette US corrige.

## Definition of Done

> ### ✂️ DOD amendé le 2026-08-06 — décision humaine
>
> La US portait **trois remèdes**. Les remèdes **1** (échouer sur une erreur journalisée) et
> **3** (`MssRpps` dans les fixtures) sont **livrés** ; le remède **2** (câbler
> `IBackgroundTaskQueue`) est **découpé vers `task-237`**.
>
> **Pourquoi ce découpage.** Le filet livré a déjà attrapé un vrai défaut du harnais — la jambe
> de durabilité morte sur un hôte nul, six tests rouges portant l'erreur que la US citait en
> preuve. Le laisser sur une branche prolongeait l'aveuglement qui a laissé passer task-234,
> task-233 et task-236. Le remède 2 est plus gros que les deux autres réunis et porte son propre
> risque de conception (un exécuteur non déterministe rendrait la suite intermittente, donc
> ignorée — le travers même que cette US corrige) : il mérite sa revue.
>
> **La règle 11 ne s'y oppose pas** : elle interdit de livrer une US **produit** à moitié.
> Celle-ci n'a aucun impact produit — c'est sa borne, écrite par le PO en tête de fichier.
>
> Les items déplacés sont barrés ci-dessous et **repris intégralement** dans le DOD de
> task-237, dont ce qui est livré ici est une **dépendance stricte**.


- [ ] Build passes (0 errors) — `dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) — `dotnet test HealthPlatform.Api.Mail.sln`
- [ ] **Un test d'intégration échoue si une erreur inattendue est journalisée** — preuve par un test qui en provoque une délibérément et constate l'échec
- [ ] Liste d'exemptions explicite, **chaque entrée justifiée en une phrase** ; aucune exemption « pour faire passer »
- [x] ~~`IBackgroundTaskQueue` câblée dans les fixtures, **exécution déterministe** (aucun `Task.Delay`, aucun `Thread.Sleep`, aucune attente de scrutation dans les tests)~~ → **déplacé vers task-237** (découpage du 2026-08-06)
- [x] ~~**Au moins un test par chemin de fond** (enrichissement asynchrone, réconciliation de dossiers, propagation de flags) prouvant que le travail a eu lieu — assertion sur l'**effet**, pas sur le code HTTP~~ → **déplacé vers task-237** (découpage du 2026-08-06)
- [ ] `MssRpps` renseigné dans les fixtures partagées, avec le commentaire expliquant pourquoi
- [x] ~~**Un test compare le nom de base utilisé par la tâche de fond à celui de la requête** — l'assertion qui aurait attrapé task-234~~ → **déplacé vers task-237** (découpage du 2026-08-06)
- [x] **Preuve ROUGE du filet livré** : en supprimant son exemption, le test de démonstration échoue — vérifié. ~~La preuve par réintroduction de l'oubli de `MssRpps` dans un chemin de fond~~ → **déplacée vers task-237** : elle exige le scope de fond, donc la file câblée
- [ ] Aucun secret ni donnée de santé ajouté au harnais (le compte de test et ses identifiants restent hors du dépôt)
- [ ] Tout défaut de production révélé par le câblage est **signalé dans le task file**, non corrigé ici

## Manual Test Plan

- Lancer `dotnet test tests/mss.mail.integration.tests/mss.mail.integration.tests.csproj`
  et vérifier que la suite reste verte et **ne s'est pas allongée** de façon notable
- Introduire volontairement une erreur journalisée dans un chemin exercé (par exemple un
  `logger.LogError` temporaire) et vérifier que **le test correspondant échoue**, avec le
  message affiché dans la sortie
- Réintroduire volontairement l'oubli de `MssRpps` dans un chemin de fond et vérifier
  qu'**un test d'intégration échoue** en nommant l'écart de base
- Vérifier dans les journaux de la suite qu'on ne lit plus
  `No background queue wired` sur les chemins désormais câblés

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — outillage de test interne, aucune exigence DSR nouvelle honorée ni retirée
- **Exigences DSR honorées** : non applicable — aucun changement de périmètre fonctionnel
- **INS** : non applicable — aucun traitement d'identité modifié. ⚠️ Le harnais gagne un **RPPS de test fictif** ; il ne doit désigner **aucun professionnel réel**
- **Authentification PS** : inchangée — la US ne touche pas au flux PSC/e-CPS
- **Habilitations** : non applicable — aucune règle d'accès modifiée
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé. ⚠️ Le collecteur d'erreurs de test **conserve des messages de journal en mémoire pendant un test** : il doit rester cantonné au projet de tests et ne jamais être enregistré côté production, et son affichage en cas d'échec ne doit pas recopier de contenu de message MSSanté
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé — aucun flux ni stockage nouveau
- **AIPD / impact RGPD** : inchangé — aucun traitement nouveau. La boîte de test reste un compte dédié, hors données de patients réels

## Origine

Ouverte le 2026-08-05 sur constat humain, à la suite de task-234. Question posée par
l'humain : *« pourtant nous avons des tests d'intégration sur une boîte gmail, pourquoi
cela n'a pas révélé le problème ? »* — les trois raisons établies ci-dessus sont la
réponse, et cette US les traite.


## Branches

- `api-mail` (pushed) : `chore/task-235-filet-integration-erreurs-journalisees` —
  https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/chore/task-235-filet-integration-erreurs-journalisees
- `dtos-mss` (pushed) : même nom — **auto-incluse** par `/start`. Aucun changement de
  contrat n'est attendu (cette US ne touche que le harnais de test) : si elle reste vide,
  aucune PR ne sera ouverte pour elle, et il faudra la supprimer à la main.

Préfixe `chore/` et non `feat/` : la US ne modifie **aucun code de production** — c'est sa
borne explicite.

Pré-flight vert sur les six repos mesurables. Dépendance task-234 : archivée (mergée).

### Contexte acquis depuis la rédaction de la US, et qui la renforce

Deux défauts de la **même famille** ont été trouvés depuis, chacun invisible pour la même
raison — *le harnais est plus permissif que la production* :

1. **task-233** : trois tests unitaires ont dû être portés vers un vrai PostgreSQL, le
   fournisseur InMemory ignorant les colonnes calculées ; et un défaut de production (le
   getter `DataContext` levant) a passé 2 700 tests verts avant d'être trouvé **par un
   conflit de fusion**, parce que les tests **injectent** le contexte que la production
   **résout**.
2. **task-236** : l'outbox de propagation des flags levait dès que le cache d'identifiant
   était chaud — corrigé, mais **aucun test ne l'aurait attrapé**.

La US parlait de trois angles morts ; il y en a désormais **cinq documentés**, tous du même
genre. C'est un argument de plus pour le remède 1 (échouer sur une erreur journalisée), qui
est le seul des trois à attraper des défauts **dont on ne connaît pas la nature à l'avance**.


## Develop log

### Remède 1 — le filet, et il a mordu dès sa première exécution

`LoggedErrorSentinel` collecte les événements `Error` et `Critical` pendant chaque test ;
`IntegrationTestBase` fait échouer le test s'il en reste un non exempté, en affichant
message **et** exception.

**Portée par `AsyncLocal`, pas collecteur global.** xUnit exécute les classes en parallèle :
un collecteur unique ferait échouer la classe A sur une erreur de la classe B — un flaky,
donc un filet désactivé sous trois jours. Deux tests le vérifient plutôt que de le supposer :
l'isolation de deux portées concurrentes, et le fait que la portée **suit les continuations
asynchrones et le travail de fond** — c'est *la* propriété qui rend le filet utile, puisque
les défauts visés y vivent.

`Warning` est exclu **délibérément** : la suite en émet légitimement (replis best-effort), et
un filet qui crie pour des avertissements attendus serait ignoré.

**Ce qu'il a trouvé, mot pour mot ce que la US citait.** Appliqué à 11 classes, six tests de
`EmailManagementUseCaseTests` sont passés au rouge :

```
[Error] PendingActionRepository: Error creating DbContext for user <compte>
    → ArgumentNullException: Value cannot be null. (Parameter 'Host')
[Error] FlagPropagationService: [FlagChange] Failed to persist the pending MarkRead for INBOX/4
```

C'est **l'erreur donnée en preuve par la US** que la suite journalisait une panne et restait
verte. Le filet l'a reproduite sans rien connaître de sa nature — c'est exactement ce qu'on
lui demandait.

### Remède 3 — et la cause était le harnais, pas la production

Deux manques, tous deux dans les fixtures :

1. **`MssRpps` n'était renseigné nulle part.** Le nom de la base se dérive de
   `(Email, MssRpps)` : sans RPPS, le repli s'appliquait **dans les deux scopes**, qui
   calculaient donc le **même** nom de base. L'écart corrigé par task-234 était
   structurellement inobservable. RPPS **fictif**.
2. **`ConnectionStringServer` n'était jamais posée.** `ConnectionStringUser` s'en compose :
   tout scope construisant son propre contexte — les tâches de fond — tombait sur un **hôte
   nul**. C'est la cause exacte des six échecs, et sa correction les rend verts : la jambe de
   durabilité **fonctionne enfin** dans la fixture au lieu d'échouer en silence derrière un
   `catch` best-effort.

### Preuves ROUGE

| Preuve | Résultat |
|---|---|
| Exemption retirée du test de démonstration | le test échoue — le filet fait bien échouer |
| Filet appliqué avant le correctif de chaîne | 6 tests rouges, avec l'erreur de la US |
| Correctif de chaîne appliqué | 10/10 verts sur `EmailManagementUseCaseTests` |

### Liste d'exemptions

**Une seule entrée dans tout le dépôt**, sur le test de démonstration, avec sa justification
et un fragment étroit. Aucune exemption « pour faire passer ».

### Validation

Build 0 erreur / 0 avertissement · domain 106/106 · infrastructure 421/421 ·
application 1998/1998 · api 650/650 · integration **348/348** (16 ignorés).

### ⚠️ Ce qui N'EST PAS fait — le remède 2

**`IBackgroundTaskQueue` n'est toujours câblée dans aucune fixture.** Restent donc dus, et je
ne les ai pas commencés :

- l'exécuteur de test **synchrone et déterministe** (la US interdit tout `Task.Delay` /
  `Thread.Sleep`) ;
- **au moins un test par chemin de fond** — enrichissement asynchrone, réconciliation de
  dossiers, propagation de flags — prouvant que le travail a **eu lieu**, pas que la requête
  a répondu 200 ;
- l'item de DOD **« un test compare le nom de base utilisé par la tâche de fond à celui de la
  requête »** — l'assertion qui aurait attrapé task-234. Les deux prérequis en sont désormais
  posés (`MssRpps` **et** la chaîne serveur), donc elle est devenue **écrivable** ; elle ne
  l'était pas avant ce commit.

Conséquence à ne pas maquiller : les services de production prennent la file en paramètre
**optionnel**, donc elle vaut `null` en test et le code emprunte son **repli en ligne**. Le
scope de fond n'est **toujours jamais créé** pendant les tests d'intégration. Le remède 1
attrape désormais ce que ce chemin journalise **quand il est emprunté** ; il ne le fait pas
emprunter.

### Adoption du filet — état exact

**11 classes sur 21** en héritent (les trois `ImapService*`, les huit `UseCase*`). Une classe
qui n'en hérite pas **n'est pas protégée** — ce n'est pas une exemption, c'est un reste à
faire. Le choix de ne pas basculer les vingt-et-une d'un coup est assumé : cela aurait produit
une fournée d'échecs mêlant vrais défauts et erreurs délibérées, impossible à trier, donc en
pratique un filet désactivé.

Les classes restantes tournent en outre sur d'autres fixtures (`PostgreSqlFixture`,
`AiServicesFixture`, `PgBouncerFixture`, `AnnuaireSanteFixture`) où le fournisseur n'est **pas
branché** : y appliquer la base serait sans effet tant que leur `AddLogging` ne l'a pas.


## Sonar log

### KPIs qualité (baseline → final)

| Métrique | Baseline (task-233, 2026-08-05) | Final (task-235, 2026-08-06) |
|---|---|---|
| Quality Gate (new code) | **ERROR** | **ERROR** |
| `new_violations` | 33 | 35 |
| `new_coverage` | 0.0 % (seuil 80) | 0.0 % (seuil 80) |
| `new_security_hotspots_reviewed` | 0.0 % (seuil 100) | 0.0 % (seuil 100) |
| Bugs / Vulnérabilités / Smells | 2 / 0 / 35 | 2 / 0 / 36 |
| Coverage projet / Duplication | 0.0 % / 0.4 % | 0.0 % / 0.4 % |
| Ratings (Fiab. / Sécu. / Maint.) | C / A / A | C / A / A |
| `ncloc` | 43 533 | 44 159 |

Les deux relevés sont cette fois **comparables** — même périmètre de scan, `ncloc` en hausse du
seul volume ajouté.

### La mesure qui attribue

**Combien des 35 violations tombent dans un fichier touché par cette task ?**

> **Zéro.**

Réparties ainsi, et toutes héritées : `report.py` 15, `journey.js` 7, `journey-model.js` 4
(outillage k6, tasks 173/174/195) ; `AppHost.cs` 3 ; `AppHostSecrets.cs`,
`IIheXdmProcessingService.cs`, `ContactRepository.cs`, `BaseRepository.cs`,
`SmtpConnectionFactory.cs` 1 chacun.

### Une violation était à moi, et corrigée

`DataContextGetterScanTests.cs:45` — `SYSLIB1045` (INFO) : la regex de la garde d'architecture
livrée par **task-233** était construite à l'exécution. Passée en `[GeneratedRegex]`, donc
compilée à la génération. Mécanique, sans risque, et c'est mon code : je le corrige plutôt que
de le compter comme dette d'autrui. `api-mail` 650/650 après.

Les deux `S103` (lignes > 150 caractères) de `BaseRepository.cs` et `SmtpConnectionFactory.cs`
appartiennent à task-231 : **hors périmètre** (règle 6), signalées ici avec leur provenance.

### Ce qui garde le Quality Gate rouge — inchangé, et pour la cinquième fois

1. **`new_coverage` = 0** — aucun rapport de couverture n'est importé par le scan. Ce n'est pas
   une couverture faible, c'est une **absence de mesure** : le seuil de 80 % est inatteignable
   par construction, à chaque cycle. Cela relève d'une task d'outillage, pas de code.
2. **`new_security_hotspots_reviewed` = 0** — dont les deux `Math.random()` de `journey.js`.
   **Cinquième signalement.** Ce sont des points à *réviser*, pas à corriger ; personne ne le
   fait, donc le Quality Gate reste rouge indéfiniment.
3. **`new_violations` > 0** — la période « new code » englobe des tasks déjà mergées. Une task
   peut donc être rouge sans avoir introduit la moindre dette. C'est le cas ici.

### Itérations

**Une seule.** Zéro finding sur le code de la task ; le reste appartient à d'autres périmètres.
Aller jusqu'à cinq itérations aurait voulu dire réparer la dette d'autrui sous couvert de cette
US.


## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/164 — label `awaiting-human-merge`
- `dtos-mss` : branche auto-incluse **vide**, aucune PR. À supprimer à la main au merge — rien
  dans la chaîne ne nettoie une branche auto-incluse restée sans commit (défaut de cycle déjà
  signalé deux fois).

## Code Review Summary

**APPROVED**, 0 blocage. Un défaut trouvé et corrigé pendant le cycle : la fabrique de logger du
sentinelle existait **deux fois** dans le même fichier. Une fabrique dupliquée est une fabrique
qui dérive — il suffit qu'une des deux oublie le fournisseur pour que son test ne mesure plus
rien tout en restant vert, exactement le genre de test sans valeur que les cycles récents ont
produit trois fois.

### Ce que ce cycle apprend

Le filet a trouvé un vrai défaut **du premier coup**, et ce défaut était dans le harnais
lui-même : ni `MssRpps` ni `ConnectionStringServer` n'étaient posés, donc la jambe de
durabilité était morte en silence. Autrement dit, l'outil chargé de détecter que le harnais
mentait a commencé par trouver que **le harnais mentait**. C'est la meilleure justification
rétrospective qu'on pouvait lui souhaiter.

⚠️ **Durée de la suite d'intégration : ~2 min 45 s → 5 min 05 s** sur ce run. Cause probable et
**non établie** : la jambe de durabilité fonctionnant désormais, les chemins concernés
provisionnent réellement une base par praticien au lieu d'échouer immédiatement. Le DOD de
task-237 prend 2 min 45 s comme référence — à réviser si l'écart se confirme.


## Merged

Mergée le **2026-08-06** par l'humain (HAG, règle 10), sur attestation `--i-tested`.

- `api-mail` : PR #164 **squash-mergée** → `80b839c` sur `develop`. Ref remote supprimée,
  **branche locale conservée**. **CI `develop` verte.**
- `dtos-mss` : branche auto-incluse **vide (0 commit vérifié)**, aucune PR. Supprimée localement
  et sur le remote.

### ⚠️ Le défaut de cycle en est à sa TROISIÈME occurrence

Une branche auto-incluse sur `dtos-mss` restée sans commit n'est nettoyée par **rien** dans la
chaîne : elle a dû l'être à la main pour task-233, task-232 et maintenant task-235. Entre-temps
elle a **bloqué le pré-flight de `/start` deux fois**, chaque task payant l'auto-inclusion de la
précédente. Ce n'est plus une gêne ponctuelle, c'est un motif — il mérite sa propre US.

### Ce qui est désormais sur `develop`

Le filet à erreurs journalisées, `MssRpps` et `ConnectionStringServer` dans les deux fixtures
d'intégration. Autrement dit : **la suite ne peut plus journaliser une panne en restant verte**
sur les 11 classes qui en héritent.

### ⚠️ Ce qui reste dû, et n'a PAS été livré ici

- **task-237** — câbler `IBackgroundTaskQueue`. Tant que ce n'est pas fait, les services
  empruntent leur **repli en ligne** et **le scope de tâche de fond n'est jamais créé pendant
  les tests d'intégration**. Le filet attrape ce que ce chemin journalise *quand il est
  emprunté* ; il ne le fait pas emprunter.
- **Adoption : 11 classes sur 21.** Les dix autres ne sont **pas protégées** — ce n'est pas une
  exemption, c'est un reste à faire, d'autant qu'elles tournent sur des fixtures où le
  fournisseur n'est pas branché.
- **Durée de la suite d'intégration : ~2 min 45 s → 5 min 05 s**, cause **non établie**
  (probablement le provisionnement d'une base par praticien désormais réellement exercé). Le DOD
  de task-237 prend 2 min 45 s comme référence et sera peut-être à réviser.

Mergée en connaissance de ces trois écarts, sur décision humaine explicite.
