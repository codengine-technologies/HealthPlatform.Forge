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

## Branches

- `api-mail` (pushed) : feat/task-426-cache-du-compte-registre-invalide-a — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-426-cache-du-compte-registre-invalide-a
  - Créée depuis `origin/develop` (`b0cf4143`).

## Develop log

**Commits** (`api-mail`, poussés) : `d059deb2` (correctif + tests), `a03ccab0` (passe qualité `/simplify`).

### Cause et correctif

- `TenantRegistrySynchronizer.SynchroniseAsync` (chaque requête authentifiée) appelait `EnsureAccountAsync`, qui lisait
  le compte, le relisait, lisait l'ancre, puis **vidait le cache du compte sans condition**. La sélection de boîte, juste
  après, relisait donc le compte et l'ancre (`GetAccountAsync`), et `GetMailboxAsync` relisait encore l'ancre.
- **Synchronisation** : elle lit d'abord le compte par `GetAccountAsync` (servi par le cache). Elle n'appelle
  `EnsureAccountAsync` que si le compte est inconnu ou si le jeton apporte une projection Keycloak nouvelle
  (`RegistryAccount.ProjectionOverwrites`, la règle de task-308 : une valeur absente n'efface jamais).
- **`EnsureAccountAsync`** n'invalide plus que s'il a écrit : création (`INSERT … ON CONFLICT` qui insère une ligne) ou
  projection modifiée. `EnsureAccountRowAsync` rend désormais le drapeau « inséré ».
- **`GetMailboxAsync`** lit l'ancre PSC **dans la même requête** que le rattachement et le compte (sous-requête
  `AnchorCandidates`, même règle que `LoadAnchorAsync` : plus ancien rattachement validé, détachés compris). Elle reste
  lue en base, jamais dans le cache, pour le verdict de compatibilité (règle 14), sans aller-retour de plus.
- **Le chemin de rattachement** (`MailboxManagementService`) continue d'appeler `EnsureAccountAsync`, donc de lire le
  compte en base : il n'est pas servi par le cache.
- Invalidations inchangées : rattachement, détachement, issue d'authentification, `Touch*`. Une panne du registre
  remonte toujours en `TenantRegistryUnavailableException` (task-423) : `GetAccountAsync` lève comme `EnsureAccountAsync`.

### `DISCARD ALL` — décision : `No Reset On Close=true` posé

Inventaire de l'état de session du registre (code de `PostgresTenantRegistryClient`, `AuditTraceRepository`, migrations) :
- aucun `SET` de session (le pool d'audit ne pose que `SET LOCAL ROLE`, levé au commit) ;
- aucune table temporaire, aucun `LISTEN` ;
- aucune requête préparée persistante (`Max Auto Prepare` à 0) ;
- verrous consultatifs uniquement transactionnels (`pg_advisory_xact_lock`).

Le réglage est posé dans `TenantRegistryConnectionString.Build`, donc pour le registre **et** l'audit (test
`TenantRegistryConnectionStringTests`). Gain attendu : Postgres CPU (instruction préfixée à la suivante), pas un
aller-retour réseau. Un état de session ajouté un jour devra retirer ce réglage (remarque dans le code).

### Tests (règle 1b)

Test d'intégration de bout en bout `RegistryAccountCacheEndpointIntegrationTests` : vrai `UserContextEnricherMiddleware`,
vrai synchroniseur, vraie sélection, vrai `PostgresTenantRegistryClient` et son cache, vraie base du registre. Chaque
commande SQL est relevée par un intercepteur EF. Seul le verdict de l'opérateur est simulé.

| Comportement | Test | Preuve du rouge |
|---|---|---|
| La 2ᵉ requête du même médecin ne lit ni `accounts` ni l'ancre (deux 200, même boîte) | `TheSecondRequestOfTheSameDoctor_ReadsNeitherTheAccountNorItsAnchor` (témoin positif sur la 1ʳᵉ requête) | rouge sur le code d'avant ; M2 (synchronisation toujours en `Ensure`) ; M5 (ancre relue à part dans `GetMailboxAsync`) |
| Un email changé dans le jeton met à jour le registre, et la réponse suivante le sert | `AnEmailChangedInTheToken_UpdatesTheRegistry_AndTheNextResponseServesIt` | M3 (`ProjectionChanged` toujours faux) |
| Un rattachement entre deux requêtes ancre le compte dès la suivante | `AnAttachmentBetweenTwoRequests_AnchorsTheAccountAtTheNextRequest` | M4 (le rattachement n'invalide plus) |
| L'ancre lue avec la boîte refuse une boîte validée par un autre professionnel (403 `PSC_MISMATCH`, sans jeton PSC) | `AMailboxValidatedByAnotherProfessionalThanTheAnchor_IsRefused_FromTheAnchorReadWithTheMailbox` | M6 (ancre de la requête jointe ignorée) |

- **M6 a d'abord survécu** à 143 tests d'intégration du registre et de la sélection : aucun ne lisait l'effet de l'ancre
  lue par `GetMailboxAsync` (trou antérieur à la task, rendu visible parce que la task réécrit cette lecture). Le 4ᵉ test
  a été ajouté pendant la passe qualité, puis vu rouge par M6.
- Chaque mutation : réinjectée, test rouge constaté, source restauré **puis recompilé** (script de mutation).
- Tests unitaires : synchroniseur (compte connu inchangé → aucune écriture ; inconnu ; email changé ; jeton sans email),
  client (sans écriture → cache intact ; création et projection modifiée → invalidation), chaîne de connexion
  (`NoResetOnClose` sur les deux pools), règle de projection (`RegistryAccountProjectionTests`).
- Validation finale (après la passe qualité) : build 0 avertissement, 0 erreur. Tests : domain 210, infrastructure 705,
  api 1 361, application 4 028, intégration 1 124 (+16 ignorés), **0 échec**.
- **Flaky constaté, hors task** : `ImapServiceTests.GetFolderNotSeenAsync_HappyPath_TagsTheImapActivityWithPerCommandDurationsAsync`,
  1 échec en suite complète, vert isolé (×3) puis vert en suite rejouée. `ActivityListener` global. Consigné en mémoire.

### Passe qualité `/simplify` (4 relectures)

Appliqué : règle de projection en un seul endroit (Domain) ; règle d'ancrage en une seule source (`AnchorCandidates` +
`ToIdentity`) ; `ApplyKeycloakProjection(...) || inserted` ; lecture finale sortie du tuple ; en-tête `Client-Email` posé
par la requête de test (middleware de test retiré) ; commentaire `NoResetOnClose` précisé.

Écarté, avec raison :
- **Méthode de cache unique sur le client** (`SyncAccountAsync`) : nouveau membre d'interface et refonte des faux ; la
  version minimale (règle en Domain) supprime la duplication.
- **Cache et handler de test partagés** (5ᵉ et 6ᵉ copies) : hors du diff, à factoriser dans une task de harnais.
- **Suites proposées, hors périmètre** (mesurées faibles en régime) :
  - le compte lu deux fois par requête dans Redis (synchronisation puis sélection) : le passer de l'un à l'autre ;
  - `TouchAsync` vide le cache du compte alors qu'aucun lecteur n'utilise `LastActivityAt` : un seul `ExecuteUpdate`,
    sans invalidation ;
  - le SDK pose une expiration glissante de 30 min par défaut : chaque lecture Redis coûte un `EXPIRE` de plus ;
  - `ListMailboxesAsync` (requête sans `Client-Email`) lit encore l'ancre à part.

> **Point pour l'humain (HAG), fraîcheur de l'ancre.** `MailboxSelectionService.SelectAsync` compare le jeton PSC à
> l'ancre du compte **servi par le cache** (jusqu'à 10 min), alors qu'avant cette task le cache était vidé à chaque
> requête. C'est exact tant que l'ancre ne change qu'au rattachement (de « aucune » au premier rattachement validé), qui
> invalide le cache dans le Redis partagé. Une purge future de rattachements, qui changerait le plus ancien, devrait
> invalider aussi. Le verdict de compatibilité de `GetMailboxAsync` lit, lui, l'ancre en base.

## Mesure au banc (2026-11-06, 15:04 → 16:35)

Même tir court que la référence : `JOURNEY_STAGES="1400:18m,1996:18m"`, K = 1, IA simulée, pool PgBouncer à 1, mêmes
bases, tireur k6bench, `LATENCY_MS=96`. Proxies Toxiproxy et santé de l'API contrôlés toutes les 30 s, sans incident.

**Le tir de référence de la veille ne suffisait pas.** Comparé au tir task-427 du 2026-11-05, ce tir montrait à 1996
des p95 d'étape dégradés de 50 à 67 % (inbox, message servi base, dossier patient). Mais :
- ces requêtes sont celles des bases praticien, que task-426 ne touche pas, et elles sont appelées autant de fois ;
- leur temps de lecture disque double (98 → 182 s) ;
- les fautes majeures du cgroup Postgres montent de 0,6 à 33/s, et uniquement au palier 1996, avec RSS et cache de
  pages identiques.

Le jeu de travail a grossi : les bases ont pris 913 Mo au tir task-427, plus le tir task-424 du matin. D'où un **tir de
contrôle sur `develop`** (`b0cf4143`, sans task-426), joué juste après, dans des conditions au plus égales.
- Ce tir : `Docs/audits/api-mail-loadtest-journey-courte-1400-1996-task426-20261106.md`.
- Contrôle : `Docs/audits/api-mail-loadtest-journey-courte-1400-1996-task426-controle-develop-20261106.md`.
- Tir de la veille, pour mémoire : `Docs/audits/api-mail-loadtest-journey-courte-1400-1996-task427-20261106.md`.

**Lectures du registre par requête HTTP** (`pg_stat_statements`, base `mss_registry_loadtest`) :

| Forme | Contrôle `develop` | task-426 | Écart |
|---|---|---|---|
| `SELECT … FROM accounts` (lecture directe) | 2,97 | **0,02** | −99 % |
| Ancre PSC (requête séparée) | 2,97 | **0,01** | −99,6 % |
| **`accounts` + ancre** (critère DoD, cible −50 %) | **5,94** | **0,03** | ✅ **−99,5 %** |
| `DISCARD ALL` (registre) | 7,13 | **0** | −100 % |
| Rattachement + compte (jointure, ancre incluse depuis task-426) | 1,00 (46,6 s) | 1,00 (76,4 s) | +30 s : l'ancre jointe |
| Temps SQL du registre, toutes formes | 379 s | **125 s** | −67 % |
| Temps SQL total du tir | 27,5 min (6,1 ms/req) | **25,6 min** (5,6 ms/req) | −7 % |

**p95 d'étape contre le contrôle** (même conditions), critère « aucun p95 dégradé de plus de 20 % » :

| Étape | 1400 contrôle → task-426 | 1996 contrôle → task-426 |
|---|---|---|
| Dashboard | 548 → 540 | 672 → 661 |
| Inbox | 128 → 114 | 310 → 303 |
| Message servi base | 99 → 83 | 269 → 264 |
| Message froid (IMAP) | 527 → 514 | 616 → 584 |
| Recherche | 610 → 631 (+3 %) | 855 → 827 |
| Envoi | 944 → 931 | 1 038 → 1 024 |
| Télécharger une PJ | 130 → **378** | 743 → 792 (+7 %) |
| Marquer lu | 108 → 95 | 246 → 237 |
| Rechercher un patient | 87 → 72 | 166 → 126 |
| Page d'un dossier patient | 146 → 134 | 350 → 397 (+13 %) |
| Fiche patient complète | 680 → 618 | 1 693 → 1 774 (+5 %) |

- Les p50 sont meilleurs ou égaux sur toutes les étapes, aux deux paliers.
- **Seul écart au-delà de 20 % : le p95 du téléchargement de PJ à 1400** (130 → 378 ms), avec un p50 meilleur
  (51 → 43 ms). Ce p95 n'est pas stable d'un tir à l'autre : il valait 641 ms au tir task-427 de la veille, sur un code
  sans task-426. Le téléchargement ne lit pas le registre plus qu'une autre route. Lu comme du bruit, à confirmer par
  l'humain.
- **5xx en régime : 0** dans les deux tirs (Seq). Erreurs k6 : 0,014 % (task-426) et 0,009 % (contrôle), relais réseau.

**Conséquence pour la campagne** : à 1996, un tir de la veille n'est plus une référence opposable, parce que chaque tir
fait grossir les bases et que le cgroup Postgres (48 Go) est plein. Toute mesure comparative à ce palier exige un
contrôle joué dans la même session.

## Sonar log

- **Mode A (chaîné)**, `api-mail` sur `feat/task-426-cache-du-compte-registre-invalide-a`, **2 itérations**.
- **Itération 1** : 3 issues sur le nouveau code, toutes dans le test d'intégration `RegistryAccountCacheEndpointIntegrationTests` :
  - `SYSLIB1045` ×2 : les deux formes SQL de l'intercepteur étaient des `static readonly Regex … = new(…)`, passées en
    `[GeneratedRegex]` ;
  - `CA1859` : `RegistryCommands.Matching` déclarait `IReadOnlyList<string>` pour rendre un `List<string>`.
  - Corrigées dans `6728452c`. Les deux règles sont des **récidives** : compteurs portés à 3 et 15 dans
    `conventions/csharp.md`. Les deux consignes existaient et n'ont pas été appliquées en écrivant le test (règle d'or, point 3).
- **Itération 2** : 0 issue sur le nouveau code, Quality Gate OK, 0 hotspot.
- **Tests sous couverture** (deux passes) : domain 210, application 4 028, infrastructure 705, api 1 361, intégration
  1 124 (+16 ignorés), **0 échec**.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | = |
| Issues new code | 0 | 0 (3 à l'itération 1, corrigées) | = |
| New coverage | 95,9 % | 96,0 % | +0,1 |
| Bugs / Vulnérabilités / Code smells | 0 / 0 / 0 | 0 / 0 / 0 | = |
| Security hotspots | 0 | 0 | = |
| Coverage projet | 97,9 % | 97,9 % | = |
| Duplication | 0,4 % | 0,4 % | = |
| Ratings fiabilité / sécurité / maintenabilité | A / A / A | A / A / A | = |

## Timings

*(généré par `tools/timing/report.sh --task task-426 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 12 s | — | — | — | — |
| /develop | ok | 2 h 28 min | 4 (25 s) | 3 (11 min 14 s) | — | api-mail 4B/3T, registre accounts+ancre -99,5 %/req (A/B même session), DISCARD ALL registre supprimé |
| /sonar | ok | 26 min 43 s | 3 (1 min 41 s) | 11 (16 min 27 s) | 4 (1 min 25 s) | 2 itération(s), api-mail 3B/11T, 3 issues tests (SYSLIB1045 x2, CA1859) corrigées ; QG OK |
| **Total cycle** | | **2 h 55 min** | **7 (2 min 07 s)** | **14 (27 min 41 s)** | **4 (1 min 25 s)** | |
