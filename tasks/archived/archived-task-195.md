# todo-task-195.md — Banc de charge d'envergure : serveur IMAP Dovecot (débloque la pipeline CDA/XDM)

**Repos**: api-mail
**Dependencies**: —
**Epic**: E015

> **Référence** : ADR-2026-07-25-B « Tests de charge api-mail sur infrastructure
> mail mockée » (amendement **v1.2** — bascule IMAP GreenMail→Dovecot). Prérequis
> du harnais k6 (task-174, qui dépendra de cette task).

## Objective

Le banc actuel (task-173, GreenMail IMAP+SMTP) charge correctement les
connexions, sessions et le listing de dossiers, mais **ne peut pas exercer la
pipeline de traitement CDA/IHE-XDM** — le cœur de ce qu'un test de charge doit
mesurer. Cause vérifiée empiriquement (trace Seq + issue GreenMail #187) :
GreenMail répond mal au **fetch partiel `BODY[part]`**, donc le téléchargement de
la pièce jointe `IHE_XDM.ZIP` par MailKit (`GetBodyPartAsync`) échoue avec
`System.FormatException: Failed to parse entity headers`. L'exception est
attrapée → 0 ZIP → aucun `[CdaParsingService] Parsing completed`,
`hasMedicalDocuments=false`. Ce n'est ni un bug du seed (MIME/BODYSTRUCTURE
vérifiés corrects) ni d'api-mail (le fetch partiel est le comportement de
production voulu) — c'est une limitation de GreenMail.

Cette US remplace le **serveur IMAP** du banc par **Dovecot** (serveur IMAP de
référence, `BODY[part]` conforme → débloque le parsing CDA) et **conserve
GreenMail comme puits SMTP**. Le stockage **maildir sur disque** de Dovecot lève
le plafond de heap qui bornait la volumétrie → **banc de charge d'envergure**
(grands corpus, nombreuses boîtes, mails lourds).

**US backend-only (justification)** : outillage de test pur, aucun frontend ni
contrat impacté. **Aucune modification du binaire api-mail** — tout se joue dans
l'AppHost (orchestration) et l'outil de seed.

### Contenu

1. **AppHost — conteneur Dovecot** (`src/AppHost/AppHost.cs`, profil `loadtest`
   opt-in existant) :
   - remplacer le conteneur IMAP GreenMail par `dovecot/dovecot` (**version
     épinglée**) exposant **IMAPS** ;
   - **auth wildcard** : n'importe quel utilisateur + mot de passe fixe
     (`USER_PASSWORD` / passdb `static`) — reproduit la sémantique « auth
     désactivée » de GreenMail, les N utilisateurs virtuels `loadtest-{n}`
     fonctionnent sans provisioning individuel ;
   - **maildir sur volume disque** (userdb `static` templaté par utilisateur) ;
   - **TLS auto-signé** (consommé par api-mail en `ValidateServerCertificate=false`
     via les `UserSettings` seedés) ;
   - override de conf monté dans `conf.d` si les défauts de l'image ne suffisent
     pas ; épingler la version pour figer la syntaxe (2.3 vs 2.4 divergent).
2. **GreenMail conservé en puits SMTP** : garder le conteneur GreenMail
   uniquement pour le SMTP (scénario `send`), retirer son rôle IMAP.
3. **Toxiproxy** : proxifier l'IMAPS Dovecot (latence) ; SMTP inchangé vers le
   puits GreenMail.
4. **Seed** (`tests/mss.mail.loadtest.seed`) : pointer l'APPEND IMAP sur Dovecot
   (host/port/password par défaut), APPEND MailKit inchangé ; les `UserSettings`
   transitent déjà par Toxiproxy. Adapter les ports/mot de passe par défaut et la
   doc. Conserver l'injection `IHE_XDM.ZIP` (déjà en place) et le read-back.
5. **Volumétrie d'envergure** : documenter/valider un run à gros volume rendu
   possible par le maildir disque (ex. plusieurs centaines de boîtes × centaines
   de mails avec PJ XDM), en surveillant l'espace disque du volume Dovecot.
6. **Documentation** : mettre à jour `docs/loadtest.md` (Dovecot IMAP + GreenMail
   SMTP, lancement, seed, limites disque).

### Hors scope

- Le harnais k6 et les scénarios (task-174).
- Toute modification du binaire api-mail (le fetch partiel de prod reste inchangé).
- `docker-mailserver` (trop lourd — écarté dans l'ADR).

## Definition of Done

- [ ] Build passes (0 errors) — `dotnet build src/AppHost/mss.mail.AppHost.csproj`
      (aucun changement de code de prod attendu)
- [ ] Profil `loadtest` : Dovecot (IMAPS) + GreenMail (SMTP) + Toxiproxy démarrent
      et sont `healthy` ; jamais actif hors `MSS_LOADTEST` / profil `https-load-test`
- [ ] Seed : APPEND vers Dovecot OK, read-back des `UserSettings` OK, sortie en
      erreur bruyante si un utilisateur n'est pas exploitable
- [ ] **Validation end-to-end du parsing CDA** : après seed (mails avec
      `IHE_XDM.ZIP`) + `POST /folders/INBOX/emails/enrich/sync`, les logs Seq
      montrent `[CdaParsingService] Parsing completed` et `hasMedicalDocuments=true`
      sur au moins un mail (preuve que la pipeline s'exécute réellement — c'était
      l'échec bloquant avec GreenMail)
- [ ] Run de volumétrie d'envergure documenté (N boîtes × M mails XDM) sans
      saturation mémoire (maildir disque), avec la charge disque relevée
- [ ] Aucune DSCP : données 100 % synthétiques ; aucun secret/token en clair dans
      les logs du seed
- [ ] `docs/loadtest.md` à jour (Dovecot + puits SMTP GreenMail)

## Manual Test Plan

Prérequis : `MSS_LOADTEST=true dotnet run --project src/AppHost` (ou
`--launch-profile https-load-test`), Postgres métier up.

1. Dashboard Aspire : `loadtest-dovecot` (IMAPS), `loadtest-greenmail` (SMTP) et
   `loadtest-toxiproxy` visibles et healthy.
2. Seed : `dotnet run --project tests/mss.mail.loadtest.seed -- --users 5 --messages 10`
   → APPEND + read-back OK, exit 0.
3. **Parsing CDA** : forger le token bypass, `POST http://localhost:5052/api/v1/mail/folders/INBOX/emails/enrich/sync`
   avec body `[1,2,3]` et les en-têtes `X-Test-Bypass`/`Client-Email`/`Client-Psc-Sub`/`Client-Rpps`/`X-PSC-Token`
   → dans Seq : `[CdaParsingService] Parsing completed`, puis
   `GET .../emails/1` → `hasMedicalDocuments: true`.
4. **Envergure** : seed `--users 200 --messages 200`, vérifier l'absence de
   saturation (Dovecot maildir sur disque) et relever la taille du volume.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — outillage interne de test de performance
- **Vague Ségur** : hors Ségur — aucune exigence DSR concernée
- **Exigences DSR honorées** : non applicable — contribue à la robustesse
  (mesure de charge de la pipeline CDA/MSSanté)
- **INS** : non applicable — données 100 % synthétiques
- **Authentification PS** : contournée sur le banc uniquement (bypass de test,
  hard-block Production) — PSC/e-CPS inchangés ailleurs
- **Habilitations** : non applicable — utilisateurs virtuels fictifs
- **Interop CI-SIS** : le banc exerce le parsing **CDA r2 / IHE-XDM** (volets
  CI-SIS) sur des documents de test synthétiques (`JEUX_TESTS_FULL`) — aucun
  document réel
- **Tracé PGSSI-S** : non applicable au banc ; logs sans token ni clé
- **Consentement patient** : non applicable
- **Référentiels métier** : documents CDA de test (jeux `JEUX_TESTS_FULL`)
- **Hébergement HDS** : non — banc local/CI uniquement, jamais sur un
  environnement HDS ; le maildir Dovecot ne contient que des données de test
- **AIPD / impact RGPD** : inchangé — aucune donnée personnelle réelle

## Branches

- `api-mail` (pushed) : `feat/task-195-loadtest-dovecot-imap` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-195-loadtest-dovecot-imap
- `dtos-mss` (pushed, auto-inclus) : `feat/task-195-loadtest-dovecot-imap` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-195-loadtest-dovecot-imap
  (branche créée proactivement par convention ; aucun changement de contrat DTO n'est attendu par cette US — elle restera probablement sans commit et sans PR)

Pré-vol `/start` du 2026-07-25 : `api-mail`, `client-blazor`, `client-mobile`,
`dtos-mss`, `sdk`, `interop-cda` tous sur `develop` et propres. `host`
(`Host/Modules`) n'est pas un dépôt git dans ce workspace — rien à vérifier.

## Develop log

- **Repos touchés** : `api-mail` (`dtos-mss` : branche créée par convention, **aucun
  commit** — aucun contrat DTO impacté, comme anticipé).
- **DTOs publiés** : aucun changement de contrat.
- **Interop publié** : aucun changement.
- **Commit** : `api-mail` — `803b68d` *feat(loadtest): bascule l'IMAP du banc de
  GreenMail vers Dovecot (task-195)* (6 fichiers, +550/−74), poussé.

### Prémisse vérifiée avant la bascule (RED)

La prémisse de l'US a été **reproduite indépendamment**, pas prise sur parole : une
sonde jetable exécutant l'appel de production exact
(`IMailFolder.GetBodyPartAsync`) sur une PJ `IHE_XDM.ZIP` appendue dans GreenMail
échoue avec

```
System.FormatException : Failed to parse entity headers.
   at MimeKit.MimeParser.ParseEntityAsync(...)
   at MailKit.Net.Imap.ImapFolder.GetBodyPartAsync(UniqueId uid, String partSpecifier, ...)
```

La **même** assertion passe contre Dovecot. La sonde a ensuite été retirée ; c'est
`DovecotBenchSmokeTests.PartialFetch_OfIheXdmAttachment_ReturnsExactBytes` qui
porte durablement la vérification.

### Décisions d'implémentation

1. **Configuration montée, pas recopiée** — `DovecotBenchSmokeTests` bind-mount
   `src/AppHost/dovecot/dovecot.conf`, la configuration *réellement* utilisée par
   l'AppHost (résolue en remontant jusqu'à la solution). Une régression de conf
   casse donc le test, au lieu de diverger en silence d'une copie de test.
2. **Un seul fichier monté**, pas le répertoire `/etc/dovecot` : les `cert.pem` /
   `key.pem` auto-signés de l'image restent en place et sont réutilisés tels quels.
   L'image invite elle-même à remplacer ce fichier.
3. **`TestMode__Password` ajouté à l'AppHost — trouvaille non prévue par l'US.**
   GreenMail tournait en `greenmail.auth.disabled` : le mot de passe n'était jamais
   vérifié, et le banc n'en configurait donc aucun côté api-mail
   (`TestMode:Password` était absent partout). La `passdb` statique de Dovecot le
   **vérifie** : sans ce réglage, toute connexion IMAP du banc aurait échoué à
   l'authentification. Contrat désormais explicite en trois points alignés
   (`dovecot.conf`, `TestMode__Password`, `LoadTestPlanGenerator.DefaultPassword`),
   documenté et couvert par un test de rejet de mauvais mot de passe.
4. **Port hôte 3993 conservé** (conteneur 993) pour ne pas déplacer la surface du
   banc ni la documentation existante.
5. **Volume nommé** `loadtest-dovecot-mail` plutôt qu'anonyme : l'occupation
   disque devient mesurable (`docker volume inspect`), ce que le DOD demande. Revers
   documenté : le maildir **persiste**, les seeds successifs s'accumulent.
6. **`GreenMailBenchSmokeTests` conservé** — il garde la couverture SMTP et le
   chemin historique du gestionnaire de sessions ; il utilise son propre conteneur
   et ne référence plus le câblage IMAP du banc.

### Validation

- Build solution : ✓ 0 erreur, 0 avertissement.
- Suite complète : ✓ **3101 réussis, 0 échec**, 16 ignorés (les 3 flaky historiques
  connus sont passés sur ce run).
- `DovecotBenchSmokeTests` : ✓ 3/3 — fetch partiel octet pour octet, auth wildcard
  sans provisioning, rejet d'un mauvais mot de passe, réutilisation de session.

### DOD — état

| Critère | État |
|---|---|
| Build 0 erreur | ✓ vérifié |
| Profil `loadtest` : Dovecot + GreenMail + Toxiproxy, jamais actif hors opt-in | ✓ code + conf ; démarrage réel → HAG |
| Seed : APPEND Dovecot, read-back, erreur bruyante | ✓ code ; exécution réelle → HAG |
| **Validation end-to-end parsing CDA (Seq)** | ⏳ **déférée au HAG** — voir ci-dessous |
| Run de volumétrie d'envergure | ⏳ déféré au HAG (opération lourde, Manual Test Plan) |
| Aucune DSCP, aucun secret en clair | ✓ données synthétiques ; le test forge ses octets |
| `docs/loadtest.md` à jour | ✓ |

**Pourquoi l'end-to-end est déféré** : `api-mail` exige la base Postgres métier sur
`localhost:5432`, qui n'est **pas** orchestrée par l'AppHost et n'était pas démarrée
sur la machine. Provisionner la base du développeur sortait du périmètre de la task.
Le mécanisme décisif — le fetch partiel qui bloquait la pipeline — est lui
**prouvé automatiquement** contre la configuration réelle du banc ; ce qui reste à
observer est son intégration dans l'application en marche, précisément ce que
décrit le Manual Test Plan.

### Hors repo api-mail

`.claude/skills/loadtest-skill/SKILL.md` mis à jour comme sa section « Évolution du
skill » l'exige (IMAP Dovecot + puits SMTP GreenMail, avertissement #187 retiré,
pipeline CDA déclarée opérationnelle, volumétrie maildir, nouveau piège du mot de
passe vérifié). Fichier du plan de contrôle de la forge — hors PR `api-mail`.

- **Étape suivante** : `/forge-simplify task-195`

## Simplify log

- **Repos passés** : `api-mail` (seul touché et éligible).
- **Appliqué & committé** : `api-mail` — 4 fichiers (`d8b97f0`), poussé.
  - *reuse* : extraction de `BenchImap` (client IMAP tolérant au certificat
    auto-signé, seed de boîte, append avec pièce jointe). `DovecotBenchSmokeTests`
    recréait des gestes déjà présents dans `GreenMailBenchSmokeTests` — exactement
    le « réutiliser avant de créer » du workspace. Les **deux** smoke tests
    consomment désormais le helper.
  - *altitude* : la justification « pourquoi Dovecot remplace GreenMail » était
    recopiée dans trois fichiers. Conservée une fois, dans `docs/loadtest.md` ;
    `AppHost.cs` et le smoke test y renvoient.
  - *simplification / efficacité* : rien de substantiel à reprendre (câblage
    déclaratif de conteneurs, options de seed, assertions de test).
- **Non modifié** : `docs/loadtest.md`, `dovecot.conf`, seed — la passe n'a rien
  trouvé d'applicable.
- **Rollback** : aucun.
- **Skippés (contrat / exclus)** : `dtos-mss` (porteur de contrat, et 0 commit),
  `interop-cda`, `devops`, `psc-proxy-*`.
- **Build / tests** : ✓ verts après la passe — **3101 réussis, 0 échec**,
  16 ignorés, soit exactement les mêmes comptes qu'avant (aucun test perdu dans
  l'extraction, aucun changement de comportement).
- **Étape suivante** : `/sonar task-195` (api-mail touché).

## Sonar log

- **Phase 1 (new code)** : ✓ Quality Gate **OK**, `new_coverage` = 85,3 % (seuil 80),
  `new_violations` = 0, hotspots revus 100 %.
- **Phase 1 — Issues fixées** : 2 (2 code smells, 0 bug, 0 vulnérabilité, 0 hotspot)
  - `xUnit2032` — `DovecotBenchSmokeTests.cs:70` : `Assert.IsType<MimePart>(entity,
    exactMatch: false)` au lieu de `Assert.IsAssignableFrom`. **Introduite par cette
    task** — c'est le seul finding réellement imputable au code frais.
  - `external_roslyn:CA1822` — `IheXdmProcessingServiceTests.cs:80` :
    `ArrangeSingleZip` marqué `static`. **Pré-existante**, mais comptée sur le new
    code par la période `PREVIOUS_VERSION` (donc bloquante pour la porte).
- **Phase 1 — Tests ajoutés** : 0 (`new_coverage` déjà au-dessus du seuil ; le code
  de cette task est sous `tests/**`, exclu de la couverture par configuration).
- **Phase 2 (legacy)** : **skippée — plus rien à corriger** (0 bug, 0 vulnérabilité,
  0 code smell, 0 hotspot à l'échelle du projet). Seul écart aux cibles long terme :
  couverture 85,9 % vs 95 % — campagne de couverture, hors périmètre de cette task
  (relève du `code-coverage-skill`).
- **Itérations** : 2 analyses complètes (build Release + 5 projets de tests avec
  couverture OpenCover + scanner).
- **Build / tests** : ✓ build Release 0 erreur. Suite complète verte **hors
  `MailExportServiceTests.BuildPdfWithoutAttachmentsOmitsAttachmentSection`**, l'un
  des flaky pré-existants documentés du projet : vérifié **vert en isolation**
  (2 exécutions) et **aucun fichier Export dans le diff** de la task.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | **ERROR** | **OK** | ✓ redressé |
| New coverage | 73,1 % | 85,3 % | +12,2 pt |
| New violations | 1 | **0** | −1 |
| Bugs | 0 | 0 | = |
| Vulnerabilities | 0 | 0 | = |
| Security hotspots | 0 | 0 | = |
| Code smells | 1 | **0** | −1 |
| Coverage (projet) | 74,5 % | 85,9 % | +11,4 pt |
| Duplication | 0,7 % | 0,7 % | = |
| Reliability / Security / Maintainability | A / A / A | A / A / A | → |

> **Honnêteté de lecture** : le bond de couverture projet (+11,4 pt) n'est pas
> imputable à cette task. La mesure de baseline provenait d'une analyse antérieure
> dont la collecte de couverture était partielle ; les deux analyses de ce run ont
> exécuté les cinq projets de tests avec OpenCover. Ce qui est réellement imputable
> à la task : `new_violations` 1 → 0 et le Quality Gate ERROR → OK.

- **Étape suivante** : `/review task-195` (ni `client-angular` ni `client-mobile`
  touchés — `/lint-angular` et `/lint-mobile` sans objet).

## Validation end-to-end du banc (exécutée — 2026-07-25)

Réalisée à la demande de l'humain via le `loadtest-skill`. **Elle lève les deux
items du DOD qui étaient déférés au HAG.**

### Correction d'un constat précédent

Le log `/develop` indiquait Postgres métier « non démarré ». **C'était un faux
négatif** : le test `</dev/tcp/localhost/5432` en Git Bash résout `localhost` en
IPv6 (`::1`), où rien n'écoute. Le conteneur `postgres-pgvector` publie bien
`0.0.0.0:5432` et acceptait les connexions. Le prérequis était réuni.

### Déroulé

| Étape | Résultat |
|---|---|
| AppHost profil `https-load-test` | ✓ `loadtest-dovecot`, `loadtest-greenmail`, `loadtest-toxiproxy` up |
| Dovecot démarré avec la conf montée | ✓ `v2.3.21 starting up for imap` ; conf effective vérifiée dans le conteneur (`mail_location = maildir:~/Maildir`, `protocols = imap`, `password=loadtest`) |
| api-mail prêt | ✓ `connection/status` → `{"mode":"online","canAccessImap":true,"canSendEmail":true}` |
| Seed (3 utilisateurs × 5 messages, PJ XDM réelles) | ✓ proxies `dovecot-imap` + `greenmail-smtp`, 15 messages appendus, settings **read-back vérifiés**, exit 0 |
| **Réception de mail** | ✓ dossiers (`INBOX`, `Brouillons`) et messages 1–5 remontés via api-mail → Toxiproxy → Dovecot (HTTP 200) |
| **Pipeline CDA / IHE-XDM** | ✓ **4 messages sur 5** en `hasMedicalDocuments: true` **et** `hasBiologyResults: true` |
| Trace Seq exigée par le DOD | ✓ 4 × `[CdaParsingService] Parsing completed: 1 CDA documents extracted from …zip` (application `mss.mail.api`, `loadtest-2@loadtest.local`) |
| Auth wildcard sans provisioning | ✓ 3 maildirs créés à la volée : `/srv/mail/loadtest-{1,2,3}@loadtest.local` |
| Volumétrie maildir disque | ✓ `du -sh /srv/mail` = **4,6 Mo** pour 15 messages à PJ (~124 Ko en moyenne) |

### Ce que la mesure démontre

- **Le blocage est levé.** Le même appel de production (`GetBodyPartAsync` sur
  `IHE_XDM.ZIP`) qui échouait contre GreenMail aboutit contre Dovecot : la pipeline
  CDA s'exécute réellement, ce qui était **impossible** sur le banc précédent.
- **Le court-circuit « déjà enrichi » est bien réel** (piège documenté du skill) :
  un premier `enrich/sync` sur une boîte dont les messages avaient déjà été lus a
  répondu 200 en **58 ms** sans rien parser. Rejoué sur une boîte **vierge**
  (`loadtest-2`), le même appel a pris **11,5 s** — le temps d'un vrai
  téléchargement à travers les 100 ms de latence injectée — et a produit les
  4 extractions. Ordre correct : `enrich/sync` **avant** toute lecture.
- Le 5ᵉ message sans document médical n'est pas un défaut du banc : le corpus
  `JEUX_TESTS_FULL` est parcouru en round-robin et toutes ses archives ne portent
  pas un CDA exploitable.

### Observation annexe — confirme un finding de l'audit

Les traces Seq montrent les archives extraites vers
`C:\Users\…\AppData\Local\Temp\{guid}.zip`, et **24 fichiers `.zip` subsistent dans
`%TEMP%` après le run**. C'est la confirmation empirique, en conditions réelles, du
finding **task-185** (« Archives IHE_XDM écrites en clair dans le répertoire
temporaire et jamais supprimées »). Hors périmètre de cette task — task-185 le
traite.

### Reste déféré au HAG

- **Run de volumétrie d'envergure** (ex. 200 × 200) : opération lourde, laissée au
  Manual Test Plan. Le mécanisme est prouvé à petite échelle et le stockage disque
  (4,6 Mo mesurés, plus de plafond de heap) est vérifié.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/122
  — label `awaiting-human-merge`, `MERGEABLE`.
- `dtos-mss` : **aucune PR** — branche créée par convention, 0 commit (aucun contrat
  DTO impacté, comme anticipé au `/start`).

## Code Review Summary

**Verdict : APPROVED** — 9 fichiers, 0 blocage, 1 suggestion non bloquante.

Garde-fous vérifiés : aucun secret introduit dans le diff ; profil `loadtest`
toujours opt-in (`MSS_LOADTEST`) ; `TestBypassAuthenticationHandler` toujours
hard-blocké en Production ; données 100 % synthétiques.

Suggestion non bloquante : les archives IHE-XDM extraites s'accumulent dans `%TEMP%`
(24 fichiers résiduels **observés** pendant la validation end-to-end) — finding
**task-185**, hors périmètre de cette task.

## Tir de charge 20 utilisateurs (2026-07-25, post-review)

Exécuté à la demande de l'humain, après ouverture de la PR. Détail complet dans le
body de la **PR #122** (section « Tir de charge 20 utilisateurs »). En résumé :

- 20 boîtes × 20 messages = **400 messages** à PJ `IHE_XDM.ZIP` (seed 4 min 53).
- 120 requêtes concurrentes, **0 erreur HTTP**.
- Pooling de session : **14 ms à chaud contre 699 ms à froid** (50×).
- **94 messages sur 100** avec documents médicaux extraits.
- Maildir : 4,6 Mo → **71 Mo**, sans plafond de heap.

**Défaut latent révélé par le tir** → **task-196** : l'embedding tronque en
caractères (20 000) alors que la limite du modèle est en tokens (8192) ; les
documents cliniques longs sont rejetés en `400`, l'exception est avalée et le
document n'entre jamais dans l'index sémantique. Non causé par cette task — il ne
pouvait pas se manifester tant que la pipeline n'extrayait rien.

Les mêmes traces confirment **task-178** en conditions réelles (contenu clinique
transmis à OpenAI hors périmètre HDS).

## Merged

Mergée le 2026-07-25 par l'humain (`/merge task-195 --i-tested` — HAG, règle 10).

| Repo | PR | Commit squash | Branche distante |
|---|---|---|---|
| `api-mail` | [#122](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/122) | `5f22334` | supprimée |
| `dtos-mss` | aucune (0 commit) | — | supprimée |

- Portes de sécurité : `--i-tested` fourni, label `awaiting-human-merge` (pas
  `awaiting-us-completion`), CI PR verte, aucune revue `CHANGES_REQUESTED`,
  `MERGEABLE`/`CLEAN`, clones propres.
- Merge **squash** (historique linéaire). `--delete-branch` volontairement **non
  utilisé** (il supprimerait aussi la branche locale) : les refs distantes ont été
  retirées via `git push origin --delete`, les branches locales sont conservées.
- `develop` synchronisé sur les deux repos ; **CI verte** sur `5f22334`
  (règle 5 respectée).
- Aucune branche staging `forge/staging-*` à nettoyer — task lancée hors `/forge`.
- `client-angular` non concerné (hors `**Repos**:`) — aucune opération git.

### Suites ouvertes

- **task-196** — défaut d'embedding (troncature en caractères vs limite en tokens),
  révélé par le tir de charge 20 utilisateurs sur ce banc.
- **task-185** — archives IHE-XDM laissées en clair dans `%TEMP%`, confirmée en
  conditions réelles pendant les tirs.
- Run de volumétrie d'envergure (200 × 200) : toujours à conduire.
