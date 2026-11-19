# todo-task-489.md — Outillage e2e : relais et faux services sans build parallèle

**Repos**: api-mail
**Dependencies**: —
**Priorité**: bloquant pour la voie e2e mobile — demandé par l'humain le 2026-11-19, après la panne de task-485.

> Constat du 2026-11-19 (task-485, `questions/task-485.md`) : la voie mobile tombe à 12 rouges, deux fois de suite, sans
> rapport avec le code testé. Aucun message envoyé n'arrive (`uidNext` inchangé) et le faux annuaire manque.

## Objectif

Le banc e2e démarre **toujours** ses trois ressources d'outillage — le relais SMTP → IMAP (`e2e-relay`), la fausse IA
(`e2e-fake-ai`) et le faux annuaire (`e2e-fake-annuaire`) — quel que soit l'état des fichiers de build. Une voie qui
rougit le fait pour une raison du code testé, jamais parce qu'une ressource d'outillage n'a pas démarré.

### Ce qui est établi

- `Api/Mail/src/AppHost/AppHost.cs` déclare les trois ressources par `AddProject(…/tests/mss.mail.e2e/mss.mail.e2e.csproj)`.
  DCP les lance par `dotnet run --project … --configuration Debug --no-launch-profile …`, **sans `--no-build`**, en
  parallèle.
- Les trois builds se gênent : `MSB3027 Could not copy obj/Debug/net10.0/apphost.exe to bin/…` (exécutable verrouillé
  par la première ressource lancée) ou « Error writing to source link file ». Journaux `*_err` de DCP
  (`%TEMP%/aspire-dcp*`) : « The build failed ». Une seule ressource tourne ensuite.
- L'orchestrateur `Client/Mobile/e2e/headless/run.mjs` construit **déjà** l'outillage avant l'AppHost
  (`dotnet build tests/mss.mail.e2e`) et lance l'AppHost en `--no-build` : seules les trois ressources rebuildent.
- Le relais lancé à la main (`dotnet tests/mss.mail.e2e/bin/Debug/net10.0/mss.mail.e2e.dll relay …`) relaie aussitôt.

### Règles

1. Les trois ressources lancent l'outillage **déjà construit** (la DLL de `bin/Debug/net10.0`), sans build : par
   `AddExecutable("dotnet", …, "<dll>", "<sous-commande>", …)`, ou tout autre moyen qui exclut un build concurrent.
2. Leurs arguments, ports et dépendances (`WaitFor` Dovecot, GreenMail) ne changent pas.
3. Si la DLL manque (outillage non construit), l'AppHost le dit clairement au démarrage du profil e2e au lieu de lancer
   une ressource qui échoue en silence.

### Hors périmètre

- Le contenu des scénarios et le catalogue.
- Le profil de charge (`loadtest`) et les autres profils de l'AppHost.

## Definition of Done

- [ ] Build passes (`dotnet build HealthPlatform.Api.Mail.sln`, 0 erreur).
- [ ] Tests pass (`dotnet test HealthPlatform.Api.Mail.sln`, 0 échec).
- [ ] Les trois ressources `e2e-relay`, `e2e-fake-ai`, `e2e-fake-annuaire` ne passent plus par `dotnet run` : aucun build
      au démarrage de l'AppHost e2e (vérifié dans les journaux DCP : aucun « Build », aucun `*_err` « build failed »).
- [ ] Au banc `--serve-only` : trois processus `mss.mail.e2e.exe` (ou `dotnet … mss.mail.e2e.dll`) tournent, `relay`,
      `fake-ai`, `fake-annuaire`.
- [ ] Voie e2e mobile **verte deux fois de suite** (`npm run e2e:headless`), dont E2E-COMPOSE-001 et E2E-MAILBOX-003 ;
      preuve rouge : la même voie rouge sur le code d'avant (12 rouges du 2026-11-19), consignée au `## Develop log`.
- [ ] DLL absente → message explicite au démarrage du profil e2e (test ou démonstration consignée).
- [ ] `conventions/e2e.md`, entrée `relais-non-demarre-build-concurrent` : « Correctif de fond à faire » remplacé par
      le correctif livré.

## Manual Test Plan

1. `cd Client/Mobile && npm run e2e:headless -- --serve-only`.
2. Vérifier que trois processus d'outillage tournent : relais, fausse IA, faux annuaire.
3. Dans l'app mobile servie (port 8100), écrire à « robert » (le praticien lui-même) : le message arrive dans la boîte.
4. Arrêter le banc (`e2e/headless/out/STOP`) : démontage complet.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — outillage de test, sans effet pour le médecin
- **Vague Ségur** : hors Ségur — outillage de test
- **Exigences DSR honorées** : non applicable — outillage de test
- **INS** : non applicable — aucune donnée patient
- **Authentification PS** : non applicable — banc e2e (identités de test)
- **Habilitations** : non applicable — banc e2e
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : non applicable — aucun acte médecin
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — banc local, données synthétiques
- **AIPD / impact RGPD** : inchangé — aucune donnée réelle

## Branches
- `api-mail` (pushed) : feat/task-489-outillage-e2e-relais-et-faux-services — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-489-outillage-e2e-relais-et-faux-services

## Timings

*(généré par `tools/timing/report.sh --task task-489 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 20 s | — | — | — | — |
| /develop | ok | 41 min 15 s | 2 (14 s) | 4 (34 min 33 s) | — | api-mail 2B/2T, client-mobile 0B/2T |
| /review-code | ok | 1 min 58 s | — | — | — | — |
| /sonar | ok | 11 min 41 s | 1 (50 s) | 5 (8 min 35 s) | 2 (48 s) | 1 itération(s), api-mail 1B/5T |
| /lint-angular | skipped | 4.8 s | — | — | — | client-angular non touché |
| /lint-mobile | skipped | 1.0 s | — | — | — | client-mobile non touché |
| /e2e | ok | 28 min 26 s | — | — | — | e2e ×3 (27 min 00 s) |
| /review | ok | 38 s | — | — | — | — |
| **Total cycle** | | **1 h 24 min** | **3 (1 min 05 s)** | **9 (43 min 09 s)** | **2 (48 s)** | |

## Develop log

- Repos touched : api-mail
- DTOs published : no DTO change
- Interop published : no interop change
- api-mcp : aucun impact (`mcp_impact.py check`, sortie 0)
- Commits :
  - api-mail : abca6aec fix(e2e): lancer l'outillage e2e déjà construit, sans build concurrent (task-489)
- Correctif : `E2eProfile.Tools` déclare les trois ressources (`e2e-relay`, `e2e-fake-ai`, `e2e-fake-annuaire`), avec
  leurs arguments, ports et attentes inchangés. Seul le relais attend Dovecot et GreenMail. `E2eProfile.ResolveTooling`
  résout `tests/mss.mail.e2e/bin/Debug/net10.0/mss.mail.e2e.dll` depuis `builder.AppHostDirectory` et refuse de démarrer
  si elle manque. L'AppHost lance chaque ressource par `AddExecutable("dotnet", <projet>, <dll>, <sous-commande>…)` :
  plus aucun `dotnet run`. Le profil `loadtest` (`loadtest-fake-openai`, une seule ressource) est hors périmètre et inchangé.
- Tests unitaires (`E2eProfileTests`, +6) et preuves par mutation (chaque mutation fait échouer le test prévu, puis
  restauration et recompilation) :
  - M1, pas de refus quand la DLL manque → rouge `ResolveTooling_DllMissing_RefusesToStartAndSaysWhatToBuild` ;
  - M2, retour à `run --project <dll>` → rouge `CommandFor_RunsTheBuiltDll_NeverDotnetRun` ;
  - M3, port du relais remplacé par celui de la fausse IA → rouge `Tools_AreTheRelayTheFakeAiAndTheFakeAnnuaire_WithUnchangedArguments` ;
  - M4, la fausse IA attend les serveurs mail → rouge `Tools_OnlyTheRelayWaitsForTheMailServers` ;
  - M5, DLL cherchée en Release → rouge `ResolveTooling_DllBuilt_PointsAtTheBuiltDllOfTheToolingProject` et
    `ToolingDllDisplayPath_IsTheResolvedDllRelativeToTheRepository`.
- Règle 1b : sans objet. Aucun comportement atteignable par un endpoint ne change, seul l'outillage de test de l'AppHost
  change. La preuve d'intégration de ce changement, c'est le banc e2e réel (ci-dessous).
- Banc `--serve-only` (2026-11-19, 08:09) :
  - trois processus `dotnet …\mss.mail.e2e.dll` tournent : `fake-ai --port 11534 --tagging-delay-ms 5000`,
    `fake-annuaire --port 11535`, `relay --sink-port 3143 --password loadtest` ;
  - sorties DCP (`%TEMP%/aspire-dcpt0c52jh1.p3x`) : aucune trace de build (`Build`, `MSB3027`, « build failed »),
    les neuf `*_err` sont vides. Le relais affiche « actif pour 1 boîte(s) » 3 s après le démarrage, le faux annuaire et
    la fausse IA écoutent dès le lancement ;
  - démontage complet par `out/STOP` en 2 s.
- Voie e2e mobile (`npm run e2e:headless`), **verte deux fois de suite** :
  - passage 1 : 75 verts, 1 flaky, 0 rouge, parité verte. Le flaky est E2E-CONV-003 (« les deux messages forment un
    fil », rouge au 1er essai puis vert au retry). Il est sans rapport avec l'outillage : entrée `fil-depose-a-la-seconde`
    de `conventions/e2e.md`, passée à 3 occurrences ;
  - passage 2 : 76 verts, 0 flaky, 0 rouge, parité verte ;
  - E2E-COMPOSE-001 (envoyer à « robert », recevoir) et E2E-MAILBOX-003 (« Mes boîtes », faux annuaire) verts aux
    deux passages.
- Preuve rouge sur le code d'avant : la même voie à 12 rouges, deux fois de suite, le 2026-11-19 (task-485,
  `questions/task-485.md`). Les 12 rouges sont tous des parcours qui attendent un envoi relayé ou l'annuaire. Seul
  `fake-ai` tournait, et deux `_err` DCP portaient « The build failed ».
- DLL absente → refus explicite au démarrage du profil e2e, prouvé par `ResolveTooling_DllMissing_RefusesToStartAndSaysWhatToBuild`
  (le message cite `tests/mss.mail.e2e/bin/Debug/net10.0/mss.mail.e2e.dll` et `dotnet build tests/mss.mail.e2e`).
- `conventions/e2e.md`, `relais-non-demarre-build-concurrent` : « Correctif de fond à faire » est remplacé par le correctif
  livré, avec une consigne pour toute nouvelle ressource d'outillage.
- Local build / test : ✓ api-mail. Build à 0 erreur et 0 avertissement. Suite complète à 0 échec : domain 368,
  infrastructure 749, application 4 346, api 1 388, integration 1 369 (+16 sautés).
- Passe qualité (/simplify) :
  - No change : api-mail. Le diff est déjà minimal, une seule déclaration des trois ressources.
  - Contrôles mécaniques §Q 2b : 1 hit S125 (« … ; … » dans un commentaire de l'AppHost), réécrit avant le commit.
    Compteur incrémenté dans `conventions/csharp.md` (30).
  - Skipped (contract/excluded) : dtos-mss, interop-cda, sdk non touchés.
- DOD self-check : 7/7 vérifiés (build, tests, aucun `dotnet run` ni build au démarrage, trois processus au banc,
  deux voies vertes avec la preuve rouge, refus explicite, convention mise à jour).
- Green marked : api-mail (`Tools/green/green.py`, abca6aec)
- Next step : /review task-489 --code

## Code Review Summary

### Passage 1 (revue anticipée) — APPROVED

- **approved at** : api-mail `abca6aec`
- Relecteur indépendant (sous-agent, code seul) : 3 fichiers relus, 0 bloquant, 4 suggestions.
- **Règle 1b (4a)** : sans objet. Aucun comportement atteignable par un endpoint ne change : le diff ne touche que
  l'AppHost (profil e2e) et ses tests unitaires. La preuve d'assemblage est le banc réel, consignée au `## Develop log` :
  trois processus `dotnet <dll>`, sorties DCP sans build, deux voies mobiles vertes, contre 12 rouges avant (task-485).
- **api-mcp (4c)** : aucun impact (`mcp_impact.py check`, sortie 0).
- **Clause DOD e2e (4b)** : aucun parcours médecin créé ni modifié, aucun scénario au catalogue attendu.

| Fichier | Verdict |
|---|---|
| `src/AppHost/AppHost.cs` | ✅ `AddExecutable("dotnet", <projet>, <dll>, …)` : aucun build. Seul le relais attend Dovecot et GreenMail. Le répertoire de travail est le projet, comme sous `AddProject`. Refus levé avant `builder.Build()`. Ce que `AddProject` ajoutait (OTEL, service discovery, profil de lancement) n'est pas utilisé par l'outillage, dont les serveurs se lient par `UseUrls`. |
| `src/AppHost/E2eProfile.cs` | ✅ Arguments identiques à ceux d'avant (invariant culture). Le message de refus ne porte que le chemin relatif au dépôt. Tableaux hissés (CA1861). |
| `tests/mss.mail.api.tests/E2e/E2eProfileTests.cs` | ✅ avec suggestions |

#### Suggestions (non bloquantes)

- ⚠️ **DLL périmée** : `dotnet run` reconstruisait un outillage modifié. Lancé à la main sans `dotnet build
  tests/mss.mail.e2e`, l'AppHost lance désormais l'ancienne DLL. Le script `e2e:headless` construit toujours avant,
  donc c'est hors règle 3. Une phrase dans le commentaire de `ToolingDllDisplayPath` suffirait.
- ⚠️ **Câblage non couvert par un test** : la règle 1 (« `AddExecutable`, pas `AddProject` ») vit dans la boucle de
  l'AppHost, qu'aucun test unitaire ne couvre, faute de référence Aspire au projet de tests. Remettre `AddProject`
  laisserait les tests verts. La preuve de la règle 1, c'est le banc (processus + sorties DCP), pas
  `CommandFor_RunsTheBuiltDll_NeverDotnetRun`.
- ⚠️ **Argument de `fileExists` non contrôlé** : les stubs `_ => true` / `_ => false` ignorent le chemin testé.
  Capturer l'argument et l'égaler à `tooling.Dll` fermerait l'écart entre le chemin testé et le chemin rendu.
- ⚠️ **S125 dans un `///`** : « …avant l'AppHost ; la ressource tourne… » (doc XML d'un test). Sonar ignore
  d'ordinaire les commentaires XML, mais la consigne vise toute ligne de commentaire. `/sonar` le dira s'il le relève.

## Sonar log

- Mode A (chaîné), branche `feat/task-489-…`. Analyse complète, parce que le diff touche un fichier C# analysé
  (`tests/mss.mail.api.tests/E2e/E2eProfileTests.cs`). `src/AppHost/**` est exclu de l'analyse.
- Serveur 9.9.8.100196 (`sonar.login`). Build Release à 0 erreur, 5 suites OpenCover vertes (domain 368,
  application 4 346, infrastructure 749, api 1 388, integration 1 369 + 16 sautés).
- Phase 1 (new code) : ✓ Quality Gate OK, new_coverage = 96,0 %.
- Phase 1 — 1 issue, **hors du diff de la task** : `csharpsquid:S3925` sur `src/Application/Exceptions/ForbiddenException.cs`
  (task-457, déjà sur `develop`). Le triplet de constructeurs est présent : marquée **FALSE-POSITIVE** avec motif
  (faux positif consigné, `conventions/csharp.md` S3925, compteur 10). Aucun code modifié.
- Phase 1 — tests ajoutés : 0. Aucune issue sur les fichiers de la task.
- Phase 2 (legacy) : non jouée. Les cibles projet sont déjà atteintes (0 bug, 0 vulnérabilité, maintenabilité A,
  couverture 97,6 % ≥ 95 %).
- Build / tests : ✓ verts. Vert marqué (`green.py`, par sonar, abca6aec).

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 96,2 % | 96,0 % | −0,2 pt |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 0 | 1 → 0 après FALSE-POSITIVE (S3925, hors task) | 0 |
| Coverage (projet) | 97,7 % | 97,6 % | −0,1 pt |
| Duplication | 0,3 % | 0,3 % | 0 |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

> La couverture bouge de −0,1 pt sans rapport avec la task : `src/AppHost/**` et `tests/**` sont exclus de la couverture.
> L'écart vient de la période de new code, qui inclut ce que `develop` a reçu depuis la référence (task-457).

## Lint log
- skipped — no angular change (client-angular hors **Repos**, arbre `Client/Angular/front` propre)

## Lint mobile log
- skipped — no mobile change (client-mobile hors **Repos**, arbre `Client/Mobile` propre sur `develop`)

## E2E log

> ⚠️ **Quarantaine de plus de 14 jours** : E2E-COMPOSE-002 (Angular) est en quarantaine depuis le 2026-10-09 (41 jours).
> Sa task de correction, task-350, est archivée, mais la quarantaine est toujours posée. Le test est passé au vert
> sur ce run. **Décision humaine** : lever la quarantaine, ou ouvrir la task de correction qui manque.

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail touché | ✅ verte (jouée) | 76 verts, 0 flaky, 0 rouge | 13 min 26 s |
| angular | api-mail touché | ✅ verte (jouée) | 97 verts, 1 flaky (E2E-SEARCH-004), 0 rouge, 1 quarantaine | 13 min 35 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task (`abca6aec`), inchangé par la task
- Client mobile aligné sur `origin/develop` avant la voie (déjà à jour). Angular : branche de l'humain
  `feature/nova-mss-weda-integration`, arbre propre.
- Quarantaines : E2E-COMPOSE-002 [angular], task-350, posée le 2026-10-09 (passée au vert sur ce run)
- Divergences ouvertes : 9 (E2E-SEARCH-001/004/005/006/007/009 → task-450 ; E2E-SEARCH-008/010/012 → task-451)
- Flaky : E2E-SEARCH-004 [angular], 1re occurrence au registre (`GET …/folders/INBOX` → 500 au 1er essai)
- Parcours touchés sans spec e2e modifié : aucun (la task ne touche aucun écran)
- Démontage : complet. Ports 5052/8100/4200/3993/3465/3143 libres, aucun conteneur e2e créé par le run.
  Deux résidus anciens, `e2e-greenmail-gcgjbrzp` et `e2e-dovecot-kgrndjwd`, sont arrêtés depuis le
  2026-10-14 et n'ont pas été touchés.
- Outillage de la task vérifié en voie : le relais, la fausse IA et le faux annuaire ont tourné en `dotnet <dll>`.
  E2E-COMPOSE-001, E2E-LIVE-001 et E2E-MAILBOX-003/004/006 sont verts sur les deux voies.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**Flaky (vert au second essai, non bloquant)** (1) :

- [angular] « recherche — un nom de patient sans accent trouve ses messages, puis les messages partiels » (E2E-SEARCH-004)

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
| E2E-BIO-004 | 1 | headless | Un compte rendu acquitté puis déplacé depuis un autre client garde son acquittement | ✅ | ✅ |
| E2E-BIO-007 | 1 | headless | Un compte rendu arrivé avant la date de début du suivi ne réclame rien, et s'acquitte quand même | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-DETAIL-006 | 1 | headless | Après une réponse, le message d'origine dit « Vous avez répondu à ce message le… » | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SETTINGS-004 | 1 | headless | Paramètres indisponibles : rien n'est écrasé | ✅ | — |
| E2E-SEARCH-001 | 2 | headless | Composer ses critères puis lancer la recherche | ✅ | ✅ (v1) · divergence (task-450) |
| E2E-SEARCH-002 | 1 | headless | Un mot rare et accentué trouve le message qui le contient | ✅ | ✅ |
| E2E-SEARCH-003 | 1 | headless | Un numéro de dossier trouve son message, et un seul | ✅ | ✅ |
| E2E-SEARCH-004 | 1 | headless | Un nom de patient tapé sans accent ni majuscule trouve ses messages, puis les messages partiels | ⚠️ flaky | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-005 | 1 | headless | Un mot absent de la boîte affiche « Aucun résultat » | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-006 | 1 | headless | Plus de résultats qu'une page — « Voir plus » affiche la suite, jusqu'au dernier | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-007 | 1 | headless | Une recherche en échec affiche un message, et l'ancienne liste n'est plus affichée | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-009 | 1 | headless | Fermer la recherche rend le dossier à la même position ; retirer une étiquette relance sans elle | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-010 | 1 | headless | Reconnaître un résultat et ouvrir le dossier du patient | ✅ | ⛔ non joué · divergence (task-451) |
| E2E-SEARCH-012 | 1 | headless | Traiter tous les résultats d'une recherche | ✅ | ⛔ non joué · divergence (task-451) |
| E2E-SEARCH-015 | 1 | headless | Le détail surligne ce qui a été cherché | ✅ | — |
| E2E-SEARCH-008 | 1 | headless | Restreindre la recherche à un patient et à ses biologies anormales | ✅ | ⛔ non joué · divergence (task-451) |
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
| E2E-TAG-001 | 1 | headless | Choisir un tag de la boîte dans la liste, créer un tag de plusieurs mots | ✅ | ✅ |
| E2E-TAG-002 | 2 | headless | Les tags système classent la Boîte de réception : Biologie, Patient, Pour info | ✅ | ✅ |
| E2E-TAG-003 | 1 | headless | Combiner deux tags et retrouver le filtre « Non lus » | ✅ | ✅ |
| E2E-TRIAGE-001 | 1 | headless | Traiter un message le retire de « À traiter », le compteur baisse, « Annuler » le remet | ✅ | ✅ |
| E2E-TRIAGE-002 | 1 | headless | Traiter les messages affichés laisse le compte rendu de biologie à acquitter | ✅ | ✅ |
| E2E-TRIAGE-006 | 1 | headless | Dans la vue « Biologie », « Traiter les résultats sans anomalie » laisse le résultat anormal à traiter | ✅ | ✅ |
| E2E-TRIAGE-007 | 1 | headless | Répondre à un message le fait sortir de « À traiter », libellé « — répondu » | ✅ | ✅ |
| E2E-SHARED-003 | 1 | headless | Le délégataire traite un message, le titulaire le voit traité « par » le délégataire | ✅ | ✅ |
| E2E-ASSIGN-001 | 1 | headless | Le titulaire attribue un message à la secrétaire délégataire, qui le trouve dans « Pour moi » | ✅ | ✅ |
| E2E-ASSIGN-002 | 1 | headless | Traiter un message attribué le retire de « Pour moi », et le détail dit « traité par » | ✅ | ✅ |
| E2E-CONV-001 | 1 | headless | Lire un fil en vue chat et y répondre en une ligne, à tous les participants | ✅ | ✅ |
| E2E-CONV-002 | 1 | headless | Joindre un fichier depuis la vue chat | ✅ | ✅ |
| E2E-CONV-003 | 1 | headless | La vue chat s'ouvre d'elle-même sur un fil engagé, et n'existe qu'en mode Conversation | ✅ | ✅ |

**Divergences temporaires ouvertes** (9) :

- E2E-SEARCH-001 [mobile] — le mobile adopte le formulaire à un seul niveau avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-004 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-005 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-006 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-007 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-009 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-010 [mobile] — la lecture enrichie arrive sur le mobile avec la refonte mobile — résorbée par task-451
- E2E-SEARCH-012 [mobile] — la sélection de tous les résultats arrive sur le mobile avec la refonte mobile — résorbée par task-451
- E2E-SEARCH-008 [mobile] — les critères médicaux arrivent sur le mobile avec la refonte mobile — résorbée par task-451

**Parité : verte** — aucun écart entre le catalogue et les suites.

### Passage 2 (validation finale) — APPROVED

- Build + tests : vert de /sonar réutilisé (api-mail `abca6aec`, `green.py check`). Aucun commit depuis l'approbation,
  donc aucun diff à relire.
- DOD : 7/7. Build, tests, `AddExecutable` sans `dotnet run`, trois processus au banc, voies vertes avec la preuve
  rouge, refus explicite (`ResolveTooling_DllMissing_RefusesToStartAndSaysWhatToBuild`), convention mise à jour.
- Verrou e2e : `## E2E log` vert (mobile 76/76, Angular 97 verts dont 1 flaky, porte verte).
- api-mcp : aucun impact. Sync `develop` : aucun commit en avance, pas de merge.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/377 — label `awaiting-human-merge`
