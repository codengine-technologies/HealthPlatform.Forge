# todo-task-352.md — Ouvrir un dossier supprimé depuis un autre logiciel : un message clair et un retour à la boîte de réception, plus jamais un chargement sans fin

**Repos**: api-mail, client-angular, client-blazor, client-mobile
**Dependencies**: — (aucune ; task-339, PR #272, touche la même zone côté serveur, sans dépendance fonctionnelle)
**Epic**: E009
**Priorité**: **2** — sur Angular, le praticien reste bloqué devant un chargement sans fin. Il doit changer de dossier pour sortir de l'impasse, sans savoir que le dossier n'existe plus. Le cas est courant : une boîte MSSanté est souvent ouverte aussi dans un autre logiciel (LPS, webmail de l'opérateur).

> **Origine.** Bug constaté par l'humain le 2026-10-04, journal Seq à l'appui :
> 1. Dans le client Angular, la vue e-mail et la liste des dossiers sont chargées, avec le dossier `Demo/Demo2` visible.
> 2. Dans un autre client de messagerie, sur la même boîte, on supprime `Demo2`.
> 3. De retour dans Angular, un clic sur `Demo2` laisse un **spinner sans fin** dans la liste des e-mails.

## Ce qui est établi (Seq, 2026-10-04 07:43:46 UTC ; code de develop)

1. **Serveur** :
   - `GET /api/v1/mail/folders/Demo%2FDemo2` : le serveur IMAP répond `NO Mailbox doesn't exist` au `STATUS`.
   - L'API se répare d'elle-même (« IMAP folder … no longer exists - cleaning up local state » : ligne dossier et mails locaux retirés, liste des dossiers en cache invalidée).
   - Elle rend ensuite **404 avec un corps vide** (`Size=0`, `result.ToActionResult(this)` dans `MailController.GetFolderAsync`). Ce n'est pas du `problem+json` (règle 12), et rien ne permet à un client de distinguer « dossier disparu » d'un autre 404.
2. **Angular** (`libs/mss/src/features/mail/mss-mail.component.ts`) :
   - au changement de dossier, `isLoading.set(true)` puis `getFolder(...).subscribe(next)` **sans gestionnaire d'erreur**. Le 404 laisse le chargement allumé indéfiniment, n'affiche aucun message, et `Demo2` reste dans la liste des dossiers ;
   - le rafraîchissement périodique du dossier ouvert (`getFolder` vers la ligne 401) ne traite pas davantage le cas.
3. **Mobile** (`src/app/inbox/inbox.page.ts`) : l'erreur est attrapée et le chargement s'arrête, mais le message affiché est le texte technique brut (« Http failure response … 404 »), et le dossier fantôme reste dans la liste.
4. **Blazor** (`Application/Services/FolderService.GetFolderAsync`) : l'erreur devient un « Failed to get folder » générique, et le dossier fantôme reste dans la liste.

## Objective

Quand le praticien ouvre un dossier qui n'existe plus sur le serveur de messagerie (supprimé ou renommé depuis un autre logiciel), ou quand le dossier ouvert disparaît pendant la consultation, les **trois clients** :
1. arrêtent le chargement ;
2. affichent un message clair : « Ce dossier n'existe plus : il a été supprimé ou renommé depuis un autre logiciel de messagerie. » ;
3. rafraîchissent la liste des dossiers, où le dossier disparu n'apparaît plus ;
4. ramènent le praticien sur la **Boîte de réception**.

### Périmètre

1. **API** : `GET /api/v1/mail/folders/{dossier}` sur un dossier absent du serveur rend un **404 `problem+json`** que les clients peuvent reconnaître comme « dossier introuvable » (titre ou type stable, sans le chemin du dossier dans le `detail`). Le nettoyage local existant (ligne dossier, mails, cache de la liste) est conservé.
2. **Angular** :
   - ouverture d'un dossier disparu : comportement de l'objectif ;
   - dossier ouvert qui disparaît, constaté au rafraîchissement suivant : même comportement, et le message éventuellement ouvert est refermé avec le dossier ;
   - toute autre erreur de chargement arrête aussi le chargement, avec un message générique, et ne laisse jamais de spinner sans fin.
3. **Mobile** : même comportement, à l'ouverture et au rafraîchissement du dossier ouvert ; plus de message technique brut.
4. **Blazor** : même comportement, à l'ouverture et au rafraîchissement du dossier ouvert.
5. Les **étiquettes** (vues `tag:…`) et le dossier virtuel **Brouillons** ne sont pas concernés : ce ne sont pas des dossiers IMAP.

### Hors périmètre

- Détecter la suppression **avant** le clic (notification temps réel de la structure des dossiers) : suivi.
- Retrouver automatiquement le nouveau nom d'un dossier renommé ailleurs.
- Les autres routes d'un dossier disparu (lecture d'un message, déplacement vers lui) : leur comportement d'erreur actuel n'est pas modifié, sauf s'il laisse un chargement sans fin dans le même parcours (alors corrigé ici).

## Definition of Done

- [ ] Build passes (0 errors) et tests pass (0 failures, hors flaky préexistants documentés) sur `api-mail`, `client-angular`, `client-blazor` et `client-mobile` (commandes de la table des repos)
- [ ] **Tests rouges d'abord** (log des runs rouges dans le task file), sur le code actuel
- [ ] Test d'intégration de bout en bout pour `GET /api/v1/mail/folders/{dossier}` (règle 1b) :
  - un dossier supprimé sur le serveur IMAP après avoir été listé rend un 404 `application/problem+json`, reconnaissable comme « dossier introuvable », sans le chemin du dossier dans le `detail`, lu dans la réponse réelle ;
  - le nettoyage local a eu lieu : la liste des dossiers suivante ne contient plus le dossier ;
  - cas nominal : un dossier existant rend 200 ;
  - test vu rouge (règle 1b).
- [ ] Tests de composant, par client (Angular vitest, Blazor bUnit, mobile Jasmine) :
  - ouverture d'un dossier qui répond « dossier introuvable » : chargement arrêté, message clair affiché, liste des dossiers rechargée, Boîte de réception sélectionnée ;
  - même chose quand le rafraîchissement du dossier ouvert répond « dossier introuvable » ;
  - toute autre erreur à l'ouverture : chargement arrêté, message générique, aucune redirection.
- [ ] Libellé du message en dur en français sur Angular et mobile (convention actuelle), via `Localizer` sur Blazor (FR et EN) ; `data-testid` sur le message
- [ ] Scénario `E2E-FOLDER-003` (v1) ajouté à `Api/Mail/e2e/scenarios.yml`, clients **mobile et angular requis**, et implémenté dans les deux suites :
  - le dossier est créé, listé, puis supprimé **hors de l'application** ;
  - son ouverture affiche le message, le dossier n'est plus dans la liste et la Boîte de réception est affichée.
- [ ] **Trou du filet** : `E2E-FOLDER-003` prouvé rouge sur le bug non corrigé (Angular : spinner sans fin), ligne ajoutée dans `conventions/e2e.md`
- [ ] `/e2e` vert sur les deux voies, parité verte
- [ ] Aucune donnée de santé dans les journaux, ni le nom du dossier dans le `detail` de l'erreur : un nom de dossier peut nommer un patient

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` (profil banc, Dovecot) ; Angular, Blazor et mobile sur une boîte de test ; un client IMAP tiers (Thunderbird) sur la même boîte.
2. **Ouverture d'un dossier disparu** :
   - dans l'application, ouvrir la vue e-mail : la liste des dossiers montre `Demo/Demo2` ;
   - dans Thunderbird, supprimer `Demo2` ;
   - revenir dans l'application et cliquer sur `Demo2`.
   - **Attendu** : le chargement s'arrête aussitôt, le message « Ce dossier n'existe plus… » s'affiche, `Demo2` disparaît de la liste et la Boîte de réception s'affiche. Avant : spinner sans fin sur Angular, message technique sur mobile et Blazor.
3. **Dossier ouvert qui disparaît** :
   - ouvrir `Demo3` dans l'application (avec un message ouvert) ;
   - le supprimer dans Thunderbird ;
   - attendre le rafraîchissement, ou le provoquer.
   - **Attendu** : même message, `Demo3` disparaît de la liste, retour à la Boîte de réception.
4. **Non-régression** : ouvrir un dossier existant, une étiquette (« BIO ») et les Brouillons : aucun message, aucun changement.
5. Refaire 2 et 3 sur les trois clients.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR honorées** : non applicable — robustesse de l'interface de messagerie existante, aucune exigence nouvelle
- **INS** : non applicable — aucune donnée patient manipulée
- **Authentification PS** : inchangée — PSC / e-CPS, session existante
- **Habilitations** : inchangées — la boîte du praticien connecté
- **Interop CI-SIS** : non applicable — opérations IMAP de structure de boîte
- **Tracé PGSSI-S** : inchangé. L'échec d'ouverture est journalisé en avertissement technique, sans chemin de dossier ni contenu de message (un nom de dossier peut nommer un patient). Le message d'erreur rendu au client ne porte pas le chemin.
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement inchangé
- **AIPD / impact RGPD** : inchangé — aucun traitement nouveau ; le nettoyage local des mails d'un dossier disparu existe déjà

## Branches

- `api-mail` (pushed) : fix/task-352-dossier-supprime-ailleurs — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-352-dossier-supprime-ailleurs
- `client-blazor` (pushed) : fix/task-352-dossier-supprime-ailleurs — https://github.com/codengine-technologies/HealthPlatform.Client/tree/fix/task-352-dossier-supprime-ailleurs
- `client-mobile` (pushed) : fix/task-352-dossier-supprime-ailleurs — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/fix/task-352-dossier-supprime-ailleurs
- `client-angular` (code-only) : la forge écrit sur la branche checked out dans `Client/Angular/` (`feature/nova-rewriting-mss` au /start) — humain gère branche, commit, push, PR TFS
- `dtos-mss` : aucune branche à ce stade (branche paresseuse, créée par /develop si un contrat bouge)
