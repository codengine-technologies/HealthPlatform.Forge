# todo-task-404 — Une base par boîte

**Repos**: api-mail, client-mobile, client-angular
**Dependencies**: task-403 (le verrou d'accès doit précéder le partage)
**Epic**: E020

> **Cadre** : CLAUDE.md règle 14, réécrite le 2026-10-28 — « une boîte = une base ». Analyse
> d'origine : le nom `u_{rpps}_{slug}_{hash(adresse)}` (`UserContextInfo.BuildUserDatabaseName`)
> donne au délégataire qui ouvre la boîte de son délégant **une seconde base**, copie complète des
> données de santé, qui survit à la révocation et diverge de l'original.
>
> **Repos clients** : aucun contrat ni écran ne change. `client-mobile` et `client-angular` sont
> listés **pour le scénario E2E-SHARED-001 seulement** (règle 1c).
>
> **Aucune reprise** (humain, 2026-10-28) : rien n'est en production. Le registre et les bases
> praticien de dev sont supprimés au déploiement.

## Ce qui est établi

- **Nommage** : `u_{rpps}_{slug}_{hash}` où le hash ne porte que l'adresse — le RPPS est le seul
  discriminant entre deux personnes sur une même boîte. Le nom est calculé une fois au rattachement
  (`MailboxManagementService.cs:108`, `UserContextInfo.ProposeDatabaseName`) puis enregistré dans
  `mss_accounts.database_name` ; les requêtes relisent le nom enregistré.
- **Registre** : clé unique `(account_id, mailbox_address)` ; deux comptes peuvent rattacher la même
  adresse, chacun avec son nom de base.
- **Personne dans la base** : `Users` est indexé par `UserContextInfo.Email`, c'est-à-dire l'adresse
  de la **boîte** (`BaseRepository.GetCurrentUserIdAsync`, `:150-199`). Filtrés par `UserId` :
  `UserSettings`, `MailSignatures`, `MailTemplates`, `Contacts` (`ContactRepository`),
  `BiologyAck` (`BiologyAckRepository:52,171,302`), `PendingActions`.
- **Redis** : `user:id:{email}` (`BaseRepository.cs:135`) n'inclut **pas** la base — sur deux bases
  d'une même adresse, la seconde personne relit l'identifiant de la première. Les autres clés
  (`RedisKeys` : contacts, métadonnées, UIDs, `background-sync`, brouillons) sont indexées par
  adresse, donc déjà au niveau de la boîte.
- **Code du banc et tests qui fixent le format** : `E2eReset.cs:36-45`, `E2eSeed.cs:93`,
  `LoadTestRegistryProvisioner.cs:165`, `UserContextInfoDatabaseNameCoverageTests`,
  `E2eResetTests`, `LoadTestRegistryProvisionerTests`, `UserContextEnricherMiddlewareTests`,
  intégrations `E2eRegistryProvisioning`, `LoadTestBenchProvisioning`, `AuditJournal`,
  `ProxySessionPoolKey`, `MailboxReauthentication`. Commentaires `u_{rpps}_…` : `AppHost.cs:457`,
  `pgbouncer.ini:23`, `UserContextEnricherMiddleware.cs:100,774`, `RequestHelper.cs:85`.

## Objective

Toutes les personnes rattachées à une adresse travaillent dans **la même base** : ce que l'une fait
(rattachement patient, étiquette, acquittement, classement) est vu des autres. Seuls les réglages et
les signatures restent propres à chacun. La copie par personne disparaît, et avec elle le double coût
de synchronisation et d'IA.

## Règles

1. **Nom de base = fonction de l'adresse seule** : `u_{slug}_{hash(adresse)}`, sans RPPS. Calculé
   une fois, au premier rattachement de l'adresse.
2. **Une adresse, une base — garanti par la base de données.** Une table des boîtes du registre
   (adresse unique, nom de base, type d'adresse) est référencée par les rattachements ; le type
   d'adresse posé par la task-402 y migre. Deux premiers rattachements simultanés aboutissent à
   **une** base.
3. **Partage des données** :

   | À la boîte (vu de tous) | À la personne |
   |---|---|
   | messages, dossiers, documents, patients, biologie **et son état d'acquittement**, étiquettes, contacts, modèles, brouillons (déjà dans le dossier IMAP Brouillons) | réglages, signatures, **actions IMAP en attente** |

   Les actions en attente restent à la personne : elles s'exécutent **avec son jeton**, et
   l'opérateur doit voir agir la bonne personne (règle 14).
4. **La personne dans la base** est identifiée par son compte (`sub` Keycloak, présent en ligne
   comme hors ligne), plus par l'adresse de la boîte. RPPS et nom d'affichage : task-405.
5. **Redis** : la clé de l'identifiant de la personne porte la base **et** la personne. Les clés
   indexées par adresse restent au niveau de la boîte.
6. **Consommateurs du bus et tâches de fond** : sans personne, ils n'écrivent **aucune** donnée
   personnelle (actes système, règle 14).
7. **Aucune compatibilité** : pas de repli sur l'ancien nom, pas d'ancienne forme dans les resets.

## Definition of Done

- [ ] Build passes (0 errors) sur `api-mail`, `client-mobile`, `client-angular` (code-only)
- [ ] Tests pass (0 failures) sur chaque repo listé
- [ ] Migration du registre (table des boîtes, référence depuis le rattachement) auditée (règle 7c)
- [ ] Migration de la base praticien (clé personne, filtres boîte / personne) auditée (règle 7c)
- [ ] Unit tests du nommage (sans RPPS, stabilité, longueur ≤ 63) et de la clé Redis de la personne
- [ ] Test d'intégration de bout en bout : deux comptes rattachent la même adresse → **une seule**
      base au registre ; deux rattachements simultanés → une seule base — vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout : un patient rattaché, une étiquette posée et un résultat
      acquitté par le titulaire sont lus dans la réponse réelle du délégataire — vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout : contacts et modèles créés par l'un sont lus par l'autre —
      vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout : réglages et signature du délégataire **absents** de la
      réponse du titulaire, et inversement — vu rouge (règle 1b)
- [ ] Test d'intégration : une action en attente du délégataire s'exécute avec **son** identité —
      vu rouge (règle 1b)
- [ ] **Banc** : `E2eReset` et `E2eSeed` sur les nouveaux noms (seconde personne au seed),
      `LoadTestRegistryProvisioner` aligné, tests qui fixent le format corrigés, commentaires
      `u_{rpps}_…` mis à jour (liste dans « Ce qui est établi »)
- [ ] Scénario E2E-SHARED-001 (v1 : le titulaire rattache un patient, le délégataire le voit ; le
      délégataire change sa signature, celle du titulaire est intacte) ajouté dans
      Api/Mail/e2e/scenarios.yml, et implémenté dans chaque client où il est requis (mobile, angular)
- [ ] Aucune donnée de santé en clair dans les logs (INS, NIR, contenu CDA, contenu MSSanté)

## Manual Test Plan

- **Avant tout test** : registre et bases praticien de dev supprimés (local, e2e, banc de charge ;
  le cluster weda-dev est appliqué par l'humain).
- Backend e2e : `cd Api/Mail && dotnet run --project src/AppHost` (profil `e2e`) ; mobile
  `cd Client/Mobile && npm start` ; weda2 via le faux hôte.
- Le titulaire rattache un patient à un document, pose une étiquette, acquitte un résultat de
  biologie → le délégataire voit les trois.
- Le délégataire crée un contact et un modèle → le titulaire les voit. Il change sa signature →
  celle du titulaire ne bouge pas.
- `psql -c '\l'` : **une** base `u_…` pour `boite-praticien`.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — organisation du stockage, sans exigence DSR publiée
- **Exigences DSR honorées** : non applicable
- **INS** : inchangé — les patients restent ceux de la boîte, sans duplication
- **Authentification PS** : inchangée (PSC / e-CPS ; verrou de la task-403)
- **Habilitations** : inchangées (rôle de la task-402, verdict de la task-403)
- **Interop CI-SIS** : inchangé — IHE-XDM, CDA r2 via `interop-cda`, HPRIM
- **Tracé PGSSI-S** : inchangé ici ; l'imputation complète vient avec la task-405
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé — effet positif : plus de copie des données de santé par personne
- **AIPD / impact RGPD** : à mettre à jour — une base par boîte, partagée entre titulaire,
  délégataires et membres

## Branches

- `client-angular` (code-only) : la forge écrit sur la branche courante de `Client/Angular/` ;
  l'humain gère branche, commit, push et PR TFS
