# todo-task-206.md — Le banc lève une exception par requête, et ce bruit noie la télémétrie

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: task-204 (la colonne « Exceptions /s » qui a rendu le défaut visible)
**Priorité**: **4/6** — Fidelite du banc (ordre arrêté le 2026-07-31, objectif montée en charge)
> Une exception par requete (~1 400/s au plafond) : le banc n'exerce pas le chemin d'authentification de production. Un chiffre de capacite mesure sur un autre chemin que celui deploye n'est pas opposable.

> **Origine** : tir de contrôle télémétrie du 2026-07-29 (task-204). La colonne
> « Exceptions /s » que task-204 vient d'ajouter au rapport a immédiatement montré
> un débit d'exceptions absurde. Personne ne l'avait vu avant, faute de la mesurer.

## Objective

Faire en sorte qu'un tir de charge n'exerce pas un chemin de code qui **lève une
exception à chaque requête**, pour deux raisons également importantes : la mesure
n'est pas fidèle au chemin de production, et le bruit rend la colonne
« Exceptions /s » inutilisable pour détecter une vraie anomalie.

### La mesure

| Charge | `SecurityTokenMalformedException` | Débit d'exceptions |
|---|---|---|
| 106 req/s (20 praticiens) | 12 668 en 121 s | ~105/s, **≈1,2 par requête** |
| ~480 req/s (200 praticiens) | — | ~110-145/s **par réplica** |
| ~858 req/s (200 praticiens) | — | ~233-290/s **par réplica**, soit **>1 200/s** au total |

Le débit croît linéairement avec la charge : c'est **une exception par requête**,
pas un incident.

Autres familles relevées, pour mémoire (elles ne sont pas l'objet de cette task) :
`FolderNotFoundException` (l'absence de dossier `Sent` sur les boîtes du banc,
connue et documentée comme bénigne), `HttpRequestException`, `FlagsmithAPIError`,
`IOException`, `XmlException`.

### La cause

Le banc envoie `X-PSC-Token: loadtest` — une valeur non vide mais **pas un JWT** —
parce que le profil `https-load-test` pose `MSS_ENFORCE_PSC_IDENTITY=false` et que
« n'importe quelle valeur non vide suffit ». Or le code **tente quand même de
parser le token** avant de constater qu'il n'a pas à l'exiger : le parse lève,
l'exception est avalée, et la requête continue normalement.

⚠️ **En production le token est valide, donc ce chemin ne lève pas.** Ce n'est
donc pas un défaut de production — c'est un défaut de **fidélité du banc** (la
mesure inclut un coût que la production ne paie pas) doublé d'un défaut
d'**observabilité** (le bruit masque les vraies exceptions). Les deux se corrigent
ensemble.

### Deux voies, à trancher dans l'US

1. **Ne pas parser quand l'enforcement est désactivé** — le garde `enforce=false`
   doit court-circuiter *avant* la tentative de parse, pas après. Corrige la cause
   pour tout appelant, banc ou non. À préférer si le parse n'a aucun autre effet
   utile dans ce mode.
2. **Faire forger au banc un token syntaxiquement valide** (seed / harnais k6) —
   la mesure exerce alors exactement le chemin de production, y compris son coût
   de parsing. Plus fidèle, mais laisse le parse spéculatif en place.

Les deux sont compatibles ; la voie 1 est la correction, la voie 2 la fidélité.

## Contenu attendu

1. Localiser le site du parse spéculatif et **nommer** pourquoi il s'exécute alors
   que l'enforcement est désactivé.
2. Mettre en œuvre la voie retenue (argumenter le choix dans la task).
3. Vérifier au banc que le débit d'exceptions s'effondre, et que les familles
   restantes sont **toutes** explicables.
4. Documenter dans le skill `loadtest-skill` la lecture attendue de la colonne
   « Exceptions /s » (quel ordre de grandeur est normal après correction).

## Hors scope

- `FolderNotFoundException` / l'absence de dossier `Sent` sur les boîtes du banc :
  déjà documentée comme bénigne, à traiter seulement si le banc provisionne un
  `Sent` un jour.
- La famine de ThreadPool et le plafond de capacité (task-205).

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures)
- [ ] Test unitaire : avec l'enforcement **désactivé** et un token non-JWT,
      **aucune exception n'est levée** sur le chemin de la requête
- [ ] Test unitaire : avec l'enforcement **activé**, un token invalide est toujours
      rejeté (la correction ne desserre aucun contrôle)
- [ ] **Mesure au banc** : à ~480 req/s, `SecurityTokenMalformedException`
      **= 0** sur la fenêtre du tir (contre ~110-145/s par réplica)
- [ ] Après correction, chaque famille d'exception restante est nommée et
      expliquée dans le rapport de tir
- [ ] `loadtest-skill` : la lecture attendue de « Exceptions /s » est écrite

## Manual Test Plan

1. Monter le banc (skill `loadtest-skill`), 200 praticiens re-câblés
   (`--users 200 --messages 0`).
2. Tir court : `RPS=540 ... run.sh mixed --env VUS=60 --env DURATION=2m`.
3. Relever le débit d'exceptions par type :
   ```bash
   curl -s --get 'http://127.0.0.1:9090/api/v1/query' \
     --data-urlencode 'query=sum by (error_type) (increase(dotnet_exceptions_total[2m]))'
   ```
   `SecurityTokenMalformedException` doit être **absent**.
4. Lire la colonne « Exceptions /s » de la table « Par réplica api-mail » du
   rapport : elle doit tomber à un ordre de grandeur exploitable.
5. Contrôle de non-régression fonctionnelle : les tirs `folders` / `read` /
   `search` / `send` répondent toujours 200 (aucun 401/403 nouveau).

## Branches

- `api-mail` (pushed) : `fix/task-206-psc-token-speculative-parse` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-206-psc-token-speculative-parse
- `dtos-mss` (pushed, auto-inclus) : `fix/task-206-psc-token-speculative-parse` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/fix/task-206-psc-token-speculative-parse
  (aucun changement de contrat attendu — branche créée proactivement, pas de PR si aucun commit)

> **Préfixe `fix/`** : la task supprime un parse spéculatif qui lève à chaque
> requête, ce n'est pas une nouvelle capacité.

> ⚠️ **Deux critères de la DOD sur six exigent le banc** — la mesure
> `SecurityTokenMalformedException = 0` à ~480 req/s, et l'explication de chaque
> famille d'exception restante dans un rapport de tir. Ce sont les étapes 1 à 5
> du Manual Test Plan, côté humain. Les deux tests unitaires (enforcement
> désactivé → aucune exception ; enforcement activé → token invalide toujours
> rejeté) et la documentation du skill sont du ressort de `/develop`.

## Develop log

- **Repos touchés** : `api-mail` (C# de production + tests + harnais k6).
  `dtos-mss` : aucun commit → pas de PR.
- **Commits** : `b0fd300` (correctif + tests), `42daac8` (passe `/simplify`).
- **Build / tests** : Release 0 erreur / 0 avertissement ; **3 236 réussis** au
  moment du développement, dont **+17** dans `mss.mail.api.tests` (607 vs 590).
  `selftest.sh` du harnais vert (15 node + 90 Python) ; `k6 inspect` OK.
- **Test-first** : constatés RED avant le code — 4 des 5 tokens non-JWT levaient
  effectivement une exception.

### Le choix entre les deux voies, et pourquoi il s'écarte de l'énoncé

L'énoncé proposait, en voie 1, de court-circuiter le parse quand
`Enforce=false`. **Je ne l'ai pas fait ainsi.** Ce garde-là aurait privé le
**mode observation** — qui *est* `Enforce=false`, phase 1 — des journaux
`3721`/`3722`/`3723` qu'il existe précisément pour produire : un déploiement en
observation serait devenu aveugle sans que rien ne le signale.

La garde porte donc sur la **lisibilité du token** (`CanReadToken`), pas sur
l'enforcement. Elle supprime l'exception pour **tout appelant** et dans **tous
les modes**, sans rien perdre : un token illisible n'a jamais rendu de claims, il
coûtait seulement une exception pour le dire. Deux tests pinnent qu'aucun
contrôle n'est desserré (`Enforce=true` → toujours 403 ; `Enforce=false` →
journal 3723 toujours émis).

**Et la voie 2 est livrée aussi, parce qu'elle est nécessaire.** La voie 1 seule
fait désormais *sauter* le parse au banc : il n'exerce toujours pas le chemin
déployé, alors que l'énoncé pose lui-même qu'« un chiffre de capacité mesuré sur
un autre chemin que celui déployé n'est pas opposable ». Le harnais forge donc un
token à la forme d'un vrai JWT par identité, miroir de
`PscTokenForge.BuildPayloadOnlyToken`. `PSC_TOKEN` reste une échappatoire.

### Deux choix de test qui méritent d'être dits

- **Exceptions comptées en première chance** (`AppDomain.FirstChanceException`).
  Une exception avalée reste levée, avec son coût de pile et sa ligne de
  télémétrie ; c'est le seul moyen d'observer un défaut que le code masque.
- **Le token réellement produit par k6 est figé en fixture** dans le test C#.
  Une divergence d'encodage JS/.NET — remplissage base64url, casse de
  `SubjectNameID` — ferait retomber le banc dans le chemin qu'il quitte, **sans
  rien casser de visible**.

### Passe `/simplify` — le cache retiré

Le cache de tokens ajouté par `/develop` est **par VU**, et le banc en alloue
~900. À 200 identités en tourniquet, il retiendrait ~110 Ko par VU, soit ~100 Mo
côté tireur — pour économiser un `JSON.stringify`, un base64url et un SHA-256 sur
~250 octets. À 900 req/s le forgeage coûte bien moins d'un pour cent d'un cœur,
quand k6 en consomme déjà 0,2 à 0,4. Le tireur doit rester hors de cause : ici le
risque était la mémoire, pas le CPU.

### ⚠️ Un vrai défaut trouvé à la validation, hors périmètre

`PatientRepositoryTests.GetWithMedicalDocumentsTodayAsync…` échoue **de façon
déterministe entre minuit et 2 h du matin** (heure d'été). Diagnostic :

| | |
|---|---|
| `PatientRepository` filtre sur | `var today = DateTime.Today` — minuit **local** |
| Les dates sont stockées en | UTC |

À 00 h 14 local (22 h 14 UTC), le document semé « aujourd'hui » tombe avant la
borne locale, et la requête ne renvoie rien.

**Ce n'est pas qu'un test fragile** : la liste « patients avec un document
aujourd'hui » est fausse en production pendant la même fenêtre quotidienne.
Module différent, aucun rapport avec le token PSC — **à arbitrer par le PO**,
probablement une task dédiée.

L'autre échec de la passe finale est le flaky documenté
`MailExportServiceTests.BuildPdfWithMedicalDocumentHtmlBodyFallback` :
`mss.mail.application.tests` repasse **1 858/1 858 en isolation**.

### DOD

Réalisés :

- [x] Build passes (0 errors)
- [x] Tests pass (les deux échecs de la passe finale sont antérieurs et
      diagnostiqués ci-dessus)
- [x] Test unitaire : enforcement **désactivé** + token non-JWT → **aucune
      exception levée**
- [x] Test unitaire : enforcement **activé** + token invalide → **toujours
      rejeté**
- [x] `loadtest-skill` : la lecture attendue de « Exceptions /s » est écrite

Non réalisés — **le banc n'est pas monté** :

- [ ] Mesure au banc : `SecurityTokenMalformedException` **= 0** à ~480 req/s
- [ ] Chaque famille d'exception restante nommée dans le rapport de tir

## Sonar log

- **Aucun finding introduit** — un seul passage d'analyse a suffi.
- **Build / tests** : ✓ Release 0 erreur / 0 avertissement.

### KPIs qualité

| Métrique | Valeur |
|---|---|
| Quality Gate | ERROR (2 findings Python de task-204, hors diff) |
| **Findings sur le code de cette task** | **0** |
| Bugs / Vulnerabilities / Hotspots à revoir | 0 / 0 / 0 |
| Code smells | 2 |
| Coverage projet / new | 86,6 % / 86,2 % |
| Reliability / Security / Maintainability | A / A / A |

Convention `csharpsquid:S103` vérifiée avant commit. Aucune convention nouvelle à
consigner : la task n'a corrigé aucune règle Sonar.

## PRs

- `api-mail` : **https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/136**
  — label `awaiting-human-merge`, `MERGEABLE`, 2 commits, 5 fichiers.
- `dtos-mss` : **aucune PR** — branche sans commit. Ref distant supprimé.
- `client-angular`, `client-mobile`, `devops`, `psc-proxy-*` : hors périmètre.

## Code Review Summary

Verdict : **APPROVED** — 0 blocage.

| Fichier | Verdict |
|---|---|
| `src/Api/Middleware/UserContextEnricherMiddleware.cs` | ✅ garde de 4 lignes au bon niveau d'abstraction, mesure et raisonnement en commentaire |
| `tests/.../PscTokenSpeculativeParseTests.cs` | ✅ 12 tests, exceptions en première chance, contrat JS→.NET figé |
| `tests/.../UserContextEnricherCrossCheckTests.cs` | ✅ 5 tests ajoutés là où vivent déjà les helpers, sans les dupliquer |
| `tests/loadtest-k6/lib/identity.js` | ✅ forge sans cache, raisonnement écrit sur place |
| `tests/loadtest-k6/lib/config.js` | ✅ échappatoire `PSC_TOKEN` préservée |

## Reste à faire par le humain

1. **Tester puis merger la PR #136** — HAG, règle 10.
2. **Les deux critères de DOD au banc** restent décochés.
3. **Arbitrer le défaut `DateTime.Today` vs UTC** de `PatientRepository`
   (ci-dessus) — il mérite sa propre task.
4. **Révoquer et régénérer le `SONAR_TOKEN`** : `agents/sonar.md` le passe en
   argument de ligne de commande (`/d:sonar.token=…`), donc il est lisible par
   tout processus local — et il s'est retrouvé affiché dans un listing de
   processus pendant ce cycle. Le scanner sait lire la variable d'environnement
   `SONAR_TOKEN` à la place.

## Merged

- **Date** : 2026-08-01
- `api-mail` : squash `c99b04a` — PR
  [#136](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/136)
  fermée. Ref distant `fix/task-206-psc-token-speculative-parse` supprimé,
  **branche locale conservée**.
- `dtos-mss` : aucune PR (branche sans commit) — ref distant déjà supprimé au
  `/review`, repo sur `develop`.
- `client-angular`, `client-mobile`, `devops`, `psc-proxy-*` : hors périmètre.
- **Staging** : `forge/staging-task-176-196-20260728` conservée — 206 est hors
  de sa plage `[176, 196]`, et ce run n'est pas drainé.
