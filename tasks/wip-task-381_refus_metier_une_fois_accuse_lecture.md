# todo-task-381.md — Un refus métier d'api-mail s'affiche une seule fois, avec son vrai motif

**Repos**: client-angular
**Dependencies**: — (aucune). task-370 (intercepteurs d'authentification et d'erreur) est archivée.
**Epic**: E009
**Single frontend**: true
**Priorité**: **3** — messages contradictoires : un « Accès refusé » ou « Service temporairement indisponible » générique s'ajoute au motif réel qu'affiche l'écran MSS.

> **Origine.** Audit de détection de bugs du client Angular du 2026-10-13
> (`Docs/audits/client-angular-audit-bugs-20261013.md`, **ANG-68** ; ANG-72 corrigé depuis, voir plus bas).

## Ce qui est établi

> **Revérifié le 2026-11-01** sur weda2 `feature/nova-mss-weda-integration` (`10e55c09`, après le rebase sur
> `next` Angular 22). Les numéros de ligne ci-dessous sont ceux de cette révision.

- **ANG-68 — toujours présent.** `apps/weda2/src/app/core/interceptors/error.interceptor.ts:86-132`
  (`handleTechnicalError`) notifie **tout** 5xx (« Service temporairement indisponible. Veuillez patienter. ») et
  **tout** 403 (« Accès refusé. Vous n'avez pas les permissions nécessaires. »), sans regarder qui répond ni ce que
  dit la réponse. Or api-mail rend ses refus métier en problem+json avec un `code` (`GlobalExceptionHandler.cs:79`),
  que le module MSS lit et explique lui-même. Le médecin reçoit donc deux messages, dont un générique qui peut
  contredire le premier. Cas concrets :
  - 403 `MAILBOX_PSC_MISMATCH`, `MAILBOX_ACCESS_REFUSED`, `MAILBOX_NOT_ATTACHED`, `MAILBOX_PSC_SESSION_REQUIRED` ;
  - 503 `MAIL_SERVER_UNAVAILABLE`, et 503 `MAIL_DELIVERY_UNCERTAIN` (task-376 : la rédaction dit « ce message est
    peut-être parti », le toast dit « service indisponible ») ;
  - 503 du proxy PSC, refus d'auteur de task-367.
- **Le mécanisme d'exclusion existe déjà** : le jeton `SILENT_HTTP_ERRORS`
  (`apps/weda2/src/lib/auth/models/silent-http-errors.token.ts`, task-365) coupe la notification d'une requête
  marquée. Aucune requête MSS ne le porte aujourd'hui.
- **Les requêtes vers api-mail sont reconnaissables** : `mss-headers.interceptor.ts:34-36` les identifie par
  `request.url.startsWith(MSS_API_URL)`.
- **Contournement existant** : `libs/mss/src/features/mailbox-management/mss-mailbox-management.component.ts:436-441`
  évite `reload()` au détachement de la boîte par défaut, en partie pour ne pas déclencher deux toasts « Accès
  refusé ». Il a une **seconde raison**, indépendante : le résultat de ces deux appels serait jeté par la
  déconnexion qui suit. Il reste donc en place ; seul son commentaire est à mettre à jour.
- **ANG-72 — corrigé par task-417 (archivée le 2026-10-30).** L'accusé de lecture repose désormais sur
  `FolderType.Sent` (`isSentFolder` dans `libs/mss/src/core/utils/read-receipt.util.ts`), avec un test sur un dossier
  « Consent ». Hors périmètre de cette task.

## Objective

Qu'un refus métier d'api-mail soit annoncé **une seule fois**, par l'écran qui sait l'expliquer, sans retirer la
notification générique des erreurs que personne d'autre n'explique.

### Périmètre

1. **`errorInterceptor`** : pas de notification générique pour une réponse d'**api-mail** (URL sous `MSS_API_URL`)
   dont le corps est un problem+json portant un `code`. Le module MSS s'en charge.
2. **Inchangé** : la notification générique reste pour un 403 / 5xx sans `code` (passerelle, panne réseau, autre
   service que api-mail) et pour toute réponse d'un autre service, même porteuse d'un `code`.
3. **Commentaire** du contournement de `mss-mailbox-management` mis à jour : il ne cite plus le toast comme raison.

## Definition of Done

- [ ] Build et tests weda2 verts
- [ ] Tests unitaires de `errorInterceptor`, rouges d'abord :
  - [ ] 403 `MAILBOX_PSC_MISMATCH` d'api-mail : aucune notification générique
  - [ ] 503 `MAIL_DELIVERY_UNCERTAIN` d'api-mail : aucune notification générique
  - [ ] 503 d'api-mail **sans** `code` (corps vide ou HTML de passerelle) : la notification générique reste
  - [ ] 403 **avec** `code` d'un autre service que api-mail : la notification générique reste
  - [ ] requête marquée `SILENT_HTTP_ERRORS` : toujours aucune notification (non-régression task-365)
- [ ] Le motif MSS reste affiché : test du composant qui lit `MAILBOX_PSC_MISMATCH` inchangé et vert
- [ ] Aucune donnée de santé ajoutée aux journaux

## Manual Test Plan

1. Lancer api-mail (AppHost) et weda2 (`npm start` dans `Client/Angular/front`).
2. Provoquer un 403 `MAILBOX_PSC_MISMATCH` (carte d'un autre praticien sur la boîte) → un seul message, celui de
   l'écran MSS ; aucun toast « Accès refusé ».
3. Arrêter le serveur de messagerie (ou couper IMAP via Toxiproxy) et ouvrir la boîte → le message MSS de panne
   seul ; aucun toast « Service temporairement indisponible » en plus.
4. Arrêter api-mail entièrement (aucun problem+json) → le toast générique apparaît, comme aujourd'hui.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : inchangée ; le motif d'un refus PSC est affiché sans contradiction
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non applicable
- **AIPD / impact RGPD** : inchangé

## Branches
- `client-angular` (code-only) : la forge écrit sur la branche checked out dans `Client/Angular/` — `feature/nova-mss-weda-integration` @ `32cc9b79` au /start, arbre portant déjà le travail non commité de task-380 — humain gère branche, commit, push, PR TFS

## Develop log

- Repos touched : `client-angular` (code-only). DTOs / interop : aucun changement.
- Commits : aucun (code-only) — fichiers modifiés, non commités sur `feature/nova-mss-weda-integration`
  (l'arbre porte aussi le travail non commité de task-380) :
  - `apps/weda2/src/app/core/interceptors/error.interceptor.ts`
  - `apps/weda2/src/app/core/interceptors/error.interceptor.spec.ts`
  - `libs/mss/src/features/mailbox-management/mss-mailbox-management.component.ts` (commentaire seul)
- Correctif (ANG-68) : `errorInterceptor` ne notifie plus un refus **d'api-mail** (URL sous `MSS_API_URL`) dont le corps
  porte un `code` (`isMssBusinessRefusal`). Inchangé : 403 / 5xx sans `code`, réponses d'autres services (même avec
  `code`), requêtes `SILENT_HTTP_ERRORS`. Le commentaire du contournement de `mss-mailbox-management` ne cite plus le
  toast ; sa raison restante (résultat jeté par la déconnexion) est conservée.
- Tests (Vitest, `error.interceptor.spec.ts`) : 7 ajoutés — 403 `MAILBOX_PSC_MISMATCH` et 503 `MAIL_DELIVERY_UNCERTAIN`
  d'api-mail sans notification (**vus rouges** avant correctif), 503 d'api-mail sans `code` ×3 (corps vide, HTML de
  passerelle, problem+json sans code), 403 avec `code` d'un autre service, `SILENT_HTTP_ERRORS`. 18/18 verts.
- Preuves par mutation (restauration par `cp`) :
  - M1 contrôle d'URL retiré → « 403 avec code d'un autre service » rouge ;
  - M2 contrôle du `code` retiré → les 3 cas « 503 sans code » rouges ;
  - M3 exclusion retirée → les 2 refus métier rouges.
- DoD « motif MSS toujours affiché » : `mss-mailbox-management.component.spec.ts` et `mss-pending-sends.component.spec.ts`
  (lecture de `MAILBOX_PSC_MISMATCH`) non modifiés et verts.
- Local build / test : `nx build weda2` vert ; `nx run-many -t test -p weda2 mss-lib` : weda2 2 662, mss-lib 1 464,
  0 échec ; ESLint des fichiers touchés : 0 problème.
- Passe qualité (/simplify) : **aucune simplification appliquée** — diff de production d'une trentaine de lignes ;
  `isProblemDetails` (mss-lib) aurait pu servir mais n'est pas exporté par `@weda/mss` : l'exporter sort du périmètre.
- E2E : la DoD ne demande aucun scénario ; `api-mail` non touché → /e2e jouera la voie Angular (client-angular touché).
- Next step : /lint-angular task-381

## Lint log

- Mode A, base `origin/next`, lint `tag:scope:mss` : **0 erreur** (avertissements antérieurs uniquement) ; le fichier
  de weda2 touché (`error.interceptor.ts`, hors scope MSS) a été linté à part en /develop : 0 problème. Aucune itération.
- `nx affected -t test` : 12 projets verts (weda2 2 662, mss-lib 1 464, … 0 échec).
- Fichiers modifiés par /lint-angular : aucun.

## Lint mobile log

- Skipped : `client-mobile` absent des `**Repos**`.

## E2E log

> ⚠️ **Quarantaine de plus de 14 jours** : E2E-COMPOSE-002 (angular) depuis le 2026-10-09 ; sa task de correction,
> task-350, est archivée. Le test passe à ce run. À l'humain de lever la quarantaine ou d'ouvrir la task qui la résorbe.

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| angular | client-angular touché | ✅ suite verte (70 verts, 0 flaky, 0 rouge, 1 quarantaine passée) — parité de la voie rouge, voir ci-dessous | 70 verts | ~9 min |
| mobile | non touchée — listing | 📋 listée (`Client/Mobile` sur `develop`) | — | — |

- **Pourquoi la voie dit « parité ROUGE » et la porte « vert »** : l'arbre weda2 (code-only, non commité) porte aussi
  les parcours de **task-380** (E2E-AUDIT-002, E2E-SETTINGS-004), dont le catalogue n'existe que sur sa PR api-mail #337
  et sur la branche staging du run. Le contrôle intégré de la voie lit le catalogue d'`Api/Mail` sur `develop` :
  `UnknownIdentifier` pour ces deux tests. La porte est jugée sur le catalogue de
  `origin/forge/staging-task-380-381-20261101` (task-380 incluse) : **parité verte**, les deux parcours verts.
  Cas consigné en mémoire (« catalogue staging pour tasks empilées », task-418).
- Catalogue de la porte : `forge/staging-task-380-381-20261101:e2e/scenarios.yml`
- Quarantaines : [angular] E2E-COMPOSE-002 (task-350) — passée
- Divergences ouvertes : aucune
- Parcours touchés sans spec e2e modifié : aucun (aucun écran modifié ; intercepteur et commentaire seulement)
- Démontage : complet pour ce run. Deux conteneurs antérieurs (2026-10-14) subsistent, non créés par ce cycle.
- Porte : **0**.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

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
| E2E-PATIENT-004 | 1 | headless | La vue « Mails du patient » reste ouverte et ses pages viennent du serveur | ✅ | — |
| E2E-CONTACT-001 | 2 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 📋 listé |
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
| E2E-SETTINGS-004 | 1 | headless | Paramètres indisponibles : rien n'est écrasé | ✅ | — |
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
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 📋 listé |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 📋 listé |
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
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ | 📋 listé |
| E2E-MAILBOX-003 | 2 | headless | Rattacher ses boîtes depuis « Mes boîtes » en un geste — titulaire et membre | ✅ | 📋 listé |
| E2E-MAILBOX-006 | 1 | headless | Après le rattachement, l'identité d'expéditeur et la signature sont déjà là | ✅ | 📋 listé |
| E2E-MAILBOX-004 | 1 | headless | Ajouter une BAL déléguée par saisie — et refus de sa propre adresse | ✅ | 📋 listé |
| E2E-MAILBOX-005 | 1 | headless | Le délégataire refusé par l'opérateur perd l'accès, en ligne puis hors ligne ; le titulaire garde le sien | ✅ | 📋 listé |
| E2E-AUDIT-001 | 1 | headless | Le titulaire lit au journal le message supprimé par son délégataire, au nom du délégataire | ✅ | — |
| E2E-AUDIT-002 | 1 | headless | Le journal d'audit montre chaque action sur un mail | ✅ | — |
| E2E-SHARED-001 | 1 | headless | Une boîte partagée, une base — le patient rattaché par le titulaire est vu du délégataire, la signature reste à chacun | ✅ | 📋 listé |
| E2E-SHARED-002 | 1 | headless | Le délégataire écrit pour le compte du titulaire — le destinataire voit qui a écrit, sa réponse revient à la boîte | ✅ | 📋 listé |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |
| E2E-SESSION-004 | 1 | headless | Sur un appareil partagé, la personne suivante n'arrive jamais dans la boîte de la précédente | ✅ | 📋 listé |
| E2E-AI-002 | 1 | headless | Un délégataire interroge l'assistant dans la boîte qu'il a ouverte | ✅ | 📋 listé |
| E2E-MAILBOX-007 | 1 | headless | Après un changement de boîte, l'onglet Patients ne montre plus rien de la précédente | ✅ | 📋 listé |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## Timings

*(généré par `tools/timing/report.sh --task task-381 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 1.2 s | — | — | — | — |
| /develop | ok | 4 min 38 s | 1 (16 s) | 1 (30 s) | — | client-angular 1B/1T |
| /lint-angular | ok | 1 min 50 s | — | 1 (1 min 29 s) | — | client-angular 0B/1T |
| /lint-mobile | skipped | 0.6 s | — | — | — | client-mobile non touché |
| /e2e | ok | 10 min 29 s | — | — | — | e2e ×2 (9 min 59 s) |
| **Total cycle** | | **16 min 59 s** | **1 (16 s)** | **2 (1 min 59 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : lint ×1 (10 s)
