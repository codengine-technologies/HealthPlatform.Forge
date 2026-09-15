# todo-task-313.md — Détacher sa dernière messagerie déconnecte, sur les trois fronts

**Repos**: client-blazor, client-mobile, api-mail
**Dependencies**: done-task-312
**Epic**: E016

## Objectif

Le praticien qui détache sa **dernière** messagerie doit être **déconnecté de
l'application**, sur Blazor et sur mobile comme sur Angular. Aujourd'hui les deux
fronts le laissent connecté avec une session qui porte une boîte qui n'existe
plus : chaque appel suivant est refusé, et **la route qui sert à rattacher une
nouvelle messagerie est refusée elle aussi**. Le compte n'a plus aucun chemin de
retour.

Décision humaine du 2026-09-15, prise après un test de bout en bout sur Angular,
puis étendue aux deux autres fronts le même jour. Le correctif Angular est déjà
écrit (task-312) : cette US le porte à l'identique, **sans le ré-inventer**.

### Pourquoi une déconnexion, et pas un assouplissement du backend

C'est aussi ce qui débloque techniquement le compte, sans toucher à une seule
garde de sécurité. Tant que la session reste ouverte, le front continue
d'annoncer la boîte détachée. Le backend la retrouve en base — elle existe
toujours, à l'état détaché —, la juge non sélectionnable, et refuse. Après
déconnexion, plus d'annonce de boîte : le backend prend l'autre branche de la
sélection, ne trouve aucune boîte sélectionnable, et rend l'issue « une
messagerie est requise » — la seule que les routes de rattachement laissent
déjà passer. L'onboarding redevient joignable à la reconnexion.

### Ce qui est déjà en place et qu'il ne faut PAS refaire

- **Blazor** : `ISessionExpirationHandler.HandleExpiredSession()` purge
  l'authentification locale et bascule sur l'écran de connexion. Il est
  **idempotent** par contrat. C'est la couture à employer.
- **Mobile** : `LogoutService.run()` ferme la session de boîte, révoque, purge,
  et bascule sur `/login`.
- **Angular** : `MSS_LOGOUT` (task-312), pour référence de comportement.

---

## Les quatre défauts à corriger, établis par lecture du code le 2026-09-15

### Défaut 1 — aucune déconnexion quand il ne reste plus rien (les deux fronts)

Les deux écrans de gestion naviguent vers l'onboarding et **laissent la session
ouverte** :

- `Client/Blazor/Src/Modules/Mss/Plugin/Pages/MailboxManagement.razor`
  → `ConfirmRemoveAsync()`
- `Client/Mobile/src/app/mailbox/management/mailbox-management.page.ts`
  → `confirmRemove()`

**Attendu** : plus aucune boîte utilisable **et** c'est la boîte courante qui
vient d'être détachée → vider la session de boîte, puis **déconnexion complète**.
Les autres branches (un repli existe, la boîte détachée n'était pas la courante)
ne changent pas.

### Défaut 2 — la décision est prise sur une liste PÉRIMÉE (les deux fronts)

Les deux écrans rechargent **avant** de décider, et les deux rechargements
échouent en silence en laissant la liste d'avant :

- Blazor : `MailboxSessionService.RefreshAsync()` sort en `Result.Error` **sans
  toucher** `_mailboxes` quand la liste est refusée.
- Mobile : `MailboxSessionService.refresh()` rend `false` **sans toucher**
  `mailboxesSignal` dans le même cas.

Or la liste est précisément refusée ici, puisque la session porte encore la
boîte détachée. La boîte retirée y figure donc toujours comme sélectionnable et
par défaut : les deux écrans trouvent **un repli qui n'existe plus** et
rebasculent vers la messagerie qu'on vient de supprimer.

**Attendu** : décider sur la liste de **l'écran** — celle que le praticien avait
sous les yeux, amputée de la boîte retirée — et **avant** de recharger. C'est
exactement la correction portée sur Angular.

### Défaut 3 — Blazor « récupère » vers la boîte détachée

Propre à Blazor, et plus grave que les deux précédents : `Mss403Handler`
intercepte le refus et tente une récupération automatique
(`RecoverMailboxAsync()`) qui enchaîne `RefreshAsync()` — refusé, donc liste
périmée — puis bascule vers le repli fantôme. Le front réinstalle lui-même la
boîte détachée comme boîte courante.

**Attendu** : quand la récupération ne trouve **aucune** boîte réellement
utilisable, elle ne bascule pas — elle déclenche la même déconnexion. Une
récupération qui ne peut pas aboutir doit rendre la main, pas boucler.

> ⚠️ **Point à contester, à trancher au test humain.** La récupération
> silencieuse de `Mss403Handler` est un confort réel quand une boîte perd son
> jeton en cours de session. On ne la supprime pas : on lui interdit seulement
> de conclure sur une liste qu'elle n'a pas pu rafraîchir.

### Défaut 4 — l'ordre de clôture est refusé quand il n'y a plus de boîte (api-mail)

`POST /api/v1/sync/logout` **ne porte pas** `[MailboxNotRequired]`
(`Api/Mail/src/Api/Controllers/V1/SyncController.cs`). Sans boîte annoncée, la
sélection rend « une messagerie est requise » et l'ordre de clôture est refusé —
alors que sa portée est **(praticien, session cliente)** et qu'il ne touche
aucune boîte. Les trois fronts émettent cet ordre au début de leur déconnexion :
Angular s'en protège déjà par une garde côté client, Blazor et mobile le
traversent.

**Attendu** : la route accepte une déconnexion sans boîte ouverte. C'est un
alignement de l'attribut sur ce que la route fait réellement, pas un
assouplissement de garde : l'authentification du praticien reste exigée.

> **La garde côté Angular reste en place après ce correctif** : ne rien demander
> quand il n'y a rien à fermer est juste indépendamment du backend.

---

## Hors périmètre (explicite)

- **Le code d'erreur trompeur.** Une messagerie **détachée** est aujourd'hui
  rapportée comme un conflit d'identité PSC alors qu'elle n'en a aucun. Ce
  libellé a égaré le diagnostic pendant plusieurs échanges le 2026-09-15. Il
  mérite sa propre US : le corriger ici mêlerait un changement de contrat à un
  correctif de comportement.
- **La parité de la clôture de session sur Blazor** — l'ordre de clôture y est
  câblé au changement de messagerie, pas à la déconnexion du praticien.
- **Angular** : déjà corrigé (task-312), non listé dans `**Repos**:`.

---

## Definition of Done

- [ ] Build passes sur les trois repos (0 erreur)
- [ ] Tests verts sur les trois repos (0 échec)
- [ ] **Blazor** — `MailboxManagement` : détacher la dernière messagerie
      courante déclenche `ISessionExpirationHandler.HandleExpiredSession()`,
      ne navigue pas vers l'onboarding, et **ne recharge pas** avant de décider
- [ ] **Blazor** — test bUnit du **store périmé** : liste de session inchangée
      après un rafraîchissement refusé ⇒ **aucune** bascule vers le repli
      fantôme, déconnexion déclenchée. Ce test doit être vérifié **ROUGE contre
      la logique actuelle** avant correction (rule 1)
- [ ] **Blazor** — test `Mss403Handler` : récupération sur un rafraîchissement
      refusé ⇒ pas de bascule, déconnexion déclenchée
- [ ] **Mobile** — `mailbox-management.page` : mêmes trois comportements
      (déconnexion via `LogoutService.run()`, décision sur la liste de l'écran,
      aucun rechargement sur le chemin de déconnexion)
- [ ] **Mobile** — test du **store périmé**, également vérifié ROUGE avant
      correction (rule 1)
- [ ] Les branches inchangées sont couvertes par un test chacune, sur les deux
      fronts : un repli par défaut existe ⇒ bascule ; la boîte détachée n'est
      pas la courante ⇒ la session n'est pas touchée
- [ ] **api-mail** — `POST /api/v1/sync/logout` porte `[MailboxNotRequired]`
- [ ] **api-mail** — test d'intégration : déconnexion **sans boîte annoncée**
      acceptée (rule 1b), et déconnexion avec boîte ouverte toujours acceptée
- [ ] Aucune garde de sélection de messagerie assouplie — le diff d'api-mail se
      limite à l'attribut de route et à son test
- [ ] Aucune donnée de santé en clair dans les logs (adresse MSSanté, contenu)
- [ ] Évènement PGSSI-S de clôture de session de boîte toujours journalisé

## Manual Test Plan

**Pré-requis** : un compte praticien avec **une seule** messagerie rattachée,
authentifié via Pro Santé Connect.

**Backend** : `cd Api/Mail && dotnet run --project src/AppHost`

### Blazor
1. `cd Client/Blazor && dotnet run`
2. Se connecter, ouvrir la messagerie, aller sur « Gérer mes messageries »
3. Détacher la seule messagerie, confirmer
4. **Attendu** : retour à l'écran de connexion. **Pas** d'écran d'onboarding,
   **pas** de retour sur la messagerie détachée, **aucune** notification
   d'erreur pendant la bascule
5. Se reconnecter : le parcours de rattachement d'une nouvelle messagerie est
   accessible et fonctionne

### Mobile
6. `cd Client/Mobile && npm start`
7. Mêmes étapes 2 à 5, écran « Mes messageries »
8. **Attendu** : bascule sur `/login`, mêmes interdits qu'en 4

### Non-régression (les deux fronts)
9. Avec **deux** messageries rattachées, détacher la **courante** : l'application
   bascule sur l'autre messagerie et **ne déconnecte pas**
10. Avec deux messageries, détacher **celle qui n'est pas ouverte** : rien ne
    change à l'écran ouvert, aucune déconnexion
11. Déconnexion ordinaire depuis la barre/le menu, avec une messagerie ouverte :
    inchangée, et l'ordre de clôture de session part toujours

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR honorées** : MSSanté — accessibilité du parcours de
  rattachement d'une adresse MSSanté par le PS ; PGSSI-S § journalisation
  (frontière de session)
- **INS** : non applicable — la US ne manipule aucune identité patient, aucun
  document, aucun contenu de message
- **Authentification PS** : Pro Santé Connect / e-CPS, niveau eIDAS
  substantiel — **inchangé**. La US ne modifie aucune exigence
  d'authentification : elle met fin à une session dont la boîte a disparu.
- **Habilitations** : RPPS porté par le jeton PSC — contrôle inchangé
- **Interop CI-SIS** : non applicable — aucun échange métier, aucun document
  CDA ni ressource FHIR sur ce chemin
- **Tracé PGSSI-S** : clôture de session de boîte (déjà journalisée côté
  api-mail comme une **frontière d'imputabilité**, task-303) ; détachement de
  messagerie ; déconnexion du praticien. Conservation 6 ans, inchangée. La US
  ne retire aucun évènement : elle rend joignable la route qui en émet un.
- **Consentement patient** : non applicable — aucune donnée patient
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement existant, inchangé par la US
- **AIPD / impact RGPD** : inchangé — aucun traitement nouveau, aucune donnée
  nouvelle collectée. La US **raccourcit** la durée de vie d'une session
  devenue sans objet, ce qui va dans le sens de la minimisation.

## Branches

Branche unique sur les quatre repos : `feat/task-313-logout-derniere-messagerie`
(créée depuis `origin/develop` le 2026-09-15).

- `api-mail` (pushed) — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-313-logout-derniere-messagerie
- `client-blazor` (pushed) — https://github.com/codengine-technologies/HealthPlatform.Client/tree/feat/task-313-logout-derniere-messagerie
- `client-mobile` (pushed) — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-313-logout-derniere-messagerie
- `dtos-mss` (pushed, auto-inclus) — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-313-logout-derniere-messagerie
  — branche de précaution : la US ne prévoit **aucun** changement de contrat.
  Sans commit, aucune PR ne sera ouverte.

Pré-flight du 2026-09-15 : `api-mail`, `client-blazor`, `client-mobile`,
`dtos-mss`, `sdk` sur `develop` et propres. `interop` n'a pas de `.git` — il
répond pour le dépôt de la forge (même piège que `Host/Modules`, cf. CLAUDE.md) ;
il n'est pas ciblé par cette US.

`client-angular` n'est **pas** listé : le correctif y est déjà en place
(task-312), et la couture `MSS_LOGOUT` sert de référence de comportement.

## Timings

*(généré par `tools/timing/report.sh --task task-313 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 1 min 07 s | — | — | — | — |
| /develop | ok | 12 min 23 s | 3 (21 s) | 10 (3 min 01 s) | — | api-mail 1B/2T, client-blazor 1B/4T, client-mobile 1B/4T |
| /sonar | ok | 7 min 19 s | 1 (14 s) | 5 (4 min 46 s) | 1 (31 s) | api-mail 1B/5T |
| /lint-angular | skipped | 23 s | — | — | — | client-angular hors perimetre (Repos ne le liste pas) — deja livre par task-312 |
| /lint-mobile | ok | 28 s | — | — | — | 0 erreur des la baseline — aucun correctif |
| /verify-visual | skipped | 26 s | — | — | — | aucun Stitch design log (aucun template touche) + Tools/visual-verify absent du poste |
| /review | ok | 7 min 11 s | 3 (17 s) | 3 (1 min 48 s) | — | api-mail 1B/1T, client-blazor 1B/1T, client-mobile 1B/1T |
| /tech-writer | ok | 1 min 43 s | — | — | — | — |
| **Total cycle** | | **31 min 03 s** | **7 (54 s)** | **18 (9 min 36 s)** | **1 (31 s)** | |

Autres commandes mesurées : lint ×1 (15 s)

## Sonar log

Scan du 2026-09-15 sur `feat/task-313-logout-derniere-messagerie`
(SonarQube 9.9.8, projet `healthplatform-api-mail`).

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| **Quality Gate (new code)** | OK | **OK** | = |
| New coverage | 84,8 % | **85,8 %** | +1,0 pt |
| New bugs / vulnérabilités | 0 / 0 | **0 / 0** | = |
| New code smells | 35 | 35 | = |
| Coverage projet | 87,7 % | **87,8 %** | +0,1 pt |
| Duplication | 0,4 % | 0,4 % | = |
| Bugs / Vulnérabilités / Smells | 0 / 0 / 228 | 0 / 0 / 228 | = |
| Ratings (fiabilité / sécurité / maintenabilité) | 1.0 / 1.0 / 1.0 | 1.0 / 1.0 / 1.0 | = |

### Itérations de nettoyage : 0

**Aucune n'était justifiée, et c'est une mesure, pas une dispense.** Requête
ciblée sur les deux seuls fichiers du diff api-mail — `SyncController.cs` et
`SyncControllerTests.cs` — : **0 issue ouverte**. Le diff se réduit à un
attribut de route, son commentaire et un test par réflexion.

Les 35 *new code smells* et les 228 du projet sont **antérieurs** à cette
branche : aucun ne porte sur les fichiers touchés. Les revendiquer ou les
nettoyer ici mêlerait de la dette d'arrière-plan à un correctif de
comportement.

5 passes instrumentées OpenCover, 4 476 tests verts, 0 échec.

## Lint log

**Skip propre — `client-angular` hors périmètre de cette US.** Le champ
`**Repos**:` ne le liste pas : le correctif y est déjà livré par task-312, et
l'humain l'a committé sur TFS (`88d05429 Fix logout`, branche
`feature/nova-rewriting-mss`), garde `closeMailSession` comprise.

Aucun fichier Angular n'a été écrit par task-313. Les deux seules modifications
du working tree (`apps/mss/.../environment.ts`, `apps/weda2/.../environment.ts`)
appartiennent à l'humain et ne sont pas touchées — code-only, la forge ne
committe jamais sur ce repo.

Itérations : 0.

## Lint mobile log

`npm run lint` (`ng lint`) sur `feat/task-313-logout-derniere-messagerie` :
**« All files pass linting »** — 0 erreur, 0 warning, dès la baseline.

Itérations : 0. Aucun correctif appliqué, donc aucun commit et rien à pousser
— et le filet anti-régression (build + tests) n'avait pas à être rejoué : le
repo est vert depuis `/develop` (837 tests, build OK) et n'a pas bougé depuis.

Le fichier écrit par cette task (`mailbox-management.page.spec.ts`) et celui
modifié (`mailbox-management.page.ts`) passent tous deux sans remarque.

## Visual verify log

**Skip best-effort.** Deux motifs, dont un qui n'est pas de mon fait :

1. **Aucun `## Stitch design log`** dans cette task — condition de skip
   documentée de l'étape. `/develop` n'a pas appelé `/stitch-design` parce
   qu'aucun écran n'a été dessiné : le diff mobile ne touche **aucun
   template**. `git diff --stat origin/develop...HEAD` le confirme — deux
   fichiers, `mailbox-management.page.ts` (logique) et son nouveau
   `.spec.ts`. `mailbox-management.page.html` est intact.

2. **L'outillage n'est pas installé sur ce poste** : `Tools/visual-verify/`
   n'existe pas. Panne d'outillage = best-effort par la règle de l'étape,
   jamais un point d'arrêt.

### Réserve assumée, à couvrir au test humain

Le motif 1 dit qu'il n'y a **rien de nouveau à comparer au design**. Il ne dit
pas qu'il n'y a **aucun risque de rendu** : cette task ajoute une injection à
la page (`inject(LogoutService)`). Une injection fautive produit un écran
blanc — exactement la seule sévérité bloquante de cette étape, et exactement
ce qu'un test unitaire ne voit pas, puisqu'il fournit lui-même le service.

Le risque est faible (`LogoutService` est `providedIn: 'root'`, donc résolu
sans déclaration) mais il n'est **pas mesuré ici**. Il est couvert par les
étapes 6-8 du `## Manual Test Plan`, qui ouvrent réellement l'écran
« Mes messageries » sur mobile.

Écrans capturés : 0.

## PRs

| Repo | PR | Label |
|---|---|---|
| `api-mail` | https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/241 | `awaiting-human-merge` |
| `client-blazor` | https://github.com/codengine-technologies/HealthPlatform.Client/pull/77 | `awaiting-human-merge` |
| `client-mobile` | https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/73 | `awaiting-human-merge` |
| `dtos-mss` | **aucune PR** — branche créée par précaution, 0 commit : la US ne change aucun contrat | — |

`client-angular` : hors périmètre (déjà livré par task-312, committé par
l'humain sur TFS — `88d05429 Fix logout`).

## Code Review Summary

**Verdict : APPROVED** — 6 fichiers relus, 0 blocage, 1 point de conformité
remonté (non bloquant).

| Fichier | Verdict |
|---|---|
| `api-mail` · `SyncController.cs` | ✅ exemption étroite, justifiée par le corps de la méthode |
| `api-mail` · `SyncControllerTests.cs` | ✅ garde de convention par réflexion — attrape un retrait futur de l'attribut |
| `blazor` · `MailboxManagement.razor` | ✅ l'ordre des opérations EST le correctif ; aucun chemin perdu |
| `blazor` · `Mss403Handler.cs` | ✅ la récupération est bornée, pas supprimée |
| `blazor` · tests (2 fichiers) | ✅ 3 nouveaux tests ROUGE→VERT + 2 non-régressions |
| `mobile` · `mailbox-management.page.ts` + spec | ✅ parité stricte ; 1er spec de cette page |

### Deux risques levés par vérification, pas par impression

1. **Purge croisée entre praticiens ?** Non. `CleanupUserAsync` n'utilise
   `userEmail` que comme **clé de recherche** (`TryGetValue`,
   `HasActiveSessionsForEmail`, `GetStateAsync`). Une chaîne vide ne correspond
   à rien : l'appel devient un no-op, jamais un effacement de masse.

2. **Résolution d'un service `AddScoped` depuis le provider racine (Blazor) ?**
   Sans risque nouveau : `ISessionExpirationHandler` a le **même cycle de vie**
   et le **même mode de résolution** que `IMailboxSessionService`, que
   `Mss403Handler` résout déjà ainsi.

### ⚠️ Point de conformité remonté — `questions/task-313.md`

Cette route devient la **première** route `[MailboxNotRequired]` qui émet une
trace d'audit. Sur ce chemin `userContext.Email` est vide **par conception**, et
`AuditService` en dérive `UserId` : la trace `MailboxSessionClosed` est donc
**non attribuable**.

**Ce n'est pas une régression** — avant le correctif la requête était refusée en
403 et aucune trace n'était écrite. Mais trancher entre « ne pas émettre » et
« émettre sous une identité de repli (sub PSC / RPPS) » est une décision de
conformité, et la seconde option toucherait `AuditService`, donc **toutes** les
traces de la plateforme. Hors périmètre de cette US (règles 6 et 7c), et hors du
mandat de `/review` qui ne corrige pas de code.
