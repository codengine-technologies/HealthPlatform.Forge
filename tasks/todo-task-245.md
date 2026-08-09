# todo-task-245.md — Le pipeline d'enrichissement est le prochain poste de coût, et c'est une boîte noire

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: **task-244** (chauffe lotie) — coordination forte : les deux US
se répondent. Celle-ci peut démarrer avant, elle gagne à être **mesurée** après,
quand un tir 500 termine enfin sa chauffe.
**Priorité**: **1** — c'est le goulot **G1** du premier tir 500, et le seul qui
rompe franchement : un abandon, pas une dégradation.

## Objective

Qu'on puisse répondre à « **où part le temps** dans l'enrichissement d'un
message ? » — exactement comme task-243 l'a fait pour la page d'en-têtes.

C'est une US **d'instrument, pas d'optimisation**. Elle ne rend rien plus rapide.
Elle rend le prochain correctif décidable, et surtout elle **empêche** de l'écrire
sur une intuition. Cette EPIC a déjà annulé une US applicative bâtie sur une cause
plausible et fausse (task-222) ; la règle qui en est sortie s'applique ici mot
pour mot.

## Ce qui est établi — et qu'il ne faut pas re-mesurer

Tir `journey-remote-n500` du 2026-08-09, 500 praticiens, mode distant :

| Fait | Mesure |
|---|---|
| La chauffe expire pour **500 médecins sur 500** | 98 messages en une requête, délai client 300 s |
| Coût unitaire, **borné par le bas** | **plus de 3 s par message** sous la concurrence de 100 médecins |
| p95 serveur de la route `enrich/sync` | **au moins 10 s** — le dernier bucket de l'histogramme sature |
| Le serveur travaille vraiment | `[CdaParsingService] Parsing completed` pendant et après l'abandon client |
| Ce n'est pas qu'une affaire de taille de lot | un `treatment` de **2 messages** a aussi expiré au palier 500 |

**Ce que la télémétrie ne sait PAS dire aujourd'hui** : la répartition de ces
secondes entre le **fetch IMAP du corps**, l'**extraction de l'archive XDM**, le
**parsing CDA**, la **génération d'embedding** et les **écritures base**. Sans
cette décomposition, tout remède est une devinette.

## Ce que la US doit livrer

Le pendant de `DbOperationScope` (task-243) pour le pipeline d'enrichissement :
un périmètre par message enrichi, découpé en phases nommées, **non ré-entrant**,
et **sans coût hors périmètre**. Plus un compteur du **nombre de messages par
requête**, pour distinguer « un message lent » de « trente messages moyens » —
deux remèdes sans rapport.

Les buckets d'histogramme doivent couvrir la **dizaine de secondes** : au-delà de
10 s le p95 actuel sature et ne dit plus rien, défaut constaté sur ce tir.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que c'est le parsing CDA.** C'est le candidat évident, donc
  celui qu'il faut se garder de désigner avant mesure. Le fetch IMAP distant
  (94 ms de latence injectée, corps d'environ 124 Ko) est tout aussi plausible.
- **Ne pas présumer que c'est le mode distant.** Le coût unitaire doit être mesuré
  **des deux côtés**, banc local et cluster : sinon on imputera au réseau ce qui
  appartient au traitement.
- **Ne pas optimiser en passant.** Si une évidence saute aux yeux, la consigner
  comme finding et la traiter dans une US suivante — mesurée. Une US d'instrument
  qui optimise ne peut plus prouver son propre effet.

## Definition of Done

- [ ] Chaque message enrichi produit une décomposition par phase (fetch IMAP,
      extraction XDM, parsing CDA, embedding, écriture base), en histogrammes
- [ ] Un compteur donne le **nombre de messages par requête** d'enrichissement
- [ ] Les buckets couvrent au moins **30 s** — plus aucune saturation de p95
- [ ] **Hors périmètre, rien ne coûte** : sans scope actif, ni allocation ni série
- [ ] `report.py` publie la décomposition et **la phrase attribuable** : « sur les
      X ms d'un enrichissement, A ms sont le fetch, B le parsing, C l'écriture »
- [ ] Si les phases ne somment pas au total, le rapport **le dit**
- [ ] Tests unitaires du scope + tests du rendu rapport, dont un cas « aucune
      donnée » qui écrit son absence au lieu de rendre une table vide
- [ ] Aucune donnée de santé dans les étiquettes : ni INS, ni contenu CDA, ni objet

## Manual Test Plan

- Monter le banc (skill `loadtest-skill`), en local **puis** en distant
- `POST .../emails/enrich/sync` sur 10 UID frais, puis lire la section
  « Où part le temps d'un enrichissement » du rapport
- Vérifier que la somme des phases explique le total à quelques pourcents près
- Contrôler dans Seq qu'aucune étiquette ne porte de donnée patient

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — observabilité interne
- **Exigences DSR honorées** : aucune
- **INS** : ⚠️ le pipeline manipule des CDA porteurs d'INS — **aucune étiquette de
  métrique ni aucun journal ajouté ne doit en contenir**. C'est le point de
  vigilance n°1 de cette US.
- **Authentification PS / Habilitations / Consentement / Interop CI-SIS** : inchangés
- **Tracé PGSSI-S** : métriques d'exploitation uniquement, corrélées par `traceId`
- **Hébergement HDS** : l'instrument doit être transposable à l'environnement cible
- **AIPD / impact RGPD** : inchangé — aucune donnée nouvelle collectée
