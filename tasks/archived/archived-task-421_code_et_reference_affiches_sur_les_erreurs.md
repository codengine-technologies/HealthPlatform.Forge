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

## Sonar log

- **Sonar : skipped** — la branche api-mail ne modifie que `e2e/scenarios.yml` (catalogue E2E-ERROR-001), qu'aucune
  règle Sonar n'analyse : aucun fichier C#, nouveau code vide par construction. La dette introduite par la task est
  donc nulle côté api-mail.
- Écart au playbook, signalé : `agents/sonar.md` ne prévoit le skip que pour « aucun commit sur api-mail ». Proposition
  pour l'humain (plan de contrôle, non appliquée) : fonder le skip sur les fichiers analysables (`*.cs`, `*.csproj`),
  pas sur les commits.

## Lint log

- Mode A, `nx affected -t lint --base=origin/next --projects=tag:scope:mss` : **0 erreur** sur 13 projets dès la ligne de
  base ; avertissements préexistants seulement (`max-lines`, `complexity` sur des fichiers déjà au-delà des seuils).
- Itérations de correction : 0. Build et tests non rejoués : rien n'a changé depuis la validation de /develop (mss-lib 136
  fichiers verts, build weda2 OK). Fichiers weda2 hors portée MSS (intercepteur) lintés à la main en /develop : 0 erreur.
- Code-only : aucune opération git sur `client-angular`.

## Lint mobile log

- Ligne de base `npm run lint` : **All files pass linting** (0 erreur, 0 avertissement). Itérations : 0, aucun commit.
- Build et tests non rejoués : rien n'a changé depuis la validation de /develop (build OK, 1 417 verts).

## E2E log

> ⚠️ **Quarantaine de plus de 14 jours** : E2E-COMPOSE-002 (angular) depuis le 2026-10-09 ; sa task de correction,
> task-350, est archivée. Le test passe à ce run.

| Voie | Déclencheur | Résultat | Tests |
|---|---|---|---|
| mobile | api-mail, client-mobile touchés | ✅ verte | 58 verts, 0 flaky, 0 rouge |
| angular | api-mail, client-angular touchés | ✅ verte | 70 verts, 1 flaky (E2E-COMPOSE-001), 0 rouge, 1 quarantaine passée |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ `feat/task-421-code-et-reference-affiches-sur-les` (E2E-ERROR-001 v1).
- Flaky : [angular] E2E-COMPOSE-001 — à inscrire au registre de `conventions/e2e.md`.
- Divergences ouvertes : aucune. Parcours touchés sans spec e2e modifié : aucun (rédaction couverte par E2E-ERROR-001).
- **Preuve par mutation d'E2E-ERROR-001** (banc mobile `--serve-only`, mutation plantée avant le montage) : ME1, ligne de
  référence retirée du gabarit de la rédaction → rouge sur « le code et la référence courte sont affichés sous le
  message » (élément absent), après le message d'échec et la panne servie ; restauré (marqueur 0) → témoin vert. Côté
  Angular, le même composant est prouvé par M1 (tests de composant et de rédaction) ; la mutation e2e Angular n'a pas été
  jouée.
- Démontage : complet (voies et banc de mutation).
- Porte : **0**.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**Flaky (vert au second essai, non bloquant)** (1) :

- [angular] « rédaction — envoyer, recevoir, lire, supprimer » (E2E-COMPOSE-001)

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-PATIENT-003 | 1 | headless | La fiche d'un patient ne montre pas les documents d'un autre patient du même mail | ✅ | ✅ |
| E2E-PATIENT-004 | 1 | headless | La vue « Mails du patient » reste ouverte et ses pages viennent du serveur | ✅ | — |
| E2E-CONTACT-001 | 2 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ⚠️ flaky | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Écrire à l'adresse choisie d'un contact à plusieurs adresses, ou à son adresse par défaut | ✅ | ✅ |
| E2E-COMPOSE-005 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-MAIL-006 | 1 | headless | Glisser sur la Corbeille un message d'un fil supprime ce message, et lui seul | ✅ | — |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-DRAFT-004 | 1 | headless | Une rédaction sans texte dans le corps ne laisse ni brouillon ni question | ✅ | ✅ |
| E2E-BIO-001 | 2 | headless | Acquitter un compte rendu de biologie, à son nom | ✅ | ✅ |
| E2E-BIO-002 | 1 | headless | La puce « Bio à acquitter » montre tous les résultats en attente, sur toutes les pages | ✅ | ✅ |
| E2E-BIO-003 | 1 | headless | Lire un résultat HPRIM puis l'acquitter | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SETTINGS-004 | 1 | headless | Paramètres indisponibles : rien n'est écrasé | ✅ | — |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 2 | headless | Créer un contact à deux adresses, le modifier sans les perdre, puis le supprimer | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-CONTACT-004 | 1 | headless | Consulter un contact depuis le carnet et lui écrire | ✅ | ✅ |
| E2E-CONTACT-005 | 1 | headless | Une fiche modifiée ne se perd pas sans confirmation, une adresse mal formée est refusée | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 2 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ | ✅ |
| E2E-MAILBOX-003 | 2 | headless | Rattacher ses boîtes depuis « Mes boîtes » en un geste — titulaire et membre | ✅ | ✅ |
| E2E-MAILBOX-006 | 1 | headless | Après le rattachement, l'identité d'expéditeur et la signature sont déjà là | ✅ | ✅ |
| E2E-MAILBOX-004 | 1 | headless | Ajouter une BAL déléguée par saisie — et refus de sa propre adresse | ✅ | ✅ |
| E2E-MAILBOX-005 | 1 | headless | Le délégataire refusé par l'opérateur perd l'accès, en ligne puis hors ligne ; le titulaire garde le sien | ✅ | ✅ |
| E2E-AUDIT-001 | 1 | headless | Le titulaire lit au journal le message supprimé par son délégataire, au nom du délégataire | ✅ | — |
| E2E-AUDIT-002 | 1 | headless | Le journal d'audit montre chaque action sur un mail | ✅ | — |
| E2E-SHARED-001 | 1 | headless | Une boîte partagée, une base — le patient rattaché par le titulaire est vu du délégataire, la signature reste à chacun | ✅ | ✅ |
| E2E-SHARED-002 | 1 | headless | Le délégataire écrit pour le compte du titulaire — le destinataire voit qui a écrit, sa réponse revient à la boîte | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |
| E2E-SESSION-004 | 1 | headless | Sur un appareil partagé, la personne suivante n'arrive jamais dans la boîte de la précédente | ✅ | ✅ |
| E2E-AI-002 | 1 | headless | Un délégataire interroge l'assistant dans la boîte qu'il a ouverte | ✅ | ✅ |
| E2E-MAILBOX-007 | 1 | headless | Après un changement de boîte, l'onglet Patients ne montre plus rien de la précédente | ✅ | ✅ |
| E2E-ERROR-001 | 1 | headless | Une erreur affiche un code et une référence à transmettre au support | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## Timings

*(généré par `tools/timing/report.sh --task task-421 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 24 s | — | — | — | — |
| /develop | ok | 28 min 18 s | 10 (1 min 45 s) | 9 (2 min 37 s) | — | client-mobile 3B/3T, client-blazor 5B/3T, client-angular 2B/3T |
| /sonar | skipped | 0.6 s | — | — | — | api-mail : catalogue YAML seul, aucun fichier analysé |
| /lint-angular | ok | 25 s | — | — | — | — |
| /lint-mobile | ok | 14 s | — | — | — | — |
| /e2e | ok | 22 min 56 s | — | — | — | e2e ×5 (39 min 58 s) |
| /review | ok | 6 min 50 s | 3 (35 s) | 6 (2 min 33 s) | — | client-blazor 1B/1T, client-mobile 1B/3T, client-angular 1B/2T |
| /tech-writer | ok | 0.6 s | — | — | — | — |
| **Total cycle** | | **59 min 12 s** | **13 (2 min 21 s)** | **15 (5 min 11 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : lint ×2 (17 s)

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/339 (catalogue E2E-ERROR-001) — `awaiting-human-merge`
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/121 — `awaiting-human-merge`
- `client-blazor` : https://github.com/codengine-technologies/HealthPlatform.Client/pull/97 — `awaiting-human-merge`
- `client-angular` : code-only — humain gère commit/push TFS et ouverture PR, sur `feature/nova-mss-weda-integration`.
  **`functional.e2e.ts` (E2E-ERROR-001, requis angular) à commiter avant le merge de #339.** Fichiers :
  `apps/weda2/src/app/core/interceptors/error.interceptor.ts`, `error.interceptor.spec.ts`, `e2e/mss-e2e/specs/functional.e2e.ts`,
  `libs/mss/src/core/index.ts`, `libs/mss/src/core/utils/error-reference.util.ts`, `error-reference.util.spec.ts`,
  `libs/mss/src/ui/error-reference/` (4 fichiers), `libs/mss/src/ui/index.ts`, `mss-contacts.component.{ts,html}`,
  `mail-compose.component.{ts,html,scss}`, `mail-compose-safety.component.spec.ts`, `mail-detail.component.{ts,html}`,
  `mss-pending-sends.component.{ts,html,spec.ts}`.
- Dépendance : task-420, api-mail #338. Le correctif de l'intercepteur weda2 part avant ou avec #338.
- Staging `forge/staging-task-420-421-20261101` : api-mail `ca769ec7`, mobile `1ab123d`, Blazor `0fb08c5`.

## Code Review Summary

- Validation : Blazor 498 verts (projet de tests ; `Mss.Console` NU1100 préexistant), 0 avertissement ; weda2 mss-lib 136
  fichiers et weda2 107 fichiers verts, build weda2 OK ; mobile build OK, suite verte 4 passages sur 7. Les rouges des 3
  autres changent d'ensemble (suggestions de task-388, sélection de l'éditeur), hors du code de la task : instabilité
  `page-ionic-non-demontee`, 4ᵉ occurrence consignée. api-mail : catalogue seul, relu par la porte e2e.
- Verdict : **APPROVED** — 3 suggestions, 0 bloquant.
- DoD : toutes les lignes vérifiées. Tests de ligne, d'absence sans `traceId` et de copie dans les trois clients ;
  E2E-ERROR-001 au catalogue (v1) et dans les deux suites, vert, prouvé par mutation (mobile) ; `data-testid` présents ;
  ni donnée de santé ni donnée personnelle (un code du catalogue et un identifiant de trace).
- Règle 1b : sans objet côté serveur (aucun comportement d'api-mail modifié) ; parcours client prouvé par E2E-ERROR-001.
- Double verrou e2e : `## E2E log` vert (mobile 58, angular 70 + 1 flaky).
- Suggestions :
  1. toasts mobiles sans bouton « Copier » ;
  2. middleware de boîte d'api-mail : `traceId` = `TraceIdentifier`, non W3C (petite task api-mail) ;
  3. `TECHNICAL_ERROR_CODES` tenue à la main, piste : liste blanche des codes expliqués par l'écran.

## Merged

- 2026-11-02 — `api-mail` #339 squash `892b571a`, `client-blazor` #97 squash `702ceecb`, `client-mobile` #121 squash
  `19b5bf38` (testé par l'humain, `/merge --i-tested`).
- Branches `feat/task-421-code-et-reference-affiches-sur-les` supprimées (distantes et locales).
- `client-angular` : code-only, commit/push TFS et PR à la main de l'humain.
