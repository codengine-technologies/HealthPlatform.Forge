# todo-task-139.md — Brouillons sur mobile (auto-save, reprise, dossier Brouillons)

**Repos**: client-mobile
**Dependencies**: —
**Epic**: E012

## Objective

Porter sur `client-mobile` la gestion des **brouillons** de `client-angular` :
sauvegarde automatique du compose toutes les **30 s** (pas de bouton manuel),
reprise d'un brouillon depuis le **dossier Brouillons** (virtuel, Redis côté
serveur), suppression, et envoi d'un brouillon. Le mobile possède déjà les
modèles TS (`core/models/draft.model.ts`) mais **aucune API ni UI**.

US **frontend-only** : endpoints existants (`saveDraft`, `updateDraft`,
`getDrafts`, `getDraft`, `deleteDraft`, `sendDraft` — cf. Angular
`mss-api.service.ts:2077-2148`). Aucun changement backend ni DTO.

## Comportement attendu (parité Angular)

- Compose ouvert avec du contenu (destinataire, objet ou corps non vides) →
  auto-save 30 s : création au premier cycle, `updateDraft` ensuite.
- Fermeture du compose avec contenu non envoyé → brouillon conservé.
- Dossier **Brouillons** dans `mail-folder-list` : liste les brouillons
  (objet, destinataires, date) avec compteur.
- Tap sur un brouillon → réouverture du compose pré-rempli (To/Cc/Cci, objet,
  corps HTML, PJ conservées côté serveur).
- Envoi d'un brouillon (`sendDraft`) → disparaît des Brouillons, apparaît dans
  Envoyés. Suppression (swipe) → confirmation → `deleteDraft`.
- Envoi normal d'un compose auto-sauvegardé → le brouillon intermédiaire est
  nettoyé (pas d'orphelin).

## Definition of Done

- [ ] Build passe (`npm ci && npm run build`) — 0 erreur
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`) — 0 échec
- [ ] `MssApiService` : 6 méthodes drafts + tests unitaires (succès + erreur)
- [ ] Auto-save 30 s dans `mail-compose` (création puis update) — testé avec timers fake
- [ ] Dossier Brouillons visible dans la liste des dossiers avec compteur
- [ ] Reprise d'un brouillon : compose pré-rempli fidèlement (To/Cc/Cci, objet, corps, PJ)
- [ ] Envoi de brouillon + nettoyage du brouillon après envoi normal (pas d'orphelin)
- [ ] Suppression avec confirmation (swipe)
- [ ] Libellés FR en dur ; `data-testid` sur liste brouillons, actions
- [ ] Aucun contenu de courrier dans les logs client

## Manual Test Plan

- `cd Client/Mobile && npm start`
- Composer un message (objet + corps), attendre ~35 s sans envoyer, fermer le compose
- Ouvrir le dossier **Brouillons** → le brouillon apparaît
- Le rouvrir → champs restaurés à l'identique ; modifier, attendre 35 s → update (pas de doublon)
- L'envoyer → disparaît des Brouillons, visible dans Envoyés
- Créer un second brouillon, le supprimer par swipe → confirmation → disparu
- Composer et envoyer directement → aucun brouillon orphelin ne reste

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors DSR nouvelle — parité d'une capacité web existante
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — pas de manipulation d'INS spécifique aux brouillons
- **Authentification PS** : session existante, inchangée
- **Habilitations** : inchangées — brouillons cloisonnés par praticien (garantie backend task-023)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : cycle de vie des brouillons géré côté serveur (canal existant) ; aucun log client du contenu
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — brouillons stockés côté serveur (Redis backend HDS), pas de persistance locale mobile
- **AIPD / impact RGPD** : inchangé

## Branches
- `client-mobile` (pushed) : feat/task-139-mobile-drafts — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-139-mobile-drafts

## Stitch design log

- Project : client-mobile (id 10088502293310567548)
- Screens :
  | Component / Page | Stitch title | Screen id | Action | Screenshot |
  |---|---|---|---|---|
  | mail-folder-list (entrée Brouillons + badge) | mail-folder-list | 84138523de2c40c1aa866c64bb5ef84d | reused | https://lh3.googleusercontent.com/aida/AP1WRLsTDXXw5luBQiJD7II2d66fJfmlRL1nHBQitx65PTd21Hkdfqzppk8GHO7Q7fXExu26SGfgOZhGu7CJk5E_DzOOGLujJkDpPNTEudjAqAAyEbUFk37d6IjltJp_GH-enDJ2dbRzSVMmSD2TZZSV2mESP6XYeQ8skWHTStBEGcEKNRL-pKY4pLRdc4aUO_FcWpUZygGz2D9nJ6Xp7S6dYRVh2iaJfwCvuLETU-8mWYkrALUTvT6VqVp38tRX |
  | mail-compose (auto-save 30 s — pas de changement visuel majeur, indicateur discret) | mail-compose | 340f18be9395435f8fc472e0c476f736 | reused | https://lh3.googleusercontent.com/aida/AP1WRLvyMPn0Tx43j94UDZ5P-9z1pkfxN9mtioVW-_1NB035wUscDInZxdza3wb9h3T6h3vZ0DzaIpTF6v9UisVvqByDZ7AbY-XQmBenh9sRqvlilCosCE0T69Pn9c6lxllpxHx3Xq20rvHNzfoMqCn0YscFuntgCX60s39yhpGZLm6mrx5vV0csP-GwbtU33zo0Uqhh0aB-2XIX4I9Ldph4yWvs9fiR1tigeRJsLmvsLuMYw8IIR8y6ipXfgx7u |
  | mail-draft-list (nouvel écran — liste des brouillons) | mail-draft-list | — | **génération non matérialisée** | — |
- Génération `mail-draft-list` : `generate_screen_from_text` a timeouté (attendu), mais **aucun nouvel écran détecté** par diff `get_project` après 2 tentatives espacées (~3 et ~20 min). Conformément au protocole : pas de re-génération (anti-doublon), implémentation faite sans référence, à partir des conventions « Clinical Precision » (listes denses 56 px, séparateurs 1 px, Public Sans).
- Prompt de génération à rejouer manuellement dans l'UI Stitch si souhaité :
  > mail-draft-list — titre exact de l'écran : « mail-draft-list ». Écran de la liste des brouillons (dossier « Brouillons ») du client mobile de messagerie sécurisée de santé MSSanté (application Ionic, design system « Clinical Precision », Public Sans, primaire #005EB8, libellés en français). Layout mobile 390px : header avec flèche retour, titre « Brouillons » et badge compteur du nombre de brouillons. Liste dense de lignes de brouillons (hauteur min 56px, séparateurs 1px) : chaque ligne montre l'objet du brouillon en semi-bold (ou « (Sans objet) » en gris italique si vide), en dessous la ligne des destinataires (adresses ou noms, tronquée avec ellipsis), et à droite la date/heure de dernière modification en caption grise. Une ligne du milieu est représentée en cours de swipe vers la gauche révélant une action rouge « Supprimer » avec icône corbeille. En bas de liste, un état visuellement discret. Bouton flottant (FAB) primaire en bas à droite pour composer un nouveau message. Cohérent avec les autres écrans du projet client-mobile (inbox, mail-list, mail-folder-list).
- ⚠ Rename / labelliser in Stitch UI : si la génération finit par se matérialiser, vérifier le titre `mail-draft-list` et labelliser l'instance
- ⚠ Doublons suspectés à nettoyer dans l'UI : ceux de task-137 (déjà signalés, instances hidden) — inchangé
- Stitch reachable : ✓ (génération lancée, non matérialisée — prompt inclus ci-dessus pour run manuel)

## Develop log

- Repos touched : client-mobile (US frontend-only)
- DTOs published : no DTO change
- Interop published : no interop change
- Commits :
  - client-mobile : d4994ba feat(mobile): brouillons — auto-save 30 s, dossier Brouillons, reprise, envoi (task-139)
- Local build / test : ✓ `npm run build` 0 erreur ; `npm test -- --watch=false --browsers=ChromeHeadless` 367/367 SUCCESS (+32)
- DOD self-check : 10/10 items vérifiables vérifiés
  - build ✓, tests ✓ ; 6 méthodes drafts `MssApiService` + tests succès/erreur ✓ ;
    auto-save 30 s création-puis-update testé fakeAsync (tick 30 000, pas de
    doublon, pas de save à vide) ✓ ; dossier Brouillons dans l'arbre
    (imapFolders admet FolderSource.Drafts, badge = count total) ✓ ; reprise
    pré-remplie fidèle (To/Cc/Cci, objet, corps HTML, PJ serveur en
    carriedOver) ✓ ; envoi de brouillon via `sendDraft` (nettoyage serveur
    atomique) + fermeture avec contenu → brouillon conservé + suppression
    externe → pas de résurrection ✓ (testés) ; suppression swipe avec
    confirmation AlertController ✓ (confirm/cancel/erreur testés) ; FR en dur +
    data-testid (draft-item/-delete/-date, draft-list-empty,
    compose-draft-saved) ✓ ; aucun contenu de courrier loggé (0 console.*) ✓
  - validation visuelle end-to-end : deferred to manual test (HAG)
- Choix documentés :
  - Composant dédié `mail-draft-list` (Angular réutilise mail-list avec des
    MailDto synthétiques ; sur mobile mail-list est couplé aux actions IMAP
    uid — un composant dédié est plus sûr et colle à la convention Stitch
    « 1 écran = 1 composant »)
  - Envoi d'un compose adossé à un brouillon **avec PJ locale (base64)** :
    repli `sendMail` + `deleteDraft` (SaveDraftDto ne transporte pas les PJ —
    le chemin `sendDraft` seul les perdrait, gap présent côté Angular) ; sans
    PJ locale : `sendDraft` (nettoyage atomique). Pas d'orphelin dans les 2 cas
  - Parité Angular assumée : les PJ ne sont PAS persistées dans le brouillon
    (`buildSaveDraftDto` sans attachmentIds) ; la reprise restaure ce que le
    serveur renvoie (`draft.attachments`, en pratique vide) — gap connu côté
    web, non corrigé ici (hors scope US)
  - `formatRowDate` extrait de mail-header vers `core/utils/row-date.util.ts`
    (réutilisé par mail-draft-list, +tests)
- Next step : /forge-simplify task-139

## Simplify log
- Repos passed : client-mobile
- Applied & committed : client-mobile: 3 files (ec0f1de)
  - simplification/altitude : algorithme de persistance du brouillon factorisé en `persistDraft(notify)` (saveDraftNow / fermeture — la règle POST-création/PUT-update ne vit plus qu'à un endroit) ; `fetchDraftsInto(folderPath)` partagé par loadDraftsFolder/refreshDrafts (inbox)
  - efficiency : `draftSent$` émis à la **création** et à la **fermeture** seulement, plus à chaque PUT du cycle 30 s — supprime un GET /drafts par tick d'auto-save par compose ouvert (le badge ne changeait pas) ; test dédié ajouté (création émet, PUT silencieux, fermeture notifie)
- No change (skips motivés) : PUT-upsert systématique sans POST (dépend du contrat backend non vérifié, rompt la parité Angular — noté pour plus tard) ; split de `draftSent$` en deux évènements (le gating suffit) ; extraction `buildFallbackGuid` en util (aucun autre consommateur) ; reuse : clean (l'extraction `row-date.util` saluée par l'agent)
- Rolled back (validation RED) : none
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*
- Build / tests : ✓ `npm run build` 0 erreur ; 367/367 tests SUCCESS

## Lint mobile log
- Baseline : 0 error / 0 warning — « All files pass linting »
- Iterations : 0 (rien à corriger)
- Fixes committed : none
- Residual : none
- Build / tests : inchangés depuis la passe simplify (build ✓, 367/367 ✓)

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/43 — label `awaiting-human-merge`

## Code Review Summary
- Verdict : **APPROVED** (0 blocking)
- 22 fichiers reviewés (diff complet vs origin/develop), review indépendante « second développeur »
- Points validés : parité endpoints Angular (verbes/URLs vérifiés jusqu'au backend), cycle de vie des subscriptions (takeUntilDestroyed + unsubscribe explicite de l'auto-save, garde de réentrance isSavingDraft, auto-save inhibé pendant l'envoi), dossier virtuel servi par getFolders() (feature atteignable), aucun trait/contenu de courrier loggé
- Suggestions non bloquantes : commentaire POST/PUT imprécis dans persistDraft (PUT backend = upsert, comportement correct) ; course théorique faible si réouverture d'un compose pendant la persistance de fermeture (best-effort accepté) ; scintillement cosmétique possible du badge sur le chemin sendMail+deleteDraft
- Validation finale : build ✓ (0 erreur), 367/367 tests ✓, lint ✓ (0 erreur)
- Commits : d4994ba (feat), ec0f1de (refactor /simplify)

## Merged
- Date : 2026-07-07
- `client-mobile` : squash `611c7f5996dc9c7a5c42814c95168f719fa7a5e5` (PR #43 closed, remote branch deleted, local branch kept)
- develop CI : ✓ green — https://github.com/codengine-technologies/HealthPlatform.Mobile/actions/runs/28851921881
