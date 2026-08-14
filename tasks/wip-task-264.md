# todo-task-264.md — La chauffe consomme 139 % de la fenêtre de son palier : le palier mesure surtout sa propre préparation

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: **task-253** (`archived`) a rendu la chauffe aboutissante et a
posé l'avertissement de part de fenêtre. Celle-ci traite le cas où
l'avertissement se déclenche.
**Priorité**: **3** — le tir reste **lisible** puisque le rapport le dit ; mais
toute campagne future à forte population souffrira du même travers.

## Objective

Qu'un palier de campagne mesure un **régime établi** et non sa propre mise en
condition.

## Ce qui est établi — tir `journey-500-esc` du 2026-08-14

| Grandeur | Valeur |
|---|---|
| Chauffe au p95 (attente de vague incluse) | **2 494 s** |
| Fenêtre du palier | 1 800 s |
| **Part consommée** | **139 %** — plafond de l'avertissement : 50 % |
| Chauffe aboutie | **99,1 %** de 464 médecins (plancher 90 %) ✅ |

**Le tir reste opposable** : la chauffe a abouti, donc la base servant les étapes
« ouvrir l'inbox », « message enrichi », « dossier patient » et « fiche patient »
est peuplée, et leurs verdicts tiennent. Mais **une partie de la fenêtre a
mesuré la préparation**, pas le régime.

**Ce qui borne le gain côté harnais** : le débit d'enrichissement du serveur
(~9,5 messages/s, task-245). Étaler la chauffe ne la rend pas plus rapide — c'est
task-254 qui a relevé ce plafond, et task-255 a montré que le débit **croît**
avec la concurrence, donc le levier existe.

**Ce qui a déjà été tenté** : task-244 (refus d'un verdict sans chauffe),
task-253 (chauffe par vagues, décalage par rang de cohorte). Le problème n'est
plus que la chauffe échoue — c'est qu'elle **dure**.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer qu'allonger la fenêtre suffit.** Le contrôle de budget du
  parcours refuse les campagnes trop longues : les réserves d'UID par boîte sont
  finies, et une fenêtre plus longue consomme plus de corpus. Le 2026-08-14, une
  campagne de 143 min a été **refusée** pour cette raison. Les deux contraintes
  se contredisent, et c'est le cœur du sujet.
- **Ne pas présumer que réduire la réserve analysée est sans effet.** Moins de
  messages analysés, c'est un dossier patient plus maigre, donc des étapes 10 et
  11 qui mesurent autre chose.
- **Ne pas présumer que c'est un défaut de l'application.** La chauffe est un
  artefact **de protocole de mesure**. Le débit d'enrichissement, lui, est un
  sujet applicatif traité ailleurs.
- **Ne pas chauffer hors fenêtre sans le dire.** Une chauffe préalable au tir
  changerait la nature de la mesure — à documenter explicitement si c'est le
  levier retenu.

## Ce que la US doit livrer

Un protocole où la chauffe **n'ampute plus** la fenêtre de mesure, sans violer le
budget de corpus. Les pistes à instruire — **aucune n'est choisie d'avance** :

- **Chauffe préalable, hors fenêtre mesurée** : une phase dédiée avant le premier
  palier, dont la durée ne compte pas dans le régime. Consomme du corpus : à
  confronter au contrôle de budget.
- **Chauffe incrémentale par palier** : seuls les médecins **nouveaux** d'un
  palier chauffent, ceux du palier précédent étant déjà chauds. À 500, cela
  ramènerait la chauffe à 300 médecins au lieu de 500.
- **Fenêtre de mesure décalée** : le régime ne commence à être mesuré qu'une fois
  la chauffe aboutie, et le rapport ne juge que cette sous-fenêtre.

## Definition of Done

- [ ] Auto-tests du harnais verts (`selftest.sh`), **tests JS compris**
- [ ] Sur un tir à forte population, la part de fenêtre consommée par la chauffe
      **passe sous 50 %**, ou le rapport **explique pourquoi c'est impossible**
      et pose le seuil
- [ ] Le **contrôle de budget de corpus continue de passer** — le remède ne doit
      pas se payer en refus de campagne
- [ ] Le rapport **distingue** la fenêtre de chauffe de la fenêtre de régime, et
      dit laquelle porte chaque verdict
- [ ] Si la chauffe est déplacée hors fenêtre, le rapport le **dit** — une mesure
      dont la préparation est invisible n'est pas comparable à une mesure où elle
      ne l'était pas
- [ ] **Contre-épreuve** : deux tirs à protocole identique, avant/après, avec
      part de fenêtre et verdicts SLO comparés. Les verdicts ne doivent **pas**
      s'améliorer par construction — si le changement rend des étapes vertes qui
      ne l'étaient pas, c'est un **biais**, pas un gain, et il faut le dire

## Manual Test Plan

- Monter le banc distant, population d'au moins 200 médecins
- Lancer un escalier à deux paliers
- **Ce qu'il faut voir** : la part de fenêtre consommée par la chauffe, sous
  50 %, et l'indication explicite de la fenêtre sur laquelle porte le verdict
- Vérifier que le taux de chauffe aboutie reste **au-dessus de 90 %**
- Vérifier que le contrôle de budget de corpus ne refuse pas la campagne

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — outillage de banc
- **Exigences DSR honorées** : aucune — aucun changement fonctionnel
- **INS** : sans objet — outillage de test, données 100 % synthétiques
- **Interop CI-SIS** : sans objet
- **Habilitations** : sans objet
- **Authentification PS / Consentement** : inchangés
- **Tracé PGSSI-S** : inchangé
- **Hébergement HDS** : sans objet
- **AIPD / impact RGPD** : inchangé

## Branches

- `api-mail` (pushed) : feat/task-264-chauffe-fenetre
- `dtos-mss` (pushed, auto-inclus) : feat/task-264-chauffe-fenetre — aucune modification attendue

## Develop log (2026-08-15)

**Levier retenu : fenêtre de mesure décalée, dérivée du MODÈLE** — pas observée
(les VU k6 n'ont aucun état partagé : personne ne peut savoir à l'exécution
quand « la cohorte » a fini de chauffer). L'allocation se calcule d'avance des
grandeurs qui étalent déjà les vagues (task-253) : vagues pleines de
maxConcurrent médecins × réserve analysée ÷ débit plafond. Vagues PLEINES à
dessein : sous-évaluer remettrait de la chauffe dans le régime — l'erreur est
du côté sûr. La « chauffe incrémentale » demandée par la US **existait déjà**
(task-253, rang de cohorte) : l'allocation d'un palier se calcule sur sa
cohorte NOUVELLE (à 500 après 200 : 300 médecins, 44 % d'une fenêtre de
1 800 s — sous les 50 %).

Livré (`5edfeba`, `84c6dcd`) : `warmupWindowSeconds` + `warmupWindowChecks`
(refus si l'allocation avale la fenêtre — aucun régime = aucun verdict ;
avertissement > 50 %) ; `buildStagePlan` porte `warmupEndS` par palier
(défaut : comportement historique intact) ; `palierAt` tague `chauffe` pendant
l'allocation — ces requêtes n'entrent dans AUCUN verdict ; report.py publie
« Fenêtres de verdict » (chauffe/régime par palier, laquelle porte le verdict,
et la rupture de comparabilité DITE) ; les tirs archivés sans `warmupEndS`
gardent leur récit d'origine. Budget de corpus INCHANGÉ (re-fenêtrage, aucune
consommation déplacée).

Tests : 6 cas node --test + 4 unittest ; mutation (branche `chauffe` de
palierAt neutralisée → rouge) ; selftest.sh intégralement vert, zéro SKIP.

**Contre-épreuve (DOD)** — deux tirs à protocole identique, banc local
(`2:120s,4:120s`, seed 4×100, reset-state entre jambes) :
| | Jambe A (develop) | Jambe B (task-264) |
|---|---|---|
| Chauffe dans la fenêtre | incluse | **allouée [+30..+64s] et [+180..+214s], 28 %, taguée `chauffe`** |
| Verdicts SLO | échantillons insuffisants (échelle locale) | idem — **pas verdis par construction** |
| p95 dashboard (palier max) | 361 ms | 667 ms — l'exclusion ne flatte pas |
| Chauffe aboutie / budget | 100 % / passé | 100 % / passé |
Rapports : `reports/2026-08-15/journey-264-leg{A,B}-contre-epreuve.md` (INDEX
committé ; répertoire daté gitignoré, conservé localement).

**Part < 50 % à forte population** : établie par le modèle (500 : 789 s /
1 800 s = 44 %) — à confirmer en distant à la prochaine campagne ; au-delà de
50 %, le rapport avertit et nomme le geste (allonger le hold), le refus ne
tombe que sur régime nul. Banc local éteint après la contre-épreuve.

## Simplify log (2026-08-15)

Skip propre — modèle pur + calendrier + rapport, dans les modules et styles
existants (journey-model/report), aucun axe actionnable. dtos-mss non touché.

## Sonar log (2026-08-15)

Skip propre — aucun fichier C# modifié (JS/Python du harnais uniquement, hors
périmètre dotnet-sonarscanner). Build api-mail : 0 erreur. QG develop : OK.
