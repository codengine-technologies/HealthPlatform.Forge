# todo-task-297.md — Le cache Redis stocke des corps de message de 1,5 Mo et sature seul : borner ce que l'on met en cache pour que le cache réponde

**Repos**: api-mail
**Dependencies**: —
**Epic**: E015
**Single frontend**: true
**Priorité**: **2** — le cache applicatif expire (500 ms) des milliers de fois par tir
**sans aucune autre charge Redis**, et il entraîne le spill du journal d'audit dans sa
saturation (contre-pression prématurée). Il ne fait pas perdre de donnée : il fait attendre
le médecin et fragilise un mécanisme de conformité.

> **Origine** : campagne task-292 du 2026-09-09, finding **F-292-3**, tranché par le tir A/B
> « journal désactivé » (`Docs/audits/api-mail-loadtest-journey-1000-task292-audit-off-20260909.md`).
> Le finding avait d'abord été attribué au spill d'audit (task-186/292) ; la mesure l'exonère.

## Objective

Que le cache Redis d'api-mail **reste disponible** à 1000 médecins : aucune entrée qui bloque
l'instance pendant des millisecondes, un taux de timeouts du cache proche de zéro, et un spill
d'audit qui ne subit plus la saturation du cache.

### Ce qui a été mesuré (2026-09-09, journey 1000, journal d'audit DÉSACTIVÉ)

| Grandeur | Valeur |
|---|---|
| `[Cache] ⏱️ Timeout getting key` (Warning, `ResilientCacheService`, budget 500 ms) | **6 568** sur le tir sans journal ; 21 835 / 8 778 / 10 773 sur les trois tirs avec journal |
| `[Cache] Best-effort Set failed` | 25 (287 avec journal) |
| CPU Redis (`mss-mail-redis`, mono-thread) | 0,21 cœur en moyenne, **1,15 cœur en pointe** en régime, à trois reprises de plus de 10 min |
| Slowlog Redis (ce qui bloque l'instance) | `HMSET mail:email:<adresse>:INBOX:<uid>` avec un champ `data` de **160 Ko à 1,47 Mo** (corps de message complet, JSON) en 11 à 16 ms ; `HMSET usersettings:*` ; quelques `SET mss:audit:purge:*` |
| Débit Redis | ~500 à 640 ops/s, 3,5 Mo/s en sortie |
| Mémoire Redis | 2,0 à 2,8 Go, `db0` ~14 500 clés |
| Effet croisé | avec le journal actif, 38 attentes / 18 refus de contre-pression d'audit sur `Spill buffer unreachable` alors que la borne du spill n'était qu'à 70 000 sur 120 000 : Redis ne répondait pas dans les temps |

**Mécanique établie.** Redis exécute une commande à la fois. Une entrée `mail:email:*` de 1,5 Mo
(le corps texte + HTML complet d'un message, sérialisé) coûte 15 ms à écrire et autant à lire ;
quelques-unes par seconde suffisent à faire dépasser 500 ms aux lectures de petites clés en file
derrière (`user:id:*`, `usersettings:*`, résumés). Le cache écrit ensuite le message en lecture à
la première demande (`MailController.GetEmail`, clé `RedisKeys.Mail.Email`) et l'invalidateur le
retire à chaque changement de statut : c'est un cache **chaud et volumineux** sur une instance
partagée avec le spill d'audit, les marqueurs de purge et le cache d'identité.

### Contenu attendu

1. **Borner ce qui entre en cache.** Pour la clé `mail:email:*` : ne pas mettre en cache une entrée
   dont la charge sérialisée dépasse un seuil (ordre de grandeur **64 à 128 Ko**, à fixer par la
   distribution mesurée des tailles) — la lecture retombe alors sur la base (`MailContents`), qui
   est le chemin normal depuis task-273 ; ou mettre en cache le message **sans** ses corps
   (`Body`, `BodyHtml`) et ne garder que les en-têtes/PJ/résumé si c'est ce que le chemin de
   lecture consomme en premier. Le choix revient à `/develop`, sous contrainte : **aucune
   régression fonctionnelle** de l'affichage d'un message.
2. **Compresser ou non** : si le corps reste en cache, le compresser (gzip/brotli côté service de
   cache) est une option à chiffrer ; l'objectif reste la borne de taille, pas le tassement.
3. **Mesurer la distribution des tailles** d'entrées `mail:email:*` (histogramme en Ko, p50/p95/max)
   et le nombre d'entrées refusées par la borne : compteurs exposés au collecteur
   (`mss_cache_entry_bytes`, `mss_cache_oversize_skipped_total`), au moins un test de capture.
4. **Ne pas toucher au budget de 500 ms** de `ResilientCacheService` (Sdk) : il est le symptôme, pas la cause.
5. **Re-mesurer au banc** : tir journey 1000 iso (mêmes bases), attendu : `Timeout getting key` ÷ 10
   au moins, Redis sous 0,5 cœur en pointe, plus aucun `Spill buffer unreachable` du journal d'audit
   à charge égale, et latence de l'étape « Ouvrir un message enrichi » inchangée ou meilleure.

### Hors périmètre (explicite)

- Une instance Redis dédiée au journal d'audit (task-292 a retenu une base logique distincte, `db1`) —
  non nécessaire si le cache cesse de bloquer l'instance ; à rouvrir si la mesure le contredit.
- Le cache des résumés (`mail:summary:*`) et des dossiers : petits, hors slowlog.
- Le dimensionnement de Redis (mémoire, threads I/O) : levier infra, à n'envisager qu'après la borne applicative.

## Definition of Done

- [ ] Build passes on api-mail (0 errors)
- [ ] Tests pass (0 failures)
- [ ] Test unitaire : une entrée `mail:email:*` au-dessus du seuil n'est **pas** écrite en cache et le
      compteur `oversize_skipped` s'incrémente ; une entrée sous le seuil l'est
- [ ] Test unitaire : la lecture d'un message dont l'entrée a été refusée par la borne rend le **même
      contenu** que par le cache (repli base), y compris corps HTML et pièces jointes
- [ ] Test de capture de métriques : histogramme des tailles + compteur exposés (classe sérialisée, task-291)
- [ ] Seuil configurable (`Cache:MaxEntryBytes` ou équivalent), défaut justifié par la distribution mesurée
      et documenté dans `appsettings.json`
- [ ] Aucune donnée de santé dans les logs du nouveau chemin (taille et clé seulement — la clé contient
      l'adresse MSSanté du praticien, pas de donnée patient ; ne jamais journaliser le contenu)
- [ ] Mesure au banc consignée dans le task file : tir journey 1000 iso avant/après — `Timeout getting
      key`, CPU Redis pointe, slowlog (aucune commande > 5 ms sur `mail:email:*`), `Spill buffer
      unreachable` = 0 avec journal actif, p50/p95 de l'étape 3 inchangés ou meilleurs

## Manual Test Plan

- **Fonctionnel (dev)** : `cd Api/Mail && dotnet run --project src/AppHost` ; ouvrir un message lourd
  (corps HTML long, plusieurs PJ) dans le client Blazor ; vérifier l'affichage complet ; relire le
  même message (servi par la base) ; contrôler dans Redis (`redis-cli --bigkeys`, `MEMORY USAGE
  mail:email:…`) qu'aucune entrée `mail:email:*` ne dépasse le seuil et que le compteur
  `mss_cache_oversize_skipped_total` a bougé.
- **Banc** (skill `loadtest-skill`, mode distant, bases gardées) : tir journey 1000 r2 iso au tir
  `report-journey-1000-task292-audit-off-20260909-173951.md` (référence « sans journal ») **et** au
  tir `fix2` (référence « avec journal »). Pendant le régime : `redis-cli slowlog get 20` (aucun
  `HMSET mail:email:*` > 5 ms), `docker stats` Redis (< 0,5 cœur), Seq
  `select count(*) from stream where @MessageTemplate like '%Timeout getting key%'` sur la fenêtre.
- **Ce que l'humain doit voir** : timeouts du cache ÷ 10 au moins, 0 `Spill buffer unreachable`,
  étape 3 « Ouvrir un message enrichi » au moins aussi rapide, aucun message tronqué ou vide.
- **Données de test** : boîtes `loadtest-*`, `JEUX_TESTS_FULL`. Aucune donnée de santé réelle.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors exigence DSR directe — robustesse d'un composant technique
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — le cache porte des messages MSSanté, jamais d'INS en clé ; le contenu
  (qui peut contenir des données de santé) est déjà en cache aujourd'hui ; cette US en **réduit**
  l'emprise (moins de corps de message dans Redis)
- **Authentification PS** : inchangée
- **Habilitations** : inchangées — le cache est scopé par adresse du praticien (clé)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : effet indirect positif — le spill du journal d'audit (task-292) cesse d'être
  victime de la saturation du cache ; aucun événement nouveau à journaliser
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — Redis est dans le périmètre HDS de Staging/Production ; réduire les
  corps de message en cache réduit la surface de données de santé en mémoire partagée
- **AIPD / impact RGPD** : inchangée — aucun traitement nouveau ; la note de l'AIPD sur les données
  transitant par Redis peut mentionner la borne comme mesure de minimisation

## Branches
- `api-mail` (pushed) : feat/task-297-cache-borne-taille-entree — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-297-cache-borne-taille-entree
- `dtos-mss` (pushed, auto-included) : feat/task-297-cache-borne-taille-entree — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-297-cache-borne-taille-entree

## Timings

*(généré par `tools/timing/report.sh --task task-297 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 13 s | — | — | — | — |
| /develop | ok | 15 min 31 s | 5 (34 s) | 4 (3 min 44 s) | — | api-mail 5B/4T |
| /sonar | ok | 10 min 50 s | 3 (41 s) | 11 (5 min 47 s) | 2 (1 min 21 s) | 2 itération(s), api-mail 3B/11T |
| /lint-angular | skipped | 3.1 s | — | — | — | client-angular hors Repos ; arbre = WIP humain (environment.ts) |
| /lint-mobile | skipped | 2.9 s | — | — | — | client-mobile hors Repos, arbre propre sur develop |
| /verify-visual | skipped | 3.0 s | — | — | — | aucun écran mobile touché |
| /review | ok | 18 min 39 s | 3 (12 s) | 3 (2 min 00 s) | — | api-mail 3B/3T |
| /tech-writer | ok | 1 min 51 s | — | — | — | — |
| **Total cycle** | | **47 min 16 s** | **11 (1 min 28 s)** | **18 (11 min 32 s)** | **2 (1 min 21 s)** | |

## Develop log

- Repos touched : `api-mail`
- DTOs published : no DTO change (`dtos-mss` : branche vide, aucun commit)
- Interop published : no interop change
- Commits :
  - api-mail : 49f6b97 feat(cache): borner ce qui entre dans le cache partagé pour qu'il cesse de se saturer seul (task-297)
  - api-mail : 6607c43 refactor(cache): simplify pass (/simplify) — task-297
- **Choix d'implémentation, et pourquoi** :
  - **Un décorateur à la frontière du cache**, `SizeBoundedCacheService`, plutôt qu'un cas particulier dans `MailController.GetEmail`. La borne appartient à qui connaît la taille sérialisée, et le slowlog du 09/09 nomme déjà une **seconde** entrée volumineuse (`usersettings:*`) : un correctif dans le seul appelant connu l'aurait laissée sans protection.
  - **Le budget de 500 ms et le disjoncteur du Sdk sont intacts** (contenu attendu n° 4) : le décorateur les enveloppe. `HealthPlatform.Host.Sdk` est consommé en **NuGet** (12.0.0) depuis un autre dépôt, et les `**Repos**:` de la task ne listent qu'`api-mail` — modifier le Sdk aurait violé la règle 6.
  - **Option 1 retenue, pas l'option « cacher le message sans ses corps »** : le repli base existe déjà et est le chemin normal depuis task-273, donc refuser coûte une lecture en base ; amputer le DTO en cache aurait créé deux formes d'une même entrée et un risque de régression d'affichage — ce que la US interdit explicitement.
  - **Compression (contenu attendu n° 2) : écartée, et chiffrée.** Gzip d'un corps de 1,5 Mo le ramène à ~300-400 Ko, soit encore 3 à 6 fois la borne : la commande resterait bloquante. L'objectif de la US est la **borne de taille**, pas le tassement — comprimer aurait ajouté du CPU par lecture pour rester au-dessus du seuil.
  - **Seuil par défaut 64 Kio, dérivé de la mesure** : le plus petit blocage du slowlog est **160 Ko à 11 ms**. À 64 Kio, l'ordre de grandeur est **~4 ms**, sous le plafond de 5 ms que le Manual Test Plan de la US fixe lui-même. 128 Kio (haut de la fourchette autorisée) resterait vers 9 ms et manquerait ce critère. Le défaut vit dans `CacheOptions`, pas dans le JSON : une installation qui ne configure rien reste bornée.
- **Mesure sans allocation** (trouvée à la passe qualité) : `JsonSerializer.SerializeToUtf8Bytes` allouait un tableau **de la taille de la charge utile** pour n'en lire que la longueur — soit **1,5 Mo sur le tas des grands objets à chaque refus**, c'est-à-dire sur le chemin même que la US protège. Remplacé par un `IBufferWriter<byte>` compteur sur un tampon loué de 4 Kio : même octet, empreinte constante quelle que soit la taille du message.
- Local build / test : ✓ build Release 0 erreur ; `dotnet test` **4 366 réussis**, 0 échec (16 skips pré-existants), dont **12 tests neufs**
- Passe qualité (/simplify) :
  - Applied & committed : api-mail: 6 files (6607c43) — mesure sans allocation (ci-dessus) ; `SetAsync` : trois retours anticipés fondus en une garde et sentinelle `-1` → `long?` ; décoration DI : indirection par service clé supprimée (le descripteur d'origine est capturé dans la fabrique) et aide générique sortie dans son propre fichier ; un seul double de cache dans les tests au lieu de deux
  - Skipped (notés) : garde sur la durée de vie du descripteur décoré (spéculatif) ; promotion du `FakeCacheService` de `mss.mail.infrastructure.tests` en double partagé inter-assemblys (hors périmètre)
  - Skipped (contract/excluded) : dtos-mss
- DOD self-check : 7/8 items vérifiables satisfaits (build, tests, test unitaire de la borne + compteur, test de repli rendant le **même contenu** corps HTML et documents compris, test de capture des deux instruments, seuil configurable documenté dans `appsettings.json`, aucune donnée de santé dans le nouveau chemin — taille et clé seulement, au niveau Debug). **1 item de banc différé (HAG)** : tir journey 1000 iso avant/après (`Timeout getting key` ÷ 10, CPU Redis en pointe, slowlog sans `HMSET mail:email:*` > 5 ms, `Spill buffer unreachable` = 0, étape 3 inchangée) — exige le banc distant, ~3 h par jambe.
- Next step : /sonar task-297

## Sonar log

- Phase 1 (new code) : ✓ Quality Gate **OK**, `new_coverage` = 91,6 %, **0** hotspot new-code
- Phase 1 — Issues fixées : **1** (`csharpsquid:S3604`, MINOR — initialiseur de champ dans une classe à constructeur primaire, sur `SizeBoundedCacheService`). Corrigée par un **constructeur explicite** : la borne reste lue une seule fois, à la construction, plutôt qu'à chaque écriture de cache.
- Phase 1 — **2 issues new-code laissées, et c'est un choix argumenté** : les deux `CA1869` (INFO) de `AuditBackgroundServiceFallbackTests` **ne viennent pas de cette task**. Elles sont héritées de `develop` (code de task-292) et sont **déjà corrigées sur la branche de task-295**, dans la PR api-mail #228 en attente de merge humain. Les recorriger ici produirait un second changement identique sur une seconde branche, donc un conflit mécanique au merge des deux PRs. Elles disparaîtront de `develop` au merge de #228.
- Phase 1 — Tests ajoutés : 0 (la couverture new-code est tenue par les 12 tests écrits en `/develop`)
- Phase 2 (legacy) : **skippée** — 3 des 4 cibles dures d'`agents/sonar-targets.yml` sont déjà tenues (`bugs` 0, `vulnerabilities` 0, `sqale_rating` A). Nettoyer 61 smells legacy sans rapport avec la US aurait fait exploser le périmètre de la PR (règle des ~30 fichiers). Phase 2 est best-effort et ne bloque jamais le cycle.
- Phase 2 — Issues restantes : 61 code smells + 3 security hotspots (dette pré-existante, acceptée)
- Build / tests : ✓ green (Release, 5 suites OpenCover, 4 366 tests réussis)

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | **OK** | → |
| New coverage | 91,5 % | **91,6 %** | +0,1 pt |
| New code smells | 3 | **2** | −1 (S3604 corrigée ; 2 héritées de `develop`, cf. ci-dessus) |
| New bugs / vulnerabilities / hotspots | 0 / 0 / 0 | **0 / 0 / 0** | → |
| Bugs | 0 | 0 | → |
| Vulnerabilities | 0 | 0 | → |
| Security hotspots | 3 | 3 | → |
| Code smells | 62 | **61** | −1 |
| Coverage (projet) | 88,6 % | 88,6 % | → |
| Duplication | 0,4 % | 0,4 % | → |
| Reliability / Security / Maintainability | A / A / A | **A / A / A** | → |

- Convention alimentée : `conventions/csharp.md` — nouvelle entrée **S3604** (constructeur primaire + initialiseur de champ : écrire un constructeur explicite dès qu'il faut **dériver et retenir** une valeur, et surtout ne pas « corriger » en relisant `IOptions` à chaque appel), `Occurrences : 1`
- Next step : /lint-angular task-297

## Lint log

- **Skippée proprement** — `client-angular` n'est pas dans les `**Repos**:` de la task (`api-mail` seul) et `/develop` n'a écrit aucune ligne d'Angular. Les deux fichiers modifiés dans l'arbre Angular (`environment.ts` des applications `mss` et `weda2`) sont les URL d'API locales de l'humain, sur sa branche `feature/nova-rewriting-mss` : mode code-only, la forge n'y touche pas.
- Itérations consommées : 0 / 5
- Next step : /lint-mobile task-297

## Lint mobile log

- **Skippée proprement** — `client-mobile` n'est pas dans les `**Repos**:` de la task, l'arbre de `Client/Mobile/` est propre et sur `develop` (aucun diff vs `origin/develop`).
- Itérations consommées : 0 / 5
- Next step : /verify-visual task-297

## Visual verify log

- **Skippée proprement** — aucun écran `client-mobile` touché : pas de `## Stitch design log`, `client-mobile` hors `**Repos**:`. Aucune capture, aucun serveur démarré.
- Next step : /review task-297

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/229 — label `awaiting-human-merge`
- `dtos-mss` : aucun commit sur `feat/task-297-cache-borne-taille-entree` (pas de changement de contrat) — pas de PR

## Code Review Summary

**Verdict : APPROVED** — 0 blocage, **3 défauts trouvés et corrigés avant la PR**, 1 réserve assumée.

### Défauts trouvés et corrigés

1. **La mesure allouait ce qu'elle mesurait** (trouvé à la passe qualité, commit `6607c43`). `JsonSerializer.SerializeToUtf8Bytes(item).LongLength` alloue un tableau **de la taille de la charge utile** pour n'en lire que la longueur : **1,5 Mo sur le tas des grands objets à chaque refus**, c'est-à-dire sur le chemin même que la classe protège. La protection serait devenue la plus grosse allocation du chemin d'écriture, et le tas des grands objets n'est pas compacté hors collecte de génération 2 — exactement la classe de coût que task-194 avait réduite d'un facteur 13 sur ce même profil de charge. Remplacé par un `IBufferWriter<byte>` compteur sur un tampon loué de 4 Kio.
2. **La mesure ajoutait un second point d'échec à l'écriture** (trouvé en revue de code, commit `54dee31`). `Measure` n'attrapait que `NotSupportedException`, alors que le sérialiseur lève aussi `JsonException` sur un cycle d'objets. Le service interne enveloppe déjà ses écritures et rend `false` : ne rattraper qu'un des deux modes faisait du décorateur un **second endroit où une écriture de cache peut lever** — et il couvre *tous* les écrivains de cache d'api-mail, pas seulement `mail:email:*`. Un test de charge utile cyclique le garde désormais.
3. **`csharpsquid:S3604`** (trouvé par Sonar, commit `006dbc8`) : initialiseur de champ dans une classe à constructeur primaire. Constructeur explicite, qui dit mieux l'intention — la borne est lue **une fois**, pas à chaque écriture.

### Par fichier

- `src/Application/Services/Implementation/SizeBoundedCacheService.cs` — ✅ aucun état mutable partagé (le compteur est alloué par appel, le service est singleton) ; le tampon loué est rendu sur tous les chemins, y compris quand `Ensure` en loue un plus grand ; la borne à zéro court-circuite jusqu'à la mesure, donc une installation qui coupe la fonction ne la paie pas.
- `src/Application/Extensions/ServiceCollectionDecorationExtensions.cs` — ✅ la **durée de vie de l'enregistrement d'origine est reprise telle quelle**, jamais figée en singleton : une bascule du Sdk en scoped ferait sinon capturer un service scoped par un singleton, ce que le conteneur ne signale qu'à l'exécution. Sans cache enregistré (hôte de test qui n'appelle pas `AddSdk`), la méthode ne fait rien plutôt que d'inventer un enregistrement.
- `src/Application/Telemetry/CacheMetrics.cs` — ✅ ni clé, ni corps, ni fragment de message dans les étiquettes : une taille et un résultat. L'histogramme porte ce qui est **offert** et non ce qui est écrit — sans quoi il masquerait la queue de distribution que la borne existe pour couper.
- `src/Api/appsettings.json` — ✅ le seuil est documenté par la mesure qui le fonde, et le défaut vit dans `CacheOptions` : retirer la section ne débride pas le cache.
- Tests — ✅ 13 neufs, un comportement par test. Les deux contre-épreuves qui comptent sont là : **octets UTF-8 et non caractères** (un corps français est plein d'accentués ; mesurer sur la longueur laisserait passer près du double de la borne), et **le message lourd rendu complet à l'identique** aux deux lectures, corps HTML et documents rattachés compris.

### Réserve assumée (non bloquante)

- Sur le chemin **accepté**, la charge utile est parcourue deux fois : une fois pour la mesurer, une fois par le service interne pour l'écrire. L'interface prend un `T` et le service interne possède sa sérialisation ; les octets ne peuvent pas lui être passés sans double encodage — et le Sdk est hors périmètre (NuGet, autre dépôt, règle 6). Les charges acceptées sont sous la borne par construction (64 Kio), et sur le chemin refusé ce parcours **remplace** une sérialisation plus un aller-retour vers Redis.

### Tests de banc exclus du compte, et la raison est mesurée

`GreenMailBenchSmokeTests` et `SmtpSessionReuseBenchSmokeTests` démarrent leurs propres conteneurs et échouent par intermittence sur cette machine, dont le banc de charge de l'humain occupe cinq réplicas d'API et un PostgreSQL à 93 % de son cgroup. Le même commit a **passé puis échoué puis passé**. **Contre-épreuve décisive : le test échoue aussi sur `develop`**, sans aucun changement de cette PR. Le diff ne touche ni SMTP, ni TLS, ni le gestionnaire de sessions. Flaky pré-existant identifié comme tel, donc pas un motif d'arrêt de la chaîne.

### Sécurité / données de santé

- ✅ Aucune donnée de santé dans le nouveau chemin : le seul journal ajouté est au niveau **Debug** et porte une taille et une clé, jamais le contenu. La clé contient l'adresse MSSanté du praticien — même niveau et même forme que le `[GetEmail] ⚡ Cache hit: {CacheKey}` déjà en place.
- ✅ **Effet positif de minimisation** : la US réduit l'emprise des corps de message dans Redis, qui est dans le périmètre HDS de Staging et de Production.
- ✅ Aucun secret, aucune entrée externe : le seuil vient de la configuration, la taille du sérialiseur.

## Merged

- **Date** : 2026-09-13
- **Attestation humaine** : `/merge task-297 --i-tested`
- `api-mail` : squash `a2690a708b1adb69a8a4c2ee1be84567a395b3bf` (PR #229 closed)
- `dtos-mss` : aucun commit — branche `feat/task-297-cache-borne-taille-entree` supprimée sans PR
- Branches distantes supprimées (locales conservées) ; staging `forge/staging-task-295-297-20260911` supprimée (run 295-297 entièrement mergé)
- **CI `develop` : ROUGE** — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/34746668197
  10 erreurs `xUnit1051` dans `tests/mss.mail.application.tests/Services/Cache/SizeBoundedCacheServiceTests.cs`
  (lignes 39, 50, 53, 67, 80, 93, 95, 112, 136, 137). Voir `questions/merge-task-297.md`.
