# todo-task-284.md — Le web perd sa session en silence quand le proxy re-frappe le jeton : le refresh Angular est bloqué par une garde vestigiale

**Repos**: client-angular
**Dependencies**: `psc-auth-proxy/task-015` (refresh PSC-primaire par re-échange — autre forge, dépôt `D:\Workspaces\psc-auth-proxy`, état `done-*`, PR `!9039`). Pendant mobile : `task-275` (livrée, [Mobile#64](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/64)).
**Epic**: E009
**LintProjects**: `weda2`

> **Origine** : question humaine du 2026-08-30 pendant le `/merge` de task-275 —
> « est-il normal que `client-angular` ne soit pas impacté lui aussi ? ». Non,
> il ne l'est pas. `task-275` a verrouillé la compatibilité **du mobile** au
> nouveau modèle de refresh ; personne n'avait regardé le web.

## Objectif

`psc-auth-proxy/task-015` fait basculer le refresh : le jeton Keycloak n'est
plus rafraîchi mais **re-frappé** à chaque `/auth/refresh` (re-échange JWT
Authorization Grant, RFC 7523). Conséquence sur le contrat de réponse —
l'agrégat rendu au client a un **`refreshToken` vide**, et son
`refreshTokenExpirationDateUtc` porte désormais l'échéance du refresh token
**PSC** au lieu de celle d'un refresh token Keycloak qui n'existe plus.

`client-mobile` s'en sortait sans rien changer, parce qu'il ne lit **ni** l'un
**ni** l'autre — c'est précisément l'invariant que `task-275` vient d'épingler.
**`client-angular` lit les deux.** Sa compatibilité n'était donc pas une
propriété de la plateforme, mais une propriété de l'autre client.

Cette US remet le web au niveau : **un vrai correctif** (contrairement à
`task-275`, qui était purement du test), plus les tests qui verrouillent le
nouveau contrat.

### Où vit le code

Tout l'auth Angular est dans **`apps/weda2/src/lib/auth/`** — le shell.
`apps/mss` le **consomme** sans en redéfinir : `grep -rl "auth/refresh"` sur
`apps/` + `libs/` ne remonte **que** `apps/weda2`. Le module MSS dépend donc
entièrement de cette pile.

### La bonne nouvelle : l'appel HTTP est déjà compatible

`authentication-callback.service.ts` `$refreshToken()` poste déjà en
**cookie-based**, sans jamais transmettre de refresh token :

```ts
return this.httpClient
    .post<ITokenAggregate>(this.buildUrl('/auth/refresh'), null, {
        withCredentials: true
    })
```

Body `null`, `withCredentials: true`. Cet appel n'a **aucun** besoin du champ
`refreshToken`. Le contrat réseau est donc déjà celui de task-015.

### La cassure : une garde vestigiale devant cet appel

`store/utils/store-helpers.utils.ts`, `createRefreshTokenMethod` :

```ts
const currentTokenAggregate = store.tokenAggregate?.()
const refreshToken = currentTokenAggregate?.refreshToken

if (!refreshToken) {
    return of(undefined)      // ← sort sans rien faire
}

return handleTokenRefresh(...)
```

Sous task-015, `refreshToken` est **vide**. La garde court-circuite donc
**systématiquement** un appel qui, lui, n'utilise pas ce champ. Résultat :

- **aucune requête `/auth/refresh` n'est jamais émise** ;
- **aucune erreur** — la méthode rend `of(undefined)`, un succès vide ;
- la session meurt à l'expiration de l'access token, sans trace côté client
  ni côté serveur.

C'est une panne **silencieuse**, et c'est le cœur de cette US.

### Le reste : un glissement de sens, pas une casse

Cinq autres sites lisent `refreshTokenExpirationDateUtc`. Le champ **reste
peuplé** sous task-015 (il porte l'horizon PSC), donc rien ne casse — mais ce
qu'il mesure change. Or sous le nouveau modèle, **l'horizon PSC *est* l'horizon
de session** : ces sites deviennent en réalité *plus* justes qu'avant. Ce qui
manque, ce n'est pas du code, c'est (a) des tests qui l'épinglent et (b) des
noms/commentaires qui ne racontent plus « refresh token Keycloak ».

| Fichier | Site | Sous task-015 | Action |
|---|---|---|---|
| `store/utils/store-helpers.utils.ts` | `createRefreshTokenMethod` (garde `!refreshToken`) | ❌ **refresh jamais émis** | **corriger** |
| `store/utils/store-helpers.utils.ts` | gate de logout (`accessToken && refreshTokenExpirationDateUtc`) | ⚠️ dépend du champ | relire + test |
| `store/utils/authentication.utils.ts` | `computeAuthStatus` (`: false` si date absente) | ⚠️ mesure l'horizon PSC | test + commentaire |
| `store/utils/authentication.utils.ts` | `hasValidTokens` (`!date → true`) | ✅ permissif | test de non-régression |
| `store/authentication-store.ts` | `isRefreshTokenValidComputed` | ⚠️ mesure l'horizon PSC | test + renommage/commentaire |
| `interceptors/utils/auth-interceptor.utils.ts` | `checkAndHandleRefreshTokenExpiration` | ⚠️ déconnecte sur horizon PSC — **sémantiquement correct** | test + commentaire |

## Hors périmètre

- Tout changement du `psc-auth-proxy` (autre forge).
- `client-mobile` — déjà traité par `task-275`.
- `client-blazor` — **non instruit**. Il faudra vérifier séparément s'il
  consomme le même `/auth/refresh` ; ne pas le supposer compatible sur la foi
  de cette US.
- Le champ `refreshToken` **reste déclaré** dans `ITokenAggregate` (le contrat
  de réponse du proxy est inchangé, RG-6 de task-015) — ne pas le supprimer du
  modèle.
- La désynchronisation d'horloge PSC (~2 min) vs Keycloak (5 min) sur le chemin
  IMAP : c'est `todo-task-283`, sujet distinct.

## Definition of Done

- [ ] Build passe (`npm ci && npm run build`), tests passent (`npm test`) — 0 échec
- [ ] La garde `if (!refreshToken) return of(undefined)` de
      `createRefreshTokenMethod` ne bloque plus le refresh : un agrégat dont le
      `refreshToken` est **vide** déclenche bien l'appel cookie-based
- [ ] Test unitaire : `createRefreshTokenMethod` avec `refreshToken: ''`
      **appelle** `handleTokenRefresh` (aujourd'hui : ne l'appelle pas) —
      ce test doit être **RED avant le fix** (règle 1, test-first)
- [ ] Test unitaire : `createRefreshTokenMethod` sans aucun `tokenAggregate`
      (utilisateur jamais connecté) ne déclenche **pas** d'appel — non-régression
      du seul cas que la garde protégeait légitimement
- [ ] Test unitaire : un agrégat au nouveau format (`refreshToken: ''`,
      `accessToken` re-frappé, `refreshTokenExpirationDateUtc` = horizon PSC)
      produit `AuthStatus.Authenticated` via `computeAuthStatus`
- [ ] Test unitaire : `isRefreshTokenValidComputed` reflète l'horizon PSC
      (vrai avant l'échéance, faux après)
- [ ] Test unitaire : `checkAndHandleRefreshTokenExpiration` déconnecte quand
      l'horizon PSC est dépassé, et **pas avant**
- [ ] Test unitaire : `hasValidTokens` reste permissif quand
      `refreshTokenExpirationDateUtc` est absent (non-régression)
- [ ] Les commentaires et noms qui disent « refresh token » au sens Keycloak
      sont redressés : sous le nouveau modèle la valeur mesurée est **l'horizon
      de session, porté par PSC**
- [ ] Aucune modification de `ITokenAggregate` (le champ `refreshToken` reste
      déclaré)
- [ ] Aucun changement d'URL ni de configuration d'environnement
- [ ] Aucune régression sur les specs existantes de `lib/auth/`

## Manual Test Plan

Pré-requis : `psc-auth-proxy` sur la branche portant task-015 (les deux AppHost
lancés), `api-mail` lancé, app web Angular servie localement, Seq sur
http://localhost:5341.

1. Login PSC complet → boîte de réception MSS affichée.
2. Laisser l'onglet ouvert **au-delà de l'expiration de l'access token**, puis
   naviguer (ouvrir un dossier, un message).
   **Attendu** — navigation fluide, **aucun** retour au formulaire de connexion.
3. Dans Seq (`auth-proxy.Api`), filtrer
   `@Message like '%Client requesting OAuth access token refresh%'` :
   **attendu** — au moins un refresh émis pendant l'étape 2.
   **C'est le cœur du test** : avant le fix, ce filtre reste **vide** parce que
   la garde court-circuite l'appel — la session mourait sans qu'aucune requête
   ne parte.
4. Répéter l'attente et la navigation une seconde fois (deux refresh successifs).
5. Dans la console du navigateur : aucune erreur d'auth, aucun jeton en clair.
6. Mode dégradé : arrêter le conteneur Keycloak, attendre l'expiration, naviguer
   → retour propre à l'écran de connexion (pas d'écran blanc, pas de boucle de
   requêtes) ; redémarrer Keycloak, re-login → OK.

## Notes pour /develop

- **`client-angular` est en mode code-only.** `/start` ne crée **aucune**
  branche, `/develop` écrit sur la branche **actuellement checkée** dans
  `Client/Angular/` (au 2026-08-30 : `feature/nova-rewriting-mss`), et ne
  commite ni ne pousse. `/review` re-valide build + test mais **n'ouvre pas de
  PR** (remote TFS). L'humain garde la main sur branche, commit, push et PR.
  **Vérifier la branche checkée avant de lancer.**

- **Le scope lint par défaut ne couvre pas ce code.** `/lint-angular` filtre
  `--projects=tag:scope:mss`, or l'auth vit dans `apps/weda2`, taggé
  `scope:weda2` (`apps/mss` porte `scope:mss`). D'où le champ
  **`**LintProjects**: weda2`** en tête de cette task — sans lui, le lint ne
  regarderait pas une seule ligne du code modifié.

- **Test-first obligatoire sur le correctif** (règle 1). Le test
  « `refreshToken: ''` déclenche quand même le refresh » doit être écrit et
  vérifié **RED** avant de toucher `createRefreshTokenMethod`. C'est ce test
  qui documente la panne silencieuse ; sans l'étape RED, rien ne prouve qu'il
  attrape quoi que ce soit.

- **Ne pas se contenter de supprimer la garde.** Elle protégeait un cas réel :
  l'utilisateur jamais connecté, sans agrégat du tout. Le bon prédicat n'est
  plus « ai-je un refresh token ? » mais « ai-je une session à rafraîchir ? »
  — c'est-à-dire la présence d'un `tokenAggregate` (et de son `accessToken`),
  pas celle d'un champ que l'appel n'utilise pas. Les deux tests du DOD
  encadrent exactement cette distinction.

- Les specs existantes sont nombreuses et adjacentes
  (`store-helpers.utils.spec.ts`, `authentication.utils.spec.ts`,
  `authentication-store.spec.ts`, `auth-interceptor.utils.spec.ts`,
  `refresh-token-shared.service.spec.ts`) — écrire dans leur idiome plutôt que
  d'ouvrir un fichier de specs parallèle.

- Rappel de convention Angular MSS : **pas de ngx-translate**, libellés FR en
  dur. Sans objet ici (aucun libellé), mais ne pas en introduire.
