> **RÉSOLU (2026-07-16)** — voie choisie par l'humain : implémentation sur base staging.
> task-161 implémentée sur `feat/task-161-home-load-robustness` (basée sur la staging,
> qui contient le dashboard task-149) puis **agrégée sur la staging** (commit 54dce54).
> Build/tests/lint verts (738/0), code review APPROVED, vérif visuelle OK. PR vers `develop`
> différée jusqu'au merge du batch. Détails dans `tasks/wip-task-161.md` (## Develop log).

# questions/task-161.md — Blocage : le code cible (task-149) n'est pas sur `develop`

**Étape** : `/develop` (halt avant toute écriture de code).
**Task** : `wip-task-161.md` (client-mobile, E012).
**Branche créée** : `feat/task-161-home-load-robustness` (depuis `origin/develop`, poussée, **vide** — aucun commit).

## Le blocage

task-161 corrige deux défauts de robustesse du **dashboard mobile** (`/tabs/home`)
et référence explicitement :
- `home.page.ts:35-42` — ré-abonnement SSE (`notification$` + `emailsEnriched$`) qui appelle `refresh.trigger()` ;
- `DashboardRefreshService.refresh$` — le bus de refresh à debouncer ;
- le fan-out `forkJoin({...})` des 5 widgets ;
- `mss-api.service.ts:903` — le `baseUrl` qui `throw` en synchrone sans session.

**Or ce code n'existe pas sur `develop`.** Il est livré par **task-149**
(« dashboard clinique mobile + onglet Accueil »), dont la **PR #53 est ouverte
mais non mergée** (HAG). Vérifié :

| Élément | `develop` | `feat/task-149-dashboard-tab` |
|---|---|---|
| `src/app/features/dashboard/` (widgets + `dashboard-refresh.service`) | absent | présent |
| `home.page.ts` : SSE + `refresh.trigger()` + `DashboardRefreshService` | non (version task-113 : `load()` séquentiel, pas de SSE, pas de fan-out) | oui (lignes 27/37/41/52/57) |
| `baseUrl` throw synchrone | ligne 532 | ligne 623 |

Ma branche `feat/task-161` est issue de `develop` → elle ne contient que
l'ancien `home.page` (task-113), qui **n'a aucun des défauts décrits**
(pas de tempête de refresh SSE, pas de `DashboardRefreshService`, pas de
fan-out `forkJoin`). Implémenter ici corrigerait un code qui n'est pas celui
visé par l'US.

## Décision nécessaire (humain)

Deux voies, au choix :

1. **Merger d'abord le batch (dont task-149 / PR #53) sur `develop`**, puis
   relancer `/forge` (ou `/start 161`). task-161 partira alors d'un `develop`
   contenant le dashboard réel — implémentation propre, PR autonome. *(Voie
   recommandée : cohérente avec 1 task = 1 branche depuis develop ; règle US-complete.)*

2. **Autoriser explicitement un stacking** de task-161 sur
   `feat/task-149-dashboard-tab` (base de PR = la branche task-149, pas
   `develop`). Évite d'attendre le merge, mais la PR task-161 restera
   dépendante de #53 et ne pourra merger qu'après elle.

La forge ne choisit pas seule entre ces voies (règle 7 — fail-fast sur
dépendance non résolvable depuis `develop`, et pas d'improvisation de chaîne
inter-tasks). Dis-moi la voie et je reprends.

## État laissé
- Task : `wip-task-161.md` (inchangée hormis la section `## Branches`).
- Branche `feat/task-161-home-load-robustness` : vide, poussée (supprimable si tu préfères repartir propre).
- Aucun code écrit, aucun repo modifié.
