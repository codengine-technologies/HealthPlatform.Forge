# todo-task-388.md — Annuaire Santé : les finitions relevées en revue de task-386

**Repos**: api-mail, client-mobile, client-blazor, client-angular
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
