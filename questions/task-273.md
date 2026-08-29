# task-273 — recouvrement avec task-270 (PR #205) : deux implémentations concurrentes du même remède

**Date** : 2026-08-29
**Découvert par** : /tech-writer (lecture du changelog v1.64) — APRÈS ouverture de la PR #206
**Gravité** : aucun code mergé n'est en cause ; l'arbitrage porte sur DEUX PRs ouvertes en conflit

## Constat

- **task-270** (`done`, PR api-mail [#205](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/205), `awaiting-human-merge`) a déjà fusionné le chemin froid de `GET /folders/{name}` : 7 → 5 allers-retours, **un seul verrou de session**, + remède `today` (re-validation à 2 commandes au lieu d'une re-recherche à 5).
- **task-273** (`done`, PR api-mail [#206](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/206), `awaiting-human-merge`) a ré-implémenté **indépendamment** la même fusion (branche partie de `develop`, qui ne contient pas #205), + pollinisation LIST-STATUS → `folder:status` (absente de 270), + dossier de cause complet, + tests d'intégration DOD (2 arrivées, cache menteur), + nouvelle famille de verrou `GetFolderRead`.
- Les deux PRs modifient **les mêmes fichiers** (`ImapService.cs`, `ImapDashboardCachingTests.cs`, `ImapServiceFolderStatusSolicitationTests.cs`) : la seconde mergée aura des conflits.
- Défaut de processus côté forge (consigné) : `/develop task-273` n'a pas balayé les `done-*`/PRs ouvertes touchant la même zone avant d'implémenter.

## Ce que chaque PR apporte que l'autre n'a pas

| | #205 (task-270) | #206 (task-273) |
|---|---|---|
| Fusion 7→5 RTT, verrou unique | ✅ | ✅ (ré-implémentée) |
| `today` : re-validation 2 cmds au lieu de re-recherche 5 cmds | ✅ | ❌ |
| Pollinisation LIST-STATUS → `folder:status` (tous dossiers) | ❌ | ✅ |
| Dossier de cause (verrou/IMAP/base/matérialisation) dans la task | partiel | ✅ |
| Tests d'intégration DOD (2 arrivées = 0 RTT ; cache menteur) | ❌ | ✅ |
| Famille de verrou dédiée `GetFolderRead` (lecture campagne) | ❌ (garde les familles existantes) | ✅ |

## Arbitrage demandé (recommandation en 1)

1. **Merger #205 d'abord, puis la forge retravaille la 273 par-dessus** :
   `/merge 270 --i-tested` (ou merge manuel), puis la forge merge `develop`
   dans `feat/task-273-dashboard-folder-cost`, résout les conflits en
   **gardant la fusion de 270** et en ne conservant de 273 que ses apports
   propres (pollinisation, tests d'intégration, famille de verrou si souhaité),
   re-valide, re-pousse — la PR #206 devient additive et propre.
2. **Merger #206 et fermer #205** : perd le remède `today` de 270 (à
   re-porter), et jette une implémentation déjà validée — déconseillé.
3. **Fermer #206** : perd la pollinisation et les tests DOD de 273 — la task
   273 repartirait en `todo` avec un périmètre réduit aux apports propres.

Dans tous les cas : **ne pas merger les deux PRs en l'état**.

## État laissé par la forge

- task-273 reste `done-*`, PR #206 ouverte, avertissement posé en commentaire
  sur les deux PRs.
- Le changelog E015 v1.65 documente la 273 **avec la mention du recouvrement**.
