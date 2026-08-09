# todo-task-247.md — Ouvrir sa boîte coûte 1,2 seconde, et 80 % de ce temps n'est pas de la base

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: **task-243** (`archived`) — c'est elle qui a rendu ce coût
décomposable. Aucune dépendance bloquante ; **task-245** est indépendante.
**Priorité**: **1 (produit)** — c'est le **premier poste de coût du parcours du
médecin**, et la cause est désormais mesurée, plus supposée.

## Objective

Réduire le coût d'ouverture de la boîte de réception, en s'attaquant au poste que
la mesure désigne : la **construction des données renvoyées**, pas la base.

C'est la première US **d'optimisation** de cette série. Elle n'existe que parce
que task-243 a instrumenté et que task-242 a mesuré : on sait quoi corriger, et on
saura le prouver.

## Ce qui est établi — mesuré, pas supposé

Tir local 200 praticiens du 2026-08-08, instrument de task-243 :

| `GetMailsByUids` — la page d'en-têtes | Valeur |
|---|---|
| Moyenne totale | **1 199,7 ms** |
| **Matérialisation / construction des DTO** | **961,6 ms — 80,2 %** |
| Exécution SQL | 236,2 ms — 19,7 % |
| **Attente d'une connexion à la base** | **1,8 ms — 0,1 %** |
| **Requêtes SQL par appel** | **14,8** (l'analyse de code annonçait « 6 à 8 ») |

**La contention base est écartée par la mesure**, et elle l'est deux fois : le
tir 500 distant du 2026-08-09 redonne **0,1 %** sur un régime pourtant
complètement différent. C'est un invariant, pas une coïncidence.

**Effet sur le médecin** : l'étape « ouvrir / rafraîchir l'inbox » sort de la
grille SLO au palier 200 — p95 **5 198 ms** pour une cible de 1 000 ms.

**Un finding déjà consigné et non corrigé**, qui vit dans ce chemin
(**F-243-1**) : `ComputeThreadCountsAsync` lit **toute la table `Mails`** du
praticien à chaque page d'en-têtes — deux requêtes sans filtre de dossier, de page
ni de génération
([MailRepository.cs:1301-1310](../Api/Mail/src/Infrastructure/Repository/MailRepository.cs#L1301-L1310)).
Ce coût suit la **taille de la boîte**, pas celle de la page : modeste à 247
messages au banc, deux scans complets par ouverture à 50 000 messages pour un
praticien réel.

**Confirmation croisée, inattendue** : au tir 500 sur base quasi vide, le même
appel tombe à **55,4 ms et 7,8 requêtes**. Les ~7 requêtes et ~927 ms qui
disparaissent sont exactement ce que coûte le **contenu** (tags, destinataires,
pièces jointes, identifiants enrichis, acquittements). Le levier est donc bien là.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que réduire le nombre de requêtes suffit.** 14,8 requêtes
  groupées ne font pas 961 ms à elles seules : une partie du coût est le travail
  CPU et les allocations de la construction elle-même. Les deux axes doivent être
  mesurés séparément **avant** d'être traités.
- **Ne pas présumer que F-243-1 est LA cause.** C'est un candidat sérieux, établi
  par lecture de code et non par mesure isolée. Le chronomètre de task-243 doit le
  confirmer ou l'écarter — il apparaîtra dans `sql_execute` **et** dans le reste.
- **Ne pas toucher au dimensionnement du pooler.** Il gagnerait 0,1 %.

## Definition of Done

- [ ] Le nombre de requêtes SQL par appel de `GetMailsByUids` est **réduit**, et
      la valeur avant/après est **mesurée** par le compteur de task-243
- [ ] `ComputeThreadCountsAsync` ne lit plus la table entière : filtre de dossier,
      de page et de génération — ou le rapport explique pourquoi c'est impossible
- [ ] **Le gain est prouvé par un A/B iso-conditions** sur la lignée courante :
      même corpus, même population, un seul facteur, décomposition task-243 avant
      et après
- [ ] L'étape « ouvrir / rafraîchir l'inbox » **rentre dans la grille** au palier
      200 (p95 < 1 000 ms), ou l'écart résiduel est expliqué et chiffré
- [ ] Aucune régression fonctionnelle sur le comptage des fils de discussion —
      tests unitaires sur le comptage, **écrits avant** le correctif
- [ ] Tests unitaires sur les nouveaux chemins de requête (au moins un par branche)

## Manual Test Plan

- Lancer l'app localement, ouvrir la boîte de réception d'un praticien du banc
- Vérifier que la liste affiche les **mêmes** messages, avec les mêmes compteurs
  de fils, les mêmes tags et les mêmes marqueurs de pièce jointe qu'avant
- Ouvrir une boîte volumineuse (plusieurs milliers de messages) : le temps
  d'ouverture ne doit plus croître avec la taille de la boîte
- Au banc : comparer la section « Où part le temps d'une lecture servie par la
  base » avant et après

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — performance, aucun changement fonctionnel
- **Exigences DSR honorées** : aucune exigence nouvelle ; la US ne doit **pas**
  dégrader l'affichage des métadonnées MSSanté déjà rendues
- **INS** : non manipulé directement — ⚠️ les identifiants enrichis chargés par ce
  chemin peuvent porter de l'INS : aucun ne doit apparaître dans un journal ou une
  étiquette de métrique
- **Authentification PS / Habilitations** : inchangées — le cloisonnement « une
  base par praticien » ne doit **pas** être affaibli par un regroupement de requêtes
- **Consentement / Interop CI-SIS / MSSanté** : non applicable
- **Tracé PGSSI-S** : inchangé
- **Hébergement HDS** : sans objet
- **AIPD / impact RGPD** : inchangé
