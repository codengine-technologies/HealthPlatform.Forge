Feature: Réponse automatique en cas d'absence

  En tant que professionnel de santé,
  je veux configurer un message de réponse automatique
  afin d'informer mes correspondants lorsque je suis absent.

  Scenario: Activer la réponse automatique
    Given un professionnel de santé connecté
    When il active la réponse automatique avec une date de début et une date de fin
    And il saisit un objet et un message d'absence
    Then la réponse automatique est activée pour la période définie

  Scenario: Réponse envoyée à un correspondant
    Given un professionnel de santé a activé sa réponse automatique
    And la période d'absence est en cours
    When un correspondant lui envoie un message
    Then le correspondant reçoit automatiquement le message d'absence

  Scenario: Un seul message d'absence par correspondant
    Given un professionnel de santé a activé sa réponse automatique
    And un correspondant a déjà reçu le message d'absence
    When le même correspondant envoie un nouveau message
    Then aucun second message d'absence n'est envoyé

  Scenario: Désactiver la réponse automatique
    Given un professionnel de santé connecté
    And sa réponse automatique est activée
    When il désactive la réponse automatique
    Then les prochains messages reçus ne déclenchent plus de réponse automatique

  Scenario: Fin automatique de la période d'absence
    Given un professionnel de santé a activé sa réponse automatique
    When la date de fin de la période d'absence est passée
    Then la réponse automatique est automatiquement désactivée

  Scenario: Modifier le message d'absence en cours
    Given un professionnel de santé connecté
    And sa réponse automatique est activée
    When il modifie le message d'absence
    Then les prochaines réponses automatiques utilisent le nouveau message

  Scenario: Prévisualiser le message d'absence
    Given un professionnel de santé connecté
    And il configure sa réponse automatique
    When il demande un aperçu du message
    Then il voit le message tel qu'il sera reçu par ses correspondants
