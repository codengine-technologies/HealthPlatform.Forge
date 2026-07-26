# todo-task-172.md — Clients : arrêt du refresh et du push X-PSC-Token (Angular + mobile)

> ⏸️ **ON HOLD (décision humaine 2026-07-25)** — suit task-171, elle-même en attente
> de la bascule d'api-mail sous `*.weda.fr`. Ne pas réactiver avant que task-171 soit
> mergée et déployée.

**Repos**: client-angular, client-mobile
**Dependencies**: done-task-171
**Epic**: E013

> **Référence** : ADR-2026-07-25 « [PSC] Stratégie Refresh Token PSC Backend Pull Via
> Proxy » — chantier 5. Prérequis : task-171 (backend pull) mergée **et déployée sur
> l'environnement testé** : sans elle, retirer `X-PSC-Token` casse le mode online.
> **Prérequis supplémentaire hors dev** : api-mail servi sous `*.weda.fr` (portée du
> cookie) — aujourd'hui `mss-api.xsd2code.com` dans les `environment.prod.ts`, voir
> `questions/task-171.md`. Les flux SSE (notifications/mail events) doivent aussi
> passer en `withCredentials` côté clients.

## Objective

Le backend `api-mail` sait désormais résoudre l'access token PSC lui-même via le
psc-auth-proxy (task-171, cookie `proxy_session_id`). Les clients n'ont donc plus
aucune raison de rafraîchir ni de transporter le token PSC. Cette US **supprime le
volet PSC des deux clients** ; le refresh du token **Keycloak** (header
`Authorization: Bearer`, qui authentifie les requêtes API et prolonge la session
proxy) reste strictement inchangé.

### Contenu

**client-angular** (code-only — l'humain gère branche/commit/push TFS) :
- Supprimer `psc-token-guard.interceptor.ts` (libs/mss) et son enregistrement dans
  `app.config.ts`, ainsi que le token d'injection `MSS_PSC_REFRESH_FN` et son câblage.
- `mss-headers.interceptor.ts` : ne plus poser `X-PSC-Token` ; garantir
  `withCredentials: true` sur les appels vers `MSS_API_URL` pour que le cookie
  `proxy_session_id` parte vers api-mail.
- Purger `pscAccessToken` du state (`AuthenticationStore` / `ITokenAggregate`) là où
  il n'est plus consommé (le proxy peut continuer de le renvoyer — le client l'ignore).

**client-mobile** (full automation) :
- `mss-headers.interceptor.ts` : retirer le volet PSC (pose du header `X-PSC-Token`) ;
  conserver la logique de refresh **Keycloak** (préventif 30 s + filet 401 + 429) ;
  garantir `withCredentials: true` vers `mssApiUrl`.
- `auth-session.service.ts` / `session.model.ts` : ne plus persister `pscAccessToken`
  dans `localStorage` (`mobile_mss_session`) — une donnée d'authentification santé de
  moins sur le device.
- **Point de vigilance WebView Capacitor** : valider sur émulateur que le cookie
  `proxy_session_id` (SameSite=None) part bien vers api-mail depuis la WebView. S'il
  ne passe pas : **ne pas improviser** — ouvrir `questions/task-172.md` avec le
  constat ; le plan B de l'ADR (transmission du `ProxySessionId` renvoyé par le flux
  CIBA dans un header explicite) est une décision d'architecture à valider, pas un
  contournement silencieux.

**Mode online/offline — rien à réimplémenter côté client** : depuis task-171, le
mode est déterminé par le backend (« un token PSC est-il obtenable auprès du
proxy pour cette session ? ») et exposé par l'endpoint de statut de connexion
existant. Le client ne signale plus rien via `X-PSC-Token` ; il se contente de
consommer/afficher le statut comme aujourd'hui. Vérifier simplement qu'aucun code
client ne dérive un état « online » de la présence locale d'un `pscAccessToken`
(sinon l'adapter pour lire le statut backend).

### Hors scope

- Tout changement backend (fallback `X-PSC-Token` conservé côté api-mail jusqu'au
  chantier 6 de nettoyage, task ultérieure).
- Le refresh Keycloak et ses interceptors (`authInterceptorFn`,
  `SharedRefreshTokenService`) — intouchés.
- La TTL de l'access token Keycloak (realm) — hors périmètre.
- Aucun écran modifié (pas de passage `/stitch-design` ni `/verify-visual` attendu).

## Definition of Done

- [ ] client-angular : build passes — `npm ci && npm run build` (0 errors)
- [ ] client-angular : tests pass — `npm test` (0 failures)
- [ ] client-mobile : build passes — `npm ci && npm run build` (0 errors)
- [ ] client-mobile : tests pass — `npm test -- --watch=false --browsers=ChromeHeadless`
- [ ] Plus aucune occurrence de `X-PSC-Token` dans le code des deux clients
      (grep = 0 hit hors commentaires/changelog)
- [ ] `psc-token-guard.interceptor` supprimé (fichier + enregistrement + token DI)
      côté Angular ; tests associés supprimés ou adaptés
- [ ] `withCredentials: true` effectif sur tous les appels api-mail des deux clients
      (test unitaire d'interceptor le vérifiant)
- [ ] client-mobile : `pscAccessToken` absent de `localStorage` après login (test
      unitaire sur `AuthSessionService` + vérification manuelle)
- [ ] Refresh Keycloak inchangé : tests existants des interceptors Keycloak verts
      sans modification de comportement
- [ ] Aucun code client ne dérive l'état online/offline de la présence locale d'un
      `pscAccessToken` (l'état vient du statut de connexion backend)
- [ ] Aucun libellé/log client contenant token ou session id en clair

## Manual Test Plan

Prérequis : task-171 déployée (api-mail résout le token via le proxy), psc-auth-proxy
et api-mail lancés.

**Web (client-angular)** :
1. `cd Client/Angular/front && npm start`, se connecter via PSC.
2. DevTools → Network : sur les appels api-mail, vérifier **absence** du header
   `X-PSC-Token`, **présence** du cookie `proxy_session_id` (Request Cookies).
3. Utiliser la messagerie (liste des dossiers, lecture d'un mail, envoi d'un mail de
   test vers une boîte MSSanté de test) → tout fonctionne.
4. Laisser la session ouverte > 5 min avec activité intermittente → pas de
   déconnexion, pas d'erreur « token expiré » (le backend rafraîchit seul).
5. **Maintien de session longue durée (sans refresh PSC client)** : utiliser la
   messagerie par intermittence pendant > 35 min (une action toutes les ~10 min)
   → jamais déconnecté (chaque refresh Keycloak prolonge cookie + session proxy
   de 30 min glissants et rafraîchit les tokens broker PSC). Puis rester
   totalement inactif > 30 min → à la prochaine action, redirection login propre
   (session expirée — comportement identique à aujourd'hui).

**Mobile (client-mobile)** :
1. `cd Client/Mobile && npm start`, ou émulateur Android (AVD Pixel, config 4096M).
2. Login e-CPS (flux CIBA). Vérifier dans l'inspecteur réseau l'absence de
   `X-PSC-Token` et le bon envoi du cookie vers api-mail.
3. Inbox : les messages se chargent ; ouvrir un mail ; envoyer un mail de test.
4. `localStorage` (`mobile_mss_session`) : plus de champ `pscAccessToken`.
5. Laisser l'app ouverte > 5 min, revenir sur l'inbox → toujours fonctionnelle.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — refactoring d'architecture sécurité (suite ADR
  2026-07-25), aucune exigence DSR nouvelle
- **Exigences DSR honorées** : non applicable — renforce la posture PGSSI-S : le
  token PSC ne transite plus par le navigateur/WebView ni par le stockage local
  du device
- **INS** : non applicable — aucune manipulation de données patient
- **Authentification PS** : PSC / e-CPS via psc-auth-proxy, niveau eIDAS
  substantiel — flux de login inchangés (PSC web + CIBA mobile)
- **Habilitations** : inchangées — contrôles côté backend (task-171)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : côté client, aucun évènement nouveau ; les échecs de session
  restent tracés côté proxy et api-mail (task-171)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non applicable côté client — bénéfice : suppression d'un
  token d'accès à des DSCP du `localStorage` mobile
- **AIPD / impact RGPD** : inchangé — réduction de surface (token PSC retiré du
  poste client)
