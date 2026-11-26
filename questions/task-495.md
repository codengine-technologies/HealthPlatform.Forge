Résolu le 2026-11-26 : plage libérée par l'humain, `/e2e task-495` rejoué vert (voie Angular 102 verts, 1 flaky).

# task-495 — /e2e rouge : outillage (port 47399 réservé par Windows)

**Étape** : `/e2e`, voie Angular (weda2).
**Nature** : **outillage**, pas régression, pas parité.

## Constat

- Voie mobile : verte (80/80, parité verte).
- Voie Angular : 96 verts, 1 flaky, **6 rouges**. Ce sont les six parcours Weda embarqué (E2E-WEDA-001, 002, 003,
  E2E-MAILBOX-001 embarqué, E2E-SESSION-001, 003). Tous échouent au démarrage de l'hôte Weda factice, avec la même
  erreur : `listen EACCES: permission denied 0.0.0.0:47399`.
- Aucun processus n'écoute sur 47399. Le port est dans une plage TCP **réservée par Windows** :
  `netsh interface ipv4 show excludedportrange protocol=tcp` affiche 47394–47493. Cette plage est posée
  dynamiquement par WinNAT / Hyper-V, typiquement au redémarrage des services réseau de Docker.
- Les scénarios de la task (E2E-SHARED-004 et 005) sont verts sur les deux voies. La parité est verte et le
  démontage est complet.

## Ce qu'il faut faire (droits administrateur, hors de portée de la forge)

Au choix :
1. Libérer la plage : `net stop winnat` puis `net start winnat`, dans un terminal administrateur. Docker Desktop
   peut avoir besoin d'être redémarré ensuite.
2. Redémarrer le poste.

Vérifier ensuite que 47399 n'apparaît plus dans `netsh interface ipv4 show excludedportrange protocol=tcp`. Relancer
alors `/e2e task-495` : la voie mobile, inchangée, est réutilisée (`lane_cache.py`) ; seule la voie Angular rejoue.
La chaîne reprend ensuite d'elle-même (`/review` → `/tech-writer`).

## Décision attendue

Aucune décision métier. Seulement l'action poste ci-dessus, puis la relance de `/e2e task-495`.

Prévention à arbitrer (changement de chaîne, à relire avant push) : faire tester le port 47399 par le pré-vol de
`agents/e2e.md`, en plus de `netstat` (plages réservées comprises), et faire dire à la voie Angular « outillage »
plutôt que « rouge ».
