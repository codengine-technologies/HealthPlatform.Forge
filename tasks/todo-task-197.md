# todo-task-197.md — Tests d'intégration MSS hermétiques : Dovecot + GreenMail conteneurisés, boîte semée, assertions qui garantissent quelque chose

**Repos**: api-mail
**Dependencies**: task-177 (mergée, archivée), task-195 (mergée — fournit `dovecot.conf`, `BenchImap`, le corpus IHE-XDM)
**Epic**: E009
**Single frontend**: true

> **Origine** : retombée de task-177 (externalisation des secrets). Le retrait du
> mot de passe d'application Gmail committé devait faire *skipper* les suites qui
> en dépendaient. **L'analyse du 2026-08-08 montre que la situation réelle est
> pire que celle décrite** : sur un poste de développement, `Api/Mail/.env`
> (ignoré par git) porte toujours `GMAIL_EMAIL` / `GMAIL_APP_PASSWORD`, que
> `DotEnvLoader` charge — donc les 87 tests **s'exécutent**, contre **une vraie
> boîte Gmail personnelle**, à chaque run de la suite d'intégration. La perte de
> couverture n'existe qu'en CI ; le problème de fond, lui, est permanent.

## Objective

Rendre les suites d'intégration MSS **hermétiques et probantes** : elles doivent
s'exécuter contre des conteneurs **Dovecot** (IMAP) et **GreenMail** (puits SMTP)
pilotés par Testcontainers, contre une boîte **semée de façon déterministe**, et
**asserter exactement** sur ce qui a été semé.

Trois bénéfices, dans cet ordre d'importance :

1. **Les tests garantissent quelque chose.** ~58 des 96 tests concernés ne
   garantissent rien aujourd'hui (détail plus bas). C'est le vrai gain, et il est
   indépendant du serveur employé.
2. **Reproductibilité.** Le résultat cesse de dépendre du contenu d'une boîte
   personnelle qui dérive à chaque run.
3. **Aucune donnée personnelle ni credential** dans la chaîne de test d'un
   service HDS, et exécutabilité en CI sans réseau sortant.

**US backend-only (justification)** : infrastructure de test de `api-mail`.
Aucun code de production, aucun contrat, aucun écran modifié.

---

## État réel constaté (analyse du 2026-08-08 — remplace le constat d'origine)

### Le compte exact

| Grandeur | Valeur | Source |
|---|---|---|
| Tests dans les 12 suites visées | **96** | comptage `[Fact]`/`[SkippableFact]`/`[Theory]` |
| Gatés sur `IsConfigured` (credentials Gmail) | **87** | `Skip.IfNot(_fixture.IsConfigured, …)` |
| **Ne garantissent rien** (early-return sur boîte vide, assertion tautologique, `Assert.True(true)`, action jamais exécutée) | **~58** | inventaire ligne à ligne |
| `CdaParsingIntegrationTests` — **0 gate**, tourne déjà | **9** | 0 occurrence de `IsConfigured` |
| `ContactsUseCaseTests` — gatés Gmail mais **n'utilisent aucun IMAP** | **8** | 8 gates, 0 référence `IImapService`/`IImapFolderService`/`EnsureEmailsEnriched` |
| Tests exigeant réellement une boîte semée | **79** | 87 − 8 |

Compte de la suite d'intégration : **370 passants / 16 ignorés avec `.env`**
(poste de dev, boîte Gmail réelle) ; **183 / 103 sans `.env`** (CI). Les 16
ignorés structurels sont les suites Ollama, hors périmètre.

### Deux corrections au constat d'origine

- **`CdaParsingIntegrationTests` n'est pas concernée** : elle lit les archives
  locales de `Resources/cda-samples/`, n'est gatée sur rien, et passe déjà. Elle
  ne fait pas partie des 87. (Elle sera néanmoins **complétée** — voir le
  livrable 5.)
- **`ContactsUseCaseTests` est gatée sans raison** : 8 tests purement Postgres.
  Retirer leur gate les débloque immédiatement, sans Dovecot ni seed.

### Les familles de non-déterminisme à éliminer

Elles sont toutes grep-vérifiables, ce qui rend le DOD binaire :

1. **Early-return silencieux « boîte vide → test vert »** — 29 occurrences.
   Exemple : `ImapServiceIntegrationTests.cs:33-37`
   `if (…Uids.Count == 0) { WriteLine("No unread emails in INBOX, skipping test"); return; }`.
2. **Assertion tautologique** — `Assert.NotNull(x)` sur un type non nullable
   (11 occurrences), `Assert.True(true)` dans un `catch` (5 occurrences dans
   `SearchUseCaseTests`), assertions portant sur une variable **construite dans
   le test** (`EmailCompositionUseCaseTests.cs:318-319`, `:431-432`, `:618-620`).
3. **Succès affiché sur données simulées** — `MedicalDocumentsUseCaseTests.cs:74-84`,
   `:167-180`, `:335-346` : quand la boîte ne porte pas de document médical, le
   test appelle un `DisplaySample…()` codé en dur puis écrit
   `"✅ SUCCÈS: Format d'extraction patient validé"` et sort vert.
   `:296-297` (UC7.3) asserte `Assert.Equal(3, abnormalCount)` sur **un tableau
   littéral déclaré dans le test** — zéro contact avec le code de production.
4. **Action annoncée jamais exécutée** — `EmailManagementUseCaseTests.cs:569-613`
   et `:631-678` : « Supprimer un email » / « Supprimer plusieurs emails »
   n'appellent jamais `DeleteEmailAsync`/`DeleteEmailsAsync`
   (« suppression non exécutée pour préserver les données »).
5. **Échec transformé en skip** — `ImapConnectionServiceIntegrationTests.cs:56`
   et `:183` : `Skip.IfNot(result1.IsSuccess, "First connection failed")`. Une
   panne de connexion devient un test ignoré, jamais un échec.
6. **Branche morte** — les 6 tests de `SearchUseCaseTests` enveloppent
   `GetService<ISemanticSearchService>()` (qui ne lève jamais) dans un
   `catch (InvalidOperationException)`. Le service **est** enregistré
   (`ServiceCollectionExtensions.cs:70`) : la branche « service indisponible »
   est inatteignable, et le `catch (Exception) { Assert.True(true); }` qui suit
   rend le test vert sur n'importe quelle panne.
7. **Crash au lieu d'une assertion** — `EmailReadingUseCaseTests.cs:207` :
   `page2Uids.Max()` lève `InvalidOperationException` si l'INBOX porte moins de
   21 messages. Le seed doit donc garantir un plancher, et le test doit asserter
   plutôt que crasher.

### Ce qui existe déjà et doit être réutilisé (ne rien réinventer)

| Actif | Emplacement | Usage |
|---|---|---|
| `StartDovecotOrSkipAsync()` | `tests/…/LoadTest/DovecotBenchSmokeTests.cs` | **Patron prouvé vert** : `ContainerBuilder`, bind-mount de la conf du banc, port aléatoire, `Wait…UntilMessageIsLogged("starting up")` |
| `BenchImap` | `tests/…/LoadTest/BenchImap.cs` | `NewTrustingClient()`, `SeedMailboxAsync(…)`, `AppendWithAttachmentAsync(…)` — à **étendre**, voir livrable 2 |
| `dovecot.conf` du banc | `src/AppHost/dovecot/dovecot.conf` | `passdb static` wildcard (aucun provisioning d'utilisateur) ; `Sent`/`Drafts`/`Trash` en `special_use` ; maildir ; **fetch partiel `BODY[part]` fonctionnel** |
| Conteneur GreenMail du banc | `src/AppHost/AppHost.cs` (`greenmail/standalone:2.1.3`, `-Dgreenmail.auth.disabled`) | Puits SMTP — Dovecot est en `protocols = imap`, il n'y a **pas** de SMTP côté Dovecot |
| `LoadTestPlanGenerator` | `tests/mss.mail.testing.shared` | Génération **déterministe** : `loadtest-{n}@loadtest.local`, mot de passe `loadtest`, `OwnerMarker`, sujets/expéditeurs/corps sans aléa |
| Corpus IHE-XDM | `tests/…/Resources/cda-samples/` | **5 archives valides + 1 `Malformed`**, 16 Ko à 324 Ko, déjà copiées à l'output (`Content … CopyToOutputDirectory`), résolues par `AppContext.BaseDirectory`. **Les 5 portent des OID INS** (`1.2.250.1.213.1.4.8`/`.10`) pour **3 identifiants distincts** |
| Seeder du banc | `tests/mss.mail.loadtest.seed/Program.cs` | Fait déjà le round-robin du corpus IHE-XDM sur les messages semés — **patron à reprendre tel quel** |
| `PostgreSqlFixture` | `tests/…/Fixtures/` | Patron de fixture Testcontainers (`IAsyncLifetime`) |
| `BenchConfigLocator` | `tests/…/Fixtures/` | Localise `src/AppHost/{dossier}/{fichier}` depuis la racine du repo |
| `MailServerDiscovery` | `src/Application/…` | `GetImapServerConfig` donne la **priorité à `UserSettings.ImapServerConfig`** sur le domaine — porte de sortie si une suite doit voir un autre serveur |

---

## Contenu attendu

### 1. `DovecotFixture` + `GreenMailFixture` (nouvelles, `tests/…/Fixtures/`)

Conteneurs gérés par **Testcontainers**, auto-portants — ils démarrent leur
propre conteneur et ne dépendent **pas** de l'AppHost. C'est la différence
décisive avec `DovecotBenchSmokeTests`, qui skippent proprement quand le banc
n'est pas monté et resteraient donc ignorés en CI.

- **Dovecot** : image `dovecot/dovecot:2.3.21`, bind-mount de
  `src/AppHost/dovecot/dovecot.conf` **en lecture seule** via `BenchConfigLocator`
  (la conf du banc, pas une copie : une régression de configuration casse le
  test), port 993 en binding aléatoire. Expose hôte + port IMAPS.
- **GreenMail** : image `greenmail/standalone:2.1.3`,
  `GREENMAIL_OPTS=-Dgreenmail.setup.test.all -Dgreenmail.hostname=0.0.0.0 -Dgreenmail.auth.disabled`,
  port SMTPS 3465 en binding aléatoire. **Puits d'envoi uniquement** — il ne sert
  jamais d'IMAP (motif du remplacement en task-195 : il répond mal au fetch
  partiel `BODY[part]`).

**Le port étant dynamique**, la configuration doit être construite **après** le
démarrage des conteneurs — c'est déjà l'ordre de `InitializeAsync` (conteneurs,
puis `ConfigureServices`).

### 2. Extension de `BenchImap` — les primitives de seed manquantes

`BenchImap` ne sait aujourd'hui appender **que dans INBOX, en non-lu, avec
from/to/sujet/corps**. Le corpus exigé (§ « Corpus de seed ») demande en plus :

- APPEND avec **flags** (`\Seen`, `\Flagged`) — pour les « ≥ 10 lus » / « ≥ 10 non flaggés » ;
- APPEND avec **date interne** — pour le « reçu aujourd'hui » ;
- APPEND avec en-têtes **`Message-ID`, `In-Reply-To`, `References`** — pour le fil de discussion ;
- APPEND **dans un dossier arbitraire** (pas seulement INBOX) ;
- une surcharge acceptant un **`MimeMessage` complet**, qui absorbe tous les cas ci-dessus.

Rester **déterministe** : aucun `Guid.NewGuid()`, aucun `DateTime.Now` dans le
contenu semé, hormis la date interne explicitement voulue par le test « du jour ».

### 3. Recâblage des fixtures + isolation par utilisateur virtuel

`ImapServicesFixture` et `UseCaseFixture` pointent sur les conteneurs au lieu de
Gmail. `IsConfigured` disparaît (le conteneur est toujours là), donc **tous** les
`Skip.IfNot(_fixture.IsConfigured, …)` sont supprimés.

- Déclarer le domaine **`loadtest.local`** dans le dictionnaire in-memory
  `MailServers:Domains` (là où `gmail.com` est déclaré depuis task-237), avec
  l'hôte/port mappés, `UseSsl=true`, `UseOAuth2=false`,
  `ValidateServerCertificate=false`, `ForceIPv4=true`, et le SMTP pointant sur
  GreenMail.
- **`SslTlsOptions`** (`ValidateCertificate=false`, `AllowUntrustedCertificates=true`,
  `CheckCertificateRevocation=false`) doit être configuré dans **les deux**
  fixtures — `UseCaseFixture` ne le fait pas aujourd'hui.
- **Un utilisateur virtuel dédié par suite** (`GenerateUsers(n)` — la `passdb
  static` wildcard les rend gratuits, la boîte naît à la première connexion).
  C'est plus fort que le dossier dédié : les suites qui mutent ne peuvent plus
  détruire les pré-conditions des autres, et l'ordre d'exécution devient
  indifférent (xUnit parallélise les classes).

**Pourquoi l'isolation est une condition, pas une précaution** — trois suites
mutent la boîte et se détruisent mutuellement leurs pré-conditions :
`EmailManagementUseCaseTests` bascule `\Seen`/`\Unseen`/`\Flagged` (le stock de
non-lus fond à chaque run, ce dont dépendent 3 tests `ImapService` et UC1.6) ;
`ImapFolderServiceIntegrationTests` déplace un vrai message hors d'INBOX puis le
remet (si le retour échoue, la boîte reste dégradée) ;
`EmailCompositionUseCaseTests` fait 6 envois réels vers soi-même plus l'archivage
dans `Sent` (chaque run fait dériver compteurs, pagination et « UID le plus
récent »). Le maildir mourant avec le conteneur, l'idempotence inter-run devient
gratuite.

### 4. Seed déterministe par suite + assertions exactes

Chaque suite sème les messages dont elle a besoin (voir § « Corpus de seed »),
puis **asserte exactement dessus**. Toute assertion écrite contre le contenu
arbitraire de la boîte Gmail devient une assertion exacte sur les données semées.

Les sept familles listées plus haut disparaissent :

- l'early-return sur boîte vide devient une **assertion sur le compte semé** ;
- `Assert.NotNull` sur non-nullable devient une assertion de **contenu** ;
- les `catch (Exception) { Assert.True(true); }` de `SearchUseCaseTests` et leur
  `catch (InvalidOperationException)` mort sont **supprimés** ; la suite asserte
  sur `SearchMode.FullTextOnly` — chemin qui **n'exige aucun embedding**
  (`PerformFullTextSearchAsync`) — contre des sujets/corps semés connus. Le
  chemin sémantique reste hors portée (embeddings mockés, Ollama hors scope) :
  soit il est retiré de la suite, soit il porte un `Skip` **honnête** qui dit
  pourquoi ;
- `UC2.7`/`UC2.8` **appellent réellement** `DeleteEmailAsync`/`DeleteEmailsAsync`
  sur des messages semés pour ça, et assertent la disparition — la boîte étant
  jetable, l'argument « préserver les données » tombe ;
- les `Skip.IfNot(result.IsSuccess, …)` de `ImapConnectionServiceIntegrationTests`
  deviennent des `Assert` : une panne de connexion doit **échouer** ;
- `EmailReadingUseCaseTests` UC1.2 asserte la pagination au lieu de crasher sur
  `page2Uids.Max()` ;
- les `DisplaySample…()` de `MedicalDocumentsUseCaseTests` et le tableau littéral
  d'UC7.3 sont **supprimés** : les valeurs assertées viennent du CDA semé.

### 5. ⭐ Le test de bout en bout de la pipeline documents médicaux

**Livrable central de cette task** — un test qui prouve que la chaîne complète
fonctionne contre un serveur conteneurisé, avec un **vrai CDA injecté**.

Scénario, dans `UseCases/MedicalDocumentsUseCaseTests` (ou une classe dédiée) :

1. **Semer** dans l'INBOX d'un utilisateur virtuel dédié un message portant une
   archive **`IHE_XDM.ZIP` réelle** de `Resources/cda-samples/` (nom de fichier
   **exactement** `IHE_XDM.ZIP` — api-mail déclenche la pipeline sur le **nom**,
   insensible à la casse, jamais sur le content-type).
2. **Enrichir** via `EnrichEmailsAsync` (le chemin de production), ce qui exerce
   le **fetch partiel `BODY[part]`** — la raison même du choix de Dovecot.
3. **Asserter exactement**, sans aucune branche conditionnelle :
   - le mail est stocké avec `HasMedicalDocuments == true` ;
   - le **nombre** de documents médicaux extraits est celui attendu de l'archive
     choisie, et leurs champs (titre / type / date) valent les valeurs du CDA ;
   - le **patient est créé en base avec son INS**, celui du CDA ;
   - pour une archive de biologie, les résultats sont exploitables
     (`HasBiologyResults`, comptes attendus).
4. **Le chemin d'erreur, dans le même lot** : l'archive `Malformed/IHE_XDM.ZIP`
   ne doit ni faire crasher l'enrichissement ni produire de document — **et le
   message doit rester stocké** (invariant task-227 : le contenu clinique ne
   disparaît jamais en silence).
5. **Le multi-archives** : semer les 5 archives valides et asserter le nombre de
   **patients distincts** créés. Le corpus en porte **3 INS distincts** — le
   chiffre exact doit être épinglé par un premier run avant d'être gravé, le
   parseur pouvant ne retenir qu'un type d'INS.

Ce test est le seul du dépôt qui exercera CDA + IHE-XDM + fetch partiel +
persistance patient **de bout en bout et sans dépendance externe**. Aujourd'hui,
la seule assertion forte équivalente (`MedicalDocumentsUseCaseTests.cs:606-611`)
est conditionnée à la présence fortuite d'une pièce jointe dans une boîte réelle.

### 6. Neutralité SMTP — GreenMail comme puits d'envoi

`EmailCompositionUseCaseTests` effectue **6 envois SMTP réels**. Ils doivent
viser GreenMail, **jamais** un relais externe. `AppendToSentAsync` continue
d'archiver dans `Sent` côté Dovecot (le dossier existe via `special_use`). Un
test doit vérifier que le message **est bien arrivé dans le puits** — un envoi
non vérifié ne prouve rien de plus qu'une absence d'exception.

### 7. Retrait des credentials Gmail du code de test

`GmailEmail`, `GmailAppPassword`, `GMAIL_EMAIL`, `GMAIL_APP_PASSWORD`,
`IsConfigured` et le bloc `Gmail` disparaissent des **fixtures**, de
`appsettings.test.json` et de `.env.example`.

> ⚠️ **Le critère ne peut pas être « `git grep -i gmail` ne rend rien ».** Gmail
> est un **fournisseur supporté en production** : `src/Api/appsettings.json`
> déclare le domaine `gmail.com`, `MailFolderNamingRule` traite
> `[Gmail]/Sent Mail`, `AutoconfigService` aussi — 52 fichiers suivis citent
> Gmail légitimement. Le critère est **scopé aux fixtures et à la configuration
> de test**. (Correction du DOD d'origine, qui était infaisable.)

### 8. Déblocage sans infrastructure (à faire en premier, coût nul)

- **`ContactsUseCaseTests`** : retirer les 8 gates `IsConfigured`. Ces tests sont
  purement Postgres et n'ont jamais eu besoin d'une boîte mail.
- **`CdaParsingIntegrationTests`** : la sortir du décompte des suites migrées
  (0 gate, elle tourne déjà). Elle n'est concernée que par le livrable 5.

---

## Corpus de seed exigé (INBOX, dans les **100 messages les plus récents**)

Le plafond de 100 n'est pas arbitraire : `UseCaseFixture.EnsureEmailsEnrichedAsync`
et UC7.5 prennent `Take(100)`.

| Ce qu'il faut | Pourquoi |
|---|---|
| **≥ 41 messages** | pagination UC1.2 — en dessous de **21**, `EmailReadingUseCaseTests.cs:207` `page2Uids.Max()` **crashe** ; en dessous de 40 le test se contente de logger |
| **≥ 10 non lus** | UC2.1, UC2.5, UC1.6, 3 tests `ImapServiceIntegrationTests` |
| **≥ 10 lus** (`\Seen`) | UC2.2, UC2.6 |
| **≥ 10 non flaggés** | UC2.3 |
| **≥ 1 message avec pièce jointe** dans les 50 plus récents | UC1.4 — téléchargeable par nom exact |
| **≥ 1 message avec `IHE_XDM.ZIP`** (nom exact, sans suffixe) | UC7.5 + livrable 5 |
| **≥ 1 CDA portant un INS** | sans lui, 6 des 8 tests de `PatientUseCaseTests` ne testent plus rien |
| **≥ 1 message de biologie** (ou sujet « biologie » / « laboratoire ») | UC7.2 |
| **≥ 1 corps lisible** dans les 10 plus récents | UC1.3 |
| **≥ 1 `Message-ID`** dans les 10 / 30 / 50 plus récents | UC3.3, UC1.5 |
| **≥ 1 fil** (`In-Reply-To` / `References`) | UC1.5 — sans assertion aujourd'hui, c'est le contrat visé |
| **≥ 1 message reçu aujourd'hui** | UC1.7, UC7.4 (`GetFolderTodayAsync`, `GetWithMedicalDocumentsTodayAsync`) |
| **Absents** : dossier `NONEXISTENT_FOLDER_12345`, INS `UNKNOWN_INS` / `ZZZZNONEXISTENT`, PJ `nonexistent.pdf` | assertions négatives existantes |

**Dossiers** : INBOX, `Sent`, `Drafts`, `Trash` — fournis d'office par
`dovecot.conf` via `special_use`. Les tests acceptent indifféremment `Sent` ou
`[Gmail]/Sent Mail`, donc rien à adapter. Le harnais crée et supprime lui-même
ses `TestFolder_*` / `MoveTest_*`.

---

## Hors scope

- Les suites **Ollama** (`Services/Ai*`) : elles gatent sur un service local sans
  credential et skippaient déjà avant task-177. Conteneuriser Ollama est une task
  distincte (modèles lourds). Ce sont les **16 ignorés structurels** attendus.
- Le **chemin sémantique** de la recherche (embeddings) : `IEmailEmbeddingService`
  est un mock dans les fixtures et le rendre réel dépend d'Ollama. Seul le chemin
  `FullTextOnly` est rendu déterministe ici.
- La suite **Annuaire Santé / FHIR ANS** : `AnnuaireSanteServiceIntegrationTests.cs`
  est **intégralement commenté** (`////`) et ne contribue à aucun test. Le
  comportement est couvert unitairement. **Décider séparément** : supprimer le
  fichier mort ou le ressusciter contre un stub HTTP.
- Le banc de **charge** (E015) : on **réutilise** son image, sa configuration
  Dovecot, `BenchImap` et son corpus — on ne le modifie pas. Une seule exception
  autorisée : **étendre** `BenchImap` (livrable 2), qui est du code de test
  partagé, en préservant ses appelants existants.
- **Toute modification de code de production.**

---

## Definition of Done

### Infrastructure

- [ ] Build passes (0 errors), 0 avertissement
- [ ] `DovecotFixture` démarre un conteneur Dovecot via Testcontainers, **sans
      AppHost**, en montant `src/AppHost/dovecot/dovecot.conf`, et sans aucun
      credential lu depuis un fichier suivi
- [ ] `GreenMailFixture` démarre un conteneur GreenMail servant de **puits SMTP**,
      et un test vérifie qu'un message envoyé y **arrive** (pas seulement qu'aucune
      exception n'est levée)
- [ ] Les deux fixtures configurent `SslTlsOptions` (certificat auto-signé accepté)
- [ ] `BenchImap` sait appender avec **flags**, **date interne**, en-têtes de
      **fil** (`Message-ID`/`In-Reply-To`/`References`) et **dans un dossier
      arbitraire** ; ses appelants existants (banc de charge) compilent et passent
      inchangés

### Exécution et couverture

- [ ] Plus aucun `Skip.IfNot(_fixture.IsConfigured, …)` dans les 12 suites —
      vérifiable : `grep -rc "IsConfigured" tests/mss.mail.integration.tests/` rend **0**
- [ ] Suite d'intégration exécutée **sans `.env`, sans variable Gmail** :
      **≥ 370 passants, 0 échec, ≤ 16 ignorés** (Ollama uniquement). Référence
      d'avant : 183 / 103 dans ces conditions
- [ ] Le compte d'ignorés pour cause de « Gmail credentials not configured » vaut **0**
- [ ] Aucun appel réseau sortant pendant la suite (Docker local excepté) —
      vérification documentée : la suite passe réseau externe coupé

### Les tests garantissent quelque chose

- [ ] **Zéro early-return sur boîte vide** dans les 12 suites — vérifiable :
      aucune occurrence de `Count == 0` / `is not > 0` / `== null` suivie d'un
      `return;` sans assertion (29 occurrences à traiter)
- [ ] **Zéro `Assert.True(true)`** et **zéro `catch` avalant une exception sans
      assertion** dans les 12 suites
- [ ] **Zéro `Assert.NotNull`** portant sur un type non nullable (11 occurrences)
- [ ] **Zéro assertion portant sur une variable construite dans le test**
      (`EmailComposition` `:318-319`, `:431-432`, `:618-620`)
- [ ] Les `DisplaySample…()` et le tableau littéral d'UC7.3 de
      `MedicalDocumentsUseCaseTests` sont **supprimés** ; les valeurs assertées
      viennent du CDA semé
- [ ] `UC2.7` et `UC2.8` **appellent** `DeleteEmailAsync`/`DeleteEmailsAsync` et
      assertent la disparition du message
- [ ] `ImapConnectionServiceIntegrationTests` : une panne de connexion **échoue**
      (plus de `Skip.IfNot(result.IsSuccess, …)`)
- [ ] `EmailReadingUseCaseTests` UC1.2 asserte la pagination au lieu de crasher
- [ ] `SearchUseCaseTests` : le `catch (InvalidOperationException)` mort est
      supprimé et chaque test asserte sur `SearchMode.FullTextOnly` contre du
      contenu semé, **ou** porte un `Skip` explicite motivé par l'absence
      d'embeddings

### ⭐ Pipeline documents médicaux (livrable central)

- [ ] Un test **de bout en bout** sème un message porteur d'une archive
      `IHE_XDM.ZIP` **réelle** de `Resources/cda-samples/`, l'enrichit via
      `EnrichEmailsAsync`, et asserte **sans branche conditionnelle** :
      `HasMedicalDocuments == true`, le **nombre exact** de documents extraits,
      leurs champs (titre / type / date), et le **patient créé en base avec son INS**
- [ ] Le **fetch partiel `BODY[part]`** est effectivement exercé par ce chemin
      (c'est la raison du choix de Dovecot ; GreenMail y échoue)
- [ ] Une archive de **biologie** produit des résultats exploitables
      (`HasBiologyResults`, comptes attendus)
- [ ] L'archive **`Malformed`** ne fait ni crasher l'enrichissement ni produire de
      document, **et le message reste stocké** (invariant task-227)
- [ ] Les **5 archives valides** semées produisent le nombre attendu de **patients
      distincts** (chiffre épinglé par un premier run — le corpus porte 3 INS distincts)

### Isolation et hygiène

- [ ] Isolation prouvée : un **utilisateur virtuel dédié par suite**, les suites
      passent dans n'importe quel ordre et en parallèle sans se polluer —
      vérifié par deux exécutions consécutives sans nettoyage, résultat identique
- [ ] Aucun conteneur résiduel après le run (`docker ps -a`)
- [ ] Plus aucune référence à Gmail **dans les fixtures, `appsettings.test.json`
      et `.env.example`** (le code de production continue légitimement de
      supporter Gmail — voir livrable 7)
- [ ] Le garde-fou `SecretLiteralScanTests` de task-177 reste vert
- [ ] `IntegrationTestBase` (filet à erreurs journalisées, task-235) reste actif
      sur les suites qui en héritent

---

## Manual Test Plan

1. **Le cas CI** — `cd Api/Mail`, renommer temporairement `.env` en `.env.off`,
   puis :
   `dotnet test tests/mss.mail.integration.tests/mss.mail.integration.tests.csproj`
   **Attendu** : ≥ 370 passants, 0 échec, ≤ 16 ignorés (Ollama uniquement).
   Avant cette task, dans ces conditions : 183 passants / 103 ignorés.
2. **Les conteneurs** — pendant l'exécution, `docker ps` montre un conteneur
   Dovecot **et** un conteneur GreenMail ; après, `docker ps -a` n'en montre
   aucun résidu.
3. **Hermétisme** — couper le réseau externe (garder Docker local), relancer :
   même résultat, aucune dépendance à un service externe.
4. **Idempotence** — relancer deux fois de suite sans nettoyer : même résultat,
   au test près (seed déterministe, pas de pollution inter-run).
5. **La pipeline médicale** — lancer le seul test de bout en bout du livrable 5 :
   `dotnet test … --filter "FullyQualifiedName~MedicalDocument"`, vérifier qu'il
   asserte des valeurs **exactes** issues du CDA (et non « au moins un »), et que
   le cas `Malformed` passe sans crash avec le message tout de même stocké.
6. **Le puits SMTP** — vérifier qu'un test lit le message dans GreenMail après
   envoi, et que `Sent` côté Dovecot en porte la copie.
7. **Aucun credential** — `git grep -i "gmail"` limité à
   `tests/**/Fixtures`, `tests/**/appsettings.test.json` et `.env.example` :
   aucune occurrence. (Le reste du dépôt en porte légitimement — Gmail est un
   fournisseur supporté.)
8. **Isolation** — lancer les suites dans un ordre inversé (ou en parallèle) :
   même résultat.

---

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors DSR — infrastructure de test, aucune exigence
  fonctionnelle adressée
- **Exigences DSR honorées** : aucune directement. Contribution **indirecte** à
  la conformité PGSSI-S : suppression d'un compte de messagerie **externe et
  personnel** de la chaîne de test d'un service hébergé HDS, et suppression du
  besoin de credential dans le repo (complète task-177)
- **INS** : les INS manipulées sont celles du corpus IHE-XDM de test déjà présent
  au dépôt (échantillons publiés, **valeurs de test**, aucun patient réel).
  Aucune INS réelle ne doit entrer dans les fixtures
- **Authentification PS** : non applicable — authentification IMAP/SMTP basique
  contre des conteneurs locaux, aucun PSC dans ce périmètre
- **Habilitations** : inchangées
- **Interop CI-SIS** : le fetch partiel `BODY[part]` et la pipeline CDA/IHE-XDM
  restent exercés, désormais localement et **de façon assertée** — la couverture
  d'interopérabilité est **renforcée**, pas seulement maintenue
- **Tracé PGSSI-S** : non applicable
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : sans objet pour les tests, mais la task **retire** une
  dépendance externe de la chaîne de validation d'un service HDS
- **AIPD / impact RGPD** : **amélioration, et le constat d'origine est aggravé**.
  Il ne s'agit pas d'un risque théorique : sur tout poste portant un `.env`, la
  suite d'intégration **lit aujourd'hui une boîte Gmail personnelle réelle** à
  chaque exécution, et tout message qui s'y trouve traverse la chaîne de test.
  Après migration, plus aucune donnée personnelle réelle n'est traitée par les
  tests. **À signaler au DPO** comme mesure corrective associée à l'incident
  task-177.

---

## ⚠️ Note de dimensionnement (pour le PO et la forge)

Cette task réunit délibérément ce qui pourrait être trois lots : (1) le déblocage
gratuit (`Contacts`, décompte `CdaParsing`), (2) le socle conteneurs + seed, (3)
la réécriture de ~58 assertions sur 11 suites. C'est un choix assumé — la
migration n'a de valeur que si les tests migrés garantissent quelque chose, et
livrer (2) sans (3) poserait une infrastructure hermétique sous des tests qui ne
prouvent toujours rien.

**Conséquence pratique** : le volume de fichiers modifiés dépassera le repère des
~30 fichiers par PR (règle 5). Si `/develop` doit fractionner, l'ordre imposé est
**1 → 2 → 5 (pipeline médicale) → 3 → 6 → 4 sur les suites restantes**, et aucune
PR intermédiaire ne merge avant que l'ensemble soit prêt (règle 11, US-complete
merge gate).
