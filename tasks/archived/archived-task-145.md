# todo-task-145.md — Signatures sur mobile (CRUD + injection compose)

**Repos**: client-mobile
**Dependencies**: —
**Epic**: E012

## Objective

Porter sur `client-mobile` la gestion des **signatures** de `client-angular`
(`mss-signatures` + intégration `mail-compose`, E009-F014) :

1. **Écran Signatures** (accessible depuis Paramètres) : liste, création,
   édition, suppression, définition de la **signature par défaut**. Édition du
   contenu via le `html-editor` mobile existant.
2. **Intégration compose** : la signature par défaut est **auto-injectée** à
   l'ouverture d'un nouveau message / réponse / transfert (position et
   séparateur identiques à Angular) ; un **sélecteur** permet d'en changer ou
   de l'enlever.

US **frontend-only** : endpoints existants (`getSignatures`,
`getDefaultSignature`, `createSignature`, `updateSignature`,
`deleteSignature`, `setDefaultSignature` — Angular `mss-api.service.ts:672-752`).
Aucun changement backend ni DTO. Signatures cloisonnées par praticien
(backend task-023).

## Definition of Done

- [ ] Build passe (`npm ci && npm run build`) — 0 erreur
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`) — 0 échec
- [ ] `MssApiService` : 6 méthodes signatures + tests unitaires (succès + erreur)
- [ ] Écran Signatures : liste + CRUD complets, marquage visuel de la signature par défaut
- [ ] « Définir par défaut » exclusif (une seule signature par défaut)
- [ ] Compose : signature par défaut injectée à l'ouverture (nouveau/réponse/transfert), au bon emplacement (au-dessus de la citation en réponse)
- [ ] Sélecteur de signature dans le compose (changer / aucune)
- [ ] Suppression d'une signature avec confirmation ; suppression de la signature par défaut → plus d'injection
- [ ] Tests : CRUD, exclusivité du défaut, injection compose (3 modes)
- [ ] Libellés FR en dur ; `data-testid` sur liste, actions, sélecteur compose
- [ ] Aucune donnée de santé dans les logs client

## Manual Test Plan

- `cd Client/Mobile && npm start` ; Paramètres → Signatures
- Créer une signature « Dr Test — Cabinet » avec mise en forme (gras) ; la définir par défaut
- Nouveau message → la signature apparaît en pied de corps
- Répondre à un mail → signature au-dessus de la citation
- Dans le compose, changer de signature via le sélecteur → corps mis à jour
- Créer une 2e signature et la passer par défaut → la 1re perd le marquage
- Supprimer la signature par défaut → nouveau message sans signature, pas d'erreur

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors DSR nouvelle — parité web (E009-F014)
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : session existante, inchangée
- **Habilitations** : inchangées — signatures cloisonnées par praticien
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : CRUD signatures via endpoints existants (canal serveur)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — backend existant
- **AIPD / impact RGPD** : inchangé

## Branches
- `client-mobile` (pushed) : feat/task-145-mobile-signatures — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-145-mobile-signatures

## Stitch design log

- Projet `client-mobile` (id `10088502293310567548`, MOBILE). Aucun écran
  `signatures` existant dans le projet ; **best-effort & non bloquant** — l'écran
  a été conçu contre le socle « Clinical Precision » (Public Sans, primaire
  #005EB8, listes 56 px, cartes blanches) et les patterns mobiles existants
  (Paramètres, éditeur du compose). Génération/matérialisation d'une référence
  Stitch dédiée déférée à une passe `/stitch-design` humaine (le connecteur MCP
  a des pièges timeout→doublon — création non tentée dans le flux autonome).
- Écran nouveau : `signatures` (route `/signatures`).

## Develop log

- Repos touched : `client-mobile` (US mono-repo, frontend-only)
- DTOs published : no DTO change · Interop published : no interop change
- Commits :
  - client-mobile : `857066c` feat(mobile): signatures (CRUD + injection compose) (task-145)
- Local build / test : ✓ `npm run build` (0 erreur) · `npm test … ChromeHeadless` (**506 SUCCESS**, +37 vs baseline 469)
- Implémentation :
  - `signature.model.ts` : `SignatureDto`, `CreateSignatureDto`, `UpdateSignatureDto`,
    `EditableSignature` + `createEmptySignature`/`signatureFromDto` (miroir Angular).
  - `MssApiService` : 6 méthodes — `getSignatures` (GET /Signature), `getDefaultSignature`
    (GET /Signature/default), `createSignature` (POST), `updateSignature` (PUT /{id}),
    `deleteSignature` (DELETE /{id}), `setDefaultSignature` (PUT /{id}/default). `encodeURIComponent` sur l'id.
  - Écran `signatures/` (page module lazy, route `/signatures`) : liste (badge « Par
    défaut »), éditeur en `ion-modal` (nom, `mss-html-editor`, toggle défaut,
    suppression avec confirmation `AlertController`), refresh après save/delete,
    erreurs en toast (`extractProblemDetail`). Exclusivité du défaut portée par le
    backend, reflétée au reload.
  - Paramètres : section « Rédaction » → item de navigation « Signatures »
    (`data-testid=settings-signatures-nav`) → `/signatures`.
  - `mail-compose` : signaux `signatures`/`selectedSignatureId` ; `loadSignatures(inject)`
    charge la liste et injecte la signature par défaut à l'ouverture d'un message frais
    (nouveau/réponse/transfert) via `injectSignature` (au-dessus de la citation
    `<blockquote>` en réponse/transfert), gardé par le marqueur `<!-- signature -->` ;
    reprise de brouillon = corps authoritatif (pas de réinjection). Sélecteur
    `ion-select` (Aucune + signatures) → `onSignatureChanged` (strip + réinjection,
    jamais d'empilement). Reset nettoie les signaux.
- DOD self-check : build ✓ · tests ✓ · 6 méthodes API + tests succès/erreur ✓ ·
  écran liste + CRUD + marquage défaut ✓ · défaut exclusif (reload) ✓ · injection
  compose 3 modes au bon emplacement ✓ · sélecteur (changer/aucune) ✓ · suppression
  avec confirmation ✓ · libellés FR + data-testid (liste, actions, sélecteur) ✓ ·
  aucune donnée santé en log ✓. Rendu visuel déféré au test manuel (HAG).
- Next step : /forge-simplify task-145

## Simplify log

- Repos passed : `client-mobile`
- Applied & committed : — (aucune simplification appliquée)
- No change : `client-mobile` — reuse déjà appliqué par /develop (`mss-html-editor`,
  `extractProblemDetail`, pattern de confirmation `AlertController`, `UpdateSignatureDto`
  = alias de `CreateSignatureDto`, helpers purs `stripSignature`/`injectSignature`).
  Écran conçu en modale mobile-idiomatique (pas de calque du two-panel Angular).
  Extraction d'un service toast/erreur partagé = hors scope isolé (règle 6, toucherait
  plusieurs composants pré-existants) → non appliqué (quality-only, best-effort).
- Rolled back (validation RED) : aucun
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*
- Build / tests : ✓ verts (inchangés depuis /develop — 506 SUCCESS)
- Next step : /lint-mobile task-145 (api-mail & client-angular non touchés → /sonar & /lint-angular skip)

## Lint mobile log

- Repo : `client-mobile` (feat/task-145-mobile-signatures)
- Baseline `ng lint` : **All files pass linting** — 0 error, 0 warning, 0 fixable
- Iterations : aucune (code frais conforme à `conventions/angular.md` — control flow
  natif, sélecteurs `mss-`/`app-`, libellés FR en dur, `data-testid`)
- Commit : aucun (rien à corriger)
- Next step : /verify-visual task-145

## Visual verify log

- Écrans capturés : 2 / 2 — aucun écran blanc, aucune erreur console — commit `28d83e6`

| Écran | Route | Référence Stitch | Capture | Verdict fidélité |
|---|---|---|---|---|
| signatures | /signatures | — (écran neuf, pas encore matérialisé dans Stitch) | [`task-145/signatures.png`](https://github.com/codengine-technologies/HealthPlatform.Mobile/blob/28d83e6caf4bf577429ce44b3ec496edcadc46f1/e2e/screenshots/task-145/signatures.png) | Conforme « Clinical Precision » : en-tête « Signatures » + retour + « + », liste 56 px, badge bleu « Par défaut » sur la signature par défaut, chevrons de détail. Public Sans, primaire #005EB8. RAS. |
| mail-compose | /tabs/messages (compose) | Stitch `mail-compose` (existant) | [`task-145/mail-compose.png`](https://github.com/codengine-technologies/HealthPlatform.Mobile/blob/28d83e6caf4bf577429ce44b3ec496edcadc46f1/e2e/screenshots/task-145/mail-compose.png) | Signature par défaut auto-injectée dans le corps (« Dr Démo / Cabinet médical », gras préservé) + sélecteur « Signature : Dr Démo — Cabinet ▾ » sous l'éditeur. Reste du compose inchangé. RAS. |

- Écrans non mappés (screens.json) : aucun (mapping `signatures` ajouté)
- APIs non mappées loguées : aucune (fixture `/api/v1/Signature` + `/default` ajoutée à capture.mjs)
- Note outillage : `screens.json` (écran `signatures`) + `capture.mjs` (routes Signature) enrichis pour matérialiser la liste et l'injection compose.
- Next step : /review task-145

## PRs

- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/49 — label `awaiting-human-merge`

## Code Review Summary

- Verdict : **APPROVED** — 0 bloquant.
- Build ✓ · Tests ✓ (**506 SUCCESS**, +37 vs baseline 469) · `ng lint` All files pass · `/verify-visual` 2/2 (aucun écran blanc).
- **Correctness** : parité fidèle E009-F014 ; `encodeURIComponent` sur l'id ; injection gardée par marqueur (jamais d'empilement), au-dessus de la citation en réponse/transfert ; reprise de brouillon = corps authoritatif.
- **Contrainte métier** : exclusivité du défaut portée par le backend, reflétée au reload ; signatures cloisonnées par praticien.
- **Security** : aucun secret, aucune donnée de santé en log ; toasts via `extractProblemDetail` (RFC 7807).
- **Test coverage** : 37 tests (6 méthodes API succès/erreur, page CRUD + exclusivité + suppression confirmée, injection compose 3 modes + sélecteur + non-réinjection brouillon).
- **Note non bloquante** : `setDefaultSignature` testé mais non câblé à une action rapide de liste (défaut réglé via le toggle de l'éditeur) — amélioration UX possible.
- Qualité : /sonar skipped — api-mail non touché.

## Merged

- Merged : 2026-07-12 (human-triggered `/merge --i-tested`)
- Squash commits :
  - client-mobile : `3ac9d45` (PR #49 squash-merged & closed, remote branch deleted, local kept)
- develop CI : voir run ci-dessous (build-android ~3m30s, hors fenêtre 2 min — voir rapport)
