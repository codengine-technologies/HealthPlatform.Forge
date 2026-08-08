# todo-task-240.md — Le premier poste de coût du parcours n'est attribuable à aucun de ses deux appels

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune
**Priorité**: **1** — **bloquante pour tout le reste du banc**. `read_list` pèse
46,3 % du temps serveur et rien ne dit lequel de ses deux appels le porte. Tant
que c'est vrai, aucune optimisation de ce chemin n'est décidable, aucune
certification 200 n'est explicable, et le passage à 500 est un NO-GO.

## Objective

Qu'on puisse répondre à « **quelle requête** fait attendre le médecin quand il
ouvre son inbox ? ». Aujourd'hui l'étape `read_list` du parcours agrège **deux
appels HTTP distincts** sous une seule étiquette `op`, si bien que son p95 de
4 781 ms ne désigne rien de précis.

C'est une US **d'instrument**, pas d'application : elle ne rend pas le produit
plus rapide, elle rend le prochain correctif décidable. La distinction est le
cœur du sujet — cette EPIC a déjà annulé une US applicative écrite sur une cause
supposée (task-222), et la règle qui en est sortie est explicite : « si le coût
d'une étape ne peut pas être attribué à l'un de ses appels, le premier finding
est le manque d'instrumentation, pas une optimisation devinée ».

## Le défaut — deux appels, une étiquette

`tests/loadtest-k6/scenarios/journey.js`, lignes 539-540 :

```js
const inboxTags = tagsFor('read_list');
account('read_list', api.getFolder(user, session, inboxTags));
account('read_list', getEmails(user, session, PAGE_UIDS, inboxTags));
```

Deux appels de nature très différente — l'ouverture du dossier (`GET
/Mail/folders/{foldername}`) et la lecture de la page d'en-têtes (`GET
.../emails/{ids}`) — partagent l'étiquette. Le rapport publie donc **un
percentile de mélange**.

## La mesure qui motive la US — campagne K=1 du 2026-08-08 (`journey-certif-n200-142630`)

| Signal | Valeur |
|---|---|
| Part de `read_list` dans le temps serveur | **46,3 %** (1ᵉʳ poste ; 21,8 % à la campagne précédente) |
| p95 client à 200 médecins | **4 781 ms** (cible 1 000) — **pire** que les 4 112 ms de la référence |
| Nombre d'appels agrégés sous l'étiquette | **2** |

**Ce que la mesure écarte déjà** — et qui doit rester écarté, pour ne pas
repartir sur ces pistes : attente de verrou `imap_session` (**5 ms** depuis
task-239), file d'acceptation Kestrel (`queued_connections = 0`), famine de
ThreadPool (file ≤ 29 pour un seuil de 100), CPU (1,05 à 1,31 cœur par réplica
sur 24 logiques). Le temps est bien **dans l'application**, sur l'un des deux
appels — le rapport voit des requêtes serveur jusqu'à 10 s sur `.../emails/{ids}`.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que c'est `getEmails`** parce que la route serveur y monte à
  10 s : le tableau « p95 client vs p95 serveur » publie un p95 **max** sur toute
  la campagne, transitoires compris — pas la contribution au palier 200.
- **Ne pas présumer qu'une seule étiquette de plus suffit.** Si les deux appels
  sont séquentiels dans la même étape, le médecin attend leur **somme** : il faut
  pouvoir lire à la fois le coût de chacun **et** le coût ressenti de l'étape.
  Décider explicitement comment les deux cohabitent dans le rapport.
- **Ne pas présumer que le défaut est propre à `read_list`.** Le même travers a
  déjà été signalé le 2026-08-04 sur l'arrivée dashboard (quatre appels, une
  étiquette). **Recenser** les étapes du parcours qui agrègent plusieurs appels
  et traiter la famille, pas le cas.
- **Ne pas casser la comparabilité inter-tirs.** `read_list` est une ligne de la
  grille SLO et de l'INDEX depuis des dizaines de tirs : l'étape doit continuer
  d'exister sous ce nom et avec la même sémantique, sinon toute la série
  historique devient incomparable.

## Definition of Done

- [ ] Recensement écrit des étapes du parcours qui agrègent plusieurs appels HTTP
      sous une étiquette (consigné même si `read_list` est la seule)
- [ ] Chaque appel de `read_list` porte sa propre étiquette, **sans supprimer**
      l'étape `read_list` ni changer sa sémantique (comparabilité historique)
- [ ] `report.py` publie le coût **par appel** pour les étapes concernées, en
      plus du coût de l'étape
- [ ] Auto-tests du harnais verts (`tests/loadtest-k6/selftest.sh`)
- [ ] Un test sur `report.py` prouve qu'une étape multi-appels est ventilée
      correctement (fixture dédiée)
- [ ] **Contre-épreuve au banc** : un tir `journey` court (100 médecins) suffit —
      le rapport doit **nommer** lequel des deux appels porte le coût de
      `read_list`, avec son chiffre. C'est le livrable : une phrase attribuable.
- [ ] Aucune donnée de santé dans les nouvelles étiquettes (pas de nom de
      dossier ni d'identifiant patient — cf. la fuite évitée par task-213 sur le
      nom de pièce jointe)

## Manual Test Plan

- Monter le banc : skill `loadtest-skill`
- Tir court : `journey`, 100 médecins, 10 min, latence `mssante`
- Ouvrir le rapport généré et vérifier qu'on peut répondre, **chiffre à
  l'appui**, à « lequel des deux appels de l'inbox coûte le plus ? »
- Vérifier que la ligne `read_list` existe toujours dans la grille SLO et dans
  `reports/INDEX.md`, avec la même signification qu'aux tirs précédents

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — outillage de mesure interne
- **Exigences DSR honorées** : aucune — la US ne touche pas au produit
- **INS** : non applicable — aucun traitement d'identité ; ⚠️ les étiquettes de
  métrique ne doivent porter **aucun** identifiant patient (cardinalité **et**
  confidentialité)
- **Authentification PS** : inchangée — le harnais forge déjà ses jetons
- **Habilitations** : non applicable
- **Interop CI-SIS** : non applicable
- **MSSanté** : non applicable — aucun échange modifié
- **Tracé PGSSI-S** : non applicable — métriques d'exploitation du banc, aucune
  donnée patient
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non applicable — banc local, données synthétiques
- **AIPD / impact RGPD** : inchangé

## Branches

- `api-mail` (pushed) : `feat/task-240-read-list-attribution` —
  https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-240-read-list-attribution
- `dtos-mss` (pushed, auto-inclus) : même nom de branche — **US de harnais**
  (`tests/loadtest-k6/`), aucun changement de contrat attendu ; la branche
  restera sans commit et sans PR.

> **Nature de la task** : le code touché vit dans `Api/Mail/tests/loadtest-k6/`
> (`scenarios/journey.js`, `report.py`) — **pas** dans le code applicatif.
> `/sonar`, `/lint-*` et `/verify-visual` skipperont donc proprement, et la
> contre-épreuve est un tir court de 100 médecins, pas une campagne complète.

## Simplify log

Passe qualité `/forge-simplify` du 2026-08-08 — harnais seul touché
(`tests/loadtest-k6/`) ; `dtos-mss` sans commit, aucun changement de contrat.

| Axe | Constat | Correction |
|---|---|---|
| Simplification | `tagsFor(op, call)` avait gagné un paramètre qu'**aucun appelant ne passait** : les six sites multi-appels contournaient la fonction et appelaient `stepTags` en direct, avec `op` répété deux fois par ligne. | `tagsFor(op)` retrouve sa signature d'origine ; un `stepTagger(op)` fige le palier une fois et rend un étiqueteur. Même sémantique de palier. |
| Réutilisation | La section du rapport **recalculait** la ventilation du palier le plus peuplé alors qu'elle venait de la calculer pour tous les paliers — double lecture des métriques, et deux chemins pouvant diverger. | Un seul calcul, indexé par palier. |
| Simplification | La parenthèse de coût de la phrase d'attribution était écrite deux fois, une par tournure. | Extraite. |
| Efficacité | Le jeu de tags de la ventilation était construit deux fois par appel. | Construit une fois. |
| Altitude | Rien à redire. | — |

**Le contrat inter-runtime suit déjà le patron maison**, découvert à la
relecture : `MULTI_CALL_STEPS` (JS) et `JOURNEY_MULTI_CALL_STEPS` (Python) ne
peuvent pas s'importer l'une l'autre, et le repo tient ce genre de contrat par
**commentaire directionnel + échec visible** — exactement comme
`ITERATION_SECONDS_ENV_PREFIX` entre `report.py` et `lib/vu-sizing.js`. Un
générateur ou un parseur JS-depuis-Python aurait été une **régression** par
rapport à la convention locale. Rien inventé.

**Non retenu délibérément** : factoriser la lecture `avg/med/p95/count` d'un
sélecteur (duplication réelle mais **préexistante**, et la refonte toucherait
quatre fonctions hors diff dont celles que les tests de comparabilité
verrouillent octet pour octet) ; fusionner les deux tables (voir ci-dessus).

Auto-tests du harnais verts avant et après : **203 Python + 57 node**. Aucun
rollback nécessaire, aucun comportement changé.

## Sonar log

`/sonar` — **skip propre** : cette US ne touche **aucun code applicatif**. Le
diff vit entièrement dans `Api/Mail/tests/loadtest-k6/` (JavaScript de harnais
k6 et Python de rapport), hors périmètre de l'analyse C# d'`api-mail`. La
qualité de ce diff est tenue par les auto-tests du harnais (`selftest.sh`), qui
sont son filet propre.

## Lint log

`/lint-angular` — **skip propre** : `client-angular` hors `**Repos**:`
(`**Single frontend**: true`), aucun code Angular produit.

## Lint mobile log

`/lint-mobile` — **skip propre** : `client-mobile` hors `**Repos**:`, et
`Client/Mobile/` n'est pas un dépôt git sur ce poste.

## Visual verify log

`/verify-visual` — **skip propre** : aucun écran `client-mobile` touché.
