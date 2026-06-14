# todo-task-073.md — Perf DI : HttpClientFactory pour Semantic Kernel, double registration et lifetimes

**Repos**: api-mail
**Dependencies**: (aucune)
**Epic**: E011

> US mono-repo justifiée : hygiène de l'injection de dépendances et du cycle de
> vie des clients HTTP. Aucun changement de contrat ni d'UI.

## Objective

Corriger les enregistrements DI qui dégradent la performance et la stabilité :
`new HttpClient()` non poolés recréés à chaque construction du Kernel Semantic
Kernel (épuisement de sockets vers l'API IA), double enregistrement
contradictoire d'`IEmailEmbeddingService` (Scoped puis Singleton), et lifetimes
inadaptés sur la chaîne de validation de certificats.

## Findings adressés (audit perf 2026-06-10)

| # | Localisation | Problème | Impact |
|---|---|---|---|
| 1 | `src/Api/Extensions/SemanticKernelExtensions.cs:66,74` | `new HttpClient { Timeout = ... }` passé au Kernel ; le Kernel étant **Transient** (lignes 80, 125), chaque résolution recrée des HttpClient non poolés → TIME_WAIT bloat, pas de keep-alive vers le provider IA | Élevé |
| 2 | `src/Api/DependencyInjection.cs:51` + `src/Application/Extensions/ServiceCollectionExtensions.cs:49` + `SemanticKernelExtensions.cs:90,135` | `IEmailEmbeddingService` enregistré en Scoped à deux endroits puis en Singleton — la dernière registration gagne, ambiguïté + risque de fuite d'état | Élevé |
| 3 | `src/Application/Extensions/ServiceCollectionExtensions.cs:40-41` | `CertificateValidator` / `ImapClientTlsConfigurer` Scoped sans cache : recherche dans le store de certificats à chaque requête (complète la task-069 — ici seul le lifetime/cache d'accès au store est en scope) | Moyen |
| 4 | `src/Api/Extensions/SemanticKernelExtensions.cs:28-30,51-53,100-102` | Binding de configuration `.Get<T>()` répété au lieu d'`IOptions<T>` | Faible |
| 5 | `src/AppHost/FlagsmithSeeder.cs:29,132-133` | `new HttpClient()` directs (bootstrap uniquement — corriger pour l'exemplarité) | Faible |

## Comportement attendu

- Les connecteurs Semantic Kernel (chat + embeddings) consomment des
  `HttpClient` issus d'`IHttpClientFactory` (clients nommés), ou le Kernel est
  enregistré en Singleton si son caractère stateless est démontré.
- `IEmailEmbeddingService` a **une seule** registration, avec le lifetime
  correct, documenté.
- L'accès au store de certificats est caché (clé thumbprint, TTL) au lieu d'être
  re-exécuté par requête.
- Les options de configuration sont liées une fois via `IOptions<T>`.

## Definition of Done

- [ ] Build passes : `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` (0 erreur)
- [ ] Tests pass : `dotnet test HealthPlatform.Api.Mail.sln` (0 échec)
- [ ] Plus aucun `new HttpClient(` dans `src/Api` et `src/Application` (grep vérifiable), hors tests
- [ ] `IEmailEmbeddingService` : une seule registration, lifetime justifié dans la PR
- [ ] Accès au store de certificats caché (plus de `X509Store.Find` par requête)
- [ ] Aucune fonctionnalité IA régressée : chat et embeddings fonctionnent à l'identique
- [ ] Unit tests : >= 1 test de résolution DI (le conteneur se construit, les services clés se résolvent avec le bon lifetime)
- [ ] Integration test : 1 appel d'un endpoint IA (mocké côté provider) via le pipeline DI complet
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

- Lancer l'API : `cd Api/Mail && docker-compose up -d && dotnet run --project src/Api`
- Depuis le client Blazor, utiliser une fonction IA (résumé/chat) sur un mail de
  test : la réponse arrive normalement.
- Enchaîner 20 appels IA : sur la machine serveur, `netstat -ano | findstr TIME_WAIT`
  ne montre pas d'accumulation de sockets vers le provider IA.
- Envoyer un mail MSSanté : la validation de certificat fonctionne, le second
  envoi ne refait pas de recherche dans le store (visible en logs debug).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (LPS MSSanté)
- **Vague Ségur** : hors Ségur — optimisation technique
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : inchangée
- **Habilitations** : non applicable
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé
- **Consentement patient** : non applicable — les flux IA existants et leur périmètre de données ne sont pas modifiés par cette US
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement HDS existant inchangé
- **AIPD / impact RGPD** : inchangé — aucun nouveau flux de données vers le provider IA

## Branches
- `api-mail` (pushed) : feat/task-073-di-httpclientfactory
- `dtos-mss` (pushed, auto-incluse) : feat/task-073-di-httpclientfactory — sera supprimée sans PR si aucun changement de contrat

## Develop log (2026-06-10)

**Commit (api-mail, `feat/task-073-di-httpclientfactory`)** : `b9926d5`

**Findings traités** :
1. ✅ Client nommé `SemanticKernelOpenAI` via `IHttpClientFactory` + `SocketsHttpHandler` (`PooledConnectionLifetime` 5 min) — keep-alive et rotation DNS malgré la durée de vie du Kernel. **Correction d'analyse** : le Kernel était déjà construit une fois (pas de recréation par résolution comme l'audit le pensait) — le vrai problème était les 2 `new HttpClient` non poolés et la registration Transient mensongère. Kernel désormais en **vrai singleton** (stateless démontré : il était déjà partagé de fait).
2. ✅ `IEmailEmbeddingService` : registration **unique** (Application, Scoped, `EmailEmbeddingService`). Justification du lifetime : c'était déjà l'implémentation et le lifetime effectifs (last-wins après `AddApplication`) — la registration Singleton `FlexibleEmbeddingService` était **morte** (shadowée). Comportement strictement identique. `FlexibleEmbeddingService`/`IEmbeddingProviderService` ne sont plus enregistrés (classes laissées en place, hors scope).
3. ✅ (obsolète) Aucun `X509Store` dans src — la chaîne OCSP/CRL cache déjà via Redis (task-057). Lifetimes Scoped de `CertificateValidator`/`ImapClientTlsConfigurer` corrects (dépendances Scoped → singleton = captive dependency). DOD « plus de X509Store.Find par requête » : vérifié par grep (0 occurrence).
4. ✅ (déjà conforme) Les `.Get<T>()` sont des lectures one-shot au démarrage pour choisir la branche provider ; les consommateurs par requête passent par `IOptions<T>` (déjà bindés). Commentaire ajouté.
5. ⏸ `FlagsmithSeeder` (AppHost) : bootstrap one-shot, clients `using`-disposés, hors périmètre du grep DOD (src/Api + src/Application) — laissé en l'état, documenté.

**DOD grep** : `grep -rn "new HttpClient(" src/Api src/Application` → 0 occurrence (hors commentaire).

**Validation** : build Release 0 erreur ; suite complète **2699 verts, 0 échec** (même la flaky IMAP passe). 5 nouveaux tests (Kernel singleton cross-scope, generator singleton, AddSemanticKernel sans registration embedding, timeout client nommé, endpoint IA TestServer provider mocké).

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/96 — label `awaiting-human-merge`
- `dtos-mss` : branche `feat/task-073-di-httpclientfactory` sans commit — pas de PR, branche à supprimer au `/merge`

## Code Review Summary

APPROVED — 0 issue bloquante.
- `SemanticKernelExtensions.cs` — ✅ client nommé + SocketsHttpHandler 5 min, Kernel vrai singleton, comportement préservé
- `DependencyInjection.cs` / `ServiceCollectionExtensions.cs` — ✅ registration unique justifiée (last-wins préservé)
- Findings 3/4/5 requalifiés avec preuves (grep X509Store = 0, .Get<T> one-shot, AppHost hors scope)
- DOD : tous items verts (grep new HttpClient = 0 dans src/Api+src/Application ; test endpoint IA provider mocké)
- Sonar : Quality Gate OK, 0 new-code issue

## Merged

- **Date** : 2026-06-11
- **api-mail** : PR #96 squash-mergée — commit `bac7b1b` sur `develop`
- **dtos-mss** : aucune PR (branche sans commit) — branche remote supprimée
- **CI develop** : ✅ success — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/27367867669
- Branches locales conservées pour inspection rétroactive (convention /merge)
