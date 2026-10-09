# todo-task-334.md — La synchronisation de fond traite un mail exactement comme l'ouverture à l'écran : mêmes documents, même audit, même nettoyage

**Repos**: api-mail
**Dependencies**: task-333 (la garde d'échec technique et le verrou d'enrichissement, que le constructeur unique réutilise)
**Epic**: E009
**Single frontend**: true
**Priorité**: **2** — un mail ingéré par la synchro de fond perd définitivement son accusé de lecture, son rattachement de message patient, ses traces d'audit et ses notifications ; ses archives CDA restent sur disque ; ses actions rejouées sont tracées hors du tenant du praticien.

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, **AUD-11** — contre-vérifié —, **AUD-12**, **AUD-13**,
> **AUD-14**, **AUD-15**, **AUD-65**). Cause commune : la synchro de fond a **son propre** constructeur
> de mail et sa propre copie d'identité, qui ont manqué les correctifs du chemin de premier plan.

## Ce qui est établi (develop @ `14d58398`)

1. **Archives jamais supprimées (AUD-11)** — `BackgroundImapService.cs:223-297` : la liste `fetched` de
   `FetchedBackgroundMail` (`IDisposable`, propriétaire de ses archives) n'est jamais libérée (ni `using`,
   ni `finally`) ; `BackgroundEnrichmentProcessor` ne libère rien non plus. CDA et PDF en clair restent
   dans `%TEMP%/mss-ihe-xdm/` jusqu'au redémarrage. Le premier plan a été corrigé en task-228
   (`ImapService.cs:1699-1717`, `DisposeAll`).
2. **Identité incomplète (AUD-12)** — `BackgroundSyncManager.cs:147-158`, `BackgroundEnrichmentProcessor.cs:178-192`,
   `AddNewMailConsumer.cs:161-168`, `Create*ContactConsumer` : copie champ par champ (interdite par task-234)
   au lieu de `CopyIdentityTo`, sans `TenantId` ni `RegisteredDatabaseName`. Les actions rejouées en début
   de synchro (acquittement biologique avec `PatientIns`, drapeaux, envoi) sont tracées sous `Guid.Empty`
   → **invisibles** dans l'écran d'audit du praticien (RLS) — le défaut de task-300 × 312.
3. **Constructeur divergent (AUD-13)** — `BackgroundEnrichmentProcessor.cs:234-292`, `BackgroundImapService.cs:230-233` :
   en-têtes non récupérés (`ReadReceiptTo` vide → accusé de lecture jamais détecté) ; `IsFromPatient` /
   `PatientInsMatricule` non posés (messages Mon Espace Santé sans document COURRIER ni lien patient) ;
   aucune trace `MailReceive` ni `MedicalDocumentProcess` ; aucune notification (enrichi, remplacé, suppression).
4. **HTML non assaini (AUD-14)** — `BackgroundEnrichmentProcessor.cs:258-266` stocke le HTML brut
   (le premier plan assainit, `EmailBuildingService.cs:69`) ; le mode hors ligne
   (`OfflineMailDataProvider.cs:120-131`) le sert tel quel.
5. **Candidats (AUD-15)** — `BackgroundSyncService.cs:384-403` : `missingUids = IMAP − GetExistingUidsAsync`
   exclut les lignes « en-têtes seuls » laissées par le listing → un mail dont l'enrichissement de premier
   plan a échoué n'est jamais repris par la synchro.
6. **Mineurs (AUD-65)** — notification « nouveau mail » jamais émise (`BackgroundImapService.cs:205`,
   `isIncrementalSync` toujours faux) ; synchro « réussie » sur des lots injoignables
   (`BackgroundSyncService.cs:503-504` ignore `EnrichmentOutcome`) ; `ex.Message` brut envoyé au client
   par SSE (`:134`) ; vecteur `null` écrasant un index valide à la relivraison (`MailRepository.cs:2872`) ;
   double politique de retry MassTransit (jusqu'à ~16 appels LLM par message).

## Objective

Qu'un mail soit **construit, persisté, audité, notifié et nettoyé par une seule séquence**, qu'il arrive
par l'ouverture à l'écran ou par la synchronisation de fond ; que le travail de fond s'exécute sous
l'identité complète du praticien ; et que la synchronisation reprenne tout mail non encore analysé.

### Périmètre

1. **Constructeur unique** : la synchro de fond utilise `IEmailBuildingService` et la même séquence
   post-persistance que le premier plan (audit, notifications, rafraîchissements, messages patient) ;
   le FETCH récupère les en-têtes nécessaires.
2. **Nettoyage** : les archives extraites sont libérées sur **tous** les chemins (succès, erreur, annulation).
3. **Identité** : `CopyIdentityTo` partout où un travail quitte la requête (gestionnaire de synchro,
   processeur, trois consommateurs) ; plus aucune copie champ par champ.
4. **Candidats** : `IMAP − GetEnrichedUidsAsync` ; une ligne « en-têtes seuls » est promue.
5. **Mineurs** : notification « nouveau mail » réellement émise ; progression fidèle à `EnrichmentOutcome` ;
   message d'erreur SSE générique ; pas d'écrasement d'un vecteur valide par `null` ; une seule politique de retry.

### Hors périmètre

- La garde d'échec technique elle-même (task-333, prérequis).
- Les notifications entre réplicas (task-336).

## Definition of Done

- [ ] Build passes (0 errors) — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` ; Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] **Tests rouges d'abord** (log des runs rouges dans le task file), rouges sur le code actuel :
  - [ ] synchro de fond d'un mail porteur d'`IHE_XDM.ZIP` → après le lot, **aucune** archive ne reste dans le répertoire de travail (aussi en erreur et en annulation)
  - [ ] action rejouée en début de synchro → trace d'audit sous le **tenant du praticien**
  - [ ] mail entrant avec `Disposition-Notification-To` ingéré en fond → `ReadReceiptTo` renseigné
  - [ ] message patient Mon Espace Santé ingéré en fond → document COURRIER et lien patient créés
  - [ ] mail HTML contenant `<script>` ingéré en fond → stocké assaini
  - [ ] ligne « en-têtes seuls » existante → reprise et enrichie par la synchro
- [ ] Test : traces `MailReceive` et `MedicalDocumentProcess` émises en fond comme au premier plan
- [ ] Test d'architecture : aucune copie champ par champ de `UserContextInfo` hors de `CopyIdentityTo` / `CopyTo`
- [ ] Tests des mineurs : notification « nouveau mail », progression sur lot injoignable, message SSE générique, vecteur non écrasé
- [ ] Non-régression : tests existants du premier plan (task-228, task-293) et de la synchro verts
- [ ] Aucune INS, contenu CDA ni corps de mail dans les logs

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` (profil banc, seed de mails `IHE_XDM.ZIP` via `loadtest-skill`).
2. Lancer une synchro complète (`POST /api/v1/sync/start`) sans ouvrir de mail.
3. **Archives** : pendant et après la synchro, le répertoire `mss-ihe-xdm` du poste se vide. Avant : il grossit jusqu'au redémarrage.
4. **Audit** : écran d'audit du praticien → les traces de réception et de traitement des documents des mails synchronisés sont visibles.
5. **Accusé de lecture** : un mail seedé demandant un accusé → à l'ouverture, la proposition d'accusé apparaît.
6. **Reprise** : afficher la liste (en-têtes seuls), couper l'IMAP pendant l'ouverture d'un mail (503), relancer une synchro → le mail est enrichi par la synchro.
7. Pendant la synchro, la progression reflète les lots injoignables (Toxiproxy coupé) au lieu d'afficher 100 %.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville, biologie
- **Vague Ségur** : V2
- **Exigences DSR honorées** : intégration des documents MSSanté reçus ; traçabilité de la réception ; messages patient Mon Espace Santé rattachés
- **INS** : l'INS des messages patient est lue et rattachée comme au premier plan (même règles, task-183) ; aucune INS en log
- **Authentification PS** : PSC / e-CPS inchangée ; le travail de fond hérite de l'identité complète du praticien
- **Habilitations** : inchangées — travail limité à la boîte et au tenant du praticien
- **Interop CI-SIS** : IHE-XDM / CDA r2 via `interop-cda` (chemin existant)
- **Tracé PGSSI-S** : `MailReceive`, `MedicalDocumentProcess` et actions rejouées tracés sous le bon tenant (rétention inchangée)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — archives CDA temporaires purgées ; environnement inchangé
- **AIPD / impact RGPD** : inchangé — réduit la rétention non maîtrisée de documents de santé sur disque

## Branches
- `api-mail` (pushed) : fix/task-334-synchro-fond-constructeur-unique — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-334-synchro-fond-constructeur-unique

## Develop log

- Repos touched : api-mail (branche `fix/task-334-synchro-fond-constructeur-unique`, poussée, 5 commits).
  Aucun DTO, aucun interop, aucun SDK.
- Commits (api-mail) :
  - `53e36b43` fix(sync) : constructeur unique, séquence post-persistance partagée, archives libérées,
    en-têtes récupérés (AUD-11, 13, 14)
  - `d56cb673` fix(sync) : identité complète par `CopyIdentityTo` (AUD-12)
  - `54ea5ecf` fix(sync) : candidats, progression, notification de nouveau mail, message SSE (AUD-15, 65)
  - `85f4c37d` fix(mail) : vecteur nul sans effet, une seule politique de retry (AUD-65)
  - `180f369e` refactor(sync) : passe qualité /simplify
- **Ce qui change** :
  - `EnrichedMailPersistence` (nouveau) : la séquence qui suit la construction d'un mail, écrite une
    fois. Elle couvre l'écriture, l'éviction du cache, la publication IA (avec le type de document,
    task-344), la trace `MailReceive`, les notifications d'enrichissement, de remplacement et de
    suppression, et la notification « nouveau mail ». `ImapService` et `BackgroundEnrichmentProcessor`
    l'appellent tous les deux. Le processeur construit le mail par `IEmailBuildingService`, comme le
    premier plan : en-têtes, messages patient, HTML assaini, trace `MedicalDocumentProcess`.
  - `BackgroundImapService` : archives libérées dans un `finally` sur tous les chemins ; FETCH avec
    `Headers` ; `isIncrementalSync` fourni par l'appelant.
  - `BackgroundEnrichmentProcessor` : scope de travail rempli par `CopyIdentityTo`. L'écriture se fait
    sous le verrou de persistance du premier plan (`LockEnrichPersistAsync`) et est sautée si le
    premier plan a analysé le mail entre-temps. Seules la vérification et l'écriture sont sérialisées.
  - `BackgroundSyncManager` et les trois consommateurs : `CopyIdentityTo` au lieu des recopies champ
    par champ. Le tenant et le nom de base enregistré traversent désormais.
  - `BackgroundSyncService` : candidats = IMAP − `GetEnrichedUidsAsync`. Une ligne « en-têtes seuls »
    est reprise. L'indicateur incrémental est calculé avant les lots. La progression suit
    `EnrichmentOutcome`. Le message d'erreur SSE est générique.
  - `MailRepository` : un vecteur `null` n'efface plus un vecteur valide (contenu et documents).
    `MassTransitExtensions` : plus de retry au niveau du bus, une politique par file.
- **Rouges d'abord, sur le code d'avant (`6435bbeb`)** : 9 tests nouveaux, chacun rouge sur
  l'assertion prévue.
  - Synchro de fond, Dovecot et PostgreSQL réels, tous dans `BackgroundSyncIngestionTests` :
    - archive restée sur disque (« archive CDA restée sur disque : …\mss-ihe-xdm\….zip ») ;
    - aucune trace `MailReceive` ;
    - `ReadReceiptTo` à `null` ;
    - aucun courrier patient ni lien patient ;
    - `<script>` stocké ;
    - ligne « en-têtes seuls » jamais reprise (0 ligne de contenu).
  - Vecteur effacé (`Embedding` à `null`, `MailRepositoryIntegrationTests`).
  - Scan d'identité : 5 fichiers fautifs.
  - Scan de retry : politique au niveau du bus.
  - Les tests unitaires écrits en même temps (gestionnaire, consommateurs, `BackgroundImapService`,
    `BackgroundSyncService`) ne compilaient pas sur l'ancienne signature. Ils sont prouvés par
    mutation (ci-dessous).
- **Preuves par mutation** (code restauré par copie puis `touch`, restauration vérifiée par grep et
  diff) :
  - Lot A, toutes les mutations ensemble :
    - mutations : tenant retiré du gestionnaire, du processeur et des 3 consommateurs ; garde
      « analysé entre-temps » neutralisée ; `Dispose` des archives retiré ; `Headers` retiré du FETCH ;
      candidats repris contre les lignes existantes ; progression `+= batchList.Count` ;
      `ex.Message` renvoyé au client ; indicateur incrémental forcé à faux ;
    - résultat : **14 tests unitaires rouges** et **4 tests d'intégration rouges** (archive, accusé de
      lecture, ligne « en-têtes seuls », tenant de la trace), chacun sur sa règle.
  - Lot B, tenant retiré du seul gestionnaire : le test d'intégration tracé rougit sur
    `Expected: 01a0a415-… Actual: null`. Il passe par la vraie route : `POST /api/v1/sync/start` →
    gestionnaire → file → synchro → IMAP → base.
  - Lot C, constructeur partagé sans assainissement ni détection des messages patient : les 2 tests
    d'intégration HTML et message patient rougissent dans leur forme HTTP finale.
- **Règle 1b** : la route `POST /api/v1/sync/start` (contrôleur réel, `GlobalExceptionHandler`, DI de
  la fixture) lance la synchro par le vrai `BackgroundSyncManager`, la file déterministe, le vrai
  `BackgroundSyncService`, Dovecot, Redis et la base du praticien. Les 6 tests de
  `BackgroundSyncIngestionTests` relisent la base et le canal d'audit. Seules les notifications temps
  réel vers le client sont simulées. Le vecteur est prouvé sur la vraie base
  (`MailRepositoryIntegrationTests`).
- Local build / test : ✓ 0 erreur. Suite complète 6 464 réussis, 16 ignorés, 0 échec (domain 190,
  infrastructure 683, application 3 569, api 1 185, integration 837 + 16). Mêmes totaux avant et
  après la passe qualité.
- Passe qualité (/simplify), appliquée et commitée (`180f369e`), re-validation verte :
  - verrou de persistance réduit à la vérification et à l'écriture : l'éviction et la publication
    sortent du verrou (`WriteAsync` / `AfterWriteAsync`) ;
  - fabrique `EnrichedMailPersistence.Create(provider, logger)` au lieu de 8 résolutions écrites à la
    main ;
  - `BackgroundImapService` ramené à un seul retour, avec `<inheritdoc/>` ;
  - usings morts et documentation XML orpheline retirés d'`ImapService` ;
  - contrat `IMailRepository` mis en accord (« `null` n'efface rien ») ;
  - `WireExisting` mis en commun (`TestInfrastructure/MailRepositoryStubs.cs`).
  - **Écartés, en suggestions pour la revue** :
    - re-vérification « analysé entre-temps » aussi côté premier plan : changement de comportement ;
    - insertion idempotente par l'index unique `MailContents.MailId` à la place du verrou ;
    - requête unique lignes existantes et analysées par dossier ;
    - helper `DisposeAll` générique et éviction par liste (duplications préexistantes) ;
    - montage commun des scopes de test ; scan d'identité dérivé par réflexion.
  - Contrôles mécaniques : S125 ×3 et S103 ×5 corrigés avant la passe. `conventions/csharp.md`
    incrémenté (S125 → 14, S103 → 5).
- Hors périmètre, noté pour la revue : 31 fichiers, juste au-dessus des ~30 de la règle 5.
- DOD self-check :
  - ✓ build, tests ;
  - ✓ les 6 tests rouges d'abord de la DOD (archives en succès, erreur et annulation au niveau
    unitaire, plus l'archive réelle en intégration ; tenant ; accusé de lecture ; message patient ;
    HTML ; ligne « en-têtes seuls ») ;
  - ✓ traces `MailReceive` et `MedicalDocumentProcess` en fond, sous le tenant du praticien ;
  - ✓ test d'architecture d'identité ;
  - ✓ mineurs : nouveau mail, lot injoignable, SSE générique, vecteur, retry ;
  - ✓ non-régression premier plan et synchro : suites existantes vertes ;
  - ✓ aucune INS, aucun CDA ni corps de mail dans les journaux ajoutés : UID, dossier et MailId
    seulement.
- Next step : `/sonar task-334`.

## Sonar log

- Serveur 9.9.8.100196 (`sonar.login`), port 9000. Deux analyses de la branche.
- Phase 1 (code neuf) : ✓ Quality Gate OK, new_coverage = 97,5 %. 0 bug, 0 vulnérabilité, 0 hotspot.
  - Première analyse : 4 constats sur le code de la task, corrigés à la main :
    - S3358 : ternaire imbriqué dans `EnrichedMailPersistence`, remplacé par `SkipReasonOf` ;
    - CA1875 ×2 : `Regex.Count` dans le scan MassTransit ;
    - CA1861 : tableau littéral dans un `Arg.Is`.
  - Seconde analyse : plus aucun constat du code de la task. Reste le S107 de
    `SemanticSearchService.cs:395` (task-329), hors task, comme pour task-351 à 355.
- Phase 1, issues fixées : 4 (smells). Tests ajoutés : 0 (couverture déjà au-dessus de la cible).
- Phase 2 (legacy) : sautée, les cibles du projet sont tenues (0 bug, 0 vulnérabilité, A/A/A,
  couverture 98,0 %).
- `conventions/csharp.md` : CA1861 → 3 occurrences ; S3358 et CA1875 créées. Le contrôle mécanique de
  `/develop` avait déjà porté S125 → 14 et S103 → 5.
- Passes OpenCover (Release) : domain, application, infrastructure et api vertes. Intégration :
  834 réussis, 3 rouges, les trois tests « du jour » (`FilterTodayEmails…`, `GetFolderTodayAsync…`,
  `GetFolderNotSeenTodayAsync…`). Les analyses ont tourné à 00:05 et 00:11, heure locale, dans la
  fenêtre connue de 00:00 à 02:00 : le corpus est en heure locale, Dovecot compare `SINCE` en UTC.
  Rouges aussi sur `develop`, sans lien avec la task.

### KPIs qualité (baseline → final)

| Métrique | Baseline (analyse du 2026-10-08, task-355) | Final (branche task-334) | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 97,5 % | 97,5 % | 0 |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 13 | 13 | 0 (4 introduits par la task, 4 corrigés) |
| Coverage (projet) | 97,9 % | 98,0 % | +0,1 pt |
| Duplication | 0,4 % | 0,4 % | 0 |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

## Lint log

- `/lint-angular` : skipped. `client-angular` n'est pas listé. L'arbre porte 2 fichiers de travail non
  commité de l'humain (`apps/mss/…/environment.ts`, `apps/weda2/…/environment.ts`), non touchés
  (règle 6).
- `/lint-mobile` : skipped. `client-mobile` n'est pas listé, aucun diff.

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail touché | ✅ verte | 31 verts, 0 flaky, 0 rouge, 0 quarantaine | voir Timings |
| angular | api-mail touché | ✅ verte | 31 verts, 0 flaky, 0 rouge, 0 quarantaine | voir Timings |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task (inchangé par la task).
- Clone mobile : `develop`, aligné sur `origin/develop`. Angular : branche de l'humain, avec ses
  2 `environment.ts` non commités.
- Quarantaines : aucune
- Divergences ouvertes : aucune
- Parcours touchés sans spec e2e modifié : aucun (aucun écran touché)
- Démontage : complet (ports libres, aucun conteneur e2e résiduel)

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

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
| E2E-DETAIL-001 | 1 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
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

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/283, label
  `awaiting-human-merge`.
- Aucun autre repo. Les voies e2e mobile et Angular ont été rejouées contre l'api-mail de la branche,
  vertes.

## Code Review Summary

**Verdict : APPROVED.** 33 fichiers relus ; 0 bloquant, 3 suggestions.

- Build : 0 erreur. Tests de `/review` : 6 461 réussis. Les 3 tests « du jour » sont rouges à 00:27,
  dans la fenêtre connue de 00:00 à 02:00 (écart heure locale / UTC du corpus, rouges aussi sur
  `develop`). Le même jeu était vert avant minuit (837/837 en intégration).
- Règle 1b, comportement → test → preuve rouge :

  | Comportement (route `POST /api/v1/sync/start`) | Test d'intégration | Preuve rouge |
  |---|---|---|
  | Archives libérées | `ASyncedMailWithAnArchive_KeepsItsDocuments_AndLeavesNoArchiveOnDisk` | ancien code ; mutation lot A |
  | `MailReceive` et `MedicalDocumentProcess` sous le tenant | `…IsTracedLikeAForegroundOne_UnderThePractitionersTenant` | ancien code ; lots A et B (`Actual: null`) |
  | Demande d'accusé de lecture conservée | `ASyncedMailAskingForAReadReceipt_KeepsTheRequest` | ancien code ; lot A |
  | Courrier et lien patient | `ASyncedPatientMessage_GetsItsLetterAndItsPatientLink` | ancien code ; lot C |
  | HTML assaini | `ASyncedHtmlMail_IsStoredSanitized` | ancien code ; lot C |
  | Ligne « en-têtes seuls » reprise | `AHeaderOnlyRow_IsEnrichedByTheSync` | ancien code ; lot A |
  | Vecteur non écrasé | `MailRepositoryIntegrationTests.UpdateMailContentEmbeddingAsync_ANullVector…` | ancien code |

- Tests unitaires par branche : identité (gestionnaire, processeur, 3 consommateurs), archives (succès,
  erreur, annulation), en-têtes, indicateur incrémental, progression injoignable, SSE générique,
  « analysé entre-temps ». Tous prouvés par mutation (lot A, 14 rouges). Scans d'architecture :
  identité et retry, rouges sur l'ancien code.
- DOD : tous les items ✓ (voir Develop log).
- E2E : double verrou levé, deux voies vertes 31/31, parité verte.
- Suggestions :
  - commentaire de `ImapService.NotifyAlreadyEnrichedAsync` devenu faux ;
  - surcoût par mail pendant la première synchro massive ;
  - 33 fichiers, au-delà des ~30 de la règle 5.

## Timings

*(généré par `tools/timing/report.sh --task task-334 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 18 s | — | — | — | — |
| /develop | ok | 38 min 55 s | 12 (46 s) | 14 (8 min 58 s) | — | api-mail 12B/14T, constructeur unique, identite complete, candidats, mineurs ; 9 rouges d'abord, 3 lots de mutation |
| /sonar | ok | 11 min 46 s | 3 (33 s) | 10 (8 min 20 s) | 4 (1 min 09 s) | 2 itération(s), api-mail 3B/10T, QG OK, 4 smells du code neuf corriges ; S107 task-329 hors task |
| /lint-angular | skipped | 0.5 s | — | — | — | client-angular non liste ; 2 fichiers de WIP humain (environment.ts) non touches |
| /lint-mobile | skipped | 0.4 s | — | — | — | client-mobile non liste, aucun diff |
| /e2e | ok | 10 min 48 s | — | — | — | e2e ×3 (10 min 20 s), 2 voies vertes 31/31, parite verte, 0 flaky |
| /review | ok | 4 min 16 s | 1 (9.1 s) | 1 (3 min 06 s) | — | api-mail 1B/1T, APPROVED, PR api-mail #283 |
| /tech-writer | ok | 1 min 06 s | — | — | — | E009 v1.94 (changelogs) / 1.86 (produit) |
| **Total cycle** | | **1 h 07 min** | **16 (1 min 29 s)** | **25 (20 min 26 s)** | **4 (1 min 09 s)** | |

## Merged

- Date : 2026-10-09, par `/merge task-334 --i-tested` (HAG : test humain attesté).
- `api-mail` : PR #283 squash-mergée → `29f6853d` sur `develop` ; label `awaiting-human-merge` retiré ;
  branche `fix/task-334-synchro-fond-constructeur-unique` supprimée (distante et locale).
- CI `develop` api-mail : verte — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/37954337053
- Staging : aucune branche `forge/staging-*` sur api-mail, rien à nettoyer.
