# Bilan du lot de findings — A/B/A du 2026-11-07/08

> Banc de charge api-mail (EPIC E015). Synthèse de trois tirs joués à la suite, dans la même session.
> Rapports détaillés : `api-mail-loadtest-journey-courte-1400-1996-bilan-{avant-1,apres,avant-2}-20261108.md`.

## Question

Depuis le tir de référence du 2026-11-05 (task-422), cinq tasks produit ont été mergées sur `develop`, chacune mesurée
seule contre un contrôle :

| Task | Objet | Finding |
|---|---|---|
| task-426 | Cache du compte du registre | FND-001 |
| task-427 | Recherche plein texte en un passage | FND-002 |
| task-429 | Le dossier patient ne lit plus le contenu des pièces jointes | FND-003 |
| task-430 | Comptages de biologie (index) et d'étiquettes (une fois) | FND-004, FND-005 |
| task-432 | Chaque requête SQL porte sa route et son site | instrument |

**Qu'a gagné la plateforme sur l'ensemble du lot, et où est la limite suivante ?**

## Protocole

- **A** = `d6712a10` : merge de task-422, l'état du tir de référence du 2026-11-05.
- **B** = `5b4e394f` : `develop` du 2026-11-07, les cinq tasks mergées.
- **Seul le binaire de l'API change.** Pour A, `src/` est restauré à `d6712a10`, sauf `src/AppHost`, qui reste celui de
  `develop`. Les deux AppHost ne diffèrent que par deux tableaux de bord Grafana. Le harnais et le générateur de rapport
  sont ceux de `develop` pour les trois tirs.
- **Tir identique** : `JOURNEY_STAGES="1400:18m,1996:18m"`, K = 1, IA simulée, pool 1, tireur k6bench, banc mail
  cluster, `LATENCY_MS=96`, 1 996 médecins hydratés, mêmes bases.
- **Ordre A/B/A** : avant-1 (23:38) → après (00:19) → avant-2 (01:09).
- **Pré-vol** : l'index de task-430 est présent sur 1 996 bases sur 2 000. Les 4 autres sont les boîtes exclues du tir
  (`USER_SKIP`). Lien poste → k6bench : 76,8 à 78,2 Mo/s, au-dessus du seuil de 60.
- **Limite de la comparaison** : le schéma ne revient pas en arrière. L'index de task-430 est présent aussi pour A. Le
  bilan mesure donc le **code** du lot. Le gain de l'index seul reste celui de task-430 (−43 % de pages lues par la forme).

## Validité des trois tirs

| | avant-1 | **après** | avant-2 |
|---|---|---|---|
| Requêtes HTTP | 687 365 | 759 657 | 749 569 |
| Débit à 1996 (req/s, régime) | 397,0 | 411,5 | 408,5 |
| Erreurs k6 | **0,21 %** | 0,01 % | 0,01 % |
| Envoi : obtention de session SMTP, moyenne | **12 892 ms** | 222 ms | 218 ms |
| Erreurs Seq | **2 606** | 2 | 0 |
| Fautes majeures du cgroup Postgres, max | 23,7 /s | 3,6 /s | 0,8 /s |
| Attente disque (part du temps SQL) | 11,4 % | 9,9 % | 8,7 % |
| IA | 🧪 simulée | 🧪 simulée | 🧪 simulée |
| Propriété des données | PASS | PASS | PASS |

**avant-1 est VOID.** Le serveur SMTP du banc (GreenMail, cluster) a calé de 22:51:45 à 23:02:12 UTC : négociations TLS
annulées, déconnexions en pleine phase DATA, 1 006 envois en échec, envoi au p50 de 31,7 s. Les médecins bloqués dans
l'envoi ont émis 9 % de requêtes en moins, ce qui allège toutes les autres étapes. Le même code A tourne sans une
erreur au tir avant-2.

**Le bilan repose donc sur avant-2 contre après.** C'est aussi le tir A aux meilleures conditions de disque des trois
(0,8 faute majeure par seconde) : la comparaison avantage A, pas B.

**Reproductibilité** : le tir après retombe sur les chiffres du tir B' de task-432, joué la veille sur le même code. Au
p50 à 1996 : dashboard 64 contre 64, inbox 51 contre 51, message enrichi 46 contre 46, fiche patient 339 contre 340.

## Ce que voit le médecin

Latence par étape, en ms, avant-2 → après :

| # | Étape | p50 1400 A → B | p50 1996 A → B | p95 1996 A → B |
|---|---|---|---|---|
| 1 | Arrivée dashboard | 71 → 58 (-18 %) | 114 → 64 (-44 %) | 677 → 558 (-18 %) |
| 2 | Ouvrir / rafraîchir l'inbox | 51 → 39 (-24 %) | 110 → 51 (-54 %) | 342 → 132 (-61 %) |
| 3 | Ouvrir un message enrichi (servi base) | 47 → 33 (-30 %) | 119 → 46 (-61 %) | 301 → 103 (-66 %) |
| 4 | Ouvrir un message froid (fetch IMAP) | 457 → 443 (-3 %) | 498 → 454 (-9 %) | 641 → 520 (-19 %) |
| 5 | Recherche | 407 → 323 (-21 %) | 518 → 345 (-33 %) | 920 → 640 (-30 %) |
| 6 | Envoi (acquittement UI) | 507 → 491 (-3 %) | 577 → 492 (-15 %) | 1059 → 950 (-10 %) |
| 7 | Télécharger une PJ (~124 Ko) | 51 → 36 (-29 %) | 132 → 51 (-61 %) | 348 → 124 (-64 %) |
| 8 | Marquer lu | 52 → 33 (-37 %) | 116 → 52 (-55 %) | 282 → 105 (-63 %) |
| 9 | Rechercher un patient | 63 → 55 (-13 %) | 80 → 56 (-30 %) | 188 → 75 (-60 %) |
| 10 | Ouvrir la page d'un dossier patient | 66 → 56 (-15 %) | 148 → 59 (-60 %) | 397 → 77 (-81 %) |
| 11 | Fiche patient complète (ressenti médecin) | 383 → 261 (-32 %) | 740 → 339 (-54 %) | 1884 → 672 (-64 %) |

- **Aucune étape ne régresse.** Toutes les étapes s'améliorent, aux deux paliers, au p50 comme au p95.
- **Le genou a reculé.** Le gain est deux fois plus fort à 1996 qu'à 1400. Avec A, le p50 de sept étapes double ou plus
  entre 1400 et 1996 médecins (inbox +116 %, message enrichi +153 %, PJ +159 %, page de dossier +124 %). Avec B, il
  dérive de 0 à 58 %. À 1996 médecins, la plateforme se comporte désormais presque comme à 1400.
- **Les étapes IMAP gagnent peu** (message froid −9 %, envoi −15 % au p50 à 1996). Leur temps est dans le serveur de
  messagerie, que le lot ne touche pas. Ce qu'elles gagnent vient de la contention en moins côté base.
- **Global** : latence moyenne 214,4 → 143,9 ms (−33 %), p50 103,1 → 58,6 ms (−43 %), p95 742,6 → 548,4 ms (−26 %).
- **Verdict SLO** : 11 étapes sur 11 dans la grille aux deux paliers, pour B comme pour A. Le verdict reste
  **indicatif** : la grille exige 30 min de plateau, ce tir en donne 18 par palier.

## Ce que fait la base

| | avant-2 | **après** | Écart |
|---|---|---|---|
| Temps SQL total du tir | 2 758 s | 1 031 s | **−63 %** |
| Coût SQL par requête HTTP | 7,1 ms | 3,6 ms | −49 % |
| Transactions validées / s | 6 781 | 2 595 | −62 % |
| Backends actifs (équivalent) | 2,29 | 1,19 | −48 % |
| Lecture disque | 20,1 Mo/s | 6,9 Mo/s | **−66 %** |
| Taux de cache (blocs) | 96,4 % | 98,2 % | +1,8 pt |
| Lignes balayées / s | 525 257 | 276 303 | −47 % |
| CPU de l'hôte, moyenne | 75,2 % | 62,2 % | −13 pt |

- Les transactions divisées par 2,6 : c'est le cache du registre (task-426), qui supprime les relectures du compte et le
  `DISCARD ALL` à chaque connexion.
- Les lectures disque divisées par 3 : c'est le dossier patient sans le contenu des PJ (task-429) et les comptages
  (task-430).
- **Plus de débit pour moins de CPU** : +1,3 % de requêtes servies, avec 13 points de CPU hôte en moins.

## Ce qui reste — la limite suivante

1. **PgBouncer fait encore attendre des requêtes.** `cl_waiting` est non nul sur 16 % des relevés à 1400 et 34 % à
   1996 (A : 28 % et 60 %). Le lot a réduit l'attente de moitié, sans l'annuler. Le contrat exige zéro. Avec le pool à 1
   connexion par base (task-422), c'est la première ressource épinglée du tir.
2. **Le premier lecteur de disque est FND-007** : 52,4 % des lectures disque du tir. À l'ouverture d'un message, le
   document médical et le contenu sont chargés avec leur vecteur, que rien n'affiche (FND-007, FND-009, confirmés).
3. **L'arrivée sur le dashboard est dominée par un appel IMAP.** `GET /mail/folders/{folder}` porte 61 % du temps
   serveur de l'étape, au p50 de 398 ms à 1996. Ce n'est pas du SQL : `/loadtest-findings` ne le voit pas. À instruire
   par la télémétrie IMAP (verrou de session, allers-retours).
4. **Deux coûts croissent avec la taille des boîtes** : la recherche vectorielle exacte (FND-010) et la recherche des
   messages qui citent un fil par `LIKE '%…%'` (FND-014). Le banc (157 documents par boîte) ne les mesure pas.

Détail des findings SQL : section « Findings — analyse de code » du rapport `bilan-apres` (8 candidats, contrôle
99 éléments, 0 écart). Registre : `findings-registry.md`.

## Défauts trouvés pendant la campagne

| Défaut | Effet | Prévention proposée |
|---|---|---|
| **Le rapport classe ORANGE « exploitable » un tir dont le SMTP du banc a calé.** 2e occurrence (tir A2 de task-432, le 2026-11-07). | Un tir VOID se lit comme un tir valide qui impute le dépassement de l'envoi au produit. | Une garde de validité dans `report.py` : obtention de session SMTP > 2 s en moyenne, ou erreurs d'envoi > 0,1 %, rend le tir **VOID (banc mail)**, testée sur ce tir. |
| **« Émise par » n'est pas une répartition.** `pg_stat_statements` garde le texte de la première exécution par base, donc le commentaire `site=` de la chauffe. | Deux formes sont attribuées à `enrich/sync` (chauffe) alors qu'elles sont surtout émises par l'ouverture d'un message. | Documenter la limite dans `report_postgres.py` et `agents/loadtest-findings.md`, renommer la colonne « premier site vu ». |
| `findings.py` plante en cp1252 dès que sa sortie est redirigée. | `candidates > fichier` échoue sous Windows. | `sys.stdout.reconfigure(encoding="utf-8")` et un test. |
| `findings.py explain` ne sait pas passer un paramètre NULL (`:'p8'` non défini). | Plan de l'INSERT d'audit impossible sans contournement. | Traiter NULL explicitement, et un test. |
| Le script de campagne exporte `MSYS_NO_PATHCONV=1` avant ses `git -C /d/…`. | `src/` n'est pas restauré au démontage. Rattrapé au tir suivant et à la main. | `cd` avant les commandes git, dans le script de campagne. |
| Un tir à cheval sur minuit : le résumé k6 va dans `reports/{J+1}/`, l'échantillonneur reste dans `reports/{J}/`. | Rapport de avant-1 non généré par la campagne, régénéré à la main. | Figer le répertoire du tir au lancement, côté `remote.sh fetch`. |

## Amélioration continue

- **Appris** : avec le lot, le genou n'est plus visible entre 1400 et 1996 médecins sur les étapes servies par la base.
  Avant, le p50 doublait. La limite suivante est l'attente PgBouncer, puis FND-007.
- **Appris** : une panne SMTP du banc se répète et n'est pas détectée par le rapport. Tant que la garde n'existe pas,
  chaque tir A/B doit relever l'obtention de session SMTP avant toute conclusion. C'est consigné en mémoire de session.
- **Capturé** : les trois rapports, la section Seq remplie (vide dans la campagne du 2026-11-06), les findings et le
  registre (FND-011 à FND-015).

## Ce que l'humain décide

1. **FND-007 + FND-009** : projeter le document et le contenu sans vecteur à l'ouverture d'un message, avec la garde
   « aucune route de lecture ne sélectionne `Embedding` ». Premier lecteur de disque restant.
2. **`cl_waiting` à 34 %** : instruire l'attente PgBouncer à 1996 (pool 1, durée de détention des connexions).
3. **Garde VOID sur le SMTP du banc** dans `report.py` : deuxième occurrence en deux jours.
4. **Tir sur des boîtes 10 fois plus grosses** pour trancher FND-010 et FND-014.
5. **Petits correctifs d'outillage** : `findings.py` (encodage, NULL), limite d'« Émise par », script de campagne.
