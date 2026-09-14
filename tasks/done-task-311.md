# todo-task-311.md — Le banc de charge ne démarre plus : son seeder doit provisionner le registre

**Repos**: api-mail
**Dependencies**: **task-308** (mergée le 2026-09-14 — c'est elle qui supprime le
rattachement automatique). Aucune dépendance sortante, mais **bloque toute campagne de
charge** : aucun tir n'est exploitable tant que cette US n'est pas passée.
**Epic**: E016
**Priorité**: **0 — bloquant.** Le banc ne mesure plus rien. Toutes les routes de
messagerie répondent en 4xx dès la première requête de chaque praticien synthétique.

## Objective

Faire écrire au seeder du banc les lignes de registre que l'onboarding écrirait, pour
chaque praticien synthétique — afin que le banc redevienne exploitable **et** que ses tirs
exercent le journal d'audit mutualisé, comme avant task-308.

## Ce qui est cassé, et pourquoi

task-308 a supprimé `TenantRegistrySynchronizer.EnsureCurrentTenantAsync`, qui fabriquait
un rattachement à chaque requête authentifiée depuis le claim `mssEmail`. **C'est ce
mécanisme qui provisionnait le banc à son insu** : le harnais n'a jamais su que le registre
existait, ses boîtes se rattachaient toutes seules à la première requête.

### La séquence aujourd'hui, avec un registre vide

Le harnais envoie `Client-Email`, `Client-Psc-Sub`, `Client-Rpps`
(`tests/loadtest-k6/lib/identity.js:107-111`) :

1. `EnsureAccountAsync` crée la ligne `accounts` — **le compte existe**.
2. `ApplyMailboxSelectionAsync` prend `Client-Email` comme boîte demandée →
   `GetMailboxAsync` → **aucun rattachement** → `NotAttached`
   (`MailboxSelectionService.cs:60`).
3. La requête est **refusée avant le contrôleur**.

**Toutes les routes de messagerie répondent en 4xx.** Il n'y a rien à mesurer.

### Et si l'on franchissait cet obstacle : l'audit ne serait plus exercé

`userContext.TenantId` ne vient plus que de la boîte résolue
(`UserContextEnricherMiddleware.cs:796`). Sans rattachement, il reste **nul**, et
`AuditService` retombe sur la base praticien — le mode dégradé prévu par task-300.

Le **journal mutualisé ne serait donc pas exercé du tout** : le banc cesserait de mesurer
précisément ce que task-300 a été construit pour corriger (52 088 des 53 456 exceptions
« too many clients », soit 97 %), et **la référence de capacité E015 deviendrait
incomparable** avec tous les tirs antérieurs. C'est le deuxième défaut, et il est plus
insidieux que le premier : un tir « vert » mesurerait alors autre chose que ce qu'on croit.

## La voie qui ne marche pas — et il faut le savoir avant d'essayer

**Faire appeler `POST /api/v1/account/mailboxes` par le seeder est impossible.**

Le domaine `loadtest.local` **n'existe pas** dans `MailServers.Domains`
(`appsettings.json` ne porte que `gmail.com` et les deux domaines MSSanté). La sonde
d'onboarding appelle `GetImapServerConfig(email)` **sans** configuration utilisateur :
elle rendrait `null`, donc `MailboxNotFound`, et rien ne serait rattaché.

> **Pourquoi l'IMAP du banc fonctionne malgré cette absence.**
> `ImapConnectionService` passe `userSettings?.ImapServerConfig` en **second argument** de
> `GetImapServerConfig` : le seeder écrit une configuration IMAP **par praticien** dans sa
> base, et `FromUserConfig` court-circuite la table des domaines. La sonde d'onboarding, au
> contraire, ne consulte pas ces réglages — elle n'a pas de contexte praticien.
>
> Ajouter `loadtest.local` à la table des domaines pour contourner cela serait un mauvais
> échange : on ferait entrer une configuration de banc dans la configuration produit, et on
> paierait mille sondes IMAP au provisionnement.

## Le correctif — le seeder écrit ce que l'onboarding écrirait

Pour chaque praticien synthétique, deux lignes dans `mss_registry` :

| Table | Colonne | Valeur |
|---|---|---|
| `accounts` | `authentication_subject` | le **`PscSub`** du praticien — c'est ce que `TestBypassAuthenticationHandler` pose en `ClaimTypes.NameIdentifier` quand l'en-tête `Client-Psc-Sub` est présent |
| | `email`, `username` | `loadtest-{n}@loadtest.local` |
| `mss_accounts` | `mailbox_address` | `loadtest-{n}@loadtest.local` |
| | `database_name` | le nom que le banc utilise déjà — **enregistré, jamais réinventé** |
| | `is_default` | `true` |
| | `validated_by_psc_subject` | le **`PscSub`** du praticien |
| | `validated_by_rpps` | le **`Rpps`** du praticien |

**Les identités doivent correspondre au bit près** à ce que le harnais enverra, sans quoi
`MailboxCompatibility` règle 4 refusera la session en `PscIdentityConflict`. La source
existe déjà et est partagée : `LoadTestPlanGenerator`
(`tests/mss.mail.testing.shared/LoadTestPlanGenerator.cs`) produit
`Rpps => $"9{Index:D10}"` et `PscSub => $"00000000-0000-4000-8000-{Index:D12}"` — exactement
ce que `identity.js` reproduit côté k6. **Le seeder doit s'en servir, pas recalculer.**

> **Les deux colonnes `validated_by_*` sont `NOT NULL` depuis task-308.** Le seeder ne peut
> donc pas produire un rattachement à moitié : soit il porte l'identité, soit l'insertion
> échoue. C'est la contrainte qui travaille pour nous.

## Definition of Done

- [ ] Build passes on `api-mail` (0 erreur) ; tests passent (0 échec)
- [ ] Le seeder provisionne `accounts` + `mss_accounts` pour **chaque** praticien
      synthétique, avec les identités issues de `LoadTestPlanGenerator` — **jamais
      recalculées sur place**
- [ ] **Idempotent** : rejouer le seed sur un registre déjà provisionné ne duplique rien et
      n'échoue pas. Le banc se re-seede souvent, parfois partiellement
- [ ] Le `database_name` écrit est **celui que le banc utilise déjà** pour la base du
      praticien. Un test le vérifie en comparant à la valeur que le seeder emploie pour
      créer la base — une divergence enverrait les traces d'audit sur un tenant dont la base
      n'existe pas
- [ ] **Le test qui prouve l'US** : après seed, une requête du harnais sur
      `GET /api/v1/mail/folders` avec les en-têtes d'un praticien synthétique répond
      **200**, pas 4xx. Automatisable en test d'intégration avec le bypass de test
- [ ] **Le TenantId est renseigné** : sur cette même requête, `userContext.TenantId` est non
      nul et vaut l'`id` de la ligne `mss_accounts` du praticien. C'est la condition pour
      que le journal mutualisé soit exercé
- [ ] Un test vérifie qu'une trace d'audit émise pendant un tir atterrit dans
      `audit_traces` de la base commune (et **non** dans la base praticien), avec le bon
      `tenant_id`
- [ ] Le seeder **échoue bruyamment** si le registre est injoignable. Un banc qui se seede
      à moitié produit un tir vert qui ne mesure rien — c'est le pire résultat possible
- [ ] `docs/loadtest.md` (ou la doc du banc) mentionne l'étape de provisionnement du
      registre : un exploitant qui seede à la main doit savoir qu'elle existe

## Manual Test Plan

- **Lancer** : `cd Api/Mail && aspire run --project src/AppHost` avec le profil
  `loadtest`.
- **Actions et vérifications** :
  1. Partir d'un registre **vide** :
     `docker exec postgres-pgvector psql -U postgres -d mss_registry -c "delete from mss_accounts; delete from accounts;"`
  2. Lancer le seed du banc pour un petit effectif (ex. `--users 5`).
  3. Vérifier le registre :
     `docker exec postgres-pgvector psql -U postgres -d mss_registry -c "select a.authentication_subject, a.email, m.mailbox_address, m.validated_by_rpps, m.is_default from accounts a join mss_accounts m on m.account_id=a.id order by a.email;"`
     → **5 lignes**, `validated_by_psc_subject` et `validated_by_rpps` renseignés,
     `is_default = t`.
  4. **Rejouer le seed à l'identique** → toujours 5 lignes, aucune erreur (idempotence).
  5. Tirer un k6 très court (ex. `--vus 2 --duration 30s`, scénario `folders`).
  6. **Attendu** : taux d'erreur **0 %**. Avant cette US, il serait de 100 %.
  7. Vérifier que le journal mutualisé est alimenté :
     `docker exec postgres-pgvector psql -U postgres -d mss_registry -c "select count(*), count(distinct tenant_id) from audit_traces;"`
     → un compte **non nul**, et autant de `tenant_id` distincts que de praticiens
     sollicités. **C'est la vérification qui prouve que l'audit route correctement.**
  8. **Contre-épreuve** : vider `mss_accounts` sans vider `accounts`, relancer le tir →
     **100 % d'erreurs**. C'est le défaut que cette US corrige, reproduit à la demande.
- **Données de test** : praticiens synthétiques `loadtest-{n}@loadtest.local`. Aucune
  donnée de santé réelle, aucun opérateur MSSanté contacté.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — outillage de test de charge, jamais déployé
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — aucun patient. Les praticiens du banc sont synthétiques et
  leurs adresses sont en `.local`, non routables
- **Authentification PS** : **contournée par construction, et c'est borné.** Le banc passe
  par `TestBypassAuthenticationHandler`, protégé par l'en-tête `X-Test-Bypass` et une clé
  (`MSS_LOADTEST_BYPASS_KEY`). Cette US **n'élargit pas** ce contournement : elle écrit des
  lignes de registre, elle ne touche ni le handler, ni sa clé, ni son périmètre
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : **restauré.** Sans cette US, les traces du banc retombent sur la base
  praticien et le journal mutualisé n'est jamais exercé — donc jamais éprouvé en charge,
  alors que c'est précisément l'organe dont task-300 a corrigé la tenue à 1000 praticiens.
  Les traces produites restent synthétiques et confinées au banc
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non applicable — banc local, données synthétiques
- **AIPD / impact RGPD** : aucun — aucune donnée personnelle réelle n'entre dans le banc

### DOD santé applicable

- [ ] Les identités écrites dans le registre sont **exclusivement** synthétiques
      (`loadtest-*@loadtest.local`, RPPS en `9…`, `PscSub` en UUID de test). Un test refuse
      tout domaine autre que celui configuré pour le banc
- [ ] Le seeder **refuse de s'exécuter** contre un registre qui contiendrait déjà des
      comptes non synthétiques — garde-fou contre un pointage accidentel sur un
      environnement réel

## Ce que cette US n'est pas

- **Pas un retour en arrière sur task-308.** Le rattachement automatique reste supprimé
  pour les praticiens réels. Le banc, lui, n'a pas d'opérateur MSSanté à interroger : il
  écrit directement ce que l'onboarding écrirait, comme il écrit déjà les maildirs et les
  bases praticien.
- **Pas l'ajout de `loadtest.local` à la configuration produit.** Ce serait faire entrer
  une configuration de banc dans `appsettings.json`, et payer mille sondes IMAP au
  provisionnement.
- **Pas une modification du bypass de test.** `TestBypassAuthenticationHandler` émet encore
  `mssEmail` / `mssSub` / `mssRpps` — claims devenus morts après task-308, laissés en place
  car inoffensifs. Leur retrait est un ménage séparé, sans urgence.
- **Pas une campagne de charge.** Cette US rend le banc exploitable ; elle ne tire pas. La
  campagne qui suivra devra **re-établir une référence**, les tirs antérieurs à task-300
  n'étant plus comparables.

## Branches

- `api-mail` (pushed) : `fix/task-311-seeder-provisionne-registre` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-311-seeder-provisionne-registre
- `dtos-mss` (pushed, auto-inclus) : `fix/task-311-seeder-provisionne-registre` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/fix/task-311-seeder-provisionne-registre

## Timings

*(généré par `tools/timing/report.sh --task task-311 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 59 s | — | — | — | — |
| /develop | ok | 46 min 36 s | 4 (1 min 35 s) | 7 (5 min 14 s) | — | api-mail 4B/7T |
| /sonar | ok | 11 min 13 s | 1 (20 s) | 5 (3 min 38 s) | — | 1 itération(s), api-mail 1B/5T |
| /lint-angular | skipped | 3.2 s | — | — | — | client-angular non touche (Repos: api-mail) |
| /lint-mobile | skipped | 3.0 s | — | — | — | client-mobile non touche (Repos: api-mail) |
| /verify-visual | skipped | 2.7 s | — | — | — | aucun ecran client-mobile touche (Repos: api-mail) |
| /review | ok | 8 min 59 s | 1 (9.7 s) | 1 (1 min 45 s) | — | api-mail 1B/1T |
| /tech-writer | ok | 3 min 53 s | — | — | — | — |
| **Total cycle** | | **1 h 11 min** | **6 (2 min 05 s)** | **13 (10 min 39 s)** | **0 (0.0 s)** | |

## Develop log

**Correctif livré** — le seeder du banc (`tests/mss.mail.loadtest.seed`) écrit
désormais, en **étape 0 et avant toute injection**, les deux lignes de registre
que l'onboarding écrirait pour chaque praticien synthétique.

### Ce qui a été écrit

| Fichier | Rôle |
|---|---|
| `tests/mss.mail.testing.shared/LoadTestRegistryProvisioner.cs` | La logique, partagée par le seeder **et** les suites de tests — une seule écriture du registre, pas une par appelant |
| `tests/mss.mail.loadtest.seed/RegistryComposition.cs` | La composition DI : le **câblage de production** du registre, plus la mise à niveau idempotente du schéma |
| `tests/mss.mail.loadtest.seed/Program.cs` | L'étape 0, et son échec bruyant |
| `tests/mss.mail.loadtest.seed/SeedOptions.cs` | `--registry` + variable `TenantRegistry__ConnectionString` (même nom que côté AppHost) |
| `src/Infrastructure/Extensions/ServiceCollectionExtensions.cs` | `AddTenantRegistry` rendue **publique** — la seule ligne de production touchée |
| `docs/loadtest.md` | L'étape 0 documentée, avec les deux requêtes psql de contrôle |

### Décisions de conception

- **Écrire par le contrat, jamais en SQL.** Le provisionnement passe par
  `ITenantRegistryClient.EnsureAccountAsync` + `AttachMailboxAsync`, c'est-à-dire
  le chemin d'écriture de l'onboarding moins la sonde XOAUTH2 (impossible pour un
  domaine hors `MailServers.Domains`). Un `INSERT` de banc aurait ré-implémenté en
  silence la normalisation d'adresse, le choix de la boîte par défaut, l'ancrage
  PSC et l'unicité « un RPPS = un compte ». **Contrepartie assumée** : le seed
  dépend maintenant de `mss.mail.infrastructure` et son `packages.lock.json`
  grossit — sans conséquence pour un outil jamais livré.
- **Le balayage de garde est aussi la sonde de joignabilité.** `ListTenantsAsync`
  est l'une des rares lectures du contrat qui **propagent** la panne ; les lectures
  du chemin de requête dégradent en « je ne sais pas », ce qui rendrait un registre
  injoignable indistinguable d'un registre vide.
- **`database_name` = `UserContextInfo.ProposeDatabaseName(email, rpps)`** — la
  fonction du produit, appelée avec exactement ce que le harnais envoie. C'est
  aussi ce sur quoi le middleware retombait avant que le rattachement n'existe,
  donc le banc retrouve **ses** bases, il n'en crée pas de neuves.

### Vérifications

- `dotnet build HealthPlatform.Api.Mail.sln` : **0 erreur**.
- 7 tests unitaires (`LoadTestRegistryProvisionerTests`) : verts.
- 5 tests d'intégration (`LoadTestBenchProvisioningIntegrationTests`, vrai
  PostgreSQL) : verts — dont **le test qui prouve l'US** (requête du harnais sur
  `/api/v1/mail/folders` → **200**, `TenantId` = `mss_accounts.id`), sa
  **contre-épreuve** (praticien non provisionné → **403**), l'idempotence contre
  les contraintes réelles, et la trace d'audit qui atterrit dans `audit_traces` de
  la base commune sous le bon `tenant_id`.
- Suite complète : **4 632 tests, 5 échecs — tous pré-existants**
  (`…Today…` / `…NotSeenToday…` sur IMAP), vérifiés en rejouant les mêmes tests
  sur `develop` nu, travail remisé : mêmes échecs, mêmes assertions vides.

### Écart assumé avec la DOD

La DOD demande le test sur `GET /api/v1/mail/folders` « automatisable en test
d'intégration avec le bypass de test ». Le test monte **le vrai chemin
d'identité** — bypass, `UserContextEnricherMiddleware`, résolution de boîte
contre un vrai registre PostgreSQL — devant une **sonde** qui rend le contexte
utilisateur, plutôt que devant `MailController`. Raison : le refus que cette US
corrige est émis **par le middleware, avant le contrôleur** ; monter Dovecot et
une base praticien pour observer un refus qui ne les atteint jamais n'aurait rien
prouvé de plus, et aurait rendu la preuve tributaire d'IMAP. La vérification
bout-en-bout avec le vrai contrôleur reste le Manual Test Plan (étapes 5 à 7).

## Passe qualité (`/simplify`, intégrée à `/develop`)

Quatre angles (réutilisation, simplification, efficacité, altitude). **Un défaut
réel trouvé**, et corrigé :

> **Parité du bootstrap du registre.** `RegistryComposition` ne rejouait que la
> migration ; le service hébergé, lui, enchaîne migration **puis avance de
> partitions du journal d'audit**. Un seed lancé avant le premier démarrage
> d'api-mail — un cas normal du banc, et la raison même de migrer ici — obtenait
> donc un schéma à jour **sans partitions**, et les traces du tir seraient tombées
> dans la partition `DEFAULT`. Dans l'organe que cette US existe précisément pour
> faire exercer. `TenantRegistryBootstrap.Ensure` porte désormais la définition
> unique de « la base commune est prête » ; le service hébergé et l'outillage
> l'appellent tous deux.

Autres cleanups appliqués : extension DI **étroite**
(`AddTenantRegistryClient`) au lieu de publier `AddTenantRegistry` entier ;
garde de domaine rendue **non tautologique** (refus des domaines routables,
suffixes réservés RFC 2606/6761, deux théories) ; balayage d'entrée qui sert
trois fois au lieu d'une (garde, sonde de joignabilité, inventaire — un re-seed
ne repaie plus ~10 000 allers-retours) ; `ContextFactory` dédupliqué de **quatre
copies** à une (`Fixtures/TenantRegistryTestClient`), les trois classes
préexistantes migrées ; stubs manuscrits → `Substitute.For<>()` ; assertion
tautologique supprimée.

**Écartés, et pourquoi** : paralléliser la boucle de provisionnement (le coût
dominant du seed est ailleurs — ~15 s par praticien côté settings — et des
écritures concurrentes frotteraient contre l'invariant « un RPPS = un compte ») ;
scinder `MailboxManagementService.AttachAsync` en sonde + persistance pour que le
banc réutilise la seconde moitié (remodeler le produit pour l'outillage, hors
diff) ; promouvoir le découpage d'adresse e-mail en helper de domaine (touche
deux services de production hors diff).

Re-validation après cleanups : build **0 erreur**, 72 tests unitaires `LoadTest`
verts, 32 tests d'intégration `TenantRegistry` verts (dont les trois classes
migrées), suite complète inchangée — **mêmes 5 échecs pré-existants, aucun
nouveau**.

## Sonar log

Analyse complète jouée sur la branche `fix/task-311-seeder-provisionne-registre`
(begin → build Release → 5 passes OpenCover → end), projet
`healthplatform-api-mail`.

### KPIs

| Mesure | Baseline (analyse du 2026-09-08) | Final (cette analyse) | Cible |
|---|---|---|---|
| Bugs | 2 | 2 | 0 |
| Vulnérabilités | 0 | 2 | 0 |
| Code smells | 72 | 253 | — |
| Couverture | 88,2 % | 87,6 % | ≥ 95 % |
| Security hotspots `TO_REVIEW` | 15 | 15 | 0 |
| Note fiabilité | C (3) | C (3) | A |
| Note sécurité | A (1) | E (5) | A |
| Note maintenabilité | **A (1)** | **A (1)** | A |
| **Quality Gate** | **ERROR** | **ERROR** | OK |

### Phase 1 — new code de cette task : **rien à corriger**

**Zéro finding sur les fichiers touchés par task-311**, vérifié de deux façons
indépendantes :

1. Filtrage des 181 violations du *new code period* par composant : aucune ne
   porte sur un fichier de cette task (le seul `ServiceCollectionExtensions.cs`
   qui remonte est celui de **`src/Application`**, que la task ne touche pas —
   elle modifie celui de `src/Infrastructure`).
2. Dates de création des issues ouvertes : elles s'échelonnent du 2025-12-28 au
   2026-09-14. **Aucune issue datée d'aujourd'hui.**

### Pourquoi les chiffres bougent quand même

La *new code period* du projet **inclut les tasks déjà mergées** depuis la
dernière analyse (2026-09-08) : 15 issues du 2026-09-11, 11 du 2026-09-13 et 18
du 2026-09-14 — c'est-à-dire l'EPIC E016 (tasks 299 à 308). Le Quality Gate est
donc `ERROR` sans qu'aucune dette n'ait été introduite ici ; c'est un piège connu
de ce projet, à ne pas relire comme une régression de cette PR.

L'écart smells 72 → 253 et la note de sécurité A → E viennent du **périmètre
analysé**, pas du code : cette analyse a couvert l'outillage du banc
(`tests/loadtest-k6/**` — 24 fichiers `.py`, 24 `.js`, 2 `.ps1`) que la
précédente n'avait pas indexé. Les deux « vulnérabilités » sont deux
`secrets:S6698` sur `observe.ps1` — le littéral `PGPASSWORD=postgres`, c'est-à-dire
**l'identifiant synthétique du Postgres de banc local**, le même que le défaut
`MSS_BENCH_PG_PASSWORD` de l'AppHost. Aucun secret réel n'est exposé.

### Phase 2 — dette héritée : **volontairement non traitée**

Les 181 findings restants vivent dans l'outillage k6 (Python/JS/PowerShell) et
dans du code applicatif antérieur. Les corriger ici aurait :

- fait sortir la PR de son module (règle 6) et du plafond de ~30 fichiers
  (règle 5) ;
- introduit dans `observe.ps1` — script PowerShell de sonde, **non couvert par
  les tests** et non exécutable sans le banc monté — une modification que ce
  cycle n'aurait pas pu vérifier. Un correctif invérifiable sur un script
  d'observation vaut moins que le finding cosmétique qu'il efface.

**À traiter séparément** : le paramétrage de `PGPASSWORD` dans
`tests/loadtest-k6/observe.ps1` (4 occurrences, dont 2 signalées), sur le modèle
`MSS_BENCH_PG_PASSWORD` déjà en vigueur dans l'AppHost. C'est ce qui ramènera la
note de sécurité à A.

## PRs

- `api-mail` (pushed) : **[PR #240](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/240)** — label `awaiting-human-merge`
- `dtos-mss` (auto-inclus) : branche créée par `/start`, **aucun commit** — la task
  ne touche aucun contrat DTO. Pas de PR ; la branche vide est nettoyée au `/merge`.

## Code Review Summary

**APPROVED** — 16 fichiers, 0 blocage, 2 suggestions non bloquantes.

Un **défaut réel** trouvé par la passe qualité et corrigé dans le cycle : la
composition du seeder ne rejouait que la migration du registre, pas l'avance de
partitions du journal d'audit. Un seed lancé avant le premier démarrage
d'api-mail aurait donc envoyé les traces du tir dans la partition `DEFAULT` —
dans l'organe même que cette US existe pour faire exercer.
`TenantRegistryBootstrap` porte désormais la définition unique de « la base
commune est prête ». **Vérifié empiriquement** : registre neuf créé par le
seeder ⇒ 6 objets `audit_traces` (table partitionnée + 5 partitions) ; 1 seul
sans le correctif.

Suggestions non bloquantes : portée DI explicite dans `RegistryComposition`
(le client est `scoped`, résolu depuis la racine — correct aujourd'hui,
`ValidateScopes` étant inactif, et vérifié à l'exécution) ; la projection
Keycloak d'un compte n'est pas rafraîchie au re-jeu (sans effet : elle ne
résout rien et ne change jamais pour un praticien synthétique).

## Vérification en conditions réelles

Seeder exécuté contre le PostgreSQL du banc sur un registre neuf : 1er passage
**3 lignes créées**, 2e passage **« 0 créé(s), 3 déjà présent(s) »**. Lignes
contrôlées en base (`authentication_subject` = `PscSub`, `database_name` en
`u_{rpps}_{slug}_{hash}`, `is_default = t`). Base de test supprimée après coup.
