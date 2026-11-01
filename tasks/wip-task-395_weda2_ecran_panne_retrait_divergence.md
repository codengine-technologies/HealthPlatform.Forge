# todo-task-395.md — Livrer sur weda2 le code de task-378 (écran de panne à l'entrée) et retirer la divergence E2E-MAILBOX-002

**Repos**: client-angular, api-mail
**Dependencies**: task-378 (mergée côté api-mail et mobile)
**Epic**: E016
**Single frontend**: true
**Priorité**: **2** — tant que ce code manque, le scénario requis E2E-MAILBOX-002 est en divergence temporaire côté
weda2, et weda2 n'a pas l'écran de panne à l'entrée qu'ont api-mail et le mobile.

> **Origine.** `/e2e` de task-394 (2026-10-25) : après la synchronisation avec `develop`, la porte bloquait sur
> E2E-MAILBOX-002 « requis pour angular mais absent de sa suite ». Le code weda2 de task-378, écrit en code seul sur
> `feature/nova-mss-weda-integration` (17 fichiers modifiés et `libs/mss/src/features/mailbox-unavailable/`, d'après
> `tasks/archived/archived-task-378.md`), n'est plus dans le clone : ni dans l'arbre de travail, ni dans un stash, ni
> dans un commit. L'humain a décidé une **divergence temporaire** côté angular, résorbée par cette task.

## Objective

weda2 affiche, comme le mobile, l'écran « service indisponible » quand api-mail ne répond pas à l'entrée, avec
« Réessayer ». Le test E2E-MAILBOX-002 weda2 est livré, et la divergence est retirée du catalogue.

## Definition of Done

- [ ] Le code weda2 de task-378 est retrouvé (clone ou poste où il a été écrit), ou réécrit d'après
      `tasks/archived/archived-task-378.md`, sur la branche weda2
- [ ] E2E-MAILBOX-002 implémenté dans `Client/Angular/front/e2e/mss-e2e/specs/functional.e2e.ts` à la version du
      catalogue, et prouvé rouge par mutation
- [ ] Divergence `angular` de E2E-MAILBOX-002 retirée de `Api/Mail/e2e/scenarios.yml`
- [ ] Build et tests weda2 verts ; `/e2e` vert avec parité verte, sans divergence

## Manual Test Plan

1. weda2, api-mail arrêté : ouvrir la messagerie. L'écran dit que le service est indisponible et propose
   « Réessayer », sans l'écran « Pro Santé Connect requis » ni l'ajout d'une messagerie.
2. Relancer api-mail, puis cliquer « Réessayer » : la boîte de réception s'affiche.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur, robustesse de l'entrée dans la messagerie
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé (déjà livré par task-378 côté api-mail)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé
- **AIPD / impact RGPD** : inchangé

## Branches

- `api-mail` (pushed) : feat/task-395-weda2-ecran-panne-retrait-divergence — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-395-weda2-ecran-panne-retrait-divergence
- `client-angular` (code-only) : la forge travaille sur la branche courante de `Client/Angular/` (`feature/nova-mss-weda-integration` au /start) — humain gère branche, commit, push, PR TFS

## Timings

*(généré par `tools/timing/report.sh --task task-395 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 13 s | — | — | — | — |
| /develop | ok | 4 min 06 s | 1 (13 s) | 1 (4.5 s) | — | api-mail 1B/1T |
| /sonar | skipped | 0.8 s | — | — | — | diff = e2e/scenarios.yml seul, aucun C# changé depuis l'analyse task-419 |
| /lint-angular | skipped | 0.8 s | — | — | — | aucun code Angular écrit par la forge (arbre propre) |
| /lint-mobile | skipped | 0.6 s | — | — | — | client-mobile non touché |
| **Total cycle** | | **4 min 22 s** | **1 (13 s)** | **1 (4.5 s)** | **0 (0.0 s)** | |

## Develop log

- **Repos touchés** : `api-mail` (catalogue e2e). `client-angular` : aucun changement. Le code et le test weda2 de task-378 sont déjà sur `feature/nova-mss-weda-integration` (commit `85a13925` « Task 378 », `libs/mss/src/features/mailbox-unavailable/`), retrouvés dans le clone.
- **Aucun DTO, aucun interop.**
- **Commit** : api-mail `7b42ed1c` test(e2e) : divergence `angular` d'E2E-MAILBOX-002 retirée de `Api/Mail/e2e/scenarios.yml`, l'origine mentionne la résorption.
- **E2E-MAILBOX-002 sur weda2** : le test `functional.e2e.ts:3358` déclare `scenario('E2E-MAILBOX-002', 1)`, la version du catalogue.
  - Il passe sur un banc e2e monté pour l'occasion (`run.mjs --serve-only`).
  - **Vu rouge par mutation** : `data-testid="mailbox-unavailable"` renommé dans `mss-mailbox-unavailable.component.html` → « la panne est dite comme une panne : expect(locator).toBeVisible() failed ».
  - Restauré par copie, rejoué au vert. L'arbre weda2 est propre et le banc démonté.
- **Build / tests** : api-mail build vert ; `ScenarioCatalogTests` 17/17. weda2 n'est pas modifié : son build et ses tests sont rejoués par `/review`.
- **Passe qualité (/simplify)** : rien à simplifier (une modification YAML).
- **DOD** :
  - code weda2 retrouvé ✓ ;
  - test à la version du catalogue et vu rouge ✓ ;
  - divergence retirée ✓ ;
  - `/e2e` parité sans divergence → étape `/e2e`.
- **Étape suivante** : `/sonar task-395`.

## Sonar log

- **Sonar : skip mesuré**. Le diff api-mail se limite à `e2e/scenarios.yml`, hors des sources analysées (C#). Aucun fichier C# n'a changé depuis la dernière analyse complète (`72b82aec`, task-419, 2026-11-01), identique à `develop` @ `f2732115`.
- KPIs de cette analyse, valables pour ce code : Quality Gate OK ; new coverage 96,2 % ; bugs / vulnérabilités / code smells / hotspots 0 / 0 / 0 / 0 ; coverage 97,8 % ; duplication 0,4 % ; ratings A/A/A.

## Lint log

- **/lint-angular** : skip — aucun code Angular écrit par la forge (arbre `Client/Angular/front` propre) ; le code weda2 de task-378 est déjà commité par l'humain sur `feature/nova-mss-weda-integration`.
- **/lint-mobile** : skip — `client-mobile` absent des `**Repos**`, sur `develop`, arbre propre.
