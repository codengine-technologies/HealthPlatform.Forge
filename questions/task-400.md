# task-400 — /e2e bloqué : outillage (ports du banc occupés)

**Nature du blocage : outillage.** Ni régression, ni écart de parité constatés : les voies n'ont pas pu
démarrer.

## Constat (2026-10-27)

- Le port **5052** est tenu par `dcp.exe` (PID 70596), le contrôleur Aspire de l'AppHost lancé sur le poste.
- Le port **4200** est tenu par un `node.exe` (PID 56544), le serveur de dev weda2.
- Les deux voies e2e (mobile et Angular) publient 5052 ; la voie Angular sert aussi weda2 sur 4200.
- La forge n'arrête pas les processus de l'humain : aucune voie n'a été jouée.

## État de la task

Tout le reste de la chaîne est vert :

- `/develop` : contrat `dtos-mss` 547.0.0 publié ; api-mail poussé ; weda2 écrit (code seul, non commité) ;
- `/sonar` : QG OK, 0 défaut sur le nouveau code, new coverage 95,1 % ;
- `/lint-angular` : 0 erreur ; `/lint-mobile` : sans objet.

Le parcours **E2E-DELEG-008** (nouveau) est écrit et typé, mais n'a encore jamais tourné : sa preuve par
mutation reste à faire au premier passage de la voie Angular.

## Décision demandée

Libérer les ports 5052 et 4200 (arrêter l'AppHost et le serveur de dev weda2), puis relancer :

```
/e2e task-400
```

La chaîne reprend seule (`/review`, puis `/tech-writer`) si les voies sont vertes. Si tu préfères ne pas
rejouer les parcours pour cette task, c'est ton seul arbitrage : écrire à la main, sous `**Repos**:`,
`**E2E**: bypass — décision humaine du {date}`, puis lancer `/e2e task-400`.
