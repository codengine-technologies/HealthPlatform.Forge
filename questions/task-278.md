# questions/task-278.md — De combien de secondes le tableau de bord peut-il être périmé ?

**Task** : task-278 — *L'arrivée sur le tableau de bord coûte encore un tiers du
temps serveur*
**État** : `wip-task-278.md`, **cause établie, remède non écrit**
**Bloquant** : arbitrage produit, pas technique

---

## Ce qui est acquis (aucune question là-dessus)

La cause du coût est **établie et chiffrée** — le détail est dans le
`## Develop log` de la task. En deux lignes :

> L'appel `folder` de l'arrivée dashboard n'est pas cher : il est **froid**. La
> même route, rejouée 5 secondes plus tard dans la même itération et sur la même
> session, coûte **52,7 ms au lieu de 358,4** (×6,8 sur la moyenne, ×13,6 sur la
> médiane). Le passage du médecin dure ~63 s : toutes les fenêtres de cache ont
> expiré quand il revient sur son tableau de bord.

Et la piste qu'on suivait depuis deux US est **définitivement fermée** :
task-270 a supprimé **45 %** des allers-retours IMAP du chemin dossier (7→5 par
miss **et** part froide 62,7 % → 24,9 %), pour **+0,4 %** de coût vu du médecin.
Le coût de cette route n'est pas borné par les allers-retours.

---

## La question, et elle est pour le PO

Le seul remède que la cause appelle consiste à **servir l'arrivée dashboard sans
attendre le serveur de messagerie**, ce qui revient à afficher des compteurs
potentiellement périmés. Trois formes possibles, du moins au plus agressif :

### Option A — servir le cache, rafraîchir derrière (*stale-while-revalidate*)

Le médecin voit **instantanément** les compteurs de son dernier passage, et
l'écran se met à jour tout seul dès que le serveur a répondu.

- **Gain attendu** : l'arrivée dashboard passe de ~358 ms à ~10 ms **ressentis**.
- **Prix** : pendant ~300 ms, les compteurs affichés peuvent dater du passage
  précédent (jusqu'à quelques minutes si le médecin revient de loin).
- **Question** : est-ce acceptable qu'un compteur « 3 nouveaux messages »
  s'affiche puis devienne « 5 » une fraction de seconde plus tard ?

### Option B — allonger la fenêtre de fraîcheur du statut (aujourd'hui 10 s)

- **Gain attendu** : proportionnel à l'allongement ; à 60 s, la plupart des
  arrivées redeviendraient chaudes.
- **Prix** : un message reçu peut rester invisible jusqu'à N secondes.
- **Question** : **quel N est acceptable pour de la messagerie de santé ?**
  task-270 a déjà refusé d'allonger la fenêtre des **non-lus**, au motif que
  marquer un message comme lu ne fait bouger aucun compteur qui permettrait de
  s'en apercevoir. Le même argument vaut-il ici ?

### Option C — ne rien faire

- **Prix** : l'arrivée dashboard reste le premier poste du temps serveur
  (**34,9 %**), et ce poste croît avec la population.
- **À décharge** : l'étape est **verte au SLO** (p50 14 ms, p95 559 ms pour une
  cible de 300/1 500). **Le médecin n'attend pas trop aujourd'hui.** C'est un
  coût de plateforme, pas une gêne ressentie.

---

## Ce que je recommande, et pourquoi je ne l'ai pas fait

**Option A**, parce qu'elle est la seule qui ne dégrade la fraîcheur que
**pendant l'affichage** et jamais au-delà : le compteur juste est là 300 ms plus
tard, sans action du médecin. L'option B, elle, rend un compteur faux pendant N
secondes **sans que rien ne le corrige**.

Je ne l'ai pas écrite parce qu'elle change **ce que le praticien voit**, et que
la règle 7 réserve ce genre d'arbitrage au PO. Écrire un remède de fraîcheur sur
ma seule appréciation serait exactement le raccourci que cette EPIC a déjà payé
deux fois (task-222 annulée ; et la cause du verrou que j'ai publiée à tort
avant que task-276 ne la réfute).

---

## Deux constats annexes, sans question

1. **La recommandation de mon propre task file était fausse.** Il proposait
   d'attribuer la charge widget par widget via les flags `dashboard_widget_*`
   (task-274). **Ça ne marche pas au banc** : k6 appelle l'API directement et ne
   lit jamais Flagsmith. Les flags restent un levier d'exploitation réel, mais
   pas un instrument de banc. Consigné pour que personne ne le retente.
2. **L'attente du verrou de session vaut 82,8 ms en moyenne** sur `ReadFolder`,
   soit ~48 % du temps serveur de la route. Ce n'est pas la cause du coût froid,
   mais c'est un poste réel qui grandira avec la population — candidat à une US
   distincte, sans arbitrage produit.

---

## RÉPONSE DE L'HUMAIN — 2026-08-30

> « A, oui c'est absolument acceptable »

**Option A retenue** : *stale-while-revalidate*. L'arrivée dashboard est servie
depuis le dernier instantané connu, le rafraîchissement s'exécute derrière.

### Périmètre précisé au moment de la réponse (et pourquoi)

La question posée décrivait « l'écran se corrige tout seul ~300 ms plus tard ».
**Côté `api-mail` seul, la correction est PASSIVE** : la route répond
instantanément et rafraîchit en arrière-plan, mais sans changement côté front la
valeur affichée ne se met à jour **qu'à la navigation suivante**.

Dans le parcours réel, cela reste utile et borné : le rafraîchissement se
termine en ~300 ms, et l'appel suivant du médecin — l'ouverture de l'inbox, 3 à
10 s plus tard — est déjà juste.

Une correction **visible sans navigation** exigerait un drapeau de fraîcheur
dans la réponse et un re-fetch côté client, ou une notification poussée : c'est
une US sur les **trois clients**, pas sur `api-mail`. **Elle est proposée
séparément et n'est pas embarquée ici.**

**Question soldée** — task-278 reprend son cycle.
