# todo-task-341.md — Aucune donnée de santé ni saisie du praticien dans les journaux et la télémétrie

**Repos**: api-mail
**Dependencies**: — (aucune)
**Epic**: E009
**Single frontend**: true
**Priorité**: **2** — des **constats cliniques** (réponse brute du modèle de tagging), des saisies libres du praticien, une adresse de messagerie et des noms de dossiers personnels partent dans Seq, OTLP ou un `/metrics` non authentifié.

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, **AUD-37**, **AUD-55**, **AUD-60**, **AUD-61**).
> Règle rappelée : l'INS et les données de santé vont dans le journal d'audit en base, **jamais** dans
> Seq / Graylog / OTLP (mémoire « INS — audit oui, logs jamais », task-184, task-265).

## Ce qui est établi (develop @ `14d58398`)

1. **Réponse du LLM (AUD-37)** — `EmailTaggingService.cs:296` :
   `logger.LogWarning(ex, "... Failed to parse JSON response: {Response}", response);` — sur JSON invalide,
   la réponse entière (qui cite par construction du prompt valeurs biologiques et diagnostics) est
   journalisée au niveau Warning, toujours actif. Le même fichier a été durci par task-265.
2. **Saisies libres (AUD-55)** — `AiController.cs:102` et `AiTextService.cs:100` journalisent la
   description d'un modèle (« courrier pour Mme Martin, suivi de son diabète ») en Information ;
   `AiController.cs:70` journalise chaque morceau du texte médical corrigé en Debug (actif en Staging : `Serilog__MinimumLevel__Default: "Debug"`).
3. **Route morte qui journalise une adresse (AUD-60)** — `POST account/mss-imap-test` : exclue du middleware
   (`UserContextEnricherMiddleware.cs:67-70, 164-169`) donc jeton PSC vide → échoue toujours ; journalise
   l'adresse candidate non masquée en Information (EventId 3700, `AccountController.cs:53-57, 111, 291-294`) ;
   aucun client vivant ne l'appelle.
4. **Labels Prometheus (AUD-61)** — `MailProcessingMetrics.cs:551-563`, `BackgroundSyncService.cs:399-506`,
   `Program.cs:219` : le label `folder=<chemin>` porte les noms de dossiers IMAP du praticien (possiblement
   nominatifs), exposés sur `/metrics` sans authentification, avec une cardinalité non bornée.

## Objective

Qu'**aucune donnée de santé, aucune saisie libre du praticien, aucune adresse en clair ni aucun nom de
dossier personnel** n'atteigne les journaux techniques ou la télémétrie, et qu'un garde-fou empêche la réintroduction.

### Périmètre

1. Tagging : journaliser longueur et type d'exception seulement ; compter l'échec (`RecordTaggingFailure`).
2. Saisies libres IA : longueur seulement, aux trois emplacements.
3. `mss-imap-test` : route et exclusion supprimées (remplacées par `POST account/mailboxes`) ; si l'humain
   préfère la garder, adresse masquée et exclusion corrigée.
4. Métriques : label `folder` réduit à une catégorie bornée (inbox, sent, drafts, trash, other).
5. **Garde-fou** : test d'architecture ou analyseur qui refuse un paramètre de log nommé comme une donnée
   sensible (réponse de modèle, corps, description, texte, INS, NIR…) — nomenclature consignée.
6. Balayage complémentaire des autres `Log*` de la couche IA et de l'assistant, avec la même règle.

### Hors périmètre

- Le journal d'audit en base (où l'INS reste, par finalité réglementaire).
- Les fuites par le bus de messages (task-332).

## Definition of Done

- [ ] Build passes (0 errors) — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` ; Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] **Tests rouges d'abord** (log des runs rouges dans le task file) : logger de test capturant les messages —
      réponse de tagging invalide contenant « Potassium 6,8 mmol/L » → sur le code actuel présente dans le log ; après correctif absente
- [ ] Test : description et texte corrigé absents des logs (Information et Debug)
- [ ] Test : route `mss-imap-test` supprimée (404) — ou adresse masquée si conservée par décision humaine consignée
- [ ] Test : un dossier nommé « Dupont Jean » produit le label `folder="other"`
- [ ] Test d'architecture / analyseur de garde-fou actif et vert sur le code corrigé, **rouge** sur une réintroduction volontaire (vérifié puis retiré)
- [ ] Compteur d'échec de tagging incrémenté sur JSON invalide
- [ ] Aucune régression des tableaux de bord qui lisent le label `folder` (vérifier et adapter les requêtes Grafana du dépôt si présentes)

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` ; Seq local ouvert (port 5341).
2. Provoquer une réponse de tagging invalide (fournisseur IA de test renvoyant un JSON tronqué) sur un compte rendu de biologie de test → dans Seq, **aucune** valeur biologique. Avant : la réponse complète en Warning.
3. Générer un modèle avec une description nominative fictive → Seq ne montre que la longueur.
4. `curl http://localhost:<port>/metrics | grep folder=` → seulement des catégories (`inbox`, `other`…), aucun nom de dossier personnel.
5. `POST /api/v1/account/mss-imap-test` → 404 (ou réponse sans adresse journalisée si conservée).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville, biologie
- **Vague Ségur** : hors Ségur — conformité PGSSI-S
- **Exigences DSR honorées** : non applicable — PGSSI-S (masquage des données de santé dans les journaux techniques)
- **INS** : jamais dans les logs (garde-fou étendu) ; inchangée dans le journal d'audit en base
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : **au cœur** — journaux techniques sans donnée de santé ; échecs de tagging comptés
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — Seq / OTLP / Prometheus dans le périmètre ; données de santé retirées
- **AIPD / impact RGPD** : à informer le DPO — données de santé présentes dans les journaux techniques avant correctif (durée de rétention Seq à vérifier)

## Branches
- `api-mail` (pushed) : feat/task-341-no-health-data-in-logs — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-341-no-health-data-in-logs

## Timings

*(généré par `tools/timing/report.sh --task task-341 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 29 s | — | — | — | — |
| /develop | ok | 27 min 34 s | 10 (1 min 36 s) | 11 (5 min 03 s) | — | api-mail 10B/11T |
| /sonar | ok | 19 min 36 s | 2 (52 s) | 10 (9 min 58 s) | 4 (4 min 57 s) | 2 itération(s), api-mail 2B/10T |
| /lint-angular | skipped | 2.5 s | — | — | — | client-angular non listé dans Repos, aucun travail Angular |
| /lint-mobile | skipped | 3.2 s | — | — | — | client-mobile non listé dans Repos |
| /e2e | ok | 13 min 45 s | — | — | — | e2e ×6 (23 min 52 s), 2e passage vert, parite verte apres restauration E2E-MAIL-005 angular |
| /review | ok | 5 min 46 s | 1 (35 s) | 1 (3 min 47 s) | — | api-mail 1B/1T |
| /tech-writer | ok | 1 min 29 s | — | — | — | — |
| **Total cycle** | | **1 h 08 min** | **13 (3 min 04 s)** | **22 (18 min 49 s)** | **4 (4 min 57 s)** | |

## Develop log

- Repos touched : api-mail (seul repo listé). Aucun DTO, aucun interop, aucun SDK touchés.
- Commits (api-mail, `feat/task-341-no-health-data-in-logs`, poussés) :
  - `5e52a9cd` fix(telemetry): réponse de tagging hors des journaux + label `folder` borné (AUD-37, AUD-61)
  - `c9f5d050` fix(ai): saisies libres et objets de mail hors des journaux + garde étendu (AUD-55, balayage)
  - `9d8aa7f7` fix(account): route morte `mss-imap-test` et son exclusion retirées (AUD-60)
- **Tests rouges d'abord**, constatés sur le code non corrigé (squelette `FolderMetricCategory` à comportement inchangé pour compiler) :
  - `TaggingInvalidResponseLogHygieneTests` (3) : rouges. Fuite « Potassium… » présente en Warning, longueur absente, compteur `invalid_response` à 0.
  - `FolderMetricLabelTests` (19) : rouges. « Dupont Jean » publié tel quel dans le label `folder`.
  - `SensitiveLogTemplateScanTests.NoProductionSourceLogsFreeContentOrAModelResponse` : rouge sur 12 gabarits (AiController ×2, AiTextService, EmailTaggingService, EmailSummaryService ×4, MdnService, MailCancellationService, plus 2 noms trompeurs, `{Subject}` d'un certificat et le booléen `{DtoContent}`, renommés).
  - Intégration (règle 1b), `AiFreeTextOutOfLogsIntegrationTests` : rouges. `generate-template` journalisait la description en Information (contrôleur + service), `correct-text` chaque morceau corrigé en Debug.
  - Intégration, `StaleClientEmailMailboxManagementIntegrationTests.RetiredImapTestRoute_Answers404_WhileTheAttachRouteIsServed` : rouge (500 au lieu de 404) sur le code d'avant. **Mutation** : action `mss-imap-test` réinjectée → rouge (200 au lieu de 404), puis restaurée.
- **Garde-fou** : `SensitiveLogTemplateScanTests` étendu par une seconde nomenclature, consignée dans le doc XML de `FreeContentPlaceholder` : Response, Completion, Answer, Explanation, Chunk, Prompt, Question, Description, Text, Content, Body, Html, Markdown, Snippet, Excerpt, Subject. Elle complète la nomenclature INS/NIR/traits de task-184. **Mutation** : `{Response}` réintroduit dans `EmailTaggingService` → rouge (`EmailTaggingService.cs:303 — {Response}`), puis retiré.
- Décisions :
  - `mss-imap-test` **supprimée** (option par défaut du périmètre). L'attribut `AllowMissingMssEmail` devient orphelin et est supprimé, de même que le paramètre mort `allowMissingMssEmail` du middleware. Les DTOs `MssImapTest*` restent : ils servent encore au rattachement et vivent dans `dtos-mss`, porteur de contrat non touché.
  - Label `folder` : catégorie lue depuis le chemin (`FolderMetricCategory`), appliquée **dans** `RecordSyncDuration`/`RecordSyncEmails`, donc sûre pour tout appelant. Un nom connu n'est reconnu qu'à la racine ou directement sous `INBOX` : un `Sent` sous un dossier personnel reste `other`.
  - Tableaux de bord : aucune requête Grafana ni aucun script du workspace ne lit `mssante_sync_*` (recherche json/yaml/py/js/md). Rien à adapter.
- Hors périmètre, signalé : les **journaux** (pas les métriques) portent encore le chemin de dossier en `{Folder}` à de nombreux endroits (Debug/Error de la synchronisation, par exemple). AUD-61 ne visait que les labels Prometheus. À traiter par une task dédiée si l'humain le souhaite.
- Local build / test : ✓ `dotnet build` 0 erreur. `dotnet test` : 0 échec (domain 190, infrastructure 683, application 3 468, api 1 172, integration 813 + 16 ignorés). Aucun FATAL ni crash.
- Passe qualité (/simplify) :
  - No change : api-mail (relecture du diff, aucun cleanup net). Contrôles mécaniques §Q 2b : un S103 (regex du garde > 150 car.), corrigé par concaténation avant le commit, puis classe revalidée (8/8).
  - Skipped (contract/excluded) : dtos-mss, interop-cda, sdk (non touchés)
- DOD self-check : 8/8 vérifiables par commande (Build, tests, rouges d'abord, description/texte absents en Information et Debug, route 404, `folder="other"` pour « Dupont Jean », garde rouge sur réintroduction, compteur d'échec incrémenté, tableaux de bord vérifiés). Observation Seq et `/metrics` en réel : différée au test manuel (HAG).
- Next step : /sonar task-341

## Sonar log

- Serveur 25.6.0.109173 (`sonar.token`), port 9001 mesuré. 2 analyses complètes (Release + OpenCover, 5 projets).
- Phase 1 (new code) : **aucune issue introduite par task-341.** Le seul finding sur un fichier du diff, S138 sur `MailRepository.LoadBulkContentLookupsAsync` (l. 1768), vient du commit `c1b5ff93`, antérieur à la task. La task n'a touché que la ligne 727 de ce fichier. `new_violations` : 68 avant, 68 après, tous hors des lignes de la task. Hotspots new-code : 13 `TO_REVIEW`, aucun sur un fichier de la task.
- Le Quality Gate reste ERROR (`new_violations`, `new_security_hotspots_reviewed`) **par héritage** : la new-code period inclut des tasks déjà mergées (constat connu, cf. mémoire « Sonar — la new-code period inclut des tasks déjà mergées »). Les corriger sortirait du périmètre (règle 6).
- Couverture du nouveau code : 3 conditions découvertes après la 1re analyse (2 dans `FolderMetricCategory`, 1 dans `AiController`, description nulle), couvertes par `6ed2d95b`. 2e analyse : **100 %** sur `FolderMetricCategory.cs`, `AiController.cs`, `EmailTaggingService.cs`, `AccountController.cs`. `new_coverage` projet 98,1 %.
- Tests ajoutés : 6 (5 cas de théorie `FolderMetricCategory`, 1 `AiControllerTests.GenerateTemplate_WithNullDescription_ThrowsValidation`).
- Phase 2 (legacy) : non lancée. Les 68 findings ouverts appartiennent à d'autres tasks, best-effort.
- Build / tests : ✓ verts (Release). domain 190, application 3 473, infrastructure 683, api 1 173, integration 813 + 16 ignorés.
- Conventions : `conventions/csharp.md` S103 → Occurrences 4 (regex du garde > 150 car., attrapée avant commit par §Q 2b).

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | ERROR (hérité) | ERROR (hérité) | → |
| New coverage | 98,1 % | 98,1 % | = |
| Bugs | 2 | 2 | = |
| Vulnerabilities | 0 | 0 | = |
| Security hotspots | 15 | 15 | = |
| Code smells | 70 | 70 | = |
| Coverage (projet) | 97,9 % | 97,9 % | = |
| Duplication | 0,3 % | 0,3 % | = |
| Reliability / Security / Maintainability | D/A/A | D/A/A | → |

## Lint log

- /lint-angular : skipped — `client-angular` non listé dans `**Repos**`, aucun travail Angular laissé par `/develop`.
- Note : `Client/Angular/front` porte 2 fichiers modifiés (`apps/mss` et `apps/weda2`, `environments/environment.ts`). C’est du WIP humain antérieur, sans lien avec la task, laissé intact.
- /lint-mobile : skipped. `client-mobile` n’est pas listé dans `**Repos**` et son arbre de travail est propre, sur `develop`.

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail touché | ✅ verte | 30 verts, 0 flaky, 0 rouge, 0 quarantaine (3 scénarios humains non joués) | voir journal de mesure |
| angular | api-mail touché | ⛔ parité rouge | 29 verts, 0 flaky, 0 rouge, 0 quarantaine, **1 scénario requis absent** | voir journal de mesure |

- Backend : `api-mail` @ `6ed2d95b` (branche de la task). Clients : `client-mobile` @ `origin/develop`, avancé en avance rapide d'un commit avant la voie. `client-angular` @ `feature/nova-rewriting-mss` (`30b27715`), arbre de l'humain.
- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task. La task ne le modifie pas.
- Quarantaines : aucune
- Divergences ouvertes : aucune
- Parcours touchés sans spec e2e modifié : aucun (task backend uniquement)
- Démontage : complet (ports 5052/8100/4200/3993/3465/3143 libres, aucun conteneur e2e résiduel)
- **Verdict : ROUGE, parité.** `E2E-MAIL-005` est requis pour angular, mais aucun test ne le porte dans `Client/Angular/front/e2e/mss-e2e/specs/functional.e2e.ts`. Ce n'est **pas une régression de task-341** : le scénario vient de task-353 (archivée), dont le test Angular était resté non commité (mode code-only). Il ne figure dans aucun commit, aucune branche ni aucun stash du clone Angular. Détails : `questions/task-341.md`.

**E2E : ROUGE** — 1 motif(s) de blocage.

**Bloquant** (1) :

- [angular] parité MissingRequired : E2E-MAIL-005 (« Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide ») est requis pour angular mais absent de sa suite, ou non joué.

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
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ⛔ non joué | ✅ |
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

**Parité : ROUGE** — 1 écart(s) :

- `MissingRequired` [angular] E2E-MAIL-005 (« Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide ») est requis pour angular mais absent de sa suite, ou non joué.

### E2E — 2ᵉ passage (après restauration d'E2E-MAIL-005 côté Angular) : ✅ VERT

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail touché | ✅ verte | 30 verts, 0 flaky, 0 rouge, 0 quarantaine (3 scénarios humains non joués) | voir journal de mesure |
| angular | api-mail touché | ✅ verte | 30 verts, 0 flaky, 0 rouge, 0 quarantaine (3 scénarios humains non joués) | voir journal de mesure |

- Backend : `api-mail` @ `6ed2d95b` (branche de la task). Clients : `client-mobile` @ `origin/develop` ; `client-angular` @ `feature/nova-rewriting-mss` (`8a288e97`, qui porte désormais le test `E2E-MAIL-005`), arbre de l'humain.
- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task (non modifié par la task).
- Quarantaines : aucune · Divergences ouvertes : aucune · Parcours touchés sans spec e2e modifié : aucun.
- Démontage : complet (ports libres, aucun conteneur e2e résiduel).
- Le blocage du 1er passage (`questions/task-341.md`) est **levé**.

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

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/279 — label `awaiting-human-merge`
- Aucun autre repo touché (task mono-repo, `**Single frontend**: true`).

## Code Review Summary

- **Verdict : APPROVED.** 15 fichiers de production et 10 de tests relus, 0 bloquant, 2 suggestions.
- Validation `/review` : build 0 erreur. Tests : 0 échec (domain 190, infrastructure 683, application 3 473, api 1 173, integration 813 + 16 ignorés), aucun crash. Branche à jour avec `origin/develop` (0 commit de retard).
- DoD : 8/8.
  1. Build et tests verts.
  2. Rouges d'abord consignés (`## Develop log`).
  3. Description et texte corrigé absents des journaux en Information et Debug (intégration).
  4. Route 404 (intégration + mutation).
  5. `folder="other"` pour « Dupont Jean ».
  6. Garde rouge sur réintroduction (mutation `{Response}`).
  7. Compteur `invalid_response` incrémenté.
  8. Aucun tableau de bord à adapter.
- Règle 1b, comportement → test → preuve rouge :
  - `POST ai/generate-template` (journaux) → `AiFreeTextOutOfLogsIntegrationTests.GenerateTemplate_ANominativeDescription_…` → rouge sur le code d'avant.
  - `POST ai/correct-text` (journaux) → `AiFreeTextOutOfLogsIntegrationTests.CorrectText_…` → rouge sur le code d'avant.
  - `POST account/mss-imap-test` retirée → `StaleClientEmailMailboxManagementIntegrationTests.RetiredImapTestRoute_…` → rouge sur le code d'avant (500) et par mutation (200).
  - Tagging et label `folder` : déclenchés par le consumer et par la synchronisation de fond, pas par un endpoint. Preuve unitaire, rouge sur le code d'avant.
- Double verrou e2e : `## E2E log` vert (2ᵉ passage), mobile 30/30 et angular 30/30, parité verte.
- Suggestions (non bloquantes) :
  - retirer les DTOs `MssImapTest*` de `dtos-mss`, devenus sans appelant serveur ;
  - traiter dans une task dédiée le chemin de dossier encore présent dans les **journaux** (`{Folder}`).
