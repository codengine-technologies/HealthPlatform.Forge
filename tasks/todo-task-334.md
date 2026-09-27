# todo-task-334.md — La synchronisation de fond traite un mail exactement comme l'ouverture à l'écran : mêmes documents, même audit, même nettoyage

**Repos**: api-mail
**Dependencies**: task-333 (la garde d'échec technique et le verrou d'enrichissement, que le constructeur unique réutilise)
**Epic**: E009
**Single frontend**: true
**Priorité**: **2** — un mail ingéré par la synchro de fond perd définitivement son accusé de lecture, son rattachement de message patient, ses traces d'audit et ses notifications ; ses archives CDA restent sur disque ; ses actions rejouées sont tracées hors du tenant du praticien.

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, **AUD-11** — contre-vérifié —, **AUD-12**, **AUD-13**,
> **AUD-14**, **AUD-15**, **AUD-65**). Cause commune : la synchro de fond a **son propre** constructeur
> de mail et sa propre copie d'identité, qui ont manqué les correctifs du chemin de premier plan.

## Ce qui est établi (develop @ `14d58398`)

1. **Archives jamais supprimées (AUD-11)** — `BackgroundImapService.cs:223-297` : la liste `fetched` de
   `FetchedBackgroundMail` (`IDisposable`, propriétaire de ses archives) n'est jamais libérée (ni `using`,
   ni `finally`) ; `BackgroundEnrichmentProcessor` ne libère rien non plus. CDA et PDF en clair restent
   dans `%TEMP%/mss-ihe-xdm/` jusqu'au redémarrage. Le premier plan a été corrigé en task-228
   (`ImapService.cs:1699-1717`, `DisposeAll`).
2. **Identité incomplète (AUD-12)** — `BackgroundSyncManager.cs:147-158`, `BackgroundEnrichmentProcessor.cs:178-192`,
   `AddNewMailConsumer.cs:161-168`, `Create*ContactConsumer` : copie champ par champ (interdite par task-234)
   au lieu de `CopyIdentityTo`, sans `TenantId` ni `RegisteredDatabaseName`. Les actions rejouées en début
   de synchro (acquittement biologique avec `PatientIns`, drapeaux, envoi) sont tracées sous `Guid.Empty`
   → **invisibles** dans l'écran d'audit du praticien (RLS) — le défaut de task-300 × 312.
3. **Constructeur divergent (AUD-13)** — `BackgroundEnrichmentProcessor.cs:234-292`, `BackgroundImapService.cs:230-233` :
   en-têtes non récupérés (`ReadReceiptTo` vide → accusé de lecture jamais détecté) ; `IsFromPatient` /
   `PatientInsMatricule` non posés (messages Mon Espace Santé sans document COURRIER ni lien patient) ;
   aucune trace `MailReceive` ni `MedicalDocumentProcess` ; aucune notification (enrichi, remplacé, suppression).
4. **HTML non assaini (AUD-14)** — `BackgroundEnrichmentProcessor.cs:258-266` stocke le HTML brut
   (le premier plan assainit, `EmailBuildingService.cs:69`) ; le mode hors ligne
   (`OfflineMailDataProvider.cs:120-131`) le sert tel quel.
5. **Candidats (AUD-15)** — `BackgroundSyncService.cs:384-403` : `missingUids = IMAP − GetExistingUidsAsync`
   exclut les lignes « en-têtes seuls » laissées par le listing → un mail dont l'enrichissement de premier
   plan a échoué n'est jamais repris par la synchro.
6. **Mineurs (AUD-65)** — notification « nouveau mail » jamais émise (`BackgroundImapService.cs:205`,
   `isIncrementalSync` toujours faux) ; synchro « réussie » sur des lots injoignables
   (`BackgroundSyncService.cs:503-504` ignore `EnrichmentOutcome`) ; `ex.Message` brut envoyé au client
   par SSE (`:134`) ; vecteur `null` écrasant un index valide à la relivraison (`MailRepository.cs:2872`) ;
   double politique de retry MassTransit (jusqu'à ~16 appels LLM par message).

## Objective

Qu'un mail soit **construit, persisté, audité, notifié et nettoyé par une seule séquence**, qu'il arrive
par l'ouverture à l'écran ou par la synchronisation de fond ; que le travail de fond s'exécute sous
l'identité complète du praticien ; et que la synchronisation reprenne tout mail non encore analysé.

### Périmètre

1. **Constructeur unique** : la synchro de fond utilise `IEmailBuildingService` et la même séquence
   post-persistance que le premier plan (audit, notifications, rafraîchissements, messages patient) ;
   le FETCH récupère les en-têtes nécessaires.
2. **Nettoyage** : les archives extraites sont libérées sur **tous** les chemins (succès, erreur, annulation).
3. **Identité** : `CopyIdentityTo` partout où un travail quitte la requête (gestionnaire de synchro,
   processeur, trois consommateurs) ; plus aucune copie champ par champ.
4. **Candidats** : `IMAP − GetEnrichedUidsAsync` ; une ligne « en-têtes seuls » est promue.
5. **Mineurs** : notification « nouveau mail » réellement émise ; progression fidèle à `EnrichmentOutcome` ;
   message d'erreur SSE générique ; pas d'écrasement d'un vecteur valide par `null` ; une seule politique de retry.

### Hors périmètre

- La garde d'échec technique elle-même (task-333, prérequis).
- Les notifications entre réplicas (task-336).

## Definition of Done

- [ ] Build passes (0 errors) — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` ; Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] **Tests rouges d'abord** (log des runs rouges dans le task file), rouges sur le code actuel :
  - [ ] synchro de fond d'un mail porteur d'`IHE_XDM.ZIP` → après le lot, **aucune** archive ne reste dans le répertoire de travail (aussi en erreur et en annulation)
  - [ ] action rejouée en début de synchro → trace d'audit sous le **tenant du praticien**
  - [ ] mail entrant avec `Disposition-Notification-To` ingéré en fond → `ReadReceiptTo` renseigné
  - [ ] message patient Mon Espace Santé ingéré en fond → document COURRIER et lien patient créés
  - [ ] mail HTML contenant `<script>` ingéré en fond → stocké assaini
  - [ ] ligne « en-têtes seuls » existante → reprise et enrichie par la synchro
- [ ] Test : traces `MailReceive` et `MedicalDocumentProcess` émises en fond comme au premier plan
- [ ] Test d'architecture : aucune copie champ par champ de `UserContextInfo` hors de `CopyIdentityTo` / `CopyTo`
- [ ] Tests des mineurs : notification « nouveau mail », progression sur lot injoignable, message SSE générique, vecteur non écrasé
- [ ] Non-régression : tests existants du premier plan (task-228, task-293) et de la synchro verts
- [ ] Aucune INS, contenu CDA ni corps de mail dans les logs

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` (profil banc, seed de mails `IHE_XDM.ZIP` via `loadtest-skill`).
2. Lancer une synchro complète (`POST /api/v1/sync/start`) sans ouvrir de mail.
3. **Archives** : pendant et après la synchro, le répertoire `mss-ihe-xdm` du poste se vide. Avant : il grossit jusqu'au redémarrage.
4. **Audit** : écran d'audit du praticien → les traces de réception et de traitement des documents des mails synchronisés sont visibles.
5. **Accusé de lecture** : un mail seedé demandant un accusé → à l'ouverture, la proposition d'accusé apparaît.
6. **Reprise** : afficher la liste (en-têtes seuls), couper l'IMAP pendant l'ouverture d'un mail (503), relancer une synchro → le mail est enrichi par la synchro.
7. Pendant la synchro, la progression reflète les lots injoignables (Toxiproxy coupé) au lieu d'afficher 100 %.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville, biologie
- **Vague Ségur** : V2
- **Exigences DSR honorées** : intégration des documents MSSanté reçus ; traçabilité de la réception ; messages patient Mon Espace Santé rattachés
- **INS** : l'INS des messages patient est lue et rattachée comme au premier plan (même règles, task-183) ; aucune INS en log
- **Authentification PS** : PSC / e-CPS inchangée ; le travail de fond hérite de l'identité complète du praticien
- **Habilitations** : inchangées — travail limité à la boîte et au tenant du praticien
- **Interop CI-SIS** : IHE-XDM / CDA r2 via `interop-cda` (chemin existant)
- **Tracé PGSSI-S** : `MailReceive`, `MedicalDocumentProcess` et actions rejouées tracés sous le bon tenant (rétention inchangée)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — archives CDA temporaires purgées ; environnement inchangé
- **AIPD / impact RGPD** : inchangé — réduit la rétention non maîtrisée de documents de santé sur disque
