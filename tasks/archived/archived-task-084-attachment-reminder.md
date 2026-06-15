# todo-task-084.md — Rappel de pièce jointe oubliée à l'envoi

**Repos**: client-blazor, client-angular
**Epic**: E009

> US front-only justifiée : la détection se fait à la rédaction, dans le
> compositeur. Aucun changement de contrat backend ni d'envoi MSSanté.

## Objective

Réduire les envois incomplets : lorsque le professionnel de santé rédige un
courrier dont le corps évoque une pièce jointe (« ci-joint », « veuillez
trouver en pièce jointe », « PJ », etc.) **sans avoir attaché aucun fichier**,
afficher un avertissement de confirmation avant l'envoi. Inspiré du plugin
`attachment_reminder` de Roundcube. Cas d'usage : un médecin écrit « vous
trouverez ci-joint le compte-rendu » et oublie de joindre le document.

## Comportement attendu

- À l'envoi d'un courrier, si le corps (ou l'objet) contient une expression
  évoquant une pièce jointe **et** qu'aucun fichier n'est attaché, une boîte de
  confirmation s'affiche : « Vous semblez mentionner une pièce jointe mais
  aucun fichier n'est attaché. Envoyer quand même ? ».
- Le PS peut confirmer l'envoi (« Envoyer quand même ») ou annuler pour ajouter
  une pièce jointe.
- La détection repose sur une liste configurable d'expressions FR (« ci-joint »,
  « ci-joints », « ci-jointe », « pièce jointe », « pièces jointes », « PJ »,
  « en annexe », « veuillez trouver »).
- Si au moins une pièce jointe est présente, aucun avertissement n'est affiché.
- La détection est insensible à la casse et aux accents.

## Gherkin

```gherkin
Feature: Rappel de pièce jointe oubliée

  Scenario: Mention d'une PJ sans fichier attaché
    Given un médecin rédige un courrier dont le corps contient "ci-joint le compte-rendu"
    And aucun fichier n'est attaché
    When il demande l'envoi du courrier
    Then un avertissement lui propose d'envoyer quand même ou d'ajouter une pièce jointe

  Scenario: Mention d'une PJ avec fichier attaché
    Given un médecin rédige un courrier mentionnant une pièce jointe
    And un fichier est attaché
    When il demande l'envoi du courrier
    Then le courrier est envoyé sans avertissement

  Scenario: Aucune mention de pièce jointe
    Given un médecin rédige un courrier sans mention de pièce jointe et sans fichier
    When il demande l'envoi du courrier
    Then le courrier est envoyé sans avertissement
```

## Definition of Done

- [ ] Build passes sur chaque repo listé (0 erreur)
- [ ] Détection partagée (liste d'expressions FR configurable, insensible casse/accents)
- [ ] Blazor : dialogue de confirmation avant envoi, aucune chaîne en dur (i18n), `data-testid`
- [ ] Angular : idem côté front legacy, aucune chaîne en dur (i18n), `data-testid`
- [ ] >= 1 test unitaire par cas (mention sans PJ → avertissement, mention avec PJ → pas d'avertissement, sans mention → pas d'avertissement, casse/accents) sur chaque frontend
- [ ] Le comportement n'altère pas le flux d'envoi quand le PS confirme
- [ ] Aucune donnée de santé en clair dans les logs (le corps du mail n'est jamais loggué)

## Manual Test Plan

- Lancer Blazor : `cd Client/Blazor && dotnet run`
- Lancer Angular : `cd Client/Angular && npm start`
- Rédiger un courrier avec « ci-joint le compte-rendu » dans le corps, sans
  attacher de fichier, puis cliquer sur Envoyer → vérifier l'avertissement
- Confirmer « Envoyer quand même » → le courrier part
- Recommencer en attachant un fichier → aucun avertissement
- Rédiger un courrier sans mention ni fichier → aucun avertissement

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors exigence DSR spécifique — confort de rédaction
- **Exigences DSR honorées** : non applicable — aide à la saisie, n'altère pas le contenu ni le transport MSSanté
- **INS** : non applicable
- **Authentification PS** : inchangé — session PS déjà authentifiée
- **Habilitations** : non applicable
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : non applicable — l'avertissement est purement local au compositeur ; aucune donnée à journaliser
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — fonctionnalité 100 % front, le corps du courrier ne quitte pas le compositeur tant que l'envoi n'est pas confirmé
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement de données

## Develop log

- Front-only (client-blazor + client-angular). Détection équivalente dans les 2 fronts (même liste FR), pas de backend, pas de DTO.
- Blazor : `AttachmentReminderDetector` (pur) + hook `NewMailComponent.OnValidSubmit` (DialogService.Confirm) + 4 clés i18n. 13 tests, suite 112/112.
- Angular : util `attachment-reminder.util.ts` (pur) + hook `mail-compose.send()` (dialogue inline réutilisant `showConfirmDialog`/resolver existant) + bloc template `data-testid=compose-missing-attachment-*`. 13 tests util, suite mss-lib 212/212. Lint 0 erreur.

## PRs

- **client-blazor** : https://github.com/codengine-technologies/HealthPlatform.Client/pull/57 — `awaiting-human-merge`.
- **client-angular** : code-only — l'humain gère commit/push TFS. Fichiers : `core/utils/attachment-reminder.util.{ts,spec.ts}` (nouveaux), `mail-compose.component.{ts,html}`.
- **dtos-mss** : branche auto-incluse vide, pas de PR.

## Code Review Summary

Verdict : **APPROVED**. Détecteurs purs testés (casse/accents/HTML/token PJ), réutilisation des mécanismes de dialogue existants des deux fronts, aucune chaîne en dur (Blazor Localizer ; Angular FR convention MSS), aucun flux d'envoi altéré sur confirmation. Sonar skip (api-mail non touché).
