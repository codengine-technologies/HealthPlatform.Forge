# Registre des findings de banc

> Tenu par `/loadtest-findings` (task-433, playbook `agents/loadtest-findings.md`). Un finding est une forme SQL du
> banc, explorée jusqu'à son code et son plan. Il est suivi ici d'un tir à l'autre.

## Comment le lire

- **Identifiant** : `FND-NNN`. Il n'est jamais réattribué, même si le finding est écarté.
- **Formes** : le md5 du texte normalisé, la clé `queryid` des `pgstats-*.tsv`. Une ligne peut en porter plusieurs :
  la forme du premier tir, ses variantes, et la forme d'après correctif. Une forme n'apparaît que dans une ligne
  (contrôlé par `findings.py check --registry`).
- **Classe** : le détecteur de task-431 qui l'a signalée. `hors-détecteur` veut dire qu'elle a été choisie pour son
  seul coût.
- **Verdict** : `confirmé` (site et plan montrent la cause), `plausible` (il manque le site ou le plan, ou une mesure
  qui tranche) ou `écarté` (avec sa raison).
- **Statut** : où en est le finding.
  - `ouvert` : rien n'est décidé ; il est ré-exploré au tir suivant.
  - `task` : l'humain a demandé une task ; il est seulement remesuré.
  - `corrigé et mesuré` : la task est mergée et sa mesure faite ; il est seulement remesuré, et sa forme absente
    confirme le correctif.
  - `écarté` : il est seulement remesuré.
- **Récidive** : un nouveau finding de même classe qu'un finding corrigé. La prévention qui a manqué est nommée dans
  la section du rapport.
- **L'humain décide** : la forge propose, l'humain choisit, puis `/po` rédige la task. Le registre passe en `task` à
  la création du task file.

## Registre

| Id | Formes | Classe | Titre | Premier tir | Verdict | Statut | Task | Mesure après |
|---|---|---|---|---|---|---|---|---|
| FND-001 | `49eeb2b6b524042c31021f84f1c72b7c` `d74d553c99fed54cae4db16d404e4169` `1051db88ffe98a2a02754f105ed9e534` | `appels-par-requete` | Le compte du registre est relu à chaque requête, et `DISCARD ALL` à chaque connexion (F2) | 2026-11-05 `task422` | confirmé | corrigé et mesuré | task-426 | `accounts` + ancre PSC : 5,94 → 0,03 appel par requête HTTP (−99,5 %) |
| FND-002 | `71f6575486dd8b4762cd373bb3aacd89` `b22ced34d5b099a2922831f66a11e122` → après : `840774b6aad35df6f93d47d8d971aca0` `28e9d819261554f956f0ee69032938d7` | `poids-dans-le-tir` | La recherche plein texte refait `lower()` du corps pour chaque terme (F1) | 2026-11-05 `task422` | confirmé | corrigé et mesuré | task-427 | temps SQL des formes de recherche −79 %. La forme d'après est ré-explorée et écartée au rejeu du 2026-11-07 |
| FND-003 | `e25db356be94a82ee5c4619e7473f2ff` | `colonne-volumineuse` | Les pièces jointes du dossier patient sont lues avec leur contenu | 2026-11-06 `apres` | confirmé | corrigé et mesuré | task-429 | lectures disque du tir 16,2 → 6,4 Go (−60 %) |
| FND-004 | `ac42e9c32aa51dc548795bf6a9692db0` | `sous-requete-correlee` | Le comptage de biologie parcourt la table par document (F-A) | 2026-11-06 `apres` | confirmé | corrigé et mesuré | task-430 | 144,3 → 82,3 Go lus par la forme (−43 %) |
| FND-005 | `2a14c9daf0b3eeb161b438a62f3eac73` | `sous-requete-correlee` | Les comptages d'étiquettes sont calculés trois fois (F-B) | 2026-11-06 `apres` | confirmé | corrigé et mesuré | task-430 | 91,0 → 3,7 Go lus par la forme (−96 %) |
| FND-006 | `8b53e22fb9e5951d2a2cd7da49917075` | `hors-détecteur` | Registre : la boîte de la personne, lue une fois par requête | 2026-11-06 `apres` | écarté | écarté | — | coût normal d'une recherche indexée d'une ligne (12 pages, 0,3 ms). Le poids vient de la fréquence, la réponse serait un cache |
| FND-007 | `9a63b74fac8c0708f158bb2588df9b57` | `colonne-volumineuse` | Le document médical est chargé entier, vecteur compris, à l'ouverture d'un message — **récidive** de FND-003 | 2026-11-06 `apres` | confirmé | ouvert | — | — |
| FND-008 | `e759630c6a29f7fe648e9fb10ab88668` | `hors-détecteur` | Npgsql recharge le catalogue des types à chaque connexion neuve | 2026-11-06 `apres` | — | ouvert | — | non exploré |
| FND-009 | `4b9380ddd1837d2bc365a5afbc833f85` | `colonne-volumineuse` | Le contenu du message est chargé avec son vecteur — **récidive** de FND-003 | 2026-11-06 `apres` | confirmé | ouvert | — | — |
| FND-010 | `9b0276b995554c73320b5caa00935e87` `90fed31c06a6aff57d1fb5c7c8d25a5d` | `pages-par-ligne` | La recherche vectorielle calcule la distance de chaque document de la boîte | 2026-11-06 `apres` | plausible | ouvert | — | à trancher par un tir sur des boîtes 10 fois plus grosses |

## Historique

- **2026-11-07 — amorçage (task-433)**.
  - FND-001 et FND-002 viennent de l'analyse manuelle du tir du 2026-11-05 (F1, F2).
  - FND-003 à FND-006 et FND-008 viennent de l'analyse manuelle du tir du 2026-11-06.
  - FND-007 était jugé « plausible, gain mineur » par la lecture manuelle. Le rejeu le confirme : le vecteur et les
    métadonnées sont lus et jamais affichés, la forme pèse 13,0 % du temps SQL et 33,1 % des lectures disque du tir,
    et le gain est borné à ≈ 13 % de la forme.
  - FND-009 et FND-010 sont trouvés par le rejeu, sans équivalent dans la lecture manuelle.
  - Section du rejeu : `Docs/audits/api-mail-loadtest-journey-courte-1400-1996-ab-findings-apres-20261106.md`,
    « Findings — analyse de code ». Plans : `Docs/audits/findings/plans/20261106-apres/`.
