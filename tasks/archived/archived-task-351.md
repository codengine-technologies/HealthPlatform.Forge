# todo-task-351.md — Étape 2 d'AUD-42 : supprimer du contrat les champs serveur que plus personne ne lit

**Repos**: dtos-mss, api-mail, client-blazor, client-angular
**Dependencies**: task-348 **mergée et déployée**, et **tous les fronts déployés à jour** (Blazor, Angular TFS) — voir « Condition de lancement »
**Epic**: E009
**Priorité**: 4 — dette de contrat, sans effet utilisateur ; la faille est fermée par task-348.

> **Origine.** task-348 (AUD-42) a fait résoudre le serveur de messagerie par le seul serveur.
> Elle a gardé `UserSettingsDto.ImapServerConfig` / `SmtpServerConfig` marqués `[Obsolete]`,
> parce que `client-angular` est déployé par l'humain via TFS, à son rythme : un ancien front
> envoie encore ces champs, et api-mail les ignore (mis à `null`, réponse 200).

> **Condition de lancement — arbitrage humain requis.** Ne lancer que quand l'humain confirme
> que **tous** les fronts déployés (Blazor et Angular, toutes instances) sont au niveau de
> task-348 ou plus. Le risque technique est faible : un champ inconnu envoyé par un ancien front
> est ignoré par System.Text.Json, et un ancien front qui lit `imapServerConfig` reçoit déjà
> `null` depuis task-348. La condition reste posée par prudence, et c'est l'humain qui la lève.

## Objective

Retirer du contrat, puis de chaque consommateur, les deux champs serveur que task-348 a rendus
inertes, et nettoyer les valeurs résiduelles en base.

## Périmètre

1. `dtos-mss` : supprimer `UserSettingsDto.ImapServerConfig` / `SmtpServerConfig` et leur
   constante `ServerSelectionRetired`. Publication NuGet, bump d'`api-mail` et `client-blazor`.
2. `api-mail` : supprimer `SettingsController.DropServerSelection` (devenu sans objet) et le
   `#pragma warning disable CS0618` qui l'accompagne ; les tests qui prouvaient le vidage
   deviennent des tests de non-régression « `GET /settings` ne contient aucune propriété
   serveur » (JSON brut).
3. Base : script ou migration qui retire `imapServerConfig` / `smtpServerConfig` du JSON des
   réglages déjà stockés (le blob est remplacé en bloc à chaque enregistrement ; vérifier le
   format réel avant d'écrire la migration, règle 7c).
4. `client-blazor` : rien à retirer côté écran (fait par task-348) ; recompiler contre le
   nouveau DTO.
5. `client-angular` : retirer `imapServerConfig` / `smtpServerConfig` de
   `user-settings.model.ts` et la fonction `withoutServerSelection` de
   `mss-settings.component.ts` (avec ses tests), devenue sans objet.

## Hors périmètre

- `MailServerConfigDto` reste : `MailServerInfoDto` (réponse de `GET /settings/mail-server`)
  l'utilise.
- `client-mobile` : n'a jamais porté ces champs.

## Definition of Done

- [ ] Build passes (0 errors) — dtos-mss, api-mail, client-blazor, client-angular
- [ ] Tests pass (0 failures) — hors rouges pré-existants identifiés sur `develop`
- [ ] `grep -rn "ImapServerConfig\|SmtpServerConfig" Dtos Api/Mail/src Client/Blazor/Src` ne renvoie rien
- [ ] `grep -rn "imapServerConfig\|smtpServerConfig\|withoutServerSelection" Client/Angular/front/libs/mss/src` ne renvoie rien
- [ ] Test d'intégration `GET /settings` sur des réglages stockés AVANT la migration (JSON porteur des deux champs) : la réponse ne contient aucune propriété serveur, lue dans le JSON brut — vu rouge (règle 1b)
- [ ] Migration des réglages : relue, sans opération fantôme, « pending changes » vide (règle 7c)
- [ ] `dtos-mss` publié, consommateurs .NET bumpés

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost`, client Blazor et client Angular connectés
   avec une boîte de test sur `medecin.formation.mssante.fr`.
2. Blazor → Paramètres : l'encart du serveur s'affiche comme avant ; modifier la signature et
   enregistrer → succès.
3. Angular → Paramètres : même vérification.
4. `GET /api/v1/settings/getsettings` (Swagger) → la réponse ne contient ni `imapServerConfig`
   ni `smtpServerConfig`.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville, biologie
- **Vague Ségur** : V2
- **Exigences DSR honorées** : non applicable — nettoyage de contrat
- **INS** : non applicable
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : non applicable
- **Consentement patient** : non applicable
- **Référentiels métier** : non applicable
- **Hébergement HDS** : oui — environnement inchangé
- **AIPD / impact RGPD** : non applicable

## Branches

> **Condition de lancement levée par l'humain** : `/start 351` lancé le 2026-10-04, après l'exposé de la condition « tous les fronts déployés au niveau de task-348 ». Périmètre inchangé, migration des réglages stockés comprise (aucune décision contraire).

- `dtos-mss` (pushed, branche paresseuse) : `chore/task-351-retrait-champs-serveur`, créée par `/develop` au moment de toucher le contrat
- `api-mail` (pushed) : chore/task-351-retrait-champs-serveur — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/chore/task-351-retrait-champs-serveur
- `client-blazor` (pushed) : chore/task-351-retrait-champs-serveur — https://github.com/codengine-technologies/HealthPlatform.Client/tree/chore/task-351-retrait-champs-serveur
- `client-angular` (code-only) : la forge écrit sur la branche active de `Client/Angular/` (`feature/nova-rewriting-mss` au /start). ⚠️ Les fichiers de task-353 n'y sont **pas encore commités** ; ceux de task-351 (`user-settings.model.ts`, `mss-settings.component.*`) sont distincts et seront listés à part. L'humain gère la branche, le commit, le push et la PR TFS.

## Timings

*(généré par `tools/timing/report.sh --task task-351 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 27 s | — | — | — | — |
| /develop | ok | 9 min 40 s | 2 (31 s) | 4 (4 min 26 s) | — | api-mail 1B/2T, dtos-mss 1B/0T, client-blazor 0B/1T, client-angular 0B/1T |
| /sonar | ok | 6 min 52 s | 1 (19 s) | 5 (5 min 23 s) | 2 (35 s) | api-mail 1B/5T |
| /lint-angular | ok | 2 min 03 s | 1 (21 s) | 1 (53 s) | — | client-angular 1B/1T |
| /lint-mobile | skipped | 0.4 s | — | — | — | client-mobile non touché |
| /e2e | ok | 9 min 46 s | — | — | — | e2e ×3 (9 min 17 s) |
| /review | ok | 7 min 15 s | 3 (30 s) | 6 (5 min 08 s) | — | dtos-mss 1B/0T, api-mail 1B/5T, client-blazor 1B/1T |
| /tech-writer | ok | 24 s | — | — | — | — |
| **Total cycle** | | **36 min 31 s** | **7 (1 min 43 s)** | **16 (15 min 51 s)** | **2 (35 s)** | |

Autres commandes mesurées : lint ×1 (9.4 s), nuget-wait ×1 (10 s)

## Develop log

**Ordre** : dtos-mss → api-mail → client-blazor → client-angular (code-only).

### Ce qui a été fait
- **dtos-mss** (`chore/task-351-retrait-champs-serveur`, branche paresseuse créée ici) :
  - suppression de `UserSettingsDto.ImapServerConfig` / `SmtpServerConfig` et de la constante `ServerSelectionRetired` ;
  - `MailServerConfigDto` reste (utilisé par `MailServerInfoDto`) ;
  - publication **517.0.0** par la CI (run 37210303170, vert). Un second push, qui ne fait que reformuler un commentaire, republie en 518 avec la même API ; les consommateurs restent en 517.
- **api-mail** :
  - `Dtos.Mss` 517.0.0, avec les `packages.lock.json` ;
  - `SettingsController.DropServerSelection` supprimé, ainsi que son `#pragma warning disable CS0618` ;
  - les deux tests unitaires qui prouvaient le vidage sont retirés (champs inexistants), le comportement est prouvé en intégration sur le JSON brut ;
  - migration FluentMigrator **20261004120000** `RetireServerSelectionFromSettings` : un `UPDATE` qui retire les deux clés du JSON des réglages stockés (`jsonb - 'imapServerConfig' - 'smtpServerConfig'`), limité aux lignes qui les portent. Sa descente est volontairement vide.
- **client-blazor** : `Dtos.Mss` 517.0.0, recompilé. Aucun code ne nommait les champs (déjà retiré par task-348).
- **client-angular** (code-only, non commité) :
  - `imapServerConfig` / `smtpServerConfig` retirés de `UserSettingsDto` ;
  - `withoutServerSelection` et son test retirés de `mss-settings.component.ts` ; l'enregistrement envoie `this.settings()` ;
  - le spec n'emploie plus de réglages « porteurs d'un serveur » (`storedSettings`).

### Tests rouges d'abord (règle 1b)

| Comportement | Test | Preuve du rouge |
|---|---|---|
| `GET /settings` sur des réglages stockés avant task-348 (JSON porteur des deux champs) : aucune propriété serveur dans la réponse, lue en JSON brut | `SettingsMailServerEndpointIntegrationTests.GetSettings_StoredWithTheRetiredServerFields_ReturnsNoServerProperty` | rouge sur le code d'avant : `"imapServerConfig":null` présent |
| Enregistrer avec un serveur : accepté, rien n'est stocké ni rendu | `PostingAServer_IsAccepted_ButNeverStoredNorReturned_…` (adapté au JSON brut) | rouge sur le code d'avant (même cause) |
| Migration : les deux clés partent, le reste du JSON et les autres lignes restent intacts | `RetireServerSelectionMigrationTests.MigratingStoredSettings_RemovesTheServerKeys_AndKeepsEverythingElse` (coureur de production rejoué jusqu'à 20261002120000, puis lignes déposées, puis migration) | rouge sans la migration : clés présentes |

### Règle 7c (migration)
- Migration relue : elle fait ce qui est prévu.
- Aucune opération fantôme : un seul `UPDATE`, filtré.
- Pas de fichier compagnon (FluentMigrator : ni `.Designer` ni snapshot).
- « Pending changes » sans objet : le schéma n'est pas géré par des migrations EF.
- Le JSON visé a été écrit par le sérialiseur, donc la conversion en `jsonb` ne peut pas échouer.

### DOD (greps)
- `grep -rn "ImapServerConfig\|SmtpServerConfig" Dtos Api/Mail/src Client/Blazor/Src` : **0** (le commentaire du DTO a été reformulé).
- `grep -rn "imapServerConfig\|smtpServerConfig\|withoutServerSelection" Client/Angular/front/libs/mss/src` : **0**.

### Passe qualité §Q
Faite en revue directe : le diff consiste presque entièrement en suppressions, rien à simplifier.

### Validation
- api-mail : domain 190, infrastructure 683, api 1 176, application 3 433, intégration 803 (+16 ignorés).
- Blazor : 423 (+2 ignorés).
- Angular `libs/mss` : 581.
- dtos-mss : build OK.

## Sonar log

**Analyse** : une passe complète sur `chore/task-351-retrait-champs-serveur` (serveur 9.9.8), avec la couverture des cinq suites, toutes vertes : domain 190, application 3 433, infrastructure 683, api 1 176, intégration 803 (+16 ignorés).

**Aucun constat sur le code de la task**, donc aucune itération de correction.
- `SettingsController` : couverture 100 %.
- La migration est exclue de l'analyse (`**/Migrations/**`), comme toutes les migrations.
- Les 13 constats restants sont tous antérieurs : 9 × S107 et 4 × CA1829, dans des tests de 2026-03. Le seul compté en « nouveau code » est le S107 de `SemanticSearchService:395` (task-329).

### KPIs qualité (baseline → final)

| Métrique | Baseline (analyse task-353, 2026-10-04) | Final (task-351) | Δ |
|---|---|---|---|
| Quality Gate | OK | **OK** | = |
| New coverage | 97,5 % | 97,5 % (`SettingsController` 100 %) | = |
| Coverage projet | 97,9 % | 97,9 % | = |
| Bugs / Vulnérabilités / Hotspots | 0 / 0 / 0 | 0 / 0 / 0 | = |
| Code smells | 13 | 13 | = |
| Duplication | 0,4 % (nouveau code 0,15 %) | 0,4 % (nouveau code 0,15 %) | = |
| Ratings fiabilité / sécurité / maintenabilité | A / A / A | A / A / A | = |

## Lint log

- **Commande** : `npx nx affected -t lint --base=origin/next --head=HEAD --parallel=3 --projects=tag:scope:mss` (`Client/Angular/front`, `feature/nova-rewriting-mss`, code-only).
- **Baseline** : **0 erreur**, donc aucune itération.
  - 42 avertissements, tous antérieurs : `max-lines`, `require-example`, `complexity`.
  - Sur les fichiers de la task, un seul : `require-example` sur `loadMailServer` (code de task-348, ligne non modifiée).
- **Build** : 10 projets sur 11 verts. Seul `mss:build:production` est rouge, comme avant la task (`environment.prod.ts` absent).
- **Tests** : 11 projets sur 11 verts.
- **Rappel code-only** : les trois fichiers Angular de la task ne sont pas commités. Les `environment.ts` de l'humain ne sont pas touchés.

## Lint mobile log

- **Skipped** : `client-mobile` non touché par la task (absent des `**Repos**`).

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | `api-mail`, `dtos-mss` touchés | ✅ verte | 30 verts, 0 flaky, 0 rouge, 0 quarantaine | 5 min 05 s |
| angular | `api-mail`, `client-angular`, `dtos-mss` touchés | ✅ verte | 30 verts, 0 flaky, 0 rouge, 0 quarantaine | 4 min 12 s |

- **Code testé** :
  - backend `api-mail` @ `e14b70e4` (DTO 517) ;
  - `client-mobile` @ `e9577cc` (`develop`, non touché par la task, rejoué parce que le backend et le contrat ont changé) ;
  - `client-angular` @ `feature/nova-rewriting-mss`, avec les modifications non commitées de la task.
- Les rapports sont copiés dans la même commande que leur voie (`agents/e2e.md`).
- **Catalogue** : inchangé. La task ne crée ni ne modifie aucun parcours médecin : elle retire deux champs morts du contrat des réglages. Les écrans de réglages n'ont pas changé.
- **Porte `gate`** sur les copies des rapports : **code 0**. Aucune quarantaine, aucune divergence.
- **Démontage** complet : ports libres, aucun conteneur e2e résiduel.

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

- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/42 — `awaiting-human-merge`
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/277 — `awaiting-human-merge`
- `client-blazor` : https://github.com/codengine-technologies/HealthPlatform.Client/pull/92 — `awaiting-human-merge`
- `client-angular` : code-only. L'humain gère le commit, le push TFS et l'ouverture de la PR. Fichiers de la task, non commités, sur `feature/nova-rewriting-mss` :
  - `front/libs/mss/src/core/models/user-settings.model.ts`
  - `front/libs/mss/src/features/settings/mss-settings.component.spec.ts`
  - `front/libs/mss/src/features/settings/mss-settings.component.ts`
  - Les deux `environment.ts` modifiés appartiennent à l'humain ; la forge ne les a pas touchés.

**Ordre de merge** : dtos-mss → api-mail → client-blazor (règle 11 : à merger ensemble).

## Code Review Summary

**Validation** (après la fusion de `develop` / task-333 dans api-mail) :
- dtos-mss : build OK.
- api-mail : build OK ; tests domain 190, infrastructure 683, api 1 176, application 3 446, intégration 809 (+16 ignorés).
- client-blazor : build OK, 423 tests (+2 ignorés).
- client-angular : build OK, sauf `mss:build:production`, déjà rouge avant la task ; tests 11 projets sur 11 (étape `/lint-angular`).
- DOD : les deux greps renvoient 0 ; `## E2E log` vert.

**APPROVED** — 0 point bloquant, 2 suggestions.

> **Condition de lancement levée par l'humain** (`/start 351`, 2026-10-04) : tous les fronts déployés sont au niveau de task-348. Si un ancien front envoie encore les deux champs, ils sont ignorés à la désérialisation, sans erreur.

- **dtos-mss** ✅ `UserSettingsDto.ImapServerConfig` / `SmtpServerConfig` et la constante `ServerSelectionRetired` sont supprimés. `MailServerConfigDto` est conservé, parce que `MailServerInfoDto` l'utilise.
- **api-mail** ✅
  - `SettingsController.DropServerSelection` et son `#pragma warning disable CS0618` sont supprimés. Les deux tests unitaires qui prouvaient le vidage sont retirés, puisque les champs n'existent plus.
  - Migration FluentMigrator `20261004120000` : un seul `UPDATE`, limité aux lignes qui portent l'une des deux clés. L'opérateur `jsonb -` retire uniquement des clés de premier niveau. Un texte saisi par le praticien qui contiendrait ces mots est échappé dans le JSON, donc ni le filtre ni l'opérateur ne le touchent.
  - Règle 7c : migration relue, sans opération fantôme. FluentMigrator ne produit ni `.Designer` ni snapshot.
  - `Dtos.Mss` est en 517.0.0, avec ses lock files. Après la fusion de `develop` (task-333), `Interop.Cda.Parser` est en 101.
- **client-blazor** ✅ Seul le bump `Dtos.Mss` 517.0.0 change ; aucun code ne nommait les champs depuis task-348.
- **client-angular** (code-only) ✅ Les deux champs sont retirés de `UserSettingsDto`, ainsi que `withoutServerSelection` et ses tests. L'enregistrement envoie `this.settings()`.

**Règle 1b** (comportement → test d'intégration → preuve du rouge)

| Comportement | Test | Rouge |
|---|---|---|
| `GET /settings` sur des réglages stockés avant task-348, avec les deux champs dans le JSON : aucune propriété serveur dans la réponse, lue dans le JSON brut (vraie pile, PostgreSQL) | `SettingsMailServerEndpointIntegrationTests.GetSettings_StoredWithTheRetiredServerFields_ReturnsNoServerProperty` | code d'avant : `"imapServerConfig":null` présent |
| `POST` avec un serveur : accepté, rien n'est stocké ni rendu, et la connexion IMAP suivante vise le serveur du domaine | `PostingAServer_IsAccepted_ButNeverStoredNorReturned_…` (assertion passée sur le JSON brut) | code d'avant : même cause |
| Migration : les deux clés partent, le reste du JSON et les autres lignes restent intacts (migrations de production rejouées) | `RetireServerSelectionMigrationTests.MigratingStoredSettings_RemovesTheServerKeys_AndKeepsEverythingElse` | sans la migration : les clés sont présentes |

**Suggestions (non bloquantes)**
- La migration convertit en `jsonb` toutes les lignes ciblées : un JSON invalide en base ferait échouer le démarrage. Ce cas ne peut pas se produire aujourd'hui, car seul le sérialiseur écrit cette colonne. Un `WHERE … IS JSON` n'existe qu'à partir de PostgreSQL 16.
- La conversion `jsonb` réordonne et reformate le JSON des lignes migrées. Le dépôt le relit par désérialisation, donc sans effet.

## Merged

Mergée le 2026-10-04 par `/merge task-351 --i-tested` (squash, ordre dtos-mss → api-mail → client-blazor), CI `develop` verte sur les trois repos.

- `dtos-mss` #42 : `d7917ede`
- `api-mail` #277 : `1a36fcbc`
- `client-blazor` #92 : `4c8cf1a1`
- Branches `chore/task-351-retrait-champs-serveur` supprimées, distantes et locales.
- `client-angular` : code-only. Le commit, le push TFS et la PR restent à la main de l'humain ; le clone local n'est pas touché.
