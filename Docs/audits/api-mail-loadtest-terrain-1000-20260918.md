# Campagne de charge — premier tir `terrain` : 1 000 praticiens inscrits (2026-09-18)

> Tir `terrain-1000-20260918`, 18:51:06 → 21:52:18 à l'horloge du poste (3 h 01 min 11).
> Harnais : branche `feat/task-321-scenario-terrain` (PR api-mail #245, non mergée).
> API : `develop` à `2526f413` (task-315 mergée). Banc distant `192.168.1.69`.
> Population : celle du 17/09, entièrement hydratée (bouchage 641-1000 + tir journey).
> Source k6 : `Api/Mail/tests/loadtest-k6/reports/2026-09-18/terrain-1000-20260918-215218.json`
> Rapport harnais : `report-terrain-1000-20260918-215218.md`

## Ce que ce tir est

**Le premier tir de la famille `terrain`** (task-321) : le parcours `journey` sous un
modèle de session — le praticien s'absente entre deux sessions de messagerie, la
population est hétérogène (occasionnel 30 %, régulier 50 %, intensif 20 %), et la
concurrence active **émerge** au lieu d'être fixée à 100 %. Même population, mêmes
gestes, même grille SLO que le tir `journey-1000-hydrate` de la veille : **seul le
rythme change**, et c'est précisément ce qu'on voulait isoler.

**Une ligne `terrain` ne se compare pas à une ligne `journey`.** Les deux tirs
mesurent la même application sur deux populations différentes : mille robots en
boucle hier, mille praticiens inscrits aujourd'hui. Les mettre côte à côte n'a de
sens que pour dire ce que le modèle change — pas pour dire que l'application a
progressé entre les deux (elle n'a pas bougé : même commit).

## Verdict — 1 000 praticiens inscrits, 93 actifs en moyenne : SLO tenu 11/11

| # | Étape | p50 (cible) | p95 (cible) | n | Verdict |
|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 19 (300) | 759 (1500) | 68 764 | OK |
| 2 | Ouvrir / rafraîchir l'inbox | 65 (300) | 158 (1000) | 34 376 | OK |
| 3 | Ouvrir un message enrichi | 29 (100) | 51 (500) | 17 187 | OK |
| 4 | Ouvrir un message froid | 436 (800) | 504 (2500) | 3 313 | OK |
| 5 | Recherche | 271 (500) | 351 (2000) | 5 073 | OK |
| 6 | Envoi (acquittement UI) | 839 (1000) | 944 (3000) | 5 044 | OK |
| 7 | Télécharger une PJ | 35 (500) | 757 (2000) | 6 931 | OK |
| 8 | Marquer lu | 25 (200) | 39 (1000) | 13 746 | OK |
| 9 | Rechercher un patient | 14 (300) | 22 (1500) | 4 092 | OK |
| 10 | Page dossier patient | 36 (500) | 68 (2000) | 4 994 | OK |
| 11 | Fiche patient complète | 229 (1500) | 370 (4000) | 2 497 | OK |

Toutes les étapes dépassent le plancher de 300 échantillons ; la fenêtre de régime
fait **2 h 56** (10 555 s). Erreurs : **13 requêtes sur 215 654 (0,006 %)**, zéro
429, aucune réserve épuisée.

Gardes système, toutes tenues : `cl_waiting` non nul sur **1 %** des relevés avec
un `maxwait` pire cas de **7 ms** (hier : 37 % et 3 436 ms) ; file ThreadPool
moy 0,2 / max 31 ; login Postgres p50 6 ms ; zéro refus `server_login_retry` ;
RSS par réplica 969 Mo en moyenne, plate.

## Le modèle a-t-il produit ce qu'il annonçait ?

C'est la question propre à un premier tir d'un nouveau scénario. Le rapport publie
le rythme **obtenu** face au rythme **attendu** du modèle :

| Grandeur | Obtenu | Attendu | Lecture |
|---|---|---|---|
| Praticiens actifs en moyenne | **93** | 85 | +9 % — voir le sens de l'écart ci-dessous |
| Sessions / praticien / h | 0,61 | 0,58 | conforme |
| Passages / praticien / h | 5,7 | 4,8 | +19 % : le serveur est rapide, une session contient plus de passages (9,3 par session) |
| Absence moyenne | 95 min | 135 min | **transitoire de démarrage**, voir ci-dessous |
| Sessions complètes | 1 790 | — | ~1,8 par praticien sur 3 h |

**L'écart sur l'absence est attendu et se calcule.** La première absence d'un VU est
tirée uniformément sur [0, moyenne] — espérance moyenne ÷ 2 — pour que les praticiens
n'arrivent pas tous à la seconde 0. Sur un tir de 3 h où chacun ne fait que ~1,8
session, cette première absence pèse **plus de la moitié** des absences observées.
En retirant les 1 000 premières absences (espérance ~68 min) des 1 790 relevées à
95 min de moyenne, les ~790 absences de régime valent **~129 min** — la valeur
attendue est 135. Le modèle est **calibré en régime** ; la moyenne publiée porte un
transitoire de démarrage qu'un tir plus long dilue. C'est aussi ce qui explique la
charge légèrement plus dense de la première heure (24,8 req/s à 44 min, 14,5 à
1 h 55, 20 à la fin).

Les +9 % d'actifs vont dans le sens que la section « Terrain » du rapport annonce
comme signature d'un serveur qui **ne** freine **pas** : plus de passages par
session (le serveur répond vite, le praticien fait plus de choses dans le même
temps), donc des sessions un peu plus pleines. À l'inverse d'hier, où 28 s de
chaque passage de 87 s étaient de l'attente serveur.

## Ce que le changement de rythme fait à la charge

| Grandeur | journey 1000 (17/09) | terrain 1000 (18/09) | Rapport |
|---|---|---|---|
| Praticiens actifs à un instant donné | 1 000 | **93** | ÷ 10,8 |
| Débit serveur en régime | 136 req/s | **19,3 req/s** | ÷ 7,0 |
| Passages / praticien / h | 41 | **5,7** | ÷ 7,2 |
| Backends Postgres (moy / max) | 1 127 / 1 911 | **231 / 669** | ÷ 4,9 / ÷ 2,9 |
| Sessions IMAP (moy / max) | 797 / 1 325 | **211 / 1 024** | ÷ 3,8 / — |
| CPU total de l'hôte (moy / max) | 75 % / 99 % | **18,6 % / 81 %** | ÷ 4 |
| CPU des 5 réplicas api-mail (cumul, moy) | 2,9 cœurs | **0,47 cœur** | ÷ 6 |
| `cl_waiting` non nul | 37 % des relevés, 3,4 s | **1 %, 7 ms** | — |
| Page d'en-têtes (`emails`) p50 / p95 | 20 179 / 33 351 ms | **103 / 176 ms** | ÷ 196 / ÷ 190 |

La dernière ligne est celle qui porte la leçon. **La page d'en-têtes n'a pas
changé d'un octet entre les deux tirs.** Hier elle coûtait 20 s parce que l'hôte
était à 99 % de CPU et Postgres à court de mémoire sous mille praticiens en boucle ;
aujourd'hui elle coûte 100 ms parce que 93 praticiens la demandent. Le « finding »
d'hier — 74 % du temps serveur — était bien une mesure de la saturation du poste,
comme l'audit du 17/09 le disait, et non d'un défaut applicatif.

**Réserve, à ne pas laisser passer** : le CPU de l'hôte a encore fait des **pointes
à 81 %**, portées par la VM Docker (`vmmemWSL` max 1 041 %). En moyenne le poste est
loin de la saturation (18,6 %) mais il n'est pas neutre. Et le cgroup mémoire de
Postgres reste à **100 %** avec 47,8 Go de cache — c'est le comportement normal
d'un cache de pages qui prend ce qu'on lui donne, avec des fautes majeures
retombées à 0 en moyenne (max 12/s, contre 88 hier).

## Chauffe hydratée : 245 s au lieu de 10 316 s

| | journey 17/09 | terrain 18/09 |
|---|---|---|
| Allocation de chauffe | 10 316 s (82 % du palier) | **245 s (2 %)** |
| Chauffe réelle (p95, attente de vague incluse) | 9 807 s | **233 s** |
| Fenêtre de régime portant le verdict | 2 284 s | **10 555 s** |
| Chauffe aboutie | 100 % | **100 %** |
| Messages réellement analysés | 12 018 | **210** |

Le mode hydraté fait ce qu'il annonce : la chauffe a **vérifié** l'hydratation en
4 minutes au lieu de la ré-allouer pendant 2 h 50 pour ne rien analyser. Le bilan
d'enrichissement de task-315 boucle : **101 190 demandés = 100 882 déjà analysés +
210 analysés + 0 injoignable**, sur 11 595 appels ; **0 réponse 503**. Les 210
messages analysés sont les lots du geste « traitement » du parcours (réserve
537-611), pas de la chauffe. Trois appels `getFolders` de chauffe ont échoué
(`warmup: HTTP 2xx — 997 ok / 3 ko`) : ce sont des listages de dossiers, pas des
lots d'analyse — la chauffe reste aboutie à 100 %, et ces trois échecs sont dans
les 11 `Failed to connect to IMAP server` du journal.

## Attribution de l'audit : exacte, à 1 000 tenants

| Grandeur | Valeur |
|---|---|
| `mss_audit_traces_emitted_total` | 40 799 |
| `mss_audit_traces_persisted_total` | **40 799** |
| Traces sur la fenêtre du tir | 40 796 |
| Tenants distincts | **1 000 / 1 000** |
| Backends `mss-mail-audit` (max) | 5 |

Recoupements avec k6, sans écart : `MailRead` 13 819 = 13 819 checks `mark_read` ;
`AttachmentDownload` 6 963 = 6 963 ; `MailSend` 5 062 = 5 062 ;
`MailboxSessionOpened` 2 320 pour 1 790 sessions complètes + 997 interrompues (une
session ouverte en fin de tir est comptée par l'audit, pas par k6 — cohérent).

## Analyse Seq (findings)

Fenêtre 16:51 → 19:53 UTC. **1 089 853** Information, **11 857** Warning,
**43** Error, **1** Fatal. Zéro Debug.

**Erreurs (44)** — une seule famille de cause, la connexion IMAP :
`Failed to connect to IMAP server` ×11, et leurs conséquences (`Error get email` ×3,
`AppendToSentAsync` ×1, `GetEmailContentAsync` ×1, `Error getting email UID` ×1,
un `Unhandled exception`), plus les 13 lignes HTTP et 12 `Result-mapped` qui les
comptent une seconde fois. **Le Fatal** est un `Connection id … application never
completed` — une réponse Kestrel jamais terminée à la coupure du tir, comme hier.
Aucune famille nouvelle, aucune erreur de base de données, aucune erreur de pooler.

**Warnings (11 857)** : certificat accepté par configuration (7 149, banc),
expirations de session IMAP (4 079, balayage nominal — le praticien s'absente, sa
session expire : c'est le modèle qui produit ce chiffre), valeurs manquantes CDA
(307), **verrous longs** `[ImapLock] Lock released (long)` ×280 — à noter : à 93
actifs, la détention longue du verrou de session existe encore sur certains gestes ;
sans effet sur le verdict (p95 tous verts), mais c'est la trace de ce que le modèle
`journey` amplifiait.

## Ce que ce tir établit, et ce qu'il n'établit pas

**Établi.**
1. Le scénario `terrain` fonctionne de bout en bout : budget accepté, chauffe
   hydratée courte, métriques publiées, verdict titré en inscrits et actifs, rythme
   obtenu confronté à l'attendu — et l'écart sur l'absence est **explicable par le
   modèle lui-même** (transitoire de la première absence).
2. **À 1 000 praticiens inscrits sous les hypothèses de profil de la US, la grille
   SLO est tenue 11/11**, avec des marges larges (page d'en-têtes à 158 ms de p95
   pour une cible de 1 000 ; fiche patient complète à 370 ms pour 4 000).
3. Le verdict 4/11 de la veille mesurait la saturation du poste sous un rythme
   irréaliste, pas l'application — confirmé par le même code, sur la même base, à
   un rythme plausible.

**Non établi — et à écrire en face de tout usage de ce chiffre.**
1. **Les profils sont des hypothèses.** 2 / 5 / 10 sessions par jour, 3 / 6 / 12
   minutes : construits par cohérence, jamais mesurés. Si les praticiens réels sont
   deux fois plus assidus, la charge double. La source de calibration est le journal
   d'audit en production (`audit_traces`) — pas ce tir.
2. **Le poste n'est pas neutre** : pointes CPU à 81 %, cgroup Postgres à 100 %.
   Le verdict est vert avec de la marge, mais la marge exacte reste inconnue tant
   que le générateur de charge et Postgres partagent l'hôte avec le système mesuré.
3. **La concurrence active de 93 est une moyenne.** Le pic n'est pas publié
   (k6 ne porte pas de jauge partagée entre VUs) ; l'échantillonneur donne une
   borne haute par les bases praticien touchées sur 10 min : 86 à 135.
4. **3 h, c'est court pour un modèle à absences de 135 min** : 1,8 session par
   praticien, transitoire de démarrage visible dans la moyenne d'absence. Un tir de
   6 h ou une journée de 4 h (`TERRAIN_DAY_HOURS=4`, qui comprime la journée sans
   toucher aux gestes) donnerait des moyennes de régime plus propres.

## Axes proposés — à arbitrer

Aucune US n'est créée ici.

1. **Calibrer les profils sur `audit_traces` dès que l'audit tourne en production**
   — c'est la seule action qui transforme ce verdict en verdict terrain. La forme de
   `TERRAIN_PROFILES` est prête à recevoir les distributions observées.
2. **Rejouer `terrain` à 2 000 puis 5 000 inscrits.** Sous ces hypothèses, 5 000
   inscrits font ~465 actifs — l'ordre de grandeur du palier 500 de `journey`, que
   l'application tenait à 10/11. C'est la question « combien d'inscrits peut-on
   servir ? » posée pour de vrai, et le premier tir où le nombre de **bases**
   (5 000) et non le nombre d'actifs deviendra le facteur limitant côté Postgres.
3. **Sortir k6 du poste** — inchangé depuis hier, et plus urgent si l'on monte à
   5 000 : les pointes à 81 % sont déjà là.
4. **Les 280 détentions longues du verrou de session** à 93 actifs : sans effet sur
   la grille, mais un indice que les gestes concernés ne sont pas indépendants les
   uns des autres au sein d'une même session. À instrumenter avant d'y toucher
   (même consigne que pour la page d'en-têtes : pas de US sur une cause supposée).
5. **Publier le pic de concurrence active**, pas seulement la moyenne : dérivable
   côté rapport depuis les séries Prometheus de `terrain_session_seconds` par
   fenêtre glissante, ou depuis `MailboxSessionOpened` de l'audit. C'est ce qui
   manque pour dimensionner un pooler ou un plafond de sessions IMAP.

## Réserves

- Harnais sur branche non mergée (PR #245) ; API sur `develop`. Le rapport est
  reproductible dès le merge.
- Corpus fileté (`CORPUS_THREAD_SHARE=0.3`) ; latence injectée 96 ms pour un RTT
  cluster de 4,7 ms ; `UID_BASE=365`, `MESSAGES_PER_USER=247` — iso-conditions avec
  les tirs des 13 et 17/09.
- `loadtest-600` toujours vide (irréparable) : 1 inscrit sur 1 000.
- Horloge du poste décalée (le tir est daté 18:51-21:52 alors qu'il a couru de nuit) :
  toutes les fenêtres de ce document sont exprimées dans l'horloge du poste, et les
  requêtes Seq en UTC correspondant (16:51 → 19:53 Z).
