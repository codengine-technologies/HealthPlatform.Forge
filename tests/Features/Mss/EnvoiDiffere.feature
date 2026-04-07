Feature: Envoi différé de messages

  En tant que professionnel de santé,
  je veux pouvoir programmer l'envoi d'un message à une date et heure ultérieures
  afin de rédiger mes messages à mon rythme et les envoyer au moment opportun.

  Scenario: Programmer un envoi différé
    Given un professionnel de santé connecté
    And il compose un nouveau message
    When il programme l'envoi pour une date et heure futures
    Then le message est enregistré comme envoi programmé
    And il apparaît dans la liste des envois programmés

  Scenario: Message envoyé à l'heure programmée
    Given un professionnel de santé a programmé un envoi de message
    When la date et l'heure programmées sont atteintes
    Then le message est automatiquement envoyé aux destinataires

  Scenario: Annuler un envoi programmé
    Given un professionnel de santé connecté
    And il a un envoi programmé en attente
    When il annule l'envoi programmé
    Then le message est supprimé de la liste des envois programmés
    And le message n'est pas envoyé

  Scenario: Modifier un envoi programmé
    Given un professionnel de santé connecté
    And il a un envoi programmé en attente
    When il modifie le contenu ou l'heure d'envoi
    Then les modifications sont enregistrées
    And le message sera envoyé avec le nouveau contenu à la nouvelle heure

  Scenario: Voir la liste des envois programmés
    Given un professionnel de santé connecté
    And il a plusieurs envois programmés
    When il consulte la liste des envois programmés
    Then il voit tous ses envois en attente avec la date et l'heure prévues

  Scenario: Programmer un envoi dans le passé est refusé
    Given un professionnel de santé connecté
    And il compose un nouveau message
    When il tente de programmer l'envoi pour une date passée
    Then l'action est refusée
    And un message indique que la date doit être dans le futur
