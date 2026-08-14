# todo-task-262.md — Le tableau de bord est vert au SLO et consomme 23,5 % du serveur : le point aveugle que le verdict ne signalera jamais

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: **task-229** (`archived`) a déjà allégé ce geste — le décompte
du jour n'est plus redemandé intégralement au serveur de messagerie. Le coût
mesuré ici est **ce qui reste après** cette correction.
**Priorité**: **2** — deuxième poste de coût serveur du tir à 500, mais **aucune
attente pour le médecin** : c'est une US de capacité, pas de confort.

## Objective

Réduire ce que coûte au serveur l'arrivée d'un médecin sur son tableau de bord,
sans rien changer à ce qu'il y voit.

## Ce qui est établi — tir `journey-500-esc` du 2026-08-14

| Palier | p50 | p95 | Cible p50 / p95 | Verdict |
|---|---|---|---|---|
| 100 médecins | 6 ms | 556 ms | 300 / 1 500 | ✅ |
| 200 médecins | 7 ms | 537 ms | 300 / 1 500 | ✅ |
| 500 médecins | 10 ms | 552 ms | 300 / 1 500 | ✅ |

**Vert aux trois paliers, et plat.** Et pourtant :

| Traitement | Appels | Moy. | Total | **Part du temps serveur** |
|---|---|---|---|---|
| Envoi | 4 031 | 1 509 ms | 6 085 s | 25,1 % |
| **Arrivée dashboard** | **55 780** | **102 ms** | **5 705 s** | **23,5 %** |
| Ouvrir l'inbox | 27 854 | 100 ms | 2 779 s | 11,5 % |

**Le coût ne vient pas de la lenteur mais du nombre** : 55 780 appels au palier
500, soit **le traitement le plus appelé de tout le parcours** — environ quatre
par passage de médecin. À 102 ms l'unité, cela suffit à en faire le deuxième
consommateur du serveur.

**C'est exactement le point aveugle que la section « Axes d'amélioration »
existe pour attraper** : un traitement que le verdict SLO ne signalera jamais,
parce que le médecin ne l'attend pas. Le signal mécanique « vert au SLO mais gros
consommateur » l'a désigné de lui-même.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que les quatre appels sont réductibles à un.** Ils servent
  peut-être des écrans distincts, avec des fraîcheurs différentes. Établir **ce
  que chacun rapporte** avant de proposer de les fusionner.
- **Ne pas présumer que c'est encore le serveur de messagerie.** task-229 a déjà
  retiré cette dépendance ; le coût restant est probablement en base ou en
  construction de réponse — **à mesurer**, l'attribution par appel n'existe pas
  aujourd'hui (finding du 2026-08-04 : les quatre appels partagent un seul `op`).
- **Ne pas présumer qu'un cache est la réponse.** Un tableau de bord qui affiche
  des chiffres périmés est un défaut produit, pas une optimisation. Toute mise en
  cache doit énoncer sa **fraîcheur acceptable**, et c'est une décision produit.
- **Ne pas confondre ce lot avec la fiche patient** : `patient_dossier` est
  signalé séparément et ne pèse que 0,5 %.

## Ce que la US doit livrer

**Étape 1, obligatoire — rendre les quatre appels attribuables.** Aujourd'hui ils
partagent une seule opération dans le rapport : impossible de dire lequel des
quatre coûte. C'est le finding d'instrumentation du 2026-08-04, jamais traité.

**Étape 2 — réduire, une fois qu'on sait quoi.** Le levier n'est décidable
qu'après l'étape 1, et le task file **interdit de le choisir d'avance**.

## Definition of Done

- [ ] Build passe (0 erreur), tests passent (0 échec)
- [ ] Les appels de l'arrivée sur le tableau de bord sont **attribuables un par
      un** dans le rapport — plus un `op` unique pour quatre gestes
- [ ] Le rapport publie, pour chacun, **appels × durée moyenne** — la grandeur
      qui classe, pas le percentile
- [ ] **Ce que le médecin voit est inchangé** : mêmes compteurs, mêmes valeurs,
      même fraîcheur. Vérifié par test et au plan de test manuel
- [ ] Si une réduction est livrée : **contre-épreuve chiffrée** sur deux paliers,
      et la part du temps serveur du dashboard **baisse**
- [ ] Si aucune réduction n'est livrée : le **dire**, écrire pourquoi, et poser le
      seuil qui rouvrirait le sujet
- [ ] Toute mise en cache éventuelle **énonce sa fraîcheur** et la justifie côté
      produit

## Manual Test Plan

- Monter le banc, lancer un tir `journey` à deux paliers
- **Ce qu'il faut voir** dans « Axes d'amélioration » : les appels du tableau de
  bord **listés séparément**, chacun avec son total
- Ouvrir le tableau de bord depuis l'application : **compteurs identiques** à
  avant (messages du jour, non lus, dossiers), et mise à jour au même rythme
- Enchaîner plusieurs arrivées successives : les valeurs doivent rester justes,
  y compris après réception d'un nouveau message

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — performance / exploitation
- **Exigences DSR honorées** : aucune exigence nouvelle
- **INS** : les compteurs du tableau de bord sont des **agrégats** ; aucune
  étiquette de métrique ne doit porter d'identifiant ni de contenu
- **Interop CI-SIS** : sans objet
- **Habilitations** : ⚠️ toute mise en cache doit rester **cloisonnée par
  praticien** — un compteur partagé entre deux médecins serait une fuite, pas une
  optimisation
- **Authentification PS / Consentement** : inchangés
- **Tracé PGSSI-S** : inchangé
- **Hébergement HDS** : gain de capacité attendu, sans effet visible utilisateur
- **AIPD / impact RGPD** : inchangé

## Branches

- `api-mail` (pushed) : feat/task-262-dashboard-attribuable
- `dtos-mss` (pushed, auto-inclus) : aucune modification attendue

## Develop log (2026-08-15)

### Étape 1 — déjà livrée par task-240 : la prémisse de la US était périmée

Le finding cité (« les quatre appels partagent un seul `op` », 2026-08-04) a été
traité par **task-240** dès le 5 août. Le rapport du tir `journey-500-esc` du
2026-08-14 attribue déjà appel par appel, avec la grandeur qui classe
(total = appels × durée moyenne) :

> **Arrivée dashboard** (`dashboard`, palier 500) — le p95 de l'étape est porté
> par l'appel **`folder`** (826 ms de p95, 139 ms de p50, n=13945), qui porte
> **aussi** le temps serveur de l'étape (**3725,6 s, 65 %**).

Les DOD « attribuables un par un » et « appels × durée moyenne » sont donc
satisfaits **par l'existant** — rien à livrer côté rapport, et le vérifier était
la première chose à faire avant d'écrire du code.

### Le trou réel, découvert en instruisant l'attribution : côté serveur

- L'appel `folder` (65 % du coût de l'étape) correspond à la route
  `GET /folders/{name}` — **p95 serveur 726 ms** sur la fenêtre du palier 500 :
  le coût est bien dans l'application, pas dans le transport.
- Or sur cette même fenêtre, `mssante_mail_server_solicitations_total`
  (task-225) ne contient **aucune** opération `GetFolder*` : les 4
  allers-retours IMAP de la recherche de dossier (resolve, open, SEARCH, close)
  n'étaient enregistrés nulle part — `ImapFolderService` n'était pas branché sur
  le compteur. C'est l'angle mort exact que task-225 documentait : l'absence
  d'une opération ne prouve pas qu'elle ne sollicite pas le serveur.

**Livré** (`91f0cfb`, `945cdb8`) :
- `MailServerCommands.SearchFolder` (IMAP SEARCH, jamais nommé jusqu'ici) ;
- les 4 enregistrements dans `ExecuteFolderSearchAsync`, étiquetés par la
  famille d'opération appelante (`GetFolderStatus` / `GetFolderQuery`) — couvre
  les appels `folder` (cache-miss) **et** `today` du dashboard ;
- recorder en paramètre optionnel du constructeur (style ImapService) ;
- 3 tests (nombre + ordre, attribution, absence prouvable), **mutation éprouvée
  avec reconstruction du binaire de test : 2/3 rouges** quand l'enregistrement
  de `search_folder` disparaît.

### Étape 2 — aucune réduction livrée, et voici pourquoi (DOD honoré)

La moyenne de 267 ms de l'appel `folder` mélange cache-hit Redis (rapide) et
cache-miss (4 allers-retours IMAP sous 96 ms de latence injectée). **Cette
décomposition n'était pas mesurable** — c'est précisément ce que le compteur
branché ici rend lisible à la prochaine campagne. Réduire avant de compter
serait l'erreur de task-222.

**Seuil qui rouvre le sujet** : si la prochaine campagne confirme ≥ 2
allers-retours IMAP par appel `folder` non-caché (lecture directe de
`mssante_mail_server_solicitations_total{operation="GetFolderStatus"}` rapportée
au nombre d'appels), le remède candidat est côté cache — durée, ou STATUS au
lieu de SEARCH — dans une US dédiée, avec fraîcheur énoncée (décision produit,
comme l'exige ce task file).

**Ce que le médecin voit est inchangé** : le diff ne touche que l'enregistrement
de compteurs (aucune valeur servie ne change) ; les tests existants du service
restent verts.

### Suite pré-existante connue (hors diff)

AiPromptHelperTests (rouge depuis `411b289`) et les 5 filtres « aujourd'hui »
dans la fenêtre nocturne 00h–02h (documentés à la PR #190) — aucun de ces
fichiers dans ce diff.

## Simplify log (2026-08-15)

Skip propre — diff de 3 fichiers (+142/−1) entièrement calqué sur les patterns
maison : enregistrements identiques à ceux d'ImapService (task-225), injection
optionnelle identique à ImapService, harnais de test réutilisé
d'ImapFolderServiceSuccessTests. Aucun axe reuse/simplification/efficacité/
altitude actionnable. dtos-mss non touché (porteur de contrat, jamais simplifié).
