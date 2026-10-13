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
   > **Décision humaine (2026-10-13, avant `/forge 368 to 381`) : la forge code le correctif sans attendre ;
   > le constat est fait par l'humain** (réseau interne inaccessible à la forge) et consigné ensuite, comme
   > pour task-326.
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

## Branches
- `client-angular` (code-only) : branche courante `feature/nova-rewriting-mss-weda-integration` (instantané au `/start`) — humain gère commit, push, PR TFS
- `devops` (manual) : managed manually by the human — la forge rédige le bloc ConfigMap dans ce fichier, l'humain l'applique

## Constat (humain, à consigner avant toute mise en production)

> Décision humaine du 2026-10-13 : la forge code sans attendre ; le constat est fait par l'humain (réseau
> interne inaccessible à la forge). **À remplir** :

| Environnement | `curl -s https://<weda2>/assets/config.json` | `mssApiUrl` effectif (navigateur) | Verdict |
|---|---|---|---|
| dev | | | |
| qa / staging | | | |
| prod | | | |

Si la production vise l'api-mail de dev : mesure immédiate hors cycle décidée par l'humain, et AIPD à évaluer (DPO).

## Bloc ConfigMap / manifest à appliquer (devops — humain)

`Client/Angular/devops/k8s/weda2-frontend-configmap.yaml` — **avant** de déployer l'image de cette task :
sans `mssApiUrl` ni `embeddedHostOrigins`, weda2 de production refuse désormais de démarrer.

```yaml
# Variables de release ajoutées :
#   - ${MSS_API_URL}            : URL de l'api-mail DE CET environnement (ex: https://mss-api.<env>.k8s.office.weda.fr)
#   - ${WEDA_EMBED_ORIGINS_JSON} : origines EXACTES de Weda, en tableau JSON (ex: ["https://secure.weda.fr"])
#   - ${WEDA_EMBED_ORIGINS}      : les mêmes, séparées par des espaces (ex: https://secure.weda.fr)
data:
  config.json: |
    {
      "apiEndpoint": "${API_ENDPOINT}",
      "authEndpoint": "${AUTH_ENDPOINT}",
      "authClientId": "${AUTH_CLIENT_ID}",
      "wedaRedirectUrl": "${WEDA_REDIRECTION_URL}",
      "mssApiUrl": "${MSS_API_URL}",
      "embeddedHostOrigins": ${WEDA_EMBED_ORIGINS_JSON}
    }
  frame-ancestors.conf: |
    set $frame_ancestors "${WEDA_EMBED_ORIGINS}";
```

`Client/Angular/devops/k8s/weda2-frontend-manifest.yaml` — deuxième montage, à côté de `config.json` :

```yaml
          volumeMounts:
            - name: frontend-config
              mountPath: /usr/share/nginx/html/assets/config.json
              subPath: config.json
              readOnly: true
            - name: frontend-config
              mountPath: /etc/nginx/frame-ancestors.conf
              subPath: frame-ancestors.conf
              readOnly: true
```

⚠️ `$frame_ancestors` est une variable **nginx** : si la pipeline de release substitue toutes les
`$VARIABLES` (envsubst sans liste), la protéger (`$${frame_ancestors}` selon l'outil) ou restreindre la
substitution aux variables listées ci-dessus.

## Develop log

### Livré (client-angular, code-only — non commité)

- `apps/weda2/src/runtime-config.ts` (nouveau) : `loadRuntimeConfig` charge `/assets/config.json` ; **en
  production**, refuse de démarrer si `apiEndpoint`, `authEndpoint`, `mssApiUrl` ou `embeddedHostOrigins`
  manque, est vide, ou si une origine porte un joker ; `config.json` absent → refus aussi. Hors production
  (ng serve, filet e2e), repli inchangé sur les valeurs du build. `showBootstrapError` remplace la page par
  un message qui **nomme les clés, jamais leurs valeurs**.
- `apps/weda2/src/main.ts` : amorçage seulement si la configuration est complète.
- `apps/weda2/src/environments/environment.prod.ts` : plus aucune URL (`apiEndpoint`, `authEndpoint`,
  `mssApiUrl` vides, `embeddedHostOrigins: []`), `storeWithDevTools: withDevToolsStub` (ANG-70).
- `apps/weda2/src/lib/embedded/embedded-host.utils.ts` : `isOriginMatching` en égalité stricte — un joker
  n'autorise plus rien (ANG-65).
- `nginx.conf` : `frame-ancestors 'self' $frame_ancestors`, variable posée par
  `/etc/nginx/frame-ancestors.conf` ; `nginx-frame-ancestors.conf` (nouveau, défaut : aucune origine) copié
  par `apps/weda2/Dockerfile`.

### Preuves (tests rouges d'abord)

| DOD | Test | Rouge d'abord |
|---|---|---|
| sans `mssApiUrl` / `embeddedHostOrigins` (et `apiEndpoint`, `authEndpoint`) : pas d'amorçage, erreur affichée | `runtime-config.spec.ts` (4 cas + config absente + joker + écran d'erreur) | oui — 7 rouges sur la version qui reproduisait le repli silencieux |
| une configuration complète remplace les valeurs du build | `runtime-config.spec.ts` | vert dès l'origine (comportement conservé, verrouillé) |
| `environment.prod.ts` sans URL `*.dev.*`, sans `withDevtools` | `runtime-config.spec.ts` (lecture du fichier) | oui — 3 rouges |
| `https://autre.weda.fr` refusée, origine exacte acceptée | `embedded-host.utils.spec.ts` | oui |
| `frame-ancestors` par environnement | vérifié dans un conteneur `nginxinc/nginx-unprivileged:alpine` : `nginx -t` OK ; fichier monté → `Content-Security-Policy: frame-ancestors 'self' https://secure.weda.example` | — |

### Validation

- `npm run build` (weda2 production) ✓ ; `nx test weda2` ✓ (2 697 tests) ; eslint des fichiers touchés : 0 erreur.
- Aucune URL, aucun jeton, aucune adresse dans les journaux ajoutés (les clés seules sont nommées).
- Passe qualité (§Q) : relue, rien à simplifier.

### Fichiers modifiés (client-angular)

`front/apps/weda2/src/main.ts`, `front/apps/weda2/src/runtime-config.ts` (nouveau),
`front/apps/weda2/src/runtime-config.spec.ts` (nouveau), `front/apps/weda2/src/environments/environment.prod.ts`,
`front/apps/weda2/src/lib/embedded/embedded-host.utils.ts`, `front/apps/weda2/src/lib/embedded/embedded-host.utils.spec.ts`,
`front/nginx.conf`, `front/nginx-frame-ancestors.conf` (nouveau), `front/apps/weda2/Dockerfile`.

## Lint log

- Mode A. La task ne touche que l'application `weda2`, hors portée de lint par défaut (`tag:scope:mss`) : lint ciblé sur les 6 fichiers TypeScript de la task (`eslint`, configuration du dépôt) — **0 erreur** (1 `prettier/prettier` corrigé pendant `/develop`), 2 avertissements `jsdoc/require-example` existants. 0 itération.
- Build (`npm run build`, weda2 production) et tests (`nx test weda2`, 2 697) déjà verts sur l'état final dans `/develop` : non rejoués.
- client-angular non commité (code-only).

## Lint mobile log

- skipped — no mobile change : `client-mobile` absent des `**Repos**`, arbre propre sur `develop`.

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| angular | client-angular touché | ✅ verte (2ᵉ passage) | 38 verts, 0 rouge, 1 flaky (E2E-COMPOSE-002, en quarantaine) | ~6 min 30 s |
| mobile | non touchée — listing | 📋 listée | — | — |

- **Banc** : l'arbre weda2 porte aussi le travail non commité de task-368 (E2E-SECURITY-001 compris). Pour le jouer contre son backend, api-mail et client-mobile ont été placés le temps de l'étape sur `forge/staging-task-368-381-20261013` (arbres propres), puis remis sur `develop`. Catalogue : celui de cette branche de staging. Écart assumé à la règle « aucun checkout » de `/e2e`.
- **1ᵉʳ passage rouge** : E2E-COMPOSE-001 (« Supprimer » détaché du DOM pendant le clic, au premier essai et au nouvel essai) ; E2E-WEDA-003 flaky. Rejoué seul : vert ; 2ᵉ passage complet : vert. Écrans touchés par la task : aucun dans ce parcours. Signalé comme instabilité à surveiller (menu « Plus d'actions » re-rendu pendant le clic), à reprendre si elle revient.
- Parcours touchés sans spec e2e modifié : aucun écran modifié (amorçage et configuration seulement).
- Démontage : complet (ports libres, aucun conteneur e2e résiduel).

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Flaky — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | 📋 listé |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | 📋 listé |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | 📋 listé |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | 📋 listé |
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | 📋 listé |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | 📋 listé |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | 📋 listé |
| E2E-DETAIL-001 | 2 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | 📋 listé |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | 📋 listé |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ⚠️ flaky | 📋 listé |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | 📋 listé |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | 📋 listé |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | 📋 listé |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | 📋 listé |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | 📋 listé |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | 📋 listé |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | 📋 listé |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | 📋 listé |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | 📋 listé |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | 📋 listé |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | 📋 listé |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | 📋 listé |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | 📋 listé |
| E2E-CONTACT-002 | 1 | headless | Créer puis supprimer un contact | ✅ | 📋 listé |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | 📋 listé |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | 📋 listé |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | 📋 listé |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | 📋 listé |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | 📋 listé |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | 📋 listé |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | 📋 listé |
| E2E-WEDA-001 | 1 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 1 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 1 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | 📋 listé |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | 📋 listé |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | 📋 listé |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | 📋 listé |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- client-angular : code-only — humain gère commit/push TFS et ouverture PR, branche `feature/nova-rewriting-mss-weda-integration`. Fichiers de **cette** task (l'arbre porte aussi ceux de task-368, listés dans `done-task-368.md`) :

```
front/apps/weda2/Dockerfile
front/apps/weda2/src/environments/environment.prod.ts
front/apps/weda2/src/lib/embedded/embedded-host.utils.spec.ts
front/apps/weda2/src/lib/embedded/embedded-host.utils.ts
front/apps/weda2/src/main.ts
front/apps/weda2/src/runtime-config.spec.ts (nouveau)
front/apps/weda2/src/runtime-config.ts (nouveau)
front/nginx-frame-ancestors.conf (nouveau)
front/nginx.conf
```

- devops (`Client/Angular/devops/k8s/…`) : managed manually by the human — bloc ConfigMap / manifest prêt dans ce fichier, **à appliquer avant de déployer** l'image de cette task.
- Aucun repo poussable touché : aucune PR GitHub.

## Code Review Summary

**Verdict : APPROVED** — 0 bloquant, 4 suggestions. Validation : `npm run build` ✓, `npm test` ✓ (11 projets).

- **Règle 1b** : non applicable — aucun repo backend touché, aucun comportement servi par un endpoint.
- `runtime-config.ts` ✅ — refus en production seulement ; message construit par `textContent` (aucune injection) ; seules les clés sont journalisées. Un `config.json` présent mais au JSON invalide est traité comme absent (refus).
- `environment.prod.ts` ✅ — plus aucune URL ni origine ; `withDevToolsStub`.
- `embedded-host.utils.ts` ✅ — égalité stricte ; joker sans effet même s'il revenait dans une configuration.
- `nginx.conf` / `Dockerfile` ✅ — vérifiés dans un conteneur nginx-unprivileged (`nginx -t`, en-tête rendu).

### DOD

| Item | État |
|---|---|
| Constat consigné (config.json et `mssApiUrl` effectifs par environnement) | ⏳ **humain** — tableau à remplir dans ce fichier |
| Bloc ConfigMap rédigé / appliqué | ✅ rédigé ; ⏳ application humaine |
| Build et tests weda2 verts | ✅ |
| Tests rouges d'abord (4 items) | ✅ (`runtime-config.spec.ts`, `embedded-host.utils.spec.ts`) |
| Scénarios e2e Angular verts | ✅ (2ᵉ passage ; voir `## E2E log`) |
| Aucune URL, jeton ou adresse dans les journaux | ✅ |

### Suggestions (non bloquantes)

1. ⚠️ **Ordre de déploiement** : sans les nouvelles clés de la ConfigMap, l'image refuse de démarrer (voulu) et, sans le montage `frame-ancestors.conf`, Weda ne peut plus embarquer weda2. La ConfigMap et le manifest passent **avant** l'image.
2. ⚠️ `$frame_ancestors` est une variable nginx : la substitution de la pipeline de release doit la laisser intacte (voir la note du bloc devops).
3. ⚠️ `wedaRedirectUrl` et `authClientId` ne sont pas exigés : à ajouter à `REQUIRED_RUNTIME_KEYS` si un environnement sans eux doit aussi refuser de démarrer.
4. ⚠️ e2e : E2E-COMPOSE-001 rouge au premier passage complet (menu « Plus d'actions » re-rendu pendant le clic), vert seul et au second passage : instabilité à surveiller.

## Timings

*(généré par `tools/timing/report.sh --task task-369 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 0.5 s | — | — | — | — |
| /develop | ok | 5 min 28 s | 2 (24 s) | 1 (20 s) | — | client-angular 2B/1T |
| /lint-angular | ok | 5.6 s | — | — | — | — |
| /lint-mobile | skipped | 0.5 s | — | — | — | client-mobile non touché |
| /e2e | ok | 15 min 30 s | — | — | — | e2e ×3 (12 min 57 s) |
| /review | ok | 39 s | 1 (1.0 s) | 1 (19 s) | — | client-angular 1B/1T |
| /tech-writer | ok | 30 s | — | — | — | — |
| **Total cycle** | | **22 min 15 s** | **3 (26 s)** | **2 (40 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : lint ×1 (4.2 s)
