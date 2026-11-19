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
