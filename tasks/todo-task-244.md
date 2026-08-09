# todo-task-244.md — Un tir sans chauffe ne doit plus pouvoir rendre un verdict vert

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune (outillage de banc, indépendant du code applicatif)
**Priorité**: **1 — bloquante.** Tant qu'elle n'est pas livrée, **aucune campagne
500 ne produit de latence comparable**, et le rapport peut publier « 8 étapes
vertes sur 11 » sur un tir qui n'a rien mesuré.

## Objective

Que la chauffe du parcours passe à 500 praticiens, et que **si elle échoue quand
même, le rapport refuse le verdict de toutes les étapes servies par la base** —
au lieu de les rendre vertes.

## Ce qui est établi — tir `journey-remote-n500` du 2026-08-09

- La chauffe envoie les **98 UID de la réserve analysée en UNE requête**
  `enrich/sync` (`tests/loadtest-k6/lib/api.js`, délai client **300 s**). Elle a
  expiré pour **500 médecins sur 500**, dès le palier 100.
- Le serveur, lui, **travaillait** : `[CdaParsingService] Parsing completed`
  pendant et après l'abandon du client. Ce n'est pas une panne, c'est un délai.
- Conséquence mesurée par l'instrument de task-243 : base quasi vide, donc
  `GetMailsByUids` à **55,4 ms / 7,8 requêtes par appel** contre **1 199,7 ms /
  14,8** au tir local 200 de la veille. Les latences du tir sont **flattées**.
- Le garde-fou de task-224 a bien refusé l'**étape 3** (« ⛔ étape mal nommée »).
  Il **ne propage pas** ce refus aux étapes 2, 10 et 11, qui sont pourtant
  servies par la même base vide et sont passées **vertes**.

## Ce que la US doit livrer

1. **Une chauffe qui passe** : lotir l'appel (N UID par requête, N à déterminer
   par la mesure, pas par intuition), avec un délai cohérent avec le coût
   unitaire réel.
2. **Un échec de chauffe qui se voit** : compté comme un **refus explicite**
   (une ligne de verdict), pas comme 500 lignes d'erreur noyées dans le log.
3. **La propagation du refus** : si la part de chauffe réussie est sous un seuil,
   **toute étape servie par la base** est rendue non opposable dans le rapport,
   avec la raison écrite. Le même principe que task-224, étendu à sa portée
   logique.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que réduire le lot suffit.** Le `treatment` du parcours réel
  — **2 messages par lot** — a lui aussi expiré une fois au palier 500. Le coût
  unitaire est le sujet ; le lot n'est que le déclencheur. C'est task-245 qui
  l'établira, et cette US **n'attend pas** son résultat pour lotir.
- **Ne pas présumer que le seuil de refus est 100 %.** Une chauffe partiellement
  réussie n'est pas forcément inutilisable — c'est la part servie par la base
  (`warm_served`) qui décide, et le seuil doit être posé et écrit.

## Definition of Done

- [ ] La chauffe est lotie ; un tir 500 en mode distant la termine sans timeout
- [ ] Un échec de chauffe produit **une** ligne de verdict lisible, pas N erreurs
- [ ] Sous le seuil de chauffe servie, le rapport marque **toutes** les étapes
      servies par la base comme non opposables, avec la raison
- [ ] Le seuil retenu est **écrit** dans le rapport et dans `docs/loadtest.md`
- [ ] Tests du harnais : un cas « chauffe échouée → aucune étape base opposable »
      et son **témoin négatif** « chauffe réussie → verdict rendu normalement »
- [ ] `tests/loadtest-k6/selftest.sh` vert, suite Python verte

## Manual Test Plan

- Monter le banc en mode distant : `MSS_LOADTEST_MAIL_HOST=192.168.1.69`
- Tir court (`JOURNEY_STAGES="100:5m"`, K=1) : la chauffe doit se terminer
- Forcer l'échec (délai client abaissé) et régénérer le rapport : vérifier que
  les étapes 2, 3, 10 et 11 portent toutes le refus, pas seulement la 3
- Lire le bandeau de tête : il doit dire que le tir ne mesure pas la capacité

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS) — **Vague** : hors Ségur
- **Exigences DSR honorées** : aucune — outillage de banc, aucun changement fonctionnel
- **INS / Authentification PS / Habilitations / Consentement / Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : non applicable — métriques de banc, données synthétiques
- **Sécurité** : aucun contenu CDA ni identifiant patient dans les journaux du harnais
- **Hébergement HDS** : sans objet (banc de test)
- **AIPD / impact RGPD** : inchangé
