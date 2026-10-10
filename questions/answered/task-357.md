> **Réponse du responsable produit (2026-10-10) : option 2, reporter.** La couverture e2e du
> parcours « Dossier Weda » passe dans task-360, dont le scénario E2E-WEDA-001 part désormais du
> panneau (DoD de task-360 élargie). La DoD de task-357 porte la ligne de report.
> `/review task-357` reprend.

# questions/task-357.md — `/review` : un parcours médecin sans scénario e2e

**Étape** : `/review task-357` (2026-10-10), revue de code, critère 5.6 (règles 1b et 1c, côté
frontend).
**Décision attendue de** : l'humain (PO). C'est un arbitrage de périmètre, voir les deux options.
**Tout le reste est vert** :
- build et tests client-angular : `npm ci`, `nx build weda2`, 11 projets ;
- `/e2e` : vert (angular 30 verts ; E2E-COMPOSE-002 en quarantaine, passé au 2e essai ; mobile
  listé ; parité verte) ;
- DoD cochée ;
- revue du code sans autre point bloquant.

## Le blocage

task-357 **crée un parcours du médecin** dans le client Angular : le panneau « Dossier Weda » sous
un message reçu, avec le dossier trouvé par INS ou des correspondances à vérifier, et le bouton
« Ouvrir le dossier ». Pour la forge, le test d'intégration d'un parcours médecin est **son scénario
e2e** (règle 1b, côté frontend ; règle 1c). Les 20 tests de composant du panneau sont nécessaires,
mais ils ne suffisent jamais seuls.

**La DoD de la task ne porte pas la ligne « Scénario E2E-… »**. C'est un **oubli de rédaction de la
task**, faite par la forge en mode PO le 2026-10-09. `/e2e` l'a d'ailleurs signalé (« parcours
touchés sans spec e2e modifié » : `mail-detail.component.html`, `weda-patient-panel.component.html`).

Pourquoi ce scénario n'existe pas encore : le panneau n'est rendu **qu'embarqué dans Weda**, avec le
port d'accès au dossier disponible. La suite e2e joue weda2 seul, sans hôte. Le **faux hôte de
test** (une page qui embarque weda2 et répond au pont) est prévu par **task-360**, avec le scénario
E2E-WEDA-001 qui part justement de ce panneau.

## Les deux sorties possibles (décision humaine)

1. **Couvrir le parcours dans task-357.** La forge ajoute :
   - le faux hôte de test ;
   - le scénario **E2E-WEDA-001** « Voir le dossier Weda du patient d'un document reçu et l'ouvrir »
     (angular `requis`, mobile `non-applicable — l'application mobile n'est pas embarquée dans
     Weda`) ;
   - l'activation de `weda_integration` dans le profil e2e d'api-mail.

   **Conséquence** : api-mail entre dans les `**Repos**` de 357 (branche `feat/task-357-…`), puis
   `/e2e` et `/review` sont rejoués. task-360 réutilise ensuite ce faux hôte, avec un scénario
   E2E-WEDA-002 pour le classement.
2. **Reporter explicitement la couverture à task-360** (arbitrage PO). Le scénario de task-360
   devient « voir le dossier Weda du patient puis classer le document », et couvre le panneau de
   357. La DoD de 357 reçoit une ligne qui dit ce report, et 357 est close sans scénario propre.

**Recommandation de la forge : 2.**
- Le panneau et le classement forment un **seul parcours** du médecin : il voit le dossier, puis
  il classe.
- Le faux hôte est déjà le livrable de task-360.
- 357 n'a aucune PR à merger côté forge : client-angular est en code-only, Weda hors forge. Le
  report ne laisse donc aucune plomberie nue sur `develop` (règle 11).

L'option 1 est plus stricte, et coûte environ une demi-journée de plus sur 357.

## Pour reprendre

- **Option 1** : relancer la forge sur 357 avec les ajouts listés, puis `/e2e task-357` et
  `/review task-357`.
- **Option 2** : la forge (mode PO) ajoute la ligne de report dans la DoD de 357 et élargit le
  scénario de task-360, puis `/review task-357`.
