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
- [~] ~~Le débit d'enrichissement **croît avec la concurrence** : le plateau à
      ~9,5 messages/s est franchi, chiffre à l'appui~~ → **DÉPLACÉ vers
      [task-255](todo-task-255.md)** par arbitrage PO du 2026-08-10.
      **Motif** : le critère a été **mesuré, et il est négatif** — doubler la
      concurrence rend **+4 %** (2,66 → 2,77 msg/s). La même mesure **écarte le
      fetch** comme cause du plateau : son coût par message ne se dégrade pas
      avec la concurrence (131 → 130 ms), et le retrait d'un aller-retour sur
      deux n'a rien rendu au débit. Ce critère ne relevait donc pas de cette
      piste, et l'y laisser aurait bloqué un gain acquis et prouvé
      (−43 % sur `imap_fetch`, −34 % de détention de verrou) derrière une cause
      qui n'est pas la sienne. Il n'est **pas abandonné** : il est le cœur de
      task-255, avec les faits que cette campagne a établis.
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

---

## Develop log — étape 2/2 : les tests, puis l'A/B au banc

### Resynchronisation

Branche remise à niveau sur `develop` par **merge** (`5598f89`) — task-251, task-252
et task-249 avaient atterri depuis. **Aucun conflit** malgré une collision
apparente : task-254 et task-252 touchent tous deux `ImapService.cs` et
`MailProcessingMetrics.cs`, mais sur des régions disjointes (enrichissement vs
téléchargement). Suite complète après merge : **3 747 verts**, 1 flaky documenté
(`BulkDelete`, vert en isolation).

### Les deux critères de test (livrés)

**`8a843a8` — non-régression sur les 3 formes de corpus.** Le compte de documents
cliniques est désormais **exact** là où `CdaParsingIntegrationTests` se contentait
de `NotEmpty` (« au moins un ») : une archive rendant 1 document au lieu de 2
passait sans broncher. La forme **multi-documents est absente du corpus versionné**
(les 5 archives de l'ANS portent un seul `SUBSET01`) — elle est fabriquée à
l'exécution en dupliquant le sous-ensemble d'une archive réelle.

⚠️ **Ces tests sont verts avant comme après le correctif, et c'est le but.** Mon
cadrage initial (« reverter `4cf6021` doit les rendre rouges ») était faux :
l'ancien code extrayait les mêmes documents, il était seulement plus lent.

Mutations : (A) n'extraire que le premier document → **multi-documents rouge, mono
verts** ; (B) n'extraire aucun document → **6/7 rouges** ; (C) injecter un DTO vide
dans la garde anti-fantôme → **aucun rouge**. La C est un résultat : la
bibliothèque XDM ne produit aucun `CdaFile` candidat pour cette archive, donc la
garde n'est **jamais atteinte**. Test renommé et **trou de couverture écrit** dans
le fichier.

**`e71f14e` — ni perdu ni dupliqué sur échec partiel.** L'invariant était
revendiqué en prose par le commentaire d'`EnrichEmailsAsync` et vérifié par aucun
test. Éprouvé contre un vrai PostgreSQL, en assertant l'état de la **base**.

Mutations : (D) jeter ce qui a été lu → **rouge** ; (E) retirer le filtre de
déduplication → **aucun rouge**. La E établit deux gardes indépendantes dont la
seconde suffit : le filtre de `ComputePendingEnrichmentAsync` est une garde de
**coût**, `AddNewMail` (refus si `ContentCount > 0`) la garde de **correction**.
Le test ne protège donc **pas** la déduplication amont — **trou de couverture
consigné**.

### L'A/B iso-conditions — le levier retenu

`EnrichmentFetchPlan` n'expose aucun réglage : les seuils sont des `const`. Le
bras A n'est donc **pas** `develop` (qui diffère aussi par l'instrument et le fix
de rapport = plusieurs facteurs), mais **le même binaire** avec
`UsefulOctetsShareFloor = 2.0` — une part impossible (≤ 100 %), donc le
groupement n'est jamais choisi. **Un seul facteur.** Levier retiré après mesure,
contenu de production vérifié **identique à HEAD par hachage**.

Protocole par bras : purge (`reset-state.sh`) → snapshot des compteurs cumulés →
tir → snapshot → deltas. Compteurs cumulés et non `rate()` : sur un tir de 40 s,
une fenêtre de `rate` rend des séries vides ou du `nan` (constaté).

Conditions : banc local, 8 praticiens × 30 messages porteurs d'`IHE_XDM.ZIP`,
`VUS=4`, `ENRICH_BATCH=20`, `SESSION_ROTATION=0.002`, latence Toxiproxy du banc.

### Le résultat

| Grandeur (par message) | Bras A (une commande/partie) | Bras B (groupé) | Écart |
|---|---|---|---|
| **Sollicitations serveur** | **2,50** | **1,50** | **−40 %** |
| `imap_fetch` | 232,1 ms | 127,5 ms | −45 % |
| Enveloppe d'enrichissement | 418,6 ms | 274,6 ms | −34 % |
| Détention `imap_session` | 272,3 ms/acq | 178,1 ms/acq | −35 % |
| Acquisitions `imap_session` | 1,10 | 1,10 | **+0 %** |
| `cda_parse` | 50,1 ms | 37,3 ms | −25 % |
| `xdm_extract` | 53,3 ms | 44,9 ms | −16 % |
| `db_write` | 58,2 ms | 47,7 ms | −18 % |

**Ce qui est établi sans réserve** : **un aller-retour de moins par message**
(2,50 → 1,50). C'est un **compte**, pas une durée — il ne dépend d'aucune
condition de machine, et il correspond exactement au mécanisme annoncé. Et la
promesse de conception est tenue : la détention du verrou baisse de 35 % **à
nombre d'acquisitions inchangé** (1,10), c'est-à-dire que le groupement s'est bien
fait **à l'intérieur** d'un message — task-239 n'est pas défaite.

### ⚠️ Deux réserves qui interdisent de publier « −45 % » comme un gain net

1. **Des phases sans aucun rapport avec le fetch ont bougé de 16 à 25 %.**
   `cda_parse`, `xdm_extract` et `db_write` ne touchent pas au réseau : un
   changement à facteur unique ne devrait pas les déplacer. Il existe donc un
   **confondant de cet ordre** entre les deux tirs (charge de la machine hôte),
   et il joue dans le **même sens** que le gain. Les écarts de **durée** ne sont
   donc pas opposables à mieux que ~±20 % ; seul le **compte** de sollicitations
   l'est.
2. **Les deux bras n'ont pas abouti pareil** : bras A **8 lots / 8**, bras B
   **5 lots / 8** (100 messages contre 160). La normalisation par message atténue
   l'écart de volume, mais **l'asymétrie d'échec va dans le sens gênant** — c'est
   le *correctif* qui a échoué davantage. Un fetch de message entier est plus gros
   qu'un fetch de partie : l'hypothèse d'une sensibilité accrue au délai est
   ouverte et **non écartée**. À trancher avant de livrer le gain.

### État du DOD

| Critère | État |
|---|---|
| Allers-retours IMAP mesurés et rendus | ✅ étape 1 |
| Aucune régression fonctionnelle, 3 formes de corpus | ✅ `8a843a8` |
| Ni perdu ni dupliqué sur échec partiel | ✅ `e71f14e` |
| Phase `fetch IMAP` réduite, **prouvée par A/B** | 🟡 **réduction établie en compte** (−1 aller-retour), **gain en temps non opposable** (confondant ~±20 %, asymétrie d'échec) |
| Détention `imap_session` mesurée avant/après | ✅ 272,3 → 178,1 ms/acq, acquisitions inchangées |
| Plateau ~9,5 messages/s franchi | ❌ **non mesuré** — exige deux points de concurrence, et le confondant ci-dessus le rendrait de toute façon non opposable en l'état |

### Ce qu'il reste, et dans quel ordre

1. **Expliquer l'asymétrie d'échec** (5/8 contre 8/8). C'est le point bloquant :
   tant qu'il tient, le correctif peut être un gain de latence payé en abandons.
2. **Rejouer l'A/B sur une machine au repos**, ou en alternant les bras
   (A-B-A-B) pour absorber le confondant.
3. **Le plateau**, seulement ensuite.

---

## Develop log — étape 2/2, suite : les trois réserves levées, et le plateau qui ne l'est pas

### 1. L'asymétrie d'échec est ENVIRONNEMENTALE — le correctif est disculpé

La pile Seq du 500 (trace `87f0463b`, `ElapsedMs=15015`) est sans ambiguïté :

```
InvalidOperationException (transient) → NpgsqlException: The operation has timed out
  at NpgsqlConnector.ConnectAsync            ← ouverture d'une connexion NEUVE
  at PoolingDataSource.OpenNewConnector
  at MailRepository.GetEnrichedUidsAsync     (MailRepository.cs:2749)
  at ImapService.ComputePendingEnrichmentAsync (ImapService.cs:1468)
```

L'échec tombe sur la **toute première requête base** de l'enrichissement,
**avant tout fetch IMAP**, sur un chemin **identique dans les deux bras**. C'est
le plafond de connexions Postgres (un pool par base praticien), pas une
fragilité du message entier.

**Deux preuves indépendantes** : (a) préchauffer les pools (une requête
`GET /folders` par praticien avant le tir) fait passer un bras de 5/8 à **8/8** ;
(b) l'asymétrie **s'inverse** d'un round à l'autre — round 1 c'est B qui échoue,
round 2 c'est A. Un défaut du facteur ne change pas de camp.

⚠️ **Effet de bord à connaître** : un lot échoué ne contribue **aucun message**
mesuré, donc le bras qui échoue est **flatté** (biais de survie). C'est ce qui
gonflait le −45 % du premier round.

### 2. ⚠️ Mon deuxième round était aveugle — A contre A

`--artifacts-path` (le contournement qui évite de tuer un AppHost en vol) écrit
**hors du `bin` normal**. Chronologie établie par horodatage :

| Heure | Fait |
|---|---|
| 11:33:35 | `src/Api` construit avec `floor = 2.0` (bras A) |
| 11:38:34 | build « de vérification » → parti dans le **scratchpad** |
| 11:53:30 | rebuild à `2.0` pour A1 |

Entre 11:38 et 11:53 le `bin` portait donc encore `floor = 2.0`, et le bras « B1 »
lancé avec `--no-build` a exécuté **le binaire du bras A**. D'où un round qui
rendait −4 % de sollicitations et **+1 %** sur `imap_fetch` : je m'apprêtais à
conclure que le gain n'existait pas. **`--artifacts-path` et `--no-build` ne se
combinent pas** — à ne pas reproduire.

### 3. L'A/B valide : deux mesures indépendantes qui concordent

Bras préchauffés, **même taux d'échec (6/8 des deux côtés)**, binaires vérifiés :

| Par message | A1 (une commande/partie) | B2 (groupé) | Écart | Rappel round 1 |
|---|---|---|---|---|
| **Sollicitations serveur** | **3,00** | **1,50** | **−50 %** | −40 % |
| `imap_fetch` | 228,8 ms | 131,4 ms | **−43 %** | −45 % |
| Enveloppe | 425,1 ms | 300,6 ms | −29 % | −34 % |
| Détention `imap_session` | 269,3 ms/acq | 178,7 ms/acq | **−34 %** | −35 % |
| `cda_parse` (sans rapport) | 62,2 ms | 48,6 ms | −22 % | −25 % |
| `db_write` (sans rapport) | 46,7 ms | 47,7 ms | +2 % | −18 % |

**Établi** : un aller-retour de moins par message (compte, pas durée), un
`imap_fetch` réduit de ~43 % reproduit deux fois, et une détention de verrou en
baisse de ~34 % **à nombre d'acquisitions inchangé** — le groupement s'est bien
fait *à l'intérieur* d'un message, **task-239 n'est pas défaite**.

**Réserve résiduelle honnête** : des phases sans rapport avec le réseau bougent
encore de 15 à 22 % (`cda_parse`, `xdm_extract`), alors que `db_write` ne bouge
pas. Il reste donc un confondant de cet ordre — plus petit que le gain de fetch,
et incapable d'expliquer le **compte** de sollicitations, qui est structurel.

### 4. ❌ Le plateau n'est PAS franchi — et c'est le résultat qui compte

Même bras (groupement actif), deux points de concurrence :

| Concurrence | Débit | `imap_fetch` | Sollicitations |
|---|---|---|---|
| 4 | **2,66 msg/s** | 131,4 ms | 1,50 |
| 8 | **2,77 msg/s** | 130,1 ms | 1,80 |

**Doubler la concurrence rend +4 %.** Le plateau tient, et le coût de fetch par
message ne se dégrade pas (131 → 130 ms) : **ce n'est donc pas le fetch qui
plafonne le débit**.

⚠️ Le niveau absolu (2,7 msg/s) n'est **pas** comparable aux 9,5 msg/s
documentés — banc local, 8 praticiens, latence Toxiproxy. C'est la **platitude
relative** qui est le résultat, pas le chiffre.

**Conséquence pour la US** : le correctif améliore la **latence par message**
sans lever le **plafond de débit**. Le critère « le plateau à ~9,5 messages/s est
franchi » est **non atteint**, et il ne le sera pas par cette piste. La piste 2
(détention de `imap_session`) reste candidate — et le task file avait raison
d'interdire de présumer dans un sens comme dans l'autre.

### État final du DOD

| Critère | État |
|---|---|
| Allers-retours IMAP mesurés et rendus | ✅ |
| Aucune régression fonctionnelle, 3 formes de corpus | ✅ `8a843a8` |
| Ni perdu ni dupliqué sur échec partiel | ✅ `e71f14e` |
| Phase `fetch IMAP` réduite, **prouvée par A/B iso-conditions** | ✅ **−43 %, reproduit deux fois, un aller-retour de moins par message** |
| Détention `imap_session` mesurée avant/après | ✅ 269,3 → 178,7 ms/acq, acquisitions inchangées |
| **Plateau ~9,5 msg/s franchi** | ❌ **non atteint** — +4 % pour un doublement de concurrence |

**5 sur 6.** Le sixième n'est pas « à finir » : il est **mesuré et négatif**.
C'est un arbitrage PO, pas un reste de travail — voir ci-dessous.

### La décision qui revient au PO

Le correctif est **sain, mesuré et sans régression** : il retire un aller-retour
par message et raccourcit la détention du verrou d'un tiers. Il ne fait pas ce
que le DOD lui demandait en dernier critère : franchir le plateau.

Trois options :
1. **Livrer tel quel** en amendant le DOD : le gain de latence est acquis et
   prouvé, le plateau devient une US séparée (piste 2 — la détention de
   `imap_session`, dont on sait maintenant qu'elle baisse de 34 % mais reste à
   178 ms/acquisition).
2. **Garder la branche ouverte** jusqu'à ce que la piste 2 soit traitée, et
   livrer les deux ensemble — conforme à la règle 11 si l'on considère que « le
   débit croît avec la concurrence » est la valeur attendue par le médecin.
3. **Reprendre la mesure du plateau sur le banc distant**, où le niveau absolu
   est opposable, avant de trancher.

⚠️ **Deux réserves à ne pas perdre** : le plafond de connexions Postgres
(préchauffage obligatoire avant toute mesure d'enrichissement, sinon 15 s de
timeout à l'ouverture) et le confondant résiduel de 15-22 % sur ce banc local.
