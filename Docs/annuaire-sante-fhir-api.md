# API FHIR Annuaire Santé (ANS) — comportement mesuré

> Fiche de référence pour api-mail (`AnnuaireSante/`). Mesures faites le 2026-10-22 contre
> `https://gateway.api.esante.gouv.fr/fhir/v2` avec la clé d'api-mail (une cinquantaine d'appels,
> espacés de 250 ms). Doc officielle : `ansforge/annuaire-sante-fhir-documentation` (version-2).
> À re-mesurer si la passerelle change de comportement.

## Accès

- En-tête `ESANTE-API-KEY: <clé>` ; `Accept: application/fhir+json`. FHIR R4 (4.0.1).
- Interactions : `search-type` et `read` seulement, sur `Practitioner`, `PractitionerRole`, `Organization`
  (et `Device`, `HealthcareService`). Aucune opération, aucun chaînage déclaré.
- Latence typique : 100 à 300 ms par appel, y compris pour 1 000 ressources (≈ 2 Mo).

## Quota

- **17 appels par seconde par application** (passerelle Gravitee, doc ANS). Le quota suit la **clé** :
  toutes les instances d'api-mail le partagent.
- Mesuré : rafale de 25 appels simultanés → 21 × 200, 4 × **429** ; tout repasse 2 s plus tard.
- La réponse 429 **ne porte ni `Retry-After` ni en-tête de quota** (`X-RateLimit-*` absents, y compris
  sur les 200) ; corps JSON « Rate limit exceeded! You reached the limit of 17 requests per 1 seconds ».
- Conséquence : le client doit **se réguler lui-même** (budget partagé entre instances) et, sur 429,
  attendre ~1 s avant de réessayer — il n'y a rien à lire dans la réponse.

## Paramètres de recherche (CapabilityStatement)

| Ressource | Paramètres utiles | `_include` | `_revinclude` |
|---|---|---|---|
| `Practitioner` | `family`, `given`, `name`, `identifier` (RPPS), `active`, `mailbox-mss`, `qualification-code` | — | `PractitionerRole:practitioner` |
| `PractitionerRole` | `practitioner`, `organization`, `role`, `active`, `mailbox-mss` | `PractitionerRole:practitioner`, `PractitionerRole:organization`, `*` | — |
| `Organization` | `_id`, `name`, `address-postalcode`, `address-city`, `address`, `type`, `mailbox-mss`, `partof` | `Organization:partof`, `*` | `PractitionerRole:organization`, `HealthcareService:organization`, `Device:organization` |

- **Aucun critère de lieu sur `Practitioner` ni `PractitionerRole`** : le lieu ne se filtre que sur `Organization`.
- `_include:iterate` **non supporté**.

## Sémantique mesurée

| Requête | Résultat |
|---|---|
| `family=dupon` | « commence par », insensible à la casse (1 761 ; `DUPONT` : 1 650) — 120 ms |
| `family:contains=dup` | « contient » — **14 s** : à proscrire |
| `family:exact=DUPONT` | sensible à la casse et aux accents (1 500) |
| `family=DUPONT&given=philippe` | 9 |
| `family=DUPONT&mailbox-mss:contains=%40` | 225 praticiens **ayant une BAL MSSanté** (e-mails portés par `Practitioner`) |
| `address-postalcode=18` | « commence par » : tout le département (2 810 établissements) ; `18000` : 826 |
| `_id=a,b,c` (OU) | plusieurs ressources en un appel ; **se combine** avec `address-postalcode` (filtre serveur) |
| `organization=Organization/a,Organization/b` | OU accepté sur `PractitionerRole` |
| `_count=1000` | accepté (1 000 ressources, 0,3 s) ; défaut 50 ; pagination par le lien `next` (`_page?id=…`), à suivre tel quel |
| `_total=accurate` | fournit `total` |

## Pièges

- **`POST …/_search` ne fonctionne pas** sur cette passerelle : 500 « Parameter X not found for resource
  Organization/_search », quel que soit le paramètre. Rester en `GET`.
- **URL limitée à ~4 096 caractères** : 4 092 acceptés, **414** à 4 177 (mesuré le 2026-10-22). Le client FHIR
  .NET encode les virgules d'une liste `_id` en `%2C` (3 caractères), que la passerelle lit bien comme un OU :
  200 identifiants réels (`001-01-2027347`) font ~3 400 caractères avec un code postal. api-mail coupe ses lots
  à 200 identifiants **et** 3 800 caractères d'URL (`AnnuaireQuery.Batch`).
- **`_id=` vide est ignoré** : l'appel renvoie alors tout ce qui correspond aux autres critères. Ne jamais
  envoyer une liste vide.
- **Paramètre inconnu → 500** (et non 400), avec un `OperationOutcome`.
- Environ 14 % des `PractitionerRole` n'ont **pas d'`organization`** : pas de lieu, ils ne passent aucun filtre de lieu.
- `Organization` peut porter des e-mails de **contact** qui ne sont pas des BAL MSSanté (doc ANS) ; les BAL
  personnelles et cabinet sont sur `Practitioner` / `PractitionerRole`.

## Recherche « nom + lieu » — approche validée

1. `Practitioner?family={nom}[&given={prénom}][&mailbox-mss:contains=%40]&_revinclude=PractitionerRole:practitioner&_count=1000`, en suivant `next`.
2. Identifiants d'établissement des activités → `Organization?_id={lot de 200}&address-postalcode={cp}` (ou `address-city`) : le serveur ne rend que les établissements du lieu.
3. Garder les praticiens dont une activité est dans l'un de ces établissements.

Cas réel « dup » + « 18 » (trace Seq du 2026-10-22, où api-mail rendait 0) :

| Variante | Praticiens « dup… » | Appels | Durée | Résultat |
|---|---|---|---|---|
| api-mail actuel (lieu d'abord, 1 appel par établissement) | — | 101 | 4,1 s | 0, avec des 429 |
| nom d'abord | 6 422 | 29 | 17,7 s (dont 7 s d'espacement de test) | **22** |
| nom d'abord + `mailbox-mss` | 989 | 7 | 4,4 s | **1** (avec BAL) |

Pour une messagerie MSSanté, le filtre `mailbox-mss` est le critère naturel (seuls les praticiens joignables) et
divise le coût par quatre. Un préfixe de nom court (« dup ») reste coûteux : prévoir un nombre minimal de
caractères, ou une borne de pages avec résultat signalé comme incomplet.

## Ce qui protège ces hypothèses (task-386)

- **Faux annuaire fidèle** — `Api/Mail/tests/mss.mail.testing.shared/Annuaire/FakeAnnuaireSante.cs` : il sert
  les mêmes paramètres et la même sémantique que la passerelle, reproduit ses pièges (paramètre chaîné → 504,
  `POST _search` → 500, paramètre inconnu → 500, URL au-delà de 4 096 → 414, `_id=` vide ignoré, 429 sans
  `Retry-After`) et consigne tout appel interdit, ce qui fait échouer le test qui l'émet. Chaque piège a son
  propre test (`FakeAnnuaireSanteTests`).
- **Tests de bout en bout de la route** — `DirectorySearchEndpointIntegrationTests` (vraie route, vrai service,
  budget Redis réel, horloge simulée) et `AnnuaireQuotaSharedRedisIntegrationTests` (deux instances, un Redis).
- **Test de contrat contre l'API réelle** — `AnnuaireSanteContractTests`, ci-dessous.

### Test de contrat

Il revérifie sur la passerelle réelle chaque hypothèse dont dépend la recherche : `family` en « commence par »,
`_revinclude` sur `Practitioner` et sur `Organization`, pagination `next`, les trois formes de RPPS, un lot de
200 `_id` (virgules encodées `%2C`) combiné à un code postal, `qualification-code` et `mailbox-mss` sur un lot,
paramètre inconnu → 500, limite d'URL. **Hors CI** (`Explicit`) : il consomme le quota de la clé partagée
(14 appels, espacés de 300 ms). À jouer avant une mise en production et dès qu'un écart est suspecté ; un échec
veut dire que l'ANS a changé quelque chose — corriger la recherche **et** le faux annuaire.

```bash
# Clé lue dans l'environnement ou dans Api/Mail/.env (FhirOptions__ApiKey) — jamais affichée.
cd Api/Mail
dotnet test tests/mss.mail.integration.tests/mss.mail.integration.tests.csproj   --filter "FullyQualifiedName~AnnuaireSanteContractTests"   --logger "console;verbosity=detailed" -- xUnit.Explicit=on
```

Sans clé, le test s'ignore (`Skip`) au lieu d'échouer. Sa sortie ne contient que des comptes, jamais un nom.
