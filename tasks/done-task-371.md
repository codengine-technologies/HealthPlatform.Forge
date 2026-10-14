# todo-task-371.md — Le mail affiché est toujours celui qui est sélectionné : contenu, documents médicaux, biologie et synthèse IA

**Repos**: client-angular, client-mobile, api-mail (catalogue e2e `Api/Mail/e2e/scenarios.yml` seulement)
**Dependencies**: — (aucune). task-372 (import Weda) et task-373 (dossier patient) en dépendent pour leur part d'identito-vigilance.
**Epic**: E009
**Single frontend**: false — weda2 et le mobile (décision humaine du 2026-10-13).
**Priorité**: **1** — le contenu, les documents CDA, les résultats de biologie et le panneau d'acquittement d'un mail s'affichent sous l'en-tête d'un autre : un résultat critique peut être acquitté, un document importé ou un compte rendu lu pour le mauvais patient.

> **Origine.** Audit de détection de bugs du client Angular du 2026-10-13
> (`Docs/audits/client-angular-audit-bugs-20261013.md`, **ANG-08 ✔, ANG-21, ANG-40, ANG-41, ANG-55, ANG-73**).

## Ce qui est établi

- **ANG-08** — `mail-detail.component.ts:737-750, 777-806` : chaque sélection lance un `getEmailContent` indépendant, sans annulation ; `mailContent` n'est pas vidé au changement de mail. Pendant chaque chargement — et durablement si A répond après B ou si B échoue — le corps, les onglets CDA, la biologie, les pièces jointes, le panneau d'acquittement et la section Patient de B montrent le contenu de A (`mail-detail.component.html:705-740, 922-928`). Le garde `originalLoaded` (task-350) ne protège que Répondre et Transférer.
- **ANG-21** — `mail-summary.component.ts:48-52, 126-147` : la synthèse IA de A (génération lente) remplace celle de B sous l'identité patient de B ; `showSummary` n'est pas remis à faux au changement.
- **ANG-40** — l'identité d'un mail est réduite à son UID (`lastLoadedUid`, `updateMailInList`) alors que les UID repartent à 1 dans chaque dossier : dans la vue « Mails du patient », Archives/42 après INBOX/42 garde le contenu d'INBOX/42.
- **ANG-41 / ANG-55** — la vue en lecture seule (doublons, widget patient) et la fenêtre du document patient appliquent des réponses non annulées : le médecin supprime le mauvais exemplaire, ou lit le PDF d'un document sous le titre d'un autre.
- **ANG-73** — `mail-body.component.ts:61-74` remet l'onglet et « Afficher les images » à zéro à chaque changement d'entrée, pas seulement au changement de mail.

## Objective

Qu'un mail, ses documents médicaux, ses résultats et sa synthèse ne s'affichent **que** sous son propre en-tête : jamais de contenu, de document ou de synthèse d'un autre mail, même pendant un chargement, après un échec, ou quand les réponses arrivent dans le désordre.

### Périmètre

1. **Identité `(folderPath, uid)`** partout où un mail est désigné : chargement, cache local, mises à jour de la liste, synthèse, accusés.
2. **Chargement du contenu** annulable (`switchMap` sur `(folderPath, uid)`) ; contenu vidé à chaque changement de mail ; corps, onglets CDA, panneau latéral et section Patient rendus **seulement** quand le contenu chargé appartient au mail affiché.
3. **Synthèse IA** : requête annulée au changement de mail, réponse ignorée si elle ne correspond plus ; `showSummary` remis à faux.
4. **Vue en lecture seule** et **fenêtre du document** : annulation et garde de clé sur chaque chargement (contenu, PDF).
5. **`mail-body`** : réinitialisation de l'onglet et des images seulement au changement de `(folderPath, uid)`.

## Definition of Done

- [ ] Build et tests weda2 verts
- [ ] Tests unitaires et de composant rouges d'abord :
  - [ ] sélection de A puis de B, réponse de A arrivée en dernier : le contenu affiché est celui de B
  - [ ] pendant le chargement de B, ni le corps, ni les documents médicaux, ni le panneau d'acquittement, ni la section Patient de A ne sont rendus
  - [ ] chargement de B en échec : aucun contenu de A ne reste affiché
  - [ ] INBOX/42 puis Archives/42 : le contenu est rechargé
  - [ ] synthèse de A lente, B rapide : la synthèse affichée est celle de B
  - [ ] vue en lecture seule et fenêtre du document : une réponse d'un élément quitté est ignorée
  - [ ] un enrichissement SSE du même mail ne remet pas l'onglet ni « Afficher les images » à zéro
- [ ] Scénario E2E-DETAIL-005 « Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent » ajouté au catalogue (angular `requis` ; mobile : à trancher au `/start`, voir l'arbitrage), implémenté dans weda2 avec une latence injectée sur le premier mail
- [ ] Trou du filet : scénario prouvé rouge sur le code d'avant, ligne ajoutée dans `conventions/e2e.md`
- [ ] Aucune donnée de santé ajoutée aux journaux

> **⚠️ Arbitrage humain requis — le client mobile.** Le mobile n'a pas été audité ; son écran de lecture
> a pu reproduire le même chargement non annulé. Inclure `client-mobile` (scénario `requis` des deux
> côtés), ou déclarer une divergence temporaire avec une task mobile de vérification ?
>
> **Décision humaine (2026-10-13, avant `/forge 368 to 381`) : inclure le mobile.** `/develop` audite le
> même périmètre sur `client-mobile` et y corrige les défauts trouvés ; les scénarios e2e de la task sont
> `requis` sur angular **et** mobile.

## Manual Test Plan

1. Mail A portant un CDA lourd, mail B sans document : cliquer sur A puis aussitôt sur B → seuls le contenu et les documents de B s'affichent, à aucun moment ceux de A.
2. Couper le réseau, cliquer sur B → message d'échec, aucun contenu de A visible.
3. Ouvrir la synthèse IA sur A, passer aussitôt à B → la synthèse affichée est celle de B.
4. Vue « Mails du patient » : ouvrir deux mails de même numéro dans deux dossiers → chacun affiche son propre contenu.
5. Dialogue « Nettoyer les doublons » : passer vite d'un exemplaire à l'autre → l'aperçu suit toujours l'exemplaire sélectionné.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif
- **Exigences DSR honorées** : non applicable — rétablit l'identito-vigilance de l'affichage (un document est présenté avec le patient auquel il appartient)
- **INS** : non applicable en écriture ; la task garantit que l'identité affichée est celle du document affiché
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : CDA r2 — affichage seulement, aucun changement de format
- **Tracé PGSSI-S** : inchangé
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — DSCP affichées, aucune nouvelle donnée stockée
- **AIPD / impact RGPD** : inchangé

## Branches
- `api-mail` (pushed) : fix/task-371-mail-affiche-selectionne — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-371-mail-affiche-selectionne (catalogue e2e `Api/Mail/e2e/scenarios.yml` uniquement)
- `client-mobile` (pushed) : fix/task-371-mail-affiche-selectionne — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/fix/task-371-mail-affiche-selectionne
- `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` (snapshot au `/start` : `feature/nova-rewriting-mss-weda-integration`) — humain gère branche, commit, push, PR TFS

## Develop log

> **Reprise (2026-10-14)** — le premier passage (`/forge 368 to 381`, nuit du 13 au 14) a été annulé par
> l'humain (control plane `50723a1`) ; la task est reprise une à une. Même règle que la reprise de task-368 :
> les commits mobile et catalogue du premier passage sont **réutilisés** (cherry-pick sur les branches
> recréées), la partie weda2 est **refaite test d'abord**. Le travail weda2 annulé (`915a9339`, mêlé aux
> tasks 368-370) n'a servi que de référence.

- Repos touchés : api-mail (catalogue e2e), client-mobile, client-angular (code-only)
- DTOs publiés : aucun changement de contrat — Interop : aucun

### Commits (repos poussés)

| Repo | Commit | Contenu |
|---|---|---|
| api-mail | `77c1233f` | catalogue : E2E-DETAIL-005 v1 (mobile et angular `requis`) — cherry-pick de `62195d31` |
| client-mobile | `f5891cc` | chargement annulé et réponses périmées ignorées (lecture, rechargement SSE), identité (dossier, uid) dans l'état, les actions, les accusés et les patches SSE, synthèse annulée et fermée au changement, `mail-body` remis à zéro au seul changement de mail, aperçu / fenêtre du document / chronologie gardés par clé, spec E2E-DETAIL-005 — cherry-pick de `ce17a66`, 2 conflits avec task-368 résolus (les deux tests e2e gardés ; garde de clé du PDF + `asPdf` de task-368) |
| client-mobile | `c325b75` | specs de 371 alignés sur 368 : clé de document composite dans le test de contenu distant, PDF retypé reconnu à sa taille ; mutation (garde + désabonnements retirés) → 3 rouges |
| client-mobile | `523bdb8` | E2E-DETAIL-005 : réponse de A **retenue** jusqu'à l'affichage de B (voir « Preuve e2e ») |

### client-angular (weda2) — refait test d'abord (code-only, non commité)

| Bloc | Rouge vu | Vert |
|---|---|---|
| 1. `mail-key.util` — identité `(folderPath, uid)` | module absent | 3 |
| 2. `mail-detail` (ANG-08, ANG-40) — chargement par `switchMap`, `loadedContent` = contenu du seul mail affiché (corps, onglets, acquittement, section Patient, import Weda, Répondre/Transférer), contenu vidé au changement, `showSummary` remis à faux, chaîne de versions annulable, rechargement de nettoyage annulé, `resetKey` du panneau en (dossier/uid), accusés de lecture par clé | 9 rouges (`mail-detail.stale-content.spec.ts`) : A après B, rendu pendant le chargement, échec de B, INBOX/42 → Archives/42, synthèse, SSE, B texte brut | 64 (dossier mail-detail) |
| 3. Aperçu de pièce jointe — téléchargement annulé au changement d'aperçu ou de mail | 1 rouge (le blob de A posé sous la pièce de B) | 1 |
| 4. `mail-body` (ANG-73) — onglet, modes et PDF remis à zéro au seul changement de (dossier, uid) ; `revealKey` du cadre : « Afficher les images » survit à un SSE, pas à un autre mail même à HTML identique ; **message texte brut** (`text/plain`, sans HTML ni document) affiché — il ne l'était pas du tout | 4 rouges | 10 |
| 5. `mail-state` — `updateMailInList`, `applyBiologyAck`, `removeMailFromList`, `moveMailFromList` acceptent le dossier ; retrait et pierre tombale dans le dossier du message (un doublon d'Archives supprimé depuis INBOX ne retire plus INBOX/42) ; tous les appelants de `mail-detail` et `mail-list` passent le dossier | 3 rouges + 1 prouvé par mutation (son premier passage tombait sur une aide de test hors de portée) | 43 |
| 6. Synthèse IA (ANG-21) — `features/…/mail-summary` et carte du widget : requête annulée, clé (dossier, uid) | 5 rouges | 6 |
| 7. Vue en lecture seule (ANG-41) — chargement et PDF annulés et gardés par clé, aperçu de l'ancien retiré pendant le chargement | 3 rouges | 6 |
| 8. Fenêtre du document patient (ANG-55) — PDF annulable par clé (dossier, uid, fichier), abandonné au changement de document et à la fermeture | 4 rouges | 6 |

**Preuve de mutation (unitaire)** : `removeMailFromList` sans le dossier → rouge sur l'assertion visée
(`expected [] to deeply equal [INBOX/42]`), restauré.

**Preuve e2e — E2E-DETAIL-005** (backend e2e + weda2 servis, `--serve-only`) :
- weda2, correctif : vert. **Mutation** « code d'avant » (`mergeMap` au lieu de `switchMap`, contenu rendu
  sans garde de propriétaire ; `grep -c MUTATION` = 2, bundle 2 → 3, +15 s) : **vert** avec la latence CDP
  du premier passage — le test ne prouvait rien. Deux causes : la latence était levée avant le départ de la
  requête de A, puis Chrome servait B derrière A. Test réécrit : réponse de A retenue (`route.fetch` +
  `fulfill` une fois B affiché). Sous mutation : **rouge sur l'assertion visée** (« le contenu du second
  reste affiché » — corps de `mail-flagge` sous l'objet de `mail-lu`). Restauré (MUTATION = 0, nouveau
  bundle, +15 s) : vert 2 fois. Consigne ajoutée : `conventions/e2e.md` › `latence-cdp-n-ordonne-pas`.
- mobile : même réécriture. Vert sur le correctif ; **vert aussi** sous mutation des gardes, puis sur la page
  de lecture de `develop` : le retour à la liste détruit la page de A, sa réponse tardive n'atteint plus
  l'écran. La course existe quand une même instance change de mail ; elle est prouvée par les tests unitaires
  de `MailDetailPage`, **4 rouges** sur la page de `develop`, verts sur le correctif. Le scénario reste un
  filet de non-régression côté mobile.
- Rejoués verts sur les deux clients : E2E-DETAIL-001/005, E2E-SECURITY-001 (+ E2E-PATIENT-* sur weda2).
- Trou du filet : ligne ajoutée dans `conventions/e2e.md`.

**Fichiers modifiés (client-angular, non commités sur `feature/nova-rewriting-mss-weda-integration`)** :
- nouveaux : `core/utils/mail-key.util.ts` (+spec), `mail-detail/mail-detail.stale-content.spec.ts`,
  `features/mail/components/mail-summary/mail-summary.component.spec.ts`, `ui/mail-summary/mail-summary.component.spec.ts`
- modifiés : `mail-detail.component.{ts,html}`, `mail-body.component.{ts,html}` (+spec),
  `medical-html-frame.component.ts`, `mail-list.component.ts`, `mail-read-only-view.component.ts` (+spec),
  `features/…/mail-summary.component.ts`, `ui/mail-summary/mail-summary.component.ts`,
  `mail-state.service.ts` (+spec), `medical-document-modal.component.ts` (+spec),
  `e2e/mss-e2e/specs/functional.e2e.ts` (E2E-DETAIL-005)
- ⚠️ `functional.e2e.ts` porte un scénario **requis** côté angular : à commiter sur TFS **avant** le merge de
  la PR api-mail (conventions/e2e.md, test-angular-non-commite).

### Validation

- weda2 : `npm run build` ✓ ; `npm test` ✓ — 11 projets, 2 700 tests (14 skipped, préexistants), 0 échec,
  aucune erreur non gérée ; libs/mss 860/860. `tsc --noEmit` e2e ✓. ESLint des fichiers touchés : 0 erreur
  (2 erreurs Prettier corrigées à la main ; les warnings `max-lines` / `require-example` sont ceux de HEAD).
- client-mobile : `npm run build` ✓ ; tests 1 083/1 083 ✓ ; e2e `tsc` ✓, ESLint ✓.
- api-mail : catalogue seul, pas de code — hook de push ✓.

### Passe qualité (/simplify)

- client-angular : relecture du diff (chargement, clés, annulations) — aucun nettoyage à appliquer.
- client-mobile : commit réutilisé, déjà passé par la chaîne complète au premier passage ; ajouts de cette
  reprise limités aux specs — rien appliqué.
- api-mail : catalogue seul — sans objet.

### Règle 1b

Aucun comportement atteignable par un endpoint n'est modifié (correctifs côté clients) : pas de test
d'intégration api-mail à écrire.

### Hors périmètre, relevé

- Actions groupées dans la vue « Mails du patient » (dossier virtuel) : l'API est appelée avec le chemin du
  dossier virtuel et une sélection par UID seul (`selectedMailUids`) — défaut préexistant, non traité ici.
- `mail-notification-widget` retire une carte par UID seul (boîte de réception seulement, risque faible).

### DOD self-check

- Build et tests weda2 verts ✓
- Tests rouges d'abord : A/B réponse tardive ✓, rien de A pendant le chargement de B ✓, échec de B ✓,
  INBOX/42 → Archives/42 ✓, synthèse A lente / B rapide ✓, lecture seule et fenêtre du document ✓,
  SSE ne remet ni l'onglet ni les images à zéro ✓
- E2E-DETAIL-005 au catalogue, implémenté weda2 (et mobile) ✓ ; prouvé rouge sur le code d'avant (weda2) ✓
- Trou du filet consigné ✓
- Aucune donnée de santé ajoutée aux journaux ✓ (aucun log ajouté)
- Next step : /sonar task-371 (api-mail touché, catalogue seulement → skip attendu)

## Sonar log

- Skipped : api-mail ne porte que le catalogue e2e (`e2e/scenarios.yml`), aucun code C# — rien à analyser.

## Lint log

- client-angular (Mode A, base `origin/next`, `tag:scope:mss`) : 0 erreur au relevé initial (warnings seulement, préexistants) — aucune itération, aucun fichier modifié.

## Lint mobile log

- client-mobile : `npm run lint` — « All files pass linting » au relevé initial. Aucune itération, aucun commit.

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | client-mobile et api-mail touchés | ✅ verte | 36 verts, 0 flaky, 0 rouge, 0 quarantaine | 6 min 20 s |
| angular | client-angular et api-mail touchés | ✅ verte | 40 verts, 0 flaky, 0 rouge, 1 quarantaine (passée) | 5 min 51 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ fix/task-371-mail-affiche-selectionne (E2E-DETAIL-005 v1)
- Quarantaines : [angular] E2E-COMPOSE-002 (correction : task-350) — joué vert
- Divergences ouvertes : aucune
- Parcours touchés sans spec e2e modifié : aucun (E2E-DETAIL-005 ajouté sur les deux suites)
- Démontage : complet (ports libres, aucun conteneur e2e résiduel)
- ⚠️ Le test Angular d'E2E-DETAIL-005 est **non commité** (code-only) : à commiter sur TFS avant le merge de la PR api-mail.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 2 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 1 | headless | Créer puis supprimer un contact | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 1 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 1 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 1 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/296 — label `awaiting-human-merge` (catalogue E2E-DETAIL-005)
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/94 — label `awaiting-human-merge`
- `client-angular` : code-only — humain gère commit/push TFS et ouverture PR, branche `feature/nova-rewriting-mss-weda-integration`. **`functional.e2e.ts` (E2E-DETAIL-005, requis) à commiter avant le merge de la PR api-mail.** Fichiers modifiés :
  - `front/e2e/mss-e2e/specs/functional.e2e.ts`
  - `front/libs/mss/src/features/mail/components/mail-body/mail-body.component.html`
  - `front/libs/mss/src/features/mail/components/mail-body/mail-body.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-body/mail-body.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.html`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-read-only-view/mail-read-only-view.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-read-only-view/mail-read-only-view.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-summary/mail-summary.component.ts`
  - `front/libs/mss/src/features/mail/components/medical-html-frame/medical-html-frame.component.ts`
  - `front/libs/mss/src/features/mail/services/mail-state.service.spec.ts`
  - `front/libs/mss/src/features/mail/services/mail-state.service.ts`
  - `front/libs/mss/src/features/patient/components/medical-document-modal/medical-document-modal.component.spec.ts`
  - `front/libs/mss/src/features/patient/components/medical-document-modal/medical-document-modal.component.ts`
  - `front/libs/mss/src/ui/mail-summary/mail-summary.component.ts`
  - `front/libs/mss/src/core/utils/mail-key.util.spec.ts`
  - `front/libs/mss/src/core/utils/mail-key.util.ts`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.stale-content.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-summary/mail-summary.component.spec.ts`
  - `front/libs/mss/src/ui/mail-summary/mail-summary.component.spec.ts`

## Code Review Summary

**APPROVED** — 0 bloquant, 1 suggestion hors périmètre.

| Repo | Fichiers | Verdict |
|---|---|---|
| api-mail | `e2e/scenarios.yml` | ✅ scénario cohérent avec les deux suites (v1, seed `mail-flagge` / `mail-lu`) |
| client-mobile | page de lecture, `mail-detail`, `mail-state`, `mail-actions`, `mail-summary`, `mail-body`, fenêtre du document, chronologie, spec e2e | ✅ contenu exposé seulement pour le mail affiché, actions tardives gardées (`isShown`), aperçu annulé |
| client-angular | `mail-detail`, `mail-body` + cadre, `mail-state` + appelants de `mail-list`, synthèses, lecture seule, fenêtre du document, e2e | ✅ `switchMap` + `loadedContent`, clés (dossier, uid) partout, PDF et aperçus annulables |

- Règle 1b : aucun comportement atteignable par un endpoint n'est modifié — sans objet.
- Double verrou e2e : `## E2E log` vert (mobile 36/36, angular 40/40, parité verte).
- Validation `/review` : api-mail build ✓, tests ✓ (6 951 verts, 16 skipped) ; client-mobile build ✓, tests 1 083/1 083 ✓ (un premier passage, lancé **en parallèle** des tests .NET, a perdu 3 tests de sélection de `HtmlEditorComponent`, non touché par la task — rejoué seul : vert) ; client-angular build ✓, tests ✓ (11 projets).
- ⚠️ Suggestion : actions groupées de la vue « Mails du patient » (dossier virtuel, sélection par UID seul) — défaut préexistant, à traiter dans une task dédiée.

## Timings

*(généré par `tools/timing/report.sh --task task-371 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 23 s | — | — | — | — |
| /develop | ok | 28 min 44 s | 4 (1 min 20 s) | 5 (1 min 38 s) | — | client-mobile 2B/3T, client-angular 2B/2T |
| /sonar | skipped | 0.5 s | — | — | — | catalogue e2e seulement |
| /lint-angular | ok | 17 s | — | — | — | — |
| /lint-mobile | ok | 10 s | — | — | — | — |
| /e2e | ok | 12 min 32 s | — | — | — | e2e ×8 (39 min 14 s) |
| /review | ok | 5 min 28 s | 3 (25 s) | 4 (4 min 27 s) | — | api-mail 1B/1T, client-mobile 1B/2T, client-angular 1B/1T |
| /tech-writer | ok | 36 s | — | — | — | — |
| **Total cycle** | | **48 min 13 s** | **7 (1 min 45 s)** | **9 (6 min 05 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : lint ×3 (25 s)
