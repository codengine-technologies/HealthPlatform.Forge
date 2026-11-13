# todo-task-472.md — Règle 14 : chaque personne son accès, chaque acte sa trace exacte

**Repos**: api-mail
**Dependencies**: aucune
**Epic**: E025
**Priorité**: EPIC E025, issue de l'audit du 2026-11-12/13, validée par l'humain le 2026-11-13 (après ajustement).

> **Origine.** Audit en lecture seule du 2026-11-12/13 (agents « concurrence et sessions », « données, audit, IA »,
> « entrées et injections »). La connexion IMAP de fond partagée et la perte d'un lot d'audit ont été relues dans le
> code par l'orchestrateur le 2026-11-13.

## Ce qui est établi

Lecture du code au 2026-11-13 (`Api/Mail/src`) :

- **Connexion IMAP de fond partagée entre personnes.** La synchro de fond s'authentifie en XOAUTH2 avec le jeton PSC
  de la personne qui l'a lancée (`BackgroundImapService.cs:605-616`), puis confie la connexion au registre
  (`:520`). Le registre l'indexe par **adresse seule** (`Session/BackgroundImapConnectionRegistry.cs:56`), l'entrée
  ne dit pas à qui elle appartient (`:182-187`). Le cycle suivant, quel que soit celui qui le lance, la reprend en ne
  testant que son état (`BackgroundImapService.cs:377-378`, `:401-419`). Le NOOP de maintenance (`:120-123`) et chaque
  cycle la gardent vivante ; elle ne se ferme qu'après 60 min sans usage. Une révocation arrête la synchro lancée par la
  personne (`BackgroundSyncManager.StopSyncStartedByAsync`) mais ne ferme pas sa connexion. Effets : les lectures de la
  synchro de B passent par une session que l'opérateur attribue à A ; après la révocation de A, une session ouverte
  avec ses droits continue de lire la boîte. Le comportement de l'opérateur sur une session déjà ouverte n'est pas
  qualifié ; l'imputation fausse chez l'opérateur, elle, est certaine.
- **Préférences de notification d'une personne pour toute la boîte.** `NewMailNotifier.cs:84` lit les réglages de la
  personne du contexte (celle qui a lancé la synchro), puis `:110` diffuse à tous les flux de la boîte.
- **Plafond de sessions par adresse.** `Session/MailClientSessionManager.cs:407-439` compte les sessions par
  `OwnerEmail` et retire la plus ancienne d'une **autre** personne : sur une boîte d'organisation à quatre membres actifs
  (plafond 3), chacun évince l'autre à chaque requête.
- **Arrêt de synchro qui vide un contexte vivant.** `BackgroundSyncManager.cs:770-776` (`StopLocallyAsync`) appelle
  `runtime.UserContextInfo.Reset()` pendant que le travail annulé tourne encore : la trace qui suit (par exemple
  `MailDelete` d'un rejeu hors ligne) part sans personne ni boîte. `cts.Token` (`:137`) est lu hors `try` sur un jeton
  qui peut être disposé.
- **Repli de la personne sur la boîte.** `Infrastructure/Repositories/MailDb/BaseRepository.cs:162-165` replie
  l'identifiant de personne sur celui de la boîte quand `AuthenticationSubject` est vide ; dans ce cas
  `UserSettingsRepository.SaveSettingsAsync` (`:214-249`) écrit l'identité d'expéditeur de la boîte. Plausible : le
  chemin sans personne reste à démontrer par un test.
- **Lot d'audit perdu par une seule trace.** `AuditBackgroundService.cs:292-302` applique l'échec d'un lot à chacune de
  ses traces ; `:183-185` classe « poison » les SqlState 22, 23 **et 42** (`42501` droit manquant, `42703` colonne
  absente : des pannes d'environnement). Le tampon étant FIFO, le lot revient groupé ; à la 5ᵉ tentative toutes les
  traces qui voyagent avec la fautive sont perdues, de toutes les boîtes. Vecteur : `Api/Audit/AuditAttributes.cs:55`
  décode une seconde fois le dossier de la route (`INBOX%2500` → `INBOX\0`), et aucun champ texte n'est nettoyé du
  caractère NUL, que PostgreSQL refuse (`22021`).
- **Ingestion de fond imputée à une personne.** `UserContextInfo.cs:235` recopie `AuthenticationSubject` vers les
  portées de fond ; `AuditService.cs:124-125` n'en fait un acte système que si le sujet est vide ou si l'appelant pose
  `IsSystemAct`. `EnrichedMailPersistence.cs:114` (`MailReceive`) et `EmailBuildingService.cs:109`
  (`MedicalDocumentProcess`, avec INS et nom du patient) ne le posent pas : la synchro lancée par un délégataire
  produit des centaines de lignes « Cyril — MedicalDocumentProcess » pour des documents qu'il n'a jamais ouverts.
- **Traces sans objet.** `AuditAttributes.cs:51-58` ne renseigne que le dossier et l'UID de la route : `POST
  patients/resolve`, `POST patients/mails`, `POST search/patient` et `GET patients/{guid}/…` tracent « une fiche
  consultée » sans dire laquelle.
- **Recherche de patients.** `PatientRepository.cs:187-195`, `:213-215`, `:894-903` : `ILike(p.LastName, "%" + l +
  "%")` sans échappement ni `Take` ; `PatientsController.cs:110-112` et `:140-142` sont `[TraceExempt]`.
  `search?lastName=%` rend toutes les fiches (nom, naissance, INS, téléphones, adresse), sans trace. Même défaut
  d'échappement dans `ContactRepository.cs:312-316`.
- **Lecture et rétention du journal.** `AuditController.cs:44-56` ne borne la fenêtre (92 jours) que si `DateTo` est
  fourni, et journalise le filtre `Search` (souvent un nom de patient ou un RPPS).
  `AuditRetentionPolicy.cs:119-139` accepte toute valeur positive pour `HealthDataAccessDays`.

## Objective

Sur une boîte partagée, ce qui appartient à une personne ne sert qu'à elle ; le journal d'audit est complet, exact et
conservé, et chaque acte y est imputé à son auteur réel ou, sans personne, à un acte système.

Règles :

1. **Par personne.** La connexion IMAP de fond, l'application des préférences de notification (filtrées à la
   livraison, par abonné) et le plafond de sessions sont indexés par (boîte, personne). À la suspension, à la
   révocation ou à la déconnexion d'une personne, ses connexions de fond sont fermées et ses synchros arrêtées.
2. **Pas de repli de la personne sur la boîte.** Un acte sans personne est un acte système explicite ; la lecture ou
   l'écriture d'une donnée personnelle (réglages, signatures) sans personne est refusée. L'arrêt d'une synchro ne
   modifie jamais le contexte d'un travail encore vivant.
3. **Journal sans perte.**
   - Un lot refusé est rejoué par moitiés, jusqu'à isoler la trace fautive, rangée en **quarantaine** (conservée,
     comptée), jamais jetée.
   - Une erreur de classe 42 est transitoire (rejouée sans limite).
   - Le caractère NUL est retiré des champs texte d'une trace ; le dossier de la route n'est plus décodé deux fois.
4. **Imputation de l'ingestion.** `MailReceive` et `MedicalDocumentProcess` émis par une tâche de fond sont des actes
   système. Le rejeu d'une action de la personne et l'archivage de son propre envoi restent à son nom.
5. **Objet de la trace.** La consultation d'une fiche (`PatientRecordViewed`) porte le patient (INS et nom). La
   recherche de patients échappe ses jokers (`%`, `_`, `\`), exige 2 caractères au moins, plafonne ses résultats et
   est tracée (critères réduits à leur nature, jamais en clair dans les journaux d'exploitation). Même échappement pour
   la recherche de contacts.
6. **Lecture et rétention du journal.** Fenêtre bornée à 92 jours, `DateTo` fourni ou non ; le filtre `Search` n'est
   journalisé que par sa longueur ; une rétention `HealthDataAccess` inférieure à 3 653 jours est refusée (repli sur
   3 653, erreur journalisée).

### Hors périmètre (décisions humaines du 2026-11-13)

- **Historique de recherche et conversations IA** : ils restent rangés **par boîte**, partagés entre les personnes de
  la boîte. Décision de l'humain, en connaissance du constat de l'audit (un délégataire lit et efface ceux du
  titulaire).
- **Lecture du contenu d'un message** : elle reste tracée au passage à « lu » (`MailRead`), pas à chaque ouverture.
  Décision de l'humain, en connaissance du constat (un délégataire qui ouvre un message déjà lu ne laisse pas de
  trace).
- L'exemption du titulaire, hors ligne et en ligne, décidée par task-403.

## Definition of Done

- [ ] Tests unitaires : clé du registre de fond (boîte, personne) ; règle de quarantaine (dichotomie d'un lot,
      classes SQL) ; nettoyage du NUL ; acte système des traces d'ingestion ; échappement des jokers ; bornes de la
      lecture du journal ; plancher de rétention.
- [ ] **Deux personnes sur la même boîte** (règle 14), test d'intégration de bout en bout : A (délégataire) puis B
      (titulaire) lancent la synchro ; deux connexions de fond distinctes sont ouvertes, chacune authentifiée avec le
      jeton de sa personne ; la délégation de A est révoquée, sa connexion est fermée et celle de B continue ; A coupe
      ses notifications « nouveau message », B reçoit toujours les siennes ; les traces portent chacune leur auteur
      réel, l'ingestion est en acte système. Vu rouge.
- [ ] **Test d'intégration du journal** : un lot de dix traces dont une porte un NUL ; neuf sont relues par
      `GET audit`, la dixième est en quarantaine (compteur). Une erreur de classe 42 simulée est rejouée sans perte.
      Vu rouge.
- [ ] **Test d'intégration de l'objet** : `GET patients/{id}` produit `PatientRecordViewed` portant l'INS et le nom du
      patient, relus par `GET audit`. Vu rouge.
- [ ] **Test d'intégration de la recherche** : `GET patients/search?lastName=%` est traité littéralement (aucune fiche
      dont le nom ne contient pas `%`) ; une recherche d'un caractère rend 400 ; le nombre de résultats est plafonné ;
      la recherche produit une trace. Vu rouge.
- [ ] **Test d'intégration de la lecture du journal** : `GET audit?DateFrom=2016-01-01` sans `DateTo` couvre au plus
      92 jours. Test de configuration : `HealthDataAccessDays = 365` retombe à 3 653, avec une erreur journalisée.
- [ ] **Test du repli** : une lecture de réglages sans personne est refusée ; aucune écriture n'atteint l'identité
      d'expéditeur de la boîte.
- [ ] Prévention (règle d'or) : `conventions/csharp.md` — « toute clé de pool, de cache ou de plafond d'une ressource
      ouverte par une personne contient la personne » ; « une tâche de fond trace en acte système » ; « l'échec d'un
      lot ne s'impute jamais à toutes ses traces ».
- [ ] Aucune donnée de santé dans les journaux d'exploitation (le critère de recherche n'y figure pas).
- [ ] Build et tests verts : `HealthPlatform.Api.Mail.sln`. Parcours e2e existants rejoués verts par `/e2e`.

## Manual Test Plan

1. Lancer le backend (`cd Api/Mail/src/AppHost && dotnet run`) et weda2 (`cd Client/Angular/front && npm start`).
2. Deux comptes rattachés à la même boîte de formation : le titulaire et un délégataire. Lancer la synchro avec le
   délégataire, puis avec le titulaire ; dans Seq, deux connexions de fond distinctes.
3. Retirer la délégation : la connexion de fond du délégataire se ferme (Seq), la synchro du titulaire continue.
4. Délégataire : couper les notifications « nouveau message ». Injecter un message : le titulaire est notifié.
5. Journal d'audit (web) : l'ingestion du message apparaît en acte système ; ouvrir une fiche patient produit une
   ligne qui nomme le patient.
6. Rechercher un patient avec `%` : aucun résultat inattendu ; la recherche apparaît au journal.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — socle de traçabilité et de boîte partagée (règle 14)
- **Vague Ségur** : hors Ségur — conformité PGSSI-S
- **Exigences DSR honorées** : non applicable — exigences PGSSI-S (imputabilité, intégrité et exhaustivité des traces,
  durée de conservation)
- **INS** : portée par la trace de consultation d'une fiche, comme pour le rattachement aujourd'hui ; jamais dans les
  journaux d'exploitation ; la recherche par traits ne rend plus la base entière
- **Authentification PS** : inchangée — PSC (e-CPS), eIDAS substantiel ; chaque connexion de fond porte le jeton de sa
  personne
- **Habilitations** : verdict de l'opérateur par personne (règle 14) ; fermeture des connexions de la personne révoquée
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : ingestion en acte système ; consultation de fiche avec patient ; recherche de patients tracée ;
  aucune trace perdue (quarantaine) ; `HealthDataAccess`, 3 653 jours garantis
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — base de la boîte et journal commun
- **AIPD / impact RGPD** : inchangée — renforcement de la traçabilité existante
