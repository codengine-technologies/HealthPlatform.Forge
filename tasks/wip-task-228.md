# todo-task-228.md — L'enrichissement tient le verrou de session IMAP jusqu'à 58 s : ouvrir un message attend derrière le lot entier

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: **task-227 (wip, à merger d'abord)** — pose les tests qui
assertent réellement le skip des UIDs déjà enrichis, le lot mixte et la chaîne
bout en bout sur base réelle : c'est le filet anti-régression exact du refactor
de cette task (ne pas refactorer la Phase A tant que ces tests ne sont pas sur
`develop`) ; task-079 (mergée) — a séparé la Phase A (fetch IMAP sous verrou)
de la Phase B (persistance hors verrou) : cette task découpe la Phase A elle-même ;
task-211 (mergée) — instrumentation des trois verrous, indispensable à la
contre-épreuve ; task-213/214 (archivées) — leçon de méthode : tout correctif de
verrou se **prouve par un tir avant/après en iso-conditions**, jamais par
intuition (la voie d'écriture de task-213 a été retirée après contre-épreuve).
**Priorité**: **1** — c'est le goulet structurel désigné par le tir
journey-mssante-n300 du 2026-08-04 : il dégrade **trois gestes du médecin à la
fois** (ouvrir un message, rafraîchir l'inbox, marquer lu).

## Objective

Qu'aucun geste court du médecin (ouvrir un message, lister un dossier, marquer
lu) n'attende plusieurs secondes derrière un **lot d'enrichissement entier** de
sa propre session. Aujourd'hui, `EnrichEmailsAsync` acquiert le verrou
`imap_session` **une fois pour tout le lot** et le garde pendant toute la
Phase A (fetch réseau des corps + pièces jointes de chaque message, en
séquentiel, sous latence MSSanté) : détention p95 mesurée à **58,5 s**.

La US demande de **découper la Phase A en sous-lots** : acquérir le verrou,
fetcher un sous-lot de messages, relâcher le verrou, et laisser les opérations
courtes de la même session s'intercaler avant le sous-lot suivant. La taille de
sous-lot est un paramètre de configuration avec une valeur par défaut
raisonnable (ordre de grandeur 10–20 UIDs — à faire trancher par la mesure,
pas par le goût).

**US backend-only (justification)** : portée d'un verrou applicatif dans
`ImapService.EnrichEmailsAsync` (Phase A). Aucun contrat DTO, aucun écran,
aucun changement de comportement fonctionnel visible — seulement l'ordonnancement
interne des opérations IMAP d'une session.

## La mesure — tir `journey-mssante-n300` du 2026-08-04

Rapport : `Api/Mail/tests/loadtest-k6/reports/2026-08-04/report-journey-mssante-n300-142603.md`
(300 médecins, modèle fermé, K=1,2, latence mssante injectée).

| Verrou / opération | Attente p95 | **Détention p95** | Acquisitions/s |
|---|---|---|---|
| `imap_session` (global) | 0,765 s | **58,500 s** | 52,84 |
| `imap_session` / `EnrichEmails` | 0,005 s | **58,500 s** | 2,80 |
| `imap_session` / `GetEmailContent` | **1,790 s** | 2,112 s | 17,84 |

**Lecture.** La détention du verrou de session est entièrement portée par
`EnrichEmails` : le fetch réseau du lot complet se fait sous le verrou
(Phase A), et c'est `GetEmailContent` — le geste du médecin qui ouvre un
message — qui paie l'attente (1,79 s au p95, 17,8 acquisitions/s). Les max
aberrants du tir (`read_list` 15,1 s, `read_content` 7,4 s, `mark_read` 7,4 s)
sont cohérents avec un geste coincé derrière un lot d'enrichissement.

La cause est confirmée dans le code : depuis task-079 la persistance (Phase B)
est bien hors verrou, mais la Phase A garde le verrou pendant **toute** la
boucle de fetch des messages du lot.

## Contraintes — ce que le découpage ne doit pas casser

1. **La garantie anti-course de la clé de verrou.** La clé actuelle
   (`EnrichEmails:{folder}:{pendingUidsHash}`) sérialise deux passes
   d'enrichissement concurrentes sur le **même** jeu de UIDs, précisément pour
   éviter la course sur l'upsert par UID (`DbUpdateConcurrencyException` vue en
   Seq avant ce correctif — commentaire en tête de la méthode). Relâcher le
   verrou entre deux sous-lots rouvre potentiellement cette fenêtre : le
   découpage doit préserver l'exclusion entre passes concurrentes sur les mêmes
   UIDs (par exemple en conservant une sérialisation au niveau du lot logique,
   tout en relâchant la session IMAP entre sous-lots). C'est le point dur de la
   US — s'il s'avère irréductible, ouvrir `questions/task-228.md` plutôt que
   d'affaiblir la garantie.
2. **La complétude de l'enrichissement.** Un lot interrompu entre deux
   sous-lots (annulation, erreur IMAP) doit laisser le système dans l'état déjà
   toléré aujourd'hui : les UIDs non traités restent « pending » et sont repris
   à la passe suivante. Aucun message perdu, aucun message enrichi deux fois
   avec des contenus divergents.
3. **Le coût total de l'enrichissement.** Relâcher/réacquérir le verrou et
   rouvrir le dossier IMAP à chaque sous-lot a un coût (aller-retour sous
   latence MSSanté). La durée totale d'enrichissement d'un lot ne doit pas se
   dégrader au-delà de ce que la contre-épreuve juge acceptable (< +20 % sur la
   durée de bout en bout d'un lot, à confirmer au tir).
4. **La télémétrie existante.** Les compteurs de verrous (task-211) et les
   activités OTLP doivent continuer de mesurer chaque acquisition — c'est eux
   qui rendent la contre-épreuve possible.

## Definition of Done

- [ ] Build passes (0 errors) — `dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) — `dotnet test HealthPlatform.Api.Mail.sln`
- [ ] La Phase A d'`EnrichEmailsAsync` fetch par sous-lots, verrou `imap_session` relâché entre chaque sous-lot
- [ ] Taille de sous-lot configurable (options .NET), valeur par défaut documentée dans le code
- [ ] La garantie anti-course entre passes concurrentes sur les mêmes UIDs est préservée (contrainte 1) — test unitaire qui le prouve
- [ ] Unit tests du découpage : lot < taille de sous-lot (1 seul sous-lot), lot multiple, annulation entre deux sous-lots (reprise propre), erreur IMAP au milieu (UIDs restants toujours pending)
- [ ] Aucune régression sur les tests d'enrichissement existants
- [ ] Aucune donnée de santé en clair dans les logs (INS, NIR, contenu CDA, contenu MSSanté) — les logs de sous-lots ne loggent que folder + compte d'UIDs
- [ ] **Contre-épreuve au banc (bloquante pour le merge, pas pour la PR)** : tir `journey` n300 en iso-conditions (même K, même seed, reset-state, même lignée de code à la task près) avant/après, et dans le rapport « après » :
  - détention p95 `imap_session` / `EnrichEmails` **très nettement réduite** (ordre de grandeur attendu : ≤ 10 s)
  - attente p95 `imap_session` / `GetEmailContent` **en nette baisse** (référence : 1,79 s)
  - durée de bout en bout d'un lot d'enrichissement non dégradée au-delà de +20 %
  - vérification par base toujours PASS (propriété + complétude), zéro `DbUpdateConcurrencyException` en Seq

## Manual Test Plan

- Monter le banc : suivre le skill `loadtest-skill` (AppHost profil `loadtest`,
  GreenMail/Dovecot + Toxiproxy, seed des boîtes)
- Tir de contre-épreuve : `journey`, 300 médecins, latence `mssante`, K=1,2,
  iso-conditions avec le tir de référence `journey-mssante-n300-142603`
  (reset-state avant tir — la bande froide recouvre la bande enrich)
- Ouvrir le rapport généré dans `Api/Mail/tests/loadtest-k6/reports/{date}/`
- Comparer la table « Verrou de session `imap_session`, par opération » au
  rapport de référence du 2026-08-04 : détention `EnrichEmails` et attente
  `GetEmailContent` doivent avoir chuté dans les proportions du DOD
- Vérifier « Vérification par base » : PASS, 0 sujet étranger, complétude tenue
- Vérifier en Seq (MCP seq-local) : aucune `DbUpdateConcurrencyException`,
  aucun nouveau warning d'enrichissement hors bruit connu
- Contrôle fonctionnel rapide : ouvrir l'inbox d'un praticien de test pendant
  qu'un enrichissement tourne — l'ouverture d'un message ne doit plus se figer
  plusieurs secondes

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — optimisation de performance interne, aucune exigence DSR nouvelle honorée ni retirée
- **Exigences DSR honorées** : non applicable — pas de changement de périmètre fonctionnel
- **INS** : non applicable — aucun traitement d'identité modifié ; l'enrichissement CDA en aval (Phase B) est inchangé
- **Authentification PS** : inchangée — la US ne touche pas au flux d'authentification (PSC/e-CPS)
- **Habilitations** : non applicable — aucune règle d'accès modifiée
- **Interop CI-SIS** : non applicable — le parsing CDA (`interop-cda`) et son ordonnancement Phase B sont hors périmètre
- **Tracé PGSSI-S** : inchangé — les évènements existants (enrichissement, accès messagerie) restent journalisés ; les nouveaux logs de sous-lots ne portent que folder + compte d'UIDs, jamais de contenu
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé — aucun flux ni stockage nouveau
- **AIPD / impact RGPD** : inchangé — aucun traitement nouveau, aucune donnée nouvelle

## Branches

- `api-mail` (pushed) : `fix/task-228-enrich-phase-a-chunking` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-228-enrich-phase-a-chunking
- `dtos-mss` (pushed, auto-inclus) : même nom de branche — aucun changement de contrat attendu (US backend-only, portée d'un verrou applicatif), donc pas de PR si aucun commit.

**Base** : `develop` d'`api-mail` au commit `4ec2b73` — **task-227 y est mergée**.
Ce n'est pas un détail : cette US refactore `EnrichEmailsAsync`, c'est-à-dire
**exactement** le code que task-227 vient de garder. Les 13 tests de la chaîne
d'analyse font donc office de filet sur ce refactoring — dont les deux tests
réparés, qui échouent désormais si le verrouillage de l'analyse est cassé.

**Dépendances vérifiées** : task-079, task-211, task-213 et task-214 sont toutes
dans `tasks/archived/`.

**Préfixe `fix/`** : la US corrige un défaut **mesuré** (détention p95 du verrou
de session à 58,5 s au tir n300 du 2026-08-04), pas une amélioration spéculative.


---

## Develop log

**Commit** : `d863087` — `perf(imap): task-228 — decouper la phase A de l'enrichissement en sous-lots`
**Branche** : `fix/task-228-enrich-phase-a-chunking` (poussée sur `api-mail`)
**Base** : `develop` @ `4ec2b73` (task-227 mergée)

### Ce qui a changé

| Fichier | Nature |
|---|---|
| `src/Application/Services/Implementation/ImapService.cs` | Phase A découpée en sous-lots ; verrou de session pris/rendu **par fenêtre** ; `FetchedMail` libéré ; commentaire de `ComputePendingUidsHash` corrigé |
| `src/Application/Options/MailOptions.cs` | `EnrichFetchChunkSize` (défaut **15**) |
| `tests/mss.mail.application.tests/Services/Imap/ImapServiceTests.cs` | 7 tests de découpage + `BuildServiceWithChunkSize(int)` |

Découpage : la boucle de fetch itère `ChunkForEnrichment(pendingUids, EnrichFetchChunkSize)`
et délègue chaque fenêtre à `FetchEnrichmentChunkAsync`, qui ouvre **son** `ImapLockScope`.
L'ordre décroissant des UIDs est conservé — les messages récents, ceux que le
médecin regarde, arrivent dans la première fenêtre au lieu d'attendre la fin du lot.

Phase B inchangée : un seul appel à `PersistEnrichedBatchAsync`, donc **une** prise
du verrou de persistance par (boîte, dossier).

### Deux constats que la US ne pouvait pas connaître

**1. La contrainte 1 se trompait d'endroit — le hash d'UIDs ne sérialise rien.**

La US posait comme risque principal que relâcher le verrou entre sous-lots
rouvrirait la course sur l'upsert par UID, en s'appuyant sur ce commentaire :

> *« Lock key includes a stable hash of the actual UID set […] so two concurrent
> enrichment passes hitting the same UIDs serialize on the same key »*

Vérifié par le code : `AcquireLockAsync` transmet ce libellé à `ImapLockScope`,
qui appelle `LockImapClientAsync(userContext)` — lequel keye le sémaphore sur
`{email}_{ClientSessionId}` **et rien d'autre**. Le hash n'influence **aucune**
décision de verrouillage, et ne survit même pas dans les métriques
(`LockOperationFamily` le tronque au premier `:`).

La garantie anti-course vit dans le **verrou de persistance** par (boîte, dossier),
pris en Phase B — hors du découpage. Donc découper la Phase A n'affaiblit rien :
il n'y avait rien à affaiblir à cet endroit.

Commentaire réécrit pour dire ce que le hash fait réellement (un libellé de
journal, conservé pour ça). Propriété figée par
`EnrichEmailsAsync_KeepsThePersistLockWhichIsTheRealAntiRaceGuardAsync`.

**2. `FetchedMail` n'était libéré par aucun chemin — fuite préalable.**

`FetchedMail` est `IDisposable` (il possède un `IheXdmScratchSet`, donc des
répertoires de travail sur disque) et ni `PersistEnrichedBatchAsync`, ni
`PersistEnrichedMailAsync`, ni les chemins d'erreur ne le libéraient : les
répertoires ne disparaissaient qu'au balayage de démarrage. Corrigé dans le bloc
restructuré (`finally` + `DisposeAll`), parce que laisser une fuite connue dans du
code qu'on réécrit serait pire. Sûr : `BuildMailDtoAsync` consomme les chemins de
façon synchrone, personne n'en a besoin après la Phase B.

### Tests

7 nouveaux, tous sur le **nombre** d'acquisitions du verrou — la seule grandeur
qui prouve le découpage. Une durée dépendrait de la machine ; un test qui ne
compte rien laisserait passer un lot redevenu monolithique.

| Test | Ce qu'il fige |
|---|---|
| `WhenBatchFitsInOneChunk_TakesTheSessionLockOnce` | Cas limite bas : pas de fenêtre superflue |
| `WithMoreUidsThanTheChunkSize_ReleasesAndRetakesTheLock` | **Le cœur** : 5 UIDs / sous-lot 2 ⇒ 3 fenêtres, 5 messages enrichis |
| `EnrichesTheMostRecentUidsFirst` | Ordre décroissant conservé |
| `WhenAChunkFailsToConnect_PersistsWhatWasAlreadyRead` | Le travail réseau déjà payé n'est pas jeté ; le reste redevient « pending » |
| `WhenCancelledBetweenTwoChunks_PersistsNothing` | Comportement d'annulation d'avant task-228 délibérément conservé |
| `KeepsThePersistLockWhichIsTheRealAntiRaceGuard` | 3 fenêtres de fetch, **1** persistance |
| `WithAnInvalidChunkSize_FallsBackToTheDefault` | Une taille ≤ 0 en config ne donne pas une boucle qui n'avance pas |

**Preuve ROUGE** — en neutralisant le découpage (sous-lot = `int.MaxValue`, donc
lot monolithique), **3 tests échouent** :
`KeepsThePersistLockWhichIsTheRealAntiRaceGuard`,
`WhenAChunkFailsToConnect_PersistsWhatWasAlreadyRead`,
`WithMoreUidsThanTheChunkSize_ReleasesAndRetakesTheLock`. Découpage rétabli, aucune
trace du patch de preuve dans le commit.

**Filet task-227** : les 13 tests de la chaîne d'analyse (dont les deux réparés)
restent verts — le refactoring n'a pas cassé le verrouillage de l'analyse.

### Suite complète

`3 412` réussis, `16` ignorés, **1** échec :
`Services.Export.MarkdownPdfRendererTests.RenderHeadingPreservesText`.

Flaky préexistant (`UglyToad.PdfPig`, connu et documenté), **sans rapport avec le
diff** : relancé **3 fois sur 3 en isolation, vert à chaque fois**. Ce n'est pas
une régression, et ce n'est pas non plus une excuse — c'est vérifié, pas supposé.

### ⚠️ Ce que ce commit ne prouve PAS

**La valeur 15 n'est pas mesurée.** C'est le milieu de la fourchette 10–20 donnée
par le PO. Elle est configurable **précisément** pour que le banc la tranche.

**Le gain n'est pas mesuré.** Les tests prouvent le *découpage* (le verrou est
rendu N fois), pas la *latence* (p95 de détention, p95 d'ouverture d'un message).
La contre-épreuve `journey-mssante-n300` avant/après est **bloquante pour le
merge, pas pour la PR** — elle exige le nœud de banc distant, donc c'est la main
de l'humain. C'est la leçon de task-213 : un correctif de verrou se prouve par un
tir, jamais par intuition. Et celle de task-222 : un chiffre non opposable ne
vaut rien.


---

## Simplify log

**Repos éligibles touchés** : `api-mail` seul.
`dtos-mss` : branche créée (auto-inclusion) mais **aucun commit** — le contrat est
inchangé, comme la US le prévoyait. Et de toute façon hors périmètre de cette étape
(porteur de contrat, jamais simplifié).

**Commit** : `fb4a21d` — `refactor(imap): task-228 — deleguer le decoupage a Enumerable.Chunk et reutiliser DisposeAll`
(−13 / +10 lignes, un seul fichier)

### Deux prises, sur les axes réutilisation et simplification

**1. `ChunkForEnrichment` réécrivait `Enumerable.Chunk`.**
La méthode portait une arithmétique d'offsets à la main (`GetRange` +
`Math.Min` + boucle `for`) alors que `Enumerable.Chunk` fait précisément cela
depuis .NET 6. Elle se réduit à ce qu'elle a de propre à dire — **l'ordre**
décroissant — et le découpage est délégué. Un endroit de moins où se tromper d'un
cran, pour zéro information perdue. Signature `IEnumerable<uint[]>` ; le paramètre
du consommateur passe à `IReadOnlyList<uint>`.

**2. Le `finally` recopiait `DisposeAll`.**
J'avais créé le helper puis oublié de l'appeler à l'un des deux endroits. Réutilisé.

### Re-validation (filet anti-régression)

| Suite | Résultat |
|---|---|
| Build solution | **0 avertissement, 0 erreur** |
| `application` | 1948 / 1948 |
| `api` | 649 / 649 |
| `domain` | 102 / 102 |
| `infrastructure` | 410 / 410 |

Dont les 7 tests de découpage et les 13 gardes de la chaîne d'analyse (task-227).
La passe qualité n'a pas changé le comportement.

### Deux artefacts d'environnement, nommés pour ne pas être pris pour des régressions

**`--artifacts-path` casse les 4 scans de sources.** L'AppHost tournait et
verrouillait `src/Api/bin` (MSB3026), j'ai donc compilé via `--artifacts-path` —
ce qui déplace `AppContext.BaseDirectory` hors du dépôt et fait échouer les tests
qui remontent au `RepoRoot()` : `SecretLiteralScanTests` et les **3**
`MailContentWriterScanTests` de task-227. Vérifié en recompilant normalement : les
4 redeviennent verts. Ce n'est pas une régression, c'est le prix de mon propre
contournement de verrous.

À noter tout de même : le garde-du-garde `Assert.NotEmpty(writers)` de task-227
a fait exactement son travail ici — il a **échoué bruyamment** au lieu de passer
en silence sur un scan devenu aveugle. C'est la propriété pour laquelle il a été
écrit, et elle vient d'être exercée pour de vrai.

**Un échec intermittent, non reproduit et non attribué.** Une exécution d'`api`
a rendu 648/649 ; les **4** suivantes ont rendu 649/649. J'ai perdu le nom du test
dans un filtre `grep`, donc **je ne l'attribue pas** : le défaut d'isolation connu
sur `develop` (écouteur d'activité global,
`GetFolderTodayAsync_HappyPath_TagsTheImapActivityWithPerCommandDurations`) en est
le candidat plausible, pas une certitude. Le nommer sans preuve serait exactement
la faute que task-227 a eu à réparer.

**Routage** : `api-mail` touché ⇒ `/sonar 228`.
