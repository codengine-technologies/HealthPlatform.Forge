# todo-task-177.md — Secrets vivants committés dans `AppHost.cs` (clé OpenAI, clé passerelle FHIR ANS, mots de passe)

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axe confidentialité).
> **⚠️ Incident de sécurité — traiter en priorité absolue, avant toute autre task
> de ce lot.** Une partie du traitement est **humaine et hors code** (rotation,
> réécriture d'historique) : voir la répartition ci-dessous.

## Objective

Sortir du code source les secrets aujourd'hui **committés en clair** dans
`src/AppHost/AppHost.cs`, et déclencher la rotation des credentials exposés. Le
fichier porte notamment une clé d'API OpenAI de projet, la clé d'accès à la
**passerelle FHIR de l'ANS** (`gateway.api.esante.gouv.fr`), la clé
d'environnement Flagsmith et des mots de passe de base.

Le dispositif d'externalisation **existe déjà et fonctionne** : un `.env`
correctement git-ignoré porte précisément ces clés, et des commentaires du fichier
indiquent explicitement `=> .env`. Le code les court-circuite en dur.

**US backend-only (justification)** : configuration et amorçage local de
`api-mail`. Aucun contrat ni écran impacté.

### Preuve (constat vérifié, sans divulgation)

Vérifié par le PO **sans jamais afficher les valeurs** :

- `src/AppHost/AppHost.cs` est un fichier **suivi par git** (`git ls-files`).
- Il contient **un** littéral de forme clé de projet OpenAI (`sk-proj-…`),
  **délibérément scindé en deux littéraux concaténés** — ce qui le fait passer
  sous le radar d'un scan de secrets naïf.
- Ce littéral est présent **dans `HEAD`** et dans **3 commits** de l'historique
  (`git log -S`), donc dans tout clone, fork, cache CI et artefact de build.
- 5 affectations de variables d'environnement sensibles dans ce fichier :
  `OpenAi__ApiKey`, `FhirOptions__ApiKey`, `FLAGSMITH_ENVIRONMENT_KEY`, mots de
  passe Postgres et Flagsmith (ce dernier également dans
  `src/AppHost/FlagsmithSeeder.cs`).

Portée aggravante : la clé OpenAI donne accès à l'**historique des requêtes** du
compte, lequel contient des prompts cliniques (voir task-178).

Hors périmètre du finding : `src/Api/appsettings.Development.json` porte la même
valeur mais est git-ignoré et absent de l'historique — local uniquement.

### Répartition du traitement

**Partie humaine — à faire immédiatement, hors forge (non automatisable) :**

1. **Rotation** de tous les credentials exposés : clé OpenAI, clé passerelle FHIR
   ANS (procédure ANS), clé d'environnement Flagsmith, mots de passe Postgres et
   Flagsmith. La rotation prime sur le nettoyage du code : tant que la clé est
   valide, le retrait du littéral ne protège rien.
2. **Décision sur l'historique git** : la réécriture d'historique
   (`git filter-repo` ou équivalent) est nécessaire pour effacer la valeur des
   3 commits, avec la coordination que cela impose sur un repo partagé. À arbitrer
   par le humain — la forge ne réécrit jamais l'historique.
3. **Revue d'accès** : qui a eu accès au repo, aux forks, aux caches CI, aux
   artefacts de build sur la période. Statuer avec le DPO sur la qualification
   RGPD (voir section conformité).

**Partie code — périmètre de cette task :**

1. **Aucun secret littéral** dans `src/AppHost/AppHost.cs`, `FlagsmithSeeder.cs`
   ni ailleurs dans le code suivi : lecture **exclusive** depuis la configuration
   (`.env`, variables d'environnement, gestionnaire de secrets).
2. **Fail-fast au démarrage** : un secret requis absent ⇒ message d'erreur
   explicite nommant la clé manquante et **arrêt**. Jamais de repli silencieux,
   jamais de valeur par défaut de secours.
3. **Aucune valeur de secret journalisée** ni affichée au démarrage. Attention au
   piège connu du workspace : `${VAR:+<set>}${VAR:-<missing>}` en bash **imprime
   le secret** — utiliser `[ -n "$VAR" ] && echo "<set>" || echo "<missing>"`.
4. **Garde-fou anti-récidive** : un contrôle mécanique refusant l'introduction
   d'un littéral de forme secret dans le code suivi (hook, règle CI ou test),
   capable de détecter le contournement **par concaténation** utilisé ici.
5. **Documentation** : `.env.example` (sans valeurs) listant toutes les clés
   requises, et la procédure de démarrage local mise à jour.

### Hors scope

- La rotation elle-même et la réécriture d'historique (humain, ci-dessus).
- La question du routage des données cliniques vers OpenAI → **task-178**.
- L'audit des secrets des autres repos du workspace (un secret Gmail committé est
  connu ailleurs et n'a **pas** été retrouvé dans `api-mail`).

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] `git grep` sur le code **suivi** ne remonte plus aucun littéral de forme
      secret (clé OpenAI, clé FHIR, clé Flagsmith, mot de passe) — y compris
      recherche **résistante à la concaténation** de littéraux
- [ ] Toutes les valeurs sensibles proviennent de la configuration ; aucune valeur
      par défaut en dur, aucun repli silencieux
- [ ] Démarrage sans secret requis ⇒ échec immédiat et message nommant la clé
      manquante (test automatisé sur ce comportement)
- [ ] Aucun secret dans les logs de démarrage, ni en clair ni partiellement
      (test ou vérification documentée)
- [ ] Garde-fou anti-récidive en place et **prouvé** : un littéral de test
      scindé en deux morceaux concaténés est bien détecté
- [ ] `.env.example` complet (clés, aucune valeur) + procédure de démarrage local
      à jour
- [ ] Démarrage local vérifié de bout en bout avec les secrets en `.env`
- [ ] Note d'incident rédigée pour le humain : credentials exposés, fenêtre
      d'exposition, état de la rotation, décision sur l'historique git

## Manual Test Plan

1. Renseigner les clés (après rotation) dans le `.env` du workspace.
2. Lancer : `cd Api/Mail && dotnet run --project src/AppHost` → l'application
   démarre, IA et passerelle FHIR fonctionnelles comme avant.
3. **Retirer** une clé requise du `.env`, relancer → échec immédiat au démarrage
   avec un message nommant la clé manquante (et non un 500 tardif à la première
   requête IA).
4. Relire les logs de démarrage : aucune valeur de secret, même tronquée.
5. Vérifier le nettoyage : `git grep -i 'sk-proj'` (et équivalents) sur les
   fichiers suivis ne remonte rien.
6. Tester le garde-fou : introduire dans un fichier suivi un faux secret **scindé
   en deux littéraux concaténés**, tenter le commit → refus explicite. Retirer.
7. Vérifier avec le humain que la rotation est effective : l'ancienne clé OpenAI
   est révoquée (un appel avec l'ancienne valeur échoue).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — le credential exposé donne accès à une passerelle
  **nationale** (FHIR ANS)
- **Exigences DSR honorées** : correctif de conformité PGSSI-S — gestion des
  secrets et protection des accès aux téléservices ANS
- **INS** : non applicable directement — mais l'accès au compte OpenAI exposé
  permet de lire un historique de requêtes contenant des données de santé
  (task-178), ce qui étend la portée de l'incident
- **Authentification PS** : inchangée — les secrets concernés sont des
  credentials **applicatifs**, pas l'authentification des praticiens
- **Habilitations** : non applicable
- **Interop CI-SIS** : la clé de la passerelle FHIR ANS relève des volets de
  transport CI-SIS ; sa compromission est à signaler à l'ANS selon leur procédure
  (arbitrage humain)
- **Tracé PGSSI-S** : journaliser l'échec de démarrage pour secret manquant
  (évènement technique, jamais la valeur)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — `api-mail` est hébergé HDS ; un secret dans le code
  source est hors du périmètre de protection HDS
- **AIPD / impact RGPD** : **à mettre à jour**. Violation de l'art. 32 (sécurité
  du traitement). Combinée à task-178, l'exposition peut donner accès à des
  données de santé : à qualifier avec le DPO, y compris sur l'obligation de
  notification CNIL. **Qualification = livrable humain de cette task.**

## Branches
- `api-mail` (pushed) : `feat/task-177-externalize-apphost-secrets`
- `dtos-mss` (pushed, auto-included) : même nom de branche — 0 commit attendu

## Develop log

- **Repos touched** : `api-mail` uniquement. `dtos-mss` branche vide.
- **DTOs / Interop published** : aucun changement de contrat.

### Ce qui a été fait

| Fichier | Changement |
|---|---|
| `src/AppHost/AppHostSecrets.cs` *(nouveau)* | chargement du `.env` du workspace (remontée de répertoires ; **l'environnement l'emporte** sur le fichier) ; `Require(clé)` = secret réel, absent ⇒ **échec immédiat nommant la clé**, aucun repli ; `LocalOrDefault(clé, défaut)` = valeur locale non secrète, surchargeable |
| `src/AppHost/AppHost.cs` | 3 secrets réels via `Require` ; mots de passe de conteneurs locaux via `LocalOrDefault` ; **plus aucun littéral** |
| `src/AppHost/FlagsmithSeeder.cs` | mot de passe admin externalisé ; **2 `Console.WriteLine` qui imprimaient la clé d'environnement Flagsmith** ne loggent plus que sa présence |
| `tests/mss.mail.integration.tests/appsettings.test.json` | clés secrètes **retirées** (pas remplacées par une valeur bidon) |
| `.env.example` *(nouveau)* | toutes les clés, aucune valeur, + procédure de démarrage local |
| `docs/task-177-incident-secrets.md` *(nouveau)* | note d'incident : credentials, fenêtre d'exposition, checklist rotation / historique / DPO |
| `tests/.../Security/SecretLiteralScanTests.cs` *(nouveau)* | garde-fou anti-récidive, 8 tests |
| `tests/.../Security/AppHostSecretsTests.cs` *(nouveau)* | 7 tests de résolution des secrets |

### 🔴 Deux expositions au-delà du périmètre annoncé par la task

Le garde-fou écrit pour cette task a trouvé, dans le fichier **suivi**
`tests/mss.mail.integration.tests/appsettings.test.json` :

1. **la même clé de passerelle FHIR ANS** que `AppHost.cs` ;
2. **le mot de passe d'application Gmail** — que la task affirmait explicitement
   **absent** de `api-mail` (« un secret Gmail committé est connu ailleurs et n'a
   **pas** été retrouvé dans `api-mail` »).

La surface d'exposition est donc plus large que documentée. Le DOD couvre le cas
(« aucun secret littéral … **ni ailleurs dans le code suivi** »), donc les deux
sont traités ici et entrent dans le périmètre de **rotation**.

### 🔴 Fuite additionnelle dans la conduite de la task

La clé **FHIR ANS** et la clé **d'environnement Flagsmith** ont été imprimées en
clair dans le transcript de la session de forge : une commande de redaction dont
le motif ne couvrait pas la forme `WithEnvironment("clé", "valeur")`. Ces deux
valeurs sont exposées dans un support supplémentaire. N'change pas l'action
requise (la rotation était déjà obligatoire) mais **en renforce l'urgence** et
doit figurer dans la qualification de portée. Consigné dans la note d'incident.

### Choix de conception

- **Deux accès distincts, pas un seul avec défaut optionnel** : `Require` n'a
  **aucune** surcharge acceptant un fallback (test dédié qui le vérifie par
  réflexion). Un défaut silencieux est la façon dont une machine finit par
  appeler une passerelle nationale avec le mauvais credential.
- **Clés secrètes retirées du JSON de test, pas remplacées par une valeur bidon** :
  les fixtures font `config → variable d'environnement → absent ⇒ skip`. Une
  valeur factice non vide aurait rendu `IsConfigured` vrai et fait **échouer** les
  tests Gmail/FHIR au lieu de les **skipper**.
- **`AppHostSecrets.cs` lié en compilation** dans `mss.mail.api.tests` plutôt que
  référencé par projet : l'AppHost est un exécutable Aspire, une `ProjectReference`
  tirerait tout l'hôte distribué dans les tests unitaires.

### Garde-fou anti-récidive — calibrage

Première version : scan du texte brut → **15 fichiers signalés, tous faux
positifs** (`Password = clientPassword`, une affectation d'identifiant). Un
garde-fou à quinze faux positifs finit désactivé. Resserré à :

- scan du **contenu des littéraux de chaîne** (les identifiants n'y sont pas) ;
- **recollage des littéraux concaténés** avant match ⇒ neutralise exactement le
  contournement de l'incident (prouvé sur 2 et 3 morceaux) ;
- règle « mot de passe » limitée au **code de production** (les fixtures portent
  légitimement des chaînes de connexion synthétiques) ; les règles **clé d'API**
  s'appliquent partout, tests inclus — c'est ce qui a trouvé les 2 secrets de
  `appsettings.test.json` ;
- allowlist **étroite et nommée** des défauts locaux documentés.

### Build / tests

Build **0 erreur / 0 avertissement**.

| Projet | Résultat |
|---|---|
| `mss.mail.domain.tests` | 102 ✓ |
| `mss.mail.application.tests` | 1852 ✓ |
| `mss.mail.infrastructure.tests` | 370 ✓ |
| `mss.mail.api.tests` | **590 ✓** (+15) |

⚠️ Deux tests **flaky sous charge parallèle**, tous deux verts en isolation
(31/31 et 7/7), aucun lien avec ce diff : `MarkdownPdfRendererTests` /
`MailExportServiceTests` (flaky documenté) et **`CdaProcessingMetricsTests`
(nouvellement observé** — probable état statique OTel partagé).

### DOD self-check

| Critère | État |
|---|---|
| Build 0 erreur | ✓ |
| Tests 0 échec | ✓ (hors 2 flaky documentés) |
| `git grep` code suivi sans littéral de forme secret, résistant à la concaténation | ✓ test automatisé |
| Toutes valeurs sensibles depuis la configuration, aucun défaut en dur | ✓ `Require` sans surcharge fallback (test par réflexion) |
| Démarrage sans secret ⇒ échec immédiat nommant la clé | ✓ `Require_WhenTheSecretIsAbsent_ThrowsNamingTheKey` (3 cas) |
| Aucun secret dans les logs de démarrage | ✓ 2 `Console.WriteLine` corrigés ; `MissingSecretMessage` ne porte que la clé |
| Garde-fou en place et **prouvé** sur un littéral scindé | ✓ 2 tests (2 et 3 morceaux) |
| `.env.example` complet + procédure locale | ✓ |
| Démarrage local vérifié de bout en bout | ⚠️ **non fait** — exige les clés **après rotation**, donc reporté au Manual Test Plan (humain) |
| Note d'incident rédigée | ✓ `docs/task-177-incident-secrets.md` |

- **Next step** : /sonar task-177

## Sonar log

Projet `healthplatform` — **2 analyses** (la première a été rejetée, voir ci-dessous).

### ⚠️ Première analyse invalidée

L'analyse initiale a été lancée **avant** la correction du garde-fou de skip,
donc sur un run où **87 tests d'intégration échouaient**. La couverture qu'elle a
mesurée n'était pas représentative (des tests non exécutés ne couvrent rien). Elle
a été **jetée et refaite** après correction plutôt que rapportée avec un
avertissement : une KPI de couverture fausse dans le body d'une PR est pire
qu'absente.

### KPIs qualité (analyse retenue)

| Métrique | Valeur | Cible | État |
|---|---|---|---|
| Bugs | **0** | 0 | ✓ |
| Vulnerabilities | **0** | 0 | ✓ |
| Security hotspots | **0** | revue humaine | ✓ |
| Code smells | **9 → 3** (après fix, cf. ci-dessous) | — | — |
| Reliability / Security / Maintainability | **A / A / A** | A | ✓ |
| Coverage | **84.2 %** | 95.0 % | ✗ |
| Line / Branch coverage | **88.0 % / 74.3 %** | — | — |
| New coverage | **84.5 %** | — | QG OK |
| Duplication | **0.7 %** | — | — |
| Dette technique | **11 min** | — | — |

**Quality Gate : `ERROR`** — unique condition en échec `new_violations = 9`. Les
3 autres sont `OK` (`new_coverage` 84.5, `new_duplicated_lines_density` 0.12 %,
`new_security_hotspots_reviewed` 100 %).

### 📉 Baisse de couverture assumée : 86.5 % → 84.2 %

**Ce n'est pas une régression de qualité, c'est la fin d'une illusion.** Les
87 tests d'intégration qui ne tournent plus produisaient de la couverture en
appelant une **vraie boîte Gmail** avec le credential committé. Cette couverture
existait au prix d'un secret dans le repo et d'un résultat dépendant du contenu
réel d'une boîte personnelle. La retirer fait apparaître le niveau réel de
couverture hermétique.

Récupération prévue par **task-197** (migration vers le conteneur Dovecot), qui
restaure la couverture **sans credential** et avec des assertions déterministes.

### Findings introduits par task-177 — tous corrigés

| Règle | Fichier | Occurrences | Correction |
|---|---|---|---|
| `external_roslyn:SYSLIB1045` | `tests/…/Security/SecretLiteralScanTests.cs` | 6 | `new Regex(...)` → méthodes partielles `[GeneratedRegex]` (automate construit à la compilation) — commit `a24a08c` |

→ **Zero-new-debt tenu** : plus aucun finding Sonar sur les fichiers du diff
task-177. Contrôle `awk 'length($0)>150'` passé avant commit cette fois (la
consigne `S103` de `conventions/csharp.md` a été appliquée d'emblée, contrairement
à task-176).

### Findings restants — dette antérieure, hors module

| Règle | Fichier | Ligne |
|---|---|---|
| `python:S1481` | `tests/loadtest-k6/report.py` | 62 |
| `python:S1481` | `tests/loadtest-k6/report.py` | 64 |
| `python:S3457` | `tests/loadtest-k6/report.py` | 121 |

Troisième PR consécutive où ces 3 issues rougissent le Quality Gate sans lui
appartenir (fichier absent du diff, commit `134647b` de task-174 déjà sur
`develop`). **Le housekeeping devient utile** : à ce rythme le QG rouge cesse
d'être un signal.

- **Itérations** : 1 corrective (+1 analyse jetée)
- **Next step** : /review task-177

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/129 — label `awaiting-human-merge`
- `dtos-mss` : **aucune PR** — branche créée par `/start`, 0 commit. À supprimer au `/merge`.
- `client-angular` / `client-mobile` / `client-blazor` : non touchés
- `devops`, `psc-proxy-*` : managed manually by the human

## Staging

- `api-mail` : `forge/staging-task-176-196-20260728` — task-176 puis task-177
  agrégées par `git merge --no-ff`, **sans conflit**.

## Code Review Summary

**Verdict : APPROVED** — 21 fichiers, **0 blocage**, 3 remarques non bloquantes.

| Axe | Verdict |
|---|---|
| Correctness | ✓ `LoadEnvFile()` avant `CreateBuilder` ; environnement prioritaire sur le fichier ; aucun littéral de forme secret ou mot de passe restant |
| Sécurité | ✓ garde-fou prouvant l'absence de littéral ; `FlagsmithSeeder` n'imprime plus la clé ; le scanner rapporte la **règle**, jamais la valeur |
| Architecture | ✓ séparation `Require` / `LocalOrDefault` **vérifiée par réflexion** (aucune surcharge fallback) ; lien de compilation évitant l'hôte Aspire dans les tests |
| Qualité | ✓ 0 avertissement ; regex générées à la compilation |
| Tests | ✓ 15 nouveaux ; garde-fou prouvé sur 2 et 3 morceaux concaténés |

**Remarques non bloquantes** :
1. ⚠️ `LoadEnvFile` / `ApplyEnvFile` **non testés** — seule vraie lacune. Parseur
   avec des cas limites (commentaires, dé-quotage, valeur contenant `=`, règle
   « l'environnement gagne »). Risque contenu : une mauvaise analyse ⇒ `Require`
   lève ⇒ arrêt bruyant, jamais une valeur erronée silencieuse.
2. ⚠️ `[ExcludeFromCodeCoverage]` sur une classe désormais testée (7 tests) —
   l'attribut sous-estime la couverture. À revoir avec le point 1.
3. ℹ️ `KEY=` vide exporté par le shell n'est pas `null` ⇒ non écrasé par le
   fichier ⇒ `Require` lève. Sens sûr mais subtil.

## Validation finale

- Build : ✓ 0 erreur / 0 avertissement (Debug et Release)
- Tests : ✓ 3097 ✓ / 0 ✗ / 103 ignorés (domain 102, application 1852,
  infrastructure 370, api 590, intégration 183)
- Sync `develop` : ✓ `Already up to date`
- DOD : ✓ tous les items vérifiables ; **1 item reporté au Manual Test Plan** —
  « démarrage local vérifié de bout en bout » exige les clés **après rotation**
- Code review : ✓ APPROVED
- Quality Gate : `ERROR` sur `new_violations = 9` → 6 findings task-177 corrigés
  (`a24a08c`), 3 restants **antérieurs** hors diff (`tests/loadtest-k6/report.py`)

## Suites ouvertes (hors périmètre, à arbitrer)

1. **Rotation des 4 credentials** — OpenAI, FHIR ANS (procédure ANS), Flagsmith,
   **Gmail**. Rien n'est protégé avant. Checklist : `docs/task-177-incident-secrets.md`
2. **Réécriture d'historique** — valeur OpenAI dans 3 commits ; la forge ne
   réécrit jamais l'historique
3. **Qualification RGPD art. 32 avec le DPO** + signalement ANS
4. **task-197** — migration Dovecot pour récupérer les 87 tests sans credential
5. **Housekeeping `tests/loadtest-k6/`** — 3 issues Python qui rougissent le QG
   de **chaque** PR api-mail (3ᵉ consécutive)
6. **Flaky `CdaProcessingMetricsTests`** — nouvellement observé, à documenter
