# todo-task-212.md — « Patients du jour » se trompe de jour pendant deux heures chaque nuit

**Repos**: api-mail
**Epic**: E009
**Single frontend**: true
**Dependencies**: aucune

> La liste « patients avec un document aujourd'hui » filtre sur minuit **local**
> des horodatages stockés en **UTC**. En heure d'été, entre 00 h 00 et 02 h 00,
> elle est fausse — et le décalage existe toute l'année, il n'est simplement
> visible qu'à ce moment-là.

> **Origine** : trouvé par accident au `/review` de task-206, dont la passe de
> validation a tourné à **00 h 14**. Le test
> `PatientRepositoryTests.GetWithMedicalDocumentsTodayAsyncShouldReturnPatientsWithTodayDocsAsyncAsync`
> échouait — pas de façon aléatoire, mais **de façon déterministe dans cette
> fenêtre horaire**. C'est ce déterminisme qui a fait chercher au-delà du
> « encore un flaky ».

## Objective

Que la liste des patients ayant reçu un document « aujourd'hui » désigne le même
jour pour le praticien qui la lit et pour la base qui la calcule, à toute heure.

**US backend-only (justification)** : une borne de requête dans
`PatientRepository`, aucun contrat, aucun écran.

## Le défaut, établi

`src/Infrastructure/Repository/PatientRepository.cs:156` —
`GetWithMedicalDocumentsTodayAsync` :

```csharp
var today = DateTime.Today;          // minuit LOCAL
var tomorrow = today.AddDays(1);

.Where(md => md.CreatedAt >= today && md.CreatedAt < tomorrow && md.PatientId != null)
```

Trois faits qui, ensemble, ne laissent pas d'échappatoire :

| Fait | Vérifié où |
|---|---|
| La colonne est `timestamp **without** time zone` | `MailDataContext.cs:136-138` — Npgsql ne convertit donc **rien**, ni à l'écriture ni à la lecture |
| Les valeurs stockées sont en **UTC** | défaut SQL `now()` (conteneur Postgres en UTC) ; et le test du dépôt sème `DateTime.UtcNow` |
| La borne du filtre est en **heure locale** | `DateTime.Today`, `Kind = Local` |

La fenêtre interrogée est donc décalée de l'offset local — **2 heures en été,
1 heure en hiver**. Conséquence concrète en CEST :

- un document reçu à **00 h 30 locale** est horodaté 22 h 30 UTC la veille : il
  **n'apparaît pas** dans « aujourd'hui » ;
- il apparaîtra le lendemain, un jour trop tard.

⚠️ **Ce n'est pas un défaut de test.** Le test le révèle, mais la requête servie
à `GET /patients/today` (`PatientsController.cs:108`) est la même.

## Ce qu'il ne faut PAS conclure trop vite

- **Tous les `DateTime.Today` du code ne sont pas fautifs.**
  `PatientRepository.cs:1055` et `MailDigest.cs:92` calculent un **âge** depuis
  une date de naissance : l'heure locale y est correcte, ne pas les toucher.
- **`OfflineMailDataProvider.cs:157/187`** compare `mail.SentDate?.Date` à
  `DateTime.Today`. `SentDate` vient de l'en-tête du message, pas de nous —
  autre famille de problème, à instruire séparément, **hors scope ici**.
- **`ImapService` / `ImapFolderService`** passent `DateTime.Now.Date` à
  `SearchQuery.DeliveredAfter` : c'est le **serveur IMAP** qui interprète cette
  date, pas notre base. À vérifier, mais **hors scope**.

## Contenu attendu

1. **Trancher la convention** et l'écrire : soit la borne passe en UTC
   (`DateTime.UtcNow.Date`), soit la colonne passe en `timestamp with time zone`.
   Les deux corrigent ; elles n'ont pas le même coût ni la même portée.
   - La borne en UTC est locale au correctif, sans migration — mais « aujourd'hui »
     devient alors **la journée UTC**, ce qui décale la liste pour le praticien
     entre 00 h et 02 h dans l'autre sens.
   - La colonne en `timestamptz` rend la sémantique correcte pour de bon, mais
     c'est une migration (règle 7c) et elle touche d'autres lectures.
   - **Une troisième voie existe** : garder le stockage tel quel et convertir la
     borne locale en UTC (`DateTime.Today.ToUniversalTime()`), ce qui donne « la
     journée du praticien » exprimée dans l'échelle où les données sont écrites.
     C'est probablement la bonne — **mais l'argumenter, pas la présumer**, et
     nommer ce qui se passe si le serveur n'est pas dans le fuseau du praticien.
2. **Corriger `GetWithMedicalDocumentsTodayAsync`** selon la voie retenue.
3. **Rendre le test insensible à l'heure d'exécution** : il doit échouer si la
   borne est fausse, à **n'importe quelle heure**, y compris à 00 h 14. Un test
   qui ne passe que la journée n'est pas un test.
4. **Chercher les autres occurrences du même mélange** (borne locale contre
   colonne `timestamp without time zone` alimentée en UTC) et les lister, même
   celles laissées hors scope — l'inventaire vaut le correctif.

## Hors scope

- `OfflineMailDataProvider` (`SentDate` vient de l'en-tête du message).
- Les requêtes IMAP `DeliveredAfter` (interprétées par le serveur IMAP).
- Les calculs d'âge (`PatientRepository:1055`, `MailDigest:92`) — corrects.
- Une migration généralisée `timestamp` → `timestamptz` sur tout le schéma :
  si la voie 1 la retient pour cette colonne, s'y tenir ; l'extension aux
  autres tables est une task à part.

## Definition of Done

- [ ] Build passes (0 errors) — Tests pass (0 failures)
- [ ] La convention retenue est **écrite** dans le code, avec l'argument qui l'a
      fait préférer aux deux autres
- [ ] Test unitaire : un document créé « maintenant » apparaît dans la liste,
      **quelle que soit l'heure locale simulée** — dont au moins un cas dans la
      fenêtre 00 h 00–02 h 00
- [ ] Test unitaire : un document de la veille n'y apparaît **pas**, même mesuré
      dans cette même fenêtre
- [ ] Le test existant
      `GetWithMedicalDocumentsTodayAsyncShouldReturnPatientsWithTodayDocsAsyncAsync`
      passe à **toute heure** (le rejouer en forçant l'horloge, ou en injectant la
      borne)
- [ ] Si une migration est retenue : audit de la migration générée (règle 7c) —
      lecture du fichier, absence d'opérations fantômes, fichiers compagnons
      présents, « pending changes » vide
- [ ] L'inventaire des autres occurrences du même mélange est consigné dans la
      task, y compris celles laissées hors scope

## Manual Test Plan

1. Lancer l'API locale (AppHost) et ouvrir l'écran listant les patients du jour.
2. Provoquer la réception d'un document médical pour un patient (ou insérer un
   `MailMedicalDocument` avec `CreatedAt = now() at time zone 'utc'`).
3. Vérifier qu'il apparaît **immédiatement** dans « patients du jour ».
4. **Le contrôle qui compte** — refaire l'étape 2 avec un `CreatedAt` situé dans
   la fenêtre piège, par exemple :
   ```sql
   -- 00 h 30 locale un jour d'été = 22 h 30 UTC la veille
   insert into "MailMedicalDocuments" (..., "CreatedAt") values (..., '2026-08-01 22:30:00');
   ```
   puis relire la liste le lendemain matin : le document doit être attribué au
   **2 août** (jour local de sa réception), pas au 1er.
5. Contrôle de non-régression : la liste reste correcte en pleine journée, et le
   plafond de 500 patients (`SearchLimits.TodayPatientsMax`) est inchangé.

> ⓘ Pour reproduire le défaut sans attendre minuit : régler temporairement le
> fuseau de la machine sur `UTC+13` (Pacific/Auckland) — la fenêtre fautive
> couvre alors 13 heures de la journée.

## Branches
- `api-mail` (pushed) : fix/task-212-patients-du-jour-utc — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-212-patients-du-jour-utc
- `dtos-mss` (pushed, auto-inclus) : fix/task-212-patients-du-jour-utc — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/fix/task-212-patients-du-jour-utc (aucun changement de contrat attendu — US backend-only)

## Inventaire — colonnes `timestamp without time zone` et échelle d'écriture

Recensement systématique (`grep DateTime.Today|DateTime.Now` dans `src`, croisé
avec le type de colonne dans `MailDataContext` et le défaut SQL dans
`20240101_SetupMigration.cs`). **✅ corrigé ici · ⚠️ mélange réel, hors scope ·
ⓘ correct, ne pas toucher.**

| # | Emplacement | Constat | Verdict |
|---|---|---|---|
| 1 | `PatientRepository.cs:158` — borne de `GetWithMedicalDocumentsTodayAsync` | `DateTime.Today` (local) comparé à une colonne écrite en UTC | ✅ corrigé — `PractitionerDay.UtcBoundsFor` |
| 2 | `MailRepository.cs:3089` — `CreateMedicalDocumentEntity` | Écrit `MailMedicalDocuments.CreatedAt` en **heure locale**, alors que le chemin COURRIER (`MailRepository.cs:347`) y écrit de l'**UTC** via `NormalizeUtc` | ✅ corrigé — **la même colonne portait deux échelles**, aucune borne ne pouvait être juste pour les deux |
| 3 | Défaut SQL de `MailMedicalDocuments.CreatedAt` | `SystemMethods.CurrentDateTime` → `now()` casté en `timestamp`, donc **fuseau de session Postgres** (UTC dans le conteneur, par accident et non par contrat) | ⚠️ latent — les deux seuls chemins d'insertion (`MailRepository.cs:333` et `CreateMedicalDocumentEntity`) fixent la valeur, le défaut ne se déclenche jamais. Le rendre explicite (`CurrentUTCDateTime`) est une migration FluentMigrator sur une colonne vivante : disproportionné pour un défaut mort |
| 4 | `MailFolder.LastSyncedAt` | **Deuxième mélange avéré, autre colonne** : `ImapHelper.cs:79` écrit `DateTime.Now`, `FolderRepository.cs:73` écrit `DateTime.UtcNow`, et `FolderRepository.cs:82` en prend le `Max` renvoyé au client (`ConnectionController.cs:38`) | ⚠️ hors scope — même classe de défaut, autre fonctionnalité. Conséquence : une heure de dernière synchro fausse de 1–2 h, pas une liste fausse. Mérite sa propre task |
| 5 | `PendingAction.CreatedAt` (`PendingAction.cs:17`, `PendingActionService.cs:65`) vs purge `PendingActionRepository.cs:155` | Écriture **et** borne en heure locale — cohérentes entre elles | ⓘ pas de mélange aujourd'hui. Dérive si l'hôte change de fuseau ; à normaliser en UTC à la prochaine intervention sur ce chemin |
| 6 | Schéma : 7 colonnes `CreatedAt` | 5 en `SystemMethods.CurrentDateTime` (fuseau de session), 2 en `CurrentUTCDateTime` (`MailSignatures`, l.67 ; l.561) | ⚠️ le schéma lui-même n'a pas de convention unique. Constat, pas un correctif |
| 7 | `OfflineMailDataProvider.cs:157/187` | `mail.SentDate?.Date` comparé à `DateTime.Today` — `SentDate` vient de l'en-tête du message | ⓘ hors scope (posé par la task) — autre famille : la donnée n'est pas de nous |
| 8 | `ImapService.cs:565/571`, `ImapFolderService.cs:216/222` | `DateTime.Now.Date` passé à `SearchQuery.DeliveredAfter` | ⓘ hors scope (posé par la task) — la date est interprétée par le **serveur IMAP**, pas par notre base |
| 9 | `PatientRepository.cs:1055`, `MailDigest.cs:92` | `DateTime.Today` pour calculer un **âge** depuis une date de naissance | ⓘ corrects — l'heure locale y est la bonne référence, ne pas toucher |
| 10 | `MailExportService.cs:94`, `MdnService.cs:107` | `DateTime.Now` **formaté pour affichage** (PDF, accusé de lecture) | ⓘ corrects — destinés à un lecteur humain français |

**Ce que l'inventaire apprend au-delà du correctif** : le défaut signalé n'était
pas isolé côté *lecture*. La même colonne était alimentée dans deux échelles
selon le chemin d'ingestion (ligne 2) — corriger la seule borne aurait laissé
faux la moitié des documents, ceux issus du chemin CDA. C'est le vrai contenu de
cette task ; la borne locale n'en était que le symptôme visible.

## Sonar log

**Verdict sur la task : zéro finding sur les 5 fichiers touchés**, établi sous
**trois périmètres d'analyse différents** — c'est le seul résultat de cette
étape sur lequel on peut s'appuyer.

| Fichier | Issues ouvertes |
|---|---|
| `src/Application/Helpers/PractitionerDay.cs` | 0 |
| `src/Infrastructure/Repository/PatientRepository.cs` | 0 |
| `src/Infrastructure/Repository/MailRepository.cs` | 0 |
| `tests/.../PractitionerDayTests.cs` | 0 |
| `tests/.../PatientRepositoryTests.cs` | 0 |

Les **4 `new_violations`** du Quality Gate sont toutes hors du diff, provenance
vérifiée par `git log -L` :

| Règle | Fichier | Introduite par |
|---|---|---|
| `csharpsquid:S125` ×3 | `src/AppHost/AppHost.cs` L8/103/322 | task-195 (5f22334, 2026-07-25) |
| `csharpsquid:S1067` | `src/Infrastructure/Repository/ContactRepository.cs` L210 | task-023 (882d3c61, 2026-05-03) |

Les 4 hotspots non revus (`S2068`, mots de passe du banc) viennent de task-200
(179eb32, 2026-07-27). Aucun n'est corrigé ici : hors périmètre de la task
(règles 5 et 6).

### ⚠️ KPIs projet — non exploitables, et dégradés par cette exécution

**À lire avant le prochain `/sonar`.** Je n'ai pas réussi à reproduire le
périmètre de l'analyse stockée, et j'ai écrasé les mesures projet avec le mien.

| Métrique | Baseline lue avant | Après |
|---|---|---|
| Quality Gate | ERROR | ERROR |
| `code_smells` | 1066 | 7 |
| `coverage` | 70,6 % | 0,0 % |
| `duplicated_lines_density` | 4,0 % | 0,6 % |
| Bugs / Vulnérabilités | 0 / 0 | 0 / 0 |
| Ratings (fiab. / sécu. / maint.) | 1 / 1 / 1 | 1 / 1 / 1 |

**Ce n'est pas une amélioration** — c'est un changement de périmètre. Cause :
`agents/sonar.md` est périmé sur trois points, découverts un par un :

1. `/d:sonar.login=` — rejeté par le scanner (serveur 25.6.0, il faut
   `sonar.token`). Déjà signalé aux cycles précédents.
2. `/d:sonar.cs.opencover.reportsPaths="TestResults/**/coverage.opencover.xml"`
   — ce chemin **ne matche rien** : `codecoverage.runsettings` déclare
   `<Format>cobertura</Format>` et les rapports atterrissent sous
   `tests/*/TestResults/`. D'où la couverture à 0.
3. Aucune mention de `sonar.scanner.scanAll` ni du profil `Weda way`, alors que
   ces deux paramètres font varier `code_smells` d'un facteur 100.

Trois exécutions successives (périmètre large sans exclusions ; canonique en
Release ; canonique en Debug avec forçage OpenCover) ont donné 8, 7 et 7 smells
et 84,6 %, 0 % et 0 % de couverture — aucune ne retrouve le 1066 / 70,6 % de
départ. **La prochaine analyse doit re-baseliner**, et `agents/sonar.md` doit
être corrigé avant, sinon le problème se reproduira à chaque task.

Un rapport de couverture **périmé du 10 juin** traînait par ailleurs dans
`tests/*/TestResults/` et faisait planter l'import (`Line 188 is out of range in
RedisSyncStateStore.cs (lines: 187)`). Supprimé — artefacts de build non suivis.

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/138 — label `awaiting-human-merge`
- `dtos-mss` : aucune PR — branche `fix/task-212-patients-du-jour-utc` créée par précaution, aucun commit (US backend-only, aucun contrat touché)

## Code Review Summary

**APPROVED** — 5 fichiers, 0 blocage.

- `src/Application/Helpers/PractitionerDay.cs` — ✅ helper pur, sans dépendance,
  testable ; la convention et son arbitrage sont dans la doc XML, pas seulement
  dans le message de commit. Repli explicite si la base de fuseaux manque.
- `src/Infrastructure/Repository/PatientRepository.cs` — ✅ surcharge `internal`
  à instant injecté ; la méthode publique reste le seul point qui lit l'horloge.
- `src/Infrastructure/Repository/MailRepository.cs` — ✅ `CreatedAt` du chemin CDA
  aligné sur `NormalizeUtc`, cohérent avec le chemin COURRIER.
- Tests — ✅ tous à instant épinglé, contre-épreuve exécutée.

### Trouvailles de la passe `/forge-simplify` (appliquées)
- `UtcBoundsForToday()` n'avait **aucun appelant** → supprimée.
- Double `try/catch` de résolution de fuseau → `TryFindSystemTimeZoneById`,
  même repli sans exception sur le chemin normal.

### Suggestion non bloquante
- La convention « UTC en `Kind = Unspecified` » vit désormais à **deux endroits** :
  `MailRepository.NormalizeUtc` (privé, 17 appels) et `PractitionerDay`.
  La bonne altitude serait un helper partagé — écarté ici : déplacer
  `NormalizeUtc` touche 17 sites d'appel dans un fichier hors diff (règles 5 et 6).

## Merged
- `api-mail` : **f375896** — squash de la PR #138, mergée le 2026-08-01
- `dtos-mss` : aucune PR (branche sans commit) ; ref distant supprimé

Refs distants supprimés sur les deux repos ; **branches locales conservées**
(`gh pr merge --delete-branch` supprime aussi le local).
