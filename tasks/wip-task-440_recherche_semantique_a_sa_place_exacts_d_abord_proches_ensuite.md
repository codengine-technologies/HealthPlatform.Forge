# todo-task-440.md — Recherche sémantique à sa place : exacts d'abord, proches ensuite

**Repos**: api-mail, dtos-mss
**Dependencies**: done-task-439 (même fusion des résultats, même champ de contrat ; task-438 est déjà requise par 439)
**Epic**: E022
**Single frontend**: true
**Priorité**: EPIC E022, demandée par l'humain le 2026-11-09. Décision de l'humain : « exacts d'abord, proches
ensuite » — les correspondances exactes en tête, puis une section de résultats proches sous un seuil unique calibré ;
un mot absent ne ramène aucun résultat exact.

> **Origine.** Campagne du 2026-11-09 : `Docs/audits/recherche-campagne-bugs-weda2-mobile-20261109.md`, défauts **R6**
> et **R7** (et la part sémantique de R1). À coordonner avec task-437 (index vectoriel), qui change la requête
> vectorielle mais pas la fusion.

## Ce qui est établi

| Requête | Seuil 0,7 (défaut weda2) | Seuil 0,1 (défaut mobile) |
|---|---|---|
| `zorglubine` (absent de la boîte) | 0 | **50 résultats sans rapport** |
| `psoriasis` (6 messages) | 6 | 6 bons, puis **44 qui ne contiennent pas le mot** |
| `hemoglobine` (sans accent) | 2 | 50, tous pertinents : la similarité **rattrape** l'accent |
| `urgent` (67 messages par l'objet seul) | 5 | 5 exacts, puis 45 voisins |

- **Fusion** (`SemanticSearchService.MergeAndScoreResults` / `BuildHybridResult`, `405da376`) : un résultat trouvé par
  les deux moteurs vaut `0,6 × similarité + 0,4 × score plein texte` ; par la similarité seule, `similarité × 0,8` ;
  par le plein texte seul, `score normalisé × 0,6`. Les deux sources sont **mêlées** dans un seul classement : un voisin
  sémantique vague peut passer devant un message qui contient le mot exact.
- **Seuil** : `maxDistance = 1 − minSimilarity`, fourni par chaque client. weda2 prend le réglage de la personne
  (`UserSettingsDto.MinSimilarity`, défaut **0,7** ; la boîte de Virginie porte 0,1 pour deux personnes et 0,7 pour
  deux autres) ; le mobile prend **0,1** (stockage local). Pour la même recherche, `psoriasis` rend 6 résultats dans
  weda2 et 50 sur le mobile.
- À 0,1, la recherche sémantique rend **toujours** ses voisins les plus proches, même lointains : aucun seuil ne
  protège d'un mot absent.
- Aucun test ne joue la recherche sémantique de bout en bout (constat de task-438).

## Objective

Les correspondances exactes passent toujours en tête. La recherche par le sens complète, sans jamais noyer : ses
résultats forment une section à part, et n'y entrent que s'ils sont réellement proches de la requête, selon un seuil
unique, calibré sur le corpus de référence, identique pour tous les clients et toutes les personnes.

Règles :
- **Deux sections dans la réponse**, dans cet ordre :
  1. **les correspondances exactes** (groupes « tous les mots » puis « une partie des mots », task-439) ;
  2. **les résultats proches** : trouvés par la similarité seule, absents de la première section, au-dessus du seuil.
  Un message trouvé par les deux moteurs est un résultat exact : il n'est pas répété dans les proches.
- **Un seuil unique, fixé par le serveur** et calibré sur le corpus de task-438 : les résultats proches rendus pour
  les requêtes de référence sont pertinents dans au moins **90 %** des cas (jugés par les attendus du corpus). Le seuil
  et sa calibration sont consignés.
- **Le réglage du client ne décide plus** : `minSimilarity` envoyé par un client est ignoré (contrat déprécié, accepté
  pour la compatibilité) ; le réglage de la personne n'influe plus sur la recherche. Son retrait de l'interface est
  task-441.
- **Mot absent** : aucun résultat exact ; des résultats proches seulement s'il en existe au-dessus du seuil. Pour un mot
  sans rapport avec la boîte (`zorglubine`), la réponse est vide.
- **Le rattrapage par le sens reste** : une formulation différente (synonyme, abréviation médicale courante, faute de
  frappe) peut trouver des messages en section « proches ». Task-440 complète le corpus de task-438 avec des requêtes
  de ce type, et leurs attendus.
- **Panne d'un moteur** : inchangé — l'autre répond, `isDegraded` le signale.
- **Règle 14 inchangée.**

Contrat (`dtos-mss`, rétrocompatible) : chaque `hit` dit s'il est **exact** (avec son groupe, task-439) ou **proche** ;
`minSimilarity` est déprécié dans la requête.

### Hors périmètre

- L'index vectoriel et le coût de la requête vectorielle : task-437.
- L'affichage des sections dans les clients et le retrait du réglage de similarité de l'interface : task-441.
- L'assistant IA, qui a ses propres usages de la similarité.

## Definition of Done

- [ ] Build passes (0 errors) : `HealthPlatform.Api.Mail.sln`, `HealthPlatform.Dtos.Mss.csproj`
- [ ] Tests pass (0 failures) : `HealthPlatform.Api.Mail.sln`
- [ ] **Les requêtes de référence de task-438 marquées « task-440 » sont vertes**, marquage retiré : mot absent (réponse
      vide), mot rare (aucun voisin intercalé avant les exacts), mêmes résultats quel que soit le `minSimilarity` envoyé
- [ ] **Test d'intégration de bout en bout (règle 1b), `POST /api/v1/Search/semantic`** en mode hybride, embeddings
      pré-calculés du corpus, lu dans la réponse réelle :
      - les exacts précèdent tous les proches ; aucun message n'apparaît dans les deux sections ;
      - la section de chaque `hit` est lue et vaut ce qu'elle doit valoir ;
      - deux requêtes identiques avec `minSimilarity` 0,1 et 0,9 rendent la même réponse ;
      - **vu rouge** sur le code d'avant (cas de task-438) et par mutation (fusion mêlée réinjectée), consigné
- [ ] **Cas d'échec** : moteur sémantique en panne → les exacts sont rendus, `isDegraded` vrai, `degradedSources`
      « semantic », lu dans la réponse réelle
- [ ] **Calibration du seuil** consignée dans le `## Develop log` : courbe pertinence / seuil sur le corpus, seuil retenu,
      ≥ 90 % de résultats proches pertinents ; requêtes « par le sens » ajoutées au corpus de task-438
- [ ] Contrat `dtos-mss` publié et consommateurs .NET mis à jour ; un client qui ne lit que `uids` reçoit les exacts puis
      les proches, dans cet ordre
- [ ] Outil de campagne rejoué sur la boîte de formation de Virginie : `zorglubine` vide, `psoriasis` sans voisins avant
      les 6 exacts, même réponse pour les deux seuils
- [ ] Aucune donnée de santé en clair dans les logs (termes de recherche et vecteurs compris)
- [ ] **Prévention (règle d'or)** : consigne dans `conventions/csharp.md` : un seuil qui décide de ce que voit le médecin
      est fixé par le serveur et calibré sur un corpus, jamais laissé à chaque client

## Manual Test Plan

1. Lancer le backend sur la boîte de formation de Virginie : `cd Api/Mail/src/AppHost && dotnet run`.
2. Dans weda2 puis sur le mobile, rechercher `zorglubine`, `psoriasis`, `infarctus`.
3. Attendu :
   - `zorglubine` : aucun résultat, dans les deux clients ;
   - `psoriasis` : les 6 messages qui contiennent le mot, et les mêmes dans les deux clients ;
   - `infarctus` : les messages qui contiennent le mot, puis éventuellement des messages proches (affichés à part à
     partir de task-441).
4. Changer le réglage de similarité dans les paramètres de weda2 : le résultat d'une recherche ne change pas.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du praticien)
- **Vague Ségur** : hors Ségur — fiabilité de la recherche
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : inchangée — PSC (e-CPS), niveau eIDAS substantiel
- **Habilitations** : inchangées — verdict de l'opérateur MSSanté (règle 14)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé — `MailSearch` au nom de la personne réelle, 3 653 jours ; ni terme ni vecteur journalisé
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — embeddings et résultats dans la base de la boîte, inchangés
- **AIPD / impact RGPD** : inchangé — l'usage de la similarité existe déjà ; seule sa présentation change

## Branches
- `api-mail` (pushed) : feat/task-440-recherche-semantique-a-sa-place-exacts-d — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-440-recherche-semantique-a-sa-place-exacts-d
- `dtos-mss` (paresseuse) : branche `feat/task-440-recherche-semantique-a-sa-place-exacts-d` créée par `/develop` depuis `origin/develop` au moment où il touche le contrat (section exact / proche, `minSimilarity` déprécié)

## Timings

*(généré par `tools/timing/report.sh --task task-440 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 21 s | — | — | — | — |
| **Total cycle** | | **21 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |
