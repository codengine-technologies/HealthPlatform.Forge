# E018 — Changelogs (vue ingénierie)

> **Audience** : équipes techniques, backlog, dette.
> Vue produit : [E018-filet-de-non-regression-fonctionnel.md](E018-filet-de-non-regression-fonctionnel.md).
> **Dernière mise à jour** : 2026-09-29 (v1.0)

---

## Historique détaillé des changelogs

### v1.0 — Filet e2e headless client-mobile, backend e2e et catalogue de scénarios — task-345

- **Task** : task-345, statut `done`.
- **PRs** : `api-mail` #259 et `client-mobile` #81, label `awaiting-human-merge`, branche
  `feat/task-345-filet-e2e-headless-mobile`.
- **Backend e2e (api-mail)** :
  - Profil AppHost `https-e2e` (`MSS_E2E=true`), résolu par `src/AppHost/E2eProfile.cs`.
  - La clé `MSS_E2E_BYPASS_KEY` est obligatoire et n'a aucune valeur par défaut.
  - Le profil est exclusif du profil `MSS_LOADTEST` et utilise le registre dédié `mss_registry_e2e`.
  - Dovecot et GreenMail sont factorisés avec le banc de charge (`AddBenchDovecot` / `AddBenchGreenMail`), sans volume.
  - Relais SMTP→IMAP `e2e-relay`, déclaré par chemin : les autres profils ne compilent pas l'outillage.
  - `MSS_E2E_PASSWORD` retiré, car la passdb statique de Dovecot ne suivait pas une surcharge.
- **Outillage `tests/mss.mail.e2e`** : sous-commandes `reset`, `seed`, `relay` et `parity`.
  - Codes retour : 0 succès, 1 échec vérifié, 2 outillage ou interruption.
  - Seed déterministe (`E2eSeedPlan`) : 7 messages, dont le CR de biologie TSH du corpus ANS, un dossier Archive et un contact.
  - Le seed relit tout ce qu'il écrit : boîte sélectionnable, CR servi par la base avec son document CDA.
  - Le seed liste les dossiers avant l'enrichissement, pour contourner la génération UIDVALIDITY 0 d'`AddNewMail` (même remède que la chauffe du banc, `f209ce8`).
- **Catalogue** : `Api/Mail/e2e/scenarios.yml` contient 25 scénarios `E2E-{DOMAINE}-{NNN}`, requis pour `mobile` et `angular`.
  - 3 scénarios sont en `mode: humain` : CONTACT-001, AUTH-001 et AUTH-002.
  - Le chargement est strict. Depuis la 2e review, il refuse aussi un scénario muet sur un client du catalogue.
  - Le contrôle de parité confronte ce catalogue au rapport Playwright **exécuté** et produit une matrice Markdown.
- **Client-mobile** : la commande `npm run e2e:headless` lance l'orchestrateur `e2e/headless/run.mjs`, qui enchaîne :
  pré-vol → build → `ng serve` (proxy e2e) → reset → AppHost → seed → Playwright → parité → démontage.
  - Le projet Playwright `headless` utilise le canal `chrome`, sans vidéo, avec 1 retry (un flaky reste visible).
  - La session est simulée dans le stockage du navigateur. Les en-têtes du bypass ne visent que l'origine de l'app.
  - Aucune occurrence du bypass sous `src/`.
- **Défauts produit corrigés** (test rouge d'abord) :
  - `EmailBuildingService.MapHeaderFields` pose maintenant `AttachmentCount`, ce qui rétablit le badge trombone sur la liste servie par IMAP.
  - La page inbox ferme le menu des dossiers après un choix.
- **Reviews** : 2 CHANGES REQUESTED, puis APPROVED au 3e passage.
  - Démontage : il ne retire que les conteneurs apparus pendant le run, et échoue fermé si `docker ps -a` échoue.
  - Signaux gérés : SIGTERM, SIGHUP et SIGBREAK.
  - 15 parcours durcis. Lu, flag et acquittement bio sont désormais relus du serveur, car l'UI est optimiste.
- **Preuve par mutation** : 12 no-ops plantés dans `MssApiService` font échouer exactement les 10 parcours visés.
  - Les no-ops portent sur les suppressions (contact, signature, groupe, dossier, mail, brouillon), l'acquittement et les statuts lu/non-lu/flag.
  - Ensuite, **22/22 verts deux fois de suite**, 0 flaky, parité verte, environ 3 min par run.
  - `docker ps -a` est identique avant et après chacun des 7 runs.
- **Tests** : api-mail 5 849 verts (16 ignorés préexistants), client-mobile 947/947.
- **Sonar** : Quality Gate OK, new_coverage 98,3 %, 0 finding sur les lignes de la branche (1 CA1859 corrigé).
- **Limites et constats routés au PO** :
  - `MailPendingDeleteService` ne vide pas sa file au déchargement de la page : une suppression est perdue si l'app est rechargée dans les 6 s.
  - `AddNewMail` estampille la génération 0 sans le signaler.
  - `AttachmentCount` n'est pas posé par `BackgroundEnrichmentProcessor.cs:314` ni `MailRepository.cs:3295`.
  - `SentDate` utilise `LocalDateTime` (famille AUD-28).
  - « Aucun contenu disponible » s'affiche pendant le chargement du détail.
  - DOD « run vert réseau Internet coupé » reportée au test humain.

---

## Annexe A — Cartographie des briques applicatives

| Brique | Emplacement | Rôle |
|---|---|---|
| Profil AppHost e2e | `Api/Mail/src/AppHost/E2eProfile.cs`, `AppHost.cs` | Backend du filet (Dovecot, GreenMail, relais, registre dédié, clé de bypass) |
| Outillage e2e | `Api/Mail/tests/mss.mail.e2e/` | Reset, seed, relais, contrôle de parité |
| Plan de seed | `Api/Mail/tests/mss.mail.testing.shared/E2eSeedPlan.cs` | Jeu de données déterministe, partagé seed et tests |
| Catalogue | `Api/Mail/e2e/scenarios.yml`, `Api/Mail/e2e/README.md` | Référence commune des scénarios |
| Orchestrateur | `Client/Mobile/e2e/headless/run.mjs` | Run headless de bout en bout, démontage |
| Suite mobile | `Client/Mobile/e2e/specs/functional.spec.ts`, `e2e/support/*` | Parcours taggés `@E2E-…` + annotation `version` |

---

## Annexe B — Inventaire fonctionnel (2026-09-29)

- Scénarios au catalogue : 25, dont 22 headless et 3 humains.
- Suite mobile headless : 22 tests joués, 22 verts.
- Tests unitaires de l'outillage e2e (api-mail) : 53.

---

## Annexe C — Tasks ayant contribué à cet EPIC

| Task | Statut | Contribution | RGs |
|---|---|---|---|
| task-345 | done (PRs en attente de merge) | Backend e2e, outillage, catalogue, filet mobile headless | RG-E018-01, 02, 03 (mobile), 04 |
| task-346 | todo | Filet web (Angular) sur le même backend et le même catalogue | RG-E018-03 (web) |
| task-347 | todo | Étape `/e2e` bloquante dans la chaîne, clause de DOD | — |
