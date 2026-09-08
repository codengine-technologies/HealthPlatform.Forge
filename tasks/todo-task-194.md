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
