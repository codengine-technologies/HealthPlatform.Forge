# todo-task-248.md — La fiche patient paie une requête par document, et le chemin groupé existe déjà

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: **task-247** — coordination : les deux chemins partagent
`PopulateMailContentAsync`. À traiter **après**, pour que le gain de chacune reste
attribuable.
**Priorité**: **2** — la fiche patient sort de la grille au palier 200, et c'est
la seule étape qui ait produit des **timeouts à 60 s** en local.

## Objective

Que l'ouverture d'un message et l'hydratation de sa fiche patient cessent de
coûter proportionnellement au **nombre de documents cliniques** attachés.

## Ce qui est établi

**Par lecture de code, annoncée comme telle (F-243-2)** : l'hydratation d'un
document reste en **N+1** sur `GetMailAsync` — environ **10 + 3×D requêtes
séquentielles** par message, où D est le nombre de documents CDA. Le chemin groupé
**existe déjà dans le dépôt** (`LoadBulkMailLookupsAsync`), mais aucune route HTTP
ne l'expose avec le contenu.

**Par mesure**, tir local 200 du 2026-08-08 (instrument task-243) :

| `GetMail` | Valeur |
|---|---|
| Requêtes SQL par appel | **10,5** |
| Moyenne totale | 299,4 ms |
| Exécution SQL | 171,3 ms — 57,2 % |
| Matérialisation | 109,8 ms — 36,7 % |
| **p95 total** | **60 000 ms** — le plafond de timeout |

**Confirmation croisée** : au tir 500 sur base quasi vide, la matérialisation de
`GetMail` s'effondre de **109,8 ms à 2,1 ms** et le p95 de 60 000 ms à **281 ms**.
Le plafond de 60 s était donc conduit par **la donnée** (les documents à hydrater),
pas par la charge. C'est l'argument le plus net en faveur du N+1.

**Effet sur le médecin** : étape « fiche patient complète » à p95 **5 004 ms** au
palier 200 pour une cible de 4 000 ms, et des timeouts `patient_docs` observés dès
le palier 100.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que réutiliser `LoadBulkMailLookupsAsync` suffit.** Le chemin
  groupé existe pour les *lookups* ; l'hydratation du **contenu** des documents est
  un autre geste. Vérifier avant de câbler.
- **Ne pas présumer que le gain se voit à 200.** Il est proportionnel à D : c'est
  sur les messages **multi-documents** qu'il faut mesurer, et le corpus du banc
  doit en contenir assez pour que la mesure soit significative.

## Definition of Done

- [ ] L'hydratation des documents d'un message ne fait plus de requête par
      document — décompte **prouvé** par le compteur de requêtes de task-243
- [ ] Le p95 de `GetMail` ne plafonne plus à la valeur de timeout
- [ ] L'étape « fiche patient complète » rentre dans la grille au palier 200, ou
      l'écart résiduel est expliqué et chiffré
- [ ] Zéro timeout `patient_docs` sur un tir 200 en local
- [ ] Tests unitaires : un message à 1 document, un à N documents, un sans document
      — le contenu rendu doit être **identique** à l'avant-correctif
- [ ] A/B iso-conditions sur la lignée courante, décomposition task-243 avant/après

## Manual Test Plan

- Ouvrir un message porteur de **plusieurs** documents CDA, puis sa fiche patient
- Vérifier que **tous** les documents s'affichent, avec leurs métadonnées et leur
  contenu — aucun document manquant, aucun doublon
- Comparer le temps d'affichage avant/après sur le même message
- Vérifier qu'un message **sans** document ne régresse pas

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — performance
- **Exigences DSR honorées** : aucune exigence nouvelle ; ⚠️ la US touche
  l'affichage des **documents cliniques** — aucune perte ni troncature ne doit en
  résulter, c'est le risque fonctionnel n°1
- **INS** : ⚠️ les documents hydratés portent l'INS du patient — le regroupement
  des requêtes ne doit **jamais** mélanger les documents de deux messages ni de
  deux praticiens. Un test doit le prouver.
- **Habilitations** : cloisonnement « une base par praticien » inchangé
- **Interop CI-SIS** : les documents restent des CDA r2 rendus à l'identique
- **Consentement patient** : non applicable
- **Tracé PGSSI-S** : inchangé — aucun contenu CDA en clair dans les journaux
- **Hébergement HDS** : sans objet
- **AIPD / impact RGPD** : inchangé

## Branches
- `api-mail` (pushed) : feat/task-248-patient-file-n-plus-one
- `dtos-mss` (pushed, auto-inclus) : feat/task-248-patient-file-n-plus-one

> Branchée sur `develop` **après** le merge de task-247 (`9e1b4bf`), comme la
> dépendance l'exige — pour que le gain de chacune reste attribuable.

## PRs

- **api-mail** : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/179 — label `awaiting-human-merge`
- **dtos-mss** : aucun commit → **pas de PR** (branche vide, comme prévu)

## Code Review Summary

**APPROVED** — 2 fichiers, 0 blocage.

| Fichier | Verdict |
|---|---|
| `MailRepository.cs` | ✅ **0 `await` restant** dans la boucle sur les documents (vérifié) ; 3 chargeurs groupés avec garde `Count == 0` ; clé d'appariement = `DocumentId`, filtre = `MailId` |
| `PatientFileHydrationTests.cs` | ✅ 5 cas dont le cloisonnement inter-messages et le décompte |

**Éprouvé par mutation, deux fois** — mauvaise clé d'appariement → 2 tests tombent ;
pièces jointes perdues → 3 tests tombent. Pas des tests verts par construction.

### Validation

Build 0 erreur. domain 136 · infrastructure 436 · api 660 · application 2 099 ·
**integration 380, 0 échec**.

> **La suite d'intégration est intégralement verte sur cette branche**, ce qui
> **tranche la question laissée ouverte** au développement :
> `PatientUseCaseTests.SearchShouldReturnMatchingPatients` avait échoué de façon non
> reproductible et je ne pouvais pas dire flaky vs régression. C'était bien un
> **flaky d'état entre tests**.

### DOD

| Critère | État |
|---|---|
| Plus de requête par document — **décompte prouvé** | ✅ |
| Tests 1 / N / 0 document, contenu identique | ✅ |
| p95 de `GetMail` ne plafonne plus | ⏳ **exige un tir** |
| Étape fiche patient dans la grille au palier 200 | ⏳ **tir** |
| Zéro timeout `patient_docs` sur un tir 200 | ⏳ **tir** |
| A/B iso-conditions, décomposition avant/après | ⏳ **tir** |

**Comment le premier critère est prouvé** : le compteur de task-243 est alimenté par
les intercepteurs EF de **production**, absents de la fixture de test — il ne
publiait rien (constat empirique). Les commandes sont donc comptées par un
**intercepteur local au test** : preuve indépendante du câblage, **déterministe**, et
portant sur un **nombre**. L'assertion est l'**égalité** entre D=1 et D=5, et non
« moins de requêtes » — ce dernier serait satisfait par un passage de 3×D à 2×D.

### ⚠️ Reste ouvert

**`/sonar` n'a pas été rejoué** sur cette task, qui modifie du C#.

Commits : `af8d61e` (perf), `98440c8` (preuve du décompte).
