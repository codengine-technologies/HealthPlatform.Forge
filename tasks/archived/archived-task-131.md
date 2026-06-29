# todo-task-131.md — Synthèse IA d'un email sur le client mobile

**Repos**: client-mobile
**Dependencies**: —
**Epic**: E012

## Objective

Porter sur `client-mobile` la fonctionnalité **« Synthèse IA »** déjà
disponible dans `client-angular` (vue `mail-detail`) : depuis le détail d'un
email, le médecin peut déclencher l'affichage d'une **synthèse rédigée par
l'IA** du message courant, rendue en markdown, avec un en-tête de contexte
(titre du document / sujet, patient, praticien émetteur, expéditeur, date).

US **frontend-only** : le endpoint backend existe déjà en production et est
consommé tel quel par `client-angular`
(`GET /api/v1/mail/folders/{foldername}/emails/summary/{emailid}` →
`MailSummaryDto { uid, folderPath, from, markdownSummary }`, mis en cache Redis
côté serveur, génération IA côté `api-mail`). **Aucune modification backend ni
DTO**. Le scope est donc limité au seul repo `client-mobile` — c'est une mise
en parité d'affichage conforme à la vision E012 (« miroir structurel du client
Angular »). Le panneau **AI Chat multi-emails** d'Angular est **hors scope** de
cette US (feature distincte, US ultérieure si besoin).

## Comportement attendu (parité Angular)

- Dans le détail d'un email, une **action « Synthèse IA »** est disponible
  (bouton de la barre d'action / en-tête, ou entrée de l'action sheet « Actions »
  — au choix du dev mobile selon l'ergonomie Ionic, cf. `/stitch-design`).
- Au déclenchement, l'app appelle
  `GET /api/v1/mail/folders/{folderPath}/emails/summary/{uid}` (mêmes en-têtes
  d'auth que les autres appels, via l'intercepteur existant).
- **Pendant la génération** : indicateur de chargement (ion-spinner /
  ion-progress-bar) avec le libellé « Génération de la synthèse en cours… ».
- **Succès** : affichage d'un panneau de synthèse contenant
  - un en-tête de contexte : titre (titre du 1ᵉʳ document médical si présent,
    sinon sujet de l'email), patient (nom + âge si dispo, dérivé de
    `content.medicalDocuments[0]`), praticien émetteur + spécialité, expéditeur,
    date ;
  - le corps : `markdownSummary` **rendu en HTML** (titres, gras, italique,
    listes, retours ligne) puis **assaini** avant rendu (Angular `DomSanitizer`
    — pas de `bypassSecurityTrustHtml` sur du HTML non nettoyé).
- **Synthèse indisponible** (le backend renvoie `404` avec
  `ProblemDetails` « AI summary is not available » quand le pipeline IA est
  désactivé) : afficher un message neutre **« Synthèse IA non disponible »**,
  **pas** une erreur bloquante ni une alerte d'échec.
- **Autre erreur** (réseau, 5xx) : message d'erreur lisible
  « Erreur lors de la génération de la synthèse » (réutiliser le pattern
  `extractProblemDetail` existant), réessayable.
- Le panneau se **referme / se masque** (toggle) sans recharger l'email.

## Points d'implémentation (indicatifs — le dev mobile reste maître)

- Ajouter `getEmailSummary(folderPath, uid)` à
  `src/app/core/services/mss-api.service.ts` (Observable<MailSummaryDto>).
- Ajouter le type `MailSummaryDto` dans `src/app/core/models/` (transposition
  TS du contrat backend : `{ uid, folderPath, from, markdownSummary }`).
- Composant d'affichage de la synthèse (miroir de
  `mss-mail-summary` Angular), intégré au détail
  (`src/app/features/mail/components/mail-detail/`).
- Le champ `summary` déjà présent sur `MailContentDto` mobile **n'est pas** la
  synthèse IA (il n'est pas alimenté par ce endpoint) — ne pas le réutiliser à
  tort ; la synthèse vient de l'appel dédié.

## Definition of Done

- [ ] Build passe (`npm ci && npm run build`) — 0 erreur
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`) — 0 échec
- [ ] `MssApiService.getEmailSummary` ajouté + test unitaire (succès + 404 « non disponible » + erreur)
- [ ] Composant de synthèse : test de rendu (état chargement, succès avec markdown rendu, état « non disponible »)
- [ ] Markdown de la synthèse **assaini** avant rendu (pas d'injection HTML/XSS depuis le contenu IA)
- [ ] Cas `404 « AI summary is not available »` géré en message neutre (pas d'alerte d'échec)
- [ ] Aucun libellé en dur hors FR (app mobile : libellés FR en dur assumés, cf. parité client-angular)
- [ ] `data-testid` sur l'action de déclenchement et le conteneur de synthèse
- [ ] Aucune donnée de santé en clair dans les logs (contenu de la synthèse, patient, INS jamais loggés côté client)
- [ ] Parité visuelle/structurelle avec la « Synthèse IA » de `client-angular` (en-tête contexte + corps markdown)

## Manual Test Plan

- Lancer l'app mobile : `cd Client/Mobile && npm start` (ou via Capacitor / navigateur)
- Se connecter avec une session MSSanté de test pointant sur l'`api-mail` de test (pipeline IA **activé**)
- Ouvrir un email **contenant un document médical** (pour vérifier l'en-tête patient/praticien)
- Déclencher l'action **« Synthèse IA »** dans le détail de l'email
- Attendu :
  - indicateur de chargement « Génération de la synthèse en cours… » ;
  - puis affichage de la synthèse : en-tête (titre, patient + âge, praticien +
    spécialité, expéditeur, date) + corps markdown rendu (titres/listes/gras) ;
  - masquage du panneau au re-clic, sans rechargement de l'email.
- Ouvrir un email **sans document médical** : la synthèse s'affiche, l'en-tête
  retombe sur le sujet / l'expéditeur, sans planter.
- Tester avec un `api-mail` dont le pipeline IA est **désactivé** : attendu
  message neutre **« Synthèse IA non disponible »**, pas d'alerte d'erreur.
- Couper le réseau et déclencher : attendu message d'erreur lisible et
  réessayable, l'app ne crashe pas.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie sécurisée de santé, client mobile)
- **Vague Ségur** : hors exigence DSR stricte — la synthèse IA est un service à
  valeur ajoutée d'aide à la lecture, pas une exigence de référencement ; le
  couloir MSSanté sous-jacent reste celui de l'EPIC E012
- **Exigences DSR honorées** : non applicable — fonctionnalité de confort,
  aucune exigence DSR nouvelle ; le transport/affichage MSSanté est couvert par E012
- **INS** : non applicable — affichage en lecture seule de l'identité patient
  déjà présente dans le document médical reçu ; aucune manipulation / récupération
  INSi déclenchée par cette US. L'INS / le NIR ne sont **jamais** loggés côté client
- **Authentification PS** : aucune nouvelle authentification — réutilise la
  session MSSanté du médecin déjà établie (PSC / e-CPS en amont). Niveau eIDAS
  inchangé par rapport à l'accès à la boîte
- **Habilitations** : inchangées — l'accès à la synthèse suit l'accès à l'email
  (le médecin titulaire de la boîte). Aucune délégation introduite
- **Interop CI-SIS** : non applicable — la synthèse est un texte IA propriétaire
  (markdown), pas un échange CDA/FHIR. Les documents CDA sous-jacents sont parsés
  en amont côté `api-mail` (hors scope de cette US frontend)
- **Tracé PGSSI-S** : la consultation de synthèse est journalisée **côté serveur**
  par `api-mail` (`GetEmailSummary`, scope opération existant) — aucun nouveau
  journal côté mobile. Pas de log client du contenu
- **Consentement patient** : non applicable — le médecin consulte sa propre boîte
  MSSanté ; pas d'alimentation DMP / Mon Espace Santé, pas de partage externe
- **Référentiels métier** : aucun — pas de codage terminologique introduit
- **Hébergement HDS** : oui — la synthèse est une donnée de santé (DSCP) produite
  et hébergée par l'`api-mail` existant (environnement HDS du backend) ;
  transit HTTPS uniquement, pas de persistance disque côté mobile
- **AIPD / impact RGPD** : inchangé — la chaîne de traitement IA et l'AIPD
  associée sont déjà en place côté `api-mail` (feature déjà en production sur
  `client-angular`) ; cette US n'ouvre qu'un nouveau canal de consultation mobile,
  sans nouveau traitement

## Branches
- `client-mobile` (pushed) : feat/task-131-mobile-ai-email-summary — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-131-mobile-ai-email-summary

## Stitch design log

- Pas de nouvel écran Stitch : la « Synthèse IA » est un **sous-panneau
  repliable** ajouté à l'écran existant `mail-detail` (déjà couvert par Stitch),
  pas une nouvelle page. La traduction Ionic reprend la structure de référence
  du composant client-angular `mss-mail-summary` (carte d'en-tête à indicateur
  + corps markdown). `/stitch-design` non invoqué (best-effort, hors périmètre
  écran-complet).

## Develop log

- Repos touched : client-mobile
- DTOs published : no DTO change (frontend-only port, backend endpoint already in prod)
- Interop published : no interop change
- Commits :
  - client-mobile : 8a37dcb feat(mobile): add AI email summary panel to mail detail (task-131)
- Local build / test : ✓ client-mobile (`npm run build` 0 error ; `npm test` 162/162 green)
- DOD self-check :
  - ✓ Build passe / Tests passent
  - ✓ MssApiService.getEmailSummary + tests (succès + 404)
  - ✓ Composant mss-mail-summary + tests (loading/success/non-disponible/erreur/retry, en-tête, markdown)
  - ✓ Markdown assaini avant rendu (échappement HTML préalable, anti-XSS) + test dédié
  - ✓ 404 « AI summary is not available » → état neutre « Synthèse IA non disponible » (pas d'alerte)
  - ✓ Libellés FR en dur
  - ✓ data-testid sur le déclencheur (detail-summary-toggle) et le panneau (detail-summary-panel + sous-états)
  - ✓ Aucune donnée de santé loggée côté client (pas de console.log de synthèse/patient/INS)
  - ~ Parité visuelle : structure mirroir (carte en-tête + corps markdown) — rendu final à valider à l'œil (HAG)
- Next step : /forge-simplify task-131

## Simplify log
- Repos passed : client-mobile
- Applied & committed : client-mobile: 1 file (8f4314d) — reuse `getPatientAge()` helper instead of a private `calculateAge()` duplicate
- No change : —
- Rolled back (validation RED) : none
- Skipped findings (noted, not applied) :
  - "Remove unused DatePipe import" — **false positive** : the template uses the `| date` pipe, DatePipe is required (removing breaks the build)
  - "Move 404→neutral mapping into the service" — design change, single consumer ; kept in component (acceptable altitude, parity with Angular)
  - "Extract markdownToHtml to a shared util" — speculative (single consumer) ; reuse agent agreed it's not a current reuse issue, parity-inlined like Angular
  - "Extract resetLoadState() helper" — single call site, not duplication
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*
- Build / tests : ✓ green on client-mobile (build 0 error ; 162/162 tests)
- Next step : /lint-mobile task-131

## Lint mobile log
- Baseline `npm run lint` (ng lint) : **All files pass linting** — 0 error, 0 warning
- Iterations run : 0 (nothing to fix)
- Fixes committed : none (tree clean)
- Build / tests : already green from /develop + /forge-simplify (build 0 error ; 162/162 tests)
- Next step : /review task-131

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/34 — label `awaiting-human-merge`

## Code Review Summary
- Verdict : **APPROVED** (0 blocking, 1 non-blocking suggestion)
- client-mobile :
  - `mss-api.service.ts` (getEmailSummary) — ✅ co-localisé avec les endpoints mail, JSDoc 404
  - `mail-summary.model.ts` — ✅ miroir TS du contrat backend
  - `mail-summary.component.ts` — ✅ états signaux nets, anti-XSS (échappement avant rendu), réutilise getPatientAge
  - `mail-detail.component.{ts,html,scss}` — ✅ toggle + panneau, data-testid, scss tokens app
  - tests (service + composant) — ✅ couvrent succès/404/erreur/retry, fallback en-tête, échappement markdown
- Suggestion non bloquante : `safeMarkdownHtml` pourrait être un `computed()` — laissé en getter par cohérence avec la convention du repo (`mail-detail`).
- Validation : build ✓ 0 erreur, tests ✓ 162/162, lint ✓ clean.

## Merged
- Date : 2026-06-28
- `client-mobile` : squash commit `5bf38556a0704c837570fd5c4509973db5a89122` — PR #34 mergée (squash), branche remote supprimée (locale conservée)
- develop CI : aucun workflow GitHub Actions configuré sur le repo (rien à vérifier ; PR « no checks reported », mergeState CLEAN au merge)
