Feature: Listes de diffusion

  En tant que professionnel de santé,
  je veux pouvoir envoyer un message à un groupe de contacts en un clic
  afin de communiquer efficacement avec une équipe ou un cercle de soins.

  Scenario: Envoyer un message à un groupe de contacts
    Given un professionnel de santé connecté
    And il possède un groupe de contacts "Équipe cardiologie" avec trois membres
    When il compose un nouveau message et sélectionne le groupe "Équipe cardiologie" comme destinataire
    Then les adresses des trois membres sont ajoutées dans les destinataires

  Scenario: Suggestion des groupes dans l'auto-complétion
    Given un professionnel de santé connecté
    And il possède des groupes de contacts
    When il commence à saisir un nom de groupe dans le champ destinataire
    Then les groupes correspondants apparaissent dans les suggestions
    And les groupes sont distingués visuellement des contacts individuels

  Scenario: Voir les membres d'un groupe avant envoi
    Given un professionnel de santé connecté
    And il a sélectionné un groupe comme destinataire
    When il clique sur le groupe dans le champ destinataire
    Then il voit la liste des membres du groupe avec leurs adresses

  Scenario: Retirer un membre de la liste après sélection du groupe
    Given un professionnel de santé connecté
    And il a sélectionné un groupe comme destinataire
    And les adresses des membres sont affichées
    When il retire un des membres de la liste
    Then le message sera envoyé aux membres restants uniquement

  Scenario: Groupe sans adresse de messagerie valide
    Given un professionnel de santé connecté
    And il possède un groupe dont un membre n'a pas d'adresse de messagerie
    When il sélectionne ce groupe comme destinataire
    Then seuls les membres ayant une adresse valide sont ajoutés
    And un avertissement indique que certains membres n'ont pas d'adresse
