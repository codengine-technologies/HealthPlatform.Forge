# todo-task-048-psc-kc-identity-crosscheck.md — Cross-check d'identité à deux facteurs entre le JWT Keycloak et le token PSC

**Repos**: api-mail
**Dependencies**: task-049 (opt-in backend-auth qui écrit `mssSub`/`mssRpps` dans Keycloak), task-050 (Protocol Mappers Keycloak qui projettent ces attributs en claims du JWT KC)
**Epic**: E010
**EpicTitle**: Security hardening — identity propagation & cross-user leak prevention

> ⚠ **Priorité SÉCURITÉ — incident de production confirmé** (2026-05-19) :
> un praticien authentifié via Pro Santé Connect avec sa propre carte CPS
> (Dr Kit) s'est vu afficher la boîte aux lettres MSSanté d'un autre
> praticien (Virginie) après un changement de carte CPS sur le même
> navigateur. Cause racine côté `api-mail` : le middleware
> `UserContextEnricherMiddleware` lit `X-PSC-Token` sans le rapprocher
> de l'identité portée par le JWT Keycloak, puis ce token est utilisé
> directement comme credential OAuth2 IMAP → le serveur MSSanté ouvre
> la mailbox du propriétaire du **token PSC**, pas celle de
> l'utilisateur authentifié côté Keycloak.

## Objectif

Faire de `UserContextEnricherMiddleware` la **barrière souveraine** de
cohérence d'identité côté backend : refuser (HTTP 403) toute requête où
l'identité portée par le token PSC ne correspond pas à l'identité du
JWT Keycloak, **via un cross-check à deux facteurs sur `mssSub` et
`mssRpps`**.

Cette barrière est **indépendante du client Angular et du backend
d'authentification** : même avec un front buggué ou un backend d'auth
défaillant qui enverraient un token PSC d'un autre utilisateur, `api-mail`
doit rejeter la requête avant qu'elle n'atteigne le pool IMAP.

## Modèle d'identité confirmé

Le token PSC porte **deux identifiants distincts**, issus de deux
référentiels indépendants (confirmé par un payload PSC décodé réel,
2026-05-19) :

| Claim PSC | Exemple | Nature | Source de vérité |
|---|---|---|---|
| `sub` | `c5869b2a-d0e9-4012-8088-1bddda1c079a` | UUID interne IAM PSC | Référentiel IAM ANS (Keycloak PSC) |
| `SubjectNameID` | `899700771191` | RPPS (12 chiffres) | Référentiel national professionnel ANS |

> **Casse exacte critique** : `SubjectNameID` (avec un `D` capital final),
> pas `SubjectNameId`. La comparaison JSON est case-sensitive.

Côté Keycloak (le nôtre), `task-049` + `task-050` garantissent que le JWT
KC porte trois claims provisionnés au moment de l'opt-in :

- `mssEmail`  — déjà présent aujourd'hui
- `mssSub`    — **nouveau**, copie de `PSC.sub` au moment de l'opt-in
- `mssRpps`   — **nouveau**, copie de `PSC.SubjectNameID` au moment de
  l'opt-in

Le cross-check `api-mail` revient alors à deux égalités `Ordinal` :

```
KC.mssSub  == PSC.sub
KC.mssRpps == PSC.SubjectNameID
```

## Scope

### `api-mail` (.NET 10) — modifications

1. **Feature flag** `MSS_ENFORCE_PSC_IDENTITY` (variable d'environnement,
   booléen, défaut `false`) lu au démarrage et exposé via une option
   typée (`PscIdentityOptions.Enforce`) :
   - `false` → mode **observation** : exécute la logique de check, **logge**
     match/mismatch/missing, mais **laisse passer** toutes les requêtes.
   - `true` → mode **enforcement** : un mismatch ou un claim manquant
     retourne 403.

2. **`UserContextEnricherMiddleware.ResolvePscToken`** — étendre pour
   décoder le PSC token (sans validation de signature — cf. note 1
   ci-dessous) et extraire deux claims :
   - `pscSub` (= claim `sub`, string)
   - `pscSubjectNameId` (= claim `SubjectNameID`, string, **casse exacte**)
   - Utiliser `Microsoft.IdentityModel.JsonWebTokens.JsonWebTokenHandler.ReadJsonWebToken(string)`.
     Si le parsing échoue → traiter comme `missing`.

3. **Nouveau check dans `ApplyAuthenticatedUserAsync`** (ou méthode
   privée dédiée appelée juste après la validation `mssEmail`) :

   ```csharp
   var mssEmail = context.User.FindFirstValue("mssEmail");
   var mssSub   = context.User.FindFirstValue("mssSub");
   var mssRpps  = context.User.FindFirstValue("mssRpps");

   // Étape 1 — complétude (3 claims obligatoires)
   var incompleteKc =
       string.IsNullOrWhiteSpace(mssEmail) ||
       string.IsNullOrWhiteSpace(mssSub)   ||
       string.IsNullOrWhiteSpace(mssRpps);

   // Étape 2 — cohérence (cross-check à 2 facteurs)
   var mismatch =
       !string.Equals(mssSub,  pscSub,            StringComparison.Ordinal) ||
       !string.Equals(mssRpps, pscSubjectNameId,  StringComparison.Ordinal);
   ```

   Comportement :
   - Si pas de `X-PSC-Token` (mode offline / KC-only) → le check ne
     s'applique pas, laisser passer.
   - Sinon (PSC token présent) :
     - `incompleteKc` → log Warning EventId 3722 « KC token incomplete:
       missing mssEmail/mssSub/mssRpps ». Si `Enforce=true` → 403.
     - `mismatch` → log Warning EventId 3723 « PSC/KC identity
       mismatch ». Si `Enforce=true` → 403.
     - Sinon → log Information EventId 3721 « PSC/KC identity match »
       (uniquement en mode observation pour faciliter le monitoring de
       rollout ; en enforcement, ne pas logger l'événement nominal).

4. **Réponse 403** au client — corps minimal, pas de détail sensible :
   ```json
   { "error": "Identity check failed." }
   ```
   Distinguer les deux causes uniquement côté logs (EventId 3722 vs 3723),
   pas dans le body HTTP.

5. **`LoggerMessage` source-generator** pour les 3 événements :
   - EventId 3721 Information « PSC/KC identity match »
   - EventId 3722 Warning     « KC token incomplete »
   - EventId 3723 Warning     « PSC/KC identity mismatch »

   Champs structurés :
   - `MssEmail` (anonymisé : 3 premiers chars + `…` + domaine)
   - `KcSub` (6 derniers chars)
   - `PscSub` (6 derniers chars)
   - `KcRpps` (entier, non sensible)
   - `PscRpps` (entier, non sensible)
   - `Path`, `CorrelationId`, `Enforce` (bool — pour différencier
     observation vs enforcement dans Seq)
   - **Ne jamais** logger les tokens complets, même tronqués au-delà de
     6 chars.

6. **Path exclusions** : aucune nouvelle exclusion. La nouvelle vérif
   est dans `ApplyAuthenticatedUserAsync`, qui n'est déjà pas appelée
   pour `/api/v1/account/mss-imap-test` (onboarding) — comportement
   conservé.

7. **Configuration `PscIdentityOptions`** dans
   `Api/Mail/src/Api/Configuration/` (nouveau fichier) :
   - `bool Enforce { get; init; }` — bound depuis section `PscIdentity`
     d'`appsettings.json` ou variable env `MSS_ENFORCE_PSC_IDENTITY`.
   - Documenter dans `appsettings.json` (commentaire) le sens des deux
     phases.

### Notes d'implémentation

1. **Pas de vérification cryptographique du token PSC à chaque requête.**
   Le rôle d'`api-mail` ici est uniquement la **cohérence d'identité
   applicative** entre deux tokens dont la signature est validée
   ailleurs (KC par `UseAuthentication` du pipeline, PSC par le serveur
   MSSanté en aval lors du `SaslMechanismOAuth2`). Une task de
   défense-en-profondeur séparée (task-051) pourra ajouter la vérif
   JWKS PSC plus tard. **À documenter explicitement** en commentaire
   au-dessus du parsing.

2. **Casse `SubjectNameID`** : un test unitaire dédié doit échouer si
   un développeur change la clé en `SubjectNameId` (assertion exacte).

3. **`PSISubjectNameID`** (présent dans le token PSC, vide pour les
   pros) ne doit **pas** être lu — c'est un claim distinct destiné aux
   patients. À ignorer.

4. **Pas de cache** du parsing PSC : ~0,1 ms par requête, négligeable.

### Tests à produire

#### Unitaires — `Api/Mail/tests/mss.mail.api.tests/Middleware/UserContextEnricherCrossCheckTests.cs`

(Nouveau fichier ; conserver les tests middleware existants intacts.)

Tests sur le **parsing PSC** :
- `ResolvePscToken_TokenAbsent_LeavesContextEmpty` — pas de header → pas de tentative de parsing.
- `ResolvePscToken_ValidJwt_ExtractsSubAndSubjectNameID` — payload réel (cf. fixture ci-dessous), attendus exacts.
- `ResolvePscToken_SubjectNameIdLowerCase_IsNotConfusedWithSubjectNameID` — un token contenant `SubjectNameId` en place de `SubjectNameID` → champ extrait = `null` (garantit la casse stricte).
- `ResolvePscToken_MalformedJwt_TreatsClaimsAsMissing` — payload non parsable → claims null, pas de crash.

Tests sur le **cross-check observation (Enforce=false)** :
- `CrossCheck_Observation_MatchingTokens_LogsInfo3721_LetsThrough`
- `CrossCheck_Observation_KcMissingMssSub_LogsWarn3722_LetsThrough`
- `CrossCheck_Observation_KcMissingMssRpps_LogsWarn3722_LetsThrough`
- `CrossCheck_Observation_MismatchOnSub_LogsWarn3723_LetsThrough`
- `CrossCheck_Observation_MismatchOnRpps_LogsWarn3723_LetsThrough`
- `CrossCheck_Observation_NoPscToken_NoLog_LetsThrough`

Tests sur le **cross-check enforcement (Enforce=true)** :
- `CrossCheck_Enforce_MatchingTokens_LetsThrough` — aucun log nominal, `next` appelé.
- `CrossCheck_Enforce_KcMissingClaims_Returns403_BodyIdentityCheckFailed`
- `CrossCheck_Enforce_MismatchOnSub_Returns403`
- `CrossCheck_Enforce_MismatchOnRpps_Returns403`
- `CrossCheck_Enforce_NoPscToken_LetsThrough` — mode KC-only conservé.

Test sur **la non-fuite de secrets dans les logs** :
- `CrossCheck_Mismatch_LogScope_DoesNotContainFullToken` — vérifier
  qu'aucun log scope ne contient la chaîne complète du PSC token ou du
  KC bearer.

#### Intégration — `Api/Mail/tests/mss.mail.api.integration.tests/Middleware/PscKcCrossCheckIntegrationTests.cs`

(Nouveau fichier ; helper `WebApplicationFactory` déjà en place pour
d'autres tests d'intégration auth.)

Avec `Enforce=true` :
- `Request_WithMatchingPscAndKcIdentity_Returns200` — JWT KC (mssSub=A_uuid, mssRpps=A_rpps) + PSC token (sub=A_uuid, SubjectNameID=A_rpps) → 200 sur `/api/v1/mail/folders` (IMAP mocké).
- `Request_WithMismatchedSub_Returns403_NoImapCall` — JWT KC userA + PSC token sub=userB → 403, body `Identity check failed.`, **aucun appel à `IMailClientSessionManager`** (vérifié via spy NSubstitute).
- `Request_WithMismatchedRpps_Returns403_NoImapCall` — idem pour mismatch RPPS.
- `Request_WithKcMissingMssSub_Returns403` — JWT KC sans `mssSub` → 403, body `Identity check failed.`.
- `Request_WithoutPscToken_Returns200` — KC-only, pas de header X-PSC-Token → 200 (mode offline).

#### Fixture de test (payload PSC réaliste)

Constante de test dans `TestData/PscTokenFixtures.cs` :

```json
{
  "iss": "https://auth.bas.psc.esante.gouv.fr/auth/realms/esante-wallet",
  "azp": "weda-edc-bas",
  "sub": "c5869b2a-d0e9-4012-8088-1bddda1c079a",
  "SubjectNameID": "899700771191",
  "PSISubjectNameID": "",
  "preferred_username": "899700771191",
  "otherIds": [
    { "identifiant": "899700771191", "origine": "RPPS", "qualite": 1 }
  ],
  "sid": "273ada99-8292-4db1-a3c7-75a2dd7c97ac",
  "acr": "eidas1",
  "authMode": "CARD",
  "auth_level": "1",
  "exp": 1779219541, "iat": 1779219421, "auth_time": 1779216089,
  "jti": "onrtac:21910429-730e-4b7c-a991-53a75a77ea81",
  "nonce": "ced5528a-361c-4df5-942c-6d677cc07121",
  "scope": "openid scope_all",
  "typ": "Bearer"
}
```

Signature factice (non vérifiée par `api-mail`), header `{ "alg": "RS256", "typ": "JWT", "kid": "test" }`.

### Hors scope (autres tasks)

- ❌ Opt-in `mssSub`/`mssRpps` côté backend-auth → **task-049** (hors workspace).
- ❌ Protocol Mappers Keycloak → **task-050** (`devops`).
- ❌ Vérification JWKS PSC à chaque requête → **task-051** (defense-in-depth, plus tard).
- ❌ Invalidation `tokenAggregate.pscAccessToken` côté Angular → **task-052** (defense-in-depth, plus tard).
- ❌ LogContext Serilog leak `MailClientSessionManager` → **task-053** (bug logs, sans impact sécu).

## Definition of Done

- [ ] Option typée `PscIdentityOptions` introduite, bound sur env
      `MSS_ENFORCE_PSC_IDENTITY` ou section `PscIdentity:Enforce`
- [ ] `UserContextEnricherMiddleware.ResolvePscToken` étendu pour
      extraire `sub` et `SubjectNameID` (casse stricte)
- [ ] Nouveau check à deux facteurs dans `ApplyAuthenticatedUserAsync` :
      complétude des 3 claims KC + égalité `(mssSub, mssRpps)` ↔
      `(PSC.sub, PSC.SubjectNameID)`
- [ ] Mode observation (`Enforce=false`) : log uniquement, laisse passer.
- [ ] Mode enforcement (`Enforce=true`) : 403 sur incomplete ou mismatch,
      body `{ "error": "Identity check failed." }`
- [ ] 3 `LoggerMessage` (EventId 3721/3722/3723), aucun log de token complet
- [ ] Anonymisation `mssEmail` dans les logs (3 chars + domaine)
- [ ] >= 11 tests unitaires (parsing + observation + enforcement + non-fuite logs)
- [ ] >= 5 tests d'intégration (matching, 2 mismatch, incomplete, sans PSC)
- [ ] Fixture `PscTokenFixtures.cs` créée avec un payload réaliste
- [ ] Build `dotnet build HealthPlatform.Api.Mail.sln` → 0 erreur
- [ ] Tests `dotnet test HealthPlatform.Api.Mail.sln` → 0 failure
- [ ] Aucune régression sur les tests middleware existants ni sur
      `/api/v1/account/mss-imap-test` (onboarding) ni sur le test bypass
      `/qa` Playwright
- [ ] `appsettings.Development.json` documente le flag (commentaire +
      valeur `false` par défaut)
- [ ] PR ouverte sur `feat/task-048-psc-kc-identity-crosscheck`,
      labelée `awaiting-human-merge`
- [ ] PR description rappelle :
      « Security defense-in-depth — phase 1 (observation). Enforcement à
      activer après task-049/task-050 déployées et > 95 % de sessions KC
      portant `mssSub`+`mssRpps` (cf. monitoring EventId 3721/3722). »

## Manual Test Plan

> Cette task ne change **rien** au comportement utilisateur tant que
> `MSS_ENFORCE_PSC_IDENTITY=false`. Le test humain valide d'abord la
> non-régression en observation, puis (dans une opération de runbook
> ultérieure) la coupure réelle en enforcement.

### Setup commun

- Image `api-mail` issue de `feat/task-048-…` déployée sur env Dev.
- `MSS_ENFORCE_PSC_IDENTITY` non défini (= `false`, mode observation).
- Au moins une paire de comptes praticien MSSanté distincts avec
  cartes CPS différentes (p. ex. Dr Kit `899700771191` et Virginie
  `XXXXXXXXXXXX`).

### Phase 1 — Observation (non-régression)

1. **Connexion online normale (PSC + carte personnelle)** :
   se connecter avec la carte de Kit, ouvrir messagerie → comportement
   inchangé (boîte de Kit affichée, latence inchangée).
2. **Connexion offline (KC-only, mode dégradé)** :
   se connecter sans PSC → comportement inchangé.
3. **Reproduction du leak en observation** :
   - Se connecter avec carte Virginie, ouvrir la boîte.
   - Changer pour carte Kit (sans fermer le navigateur), retrigger une
     auth PSC.
   - Constat attendu : **la boîte de Virginie reste visible**
     (le bug n'est PAS encore corrigé par cette task seule — c'est
     l'enforcement post-task-049/050 qui le coupera).
   - Mais Seq doit montrer : EventId 3723 (mismatch) ou EventId 3722
     (incomplete, si KC n'a pas encore `mssSub`/`mssRpps` provisionnés),
     **par requête**, avec `MssEmail=vir…@…`, `KcRpps=XXXXXXXXXXXX`,
     `PscRpps=899700771191`. C'est le **signal de monitoring** qui
     permettra de mesurer la prévalence du bug en prod.
4. **Test bypass `/qa`** : suite Playwright auth → toujours verte
   (`TestBypassAuthenticationHandler` n'envoie pas `X-PSC-Token`).

### Phase 2 — Enforcement (à exécuter dans un runbook ultérieur)

> ⚠ **Ne PAS activer en prod tant que task-049/050 ne sont pas
> déployées et qu'au moins 95 % des sessions KC ne portent pas les
> claims `mssSub`+`mssRpps`** (vérifié via taux EventId 3722 en Seq).

1. Activer `MSS_ENFORCE_PSC_IDENTITY=true` sur Dev d'abord.
2. Refaire la séquence de leak (Virginie → Kit sur même navigateur).
3. Constat attendu : la première requête `/api/v1/mail/folders` après
   le changement de carte retourne **403** avec body
   `{"error":"Identity check failed."}`. EventId 3723 dans Seq.
4. Action correctrice utilisateur : fermer le navigateur, le rouvrir,
   réauth complète avec carte Kit → boîte de Kit affichée normalement.

### Vérification logs (Seq)

- Filtrer `EventId in [3721, 3722, 3723]` → présence en cohérence avec
  le trafic. Aucun champ ne doit contenir la chaîne complète d'un
  token ; vérifier visuellement sur 10 entrées.
- Aucun `EventId 3723` avec `Enforce=true` ne doit être suivi d'une
  réponse 200 sur la même requête (corrélation par `CorrelationId`).
