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
