---
description: Rédige les findings d'un tir de banc par analyse de code (site, plan, cause, gain borné, test) et tient leur registre
argument-hint: "{rapport.md} [--full] [--commit {sha}] [--task {task-id}]"
---

# /loadtest-findings — Findings de banc rédigés par analyse de code

Usage :
- `/loadtest-findings {rapport.md}` — explore les traitements coûteux du tir et ajoute au rapport la section
  « Findings — analyse de code ». Met à jour `Docs/audits/findings-registry.md`.
- `--full` — ignore le registre et ré-explore chaque candidat (rejeu de preuve, changement de méthode).
- `--commit {sha}` — le commit d'api-mail tiré, quand le journal du tir ne le donne pas.

Read `agents/loadtest-findings.md` and execute the full playbook :

1. Pré-vol : rapport, `pgstats-*.tsv`, commit du tir, Postgres du banc vivant, migrations depuis le tir.
2. Candidats, au plus 8 : `python Tools/loadtest-findings/findings.py candidates …`. Les formes signalées par
   task-431 passent d'abord, puis les plus coûteuses. Les findings réglés au registre sont remesurés, pas ré-explorés.
3. Pour chaque candidat :
   - lire le SQL complet ;
   - retrouver le site au commit du tir (`site=` de task-432, sinon recherche citée) ;
   - jouer le plan sur une base du banc (`explain`, `column-sizes` pour une colonne volumineuse) ;
   - juger, borner le gain, proposer le correctif et son test (règle 1b) ;
   - rendre un verdict confirmé, plausible ou écarté.
4. Récidive : nommer la prévention qui a manqué.
5. Rédiger la section sur le modèle du playbook.
6. **Contrôle de non-confabulation, bloquant** : `findings.py check …`, 0 écart exigé.
7. Mettre à jour le registre, sans doublon.
8. Proposer à l'humain. **Ne jamais rédiger de task** : l'humain choisit, puis `/po`.

## ⏱️ Instrumentation (obligatoire)

```bash
Tools/timing/step.sh start --task {task-id ou -} --step loadtest-findings
Tools/timing/step.sh end --task {task-id ou -} --step loadtest-findings --status ok
```

`--status skipped --note "{raison}"` quand le pré-vol refuse (pas de `pgstats`, banc arrêté avant l'étape).

## Rules

- **Hors chaîne autonome** : jamais invoqué par `/start` → `/review`, et n'invoque aucune étape (règle 13 inchangée).
- **Preuves exigées** : chaque chiffre vient du `pgstats` du tir, chaque `fichier:ligne` du commit du tir, chaque
  ligne de plan d'un plan sauvegardé. Sans plan ni site, le verdict est au mieux plausible.
- **Bases du banc uniquement** : aucun plan sur une base réelle, même en lecture. L'outil refuse toute autre base.
- **Aucune valeur de ligne** dans les findings ni dans les plans : textes normalisés, plans génériques (`$1`),
  compteurs.
- **Gain borné** par le coût de la forme sur le tir. Un effet sur le temps de réponse s'annonce « à mesurer par A/B ».
- **L'humain décide** : la forge propose, l'humain choisit, `/po` rédige.
