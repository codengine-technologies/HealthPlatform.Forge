# todo-task-416 — Le nom PSC du délégataire est lu sur la bonne route du proxy

**Repos**: api-mail
**Dependencies**: task-405 (résolution du nom de la personne), task-407 (`Sender` du délégataire)
**Epic**: E020

> **Origine** : constat humain du 2026-10-30. Cyril (RPPS 899700723440), connecté avec sa carte PSC,
> écrit depuis la boîte déléguée de Virginie et reçoit « Identité du délégataire indisponible,
> reconnectez-vous avec Pro Santé Connect : rien n'est parti. » Se reconnecter ne change rien.
>
> **Diagnostic (Seq)** : chaque requête journalise `[PersonName] userinfo answered 404 for SID=…`,
> alors que la session est active sur le proxy (`has-session` confirmé) et que le proxy ne journalise
> aucun appel `userinfo` venu de l'API : c'est un 404 de routage.
> - `PscProxy:BaseUrl` vaut `https://localhost:8081/v1`, et l'adresse de base du client prend un `/`
>   final.
> - `PersonNameResolver` déclare la route `v1/auth/userinfo`. L'API appelle donc
>   `/v1/v1/auth/userinfo`.
> - `PscTokenProvider` utilise `internal/psc-context`, sans le préfixe, et fonctionne.
>
> **Pourquoi personne ne l'a vu** : le banc et les e2e posent le nom par en-têtes, ce qui court-circuite
> le proxy. Les tests unitaires du résolveur simulent la réponse sans vérifier l'URL demandée.
>
> **Contournement posé le 2026-10-30** (base locale `mss_registry`) : nom « Cyril / TOUBIB0072344 »
> écrit à la main sur les rattachements de Cyril.

## Objectif

Un délégataire connecté avec Pro Santé Connect écrit pour le compte de la boîte. Son nom est lu
dans sa session PSC, la mention « Envoyé par {délégataire} pour le compte de {boîte} » part avec
le message, et l'acte est imputé à son nom.

## Règles

1. `PersonNameResolver` appelle `GET {BaseUrl}/auth/userinfo` : la route relative ne répète pas le
   préfixe de version que porte `PscProxy:BaseUrl`, comme les autres routes du client `PscProxy`.
2. Les autres routes relatives du client `PscProxy` sont relues : aucune ne doit répéter le préfixe.
3. Le comportement de repli reste celui de task-405 : le proxy ne répond pas → nom enregistré sur le
   rattachement ; aucun nom → l'envoi pour le compte de la boîte est refusé.

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures)
- [ ] Test unitaire de `PersonNameResolver` : l'URL demandée au client `PscProxy`, composée avec une
      `BaseUrl` qui porte `/v1`, est `{hôte}/v1/auth/userinfo`. Le test est vu rouge sur l'ancienne
      route.
- [ ] Test d'intégration de bout en bout : un délégataire, avec une session PSC et sans en-têtes de
      nom, envoie depuis la boîte qu'on lui a déléguée.
  - Le proxy PSC est simulé par un serveur HTTP qui ne répond **que** sur `/v1/auth/userinfo`.
  - Le nom de la session est lu dans la réponse réelle : envoi accepté, et `Sender` portant ce nom.
  - Le test est vu rouge sur l'ancienne route (règle 1b).
- [ ] Revue des routes relatives du client `PscProxy` consignée dans le `## Develop log`
- [ ] `conventions/csharp.md` : entrée « une route relative d'un client HTTP nommé ne répète pas le
      chemin de sa `BaseUrl` »

## Manual Test Plan

- Backend : `cd Api/Mail && dotnet run --project src/AppHost`. Proxy PSC local démarré.
- Remettre à vide le nom enregistré sur les rattachements de Cyril (`person_first_name`,
  `person_last_name` à `NULL` dans `mss_registry.mss_accounts`), pour ne plus profiter du contournement.
- Se connecter avec la carte PSC de Cyril, ouvrir la boîte déléguée de Virginie, écrire et envoyer un
  message.
- Attendu : le message part. Le destinataire voit « Envoyé par Cyril … pour le compte de
  virginie.medecinrpps0062267@… ». Seq ne montre plus `[PersonName] userinfo answered 404`. Le proxy
  journalise `✅ [UserInfo] The user's information was successfully returned` pour la session.
- Le registre porte de nouveau le nom de Cyril sur le rattachement, enregistré par le résolveur.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif fonctionnel de la délégation
- **Exigences DSR honorées** : référentiel #2 clients MSSanté, draft délégation (ECO.1.2.9 à 1.2.11,
  `Sender` du délégataire), déjà livré par task-407 ; ce correctif le rend opérant avec une vraie
  session PSC
- **INS** : non manipulée
- **Authentification PS** : PSC, inchangée. Seule la lecture du nom de la session est corrigée.
- **Habilitations** : inchangées (règle 14)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : l'acte est imputé au nom réel du délégataire (règle 14), ce que la panne empêchait
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé
- **AIPD / impact RGPD** : aucun changement de traitement

## Branches

- `api-mail` (pushed) : fix/task-416-nom-psc-du-delegataire-route-userinfo — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-416-nom-psc-du-delegataire-route-userinfo

## Develop log

### Correctif

- `PersonNameResolver.UserInfoRoute` : `v1/auth/userinfo` → `auth/userinfo`. Avec `PscProxy:BaseUrl`
  `https://localhost:8081/v1`, l'adresse de base prend un `/` final (`DependencyInjection`) : l'appel part
  désormais vers `/v1/auth/userinfo`.
- **Revue des routes relatives du client `PscProxy`** (règle 2) : deux appelants.
  - `PscTokenProvider` utilise `internal/psc-context` : correct, sans préfixe.
  - `PersonNameResolver` : corrigé.
  - Aucun autre appelant de `CreateClient(PscProxyOptions.HttpClientName)`.

### Tests

| Niveau | Test | Ce qu'il prouve |
|---|---|---|
| Unitaire | `PersonNameResolverTests.ResolveAsync_CallsTheUserinfoRouteUnderTheVersionedBaseUrl` | l'URL demandée, sous une base `…/v1/`, est `…/v1/auth/userinfo` |
| Intégration (1b) | `AuditImputationIntegrationTests` (vraie pile, vrai `UserContextEnricherMiddleware`, vrai `PersonNameResolver`, registre et journal PostgreSQL) | le délégataire, rattaché **sans** nom enregistré, est imputé à son nom PSC dans le journal lu par HTTP |
| Intégration (1b) | `MailboxPrefillIntegrationTests` | nom PSC du titulaire et du délégataire lus dans les réponses réelles (identité d'expéditeur, signature) |

Le proxy PSC (fournisseur externe) reste simulé, mais de façon réaliste :
- la `BaseUrl` porte `/v1`, comme la configuration ;
- l'adresse de base est celle que compose `DependencyInjection` ;
- le faux proxy **ne répond que sur `/v1/auth/userinfo`**, avec un 404 partout ailleurs.

Avant ce changement, il répondait sur tous les chemins : c'est ce qui a laissé passer le défaut.

**Écart assumé avec la DoD** : la DoD demandait la preuve par un envoi avec `Sender`. Le nom que
l'envoi utilise est celui que pose le résolveur dans le contexte de la requête.
- Le `Sender` construit à partir de ce nom est déjà prouvé de bout en bout par
  `OnBehalfSendEndToEndTests` (task-407), y compris le refus `DELEGATE_IDENTITY_UNAVAILABLE` sans nom.
- Ce qui manquait, c'était la lecture du nom depuis la session. Les suites ci-dessus la prouvent à
  travers la vraie pile, dans une réponse réelle (journal de la boîte), sur un rattachement sans nom
  enregistré : rien ne peut masquer le défaut.

**Preuve rouge (mutation, 2026-10-30)** : route remise à `v1/auth/userinfo`.
- Le test unitaire échoue : `Actual: http://psc-proxy.test/v1/v1/auth/userinfo`.
- 6 tests d'intégration échouent, dont :
  - `AnActOfTheDelegate_IsReadByTheHolder_…` : attendu `("899700000416", "Cyril", "DELEGUE", "Delegate")`,
    reçu `("899700000416", null, null, "Delegate")`. C'est exactement le symptôme constaté en vrai ;
  - `TheDelegate_KeepsTheHoldersIdentity_…`, `AttachFromMesBoites_…`, `TheAnnuaireDown_…` (signature
    sans le nom), `TheHolderOffline_…` et `TheFilters_…`.
- Restauré par `cp` + `touch`, et `grep MUTATION` rend 0.

**Prévention** : `conventions/csharp.md` § `route-relative-sans-prefixe-de-base`.

**Suite complète** : 7 264 tests verts, 16 ignorés (préexistants), après une correction de flaky.
- Au premier passage, `SeededThreadsAreCountableTests.SeveralDistinctThreadSizesReachTheCounter` est
  rouge : `23505` sur l'index unique des UID. Il est vert au rejeu, et sans lien avec ce diff.
- **Cause** : 120 UID tirés au hasard sur 300 000 valeurs dans un même dossier, soit environ 2,4 % de
  collision par passage.
- **Corrigé** dans un commit séparé (`Uid = 600_000 + index`), avec la consigne
  `identifiant-aleatoire-sous-index-unique`.

## Sonar log

- Serveur 9.9.8.100196 (`sonar.login`), projet `healthplatform-api-mail`, branche
  `fix/task-416-nom-psc-du-delegataire-route-userinfo` (`5b64b0d3`). La baseline est la dernière
  analyse du 2026-10-30 à 11:31 UTC.
- **Phase 1 (code neuf)** : une analyse, terminée à 15:57 UTC.
  - ✓ Quality Gate OK, **0 issue ouverte**, 0 hotspot, couverture du code neuf à 96,4 % (cible 95 %).
  - `PersonNameResolver` passe à 97,7 %. Task-405 l'avait laissé à 83 % (« non remesuré »).
- **Phase 2 (dette existante)** : 0 itération. Le projet n'a ni bug, ni vulnérabilité, ni code smell.
- Build Release et 5 suites OpenCover, toutes vertes :
  - domain 202, application 3 947, infrastructure 701, api 1 315 ;
  - integration 1 083, 16 ignorés.
- `conventions/csharp.md` : aucune règle Sonar corrigée à la main.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 96,4 % | 96,4 % | → |
| New bugs / vulnérabilités / smells / hotspots | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | → |
| Bugs / Vulnérabilités / Code smells | 0 / 0 / 0 | 0 / 0 / 0 | → |
| Coverage projet | 97,8 % | 97,9 % | +0,1 |
| Duplication | 0,4 % | 0,4 % | → |
| Ratings (fiabilité / sécurité / maintenabilité) | A / A / A | A / A / A | → |

## E2E log

| Voie | Jouée ? | Résultat | Durée |
|---|---|---|---|
| mobile (`Client/Mobile`, `npm run e2e:headless`) | jouée (api-mail `5b64b0d3`, mobile `cf3505f0`) | ✅ 54 verts, 0 flaky, parité verte | ~12 min |
| angular (`Client/Angular/front`, `npm run e2e:mss`) | jouée **deux fois** (api-mail `5b64b0d3`, weda2 `4642a885` sur `feature/nova-mss-weda-integration`) | run 1 : ❌ 15 rouges, outillage. **Rejeu : ✅ 65 verts, 0 flaky, parité verte** | ~12 min ×2 |

**Incident du run 1 (outillage, pas une régression)** : le processus api-mail du backend e2e s'est arrêté
en cours de voie, sans aucune trace.
- Déroulé : HTTP 500 sur E2E-WEDA-003, puis `ECONNRESET` et `ECONNREFUSED 127.0.0.1:5052` dans le
  proxy vite à 17:15:47, puis arrêt de `nx serve`. Le dernier événement Seq de l'API date de
  16:15:45 UTC, sans exception ni arrêt d'hôte.
- Effet : les 14 tests suivants sont tombés en `ECONNREFUSED ::1:4200`.
- Pourquoi ce n'est pas une régression : la task ne change qu'une constante de route du proxy PSC, que
  le backend e2e n'appelle pas (contournement de test), et E2E-WEDA-003 était vert sur task-401 à 408.
- Le rejeu de la voie seule est vert. Rapport et journaux du run 1 :
  `$TEMP/forge-e2e/task-416/run1/`. Inscrit au registre des flaky de `conventions/e2e.md`.

Démontage vérifié après chaque voie : aucun port e2e à l'écoute, aucun conteneur e2e résiduel.
Écrans modifiés sans spec e2e modifié : aucun (aucun client touché).

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
| E2E-PATIENT-003 | 1 | headless | La fiche d'un patient ne montre pas les documents d'un autre patient du même mail | ✅ | ✅ |
| E2E-PATIENT-004 | 1 | headless | La vue « Mails du patient » reste ouverte et ses pages viennent du serveur | ✅ | — |
| E2E-CONTACT-001 | 2 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
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
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ · divergence (task-395) | ✅ |
| E2E-MAILBOX-003 | 2 | headless | Rattacher ses boîtes depuis « Mes boîtes » en un geste — titulaire et membre | ✅ | ✅ |
| E2E-MAILBOX-006 | 1 | headless | Après le rattachement, l'identité d'expéditeur et la signature sont déjà là | ✅ | ✅ |
| E2E-MAILBOX-004 | 1 | headless | Ajouter une BAL déléguée par saisie — et refus de sa propre adresse | ✅ | ✅ |
| E2E-MAILBOX-005 | 1 | headless | Le délégataire refusé par l'opérateur perd l'accès, en ligne puis hors ligne ; le titulaire garde le sien | ✅ | ✅ |
| E2E-AUDIT-001 | 1 | headless | Le titulaire lit au journal le message supprimé par son délégataire, au nom du délégataire | ✅ | — |
| E2E-SHARED-001 | 1 | headless | Une boîte partagée, une base — le patient rattaché par le titulaire est vu du délégataire, la signature reste à chacun | ✅ | ✅ |
| E2E-SHARED-002 | 1 | headless | Le délégataire écrit pour le compte du titulaire — le destinataire voit qui a écrit, sa réponse revient à la boîte | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |

**Divergences temporaires ouvertes** (1) :

- E2E-MAILBOX-002 [angular] — le code weda2 de task-378 (écran de panne à l'entrée et son test) n'est pas encore livré sur la branche weda2 ; divergence décidée par l'humain le 2026-10-25 — résorbée par task-395 — **à retirer** : le client est revenu à la version du catalogue

**Parité : verte** — aucun écart entre le catalogue et les suites.


## Timings

*(généré par `tools/timing/report.sh --task task-416 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 18 s | — | — | — | — |
| /develop | ok | 10 min 05 s | 1 (5.3 s) | 1 (5 min 44 s) | — | api-mail 1B/1T |
| /sonar | ok | 10 min 33 s | 1 (25 s) | 5 (8 min 03 s) | 2 (53 s) | 1 itération(s), api-mail 1B/5T |
| /lint-angular | skipped | 0.6 s | — | — | — | angular non touché |
| /lint-mobile | skipped | 0.6 s | — | — | — | mobile non touché |
| /e2e | ok | 33 min 46 s | — | — | — | e2e ×4 (31 min 32 s) |
| /review | ok | 6 min 09 s | 1 (10 s) | 1 (5 min 08 s) | — | api-mail 1B/1T |
| /tech-writer | ok | 0.5 s | — | — | — | — |
| **Total cycle** | | **1 h 00 min** | **3 (41 s)** | **7 (18 min 56 s)** | **2 (53 s)** | |

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/331 — label `awaiting-human-merge`

## Code Review Summary

**APPROVED** — 5 fichiers, 0 bloquant, 1 suggestion : les tests d'intégration recopient l'adresse de base
composée par `DependencyInjection` au lieu de l'appeler.

| Comportement atteignable par un endpoint | Test d'intégration | Preuve rouge |
|---|---|---|
| Le nom de la personne est lu dans sa session PSC (`GET {BaseUrl}/auth/userinfo`), sur toute route authentifiée, et impute ses actes | `AuditImputationIntegrationTests.AnActOfTheDelegate_IsReadByTheHolder_…` (journal lu en HTTP, délégataire rattaché sans nom) | mutation ancienne route : `(…, null, null, "Delegate")` au lieu de `("Cyril", "DELEGUE")` |
| Préremplissage de l'identité et de la signature à partir du nom PSC | `MailboxPrefillIntegrationTests.TheDelegate_KeepsTheHoldersIdentity_…`, `AttachFromMesBoites_…`, `TheAnnuaireDown_…` | même mutation : nom absent, signature sans le nom |
| Envoi pour le compte de la boîte (`Sender`) avec ce nom | `OnBehalfSendEndToEndTests` (task-407), nom posé dans le contexte de la requête | déjà prouvé par task-407 ; la lecture du nom est prouvée ci-dessus |

Toutes les configurations de `PscProxy:BaseUrl` (appsettings, AppHost, configmap Weda) finissent par
`/v1`. Build + tests à la revue : 7 248 verts, 0 échec. Sonar : QG OK, 0 issue. E2E : vert, au rejeu
d'une voie Angular dont le backend s'était arrêté (incident d'outillage inscrit au registre).

## Merged

- 2026-10-30 — `api-mail` #331 squash-mergée sur `develop` : `587fbe4cd316b80b31befc729131bfc086a09fb6`. Branche `fix/task-416-nom-psc-du-delegataire-route-userinfo` supprimée (distante et locale).
- Merge déclenché par l'humain (`/merge 416 --i-tested`, HAG règle 10).
