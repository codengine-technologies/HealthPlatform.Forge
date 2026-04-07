Feature: Signature email du professionnel de santé

  En tant que professionnel de santé,
  je veux gérer ma signature email
  afin qu'elle soit automatiquement ajoutée à mes messages envoyés.

  Scenario: Créer une signature
    Given un professionnel de santé connecté
    And il n'a aucune signature enregistrée
    When il crée une nouvelle signature avec un nom et un contenu
    Then la signature est enregistrée dans son compte
    And elle est définie comme signature par défaut

  Scenario: Modifier une signature existante
    Given un professionnel de santé connecté
    And il possède une signature enregistrée
    When il modifie le contenu de sa signature
    Then la signature mise à jour est enregistrée

  Scenario: Supprimer une signature
    Given un professionnel de santé connecté
    And il possède une signature enregistrée
    When il supprime sa signature
    Then la signature est supprimée de son compte

  Scenario: Gérer plusieurs signatures
    Given un professionnel de santé connecté
    And il possède deux signatures enregistrées
    When il définit la seconde signature comme signature par défaut
    Then la seconde signature devient la signature par défaut
    And la première signature n'est plus la signature par défaut

  Scenario: Signature automatiquement ajoutée à un nouveau message
    Given un professionnel de santé connecté
    And il possède une signature par défaut
    When il compose un nouveau message
    Then la signature par défaut est automatiquement insérée dans le corps du message

  Scenario: Signature ajoutée lors d'une réponse
    Given un professionnel de santé connecté
    And il possède une signature par défaut
    When il répond à un message reçu
    Then la signature par défaut est insérée avant le message cité

  Scenario: Changer de signature lors de la composition
    Given un professionnel de santé connecté
    And il possède plusieurs signatures
    And il compose un nouveau message
    When il sélectionne une autre signature dans la liste
    Then la signature du message est remplacée par celle sélectionnée

  Scenario: Prévisualiser une signature
    Given un professionnel de santé connecté
    And il est en train de créer ou modifier une signature
    When il demande un aperçu
    Then il voit un rendu de sa signature telle qu'elle apparaîtra dans un message
