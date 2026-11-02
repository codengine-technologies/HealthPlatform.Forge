# todo-task-421.md — Un message d'erreur donne au médecin un code et une référence à transmettre au support

**Repos**: client-angular, client-mobile, client-blazor, api-mail (catalogue e2e `Api/Mail/e2e/scenarios.yml` seulement)
**Dependencies**: task-420 (chaque erreur d'api-mail porte un code, imprévue comprise)
**Epic**: E021
**Priorité**: **3** — sans référence, le support ne peut pas relier l'appel d'un médecin à l'erreur exacte dans les journaux.

> **Origine.** Demande humaine du 2026-11-01 : faciliter l'analyse des pannes en production sans dégrader les
> performances. Pendant de task-420 côté écrans : api-mail rend déjà `traceId` dans chaque problem+json, et
> task-420 y garantit un `code` ; il reste à les montrer.

## Ce qui est établi

- api-mail pose `traceId` (et `instance`) sur chaque problem+json (`ProblemDetailsSetup`) ; task-420 y garantit
  un `code` pour toute erreur, `UNEXPECTED_ERROR` compris.
- Chaque client a son point de traduction des erreurs :
  - weda2 : `libs/mss/src/core/utils/problem-details.utils.ts` (`mapProblemDetailsToMessage`), modèle
    `problem-details.model.ts` (qui connaît déjà `traceId`) ;
  - mobile : `src/app/core/utils/http-error.util.ts` ;
  - Blazor : `Src/Modules/Mss/Application/Services/HttpRequestService.cs` (+ `GetOutcome` / `PostOutcome`).
- Aucun des trois n'affiche aujourd'hui de référence : le médecin ne peut rien transmettre de précis au support.
- Le `traceId` est un identifiant technique de corrélation : il ne contient aucune donnée de santé ni personnelle.

## Objective

Qu'une erreur d'api-mail affichée au médecin, sur weda2, le mobile ou Blazor, porte **en plus** de son message
une ligne discrète « Code : {code} — Réf. : {référence} », que le médecin peut copier et transmettre. Le support
retrouve l'erreur exacte dans Seq à partir de cette référence.

### Périmètre

1. **Référence courte** : les 8 premiers caractères de l'identifiant de trace contenu dans `traceId` (format W3C
   `00-{trace-id}-{span-id}-{flags}` : on prend le `trace-id`). Assez pour une recherche Seq, assez court pour
   être dicté.
2. **Affichage** : sous le message d'erreur existant, en petit, « Code : … — Réf. : … », avec un bouton
   « Copier » qui copie le code et la référence **complète**. Le message principal ne change pas.
3. **Où** : partout où une erreur d'api-mail est présentée au médecin par les points de traduction ci-dessus
   (toasts, bandeaux, messages d'écran). Une erreur **sans** `traceId` (panne réseau, passerelle sans
   problem+json) n'affiche ni code ni référence : le message seul, comme aujourd'hui.
4. **Libellés** : français en dur (weda2, mobile), via `Localizer` (Blazor). `data-testid` sur la ligne et le
   bouton.

### Hors périmètre

- Les erreurs d'autres services que api-mail (proxy PSC, Weda) : leur forme n'est pas garantie.
- La page support / la recherche par référence : c'est Seq.

## Definition of Done

- [ ] Build et tests verts : weda2, mobile, Blazor, api-mail
- [ ] weda2 : tests unitaires — une erreur d'api-mail avec `code` et `traceId` affiche la ligne « Code : … — Réf. : … »
      (référence = 8 premiers caractères du trace-id) ; sans `traceId`, la ligne est absente ; le bouton copie code
      et référence complète
- [ ] mobile : mêmes tests unitaires (Jasmine/Karma)
- [ ] Blazor : mêmes tests (bUnit) sur le composant d'affichage d'erreur
- [ ] Scénario **E2E-ERROR-001** « Une erreur affiche un code et une référence à transmettre au support » ajouté
      dans `Api/Mail/e2e/scenarios.yml` (version 1 ; angular `requis`, mobile `requis`) et implémenté dans les deux
      suites : refus simulé à la frontière avec le contrat exact d'api-mail (problem+json, `code`, `traceId`), la
      ligne affiche ce code et la référence attendue (`refus-simule-a-la-frontiere`)
- [ ] `data-testid` sur la ligne et le bouton « Copier »
- [ ] Aucune donnée de santé ni personnelle affichée ou copiée : seuls le code du catalogue et l'identifiant de trace

## Manual Test Plan

1. Lancer api-mail (AppHost, Seq) et weda2 (`npm start` dans `Client/Angular/front`).
2. Provoquer un refus connu (carte d'un autre praticien sur la boîte) : sous le message, « Code :
   MAILBOX_PSC_MISMATCH — Réf. : xxxxxxxx ». Cliquer « Copier », coller dans Seq : l'erreur exacte est trouvée.
3. Arrêter api-mail entièrement : le message de panne s'affiche **sans** ligne de code ni référence.
4. Refaire 2 sur le mobile (`npm start` dans `Client/Mobile`) et sur Blazor.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — outillage d'exploitation et de support
- **Vague Ségur** : hors Ségur — exploitabilité
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — aucune donnée patient affichée ni copiée
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé — aucun acte nouveau ; la référence relie l'écran au journal technique, pas au
  journal d'audit
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non applicable — l'écran n'expose qu'un code et un identifiant technique
- **AIPD / impact RGPD** : inchangé — l'identifiant de trace n'est pas une donnée personnelle

## Branches

- `api-mail` (pushed) : feat/task-421-code-et-reference-affiches-sur-les — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-421-code-et-reference-affiches-sur-les (catalogue e2e seulement)
- `client-mobile` (pushed) : feat/task-421-code-et-reference-affiches-sur-les — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-421-code-et-reference-affiches-sur-les
- `client-blazor` (pushed) : feat/task-421-code-et-reference-affiches-sur-les — https://github.com/codengine-technologies/HealthPlatform.Client/tree/feat/task-421-code-et-reference-affiches-sur-les
- `client-angular` (code-only) : la forge écrit sur la branche checkée dans `Client/Angular/` (au /start : `feature/nova-mss-weda-integration`) — humain gère branche, commit, push, PR TFS

## Timings

*(généré par `tools/timing/report.sh --task task-421 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 24 s | — | — | — | — |
| **Total cycle** | | **24 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |
