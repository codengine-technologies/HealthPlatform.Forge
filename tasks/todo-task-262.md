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
