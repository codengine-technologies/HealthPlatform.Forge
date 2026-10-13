# todo-task-369.md — weda2 déployé parle à l'api-mail de son environnement, et n'accepte que l'hôte Weda attendu

**Repos**: client-angular, devops
**Dependencies**: — (aucune)
**Epic**: E019
**Single frontend**: true
**Priorité**: **0** — si la ConfigMap du dépôt est celle qui tourne, weda2 de production envoie le jeton Keycloak du praticien à l'api-mail de **dev**. **Première action, avant tout code : vérifier la configuration réellement déployée.**

> **Origine.** Audit de détection de bugs du client Angular du 2026-10-13
> (`Docs/audits/client-angular-audit-bugs-20261013.md`, **ANG-05 ✔, ANG-65, ANG-70**).

## Ce qui est établi

- `apps/weda2/src/environments/environment.prod.ts:17` : `mssApiUrl: 'https://mss-api.dev.k8s.office.weda.fr'`.
- `Client/Angular/devops/k8s/weda2-frontend-configmap.yaml:21-29` : le `config.json` monté au runtime ne fournit que `apiEndpoint`, `authEndpoint`, `authClientId` et `wedaRedirectUrl`.
- `apps/weda2/src/main.ts:25-39` : `Object.assign(environment, runtimeConfig)` — `mssApiUrl` garde donc sa valeur de build ; une configuration absente est seulement journalisée (`console.warn`).
- `mssHeadersInterceptor` envoie le Bearer du praticien vers `mssApiUrl`, avec `withCredentials`.
- **ANG-65** : `embeddedHostOrigins: ['https://*.weda.fr']` et `frame-ancestors 'self' https://*.weda.fr` (`nginx.conf:51`) : toute page d'un sous-domaine `weda.fr` peut embarquer weda2 et devenir l'hôte de confiance du pont (désigner la boîte, injecter une intention d'envoi, recevoir les documents importés).
- **ANG-70** : `environment.prod.ts:16` branche le vrai `withDevtools` : l'état des stores est poussé vers l'extension Redux DevTools si elle est installée.

## Objective

Que chaque instance déployée de weda2 vise **l'api-mail de son propre environnement**, refuse de démarrer si une clé de configuration obligatoire manque, et n'accepte comme hôte d'embarquement que l'origine exacte de l'application Weda.

### Périmètre

1. **Constat d'abord** (humain, lecture) : `config.json` réellement servi par chaque environnement (`curl https://<weda2>/assets/config.json`) et valeur effective de `mssApiUrl` dans le navigateur. Consigné dans le task file **avant** tout correctif. Si la production vise le dev : mesure immédiate hors cycle décidée par l'humain.
2. **ConfigMap** (`devops`, appliquée par l'humain) : `mssApiUrl` et `embeddedHostOrigins` ajoutés, avec leurs variables de release par environnement. La forge rédige le bloc dans le task file.
3. **Amorçage** : `main.ts` refuse de démarrer (écran d'erreur explicite) si `apiEndpoint`, `authEndpoint`, `mssApiUrl` ou `embeddedHostOrigins` manque à la configuration runtime, au lieu de retomber sur les valeurs de build.
4. **`environment.prod.ts`** : plus aucune URL de dev ; `storeWithDevTools: withDevToolsStub`.
5. **Origines d'embarquement** : liste fermée des origines exactes de Weda par environnement (plus de joker `*.weda.fr`), dans `embeddedHostOrigins` et dans `frame-ancestors`.

## Definition of Done

- [ ] **Constat consigné** dans le task file : `config.json` et `mssApiUrl` effectifs par environnement
- [ ] Bloc ConfigMap rédigé dans le task file (prêt à appliquer), appliqué par l'humain
- [ ] Build et tests weda2 verts
- [ ] Tests unitaires rouges d'abord :
  - [ ] une configuration runtime sans `mssApiUrl` (ou sans `embeddedHostOrigins`) empêche l'amorçage et affiche l'erreur
  - [ ] une configuration complète remplace bien les valeurs de build
  - [ ] `environment.prod.ts` ne contient aucune URL `*.dev.*` (test de non-régression sur le fichier)
  - [ ] une origine `https://autre.weda.fr` n'est plus acceptée comme hôte ; l'origine exacte de Weda l'est
- [ ] Les scénarios e2e existants (voie Angular) restent verts — le filet sert la configuration par sa propre `config.json`
- [ ] Aucune URL, jeton ou adresse ajouté aux journaux

## Manual Test Plan

1. Pour chaque environnement : `curl -s https://<weda2>/assets/config.json` → `mssApiUrl` pointe vers l'api-mail de **cet** environnement.
2. Ouvrir weda2, onglet Réseau : les appels `…/api/v1/mail/…` partent vers l'api-mail attendue.
3. Retirer `mssApiUrl` du `config.json` d'un environnement de test : weda2 affiche l'erreur d'amorçage au lieu de démarrer.
4. Embarquer weda2 depuis une page d'un autre sous-domaine `weda.fr` : le pont reste inactif ; depuis Weda Échanges, il fonctionne.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif de configuration de la plateforme
- **Exigences DSR honorées** : non applicable — aucune exigence fonctionnelle nouvelle
- **INS** : non applicable — aucun trait d'identité manipulé
- **Authentification PS** : PSC / e-CPS inchangés ; la task empêche que le jeton du praticien parte vers un environnement non prévu
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — un jeton de production envoyé hors de son environnement HDS est une fuite à qualifier
- **AIPD / impact RGPD** : **à évaluer** si le constat établit que la production a visé le dev (DPO) ; inchangé sinon
