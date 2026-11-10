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
| FND-007 | `9a63b74fac8c0708f158bb2588df9b57` → après : `bc5acb2c69c5d6799de85c3fd161a904` | `colonne-volumineuse` | Le document médical est chargé entier, vecteur compris, à l'ouverture d'un message — **récidive** de FND-003 | 2026-11-06 `apres` | confirmé | corrigé et mesuré | task-434 | A/B du 2026-11-08 (`t434-task` contre `t434-controle`) : forme d'avant 168 539 → 20 appels (reste : voie du bus) ; forme d'après sans vecteur, pages lues 24,4 → 19,3 Go (−21 %), lectures disque inchangées (`HtmlBody`, servi). Mergée le 2026-11-08 (PR #352) |
| FND-008 | `e759630c6a29f7fe648e9fb10ab88668` | `hors-détecteur` | Npgsql recharge le catalogue des types à chaque source de données neuve | 2026-11-06 `apres` | écarté | écarté | — | 2026-11-08 `t434-task` : coût de démarrage, une fois par réplica et par base (sources de données en cache par processus, `BaseRepository.GetOrCreateDataSource`) : 6 035 appels pour 1 041 bases |
| FND-009 | `4b9380ddd1837d2bc365a5afbc833f85` → après : `2a6ce021d70dc17b91701c8f338e7a6f` | `colonne-volumineuse` | Le contenu du message est chargé avec son vecteur — **récidive** de FND-003 | 2026-11-06 `apres` | confirmé | corrigé et mesuré | task-434 | A/B du 2026-11-08 : forme d'avant absente ; forme d'après 37,6 → 23,4 s, pages lues 11,5 → 6,3 Go (−45 %). Mergée le 2026-11-08 (PR #352) |
| FND-010 | `9b0276b995554c73320b5caa00935e87` `90fed31c06a6aff57d1fb5c7c8d25a5d` | `pages-par-ligne` | La recherche vectorielle calcule la distance de chaque document de la boîte | 2026-11-06 `apres` | confirmé | task | task-437 | 2026-11-09, boîte de 11 178 mails contre 156 : contenus 2,2 → 296 ms (×133), documents 2,4 → 16 ms ; aucun index sur `Embedding`. **Après (laboratoire, 2026-11-10, copie de la boîte de 11 178 mails)** : index HNSW `halfvec`, contenus 157 → 12 ms (38 312 → 1 986 pages), documents 11,6 → 4,9 ms, rappel@10 97,9 % / 98,8 % sur 24 vraies phrases ; statut à passer en « corrigé et mesuré » au merge |
| FND-011 | `4c9c73a7b84af06ddf5fcf9b73b3c7ab` | `colonne-volumineuse` | Le téléchargement d'une pièce jointe lit son contenu | 2026-11-08 `bilan-apres` | écarté | écarté | — | faux positif connu de D2 : le contenu est servi sur la route qui le rend. Sa part du disque (29,5 %) relève du stockage des pièces jointes |
| FND-012 | `5148cb399674048f3066e09be6ab72ed` | `hors-détecteur` | L'écriture du journal d'audit, une trace par lot | 2026-11-08 `bilan-apres` | écarté | écarté | — | 13 pages par ligne = tas + 3 index + trigger : coût normal. 1,02 trace par lot, grouper n'économiserait que les transactions |
| FND-013 | `8f9a23fbdfe763775fed3766b575821b` | `hors-détecteur` | La résolution des doublons actifs | 2026-11-08 `bilan-apres` | écarté | écarté | — | tout par index, 16 pages par appel. Le poids vient de la fréquence |
| FND-014 | `a5978bf1120a527de14ca8d1c8283f21` | `hors-détecteur` | Les messages qui citent un fil sont cherchés par `LIKE '%…%'` sur `References` | 2026-11-08 `bilan-apres` | confirmé | ouvert | — | 2026-11-09, boîte de 11 178 mails : 5 → 433 pages, 0,13 → 2,1 ms par page de liste. Linéaire, coût faible à 11 000 mails : priorité basse |
| FND-015 | `9ecf42a479e49a52787a30295de1f894` | `hors-détecteur` | Les acquittements de biologie | 2026-11-08 `bilan-apres` | écarté | écarté | — | 3 pages, balayage préféré à l'index sur 119 lignes : coût normal à cette taille |
| FND-016 | `38927728f1f6554f6d1a7c88063a13be` | `hors-détecteur` | Les messages d'une page, lus par UID | 2026-11-08 `t434-task` | écarté | écarté | — | 5 pages, index présent, balayage préféré sur 156 lignes : coût normal |
| FND-017 | `be95a8c47cbdd9a4824f427030e5ec35` | `hors-détecteur` | Les étiquettes d'un message | 2026-11-08 `t434-task` | écarté | écarté | — | index `IX_MailTags_MailId_TagId` présent, balayage préféré sur 248 lignes : le poids vient de la fréquence |
| FND-018 | `11c8c9fdd0b35ceb0f59532bd9ba2471` | `hors-détecteur` | Les résultats de biologie marqués d'une page | 2026-11-08 `t434-task` | écarté | écarté | — | index présent, balayage préféré sur 119 lignes : coût normal |

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
- **2026-11-08 — tir `bilan-apres` (A/B/A bilan du lot, code `5b4e394f`)**. Premier usage en mode normal.
  - FND-003 et FND-005 : formes absentes, les correctifs tiennent.
  - FND-007 et FND-009 re-confirmés. FND-007 passe de 33,1 % à 52,4 % des lectures disque, par report après FND-003.
  - FND-010 reste plausible. FND-014, nouveau, est de la même nature : un coût qui croît avec la boîte.
  - FND-011, FND-012, FND-013 et FND-015 sont écartés.
  - Finding d'instrument : « Émise par » est le premier site vu par base, pas une répartition.
  - Section : `Docs/audits/api-mail-loadtest-journey-courte-1400-1996-bilan-apres-20261108.md`. Plans :
    `Docs/audits/findings/plans/20261108-bilan-apres/`.
- **2026-11-08 — décision de l'humain** : FND-007 et FND-009 en une seule task, `task-434`, avec la garde de toute la
  classe `colonne-volumineuse`.
- **2026-11-08 — tir `t434-task` (A/B de task-434, code `dfda613b`)**.
  - FND-007 et FND-009 : formes d'avant disparues (FND-007 garde 20 appels de la voie du bus), formes d'après
    ajoutées à leurs lignes. Le reste du coût du document est `HtmlBody`, servi : piste « HTML au dépliage » proposée.
  - FND-008 écarté (coût de démarrage). FND-010 et FND-014 restent plausibles.
  - FND-016, FND-017 et FND-018, nouveaux, écartés.
  - Section : `Docs/audits/api-mail-loadtest-journey-courte-1400-1996-t434-task-20261108.md`. Plans :
    `Docs/audits/findings/plans/20261108-t434-task/`.
- **2026-11-08 — `/merge` de task-434** : FND-007 et FND-009 passent en `corrigé et mesuré` (PR #352).
- **2026-11-09 — temps 1 du plan de volumétrie (plans rejoués, aucun tir)**. Boîte de formation de Virginie
  (11 178 mails) contre la plus grosse base du banc (156 mails), 12 formes du tir du 2026-11-08 17:48.
  - FND-010 confirmé, la forme sur les contenus est la plus lourde de la grosse boîte (×133 en temps). Décision de
    l'humain : `task-437` (index, précision approchée sous un plancher de 95 %).
  - FND-014 confirmé linéaire, coût faible : reste ouvert, priorité basse.
  - La forme d'après de FND-002 (`840774…`, plein texte des contenus), écartée au rejeu du 2026-11-07, croît avec la
    boîte (×137 en pages) : rouverte par `task-436`, sans changer de ligne au registre. task-436 a été absorbée le même jour par `task-439`
    (EPIC E022, refonte du plein texte), qui reprend son seuil de coût.
  - Rapport : `Docs/audits/api-mail-volumetrie-plans-boite-11k-20261109.md`. Plans :
    `Docs/audits/findings/plans/20261109-volumetrie-boite-11k/`.
