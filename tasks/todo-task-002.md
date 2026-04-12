# todo-task-002.md — Masquage prefixe XDM dans l'objet

**Repos**: api-mail, client-blazor, client-angular
**Dependencies**: aucune

## Objectif

Lorsqu'un message MSSante contient des documents de sante, l'objet du courriel est
prefixe par `XDM/1.0/DDM+` suivi des metadonnees patient (conformement a ECO.2.1.3 —
Ref#2 §3.1.3). Ce prefixe technique ne doit pas etre affiche a l'utilisateur dans la
liste des messages recus. Le systeme doit le masquer a l'affichage tout en conservant
l'objet original en base.

## Format de l'objet (Ref#2 §3.1.3, ECO.2.1.3)

Le format complet de l'objet est :
```
XDM/1.0/DDM+<libelle> <NOM> <prenom> <date de naissance>
```

- `XDM/1.0/DDM` : marqueur que le message contient des documents CI-SIS
- `+` : separateur (ASCII 43)
- `<libelle>` : si 1 CDA → `displayName` du code CDA (tronque a 40 car.), si N CDA → `N documents`
- `<NOM>` : nom de naissance en MAJUSCULES, sans accents
- `<prenom>` : prenom sans accents
- `<date de naissance>` : JJ/MM/AAAA (optionnel)

Exemples d'objets bruts :
- `XDM/1.0/DDM+CR d'examens biologiques VIAL Paul 26/11/1978`
- `XDM/1.0/DDM+Lettre de liaison a la sortie d'un etabl VIAL Paul 26/11/1978`
- `XDM/1.0/DDM+2 documents VIAL Paul 26/11/1978`

Affichage attendu (prefixe retire) :
- `CR d'examens biologiques VIAL Paul 26/11/1978`
- `Lettre de liaison a la sortie d'un etabl VIAL Paul 26/11/1978`
- `2 documents VIAL Paul 26/11/1978`

## Exigence Segur couverte

- SC.MSS/UX.28

## Gherkin

See `tests/mss.mail.bdd.tests/Features/Mss/MasquagePrefixeXdm.feature`

## Definition of Done

- [ ] Build passes (0 errors) sur `api-mail`, `client-blazor`, `client-angular`
- [ ] Tests pass (0 failures)
- [ ] Le prefixe `XDM/1.0/DDM+` est retire de l'objet a l'affichage dans la liste des messages
- [ ] L'objet original est conserve intact en base de donnees
- [ ] Les messages sans prefixe `XDM/1.0/DDM+` ne sont pas modifies
- [ ] Blazor : objet nettoye dans la liste des messages et dans le detail
- [ ] Angular : objet nettoye dans la liste des messages et dans le detail
- [ ] >= 1 test d'integration par scenario Gherkin
- [ ] Aucune regression

## Manual Test Plan

- Lancer backend + Blazor + Angular
- Recevoir un message avec objet `XDM/1.0/DDM+CR d'examens biologiques VIAL Paul 26/11/1978`
  - Verifier dans les deux frontends que l'objet affiche est `CR d'examens biologiques VIAL Paul 26/11/1978`
- Recevoir un message avec objet `XDM/1.0/DDM+2 documents VIAL Paul 26/11/1978`
  - Verifier affichage `2 documents VIAL Paul 26/11/1978`
- Recevoir un message avec objet libre (ex: `Bonjour docteur`)
  - Verifier qu'il est affiche tel quel
- Verifier en base que l'objet original complet est conserve avec le prefixe
