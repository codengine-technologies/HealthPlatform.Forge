Feature: Liste de blocage

  En tant que professionnel de santé,
  je veux pouvoir bloquer certaines adresses email
  afin de ne plus recevoir de messages indésirables.

  Scenario: Bloquer une adresse depuis un message reçu
    Given un professionnel de santé connecté
    And il consulte un message reçu
    When il bloque l'expéditeur du message
    Then l'adresse de l'expéditeur est ajoutée à sa liste de blocage

  Scenario: Bloquer une adresse manuellement
    Given un professionnel de santé connecté
    And il consulte sa liste de blocage dans les paramètres
    When il ajoute une adresse à la liste de blocage
    Then l'adresse apparaît dans sa liste de blocage

  Scenario: Messages d'une adresse bloquée déplacés automatiquement
    Given un professionnel de santé connecté
    And il a bloqué une adresse
    When un nouveau message arrive de cette adresse bloquée
    Then le message est automatiquement déplacé vers le dossier indésirables

  Scenario: Débloquer une adresse
    Given un professionnel de santé connecté
    And il a une adresse dans sa liste de blocage
    When il débloque cette adresse
    Then l'adresse est retirée de la liste de blocage
    And les prochains messages de cette adresse arriveront normalement

  Scenario: Voir la liste de blocage
    Given un professionnel de santé connecté
    And il a bloqué plusieurs adresses
    When il consulte sa liste de blocage dans les paramètres
    Then il voit toutes les adresses bloquées avec la date de blocage

  Scenario: Bloquer un expéditeur ne supprime pas les messages existants
    Given un professionnel de santé connecté
    And il a reçu des messages d'un expéditeur
    When il bloque cet expéditeur
    Then les messages déjà reçus restent dans leur dossier actuel
    And seuls les futurs messages seront déplacés vers les indésirables
