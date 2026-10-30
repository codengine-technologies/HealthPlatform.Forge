# todo-task-416 — Le nom PSC du délégataire est lu sur la bonne route du proxy

**Repos**: api-mail
**Dependencies**: task-405 (résolution du nom de la personne), task-407 (`Sender` du délégataire)
**Epic**: E020

> **Origine** : constat humain du 2026-10-30. Cyril (RPPS 899700723440), connecté avec sa carte PSC,
> écrit depuis la boîte déléguée de Virginie et reçoit « Identité du délégataire indisponible,
> reconnectez-vous avec Pro Santé Connect : rien n'est parti. » Se reconnecter ne change rien.
>
> **Diagnostic (Seq)** : chaque requête journalise `[PersonName] userinfo answered 404 for SID=…`,
> alors que la session est active sur le proxy (`has-session` confirmé) et que le proxy ne journalise
> aucun appel `userinfo` venu de l'API : c'est un 404 de routage.
> - `PscProxy:BaseUrl` vaut `https://localhost:8081/v1`, et l'adresse de base du client prend un `/`
>   final.
> - `PersonNameResolver` déclare la route `v1/auth/userinfo`. L'API appelle donc
>   `/v1/v1/auth/userinfo`.
> - `PscTokenProvider` utilise `internal/psc-context`, sans le préfixe, et fonctionne.
>
> **Pourquoi personne ne l'a vu** : le banc et les e2e posent le nom par en-têtes, ce qui court-circuite
> le proxy. Les tests unitaires du résolveur simulent la réponse sans vérifier l'URL demandée.
>
> **Contournement posé le 2026-10-30** (base locale `mss_registry`) : nom « Cyril / TOUBIB0072344 »
> écrit à la main sur les rattachements de Cyril.

## Objectif

Un délégataire connecté avec Pro Santé Connect écrit pour le compte de la boîte. Son nom est lu
dans sa session PSC, la mention « Envoyé par {délégataire} pour le compte de {boîte} » part avec
le message, et l'acte est imputé à son nom.

## Règles

1. `PersonNameResolver` appelle `GET {BaseUrl}/auth/userinfo` : la route relative ne répète pas le
   préfixe de version que porte `PscProxy:BaseUrl`, comme les autres routes du client `PscProxy`.
2. Les autres routes relatives du client `PscProxy` sont relues : aucune ne doit répéter le préfixe.
3. Le comportement de repli reste celui de task-405 : le proxy ne répond pas → nom enregistré sur le
   rattachement ; aucun nom → l'envoi pour le compte de la boîte est refusé.

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures)
- [ ] Test unitaire de `PersonNameResolver` : l'URL demandée au client `PscProxy`, composée avec une
      `BaseUrl` qui porte `/v1`, est `{hôte}/v1/auth/userinfo`. Le test est vu rouge sur l'ancienne
      route.
- [ ] Test d'intégration de bout en bout : un délégataire, avec une session PSC et sans en-têtes de
      nom, envoie depuis la boîte qu'on lui a déléguée.
  - Le proxy PSC est simulé par un serveur HTTP qui ne répond **que** sur `/v1/auth/userinfo`.
  - Le nom de la session est lu dans la réponse réelle : envoi accepté, et `Sender` portant ce nom.
  - Le test est vu rouge sur l'ancienne route (règle 1b).
- [ ] Revue des routes relatives du client `PscProxy` consignée dans le `## Develop log`
- [ ] `conventions/csharp.md` : entrée « une route relative d'un client HTTP nommé ne répète pas le
      chemin de sa `BaseUrl` »

## Manual Test Plan

- Backend : `cd Api/Mail && dotnet run --project src/AppHost`. Proxy PSC local démarré.
- Remettre à vide le nom enregistré sur les rattachements de Cyril (`person_first_name`,
  `person_last_name` à `NULL` dans `mss_registry.mss_accounts`), pour ne plus profiter du contournement.
- Se connecter avec la carte PSC de Cyril, ouvrir la boîte déléguée de Virginie, écrire et envoyer un
  message.
- Attendu : le message part. Le destinataire voit « Envoyé par Cyril … pour le compte de
  virginie.medecinrpps0062267@… ». Seq ne montre plus `[PersonName] userinfo answered 404`. Le proxy
  journalise `✅ [UserInfo] The user's information was successfully returned` pour la session.
- Le registre porte de nouveau le nom de Cyril sur le rattachement, enregistré par le résolveur.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif fonctionnel de la délégation
- **Exigences DSR honorées** : référentiel #2 clients MSSanté, draft délégation (ECO.1.2.9 à 1.2.11,
  `Sender` du délégataire), déjà livré par task-407 ; ce correctif le rend opérant avec une vraie
  session PSC
- **INS** : non manipulée
- **Authentification PS** : PSC, inchangée. Seule la lecture du nom de la session est corrigée.
- **Habilitations** : inchangées (règle 14)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : l'acte est imputé au nom réel du délégataire (règle 14), ce que la panne empêchait
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé
- **AIPD / impact RGPD** : aucun changement de traitement

## Branches

- `api-mail` (pushed) : fix/task-416-nom-psc-du-delegataire-route-userinfo — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-416-nom-psc-du-delegataire-route-userinfo
