# Tir de clôture du palier 1000 — task-297 + task-298 (2026-09-13)

> Banc de charge api-mail, EPIC E015. Rapport déterministe :
> `Api/Mail/tests/loadtest-k6/reports/2026-09-13/report-journey-1000-task297-298-20260913-140525.md`.
> Dump Seq : `seq-journey-1000-task297-298-20260913-140525.jsonl`.
> Échantillonneur : `observe-103501.csv` (+ copie brute `…-brut-avant-correction-fantome.csv`, voir §4).

## 1. Objet et protocole

Fermer les trois mesures au banc encore ouvertes : la borne de taille du cache Redis
(task-297) et les deux jambes du plafonnement des connexions (task-298). Un tir unique,
décision humaine du 2026-09-13 : si le résultat est vert, l'attribution par facteur ne
sert à rien ; s'il est rouge, il faudra dédoubler.

**Iso-conditions avec la référence** (jambe B de task-296, 2026-09-11,
`…-task296-legB-48G-20260911.md`) — seul le code sous test change :

| Paramètre | Valeur |
|---|---|
| Scénario / plan | `journey`, `1000:12600s`, K=1, rampe 30 s |
| Réserves (UID) | analysée 365-462, froide 463-536, traitement 537-611 (`UID_BASE=365`) |
| Probabilités | froid 0,19 — traitement 0,095 — corpus fileté 0,3 |
| Serveurs mail | cluster distant `192.168.1.69`, RTT p50 **4,9 ms** → `LATENCY_MS=96` (réf. : 5,2 ms → 96) |
| Bases | **1050 bases hydratées conservées**, 59 Go — aucune purge |
| Postgres | 48 GiB, `max_connections=2500`, `shared_buffers=12GB`, `effective_cache_size=36GB` |
| VM Docker | **94,3 GiB / 20 vCPU** (62,8 GiB à la référence — relevée par l'humain) |
| Fenêtre | 10h32 → 14h03 (local) ; régime [+10346 s..+12630 s] |

**Code sous test** : `cddaf73` = `d04f2ca` (référence) + task-297 + task-298 jambes 1 et 2.
`MaxEntryBytes=65536`, `Audit:DrainMaxConnections=16`, `server_idle_timeout=120`.

**Divergences assumées, à ne pas taire** :

- les `packages.lock.json` ont bougé entre les deux tirs (migration xUnit v3, `cf685ac`,
  postérieure à la référence) ;
- la VM Docker est passée de 62,8 à 94,3 GiB. Le conteneur Postgres reste à 48 GiB : ce
  qui change est la **marge de l'hôte**, qui avait figé la VM 45 min le 11/09 pendant le
  rejeu du spill ;
- les conteneurs étrangers au banc ont été laissés en marche (décision humaine,
  iso-conditions) ; ils consommaient moins de 1 % de CPU au pré-vol.

## 2. Verdict

**🟠 ORANGE — « tir réussi, ses chiffres sont exploitables »**, contre 🔴 ROUGE le 11/09.

| Grandeur | 11/09 (réf.) | **13/09** |
|---|---|---|
| Requêtes / débit émergent | 1 233 799 / 97,4 req/s | **1 405 348 / 111,0 req/s** (+14 %) |
| Taux d'erreur k6 | 0,024 % | **0,013 %** — et **0,0002 %** hors boîte de banc vide (§4) |
| Refus `53300 too many clients` | **118 886** | **0** |
| Refus PgBouncer `08P01` | 175 | **0** |
| Backends au pic | **2 506 = `max_connections`** | **2 421 / 2 500 (96,8 %)** |
| …dont pooler / drain d'audit | non attribuable (sonde fausse) | **1 874 / 586** |
| Login Postgres p95 | 0,079 s | **0,016 s** |
| `cl_waiting` non nul | 28 % des relevés, `maxwait` 12,3 s | **6 %**, `maxwait` **814 ms** (chemin médecin) |
| Journal d'audit émises / persistées / perdues | 207 396 / 193 909 / 0 (13 487 bloquées) | **236 781 / 236 781 / 0**, spill **0** |
| Âge de la plus vieille trace | 5 307 s | **0 s** |
| `Timeout getting key` (cache Redis) | 6 568 (tir du 09/09) | **0** |
| SLOWLOG Redis (seuil 10 ms) | écritures de 11-16 ms portant 160 Ko à 1,47 Mo | **3 entrées**, toutes ~10 ms, aucune écriture de corps |
| Verdict SLO | 7 ❌ / 4 ✅ | **7 ❌ / 4 ✅** (mêmes étapes) |
| Après le tir | rejeu du spill → 2 500 backends, 27 575 refus, **VM figée 45 min** | **rien à rejouer** ; backends 2 421 → 8 en 100 s |

## 3. Ce que chaque US a démontré

### task-297 — la borne du cache (fermée)

Trois preuves concordantes, aucune contredite :

- **0** `Timeout getting key` sur 3 h 30 à 1000 médecins, contre **6 568** le 09/09 sur un
  tir **sans aucune autre charge Redis** ;
- **SLOWLOG Redis : 3 entrées** sur tout le tir (seuil 10 ms), à peine au-dessus du seuil
  (`HMGET` 10,6 ms, `PEXPIRE` 10,1 ms) — **aucune écriture portant un corps de message**,
  alors que c'est précisément ce que le slowlog du 09/09 montrait ;
- aucune erreur de cache dans Seq.

**Réserve honnête** : le *nombre* d'entrées refusées par la borne n'est pas mesurable sur
ce tir — voir le défaut F-297-M au §4. C'est l'**effet** qui est démontré, pas le compte.

### task-298 jambe 1 — le plafond du drain d'audit (fermée sur le fond)

- Les connexions directes sont **attribuables** pour la première fois
  (`application_name` = `mss-mail-audit`) : la colonne « directs » affichait **0** le 11/09
  pendant que le drain saturait le serveur. Pic **586**, provisionnement **2**.
- **Aucune n'a jamais dépassé 30 s d'oisiveté** (contrôlé pendant le tir) : le nombre
  résident n'est pas le plafond de concurrence, c'est **le débit du drain × 30 s**. Il est
  borné par construction, il ne dérive pas.
- **Retour à zéro en moins de 10 secondes** après la fin du tir (le DOD demandait moins
  d'une minute). Total des backends : 2 421 → 8 en 100 s.
- **Zéro spill, zéro perte, zéro retard** : 236 781 émises = 236 781 persistées, plus
  vieille trace à 0 s. Il n'y a donc **rien eu à rejouer** après le tir — c'est ce rejeu
  qui avait figé la VM trois fois le 11/09.

### task-298 jambe 2 — `server_idle_timeout` 600 → 120 (mécanisme prouvé, cible manquée)

Preuve directe obtenue **avant même le tir** : le seed a ouvert un pool par base
(969 backends), tous rendus en **150 secondes**. À 600 s ils seraient restés dix minutes.

Pendant le tir, la grandeur a changé de **nature**. Le 11/09, les backends croissaient
**linéairement avec le temps** (270 → 2 504 en 2 h 46) alors que le débit plafonnait
depuis deux heures. Ici chaque poste est borné par une grandeur physique — le pooler par la
**population** (934 bases sur 1000 à 13h15, à 1,90 backend chacune, plateau 1 874), le
drain par son **débit**. Le plateau s'est formé vers 13h25 puis a **reculé**
(2 373 → 2 290). C'est l'objectif écrit de la US : *borné et indépendant de la durée*.

## 4. Ce qui reste ouvert

### Deux cibles chiffrées du DOD sont manquées

| Cible | Mesuré | Lecture |
|---|---|---|
| Backends max **< 2 300** (jambe 1) / **< 1 800** (jambe 2) | **2 421** | manquée |
| `cl_waiting` **< 5 %** (j1) / **0 soutenu** (j2) | **6 %**, `maxwait` 814 ms | manquée |

**La cause est un dimensionnement, pas une dérive.** À 1000 médecins,
`max_connections = 2500` ne couvre que le pooler (1000 × `default_pool_size` 2 = 2000) : la
note `DIMENSIONNEMENT-POSTGRESQL-API-MAIL.md` l'a dimensionné sur le **seul** pooler et ne
laisse rien pour la route directe du journal (~586) ni pour le provisionnement. Deux
leviers, à mesurer **séparément** :

1. **`max_db_connections` 3 → 2** (profil de banc) — plafond dur du pooler à 2 000, marge de
   500 pour le drain, **aucun coût mémoire**. C'est la jambe déjà écrite dans
   `pgbouncer.ini` comme suite prévue.
2. **`max_connections` 2500 → 3000** — environ 2,5 Mo de RSS par backend, soit +1,25 Go sur
   un Postgres qui a désormais de la marge.

### F-297-M — le meter du cache n'est pas exporté

`CacheMetrics.MeterName` (`"Mssante.Cache"`) n'est **jamais** passé à `AddMeter(...)` dans
`src/Api/DependencyInjectionExtensions.cs` : `mss_cache_entry_bytes` et
`mss_cache_oversize_skipped_total` existent en processus, sont couverts par un test
unitaire, et **aucune série n'atteint le collecteur** (vérifié pendant le tir). C'est
exactement le défaut que task-292 avait corrigé pour le meter d'audit — le commentaire qui
le raconte est trois lignes au-dessus de la ligne manquante. Le journal
`[Cache] Entry skipped` étant en `Debug`, il est invisible au banc lui aussi.
**Correctif : une ligne.** Non appliqué ici délibérément — le tir devait porter le code
mergé sur `develop`.

### F-BANC-600 — une boîte vide fabrique 98 % des erreurs

`loadtest-600` a une INBOX à **0 message** pour un `uidNext` à 613 : vidée lors d'une
campagne antérieure, et les UID ne se réutilisent jamais. **180 des 183** contrôles k6 en
échec lui sont imputables ; hors cette boîte, **3 échecs sur 1 405 348 requêtes**
(0,0002 %), tous sur `sendmail` (« A task was canceled »). `setup()` ne l'a pas vue car il
sonde trois boîtes (première, milieu, dernière) — **la sonde doit porter sur un échantillon
aléatoire**.

### F-BANC-PHANTOM — `observe.ps1` comptait des refus PgBouncer inexistants (corrigé)

Le rapport a d'abord classé ce tir **🔴 ROUGE** sur « 208 refus `server_login_retry` ». Les
journaux de PgBouncer en contiennent **0** sur toute la fenêtre.

Cause, en PowerShell : `@($logLines -match 'motif').Count`. Quand `docker logs --since` ne
rend **qu'une seule ligne**, PowerShell la passe en **scalaire** ; `-match` rend alors un
**booléen** `$false`, et `@($false).Count` vaut **1**. Un refus fantôme était donc compté à
chaque relevé où le pooler n'avait écrit qu'une ligne — et son journal est saturé de
`WARNING dropping database …`. **220 faux refus** sur un tir qui n'en comptait aucun.

```powershell
@('une ligne'   -match 'motif').Count   # -> 1   FAUX
@(@('a','b')    -match 'motif').Count   # -> 0   juste
```

Corrigé (`Where-Object`, qui filtre identiquement dans les deux cas), syntaxe validée,
comportement vérifié sur scalaire et sur tableau. Le CSV a été remis en accord avec les
journaux (220 relevés ramenés à 0, **copie brute conservée** à côté), et le rapport
régénéré : verdict **🟠 ORANGE**.

⚠️ **Portée au-delà de ce tir** : les *petits* comptes de refus des rapports récents sont
suspects du même artefact — 175 le 11/09, par exemple. Les *gros* comptes restent réels
(85 787 lus directement dans `docker logs` le 08/09). Ne pas rejuger une campagne passée
sans rouvrir son CSV.

## 5. SLO — inchangé, et c'est un résultat

4 ✅ / 7 ❌ à 1000 médecins, **exactement les mêmes étapes** qu'au 11/09 (vertes : dashboard,
lecture froide, envoi, recherche patient). Ni régression, ni gain : les rouges restantes —
inbox hydratée (p95 10,3 s), dossier patient (6,2 s), fiche patient complète (11,0 s),
recherche (2,2 s) — relèvent du backlog E015 et ne sont traitées ni par 297 ni par 298.

⚠️ La chauffe occupe **77 % de la fenêtre** (plafond 50 %) : le verdict est porté par la
seule fenêtre de régime (38 min). Limite connue du palier 1000, relevée par `report.py`
lui-même, et qui appelle task-254.

## 6. Conclusion

**Le chapitre « stabilité du palier 1000 » est clos sur le fond** : plus aucun refus, plus
aucune saturation, plus aucune perte de trace d'audit, plus de spirale post-tir, et des
grandeurs redevenues **bornées par la population et par le débit** au lieu de croître avec
la durée du service. Le débit émergent progresse de 14 % et le taux d'erreur réel est de
0,0002 %.

**Deux cibles chiffrées restent manquées**, pour une raison de dimensionnement clairement
identifiée et dont le prochain levier est déjà écrit. La marge au pic est de **79
connexions sur 2 500** : c'est peu, et c'est ce qui justifie de tirer la jambe
`max_db_connections` 3 → 2 avant d'annoncer une capacité de 1000 médecins opposable en
exploitation.
