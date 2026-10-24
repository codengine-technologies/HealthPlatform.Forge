# todo-task-388.md — Annuaire Santé : les finitions relevées en revue de task-386

**Repos**: dtos-mss, api-mail, client-mobile, client-blazor, client-angular
**Dependencies**: done-task-386 (archivée)
**Epic**: E009
**Single frontend**: false
**Priorité**: **4** — aucun défaut bloquant ; quelques cas rares où le médecin lit un message technique ou ambigu,
et une combinaison de critères qui part en recherche longue.

> **Origine.** Seconde revue indépendante de task-386 (2026-10-23, `tasks/archived/archived-task-386.md` § Code Review
> Summary, `questions/task-386.md`) : APPROVED avec suggestions non bloquantes, regroupées ici.

## Objective

Terminer la recherche dans l'annuaire santé : refuser une combinaison encore trop large, ne jamais afficher de
message technique ni de cause fausse au médecin, et éviter les recherches lancées deux fois.

### Périmètre

- **(a) Spécialité + organisation de moins de 3 caractères, sans lieu** (« Médecine générale » + « CH ») : acceptée
  aujourd'hui alors que « CH » seul est refusé ; elle cherche tous les établissements dont le nom commence par « CH »
  et finit presque toujours incomplète. → Exiger **3 caractères** pour l'organisation dans ce cas aussi (API,
  weda2, mobile, Blazor — même motif partout).
- **(b) Réponse non FHIR de la passerelle** (page HTML de maintenance renvoyée en 200, corps illisible) : donne
  aujourd'hui une erreur serveur (500). → La classer « annuaire indisponible » (503 `DIRECTORY_UNAVAILABLE`, ou
  incomplétude `unavailable` si d'autres appels ont abouti).
- **(c) Mobile — message technique brut** : une coupure réseau (statut 0), un 502 / 504 de proxy ou un 503 sans code
  affiche « Http failure response for … » (l'URL, critères compris). → Message générique par statut, comme weda2 ;
  jamais l'URL ni la requête.
- **(d) Blazor** :
  - une requête qui n'est pas partie (session absente, annulation) s'affiche « annuaire indisponible » → message
    adapté (session) ou rien (annulation) ;
  - Entrée pendant une recherche en cours en lance une seconde → ignorée tant qu'une recherche tourne (bouton déjà
    désactivé, clavier aligné).
- **(e)** api-mail : le commentaire XML `<summary>` de `ValidateSearchCriteria` est resté sur
  `EnsureNoReservedCharacters` → le replacer.

**Hors périmètre, à arbitrer (question ci-dessous)** : échapper `, | $ \` dans `AnnuaireQuery` plutôt que les
refuser ; partager les règles C# API / Blazor via `dtos-mss`.

## Gherkin

```gherkin
Feature: Directory search finishing touches

  Scenario: A specialty with a very short organisation name needs a place
    When the doctor searches by specialty and an organisation name of two letters, without a place
    Then the doctor is told to enter at least three letters of the organisation or a place
    And no search is run

  Scenario: The national directory answers with a maintenance page
    Given the national directory answers with something that is not directory data
    When the doctor searches by name
    Then the doctor is told the directory is temporarily unavailable

  Scenario: The network drops during a search on mobile
    Given the doctor's phone loses its connection during a directory search
    Then the doctor reads a plain message inviting them to try again
    And never a technical message or the search address

  Scenario: Pressing Enter twice does not run two searches
    Given a directory search in progress
    When the doctor presses Enter again
    Then a single search runs
```

## Definition of Done

- [ ] Build et tests verts : api-mail, weda2, client-mobile, client-blazor
- [ ] Test d'intégration de bout en bout pour `GET /api/v1/Directory/practitioners/search` : spécialité + organisation
      de 2 caractères sans lieu → 400 avec le motif, **aucun appel** à l'annuaire (faux annuaire) ; spécialité +
      organisation de 3 caractères sans lieu → acceptée ; vus rouges (règle 1b)
- [ ] Test d'intégration de bout en bout pour la même route : le faux annuaire rend un 200 au corps non FHIR (HTML) →
      503 `DIRECTORY_UNAVAILABLE` lu dans la réponse réelle ; si un appel précédent a abouti → 200 + issue
      `incomplete;reason=unavailable` ; vus rouges (règle 1b)
- [ ] weda2, mobile, Blazor : même règle (a) et même motif que l'API, test de composant rouge d'abord
- [ ] Mobile : statut 0, 502, 504, 503 sans code → message générique ; test de composant vérifiant que le message
      ne contient ni l'URL ni les critères
- [ ] Blazor : requête non partie → message de session (ou aucun pour une annulation) ; Entrée pendant une recherche
      → un seul appel au service (test bUnit)
- [ ] api-mail : commentaire XML de `ValidateSearchCriteria` replacé
- [ ] Aucun nom recherché ni URL de requête dans les messages affichés ni dans les journaux
- [ ] Scénario E2E-CONTACT-001 : attendu inchangé (refus d'une recherche trop large déjà couvert) — **pas** de montée
      de version ; à revoir si l'humain en décide autrement

## Manual Test Plan

1. weda2, mobile, Blazor — Annuaire : spécialité « Médecine générale » + organisation « CH », sans lieu → motif
   affiché, bouton inactif, aucune requête dans Seq. Avec « CHU » → la recherche part.
2. Mobile en mode avion, lancer une recherche → message simple « réessayez », sans adresse technique.
3. Blazor : lancer une recherche et appuyer plusieurs fois sur Entrée → une seule recherche dans Seq.
4. api-mail local avec `FhirOptions__BaseUrl` pointant vers une page HTML (serveur statique local) → « annuaire
   indisponible » dans les trois clients.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 (volet Annuaire Santé de la messagerie MSSanté)
- **Exigences DSR honorées** : RG-E009-022 (SC.MSS/UX.41, recherche multicritères) et RG-E009-026 (ANN/va1.04,
  appels unitaires en temps réel via l'API FHIR) — robustesse et lisibilité, aucune exigence nouvelle
- **INS** : non applicable — recherche de professionnels, aucune donnée patient
- **Authentification PS** : inchangée — PSC (e-CPS), niveau eIDAS substantiel
- **Habilitations** : inchangées — l'annuaire est consultable par tout praticien connecté
- **Interop CI-SIS** : FHIR R4, ressources `Practitioner`, `PractitionerRole`, `Organization` de l'Annuaire Santé
  (profils `as-dp-*`) ; aucun changement de requête hors (a) et (b)
- **Tracé PGSSI-S** : inchangé — un évènement de synthèse par recherche, sans les valeurs saisies
- **Consentement patient** : non applicable
- **Référentiels métier** : TRE-R38 spécialités ordinales (inchangé)
- **Hébergement HDS** : inchangé — données publiques de l'annuaire, aucun stockage nouveau
- **AIPD / impact RGPD** : inchangé

## Question (humain, avant `/start`)

> Faut-il **échapper** `, | $ \` dans les critères (recherche littérale de « dup,a ») plutôt que les **refuser** (400
> avec motif, comportement actuel) ? L'échappement est la forme FHIR normale mais doit d'abord être vérifié sur la
> passerelle de l'ANS. Et faut-il partager les règles C# entre l'API et Blazor via `dtos-mss` (une seule copie, au
> prix d'un cycle de publication) ? Par défaut, cette task garde le refus et les deux copies.

## Extension du périmètre (humain, 2026-10-24)

> Ajoutée après la première revue, à la demande de l'humain, et incluse dans task-388. Les PR déjà ouvertes reçoivent
> les nouveaux commits ; `dtos-mss` reçoit sa branche (paresseuse) et sa PR.

- **(f) Icônes des types de contact (weda2)** : le professionnel porte le stéthoscope, le patient une personne, dans la
  liste des contacts et dans le filtre « Types de contact » (déjà fait, code seul).
- **(g) Profession et spécialité d'un contact, et suggestions de destinataires lisibles** :
  - `dtos-mss` : `ContactDto.Profession` et `ContactDto.Specialty` (libellés, facultatifs) ;
  - api-mail : deux colonnes nullables sur `Contacts` (migration MailDb), lues et écrites par `ContactRepository`,
    longueur bornée (400 au-delà) ; l'enrichissement depuis un CDA remplit `Specialty` au lieu d'une étiquette ;
  - import depuis l'annuaire (weda2, mobile, Blazor) : profession et spécialité vont dans les champs dédiés, **plus**
    dans les étiquettes ;
  - rédaction (A, Cc, Cci) de **weda2 et du mobile** : chaque suggestion montre l'avatar avec l'icône du type de
    contact, le nom, la spécialité dessous quand elle est connue, et l'adresse à droite.

- **(h) Spécialité visible dans la liste des contacts** (weda2, mobile, Blazor) : sous le nom, la spécialité, à défaut
  la profession, comme dans les suggestions. Corrige une régression de (g) : l'import n'écrivant plus d'étiquettes, un
  contact importé n'affichait plus sa spécialité dans la liste.
- **(i) Profession et spécialité modifiables dans la fiche** (weda2, mobile, Blazor) : profession en texte libre ;
  spécialité en texte libre avec suggestions tirées de la liste de l'annuaire (`GET …/Directory/specialties`).
  Un nouvel import depuis l'annuaire remplace la valeur saisie (l'annuaire fait foi) ; l'enrichissement CDA ne
  remplace jamais.
- **(j) Fiche de modification d'un contact sans défilement** (weda2) : mise en page compacte, sur deux colonnes.

- **(k) Fiche d'un contact redessinée (weda2)**, d'après la maquette fournie par l'humain le 2026-10-24 :
  - page centrée, avec un fil d'Ariane ;
  - en-tête : initiales, nom, badge « RPPS Certifié » (seulement pour un contact importé de l'annuaire qui a un RPPS),
    sous-ligne « spécialité • organisation • Fiche mise à jour le … » ;
  - quatre cartes : identité et type ; activité et référencement (profession, spécialité, RPPS avec contrôle de format,
    téléphone) ; adresses MSSanté (une ligne par adresse avec cadenas et badge « Par défaut ») ; étiquettes en pastilles
    et notes ;
  - actions en haut et en pied de page.
  Les identifiants et les libellés de boutons utilisés par les suites e2e sont conservés.

**Décisions de l'humain (2026-10-24)** :
1. Pas de récupération des contacts existants : les champs se remplissent au fil des imports et des enrichissements.
2. À l'import depuis l'annuaire, champs dédiés seulement : aucune étiquette n'est plus ajoutée ; les étiquettes
   existantes ne sont pas touchées.
3. Nouvel affichage des suggestions dans weda2 et le mobile.

### Definition of Done — extension

- [ ] Build et tests verts : dtos-mss, api-mail, weda2, client-mobile, client-blazor
- [ ] `dtos-mss` publié par la CI ; `api-mail` et `client-blazor` passés à la nouvelle version du paquet
- [ ] Migration MailDb : deux colonnes nullables, contacts existants inchangés (valeurs nulles), descente testée
- [ ] Test d'intégration de route `POST`/`PUT`/`GET /api/v1/Contact` : profession et spécialité relues dans la réponse
      et en base ; longueur dépassée → 400 ; vus rouges (règle 1b)
- [ ] Enrichissement CDA : la spécialité va dans `Specialty`, plus dans les étiquettes (test vu rouge)
- [ ] weda2, mobile, Blazor : l'import depuis l'annuaire remplit `profession` / `specialty` et n'ajoute aucune
      étiquette (tests rouges d'abord)
- [ ] weda2 et mobile : suggestion de destinataire = avatar + icône du type, nom, spécialité (si connue), adresse à
      droite ; tests de composant rouges d'abord ; `data-testid` existants conservés (suites e2e inchangées)
- [ ] weda2 : icônes de type de la liste, du filtre et des suggestions tirées d'une seule source

### Manual Test Plan — extension

5. weda2 — Contacts : un professionnel porte le stéthoscope, un patient une personne (liste et filtre).
6. Importer un praticien depuis l'annuaire (weda2, puis mobile) : la fiche n'a aucune nouvelle étiquette ; dans une
   rédaction, taper son nom → avatar, icône stéthoscope, nom, spécialité dessous, adresse à droite.
7. Un contact sans spécialité (créé à la main) : la suggestion montre le nom sans ligne vide.
8. Liste des contacts (weda2, mobile, Blazor) : un contact importé montre sa spécialité sous le nom.
9. Fiche d'un contact (weda2, mobile, Blazor) : modifier la profession et choisir une spécialité suggérée (ou en
   taper une autre), enregistrer, rouvrir : les valeurs sont conservées et la liste les affiche.
10. weda2 — fiche de modification sur un écran de portable (1366×768) : tous les champs visibles sans défilement.

## Develop log

**2026-10-23 — `/develop` (forge).** api-mail `24599977` + `09634f48` ; client-mobile `ffdf47c` + `9cf662b` ;
client-blazor `4efdebc` + `b00338d` ; weda2 en code seul (non commité). Branches poussées.

- **(a)** Spécialité + organisation de moins de 3 caractères sans lieu : 400 avec le motif de l'organisation, aucun
  appel (API) ; même règle et même motif dans weda2, mobile et Blazor. Spécialité + organisation de 3 caractères, ou
  avec un lieu : acceptée. Test de route vu rouge avant le correctif, puis mutation M14 rouge.
- **(b) Faux positif de la revue de task-386** : une page HTML en 200 — annoncée `text/html` **ou** `application/fhir+json`
  — est déjà rejetée par le client FHIR (`FhirOperationException`) et classée « indisponible » par la passerelle.
  Aucun changement de code ; deux tests de route ajoutés en garde (503 sans réponse ; `incomplete;reason=unavailable`
  après une première réponse) et le faux annuaire sait servir une page de maintenance. Ces tests n'ont pas pu être
  vus rouges : il n'y avait rien à corriger.
- **(c)** Mobile : statut 0, 502, 504, 503 sans code → « annuaire indisponible » ; refus sans motif lisible → message
  simple ; jamais le message technique d'Angular (adresse de la requête). `problemMessage` (sur `problemOf`) dans
  `http-error.util`. Tests vus rouges par mutation.
- **(d)** Blazor : requête non partie faute de session → « Votre session a expiré » (`GetOutcome.NotAuthenticated`,
  code `CLIENT_NOT_AUTHENTICATED`) ; recherche annulée → exception d'annulation, pas un échec affiché ; Entrée pendant
  une recherche ignorée (test bUnit vu rouge par mutation).
- **(e)** Commentaire XML de `ValidateSearchCriteria` replacé.
- **Tests** : api-mail application 111 / route 51 ; weda2 `mss` 1 089 ; mobile 1 192 ; Blazor 471.
- **Passe qualité (§Q)** : appliqué — règle organisation réécrite plus simplement dans les quatre portages
  (comportement identique) ; `problemMessage` réutilise `problemOf` ; `isDirectoryUnavailable` mobile devenu mort,
  retiré ; double garde `_isLoading` Blazor ramenée à une. Écarté : fusionner les listes de réponses du faux annuaire
  (fixture de test) ; `PostOutcome.NotSent` mêle aussi session absente et réseau (hors task).
- **Question de la task** : défaut appliqué (refus de `, | $ \`, deux copies des règles C#).

**2026-10-24 — `/develop`, extension (f) et (g).** dtos-mss `fix/task-388-annuaire-finitions` (paresseuse, créée
ici) ; HealthPlatform.Dtos.Mss **533.0.0** publié par la CI (run 533) ; api-mail `bcbe1b0d` (bump) + `673d2082` ;
client-blazor `11127fb` (bump) + `d99c195` + `2c8d8cf` ; client-mobile `ae166b9` + `105cb05` ; weda2 en code seul.

- **(f)** weda2 : icônes de type inversées (professionnel = personne, patient = stéthoscope) dans la liste et le filtre.
  Test rouge d'abord (`expected 'user' to be 'stethoscope'`). Les trois écrans lisent désormais `contact-type.util`.
- **(g) contrat et API** : `ContactDto.Profession` / `Specialty` (256 car.) ; colonnes `Contacts.Profession` /
  `Specialty` (migration `20261024120000`, nullables, aucune récupération depuis les étiquettes) ; `ContactRepository`
  lit et écrit les deux champs ; `InputSanitizer.SanitizeLabel` (pas d'encodage HTML) ; l'enrichissement CDA remplit
  `Specialty` quand la fiche n'en a pas, ne la remplace jamais, n'ajoute plus d'étiquette, ignore un libellé hors contrat.
- **Règle 1b** — `ContactProfessionSpecialtyEndpointIntegrationTests` (vraie route, PostgreSQL réel) et
  `ContactProfessionSpecialtyMigrationTests`, vus rouges par mutation :
  M16 lecture retirée (`MapToDto`) → 4 rouges ; M17 écriture retirée (`UpdateAsync`) → 2 ; M18 enrichissement ramené
  aux étiquettes → `TheCdaEnrichment_FillsTheSpecialty…` ; M19 enrichissement qui écrase → `…NeverReplacesAKnownSpecialty` ;
  M20 libellé encodé (`Sanitize`) → 2 ; M21 descente incomplète → `TheColumns_GoDownAndComeBack`. Le 400 au-delà de
  256 caractères vient de l'attribut `[MaxLength]` du contrat (validation du modèle), non mutable dans ce dépôt.
  > **Piège rencontré** : une mutation restaurée par `shutil.move` garde la date de la copie, plus ancienne que les
  > binaires mutés : MSBuild ne recompile pas, et la mutation suivante s'exécute sur un binaire encore muté (M18 et
  > M19 d'abord faux). Rejouées après `touch` des fichiers restaurés : chacune rouge sur son test. Consigné dans
  > `conventions/csharp.md`.
- **Imports depuis l'annuaire** : weda2, mobile et Blazor remplissent `profession` / `specialty` (libellés), sans
  étiquette. Défauts trouvés en route : weda2 rangeait des **codes** dans les étiquettes quand le libellé manquait ;
  le mobile **remplaçait** les étiquettes du médecin par celles de l'annuaire ; Blazor recopiait la fiche champ par
  champ — sans les deux champs, l'enregistrement les aurait effacés (recopie et duplication corrigées).
- **Rédaction (weda2 et mobile)** : chaque suggestion (A, Cc, Cci) montre l'avatar avec l'icône du type, le nom, la
  spécialité (à défaut la profession) dessous et l'adresse à droite ; `data-testid` existants conservés. weda2 :
  composant partagé `ContactAvatarComponent` (liste et rédaction). Mobile : stéthoscope du design system weda2 livré
  dans `assets/icons` (Ionicons n'en a pas). Tests de rendu rouges d'abord (weda2) ; mobile prouvé par mutation
  (icône du professionnel et ligne de spécialité retirées → 5 rouges).
- **Tests** : api-mail domain 195, infra 695, api 1 277, application 3 615, intégration 973 (16 ignorés) ; weda2
  `mss-lib` 1 102 ; mobile 1 203 ; Blazor 475. Un rouge non lié pendant la suite complète :
  `SeededThreadsAreCountableTests.SeveralDistinctThreadSizesReachTheCounter` (`Uid` tiré au hasard dans une base
  partagée → collision de clé unique), vert rejoué seul — instabilité préexistante, à corriger par une task.
- **Passe qualité (§Q)** : `SpecialtyOf` passe par `SanitizeLabel` ; enveloppes d'icônes retirées de la liste weda2
  (utilitaire exposé, `@let`) et test redondant supprimé ; variantes de couleur mortes retirées ; `@let` dans la
  rédaction mobile ; test Blazor allégé. Écarté : remonter le `ng-template` au niveau de la liste (restructure un bloc
  existant), avatar partagé sur la carte de l'annuaire (changement visuel), copie unique de `ContactDto` dans Blazor
  (reprendrait `DefaultMssAddress`, changement de comportement), import côté serveur (suite).
- **Non couvert par un test unitaire** : la recopie de la fiche dans `Contacts.razor` (Blazor) — vérifiée à la lecture.

**2026-10-24 — `/develop`, extension (h), (i), (j).** api-mail `d1343c18` ; client-mobile `cfb0e80` + `0d9882b` ;
client-blazor `6bf8c09` + `465434f` ; weda2 en code seul (design system compris). Contrat inchangé (533.0.0).

- **(h) Spécialité dans la liste des contacts.** Sous le nom s'affiche la spécialité, ou à défaut la profession :
  weda2 (`contactSubtitle`), mobile (même utilitaire) et Blazor (`Contacts.SubtitleOf`).
- **(i) Fiche modifiable.** La profession est en saisie libre. La spécialité aussi, avec les libellés de l'annuaire proposés :
  - weda2 : `<datalist>` native, grâce à une nouvelle entrée facultative `list` sur `ds-input` (design system) ;
  - mobile : correspondance sans accent ni casse, cinq propositions au plus, choisies d'un toucher ;
  - Blazor : `RadzenAutoComplete`.
  Un patient n'a ni l'une ni l'autre. La règle est désormais portée par l'API (`SanitizeContactDto`), pour tous les
  écrivains.
- **(j) weda2 : la fiche tient sur deux colonnes** (identité à gauche, messagerie et notes à droite, boutons dessous).
  Contrôle visuel sur le banc e2e (weda2 servi en `--serve-only`, Playwright) : à **1366×768** avec deux adresses,
  `formScroll = 0`, et les boutons s'arrêtent à 698 px pour une hauteur de 768 : la fiche est visible en entier. Même
  résultat à 1920×1080. La spec de capture était temporaire, elle a été supprimée.
- **Blazor** : les icônes de type de la liste et du filtre sont alignées sur weda2 (stéthoscope pour un professionnel,
  personne pour un patient).
- **Preuves rouges** :
  - weda2 : tests de rendu (`mss-contacts-render.component.spec.ts`) et tests d'instance rouges d'abord ; `ds-input`
    prouvé par mutation (`[attr.list]` retiré).
  - mobile : une mutation combinée (champ retiré de `toContactDto`, ligne de liste retirée, suggestions non
    filtrées) fait échouer les 4 tests visés.
  - Blazor : une mutation (`SubtitleOf` vidé, nettoyage de la spécialité retiré) fait échouer les 3 tests visés.
  - API : `APatient_IsStoredWithoutProfessionNorSpecialty` rouge avant le correctif (M22).
  > **Test qui mentait, corrigé avant de servir** : le test de rendu « deux colonnes » passait sans les colonnes.
  > `identity?.querySelector(...)` vaut `undefined`, et `not.toBeNull()` l'accepte. Il exige désormais l'existence de
  > chaque colonne (`toBeTruthy`). Consigné dans `conventions/angular.md`.
  > **Effet de bord observé en mutation, côté mobile** : les tests de contacts mutés laissent des `ion-modal`
  > ouvertes, et les 4 tests de rendu de la rédaction échouent en cascade. Sur le code restauré, tout est vert.
  > Retirer les modales au début de ces tests cassait leur propre modale : cette idée a été annulée.
- **Tests** : weda2 `mss-lib` 1 109 ; design system 1 925 ; mobile 1 207 ; Blazor 481 ; api-mail (route) 12.
- **Passe qualité (§Q)** :
  - appliqué : règle « patient » descendue dans l'API ; normalisation partagée côté mobile (`normalize`), libellés
    normalisés une fois, garde de chargement dans `loadSpecialties` ; icônes du filtre Blazor ; `datalist` qui
    parcourt directement les spécialités ; styles du sous-titre et de l'adresse regroupés ;
  - écarté : sous-titre calculé dans le contrat (republication du paquet) ; nettoyage des champs côté client, qui
    double celui de l'API (inoffensif, testé) ; boucle `@for` sur les trois filtres (structure existante) ;
    `ContactEmailInput` (Blazor) encore sur `medical_services`, en suite.

**2026-10-24 — `/develop`, (k) fiche redessinée (weda2, code seul).**

- Tests de rendu rouges d'abord (en-tête, badge certifié, quatre cartes, badge « Par défaut », pastilles, libellés des
  boutons), puis test d'instance des étiquettes (Entrée et virgule ajoutent, sans doublon ; × retire ; la saisie en
  cours part à l'enregistrement). Résultat : `mss-lib` 1 117 verts, lint 0 erreur, build `weda2` ✓.
- Écarté de la maquette, car aucune donnée ne le porte ou le libellé serait faux :
  - « Chiffré TLS » ;
  - le type de chaque boîte (« nominative », « organisationnelle ») ;
  - « Prévisualiser la fiche ».
  « Valide » sur le RPPS devient « Format valide » : c'est un contrôle de format, pas une vérification à l'annuaire.
- Contrôle visuel **non fait** : le banc e2e n'a pas pu démarrer, car le port 5052 était occupé par l'API locale de
  l'humain. À refaire, ou à vérifier directement dans weda2.

## Sonar log
- Phase 1 (new code) : ✓ Quality Gate OK au premier passage, new_coverage = 97,1 %, 0 finding
- Phase 2 (legacy) : 0 itération — cibles projet atteintes
- Build / tests : ✓ green (Release ; domain 195, application 3 604, infrastructure 695, api 1 277, intégration 967 + 16
  ignorés préexistants)

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 97,0 % | 97,1 % | +0,1 pt |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 0 | 0 | 0 |
| Coverage (projet) | 98,1 % | 98,1 % | 0 |
| Duplication | 0,4 % | 0,4 % | 0 |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

### Sonar — extension (2026-10-24)

- Phase 1 (new code) : ✓ Quality Gate OK au premier passage, new_coverage = 97,1 %, 0 finding (migration exclue de
  l'analyse, comme les autres)
- Phase 2 (legacy) : 0 itération — cibles projet atteintes (98,1 %, A/A/A, 0 bug / vulnérabilité / smell / hotspot,
  duplication 0,4 %)
- Build / tests : ✓ Release ; domain 195, application 3 615, infrastructure 695, api 1 277, intégration 974 (16 ignorés)

### Sonar — extension (h)(i)(j) (2026-10-24)

- Phase 1 : ✓ Quality Gate OK, new_coverage 97,1 %, 0 finding ; Phase 2 : 0 itération (98,1 %, A/A/A, 0 smell)
- Tests : domain 195, application 3 615, infrastructure 695, api 1 277, intégration 975 (16 ignorés)

## Lint log
- **client-angular** (code seul, base `origin/next`, lint `tag:scope:mss`) — 0 itération : 0 erreur, 46 avertissements
  (aucun sur les fichiers de la task) ; Prettier ✓ ; tests affected ✓ 12 projets ; `weda2:build:production` ✓
  (avertissement budget initial 2,06 Mo / 2 Mo, préexistant).

- **client-angular, extension (2026-10-24)** — base `origin/next`, lint `tag:scope:mss` : 0 erreur (3 + 16
  avertissements, aucun sur les fichiers de la task), 0 itération. Tests affected ✓. Build affected : `weda2` ✓
  (budget initial 2,06 Mo / 2 Mo, avertissement : +2,6 Ko pour la task, 61,3 → 63,9 Ko au-delà) ; **`mss` (application
  autonome) et `prescription` en erreur de budget** (1,93 Mo et 1,26 Mo pour 1 Mo) — **préexistant** :
  `prescription` n'est pas touché par la task, et le dépassement de `mss` (930 Ko) est sans commune mesure avec la
  part de la task (~2,6 Ko, mesurée sur weda2). Non bloquant pour cette étape (aucun correctif appliqué) ; à signaler
  à l'humain (budgets de la branche `feature/nova-mss-weda-integration`).

- **client-angular, extension (h)(i)(j)** — lint `tag:scope:mss` 0 erreur ; lint `design-system` 0 erreur (entrée
  `list` de `ds-input`) ; tests affected ✓ 12 projets ; budgets `mss` / `prescription` toujours en erreur
  (préexistant, inchangé).

## Lint mobile log
- **client-mobile** — « All files pass linting » ; 0 itération, aucun commit ; build ✓ ; tests ✓ 1 192 (passe de
  `/develop`).

- **client-mobile, extension (2026-10-24)** — « All files pass linting » ; 0 itération, aucun commit ; build ✓ ;
  tests ✓ 1 203 (passe qualité de `/develop`).

- **client-mobile, extension (h)(i)(j)** — « All files pass linting » ; build ✓ ; tests ✓ 1 207.

## Branches
- `api-mail` (pushed) : fix/task-388-annuaire-finitions — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-388-annuaire-finitions
- `client-mobile` (pushed) : fix/task-388-annuaire-finitions — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/fix/task-388-annuaire-finitions
- `client-blazor` (pushed) : fix/task-388-annuaire-finitions — https://github.com/codengine-technologies/HealthPlatform.Client/tree/fix/task-388-annuaire-finitions
- `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` (au `/start` : `feature/nova-mss-weda-integration`, arbre propre) — humain gère branche, commit, push, PR TFS
- `dtos-mss` : non listé — aucun changement de contrat prévu ; question « partage des règles via dtos-mss » non tranchée → défaut de la task (deux copies)

> **Question de la task non tranchée au `/start`** : défaut appliqué — refus (400) de `, | $ \` conservé, pas d'échappement ; pas de partage via `dtos-mss`.

## Timings

*(généré par `tools/timing/report.sh --task task-388 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 25 s | — | — | — | — |
| /develop | ok | 25 min 40 s | 5 (1 min 14 s) | 19 (8 min 11 s) | — | client-mobile 2B/6T, client-blazor 0B/5T, api-mail 2B/7T, client-angular 1B/1T, extension (h)(i)(j) : liste, fiche, deux colonnes |
| /sonar | ok | 8 min 34 s | 3 (1 min 06 s) | 15 (20 min 27 s) | 6 (2 min 12 s) | api-mail 3B/15T, (h)(i)(j) : QG OK, 0 finding |
| /lint-angular | ok | 2 min 04 s | 3 (44 s) | 3 (4 min 41 s) | — | client-angular 3B/3T |
| /lint-mobile | ok | 6.7 s | 1 (8.6 s) | — | — | client-mobile 1B/0T |
| /e2e | failed | 22 min 20 s | — | — | — | e2e ×11 (1 h 06 min), E2E-DETAIL-001 mobile rouge (3e occurrence), questions/task-388.md |
| /review | ok | 7 min 29 s | 9 (1 min 14 s) | 8 (9 min 53 s) | — | api-mail 2B/2T, client-mobile 2B/2T, client-blazor 2B/2T, client-angular 2B/2T, dtos-mss 1B/0T, extension APPROVED ; PR dtos-mss #47 ; corps #307 #101 #96 mis à jour |
| /tech-writer | ok | 0.6 s | — | — | — | — |
| **Total cycle** | | **1 h 06 min** | **21 (4 min 28 s)** | **45 (43 min 13 s)** | **6 (2 min 12 s)** | |

Autres commandes mesurées : lint ×10 (1 min 32 s), nuget-wait ×1 (26 s)

## E2E log

Run de l'extension (h)(i)(j) (2026-10-24, après-midi) — **ROUGE**. Il remplace le run vert du matin (mobile 41/41,
Angular 49/49).

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail et client-mobile touchés | ❌ rouge | 40 verts, 1 rouge (E2E-DETAIL-001, deux essais) | 13 min 04 s |
| angular | api-mail et client-angular touchés | ✅ verte | 49 verts, 0 flaky, 1 quarantaine (E2E-COMPOSE-002, passée) | 7 min 12 s |

> **Blocage, motif « régression » au sens de la porte.** E2E-DETAIL-001 sur mobile a échoué aux deux essais, sur
> « le transfert arrive » (`functional.spec.ts:594`, étape 3 : transfert d'un message à deux pièces homonymes). C'est
> la **troisième occurrence** de cette instabilité : 2026-10-23, run 1 rouge puis relance flaky ; 2026-10-24 matin,
> vert ; 2026-10-24 après-midi, rouge.
> - **Sans lien démontré avec l'extension** : l'étape 1, qui choisit aussi un destinataire suggéré dans la rédaction
>   modifiée, passe. Le même échec existait avant ce changement (run 1 du 2026-10-23). Côté serveur, tous les
>   `sendmail` répondent 200 (Seq) ; le message envoyé n'arrive pas.
> - **Hypothèse non prouvée** : à l'étape 3, le test clique sur la suggestion « robert » puis envoie **sans attendre
>   la puce du destinataire**, ce que fait l'étape 1. Un clic qui ne prend pas laisserait « robert » partir comme
>   adresse : envoi accepté, rien de reçu. La trace ne conserve ni le corps de la requête ni les puces : non vérifié.
> - **Question posée à l'humain** : `questions/task-388.md`.

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task ; quarantaines : E2E-COMPOSE-002 (angular, task-350)
- Démontage : complet (ports libres)

**E2E : ROUGE** — 1 motif(s) de blocage.

**Bloquant** (1) :

- [mobile] rouge : « détail — Répondre et Transférer partent avec le message d’origine, même cliqués pendant son chargement » (E2E-DETAIL-001)

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
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ❌ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Écrire à l'adresse choisie d'un contact à plusieurs adresses, ou à son adresse par défaut | ✅ | ✅ |
| E2E-COMPOSE-005 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
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

## PRs

- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/47 — label `awaiting-human-merge`
  (extension ; version 533.0.0 déjà publiée par la CI et consommée par api-mail et client-blazor)
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/307 — label `awaiting-human-merge`
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/101 — label `awaiting-human-merge`
- `client-blazor` : https://github.com/codengine-technologies/HealthPlatform.Client/pull/96 — label `awaiting-human-merge`
- **Ordre de merge** : `dtos-mss` (#47) avant les autres. Les autres PR consomment déjà la version 533.0.0, publiée
  depuis la branche ; le merge de #47 ne fait que ramener le contrat sur `develop`.
- `client-angular` : code seul. L'humain gère le commit, le push sur TFS et l'ouverture de la PR. Fichiers modifiés,
  non commités, sur `feature/nova-mss-weda-integration` :
  - `front/libs/mss/src/core/models/contact.model.ts`
  - `front/libs/mss/src/core/utils/directory-search.util.ts` et `.spec.ts`
  - `front/libs/mss/src/core/utils/contact-type.util.ts` et `.spec.ts` (nouveaux)
  - `front/libs/mss/src/ui/contact-avatar/` (nouveau composant) et `front/libs/mss/src/ui/index.ts`
  - `front/libs/mss/src/features/contacts/mss-contacts.component.ts`, `.html`, `.scss`, `.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose.component.ts`, `.html`, `.scss`
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose-suggestions.component.spec.ts` (nouveau)

## Code Review Summary

**Verdict : APPROVED** — 0 bloquant, 4 suggestions.

**Validation (/review, 2026-10-23)**

| Repo | Build | Tests |
|---|---|---|
| api-mail | ✓ | ✓ 6 738 au total, 0 échec. Domain 195, application 3 604, infrastructure 695, api 1 277, intégration 967 ; 16 ignorés, préexistants |
| client-mobile | ✓ | ✓ 1 192/1 192 |
| client-blazor | ✓ hors `Mss.Console` (NU1100, source NuGet `github`, préexistant) | ✓ 471, 2 ignorés |
| client-angular (code seul) | ✓ `weda2` (budget initial 2,06 Mo / 2 Mo, préexistant) | ✓ `mss` 1 089 |

Pour Angular, aucun `npm ci` : `node_modules` était à jour, la voie e2e Angular venait de tourner dessus, et aucun serveur de développement n'écoutait.

**Règle 1b — comportement → test de route → preuve rouge**

| Comportement | Test | Preuve rouge |
|---|---|---|
| Spécialité + organisation de 2 caractères sans lieu → 400 avec le motif, aucun appel à l'annuaire | `Search_TooBroad_Is400_WithoutAnyDirectoryCall("SpecialtyCode=SM54&OrganizationName=CH")` | Rouge avant le correctif, puis mutation M14 (/develop) |
| Spécialité + organisation de 3 caractères sans lieu → acceptée | `Search_SpecialtyAndOrganisationWithoutPlace_IsAccepted` (« Cen ») | Idem |
| Page de maintenance en 200 → 503 `DIRECTORY_UNAVAILABLE` | `Search_DirectoryAnswersWithAMaintenancePage_Is503DirectoryUnavailable` (`text/html` et `application/fhir+json`) | **Mutation M15 (/review)**, voir ci-dessous |
| Page de maintenance après une première réponse → 200 `incomplete;reason=unavailable` | `Search_MaintenancePageAfterAFirstAnswer_Is200AnnouncedIncomplete` | Mutation M15 → rouge |

Le point (b) n'a demandé aucun changement de code : c'était un faux positif de la revue de task-386. /develop n'avait donc pas pu voir ces gardes rouges. La mutation M15 ferme ce manque : `FhirOperationException` est retirée du classement « indisponible » de `AnnuaireSanteGateway`, et les 3 tests passent au rouge. Le fichier est ensuite restauré par copie, la solution reconstruite, et les 3 tests repassent au vert.

**Revue par repo**

- **api-mail** — ✅
  - `ValidateSearchCriteria` : l'organisation est rognée, ce qui ferme aussi le cas « CH » entouré d'espaces, accepté jusqu'ici. L'ordre des contrôles est inchangé hors du cas (a).
  - Le commentaire XML est remis à sa place.
  - `FakeAnnuaireSante.ServeMaintenancePageWhen` est copié sous verrou, comme les autres réponses forcées.
- **client-mobile** — ✅
  - Le message d'erreur ne reprend jamais `HttpErrorResponse.message`.
  - Tout 5xx et le statut 0 donnent « indisponible ».
  - `problemMessage` réutilise `problemOf`.
  - Il ne reste aucune référence à `isDirectoryUnavailable` ni à `DIRECTORY_UNAVAILABLE`.
- **client-blazor** — ✅
  - `GetOutcome.NotAuthenticated` s'applique à tous les GET. Les autres consommateurs de `GetWithOutcomeAsync` (`FolderService.GetFolderAsync`, `MailService` pour le contenu) ne testent que le 404 : vérifié, aucun effet de bord.
  - La garde `_isLoading` est placée dans `Search()`, ce qui couvre le clic et Entrée.
- **client-angular** — ✅ `placeProblem` est identique aux trois autres portages.

**Suggestions (non bloquantes)**

1. Blazor : fermer le dialogue n'annule pas la recherche en cours, car le dialogue ne passe aucun jeton. La branche d'annulation de `DirectoryService` reste donc défensive.
2. `PostOutcome.NotSent` mêle encore session absente et panne réseau (même défaut que (d), côté POST). Hors de cette task.
3. Les règles existent en quatre copies (API, Blazor, weda2, mobile). Leur partage via `dtos-mss` reste la question ouverte de la task.
4. E2E-DETAIL-001 (mobile) a échoué 3 fois sur 4 essais pendant /e2e, sans lien avec cette task : voir le `## E2E log`. Ce test est inscrit au registre des flaky. **Une task de stabilisation est à ouvrir.**

### Revue de l'extension (2026-10-24)

**Verdict : APPROVED** — 0 bloquant.

**Validation (/review)**

| Repo | Build | Tests |
|---|---|---|
| dtos-mss | ✓ | sans objet |
| api-mail | ✓ | ✓ 6 756 : domain 195, application 3 615, infrastructure 695, api 1 277, intégration 974 (16 ignorés) |
| client-blazor | ✓ (projet de tests ; `Mss.Console` NU1100, préexistant) | ✓ 475, 2 ignorés |
| client-mobile | ✓ | ✓ 1 203 |
| client-angular (code seul) | ✓ `weda2` | ✓ `mss-lib` 1 102 |

**Règle 1b, extension**

| Comportement | Test de route | Preuve rouge |
|---|---|---|
| `POST`/`GET /api/v1/Contact` : profession et spécialité relues dans la réponse et en base (apostrophe intacte) | `AContactsProfessionAndSpecialty_AreReadBack_InTheResponseAndInTheDatabase` | M16 (lecture), M20 (encodage) |
| `PUT` : spécialité remplacée, profession effacée | `SavingTheContact_ReplacesTheSpecialty_AndClearsTheProfession` | M16, M17 (écriture) |
| Plus de 256 caractères → 400, rien en base | `ASpecialtyLongerThanTheContract_IsRefusedWith400_AndNothingIsStored` | Attribut `[MaxLength]` du contrat (validation du modèle), non mutable dans api-mail |
| Enrichissement CDA → `Specialty`, sans étiquette | `TheCdaEnrichment_FillsTheSpecialty_WithoutAddingATag` | M18 |
| Enrichissement CDA : ne remplace jamais une spécialité connue | `TheCdaEnrichment_NeverReplacesAKnownSpecialty` | M19 |
| Migration : contacts existants à `null`, étiquettes intactes ; descente puis remontée | `ContactProfessionSpecialtyMigrationTests` (2) | M21 |

**Points vérifiés à la lecture**

- **Les écrivains serveur gardent les deux champs.** L'import vCard (`VCardService`) et le service patient fusionnent dans le contact lu en base.
- **L'édition côté clients garde les deux champs.** weda2 envoie `...existing` ; le mobile passe par `toContactDto(form, base)` ; Blazor recopie désormais les deux champs.
- **Le cache Redis des contacts s'adapte seul.** Il sérialise le DTO, donc les nouveaux champs suivent. Une entrée en cache d'avant le déploiement n'a pas de spécialité tant qu'elle n'est pas invalidée, ce qui est sans gravité.
- **Pas d'injection possible.** `SanitizeLabel` retire balises et caractères de contrôle sans encoder ; Angular, Ionic et Razor échappent eux-mêmes à l'affichage.

**Suggestions (non bloquantes)**

1. **Blazor : une seule recopie de `ContactDto`.** Elle servirait à la fiche et à la duplication. Aujourd'hui `DefaultMssAddress` n'est pas recopié : c'est préexistant, et éditer une fiche dans Blazor efface l'adresse par défaut. À corriger par une task.
2. **Import depuis l'annuaire côté serveur.** Trois clients reproduisent la même correspondance et la même règle de fusion (l'annuaire l'emporte), alors que le CDA ne fait que compléter. Un point d'entrée serveur unique supprimerait la dérive. À faire par une task.
3. **Blazor : URL de mise à jour.** `ContactService.UpdateContactAsync` appelle `PUT api/v1/Contact/{Id.GetHashCode()}`, ce qui ressemble à un défaut préexistant. À vérifier hors task.
4. **weda2 : budgets de build.** Les budgets de `mss` (application autonome) et de `prescription` sont dépassés sur la branche `feature/nova-mss-weda-integration`. C'est préexistant : la task n'y ajoute qu'environ 2,6 Ko.
5. **Test d'intégration instable.** `SeededThreadsAreCountableTests` tire un `Uid` au hasard dans une base partagée : collision de clé possible. Une task de stabilisation est à ouvrir.

