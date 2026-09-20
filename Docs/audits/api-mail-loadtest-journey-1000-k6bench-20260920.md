# Campagne de charge — premier journey 1000 depuis le tireur dédié `linux-k6` (2026-09-20)

> Tir `journey-1000-k6bench-20260920`, 12:24:38 → 13:25:57 (1 h 01, dont régime 56 min).
> Code : `develop` à `42707fa` (task-322 mergée) ; harnais `05135288`. Banc mail cluster
> `192.168.1.69` (latence injectée 96 ms), registre `mss_registry_loadtest`, population
> hydratée (`UID_BASE=365`, `MESSAGES_PER_USER=247`, `JOURNEY_WARMUP_HYDRATED=1`).
> **Tireur : k6 2.1.0 sur `linux-k6` (VM VMware, 4 vCPU, 32 Go)**, cible le poste par
> relais `netsh portproxy` `192.168.1.53:5052`.
> Source k6 : `Api/Mail/tests/loadtest-k6/reports/2026-09-20/journey-1000-k6bench-20260920-132557.json` ;
> rapport harnais : `report-journey-1000-k6bench-20260920-132557.md` ;
> lignée : `manifest-k6-journey-20260920-122438.txt`.

## Verdict : ⛔ VOID pour le produit — le tir a mesuré le réseau entre le tireur et le poste

Le rapport harnais classe le tir 🔴 (SLO 2/11 vertes, `http_req_failed` 8,6 %,
`read_list` 20 062 échecs sur 40 495). **Aucun de ces chiffres n'est opposable au
produit.** Le chemin réseau tireur → système sous test plafonne à **12,7 Mo/s**
(classe 100 Mbit/s), mesuré trois fois à froid, banc à l'arrêt :

| Mesure (à vide, après le tir) | Résultat |
|---|---|
| `dd 300 Mo \| ssh k6bench` (brut, borne basse) | **12,7 Mo/s** |
| 6 pages d'en-têtes séquentielles via le relais | 8,1 Mo/s |
| 8 pages en parallèle via le relais | **8,7 Mo/s agrégés** (5,3 s) |
| 8 pages en parallèle, poste en loopback | **0,44 s** (≈ 110 Mo/s) |
| Carte du poste / de la VM | 1 Gbit/s (Realtek) / 10 Gbit/s (vmxnet3) |

Or la **page d'en-têtes pèse 6,04 Mo pour 25 messages** (`GET
/mail/folders/INBOX/emails/{ids}`, user 1, servie en 0,1 s sur le poste). À 1 000
médecins elle est appelée ~6 fois/s : **36 Mo/s pour cette seule route**, trois fois
ce que le lien transporte. Le serveur passe alors son temps à *écrire* ses réponses
— le p50 **serveur** de la route est à 59,9 s sur les six tranches de 10 min, borné
par le délai client de 60 s — et k6 abandonne. Signature complète :

- 620 erreurs k6 à 4 min, 41 221 à la fin : `read_list … HTTP 0 (request timeout)`
  dominant, quelques `dial: i/o timeout` et `connection reset` ;
- côté api-mail : 104 106 `OperationCanceledException`, 63 221 `IOException`,
  41 043 `ConnectionResetException` sur l'heure — des clients qui raccrochent ;
- **le produit n'est pas saturé** : api-mail 1,3 cœur cumulé en moyenne (max 8),
  hôte 40 % moyen, Postgres 1 020 backends puis 568, `cl_waiting` 0, 0 refus de login,
  ~400 requêtes HTTP actives (des écritures en attente), 2 100 sessions IMAP (≈ 2 par
  médecin, conforme) ;
- **le tireur n'est pas saturé** : k6 0,37 cœur moyen / 0,92 max sur 4, RSS max
  5,45 Go, 2 181 connexions TCP établies.

Pour comparaison, le journey 1000 hydraté du 17/09 (même population, même code
moins task-322, k6 sur le poste en loopback) rendait `read_list` p50 client 20,2 s /
serveur 7,2 s, sur un **hôte saturé à 99 %**. Les deux tirs sont invalides pour des
raisons opposées : l'un manquait de CPU, l'autre de réseau.

## Ce que le tir a tout de même établi

1. **La chaîne tireur distant fonctionne** de bout en bout sur un tir long :
   publication par `tar | ssh`, tmux détaché, 1 000 VU, remote-write Prometheus
   (78 req/s vus des deux côtés), échantillonneur du tireur fusionné dans celui du
   poste et lu par `report.py` (`k6#2385`), photos `pg_stat_statements`, MANIFEST.
2. **La chauffe hydratée tient sa promesse** : 275 s (992 lots ok / 8 ko) contre
   10 346 s le 17/09 — le régime commence à 4 min 35 au lieu de 2 h 52.
3. **4 vCPU / 32 Go suffisent** au journey 1000 côté k6 (< 1 cœur, 5,5 Go) ; le
   dimensionnement précédent (2 vCPU, 23 Go) aurait été juste en mémoire.
4. **La page d'en-têtes à 6 Mo est un fait produit**, indépendant du banc : c'est
   le « HTML des documents » déjà identifié comme reste après task-322 (voir
   `api-mail-loadtest-terrain-1000-ab-task322-*`). Sur une liaison praticien
   réelle (ADSL/4G, 1 à 5 Mo/s), 25 en-têtes = 1 à 6 s de transfert avant toute
   latence serveur. À instruire côté PO (pagination du contenu, compression HTTP,
   ou projection sans HTML) — **un finding lu dans la mesure, pas une US écrite**.

## Défauts de l'outillage trouvés et corrigés pendant le tir

- `remote.sh wait` sortait sur un hoquet ssh (code 255 pris pour « session finie »,
  12:49) : la fin de session est désormais le fichier `.rc`. Conséquence : le
  sampler du poste a été arrêté puis relancé, **trou d'une minute à 12:49** dans
  `observe-124927.csv` (les deux fichiers ont été fusionnés avant le rapport).
- `tar` sortait en 1 (« file changed as we read it ») quand `observe.ps1` écrivait
  son `.pid` dans le dossier publié — c'était le « lancement muet » du matin ;
  toléré désormais.
- `USERS` n'était pas posé au premier lancement : le contrôle de budget du harnais a
  refusé le tir (code 107), correctement.
- `keep-awake.ps1` (nouveau) : PowerShell 5.1 exige un BOM UTF-8, preuve d'armement
  imprimée (`etat precedent=0x80000000`).
- Le preflight du tireur mesure désormais le **débit brut** et refuse
  l'interprétation sous 60 Mo/s.

## Suite

1. **Localiser le maillon à 100 Mbit/s** entre le poste (1 Gbit/s) et l'hôte VMware
   de `linux-k6` : port de switch, câble, uplink de l'ESXi. Contrôle : `remote.sh
   preflight` doit annoncer ≥ 100 Mo/s (`dd | ssh` est une borne basse).
2. **Rejouer ce tir à l'identique** (mêmes variables, `NO_PUBLISH=1`) une fois le
   lien à 1 Gbit/s : c'est le premier journey 1000 qui ne mesurera ni le CPU du
   poste ni le réseau du banc.
3. Ne pas ouvrir de finding produit sur `read_list`, `attachment`, `read_content`
   ou l'envoi à partir de ce tir : toutes ces routes transportent des corps
   volumineux et leurs latences sont celles du lien.
