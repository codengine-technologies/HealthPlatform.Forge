# todo-task-254.md — Traiter un message coûte 2,7 secondes, dont 97 % à aller le chercher

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: **task-245** (`archived`) — c'est elle qui a rendu ce coût
décomposable, et sans elle cette US n'aurait pas pu être écrite. **task-253**
(chauffe) est requise pour **prouver** le gain au banc, pas pour développer.
**Priorité**: **1** — c'est le goulot **G1**, le seul de la campagne 500 qui rompe
franchement (abandon, pas dégradation), et sa cause est maintenant mesurée.

## Objective

Réduire le coût de traitement d'un message reçu, en s'attaquant au poste que la
mesure désigne : **le téléchargement du corps depuis le serveur IMAP**.

C'est une US **d'optimisation**, et elle n'existe que parce que task-245 a
instrumenté. La cause n'est pas supposée : elle est chiffrée, et le candidat que
tout le monde aurait corrigé d'abord est écarté par un facteur 237.

## Ce qui est établi — mesuré, pas supposé

Tir `enrich-245-n100` du 2026-08-09, 100 médecins en mode distant, instrument de
task-245 :

| Phase d'un enrichissement | Moyenne par message | Part |
|---|---|---|
| **Fetch IMAP du corps** | **2 612,7 ms** | **97,1 %** |
| Écritures base | 35,4 ms | 1,3 % |
| Extraction de l'archive XDM | 20,4 ms | 0,8 % |
| **Parsing CDA** | **11,0 ms** | **0,4 %** |
| Le reste (DTO, notifications) | 10,4 ms | 0,4 % |
| **Total** | **2 691,7 ms** | (6,0 messages par requête) |

**Le mécanisme de la sérialisation**, table des verrous du même tir :
`EnrichEmails` **détient `imap_session` 29,68 s en p95**, à 15,93 acquisitions par
seconde. Ce verrou sérialise **toutes** les opérations IMAP d'une session, pas
seulement les lectures entre elles — l'enrichissement tient donc la session du
médecin pendant qu'il télécharge.

**Conséquence observée** : le débit d'enrichissement plafonne autour de
**9,5 messages/s** quelle que soit la concurrence. Pré-chauffe du 2026-08-09 —
**0,59 s/message** à 4 requêtes parallèles, **2,11 s** à 20 : multiplier la
concurrence par 5 ne gagne que **40 %** de débit.

**Effet produit, à deux échelles** : la chauffe de 98 messages a expiré pour
**500 médecins sur 500** au tir 500, et un lot de traitement de **2 messages** a
expiré une fois au palier 500. Côté médecin, c'est l'attente entre « un message
arrive » et « je peux le lire enrichi ».

## Ce qu'il ne faut PAS présumer

- **Ne pas toucher au parsing CDA.** Il pèse **0,4 %**. C'est écrit ici parce que
  c'est le réflexe attendu, et il ne rendrait rien.
- **Ne pas présumer que c'est la latence réseau et qu'on n'y peut rien.** 94 ms de
  latence injectée × quelques allers-retours ne font pas 2,6 s : il faut établir
  **combien d'allers-retours IMAP** un enrichissement émet par message. Cette
  grandeur manque encore — la mesurer fait partie de cette US.
- **Ne pas présumer que le corps n'est téléchargé qu'une fois.** À vérifier : un
  corps déjà présent en base est-il re-téléchargé ?

## Les trois pistes que la mesure désigne

À instruire dans cet ordre, en mesurant l'effet de chacune :

1. **Grouper les allers-retours** — récupérer les corps de plusieurs UID en une
   commande `FETCH` plutôt qu'un aller-retour par message. C'est la piste la plus
   directe si le décompte d'allers-retours confirme un appel par message.
2. **Ne pas tenir `imap_session` pendant le téléchargement** — ou donner à
   l'enrichissement une voie dédiée, comme task-213 l'avait fait pour l'écriture.
   29,68 s de détention est la cause directe de la sérialisation. ⚠️ task-213 a
   montré qu'une voie dédiée **double les sessions IMAP par praticien** : le
   plafond `mail_max_userip_connections` et le dimensionnement Dovecot doivent
   entrer dans l'arbitrage.
3. **Ne pas re-télécharger ce qui est déjà là** — si le corps est déjà en base.

## Definition of Done

- [ ] Le **nombre d'allers-retours IMAP par message enrichi** est mesuré et rendu
      (grandeur manquante aujourd'hui — sans elle, la piste 1 n'est pas décidable)
- [ ] La phase `fetch IMAP` d'un enrichissement est **réduite**, et le gain est
      **prouvé par un A/B iso-conditions** sur la lignée courante : même corpus,
      même population, un seul facteur, décomposition task-245 avant et après
- [ ] La détention de `imap_session` par `EnrichEmails` est **mesurée** avant/après ;
      si la piste 2 est retenue, l'effet sur le **nombre de sessions IMAP par
      praticien** est mesuré lui aussi (coût résident, table « contre N »)
- [ ] Le débit d'enrichissement **croît avec la concurrence** : le plateau à
      ~9,5 messages/s est franchi, chiffre à l'appui
- [ ] Aucune régression fonctionnelle : le **même** nombre de documents cliniques
      est extrait des mêmes messages, avec le même contenu — tests écrits **avant**
      le correctif, sur un message mono-document, un multi-documents, et une
      archive sans CDA exploitable
- [ ] Aucun message analysé n'est perdu ni dupliqué en cas d'échec partiel du lot

## Manual Test Plan

- Monter le banc, purger les tables, prendre un praticien du banc
- Déclencher le traitement d'un lot de 10 messages frais, puis ouvrir chacun d'eux
  dans l'application : **tous** doivent afficher leurs documents cliniques, avec
  les mêmes valeurs qu'avant le correctif (patient, date, contenu du CDA)
- Vérifier que l'archive IHE_XDM téléchargée depuis l'application s'ouvre toujours
- Comparer la section « Où part le temps d'un enrichissement » du rapport avant et
  après, sur le même corpus
- Relever le nombre de sessions IMAP du praticien (`doveadm who`) avant/après : il
  ne doit pas croître silencieusement

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — performance du traitement des messages reçus
- **Exigences DSR honorées** : aucune exigence nouvelle. ⚠️ La US touche le chemin
  qui **extrait les documents cliniques d'un message MSSanté** : toute perte,
  troncature ou duplication serait une atteinte à la donnée de santé et prime sur
  tout gain de performance. C'est le risque fonctionnel n°1.
- **INS** : les CDA extraits portent l'INS du patient — un regroupement de fetch ne
  doit **jamais** associer le corps d'un message au mauvais UID, ni mélanger deux
  praticiens. Un test doit le prouver explicitement.
- **Interop CI-SIS** : volet transport MSSanté / IHE-XDM et volet contenu CDA r2 —
  le contenu extrait doit rester identique **octet pour octet** sur le corpus de test
- **Habilitations** : cloisonnement « une base par praticien » inchangé ; si une voie
  IMAP dédiée est retenue, elle doit s'authentifier comme le praticien et lui seul
- **MSSanté** : ⚠️ le plafond de connexions IMAP par utilisateur de l'opérateur est
  une contrainte **externe** — une voie dédiée qui double les sessions doit être
  arbitrée contre ce plafond, pas seulement contre la latence
- **Authentification PS / Consentement patient** : inchangés
- **Tracé PGSSI-S** : aucun contenu CDA en clair dans les journaux ajoutés
- **Hébergement HDS** : le gain doit être transposable à l'environnement cible ; le
  banc local n'est pas la cible et ses latences IMAP ne sont pas celles de production
- **AIPD / impact RGPD** : inchangé — aucune donnée nouvelle collectée

## Branches
- `api-mail` (pushed) : feat/task-254-enrich-imap-fetch
- `dtos-mss` (pushed, auto-inclus) : feat/task-254-enrich-imap-fetch — aucun changement de contrat attendu

## Develop log — étape 1/2 : l'instrument (le livrable gatant du DOD)

- **api-mail** `feat/task-254-enrich-imap-fetch` @0b3f4e6 — poussé.
- **dtos-mss** — branche créée, aucun commit.

### Ce qui est livré

Le **nombre d'allers-retours IMAP par message enrichi** — premier critère du DOD,
et explicitement gatant : « sans lui, la piste 1 n'est pas décidable ».

Le compteur de sollicitations existait (task-225) mais **n'était câblé que sur
`GetEmailContent` et le SMTP** : le chemin d'enrichissement n'en publiait aucune.
Il l'est désormais aux 6 emplacements qui parlent au serveur, avec le **même
vocabulaire** que `GetEmailContent` — c'est ce qui rend les deux voies comparables.
Le dénominateur existait déjà (task-245) : **aucun nouvel instrument nécessaire**.

### ⚠️ CE QUE LA MESURE CHANGE — l'ordre des pistes doit être revu

**3 allers-retours `FETCH BODY[..]` par message**, un **par partie** (texte, HTML,
archive). Les résumés, eux, sont **déjà groupés** : un seul `FETCH` par sous-lot.

Conséquence à confronter au banc, mais elle saute aux yeux : à **94 ms** de latence
injectée, 3 allers-retours coûtent **~282 ms**, soit **~11 %** des 2 612,7 ms du
fetch. **La piste 1 (grouper les commandes) ne peut donc pas rendre l'essentiel** —
elle plafonne à ~11 % du poste, ~10 % du total.

Les ~2 330 ms restantes sont du **transfert** (l'archive pèse ~124 Ko contre
quelques Ko pour un corps) et/ou de la **sérialisation** — et c'est exactement ce
que désigne l'autre chiffre du tir : `EnrichEmails` **détient `imap_session`
29,68 s en p95**. La **piste 2** (ne pas tenir la session pendant le téléchargement)
devient donc le levier principal, et non la piste 1 comme l'ordre du task file le
suggérait.

C'est précisément le service qu'un instrument doit rendre : **écarter une piste
avant qu'on l'écrive**. Le task file demandait de mesurer avant de choisir — c'est
fait, et le choix change.

### Validation

- 3 tests d'intégration sur le vrai dépôt : attribution à `EnrichEmails`, un
  aller-retour par partie, et le **témoin négatif** « sans archive, un de moins »
  (sans lui, un compteur publiant un nombre fixe passerait).
- 3 tests de rendu, dont **« absence ≠ zéro »**.
- Suite : 136 + 436 + 660 + 2 099 .NET, **270 Python, 72 JS**. Échecs observés =
  flakies documentés (`MailExport` PDF, `BulkDelete`, `GetThreadAsync`), **tous
  verts isolément** — vérifié, et `GetThreadAsync` isolé confirme au passage que
  task-247 est saine.
- **Aucun changement de comportement** : seules des sollicitations sont consignées.

### Reste à faire — étape 2/2

Les 5 autres critères du DOD sont des **optimisations et des mesures au banc** :
réduire la phase fetch, A/B iso-conditions, détention de `imap_session` avant/après,
franchir le plateau de ~9,5 messages/s, et les tests de non-régression sur les
3 formes de corpus (mono-document, multi-documents, archive sans CDA exploitable).

**Piste 2 d'abord**, à la lumière du calcul ci-dessus — et son arbitrage inclut le
plafond `mail_max_userip_connections` (task-213 a montré qu'une voie dédiée
**double** les sessions IMAP par praticien).

**`/sonar` n'a pas été rejoué** sur cette étape (du C# a été modifié).
