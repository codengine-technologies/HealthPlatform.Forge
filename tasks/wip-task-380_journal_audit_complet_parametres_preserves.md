# todo-task-380.md — Le journal d'audit montre toutes les traces filtrées, et les paramètres du médecin ne sont jamais écrasés

**Repos**: client-angular, api-mail (catalogue e2e `Api/Mail/e2e/scenarios.yml` seulement)
**Dependencies**: — (aucune). Le filtre « type d'action » sans effet, défaut serveur de `PostgresAuditReader.ApplyFilters`, a été corrigé par task-405 (archivée) : `ActionType`, `Search` et le filtre par personne sont appliqués côté serveur.
**Epic**: E009
**Single frontend**: true
**Priorité**: **2** — le journal d'imputabilité cache des actions, son export est incomplet et un extrait borné par dates manque des traces ; un échec de chargement des paramètres peut couper les alertes « biologie anormale » sans que le médecin le sache.

> **Origine.** Audit de détection de bugs du client Angular du 2026-10-13
> (`Docs/audits/client-angular-audit-bugs-20261013.md`, **ANG-59, ANG-60, ANG-61, ANG-62, ANG-78**).

## Ce qui est établi

> **Revérifié le 2026-11-01** sur weda2 `feature/nova-mss-weda-integration` (`35b5163c`, 2026-10-30),
> après les tasks 384, 403, 404 et 405 qui ont touché ces fichiers. Les cinq défauts sont toujours
> présents ; les numéros de ligne ci-dessous sont ceux de cette révision.

- **ANG-59** — `mss-audit.component.ts:242-260` (`deduplicateByMailUid`, appelé `:224`) garde une trace par UID sur chaque page, sans tenir compte du dossier : « Lu », « Déplacé », « Supprimé » se réduisent à la dernière ; la page est retriée par date (le tri demandé est ignoré) ; l'export CSV (`:129-163`) n'exporte que `traces()`, la page dédoublonnée. Aucun endpoint d'export n'existe côté api-mail.
- **ANG-60** — `mss-audit.component.ts:75-78` remplace le filtre au lieu de le fusionner : `success` repart de la liste déroulante du filtre (`audit-filter.component.ts:93`), `sortBy`/`sortDirection` sont perdus. `audit-list.component.ts:46-50` garde ses propres `errorOnly`, `currentPage` et tri, jamais réinitialisés par le parent : le bouton « Erreurs uniquement » reste actif et la pagination affiche une autre page que celle chargée.
- **ANG-61** — `audit-filter.component.ts:40-43` (`todayIso` en UTC) et `:97-105` : `new Date('AAAA-MM-JJ')` est minuit UTC. En UTC−4, la période du 01/10 au 01/10 couvre du 30/09 20:00 au 30/09 23:59 locales, et toute la journée choisie est exclue. Entre 00:00 et 02:00 en métropole, « aujourd'hui » dépasse le `max` du sélecteur.
- **ANG-62** — `mss-settings.component.ts:120-123, 402-420, 519-541` : un échec de `getUserSettings` laisse `DEFAULT_SETTINGS` à l'écran (alertes, dont « biologie anormale », toutes à `false`), sans message et sans blocage ; le premier réglage touché les POSTe toutes. L'erreur du `switchMap` termine le flux d'enregistrement automatique : plus rien n'est enregistré jusqu'au rechargement.
  - **Changé par task-404** : l'identité d'expéditeur ne passe plus par `saveUserSettings`. Elle a sa route (`getMailboxSenderIdentity` / `saveMailboxSenderIdentity`, `:486-511`), et un échec de chargement la verrouille (`canEdit = false`) : elle n'est plus écrasée par des valeurs vides. **Même défaut d'enregistrement** en revanche : un échec bascule le champ en lecture seule, sans message, et termine son flux d'enregistrement.
- **ANG-78** — l'aperçu d'une trace (`mss-audit.component.ts:186-199, 296-308`) n'annule pas la requête précédente et ne vérifie pas le Message-ID du mail reçu : il peut afficher le mail d'une autre trace. La recherche patient (`patient-search.component.html:7`) promet « nom, prénom, INS… » mais `searchPatients` n'envoie que `lastName` (`mss-api.service.ts:1360`).
- **Mobile** : pas d'écran de journal (cf. E2E-AUDIT-001). Ses paramètres ne sont pas concernés par ANG-62 : `user-settings.service.ts` n'enregistre rien tant que le chargement n'a pas réussi, et un échec d'enregistrement ne coupe pas le flux.

## Objective

Que le journal d'audit montre **toutes** les traces correspondant aux filtres affichés, dans l'ordre demandé, sur la période choisie en heure locale, avec un export complet ; et que les paramètres du médecin **ne soient jamais remplacés** par des valeurs par défaut à la suite d'une panne.

### Périmètre

1. **Journal** : plus de dédoublonnage (la vue par mail existe déjà via la frise par Message-ID) ; tri respecté ; filtre fusionné et non remplacé ; page pilotée par le parent ; dates construites en heure locale ; export sur tout le filtre (côté serveur si besoin, en accord avec l'équipe api-mail) ; aperçu annulable et vérifié par Message-ID.
2. **Paramètres** : édition bloquée et message tant que le chargement n'a pas réussi ; erreur d'enregistrement visible, enregistrement automatique qui reprend. Même traitement pour l'enregistrement de l'identité d'expéditeur (task-404).
3. **Recherche patient** : l'invite décrit ce qui est réellement cherché.

## Definition of Done

- [ ] Build et tests weda2 verts
- [ ] Tests unitaires et de composant rouges d'abord :
  - [ ] trois traces du même mail sur une page : les trois sont affichées ; deux traces de même UID dans deux dossiers aussi
  - [ ] tri par action : l'ordre affiché est celui du serveur
  - [ ] « Erreurs uniquement » activé puis changement de période : le filtre d'erreurs est conservé ; la page revient à 1
  - [ ] période du 01/10 au 01/10 en UTC−4 : les bornes envoyées couvrent la journée locale entière
  - [ ] échec de chargement des paramètres : formulaire désactivé, message affiché, aucun POST
  - [ ] échec d'enregistrement : message affiché, la modification suivante est enregistrée
  - [ ] échec d'enregistrement de l'identité d'expéditeur : message affiché, la modification suivante est enregistrée
  - [ ] aperçu : deux traces sélectionnées à la suite, la réponse de la première arrive en dernier → c'est le mail de la seconde qui est affiché
- [ ] Scénario E2E-AUDIT-002 « Le journal d'audit montre chaque action sur un mail » ajouté (angular `requis` ; mobile `non-applicable` — pas d'écran de journal). E2E-AUDIT-001 est pris par task-405.
- [ ] Scénario E2E-SETTINGS-004 « Paramètres indisponibles : rien n'est écrasé » ajouté (angular `requis` ; mobile `non-applicable` — le client mobile n'enregistre rien sans chargement réussi). E2E-SETTINGS-003 est pris par task-384.
- [ ] Aucune donnée de santé ajoutée aux journaux

## Manual Test Plan

1. Lire, déplacer puis supprimer un mail ; ouvrir le journal → trois traces.
2. Trier par action → l'ordre suit la colonne ; exporter → le fichier contient toutes les traces du filtre.
3. Filtrer « Erreurs uniquement », changer de période → seules les erreurs restent affichées.
4. Rendre `getsettings` indisponible (api-mail arrêtée), ouvrir les paramètres → message d'erreur, rien n'est modifiable ; relancer api-mail → les vrais paramètres s'affichent, intacts.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif
- **Exigences DSR honorées** : non applicable — rétablit l'exhaustivité de la consultation du journal PGSSI-S
- **INS** : non applicable
- **Authentification PS** : inchangée
- **Habilitations** : le journal reste cloisonné par boîte (inchangé)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : la consultation des traces devient exhaustive ; aucune trace nouvelle
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — le journal porte des métadonnées de mails
- **AIPD / impact RGPD** : inchangé

## Branches
- `api-mail` (pushed) : fix/task-380-journal-audit-complet-parametres — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-380-journal-audit-complet-parametres (catalogue e2e uniquement)
- `client-angular` (code-only) : la forge écrit sur la branche checked out dans `Client/Angular/` — `feature/nova-mss-weda-integration` @ `32cc9b79` au /start — humain gère branche, commit, push, PR TFS

## Develop log

- Repos touched : `api-mail` (catalogue e2e seulement), `client-angular` (code-only)
- DTOs published : no DTO change — Interop : no interop change
- **Export complet sans endpoint serveur** : le serveur borne `pageSize` à 200 ; l'export lit toutes les pages du
  filtre côté client (`expand`, séquentiel, plafond 10 000 traces, message si le plafond est atteint). Un export
  côté serveur (CSV en flux, sans pagination par décalage) reste la solution de fond : à proposer à l'équipe
  api-mail si le volume réel le demande — non ouvert ici, hors périmètre `**Repos**` de la task.
- Commits :
  - api-mail : `c49132ac` test(e2e): catalogue E2E-AUDIT-002 et E2E-SETTINGS-004
  - client-angular : **non commité** (code-only) sur `feature/nova-mss-weda-integration` — l'humain commite et pousse sur TFS
- Fichiers Angular modifiés (non commités) :
  - `libs/mss/src/features/audit/mss-audit.component.{ts,html,scss}` (+ spec **créé** `mss-audit.component.spec.ts`)
  - `libs/mss/src/features/audit/components/audit-list/audit-list.component.{ts,html}`
  - `libs/mss/src/features/audit/components/audit-filter/audit-filter.component.{ts,spec.ts}`
  - `libs/mss/src/features/settings/mss-settings.component.{ts,html,scss,spec.ts}`
  - `libs/mss/src/features/patient/components/patient-search/patient-search.component.{html,spec.ts}`
  - `e2e/mss-e2e/specs/functional.e2e.ts`, `e2e/mss-e2e/support/e2e-backend.ts`
- Correctifs :
  - **ANG-59** : plus de dédoublonnage ; la page est celle du serveur, dans l'ordre demandé ; l'export lit tout le filtre.
  - **ANG-60** : filtre du panneau fusionné (tri gardé) ; « Erreurs uniquement » appliqué par `requestFilter` (calculé) et
    rendu au statut du panneau quand on le retire ; `AuditListComponent` devenu contrôlé (page, tri, erreurs, export en entrées).
  - **ANG-61** : dates `AAAA-MM-JJ` construites en heure locale (`localDay`, `localIsoDate`) ; `max` du sélecteur en date locale.
  - **ANG-62** : échec de chargement → écran d'erreur + « Réessayer », aucun réglage modifiable, aucun POST (garde dans
    `triggerSave`) ; échec d'enregistrement annoncé, `catchError` dans le `switchMap` (le flux continue) ; même traitement
    pour l'identité d'expéditeur (plus de verrouillage silencieux).
  - **ANG-78** : aperçu annulable (abonnements abandonnés + garde de sélection, consigne `reponse-d-un-contexte-depasse`),
    mail affiché seulement si son Message-ID est celui de la trace ; invite de recherche patient « Rechercher un patient par nom ».
- Tests unitaires (Vitest) : 16 ajoutés, vus **rouges** avant correctif (sur l'assertion prévue), verts après.
- Preuves par mutation (unitaires, code restauré par `cp`) — chaque mutation rouge sur le test visé :
  - M1 dates en UTC (ancien calcul) → 2 tests dates rouges
  - M2 dédoublonnage par UID réinjecté → 3 tests (trois traces, deux dossiers, tri) rouges
  - M3 aperçu non annulable (garde + désabonnement retirés) → test « réponse de la première en dernier » rouge
  - M4 filtre remplacé (tri et erreurs perdus) → 2 tests rouges
  - M5 export limité à la page 1 → test export rouge
  - M6 Message-ID non vérifié → test « autre mail à cet emplacement » rouge
  - M7 garde `triggerSave` retirée → « aucun POST » rouge
  - M8 erreur d'auto-enregistrement non captée → « la modification suivante est enregistrée » rouge
  - M9 erreur d'identité non captée → test identité rouge
- **Fuseau** : le pool Vitest `vmThreads` fige le fuseau du worker ; les tests de dates jugent la journée locale du poste
  (rouges sur l'ancien code à Paris, pas sur un agent en UTC). Consigné : `conventions/angular.md`, `fuseau-fige-sous-vmthreads`.
- Parcours e2e (Step 6b) : catalogue d'abord (`E2E-AUDIT-002`, `E2E-SETTINGS-004`, YAML relu par `yaml.safe_load`,
  `ScenarioCatalogTests` 17/17), tests Angular avec tag et version 1, `tsc --noEmit` vert. Banc `--serve-only` :
  - vert sur le code final (2/2) ;
  - E1 dédoublonnage réinjecté (marqueur vérifié **servi** dans les chunks) → E2E-AUDIT-002 rouge sur « une ligne par trace
    enregistrée (3) » : reçu 1 ;
  - E2 échec de chargement silencieux (marqueur servi) → E2E-SETTINGS-004 rouge sur « l'écran dit que les paramètres n'ont
    pas pu être lus » ;
  - vert après restauration (2/2).
  - Piège : le journal `out/logs/weda2.log` reste vide, et une comparaison de chaînes littérales est pliée par esbuild
    (marqueur jamais servi). Le marqueur servi a été vérifié par lecture des chunks de `https://localhost:4200`.
- Local build / test : weda2 `nx build` vert (NG8107 restant antérieur, task-405) ; `nx test mss-lib` 134 fichiers,
  1 464 tests, 0 échec, 0 erreur ; api-mail : `ScenarioCatalogTests` 17/17 (seul `scenarios.yml` change ; build + suite
  complets rejoués par /review). ESLint ciblé : 0 erreur (avertissements tous antérieurs).
- Passe qualité (/simplify, 4 relecteurs) :
  - Applied (code-only, uncommitted) : client-angular — `requestFilter` calculé (plus de `panelSuccess`), remise à zéro de
    l'aperçu regroupée dans `cancelPreview`, code mort retiré, accumulation linéaire de l'export, une lecture du journal par
    sondage e2e (`mailAuditTraces`), BOM du CSV remis en échappement `﻿` (l'outil d'écriture l'avait converti) ;
    re-validé : 1 464/1 464, build vert, lint 0 erreur, e2e 2/2.
  - Écartés : refonte en `switchMap` et retrait des gardes (la consigne demande les deux protections), export côté serveur
    (hors périmètre), helpers de date du design-system (non exportés par son barrel), état de chargement unique des réglages.
  - Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*
- Prévention (règle d'or) : `conventions/e2e.md` « Trous du filet » (ANG-59, E2E-AUDIT-002) ; `conventions/angular.md`
  `fuseau-fige-sous-vmthreads`.
- DOD self-check : 8/8 tests unitaires listés présents ; 2 scénarios ajoutés ; aucune donnée de santé ajoutée aux journaux.
- ⚠️ À commiter sur TFS **avant** le merge de la PR api-mail : `functional.e2e.ts` (E2E-AUDIT-002, E2E-SETTINGS-004),
  sinon la parité Angular bloquera les tasks suivantes (`test-angular-non-commite`).
- Next step : /sonar task-380

## Sonar log

- **Skipped** : le diff api-mail vs `develop` se limite à `e2e/scenarios.yml` (catalogue E2E-AUDIT-002,
  E2E-SETTINGS-004), **aucun fichier C#** : le new code Sonar est vide. Même traitement que task-350, 362, 364, 370.
  KPIs inchangés, aucune analyse lancée.

## Lint log

- Mode A (chaîné), base `origin/next`, lint scopé `tag:scope:mss` (13 projets affectés).
- Baseline : **0 erreur** ; avertissements tous antérieurs (sur les fichiers de la task : `mss-settings.component.ts`
  — `@example` vide de `loadMailServer` et `max-lines`, déjà présents en HEAD). Aucune itération : pas d'auto-fix,
  pour ne pas toucher du code hors de la task.
- Anti-régression alignée sur le pipeline : `nx affected -t test` **12 projets verts** (mss-lib 1 464, weda2 3 329,
  … 0 échec, 0 erreur non gérée).
- Fichiers modifiés par /lint-angular : aucun. Code-only : aucune opération git.

## Lint mobile log

- Skipped : `client-mobile` absent des `**Repos**` et arbre propre sur `develop`.

## E2E log

> ⚠️ **Quarantaine de plus de 14 jours** : E2E-COMPOSE-002 (angular, `live-ai.e2e.ts`) est en quarantaine depuis
> le 2026-10-09 (23 jours), et sa task de correction, task-350, est **archivée**. Le test passe à ce run : un test en
> quarantaine ne protège rien — à l'humain de la lever ou d'ouvrir la task qui la résorbe.

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail touché (catalogue) | ✅ verte | 57 verts, 0 flaky, 0 rouge, 0 quarantaine | 8 min 48 s |
| angular | api-mail + client-angular touchés | ✅ verte | 70 verts, 0 flaky, 0 rouge, 1 quarantaine (E2E-COMPOSE-002, passée) | 9 min 24 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ `fix/task-380-journal-audit-complet-parametres` (`c49132ac`)
- Nouveaux parcours joués : E2E-AUDIT-002, E2E-SETTINGS-004 (angular, verts ; prouvés rouges par mutation en /develop)
- Quarantaines : [angular] E2E-COMPOSE-002 (correction : task-350) — posée par l'humain, passée ce run
- Divergences ouvertes : aucune
- Parcours touchés sans spec e2e modifié : aucun (`functional.e2e.ts` modifié)
- Démontage : complet pour ce run (ports libres). Deux conteneurs **antérieurs** subsistent, arrêtés depuis le
  2026-10-14 (`e2e-greenmail-gcgjbrzp`, `e2e-dovecot-kgrndjwd`) : pas créés par ce cycle, laissés en l'état.
- Porte : **0** (rapport de ce run).

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

**Parité : verte** — aucun écart entre le catalogue et les suites.

## Timings

*(généré par `tools/timing/report.sh --task task-380 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 13 s | — | — | — | — |
| /develop | ok | 32 min 25 s | 2 (29 s) | 3 (1 min 05 s) | — | api-mail 0B/1T, client-angular 2B/2T |
| /sonar | skipped | 0.7 s | — | — | — | api-mail : catalogue e2e seul, aucun C# |
| /lint-angular | ok | 2 min 32 s | — | 1 (1 min 31 s) | — | client-angular 0B/1T |
| /lint-mobile | skipped | 0.6 s | — | — | — | client-mobile non touché |
| /e2e | ok | 18 min 56 s | — | — | — | e2e ×3 (18 min 12 s) |
| **Total cycle** | | **54 min 09 s** | **2 (29 s)** | **4 (2 min 36 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : lint ×1 (32 s)
