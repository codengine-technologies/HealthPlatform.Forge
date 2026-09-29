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

## Branches
- `forge` (plan de contrôle, racine du workspace) : **aucune branche**. La modification se fait sur `develop`, dans la session Claude, et le diff est **relu par l'humain avant le push** (mode d'exécution de la task, règle 5).
- Aucun repo de code n'est touché par cette task.

## Timings

*(généré par `tools/timing/report.sh --task task-347 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 37 s | — | — | — | plan de contrôle, pas de branche (diff relu avant push) |
| /develop | ok | 4 min 27 s | 2 (8.1 s) | 2 (4 min 18 s) | — | api-mail 2B/2T, reprise après review : porte qui valide ses entrées |
| /sonar | ok | 5 min 47 s | 2 (55 s) | 10 (9 min 11 s) | 4 (1 min 14 s) | api-mail 2B/10T, re-analyse : QG OK, 0 finding branche |
| /lint-angular | skipped | 0.4 s | — | — | — | repo non touché |
| /lint-mobile | skipped | 0.4 s | — | — | — | repo non touché |
| /e2e | ok | 6 min 47 s | — | — | — | e2e ×6 (11 min 59 s), 2 voies vertes, 1 flaky angular FOLDER-001 (registre) |
| /review | ok | — | 1 (4.7 s) | 1 (2 min 16 s) | — | api-mail 1B/1T, APPROVED (2e passage), PR api-mail #262; no start marker |
| /tech-writer | ok | 1 min 21 s | — | — | — | — |
| /merge | ok | 4 min 53 s | — | — | — | — |
| **Total cycle** | | **23 min 56 s** | **5 (1 min 07 s)** | **13 (15 min 46 s)** | **4 (1 min 14 s)** | |

## Develop log

- **Périmètre étendu à api-mail** (arbitrage humain du 2026-09-29, « ajouter api-mail à 347 ») : la DOD exige un contrôle de parité capable de lire un listing, d'accepter une divergence déclarée et de gérer la quarantaine. Branche `feat/task-347-etape-e2e-bloquante`, commit `e1d67c86` (poussé, PR à ouvrir par `/review`).
  - Porte `gate` : un seul verdict pour `/e2e`, et le corps du `## E2E log`.
    - Bloque sur tout écart de parité, tout test rouge hors quarantaine, et une quarantaine sans task de correction.
    - Liste sans bloquer les flaky, les quarantaines et les divergences.
  - Parité : `--listed client=listing` (`playwright test --list`) pour le client non touché : identifiants et versions contrôlés sans rejouer sa suite (📋 listé).
  - Catalogue : `divergences:` par scénario et par client. Raison et `task-NNN` obligatoires, client requis seulement. Le contrôle tolère alors une version périmée ou un test absent pour ce client, et liste la divergence.
  - Rapport Playwright : tag `@quarantaine` et annotation `quarantaine` (task de correction), posés par l'humain seul.
  - 16 tests, rouge vérifié par mutation (3 tests rouges quand les rouges ne bloquent plus et que le listing est ignoré). api-mail : **5 865 verts** (16 ignorés préexistants).
- **Plan de contrôle** (non poussé : diff à relire par l'humain) :
  - nouveaux : `.claude/commands/e2e.md`, `agents/e2e.md` (règles 1 à 12, format du `## E2E log` et de la matrice, quarantaine, divergence) ;
  - `CLAUDE.md` : schéma du cycle, table ownership, section « `/e2e` — le filet fonctionnel, bloquant », règle 1c (clause de DOD e2e), table Commands, et `/verify-visual` décrit « entre `/lint-mobile` et `/e2e` » ;
  - hand-offs : `/verify-visual` appelle `Skill(e2e, …)` (commande et playbook), `/e2e` appelle `Skill(review, …)`, et `/develop` route vers `/e2e` quand aucun des trois repos n'est touché (commande et playbook) ;
  - chaîne mise à jour dans `.claude/commands/{develop,start,forge}.md` et `agents/{develop,merge,stitch-design,verify-visual,orchestrator}.md`. `forge.md` avait perdu `/verify-visual` : rétabli ;
  - `/review` : étape 4b (double verrou : refus si le `## E2E log` est absent ou rouge sur une voie concernée), recopie `## Parcours e2e` dans chaque PR, ligne au rapport final, règle ;
  - `agents/po.md` : clause de DOD e2e, colonne `clients`, divergence comme arbitrage humain, ligne dans le template et dans les règles ;
  - `agents/develop.md` : Step 6b, le catalogue s'écrit **avant** les tests e2e ;
  - `agents/technical-writer.md` : section « Parcours vérifiés automatiquement » de la doc E018, reprise du dernier `## E2E log` ;
  - `agents/qa.md` : « never bypass auth » précisé (le bypass est autorisé dans le seul profil headless `e2e` de `/e2e`, et `/qa` reste le parcours au vrai login) ;
  - `Tools/timing/{measure.sh,README.md}` : kind `e2e` (accepté tel quel par `measure.sh`, affiché dans « Détail » et `--by-kind`).
  - `grep -n "verify-visual → /review"` dans CLAUDE.md et `.claude/commands/` : **aucun résultat**.
- **Preuves**, sur des tasks jetables 990 à 992, supprimées ensuite. Les événements restent dans `metrics/timings.jsonl` :
  - **Skip** (task-990, Repos `devops`) : `/e2e` saute, mesuré `skipped` (« aucune voie touchée »).
  - **Blocage sur régression** (task-991, branche mobile locale où le filtre « Non lus » renvoie tout) :
    - voie mobile rouge, **E2E-INBOX-001** (« filtre Non lus : les lignes affichées respectent le filtre »), 21 verts ;
    - Angular listé, parité verte ;
    - la porte sort en 1, `questions/task-991.md` est écrit, la chaîne s'arrête, aucune PR ;
    - régression annulée, démontage complet.
  - **Blocage sur parité** (task-992, E2E-INBOX-001 passé en v2 au catalogue, seul le test mobile suit) :
    - les deux voies ont joué (api-mail touché) : mobile 22/22 et Angular 22/22 ;
    - **la porte bloque sur `[angular] StaleVersion`** (v1 contre v2), `questions/task-992.md` est écrit avec les deux sorties légitimes, aucune PR ;
    - branches jetables supprimées, démontage complet.
- **Non fait / reporté** :
  - **Répétition sur une task réelle** (cycle complet mobile, `/e2e` vert, `## E2E log` dans la PR) : à jouer sur la prochaine task mobile du backlog, une fois ce plan de contrôle poussé et la PR api-mail mergée. D'ici là, `develop` d'api-mail n'a pas la porte `gate`.
  - « Voie Angular sautée avec la mention task-346 » : la règle est écrite, mais la suite existe désormais, donc le cas n'est plus reproductible sur ce poste.
- **Décision humaine du 2026-09-29 : `/verify-visual` sort de la chaîne autonome.** Constat :
  - sur 66 tasks portant un `## Visual verify log`, l'étape n'a **jamais** bloqué ;
  - elle saute depuis environ task-274, faute de `Tools/visual-verify/` sur ce poste ;
  - son seul cas bloquant (écran blanc, crash de navigation) est couvert par `/e2e`, contre le vrai backend.
- La chaîne devient `/lint-mobile → /e2e → /review` : `/lint-mobile` appelle `Skill(e2e, …)`, et le schéma est retiré de tous les fichiers de chaîne. `/verify-visual` reste une commande **à la demande** (captures, comparaison Stitch, galerie de l'EPIC) et n'enchaîne plus sur rien.
  - Le DOD de la task parle du hand-off « `/verify-visual` → `/e2e` » ; la décision le remplace par « `/lint-mobile` → `/e2e` », avec le même principe : un ordre d'appel via `Skill`.
- **Demande humaine du 2026-09-29 : règle d'or « la forge s'améliore toujours »**, gravée en tête de CLAUDE.md.
  - Tout défaut laisse une prévention, qui vit dans un endroit défini.
  - Une récidive signale un fichier non lu.
  - `/review` rend compte de chaque leçon, ou écrit « aucune leçon ».
  - Mesurer avant d'améliorer, et retirer ce qui ne sert plus.
- **Boucle d'amélioration du filet e2e** :
  - `conventions/e2e.md` (nouveau) : 9 conventions tirées des tasks 345 à 347 (état optimiste, absence pendant le chargement, `isVisible` sans attente, jamais de skip en headless, fenêtre d'annulation, sélecteur ambigu, geste caché, session non persistée, preuve par mutation), plus les registres des flaky, des quarantaines et des trous du filet ;
  - `/e2e` Step 7b : il tient les registres et signale le flaky récurrent (3e occurrence), la quarantaine de plus de 14 jours, la divergence à retirer et la voie qui dérive en durée ;
  - `/develop` Step 6b : il lit `conventions/e2e.md` d'abord ; preuve par mutation obligatoire ; trou du filet prouvé rouge sur le bug non corrigé ;
  - `/review` : un piège récurrent trouvé en revue laisse une prévention, et le rapport porte une section « Amélioration continue » ;
  - `/po` : ligne de DOD « trou du filet » pour tout bug visible passé au travers.
- Next step : **relecture du diff par l'humain** (mode d'exécution de la task), puis push du plan de contrôle, puis `/review task-347` pour la PR api-mail.

### Reprise après /review (2026-09-29, CHANGES REQUESTED)

- **3 bloquants corrigés** (`040862b6`) : la porte refuse de conclure sans rapport exécuté, elle refuse un « listing » qui contient un test joué, et la tolérance « test absent » d'une divergence est testée dans les deux sens (vérifiée rouge par mutation).
- **Suggestions appliquées** : quarantaine sans task bloquante aussi au listing ; divergence devenue inutile signalée « à retirer » ; divergence visible sur une case humaine ; `IsTaskId` partagé.
- **Règle d'or** : la leçon devient la consigne « porte-valide-ses-entrees » de `conventions/e2e.md`.
- api-mail : **5 872 verts** (16 ignorés préexistants).

## Sonar log

Mode A, serveur SonarQube 9.9.8, projet `healthplatform-api-mail`. 1 analyse complète : begin, build Release, 5 passes OpenCover, end.

- Phase 1 (lignes de task-347, uniquement l'outillage `tests/mss.mail.e2e` et ses tests) : ✓ **0 finding**. Quality Gate **OK**, new_coverage **98,3 %**.
- Phase 2 (legacy) : 0 itération. Les mêmes 10 findings structurels (S107, S3604) restent, acceptés en best-effort.
- Build et tests verts sous OpenCover : domain 190, application 3 267, infrastructure 665, api 1 100, integration 643 (+16 ignorés).

**Re-analyse après la reprise** (`040862b6`) : Quality Gate **OK**, 0 finding sur les fichiers de la branche, KPIs inchangés.

### KPIs qualité (baseline → final)

Baseline = dernière analyse, task-346 et develop (2026-09-29).

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 98,3 % | 98,3 % | ±0 pt |
| Bugs / Vulnerabilities / Hotspots | 0 / 0 / 0 | 0 / 0 / 0 | ±0 |
| Code smells | 10 | 10 | ±0 |
| Coverage (projet) | 98,2 % | 98,3 % | +0,1 pt |
| Duplication | 0,5 % | 0,5 % | ±0 pt |

## Lint log

- `/lint-angular` : skipped — client-angular non touché par task-347.
- `/lint-mobile` : skipped — client-mobile non touché par task-347.

## E2E log

Run après la reprise de review (`040862b6`), sur le code que `/review` valide.

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail touché | ✅ verte | 22 verts, 0 flaky, 0 rouge, 0 quarantaine | 2 min 57 s |
| angular | api-mail touché | ✅ verte | 21 verts, **1 flaky**, 0 rouge, 0 quarantaine | 2 min 48 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task (`feat/task-347-etape-e2e-bloquante`)
- Quarantaines : aucune — Divergences ouvertes : aucune
- **Flaky** : `[angular] E2E-FOLDER-001`. Au 1er essai, « le dossier INBOX est ouvert » a échoué au retour vers INBOX ; il est vert au 2e. **1re occurrence**, inscrite au registre de `conventions/e2e.md` (task de stabilisation à la 3e).
- Parcours touchés sans spec e2e modifié : aucun (aucun fichier client touché)
- Démontage : complet (ports libres, aucun conteneur e2e résiduel)

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**Flaky (vert au second essai, non bloquant)** (1) :

- [angular] « dossiers — naviguer vers Archive et Corbeille » (E2E-FOLDER-001)

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ⚠️ flaky | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 1 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 1 | headless | Créer puis supprimer un contact | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/262 — label `awaiting-human-merge` (porte `gate`).
- `forge` (plan de contrôle) : poussé sur `develop` après relecture humaine (`bad1a7a`, puis les suites de la revue). Pas de PR (règle 5).

## Code Review Summary

- Verdict : **APPROVED** au 2e passage (revue indépendante), le 2026-09-29.
- 1er passage, CHANGES REQUESTED, trois bloquants corrigés dans `040862b6` :
  - la porte rendait vert sans rapport exécuté ;
  - un vrai rapport passé en `--listed` masquait ses rouges ;
  - la tolérance « test absent » d'une divergence n'était pas testée.
- 2e passage : code approuvé. Un point du playbook est corrigé : la porte qui sort en 2 bloque, et un vieux log n'est jamais recopié.
- Validation : api-mail 5 872/5 872 ; Sonar QG OK, 0 finding sur la branche ; `/e2e` vert (mobile 22/22, Angular 21 + 1 flaky).

## Amélioration continue (règle d'or)

- Leçon de revue « une porte bloquante valide ses entrées » → consigne `porte-valide-ses-entrees` dans `conventions/e2e.md`.
- Flaky `[angular] E2E-FOLDER-001` (1re occurrence) → inscrit au registre des flaky de `conventions/e2e.md`. Task de stabilisation à la 3e occurrence.
- `/verify-visual` retiré de la chaîne, chiffres à l'appui (règle d'or, point 6).

## Merged

- 2026-09-29, `/merge task-347 --i-tested` (validation humaine attestée).
- `api-mail` #262 → squash `f8e3bef0` sur `develop`, CI « Build and Publish » verte. Branche `feat/task-347-etape-e2e-bloquante` supprimée (distant et local).
- Plan de contrôle : déjà sur `develop` (`bad1a7a`, `b44830c`, `991ca5a`).
- `client-angular` non touché par la task. Pas de branche staging, car la task ne vient pas d'un run `/forge`.
- Reste ouvert : la **répétition sur une task mobile réelle** (DOD). Elle sera jouée au prochain cycle qui touche `client-mobile` ; la porte `gate` est maintenant sur `develop`.
