# todo-task-106-mobile-email-search.md — Recherche d'emails sur le client mobile

**Repos**: client-mobile
**Single frontend**: true
**Dependencies**: none
**Epic**: E012

> **US mono-repo justifiée** : le backend expose déjà la recherche
> (`POST /api/v1/search/semantic`, `GET /api/v1/search/suggestions`) ; l'écart
> est l'absence d'UI/orchestration de recherche côté `client-mobile`.

## Objective

Permettre au médecin de **rechercher** ses emails depuis le mobile (objet,
expéditeur, identité patient, plage de dates, présence de PJ / documents
médicaux / biologie), à parité fonctionnelle avec la recherche de
`client-angular` (composant `mail-search`).

## Analyse de référence

- API : `semanticSearch(SearchRequestDto)` → `POST /api/v1/search/semantic`
  → `SearchResponseDto` (UIDs / résultats) ; `getSearchSuggestions(query, limit)`
  → `GET /api/v1/search/suggestions`.
- `SearchFilterDto` riche (champ : objet/from/recipient/patient ; statut :
  lu/important/répondu/brouillon ; dates : envoi/document/biologie ; contenu :
  PJ/document médical/biologie/type de document).

## Comportement attendu

- Une barre de recherche (`ion-searchbar`) accessible depuis l'inbox.
- Saisie d'une requête → exécution `semanticSearch` (debounce) → affichage des
  résultats dans la liste (réutilise `mss-mail-list` / `mss-mail-header`).
- Filtres de base mobile-friendly (au minimum : non lus, avec PJ, avec document
  médical, plage de dates) ; le périmètre complet de `SearchFilterDto` peut être
  introduit progressivement.
- Effacer la recherche → retour à la liste paginée normale.
- État « aucun résultat » clair ; gestion d'erreur `ProblemDetails`.

## Scénarios d'acceptation

1. **Recherche simple** — Quand je saisis un terme, alors les emails
   correspondants s'affichent dans la liste.
2. **Filtre** — Quand j'active un filtre (ex. « avec document médical »), alors
   les résultats sont restreints en conséquence.
3. **Aucun résultat** — Une requête sans correspondance affiche un état vide explicite.
4. **Effacer** — Effacer la recherche restaure la liste inbox normale (paginée).
5. **Robustesse** — Pas de double-appel intempestif (debounce) ; erreur réseau gérée.

## Definition of Done

- [ ] Build passes (`npm run build`, 0 erreur)
- [ ] Tests pass (`npm test -- --watch=false --browsers=ChromeHeadless`, 0 échec)
- [ ] `MssApiService.semanticSearch(request)` (+ `getSearchSuggestions` si retenu) implémenté
- [ ] Modèles `SearchRequestDto` / `SearchResponseDto` / `SearchFilterDto` mobiles (miroir)
- [ ] Composant `mss-mail-search` (barre + filtres de base) intégré à l'inbox
- [ ] Résultats affichés via la liste existante ; effacement restaure la liste paginée
- [ ] Debounce + anti double-appel ; état vide + erreur `ProblemDetails`
- [ ] Libellés FR en dur ; `data-testid` sur la barre, les filtres, l'état vide
- [ ] Tests : `mss-api.semanticSearch` (POST endpoint + payload), composant recherche (émission requête + rendu résultats/vide)
- [ ] **Aucune requête de recherche ni terme patient loggé en clair** (peut contenir nom patient)

## Manual Test Plan

- Backend `cd Api/Mail && dotnet run` ; Mobile `cd Client/Mobile && npm start`
- Se connecter (PSC), ouvrir l'inbox, lancer une recherche par objet puis par nom patient
- Activer un filtre (avec PJ / document médical / plage de dates) → vérifier la restriction
- Vérifier l'état « aucun résultat » sur une requête vide de correspondances
- Effacer → la liste paginée normale revient
- Comparer avec `client-angular`

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR honorées** : ergonomie d'accès aux messages MSS
- **Authentification PS** : PSC / e-CPS (en place) — recherche scope-utilisateur
- **Interop CI-SIS** : non applicable (recherche sur métadonnées déjà indexées)
- **Tracé PGSSI-S** : recherche journalisée côté backend si applicable — sans terme patient en clair
- **Sécurité** : ne jamais logger la requête de recherche en clair (peut contenir nom/identité patient) ; pas d'INS en clair
- **AIPD / RGPD** : inchangé — consultation de la boîte du PS

## Branches
- `client-mobile` (pushed) : feat/task-106-mobile-email-search — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-106-mobile-email-search

> Single frontend (client-mobile only). Deps none (socle E012 sur develop).

## Develop log
- Repos : client-mobile
- mss-api.semanticSearch + modèles search ; mss-mail-search (searchbar + chips, debounce) ; inbox mode recherche (suspend pagination via isSearchActive)
- Build ✓ · Tests ✓ 96/96 (6 nouveaux) · Lint ✓
- Commit : client-mobile @3385011

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/11 — label `awaiting-human-merge`

## Code Review Summary
- Verdict : APPROVED · Build ✓ · Tests ✓ 96/96 · Lint ✓
- recherche debouncée + filtres, suspension pagination, ProblemDetails ; requête jamais loggée ; FR + data-testid

## Merged
- Merged : 2026-06-19 (squash) by human authorization
- client-mobile : develop @29642ae (PR #11 closed)
- Local feature branch conservée
