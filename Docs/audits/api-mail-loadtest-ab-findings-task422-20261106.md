# Gain mesuré des correctifs issus du tir court du 2026-11-05 — A/B/A du 2026-11-06

> Banc de charge api-mail (EPIC E015). Synthèse de trois tirs joués à la suite dans la même session.
> Rapports détaillés : `api-mail-loadtest-journey-courte-1400-1996-ab-findings-{avant-1,apres,avant-2}-20261106.md`.

## Question

Le tir court 1400 → 1996 du 2026-11-05 (task-422,
`api-mail-loadtest-journey-courte-1400-1996-task422-20261105.md`) a produit deux findings :
- **F1** : la recherche plein texte prend 50,6 % du temps SQL ;
- **F2** : le registre est relu environ 6 fois par requête HTTP.

Depuis, quatre tasks ont été mergées sur `develop` :

| Task | Objet |
|---|---|
| task-427 | F1, recherche en un passage |
| task-424 | Harnais, verdicts par palier |
| task-425 | Panne de messagerie en 503 |
| task-426 | F2, cache du compte du registre |

**Combien la plateforme a-t-elle gagné, exactement ?**

## Protocole

- **Avant** = `d6712a10` (merge de task-422, pool PgBouncer à 1 : l'état du tir de référence).
- **Après** = `f50f2ae5` (`develop` du 2026-11-06, les quatre tasks mergées).
- **Seul le binaire de l'API change.**
  - AppHost et faux fournisseur IA sont identiques entre les deux commits (diff vide).
  - Le harnais k6 et le générateur de rapport sont ceux de `f50f2ae5` pour les trois tirs.
- **Tir identique** :
  - `JOURNEY_STAGES="1400:18m,1996:18m"`, K = 1, IA simulée, pool 1 ;
  - tireur k6bench, banc mail cluster, `LATENCY_MS=96` ;
  - 1 996 médecins hydratés, mêmes bases.
- **Ordre A/B/A** : avant (18:02) → après (18:52) → avant (19:41).
  - Un tir de la veille n'est plus opposable à 1996 : les bases grossissent à chaque tir et le cgroup Postgres est
    plein.
  - L'ordre a deux effets contraires : les bases grossissent, le cache se réchauffe.
  - L'alternance encadre le tir « après » par deux tirs « avant ».

## Conditions des trois tirs

| | avant-1 | **après** | avant-2 |
|---|---|---|---|
| Requêtes HTTP | 743 709 | 760 903 | 752 654 |
| Débit à 1996 (req/s, régime) | 406,5 | 412,8 | 409,0 |
| Erreurs k6 | 0,011 % | 0,013 % | 0,005 % |
| Fautes majeures du cgroup Postgres, max | 56,8 /s | 16,2 /s | **7,3 /s** |
| Attente disque (part du temps SQL) | 14,0 % | 9,8 % | **6,7 %** |

Le tir **avant-2** a joui des meilleures conditions disque des trois. C'est la référence la plus exigeante. Les gains
ci-dessous sont donnés contre lui.

## Ce que fait la base

| Grandeur | avant-1 | **après** | avant-2 | Gain contre avant-2 |
|---|---|---|---|---|
| Temps SQL total du tir | 52,4 min | **21,3 min** | 45,7 min | **−53 %** |
| Coût SQL par requête HTTP (rapport) | 8,3 ms | **4,3 ms** | 7,0 ms | **−39 %** |
| Backends Postgres actifs (équivalent) | 2,66 | **1,41** | 2,26 | −38 % |
| Recherche plein texte : temps SQL | 26,1 min | **5,4 min** | 23,9 min | **−77 %** |
| Registre : temps SQL | 419 s | **108 s** | 387 s | **−72 %** |
| Registre : lectures `accounts` + ancre par requête | 5,93 | **0,03** | 5,93 | −99,5 % |
| `DISCARD ALL` par requête | 7,12 | **0** | 7,12 | −100 % |
| Lecture disque (temps cumulé) | 234 s | 104 s | 116 s | −10 % |

**La moitié du temps de Postgres est libérée.** La base en tire moins pour les deux chemins corrigés, et elle sert plus
vite tout le reste.

## Ce que voit le médecin — temps de réponse par étape (ms, p50 / p95)

### Palier 1996 médecins

| Étape | avant-1 | **après** | avant-2 | p95 contre avant-2 |
|---|---|---|---|---|
| Arrivée tableau de bord | 133 / 748 | **69 / 649** | 116 / 702 | −8 % |
| Ouvrir / rafraîchir l'inbox | 137 / 478 | **57 / 174** | 110 / 362 | **−52 %** |
| Ouvrir un message enrichi (servi base) | 147 / 440 | **57 / 147** | 118 / 330 | **−55 %** |
| Ouvrir un message froid (IMAP) | 513 / 761 | **460 / 534** | 498 / 661 | −19 % |
| Recherche | 563 / 1 219 | **368 / 707** | 513 / 945 | −25 % |
| Envoi | 642 / 1 134 | **499 / 964** | 588 / 1 073 | −10 % |
| Télécharger une PJ | 170 / 777 | **66 / 443** | 134 / 503 | −12 % |
| Marquer lu | 136 / 435 | **68 / 136** | 116 / 299 | **−55 %** |
| Rechercher un patient | 87 / 328 | **58 / 87** | 80 / 203 | **−57 %** |
| Page d'un dossier patient | 180 / 578 | **85 / 239** | 147 / 406 | **−41 %** |
| Fiche patient complète | 907 / 2 915 | **442 / 1 044** | 729 / 2 011 | **−48 %** |

### Palier 1400 médecins

| Étape | avant-1 | **après** | avant-2 | p95 contre avant-2 |
|---|---|---|---|---|
| Arrivée tableau de bord | 71 / 556 | **59 / 541** | 71 / 576 | −6 % |
| Ouvrir / rafraîchir l'inbox | 52 / 129 | **41 / 97** | 51 / 128 | −24 % |
| Ouvrir un message enrichi (servi base) | 48 / 103 | **35 / 66** | 47 / 99 | −33 % |
| Ouvrir un message froid (IMAP) | 457 / 526 | **446 / 510** | 458 / 525 | −3 % |
| Recherche | 414 / 672 | **328 / 593** | 405 / 709 | −16 % |
| Envoi | 516 / 941 | **489 / 925** | 512 / 941 | −2 % |
| Télécharger une PJ | 53 / 124 | **37 / 79** | 50 / 110 | −28 % |
| Marquer lu | 54 / 110 | **36 / 86** | 54 / 109 | −21 % |
| Rechercher un patient | 63 / 87 | **55 / 67** | 63 / 85 | −21 % |
| Page d'un dossier patient | 70 / 162 | **56 / 110** | 66 / 144 | −24 % |
| Fiche patient complète | 391 / 727 | **302 / 510** | 387 / 690 | −26 % |

- **Aucune étape plus lente**, à aucun palier, contre aucun des deux tirs « avant ».
- Le gain croît avec la charge : il est modéré à 1400, où la base n'est pas encore le goulet, et fort à 1996.
- Les étapes servies par la base gagnent le plus. Les étapes dominées par la messagerie (message froid, envoi) bougent
  peu : leur temps est chez le serveur IMAP/SMTP et dans la latence injectée.

## Grille SLO (`docs/SLO-parcours-medecin.md`)

| Palier 1996 | avant-1 | **après** | avant-2 |
|---|---|---|---|
| Étapes hors grille | 2 (message servi base p50 147 > 100 ; recherche p50 563 > 500) | **0** | 2 (message servi base p50 118 > 100 ; recherche p50 513 > 500) |

Le « SLO non tenu » affiché par les trois rapports ne vient que de la **durée du palier** : 18 min, alors que la grille
exige 30 min de plateau. Ce verdict est indicatif. **Avec le code « après », toutes les étapes sont dans la grille à
1 996 médecins actifs.**

## Attribution

- Le gain cumulé n'est pas ventilé tâche par tâche par ce protocole.
- Les deux correctifs de performance ont chacun leur mesure isolée :
  - task-427 : temps SQL de la recherche −79 % ;
  - task-426 : lectures du registre −99,5 %, A/B dans la même session.
- Ici, les deux formes corrigées expliquent **≈ 21 min** des 24,4 min de SQL économisées contre avant-2 :
  - recherche −18,5 min ;
  - registre −4,7 min.
- Le reste vient du désengorgement de Postgres : les autres requêtes attendent moins.
- task-425 et task-424 n'ont pas d'effet de performance attendu : la première change des codes d'erreur, la seconde le
  harnais.

## Ce qui reste

- **Multiplexeur à 1400** : `cl_waiting` est non nul sur 20 à 28 % des relevés dans les trois tirs. Il en résulte de rares
  503 `DATABASE_UNAVAILABLE` (PgBouncer `08P01 query_wait_timeout`) : 0, 6 et 3 en régime, environ 0,001 %. C'est la
  contrepartie connue de `default_pool_size = 1` (task-422), pas une régression.
- **Arrêt du tir** : un `GET …/download/attachment/…` interrompu par l'arrêt des VUs sort en **500** sur les deux codes.
  C'est un site de 500 restant, hors régime.
- **Prochaine limite** : la mémoire de Postgres (cgroup de 48 Go plein dans les trois tirs). La moitié du temps SQL est
  libérée : la marge porte désormais sur la mémoire, plus sur le calcul.
