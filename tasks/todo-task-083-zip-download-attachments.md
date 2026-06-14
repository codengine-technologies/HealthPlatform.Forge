# todo-task-083.md — Téléchargement groupé des pièces jointes (archive ZIP)

**Repos**: api-mail, client-blazor, client-angular
**Epic**: E009
**EpicTitle**: Parité fonctionnelle webmail (confort de rédaction et de lecture)

## Objective

Permettre au professionnel de santé de télécharger **toutes les pièces jointes
d'un mail en une seule archive ZIP**, au lieu de les enregistrer une par une.
Inspiré du plugin `zipdownload` de Roundcube. Cas d'usage fréquent : un courrier
MSSanté contenant plusieurs documents (CR de biologie, imagerie, lettre de
liaison) que le médecin veut archiver d'un seul geste dans le dossier patient.

## Comportement attendu

- Sur un mail comportant au moins 2 pièces jointes, un bouton « Tout télécharger
  (ZIP) » est proposé à côté de la liste des pièces jointes.
- Le clic déclenche le téléchargement d'une archive `.zip` contenant toutes les
  pièces jointes du mail, avec leurs noms de fichiers d'origine.
- Les noms de fichiers en doublon dans l'archive sont désambiguïsés (suffixe
  `(1)`, `(2)`…).
- L'archive n'est jamais persistée sur disque côté serveur : elle est produite
  en flux (streaming) et envoyée directement au client.
- Si un mail ne comporte aucune pièce jointe, le bouton n'apparaît pas.

## Gherkin

```gherkin
Feature: Téléchargement groupé des pièces jointes

  Scenario: Un médecin télécharge toutes les pièces jointes d'un courrier
    Given un courrier reçu comportant trois pièces jointes
    When le médecin demande à télécharger toutes les pièces jointes
    Then une archive compressée contenant les trois fichiers est téléchargée
    And chaque fichier conserve son nom d'origine

  Scenario: Désambiguïsation des noms en doublon
    Given un courrier comportant deux pièces jointes nommées "resultat.pdf"
    When le médecin télécharge toutes les pièces jointes
    Then l'archive contient "resultat.pdf" et "resultat (1).pdf"

  Scenario: Aucun bouton sans pièce jointe
    Given un courrier sans pièce jointe
    When le médecin ouvre le courrier
    Then aucune action de téléchargement groupé n'est proposée
```

## Definition of Done

- [ ] Build passes sur chaque repo listé (0 erreur)
- [ ] Endpoint backend `GET folders/{foldername}/emails/{emailid}/attachments/download/zip` qui streame une archive ZIP (`application/zip`)
- [ ] L'archive est produite en flux, jamais écrite sur disque serveur
- [ ] Désambiguïsation des noms de fichiers en doublon
- [ ] >= 1 test unitaire par comportement backend (composition de l'archive, désambiguïsation, mail sans PJ → 204/404)
- [ ] >= 1 test d'intégration de l'endpoint (happy path multi-PJ + mail sans PJ)
- [ ] Blazor : bouton « Tout télécharger (ZIP) » conditionné à >= 1 PJ, aucune chaîne en dur (i18n), `data-testid`
- [ ] Angular : idem côté front legacy, aucune chaîne en dur (i18n), `data-testid`
- [ ] Erreurs renvoyées en `ProblemDetails` (RFC 7807) via le `GlobalExceptionHandler` (règle 12)
- [ ] Aucune donnée de santé en clair dans les logs (nom de fichier de PJ inclus → loggué uniquement en niveau debug masqué)

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run`
- Lancer Blazor : `cd Client/Blazor && dotnet run`
- Lancer Angular : `cd Client/Angular && npm start`
- Ouvrir un courrier MSSanté comportant au moins 2 pièces jointes
- Cliquer sur « Tout télécharger (ZIP) »
- Vérifier qu'une archive `.zip` se télécharge et contient toutes les PJ avec
  leurs noms d'origine
- Ouvrir un courrier sans pièce jointe et vérifier l'absence du bouton

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors exigence DSR spécifique — confort utilisateur (la messagerie MSSanté reste l'élément référencé)
- **Exigences DSR honorées** : non applicable — fonctionnalité de confort, n'altère ni le transport MSSanté ni le contenu des documents
- **INS** : non applicable — pas de manipulation de l'identité patient ; les pièces jointes sont transférées telles quelles
- **Authentification PS** : session PS déjà authentifiée (PSC / e-CPS) — pas de nouvelle exigence
- **Habilitations** : accès limité aux courriers de la boîte du PS authentifié (inchangé)
- **Interop CI-SIS** : non applicable — les documents (CDA, PDF) sont transmis sans transformation
- **Tracé PGSSI-S** : journaliser l'évènement « téléchargement groupé des pièces jointes » (id mail, nombre de PJ) — conservation selon politique en vigueur
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement existant, aucune donnée nouvelle persistée
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement persistant (archive produite en flux)
