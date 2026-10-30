# todo-task-410 — Le cache patient par INS est cloisonné par boîte

**Repos**: api-mail
**Sonar**: bypass — décision humaine du 2026-10-30 (`/start --no-sonar`)
**E2E**: bypass — décision humaine du 2026-10-30 (`/start --no-e2e`)
**Dependencies**: aucune
**Epic**: E020

> **Origine** : audit du périmètre « boîte déléguée » du 2026-10-30
> (`Docs/audits/2026-10-30-audit-boite-deleguee.md`), constat **C1 (critique)**.
>
> **Single layer** : correctif backend seul, sans effet visible sur les écrans. Les fronts ne
> changent pas.

## Objectif

Une fiche patient n'est jamais servie à une autre boîte que la sienne. Aujourd'hui, le cache Redis
de la résolution d'un patient par INS a pour clé `patient:ins:{hash(INS)}`. Elle ne nomme ni la base
ni la boîte, et le cache est commun à toute la plateforme. Quand un médecin résout un INS, la fiche
d'un autre cabinet (identité, naissance, identifiant technique) peut lui être rendue pendant 5
minutes. Il apprend du même coup que ce patient est suivi ailleurs.

## Règles

1. La clé de cache d'une fiche patient porte l'**adresse de la boîte** (`UserContextInfo.Email`), comme
   toutes les clés de boîte du catalogue `RedisKeys` (`mail`, `folder`, `sync`, `user:{adresse}:contacts`).
   Décision humaine du 2026-10-30, en remplacement du nom de base.
   - **Pourquoi c'est équivalent** : depuis task-404, une adresse donne exactement une base (unicité de
     `mss_mailboxes` sur l'adresse et sur `database_name`). Deux boîtes n'ont donc jamais la même clé.
   - **Construite dans le catalogue** : un constructeur `RedisKeys.Patient.ByIns(adresse, condensatIns)`,
     jamais une chaîne assemblée à la main dans `PatientRepository`.
   - **Adresse normalisée** : minuscules, espaces retirés. Sinon une même boîte écrite en deux casses
     aurait deux clés : rien ne fuit, mais le cache rate.
   - L'INS reste **haché**, comme aujourd'hui. Seule l'adresse est en clair, comme dans les autres clés.
2. L'invalidation à l'écriture d'une fiche vise la clé de **cette** boîte.
3. **Revue des autres clés** : toute clé de cache Redis construite sans la boîte est soit cloisonnée,
   soit justifiée par écrit. Une clé de déduplication de tâche, par exemple, ne porte aucune donnée.
   L'audit n'a trouvé que `patient:ins` ; la revue le confirme ou complète la liste. Toute clé de boîte
   passe par `RedisKeys`.
4. Les entrées déjà en cache sous l'ancienne clé ne sont plus jamais lues : le changement de format
   suffit, et leur TTL de 5 minutes les efface.

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures)
- [ ] Unit tests de `RedisKeys.Patient.ByIns` :
  - la clé diffère pour un même INS dans deux boîtes ;
  - elle est identique pour une même boîte écrite en deux casses ou avec des espaces ;
  - elle ne contient pas l'INS en clair.
- [ ] Test d'intégration de bout en bout pour `POST /patients/resolve` : deux boîtes A et B, sur deux
      bases, connaissent chacune une fiche différente pour le même INS. A résout l'INS, puis B le
      résout : B lit **sa** fiche (nom et identifiant de B) dans la réponse réelle. Quand B ne
      connaît pas l'INS, B reçoit l'absence de fiche, jamais celle de A. Vu rouge sur le code d'avant
      le correctif (règle 1b).
- [ ] Revue des clés Redis consignée dans le `## Develop log` : chaque gabarit de clé, sa portée
      (boîte, personne, plateforme) et sa justification
- [ ] Aucune donnée de santé en clair dans les logs ni dans les clés Redis (l'INS reste haché)
- [ ] `conventions/csharp.md` : entrée « une clé de cache d'une donnée de boîte nomme la boîte, par son
      adresse, et se construit dans `RedisKeys` »

## Manual Test Plan

- Backend : `cd Api/Mail && dotnet run --project src/AppHost` (profil e2e).
- Deux médecins du seed, sur deux boîtes, avec chacun un patient de même INS (seed ou fiche saisie).
- Médecin A : ouvrir la fiche du patient par son INS. Médecin B, dans les 5 minutes : rechercher le
  même INS.
- Attendu : B voit sa propre fiche, ou « aucun patient », jamais le nom saisi chez A.
- Redis (`redis-cli --scan --pattern 'patient:*'`) : chaque clé porte l'adresse de sa boîte, par
  exemple `patient:{adresse}:ins:{condensat}`. Aucune clé ne porte l'INS en clair, et l'ancien format
  `patient:ins:*` a disparu.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif de sécurité
- **Exigences DSR honorées** : non applicable — confidentialité des données de santé (PGSSI-S,
  cloisonnement des données entre structures)
- **INS** : manipulée comme clé de recherche. Statut inchangé, jamais en clair dans la clé ni dans
  les logs.
- **Authentification PS** : inchangée (PSC)
- **Habilitations** : une fiche patient n'est lue que par les personnes rattachées à sa boîte
  (règle 14)
- **Interop CI-SIS** : non applicable — aucun échange
- **Tracé PGSSI-S** : inchangé (`PatientRecordViewed`). La journalisation de l'objet consulté relève
  de task-413.
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — Redis et PostgreSQL de la plateforme
- **AIPD / impact RGPD** : à noter — la fuite possible entre cabinets avant correctif est à évaluer
  comme incident potentiel (journal de Redis, durée d'exposition). Inchangé après correctif.

## Branches

> **Sonar** : bypass demandé par l'humain au /start — /sonar n'analysera pas api-mail ; la PR le dira.
> **E2E** : bypass demandé par l'humain au /start — /e2e ne jouera aucune voie ; la PR le dira.

- `api-mail` (pushed) : fix/task-410-cache-patient-par-ins-cloisonne-par — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-410-cache-patient-par-ins-cloisonne-par

## Develop log

### Correctif

- `RedisKeys.Patient.ByIns(adresse, ins)` (`src/Application/Constants/RedisKeys.cs`) :
  `patient:{adresse normalisée}:ins:{SHA-256 de l'INS, 16 octets en hexa}`. Une adresse vide est refusée
  (`ArgumentException`). L'adresse est passée en minuscules et sans espaces autour.
- `PatientRepository` : la clé n'est plus construite dans le dépôt. `PatientCacheKey` rend `null` quand
  aucune boîte n'est connue (`OptionalUserContextInfo?.Email` vide, cas du dépôt construit sur un contexte
  explicite). Alors **rien n'est mis en cache** : ni lecture, ni écriture, ni invalidation. Une clé sans
  boîte serait commune à toutes les boîtes.
- L'invalidation à l'écriture de l'opposition vise la clé de la boîte courante (règle 2).
- Nouveau constructeur de test `PatientRepository(MailDataContext, UserContextInfo, ILogger, cache?)`.
- Anciennes entrées `patient:ins:*` : plus jamais lues, effacées par leur TTL de 5 min (règle 4).

### Tests

| Niveau | Test | Ce qu'il prouve |
|---|---|---|
| Unitaire | `RedisKeysPatientTests` (7) | deux boîtes → deux clés ; même boîte en deux casses ou avec espaces → même clé ; pas d'INS en clair ; deux INS → deux clés ; adresse vide refusée |
| Unitaire | `PatientRepositoryCacheTests` (6, dont 2 nouveaux) | deux boîtes sur **un même cache** lisent chacune leur fiche ; sans boîte, rien n'est caché ; préfixe `patient:{boîte}:ins:` |
| Intégration (1b) | `PatientCacheAcrossMailboxesEndToEndTests` (3) | `POST /api/v1/patients/resolve`, vraie pile, deux bases PostgreSQL (boîtes 22 et 23), **vrai cache** `ResilientCacheService` sur le Redis de la fixture, partagé par les deux boîtes |

Le test d'intégration remplace le substitut de cache de la fixture par le vrai, parce que c'est le cache
qui porte le comportement : avec le substitut, le test serait vert sur le code fautif.

**Preuve rouge (mutation, 2026-10-30)** : `ByIns` remis à l'ancien format `patient:ins:{condensat}`,
sans la boîte. Les deux tests d'intégration échouent :
- `TheSameInsInTwoMailboxes_…` : attendu `(id de B, "Bravo")`, reçu `(id de A, "Alpha")`. B lit la fiche de A ;
- `AnInsKnownOnlyInMailboxA_…` : attendu 404, reçu 200 avec la fiche « Alpha » de A.

Restauré par `cp` + `touch`, et `grep MUTATION` rend 0. Reconstruit puis vert.

**Ajout à la revue** (`/review`, 2026-10-30) : l'invalidation à l'écriture de l'opposition change aussi
de clé, et seul un test unitaire sur un cache en mémoire la couvrait. Comme la règle 1b n'accepte pas
un test unitaire seul, un test d'intégration a été ajouté :
`AnOppositionWritten_IsReadAtOnce_ByTheNextResolutionOfThatMailbox`.
- Le parcours : résolution (mise en cache, opposition fausse), puis `PUT /patients/{id}/opposition`,
  puis nouvelle résolution, qui doit lire l'opposition vraie sur le vrai cache.
- **Preuve rouge (mutation)** : `RemoveAsync(cacheKey)` est retiré. Le test reçoit `False` (fiche
  périmée servie par le cache) au lieu de `True`.
- Code restauré par `cp` + `touch`, `grep MUTATION` rend 0. Les 26 tests patient d'intégration sont verts.

### Revue des clés Redis (règle 3)

| Gabarit | Portée | Verdict |
|---|---|---|
| `patient:{adresse}:ins:{condensat}` | boîte | **corrigé** (C1) : portait l'INS seul |
| `RedisKeys.Mail.*`, `Folder.*`, `Sync.Coverage`, `Lock.*`, `Account.Quota`, `Contact.*` (`user:{adresse}:contacts…`) | boîte | cloisonnées par l'adresse, dans le catalogue |
| `mss:sync:state:{adresse}`, `mss:sync:progress:{adresse}` (`RedisSyncStateStore`) | boîte | cloisonnées par l'adresse ; préfixe propre au magasin |
| `draft:{adresse}:{id}`, `draft:index:{adresse}`, `draft:lock:…` (`DraftCacheRepository`) | boîte | cloisonnées par l'adresse |
| `mss:ai:conv:{boîte}:{id}`, `mss:ai:conv-index:…` | boîte | cloisonnées (décision humaine : IA à la boîte) |
| `mss:search-history:{adresse}` | adresse, à passer à la personne | cloisonnée, sans fuite entre boîtes ; le passage à la personne relève de task-413 |
| `user:id:{base}:{sujet}` (`BaseRepository`) | boîte × personne | cloisonnée par le nom de base |
| `setupdb:{base}` | boîte | marqueur de provisionnement, sans donnée |
| `mailbox-sender:{guid}` | boîte | GUID v7 de l'utilisateur de la base : unique par construction |
| réglages `…{userId:N}` (`UserSettingsRepository`) | personne | GUID unique par construction |
| `registry:tenant:{sujet}:{adresse}` | personne × boîte | cloisonnée |
| `session:mailbox:{clientSessionId}` | session | lie une session à une boîte (task-365) ; sans donnée de boîte |
| `psc:person-name:{proxySession}` | personne | nom PSC, par session de proxy |
| `archive-sent:{Message-ID}` | message | déduplication d'une tâche ; ne porte aucune donnée ; Message-ID unique par message envoyé |
| `sync-command:{kind}` | plateforme | déduplication de commande, sans donnée |
| `mail-autoconfig:{domaine}`, `crl:validation:…`, `ocsp:validation:v2:…`, `ocsp:issuer:…`, `annuaire:quota:…`, instantanés de drapeaux | plateforme | aucune donnée de boîte |

Conclusion : `patient:ins` était la seule clé portant une donnée de boîte sans nommer la boîte.
L'audit est confirmé, et la liste n'est pas complétée.
- Les magasins `RedisSyncStateStore`, `DraftCacheRepository` et `RedisAiConversationStorage`
  construisent leurs clés hors du catalogue, mais toujours avec l'adresse.
- Les y déplacer ne change aucun format : la consigne s'applique au code nouveau.

**Données de santé** : l'INS n'apparaît ni dans les clés (condensat seul, test unitaire) ni dans les
journaux (aucun journal ajouté).

**Convention** : `conventions/csharp.md` § `cle-de-cache-de-boite`.

## Sonar log

**Sonar : non joué — bypass demandé par l'humain** (`/start --no-sonar`, 2026-10-30). Aucune analyse
d'api-mail : la dette introduite par cette task n'est pas mesurée. Build, tests, règle 1b et revue de
code inchangés.

## Lint log

`/lint-angular` : skipped — client-angular non touché. `/lint-mobile` : skipped — client-mobile non touché.

## E2E log

**E2E : non joué — bypass demandé par l'humain** (`/start --no-e2e`, 2026-10-30). La task touche
`api-mail`, donc la voie mobile et la voie Angular auraient été jouées. Aucune voie ni porte n'a été
jouée. La non-régression fonctionnelle n'est pas prouvée, et le test manuel doit la couvrir. La task ne
crée ni ne modifie de parcours médecin : aucun scénario n'est attendu au catalogue.

## Timings

*(généré par `tools/timing/report.sh --task task-410 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 17 s | — | — | — | — |
| /develop | ok | 14 min 16 s | 2 (24 s) | 2 (5 min 42 s) | — | api-mail 2B/2T |
| /sonar | skipped | 0.5 s | — | — | — | bypass humain (--no-sonar) |
| /lint-angular | skipped | 0.5 s | — | — | — | angular non touché |
| /lint-mobile | skipped | 0.5 s | — | — | — | mobile non touché |
| /e2e | skipped | 0.5 s | — | — | — | bypass humain (--no-e2e) |
| /review | ok | 7 min 47 s | 2 (12 s) | 1 (5 min 23 s) | — | api-mail 2B/1T |
| /tech-writer | ok | 29 s | — | — | — | — |
| **Total cycle** | | **22 min 53 s** | **4 (36 s)** | **3 (11 min 06 s)** | **0 (0.0 s)** | |

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/330 — label `awaiting-human-merge`

## Code Review Summary

**APPROVED** — 5 fichiers, 0 bloquant, 1 suggestion (ligne de commentaire vide `//` dans `PatientRepository`).

| Comportement atteignable par un endpoint | Test d'intégration | Preuve rouge |
|---|---|---|
| `POST /patients/resolve` : la fiche lue en cache est celle de la boîte (même INS, deux boîtes) | `TheSameInsInTwoMailboxes_EachMailboxResolvesItsOwnRecord_ThroughOneSharedCache` | mutation clé sans boîte : B reçoit la fiche « Alpha » de A |
| `POST /patients/resolve` : un INS inconnu de B rend 404, même mis en cache par A | `AnInsKnownOnlyInMailboxA_IsNotFoundInMailboxB_EvenOnceCachedByA` | même mutation : 200 avec la fiche de A |
| `PUT /patients/{id}/opposition` invalide l'entrée de la boîte | `AnOppositionWritten_IsReadAtOnce_ByTheNextResolutionOfThatMailbox` (ajouté à la revue) | mutation invalidation retirée : `False` au lieu de `True` |

Build + tests à la revue : 7 262 tests, 0 échec. Sonar et e2e : bypass humain, annoncés en tête de PR.
