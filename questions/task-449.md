# task-449 — /review passage 3 : CHANGES REQUESTED, plafond de reprises atteint

**Étape** : `/review`, 3ᵉ passe (revue indépendante, 2026-11-12), après deux reprises automatiques. Build, tests,
Sonar (QG OK, 0 issue), `/e2e` (mobile 61, angular 84, parité verte) : verts. B1, B2, B3, S2, S3, S8, S9, S10, S12, S13,
S14, S15 : corrigés et prouvés rouges. La PR n'est **pas** ouverte. La task reste en `wip-*` (`**Reprises**: 2`).

## Bloquants (passe 3)

### B4 — Une demande de suggestions part liste fermée, et trace des patients jamais montrés

- Le correctif de B3 fait appeler `suggestions.update(criteria.query)` par `restoreCriteria`
  (`mail-search.component.ts:562`). Quand le texte remis a au moins deux caractères, une demande part 250 ms plus tard,
  liste fermée. Le serveur trace toute réponse qui nomme un patient (« N patient(s) proposé(s) »).
- Scénario : rechercher « bernard », ouvrir un mail, revenir : la barre suit la recherche affichée
  (`followShownSearch` → `restoreCriteria`) et une demande cachée part. Le journal dit que des patients ont été montrés
  au médecin ; ils ne l'ont pas été. Même chose sur Échap après une saisie, et au rejeu d'une recherche récente.
  Contraire à la règle 14 (traçabilité exacte).
- Correctif attendu : `restoreCriteria` remet l'état des suggestions **sans rien demander** (`clear()`), et
  `openDropdown` demande les suggestions du texte courant à l'ouverture. Test : aucune demande liste fermée après la
  restauration d'un texte de deux caractères ou plus.

### B5 — Un clic droit ou un clic molette sur un patient suggéré ouvre son dossier

- `MailSearchSuggestionsComponent.onChoose` (`mail-search-suggestions.component.ts:133`) réagit à `mousedown` sans
  regarder le bouton : un clic droit (menu contextuel) ou molette (habitude d'ouvrir dans un onglet) ouvre la vue
  « Mails du patient », consultation tracée.
- Correctif attendu : ne choisir qu'au bouton principal (`button === 0`). Test : clic droit sans effet.

## Suggestions (même reprise)

- **S16** — `launch()` ignore la règle « un patient ou un type se choisit » : avec `patient : bern` dans la barre, le
  bouton « Lancer la recherche » ou Entrée dans le champ « De » lancent quand même une recherche plein texte.
- **S17** — à la réouverture, l'ancienne liste de recherches récentes reste affichée pendant le rechargement ; ↓ + Entrée
  peut rejouer une autre recherche que celle désignée. Remettre la désignation à zéro quand la liste est remplacée.

## Arbitrage humain (inchangé)

- **S11** — un « Effacer » dans la catégorie « Recherches récentes » (poste partagé) ?
- **S4 / S5** — aligner les critères tapés (`de :`, `à :`, `objet :` puis Entrée) sur les suggestions (nom et adresse,
  accents ignorés) ?
- **S6 / S7** — un préfixe qui remplace un critère déjà posé, ou qui prend toute la fin de la saisie : combiner,
  refuser, ou couper au guillemet ?

## Pourquoi la chaîne s'arrête

Deux reprises automatiques ont été faites (plafond de la règle 13, reprise automatique après revue). Chaque passe a
trouvé un défaut **nouveau** de la même famille (une suggestion choisie ou tracée sans que le médecin l'ait voulu),
souvent introduit par le correctif précédent. Ce n'est pas un échec de correction, c'est le signe que la conception de
l'état des suggestions mérite d'être reprise d'un bloc.

## Reprise

`/develop task-449 --reprise` corrige B4, B5, S16, S17 (chaque correctif vu rouge), puis la chaîne reprend jusqu'à
`/review`. Recommandation forge : traiter les suggestions comme **dérivées de la liste ouverte** (aucune demande, aucune
désignation, aucun choix tant qu'elle est fermée), en une seule règle dans `MailSearchSuggestions`, plutôt que chemin par
chemin.
