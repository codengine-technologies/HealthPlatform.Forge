# todo-task-107-mobile-new-mail-notifications.md — Notifications de nouveaux emails (stream temps réel)

**Repos**: client-mobile
**Single frontend**: true
**Dependencies**: none
**Epic**: E012

> **US mono-repo justifiée** : le backend expose déjà le flux de notifications
> (`GET /api/v1/mail/notifications/stream?token=`) ; l'écart est l'absence
> d'écoute côté `client-mobile`. Parité avec `NotificationStreamService` d'angular.

## Objective

Alerter le médecin **en temps réel** de l'arrivée de **nouveaux emails** dans sa
boîte, à parité avec le flux de notifications de `client-angular` : connexion à
un stream SSE **scoped-utilisateur**, et restitution **in-app** (toast +
indicateur), avec rafraîchissement de la liste si pertinent.

## Périmètre & cadrage

- **Dans ce périmètre** : notification **in-app** via le stream SSE existant
  (`/api/v1/mail/notifications/stream`), surfaçant l'arrivée de nouveaux mails
  (toast / badge) et déclenchant un refresh de l'inbox courante.
- **Hors périmètre de cette US** (à traiter en task dédiée si souhaité) : les
  **push natives** (Capacitor Push / FCM / APNs) en arrière-plan, qui exigent
  une infra (clés FCM/APNs, enregistrement device côté backend, `devops`) non
  disponible ici. Cette US livre la parité angular (in-app SSE) ; la push native
  est un suivi infra-portant.

## Analyse de référence (client-angular)

- `NotificationStreamService` : `EventSource` vers
  `/api/v1/mail/notifications/stream?token={jwt}` (scope-utilisateur, distinct du
  stream folder-scoped de task-104), évènement `notification` →
  `NotificationPayloadDto` ; reconnexion native ; fermeture au teardown.

## Comportement attendu

- Connexion au stream notifications après authentification (scope-utilisateur).
- À réception d'un évènement « nouveau mail » : toast non intrusif + indicateur
  (ex. badge / pastille) ; si l'utilisateur est sur l'inbox du dossier concerné,
  proposer/effectuer un refresh (sans casser la position de scroll).
- Une seule connexion active ; reconnexion native EventSource sur coupure ;
  fermeture propre au logout / destroy.
- Aucune donnée de santé dans le payload affiché/loggé.

## Scénarios d'acceptation

1. **Nouveau mail** — Quand un nouvel email arrive, alors une notification in-app
   s'affiche.
2. **Refresh contextuel** — Si je suis sur l'inbox du dossier concerné, la liste
   se met à jour (ou propose de se mettre à jour) sans perte de position.
3. **Connexion unique** — Une seule connexion SSE notifications active à la fois.
4. **Robustesse** — Coupure réseau courte : reprise automatique du stream.
5. **Teardown** — Au logout, le stream est fermé.

## Definition of Done

- [ ] Build passes (`npm run build`, 0 erreur)
- [ ] Tests pass (`npm test -- --watch=false --browsers=ChromeHeadless`, 0 échec)
- [ ] Service `NotificationStreamService` mobile (EventSource scope-utilisateur, connect/disconnect)
- [ ] Modèle `NotificationPayloadDto` mobile (miroir)
- [ ] Restitution in-app (toast + indicateur) à réception d'un nouveau mail
- [ ] Refresh contextuel de l'inbox sans saut de scroll ; pas de boucle
- [ ] Connexion unique ; reconnexion native ; fermeture au logout/destroy
- [ ] Libellés FR en dur ; `data-testid` sur l'indicateur
- [ ] Tests : service notifications (connexion + parsing évènement via fake EventSource, close au disconnect), restitution (toast déclenché)
- [ ] Aucune donnée de santé ni token en clair dans les logs
- [ ] Note explicite : push natives Capacitor = suivi hors périmètre

## Manual Test Plan

- Backend `cd Api/Mail && dotnet run` ; Mobile `cd Client/Mobile && npm start`
- Se connecter (PSC) ; Network : ouverture du stream `…/notifications/stream?...`
- Provoquer l'arrivée d'un nouvel email (envoi depuis un autre compte de test)
- Vérifier la notification in-app + (si sur l'inbox) la mise à jour de la liste
- Couper le réseau brièvement → vérifier la reprise du stream
- Se déconnecter → vérifier la fermeture du stream
- Comparer avec `client-angular`

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR honorées** : continuité d'accès MSS (notification d'arrivée)
- **Authentification PS** : PSC / e-CPS ; stream authentifié (JWT en `?token=`)
- **Sécurité** : aucune donnée de santé dans le payload de notification ni les logs ; token jamais loggé en clair
- **AIPD / RGPD** : inchangé — signalement d'arrivée, pas de nouveau traitement de données

## Branches
- `client-mobile` (pushed) : feat/task-107-mobile-new-mail-notifications — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-107-mobile-new-mail-notifications

> Single frontend (client-mobile only). Deps none (socle E012 sur develop). Périmètre : notification in-app SSE (push native = suivi infra hors US).

## Develop log
- Repos : client-mobile
- NotificationStreamService (EventSource user-scoped, NgZone, single connection, close on destroy) + NotificationPayloadDto
- inbox : connect à l'entrée, toast sur notification, append du nouveau mail si dossier courant, disconnect au destroy
- Build ✓ · Tests ✓ 100/100 (4 nouveaux) · Lint ✓
- Commit : client-mobile @685cfda
- Note : push natives Capacitor = suivi infra hors US

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/12 — label `awaiting-human-merge`

## Code Review Summary
- Verdict : APPROVED · Build ✓ · Tests ✓ 100/100 · Lint ✓
- stream user-scoped testé, restitution in-app, connexion unique, close ; aucun token/donnée santé loggé

## Merged
- Merged : 2026-06-19 (squash) by human authorization
- client-mobile : develop @c0ac9dd (PR #12 closed)
- Local feature branch conservée
