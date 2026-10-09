# wip-task-356.md — Intégration Weda, phase A : le pont dans les deux sens, sous le flag `weda_integration`

**Repos**: api-mail, client-angular
**Dependencies**: — (aucune)
**Epic**: E019
**EpicTitle**: Intégration de la nouvelle messagerie dans Weda
**Single frontend**: true — seul le client Angular (weda2) est embarqué dans Weda.
**Priorité**: **2** — socle de l'intégration de la nouvelle messagerie dans Weda. Rien n'est visible
pour l'utilisateur tant que le flag est désactivé, mais tout ce qui suit en dépend (phase B : trouver
le patient Weda ; phase C : classer en un clic dans le dossier patient).

> **Origine.** POC du 2026-10-09 : weda2 est affiché dans une iframe de la page Weda
> `/FolderMedical/WedaEchanges/` (switch « Nouvelle expérience Weda »), et s'y authentifie
> silencieusement sur la session du proxy (`proxy_session_id`). Les décisions sont fixées par deux
> ADR acceptés le même jour :
> - `Client/Angular/docs/ADR-2026-10-09-integration-weda-mode-embarque.md` (côté client) ;
> - dépôt Weda, `docs/architecture/adr/007_integration-nouvelle-experience-messagerie.md`. Il porte
>   **le contrat du pont** (enveloppe, types de demandes, codes d'erreur) et le registre de classement.
>
> Arbitrages de l'humain : Weda classe, weda2 demande ; les deux expériences coexistent ; tout ce qui
> touche à Weda dans weda2 est sous `weda_integration` ; hors iframe, l'intégration est masquée ;
> le switch est réservé aux boîtes IMAP.

## Ce qui existe (constaté dans le code le 2026-10-09)

- **client-angular** — `apps/weda2/src/lib/embedded/` (commit WIP de la branche
  `feature/nova-rewriting-mss-weda-integration`) :
  - `EmbeddedHostService` : `isEmbedded` (iframe + origine du referrer dans
    `EMBEDDED_HOST_ORIGINS`), `hostOrigin`, `notify(type)`.
  - Il émet seulement trois événements vers l'hôte (`authenticated`, `session-expired`,
    `psc-login-required`). **Aucun écouteur** de messages venant de l'hôte, aucune demande avec
    réponse.
  - Le mode embarqué (connexion déléguée, inactivité désactivée, barre du haut masquée) ne dépend
    que de la liste d'origines. C'est voulu (ADR client, § 1) et inchangé par cette task.
- **client-angular** — `libs/mss` : aucun port vers un dossier patient externe. Les jetons existants
  (`MSS_PSC_SIGN_IN`, `MSS_LOGOUT`…) suivent le modèle « le module sait QUAND, le shell sait
  COMMENT ». `MssApiService.isFeatureEnabled(name)` existe et laisse la politique d'échec à
  l'appelant.
- **api-mail** — `Application/Constants/FeatureFlags.cs` : `weda_integration` **n'existe pas**. Un
  flag absent de `FeatureFlags.All` n'existe pas pour l'API (`GET /api/v1/FeatureFlag/{name}`).
  `AppHost/FlagsmithSeeder.cs` sème la liste de développement.
- **Weda** (hors forge) — `Default.aspx` n'a qu'un écouteur des trois événements. Le gestionnaire
  de demandes côté hôte est fait en parallèle dans le dépôt Weda (branche
  `lotus/segur/17546-enveloppe-segur-v2-with-mss-api`).

## Objective

1. **api-mail** — déclarer le flag `weda_integration` :
   - constante `FeatureFlags.WedaIntegration`, ajoutée à `FeatureFlags.All` ;
   - valeur de démarrage à froid **`false`** (fermé) : sans état Flagsmith connu, aucune
     intégration Weda ;
   - semé par `FlagsmithSeeder` en développement. En recette et en production, il est créé
     **désactivé**, puis activé par identité pour les pilotes (geste d'exploitation).
2. **client-angular** — `EmbeddedHostService.request<T>(type, payload?, { timeoutMs?, transfer? })` :
   - `requestId = crypto.randomUUID()`, table des demandes en attente, délai d'expiration de 30 s
     (120 s pour `file-documents`) qui rejette avec le code `timeout` ;
   - **un seul** écouteur `message`, posé uniquement en mode embarqué. Il ignore tout message dont
     `event.source !== window.parent`, dont `event.origin !== hostOrigin` ou dont
     `data.source !== 'weda-host'` ;
   - envois vers `hostOrigin`, jamais `*` ; `version: 1` ajouté à **tous** les messages émis,
     y compris les trois événements existants ;
   - hors mode embarqué, `request()` rejette immédiatement avec `unsupported`.
3. **client-angular** — `WedaIntegrationService` (shell), seul lecteur de `weda_integration`.
   `available: Signal<boolean>` vaut vrai si et seulement si :
   - weda2 est embarqué ;
   - **et** le flag est confirmé actif par `GET /api/v1/FeatureFlag` (évaluation par identité,
     via `MssApiService.getFeatureFlags()`). Échec, absence de réponse ou délai dépassé valent inactif ;
   - **et** l'hôte a répondu à `host-capabilities` avec `protocolVersion: 1`.

   Hors mode embarqué, **aucun** appel n'est émis : ni flag, ni `host-capabilities`.
4. **client-angular** — port `MSS_PATIENT_RECORD_GATEWAY` dans `libs/mss/src/core/tokens/` et
   modèles du contrat dans `libs/mss/src/core/models/weda-patient-record.model.ts`, traduits
   fidèlement de l'ADR-007 § D2. weda2 fournit l'implémentation `WedaPatientRecordGateway` dans
   `app.config.ts`. Ses méthodes (`resolvePatient`, `getFilingContext`, `getFilingStatus`,
   `fileDocuments`, `openPatientRecord`) relaient vers `request()`.
   **Aucun élément d'interface n'est ajouté dans cette task** : les phases B et C les ajouteront.

## Definition of Done

- [x] Build passes (0 errors) ; Tests pass (0 failures, hors flaky préexistants documentés)
- [x] **api-mail** — tests unitaires :
  - [x] `weda_integration` présent dans `FeatureFlags.All`
  - [x] valeur de démarrage à froid `false`
  - [x] le nom `weda_integration` est figé en littéral (contrat partagé avec weda2 et Weda)
  - [x] weda2 lit le flag par `GET /api/v1/FeatureFlag`, qui évalue **par identité**. Le
    `GET /api/v1/FeatureFlag/{name}` n'applique pas les surcharges par identité
    (`IsEnabledAsync(featureName)`) : il ne convient pas à un flag activé pour des pilotes.
- [x] **Angular** — tests unitaires (écrits avec le code, pas rouges d'abord : écart assumé, voir Avancement) :
  - [x] `request()` résout sur la réponse portant le même `requestId`, et ignore les autres
  - [x] message ignoré si l'origine diffère, si la fenêtre émettrice n'est pas `window.parent`, ou si
    `source !== 'weda-host'`
  - [x] réponse `ok: false` → rejet avec le `code` d'erreur de l'hôte
  - [x] délai dépassé → rejet `timeout`, et la demande est retirée de la table
  - [x] hors mode embarqué → `unsupported`, aucun `postMessage`
  - [x] matrice d'activation de `WedaIntegrationService` : embarqué ou non × flag vrai, faux ou en
    erreur × capacités compatibles, incompatibles ou sans réponse. `available` n'est vrai que dans
    le seul cas tout-vrai
  - [x] hors mode embarqué, aucun appel au flag ni à `host-capabilities`
  - [x] les trois événements existants portent `version: 1`
- [x] `weda_integration` n'est lu **que** par `WedaIntegrationService` (vérifié par recherche dans le
  code, consigné dans la revue)
- [x] Couverture ≥ 90 % sur les fichiers créés (règle du dépôt Angular)
- [x] Aucune donnée de santé dans les logs : les demandes du pont ne sont journalisées que par leur
  `type` et leur `requestId`, jamais par leur `payload`

## Manual Test Plan

Prérequis : Weda en `https://localhost:44300`, avec le gestionnaire `host-capabilities` côté hôte ;
weda2 en `https://localhost:4200` ; proxy d'authentification et api-mail locaux.

1. Flag `weda_integration` **désactivé** dans Flagsmith → ouvrir WedaEchanges et activer le switch.
   La messagerie s'affiche comme avant. Dans la console de l'iframe, `available` est faux et aucune
   demande `host-capabilities` n'est émise.
2. Activer le flag pour l'identité de test, puis recharger → une demande `host-capabilities` part
   vers `https://localhost:44300`, la réponse revient avec le même `requestId`, et `available`
   devient vrai.
3. Ouvrir `https://localhost:4200/messagerie` dans un **onglet** (hors iframe), flag actif →
   `available` est faux, et ni `/api/v1/FeatureFlag` ni `host-capabilities` ne
   partent.
4. Couper le gestionnaire côté hôte (ou répondre `protocolVersion: 2`) → `available` reste faux, et
   la demande se termine en `timeout` au bout de 30 s.
5. Depuis la console de la page **hôte**, poster un message forgé vers l'iframe avec
   `source: 'weda-host'` et un `requestId` inconnu → il est ignoré, sans erreur.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — messagerie MSSanté intégrée au logiciel (intégration au dossier patient du
  LGC, exigence de classement visée par les phases suivantes)
- **Exigences DSR honorées** : non applicable dans cette phase — socle technique, aucun classement.
  La phase C portera RG-E009-034 « Visualiser et classer en 1 clic dans le dossier patient ».
- **INS** : non applicable — aucune INS ne transite dans cette phase. Elles transiteront en phase B
  (`resolve-patient`), toujours dans le `payload`, jamais dans une URL ni dans un log.
- **Authentification PS** : inchangée — session proxy partagée avec Weda (PSC / e-CPS, Keycloak)
- **Habilitations** : inchangées. Le pont est un transport, pas une autorité : Weda revérifie tout
  (ADR-007, D1).
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé. Aucun échange du pont ne journalise de contenu.
- **Consentement patient** : non applicable — aucun partage nouveau
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé — aucune donnée nouvelle n'est stockée. weda2 ne persiste aucun
  identifiant Weda (ADR client, § 5).
- **AIPD / impact RGPD** : inchangé dans cette phase. Le classement dans le dossier patient Weda
  (phase C) reste dans le périmètre du logiciel Weda.

## Branches

- `api-mail` (locale, non poussée) : feat/task-356-weda-integration-pont — créée depuis `origin/develop` le 2026-10-09
- `client-angular` (code-only) : la forge travaille sur la branche courante de `Client/Angular/`, soit `feature/nova-rewriting-mss-weda-integration` au 2026-10-09. L'humain gère la branche, le commit, le push et la PR TFS.
- Hors forge, `Weda` : `lotus/segur/17546-enveloppe-segur-v2-with-mss-api` (gestionnaire `host-capabilities` côté hôte)

## Avancement (2026-10-09)

Implémenté directement (hors `/develop`), à la demande de l'humain.

- **api-mail** (`feat/task-356-weda-integration-pont`, non commité) :
  - `FeatureFlags.WedaIntegration`, ajouté à `All`, valeur de démarrage à froid `false`, semé par
    `FlagsmithSeeder` ;
  - test de convention `WedaIntegration_IsDeclaredFailClosed`, et ancrage littéral des flags fermés
    étendu à 5 flags.
  - 41 tests `FeatureFlag*` verts. Ils ont été compilés dans un `--artifacts-path` séparé, parce
    qu'api-mail tournait et verrouillait `bin/`.
- **client-angular** (`feature/nova-rewriting-mss-weda-integration`, non commité) :
  - `EmbeddedHostService.request()` et son écouteur unique ;
  - `isHostResponse` ;
  - `WedaIntegrationService` ;
  - `WedaPatientRecordGateway` ;
  - `MSS_PATIENT_RECORD_GATEWAY` et les modèles `weda-patient-record.model.ts` ;
  - branchement dans `app.config.ts` et `AppComponent`.
  - Résultats : 2 654 tests weda2 verts ; couverture `lib/embedded` 98,6 % (lignes) ; ESLint propre.
    `tsc` ne remonte que les 2 erreurs préexistantes d'`antecedents`.
- **Weda** (`lotus/segur/17546-enveloppe-segur-v2-with-mss-api`, non commité) :
  - `Default.aspx` répond à `host-capabilities` (v1) ;
  - les autres types répondent `unsupported`, de même qu'une version ≠ 1 ;
  - messages d'une autre origine ignorés. Vérifié par simulation Node du script extrait de la page.

**Écart** : les tests Angular ont été écrits juste après le code et sont passés au premier
lancement. Ils n'ont pas été vus rouges.

**Reste** : le Manual Test Plan (navigateur, Flagsmith local) et les commits dans les trois dépôts.
