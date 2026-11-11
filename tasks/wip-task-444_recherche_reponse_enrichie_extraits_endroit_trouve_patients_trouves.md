# todo-task-444.md — Recherche : réponse enrichie (extraits, endroit trouvé, patients trouvés)

**Repos**: api-mail, dtos-mss
**Dependencies**: done-task-440 (groupes et sections de la réponse ; 438 et 439 requises en amont)
**Epic**: E023
**Single frontend**: true
**Priorité**: EPIC E023, demandée par l'humain le 2026-11-10. Le médecin doit voir **pourquoi** un message est trouvé,
et **quel patient** sa recherche désigne. Le serveur ne rend aujourd'hui que des identifiants : cette task lui fait
rendre de quoi l'expliquer.

> **Origine.** Analyse du 2026-11-10 (surlignage d'Outlook, « Personnes » en tête des résultats). Backend seul : les
> clients l'affichent en task-446 (weda2) et task-451 (mobile).

## Ce qui est établi

- `SearchResponseDto` rend `Uids`, `Hits` (UID + dossier, task-192), `IsTruncated`, `IsDegraded`, `DegradedSources`.
  Après task-439 et task-440, chaque `hit` porte son groupe (tous les mots, une partie) ou sa section (proches).
- Aucun extrait, aucun endroit trouvé, aucun patient n'est rendu : les clients ne peuvent rien expliquer.

## Objective

Chaque résultat dit où le terme a été trouvé et en montre un extrait ; la réponse dit quels patients de la boîte la
recherche désigne.

Règles :
- **Endroit trouvé** : chaque résultat exact indique le ou les champs où un terme a été trouvé, parmi : objet, corps,
  document médical, expéditeur, nom de pièce jointe. Un résultat proche par le sens porte « proche par le sens ».
- **Extrait** : un passage court (≤ 200 caractères) du champ trouvé, centré sur le premier terme trouvé, avec les
  positions des termes à surligner. Pour un document médical, l'extrait vient du texte du document. Pour un résultat
  proche, l'extrait est le début du corps, sans surlignage.
- **Surlignage tolérant** : les positions désignent le mot tel qu'il est écrit dans le message, même si le médecin l'a
  tapé sans accent ou en majuscules (`hemoglobine` surligne « hémoglobine »).
- **Patients trouvés** : la réponse liste, à part des messages, les patients de la boîte que la requête désigne, **par
  correspondance exacte seulement** :
  - les mots de la requête égalent, après normalisation de la casse, des accents, des tirets et des espaces, le nom de
    naissance ou le nom d'utilisation **et**, si un second mot est tapé, le prénom ;
  - ou la requête est une date de naissance complète associée à un nom ;
  - ou la requête est une **INS complète** (15 caractères + clé), égale à l'INS d'un patient de la boîte.
  - **Jamais** de correspondance phonétique, approchée ou par le sens. `Vidal` ne désigne jamais `Collette`.
  - Chaque patient trouvé porte : nom de naissance, nom d'utilisation, prénom, date de naissance, sexe, statut de l'INS
    (qualifiée ou non) et le nombre de messages rattachés. **Jamais l'INS elle-même.**
  - Au plus 5 patients ; au-delà, la réponse le signale.
- **Requête INS hors historique** : une requête reconnue comme une INS n'est **pas** enregistrée dans l'historique des
  recherches, qui l'afficherait en clair.
- Les champs ajoutés sont **rétrocompatibles** : un client qui ne les lit pas fonctionne comme avant.
- **Coût** : sur la boîte cible de 10 000 messages, l'enrichissement n'ajoute pas plus de 100 ms au p95 de la recherche
  (mesuré avec l'outil de volumétrie de task-439).
- **Règle 14 inchangée** : les patients trouvés sont ceux de la base de la boîte, lue après le verdict de l'opérateur.

### Hors périmètre

- L'affichage : task-446 (weda2), task-451 (mobile).
- La recherche de patients par sa route dédiée (`Patients/search`) : inchangée.

## Definition of Done

- [ ] Build passes (0 errors) : `HealthPlatform.Api.Mail.sln`, `HealthPlatform.Dtos.Mss.csproj`
- [ ] Tests pass (0 failures) : `HealthPlatform.Api.Mail.sln`
- [ ] Tests unitaires : calcul de l'extrait et des positions (accent, casse, plusieurs termes, terme en fin de champ),
      détection de l'endroit trouvé, reconnaissance d'une INS, correspondance exacte des patients (≥ 1 test par branche)
- [ ] **Tests d'intégration de bout en bout (règle 1b), `POST /api/v1/Search/semantic`**, sur le corpus fictif de
      task-438, lus dans la réponse réelle, chacun vu rouge par mutation :
      - `hemoglobine` : le `hit` porte l'endroit « document médical », un extrait contenant « hémoglobine » et une
        position qui le couvre exactement ;
      - un mot présent seulement dans le nom d'une pièce jointe : endroit « nom de pièce jointe » ;
      - un résultat proche : section proches, endroit « proche par le sens », aucune position ;
      - `bernard catherine` : la liste des patients trouvés contient Catherine BERNARD, avec son nombre de messages, et
        **aucun champ ne contient l'INS** ;
      - un nom voisin (`bernart`) : **aucun** patient trouvé ;
      - une INS complète d'un patient de la boîte : ce patient est trouvé, et la requête **n'apparaît pas** dans
        `GET /api/v1/Search/history` ;
      - **cas d'échec** : moteur plein texte en panne → les résultats proches sont rendus sans extrait surligné,
        `isDegraded` vrai
- [ ] Mesure de coût consignée dans le `## Develop log` : p95 de la recherche avant / après sur la boîte de 11 178
      messages, écart ≤ 100 ms
- [ ] Contrat `dtos-mss` publié (rétrocompatible) et consommateurs .NET mis à jour
- [ ] Aucune donnée de santé en clair dans les logs : ni terme, ni extrait, ni nom, ni INS, ni date de naissance
- [ ] **Prévention (règle d'or)** : consigne dans `conventions/csharp.md` : une correspondance d'identité patient est
      exacte après normalisation, jamais approchée, et l'INS ne sort jamais d'une réponse de recherche

## Manual Test Plan

1. Lancer le backend sur le corpus fictif : `cd Api/Mail/src/AppHost && dotnet run`, puis le seed de référence.
2. Avec l'interface Scalar de l'API (ou `curl` via la session du proxy), appeler `POST /api/v1/Search/semantic` :
   - `hemoglobine` : chaque `hit` porte un extrait et une position qui couvre « hémoglobine » ;
   - `bernard catherine` : la liste des patients trouvés contient Catherine BERNARD, sans INS ;
   - `bernart` : aucun patient trouvé ;
   - l'INS fictive d'un patient du corpus : ce patient est trouvé.
3. Appeler `GET /api/v1/Search/history` : la requête INS n'y figure pas.
4. Lire les journaux dans Seq : aucun terme, extrait, nom ou INS en clair.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du praticien)
- **Vague Ségur** : hors Ségur — ergonomie de la recherche
- **Exigences DSR honorées** : non applicable — la correspondance exacte des patients suit le principe
  d'identito-vigilance (pas de rapprochement d'identité approché), sans exigence DSR spécifique
- **INS** : une INS complète peut être cherchée ; elle n'est **jamais** rendue, ni journalisée, ni enregistrée dans
  l'historique. Les patients trouvés portent le **statut** de leur INS (qualifiée ou non) pour que le médecin sache s'il
  peut se fier à l'identité
- **Authentification PS** : inchangée — PSC (e-CPS), niveau eIDAS substantiel
- **Habilitations** : inchangées — verdict de l'opérateur MSSanté (règle 14)
- **Interop CI-SIS** : extraits lus dans le texte déjà extrait des documents CDA r2 ; aucun nouvel échange
- **Tracé PGSSI-S** : chaque recherche tracée (`MailSearch`, famille `HealthDataAccess`) au nom de la personne réelle,
  avec son rôle, 3 653 jours ; la trace ne porte ni terme, ni extrait, ni patient trouvé en clair
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — extraits calculés à la volée depuis la base de la boîte, rien de nouveau n'est stocké
- **AIPD / impact RGPD** : à vérifier — la réponse de recherche expose désormais des extraits de contenu et des
  identités de patients ; même périmètre de personnes habilitées, note RGPD à compléter si l'AIPD de la recherche ne
  couvre pas l'affichage d'extraits

## Develop log

**Contrat** (`dtos-mss`, rétrocompatible, paquet **588**, PR à ouvrir par `/review`) :
- `SearchHitDto` : `Locations` (`SearchMatchLocation` : objet, corps, document médical, expéditeur, nom de pièce
  jointe, proche par le sens), `Excerpt` (≤ `ExcerptMaxLength` = 200, « … » aux coupes), `ExcerptLocation`,
  `Highlights` (`SearchHighlightDto` : `Start`, `Length`, en unités UTF-16 de l'extrait) ;
- `SearchResponseDto` : `Patients` (`SearchFoundPatientDto`, au plus `MaxPatients` = 5) et `IsPatientsTruncated`.
  Aucun champ INS : seul `IsInsQualified` sort.

**api-mail** :
- `SearchExcerpts` : extrait centré sur le premier mot, coupé aux mots, positions tolérantes (le texte est replié
  caractère par caractère comme `SearchTerms.Normalize`, avec la position source de chaque caractère replié) ;
- `SearchHitEnrichment` : endroits trouvés (un passage par texte), extrait du champ le plus parlant (corps, document,
  objet, pièce jointe, expéditeur) ; un proche reçoit `Similar` et le début de son corps, sans surlignage ;
- `PatientQuery` : nom (et prénom, dans les deux ordres), nom et date de naissance complète, ou INS complète ;
  correspondance de clés normalisées égales (`Key`), jamais approchée ;
- `SemanticSearchRepository.Explain.cs` : `GetMailTextsAsync` (textes de la page, filtre exact dossier + UID) et
  `FindPatientCandidatesAsync` (nom plié en SQL par `regexp_replace(search_normalize(…), '[^[:alnum:]]', '')`, jumeau de
  `Key` ; INS comparée en base, jamais lue) ;
- `SemanticSearchService` : étape 6 (patients, puis extraits de la page) ; une seule politique de mode dégradé
  (`RunDegradableAsync`), partagée par les moteurs et les deux enrichissements (`excerpts`, `patients`) ;
- une requête INS n'est **jamais envoyée au fournisseur d'embeddings** (`EmbeddableQuery`, sur les deux routes) ni
  **gardée dans l'historique** (`SearchHistoryService.RecordAsync`) ;
- `SearchResultHelper.ToResponse` : la partie commune de la réponse des deux routes.

**Écarts assumés** (signalés à la revue) :
- **Nom de naissance et nom d'utilisation non distingués** : la fiche patient (`MailPatient`) n'a qu'un champ
  `LastName`. La correspondance et la réponse portent ce nom ; le DTO le documente. Le distinguer demande d'abord de
  stocker les deux noms à l'analyse du CDA.
- **Statut de l'INS** : `IsInsQualified` = INS présente et OID du domaine NIR qualifié (`InsIdentityDomain.IsQualifying`).
  Une INS provisoire, de test ou d'OID inconnu (lignes antérieures à task-183) rend `false`.
- **Corpus** : le corpus de task-438 n'a ni patient ni « hémoglobine » dans un document médical. Les tests d'intégration
  posent leurs propres données fictives dans une base isolée (`SearchEnrichedResponseIntegrationTests`), plutôt que de
  modifier un corpus dont dépend le verdict de qualité de task-438.
- **Reconnaissance d'une INS volontairement large** : la forme (15 caractères, 2A/2B admis), sans contrôle de clé, pour
  que tout ce qui ressemble à une INS reste hors de l'historique et du fournisseur d'embeddings.

**Règle 1b — tests d'intégration de bout en bout** (`SearchEnrichedResponseIntegrationTests`, `POST
/api/v1/search/semantic`, vraie pile, PostgreSQL ; seul le générateur d'embeddings est un double ; l'historique passe
par le vrai `SearchHistoryService` sur la vraie pile de cache adossée à un cache en mémoire). Vus rouges par mutation,
rejouées après la passe qualité :

| Comportement | Test | Mutation | Verdict |
|---|---|---|---|
| `hemoglobine` → endroit « document médical », extrait, position qui couvre « Hémoglobine » | `WordInAMedicalDocument…` | B1 (champ document retiré), B2 (repli sans accent) | rouge, rouge |
| Mot seulement dans le nom d'une pièce jointe → endroit « nom de pièce jointe » | `WordOnlyInTheNameOfAnAttachment…` | B3 | rouge |
| Proche → section `Similar`, endroit « proche par le sens », début du corps, aucune position | `SimilarResult_IsInTheSimilarSection…` | B4 | rouge |
| `bernard catherine` → Catherine BERNARD avec son nombre de messages, jamais l'INS (JSON brut) | `NameAndFirstName_ListsThePatient…` | B5 (prénom ignoré), B11 (nombre de messages) | rouge, rouge |
| `bernart` → aucun patient | `NeighbouringName_ListsNoPatient` | B6 (nom approché à 6 lettres, en SQL et en C#) | rouge |
| Nom + date de naissance → la seule patiente née ce jour | `NameAndBirthDate…` | B9 | rouge |
| INS complète → la patiente trouvée, requête absente de `GET /search/history` | `CompleteIns_ListsThePatient…` | B7 (INS gardée), B8 (INS non comparée) | rouge, rouge |
| **Échec** : moteur plein texte en panne (`search_normalize` renommée en base) → proche rendu avec extrait, sans surlignage, `isDegraded` | `FullTextEngineDown…` | B10 (enrichissement patients non dégradable → 503) | rouge |

Unitaires : `SearchExcerptsTests`, `PatientQueryTests`, `SearchHitEnrichmentTests`,
`SemanticSearchServiceEnrichmentTests` (dégradé `excerpts` / `patients`, annulation jamais avalée, INS jamais envoyée au
moteur sémantique, plafond de 5), `SearchHistoryServiceTests` (INS jamais gardée).

**Coût** (`Docs/audits/findings/plans/20261111-task-444/`, `cost444.cs`) : copie `srch_lab` de la boîte de formation
(11 291 messages, 56 patients), page de 50 résultats, 30 passages après chauffe, Release. Surcoût de l'enrichissement
(candidats patients + textes de la page + extraits) : **p50 21,4 ms, p95 45,9 ms**, pire requête (4 mots) p95 55,7 ms.
Borne de la DoD : ≤ 100 ms ajoutés au p95. Le coût dépend de la taille de la page, pas de celle de la boîte (une page
de textes, un balayage des patients).

**Journaux** : aucun terme, extrait, nom, INS ni date de naissance. Seuls le nombre de patients trouvés (Debug) et le
nom de la source dégradée (Warning) sont journalisés.

**Passe qualité §Q** (`/simplify`, 4 revues) — appliqué :
- un seul passage par texte (repli + recherche) au lieu de `Contains` puis `Around` ; table de repli en cache pour le
  latin ; `Beginning` ne réduit les espaces que sur la longueur utile ;
- filtre exact (dossier, UID) dans `GetMailTextsAsync` (`MailKey` sorti du service vers les modèles) ;
- garde INS déplacée dans la préparation de la requête sémantique, commune aux deux routes (la route patient
  l'oubliait) ;
- pliage SQL du nom identique à `PatientQuery.Key` (`regexp_replace`), au lieu de quatre `Replace` ;
- une seule politique de mode dégradé, générique (`RunDegradableAsync<T>`), au lieu de deux copies ;
- `PatientQuery` : réutilise `SearchTerms.Words`, `DateOnly.TryParseExact`, un seul générateur de découpes ;
  `SearchHitEnrichment` : champs dans l'ordre de l'extrait, une boucle pour les proches ;
- `SearchResultHelper.ToResponse` : la réponse commune des deux routes construite une fois.

Écarté :
- contrôle de la clé INS (mod 97) : la reconnaissance reste large exprès ;
- index sur le nom des patients : 56 patients sur la boîte de 11 000 messages, de l'ordre de la milliseconde ;
- extraction d'un `SearchResultEnricher` : changement de structure hors de la passe.

**Prévention (règle d'or)** : `conventions/csharp.md` § `identite-patient-exacte`.

## Sonar log

**Mode A** (chaîné depuis `/develop`), `api-mail`, branche `feat/task-444-…`, build `Release`, 2 itérations.

### KPIs qualité (baseline → final)

| KPI | Baseline (analyse finale de task-443) | Itération 1 | Final |
|---|---|---|---|
| Quality Gate | OK | **ERROR** (hotspot non revu) | **OK** |
| Bugs / Vulnérabilités | 0 / 0 | 0 / 0 | 0 / 0 |
| Code smells | 0 | 1 | **0** |
| Hotspots à revoir | 0 | 1 | **0** |
| Couverture globale | 97,8 % | 97,8 % | **97,8 %** |
| Couverture du nouveau code | — | 96,2 % | **96,2 %** |
| Duplication (nouveau code) | 0,4 % | 0,4 % (0,04 %) | 0,4 % (0,04 %) |
| Ratings (fiabilité / sécurité / maintenabilité) | A / A / A | A / A / A | A / A / A |

**Phase 1 — nouveau code** : 1 issue et 1 hotspot, sur la même ligne, corrigés à la main.
- **SYSLIB1045** et **S6444** (hotspot « regex sans délai d'expiration »), `SemanticSearchRepository.Explain.cs` :
  `Regex.Replace(search_normalize(LastName), "[^[:alnum:]]", "")` écrit dans la requête EF pour qu'EF le traduise
  en `regexp_replace`. La regex est destinée à PostgreSQL, pas au processus : la fonction intégrée est déclarée à EF
  (`MailDataContext.RegexpReplace`, `IsBuiltIn`), comme `search_normalize`. Plus aucune regex ne s'exécute en C#.
  Comportement prouvé : `SearchEnrichedResponseIntegrationTests` 8/8, mutation B6 rejouée, rouge.
- Introduite par la passe qualité §Q (pliage SQL du nom jumeau de `PatientQuery.Key`), pas par le premier jet.

**Phase 2 — dette ancienne** : 0 issue ouverte sur le projet.

**Tests de l'analyse finale** : domain 210, application 4 193, infrastructure 743, api 1 375, intégration 1 250
(+16 ignorés), 0 échec, totaux conformes (aucun plantage masqué).

**Conventions** : `SYSLIB1045` porté à 5, avec la variante EF (déclarer la fonction PostgreSQL, jamais `Regex` dans
une requête).

## Lint log

**Lint Angular : skipped** — `client-angular` n'est pas dans les `**Repos**` de la task (`api-mail`, `dtos-mss`).

## Lint mobile log

**Lint mobile : skipped** — `client-mobile` n'est pas dans les `**Repos**` de la task.

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail et dtos-mss touchés | ✅ verte (1ᵉʳ passage) | 60 verts, 0 flaky, 0 rouge, 0 quarantaine | ~9 min |
| angular | api-mail et dtos-mss touchés | ✅ verte (1ᵉʳ passage) | 74 verts, 0 flaky, 0 rouge, 1 quarantaine (E2E-COMPOSE-002, verte) | ~10 min |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ `feat/task-444-…`, inchangé par la task (identique à `origin/develop`).
- Aucun parcours médecin créé ni modifié : la task enrichit la réponse du serveur (champs rétrocompatibles) ; leur
  affichage, et donc leurs scénarios, arrivent avec task-446 (weda2) et task-451 (mobile). Les deux voies prouvent que
  les clients actuels fonctionnent comme avant avec la réponse enrichie.
- Parcours touchés sans spec e2e modifié : aucun (aucun écran touché).
- Démontage : complet (ports 5052 et 47399 libres, aucun conteneur e2e résiduel).

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
| E2E-PATIENT-003 | 1 | headless | La fiche d'un patient ne montre pas les documents d'un autre patient du même mail | ✅ | ✅ |
| E2E-PATIENT-004 | 1 | headless | La vue « Mails du patient » reste ouverte et ses pages viennent du serveur | ✅ | — |
| E2E-CONTACT-001 | 2 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Écrire à l'adresse choisie d'un contact à plusieurs adresses, ou à son adresse par défaut | ✅ | ✅ |
| E2E-COMPOSE-005 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-MAIL-006 | 1 | headless | Glisser sur la Corbeille un message d'un fil supprime ce message, et lui seul | ✅ | — |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-DRAFT-004 | 1 | headless | Une rédaction sans texte dans le corps ne laisse ni brouillon ni question | ✅ | ✅ |
| E2E-BIO-001 | 2 | headless | Acquitter un compte rendu de biologie, à son nom | ✅ | ✅ |
| E2E-BIO-002 | 1 | headless | La puce « Bio à acquitter » montre tous les résultats en attente, sur toutes les pages | ✅ | ✅ |
| E2E-BIO-003 | 1 | headless | Lire un résultat HPRIM puis l'acquitter | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SETTINGS-004 | 1 | headless | Paramètres indisponibles : rien n'est écrasé | ✅ | — |
| E2E-SEARCH-001 | 2 | headless | Composer ses critères puis lancer la recherche | ✅ | ✅ (v1) · divergence (task-450) |
| E2E-SEARCH-002 | 1 | headless | Un mot rare et accentué trouve le message qui le contient | ✅ | ✅ |
| E2E-SEARCH-003 | 1 | headless | Un numéro de dossier trouve son message, et un seul | ✅ | ✅ |
| E2E-SEARCH-008 | 1 | headless | Restreindre la recherche à un patient et à ses biologies anormales | ✅ | ⛔ non joué · divergence (task-451) |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 2 | headless | Créer un contact à deux adresses, le modifier sans les perdre, puis le supprimer | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-CONTACT-004 | 1 | headless | Consulter un contact depuis le carnet et lui écrire | ✅ | ✅ |
| E2E-CONTACT-005 | 1 | headless | Une fiche modifiée ne se perd pas sans confirmation, une adresse mal formée est refusée | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 2 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ | ✅ |
| E2E-MAILBOX-003 | 2 | headless | Rattacher ses boîtes depuis « Mes boîtes » en un geste — titulaire et membre | ✅ | ✅ |
| E2E-MAILBOX-006 | 1 | headless | Après le rattachement, l'identité d'expéditeur et la signature sont déjà là | ✅ | ✅ |
| E2E-MAILBOX-004 | 1 | headless | Ajouter une BAL déléguée par saisie — et refus de sa propre adresse | ✅ | ✅ |
| E2E-MAILBOX-005 | 1 | headless | Le délégataire refusé par l'opérateur perd l'accès, en ligne puis hors ligne ; le titulaire garde le sien | ✅ | ✅ |
| E2E-AUDIT-001 | 1 | headless | Le titulaire lit au journal le message supprimé par son délégataire, au nom du délégataire | ✅ | — |
| E2E-AUDIT-002 | 1 | headless | Le journal d'audit montre chaque action sur un mail | ✅ | — |
| E2E-SHARED-001 | 1 | headless | Une boîte partagée, une base — le patient rattaché par le titulaire est vu du délégataire, la signature reste à chacun | ✅ | ✅ |
| E2E-SHARED-002 | 1 | headless | Le délégataire écrit pour le compte du titulaire — le destinataire voit qui a écrit, sa réponse revient à la boîte | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |
| E2E-SESSION-004 | 1 | headless | Sur un appareil partagé, la personne suivante n'arrive jamais dans la boîte de la précédente | ✅ | ✅ |
| E2E-AI-002 | 1 | headless | Un délégataire interroge l'assistant dans la boîte qu'il a ouverte | ✅ | ✅ |
| E2E-MAILBOX-007 | 1 | headless | Après un changement de boîte, l'onglet Patients ne montre plus rien de la précédente | ✅ | ✅ |
| E2E-ERROR-001 | 1 | headless | Une erreur affiche un code et une référence à transmettre au support | ✅ | ✅ |

**Divergences temporaires ouvertes** (2) :

- E2E-SEARCH-001 [mobile] — le mobile adopte le formulaire à un seul niveau avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-008 [mobile] — les critères médicaux arrivent sur le mobile avec la refonte mobile — résorbée par task-451

**Parité : verte** — aucun écart entre le catalogue et les suites.

## Branches

- `api-mail` (pushed) : feat/task-444-recherche-reponse-enrichie-extraits — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-444-recherche-reponse-enrichie-extraits
- `dtos-mss` (pushed, paresseuse) : branche créée par `/develop` au premier changement de contrat (même nom).

## Timings

*(généré par `tools/timing/report.sh --task task-444 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 20 s | — | — | — | — |
| /develop | ok | 41 min 05 s | 7 (41 s) | 5 (9 min 10 s) | — | dtos-mss 1B/0T, api-mail 6B/5T |
| /sonar | ok | 21 min 40 s | 3 (1 min 01 s) | 12 (16 min 15 s) | 4 (1 min 29 s) | 2 itération(s), api-mail 3B/12T |
| /lint-angular | skipped | 0.4 s | — | — | — | client-angular non touché (Repos: api-mail, dtos-mss) |
| /lint-mobile | skipped | 0.4 s | — | — | — | client-mobile non touché (Repos: api-mail, dtos-mss) |
| /e2e | ok | 20 min 19 s | — | — | — | e2e ×3 (19 min 27 s) |
| **Total cycle** | | **1 h 23 min** | **10 (1 min 42 s)** | **17 (25 min 26 s)** | **4 (1 min 29 s)** | |

Autres commandes mesurées : nuget-wait ×1 (20 s), restore ×1 (23 s)
