# todo-task-285.md — Clôture immédiate de la session de messagerie à la déconnexion, sur tous les pods

**Repos**: api-mail, client-angular, client-mobile, client-blazor
**Dependencies**: —
**Epic**: E009

## Objective

Quand un professionnel de santé se déconnecte, ses connexions IMAP et SMTP
MSSanté doivent tomber **immédiatement**, et pas au bout du délai d'inactivité.
Aujourd'hui elles survivent : le praticien croit être sorti, mais une session
authentifiée auprès de l'opérateur MSSanté reste ouverte en son nom pendant
plusieurs minutes.

Deux causes distinctes, à traiter ensemble :

1. **Les frontends ne préviennent pas le backend.** `client-angular` et
   `client-mobile` n'émettent aucun ordre de clôture à la déconnexion ; seul
   `client-blazor` appelle l'API, et pas systématiquement au bon moment. Le
   praticien part vers la déconnexion du proxy sans que la messagerie
   l'apprenne.
2. **L'ordre ne porte que sur un pod.** Le mécanisme de clôture existe déjà côté
   backend, mais le registre des sessions est **propre à chaque processus**.
   L'API tourne en plusieurs instances : l'ordre atterrit sur celle qui répond,
   ferme la session qu'elle détient, et laisse intactes celles des autres
   instances. Le praticien peut donc avoir des connexions ouvertes sur
   plusieurs instances et n'en voir tomber qu'une.

La US ferme les deux : les trois frontends émettent l'ordre **avant** de
quitter la session, et l'ordre atteint **toutes** les instances de l'API.

## Contexte constaté (pour l'implémentation)

- Le point d'entrée `POST /api/v1/sync/logout` existe et fonctionne — il ferme
  la session **de l'instance qui reçoit l'appel**.
- Le registre des sessions est en mémoire du processus, indexé par la paire
  (adresse MSSanté du praticien, identifiant de session cliente).
- L'identifiant de session cliente vient d'un en-tête envoyé par le client.
  **Seul `client-mobile` l'envoie aujourd'hui** (acquis de task-282) ;
  `client-angular` et `client-blazor` retombent sur l'identifiant de session du
  fournisseur d'identité. Conséquence assumée du périmètre retenu (voir règles
  métier) : sur ces deux frontends, « la session courante » vaut de fait pour la
  session d'authentification entière — deux onglets Angular du même praticien
  partagent un identifiant, donc se déconnectent ensemble.
- **Ce repli est fonctionnel aujourd'hui, mais il n'est garanti par rien.**
  Vérifié le 2026-09-01 sur deux jetons `client-angular` successifs séparés d'un
  refresh : `jti` change, l'identifiant de session du fournisseur d'identité
  reste stable. Il ne s'agit donc pas du défaut de rotation corrigé par
  task-282 — ce défaut portait sur des jetons *sans* identifiant de session, qui
  retombaient sur `jti`, unique par jeton. L'alignement des deux frontends sur
  l'en-tête fait l'objet d'une US séparée (voir `questions/task-286.md`) : il
  rendra le périmètre de la règle 2 uniforme, mais **n'est pas un prérequis** de
  cette US.
- L'infrastructure de diffusion inter-instances est déjà en place (bus de
  messages et cache distribué). Le choix du véhicule appartient à
  l'implémentation, pas à cette US.

## Règles métier

1. **L'ordre précède la déconnexion.** Le frontend contacte l'API pour ordonner
   la fin de session **avant** de purger sa session locale et avant de rediriger
   vers la déconnexion du proxy. Aucun frontend ne quitte l'écran authentifié
   sans avoir émis l'ordre.

2. **Périmètre : la session cliente courante.** L'ordre ferme la session
   identifiée par (praticien, identifiant de session cliente). Un praticien
   connecté sur un autre appareil **conserve** sa session sur cet appareil.

3. **Un échec n'emprisonne jamais le praticien.** Si l'API ne répond pas
   (délai dépassé, erreur serveur, réseau coupé), la déconnexion se poursuit
   quand même : session locale purgée, redirection vers le proxy. L'échec est
   journalisé. La fermeture reste alors garantie par le filet serveur existant
   (expiration de session et balayage périodique).

4. **L'ordre atteint toutes les instances.** Une fois l'ordre accepté, aucune
   instance de l'API ne conserve de connexion IMAP ou SMTP ouverte pour cette
   session — y compris les instances qui n'ont pas reçu l'appel.

5. **L'API n'attend pas la confirmation de toutes les instances pour répondre.**
   Elle accuse réception dès que l'ordre est émis. Le praticien ne paie pas le
   temps de propagation.

6. **Rejouer l'ordre est sans effet de bord.** Un second appel pour une session
   déjà close répond normalement, sans erreur — le frontend peut réessayer, et
   deux onglets peuvent se déconnecter en même temps.

## Risque accepté

**Une requête en vol peut rouvrir une connexion juste après l'ordre.** Le
périmètre retenu est une diffusion simple : on ferme ce qui est ouvert au
moment de l'ordre, sans marquer la session comme révoquée. Une requête partie
avant la déconnexion et arrivée après peut donc recréer une session sur une
instance. La fenêtre est courte et la session recréée retombe sur le filet
d'expiration existant. Arbitrage humain du 2026-09-01 ; à revoir si la
journalisation montre des ré-ouvertures effectives.

## Definition of Done

- [ ] Build passe sur chaque repo listé (0 erreur)
- [ ] Tests passent sur chaque repo listé (0 échec)
- [ ] Test d'intégration : l'ordre reçu par une instance ferme la session
      détenue par **une autre** instance
- [ ] Test d'intégration : l'ordre sur une session inexistante ou déjà close
      répond en succès, sans erreur (règle 6)
- [ ] Test d'intégration : la réponse de l'API n'attend pas la propagation
      (règle 5)
- [ ] >= 1 test unitaire par nouveau handler backend
- [ ] Test unitaire par frontend : la déconnexion appelle l'API **avant** de
      purger la session locale (règle 1)
- [ ] Test unitaire par frontend : la déconnexion aboutit même quand l'appel
      échoue ou expire (règle 3)
- [ ] `client-mobile` transmet son identifiant de session cliente dans l'ordre
- [ ] Évènements PGSSI-S journalisés : ordre de clôture reçu, nombre de
      sessions effectivement fermées, échec de diffusion, échec d'émission
      côté client
- [ ] Aucune donnée de santé en clair dans les logs (contenu de message, INS,
      pièce jointe, contenu CDA) — l'identification du praticien reste limitée
      à ce qu'exige l'imputabilité PGSSI-S
- [ ] `data-testid` sur le contrôle de déconnexion des trois frontends

## Manual Test Plan

**Le banc local reproduit le multi-pods** : l'AppHost lance l'API en 5
instances, c'est exactement le cas à couvrir.

1. Démarrer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
   (profil `https`). Vérifier dans le tableau de bord Aspire que les 5 instances
   de `mss-mail-api` sont vertes.
2. Démarrer un frontend :
   - mobile : `cd Client/Mobile && npm start`
   - angular : `cd Client/Angular && npm start`
   - blazor : `cd Client/Blazor && dotnet run`
3. Se connecter avec un compte MSSanté de test, ouvrir la boîte de réception et
   naviguer dans plusieurs dossiers — l'objectif est que **plusieurs** instances
   ouvrent une connexion IMAP (la répartition de charge les distribue).
4. Dans Seq (`http://localhost:5342`), relever les instances qui ont créé une
   session pour ce praticien.
5. Se déconnecter depuis le frontend.
6. **Attendu** : dans Seq, un ordre de clôture reçu, puis une fermeture de
   session sur **chacune** des instances relevées à l'étape 4 — en quelques
   secondes, sans attendre le délai d'inactivité de 5 minutes.
7. **Attendu** : côté opérateur MSSanté, plus aucune session IMAP ouverte pour
   ce compte (visible dans les journaux du serveur de test).
8. Répéter les étapes 2 à 5 sur les deux autres frontends.
9. **Cas dégradé** : arrêter le backend, puis se déconnecter depuis le
   frontend. **Attendu** : la déconnexion aboutit, le praticien arrive bien sur
   l'écran de connexion, et l'échec est visible dans la console du frontend.
10. **Cas multi-appareils** : se connecter sur mobile ET sur angular avec le
    même compte, se déconnecter du mobile. **Attendu** : la session angular
    reste fonctionnelle (règle 2).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors périmètre fonctionnel DSR — exigence de sécurité
  transverse au socle MSSanté déjà référencé
- **Exigences DSR honorées** : aucune exigence DSR fonctionnelle nouvelle. La US
  sert la PGSSI-S (§ authentification, § journalisation, § imputabilité) et
  réduit la durée de vie d'une session MSSanté authentifiée sans utilisateur.
  **Le rattachement DSR précis est à confirmer avec le référent Ségur** — je ne
  cite pas de code d'exigence que je n'ai pas vérifié.
- **INS** : non applicable — la déconnexion ne manipule aucune donnée patient
  ni aucun identifiant national de santé.
- **Authentification PS** : PSC / e-CPS via le proxy d'identité, niveau eIDAS
  substantiel. La US ne modifie pas l'authentification ; elle traite sa
  terminaison.
- **Habilitations** : non applicable — tout praticien authentifié peut clore sa
  propre session, et seulement la sienne. L'ordre ne peut pas viser la session
  d'un autre praticien.
- **Interop CI-SIS** : non applicable — aucun échange métier, aucun document.
- **Tracé PGSSI-S** : ordre de clôture reçu (praticien, session, horodatage),
  nombre de sessions effectivement fermées, échec de diffusion inter-instances,
  échec d'émission côté client. Conservation alignée sur les journaux d'accès
  existants de l'API (6 ans).
- **Consentement patient** : non applicable.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : oui — l'API héberge des données de santé à caractère
  personnel (contenu des messages MSSanté). La US ne crée aucun nouveau
  traitement de DSCP ; elle raccourcit la fenêtre d'exposition d'une session
  ouverte.
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement de données
  personnelles. Effet favorable sur la minimisation (durée de conservation
  d'une session active réduite).
- **MSSanté** : les connexions closes sont celles de l'API LPS de l'opérateur
  MSSanté (adresse personnelle PS). Aucun en-tête ni certificat n'est modifié
  par cette US.

## Branches

Branche unique sur les repos pushables : `feat/task-285-logout-closes-mail-session-all-pods`

- `api-mail` (pushed) — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-285-logout-closes-mail-session-all-pods
- `client-blazor` (pushed) — https://github.com/codengine-technologies/HealthPlatform.Client/tree/feat/task-285-logout-closes-mail-session-all-pods
- `client-mobile` (pushed) — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-285-logout-closes-mail-session-all-pods
- `dtos-mss` (pushed, auto-inclus) — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-285-logout-closes-mail-session-all-pods
- `client-angular` (code-only) — aucune branche créée. `/develop` écrit sur la branche checkée dans `Client/Angular/` ; snapshot au `/start` : `feature/nova-rewriting-mss`. L'humain garde branche, commit, push et PR TFS.

### Observations du pré-flight (2026-09-01)

- Tous les repos pushables en scope étaient sur `develop`, arbre propre.
- `interop-cda` (`interop/`) **n'a pas de `.git`** — comme `host/Modules`,
  déjà documenté dans CLAUDE.md. Le pré-flight ne mesure donc rien sur ces deux
  repos : toute commande git qui les cible répond pour le dépôt de la forge.
  Hors périmètre de cette US, mais l'avertissement de CLAUDE.md vaut pour les
  deux, pas seulement `host`.
- `api-mail` porte `f3f0b6b` (« Add MOTCOV2 server config ») — vérifié présent
  sur `origin/develop`, donc hérité par la branche de la task.

## Timings

*(généré par `tools/timing/report.sh --task task-285 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 1 min 24 s | — | — | — | — |
| /develop | ok | 41 min 33 s | 8 (2 min 09 s) | 15 (5 min 13 s) | — | api-mail 4B/6T, client-mobile 1B/2T, client-blazor 1B/4T, client-angular 2B/3T |
| /sonar | ok | 12 min 24 s | 1 (12 s) | 2 (4.7 s) | — | 1 itération(s), api-mail 1B/2T |
| /lint-angular | ok | 3 min 12 s | 1 (17 s) | 1 (21 s) | — | 1 itération(s), client-angular 1B/1T |
| **Total cycle** | | **58 min 34 s** | **10 (2 min 39 s)** | **18 (5 min 39 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : lint ×2 (35 s)

## Develop log

- **Repos touchés** : `api-mail`, `client-blazor`, `client-mobile`, `client-angular` (code-only).
- **DTO publié** : aucun. La US n'ajoute aucun champ de contrat — l'endpoint
  `POST /api/v1/sync/logout` existait et n'a ni corps ni réponse typée. La
  branche `dtos-mss` auto-incluse reste **vide**, aucune PR : pas de cascade
  NuGet pour une US qui n'en avait pas besoin.
- **Interop publié** : aucun (repo non touché).

### Ce que l'instruction du code a révélé

Le task file décrivait deux causes. L'instruction en a précisé la mécanique, et
a fait apparaître un troisième défaut :

1. **Le bus inter-instances existait déjà** — canal Redis `mss:sync:cmd`,
   `SyncControlCommand`, abonné sur chaque instance. Rien à construire. Mais
   `HandleRemoteCommandAsync` **sortait immédiatement** si l'instance ne
   détenait pas le runtime de synchronisation. Une instance porteuse d'une
   session IMAP sans runtime de sync ignorait donc tout ordre. La nouvelle
   commande `CloseMailSession` est traitée **avant** ce garde-fou.
2. **`client-blazor` n'appelait rien.** `SyncProgressService.LogoutCleanupAsync()`
   existait, appelait le bon endpoint — et **aucun écran ne l'appelait**. Le
   task file disait « pas systématiquement au bon moment » ; c'était zéro
   appelant.
3. **Défaut non prévu, trouvé par un test** (bUnit, cas dégradé) : dans
   `Logout.razor`, une exception échappée de l'ordre de clôture faisait sauter
   la purge locale plus bas — le praticien restait authentifié sur son poste.
   Corrigé par un `catch` dédié.

### Commits

| Repo | Commit | Objet |
|---|---|---|
| `api-mail` | `1ce74a0` | commande `CloseMailSession`, diffusion, traitement hors garde-fou |
| `api-mail` | `b3d380c` | passe qualité `/simplify` |
| `client-mobile` | `e487353` | `LogoutService` — séquence unique pour les 3 écrans |
| `client-blazor` | `a6b7582` | ordre émis en premier, appel borné, page durcie |
| `client-angular` | — | **code-only, non commité** (voir plus bas) |

### Build / tests

| Repo | Build | Tests |
|---|---|---|
| `api-mail` | ✓ | **3963 passés**, 16 skipped, 0 échec |
| `client-blazor` | ✓ | 157 passés, 2 skipped |
| `client-mobile` | ✓ | 801 passés |
| `client-angular` | ✓ (`nx build weda2`) | weda2 **2570 passés** · mss-lib **329 passés** |

**Test-first (règle 1) — démonstration RED faite.** Correctif d'`api-mail` retiré
puis tests relancés : **4 échecs sur 7**, exactement les tests inter-instances
(`ClosesTheMailSessionHeldByAnotherInstance`, `ReachesAnInstanceThatOwnsNoSyncRuntime`,
`ReplayedOnAnAlreadyClosedSession`, `PublishesTheCloseOrderCarryingTheClientSessionId`).
Les 3 autres passaient déjà : ce sont les fermetures locales, qui tiennent lieu de
non-régression. Correctif remis → 13/13.

**Deux flakies pré-existants rencontrés, aucun lié à cette US** :
`MailRepositoryEnrichPersistInstrumentationTests.The_remainder_carries_the_whole_total_when_no_phase_was_observed`
(6/6 en isolation, 3 exécutions) et un échec non reproductible dans
`mss.mail.application.tests`. La classe de tests ajoutée par cette US a été
lancée **5 fois de suite : 13/13 à chaque fois**. Deux exécutions complètes de la
solution finissent à 0 échec.

### Passe qualité (`/simplify`)

- **Appliquée & commitée** : `api-mail` (`b3d380c`) — le retrait de session et sa
  ligne de journal PGSSI-S étaient dupliqués entre le chemin HTTP et le chemin
  diffusé ; extraits dans `CloseMailSessionLocally`. Un seul message, donc un
  total cluster qui s'agrège en filtrant une seule ligne. Au passage,
  `BroadcastCloseMailSessionAsync` ne reçoit plus le résultat de la fermeture
  locale, dont il ne se servait que pour journaliser.
- **Sans changement** : `client-mobile` et `client-angular` — l'axe réutilisation
  a été appliqué pendant l'écriture, pas après : trois copies du bloc de
  déconnexion mobile fondues en un `LogoutService`, et côté Angular le jeton
  `MAIL_SESSION_CLOSER` reprend le schéma déjà en place pour `MSS_PSC_REFRESH_FN`
  au lieu d'introduire une dépendance shell → module.
- **Sans changement** : `client-blazor` — le diff réutilise `LogoutCleanupAsync`,
  qui existait déjà.
- **Sautée (porteur de contrat)** : `dtos-mss`.

### `client-angular` — code-only, en attente de l'humain

Branche checkée : **`feature/nova-rewriting-mss`**. Rien n'est commité ni poussé.

Fichiers écrits par la forge :

- `apps/weda2/src/lib/auth/models/mail-session-closer.model.ts` *(nouveau)*
- `apps/weda2/src/lib/auth/index.ts`
- `apps/weda2/src/lib/auth/store/authentication-store.ts`
- `apps/weda2/src/lib/auth/store/models/authentication-store-props.model.ts`
- `apps/weda2/src/lib/auth/store/utils/store-helpers.utils.ts`
- `apps/weda2/src/lib/auth/store/utils/store-helpers.utils.spec.ts`
- `apps/weda2/src/app/app.config.ts`
- `libs/mss/src/core/services/mss-api.service.ts`

⚠️ **Deux fichiers modifiés qui ne sont PAS de la forge** — WIP humain
antérieur, laissé intact : `apps/mss/src/environments/environment.ts` et
`apps/weda2/src/environments/environment.ts`. Ne pas les inclure dans la PR TFS
sans vérification.

### Notes

- `conventions/angular.md` **n'existe pas** dans le workspace (seul
  `conventions/csharp.md` est présent), alors que CLAUDE.md le décrit comme lu
  par `/develop` avant tout code Angular/Ionic. Rien à appliquer, donc, mais
  l'écart mérite d'être connu : la boucle d'auto-amélioration côté front n'a pas
  encore de support.
- `interop-cda` (`interop/`) n'a **pas de `.git`**, comme `host/Modules`.
  L'avertissement de CLAUDE.md ne nomme que `host` — il vaut pour les deux.

- **Étape suivante** : `/sonar task-285`

## Sonar log

**Analyse** : `healthplatform-api-mail`, branche `feat/task-285-logout-closes-mail-session-all-pods`,
2026-09-01 23:52. Scan complet (build Release + 5 projets de tests avec couverture
OpenCover, 7 rapports).

> **Le serveur SonarQube était arrêté** (conteneur `sonarqube` en `Exited (255)`
> depuis 28 h). Redémarré avec `sonarqube_db` — sans quoi l'étape aurait skippé
> sur une indisponibilité d'outillage, pas sur une absence de dette.

### KPI

| Métrique | Baseline (avant) | Final | Cible |
|---|---|---|---|
| `bugs` | 0 | **0** | 0 ✓ |
| `vulnerabilities` | 0 | **0** | 0 ✓ |
| `code_smells` | 63 | **62** | — |
| `coverage` | 88,2 % | **88,2 %** | ≥ 95 % |
| `security_hotspots` | 3 | **3** | — |
| `sqale_rating` | A | **A** | A ✓ |
| `new_bugs` | 0 | **0** | 0 ✓ |
| `new_vulnerabilities` | 0 | **0** | 0 ✓ |
| `new_security_hotspots` | — | **0** | 0 ✓ |
| `new_code_smells` | 36 | **35** | 0 |
| `new_coverage` | 90,5 % | **90,4 %** | ≥ 95 % |

**Quality Gate : `OK`** — les 5 conditions passent (`new_reliability_rating`,
`new_security_rating`, `new_maintainability_rating`, `new_coverage` 90,4 % ≥ 80 %,
`new_duplicated_lines_density` 0,02 % ≤ 3 %).

### Phase 1 — zero-new-debt : verte, et mesurée fichier par fichier

Les 35 findings de la période « new code » **n'appartiennent pas à cette US**.
Vérifié par une requête par fichier, pas par déduction :

| Fichier de task-285 | Findings new-code |
|---|---|
| `src/Application/Services/Implementation/BackgroundSyncManager.cs` | **0** |
| `src/Application/Services/Interfaces/ISyncStateStore.cs` | **0** |
| `src/Application/Session/IMailClientSessionManager.cs` | **0** |
| `src/Application/Session/MailClientSessionManager.cs` | **0** |
| `tests/…/Sync/ClusterBusFake.cs` | **0** |
| `tests/…/Sync/LogoutClosesMailSessionAcrossPodsTests.cs` | **0** |

**Cette PR introduit zéro nouvelle dette.** Le compteur `new_code_smells` était
déjà à 36 avant l'analyse : les 35 restants viennent de la période « new code »
du projet (travaux récemment mergés), concentrés sur
`MailClientSession.cs` (9 — à ne pas confondre avec `MailClientSessionManager.cs`),
et répartis sur `S3604` (15), `CA1861` (9), `S107` (3).

**Un trou de couverture réel a été trouvé et bouché** (`dc1ee69`) : le new code de
`BackgroundSyncManager.cs` était à 85,4 %, et la branche non couverte de mes ajouts
était le garde-fou de périmètre — un ordre de clôture sans identifiant de session
cliente. Branche non décorative : l'appliquer construirait une clé « email_ » vide
et pourrait déconnecter un praticien actif sur un autre appareil (règle 2).

### Phase 2 — dette héritée : sautée délibérément

Phase 2 est **optionnelle** (`agents/sonar.md`). Sautée ici pour trois raisons :

1. Les 35 findings sont dans des fichiers **qu'aucun commit de cette US ne touche**.
2. Les corriger gonflerait une PR déjà répartie sur 4 repos et brouillerait la
   revue humaine du HAG (règle 10), qui porte sur une US de sécurité.
3. `CA1861` (9 occurrences) est déjà consigné dans `conventions/csharp.md`
   (`Occurrences : 2`) — la récidive est donc **connue et tracée**, et relève
   d'un run `/sonar` autonome (Mode B), pas du passager de cette US.

### Instabilité de tests observée (pré-existante, non liée)

Trois exécutions de la suite `api-mail` ont montré des échecs intermittents non
reproductibles : 2 échecs, puis 1, puis 0, puis 2 sous Release + couverture, puis 0.
Le seul nommé est
`MailRepositoryEnrichPersistInstrumentationTests.The_remainder_carries_the_whole_total_when_no_phase_was_observed`
(6/6 en isolation sur 3 exécutions). **La classe ajoutée par cette US a été lancée
5 fois de suite : 13/13 à chaque fois**, puis 14/14 après l'ajout du test de
couverture. Deux exécutions complètes de la solution finissent à 0 échec. Mérite
sa propre task.

- **Étape suivante** : `/lint-angular task-285`

## Lint log — `client-angular` (code-only)

**Scope retenu : `weda2` + `mss-lib`, pas le défaut.**

Le task file ne déclare pas `**LintProjects**`, or le code Angular de cette US
vit dans **`apps/weda2/src/lib/auth`** (`scope:weda2`) autant que dans
`libs/mss`. Le scope par défaut de `/lint-angular` (`tag:scope:mss`) n'aurait
donc pas regardé une seule ligne de la partie shell — exactement le piège que
task-284 avait consigné. Lint lancé explicitement sur les deux projets.

Base de comparaison : projets ciblés directement plutôt que
`affected --base=origin/next`, car la branche checkée
(`feature/nova-rewriting-mss`) porte du travail humain en cours qui n'appartient
pas à cette US.

### Résultat — 1 itération

| Projet | Avant | Après |
|---|---|---|
| `weda2` | 39 problèmes (**2 erreurs**, 37 warnings) | 36 problèmes (**0 erreur**, 36 warnings) |
| `mss-lib` | 17 problèmes (**2 erreurs**, 15 warnings) | 14 problèmes (**0 erreur**, 14 warnings) |

**Les 4 erreurs étaient toutes dans des fichiers de cette US** — corrigées, aucune
acceptée. Les warnings restants sont pré-existants (`max-lines`, `complexity`,
`jsdoc/require-example` sur du code ancien) ; un warning a disparu au passage.

### Un vrai défaut d'insertion, révélé par le lint

Deux des quatre erreurs venaient de la **même bévue** : dans
`libs/mss/src/core/services/mss-api.service.ts`, mon ancre d'insertion était la
signature de `getFolders()`, ce qui a placé `closeMailSession` **entre le JSDoc
existant de `getFolders` et `getFolders` lui-même**. Résultat : un bloc JSDoc
orphelin attribué à ma méthode, et `getFolders` sans documentation
(`jsdoc/require-jsdoc`). Le JSDoc a été rendu à son propriétaire.

Le même motif d'insertion avait été utilisé côté `client-mobile` — **vérifié, il
est sain** : l'ancre y était placée après le corps de `getFolders`, pas avant sa
signature.

Deux autres erreurs : `@param`/`@returns` manquants sur le helper
`closeMailSession` de `store-helpers.utils.ts`. Ajoutés.

### Re-validation

- `npx nx build weda2` → **succès**
- `npx nx run-many -t test --projects=weda2,mss-lib` → **weda2 2570 passés**
  (14 skipped), **mss-lib 329 passés**, 0 échec

### Code-only

Aucune opération git sur `client-angular`. Les fichiers restent modifiés dans
l'arbre de travail de `feature/nova-rewriting-mss` — l'humain garde branche,
commit, push et PR TFS.

- **Étape suivante** : `/lint-mobile task-285`

## Lint mobile log

`npm run lint` (`ng lint`) sur `feat/task-285-logout-closes-mail-session-all-pods` :

```
Linting "app"...
All files pass linting.
```

**0 erreur, 0 warning — 0 itération consommée.** Rien à corriger, donc aucun
commit : le code écrit par `/develop` (`LogoutService`, son spec, la méthode
`closeMailSession`, et les trois écrans recâblés) passe le lint tel quel.

Contraste utile avec `client-angular`, qui portait 4 erreurs sur les fichiers de
cette US : la configuration ESLint de `client-mobile` n'impose pas les règles
`jsdoc/*` qui les avaient déclenchées là-bas.

- **Étape suivante** : `/verify-visual task-285`
