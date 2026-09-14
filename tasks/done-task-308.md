# todo-task-308.md — Le registre se sépare en deux identités : `accounts` ne dit plus que Keycloak, et le rattachement passe exclusivement par l'onboarding PSC

**Repos**: api-mail, client-blazor, client-mobile, client-angular
**Dependencies**: **task-303** (la bascule registre) et **task-304** (le sélecteur de boîtes sur
les trois fronts) — toutes deux **mergées sur `develop` le 2026-09-14** et archivées ;
**task-299** (le schéma du registre, archivée). `develop` porte donc bien le code que cette US
doit retirer.
Aucune dépendance sortante. **Doit passer avant la mise en production** : après, le retrait des
deux chemins coûterait une migration de données au lieu d'une purge.
**Epic**: E016
**Priorité**: **1** — la fenêtre est ouverte tant que l'application n'est pas en production.
Arbitrage humain du 2026-09-14 : « pas besoin de migrer la legacy, on assume une phase
d'onboarding ».

## Objective

Deux changements indissociables, parce que le second n'est tenable que si le premier a lieu.

**1. Un seul écrivain.** Supprimer les **deux** chemins qui créent un rattachement de messagerie
sans identité PSC et sans sonde IMAP. Après cette US, `mss_accounts` n'a plus qu'**un seul
écrivain** : `POST /api/v1/account/mailboxes`, c'est-à-dire l'onboarding.

**2. Deux identités, deux tables.** `accounts` devient la **projection du user Keycloak** — le
`sub`, l'`email`, le `username`, les horodatages — et **rien d'autre**. L'identité
professionnelle (`rpps`, `psc_subject`) descend sur `mss_accounts`, à côté du
`validated_by_psc_subject` qui l'attend déjà : c'est l'**opérateur MSSanté** qui la délivre, au
rattachement, jamais Keycloak.

Un compte neuf porte donc une ligne `accounts` purement Keycloak et **zéro** rattachement — état
dans lequel les trois fronts déclenchent déjà l'onboarding.

> **Pourquoi les deux ensemble.** Tant que le synchroniseur crée des rattachements sans identité
> PSC, `validated_by_rpps` ne peut pas être `NOT NULL` — il resterait nul sur toutes les lignes
> qu'il fabrique. Sortir `rpps` de `accounts` sans couper ce chemin laisserait l'ancrage sans
> aucun porteur fiable. Le découpage en deux US produirait un état intermédiaire où l'identité
> professionnelle n'est garantie nulle part.

## Ce que la mesure a établi — 2026-09-14, première connexion réelle

Un praticien se connecte pour la première fois via Keycloak + proxy + PSC. Il **ne voit pas**
l'onboarding : la messagerie s'ouvre directement. Le registre a été rempli avant que le front
n'ait pu poser la question.

```
16:34:43.395   accounts.created_at          <- EnsureAccountAsync        (compte Keycloak seul, correct)
16:34:43.691   mss_accounts.attached_at     <- EnsureCurrentTenantAsync  <- LE rattachement automatique
16:34:43.801   [LegacyClaims] Compte migre  <- n'a fait que l'ANCRAGE du compte
```

La ligne a été créée à `.691` par `TenantRegistrySynchronizer.EnsureCurrentTenantAsync`, depuis le
seul claim `mssEmail`. **La preuve matérielle est un `NULL`** : `EnsureTenantAsync` pose
`ValidatedByPscSubject` *à la création* du rattachement (`PostgresTenantRegistryClient.cs:185`).
Or la ligne produite porte :

| colonne | valeur | lecture |
|---|---|---|
| `accounts.psc_subject` | `e3ba824c-…` | compte **ancré** |
| `accounts.rpps` | `899700622675` | ancré depuis les claims — ce que task-299 interdisait |
| `mss_accounts.validated_by_psc_subject` | **`NULL`** | rattachement **jamais validé par un opérateur** |
| `mss_accounts.is_default` | `t` | et pourtant retenu comme boîte par défaut |

Conséquence dans `MailboxCompatibility.Evaluate` : les **deux** règles qui comparent
`ValidatedByPscSubject` sont court-circuitées. Rien n'est exploitable aujourd'hui — l'ancrage du
compte tient encore la garde (règle 4) — mais la validation **par rattachement**, celle qui
protège une adresse organisationnelle partagée entre deux praticiens, est absente de la ligne.

> **Le point non évident, et la raison d'être de cette US.** Supprimer `LegacyClaimsMigration` —
> le coupable apparent — **ne suffirait pas** : le rattachement est créé par le synchroniseur,
> *avant* elle. La migration n'a fait que l'ancrage. C'est le synchroniseur qu'il faut couper en
> premier.

## Les deux chemins à couper

### 1. `TenantRegistrySynchronizer.EnsureCurrentTenantAsync` — le provisionneur réel

Il appelle `EnsureTenantAsync(subject, mailboxAddress, databaseName)` à **chaque requête
authentifiée**, sans identité PSC, avec `userContext.Email` (donc le claim `mssEmail`) pour seule
source. Le synchroniseur doit se borner à ce que son nom promet et à ce que le modèle cible
demande : `EnsureAccountAsync` (la ligne Keycloak-seule), `TouchAuthentication`, `TouchActivity`.
**Il ne fabrique plus jamais de rattachement.**

Son `TenantId` de retour est déjà redondant : `ApplyMailboxSelectionAsync` le **recale** plus bas
sur la boîte réellement retenue (`UserContextEnricherMiddleware.cs:796`), et le commentaire de
task-303 le dit explicitement. Le supprimer ne prive donc le journal d'audit d'aucune clé.

### 2. `LegacyClaimsMigration` — l'ancrage depuis les claims

Son contrat de sortie était : « zéro pendant trente jours en production, puis retrait ».
L'application n'est pas en production et n'y ira pas avec ce code. Le compteur n'a plus de
question à trancher : la classe part maintenant, avec `ILegacyClaimsMigration`, son enregistrement
DI, le champ `LegacyClaims` de `RequestIdentityServices` et les deux compteurs
`RegistryMetrics.LegacyClaimsMigrations` / `LegacyClaimsConflicts`.

### Effet de bord vérifié : `EnsureTenantAsync` devient du code mort

Ses **deux** seuls appelants sont les deux chemins ci-dessus. L'opération et son
`EnsureTenantRequest` sortent donc du contrat `ITenantRegistryClient` et de son implémentation.
Laisser en place une opération capable de créer un rattachement sans identité PSC, c'est laisser
en place la faute qu'on vient de retirer : le prochain appelant la commettra de bonne foi.

## Le nouveau schéma du registre — arbitrage humain du 2026-09-14

**Le principe.** `accounts` répond à « quel compte Keycloak ? ». `mss_accounts` répond à « quelle
messagerie, validée par quel professionnel ? ». Aucune ligne ne mélange plus les deux autorités.

```
accounts                      (projection Keycloak, PURE)
  id
  authentication_subject      sub Keycloak — unique, obligatoire
  email                       <- claim `email`               [AJOUTÉE]
  username                    <- claim `preferred_username`  [AJOUTÉE]
  last_authentication_at
  last_activity_at
  created_at
                              rpps         [SUPPRIMÉE]
                              psc_subject  [SUPPRIMÉE]

mss_accounts                  (rattachements + identité qui les a autorisés)
  ...
  validated_by_psc_subject    NOT NULL   [CONTRAINTE AJOUTÉE]
  validated_by_rpps           NOT NULL   [COLONNE AJOUTÉE]
```

**`email` et `username` sont dénormalisés et NON autoritaires.** Ils existent pour qu'une ligne du
registre soit lisible par un humain — support, diagnostic, demande RGPD — sans aller-retour vers
Keycloak. La **clé** reste `authentication_subject` : rien ne résout un compte par l'email, qui
est mutable et dont l'unicité dépend du réglage `Duplicate Emails` du realm. Ils sont
**rafraîchis à chaque synchronisation** depuis le jeton, jamais lus pour décider quoi que ce soit.

> ⚠️ **Dans `weda-realm` aujourd'hui, `email` et `username` valent tous deux l'adresse MSSanté**
> (`virginie.medecinrpps0062267@medecin.formation.mssante.fr`). Ce sont **malgré tout** des
> attributs Keycloak, pas la boîte du praticien : la boîte vit dans `mss_accounts.mailbox_address`,
> et un compte en porte N. **Ne jamais joindre `accounts.email` à `mss_accounts`**, ne jamais s'en
> servir pour résoudre une messagerie. Un commentaire de colonne doit le graver dans la migration.

### L'ancrage devient dérivé

`accounts.psc_subject` portait l'ancrage et la règle « pas de re-binding silencieux » (task-049,
règle 3). Sans cette colonne, l'ancrage se **dérive des rattachements** : *toutes les boîtes d'un
compte partagent la même identité PSC.* Un compte à zéro rattachement n'a **pas** d'ancrage — et
c'est exactement l'état cible, celui d'un compte Keycloak qui n'a encore rien rattaché. Le premier
`AttachAsync` établit l'identité ; les suivants doivent la respecter, sous peine de
`PscIdentityConflict`.

### Ce qu'on perd, et qui est assumé

L'index `ix_accounts_rpps` (unique partiel, « un RPPS = un compte ») **disparaît avec sa colonne**
et n'a pas d'équivalent par index sur `mss_accounts` : un praticien à N boîtes y produit N lignes
portant le même `validated_by_rpps`, donc aucun index unique ne peut l'exprimer. La garantie
descend au niveau **applicatif** et doit être couverte par un test : deux comptes Keycloak
distincts ne peuvent pas rattacher des boîtes sous le même RPPS. Arbitrage humain assumé — la
table dédiée `psc_identities` qui l'aurait tenue par index a été écartée.

### Le piège de lecture des claims — déjà payé une fois

`MapInboundClaims` n'est pas désactivé sur ce service. Le gestionnaire de jetons **renomme** les
revendications standard avant qu'elles n'atteignent le principal : `sub` devient
`ClaimTypes.NameIdentifier`, `email` devient `ClaimTypes.Email`. Un `FindFirstValue("email")`
rendrait donc **toujours `null`** — exactement la faute qui a coûté des semaines de `KcSub=<none>`
dans les journaux, documentée sur `TenantRegistrySynchronizer.ReadAuthenticationSubject`.

Lire **le nom mappé d'abord, le nom brut en repli**, comme le fait déjà ce helper :
- `email` → `ClaimTypes.Email`, puis `"email"`
- `username` → `"preferred_username"` (absent de la table de mappage par défaut), puis
  `ClaimTypes.Name` en repli

Vérifié le 2026-09-14 : le client `weda` du realm porte `email` et `profile` en scopes par défaut,
et **les deux mappers écrivent dans l'access token** (`access.token.claim = true`). Aucun appel à
l'API d'administration Keycloak n'est nécessaire — tout se lit sur le chemin de requête.

## Ce qui ne change pas — et qu'il faut protéger

- **La table de décision des trois fronts.** Le cas « liste vide → onboarding » est **déjà
  implémenté et identique** sur Angular (`mailbox-session.store.ts:295`), Mobile
  (`mailbox-session.service.ts:229`) et Blazor (`MailboxSessionService.cs:99`), et **déjà testé**
  sur les trois. Cette US n'y touche pas — elle en **prouve l'atterrissage** (cf. section
  suivante).
- **Le mode hors ligne.** `MailboxCompatibility` règle 3 — sans jeton PSC, une boîte **déjà
  rattachée** reste sélectionnable et lisible, sans écriture. Le PSC n'est exigé qu'au
  *rattachement*, jamais à la lecture. C'est l'arbitrage humain, et il est déjà codé.
- **Le chemin d'onboarding.** `MailboxManagementService.AttachAsync` fait déjà exactement ce que
  le modèle cible demande : session PSC obligatoire, **sonde IMAP en XOAUTH2 avant toute
  écriture**, puis ancrage du compte et `validated_by_psc_subject` depuis l'identité PSC réelle.
  Rien à y écrire.
- **Le retrait du refus « `mssEmail` absent → 403 »**, livré par task-303. Il reste retiré.

## Les trois fronts — ce qui est déjà là, et le seul trou

Audit mené sur `develop` le 2026-09-14, **après** le merge de task-303 et task-304.

| Contrôle | `client-angular` | `client-mobile` | `client-blazor` |
|---|---|---|---|
| Résidu de lecture de `mssEmail` / `mssSub` / `mssRpps` | **aucun** (commentaires seuls) | **aucun** | **aucun** |
| Décision « 0 boîte → `Onboarding` » | `mailbox-session.store.ts:295` | `mailbox-session.service.ts:229` | `MailboxSessionService.cs:99` |
| …et son test | `store.spec.ts:108` ✅ | `service.spec.ts:121` ✅ | `MailboxSessionServiceTests:107` ✅ |
| Garde câblée sur les routes | `canActivateChild: [mailboxGuard]` | `canActivate: [authGuard, mailboxGuard]` | `Mail.razor:189` → `NavigateTo` |
| **Test de la REDIRECTION** | **absent** ❌ | **absent** ❌ | **absent** ❌ |

**La décision est prouvée, l'atterrissage ne l'est pas.** `mailbox.guard.ts` n'a de `.spec.ts` ni
sur Angular ni sur Mobile ; le `switch` sur la décision dans `Mail.razor` n'est couvert par aucun
test Blazor — seuls les écrans d'arrivée le sont, rendus directement par bUnit.

**Pourquoi ça devient inacceptable avec cette US, et pas avant.** Tant que le claim `mssEmail`
peuplait le registre, l'onboarding était un chemin de secours que presque personne n'empruntait :
une redirection cassée se serait vue tard, et sans conséquence. Après 308, l'onboarding est le
**seul** moyen d'obtenir une boîte. Une garde qui cesse de rediriger ne laisse plus le praticien
devant un mauvais écran : elle le laisse devant une messagerie vide, sans aucun chemin pour en
rattacher une. C'est le mode d'échec que le filet doit couvrir.

> **Ce que l'US n'ajoute donc PAS côté front** : aucun écran, aucune logique, aucun changement de
> comportement. Uniquement **le test qui prouve que la règle se déclenche**, sur chacun des trois.

### Note d'environnement — l'état cible est déjà atteignable

L'humain a retiré `mssEmail` / `mssSub` / `mssRpps` du user Keycloak le 2026-09-14. Sans ces
claims, `EnsureCurrentTenantAsync` sort sur `mailboxAddress` vide et `LegacyClaimsMigration`
retourne `false` : **le registre n'est plus peuplé automatiquement**, et l'onboarding se déclenche
déjà sur `develop`. Cette US ne crée donc pas le comportement — elle le rend **impossible à
régresser**, en supprimant les deux chemins qui le contournaient et en verrouillant l'invariant
dans la base. Pour l'observer sans attendre l'US, il suffit de purger le rattachement hérité
(cf. Manual Test Plan, étape de préparation).

## Definition of Done

- [ ] Build passes on `api-mail` (0 errors) ; tests pass (0 failures)
- [ ] `TenantRegistrySynchronizer` ne crée **aucun** rattachement : `EnsureCurrentTenantAsync` est
      supprimée. **Test** : compte connu du registre, sans rattachement, jeton portant `mssEmail`
      → après une requête authentifiée, `mss_accounts` compte **0 ligne** pour ce compte
- [ ] `SynchroniseAsync` conserve ses trois effets : création du compte au premier contact,
      `TouchAuthentication` par session applicative inédite, `TouchActivity` sous bride. Les tests
      existants de ces trois comportements restent verts **sans modification de leurs assertions**
- [ ] `userContext.TenantId` provient **exclusivement** de la résolution de boîte
      (`UserContextEnricherMiddleware.cs:796`). **Test** : requête authentifiée d'un compte sans
      rattachement → `TenantId` nul, aucune exception, la trace retombe sur la base praticien
- [ ] `LegacyClaimsMigration`, `ILegacyClaimsMigration`, son `AddScoped` de
      `ServiceCollectionExtensions`, le champ `LegacyClaims` de `RequestIdentityServices` et les
      compteurs `RegistryMetrics.LegacyClaimsMigrations` / `LegacyClaimsConflicts` sont
      **supprimés**. Vérification binaire : `grep -rn "LegacyClaims" Api/Mail/src` → **0 résultat**
- [ ] `ITenantRegistryClient.EnsureTenantAsync` et `EnsureTenantRequest` sont supprimés du contrat
      et de `PostgresTenantRegistryClient`. Leurs tests sont **supprimés**, jamais commentés ni
      mis en `Skip`
- [ ] Le claim `mssEmail` n'est plus lu : la ligne 431 de `UserContextEnricherMiddleware`
      disparaît, `userContext.Email` ne vient plus que de `selection.MailboxAddress` (l.784).
      Vérification : `grep -rn "mssEmail" Api/Mail/src` → **0 résultat**
- [ ] **Migration `TenantDb` NOUVELLE** (règle 7c — ne jamais éditer `20260913120000` ni
      `20260914160000`), dans cet ordre :
      1. `delete from mss_accounts where validated_by_psc_subject is null` — purge des
         rattachements hérités, assumée (l'application n'est pas en production)
      2. `alter table mss_accounts add column validated_by_rpps text` puis report depuis
         `accounts.rpps` **avant** la suppression de la colonne source
      3. `validated_by_psc_subject` et `validated_by_rpps` passent en **`NOT NULL`**
      4. `alter table accounts add column email text, add column username text`, avec un
         **commentaire de colonne** disant qu'elles sont dénormalisées, non autoritaires, et
         qu'elles ne doivent **jamais** être jointes à `mss_accounts`
      5. `drop index ix_accounts_rpps` puis `alter table accounts drop column rpps, drop column
         psc_subject`
      Le `Down()` relâche les contraintes et recrée les colonnes **vides** — il ne restaure aucune
      donnée. La purge n'est pas réversible, et le task file le dit
- [ ] `EnsureAccountAsync` renseigne **et rafraîchit** `email` / `username` à chaque
      synchronisation, depuis le jeton. **Test du piège `MapInboundClaims`** : un principal ne
      portant que les claims mappés (`ClaimTypes.Email`) **et** un principal ne portant que les
      claims bruts (`email`, `preferred_username`) donnent tous deux un compte renseigné. Un seul
      des deux cas testé ne vaut rien — c'est précisément l'angle mort qui a produit
      `KcSub=<none>`
- [ ] `RegistryAccount` perd `Rpps` et `PscSubject`, gagne `Email` et `Username`. `IsAnchored` et
      `PscIdentity.AnchorsAccount` sont **réécrits sur l'ancrage dérivé** (l'identité PSC commune
      aux rattachements du compte), pas supprimés
- [ ] `MailboxCompatibility` — les règles 2 et 4 lisent désormais l'ancrage dérivé.
      **Sa matrice de 14 tests reste verte**, assertions inchangées : la règle métier ne bouge
      pas, seule sa source de données change. Un test nouveau couvre le compte **sans aucun
      rattachement** → aucun ancrage, aucun blocage (c'est le premier contact)
- [ ] `AttachAsync` refuse toujours en `PscIdentityConflict` une identité PSC qui ne correspond pas
      à celle des rattachements existants. Test : compte avec une boîte validée par PSC-A, tentative
      de rattachement avec PSC-B → refus, **rien d'écrit**
- [ ] **L'unicité « un RPPS = un compte » devient un invariant applicatif** — l'index qui la tenait
      disparaît avec sa colonne. Test explicite : deux `authentication_subject` distincts tentant
      un rattachement sous le même RPPS → le second est refusé. Un commentaire de décision dit
      pourquoi la base ne peut plus le garantir (N boîtes = N lignes au même RPPS)
- [ ] **Aucun code ne résout un compte par `email` ou `username`.** Vérification : ces deux
      colonnes n'apparaissent dans aucune clause `Where` du dépôt, seulement en écriture et en
      lecture d'affichage
- [ ] La migration est couverte par `TenantRegistryMigrationScopeTests` — elle vit dans
      `mss.mail.Infrastructure.Migrations.TenantDb` et **ne fuit pas** dans les bases praticien
- [ ] `MailboxCompatibility` est **inchangé**, et ses tests des règles 2, 3 et 4 restent verts
      sans modification : le mode hors ligne d'une boîte rattachée ne se dégrade pas
- [ ] Un test d'intégration **bout en bout du cas cible** : compte neuf (0 rattachement) →
      `GET /api/v1/account/mailboxes` rend **200 + liste vide** (jamais 403) →
      `POST /api/v1/account/mailboxes` avec session PSC rend **201**, et la ligne créée porte
      `validated_by_psc_subject` **non nul** et `is_default = true`
- [ ] Un test de **refus** : `POST /api/v1/account/mailboxes` **sans** jeton PSC rend
      **400 `PscTokenRequired`** et n'écrit **rien** dans `mss_accounts`
- [ ] **`client-angular`** — test de garde `mailbox.guard.spec.ts` (nouveau fichier) : registre
      rendant **0 boîte** avec session PSC → la garde rend l'`UrlTree` du segment `onboarding` ;
      **0 boîte sans PSC** → segment `psc-required` ; **1 boîte sélectionnable par défaut** →
      `true` (aucun écran intercalé). Mode **code-only** : la forge écrit le test, l'humain gère
      branche, commit, push et PR TFS
- [ ] **`client-mobile`** — test de garde équivalent sur `mailbox.guard.ts` : `router.parseUrl`
      appelé avec `/onboarding`, `/mailbox-psc-required`, ou garde passante selon les trois mêmes
      cas
- [ ] **`client-blazor`** — test de la **redirection** de `Mail.razor` (bUnit) : `InitializeAsync`
      rendant `Onboarding` → `NavigationManager.Uri` se termine par `/Mail/onboarding` ;
      `PscRequired` → `/Mail/psc-required`. C'est le maillon non couvert : les tests actuels
      rendent les écrans directement, sans passer par la décision
- [ ] Les trois tests de garde échouent si la redirection est retirée — vérifié en la commentant
      une fois, puis en la rétablissant. **Une garde qui ne redirige plus doit faire rouge**
- [ ] Build + tests verts sur `client-blazor` (`dotnet test HealthPlatform.Client.sln`),
      `client-mobile` (`npm test -- --watch=false --browsers=ChromeHeadless`) et `client-angular`
      (`npm test`)
- [ ] **Aucun écran, aucune logique de décision, aucun libellé modifié sur les trois fronts.** Le
      diff front ne contient que des fichiers de test — vérifiable au `git diff --stat`
- [ ] `Docs/epics/E016-*.md` rafraîchi par `/tech-writer` : la section qui décrit la migration des
      claims hérités est remplacée par « un seul écrivain : l'onboarding »

## Manual Test Plan

- **Lancer** : `cd Api/Mail && aspire run --project src/AppHost`, puis le front de ton choix
  (Angular : `cd Client/Angular/front && npx nx serve weda2`).
- **Préparer le cas cible** (une seule fois, et c'est le test lui-même) :
  1. Retirer les attributs `mssEmail`, `mssSub`, `mssRpps` du user Keycloak dans le realm
     `weda-realm` (`https://localhost:5600`, admin/admin). Conserver `cauRoles`.
  2. Purger le registre (avant migration — les colonnes `rpps` / `psc_subject` existent encore) :
     `docker exec postgres-pgvector psql -U postgres -d mss_registry -c "delete from mss_accounts; update accounts set rpps=null, psc_subject=null;"`
- **Actions et vérifications** :
  1. Se connecter via Keycloak + PSC. **Attendu : l'écran d'onboarding s'affiche**, pas la boîte
     de réception.
  2. Vérifier l'état du registre **avant** tout rattachement :
     `docker exec postgres-pgvector psql -U postgres -d mss_registry -c "\d accounts; select id, authentication_subject, email, username from accounts; select count(*) from mss_accounts;"`
     → la table `accounts` **ne porte plus** `rpps` ni `psc_subject` ; sa ligne unique porte le
     `sub` Keycloak, l'`email` et le `username` renseignés depuis le jeton ; `mss_accounts` est
     **vide**. C'est l'état cible de l'US : un compte qui ne dit que Keycloak, aucune messagerie.
  3. Saisir l'adresse MSSanté dans l'onboarding et valider. **Attendu : 201**, la messagerie
     s'ouvre.
  4. Re-vérifier : `mss_accounts` porte **une** ligne, avec `validated_by_psc_subject` **et**
     `validated_by_rpps` **non nuls** et `is_default = t`. `accounts` est **inchangée** — c'est le
     rattachement qui porte l'identité professionnelle, plus le compte.
  4bis. **Contre-épreuve de l'ancrage dérivé** : tenter un second rattachement avec un jeton PSC
     d'un **autre** professionnel → **409 `PscIdentityConflict`**, et `mss_accounts` toujours à une
     seule ligne. C'est la règle anti-ré-association (task-049) qui doit survivre au déménagement
     de l'ancrage.
  5. **Le test qui prouve l'US** : se déconnecter, se reconnecter. La messagerie s'ouvre
     directement, **et aucune nouvelle ligne n'apparaît** dans `mss_accounts`.
  6. **Mode hors ligne** : se reconnecter sans session PSC. La boîte rattachée reste
     **sélectionnable et lisible**, l'envoi et les drapeaux sont grisés. Le PSC n'est exigé qu'au
     rattachement.
  7. Répéter les étapes 1 et 3 sur **client-mobile** et **client-blazor** — même écran, même
     résultat, aucun code front n'ayant été touché.
- **Données de test** : praticien synthétique du realm de formation, boîte MSSanté de formation.
  Aucune donnée de santé réelle.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — durcissement du socle d'identité
- **Exigences DSR honorées** : non applicable
- **INS** : aucune donnée de santé lue ni écrite. L'US touche des identifiants de compte et de
  rattachement
- **Authentification PS** : **c'est l'objet de l'US.** Le rattachement d'une messagerie redevient
  conditionné à une session Pro Santé Connect active et à une sonde XOAUTH2 réussie auprès de
  l'opérateur MSSanté. Aujourd'hui, un claim Keycloak suffit à créer le rattachement : l'opérateur
  n'est jamais consulté. Après, il est la seule autorité — ce que task-049 et task-299 avaient posé
  comme règle et que le chemin de transition contournait
- **Habilitations** : resserrées, jamais élargies. Aucune route nouvelle. Le seul changement
  observable pour un praticien déjà rattaché est **nul** ; pour un compte neuf, l'onboarding
  remplace un rattachement implicite
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : amélioré. `validated_by_psc_subject` devient `NOT NULL` : chaque rattachement
  porte désormais l'identité PSC qui l'a autorisé, donc chaque `TenantId` du journal d'audit est
  rattachable à un professionnel identifié. Le `NULL` observé le 2026-09-14 rendait cette chaîne
  incomplète
- **Consentement patient** : non applicable
- **Référentiels métier** : RPPS, via PSC — désormais lu du seul jeton PSC, jamais d'un claim
  Keycloak
- **Hébergement HDS** : inchangé
- **AIPD / impact RGPD** : **mitigé, et il faut le dire des deux côtés.** Au crédit : trois
  attributs personnels (`mssEmail`, `mssSub`, `mssRpps`) cessent d'être dupliqués dans le profil
  Keycloak et dans les jetons, et la purge des rattachements non validés supprime des données dont
  l'origine n'est pas traçable. Au débit : **`accounts` gagne deux données personnelles
  dénormalisées** (`email`, `username`) qui n'y étaient pas. Elles ne sont pas nouvelles pour la
  plateforme — Keycloak les détient déjà — mais elles créent une **deuxième copie**, donc un
  deuxième point de purge lors d'une demande d'effacement. Le registre étant déjà soumis à la
  purge des comptes dormants (task-299), le chemin existe ; il doit couvrir ces colonnes

## Ce que cette US n'est pas

- **Pas une US de comportement front.** Les trois fronts gèrent déjà le cas « liste vide →
  onboarding », et leur table de décision est identique et testée. Le diff front de cette US ne
  contient **que des fichiers de test** : la garde de redirection, seul maillon non couvert, que
  l'US rend porteur en supprimant tout autre chemin d'obtention d'une boîte. Aucun écran, aucune
  logique, aucun libellé.
- **Pas un durcissement du mode hors ligne.** Il reste tel quel : une boîte **rattachée** se lit
  sans PSC. L'US ne déplace le PSC que sur l'acte de rattachement.
- **Pas la suppression des mappers Keycloak ni de `PUT /v1/admin/mss-profile`.** Ils vivent dans
  `psc-auth-proxy`, hors automation de la forge (repos `psc-proxy-*` entièrement manuels). Cette
  US rend leur retrait **possible et sans effet de bord** côté `api-mail` ; le retrait lui-même
  est une action humaine, à faire après le merge.
- **Pas une table `psc_identities`.** L'alternative qui aurait gardé « un RPPS = un compte »
  garanti par index a été **écartée par arbitrage humain** le 2026-09-14, au profit de la descente
  sur `mss_accounts`. La contrepartie — unicité RPPS devenue applicative — est inscrite au DOD.
- **Pas une clé de résolution nouvelle.** `email` et `username` arrivent sur `accounts` pour la
  **lisibilité** du registre, jamais pour résoudre un compte ni une messagerie. Le jour où une
  requête filtrera sur `accounts.email`, la conflation « 1 compte = 1 boîte » que task-303 a
  démontée sera revenue — c'est ce que le DOD « aucune clause `Where` » empêche.

## Branches

Créées par `/start 308` le 2026-09-14, depuis `origin/develop` (post-merge de task-303 et
task-304 — `develop` porte donc bien le code que cette US doit retirer).

- `api-mail` (pushed) : `feat/task-308-registre-deux-identites`
  https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-308-registre-deux-identites
- `client-blazor` (pushed) : `feat/task-308-registre-deux-identites`
  https://github.com/codengine-technologies/HealthPlatform.Client/tree/feat/task-308-registre-deux-identites
- `client-mobile` (pushed) : `feat/task-308-registre-deux-identites`
  https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-308-registre-deux-identites
- `dtos-mss` (pushed, auto-incluse) : `feat/task-308-registre-deux-identites`
  https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-308-registre-deux-identites
- `client-angular` (code-only) : la forge écrit sur la branche actuellement checked out dans
  `Client/Angular/` — instantané au moment du `/start` : `feature/nova-rewriting-mss-tenant`. L'humain gère branche, commit,
  push et PR TFS.

> Pré-vol : `api-mail`, `client-blazor`, `client-mobile`, `dtos-mss`, `sdk` tous sur `develop`,
> arbres propres. `host` et `interop-cda` n'ont pas de dépôt sur ce poste — non mesurables
> (cf. avertissement CLAUDE.md). `client-angular` hors pré-vol (code-only).
>
> ⚠️ `Client/Angular/` porte des modifications non committées au moment du `/start`, dont le
> correctif NG0200 (cycle d'injection `MSS_USER_EMAIL` → `MailboxSessionStore` →
> `MSS_RESETTABLE_STORES` → `MailEventsStreamService`) appliqué hors cycle le 2026-09-14.

## Timings

*(généré par `tools/timing/report.sh --task task-308 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /develop | ok | 42 min 18 s | 28 (1 min 36 s) | 9 (10 min 10 s) | — | api-mail 24B/6T, client-mobile 0B/1T, client-blazor 3B/1T, client-angular 1B/1T |
| /start | ok | 46 s | — | — | — | — |
| /sonar | ok | 16 min 44 s | 3 (28 s) | 6 (4 min 38 s) | 2 (1 min 00 s) | 1 itération(s), api-mail 3B/6T |
| /lint-angular | ok | 1 min 28 s | — | — | — | — |
| /lint-mobile | ok | 27 s | — | — | — | — |
| /verify-visual | skipped | 9.9 s | — | — | — | aucun ecran mobile touche (diff = 1 spec) ; outillage Tools/visual-verify absent |
| /review | ok | 12 min 19 s | 5 (27 s) | 6 (3 min 20 s) | — | api-mail 3B/3T, client-blazor 1B/1T, client-mobile 1B/1T, client-angular 0B/1T |
| /tech-writer | ok | 2 min 31 s | — | — | — | — |
| **Total cycle** | | **1 h 16 min** | **36 (2 min 32 s)** | **21 (18 min 09 s)** | **2 (1 min 00 s)** | |

Autres commandes mesurées : lint ×3 (53 s)

## Develop log — implémentation terminée (2026-09-14)

### Vert sur les quatre repos

| Repo | Build | Tests | Détail |
|---|---|---|---|
| `api-mail` | ✅ | **4 500 / 0 échec** | domain 181, infrastructure 521, application 2 485, api 815, integration 498 (+16 skip pré-existants) |
| `client-blazor` | ✅ | **232 / 0 échec** | dont les 4 tests de redirection ajoutés |
| `client-mobile` | ✅ | **823 / 0 échec** | 819 → 823, les 4 tests de garde ajoutés |
| `client-angular` | ✅ | **347 / 0 échec** | 343 → 347, les 4 tests de garde ajoutés (code-only, non committé) |
| `dtos-mss` | — | — | **aucun changement de contrat** — `MailboxDto` inchangé, branche sans commit |

### Trois décisions prises pendant l'implémentation, hors périmètre écrit

**1. Le cross-check PSC/KC de task-048 est retiré — c'était forcé, pas un choix.**
`ApplyPscKcCrossCheckAsync` comparait `(mssSub, mssRpps)` du jeton Keycloak à
`(sub, SubjectNameID)` du jeton PSC. Son étape 1 exige la **complétude des trois claims**
— or ils ont disparu du realm. Avec `"Enforce": true` dans `appsettings.json`, il aurait
donc répondu **403 à toute requête authentifiée**. Sa garantie est reprise par
`MailboxCompatibility` règle 4, et *renforcée* : l'ancrage comparé vient d'une sonde
XOAUTH2 validée par l'opérateur, là où les claims étaient auto-déclarés par le jeton même
qu'on cherchait à vérifier. `PscIdentityOptions` part avec lui — un drapeau de
configuration qui ne gouverne plus rien et dont le commentaire décrit un mécanisme retiré
est pire qu'absent.

**2. Le journal de décision de routage (EventId 3724) est déplacé après la résolution de
la boîte.** Il était émis avant, là où l'adresse venait du claim `mssEmail`. Ce claim
disparu, la ligne aurait affiché `<none>` à **chaque** requête pour les deux champs qui
font tout son intérêt — l'adresse et le nom de base. Sa propre documentation exige qu'il
reflète « the values actually used downstream by the repository » : il fallait le
déplacer, pas le laisser mentir.

**3. `AnchorPscIdentityAsync` sort aussi du contrat.** Elle n'avait **aucun appelant de
production** — seulement le contrat et un stub de test. Avec l'ancrage devenu dérivé,
laisser une opération capable d'ancrer hors du chemin de rattachement revenait à laisser
en place la faute qu'on venait de retirer.

### Deux points pour la revue humaine

- **43 fichiers dans la PR `api-mail`**, au-delà du repère « ~30 » de la règle 5. Le
  découpage n'est pas possible sans livrer un état intermédiaire incohérent :
  `validated_by_rpps NOT NULL` ne tient que si le synchroniseur a cessé de fabriquer des
  lignes sans PSC, et sortir `rpps` de `accounts` sans cette coupe laisserait l'ancrage
  sans porteur fiable.
- **Le banc de charge devra rattacher explicitement.** `TestBypassAuthenticationHandler`
  émet encore `mssEmail` / `mssSub` / `mssRpps` — claims désormais morts, laissés en
  place car inoffensifs. Mais les boîtes du banc étaient créées **par le synchroniseur** :
  un tir sur base vierge devra désormais passer par `POST /api/v1/account/mailboxes`.
  À traiter dans le harnais (`Tools/`), hors de cette US.

### Passe qualité `/simplify` (§Q)

Appliquée à `api-mail` (seul repo au diff non trivial) : retrait de
`WriteIdentityCheckFailedAsync`, devenue sans appelant avec le cross-check, et de l'import
`Microsoft.Extensions.Options` devenu inutile. Re-validation build + tests → verte.
`client-blazor` et `client-mobile` : diff limité à un fichier de test chacun, aucun
cleanup à appliquer. `dtos-mss` : porteur de contrat, jamais éligible.

## Sonar log — 2026-09-14

**Quality Gate : ✅ OK** (les cinq conditions du new-code passent).

| KPI | Baseline (analyse du 2026-09-13) | Final (task-308) | Δ |
|---|---|---|---|
| Quality Gate | — | **OK** | — |
| Bugs | 0 | **0** | = |
| Vulnérabilités | 0 | **0** | = |
| Code smells | 233 | **231** | **−2** |
| Couverture | 87,3 % | **87,4 %** | **+0,1** |
| Couverture *new code* | — | **83,5 %** (seuil 80) | ✅ |
| Duplication | 0,3 % | 0,5 % | +0,2 |
| Reliability / Security / Maintainability | A / A / A | **A / A / A** | = |
| Hotspots de sécurité | — | 3 (`TO_REVIEW`, pré-existants) | = |
| ncloc | 44 388 | 44 447 | +59 |

**1 itération.** Un seul finding du new-code appartenait à ce diff :
`csharpsquid:S1144` sur `RegistryMetrics.RegistryMeter`, devenu un champ privé inutilisé
après le retrait des deux compteurs de migration des claims hérités. Corrigé en supprimant
la classe **et** son `AddMeter` : un meter exporté sans aucun instrument ne remonte rien
tout en laissant croire qu'il surveille quelque chose.

**Les 37 findings restants sont acceptés** — best-effort assumé, aucun n'appartient au
diff de cette US :
- 30 `external_roslyn` en **INFO** (CA1068, CA1816, xUnit2033, AV0011) ;
- 2 `S1144` et 2 `S3925` sur `BaseRepository` et `TenantRegistryExceptions`, code
  pré-existant que cette US ne touche pas ;
- 2 `S3604` sur les services d'audit, idem ;
- 1 `S3776` — **liste noire** (`agents/sonar-blacklist.yml`), traité par la commande
  dédiée `/sonar-s3776`, hors chaîne autonome.

### Deux écarts d'outillage rencontrés

- **SonarQube était arrêté** (conteneur sorti depuis 2 h). Redémarré
  (`docker start sonarqube_db sonarqube`), opérationnel en ~3 min.
- **Le port publié est 9000, pas 9001.** `agents/sonar.md` affirme 9001 dans un encadré
  qui raconte précisément l'histoire d'une valeur corrigée deux fois. Mesuré ce jour :
  `0.0.0.0:9000->9000/tcp`, et `curl` sur 9001 ne répond pas. Le conteneur a dû être
  recréé depuis. **La consigne de l'encadré reste la bonne — mesurer, pas réécrire de
  mémoire** ; c'est sa valeur qui est périmée.

### Un flaky confirmé comme tel

`ImapServiceIntegrationTests.GetEmailAsync_WithFullContent_ShouldReturnCompleteEmailAsync`
a échoué une fois puis repassé au rejeu **sans aucune modification**. Même famille que les
flakies GreenMail identifiés depuis task-297 ; hors du diff de cette US.

## Lint log — client-angular, 2026-09-14

**Vert dès la baseline. 0 itération consommée sur les 5 autorisées.**

```
npx nx affected -t lint --base=origin/next --head=HEAD --parallel=3 --projects=tag:scope:mss
→ Successfully ran target lint for 11 projects
→ 0 error
```

Seuls des **warnings** subsistent (`max-lines`, `jsdoc/require-example`), tous
pré-existants et hors du diff de cette US. La règle de la chaîne porte sur les
**errors** : rien à corriger, ni par l'auto-fixer ni à la main.

**Le seul fichier Angular de cette US est un `.spec.ts`** — et les specs sont
**exclus** de la configuration ESLint de ce workspace (`File ignored because of a
matching ignore pattern`). Le diff Angular n'était donc, par construction, pas
linatble.

**Aucune entrée ajoutée à `conventions/angular.md`** : ce fichier n'enregistre que les
règles corrigées **manuellement**, et aucune ne l'a été.

**Aucune opération git** — mode code-only. `git fetch origin next` (lecture seule, tolérée
par le playbook pour fiabiliser la référence de comparaison Nx) est la seule commande git
exécutée. Le correctif du spec, comme le correctif NG0200 appliqué hors cycle, reste
non committé : branche, commit, push TFS et ouverture de PR appartiennent à l'humain.

## Lint mobile log — client-mobile, 2026-09-14

**Vert dès la baseline. 0 itération consommée sur les 5 autorisées.**

```
npm run lint  (ng lint)
→ All files pass linting.
→ 0 error, 0 warning
```

Le diff mobile de cette US ne contient qu'un fichier — `mailbox.guard.spec.ts` — et il
passe le lint tel quel. Ni auto-fixer ni correction manuelle n'ont été nécessaires,
**aucun commit de lint** n'a donc été produit : le seul commit de ce repo reste celui de
`/develop` (`7889060`), déjà poussé.

**Aucune entrée ajoutée à `conventions/angular.md`** — ce fichier n'enregistre que les
règles corrigées **manuellement**, et aucune ne l'a été.

## Visual verify log — 2026-09-14

**Skip propre — aucun écran à vérifier.**

Le diff `client-mobile` de cette US se réduit à **un fichier de test**
(`src/app/core/auth/mailbox.guard.spec.ts`) : aucun template, aucun style, aucune page.
La task ne porte donc **aucun `## Stitch design log`**, ce qui est la condition de skip
du playbook.

Constat secondaire, déjà relevé sur task-304 : **`Tools/visual-verify/` n'existe pas sur
ce poste**. L'étape aurait skippé en best-effort de toute façon. À traiter hors de cette
US — ici, le skip est légitime sur son premier critère, pas sur celui-là.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/238 — label **`awaiting-human-merge`**
- `client-blazor` : https://github.com/codengine-technologies/HealthPlatform.Client/pull/75 — label **`awaiting-human-merge`**
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/71 — label **`awaiting-human-merge`**
- `dtos-mss` : **aucune PR** — branche créée par auto-inclusion, **zéro commit**. Cette US ne
  change aucun contrat : `MailboxDto` est inchangé, les colonnes déplacées ne traversent pas
  la frontière HTTP.
- `client-angular` : **code-only** — l'humain gère commit/push TFS et l'ouverture de la PR.
  Branche au moment du cycle : `feature/nova-rewriting-mss-tenant`. Fichiers :
  - `front/libs/mss/src/core/guards/mailbox.guard.spec.ts` *(nouveau — les 4 tests de garde)*
  - `front/libs/mss/src/core/stores/mailbox-session.store.ts` *(correctif NG0200 appliqué hors
    cycle le 2026-09-14 — cycle d'injection `MSS_USER_EMAIL` → `MailboxSessionStore` →
    `MSS_RESETTABLE_STORES` → `MailEventsStreamService` ; indépendant de cette US)*
  - les deux `environments/environment.ts` sont des modifications locales de l'humain,
    antérieures au cycle.

> **Règle 11 — US complète.** Les trois PRs portent `awaiting-human-merge` : le changement de
> comportement (api-mail) et sa preuve côté front arrivent ensemble, la US est testable de bout
> en bout. Ordre de merge : **`api-mail` #238 d'abord** (il porte la migration), puis les deux
> fronts, dans n'importe quel ordre.

## Code Review Summary

**APPROVED** — 0 blocage. **Trois défauts trouvés et corrigés pendant la revue**, chacun avec
son commit :

| Zone | Verdict |
|---|---|
| `RegistryAccount` / `PscIdentity` | ✅ ancrage dérivé, `Matches` réutilisé plutôt que dupliqué ; le détachement ne désancre pas, et c'est testé |
| `MailboxCompatibility` | ✅ règle 2 **gagne** en portée : elle compare désormais les rattachements entre eux. Matrice de 14 tests verte, assertions inchangées |
| Migration `TenantDb` | ✅ nouvelle (règle 7c) ; ordre report → `NOT NULL` → drop non inversable ; `Down()` honnête sur ce qu'il ne restaure pas ; commentaires de colonne en base |
| `PostgresTenantRegistryClient` | ⚠️ **réserve** : `LoadAnchorAsync` ajoute une requête par requête authentifiée (indexée, ≤ 1 ligne). À mesurer au banc |
| `AttachMailboxAsync` | ❌→✅ **corrigé** : filtre sur `validated_by_rpps` sans index → `ix_mss_accounts_validated_by_rpps` ajouté (commit `5818083`) |
| Flux SSE | ❌→✅ **corrigé** : « JWT lacks the mssEmail claim » là où il manque une boîte ouverte — un praticien en onboarding y tombe légitimement (commit `b62eabd`) |
| `RegistryMetrics` | ❌→✅ **corrigé** : meter vide après retrait des compteurs, S1144 (commit `5afd3d9`) |
| Middleware | ✅ cross-check retiré à raison (403 systématique sinon) ; journal 3724 déplacé pour ne plus mentir |
| Sécurité / données de santé | ✅ aucune adresse ni jeton dans les nouveaux journaux ; `email`/`username` dénormalisés documentés comme non autoritaires, jamais joints |
| Tests | ✅ le piège `MapInboundClaims` couvert des **deux** côtés — la moitié testée est précisément ce qui a laissé survivre `KcSub=<none>` |

### Réserves assumées (non bloquantes)

- **`LoadAnchorAsync` sur le chemin chaud** — une requête indexée de plus par requête
  authentifiée. À confirmer au banc avant la prochaine campagne de capacité.
- **48 fichiers dans la PR `api-mail`**, au-delà du repère « ~30 » de la règle 5. Indivisible
  sans état intermédiaire incohérent.
- **Le banc de charge devra rattacher explicitement** — ses boîtes étaient créées par le
  synchroniseur. À traiter dans le harnais, hors US.
- **`mss_registry` local a été vidé** par la suite d'intégration pendant le cycle : les lignes
  du praticien de test observées en début de session n'existent plus. La base se recrée au
  prochain démarrage de l'app, avec la nouvelle migration. Sans conséquence ici — l'humain
  cherchait précisément un registre vide pour voir l'onboarding.
- **Flaky confirmé** : `ImapServiceIntegrationTests.GetEmailAsync_WithFullContent` a échoué une
  fois puis repassé au rejeu sans modification. Même famille que les flakies GreenMail
  identifiés depuis task-297.

## Design system — écrans de rattachement (client-angular, 2026-09-14)

**Constat humain après le premier test réel** : les écrans du parcours de rattachement
n'utilisaient **aucun** composant du design system. Vérifié — `grep '@weda/design-system'`
rendait **0** sur les cinq fichiers concernés, alors que le reste du module MSS
(`contacts`, `dashboard`, `layout`, `mail/*`) s'en sert partout. Livrés par task-304 en
HTML brut : `<input>`, `<button>`, `<label>`, styles maison.

### Ce qui a été converti

| Composant | Avant | Après |
|---|---|---|
| `ui/attach-mailbox-form` | `<input type="email">`, `<input type="checkbox">`, `<button>` | `ds-input` (label + hint + type email), `ds-checkbox`, `ds-button` (icône, état `loading`) |
| `features/mailbox-onboarding` | `<h2>`, `<p>`, deux `<button>` | `ds-card` / `ds-card-title` / `ds-card-content` / `ds-card-footer`, `ds-button`, `ds-icon` |
| `features/mailbox-psc-required` | idem | idem + icône `lock` sur le titre |
| `features/mailbox-select` | `<ul>`, `<input type="checkbox">`, deux `<button>` | `ds-card`, `ds-checkbox`, `ds-button` |
| `features/mailbox-management` | liste, pastilles, 3 boutons par ligne, confirmation | `ds-card` (dont la confirmation destructive), `ds-checkbox`, `ds-button` `size="small"`, `ds-icon` sur les pastilles |

**Tous les `data-testid` sont conservés à l'identique** — c'est le contrat des tests à
venir, et aucun de ces cinq composants n'a de spec aujourd'hui.

### Trois choses apprises en chemin

**1. `--ds-spacing-md` et `--ds-spacing-sm` n'existent pas.** L'échelle du design system
est **numérique** (`--ds-spacing-2` = 8 px, `--ds-spacing-4` = 16 px). Ces deux noms sont
pourtant employés dans six déclarations existantes de `libs/mss` : elles retombent
silencieusement sur leur valeur de repli. Les nouveaux styles utilisent les vrais tokens,
et un encadré dans `attach-mailbox-form.component.scss` dit de ne pas propager l'erreur.
La couleur sémantique est `--ds-color-error-*`, pas `--ds-color-danger-*`.

**2. `ds-checkbox` émet un booléen, `<input>` émettait un `Event`.** Les deux
gestionnaires (`onAlwaysOpenChange`, `onIncludeDetachedChange`) sondaient
`event.target.checked` ; leur signature suit désormais l'émetteur. Garder `Event`
obligerait à fabriquer un faux événement pour tester une case à cocher.

**3. `MssMailboxPscRequiredComponent` n'avait aucun tableau `imports:`** — il n'en avait
pas besoin, son template n'utilisait aucun composant. Il en a un maintenant.

### L'erreur du formulaire reste un bandeau, pas un message de champ

`ds-input` sait afficher une erreur, mais la sienne est une erreur de **saisie**
(`showError = touched && invalid`). L'erreur du rattachement vient de l'opérateur MSSanté
ou du registre — « déjà rattachée », « identité non concordante », « authentification
refusée ». La placer sous le champ laisserait croire que l'adresse est mal écrite. Elle
garde donc son bandeau `role="alert"`, avec une icône `warning`.

### Validation

Build `mss-lib` ✅ (`--skip-nx-cache`) · **347 tests verts** · lint scope MSS **0 erreur**
(41 warnings pré-existants, hors diff).

**Mode code-only** : aucune opération git sur `client-angular`. Les 15 fichiers modifiés
attendent ton commit/push TFS.

### Récidive lint consignée

`jsdoc/require-param`, 2 erreurs — sur des méthodes dont le JSDoc **existait déjà** : en
changeant leur signature, le bloc a été laissé tel quel. `conventions/angular.md` passe à
**Occurrences : 2** avec la leçon : *modifier une signature, c'est modifier son JSDoc* —
le lint ne distingue pas un bloc absent d'un bloc périmé.

> **Les deux autres fronts ne sont pas traités.** `client-blazor` et `client-mobile` ont
> leurs propres écrans de rattachement, non audités ici. À vérifier séparément — cette
> passe ne couvre que `client-angular`, le front sur lequel le constat a été fait.
