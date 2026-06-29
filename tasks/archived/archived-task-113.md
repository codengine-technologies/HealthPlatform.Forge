# todo-task-113.md — Dashboard d'accueil mobile `home` (miroir Angular MSS)

**Repos**: client-mobile
**Dependencies**: done-task-110
**Single frontend**: true
**Epic**: E014

## Branches
- `client-mobile` (pushed) : feat/task-113-refonte-home-stitch — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-113-refonte-home-stitch

## Objective
Transformer l'écran `home` — aujourd'hui un **placeholder orphelin** du starter
Ionic, non routé — en un véritable **tableau de bord d'accueil**, **miroir du
dashboard de l'application Angular** (`libs/mss/src/features/dashboard/mss-dashboard`),
adapté au mobile (colonne unique empilée). Cohérent avec la philosophie E012
(client-mobile = miroir structurel de client-angular).

Le dashboard devient la **page d'atterrissage post-login** : après connexion PSC,
l'app arrive sur `/home` (dashboard) au lieu d'`/inbox`. Depuis le dashboard, le
praticien accède à la messagerie et aux raccourcis cliniques.

`client-mobile` **uniquement** — agrégation **client-side** de l'état mail
existant (signals `MailStateService`), **aucun changement backend / dtos**.

## Référence design (Angular + Stitch)
- **Angular** : `mss-dashboard.component` — hub 3 colonnes : Messagerie (stats +
  tag cloud), « Résumé des mails non lus du jour », Biologie (KPI en attente
  d'acquittement + résultats anormaux), « Patients avec mails non lus ». Nav
  latérale : Tableau de bord / Messagerie / Contacts / Modèles / Patient / Audit /
  Paramètres.
- **Stitch** : écran `home` du projet `client-mobile` (à produire/mettre à jour
  par `/stitch-design`) — version mobile colonne unique du dashboard ci-dessus.

## Périmètre mobile (sections retenues)
Adaptation mobile, **colonne unique**, alimentée par l'état mail déjà chargé :

1. **En-tête de marque** « 🔒 MSSanté ».
2. **Bloc Messagerie** — stats : **Total** / **Non lus** / **Non lus aujourd'hui**
   (dérivés de `folders[].unreadCount` + `emails[].sentDate`/`isRead`). Bouton
   **« Accéder à ma messagerie »** → `/inbox`.
3. **Résumé des mails non lus du jour** — liste compacte (expéditeur, objet,
   heure) des emails `!isRead` et `sentDate == aujourd'hui` ; tap → ouvre le
   mail (`/mail/:folderPath/:uid`). État vide explicite si aucun.
4. **Biologie** — tuile KPI **« Résultats en attente d'acquittement »**
   (count = mails avec `pendingBiologyAcksCount > 0`, dont **critiques** mis en
   avant via `hasCriticalPendingBiologyAck`) + **« Résultats anormaux »**
   (count `hasAbnormalBiology`). Tap → `/inbox` (filtre biologie existant).

## Hors périmètre (justifié)
- **« Patients avec mails non lus »** (widget Angular) : **différé**. L'identité
  patient n'est pas sur `MailDto` en liste (lazy dans `MailContentDto`), et
  l'INS ne doit **jamais** être affichée en clair (garde-fou). Une version
  fidèle exigerait un **endpoint dashboard backend** (agrégation patient) →
  US backend dédiée ultérieure. Non implémenté ici.
- **Nav latérale Angular** (Contacts, Modèles, Patient, Audit, Paramètres) :
  ces écrans **n'existent pas** dans l'app mobile (scope E012). On **n'ajoute
  pas** de tab bar / liens vers des écrans inexistants (pas de lien mort). Les
  seuls liens du dashboard pointent vers ce qui existe : `/inbox` (et le détail
  mail).
- **Tag cloud** Angular : non repris (pas de navigation par tag sur mobile).

## Navigation
- `home` est **routé** (`app-routing.module.ts`) et devient la **landing
  post-login** : `AuthService.loginPsc` / le callback redirigent vers `/home`
  (au lieu de `/inbox`). `/inbox` reste accessible depuis le dashboard.

## Stitch design log
- Project : client-mobile (id 10088502293310567548)
- Écran dashboard **produit** via `edit_screens` (sur retour humain : transformer
  `home` en dashboard miroir Angular).
  | Composant | Titre Stitch | Screen id | Action |
  |---|---|---|---|
  | home | **Dashboard Accueil** | 83399bfa940a4e36ba56d66e3b210e76 | **created** |
- Rendu validé (screenshot) : header « 🔒 MSSanté » ; MESSAGERIE (3 stat cards
  Total/Non lus/Aujourd'hui + bouton « Accéder à ma messagerie ») ; MAILS NON LUS
  DU JOUR (liste avatar/expéditeur/objet/heure/point non-lu) ; BIOLOGIE (tuile
  « En attente d'acquittement » + chip « critiques », tuile « Résultats anormaux »
  en rouge). Pas de tab bar, pas d'Annuaire/Documents (conforme au périmètre).
- ⚠ **Housekeeping Stitch (UI humaine, MCP sans rename/delete)** :
  - renommer l'écran **« Dashboard Accueil » → `home`** (convention titre = nom
    kebab du composant) ;
  - supprimer l'ancien écran `home` générique (id 8c3d240e346f42f8a4bbd55c57f98a70,
    welcome + Annuaire/Documents/tab bar) devenu obsolète.

## Simplify log
- `/forge-simplify` (2026-06-23) — repo touché : `client-mobile`. **Skip clean**
  (rien de matériel à simplifier). Reuse écarté : `MailStateService` ne peut pas
  alimenter une landing page (signals vides tant que l'inbox n'a pas été visité)
  → agrégation directe via `MssApiService` requise, pas une simplification.
  Build + 116 tests verts inchangés. Aucun commit.

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/17
  — label `awaiting-human-merge` (HAG, règle 10).

## Code Review Summary
- **Verdict : APPROVED** (7 fichiers, 1 suggestion non bloquante, 0 blocker).
- Build ✅ (0 erreur) · Tests ✅ (116 passed) · Lint ✅ (all files pass).
- Suggestion : compteurs bio critiques/anormaux dérivés de l'échantillon récent
  (30 derniers UIDs), pas de l'inbox entière — approximation d'affichage
  documentée ; comptage exact = endpoint dashboard backend (US ultérieure).
- Aucune INS / donnée de santé en clair.

## Lint mobile log
- `/lint-mobile` (2026-06-23) — `ng lint` baseline : **All files pass linting**.
  0 erreur, 0 warning, aucun fix nécessaire. Aucun commit.

## Definition of Done
- [ ] Build passe : `cd Client/Mobile && npm ci && npm run build` (0 erreur)
- [ ] Tests passent : `npm test -- --watch=false --browsers=ChromeHeadless` (0 échec)
- [ ] `home` routé dans `app-routing.module.ts` et défini comme landing post-login
      (login/callback → `/home`)
- [ ] Section **Messagerie** : stats Total / Non lus / Non lus aujourd'hui
      correctes (dérivées de l'état), bouton → `/inbox`
- [ ] Section **Résumé non lus du jour** : liste correcte + tap ouvre le mail +
      état vide géré
- [ ] Section **Biologie** : KPI en attente d'acquittement (+ critiques) et
      résultats anormaux, tap → `/inbox`
- [ ] Aucun lien mort ; aucune nav vers un écran inexistant
- [ ] Aucun INS / donnée de santé en clair dans l'UI ou les logs
- [ ] 100% tokens du socle (task-110) ; `data-testid` sur les éléments interactifs
- [ ] Aucun changement backend / dtos ; agrégation client-side uniquement
- [ ] `home.page.spec.ts` toujours vert (adapté si besoin : injection de l'état)
- [ ] Component test : rendu du dashboard avec un état mail simulé (stats + listes)

## Manual Test Plan
- Lancer : `cd Client/Mobile && npm start`. Se connecter (PSC).
- Vérifier l'arrivée sur le **dashboard `/home`** (et non directement l'inbox).
- Vérifier : en-tête marque, stats Messagerie cohérentes avec l'inbox, résumé des
  non-lus du jour (ou état vide), tuiles Biologie (en attente / anormaux).
- Taper « Accéder à ma messagerie » → arrive sur `/inbox`.
- Taper un mail du résumé → ouvre le détail.
- Taper une tuile Biologie → arrive sur `/inbox`.
- Comparer la structure à la maquette Stitch `home` et au dashboard Angular.

## Conformité santé / Ségur / ANS
- **Couloir / Vague Ségur** : hors couloir / hors Ségur — UX d'accueil (agrégation
  d'affichage de la messagerie existante).
- **INS** : **aucune INS affichée** (le widget patient, qui en aurait eu besoin,
  est explicitement hors périmètre). Aucune donnée de santé en clair.
- **DSR / Authentification / Habilitations / Interop / PGSSI-S / Consentement /
  Référentiels / HDS / RGPD** : non applicable — agrégation d'affichage côté
  client, aucun nouvel échange ni traitement.

## Merged
- `client-mobile` PR [#17](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/17)
  — squash-merge `cfffcc147b8597e5ab0ac4d11e5217e3c5629adf` sur `develop` le
  2026-06-23 (validation humaine `--i-tested`). Branche distante supprimée,
  branche locale conservée. CI : aucun check configuré sur le repo.
