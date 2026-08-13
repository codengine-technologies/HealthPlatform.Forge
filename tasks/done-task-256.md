# todo-task-256.md — La page d'en-têtes coûte 51 % de plus sans émettre une requête de plus : on déduit pourquoi, on ne le mesure pas

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: **task-243** (`archived`) — sa décomposition en phases a isolé
`assemble` ; celle-ci compte **ce que cette phase construit**. Aucune dépendance
bloquante ; **task-255** est indépendante (elle traite le débit, pas le coût par
appel).
**Priorité**: **1** — c'est la **seule étape du parcours encore hors grille à 200
praticiens** hors envoi, et son remède n'est pas décidable en l'état. Sans ce
compteur, la prochaine US d'optimisation devinerait.

## Objective

Que le coût de la page d'en-têtes soit attribuable à un **volume**, et pas seulement
à une durée. Aujourd'hui on sait **combien de temps** la matérialisation prend, et
**combien de requêtes** l'appel émet. On ne sait pas **combien d'objets il
construit** — donc on ne sait pas si le remède est « moins d'objets », « des objets
moins chers », ou « ne pas les construire ici ».

C'est une US **d'instrument, pas d'optimisation**. Elle ne rend rien plus rapide.

## Ce qui est établi — et qui rend cette US nécessaire

Deux tirs à protocole identique (escalier 50/100/200 distant, mêmes boîtes, chauffe
intégrée), `journey-247-proof` du 2026-08-09 puis `journey-lot254-n200` du
2026-08-10 :

| `GetMailsByUids` | 09-08 | 10-08 | |
|---|---|---|---|
| **Requêtes SQL par appel** | **15,8** | **15,8** | identique au millième |
| Matérialisation | 433,3 ms | **654,5 ms** | **+51 %** |
| Attente d'une connexion | 0,1 ms (0,0 %) | 0,1 ms (0,0 %) | négligeable, deux fois |
| Étape « ouvrir l'inbox », p95 à 200 | 1 380 ms ❌ | **3 154 ms** ❌ | +129 % |

**Le travail demandé n'a pas changé** — même nombre de requêtes, même code de
lecture. Ce qui a changé est le **volume de données à construire** : la chauffe
aboutit désormais pour **100 %** des médecins contre 94,5 %, et **plus vite**
(961 s contre 1 156 s), grâce à task-254. La fenêtre de régime contient donc plus de
contenu enrichi.

**Cette explication est une déduction, pas une mesure.** Elle est solide — trois
indices concordants — mais **aucun compteur ne dit combien d'objets l'appel a
construits**. Tant qu'il manque, « il y a plus de contenu » ne peut ni être vérifié,
ni être chiffré, ni servir à dimensionner un remède.

**Rappel du poids de l'enjeu** : la matérialisation vaut **83,7 %** du coût de cet
appel, et cet appel est le **premier poste du parcours du médecin** (finding
F-242-1, confirmé sur quatre campagnes).

## Ce que la US doit livrer

Le pendant, pour les **objets**, de ce que task-243 a fait pour les **requêtes** :
un compteur par appel, **ventilé par famille d'objet**, publié à côté de la durée de
la phase — de sorte que le rapport puisse rendre un **coût par objet**.

Les familles à distinguer sont celles que le dépôt charge en lots séparés : les
**messages** eux-mêmes, leurs **étiquettes**, leurs **destinataires**, leurs **pièces
jointes**, leurs **identifiants enrichis**, leurs **acquittements de biologie**. Ce
découpage n'est pas de la commodité : chacune désigne un remède différent, et c'est
le critère de découpage qu'a retenu task-252.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que le coût est proportionnel au nombre d'objets.** Il peut être
  dominé par **une seule** famille, par le suivi de changements d'EF, ou par une
  allocation par objet indépendante de sa taille. C'est précisément ce que la
  ventilation doit trancher.
- **Ne pas présumer que ce sont les messages.** La page en affiche 25 ; ce sont
  probablement les familles satellites qui font le volume. Le supposer d'emblée
  reviendrait à choisir le remède avant la mesure.
- **Ne pas optimiser en passant.** Si une évidence saute aux yeux, la consigner comme
  finding et la traiter dans une US suivante — mesurée. Cette EPIC a déjà annulé une
  US applicative écrite sur une cause plausible et fausse (task-222).
- **Ne pas re-mesurer ce qui l'est déjà** : le nombre de requêtes par appel (15,8) et
  la durée de la phase sont acquis. Cette US ajoute **le dénominateur qui manque**.

## Definition of Done

- [ ] Un compteur donne le **nombre d'objets matérialisés par appel** de
      `GetMailsByUids`, **ventilé** par famille (messages, étiquettes, destinataires,
      pièces jointes, identifiants enrichis, acquittements)
- [ ] Le même compteur couvre `GetMail`, l'autre lecture servie par la base — sans
      quoi on ne pourra pas comparer les deux chemins
- [ ] `report.py` publie le **coût par objet** et la **phrase attribuable** : « sur
      les X ms de matérialisation, l'appel a construit N objets, dont … »
- [ ] **Hors périmètre, rien ne coûte** : sans scope actif, ni allocation ni série
- [ ] Une absence de donnée écrit **« non relevé »**, jamais un zéro
- [ ] **Contre-épreuve chiffrée** : à corpus identique, le compteur explique-t-il
      l'écart de **+51 %** observé entre les deux tirs ? Si non, le rapport le **dit**
      — et c'est alors la déduction actuelle qui est fausse, ce qui est un résultat
- [ ] Tests unitaires du compteur, dont un cas « aucun objet » et un cas
      multi-familles
- [ ] **Aucune donnée de santé dans les étiquettes** : ni INS, ni objet de message,
      ni nom de fichier — seulement des noms de familles pris dans un ensemble fini

## Manual Test Plan

- Monter le banc (skill `loadtest-skill`), en mode **distant** — c'est la seule
  configuration honnête depuis le constat du 9 août
- Purger les tables, chauffer une boîte, puis ouvrir la boîte de réception depuis
  l'application : la liste doit afficher **exactement** les mêmes messages, avec les
  mêmes compteurs de fils, étiquettes et marqueurs de pièce jointe qu'avant
- Lire la section « Où part le temps d'une lecture servie par la base » : le nombre
  d'objets et le coût par objet doivent y figurer
- Ouvrir la même boîte **avant** puis **après** chauffe : le compteur d'objets doit
  augmenter, et la durée de matérialisation suivre — c'est la contre-épreuve
- Vérifier dans Seq qu'aucune étiquette ne porte de donnée patient

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — observabilité interne
- **Exigences DSR honorées** : aucune — aucun changement fonctionnel
- **INS** : ⚠️ les identifiants enrichis comptés par ce compteur **peuvent porter de
  l'INS**. Le compteur ne doit publier qu'un **nombre** et un **nom de famille** :
  aucune valeur d'identifiant, aucun sujet de message, aucun nom de fichier. C'est le
  point de vigilance n°1 de cette US, et un test doit l'épingler.
- **Authentification PS / Habilitations** : inchangées — le cloisonnement « une base
  par praticien » n'est pas touché
- **Consentement patient / Interop CI-SIS / MSSanté** : non applicable
- **Tracé PGSSI-S** : métriques d'exploitation uniquement, corrélées par `traceId`
- **Hébergement HDS** : l'instrument doit être transposable à l'environnement cible
- **AIPD / impact RGPD** : inchangé — aucune donnée nouvelle collectée, seulement des
  décomptes
