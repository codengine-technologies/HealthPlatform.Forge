# task-427 — /review : un critère de la DoD n'est pas tenu à la lettre (taux de cache)

**Étape** : `/review`, 2026-11-06 vers 00:50. **Nature** : arbitrage humain sur un critère de la DoD. Le code n'est pas
en cause. La task reste en `wip-*` et aucune PR n'est ouverte (règle 9).

## Ce qui est tenu

- **Revue de code** : aucun point bloquant. Comportement identique, prouvé par 9 tests d'intégration verts sur
  l'ancien code comme sur le nouveau, et par 5 mutations vues rouges (`## Develop log`). SQL constant et paramétré.
- **Sonar** : Quality Gate OK, 0 issue sur le nouveau code.
- **E2E** : vert, mobile 58/58 et Angular 71/71.
- **Banc**, tir court 1400 → 1996, même protocole que la référence task-422 :
  - temps SQL de la recherche **−79 %** (cible −50 %) ;
  - recherche p50 **384 ms** à 1996 (cible 500) ;
  - aucune étape dégradée, toutes améliorées ;
  - 0 erreur 5xx.
- **Build et tests** : verts, sauf les 3 tests « du jour », rouges connus entre 00:00 et 02:00 (IMAP `SINCE` en UTC,
  mémoire de session). Ils sont rejoués automatiquement après 02:00, résultat ci-dessous.

## Le point à trancher

DoD : « taux de cache Postgres **pas plus mauvais** qu'au tir de référence ». Mesure : 96,74 % → **96,34 %**.

Ce ratio vaut `lus en cache ÷ (lus en cache + lus sur disque)`.

| Grandeur (tir entier) | Référence | task-427 |
|---|---|---|
| Blocs lus sur disque | 2 006 703 | **1 992 204** (−0,7 %) |
| Blocs lus en cache | 115 752 166 | 95 676 621 (−17 %) |
| Fautes majeures du cgroup Postgres, max | 22,3 /s | **0,6 /s** |

Le ratio baisse parce que la recherche ne relit plus six fois les corps en cache. Le nombre de lectures en cache, au
dénominateur, chute. Les lectures disque, elles, n'augmentent pas. Le critère avait été écrit (par le PO, le
2026-11-05) pour interdire un **index** qui chasserait le jeu de travail du cache. Aucun index n'a été ajouté.

**Options :**
1. **Accepter** : le critère est jugé sur son intention (lectures disque non accrues). La forge consigne votre
   décision dans le task file, puis ouvre la PR avec ce point en tête du corps.
2. **Refuser** : préciser ce qui doit être démontré.

Réponse attendue : « 1 » ou « 2 + précision ». Ensuite, relancer `/review task-427`.

## Rejeu des tests « du jour » après 02:00

_(complété automatiquement par la forge)_
