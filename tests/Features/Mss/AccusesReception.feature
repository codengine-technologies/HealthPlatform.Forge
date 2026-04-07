Feature: Suivi des accusés de réception

  En tant que professionnel de santé,
  je veux suivre qui a lu mes messages
  afin de m'assurer que mes communications médicales ont bien été reçues.

  Scenario: Demander un accusé de réception à l'envoi
    Given un professionnel de santé connecté
    And il compose un nouveau message
    When il active l'option "Demander un accusé de réception"
    And il envoie le message
    Then le message est envoyé avec une demande d'accusé de réception

  Scenario: Voir le statut de lecture d'un message envoyé
    Given un professionnel de santé connecté
    And il a envoyé un message avec accusé de réception demandé
    When il consulte le message dans ses messages envoyés
    Then il voit le statut de lecture pour chaque destinataire
    And le statut indique "En attente" ou "Lu" avec la date de lecture

  Scenario: Réception d'un accusé de lecture
    Given un professionnel de santé connecté
    And il a envoyé un message avec accusé de réception demandé
    When un destinataire lit le message et envoie l'accusé
    Then le statut du destinataire passe à "Lu"
    And la date et l'heure de lecture sont enregistrées

  Scenario: Accusé de réception pour plusieurs destinataires
    Given un professionnel de santé connecté
    And il a envoyé un message à trois destinataires avec accusé demandé
    When deux des trois destinataires ont lu le message
    Then le suivi indique deux lectures sur trois destinataires
    And chaque destinataire a son propre statut

  Scenario: Message sans accusé de réception demandé
    Given un professionnel de santé connecté
    And il a envoyé un message sans demander d'accusé
    When il consulte le message dans ses messages envoyés
    Then aucun suivi de lecture n'est affiché
