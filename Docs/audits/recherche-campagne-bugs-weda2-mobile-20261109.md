# Recherche dans weda2 et le mobile : campagne de bugs du 2026-11-09

> Question de l'humain : « Je voudrais savoir si cette recherche fonctionne. J'ai des doutes. »
> Boîte de formation de Virginie (11 178 mails dans l'INBOX), api-mail local au commit `405da376`, appels réels à
> `POST /api/v1/Search/semantic` avec la session de Virginie (jeton obtenu par le proxy PSC). Script, réponses et
> notation : `scratchpad/recherche/` de la session (`campagne.py`, `resultats.json`).

## Réponse courte

**La recherche trouve un mot rare, bien orthographié, dans le corps d'un message récent.** Dès qu'on s'écarte de ce cas
(accent oublié, mot dans l'objet, patient au long historique, plusieurs mots, ponctuation), elle rate une grande part
des messages, ou noie les bons parmi des résultats sans rapport. Et les deux clients ne rendent pas la même chose pour
la même recherche.

## Méthode

- **Vérité terrain** : pour chaque requête, les messages de l'INBOX qui contiennent les termes, comptés dans la base
  (objet, corps et documents médicaux).
- **15 requêtes × 2 réglages** du serveur, tels que les clients les envoient (`maxResults` 50, `searchType` 3,
  `searchMode` 3, dossier INBOX) :
  - seuil de similarité **0,7** : défaut de weda2 pour une personne sans réglage enregistré ;
  - seuil **0,1** : défaut du mobile, et réglage enregistré de deux des quatre personnes de la boîte.
- Le mobile envoie au serveur la même requête que weda2 réglé à 0,1 ; son tri par date est appliqué à l'analyse.
- Les 30 appels ont répondu 200, sans mode dégradé, en 0,5 à 0,9 s (4 s pour le premier).

## Ce qui marche

| Requête | Vérité | weda2 (0,7) |
|---|---|---|
| `psoriasis` | 6 messages | 6 rendus, tous aux rangs 1 à 6 |
| `kaliémie` | 20 | 20, tous pertinents |
| `261109954185` (numéro de dossier HPRIM) | 1 | 1, au rang 1 |
| `holter`, `hémoglobine`, `bilan lipidique` | 117 à 1 608 | 50 rendus, tous pertinents |

## Défauts constatés par l'API

### R1 — Un accent oublié fait perdre presque tout (serveur)

| Requête | Vérité (avec accent) | 0,7 | 0,1 |
|---|---|---|---|
| `hemoglobine` | 804 messages contiennent « hémoglobine » | **2** | 50, tous pertinents (rattrapés par la similarité) |
| `compte rendu de synthese` | 669 contiennent les trois mots accentués | 50 rendus, **5** contiennent « synthèse » | 11 sur 50 |

- Cause : le plein texte compare `lower(Body) LIKE '%terme%'`, sans repli des accents (`SearchQueryHelper`,
  `SemanticSearchRepository`). Seule la recherche sémantique rattrape, et seulement avec un seuil bas.
- La requête du banc de charge elle-même (« compte rendu de synthese ») est concernée.

### R2 — L'objet n'est pas cherché (serveur)

- `urgent` : 72 messages le portent, dont **67 dans l'objet seulement**. Rendus : **5** (à 0,7 comme à 0,1).
- Cause : le plein texte ne lit que le corps des messages et des documents. L'objet n'entre que dans l'embedding.
  L'expéditeur et le nom des pièces jointes ne sont pas cherchés non plus (sauf par les filtres avancés).

### R3 — L'historique ancien d'un patient est invisible (serveur)

- `Catherine BERNARD` : **51** messages portent les deux noms dans le corps. Rendus : **22** (0,7), 25 (0,1).
- Tous les manquants sont **plus anciens** : à partir du 296e message le plus récent contenant « bernard ».
- Cause : chaque terme ne garde que ses **200 candidats les plus récents** (`SearchLimits.FullTextCandidatesPerTerm`)
  avant tout classement. Un nom fréquent épuise ce quota avec des messages récents d'autres patients.

### R4 — Plusieurs mots : OU au lieu de ET (serveur)

- `Catherine BERNARD` : 28 des 50 résultats (0,7) ne portent **qu'un seul** des deux noms.
- `bilan lipidique cholestérol total` : 35 messages portent les quatre mots ; 27 seulement sont rendus (0,7). Seuls
  les 3 termes les plus longs sont envoyés à la base, le plus court est abandonné sans le dire.

### R5 — La ponctuation tue la recherche (serveur)

- `cholestérol,` (virgule copiée avec le mot) : **0** résultat à 0,7, alors que 47 messages contiennent
  « cholestérol ». Cause : la requête n'est découpée que sur les espaces.

### R6 — Un mot absent ramène 50 résultats sans rapport (serveur, seuil bas)

- `zorglubine` (n'existe pas dans la boîte) : 0 à 0,7, **50 résultats** à 0,1.
- `psoriasis` à 0,1 : les 6 bons, puis 44 messages qui ne contiennent pas le mot.
- Cause : à 0,1, la recherche sémantique rend toujours ses 50 voisins les plus proches, même lointains.

### R7 — Le même médecin n'obtient pas la même chose selon le client (clients)

- Seuil : weda2 prend le réglage de la personne (défaut **0,7**) ; le mobile prend **0,1** (stockage local). Résultat :
  `psoriasis` 6 contre 50, `urgent` 5 contre 50, `hemoglobine` 2 contre 50.
- Aucun des deux réglages n'est bon partout : 0,7 perd le rattrapage des accents (R1), 0,1 ajoute du bruit (R6).

### R8 — Le mobile enterre les bons résultats sous le tri par date (client mobile)

- `psoriasis` à 0,1 : les 6 messages qui contiennent le mot sont aux rangs 1 à 6 dans weda2, et aux rangs
  **5, 42, 44, 48, 49 et 50** sur le mobile.
- Cause : `mail-state.service.ts` (mobile) retrie les résultats par date d'envoi ; la pertinence est perdue.

### R9 — La troncature n'est jamais signalée (clients)

- 22 réponses sur 30 portent `isTruncated: true`. Aucun client ne lit `isTruncated`, `isDegraded`, `degradedSources`
  ni `hits` : le médecin ne sait jamais qu'il manque des résultats, ni qu'un moteur est en panne.

## Défauts lus dans le code, non exercés par la campagne

- **Mobile — requêtes obsolètes non annulées** : chaque frappe lance une recherche (300 ms de délai) sans `switchMap` ;
  une réponse lente peut écraser la plus récente.
- **weda2 — erreur muette** : en cas d'échec, rien n'est affiché et l'ancienne liste reste à l'écran.
- **Les deux — résultats rattachés par UID dans le dossier courant** : le dossier renvoyé par l'API est ignoré. Sur un
  dossier d'étiquette, deux messages de même UID venant de deux dossiers peuvent être confondus ou perdus.
- **weda2 — aucun dossier sélectionné** : la recherche porte sur tous les dossiers, mais l'écran abandonne l'affichage
  des résultats (`mail-list.component.ts`, retour anticipé sans dossier). À confirmer à l'écran.

## Ordre de gravité proposé

1. **R3** (historique ancien d'un patient invisible) et **R2** (objet non cherché) : le médecin croit qu'un message
   n'existe pas.
2. **R1** (accents) et **R5** (ponctuation) : l'usage normal du clavier fait échouer la recherche.
3. **R8** (tri par date du mobile) et **R6** / **R7** (seuil) : les bons résultats existent, mais sont noyés.
4. **R4** (OU), **R9** (troncature muette) et les défauts lus dans le code.

## Liens

- Coût de la recherche selon la taille de la boîte : `Docs/audits/api-mail-volumetrie-plans-boite-11k-20261109.md`,
  task-437. Suite donnée : EPIC E022 « Recherche fiable », tasks 438 à 441 ; task-436 (coût du plein texte) y est
  absorbée par task-439.
