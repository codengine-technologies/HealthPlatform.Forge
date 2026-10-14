# todo-task-370.md — La session de weda2 reste valide tant que le médecin travaille, et se ferme vraiment quand il s'absente

**Repos**: client-angular, api-mail (catalogue e2e `Api/Mail/e2e/scenarios.yml` seulement)
**Dependencies**: — (aucune). À coordonner avec task-365 (surveillance de la session partagée avec Weda), qui touche aux mêmes services d'authentification.
**Epic**: E016
**Single frontend**: true
**Priorité**: **1** — hors de Weda, la messagerie tombe en « session expirée » environ 4 min après la connexion ; sur un poste de cabinet partagé, la session d'un médecin absent ne se ferme jamais.

> **Origine.** Audit de détection de bugs du client Angular du 2026-10-13
> (`Docs/audits/client-angular-audit-bugs-20261013.md`, **ANG-06 ✔, ANG-07 ✔, ANG-22, ANG-23, ANG-24, ANG-66, ANG-67, ANG-69, ANG-71**).

## Ce qui est établi

- **ANG-06** — `auth-interceptor.utils.ts:101-111` (`shouldSkipRequest`) laisse passer sans rafraîchissement toute URL qui ne vise ni `apiEndpoint` ni `authEndpoint`, donc **tous les appels à api-mail**. Aucun rafraîchissement préventif n'existe. Avec un jeton de 120 s et la tolérance d'api-mail de 2 min, les appels répondent 401 environ 4 min après la connexion ; le flux SSE (jeton en query string) meurt et n'est jamais rouvert ; `error.interceptor.ts:104-107` tait ces 401.
- **ANG-07** — `auto-logout.service.ts:207-240` : `initialize()` n'est appelé nulle part ; à l'échéance, `triggerLogout()` journalise « Auth store not initialized » et ne déconnecte pas. Le bouton « Se déconnecter » du dialogue ne fait rien. Un réveil de veille au-delà de la fenêtre n'ouvre aucun dialogue.
- **ANG-22** — `auth.interceptor.ts:122-139` : le `catchError` de perte de session est placé après le rejeu ; un 409 métier ou une coupure réseau pendant un rafraîchissement déconnecte le médecin et révoque la session du proxy (partagée avec Weda). `$refreshToken` appelle `login()` sur toute erreur.
- **ANG-23** — « Se connecter avec Pro Santé Connect » (écran « PSC requis ») navigue vers `/login`, une route qui n'existe pas ; `loginPsc()` n'est jamais appelé.
- **ANG-24 / ANG-66** — Aucun garde-fou contre une boucle callback ↔ proxy ; un retour d'erreur OAuth (annulation PSC) laisse un spinner infini.
- **ANG-67 / ANG-69 / ANG-71** — Créneau de rafraîchissement partagé libéré au désabonnement d'un appelant ; rechargement inutile au callback qui perd la page demandée ; repli sur `preferred_username` jamais appliqué (`??` après `join`).

## Objective

Que le médecin qui travaille ne soit **jamais** déconnecté par un défaut technique (jeton, coupure réseau, erreur métier), et que le médecin qui s'absente le soit **toujours** à l'échéance prévue, en mode autonome comme dans un onglet ouvert depuis Weda.

### Périmètre

1. **api-mail origine de confiance** de l'intercepteur d'authentification : rafraîchissement sur échéance et rejeu sur 401 pour `MSS_API_URL`, Bearer posé une seule fois.
2. **Rafraîchissement préventif** avant `exp` ; le flux SSE se rouvre avec le jeton neuf.
3. **Perte de session seulement sur refus explicite** du rafraîchissement (401, 400, `invalid_grant`) ; une erreur métier de la requête rejouée remonte telle quelle ; plus de `login()` dans `$refreshToken`.
4. **Déconnexion pour inactivité réelle** : le service reçoit le store ; `timeRemaining <= 0` (réveil de veille) déconnecte sans dialogue ; le bouton du dialogue déconnecte. Le mode embarqué reste régi par Weda (inchangé).
5. **« Se connecter avec Pro Santé Connect »** branché sur `loginPsc()`, avec `state` CSRF.
6. **Callback** : relances bornées puis écran d'erreur avec « Réessayer » ; `error` / `error_description` affichés ; pas de rechargement superflu.
7. Corrections mineures : `finalize` du créneau partagé avant `shareReplay` ; `||` pour le repli `preferred_username`.

## Definition of Done

- [ ] Build et tests weda2 verts
- [ ] Tests unitaires rouges d'abord :
  - [ ] une requête vers `MSS_API_URL` avec un jeton expiré déclenche un rafraîchissement puis part avec le jeton neuf ; un 401 d'api-mail est rejoué une fois
  - [ ] le jeton est rafraîchi avant `exp` sans requête déclenchante ; le flux SSE se rouvre avec le nouveau jeton
  - [ ] un 409 sur la requête rejouée remonte en 409, sans déconnexion ; un statut 0 pendant le rafraîchissement ne déconnecte pas ; un 400 `invalid_grant` déconnecte
  - [ ] à l'échéance d'inactivité, `logout()` du store est appelé ; au réveil après l'échéance, aussi ; le bouton du dialogue aussi
  - [ ] « Se connecter avec Pro Santé Connect » appelle `loginPsc()` avec un `state` stocké
  - [ ] au-delà de N relances du callback, l'écran d'erreur s'affiche ; un `?error=` affiche son message
  - [ ] l'annulation d'un abonné ne libère pas le créneau de rafraîchissement en vol
- [ ] Scénario E2E-AUTH-001 « Rester connecté quand le jeton d'accès expire » : passé du mode `humain` à `headless` si le banc le permet (jeton simulé à courte échéance), version montée, implémenté dans weda2 ; sinon la raison est consignée au catalogue
- [ ] Scénario E2E-AUTH-003 « Déconnexion après inactivité » ajouté au catalogue (angular `requis` en mode autonome ; mobile `non-applicable` — pas de déconnexion pour inactivité dans l'application mobile, à confirmer au `/start`)
- [ ] Trou du filet : ligne ajoutée dans `conventions/e2e.md` (le filet simule des jetons à échéance lointaine et ne pouvait pas voir ANG-06)
- [ ] Aucun jeton, `sub` ni adresse ajouté aux journaux

## Manual Test Plan

1. weda2 en onglet autonome, AppHost de dev (Keycloak local) : travailler 10 min dans la messagerie (ouvrir des mails, rédiger) → aucun « Session expirée » ; un nouveau mail reçu apparaît en direct.
2. Couper le Wi-Fi 5 s pendant que le jeton est rafraîchi → pas de déconnexion.
3. Rester inactif jusqu'au dialogue, ne rien faire → déconnexion et écran de connexion. Recommencer en cliquant « Se déconnecter ».
4. Mettre le poste en veille au-delà de la durée d'inactivité, le réveiller → déconnexion immédiate.
5. Compte sans boîte ni jeton PSC : écran « PSC requis », bouton « Se connecter avec Pro Santé Connect » → redirection PSC.
6. Annuler la connexion PSC → message d'erreur avec « Réessayer », pas de spinner infini.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif de la session de la plateforme
- **Exigences DSR honorées** : non applicable — rétablit le socle PGSSI-S (verrouillage de session après inactivité)
- **INS** : non applicable
- **Authentification PS** : PSC / e-CPS (niveau eIDAS substantiel) inchangés ; la déconnexion pour inactivité du poste partagé redevient effective
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : déconnexion pour inactivité et perte de session journalisées côté client (cause seulement, sans jeton ni `sub`)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — protège l'accès aux DSCP sur un poste partagé
- **AIPD / impact RGPD** : inchangé
