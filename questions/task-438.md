# task-438 — /e2e bloqué : outillage (port 5052 occupé)

**Nature du blocage** : outillage, pas une régression ni un écart de parité. Aucune voie n'a été jouée.

## Constat (2026-11-09)

- `/e2e` démarre son propre backend sur le port **5052**. Ce port est tenu par `dcp` (pid 49736), le
  contrôleur de l'**AppHost Aspire de développement** de l'humain, lancé pour la campagne de recherche sur la
  boîte de Virginie. On voit aussi `mss.mail.AppHost.exe` (pid 55960) et 5 processus `mss.mail.api`.
- Les autres ports du banc sont libres : 8100, 3993, 3465, 3143 et 47399.
- La forge n'arrête pas un AppHost lancé par l'humain.

## État de la chaîne

| Étape | Résultat |
|---|---|
| `/develop` | vert, poussé (api-mail `079da993`…, client-mobile `ba3e1ae`), Angular non commité (code-only) |
| `/sonar` | Quality Gate OK, 0 nouvelle issue après correction (`8293f042`) |
| `/lint-angular` | 0 erreur |
| `/lint-mobile` | 0 erreur |
| `/e2e` | **non joué, port 5052 occupé** |
| `/review`, `/tech-writer` | en attente |

## Ce qu'il faut à l'humain

Arrêter l'AppHost de développement (Ctrl+C dans son terminal, ou arrêt depuis l'IDE), vérifier que le port 5052
est libre, puis relancer :

```
/e2e task-438
```

`/e2e` jouera les deux voies (mobile, puis Angular), dont E2E-SEARCH-002 et E2E-SEARCH-003, ajoutés par la task.
Puis la chaîne reprendra `/review`, puis `/tech-writer`. La preuve par mutation des deux nouveaux scénarios
(règle 1b, côté frontend) sera faite pendant ce passage.
