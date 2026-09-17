# Campagne de charge — palier 1000 sur population entièrement hydratée (2026-09-17)

> Tir `journey-1000-hydrate-20260917`, 19:46:02 → 23:17:13 (3 h 31 min 09).
> Code : `develop` à `2526f413` (task-315 mergée). Banc distant `192.168.1.69`.
> Source k6 : `Api/Mail/tests/loadtest-k6/reports/2026-09-17/journey-1000-hydrate-20260917-231713.json`
> Rapport harnais : `report-journey-1000-hydrate-20260917-231713.md`

## Ce que ce tir est

**Le premier tir 1000 de cette EPIC sur une population dont les 1 000 boîtes sont
réellement peuplées.** Tous les tirs 1000 antérieurs mesuraient, pour une part
qu'on ne savait pas chiffrer, une base vide — la chauffe s'y déclarait réussie sur
un code HTTP pendant que des centaines de médecins ne recevaient aucun document.
Le bouchage préalable (scénario `enrich` sur les boîtes 641-1000, 18 899 messages)
et la vérification boîte par boîte ont levé cette réserve.

**Conséquence : c'est le premier verdict 1000 opposable**, et il est sévère.

## Verdict — trois questions, trois réponses

### 1. SLO à 1000 sur base pleine : 4 étapes vertes sur 11

| # | Étape | p50 (cible) | p95 (cible) | Verdict |
|---|---|---|---|---|
| 1 | Arrivée dashboard | 157 (300) | 775 (1500) | OK |
| 2 | Ouvrir / rafraîchir l'inbox | 754 (300) | **30 532** (1000) | ECHEC |
| 3 | Ouvrir un message enrichi | 1 319 (100) | 2 415 (500) | ECHEC |
| 4 | Ouvrir un message froid | 787 (800) | 1 867 (2500) | OK |
| 5 | Recherche | 3 629 (500) | 5 296 (2000) | ECHEC |
| 6 | Envoi (acquittement UI) | 804 (1000) | 1 400 (3000) | OK |
| 7 | Télécharger une PJ | 2 236 (500) | 4 145 (2000) | ECHEC |
| 8 | Marquer lu | 575 (200) | 775 (1000) | ECHEC |
| 9 | Rechercher un patient | 122 (300) | 247 (1500) | OK |
| 10 | Page dossier patient | 7 364 (500) | 17 754 (2000) | ECHEC |
| 11 | Fiche patient complète | 17 568 (1500) | **33 455** (4000) | ECHEC |

À rapprocher de la contre-épreuve 500 sur base hydratée (10/11 vertes) : **le
passage de 500 à 1000 ne dégrade pas, il casse.**

### 2. Attribution de l'audit à 1000 : opposable, zéro perte

| Grandeur | Valeur |
|---|---|
| `mss_audit_traces_emitted_total` | 278 793 |
| `mss_audit_traces_persisted_total` | **278 793** |
| `mss_audit_traces_dropped_total` | (série absente) |
| Traces sur la fenêtre du tir | 237 697 |
| Tenants distincts porteurs de traces | **1 000 / 1 000** |
| Backends `mss-mail-audit` (max) | 5 |

Les comptes se recoupent avec k6 sans écart : `MailRead` 84 670 = 84 670 checks
`mark_read` ; `AttachmentDownload` 42 291 = 42 291 checks `attachment` ;
`MailSend` 31 727 vs 31 726. **Le journal en base commune (task-300/301) tient le
palier 1000 sans perte et pour un coût résident négligeable** — 5 backends directs.
C'est l'inverse du 2026-09-08, où task-186 avait perdu 1 477 traces.

### 3. Le vrai coût de la chauffe : le portillon, pas le débit serveur

- Chauffe **aboutie pour 100 % des 1 000 médecins** (plancher 90 %) — une première.
- Mais elle consomme **9 807 s au p95 sur 12 600 s, soit 78 %** de la fenêtre.
  Le régime ne porte le verdict que sur `[+10 346 s .. +12 630 s]`, soit 2 284 s.

**Ce chiffre tranche la question, et dans un sens qu'aucun tir précédent ne
pouvait établir.** La population était déjà hydratée : sur 118 270 UIDs demandés,
**106 130 (89,7 %) étaient déjà analysés** et court-circuitaient. Il n'y avait
donc quasiment rien à analyser — 12 018 messages réellement traités en 3 h 30.
Le temps n'est pas parti dans l'analyse, il est parti dans **l'attente de vague**.

> Le facteur limitant de la chauffe n'est pas le débit d'enrichissement du
> serveur : c'est le **portillon de concurrence** du harnais. C'est task-254.

## Comportement de task-315 en conditions nominales

Le tir de vérification du 17/09 (coupure Toxiproxy provoquée) avait prouvé que le
503 **part** quand la messagerie tombe. Ce tir prouve le versant complémentaire :
**il ne part pas quand tout va bien.**

| Grandeur (20 135 appels d'enrichissement) | Valeur |
|---|---|
| Demandés | 118 270 |
| Déjà analysés (court-circuit) | 106 130 |
| Analysés | 12 018 |
| **Injoignables** | **0** |
| Appels avec au moins un injoignable | **0** |
| Réponses 503 | **0** |

La comptabilité boucle exactement : 118 270 = 106 130 + 12 018 + 0. Aucun faux
positif, aucun bandeau intempestif. `MedicalDocumentProcess` en audit : 12 015,
cohérent avec les 12 018 analysés.

## La cause dominante — et elle n'est pas applicative

`read_list` pèse **74,4 % du temps serveur** (537 699 s), porté à 99 % par son
appel `emails` (page d'en-têtes, 25 UIDs) : p50 20 179 ms, p95 33 351 ms côté
client, p50 7 217 ms / p95 28 493 ms côté serveur.

Mais la télémétrie de l'hôte interdit d'en faire un finding applicatif :

| Signal | Valeur (fenêtre de régime) |
|---|---|
| **CPU total de l'hôte** | **moy 75,4 % — max 99,0 %** |
| dont VM Docker (`vmmemWSL`) | moy 687 % (≈ 6,9 cœurs) |
| dont 5 réplicas api-mail **cumulés** | ≈ 289 % (≈ 2,9 cœurs) |
| File du ThreadPool | moy 3,3 — max 72 (seuil 100) |
| `cl_waiting` PgBouncer | non nul sur **37 %** des relevés, max 2 488 |
| `maxwait` bases praticien | **3 436 ms** |
| Cache Postgres | 41 Go — cgroup à **100 %** |
| Fautes majeures cgroup | moy 5/s, max 88/s |
| Backends Postgres (pic) | 1 911 / 2 500 (76 %) |

**L'hôte est saturé, et ce n'est pas api-mail qui le sature** : les cinq réplicas
consomment 2,9 cœurs quand la VM Docker en consomme 6,9. Le ThreadPool n'est pas
affamé (72 < 100). En revanche `cl_waiting` cesse d'être nul pour la première fois
sur un tir 1000 — 37 % des relevés, avec 3,4 s d'attente au pire — et la mémoire
du cgroup Postgres est à 100 % avec 41 Go de cache.

> **Ces 20 s de page d'en-têtes ne sont pas attribuables à un défaut applicatif en
> l'état.** Elles sont mesurées sur un hôte qui tourne à 99 % de CPU crête et dont
> Postgres attend de la mémoire. La consigne de cette EPIC s'applique : un finding
> sans cause mesurée n'est pas un finding — cette EPIC a déjà payé une US écrite
> sur une cause supposée (task-222, annulée).

## Ce que le tir a aussi établi

**Les backends Postgres plafonnent, ils ne croissent pas indéfiniment.** Relevés :
979 (1 h 28) → 1 307 (1 h 59) → 1 614 (2 h 24) → 1 710 (2 h 34) → 1 900 (2 h 54) →
**1 859** (3 h 04) → 1 895 (3 h 13). La courbe s'infléchit d'elle-même vers 1 890 :
le recyclage (idle 600 s) finit par compenser la création. La lecture
« backends ∝ temps » de task-296 doit être amendée en **proportionnel jusqu'à un
palier**, atteint ici à 76 % de `max_connections`. Aucun refus `server_login_retry`,
login Postgres à 11 ms de p50 — la spirale `08P01` des campagnes précédentes ne
s'est pas produite.

## Analyse Seq (findings)

Fenêtre 17:46 → 21:18 UTC. Volume : **6 706 356** Information, **54 568** Warning,
**342** Error, **9** Fatal. **Zéro Debug** — le niveau de log de production tient
(task-203).

Taux d'erreur : 342 / 6,76 M = **0,005 %**. Côté k6 : 0,018 % des requêtes.

**Erreurs (342)** — toutes sur le chemin IMAP, aucune nouvelle famille :

| Message | n |
|---|---|
| `Error get email` | 148 |
| `Error retrieving attachment` | 42 |
| `Failed to connect to IMAP server for {Email}` | 39 |
| `HTTP … Status=…` | 38 |
| `Result-mapped …` | 33 |
| `[AppendToSentAsync] IMAP connection failed` | 11 |
| autres (13 familles) | 31 |

Les 39 `Failed to connect` correspondent exactement aux 39 `ConnectionError` du
journal d'audit et aux 39 checks `attachment` en échec : **la même panne comptée
trois fois par trois sous-systèmes indépendants, sans divergence.**

**Fatal (9)** : `Connection id "…" application never completed.` — Kestrel constate
une réponse jamais terminée. À rapprocher des 608 itérations interrompues à la
coupure du tir ; sans signal de corruption d'état par ailleurs.

**Warnings (54 568)** — dominés par trois familles structurelles, aucune n'est un
incident : certificat non approuvé accepté par configuration (22 235, attendu au
banc), valeurs manquantes au parsing CDA (21 227, qualité du corpus de test),
expiration de session IMAP (9 487, fonctionnement nominal du balayage).

À noter, non bloquant : `[PractitionerContactService] CONFLIT MÉTIER` ×3 —
un enrichissement de contact RPPS abandonné après rejeu, **apport perdu et
signalé**. Le message dit lui-même « jamais avalé » : c'est un cas connu et
instrumenté, pas une découverte, mais il vaut d'être compté.

## Axes proposés — à arbitrer

Aucune US n'est créée ici : le découpage et la priorité sont des décisions produit.

1. **Rejouer le palier 1000 sur un hôte non saturé.** C'est le préalable à tout
   finding applicatif sur la page d'en-têtes. En l'état, le verdict 4/11 mesure
   autant le poste que le produit. Sans cela, on risque une seconde task-222.
2. **task-254 — relever le portillon de concurrence de la chauffe.** Établi par ce
   tir : 78 % de la fenêtre consommée alors que 89,7 % du travail court-circuitait.
3. **`cl_waiting` non nul à 1000 (37 % des relevés, 3,4 s au pire).** Premier tir
   où le multiplexeur devient un facteur. Le levier `max_db_connections` 3 → 2
   reste non essayé.
4. **Mémoire Postgres : 41 Go de cache, cgroup à 100 %.** Le besoin réel dépasse
   les 34 Go mesurés par task-296 — la population pleine coûte plus cher que le
   modèle. Redimensionner avant le prochain 1000.
5. **La chauffe du banc se déclare réussie sur un code HTTP.** Corrigé de fait ici
   par le bouchage préalable, mais le défaut d'outillage demeure.

## Réserves

- **Pas de comparaison directe avec les tirs antérieurs à ce jour** : la population
  hydratée change la grandeur mesurée. Les chiffres de ce tir font référence pour
  les suivants, pas pour les précédents.
- **Le corpus est fileté** (`CORPUS_THREAD_SHARE=0.3`) : les chemins qui touchent
  au comptage de fils ne se comparent pas à un corpus sans fil.
- **`loadtest-600` reste vide et irréparable** (`uidNext` 613 > bande 611) : 1 boîte
  sur 1 000, effet négligeable, mais le tir n'a pas porté sur 1 000 boîtes pleines
  au sens strict.
- **Latence injectée 96 ms** pour un RTT cluster mesuré à 4,72 ms, iso-conditions
  avec le tir de référence du 2026-09-13.
