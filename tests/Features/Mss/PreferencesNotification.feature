Feature: Préférences de notification

  En tant que professionnel de santé,
  je veux configurer quels événements déclenchent des notifications
  afin de ne recevoir que les alertes pertinentes pour mon activité.

  Scenario: Activer les notifications pour les nouveaux messages
    Given un professionnel de santé connecté
    And il consulte ses préférences de notification
    When il active les notifications pour les nouveaux messages
    Then il recevra une notification à chaque nouveau message reçu

  Scenario: Activer les notifications uniquement pour les messages urgents
    Given un professionnel de santé connecté
    When il active les notifications uniquement pour les messages urgents
    Then il ne recevra une notification que pour les messages identifiés comme urgents

  Scenario: Activer les notifications pour les résultats biologiques anormaux
    Given un professionnel de santé connecté
    When il active les notifications pour les résultats biologiques anormaux
    Then il recevra une notification lorsqu'un résultat anormal est détecté

  Scenario: Désactiver toutes les notifications
    Given un professionnel de santé connecté
    When il désactive toutes les notifications
    Then il ne reçoit plus aucune notification

  Scenario: Conserver les préférences entre les sessions
    Given un professionnel de santé connecté
    And il a configuré ses préférences de notification
    When il se déconnecte puis se reconnecte
    Then ses préférences de notification sont conservées
