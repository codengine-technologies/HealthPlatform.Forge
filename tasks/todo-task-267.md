# todo-task-267.md — Le corpus du banc n'a aucun fil de discussion : on ne peut pas mesurer ce qu'on optimise

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune. **Sert de préalable de mesure** à **task-194**
(comptage de fils borné) et, accessoirement, à **task-266** (gating du calcul).
Aucune des deux n'est bloquée par celle-ci — elles sont livrables avant, avec
une mesure partielle qu'elles doivent alors **déclarer comme telle**.
**Priorité**: **3** — outillage de banc. Aucun impact produit, aucun risque
patient.

> **Origine** : constat du 2026-08-20, en instruisant task-266 sur question
> humaine (« comment le test k6 consomme le chargement des listes ? »).

## Objective

Que le corpus semé sur le banc contienne des **fils de discussion**, pour que le
coût du comptage de fils — celui que task-194 optimise — soit réellement exercé
par une campagne.

## Ce qui est établi — état du code au 2026-08-20

`BuildMime` (`tests/mss.mail.loadtest.seed/Program.cs:312-334`) construit chaque
message synthétique avec **`From`, `To`, `Subject`, corps et pièces jointes**, et
rien d'autre. Ni `In-Reply-To`, ni `References`. Une recherche de ces deux
en-têtes sur le seeder et sur le harnais k6 ne renvoie **aucune** occurrence.

Conséquence sur `MailRepository.GetThreadCountsAsync` (`:4039`), le chemin que
task-194 vise :

| Étape de la requête | Sur le banc actuel | Sur une boîte réelle |
|---|---|---|
| `existingMessageIds` — tous les `MessageId` de la base | **exercée** (scan complet, N lignes matérialisées) | exercée |
| `allMailsWithReferences` — lignes porteuses de `References`/`InReplyTo` | **0 ligne** | N lignes |
| Boucle `racines de la page × allMailsWithReferences` avec `Contains` sur `dynamic` | **à vide** — 0 itération | **le coût dominant** |

`MimeKit` génère automatiquement un `Message-Id` à l'envoi, donc la première
requête ramène bien N lignes : **la moitié du coût est mesurée**. La seconde
moitié — celle que task-194 chiffre à « 50 racines × 50 000 lignes = 2,5 millions
de recherches de sous-chaîne à répartition dynamique par page » — ne l'est pas
du tout.

**Ce que ça implique** : une campagne conclurait aujourd'hui à un gain modeste
pour task-194, non parce que le correctif est modeste, mais parce que le banc
n'exerce pas ce qu'il corrige.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que le défaut est neutre.** Semer des fils **change le
  corpus**, donc rompt la comparabilité stricte avec toutes les campagnes
  antérieures. C'est acceptable, mais cela doit être **dit** — même exigence que
  task-264 pour le re-fenêtrage de la chauffe. Une mesure dont l'instrument a
  changé sans le dire n'est pas une mesure.
- **Ne pas présumer qu'il faut semer beaucoup.** Une part trop élevée de
  réponses rendrait le corpus atypique dans l'autre sens : une boîte MSSanté
  réelle n'est pas majoritairement composée de fils. La part doit être
  **paramétrable** et son défaut **justifié**, pas choisi au hasard.
- **Ne pas présumer que le défaut du paramètre peut être non nul.** Le
  comportement par défaut du seeder doit rester **exactement** celui
  d'aujourd'hui, sinon toute campagne relancée sans y penser change de nature en
  silence.
- **Ne pas présumer que c'est cosmétique.** Sans fils, un futur régresseur du
  comptage de fils passerait inaperçu sur le banc : le coût qu'il réintroduirait
  serait multiplié par zéro.
- **Ne pas confondre avec task-266.** Celle-ci ne parle pas du calcul ni de son
  déclenchement — uniquement du corpus.

## Ce que la US doit livrer

1. **Des fils dans le corpus semé** : une part paramétrable des messages répond
   à un message précédent de la **même boîte**, avec `In-Reply-To` et
   `References` conformes RFC 5322 (`References` cumulant la chaîne, pas
   seulement le parent).
2. **Défaut rétro-compatible** : sans réglage explicite, le seeder produit
   exactement le corpus d'aujourd'hui (aucun fil). L'activation est **opt-in**.
3. **Des fils de profondeur variée**, pas uniquement des paires — le coût du
   comptage dépend de la longueur des chaînes, et une chaîne de deux ne
   ressemble pas à une chaîne de six.
4. **Le rapport dit ce qu'il a semé** : part de messages en fil et profondeur
   moyenne apparaissent dans le rapport de campagne, au même titre que les
   autres paramètres de corpus. Une campagne dont on ne peut pas relire le
   corpus n'est pas rejouable.
5. **La rupture de comparabilité est énoncée** dans le rapport quand la part est
   non nulle : « ce tir n'est pas comparable aux campagnes à corpus sans fil ».
6. **Un contrôle de budget qui tient** : les fils consomment des UID comme les
   autres messages ; le contrôle de budget de corpus (tasks 253/264) doit
   continuer de passer, ou refuser explicitement.

### Hors scope

- **L'optimisation du comptage** → task-194.
- **Le gating du calcul** → task-266.
- La représentativité clinique du contenu des messages : on sème des en-têtes de
  fil, pas des échanges médicaux vraisemblables.
- Les fils **inter-boîtes** (un message et sa réponse dans deux boîtes
  différentes) : la mesure porte sur le comptage intra-base, une boîte à la fois.

## Definition of Done

- [ ] Build passe (`dotnet build HealthPlatform.Api.Mail.sln`, 0 erreur)
- [ ] Tests passent (0 échec, hors flaky pré-existants documentés)
- [ ] Auto-tests du harnais verts (`selftest.sh`), **tests JS compris**
- [ ] Test : sans réglage explicite, le corpus produit est **identique** à celui
      d'aujourd'hui — aucun `In-Reply-To`, aucun `References`
- [ ] Test : avec une part non nulle, les messages en fil portent un
      `In-Reply-To` **et** un `References` cumulant la chaîne complète, et les
      `Message-Id` référencés **existent** dans la même boîte
- [ ] Test : la profondeur des fils varie (au moins deux profondeurs distinctes
      sur un corpus semé)
- [ ] Test : le rapport de campagne publie la part de messages en fil et la
      profondeur moyenne
- [ ] Test : quand la part est non nulle, le rapport **énonce** la rupture de
      comparabilité
- [ ] Le contrôle de budget de corpus continue de passer (ou refuse
      explicitement, avec un message nommant le geste)
- [ ] **Vérification sur pièce** : après un semis avec fils, la seconde requête
      de `GetThreadCountsAsync` ramène un nombre de lignes **non nul** —
      constaté, pas déduit. C'est le seul critère qui prouve que la US atteint
      son but
- [ ] Aucune donnée de santé : corpus 100 % synthétique, aucun INS, aucun
      contenu clinique réel

## Manual Test Plan

1. Monter le banc local : `cd Api/Mail && dotnet run --project src/AppHost`
   avec le profil « loadtest ».
2. **Semis de référence** — lancer le seeder **sans** réglage de fil.
   **Attendu** : corpus identique à d'habitude. Vérifier en base que la colonne
   `References` est vide sur l'ensemble des messages.
3. **Semis avec fils** — relancer le seeder avec une part non nulle sur une
   boîte neuve. **Attendu** : une partie des messages porte `In-Reply-To` et
   `References` ; les identifiants référencés existent dans la même boîte.
4. Ouvrir la boîte de réception dans le front legacy, **basculer le mode
   d'affichage sur « Conversation »**. **Attendu** : des fils apparaissent, avec
   des badges « N messages » cohérents avec ce qui a été semé.
5. Lancer une campagne courte et ouvrir le rapport. **Attendu** : la part de
   messages en fil et la profondeur moyenne y figurent, et la mention de rupture
   de comparabilité est présente.
6. Vérifier que le contrôle de budget de corpus ne refuse pas la campagne.

**Données de test** : corpus synthétique uniquement, aucun patient réel, aucun
INS.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — outillage de banc, aucune exigence produit
- **Exigences DSR honorées** : aucune — aucun changement fonctionnel
- **INS** : sans objet — outillage de test, données 100 % synthétiques
- **Authentification PS** : inchangée — hors périmètre
- **Habilitations** : sans objet
- **Interop CI-SIS** : sans objet — les en-têtes posés sont des en-têtes de
  transport RFC 5322 (`In-Reply-To`, `References`), pas du contenu métier
- **Tracé PGSSI-S** : inchangé
- **Consentement patient** : sans objet
- **Référentiels métier** : aucun
- **Hébergement HDS** : sans objet — environnement de banc
- **AIPD / impact RGPD** : inchangé — aucun traitement nouveau, aucune donnée
  personnelle
