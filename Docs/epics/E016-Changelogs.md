# E016 — Changelogs (vue ingénierie)

> **Audience** : équipes techniques, backlog, dette — la vue produit vit dans [E016-tests-integration-serveur-reel.md](E016-tests-integration-serveur-reel.md)
> **Dernière mise à jour** : 2026-09-11

---

## Historique détaillé des changelogs

### v1.0 — task-300 : le gate CI s'applique enfin à `develop`

**PR** : api-mail [#230](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/230) (`awaiting-human-merge`)
**Branche** : `feat/task-300-ci-gate-tests-serveur-reel`, base `origin/develop` @ `5855604`
**Commit** : `8b25451`
**NuGet** : aucun — `dtos-mss` branché par auto-inclusion, 0 commit, pas de PR

#### Le défaut

`.github/workflows/dotnet.yml:34` portait sur l'étape `Test` :

```yaml
if: github.ref == 'refs/heads/master' || github.base_ref == 'master'
```

La forge ouvre **toutes** ses PR vers `develop` (règle 5 du CLAUDE.md racine) ;
`master` ne reçoit que des releases. La CI **construisait** sur le chemin normal
et ne **testait** jamais. Mesure du 2026-09-11 : **0 test exécuté** sur une PR
vers `develop`.

Ampleur : **97 tests** consomment un vrai serveur IMAP/SMTP (Dovecot 2.3.21 +
GreenMail 2.1.3 via Testcontainers) et ne tournaient que sur le poste du
développeur — où `metrics/timings.jsonl` journalise **13 rouges sur 30
exécutions de `mss.mail.integration.tests` (43 %)**.

#### Le livrable

1. **`[Trait("Server", "real")]` sur 16 classes** — collections `ImapServices`
   (4 : `ImapConnectionServiceIntegrationTests`,
   `ImapFolderServiceIntegrationTests`, `ImapServiceIntegrationTests`,
   `BackgroundQueueDrainTests`) et `UseCases` (9), plus
   `DovecotBenchSmokeTests`, `GreenMailBenchSmokeTests`,
   `SmtpSessionReuseBenchSmokeTests`.
   Littéraux et non constantes : convention déjà en place dans le repo
   (`[Trait("Category", "Integration")]`, `[Trait("Feature", "AI")]`).

   > Le DOD disait « les 13 suites […] plus les 3 `*BenchSmokeTests` » — 13 est
   > le compte des deux collections (4 + 9), le total à étiqueter est **16**.
   > Le critère liant est `Server=real` → **exactement 97 tests**, et il est tenu.

2. **Gate CI scindé en deux étapes gatantes**, sans condition de branche :
   - `Test (hors serveur réel)` → `--filter "Server!=real&Quarantine!~task"`
   - `Test (serveur réel — Dovecot/GreenMail via Testcontainers)` → `--filter "Server=real&Quarantine!~task"`

   Séparées pour que l'échec dise **lequel** des deux mondes a cassé et pour
   mesurer le coût de la population serveur réel à part.

3. **`Api/Mail/tests/quarantine.md`** — contrat, procédure d'entrée/sortie,
   tableau. `Quarantine!~task` est le **seul** motif d'exclusion du gate ;
   jamais un projet, un namespace ou une catégorie.

4. **Les 3 `*BenchSmokeTests` héritent d'`IntegrationTestBase`.** Les 13 autres
   suites en héritaient déjà (constat de l'implémentation, contrairement à
   l'hypothèse du task file). **Aucune exemption `ExpectedErrorFragments`
   nécessaire** — y compris pour
   `WildcardAuth_AcceptsAnyUser_AndRejectsWrongPassword`, qui éprouve pourtant
   un refus d'authentification.

#### Calibrage — 3 exécutions consécutives, base `5855604`

`dotnet test HealthPlatform.Api.Mail.sln --no-build` :

| Projet | Passe 1 | Passe 2 | Passe 3 |
|---|---|---|---|
| `mss.mail.domain.tests` | 167 ✓ | 167 ✓ | 167 ✓ |
| `mss.mail.infrastructure.tests` | 487 ✓ | 487 ✓ | 487 ✓ |
| `mss.mail.application.tests` | 2 400 ✓ | 2 400 ✓ | 2 400 ✓ |
| `mss.mail.api.tests` | 829 ✓ | 829 ✓ | 829 ✓ |
| `mss.mail.integration.tests` | 471 ✓ / 16 skip | 471 ✓ / 16 skip | 471 ✓ / 16 skip |
| **Total** | **4 370, 0 échec** | **4 370, 0 échec** | **4 370, 0 échec** |

**Liste de quarantaine vide.** Les 16 ignorés sont des `Assert.SkipUnless`
explicites (Ollama indisponible, chemins Windows-only), pas des rouges.

⚠️ Ce résultat ne dit **pas** que les flakies historiques sont corrigés — les
13 rouges de `timings.jsonl` portent sur des bases antérieures. Il dit que sur
`5855604`, le gate peut être armé **sans exclusion**, ce qui était l'inconnue.

#### Contre-épreuves du mécanisme de quarantaine

| Contre-épreuve | Attendu | Mesuré |
|---|---|---|
| `--filter "Server=real"` | population serveur réel | **97** |
| `"Server=real&Quarantine!~task"`, registre vide | 97 (clause inerte sans trait) | **97** |
| `"Server!=real&Quarantine!~task"` | 97 + N = suite complète | **4 273** (97 + 4 273 = 4 370) |
| idem après étiquetage d'**un** test | 96 | **96** |

La 2ᵉ ligne était le risque réel : si `Quarantine!~task` avait exclu les tests
**dépourvus** du trait, le gate aurait exécuté zéro test en silence — le défaut
corrigé par cette task, sous une autre forme. Étiquette de vérification retirée
(`grep task-999` → aucune trace).

#### Note de mesure

La suite compte **4 370 cas de test** exécutés pour **3 993 déclarations**
`[Fact]`/`[Theory]` — l'écart vient des lignes de données des `[Theory]`. Les
deux chiffres sont justes et ne mesurent pas la même chose.

#### Sonar

**Skippé** — `git diff --name-only origin/develop...HEAD` ne rend aucun
`src/**/*.cs`. Diff : 16 attributs de test, 3 héritages de classe de test,
1 workflow YAML, 1 markdown. Aucune issue attribuable.
Motif **indépendant** de l'état de l'infra (conteneurs `sonarqube` /
`sonarqube_db` arrêtés — `Exited (255)` depuis 2 jours ; `localhost:9001` muet).
Pour les tasks suivantes touchant du code de production :
`docker start sonarqube_db && sleep 30 && docker start sonarqube`.

#### Passe qualité `/simplify`

Aucun cleanup appliqué. Diff constitué d'attributs, d'un héritage et d'un
workflow — pas de duplication à factoriser. Une constante partagée pour les
littéraux `"Server"` / `"real"` a été **écartée** : elle dégraderait la
cohérence avec la convention `[Trait(...)]` existante et la greppabilité, pour
16 occurrences dont une faute de frappe serait sans conséquence (le test
retomberait dans la population `Server!=real`, donc resterait exécuté).

#### Limites résiduelles

- Le premier run CI paiera le tirage des images `dovecot:2.3.21`,
  `greenmail:2.1.3`, `pgvector/pgvector:pg16`, `redis:7-alpine`. Durée de CI en
  hausse — coût assumé.
- Le comportement de Testcontainers sur `ubuntu-latest` n'est validé qu'à
  partir du premier run de la PR #230.

---

## Annexe A — Cartographie des briques applicatives

| Brique | Chemin | Rôle dans l'EPIC |
|---|---|---|
| Gate CI | `Api/Mail/.github/workflows/dotnet.yml` | Deux étapes `Test` gatantes, sans condition de branche |
| Registre de quarantaine | `Api/Mail/tests/quarantine.md` | Seul motif d'exclusion admis |
| Filet d'erreurs journalisées | `tests/mss.mail.integration.tests/Harness/IntegrationTestBase.cs` | Fait échouer un test sur toute erreur `Error`/`Critical` non exemptée |
| Harnais serveur — IMAP | `tests/mss.mail.integration.tests/Fixtures/DovecotFixture.cs` | `dovecot/dovecot:2.3.21`, IMAPS, port hôte dynamique |
| Harnais serveur — puits SMTP | `tests/mss.mail.integration.tests/Fixtures/GreenMailFixture.cs` | `greenmail/standalone:2.1.3`, SMTPS + IMAPS de relecture |
| Câblage de configuration | `tests/mss.mail.integration.tests/Fixtures/MailServerTestHarness.cs` | `MailServers:Domains:{domain}:Imap|Smtp:*` |
| Corpus déterministe | `tests/mss.mail.integration.tests/Fixtures/MailboxCorpus.cs` | 45 messages/boîte, dont 1 archive IHE-XDM réelle |
| Fixture de collection `ImapServices` | `tests/mss.mail.integration.tests/Fixtures/ImapServicesFixture.cs` | Dovecot + GreenMail + pgvector + Redis |
| Fixture de collection `UseCases` | `tests/mss.mail.integration.tests/UseCases/UseCaseFixture.cs` | Les mêmes 4 images, re-démarrées (cible de task-301) |
| Client d'injection de panne | `tests/mss.mail.loadtest.seed/ToxiproxyClient.cs` | Écrit, référencé par 0 test (cible de task-304) |
| Bypass d'authentification de test | `src/Api/Authentication/TestBypassAuthenticationHandler.cs` | Code de production, utilisé par le banc (cible de task-303) |

## Annexe B — Inventaire fonctionnel daté

*Instantané au 2026-09-11, base `5855604`.*

| Grandeur | Valeur |
|---|---|
| Cas de test exécutés (solution) | **4 370** (3 993 déclarations `[Fact]`/`[Theory]`) |
| dont `Server=real` | **97** (2,2 %) |
| dont consommant réellement IMAP | **87** (97 − 8 `ContactsUseCaseTests` − 2 smoke SMTP seuls) |
| Suites étiquetées `Server=real` | **16** classes |
| Tests en quarantaine | **0** |
| Démarrages de conteneur par exécution complète | **8** (2 jeux de 4 — cible de task-301 : 6) |
| `APPEND` IMAPS par exécution complète | ~**675** (≈ 15 boîtes × 45 messages) |
| Coût marginal d'un test à serveur réel | **0,11 s** (`ImapFolderService`, 12/1,3 s) à **0,25 s** (`ImapService`, 14/3,5 s) |
| Durée de la population `Server=real` | 74 s à froid, **51 s** images tirées |
| Actions HTTP dans `src/Api` | **146**, dont **55** dépendantes d'IMAP/SMTP |
| Actions HTTP traversant un vrai serveur | **0** (cible de task-303) |
| Usages de `WebApplicationFactory` | **0** (les 2 occurrences du nom sont des commentaires) |
| Services IMAP/SMTP jamais confrontés à un vrai serveur | **15** |
| Familles de panne serveur éprouvées | **1** (mot de passe erroné) |

## Annexe C — Tasks ayant contribué à cet EPIC

| Task | Apport | RG fermées | Statut |
|---|---|---|---|
| **task-300** | Gate CI rétabli sur `develop` (deux étapes gatantes) ; `[Trait("Server","real")]` sur 16 suites ; registre de quarantaine ; 3 `*BenchSmokeTests` passés sous `IntegrationTestBase` | — | ✅ PR #230 ouverte |
| **task-301** | Harnais serveur unique au niveau assembly (`AssemblyFixture`), table d'attribution des utilisateurs virtuels, parallélisme des collections | — | 📋 todo |
| **task-302** | Conf Dovecot de test dédiée : capacité QUOTA, `Junk`/`Archive`, comptes distincts par praticien ; suite de cloisonnement inter-praticiens | — | 📋 todo |
| **task-303** | `MailApiFactory` (pipeline `Program` réel) ; première vague de 13 endpoints bout-en-bout ; Kestrel réel pour le streaming ; `ProblemDetails` sur panne IMAP | — | 📋 todo |
| **task-304** | Toxiproxy dans le harnais ; 5 familles de panne ; non-amplification des reconnexions ; intégrité de l'archive IHE-XDM sous débit dégradé | — | 📋 todo |

---

*Document vivant — régénéré par `/tech-writer E016` à chaque fin de cycle.*
