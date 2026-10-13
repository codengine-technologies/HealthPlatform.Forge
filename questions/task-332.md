# questions/task-332.md — `/e2e` bloque sur un écart de **parité** Angular, hérité de task-340

**Étape** : `/e2e` (chaîne autonome, après `/develop`, `/sonar`, `/lint-*`)
**Nature du blocage** : **PARITÉ**. Ce n'est ni une régression ni une panne d'outillage.
**Task** : laissée en `wip-task-332.md`. La branche api-mail `fix/task-332-bus-messages-without-secrets`
est poussée, verte, et nettoyée par Sonar. Aucune PR n'est ouverte.

## Ce que la porte rend

Porte `gate` : code 1, **3 motifs bloquants**, tous de parité côté Angular :

- `MissingRequired` [angular] **E2E-RECEIPT-001** « Demander un accusé de lecture à l'envoi »
- `MissingRequired` [angular] **E2E-RECEIPT-002** « Envoyer l'accusé de lecture d'un message reçu, une seule fois »
- `MissingRequired` [angular] **E2E-RECEIPT-003** « Refuser l'accusé de lecture d'un message reçu »

Tous les tests joués sont verts : 34 sur la voie mobile, 35 sur la voie Angular, dont E2E-COMPOSE-002, en
quarantaine et vert. La matrice complète est dans le `## E2E log` de la task.

## Pourquoi ce n'est pas un défaut de task-332

- task-332 ne touche **qu'api-mail** : le contrat des messages du bus et le consommateur. Aucun écran,
  aucune suite e2e, aucun scénario du catalogue.
- Les trois scénarios viennent de **task-340** (`origine: task-340`, `angular: requis`). Son Develop log
  (`tasks/archived/archived-task-340.md`) indique que les tests Angular ont été écrits **en code-only, non
  commités**, sur `feature/nova-rewriting-mss-weda-integration`, « à commiter sur TFS avant le merge de la
  PR api-mail ».
- Aujourd'hui, sur cette même branche (HEAD `00f0e37c`, « task 367 »), l'arbre Angular est **propre** et
  ces fichiers n'y sont plus :
  - `libs/mss/src/core/utils/read-receipt.util.ts` est absent ;
  - aucun `E2E-RECEIPT` dans `e2e/mss-e2e/specs/`.

  Le travail Angular de task-340 n'est donc pas dans le checkout qui a été rejoué : committé ailleurs,
  remisé, ou perdu. La forge ne fait aucune opération git sur `client-angular`, elle ne peut pas trancher.
- Toute task qui touche api-mail rencontrera ce même rouge tant que le point n'est pas résolu, puisque
  la voie Angular se joue dès qu'api-mail bouge.

## Décision attendue de l'humain : une des deux sorties légitimes

1. **Remettre les tests Angular de task-340 dans le checkout** (recommandé), si ce travail existe encore :
   commit TFS sur une autre branche, `git stash list`, ou poste de travail. Les fichiers listés dans le
   Develop log de task-340 sont :
   - `core/models/{audit.model.ts, audit.model.spec.ts, mail.model.ts}` ;
   - `core/services/mss-api.service.ts` ;
   - `core/utils/read-receipt.util.ts` et sa spec ;
   - `features/mail/components/mail-detail/{.ts,.html,.scss}` ;
   - `mail-detail.read-receipt.spec.ts` ;
   - `e2e/mss-e2e/specs/functional.e2e.ts` ;
   - `e2e/mss-e2e/support/e2e-backend.ts`.

   Puis relancer `/e2e task-332`, qui rejouera la voie Angular et enchaînera `/review`.
2. **Déclarer une divergence temporaire** au catalogue pour ces trois scénarios, côté `angular`, avec une
   raison et une task de résorption au format `task-NNN` :
   ```yaml
       divergences:
         angular:
           raison: le travail Angular de task-340 (accusés de lecture) n'est pas encore sur la branche weda2
           tache: task-NNN
   ```
   La forge ne pose jamais de divergence. Si vous la posez, elle sera committée sur la branche api-mail de
   task-332 (ou sur `develop`), puis `/e2e task-332` sera relancé.

## État des repos

| Repo | État |
|---|---|
| api-mail | `fix/task-332-bus-messages-without-secrets` @ `3e9d61a9`, poussée ; 6 568 tests verts ; Sonar : la seule issue de la task est corrigée |
| client-mobile | `develop`, non touché, aligné sur `origin/develop` |
| client-angular | `feature/nova-rewriting-mss-weda-integration`, propre, non touché par la forge |
| plan de contrôle | `tasks/wip-task-332.md` (Develop, Sonar et E2E logs), `conventions/csharp.md` (S125 → 17, CA1859 → 9), non committés |
