# todo-task-197.md — Tests d'intégration MSS hermétiques : migrer les suites Gmail vers le conteneur Dovecot

**Repos**: api-mail
**Dependencies**: task-177
**Epic**: E009
**Single frontend**: true

> **Origine** : retombée de task-177 (externalisation des secrets). Le retrait du
> mot de passe d'application Gmail committé a révélé que **87 tests
> d'intégration ne passaient que parce qu'ils appelaient une vraie boîte Gmail
> personnelle** avec ce credential. Ils sont désormais correctement *skippés*,
> d'où une perte de couverture réelle à récupérer.

## Objective

Rendre les suites d'intégration MSS **hermétiques** : elles doivent s'exécuter
contre un conteneur **Dovecot** piloté par Testcontainers, avec une boîte
**semée de façon déterministe**, au lieu d'un compte Gmail externe.

Bénéfice au-delà de la simple restauration de couverture : les tests deviennent
**reproductibles** (aujourd'hui leur résultat dépend du contenu réel d'une boîte
personnelle), **exécutables en CI** (aucun credential, aucun réseau sortant), et
**sans donnée personnelle** dans la chaîne de test d'un service HDS.

**US backend-only (justification)** : infrastructure de test de `api-mail`.
Aucun code de production, aucun contrat, aucun écran modifié.

### État actuel (vérifié)

- `Fixtures/ImapServicesFixture.cs` résout ses credentials en
  `config["Gmail:…"] ?? Environment.GetEnvironmentVariable("GMAIL_…") ?? ""`,
  puis expose `IsConfigured`. Idem `UseCases/UseCaseFixture.cs`.
- Depuis task-177 les clés ont été **retirées** du
  `tests/mss.mail.integration.tests/appsettings.test.json` suivi par git ⇒
  `IsConfigured == false` ⇒ `Skip.IfNot(...)` ⇒ suites skippées.
- Mesure après task-177 : suite d'intégration **183 ✓ / 0 ✗ / 103 ignorés**,
  contre **274 ✓ / 16 ignorés** avant. Les 16 ignorés d'origine sont les suites
  **Ollama** (service local, aucun credential — hors périmètre de cette task).
- Suites concernées (12 fichiers, ~87 tests) :
  `Services/ImapConnectionServiceIntegrationTests`,
  `Services/ImapFolderServiceIntegrationTests`,
  `Services/ImapServiceIntegrationTests`,
  `Services/CdaParsingIntegrationTests`,
  `UseCases/{Contacts,EmailComposition,EmailManagement,EmailReading,Folders,MedicalDocuments,Patient,Search}UseCaseTests`.

### Ce qui existe déjà et doit être réutilisé (ne rien réinventer)

| Actif | Emplacement | Usage |
|---|---|---|
| `BenchImap` | `tests/…/LoadTest/BenchImap.cs` | `NewTrustingClient()` (accepte le certificat auto-signé du conteneur), `SeedMailboxAsync(host, port, user, messages)`, `AppendWithAttachmentAsync(…)` — **exactement** les primitives de seed nécessaires, pièces jointes CDA/IHE-XDM comprises |
| Configuration Dovecot de production du banc | `src/AppHost/dovecot/dovecot.conf` | à monter dans le conteneur — stockage maildir et **fetch partiel `BODY[part]` fonctionnel**, ce que GreenMail rate (motif du remplacement en task-195) |
| `SyntheticUser` / `SyntheticMessage` | `tests/mss.mail.testing.shared` | modèles d'identité et de message du banc |
| `PostgreSqlFixture` | `tests/…/Fixtures/PostgreSqlFixture.cs` | **patron** de fixture Testcontainers : `IAsyncLifetime`, conteneur en champ, `InitializeAsync`/`DisposeAsync`, accesseur de connexion |
| `BenchConfigLocator.TryFindRepositoryRoot()` | `tests/…/Fixtures/` | localise la racine du repo pour monter `dovecot.conf` |

### Contenu attendu

1. **`DovecotFixture`** (nouvelle, `tests/…/Fixtures/`) : conteneur Dovecot géré
   par **Testcontainers** (paquet `Testcontainers` déjà référencé), montant
   `src/AppHost/dovecot/dovecot.conf`, exposant hôte + port IMAPS et les
   identifiants de l'utilisateur virtuel. Modelée sur `PostgreSqlFixture`.
   **Auto-portante** : elle démarre son propre conteneur et ne dépend **pas** de
   l'AppHost — c'est la différence décisive avec `DovecotBenchSmokeTests`, qui se
   contentent de skipper quand le banc n'est pas monté et resteraient donc
   ignorés en CI.
2. **Recâblage des fixtures** : `ImapServicesFixture` et `UseCaseFixture`
   pointent sur `DovecotFixture` au lieu de Gmail. `IsConfigured` devient vrai
   par construction (le conteneur est toujours là), donc les `Skip.IfNot(…)`
   correspondants **disparaissent**.
3. **Seed déterministe par suite** : chaque suite sème les messages dont elle a
   besoin via `BenchImap` (sujets, expéditeurs, pièces jointes, dossiers), au
   lieu de dépendre du contenu d'une boîte réelle. **Isolation entre suites** :
   utilisateur virtuel ou dossier dédié par suite, comme le fait déjà
   `SearchScenarioTests` avec un nom de dossier unique par test.
4. **Assertions rendues déterministes** : toute assertion aujourd'hui écrite
   contre le contenu arbitraire de la boîte Gmail (« il existe au moins un
   mail… ») devient une assertion **exacte** sur les données semées. C'est le
   vrai gain : ces tests passaient sans rien garantir.
5. **Retrait des credentials Gmail du code de test** : `GmailEmail`,
   `GmailAppPassword`, `GMAIL_EMAIL`, `GMAIL_APP_PASSWORD` et le bloc `Gmail`
   n'ont plus de raison d'exister dans les fixtures ni dans `.env.example`.
6. **Neutralité SMTP** : les suites d'envoi (`EmailComposition`) doivent viser un
   puits SMTP local (GreenMail est déjà le puits d'envoi du banc) et **jamais**
   un relais externe.

### Hors scope

- Les suites **Ollama** (`Services/Ai*`) : elles gatent sur un service local
  sans credential, elles skippaient déjà avant task-177. Conteneuriser Ollama
  est une task distincte (et discutable — modèles lourds).
- La suite **Annuaire Santé / FHIR ANS** : le fichier
  `Services/AnnuaireSanteServiceIntegrationTests.cs` est **intégralement commenté**
  (`////`) et ne contribue à aucun test. Le comportement est déjà couvert au
  niveau unitaire par `mss.mail.application.tests/Services/AnnuaireSante/` avec
  `FhirBundleFactory`. **Décider séparément** : supprimer ce fichier mort ou le
  ressusciter contre un stub HTTP. Une passerelle nationale n'a pas à être verte
  en CI.
- Le banc de **charge** (task-173/195/174, EPIC E015) : on **réutilise** son
  image et sa configuration Dovecot, on ne le modifie pas.
- Toute modification de code de production.

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] `DovecotFixture` démarre un conteneur Dovecot via Testcontainers, sans
      AppHost, et sans aucun credential lu depuis un fichier suivi
- [ ] Les 12 suites listées **s'exécutent** (plus aucune n'est ignorée pour cause
      de « Gmail credentials not configured ») — vérifié par le compte
      `ignorée(s)` de la suite d'intégration
- [ ] Suite d'intégration : **≥ 270 tests passants**, 0 échec, et les seuls
      ignorés restants sont les suites Ollama (~16) — c'est-à-dire retour au
      niveau de couverture d'avant task-177, désormais **sans credential**
- [ ] Chaque suite migrée sème ses propres données et assert **exactement**
      dessus (aucune assertion du type « au moins un mail existe »)
- [ ] Isolation prouvée : les suites peuvent tourner dans n'importe quel ordre et
      en parallèle du reste sans se polluer (utilisateur ou dossier dédié)
- [ ] Le fetch partiel `BODY[part]` et la pipeline CDA/IHE-XDM sont exercés
      contre Dovecot (au moins 1 test de `CdaParsingIntegrationTests` avec une
      pièce jointe `IHE_XDM.ZIP` semée par `BenchImap.AppendWithAttachmentAsync`)
- [ ] Aucune référence résiduelle à Gmail dans les fixtures, `appsettings.test.json`
      et `.env.example` (`git grep -i gmail` sur les fichiers suivis)
- [ ] Aucun appel réseau sortant pendant la suite d'intégration (vérification
      documentée : la suite passe avec le réseau externe coupé, Docker local
      excepté)
- [ ] Le garde-fou `SecretLiteralScanTests` de task-177 reste vert

## Manual Test Plan

1. `cd Api/Mail` puis, **sans aucun `.env` ni variable Gmail** :
   `dotnet test tests/mss.mail.integration.tests/mss.mail.integration.tests.csproj`
2. **Attendu** : ≥ 270 passants, 0 échec, ~16 ignorés (Ollama uniquement).
   Avant cette task : 183 passants / 103 ignorés.
3. Vérifier qu'un conteneur Dovecot est bien créé puis détruit pendant le run
   (`docker ps` pendant l'exécution, puis `docker ps -a` après : aucun résidu).
4. Couper le réseau externe (garder Docker local), relancer la suite → même
   résultat : plus aucune dépendance à un service externe.
5. `git grep -i gmail -- .` sur les fichiers suivis → aucune occurrence dans les
   fixtures ni la configuration de test.
6. Relancer deux fois de suite sans nettoyer → même résultat (seed idempotent,
   pas de pollution inter-run).
7. Vérifier qu'un test de pièce jointe CDA passe : la pipeline IHE-XDM est bien
   exercée via le fetch partiel Dovecot.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors DSR — infrastructure de test, aucune exigence
  fonctionnelle adressée
- **Exigences DSR honorées** : aucune directement. Contribution **indirecte** à
  la conformité PGSSI-S : suppression d'un compte de messagerie **externe et
  personnel** de la chaîne de test d'un service hébergé HDS, et suppression du
  besoin de credential dans le repo (complète task-177)
- **INS** : non applicable — données semées **synthétiques uniquement**. Aucune
  donnée de santé réelle ne doit entrer dans les fixtures (les INS utilisées
  sont des valeurs de test, comme dans les suites existantes)
- **Authentification PS** : non applicable — pas d'authentification praticien
  dans ce périmètre
- **Habilitations** : inchangées
- **Interop CI-SIS** : le fetch partiel `BODY[part]` et la pipeline CDA/IHE-XDM
  restent exercés, désormais localement — la couverture d'interopérabilité est
  **maintenue**, pas réduite
- **Tracé PGSSI-S** : non applicable
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : sans objet pour les tests, mais la task **retire** une
  dépendance externe de la chaîne de validation d'un service HDS
- **AIPD / impact RGPD** : **amélioration**. Aujourd'hui la suite de tests lit une
  boîte Gmail personnelle réelle (`pascalcabanelweda@gmail.com`) : tout message
  qui s'y trouve traverse la chaîne de test. Après migration, plus aucune donnée
  personnelle réelle n'est traitée par les tests. À signaler au DPO comme mesure
  corrective associée à l'incident task-177.
