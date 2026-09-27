# todo-task-347.md — Étape `/e2e` bloquante dans la chaîne autonome, et un scénario e2e par parcours touché

**Repos**: forge *(plan de contrôle `HealthPlatform.Forge` — racine du workspace, hors table des repos de code)*
**Dependencies**: done-task-345 (voie mobile) ; la voie Angular s'active à la livraison de la task-346
**Epic**: E018
**Priorité**: **1** — c'est cette étape qui fait des suites 345/346 un **filet de non-régression**, et non un outil de plus.

> **Mode d'exécution.** Le plan de contrôle n'est pas un repo de code de la table : `/start` n'y crée
> pas de branche et `/develop` ne le prend pas en charge. Cette task est implémentée **dans une
> session Claude à la demande de l'humain**. L'humain **relit le diff avant le push** sur `develop`
> (règle 5 : le plan de contrôle se pousse sans PR). Elle modifie la chaîne elle-même, d'où cette
> relecture explicite.

## Objective

Insérer dans la chaîne autonome une étape **`/e2e {task-id}`**, **bloquante**, placée entre
`/verify-visual` et `/review`. Elle rejoue les suites headless des tasks 345 (mobile) et 346
(Angular) contre le backend `e2e`, vérifie leur **parité avec le catalogue de scénarios** (`Api/Mail/e2e/scenarios.yml`), et **arrête la chaîne si un parcours régresse ou si un client décroche du catalogue**.

Elle impose aussi une **clause de DOD** : toute US qui crée ou modifie un parcours médecin sur
`client-mobile` ou `client-angular` ajoute ou met à jour son scénario e2e. Sans cette clause, le filet
vieillirait comme la suite `/qa` depuis juillet.

```
/start → /develop → /sonar → /lint-angular → /lint-mobile → /verify-visual → /e2e → /review → /tech-writer
```

### Règles de l'étape `/e2e`

1. **Déclenchement par voie.** Une régression de parcours peut venir du backend autant que du client.
   - **Voie mobile** : jouée si la task a touché `api-mail`, `client-mobile` ou `dtos-mss`.
   - **Voie Angular** : jouée si la task a touché `api-mail`, `client-angular` ou `dtos-mss`. **Tant
     que la suite de la task-346 n'existe pas**, elle est sautée avec la mention explicite « suite
     Angular non livrée (task-346) », et jamais en silence.
   - **Skip propre** si aucun de ces repos n'est touché, **mesuré** (`step.sh end --status skipped`).
2. **Code testé.** Chaque voie tourne sur la **branche de la task** (`feat/*` pour api-mail et
   mobile ; branche courante pour Angular, qui reste en mode code-only, sans aucune opération git).
   Elle joue **après** tous les fixes qualité, pour que `/review` valide exactement le code testé.
3. **Bloquante, sans exemption.** Un test rouge après `retries: 1` → `questions/{task-id}.md` (tests
   en échec, extrait d'erreur, chemins des traces Playwright, sans aucune donnée de santé), task
   laissée dans son état, **chaîne arrêtée**. C'est un fail-fast au sens de la règle 13.
   - **Aucune exemption « flaky pré-existant »** : un test rouge sur `develop` bloque aussi, parce
     qu'un filet troué ne protège plus rien.
   - La seule échappatoire est la **quarantaine**, que **seul l'humain** pose : une étiquette sur le
     test, qui cite la task de correction. `/e2e` liste les tests en quarantaine dans son log à chaque
     run.
4. **Échec d'outillage = bloquant aussi** (Docker absent, AppHost qui ne démarre pas, seed non
   vérifié). La non-régression n'est alors pas prouvée. Le `questions/` distingue explicitement
   « outillage » de « régression ».
5. **Flaky = non bloquant mais visible.** Un test vert au second essai est consigné dans le
   `## E2E log`, recopié dans la PR et dans le rapport de fin de cycle.
6. **Log et restitution.** Section `## E2E log` du task file : voie par voie, les tests passés,
   échoués, flaky et en quarantaine, avec la durée. `/review` la recopie dans le body des PRs, comme
   la table `/verify-visual`.
7. **Double verrou.** `/review` refuse d'ouvrir une PR si le `## E2E log` est absent ou rouge, alors
   que la task touche une des voies.
8. **Mesure.** Chaque voie est enveloppée par `Tools/timing/measure.sh` avec un nouveau kind `e2e`,
   ajouté au vocabulaire de `Tools/timing/README.md`.
9. **Démontage garanti.** L'étape ne rend jamais la main avec un backend `e2e` debout, même après un
   échec.
10. **Chaînage.** `/verify-visual` enchaîne sur `/e2e` via l'outil `Skill`, et `/e2e` sur `/review`,
    sans rapport intermédiaire (règle 13).
11. **Parité bloquante.** Après les suites, `/e2e` lance le contrôle de parité de la task-345 : le
    catalogue `Api/Mail/e2e/scenarios.yml` est lu sur la branche de la task si api-mail est touché,
    sinon sur `origin/develop`. Il le confronte aux rapports exécutés de **chaque** client.
    - **Le contrôle tourne dès qu'une voie tourne**, y compris sur le client que la task ne touche
      pas. C'est ce qui attrape « comportement changé sur le mobile, Angular resté à l'ancienne
      version ».
    - **Tout écart bloque**, comme un test rouge (règle 3) : scénario `requis` manquant, test sans
      identifiant ou inconnu du catalogue, version périmée.
    - **Deux sorties légitimes**, qui sont des décisions de l'humain :
      - la task ajoute le client manquant à ses `**Repos**` et met son test à jour ;
      - une **divergence temporaire** est déclarée dans le catalogue, sur le scénario, pour le client
        concerné, avec une raison et la task qui la résorbera. `/e2e` liste les divergences ouvertes à
        chaque run.
    - **Voie Angular pas encore livrée** (task-346) : la colonne `angular` est reportée « non
      contrôlée (task-346) », jamais « verte ».
12. **Matrice de parité** : scénario × client, avec version, résultat, mode et divergences. Elle est
    placée dans le `## E2E log`, recopiée par `/review` dans le body des PRs, et reprise par
    `/tech-writer` dans la doc de l'EPIC E018.

### Clause de DOD — un parcours touché, un scénario catalogué et implémenté partout où il est requis

- **`/po`** ajoute systématiquement, à toute US qui crée ou modifie un parcours médecin mobile ou
  Angular, la ligne de DOD :
  `- [ ] Scénario E2E-{…} ajouté / versionné dans Api/Mail/e2e/scenarios.yml, et implémenté dans chaque client où il est requis`.
  - `/po` décide aussi **dès la rédaction** de la colonne `clients` du scénario. Si un client est
    `requis`, il figure dans les `**Repos**` de l'US, avec `api-mail` pour le catalogue.
  - Un comportement modifié sur un seul client est un **arbitrage explicite** (divergence
    temporaire), jamais un oubli.
- **`/develop`** écrit ou versionne l'entrée du catalogue **avant** les tests, puis les tests **avec**
  la fonctionnalité, dans chaque suite concernée.
- **`/e2e`** signale dans son log les écrans ou pages modifiés par la task **sans** spec e2e modifié.
  C'est un avertissement, pas un blocage : c'est la ligne de DOD, vérifiée par `/review`, qui bloque.
- **Règle 1c de CLAUDE.md** complétée en conséquence.

### Fichiers du plan de contrôle concernés

- **Nouveaux** : `.claude/commands/e2e.md`, `agents/e2e.md`.
- **CLAUDE.md** : schéma du cycle, table ownership, règle 13, table Commands, règle 1c et section
  « Sonar + Lint… — étapes standard ».
- **Hand-offs et commandes** : `agents/verify-visual.md` et `.claude/commands/verify-visual.md`
  (hand-off → `/e2e`) ; `.claude/commands/review.md` (lecture du `## E2E log`, double verrou,
  recopie en PR) ; `.claude/commands/forge.md` et `agents/orchestrator.md` (ordre de la chaîne).
- **`agents/po.md`** : clause de DOD et colonne `clients` du catalogue dans le template.
- **`agents/develop.md`** : l'entrée du catalogue s'écrit avant les tests e2e.
- **`agents/technical-writer.md`** : reprise de la matrice de parité dans la doc de l'EPIC E018.
- **`agents/qa.md`** : la règle « never bypass auth » est **précisée** — `/qa` reste le parcours au
  vrai login PSC, et le bypass n'est autorisé **que** dans le profil headless `e2e` de `/e2e`.
- **`Tools/timing/README.md`** : kind `e2e`.

### Hors périmètre

- L'exécution des suites en CI GitHub ou TFS.
- La conversion des Manual Test Plans archivés en scénarios. C'est le rattrapage, en US de suivi.

## Definition of Done

- [ ] `.claude/commands/e2e.md` et `agents/e2e.md` créés, avec règles 1 à 12, format du `## E2E log` et de la matrice de parité
- [ ] CLAUDE.md : `/e2e` présent dans le schéma du cycle, la table ownership, la règle 13 et la table Commands, et règle 1c complétée — `grep -n "verify-visual → /review"` ne renvoie plus rien dans CLAUDE.md ni dans `.claude/commands/`
- [ ] Hand-off `/verify-visual` → `/e2e` → `/review` écrit comme **ordre d'appel via `Skill`** (pas en prose)
- [ ] `/review` : recopie du `## E2E log` en PR et refus si absent ou rouge sur une voie concernée
- [ ] `agents/po.md` : ligne de DOD e2e dans le template et dans la checklist
- [ ] `agents/qa.md` : règle bypass précisée, sans contradiction avec `/e2e`
- [ ] Kind `e2e` documenté et accepté par `Tools/timing/measure.sh`
- [ ] **Répétition sur une task réelle** : un cycle complet sur une task touchant `client-mobile`, avec `/e2e` vert, `## E2E log` dans le task file et dans la PR, timing `e2e` au journal
- [ ] **Preuve du blocage** : une régression volontaire sur une branche de test fait arrêter la chaîne à `/e2e`, avec `questions/{task-id}.md` écrit, sans PR ouverte ; la régression est annulée ensuite
- [ ] **Preuve du skip** : une task qui ne touche aucune des voies saute `/e2e`, mesuré `skipped`
- [ ] Voie Angular sautée avec la mention « suite Angular non livrée (task-346) » tant que la suite est absente ; colonne `angular` de la matrice reportée « non contrôlée », jamais verte
- [ ] **Preuve du blocage de parité** : sur une branche jetable, monter la version d'un scénario `requis` sur les deux clients et ne mettre à jour que le test mobile → `/e2e` s'arrête sur « version périmée » côté Angular, `questions/{task-id}.md` écrit ; annulé ensuite
- [ ] Divergence temporaire : format documenté dans `agents/e2e.md`, listée à chaque run, et acceptée par le contrôle seulement si elle porte une raison et une task de résorption
- [ ] Matrice de parité recopiée dans la PR (`/review`) et dans la doc EPIC E018 (`agents/technical-writer.md`)
- [ ] Diff relu par l'humain avant push sur `develop` du plan de contrôle

## Manual Test Plan

1. Lire le diff du plan de contrôle : chaîne, hand-offs, règles de `/e2e`.
2. Prendre une petite task mobile du backlog et lancer `/start {task-id}`. La chaîne doit passer par
   `/e2e` après `/verify-visual`, sans s'arrêter entre les deux.
3. Vérifier dans le task file : `## E2E log` renseigné, section `## Timings` avec une ligne `e2e`.
   Dans la PR : la table e2e.
4. Sur une branche jetable, casser le filtre « Non lus » du mobile, puis lancer `/e2e {task-id}` à la
   main. Attendu : chaîne arrêtée, `questions/{task-id}.md` qui nomme le test en échec, aucune PR.
5. Lancer le cycle d'une task purement backend sans effet de parcours (ou `/e2e` seul sur une task ne
   touchant aucune voie) : skip mesuré.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — outillage de la forge
- **Vague Ségur** : hors Ségur
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : inchangée en production. Le bypass reste cantonné au profil `e2e` (task-345), et `/qa` conserve le vrai login PSC.
- **Habilitations** : non applicable
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : non applicable — les `questions/` et logs e2e ne contiennent aucune donnée de santé (données synthétiques, extraits nettoyés)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — poste de développement
- **AIPD / impact RGPD** : inchangé
