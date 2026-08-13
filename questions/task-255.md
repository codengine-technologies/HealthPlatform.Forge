# questions/task-255.md — `/review` bloqué : le correctif de banc fait tomber le garde-fou de task-200

**Date** : 2026-08-13
**Étape** : `/review task-255`
**État de la chaîne** : **arrêtée** avant commit et avant ouverture de PR.
La task reste en `wip-task-255.md`.

## Le blocage

Build `api-mail` : ✅ 0 erreur.
Test : ❌ **1 échec**, et il est causé par le correctif de cette branche.

```
mss.mail.integration.tests.Repository.PgBouncerTransactionPoolingTests
  .BenchUpstream_DoesNotRelyOnHostDockerInternal [FAIL]

Assert.Contains() Failure: Sub-string not found
String:    "* = host=postgres-pgvector port=5432 user"···
Not found: "pgupstream"
   at PgBouncerTransactionPoolingTests.cs:line 284
```

Le test de task-200 vérifie deux choses sur la ligne d'upstream du banc :

```csharp
Assert.DoesNotContain("host.docker.internal", upstream);   // ✅ toujours vrai
Assert.Contains("pgupstream", upstream);                   // ❌ le correctif l'a retiré
```

## Pourquoi ce n'est pas une simple ligne à mettre à jour

**Le test assertait le mauvais invariant, et c'est précisément ce qui a laissé
passer la panne que task-255 a dû diagnostiquer.** Il vérifie **le nom** utilisé
comme upstream. Or le nom n'avait pas changé : c'est **ce en quoi il résout** qui
a changé, Docker Desktop ayant ajouté un enregistrement AAAA à `host-gateway`.
PgBouncer a retenu l'IPv6, échoué en `Network unreachable`, mis l'échec en cache,
et rendu des `08P01` à tous les clients du pool — **13 % des lots perdus**, et
deux campagnes jetées avant que la cause soit établie.

Remplacer `Assert.Contains("pgupstream")` par `Assert.Contains("postgres-pgvector")`
reproduirait exactement le défaut de conception : un test qui protège la lettre du
correctif du jour, pas sa raison d'être. Le bon invariant est **« l'upstream du
banc résout en IPv4 et ne dépend d'aucun alias d'hôte »**, ce qui demande un vrai
travail de test — et c'est le cœur de **task-257**, écrite pour ça.

## Deuxième point à trancher, indépendant du test

Le correctif dans `pgbouncer.ini` **n'est pas complet à lui seul** : il exige que
le conteneur PgBouncer soit membre du réseau `postgresql_default`, ce qui est fait
**à la main** aujourd'hui (`docker network connect`). Tel quel sur `develop`, un
démarrage de banc rendrait un PgBouncer qui ne résout pas son upstream tant que
personne n'a joué cette commande.

À noter tout de même : l'échec deviendrait **total et bruyant** (rien ne se
connecte, on le voit tout de suite) au lieu d'être **partiel et silencieux**
(13 % de lots perdus qui corrompent une mesure sans la faire échouer). Le second
est le pire des deux pour un banc de mesure. Le remède est documenté dans le
skill, à l'endroit où on le lit avant une campagne.

## Arbitrage demandé

**Option A — recommandée. Sortir le correctif `pgbouncer.ini` de task-255.**
task-255 redevient ce qu'elle est : une US **de mesure**, sans une ligne de code
applicatif. Le correctif d'upstream part **entier** dans task-257 — `pgbouncer.ini`
+ le rattachement réseau dans `AppHost.cs` + le garde-fou réécrit sur la famille
d'adresses — c'est-à-dire un changement cohérent et testé, plutôt qu'un tiers de
correctif mergé avec un test désactivé. La PR de task-255 ne porte alors que le
task file, le skill et la ligne d'INDEX. Le diagnostic, lui, ne se perd pas : il
est écrit dans le task file, dans le skill et dans task-257.

**Option B — corriger le test dans task-255.** Réécrire
`BenchUpstream_DoesNotRelyOnHostDockerInternal` pour qu'il teste la famille
d'adresses résolue, et livrer aussi le rattachement réseau dans `AppHost.cs` pour
que le banc démarre sans geste manuel. C'est faisable, mais c'est **le contenu de
task-257** déplacé dans task-255 — donc une US de mesure qui livre un correctif
d'infrastructure, et task-257 qui perd son objet.

**Option C — ne rien changer et faire passer le test en l'état.** Écartée : cela
voudrait dire assouplir le garde-fou pour qu'il accepte n'importe quel upstream,
et supprimer la seule protection existante contre la classe de pannes qui a coûté
deux campagnes.

## Ce qui est prêt et ne dépend pas de cet arbitrage

- Campagne complète, trois points de concurrence, verdict établi (`wip-task-255.md`)
- Rapports de tir + ligne d'INDEX
- Pièges consignés dans `.claude/skills/loadtest-skill/SKILL.md`
- Trois US créées : `todo-task-257.md`, `todo-task-258.md`, `todo-task-259.md`
