# todo-task-403 — L'accès à la base d'une boîte est ouvert par l'opérateur MSSanté

**Repos**: dtos-mss, api-mail, client-mobile, client-angular
**Dependencies**: task-402 (le rôle du rattachement)
**Epic**: E020

> **Cadre** : CLAUDE.md règle 14, réécrite le 2026-10-28 — « l'opérateur ouvre l'accès ; seule
> exception, le hors-ligne du titulaire ». Cette task est le **verrou** qui doit exister **avant**
> que la task-404 fasse partager la base d'une boîte entre plusieurs personnes : sans lui, partager
> la base donnerait à un délégataire révoqué un accès durable aux données du titulaire.
>
> **Aucune reprise** : registre et bases de dev repartent vides (humain, 2026-10-28).

## Ce qui est établi

- **Verdict de compatibilité** (`Api/Mail/src/Domain/Entities/TenantDb/MailboxCompatibility.cs`) :
  une boîte active reste **sélectionnable et lisible hors ligne** (`NoPscToken`), quelle que soit la
  personne. `AuthFailing` et `Detached` la rendent non sélectionnable.
- **Refus du jeton en cours d'usage** : reconnu par `MailServerTokenRefusal.TryDescribe`
  (`ImapConnectionService`, `SmtpConnectionFactory`, `BackgroundImapService`), qui évince le jeton du
  cache — mais **rien n'est reporté au registre**. Seule la ré-authentification explicite
  (`MailboxManagementService.ReauthenticateAsync` → `MarkAuthenticationOutcomeAsync`) pose
  `AuthFailing`. Une révocation est donc invisible pour l'accès aux données (écart déjà relevé par
  l'audit sécurité E016 du 2026-09-16 : « re-validation AuthFailing jamais câblée »).
- **Redis** sert des données de la boîte (listes, contacts, métadonnées) indexées par adresse : un
  contrôle placé après le cache ne protège rien.

## Objective

Une personne ne lit ni n'écrit les données d'une boîte que si l'opérateur MSSanté lui en a ouvert
l'accès **récemment**. Un refus ou une révocation ferment l'accès, y compris aux données déjà
synchronisées. Seul le **titulaire** garde la lecture hors ligne sur sa boîte personnelle.

## Règles

1. **Verdict de l'opérateur.** Toute authentification XOAUTH2 réussie (IMAP ou SMTP) enregistre un
   verdict favorable pour la paire (personne, boîte). Tout refus du jeton reconnu en cours d'usage
   passe le rattachement en **`AuthFailing`** au registre.
2. **Fenêtre de 5 minutes**, alignée sur la révocation. Pour un **délégataire**, un **membre** ou une
   boîte **« à requalifier »**, toute requête qui touche les données de la boîte exige un verdict de
   moins de 5 minutes. Au-delà, le serveur **renouvelle** le verdict auprès de l'opérateur avant de
   servir ; un échec est un refus.
3. **Refus** : `application/problem+json` 403, code distinct selon la cause — accès révoqué ou refusé
   par l'opérateur, connexion PSC requise. **Aucune donnée servie**, cache Redis compris : le contrôle
   passe **avant** toute lecture.
4. **Hors-ligne** (session sans jeton PSC) :
   - **titulaire** : lecture inchangée (sans envoi ni drapeaux, comme aujourd'hui) ;
   - **délégataire, membre, « à requalifier »** : refus « connexion PSC requise ».
5. **`AuthFailing` ferme tout**, titulaire compris (comportement actuel). On en sort par la
   ré-authentification.
6. **Temps réel** : le flux SSE d'une personne dont l'accès tombe est **fermé**, et la
   synchronisation de fond lancée pour elle s'arrête.
7. **Tâches de fond et consommateurs du bus** : ils travaillent pour la boîte sans rien exposer à une
   personne ; ils ne passent pas par ce verrou et restent des **actes système** (règle 14).
8. **Traces (règle 14)** : refus d'accès, passage en `AuthFailing`, renouvellement refusé — avec la
   personne qui agit, son rôle, la boîte et la cause.

## Definition of Done

- [ ] Build passes (0 errors) sur `dtos-mss`, `api-mail`, `client-mobile`, `client-angular` (code-only)
- [ ] Tests pass (0 failures) sur chaque repo listé
- [ ] Contrat `dtos-mss` : codes de refus et état « accès suspendu » — package publié, consommateurs
      .NET bumpés, types TypeScript mobile et Angular régénérés
- [ ] Unit tests du verdict d'accès : chaque rôle (titulaire, membre, délégataire, à requalifier)
      croisé avec chaque état (en ligne verdict frais, en ligne verdict périmé, hors ligne,
      `AuthFailing`)
- [ ] Test d'intégration de bout en bout : délégataire dont l'opérateur refuse le renouvellement →
      403 problem+json, **aucune donnée** dans la réponse réelle, y compris une liste déjà en cache
      Redis ; rattachement `AuthFailing` relu au registre — vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout : délégataire hors ligne → 403 « connexion PSC requise » ;
      titulaire hors ligne → ses messages lus dans la réponse réelle — vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout : refus du jeton en cours d'usage (IMAP, puis SMTP) →
      `AuthFailing` posé au registre — vu rouge (règle 1b)
- [ ] Test d'intégration : flux SSE fermé après révocation — vu rouge (règle 1b)
- [ ] Test d'intégration : traces de refus lues dans le journal réel (personne, rôle, cause) — vu
      rouge (règle 1b)
- [ ] Mobile et weda2 : écran « accès suspendu » qui dit la cause, sans aucune donnée de la boîte,
      `data-testid` sur tous les éléments interactifs
- [ ] UI component tests : écran « accès suspendu » (rendu de chaque cause + action proposée)
- [ ] **Banc e2e** : le banc sait **refuser une personne donnée sur une boîte donnée** (révocation
      simulée), sans affecter les autres personnes de la même boîte
- [ ] Scénario E2E-MAILBOX-005 (v1, le délégataire révoqué perd l'accès en ligne puis hors ligne ; le
      titulaire garde le sien) ajouté dans Api/Mail/e2e/scenarios.yml, et implémenté dans chaque
      client où il est requis (mobile, angular)
- [ ] Aucune donnée de santé en clair dans les logs (INS, NIR, contenu CDA, contenu MSSanté)
- [ ] Évènements PGSSI-S journalisés : refus d'accès, échec d'authentification opérateur,
      `AuthFailing`

## Manual Test Plan

- Backend e2e : `cd Api/Mail && dotnet run --project src/AppHost` (profil `e2e`)
- Mobile : `cd Client/Mobile && npm start` → http://localhost:4200 ; weda2 via le faux hôte e2e
- Le titulaire e2e et le délégataire e2e sont rattachés à `boite-praticien` (task-402).
- Le délégataire lit la boîte. Révocation simulée sur le banc → en moins de 5 minutes, l'écran passe
  à « Accès suspendu — accès retiré par la messagerie » ; plus aucun message ne s'affiche, même en
  revenant sur un dossier déjà ouvert.
- Le titulaire continue de lire. Couper sa session PSC → lecture hors ligne maintenue, envoi
  indisponible.
- Délégataire sans session PSC → « Connexion Pro Santé Connect requise ».
- Écran Audit de weda2 : refus et révocation tracés au nom du délégataire.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — contrôle d'accès interne, sans exigence DSR publiée
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — aucune donnée patient n'est ajoutée ; l'accès à celles qui existent est
  restreint
- **Authentification PS** : PSC / e-CPS, eIDAS substantiel ; l'opérateur MSSanté reste juge par
  XOAUTH2. Hors-ligne réservé au titulaire
- **Habilitations** : rôle du rattachement (task-402) et verdict de l'opérateur de moins de 5 minutes
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : refus d'accès, échec d'authentification, `AuthFailing` — personne, rôle, boîte,
  cause. Conservation inchangée
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé
- **AIPD / impact RGPD** : à mettre à jour — la révocation d'une délégation coupe l'accès aux données
  déjà synchronisées

## Branches

- `dtos-mss` (lazy) : aucune branche au /start — `/develop` la crée au premier contrat touché
- `client-angular` (code-only) : la forge écrit sur la branche courante de `Client/Angular/` ;
  l'humain gère branche, commit, push et PR TFS
