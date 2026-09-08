# todo-task-194.md — Borner le chargement des données de fils sur le chemin IMAP, sans modifier les compteurs

**Repos**: api-mail
**Dependencies**: — aucune bloquante. task-267 (corpus de banc porteur de fils) est
mergée depuis le 2026-08-23 (`9cea3f75`). Le banc permet une mesure représentative
si le corpus est réellement fileté et si le comptage est activé pendant le tir.
**Epic**: E011
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25, axe accès données.
> **Révision du 2026-09-08** : périmètre réévalué sur `api-mail/develop`, commit
> `cecf2c48`, identique au `develop` distant lors du contrôle. Cette rédaction
> remplace les révisions précédentes et leurs consignes contradictoires.
> Analyse du code et des tests existants uniquement : aucun benchmark ni test
> exécuté lors de cette réévaluation, aucun gain de latence annoncé.

## Objective

Ne plus matérialiser les identifiants et les liens de discussion de toute la
boîte pour calculer les compteurs des fils demandés par une page IMAP.
Les données chargées doivent dépendre des fils recherchés, pas des messages
sans rapport avec eux. Les compteurs et les drapeaux exposés au client restent
inchangés.

**US backend-only (justification)** : optimisation des requêtes et tests dans
`api-mail`, sans modification des DTOs, des routes ni des frontends. Le volet
patient de la rédaction initiale est retiré de cette livraison ; voir « Hors
scope ».

### État vérifié au 2026-09-08

Les chemins ci-dessous sont relatifs à `Api/Mail`. Les numéros de ligne sont
ceux du commit de référence ; les noms de méthodes font foi après déplacement.

| Élément | État actuel | Preuve |
|---|---|---|
| `GetThreadCountsAsync` | Deux chargements non restreints aux racines demandées : tous les `MessageId` non vides, puis tous les messages ayant `References` ou `InReplyTo`. Une boucle recompte les descendants pour chaque identifiant demandé. | `src/Infrastructure/Repository/MailRepository.cs:4145-4187` |
| Appel sur le chemin IMAP | `OnlineMailDataProvider` appelle ce comptage lorsque `includeThreadCounts=true`, valeur par défaut. Depuis task-266, `false` évite cet enrichissement : le défaut ne touche plus systématiquement tous les listages. | `src/Application/Services/Implementation/OnlineMailDataProvider.cs:74-102,126-160` |
| Chemin servi par la base | task-247 a déjà restreint les chargements aux fils recherchés ; task-256 a ajouté le décompte des objets matérialisés. Ce n'est pas un second balayage à corriger. | `src/Infrastructure/Repository/MailRepository.cs:1622-1669` |
| Sémantique des fils | task-268 a inclus `Sent` et ajouté des tests de convergence des deux chemins. Un mono-message expose `ThreadCount=1`. | `tests/mss.mail.integration.tests/Repository/ThreadCountConvergenceTests.cs`, `MailRepository.cs:4190-4198` |
| Typage | Le chemin base utilise `ThreadLink`, le comptage IMAP une projection anonyme statiquement typée. Aucun travail de suppression de `dynamic` ne reste à faire. | `src/Infrastructure/Repository/MailRepository.cs:1735-1737,4162-4165` |
| Préalable de mesure | Le seeder supporte `--thread-share`. Le harnais expose `CORPUS_THREAD_SHARE` et `JOURNEY_THREAD_COUNTS`. | `tests/mss.mail.loadtest.seed/SeedOptions.cs`, `tests/loadtest-k6/lib/config.js:66-86` |

Les deux requêtes de `GetThreadCountsAsync` ont des filtres de non-vacuité,
mais **aucun filtre sur les identifiants demandés**. Le problème est le volume
transféré et matérialisé, puis parcouru en mémoire. L'absence de
`AsNoTracking` n'est pas un défaut autonome sur ces projections scalaires,
qui ne matérialisent pas d'entités suivies.

## Contenu attendu

### 1. Restreindre les chargements IMAP aux fils demandés

Porter sur `GetThreadCountsAsync` la forme déjà utilisée par task-247 :

| Lot | Prédicat | Sémantique conservée |
|---|---|---|
| Racines existantes | `MessageId IN (identifiants demandés)` | Détermine le `+1` lorsque la racine existe en base. |
| Réponses directes | `InReplyTo IN (identifiants demandés)` | Recherche les réponses par égalité. |
| Citations | Disjonction de `References.Contains(rootId)` traduite en SQL | Recherche par sous-chaîne, pas par égalité ni par jeton RFC. |

Réutiliser `ReferencesAnyOf`, `LoadMailsReferencingAnyRootAsync` et les helpers
existants lorsque leurs contrats conviennent, plutôt que dupliquer les règles.
La traduction doit rester vérifiée avec Npgsql et compatible avec les tests
InMemory existants. Ne pas construire du SQL par concaténation des identifiants.

Les identifiants recherchés sont dérivés des messages de la page : ils incluent
leurs propres `MessageId` et les racines déduites de leurs références. Leur
nombre n'est donc pas nécessairement égal au nombre de messages affichés.

**Borner le chargement ne signifie pas limiter les descendants à la page.**
Aucun `Take` arbitraire, filtre sur les seuls UID affichés, filtre de dossier ou
filtre sur la seule génération du dossier affiché ne doit tronquer un fil.

### 2. Préserver les règles de comptage et d'affichage

- **Périmètre inter-dossiers et inter-pages** : une racine dans `Sent` et ses
  réponses dans `INBOX` constituent toujours le même fil. Un descendant situé
  sur une autre page reste compté.
- **Comptage de lignes pour les descendants**, pas de `MessageId` distincts :
  plusieurs lignes portant le même `MessageId` restent plusieurs descendants.
- **Union sans double comptage** : une même ligne qui répond à la racine et la
  cite dans `References` compte une seule fois, pas une fois par lot SQL.
- **Correspondance par sous-chaîne sensible à la casse** : préserver le
  comportement de `string.Contains`, y compris lorsque les identifiants
  comportent des caractères spéciaux SQL (`%`, `_`, barre oblique inverse).
  Le passage à une comparaison par jeton RFC est hors scope.
- **Racine présente ou absente** : le `+1` est conditionné par l'existence de la
  racine, pas par son nombre de copies. Les fils orphelins restent possibles.
  Le dictionnaire de compteurs ne conserve que les totaux supérieurs ou égaux
  à deux ; à l'affichage, un mono-message conserve `ThreadCount=1`.
- **Affichage inchangé** : conserver `IsPartOfThread`, la désignation de la
  feuille d'affichage via `IsThreadRoot`, le départage des dates égales et le
  dépliage du fil. Ne pas réécrire ces comportements dans cette optimisation.
- **Comptage à la demande** : conserver `includeThreadCounts=false`, l'absence
  d'appel aux deux méthodes d'enrichissement des fils et les drapeaux neutres.
  L'omission du paramètre continue d'activer les compteurs.
- **Entrée vide** : ne pas interroger la table lorsque la liste demandée est vide.

### 3. Verrouiller l'identité avant de réutiliser la déduplication

Depuis task-179, l'index unique est
`(FolderPath, UidValidity, Uid)` et non `(FolderPath, Uid)` :
`src/Infrastructure/Migrations/20260802_AddMailUidValidity.cs:43-53`.
Le helper du chemin base déduplique encore sur `(FolderPath, Uid)` et
`ThreadLink` ne porte pas `UidValidity`.

**Ne pas recopier cette clé sans test de caractérisation.** Ajouter un jeu de
référence contenant deux générations du même dossier avec le même UID et
vérifier que le portage conserve le résultat actuel de `GetThreadCountsAsync`.
Distinguer les lignes physiques, par exemple par `Mail.Id` ou l'identité
complète, tout en éliminant la double sélection d'une même ligne par les lots
« réponses » et « citations ».

Si ce jeu révèle une divergence préexistante avec le chemin base, la consigner
et demander un arbitrage avant toute modification de sa sémantique. Ne pas
masquer cette divergence en changeant les attendus ni transformer une
optimisation IMAP en correction fonctionnelle implicite des deux chemins.

### 4. Mesurer la matérialisation et le coût observé

- Ajouter une preuve sur les requêtes **réellement exécutées** par
  `GetThreadCountsAsync`, pas sur une requête équivalente reconstruite par le test.
- À fils demandés constants, ajouter des messages et des fils étrangers : le
  nombre de lignes matérialisées par ce comptage ne doit plus augmenter.
  Vérifier aussi les filtres du SQL exécuté ; un résultat fonctionnel identique
  ne prouve pas que la table n'a pas été chargée en entier.
- Produire une comparaison avant/après sur le banc des tasks 173/174, avec
  `--thread-share > 0`, `CORPUS_THREAD_SHARE` égal à la part semée et
  **`JOURNEY_THREAD_COUNTS=1`**. Cette dernière option est nécessaire pour ne
  pas mesurer uniquement le court-circuit de task-266.
- Vérifier que des fils et leurs descendants sont réellement présents dans la
  base du banc au moment du tir. `CORPUS_THREAD_SHARE` est une déclaration,
  pas une mesure du contenu stocké.
- Consigner les commits, le volume réel, la part de fils, les tailles de page,
  la concurrence, la latence réseau simulée et le protocole de chauffe. Comparer
  la latence p50/p95 de `read_list`, les erreurs, la matérialisation et la mémoire
  ou les allocations avec le même protocole d'observation.

**Limite explicite** : une recherche de sous-chaîne peut encore entraîner un
parcours important côté PostgreSQL. La tâche ne garantit ni l'absence de scan
physique ni une latence indépendante de la taille de la boîte. Le résultat
attendu est la suppression du chargement des messages étrangers aux fils
recherchés et une comparaison de performances chiffrée, sans gain prédéterminé.
Un corpus sans fils ou un tir avec comptage désactivé ne valide pas ce DOD.

## Hors scope

- **Historique patient** : le parcours `GetMailsByInsAsync(ins, page, pageSize)`
  applique déjà `CountAsync`, `Skip` et `Take` en SQL depuis task-233, puis charge
  les pièces jointes par lot (`PatientRepository.cs:463-518,566-638`). Ne pas
  refaire ce travail.
- **Suivi patient distinct à qualifier** : la surcharge sans pagination utilise
  encore `int.MaxValue` et reste accessible lorsque les paramètres sont omis.
  `GetMedicalDocumentsByInsAsync` charge encore les corps et présente un N+1,
  mais le contrôleur expose les surcharges de `GetMailsByInsAsync`, pas cette
  méthode. Examiner séparément les consommateurs et la compatibilité avant de
  plafonner le fallback ou de décider du devenir du chemin documentaire non
  exposé. Aucun `Take` silencieux ni changement patient dans task-194.
- Changement du contrat d'API, publication de DTOs, modifications des frontends.
- Nouvelle règle d'appartenance à un fil, comparaison RFC par jeton, exclusion
  de `Sent`, nouvelle politique de générations ou de purge des mails.
- Refonte du choix de la feuille d'affichage ou de la recherche de messages.
- Migration d'index ou optimisation du plan PostgreSQL à présenter comme un gain
  garanti sans mesure ; qualifier séparément un besoin révélé par le benchmark.

## Definition of Done

- [ ] Build passes (0 errors) : `dotnet build HealthPlatform.Api.Mail.sln`.
- [ ] Tests pass (0 failures, hors flaky préexistants documentés) :
      `dotnet test HealthPlatform.Api.Mail.sln`.
- [ ] Test de régression du coût sur `GetThreadCountsAsync` : SQL réellement
      exécuté filtré par les racines demandées et nombre de lignes matérialisées
      inchangé lorsque seuls des messages/fils étrangers sont ajoutés. Vérifier
      et consigner l'échec de ce test avant correction, puis son succès après.
- [ ] Tests de caractérisation : mêmes compteurs avant/après sur réponses
      directes, références seules, références nulles/vides, sous-chaînes,
      différences de casse et identifiants contenant des caractères spéciaux SQL.
- [ ] Tests : descendants hors page et racine dans un autre dossier, **`Sent`
      inclus**, conservés dans le comptage.
- [ ] Tests : même `MessageId` dans plusieurs dossiers conservé comme plusieurs
      lignes ; une ligne satisfaisant les deux critères compte une seule fois.
- [ ] Test : deux générations du même dossier avec un UID identique ne sont pas
      fusionnées par le portage ; le résultat IMAP de référence est conservé.
      Toute divergence préexistante avec le chemin base est documentée et tout
      élargissement fonctionnel fait l'objet d'un arbitrage explicite.
- [ ] Tests : racine absente, racine présente en plusieurs exemplaires,
      mono-message et liste d'identifiants vide conservent leur comportement.
- [ ] Les tests de `ThreadCountConvergenceTests` restent verts : compteurs,
      drapeaux, feuille d'affichage et dépliage inchangés sur les cas existants.
- [ ] Les tests de `ThreadCountsOnDemandTests` restent verts : aucune des deux
      méthodes d'enrichissement des fils appelée lorsque
      `includeThreadCounts=false`, et comportement par défaut inchangé.
- [ ] Réutilisation de la logique filtrée existante, sans introduire de `dynamic`,
      de filtre de dossier/génération de la page ou de limite de descendants.
- [ ] Mesures avant/après consignées dans la tâche : corpus réellement fileté,
      paramètres seeder/k6 cohérents, comptage activé, commits, volumes, chauffe,
      p50/p95 `read_list`, erreurs, lignes matérialisées et mémoire/allocations.
- [ ] Aucun changement patient, DTO, route ou frontend ; aucune donnée de santé,
      aucun identifiant de message ni contenu de référence en clair dans les
      nouveaux logs de diagnostic.

## Manual Test Plan

1. Préparer un banc isolé avec les identités synthétiques, conformément à
   `Api/Mail/docs/loadtest.md` et `Api/Mail/tests/loadtest-k6/README.md`.
   Toute purge ou réinitialisation destructive nécessite une confirmation
   explicite ; ne pas toucher à une boîte clinique pour cette campagne.
2. Depuis `Api/Mail`, lancer l'AppHost dans un terminal dédié :

   ```powershell
   dotnet run --project src/AppHost --launch-profile https-load-test
   ```

   Ouvrir le dashboard Aspire indiqué au démarrage et vérifier l'état du banc.
   Préparer un corpus représentatif avec `--thread-share` non nul, des racines
   dans `Sent`, des réponses dans d'autres dossiers, des descendants hors page
   et des messages étrangers aux fils observés. Documenter le volume atteint
   (cible : au moins 10 000 messages dans la boîte observée) et la chauffe.
3. Dans le terminal de tir, depuis `Api/Mail`, configurer la clé du banc par
   l'environnement conformément au mode d'emploi, sans la recopier dans le
   rapport. Renseigner `CORPUS_THREAD_SHARE` avec la part réellement semée et
   aligner les autres paramètres de population avec le corpus. Puis lancer :

   ```powershell
   $env:JOURNEY_THREAD_COUNTS = '1'
   .\tests\loadtest-k6\run.ps1 read
   ```

   La route observée est
   `GET /api/v1/mail/folders/{folder}/emails/{uids}`, avec comptage activé.
   Relever séparément l'opération `read_list`, pas seulement le scénario agrégé
   qui comprend aussi l'ouverture du contenu.
4. Effectuer la mesure avant correction, puis après correction sur le même
   corpus et avec les mêmes paramètres, en répétant le même protocole de chauffe.
   Publier les p50/p95, erreurs, lignes matérialisées et mémoire/allocations.
   Ne pas réensemencer par simple ajout entre les deux jambes.
5. Comparer les réponses avant/après sur plusieurs pages : mêmes `ThreadCount`,
   `IsPartOfThread` et `IsThreadRoot`, fils inter-dossiers et orphelins conservés.
   Déplier les fils dans un client existant ou via la route de fil existante et
   vérifier le contenu et la cohérence des compteurs.
6. Répéter la lecture avec `includeThreadCounts=false` et vérifier l'absence
   d'appel aux méthodes d'enrichissement des fils et les drapeaux neutres.
7. À fils demandés et page constants, comparer deux jeux synthétiques ne
   différant que par le volume de messages étrangers. **Attendu** : aucune
   croissance du nombre de lignes matérialisées par `GetThreadCountsAsync`.
   Mesurer séparément le coût PostgreSQL résiduel au lieu de supposer qu'il est
   constant.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville.
- **Vague Ségur** : hors exigence DSR spécifique ; amélioration de performance
  sans changement fonctionnel.
- **Exigences DSR honorées** : non applicable, aucune exigence fonctionnelle
  nouvelle.
- **INS** : aucune modification ; le volet patient est hors scope.
- **Authentification PS** : inchangée.
- **Habilitations** : inchangées ; conserver la base de l'utilisateur courant
  et le périmètre fonctionnel des fils, sans accès inter-utilisateurs.
- **Interop CI-SIS** : inchangée.
- **Tracé PGSSI-S** : inchangé ; ne pas réduire la journalisation existante et
  ne pas exposer le contenu des messages dans les mesures.
- **Consentement patient** : inchangé.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : oui.
- **AIPD / impact RGPD** : inchangé, aucun nouveau traitement ni changement du
  périmètre fonctionnel.

## Branches

- `api-mail` (pushed) : `fix/task-194-thread-counts-scoped-load` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-194-thread-counts-scoped-load
- `dtos-mss` (pushed, auto-inclus) : `fix/task-194-thread-counts-scoped-load` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/fix/task-194-thread-counts-scoped-load — aucun changement de contrat attendu (US backend-only), la branche restera probablement sans commit et sans PR

Créées le 2026-09-08 depuis `origin/develop`. Pré-flight `/start` : les 7 repos
forge-automated étaient sur `develop`.

## Develop log

**Repo touché** : `api-mail` uniquement. `dtos-mss` : branche créée par `/start`
(auto-inclusion), **aucun commit** — l'US ne change ni DTO, ni route, ni
frontend, donc aucune publication NuGet et aucun bump de consommateur.

**Commits** :
- `531d0dd3` — `fix(mail): borner le chargement des fils aux racines demandees
  sur le chemin IMAP — task-194` (la feature et ses tests) ;
- `5fea456f` — `refactor(mail): simplify pass (/simplify) — task-194` (la passe
  qualité intégrée, quality-only).

### Ce qui a changé

`src/Infrastructure/Repository/MailRepository.cs` :

| Élément | Avant | Après |
|---|---|---|
| `GetThreadCountsAsync` | 2 requêtes **non filtrées** (tous les `MessageId` non vides ; tous les messages porteurs de `References` ou `InReplyTo`), prédicat de comptage appliqué en mémoire | 3 lots **bornés aux racines demandées** : racines existantes (`MessageId IN`), réponses directes (`InReplyTo IN`), citations (sous-chaîne via `ReferencesAnyOf` / `LoadMailsReferencingAnyRootAsync`) |
| Comptage | boucle locale recopiée | `BuildThreadCountsByRoot`, le helper **déjà** utilisé par le chemin base |
| Règle de rattachement | écrite 4 fois (comptage base, comptage IMAP, `BelongsToThread`, feuille d'affichage) | extraite dans `IsDescendantOf(inReplyTo, references, rootId)` — sous-chaîne, **ordinale** |
| Union des lots | inexistante (une seule requête, donc comptage de lignes de fait) | `DistinctBy(m => m.Id)` — la **ligne physique** |
| `ThreadLink` | `(FolderPath, Uid, MessageId, InReplyTo, References, SentDate)` | + `Id` en tête, l'identité de ligne |
| Instrumentation | aucune | `DbOperationScope.AddMaterializedObjects(ThreadLinks, …)` sur les 3 lots, comme le chemin base depuis task-256 |

**Aucun** filtre de dossier, de génération ou de page n'a été ajouté ; aucun
`Take` ; `Sent` reste inclus. Pas de `dynamic`. La liste vide sort avant toute
requête, et une liste ne contenant que des identifiants vides aussi — laisser
entrer un identifiant vide rendait `References.Contains("")` vrai pour chaque
ligne, c'est-à-dire le balayage supprimé, rentré par la porte du cas limite.

### Preuves de coût — rouges AVANT, vertes APRÈS

Nouveau fichier `tests/mss.mail.integration.tests/Repository/ThreadCountsScopedLoadTests.cs`
(15 tests, vrai PostgreSQL). Le rouge a été **constaté** en remettant la version
`origin/develop` du seul fichier de production, les tests inchangés :

| Test | Avant correction | Après |
|---|---|---|
| `TheExecutedSqlIsScopedToTheRequestedRoots` | **ROUGE** — « 2 out of 2 items in the collection did not pass » : les deux lectures de `Mails` exécutées avec `[Parameters=[]]`, c'est-à-dire sans aucune référence aux racines demandées | vert |
| `AddingForeignMailsDoesNotReadMoreRows` | **ROUGE** — 4 lignes attendues, **23 lues** | vert : 4 avant l'ajout de 40 messages étrangers, **4 après** — écart nul |
| `IdentifiersWithSqlSpecialCharactersAreMatchedLiterally` | **ROUGE** — 3 lignes attendues, **111 lues** | vert |
| `ARequestMadeOnlyOfEmptyIdentifiersQueriesNothing` | **ROUGE** — une liste faite uniquement d'identifiants vides interrogeait la table | vert |
| les 11 autres (caractérisation) | **verts** | verts |

Les deux chiffres « 23 » et « 111 » ne sont pas du bruit : la base du conteneur
est partagée par la collection, donc le comptage non borné **suivait le volume
accumulé par les tests voisins**. C'est le défaut, mesuré.

Les lignes sont comptées par un **intercepteur EF attaché au contexte du test**
(`RowCountingInterceptor`, `ReadCount` par commande), et non par le compteur
d'objets du dépôt : celui-ci passe par un `Meter` statique partagé par tout le
processus, et task-291 réserve ce type de capture aux collections sérialisantes
(le garde-fou `MetricCaptureSerialisationScanTests` aurait signalé le fichier).
L'intercepteur mesure de surcroît **ce que la base a rendu**, pas ce que le code
déclare avoir matérialisé. Ce choix n'était pas cosmétique : le tir final en
chemins standards confirme que `MetricCaptureSerialisationScanTests` serait
sorti **rouge** avec la première version, fondée sur le `Meter` statique.

Les 11 tests de caractérisation verts *des deux côtés* sont le point important :
ils prouvent que les compteurs et les règles de rattachement n'ont pas bougé.
Ils couvrent : réponse directe, descendant par `References` seul,
`References` nul et vide, sous-chaîne, différence de casse, identifiants
contenant `%`, `_` et `\`, racine dans `Sent` avec descendants hors page et
hors génération, même `MessageId` dans plusieurs dossiers, ligne satisfaisant
les deux critères comptée une fois, deux générations d'un même dossier
partageant un `Uid`, racine absente, racine en plusieurs exemplaires,
mono-message, liste vide.

Le test de coût porte sur le **SQL réellement exécuté**, relu dans le journal
du provider (`LogTo` + `EnableSensitiveDataLogging`), pas sur une requête
équivalente reconstruite par le test.

### Divergence pré-existante consignée — arbitrage demandé, rien changé

Le chemin base déduplique encore son union sur `(FolderPath, Uid)`. Depuis
task-179 l'index unique est `(FolderPath, UidValidity, Uid)`
(`src/Infrastructure/Migrations/20260802_AddMailUidValidity.cs:43-53`) : cette
clé **n'identifie plus une ligne**. Sur un décor de deux générations d'un même
dossier partageant un `Uid`, le chemin base **fusionnerait** les deux
descendants là où le chemin IMAP en compte deux.

Conformément au §3 de la tâche, le portage n'a **pas** recopié cette clé : il
déduplique sur `Mail.Id`, seule clé qui reproduit exactement le comportement
d'avant task-194 (une requête, aucune déduplication, donc un comptage de
lignes). Le cas est verrouillé par
`TwoGenerationsOfTheSameFolderSharingAUidAreNotMerged`. **La sémantique du
chemin base n'est pas modifiée** — l'aligner (et donc changer des compteurs
servis par la base) demande un arbitrage explicite, hors scope de task-194.

### Validation build / tests

**Suite complète VERTE en chemins standards**, AppHost arrêté par l'humain sur
demande (2026-09-08) :

| Projet | Verts | Rouges | Ignorés |
|---|---|---|---|
| `mss.mail.domain.tests` | 136 | 0 | 0 |
| `mss.mail.infrastructure.tests` | 475 | 0 | 0 |
| `mss.mail.application.tests` | 2 312 | 0 | 0 |
| `mss.mail.api.tests` | 822 | 0 | 0 |
| `mss.mail.integration.tests` | 463 | 0 | 16 |
| **Total** | **4 208** | **0** | **16** |

- `dotnet build HealthPlatform.Api.Mail.sln` : **0 erreur, 0 avertissement**.
- `dotnet test HealthPlatform.Api.Mail.sln` : **0 échec**. Les trois flaky
  pré-existants connus de ce dépôt (middleware DB-name en Release, annulation
  IMAP, export PDF) ne se sont pas déclenchés sur ce tir.
- Les **7 tests d'architecture** qui scannent les sources sont donc réellement
  exécutés et verts — dont `MetricCaptureSerialisationScanTests` (task-291),
  celui qui aurait signalé le fichier de test si la passe qualité n'avait pas
  remplacé le `MeterListener` par un intercepteur EF.

**Chemin parcouru avant ce tir, et pourquoi il est consigné.** Toute la mise au
point s'est faite avec `--artifacts-path`, parce que l'AppHost tournait (5
réplicas `mss.mail.api` + Visual Studio verrouillaient
`src/Api/bin/Debug/net10.0`) et que `dotnet build` sortait en `MSB3021`/`MSB3027`
sur la copie des DLL. Ce contournement **casse 107 tests** — non pas par
régression mais par résolution de chemin : 91 × `src/AppHost/dovecot/dovecot.conf
introuvable`, 12 × `Assert.NotNull` dans les scans de sources (`RepoRoot()` rend
null), 4 × `src/Api/appsettings.json introuvable`. C'est bien plus large que les
« ~10 tests » que la mémoire de la forge annonçait, et **ces 107 rouges masquent
précisément les garde-fous d'architecture** : sans le tir en chemins standards,
la violation de task-291 introduite par la première version des tests serait
passée inaperçue jusqu'à la CI.

> ⚠️ **Constat sur le garde-fou de la forge** : `git push` sur `api-mail` a été
> **accepté** alors que `dotnet build` en chemins standards échouait sur les
> verrous. Le hook `verify-before-push.sh` n'a donc pas joué son rôle de
> barrière sur ce coup-ci. Hors périmètre de task-194, mais à regarder — c'est
> la seule vérification automatique avant la sortie du code.

### Passe qualité `/simplify` (§Q) — ce qui a été appliqué, ce qui a été écarté

Quatre revues en parallèle (reuse / simplification / efficacité / altitude).
**Appliqué** (commit `5fea456f`) :

- `LoadThreadLinkBatchesAsync` — **le point sur lequel deux revues
  indépendantes ont convergé** : après le portage, les deux chemins émettaient
  les mêmes trois requêtes, écrites deux fois, télémétrie comprise. Elles sont
  désormais définies une fois pour les deux, et la seule différence restante
  entre les appelants (la clé de déduplication) est visible comme telle.
- `ToThreadLink` — la projection du maillon était recopiée sur **quatre**
  requêtes ; ajouter `Id` avait demandé quatre modifications identiques.
- `IsDescendantOf(ThreadLink, rootId)` au lieu de deux `string?` consécutifs,
  que le compilateur laissait transposer — transposition qui échangeait
  l'égalité et la sous-chaîne.
- Doc XML de `ThreadLink` **qui mentait** : elle affirmait encore que
  `(FolderPath, Uid)` identifie une ligne, en citant un index supprimé par
  task-179. Corrigée, `Id` documenté, et l'asymétrie des clés signalée aux
  **deux** bouts (le chemin base ne disait rien du chemin IMAP — sans quoi
  « harmoniser » sa ligne passait pour un rangement).
- `PostgreSqlFixture.CreateContext(configure)` — l'incantation
  `UseNpgsql(…, o => o.UseVector())` était recopiée par chaque test devant
  observer le SQL.
- Décor de test : `SeedAsync` rend l'identifiant de racine (les deux autres
  champs du record étaient morts), le paramètre `sent` inutilisé dans 8 lambdas
  sur 9 devient une constante de classe, `CreateRepository` remplace trois
  copies, le littéral à caractères spéciaux n'est plus épelé trois fois.
- CA1861 (`conventions/csharp.md`) appliqué d'emblée sur le tableau littéral
  passé à `LogTo`.

**Écarté, et pourquoi** :

- **Paralléliser les trois requêtes** : elles partagent le `DbContext` mémoïsé
  du dépôt, qui n'est pas thread-safe — EF lève sur une seconde opération
  concurrente. Un `Task.WhenAll` serait une régression de fiabilité.
- **Projection plus étroite pour le comptage** (il n'a besoin ni de
  `FolderPath`, ni de `Uid`, ni de `SentDate`) : elle referait deux formes de
  maillon là où la passe vient d'en unifier une, pour quelques octets par ligne
  d'un lot déjà borné par le fil.
- **Resserrer `List<string?>` en `List<string>`** sur les helpers partagés :
  correct, mais la nullabilité vient du chemin base (`RootOf`) et le
  changement se propage à trois méthodes de ce chemin. Hors périmètre d'une
  passe qualité.
- **Mutualiser le décor de semis avec `ThreadCountConvergenceTests`** : ~65
  lignes dupliquées, dont l'invariant « le dossier s'appelle exactement
  `Sent` ». Réel, mais toucher le garde-fou anti-divergence de task-268 pendant
  la passe qualité de task-194 ajoute du risque à un fichier dont la stabilité
  est la raison d'être. **À reprendre dans une task de dette de test.**
- **`GetLatestMessageIdsPerThreadAsync` et `CollectThreadMessageIdsAsync`**
  épellent encore la règle de rattachement côté SQL, sous la forme
  `roots.Any(id => References.Contains(id))` que le doc de `ReferencesAnyOf`
  documente comme **non traduisible par le fournisseur InMemory**. Aucune n'a
  le défaut corrigé ici (la première est déjà bornée aux racines demandées).
  **Candidates identifiées pour la prochaine passe sur ce fichier.**
- **Cinq tests de caractérisation en un `[Theory]`** : la revue le proposait en
  signalant elle-même la contrepartie — chaque cas porte un « pourquoi » que la
  table effacerait.

### Mesure de charge avant/après — non exécutée

La comparaison p50/p95 `read_list` sur le banc des tasks 173/174 (§4 de la
tâche et DOD) **n'a pas été produite**. Elle est gated humainement par le
Manual Test Plan lui-même :

1. elle exige un banc isolé et une préparation de corpus dont « toute purge ou
   réinitialisation destructive nécessite une confirmation explicite » ;
2. elle exige la clé du banc **par l'environnement**, que la forge ne détient
   pas ;
3. elle exige un AppHost lancé sur le profil `https-load-test`, alors qu'un
   AppHost tourne déjà sur un autre profil sur cette machine ;
4. la jambe « avant » se tire sur le code **pré-correctif**, donc sur un
   `develop` re-checkouté, avec le même corpus et le même protocole de chauffe.

**Décision humaine du 2026-09-08** : la campagne est menée par l'humain **au
HAG**, sur la PR ouverte. Ce point du DOD reste donc explicitement **ouvert** —
il n'est ni retiré, ni réputé satisfait — et `/review` le signale dans le body
de la PR.

Le protocole exact à rejouer est celui du `## Manual Test Plan`, avec
`--thread-share > 0`, `CORPUS_THREAD_SHARE` égal à la part semée et
**`JOURNEY_THREAD_COUNTS=1`** (sans quoi on ne mesure que le court-circuit de
task-266). Ce qui est livré et mesuré ici est la **preuve structurelle** :
filtres du SQL exécuté, et lignes matérialisées insensibles aux messages
étrangers. La tâche l'annonçait comme le résultat attendu — « sans gain
prédéterminé » — mais le DOD demande en plus les chiffres du banc : ce point du
DOD reste donc **ouvert**.

## Sonar log

Analyse complète du 2026-09-08 sur la branche `fix/task-194-thread-counts-scoped-load`
(projet `healthplatform-api-mail`, analyse serveur `12:25:43Z`, build Release +
5 suites instrumentées OpenCover, `EXECUTION SUCCESS`).

### KPIs qualité — baseline → final

| Métrique | Baseline (`08:09Z`, avant task-194) | Final (`12:25Z`, avec task-194) | Δ |
|---|---|---|---|
| Bugs | 2 | 2 | 0 |
| Vulnérabilités | 0 | 0 | 0 |
| Code smells | 73 | 73 | 0 |
| Security hotspots | 15 | 15 | 0 |
| Couverture | 88,0 % | 88,0 % | 0 |
| Duplication | 0,3 % | 0,3 % | 0 |
| `ncloc` | 49 908 | 49 908 | 0 |
| Maintenabilité (`sqale_rating`) | A | A | — |
| Sécurité (`security_rating`) | A | A | — |
| Fiabilité (`reliability_rating`) | C | C | — |
| **Quality Gate** | **ERROR** | **ERROR** | inchangé |

Conditions du Quality Gate au tir final :

| Condition | Valeur | Verdict |
|---|---|---|
| `new_coverage` ≥ 80 % | 88,0 % | OK |
| `new_duplicated_lines_density` ≤ 3 % | 0,05 % | OK |
| `new_security_hotspots_reviewed` = 100 % | 0 % | **ERROR** |
| `new_violations` = 0 | 74 | **ERROR** |

### Phase 1 — new code : zéro dette introduite par task-194

**Aucun finding sur les fichiers de la task**, vérifié fichier par fichier :

| Fichier | Issues | Hotspots |
|---|---|---|
| `src/Infrastructure/Repository/MailRepository.cs` | 1 (voir ci-dessous) | 0 |
| `tests/mss.mail.integration.tests/Repository/ThreadCountsScopedLoadTests.cs` | **0** | 0 |
| `tests/mss.mail.integration.tests/Fixtures/PostgreSqlFixture.cs` | **0** | 0 |

Le finding unique sur `MailRepository.cs` est `csharpsquid:S138` (« méthode de
106 lignes ») sur **`LoadBulkContentLookupsAsync`**, ligne 1416 — une méthode que
task-194 **n'a pas touchée**, et hors new code period (`inNewCodePeriod` non
positionné). Ce n'est pas de la dette introduite ici ; la réduire est un
refactor d'une méthode étrangère à cette US (règle 6, périmètres isolés).

La convention `CA1861` (tableau littéral en argument) a été appliquée **d'emblée**
sur le nouveau code de test, avant analyse : `conventions/csharp.md` la donnait à
2 occurrences, et le new code period en compte 10 sur d'autres fichiers. La
boucle d'auto-amélioration a donc joué son rôle — aucune récidive sur du code
frais.

### Phase 2 — dette héritée : non engagée, et pourquoi

Le Quality Gate est `ERROR`, mais **aucune** des conditions en échec n'est
imputable à cette task. Provenance des 90 issues du new code period (dont les 74
comptées par `new_violations`) et des 15 hotspots `TO_REVIEW` :

| Fichier | Issues new-code | Hotspots |
|---|---|---|
| `tests/loadtest-k6/report.py` | 23 | 1 |
| `tests/loadtest-k6/lib/journey-model.js` | 14 | — |
| `tests/loadtest-k6/scenarios/journey.js` | 9 | 2 |
| `src/Application/Session/MailClientSession.cs` | 6 | — |
| autres (`AppHost.cs`, `IheXdmProcessingService`, `ContactRepository`, `MailServerDiscovery`, suites de tests…) | 38 | — |
| `src/Api/Program.cs`, `Dockerfile`, `BaseRepository.cs`, harnais k6 (`test_report_*.py`, `folders.js`, `mixed.js`) | — | 12 |
| **dont fichiers de task-194** | **0** | **0** |

Règles dominantes : `javascript:S1940` (13), `python:S3776` (13),
`external_roslyn:CA1861` (10), `csharpsquid:S125` (6), `python:S1192` (5).

C'est le piège documenté de ce poste : **la new code period englobe des tasks
déjà mergées** (le harnais de charge des tasks 173/174/195 en tête), donc un
`ERROR` du Quality Gate ne signifie pas qu'une task a introduit de la dette.
La provenance a été vérifiée avant de conclure, comme l'exige ce constat.

Phase 2 est donc **délibérément non engagée** — elle est best-effort et
optionnelle par playbook, et la traiter ici aurait signifié :

- modifier du Python et du JavaScript du harnais de charge, plus
  `MailClientSession.cs`, `AppHost.cs`, `Program.cs`, `BaseRepository.cs` — des
  fichiers **hors du module de cette US** (règle 6, « périmètres isolés ») et
  explicitement hors scope du task file ;
- faire exploser la PR bien au-delà des ~30 fichiers de la règle 5, en mélangeant
  une optimisation de requêtes avec du nettoyage de harnais de test.

**Ce n'est pas un skip silencieux** : la dette est ici chiffrée, localisée et
attribuée. Elle mérite sa propre task (nettoyage du harnais `loadtest-k6` +
revue des 15 hotspots), et les 12 hotspots du harnais devraient probablement
être marqués `SAFE` en lot plutôt que corrigés.

### Faits opérationnels relevés — le playbook était faux sur trois points

À consigner, parce que chacun coûte une analyse ratée :

| Point | Ce que dit `agents/sonar.md` | Mesuré ce jour |
|---|---|---|
| Port | `http://localhost:9000` (« corrigé le 2026-08-30 ») | **9001** — 9000 ne répond pas (`http_code 000`) |
| Version / propriété d'auth | 9.9.8 → `sonar.login` (mesuré le 2026-09-04) | **25.6.0.109173 → `sonar.token`** — sixième bascule du tableau |
| Clé de projet | `healthplatform-api-mail` | correcte, mais **`SONAR_PROJECT_KEY` de l'environnement vaut `healthplatform`**, un projet distinct dont la dernière analyse date du 2026-09-02 |

Le contrôle `curl /api/server/version` avant analyse est donc bien la seule
conduite tenable — la dernière ligne du tableau du playbook n'est jamais fiable.
Accessoirement, `Api/Mail/.env` a une ligne 70 qui casse un `source` (`xpui:
command not found`) sans conséquence ici, mais qui polluera tout script qui la
source.

## PRs

- `api-mail` : **https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/223**
  — label `awaiting-human-merge`, `MERGEABLE`. Branche
  `fix/task-194-thread-counts-scoped-load`, fusionnée avec `origin/develop`
  (`da2f2b65`, task-183) sans conflit avant validation.
- `dtos-mss` : **aucune PR** — la branche a été créée par `/start`
  (auto-inclusion) mais l'US ne change aucun contrat : 0 commit, donc rien à
  publier et aucun consommateur à bumper.
- `client-angular`, `client-mobile`, `client-blazor` : non concernés (US
  backend-only assumée et justifiée dans le task file).

## Code Review Summary

**Verdict : APPROVED** — 3 fichiers, 0 blocage, 3 suggestions non bloquantes.

Vérifié à la revue, au-delà de ce que la passe qualité couvre (elle est
quality-only par contrat) :

- **Équivalence sémantique lot par lot** : toute ligne que l'ancien code comptait
  est chargée par la nouvelle union (`InReplyTo == root` → lot « réponses
  directes », `References.Contains(root)` → lot « citations »), et le prédicat de
  comptage est le même helper partagé. La déduplication par `Mail.Id` reproduit
  le comptage de lignes de l'implémentation à requête unique.
- **Sécurité** : aucun SQL concaténé (arbre d'expression + paramètres, échappement
  délégué au provider), aucun secret, aucune validation d'entrée contournée.
- **Données de santé** : **0 nouveau log**. `EnableSensitiveDataLogging` n'apparaît
  que dans le contexte d'observation **du test**, jamais en production
  (vérifié : 0 occurrence dans `src/`).
- **task-183 intacte** : le diff de la task ne touche **aucune** ligne INS/OID, et
  les marqueurs `InsIdentityDomain` / `PatientInsOid` sont toujours présents après
  la fusion.
- **Performance** : 3 requêtes bornées, séquentielles à dessein (le `DbContext`
  mémoïsé du dépôt n'est pas thread-safe) ; comptage en mémoire O(racines ×
  descendants) inchangé et borné par la page.

Suggestions consignées dans le body de la PR : les deux dernières copies SQL de
la règle de rattachement (`GetLatestMessageIdsPerThreadAsync`,
`CollectThreadMessageIdsAsync`), le `S138` pré-existant, et la mutualisation du
décor de semis avec `ThreadCountConvergenceTests`.

## Timings

*(généré par `tools/timing/report.sh --task task-194 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 2 min 15 s | — | — | — | — |
| /develop | ok | 1 h 52 min | 4 (1 min 36 s) | 7 (5 min 18 s) | — | api-mail 4B/7T |
| /sonar | ok | 11 min 21 s | 1 (27 s) | 5 (3 min 30 s) | — | 1 itération(s), api-mail 1B/5T |
| /lint-angular | skipped | 1.9 s | — | — | — | client-angular non touche (Repos: api-mail) |
| /lint-mobile | skipped | 2.2 s | — | — | — | client-mobile non touche (Repos: api-mail) |
| /verify-visual | skipped | 1.9 s | — | — | — | aucun ecran mobile touche (US backend-only, api-mail) |
| /review | ok | 5 min 17 s | 1 (26 s) | 1 (1 min 41 s) | — | api-mail 1B/1T |
| **Total cycle** | | **2 h 11 min** | **6 (2 min 31 s)** | **13 (10 min 30 s)** | **0 (0.0 s)** | |
