# Campagne de charge api-mail — post-lot du 2026-09-08 (1000 puis 500 médecins)

> EPIC E015. Code sous test : `develop` `9bd8a72` = référence du 2026-09-01 (`b85f409`) + **9 PR** mergées
> depuis : task-288 (révocation OCSP/CRL), task-285 (déconnexion multi-instances), task-289 (flag Flagsmith
> absent), task-184 (INS hors URL/logs), **task-186 (journal d'audit PGSSI-S)**, task-291 (tests télémétrie),
> task-193 (document sans identifiant), task-183 (OID dans la clé patient), **task-194 (comptage de fils borné)**.
>
> Rapports détaillés (copies, l'original de `tests/loadtest-k6/reports/` est gitignoré) :
> `api-mail-loadtest-journey-1000-post-lot-20260908.md`, `api-mail-loadtest-journey-500-post-lot-20260908.md`.
> Références : `report-journey-1000-solo-send272-20260826-184235` (1000) et
> `report-journey-500-lot281283-20260831-004458` (500).

## Verdict en une ligne

**À 500 médecins, le lot ne régresse pas : 10/11 étapes vertes, p95 global inchangé (+0,7 %), envoi et
lecture froide meilleurs ; la Recherche seule sort de la grille au p50, pour une cause externe mesurée (67 % du
temps chez OpenAI). À 1000, le tir est ROUGE (5,2 % d'erreurs) : le genou de capacité prend un mode nouveau
— le pooler rejette au lieu de faire attendre — et le journal d'audit de task-186 a PERDU 1 477 traces (Fatal).
task-194 est confirmée là où elle compte : la page d'en-têtes hydratée coûte 5,6 fois moins à 1000.**

## Protocole

| | Tir 1000 (r2) | Tir 500 |
|---|---|---|
| Fenêtre (locale) | 17h16 → 20h47 (12 630 s ; régime 20h08 → 20h47) | 20h53 → 22h54 (7 230 s ; régime 22h20 → 22h53) |
| Journey K=1, stages | `1000:12600s` | `500:7200s` |
| Réserves / probabilités | 365..462 / 463..536 / 537..611 ; traitement 0,095, froid 0,19 (= références) | idem |
| Mail distant | cluster 192.168.1.69, corpus fileté 0,3, 247 msg/boîte, `UID_BASE=365`, maildir **intact** (1000 boîtes contrôlées) | idem |
| RTT / latence injectée | 14,6 ms / 86 ms | 18,4 ms / 83 ms |
| Bases | **vides au départ** (purgées le matin par l'A/B task-194) — écart déclaré | non purgées après le tir 1000 (protocole 26/08 → 01/09) |
| Chauffe aboutie | **75,6 %** (référence 98,8 %) → étapes 2/3/10/11 non opposables | 100 % |
| Pré-vol | PgBouncer 0 refus, résolution IPv4 seule, files bus à 0, aucun conteneur étranger gourmand | idem |

**Incident de protocole** : le premier lancement 1000 (r1, 16h37) a été avorté à 17h10 — le répertoire scratch
`%TEMP%\mss-ihe-xdm` avait disparu à 17h02 et l'enrichissement CDA était mort (F-SCRATCH-1). Purge des tables,
garde de recréation posée, relance r2. Aucune récidive.

## Résultats

### 500 médecins — comparaison au 2026-09-01 (même protocole, base plus jeune)

| Étape | 01/09 p50 / p95 | 08/09 p50 / p95 | Verdict |
|---|---|---|---|
| 1 Arrivée dashboard | 9 / 521 | 13 / 467 | ✅ |
| 2 Inbox | 105 / 304 | 118 / 483 | ✅ |
| 3 Message enrichi (base) | 27 / 71 | 39 / 110 | ✅ |
| 4 Message froid (IMAP) | 455 / 512 | 409 / 469 | ✅ |
| 5 Recherche | 404 / 560 | **567** / 906 | ❌ p50 (cible 500) |
| 6 Envoi | 470 / 963 | 440 / 890 | ✅ |
| 7 PJ | 9 / 423 | 344 / 715 | ✅ — voir F-AGE-1 |
| 8 Marquer lu | 20 / 48 | 29 / 75 | ✅ |
| 9 Rechercher un patient | 5 / 18 | 6 / 30 | ✅ |
| 10 Page dossier patient | 51 / 147 | 78 / 235 | ✅ |
| 11 Fiche patient complète | 157 / 463 | 229 / 732 | ✅ |
| Moyenne / p95 global (ms) | 102,5 / 471,7 | 116,5 / 474,9 | |
| Erreurs | 0,000 % | 0,002 % (9, résidu en chauffe) | |
| `cl_waiting` / `maxwait` | 2 / — | pointe 5 / 73 ms | |

### 1000 médecins — comparaison au 2026-08-26 (tir ROUGE, chauffe incomplète : bornes optimistes)

| Étape | 26/08 p50 / p95 | 08/09 p50 / p95 | Lecture |
|---|---|---|---|
| 1 Arrivée dashboard | 401 / 2 336 | 96 / 781 | ❌ → ✅ |
| 2 Inbox (page d'en-têtes) | 6 305 / 41 940 | 208 / 5 058 | non opposable (chauffe), ÷14 sur l'appel `emails` |
| 4 Message froid | 1 048 / 3 211 | 505 / 1 348 | ❌ → ✅ |
| 5 Recherche | 6 481 / 11 384 | 2 255 / 5 474 | ❌, ÷2,9 |
| 6 Envoi | 2 448 / 14 272 | 788 / **38 185** | ❌ — p95 ×2,7 (08P01) |
| 7 PJ | 1 689 / 4 597 | 796 / 2 280 | ❌, ÷2 |
| 8 Marquer lu | 1 310 / 3 372 | 240 / 1 166 | ❌, ÷5,5 |
| 9 Rechercher un patient | 137 / 528 | 23 / 222 | ✅ |
| Erreurs | 0,058 % | **5,21 %** | |
| `GetMailsByUids` moyenne / coût par objet | 7 649 ms / 24 512 µs | 1 376 ms / 4 203 µs | ÷5,6 / ÷5,8 |
| Documents CDA /s (pointe) | 24,3 | 42,8 | |
| Postgres CPU (pointe) / hôte | 15 cœurs / 71 % moy | 15,5 cœurs / 95 % moy | |

## Findings

### 🛑 F-08P01-1 — À 1000, PgBouncer rejette au lieu de faire attendre (nouveau mode de défaillance)

Postgres saturé (11–15 cœurs) → l'ouverture d'un nouveau backend dépasse `server_connect_timeout` → PgBouncer met
l'échec en cache (`server_login_retry`) et répond `08P01` en ~10 ms à tout client du pool : **85 787 refus**,
2,18 M `PostgresException`, 5,21 % d'erreurs, `sv_login` 212–243 permanents. Aggravé par `server_idle_timeout =
60 s` sur 1000 pools (réouverture permanente). Cascade mesurée : rejeux EF Core (139 k `InvalidOperationException`)
qui gonflent `GetMail` à 2,2 s et l'envoi à 38 s au p95. Cause structurelle inchangée depuis le 26/08 (coût
Postgres de la page hydratée et de la recherche) ; ce qui change est la **forme** de la défaillance, et elle
délest ~12 % du trafic — ce qui flatte les latences des autres étapes. **Levier** : réglage du pooler
(`server_idle_timeout`, `min_pool_size`, `server_login_retry`, `query_wait_timeout`) à mesurer au banc.

### 🛑 F-AUDIT-1 — task-186 : le journal PGSSI-S a perdu 1 477 traces sous saturation

413 939 traces écrites en 3 h 30 sur 1000 bases (0,31 par requête HTTP), via le même pooler saturé : 113 248
bascules vers le spill Redis (`mss:audit:spill`, plafond 100 000), puis **1 477 `Fatal` « trace … is LOST. The
audit trail is no longer exhaustive (PGSSI-S) »** à partir de 20h26. Effet de bord : 10 233 timeouts du cache
Redis applicatif. Contre-épreuve à 500 : 86 888 traces, **0 perdue, 0 erreur**. La perte est un phénomène de
saturation, mais c'est un finding de **conformité** : le journal doit être découplé du chemin de données du
praticien (base/schéma dédié ou back-pressure sans perte), et son spill dimensionné en durée.

### 🛑 F-SCRATCH-1 — Un répertoire scratch supprimé tue l'enrichissement CDA jusqu'au redémarrage

`IheXdmScratchDirectory` (task-185) crée `%TEMP%\mss-ihe-xdm` une fois et ne le recrée jamais : après sa
suppression externe à 17h02, 0 document CDA créé et ~900 `DirectoryNotFoundException`/min, en **HTTP 200** côté
médecin. Auteur de la suppression non attribué. Remède : recréation à la demande dans `CreateFile()`.

### ⭐ F-194-1 — task-194 confirmée à 1000 : page d'en-têtes ÷5,6, coût par objet ÷5,8, temps serveur de l'inbox ÷7,5

Objets par page constants (270 → 247) : c'est un coût par objet, cohérent avec l'A/B du matin (allocations ÷13).
Réserve : bornes optimistes (délestage 12 %). À 500, la même opération coûte +38 % qu'au 01/09 — le gain de
task-194 est un gain **mémoire**, visible sous contrainte GC/CPU (1000) et pas à 500 (F-194-2).

### F-SEARCH-1 — La Recherche sort de la grille au p50 ; 67 % de son temps est chez OpenAI

Décomposition d'une recherche médiane (584 ms) : embedding `api.openai.com` **392 ms**, requête pgvector ~18 ms,
hydratation des 10 résultats ~171 ms. La dérive de trois campagnes (331 → 425 → 567 ms) est d'abord une latence
externe. Leviers : cache d'embedding de requête, allègement de l'hydratation (17 ms/document).

### F-AGE-1 — L'étape PJ (9 → 344 ms au p50) n'est pas une régression : le contenu se remplit à la première demande

En base, 68 archives `IHE_XDM.ZIP` sur 116 sans `Content` = exactement celles jamais téléchargées (audit
`AttachmentDownload`) ; `ImapService` → `UpdateAttachmentAsync` après le premier téléchargement IMAP. Le 01/09
mesurait un cache plein après quatre tirs, le 08/09 le premier passage. **L'iso-condition inclut l'âge de la
base.** Une partie des +50/60 % au p95 des étapes servies par la base relève probablement de la même cause ;
le rejeu de ce tir sur cette base non purgée, dans quelques jours, tranchera.

### F-EXC — Hygiène des marqueurs tenue sur les deux tirs

`Failed to parse entity headers` 0, HTTP 429 0, embedding 8192 tokens 0, `Error extracting IHE-XDM` 0 (r2).
Les familles `Embedding failed` (5 366) et `[Tagging] Failed` (2 715) du tir 1000 tombent à 0 à 500 : effets de
la saturation, instruction close. `SmtpCommandException` / `keep-alive NOOP failed` : serveur SMTP du banc, connu.

## Propositions de tasks `/po` (à arbitrer par le PO — proposées, jamais créées d'office)

1. **F-AUDIT-1** — journal d'audit découplé du pooler praticien, spill sans perte, Redis dédié (conformité).
2. **F-SCRATCH-1** — recréation du répertoire scratch à la demande (robustesse, risque nul).
3. **F-08P01-1** — réglage PgBouncer mesuré au banc (`server_idle_timeout`, `min_pool_size`,
   `server_login_retry`, `query_wait_timeout`) avant portage DevOps ; puis re-tir 1000 pour rendre les latences
   opposables.
4. **F-SEARCH-1** — cache d'embedding de requête + hydratation des résultats.
5. **Instrument** — part des PJ servies par la base dans le rapport (ou scission de l'étape 7), et coût Postgres du
   journal d'audit à 1000 (tir avec journal désactivé, protocole égal).

## Leçons de banc (mémorisées)

- **Ne jamais purger les bases avant une campagne comparative** : l'A/B du matin a détruit l'iso-condition
  « base hydratée non purgée » des deux références, ce qui a coûté la chauffe du tir 1000 (75,6 %) et
  l'opposabilité de l'étape PJ à 500.
- **Garde scratch** : `%TEMP%\mss-ihe-xdm` peut disparaître ; une boucle qui le recrée et date la disparition
  fait partie du pré-vol tant que F-SCRATCH-1 n'est pas corrigée.
- **Ne pas lancer de requêtes Seq lourdes pendant un tir** : les comptages du tir 1000 ont tourné pendant la
  chauffe du tir 500 (hors fenêtre de verdict, mais déclaré).
- Bases **gardées** (49 Go, 1000 praticiens hydratés) et maildir cluster **intact** (UID 365..611) : le prochain
  tir iso se lance avec `UID_BASE=365`, sans seed, `--messages 0` après redémarrage de l'AppHost.
- Le fichier `tests/loadtest-k6/reports/INDEX.md` d'api-mail porte deux lignes nouvelles **non committées**
  (pas de task porteuse) : à embarquer dans la prochaine PR api-mail.
