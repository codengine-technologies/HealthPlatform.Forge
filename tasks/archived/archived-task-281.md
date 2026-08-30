# todo-task-281.md — Lire ses dossiers ne fait plus la queue derrière l'archivage de ses envois

**Repos**: api-mail
**Dependencies**: —
**Epic**: E015

## Objectif

**La lecture de dossier du médecin attend derrière l'archivage de ses propres
messages envoyés.** C'est établi, chiffré, et c'est la première fois.

Le tir du 2026-08-30
(`Api/Mail/tests/loadtest-k6/reports/2026-08-30/report-journey-500-lot277279-20260830-180647.md`,
finding **F-LOCK-1**), grâce à l'étiquette `holder` livrée par task-278 et
conservée à son retrait :

| Attente sur `imap_session` | p95 médian | max |
|---|---|---|
| **`ReadFolder` derrière `AppendToSent`** | **3,938 s** | **20,357 s** |
| `ReadFolder` derrière `UpdateFlag` | 0,638 s | 0,725 |
| `UpdateFlag` derrière `GetAttachmentStream` | 0,498 s | 0,875 |
| `ReadFolder` derrière `ReadFolder` | 0,487 s | 28,000 |
| **`ReadFolder` derrière rien (`(none)`)** | **0,005 s** | 0,005 |

**La dernière ligne est la contre-épreuve** : verrou libre, l'acquisition ne coûte
rien. L'attente est donc de la **contention pure**, pas un coût d'acquisition —
deux situations aux remèdes opposés, que le rapport ne distinguait pas avant.

### Pourquoi ça a mis trois US à se voir

`ReadFolder` attendait **82,8 ms en moyenne** au tir du 29/08 (~48 % du temps
serveur de la route). task-276, task-277 et task-278 ont toutes buté dessus sans
pouvoir l'attribuer : l'histogramme disait *qui attend*, jamais *derrière qui*.
task-276 a même publié une cause **fausse** sur ce chiffre, réfutée par sa propre
correction d'instrument.

### Ce que task-272 avait déjà fait, et ce qu'il reste

task-272 a sorti l'archivage du **chemin de la réponse** : l'acquittement de
l'envoi n'attend plus la copie dans « Envoyés ». C'est acquis et il ne faut pas
le défaire.

**Mais l'archivage est resté sur la session du praticien** — décision de
task-216, qui avait mesuré qu'une voie d'écriture dédiée rendait l'envoi *plus
lent*. C'est là qu'il gêne : il ne bloque plus l'envoi, il bloque **les lectures
suivantes du même médecin**.

### ⚠️ Établir avant de corriger — et il y a un piège précis ici

**Le remède évident est celui que task-216 a déjà mesuré et rejeté.** Rouvrir une
seconde session IMAP pour l'archivage ferait exactement ce que task-213 avait
fait et que task-215 a réfuté par contre-épreuve : *ce que la voie retirait au
verrou, elle le repayait en ouverture de connexion*, et l'envoi était **plus
lent avec elle que sans** (p95 7 874 ms sans, 10 439 et 12 573 avec).

**Ne pas refaire task-213.** Si l'US y revient, elle doit dire ce qui a changé
depuis — et le mesurer, pas le supposer.

Pistes à instruire, aucune établie :

1. **Réduire la détention, pas la déplacer.** `AppendToSent` tient le verrou
   pendant l'APPEND IMAP complet. Que fait-il exactement sous le verrou ? La
   décomposition existe-t-elle (task-252 l'a faite pour les PJ) ?
2. **Différer l'archivage hors des fenêtres d'activité du médecin.** Il est déjà
   sur le bus (task-272) : le consommateur pourrait renoncer quand le verrou est
   tenu, comme l'avait fait le consommateur de task-278 — mécanisme éprouvé, et
   son échec ne coûterait qu'un archivage retardé, jamais une erreur.
3. **Regrouper les archivages** d'un même praticien plutôt qu'une acquisition par
   envoi (2,26 acquisitions/s mesurées).

## Definition of Done

- [ ] Build passes (0 erreur)
- [ ] Tests pass (0 échec)
- [ ] **La cause de la détention d'`AppendToSent` est établie et écrite** dans le
      task file, chiffres à l'appui — décomposition de ce qui se fait sous le
      verrou, comme task-252 l'a fait pour le téléchargement de PJ
- [ ] Le task file dit explicitement **ce qui a changé depuis task-215/216** si
      l'US propose une seconde session — sinon, elle ne la propose pas
- [ ] Si remède : l'acquittement de l'envoi n'attend **toujours pas** l'archivage
      (acquis de task-272, non-régression testée)
- [ ] Si remède : un échec d'archivage reste **visible et tracé** (acquis de
      task-272, non-régression testée)
- [ ] Si la mesure ne désigne aucun remède sans contrepartie, **l'US s'arrête sur
      le constat** — c'est un résultat (précédents task-276 et task-279)
- [ ] Aucune donnée de santé dans les journaux ni les étiquettes

## Manual Test Plan

**Ce que l'humain valide au HAG** : qu'envoyer un message fonctionne à
l'identique, et que la copie arrive bien dans « Envoyés ».

1. Banc : `dotnet run --project src/AppHost --launch-profile https-load-test`
2. Seed 2 utilisateurs :
   `dotnet run --project tests/mss.mail.loadtest.seed -- --users 2 --messages 20 --api http://127.0.0.1:5052`
3. Envoyer un message de `loadtest-1` vers `loadtest-2` via
   `POST /api/v1/mail/sendmail` (en-têtes d'identité virtuelle habituels).
4. **Vérifier** : l'acquittement revient **sans attendre** l'archivage, et la
   copie apparaît dans « Envoyés » dans les secondes qui suivent.
5. **Vérifier** : immédiatement après l'envoi, ouvrir `INBOX` — la lecture ne doit
   pas être retardée par l'archivage en cours.
6. Provoquer un échec d'archivage (toxic `reset_peer` sur `dovecot-imap` juste
   après l'envoi) : l'échec doit rester **tracé et visible**, pas silencieux.
7. **Clôture de l'US — au banc, tir suivant**, iso-conditions du
   `report-journey-500-lot277279-20260830-180647.md` sur la **même base
   hydratée**. Critères :
   - attente p95 de `ReadFolder` **derrière `AppendToSent`** < **1 s**
     (contre 3,938 s) — lisible directement dans la table `holder`
   - attente **moyenne** de `ReadFolder` < **50 ms** (contre 82,8 ms au 29/08)
   - `send` toujours vert au SLO et **pas plus lent** qu'au tir de référence
     (p50 417 ms, p95 860) — c'est la garde anti-task-213
   - 11/11 étapes vertes

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — performance interne
- **Exigences DSR honorées** : non applicable — comportement fonctionnel inchangé
- **INS** : non applicable
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable — IMAP interne au périmètre MSSanté existant
- **Tracé PGSSI-S** : **inchangé, et c'est une exigence de l'US** — l'échec
  d'archivage d'un envoi doit rester journalisé et corrélé par `traceId` (acquis
  de task-272). Un archivage rendu « discret » pour gagner du verrou serait une
  régression de traçabilité sur un geste métier.
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — inchangé
- **AIPD / impact RGPD** : inchangé

## Branches

- `api-mail` (pushed) : `feat/task-281-append-to-sent-contention` —
  https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-281-append-to-sent-contention
- `dtos-mss` (pushed, auto-inclus) : `feat/task-281-append-to-sent-contention` —
  https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-281-append-to-sent-contention
  (auto-inclusion systématique dès qu'`api-mail` est listé ; restera sans commit
  ni PR si aucun contrat DTO ne bouge — ce qui est l'attendu ici)

Pré-flight `/start` du 2026-08-30 : `api-mail`, `client-blazor`,
`client-mobile`, `dtos-mss`, `sdk`, `interop-cda` tous sur `develop`.
`client-angular`, `devops`, `psc-proxy-*` : non vérifiés (hors automation).

> ### ⚠️ Modification locale non commitée dans `api-mail`, à ne PAS embarquer
>
> `src/AppHost/AppHost.cs` porte une modification locale antérieure à cette US,
> qui déplace le conteneur Seq de `5342` vers `5341` :
>
> ```diff
> -    .WithHttpEndpoint(name: "ui", targetPort: 80, port: 5342)
> +    .WithHttpEndpoint(name: "ui", targetPort: 80, port: 5341)
> ```
>
> Elle a été **reportée telle quelle** sur la branche par le `git checkout -b`
> (comportement normal). Elle **n'appartient pas à task-281**.
>
> **Consigne pour `/develop` et `/review`** : staging explicite uniquement —
> ne jamais faire `git add -A` / `git add .` (CLAUDE.md, convention de commit).
> Le pas-à-pas de `/review` mentionne `git add -A` ; **CLAUDE.md prévaut** et
> l'interdit. Ce fichier doit rester non commité, sauf décision humaine
> explicite de l'intégrer — auquel cas ce serait un commit séparé, hors US.

## Develop log — la cause de la détention est établie

**2026-08-30.** Première moitié de l'US : établir, avant de corriger.

### Ce que `AppendToSent` fait sous le verrou — décomposition par lecture du code

`TryAppendToSentAsync` (`ImapService.cs`) prend le verrou **en premier**, puis
exécute, **tout entier sous le verrou** :

| # | Étape | Nature |
|---|---|---|
| 0 | `AcquireLockAsync(userContextInfo, "AppendToSent", …)` | prise du verrou |
| 1 | `ConnectInternalAsync` | **CONNECT + TLS + AUTH si la session n'est pas déjà établie** |
| 2 | `TryResolveSpecialFolderAsync(Sent, SentFolderNameCandidates)` | résolution du dossier — **non mémoïsée**, refaite à chaque envoi ; en repli, elle **sonde les noms candidats un par un** |
| 3 | `sentFolder.OpenAsync(ReadWrite)` | SELECT |
| 4 | `sentFolder.AppendAsync(message, Seen)` | **APPEND** — transfert du message entier |
| 5 | `sentFolder.CloseAsync(false)` | CLOSE |

**La détention n'est donc pas « un APPEND ».** C'est **quatre allers-retours**
IMAP au minimum, précédés d'un établissement de session complet quand la session
est froide. Le nom de l'opération désignait l'étape 4 ; le verrou couvre 1 à 5.

### Pourquoi trois US ont buté dessus sans pouvoir l'attribuer

Le tir disait *qui attend* (task-211/213), *derrière qui* (`holder`, task-278) et
*si la détention payait l'établissement* (`phase` establish/operate, task-271).
Il ne pouvait pas dire **de combien d'allers-retours** cette détention était
faite — parce que :

> **`AppendToSent` n'enregistrait aucune sollicitation serveur.**
> Vérifié : zéro appel à `mailServerSolicitations.Record` sur tout le corps de
> `TryAppendToSentAsync`. Idem pour `AppendToDrafts`.

C'est **exactement** l'angle mort que task-225 décrivait (« le rapport pouvait
dire que 420 ms étaient passées DANS le verrou sans pouvoir dire de combien
d'allers-retours ») et que task-262 avait fermé **pour les chemins de lecture**.
Les chemins d'**écriture** étaient restés dehors. Le décompte de banc était donc
structurellement muet sur le seul chemin que la table `holder` désignait.

### Ce que cette US livre

La fermeture de cet angle mort, sur le patron exact de task-262 :

- `MailServerCommands.AppendMessage` (`append_message`) — la commande manquait ;
- les 4 allers-retours de `TryAppendToSentAsync` comptés, étiquetés
  `operation="AppendToSent"` — **la même chaîne que le verrou**, pour que la
  table `holder` et le décompte de sollicitations se recoupent au banc ;
- `ResolveFolder` compté **avant** le contrôle de validité (la résolution coûte
  un aller-retour même quand elle échoue), convention de task-262 ;
- 3 tests, cycle **RED → GREEN** vérifié (`Actual: []` avant, 3/3 après).

**Aucun remède appliqué.** L'US ne propose pas de seconde session : le piège
task-213/215/216 est explicitement évité, rien n'a changé depuis qui justifierait
d'y revenir, et **la mesure qui désignerait un remède n'existe pas encore** —
c'est précisément ce que cette livraison rend possible.

### Piste que la décomposition désigne déjà, sans la trancher

L'étape 2 est la seule du lot qui soit **du travail répété sans nécessité** : le
dossier « Envoyés » d'un praticien ne change pas d'un envoi à l'autre, et sa
résolution est refaite à chaque fois, sous le verrou, avec sondage des candidats
en repli. C'est un candidat de « réduire la détention » (piste 1 du task file),
et il ne rouvre pas task-213. **À confirmer par le tir** : si `resolve_folder`
pèse peu face à `append_message`, la piste ne vaut pas le changement.

### ⚠️ Limite de cette livraison — le rapport de référence n'est pas dans ce clone

Le rapport qui fonde l'US
(`tests/loadtest-k6/reports/2026-08-30/report-journey-500-lot277279-20260830-180647.md`)
**est absent de ce dépôt** : `tests/loadtest-k6/reports/*` est **git-ignoré**
(`.gitignore:386`), seul `INDEX.md` est suivi. C'est un artefact local de la
machine qui a rédigé la task.

Conséquence, à assumer explicitement : la décomposition ci-dessus est
**structurelle et vérifiée par le code et par les tests**, mais les **chiffres**
de répartition (combien de la détention va à l'établissement, à la résolution, à
l'APPEND) **n'existent pas encore**. Ils seront produits par le tir de clôture
(plan de test manuel, point 7), qui disposera désormais de l'instrument pour les
attribuer — ce qui n'était pas le cas avant cette US.

### Vérification

| Contrôle | Résultat |
|---|---|
| `dotnet build HealthPlatform.Api.Mail.sln` | ✅ **0 erreur**, 0 avertissement |
| Suite complète | ✅ 3 931 réussis / 1 échec |
| Unique échec | `MailExportServiceTests.BuildPdfWithoutAttachmentsOmitsAttachmentSection` — **flaky pré-existant connu**, rejoué **2/2 verts** en isolation, sans rapport avec ce diff |
| Tests neufs | 3/3, RED avant instrumentation |

> **Note d'outillage, coûteuse à redécouvrir** : `dotnet test --artifacts-path …`
> **fait échouer tous les tests qui scannent les sources**
> (`SecretLiteralScan`, `MailContentWriterScan`, `DataContextGetterScan`,
> `SslTlsOptionsBinding`, `EmbeddingOptionsConsistency`…). `TrackedSourceScan.RepoRoot()`
> remonte depuis l'emplacement de l'assembly pour trouver la racine du dépôt ;
> avec `--artifacts-path` les binaires sortent du dépôt et `RepoRoot()` rend
> `null`. Le contournement des verrous MSB3021 se paie donc d'une **dizaine de
> faux rouges**. Utiliser les chemins standards dès que l'AppHost est arrêté.

## Simplify log

**Passe qualité `/forge-simplify` du 2026-08-30 — skip clean, aucun changement.**

| Repo | Éligible | Verdict |
|---|---|---|
| `api-mail` | oui | **rien à simplifier** |
| `dtos-mss` | non — porteur de contrat, exclu par principe | skip (branche sans commit) |
| tous les autres | non touchés | skip |

Diff examiné : 5 lignes de production (1 constante d'opération, 4 `Record`) plus
une constante de commande documentée, et un fichier de test de 149 lignes.

**Axe réutilisation — vérifié, pas supposé** : le diff ne crée aucune
abstraction. Il s'appuie sur `MailServerCommands`, le recorder
`mailServerSolicitations` déjà injecté, le double de test
`MailServerSolicitationRecorder`, `MockFactory.CreateLogger`, et l'arrangement
`ImapLockScope.AcquireAsync` — tous préexistants.

**Piste envisagée puis écartée** : factoriser la construction d'`ImapService`
(15 arguments) dans une fabrique partagée. Écartée sur constat — **17 classes de
test la construisent déjà en ligne**, et `MockFactory.CreateImapService()` rend
un *substitut* d'interface, pas une instance réelle : il ne répond pas au besoin.
Introduire une fabrique pour la seule classe neuve serait incohérent ; le faire
pour les 17 est un refactor transverse hors périmètre d'une US de mesure, et
`/forge-simplify` est quality-only et non modificateur de comportement.

Le fichier suit exactement la famille existante
(`ImapServiceAttachmentSolicitationTests` de task-279,
`ImapServiceFolderStatusSolicitationTests` de task-262) — et se trouve déjà plus
serré que son plus proche voisin : **149 lignes contre 260**, avec une seule
construction du service là où l'autre la répète deux fois.

Aucun commit, aucun push : la passe n'a rien produit.

## Sonar log

**Analyse exécutée** le 2026-08-30 (serveur relancé — conteneurs `sonarqube_db`
puis `sonarqube`, `UP` sur **9001**). Build Release + 5 projets de tests avec
couverture OpenCover (5 rapports), scan complet, traitement serveur `SUCCESS`.

### KPIs qualité (baseline → final)

| Métrique | Baseline (2026-08-23) | Final (2026-08-30) | Δ |
|---|---|---|---|
| **Quality Gate** | **ERROR** | **ERROR** | = |
| Bugs | 2 | 2 | = |
| Vulnérabilités | 0 | 0 | = |
| Code smells | 69 | 69 | = |
| Security hotspots | 13 | 15 | +2 |
| Couverture | 88,0 % | **88,1 %** | +0,1 |
| Duplication | 0,3 % | 0,3 % | = |
| Lignes de code | 48 363 | 49 150 | +787 |
| Dette technique | 578 min | 599 min | +21 |
| Fiabilité / Sécurité / Maintenabilité | C / A / A | C / A / A | = |

Conditions du Quality Gate : `new_coverage` **88,1 %** (seuil 80) ✅,
`new_duplicated_lines_density` **0,05 %** (seuil 3) ✅,
`new_security_hotspots_reviewed` 0 % (seuil 100) ❌,
`new_violations` 69 (seuil 0) ❌.

### Attribution — rien de ce qui est rouge ne vient de cette US

Le baseline datait du **2026-08-23**, soit **une semaine de `develop`** avant ce
tir (tasks 276 à 280 mergées entre-temps). Le Δ de +787 lignes, +2 hotspots et
+21 min de dette mesure donc **cette semaine-là**, pas un diff de 5 lignes de
production. C'est le piège documenté : la période « new code » englobe des tasks
déjà mergées, et un Quality Gate rouge n'y prouve aucune dette introduite.

Vérification directe plutôt que déduction — **issues ouvertes et hotspots sur les
trois fichiers touchés par task-281** :

| Fichier | Issues ouvertes | Hotspots |
|---|---|---|
| `ImapService.cs` | **0** | **0** |
| `IMailServerSolicitationRecorder.cs` | **0** | **0** |
| `ImapServiceAppendSolicitationTests.cs` | **0** | **0** |

Sur les 15 hotspots `TO_REVIEW` du projet, **aucun** n'est sur ce diff.

**Conclusion** : passe best-effort sans findings actionnables sur le code de la
task — aucun nettoyage à faire, aucune itération lancée, aucun commit. Le QG
rouge est **antérieur et extérieur** à cette US ; le solder relève d'une revue de
hotspots dédiée, pas d'un cycle de task.

> **Effet de bord à connaître** : l'édition Community n'analyse pas par branche.
> Ce scan a été lancé depuis `feat/task-281-append-to-sent-contention`, donc les
> mesures du projet reflètent désormais cette branche et non `develop`. La
> prochaine analyse depuis `develop` les rétablira.
>
> **Correctif de doc au passage** : `agents/sonar.md` et le skill `sonar-skill`
> annoncent le port **9000** ; le serveur écoute sur **9001**. task-279 avait
> buté sur ce même écart et n'avait produit aucun KPI.

## Lint log (/lint-angular)

**`/lint-angular` du 2026-08-30 — skip clean, `client-angular` hors périmètre.**

| Condition | Constat |
|---|---|
| `client-angular` dans `**Repos**:` ? | **non** — la task déclare `api-mail` seul |
| Code Angular écrit par `/develop` ? | **non** |
| Itérations | **0** |

Aucune commande `nx affected` lancée, aucun fichier touché.

> **Deux modifications locales préexistantes** ont été observées dans
> `Client/Angular/` (branche `feature/nova-rewriting-mss`) :
> `front/apps/mss/src/environments/environment.ts` et
> `front/apps/weda2/src/environments/environment.ts`. Elles **n'appartiennent
> pas à cette US** et sont antérieures à elle. Conformément au mode code-only,
> elles n'ont été ni lintées, ni corrigées, ni approchées : sur `client-angular`
> la forge ne touche jamais à git, et elle ne s'autorise pas davantage à
> « nettoyer » un travail humain en cours.

## Lint mobile log

**`/lint-mobile` du 2026-08-30 — skip clean, `client-mobile` hors périmètre.**

| Condition | Constat |
|---|---|
| `client-mobile` dans `**Repos**:` ? | **non** — la task déclare `api-mail` seul |
| Code mobile écrit par `/develop` ? | **non** |
| Itérations | **0** |

Le clone est resté sur `develop`, arbre propre, aucun fichier touché. Aucune
commande `ng lint` lancée, aucun commit, aucun push.

## Visual verify log

**`/verify-visual` du 2026-08-30 — skip clean, aucun écran concerné.**

| Condition de skip | Constat |
|---|---|
| `client-mobile` touché ? | **non** — `**Repos**: api-mail` |
| `## Stitch design log` présent ? | **non** |
| Fichiers d'écran modifiés | **0** |

US strictement backend (télémétrie `api-mail`). Ni Playwright lancé, ni serveur
`npm start` démarré, ni PNG produit. L'état visuel global de l'application dans
`Docs/epics/img/screens/client-mobile/` est inchangé.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/213
  — label `awaiting-human-merge`, base `develop`, head
  `feat/task-281-append-to-sent-contention` (commit `490b032`).
- `dtos-mss` : branche `feat/task-281-append-to-sent-contention` créée par
  auto-inclusion, **aucun commit, aucune PR** — aucun contrat DTO ne bouge,
  c'était l'attendu.
- `client-angular`, `client-mobile`, `devops`, `psc-proxy-*` : hors périmètre,
  non touchés.

## Code Review Summary

**Verdict : APPROVED** — 3 fichiers revus, 0 bloquant, 1 suggestion non bloquante.

| Fichier | Verdict |
|---|---|
| `src/Application/Services/Implementation/ImapService.cs` | ✅ les 4 `Record` placés **après** chaque `await` (convention task-262) ; si `OpenAsync` lève, `open_folder` n'est pas compté — correct, l'aller-retour n'a pas abouti — ⚠️ le littéral `"AppendToSent"` de `AcquireLockAsync` (`:4054`) duplique la constante neuve ; l'employer des deux côtés ferait vérifier l'invariant par le compilateur plutôt que par un commentaire |
| `src/Application/Telemetry/IMailServerSolicitationRecorder.cs` | ✅ constante documentée, cardinalité bornée, aucune donnée de santé |
| `tests/…/ImapServiceAppendSolicitationTests.cs` | ✅ 3 tests, RED→GREEN vérifié ; assertions sur nombre / ordre / étiquettes, jamais sur des temps ; le chemin d'échec est couvert |

- **Sécurité** : compteurs seuls, aucun secret, aucune donnée de santé.
- **Performance** : 4 incréments sur un chemin qui fait 4 allers-retours réseau.
- **Architecture** : recorder déjà injecté, patron télémétrie établi respecté.

### Vérification

| Contrôle | Résultat |
|---|---|
| Build Debug + Release | ✅ 0 erreur, 0 avertissement |
| Suite complète (Release) | ✅ **3 932 réussis / 0 échec**, 16 ignorés |
| Merge `origin/develop` | ✅ already up to date, aucun conflit |
| `AppHost.cs` (modif locale préexistante) | ✅ **laissé non commité**, staging explicite respecté |

### DOD — état item par item

| Item | État |
|---|---|
| Build 0 erreur | ✅ |
| Tests 0 échec | ✅ |
| Cause de la détention établie et écrite, **chiffres à l'appui** | 🟡 **moitié livrée** — la **décomposition** est établie, écrite et prouvée (4 allers-retours, angle mort d'instrumentation démontré par un cycle RED→GREEN). Les **chiffres de répartition** n'existent pas : le rapport de référence est git-ignoré et absent de ce clone. Reporté au tir de clôture (plan de test manuel, point 7), qui dispose désormais de l'instrument — ce qui n'était pas le cas avant. |
| Dire ce qui a changé depuis task-215/216 si seconde session proposée | ✅ **l'US n'en propose pas**, et le dit explicitement |
| Si remède : acquittement n'attend pas l'archivage | n/a — **aucun remède**, comportement strictement inchangé |
| Si remède : échec d'archivage visible et tracé | n/a — idem |
| Si aucun remède sans contrepartie, l'US s'arrête sur le constat | ✅ **c'est le cas** |
| Aucune donnée de santé dans journaux ni étiquettes | ✅ étiquettes = littéraux de code |

## Merged

**Mergée le 2026-08-30** par `/merge 281 --i-tested`.

| Repo | PR | Merge | Commit squash |
|---|---|---|---|
| `api-mail` | [#213](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/213) | squash | `b85f409110db7833d5c900d05bf108fd38b52450` |
| `dtos-mss` | — | aucune PR | branche sans commit, supprimée |

**Portes de sécurité — toutes vertes, aucune dérogation** (contrairement à
task-275) : `--i-tested` présent, label `awaiting-human-merge`, aucune review
`CHANGES_REQUESTED`, `mergeable: MERGEABLE` / `mergeState: **CLEAN**`, et
surtout **CI verte** (`build=SUCCESS`, `publish=SKIPPED`).

**Règle 5 satisfaite** : CI de `develop` **verte** sur le commit de merge
`b85f409`, vérifiée dans la fenêtre.

- Références distantes supprimées sur les deux repos ; branches **locales
  conservées** (`gh pr merge --squash` seul, jamais `--delete-branch`).
- Clones resynchronisés sur `develop`.
- Aucune branche staging à nettoyer (`/start` isolé, pas un run `/forge`).
- `client-angular`, `client-mobile`, `devops`, `psc-proxy-*` : hors périmètre.

> **Note** : `Api/Mail/src/AppHost/AppHost.cs` porte toujours la modification
> locale non commitée (Seq `5342` → `5341`). Elle n'est **pas** entrée dans la
> PR — staging explicite tenu de bout en bout. Elle reste à committer ou à
> annuler, hors de cette US.

### Ce que `develop` a reçu en parallèle

Le merge a révélé que **task-282 et task-283 ont été livrées et mergées** entre
temps par l'autre machine, **dans l'ordre prescrit** :

| Commit | Task |
|---|---|
| `9edb6d8` | task-282 — la clé du pool de sessions suit le client, plus le jeton (#212) |
| `085fc29` | task-283 — un jeton PSC expiré ressort en 401, plus en 500 muet (#214) |
| `b85f409` | **task-281 — le chemin d'archivage compte ses allers-retours (#213)** |

`282` **avant** `283` : la contrainte d'ordre consignée le 2026-08-30 (découpler
la clé du pool avant de tripler la cadence de refresh, sous peine de franchir le
plafond de 10 connexions IMAP par praticien) a bien été respectée.
