# Anneau de traitement — challenge du design

> **Date** : 2026-11-27. Complète la [spécification](specification.md) et les [maquettes](maquettes.html).
> Les maquettes dessinent quatre variantes sur les mêmes données ; le sélecteur en haut de la page passe de l'une à
> l'autre.

## 1. Les quatre variantes

| Variante | Principe | Taille dans la liste |
|---|---|---|
| **A — demande littérale** | Arc en pointe, sens de rotation, balle au centre ou dehors, cernes, couleur de gravité, pastille rouge, initiales en pastille sur l'anneau, pastille vide si non affecté | 24 px |
| **B — le centre dit à qui** | Même grammaire, mais le centre répond à « à qui le tour » : point = moi, initiales = collègue, rond pointillé = personne, balle sortie = tiers. Triangle de gravité, coche de fermeture | 32 px web, 40 px mobile, à la place de l'initiale de l'expéditeur |
| **C — sobre** | Petit anneau : étapes et couleur de gravité. Le reste en pastilles de texte | 18 px |
| **D — hybride issu de la revue** | Anneau à la taille de B, qui dit l'avancement et la gravité. Centre : initiales de la personne attribuée, coche ou croix. Le reste est écrit à droite | 32 px web, 40 px mobile |

La variante D n'existait pas avant la revue contradictoire. Elle en est le résultat.

## 2. Alternatives par choix visuel

| Choix | Option de la demande | Alternatives | Retenu après revue | Pourquoi |
|---|---|---|---|---|
| Ce qui reste à faire | Trou vide | Piste claire ; traits fins contrastés | Traits fins contrastés | Le trou seul ne dit pas combien d'étapes restent. La piste claire était presque invisible (contraste estimé 1,2:1) alors que c'est le cœur de l'idée |
| Sens reçu / envoyé | Pointe et sens de rotation | Aucun codage ; libellé « Envoyé » | Aucun codage | À 32 px personne ne distingue horaire d'antihoraire. La pointe fait lire « actualiser » ou « synchronisation en cours ». Le dossier et le libellé disent déjà le sens |
| À qui le tour | Balle au centre ou dehors, initiales sur l'anneau | Le centre dit à qui (B) ; pastille d'initiales à droite | **Initiales dans l'anneau** (décision du product owner, 2026-11-27) ; « Attente patient » écrit | La revue proposait de garder la pastille à droite. Écarté : l'information serait en double. La pastille de task-457 est supprimée de la ligne et du détail |
| Non affecté | Pastille vide | Rond pointillé au centre ; « Non affecté » écrit | « Non affecté » écrit | Le rond pointillé mesurait 7 px et ressemblait au signe « hors suivi ». C'est l'état le plus risqué d'une boîte partagée |
| Ancienneté | Cernes | Compteur J+N ; épaisseur du trait | Compteur J+N, plein au dernier seuil | Deux et trois cernes se confondent, débordent de la ligne et noient les segments en rouge. Le médecin testé n'a trouvé la lettre de 15 jours que par « J+15 » |
| Gravité | Couleur, pastille rouge | Couleur et triangle ; couleur et pastille ⚠ n existante | Couleur et pastille ⚠ n | La pastille rouge seule ne distingue pas anormal de critique et disparaît en niveaux de gris. Le « ! » du triangle est illisible. La pastille ⚠ n est déjà apprise et porte le nombre de valeurs |
| Fermeture | Anneau plein atténué | Anneau plein et coche ; coche fine | Coche fine | Le rond gris plein se lit « case non cochée ». Sur 200 lignes, 150 anneaux épais forment un mur |
| Place dans la liste | À gauche, à la place ou en plus de l'icône | Colonne dédiée ; à droite | À la place de l'initiale de l'expéditeur | L'initiale n'informe pas (« D » pour tous les « Dr … »). Aucune largeur perdue |
| Message hors suivi | Catégorie « insignifiant » à définir | Aucun signe ; cercle pointillé | Cercle pointillé, « Pour info » seulement | À rapprocher de la remarque 4 du § 4 : il ne doit pas servir aux biologies antérieures au suivi |

## 3. Revue contradictoire

Un sous-agent a joué deux rôles sur vingt captures (liste, planche d'états, détail, tuile, légende, 200 lignes,
niveaux de gris) : un designer d'outils professionnels denses, et un médecin généraliste pressé qui ne lit pas de
légende. Il ne connaissait pas la variante D, qui n'existait pas.

### Test des 3 secondes, sans légende

| Ce qu'il fallait repérer | A | B | C |
|---|---|---|---|
| Potassium critique, non affecté | Trouvé, par le texte | Trouvé, par le texte | Trouvé, par ⚠ 1 |
| Lettre de liaison de 15 jours | Invisible | Non trouvée : « une cible grise » | Trouvée, par « J+15 » |
| Envoi non distribué | Confondu avec le potassium (même rouge) | Vu une fois sur deux | Raté |
| Fausse priorité | — | L'INR, déjà en attente du patient, est l'objet le plus lourd de l'écran | — |
| Contresens | Traité = « case non cochée » | « CD » pris pour l'expéditeur ; pointe = « synchronisation » ; pointillé = « pas chargé » | « (—) » incompris |

Dans les trois variantes, c'est le texte de la ligne qui alerte, pas l'anneau.

### Verdict par critère

| Critère | A | B | C |
|---|---|---|---|
| Lisibilité à petite taille | Échec | Moyen | L'anneau est illisible, sans enjeu |
| Compréhension sans légende | Échec | Coche et croix seulement | Bonne |
| Surcharge | Trois satellites autour de 24 px | Une dizaine de variables dans 32 px | Déplacée vers la droite |
| Niveaux de gris | Échec | Le critique pâlit, la lettre ancienne devient la plus noire | Bon |
| Cohérence avec l'existant | Faible | Rupture | Forte |
| 200 lignes | Mer de ronds vides | Mer de coches | La plus calme |

### Problèmes bloquants

1. **Saillance inversée.** Plus un message a avancé, plus son anneau pèse. Un critique tout juste reçu (1 segment
   sur 4) est plus pâle qu'un résultat presque clos (3 sur 4). L'anneau seul attire l'œil au mauvais endroit.
2. **Critique non affecté presque invisible.** L'état le plus dangereux était porté par le signe le plus faible.
3. **Retard aveugle à la gravité.** Avec des seuils en jours, un potassium à 6,1 non acquitté depuis 24 heures n'a
   qu'un cerne et n'est « en retard » qu'au septième jour.
4. **« Antérieur au suivi » a le signe de « rien à faire ».** Une anomalie ancienne jamais acquittée paraît sans
   objet.
5. **Variante A : un message traité ressemble à une case non cochée.**

### Problèmes importants

6. Le rouge servait aussi au non-distribué, contre la règle « couleur = gravité clinique ».
7. La fermeture effaçait l'anomalie : la ligne traitée ne montrait plus qu'une coche.
8. « Marquer comme résolu » est le bouton principal, même sur un critique à l'étape 1.
9. Le détail contredisait la liste sur le même message (« à vous » contre « personne »).
10. Envoyé : l'étape « lu » dépend d'un accusé facultatif, donc un trou permanent sur la plupart des envois.
11. Le contraste suffisant était une option. Il doit être le réglage par défaut.

### Problèmes mineurs

12. Cinq cases d'affichage : deux personnes du même cabinet ne verront plus le même signe.
13. « Cerne » et « tiers » sont du jargon dans l'interface.

### Tuile et détail

- **Tuile** : seul « en retard » est actionnable. Les groupes se recouvraient sans le dire (44 pour « 36 »). Trois
  lignes doublent les tuiles « À traiter », « Pour moi » et « Bio à acquitter ». Le seul apport propre est « Non
  affectées ». Proposition du relecteur : ajouter « dont N en retard » aux tuiles existantes.
- **Détail** : les étapes nommées et datées sont « la meilleure pièce du dossier », et le bon endroit pour apprendre
  l'anneau. Reproches : cinq boutons pour quatre segments sans correspondance visible, puces d'apparence cliquable.

### Non vérifiable sur capture

Animations, infobulles, lecteur d'écran, rendu sur un écran de densité 1, mode sombre, cibles tactiles.

## 4. Ce que j'en retiens

**Accepté et corrigé dans les maquettes (variante D)**

| Remarque | Correction |
|---|---|
| 1 Saillance inversée | L'urgence passe par le texte : ⚠ n, « Non affecté », J+N ou H+N. L'anneau ne porte que l'avancement et la couleur de gravité |
| 2 Critique non affecté | « Non affecté » écrit en toutes lettres, anneau au centre vide |
| 3 Retard et gravité | Seuils en heures pour une valeur critique : 4 h, 24 h, 72 h (décision 16) |
| 5 Traité = case vide | Coche |
| 6 Rouge du non-distribué | Croix, teinte neutre, « Non distribué » écrit |
| 7 Anomalie effacée | La pastille ⚠ n reste, atténuée, sur une ligne traitée |
| 9 Détail et liste | Même état dans les deux |
| 11 Contraste | Étapes restantes en traits contrastés par défaut |
| 13 Jargon | « Seuil », « en retard », « Attente patient » |
| Tuile | Les groupes se somment (12 + 9 + 15 = 36) ; « Non affectées » et « Pour moi » sont à part ; l'alternative « enrichir les tuiles existantes » est dessinée à côté |
| Détail | Boutons rangés par étape ; puces rondes |

**Tranché par le product owner le 2026-11-27**

- **Initiales dans l'anneau.** Quand un message est « à traiter par » quelqu'un, ses initiales sont au centre de
  l'anneau, et la pastille d'initiales disparaît de la ligne et du détail. La revue avait relevé qu'un rond à gauche
  portant des lettres peut se lire « expéditeur » (« CD » à côté de « Dr Camille ARNAUD »). Ce risque reste à
  mesurer : c'est l'épreuve 2 du § 5. L'infobulle (« À traiter par Cyril DELEGUE ») et la légende le couvrent.

**À trancher par le product owner**

- **4 Antérieur au suivi.** La règle vient de task-466 : l'historique ne réclame rien. La remarque porte sur le signe,
  pas sur la règle. Proposition : aucun signe de boucle pour l'historique, et la mention « Antérieur au suivi »
  existante dans le détail.
- **8 « Marquer comme résolu ».** Chaque action passe déjà par une fenêtre de confirmation. Rien à changer, sauf avis
  contraire.
- **10 Envoyé.** Rejoint la décision 9 : hors première version.
- **12 Cases d'affichage.** La demande en veut une par élément. Le relecteur conseille « tout ou rien ». À trancher.

**Ce que la revue retire de la demande**

La variante D abandonne quatre codes de la grammaire demandée : la pointe, le sens de rotation, la balle et les
cernes. Elle garde les initiales dans l'anneau. Les quatre questions gardent une réponse, mais deux passent de la forme au texte :

| Question | Demande | Variante D |
|---|---|---|
| Où en est-on ? | Segments | Segments |
| Dans quel sens ? | Pointe et rotation | Le dossier et le libellé « Envoyé » |
| À qui le tour ? | Balle | Initiales dans l'anneau, « Non affecté », « Attente patient » |
| Depuis combien de temps ? | Cernes | J+N, plein au dernier seuil |

C'est un écart net avec l'intention d'origine. Les variantes A et B restent dans les maquettes pour que le choix se
fasse sur pièces.

## 5. Recommandation

1. Retenir la **variante D** pour le premier lot.
2. Avant de coder, la confronter à **B** et à l'écran actuel avec trois à cinq médecins, sur trois épreuves :
   - **Priorité sans légende** : douze lignes, cinq secondes, « lesquelles ouvrez-vous ? ». Le potassium, la lettre de
     quinze jours et le non-distribué sortent-ils dans les trois premières ?
   - **Fausse réassurance** : que croient-ils traité ? Voient-ils le critique sans propriétaire ?
   - **Retard** : cernes contre J+N, sur un écran ordinaire, un téléphone en plein jour et une simulation de
     daltonisme.
3. Garder les cernes comme piste pour un lot ultérieur si l'épreuve 3 les sauve.

## 6. Scénarios de validation

Les quatre scénarios sont déroulés étape par étape dans les maquettes, section 7, dans la variante choisie.

| Scénario | Ce qu'on voit | Ce qu'il révèle |
|---|---|---|
| 20 biologies dans la journée, dont 3 avec anomalie | 3 anneaux colorés à quatre étapes, 17 neutres à trois étapes. « Traiter les résultats sans anomalie » ferme les 17. À J+3, une seule boucle reste ouverte, en attente du patient et en retard | La biologie sans anomalie suit l'anneau du courrier (décision 12). Le retard d'un critique se compte en heures (décision 16) |
| Courrier d'un confrère affecté à la secrétaire | Non affecté, puis lu, puis « CD » chez le médecin et sa propre pastille pleine chez Cyril, puis J+3, puis coche | Le même message ne se dessine pas pareil chez deux personnes. Le médecin voit que sa délégation traîne |
| Envoi sans réponse depuis 10 jours | Envoyé, distribué, lu, « Attente réponse », J+10, puis fermé | Dépend entièrement de la décision 9. Les rapports ne sont lus aujourd'hui qu'à l'ouverture d'une conversation |
| Accusé de lecture | L'accusé remplit l'étape « lu » de l'envoi. Dans la Boîte de réception, il n'a pas de boucle | Règle existante : un accusé n'est jamais un message |
