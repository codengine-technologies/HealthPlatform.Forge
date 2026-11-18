> **Résolu le 2026-11-18** — l'humain a relevé la règle 13 (5 reprises, un bloquant toléré une fois en récidive) et demandé la reprise 2.

# task-487 — revue anticipée, passage 2 : un bloquant revenu après la reprise

**Étape** : /review --code (passage 2, après la reprise 1). **Chaîne arrêtée** (règle 13 : un bloquant qui revient après
une reprise arrête la chaîne).

## Ce qui est fait

- dtos-mss 621.0.0 publié ; api-mail, client-mobile poussés sur `feat/task-487-conversation-en-chat-lire-le-fil-et` ;
  weda2 non commité sur `feature/nova-mss-weda-integration` (code-only).
- Serveur : contrat de conversation, réponse composée, accusés reçus, lecture à l'ouverture tracée ; 10 tests
  d'intégration de bout en bout, 34 mutations, toutes rouges.
- Clients : vues chat mobile et weda2, E2E-CONV-001 et E2E-CONV-002 verts sur les deux voies et prouvés par mutation.
- Reprise 1 : sept constats sur huit corrigés (B1, B3, B4, les accusés, la page lointaine, les points weda2 et mobile).
  Détail dans la task, `## Code Review Summary`.

## Ce qui bloque

1. **R1 (retour de B2) — un PS peut encore être masqué** sous la signature quand le message cité porte lui aussi une
   signature, ou quand la marque de fin manque. La plage de signature est calculée sur tout le message, citation
   comprise. Correctif identifié : ne garder que la première suite de lignes de signature, hors citation, et seulement
   si elle se termine avant l'historique. Ajouter un cas au corpus avec réponse et parent signés.
2. **R2 (weda2)** — relire la page 1 avant l'envoi peut faire partir la réponse dans un autre fil si le médecin change
   de conversation pendant la relecture : historique cité d'un patient envoyé aux correspondants d'un autre fil.
   Correctif identifié : capturer le fil, les destinataires et le numéro de chargement à l'envoi, et ne rien écrire ni
   envoyer si le fil a changé.
3. **R3 (mobile)** — une bulle « prêt à partir » disparaît à la relecture alors que la réponse n'est pas confirmée.
   Correctif identifié : ne retirer la bulle qu'une fois l'envoi en attente disparu (lecture de `pending-emails`, ou un
   identifiant rendu par le 202).

Les trois sont corrigeables par le code. L'arrêt tient seulement à la règle de récidive : R1 est B2, qui revient.

## Décision attendue

- **Relancer une reprise 2** (`/develop task-487 --reprise`, la dernière permise) pour R1, R2 et R3. C'est ma
  recommandation : les trois correctifs sont identifiés et bornés.
- Ou reprendre la main sur ces points.

## Arbitrages ouverts (non bloquants, rappel)

- Joindre un document du dossier patient depuis le chat weda2 : absent, faute de parcours existant dans weda2.
- Bouton d'ouverture de la vue chat en mode Conversation (weda2) au lieu du clic sur la ligne.
- Sens de l'avertissement « Les destinataires ont changé ».
- Coupe à 12 lignes de texte ou à 12 lignes affichées.
- Corpus : formes réelles reconstruites, pas de vrais messages anonymisés.
- Accusés reçus avant task-459 encore affichés comme bulles sur les boîtes existantes.
