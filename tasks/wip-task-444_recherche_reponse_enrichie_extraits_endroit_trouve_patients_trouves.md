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

## Branches

- `api-mail` (pushed) : feat/task-444-recherche-reponse-enrichie-extraits — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-444-recherche-reponse-enrichie-extraits
- `dtos-mss` (pushed, paresseuse) : branche créée par `/develop` au premier changement de contrat (même nom).
