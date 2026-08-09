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
