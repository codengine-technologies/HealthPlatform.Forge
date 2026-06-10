# questions/task-068-sonar-newcoverage.md — Arbitrage Phase 1 : new_coverage structurellement hors périmètre

**Date** : 2026-06-10
**Étape** : `/sonar task-068` — Phase 1 (zero-new-debt), dernière condition du Quality Gate.

## État

Tout le new-code Quality Gate est vert **sauf** `new_coverage` :

| Condition new-code | Statut |
|---|---|
| Issues (bugs/vulns/smells) | ✅ 27 → 0 |
| Security hotspots | ✅ 0 à revoir |
| Ratings reliability/security/maintainability | ✅ A / A / A |
| Duplication | ✅ 0.02 % |
| **new_coverage** | ❌ **75.8 %** (gate : 80 %, cible `sonar-targets.yml` : 95 %) |

## Pourquoi c'est structurel

La période « new code » du projet SonarQube est `PREVIOUS_VERSION` **sans
version fournie par les analyses** → la baseline est figée à la **première
analyse de l'instance** (~3 semaines). Le « new code » mesuré couvre donc
tous les merges depuis (E009/E010, bulk delete, Redis sync, annuaire…), pas
seulement task-068.

Concrètement : 703 lignes new-code non couvertes réparties sur ~30 fichiers
(`RedisSyncStateStore` 106, `MailRepository` 111, `BaseRepository` 68,
`ImapConnectionService` 48, etc.). Le code introduit par task-068 est, lui,
couvert (14 tests unitaires dédiés ; les fichiers touchés par la task ne
portent plus que des reliquats marginaux).

Atteindre 80 % (a fortiori 95 %) exigerait d'écrire des tests sur des pans
entiers de code des tasks précédentes — exactement le mandat de la campagne
**wip-task-067** (E009, code-coverage-skill, en cours), et clairement hors
périmètre de task-068 (règle 6 — scopes isolés).

## Options

1. **(Recommandé) Accepter le résidu et poursuivre la chaîne** : la
   couverture du new-code hérité est traitée par la campagne task-067 ;
   `/sonar` consigne l'acceptation et enchaîne sur `/review task-068`
   (Phase 2 legacy best-effort pouvant être faite au passage ou sautée).
2. **Re-borner la période new-code** (action admin SonarQube, je peux
   l'exécuter) : `NUMBER_OF_DAYS=30` ou baseline `SPECIFIC_ANALYSIS` sur
   l'analyse courante, pour que les prochains runs mesurent un new-code
   par-task pertinent. Peut se combiner avec l'option 1. Note : re-borner
   sur l'analyse courante ferait mécaniquement passer le gate au prochain
   run — c'est un choix de gouvernance, pas un fix.
3. **Étendre task-068 à la couverture des 703 lignes** : déconseillé —
   chevauche task-067, explose le périmètre (~30 fichiers de plus dans la PR,
   limite des 30 fichiers/PR).

## Décision attendue

Choisir 1, 2, 1+2 ou 3. La chaîne `/sonar → /review` est en pause jusqu'à
réponse (zero-new-debt : pas de hand-off avec un gate new-code rouge sans
arbitrage humain).

## Réponse de l'humain (2026-06-10)

**Option 1+2 retenue** : résidu `new_coverage` accepté (couvert par la
campagne wip-task-067), chaîne débloquée vers `/review task-068` ; période
new-code re-bornée à `NUMBER_OF_DAYS=30` (appliquée au niveau branche `main`).
