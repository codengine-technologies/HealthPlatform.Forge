# Volumétrie d'une boîte : les requêtes du banc rejouées sur une boîte de 11 000 mails

> 2026-11-09. Temps 1 du plan de volumétrie : aucun tir, des plans d'exécution seulement.
> Plans, mesures et script : `Docs/audits/findings/plans/20261109-volumetrie-boite-11k/`.

## Question

Les boîtes du banc portent environ 150 à 250 mails ; une boîte de production en porte environ 10 000. Quelles requêtes
du parcours médecin coûtent plus quand la boîte grossit, et de combien ?

## Méthode

- **Requêtes** : les 15 formes SQL les plus coûteuses du tir `journey-courte 1400→1996` du 2026-11-08 à 17:48
  (qualification de task-435, task-434 comprise), moins trois qui ne portent pas sur la base d'une boîte (registre
  des boîtes, écriture d'audit FND-012, catalogue de types Npgsql FND-008). Restent 12 formes, dont FND-010 et FND-014.
- **Deux bases**, même schéma, même Postgres local :

  | | Banc `u_l9l_b27c…` | Boîte de Virginie `u_vmm_c9e6…` | Rapport |
  |---|---|---|---|
  | Mails (INBOX) | 156 | 11 178 | ×72 |
  | Documents médicaux | 157 | 567 | ×3,6 |
  | Taille de la base | 49 Mo | 182 Mo | ×3,7 |
  | `MailContents` (dont TOAST) | 2 Mo | 103 Mo (91 Mo) | ×53 |

- **Plans** : `findings.explain_script` de `/loadtest-findings` (plan générique, paramètres tirés de chaque base et
  jamais affichés, `ROLLBACK`). Le garde-fou `BENCH_DB` de l'outil n'a pas été modifié : la base de Virginie (boîte
  de formation, données de test) est jouée par un `psql` direct, en lecture seule. Chaque plan est joué deux fois ;
  la seconde mesure (cache chaud) est retenue. Les deux passages complets ont donné les mêmes chiffres.
- **Paramètres** : ceux du parcours du banc. Recherche « compte rendu de synthese » (motifs `%compte%`, `%rendu%`,
  `%synthese%`), 200 candidats par terme, distance maximale 0,9, limite 20 ; page de liste = les 18 messages les plus
  récents de l'INBOX.

## Résultats

| Requête | Banc : ms / pages | Virginie : ms / pages | Pages | Temps |
|---|---|---|---|---|
| **Recherche vectorielle — contenus** (FND-010) | 2,23 / 715 | **295,88 / 70 439** | **×98** | **×133** |
| **Recherche plein texte — contenus** | 11,65 / 505 | **134,73 / 69 204** | **×137** | ×12 |
| Recherche plein texte — documents | 8,69 / 522 | 31,70 / 3 860 | ×7,4 | ×3,6 |
| Recherche vectorielle — documents (FND-010) | 2,40 / 743 | 16,35 / 4 092 | ×5,5 | ×6,8 |
| Messages qui citent un fil (FND-014) | 0,13 / 5 | 2,13 / 433 | ×87 | ×16 |
| Acquittements de biologie d'une page | 0,04 / 3 | 0,08 / 49 | ×16 | ×2,2 |
| Messages d'une page, par UID | 0,04 / 5 | 0,07 / 55 | ×11 | ×1,7 |
| Page de liste — documents et comptages | 0,30 / 126 | 0,48 / 274 | ×2,2 | ×1,6 |
| Ouvrir un message — document | 0,04 / 2 | 0,04 / 3 | ×1,5 | stable |
| Ouvrir un message — contenu | 0,03 / 2 | 0,05 / 3 | ×1,5 | stable |
| Télécharger une pièce jointe | 0,12 / 5 | 0,08 / 6 | ×1,2 | stable |
| Doublons actifs d'une page | 0,22 / 140 | 0,18 / 148 | ×1,1 | stable |

**Une recherche hybride** (les 4 requêtes de recherche d'un appel `POST /search/semantic`) coûte **25 ms** de SQL sur la
boîte du banc et **479 ms** sur la boîte de 11 000 mails, à cache chaud et pour un seul médecin.

## Lecture

1. **La recherche suit linéairement la taille de la boîte.** C'est le seul geste du médecin dans ce cas : ouvrir un
   message, télécharger une pièce, afficher une page de liste restent stables.
   - **Vectorielle, contenus** — `Seq Scan` de `MailContents` : la distance est calculée pour les 11 284 contenus.
     Aucun index sur `Embedding` n'existe, dans aucune migration, et aucune décision ne l'écarte. Chaque vecteur pèse
     6 148 octets (1 536 flottants), stockés en TOAST : la requête relit environ 70 Mo de vecteurs, à raison d'environ
     trois lectures de page par ligne (filtre de distance, puis tri).
   - **Plein texte, contenus** — l'application passe en `$2` les identifiants de **tous** les contenus du dossier
     (`SemanticSearchRepository.FullTextSearchEmailContentsAsync` : `candidateRowIds` = tous les `MailContents` de
     l'INBOX qui ont un corps), puis la requête met chaque corps en minuscules. 11 175 lignes lues pour 202 rendues.
   - **Documents** — même mécanique, proportionnelle au nombre de documents (×3,6) : faible dans cette boîte, mais une
     boîte riche en CDA la ferait grossir comme les contenus.
2. **FND-014 est confirmé linéaire** (×87 pages pour ×72 mails : balayage de `Mails` sur `References`), mais son coût
   reste faible à cette taille : 2 ms par page de liste.
3. **Les correctifs des tasks 429, 430 et 434 tiennent** : ouverture d'un message, comptages et pièces jointes ne
   croissent pas avec la boîte.

## Ce que cela annonce en charge

- Les chiffres ci-dessus sont **à cache chaud**. En production, avec 10 000 bases, les 103 Mo de `MailContents` d'une
  boîte ne resteront pas en mémoire : chaque recherche relira de l'ordre de 100 Mo sur disque.
- Au banc, l'étape « recherche » était déjà la plus lente au palier 1996 (p50 532 ms, genou naissant), sur des boîtes
  de 156 mails. Avec des boîtes de 10 000 mails, le SQL seul d'une recherche est multiplié par environ 19.

## Verdicts proposés pour le registre

- **FND-010** (`9b0276…`, `90fed31…`) : plausible → **confirmé**. La forme sur les contenus est la plus lourde de la
  boîte de 11 000 mails (×133 en temps).
- **FND-014** (`a5978b…`) : plausible → **confirmé**, coût faible à 11 000 mails ; priorité basse.
- **Recherche plein texte des contenus** (`840774…`, forme d'après de FND-002, écartée au rejeu du 2026-11-07 sur une
  boîte de 156 mails) : à rouvrir comme **nouveau finding de croissance** (lecture de tout le dossier à chaque recherche).

Ces verdicts sont à porter au registre par `/loadtest-findings`, puis l'humain choisit les tasks.

## Limites

- Plans génériques à cache chaud ; aucune concurrence. La charge se mesure au temps 3 (tir A/B au banc).
- La boîte de Virginie compte peu de documents médicaux (5 %) et des corps courts (0,9 Ko en moyenne contre 4,6 Ko au
  banc) : la recherche plein texte des contenus y est plutôt **sous-estimée**.
- La requête vectorielle utilise un vecteur de la base comme vecteur de recherche, au lieu de l'embedding d'une vraie
  requête : sans index, cela ne change pas le travail (toutes les distances sont calculées).
