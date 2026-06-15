# todo-task-085.md — Correcteur orthographique à la rédaction (FR)

**Repos**: client-blazor, client-angular
**Epic**: E009

> US front-only justifiée : la correction orthographique s'opère dans le
> compositeur côté client. Aucune donnée n'est envoyée à un service externe.

## Objective

Aider le professionnel de santé à rédiger des courriers sans fautes en activant
une **vérification orthographique française** dans le compositeur de courrier.
Inspiré de la fonction spell-check de Roundcube. Contrainte santé forte : la
correction doit s'opérer **localement** (navigateur), aucun envoi du contenu du
courrier vers un service tiers cloud (risque de fuite de données de santé).

## Comportement attendu

- Le champ de rédaction du courrier active la vérification orthographique
  native du navigateur en français (`spellcheck="true"` + `lang="fr"`).
- Les mots mal orthographiés sont soulignés ; le PS accède aux suggestions via
  le menu contextuel natif du navigateur.
- La vérification ne s'applique qu'au corps du courrier (et éventuellement à
  l'objet), pas aux champs techniques.
- Aucun contenu du courrier n'est transmis à un service de correction externe.
- Le comportement est cohérent entre Blazor et Angular.

## Gherkin

```gherkin
Feature: Correcteur orthographique à la rédaction

  Scenario: Soulignement des fautes en français
    Given un médecin rédige un courrier en français
    When il saisit un mot mal orthographié
    Then le mot est souligné comme potentiellement incorrect
    And des suggestions de correction sont accessibles

  Scenario: Aucune transmission externe du contenu
    Given un médecin rédige un courrier contenant des données de santé
    When la vérification orthographique s'exécute
    Then aucun contenu du courrier n'est transmis à un service externe
```

## Definition of Done

- [ ] Build passes sur chaque repo listé (0 erreur)
- [ ] Blazor : champ de rédaction avec `spellcheck="true"` et `lang="fr"`, `data-testid`
- [ ] Angular : idem côté front legacy, `data-testid`
- [ ] La correction reste strictement locale au navigateur (aucun appel réseau de correction)
- [ ] >= 1 test de composant par frontend vérifiant la présence des attributs `spellcheck`/`lang` sur le compositeur
- [ ] Aucune régression du compositeur (envoi, brouillon, pièces jointes inchangés)

## Manual Test Plan

- Lancer Blazor : `cd Client/Blazor && dotnet run`
- Lancer Angular : `cd Client/Angular && npm start`
- Ouvrir le compositeur de courrier
- Saisir un mot volontairement mal orthographié en français → vérifier le
  soulignement et l'accès aux suggestions via clic droit
- Ouvrir les outils réseau du navigateur et confirmer qu'aucune requête sortante
  ne contient le texte saisi

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors exigence DSR spécifique — confort de rédaction
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : inchangé
- **Habilitations** : non applicable
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : non applicable — traitement local, aucun évènement métier
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Sécurité / confidentialité** : correction strictement locale au navigateur — interdiction d'un service de correction cloud tiers susceptible d'exfiltrer des données de santé
- **Hébergement HDS** : non — aucun traitement serveur
- **AIPD / impact RGPD** : inchangé — aucune donnée transmise ni persistée

## Develop log

- Front-only (client-blazor + client-angular). Vérification orthographique native navigateur FR, 100% locale (aucun service tiers).
- Blazor : `RadzenHtmlEditor` (corps) + `RadzenTextBox` (objet) `spellcheck="true" lang="fr"` + `data-testid`. Test bUnit rendu complet `NewMailComponent` (assert attributs). Suite 100/100.
- Angular : éditeur TipTap `editorProps.attributes` (spellcheck/lang/data-testid) dans `html-editor.component.ts`. Spec dédié. Suite mss-lib 213/213. Lint 0 erreur.

## PRs

- **client-blazor** : https://github.com/codengine-technologies/HealthPlatform.Client/pull/58 — `awaiting-human-merge`.
- **client-angular** : code-only — fichiers : `ui/html-editor/html-editor.component.ts`, `ui/html-editor/html-editor.component.spec.ts` (nouveau).
- **dtos-mss** : branche auto-incluse vide, pas de PR.

## Code Review Summary

Verdict : **APPROVED**. Attributs natifs, correction strictement locale (aucun appel réseau), data-testid, tests de composant sur les deux fronts. Sonar skip (api-mail non touché).
