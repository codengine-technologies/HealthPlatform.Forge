# questions/task-040.md — halt /sonar, baseline + scope mismatch + EF LINQ technical concern

**Date** : 2026-05-17
**Step où l'agent halt** : `/sonar` Step 1 (early-stop / scope evaluation), avant tout fix appliqué.
**État repos** :
- `api-mail` : sur `chore/task-040-sonar-batch-quick-wins`, working tree propre, 0 commit applicatif.
- `dtos-mss` : sur `chore/task-040-sonar-batch-quick-wins`, working tree propre, 0 commit.
- **Workspace forge** : 1 modif non commitée — `agents/sonar.md` (ajout `**/Migrations/**` à `sonar.exclusions`, Étape 0 du task body — déjà appliquée par `/develop`). Le `wip-task-040-*.md` a aussi été enrichi (Branches + Develop log).

---

## Blockers identifiés

### 1. La baseline du task body est obsolète d'un facteur **10×**

Task body (l. 18-29) :

| Métrique | Task | Sonar actuel (2026-05-15 21:29 UTC) | Δ |
|---|---|---|---|
| Bugs | 0 | 0 | OK |
| Vulnerabilities | 0 | 0 | OK |
| Code Smells | **100** | **1064** | **+964 (10.6×)** |
| Security Hotspots | 5 | 7 | +2 |
| Coverage | 65.4 % | 66.3 % | quasi-identique |

Cause probable : changement de quality profile `Sonar way` → `Weda way` (cs) le 2026-05-14 11:53 (event `QUALITY_PROFILE` dans `/api/project_analyses/search`). Ce profile active des règles supplémentaires, dont :
- `external_roslyn:CA1873` — **636 occurrences** (LoggerMessage delegates), inexistant dans la baseline du task
- `csharpsquid:S103` — **188 occurrences** (lines too long), inexistant
- `csharpsquid:S134/S138/S1067` — ~109 occurrences cumulées

Conséquence sur la DOD :
> - [ ] Smells restants : **≤ 51** (100 − 30 − 1 − 1 − 17 = 51, soit S3776 × 39 + S107 × 9 + S6960 × 3)

→ **Mathématiquement impossible** avec un baseline de 1064. Après fix CA1862 (49) + S1075 (1) + S1135 (1) = **51 issues éliminées**, il resterait ~1013 smells, pas 51.

### 2. La prémisse "exclure Migrations supprime 17 S1192" est fausse

Task body Étape 0 :
> Ajouter `**/Migrations/**` à `sonar.exclusions` … pour éliminer définitivement les 17 issues S1192 concentrées dans la migration EF historique.

État actuel Sonar :
- **S1192 total dans le projet** : **0** (pas 17)
- **Issues dans `src/Infrastructure/Migrations` total** : **1** (un `S138` — function too long, pas un `S1192`)

L'exclusion ajoutée à `agents/sonar.md` est techniquement correcte (filet de sécurité pour futures migrations) mais l'**outcome attendu (-17 S1192)** est fictif. Au prochain run Sonar, on perdra 1 smell (S138), pas 17.

### 3. Le scope CA1862 a grossi de **+63 %** depuis le snapshot

Task body : "MailRepository (18) + PatientRepository (12) = 30"
Sonar actuel : MailRepository (24) + PatientRepository (25) = **49**

Ce n'est pas un blocker en soi (le fix reste le même par ligne), mais le volume de travail augmente significativement (49 fixes + tests vs 30).

### 4. **TECHNIQUE CRITIQUE** — les 49 CA1862 sont dans des `Where(...)` **EF Core LINQ**

Toutes les occurrences inspectées (MailRepository L2384-2389, L2414-2419, L2566-2571, L2629-2634 ; PatientRepository L186-191, L241-246, L349-354, L678-683, L841) sont **dans des LINQ-to-SQL** :

```csharp
// MailRepository.cs L2378-2389
var exact = await DataContext.MailMedicalDocuments
    .AsNoTracking()
    .Where(d => d.DocumentId == documentId
                && d.Version == version
                && d.Mail != null
                && (d.Mail.FolderPath == null
                    || (!d.Mail.FolderPath.ToLower().Contains("sent")
                        && !d.Mail.FolderPath.ToLower().Contains(FolderDraft)
                        && !d.Mail.FolderPath.ToLower().Contains(FolderTrash)
                        && !d.Mail.FolderPath.ToLower().Contains(FolderCorbeille)
                        && !d.Mail.FolderPath.ToLower().Contains(FolderEnvoy)
                        && !d.Mail.FolderPath.ToLower().Contains(FolderBrouillon))))
    ...
```

**Problème** : la "correction CA1862 mécanique" proposée par le task body :
```diff
- .ToLower().Contains("sent")
+ .Contains("sent", StringComparison.OrdinalIgnoreCase)
```
n'est **pas garantie de traduire** en SQL dans EF Core / Npgsql. Les risques :
- (a) `InvalidOperationException` au runtime : "could not be translated"
- (b) **Client evaluation silencieuse** : EF charge toute la table en mémoire puis filtre côté .NET → désastre de perfo (tables `MailMedicalDocuments` potentiellement millions de lignes)
- (c) Traduction OK si Npgsql 10 supporte l'overload → besoin de vérification empirique avec génération SQL inspectée

Stack actuel (`Api/Mail/Directory.Packages.props`) :
- `Microsoft.EntityFrameworkCore` : **10.0.7**
- `Npgsql.EntityFrameworkCore.PostgreSQL` : **10.0.1**

EF Core 9+ supporte `string.Contains(string, StringComparison)` dans certains providers, mais Npgsql 10 a son propre tableau de translatabilité — à valider.

### 5. La DOD "behavioural test case-insensitive" est fondée sur un malentendu

Task body Étape 1 (CA1862) :
> **Behavioural** car la comparaison passe de culture-sensitive à invariante : ajouter **un test par méthode impactée** qui vérifie le matching insensible à la casse avant le fix.

→ **Faux**. Le code actuel `.ToLower().Contains(x)` est **déjà case-insensitive** au niveau SQL : il génère `LOWER(field) LIKE '%x%'`. Pas de changement de comportement attendu (et donc pas de RED test à écrire pour la case-insensitivity — elle est déjà là).

La "bonne raison" du fix CA1862 c'est la perfo (éviter l'allocation de la string `.ToLower()`), pas la sémantique. Mais en EF Core, l'allocation n'a pas lieu (traduction SQL).

### 6. L. 841 PatientRepository est `==`, pas `.Contains`

```csharp
&& md.Mail.FolderPath.ToLower() == "inbox"
```

CA1862 ici recommande `.Equals("inbox", StringComparison.OrdinalIgnoreCase)`, **pas** `.Contains(..., StringComparison)`. Le task body ne couvre pas ce cas — sa stratégie de fix unique ne s'applique pas à L841.

---

## Décisions demandées au humain

### Option A — Restreindre la task à S1075 + S1135 (+ exclusion Migrations), annuler le batch CA1862

- Garder Étape 0 (exclusion Migrations dans `agents/sonar.md` — déjà fait).
- Fix S1075 (URI Flagsmith → config) : 1 fichier, 1 test, ~30 min.
- Décider S1135 (TODO NewMailNotifier) : lire le TODO, résoudre ou reformuler.
- **Abandonner CA1862 sur cette task** ; créer `todo-task-04X-ca1862-ef-linq-investigation.md` avec scope explicite :
  - Investigation SQL générée par EF Core 10 + Npgsql 10 sur `.Contains(x, OrdinalIgnoreCase)` (un endpoint de test, capture du SQL via `EnableSensitiveDataLogging` + log)
  - Décision : passer au fix CA1862, ou installer un `[SuppressMessage]` localisé sur les méthodes Repository concernées avec justification "EF LINQ — translation case-insensitive déléguée à `LOWER() LIKE`"
  - Si fix retenu : application aux 49 occurrences + L841 (Equals) + tests d'intégration vérifiant le SQL (pas juste le résultat)

Update DOD : retirer "Smells restants ≤ 51", "0 occurrence CA1862", la ligne "S1192 × 17".

### Option B — Procéder en knowing-defective : appliquer les fix CA1862 sur les 49 occurrences EF LINQ

Risque : régression de perfo non détectable par les tests unitaires actuels (qui mockent le DbContext). Détection seulement en intégration / runtime. Coût d'investigation post-hoc élevé.

**Recommandation forge** : NON. Ce serait introduire un risque silencieux dans du code SQL chaud (recherche multi-folder sur `MailMedicalDocuments`).

### Option C — Refondre la task complètement

Mettre à jour la baseline Sonar (1064 smells réels), redéfinir le scope (par exemple : top-N règles "safe-to-batch" hors EF LINQ), refondre la DOD avec les vrais compteurs.

### Option D — Halt sec : marquer task-040 comme bloquée, créer une nouvelle US plus ciblée

Effacer (`/cancel`) la branche `chore/task-040-*` sur `api-mail` + `dtos-mss`, garder l'edit `agents/sonar.md` (utile), ouvrir une nouvelle US séparée par règle Sonar plutôt qu'un "batch quick-wins" agrégé.

---

## Pourquoi je halt plutôt que procéder

- CLAUDE.md règle 7 — "Edge case not covered by task DOD" (EF LINQ translation non couvert) + "Business rule ambiguity" (baseline obsolète, scope CA1862 change ×1.6).
- Le coût d'une mauvaise décision est élevé : 49 fix EF LINQ × régression perfo silencieuse = potentiel ralentissement majeur de toutes les recherches mail/patient en prod.
- La "bonne réponse" demande une investigation EF/Npgsql ou une décision produit (accepter `SuppressMessage` localisé) qui dépasse le périmètre d'un `/sonar` automatique.

**Aucune autre étape (`/lint-angular`, `/review`, `/tech-writer`) n'est invoquée — la chaîne s'arrête ici.**

Task reste en `wip-task-040-sonar-batch-quick-wins.md`. Branches `chore/task-040-*` poussées mais vides. Aucun commit applicatif.
