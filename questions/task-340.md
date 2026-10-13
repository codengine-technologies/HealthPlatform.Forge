# questions/task-340.md — `/e2e` rouge : E2E-AI-001 (mobile), régression probable introduite par la task

**Étape** : `/e2e task-340` (après `/develop`, `/sonar`, `/lint-angular`, `/lint-mobile`, tous verts).
**Nature du blocage** : **régression** (probable, introduite par les parcours e2e de la task), pas un
défaut fonctionnel de l'accusé de lecture.
**Chaîne** : arrêtée avant `/review`. Aucune PR ouverte.

## Constat

- Voie **mobile** : 33 verts, **1 rouge** — `E2E-AI-001` (« assistant — résumé initial puis deux
  questions de suite »), rouge **aux deux essais**, sur la même assertion :
  `live-ai.spec.ts:84` — après un appui long sur la ligne seedée `mail-non-lu`, le mode sélection ne
  s'ouvre pas (`selection-cancel-btn` absent). L'instantané d'échec montre l'onglet **Patients**
  affiché.
- E2E-AI-001 était **vert** sur la voie mobile de task-367 (2026-10-11), sur le même seed.
- Voie **weda2** : verte (37 verts, 1 flaky E2E-COMPOSE-001, consigné au registre). Parité verte des
  deux côtés. Les trois parcours E2E-RECEIPT-001/002/003 sont **verts sur les deux clients**.

## Diagnostic (non encore prouvé par un rejeu)

Les parcours mobiles de la task **laissent deux messages de plus en tête de la boîte** :

- E2E-RECEIPT-001 : le message envoyé à « Robert E2E » (le praticien lui-même), jamais supprimé ;
- E2E-RECEIPT-002 : l'accusé « Lu: … » reçu dans la boîte, jamais supprimé.

Or la suite mobile pose en tête : « Les tests mutants remettent l'état d'origine » (E2E-COMPOSE-001
supprime son message, par exemple). E2E-AI-001, joué plus tard (`live-ai.spec.ts`), fait un appui long
sur `mail-non-lu`. Avec deux lignes de plus au-dessus, la ligne descend en bas de l'écran.
`gestureBox` la fait défiler jusqu'à la rendre « visible », mais la **barre d'onglets Ionic la
recouvre** : l'appui tombe sur l'onglet « Patients », d'où l'écran Patients de l'instantané.

## Correctif proposé (dans le périmètre de la task, côté tests e2e seulement)

Les parcours remettent l'état d'origine, comme le reste de la suite :

1. E2E-RECEIPT-001 (mobile **et** weda2) : supprimer, en fin de parcours, le message envoyé
   (`OtherDevice.deleteMessage(uid)`, déjà utilisé par E2E-LIVE-001 ; à ajouter côté weda2 si
   absent).
2. E2E-RECEIPT-002 (mobile **et** weda2) : supprimer l'accusé « Lu: … » une fois son arrivée
   constatée.
3. Rejouer les deux voies complètes : E2E-AI-001 mobile doit redevenir vert, et la preuve du
   diagnostic est qu'il le redevienne **sans autre changement**.

Option complémentaire, hors task (filet) : rendre `gestureBox` insensible à la barre d'onglets
(défiler la ligne au centre de la liste plutôt qu'au bord), pour qu'un test ne dépende plus du nombre
de messages laissés par les autres.

## Décision demandée à l'humain

`/e2e` est en lecture seule : la forge ne corrige rien à cette étape. Deux possibilités :

- **(recommandé)** relancer `/develop task-340` pour appliquer le correctif ci-dessus (nettoyage des
  deux parcours, mobile et weda2), puis la chaîne reprend (`/sonar` → … → `/e2e` → `/review`) ;
- ou corriger à la main, puis relancer `/e2e task-340`.

## État des dépôts

- dtos-mss, api-mail, client-blazor, client-mobile : tout est commité et **poussé** sur
  `fix/task-340-accuse-de-lecture` (rien de non commité).
- client-angular : modifications **non commitées** sur `feature/nova-rewriting-mss-weda-integration`
  (liste au `## Develop log`) — code-only, à commiter sur TFS par l'humain.
- Le `## E2E log` complet (verdict, listes, matrice de parité) est dans `tasks/wip-task-340.md`.

## Résolution (2026-10-13)

Décision humaine : relancer `/develop task-340`. Correctif appliqué (nettoyage des parcours E2E-RECEIPT-001/002, mobile et weda2), diagnostic confirmé (E2E-AI-001 vert derrière les parcours RECEIPT, seed neuf). Chaîne relancée.
