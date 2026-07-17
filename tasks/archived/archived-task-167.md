# todo-task-167.md — Onboarding MSSanté : l'opt-in ne se déclenche pas si le token a un `email` mais pas de `mssEmail`

**Repos**: client-mobile
**Dependencies**: done-task-159
**Epic**: E012

## Objective

Corriger un bug de l'**onboarding MSSanté mobile** (task-159) : quand le jeton
d'accès arrive **sans claim `mssEmail`** (boîte MSSanté non configurée) mais
**avec un claim `email`** classique, l'écran d'onboarding
(`/mss-unconfigured`) **ne se déclenche pas**. Le PS est routé vers la coquille
configurée alors que sa boîte MSSanté n'existe pas → appels mail/MSS en erreur
et mauvaise adresse envoyée au backend.

## Cause racine (identifiée)

La décision d'onboarding repose sur `userEmail`, qui a un **fallback trompeur**
vers le claim `email` :

- [session.model.ts:41](../../Client/Mobile/src/app/core/auth/session.model.ts#L41) :
  ```ts
  userEmail: jwtPayload['mssEmail'] ?? jwtPayload['email'] ?? ''
  ```
- [auth-session.service.ts:40-43](../../Client/Mobile/src/app/core/auth/auth-session.service.ts#L40-L43) :
  ```ts
  get needsMssOnboarding() { return !!accessToken && !userEmail; }
  ```

Si `mssEmail` est absent mais `email` présent, `userEmail` = `email` (non vide)
→ `needsMssOnboarding` = **false** → `mssConfiguredGuard` laisse passer, et
`mssOnboardingGuard` (via `isAuthenticated`, lui aussi basé sur `userEmail`)
considère la session « complète ». L'opt-in est donc court-circuité.

Effet de bord : l'intercepteur envoie `Client-Email: userEmail` (=`email`) à
`api-mail` — la mauvaise adresse — au lieu de bloquer avant configuration.

La décision « boîte MSSanté configurée ? » doit reposer **strictement sur la
présence du claim `mssEmail`**, jamais sur un `userEmail` doté d'un fallback.

## Comportement attendu

1. **Onboarding déclenché sur `mssEmail` absent** : un jeton présent **sans**
   `mssEmail` (peu importe la présence d'un `email`) → session « token-only » →
   `needsMssOnboarding` = **true** → redirection `/mss-unconfigured`.
2. **Session complète = `mssEmail` présent** : `isAuthenticated` /
   session « configurée » exigent le `mssEmail`, pas un `email` de repli.
3. **En-tête backend correct** : tant que la boîte n'est pas configurée,
   aucun appel mail/MSS n'est émis (garde d'onboarding) ; une fois configurée,
   `Client-Email` porte bien l'adresse **MSSanté**.
4. **Non-régression task-159** : un jeton **avec** `mssEmail` accède normalement
   à la coquille `ion-tabs` ; l'absence totale de jeton → `/login`.

## Definition of Done

- [ ] Build passe (`npm run build`) — 0 erreur
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`) — 0 échec
- [ ] La présence d'adresse MSSanté est dérivée **strictement** du claim `mssEmail` (champ dédié, sans fallback `email`) et pilote `needsMssOnboarding` / `isAuthenticated`
- [ ] Test unitaire : token avec `email` **mais sans** `mssEmail` → `needsMssOnboarding === true` (le cœur du bug)
- [ ] Test unitaire : token avec `mssEmail` → `needsMssOnboarding === false`, `isAuthenticated === true`
- [ ] Test unitaire guard : session token-only (email sans mssEmail) sur une route protégée → redirige `/mss-unconfigured` ; sur route d'onboarding → laisse passer
- [ ] Si `userEmail` conserve un usage d'affichage, il est dissocié de la décision d'onboarding (pas de régression d'affichage)
- [ ] `Client-Email` envoyé au backend n'est jamais un `email` de repli pour une session non configurée
- [ ] Non-régression task-159 : token complet → tabs ; pas de jeton → login
- [ ] Aucune donnée de santé en clair dans les logs client

## Manual Test Plan

- Lancer le mobile : `cd Client/Mobile && npm start` (+ proxy PSC / api-mail)
- **Cas bug** : se connecter avec un compte dont le jeton porte un `email` mais **pas** de `mssEmail` (PS sans boîte MSSanté configurée) → attendu : écran **`/mss-unconfigured`** (onboarding), PAS la coquille tabs, aucun appel mail en erreur
- **Cas nominal** : se connecter avec un compte doté d'une adresse MSSanté (`mssEmail`) → accès direct à l'onglet Accueil, `Client-Email` = adresse MSSanté
- **Cas déconnecté** : sans jeton → `/login`
- Vérifier les logs Seq : pas d'appel mail avec une adresse `email` non-MSSanté pour une session non configurée

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : socle MSSanté — fiabilisation de l'onboarding (task-159), pas de nouvelle exigence DSR
- **Exigences DSR honorées** : MSSanté — parcours de configuration de boîte ; fiabilisation
- **INS** : non applicable — flux d'authentification/onboarding, aucune donnée patient
- **Authentification PS** : e-CPS / PSC — inchangée ; la correction porte sur la détection d'adresse MSSanté (`mssEmail`) post-authentification
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **MSSanté** : le claim `mssEmail` est l'unique source de vérité « boîte configurée » ; aucune adresse de repli non-MSSanté ne doit être utilisée comme identité d'émission
- **Tracé PGSSI-S** : non applicable (pas de nouvel évènement) ; ne jamais logguer d'adresse en clair inutilement
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non applicable — client
- **AIPD / impact RGPD** : inchangé

## Branches
> **Base spéciale** : branchée sur `feat/task-159-mss-onboarding` (PAS `develop`) — le code onboarding à corriger n'est pas encore sur `develop` (PR #57 ouverte). Choix humain 2026-07-17 : bundle 159+167 → à la fin, 167 sera replié dans la PR #57 pour un merge atomique de l'onboarding (motif dashboard 149+161+162).
- `client-mobile` (pushed) : feat/task-167-onboarding-mssemail — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-167-onboarding-mssemail

## Statut
- 2026-07-17 — implémentée (commit intégré à `feat/task-159-mss-onboarding`), **bundlée dans la PR #57** (grappe onboarding 159+167). Build ✓, 541 tests ✓.
- En attente du merge humain de #57 (HAG). Sera archivée avec 159 au merge.

## Merged
- 2026-07-17 — grappe onboarding 159+167 mergée via PR #57 (merge atomique)
- `client-mobile` : b9c31bf (PR #57 fermée)
