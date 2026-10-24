# task-393 — /review : CHANGES REQUESTED (1 bloquant weda2)

**Nature du blocage** : défaut fonctionnel trouvé en revue de code (relecture indépendante, confirmée à la lecture).
Build, tests et e2e sont verts : aucun test n'emprunte le chemin fautif.

## ❌ Bloquant — weda2 : « Écrire » depuis une ligne, contact à plusieurs adresses sans adresse par défaut

- **Où** : `Client/Angular/front/libs/mss/src/features/contacts/mss-contacts.component.html`, environ l. 929-940. Le
  bouton `contact-quick-write-{id}` est dans un `div` qui fait `$event.stopPropagation()`. Côté
  `mss-contacts.component.ts`, `writeTo` (environ l. 706-713) fait `writeChoice.set(contact)` sans sélectionner le
  contact. Le sélecteur `contact-write-choose` (environ l. 1063) n'est rendu que dans l'aperçu,
  sous `@if (selectedContact(); as selected)` (l. 983).
- **Scénario 1** : aucun contact n'est sélectionné. « Écrire » au survol d'un contact à deux adresses sans adresse
  par défaut : rien ne s'affiche.
- **Scénario 2** : un contact A est sélectionné. « Écrire » sur la ligne de B, contact à deux adresses sans adresse
  par défaut : « À quelle adresse écrire ? » s'affiche dans l'aperçu de A, avec les adresses de B sous l'en-tête de A.
  Le médecin peut se tromper de destinataire pour un message de santé.
- **DOD touchée** : « weda2 et mobile — "Écrire un message" : … choix préalable sans adresse par défaut et avec
  plusieurs adresses ». Le test de composant ne passe que par l'aperçu
  (`mss-contacts-refonte.component.spec.ts`, environ l. 393-406).
- **Correctif attendu** (reprise `/develop`) : sélectionner le contact dans `writeTo` avant de proposer le choix (ou
  rendre le sélecteur indépendant de la sélection). Ajouter un test de composant **rouge d'abord** depuis la ligne,
  sans sélection préalable, et pour un autre contact déjà sélectionné.

## À corriger dans la même reprise (non bloquant, peu coûteux)

1. **mobile, écart à la task (b)** : la fiche de consultation n'offre pas « Supprimer ». Il n'est accessible que dans
   l'éditeur, alors que la task demande « les mêmes actions » que l'aperçu weda2 (menu « ⋯ » avec « Supprimer »).
2. **mobile, test qui ne prouve pas ce qu'il dit** : `contacts.page.spec.ts`, environ l. 357-366 (« retirer l'adresse
   par défaut retire la désignation »). Il passerait sans le correctif, car `toContactDto` envoie `null` pour une
   adresse absente. Il faut lire la désignation après le retrait.
3. **mobile, accessibilité** : les boutons radio et les boutons de copie portent un `aria-label` identique sur chaque
   ligne. Y inclure l'adresse, comme dans weda2.
4. **weda2** : `offer()` est appelé avant `navigate()`. Une navigation refusée laisse un destinataire en attente,
   repris à la prochaine entrée dans la messagerie. N'offrir qu'après une navigation réussie, ou vider le service si
   elle échoue.

## Suggestions laissées à l'appréciation

- Œ, Æ et Ø tombent dans « # », d'où une seconde section « # » et une clé de `@for` en double.
- Vider puis retaper l'adresse par défaut lui fait perdre sa désignation. C'était déjà le cas avec la task-379 ; c'est
  plus visible avec le bouton radio.
- Import et export vCard depuis le menu « ⋯ » : aucun test.
- E2E-CONTACT-004 : avec une seule adresse, « l'adresse par défaut en premier » n'est pas exercée en e2e (elle est
  couverte en unitaire).
- `mss-contacts.component.ts` à 1 803 lignes : découper en liste, aperçu et fiche.

## Reprise

Relancer `/develop task-393`, centré sur le bloquant et les points 1 à 4, puis la chaîne continue d'elle-même. Le
reste du travail est validé : builds, tests (weda2 1 202, mobile 1 238, api-mail 6 767), lint, e2e vert sur les deux
voies, mutations.
