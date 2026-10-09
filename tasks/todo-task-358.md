# todo-task-358.md — Intégration Weda : le compteur de messages non lus de l'en-tête Weda vient d'api-mail

**Repos**: api-mail
**Dependencies**: done-task-356 (flag `weda_integration`)
**Epic**: E019
**Single frontend**: true — aucun client de la forge n'est touché. Le compteur est affiché par Weda,
hors forge (voir « Partie Weda »).
**Priorité**: **2** — c'est la première brique du mode exclusif (EPIC E019) : le **canal par lequel
le serveur Weda interroge api-mail** au nom du praticien. Il est validé ici sur le besoin le plus
simple et le moins risqué, le compteur de non-lus. Les tâches suivantes (réception de la biologie,
classement, envoi depuis Weda) réutilisent ce canal.

> **Origine.** Arbitrage de l'humain du 2026-10-09, consigné dans l'amendement 2 de l'ADR-007 du
> dépôt Weda (`docs/architecture/adr/007_integration-nouvelle-experience-messagerie.md`) :
> - la synchronisation WMickey ne sert plus de socle : jeton PSC perdu dans RabbitMQ, mot-clé posé
>   avant l'import, pas de reprise ;
> - pour un cabinet en nouvelle expérience, **api-mail est le moteur unique** ;
> - c'est **le serveur Weda qui va chercher dans api-mail** ce qui doit entrer dans Weda, par une
>   API dédiée au logiciel hôte, `api/v1/integration/*`.
>
> Aujourd'hui, le compteur de l'en-tête Weda est calculé à partir du stockage WMickey : pour un
> cabinet en nouvelle expérience, il serait faux.

## Ce qui existe (constaté dans le code le 2026-10-09)

- **api-mail** :
  - toute route exige un Bearer Keycloak (politique par défaut, `Api/Program.cs`). La boîte est
    choisie par l'en-tête `Client-Email`. Le cookie `proxy_session_id` est lu par
    `UserContextEnricherMiddleware` et sert à obtenir le contexte PSC auprès du proxy
    (`PscTokenProvider`) ;
  - le nombre de non-lus d'un dossier est déjà calculé : `FolderDto.unreadCount`, dans
    `GET /mail/folders` ;
  - `GET /account/mailboxes` (`[MailboxNotRequired]`) liste les boîtes du compte ;
  - le flag `weda_integration` existe : `FeatureFlags.WedaIntegration`, fermé à froid, évalué par
    identité par `GET /api/v1/FeatureFlag` (task-356).
- **Weda** (hors forge) :
  - `IdentityProviderClient.GetTokenBySessionID` obtient, côté serveur, le jeton Keycloak du
    praticien auprès du proxy à partir du cookie `proxy_session_id`. Il sert aujourd'hui à la
    connexion ;
  - le compteur de l'en-tête vient de `MasterPages/MessagerieWidgetUcForm.ascx`, alimenté par le
    stockage WMickey (`GetMessagerieCountAsync`) pour les utilisateurs WMickey.
- **Aucune route** d'api-mail n'est pensée pour un appel serveur à serveur par le logiciel hôte.

## Objective

1. **api-mail** : créer l'API d'intégration du logiciel hôte, `api/v1/integration`.
   - Authentification identique à celle des clients : Bearer Keycloak, `Client-Email`, cookie
     `proxy_session_id` transmis par l'appelant.
   - **Fermée si `weda_integration` est inactif** pour l'identité : `403` en `ProblemDetails`
     (règle 12), avec un code d'erreur dédié.
   - Première route : `GET api/v1/integration/summary` → `{ "unreadInbox": <nombre> }`, le nombre
     de messages non lus de l'INBOX de la boîte `Client-Email`. **Même valeur** que
     `FolderDto.unreadCount` de l'INBOX.
   - Contrat documenté dans le Swagger. Il est stable : un changement de forme est une rupture
     pour Weda.
2. Cette tâche ne touche **aucun** client de la forge. Seul api-mail est dans `**Repos**`, ce qui
   est justifié : le compteur est affiché par Weda.

## Partie Weda (hors forge, faite en dehors de `/develop`)

Elle est **nécessaire pour que la tâche soit complète** (règle 11) : la PR api-mail attend la
validation de bout en bout.

- Configuration : `NouvelleExperience:ApiMailUrl`.
- Un client api-mail côté serveur (`ApiMailClient`) :
  - jeton du praticien via `GetTokenBySessionID` ;
  - cookie `proxy_session_id` relayé ;
  - adresse de la boîte obtenue une fois par session par `GET /account/mailboxes`, puis
    `Client-Email`.
- La fonctionnalité de cabinet `weda_integration` (`CabinetFeature`, des données, aucune colonne).
  Pour un cabinet où elle est active, le compteur de l'en-tête est alimenté par
  `GET api/v1/integration/summary` au lieu du stockage WMickey. En cas d'échec, le compteur est
  masqué : pas de valeur fausse.

## Definition of Done

- [ ] Build passes (0 errors) ; Tests pass (0 failures, hors flaky préexistants documentés)
- [ ] Tests unitaires du service et du contrôleur `integration`, au moins un test par branche :
  flag actif ou inactif, boîte absente
- [ ] Test d'intégration de bout en bout pour `GET /api/v1/integration/summary` : `unreadInbox`
  égale le nombre de non-lus de l'INBOX du seed, lu dans la réponse réelle. Il passe de N à N-1
  après un `PUT …/status/read` sur un non-lu. Cas d'échec : `403` `ProblemDetails` quand
  `weda_integration` est inactif. Vu rouge (règle 1b)
- [ ] Test d'intégration : sans `Client-Email`, ou avec une boîte qui n'appartient pas au compte, la
  réponse est l'erreur de sélection de boîte habituelle, en `ProblemDetails`
- [ ] Aucune donnée de santé dans les logs : la route ne journalise que l'adresse technique de la
  boîte et le résultat chiffré
- [ ] Swagger : route, schéma de réponse et codes d'erreur documentés
- [ ] Partie Weda faite et validée (règle 11) : le compteur de l'en-tête Weda est égal à celui de
  weda2

## Manual Test Plan

1. Backend : `cd Api/Mail && dotnet run --project src/AppHost`. Le seeder Flagsmith crée
   `weda_integration` activé en développement.
2. Weda : IIS Express en `https://localhost:44300`, avec la fonctionnalité de cabinet
   `weda_integration` active pour le cabinet de test. weda2 : `cd Client/Angular/front &&
   .\serve-weda2.ps1`.
3. Ouvrir n'importe quelle page Weda : le compteur de l'en-tête affiche le nombre de non-lus.
   Ouvrir Échanges : le compteur de l'INBOX de weda2 affiche **le même nombre**.
4. Lire un message non lu dans weda2, puis changer de page dans Weda : le compteur de l'en-tête a
   baissé de 1.
5. Désactiver `weda_integration` pour l'identité dans Flagsmith : le compteur de l'en-tête est
   masqué, et l'appel répond `403` dans les journaux Weda.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — messagerie MSSanté intégrée au logiciel
- **Exigences DSR honorées** : non applicable — infrastructure d'intégration. Seul un compteur
  transite, sans contenu.
- **INS** : non applicable — aucune donnée patient ne transite, seulement un nombre
- **Authentification PS** : PSC / e-CPS, niveau eIDAS substantiel. La session du praticien est
  réutilisée côté serveur (jeton Keycloak issu de la session PSC du proxy). Aucun secret
  supplémentaire, aucun compte de service.
- **Habilitations** : la boîte est celle du compte authentifié (sélection `Client-Email` existante,
  contrôlée par api-mail). Le cloisonnement par cabinet est assuré par Weda, qui n'interroge que
  la boîte du praticien connecté.
- **Interop CI-SIS** : non applicable — JSON propriétaire, aucun document médical
- **Tracé PGSSI-S** : appels journalisés techniquement (route, boîte, statut). Aucune consultation
  de contenu, donc rien de nouveau dans le journal d'audit.
- **Consentement patient** : non applicable — aucun partage de donnée patient
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé — aucune donnée de santé nouvelle n'est stockée ni transmise
- **AIPD / impact RGPD** : inchangé — aucune finalité nouvelle
