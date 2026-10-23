# archived-task-386.md — Annuaire Santé : une recherche par nom et lieu trouve le praticien, et dit quand elle est incomplète

**Repos**: api-mail, client-angular, client-mobile, client-blazor
**Dependencies**: — (aucune)
**Epic**: E009
**Single frontend**: false
**Priorité**: **2** — un médecin qui cherche un confrère par nom dans un département dense obtient « aucun praticien » alors que le confrère existe, sans aucun signe que la recherche a échoué.

> **Origine.** Constat dans Seq le 2026-10-22 (recherche dans l'annuaire depuis weda2, boîte de formation), après
> task-379. Décisions humaines au cadrage (`/po`, 2026-10-22) : le médecin voit un message **« résultats incomplets »**
> quand l'annuaire n'a pas pu être interrogé jusqu'au bout ; en cas de saturation, api-mail **attend et réessaie, dans
> une limite de temps**, plutôt que de répondre vite avec un résultat partiel.
>
> **Décisions humaines après la première `/review` (2026-10-23, `questions/task-386.md`).**
> 1. **Aucun appel abouti, quelle qu'en soit la cause (429 compris) → 503 `DIRECTORY_UNAVAILABLE`.** Le 200
>    `incomplete` n'existe que lorsqu'au moins un appel a répondu.
> 2. **client-blazor entre dans la task** : mêmes règles de critères que l'API, issue lue dans l'en-tête, messages
>    d'incomplétude, d'annuaire indisponible et de refus (400) au lieu d'une liste vide silencieuse.
> 3. **Spécialité + organisation sans lieu : acceptée. Organisation seule : au moins 3 caractères** (API et trois
>    clients), comme le nom de famille.

## Ce qui est établi (2026-10-22)

- **Le cas observé** (trace Seq `dd87971f…`) : recherche nom « dup » + code postal « 18 ».
  - Étape 1 : 200 établissements du Cher trouvés.
  - Étape 2 : 100 appels à l'annuaire en 3,4 s, un par établissement (`SearchStrategyBase.EnrichWithPractitionersAsync`, plafond `Take(100)`), soit ~30 appels/s.
  - L'annuaire répond **429 « Rate limit exceeded! You reached the limit of 17 requests per 1 seconds »** en rafale ; chaque refus est journalisé en `Warning` et l'établissement est **sauté**.
  - 54 praticiens remontés, **0** après le filtre par nom fait en mémoire ; réponse **200**, « 0 praticiens trouvés », en 4,1 s.
- **Défauts de conception, indépendants du quota** :
  - `NameWithLocationSearchStrategy` part du **lieu** (établissements du code postal) puis filtre par **nom** en mémoire : seuls 100 établissements sur 200 sont parcourus, donc un praticien rattaché au-delà n'est jamais trouvé, quel que soit son nom.
  - Aucun limiteur de débit vers l'annuaire, aucune reprise sur 429 (`Retry-After`), alors que le quota vaut pour **toute l'application** (une clé d'API) et que plusieurs recherches simultanées se l'arrachent.
  - Un refus de l'annuaire est **avalé** : un 200 vide est indiscernable d'un vrai « personne ne correspond ».
- Les autres stratégies « établissement d'abord » (`LocationSearchStrategy`, `OrganizationSearchStrategy`, `SpecialtySearchStrategy`, `CombinedSearchStrategy` — à confirmer au `/develop`) passent par le même enrichissement et partagent le défaut de débit.
- **Consommateurs** de `GET /api/v1/Directory/practitioners/search` (aujourd'hui `IReadOnlyList<PractitionerDto>`) : weda2 (`mss-api.service.ts`), mobile (`mss-api.service.ts`) et **client-blazor** (`DirectoryService.cs`, non listé : le changement de contrat doit lui rester **compatible**).

## Ce que disent l'ANS et les clients existants (recherche du 2026-10-22)

- **Quota officiel** : « L'application Gravitee applique une limitation de **17 appels par seconde par application** pour l'API FHIR Annuaire Santé » (doc ANS, `get-api-key.md`). Le quota est porté par la **clé d'API**, donc partagé par **toutes les instances** d'api-mail (5 réplicas en dev) : un limiteur par processus ne suffit pas, il faut un budget global (Redis) ou une part par réplica.
- **Regrouper au lieu de boucler** : `PractitionerRole?organization=` accepte une liste d'identifiants (OU FHIR), et l'API accepte `POST …/_search` quand l'URL devient trop longue (doc ANS, `api-basics.md`). 100 appels « un par établissement » peuvent devenir 2 ou 3 appels.
- **Chercher par nom d'abord** : `Practitioner?name:family=…` (modificateurs `:contains` / `:exact`) avec `_revinclude=PractitionerRole:practitioner` ramène les praticiens et leurs activités en un appel ; leurs établissements s'obtiennent en un appel groupé (`PractitionerRole?practitioner=a,b,…&_include=PractitionerRole:organization`) pour filtrer par code postal ou ville. Pagination par le lien `next`, 50 éléments par page par défaut (`_count`).
- **Reprise sur 429, pratique observée** (`cturkieh/france-data-mcp`, `src/core/http.ts`) : sur 429, respecter `Retry-After` (5 s par défaut), backoff exponentiel avec gigue, 4 tentatives ; 5xx repris, autres 4xx non ; résultat **discriminé** (« introuvable » ≠ « API indisponible ») au lieu d'un `null` silencieux — l'équivalent de l'indicateur « incomplet ».
- **api-mail aujourd'hui** : le `FhirClient` est construit à chaque requête (`AnnuaireSanteService`, service scoped), sans `HttpClient` partagé ni pipeline de résilience. `Microsoft.Extensions.Http.Resilience` est déjà utilisé ailleurs dans le dépôt (proxy PSC, révocation) ; un constructeur de test accepte déjà un `FhirClient` à `HttpMessageHandler` simulé (task-032bis), utilisable pour le test d'intégration.
- **Adresses** : l'ANS précise que `Organization` peut porter des e-mails de **contact** qui ne sont **pas** des BAL MSSanté. Le parseur actuel ne lit les e-mails que de `Practitioner` et `PractitionerRole` (BAL personnelles et cabinet) : à préserver si la stratégie change.

## Mesures sur l'API réelle (2026-10-22)

Fiche complète : [`Docs/annuaire-sante-fhir-api.md`](../Docs/annuaire-sante-fhir-api.md). À retenir pour cette task :

- **429 sans `Retry-After`** ni en-tête de quota : la reprise attend ~1 s ; la régulation est à notre charge.
- **`POST _search` inopérant** (500) : rester en `GET`, **lots de 200 identifiants** (414 au-delà de ~3 000 caractères).
- `_id=` vide **ignoré** (renvoie tout) ; paramètre inconnu → **500** ; `:contains` → 14 s ; `_include:iterate` non supporté.
- Approche « nom d'abord » validée sur le cas réel « dup » + « 18 » : **22 praticiens en 29 appels**, ou **1 praticien avec BAL en 7 appels** avec `mailbox-mss:contains=%40` — contre 0 aujourd'hui en 101 appels.
- Arbitrage à poser au `/develop` : filtrer par défaut sur les praticiens **ayant une BAL MSSanté** (seuls joignables par la messagerie) et exiger un nom d'au moins N caractères, ou borner les pages et signaler l'incomplétude.

## Analyse du code actuel (2026-10-22, mesures sur l'API réelle)

Sept stratégies (`SearchStrategyFactory`, première qui accepte) ; coût et fiabilité par cas :

| Critères saisis | Stratégie | Appels | Défaut mesuré |
|---|---|---|---|
| RPPS seul | `RppsSearchStrategy` | 1 | ✅ correct (`identifier`, `_revinclude`) |
| RPPS + autre critère | `NameSearchStrategy` › `practitioner.identifier` | 1 | **paramètre chaîné → 504 après 30 s**, liste vide |
| Nom seul | `NameSearchStrategy` | 1 + 20 | **N+1** (un appel d'activités par praticien) ; 50 lus, **20 enrichis** quel que soit le total (« DUPONT » : 1 650) |
| Nom + lieu | `NameWithLocationSearchStrategy` | 1 + 100 | lieu d'abord, **100 établissements sur 200**, 429 en rafale (cas Seq : 0 au lieu de **22**) |
| Lieu seul | refusé par `ValidateSearchCriteria` | — | (la stratégie `LocationSearchStrategy` existe, inatteignable : 101 appels + un chaîné à 30 s) |
| Spécialité (± lieu) | `SpecialtySearchStrategy` › `PractitionerRole?role=SMxx` | 1 | **toujours 0** : la spécialité est sur `Practitioner.qualification-code`, pas sur `role` |
| Organisation | `OrganizationSearchStrategy` | 1 + ≤ 50 | `name:contains` lent + un appel par établissement |
| **« Avec BAL MSSanté » coché** + nom, lieu ou organisation | `CombinedSearchStrategy` (toutes les autres excluent `HasMssAddress`) | 1 + 1 + 100 | `practitioner.family` chaîné → **504 après 30 s**, puis repli « lieu d'abord » ; sans lieu, ce repli lit 200 établissements **arbitraires** → résultat aléatoire ou vide |

Défauts transverses :
- **Paramètres chaînés** (`organization.*`, `practitioner.*`) : non déclarés par le serveur, **504 après 30 s** (mesuré trois fois). Utilisés par 3 stratégies.
- Filtre BAL fait **en mémoire** (`Emails.Any(contains "mssante.fr")`) au lieu de `mailbox-mss:contains=@` côté serveur.
- `FhirBundleParser.ParsePractitionerBundle` ne garde que **la première activité** d'un praticien (`g.First()`) : établissement et lieu d'une seule activité ; un filtre de lieu sur les autres est impossible.
- `FhirClient` neuf à chaque requête, **délai de 120 s** par appel, aucune régulation, aucune reprise ; erreurs avalées en `Warning`, un 200 vide indiscernable de « personne ».
- Aucun cache des réponses, alors que les données sont publiques et que la saisie relance des recherches proches.

## Conception cible

Deux pivots, plus le RPPS — à la place des sept stratégies :

1. **RPPS** : `Practitioner?identifier={rpps}&_revinclude=PractitionerRole:practitioner` (les trois formats d'identifiant sont acceptés). 1 appel.
2. **Praticien d'abord** (nom saisi) : `Practitioner?family={nom}[&given={prénom}][&qualification-code={spé}][&mailbox-mss:contains=%40]&_revinclude=PractitionerRole:practitioner&_count=1000`, pages bornées ; si lieu ou organisation : identifiants d'établissement par **lots de 200** → `Organization?_id={lot}[&address-postalcode][&address-city][&name]`, puis on garde les praticiens dont **une** activité y figure. Mesuré : nom + lieu « dup » / « 18 » = 29 appels (22 praticiens), 7 avec BAL (1 praticien).
3. **Établissement d'abord** (pas de nom : lieu et/ou organisation, ± spécialité) : `Organization?{address-postalcode|address-city|name}&_revinclude=PractitionerRole:organization&_count=1000` (mesuré : Bourges = 826 établissements + 1 264 activités en **1 appel de 0,7 s**), puis `Practitioner?_id={lot de 200}[&qualification-code][&mailbox-mss:contains=%40]` (filtres côté serveur, mesurés). ~1 + N/200 appels.

Règles d'appel : `GET` seulement ; jamais de chaînage, de `:contains` sur un nom, de `POST _search`, de liste `_id` vide ; lots ≤ 200 identifiants.

Socle d'accès : `HttpClient` partagé (`IHttpClientFactory`) passé au `FhirClient`, avec un `DelegatingHandler` qui :
- prend un jeton dans un **seau partagé entre instances** (Redis, ~15 appels/s pour la clé) avant chaque appel ;
- sur 429 (sans `Retry-After`), attend ~1 s + gigue et réessaie (3 tentatives) ;
- respecte une **échéance par recherche** (~10 s, `CancellationToken`) et un délai par appel court (~10 s au lieu de 120 s).

Résultat : la liste **et** une issue — complète, ou incomplète avec sa raison (quota, échéance, pages bornées, plafond de lot) — portées jusqu'à l'écran (périmètre 3). Le parseur garde **toutes** les activités d'un praticien et affiche celle qui correspond au lieu demandé.

Décisions humaines (2026-10-22) :
- **« Avec BAL MSSanté » coché par défaut** dans la recherche d'annuaire de weda2 et du mobile (seuls ces praticiens sont joignables) ; le médecin peut le décocher.
- **Longueur minimale du nom : 3 caractères** (aujourd'hui 2), valeur en configuration. « dup » + BAL = 989 praticiens, 7 appels.
- **Spécialité seule refusée : un lieu est exigé** (« SM54 » = 8 897 praticiens), avec le même message que pour un lieu seul.
- **Pas de cache** des réponses de l'annuaire.

## Objective

Qu'une recherche dans l'Annuaire Santé par **nom et lieu** trouve le confrère quand il existe, même dans un département
dense ; qu'api-mail **respecte le quota** de l'annuaire et **réessaie** quand il est saturé, dans une limite de temps ;
et que le médecin **soit prévenu** quand la recherche n'a pas pu aller jusqu'au bout, au lieu de lire « aucun résultat ».

### Périmètre

1. **Recherche fiable pour toutes les combinaisons de critères** (api-mail), selon la « Conception cible » ci-dessus : nom (± prénom, lieu, organisation, spécialité, BAL), RPPS, lieu ou organisation (± spécialité, BAL). En particulier : un praticien du bon nom exerçant dans le lieu demandé est trouvé quel que soit le nombre d'établissements du lieu ; la spécialité ramène des praticiens ; cocher « avec BAL MSSanté » ne dégrade plus la recherche.
2. **Quota respecté** (api-mail) : débit vers l'annuaire limité sous le quota de la clé d'API, **partagé par toutes les instances** d'api-mail et toutes leurs recherches ; appels regroupés plutôt qu'un appel par établissement ; sur un refus pour saturation, nouvel essai après le délai indiqué par l'annuaire. Durée totale d'une recherche **bornée** (ordre de grandeur : 10 s ; valeur exacte en configuration).
3. **Résultat incomplet signalé** :
   - api-mail : le **corps de la réponse reste une liste** de praticiens (client-blazor la désérialise telle quelle : passer à un objet compilerait mais casserait Blazor à l'exécution) ; l'issue passe par un **en-tête de réponse** (ex. `X-Directory-Search-Outcome: complete | incomplete;reason=quota|deadline|pages|unavailable`), exposé au CORS (`Access-Control-Expose-Headers`) pour weda2.
   - **Annuaire injoignable** (aucun appel n'a abouti : 5xx, 504, délai dépassé) : **503** typé (`UnavailableException`, code `DIRECTORY_UNAVAILABLE`, RFC 7807), jamais un 500 ni un 200 vide ; si une partie a abouti : 200 + issue `incomplete`.
   - weda2 et mobile : les résultats obtenus restent affichés, accompagnés d'un message « La recherche n'a pas pu être menée jusqu'au bout. Précisez le nom ou la ville, ou réessayez dans un instant. » ; sur 503 : « L'annuaire santé est momentanément indisponible. Réessayez dans un instant. » ; une recherche complète sans résultat garde « Aucun praticien trouvé ».
4. **Journaux** : un refus de l'annuaire n'est plus une suite d'avertissements par établissement, mais un évènement par recherche (stratégie, nombre de refus, issue complète / incomplète), sans le nom recherché en clair.

5. **Saisie guidée** (api-mail, weda2, mobile) : « avec BAL MSSanté » coché par défaut ; nom de moins de 3 caractères et spécialité sans lieu refusés avec un message clair (400 côté api-mail, message sous le formulaire côté écrans).

Hors périmètre :
- client-blazor (reste compatible, n'affiche pas le message) ;
- cache des réponses de l'annuaire (décision humaine : non).

### Filet de tests — pourquoi au-delà des cas nominaux

Les défauts constatés venaient tous d'**hypothèses fausses sur l'API réelle** (chaînage, `role`, `POST _search`, quota),
qu'un faux annuaire complaisant aurait laissées vertes. Le filet a donc trois couches :
1. **Faux annuaire fidèle** (tests d'intégration) : il reproduit les comportements mesurés (`Docs/annuaire-sante-fhir-api.md`) et **échoue bruyamment** sur tout appel interdit, au lieu de répondre poliment.
2. **Test de contrat contre l'API réelle**, hors CI (déclenché à la main ou planifié, clé d'API requise, au plus 20 appels espacés) : il revérifie chaque hypothèse dont dépend l'implémentation. Un écart = l'ANS a changé quelque chose, à traiter avant la mise en production.
3. **Tests d'intégration de bout en bout** sur la route, cas par cas (ci-dessous).

## Gherkin

```gherkin
Feature: Search the national health directory by name and place

  Scenario: A colleague practising in a busy area is found by name and place
    Given a doctor looking for a colleague who practises in a department with many health facilities
    When the doctor searches the directory by the colleague's last name and the department
    Then the colleague appears in the results

  Scenario: The directory is briefly overloaded
    Given the national directory is briefly refusing requests because it is overloaded
    When the doctor searches by name and place
    Then the search waits and tries again
    And the colleague appears in the results once the directory answers

  Scenario: The directory cannot be fully searched in time
    Given the national directory keeps refusing requests
    When the doctor searches by name and place
    Then the results found so far are shown
    And the doctor is told the search could not be completed and is invited to refine it or try again

  Scenario: The directory is unavailable
    Given the national directory does not answer at all
    When the doctor searches by name and place
    Then the doctor is told the directory is temporarily unavailable and invited to try again
    And the doctor is never told that no practitioner was found

  Scenario: A colleague working in two places is found in the place searched
    Given a colleague who practises in two places
    When the doctor searches by the colleague's name and the second place
    Then the colleague appears with the facility of that place

  Scenario: Only reachable colleagues are proposed by default
    Given a doctor opening the directory search
    Then the option to keep only colleagues with a secure health mailbox is already selected
    And the doctor can clear it to see every practitioner

  Scenario: A search too broad to be useful is refused
    When the doctor searches with a last name of fewer than three letters
    Or searches by specialty without a place
    Then the doctor is told which criterion to add
    And no search is run

  Scenario: Nobody matches
    Given the directory answers every request
    When the doctor searches for a name nobody has in that place
    Then the doctor is told no practitioner was found
    And no warning about an incomplete search is shown
```

## Definition of Done

- [ ] Build et tests verts : api-mail, weda2, client-mobile, client-blazor (contrat de la route inchangé : aucun changement de `dtos-mss` requis)
- [ ] **Bloquants de la première `/review`** (`questions/task-386.md`) corrigés : une recherche incomplète et vide n'affiche jamais « Aucun praticien trouvé » (weda2, mobile, Blazor) ; une virgule (ou `|`, `$`, `\`) dans un critère texte ne devient pas un OU FHIR — refus 400, aucun appel ; le cas « dup » + « 18 » mesuré une fois sur l'API réelle sous l'échéance (sinon lots en parallélisme borné ou échéance relevée), mesure consignée au `## Develop log`

**Faux annuaire fidèle** (`tests/…`, partagé par les tests d'intégration) :
- [ ] reproduit : `family` / `given` en « commence par » insensible à la casse ; `_revinclude=PractitionerRole:practitioner` ; `_include=PractitionerRole:*` ; `Organization?…&_revinclude=PractitionerRole:organization` ; `_id=a,b,c` combinable avec `address-postalcode` / `address-city` / `name` / `qualification-code` / `mailbox-mss` ; `_count` et pagination par lien `next`
- [ ] reproduit les pièges : paramètre chaîné → 504 ; `POST …/_search` → 500 ; paramètre inconnu → 500 ; URL > 3 000 caractères → 414 ; `_id=` vide → tout le jeu ; 429 **sans** `Retry-After`
- [ ] enregistre chaque appel ; tout appel interdit (chaîné, `:contains` sur un nom, `POST _search`, `_id` vide, URL > 3 000) **fait échouer le test** qui l'émet
- [ ] un test du faux lui-même par piège (le faux qui répondrait « poliment » est attrapé)

**Test de contrat contre l'API réelle** (hors CI, catégorie dédiée, clé lue dans la configuration locale, ≤ 20 appels espacés) :
- [ ] vérifie : paramètres et `_revinclude` / `_include` utilisés acceptés ; `family` en « commence par » ; `_id` en lot combiné à un filtre de lieu et à `qualification-code` / `mailbox-mss` ; `Organization?…&_revinclude=PractitionerRole:organization` ; pagination `next` ; un lot de 200 identifiants accepté ; les trois formats d'identifiant RPPS
- [ ] joué une fois au `/develop`, résultat consigné au `## Develop log` ; procédure de lancement décrite dans `Docs/annuaire-sante-fhir-api.md`

**Tests d'intégration de bout en bout** pour `GET /api/v1/Directory/practitioners/search` (vraie route, vrai service, faux annuaire fidèle, Redis du fixture), vus rouges (règle 1b) :
- [ ] **une combinaison de critères par test** — RPPS ; nom ; nom + prénom ; nom + lieu ; nom + organisation ; nom + spécialité ; organisation ; lieu + spécialité ; chacune avec et sans « avec BAL » — : bons praticiens, pivot attendu, **nombre d'appels plafonné** et assertion qu'aucun appel interdit n'a été émis
- [ ] nom + lieu avec plus de 200 établissements dans le lieu, praticien rattaché au-delà : il est dans la réponse, issue `complete`
- [ ] plus de 200 identifiants à filtrer : **plusieurs lots**, aucune URL au-delà de 3 000 caractères ; liste d'identifiants vide : **aucun appel**
- [ ] pagination : les pages `next` sont suivies ; au plafond de pages, réponse avec issue `incomplete;reason=pages`
- [ ] praticien exerçant dans deux lieux, le lieu demandé sur sa **seconde** activité : trouvé, établissement affiché = celui du lieu demandé
- [ ] activité sans établissement : exclue d'un filtre de lieu, présente sans filtre de lieu
- [ ] 429 (sans `Retry-After`) puis réponse : résultats complets, nouvel essai après ~1 s, issue `complete`
- [ ] 429 persistant après au moins une réponse : 200 avec les résultats obtenus, issue `incomplete;reason=quota` ; **429 dès le premier appel, aucune réponse : 503 `DIRECTORY_UNAVAILABLE`** (décision du 2026-10-23) ; échéance de la recherche respectée, mesurée avec une horloge simulée (`TimeProvider`), sans attente réelle
- [ ] annuaire en 5xx / 504 / délai dépassé sans aucun appel abouti : **503** RFC 7807 code `DIRECTORY_UNAVAILABLE` ; en partie abouti : 200 + issue `incomplete`
- [ ] recherche annulée par le client (déconnexion) : plus aucun appel émis ensuite
- [ ] aucun praticien ne correspond, annuaire disponible : liste vide, issue `complete`
- [ ] nom de 2 caractères → 400 (longueur minimale) ; spécialité sans lieu → 400 (lieu exigé) ; organisation seule de moins de 3 caractères → 400 ; spécialité + organisation sans lieu → acceptée ; aucun appel à l'annuaire dans les cas refusés
- [ ] **compatibilité client-blazor** : le corps de la réponse se désérialise en `IReadOnlyList<PractitionerDto>` exactement comme avant ; l'issue n'est lue que dans l'en-tête, lui-même exposé au CORS
- [ ] journaux de la recherche capturés : le nom recherché n'y apparaît pas ; un seul évènement de synthèse par recherche (stratégie, appels, refus, issue)

**Limiteur et reprise** :
- [ ] N recherches simultanées sur **deux instances** partageant le même Redis : jamais plus d'appels par seconde que la limite configurée (horloge simulée)
- [ ] le cas observé (« dup » + « 18 ») fait au plus 30 appels sans BAL et 8 avec BAL (mesures du 2026-10-22), contre 101 aujourd'hui
- [ ] **client-blazor** (`DirectorySearchDialog`, `DirectoryService`) : mêmes règles de critères que l'API (nom ≥ 3, prénom seul refusé, spécialité sans lieu ni organisation refusée, organisation seule ≥ 3, lieu seul refusé) avec leur motif et sans requête ; issue lue dans `X-Directory-Search-Outcome` → message d'incomplétude ; 503 `DIRECTORY_UNAVAILABLE` → « annuaire indisponible » ; 400 → motif du serveur ; « Aucun praticien trouvé » seulement après une recherche complète et vide ; « avec BAL MSSanté » coché par défaut ; tests rouges d'abord
- [ ] Tests de composant rouges d'abord (weda2 et mobile) : issue `incomplete` (en-tête) → résultats affichés + message ; 503 `DIRECTORY_UNAVAILABLE` → message « annuaire indisponible » ; réponse complète vide → « Aucun praticien trouvé », sans message d'incomplétude ; formulaire ouvert avec « avec BAL MSSanté » coché ; nom < 3 caractères ou spécialité sans lieu → message, aucune requête
- [ ] Scénario **E2E-CONTACT-001** versionné dans `Api/Mail/e2e/scenarios.yml` (v2, mode `humain` : annuaire national réel), attendu étendu au message d'incomplétude ; tests des deux clients mis à la version
- [ ] Aucun nom recherché ni donnée de praticien en clair dans les nouveaux journaux ; un seul évènement par recherche pour les refus de l'annuaire

## Manual Test Plan

1. weda2 puis mobile, Contacts › Annuaire : nom « dup » (ou un nom courant) + code postal « 18 » → résultats en quelques secondes, aucune rafale de refus dans Seq.
2. Chercher par nom + département un confrère connu exerçant dans un grand établissement du département → il est trouvé.
3. Lancer en même temps trois recherches larges (trois onglets) → toutes aboutissent ; si l'une est incomplète, le message s'affiche avec les résultats obtenus.
4. Rechercher un nom inexistant → « Aucun praticien trouvé », sans message d'incomplétude.
5. Seq : un évènement par recherche, issue complète / incomplète, nombre de refus, sans le nom recherché.
6. Couper l'accès à l'annuaire (clé d'API vide ou URL invalide en local) → « L'annuaire santé est momentanément indisponible », jamais « Aucun praticien trouvé ».
7. Blazor (si encore utilisé) : une recherche d'annuaire affiche toujours ses résultats.
8. Lancer le test de contrat contre l'API réelle → toutes les hypothèses vérifiées.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif de fiabilité de l'intégration Annuaire Santé
- **Exigences DSR honorées** : RG-E009-021 (SC.MSS/CONF.20 — recherche d'une adresse MSSanté dans l'Annuaire Santé) et RG-E009-023 (ANN/va1.01 — intégration Annuaire santé.fr par API FHIR), déjà implémentées : fiabilisées, non modifiées
- **INS** : non applicable — recherche de professionnels de santé, aucun patient manipulé
- **Authentification PS** : inchangée (PSC, session api-mail existante) ; la clé d'API de l'Annuaire Santé reste côté serveur
- **Habilitations** : inchangées — identification des correspondants par l'annuaire (RPPS)
- **Interop CI-SIS** : FHIR R4 — API Annuaire Santé de l'ANS (`Practitioner`, `PractitionerRole`, `Organization`) ; respect du quota d'appels de l'API (429, `Retry-After`)
- **Tracé PGSSI-S** : inchangé pour les accès ; journal technique par recherche (stratégie, issue, nombre de refus), sans nom recherché
- **Consentement patient** : non applicable — aucune donnée patient
- **Référentiels métier** : annuaire santé (RPPS, Annuaire Santé ANS)
- **Hébergement HDS** : non applicable — données publiques de professionnels de santé
- **AIPD / impact RGPD** : inchangé — données publiques de l'annuaire, pas de nouveau traitement
- **MSSanté** : inchangé — l'annuaire ne publie que des adresses MSSanté

## Develop log

**2026-10-22 — `/develop` (forge).** api-mail : `9230fffd` (fix) + `e42dc0c4` (passe qualité) ; client-mobile :
`05189fc` + `571b29d` ; client-angular : code seul, non commité (voir plus bas). Les deux branches poussées.

### Ce qui est livré
- **api-mail** — deux pivots (praticien d'abord / établissement d'abord), `AnnuaireQuery` qui refuse avant tout
  appel ce que la passerelle sert mal, lots `_id` coupés à 200 identifiants **et** 3 800 caractères d'URL, filtre
  « avec BAL » en mémoire sur la fiche et les activités, budget d'appels partagé Redis (15/s) + reprise sur 429
  (~1 s + gigue, 3 essais), échéance 10 s (`TimeProvider`), issue dans `X-Directory-Search-Outcome` (exposé au
  CORS), 503 `DIRECTORY_UNAVAILABLE`, 400 avant tout appel pour les recherches trop larges, un seul évènement de
  synthèse par recherche (critères présents, jamais leurs valeurs ; abandon → `Issue=cancelled`). Stratégies et
  leurs tests supprimés ; l'annuaire sort de l'exemption de `SensitiveLogTemplateScanTests`.
- **client-mobile / weda2** — issue lue dans l'en-tête, message d'incomplétude au-dessus des résultats, « annuaire
  indisponible » à la place de « aucun praticien », « Possède une adresse MSSanté » coché par défaut (interrupteur
  ajouté sur mobile, où la BAL était forcée), critères trop larges refusés avec leur motif et sans requête.
- **E2E-CONTACT-001 v2** (mode humain) dans `Api/Mail/e2e/scenarios.yml`, test mobile mis à la version. weda2 n'a
  pas de test pour ce scénario (sa suite e2e est headless seulement : « 👤 non joué (humain) » à la parité).
- **Docs** — `Docs/annuaire-sante-fhir-api.md` : limite d'URL mesurée, filet de tests, procédure du test de contrat.

### Écarts à la DoD (à arbitrer en `/review`)
1. **« dup » + « 18 » avec BAL : ≤ 15 appels, pas 8.** Le filtre serveur `mailbox-mss` ne voit que la fiche et perd
   un porteur de BAL sur cinq (BAL portée par une activité seulement) : le filtre est fait en mémoire, donc les 7
   pages de praticiens sont lues dans tous les cas. Mesuré sur le faux fidèle : 30 appels sans BAL, ~14 avec.
2. **Limite d'URL : 3 800 caractères, pas 3 000.** Mesure affinée sur la passerelle : 4 092 acceptés, 4 177 → 414
   (limite à 4 096). Le client FHIR encode les virgules `_id` en `%2C` (3 caractères), ce qui portait un lot de
   200 identifiants réels à ~3 400 caractères : avec une règle à 3 000, « dup » + « 18 » passait à 33 appels.
3. **Prénom seul refusé (400)** — le nom de famille est exigé dès qu'un nom est saisi.

### Constats en cours de route
- `PractitionerRole.code` porte le genre d'activité / mode d'exercice / fonction (GENR01, S, FON-33), **jamais la
  profession** : aucun repli sur l'activité pour la profession affichée.
- `role` est un paramètre **connu** de `PractitionerRole` (0 résultat avec un code SMxx), pas une erreur 500.
- `%2C` est bien lu comme un OU par la passerelle (vérifié), et le client FHIR ne le ré-encode pas.

### Tests
- api-mail, suite complète : 6 708 verts (domain 195, infrastructure 695, application 3 597, api 1 276,
  intégration 949 + 16 ignorés préexistants). Annuaire : 104 tests unitaires (dont un auto-test par piège du faux
  annuaire), 47 tests de route / CORS / budget partagé.
- weda2 `libs/mss` : 991 verts ; client-mobile : 1 154 verts. Rouges vus avant implémentation (module absent).
- **Preuves par mutation (règle 1b)**, chacune rougit au moins un test d'intégration, code restauré par copie :
  BAL sur la fiche seule ; virgule comptée 1 caractère ; annulation traitée en panne ; échec non signalé ; sans
  reprise sur 429 ; budget par instance au lieu de Redis ; jamais de 503 ; première activité au lieu de celle du
  lieu.
- **Test de contrat contre l'API réelle** (`AnnuaireSanteContractTests`, hors CI) : joué, **vert, 14 appels** —
  `family` en « commence par » + `_revinclude` ; pagination `next` ; RPPS sous ses trois formes ; Organization
  18000 + `_revinclude` (250 établissements, 346 activités) ; 200 `_id` + code postal filtrés côté serveur ;
  `qualification-code` sur un lot mixte → exactement les SM54 ; `mailbox-mss` → BAL sur la fiche ; paramètre
  inconnu → 500 ; URL ≤ 4 000 acceptée, ≥ 4 200 → 414.

### Passe qualité (§Q, `/simplify`, 4 angles)
Appliqué : URL mesurée telle qu'envoyée ; moteur allégé (état d'échec déduit, `Note(Limit)` en double, aides
factorisées, un seul `TryAsync`) ; plus aucun envoi ni place de budget après l'échéance ; `FormatAddress` / `Emails`
dans le parseur ; réutilisation de `CapturingLogger`, `FakeTimeProvider`, des aides de codes ProblemDetails des
deux clients ; une seule règle `directoryCanSearch` ; `_id` du faux lu une fois. Écarté : paramètres morts de
`MapPractitioner` (API publique couverte par des tests existants) ; double réglage du délai d'appel
(`FhirClientSettings` / `HttpClient`, comportement du client FHIR non vérifié) ; longueur minimale en constante
plutôt qu'en option (la décision dit configurable) ; reprise 429 via `Http.Resilience` (non référencé par
Application, et entrelacée avec la porte de budget) ; arrêt des lots après un échec de quota (changement de
comportement) ; signal d'issue unique dans les composants (churn sans gain). Test du budget : il n'impose plus
un nombre exact de secondes (instable sous charge ; seul le plafond par seconde est garanti).

### client-angular (code seul — à commiter par l'humain sur sa branche)
`front/libs/mss/src/` : `core/models/directory.model.ts`, `core/services/mss-api.service.ts` (+ spec),
`core/utils/directory-search.util.ts` (+ spec, nouveaux), `core/utils/problem-details.utils.ts`,
`features/contacts/mss-contacts.component.{ts,html,spec.ts}`.

### Relance du 2026-10-23 (après la première `/review` et les décisions humaines)
- **api-mail** `5d13216c` + `c74a85bd` :
  - aucun appel abouti, 429 compris → 503 `DIRECTORY_UNAVAILABLE` (décision n° 1) ;
  - `, | $ \` refusés en 400 (une virgule est un OU FHIR) ;
  - organisation seule ≥ 3 caractères, spécialité + organisation sans lieu acceptée (décision n° 3) ;
  - preuves par mutation : M11 (quota sans réponse rendu en 200), M12 (séparateurs acceptés), M13 (organisation
    courte acceptée), toutes rouges.
- **Bloquant n° 3 levé par la mesure** (`TheObservedCase_DupIn18_FitsTheSearchDeadline`, explicite, par
  `AddAnnuaireSante()`) : « dup » + « 18 » en **5,5 s / 29 appels / 22 praticiens**, **5,1 s / 14 appels** avec
  BAL, 0 refus, issue `complete` — sous l'échéance de 10 s, sans parallélisme.
- **client-mobile** `09f8622` et **weda2** (code seul) : « Aucun praticien trouvé » seulement après une recherche
  complète ; séparateurs et organisation courte refusés sans requête ; weda2 : le panneau d'accueil (« Aucun
  résultat ») ne s'affiche plus après une recherche incomplète et vide.
- **client-blazor** (décision n° 2) `e5fae29` + `e485fa8` :
  - `DirectorySearchRules` reprend les règles de l'API ;
  - `DirectoryService` rend une `DirectorySearchOutcome` (issue de l'en-tête, 503 → « annuaire indisponible »,
    400 → motif du serveur) au lieu d'une liste vide silencieuse ;
  - dialogue : « avec adresse MSSanté » coché par défaut, motif de refus, états « incomplète », « indisponible » et
    « aucun praticien » distincts ;
  - 29 tests (règles, service, bUnit), 466 au total.
  - Le projet `Mss.Console` ne se restaure pas sur ce poste (source NuGet `github` absente pour `psc.proxy.*`,
    préexistant, hors task) : tous les autres projets compilent.
- **Passe qualité (§Q)** :
  - appliqué : lecture unique du corps d'erreur, un seul GET avec issue, état de résultats unique dans le dialogue
    Blazor, `dirCanSearch` mémorisé (weda2), mesure réelle par l'enregistrement de production ;
  - écarté : échapper `, | $ \` dans `AnnuaireQuery` plutôt que les refuser (changerait le comportement décidé ;
    gateway à vérifier) ; partage des règles C# via `dtos-mss` (cycle de publication, hors périmètre) ; signal
    d'issue unique dans weda2 et mobile (churn) ; messages Blazor des règles en français seulement (alignés sur les
    400 de l'API).

## Sonar log
- Phase 1 (new code) : ✓ Quality Gate OK, new_coverage = 97,1 %
- Phase 1 — Issues traitées : 10 code smells (S1172, S3925, S1118, S4457, S3604 ×3, CA1859 ×2, xUnit1045) — 9
  corrigés (`f2b51fff`), 1 S3925 marqué FALSE-POSITIVE selon `conventions/csharp.md` § S3925 (triplet présent ;
  la règle réclame le constructeur ISerializable obsolète, SYSLIB0051)
- Phase 1 — Tests ajoutés : 2 (passerelle : rien n'est envoyé après l'échéance ni quand l'appelant est parti)
- Phase 2 (legacy) : 0 itération — cibles projet déjà atteintes
- Conventions : S3604, S4457, S1172 incrémentées (récidives), S1118 créée
- Build / tests : ✓ green (Release, 6 714 tests, 2 analyses complètes)

- **Relance du 2026-10-23** : 2 analyses ; 1 finding nouveau code (S3776 `ValidateSearchCriteria`, 16 → corrigé
  `866e5703`) ; final : Quality Gate OK, nouveau code 0 finding, new_coverage 97,0 %, couverture projet 98,1 %.
  Suite d'intégration : 953 verts, 3 rouges IMAP « du jour » (flaky de minuit préexistant, hors diff — runs à
  01 h locale).

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 97,0 % | 97,0 % (relance) | 0 |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 0 | 0 (10 en cours de run, traités) | 0 |
| Coverage (projet) | 98,0 % | 98,1 % | +0,1 pt |
| Duplication | 0,4 % | 0,4 % | 0 |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

## Lint log
- **client-angular** (code seul, base `origin/next`, lint `tag:scope:mss`) — 1 itération.
  - Baseline : 6 erreurs (Prettier, toutes sur les lignes de la task) + 1 avertissement de complexité sur
    `directoryCriteriaProblem` (22 > 20) ; 56 avertissements au total sur le périmètre.
  - Corrigé : `eslint --fix` sur les fichiers de la task, Prettier sur les specs neuves ou propres au départ
    (`mss-contacts.component.html` était déjà hors format avant la task : non reformaté), `directoryCriteriaProblem`
    découpée (`nameProblem`, `placeProblem`).
  - Final : **0 erreur**, 45 avertissements (tous antérieurs : `max-lines`, `jsdoc/require-example`).
  - Build affected : `weda2` ✓ (avertissement budget initial 2,05 Mo / 2 Mo — task-374 relevait déjà 2,01 Mo ; à
    comparer en revue) ; ✗ `prescription` (1,26 Mo / 1 Mo, hors MSS) et ✗ appli autonome `mss` (1,92 Mo / 1 Mo) —
    dépassements préexistants, sans commune mesure avec les quelques ko de la task.
  - Tests affected : ✓ 12 projets.

- **Relance du 2026-10-23** : 0 erreur, 45 avertissements (inchangés) ; Prettier ✓ sur les fichiers de la relance ;
  tests affected ✓ 12 projets ; `weda2:build:production` ✓ (avertissement budget 2,05 Mo / 2 Mo, inchangé).

## Lint mobile log
- **client-mobile** — baseline : « All files pass linting » ; 0 itération, aucun commit.
- Build production ✓ (avertissements de budget SCSS préexistants, aucun sur `contacts.page.scss`) ; tests ✓
  1 154 (passe de `/develop`, inchangée depuis).

- **Relance du 2026-10-23** : lint ✓ (« All files pass linting »), build ✓, tests ✓ 1 158 ; aucun commit.

## E2E log

Run de la relance (2026-10-23, 01 h 18 locale) — remplace celui du 2026-10-22, vert lui aussi.

| Voie | Commande | Code | Résultat |
|---|---|---|---|
| mobile | `npm run e2e:headless` | 0 | 39 verts, 0 flaky, 0 rouge — parité de la colonne verte |
| angular | `npm run e2e:mss` | 0 | 47 verts, 0 flaky, 0 rouge — parité de la colonne verte |
| porte | `mss.mail.e2e gate` (catalogue de la branche api-mail) | 0 | vert |

Démontage vérifié : aucun conteneur e2e résiduel, ports 5052 / 3993 / 3465 / 3143 libres.
Signalé (non bloquant) : les écrans annuaire de weda2 et de client-blazor ont changé sans spec e2e — le scénario
concerné, E2E-CONTACT-001 v2, est en mode humain (annuaire national réel), joué par `/qa` ; client-blazor n'a pas
de voie e2e au catalogue.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-CONTACT-001 | 2 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 2 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Écrire à l'adresse choisie d'un contact à plusieurs adresses, ou à son adresse par défaut | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 2 | headless | Créer un contact à deux adresses, le modifier sans les perdre, puis le supprimer | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 1 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## Review log
- **2026-10-23 — CHANGES REQUESTED** (`questions/task-386.md`) : 3 bloquants — « aucun praticien » affiché sur
  une recherche incomplète (deux clients) ; virgule = OU FHIR qui contourne la règle des 3 caractères ; cas de
  référence non prouvé sous l'échéance de 10 s avec la latence réelle. 3 décisions demandées, 2 suggestions.
- Règle 1b : M9 (nom court accepté) et M10 (en-tête d'issue absent) jouées, rouges ; correspondance complète.
- Validation : api-mail ✓ hors 3 tests IMAP « du jour » (flaky de minuit préexistant, hors diff) ; mobile ✓ ;
  weda2 ✓ (`/lint-angular`).

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/305 — label `awaiting-human-merge`
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/99 — label `awaiting-human-merge`
- `client-blazor` : https://github.com/codengine-technologies/HealthPlatform.Client/pull/95 — label `awaiting-human-merge`
- `client-angular` : code-only — humain gère commit/push TFS et ouverture PR, branche `feature/nova-mss-weda-integration`.
  Fichiers modifiés :
  - `front/libs/mss/src/core/models/directory.model.ts`
  - `front/libs/mss/src/core/services/mss-api.service.spec.ts`
  - `front/libs/mss/src/core/services/mss-api.service.ts`
  - `front/libs/mss/src/core/utils/problem-details.utils.ts`
  - `front/libs/mss/src/features/contacts/mss-contacts.component.html`
  - `front/libs/mss/src/features/contacts/mss-contacts.component.spec.ts`
  - `front/libs/mss/src/features/contacts/mss-contacts.component.ts`
  - `front/libs/mss/src/core/utils/directory-search.util.spec.ts`
  - `front/libs/mss/src/core/utils/directory-search.util.ts`

## Code Review Summary
- **Seconde revue (2026-10-23) : APPROVED** — les 3 bloquants de la première revue sont corrigés : « aucun praticien »
  seulement après une recherche complète (trois clients, panneau d'accueil compris) ; séparateurs FHIR refusés en 400 ;
  cas d'origine mesuré sur l'API réelle à 5,5 s sous l'échéance de 10 s. Décisions humaines appliquées (503 sans
  réponse, client-blazor inclus, organisation seule ≥ 3).
- **Règle 1b — comportement → test d'intégration de route → preuve rouge** :
  | Comportement | Test (`DirectorySearchEndpointIntegrationTests` sauf mention) | Preuve rouge |
  |---|---|---|
  | BAL portée par une activité seulement | `Search_WithMailbox_KeepsAColleagueWhoseMailboxIsOnlyOnARole` | M1 |
  | Lots `_id` sous la limite d'URL | `Search_LongAccentedOrganisationName_…`, `Search_MoreThan200FacilitiesToFilter_…` | M2 |
  | Abandon du client : aucun nouvel appel, synthèse `cancelled` | `Search_CancelledByTheClient_SendsNoFurtherCall` | M3 |
  | Incomplétude signalée (quota, pages, limite, panne partielle) | `Search_DirectoryKeepsRefusing_…`, `…PartlyDown…`, `…PageCap…`, `…ResultLimit…` | M4 |
  | Reprise sur 429 | `Search_DirectoryBrieflyOverloaded_…`, `Search_LogsOneSummary_…` | M5 |
  | Budget partagé entre instances | `AnnuaireQuotaSharedRedisIntegrationTests` | M6 |
  | 503 annuaire en panne / muet | `Search_DirectoryDown_Is503…`, `Search_DirectoryNeverAnswers_Is503…` | M7 |
  | Établissement du lieu demandé (deux lieux) | `Search_ColleagueInTwoPlaces_…` | M8 |
  | 400 avant tout appel (nom court) | `Search_TooBroad_Is400_WithoutAnyDirectoryCall` | M9 |
  | En-tête d'issue | `Search_EachCombination_…`, `Search_NobodyMatches_…`, `Search_AtThePageCap_…` | M10 |
  | 503 quand tout est refusé pour quota | `Search_DirectoryRefusesEveryCall_Is503_NeverAnEmptyList` | M11 |
  | Séparateurs FHIR refusés | `Search_TooBroad_Is400_…` (virgule, barre, dollar, antislash) | M12 |
  | Organisation seule ≥ 3 | `Search_TooBroad_Is400_…` (« CH ») | M13 |
- **Validation** : api-mail ✓ (intégration 953 verts ; 3 rouges IMAP « du jour » préexistants, rouges aussi sur
  `origin/develop` à 01 h 32 locale — à ouvrir en task) ; mobile ✓ 1 158 ; Blazor ✓ 466 ; weda2 ✓ 996 + lint 0 erreur.
- **Suggestions non bloquantes** (reprises dans les PR) : spécialité + organisation de 2 lettres ; réponse non FHIR →
  500 au lieu de 503 ; message technique brut sur mobile en cas d'erreur réseau ; Blazor « indisponible » sur requête
  non partie et Entrée pendant une recherche ; commentaire XML déplacé ; échapper plutôt que refuser `, | $ \`.

## Merged
- **2026-10-23** — `/merge 386 --i-tested` (plan de test manuel validé par l'humain).
- `api-mail` : PR #305 → `develop` `efbacbc8` (squash) — CI `develop` ✓
- `client-blazor` : PR #95 → `develop` `a92efae` (squash) — CI `develop` ✓
- `client-mobile` : PR #99 → `develop` `8bf6f9b` (squash) — CI `develop` ✓
- `client-angular` : PR TFS mergée par l'humain ; clone local laissé sur sa branche (`feature/nova-mss-weda-integration`) à sa demande.
- Branches `fix/task-386-annuaire-recherche-fiable` supprimées (distantes et locales) ; aucune branche de staging.

## Branches
- `api-mail` (pushed) : fix/task-386-annuaire-recherche-fiable — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-386-annuaire-recherche-fiable
- `client-mobile` (pushed) : fix/task-386-annuaire-recherche-fiable — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/fix/task-386-annuaire-recherche-fiable
- `client-blazor` (pushed, ajouté le 2026-10-23 — décision n° 2) : fix/task-386-annuaire-recherche-fiable — https://github.com/codengine-technologies/HealthPlatform.Client/tree/fix/task-386-annuaire-recherche-fiable
- `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` (au `/start` : `feature/nova-mss-weda-integration`, arbre propre) — humain gère branche, commit, push, PR TFS
- `dtos-mss` : non listé — aucun changement de contrat prévu (issue portée par un en-tête)

## Timings

*(généré par `tools/timing/report.sh --task task-386 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 15 s | — | — | — | — |
| /develop | ok | 15 min 25 s | — | 7 (5 min 07 s) | — | api-mail 0B/2T, client-angular 0B/1T, client-mobile 0B/3T, client-blazor 0B/1T, relance après review |
| /sonar | ok | 13 min 16 s | 4 (1 min 04 s) | 20 (19 min 57 s) | 8 (2 min 35 s) | 2 itération(s), api-mail 4B/20T |
| /lint-angular | ok | 2 min 04 s | 2 (35 s) | 2 (3 min 09 s) | — | client-angular 2B/2T |
| /lint-mobile | ok | 18 s | 2 (14 s) | — | — | client-mobile 2B/0T |
| /e2e | ok | 13 min 47 s | — | — | — | e2e ×6 (27 min 58 s) |
| /review | ok | 6 min 27 s | 4 (29 s) | 5 (8 min 28 s) | — | api-mail 2B/2T, client-mobile 2B/2T, client-blazor 0B/1T, APPROVED (2e revue) — PR api-mail #305, mobile #99, blazor #95 |
| /tech-writer | ok | 54 s | — | — | — | — |
| /merge | ok | 6 min 51 s | — | — | — | — |
| **Total cycle** | | **59 min 21 s** | **12 (2 min 23 s)** | **34 (36 min 42 s)** | **8 (2 min 35 s)** | |

Autres commandes mesurées : lint ×5 (1 min 03 s)
