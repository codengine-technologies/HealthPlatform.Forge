# todo-task-433.md — Chaque tir de banc produit des findings rédigés par analyse de code, suivis dans un registre

**Repos**: forge *(plan de contrôle `HealthPlatform.Forge` : racine du workspace, hors table des repos de code)*
**Dependencies**: task-431, task-432 (leurs signaux et leurs sites alimentent l'analyse ; sans eux, l'étape tourne en
mode dégradé : recherche du code par noms de tables)
**Epic**: E015
**Single frontend**: true
**Priorité**: **2**. Étage 3 de l'amélioration « le banc comme outil d'exploration » (2026-11-06). Il transforme un
rapport de mesure en liste de défauts confirmés, chacun avec sa cause dans le code, son gain chiffré et le test qui
prouverait sa correction.

> **Origine.** Demande de l'humain du 2026-11-06 : « comment faire du loadtest un outil d'exploration des axes
> d'amélioration, afin que le rapport rédige les findings issus d'une analyse de code ». Préfiguration faite le même
> jour à la main sur le tir `pgstats-journey-193047.tsv` : 6 candidats, 3 confirmés (task-429, task-430 F-A et F-B),
> 1 écarté (le registre, coût normal), 1 mineur à confirmer (document médical chargé avec `Embedding`), 1 non exploré
> (chargement des types Npgsql).

## Ce qui est établi

- **L'exploration de code se fait aujourd'hui au fil de l'attention.** Elle est rigoureuse quand elle a lieu (F1 et F2
  du tir du 2026-11-05), absente sinon : le défaut des pièces jointes a traversé tous les rapports.
- **La préfiguration du 2026-11-06 a suivi une méthode reproductible** :
  1. classer les formes par signal (task-431) ;
  2. lire le texte SQL complet ;
  3. retrouver le site dans le code (task-432) ;
  4. `EXPLAIN (ANALYZE, BUFFERS)` sur une base du banc ;
  5. juger la cause ;
  6. chiffrer le gain à partir des mesures ;
  7. proposer le correctif et son test.

  Elle a aussi produit un faux positif (le registre). La lecture du code et du plan doit donc pouvoir **écarter** un
  candidat, pas seulement le confirmer.
- **Un même défaut peut réapparaître d'un tir à l'autre** tant qu'il n'est pas corrigé. Sans registre, il est rejugé à
  chaque fois. Une récidive (même classe qu'un défaut corrigé) n'est pas distinguée d'un défaut neuf.

## Objective

Après chaque tir, une étape `/loadtest-findings {rapport}` explore les traitements coûteux et ajoute au rapport une
section « Findings — analyse de code ». Chaque finding porte :
- la forme SQL et ses chiffres ;
- la route et le `fichier:ligne` ;
- la cause, et le plan d'exécution qui la montre ;
- le gain calculé à partir des mesures du tir ;
- le correctif proposé et le test qui le prouverait (règle 1b) ;
- un verdict : **confirmé**, **plausible** ou **écarté**, avec sa raison.

Un registre suit chaque finding d'un tir à l'autre.

Règles :
- **Candidats** : au plus 8 par tir.
  - Ce sont les formes signalées par les détecteurs de task-431, puis les plus coûteuses en temps et en pages lues.
  - Un finding déjà au registre avec le statut « task » ou « écarté » n'est pas ré-exploré. Il est seulement remesuré.
- **Chaque finding cite ses preuves** :
  - chiffres tirés du `pgstats-*.tsv` du tir, jamais estimés au jugé ;
  - site du code (commentaire `site=` de task-432, sinon recherche documentée) ;
  - plan d'exécution sur une base du banc.
  - Sans plan ni site retrouvé, le verdict est au mieux **plausible**.
- **Gain** : borné par ce que la forme coûte sur le tir (temps SQL, pages, lectures disque). Jamais un gain sur le
  temps de réponse sans mesure : il est annoncé comme « à mesurer par A/B ».
- **Registre** `Docs/audits/findings-registry.md`. Chaque finding a :
  - un identifiant `FND-{NNN}` ;
  - sa classe (celle des détecteurs de task-431) ;
  - le premier tir où il apparaît ;
  - un statut : ouvert, task, corrigé et mesuré, écarté avec raison ;
  - la task et la mesure d'après.
  - Un finding de la même classe qu'un finding déjà corrigé est marqué **récidive**, et le rapport dit quelle prévention
    a manqué.
- **L'humain décide** : la forge ne rédige aucune task d'elle-même. Le rapport propose, l'humain choisit, puis `/po`.
- **Boucle d'amélioration (règle d'or)** : un défaut trouvé hors du banc, ou trouvé plus tard, alors qu'il était
  visible dans un tir passé, ajoute un détecteur à task-431 et un cas au corpus.
- **Invocation** :
  - le skill de banc l'appelle après `report.sh`, pour tout tir dont le rapport est copié dans `Docs/audits/` ;
  - elle est aussi lançable seule sur un rapport existant ;
  - elle n'est jamais dans la chaîne `/start` → `/review` (règle 13 inchangée).

### Hors périmètre

- Les détecteurs eux-mêmes : task-431. La remontée vers le code : task-432.
- Corriger un finding : chaque correctif est une task, rédigée par `/po` sur décision humaine.

## Definition of Done

- [ ] Commande `.claude/commands/loadtest-findings.md` et playbook `agents/loadtest-findings.md`, qui décrivent :
      - les candidats ;
      - les preuves exigées par verdict ;
      - le modèle de finding ;
      - le registre et la récidive ;
      - la mesure du coût de l'étape (`Tools/timing/step.sh`, `--step loadtest-findings`) ;
      - le mode dégradé sans task-431 ni task-432.
- [ ] Modèle de section « Findings — analyse de code » et `Docs/audits/findings-registry.md` créé, amorcé avec les
      findings du 2026-11-06 :
      - FND pièces jointes du dossier patient → task-429 ;
      - F-A biologie → task-430 ;
      - F-B étiquettes → task-430 ;
      - registre → écarté, coût normal d'une recherche indexée ;
      - document médical avec `Embedding` → plausible, gain mineur ;
      - chargement des types Npgsql → ouvert, non exploré ;
      - les findings F1 (task-427) et F2 (task-426) du 2026-11-05 → corrigé et mesuré.
- [ ] **Rejeu sur le tir du 2026-11-06 (`…-apres`)** : la commande produit une section qui retrouve **au moins** les
      trois findings confirmés à la main (pièces jointes, F-A, F-B) et écarte le registre, avec site et plan. Résultat
      recopié dans le task file
- [ ] **Contrôle de non-confabulation** : chaque chiffre d'un finding du rejeu est retrouvé dans le `pgstats-*.tsv` du
      tir, et chaque `fichier:ligne` existe au commit du tir. Vérification consignée
- [ ] `.claude/skills/loadtest-skill/SKILL.md` appelle l'étape après `report.sh`
- [ ] `CLAUDE.md` : la commande est ajoutée au tableau des commandes, hors chaîne autonome
- [ ] Changements du plan de contrôle relus par l'humain avant le push (règle d'or, point 7)

## Manual Test Plan

- [ ] Lancer `/loadtest-findings Docs/audits/api-mail-loadtest-journey-courte-1400-1996-ab-findings-apres-20261106.md`.
- [ ] Lire la section ajoutée : chaque finding a ses chiffres, sa route, son `fichier:ligne`, son plan et son verdict.
- [ ] Ouvrir `Docs/audits/findings-registry.md` : les findings du 2026-11-05 et du 2026-11-06 y sont, avec leur statut.
- [ ] Relancer la commande sur le même rapport : aucun doublon dans le registre, les findings connus sont remesurés et
      non ré-explorés.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — outillage de la forge
- **Vague Ségur** : hors Ségur — outillage
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — l'étape lit des textes SQL normalisés et des plans d'exécution sur des bases de banc
  synthétiques
- **Authentification PS** : non applicable
- **Habilitations** : non applicable
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : non applicable — aucun acte. Garde-fou : aucun finding ne recopie une valeur de ligne, seulement
  des textes SQL normalisés, des plans et des compteurs
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — bases de banc synthétiques. Interdit : jouer `EXPLAIN ANALYZE` sur une base réelle de
  production
- **AIPD / impact RGPD** : inchangée
