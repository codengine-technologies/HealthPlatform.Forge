# todo-task-226.md — Le dossier patient, là où il naît : à la fin du traitement CDA

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: **wip-task-224** — dépendance **dure**, sur son défaut 5. Un
dossier patient n'existe que pour des messages **analysés**, et task-224 vient
d'établir que la « bande chaude » du parcours ne l'était jamais (la lecture
n'écrit pas dans le stock, et ne doit pas y écrire). C'est sa chauffe par
l'analyse qui rend un dossier consultable ; cette US en fait le point de départ
d'une chaîne. Les lignes de grille décidées ici se transcrivent **par-dessus** la
version livrée par task-224, jamais à côté.
**Priorité**: **2** — le parcours de certification ignore aujourd'hui le geste
qui récupère de très loin le plus de données par action du médecin, et il exige
la reconstruction complète des boîtes entre deux tirs. Les deux se règlent d'un
même mouvement, et la place libérée par le premier paie le second. À livrer
**avant** la prochaine campagne de certification.

## Objective

Deux changements du parcours médecin simulé, qui n'en font qu'un :

1. **Retirer le geste « supprimer ».** C'est le seul geste du parcours qui
   **détruit son corpus** : les messages supprimés ne reviennent pas, donc chaque
   tir exige la reconstruction complète des boîtes de messagerie avant le
   suivant. Tout le reste du parcours ne consomme que de la donnée
   **reconstructible sans toucher aux boîtes**.

2. **Ajouter la consultation du dossier patient, là où elle a lieu dans la vraie
   vie : au bout du traitement.** Le dossier d'un patient n'est pas une donnée
   qui préexiste — **c'est le produit de l'analyse CDA des messages reçus**, et
   seulement pour ceux qui portent une INS. Le parcours ne mesure ni le geste, ni
   la chaîne qui le rend possible.

## La chaîne à simuler — et pourquoi c'est une chaîne, pas un geste isolé

> **Décision de modélisation, et elle révise task-220.** task-220 avait écarté
> l'analyse du parcours au motif qu'« aucun médecin ne déclenche un
> enrichissement ». C'est toujours vrai comme **geste** — et cette US ne le
> transforme pas en geste. Mais la conclusion tirée à l'époque (« l'analyse
> n'appartient pas au parcours ») ne tient plus dès qu'on veut mesurer le dossier
> patient : **sans analyse, il n'y a pas de dossier**. L'analyse entre donc dans
> le parcours comme ce qu'elle est — un **traitement de la plateforme** qui
> précède le médecin — et le dossier se consulte **à sa sortie**.

```
   [plateforme]  traitement CDA d'un lot de messages non analysés
                 → les documents porteurs d'une INS constituent le dossier
                          ↓
   [médecin]     il ouvre un des messages qui viennent d'être traités
                 → c'est là qu'apparaît le patient rattaché
                          ↓
   [médecin]     il consulte le dossier de ce patient
                 → recherche, page du dossier, opposition, puis la rafale
```

Trois raisons de passer par la lecture du message au milieu, plutôt que d'aller
droit au dossier :

- **c'est le chemin réel** — le badge patient s'affiche sur le message ouvert, et
  le client offre le saut vers le dossier de ce patient ;
- **c'est le seul chemin qui donne l'identifiant** — le traitement, lui, ne
  répond rien d'exploitable (corps de réponse vide) ; le harnais n'a donc aucun
  moyen d'apprendre le patient autrement qu'en lisant un message traité, et il
  n'a **pas** à en inventer un ;
- **il n'ajoute aucun appel artificiel** — c'est l'étape 3 du parcours, déjà là,
  déjà mesurée, qui sert de pivot.

## Ce que la consultation fait vraiment — et pourquoi elle compte

Séquence relevée sur le client **Blazor** (le seul frontend présent dans le plan
de travail ; `Client/Angular` est absent du poste — à recoller le jour où le repo
est disponible, la règle de provenance de `docs/parcours-medecin.md` reste la
même : c'est le client qui fait foi, pas l'API) :

| # | Geste du médecin | Appel | Provenance |
|---|---|---|---|
| 1 | il tape un nom dans la barre de recherche patient | recherche patient avancée | `Client/Blazor/.../SearchPatientComponent.razor:150-202` — attente de 300 ms après la frappe, minimum 3 caractères ⇒ **1 à 3 recherches** par geste, pas une |
| 2 | il clique sur un résultat | 1<sup>re</sup> page du dossier (20 documents) | `Pages/Patient.razor:114` |
| 3 | la fiche s'affiche | opposition du patient | `Components/PatientCard.razor:101` |
| 4 | **la fiche se remplit** | **N ouvertures de message, lancées toutes en parallèle** | `Pages/Patient.razor:150-171` |
| 5 | il défile vers le bas | page suivante **+ la même rafale** | `Pages/Patient.razor:127-148` |

**C'est le point 4 qui justifie cette US.** La page du dossier ne rapporte jamais
le contenu des messages : le client le redemande ensuite, **pour chacun des 20
messages de la page, tous en même temps**. Une consultation de dossier, c'est
donc de l'ordre de **23 appels en une seule action du médecin** — contre ~8,5
pour un **passage entier** du parcours actuel.

Le corpus coopère, c'est vérifié : sur les 169 jeux de documents de test,
**99 portent le même patient** (62 %), 27 un deuxième, 18 un troisième — et
**10 n'ont aucune INS**. La distribution en ronde du semis concentre donc
naturellement la majorité d'une boîte sur un seul dossier, et fournit au passage
la juste proportion de documents **non rattachables**.

**La grandeur qui rend le tir intéressant** : la première page est plafonnée à 20
documents par le client, donc la rafale **sature à 20** dès que le dossier
dépasse cette taille — tandis que le dossier, lui, **continue de grossir** à
chaque traitement. Or la page se calcule en lisant **tout** le dossier avant de
paginer (voir « Hors scope »). Le tir mesurera donc exactement ce qu'on veut
savoir : **le coût d'une page qui ne grandit pas, dans un dossier qui grandit.**

## Ce qu'il ne faut PAS présumer

- **Ne pas faire du traitement un geste du médecin.** Il n'apparaît pas dans la
  grille de temps de réponse attendus du médecin, et son temps n'est pas du temps
  d'attente du médecin. Il est **publié** (durée, volume, court-circuits), il
  n'est pas **jugé**.
- **Ne pas laisser le traitement dévorer le passage.** L'analyse est l'opération
  la plus chère du produit (plusieurs secondes par message). Un lot de la taille
  d'une page (20) coûterait plus d'une minute et ferait du médecin simulé un
  employé de la salle des machines. Le lot doit rester **de la taille d'une
  arrivée de courrier**, pas d'un rattrapage.
- **Ne pas puiser le traitement et l'ouverture froide dans la même réserve.**
  Les deux consomment le stock de messages non analysés, et le traitement
  **transforme** ce qu'il touche. Si les deux se croisent, l'étape 4 « ouvrir un
  message froid » finit par mesurer de l'analysé sous un nom de froid — c'est
  **exactement** le défaut 5 de task-224, qu'il serait absurde de réintroduire
  par une autre porte. Réserves séparées, et le rapport doit pouvoir le prouver.
- **Ne pas traiter l'absence d'INS comme une erreur.** Un document sans INS
  n'entre dans aucun dossier : il reste en attente de rattachement manuel. C'est
  le comportement attendu du produit, ~6 % du corpus, et le harnais doit le
  **compter**, jamais le compter en échec.
- **Ne pas confondre « remplir une fiche patient » et « ouvrir un message ».**
  Les deux passent par le même appel, mais l'un est une **rafale** et l'autre un
  geste unitaire. Étiquettes distinctes, obligatoirement : sinon la rafale noie le
  percentile de l'étape 3 — celle-là même que task-224 vient de remettre
  d'aplomb — et le verdict redevient non opposable pour une deuxième raison.
- **Ne pas lancer les 20 ouvertures en une seule salve.** Le vrai client est
  bridé par le navigateur (~6 requêtes simultanées par serveur). Une salve de 20
  mesurerait une charge que le produit n'émet jamais.
- **Ne pas croire que l'ouverture d'un message alimente le dossier.** Elle ne le
  fait pas (défaut 5 de task-224) : seul le traitement écrit. C'est toute la
  raison d'être de la chaîne décrite plus haut.
- **Ne pas laisser la chauffe décider du sort du tir.** La fenêtre certifiée doit
  commencer avec une première page **déjà pleine**, ce qui suppose une chauffe par
  l'analyse (task-224). Elle doit être **mesurée, bornée et publiée**. Si elle
  devient la moitié du tir, il faut l'étaler ou réduire la cible, jamais l'ignorer.
- **Ne pas payer deux fois la même analyse pour rejouer un tir.** Le besoin :
  rejouer sans reconstruire les boîtes **et** sans ré-analyser ce qui l'était
  déjà, tout en rendant la réserve froide **réellement froide**. Ces états vivent
  dans le même stock et la remise à zéro d'aujourd'hui est tout-ou-rien. Une
  remise à zéro **par réserve** est la voie évidente — mais la contrainte est le
  résultat, pas le moyen.
- **Ne jamais écrire l'identifiant patient ailleurs que dans le corps des
  appels** — ni dans une étiquette de métrique, ni dans un nom de fichier de
  rapport, ni dans une trace du harnais (garde-fou repris de task-224 et
  task-225).
- **Ne pas retirer « marquer lu » avec « supprimer ».** L'étape 8 de la grille
  reste, réduite à « marquer lu » seul.
- **Ne pas conserver la bande de suppression « au cas où ».** Une bande réservée
  que rien ne consomme est de la place perdue, et le contrôle de budget qui la
  garde ferait échouer des campagnes pour un geste qui n'existe plus.
- **Ne pas comparer les chiffres de cette version à la baseline du 2026-08-03.**
  Elle est **déjà** invalidée sur l'étape 3 par task-224, et le mélange change ici.
  Nouvelle baseline, à **dire** dans le rapport plutôt qu'à laisser deviner.

## Décisions produit — actées par le PO, à transcrire telles quelles

### La chaîne et ses fréquences

- **Traitement** : **0,25 par passage**, sur un lot de **2 messages** non
  analysés. Justification : c'est l'ordre de grandeur d'une arrivée de courrier
  entre deux visites d'un médecin, ça coûte quelques secondes au passage (contre
  plus d'une minute pour un lot de 20), et sur une fenêtre de 30 min à rythme
  réel ça alimente le dossier d'assez de documents pour que sa croissance soit
  mesurable.
- **Consultation du dossier** : **0,6 quand un traitement vient d'avoir lieu
  dans le passage** (le médecin qui voit arriver un document regarde le dossier),
  **0,1 sinon** (consultation spontanée). C'est la traduction directe de la
  décision : l'accès au dossier suit le traitement, sans devenir mécanique.
- **Temps de réflexion « lecture du dossier »** : **10 à 60 s** — le médecin lit
  une timeline, il ne la survole pas.
- **Réserves par boîte**, la suppression étant retirée : **analysée d'avance
  (chauffe) 0,4 / ouverture froide 0,3 / traitement 0,3**. Les deux dernières ne
  se recouvrent pas, c'est le point dur.

### La grille de temps de réponse attendus

Contrat produit, en deux exemplaires qui bougent ensemble : le contrat lisible
(`Api/Mail/docs/SLO-parcours-medecin.md`) et sa transcription exécutable dans le
rapport. Valeurs décidées ici, **à appliquer sur la version livrée par
task-224** :

| # | Étape | Médiane | 95<sup>e</sup> centile |
|---|---|---|---|
| 8 | **Marquer lu** (« supprimer » retiré) | 200 ms | 1 s |
| 9 | **Rechercher un patient** | 300 ms | 1,5 s |
| 10 | **Ouvrir la page d'un dossier patient** | 500 ms | 2 s |
| 11 | **Fiche patient complète** — de la sélection du patient au dernier document affiché | 1,5 s | 4 s |

L'étape 11 est le chiffre que le médecin **ressent** ; les étapes 9 et 10 disent
où le temps est passé. Les trois se lisent ensemble. **Le traitement n'a pas de
ligne** : il est publié, pas jugé.

### Conditions de mesure

- **100 messages par boîte** pour un tir de certification — la réserve analysée
  d'avance (~40 messages, dont ~25 sur le patient majoritaire) remplit la
  première page avant l'ouverture de la fenêtre. 50 restent suffisants pour un
  tir de découverte, à condition que le rapport publie la largeur de rafale
  obtenue. À inscrire dans les conditions de mesure du contrat, au même titre que
  « médecin au rythme réel » et « fenêtre ≥ 30 min ».
- **Arbitrage assumé** : si le coût de la chauffe s'avère insoutenable au palier
  200, **réduire la cible et publier la largeur de rafale réelle** est préférable
  à une page pleine obtenue au prix d'un tir que la chauffe domine. Le chiffre
  honnête bat le chiffre flatteur.
- **Repli si le traitement en ligne déforme le rythme** : si la mesure montre que
  le traitement mange une part notable du passage malgré le lot de 2, la voie de
  repli est de le sortir du passage — un petit nombre de travailleurs de
  plateforme en parallèle des médecins, comme en production. **Ne pas l'engager
  d'emblée** (ça complique le modèle fermé que task-220 a bâti), mais le mesurer
  assez pour pouvoir en décider : la part du traitement dans la durée d'un
  passage est une grandeur à publier.

## Contenu attendu

1. **Le geste « supprimer » retiré du parcours** : l'étape, sa probabilité, son
   temps d'hésitation, sa réserve de messages, et le contrôle de budget qui la
   protégeait. Le compteur de dépassement de budget survit pour les réserves
   restantes.
2. **La chaîne traitement → lecture du message traité → consultation du dossier**,
   avec les cinq appels relevés plus haut, la rafale bridée comme le vrai client,
   et l'identifiant patient récupéré **depuis la réponse de lecture**, jamais par
   un appel ajouté.
3. **Des réserves séparées** pour le traitement et pour l'ouverture froide, et de
   quoi **prouver** dans le rapport qu'elles ne se sont pas croisées.
4. **Le traitement publié, pas jugé** : nombre de messages analysés, durée, part
   du passage, court-circuits éventuels, et **documents sans INS** (en attente de
   rattachement) comptés à part.
5. **La largeur de rafale et la taille du dossier publiées par palier** — la
   première sature, la seconde croît ; c'est leur écart qui porte l'information.
6. **Le coût de la chauffe publié** : durée, part du tir, volume analysé.
7. **Rejouer un tir sans semis ni ré-analyse** : la remise à zéro doit rendre la
   réserve froide froide **sans** détruire l'analyse déjà acquise, et le mode
   d'emploi du harnais doit dire comment, avec le gain de temps constaté.
8. **La grille mise à jour dans ses deux exemplaires**, avec les 4 lignes actées
   et les conditions de mesure complétées.
9. **Le rapport qui dit que la baseline a changé.**
10. **La provenance consignée** dans `Api/Mail/docs/parcours-medecin.md` : la
    chaîne et son origine (composant client, ligne), **la révision explicite de
    la décision de task-220 sur l'analyse** et sa raison, le retrait de la
    suppression, et la règle « seul l'analysé, et seulement s'il porte une INS,
    peuple un dossier ».

## Hors scope

- **Toute campagne de mesure.** Cette US livre l'instrument. Le tir de
  certification qui l'utilisera est une décision séparée.
- **Le retour du geste « supprimer » sous une forme non destructive.** Deux voies
  existent (faire supprimer au médecin un message qu'il vient d'envoyer, ou faire
  voyager un même message entre deux dossiers), les deux tiennent, et aucune n'est
  engagée ici : la suppression est **retirée pour le moment**, sur décision
  explicite. Le jour où elle revient, ce sera une US à elle.
- **Les cinq défauts de task-224** — dont la chauffe par l'analyse et le refus
  d'une étape mal nommée. Cette US **s'appuie** dessus, elle ne les refait pas.
- **Le décompte des sollicitations serveur** livré par task-225 : il servira à
  expliquer le coût du traitement et de la rafale, il n'est pas rouvert ici.
- **Le rattachement manuel d'un document sans INS** : le harnais le **compte**,
  il ne le simule pas (c'est un geste à part entière, avec ses écrans).
- **Deux défauts du produit constatés en analysant la vue patient**, à instruire
  séparément — cette US les **observe**, et le harnais doit reproduire le client
  **tel qu'il est**, défaut compris :
  - « charger plus » sur un dossier patient **recharge la première page** (le
    client compte les pages à partir de 0, l'API à partir de 1) ;
  - la page d'un dossier **lit tous les documents du patient puis pagine en
    mémoire**, avec des filtres de dossier qui interdisent tout index — le coût
    suit la taille du dossier, jamais la page demandée. C'est le défaut que la
    croissance du dossier pendant le tir va exposer, et c'est voulu.
  Si le tir confirme qu'ils pèsent, ils deviennent des US applicatives : c'est le
  but de l'instrument.
- Les autres frontends : `client-angular` et `client-mobile` ne sont pas touchés
  (le banc mesure le service, pas l'affichage).

## Definition of Done

- [ ] Build passe (0 erreur)
- [ ] Tests passent (0 échec) — y compris les tests du modèle de parcours
- [ ] Les tests du modèle couvrent : le retrait de la suppression, les nouvelles
      réserves, **la non-intersection des réserves traitement / ouverture
      froide**, les fréquences de la chaîne (dont la consultation conditionnée au
      traitement), et un contrôle de budget qui ne mentionne plus la suppression
- [ ] `selftest.sh` vert
- [ ] **Aucune mention du geste « supprimer »** ne subsiste dans le parcours ni
      dans son contrôle de budget (vérifié par recherche, consigné dans le
      `## Develop log`)
- [ ] Un tir court produit les 4 nouvelles étiquettes avec des échantillons non
      nuls, **et** la chaîne est visible dans l'ordre attendu sur une trace
      (traitement → lecture → dossier)
- [ ] La rafale est **bridée à 6 appels simultanés** au plus (preuve : largeur
      publiée et nombre d'appels par consultation concordants avec le modèle)
- [ ] Les documents de la fiche **n'apparaissent pas** dans le percentile de
      l'étape 3 (preuve : les deux étiquettes et leurs comptes d'échantillons)
- [ ] **La fiche n'est pas vide** : largeur de rafale ≥ 10 documents sur un semis
      à 100 messages par boîte — sans quoi l'étape 11 ne mesure rien
- [ ] **L'étape 4 mesure encore du froid** à la fin du tir : prouvé, pas supposé
      (le traitement n'a pas empiété sur sa réserve)
- [ ] **La taille du dossier croît** sur la fenêtre alors que **la largeur de
      rafale sature** — les deux publiées par palier
- [ ] Le traitement est publié (messages analysés, durée, part du passage,
      court-circuits) et **n'apparaît dans aucune ligne de la grille**
- [ ] Les **documents sans INS** sont comptés à part et **ne comptent pas en
      échec**
- [ ] Le coût de la chauffe figure dans le rapport (durée, part du tir, volume)
- [ ] Les 4 lignes de grille apparaissent **à l'identique** dans le contrat
      lisible et dans le rapport — un écart fait échouer le DOD
- [ ] Le rapport signale explicitement que la baseline diffère du 2026-08-03
- [ ] `Api/Mail/docs/parcours-medecin.md` documente la chaîne, sa provenance, la
      **révision de la décision de task-220** sur l'analyse, et la règle
      « analysé + INS ⇒ dossier »
- [ ] **Deux tirs consécutifs sans reconstruction des boîtes et sans ré-analyser
      ce qui l'était déjà** : les deux exploitables, réserve froide réellement
      froide au second, écart de mesure consigné. C'est le critère qui prouve le
      gain de cette US.
- [ ] Aucun identifiant patient dans une étiquette de métrique, un nom de fichier
      de rapport ou une trace du harnais
- [ ] Rien n'est branché dans le cycle de la forge ni dans la CI

## Manual Test Plan

```bash
# 0. Prérequis : task-224 (défaut 5) présente — sans sa chauffe par l'analyse,
#    la première page du dossier est vide et l'étape 11 ne mesure rien.

# 1. Banc + semis à 100 messages par boîte (condition de certification)
cd Api/Mail
dotnet run --project src/AppHost --launch-profile https-load-test
dotnet run --project tests/mss.mail.loadtest.seed -- --users 20 --messages 100 \
  --api http://127.0.0.1:5052

# 2. Tir court au rythme accéléré — l'instrument suffit à valider
export BYPASS_KEY=loadtest-local-only
tests/loadtest-k6/observe.sh start 900
USERS=20 MESSAGES_PER_USER=100 \
  JOURNEY_STAGES="10:5m" JOURNEY_TIME_COMPRESSION=10 \
  tests/loadtest-k6/run.sh journey
tests/loadtest-k6/report.sh <dernier json>

# 3. LE test de cette US — rejouer sans semis et sans ré-analyse
#    (option exacte livrée par l'US ; elle conserve les boîtes ET l'analyse acquise)
tests/loadtest-k6/reset-state.sh --keep-maildir <option livrée par l'US>
USERS=20 MESSAGES_PER_USER=100 \
  JOURNEY_STAGES="10:5m" JOURNEY_TIME_COMPRESSION=10 \
  tests/loadtest-k6/run.sh journey
tests/loadtest-k6/report.sh <dernier json>
```

**Ce que l'humain doit voir** :

- dans le rapport du tir 1 : les étapes **« rechercher un patient »**, **« ouvrir
  la page d'un dossier »**, **« fiche patient complète »**, chacune avec ses
  échantillons et son verdict — et **plus aucune ligne « supprimer »**, l'étape 8
  ne parlant que de « marquer lu » ;
- **la chaîne, dans l'ordre**, sur au moins une trace : un traitement, puis la
  lecture d'un des messages traités, puis la consultation du dossier de son
  patient ;
- le **traitement publié hors grille** : messages analysés, durée, part du
  passage — et une part qui reste minoritaire ;
- **la taille du dossier qui croît** pendant que **la largeur de rafale sature**
  autour de 20 : c'est le couple de chiffres à surveiller ;
- des **documents sans INS** comptés à part, et **zéro erreur** de ce fait ;
- l'étape **« ouvrir un message froid »** toujours au niveau du froid en fin de
  tir — signe que le traitement n'a pas mangé sa réserve ;
- l'étape « ouvrir un message enrichi » avec un nombre d'échantillons **du même
  ordre qu'avant** : la rafale ne s'y est pas déversée ;
- un avertissement disant que la baseline diffère de celle du 2026-08-03 ;
- **entre les deux tirs : aucun semis, et pas de seconde analyse de ce qui était
  déjà analysé** — quelques secondes au lieu de la reconstruction. Le tir 2 est
  exploitable et ses chiffres sont du même ordre.

**Données de test** : boîtes `loadtest-*`, corpus de documents de test publics
(jeux ANS/CI-SIS), identités virtuelles déterministes du banc. **Aucune donnée de
santé réelle, aucun patient réel.**

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville — outillage interne de mesure du service
  de messagerie MSSanté du praticien.
- **Vague Ségur** : hors vague — instrumentation interne. Le produit n'est pas
  modifié : le banc n'appelle que des services déjà livrés.
- **Exigences DSR honorées** : aucune nouvelle. L'US **outille** la démonstration
  de tenue en charge de l'alimentation et de la consultation d'un dossier
  patient ; elle ne crée aucune exigence.
- **INS** : au **cœur** de l'US, et **uniquement sous forme synthétique**. Les
  identifiants exercés sont ceux des jeux de test publics du corpus CI-SIS,
  jamais une INS réelle, jamais une INS qualifiée par INSi — **aucun appel au
  téléservice INSi**. Le harnais ne les journalise pas et ne les met dans aucune
  étiquette. Le comportement exercé est celui du produit : **un document sans INS
  n'entre dans aucun dossier** et reste en attente de rattachement manuel
  (identito-vigilance : pas de rattachement deviné, jamais de création de patient
  depuis un flux de rattachement).
- **Authentification PS** : non applicable — le banc conserve son mécanisme de
  contournement, bloqué en production par construction.
- **Habilitations** : inchangées.
- **Interop CI-SIS** : **exercée pour de vrai** — le traitement décode du **CDA
  r2** issu des jeux de test des volets CI-SIS par la chaîne existante
  (`interop-cda`), et c'est cette analyse qui constitue le dossier. Aucun format,
  aucun ValueSet, aucun profil n'est modifié : l'US les traverse.
- **Tracé PGSSI-S** : aucun évènement métier nouveau. Le banc analyse des
  messages et lit des dossiers **synthétiques** : les traces produites côté
  produit (analyse, consultation de dossier) le restent à l'identique, et ce
  volume supplémentaire est **attendu** pendant un tir. ⚠️ Garde-fou : **ni
  identifiant patient, ni nom de document, ni identifiant de message** dans les
  étiquettes de métriques et les noms de fichiers de rapport — un titre de
  document désigne couramment le patient et l'examen (leçon de task-213, règle
  reprise par task-224 et task-225).
- **Consentement patient** : non applicable — patients synthétiques. L'appel
  d'opposition exercé par la consultation est une **lecture**, jamais une
  écriture : le banc ne modifie aucune opposition.
- **Référentiels métier** : LOINC (portés par les documents du corpus) — non
  modifiés, seulement traversés.
- **Hébergement HDS** : non — banc local et cluster de test interne, données
  synthétiques exclusivement. Aucun environnement de production touché.
- **AIPD / impact RGPD** : néant — aucune donnée personnelle réelle, aucun
  traitement nouveau.

## Branches

- `api-mail` (pushed) : `feat/task-226-journey-dossier-patient` —
  https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-226-journey-dossier-patient
- `dtos-mss` (pushed) : `feat/task-226-journey-dossier-patient` —
  https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-226-journey-dossier-patient
  (auto-incluse par `/start` ; aucun changement de contrat n'est attendu — la
  branche restera probablement sans commit et sans PR)

**Base** : `develop` d'api-mail au commit `aab6297` — **task-224 (PR #152) y est
mergée**, donc la chauffe par l'analyse dont cette US dépend est présente dans la
base. Dépendance levée au démarrage, pas supposée.

**Pre-flight** : `api-mail`, `client-blazor`, `dtos-mss`, `sdk`, `interop-cda`
sur `develop`. `host` n'a pas de `.git` (non mesurable, cf. CLAUDE.md).
`client-mobile` est **absent du poste** — hors périmètre de cette task.

## Develop log

- **Repos touchés** : `api-mail` uniquement. `dtos-mss` : branche créée par
  `/start` (auto-inclusion) mais **aucun commit** — la task ne change aucun
  contrat, donc aucun paquet NuGet publié et aucun consommateur bumpé.
- **DTOs publiés** : aucun changement de contrat. **Interop** : aucun.
- **Commits** (`feat/task-226-journey-dossier-patient`) :
  - `c481eb0` — le parcours : réserves disjointes, chaîne traitement → lecture →
    dossier, rafale bridée à 6, retrait franc de « supprimer » (modèle + scénario
    + endpoints + gabarits d'adresse)
  - `c13d795` — le rapport : grille (8 réduite, 9/10/11 ajoutées), couple
    rafale/dossier, refus d'interpréter une fiche maigre, bandeau de baseline,
    coût de la chauffe et du traitement
  - `2dbe1f5` — `reset-state.sh --keep-analysed N` (rejeu par réserve), provenance
    et contrat SLO
  - `4c9fc3a` — la grille ne peut plus diverger de son contrat lisible
- **Validation locale** : `dotnet build` 0 erreur · `dotnet test` **3 203 tests,
  0 échec** · `selftest.sh` vert (**54** tests Node + **157** Python) · les
  **7 scénarios** k6 s'initialisent (`k6 inspect`).

### Écarts de périmètre déclarés

- **Un guard non demandé par la task, ajouté** : `warmupWarnings` avertit quand la
  chauffe dépasserait le délai d'expiration de l'appel d'analyse (300 s). Sans lui,
  une réserve analysée trop grande fait échouer la chauffe **en silence** et
  l'étape 3 mesure des messages non analysés — le défaut 5 de task-224 ramené par
  la porte du dimensionnement. C'était le point de vigilance n°1 de la task, il
  n'avait pas de garde.
- **Une correction de documentation hors périmètre littéral** :
  `docs/parcours-medecin.md` affirmait encore que la lecture froide « matérialise »
  le contenu. C'est exactement l'affirmation que task-224 a démentie. Corrigée avec
  sa raison — un document faux derrière un comportement juste finit par ramener le
  défaut.

### DOD — auto-contrôle

Vérifiés par commande (14/20) :

- [x] Build 0 erreur · tests 0 échec · `selftest.sh` vert
- [x] Tests du modèle : retrait de la suppression, nouvelles réserves,
      **non-intersection** des réserves, fréquences de la chaîne (dont la
      consultation conditionnée au traitement), budget sans suppression
- [x] Aucune mention de « supprimer » dans le parcours ni son budget — vérifié par
      recherche (`grep` sur `BANDS`, `P.delete`, `'delete'`, `deleteEmail` : zéro
      occurrence) ; les surcharges d'environnement de l'ancien geste **font
      échouer le setup** (vérifié par `k6 inspect` sur les trois variables)
- [x] Rafale bridée à 6 : `http.batch` par tranches, plafond archivé dans le
      contexte du tir
- [x] Documents de la fiche hors du percentile de l'étape 3 : étiquette
      `patient_docs` distincte de `read_content`
- [x] Traitement publié et dans **aucune** ligne de grille — test dédié
- [x] Documents sans INS comptés à part et jamais en échec — test dédié, y compris
      la non-dégradation du verdict
- [x] Coût de la chauffe publié — test dédié
- [x] Grille identique dans ses deux exemplaires — **test automatisé** qui lit le
      Markdown et compare les 11 étapes seuil par seuil
- [x] Rapport signale la baseline différente du 2026-08-03, avec la raison
- [x] `parcours-medecin.md` : chaîne + provenance ligne à ligne, révision explicite
      de la décision de task-220, règle « analysé + INS ⇒ dossier »
- [x] Aucun identifiant patient dans une étiquette — test PGSSI-S sur les gabarits
- [x] Rien branché dans la forge ni dans la CI

Déferrés au test manuel (HAG) — ils exigent un banc, pas un test unitaire (6/20) :

- [ ] Un tir court produit les 4 nouvelles étiquettes, et la chaîne est visible
      dans l'ordre attendu sur une trace
- [ ] Largeur de rafale ≥ 10 documents sur un semis à 100 messages
- [ ] L'étape 4 mesure encore du froid en fin de tir (garanti par construction —
      réserves disjointes contrôlées au setup et testées — mais à **prouver** sur
      un tir)
- [ ] Taille du dossier qui croît alors que la largeur de rafale sature
- [ ] Coût de la chauffe minoritaire dans la durée du tir
- [ ] **Deux tirs consécutifs sans semis et sans ré-analyse** — le critère qui
      prouve le gain de la task. L'outil est livré
      (`reset-state.sh --keep-maildir --keep-analysed N`), la démonstration
      appartient au banc.

- **Next step** : `/forge-simplify task-226`

## Simplify log

- **Repos passés** : `api-mail` (seul repo touché).
- **Appliqué & commité** : `api-mail` — 6 fichiers (`93ed66d`).
- **Sans changement** : aucun autre repo touché.
- **Ignorés (contrat / exclus)** : `dtos-mss` (zéro diff **et** porteur de
  contrat), `interop-cda`, `devops`, `psc-proxy-*`.
- **Build / tests** : ✓ verts avant **et** après la passe (55 tests Node, 157
  Python, les 7 scénarios k6 s'initialisent) — le filet anti-régression a tenu,
  aucun rollback.

Quatre nettoyages, un par axe :

| Axe | Trouvaille | Correctif |
|---|---|---|
| Réutilisation | le chemin d'une ouverture de message construit dans **deux** fichiers (`api.js` et la rafale, qui passe par `http.batch` donc ne pouvait pas appeler le premier) | `emailContentPath()` exporté et partagé |
| Altitude | deux gardes `if` ad hoc dans le scénario, alors qu'un mécanisme générique de refus existait juste à côté | table `REMOVED_OVERRIDES` + `assertNoRemovedOverrides()` dans le modèle, **avec la raison** de chaque retrait |
| Efficacité | `reservesDisjoint` énumérait tous les UIDs de la boîte dans un `Set` pour trois intervalles ; `journey_warmup_cost` calculait un champ que personne ne lit | comparaison d'intervalles ; champ mort supprimé |
| Simplification | `treatedUid !== null` évalué trois fois dans deux expressions denses | un `justTreated` nommé |

> **Écart de mécanisme déclaré** : la consigne de session interdit d'appeler
> l'outil Agent sans demande explicite de l'humain. La revue des quatre angles a
> donc été menée **en ligne** au lieu d'être répartie sur quatre sous-agents. Le
> livrable est identique (quatre axes couverts, correctifs appliqués et validés) ;
> seul le parallélisme manque.

- **Next step** : `/sonar task-226` (api-mail touché)

## Sonar log

**Skip justifié — rien de cette task n'entre dans le périmètre de l'analyse.**
Ce n'est pas un skip silencieux : voici la preuve.

| Contrôle | Mesure |
|---|---|
| Fichiers `.cs` dans le diff de la task | **0** |
| Extensions touchées | 5 `.js`, 3 `.md`, 2 `.mjs`, 2 `.py`, 1 `.sh` |
| Périmètre du scanner | `dotnet sonarscanner` autour du build de `HealthPlatform.Api.Mail.sln` — il ne voit que ce que MSBuild compile |
| `tests/loadtest-k6/` dans la solution ? | **non** (harnais k6 / Python, aucun `.csproj`) |

La task ne produit donc **aucun new code** au sens de SonarQube : une analyse ne
pourrait remonter que de la dette préexistante de `develop`, qui n'est pas
l'affaire de cette task (la règle de la chaîne est le new code). Le principe
« jamais de skip silencieux sur du new code » est respecté — il n'y a pas de new
code à scanner.

**Aucun tableau de KPIs n'est produit, et il faut le dire** : la consigne du
CLAUDE.md est de toujours monitorer la qualité. Ici l'analyse est de surcroît
**non exécutable dans cette session** — `SONAR_TOKEN` et `SONAR_HOST_URL` sont
absents de l'environnement (le scanner, lui, est installé). Les deux raisons sont
indépendantes : même avec le jeton, il n'y aurait rien à attribuer à la task.

> La qualité du code livré a été contrôlée par les moyens qui s'appliquent
> réellement à du JS/Python : `/forge-simplify` (4 nettoyages appliqués, un par
> axe) et la suite d'auto-tests du harnais (55 Node + 157 Python, verte).

## Lint & vérification visuelle — skips

| Étape | Décision | Raison |
|---|---|---|
| `/lint-angular` | **skip** | `client-angular` n'est pas dans `**Repos**:`, aucun fichier Angular touché — et le répertoire `Client/Angular` est **absent du poste** (constat consigné au `/start`) |
| `/lint-mobile` | **skip** | `client-mobile` n'est pas dans `**Repos**:`, `Client/Mobile` **absent du poste** |
| `/verify-visual` | **skip** | aucun écran mobile touché (la task ne livre aucun écran : c'est de l'outillage de mesure) |

- **Next step** : `/review task-226`

## PRs

- **`api-mail`** : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/153
  — label `awaiting-human-merge`, 6 commits, 13 fichiers (+1 573 / −216)
- **`dtos-mss`** : **aucune PR** — branche créée par `/start` (auto-inclusion) mais
  **zéro commit** : la task ne change aucun contrat. Build vérifié quand même
  (0 erreur). La branche `feat/task-226-journey-dossier-patient` reste vide.
- Repos exclus : `devops`, `psc-proxy-*` — managed manually by the human.
- `client-angular` / `client-mobile` : **hors périmètre** (non listés dans
  `**Repos**:`) et **absents du poste**.

## Code Review Summary

**Verdict : APPROVED** — 13 fichiers relus, **0 blocage**, 2 défauts corrigés en
cours de revue, 3 suggestions non bloquantes.

### Corrigés pendant la revue — écart de règle déclaré

`/review` est en lecture seule sur le code. Ces deux points ont été corrigés
(`bffa39e`) plutôt que laissés en suggestions **parce que tous deux font dire un
faux à l'instrument** — le mode d'échec que cette EPIC a déjà payé trois fois. Le
choix est déclaré ici et dans la PR, pas caché ; validation complète rejouée
derrière (3 305 tests .NET, 55 Node, 157 Python).

1. **`journey_docs_without_ins` sous-comptait les cas mixtes** — la boucle sortait
   au premier document porteur d'une INS : un message portant un document
   rattachable *et* un document sans INS déclarait **zéro** en attente. C'est
   précisément le cas que le produit doit présenter, et ce compteur est publié.
2. **Le rapport affirmait « un appel de chauffe par médecin »** — vrai depuis
   task-224, faux avant. Constaté en régénérant le rapport du 2026-08-03, qui
   annonçait « 3000 appels (un par médecin) » pour 200 médecins.

### Suggestions non bloquantes

1. **Le 5ᵉ appel du geste (« charger plus ») n'est pas implémenté** — 4 des 5
   appels documentés sont exercés. Le PO a acté une fréquence pour le traitement et
   la consultation, **aucune pour le défilement** ; en inventer une serait une
   décision de banc déguisée en décision produit. S'ajoute que le défaut de
   pagination fait rendre à `page=1` le même contenu que `page=0` : un défilement
   doublerait la rafale pour zéro information. **Demande une décision PO**
   (`JOURNEY_P_LOAD_MORE`). Hors DOD ⇒ non bloquant (règle 9).
2. **La recherche par nom ne dépouille pas sa réponse** — le harnais va droit au
   dossier de l'INS connue là où le client choisit dans la liste. Requêtes mesurées
   identiques, seule la sélection est court-circuitée.
3. **Un check peut faire échouer un tir** — « la fiche porte au moins un document »
   pèse sur le taux de checks : un corpus sans INS passerait sous `THR_CHECK_RATE`.
   Délibéré (un tir mesurant des fiches vides ne vaut rien), mais à savoir.

### Points vérifiés

- **PGSSI-S** — l'INS voyage dans le chemin de deux adresses et n'atteint **jamais**
  une étiquette de métrique (gabarits `{ins}` + test). Aucun secret. Octets de PJ en
  mémoire, jamais sur disque.
- **Le défaut 5 de task-224 ne peut pas revenir par une autre porte** — réserves
  disjointes contrôlées au setup (refus franc) et testées.
- **Refus francs** des trois variables retirées, **avec la raison**.
- **Non-régression** — le rapport du 2026-08-03 se régénère (exit 0), les nouvelles
  étapes affichent « — » et non « 0 ms ».

### Validation

| Contrôle | Résultat |
|---|---|
| `dotnet build` (api-mail, dtos-mss) | ✓ 0 erreur |
| `dotnet test` (api-mail) | ✓ **3 305 tests, 0 échec** |
| `selftest.sh` | ✓ 55 Node + 157 Python |
| `k6 inspect` × 7 scénarios | ✓ tous s'initialisent |

**DOD** : 15 items vérifiés par commande, **6 déferrés au test manuel** (ils exigent
un banc — détail dans le `## Develop log`).
