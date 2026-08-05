# todo-task-233.md — La page d'un dossier patient lit tout le dossier avant d'en montrer vingt : paginer côté base et rendre les filtres indexables

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune.
**Priorité**: **1** — et c'est un **prérequis mesuré**, pas une préférence. Le
redimensionnement du multiplexeur de connexions (branche
`perf/cl-waiting-et-file-socket-handler`) fait gagner **53 %** à la recherche au
palier 300 médecins, mais **coûte +145 % à cette page** — parce qu'élargir le pool
multiplie la concurrence de la requête décrite ici. Tant qu'elle n'est pas
corrigée, ce gain reste inaccessible.

> ### Comment cette US est arrivée en tête, alors qu'elle pesait 1 %
>
> Le classement par temps serveur consommé de la campagne du 2026-08-04 la met
> **dernière** : 1,0 % du temps, 8,5 s sur 890. C'est la **dispersion** qui l'a
> désignée (p50 81 ms contre p95 343 ms, soit 4,2×), et c'est l'A/B du pool qui l'a
> rendue bloquante. Une US qu'aucun classement par volume n'aurait sortie.

## Objective

Qu'afficher la première page du dossier d'un patient coûte **le prix d'une page**,
et non le prix du dossier entier — aujourd'hui et quand le dossier aura grossi.

## Le constat — mesuré, pas supposé

Campagne `journey-mssante-n300-142603` (2026-08-04, 100/200/300 médecins, K=1,25) :

| Grandeur | 100 médecins | 200 médecins | 300 médecins |
|---|---|---|---|
| p95 de la page du dossier | 121 ms | 241 ms | **343 ms** |
| p50 | ~58 ms | ~69 ms | **81 ms** |
| Taille moyenne du dossier | 37,7 documents | 40,3 | **40,7** (max **85**) |
| Documents effectivement affichés | **20** | **20** | **20** |

Deux faits que ces chiffres établissent ensemble :

1. **La dispersion p95/p50 vaut 4,2×.** Un coût fixe par appel ne se disperse pas
   ainsi : celui-ci dépend de la **donnée**, donc de la taille du dossier.
2. **La page ne grandit pas** (le client la plafonne à 20) alors que **le dossier
   grandit** à chaque analyse. Le coût suit le dossier, pas la page.

Et l'A/B du pool (même campagne, iso-conditions) l'a confirmé par l'absurde : en
passant le pool de 2 à 6 connexions par base, cette page passe de 343 ms à
**843 ms au p95** (+145 %) — la requête devient six fois concurrente au lieu de
deux, sur la même base.

## La cause — établie par lecture du code

`PatientRepository.GetActiveMailIdsByDocDateAsync` :

- charge **tous** les documents médicaux du patient (`ToListAsync`), puis trie et
  pagine **en mémoire** (`OrderByDescending` / `Skip` / `Take` après matérialisation) ;
- filtre les dossiers par **six** prédicats de la forme
  `FolderPath.ToLower().Contains("sent")` — une fonction appliquée à la colonne,
  qui **interdit tout usage d'index** et impose un parcours séquentiel.

La pagination demandée par le client n'atteint donc jamais la base : elle est
appliquée après que tout a été lu.

## Ce qu'il ne faut PAS présumer

- **Ne pas se contenter de déplacer `Skip`/`Take` dans le SQL.** Les six filtres
  non indexables resteraient, et c'est le parcours séquentiel qui coûte. Les deux
  moitiés du correctif comptent.
- **Ne pas remplacer `ToLower().Contains(...)` par une comparaison exacte sans
  vérifier le besoin.** Ces filtres écartent les dossiers d'envoi, de brouillons
  et de corbeille, dont les noms varient selon le serveur MSSanté (`Sent`,
  `Envoyés`, `Trash`, `Corbeille`…). La règle métier — **un document rangé dans
  un de ces dossiers n'appartient pas au dossier clinique du patient** — doit être
  préservée à l'identique. C'est sa *forme technique* qui est en cause, pas elle.
- **Ne pas ignorer la dépendance à `MailFolder`.** Le produit connaît déjà le
  **type** d'un dossier (`ImapHelper.GetFolderType`, `SpecialFolder`) : classer une
  fois à l'écriture vaut mieux que deviner à chaque lecture par sous-chaîne. C'est
  la piste la plus profonde, et probablement la bonne.
- **Ne pas oublier `TotalCount`.** La réponse porte le nombre total de documents
  du dossier, dont le client a besoin pour « charger plus ». Le compter côté base
  est légitime ; le calculer en lisant tout ne l'est pas.
- **Ne pas corriger au passage l'écart de pagination client/API.** Le client compte
  ses pages à partir de 0 et l'API à partir de 1, donc « charger plus » recharge la
  première page. C'est un **autre** défaut, consigné en hors scope de task-226 : le
  mélanger ici rendrait la contre-épreuve illisible.
- **Ne pas juger le gain sur le banc actuel seul.** À 40 documents par dossier
  l'amélioration sera modeste. Le vrai gain se mesure sur un dossier de plusieurs
  centaines de documents — ce que la contre-épreuve doit produire explicitement.

## Contenu attendu

1. **Pagination et tri exécutés par la base** : la requête ne rapporte que la page
   demandée, plus le compte total.
2. **Filtres de dossier indexables** : suppression des `ToLower().Contains(...)`
   sur la colonne, au profit d'une classification exploitable par index — piste
   privilégiée : le **type** de dossier déjà connu du produit.
3. **Index de couverture** si la mesure le justifie, sur `(Ins, Date)` ou
   équivalent, à décider **après** avoir vu le plan d'exécution — pas avant.
4. **La règle métier inchangée** : un document rangé dans un dossier d'envoi, de
   brouillons ou de corbeille n'entre pas dans le dossier clinique. Test dédié sur
   les variantes de nommage (`Sent`, `Envoyés`, `Trash`, `Corbeille`).
5. **Le plan d'exécution consigné** avant/après (`EXPLAIN ANALYZE`) dans le
   `## Develop log` : c'est la preuve que l'index sert, et le seul moyen de
   distinguer « plus rapide » de « plus rapide par hasard ».

## Hors scope

- **L'écart de pagination client/API** (page 0 vs page 1) — défaut distinct.
- **Le redimensionnement du pool** — il attend cette US, il n'en fait pas partie.
- **La rafale de la fiche** (6 ouvertures de message en parallèle) : elle est
  conforme au client réel, ce n'est pas elle qui est en cause.
- Toute autre requête du dossier patient : la recherche patient (4 ms) et
  l'opposition (3 ms) sont hors sujet.

## Definition of Done

- [ ] Build passe (0 erreur)
- [ ] Tests passent (0 échec)
- [ ] La requête de page **ne matérialise plus** l'ensemble des documents du
      patient : pagination et tri côté base — vérifié par le SQL généré, consigné
      dans le `## Develop log`
- [ ] Plus aucun `ToLower().Contains(...)` sur une colonne dans le chemin de la
      page du dossier — vérifié par recherche
- [ ] **La règle métier est préservée** : un document en dossier d'envoi, de
      brouillons ou de corbeille n'apparaît pas dans le dossier clinique — test
      couvrant les variantes de nommage (`Sent`, `Envoyés`, `Trash`, `Corbeille`),
      **constaté ROUGE** avant correctif
- [ ] `TotalCount` reste exact, et son calcul ne relit pas tout le dossier
- [ ] `EXPLAIN ANALYZE` avant/après consigné, montrant la disparition du parcours
      séquentiel
- [ ] **Contre-épreuve au banc, bloquante pour le merge** : tir `journey` n300 en
      iso-conditions avec `report-journey-mssante-n300-142603` (300 médecins,
      K=1,25, fenêtres 30 min, 247 messages/boîte, reset-state) :
  - p95 de « ouvrir la page d'un dossier patient » **en baisse** face aux 343 ms
    de référence, et **dispersion p95/p50 sous 3×** (référence : 4,2×)
  - **le coût cesse de suivre la taille du dossier** : sur un dossier
    artificiellement porté à ~300 documents, le p95 de la page reste du même ordre
    qu'à 40 — c'est *le* critère, et il n'est pas mesurable sur le corpus nominal
  - aucune autre étape du parcours dégradée de plus de 20 %
  - vérification par base toujours PASS
- [ ] **Puis re-tir du pool à 6** (branche `perf/cl-waiting-et-file-socket-handler`,
      à rebaser) : la recherche doit regagner ses ~53 % **sans** que cette page se
      dégrade. C'est la démonstration que le prérequis était bien celui-ci.

## Manual Test Plan

```bash
# 1. Banc + semis de certification
cd Api/Mail
dotnet run --project src/AppHost --launch-profile https-load-test
dotnet run --project tests/mss.mail.loadtest.seed -- --users 300 --messages 247 \
  --api http://127.0.0.1:5052
YES=1 tests/loadtest-k6/reset-state.sh --keep-maildir

# 2. Tir en iso-conditions avec la référence
export BYPASS_KEY=loadtest-local-only
tests/loadtest-k6/observe.sh start 6600
USERS=300 MESSAGES_PER_USER=247 JOURNEY_STAGES="100:30m,200:30m,300:30m" \
  JOURNEY_TIME_COMPRESSION=1.25 PROM=1 tests/loadtest-k6/run.sh journey
tests/loadtest-k6/observe.sh stop
tests/loadtest-k6/report.sh <dernier json> --expected 98

# 3. LE critère — un dossier volumineux. À produire explicitement : un praticien
#    dont une boîte concentre ~300 documents sur un même INS (le corpus de test
#    concentre déjà 62 % de ses jeux sur un patient, cf. task-226), puis ouvrir sa
#    fiche et comparer le p95 à celui d'un dossier de 40.
```

**Ce que l'humain doit voir** :

- [ ] la page du dossier **plus rapide** qu'aux 343 ms de référence, et sa
      **dispersion retombée sous 3×** ;
- [ ] sur un dossier de ~300 documents, un temps **du même ordre** qu'à 40 — c'est
      la preuve que le coût ne suit plus la taille du dossier ;
- [ ] la liste des documents affichés **inchangée** : mêmes documents, même ordre
      (le plus récent d'abord), et **toujours aucun** document d'un dossier
      d'envoi, de brouillons ou de corbeille ;
- [ ] `EXPLAIN ANALYZE` sans parcours séquentiel sur la table des documents ;
- [ ] aucune autre étape du parcours dégradée.

**Données de test** : boîtes `loadtest-*`, corpus de documents de test publics
(jeux ANS/CI-SIS), identités virtuelles déterministes. **Aucune donnée de santé
réelle, aucun patient réel.**

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville — consultation du dossier clinique d'un
  patient par le praticien.
- **Vague Ségur** : hors vague — optimisation d'une lecture existante, aucun
  changement fonctionnel ni d'interopérabilité.
- **Exigences DSR honorées** : aucune nouvelle. L'US **préserve** le comportement
  et en réduit le coût.
- **INS** : la requête est **indexée par INS** (`md.Ins == ins`). ⚠️ Deux
  garde-fous : l'INS ne doit apparaître dans **aucune** étiquette de métrique ni
  nom d'index journalisé (leçon de task-213, règle reprise par task-224/225/226),
  et un éventuel index sur `(Ins, Date)` ne change rien à la confidentialité — mais
  sa création doit passer par une **migration relue** (règle 7c du CLAUDE.md :
  lire la migration générée, vérifier l'absence d'opérations fantômes).
- **Habilitations** : inchangées — la requête reste dans la base du praticien
  (une base par praticien), donc le cloisonnement est structurel.
- **Interop CI-SIS** : non applicable — aucune lecture ni écriture de CDA.
- **Tracé PGSSI-S** : la consultation d'un dossier patient reste tracée à
  l'identique. Aucun évènement nouveau, aucun retiré.
- **Consentement patient** : non applicable — lecture par le praticien
  destinataire, dans sa propre boîte.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : le correctif s'applique à un environnement HDS en
  production, mais l'US ne modifie ni la donnée ni son emplacement.
- **AIPD / impact RGPD** : néant — aucun traitement nouveau, aucune donnée
  supplémentaire collectée.


---

## Branches

- `api-mail` (pushed) : `fix/task-233-patient-file-page-sql-pagination` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-233-patient-file-page-sql-pagination
- `dtos-mss` (pushed, auto-inclus) : même nom de branche — aucun changement de contrat attendu (US backend-only : pagination et indexabilité d'une requête). Pas de PR si aucun commit.

**Base** : `develop` d'`api-mail` au commit `ac814e1` — task-234 y est mergée (correctif
des tâches de fond). task-230 est encore en PR ouverte (#159) et **ne touche pas** le
dépôt patient : pas de recouvrement.

**Dépendances** : aucune déclarée.

**Préfixe `fix/`** : la US corrige un défaut **mesuré** (p95 343 ms au palier 300, avec une
dispersion p95/p50 de 4,2× qui désigne un coût dépendant de la donnée), et **bloquant** —
le redimensionnement du pool fait gagner 53 % à la recherche mais coûte +145 % à cette
page tant qu'elle n'est pas corrigée.

**Pré-flight** : les 6 repos automatisés vérifiables sont sur `develop`.
⚠️ Le premier `/start 233` a été **refusé** : `dtos-mss` était resté sur
`fix/task-230-…`, branche auto-incluse **vide** (0 commit) que rien ne remet sur
`develop` quand aucune PR n'est ouverte pour ce repo. L'humain l'a basculée ; le défaut
de cycle est signalé et attend une décision.
