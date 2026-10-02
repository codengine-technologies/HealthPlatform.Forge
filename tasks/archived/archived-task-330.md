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

## Arbitrage humain du 2026-10-02 (au démarrage de /develop)

**Constat** : task-330 a été rédigée contre `develop @ 14d58398`. **task-320** a été mergée le même
jour, après ce commit (`faa4c65e`). Depuis, **aucun message ne part sans la carte** : un envoi écrit
hors ligne naît `AwaitingConfirmation`, le rejeu ne le voit jamais, et un envoi confirmé qui échoue
est rendu « prêt à envoyer » (`ReturnToAwaitingConfirmationAsync`).

**Décision 1 — garder task-320** : aucun rejeu automatique d'un envoi. Le rejeu automatique de
task-330 porte sur les **gestes** (lu / non lu, drapeau, suppression, acquittement biologique).

**Décision 2 — « remise incertaine » bloquée et signalée**.
- **Le cas** : un envoi confirmé échoue **après** le `DATA` (refus `MessageNotAccepted`), ou à un
  stade indécidable (coupure de transport, délai dépassé pendant l'envoi). Le message est peut-être
  parti.
- **Le traitement** : il passe en **remise incertaine**. Il est visible dans la liste des messages
  en attente avec l'avertissement « Ce message est peut-être parti : vérifiez auprès du destinataire
  avant de le renvoyer ».
- Il n'est **plus confirmable** tel quel. Le praticien peut seulement le retirer de la liste.

### DOD — lignes remplacées (les autres sont inchangées)

- ~~`SendMail` qui échoue une fois (503 SMTP simulé) → rejoué au passage suivant et envoyé~~ →
  **un envoi confirmé qui échoue AVANT remise** (refus SMTP pré-`DATA`, serveur injoignable)
  **reste « prêt à envoyer »** avec sa cause, et n'est jamais rejoué tout seul (task-320).
- ~~`SendMail` en échec post-DATA → jamais rejoué, passe en échec définitif visible~~ → **un envoi
  confirmé qui échoue APRÈS `DATA` ou à un stade indécidable passe en remise incertaine** :
  - `GET pending-emails` le rend avec ce statut ;
  - `POST pending-emails/{id}/send` le refuse (409) ;
  - `DELETE` le retire.
- Le test d'intégration de l'endpoint (règle 1b) porte sur ces trois comportements.

## Branches
- `api-mail` (pushed) : fix/task-330-rejeu-hors-ligne-fiable — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-330-rejeu-hors-ligne-fiable (depuis `origin/develop` @ `d3892216`)
- `dtos-mss` (pushed, créée par `/develop`) : fix/task-330-rejeu-hors-ligne-fiable — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/fix/task-330-rejeu-hors-ligne-fiable (commit `a095df4`, NuGet 501.0.0)

## Develop log

**Repos touchés** : `dtos-mss` (contrat), `api-mail`. Aucun front : l'affichage des échecs est
hors périmètre (US front à rédiger).

**Contrat** : branche `dtos-mss` `fix/task-330-rejeu-hors-ligne-fiable`, créée à la demande, commit
`a095df4`. La CI a publié le package **501.0.0**, et api-mail l'a pris en version (`f5f7f277`).
- `PendingEmailDto.DeliveryUncertain` (bool) : le message est peut-être parti.
- `ConnectionStatusDto.FailedActionsCount` (int) : les gestes hors ligne en échec définitif.

**Commits api-mail** (branche `fix/task-330-rejeu-hors-ligne-fiable`, poussée) :
- `f5f7f277` chore(deps) : DTO 501.0.0.
- `3cbd73b4` fix(pending-actions) : le cœur de l'US.
- `78e7a126` fix(smtp) : le refus après `DATA` passe en remise incertaine, et l'envoi d'un
  brouillon qui lève ne laisse plus le brouillon bloqué.
- `d13d1504` refactor : passe qualité.

### Ce qui change

**Rejeu des gestes (AUD-08)** : lu / non lu, drapeau, suppression, acquittement biologique.
1. Un geste n'est supprimé qu'après un succès **réel**. Le `Result` de la propagation des drapeaux
   et de la suppression IMAP est lu. Un échec rend le geste à la file (`Pending`) et compte une
   tentative.
2. Après **10** tentatives (`PendingActionService.MaxReplayAttempts`), le geste passe en échec
   définitif (`Failed`). Il est **gardé** et compté dans
   `GET connection/status` (`FailedActionsCount`), au lieu d'être supprimé en silence.
3. Une annulation (arrêt de la synchronisation, requête abandonnée) rend le geste sans compter de
   tentative (`ReturnClaimAsync`), et la passe s'arrête.
4. **Réclamations orphelines** : la colonne `ClaimedAt` est nouvelle. Au début de chaque passe, une
   ligne `Processing` réclamée depuis plus de 10 min est rendue. Un geste redevient `Pending`. Un
   envoi passe en **remise incertaine**, parce qu'il a pu partir.
5. **Délai de reprise** : une passe de synchronisation. Pas de backoff ajouté : la politique de
   rejeu de la synchronisation de fond est l'objet de task-334.

**Envoi confirmé (arbitrage du 2026-10-02, décisions 1 et 2)** : aucun rejeu automatique d'un
envoi (task-320 inchangée). Le **stade** de l'échec SMTP décide de la suite :

| Échec | Ce qui est parti | Statut HTTP | Le message en attente |
|---|---|---|---|
| Règles d'envoi (destinataire, expéditeur, objet, Cc/Bcc, taille des PJ) | rien | 400 | reste prêt à envoyer, avec sa cause |
| Serveur injoignable, reconnexion 421 en échec | rien | 503 | reste prêt à envoyer |
| Session déconnectée (`ServiceNotConnectedException`, levée avant toute écriture) | rien | 503 | reste prêt à envoyer |
| Refus du serveur **avant** `DATA` (expéditeur, destinataire) | rien | 500 (`Result.Error`, inchangé) | reste prêt à envoyer |
| Refus **après** `DATA` (`MessageNotAccepted`) | le corps a été transmis | 503 + avertissement | **remise incertaine** |
| Pas de réponse : coupure, délai, `SmtpProtocolException`, annulation pendant l'émission | indécidable | 503 + avertissement (499 si annulé) | **remise incertaine** |
| Refus PSC typé (task-171) | rien | 401 / 403 / 503, via `GlobalExceptionHandler` | reste prêt à envoyer |

- **Remise incertaine** :
  - `GET pending-emails` la rend avec `deliveryUncertain: true` ;
  - `POST pending-emails/{id}/send` répond 409 ;
  - `DELETE` la retire.
- L'avertissement est fixe : « Ce message est peut-être parti : vérifiez auprès du destinataire
  avant de le renvoyer. » Le message de transport n'est jamais exposé.
- **Mise en file hors ligne** : les mêmes règles d'enveloppe que l'envoi (`MailSendRules`). Un
  message sans destinataire est refusé (400) au lieu d'être accepté (202).
  - La **taille des pièces jointes** reste contrôlée à la confirmation : c'est une règle de la
    configuration d'envoi, et un message refusé y reste prêt à envoyer avec sa cause.

### Décisions prises en implémentant

- **Le refus après `DATA` est incertain**, comme l'écrit l'arbitrage. Ma première implémentation
  rangeait tout refus du serveur en « non parti ». Relue contre la décision humaine, elle a été
  corrigée, test rouge d'abord (`78e7a126`).
- **Une session déconnectée est une indisponibilité, pas une incertitude** : MailKit lève
  `ServiceNotConnectedException` avant toute écriture.
- **L'envoi d'un brouillon** (`DraftService`) suit le chemin d'échec ordinaire :
  - les cas « serveur injoignable » et « remise incertaine » répondent 502 ;
  - le brouillon revient en rédaction avec sa cause, qui est l'avertissement en cas d'incertitude ;
  - toute autre exception remet le brouillon en rédaction, puis remonte telle quelle.

  Ce défaut était introduit par ce changement : `SmtpService` lève désormais là où il rendait un
  `Result`, et le brouillon restait bloqué en `Sending`. La passe qualité l'a signalé.
- **`LastError`** stocke un type d'exception ou une cause technique, jamais le contenu du message.
- **Défaut de production trouvé en route** : une copie d'entité suivie que les `ExecuteUpdate` ne
  rafraîchissent pas.
  - La synchronisation de fond garde son contexte d'une passe à l'autre. Au second échec d'un geste,
    `ReleaseClaimAsync` remettait `Pending` sur une copie déjà `Pending` : EF n'y voyait aucun
    changement, et la ligne restait `Processing` en base.
  - **Correctif** : `GetByIdAsync` lit sans suivi, et `ReleaseClaimAsync` relit la ligne.
    `ReturnClaimAsync` est désormais un `ExecuteUpdate` conditionnel.
  - **Prévention** : `conventions/csharp.md` › `executeupdate-copie-suivie-perimee`.

### Hors de cette US, signalé pour `/review`

`DraftService.SetAsideAsync` (un brouillon mis de côté hors ligne) met un envoi en file **sans**
passer par `MailSendRules`. Ce n'est plus une perte : le message refusé reste prêt à envoyer, avec
sa cause, depuis task-320. Mais ce chemin ne refuse pas encore à l'écriture. Le déplacer dans
`PendingActionService.QueueActionAsync` changerait la réponse de `drafts/{id}/send` hors ligne :
c'est laissé à la décision de l'humain.

### Preuves rouges

- **SMTP** : les tests de stade ont été joués contre l'ancien `SmtpService` (`git show HEAD:`, puis
  restauré par `cp` + `touch`). Résultat : 10 rouges, 3 gardes vertes. Les tests du nouveau contrat
  étaient rouges à la compilation.
  - Refus après `DATA` : `SendMailAsync_ARefusalAfterTheData_IsADeliveryUncertainFailure` est rouge
    sur la première implémentation (« No exception was thrown »).
- **Brouillon** : 3 tests de `DraftServiceTests` sont rouges sur le service d'avant.
  `ADraftWhoseSendThrows_Is502WithTheCause_AndGoesBackToEditing` (HTTP, ×2) est rouge sur le
  `DraftService` d'avant : 503 au lieu de 502, et le brouillon reste `Sending`.
- **Copie suivie** (par mutation) :
  - sans `ReloadAsync`, `AGestureWhoseReplayFails_…` et `AReplayAbandonedMidway_…` sont rouges ;
  - sans `AsNoTracking`, `ADeliveryUncertainConfirmation_…` est rouge (404 au lieu de 409).
- **Intégration, par mutation** (`PendingSendConfirmationIntegrationTests`) :

| Mutation | Test rouge |
|---|---|
| M1 — supprimer le geste sans lire le `Result` (comportement d'avant) | `AGestureWhoseReplayFails_StaysQueued_…`, `AGestureThatExhaustsItsAttempts_…` |
| M2 — geste épuisé supprimé au lieu de `Failed` | `AGestureThatExhaustsItsAttempts_IsKeptFailed_AndCountedInTheStatus` |
| M3 — pas de reprise des orphelines | `AnOrphanClaim_IsReplayedForAGesture_AndBecomesDeliveryUncertainForASend` |
| M4 — annulation comptée comme échec | `AReplayAbandonedMidway_GivesTheGestureBack_WithoutCountingAnAttempt` |
| M5 — envoi incertain rendu « prêt à envoyer » | `ADeliveryUncertainConfirmation_IsListedAsSuch_CannotBeConfirmedAgain_AndCanBeRemoved` |
| M6 — mise en file sans les règles d'envoi | `WithoutTheCard_AMessageWithoutRecipient_Is400ProblemJson_AndNothingIsQueued` |
| M7 — envoi incertain reconfirmable | `ADeliveryUncertainConfirmation_…` |
| M8 — `FailedActionsCount` non rempli | `AGestureThatExhaustsItsAttempts_…` |

Chaque mutation est restaurée par réécriture, avec un mtime rafraîchi.

### Audit de migration (règle 7c)

`20261002090000_AddPendingActionClaimedAt` (FluentMigrator) :
- une colonne nullable `ClaimedAt` ajoutée à `PendingActions`, sans défaut ni rétro-remplissage ;
- `Down` symétrique, aucune opération fantôme ;
- FluentMigrator n'a ni snapshot ni designer à vérifier ;
- mapping EF `timestamp without time zone`, aligné sur `CreatedAt` ;
- jouée sur Postgres par la suite d'intégration.

**Une ligne `Processing` antérieure au déploiement** a `ClaimedAt = NULL` et est traitée comme
orpheline. Pendant un déploiement progressif, un envoi confirmé en cours sur un ancien pod pourrait
donc passer en remise incertaine. C'est le sens prudent : un avertissement, jamais un doublon.

### Validation

- Build : 0 erreur.
- Tests api-mail : **6 090 verts, 0 échec**, 16 ignorés (déjà ignorés avant la task).

| Suite | Verts |
|---|---|
| domain | 190 |
| infrastructure | 675 |
| api | 1 157 |
| application | 3 357 |
| integration | 711 |

### Passe qualité (§Q)

Commit `d13d1504` :
- `ReturnClaimAsync` est un seul `ExecuteUpdate` ;
- filtre « réclamation périmée » partagé ;
- `CountByStatusAsync` ;
- `MarkAsFailedAsync` retirée : son seul appelant a disparu avec cette task ;
- un seul bras 499 dans `GlobalExceptionHandler` ;
- message d'objet dérivé de `MaxSubjectLength`.

Écartés :
- passer `ReleaseClaimAsync` en `ExecuteUpdate` : ses tests d'infrastructure tournent sur EF
  InMemory, qui ne le supporte pas ;
- regrouper les comptages de `connection/status` : motif antérieur à la task ;
- espacer la reprise des orphelines : un `UPDATE` indexé qui ne touche aucune ligne, à mesurer au
  banc avant d'optimiser ;
- déplacer le code `MAIL_DELIVERY_UNCERTAIN` dans `MailUnavailabilityCodes` : ce n'est pas une
  indisponibilité ;
- réduire les constructeurs de l'exception : S3925 ;
- retirer les gardes `?.` sur le `Result` du rejeu : un collaborateur peut rendre `null`.

## Sonar log

Serveur SonarQube 9.9.8.100196 (`sonar.login`), new code sur 30 jours. Deux analyses complètes de
la branche. Les cinq passes Release avec couverture sont vertes aux deux analyses : 0 échec,
intégration 711/711 (16 ignorés).

- **Phase 1 (new code)** : Quality Gate **OK**, `new_coverage` = **97,5 %** (cible 95 %).
- **Phase 1, findings de la task** : 4, tous traités (`6880140c`, `309db6a4`).
  - **S3776** : `DraftService.SendDraftAsync` avait une complexité de 16. L'appel SMTP et ses
    `catch` passent dans `SendThroughSmtpAsync`.
  - **S125** : un commentaire d'intention finissait par « (503) ; ». Récidive : 8ᵉ occurrence.
  - **xUnit1045** : `TheoryData<Exception>` des coupures de transport. La théorie prend désormais
    une chaîne. Récidive : 2ᵉ occurrence.
  - **S3925** : `SmtpDeliveryUncertainException` a le triplet de constructeurs. Le constructeur
    `ISerializable` est obsolète (SYSLIB0051) : l'issue est marquée **FALSE-POSITIVE** avec ce
    motif, comme le prévoit la consigne.
- **Phase 1, finding hors task** : **S107** sur `SemanticSearchService.cs:379`, 8 paramètres.
  - Aucun fichier de cette task n'y touche, et la méthode date du dépôt initial. L'issue est entrée
    dans la fenêtre « new code » de 30 jours par un autre changement.
  - Elle n'est pas corrigée ici (règle 6 : périmètre isolé). Le Quality Gate reste OK.
- **Phase 1, tests ajoutés par `/sonar`** : aucun. La couverture du new code était déjà au-dessus
  de la cible.
- **Phase 2 (legacy)** : non lancée, les cibles du projet sont atteintes. Les 13 code smells
  restants sont tous hors des fichiers de la task : 9 S107 et 4 CA1829 en tests.
- **Build / tests** : verts.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 97,6 % | 97,5 % | −0,1 pt |
| New code smells | 0 | 1 (S107, hors task) | +1 |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 8 | 13 | +5, aucun dans un fichier de la task |
| Coverage (projet) | 98,1 % | 98,0 % | −0,1 pt |
| Duplication | 0,4 % | 0,4 % | 0 |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

La baseline est la dernière analyse du serveur (2026-10-01 21:24 UTC, branche de task-349). Elle
ne voyait pas les smells de `develop` arrivés depuis.

**Conventions** (`conventions/csharp.md`) :
- S125 passe à 8 occurrences, xUnit1045 à 2, S3925 à 3.
- Nouvelle entrée **S3776** : un `try/catch` ajouté à une méthode déjà chargée.
- **Récidive = lecture** (règle d'or, point 3) : `agents/develop.md` §Q, étape 2b, rend S125 et
  xUnit1045 **mécaniques**. Deux `grep` sur le diff doivent rester vides avant le push. Ce
  changement de playbook est à relire par l'humain avant le push du plan de contrôle.

## Lint log

`/lint-angular` : **skipped**. `client-angular` n'est pas dans les `**Repos**` de la task, et `/develop` n'y a rien écrit. Le travail non commité présent dans `Client/Angular/` appartient à l'humain et à task-349 : il n'est pas touché.

## Lint mobile log

`/lint-mobile` : **skipped**. `client-mobile` n'est pas dans les `**Repos**` de la task, et aucune branche n'y a été créée.

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail + dtos-mss touchés | ✅ verte | 25 verts, 0 flaky, 0 rouge, 0 quarantaine | 3 min 44 s |
| angular | api-mail + dtos-mss touchés | ✅ verte | 25 verts, 0 flaky, 0 rouge, 0 quarantaine | 3 min 25 s |

- Backend e2e construit depuis `Api/Mail` sur `fix/task-330-rejeu-hors-ligne-fiable` @ `309db6a4`.
- Clients : `Client/Mobile` sur `develop`. `Client/Angular` sur `feature/nova-rewriting-mss`, la branche de l'humain, avec le travail de task-349 non commité.
- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task (inchangé par la task).
- Quarantaines : aucune.
- Divergences ouvertes : aucune.
- Parcours touchés sans spec e2e modifié : aucun. La task ne touche aucun écran.
- Démontage : complet (ports libres, aucun conteneur e2e résiduel).

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 1 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 1 | headless | Créer puis supprimer un contact | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/38 — label `awaiting-human-merge`
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/269 — label `awaiting-human-merge`

Ordre de merge : `dtos-mss` d'abord (package 501.0.0 déjà publié), puis `api-mail`.

## Code Review Summary

**Verdict : APPROVED.** 0 point bloquant restant, 6 suggestions.

**Fichiers revus** : 15 fichiers `src` d'api-mail, plus 2 DTO. Une constatation bloquante du
verrou 4a a été trouvée, puis corrigée pendant la revue (voir plus bas).

### Validation

- **Build** : dtos-mss ✓, api-mail ✓ (0 erreur).
- **Tests api-mail** : 0 échec, 16 ignorés (déjà ignorés avant la task).

| Suite | Verts |
|---|---|
| domain | 190 |
| infrastructure | 675 |
| api | 1 157 |
| application | 3 357 |
| integration | 715 |

- **E2E** : vert. Les deux voies ont 25 tests verts chacune, la parité est verte.

### Verrou 4a — comportement → test d'intégration → preuve rouge

Tous les tests sont dans `PendingSendConfirmationIntegrationTests` : HTTP, base Postgres réelle du
praticien.

| Comportement atteint par un endpoint | Test | Preuve rouge |
|---|---|---|
| Un geste dont le rejeu échoue reste en file, avec une tentative comptée, puis est appliqué à la passe suivante (`POST connection/sync/pending-actions`) | `AGestureWhoseReplayFails_StaysQueued_WithOneAttempt_AndIsAppliedAtTheNextPass` | M1 : suppression sans lire le `Result`. Rouge aussi sans le `ReloadAsync` |
| Un geste épuisé est gardé `Failed` et compté dans `GET connection/status` (`FailedActionsCount`, champ DTO) | `AGestureThatExhaustsItsAttempts_IsKeptFailed_AndCountedInTheStatus` | M2 : épuisé supprimé. M8 : compteur non rempli |
| Une réclamation orpheline : le geste est rejoué, l'envoi passe en remise incertaine (colonne `ClaimedAt`, SQL) | `AnOrphanClaim_IsReplayedForAGesture_AndBecomesDeliveryUncertainForASend` | M3 : pas de reprise |
| Un rejeu abandonné rend le geste sans compter de tentative | `AReplayAbandonedMidway_GivesTheGestureBack_WithoutCountingAnAttempt` | M4 : annulation comptée. Rouge aussi sans le `ReloadAsync` |
| Une confirmation en remise incertaine : 503 avec l'avertissement, listée `deliveryUncertain` (champ DTO), 409 à la reconfirmation, retirable | `ADeliveryUncertainConfirmation_IsListedAsSuch_CannotBeConfirmedAgain_AndCanBeRemoved` | M5 : rendue prête à envoyer. M7 : reconfirmable. Rouge aussi sans `AsNoTracking` (404 au lieu de 409) |
| **Classification par stade du vrai `SmtpService`** : refus après `DATA` et coupure → incertaine. Refus avant `DATA` et serveur injoignable → reste prête à envoyer | `AConfirmedSendThatFails_IsClassifiedByItsStage_ByTheRealSmtpService` (×4) | Rouge sur le `SmtpService` de `develop` (les deux cas incertains), et sur la mutation `MessageNotAccepted` |
| Mise en file hors ligne d'un message sans destinataire : 400 problem+json, rien en file | `WithoutTheCard_AMessageWithoutRecipient_Is400ProblemJson_AndNothingIsQueued` | M6 : file sans règles d'envoi |
| Envoi d'un brouillon dont le SMTP lève : 502 avec la cause, retour en rédaction | `ADraftWhoseSendThrows_Is502WithTheCause_AndGoesBackToEditing` (×2) | Rouge sur le `DraftService` d'avant (503, brouillon bloqué en `Sending`) |

**Constatation de revue, corrigée** : la classification par stade vit dans `SmtpService`. Or les
tests d'endpoint le substituaient, donc elle n'était prouvée qu'en unitaire. Le test HTTP sur le vrai
`SmtpService` a été ajouté (`d97eb039`), avec sa preuve rouge. Le code de production n'a pas changé.

### Revue par axe

- `PendingActionService` ✅ : suppression seulement après un succès réel. L'annulation est filtrée
  sur le jeton du rejeu, donc un délai `HttpClient` reste un échec compté.
- `PendingActionRepository` ✅ : transitions conditionnelles en SQL. Lecture de décision non suivie,
  relecture avant modification.
- `SmtpService` ✅ : un seul `switch` de stade, conforme à l'arbitrage. `ServiceNotConnectedException`
  est une indisponibilité.
- `MailController` / `GlobalExceptionHandler` ✅ : remise incertaine marquée avant la remontée. 503
  avec un avertissement fixe, jamais le message de transport. 499 si le praticien a abandonné.
- `DraftService` ✅ : plus aucun brouillon bloqué `Sending`.
- Migration ✅ : audit 7c dans le Develop log.
- Sécurité ✅ : aucun secret. `LastError` ne porte que des types d'exception ou des causes techniques.
  L'avertissement exposé est fixe.

### Suggestions (non bloquantes)

1. **`ClaimedAt` en heure locale** (`DateTime.Now`), comme `CreatedAt`. Au passage à l'heure d'été,
   une réclamation vivante peut paraître vieille d'une heure. Pour un envoi, cela donne une remise
   incertaine à tort, c'est-à-dire un avertissement, jamais un doublon. Une US « horodatage UTC des
   `PendingActions` » réglerait les deux colonnes.
2. **Les clients actuels ignorent `deliveryUncertain`** :
   - ils affichent le message comme prêt à envoyer, avec son bouton « Confirmer » ;
   - la confirmation répond 409, avec un message explicite ;
   - `PendingSendsCount` ne compte pas ces messages.

   L'US front prévue au périmètre (« affichage des échecs ») doit porter l'avertissement et le
   compteur `FailedActionsCount`.
3. **`DraftService.SetAsideAsync`** met un envoi en file sans `MailSendRules`. Le message n'est pas
   perdu : refusé à la confirmation, il reste prêt à envoyer avec sa cause. Déplacer le contrôle dans
   `PendingActionService.QueueActionAsync` changerait la réponse de `drafts/{id}/send` hors ligne :
   à arbitrer.
4. **Journal « failed for good … {Error} »** de `ReleaseClaimAsync` : il existait déjà sur `develop`
   (« Dropping … »). L'erreur d'un geste peut être un message IMAP qui cite un nom de dossier. Mieux
   vaudrait n'y journaliser que le type.
5. **Déploiement progressif** : une ligne `Processing` sans `ClaimedAt` est traitée comme orpheline.
   Un envoi confirmé en cours sur un ancien pod pourrait passer en remise incertaine. C'est le sens
   prudent, et c'est documenté dans la migration.
6. **`SemanticSearchService.cs:379`** (S107, hors task) est entré dans la fenêtre « new code » de
   Sonar : il est à traiter dans sa propre task.

### Manual Test Plan aligné (recopié dans la PR api-mail)

> Ce plan est **aligné sur l'arbitrage du 2026-10-02**. Le plan initial du task file prévoyait qu'un
> envoi hors ligne parte tout seul au passage suivant (ses étapes 2 à 4). Depuis task-320, aucun envoi
> ne part sans la carte, et la décision 1 garde cette règle. Ces étapes sont remplacées par les
> étapes 2 à 5 ci-dessous. Les étapes de rejeu des gestes sont inchangées.

1. Lancer `cd Api/Mail && dotnet run --project src/AppHost` (profil banc, GreenMail + Toxiproxy),
   puis le client mobile : `cd Client/Mobile && npm start`.
2. Hors ligne, envoyer un message de test → 202, « prêt à envoyer », visible dans la liste des
   messages en attente.
3. Revenir en ligne avec la carte. Couper le SMTP (Toxiproxy `smtp`) puis confirmer le message.
   **Attendu** : 503, et le message reste prêt à envoyer. Il n'est pas rejoué tout seul.
4. Rétablir le SMTP, puis confirmer à nouveau. **Attendu** : le message part une seule fois, et il
   apparaît chez le destinataire de test.
5. **Remise incertaine** : écrire un message hors ligne, puis confirmer en coupant le transport
   **pendant** l'émission (Toxiproxy `timeout` sur `smtp`). **Attendu** :
   - 503 avec « Ce message est peut-être parti : vérifiez auprès du destinataire avant de le
     renvoyer » ;
   - `GET api/v1/mail/pending-emails` le rend avec `deliveryUncertain: true` ;
   - une nouvelle confirmation répond 409 ;
   - `DELETE api/v1/mail/pending-emails/{id}` le retire.

   Les clients n'affichent pas encore l'avertissement : c'est l'US front à suivre.
6. Hors ligne, marquer un message lu, puis provoquer un échec IMAP au rejeu (Toxiproxy `imap`
   coupé). Revenir en ligne. **Attendu** : le geste reste en file. Rétablir l'IMAP : le drapeau est
   appliqué au passage suivant (vérifier depuis un autre client IMAP).
7. Arrêter la synchronisation pendant un rejeu. **Attendu** : le geste reste en attente, sans
   tentative comptée, et il est appliqué au démarrage suivant.
8. Mettre en file, hors ligne, un message sans destinataire. **Attendu** : 400 immédiat avec un
   message clair, et rien dans la liste.
9. Un geste qui échoue 10 fois de suite reste en base, en échec. **Attendu** : `GET
   api/v1/connection/status` rend `failedActionsCount ≥ 1`.


## Timings

*(généré par `tools/timing/report.sh --task task-330 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 56 s | — | — | — | — |
| /develop | ok | 1 h 00 min | 4 (33 s) | 17 (9 min 16 s) | — | dtos-mss 1B/0T, api-mail 3B/17T |
| /sonar | ok | 18 min 03 s | 3 (38 s) | 11 (11 min 58 s) | 4 (1 min 16 s) | 2 itération(s), api-mail 3B/11T |
| /lint-angular | skipped | 0.5 s | — | — | — | client-angular non touché (Repos: api-mail) |
| /lint-mobile | skipped | 0.5 s | — | — | — | client-mobile non touché (Repos: api-mail) |
| /e2e | ok | 8 min 21 s | — | — | — | e2e ×3 (7 min 19 s) |
| /review | ok | 8 min 53 s | 2 (6.7 s) | 2 (5 min 18 s) | — | dtos-mss 1B/0T, api-mail 1B/2T |
| /tech-writer | ok | 54 s | — | — | — | — |
| **Total cycle** | | **1 h 37 min** | **9 (1 min 18 s)** | **30 (26 min 34 s)** | **4 (1 min 16 s)** | |

Autres commandes mesurées : nuget-wait ×1 (27 s), restore ×1 (23 s)

## Merged

Mergé le 2026-10-02 par `/merge 330 --i-tested` (HAG : test humain attesté).

| Repo | PR | Commit squash sur `develop` | CI `develop` |
|---|---|---|---|
| `dtos-mss` | #38 | `67f6aeb7` | ✅ https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/actions/runs/36992800485 |
| `api-mail` | #269 | `c3fdc010` | ✅ https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/36992827204 |

- Branches `fix/task-330-rejeu-hors-ligne-fiable` supprimées, distantes et locales, sur les deux repos. Label `awaiting-human-merge` retiré.
- Aucune branche staging : la task n'appartenait pas à un run `/forge`.
- task-338 (#268, api-mail) reste ouverte. Elle épingle `HealthPlatform.Dtos.Mss` 500.0.0 alors que `develop` est désormais en 501.0.0 : fusionner `develop` dans sa branche avant son merge.
