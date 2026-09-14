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
