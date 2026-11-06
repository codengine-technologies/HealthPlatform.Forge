# task-426 — /review : un critère de la DoD n'est pas tenu à la lettre (p95 du téléchargement de PJ à 1400)

**Étape** : `/review`, 2026-11-06 vers 17:55. **Nature** : arbitrage humain sur un critère de la DoD. Le code n'est pas
en cause. La task reste en `wip-*` et aucune PR n'est ouverte (règle 9).

## Ce qui est tenu

- **Revue de code** : aucun point bloquant (détail ci-dessous). Règle 1b : 4 tests d'intégration de bout en bout, chacun
  vu rouge par mutation (`## Develop log`).
- **Sonar** : Quality Gate OK, 0 issue sur le nouveau code (3 issues de test corrigées à l'itération 1).
- **E2E** : vert, mobile 58/58 et Angular 71/71.
- **Build et tests** (rejoués par `/review`, HEAD `6728452c`) : 0 avertissement, 0 erreur. Domain 210, infrastructure
  705, api 1 361, application 4 028, intégration 1 124 (+16 ignorés), **0 échec**.
- **Banc**, tir court 1400 → 1996, contre un contrôle `develop` joué juste après dans la même session :
  - lectures du registre `accounts` + ancre : **5,94 → 0,03 par requête HTTP (−99,5 %, cible −50 %)** ;
  - `DISCARD ALL` du registre : 7,13 → 0 par requête ;
  - temps SQL du registre −67 %, temps SQL total −7 % ;
  - 0 erreur 5xx en régime dans les deux tirs.

## Le point à trancher

DoD : « Aucun p95 d'étape dégradé de plus de 20 % ». Contre le contrôle du même jour, **une seule étape sur 22**
(11 étapes × 2 paliers) dépasse :

| Télécharger une PJ, palier 1400 | Contrôle `develop` | task-426 |
|---|---|---|
| p95 client (k6) | 130 ms | **378 ms** |
| p50 client (k6) | 51 ms | 43 ms (mieux) |
| p95 serveur (Prometheus, palier) | 314 ms | 409 ms |

Même étape au palier 1996 : 743 → 792 ms (+7 %), dans la marge.

**Ce que dit la télémétrie** :
- La requête SQL des pièces jointes lit le **même volume** dans les deux tirs (786 066 et 770 591 blocs disque). Elle
  met plus longtemps à les lire avec task-426 : 47,5 s contre 36,2 s.
- C'est tout le disque du tir qui est plus lent, pas cette requête : 182 s contre 136 s de lecture disque au total, pour
  un volume comparable, avec 33 fautes majeures/s contre 11,6.
- Le tir task-426 est passé **en premier**, sur un cache de pages resté au repos depuis le matin. Le contrôle a hérité du
  cache réchauffé par ce premier tir.
- Cette route ne lit pas le registre plus qu'une autre : task-426 change le même chemin pour toutes les routes.
- Ce p95 est instable d'un tir à l'autre : il valait **641 ms** au tir task-427 de la veille, sur un code sans task-426.

Lecture de la forge : écart de latence disque lié à l'ordre des tirs, pas au code. Ce n'est pas démontré par une
alternance A/B/A, qui coûterait environ 45 min de banc de plus.

**Options :**
1. **Accepter** : le critère est jugé sur son intention (aucune étape ralentie par le code). La forge consigne votre
   décision dans le task file, puis ouvre la PR avec ce point en tête du corps.
2. **Rejouer un tir task-426 après le contrôle** (alternance A/B/A, ~45 min de banc), puis rejuger le critère.
3. **Refuser** : préciser ce qui doit être démontré.

Réponse attendue : « 1 », « 2 » ou « 3 + précision ». Ensuite, `/review task-426` reprend.

## Revue de code (aucun point bloquant)

- `TenantRegistrySynchronizer` ✅ : compte lu par le cache, `EnsureAccountAsync` seulement si inconnu ou projection
  nouvelle. Panne du registre : la sélection de boîte lit toujours la base (`GetMailboxAsync`) et remonte le 503.
- `PostgresTenantRegistryClient` ✅ : invalidation seulement sur écriture ; ancre lue dans la requête de la boîte, même
  règle que `LoadAnchorAsync` (source unique `AnchorCandidates`).
- `TenantRegistryConnectionString` ✅ : `NoResetOnClose`, état de session inventorié (registre et audit).
- ⚠️ Suggestion, non bloquante — **fraîcheur de l'ancre dans `SelectAsync`** : le contrôle de conflit PSC (409) lit
  l'ancre du compte en cache, jusqu'à 10 min. Une course étroite entre un rattachement et une lecture concurrente
  peut remettre en cache un compte non ancré. La décision d'accès reste fraîche : `GetMailboxAsync` et
  `ListMailboxesAsync` relisent l'ancre en base et refusent (403). Seul le code de refus peut alors différer (403 au
  lieu de 409). Point déjà signalé dans le `## Develop log`.
- Règle 14 : aucun acte sans auteur, aucun accès qui contourne le verdict de l'opérateur, aucune donnée par personne,
  aucun rôle de titulaire modifié.
