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


## Develop log

Trois volets, dans l'ordre où la mesure les a imposés — **pas** dans l'ordre où la US
les annonçait.

### Ce que le plan d'exécution a dit, et qui corrige le diagnostic de la US

La US attribuait le parcours séquentiel de la page aux six filtres
`lower(FolderPath) LIKE '%…%'`. Le relevé dit autre chose : **`MailMedicalDocuments`
n'avait aucun index sur `Ins`** — ni sur `MailId`. Ses index portaient sur
`DuplicateOfId`, `PractitionerContactId`, `SetId`, `SupersededByDocumentId`,
`SuppressionRequestedByMailId` : aucun sur la colonne qui restreint au patient. Le
parcours séquentiel était donc **inévitable quoi qu'on fasse aux filtres de nom** —
les supprimer n'aurait rien gagné, faute d'index à parcourir à la place.

task-070 avait bien créé `IX_MailPatients_Ins` — sur la table des **patients**. La
requête de la page filtre les **documents**, table restée sans index. Le même défaut,
sur la table voisine.

### Volet 2 — la pagination en SQL (`7fb47a5`)

`GetActiveMailIdsByDocDateAsync`, qui **exécutait**, devient
`ActiveDocumentsForPatient`, qui **compose**. Le `GROUP BY MailId` + `MAX(Date)`, le
`COUNT`, le tri et le `Skip`/`Take` partent en base ; seule la page revient.
`LoadMailsWithAttachmentsAsync` ré-ordonne déjà selon la liste d'entrée (task-070),
donc l'ordre est préservé sans travail supplémentaire.

Sortie anticipée sur `totalCount == 0`, et `skip` borné à `int.MaxValue` — un
`page * pageSize` en `int` débordait silencieusement sur une page absurde.

### Volet 1 — l'index sur `Ins` (`7951339`)

`IX_MailMedicalDocuments_Ins_MailId_Date`, non unique. Trois colonnes :
`Ins` pour l'égalité qui restreint au patient ; `MailId` en seconde position pour que
les lignes sortent déjà ordonnées par message et que l'agrégat se passe du tri
intermédiaire visible dans le plan d'avant ; `Date` parce qu'elle est agrégée par
`MAX` et n'exige alors aucun accès au tas.

**Non unique volontairement** : un patient a plusieurs documents dans un même message,
et `Ins` est nullable (documents sans identité nationale, en attente de rattachement —
comportement attendu depuis task-226).

**Écartés faute de mesure**, la US demandant de décider « après avoir vu le plan » :
la variante **partielle** (`WHERE NOT SuppressionAccepted AND SupersededByDocumentId
IS NULL`) et la variante **couvrante**. La base de développement — 92 documents, 41 au
maximum pour un patient — ne permet pas de trancher : à cette taille PostgreSQL
parcourt séquentiellement même avec un index, car c'est optimal pour lui. Le choix
reste ouvert pour la contre-épreuve au banc.

Aucun index sur `MailId` seul : la jointure vers `Mails` emprunte la clé primaire de
cette table, déjà indexée.

### Volet 3 — la règle de nommage dite une seule fois (`a861ae9`)

La règle « envoyés / brouillons / corbeille n'entrent pas dans un dossier patient »
était écrite **33 fois** en LINQ : 24 occurrences dans `PatientRepository` (quatre
récitations complètes), 9 dans `MailRepository`. Elle devient une **colonne générée par
PostgreSQL**, `Mails."IsInSentDraftOrTrashFolder"`, calculée sur `FolderPath` avec les
six mêmes motifs. Il reste 3 occurrences, volontairement : elles testent « sent »
**seul**, une règle différente (préférence de doublon).

**Pourquoi pas `MailFolders.FolderType`, que la US proposait.** Ce type est dérivé
**uniquement des attributs SPECIAL-USE annoncés par le serveur**, sans repli sur le nom
(`ImapHelper.GetFolderType`). Relevé en base : le dossier littéralement nommé `Trash`,
qui contient **50 messages**, est classé `FolderType = Custom` faute d'attribut `\Trash`
annoncé, et **aucun** dossier n'y porte le type `Trash`. Filtrer sur ce type aurait
**relâché la règle clinique** et fait entrer la corbeille dans les dossiers patients.

**Ce que ce volet n'apporte pas** : le gain de latence. Ce fut le volet 1. Il apporte
une règle unique, un prédicat d'une lecture de booléen au lieu de six comparaisons de
motifs par ligne, et une colonne indexable — impossible avec `LIKE '%…%'`.

### Ce que la comparaison des cinq récitations a révélé

Deux exigent `FolderPath != null` puis excluent les motifs — chemin inconnu **écarté**.
Les deux autres écrivent `FolderPath == null || (aucun motif)` — chemin inconnu
**gardé**. Deux réponses opposées à la même question. **Sans conséquence sur les
données actuelles** : `FolderPath` est `IsRequired()`, donc NOT NULL en base. C'est une
divergence d'**intention**, qui attendait qu'on rende la colonne nullable pour devenir
un défaut. Chaque appelant garde ici son comportement local **tel quel** — cette task
unifie la règle de nommage, elle n'arbitre pas le cas nul à la place des requêtes.

### Un test unitaire a dû être porté, et c'est un constat sur le harnais

`GetDuplicateClusterAsyncShouldExcludeMembersInTrashAsync` tournait sur **InMemory**,
qui **ignore `HasComputedColumnSql`** : la colonne y vaut `false` en toutes
circonstances. Le test est donc devenu rouge alors que la production excluait toujours
la corbeille — le rouge disait la vérité sur le **harnais**, pas sur le code. Le
réparer sur InMemory aurait voulu dire écrire la valeur à la main dans le seed, donc
tester le seed et non la règle. Il est porté en intégration, avec une note à la place
de l'ancien test.

Même famille que l'angle mort ci-dessous, et que celui de task-235.

### Couverture

| Preuve | Où |
|---|---|
| Règle clinique par nom de dossier, 8 variantes exclues + 3 gardées | `PatientFilePageTests` (`[Theory]` sur la page) |
| La colonne générée elle-même, motif par motif (11 cas) | `TheFolderNamingRuleIsComputedByTheDatabase` |
| L'index dont la page dépend existe | `TheIndexThatRestrictsToOnePatientExists` |
| Corbeille exclue du cluster de doublons | `ATrashedOriginalStaysOutOfItsDuplicateCluster` (porté) |
| Page / `TotalCount` / continuité / ordre | `PatientFilePageTests` |

**Preuves ROUGE**, chacune obtenue en cassant délibérément le code :
- règle de nommage neutralisée → **18 des 28** tests du fichier échouent ;
- déclaration `HasIndex` retirée du modèle → la garde d'index échoue.

Le corps de `GetMailsByInsAsync` n'avait **aucune** couverture avant cette task : le
fournisseur InMemory refuse le `GroupBy` des pièces jointes, donc les tests
unitaires ne pouvaient pas l'atteindre. D'où le projet d'intégration.

### Angle mort signalé, non résolu

La fixture d'intégration bâtit son schéma par **`EnsureCreatedAsync()`**, donc **depuis
le modèle EF**. Les migrations FluentMigrator ne sont jouées par **aucun test** :
schéma de test et schéma de production sont produits par **deux mécanismes différents**,
et rien dans ce dépôt ne vérifie qu'ils disent la même chose. C'est pourquoi les deux
migrations de cette task déclarent aussi leur objet côté modèle, et pourquoi les noms
de colonnes bruts (`Ins`, `MailId`, `Date`) ont été vérifiés à la main contre
`information_schema`. **Même famille que task-235** — à rattacher.

### Audit de migration (règle 7c)

Deux migrations, toutes deux écrites à la main (FluentMigrator : ni `.Designer.cs`, ni
instantané EF, donc aucune dérive de snapshot possible et aucune opération fantôme —
il n'y a pas de générateur).

- `20260805120000` — une `Create.Index`, sa symétrique `Delete.Index` dans `Down`.
- `20260805130000` — une colonne générée en SQL brut (FluentMigrator n'a pas d'API
  pour cela), sa `Delete.Column` dans `Down`. L'expression vient de
  `MailFolderNamingRule` et de nulle part ailleurs, partagée avec le modèle EF.
- Numéros strictement postérieurs aux quatre existants, **aucune collision** vérifiée.
- Noms de colonnes bruts vérifiés contre `information_schema` de la base de
  développement.
- Coût dit franchement : une colonne générée `STORED` réécrit la table sous verrou
  exclusif — de l'ordre de la seconde sur une base par praticien.

### Contre-épreuve au banc — **bloquante pour le merge**

Non faite, et elle ne peut pas l'être ici : la base de développement plafonne à **41
documents** pour son patient le plus fourni, la US demande **~300**. Le plan post-index
n'a pas été relevé non plus — la migration n'est pas appliquée sur cette base (le MCP
PostgreSQL est en lecture seule, et on n'écrit pas dans une base praticien), et à 92
documents un relevé ne prouverait rien : PostgreSQL parcourt séquentiellement à cette
taille parce que c'est optimal. **La mesure appartient au banc**, avec le choix
partiel/couvrant qui en dépend.

### Décision produit à arbitrer par le PO

Renforcer la règle par l'**union** des deux signaux — SPECIAL-USE **et** nom — au lieu
du nom seul. Preuve du besoin : la boîte de développement classe `Trash` (50 messages)
en `Custom`. L'inverse est vrai aussi — un serveur peut annoncer `\Sent` sur un dossier
au nom quelconque, et le nom seul le laisserait alors entrer dans un dossier patient.
**Cela change le comportement**, donc cela ne se fait pas dans cette task (règles 6
et 7).

### Constat de cycle signalé, non corrigé

Le premier `/start 233` a été refusé parce que `dtos-mss` était resté sur
`fix/task-230-…` — branche **auto-incluse vide** (0 commit) que rien ne remet sur
`develop` quand aucune PR n'est ouverte pour ce repo. Le pré-flight de la task suivante
paie donc l'auto-inclusion de la précédente. Défaut de cycle, à décider.


## Sonar log

### KPIs qualité (baseline → final)

⚠️ **Lisez d'abord ceci, sinon le tableau mentira.** Les deux relevés **ne portent pas
sur le même périmètre**. Le scan de baseline (celui du cycle précédent) et mon premier
scan employaient un périmètre restreint ; le scan final tourne avec le périmètre complet
du scanner. `ncloc` le dit sans ambiguïté : **37 181 → 43 533**. Aucun delta de ce
tableau ne mesure donc task-233 — il mesure surtout ce qui est entré dans le champ de
l'analyse. Je le signale au lieu de présenter une amélioration ou une dégradation
imaginaire.

| Métrique | Baseline (périmètre restreint) | Final (périmètre complet) | Comparable ? |
|---|---|---|---|
| Quality Gate (new code) | **ERROR** | **ERROR** | oui — rouge avant, rouge après |
| `new_violations` | 5 | 33 | **non** — périmètres différents |
| `new_coverage` | 0.0 % (seuil 80) | 0.0 % (seuil 80) | oui — structurellement 0 |
| `new_security_hotspots_reviewed` | 0.0 % (seuil 100) | 0.0 % (seuil 100) | oui |
| Bugs / Vulnérabilités / Smells | 0 / 0 / 8 | 2 / 0 / 35 | **non** |
| Coverage projet | 0.0 % | 0.0 % | oui — aucun rapport de couverture n'est importé |
| Duplication | 0.5 % | 0.4 % | non |
| Ratings (Fiab. / Sécu. / Maint.) | A / A / A | C / A / A | **non** |
| `ncloc` | 37 181 | 43 533 | — c'est *la* cause de tout ce qui précède |

### La mesure qui, elle, est indépendante du périmètre

**Combien de violations de la période « new code » tombent dans un fichier que cette
task a touché ?**

> **Zéro sur 33.**

Les 33 sont intégralement de la dette héritée, et voici sa provenance :

| Fichiers | Violations | Origine |
|---|---|---|
| `report.py`, `journey.js`, `journey-model.js` | **26** | outillage du banc k6 (tasks 173 / 174 / 195) |
| `AppHost.cs` | 3 | `S125` — code commenté |
| `AppHostSecrets.cs` | 1 | `S3903` — type hors espace de noms nommé (le « bug » du décompte) |
| `BaseRepository.cs`, `IIheXdmProcessingService.cs` | 2 | `S103` — lignes > 150 caractères |
| `ContactRepository.cs` | 1 | `S1067` — 9 opérateurs conditionnels |

Rien de tout cela n'appartient au périmètre de cette US (règle 6). Deux violations
étaient en revanche **à moi** — les `CA1861` des tests de `GlobalExceptionHandler`
(task-234) : corrigées ici, elles ont disparu du relevé final.

### Ce qui garde le Quality Gate rouge, et depuis quand

1. **`new_coverage` = 0** — aucun rapport de couverture n'est importé par le scan.
   Ce n'est pas une couverture faible, c'est une **absence de mesure** : le seuil à 80 %
   est donc inatteignable par construction, à chaque cycle. À traiter par une task
   d'outillage, pas par du code.
2. **`new_security_hotspots_reviewed` = 0** — dont les deux `Math.random()` de
   `journey.js`. **Signalé pour la quatrième fois.** Ce sont des points à *réviser*, pas
   à corriger : personne ne le fait, donc le Quality Gate reste rouge indéfiniment.
3. **`new_violations` > 0** — la période « new code » englobe des tasks déjà mergées
   (constat déjà consigné). Une task peut donc être rouge sans avoir introduit la
   moindre dette. C'est précisément le cas ici.

### Règle blacklistée, non touchée

Les 3 `S3776` de `report.py` (complexité cognitive) relèvent de `/sonar-s3776`, commande
manuelle et hors chaîne autonome — une méthode = une PR. Non traitées, conformément à la
blacklist.

### Itérations

**Une seule**, et volontairement. La passe n'a rien à nettoyer sur le code de la task
(zéro finding), et le reste appartient à d'autres périmètres. Poursuivre jusqu'à cinq
itérations aurait voulu dire aller réparer la dette d'autrui sous couvert de cette US.


## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/162 — label `awaiting-human-merge`

Aucun autre repo touché. `dtos-mss` est auto-inclus par `/start` mais n'a reçu aucun
commit — aucune PR ouverte pour lui, conformément à la règle.

## Code Review Summary

**Verdict : APPROVED**, 0 blocage — mais trois défauts trouvés et corrigés **pendant** le
cycle, chacun ayant passé la suite verte avant d'être vu :

| Défaut | Trouvé par | Pourquoi les tests ne le voyaient pas |
|---|---|---|
| Le getter `DataContext` **lève** depuis task-231 et `ActiveDocumentsForPatient` l'appelait → la page aurait levé **à chaque appel en production** | le conflit de fusion avec `develop` — donc par chance | les tests **injectent** le contexte, où le getter fonctionne |
| Sortie anticipée « dossier vide » renvoyait `Page`/`PageSize` à **zéro** | relecture de la passe qualité | la liste étant vide, rien ne le signalait |
| Mon décompte « 3 occurrences restantes, d'une autre règle » était **faux** — 3 récitations complètes de plus, écrites avec des constantes | grep élargi aux constantes | — |

Une garde a été posée pour le premier (`DataContextGetterScanTests`). Pour le deuxième,
un test. Le troisième était une erreur de mon propre compte rendu, corrigée au commit
suivant.

**Ce que ce cycle apprend, et qui dépasse la task** : trois tests ont dû être portés
d'InMemory vers un vrai PostgreSQL, et un défaut de production n'a été trouvé que par un
conflit de fusion. Dans les deux cas la cause est la même — **le harnais est plus
permissif que la production**, donc il valide du code qui ne marche pas. C'est exactement
l'objet de task-235.


## Merged

Mergée le **2026-08-05** par l'humain (HAG, règle 10), sur attestation `--i-tested`.

- `api-mail` : PR #162 **squash-mergée** → `e296753` sur `develop`. Ref remote supprimée
  (`git push origin --delete`), **branche locale conservée**.
- `dtos-mss` : branche auto-incluse **vide (0 commit vérifié)**, aucune PR. Supprimée
  localement **et** sur le remote — c'est elle qui bloquait le pré-flight de `/start` deux
  fois de suite. Le défaut de cycle reste à corriger : rien dans la chaîne ne nettoie une
  branche auto-incluse restée vide.

### Ce que ce merge a emporté au-delà de la task

Le correctif de l'outbox (commit `357c310`, 8 emplois du getter `DataContext` levant) est
**arrivé sur `develop` avec cette PR**. Vérifié après synchronisation : `develop` porte la
garde `DataContextGetterScanTests` **et** zéro emploi du getter dans `src/`. La CI de
`develop` ne pouvait donc pas casser — le risque d'ordre que task-236 signalait est levé.

**Conséquence pour task-236** : son *correctif* est déjà en place. Il lui reste son cœur —
le test qui échoue avant lui (dépôt sans contexte injecté, cache d'identifiant chaud, preuve
ROUGE), le recensement des autres méthodes pouvant retourner sans résoudre le contexte, et
l'arbitrage sur la suppression du getter. Le task file a été mis à jour en ce sens.

### ⚠️ Ce qui reste dû, et qui n'a PAS été fait

La **contre-épreuve au banc** du DOD — non faisable en local (la base de développement
plafonne à 41 documents pour son patient le plus fourni, la US en demande ~300). Le gain est
donc **démontré structurellement** (pagination et agrégation en SQL vérifiées sur le SQL
réellement exécuté, index créé, 28 tests dont trois preuves ROUGE) mais **non mesuré**.
Restent également dus : l'`EXPLAIN ANALYZE` après, le re-tir du pool à 6, et le choix
partiel/couvrant de l'index qui dépend de cette mesure.

Mergée en connaissance de cet écart, sur décision humaine explicite après double
signalement.


## Correction post-merge — 2026-08-05

La justification écartant `MailFolders.FolderType` s'appuyait sur un relevé en base
présenté comme une propriété du système : *« `Trash` classé `Custom`, 50 messages, aucun
dossier de type `Trash` »*. **Exact à l'instant de la mesure, faux ensuite** : après une
synchronisation ultérieure, la même base classe correctement `INBOX`=0, `Sent`=1,
`Drafts`=2, `Trash`=3, `Junk`=4, seuls les dossiers réellement personnalisés restant en
`Custom`.

Reste vrai : `GetFolderType` n'a **aucun repli sur le nom** (fait de code). N'est plus
établi : que ce serveur n'annonce pas SPECIAL-USE — il l'annonce. La cause du transitoire
**n'a pas été établie**.

L'argument devient donc « la classification persistée n'est pas stable et a été observée
fausse pendant une fenêtre » — plus faible que celui écrit, mais suffisant pour le choix
retenu. **Aucune conséquence sur le code** : la règle est restée fondée sur le nom, donc le
comportement antérieur est préservé. C'est la justification qui était trop forte, pas la
décision.

Erreur de méthode à retenir : citer un volume et une classification relevés à un instant
comme s'ils caractérisaient le système. Corrigé dans `E015-Changelogs.md` (v1.27) et
`E015-tests-charge-api-mail.md` (v1.28).
