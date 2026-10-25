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
