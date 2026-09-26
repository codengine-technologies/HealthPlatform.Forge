# todo-task-320.md — Sans sa carte, le médecin travaille sur sa messagerie ; aucun message ne part sans sa carte

**Repos**: api-mail, dtos-mss, client-blazor, client-angular, client-mobile
**Dependencies**: —
**Epic**: E016

> Remédiation n°3 de l'audit sécurité du registre du 2026-09-16 (écart élevé).
> Voir aussi task-318 (jeton PSC vérifié et lié au compte, livrée) et task-319
> (re-validation continue).
>
> **Réorientée le 2026-09-26 (arbitrage humain).** La première version fermait le
> trou en passant la messagerie en **lecture seule** sans carte. L'intention produit
> est autre : *« fonctionnellement, un médecin peut avoir accès à sa messagerie en
> mode offline même s'il ne dispose pas de sa CPS »*. Arbitrage retenu : **il lit,
> classe et rédige sans carte ; ses envois attendent une confirmation explicite
> faite avec la carte.** Rien ne part tout seul.

## Objectif

**Le besoin.** Un médecin n'a pas toujours sa carte CPS sous la main (oubliée,
poste sans lecteur, e-CPS indisponible). Il doit pouvoir **travailler** sur sa
messagerie avec sa seule connexion Keycloak, qui **exige un MFA** : lire, trier,
préparer ses réponses.

**Le problème actuel.** Sans carte, un message rédigé est mis en file côté serveur
(`202 Accepted`), puis **rejoué automatiquement** dès qu'une session Pro Santé
Connect réapparaît, sous l'identité PSC du professionnel. Le message part donc
**sans que le médecin l'ait jamais validé avec sa carte** : il a présenté sa carte
pour autre chose, et un envoi préparé plus tôt part « avec ». C'est contraire au
garde-fou non négociable du PO (*« envoi MSSanté : exiger PSC ou e-CPS »*) et à la
PGSSI-S sur l'imputabilité des actes.

Le MFA de Keycloak ne ferme pas ce trou :
1. Keycloak authentifie fortement **le compte** ; seule PSC (CPS / e-CPS, adossée au
   RPPS) identifie **le professionnel** au moment de l'acte d'envoi.
2. Le décalage dans le temps reste : l'envoi est imputé à une présentation de carte
   qui ne le visait pas.
3. Le MFA protège la connexion, pas la session ouverte (poste laissé ouvert, jeton
   Keycloak volé).

**Après cette US** :
- sans carte, le médecin **lit** et **classe** comme aujourd'hui (le classement
  reste mis en file et appliqué au retour de la carte) ;
- sans carte, il **rédige** : l'envoi devient un message **« prêt à partir »**, que
  le serveur ne rejoue **jamais** de lui-même ;
- une fois sa carte présentée, l'application lui montre **« N messages prêts à
  partir »** ; il les **revoit**, puis **envoie** ou **annule** chacun, par un geste
  explicite fait **pendant une session PSC**. C'est ce geste qui constitue l'acte
  d'envoi, imputé au professionnel à cet instant.

## Constat établi par lecture du code (2026-09-16, revu le 2026-09-26)

- `Api/Mail/src/Api/Controllers/V1/MailController.cs` — sur `IsOnlineMode == false`,
  `SendMail` et `SendCancelAndReplace` sérialisent le message et l'empilent
  (`PendingActionTypes.SendMail`) avec `202 Accepted { queued = true }`. Les bascules
  lu / non lu / favori et la suppression (`MarkRead`, `MarkUnread`, `MarkFlagged`,
  `MarkUnflagged`, `Delete`) sont mises en file de la même façon. Le déplacement
  (`move`, `bulk/move`) n'est **pas** mis en file : il va directement à l'IMAP, qui
  échoue en 401 sans session PSC.
- `Api/Mail/src/Application/Services/Implementation/PendingActionService.cs` —
  `ProcessPendingActionsAsync` rejoue la file **dès que** `IsOnlineMode` est vrai,
  déclenché par `POST /api/v1/connection/sync/pending-actions` et en fin de cycle
  de synchronisation. Il sait **déjà** exclure les envois (paramètre
  `excludeSendMail`), mais par défaut il les rejoue.
- **Déjà en place et réutilisable** : `GET /api/v1/mail/pending-emails` (liste des
  envois en attente) et `DELETE /api/v1/mail/pending-emails/{id}` (annulation).
  Blazor les consomme (`ConnectionStatusService`, `PendingEmailsDialog.razor`).
  Angular et mobile lisent `pendingActionsCount` / `canSendEmail`
  (`sync.model.ts`, `connection-status.model.ts`) mais n'ont pas de liste.
- `PendingAction.Status` (`PendingActionStatus`) : `Pending`, `Processing`,
  `Completed`, `Failed`. Aucun état « attend une confirmation ».
- `Dtos/ConnectionStatusDto.cs` : `Mode`, `CanAccessImap`, `CanSendEmail`,
  `PendingActionsCount`, `LastSyncedAt`.

### Revue après task-171 (2026-09-26)

- **`IsOnlineMode` n'est plus « un jeton PSC est présent ».** C'est le **verdict du
  proxy** (`IPscTokenProvider.GetModeAsync`) sur la session désignée par le cookie
  `proxy_session_id`, posé par `UserContextEnricherMiddleware.ResolvePscSessionAsync`.
  L'en-tête `X-PSC-Token` est **ignoré**.
- **Proxy en panne = « hors ligne dégradé ».** `GetModeAsync` rend
  `Offline(Unavailable)` quand le proxy ne répond pas. Aujourd'hui, un médecin qui a
  bien présenté sa carte voit alors ses envois mis en file et rejoués plus tard.
  **Le nouveau modèle neutralise ce cas** : un envoi en file attend une
  confirmation, quelle que soit la raison du « hors ligne ».
- **La confirmation n'a pas besoin du verdict stocké.** Elle passe par
  `GetAccessTokenAsync`, qui lève déjà des exceptions typées :
  `UnauthorizedException` (pas de session, session expirée → 401),
  `UnavailableException` (`ProxyUnavailable` → 503), `PscIdentityConflictException`
  (→ 403). Le `GlobalExceptionHandler` (règle 12) les traduit.
- **Tests et banc** : en bypass de test, « en ligne » = `Client-Psc-Sub` **et**
  `Client-Rpps` présents (`ApplyTestBypassSession`) ; « hors ligne » = sans ces deux
  en-têtes.
- `MailController.cs` a été retouché par task-315 (#243) : repartir du code actuel.

## Règles métier

**RG-1 — Lecture sans carte : inchangée.** Dossiers, en-têtes, contenu, pièces
jointes déjà synchronisées, recherche locale, journal d'audit : servis avec la seule
session Keycloak.

**RG-2 — Classement sans carte : mis en file, appliqué au retour de la carte.**
Marquer lu / non lu, favori, suppression : comportement actuel (EPIC E009) conservé.
Ces gestes n'engagent pas l'identité du professionnel auprès d'un tiers. Le
déplacement reste hors file (comportement actuel, hors périmètre).

**RG-3 — Envoi sans carte : « prêt à partir », jamais rejoué automatiquement.**
`SendMail`, réponse, transfert et annuler-et-remplacer hors ligne sont enregistrés
avec un nouvel état `AwaitingConfirmation`. La réponse est `202 Accepted
{ queued = true, awaitingConfirmation = true }`, avec un message pour le praticien :
« Message prêt à partir. Il sera envoyé quand vous le confirmerez avec votre carte. »
`ProcessPendingActionsAsync` **ne traite jamais** un envoi, quel que soit l'appelant
(route manuelle, fin de synchronisation).

**RG-4 — Envoi confirmé avec la carte, message par message.** Une nouvelle route
`POST /api/v1/mail/pending-emails/{id}/send` envoie **un** message prêt à partir.
Elle exige une session PSC valide **à cet instant** : pas de session → 401, proxy
indisponible → 503, conflit d'identité → 403, tous en `ProblemDetails` (règle 12,
exceptions typées existantes). Elle exige aussi une boîte compatible avec la session
(task-303, `CanUseImap`) : sinon 403. L'envoi passe par le **chemin d'envoi normal**
(archivage Sent, traces, métriques). Un message déjà envoyé ou annulé → 404.

**RG-5 — Revoir avant d'envoyer.** La liste `GET /api/v1/mail/pending-emails`
expose, pour chaque message prêt à partir : destinataires, objet, date de
rédaction, et la mention qu'il a été rédigé **sans carte**. Le contenu complet est
consultable avant confirmation. Annuler reste `DELETE .../pending-emails/{id}`.

**RG-6 — Stock existant au déploiement.** Les `SendMail` encore `Pending` au
moment du déploiement basculent en `AwaitingConfirmation` (migration de données) :
ils apparaissent dans la liste, rien ne part tout seul. Les actions de classement en
attente restent rejouées normalement.

**RG-7 — L'état de connexion dit la vérité.** `ConnectionStatusDto` gagne
`PendingSendsCount` (messages prêts à partir), distinct de `PendingActionsCount`
(classements en file). `CanSendEmail` garde son sens : « un envoi immédiat est
possible ». Contrat `dtos-mss` → publication NuGet et bump des consommateurs .NET ;
types TypeScript mis à jour à la main côté Angular et mobile.

**RG-8 — Fronts : travailler sans carte, confirmer avec la carte.** Sur les trois
fronts (Blazor, Angular, mobile) :
- hors ligne, l'éditeur est **disponible** ; le bouton d'envoi dit ce qu'il fait
  (« Mettre de côté — à confirmer avec votre carte ») ;
- hors ligne, les gestes de classement (lu / non lu, favori, suppression) sont
  **disponibles** (task-304 les avait désactivés) ;
- en ligne avec `PendingSendsCount > 0`, un bandeau « N messages prêts à partir »
  mène à la liste ; chaque ligne propose **Revoir**, **Envoyer**, **Annuler** ;
- hors ligne, la liste est consultable mais **Envoyer** y est désactivé, avec la
  raison.

**RG-9 — Trace d'audit.** L'envoi confirmé est tracé par le chemin d'envoi normal,
sous le type existant, **à l'instant de la confirmation** et sous l'identité PSC de
la session. La mise en attente et l'annulation sont comptées dans une métrique
(par issue : mis en attente, confirmé, annulé), pas tracées une à une. **Aucun
nouveau membre `AuditActionType`** (miroir manuel côté Angular et Blazor).

> ⚠️ **Arbitrage humain requis — non bloquant pour démarrer.**
>
> 1. **« Tout envoyer »** : la v1 impose une confirmation **par message** (RG-4), pour
>    que chaque envoi soit un geste conscient. Un bouton « Tout envoyer » (avec
>    récapitulatif) est plus confortable, mais augmente le risque qu'un message
>    préparé par quelqu'un d'autre sur une session laissée ouverte parte sans être lu.
>    Défaut : **par message**.
> 2. **Durée de vie d'un message prêt à partir** : défaut **pas d'expiration**, l'âge
>    est affiché. Alternative : expiration après N jours avec information du praticien.
> 3. **Modifier un message prêt à partir** (le rouvrir dans l'éditeur) : **hors v1**.
>    Contournement : annuler puis réécrire.
>
> Sans réponse, l'US part avec les défauts.

## Definition of Done

- [ ] Build passes (0 errors) — chaque repo, commande du tableau CLAUDE.md
- [ ] Tests pass (0 failures) — chaque repo
- [ ] Hors ligne : `SendMail`, `SendCancelAndReplace`, réponse, transfert → `202 { queued = true, awaitingConfirmation = true }`, ligne en file à l'état `AwaitingConfirmation`
- [ ] `ProcessPendingActionsAsync` ne traite **aucun** `SendMail`, ni via `POST /api/v1/connection/sync/pending-actions`, ni en fin de synchronisation
- [ ] Hors ligne : marquer lu / non lu, favori, suppression restent mis en file et sont rejoués au retour en ligne (non-régression E009)
- [ ] `POST /api/v1/mail/pending-emails/{id}/send` : session PSC valide + boîte compatible → envoi par le chemin normal, ligne `Completed` ; pas de session → 401 ; proxy indisponible → 503 ; conflit d'identité → 403 ; boîte non compatible → 403 ; id inconnu, déjà envoyé ou annulé → 404 ; toutes les erreurs en `application/problem+json`
- [ ] `GET /api/v1/mail/pending-emails` expose destinataires, objet, date de rédaction et la mention « rédigé sans carte » ; contenu complet consultable
- [ ] Migration de données : les `SendMail` `Pending` existants passent en `AwaitingConfirmation` ; migration relue selon la règle 7c (pas d'opération fantôme, `.Designer.cs` présent, pas de dérive)
- [ ] `ConnectionStatusDto.PendingSendsCount` ajouté dans `dtos-mss`, package publié, consommateurs .NET bumpés ; types TS Angular et mobile mis à jour
- [ ] Lecture hors ligne inchangée — test d'intégration qui le prouve (`GET /api/v1/mail/folders` hors ligne → 200)
- [ ] Un en-tête `X-PSC-Token` envoyé par un client non migré ne permet **pas** de confirmer un envoi
- [ ] Métrique des envois par issue (mis en attente, confirmé, annulé) ; aucun nouveau membre `AuditActionType`
- [ ] Aucune donnée de santé (objet, corps, destinataires) dans les logs ajoutés
- [ ] Tests unitaires : mise en attente d'un envoi hors ligne (état `AwaitingConfirmation`) ; `ProcessPendingActionsAsync` ignore les envois et rejoue les classements ; décision de confirmation (session + compatibilité → envoi ; chaque refus → bonne exception typée)
- [ ] Tests d'intégration (bypass de test : « hors ligne » = sans `Client-Psc-Sub`/`Client-Rpps`) : envoi hors ligne → 202 et ligne `AwaitingConfirmation` ; passage en ligne + `sync/pending-actions` → le message **n'est pas** parti ; `POST .../pending-emails/{id}/send` en ligne → envoyé ; même route hors ligne → 401
- [ ] Blazor, Angular, mobile : éditeur et classement disponibles hors ligne ; bouton d'envoi hors ligne libellé « à confirmer avec votre carte » ; bandeau « N messages prêts à partir » en ligne ; liste avec Revoir / Envoyer / Annuler ; Envoyer désactivé hors ligne avec la raison ; tous les libellés en i18n, `data-testid` sur chaque élément interactif
- [ ] Tests de composant par front : bandeau (affiché si `PendingSendsCount > 0`), liste (rendu + Envoyer + Annuler), bouton d'envoi hors ligne (libellé et appel)
- [ ] Mobile : écran de la liste conçu dans Stitch (`/stitch-design`) et vérifié par `/verify-visual`
- [ ] Le document d'EPIC E016 et la fiche E009 (« mode hors-ligne ») sont mis en cohérence par `/tech-writer`

## Manual Test Plan

- **Lancer** : `cd Api/Mail && aspire run --project src/AppHost`, puis un front :
  mobile `cd Client/Mobile && npm start`, Blazor `cd Client/Blazor && dotnet run`,
  Angular `cd Client/Angular/front && npm start`.
- **Se placer hors ligne** : se connecter via Keycloak (MFA) **sans** présenter la
  carte, ou se connecter avec la carte puis fermer la session PSC (déconnexion PSC).
  Le bandeau « hors ligne » s'affiche.
- **Lire et classer sans carte** : ouvrir des dossiers, un message, une pièce jointe
  déjà synchronisée ; marquer un message lu, un autre en favori, en supprimer un.
  **Attendu** : tout fonctionne ; les classements apparaissent comme « en attente ».
- **Rédiger sans carte** : écrire un message vers une adresse de test MSSanté, cliquer
  « Mettre de côté — à confirmer avec votre carte ». **Attendu** : confirmation « prêt
  à partir » ; en base praticien, une ligne `SendMail` à l'état `AwaitingConfirmation` :
  `docker exec postgres-pgvector psql -U postgres -d {u_…} -c "select \"ActionType\", \"Status\", \"CreatedAt\" from \"PendingActions\" order by \"CreatedAt\" desc limit 5;"`
- **Retour de la carte** : se reconnecter avec la carte. **Attendu** : les classements
  sont appliqués ; **le message ne part pas** ; un bandeau « 1 message prêt à partir »
  s'affiche.
- **Confirmer** : ouvrir la liste, **Revoir** le message (destinataires, objet, date,
  mention « rédigé sans carte »), puis **Envoyer**. **Attendu** : le message part, il
  apparaît dans « Envoyés », le bandeau disparaît.
- **Annuler** : rédiger un second message hors ligne, revenir avec la carte, cliquer
  **Annuler**. **Attendu** : rien ne part, la ligne disparaît.
- **Confirmation sans carte** (ligne de commande, bearer Keycloak valide, **sans**
  cookie `proxy_session_id`) :
  ```bash
  curl -sk -X POST https://localhost:{port}/api/v1/mail/pending-emails/{id}/send \
    -H "Authorization: Bearer {bearer keycloak}" -H "Client-Email: {adresse}" -i
  ```
  **Attendu** : `401` en `application/problem+json` ; le message reste prêt à partir.
- **Proxy en panne** : connecté avec la carte, arrêter le conteneur du proxy PSC, puis
  cliquer **Envoyer** sur un message prêt à partir. **Attendu** : `503`, message
  « service d'authentification momentanément indisponible » ; rien ne part.
  Redémarrer le proxy : l'envoi repasse.
- **Non-régression en ligne** : avec la carte, envoyer un message normalement.
  **Attendu** : envoi immédiat, comme avant, sans passage par la liste.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — mise en conformité d'une promesse produit existante
- **Exigences DSR honorées** : MSSanté — exigence d'authentification forte du professionnel émetteur **au moment de l'envoi** (référence DSR à confirmer par le PO humain sur le couloir médecine de ville)
- **INS** : non applicable — aucune manipulation d'identité patient
- **Authentification PS** : **c'est l'objet de l'US.** La session Keycloak (MFA) suffit à lire, classer et **préparer** ; l'**envoi** MSSanté exige un geste explicite pendant une session Pro Santé Connect (CPS / e-CPS, niveau eIDAS substantiel). L'acte d'envoi est la confirmation, pas la rédaction
- **Habilitations** : inchangées ; l'US fixe le niveau d'authentification requis pour l'acte d'envoi, pas le périmètre des boîtes
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : envoi tracé à l'instant de la confirmation, sous l'identité PSC de la session ; métrique des envois mis en attente / confirmés / annulés. Conservation alignée sur le journal existant
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement inchangé
- **AIPD / impact RGPD** : à mettre à jour — lecture, classement et rédaction de messages contenant des DSCP possibles avec la seule session Keycloak MFA (point d'attention à formaliser) ; les messages prêts à partir sont stockés en base praticien jusqu'à confirmation ou annulation ; tout envoi exige l'identité forte du professionnel
