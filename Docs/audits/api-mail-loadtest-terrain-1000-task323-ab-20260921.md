# Campagne de charge — A/B task-323 : le HTML des documents hors des listes, tir `terrain` 1 000 inscrits (2026-09-21)

> Tir B' `terrain-1000-20260921-task323`, 19:50:31 → 22:51:41 à l'horloge du poste (3 h 01 min 10).
> Tir de référence : `terrain-1000-20260919-task322` du 2026-09-19 au soir, branche `feat/task-322-projection-entetes-index-mailid` à `a3b38e2f` — audit `api-mail-loadtest-terrain-1000-task322-ab-20260919.md`.
> Tir B' : branche `feat/task-323-doc-html-on-open` à `c98f38f9` (PR api-mail #247, **non mergée**), même harnais.
> Iso-conditions : même population (1 000 bases hydratées, **non purgées**), mêmes paramètres (247 messages par boîte, `UID_BASE=365`, corpus fileté 0,3, `SESSION_ROTATION=0.1`, chauffe hydratée, plan `1000:3h` + rampe 30 s = 10 830 s), banc mail cluster `192.168.1.69` avec le toxic de latence **déjà à 96 ms**, **tireur k6 sur le poste** (comme la référence), cache de pages **froid au départ dans les deux cas** (conteneur Postgres recréé à 18:53 puis à 19:47).
> Rapport : `Api/Mail/tests/loadtest-k6/reports/2026-09-21/report-terrain-1000-20260921-task323-225141.md`.

## Ce que ce tir est

**Un A/B à un seul facteur : le code de task-323** — le HTML et le corps d'un document
médical ne quittent plus la base pour dessiner une liste d'en-têtes ; ils ne circulent
que sur les chemins de contenu. La question posée : *qu'est-ce que cela rend, mesuré, et
où ?*

## Verdict — le constat qui fondait la US est vérifié, et le goulet s'est déplacé

### Serveur SQL (`pg_stat_statements` + compteurs serveur, fin − début)

| Grandeur | B (19/09, task-322) | **B' (21/09, task-323)** | Δ |
|---|---|---|---|
| Temps SQL cumulé sur 3 h | 55,7 min | **11,2 min** | **−80 %** |
| Coût SQL par requête HTTP (compteurs serveur) | 16,5 ms | **4,3 ms** | **−74 %** |
| Coût SQL par requête HTTP (somme des formes) | 15,3 ms | **3,0 ms** | −80 % |
| Backends actifs (équivalent) | 0,33 | **0,09** | **÷ 3,7** |
| **Requête « documents » de la page d'en-têtes** | **45,7 min (82,2 %), 97 ms/appel, 640 blocs, 28 228 appels** | **3,9 %, 0,91 ms/appel, 206 blocs, 29 009 appels** | **÷ 107 par appel** |
| Taux de cache (blocs) | 95,72 % | **97,89 %** | +2,2 pts |
| Lecture disque | 3,08 Mo/s (395 blocs/s) | **1,37 Mo/s (176 blocs/s)** | **−56 %** |
| Croissance des bases praticien | 302,6 Mo | 280,3 Mo | −7 % |
| Transactions / s | 461 | 472 | iso |
| Backends (échantillonneur, moy / max) | 226 / 670 | 231 / 669 | iso — suit la population |
| Login Postgres p50 / p95 | 6 / 7 ms | 6 / 7 ms | iso |
| Fichiers temporaires | 0 | 0 | iso |
| Refus PgBouncer `server_login_retry` | — | **0** | OK |

**La ligne qui porte la US.** La requête que le task file désignait — celle qui émettait
`SELECT … m."Body", m."HtmlBody" … FROM "MailMedicalDocuments" WHERE "MailId" = ANY($1)`
et pesait **82,2 % du temps SQL** — n'existe plus sous cette forme. La projection de
métadonnées qui la remplace coûte **0,91 ms par appel au lieu de 97** et touche **206
blocs au lieu de 640**, pour un nombre d'appels **identique** (29 009 contre 28 228). Le
détoastage des 222 Ko de HTML par document a disparu du chemin de liste, exactement comme
la US le prévoyait.

### Praticien (grille SLO, régime, p50 / p95)

| Geste | B (task-322) | **B' (task-323)** | Δ |
|---|---|---|---|
| **Ouvrir / rafraîchir l'inbox** (étape 2) | 50 / 113 ms | **30 / 59 ms** | **−40 % / −48 %** |
| **Page d'en-têtes** (`read_list`, appel `emails`, 25 en-têtes) | 69,9 / 110 ms | **36,6 / 54,1 ms** | **−48 % / −51 %** |
| Arrivée dashboard (étape 1) | 17 / 803 ms | 17 / 877 ms | p95 +9 % — voir « le goulet s'est déplacé » |
| Ouvrir un message enrichi (étape 3) | 27 / 42 ms | 28 / 42 ms | iso — chemin `WithContent`, non touché |
| Ouvrir un message froid (étape 4) | 436 / 507 ms | 453 / 588 ms | +4 % / +16 % |
| Télécharger une PJ (étape 7) | 29 / 708 ms | 28 / 424 ms | p95 −40 % |
| Marquer lu (étape 8) | 23 / 32 ms | 23 / 32 ms | iso |
| Fiche patient complète (étape 11) | 210 / 312 ms | 210 / 315 ms | **iso** |
| Recherche (étape 5) | 271 / 35 336 ms ❌ | 418 / 651 ms ✅ | **non attribuable — voir ci-dessous** |
| Latence moyenne / p95 globales | 261,8 / 974,8 ms | **131,4 / 561,7 ms** | **−50 % / −42 %** |
| Erreurs | 0,008 % | 0,008 % (19 req. sur 225 137) | iso |
| **Verdict SLO** | **10 / 11** | **11 / 11** | — |

**La fiche patient ne bouge pas (210 / 315 ms), et c'est le résultat attendu** : la frise
patient mobile était la seule consommatrice du HTML depuis la liste, et la US a déplacé ce
chargement à l'ouverture du document sans le supprimer. Le médecin ne paie pas le
déplacement.

## Trois réserves, à ne pas laisser passer dans un compte rendu

### 1. Le gain sur « Recherche » n'appartient PAS à task-323

La référence portait cette étape à un p95 de **35,3 s** — c'était la seule étape rouge, et
c'est la signature connue d'une dépendance OpenAI en défaut (circuit partagé chat /
embeddings, 429 `insufficient_quota` retenté). Ce tir compte **0 échec d'embedding** et
rend 651 ms. **Le passage de 10/11 à 11/11 tient donc à la santé d'un service externe, pas
au code de la US.** Le p50 de la recherche est d'ailleurs *plus lent* (271 → 418 ms).
Toute communication sur « SLO 11/11 » doit porter cette réserve.

### 2. Le goulet s'est déplacé vers le verrou de session IMAP

Le SQL n'étant plus le poste dominant, **l'arrivée dashboard devient 47,6 % du temps
serveur**. Cause **mesurée** (décomposition de trace + instrumentation task-214) :

- la route `GET /mail/folders/INBOX` a **deux populations** — 14 102 appels à 56 ms de
  moyenne, et **6 460 appels (31 %) à 773 ms**, qui portent 86 % du temps de l'étape ;
- sur une requête au p50 de la population lente (585 ms, `TraceId
  74d3c9ad82fa998c1f551751c83a1166`) : **442 ms d'attente du verrou `imap_session`**
  (76 % de la requête), 130 ms de re-validation IMAP, 13 ms de tout le reste ;
- généralisé par l'instrumentation : `ReadFolder` attend **1,546 s au p95**, pendant que
  `GetFolders` **retient le verrou jusqu'à 7,015 s en établissement de session**.

C'est une **file**, pas du travail. Remède candidat : sortir l'établissement de session de
la section critique. Gain attendu ~21 % du temps serveur. **Risque connu et déjà payé** :
task-270 a montré qu'allonger cette section critique fait payer les voisins de la session
jusqu'à ×19 pour un gain mécanique nul — toute US sur ce point doit être A/B au banc.

C'est le seul finding de ce tir qui mérite une US. **Proposé au PO, pas créé d'office.**

### 3. Deux inconnues annoncées par le task file le restent

- **La taille de la réponse HTTP de la page d'en-têtes n'est toujours pas mesurée** :
  `ResponseSize` vaut 0 dans le log et `data_received` de k6 n'est pas tagué par
  opération. Le gain de task-323 est établi **côté SQL et côté latence**, pas côté octets
  servis. C'est un manque d'**instrument**, à traiter avant de chiffrer le gain réseau.
- Le nombre d'allers-retours IMAP par requête n'est toujours pas compté : les 130 ms de
  re-validation sont *compatibles* avec un aller-retour sous 96 ms de latence injectée,
  ce n'est pas prouvé.

## Points de lecture secondaires

- **Part d'attente disque dans le temps SQL actif : 1,6 % → 17,3 %.** La part monte
  mécaniquement parce que le dénominateur s'est effondré (−80 %) ; le débit de lecture
  absolu, lui, **baisse de 56 %**. Ce n'est pas une régression.
- **cgroup mémoire du conteneur Postgres : 37/39 % → 51/65 %.** En hausse, avec **0 faute
  majeure**. Cause non établie — hypothèse : les pages utiles restent résidentes plus
  longtemps maintenant que les blobs ne traversent plus le cache. À surveiller au palier
  suivant, pas à interpréter ici.
- **Rapport lignes balayées / renvoyées : 9,3 → 16,3.** Les requêtes qui renvoyaient
  beaucoup de lignes ont disparu, les balayages sont restés : le rapport se dégrade sans
  qu'aucun balayage n'ait été ajouté.
- **`cl_waiting` non nul sur 1 % des relevés** (max 2 143, `maxwait` 8,6 ms) — **identique
  à la référence**, et toujours le contrat non tenu du multiplexeur.
- **Vérification par base : PASS** — 1 000 boîtes, 129 025 mails, **0 sujet étranger, 0
  sans marqueur**.
- **Erreurs** : 19 réponses 5xx, dont **17** de la famille résiduelle
  `ObjectDisposedException: ImapClient` à l'authentification (`ImapConnectionService.cs:291`,
  déjà instruite en `todo-task-324`, identique à la référence) et **2** produites dans la
  seconde de l'arrêt gracieux. Marqueurs de régression (`Failed to parse entity headers`,
  échecs d'embedding, 429, `08P01`) : **tous à zéro**.
- **Validité du tir** : 0 itération abandonnée, modèle fermé, 1 787 itérations, aucun
  signal d'auto-plafonnement du harnais.

## Conditions du banc — ce qui n'était pas iso

- La population a **vieilli de deux jours** depuis la référence (128 308 → 129 025 mails
  stockés, +0,6 %) et a subi entretemps le tir `journey` du 20/09. Effet jugé négligeable,
  mais mentionné : l'âge de la base fait partie des iso-conditions.
- Des conteneurs étrangers au banc tournaient sur l'hôte (~6 % de CPU au total, `ollama`
  en tête). Trop peu pour affamer le SUT ; relevé pour traçabilité.
- **Le lien réseau poste ↔ tireur k6bench n'a pas changé** (94,6 Mbit/s dans le sens des
  réponses, RTT 3 ms) — sans effet ici, le tir partant du poste comme sa référence.
- Un **faux départ** a eu lieu à 19:50:01 : `JOURNEY_STAGES` non posée, `setup()` en échec
  en 5 s, aucune charge appliquée. Seul effet : un `pg_stat_statements` remis à zéro, que
  le lancement réel a refait.

## Conclusion

**task-323 fait ce que son constat annonçait, et le fait entièrement.** Le temps SQL du
parcours praticien est divisé par 5, la requête qui pesait 82 % du SQL coûte 107 fois
moins par appel, la page d'en-têtes est deux fois plus rapide, et la fiche patient — le
seul écran qui dépendait du HTML de liste — ne paie rien. Le verdict SLO passe à 11/11, à
la réserve près que la recherche doit son vert à OpenAI et non à la US.

Le prochain plafond du parcours praticien n'est plus Postgres : c'est le **verrou de
session IMAP**, mesuré, chiffré, et à instruire en US.
