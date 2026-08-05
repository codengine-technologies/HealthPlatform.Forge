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

- [ ] Build passes (0 errors) — `dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) — `dotnet test HealthPlatform.Api.Mail.sln`
- [ ] **Un test d'intégration échoue si une erreur inattendue est journalisée** — preuve par un test qui en provoque une délibérément et constate l'échec
- [ ] Liste d'exemptions explicite, **chaque entrée justifiée en une phrase** ; aucune exemption « pour faire passer »
- [ ] `IBackgroundTaskQueue` câblée dans les fixtures, **exécution déterministe** (aucun `Task.Delay`, aucun `Thread.Sleep`, aucune attente de scrutation dans les tests)
- [ ] **Au moins un test par chemin de fond** (enrichissement asynchrone, réconciliation de dossiers, propagation de flags) prouvant que le travail a eu lieu — assertion sur l'**effet**, pas sur le code HTTP
- [ ] `MssRpps` renseigné dans les fixtures partagées, avec le commentaire expliquant pourquoi
- [ ] **Un test compare le nom de base utilisé par la tâche de fond à celui de la requête** — l'assertion qui aurait attrapé task-234
- [ ] **Preuve ROUGE de chaque filet** : en réintroduisant l'oubli de `MssRpps` dans un chemin de fond, un test d'intégration échoue ; en supprimant la collecte d'erreurs, le test de démonstration passe
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
