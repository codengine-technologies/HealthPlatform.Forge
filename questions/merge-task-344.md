# merge-task-344 — `develop` rouge après le merge de #278

**Statut** : merge fait (PR #278 → `cbe15a23`), CI `develop` rouge, correctif en PR **#280** (`awaiting-human-merge`).

## Ce qui s'est passé
- 20:35 UTC : task-341 (#279) mergée. Elle ajoute `tests/mss.mail.application.tests/Ai/TaggingInvalidResponseLogHygieneTests.cs`,
  écrit sur l'ancien contrat `Task<List<TagSuggestionResult>> SuggestTagsAsync(...)`.
- 20:5x UTC : `/merge task-344 --i-tested`. #278 remplace ce contrat par `Task<TagSuggestionOutcome>`.
- Toutes les barrières de `/merge` étaient vertes : CI de la PR verte (sur sa propre tête), `mergeStateStatus = CLEAN`,
  `mergeable = MERGEABLE`. La PR avait pourtant **un commit de retard** sur `develop` : GitHub ne signale `BEHIND` que si
  la protection de branche exige d'être à jour, ce qui n'est pas le cas ici.
- Résultat : `develop` ne compile plus (`CS1503` ×2). Run : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/37233705234

## Décision 1 — merger #280
Correctif mécanique (`outcome.Tags`), aucune assertion changée, validé localement sur `develop` + correctif :
6 368 réussis, 16 ignorés, 0 échec.

## Décision 2 — une réponse illisible du modèle doit-elle être reprise ?
task-341 la compte comme un échec d'étiquetage (`mssante_tagging_failures_total{cause="invalid_response"}`). Le contrat de
task-344 la traite comme « le modèle a répondu sans étiquette » : le mail est marqué étiqueté et **n'est pas repris**.
- **Reprendre** (rendre `TagSuggestionOutcome.Failure`) : un modèle qui répond mal par intermittence finit par étiqueter ;
  un mail qui fait toujours répondre mal est ressayé toutes les 15 min pendant 7 jours (borné).
- **Ne pas reprendre** (état actuel) : aucun coût supplémentaire, mais le mail reste sans signalement d'urgence.
Recommandation : reprendre — c'est la même famille qu'un fournisseur indisponible, et le coût est borné.

## Décision 3 — prévention (règle d'or) : à relire avant d'être poussée, elle modifie la chaîne
La barrière 5 de `agents/merge.md` lit `mergeable` / `mergeStateStatus`, qui ne voient pas un retard sur `develop` quand
la protection de branche ne l'exige pas. Proposition :
1. Barrière 5 réécrite : `git rev-list --count HEAD..origin/develop` > 0 ⇒ **merger `origin/develop` dans la branche,
   rebuild + tests complets**, pousser, attendre la CI de la PR, puis seulement merger. Un retard n'est plus un refus mais
   une resynchronisation prouvée.
2. Option côté GitHub (décision humaine) : activer « Require branches to be up to date before merging » sur `develop`
   d'api-mail — GitHub ferait alors la barrière lui-même.
