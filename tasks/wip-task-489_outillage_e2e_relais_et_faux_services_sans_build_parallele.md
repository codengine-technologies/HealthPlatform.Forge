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
| **Total cycle** | | **55 min 22 s** | **3 (1 min 05 s)** | **9 (43 min 09 s)** | **2 (48 s)** | |

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
