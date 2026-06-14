# todo-task-087.md — Affichage du quota d'occupation de la boîte MSSanté

**Repos**: api-mail, client-blazor, client-angular
**Epic**: E009

## Objective

Donner au professionnel de santé une **visibilité sur l'occupation de sa boîte
MSSanté** : espace utilisé, quota total et pourcentage de remplissage. Inspiré
de l'affichage de quota IMAP de Roundcube. Cas d'usage : anticiper une boîte
pleine (qui bloquerait la réception de nouveaux courriers de santé), sans
attendre un rejet d'envoi côté correspondant.

## Comportement attendu

- Le backend interroge le quota IMAP (extension `QUOTA` / `QUOTAROOT`) de la
  boîte du PS et expose espace utilisé, quota total et pourcentage.
- Une jauge d'occupation est affichée dans l'interface (ex. en pied de liste
  des dossiers ou dans les paramètres du compte).
- Si le serveur IMAP n'annonce pas l'extension QUOTA, l'interface affiche
  proprement « quota non disponible » sans erreur bloquante.
- Un seuil d'alerte visuel (ex. > 90 %) signale une boîte presque pleine.
- La valeur est rafraîchie périodiquement / au chargement, sans appel coûteux à
  chaque action.
- 

## Gherkin

```gherkin
Feature: Affichage du quota de la boîte MSSanté

  Scenario: Boîte avec quota disponible
    Given une boîte MSSanté dont le serveur annonce un quota
    When le médecin consulte sa messagerie
    Then il voit l'espace utilisé, le quota total et le pourcentage de remplissage

  Scenario: Alerte boîte presque pleine
    Given une boîte remplie à plus de 90 % de son quota
    When le médecin consulte sa messagerie
    Then une alerte visuelle signale que la boîte est presque pleine

  Scenario: Serveur sans extension de quota
    Given un serveur IMAP qui n'annonce pas de quota
    When le médecin consulte sa messagerie
    Then l'interface indique que le quota n'est pas disponible
    And aucune erreur bloquante n'est affichée
```

## Definition of Done

- [ ] Build passes sur chaque repo listé (0 erreur)
- [ ] Endpoint backend `GET account/quota` (ou équivalent) renvoyant espace utilisé, quota total, pourcentage et un indicateur « disponible/non disponible »
- [ ] Lecture du quota via l'extension IMAP QUOTA (MailKit) ; dégradation propre si non supportée
- [ ] >= 1 test unitaire par comportement (quota disponible, quota indisponible, calcul du pourcentage, seuil d'alerte)
- [ ] >= 1 test d'intégration de l'endpoint (cas disponible + cas non supporté)
- [ ] Blazor : jauge d'occupation + état « non disponible », seuil d'alerte visuel, aucune chaîne en dur (i18n), `data-testid`
- [ ] Angular : idem côté front legacy, aucune chaîne en dur (i18n), `data-testid`
- [ ] Erreurs renvoyées en `ProblemDetails` (RFC 7807) via le `GlobalExceptionHandler` (règle 12)
- [ ] Aucune donnée de santé en clair dans les logs (seules des métriques de volumétrie sont loggées)

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run`
- Lancer Blazor : `cd Client/Blazor && dotnet run`
- Lancer Angular : `cd Client/Angular && npm start`
- Se connecter à une boîte MSSanté de test
- Vérifier l'affichage de la jauge (espace utilisé / quota / pourcentage)
- Simuler / utiliser une boîte > 90 % → vérifier l'alerte visuelle
- Utiliser une boîte dont le serveur n'annonce pas de quota → vérifier le
  message « quota non disponible » sans erreur bloquante

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors exigence DSR spécifique — supervision de la boîte
- **Exigences DSR honorées** : non applicable — n'altère pas le transport MSSanté ni le contenu des courriers
- **INS** : non applicable — donnée d'infrastructure (volumétrie), aucune donnée patient
- **Authentification PS** : inchangé — quota lu pour la boîte du PS authentifié
- **Habilitations** : lecture du quota limitée à la boîte du PS authentifié
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : non applicable — lecture d'une métrique technique (option : journaliser un seuil d'alerte franchi)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement existant ; le quota est une métadonnée de volumétrie, pas une donnée de santé
- **AIPD / impact RGPD** : inchangé — aucune donnée personnelle nouvelle traitée
