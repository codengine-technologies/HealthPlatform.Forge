# todo-task-009.md — Libelle expediteur formate

**Repos**: api-mail
**Dependencies**: aucune

## Objectif

Le systeme doit formater le libelle de l'expediteur (display name du champ `From:`)
selon le format impose par le Ref#2 (ECO.2.2.7, §3.5, p.30), afin que le destinataire
identifie facilement l'emetteur du message.

## Detail de l'exigence (Ref#2 §3.5, p.30)

### ECO.2.2.7

> Le systeme DOIT specifier un libelle signifiant en complement de l'adresse de
> messagerie de l'expediteur.

### Format du champ `From:`

```
Intitule_BAL <xxx@xxx.mssante.fr>
```

### BAL personnelle professionnelle

```
Intitule_BAL = <Titre>_<Prenom>_<NOM>_<Entite fonctionnelle>
```

- `<Titre>` : civilite pour les professions de sante reglementees (Dr, Pr, etc.),
  place avant le prenom
- `_` : caractere underscore (ASCII 95) comme separateur
- `<Prenom>` : prenom du professionnel
- `<NOM>` : nom d'exercice du professionnel, **en majuscules**
- `<Entite fonctionnelle>` : nom de la structure de soins ou du service
- Seuls **nom et prenom sont obligatoires**, titre et entite sont optionnels

**Exemples :**
- `Dr_Marie_MARTIN_Cabinet Medical <marie.martin@medecin.mssante.fr>`
- `Jean_DUPONT <jean.dupont@medecin.mssante.fr>`

### BAL organisationnelle ou applicative

```
Intitule_BAL = <Entite fonctionnelle>
```

**Exemples :**
- `Hopital A – Service Cardiologie <nom du service@hopitalA.mssante.fr>`
- `Hopital C – Biologie <resultat_biologie@hopitalC.mssante.fr>`

## Gherkin

See `tests/mss.mail.bdd.tests/Features/Mss/LibelleExpediteur.feature`

## Exigence Segur couverte

- MSS/va1.16 (ECO.2.2.7) — Libelle signifiant en complement de l'adresse de messagerie

## References reglementaires

- Referentiel socle MSSante #2 v1.0.1 — §3.5 Expediteur d'un courriel
- ECO.2.2.7 — Libelle signifiant en complement de l'adresse de messagerie

## Definition of Done

- [ ] Build passes (0 errors) sur `api-mail`
- [ ] Tests pass (0 failures)
- [ ] Le champ `From:` des messages envoyes contient le libelle formate :
  `<Titre>_<Prenom>_<NOM>_<Entite> <xxx@xxx.mssante.fr>`
- [ ] Le nom d'exercice est en **majuscules**
- [ ] Les separateurs sont des underscores (ASCII 95)
- [ ] Si le titre est absent, le libelle commence par le prenom
- [ ] Si l'entite fonctionnelle est absente, le libelle se termine par le nom
- [ ] Les donnees du professionnel (titre, prenom, nom, entite) sont issues du
  `UserContextInfo` ou des parametres utilisateur
- [ ] Configuration possible du titre et de l'entite fonctionnelle dans les
  parametres utilisateur
- [ ] >= 1 test d'integration par scenario Gherkin
- [ ] Aucune regression sur les tests existants d'envoi

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run`
- Configurer un professionnel avec titre "Dr", prenom "Marie", nom "Martin",
  entite "Cabinet Medical"
- Envoyer un message → verifier dans les logs SMTP le champ `From:` :
  `Dr_Marie_MARTIN_Cabinet Medical <marie.martin@medecin.mssante.fr>`
- Supprimer le titre et l'entite → envoyer → verifier :
  `Marie_MARTIN <marie.martin@medecin.mssante.fr>`
- Verifier cote destinataire que le libelle est bien affiche dans la liste
  des messages recus
