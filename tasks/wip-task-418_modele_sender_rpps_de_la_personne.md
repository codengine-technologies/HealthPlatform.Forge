# todo-task-418 — Modèles de message : `{{SenderRPPS}}` est le RPPS de la personne qui écrit

**Repos**: client-angular
**Dependencies**: aucune
**Epic**: E020

> **Origine** : audit du périmètre « boîte déléguée » du 2026-10-30, mineur client. Il a été détaché de
> task-412 le 2026-10-30, sur décision humaine, après vérification sur le code (weda2 sur
> `feature/nova-mss-weda-integration`).
>
> **Une seule couche** : le mobile n'expose pas `{{SenderRPPS}}` dans ses modèles, et le serveur ne
> remplace pas les variables de modèle. Seul weda2 est concerné.

## Objectif

Un modèle de message qui cite le RPPS de l'expéditeur insère le RPPS de la personne qui écrit (le
titulaire, ou le délégataire qui écrit pour le compte de la boîte), jamais un fragment d'adresse.

## Constat vérifié (2026-10-30)

`MailComposeComponent` (weda2, `mail-compose.component.ts`) calcule `SenderRPPS` à partir de la partie
locale de l'adresse de la boîte ouverte. Pour la boîte de Virginie, le modèle insère
« virginie.medecinrpps0062267 ». Ce n'est jamais un RPPS, et jamais celui de la personne qui écrit.

Le RPPS de la personne est déjà disponible dans weda2 : `MSS_PRACTITIONER_IDENTITY().rpps`, issu de la
claim `rpps` du jeton (task-304), celui que l'onboarding affiche.

## Règles

1. `{{SenderRPPS}}` = `MSS_PRACTITIONER_IDENTITY().rpps`, le RPPS de la personne authentifiée, qu'elle
   soit titulaire, membre ou délégataire. Ce n'est jamais un dérivé de l'adresse de la boîte.
2. RPPS absent du jeton : la variable est remplacée par une chaîne vide. On n'invente rien.

## Definition of Done

- [ ] Build passes (0 errors) sur `client-angular` (code-only)
- [ ] Tests pass (0 failures)
- [ ] Test unitaire de la substitution des variables de modèle, vu rouge sur le code d'avant :
  - avec une identité `rpps = "899700723440"` et la boîte `virginie.medecinrpps0062267@…`,
    `{{SenderRPPS}}` vaut `899700723440` ;
  - sans RPPS dans l'identité, `{{SenderRPPS}}` vaut une chaîne vide.

## Manual Test Plan

- weda2 via le faux hôte, backend `cd Api/Mail && dotnet run --project src/AppHost` (profil e2e).
- Créer un modèle de message contenant `RPPS : {{SenderRPPS}}`.
- Le délégataire e2e ouvre la boîte du titulaire, rédige un message et applique le modèle.
- Attendu : le RPPS du délégataire, et non un morceau de l'adresse de la boîte.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — exactitude de l'identité de l'émetteur
- **Exigences DSR honorées** : référentiel socle MSSanté #2 (clients), draft délégation ECO.1.2.9 à
  1.2.11 (identité de la personne qui écrit)
- **INS** : non applicable
- **Authentification PS** : PSC. Le RPPS vient du jeton, il n'est jamais saisi.
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé
- **Consentement patient** : non applicable
- **Référentiels métier** : RPPS (identifiant national du professionnel), tel que publié par la claim
  PSC
- **Hébergement HDS** : non — logique cliente
- **AIPD / impact RGPD** : aucun changement de traitement

## Branches

- `client-angular` (code-only) : la forge écrit sur la branche checkoutée dans `Client/Angular/` (`feature/nova-mss-weda-integration` au /start, qui porte aussi le code non commité de task-412 et task-417) — l'humain gère branche, commit, push et PR TFS

## Develop log

- **client-angular** (code-only, `feature/nova-mss-weda-integration`, rien de commité) :
  - `mail-compose.component.ts` : `SenderRPPS` = `MSS_PRACTITIONER_IDENTITY().rpps` (injection
    optionnelle). La partie locale de l'adresse de la boîte n'est plus utilisée. Le jeton est fourni
    par `apps/weda2/src/app/app.config.ts`.
  - `mail-compose.component.spec.ts` : 3 tests (RPPS `899700723440` sur la boîte
    `virginie.medecinrpps0062267@…` ; RPPS vide ; aucune identité).
- **Vu rouge** sur le code d'avant : les 3 tests rendaient `RPPS : virginie.medecinrpps0062267`.
- **Vert** : `mss-lib` 1411/1411 (130 fichiers).
- **Build** : aucune erreur TypeScript. `mss:build:production` et `prescription:build:production` sont
  rouges sur le budget de bundle initial (+1,02 Mo, +264 ko), les mêmes valeurs qu'à task-417 :
  préexistant.
- **Passe qualité** : 3 lignes de production, rien à simplifier.
- **Règle 1b** : non applicable, aucun endpoint touché. Aucun parcours e2e créé ni modifié.

## Lint log

`/lint-angular` en mode A : base `origin/next`, lint limité à `tag:scope:mss`, build et tests sur tout le
périmètre affecté.
- **Base** : 1 erreur, `prettier/prettier` sur l'injection `MSS_PRACTITIONER_IDENTITY` (code de la
  task), plus des warnings préexistants.
- **Itération 1** : `--fix`. Le lint passe à **0 erreur** (13 projets).
- **Tests** : 12 projets affectés verts.
- **Build** : seuls `mss:build:production` et `prescription:build:production` sont rouges, sur le budget
  de bundle initial. Préexistant, inchangé.
- Correction faite par l'auto-fixer : aucune consigne à ajouter (gratuit).

## Lint mobile log

- **client-mobile** : non touché par la task, skip.

## Sonar log

**Sonar : skipped** — api-mail non touché.

## E2E log

| Voie | Jouée ? | Résultat |
|---|---|---|
| angular (`npm run e2e:mss`) | jouée (weda2 sur `feature/nova-mss-weda-integration`, non commité ; api-mail `587fbe4c`) | ✅ 67 verts, 1 flaky préexistant, 0 rouge |
| mobile | non touché, **listing** de la branche staging du run (57 tests) | 📋 listé |

**Catalogue de la porte : celui de la branche staging du run** (`forge/staging-task-412-418-20261030`),
et non celui d'`origin/develop`.
- **Pourquoi** : la copie de travail weda2 porte aussi les parcours non commités de task-412 et
  task-417. Leurs scénarios (E2E-SESSION-004, E2E-AI-002, E2E-MAILBOX-007) ne sont au catalogue que dans
  leurs PRs, pas encore mergées.
- **Le contrôle de parité intégré à la voie** lit le catalogue d'`Api/Mail`, checkouté sur `develop`. Il
  sort donc « parité rouge » : la voie rend le code 1, mais la suite est verte.
- **La porte**, sur le catalogue et le listing mobile de staging (ce qui sera mergé ensemble), rend le
  verdict ci-dessous.
- Démontage vérifié : aucun conteneur e2e. Les ports 7129 et 8081 sont tenus par la pile Docker du poste
  depuis le 2026-10-28, ce ne sont pas des restes de la voie.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**Flaky (vert au second essai, non bloquant)** (1) :

- [angular] « patients — la vue « Mails du patient » reste ouverte et ses pages viennent du serveur » (E2E-PATIENT-004)

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | 📋 listé |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | 📋 listé |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | 📋 listé |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | 📋 listé |
| E2E-PATIENT-003 | 1 | headless | La fiche d'un patient ne montre pas les documents d'un autre patient du même mail | ✅ | 📋 listé |
| E2E-PATIENT-004 | 1 | headless | La vue « Mails du patient » reste ouverte et ses pages viennent du serveur | ⚠️ flaky | — |
| E2E-CONTACT-001 | 2 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | 📋 listé |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | 📋 listé |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | 📋 listé |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | 📋 listé |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | 📋 listé |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | 📋 listé |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | 📋 listé |
| E2E-COMPOSE-004 | 1 | headless | Écrire à l'adresse choisie d'un contact à plusieurs adresses, ou à son adresse par défaut | ✅ | 📋 listé |
| E2E-COMPOSE-005 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | 📋 listé |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | 📋 listé |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | 📋 listé |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | 📋 listé |
| E2E-MAIL-006 | 1 | headless | Glisser sur la Corbeille un message d'un fil supprime ce message, et lui seul | ✅ | — |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | 📋 listé |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | 📋 listé |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | 📋 listé |
| E2E-DRAFT-004 | 1 | headless | Une rédaction sans texte dans le corps ne laisse ni brouillon ni question | ✅ | 📋 listé |
| E2E-BIO-001 | 2 | headless | Acquitter un compte rendu de biologie, à son nom | ✅ | 📋 listé |
| E2E-BIO-002 | 1 | headless | La puce « Bio à acquitter » montre tous les résultats en attente, sur toutes les pages | ✅ | 📋 listé |
| E2E-BIO-003 | 1 | headless | Lire un résultat HPRIM puis l'acquitter | ✅ | 📋 listé |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | 📋 listé |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | 📋 listé |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | 📋 listé |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | 📋 listé |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | 📋 listé |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | 📋 listé |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | 📋 listé |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | 📋 listé |
| E2E-CONTACT-002 | 2 | headless | Créer un contact à deux adresses, le modifier sans les perdre, puis le supprimer | ✅ | 📋 listé |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | 📋 listé |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | 📋 listé |
| E2E-CONTACT-004 | 1 | headless | Consulter un contact depuis le carnet et lui écrire | ✅ | 📋 listé |
| E2E-CONTACT-005 | 1 | headless | Une fiche modifiée ne se perd pas sans confirmation, une adresse mal formée est refusée | ✅ | 📋 listé |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | 📋 listé |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | 📋 listé |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | 📋 listé |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | 📋 listé |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | 📋 listé |
| E2E-WEDA-001 | 2 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | 📋 listé |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | 📋 listé |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | 📋 listé |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | 📋 listé |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | 📋 listé |
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ · divergence (task-395) | 📋 listé |
| E2E-MAILBOX-003 | 2 | headless | Rattacher ses boîtes depuis « Mes boîtes » en un geste — titulaire et membre | ✅ | 📋 listé |
| E2E-MAILBOX-006 | 1 | headless | Après le rattachement, l'identité d'expéditeur et la signature sont déjà là | ✅ | 📋 listé |
| E2E-MAILBOX-004 | 1 | headless | Ajouter une BAL déléguée par saisie — et refus de sa propre adresse | ✅ | 📋 listé |
| E2E-MAILBOX-005 | 1 | headless | Le délégataire refusé par l'opérateur perd l'accès, en ligne puis hors ligne ; le titulaire garde le sien | ✅ | 📋 listé |
| E2E-AUDIT-001 | 1 | headless | Le titulaire lit au journal le message supprimé par son délégataire, au nom du délégataire | ✅ | — |
| E2E-SHARED-001 | 1 | headless | Une boîte partagée, une base — le patient rattaché par le titulaire est vu du délégataire, la signature reste à chacun | ✅ | 📋 listé |
| E2E-SHARED-002 | 1 | headless | Le délégataire écrit pour le compte du titulaire — le destinataire voit qui a écrit, sa réponse revient à la boîte | ✅ | 📋 listé |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |
| E2E-SESSION-004 | 1 | headless | Sur un appareil partagé, la personne suivante n'arrive jamais dans la boîte de la précédente | ✅ | 📋 listé |
| E2E-AI-002 | 1 | headless | Un délégataire interroge l'assistant dans la boîte qu'il a ouverte | ✅ | 📋 listé |
| E2E-MAILBOX-007 | 1 | headless | Après un changement de boîte, l'onglet Patients ne montre plus rien de la précédente | ✅ | 📋 listé |

**Divergences temporaires ouvertes** (1) :

- E2E-MAILBOX-002 [angular] — le code weda2 de task-378 (écran de panne à l'entrée et son test) n'est pas encore livré sur la branche weda2 ; divergence décidée par l'humain le 2026-10-25 — résorbée par task-395 — **à retirer** : le client est revenu à la version du catalogue

**Parité : verte** — aucun écart entre le catalogue et les suites.

## Timings

*(généré par `tools/timing/report.sh --task task-418 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 8.7 s | — | — | — | — |
| /develop | ok | 2 min 26 s | 1 (21 s) | 1 (23 s) | — | client-angular 1B/1T |
| /lint-angular | ok | 3 min 19 s | 1 (21 s) | 1 (1 min 29 s) | — | 1 itération(s), client-angular 1B/1T |
| /lint-mobile | skipped | 0.6 s | — | — | — | client-mobile non touché |
| /e2e | ok | 10 min 53 s | — | — | — | e2e ×3 (19 min 52 s) |
| **Total cycle** | | **16 min 48 s** | **2 (43 s)** | **2 (1 min 53 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : lint ×3 (1 min 00 s)
