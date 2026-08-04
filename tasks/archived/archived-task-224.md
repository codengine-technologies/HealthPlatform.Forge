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

## Develop log

- **Repos touchés** : `api-mail` uniquement (harnais de mesure + tableaux de bord —
  **zéro fichier C#**). `dtos-mss` : branche vide, pas de PR, pas de publish NuGet.
  Aucun frontend (`**Single frontend**: true`).
- **Commits** :
  - `2042b3d` défaut 5 — la chauffe analyse, et le rapport refuse une étape mal nommée
  - `675c28c` défauts 1 & 2 — unités des panneaux, panneau d'erreurs aveugle, contrôles
  - `6927cc2` défaut 3 — adresses paramétrées regroupées
  - `e681869` défaut 4 + item 8 — sessions IMAP depuis le magasin, verdict requalifié
- **Build / tests** : `dotnet build` 0 erreur / 0 avertissement ; **146 tests
  Python**, **39 tests node**, `selftest.sh` vert. Côté .NET : 3 391 verts,
  **2 flaky pré-existants** (`Services/Export`, famille `UglyToad.PdfPig`
  documentée en v1.18) — vérifiés **31/31 en isolation**, et la task ne touche
  **aucun fichier C#**, ce qui exclut toute régression de son fait.

### Les cinq défauts

| # | État | Ce qui a été fait |
|---|---|---|
| **5** | ✓ | La chauffe passe par **l'analyse elle-même** (`enrich/sync`, un seul appel pour la bande), le commentaire fautif de `journey-model.js` est corrigé, et le rapport **refuse** désormais le verdict d'une étape « servie base » dont le décompte de sollicitations est non nul |
| **1** | ✓ | Unités `ms → s` sur les panneaux de latence — **et une seconde occurrence non listée dans la US**, trouvée par le contrôle |
| **2** | ✓ | Métrique corrigée (`_rate`, pas `_total` : `http_req_failed` est un Rate côté k6) **et `noValue` sur 77 blocs** des trois tableaux |
| **3** | ✓ | Gabarits d'adresse dans `lib/routes.js` (module pur), `name` posé sur 12 appels — cardinalité bornée par le nombre de routes |
| **4** | ✓ | Sessions IMAP lues dans le magasin (`mssante_imap_sessions_active`), sonde locale gardée prioritaire, « non relevé » si les deux se taisent |

### Trois choses que la US ne prévoyait pas, et qui comptent

**1. Le contrôle d'unité a trouvé une seconde occurrence du défaut 1.**
`saturation.json / « p95 serveur par route (ms) »` déclarait aussi la
milliseconde sur un `histogram_quantile` en secondes. Ce panneau est décrit par
sa **propre description** comme « le juge de l'attribution », à confronter au p95
client du tableau k6. Les deux étaient faux du **même** facteur : leur
confrontation semblait donc cohérente, et c'est la comparaison à la grille SLO
(en millisecondes) qui était fausse. Titre et unité corrigés.

**2. Mon contrôle d'unité était faux à la première écriture.** J'avais posé
« la métrique contient `_seconds` donc le panneau doit être en secondes ». C'est
faux : PromQL **change la dimension** — `rate(x_seconds_total[1m])` rend des
secondes par seconde, soit un ratio sans dimension (des cœurs, pour du CPU), où
`percentunit` et `none` sont légitimes. Dix faux positifs. Seul le **quantile
d'un histogramme** garantit la dimension de sortie, donc c'est la seule forme que
le contrôle juge. C'est consigné **à côté du code** plutôt que corrigé en
silence : un contrôle qui se trompe de dimension serait exactement le défaut
qu'il prétend empêcher.

**3. Le regroupement d'adresses réduit la donnée exposée.** Le gabarit retire le
**nom de la pièce jointe** de l'étiquette de série. En messagerie de santé, un
nom de pièce jointe désigne couramment le patient et l'examen (leçon de task-213
sur les clés de verrou). La US le mentionnait comme un garde-fou ; c'est en fait
un bénéfice direct, et un test le fige.

### Le contrôle qui empêche la récidive (item 7)

C'est la pièce la plus importante de cette task, plus que les cinq correctifs :
le rapport ne **croit** plus le nom d'une étape, il le **vérifie**.
`JOURNEY_SLO_GRID` porte `served_from_store` sur l'étape 3, et le verdict la
refuse si `mssante_mail_server_solicitations_total{operation="GetEmailContent"}`
est non nul. **Trois** états, et le troisième vaut autant que les deux autres :

- non nul → étape **refusée**, bandeau **avant** les tables, palier tombé ;
- nul → étape jugée normalement ;
- **absent** → « non vérifiée », **jamais lu comme zéro** (task-214 : une absence
  n'est pas un zéro — un binaire antérieur à task-225 ne publie pas ce compteur).

Sans lui, un chiffre **dans** la cible aurait été publié vert. C'est ce qui
transforme un artefact d'instrument en verdict refusé plutôt qu'en US applicative.

### DOD — auto-contrôle

| Critère | État |
|---|---|
| Build passe (0 erreur) | ✓ |
| Tests passent (0 échec) | ✓ 146 Python + 39 node + `selftest.sh` ; .NET 2 flaky pré-existants hors diff |
| Panneaux de latence cohérents avec la grille | ✓ unités corrigées, **2** occurrences ; confrontation au rapport d'un même tir → **déféré au banc** |
| Panneau de taux d'erreur : valeur réelle + « pas de donnée » | ✓ métrique `_rate` + `noValue` ; valeur réelle **à confirmer au banc** |
| Nombre de séries par geste **borné** | ✓ gabarits + 6 tests ; vérification sur tir court **déférée au banc** |
| Compteurs du magasin concordants à ±2 % sur tous les gestes | ⛔ **déféré au banc** |
| Ligne « sessions ouvertes » renseignée depuis le magasin | ✓ code + 4 tests ; concordance 94/195/401 **à confirmer au banc** |
| Métrique absente ⇒ « non relevé », jamais un zéro | ✓ test dédié |
| Mode local strictement inchangé | ✓ la sonde locale garde la priorité (test dédié) |
| Contrôle refusant une unité incompatible | ✓ `test_dashboards.py`, 5 tests |
| **Étape 3 : 0 sollicitation là où elle en enregistre 5** | ⛔ **déféré au banc** — les deux chiffres exigent un tir |
| Commentaire « le GET contenu matérialise le MailContent » disparu | ✓ dans `journey.js` **et** `journey-model.js` |
| Contrôle refusant une étape « servie base » au décompte non nul | ✓ 6 tests, dont le refus d'une étape **pourtant dans ses cibles** |
| Étape 3 annotée non opposable dans `INDEX.md` | ✓ ligne + note de lecture |
| Étape 4 mesurée sur des messages réellement froids | ✓ la chauffe ne touche que la bande chaude (bandes disjointes, budget inchangé) |
| `selftest.sh` vert | ✓ |

**Quatre critères sont déférés au banc**, et c'est structurel : ils exigent un tir
avec le nœud distant `MSS_LOADTEST_MAIL_HOST`, que la forge n'a pas. Le plus
important — « étape 3 : 5 sollicitations avant, 0 après » — est **la** preuve du
défaut 5, et elle se lit en une ligne du prochain rapport. Tout le reste est
couvert par test.

### Ce qui n'a pas été fait, volontairement

- **Les 16 findings Sonar new-code de `tests/loadtest-k6/`** (task-220) n'ont pas
  été touchés, bien que je rouvre ces fichiers. Les corriger mélangerait le
  nettoyage de dette d'une autre task avec cinq correctifs d'instrument, et
  `S3776` relève de `/sonar-s3776` (1 méthode = 1 PR) par construction.
- **Le rapport du 2026-08-03 n'est pas réécrit** : les JSON font foi, l'index est
  annoté. C'est ce que la US demande.

- **Étape suivante** : `/forge-simplify task-224`

## Simplify log

**Verdict : passe conduite** — contrairement à task-225, cette task n'interdit
pas la simplification.

| Axe | Fichier | Avant → après |
|---|---|---|
| Réutilisation | `report.py` | les deux nouveaux lecteurs de métrique répétaient `reduce_prom_matrix(((telemetry or {}).get("prom") or {}).get(clé), None)`. Un `prom_series(telemetry, clé)` partagé remplace les deux, et porte **une fois** la raison de la tolérance aux niveaux absents : un tir sans magasin joignable est un cas **normal**, pas une erreur |
| Réutilisation | `test_dashboards.py` | `panel_unit` et `panel_no_value` déroulaient la même descente `fieldConfig.defaults`. Un `panel_default(panel, clé)` la porte, et le prochain accesseur sera une ligne |

**Examiné et laissé tel quel** :

- la boucle de construction des UIDs chauds dans `warmUpOwnMailbox` — trois
  lignes explicites, un `Array.from({length})` n'y gagnerait rien de lisible ;
- `isBoundedRoute` — déjà une expression ;
- les 12 appels passant `ROUTES.x` en 5ᵉ argument — un objet d'options serait
  plus élégant mais toucherait 12 sites d'appel **et** la signature partagée avec
  la voie `mixed`, pour un gain cosmétique. Le contrat de périmètre de la task
  n'interdit pas ce refactoring, mais il n'apporte rien à la lisibilité du diff.

Re-validation : **146 tests Python + 39 node verts**, `selftest.sh` inclus.
Aucun rollback. Commit `f54dcec`.

- **Étape suivante** : `/sonar task-224` (api-mail touché).

## Lint / verify-visual log

Les trois étapes frontend **skippent proprement** : `**Repos**: api-mail` et
`**Single frontend**: true` — la US répare l'outillage de mesure du backend,
aucun frontend n'est touché.

| Étape | Verdict | Constat |
|---|---|---|
| `/lint-angular` | **skip** | `Client/Angular` porte deux `environments/environment.ts` modifiés non commités — **travaux en cours de l'humain**, pas de task-224. La forge n'a écrit aucune ligne d'Angular ; lancer la passe lint retoucherait ce WIP. |
| `/lint-mobile` | **skip** | `Client/Mobile` sur `develop`, arbre propre, aucun diff. Non listé dans `**Repos**:`. |
| `/verify-visual` | **skip** | Aucun écran mobile touché. |

## Sonar log

Mode A (chaîné), **2 itérations**. Projet `healthplatform`, branche
`fix/task-224-bench-instrument-truthful`.

**Pourquoi deux itérations sans aucune correction entre elles** : l'itération 1 a
tourné sur `f54dcec`, avant l'extraction de constante `b22f857`. Mesurer un commit
qui n'est pas celui qu'on merge serait ironique sur une task dont l'objet est la
véracité des instruments — l'itération 2 porte donc sur **HEAD**. Les deux donnent
le même résultat.

### KPIs qualité — baseline → final (mesuré sur HEAD)

| Métrique | Baseline (avant task-224) | Final | Cible LT |
|---|---|---|---|
| Bugs | 1 | **1** | 0 |
| Vulnerabilities | 0 | **0** | 0 ✓ |
| Security Hotspots (à revoir) | 1 | **1** | 0 |
| Code Smells | 18 | **18** | — |
| Coverage | 86,9 % | **86,9 %** | ≥ 95 % |
| Duplication | 0,5 % | **0,5 %** | — |
| Reliability rating | C | **C** | A |
| Security rating | A | **A** | A ✓ |
| Maintainability rating | A | **A** | A ✓ |
| ncloc | 41 369 | 41 666 | — |
| **Quality Gate** | ERROR | **ERROR** | OK |

`new_coverage` et `new_duplicated_lines_density` reviennent à `None` : le new code
de ce tir est **entièrement du Python et du JavaScript de harnais**, exclu de la
couverture (`sonar.coverage.exclusions` couvre `**/tests/**`). Ce n'est pas une
régression de couverture — c'est l'absence de code C# neuf.

### Zero-new-debt : tenu, et vérifié par provenance et non par total

Le total des `new_violations` est **inchangé à 18**, mais un total inchangé ne
prouve rien à lui seul : task-224 **rouvre précisément les fichiers** qui portent
ces 18 findings (`report.py`, `journey.js`, `journey-model.js`), et y insère du
code — donc **leurs numéros de ligne bougent** et les mêmes findings ressemblent à
des nouveaux. La comparaison a donc été faite par **(règle, fichier)**, relevée
avant l'analyse :

| Fichier | Baseline | Après | Δ |
|---|---|---|---|
| `report.py` | S1192 ×2, S3776 ×6, S1244 ×1, S3358 ×1 | identique | **0** |
| `lib/journey-model.js` | S1940 ×2, S6035 ×1 | identique | **0** |
| `scenarios/journey.js` | S1940 ×1, S3776 ×1, S4624 ×1 | identique | **0** |
| `BaseRepository.cs`, `IIheXdmProcessingService.cs` | S103 ×2 (task-218 / task-185) | identique | **0** |
| **Fichiers neufs** — `lib/routes.js`, `lib/routes.test.mjs`, `test_dashboards.py` | — | **aucun finding** | **0** |

**Zéro finding attribuable à task-224.** Notons que les trois fichiers neufs
(+321 lignes de JS et de Python) n'en produisent aucun : les conventions
`javascript.md` et `python.md` ont été lues avant d'écrire, ce qui est leur seule
raison d'être.

### Une honnêteté sur l'extraction de constante

J'ai extrait `IMAP_SESSIONS_KEY` **avant** l'analyse, parce que
`conventions/python.md` (S1192) impose la constante dès 3 occurrences et que la
clé était citée 5 fois. **Sonar ne l'aurait pas signalée** : le compte de `S1192`
sur `report.py` est resté à 2 dans les deux itérations. L'extraction reste
conforme à la convention et justifiée sur le fond — une faute de frappe sur l'une
des cinq occurrences rendrait `None` sans rien dire, soit le défaut 2 de cette
task transposé au code — mais je ne la présenterai pas comme un finding évité.

### Le Quality Gate est ERROR, et aucune de ses causes n'est de task-224

- `new_violations = 18 > 0` — provenance ci-dessus : **16 → task-220** (le harnais
  de mesure, dont l'unique `BUG` `python:S1244` et l'unique hotspot
  `javascript:S2245`), **2 → task-185 / task-218**, **0 → task-224**.
- `new_security_hotspots_reviewed = 83,3 % < 100 %` — le hotspot restant est le
  `Math.random()` de `journey.js`, de task-220.

**Phase 2 legacy volontairement non lancée**, et le motif est propre à cette task :
je rouvre le code du harnais, mais y corriger la dette de task-220 mélangerait ce
nettoyage avec cinq correctifs d'instrument sur la même branche — c'est exactement
le mélange qui a coulé task-222. Les 9 `S3776` relèvent par ailleurs de
`/sonar-s3776` (1 méthode = 1 PR) par construction.

### Tests .NET pendant les analyses

Un flaky `Services/Export` par run Release (`MarkdownPdfRendererTests` à
l'itération 1, `MailExportServiceTests` à l'itération 2 — la famille
`UglyToad.PdfPig` documentée en v1.18). **task-224 ne touche aucun fichier C#**,
ce qui exclut mécaniquement une régression de son fait ; 31/31 en isolation.

### Note pour les fichiers de conventions

Aucune entrée nouvelle : aucune règle n'a eu besoin d'être corrigée manuellement
sur du code frais. Les entrées existantes de `python.md` (S1192) et
`javascript.md` (S4624, S6582, S3863) ont servi en prévention.

- **Étape suivante** : `/review task-224`

## PRs

- `api-mail` : **https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/152** — label `awaiting-human-merge`
- `dtos-mss` : **aucune PR** — branche sans commit (auto-inclusion).
- Aucun frontend concerné (`**Single frontend**: true`).

## Code Review Summary

**Verdict : APPROVED** — 13 fichiers revus, **0 bloquant**, 1 risque à surveiller
au banc, 1 suggestion.

| Zone | Verdict |
|---|---|
| `journey.js` — chauffe par `enrich/sync` | ✓ un seul appel pour la bande ; `'warmup'` était déjà un op déclaré, aucun seuil cassé ; bandes disjointes, l'étape 4 reste sur du vrai froid |
| `report.py` — contrôle de l'étape mal nommée | ✓ 3 états, `mislabel` hors de l'early-return des tirs non opposables ; bandeau **avant** les tables |
| `report.py` — sessions depuis le magasin | ✓ sonde locale prioritaire (test dédié), « non relevé » jamais un zéro |
| `lib/routes.js` — gabarits | ✓ module **pur**, donc testable par node ; tags de l'appelant **copiés** (sinon le `name` fuitait d'un geste sur le suivant) |
| Tableaux de bord | ✓ unités corrigées (2 occurrences), métrique `_rate`, `noValue` sur 77 blocs |
| `test_dashboards.py` — contrôles | ✓ le modèle dimensionnel a été corrigé **et documenté** après 10 faux positifs |
| Sécurité / PGSSI-S | ✓ le gabarit **retire** le nom de pièce jointe des étiquettes — bénéfice, pas seulement garde-fou ; test dédié |

### ⚠️ Risque à surveiller au tir — le coût de la chauffe a changé d'ordre de grandeur

Conséquence directe du correctif du défaut 5, chiffrée plutôt que découverte :
15 `GET contenu` légers deviennent **1 `enrich/sync` de 15 UIDs**, soit **~65 s de
pipeline CDA par VU** contre quelques centaines de ms. `JOURNEY_PALIER_TRIM_S` ne
rogne que 10 s : le premier palier pourrait voir de la charge de chauffe dans sa
fenêtre.

Borné par le fait que `ramping-vus` échelonne les démarrages — la chauffe est
étalée, pas simultanée. Symptôme à guetter : premier palier dégradé sans raison
applicative. Remèdes, du moins au plus structurel : relever le rognage ; baisser
`JOURNEY_WARM_SHARE` ; ou **faire enrichir la bande chaude par le seed**, hors
bande, au lieu que chaque VU la refasse (le bon à terme, mais il touche
`mss.mail.loadtest.seed`, hors périmètre).

**Ne pas enrichir est le défaut lui-même** : le correctif reste le bon choix.

### Suggestion non bloquante

`store_served_solicitation_rate` est appelé deux fois par verdict. Deux lectures de
dictionnaire en mémoire — négligeable, et `/review` est en lecture seule sur le code.

### Validation

| | Résultat |
|---|---|
| Build | ✓ 0 erreur |
| Tests harnais | ✓ **146 Python + 39 node**, `selftest.sh` vert, **20 tests ajoutés** |
| Tests .NET | ✓ 3 391 verts ; 1 flaky pré-existant par run (`Services/Export`), **aucun fichier C# dans le diff** |
| Sync `develop` | ✓ `Already up to date` (merge, pas rebase) |
| Sonar | ✓ **zéro finding attribuable**, vérifié par (règle, fichier) et non par total |
| DOD | 11/15 ✓ ; **4 déférés au banc** (nœud distant absent) |

## Merged

**Mergé le 2026-08-04** par l'humain via `/merge task-224 --i-tested` (HAG,
CLAUDE.md règle 10 — attestation explicite du plan de test manuel).

| Repo | PR | Squash commit |
|---|---|---|
| `api-mail` | [#152](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/152) | `aab6297` fix(loadtest): les tableaux de bord du banc ne peuvent plus afficher un chiffre faux |
| `dtos-mss` | aucune PR (branche sans commit) | — |

- **Barrières de sécurité** : toutes vertes — CI `build` SUCCESS,
  `mergeable=MERGEABLE` / `mergeStateStatus=CLEAN`, aucun `CHANGES_REQUESTED`,
  pas de label `awaiting-us-completion`, arbre local propre, 6 commits d'avance /
  0 de retard sur `develop`.
- **Squash-merge** (`gh pr merge --squash`, jamais `--delete-branch`) : ref
  **distant** supprimé, branche **locale conservée**. Branche vide de `dtos-mss`
  nettoyée des deux côtés.
- **CI `develop` après merge** : ✅ verte (run `30890907346`, `aab62975`) —
  dans la fenêtre de 2 minutes (règle 5). Seul avertissement : dépréciation
  Node 20 des actions GitHub, antérieure et sans lien.
- **`client-angular`** : aucune opération git, aucune question — code-only, et
  cette task ne touchait aucun frontend.

### Ce qui est désormais sur `develop`

Les cinq défauts d'instrument sont corrigés, mais l'acquis qui compte le plus est
le **contrôle** : le rapport de tir ne croit plus le nom d'une étape, il le
**vérifie**, et refuse son verdict quand le serveur de messagerie a été sollicité
là où il n'aurait pas dû l'être. Sans lui, un chiffre **dans** la cible aurait été
publié vert — c'est ce qui a permis à un artefact de mesure de devenir une US
applicative (task-222, annulée).

Le verdict de l'étape 3 du tir du 2026-08-03 est requalifié **non opposable** dans
`reports/INDEX.md`.

### Suite immédiate, et elle est mesurable en une ligne

Le prochain tir `journey` doit montrer **zéro sollicitation** sur l'étape 3, là où
elle en enregistre **cinq** aujourd'hui. C'est *la* preuve du défaut 5, et le
premier des quatre critères de DOD déférés au banc.

⚠️ **À surveiller au même tir** : le coût de la chauffe est passé à ~65 s de
pipeline CDA par VU (contre quelques centaines de ms), alors que le rognage de
fenêtre n'est que de 10 s. Symptôme à guetter : premier palier dégradé sans raison
applicative. Remède structurel si constaté — faire enrichir la bande chaude par le
seed, hors bande.
