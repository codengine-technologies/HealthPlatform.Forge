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

## Develop log

- Repos touchés : `client-angular` (code-only, non commité), `client-mobile`, `client-blazor`, `api-mail` (catalogue e2e
  seulement). DTOs : aucun changement.
- Commits :
  - `client-mobile` : `4d68597` feat(errors) code et référence affichés au praticien ; `86dc4e7` refactor simplify pass.
  - `client-blazor` : `8e22e7d` feat(errors) code et référence dans les notifications ; `96e94e2` refactor simplify pass.
  - `api-mail` : `9cdf8fe5` test(e2e) scénario E2E-ERROR-001.
  - `client-angular` : non commité sur `feature/nova-mss-weda-integration` (liste en fin de section).
- Ce qui est livré :
  - **Référence** : 8 premiers caractères du trace-id W3C du `traceId` (`00-{trace-id}-{span-id}-{flags}`). Un identifiant
    hors W3C est gardé entier (tronqué, il ne serait plus unique). Sans `traceId` (panne réseau, passerelle), rien ne
    s'affiche. « Copier » copie le code et la référence **complète**.
  - **weda2** :
    - utilitaire `core/utils/error-reference.util.ts` et composant `mss-error-reference` (`data-testid` `error-reference`,
      `error-reference-text`, `error-reference-copy`) ;
    - branchés sous l'échec d'envoi de la rédaction (et la remise incertaine), les erreurs des envois en attente
      (chargement, revue, actions), le refus de l'accusé de lecture et la recherche annuaire des contacts.
  - **weda2, intercepteur** (`apps/weda2/.../error.interceptor.ts`, conflit signalé dans la PR #338) : un code générique ou
    technique d'api-mail (`UNEXPECTED_ERROR`, `DATABASE_UNAVAILABLE`, `SERVICE_UNAVAILABLE`, `FORBIDDEN`…, liste
    `TECHNICAL_ERROR_CODES`) n'est plus pris pour un refus métier : la notification générique de weda2 reste. Le
    comportement d'avant task-420 est rétabli pour ces erreurs.
  - **mobile** :
    - utilitaire et composant `mss-error-reference`, branchés sous les bandeaux de la rédaction, des envois en attente
      (chargement, ligne), de l'assistant IA, du résumé et de l'historique de recherche ;
    - les toasts et alertes d'erreur (contacts, brouillons, dossiers, liste, détail, boîte de réception, signatures,
      rattachement patient, envois en attente) portent la ligne « Code : … — Réf. : … » sous leur message, sans bouton
      « Copier » : un toast Ionic ne porte pas de composant.
  - **Blazor** :
    - `ErrorReference` (Domain), `ProblemDetailsParser.ExtractReference` ;
    - composant `ErrorReferenceLine` (libellés par `Localizer`, copie par `navigator.clipboard`) ;
    - `ErrorNotificationService` place la ligne dans `DetailContent` de la notification Radzen ;
    - `HttpRequestService` passe la référence aux notifications d'erreur, 503 compris.
- Tests :
  - weda2 : `error-reference.util.spec.ts`, `error-reference.component.spec.ts`, `mail-compose-safety` (+2), `mss-pending-sends`
    (+1), `error.interceptor.spec.ts` (+4 vus rouges sur le code d'avant : les 4 codes techniques restaient sans notification).
  - mobile : util (+11), composant (+3), rédaction (+2 ; le bandeau vit dans l'`ion-modal`, on lit ce que le gabarit lie,
    consigne `page-ionic-non-demontee`), envois en attente (+1).
  - Blazor : `ErrorReferenceTests` (+17, dont bUnit sur `ErrorReferenceLine` et sur la notification rendue).
- **Scénario E2E-ERROR-001** v1 (mobile et angular requis) au catalogue, implémenté dans `functional.spec.ts` (mobile) et
  `functional.e2e.ts` (Angular) : panne imprévue simulée une fois à la frontière (500 problem+json `UNEXPECTED_ERROR` +
  `traceId` W3C, consigne `refus-simule-a-la-frontiere`), la ligne affiche `Code : UNEXPECTED_ERROR — Réf. : 4bf92f35` et
  « Copier ». `tsc` des deux suites vert ; catalogue relu par `yaml.safe_load`.
- **Preuves par mutation** (code restauré, marqueur recompté à 0) :
  - M1 weda2 `errorReferenceOf` ne rend jamais rien → 4 fichiers de test rouges (utilitaire, composant, rédaction, envois en attente) ;
  - MM1 mobile, même mutation → 9 tests rouges (utilitaire, composant, rédaction, envois en attente) ;
  - MB1 Blazor `ErrorReference.From` → 9 rouges sur 17 ;
  - intercepteur : les 4 tests neufs rouges sur le code d'avant le correctif.
- Local build / test :
  - weda2 : mss-lib 136 fichiers verts ; weda2 107 fichiers verts ; build weda2 OK (avertissements de budget préexistants : bundle initial, SCSS contacts) ;
  - mobile : build OK, 1 417 verts ;
  - Blazor : projet de tests 498 verts, 2 ignorés, 0 avertissement. La solution entière bute sur `Mss.Console` NU1100
    (source NuGet `github` absente du poste), panne préexistante déjà notée par task-388.
- Lint : weda2, 0 erreur sur les fichiers touchés (`prettier --write` sur les seuls fichiers créés) ; mobile, 0 erreur.
- Passe qualité (/simplify, 4 relecteurs) — appliqué et revalidé :
  - Blazor : corps lu une fois, `Format` commun ;
  - weda2 : `errorReferenceLabel`, corps typé `ProblemDetails` via `isProblemDetails`, `imports: []` retiré ;
  - mobile : `problemOf` réutilisé (avec `traceId`), `problemDetailWithReference`.
  **Écartés** :
  - liste blanche des codes « expliqués par l'écran » à la place de `TECHNICAL_ERROR_CODES` : changerait ce que task-381
    retire, à décider au HAG ;
  - un seul signal `{ text, cause }` au lieu des paires message / cause : refactor large, motif cohérent et testé ;
  - service de toast commun au mobile ;
  - partage de l'utilitaire entre dépôts.
- **Récidive** S4136 (surcharges non adjacentes dans `IErrorNotificationService`), corrigée avant commit ; compteur de
  `conventions/csharp.md` porté à 4.
- **Limites, à lire au HAG** :
  - les refus du middleware de boîte d'api-mail (403 `MAILBOX_PSC_MISMATCH`…) posent `traceId = HttpContext.TraceIdentifier`,
    pas l'identifiant W3C : la référence affichée est alors l'identifiant de requête entier, retrouvable dans Seq
    (`RequestId`). Aligner ce middleware sur `Activity.Current?.Id` est un changement d'api-mail, hors de cette US ;
  - les toasts mobiles portent la ligne sans bouton « Copier ».
- Fichiers `client-angular` non commités (humain : commit + push TFS ; **`functional.e2e.ts` porte E2E-ERROR-001, requis
  côté angular : à commiter avant le merge de la PR api-mail**, consigne `test-angular-non-commite`) :
  `apps/weda2/src/app/core/interceptors/error.interceptor.ts`, `.spec.ts`, `e2e/mss-e2e/specs/functional.e2e.ts`,
  `libs/mss/src/core/index.ts`, `libs/mss/src/core/utils/error-reference.util.ts`, `.spec.ts`,
  `libs/mss/src/ui/error-reference/*` (4 fichiers), `libs/mss/src/ui/index.ts`, `mss-contacts.component.{ts,html}`,
  `mail-compose.component.{ts,html,scss}`, `mail-compose-safety.component.spec.ts`, `mail-detail.component.{ts,html}`,
  `mss-pending-sends.component.{ts,html,spec.ts}`.
- Next step : /sonar task-421 (api-mail : catalogue seul, aucun code C#).

## Timings

*(généré par `tools/timing/report.sh --task task-421 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 24 s | — | — | — | — |
| /develop | ok | 28 min 18 s | 10 (1 min 45 s) | 9 (2 min 37 s) | — | client-mobile 3B/3T, client-blazor 5B/3T, client-angular 2B/3T |
| **Total cycle** | | **28 min 43 s** | **10 (1 min 45 s)** | **9 (2 min 37 s)** | **0 (0.0 s)** | |
