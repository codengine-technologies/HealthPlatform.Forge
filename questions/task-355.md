> **Réponse du responsable produit (2026-10-08) : A**, le parallélisme seul. Le commit du gabarit est
> retiré (`c456a028`) et la chaîne reprend à `/sonar`. La question du seuil de la garde reste ouverte.

# questions/task-355.md — la garde qualité du nouveau gabarit d'étiquetage échoue

**Étape** : `/develop`, garde qualité de la DOD (règle métier « garde qualité, bloquante »).
**Décision attendue de** : responsable produit.
**Tout le reste de la DOD est fait.** Détail dans le `## Develop log` de `tasks/wip-task-355.md`.

## Le constat

Ancien contre nouveau gabarit, `qwen2.5:14b` local, 200 contenus cliniques tirés de `JEUX_TESTS_FULL` :

| Comparaison | Concordance | Sens des écarts |
|---|---|---|
| ancien contre ancien rejoué (bruit du modèle) | 92,5 à 96,0 % | équilibré |
| **ancien contre nouveau** | **89,5 à 94,0 %** | **le nouveau étiquette moins** |
| ancien contre nouveau, température 0 | 93,5 % | **13 descentes, 0 montée**, deux fois |

- Étiquettes posées sur 200 mails : ancien 39 à 41, nouveau 31 à 37.
- « Urgent » : 20 à 24 avec l'ancien, 15 à 17 avec le nouveau.
- Réponses illisibles : 0 ou 1, des deux côtés.

Le seuil de 95 % n'est jamais atteint. Il est d'ailleurs au niveau du bruit du modèle contre
lui-même. Mais l'écart n'est pas du bruit : il va toujours dans le même sens. Déplacer le type de
document et l'expéditeur après la grille rend le modèle **moins enclin à étiqueter**, sur ~6 %
des mails. C'est la direction du sous-triage. Le corpus n'a pas de vérité terrain, donc rien ne
dit lequel des deux gabarits a raison.

## Ce que l'arbitrage change

| Option | Débit à P=4 | Effet clinique | Branche |
|---|---|---|---|
| **A. Livrer le parallélisme seul** (retirer le commit `75e214c3` et sa note de doc) | **45,6 /min** : marge quasi nulle face à ~44 /min, critère DOD « ≥ 70 » non tenu | aucun | revert d'un commit, puis la chaîne reprend |
| **B. Livrer le nouveau gabarit malgré l'écart** | **79,3 /min** | ~6 % de mails étiquetés plus bas ou pas du tout | rien à changer, la chaîne reprend |
| **C. Chercher un ordre qui garde le cache sans l'écart** (par exemple, rappeler le type de document dans l'introduction constante, ou mettre le contexte juste avant le contenu avec une consigne « applique la grille ci-dessus ») | à mesurer | à mesurer, même garde | nouvelle itération de `/develop` |
| **D. Juger sur une vérité terrain** : faire étiqueter à la main les ~25 mails discordants, et livrer le gabarit le plus juste | selon le résultat | décidé sur preuve | quelques heures d'un médecin |

**Recommandation de la forge : C, puis D si C ne ferme pas l'écart.** A annule l'essentiel du gain,
et B accepte un écart dans le mauvais sens sans savoir qui a raison.

## État des dépôts

- `api-mail` : branche `feat/task-355-ollama-parallele-gabarit-prefixe` **poussée**, 4 commits
  (feature ×2, passe qualité, documentation). Arbre propre. Aucune PR ouverte.
- Plan de contrôle : `tasks/wip-task-355.md` (Develop log), le script
  `Docs/audits/ollama-bench-20261008/guard.py` et ses résultats, non commités.
- Banc : `ollama-bench` supprimé. `mss-mail-ollama` tourne avec `OLLAMA_NUM_PARALLEL=4`.

## À trancher aussi : le seuil de la garde

Avec ce modèle à la température par défaut, deux passes du **même** gabarit ne concordent qu'à
93 à 96 %. Un seuil de 95 % fait donc échouer un gabarit identique environ une fois sur deux.

Proposition pour les prochaines US de gabarit :
- juger à **température 0** ;
- **contre le bruit mesuré** de l'ancien gabarit rejoué ;
- et sur le **sens** des écarts : aucune descente systématique.

Pour reprendre : répondre ici, puis relancer `/develop task-355` (option C) ou `/sonar task-355`
(options A, après le revert, ou B).
