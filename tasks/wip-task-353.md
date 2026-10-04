# todo-task-353.md — Un message supprimé depuis un autre logiciel disparaît de la liste, et ne s'ouvre jamais sur un contenu vide

**Repos**: api-mail, client-angular, client-blazor, client-mobile
**Dependencies**: — (aucune ; task-352 touche le même composant de liste, même famille de défaut : la mettre en œuvre d'abord évite un conflit)
**Epic**: E009
**Priorité**: **2** — le praticien voit un message qui n'existe plus, l'ouvre, et lit un compte rendu **vide**. Il peut croire le document vide, ou perdu, au lieu de comprendre qu'il a été supprimé ou déplacé ailleurs. Le cas est courant dès que la boîte MSSanté est aussi ouverte dans un autre logiciel.

> **Origine.** Bug constaté par l'humain le 2026-10-04, journal Seq à l'appui :
> 1. Dans le client Angular, dossier `Demo/Biologie` ouvert, avec le message UID 10.
> 2. Dans un autre client de messagerie, sur la même boîte, on supprime ce message.
> 3. De retour dans Angular, le message est **toujours dans la liste**, et le rafraîchissement automatique (30 s) ne le retire pas. L'ouvrir affiche un **contenu vide** dans le détail.

## Ce qui est établi (Seq, 2026-10-04 07:56–07:58 UTC ; code de develop)

1. **Le serveur sait que le message a disparu.**
   - À chaque rafraîchissement de `GET /api/v1/mail/folders/Demo%2FBiologie` (200), le `SEARCH` IMAP rend **0 UID** (« Status Count=0, UidNext=11 »).
   - L'API répond donc que le dossier est vide.
   - Au passage : la liste d'UID en cache annonce encore 1 UID à chaque appel (« CACHE INVALIDATED (count 1 vs 0) »). Le résultat frais n'y est pas réécrit, et chaque rafraîchissement refait la lecture IMAP.
2. **Angular ne retire jamais un message disparu.**
   - Le rafraîchissement (`mss-mail.component.ts`, `interval(syncIntervalMs)` puis `getFolder`, vers la ligne 400) calcule les seuls UID **nouveaux** de la page.
   - S'il n'y en a pas, il s'arrête (`return EMPTY`). Un UID qui a quitté le serveur reste affiché indéfiniment.
3. **Blazor, même défaut.** `MailListComponent.RefreshEmailsCoreAsync` ne charge que les `newUids` ; les UID disparus restent à l'écran.
4. **Mobile** : pas de rafraîchissement périodique de la liste, seulement le flux temps réel et le « tirer pour rafraîchir ». Le message disparu reste jusqu'à un rechargement complet.
5. **L'ouverture d'un message disparu rend un contenu vide.**
   - `GET …/emails/10` puis `GET …/emails/content/10` répondent **200** en 17 à 24 ms, **sans aucun accès IMAP** dans la trace.
   - Le contenu est servi depuis la base locale ou le cache, où la ligne du message subsiste.
   - Le client affiche ce contenu vide, sans erreur.

## Objective

Un message qui n'existe plus sur le serveur de messagerie (supprimé ou déplacé depuis un autre logiciel) :
1. **disparaît de la liste** au rafraîchissement suivant, ou au « tirer pour rafraîchir » sur le mobile. Les compteurs du dossier suivent ;
2. **ne s'ouvre jamais sur un contenu vide** : l'ouvrir (avant que la liste ne se soit mise à jour) affiche « Ce message n'existe plus : il a été supprimé ou déplacé depuis un autre logiciel de messagerie. », puis le retire de la liste ;
3. s'il était **ouvert** dans le détail au moment où il disparaît, le détail se referme avec le même message.

Les trois clients se comportent de la même façon.

### Périmètre

1. **API** :
   - `GET …/folders/{dossier}/emails/content/{uid}`, et la lecture des en-têtes par UID, sur un message absent du serveur IMAP : un **404 `problem+json`** reconnaissable comme « message introuvable », jamais un 200 vide. Le `detail` ne contient ni sujet ni chemin de dossier ;
   - la ligne locale d'un message absent du serveur ne sert plus de contenu.
   - Le mécanisme (vérification à l'ouverture, purge des UID disparus à la lecture du dossier, cache) est laissé à `/develop`, sous la contrainte du coût : l'ouverture d'un message reste un chemin chaud (verrou `imap_session`).
2. **Angular et Blazor** : le rafraîchissement du dossier ouvert retire les messages dont l'UID n'est plus rendu par le serveur, ouverture d'un message introuvable comprise.
3. **Mobile** : le « tirer pour rafraîchir » et la réouverture du dossier retirent les messages disparus ; l'ouverture d'un message introuvable suit la même règle.
4. Les **étiquettes** (vues `tag:…`) suivent la même règle pour leurs messages, quand la vue est rafraîchie.

### Hors périmètre

- Notification temps réel d'une suppression faite ailleurs (IMAP IDLE / flux) : suivi.
- Un rafraîchissement périodique de la liste sur le mobile : non demandé. Le « tirer pour rafraîchir » suffit.
- Le cache de liste d'UID non réécrit après une lecture fraîche (« count 1 vs 0 » à chaque appel) : signalé ci-dessus. `/develop` le corrige si c'est la même cause, sinon suivi.

## Definition of Done

- [ ] Build passes (0 errors) et tests pass (0 failures, hors flaky préexistants documentés) sur `api-mail`, `client-angular`, `client-blazor` et `client-mobile`
- [ ] **Tests rouges d'abord** (log des runs rouges dans le task file), sur le code actuel
- [ ] Test d'intégration de bout en bout pour `GET /api/v1/mail/folders/{dossier}/emails/content/{uid}` (règle 1b), vu rouge (règle 1b) :
  - le message a été lu une fois par l'application, puis supprimé sur le serveur IMAP par un autre client ;
  - réponse : 404 `application/problem+json` reconnaissable comme « message introuvable », sans sujet ni chemin de dossier dans le `detail`, lu dans la réponse réelle ;
  - cas nominal : un message présent rend son contenu.
- [ ] Test d'intégration de bout en bout pour la lecture des en-têtes par UID `GET …/emails/{uids}` : le message supprimé n'est pas rendu, les autres le sont. Vu rouge.
- [ ] Test d'intégration pour `GET /api/v1/mail/folders/{dossier}` : après la suppression ailleurs, `uids` ne contient plus le message et le compte suit (non-régression du comportement déjà correct, à garder).
- [ ] Tests de composant, par client (Angular vitest, Blazor bUnit, mobile Jasmine) :
  - le rafraîchissement qui ne rend plus un UID retire le message de la liste ;
  - l'ouverture d'un message « introuvable » affiche le message clair et le retire ;
  - un message ouvert qui disparaît referme le détail avec le message clair.
- [ ] Libellé du message en dur en français sur Angular et mobile, via `Localizer` sur Blazor (FR et EN) ; `data-testid` sur le message
- [ ] Scénario `E2E-MAIL-005` (v1) ajouté à `Api/Mail/e2e/scenarios.yml`, clients **mobile et angular requis**, et implémenté dans les deux suites :
  - un message est affiché dans la liste, puis supprimé **hors de l'application** ;
  - au rafraîchissement (Angular) ou au « tirer pour rafraîchir » (mobile), il n'est plus dans la liste ;
  - l'ouvrir avant la mise à jour affiche le message clair, jamais un contenu vide.
- [ ] **Trou du filet** : `E2E-MAIL-005` prouvé rouge sur le bug non corrigé (Angular : le message reste, contenu vide), ligne ajoutée dans `conventions/e2e.md`
- [ ] `/e2e` vert sur les deux voies, parité verte
- [ ] Aucune donnée de santé dans les journaux (ni sujet, ni contenu, ni chemin de dossier)

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` (profil banc, Dovecot) ; Angular, Blazor et mobile sur une boîte de test ; Thunderbird sur la même boîte.
2. **Disparition au rafraîchissement** :
   - ouvrir `Demo/Biologie` dans l'application, avec un message visible ;
   - le supprimer dans Thunderbird (et vider la corbeille de Thunderbird, ou le déplacer ailleurs) ;
   - attendre le rafraîchissement automatique (30 s) sur Angular et Blazor, ou tirer pour rafraîchir sur mobile.
   - **Attendu** : le message disparaît de la liste et le compteur du dossier baisse. Avant : il restait indéfiniment.
3. **Ouverture avant la mise à jour** : refaire la suppression dans Thunderbird puis, **immédiatement**, cliquer sur le message dans l'application.
   - **Attendu** : « Ce message n'existe plus… », puis le message quitte la liste. Avant : détail vide.
4. **Message ouvert** : ouvrir un message dans l'application, le supprimer dans Thunderbird, attendre le rafraîchissement.
   - **Attendu** : le détail se referme avec le même message clair.
5. **Non-régression** : un message déplacé **depuis l'application** apparaît bien dans le dossier cible ; un nouveau message reçu apparaît toujours au rafraîchissement.
6. Refaire 2 à 4 sur les trois clients.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville, biologie (les comptes rendus reçus sont le contenu le plus exposé)
- **Vague Ségur** : V2
- **Exigences DSR honorées** : non applicable — fiabilité de l'affichage de la messagerie existante. Effet de bord utile : un compte rendu n'apparaît plus « vide » à tort, ce qui évite une lecture clinique erronée.
- **INS** : non applicable — aucune donnée patient manipulée par la US
- **Authentification PS** : inchangée — PSC / e-CPS, session existante
- **Habilitations** : inchangées — la boîte du praticien connecté
- **Interop CI-SIS** : non applicable — opérations IMAP de lecture
- **Tracé PGSSI-S** : inchangé. La lecture d'un message introuvable n'est pas une consultation : aucune trace de lecture (`MailRead`) n'est émise pour un message absent du serveur. Avertissement technique sans sujet ni chemin.
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement inchangé
- **AIPD / impact RGPD** : inchangé. Le retrait local d'un message supprimé côté serveur aligne la base sur le serveur, sans traitement nouveau.

## Branches

- `api-mail` (pushed) : fix/task-353-message-supprime-ailleurs — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-353-message-supprime-ailleurs
- `client-blazor` (pushed) : fix/task-353-message-supprime-ailleurs — https://github.com/codengine-technologies/HealthPlatform.Client/tree/fix/task-353-message-supprime-ailleurs
- `client-mobile` (pushed) : fix/task-353-message-supprime-ailleurs — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/fix/task-353-message-supprime-ailleurs
- `client-angular` (code-only) : la forge écrit sur la branche checked out dans `Client/Angular/` (`feature/nova-rewriting-mss` au /start, task-352 commitée par l'humain) — humain gère branche, commit, push, PR TFS
- `dtos-mss` : aucune branche à ce stade (branche paresseuse, créée par /develop si un contrat bouge)

## Timings

*(généré par `tools/timing/report.sh --task task-353 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 27 s | — | — | — | — |
| **Total cycle** | | **27 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |
