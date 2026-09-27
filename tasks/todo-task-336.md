# todo-task-336.md — Après une bascule de boîte, le praticien reçoit en temps réel les messages de la boîte qu'il regarde, et d'aucune autre

**Repos**: api-mail, client-blazor, client-mobile
**Dependencies**: — (aucune)
**Epic**: E016
**Single frontend**: false
**Priorité**: **2** — un praticien à plusieurs boîtes qui bascule sur la boîte B reçoit les nouveaux mails, les enrichissements et la progression de synchronisation **de la boîte A**, et rien de B : les indicateurs « en cours » ne se terminent jamais et les tags d'urgence de B n'apparaissent pas.

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, **AUD-21**, trouvé par deux zones indépendamment).
> **Découpage validé par l'humain le 2026-09-27** : l'ancienne task-336 (« plusieurs serveurs, un seul
> comportement ») est scindée en trois — **task-336** (ce fichier : flux SSE et boîte suivie), **task-343**
> (backplane SSE et conversations IA partagés entre réplicas), **task-344** (promotion unique d'un mail).
> Chacune est testable et mergeable seule.

## Ce qui est établi (develop @ `14d58398`)

- `EventSource` (navigateur) **ne peut pas poser d'en-tête HTTP** : le flux SSE n'envoie jamais `Client-Email`.
  Le jeton passe déjà par la query sur ces routes (`token=***` dans les logs de requête).
- `src/Api/Middleware/UserContextEnricherMiddleware.cs:596-605, 722-730` : la boîte n'est lue **que** dans l'en-tête
  `Client-Email` ; sans en-tête, le middleware sélectionne la boîte **par défaut** du compte et remplit
  `UserContextInfo.Email`.
- `src/Api/Controllers/V1/MailEventsController.cs:71, 93-95` : le contrôleur ne lit `?mailbox=` que si
  `_userContext.Email` est vide — ce qui n'arrive jamais (la route exige une boîte). Ce **repli brut, non validé
  contre le registre**, deviendrait exploitable le jour où il serait atteignable (route marquée
  `[MailboxNotRequired]`, ou correctif mal placé dans le contrôleur).
- **Aucun client n'envoie `?mailbox=`** : mobile `mail-events-stream.service.ts:66-69`, Blazor `MailSseService.cs:162-176`.
- Le commentaire de `MailEventsControllerTests.cs:90` (« le middleware aurait déjà répondu 403 ») est faux.

## Objective

Que le flux temps réel d'un praticien suive **la boîte qu'il affiche**, validée contre le registre comme toute
autre requête, et se réaligne dès qu'il change de boîte.

### Périmètre

1. **Middleware** : pour les routes SSE **uniquement** (`MailEventsController`, `NotificationsController`), quand
   l'en-tête `Client-Email` est absent, lire `?mailbox=` et le soumettre **à la même validation** que l'en-tête
   (compte × adresse au registre, compatibilité de la boîte). Adresse non rattachée ou non sélectionnable →
   403 `ProblemDetails` (même refus que l'en-tête). Sans `?mailbox=` ni en-tête : comportement actuel (boîte par défaut).
2. **Contrôleur** : suppression du repli brut sur le paramètre `mailbox` (`MailEventsController.cs:93-95`) ; le
   contrôleur ne lit plus que `UserContextInfo.Email`, déjà validé.
3. **Clients** : `client-mobile` et `client-blazor` ouvrent le flux avec `?mailbox=` de la boîte **affichée**, et
   **ferment puis rouvrent** le flux à chaque bascule de boîte. Aucune autre évolution du flux (format des
   événements inchangé).
4. Correction du commentaire erroné de `MailEventsControllerTests.cs:90`.

### Hors périmètre

- La diffusion des événements entre réplicas (**task-343**) : cette US garantit la **bonne boîte**, task-343
  garantira que l'événement atteint le praticien **quel que soit le réplica** qui l'émet.
- `client-angular` : non listé — l'humain vérifie son propre flux SSE (code-only).

## Definition of Done

- [ ] Build passes (0 errors) sur les 3 repos ; Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] **Test rouge d'abord** (log du run rouge dans le task file) : flux SSE ouvert **sans en-tête** avec
      `?mailbox=B` (B rattachée au compte) → sur le code actuel abonné à la boîte **par défaut A** ; après correctif abonné à **B**
- [ ] Test : `?mailbox=` d'une boîte **non rattachée** au compte → 403 `application/problem+json`, aucun abonnement
- [ ] Test : `?mailbox=` d'une boîte rattachée mais non sélectionnable (`Detached`, `AuthFailing`) → même refus que l'en-tête
- [ ] Test : en-tête `Client-Email` présent → il prime sur `?mailbox=` (comportement actuel inchangé)
- [ ] Test : `?mailbox=` sur une route **non** SSE → ignoré (aucun élargissement de la sélection de boîte)
- [ ] Test d'intégration endpoint (règle 1b) : `GET` du flux SSE avec `?mailbox=` validé de bout en bout (DI, registre)
- [ ] `client-mobile` : spec Jasmine — l'URL du flux porte `?mailbox=` de la boîte affichée ; à la bascule, le flux est fermé puis rouvert avec la nouvelle boîte
- [ ] `client-blazor` : test bUnit / service — même comportement
- [ ] `data-testid` et libellés (FR mobile / Localizer Blazor) sur tout élément ajouté (a priori aucun élément visuel)
- [ ] Aucune adresse ni jeton ajouté dans les logs

## Manual Test Plan

1. Backend : `cd Api/Mail && dotnet run --project src/AppHost` ; mobile : `cd Client/Mobile && npm start` ; Blazor en parallèle.
2. Praticien de test disposant de **deux boîtes** A (par défaut) et B.
3. Sur mobile, basculer sur B, puis envoyer un mail de test **vers B** depuis une autre boîte → il apparaît en temps réel dans B. **Avant** : rien n'apparaît, et un mail envoyé vers A déclenchait une notification alors que B est affichée.
4. Rebasculer sur A, envoyer un mail vers A → il apparaît en temps réel ; aucun événement de B ne s'affiche.
5. Même scénario dans Blazor.
6. `curl -N "https://localhost:{port}/api/v1/mail/events/stream?folder=INBOX&mailbox=adresse-non-rattachee@…&token={jeton}"` → 403 `ProblemDetails`.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR honorées** : non applicable — fiabilité du multi-boîtes (E016) existant
- **INS** : non applicable
- **Authentification PS** : PSC / e-CPS inchangée (jeton en query sur les routes SSE, comme aujourd'hui)
- **Habilitations** : **au cœur** — la boîte suivie par le flux est validée contre le registre (compte × adresse), jamais crue telle quelle ; le repli non validé est supprimé
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : refus d'ouverture de flux sur une boîte non rattachée tracé comme les autres refus de sélection de boîte
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement inchangé
- **AIPD / impact RGPD** : inchangé — supprime une diffusion d'événements vers la mauvaise boîte d'un même praticien
