# todo-task-191.md — Intégrité de l'ingestion : ingestion bloquée par une contrainte, dossiers patients dupliqués sur la même identité INS

**Repos**: api-mail
**Dependencies**: — (task-183 mergée le 2026-09-08, prérequis satisfait)
**Epic**: E009
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axe accès données).
> Findings vérifiés sur pièces par le PO.

> ### Historique des re-vérifications
>
> **2026-08-23** — la preuve 3 (horodatages locaux et UTC mêlés) est **corrigée par
> task-212** (`NormalizeUtc(DateTime.UtcNow)` sur toutes les écritures de `CreatedAt`,
> `PractitionerDay.UtcBoundsFor` pour la borne « du jour »). Retirée du périmètre.
> Deux résidus laissés volontairement hors périmètre : `PendingActionRepository.cs`
> (`DateTime.Now` pour un seuil d'ancienneté) et `PatientRepository.CalculateAge`
> (`DateTime.Today`, un calcul d'âge). Aucun n'écrit la colonne visée.
>
> **2026-09-08** — re-vérification sur `develop` à `da2f2b6` (task-183 mergée).
>
> | Preuve | État | Emplacement actuel |
> |---|---|---|
> | 1. Ordre d'écriture invalide | **valide, inchangée** | `MailRepository.cs:125` (`DetectSuppressionRequestAsync`), `:128` (`AddPatientMessageDocumentAsync`), `:131` (`db.Mails.Add(mail)` — toujours **après**) ; deux `SaveChangesAsync` intermédiaires `:483`, `:488` ; estampille sur entités suivies `:4040` |
> | 2. Dossiers dupliqués | **valide, reformulée** | task-183 a fait entrer l'**OID** dans la clé d'identité (`MailPatients.Oid`, nullable). La lecture-puis-écriture non synchronisée subsiste sur les deux chemins : `LoadPatientsByInsAsync` `:334` → `ResolveMedicalDocumentPatient` `:398` (CDA), et `:471` → `:482` (message patient). L'index `IX_MailPatients_Ins` reste non unique ; la migration `20260908160000_AddPatientInsOid` n'ajoute aucun index. La contrainte cible n'est plus « INS unique » mais **« (Ins, Oid) unique »** — voir point 3. |
> | 3. Horodatages | **corrigée (task-212)** | hors périmètre, ne pas re-livrer |
>
> **Ce que task-183 change pour cette US** :
> - La clé d'identité est **(matricule, domaine d'attribution)**. `Oid = NULL` signifie
>   « domaine inconnu » (lignes antérieures à task-183) ; un dossier `NULL` **adopte**
>   le domaine du premier document qui en porte un (`MatchPatientOnDomain`, cas 3).
>   La contrainte d'unicité doit donc traiter `NULL` comme une valeur (deux dossiers
>   « domaine inconnu » sur le même matricule sont bien un doublon) et l'adoption est
>   un `UPDATE` qui peut lui aussi entrer en collision avec un `INSERT` concurrent.
> - Le chemin **message patient** (`AddPatientMessageDocumentAsync`) n'a **pas** été
>   aligné : il ne renseigne pas `Oid` (l'adresse Mon Espace Santé ne porte que le
>   matricule) et résout avec `FirstOrDefaultAsync(p => p.Ins == ins)` — choix
>   **arbitraire** si plusieurs domaines existent pour ce matricule, là où le chemin
>   CDA applique la règle « document sans domaine → réutiliser l'existant » via
>   `MatchPatientOnDomain`. Cette incohérence entre les deux chemins entre dans le
>   périmètre (point 3).
> - L'inventaire demandé au point 5 est **le même** que celui demandé par la question
>   3.1 de `questions/task-183.md` (matricules portés par plusieurs dossiers). Cette US
>   en est le véhicule ; la remédiation reste un protocole humain, comme convenu là.

## Objective

Corriger deux défauts d'intégrité du chemin d'ingestion des messages, qui ont en
commun de produire des données fausses ou de perdre des messages sans le dire.

**US backend-only (justification)** : persistance côté serveur.

### Preuve (état actuel du code — `develop` au 2026-09-08)

**1. Ordre d'écriture invalide ⇒ un message n'est jamais ingéré**
`src/Infrastructure/Repository/MailRepository.cs:125-131` :
```csharp
await DetectSuppressionRequestAsync(mailDto, mail);   // :125
await AddPatientMessageDocumentAsync(mail, mailDto);  // :128  ← contient deux SaveChanges
db.Mails.Add(mail);                                   // :131  ← trop tard
```
`DetectSuppressionRequestAsync` (`:3995-4043`) attribue l'identifiant du nouveau
mail (`Guid.CreateVersion7()`, `:4016`) puis estampille des documents **suivis** :
`doc.SuppressionRequestedByMailId = newMail.Id` (`:4040`) — entités chargées **sans**
`AsNoTracking` (`:4020`). `AddPatientMessageDocumentAsync` appelle ensuite
`SaveChangesAsync` (`:483` création du patient, `:488` mise à jour de son email).
Cette sauvegarde intermédiaire émet donc un `UPDATE` référençant une ligne `Mails`
**qui n'existe pas encore** : violation de
`FK_MailMedicalDocuments_SuppressionRequestedByMail`
(`src/Infrastructure/Migrations/20240101_SetupMigration.cs:398`). Le `catch` de
`PersistNewMailAsync` (`:534`) ne gère que les violations d'unicité : l'exception
remonte, le message **n'est jamais ingéré**, et chaque synchronisation suivante
rejoue le même échec. Déclencheur : un message de patient (Mon Espace Santé, avec
INS) qui est **aussi** une demande de retrait de document (répond à un message
porteur de CDA, sans CDA joint) — les deux branches s'activent ensemble. Aucun test
n'exerce cette combinaison aujourd'hui.

**2. Dossiers patients dupliqués sur la même identité (matricule, domaine)**
Les deux chemins de résolution font une **lecture puis écriture non synchronisée** :
- chemin CDA : `LoadPatientsByInsAsync` (`:334-336`) charge les candidats, puis
  `ResolveMedicalDocumentPatient` crée le dossier manquant (`:398`). Le dictionnaire
  de candidats ne protège que **dans un même lot** de documents, pas entre requêtes ;
- chemin message patient : `FirstOrDefaultAsync(p => p.Ins == ins)` (`:471`) puis
  `AddAsync` (`:482`).

L'index sur la colonne est explicitement **non unique** —
`20260610_AddMailPatientInsIndex.cs` indique que « uniqueness is enforced at the
application level », ce que le code **ne fait pas** — et task-183 n'a ajouté aucun
index sur `(Ins, Oid)`. Deux ingestions concurrentes (même rafale de
synchronisation, ou arrière-plan qui chevauche un enrichissement de premier plan)
créent deux lignes pour la même identité. Les lectures en choisissent une
arbitrairement, les documents se répartissent entre les deux, **le praticien ne voit
que la moitié de l'historique du patient** — et une opposition MSS posée sur une
ligne n'est pas honorée quand l'autre est retenue.

### Contenu attendu

1. **Ordre d'écriture correct** : le mail doit être inséré avant toute écriture qui
   le référence (ou toutes les écritures doivent partir dans une **seule**
   sauvegarde). Supprimer les sauvegardes intermédiaires au milieu de la
   construction du graphe d'entités.
2. **Atomicité** : l'ingestion d'un message (mail, contenus, documents, liens
   patient, estampilles) doit être atomique — un échec partiel ne doit pas laisser
   un état incohérent.
3. **Unicité de l'identité patient garantie par le schéma** : contrainte d'unicité
   en base sur **(Ins, Oid)** — le seul niveau qui tient sous concurrence — avec
   `NULL` traité comme une valeur (`NULLS NOT DISTINCT`, PostgreSQL ≥ 15, ou index
   partiel équivalent ; vérifier la version du serveur cible), plus gestion propre de
   la violation côté application : retomber sur la ligne existante, y compris quand la
   collision vient de l'**adoption** de domaine (`UPDATE` d'un dossier `NULL` contre un
   `INSERT` concurrent du même domaine). **Aligner le chemin message patient** sur la
   règle de `MatchPatientOnDomain` (document sans domaine → réutiliser l'existant,
   sans choix arbitraire entre domaines) au lieu de `FirstOrDefaultAsync`. Migration
   FluentMigrator + audit règle 7c, en tenant compte des **doublons déjà présents**
   (point 4) : la migration doit **échouer proprement** ou être **conditionnée** si
   l'inventaire n'est pas vide, jamais fusionner ni supprimer des lignes.
4. **Inventaire des données existantes** : requête de lecture seule recensant les
   identités `(Ins, Oid)` portées par plusieurs dossiers patients (dont les paires
   `NULL`). Même livrable et même format que `Docs/task-193-inventaire-*.sql`
   (précédent task-193). La **remédiation** (fusion de dossiers) touche des données
   de santé : elle exige un arbitrage humain — c'est la question 3 de
   `questions/task-183.md`, à référencer, task dédiée si l'inventaire révèle des cas.
   Livrable ici : inventaire + note.

### Poids relatif des deux défauts (analyse du 2026-09-08)

- **Défaut 2 — structurel, pas à la marge.** L'enrichissement d'arrière-plan traite
  les mails en parallèle (`EnrichmentMaxDegreeOfParallelism = 4` par défaut,
  `BackgroundEnrichmentProcessor.cs:109`) et peut chevaucher un enrichissement de
  premier plan sur la même boîte. Le cas déclencheur est courant : plusieurs documents
  du même patient reçus dans la même vague (laboratoire, hôpital). Le doublon créé est
  permanent et invisible. C'est la raison principale de la task.
- **Défaut 1 — rare, effet grave.** Le déclencheur exige qu'un message Mon Espace Santé
  réponde à un message **de la boîte de réception** porteur de documents (les réponses
  du praticien sont dans « Envoyés », exclues par `IsInSentDraftOrTrashFolder`). Cas
  plausible : un patient qui enchaîne deux messages dans la même conversation. L'échec
  est attrapé **par mail** (`ImapService.cs:1844`, `BackgroundEnrichmentProcessor.cs:130`),
  le reste de la synchronisation continue ; ce message-là est perdu en silence.

> ### ⚖️ Arbitrage humain requis — la détection de retrait s'applique-t-elle aux messages de patient ?
>
> La règle task-015 (LGC.MSS/UX.05) lit « réponse sans CDA à un mail porteur de
> documents » comme une **demande de retrait**. Aujourd'hui le crash du défaut 1
> empêche cette lecture de produire un effet sur les messages de patient. Corriger
> l'ordre d'écriture la rendra **effective** : un patient qui répond « merci » dans un
> fil dont le message précédent porte un document (y compris son propre courrier,
> catégorie `COURRIER`) marquerait ce document comme retiré.
>
> Deux options, toutes deux corrigent le crash :
> - **(a)** exclure les mails `IsFromPatient` de `DetectSuppressionRequestAsync` — la
>   demande de retrait patient passe par un autre canal (à préciser) ;
> - **(b)** conserver la règle telle quelle pour les patients, avec le comportement
>   ci-dessus assumé.
>
> Sans réponse, `/develop` implémente **(a)** et le consigne : c'est l'option qui ne
> crée aucun effet nouveau sur des données de santé. La section « Consentement
> patient » ci-dessous, qui présentait le flux bloqué comme un droit patient, est à
> relire à la lumière de cette décision.

### Hors scope

- Le rattachement des documents **sans** INS → task-176 (livrée).
- L'OID et le statut de l'INS, l'annonce `X-MSS-INS` → task-183 (livrée).
- La base de temps des horodatages → task-212 (livrée). Ne pas re-livrer.
- La réunion de dossiers NIA/NIR d'une même personne (matricules **différents**) →
  arbitrage `questions/task-183.md`, question 3.
- L'exécution d'une fusion de dossiers en production.

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test d'intégration : un message de patient qui répond à un message de la boîte
      de réception porteur de documents, sans CDA joint, est ingéré avec succès et
      produit l'effet retenu par l'arbitrage ci-dessus — aucune estampille de retrait
      en option (a), estampille en option (b) (ce test doit échouer sur le code
      actuel — le vérifier explicitement et le consigner)
- [ ] Test d'intégration : l'échec partiel d'une ingestion ne laisse aucun état
      incohérent (atomicité vérifiée)
- [ ] Test d'intégration **de concurrence** : deux ingestions simultanées portant la
      même identité `(Ins, Oid)` aboutissent à **un seul** dossier patient — un cas
      avec domaine connu, un cas avec `Oid = NULL`
- [ ] Test d'intégration : une **adoption** de domaine concurrente d'une création du
      même domaine aboutit à un seul dossier
- [ ] Test unitaire : la violation d'unicité est traitée en retombant sur le dossier
      existant, sans erreur remontée au praticien
- [ ] Test unitaire : le chemin message patient réutilise le dossier existant selon
      la règle de `MatchPatientOnDomain` (pas de `FirstOrDefault` arbitraire entre
      domaines)
- [ ] Migration FluentMigrator relue selon la règle 7c (unicité `(Ins, Oid)`,
      comportement `NULL` explicité), stratégie de reprise documentée dans la
      migration : comportement si des doublons existent déjà
- [ ] Requête d'inventaire livrée (`Docs/task-191-inventaire-*.sql`, doublons
      `(Ins, Oid)`) avec test d'intégration, note de remédiation rédigée et liée à
      `questions/task-183.md` (question 3)
- [ ] Aucune donnée de santé en clair dans les logs ni dans la requête d'inventaire
      (matricules jamais journalisés — classification par domaine uniquement, comme
      task-183)

## Manual Test Plan

1. Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
2. **Ingestion bloquée** : préparer un message de patient (Mon Espace Santé, donc
   `IsFromPatient`, avec INS) qui répond (`In-Reply-To`) à un message du praticien
   ayant porté un document CDA, **sans** CDA joint — c'est une demande de retrait.
   Synchroniser. **Attendu** : le message est ingéré et la demande de retrait est
   visible. Avant correctif : le message n'apparaît jamais, et Seq montre une
   violation de contrainte rejouée à chaque synchronisation.
3. **Doublon de patient** : provoquer deux ingestions concurrentes pour la même
   identité (lancer une synchronisation d'arrière-plan et ouvrir simultanément le
   dossier pour déclencher un enrichissement de premier plan, sur une boîte
   contenant plusieurs CDA du même patient, même OID). **Attendu** : un seul dossier
   patient, historique complet. Avant correctif : deux dossiers, historique scindé.
4. **Message patient sur un matricule connu** : sur un patient déjà créé par CDA
   (OID NIR), faire ingérer un message Mon Espace Santé du même matricule. **Attendu** :
   le courrier rejoint ce dossier, aucun second dossier `Oid = NULL` n'apparaît.
5. Vérifier qu'une opposition MSS posée sur ce patient est bien honorée en lecture.
6. Exécuter la requête d'inventaire sur une base de test antérieure au correctif →
   elle remonte bien les doublons ; sur une base propre, elle ne remonte rien.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — volets MSSanté et Mon Espace Santé (messages patients)
- **Exigences DSR honorées** : correctif de conformité — intégrité et complétude du
  dossier patient, fiabilité de la réception
- **INS** : **directement concerné** — l'unicité du dossier patient par identité
  (matricule, domaine d'attribution) est un invariant d'identito-vigilance ; sa
  violation scinde ou mélange l'historique (l'absence d'INS est traitée par task-176,
  le domaine d'attribution par task-183)
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : documents CDA r2 ingérés ; parsing et validation Schematron
  via `interop-cda` inchangés
- **Tracé PGSSI-S** : journaliser l'échec d'ingestion d'un message (aujourd'hui
  rejoué silencieusement à chaque cycle) et la détection d'un doublon d'identité —
  évènements techniques, sans donnée de santé
- **Consentement patient** : la demande de retrait de document émanant du patient
  est précisément le flux bloqué par le défaut n° 1 — un droit patient inopérant
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : **à mettre à jour** — inexactitude des données
  (art. 5.1.d : historique patient scindé) et ineffectivité d'une demande de retrait
  patient. Qualifier la portée via l'inventaire, avec le DPO.
