# todo-task-191.md — Intégrité de l'ingestion : ingestion bloquée par une contrainte, dossiers patients dupliqués, horodatages incohérents

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axe accès données).
> Findings vérifiés sur pièces par le PO.

> ### Re-vérification du 2026-08-23 — **pertinente sur deux preuves ; la troisième est corrigée**
>
> Chaque preuve rejouée sur `develop`. **La preuve 3 (horodatages mêlés) est
> corrigée par task-212 : elle doit sortir du périmètre**, ce qui réduit la US
> d'un tiers et retire la migration d'horodatage de son DOD.
>
> | Preuve | 2026-07-25 | Au 2026-08-23 | État |
> |---|---|---|---|
> | 1. Ordre d'écriture invalide | `MailRepository.cs:83-90` | **`:125-131`** — `DetectSuppressionRequestAsync` `:125`, `AddPatientMessageDocumentAsync` `:128`, `db.Mails.Add(mail)` `:131` (toujours **après**) | **valide** |
> | `SaveChanges` intermédiaire | `:325`, `:330` | `AddPatientMessageDocumentAsync` **`:391`** — **trois** `SaveChangesAsync` dans le corps | **valide, pire** |
> | Estampille sur entités suivies | `:2959-2985` | `DetectSuppressionRequestAsync` **`:3901`** | **valide** |
> | 2. Dossiers dupliqués sur la même INS | `:267-269`, `:560-577` | lecture **`:401`** → écriture **`:412`** ; et **`:651-652`** → **`:667`** (avec un repli `.Local` qui ne protège pas entre requêtes) | **valide** |
> | 3. Horodatages locaux et UTC mêlés | `:3089` vs `:347` | **CORRIGÉE (task-212)** | **à retirer** |
>
> **Preuve 3 — corrigée, preuve à l'appui.** `DateTime.Now` a **disparu** de
> `MailRepository` : le seul reste est le **commentaire** de task-212 (`:4059-4062`)
> qui documente le remède, et les deux écritures de la colonne passent par
> `NormalizeUtc(DateTime.UtcNow)` (**`:435`**, **`:4063`**). Côté lecture, la borne
> `DateTime.Today` de « Patients du jour » est remplacée par
> `PractitionerDay.UtcBoundsFor(instant)` (`PatientRepository.cs:210-211`), avec le
> commentaire qui nomme le défaut d'origine. **Ne pas re-livrer ce correctif.**
>
> **Deux résidus, volontairement laissés hors périmètre** (à vérifier avant de
> conclure, pas à corriger d'office) : `PendingActionRepository.cs:250`
> (`DateTime.Now` pour un seuil d'ancienneté) et `PatientRepository.cs:1194`
> (`DateTime.Today` dans `CalculateAge` — un calcul d'âge, pas une borne de
> requête). Aucun des deux n'écrit la colonne visée par la preuve 3.
>
> **Preuve 1 — plus grave qu'écrit.** `AddPatientMessageDocumentAsync` contient
> désormais **trois** `SaveChangesAsync`, pas deux : la fenêtre pendant laquelle un
> `UPDATE` référence une ligne `Mails` inexistante s'est élargie.

## Objective

Corriger trois défauts d'intégrité du chemin d'ingestion des messages, qui ont en
commun de produire des données fausses ou de perdre des messages sans le dire.

**US backend-only (justification)** : persistance côté serveur.

### Preuve (état actuel du code)

**1. Ordre d'écriture invalide ⇒ un message n'est jamais ingéré**
`src/Infrastructure/Repository/MailRepository.cs:83-90` (vérifié par le PO) :
```csharp
await DetectSuppressionRequestAsync(mailDto, mail);   // :83
await AddPatientMessageDocumentAsync(mail, mailDto);  // :86  ← contient un SaveChanges
DataContext.Mails.Add(mail);                          // :88  ← trop tard
```
`DetectSuppressionRequestAsync` (`:2959-2985`) attribue l'identifiant du nouveau
mail puis estampille des documents **suivis** :
`doc.SuppressionRequestedByMailId = newMail.Id` — sur des entités chargées **sans**
`AsNoTracking` (`:2964`). `AddPatientMessageDocumentAsync` appelle ensuite
`SaveChangesAsync` (`:325` et `:330`). Cette sauvegarde intermédiaire émet donc un
`UPDATE` référençant une ligne `Mails` **qui n'existe pas encore** : violation de
`FK_MailMedicalDocuments_SuppressionRequestedByMail`
(`src/Infrastructure/Migrations/20240101_SetupMigration.cs:398`). Le `catch` de
`PersistNewMailAsync` ne gère que les violations d'unicité : l'exception remonte, le
message **n'est jamais ingéré**, et chaque synchronisation suivante rejoue le même
échec. Déclencheur : un message de patient (Mon Espace Santé) qui est **aussi** une
demande de retrait de document — les deux branches s'activent ensemble.

**2. Dossiers patients dupliqués sur la même INS**
`src/Infrastructure/Repository/MailRepository.cs:267-269` et `:560-577` : les deux
chemins de résolution font une **lecture puis écriture non synchronisée**
(`FirstOrDefaultAsync(p => p.Ins == …)` puis `Add`), et l'index sur la colonne est
explicitement **non unique** —
`src/Infrastructure/Migrations/20260610_AddMailPatientInsIndex.cs` indique que
« uniqueness is enforced at the application level », ce que le code **ne fait pas**.
Deux ingestions concurrentes (même rafale de synchronisation, ou arrière-plan qui
chevauche un enrichissement de premier plan) créent deux lignes pour la même INS.
Les lectures utilisent `FirstOrDefaultAsync` : elles en choisissent une
arbitrairement, les documents se répartissent entre les deux, **le praticien ne voit
que la moitié de l'historique du patient** — et une opposition MSS posée sur une
ligne n'est pas honorée quand l'autre est retenue.

**3. Horodatages mêlant heure locale et UTC**
`src/Infrastructure/Repository/MailRepository.cs:3089` écrit
`CreatedAt = DateTime.Now` (Kind=Local) tandis que `:347` écrit
`CreatedAt = NormalizeUtc(DateTime.UtcNow)` — **dans la même colonne**
(`timestamp without time zone`). Npgsql ne rejette que `Kind=Utc` sur ce type : rien
ne lève, et deux bases de temps coexistent silencieusement. Les valeurs par défaut
des migrations sont incohérentes de la même façon (`CurrentDateTime` vs
`CurrentUTCDateTime`, `20240101_SetupMigration.cs:347`).
Conséquence : `GetWithMedicalDocumentsTodayAsync`
(`src/Infrastructure/Repository/PatientRepository.cs:158-165`) filtre sur
`DateTime.Today` (minuit **local**). Sur un serveur en Europe/Paris (UTC+2 en été),
un message de patient reçu à 01:00 locale est stocké 23:00 UTC la veille et
**disparaît** de la liste « Patients du jour ». Le chaînage de versions
(`PatientRepository.cs:828`) s'ordonne aussi sur cette colonne : une chaîne mixte
peut s'ordonner à l'envers.

### Contenu attendu

1. **Ordre d'écriture correct** : le mail doit être inséré avant toute écriture qui
   le référence (ou toutes les écritures doivent partir dans une **seule**
   sauvegarde). Supprimer la sauvegarde intermédiaire au milieu de la construction
   du graphe d'entités.
2. **Atomicité** : l'ingestion d'un message (mail, contenus, documents, liens
   patient, estampilles) doit être atomique — un échec partiel ne doit pas laisser
   un état incohérent.
3. **Unicité de l'INS garantie par le schéma** : contrainte d'unicité en base (le
   seul niveau qui tient sous concurrence), plus gestion propre de la violation
   côté application (retomber sur la ligne existante). Migration FluentMigrator +
   audit règle 7c, en tenant compte des **doublons déjà présents** (voir point 5).
4. **Base de temps unique** : une seule convention pour la colonne (UTC de bout en
   bout, valeurs par défaut de migration alignées), et les requêtes « du jour »
   doivent raisonner dans le **fuseau du praticien** en convertissant explicitement
   — pas en comparant un minuit local à des valeurs UTC.
5. **Inventaire des données existantes** : requêtes de lecture seule recensant
   (a) les INS portées par plusieurs dossiers patients, (b) les valeurs `CreatedAt`
   manifestement en base locale. La **remédiation** (fusion de dossiers patients)
   touche des données de santé : elle exige un arbitrage humain, task dédiée si
   l'inventaire révèle des cas. Livrable ici : inventaire + note.

### Hors scope

- Le rattachement des documents **sans** INS → task-176.
- L'OID et le statut de l'INS → task-183.
- L'exécution d'une fusion de dossiers en production.

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test d'intégration : un message qui est **à la fois** un message de patient et
      une demande de retrait est ingéré avec succès (ce test doit échouer sur le
      code actuel — le vérifier explicitement)
- [ ] Test d'intégration : l'échec partiel d'une ingestion ne laisse aucun état
      incohérent (atomicité vérifiée)
- [ ] Test d'intégration **de concurrence** : deux ingestions simultanées portant la
      même INS aboutissent à **un seul** dossier patient
- [ ] Test unitaire : la violation d'unicité INS est traitée en retombant sur le
      dossier existant, sans erreur remontée au praticien
- [x] ~~Test unitaire : tous les chemins d'écriture de `CreatedAt` produisent la
      même base de temps~~ — **livré par task-212**. Hors périmètre
- [x] ~~Test unitaire : la requête « du jour » retient un document créé à 01:00
      heure locale~~ — **livré par task-212** (`PractitionerDay.UtcBoundsFor`).
      Hors périmètre
- [ ] Migrations FluentMigrator relues selon la règle 7c (**unicité INS** ;
      la partie « valeurs par défaut d'horodatage » est retirée — task-212),
      stratégie de reprise documentée
- [ ] Requête d'inventaire livrée (**doublons INS** ; l'inventaire des horodatages
      en base locale est retiré — task-212) et note de remédiation rédigée
- [ ] Aucune donnée de santé en clair dans les logs ni dans les requêtes
      d'inventaire

## Manual Test Plan

1. Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
2. **Ingestion bloquée** : préparer un message de patient (Mon Espace Santé, donc
   `IsFromPatient`, avec INS) qui répond (`In-Reply-To`) à un message du praticien
   ayant porté un document CDA, **sans** CDA joint — c'est une demande de retrait.
   Synchroniser. **Attendu** : le message est ingéré et la demande de retrait est
   visible. Avant correctif : le message n'apparaît jamais, et Seq montre une
   violation de contrainte rejouée à chaque synchronisation.
3. **Doublon de patient** : provoquer deux ingestions concurrentes pour la même INS
   (lancer une synchronisation d'arrière-plan et ouvrir simultanément le dossier
   pour déclencher un enrichissement de premier plan, sur une boîte contenant
   plusieurs CDA du même patient). **Attendu** : un seul dossier patient, historique
   complet. Avant correctif : deux dossiers, historique scindé.
4. Vérifier qu'une opposition MSS posée sur ce patient est bien honorée en lecture.
5. **Horodatage** : sur un serveur en Europe/Paris, faire ingérer un message de
   patient à une heure locale entre 00:00 et 02:00 (ou décaler l'horloge de test)
   → il apparaît bien dans « Patients du jour ». Avant correctif, il en est absent.
6. Exécuter les requêtes d'inventaire sur une base de test antérieure au correctif →
   elles remontent bien les doublons et les horodatages suspects.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — volets MSSanté et Mon Espace Santé (messages patients)
- **Exigences DSR honorées** : correctif de conformité — intégrité et complétude du
  dossier patient, fiabilité de la réception
- **INS** : **directement concerné** — l'unicité du dossier patient par INS est un
  invariant d'identito-vigilance ; sa violation scinde ou mélange l'historique
  (l'absence d'INS est traitée par task-176, l'OID par task-183)
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : documents CDA r2 ingérés ; parsing et validation Schematron
  via `interop-cda` inchangés
- **Tracé PGSSI-S** : journaliser l'échec d'ingestion d'un message (aujourd'hui
  rejoué silencieusement à chaque cycle) et la détection d'un doublon d'INS —
  évènements techniques, sans donnée de santé
- **Consentement patient** : la demande de retrait de document émanant du patient
  est précisément le flux bloqué par le défaut n° 1 — un droit patient inopérant
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : **à mettre à jour** — inexactitude des données
  (art. 5.1.d : historique patient scindé, liste du jour incomplète) et
  ineffectivité d'une demande de retrait patient. Qualifier la portée via
  l'inventaire, avec le DPO.
