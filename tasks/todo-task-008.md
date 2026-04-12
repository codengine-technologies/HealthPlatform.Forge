# todo-task-008.md — Verification taille PJ avant envoi

**Repos**: api-mail, client-blazor, client-angular
**Dependencies**: aucune

## Objectif

Le systeme doit verifier la taille des pieces jointes avant l'envoi d'un message MSSante
et alerter le professionnel si la taille depasse la limite autorisee par l'operateur.
La verification doit intervenir au moment de l'ajout de chaque PJ (feedback immediat
cote frontend) et en garde-fou cote backend avant l'envoi SMTP.

## Contexte reglementaire

L'exigence MSS/va1.13 impose que les pieces jointes respectent la taille maximale
definie par l'operateur MSSante. La limite varie selon les operateurs (generalement
entre 10 Mo et 25 Mo). Le Ref#2 ne definit pas de taille specifique — c'est l'operateur
qui fixe la limite. Le systeme doit donc gerer une taille maximale configurable.

## Comportement attendu

### Frontend (composition)
- Affichage permanent de la taille totale des PJ et de la limite maximale pendant
  la composition (ex: `3.2 Mo / 10 Mo`)
- A l'ajout d'une PJ qui fait depasser la limite :
  - Alerte immediate avec message clair (taille actuelle + limite)
  - La PJ n'est pas ajoutee
- Indicateur visuel de progression (jauge ou barre de progression)

### Backend (garde-fou)
- Verification de la taille totale avant envoi SMTP
- Rejet avec erreur explicite si depassement
- Taille maximale configurable dans les parametres applicatifs (defaut : 10 Mo)

## Gherkin

See `tests/mss.mail.bdd.tests/Features/Mss/VerificationTaillePj.feature`

## Exigence Segur couverte

- MSS/va1.13 — Piece jointe respecte taille max (selon operateur)

## References reglementaires

- REM Segur MSS/va1.13

## Definition of Done

- [ ] Build passes (0 errors) sur `api-mail`, `client-blazor`, `client-angular`
- [ ] Tests pass (0 failures)
- [ ] Taille maximale des PJ configurable dans les parametres applicatifs (defaut : 10 Mo)
- [ ] Verification cote backend avant envoi SMTP (rejet si depassement avec message explicite)
- [ ] Verification cote frontend au moment de l'ajout de chaque PJ (feedback immediat)
- [ ] Affichage de la taille totale des PJ et de la limite pendant la composition
- [ ] Message d'erreur clair indiquant la taille actuelle et la limite autorisee
- [ ] La PJ qui fait depasser la limite n'est pas ajoutee (avec explication)
- [ ] Blazor : indicateur de taille + alerte pendant la composition
- [ ] Angular : indicateur de taille + alerte pendant la composition
- [ ] >= 1 test d'integration par scenario Gherkin
- [ ] Aucune regression

## Manual Test Plan

- Lancer backend + Blazor + Angular
- Composer un message et ajouter une PJ de petite taille (ex: 1 Mo)
  - Verifier que la taille est affichee (ex: `1.0 Mo / 10 Mo`) et l'envoi fonctionne
- Ajouter progressivement des PJ jusqu'a approcher la limite
  - Verifier que la taille totale et la limite sont visibles en permanence
- Ajouter une PJ qui fait depasser la limite
  - Verifier l'alerte : message clair avec taille actuelle et limite
  - Verifier que la PJ n'est pas ajoutee
- Modifier la configuration de taille maximale (ex: passer a 5 Mo)
  - Verifier la prise en compte sur le prochain message
- Tenter un envoi direct via API avec PJ depassant la limite
  - Verifier le rejet backend avec message explicite
- Repeter sur les deux frontends (Blazor et Angular)
