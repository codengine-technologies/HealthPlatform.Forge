# todo-task-224.md — Les tableaux de bord du banc ne doivent plus pouvoir afficher un chiffre faux

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune.

> ⚠️ **Révisé le 2026-08-04 — cette US bloque désormais une mesure.** Il était
> écrit ici qu'« aucun [défaut] ne bloque **task-222** [...] dont les verdicts
> reposent sur le **rapport de tir** (correct) ». **C'est faux**, et le défaut 5
> ci-dessous l'établit : le rapport de tir était correct sur ce qu'il mesurait,
> mais l'étape 3 du parcours ne mesurait pas ce que son nom annonce.
>
> **task-222 a été ANNULÉE** le 2026-08-04 (trop de modifications non maîtrisées ;
> PR fermée, branche supprimée). Son seul acquis — le décompte des sollicitations
> du serveur — est repris par **task-225**. Les critères de DOD de cette US-ci qui
> s'appuient sur ce décompte **dépendent donc de task-225** ; les quatre défauts
> d'affichage n'en dépendent pas et restent traitables indépendamment.

**Priorité**: **2** — relevée de 3. Le défaut 5 n'est plus un défaut d'affichage
qui attend un lecteur : il a **rendu un verdict non opposable** et failli faire
merger un correctif applicatif qui aurait supprimé le décodage CDA. Cette EPIC a
maintenant payé **trois** fois le prix d'un instrument qui mentait sans le dire.

## Objective

Qu'un opérateur qui lit le tableau de bord du banc, ou l'état des serveurs de
messagerie pendant une campagne, y voie soit le bon chiffre, soit l'absence
explicite de chiffre — jamais un chiffre faux ni un panneau vide qui se lise
« tout va bien ».

## Les cinq défauts — constatés pendant et après la campagne de certification du 2026-08-03

**5. L'étape « relire un message enrichi » ne mesure pas un message enrichi.**
*(Ajouté le 2026-08-04, et placé en tête par gravité : les quatre autres
faussent une lecture, celui-ci a faussé un verdict.)*

Le scénario `journey` **n'appelle jamais l'enrichissement** — son propre
commentaire le dit :

```js
// Sans gravité pour CE tir — journey n'appelle jamais enrich — mais le seed
// ne doit pas être partagé avec un tir enrich/mixed sans reset-state.
```

Et sa chauffe (`warmUpOwnMailbox`) prépare la bande de relecture avec
`getEmailContent`, en affirmant :

```js
/**
 * Premier passage d'un VU : chauffe la bande de relecture de SA boîte (le
 * GET contenu matérialise le MailContent) …
 */
```

**Cette parenthèse est fausse.** Le chemin de lecture n'écrit pas dans le stock,
et **ne doit pas** y écrire : la présence d'une ligne de contenu est le
**marqueur d'analyse** du message. La bande dite « chaude » n'est donc jamais
analysée, et l'étape 3 « ouvrir un message enrichi (servi base) » mesure
l'ouverture d'un message **jamais analysé** — un aller-retour complet vers le
serveur, comportement normal et attendu dans ce cas.

Ce que cela a coûté :

- **Le verdict de l'étape 3 du 2026-08-03 est non opposable** — 440 ms pour une
  cible de 100, à comparer aux 442 ms de l'étape 4 « message froid ». Les deux
  étapes mesuraient la même chose ; l'égalité n'était pas un symptôme, c'était
  la signature de l'artefact.
- **Une US applicative a été écrite sur ce chiffre** (task-222, depuis
  **annulée**) et son correctif serait allé jusqu'au merge : il faisait écrire le
  contenu à la lecture, donc écartait le message de l'analyse ⇒ **CDA jamais
  décodé, aucun document médical, aucun rattachement patient**, et le poste du
  médecin recevait l'annonce « analyse terminée ». Le défaut a été arrêté en
  relecture humaine. Voir `questions/task-222.md`.
- **Les 34 ms de la pièce jointe du même message n'infirmaient rien** : les
  pièces jointes sont des octets mis en cache, sans sémantique d'analyse. Ce
  faux contre-exemple a renforcé la mauvaise lecture.

Levier de vérification (⚠️ **livré par task-225**, pas encore disponible) : le compteur
`mssante_mail_server_solicitations_total{operation="GetEmailContent"}`. **Une
étape annoncée « servie base » qui incrémente ce compteur ne mesure pas ce
qu'elle annonce.**

---

## Les quatre défauts d'affichage — constatés le 2026-08-03 pendant la campagne

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
  l'autorité. ⚠️ **Mais ne pas en déduire que le rapport est à l'abri** : le
  défaut 5 montre qu'un rapport parfaitement calculé peut rendre un verdict faux
  si l'étape mesurée n'est pas celle que son nom annonce. La justesse du calcul
  ne garantit pas la justesse du sujet.
- **Ne pas « chauffer » la bande de relecture en écrivant le contenu depuis la
  lecture.** C'est la voie qui a failli passer, et elle est interdite : la
  présence du contenu en base signifie « message analysé », et le poser trop tôt
  supprime le décodage CDA. La chauffe doit passer par **l'enrichissement lui-même**
  (`POST …/emails/enrich/sync` sur les UIDs de la bande chaude), qui est le seul
  producteur légitime de cet état.
- **Ne pas se contenter de corriger le commentaire fautif du harnais.** Un
  commentaire juste devant un comportement faux ne mesure toujours rien : ce qu'il
  faut, c'est que la chauffe **enrichisse réellement**, et qu'un contrôle le
  vérifie.
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
4. **La ligne « sessions ouvertes » du rapport, remplie à la source.**
   ⚠️ **Correction apportée après l'analyse fine de la campagne** : la
   messagerie publie déjà `mssante_imap_sessions_active` / `_connected` /
   `_authenticated`, vérifiées concordantes à 2 % avec un comptage indépendant
   (94 / 195 / 401 aux trois paliers). **La ligne peut donc être remplie depuis
   le magasin de métriques, sans aucun accès au cluster** — c'est la voie à
   privilégier, plus simple et plus fidèle que la sonde distante.
   Reste utile mais secondaire : relever ce qui est propre au serveur de
   messagerie (charge du pod, connexions refusées) là où il tourne ; en cas
   d'échec, écrire « non relevé », jamais un zéro.
5. **Un contrôle qui échoue si un panneau déclare une unité incompatible avec
   sa métrique** — sans quoi le défaut reviendra au prochain panneau ajouté.
6. **La bande de relecture du parcours réellement analysée avant la mesure.**
   La chauffe doit passer par l'enrichissement (`POST …/emails/enrich/sync` sur
   les UIDs de la bande chaude), et le commentaire fautif de `warmUpOwnMailbox`
   doit disparaître. L'artefact de chauffe reste assumé et tagué hors grille SLO,
   comme aujourd'hui — ce qui change est qu'il produise l'état qu'il annonce.
7. **Un contrôle qui refuse une étape mal nommée.** Toute étape déclarée « servie
   base » dont le décompte de sollicitations du serveur est non nul doit faire
   **échouer le rapport** (ou au minimum marquer son verdict non opposable, à
   l'image de ce que le rapport fait déjà pour un tir à rythme accéléré). C'est ce
   contrôle qui empêche un artefact de ce genre de redevenir une US applicative.
8. **Le verdict « étape 3 » du rapport du 2026-08-03 requalifié** dans
   `reports/INDEX.md` : non opposable, avec le motif. Ne pas réécrire le rapport
   (les JSON font foi), annoter l'index.

## Hors scope

- Le rapport de tir lui-même (`report.py`) : ses chiffres sont justes, en
  millisecondes, correctement agrégés — il n'est pas en cause.
- Les correctifs applicatifs désignés par la campagne (**task-223**) ; **task-222 est annulée** et son instrumentation est portée par **task-225**.
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
- [ ] La ligne « sessions ouvertes » du rapport est **renseignée depuis le
      magasin de métriques**, en mode local comme distant, et concorde avec les
      chiffres de la campagne du 2026-08-03 (94 / 195 / 401 aux paliers 50 / 100 / 200)
- [ ] Métrique absente ⇒ la ligne écrit « non relevé », **jamais un zéro**, et la
      campagne se poursuit
- [ ] En mode local, comportement **strictement inchangé** (vérifié)
- [ ] Un contrôle automatisé refuse un panneau dont l'unité déclarée est
      incompatible avec sa métrique
- [ ] **La bande de relecture du parcours est réellement analysée avant la
      mesure** — preuve par le décompte : sur un tir court, l'étape 3 enregistre
      **zéro** `mssante_mail_server_solicitations_total{operation="GetEmailContent"}`,
      là où elle en enregistre 5 aujourd'hui (les deux chiffres dans le
      `## Develop log`)
- [ ] Le commentaire « le GET contenu matérialise le MailContent » de
      `warmUpOwnMailbox` a disparu, et rien d'équivalent ne l'a remplacé
- [ ] **Un contrôle refuse une étape « servie base » dont le décompte de
      sollicitations est non nul** — vérifié en le constatant ROUGE avec la
      chauffe actuelle, puis VERT avec la chauffe corrigée
- [ ] L'étape 3 du rapport du 2026-08-03 est **annotée non opposable** dans
      `reports/INDEX.md`, avec son motif
- [ ] **L'étape 4 « message froid » reste mesurée sur des messages réellement
      froids** — la chauffe ne doit pas empiéter sur la bande froide (le budget de
      bandes existant est à respecter, cf. `journeyBands`)
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
- **l'étape 3 « ouvrir un message enrichi (servi base) » est enfin ce que son nom
  dit** : son décompte de sollicitations du serveur est à **zéro**, et son temps
  s'effondre par rapport aux 440 ms du 3 août — non pas parce que le produit a
  changé (il n'a pas changé), mais parce qu'on mesure enfin un message analysé ;
- l'étape 4 « message froid » reste dans sa cible : la chauffe n'a pas mangé la
  bande froide ;
- en cassant volontairement la chauffe (revenir à l'ancienne), le rapport
  **refuse** le verdict de l'étape 3 au lieu de publier un chiffre ;
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

## Branches

- `api-mail` (pushed) : `fix/task-224-bench-instrument-truthful` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-224-bench-instrument-truthful
- `dtos-mss` (pushed, auto-inclus) : même nom de branche — aucun changement de contrat attendu, donc pas de PR si aucun commit.

> **Dépendance levée le 2026-08-04** : **task-225 est mergée** (`eec2cfd` sur
> `develop`). Le compteur
> `mssante_mail_server_solicitations_total{operation="GetEmailContent"}` est donc
> disponible sur cette branche, et les critères de DOD du **défaut 5** qui
> s'appuient sur lui sont **observables** — c'était la raison de l'ordre
> 225 → 224.
