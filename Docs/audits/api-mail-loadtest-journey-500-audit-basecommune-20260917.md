# Campagne du 2026-09-16/17 — le journal d'audit en base commune, mesuré

> Banc de charge api-mail, EPIC E015 / E016. Rapport déterministe :
> `Api/Mail/tests/loadtest-k6/reports/2026-09-17/report-journey-500-audit-basecommune-20260916-014914.md`.
> Passe d'hydratation : `…/2026-09-16/journey-1000-hydratation-20260916-185707.json`.
> Échantillonneurs : `observe-151944.csv` (passe 1), `observe-234805.csv` (passe 2).

## 1. Objet

Attribuer l'effet de **task-300 / 301 / 312** — le journal d'audit PGSSI-S sorti du
sharding par praticien et écrit dans une table unique de la base commune. Ces trois US
ont été mergées les **13 et 15 septembre**, c'est-à-dire **après** le dernier tir
(clôture du palier 1000 du 2026-09-13, `…-task297-298-20260913.md`). Aucune mesure
n'existait donc sur elles.

La question précise, héritée du rapport du 13/09 : le drain d'audit pesait **586
connexions directes** au pic, et les backends touchaient **2 421 / 2 500**. task-300
annonçait qu'un lot de traces deviendrait *une* insertion sur *une* connexion au lieu
de ~100 pools vers ~100 bases. C'est cette promesse qui est mesurée ici.

## 2. Ce qui a été tiré, et pourquoi pas ce qui était prévu

**Le plan initial était un tir 1000 en iso-conditions avec le 13/09.** Il n'a pas pu
être tenu, pour une raison découverte au pré-vol et une autre découverte en cours de
campagne.

**Au pré-vol** : les 1000 bases praticien étaient **vides** (`Mails = 0`,
`MailContents = 0`, 13 Go contre 59 Go au 13/09) — un `reset-state.sh` sans
`--keep-analysed` a été joué entre les deux dates. La chauffe était donc entièrement
à refaire, d'où une **passe 1 d'hydratation** de 3 h 30 à 1000 médecins.

**En cours de passe 1** : l'hydratation s'est arrêtée à l'index **~640 sur 1000**, et
le front n'a plus avancé pendant ses 54 dernières minutes (mesuré directement en base,
pas au compteur de logs — cf. §5, F-BANC-CHAUFFE). Le harnais imposant ≥ 2 h à toute
passe de rattrapage, l'arbitrage humain du 2026-09-16 a été : **tirer à 500 sur une
population intégralement hydratée** plutôt qu'à 1000 sur une population à trous.

**Conséquence assumée, à ne pas taire** : ce tir ne mesure **pas** la pression sur
`max_connections`, qui ne se manifeste qu'à 1000. L'attribution des connexions à 1000
provient de la passe 1, dont les latences ne sont pas opposables — mais dont les
**comptes de connexions** le sont, puisqu'ils décrivent l'occupation du serveur et non
le temps servi.

### Paramètres

| Paramètre | Passe 1 (hydratation) | Passe 2 (mesure) |
|---|---|---|
| Plan | `journey 1000:12600s`, rampe 30 s, K=1 | `journey 500:7200s`, rampe 30 s, K=1 |
| Réserves (UID) | analysée 365-462, froide 463-536, traitement 537-611 (`UID_BASE=365`, `MESSAGES_PER_USER=247`) | idem |
| Probabilités | froid **0,19**, traitement **0,095** | idem |
| Serveurs mail | cluster distant `192.168.1.69`, RTT p50 **4,72 ms** → `LATENCY_MS=96` | idem |
| Postgres | 48 GiB, `max_connections=2500`, `shared_buffers=12GB`, `effective_cache_size=36GB` | idem |
| Registre | **`mss_registry_loadtest`** — base dédiée (voir §5, F-REGISTRE) | idem |
| Code sous test | `develop` au 2026-09-16, + `87f7f6e9` (sonde d'UID) | idem |

## 3. Le résultat principal

**Le journal d'audit a cessé d'être un poste de connexions.** Comparaison à iso-palier
(1000 médecins dans les deux cas) :

| Poste, au pic | 13/09 (avant task-300) | 16/09, passe 1 (après) |
|---|---|---|
| **Drain d'audit** (`application_name = mss-mail-audit`) | **586** | **5** |
| Backends totaux | **2 421 / 2 500** (96,8 %) | **~2 100** |
| Refus `53300 too many clients` | 0 | 0 |
| Refus PgBouncer `08P01` | 0 | 0 |

Et sur la passe 2 mesurée, à 500 médecins :

| Grandeur | Valeur |
|---|---|
| Backends au pic | **973 / 2 500** (38,9 %) |
| …dont pooler | 944 |
| …dont directs (audit + provisionnement) | **25**, dont **audit 5**, provisionnement 0 |
| `cl_waiting` non nul | **2 %** des relevés (13/09 à 1000 : 6 %) |
| `maxwait` PgBouncer | **82,6 ms** (13/09 : 814 ms) |
| Login PostgreSQL p50/p95/max | 0,007 / **0,013** / 0,024 s |
| Refus `server_login_retry` | **0** |

**Invariant de task-292, re-prouvé sur la nouvelle architecture** :
`emitted` = `persisted` = **1 108 201**, égalité exacte ; `spill_pending` 0 ;
plus vieille trace **0 s** ; `dropped` / `spilled` / `replayed` sans aucune série
exportée (absence = zéro, affirmable car `emitted`/`persisted` du même meter sont
présents). **Rien à rejouer après le tir** — c'est ce rejeu qui avait figé la VM
Docker 45 minutes le 11/09.

## 4. Verdict du tir — 🟠 ORANGE, SLO non tenu à 500

468 561 requêtes en 2 h, débit émergent 64,5 req/s, **0 itération abandonnée**,
vérification par base **PASS** (1000 boîtes, 73 684 mails, **0 sujet étranger**).

| # | Étape | p50 (cible) | p95 (cible) | Verdict |
|---|---|---|---|---|
| 1 | Arrivée dashboard | 35 (300) | 530 (1500) | ✅ |
| 2 | Ouvrir / rafraîchir l'inbox | 94 (300) | 415 (1000) | ⛔ non opposable |
| 3 | Ouvrir un message enrichi | 50 (100) | 442 (500) | ⛔ étape mal nommée |
| 4 | Ouvrir un message froid | 478 (800) | 544 (2500) | ✅ |
| 5 | **Recherche** | 126 (500) | **2 520 (2 000)** | ❌ |
| 6 | Envoi | 479 (1000) | 968 (3000) | ✅ |
| 7 | Télécharger une PJ | 460 (500) | 915 (2000) | ✅ |
| 8 | Marquer lu | 40 (200) | 98 (1000) | ✅ |
| 9 | Rechercher un patient | 22 (300) | 59 (1500) | ✅ |
| 10 | Page dossier patient | 57 (500) | 160 (2000) | ⛔ non opposable |
| 11 | Fiche patient complète | 330 (1500) | 847 (4000) | ⛔ non opposable |

**6 ✅ · 1 ❌ · 4 ⛔.** Les quatre non opposables le sont parce que 93,7 % des
ouvertures de l'étape 3 sont servies par la base, pour un plancher de 95 % : l'étape
mesure donc en partie du froid.

**La recherche n'est pas rouge à cause d'erreurs.** Seq sur toute la fenêtre ne rend
que **4 événements d'erreur** (2 requêtes `sendmail`) et 3 avertissements, **tous
horodatés à la seconde de l'arrêt du tir** : des opérations en vol annulées à la
fermeture. Le taux d'erreur applicatif réel est de **0,0004 %**. La famille
`ClientResultException` / OpenAI qui portait 67 % des échecs de recherche le 08/09 est
**absente**. C'est de la latence franche, à instruire.

### Comparaison avec le tir 500 du 2026-09-15 (INDEX)

| | 15/09 | 17/09 |
|---|---|---|
| Débit k6 | 65,5 | 64,5 |
| p50 | 288,6 ms | **149,4 ms** |
| p95 | 725,4 ms | **540,3 ms** |
| Erreurs | 0,08 % | **0,00 %** |

À débit équivalent, p50 ÷1,9 et p95 −26 %. ⚠️ **Non attribuable en l'état** : le tir
du 15/09 précède le merge de task-312 et son état d'hydratation n'est pas documenté —
au moins deux facteurs en plus du journal d'audit. À citer comme un signal, jamais
comme un gain mesuré.

### Où part le temps serveur

| Traitement | Appels | Moy | p95 | Part |
|---|---|---|---|---|
| **Arrivée dashboard** | 66 512 | 148 ms | 530 ms | **35,9 %** |
| Ouvrir / rafraîchir l'inbox | 33 250 | 126 ms | 415 ms | 15,2 % |
| Télécharger une PJ | 6 690 | 477 ms | 915 ms | 11,6 % |
| Envoi | 5 026 | 613 ms | 968 ms | 11,2 % |
| **Recherche** | 4 919 | 531 ms | **2 520 ms** | 9,5 % |

Le dashboard est **vert au SLO** (p95 530 pour 1 500) et consomme pourtant **plus du
tiers du temps serveur**, parce qu'il émet quatre appels à chaque passage. C'est le
point aveugle que la lecture par percentiles ne peut pas voir.

## 5. Findings de banc — tous découverts pendant cette campagne

### F-BANC-CHAUFFE — le banc ne sait pas hydrater 1000 médecins

La passe 1 a hydraté l'index 1 à **~640** en 2 h 36, puis **le front n'a plus
avancé** pendant ses 54 dernières minutes. Mesuré en base, boîte par boîte : plein
jusqu'à 640 (92-118 `MailContents`), dégradé ensuite (650:75, 665:45, 690:10), **0 à
partir de 700**.

Hypothèse — **non vérifiée**, faute des 2 h qu'aurait demandées la contre-épreuve : une
fois ~650 médecins hydratés, leur trafic de parcours normal consomme la capacité
d'enrichissement du serveur (plafonnée à ~9,5 messages/s, task-245) et **affame la
chauffe des suivants**. Si elle se confirme, aucun verdict à 1000 n'est aujourd'hui
porté par une population réellement hydratée — **y compris celui du 13/09**. C'est
`task-254` qui porte le sujet.

### F-BANC-VAGUE — la chauffe coûte 68 % de la fenêtre même sur des bases pleines

Passe 2, sur 500 bases **mesurées pleines** (100-122 `MailContents`) :
`journey_warmup_completed` = **1,0** (100 % des médecins), et pourtant
`journey_warmup_elapsed_s` p95 = **4 872 s sur 7 200, soit 68 %** — au-delà du plafond
de 50 %, et du même ordre que les 77 % du 13/09.

Le coût n'est **pas** du travail : le rapport chiffre 5 500 appels d'analyse à 232 ms
de moyenne, « 0,0 % de la durée du tir ». C'est de la **file d'attente** —
`JOURNEY_WARMUP_MAX_CONCURRENT=8` fait patienter 500 médecins même quand leur propre
chauffe court-circuite en ~25 ms.

> ⚠️ **Correction d'une inférence fautive commise en cours de campagne.** Un relevé
> intermédiaire de `journey_warmup_elapsed_s` (1 075 s, pris à 15 % d'avancement) avait
> été lu comme une valeur finale, d'où la conclusion « la chauffe est bon marché sur
> bases hydratées, donc les bases du 13/09 n'étaient pas hydratées ». **C'est faux.**
> Ici les bases étaient hydratées, la chauffe a abouti à 100 %, et elle a quand même
> coûté 68 %. Une métrique de percentile lue en cours de tir n'est pas un résultat.

### F-BANC-TOXIPROXY — un message d'erreur qui désigne le mauvais remède

Le pod Toxiproxy du cluster a redémarré pendant la campagne : `/proxies` rendait `{}`,
les NodePorts 30993 et 30465 refusaient, tandis que le 30994 (direct, hors Toxiproxy)
répondait. Le harnais a rendu :

```
proxy "dovecot-imap" not found (HTTP 0) — run the seed tool first
```

**`HTTP 0` n'est pas un 404** : c'est l'absence de réponse. Le message oriente vers un
seed à rejouer alors que la cause peut être (a) l'API Toxiproxy injoignable, ou (b)
`MSS_LOADTEST_MAIL_HOST` absente de l'environnement **de k6** — le harnais en dérive
`http://<host>:30474`, et sans elle il interroge `127.0.0.1:8474`. Les deux cas se sont
produits le même jour. Le remède proposé ne traite ni l'un ni l'autre.

### F-BANC-OBSERVE — l'échantillonneur perdu au passage de minuit

`run.sh` crée le répertoire du **lendemain** pour les résumés k6 (task-254), justement
parce qu'un tir peut franchir minuit. `observe.ps1` n'a pas cet égard : son CSV reste
dans le répertoire du jour de **démarrage**, et `report.sh`, qui cherche dans le
répertoire du jour de **fin**, a rendu « aucun CSV observe-\*.csv ». Toute la section
« Ressources & télémétrie » manquait au premier rapport. Contourné à la main (copie du
CSV), à corriger dans l'outil.

### F-REGISTRE — le registre du banc et celui du dev partagent une base

Le seed **refuse** de provisionner un registre qui porte un compte hors banc — garde-fou
correct, et il s'est déclenché : `mss_registry` contenait **3 comptes de dev**
(`medecin.formation.mssante.fr`), créés depuis le 13/09 par les tests manuels des
task-309/313/314. Contourné par un registre dédié `mss_registry_loadtest`
(`MSS_TENANT_REGISTRY_DB`). **À graver dans le playbook** : depuis task-299, un banc de
charge exige sa propre base de registre, sinon il ne démarre pas — et la sonde de santé
du skill (`connection/status` = 200) ne le voit pas, puisqu'elle passe au vert avant
même que le registre existe. Les routes de messagerie, elles, répondent `403
MAILBOX_NOT_ATTACHED`.

### F-SEED-15S — un commentaire périmé qui ferait renoncer à une campagne

`SeedOptions.TimeoutMinutes` documente « ~15 s par utilisateur […] ~110 utilisateurs
est le plafond pratique à 30 minutes ». **Mesuré** : 5 utilisateurs en 6,6 s (démarrage
compris), **1000 utilisateurs en 3 min 04**, registre provisionné en moins d'une minute.
Le chiffre du commentaire conduirait à budgéter 4 h pour 12 min de travail.

### F-KEEPAWAKE — une preuve d'armement initiale ne vaut pas pour la campagne

Le processus `keep-awake` s'est arrêté au bout de ~10 h alors qu'une échéance de 12 h
lui était donnée, **en cours de passe 2**. Il a fallu le ré-armer. La consigne connue
(« exiger la preuve d'armement ») doit donc être complétée : **vérifier périodiquement**,
pas seulement au lancement. Deux pièges d'écriture rencontrés au passage, tous deux
silencieux : un `.ps1` non-ASCII lu en ANSI par PowerShell 5.1 (un tiret cadratin se
décode en guillemet courbe et déséquilibre le parseur), et le littéral `0x80000000`
parsé en `Int32` **négatif** avant la conversion `[uint32]` — suffixe `L` obligatoire.

### F-SONDE-UID — ce que l'échantillon aléatoire attrape, et ce qu'il n'attrape pas

`87f7f6e9` fait tirer à la sonde d'UID 5 boîtes au hasard en plus des trois positions
fixes (F-BANC-600, tir du 13/09). Bilan à chaud :

- **Ce qu'elle a attrapé** : le redémarrage de Toxiproxy. Le tir a été refusé sur
  `HTTP 500`, et parmi les boîtes signalées, `loadtest-17`, `19` et `131` sont des
  **tirages aléatoires** — les trois positions fixes seules auraient suffi ici, mais le
  tirage a confirmé l'étendue du défaut.
- **Ce qu'elle n'attrape pas** : `loadtest-600`, toujours morte (`0 EXISTS`,
  `uidNext` 613 contre une bande visée 365..611 — les UID IMAP ne reculent pas, et
  kubectl est refusé sur ce poste, donc pas de reset du maildir). Un balayage manuel de
  29 boîtes réparties sur 1..1000 a montré qu'elle est la **seule** morte : 5 tirages
  sur 1000 ont ~0,5 % de chance de la désigner.

**Le bon geste n'est donc pas un échantillon plus gros dans `setup()`** — 1000 sondes
séquentielles coûteraient ~17 min. C'est un **balayage large en pré-vol**, hors harnais :
16 sondes IMAP parallèles en `openssl` ont couvert 29 boîtes en quelques secondes.

## 6. Ce qui reste à faire

1. **Tirer la jambe `max_db_connections` 3 → 2.** La cible est désormais chiffrée : à
   1000 médecins toutes bases en service, le poste « pooler » pèse ~2 050 connexions et
   le poste « audit » 5. Le levier est déjà écrit dans `pgbouncer.ini`, coût mémoire nul.
   C'est ce qui reste entre l'état actuel et une capacité 1000 opposable.
2. **task-254** — sans elle, aucune campagne à 1000 ne part d'une population hydratée,
   et F-BANC-VAGUE montre que le problème n'est pas seulement le débit d'enrichissement
   mais aussi le **portillon de concurrence** de la chauffe.
3. **L'étape 5 (recherche)** reste rouge sans cause établie ; les erreurs sont écartées,
   la latence est à décomposer par la télémétrie.
4. **Le dashboard** — 35,9 % du temps serveur pour une étape verte, quatre appels par
   passage. Le plus gros gisement du tir.
