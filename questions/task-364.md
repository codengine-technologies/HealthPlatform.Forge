# questions/task-364.md — /e2e bloqué en outillage : ports du banc tenus par la session de dev

**Étape** : `/e2e task-364`, pré-vol, avant de lancer la première voie.
**Nature du blocage** : **outillage** (règle 4 de `agents/e2e.md`). Ce n'est ni une régression ni un écart de parité : aucune voie n'a pu être jouée.

## Constat (2026-10-10, ~18:45)

- Les deux voies doivent tourner, puisque la task touche `api-mail` (catalogue) et `client-angular`.
- Ports du banc e2e déjà à l'écoute :
  - `5052` (127.0.0.1 et ::1) : `dcp.exe` PID 51296, l'AppHost Aspire de dev lancé à 16:52 (5 réplicas `mss.mail.api` sous `bin/Debug`) ;
  - `4200` (::1) : `nx serve weda2` PID 8716 (votre serveur Angular de dev).
- La forge n'arrête pas vos processus : c'est votre session de travail. Elle ne lance pas non plus la voie, qui jouerait contre votre serveur de dev ou sortirait en `EADDRINUSE` (`conventions/e2e.md` › `garde-de-port-ipv4-seul`).

## Décision attendue

1. Arrêter l'AppHost de dev (Ctrl+C dans son terminal, ou arrêt depuis Rider / VS) et `nx serve weda2`.
2. Relancer `/e2e task-364`. La chaîne reprend ensuite d'elle-même : `/review`, puis `/tech-writer`.

## Ce que `/e2e` fera à la reprise, en plus du verdict

- La **preuve par mutation d'E2E-DETAIL-004**, différée au `## Develop log` pour cette raison :
  - remettre `min-height: 60vh` sur le corps → « un seul défilement » doit tomber ;
  - neutraliser le redéploiement par message → « le message suivant redéplie le panneau » doit tomber.
- Les captures avant / après, prises par la voie (panneau ouvert, masqué, lecture étroite).

## État des repos au moment de l'arrêt

- `api-mail` : `feat/task-364-lecture-panneau-actions`, `941f9c4a` poussé (catalogue E2E-DETAIL-004 seul).
- `client-angular` : `feature/nova-rewriting-mss-weda-integration`, changements **non commités** (liste dans le `## Develop log`). Build ✓, 11 projets de tests ✓, lint 0 erreur.
- Rien à défaire. La task reste en `wip-task-364.md`.

## Pour information, à arbitrer en revue (non bloquant ici)

Cinq écarts à la DOD sont consignés au `## Develop log`. Les deux principaux :
- la section Étiquettes reste affichée même vide, pour garder l'ajout d'une étiquette ;
- E2E-DETAIL-004 joue le mode rail en 1366×768, comme le veut le seuil de 1 000 px, et la partie « déplié » en 1920×1080.
