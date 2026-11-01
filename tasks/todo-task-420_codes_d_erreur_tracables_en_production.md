# todo-task-420.md — Chaque erreur d'api-mail porte un code catalogué, retrouvable en production sans coût sur le chemin nominal

**Repos**: api-mail
**Dependencies**: — (aucune)
**Epic**: E021
**EpicTitle**: Analyse des pannes en production
**Priorité**: **2** — en production, une erreur se cherche aujourd'hui au texte libre : son code n'est pas dans le journal, un 500 imprévu n'en a aucun, et les tâches de fond n'en ont jamais.

> **Origine.** Demande humaine du 2026-11-01 : faciliter l'analyse des pannes en production **sans dégrader
> les performances**. Le catalogue d'erreurs du proxy PSC (`psc-auth-proxy`, `src/Api/Errors/ErrorCatalog.cs`)
> a servi d'exemple, pas de modèle à recopier : ses codes numériques (`PROXY-PSC-3010`) sont opaques sans la
> table. Ici, les noms lisibles déjà lus par les clients sont conservés.
>
> **Décision humaine (2026-11-01)** : il n'est **pas nécessaire de journaliser en console**. Le sink Console
> de Serilog est retiré ; les journaux partent vers Seq et OTLP.

## Ce qui est établi

- **Les codes existent mais sont dispersés** : `MailboxErrorCodes` (8 codes, dans `Dtos/MailboxDto.cs`),
  `PscSessionErrorCodes` (3), `MailNotFoundCodes`, `MailUnavailabilityCodes`, des constantes portées par les
  exceptions (`MAIL_DELIVERY_UNCERTAIN`, `IHE_XDM_*`, `MAIL_FROM_NOT_MAILBOX`, `DELEGATE_IDENTITY_UNAVAILABLE`),
  et des chaînes en dur dans le flux IA (`CONVERSATION_NOT_FOUND`, `GENERATION_ERROR`). Il n'en existe aucun
  inventaire. Ces noms sont le contrat que lisent weda2, le mobile et Blazor.
- **Le statut et le code sont choisis à deux endroits** : `GlobalExceptionHandler.Map` choisit le statut selon
  le type d'exception, et le `code` est ajouté à part via `IErrorCoded`.
- **Le code n'est pas dans le journal** : `GlobalExceptionHandler.LogException` écrit « Handled {Status} -
  {Method} {Path} » sans le code. Dans Seq, on ne peut pas filtrer une erreur par son code.
- **Un 500 imprévu n'a aucun code** : la branche `_ =>` de `Map` rend un problem+json sans `code`.
- **Les tâches de fond n'ont pas de code** : synchronisation, enrichissement, consommateurs du bus, envois
  différés journalisent en texte libre (9 `BackgroundService`, 3 consommateurs).
- **La cause amont se perd** : `PscTokenProvider.ReadAsync` ne lit que le statut HTTP du proxy (401, 403, sinon
  « indisponible »), alors que le proxy rend un `code` (`PROXY-PSC-2002`, `PROXY-PSC-4001`, `PROXY-KC-4031`…).
- **Les compteurs ont déjà un modèle** : `Application/Telemetry/AuditMetrics.cs` (Meter statique, compteurs
  `TracesDropped`, `TracesEmitted`…).
- **La version est connue** : `BuildInfoProvider` (task-384) lit `AssemblyInformationalVersionAttribute`.
- **Le sink Console est synchrone** : `Api/Program.cs`, `.WriteTo.Console(outputTemplate: …)`, dans tous les
  environnements. Seq (`SEQ_URL`) et OTLP (`OTEL_EXPORTER_OTLP_ENDPOINT`) sont déjà branchés.
- Le `traceId` est déjà posé sur chaque problem+json (`ProblemDetailsSetup`).

## Objective

Qu'une erreur vue en production — par le médecin, le support ou une alerte — se retrouve **par son code** dans
les journaux, les traces et les compteurs, avec sa catégorie, la version d'api-mail et sa cause amont, et
qu'une fiche dise quoi en penser et quoi faire. **Sans un cycle de plus sur une requête qui réussit.**

### Périmètre

1. **Catalogue unique** des codes d'erreur d'api-mail, en table statique : code (nom actuel conservé), statut
   HTTP, catégorie (session, messagerie, document, annuaire, IA, infrastructure, validation), sévérité, cause
   probable, impact pour le médecin, première action. Tous les codes existants y sont repris **sans
   renommage**. Les exceptions typées portent leur entrée de catalogue ; `GlobalExceptionHandler.Map` y lit le
   statut (règle 12 conservée : mapping par type, jamais par message).
2. **Un code pour toute erreur**, imprévue comprise : `UNEXPECTED_ERROR` pour la branche par défaut,
   `DATABASE_UNAVAILABLE` pour une base injoignable, `REQUEST_CANCELLED` pour le 499, et un code pour chaque
   mapping de `Map` qui n'en a pas aujourd'hui (validation, introuvable, conflit, indisponible, non autorisé…).
3. **Le code dans le journal d'erreur**, au point d'écriture unique (`LogException`) : propriétés structurées
   `ErrorCode`, `ErrorCategory`, `AppVersion`, et `UpstreamCode` quand elle est connue. Message en
   `[LoggerMessage]`.
4. **Les tâches de fond** : chaque `catch` qui journalise une erreur dans un `BackgroundService`, un
   consommateur du bus ou l'envoi différé porte le même `ErrorCode` (et `ErrorCategory`) que le catalogue.
5. **La cause amont, lue seulement en échec** : `PscTokenProvider` lit le `code` du corps du proxy **dans ses
   branches d'erreur uniquement** et le garde en `UpstreamCode`. Le verdict rendu aux clients reste celui
   d'api-mail (`PSC_SESSION_EXPIRED`, `PSC_PROXY_UNAVAILABLE`…) : **aucun `PROXY-…` n'est renvoyé aux clients**.
6. **Un compteur `mss_errors_total`** sur le modèle d'`AuditMetrics`, incrémenté **sur erreur seulement**,
   labels bornés : `code`, `category`, `status`, `route` (modèle de route, jamais le chemin brut).
   **Interdits en label** : boîte, personne, RPPS, identifiant de message ou de patient.
7. **L'attribut `error.type` = code** posé sur l'activité courante (span existante), et son statut mis en
   erreur — **seulement en cas d'erreur**, sans créer de span.
8. **Fiches par code générées** depuis le catalogue (un fichier dans `Docs/`, produit par un test ou un outil
   du build, pas à l'exécution) : code, statut, catégorie, cause probable, impact, première action, requête Seq
   type (`ErrorCode = '…'`).
9. **Retrait du sink Console** de Serilog dans tous les environnements (décision humaine). Les journaux partent
   vers Seq et OTLP comme aujourd'hui.

### Hors périmètre

- Événement « large » par requête réussie, nouvelles spans, échantillonnage : ils touchent le chemin nominal.
- Affichage du code et de la référence dans les clients : **task-421**.
- Reprise des codes du proxy pour affiner les verdicts d'api-mail : seule leur conservation en `UpstreamCode`
  fait partie de cette US.
- Alertes et tableaux de bord sur le compteur : configuration de l'outil de supervision, hors dépôt.

### Points d'attention pour /develop

- **Renommer un code existant casse les trois clients** : interdit. Le test de catalogue le verrouille.
- **Le catalogue ne pousse pas à lever des exceptions** pour des cas nominaux : les `Result` restent la voie
  normale.
- **Sans `SEQ_URL` ni `OTEL_EXPORTER_OTLP_ENDPOINT`**, l'API n'émet plus aucun journal une fois la console
  retirée. Le dire dans la fiche d'exploitation et le README d'api-mail ; vérifier que chaque environnement
  (dont le banc et l'AppHost, dont le tableau de bord lit l'OTLP) configure au moins l'un des deux.
- `MailboxErrorCodes` vit dans `dtos-mss` : le catalogue le **référence**, il ne le déplace pas (aucun
  changement de contrat, aucune publication NuGet).

## Definition of Done

- [ ] Build et tests api-mail verts
- [ ] Catalogue : tous les codes existants repris sans renommage ; test unitaire qui échoue sur un code en
      double, sur un code émis absent du catalogue (réflexion sur `IErrorCoded` et les constantes de codes), et
      sur un code existant renommé (liste figée des codes publiés)
- [ ] Tests unitaires de `GlobalExceptionHandler.Map` : chaque type d'exception rend le statut **et** le code de
      son entrée de catalogue ; la branche par défaut rend `UNEXPECTED_ERROR`
- [ ] Test d'intégration de bout en bout pour une route qui lève une exception imprévue : la réponse réelle est
      un 500 problem+json dont `code` vaut `UNEXPECTED_ERROR`, avec un `traceId` ; vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout pour un refus métier existant (403 `MAILBOX_PSC_MISMATCH`) : code et
      statut **inchangés** dans la réponse réelle (non-régression du contrat)
- [ ] Test : l'erreur journalisée par `LogException` porte `ErrorCode`, `ErrorCategory`, `AppVersion` en
      propriétés structurées (sink de test Serilog) ; vu rouge
- [ ] Test : un échec dans une tâche de fond (au moins la synchronisation et un consommateur du bus) journalise
      son `ErrorCode` ; vu rouge
- [ ] Test : `PscTokenProvider` garde le `code` du proxy en `UpstreamCode` sur un refus, et **ne lit pas** le
      corps sur un 200 ; le verdict rendu aux clients est inchangé
- [ ] Test : `mss_errors_total` s'incrémente sur erreur avec les labels `code`, `category`, `status`, `route`, et
      **ne s'incrémente pas** sur une réponse réussie ; aucun label hors de cette liste
- [ ] Test : `error.type` posé sur l'activité courante en cas d'erreur, absent sinon
- [ ] Fiches par code générées dans `Docs/` et à jour (le test échoue si une fiche manque ou diffère du catalogue)
- [ ] Sink Console retiré de `Program.cs` ; README d'api-mail : journaux par Seq et OTLP uniquement, au moins
      l'un des deux requis
- [ ] Aucune donnée de santé dans les propriétés ajoutées (INS, NIR, contenu de message, adresse en clair,
      RPPS) : test sur le gabarit et les propriétés
- [ ] **A/B de contrôle au banc** (même tir, même lignée, même base) : p95 et CPU par requête du chemin
      nominal dans le bruit mesuré (~1,4 %) ; résultat consigné dans le `## Develop log`

## Manual Test Plan

1. Lancer api-mail par l'AppHost avec Seq (`SEQ_URL` défini).
2. Provoquer un refus métier connu (carte d'un autre praticien sur la boîte → 403 `MAILBOX_PSC_MISMATCH`).
   Dans Seq, filtrer `ErrorCode = 'MAILBOX_PSC_MISMATCH'` : l'erreur est trouvée, avec sa catégorie et la version.
3. Couper la base (ou PgBouncer) et appeler une route : réponse 503 `DATABASE_UNAVAILABLE` ; Seq la retrouve par
   son code.
4. Arrêter le proxy PSC, ouvrir la boîte : le journal porte le code d'api-mail et, quand le proxy a répondu,
   son `UpstreamCode`.
5. Ouvrir la fiche du code dans `Docs/` : cause probable, impact, première action, requête Seq.
6. Vérifier que la console de l'API n'affiche plus de journaux applicatifs, et que Seq les reçoit toujours.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — outillage d'exploitation de la plateforme
- **Vague Ségur** : hors Ségur — exploitabilité
- **Exigences DSR honorées** : non applicable — aucune fonctionnalité métier ; soutient la disponibilité et le
  diagnostic du service MSSanté
- **INS** : non applicable — aucune donnée patient manipulée ; l'INS reste interdite dans les journaux
- **Authentification PS** : inchangée (PSC / e-CPS) ; seuls les codes de refus sont mieux journalisés
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : le **journal d'audit PGSSI-S est inchangé** (actes imputés, 3 653 jours, règle 14). Cette US
  ne touche que les journaux **techniques** : code d'erreur, catégorie, version, cause amont, sans donnée de
  santé
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui pour la plateforme ; les journaux techniques ne portent aucune donnée de santé
  (pseudonymisation et masquage existants, task-184)
- **AIPD / impact RGPD** : inchangé — aucune donnée personnelle nouvelle ; la boîte n'apparaît jamais en label
  de métrique
