# questions/task-291.md — la task suppose UNE cause, il y en a TROIS

**Statut** : `/develop` s'arrête ici (fail-fast, règle 13 arrêt légitime n°1).
Le correctif de la famille dominante est **livré, vérifié et poussé**
(`dd83bdc`). Ce qui reste demande un arbitrage de périmètre, pas du code.

## Ce qui est acquis

**Famille A — courses de capture de métrique.** Cause **établie**, corrigée,
avec garde-fou. Détail dans le message de `dd83bdc`. Le point de fond :
`MailMetricsCaptureCollection` (task-256) n'avait pas
`DisableParallelization = true`, et `infrastructure.tests` n'avait aucune
collection. Le garde-fou ajouté a trouvé du premier coup une classe que mon
relevé manuel avait manquée.

**Un piège de diagnostic mérite d'être retenu** : rejouer l'assembly seul « pour
vérifier » **innocente à tort**. `application.tests` seul est vert 5/5 (2280
tests) ; la même suite au niveau **solution** — cinq assemblies en parallèle —
sortait rouge 2/3. La course est latente en permanence, la contention CPU est
seulement ce qui la révèle. J'ai commencé par faire cette erreur.

## Le problème de périmètre

La DOD exige **10 exécutions complètes consécutives vertes**. Elles ont été
obtenues : 10/10, 0 échec. **Et le 11e run est sorti rouge.**

Le critère est donc **atteint sans que le défaut soit éteint** — ce qui en dit
plus sur le critère que sur le correctif. Un défaut qui frappe ~1 run sur 5
passe une fenêtre de 10 environ une fois sur trois. **Je ne revendique pas cette
DOD comme tenue.**

Chasse de 6 runs supplémentaires après correctif — 2 rouges, et ils désignent
**deux causes que le cadrage de la task ne prévoyait pas** :

### Famille B — `MarkdownPdfRendererTests` (cause NON établie)

Deux méthodes différentes touchées (`RenderGfmTableKeepsAllCellsInOrder`, puis
`RenderRowsWithFewerCellsThanHeaderDoesNotThrow`).

**Ce n'est pas la cause A** : aucune autre classe de test n'utilise QuestPDF, il
n'y a donc aucun concurrent qui pollue un état de test partagé. Ce qui est
partagé est **global au processus et natif** — `QuestPDF.Settings` muté par le
constructeur, et le rendu SkiaSharp de `GeneratePdf()`. Les assertions portent
sur du **texte extrait d'un PDF**, donc sur une mise en page réelle, sensible
aux ressources.

**Livré** : la classe est sérialisée, **en atténuation assumée et commentée
comme telle**. Le symptôme devient plus rare ; la sensibilité reste.
**Reproduction à la demande non obtenue** — donc, au sens de la DOD, cause non
établie. Je ne l'ai pas maquillée en corrigée.

### Famille C — fixture Postgres partagé de `integration.tests` (NON traitée)

`SeededThreadsAreCountableTests.SeveralDistinctThreadSizesReachTheCounter` et,
plus tôt, `SemanticSearchRepositoryIntegrationTests.SearchByFiltersAsyncShouldFilterBySubjectAsync`.
Les deux sont `[Collection("PostgreSql")]`.

Cet assembly a **déjà** `parallelizeTestCollections: false` : il n'y a donc
**aucune course**. C'est de l'**interférence de données séquentielle** — un test
voit les lignes semées par un voisin. Mode d'échec déjà documenté sur ce banc
(les suites pgvector se marchent sur les dimensions de vecteurs).

**Rien n'a été livré pour C.** Le remède est l'isolation des données par test
(clés uniques, ou nettoyage entre tests) sur une suite d'intégration entière.
C'est un chantier d'un autre ordre que A, et le traiter ici aurait transformé
cette task en refonte du harnais d'intégration.

## La question

**Comment découper ?** Trois options, ma recommandation en premier :

1. **Recommandé — accepter A comme livrable de task-291, ouvrir deux tasks de
   suite** (B : sensibilité du rendu PDF ; C : isolation des données de
   `integration.tests`). Le gain de A est réel et immédiat : la famille qui
   frappait le plus souvent est éteinte à la cause, et le garde-fou empêche sa
   récidive. Amender la DOD de task-291 pour qu'elle décrive ce périmètre.
2. Garder task-291 ouverte jusqu'à ce que les trois familles soient traitées.
   Honnête, mais la task devient un chantier long, et le correctif A — prêt,
   vérifié — attend pour rien.
3. Traiter A + B ici et ne différer que C. Suppose d'établir la cause de B, ce
   qui demande une campagne de reproduction sous charge contrôlée.

**Je ne réécris pas ma propre DOD pour la faire passer** — c'est précisément
l'anti-pattern que cette task dénonce chez les autres. L'arbitrage est au PO.

## Accessoirement — une lacune de CLAUDE.md constatée au pré-vol

`interop` **n'a pas de `.git`**, exactement comme `Host/Modules`. `git -C interop`
remonte donc au dépôt du plan de contrôle et répond pour lui. CLAUDE.md ne porte
cet avertissement que pour `host` : le pré-flight de `/start` ne mesure donc
rien pour **`interop-cda` non plus**, et ne le dit pas. Un correctif d'une ligne
dans CLAUDE.md, hors périmètre de cette task.
