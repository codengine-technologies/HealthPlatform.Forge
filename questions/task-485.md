> **Résolu** le 2026-11-19 : bypass e2e de task-485, décision humaine. Le correctif de l'AppHost reste à faire (task à ouvrir).

# task-485 — /e2e bloqué : panne d'outillage (relais e2e qui ne démarre pas)

**Nature : outillage**, pas régression ni parité. task-485 ne touche ni le mobile ni le code serveur (catalogue seul).

## Constat

- Voie **angular** : verte, 98/98, **E2E-SEARCH-015 vert** (le scénario de la task).
- Voie **mobile** : 12 rouges, deux passages identiques. Tous attendent l'**arrivée** d'un message envoyé
  (E2E-COMPOSE-001/002/003, DRAFT-002, DETAIL-001, RECEIPT-001/002, SHARED-002, CONV-003) ou le **faux annuaire**
  (E2E-MAILBOX-003/004/006).
- `POST /sendmail` répond 200 (`queued: false`), mais `GET folders/INBOX` garde `uidNext` : le message n'arrive jamais.

## Cause (prouvée)

L'AppHost e2e lance trois ressources depuis le même projet d'outillage (`e2e-relay`, `e2e-fake-ai`,
`e2e-fake-annuaire`, `AddProject(…/tests/mss.mail.e2e/mss.mail.e2e.csproj)`), chacune par `dotnet run --project …`
**sans `--no-build`**, en parallèle. Les trois builds se gênent : `MSB3027 Could not copy obj/Debug/net10.0/apphost.exe
to bin/…` (fichier verrouillé par la première ressource lancée), ou « Error writing to source link file ». Seule une
ressource démarre : au 1er passage `fake-ai`, au 2nd `fake-annuaire`. Sans `e2e-relay`, aucun envoi n'arrive.

Preuves : journaux `*_err` de DCP (`%TEMP%/aspire-dcp*`, « The build failed ») ; processus `mss.mail.e2e.exe` réduits à
un seul ; `relay` lancé à la main relaie aussitôt le message bloqué (« 1 message(s) relayé(s) »).

L'orchestrateur `e2e:headless` construit déjà l'outillage avant l'AppHost (`dotnet build tests/mss.mail.e2e`) et lance
l'AppHost en `--no-build` : seules les trois ressources rebuildent.

## Décision demandée

Le correctif touche `Api/Mail/src/AppHost/AppHost.cs`, hors du périmètre de task-485 (règle 6).

1. **Recommandé** : correctif d'outillage dans **une task courte séparée** — lancer l'outillage déjà construit
   (`AddExecutable("e2e-relay", "dotnet", …, "<bin>/mss.mail.e2e.dll", "relay", …)` pour les trois ressources), prouvé
   par une voie mobile verte. Puis rejouer `/e2e task-485` et poursuivre la chaîne.
2. L'inclure dans task-485 (branche api-mail déjà ouverte) : même correctif, la PR api-mail porte alors le catalogue
   **et** l'AppHost e2e.
3. Bypass e2e de task-485 (`**E2E**: bypass — décision humaine du …`) : la voie angular, la seule qui joue le parcours
   de la task, est verte ; la non-régression mobile ne serait pas prouvée.

Prévention déjà écrite : `conventions/e2e.md`, entrée `relais-non-demarre-build-concurrent`.
