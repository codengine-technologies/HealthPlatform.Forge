# todo-task-426.md — Le registre n'est plus relu à chaque requête : le cache du compte sert, et la base commune respire

**Repos**: api-mail
**Dependencies**: — (aucune ; task-422 a fourni la mesure)
**Epic**: E015
**Single frontend**: true
**Priorité**: **2**. Le registre est la **seule base commune à tous les médecins**. Il reçoit environ 6 lectures par
requête HTTP, alors que l'essentiel devrait venir d'un cache de 10 min. Sa charge croît avec le trafic total : c'est
le point de contention qui comptera à 10 000 inscrits. Le correctif est petit et ne change aucun comportement visible.

> **Origine.** Tir court 1400 → 1996 médecins actifs du 2026-11-05 (task-422, IA simulée, pool PgBouncer à 1), finding
> **F2**. Rapport et analyse : `Docs/audits/api-mail-loadtest-journey-courte-1400-1996-task422-20261105.md`, section
> « Findings d'optimisation ».

## Ce qui est établi

| Forme `pg_stat_statements` (base `mss_registry_loadtest`) | Appels sur 39 min | Par requête HTTP | Part du temps SQL |
|---|---|---|---|
| `SELECT … FROM accounts WHERE authentication_subject = $1` | 2 226 391 | 2,96 | 3,5 % |
| `SELECT validated_by_psc_subject, validated_by_rpps FROM mss_accounts WHERE account_id = $1 …` (ancre PSC) | 2 226 391 | 2,96 | 4,1 % |
| `SELECT … FROM mss_accounts JOIN accounts …` (rattachements) | 751 209 | 1,00 | 1,7 % |
| `DISCARD ALL` (registre surtout) | 5 351 884 | 7,12 | 3,3 % |

- **Cause, établie dans le code.** `UserContextEnricherMiddleware` appelle `TenantRegistrySynchronizer.SynchroniseAsync`
  à **chaque** requête authentifiée (task-299, « meilleur effort »). Celui-ci appelle
  `PostgresTenantRegistryClient.EnsureAccountAsync`, qui :
  - lit la ligne du compte, puis la relit (« relecture systématique » contre la course d'insertion) ;
  - lit l'ancre PSC ;
  - puis appelle **`InvalidateAccountAsync` sans condition**, même quand rien n'a été écrit.
- `GetAccountAsync`, appelé ensuite par la sélection de boîte, trouve donc toujours le cache vide (`registry:account:{sub}`,
  `TenantRegistryOptions.CacheLifetime` = 10 min). Il relit à son tour le compte et l'ancre.
- **`DISCARD ALL`** : le registre se connecte **en direct**, sans PgBouncer (`AppHost.cs`,
  `TenantRegistry__ConnectionString` = `postgresDirectConnectionString`). Npgsql réinitialise donc la session à chaque
  retour d'une connexion au pool. Moins de lectures, c'est moins de retours au pool. `No Reset On Close` n'est posé
  aujourd'hui que sur le chemin des bases praticien, derrière PgBouncer.

## Objective

À rythme constant, le registre ne reçoit plus que les lectures qui apportent une information nouvelle. Le compte
d'une personne déjà connue et inchangée vient du cache.

Règles :
- **N'invalider que ce qui a changé.** `EnsureAccountAsync` n'invalide le cache du compte que s'il a **écrit** :
  création du compte, ou projection Keycloak (email, nom d'utilisateur) modifiée. Sinon, il ne touche pas au cache.
- **Servir `EnsureAccountAsync` depuis le cache** quand le compte y est déjà et que la projection Keycloak du jeton est
  identique : aucune lecture de la base dans ce cas.
- **Ce qui doit rester exact, et l'est par d'autres invalidations** : l'ancre PSC, le rattachement et le détachement
  d'une boîte, l'issue d'authentification (`MarkAuthenticationOutcomeAsync`). Ces chemins invalident déjà, et ne
  changent pas.
- **Sécurité inchangée (règle 14).** Le compte en cache ne porte aucun verdict d'accès. Le verrou de l'opérateur
  (`MailboxAccessGate`) et ses fenêtres ne passent pas par ce cache. Une révocation ferme toujours l'accès au même
  instant qu'aujourd'hui.
- **Panne du registre (task-423)** : inchangée. Une lecture qui atteint la base et échoue remonte toujours en
  `TenantRegistryUnavailableException`. Un compte servi par le cache ne lit pas la base, et c'est voulu.
- **`DISCARD ALL` sur le registre** : décidé par la mesure. Si le registre n'utilise aucun état de session (`SET`,
  tables temporaires, requêtes préparées nommées), poser `No Reset On Close=true` sur sa chaîne. Sinon, le dire et
  laisser.

### Hors périmètre

- La recherche plein texte : task-427.
- Le dimensionnement de Postgres : recommandation de task-422, dans `DevOps`.
- Aucun client, aucun contrat : comportement HTTP strictement identique.

## Definition of Done

- [ ] Build passes (0 errors) : `HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) : `HealthPlatform.Api.Mail.sln`
- [ ] **Test d'intégration de bout en bout (règle 1b)** : deux requêtes authentifiées successives du même médecin sur
      une route de messagerie, à travers le vrai middleware, le vrai `PostgresTenantRegistryClient`, le vrai cache et la
      vraie base du registre. La seconde ne lit **ni** `accounts` **ni** l'ancre dans la base : compteur de requêtes du
      registre (intercepteur EF ou `pg_stat_statements` de la base du fixture) lu dans le test. Les deux réponses sont
      200 avec la même boîte. Vu rouge sur le code d'avant (lectures > 0) ou par mutation (invalidation inconditionnelle
      réinjectée)
- [ ] **Test d'intégration, la fraîcheur reste exacte** : le jeton change d'email entre deux requêtes. Le registre est
      mis à jour, le cache invalidé, et la réponse suivante sert le nouvel email
- [ ] **Test d'intégration, le rattachement reste exact** : un rattachement entre deux requêtes rend le compte ancré dès
      la requête suivante. Les invalidations existantes sont inchangées
- [ ] Tests d'intégration existants du registre et de la sélection de boîte verts sans modification de leurs assertions,
      dont task-423 (registre injoignable → 503) et task-403 (refus de l'opérateur)
- [ ] Tests unitaires : `EnsureAccountAsync` sans écriture ne touche pas au cache ; avec création ou projection modifiée,
      il invalide
- [ ] `DISCARD ALL` : décision consignée dans le `## Develop log` (état de session du registre inventorié ;
      `No Reset On Close=true` posé ou non, et pourquoi)
- [ ] **Mesure au banc** (skill `loadtest-skill`, même tir court que task-422 : `JOURNEY_STAGES="1400:18m,1996:18m"`,
      IA simulée, pool 1). Lectures du registre par requête HTTP avant et après, relevées dans `pg_stat_statements`
      (formes `accounts`, ancre PSC, `DISCARD ALL`). Cible : **au moins −50 %** sur `accounts` + ancre. Aucun p95
      d'étape dégradé de plus de 20 %, 0 erreur 5xx en régime
- [ ] Aucune donnée de santé ni identifiant de personne dans les journaux ajoutés ou modifiés

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost`, profil par défaut, une boîte rattachée.
2. Se connecter (`client-blazor` ou `client-mobile`), ouvrir l'inbox, naviguer dans 3 dossiers et 3 messages : tout
   s'affiche comme avant.
3. Changer l'email du compte dans Keycloak, se reconnecter : l'email affiché par la messagerie est le nouveau.
4. Rattacher une deuxième boîte depuis « Mes boîtes » : elle apparaît aussitôt, la sélection fonctionne.
5. Arrêter la base du registre (tableau de bord Aspire) puis ouvrir l'inbox : 503 « momentanément indisponible »
   (task-423, inchangé), ou réponse normale si le compte est déjà en cache. Jamais « messagerie non rattachée ».
6. Au banc (facultatif) : rejouer le tir court et comparer les lectures du registre par requête HTTP.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur. Capacité interne
- **Exigences DSR honorées** : non applicable. Aucun comportement visible du PS ne change
- **INS** : non applicable. Aucun trait d'identité patient n'est manipulé
- **Authentification PS** : inchangée (PSC / e-CPS). L'ancre PSC du compte reste invalidée par les mêmes chemins
  qu'aujourd'hui (rattachement, issue d'authentification)
- **Habilitations** : inchangées (règle 14). Le cache du compte ne porte aucun verdict d'accès. Le verdict de
  l'opérateur et sa fenêtre de révocation ne passent pas par lui
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé. La synchronisation reste au meilleur effort, et l'imputation des actes (règle 14) ne
  dépend pas de ce cache
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui, environnement inchangé. Le cache ne contient que des données de compte (sujet, email,
  identifiant PSC), déjà présentes dans le cache d'aujourd'hui
- **AIPD / impact RGPD** : inchangé, aucun traitement nouveau
