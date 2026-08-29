# todo-task-276.md — Le verrou de session n'est plus tenu pendant toute la lecture d'un dossier

**Repos**: api-mail
**Dependencies**: task-270 (mergée — cette US corrige la contrepartie qu'elle a introduite, sans revenir sur son acquis)
**Epic**: E015

## Objectif

task-270 a tenu sa promesse mécanique : un cache-miss de dossier coûte **5**
allers-retours IMAP au lieu de 7, et le compteur de sollicitations (task-262) le
prouve au tir discriminant du 2026-08-29
(`Api/Mail/tests/loadtest-k6/reports/2026-08-29/report-journey-500-task270-20260829-220155.md`,
finding **F-270-1**) :

| Opération | Commandes émises | Occurrences (régime) |
|---|---|---|
| `GetFolderStatus` | `resolve_folder` + `status_folder` = **2** | 21 302 |
| `GetFolderQuery` | `open_folder` + `search_folder` + `close_folder` = **3** | 5 304 |

`GetFolderQuery` n'émet plus ses propres `resolve_folder`/`status_folder` — le
doublon est bien supprimé. Les acquisitions de session pour la lecture de
dossier tombent de **18,73/s à 12,98/s (−31 %)**.

**Et le médecin n'en voit rien.** Iso-conditions avec le tir de référence du
26/08 (même base hydratée, mêmes réserves, mêmes fenêtres, latence par
aller-retour appariée à ~100 ms) :

| `dashboard,call:folder`, palier 500 | Réf 26/08 | Tir 29/08 | Δ |
|---|---|---|---|
| moyenne | 357,1 ms | **358,4 ms** | **+0,4 %** |
| p50 | 148,3 | 140,3 | −5,4 % |
| p95 | 967,5 | 928,3 | −4,1 % |

Deux allers-retours retirés à ~100 ms pièce sur ~25 % des appels valaient ~50 ms
de moyenne attendue. **Observé : 0.**

**La cause est mesurée, et c'est le verrou.** La fusion a échangé *deux sections
critiques courtes* contre *une longue* :

| Opération | Attente p95 (s) | Détention p95 **exploitation** (s) |
|---|---|---|
| 26/08 `GetFolderStatus` | 1,150 | 0,242 |
| 26/08 `GetFolderQuery` | 0,450 | 0,692 |
| **29/08 `ReadFolder`** (fusion) | 0,909 | **11,871** |

`imap_session` sérialise **toutes** les opérations IMAP d'un praticien : les
voisins paient l'allongement de la section critique.

| Opération | 26/08 | 29/08 | Δ |
|---|---|---|---|
| `UpdateFlag` — attente p95 | 0,487 s | **9,443 s** | **×19** |
| `GetAttachmentStream` — attente p95 | 0,475 s | **4,500 s** | ×9,5 |
| `GetEmailContent` — détention p95 | 0,700 s | **22,222 s** | ×32 |

Le faisceau se retrouve côté médecin : **8 étapes sur 12 se dégradent, et ce sont
celles qui partagent la session IMAP** — `read_list` +23 % de moyenne,
`patient_dossier` +27 %, `mark_read` +12 %, `read_content` +9 %, `send` +6 % —
tandis que la Recherche, servie hors IMAP, s'améliore. Le clivage suit
exactement la ligne du verrou.

**Ce n'est PAS encore une régression vécue** : les 11 étapes sont vertes,
0,000 % d'erreurs, « Marquer lu » vaut 29/76 ms au client. C'est un **risque
latent**, qui s'aggravera au palier 1000 où tout est déjà congestionné.

### ⚠️ L'instrument d'abord — la cause n'est pas encore scopée

**La table « `imap_session`, par opération » du rapport est calculée sur TOUT le
tir, chauffe comprise.** Or task-264 a séparé chauffe et régime pour le reste du
rapport, et **task-271 a précisément montré qu'une détention élevée vit souvent
dans la chauffe, hors du parcours jugé**. Tant que cette table n'est pas repliée
par fenêtre, on ne peut pas affirmer que les 11,871 s de `ReadFolder` sont sur
le chemin du médecin.

**Cette US commence donc par l'instrument, et n'écrit le remède qu'ensuite.**
Cette EPIC a déjà payé une US applicative écrite sur une cause supposée
(task-222, annulée) : le coût du raccourci est connu et non théorique.

### Contenu attendu, dans cet ordre

1. **Instrument (`report.py`, harnais)** — replier la table des verrous par
   fenêtre **chauffe / régime**, comme le rapport le fait déjà pour les étapes.
   Deux colonnes ou deux tables, au choix technique, mais la fenêtre de verdict
   doit être lisible seule.
2. **Établir sur pièce** où vit la détention de `ReadFolder` : régime, chauffe,
   ou les deux. **Si elle est majoritairement en chauffe, l'US s'arrête ici** —
   le constat est consigné, le remède n'a pas lieu d'être, et c'est un résultat.
3. **Remède, seulement si (2) le justifie** — relâcher le verrou entre le
   plancher (`resolve` + `STATUS`) et la recherche (`SELECT`/`SEARCH`/`CLOSE`),
   **sans** re-payer `resolve` + `STATUS` (passer le dossier déjà résolu à la
   seconde section) et **sans** perdre les 5 allers-retours de task-270.

**Gain attendu** : rien sur `folder` — sur les **opérations voisines** de la
session (`UpdateFlag`, `GetEmailContent`, `GetAttachmentStream`), dont l'attente
doit revenir à l'ordre de grandeur du 26/08.

**Risque à traiter explicitement dans l'implémentation** : relâcher entre les
deux sections rouvre la fenêtre que task-270 a fermée — deux appelants
pourraient intercaler une opération entre le `STATUS` et le `SEARCH`. L'US doit
dire ce que cela change pour la cohérence de la réponse (les compteurs rendus
viennent du `STATUS` de l'appel courant ; la liste d'UIDs vient du `SEARCH`) et
le fixer par un test.

**Ce qui n'est PAS dans le périmètre** : le nombre d'allers-retours (acquis de
task-270, à ne pas dégrader), le coût de la page d'en-têtes, le contrat de la
route.

## Definition of Done

- [ ] Build passes (0 erreur)
- [ ] Tests pass (0 échec)
- [ ] La table des verrous du rapport de tir est **repliée par fenêtre
      chauffe / régime** ; la fenêtre de verdict est lisible seule
- [ ] Test du harnais (`test_report_session_lock.py` ou voisin) fixant le
      repliement : une détention taguée `chauffe` n'entre pas dans la colonne
      régime
- [ ] La localisation de la détention de `ReadFolder` (régime / chauffe) est
      **établie et écrite** dans le task file, chiffres à l'appui
- [ ] Si remède : le nombre d'allers-retours d'un cache-miss reste à **5** et
      celui du chemin `GetFolderStatus` à **2** — prouvé par le compteur de
      sollicitations (tests de task-270 non régressés)
- [ ] Si remède : test unitaire sur la cohérence de la réponse quand une
      opération s'intercale entre le plancher et la recherche
- [ ] Si remède : parité champ pour champ du corps de réponse, chemin court et
      chemin long (non-régression du test de task-270)
- [ ] Aucune donnée de santé dans les journaux : les étiquettes du compteur et
      du verrou restent des littéraux, aucun contenu de message ni INS

## Manual Test Plan

**Ce que l'humain valide au HAG** : que la lecture d'un dossier fonctionne à
l'identique. Le gain, lui, est un fait de banc et se juge au tir suivant.

1. Lancer le banc en profil loadtest :
   ```bash
   cd Api/Mail
   dotnet run --project src/AppHost --launch-profile https-load-test
   ```
2. Attendre `http://127.0.0.1:5052/api/v1/connection/status` en 200.
3. Seeder deux boîtes : `dotnet run --project tests/mss.mail.loadtest.seed -- --users 2 --messages 20 --api http://127.0.0.1:5052`
4. Ouvrir le dossier `INBOX` pour l'utilisateur 1 :
   `GET http://127.0.0.1:5052/api/v1/mail/folders/INBOX` avec les en-têtes
   d'identité virtuelle (`Client-Email: loadtest-1@loadtest.local`,
   `Client-Rpps: 90000000001`, `Client-Psc-Sub: 00000000-0000-4000-8000-000000000001`,
   `Client-Session-Id: sess-1`, `X-Test-Bypass: loadtest-local-only`,
   `X-PSC-Token: loadtest`).
5. **Vérifier** : la réponse liste les messages, avec `Count`, `UnreadCount` et
   `UidNext` cohérents. Rejouer l'appel : la seconde arrivée doit être servie
   sans nouvelle recherche (voir les journaux `[ListFolder]`).
6. Marquer un message comme lu, puis rouvrir le dossier : le compteur de non-lus
   doit avoir bougé.
7. **Clôture de l'US — au banc, tir suivant** : tir `journey` 500 médecins en
   iso-conditions du `report-journey-500-task270-20260829-220155.md`, sur la
   **même base hydratée**. Critères :
   - attente p95 de `UpdateFlag` **< 1 s** (contre 9,443 s)
   - détention p95 en exploitation de la lecture de dossier **< 2 s** en fenêtre
     de régime (contre 11,871 s toutes fenêtres)
   - `read_list` et `patient_dossier` reviennent au niveau du 26/08
     (respectivement ≤ 130 ms et ≤ 70 ms de moyenne)
   - allers-retours d'un cache-miss **toujours à 5** (non-régression task-270)

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — optimisation de performance interne
- **Exigences DSR honorées** : non applicable — comportement fonctionnel inchangé
- **INS** : non applicable
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable — IMAP interne au périmètre MSSanté existant
- **Tracé PGSSI-S** : inchangé — la consultation de dossier reste journalisée à l'identique
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — inchangé
- **AIPD / impact RGPD** : inchangé

## Branches

- `api-mail` (pushed) : `feat/task-276-folder-session-lock-scope` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-276-folder-session-lock-scope
- `dtos-mss` (pushed, auto-inclus) : `feat/task-276-folder-session-lock-scope` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-276-folder-session-lock-scope (aucun changement de contrat attendu — l'US ne touche ni DTO ni route)
- `client-angular`, `client-mobile`, `devops`, `psc-proxy-*` — non concernés (US strictement backend + harnais de banc)

## Develop log

**Repos touchés** : `api-mail` uniquement (harnais de banc, `tests/loadtest-k6/`).
`dtos-mss` : branche créée par `/start` (auto-inclusion), **aucun commit** —
l'US ne touche ni DTO ni route, donc pas de publish NuGet ni de bump consommateur.

### L'US s'est arrêtée à son instrument — et c'est son résultat

Le task file prévoyait explicitement cette issue : « **Si elle est
majoritairement en chauffe, l'US s'arrête ici** — le constat est consigné, le
remède n'a pas lieu d'être, et c'est un résultat. » C'est ce qui s'est produit,
à une nuance près : la détention ne vit pas dans la chauffe, elle vit dans des
**transitoires**. Le remède prévu à l'étape 3 est **sans objet**.

### Étape 1 — l'instrument (livré)

Deux défauts empilés dans la table « `imap_session`, par opération », pas un :

| # | Défaut | Correctif |
|---|---|---|
| 1 | Fenêtre = tout le tir, chauffe comprise, alors que task-264 sépare les deux partout ailleurs | `regime_window(ctx)` + `collect_prometheus_regime()` — second passage borné à la fenêtre de verdict |
| 2 | **Réducteur = `max`** : le pire instant imprimé comme une valeur d'exploitation | `_series_distribution()` — médiane / p90 / pointe / part au-dessus de 2 s |

Le second n'était pas dans le périmètre initial de l'US. Il a été trouvé en
exécutant l'étape 2, et c'est lui qui portait la fausse conclusion.

**Piège traité au passage** : les requêtes sont des `rate(...[1m])`, donc le
premier point d'une sous-fenêtre agrège la minute qui précède. Sans décalage, le
repliement laissait entrer jusqu'à 60 s de chauffe — en petite quantité, donc
sans se voir. `PROM_RATE_LOOKBACK_S` décale le début de fenêtre ; 60 s de régime
perdus sur 2 001 (3 %), contre une contamination silencieuse.

### Étape 2 — l'établissement sur pièce

Rapport `report-journey-500-task270-20260829-220155.md` régénéré avec
l'instrument, sur le Prometheus du tir. Fenêtre de régime, palier 500 :

| Opération | Médiane | p90 | Pointe | Part > 2 s |
|---|---|---|---|---|
| `GetFolders` | 0,242 s | 0,250 | 0,394 | 0,0 % |
| `EnrichEmails` | 0,425 s | 0,713 | 2,050 | 1,4 % |
| **`ReadFolder`** (la fusion de task-270) | **0,469 s** | 0,560 | 11,871 | **2,8 %** |
| `UpdateFlag` | 0,496 s | 0,679 | 9,750 | 3,1 % |
| `AppendToSent` | 0,498 s | 0,681 | 0,871 | 0,0 % |
| `GetEmailContent` | 0,500 s | 0,745 | 22,222 | 5,4 % |
| **`GetAttachmentStream`** | 0,697 s | **2,136** | 17,500 | **11,6 %** |

**Verdict : la détention de `ReadFolder` ne pèse pas sur le chemin du médecin.**
Sa médiane (0,469 s) est **inférieure** aux 0,692 s de `GetFolderQuery` qu'elle
remplace — la fusion a légèrement **raccourci** la section critique typique, pas
allongée. Les 11,871 s sont un transitoire sur 2,8 % des relevés, et la même
forme frappe `GetEmailContent` (5,4 %) et `GetAttachmentStream` (11,6 %), que
task-270 n'a jamais touchés : **congestion du tir, pas propriété du chemin
fusionné**.

### Étape 3 — remède : AUCUN, volontairement

Relâcher le verrou entre le plancher et la recherche aurait corrigé une
contention **qui n'existe pas**. L'écrire aurait répété task-222 (US annulée,
écrite sur une cause supposée) — à ceci près que la cause était ici *mesurée*
mais *mal réduite*, ce qui est plus insidieux.

### Ce que l'US corrige en plus de son objet

Le rapport du tir portait un finding **faux** (« la fusion allonge la section
critique, les voisins paient ×19 »), déduit de la comparaison de deux **pointes**.
Il est **réfuté et corrigé** dans le rapport, avec la table de ce qui tient et de
ce qui tombe. Un finding neuf et correctement scopé le remplace :
**`GetAttachmentStream` est la seule opération dont la détention est tenue en
régime** (11,6 % des relevés > 2 s).

C'est la **troisième fois** que cette EPIC se fait piéger par son instrument —
buckets en millisecondes (task-211), plafond d'histogramme (task-245),
saturation lue comme timeout (task-271). Même famille : **une non-mesure
imprimée avec l'apparence d'une mesure.**

### Vérification

- `tests/loadtest-k6/selftest.sh` → **332 tests verts** (329 avant, +3 nets)
- 12 tests neufs dans `test_report_session_lock_regime.py` : fenêtre de régime
  (4), garde de lookback (2), rendu et attribution (6) — dont les deux tests
  symétriques qui fixent que la phrase **suit la mesure dans les deux sens**
  (une pointe est nommée pointe, une détention soutenue n'est pas excusée)
- Rapport du tir régénéré et relu : la table repliée s'imprime sur données
  réelles, l'attribution désigne `GetAttachmentStream` et exonère `ReadFolder`
- Aucun code applicatif touché — `dotnet build` / `dotnet test` sans objet pour
  ce diff (harnais Python uniquement, hors solution .NET)

### DOD

- [x] Build passes — sans objet (diff Python uniquement) ; auto-tests harnais verts
- [x] Tests pass — 332/332
- [x] Table repliée par fenêtre chauffe / régime, fenêtre de verdict lisible seule
- [x] Test du harnais fixant le repliement (+ la garde de lookback, non prévue)
- [x] Localisation de la détention de `ReadFolder` établie et écrite, chiffres à l'appui
- [x] Remède : **sans objet** — la mesure l'a rendu injustifié (issue prévue par l'US)
- [x] Allers-retours inchangés — aucun code applicatif touché
- [x] Aucune donnée de santé : le repliement ne lit que des étiquettes
      d'opération et des durées

## Simplify log

**Repos éligibles touchés** : `api-mail` (harnais Python uniquement). `dtos-mss`
exclu par construction (porteur de contrat, 0 commit). Aucun frontend touché.

| Axe | Constat | Action |
|---|---|---|
| Réutilisation | La compréhension qui indexe les séries `imap_session` par requête puis par opération était **recopiée à l'identique** dans la table toutes-fenêtres et dans la table repliée. Deux jumelles qui devaient rester égales sur l'étiquette de repliement (`operation`) — une divergence n'aurait pas planté, elle aurait rendu deux tables qu'on croirait comparables. | Extraite en `_session_lock_series(payloads)` |
| Simplification | `build_telemetry` lisait le retour de `regime_window` par indices (`regime[0]`, `regime[1]`, `regime[2]`) — un tuple opaque au point le plus lu du dict de télémétrie. | Déballage nommé `regime_start, regime_end, regime_stage` |
| Efficacité | Aucun finding : le second passage Prometheus est volontairement borné aux seules requêtes de verrou (élargir doublerait le temps de collecte d'un rapport pour des sections qui ne servent pas à décider d'un correctif). | — |
| Altitude | `_series_distribution` nomme ce que le rapport ne savait pas dire (médiane / p90 / pointe / part au-dessus du seuil) au lieu de laisser un `max` parler pour quatre grandeurs. | Déjà traité par `/develop` |

**Recherche de réutilisation préalable** : aucun helper de percentile n'existe
dans `report.py` (ni `statistics` importé) — `_series_distribution` ne duplique
donc rien.

**Re-validation** : `tests/loadtest-k6/selftest.sh` → **332 verts, 0 rouge**.
Aucun changement de comportement : les tests de rendu passent inchangés.

## Sonar log

**Analyse NON exécutée — prérequis d'environnement absent, pas un état du code.**

| Contrôle | Attendu | Constaté |
|---|---|---|
| SonarQube joignable | `http://127.0.0.1:9001` (doc `agents/sonar.md`) | ❌ port 9001 muet — le serveur écoute en fait sur **9000** (`{"status":"UP"}`, v9.9.8) |
| `$SONAR_TOKEN` | présent dans l'environnement | ❌ **absent** du shell de la forge |

Le scanner ne peut pas s'authentifier sans le token, qui appartient à l'humain
(règle du skill : « Token read from `$SONAR_TOKEN`, never hardcoded »). L'étape
étant **best-effort**, la chaîne se poursuit plutôt que de s'arrêter sur un
prérequis local — mais elle ne publie **aucun KPI**, et surtout **aucun vert**.

**Ce que ça laisse ouvert, honnêtement** : le diff de la task est **Python
uniquement** (`tests/loadtest-k6/report.py` + un fichier de tests), et le harnais
k6 **est** scanné par Sonar — il portait 42 des 64 violations new-code au tir de
task-270. Le risque de dette neuve n'est donc pas nul, il est **non mesuré**.
Aucun fichier C# n'est touché : la dette .NET, elle, est inchangée par
construction.

**Écart de documentation relevé** : `agents/sonar.md` et le skill `sonar-skill`
annoncent `9001` et `9000` respectivement. Le serveur répond sur **9000**. À
redresser dans `agents/sonar.md` — hors périmètre de cette task (règle 6).

**Geste pour l'humain** : `$env:SONAR_TOKEN = "<token>"` puis
`/sonar 276` rejoué, ou l'analyse lancée depuis le skill `sonar-skill`.

## Lint log (/lint-angular)

**Skip clean** : `client-angular` n'est pas listé dans `**Repos**:` et aucun
fichier de `Client/Angular/front/` n'a été écrit — le diff de la task est
`tests/loadtest-k6/report.py` + un fichier de tests Python. Chaîne vers
`/lint-mobile`.

## Lint mobile log (/lint-mobile)

**Skip clean** : `client-mobile` n'est pas listé dans `**Repos**:` et aucun
fichier de `Client/Mobile/` n'a été écrit. Chaîne vers `/verify-visual`.

## Visual verify log (/verify-visual)

**Skip clean** : aucun écran `client-mobile` touché (task backend/harnais seule,
pas de `## Stitch design log`). Chaîne vers `/review`.

## PRs

- `api-mail` — **[PR #207](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/207)** — label `awaiting-human-merge`, `MERGEABLE`
- `dtos-mss` — branche créée par `/start` (auto-inclusion), **0 commit** : aucun
  changement de contrat, donc **aucune PR** et aucun publish NuGet. Branche
  distante à supprimer au `/merge`.
- `client-angular`, `client-mobile`, `devops`, `psc-proxy-*` — non concernés.

## Code Review Summary

**APPROVED** — 2 fichiers revus (1 source, 1 tests), 0 bloquant, **1 défaut
trouvé et corrigé par la review elle-même**.

| Fichier | Verdict |
|---|---|
| `tests/loadtest-k6/report.py` | ✅ repliement correct, lookback des `rate[1m]` neutralisé, attribution symétrique. ❌→✅ **trouvé en review** : une phase `operate` non mesurée rendait une table à en-tête sans ligne — se lit « détentions nulles » au lieu de « aucune mesure ». Corrigé (`46dc442`) ; c'est le mode d'erreur gravé par task-214. |
| `tests/loadtest-k6/test_report_session_lock_regime.py` | ✅ 13 tests. Les deux tests symétriques (pointe nommée / détention soutenue non excusée) sont ce qui empêche la phrase d'attribution de dériver dans un seul sens. |

**Suggestion non bloquante** : `agents/sonar.md` annonce SonarQube sur le port
9001, le skill `sonar-skill` sur 9000, et le serveur répond sur **9000**. À
redresser dans `agents/sonar.md` — hors périmètre (règle 6).

**DOD** : 8/8 vérifiables verts. L'item « remède » est vert **par
non-application** : la mesure l'a rendu injustifié, issue explicitement prévue
par le task file.

### Validation finale

- `tests/loadtest-k6/selftest.sh` → **333 verts / 0 rouge**
- `dotnet build HealthPlatform.Api.Mail.sln` → 0 erreur / 0 avertissement
- Branche à jour avec `origin/develop` (merge, pas de rebase — règle 4)

## Merged

**Date** : 2026-08-29 — `/merge 276 --i-tested` (HAG, règle 10 : validé par
l'humain avant merge).

| Repo | PR | Squash commit sur `develop` |
|---|---|---|
| `api-mail` | [#207](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/207) closed | [`8867dc5`](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/commit/8867dc5741d18b2c3c99d41e11d71ebe6e2a86d4) — `feat(loadtest): task-276 — la table des verrous est repliée sur la fenêtre de verdict et rend sa distribution (#207)` |
| `dtos-mss` | aucune PR (branche à 0 commit) | — |

**Portes de sécurité au merge** : `--i-tested` fourni ; label
`awaiting-human-merge` (pas `awaiting-us-completion`) ; `MERGEABLE` / `CLEAN` ;
CI de la PR verte (`build` pass, `publish` skipped) ; aucun `CHANGES_REQUESTED`.

**Branches** : refs distantes `feat/task-276-folder-session-lock-scope`
supprimées sur `api-mail` et `dtos-mss` ; branches locales conservées.

**Staging** : aucune branche `forge/staging-*` — rien à nettoyer.

**Ce que ce merge met sur `develop`, et pourquoi l'ordre comptait** :
l'instrument corrigé est désormais sur `develop` **avant** tout nouveau tir.
Un rapport produit sans lui republierait la pointe comme une valeur
d'exploitation — l'artefact qui avait fait publier une cause fausse sur
task-270.

**Reste ouvert (hors périmètre du merge)** :
- `tests/loadtest-k6/reports/INDEX.md` — récit de campagne du tir du 2026-08-29,
  **non commité**, en attente de décision humaine.
- Finding neuf non instruit : `GetAttachmentStream` est la seule opération dont
  la détention est **tenue en régime** (médiane 0,697 s, p90 2,136 s, 11,6 % des
  relevés > 2 s). Instruisable sur les données Prometheus du tir, encore vivantes.
- Sonar jamais exécuté sur ce diff (`$SONAR_TOKEN` absent) — dette Python non mesurée.
