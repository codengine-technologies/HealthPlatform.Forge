# todo-task-052-angular-psc-token-refresh-on-identity-change.md — Refresh PSC token Angular et invalidation sur changement d'identité

**Repos**: client-angular
**Dependencies**: aucune (peut shipper indépendamment de task-048/049/050 et doit même précéder leur enforcement pour éviter les 403 user-visible)
**Epic**: E010
**EpicTitle**: Security hardening — identity propagation & cross-user leak prevention

> Repo `client-angular` en **mode code-only** : la forge écrit le code et
> exécute `nx lint`/`nx build`/`nx test` côté `Client/Angular/front/`,
> **sans** toucher à git. Le humain gère branche, commit, push TFS et PR.

## Objectif

Supprimer la fenêtre de leak « PSC token périmé en mémoire NgRx » que
l'analyse Seq + observation Ctrl+F5 a confirmée : tant que les tokens
en mémoire restent time-valid, `installBootstrapEffect` ne refait
jamais d'appel à `$getTokenFromSession`, donc un changement d'identité
côté `psc-auth-proxy` (changement de carte CPS, refresh PSC slot
backend) n'est jamais répercuté dans `tokenAggregate.pscAccessToken`.
Résultat : l'interceptor `mssHeadersInterceptor` continue d'injecter
le PSC token de l'utilisateur précédent dans le header `X-PSC-Token`,
et MSSanté ouvre la mailbox correspondant à ce token, quel que soit le
KC bearer joint.

Ce fix Angular est complémentaire de task-048 (cross-check serveur) :
task-048 transforme le leak en 403 visible ; task-052 supprime la
fenêtre où ce 403 peut survenir.

## Hypothèse de mécanisme confirmée

1. T0 — Virginie connectée. Store NgRx : `tokenAggregate = { accessToken: <KC-virginie>, pscAccessToken: <PSC-virginie> }`. Time-valid.
2. T1 — Changement carte CPS → Kit. `psc-auth-proxy` (Redis) bascule son slot PSC sur Kit.
3. T2 — L'utilisateur clique dans l'app Angular sans recharger.
   `installBootstrapEffect` early-return sur `hasValidTokens(currentTokens, Date.now())`.
   `mssHeadersInterceptor` envoie `X-PSC-Token = <PSC-virginie>`.
   MSSanté ouvre la mailbox de Virginie.
4. T3 — Ctrl+F5 → `tokenAggregate = undefined` → bootstrap appelle
   `$getTokenFromSession()` → backend renvoie le tokenAggregate frais avec PSC-Kit → tout redevient cohérent.

Preuve directe : Ctrl+F5 corrige le bug **sans relogin**, donc le
backend a déjà la bonne info ; le défaut est dans la cache mémoire
Angular qui n'est jamais invalidée.

## Scope

### 1. Revalidation périodique en arrière-plan (Niveau 1)

Dans la `AuthenticationStore`, ajouter un mécanisme qui appelle
`authenticationService.$getTokenFromSession()` à intervalles courts
(suggestion : 60 s) **même si `hasValidTokens` est vrai**, compare le
`pscAccessToken` retourné avec celui en mémoire, et :

- si identique → no-op silencieux
- si différent → `applyTokenAggregate(nouveau)` + warning console + event de log structuré
- si le backend renvoie 400/401 (session perdue) → forcer logout

Implémentation suggérée : un `effect()` Angular qui s'abonne à
`interval(60_000)` côté `signal()` ou un `setInterval` géré
proprement dans `withMethods` avec cleanup au destroy (`takeUntilDestroyed`).

### 2. Revalidation événementielle (Niveau 1 bis)

Mêmes contrôles déclenchés par :

- `document.addEventListener('visibilitychange', ...)` quand l'onglet
  redevient visible (le médecin revient sur l'onglet après avoir
  changé de patient/carte → on relit la session backend
  immédiatement, sans attendre les 60 s).
- `window.addEventListener('focus', ...)` (fallback navigateurs
  exotiques).

### 3. Détection de changement d'identité (Niveau 2)

Dans `createApplyTokenAggregate` (et la revalidation périodique
ci-dessus), comparer **avant** d'écrire :

- `previousJwtDecoded.sub` (KC) vs `newJwtDecoded.sub`
- `previousJwtDecoded.mssEmail` vs `newJwtDecoded.mssEmail`

Si l'une des deux change pour autre chose qu'`undefined → value`
(c'est-à-dire un VRAI changement de personne, pas une première
authentification) :

- forcer `clearAuthState()`
- forcer `authenticationService.$logout()` puis `.login()` redirect
- logger un warning sécurité (event structuré)
- raison : autres stores/caches (mails, contacts, drafts) sont peut-être
  encore peuplés avec les données de l'utilisateur précédent ; un
  cycle logout/relogin propre est le seul moyen safe de tout repartir.

### 4. Refresh KC garantit refresh PSC (Niveau 2 bis)

Vérifier le `createRefreshTokenMethod` : quand le refresh KC retourne
un nouveau `tokenAggregate`, s'assurer que `pscAccessToken` est
**toujours fourni par le backend** (et non « conservé » à partir de
l'ancien). Si le contrat backend ne le garantit pas → soit demander
correctif côté backend-auth, soit dans Angular faire un
`$getTokenFromSession()` supplémentaire derrière chaque refresh KC
pour resynchroniser le PSC. Documenter le choix dans le PR.

## Hors scope (à ne PAS faire dans cette task)

- Modifications côté `psc-auth-proxy` / backend-auth : task séparée si
  besoin.
- Cross-check serveur `mssSub`/`mssRpps` : c'est task-048.
- Nouveaux Protocol Mappers : c'est task-050.
- Bouton « ré-authentifier » dans la UI : peut être discuté plus tard,
  pas dans cette task.

## Manual Test Plan

> **Working dir** : `Client/Angular/front/`

### Pré-requis

- Deux cartes CPS de test (ex. Virginie `rpps0062267` et Kit
  `doc0077119`).
- Accès à un déploiement Staging avec `psc-auth-proxy` et `api-mail`
  fonctionnels.
- DevTools navigateur ouverts, onglet Console + Network.

### Scénario 1 — Bascule carte CPS sans logout

1. Connecter avec Virginie. Vérifier dans la console que
   `tokenAggregate.pscAccessToken` débute par les premiers caractères
   connus du PSC token de Virginie.
2. **Sans cliquer logout**, retirer la carte de Virginie, insérer
   celle de Kit. Patienter ≤ 60 s **ou** changer d'onglet et revenir
   sur l'onglet de l'app.
3. Vérifier dans DevTools / console :
   - un log structuré `[AuthenticationStore] PSC token rotated`
     (ou warning équivalent) est apparu
   - le nouveau `tokenAggregate.pscAccessToken` correspond à celui de
     Kit
   - les requêtes vers `/api/v1/mail/*` envoient désormais le PSC
     token de Kit dans `X-PSC-Token`
4. Vérifier dans l'UI : la mailbox affichée est celle de Kit.
5. Sans Ctrl+F5, sans logout manuel.

### Scénario 2 — Changement réel d'identité KC détecté

1. Connecté Virginie.
2. Simuler un retour de `$getTokenFromSession` avec un KC `sub`
   différent (peut se faire en stubbing direct du service backend ou
   via un changement réel de session côté backend-auth).
3. Vérifier que l'application déclenche **automatiquement** un
   `clearAuthState()` + redirect `/logout` + redirect login.
4. Vérifier qu'après re-login, **aucune** donnée de la session
   précédente (liste mails, drafts en cours) n'est encore visible.

### Scénario 3 — Pas de régression sur le flow normal

1. Connecter normalement Kit.
2. Travailler 5 min : ouvrir des mails, naviguer.
3. Vérifier qu'aucun warning « PSC token rotated » ne s'affiche.
4. Vérifier que les revalidations périodiques (60 s) restent
   silencieuses tant que rien ne change.
5. Vérifier dans Network : pas plus d'un appel à
   `$getTokenFromSession` toutes les ~60 s + 1 à chaque retour de
   focus onglet. Charge backend supplémentaire négligeable.

### Build & test (CI-style)

```pwsh
cd Client/Angular/front
npm ci
npx nx lint weda2 --projects=tag:scope:mss
npx nx test weda2 --watch=false
npx nx build weda2 --configuration=production
```

Tous doivent passer (0 erreurs ; les warnings ESLint préexistants
non liés à cette task restent dette technique).

## Definition of Done

- [ ] Revalidation périodique implémentée (intervalle configurable,
      défaut 60 s, désactivable via `provideMssAuth({ revalidate: false })`
      pour les tests unitaires)
- [ ] Listeners `visibilitychange` et `focus` posés et nettoyés au
      destroy (pas de fuite mémoire)
- [ ] Comparaison d'identité (`sub`, `mssEmail`) dans
      `createApplyTokenAggregate` avec déclenchement de logout
      auto-redirect si bascule détectée
- [ ] Comportement du refresh KC documenté (paragraphe dans le code
      ou ADR court) : confirmation que le PSC token est toujours
      refourni par backend ou contournement Angular explicite
- [ ] Unit tests Vitest dans
      `apps/weda2/src/lib/auth/store/utils/store-helpers.utils.spec.ts`
      et `authentication-store.spec.ts` :
  - [ ] le polling appelle bien `$getTokenFromSession` toutes les 60 s
  - [ ] si le PSC token retourné est identique → no-op (pas de
        `updateState` avec `SET_TOKEN_AGGREGATE` redéclenché)
  - [ ] si le PSC token retourné est différent → `applyTokenAggregate`
        appelé avec la nouvelle valeur
  - [ ] si `sub` KC change → `clearAuthState` + `login` redirect
        appelés
  - [ ] `visibilitychange` → revalidation immédiate (ne pas attendre
        l'interval)
  - [ ] cleanup au destroy : `clearInterval`/`removeEventListener`
        bien appelés
- [ ] `mssHeadersInterceptor` reste inchangé fonctionnellement (lit
      toujours `tokenAggregate.pscAccessToken`) — vérifier par les
      tests existants
- [ ] `nx lint weda2 --projects=tag:scope:mss` → 0 erreurs
- [ ] `nx test weda2 --watch=false` → 0 failures
- [ ] `nx build weda2 --configuration=production` → 0 erreurs
- [ ] Scénarios 1, 2, 3 du Manual Test Plan validés à la main par le
      humain avant push TFS

## Notes d'implémentation

- **Anonymisation logs** : ne JAMAIS logger le PSC token complet.
  Pour les warnings « rotated », logger uniquement les 6 derniers
  caractères du token précédent et du nouveau, plus le `mssEmail`
  associé (3 premiers caractères + domaine).
- **Configuration** : exposer l'intervalle de polling via
  `provideMssAuth({ pscRevalidateIntervalMs: 60_000 })` pour qu'un
  client de l'app puisse l'ajuster ou le désactiver en test.
- **Mode strict via flag** : prévoir un flag (côté config Angular ou
  via env injectée) `MSS_STRICT_IDENTITY_ROTATION` (défaut `false`)
  qui, à `true`, force le logout/redirect automatique sur tout
  changement détecté ; à `false`, se contente de
  `applyTokenAggregate` + warning sans forcer logout. Permet une
  bascule progressive.
- **Coordination avec task-048** : tant que task-048 ne tourne pas
  encore en mode enforcement, task-052 réduit fortement l'occurrence
  du leak ; quand task-048 passe en enforcement, task-052 réduit le
  nombre de 403 user-visible (puisque l'Angular se resynchronise
  avant que l'utilisateur ne déclenche un appel rejeté). Les deux
  sont défense en profondeur.
