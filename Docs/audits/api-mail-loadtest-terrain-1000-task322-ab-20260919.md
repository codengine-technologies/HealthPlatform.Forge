# Campagne de charge — A/B task-322 : projection des listes, tir `terrain` 1 000 inscrits (2026-09-19, soir)

> Tir B `terrain-1000-20260919-task322`, 19:27:24 → 22:28:38 à l'horloge du poste (3 h 01 min 14).
> Tir A de référence : `terrain-1000-20260919` du matin (11:03 → 14:04), `develop` à `6a82f28f` — audit `api-mail-loadtest-terrain-1000-postgres-20260919.md`.
> Tir B : branche `feat/task-322-projection-entetes-index-mailid` à `a3b38e2f` (PR api-mail #246, non mergée), même harnais.
> Iso-conditions : même population (1 000 bases hydratées, **non purgées** entre les deux), mêmes paramètres (247 messages par boîte, `UID_BASE=365`, corpus fileté 0,3, latence 96 ms, chauffe hydratée), banc distant `192.168.1.69`, cache de pages **froid au départ dans les deux cas** (conteneur Postgres recréé à 10:38 puis à 18:53).
> Rapport : `Api/Mail/tests/loadtest-k6/reports/2026-09-19/report-terrain-1000-20260919-task322-222838.md`. Lignes comparées : `reports/POSTGRES-INDEX.md`.

## Ce que ce tir est

**Un A/B à un seul facteur** : le code. Une seule chose sépare les deux tirs — les trois commits de task-322 (projection des pièces jointes et des documents sur les listes, deux index `MailId`). La question posée : *qu'est-ce que cela rend, mesuré, et où ?*

## Verdict — les gains sont là où le constat les plaçait

### Serveur SQL (`pg_stat_statements` + compteurs serveur, fin − début)

| Grandeur | A (matin, `develop`) | **B (soir, task-322)** | Δ |
|---|---|---|---|
| Temps SQL cumulé sur 3 h | 139 min | **55,7 min** | **−60 %** |
| Coût SQL par requête HTTP | 39,3 ms | **16,5 ms** | **−58 %** |
| Backends actifs (équivalent, temps actif ÷ durée) | 0,80 | **0,33** | ÷ 2,4 |
| Requête « pièces jointes » de la page d'en-têtes | 63,3 min (45,6 %), 134 ms/appel | **disparue** (reste 3 446 appels à 10 ms : téléchargement/détail, 1,1 %) | −63 min |
| Requête « documents » de la page d'en-têtes | 66,7 min (48,0 %), 141 ms/appel, 686 blocs | **45,7 min (82 %), 97 ms/appel, 640 blocs** | −31 % par appel |
| Taux de cache (blocs) | 93,75 % | **95,72 %** | +2 pts |
| Lecture disque | 5,40 Mo/s | **3,08 Mo/s** | **−43 %** |
| Attente disque dans le temps SQL actif | 2,5 % | 1,6 % | |
| **cgroup mémoire du conteneur Postgres** (moy / max) | 99 / 100 % (47,8 Go de cache) | **37 / 39 %** | **le cache de pages n'a plus besoin de porter les blobs** |
| Fautes de page majeures (max/s) | 3,9 | 0,2 | |
| Croissance des bases praticien | 671 Mo | 303 Mo | |
| Transactions / s | 468 | 461 | iso |
| Backends (échantillonneur, moy / max) | 230 / 676 | 226 / 670 | iso — suit la population, pas le travail |
| Login Postgres p50 / p95 | 6 / 7 ms | 6 / 7 ms | iso |
| Fichiers temporaires | 350 Mo (artefact de l'outil, base `postgres`) | **0** | photo corrigée |

**La ligne qui compte** : le coût SQL d'une requête HTTP est divisé par 2,4, et Postgres n'a plus qu'un tiers de requête en exécution en moyenne pour la même population. **La ligne inattendue** : le cgroup mémoire du conteneur, saturé à 100 % le matin, tombe à 37 % — les blobs des pièces jointes ne traversent plus le cache de pages, donc il n'a plus à les retenir. À 5 000 inscrits, c'est ce poste qui aurait fait le prochain plafond mémoire.

### Praticien (grille SLO, régime, p50 / p95)

| Geste | A | **B** | Δ |
|---|---|---|---|
| Page d'en-têtes (`read_list` / `emails`, 25 en-têtes) | 96,6 / 155 ms | **69,9 / 110 ms** | **−28 % / −29 %** |
| Ouvrir / rafraîchir l'inbox (étape SLO 2, cible 300 / 1 000) | 64 / 144 ms | **50 / 113 ms** | −22 % / −22 % |
| Marquer lu (étape 8) | 23 / 34 ms | 23 / 32 ms | iso (un seul message) |
| Ouvrir un message enrichi (étape 3) | 27 / 42 ms | 27 / 42 ms | iso — chemin `WithContent`, non touché |
| Télécharger une PJ (étape 7) | 29 / 725 ms | 29 / 708 ms | iso — la route lit `Content` légitimement |
| Fiche patient complète (étape 11) | 229 / 370 ms | 210 / 312 ms | −8 % / −16 % |
| Latence moyenne / p95 globales | 255 / 1 117 ms | 262 / 975 ms | p95 −13 % ; la moyenne porte la recherche (ci-dessous) |
| Erreurs | 0,012 % | 0,008 % (18 requêtes, famille IMAP `ObjectDisposedException`, identique) | |
| Actifs / sessions par h / absence | 92 / 0,60 / 97 min | 92 / 0,60 / 98 min | **iso-rythme confirmé** |

Le gain praticien est **réel mais plus petit que le gain serveur**, exactement comme l'audit du matin le prévoyait : la page d'en-têtes répond en 70 ms pour 97 ms de SQL restant, les requêtes tournent en parallèle de l'IMAP. Le médecin gagne un quart de seconde sur dix pages ; le serveur gagne 83 minutes de travail sur 3 heures.

### ❌ Recherche : 10/11 au SLO, et ce n'est pas la base

L'étape 5 « Recherche » sort de la grille au p95 (**35 336 ms** pour 2 000 ; p50 **271 ms**, identique au matin : 261). Attribution, par les traces et Prometheus :

- Une recherche de 42 s (trace `73cbf8f1…`) : 20:24:17,46 début ; **20:24:59,78** premier événement suivant — la requête vectorielle Postgres, dont les dix distances sont journalisées dans la **même milliseconde**. Les 42 s sont **avant** la base, dans la génération de l'embedding de la requête.
- `Failed to generate query embedding` (Warning, `SemanticSearchService`) sur plusieurs traces à la même minute.
- **p95 des appels sortants vers `api.openai.com` : 0,96 s le matin → 10 s le soir** (`http_client_request_duration`, borne haute du dernier bucket : saturé, donc « ≥ 10 s »), 6 379 appels tous en 200 — le fournisseur répondait, lentement, dès le **premier quart d'heure** (p95 serveur de la route `Search/semantic` à 41,6 s entre 17:30Z et 17:45Z, puis 36-39 s sur chaque tranche de 30 min).
- Les deux formes SQL de la recherche (`ILIKE` sur `Body`, `MailContents` / `MailMedicalDocuments`) coûtent **9,3 et 8,9 ms par appel**, identiques au matin ; les formes pgvector 2 à 3 ms.

**Conclusion** : dégradation d'une dépendance externe pendant tout le tir, sans rapport avec task-322 ni avec Postgres. Le verdict « recherche » de ce tir n'est pas opposable au produit ; les dix autres étapes le sont. Ce que le tir révèle en creux : la recherche sémantique **n'a pas de plafond de temps** propre — un fournisseur à 10 s par appel donne 42 s au praticien (retentatives comprises). Sujet connu (mémoire « OpenAI — un seul circuit pour chat et embeddings »), à instruire séparément.

## Ce que ce tir établit, et ce qu'il n'établit pas

**Établi.**
1. **task-322 rend ce qu'elle annonçait** : −60 % de temps SQL, −58 % de coût SQL par requête HTTP, la requête des pièces jointes supprimée de la charge, −28 % sur la page d'en-têtes ressentie, et un cache de pages Postgres qui cesse d'être saturé.
2. **Le poste restant est identifié et quantifié** : la requête des documents avec leur HTML porte 82 % du SQL restant (45,7 min, 97 ms/appel). C'est la US front proposée dans la PR (recharger le contenu à l'ouverture sur Blazor et la frise mobile, puis projeter côté serveur). Gain attendu : SQL par requête HTTP ~16 → ~3 ms.
3. **Iso-conditions tenues** : rythme, population, backends, login, erreurs identiques ; un seul facteur a varié.

**Non établi.**
1. **La part des index `MailId`** dans le gain : les tables font 150 à 250 lignes par praticien, le balayage coûtait 0,5 ms — l'index est une marge pour les boîtes anciennes, non mesurable ici.
2. **La recherche** : verdict rouge externe, à rejouer un jour où `api.openai.com` répond en moins d'une seconde — ou après un plafond de temps côté produit.
3. **Le gain à 5 000 inscrits** : extrapolé (le cgroup mémoire libéré est l'indice le plus fort), non mesuré.

## Axes proposés

1. **Merger la PR #246** (HAG) : le gain est mesuré, le contrat inchangé, aucune régression sur les dix étapes opposables.
2. **US front « contenu à l'ouverture »** (Blazor + frise mobile) puis projection serveur des corps : la moitié « documents » restante.
3. **Plafond de temps sur la génération d'embedding** (recherche sémantique) : borner, dégrader en recherche textuelle seule, ne jamais laisser 42 s au praticien pour un fournisseur lent.
4. **Rejouer `terrain` 2 000 inscrits** sur la branche mergée : avec la charge SQL divisée par 2,4 et le cache de pages libéré, la question « combien d'inscrits » change d'échelle.

## Réserves

- Harnais et code sur branche non mergée (PR #246) ; contrôle plan de la forge commité.
- Les deux tirs ont un cache de pages froid au départ, ce qui rend la comparaison honnête mais surestime légèrement les lectures disque des deux côtés par rapport à un régime établi.
- Les index de task-322 ont été créés **pendant la chauffe** du tir B (migration au premier accès de chaque base), hors fenêtre de verdict.
- Analyse Seq par échantillonnage (API sous session, MCP tronqué) ; les comptages Prometheus font foi.
