Feature: Gestion des brouillons

  En tant que professionnel de santé,                                                               je veux pouvoir sauvegarder mes messages en cours de rédaction                                    afin de ne pas perdre mon travail et de pouvoir le reprendre plus tard.                       
                                                                                                      # --- Composition dans la zone détail ---                                                     
                                                                                                  
    Scenario: Composer un nouveau message dans la zone de détail
      Given un professionnel de santé connecté
      When il clique sur "Nouveau message"
      Then le formulaire de composition s'affiche dans la zone de détail du message
      And aucune fenêtre superposée n'apparaît

    Scenario: Un brouillon est créé dès l'ouverture du formulaire
      Given un professionnel de santé connecté
      When il clique sur "Nouveau message"
      Then un brouillon vide est créé automatiquement

    # --- Sauvegarde ---

    Scenario: Sauvegarder un brouillon manuellement
      Given un professionnel de santé connecté
      And il compose un nouveau message avec des destinataires et un contenu
      When il enregistre le message comme brouillon
      Then le message est sauvegardé dans le dossier Brouillons

    Scenario: Sauvegarde automatique périodique
      Given un professionnel de santé connecté
      And il compose un nouveau message
      And il a saisi du contenu
      When trente secondes se sont écoulées sans sauvegarde
      Then le message est automatiquement sauvegardé comme brouillon

    Scenario: Modifier et re-sauvegarder un brouillon
      Given un professionnel de santé connecté
      And il a repris un brouillon existant
      When il modifie le contenu et sauvegarde à nouveau
      Then le brouillon existant est mis à jour sans créer de doublon

    # --- Consultation et reprise ---

    Scenario: Voir la liste des brouillons
      Given un professionnel de santé connecté
      And il possède plusieurs brouillons enregistrés
      When il consulte le dossier Brouillons
      Then il voit la liste de ses brouillons avec la date de dernière modification
      And chaque brouillon est visuellement identifiable comme tel

    Scenario: Reprendre un brouillon en cliquant dessus
      Given un professionnel de santé connecté
      And il possède un brouillon enregistré
      When il clique sur le brouillon dans le dossier Brouillons
      Then le formulaire de composition s'ouvre directement en mode édition dans la zone de détail
      And les destinataires, le sujet et le corps sont restaurés

    # --- Envoi et suppression ---

    Scenario: Envoyer un brouillon
      Given un professionnel de santé connecté
      And il a repris un brouillon existant
      When il envoie le message
      Then le message est envoyé aux destinataires
      And le brouillon est supprimé du dossier Brouillons

    Scenario: Supprimer un brouillon
      Given un professionnel de santé connecté
      And il possède un brouillon enregistré
      When il supprime le brouillon
      Then le brouillon est retiré du dossier Brouillons

    # --- Navigation pendant la rédaction ---

    Scenario: Quitter la rédaction en enregistrant le brouillon
      Given un professionnel de santé connecté
      And il est en train de rédiger un message
      When il clique sur un autre message dans la liste
      Then une demande de confirmation apparaît avec les choix "Enregistrer comme brouillon" et   
  "Annuler"
      When il choisit "Enregistrer comme brouillon"
      Then le brouillon est sauvegardé
      And le message sélectionné s'affiche dans la zone de détail

    Scenario: Quitter la rédaction en annulant le brouillon
      Given un professionnel de santé connecté
      And il est en train de rédiger un message
      When il clique sur un autre message dans la liste
      Then une demande de confirmation apparaît avec les choix "Enregistrer comme brouillon" et   
  "Annuler"
      When il choisit "Annuler"
      Then le brouillon est supprimé
      And le message sélectionné s'affiche dans la zone de détail

    # --- Synchronisation avec le serveur ---

    Scenario: Un brouillon sauvegardé est disponible sur le serveur de messagerie
      Given un professionnel de santé connecté
      And il a sauvegardé un brouillon
      When la synchronisation avec le serveur de messagerie s'effectue
      Then le brouillon est disponible dans le dossier Brouillons du serveur
      And il est accessible depuis n'importe quel logiciel de messagerie

    # --- Mode hors ligne ---

    Scenario: Un bandeau "Hors ligne" s'affiche quand la connexion au service de messagerie est perdue
      Given un professionnel de santé en train de rédiger un message
      When le service de messagerie devient injoignable
      Then un bandeau "Hors ligne" s'affiche en haut de la zone de détail
      And le professionnel peut continuer à rédiger sans interruption
      And aucune fenêtre d'erreur ne perturbe la rédaction

    Scenario: Le brouillon est synchronisé automatiquement quand la connexion revient
      Given un professionnel de santé qui a rédigé un message en mode hors ligne
      And le bandeau "Hors ligne" est affiché
      When la connexion au service de messagerie est rétablie
      Then le bandeau "Hors ligne" disparaît
      And le brouillon est automatiquement sauvegardé sur le serveur
      And aucune action manuelle n'est demandée au professionnel