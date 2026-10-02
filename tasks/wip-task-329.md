# todo-task-329.md — Un message envoyé part complet et laisse une trace, quel que soit le chemin : brouillon, transfert, envoi hors ligne ou « annule et remplace »

**Repos**: api-mail, dtos-mss, client-blazor, client-mobile, client-angular
**Dependencies**: task-330 (le rejeu hors ligne fiable, sur lequel l'envoi hors ligne unifié s'appuie)
**Epic**: E009
**Single frontend**: false
**Priorité**: **1** — des **pièces jointes médicales partent absentes** avec un « envoyé » affiché, et des envois n'apparaissent jamais dans « Envoyés ».

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, **AUD-06** — contre-vérifié —, **AUD-07**, **AUD-20**,
> **AUD-63**, **AUD-48**). Cause commune : **plusieurs chemins d'envoi qui ont divergé** — `sendmail`
> a reçu chaque correctif (archivage, garde d'opposition, file hors ligne, annule-et-remplace), les
> chemins brouillon, transfert et rejeu hors ligne non.

## Ce qui est établi (develop @ `14d58398`)

1. **Brouillon (AUD-06)** — `DraftService.cs:319-341` (`BuildMailDto`) ne copie ni les pièces jointes,
   ni `RequestReadReceipt`, ni `OppositionAcknowledged`, ni le mode annule-et-remplace ;
   `SaveDraftDto` (dtos-mss) ne porte que `AttachmentIds`, que `BuildMailDto` ne lit même pas.
   L'autosave (30 s, Blazor `NewMailComponent.razor:390`) crée un brouillon dans tous les cas, puis
   « Envoyer » passe par `POST drafts/{id}/send` (`:1060-1065`) — **chemin majoritaire**. Patient
   sous opposition acquittée : 409 systématique, et l'exception laisse le brouillon en `Sending`
   (`DraftService.cs:257-262`). Hors ligne : `DraftController` rend 502 au lieu de mettre en file.
2. **Transfert mobile (AUD-07)** — `SmtpService.cs:306-312` filtre `a?.Content != null` : les pièces
   reprises « par référence » (`carriedOver: true`, `mail-compose.component.ts:305-316, 1173-1180`)
   sont **écartées en silence** ; aucun chemin d'envoi ne résout `AttachmentDto.Guid`. Les en-têtes
   X-MSS-CODECDA / X-MSS-INS disparaissent avec elles. Le contrôle de taille (`:396`) les compte pourtant.
3. **Archivage (AUD-20)** — seuls `MailController.cs:1383` et `:1510` appellent
   `sentArchiveDispatcher.Dispatch` ; `DraftService.cs:261-302` et `PendingActionService.cs:367-390`
   non ; `SmtpService` ne fait pas d'APPEND.
4. **Annule-et-remplace hors ligne (AUD-63)** — `MailController.cs:1440-1455` le met en file comme un
   envoi simple ; `ProcessSendMailAsync` n'appelle jamais `MarkAsCancelledAsync` ni ne force
   `InReplyTo`/`References` : l'original reste affiché valide (AMBU.MSS/va1.02).
5. **Verrou d'envoi de brouillon (AUD-48)** — TTL 30 s (`DraftService.cs:29`) plus court qu'un envoi
   (attente du verrou SMTP jusqu'à 120 s) et libéré sans jeton (`DraftCacheRepository.cs:224, 241`) :
   double envoi possible.
6. **Brouillon côté Angular** (ajouté le 2026-09-30, vérifié sur `feature/nova-rewriting-mss`) —
   même défaut que le point 1, côté `client-angular`
   (`Client/Angular/front/libs/mss/src/features/mail/components/mail-compose/mail-compose.component.ts`) :
   - l'autosave (30 s, `:1586-1597`) crée un brouillon dès qu'il y a un objet, un corps ou un
     destinataire ; ensuite, `dispatchSend` (`:841-855`) passe par `executeSendDraft` → `sendDraft`
     (`:985-1000`), et plus par `sendMailDirect` ;
   - `buildSaveDraftDto` (`:1524-1537`) ne transmet ni pièce jointe (`attachmentIds` jamais rempli),
     ni `requestReadReceipt`, ni `oppositionAcknowledged`, ni `blockPatientReply` ; le modèle TS
     `SaveDraftDto` (`libs/mss/src/core/models/draft.model.ts:11-23`) n'a même pas ces trois champs ;
   - la route `cancel-and-replace` n'est appelée que depuis `sendMailDirect` (`:1141-1147`) : un
     « annuler et remplacer » rédigé plus de 30 s part comme un envoi simple, et l'original reste valide ;
   - `loadDraft` ne restaure pas les pièces jointes.

   **Conséquence** : sur l'Angular, tout message rédigé plus de 30 s part amputé, avec « envoyé »
   affiché. Cela touche aussi le transfert, qui reprend désormais l'`IHE_XDM.ZIP` d'origine (correctif
   hors chaîne du 2026-09-30). Déjà noté sans suite en task-154 (`archived-task-154.md:134` : « chemin
   sendDraft (SaveDraftDto) hors garde »).

## Objective

Qu'**un seul chemin** décide de ce qui part et de ce qui reste : tout envoi — direct, depuis un
brouillon, transfert, rejeu hors ligne, annule-et-remplace — part avec ses pièces jointes (ou est
refusé explicitement), respecte la garde d'opposition et l'accusé de lecture demandé, est archivé dans
« Envoyés », et ne part jamais deux fois.

### Périmètre

1. **Chemin d'envoi unique côté serveur** : `SendDraftAsync` et le rejeu hors ligne convergent vers
   la même séquence que `sendmail` (validation, garde d'opposition, construction du message,
   SMTP, archivage « Envoyés », annule-et-remplace). L'archivage est déclenché **par ce point commun**,
   plus par le contrôleur.
2. **Pièces jointes par référence** : résolues côté serveur (base ou IMAP) à partir de leur identifiant ;
   si une pièce ne peut pas être résolue, l'envoi est **refusé en 400** avec un message clair — jamais
   écarté en silence.
3. **Contrat brouillon** (`dtos-mss`) : `SaveDraftDto` porte `RequestReadReceipt`,
   `OppositionAcknowledged` et les informations d'annule-et-remplace ; publication NuGet et bump des
   consommateurs .NET.
4. **Brouillon en `Sending`** : toute exception remet le brouillon en `Editing`.
5. **Hors ligne** : l'envoi d'un brouillon hors ligne est mis en file comme `sendmail` ; un
   annule-et-remplace hors ligne est mis en file avec son original et rejoué comme tel.
6. **Verrou d'envoi** : durée au-delà du délai maximal d'envoi (ou renouvelée), libération conditionnée à un jeton.
7. **Clients** : Blazor, mobile et Angular transmettent les pièces jointes du brouillon (référence
   résolvable) et les nouveaux champs ; aucune régression de l'autosave.
8. **Angular** (point 6 ci-dessus) :
   - le modèle TS `SaveDraftDto` suit le contrat `dtos-mss` ;
   - `buildSaveDraftDto` transmet les pièces jointes (par la référence du point 2, ou par leur
     contenu si le contrat le prévoit), `requestReadReceipt`, `oppositionAcknowledged`,
     `blockPatientReply` et les informations d'annule-et-remplace ;
   - un compose ouvert en annule-et-remplace n'est jamais envoyé comme un brouillon simple ;
   - `loadDraft` restaure les pièces jointes.

   Le client est **code-only** : la forge écrit le code sur la branche en cours dans
   `Client/Angular/`, l'humain gère le commit, le push et la PR TFS.

### Hors périmètre

- La fiabilité du rejeu hors ligne lui-même (task-330, prérequis).
- Le format des accusés de lecture (task-340).

## Definition of Done

- [ ] Build passes (0 errors) sur les 5 repos ; Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] **Tests rouges d'abord** (log des runs rouges dans le task file), chacun rouge sur le code actuel :
  - [ ] brouillon avec une pièce jointe PDF envoyé par `drafts/{id}/send` → le message SMTP émis **contient** la pièce
  - [ ] transfert d'un mail avec pièce reprise par référence → la pièce est présente dans le message émis
  - [ ] pièce par référence **introuvable** → 400 `ProblemDetails`, aucun envoi
  - [ ] envoi par brouillon → un APPEND « Envoyés » est déclenché
  - [ ] envoi hors ligne rejoué → un APPEND « Envoyés » est déclenché
  - [ ] brouillon vers un patient sous opposition **acquittée** → envoyé ; non acquittée → 409 et brouillon revenu en `Editing`
  - [ ] annule-et-remplace hors ligne rejoué → l'original est marqué annulé, `In-Reply-To`/`References` posés
  - [ ] deux envois concurrents du même brouillon au-delà de 30 s → **un seul** message émis
- [ ] Test d'intégration endpoint (règle 1b) : `POST drafts/{id}/send` de bout en bout (DI, GreenMail) — message relu dans le puits **avec** sa pièce jointe
- [ ] `dtos-mss` publié via la CI, consommateurs .NET bumpés
- [ ] Composants Blazor et mobile : tests de composant sur l'envoi d'un brouillon à pièce jointe et à accusé de lecture
- [ ] Compose Angular : tests de composant, chacun rouge sur le code actuel :
  - [ ] brouillon à pièce jointe → le `SaveDraftDto` envoyé la porte
  - [ ] brouillon à accusé de lecture, à opposition acquittée, à blocage de réponse patient → les trois champs sont transmis
  - [ ] annule-et-remplace après autosave → la route `cancel-and-replace` est appelée
  - [ ] brouillon rechargé → ses pièces jointes sont restaurées
- [ ] Trou du filet : scénario **E2E-DRAFT-002** (v1, `mobile: requis`, `angular: requis`) ajouté dans
  `Api/Mail/e2e/scenarios.yml` — « un message à pièce jointe, envoyé après l'enregistrement
  automatique du brouillon, arrive avec sa pièce jointe ». Implémenté dans les deux clients, prouvé
  rouge sur le bug non corrigé, ligne ajoutée dans `conventions/e2e.md`
- [ ] `data-testid` sur tout élément interactif ajouté ; libellés FR (mobile) / Localizer (Blazor)
- [ ] Aucune donnée de santé ni contenu de pièce jointe dans les logs

## Manual Test Plan

1. Backend : `cd Api/Mail && dotnet run --project src/AppHost` ; Blazor : `cd Client/Blazor && dotnet run --project <projet Shell>` ; mobile : `cd Client/Mobile && npm start` ; Angular : `cd Client/Angular/front && npm start`.
2. **Brouillon + PDF (Blazor)** : nouveau message, joindre un PDF de test anonymisé, attendre 40 s (autosave), Envoyer → le destinataire de test reçoit le PDF ; le message est dans « Envoyés ». Avant : sans pièce, absent d'« Envoyés ».
3. **Transfert mobile** : transférer un mail porteur d'un `IHE_XDM.ZIP` de test → le destinataire reçoit l'archive et les en-têtes X-MSS. Avant : sans pièce.
4. **Opposition** : destinataire patient de test sous opposition, confirmer « Continuer » après autosave → envoyé. Avant : 409 et brouillon bloqué.
5. **Hors ligne** : couper l'accès PSC (mode hors ligne), envoyer un brouillon → message mis en file (202) ; rétablir → envoyé et archivé.
6. **Annule et remplace hors ligne** : sur un message envoyé, « annuler et remplacer » hors ligne, puis reconnexion → l'original est marqué annulé chez le destinataire de test.
7. **Double clic** : cliquer deux fois « Envoyer » sur un brouillon pendant un envoi lent (latence SMTP simulée au banc) → un seul message reçu.
8. **Angular, brouillon + PDF** : nouveau message, joindre un PDF de test anonymisé, cocher « Accusé de lecture », attendre 40 s (« Brouillon enregistré » s'affiche), Envoyer → le destinataire de test reçoit le PDF, et l'accusé de lecture est demandé. Avant : sans pièce ni demande d'accusé.
9. **Angular, transfert** : transférer un mail porteur d'un `IHE_XDM.ZIP` de test, attendre 40 s, Envoyer → le destinataire reçoit l'archive. Avant : sans pièce.
10. **Angular, annule et remplace** : sur un message envoyé porteur d'un document, « Annuler et remplacer », attendre 40 s, Envoyer → l'original est marqué annulé. Avant : envoyé comme un message simple, original resté valide.
11. **Angular, reprise de brouillon** : rédiger avec une pièce jointe, fermer, rouvrir le brouillon depuis « Brouillons » → la pièce jointe est toujours là.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — messagerie MSSanté intégrée au logiciel
- **Exigences DSR honorées** : traçabilité de l'envoi MSSanté (copie dans « Envoyés ») ; annule-et-remplace conforme à la recommandation MSSanté AMBU.MSS/va1.02 ; respect de l'opposition patient Mon Espace Santé
- **INS** : inchangé — les en-têtes X-MSS-INS accompagnent à nouveau les documents transférés ; aucune INS nouvelle manipulée
- **Authentification PS** : PSC / e-CPS inchangée pour l'envoi MSSanté
- **Habilitations** : inchangées (envoi depuis la boîte sélectionnée du praticien)
- **Interop CI-SIS** : IHE-XDM (pièces jointes `IHE_XDM.ZIP`) transmises intactes ; en-têtes MSSanté X-MSS-CODECDA / X-MSS-INS préservés
- **Tracé PGSSI-S** : envoi, archivage et annule-et-remplace tracés comme sur le chemin `sendmail` (même événements d'audit)
- **Consentement patient** : opposition Mon Espace Santé respectée sur tous les chemins et tous les clients (acquittement explicite du praticien) ; le blocage de réponse patient (`X-MSS-MES: FIN`, ECO.2.2.8) survit au chemin brouillon
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement inchangé
- **AIPD / impact RGPD** : inchangé — aucun traitement nouveau ; supprime des pertes de données

## Branches
- `api-mail` (pushed) : fix/task-329-envoi-chemin-unique — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-329-envoi-chemin-unique (depuis `origin/develop` @ `c3fdc010`, task-330 mergée)
- `client-blazor` (pushed) : fix/task-329-envoi-chemin-unique — https://github.com/codengine-technologies/HealthPlatform.Client/tree/fix/task-329-envoi-chemin-unique
- `client-mobile` (pushed) : fix/task-329-envoi-chemin-unique — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/fix/task-329-envoi-chemin-unique
- `dtos-mss` : aucune branche au `/start`. `/develop` la crée quand il touche le contrat (`SaveDraftDto`).
- `client-angular` (code-only) : la forge écrit sur la branche en cours dans `Client/Angular/` (au `/start` : `feature/nova-rewriting-mss`, avec du travail de task-349 non commité). L'humain gère la branche, le commit, le push et la PR TFS.

## Timings

*(généré par `tools/timing/report.sh --task task-329 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 32 s | — | — | — | — |
| **Total cycle** | | **32 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |
