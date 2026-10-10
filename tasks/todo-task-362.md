# todo-task-362.md — Intégration Weda : weda2 embarqué s'ouvre sur la messagerie que Weda désigne

**Repos**: client-angular, api-mail (catalogue e2e seulement : `Api/Mail/e2e/scenarios.yml`)
**Dependencies**: done-task-356 (pont v1, `EmbeddedHostService.request()`)
**Epic**: E019
**Single frontend**: true — seul weda2 (client-angular) est embarqué dans Weda. Blazor et mobile
n'ont pas d'hôte Weda (raison fonctionnelle).
**Priorité**: **1** — un compte Keycloak peut porter plusieurs boîtes, et weda2 ouvre aujourd'hui sa
boîte « par défaut ». Embarqué dans Weda, il peut donc afficher une autre boîte que celle que Weda
connaît et que WMickey synchronise. L'import à la demande (task-363) s'appuie sur cette tâche.

> **Origine.** Décision de l'humain du 2026-10-10, consignée dans l'amendement 3 de l'ADR-007 (dépôt
> Weda, décision B6) et dans l'amendement 3 de l'ADR client
> (`Client/Angular/docs/ADR-2026-10-09-integration-weda-mode-embarque.md`, § 1 et 2) :
> - en mode embarqué, **c'est Weda qui transmet l'adresse** de la boîte à ouvrir ;
> - weda2 ouvre cette boîte **à chaque entrée**, même si le praticien a mis une autre boîte « par
>   défaut » dans weda2 ;
> - si elle n'est pas rattachée au compte, weda2 **propose de la rattacher**, avec son écran de
>   rattachement pré-rempli, puis l'ouvre ;
> - après l'ouverture, le changement de boîte reste **libre**.
>
> **Hors flag, et c'est voulu** (ADR client, amendement 3, § 1) : api-mail évalue `weda_integration`
> sur l'identité de la boîte ouverte, et `GET /api/v1/FeatureFlag` exige une boîte. Le flag ne peut
> donc pas décider quelle boîte ouvrir. La désignation rejoint « l'adaptation à l'iframe », comme la
> connexion déléguée. Côté Weda, l'iframe n'est affichée que pour un cabinet où `weda_integration`
> est active.

## Ce qui existe (constaté dans le code le 2026-10-10)

- **client-angular** :
  - `libs/mss/src/core/guards/mailbox.guard.ts` appelle `store.initialize()` (liste des boîtes et
    statut de session), puis applique la table de décision. Pour `OpenDirectly`, il ouvre la boîte
    `selectable && isDefault`, sinon il renvoie à l'écran de choix.
  - `MailboxSessionStore` (`core/stores/mailbox-session.store.ts`) : `open()` refuse une boîte non
    sélectionnable ; `clear()` remet tout à zéro.
  - `features/mailbox-onboarding/mss-mailbox-onboarding.component.ts` est l'écran de rattachement,
    adossé à `ui/attach-mailbox-form`. Le champ `email` y est un signal local, vidé par `reset()`.
    Après le rattachement, « Ouvrir » ouvre la boîte rattachée.
  - `apps/weda2/src/lib/embedded/` : `EmbeddedHostService.request()` (pont v1 ; délai par défaut
    30 s ; `unsupported` hors mode embarqué). `WedaIntegrationService` lit `weda_integration`
    **après** l'ouverture d'une boîte.
- **api-mail** : une boîte demandée par `Client-Email` et non rattachée au compte est refusée
  (`403`, code `NOT_ATTACHED`) sur toute route qui exige une boîte (`UserContextEnricherMiddleware`).
- **e2e** : `front/e2e/mss-e2e/support/session.ts` simule le proxy d'authentification par
  `page.route` (`/session/has-session`, `/session/token`). Aucun hôte embarquant n'existe.
- **Weda** (hors forge) : la boîte de l'utilisateur est celle que WMickey synchronise,
  `IMailBoxService.GetMailBoxAsync(UserID, CabinetID)` → `ASP_Select_MailBoxById` (base Mickey,
  `T_Mailbox_Box.Box_Address`). Elle n'est pas dans `CustomPrincipal`.

## Objective

1. **libs/mss** :
   - un jeton optionnel dans `core/tokens/`, par exemple `MSS_DESIGNATED_MAILBOX`
     (`() => Promise<string | null>`), exporté par `core/index.ts` ;
   - `mailboxGuard` l'interroge à l'entrée, quand aucune boîte n'est ouverte, en parallèle de
     `store.initialize()`, puis décide :

     | Situation | Résultat |
     |---|---|
     | Une boîte sélectionnable du compte porte l'adresse (sans casse, sans espaces autour) | elle est ouverte, quel que soit `isDefault` |
     | La boîte existe mais n'est pas sélectionnable | écran de choix, qui en donne la raison |
     | Le compte ne la porte pas | écran de rattachement, pré-rempli |
     | Pas d'adresse : jeton absent, `null`, rejet | table de décision inchangée |

     `PscRequired` reste prioritaire : sans session PSC, aucun rattachement n'est possible ;
   - l'adresse désignée est gardée **en mémoire** dans `MailboxSessionStore` (signal), et `clear()`
     la remet à zéro. **Jamais dans l'URL** : elle finirait dans l'historique du navigateur et dans
     les journaux du serveur web ;
   - l'écran de rattachement pré-remplit le champ avec l'adresse désignée, et l'annonce : « La
     messagerie {adresse} n'est pas encore rattachée à votre compte. » Sans adresse désignée,
     l'écran est inchangé. Il ne nomme pas Weda.
2. **apps/weda2** : fournit le jeton **en mode embarqué seulement**.
   - Il envoie `EmbeddedHostService.request<{ email: string }>('get-mailbox')`, avec un délai de
     10 s.
   - Une erreur, une adresse vide ou mal formée donnent `null`.
   - `'get-mailbox'` rejoint `EmbeddedHostRequestType`.

   Hors mode embarqué, le jeton n'est pas fourni : weda2 autonome est inchangé.
3. **Faux hôte de test**, réutilisé par task-363 :
   - une page servie par Playwright (`page.route`), sur une origine dédiée déclarée dans les
     origines autorisées de l'environnement e2e ;
   - elle embarque weda2 dans une iframe, et répond au pont v1 avec des données fixes, contrôles
     d'origine compris ;
   - ici, elle répond à `host-capabilities` et `get-mailbox`.
4. **Journaux** : weda2 journalise l'issue de l'entrée (`designated`, `attach-proposed`, `fallback`),
   **jamais l'adresse**.

## Partie Weda (hors forge, faite en dehors de `/develop`)

Elle est nécessaire pour que la tâche soit complète (règle 11).

- **`GET /api/mss/filing/mailbox`** dans `MssFilingController` :
  - `[Authorize]`, et `HasWmss` exigé ;
  - refusé (`403`) à un secrétaire (`IsSecretary()`) ;
  - rend `{ email }` depuis `GetMailBoxAsync(UserID, CabinetID)`, ou `404` si l'utilisateur n'a pas
    de boîte ;
  - n'écrit pas l'adresse dans les journaux.
- **Gestionnaire `get-mailbox`** dans `Default.aspx`, par `callApi`, avec les codes d'erreur
  existants.
- **Switch** : il n'est pas proposé aux secrétaires (ADR-007, B7).

## Definition of Done

- [ ] Build passes (0 errors) sur client-angular ; Tests pass (0 failures, hors flaky préexistants
  documentés)
- [ ] **Angular — garde**, tests rouges d'abord, une ligne par cas de la table :
  - [ ] la boîte désignée est ouverte alors qu'une **autre** boîte est `isDefault` ;
  - [ ] la comparaison ignore la casse ;
  - [ ] boîte désignée non sélectionnable → écran de choix ;
  - [ ] boîte désignée absente du compte → écran de rattachement, et l'adresse est dans le store ;
  - [ ] jeton absent, `null` ou rejeté → table de décision inchangée (non-régression de weda2
    autonome) ;
  - [ ] sans session PSC et sans boîte → `psc-required`, même avec une adresse désignée.
- [ ] **Angular — écran de rattachement** : avec une adresse désignée, le champ est pré-rempli et
  l'annonce s'affiche ; sans adresse, l'écran est inchangé. Après le rattachement, « Ouvrir » ouvre
  la boîte désignée.
- [ ] **Angular — shell** :
  - [ ] le jeton n'est fourni qu'en mode embarqué ;
  - [ ] `get-mailbox` est envoyé à l'hôte ;
  - [ ] délai dépassé, `not-found`, `forbidden` ou adresse vide → `null`.
- [ ] **Entrée suivante** : après un changement de boîte puis une nouvelle entrée (store vidé), la
  boîte désignée est rouverte.
- [ ] Scénario **E2E-WEDA-001**, version 1, ajouté dans `Api/Mail/e2e/scenarios.yml` :
  - titre : « Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne » ;
  - attendu : weda2, embarqué par le faux hôte, s'ouvre sur `boite-praticien`, que l'hôte désigne.
    Si l'hôte désigne une adresse que le compte ne porte pas, weda2 affiche l'écran de
    rattachement, pré-rempli avec cette adresse ;
  - clients : `angular: requis`, `mobile: non-applicable — l'application mobile n'est pas embarquée
    dans Weda` ;
  - seed : `boite-praticien` ;
  - implémenté dans client-angular, avec le faux hôte.
- [ ] `data-testid` sur l'annonce de l'écran de rattachement ; libellés FR en dur
- [ ] Aucune adresse de messagerie dans les journaux de weda2, et aucune donnée de santé
- [ ] Partie Weda faite et validée (règle 11) : voir le Manual Test Plan

## Manual Test Plan

1. Lancer le backend (`cd Api/Mail && dotnet run --project src/AppHost`) et weda2
   (`cd Client/Angular/front && .\serve-weda2.ps1`). Weda tourne en `https://localhost:44300`, avec
   un utilisateur qui a une boîte V2 (WMickey), dans un cabinet où le switch est proposé.
2. Prendre un compte qui porte **deux** boîtes. Dans weda2 autonome
   (`https://localhost:4200/messagerie`), mettre « par défaut » la boîte qui **n'est pas** celle de
   Weda.
3. Dans Weda › Échanges, activer la nouvelle expérience : weda2 s'ouvre sur la boîte de Weda, pas
   sur la boîte par défaut de weda2.
4. Changer de boîte dans weda2 : la bascule fonctionne. Recharger la page Échanges : la boîte de
   Weda est rouverte.
5. Détacher la boîte de Weda dans weda2 (gestion des messageries), puis recharger Échanges. L'écran
   de rattachement s'affiche, pré-rempli avec l'adresse de Weda. Rattacher, puis « Ouvrir » : la
   boîte s'ouvre.
6. Ouvrir weda2 hors iframe, dans un onglet : la boîte par défaut de weda2 s'ouvre, comme avant.
7. Avec un compte secrétaire : le switch n'est pas proposé.
8. Dans les journaux du navigateur et du serveur Weda, aucune adresse de messagerie n'apparaît.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — messagerie MSSanté intégrée au logiciel
- **Exigences DSR honorées** : aucune nouvelle. C'est un préalable de RG-E009-034 (classer depuis le
  logiciel métier) : la messagerie affichée dans Weda est celle que Weda connaît.
- **INS** : non concerné, aucune donnée de patient
- **Authentification PS** : PSC / e-CPS, inchangée. La désignation n'accorde aucun droit : api-mail
  vérifie que la boîte est rattachée au compte, et seul le titulaire d'une boîte peut la rattacher
  (identité PSC).
- **Habilitations** : la boîte ouverte appartient au compte connecté (registre d'api-mail). Weda ne
  rend l'adresse qu'à l'utilisateur lui-même, pour le cabinet de sa session.
- **Interop CI-SIS** : non concerné
- **Tracé PGSSI-S** : l'ouverture de la boîte est tracée comme aujourd'hui (session de boîte
  d'api-mail). Aucune adresse dans les journaux techniques de weda2.
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé
- **AIPD / impact RGPD** : l'adresse MSSanté professionnelle du praticien passe de Weda à weda2 dans
  le navigateur (`postMessage`, origine vérifiée des deux côtés). Ce n'est pas une donnée de santé.
  Elle n'est ni stockée ni journalisée.
