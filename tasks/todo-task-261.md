# todo-task-261.md — Une page de 25 en-têtes construit 298 objets, dont 65 résultats de biologie : ne plus charger ce qu'on n'affiche pas

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: **task-256** (`archived`) — c'est son compteur d'objets
matérialisés qui rend ce défaut visible et chiffrable. **task-258** (`archived`)
fournit la seconde moitié de la preuve : ce n'est ni la base ni le pool.
**Priorité**: **1** — première US d'optimisation de cette EPIC dont **le coût ET
la cause sont mesurés** avant d'écrire une ligne. La page d'en-têtes est le
troisième poste de coût serveur (11,5 %) et le premier geste du médecin.

## Objective

Que l'ouverture de la boîte de réception cesse de construire des objets qu'elle
n'affiche pas.

## Ce qui est établi — tir `journey-500-esc` du 2026-08-14

**Ce que la page construit** (compteur de task-256, palier 500) :

| `GetMailsByUids` | Valeur |
|---|---|
| Objets construits **par appel** | **298,2** |
| Temps de matérialisation | 68,3 ms |
| Coût par objet | 229 µs |
| **Famille dominante** | **résultats de biologie — 65,2 par appel** |
| messages | 24,8 |
| pièces jointes | 40,2 |
| étiquettes | 37,9 |
| documents médicaux | 24,8 |
| objets de fil | 24,8 |

**La page affiche 25 en-têtes.** Elle construit **65 résultats de biologie** et
**40 pièces jointes** pour les afficher.

**Où part son temps** (décomposition de task-258, palier 500) :

| `GetMailsByUids` | Part |
|---|---|
| Attente d'obtention d'une connexion | **0,1 ms — 0,1 %** |
| Exécution SQL | 30,0 ms — 30,5 % |
| **Le reste : matérialisation, DTO** | **68,3 ms — 69,5 %** |

**Le remède n'est donc ni la base, ni le pool, ni le SQL** : c'est ce que
l'application construit après avoir reçu les lignes. Les deux instruments
concordent — 69,5 % du temps dans la matérialisation, et une famille d'objets
qui domine le décompte.

**Ce que ça pèse** : 2 779 s de temps serveur sur 27 854 appels au palier 500,
soit **11,5 %** du total. Et l'étape reste **verte au SLO** (p95 292 ms pour
1 000) — c'est un coût serveur, pas encore une attente pour le médecin.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que la biologie est inutile à la page.** Un marqueur « ce
  message porte un résultat de biologie » peut être nécessaire à l'affichage. La
  question n'est pas « faut-il l'information » mais « faut-il **construire
  l'objet complet** pour la rendre ». Établir ce que l'écran affiche
  réellement **avant** de retirer quoi que ce soit.
- **Ne pas présumer que le coût est proportionnel au nombre d'objets.** Le
  rapport le dit explicitement : un coût par objet stable peut être dominé par
  une seule famille, par le suivi de changements d'EF, ou par une allocation
  indépendante de la taille. **C'est la ventilation qui tranche, pas le ratio.**
- **Ne pas présumer que retirer une famille divise le temps d'autant.** À
  vérifier par mesure, pas par règle de trois.
- **Ne pas toucher au nombre de requêtes SQL** (15,7 par appel) : task-247 l'a
  déjà travaillé, et ce n'est pas le poste dominant.

## Ce que la US doit livrer

Une page d'en-têtes qui ne matérialise que ce que l'écran affiche. Les leviers à
instruire, dans cet ordre de valeur mesurée :

1. **Les résultats de biologie** (65,2 objets/appel) — projeter ce dont la liste
   a besoin plutôt que charger l'entité.
2. **Les pièces jointes** (40,2) — la liste affiche un marqueur de présence, pas
   le détail des pièces.
3. **Les étiquettes** (37,9) — à vérifier : elles sont probablement affichées.

## Definition of Done

- [ ] Build passe (0 erreur), tests passent (0 échec)
- [ ] **Le nombre d'objets construits par appel de `GetMailsByUids` baisse**, et
      le rapport le montre — c'est le critère, pas une durée
- [ ] **Ce que l'écran affiche est inchangé** : mêmes messages, mêmes compteurs
      de fils, mêmes étiquettes, mêmes marqueurs de pièce jointe et de biologie.
      Vérifié par test, et par le plan de test manuel
- [ ] Le nombre de **requêtes SQL par appel** ne **monte pas** — un N+1 introduit
      en retirant une matérialisation serait une régression déguisée en gain
- [ ] Tests de non-régression sur le **contenu** de la page, écrits **avant** le
      correctif
- [ ] **Contre-épreuve chiffrée** : un tir `journey` à deux paliers au moins,
      comparant objets/appel et temps de matérialisation avant/après. Si le temps
      ne baisse pas alors que les objets baissent, le **dire** — cela signifierait
      que le coût n'était pas dans la matérialisation, et le rapport avertit déjà
      de cette possibilité
- [ ] **Aucune donnée de santé** exposée qui ne l'était pas déjà

## Manual Test Plan

- Monter le banc (skill `loadtest-skill`) — contrôler à qui appartient le CPU et
  que les **UID commencent à 1**
- Ouvrir la boîte de réception depuis l'application, sur un praticien dont les
  messages portent des comptes rendus **et** des résultats de biologie
- **Ce qu'il faut voir** : la liste **strictement identique** à avant —
  même ordre, mêmes compteurs de fils, mêmes étiquettes, même marqueur de pièce
  jointe, même indication de biologie
- Ouvrir un message depuis cette liste : son contenu complet doit s'afficher
  normalement (la page de détail, elle, a le droit de tout charger)
- Lire la section « Où part le temps d'une opération servie par la base » et la
  table des objets matérialisés : le décompte doit avoir baissé

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — performance
- **Exigences DSR honorées** : aucune exigence nouvelle
- **INS** : ⚠️ les identifiants enrichis comptés par cette page **portent de
  l'INS**. Retirer une matérialisation ne doit **jamais** faire disparaître un
  contrôle d'appartenance : le cloisonnement entre messages reste vérifié par test
- **Interop CI-SIS** : ⚠️ **l'intégrité et la complétude des documents cliniques
  restent bloquantes** — un allègement de la liste ne doit rien retirer à la page
  de détail ni au dossier patient
- **Habilitations** : le cloisonnement « une base par praticien » est inchangé
- **Authentification PS / Consentement** : inchangés
- **Tracé PGSSI-S** : inchangé
- **Hébergement HDS** : gain attendu sur le premier geste du médecin
- **AIPD / impact RGPD** : ⚠️ charger **moins** de données de santé pour un écran
  qui ne les affiche pas est une **minimisation** — à noter comme bénéfice, pas
  comme simple performance
