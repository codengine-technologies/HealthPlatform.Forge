# todo-task-049-backend-auth-optin-msssub-mssrpps.md — Opt-in `mssSub` & `mssRpps` lors de l'enrôlement MSSanté

**Repos**: backend-auth *(hors workspace — pilotage manuel par le humain)*
**Dependencies**: task-050 (les Protocol Mappers Keycloak qui projetteront ces attributs en claims). Provisionnement (049) peut précéder la projection (050), mais l'enforcement task-048 attend les deux.
**Epic**: E009

> ⚠ **Repo hors automation forge** (`/start`, `/develop`, `/review`, `/merge`
> n'opèrent pas sur ce repo). Cette task documente le contrat à
> implémenter manuellement par l'équipe auth.

## Objectif

Lors de l'opt-in MSSanté (le flux Angular qui pose `mssEmail` dans
Keycloak pour la première fois quand le JWT KC n'en contient pas
encore), le backend d'authentification doit **également écrire deux
nouveaux attributs utilisateur dans Keycloak** :

- `mssSub`  — copie du claim `sub` du PSC token courant
- `mssRpps` — copie du claim `SubjectNameID` du PSC token courant

Ces attributs deviendront ensuite des claims du JWT KC via les Protocol
Mappers (task-050), et serviront au cross-check à deux facteurs côté
`api-mail` (task-048).

## Contrat de sécurité — non-négociable

1. **Source unique du `mssSub`/`mssRpps` = le PSC token vérifié.**
   - Le backend-auth **NE DOIT PAS** accepter `mssSub`/`mssRpps` depuis
     une payload client (POST body, query string, header custom).
     N'accepter QUE `mssEmail` depuis le client.
   - `mssSub`/`mssRpps` doivent être extraits **côté serveur** depuis le
     PSC token attaché à la session courante (cookie HTTP-only) ou à
     l'objet `AuthenticationResult` issu du flow OIDC PSC.

2. **Signature PSC vérifiée.**
   - Le PSC token dont on extrait `sub`/`SubjectNameID` doit avoir vu sa
     signature validée au moins une fois (typiquement au callback OIDC
     PSC par la lib `Microsoft.AspNetCore.Authentication.OpenIdConnect`
     ou équivalent).
   - Si l'extraction se fait sur un PSC token relu depuis la session,
     **garantir** que la session ne peut contenir qu'un token qui a été
     validé lors de sa pose.

3. **Refus strict de re-binding incohérent.**
   - Si le user Keycloak `mssEmail=X` a déjà `mssRpps=R1` et `mssSub=S1`
     persistés, et qu'un nouvel opt-in se présente avec un PSC token
     portant `(R2, S2)` ≠ `(R1, S1)` → **refuser** l'opt-in avec une
     erreur explicite (HTTP 409 `Conflict` ou équivalent), et logger un
     warning sécurité.
   - **Ne PAS écraser** silencieusement.
   - L'utilisateur légitime qui veut vraiment ré-associer (changement de
     RPPS — extrêmement rare) doit passer par une procédure
     administrative manuelle.

4. **Idempotence.**
   - Si `(R, S)` envoyés correspondent à `(mssRpps, mssSub)` déjà
     persistés → succès silencieux (200 OK), pas de réécriture inutile.

## Casse exacte des claims PSC

- `sub` — minuscule, claim OIDC standard.
- `SubjectNameID` — **`D` capital final**. Pas `SubjectNameId`. La
  lecture doit être case-sensitive et un test unitaire doit échouer si
  un développeur change la casse.

## Tests à produire (côté backend-auth)

- Opt-in OK : utilisateur n'a pas encore `mssEmail` ; PSC token de la
  session porte `sub=U1, SubjectNameID=R1` ; client POST `{mssEmail:E}`
  → KC user provisionné/mis à jour avec `(mssEmail=E, mssSub=U1, mssRpps=R1)`.
- Opt-in idempotent : refaire le même appel → succès, KC user inchangé.
- Opt-in conflict : utilisateur a déjà `(mssSub=U1, mssRpps=R1)` ; PSC
  token courant porte `(U2, R2)` ; client POST `{mssEmail:E}` → réponse
  409, KC user inchangé, log Warning sécurité.
- Opt-in refusé si client fournit `mssSub`/`mssRpps` dans le body → 400
  Bad Request (paramètre inconnu / non autorisé).
- Opt-in refusé si pas de PSC token dans la session → 400 ou 401
  (selon convention du repo).
- Opt-in avec PSC token portant `SubjectNameId` (mauvaise casse) → le
  champ doit être lu comme `null` (test de non-régression de la casse).

## Definition of Done

- [ ] Endpoint d'opt-in du backend-auth modifié pour extraire `sub` et
      `SubjectNameID` du PSC token serveur
- [ ] Aucune lecture de `mssSub`/`mssRpps` depuis le body/query/header client
- [ ] Refus strict de re-binding (HTTP 409 + log Warning)
- [ ] Idempotence sur valeurs identiques
- [ ] Casse stricte `SubjectNameID` (test dédié)
- [ ] Tests unitaires + intégration couvrant les 6 cas ci-dessus
- [ ] Build & tests verts dans le repo backend-auth
- [ ] PR ouverte, mergée selon les conventions du repo backend-auth
- [ ] Runbook d'exploitation rédigé : procédure administrative pour
      forcer un re-binding légitime (rare)

## Manual Test Plan

(À détailler par l'équipe auth selon les conventions du repo
backend-auth.)

1. Sur env Dev, utilisateur n'a jamais opt-in.
2. Connexion via PSC avec carte Kit → JWT KC initial sans `mssEmail`
   ni `mssSub` ni `mssRpps`.
3. Flux Angular d'opt-in : saisir `mssEmail`, soumettre.
4. Vérifier dans Keycloak Admin : user `899700771191` (ou son ID) porte
   désormais les 3 attributs `mssEmail=…`, `mssSub=…uuid…`,
   `mssRpps=899700771191`.
5. Re-trigger opt-in → 200 silencieux, attributs inchangés.
6. (Tentative malveillante) Simuler un client qui POST
   `{mssEmail:E, mssSub:HACKED, mssRpps:HACKED}` → ces deux champs
   doivent être ignorés ou rejetés (400).
