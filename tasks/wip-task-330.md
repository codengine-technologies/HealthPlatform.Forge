# todo-task-330.md — Ce que le médecin a fait hors ligne finit par être appliqué, ou il est averti : fin des actions perdues au premier échec

**Repos**: api-mail
**Dependencies**: — (aucune)
**Epic**: E009
**Single frontend**: true
**Priorité**: **1** — un courrier médical mis en file hors ligne (« sera envoyé à la reconnexion ») qui rencontre une erreur passagère au rejeu est **perdu sans aucun avertissement** ; un acquittement biologique aussi.

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, **AUD-08** — trouvé indépendamment par trois zones,
> contre-vérifié — et **AUD-23**). Le défaut est même écrit dans le code : la remarque de
> `IPendingActionRepository.ReleaseClaimAsync` (l. 101-109) dit « une action ayant échoué une fois
> n'est donc plus jamais rejouée ».

## Ce qui est établi (develop @ `14d58398`)

**Rejeu (AUD-08)** — `PendingActionService.cs:150-184, 211-235`, `PendingActionRepository.cs:43-51, 162-176, 245-259` :
1. `MarkAsFailedAsync` passe l'action à `Failed` ; `GetPendingActionsAsync` ne lit que `Pending` →
   **jamais rejouée** ; la branche `RetryCount >= 3` est inatteignable ; `GetPendingEmailsAsync`
   (lit aussi `Pending`) la retire de la liste « en attente » du praticien ;
   `CleanupOldFailedActionsAsync` finit par la supprimer. Aucune notification.
2. Drapeaux (`PropagateFlagChangeAsync`) et suppressions (`DeleteEmailAsync`) rendent un `Result`
   sans lever : `ProcessActionAsync` l'ignore, puis `DeletePendingActionAsync` s'exécute **même en échec**.
3. `TryProcessActionAsync` attrape aussi `OperationCanceledException` (arrêt de synchro, arrêt du pod)
   et la compte comme un échec.
4. Une ligne réclamée (`Processing`) puis interrompue par un crash reste bloquée à vie.
5. La mise en file (`MailController.cs:1341-1357`) n'exécute pas `CheckMailDtoForSending` : un mail
   invalide est accepté (202) puis perdu au rejeu.

**Stade de l'échec d'envoi (AUD-23)** — `SmtpService.cs:50-52, 86-90, 93-157, 197-208`,
`SmtpConnectionFactory.cs:243-276` : tout échec sort en `Result.Error` (donc 500) — y compris
l'`UnavailableException` voulue du rejeu 421 (avalée par le `catch (Exception)` englobant), les refus
PSC typés, l'échec d'authentification SMTP, l'annulation, le mode hors ligne, les erreurs de validation.
**Conséquence pour ce rejeu** : impossible de distinguer « rien n'est parti » de « le DATA a peut-être
été accepté » — un rejeu naïf d'un `SendMail` créerait des **doublons de courrier médical**.

## Objective

Qu'une action faite hors ligne soit **rejouée jusqu'à succès ou jusqu'à un échec définitif signalé au
praticien**, jamais supprimée sur un échec, jamais rejouée quand le message a peut-être déjà été remis ;
et que les échecs d'envoi sortent avec leur vrai statut (400, 401/403, 499, 503) au lieu d'un 500 unique.

### Périmètre

1. **Rejeu** : sur échec transitoire, retour à `Pending` avec compteur (`ReleaseClaimAsync`, déjà
   présent) et délai de reprise ; échec définitif après N tentatives → statut visible, non supprimé
   tant que le praticien n'en a pas pris connaissance.
2. **Résultats contrôlés** : chaque branche de `ProcessActionAsync` teste le `Result` (ou lève) ;
   une action n'est supprimée **qu'après** un succès réel.
3. **Annulation** : relancée, jamais comptée comme échec ; l'action reste `Pending`.
4. **Actions orphelines** : une ligne `Processing` plus ancienne qu'un seuil redevient `Pending`.
5. **Validation à la mise en file** : `CheckMailDtoForSending` appliqué avant d'accepter un envoi hors ligne (400 si invalide).
6. **Stade de l'échec SMTP** : `SmtpService` distingue au minimum « non émis » (rejouable) et
   « peut-être remis » (post-DATA, non rejouable) ; un `SendMail` « peut-être remis » n'est **jamais**
   rejoué et passe en échec définitif signalé.
7. **Statuts HTTP** (règle 12) : validation → 400, refus PSC typés → 401/403 via `GlobalExceptionHandler`,
   annulation → 499, transport / 421 non récupéré → 503.
8. **Visibilité** : `GET pending-emails` (ou la liste d'actions) expose les envois en échec définitif
   avec leur statut — l'affichage dans les fronts est une suite (hors périmètre), mais l'API le rend disponible.

### Hors périmètre

- L'unification des chemins d'envoi (task-329, qui s'appuie sur celle-ci).
- L'affichage des échecs dans Blazor / mobile (US front à rédiger après cette US).
- La politique de rejeu de la synchro de fond (task-334).

## Definition of Done

- [ ] Build passes (0 errors) — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] **Tests rouges d'abord** (log des runs rouges dans le task file), rouges sur le code actuel :
  - [ ] `SendMail` qui échoue une fois (503 SMTP simulé) → rejoué au passage suivant et envoyé
  - [ ] propagation de drapeau dont le `Result` est en échec → l'action **n'est pas** supprimée
  - [ ] annulation pendant le rejeu → l'action reste `Pending`, `RetryCount` inchangé
  - [ ] ligne `Processing` ancienne → redevient `Pending`
- [ ] Test : `SendMail` en échec **post-DATA** → jamais rejoué, passe en échec définitif visible
- [ ] Test : mise en file d'un mail sans destinataire → 400, rien en file
- [ ] Tests `SmtpService` : validation → `Result.Invalid` (400) ; `UnavailableException` du rejeu 421 → 503 ; refus PSC typés → remontent au `GlobalExceptionHandler` ; annulation → 499
- [ ] Test d'intégration endpoint (règle 1b) : `GET pending-emails` rend les envois en échec définitif avec leur statut
- [ ] Non-régression : `DeadSessionPolicyTests` et tests task-277 verts (aucun rejeu après DATA)
- [ ] Aucune donnée de santé ni contenu de mail dans les logs ; `LastError` stocké sans contenu clinique

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` (profil banc, GreenMail + Toxiproxy) ; client mobile `cd Client/Mobile && npm start`.
2. Passer hors ligne, envoyer un message de test → 202 « sera envoyé à la reconnexion ».
3. Rendre le SMTP indisponible (Toxiproxy `smtp` coupé), revenir en ligne → le rejeu échoue une fois.
4. Rétablir le SMTP → **Attendu** : le message part au passage suivant et apparaît chez le destinataire de test. Avant : perdu, disparu de la liste « en attente ».
5. Hors ligne, marquer un message lu puis provoquer un échec IMAP au rejeu → le drapeau est appliqué au passage suivant (vérifier depuis un autre client IMAP).
6. Arrêter la synchro pendant un rejeu → l'action reste en attente et part au démarrage suivant.
7. Mettre en file un message sans destinataire → 400 immédiat avec un message clair.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — messagerie MSSanté intégrée, continuité de service hors ligne
- **Exigences DSR honorées** : non applicable — fiabilité de fonctionnalités existantes (envoi, acquittement biologique)
- **INS** : non applicable — l'acquittement biologique rejoué conserve son rattachement existant, aucune INS nouvelle
- **Authentification PS** : PSC / e-CPS inchangée ; les refus PSC sont rendus avec leur statut propre (401/403)
- **Habilitations** : inchangées — une action n'est rejouée que dans le contexte de son praticien et de sa boîte
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : chaque rejeu (succès, échec transitoire, échec définitif) tracé ; un envoi « peut-être remis » est tracé comme tel
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement inchangé
- **AIPD / impact RGPD** : inchangé — aucun traitement nouveau

## Branches
- `api-mail` (pushed) : fix/task-330-rejeu-hors-ligne-fiable — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-330-rejeu-hors-ligne-fiable (depuis `origin/develop` @ `d3892216`)
- `dtos-mss` : aucune branche au `/start`. Elle est créée paresseusement par `/develop`, seulement si un contrat change (exposition du statut d'échec dans `pending-emails`).
