Feature: Gestion des dossiers personnalisés

  En tant que professionnel de santé,
  je veux pouvoir créer mes propres dossiers de classement
  afin d'organiser mes messages selon mes besoins.

  Scenario: Créer un nouveau dossier
    Given un professionnel de santé connecté
    When il crée un nouveau dossier nommé "Urgences cardiologie"
    Then le dossier "Urgences cardiologie" apparaît dans sa liste de dossiers

  Scenario: Créer un sous-dossier
    Given un professionnel de santé connecté
    And il possède un dossier "Patients"
    When il crée un sous-dossier "Suivi chronique" dans "Patients"
    Then le sous-dossier apparaît sous le dossier parent

  Scenario: Renommer un dossier
    Given un professionnel de santé connecté
    And il possède un dossier personnalisé "Ancien nom"
    When il renomme le dossier en "Nouveau nom"
    Then le dossier est affiché avec le nouveau nom
    And les messages qu'il contient sont conservés

  Scenario: Supprimer un dossier vide
    Given un professionnel de santé connecté
    And il possède un dossier personnalisé vide
    When il supprime le dossier
    Then le dossier disparaît de sa liste

  Scenario: Supprimer un dossier contenant des messages
    Given un professionnel de santé connecté
    And il possède un dossier personnalisé contenant des messages
    When il tente de supprimer le dossier
    Then une confirmation lui est demandée
    And après confirmation les messages sont déplacés vers la corbeille
    And le dossier est supprimé

  Scenario: Déplacer un message vers un dossier personnalisé
    Given un professionnel de santé connecté
    And il possède un dossier personnalisé
    And il consulte un message dans sa boîte de réception
    When il déplace le message vers le dossier personnalisé
    Then le message apparaît dans le dossier personnalisé
    And le message n'est plus dans la boîte de réception

  Scenario: Déplacer plusieurs messages en lot
    Given un professionnel de santé connecté
    And il a sélectionné plusieurs messages
    When il déplace la sélection vers un dossier personnalisé
    Then tous les messages sélectionnés sont déplacés

  Scenario: Impossibilité de supprimer les dossiers système
    Given un professionnel de santé connecté
    When il tente de supprimer le dossier Boîte de réception
    Then l'action est refusée
    And un message indique que les dossiers système ne peuvent pas être supprimés
