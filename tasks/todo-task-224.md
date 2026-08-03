# todo-task-224.md — Les tableaux de bord du banc ne doivent plus pouvoir afficher un chiffre faux

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune. Les trois défauts sont dans l'outillage de mesure
livré par task-174 / task-204 / task-221 ; aucun ne bloque **task-222** ni
**task-223**, dont les verdicts reposent sur le **rapport de tir** (correct)
et non sur ces tableaux.
**Priorité**: **3** — aucun chiffre publié n'est faux à ce jour, parce que le
verdict fait foi sur le rapport. Mais quatre défauts d'observabilité attendent
le premier lecteur qui regardera le tableau de bord, et cette EPIC a déjà payé
deux fois le prix d'un instrument qui mentait sans le dire.

## Objective

Qu'un opérateur qui lit le tableau de bord du banc, ou l'état des serveurs de
messagerie pendant une campagne, y voie soit le bon chiffre, soit l'absence
explicite de chiffre — jamais un chiffre faux ni un panneau vide qui se lise
« tout va bien ».

## Les quatre défauts — constatés le 2026-08-03 pendant la campagne de certification

**1. Les latences du tableau de bord sont affichées 1000× trop petites.**
Les panneaux « p95 par operation » et « p50 par operation » déclarent l'unité
**milliseconde** sur des séries que l'outil de tir publie en **seconde**
(convention du magasin de métriques). Un lecteur qui compare ce panneau à la
grille de temps de réponse attendus — qui, elle, est en millisecondes — conclut
que la messagerie est **mille fois plus rapide** qu'elle n'est. Tranché par
mesure directe, jamais par supposition : le magasin annonce `0,0097` pour un
appel que le chronomètre mesure à 5,5–11 ms ; en millisecondes cela ferait
9,7 microsecondes pour un aller-retour réseau, physiquement impossible.

**2. Le panneau « Taux d'erreur HTTP » du même tableau de bord est aveugle.**
Il interroge une métrique qui **n'existe pas** (nom erroné). Il n'affiche donc
rien — et **un panneau d'erreurs vide se lit « aucune erreur »**. C'est le mode
d'échec exact que task-204 avait déjà rencontré sur un autre compteur, et que
task-214 a nommé : « une absence n'est pas un zéro ».

**3. L'adresse complète de chaque appel sert d'étiquette de série.**
Chaque message ouvert, supprimé ou marqué crée donc **sa propre série**
(mesuré à mi-campagne : des dizaines par geste, et cela croît avec la population
et la durée). Deux conséquences constatées : les compteurs lus dans le magasin
sont **sous-estimés** (les séries touchées une seule fois sortent de la fenêtre
de fraîcheur — jusqu'à −61 % sur l'ouverture de messages froids, quand les
gestes à adresse fixe tombaient à ±1 % du modèle), et un percentile agrégé sur
ces séries **n'est plus un percentile**. L'outil de tir offre un mécanisme de
regroupement d'adresses qui n'est pas utilisé.

**4. L'état des serveurs de messagerie n'est plus relevé depuis qu'ils ont
quitté la machine de mesure.** L'échantillonneur interroge un conteneur local
qui n'existe plus (**task-221**). Il **journalise proprement l'échec** — ce qui
est le bon comportement — mais la ligne « sessions ouvertes » du rapport reste
vide, or c'est précisément le coût qui suit la **population**, l'axe central du
modèle par parcours. Pendant la campagne du 2026-08-03, la grandeur a dû être
obtenue par un contournement (compter les connexions sortantes de la
messagerie), qui a d'ailleurs révélé que le banc **surestimait ce coût d'un
facteur cinq** — un résultat qu'on a failli ne pas avoir.

## Ce qu'il ne faut PAS présumer

- **Ne pas multiplier l'expression du panneau par 1000.** La convention du
  magasin de métriques (unités de base) est la bonne ; c'est la **déclaration
  d'unité du panneau** qui est fausse. Corriger l'affichage, pas la donnée.
- **Ne pas se contenter de corriger le nom de la métrique d'erreur.** Ce
  panneau était faux depuis sa création sans que personne ne le voie, parce
  qu'un panneau vide ne se distingue pas d'un panneau à zéro. Le panneau doit
  **dire** quand il n'a pas de donnée.
- **Ne pas supprimer l'étiquette d'adresse sans réfléchir** : elle sert à
  distinguer les quatre appels du geste « arrivée sur le tableau de bord ». Ce
  qu'il faut, c'est **regrouper les adresses paramétrées** (par message, par
  dossier) sans perdre la distinction entre appels différents.
- **Ne pas faire dépendre le rapport de tir de ces tableaux.** Le rapport est
  et reste la source du verdict ; cette US répare les vues, elle ne déplace pas
  l'autorité.
- **Ne pas rendre la sonde des serveurs de messagerie obligatoire** : si le
  cluster est injoignable, la ligne doit dire « non relevé », jamais afficher un
  zéro ni faire échouer la campagne.

## Contenu attendu

1. **Unités des panneaux de latence** alignées sur ce que la donnée contient.
2. **Panneau de taux d'erreur** branché sur la métrique réelle, et **qui
   distingue « zéro erreur » de « pas de donnée »**.
3. **Regroupement des adresses paramétrées** dans les étiquettes de l'outil de
   tir, de sorte qu'un geste produise un nombre de séries **borné**, quelles que
   soient la population et la durée.
4. **Sonde de l'état des serveurs de messagerie en mode distant** : quand le
   banc pointe vers le cluster, la relever là-bas ; sinon comportement
   inchangé ; et en cas d'échec, écrire « non relevé ».
5. **Un contrôle qui échoue si un panneau déclare une unité incompatible avec
   sa métrique** — sans quoi le défaut reviendra au prochain panneau ajouté.

## Hors scope

- Le rapport de tir lui-même (`report.py`) : ses chiffres sont justes, en
  millisecondes, correctement agrégés — il n'est pas en cause.
- Les correctifs applicatifs désignés par la campagne (**task-222**, **task-223**).
- Toute nouvelle campagne de mesure : cette US répare l'instrument, elle ne
  mesure rien.

## Definition of Done

- [ ] Build passe (0 erreur)
- [ ] Tests passent (0 échec)
- [ ] Les panneaux de latence affichent une valeur **cohérente avec la grille de
      temps de réponse attendus** — vérifié en confrontant un panneau au rapport
      du même tir (preuve : les deux chiffres dans le `## Develop log`)
- [ ] Le panneau de taux d'erreur affiche la valeur réelle, et affiche
      explicitement « pas de donnée » quand la métrique est absente
- [ ] Le nombre de séries produites par un geste est **borné** : vérifié sur un
      tir court (le même geste sur 50 messages différents ne crée pas 50 séries)
- [ ] Les compteurs relus depuis le magasin de métriques concordent avec le
      rapport de tir à ±2 % sur **tous** les gestes du parcours (ils divergeaient
      jusqu'à 61 %)
- [ ] En mode distant, la ligne « sessions ouvertes des serveurs de messagerie »
      du rapport est **renseignée** ; cluster injoignable ⇒ « non relevé », et la
      campagne se poursuit
- [ ] En mode local, comportement **strictement inchangé** (vérifié)
- [ ] Un contrôle automatisé refuse un panneau dont l'unité déclarée est
      incompatible avec sa métrique
- [ ] `selftest.sh` vert (nouveaux contrôles inclus)

## Manual Test Plan

```bash
# 1. Banc distant + tir court au rythme accéléré (l'instrument suffit à valider)
cd Api/Mail
MSS_LOADTEST_MAIL_HOST=<ip-noeud> dotnet run --project src/AppHost --launch-profile https-load-test
dotnet run --project tests/mss.mail.loadtest.seed -- --users 20 --messages 50 \
  --api http://127.0.0.1:5052 --mail-host <ip-noeud> --latency 95
tests/loadtest-k6/observe.sh start 900
export BYPASS_KEY=loadtest-local-only MSS_LOADTEST_MAIL_HOST=<ip-noeud>
LATENCY_MS=95 USERS=20 MESSAGES_PER_USER=50 \
  JOURNEY_STAGES="10:5m" JOURNEY_TIME_COMPRESSION=10 \
  tests/loadtest-k6/run.sh journey
tests/loadtest-k6/report.sh <dernier json> --expected 0

# 2. Contre-épreuve du mode local (comportement inchangé)
tests/loadtest-k6/selftest.sh
```

**Ce que l'humain doit voir** :
- sur le tableau de bord du banc, panneau des latences : **les mêmes ordres de
  grandeur que le rapport de tir** (des centaines de millisecondes, pas des
  fractions de milliseconde) ;
- panneau de taux d'erreur : une valeur, et non un panneau vide ; en coupant la
  source de métriques, il affiche « pas de donnée » et non « 0 % » ;
- la légende du panneau par opération reste **lisible** : un petit nombre de
  courbes nommées par geste, pas une courbe par message ;
- dans le rapport, la ligne **« sessions ouvertes »** des coûts résidents est
  renseignée et croît avec le nombre de médecins ;
- sans la variable de banc distant : tout se comporte comme avant.

**Données de test** : boîtes `loadtest-*`, corpus synthétique, aucune donnée de
santé réelle.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville — outillage interne de mesure du service
  de messagerie MSSanté du praticien.
- **Vague Ségur** : hors vague — instrumentation interne, aucun impact
  fonctionnel ni d'interopérabilité.
- **Exigences DSR honorées** : aucune nouvelle.
- **INS** : non manipulée — identités virtuelles déterministes du banc.
- **Authentification PS** : non applicable — l'US ne touche ni l'authentification
  ni le contrôle d'accès ; le banc conserve son mécanisme de contournement,
  bloqué en production par construction.
- **Habilitations** : inchangées.
- **Interop CI-SIS** : non applicable.
- **Tracé PGSSI-S** : aucun évènement métier touché. ⚠️ **Garde-fou sur le
  regroupement d'adresses** : les étiquettes de métriques ne doivent porter **ni
  identifiant de message, ni nom de pièce jointe, ni adresse de praticien** — en
  messagerie de santé un nom de pièce jointe peut désigner le patient et
  l'examen (leçon de task-213). Le regroupement demandé va d'ailleurs dans ce
  sens : il **réduit** la donnée exposée.
- **Consentement patient** : non applicable.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : non — banc local et cluster de test interne, données
  synthétiques exclusivement. Aucun environnement de production touché.
- **AIPD / impact RGPD** : néant.
