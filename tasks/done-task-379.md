# todo-task-379.md — Contacts : la fiche et la rédaction gèrent toutes les adresses MSSanté du contact, avec une adresse par défaut au choix du médecin, et la recherche survit à une erreur

**Repos**: dtos-mss, api-mail, client-angular, client-mobile
**Dependencies**: — (aucune)
**Epic**: E009
**Single frontend**: false
**Priorité**: **2** — des adresses de messagerie de santé disparaissent à l'enregistrement d'un contact ; une seule erreur réseau rend la recherche muette jusqu'au rechargement.

> **Origine.** Audit de détection de bugs du client Angular du 2026-10-13
> (`Docs/audits/client-angular-audit-bugs-20261013.md`, **ANG-56, ANG-57** ; **ANG-58** écarté, voir ci-dessous).

## Ce qui est établi

- **ANG-57** — un contact a une **collection** d'adresses MSSanté, mais l'écran d'édition n'en gère qu'une :
  - plusieurs adresses arrivent par l'import depuis l'annuaire (`mss-contacts.component.ts:839`, toutes les boîtes du praticien) et par l'enrichissement automatique (`PractitionerContactService.cs:132-134`, ajout d'une adresse à un contact existant) ;
  - l'édition ne charge que `mssAddresses[0]` (`mss-contacts.component.ts:416`) et renvoie `[adresseSaisie]` (`:453`) ; `ContactRepository.cs:245, 693-695` remplace la liste entière : les adresses secondaires sont supprimées sans avertissement, et l'écran ne les montrant pas, la perte est invisible.
  - Côté api-mail, la collection est déjà stockée et restituée dans l'ordre (`SortOrder`) ; `ContactDto.PrimaryMssAddress` est calculé (`Dtos/ContactDto.cs:62`, première adresse).
  - Le client mobile gère déjà la collection dans la fiche contact (un champ multiligne, une adresse par ligne : `contact.model.ts:147, 166-182`) : référence pour le comportement attendu.
  - **Reproduction** : `POST /api/v1/Contact` avec deux adresses (ou import d'un praticien à deux boîtes), modifier le téléphone dans l'écran, enregistrer → `GET /api/v1/Contact/{id}` n'en renvoie plus qu'une.
- **Pas de notion d'adresse par défaut** — rien ne distingue une adresse choisie par le médecin : `ContactMssAddress` n'a que `Address` et `SortOrder` (`Contact.cs:74-90`), et `PrimaryMssAddress` vaut toujours la première adresse, qu'elle ait été choisie ou non.
- **Rédaction : un contact ne propose qu'une adresse** (angular et mobile) — les suggestions de destinataires affichent et insèrent `primaryMssAddress`, la première adresse seulement :
  - angular : `mail-compose.component.html:88, 128, 163`, `mail-compose.component.ts:849` ;
  - mobile : `mail-compose.component.html:117, 158, 199`, `mail-compose.component.ts:714`.
  - La recherche api-mail trouve pourtant un contact par **n'importe laquelle** de ses adresses (`ContactRepository.cs:312`) : taper la seconde adresse d'un praticien le fait apparaître, mais c'est la première qui est insérée.
- **Listes : seule la première adresse est visible** :
  - liste des contacts : angular `mss-contacts.component.html:605` (`primaryMssAddress`), mobile `contacts.page.html:128` (`contactAddress()`, `contacts.page.ts:591-593`) ;
  - résultats de l'annuaire : angular `mss-contacts.component.html:169-172` (`emails[0]`), mobile `contacts.page.html:434-438` (aucune adresse) — l'utilisateur ne voit pas ce qu'il importe.
- **Import depuis l'annuaire angular : doublon au lieu de fusion** — `importFromDirectory` (`mss-contacts.component.ts:830-859`) crée toujours un nouveau contact, et `ContactRepository.CreateAsync` (`:101-140`) ne dédoublonne pas : réimporter un praticien déjà connu crée un second contact au lieu de compléter ses adresses. Le mobile le fait déjà (`contacts.page.ts:673-751` : `findExistingForPractitioner` par RPPS ou adresse, `mergeAddresses`, mise à jour du contact existant).
- **Déjà correct, rien à faire** (hors adresse par défaut) : api-mail (collection ordonnée, recherche sur toutes les adresses, enrichissement `PractitionerContactService` qui ajoute sans écraser, vCard export/import multi-`EMAIL` avec fusion `VCardService.cs:118-136`) ; recherche locale mobile sur toutes les adresses (`matchesTerm`, `contacts.page.ts:625-638`) ; saisie des adresses dans la fiche contact mobile.
- **ANG-56** — `patient-search.component.ts:59-77` (`catchError` après `switchMap`) et `mss-contacts.component.ts:1003-1022` : une erreur HTTP termine le flux de recherche ; toute frappe suivante reste sans effet (« Aucun patient trouvé »). Le chargement initial des patients du jour n'est pas annulé.
- **ANG-58 écarté (faux positif)** — l'hypothèse de l'audit (« l'annuaire expose des e-mails non MSSanté ») est fausse :
  - l'annuaire santé FHIR ne contient **que des adresses MSSanté** : garder tous les `telecom` de type e-mail (`mss-contacts.component.ts:829-858`, `FhirBundleParser.cs:270-275, 384-391`) n'importe donc que des boîtes MSSanté ;
  - une messagerie MSSanté **ne peut pas écrire à une adresse hors espace de confiance** : même une adresse ordinaire saisie à la main ne ferait sortir aucune donnée de santé, l'envoi serait refusé par l'opérateur.
  
  Aucun filtrage de l'annuaire n'est à ajouter.

## Objective

Que la fiche d'un contact **affiche et gère toutes** ses adresses MSSanté, pour qu'un enregistrement n'en fasse perdre aucune, que le médecin puisse en désigner une **par défaut**, que la rédaction propose cette adresse-là ou, à défaut, **toutes** les adresses, et que les recherches de patients et de contacts survivent à une erreur passagère.

### Périmètre

1. **Adresse par défaut** (dtos-mss, api-mail) :
   - `ContactDto.DefaultMssAddress` (`string?`, `null` = aucune adresse par défaut) ; `PrimaryMssAddress` devient `DefaultMssAddress ?? MssAddresses[0]` (listes, initiales inchangées sinon).
   - Stockage : colonne `IsDefault` sur `ContactMssAddress` (migration MailDb), au plus une par contact ; lecture et écriture dans `ContactRepository` (`MapToDto`, `AddContactRelations`).
   - Création / mise à jour : une `DefaultMssAddress` absente de `MssAddresses` est refusée (400).
   - La désignation survit à ce qui touche aux adresses sans l'avoir demandé : fusion de l'annuaire, enrichissement `PractitionerContactService`, import vCard. Supprimer l'adresse par défaut retire la désignation (le contact n'a plus d'adresse par défaut).
   > **Contrat changé** → `/publish-dtos` requis après merge `dtos-mss`, pour que `api-mail` consomme la nouvelle version du package ; modèles TypeScript `ContactDto` angular et mobile alignés à la main.
2. **Fiche contact** (création et modification) :
   - angular : collection d'adresses — afficher toutes les adresses, en ajouter, en modifier, en supprimer ; l'ordre est conservé ; l'enregistrement renvoie la liste complète ;
   - angular et mobile : le médecin marque une adresse « Par défaut » ou aucune (choix « Aucune » toujours possible). Mobile : la saisie multiligne existe déjà, ajouter le choix de l'adresse par défaut parmi les adresses saisies.
3. **Suggestions de destinataires à la rédaction** (angular et mobile, recherche et favoris, À, Cc et Cci) :
   - contact **avec** adresse par défaut → **une seule** suggestion, l'adresse par défaut ;
   - contact **sans** adresse par défaut → **une suggestion par adresse** (nom + adresse), dans l'ordre de la fiche ;
   - exception : si le texte tapé correspond à une autre adresse du contact que celle par défaut, cette adresse est proposée aussi (le médecin qui tape une adresse précise doit pouvoir l'obtenir) ;
   - choisir une suggestion insère cette adresse-là ;
   - un contact à une seule adresse reste affiché comme aujourd'hui.
4. **Affichage de toutes les adresses** (angular et mobile) : liste des contacts (adresse par défaut ou première + « +N », ou liste complète ; l'adresse par défaut est signalée) et résultats de l'annuaire (toutes les boîtes du praticien, avant import).
5. **Import depuis l'annuaire angular aligné sur le mobile** : contact existant retrouvé par RPPS ou adresse → mise à jour avec fusion des adresses (sans doublon, ordre existant et adresse par défaut conservés) ; sinon création.
6. **Recherches** : `catchError` dans le `switchMap`, message d'erreur, recherche toujours active ; chargement initial annulé à la première frappe.

Hors périmètre :
- filtrage des adresses de l'annuaire (ANG-58 écarté) ;
- contrôle de version / PATCH côté api-mail (deux onglets ou un enrichissement concurrent qui s'écrasent) : risque distinct, non traité ici ;
- adresse par défaut dans l'export/import vCard (`EMAIL;TYPE=PREF`) : non traité, l'import vCard conserve simplement la désignation existante.

## Definition of Done

- [ ] Build et tests verts : dtos-mss, api-mail, weda2, client-mobile
- [ ] `/publish-dtos` exécuté après merge `dtos-mss` ; `api-mail` bumpé sur la nouvelle version du package
- [ ] Migration MailDb `AddContactMssAddressIsDefault` : contacts existants sans adresse par défaut (comportement « toutes les adresses »)
- [ ] Test d'intégration de bout en bout api-mail, vu rouge (règle 1b) : créer un contact à deux adresses avec la seconde par défaut → `GET` renvoie `DefaultMssAddress` = la seconde et `PrimaryMssAddress` = la seconde ; mise à jour sans `DefaultMssAddress` → plus d'adresse par défaut ; `DefaultMssAddress` hors de la liste → 400 ; enrichissement `PractitionerContactService` d'une nouvelle adresse → la désignation est conservée
- [ ] Tests unitaires et de composant rouges d'abord :
  - [ ] fiche (angular et mobile) : marquer une adresse « Par défaut », enregistrer → `defaultMssAddress` envoyé ; choisir « Aucune » → `null` ; supprimer l'adresse par défaut → `null`
  - [ ] rédaction (angular et mobile) : contact à deux adresses **avec** adresse par défaut → une seule suggestion, l'adresse par défaut ; taper l'autre adresse → elle est proposée aussi
  - [ ] l'écran d'édition d'un contact à deux adresses les affiche toutes deux ; modifier le téléphone et enregistrer renvoie les deux adresses, dans le même ordre
  - [ ] ajouter une adresse, en supprimer une, en modifier une : la liste envoyée reflète exactement ces changements
  - [ ] rédaction (angular et mobile) : un contact à deux adresses **sans** adresse par défaut donne deux suggestions ; choisir la seconde insère la seconde adresse dans le destinataire
  - [ ] liste des contacts et résultats de l'annuaire (angular et mobile) : un contact / praticien à deux adresses les montre toutes deux (ou « +1 » pour la liste des contacts)
  - [ ] import angular d'un praticien déjà présent (même RPPS) avec une nouvelle adresse : `updateContact` sur le contact existant, adresses fusionnées, adresse par défaut conservée, pas de `createContact`
  - [ ] recherche en 500 puis nouvelle frappe : la recherche repart et affiche ses résultats
- [ ] Scénario E2E-CONTACT-002 versionné : enregistrer un contact à deux adresses les conserve toutes deux (angular `requis` ; mobile `requis`, l'édition multi-adresses y existe déjà)
- [ ] Scénario E2E-COMPOSE versionné : contact à deux adresses sans adresse par défaut → écrire à la seconde depuis les suggestions ; marquer la seconde « Par défaut » → seule elle est proposée (angular `requis`, mobile `requis`)
- [ ] Aucune adresse ajoutée aux journaux

## Manual Test Plan

1. Contact importé de l'annuaire avec deux adresses MSSanté : les deux sont visibles dans la fiche ; modifier son téléphone, enregistrer → les deux adresses sont toujours là.
2. Ajouter une troisième adresse, supprimer la deuxième, enregistrer, rouvrir → la fiche montre exactement les adresses attendues.
3. Nouveau message (angular puis mobile), taper le nom de ce contact (sans adresse par défaut) → une suggestion par adresse ; choisir la seconde → c'est elle qui est dans « À ». Idem en tapant directement la seconde adresse, et en Cc.
4. Dans la fiche, marquer la seconde adresse « Par défaut », enregistrer ; nouveau message, taper le nom → une seule suggestion, la seconde adresse ; taper la première adresse → elle est proposée. Remettre « Aucune » → les deux suggestions reviennent.
5. Rechercher dans l'annuaire (angular) un praticien déjà dans les contacts → ses boîtes sont toutes affichées ; l'importer → pas de second contact, ses nouvelles adresses s'ajoutent au contact existant, l'adresse par défaut ne change pas.
6. Couper le réseau pendant une recherche de patient, le rétablir, retaper → les résultats s'affichent.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable (contacts professionnels ; la recherche patient ne change pas de critères)
- **Authentification PS** : inchangée
- **Habilitations** : identification des correspondants par l'annuaire santé (RPPS) inchangée
- **Interop CI-SIS** : FHIR R4 — annuaire santé (`Practitioner`, `PractitionerRole`, `telecom`) : lecture inchangée (l'annuaire ne publie que des adresses MSSanté)
- **Tracé PGSSI-S** : inchangé
- **Consentement patient** : non applicable
- **Référentiels métier** : annuaire santé (RPPS)
- **Hébergement HDS** : non applicable — données de professionnels
- **AIPD / impact RGPD** : inchangé
- **MSSanté** : inchangé — l'espace de confiance est garanti par l'opérateur, qui refuse tout envoi vers une adresse hors MSSanté

## Branches
- `api-mail` (pushed) : fix/task-379-contact-adresses-mss — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-379-contact-adresses-mss
- `client-mobile` (pushed) : fix/task-379-contact-adresses-mss — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/fix/task-379-contact-adresses-mss
- `dtos-mss` (paresseuse) : branche créée par `/develop` au premier changement de contrat (`ContactDto.DefaultMssAddress`), même nom
- `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` (au `/start` : `feature/nova-mss-weda-integration`) — humain gère branche, commit, push, PR TFS

## Timings

*(généré par `tools/timing/report.sh --task task-379 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 23 s | — | — | — | — |
| /develop | ok | 33 min 16 s | 8 (1 min 24 s) | 7 (9 min 48 s) | — | dtos-mss 1B/0T, api-mail 3B/2T, client-angular 1B/3T, client-mobile 3B/2T |
| /sonar | ok | 7 min 35 s | 1 (39 s) | 5 (4 min 50 s) | 2 (40 s) | 1 itération(s), api-mail 1B/5T |
| /lint-angular | ok | 2 min 35 s | 1 (11 s) | 1 (19 s) | — | 1 itération(s), client-angular 1B/1T |
| /lint-mobile | ok | 19 s | — | — | — | lint clean at baseline |
| /e2e | ok | 35 min 25 s | — | — | — | e2e ×6 (28 min 11 s), vert au 2e run (1er run : sélecteurs du nouveau test) |
| /review | ok | 7 min 39 s | 4 (21 s) | 3 (4 min 18 s) | — | dtos-mss 1B/0T, api-mail 1B/1T, client-mobile 1B/1T, client-angular 1B/1T |
| /tech-writer | ok | 1 min 36 s | — | — | — | — |
| **Total cycle** | | **1 h 28 min** | **14 (2 min 36 s)** | **16 (19 min 17 s)** | **2 (40 s)** | |

Autres commandes mesurées : lint ×1 (14 s), nuget-wait ×2 (15 s), restore ×2 (12 s)

## Develop log

- Repos touched : dtos-mss, api-mail, client-mobile (pushed) ; client-angular (code-only, non commité)
- DTOs published : HealthPlatform.Dtos.Mss 527.0.0 → **530.0.0** (`ContactDto.DefaultMssAddress` ; `PrimaryMssAddress` = adresse par défaut, sinon la première). `client-blazor` non listé : **non bumpé** (champ additif, sans effet sur Blazor)
- Interop published : no interop change
- Restauration NuGet : le `nuget.config` d'api-mail lit `%GH_TOKEN%` ; restauré avec `GH_TOKEN=$(gh auth token)` (401 sans)
- Commits :
  - dtos-mss : ed8faae feat(dto): adresse MSSanté par défaut d'un contact
  - api-mail : 479a8522 chore(deps) bump 530.0.0 · 35e1648d feat(contact): adresse par défaut (colonne `ContactMssAddresses.IsDefault`, migration 20261022120000, validation 400) · cc469565 test(e2e): catalogue · 3bf6e2f8 refactor simplify pass
  - client-mobile : 8b71fd4 feat(mobile) · 6b8173c test(e2e) · dc30a45 refactor simplify pass
  - client-angular (branche `feature/nova-mss-weda-integration`, **non commité**, à commiter/pousser par l'humain vers TFS) : `core/models/contact.model.ts`, `core/utils/contact-addresses.util.ts` (+spec), `core/utils/search-error.util.ts`, `core/utils/reply-all-recipients.util.ts` (export de `normalizeAddress`), `features/contacts/mss-contacts.component.{ts,html,scss}` (+spec), `features/mail/components/mail-compose/mail-compose.component.{ts,html}` (+`mail-compose-recipients.component.spec.ts`), `features/patient/components/patient-search/patient-search.component.{ts,html,scss}` (+spec), `e2e/mss-e2e/specs/functional.e2e.ts`
- Local build / test : ✓ tous les repos — api-mail 6 742 tests (0 échec, 16 ignorés préexistants) ; weda2 build ✓ + `npm test` complet ✓ puis `mss-lib` 967 ✓ après la passe qualité ; client-mobile build ✓ + 1 136 ✓
- Tests rouges prouvés (règle 1b, mutation sur copie, jamais `git checkout`) :
  - api-mail, `ContactDefaultAddressEndpointIntegrationTests` (vraie route, base PostgreSQL dédiée) : M1 mapping `DefaultMssAddress` retiré → 2 rouges ; M2 validation retirée → `ADefaultOutsideTheContactsAddresses_IsRefusedWith400…` rouge ; M3 `IsDefault` jamais écrit → 2 rouges (dont « survit à l'enrichissement ») ; M4 migration `WithDefaultValue(true)` → `ContactMssAddressIsDefaultMigrationTests…IsNotTheDefault…` rouge (rejoué après la passe qualité)
  - client-angular : M1 fiche n'envoie que la 1re adresse → 4 rouges ; M2/M4 erreur hors du `switchMap` (contacts / patients) → 1 rouge chacun ; M3/M5 la frappe n'annule plus le chargement initial → 1 rouge chacun ; M6 rédaction insère la 1re adresse → 1 rouge ; M7 règle d'adresse par défaut ignorée → 4 rouges ; M8 import crée toujours → 1 rouge
  - client-mobile : MM1 rédaction insère la 1re adresse → 1 rouge ; MM2 règle d'adresse par défaut ignorée → 3 rouges ; MM3 défaut jamais envoyé → 1 rouge
- Choix d'implémentation :
  - Suggestions avec adresse par défaut : l'autre adresse n'est proposée que si le texte tapé désigne l'adresse et **pas le nom** du contact (« martin » ne la propose pas, « dr.martin@ » oui) — règle identique sur les deux clients
  - Fiche Angular : une ligne de saisie par adresse (ajout / retrait), choix « Adresse par défaut » affiché dès deux adresses ; mobile : choix ajouté sous le champ multiligne existant
  - Message d'erreur de recherche : « La recherche a échoué. Vérifiez votre connexion puis modifiez votre saisie pour réessayer. »
- E2E (Step 6b) : catalogue `scenarios.yml` — **E2E-CONTACT-002 v2**, **E2E-COMPOSE-004 v1** (le task file cite « E2E-COMPOSE » : c'est E2E-COMPOSE-004). Tests écrits dans les deux suites, `tsc` vert sur les deux. **Preuve par mutation e2e non jouée en `/develop`** (banc `--serve-only` non monté) : à faire au premier passage de `/e2e`. Ligne ajoutée dans « Trous du filet » (`conventions/e2e.md`)
- Passe qualité (/simplify) :
  - Applied & committed : api-mail : 3 fichiers de test (3bf6e2f8 — `SqlProbe` réutilisé + `SqlProbe.ExecuteAsync`, `using` inutile, constante regroupée) ; client-mobile : 2 fichiers (dc30a45 — `normalizeAddress` réutilisé, repli `primaryMssAddress` mort retiré)
  - Applied (code-only, uncommitted) : client-angular : constante d'erreur partagée (`search-error.util.ts`), `normalizeAddress` réutilisé, repli mort retiré, **correctif SCSS** (`&__error` s'était glissé dans le sélecteur `&__loading`)
  - Non appliqué (refonte hors périmètre ou changement de comportement) : unifier les deux chemins de chargement des contacts en un seul flux ; amorcer la recherche patient par `startWith('')` (ouvrirait la liste au chargement) ; construire le payload d'import dans l'utilitaire ; éviter les 3 lectures complètes du carnet à l'import Angular ; dédoublonner les adresses saisies dans la fiche
  - Skipped (contract/excluded) : dtos-mss
- DOD self-check : build/tests ✓ ; test d'intégration api-mail ✓ (vu rouge) ; tests unitaires et de composant ✓ (vus rouges) ; scénarios E2E-CONTACT-002 v2 / E2E-COMPOSE-004 écrits (preuve e2e différée à `/e2e`) ; aucune adresse ajoutée aux journaux ✓ (aucun nouveau log)
- Next step : /sonar task-379

## Sonar log
- Serveur : SonarQube 9.9.8 (`sonar.login`), redémarré par l'agent (`sonarqube_db` puis `sonarqube`, conteneurs arrêtés depuis 35 h) ; période de nouveau code : `PREVIOUS_VERSION`
- Phase 1 (new code) : ✓ Quality Gate OK au premier passage, new_coverage = 97,0 % ; aucune issue ni hotspot sur le nouveau code
- Phase 1 — Issues fixées : 0 · Tests ajoutés : 0
- Phase 2 (legacy) : non lancée — cibles du projet déjà atteintes (0 bug, 0 vulnérabilité, 0 code smell, couverture 98 %, notes A)
- Build Release / tests OpenCover : ✓ green (6 742 tests, 16 ignorés préexistants)
- conventions/csharp.md : rien à alimenter (aucune correction manuelle)

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | — | 97,0 % | — |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 0 | 0 | 0 |
| Coverage (projet) | 98,0 % | 98,0 % | 0 pt |
| Duplication | 0,4 % | 0,4 % | 0 pt |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

## Lint log
- Mode A, branche Angular `feature/nova-mss-weda-integration` (non commité, code-only)
- Portée : contournement task-367 — ESLint lancé directement sur les 15 fichiers `.ts`/`.html` de la task, findings attribués par `git diff -U0 HEAD` (lignes ajoutées)

| Iter | Errors before | Errors after | Δ | Warnings before | Warnings after | Build | Tests |
|------|---------------|--------------|---|-----------------|----------------|-------|-------|
| 1    | 40            | 0            | −40 | 10            | 9              | ✓     | ✓ (`mss-lib` 967, e2e `tsc` ✓) |

- Iter 1 : 40 `prettier/prettier`, corrigées par `prettier --write` sur les seuls fichiers **neufs ou propres en HEAD** (consigne `prettier-fichier-existant`) ; les 3 gabarits HTML déjà non conformes en HEAD n'ont pas été reformatés
- Correction manuelle : 1 `jsdoc/require-example` (`normalizeAddress`, rendue `export` par la passe qualité) → entrée `jsdoc/require-jsdoc` de `conventions/angular.md` portée à 8 occurrences
- Avertissements restants : tous préexistants (`max-lines` sur trois fichiers déjà > 500 lignes, `complexity` dans `mail-compose.component.ts`, `jsdoc/require-example` et `consistent-type-imports` sur des lignes non touchées de `functional.e2e.ts`) ; aucun sur une ligne ajoutée par la task hors `max-lines`

## Lint mobile log
- Branche `fix/task-379-contact-adresses-mss`, arbre propre
- Baseline `npm run lint` : « All files pass linting. » — 0 erreur, 0 avertissement → aucune itération, aucun commit

## Develop log — reprise après le premier run `/e2e`
- Run `/e2e` n°1 : rouge sur **E2E-COMPOSE-004 seul**, aux deux clients, par défaut **du test** (jamais joué en `/develop`), pas du produit : mobile, les options d'un `ion-select` en feuille d'actions sont des `radio` et non des `button` ; Angular, `#edit-default-mss-address` désigne l'hôte `ds-select` **et** son bouton (violation du mode strict). E2E-CONTACT-002 v2 vert aux deux clients
- Correctifs : mobile 933d4a4 (`getByRole('radio', …)`) ; Angular `button#edit-default-mss-address` (non commité, code-only)
- Preuve par mutation e2e, banc `--serve-only` (harnais : marqueur `MUTATION` compté = 1, nouveau bundle servi + 15 s avant de jouer) : témoins verts (2 + 2) ; ME1 Angular fiche n'envoie que la 1re adresse → E2E-CONTACT-002 rouge (« le serveur a reçu les deux adresses ») ; ME2 Angular rédaction insère la 1re adresse → E2E-COMPOSE-004 rouge (« la seconde adresse est dans « À » ») ; MM1 mobile idem → E2E-COMPOSE-004 rouge ; MM2 mobile fiche n'envoie que la 1re adresse → E2E-CONTACT-002 rouge ; témoins restaurés verts (2 + 2)

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail, client-mobile, dtos-mss touchés | ✅ verte | 39 verts, 0 flaky, 0 rouge, 0 quarantaine | 6 min 39 s |
| angular | api-mail, client-angular, dtos-mss touchés | ✅ verte | 46 verts dont 1 flaky, 0 rouge, 1 quarantaine (E2E-COMPOSE-002, task-350) | 7 min 12 s |

- Run n°1 : rouge sur E2E-COMPOSE-004 aux deux clients (sélecteurs du nouveau test, voir « Develop log — reprise ») ; correctif, preuve par mutation sur le banc `--serve-only`, puis run n°2 complet ci-dessus
- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task (`fix/task-379-contact-adresses-mss`)
- Quarantaines : E2E-COMPOSE-002 (angular), posée le 2026-10-09, task de correction task-350 — **au-delà de 14 jours** à compter du 2026-10-23 : correction due
- Flaky : E2E-COMPOSE-001 (angular), même signature que les occurrences précédentes (`delete-mail-btn`, menu « Plus d’actions ») — **6ᵉ occurrence : flaky récurrent → task de stabilisation à ouvrir**
- Divergences ouvertes : aucune
- Parcours touchés sans spec e2e modifié : aucun (les deux suites sont modifiées)
- Démontage : ports libres ; deux conteneurs `e2e-greenmail-*` / `e2e-dovecot-*` arrêtés **du 2026-10-14**, antérieurs à ce run (non créés par task-379, laissés en place)

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**Flaky (vert au second essai, non bloquant)** (1) :

- [angular] « rédaction — envoyer, recevoir, lire, supprimer » (E2E-COMPOSE-001)

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 2 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ⚠️ flaky | ✅ |
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

## PRs
- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/46 — label `awaiting-human-merge`
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/304 — label `awaiting-human-merge`
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/98 — label `awaiting-human-merge`
- `client-angular` : code-only — humain gère commit/push TFS et ouverture PR, branche `feature/nova-mss-weda-integration`. Fichiers modifiés :
  - `front/e2e/mss-e2e/specs/functional.e2e.ts`
  - `front/libs/mss/src/core/models/contact.model.ts`
  - `front/libs/mss/src/core/utils/reply-all-recipients.util.ts`
  - `front/libs/mss/src/features/contacts/mss-contacts.component.html`
  - `front/libs/mss/src/features/contacts/mss-contacts.component.scss`
  - `front/libs/mss/src/features/contacts/mss-contacts.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose.component.html`
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose.component.ts`
  - `front/libs/mss/src/features/patient/components/patient-search/patient-search.component.html`
  - `front/libs/mss/src/features/patient/components/patient-search/patient-search.component.scss`
  - `front/libs/mss/src/features/patient/components/patient-search/patient-search.component.ts`
  - `front/libs/mss/src/core/utils/contact-addresses.util.spec.ts`
  - `front/libs/mss/src/core/utils/contact-addresses.util.ts`
  - `front/libs/mss/src/core/utils/search-error.util.ts`
  - `front/libs/mss/src/features/contacts/mss-contacts.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose-recipients.component.spec.ts`
  - `front/libs/mss/src/features/patient/components/patient-search/patient-search.component.spec.ts`

## Code Review Summary

**Verdict : APPROVED** — 0 point bloquant, 3 suggestions.

| Zone | Verdict | Note |
|---|---|---|
| `dtos-mss` `ContactDto.DefaultMssAddress` / `PrimaryMssAddress` | ✅ | Champ additif ; `PrimaryMssAddress` = adresse par défaut, sinon la première |
| api-mail `ContactRepository` (normalisation, 400, `IsDefault` à l'écriture, lecture) | ✅ | Validation au point de passage de tous les écrivains (contrôleur, enrichissement, vCard) ; au plus une adresse par défaut même si la liste se répète |
| api-mail migration `20261022120000` | ✅ | Colonne non nulle, défaut `false` : contacts existants sans adresse par défaut ; descente testée |
| Clients — fiche contact, suggestions par adresse, import fusionné (Angular), recherche après erreur | ✅ | Règle de suggestion identique sur les deux clients, isolée dans un utilitaire pur testé |
| Tests | ✅ | Intégration de bout en bout vue rouge (4 mutations), tests de composant vus rouges, e2e vus rouges sur le banc |

**Règle 1b — comportement → test d'intégration → preuve rouge**

| Comportement (endpoint) | Test | Preuve rouge |
|---|---|---|
| `POST`/`GET /api/v1/Contact` : adresse par défaut relue dans la réponse et en base | `AContactWithTwoAddresses_KeepsTheDesignatedDefault_InTheResponseAndInTheDatabase` | M1 (mapping retiré), M3 (`IsDefault` jamais écrit) |
| `PUT /api/v1/Contact/{id}` sans adresse par défaut : désignation retirée, adresses conservées | `SavingTheContactWithoutADefault_ClearsTheDesignation_AndKeepsBothAddresses` | M5 (première adresse désignée quand aucune n’est demandée), prouvée en `/review` |
| Adresse par défaut hors de la liste → 400, rien en base | `ADefaultOutsideTheContactsAddresses_IsRefusedWith400_AndNothingIsStored` | M2 (validation retirée) |
| Enrichissement automatique : la désignation survit | `TheDesignation_SurvivesTheEnrichmentThatAddsAnAddress` | M1, M3 |
| Migration : contact existant sans adresse par défaut | `ContactMssAddressIsDefaultMigrationTests` | M4 (défaut `true`) |

**Suggestions (non bloquantes)**
- ⚠️ `client-blazor` reste sur `HealthPlatform.Dtos.Mss` 527 : un `PUT` envoyé par Blazor ne porte pas `DefaultMssAddress` et **retire la désignation** (sémantique de remplacement du `PUT`). À aligner en montant Blazor sur 530 si Blazor édite encore des contacts.
- ⚠️ Une même adresse saisie deux fois dans la fiche est enregistrée deux fois (préexistant ; la fusion de l'annuaire, elle, dédoublonne).
- ⚠️ Angular : l'import depuis l'annuaire lit le carnet entier avant d'écrire (trois lectures complètes par import, avec le rechargement et les compteurs) — acceptable pour une action rare, à mutualiser si le carnet grossit.
- Mutation M5 (`/review`) : `defaultIndex` à 0 quand aucune adresse par défaut n'est demandée → `SavingTheContactWithoutADefault_ClearsTheDesignation_AndKeepsBothAddresses` rouge, seul ; restauré vert
