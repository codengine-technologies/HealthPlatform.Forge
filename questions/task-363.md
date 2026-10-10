# questions/task-363.md — `/e2e` bloqué : outillage (ports tenus par les serveurs de développement)

**Nature du blocage : OUTILLAGE.** Aucun parcours n'a été rejoué. La non-régression **n'est pas
prouvée**, et le nouveau parcours E2E-WEDA-002 n'a encore jamais tourné.

## Constat (2026-10-10, 13 h 50 environ)

Le filet e2e publie des ports fixes. Deux d'entre eux sont tenus par tes serveurs de
développement, démarrés à 12 h 50 :

| Port | Processus | Rôle |
|---|---|---|
| 5052 | `dcp.exe` de `mss.mail.AppHost` (PID 63276) | backend api-mail de dev |
| 4200 | `node` (PID 49016), sur `Client/Angular/front` | `nx serve` de weda2 |

Le port 5052 est codé en dur dans `Client/Mobile/e2e/headless/run.mjs` et dans
`Client/Angular/front/e2e/mss-e2e/proxy.e2e.conf.json`. Le 4200 est l'origine de weda2 en e2e. La
forge n'arrête pas tes serveurs.

L'AppHost verrouille aussi `Api/Mail/src/Api/bin`. Pendant `/develop`, la suite api-mail a donc
été compilée dans `Api/Mail/artifacts/forge-363`, dans le dépôt et gitignoré (voir le Develop log).
`/review` devra rejouer build et tests **dans `bin`**.

## Ce qui est prêt

- `/develop` est terminé : code client-angular non commité, et `2aff4aff` poussé sur
  `feat/task-363-weda-import-documents` (profil e2e et catalogue E2E-WEDA-002).
- `/sonar` est sauté (aucun code de production analysable). `/lint-angular` : 0 erreur.

## Décision attendue

1. **Arrêter ton AppHost et ton `nx serve`**, puis relancer `/e2e task-363`. La chaîne reprend
   alors seule jusqu'à `/review` et `/tech-writer`. C'est la voie normale.
2. Ou les garder, si tu testes la partie Weda en ce moment. `/e2e task-363` se relance plus tard,
   sans rien perdre : la task reste en `wip-*`.

Point à savoir pour la reprise : E2E-WEDA-002 n'a jamais tourné. Un premier rouge sur ce test
neuf est possible, et il serait corrigé en reprise `/develop`, comme pour E2E-WEDA-001 sur
task-362.
