# todo-task-074.md — Perf caching applicatif : settings utilisateur, autoconfig MSSanté, référentiels

**Repos**: api-mail
**Dependencies**: (aucune)
**Epic**: E011

> US mono-repo justifiée : ajout de caches applicatifs côté backend. Aucun
> changement de contrat ni d'UI.

## Objective

Mettre en cache les données stables relues aujourd'hui à chaque opération :
les settings utilisateur sont relus en base à **chaque** connexion IMAP/SMTP et
à chaque notification, l'autoconfig MSSanté (XML distant, timeout 5 s) est
re-téléchargée sans cache, et la catégorisation LOINC des documents médicaux
est recalculée pour chaque document de chaque listing.

## Findings adressés (audit perf 2026-06-10)

| # | Localisation | Problème | Impact |
|---|---|---|---|
| 1 | `src/Application/Services/Implementation/ImapConnectionService.cs:57`, `SmtpConnectionFactory.cs:35`, `NewMailNotifier.cs:62` | `GetSettingsAsync()` → requête DB à chaque connexion/envoi/notification, pour des settings stables | Moyen-Élevé |
| 2 | `src/Application/Services/Implementation/AutoconfigService.cs:104` | Fetch HTTP de l'autoconfig (timeout 5 s) sans cache, alors que la config d'un domaine MSSanté est stable | Moyen |
| 3 | `src/Infrastructure/Repository/MailRepository.cs:785,1345,2038` + `PatientRepository.cs:216,957` | `CDADocumentHelper.GetDocumentCategory(loinc)` recalculé par document, sans mémoïsation | Moyen |
| 4 | `src/Infrastructure/Repository/PatientRepository.cs:26-51` | `GetByInsAsync` sans cache malgré des appels répétés pendant l'enrichissement | Moyen |
| 5 | `src/Application/Services/Implementation/FolderCacheManager.cs:16-38` | TTL fixe 5-10 min sans invalidation événementielle (la sync sait quand les dossiers changent) | Moyen |

## Comportement attendu

- Settings utilisateur : cache (mémoire ou Redis existant) avec TTL court
  (~5 min) **et invalidation explicite à l'écriture des settings** — un
  changement de paramètre par l'utilisateur est pris en compte immédiatement.
- Autoconfig MSSanté : cache Redis TTL 24 h par domaine.
- Catégorie de document LOINC : mémoïsation statique (dictionnaire immuable) —
  le référentiel est fixe au runtime.
- Patient par INS : cache court avec invalidation à l'écriture du patient
  (l'INS ne doit jamais apparaître en clair dans une clé de cache loggée — clé
  hashée si la clé peut fuiter dans des logs/outils).
- Dossiers : invalidation push depuis la sync (en plus du TTL filet de
  sécurité).

## Definition of Done

- [ ] Build passes : `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` (0 erreur)
- [ ] Tests pass : `dotnet test HealthPlatform.Api.Mail.sln` (0 échec)
- [ ] `GetSettingsAsync` n'exécute plus une requête DB par connexion (cache + invalidation à l'écriture, test le prouvant)
- [ ] Autoconfig : 2 connexions successives du même domaine → 1 seul fetch HTTP (test avec HttpClient mocké)
- [ ] `GetDocumentCategory` mémoïsé (test : 1000 appels même LOINC → 1 calcul)
- [ ] Cache patient par INS avec invalidation à l'écriture ; aucune clé de cache contenant l'INS en clair dans les logs
- [ ] Invalidation push du cache dossiers branchée sur la sync
- [ ] Unit tests : >= 1 test par cache ajouté (hit, miss, invalidation)
- [ ] Integration test : modification d'un setting utilisateur → la connexion suivante utilise la nouvelle valeur (pipeline DI complet)
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

- Lancer l'API : `cd Api/Mail && docker-compose up -d && dotnet run --project src/Api`
- Se connecter, naviguer entre 3 dossiers, revenir : les logs serveur montrent
  que les settings ne sont plus relus en base à chaque action.
- Modifier un paramètre utilisateur (ex. signature) puis envoyer un mail :
  la nouvelle valeur est appliquée immédiatement (invalidation OK).
- Redémarrer la sync d'un dossier : la liste des dossiers se rafraîchit côté
  client sans attendre l'expiration du TTL.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (LPS MSSanté)
- **Vague Ségur** : hors Ségur — optimisation technique
- **Exigences DSR honorées** : non applicable
- **INS** : l'INS peut servir de clé de cache — exigence : jamais en clair dans les logs ni dans un outil d'inspection de cache (clé hashée) ; statut INS et traitements inchangés
- **Authentification PS** : inchangée
- **Habilitations** : non applicable
- **Interop CI-SIS** : non applicable — la catégorisation LOINC est mémoïsée à comportement identique
- **Tracé PGSSI-S** : inchangé
- **Consentement patient** : non applicable
- **Référentiels métier** : LOINC (mémoïsation de la table de catégorisation, valeurs inchangées)
- **Hébergement HDS** : oui — les caches (Redis/mémoire) restent dans l'environnement HDS existant
- **AIPD / impact RGPD** : inchangé — durée de vie des caches courte et bornée, pas de nouveau stockage durable

## Branches
- `api-mail` (pushed) : feat/task-074-caching-settings-referentiels
- `dtos-mss` (pushed, auto-incluse) : feat/task-074-caching-settings-referentiels — sera supprimée sans PR si aucun changement de contrat

## Develop log (2026-06-10)

**Commit (api-mail, `feat/task-074-caching-settings-referentiels`)** : `d0bac8f`

**Findings traités** :
1. ✅ Settings : cache 5 min (`usersettings:{userId}`, Guid non sensible) + invalidation explicite dans `SaveSettingsAsync`. Les défauts (aucune ligne) ne sont pas cachés. `MaxAttachmentSizeBytes` réappliqué depuis les options après hit (config d'environnement, pas une donnée utilisateur).
2. ✅ Autoconfig : cache 24 h par domaine, résultats positifs uniquement. Test : 2 connexions même domaine → 1 fetch HTTP (handler compteur).
3. ✅ `DocumentCategoryCache` (Application) : mémoïsation `ConcurrentDictionary` au-dessus de `CDADocumentHelper` (repo interop **non touché** — scope task = api-mail). 4 call sites repositories migrés ; instances partagées en lecture seule (les appelants ne font que projeter vers DTO). Test : 1000 appels même LOINC → même instance.
4. ✅ Patient par INS : cache 5 min, clé `patient:ins:{SHA256-16octets-hex}` — INS jamais en clair (test l'assertant), négatifs non cachés (un patient créé juste après un miss est visible), invalidation à `UpdateOppositionAsync`. **Limite documentée** : les écritures patient des chemins d'ingestion (MailRepository) s'appuient sur le TTL filet de 5 min.
5. ✅ **Requalifié** : `FolderCacheManager` est du code mort — non enregistré en DI, zéro consommateur production (grep : seuls ses propres tests le référencent). Brancher une invalidation push sur un cache inactif est sans objet ; la perf GetFolders a été traitée par task-080 (LIST-STATUS). Déviation DOD documentée.

**Robustesse** : `SafeCacheExtensions` — toute panne Redis dégrade vers la source (log Debug/Warning), jamais d'échec métier. Clés santé hashées.

**Validation** : build Release 0 erreur ; suite 2707 verts / 1 flaky IMAP pré-existante. 11 nouveaux tests (3 settings dont l'intégration « save → lecture suivante voit la nouvelle valeur », 4 patient dont clé-sans-INS, 2 LOINC, 2 autoconfig).

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/97 — label `awaiting-human-merge`
- `dtos-mss` : branche `feat/task-074-caching-settings-referentiels` sans commit — pas de PR, branche à supprimer au `/merge`

## Code Review Summary

APPROVED — 0 issue bloquante.
- Settings/Autoconfig/Patient/LOINC : 4 caches avec hit/miss/invalidation testés (11 tests)
- INS jamais en clair (clé SHA-256, test dédié) ; panne Redis = dégradation vers la source
- Finding 5 requalifié : FolderCacheManager code mort (preuve grep), déviation DOD documentée
- Sonar : Quality Gate OK premier scan, 0 new-code issue

## Merged

- **Date** : 2026-06-11
- **api-mail** : PR #97 squash-mergée — commit `5da065d` sur `develop`. Conflit `PatientRepository.cs` (usings 071/074) résolu par merge `origin/develop` (`1080878`) avant le merge final.
- **dtos-mss** : aucune PR (branche sans commit) — branche remote supprimée
- **CI develop** : ✅ success — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/27372961128
- Branches locales conservées pour inspection rétroactive (convention /merge)
