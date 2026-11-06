# Rapport de tir — journey-controle-20-40-task424

> Banc de charge api-mail (EPIC E015). Source k6 : `journey-controle-20-40-task424-101303.json`.

## 🟠 ORANGE — tir réussi, avec des points à instruire

Le tir s'est déroulé correctement et ses chiffres sont exploitables. Il met en évidence des points qui méritent d'être traités — ce sont des pistes de travail, pas des incidents.

- ce tir tourne au **rythme accéléré** : il désigne des goulets mais ne certifie aucun palier (seul le rythme réel d'un humain le fait)
- 5 traitement(s) sont candidats à l'optimisation (voir « Axes d'amélioration »)

## Contexte

- **Scénario** : journey
- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).
- **Utilisateurs** : 1996 — **VUs** : 40 — **Durée** : 420s — **Latence** : mssante
- **Requêtes** : 23114 — **débit émergent global** : 51.9 req/s (émergent, jamais un objectif — le détail par palier est dans la table du genou)

## Corpus — fils de discussion

- **Part de messages en fil** : 30.0 % (déclarée au tir, telle que semée par `--thread-share`)
- **Taille moyenne d'un fil** : 3 messages — **déduite** de la part, non mesurée (les longueurs de fil dérivent de la part dans le générateur du seed)

> ⚠️ **Rupture de comparabilité.** Ce tir porte sur un corpus **fileté** ; les campagnes antérieures portaient sur un corpus **sans fil**. Les chiffres des chemins qui touchent au comptage de fils ne se comparent **pas** d'un corpus à l'autre — ils mesurent deux choses différentes.

## Validité du tir

> ⓘ Scénario `journey` — **modèle fermé** (1 VU = 1 médecin) : la charge est émergente, k6 n'abandonne pas d'itérations faute de VU et `vus == vus_max` est la définition du palier, pas un symptôme. Le `TIR INVALIDE` du modèle ouvert n'existe pas **par construction** ; les contrôles ci-dessous restent affichés pour la traçabilité.

| Contrôle | Valeur | Seuil |
|---|---|---|
| Itérations abandonnées (`dropped_iterations`) | 0 (**0.0 %**) | < 1.0 % |
| Itérations exécutées | 1688 | — |
| Pic de VUs / plafond (`vus` / `vus_max`) | 40 / 40 | pic < plafond |
| Pool de VUs saturé | sans objet (modèle fermé) | non |

> ⓘ Tir antérieur à la ventilation par scénario (task-203), et sans plan de scénario fini déclaré (`context.enrichPlan`) : le compteur global est utilisé tel quel, faute de quoi retrancher. S'il a tourné un `shared-iterations` coupé par son `maxDuration`, son reliquat est compté ici comme un abandon — à ne pas confondre avec de la famine de VUs (~0,5 point à 200 praticiens sur 5 min, ~1,1 sur un palier de 3 min).

✅ Aucun signal d'auto-plafonnement du harnais : **tir exploitable** pour une conclusion de capacité.

## KPI synthèse (comparable entre tirs)

| Users | VUs | Scénario | Débit plateau | Débit k6 | Latence moy. (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Erreurs % | Checks % | 429 | Mélange | Stockés/attendus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1996 | 40 | journey | — | 51.9 | **72.8** | 25.9 | **424.1** | — | 2942.0 | 0.00 | 100.0 | 0 | 0 | 5670/— |

> Latence moyenne et p95 sont les deux repères à comparer d'un tir à l'autre : une hausse marquée à volume croissant (ex. 10 → 50 users) signale une dégradation. Le **débit** ne se compare qu'entre tirs valides (voir ci-dessus).

## Table du genou — population × latence par étape

> ⚠️ **Baseline changée depuis le 2026-08-03** — ne pas comparer ces chiffres à ceux de cette campagne. Deux raisons cumulées : l'étape 3 y mesurait des messages **jamais analysés** (défaut 5 de task-224, corrigé depuis), et le mélange du parcours a changé (task-226 : « supprimer » retiré, chaîne traitement → lecture → dossier patient ajoutée). Les paliers de ce tir se comparent entre eux, et aux tirs postérieurs à task-226.

> Modèle **fermé** (1 VU = 1 médecin) : le débit est **émergent** — il documente ce que N médecins produisent à leur rythme, il ne se compare jamais au « débit plateau » de la famille `mixed` (modèles différents, voir `reports/INDEX.md`). Le genou se lit sur la dérive des p95 par étape quand N monte.

| Palier | Fenêtre du palier (s) | dont régime (s) | Requêtes (régime) | Débit émergent (req/s, régime) | Erreurs % | PJ téléchargées (Mo) |
|---|---|---|---|---|---|---|
| **20 médecins** | 180 | 131 | 4918 | 37.54 | 0.00 | 17.4 |
| **40 médecins** | 180 | 131 | 10035 | 76.60 | 0.00 | 39.3 |

> task-321 — le débit émergent divise les requêtes du palier par sa fenêtre de **régime** (chauffe exclue) : aucune requête taguée `palier:N` n'a lieu pendant l'allocation de chauffe, donc la fenêtre entière sous-estimait le débit — d'un facteur 5,5 au tir du 2026-09-17.

### Latence par étape × palier (ms, p50 / p95, n échantillons)

| # | Étape | 20 médecins | 40 médecins |
|---|---|---|---|
| 1 | Arrivée dashboard | 15 / 428 (n=1456) | 16 / 425 (n=3004) |
| 2 | Ouvrir / rafraîchir l'inbox | 33 / 114 (n=724) | 35 / 120 (n=1504) |
| 3 | Ouvrir un message enrichi (servi base) | 27 / 36 (n=361) | 29 / 39 (n=749) |
| 4 | Ouvrir un message froid (fetch IMAP) | 426 / 482 (n=136) | 430 / 477 (n=277) |
| 5 | Recherche | 271 / 487 (n=104) | 267 / 483 (n=214) |
| 6 | Envoi (acquittement UI) | 427 / 843 (n=114) | 425 / 858 (n=208) |
| 7 | Télécharger une PJ (~124 Ko) | 29 / 42 (n=146) | 31 / 671 (n=284) |
| 8 | Marquer lu | 24 / 29 (n=297) | 26 / 33 (n=607) |
| 9 | Rechercher un patient | 14 / 18 (n=105) | 14 / 21 (n=207) |
| 10 | Ouvrir la page d'un dossier patient | 39 / 62 (n=164) | 39 / 64 (n=336) |
| 11 | Fiche patient complète (ressenti médecin) | 172 / 241 (n=82) | 173 / 260 (n=168) |

> La transition entre paliers (rampes) est taguée `palier:transition` et n'entre dans aucune colonne : un percentile de palier ne contient que sa fenêtre stabilisée.

## Dossier patient — la rafale, le dossier, l'analyse

> Le **traitement** (analyse CDA) n'est pas un geste du médecin : il n'a aucune ligne dans la grille SLO. Il est **publié, jamais jugé** — c'est lui qui constitue le dossier, et sa part du passage est ce qui décidera, sur mesure, s'il faut le sortir du passage vers un travailleur de plateforme.

| Palier | Largeur de rafale (moy/max) | Taille du dossier (moy/max) | Messages analysés | Fiche complète p95 (ms) |
|---|---|---|---|---|
| **20 médecins** | 14.7 / 20 | 34.5 / 58 | 204 | 241 |
| **40 médecins** | 14.7 / 20 | 33.9 / 60 | 364 | 260 |

> **Lecture.** La page du client réel est plafonnée à **20** documents : la largeur de rafale sature à cette valeur dès que le dossier la dépasse. Le couple à surveiller est donc « rafale plate / dossier qui croît » — c'est le coût d'une page qui ne grandit pas dans un dossier qui grandit.

- **Documents sans INS** : 50 — ils n'entrent dans **aucun** dossier et attendent un rattachement manuel. C'est le comportement **attendu** du produit (identito-vigilance : pas de rattachement deviné), ~6 % du corpus de test : **jamais une erreur**.
- **Coût de la chauffe** : 440 appels d'analyse, ~43120 messages analysés, 136 ms en moyenne, 2942 ms au pire — soit **0.0 % de la durée du tir** (les appels sont concurrents : la part se lit sur un appel, pas sur leur somme). Au-delà de quelques pourcents, étaler la chauffe ou réduire la réserve analysée.
- **Chauffe en mode population hydratée** (`JOURNEY_WARMUP_HYDRATED=1`, task-321) : allocation et vagues dérivées du coût du court-circuit, pas du plafond d'analyse — la chauffe a **vérifié** l'hydratation, elle ne l'a pas produite. Un taux d'aboutissement < 100 % signalerait ici une boîte que le bouchage préalable a manquée.

## Coûts résidents contre N

> Sessions IMAP, backends Postgres et RSS suivent la **population**, pas le débit : c'est eux qui plafonnent une montée en N. Attendu : sessions IMAP ≈ N × réplicas, `cl_waiting` = 0 soutenu, RSS plate sur la fenêtre.

⚠️ **aucun point d'échantillonneur repliable par palier** — CSV `observe-*.csv` absent, fenêtre du tir absente du JSON k6, ou calendrier des paliers non déclaré. Relancer avec `observe.sh` armé (voir `docs/loadtest.md` § 4c) pour que cette table existe.

## Verdict SLO — grille `docs/SLO-parcours-medecin.md`

⚠️ **Verdict non opposable — K=10.** Seul un tir en mode validation (`JOURNEY_TIME_COMPRESSION=1`) certifie un palier : un tir comprimé exerce les mêmes chemins de code et **désigne les goulets**, mais ses latences contiennent l'artefact de compression. Relancer à K=1, fenêtre ≥ 30 min, pour un verdict.

✅ **Chauffe aboutie à chaque palier mesuré** (planchers : 90 % de chauffe par cohorte, 95 % d'ouvertures de l'étape 3 servies par la base) : la base servant les étapes 2, 3, 10, 11 est peuplée, la chauffe ne retire aucun verdict.

- palier 20 : cohorte 20 chauffée à 100.0 % (sur 20) ; étape 3 servie par la base à 99.2 % (sur 361)
- palier 40 : cohorte 40 chauffée à 100.0 % (sur 20) ; étape 3 servie par la base à 99.2 % (sur 749)

## Axes d'amélioration — où part le temps serveur

> **Ce classement ne répond pas à la même question que le verdict SLO.** Le SLO dit si le médecin attend trop ; ceci dit **où part le temps serveur**, et les deux ne désignent pas les mêmes traitements. La grandeur est `appels × durée moyenne` sur le palier **40**, valable à tout K (la compression change le débit, pas le mélange des gestes).

| État | Traitement | Appels | Moy (ms) | p95 (ms) | Total (s) | Part |
|---|---|---|---|---|---|---|
| 🟠 | Arrivée dashboard (`dashboard`) | 3004 | 63 | 425 | 189.4 | 30.6 % |
| 🟠 | Ouvrir un message froid (fetch IMAP) (`read_content_cold`) | 277 | 431 | 477 | 119.3 | 19.3 % |
| 🟠 | Envoi (acquittement UI) (`send`) | 208 | 470 | 858 | 97.9 | 15.8 % |
| 🟢 | Recherche (`search`) | 214 | 313 | 483 | 67.0 | 10.8 % |
| 🟠 | Ouvrir / rafraîchir l'inbox (`read_list`) | 1504 | 39 | 120 | 59.0 | 9.5 % |
| 🟠 | Télécharger une PJ (~124 Ko) (`attachment`) | 284 | 104 | 671 | 29.4 | 4.8 % |
| 🟢 | Ouvrir un message enrichi (servi base) (`read_content`) | 749 | 30 | 39 | 22.2 | 3.6 % |
| 🟢 | Marquer lu (`mark_read`) | 607 | 27 | 33 | 16.3 | 2.6 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_dossier`) | 168 | 40 | 64 | 6.7 | 1.1 % |
| 🟢 | Traitement (plateforme) (`treatment`) | 182 | 35 | 44 | 6.4 | 1.0 % |
| 🟢 | Rechercher un patient (`patient_search`) | 207 | 15 | 21 | 3.1 | 0.5 % |
| 🟢 | Ouvrir la page d'un dossier patient (`patient_opposition`) | 168 | 15 | 18 | 2.5 | 0.4 % |

> **Lecture de l'état.** 🔴 le médecin attend trop **et** le traitement pèse (hors grille **cumulé** à un gros volume de temps serveur ou à un coût par appel élevé) — c'est la **conjonction** qui fait le rouge. 🟠 au moins un signal, à instruire sans urgence. 🟢 aucun signal — dire d'un traitement qu'il n'a rien à se reprocher est une information, pas un blanc.

**Bilan : 0 🔴 · 5 🟠 · 7 🟢** sur 12 traitements mesurés.

### Candidats signalés par les chiffres

- **Arrivée dashboard** (`dashboard`, 189.4 s, 30.6 %)
  - **vert au SLO mais gros consommateur** — invisible d'un rapport qui ne lit que les percentiles
  - **dispersion p95/p50 = 26.3×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Ouvrir un message froid (fetch IMAP)** (`read_content_cold`, 119.3 s, 19.3 %)
  - **vert au SLO mais gros consommateur** — invisible d'un rapport qui ne lit que les percentiles
- **Envoi (acquittement UI)** (`send`, 97.9 s, 15.8 %)
  - **vert au SLO mais gros consommateur** — invisible d'un rapport qui ne lit que les percentiles
- **Ouvrir / rafraîchir l'inbox** (`read_list`, 59.0 s, 9.5 %)
  - **dispersion p95/p50 = 3.4×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe
- **Télécharger une PJ (~124 Ko)** (`attachment`, 29.4 s, 4.8 %)
  - **dispersion p95/p50 = 21.7×** — coût qui dépend de la charge ou de la donnée, pas un coût fixe

> ⚠️ **Ces signaux ne sont PAS des causes.** Un traitement lourd peut l'être par volume d'appels, par requête SQL, par aller-retour réseau ou par verrou — et le remède diffère du tout au tout. Établir la cause par la télémétrie (§ « Télémétrie fine ») **avant** de proposer un correctif : cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

### Findings d'optimisation (À COMPLÉTER par l'analyse)

_Pour chaque candidat ci-dessus : la cause établie par la télémétrie, le remède envisagé (mise en cache, algorithme, requête SQL, regroupement d'appels), le gain attendu en temps serveur, et le risque. **Un finding sans cause mesurée n'est pas un finding.**_

_**Puis proposer à l'humain de créer une task `/po`** pour tout finding significatif — un candidat qui pèse plus de 15 % du temps serveur, ou qui sort de la grille, mérite une US. Proposer, jamais créer d'office : le découpage et la priorité sont des décisions produit._

## Ventilation des étapes multi-appels

> Une étape du parcours est un **geste** du médecin, pas une requête : l'inbox en émet deux, l'arrivée dashboard en émet quatre. L'étape reste l'unité de jugement — le médecin attend la **somme** de ses appels, et c'est elle que la grille SLO et `reports/INDEX.md` publient sous `op`. Cette table est un **supplément de diagnostic** : elle dit **lequel** des appels porte le coût. Les étapes qui n'émettent qu'un appel n'y figurent pas — leur ligne de grille **est** déjà leur appel.

| Palier | # | Étape | Appel | n | p50 (ms) | p95 (ms) | Total (s) |
|---|---|---|---|---|---|---|---|
| 20 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 364 | 113 | 485 | 73.2 |
| 20 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 364 | 14 | 17 | 5.2 |
| 20 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 364 | 17 | 21 | 6.3 |
| 20 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 364 | 13 | 15 | 4.7 |
| 20 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 362 | 15 | 131 | 12.8 |
| 20 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 362 | 35 | 44 | 13.1 |
| 40 | 1 | Arrivée dashboard (`dashboard`) | `folder` — Dossier de l'inbox (`GET /mail/folders/{folder}`) | 751 | 116 | 494 | 142.0 |
| 40 | 1 | Arrivée dashboard (`dashboard`) | `today` — Compteur du jour (`…/emails/today`) | 751 | 15 | 20 | 19.9 |
| 40 | 1 | Arrivée dashboard (`dashboard`) | `folders` — Liste des dossiers (`GET /mail/folders`) | 751 | 18 | 25 | 17.0 |
| 40 | 1 | Arrivée dashboard (`dashboard`) | `coverage` — Couverture de synchro (`GET /sync/coverage`) | 751 | 14 | 18 | 10.5 |
| 40 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `folder` — Dossier + liste d'UIDs (`GET /mail/folders/{folder}`) | 752 | 16 | 133 | 29.9 |
| 40 | 2 | Ouvrir / rafraîchir l'inbox (`read_list`) | `emails` — Page d'en-têtes (`…/emails/{ids}`) | 752 | 38 | 48 | 29.2 |

### Qui porte le coût — palier 40 médecins

- **Arrivée dashboard** (`dashboard`, palier 40) — le p95 de l'étape est porté par l'appel **`folder`** (494 ms de p95, 116 ms de p50, n=751), qui porte **aussi** le temps serveur de l'étape (142.0 s, 75 %).
- **Ouvrir / rafraîchir l'inbox** (`read_list`, palier 40) — le p95 de l'étape est porté par l'appel **`folder`** (133 ms de p95, 16 ms de p50, n=752), qui porte **aussi** le temps serveur de l'étape (29.9 s, 51 %).

> Ces phrases **attribuent**, elles n'expliquent pas. Pourquoi l'appel désigné coûte — requête SQL, aller-retour IMAP, verrou, volume de données — s'établit par la télémétrie (§ « Télémétrie fine »). Cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222, annulée).

## Latence par opération (ms)

| Opération | n | avg | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| attachment | 662 | 85.5 | 30.2 | 343.9 | 614.3 | 1008.3 |
| attachment,palier:20 | 146 | 52.2 | 28.7 | 36.0 | 42.1 | 727.0 |
| attachment,palier:40 | 284 | 103.6 | 31.0 | 392.3 | 671.4 | 806.9 |
| attachment,palier:transition | 76 | 118.6 | 31.6 | 478.8 | 667.2 | 1008.3 |
| dashboard | 6752 | 66.2 | 15.9 | 138.8 | 430.0 | 1160.5 |
| dashboard,call:coverage,palier:20 | 364 | 12.9 | 12.6 | 14.9 | 15.4 | 19.8 |
| dashboard,call:coverage,palier:40 | 751 | 14.0 | 13.5 | 16.6 | 17.9 | 27.4 |
| dashboard,call:coverage,palier:transition | 165 | 16.2 | 14.4 | 20.0 | 25.1 | 63.1 |
| dashboard,call:folder,palier:20 | 364 | 201.2 | 112.5 | 452.2 | 485.1 | 1160.5 |
| dashboard,call:folder,palier:40 | 751 | 189.1 | 116.2 | 453.4 | 493.7 | 1037.6 |
| dashboard,call:folder,palier:transition | 165 | 244.9 | 140.4 | 458.7 | 496.8 | 747.8 |
| dashboard,call:folders,palier:20 | 364 | 17.3 | 17.1 | 19.7 | 20.9 | 28.8 |
| dashboard,call:folders,palier:40 | 751 | 22.6 | 18.0 | 22.3 | 25.3 | 454.9 |
| dashboard,call:folders,palier:transition | 165 | 19.0 | 18.5 | 22.2 | 25.0 | 30.0 |
| dashboard,call:today,palier:20 | 364 | 14.3 | 14.1 | 16.1 | 17.0 | 25.5 |
| dashboard,call:today,palier:40 | 751 | 26.4 | 14.9 | 18.2 | 19.9 | 473.8 |
| dashboard,call:today,palier:transition | 165 | 112.9 | 15.8 | 439.9 | 468.3 | 498.8 |
| dashboard,palier:20 | 1456 | 61.4 | 15.1 | 126.6 | 428.4 | 1160.5 |
| dashboard,palier:40 | 3004 | 63.0 | 16.2 | 136.1 | 425.4 | 1037.6 |
| dashboard,palier:transition | 660 | 98.2 | 17.3 | 422.0 | 451.3 | 747.8 |
| mark_read | 1368 | 26.3 | 25.0 | 30.1 | 32.8 | 156.7 |
| mark_read,palier:20 | 297 | 24.1 | 23.6 | 27.2 | 29.1 | 42.7 |
| mark_read,palier:40 | 607 | 26.9 | 26.1 | 31.4 | 33.2 | 47.6 |
| mark_read,palier:transition | 126 | 32.7 | 25.7 | 35.3 | 77.7 | 156.7 |
| patient_docs | 5530 | 30.6 | 28.5 | 52.8 | 58.6 | 316.9 |
| patient_docs,palier:20 | 1209 | 27.8 | 24.3 | 47.7 | 51.9 | 71.7 |
| patient_docs,palier:40 | 2463 | 27.8 | 21.0 | 47.9 | 55.5 | 74.8 |
| patient_docs,palier:transition | 587 | 40.0 | 37.3 | 64.0 | 73.9 | 316.9 |
| patient_dossier | 376 | 42.8 | 40.0 | 63.7 | 74.6 | 177.6 |
| patient_dossier,palier:20 | 82 | 39.6 | 39.2 | 58.5 | 61.7 | 74.2 |
| patient_dossier,palier:40 | 168 | 39.6 | 38.6 | 56.7 | 63.7 | 84.1 |
| patient_dossier,palier:transition | 37 | 59.1 | 51.3 | 101.7 | 146.7 | 177.6 |
| patient_opposition | 376 | 14.4 | 14.0 | 16.6 | 18.2 | 27.2 |
| patient_opposition,palier:20 | 82 | 13.8 | 13.3 | 16.0 | 17.1 | 17.9 |
| patient_opposition,palier:40 | 168 | 14.7 | 14.3 | 16.5 | 18.1 | 27.2 |
| patient_opposition,palier:transition | 37 | 15.7 | 14.4 | 20.3 | 23.9 | 26.9 |
| patient_search | 480 | 14.7 | 14.0 | 17.2 | 19.6 | 46.1 |
| patient_search,palier:20 | 105 | 14.1 | 13.6 | 16.4 | 17.7 | 22.2 |
| patient_search,palier:40 | 207 | 14.8 | 14.2 | 17.3 | 20.8 | 28.9 |
| patient_search,palier:transition | 43 | 17.6 | 15.0 | 25.9 | 35.5 | 46.1 |
| read_content | 1688 | 29.3 | 28.3 | 35.2 | 38.2 | 192.2 |
| read_content,palier:20 | 361 | 27.7 | 27.3 | 32.7 | 35.8 | 64.0 |
| read_content,palier:40 | 749 | 29.6 | 28.8 | 35.9 | 39.3 | 59.4 |
| read_content,palier:transition | 164 | 34.0 | 29.6 | 40.6 | 43.5 | 192.2 |
| read_content_cold | 638 | 433.2 | 429.9 | 470.2 | 480.5 | 1082.1 |
| read_content_cold,palier:20 | 136 | 430.8 | 426.3 | 467.2 | 482.5 | 1035.2 |
| read_content_cold,palier:40 | 277 | 430.6 | 429.8 | 468.1 | 476.7 | 524.5 |
| read_content_cold,palier:transition | 75 | 431.5 | 431.5 | 470.2 | 479.3 | 503.3 |
| read_list | 3376 | 37.9 | 34.5 | 93.6 | 119.3 | 487.5 |
| read_list,call:emails,palier:20 | 362 | 36.2 | 35.5 | 41.3 | 43.6 | 61.8 |
| read_list,call:emails,palier:40 | 752 | 38.8 | 37.6 | 45.0 | 48.2 | 71.4 |
| read_list,call:emails,palier:transition | 165 | 43.5 | 40.0 | 51.8 | 62.1 | 120.9 |
| read_list,call:folder,palier:20 | 362 | 35.3 | 15.2 | 114.3 | 131.3 | 141.3 |
| read_list,call:folder,palier:40 | 752 | 39.7 | 15.9 | 120.3 | 133.0 | 487.5 |
| read_list,call:folder,palier:transition | 165 | 34.6 | 16.5 | 117.4 | 130.2 | 142.6 |
| read_list,palier:20 | 724 | 35.8 | 33.2 | 59.8 | 114.3 | 141.3 |
| read_list,palier:40 | 1504 | 39.3 | 35.1 | 96.8 | 120.3 | 487.5 |
| read_list,palier:transition | 330 | 39.0 | 35.2 | 96.1 | 119.6 | 142.6 |
| search | 490 | 318.2 | 270.6 | 400.5 | 515.5 | 1415.4 |
| search,palier:20 | 104 | 331.9 | 271.3 | 404.8 | 486.6 | 1415.4 |
| search,palier:40 | 214 | 313.2 | 266.8 | 382.4 | 483.0 | 1382.9 |
| search,palier:transition | 45 | 363.4 | 295.3 | 572.7 | 611.6 | 980.5 |
| send | 506 | 499.6 | 428.7 | 838.4 | 860.9 | 1013.1 |
| send,palier:20 | 114 | 475.3 | 426.9 | 796.4 | 842.5 | 902.1 |
| send,palier:40 | 208 | 470.5 | 424.6 | 801.8 | 858.3 | 903.5 |
| send,palier:transition | 61 | 530.4 | 430.9 | 861.1 | 915.7 | 954.7 |
| treatment | 418 | 34.5 | 33.6 | 39.3 | 42.8 | 58.3 |
| treatment,palier:20 | 102 | 33.7 | 32.8 | 36.8 | 42.9 | 58.3 |
| treatment,palier:40 | 182 | 35.0 | 34.3 | 39.5 | 43.5 | 50.3 |
| treatment,palier:transition | 44 | 34.9 | 34.2 | 39.5 | 40.1 | 45.8 |
| warmup | 440 | 136.2 | 38.6 | 419.4 | 815.7 | 2942.0 |

## Ressources & télémétrie

| Source | État |
|---|---|
| Fenêtre du tir (UTC) | 2026-11-06T09:05:38.001000+00:00 → 2026-11-06T09:13:03.433000+00:00 (445 s) |
| Prometheus (`http://127.0.0.1:9090`) | ✅ interrogé |
| Échantillonneur (`observe-*.csv`) | ⚠️ **absent** — hôte, k6 et conteneurs non mesurés (voir `tests/loadtest-k6/observe.sh`) |
| Collector OTLP du banc | ✅ aucun rejet |

### Par réplica api-mail

| Réplica | CPU (cœurs) | File ThreadPool (max) | Threads (max) | Pauses GC (s/s) | Exceptions /s |
|---|---|---|---|---|---|
| `DESKTOP-DEV-X2C-23052` | 0.42 | 0 | 9 | 0.004 | 0.11 |
| `DESKTOP-DEV-X2C-47748` | 0.20 | 1 | 9 | 0.003 | 2.73 |
| `DESKTOP-DEV-X2C-49448` | 0.33 | 1 | 9 | 0.003 | 0.02 |
| `DESKTOP-DEV-X2C-54700` | 0.38 | 0 | 9 | 0.003 | 0.05 |
| `DESKTOP-DEV-X2C-7348` | 0.35 | 0 | 9 | 0.003 | 0.11 |

> Valeurs **maximales** sur la fenêtre (5 réplica(s) distingué(s)). Un écart marqué entre réplicas signale un déséquilibre de répartition, pas une saturation globale.

### Par conteneur et pour le tireur

⚠️ **Échantillonneur absent de la fenêtre** — le CPU des conteneurs, celui de k6 et celui de l'hôte ne sont pas mesurés. Impossible, sur ce tir, d'écarter le tireur comme facteur limitant.

### p95 client (k6) vs p95 serveur (OpenTelemetry)

| Route (serveur) | p95 max (ms) | Points |
|---|---|---|
| `api/v{version:apiVersion}/Mail/folders` | 3081.2 | 84 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}` | 2425.0 | 87 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/content/{emailid}` | 437.8 | 83 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/enrich/sync` | 74.2 | 84 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/today` | 469.9 | 84 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/download/attachment/{attachmentfilename}` | 670.0 | 82 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{emailid}/status/read` | 145.8 | 83 |
| `api/v{version:apiVersion}/Mail/folders/{foldername}/emails/{ids}` | 232.9 | 84 |
| `api/v{version:apiVersion}/Mail/sendmail` | 987.5 | 81 |
| `api/v{version:apiVersion}/Patients/search/advanced` | 41.8 | 80 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/medical-documents` | 204.0 | 80 |
| `api/v{version:apiVersion}/Patients/{patientId:guid}/opposition` | 41.8 | 80 |
| `api/v{version:apiVersion}/Search/semantic` | 1450.0 | 82 |
| `api/v{version:apiVersion}/Settings` | 242.5 | 5 |
| `api/v{version:apiVersion}/Settings/getsettings` | 24.5 | 5 |
| `api/v{version:apiVersion}/Settings/mail-server` | 24.5 | 5 |
| `api/v{version:apiVersion}/Sync/coverage` | 45.8 | 84 |

- **p95 client global (k6)** : 424.1 ms
- **p95 serveur le plus élevé** : 3081.2 ms
- **Écart** : -2657.0 ms → l'attente est **dans l'application** — client et serveur voient la même latence, la saturation est interne

> L'appariement opération k6 → route serveur n'est **pas** 1:1 (une opération peut toucher plusieurs routes) : la confrontation est donc faite sur les agrégats, pas ligne à ligne. Les valeurs réelles de `http_route` sont listées ci-dessus telles que le serveur les déclare.

### Compteurs métier (`Mssante.MailProcessing`)

| Compteur | Valeur (max sur la fenêtre) |
|---|---|
| Événements de session IMAP /s | 0.00 |
| Recherches (s, p95) | 1.450 |

### Où part le temps d'une opération servie par la base

| Opération | Requêtes/appel | Moy. totale (ms) | p95 total (ms) | attente d'une connexion | exécution SQL | le reste (matérialisation, DTO) |
|---|---|---|---|---|---|---|
| `GetMail` | 11.0 | 19.0 | 50 | 1.5 (8.0 %), p95 21 | 15.1 (79.4 %), p95 46 | 2.3 (12.0 %), p95 13 |
| `GetMailsByUids` | 14.7 | 19.9 | 48 | 0.0 (0.1 %), p95 5 | 14.9 (75.1 %), p95 33 | 4.9 (24.8 %), p95 23 |

- **`GetMail`** — sur 19.0 ms en moyenne (11.0 requête(s) SQL par appel) : 1.5 ms attente d'une connexion, 15.1 ms exécution SQL, 2.3 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

- **`GetMailsByUids`** — sur 19.9 ms en moyenne (14.7 requête(s) SQL par appel) : 0.0 ms attente d'une connexion, 14.9 ms exécution SQL, 4.9 ms le reste (matérialisation, DTO). **Poste dominant : exécution SQL.**

> Lecture — **les parts sont calculées sur les moyennes**, qui s'additionnent ; les p95 par phase disent où vit la queue et ne se partagent aucun total (le p95 d'une somme n'est pas la somme des p95). `attente d'une connexion` est la contention base à l'état pur (pool Npgsql, PgBouncer) ; `le reste` est ce que le total ne doit pas à la base — streaming des lignes, matérialisation EF, construction des DTO.

> ⚠️ **Cette table ne couvre plus que des lectures** (task-258) : `EnrichPersistMail` est l'**écriture** d'un message enrichi, le seul poste de l'enrichissement dont le coût croît avec la concurrence. C'est elle qui tranche, sur le triplement de `db_write` mesuré par task-255 (23,3 → 62,1 ms/message de 4 à 16), entre une **file** (`attente d'une connexion` qui monte) et du **travail** (`exécution SQL` ou `requêtes/appel` qui montent). Les deux appellent des remèdes opposés : desserrer un pool d'un côté, réduire le travail par message de l'autre.

### Combien d'objets une opération servie par la base construit-elle

| Opération | Objets/appel | Matérialisation (ms) | Coût par objet (µs) | messages | étiquettes | destinataires | pièces jointes | identifiants enrichis | acquittements | documents médicaux | résultats de biologie | éléments de synthèse | corps de messages | objets de fil | références de doublon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GetMail` | 11.1 | 2.3 | 205.4 | 0.9 | 1.3 | 0.9 | 2.9 | non relevé | 0.0 | 0.9 | 3.2 | 0.0 | 0.9 | non relevé | 0.1 |
| `GetMailsByUids` | 208.2 | 4.9 | 23.7 | 18.8 | 28.4 | 18.8 | 30.3 | 18.8 | 0.0 | 18.8 | 6.4 | 0.0 | 18.7 | 44.9 | 4.2 |

- **`GetMail`** — sur 2.3 ms de matérialisation, l'appel a construit 11.1 objets, dont 0.9 messages, 1.3 étiquettes, 0.9 destinataires, 2.9 pièces jointes, 0.0 acquittements, 0.9 documents médicaux, 3.2 résultats de biologie, 0.0 éléments de synthèse, 0.9 corps de messages, 0.1 références de doublon. **Famille dominante : résultats de biologie.**
  - Coût par objet : **205.4 µs**.

- **`GetMailsByUids`** — sur 4.9 ms de matérialisation, l'appel a construit 208.2 objets, dont 18.8 messages, 28.4 étiquettes, 18.8 destinataires, 30.3 pièces jointes, 18.8 identifiants enrichis, 0.0 acquittements, 18.8 documents médicaux, 6.4 résultats de biologie, 0.0 éléments de synthèse, 18.7 corps de messages, 44.9 objets de fil, 4.2 références de doublon. **Famille dominante : objets de fil.**
  - Coût par objet : **23.7 µs**.
  - Contre-épreuve du +51 % (433.3 → 654.5 ms à 15,8 requêtes constantes) : au coût mesuré ici, ces 221.2 ms exigent **9338.7 objets de plus par appel**. Si le décompte du tir de référence est inférieur de cet ordre, la déduction « plus de contenu enrichi » tient ; sinon c'est le **coût par objet** qui a bougé, et la déduction actuelle est fausse.

> Lecture — **une cellule vide n'est pas un zéro** : `non relevé` signifie que l'appel n'a pas chargé ce lot du tout (une page sans document CDA n'interroge pas la biologie), tandis qu'un `0.0` signifie qu'il l'a chargé et n'a rien trouvé. Le coût par objet est la matérialisation divisée par les objets **mesurés** : il ne vaut que si les familles listées couvrent bien tous les lots que l'appel construit.

> ⚠️ **Un coût par objet stable ne dit pas que le coût est proportionnel au volume.** Il peut être dominé par une seule famille, par le suivi de changements d'EF, ou par une allocation par objet indépendante de sa taille. C'est la ventilation qui tranche, pas le ratio global.

### Où part le temps d'un enrichissement

⚠️ **Aucune décomposition sur la fenêtre.** Les instruments `mssante_enrichment_message_duration_seconds` / `..._phase_...` (task-245) n'ont produit aucun point : soit le binaire déployé est antérieur à leur ajout, soit le collector n'a pas tourné, soit aucun message n'a été enrichi. Sans eux, le **goulot G1** du tir 500 reste une boîte noire — et cette EPIC a déjà payé une US applicative écrite sur une cause supposée (task-222).

### Où part le temps d'un envoi

| Moy. par envoi (ms) | p95 (ms) | garde d'opposition | construction MIME | obtention de session SMTP | transmission + acquittement | archivage Sent | le reste |
|---|---|---|---|---|---|---|---|
| 503.3 | 924 | 0.0 (0.0 %), p95 5 | 5.7 (1.1 %), p95 13 | 103.2 (20.5 %), p95 425 | 394.3 (78.3 %), p95 488 | 359.9 (71.5 %), p95 715 | 0.1 (0.0 %), p95 5 |

- **Envoyer un message** — sur 503.3 ms en moyenne : 0.0 ms garde d'opposition, 5.7 ms construction MIME, 103.2 ms obtention de session SMTP, 394.3 ms transmission + acquittement, 359.9 ms archivage Sent, 0.1 ms le reste. **Poste dominant : transmission + acquittement.**

> Lecture — mêmes règles que l'enrichissement : les parts se calculent sur les moyennes, les p95 ne se partagent aucun total. `archive_sent` est optionnelle par construction : « non relevé » veut dire qu'aucun archivage n'a eu lieu dans le périmètre, jamais qu'il a coûté zéro. Le finding Seq du 2026-08-14 (≈3,1 `SmtpCommandException` par envoi) se confronte à `smtp_transmit` et `acquire_session` : c'est ici qu'il se confirme ou s'écarte.

### Verrous du chemin `read_list`

| Verrou | Attente p95 (s) | Détention p95 (s) | Acquisitions /s |
|---|---|---|---|
| `imap_session` | 0.426 | 2.425 | 14.86 |
| `smtp_session` | 0.005 | 0.987 | 1.73 |

- Aucun abandon du verrou distribué sur la fenêtre : le budget d'attente raccourci n'a jamais été épuisé.

> Lecture : une **attente** élevée désigne la contention sur ce verrou ; une **détention** élevée désigne ce qui se fait dessous, et c'est alors sa portée qu'il faut discuter. `imap_session` sérialise TOUTES les opérations IMAP d'une session, pas seulement les lectures entre elles.

### Verrou de session `imap_session`, par opération

| Opération | Attente p95 (s) | Détention p95 (s) | Détention p95 établ. (s) | Détention p95 exploit. (s) | Acquisitions /s |
|---|---|---|---|---|---|
| `AppendToSent` | 0.024 | 1.606 | 2.425 | 0.488 | 1.71 |
| `GetAttachmentStream` | 0.488 | 0.488 | — | 0.488 | 0.36 |
| `GetEmailContent` | 0.005 | 0.490 | 0.992 | 0.488 | 2.25 |
| `GetFolders` | 0.450 | 0.988 | 0.988 | 0.243 | 0.36 |
| `ReadFolder` | 0.488 | 2.425 | 2.425 | 0.474 | 5.22 |
| `ReadToday` | 0.005 | 0.488 | — | 0.488 | 0.36 |
| `UpdateFlag` | 0.005 | 0.488 | 0.988 | 0.488 | 4.96 |

#### Détention en exploitation, **fenêtre de régime** — palier 40

> task-276 — la table ci-dessus couvre tout le tir **et n'en publie que la pointe**. Celle-ci ne couvre que la fenêtre qui porte le verdict (chauffe exclue, task-264) et rend la **distribution** : c'est la médiane qui dit ce que le médecin subit d'ordinaire, la pointe ne dit que le pire instant. Les confondre a déjà produit une conclusion fausse (voir la note sous la table).

| Opération | Détention médiane (s) | p90 (s) | Pointe (s) | Part > 2 s |
|---|---|---|---|---|
| `AppendToSent` | **0.487** | 0.488 | 0.488 | 0.0 % |
| `GetAttachmentStream` | **0.487** | 0.488 | 0.488 | 0.0 % |
| `GetEmailContent` | **0.487** | 0.487 | 0.488 | 0.0 % |
| `GetFolders` | **0.241** | 0.241 | 0.242 | 0.0 % |
| `ReadFolder` | **0.275** | 0.333 | 0.336 | 0.0 % |
| `ReadToday` | **0.487** | 0.488 | 0.488 | 0.0 % |
| `UpdateFlag` | **0.487** | 0.487 | 0.487 | 0.0 % |

| Voie | Acquisitions /s |
|---|---|
| `read` | 14.86 |

**Établissement vs exploitation** (task-271) : `establish` est la détention prise sur une session pas encore connectée-et-authentifiée — elle paie le handshake, et le verrou **doit** la couvrir (le wrapper IMAP est partagé par toutes les opérations du praticien : l'établir hors verrou laisserait deux appelants le connecter en même temps). `operate` est la détention qui n'achète aucun aller-retour d'établissement. **Seule `operate` est opposable à un SLO interne.**

**Archivage vs reste** : `AppendToSent` attend 0.024 s au p95, contre 0.488 s pour l'opération la plus lente des autres. task-216 a **retiré la voie d'écriture** : l'archivage partage de nouveau la session du praticien, donc cet écart n'a plus à être en sa faveur — il est attendu du même ordre que les autres. Ce qui juge la décision n'est pas cette ligne mais `send` vu du praticien, que la contre-épreuve de task-215 a mesuré **plus rapide sans la voie qu'avec**.

### Ressource épinglée

| Ressource | Valeur max | Borne | Part de la borne | Présence |
|---|---|---|---|---|
| file ThreadPool du réplica `DESKTOP-DEV-X2C-47748` | 1.00 éléments | 100 éléments | 1.0 % | 0.0 % — transitoire |

**Aucune ressource épinglée — le plafond est ailleurs.** La plus sollicitée (file ThreadPool du réplica `DESKTOP-DEV-X2C-47748`) monte à 1.0 % de sa borne, mais sur 0.0 % des échantillons seulement — sous le seuil de présence de 25 %, c'est un transitoire et non une saturation. Chercher du côté des dépendances sérialisées (sessions IMAP, verrous de provisionnement) plutôt que d'une ressource matérielle.

## IA — fournisseurs, étiquetage, file du bus

- **IA** : 🧪 **simulée** — faux fournisseur OpenAI du banc (`MSS_LOADTEST_AI=fake`), durées et parts d'étiquetage mesurées au tir du 2026-11-02. **Famille distincte** : ne se compare pas à un tir OpenAI. La recherche sémantique paie son coût, mais ses résultats n'ont pas de sens (vecteurs dérivés d'un hachage).

> Aucune étape de la grille SLO n'appelle le chat : le fournisseur IA agit **à côté** du médecin. `AddNewMailConsumer` attend l'étiquetage et l'embedding ensemble (10 messages simultanés) : un étiquetage lent bride aussi les embeddings, donc retarde l'entrée des nouveaux mails dans la recherche. Ollama partage en outre l'hôte du système sous test. Ces chiffres sont **publiés, jamais jugés** par la grille.

- **Fournisseur du chat servi pendant le tir** : non exercé (lu sur l'étiquette `provider` de l'étiquetage)
- **Tokens de chat envoyés à OpenAI** : 0

| Fournisseur | Modèle | Type | Tokens |
|---|---|---|---|
| OpenAI | text-embedding-3-small | embedding | 2 270 |

> Tokens **déclarés** par les fournisseurs : une réponse sans usage n'est pas comptée (aucune estimation).

### Pipeline IA par étape

_Aucune exécution du pipeline IA sur la fenêtre._

- ✅ **Envois mis en attente de confirmation** (`mssante_pending_sends_total{outcome="queued"}`) : 0 — doit valoir 0. Sinon des envois sont passés par la voie hors ligne (task-320) : ils n'ont pas parlé SMTP et flattent l'étape « Envoi ».

### File `add-new-mail-queue` (échantillonneur)

_Non relevée — échantillonneur antérieur à la sonde `bus`, ou RabbitMQ injoignable._

### GPU et conteneur Ollama (échantillonneur)

_Non relevés — pas de sonde GPU (`nvidia-smi`) ni de conteneur `mss-mail-ollama` sur la fenêtre (tir tout-OpenAI, ou échantillonneur antérieur)._

## Postgres — réaction du serveur et requêtes

> Trois photos `pg-statements.sh` (compteurs serveur début/fin, `pg_stat_statements` par forme de requête, tables d'une base praticien échantillon). Les grandeurs « par seconde » et « par requête HTTP » se comparent d'un tir à l'autre à N constant ; le top 20 dit **sur quoi** le serveur a travaillé. Les pistes sont des hypothèses dérivées de compteurs : le plan (`explain (analyze, buffers)`) tranche, pas ce tableau.

### Réaction du serveur au tir (comparable inter-tirs)

| Grandeur | Valeur | Lecture |
|---|---|---|
| Durée couverte (reset → photo) | **7.6 min** | chauffe incluse — le régime seul exige un delta sur `snapshot warmup` |
| Transactions validées / s | **1 051.6** | annulées : 0.0 % |
| Backends actifs (équivalent) | **0.14** | temps SQL actif ÷ durée : requêtes simultanément en exécution, en moyenne |
| Coût SQL par requête HTTP | **2.8 ms** | sur 23 114 requêtes HTTP k6 |
| Taux de cache (blocs) | **99.14 %** | ✅ ≥ 99 % |
| Lecture disque | **0.71 Mo/s (91 blocs/s)** | attente disque : 5.0 % du temps SQL actif |
| Lignes balayées / renvoyées par index, par s | **119 375 / 5 664** | rapport 21.1 ⚠️ balayages dominants |
| Écritures de lignes / s (ins+upd+del) | **30.3** |  |
| Fichiers temporaires | **0 (0.0 Mo)** | ✅ aucun tri sur disque |
| WAL | **0.04 Mo/s** | `wal_buffers_full` : 0 |
| Checkpoints programmés / forcés | **1 / 0** | blocs écrits par les backends eux-mêmes : 25 % |
| Sessions ouvertes / s | **0.80** | abandonnées 0, fatales 0 ; `idle in transaction` : 0.0 % du temps de session |
| Interblocages | **0** | 0 attendu |
| Croissance des bases praticien | **9.6 Mo** | 2 000 bases |
| Backends (échantillonneur, moy / max) | **non relevé** | `max_connections` = 2 500 |
| Login Postgres (sonde, p50 / p95 / max) | **non relevé** | < 1 000 ms attendu |
| cgroup mémoire (moy / max) | **non relevé** |  |

Réglages au moment de la photo : PostgreSQL 16.11, `shared_buffers` 12 288 Mo, `effective_cache_size` 36 864 Mo, `work_mem` 4 096 Ko, `random_page_cost` 4.0, `max_connections` 2 500, autovacuum on.

### Top 20 des requêtes par temps serveur cumulé

90 formes de requête, 483 329 appels, **0.6 min** de temps serveur cumulé — soit **1.7 ms de SQL par requête HTTP**.

| # | Part | Cumul | Appels | /req HTTP | ms/appel | Lignes/appel | Blocs/appel | Disque | Temp | Bases | Piste | Requête |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **16.5 %** | 16 % | 490 | 0.02 | 12.93 | 54.8 | 364 | 0 % | 0 | 40 | — | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 2 | **14.5 %** | 31 % | 490 | 0.02 | 11.37 | 54.8 | 424 | 1 % | 0 | 40 | — | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINALITY AS t(pattern, po…` |
| 3 | **10.5 %** | 41 % | 376 | 0.02 | 10.73 | 30.7 | 484 | 8 % | 0 | 40 | — | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."Size" FROM "MailAtt…` |
| 4 | **8.1 %** | 50 % | 4 496 | 0.19 | 0.69 | 1.0 | 19 | 10 % | 0 | 40 | — | `SELECT m."Id", m."Body", m."Category", m."ContentFingerprint", m."CreatedAt", m."Date", m."DocumentId", m."DuplicateCon…` |
| 5 | **5.6 %** | 55 % | 2 506 | 0.11 | 0.85 | 18.8 | 247 | 0 % | 0 | 40 | — | `SELECT m."Id", m."MailId", m."PatientId", m."ManualAttachedByRpps", m."ManualAttachedByFirstName", m."ManualAttachedByL…` |
| 6 | **4.5 %** | 60 % | 69 199 | 2.99 | 0.03 | 1.0 | 3 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT m.validated_by_psc_subject AS "ValidatedByPscSubject", m.validated_by_rpps AS "ValidatedByRpps" FROM mss_account…` |
| 7 | **4.0 %** | 64 % | 490 | 0.02 | 3.12 | 20.0 | 676 | 1 % | 0 | 40 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMedicalDocuments" AS m …` |
| 8 | **3.9 %** | 68 % | 165 456 | 7.16 | 0.01 | 0.0 | 0 | — | 0 | 1 | **Infra** — cycle de connexion/transaction, pas une requête métier : coût du login et du pooler (`server_idle_timeout`, `Minimum Pool Size`) | `DISCARD ALL` |
| 9 | **3.9 %** | 71 % | 69 199 | 2.99 | 0.02 | 1.0 | 3 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT a.id, a.authentication_subject, a.created_at, a.email, a.last_activity_at, a.last_authentication_at, a.username …` |
| 10 | **3.6 %** | 75 % | 490 | 0.02 | 2.83 | 20.0 | 686 | 1 % | 0 | 40 | **Schéma** — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailContents" AS m INNER JO…` |
| 11 | **2.7 %** | 78 % | 1 728 | 0.07 | 0.59 | 9.1 | 173 | 0 % | 0 | 40 | — | `SELECT t."Code", t."Name", t."ColorCode", ( SELECT count(*)::int FROM "MailTags" AS m1 WHERE m1."TagId" = t."Id" AND EX…` |
| 12 | **2.3 %** | 80 % | 732 | 0.03 | 1.21 | 1.0 | 20 | 52 % | 0 | 40 | **Postgres** — 52 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage | `SELECT m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m."MailId", m."Size" FROM "MailAtt…` |
| 13 | **2.0 %** | 82 % | 4 167 | 0.18 | 0.18 | 1.0 | 15 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `INSERT INTO audit_traces (id, tenant_id, user_id, user_session_id, timestamp, action_type, success, error_message, erro…` |
| 14 | **1.9 %** | 84 % | 4 496 | 0.19 | 0.17 | 1.0 | 8 | 1 % | 0 | 40 | — | `SELECT m."Id", m."Body", m."BodyHtml", m."ContentType", m."Embedding", m."EmbeddingModel", m."MailId", m."Summary" FROM…` |
| 15 | **1.8 %** | 86 % | 23 108 | 1.00 | 0.03 | 1.0 | 6 | 0 % | 0 | 1 | **Infra** — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien | `SELECT m.id, m.account_id, m.address_type, m.attached_at, m.database_name, m.detached_at, m.is_default, m.last_successf…` |
| 16 | **1.1 %** | 87 % | 3 376 | 0.15 | 0.12 | 18.0 | 5 | 0 % | 0 | 40 | **Schéma** — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 17 | **0.9 %** | 88 % | 1 688 | 0.07 | 0.20 | 27.0 | 5 | 0 % | 0 | 40 | — | `SELECT m."Id", m."FolderPath", m."Uid", m."MessageId", m."InReplyTo", m."References", m."SentDate" FROM "Mails" AS m WH…` |
| 18 | **0.9 %** | 89 % | 7 647 | 0.33 | 0.04 | 1.5 | 18 | 0 % | 0 | 40 | — | `SELECT m."Id" AS "DocId", m."DuplicateOfId" AS "OriginalDocId", m0."Title" AS "DocumentTitle", m0."Date" AS "DocumentDa…` |
| 19 | **0.8 %** | 89 % | 7 647 | 0.33 | 0.04 | 2.3 | 9 | 0 % | 0 | 40 | — | `SELECT m."MedicalDocumentId", m."InterpretationCode" FROM "MailMedicalDocumentBiology" AS m WHERE m."IsFlagged" AND m."…` |
| 20 | **0.7 %** | 90 % | 2 506 | 0.11 | 0.10 | 18.7 | 5 | 0 % | 0 | 40 | — | `SELECT m."Id", m."AiTaggingPendingSince", m."FolderPath", m."FromAddress", m."FromName", m."HasBiologyResults", m."HasM…` |

Colonnes : **Part** = part du temps serveur cumulé de toutes les formes ; **/req HTTP** = appels SQL par requête HTTP du tir (> 3 sur une forme légère = N+1 probable) ; **Blocs/appel** = pages de 8 Ko touchées par exécution ; **Disque** = part de ces blocs lus hors cache ; **Bases** = nombre de bases où la forme a tourné (1 = base commune).

| Répartition | Part du temps | Part des appels |
|---|---|---|
| SELECT | 92.6 % | 61.3 % |
| INSERT | 2.4 % | 1.1 % |
| UPDATE | 0.8 % | 0.4 % |
| DELETE | 0.1 % | 0.3 % |
| AUTRE | 4.1 % | 36.9 % |
| bases : praticien (N bases) | 83.8 % | 30.6 % |
| bases : unique (1 base) | 16.2 % | 69.4 % |

Les plus lentes **par appel** (≥ 100 appels) — ce que le praticien attend :

| ms/appel | max ms | Appels | Part | Requête |
|---|---|---|---|---|
| **12.9** | 24 | 490 | 16.5 % | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINAL…` |
| **11.4** | 24 | 490 | 14.5 % | `WITH terms AS ( SELECT lower(t.pattern) AS pattern, t.position FROM unnest($1::text[]) WITH ORDINAL…` |
| **10.7** | 118 | 376 | 10.5 % | `SELECT m."MailId", m."Id", m."Content", m."ContentType", m."DocumentId", m."FileName", m."Guid", m.…` |
| **3.1** | 23 | 490 | 4.0 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailMed…` |
| **2.8** | 19 | 490 | 3.6 % | `SELECT m1."Uid"::bigint AS "Uid", m1."FolderPath", m."Embedding" <=> $1 AS "Distance" FROM "MailCon…` |

### Tables et index de la base échantillon

Base `u_l9l_b27c2b6f659b50f6240b3481927d0381` (la plus volumineuse du banc), compteurs fin − début.

✅ aucun balayage séquentiel sur la base échantillon pendant le tir.

### Pistes d'optimisation (hypothèses à confirmer par le plan)

| Cible | Gravité | Piste |
|---|---|---|
| Schéma | 🟠 | 21 lignes balayées par ligne renvoyée par index : les balayages séquentiels dominent — voir les tables balayées |
| Infra | 🟡 | requête n°6 (4.5 % du temps SQL) — une seule base pour tout le trafic : point de contention unique (base commune d'audit / registre) — à traiter avant les requêtes praticien |
| Infra | 🟡 | requête n°8 (3.9 % du temps SQL) — cycle de connexion/transaction, pas une requête métier : coût du login et du pooler (`server_idle_timeout`, `Minimum Pool Size`) |
| Postgres | 🟡 | requête n°12 (2.3 % du temps SQL) — 52 % des blocs lus sur disque : jeu de travail hors `shared_buffers` ou cache froid après redémarrage |
| Schéma | 🟡 | requête n°7 (4.0 % du temps SQL) — recherche vectorielle pgvector : index HNSW/IVFFlat et `ef_search` ; filtrer avant de trier par distance |
| Schéma | 🟡 | requête n°16 (1.1 % du temps SQL) — recherche texte : index GIN (`pg_trgm` pour LIKE/ILIKE, `tsvector` pour @@) |

Cibles : **Postgres** = réglage serveur (`shared_buffers`, `work_mem`, bgwriter…), **Schéma** = index à ajouter ou retirer (migration EF), **Code** = forme de la requête EF Core (projection, `Include`, lot, portée du `DbContext`), **Infra** = pool, login, provisionnement. Prochain geste pour chaque ligne : `explain (analyze, buffers)` de la forme sur une base praticien hydratée, puis un A/B au banc à N constant.

Sources : `pgstats-journey-101304.tsv`, `pgserver-journey-debut-100531.tsv`, `pgserver-journey-fin-101305.tsv`, `pgtables-journey-debut-100537.tsv`, `pgtables-journey-fin-101309.tsv`.

## Vérification par base (propriété + complétude)


- **Bases inspectées** : 40
- **Mails stockés (total)** : 5670 — dont **5670** correctement attribués
- **Sujets étrangers (mélange inter-utilisateurs)** : 0
- **Sujets sans marqueur** : 0
- **Verdict propriété** : PASS

✅ **40 boîte(s) vérifiée(s), aucune anomalie** — aucun message trouvé dans la boîte d'un autre praticien, aucun message sans marqueur de propriété, complétude tenue partout. Le détail par boîte n'est pas rendu : seules les anomalies le seraient.

## Analyse Seq (findings) — MCP seq-local

> Dump brut des événements du tir : `seq-journey-controle-20-40-task424-101303.jsonl`.

_À COMPLÉTER par l'analyse systématique seq-local (voir le skill). Lister ici : erreurs/warnings hors bruit de boot, nombre de parsings CDA (`[CdaParsingService] Parsing completed`), échecs d'embedding (task-196), 429, erreurs de connexion IMAP, reprises d'étiquetage IA (`[TaggingRecovery]`), et tout marqueur de régression (`Failed to parse entity headers`)._
