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
