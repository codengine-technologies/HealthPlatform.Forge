# todo-task-086.md — Import / export des contacts au format vCard

**Repos**: api-mail, client-blazor, client-angular
**Epic**: E009

## Objective

Permettre au professionnel de santé d'**importer** et d'**exporter** son carnet
d'adresses au format **vCard** (`.vcf`), standard d'échange de contacts.
Inspiré des actions `import.php` / `export.php` de Roundcube. Cas d'usage :
récupérer un carnet existant depuis un autre logiciel, ou sauvegarder/transférer
ses correspondants MSSanté.

## Comportement attendu

- **Export** : le PS exporte son carnet d'adresses (ou une sélection) dans un
  fichier `.vcf` (vCard 3.0/4.0) contenant nom, prénom, adresses MSSanté,
  organisation, et le cas échéant RPPS/profession lorsqu'ils sont déjà connus.
- **Import** : le PS importe un fichier `.vcf` ; chaque contact est créé ou
  mis à jour dans son carnet.
- **Anti-doublon** : à l'import, un contact dont l'adresse MSSanté (ou le RPPS)
  existe déjà n'est pas dupliqué — il est mis à jour, jamais cloné.
- Un compte-rendu d'import est présenté : nombre de contacts créés, mis à jour,
  ignorés (et raison).
- Les contacts issus de l'Annuaire Santé restent cohérents : pas de création de
  doublon RPPS.

## Gherkin

```gherkin
Feature: Import et export des contacts au format vCard

  Scenario: Export du carnet d'adresses
    Given un médecin disposant de plusieurs contacts
    When il exporte son carnet d'adresses
    Then un fichier vCard contenant ses contacts est téléchargé

  Scenario: Import d'un fichier vCard
    Given un fichier vCard contenant deux nouveaux contacts
    When le médecin importe ce fichier
    Then les deux contacts sont ajoutés à son carnet
    And un compte-rendu indique deux contacts créés

  Scenario: Anti-doublon à l'import
    Given un fichier vCard contenant un contact dont l'adresse MSSanté existe déjà
    When le médecin importe ce fichier
    Then le contact existant est mis à jour
    And aucun doublon n'est créé
```

## Definition of Done

- [ ] Build passes sur chaque repo listé (0 erreur)
- [ ] Endpoint backend export : `GET contacts/export/vcard` (optionnellement filtré) → `text/vcard`
- [ ] Endpoint backend import : `POST contacts/import/vcard` (multipart) → compte-rendu (créés / mis à jour / ignorés)
- [ ] Anti-doublon par adresse MSSanté et/ou RPPS — pas de duplication de contact ni de RPPS
- [ ] Parsing/sérialisation vCard 3.0 et 4.0 (lecture tolérante)
- [ ] >= 1 test unitaire par comportement (export, import création, import mise à jour, anti-doublon, vCard malformée → erreur claire)
- [ ] >= 1 test d'intégration par endpoint (export happy path, import multipart happy path + fichier invalide)
- [ ] Blazor : actions Importer / Exporter, sélecteur de fichier, affichage du compte-rendu, aucune chaîne en dur (i18n), `data-testid`
- [ ] Angular : idem côté front legacy, aucune chaîne en dur (i18n), `data-testid`
- [ ] Erreurs renvoyées en `ProblemDetails` (RFC 7807) via le `GlobalExceptionHandler` (règle 12)
- [ ] Aucune donnée de santé en clair dans les logs (contenu des contacts non loggué)

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run`
- Lancer Blazor : `cd Client/Blazor && dotnet run`
- Lancer Angular : `cd Client/Angular && npm start`
- Ouvrir le carnet d'adresses, cliquer sur Exporter → vérifier le téléchargement
  d'un `.vcf` ouvrable (contacts présents)
- Cliquer sur Importer, sélectionner un `.vcf` de 2 nouveaux contacts → vérifier
  le compte-rendu « 2 créés » et leur apparition dans le carnet
- Réimporter le même fichier → vérifier « 2 mis à jour, 0 créé » (anti-doublon)
- Importer un fichier `.vcf` malformé → vérifier un message d'erreur clair

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors exigence DSR spécifique — gestion du carnet d'adresses
- **Exigences DSR honorées** : non applicable — n'altère pas l'Annuaire Santé national ni le transport MSSanté
- **INS** : non applicable — les contacts sont des correspondants (PS / structures), pas des patients
- **Authentification PS** : inchangé — carnet propre au PS authentifié
- **Habilitations** : import/export limités au carnet du PS authentifié
- **Interop CI-SIS** : non applicable — vCard est un standard de contact, hors volets CI-SIS
- **Tracé PGSSI-S** : journaliser « export carnet » et « import carnet » (volumétrie : nombre de contacts) — conservation selon politique en vigueur
- **Consentement patient** : non applicable
- **Référentiels métier** : RPPS / ADELI utilisés pour l'anti-doublon lorsqu'ils sont présents — aucune création de RPPS
- **Hébergement HDS** : oui — environnement existant (le carnet d'adresses est déjà persisté)
- **AIPD / impact RGPD** : à vérifier — un import de contacts est un traitement de données personnelles (coordonnées de PS) ; confirmer la couverture par l'AIPD existante
