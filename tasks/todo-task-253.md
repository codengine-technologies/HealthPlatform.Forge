# todo-task-253.md — La chauffe lotie ne passe toujours pas : son délai ignore le pic de concurrence

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: **task-244** (`archived`) — celle-ci en corrige la calibration,
elle ne la refait pas. **task-245** (`archived`) fournit le chiffre qui la règle.
**Priorité**: **1 — bloquante.** Elle est petite, et **rien d'autre ne peut être
mesuré tant qu'elle n'est pas livrée** : un tir long re-mesurera une base
partiellement vide, exactement comme le tir 500 du 2026-08-09.

## Objective

Que la chauffe du parcours **aboutisse** à l'ouverture d'un palier, quand tous les
médecins du palier chauffent en même temps.

## Ce qui est établi

task-244 a loti la chauffe : au lieu d'une requête de 98 UID, elle envoie des lots
de 10, avec un délai dérivé — `lot × 3,5 s × 2 = 70 s`. **C'était le bon geste** :
un lot abouti est désormais **acquis**, là où l'ancienne requête unique perdait
tout. Mais la mesure suivante est sans appel.

Tir `enrich-245-n100` du 2026-08-09, 100 médecins en mode distant :

| Fait | Mesure |
|---|---|
| Lots de chauffe expirés | **100 sur 100 médecins** |
| Itérations du parcours en 10 minutes | **14** — les VU passaient leur temps en chauffe |
| Coût réel d'un enrichissement (instrument task-245) | **2 691,7 ms par message** |

**La cause est arithmétique.** Les 3,5 s par message qui dérivent le délai sont la
borne basse relevée **en régime établi** au palier 500. Or à l'**ouverture** d'un
palier, tous les médecins chauffent simultanément : la concurrence instantanée est
bien supérieure à celle du régime, et le coût unitaire avec elle. Un lot de 10
messages à 2,7 s l'un vaut déjà 27 s au repos ; sous le pic, il franchit les 70 s.

**Corroboration indépendante** (pré-chauffe hors k6 du 2026-08-09) : le coût
unitaire suit la concurrence — **0,59 s/message** à 4 requêtes parallèles,
**2,11 s** à 20 — pour un débit qui ne passe que de 6,8 à 9,5 messages/s.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer qu'il suffit d'allonger le délai.** C'est le geste réflexe, et
  il déplace le problème : une chauffe qui met dix minutes retarde d'autant le
  régime mesuré, et le palier n'est plus stabilisé quand la mesure commence.
- **Ne pas présumer qu'il suffit de réduire le lot.** Un lot de 2 messages passera,
  mais multipliera les requêtes ; le coût total de la chauffe ne bougera pas — il
  est conduit par le coût unitaire, que **task-254** traite.
- **Ne pas affaiblir la garde de refus** livrée par task-244. Elle a parfaitement
  fonctionné : c'est elle qui a rendu ce tir lisible comme non concluant.

## Ce que la US doit livrer

Une chauffe qui aboutit **sans** retarder le régime. Deux directions à arbitrer par
la mesure, pas par principe :

1. **Étaler la chauffe** — les VU ne chauffent pas tous à la même seconde, mais
   répartis sur la rampe du palier. Supprime le pic sans changer le coût total.
2. **Dériver le délai de la concurrence** — le budget d'un lot tient compte du
   nombre de médecins qui chauffent en même temps, et non du seul coût unitaire.

Les deux sont compatibles. Ce qui compte est que le **critère observable** soit
tenu : zéro lot expiré à l'ouverture d'un palier de 200 en mode distant.

## Definition of Done

- [ ] **Zéro lot de chauffe expiré** sur un tir 200 en mode distant, à l'ouverture
      de chaque palier
- [ ] La chauffe ne retarde pas le régime : la part de la fenêtre de palier passée
      en chauffe est **mesurée** et rendue dans le rapport
- [ ] La règle retenue (étalement, budget dérivé de la concurrence, ou les deux)
      est **écrite** dans `docs/loadtest.md`, avec le chiffre qui la fonde
- [ ] La garde de refus de task-244 est **inchangée** — un test le prouve
- [ ] Tests du harnais : un cas « ouverture de palier, N médecins simultanés →
      aucun lot expiré » et son **témoin négatif** « délai volontairement abaissé →
      la garde refuse toujours le verdict »
- [ ] `tests/loadtest-k6/selftest.sh` vert, suite Python verte

## Manual Test Plan

- Monter le banc en mode distant (`MSS_LOADTEST_MAIL_HOST`)
- Tir court à deux paliers (`JOURNEY_STAGES="50:8m,100:8m"`, K=1) : à chaque
  ouverture de palier, **aucun** `warmup failed` dans la sortie k6
- Contrôler dans le rapport la part de fenêtre consommée par la chauffe
- Abaisser volontairement le délai et vérifier que la garde repeint le tir en refus
  (contre-épreuve : la garde n'a pas été affaiblie)

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — outillage de banc
- **Exigences DSR honorées** : aucune — aucun changement fonctionnel
- **INS / Authentification PS / Habilitations / Consentement / Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : non applicable — métriques de banc, données synthétiques
- **Sécurité** : aucun contenu CDA ni identifiant patient dans les journaux du harnais
- **Hébergement HDS** : sans objet (banc de test)
- **AIPD / impact RGPD** : inchangé

## Ce qui a été livré (2026-08-09, directement sur `develop`)

> ⚠️ Développée **directement sur `develop`** à la demande humaine — pas de branche
> `feat/*`, pas de PR, donc **pas de HAG sur cette task** (même régime que
> task-243). Commit `5d056db`.

**La correction, et pourquoi celle-là.** Le fait qui commande tout est que le débit
d'enrichissement du serveur est **plafonné** (mesuré : 0,59 s/message à concurrence
4 soit 6,8 msg/s ; 2,11 s à 20 soit 9,5 msg/s — ×5 de concurrence pour +40 % de
débit). Chauffer N médecins × R messages prend donc `N × R / débit` secondes **quoi
qu'on fasse**. Allonger le délai d'un lot ne crée pas de débit : ça transforme une
expiration en attente. Le seul levier côté harnais est de **borner la concurrence**.

| Livré | Où |
|---|---|
| Chauffe par **vagues** de `JOURNEY_WARMUP_MAX_CONCURRENT` (8), décalage déduit de l'index du VU — aucun état partagé | `lib/journey-model.js`, `scenarios/journey.js` |
| Délai d'un lot dérivé de la concurrence **bornée** (`warmupCostSecondsPerMessage`, interpolation sur les deux points mesurés) et non plus d'un forfait de régime | `lib/journey-model.js` |
| `journey_warmup_elapsed_s` — le temps **prélevé sur la fenêtre**, attente de vague incluse | `scenarios/journey.js` |
| Ligne de rapport « part de la fenêtre consommée », avertissement au-delà de **50 %** | `report.py` |
| Règle et chiffres fondateurs | `docs/loadtest.md` § 4d règle **5b**, `README.md` |

**La première vague ne patiente pas** : la chauffe démarre bien à la première
seconde du palier, elle est seulement étalée.

**Pourquoi le plafond de fenêtre est à 50 % et pas 25 %** : à 100 médecins et 98
messages, le plafond serveur impose déjà ~17 min sur une fenêtre de 32. Exiger plus
court reviendrait à refuser tout tir jusqu'à ce que **task-254** relève ce plafond —
c'est le vrai remède, et il est côté application.

### DOD — état

- [x] Délai dérivé de la concurrence bornée, plus du coût en régime
- [x] Part de la fenêtre consommée par la chauffe **mesurée et rendue**
- [x] Règle écrite dans `docs/loadtest.md` avec les chiffres qui la fondent
- [x] Garde de refus de task-244 **inchangée** — prouvé par `TaskTwoFortyFourGateIsIntactTests`
- [x] Tests : vagues, coût selon concurrence, refus de NaN, témoin de physique
      (le retard total reste borné par le débit), et **témoin négatif** de la garde
- [x] `selftest.sh` vert — **268 tests Python, 45 tests JS**
- [ ] **Zéro lot expiré sur un tir 200 distant** — exige un tir, non fait ici

**Le seul critère ouvert est une mesure**, pas du code : il se referme au prochain
tir, qui est de toute façon celui qui doit aussi prouver task-247.

### Écart assumé

`/sonar` non joué : **aucun fichier C# touché** (harnais Python/JS et documentation
uniquement) — le périmètre de la solution .NET n'est pas concerné.
