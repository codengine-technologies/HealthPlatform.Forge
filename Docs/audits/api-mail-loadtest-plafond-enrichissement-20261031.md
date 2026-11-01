# Plafond d'analyse des mails (`enrich/sync`) — remesure du 2026-10-31

> Banc api-mail.
> - Code : `develop 3e3ae9ce`, 5 réplicas.
> - Tireur : k6bench. Banc mail : cluster, latence IMAP injectée de 96 ms.
> - IA : tout OpenAI, **étiquetage désactivé** le temps du tir, vectorisation active.
> - Liaison TCP IPv6 du poste corrigée juste avant (délégation du calcul TCP IPv6 de la X520 désactivée).
> - Scénario `enrich` (shared-iterations), lots de 10 UID jamais analysés (463..602), une session par médecin.
> - Boîtes disjointes par palier ; `loadtest-600` (vide) évitée.
> - Réserves remises à zéro par `reset-state.sh --keep-analysed 462` avant le tir.

## Question

Le harnais suppose un débit d'analyse plafonné à **9,5 mails/s** (`WARMUP_THROUGHPUT_MESSAGES_PER_SECOND`,
`lib/journey-model.js`) et cadence ses chauffes dessus : la chauffe de 1000 boîtes dure 2 h 52. Ce plafond
date d'avant task-254 et n'avait jamais été remesuré.

## Résultat — escalier de concurrence

| Médecins simultanés | Lots | Débit (mails/s) | Lot p50 / p95 (s) | Par mail p50 (ms) | Court-circuits | Erreurs |
|---|---|---|---|---|---|---|
| 8 | 746 | **23,9** | 3,26 / 3,83 | 326 | 0 | 0 |
| 16 | 1 362 | **43,7** | 3,54 / 4,31 | 354 | 0 | 0 |
| 32 | 1 762 | **56,2** | 5,45 / 6,69 | 545 | 0 | 0 |
| 64 | 2 100 (corpus épuisé à ~4 min 40) | **71,1** | 8,49 / 11,63 | 849 | 0 | 0 |

**La constante de 9,5 est fausse d'un facteur 4 à 7.**
- De 8 à 16 médecins, le débit croît presque linéairement (× 1,83).
- Au-delà, il ralentit : × 1,29 puis × 1,27 à chaque doublement.

## Où part le temps d'un mail (moyennes serveur, `mssante_enrichment_phase_duration_seconds`)

| Phase (ms) | c8 | c16 | c32 | c64 |
|---|---|---|---|---|
| fetch IMAP | 138 | 136 | 137 | 141 |
| extraction XDM | 22 | 27 | 30 | 35 |
| parsing CDA | 14 | 16 | 18 | 19 |
| écritures base | 27 | 44 | **133** | **258** |
| assemblage (DTO, HTML, notifications, audit) | 24 | 41 | **126** | **295** |
| **total par message** | 224 | 264 | 444 | 748 |
| attente du verrou `imap_session` | 0 | 0 | 0 | 0 |
| *(hors chemin synchrone)* embedding | 201 | 200 | 201 | 201 |

- **Le fetch IMAP est constant** (~138 ms, soit 2,9 allers-retours à 96 ms). Dovecot sur le cluster et le lien
  ne limitent pas.
- **Le verrou de session ne coûte rien** : une session par médecin, aucune contention.
- Ce qui gonfle, ce sont les deux phases qui demandent du **CPU** : l'écriture en base et l'assemblage.

## Ressources du poste par palier (échantillonneur `observe-161340.csv`)

| | c8 | c16 | c32 | c64 |
|---|---|---|---|---|
| CPU hôte (24 cœurs logiques) | 44 % | 78 % | **97 %** | **95 %** |
| File d'attente processeur | 0,1 | 2,5 | **16,7** | **20,9** |
| API, 5 réplicas (Prometheus, cœurs) | 2,5 | 5,2 | 7,1 | 7,5 |
| Postgres (cœurs) | 0,7 | 1,5 | 2,5 | 3,3 |
| VM Docker `vmmemWSL` (cœurs, Postgres compris) | 2,7 | 4,7 | 5,9 | 6,1 |
| PgBouncer, attente des praticiens | 0 | 0 | 0 | 0 |

## Conclusion

1. **Le facteur limitant est le CPU du poste de banc, saturé dès 32 médecins simultanés.**
   - Le poste porte à la fois le système sous test, Postgres, Docker et Seq.
   - Il n'y a pas de plafond applicatif : pas de verrou, pas d'attente de connexion à la base, latence IMAP constante.
   - Le genou du poste se situe vers **45 à 55 mails/s**. Au-delà, chaque mail coûte plus cher, sans échec.
   - Cela recoupe le constat [banc local affamé] des campagnes d'août : un verdict local est pessimiste.
2. **Coût CPU d'un mail à faible charge (c8)** : environ **100 ms de CPU API** (2,47 cœurs / 23,9 mails/s,
   pipeline d'embedding asynchrone compris) et environ **30 ms de CPU Postgres**. C'est ce chiffre qui
   dimensionne : à 10 000 médecins, environ 9 mails/s en moyenne ([population cible]) font environ 1,2 cœur.
   Une pointe ou une chauffe massive se paie en cœurs, pas en latence.
3. **Gisements, par ordre de levier :**
   - **CPU par mail** : profiler l'assemblage (24 ms à vide) et l'écriture (27 ms). Le bruit de journalisation
     y contribue : 24 690 « Missing values » du parsing CDA pour ~95 000 mails analysés au journey du matin.
   - **Latence par mail** : regrouper les allers-retours IMAP (2,9 → ~1,2 par mail), soit −80 ms par mail.
     Cela réduit le temps vu du médecin, pas la consommation CPU.
4. **Harnais** :
   - relever `WARMUP_THROUGHPUT_MESSAGES_PER_SECOND` de 9,5 à ~40 ;
   - passer `WARMUP_MAX_CONCURRENT` de 8 à 16.

   La chauffe de 1000 boîtes passerait d'environ 2 h 52 à environ **40 min**.

Sources :
- `Api/Mail/tests/loadtest-k6/reports/2026-10-31/enrich-plafond-c{8,16,32,64}-*.json` ;
- `observe-161340.csv`, Prometheus du banc ;
- logs `k6-log-k6-enrich-20261031-16*.txt`.
