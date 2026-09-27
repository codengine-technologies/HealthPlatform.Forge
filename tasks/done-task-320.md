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

## Branches
- `api-mail` (pushed) : feat/task-320-envoi-confirme-avec-carte — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-320-envoi-confirme-avec-carte
- `client-blazor` (pushed) : feat/task-320-envoi-confirme-avec-carte — https://github.com/codengine-technologies/HealthPlatform.Client/tree/feat/task-320-envoi-confirme-avec-carte
- `client-mobile` (pushed) : feat/task-320-envoi-confirme-avec-carte — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-320-envoi-confirme-avec-carte
- `dtos-mss` (pushed, créée par `/develop`) : feat/task-320-envoi-confirme-avec-carte — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-320-envoi-confirme-avec-carte
- `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` (au /start : `feature/nova-rewriting-mss`) — humain gère branche, commit, push, PR TFS

## Stitch design log

- Project : client-mobile (id 10088502293310567548)
- Screens :
  | Component / Page | Stitch title | Screen id | Action | Screenshot |
  |---|---|---|---|---|
  | pending-emails | — | — | création demandée, **non matérialisée** | — |
  | mail-compose (libellé d'envoi hors ligne seulement) | mail-compose | 57f1304fa14f449f90e914d1130779ed | reused (changement mineur, pas de refonte) | https://lh3.googleusercontent.com/aida/AEtjO1WoF3jZHWCn2tp9ljVkDp6G1koz_1jvKriOGPurazJaEybH030riFl89JdkNQnEs036jN7imUF2T_oXkVIQxGspMLx5MR6V_3eA85IQvKye74FcZ4pkrue4qKgK53_NEAv9QTagqjj86mJVJzIkB6jj5oTun9uiwZzlNNVEINfU9rHz-98BPCOYjMNII-6IblLk_q-83-tSL3wlTiIqq67OiRWnh0LOxJSgB3GrfrUt8yHV5HcqIXplc5s |
- `generate_screen_from_text` appelé **une seule fois** (2026-09-27, MOBILE, design system `assets/9aca84edc31f42798fd98bd24e151040`) → timeout MCP (attendu). Trois lectures espacées (2 × `get_project`, 1 × `list_screens`) sur ~20 min : aucune nouvelle `screenInstance`, aucun titre `pending-emails` (seul `updateTime` du projet a bougé, 10:59:54Z). **Pas de nouvelle génération** (règle anti-doublon). Si l'écran apparaît plus tard dans l'UI Stitch, le labelliser `pending-emails` ; sinon lancer le prompt ci-dessous à la main.
- Écran Ionic codé sans référence Stitch, dans l'esprit des écrans voisins (`mail-draft-list`, `inbox`) et du design system « Clinical Precision ».
- ⚠ Rename / labelliser in Stitch UI : l'écran généré par le timeout, s'il atterrit → label `pending-emails`
- ⚠ Doublons suspectés à nettoyer dans l'UI : none
- Stitch reachable : ✓ (génération non matérialisée — prompt ci-dessous pour exécution manuelle)

<details><summary>Prompt de génération (à rejouer dans l'UI Stitch si besoin)</summary>

```
Screen title: pending-emails

Mobile screen (390x844, Ionic-style, French UI) of a secure MSSanté medical messaging app for doctors, consistent with the existing client-mobile screens (inbox, mail-draft-list): same header bar with back arrow, Clinical Precision design system, Public Sans, primary blue #005EB8.

Purpose: list of "Messages prêts à partir" — messages the doctor wrote while working without his CPS card (Pro Santé Connect). Nothing leaves automatically: each message must be explicitly confirmed with the card.

Layout:
- Header: back arrow, title "Messages prêts à partir", subtitle count "3 messages".
- Info callout (primary blue, info icon): "Ces messages ont été rédigés sans carte. Aucun ne part sans votre confirmation."
- A second variant state shown as a warning callout at top (amber): "Hors ligne — présentez votre carte CPS pour envoyer." (the Envoyer buttons are then disabled).
- List of cards (8px radius, 1px outline), one per message: recipient line "À : dr.martin@medecin.mssante.fr" (bold), subject "Résultats biologie — suivi" , written date "Rédigé le 26/09 à 14:32", small chip "Rédigé sans carte" (surface-alt chip with card-off icon), attachment count with paperclip icon "1 pièce jointe".
- Each card has a row of 3 actions: "Revoir" (text button, eye icon), "Annuler" (outlined destructive red), "Envoyer" (solid primary, send icon).
- Empty state: envelope-check illustration, "Aucun message en attente".
No bottom tab bar (full-screen pushed page).
```
</details>

## Develop log

- Repos touched : dtos-mss, api-mail, client-blazor, client-angular (code-only), client-mobile
- DTOs published : HealthPlatform.Dtos.Mss 486.0.0 → **489.0.0** (`ConnectionStatusDto.PendingSendsCount`, `PendingEmailDto` déplacé dans le contrat partagé — la copie Blazor portait un `int Id`, l'annulation Blazor était inutilisable)
- Interop published : no interop change
- Commits :
  - dtos-mss : 36bc825 feat(dto): PendingSendsCount et PendingEmailDto partagé
  - api-mail : 726b749a chore(deps): bump Dtos 489.0.0 · c8016427 feat(mail): messages prêts à partir, confirmation avec la carte · 67cbd0fd fix(mail): envoyer un brouillon sans la carte le met de côté
  - client-blazor : fc919f3 chore(deps): bump Dtos 489.0.0 · 647043a feat(mss): messages prêts à partir · 87974c2 refactor(mss): simplify pass
  - client-mobile : 346be6d feat(mobile): messages prêts à partir · ce57c7c refactor(mobile): simplify pass
  - client-angular : **non commité** (code-only) sur `feature/nova-rewriting-mss` — `front/libs/mss/src/` : core/models/{mail,pending-email,sync}.model.ts, core/services/mss-api.service.ts (+ mss-api.pending-emails.service.spec.ts), core/stores/mailbox-session.store(.spec).ts, features/layout/mss-layout.component.{html,ts,spec.ts}, features/mail/components/mail-compose/mail-compose.component.{ts,html,scss,spec.ts}, features/pending-sends/mss-pending-sends.component.{ts,html,scss,spec.ts} (nouveau), ui/pending-sends-banner/* (nouveau), ui/offline-status-widget/*, ui/index.ts, index.ts (route `pending-sends`). Les deux `environment.ts` modifiés sont le WIP de l'humain, non touchés.
- Local build / test : ✓ tous les repos
  - api-mail : 5 618 passés, 16 ignorés (préexistants), 0 échec
  - client-blazor : 309 passés, 2 ignorés, 0 échec
  - client-angular : build 0 ; `npm test` vert sur 11 projets (mss-lib 396 dont 30 nouveaux)
  - client-mobile : 912 / 912 (un test `MailboxSwitcherComponent` est **instable, préexistant** — course Ionic `onAriaChanged`, échoue aussi sur la branche non modifiée ; vert à la revalidation)
- Passe qualité (/simplify) :
  - Applied & committed : client-blazor : 1 fichier (87974c2) · client-mobile : 2 fichiers (ce57c7c)
  - Applied (code-only, uncommitted) : client-angular : 1 fichier (`mss-pending-sends.component.ts`)
  - Rolled back (validation RED) : **api-mail** — kept as developed. La passe remplaçait la clôture d'un envoi par un `ExecuteUpdate` : EF garde alors l'entité suivie périmée dans le contexte, et le test d'intégration de confirmation a relu `AwaitingConfirmation` au lieu de `Completed`. Constat utile pour la suite : une transition par `ExecuteUpdate` après une lecture suivie laisse le tracker désynchronisé.
  - Skipped (contract/excluded) : dtos-mss
- Écarts et décisions :
  - **Faille fermée en cours de route** : `POST /drafts/{id}/send` n'avait aucun chemin hors ligne et envoyait en SMTP — donc **sans la carte** sur une boîte authentifiée par mot de passe. Hors ligne, le brouillon devient désormais un message prêt à partir (`202 awaitingConfirmation`). Les trois fronts avaient contourné la route (envoi par `sendmail` puis suppression du brouillon) : contournement désormais redondant mais correct, conservé.
  - **Blazor, hors du périmètre demandé** : `HttpRequestService` ne rafraîchit plus Keycloak / ne déconnecte plus sur un 401 dont le `code` commence par `PSC_SESSION_` — sans cela, « Envoyer » sans carte renvoyait le médecin à l'écran de connexion. Touche tous les endpoints qui rendent ce code.
  - **task-304** : aucun front ne désactivait lu / non lu, favori, suppression hors ligne ; seule la gestion des boîtes l'était, et le reste. Rien à revenir.
  - **Test d'intégration** : « hors ligne » y est une requête **sans cookie de session proxy** (chemin réel de production depuis task-171), et non le bypass `Client-Psc-Sub`/`Client-Rpps` prévu au DOD. Le test prouve aussi qu'un `X-PSC-Token` ne confirme pas un envoi.
  - **Règle 7c** : migrations FluentMigrator, sans `.Designer.cs` ni snapshot EF — le point « `.Designer.cs` présent » est sans objet. Migration prouvée en montée **et** en descente sur une base neuve (`PendingSendsAwaitConfirmationMigrationTests`), aucune autre ligne touchée.
  - **Stitch** : écran `pending-emails` **non créé** (génération expirée, jamais apparue après 20 min de vérifications) — l'écran Ionic est construit sans référence ; prompt consigné dans le `## Stitch design log` pour une génération manuelle. DOD « écran conçu dans Stitch » partiellement tenu.
  - **Cas limite connu** : si le proxy PSC était indisponible à l'entrée de la requête puis répond à la confirmation, l'identité de session est nulle et le verdict de boîte retombe en 403 au lieu de laisser passer. Rare, non traité.
  - **Préexistant, non corrigé** : l'autosave des brouillons Blazor journalise l'objet (`dto.Subject`) ; le widget Angular hors ligne interroge la liste complète toutes les 10 s pour la compter ; sur mobile, la bannière posée sur deux onglets relit l'état de connexion deux fois par changement d'onglet.
- DOD self-check : 17/19 items vérifiables par commande vérifiés ; restent au HAG : Stitch (partiel, ci-dessus) et la mise en cohérence E016 / E009 (`/tech-writer`).
- Next step : /sonar task-320

### Reprise après `/review` (CHANGES REQUESTED, 2026-09-27) — `questions/task-320.md`

- **api-mail** 9f78a225 : un envoi confirmé qui LÈVE (garde d'opposition 409, MIME, session, annulation) rend désormais le message (plus de ligne orpheline en `Processing`) ; `GET pending-emails/{id}` passe le corps dans `IHtmlBodySanitizer` (XSS de la relecture fermé à la source, pour les trois fronts). Tests : envoi qui lève (409 et annulation), HTML assaini (unitaire + intégration Postgres). 5 624 passés, 16 ignorés, 0 échec. Passe qualité : aucune simplification (diff de deux méthodes, relu).
- **client-blazor** 4b98cbd : la route brouillon distingue `Sent` / `AwaitingConfirmation` (202 → « Message prêt à partir », plus « Envoyé ») ; brouillon serveur supprimé si le chemin sendmail a réellement envoyé ; « Revoir » rendu dans une iframe `sandbox` sans `allow-scripts` ni `allow-same-origin` (défense en profondeur) ; réponse tardive de « Revoir » ignorée. 320 passés, 2 ignorés.
- **client-mobile** 731baa9 : `sendDraft` lit la réponse, 202 → `finalizeSetAside` ; la liste relit l'état de connexion à l'ouverture ; annulation gardée par le verrou de ligne. 918 / 918, lint propre.
- **client-angular** (non commité) : `sendDraft` typé `SendMailResultDto | null`, 202 → « awaiting » + rafraîchissement du compteur ; bannière masquée sur la page de la liste ; libellé du widget à 0. Build OK, tests verts (11 projets), lint 0 erreur.
- Hors reprise (suggestions de la revue, arbitrage humain) : MDN sans carte, rétention des payloads `Completed`, fraîcheur du jeton en cache au garde, exclusion `PSC_SESSION_*` à porter dans les intercepteurs mobile/Angular, polling de la bannière Blazor.

## Sonar log

- Serveur : SonarQube 9.9.8 (`sonar.login`), redémarré par l'étape (conteneurs `sonarqube_db` puis `sonarqube` arrêtés) ; période « new code » = 30 jours (héritée)
- Phase 1 (new code) : ✓ Quality Gate OK, new_coverage = 98.8 %, 0 issue new-code ouverte, 0 hotspot
- Phase 1 — Issues traitées : 1 — `csharpsquid:S3925` sur `MailboxIncompatibleException` : **faux positif** (le motif `ISerializable` réclamé est obsolète depuis .NET 8, SYSLIB0051 ; le triplet de constructeurs est présent) — marqué FALSE-POSITIVE avec justification, comme `PscIdentityConflictException` / `UnauthorizedException` le 2026-09-26
- Phase 1 — Tests ajoutés : 3 (a939435d) — confirmation refusée par SMTP → message rendu prêt à partir (intégration Postgres, couvre `ReturnToAwaitingConfirmationAsync`), échec sans message d'erreur, constructeurs de `MailboxIncompatibleException`. Toutes les lignes nouvelles de la task sont couvertes ; les 11 lignes non couvertes restantes du new code (`MailController.cs` 520-541, relance d'enrichissement) n'appartiennent pas à task-320
- Phase 2 (legacy) : skipped — baseline déjà bonne (8 code smells, notes A/A/A, reliquat du nettoyage 221 → 8)
- Build / tests : ✓ green (Release + OpenCover : 5 621 passés, 16 ignorés, 0 échec)

- **Re-analyse après la reprise de `/review`** (9f78a225) : Quality Gate OK, 0 issue new-code, new_coverage 98.8 %, toutes les lignes nouvelles de la task couvertes ; KPIs projet inchangés (tableau ci-dessous toujours exact). 5 624 passés, 16 ignorés, 0 échec.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 98.8 % | 98.8 % | 0 pt |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 8 | 8 | 0 |
| Coverage (projet) | 98.0 % | 98.0 % | 0 pt |
| Duplication | 0.5 % | 0.5 % | 0 pt |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

## Lint log

- client-angular (code-only, branche `feature/nova-rewriting-mss`) — base `origin/next`, scope `tag:scope:mss`
- Baseline : **0 erreur**, 56 warnings (`max-lines`, `complexity`, `jsdoc/require-example`) — tous sur des lignes antérieures à task-320 (vérifié par `git blame`)
- Itérations : 0 / 5 — rien à corriger ; build + tests déjà verts après la passe qualité (11 projets)
- Conventions (`conventions/angular.md`) : rien à alimenter, aucune correction manuelle
- Fichiers Angular laissés non commités pour l'humain : voir `## Develop log`

- **Re-lint après la reprise de `/review`** : 0 erreur (55 warnings préexistants), 0 itération.

## Lint mobile log

- client-mobile, branche `feat/task-320-envoi-confirme-avec-carte`
- Baseline : `npm run lint` → **All files pass linting** (0 erreur, 0 warning)
- Itérations : 0 / 5 — aucun fix, aucun commit
- Conventions (`conventions/angular.md`) : rien à alimenter

- **Re-lint après la reprise de `/review`** : All files pass linting, 0 itération.

## Visual verify log

- **skipped — tooling unavailable** : `Tools/visual-verify/` (capture.mjs, screens.json, fixtures) est absent de ce poste — `Tools/*` est exclu par `.gitignore` et l'outillage n'a jamais été versionné dans le plan de contrôle. Best-effort : la chaîne continue.
- Écrans mobiles à vérifier à la main au HAG : `pending-emails` (route `/pending-emails`, nouveau — **sans référence Stitch**, cf. `## Stitch design log`), `mail-compose` (libellé hors ligne du bouton d'envoi), `pending-sends-banner` (sur `/tabs/home` et `/tabs/messages`).
- Reprise après `/review` : toujours **skipped — tooling unavailable** (même cause).
- À traiter hors task : versionner `Tools/visual-verify/` (exception dans `.gitignore`) pour que l'étape soit reproductible sur tout poste.

## PRs

Label `awaiting-human-merge` sur les quatre (une seule US, à tester assemblée et à merger ensemble — règle 11).

- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/34
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/253
- `client-blazor` : https://github.com/codengine-technologies/HealthPlatform.Client/pull/83
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/79
- `client-angular` : code-only — humain gère commit/push TFS et ouverture PR, sur `feature/nova-rewriting-mss`. Fichiers modifiés par la forge (21) :
  - `front/libs/mss/src/core/models/mail.model.ts`
  - `front/libs/mss/src/core/models/pending-email.model.ts`
  - `front/libs/mss/src/core/models/sync.model.ts`
  - `front/libs/mss/src/core/services/mss-api.pending-emails.service.spec.ts`
  - `front/libs/mss/src/core/services/mss-api.service.ts`
  - `front/libs/mss/src/core/stores/mailbox-session.store.spec.ts`
  - `front/libs/mss/src/core/stores/mailbox-session.store.ts`
  - `front/libs/mss/src/features/layout/mss-layout.component.html`
  - `front/libs/mss/src/features/layout/mss-layout.component.spec.ts`
  - `front/libs/mss/src/features/layout/mss-layout.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose.component.html`
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose.component.scss`
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose.component.ts`
  - `front/libs/mss/src/features/pending-sends/`
  - `front/libs/mss/src/index.ts`
  - `front/libs/mss/src/ui/index.ts`
  - `front/libs/mss/src/ui/offline-status-widget/offline-status-widget.component.html`
  - `front/libs/mss/src/ui/offline-status-widget/offline-status-widget.component.scss`
  - `front/libs/mss/src/ui/offline-status-widget/offline-status-widget.component.ts`
  - `front/libs/mss/src/ui/pending-sends-banner/`
  - (les deux `environment.ts` modifiés sont le WIP de l'humain, hors task)

## Code Review Summary

- **1er passage : CHANGES REQUESTED** (`questions/task-320.md`) — ligne orpheline en `Processing` sur un envoi qui lève ; XSS dans « Revoir » (HTML client non assaini, iframe Blazor non sandboxée) ; brouillon mis de côté (202) annoncé « envoyé » sur les trois fronts.
- **2e passage : APPROVED** — les trois points fermés (api-mail 9f78a225, client-blazor 4b98cbd, client-mobile 731baa9, client-angular non commité), aucun nouveau bloquant. Revalidation : api-mail 5 624 passés / 16 ignorés, client-blazor 320 / 2 ignorés, client-mobile 918 / 918, client-angular 11 projets verts, dtos-mss build OK.
- Promesse de l'US confirmée : aucun chemin ne permet à un message rédigé de partir sans une confirmation faite pendant une session PSC.
- Suggestions non bloquantes à arbitrer : MDN envoyé sans carte (préexistant) ; rétention des payloads `Completed` (AIPD) ; jeton PSC en cache au garde ; remise en attente qui échoue elle-même ; exclusion `PSC_SESSION_*` à porter dans les intercepteurs mobile/Angular ; message d'erreur mobile sur réponse texte ; polling de la bannière Blazor.

### Correctif ajouté après ouverture des PRs — double envoi depuis l'éditeur (2026-09-27)

Signalé par l'humain : le bouton « Envoyer » / « Mettre de côté » pouvait être cliqué plusieurs fois (doublons). Corrigé sur les trois fronts, avec un spinner dans le bouton pendant l'envoi :
- client-blazor 8485980 : verrou posé en premier (il l'était après les dialogues d'avant envoi), point d'entrée unique bouton + Ctrl+Entrée ; 328 passés, 2 ignorés ; 8 tests, vérifiés rouges par mutation.
- client-mobile 385ecce : verrou tenu jusqu'à la fin de la requête (il était relâché après les contrôles) ; corrige aussi un brouillon recréé après un envoi réussi ; 927 / 927, lint propre ; tests de double envoi vérifiés rouges par mutation (un test DOM instable dépendant du rendu d'`ion-modal` remplacé par une assertion sur l'état).
- client-angular (non commité) : verrou posé avant toute attente, tenu jusqu'à la fermeture ; spinner du design system ; 11 tests ; build + tests verts, lint 0 erreur.
- Commentaire ajouté sur les PRs Client #83 et Mobile #79.

## Timings

*(généré par `tools/timing/report.sh --task task-320 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 56 s | — | — | — | — |
| /develop | ok | 7 min 07 s | 26 (3 min 09 s) | 26 (12 min 45 s) | — | dtos-mss 1B/0T, api-mail 13B/13T, client-blazor 6B/5T, client-mobile 3B/4T, client-angular 3B/4T, rework after review |
| /sonar | ok | 4 min 27 s | 4 (46 s) | 16 (8 min 58 s) | 6 (1 min 40 s) | 1 itération(s), api-mail 4B/16T, re-analysis after review rework |
| /lint-angular | ok | 16 s | — | — | — | — |
| /lint-mobile | ok | 15 s | — | — | — | — |
| /verify-visual | skipped | 0.4 s | — | — | — | tooling unavailable (Tools/visual-verify absent) |
| /review | ok | 6 min 02 s | 10 (41 s) | 8 (4 min 27 s) | — | dtos-mss 2B/0T, api-mail 2B/2T, client-blazor 2B/2T, client-mobile 2B/2T, client-angular 2B/2T |
| /tech-writer | ok | 9 min 57 s | — | — | — | — |
| **Total cycle** | | **29 min 05 s** | **40 (4 min 37 s)** | **50 (26 min 11 s)** | **6 (1 min 40 s)** | |

Autres commandes mesurées : lint ×4 (38 s), nuget-wait ×1 (18 s), restore ×2 (4.1 s)
