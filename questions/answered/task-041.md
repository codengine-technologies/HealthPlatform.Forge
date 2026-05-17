# questions/task-041.md — halt /develop, règle S107 absente du profile actif

**Date** : 2026-05-17
**Step où l'agent halt** : `/develop` Step 0 (pre-flight + scope validation), avant toute édition de code.
**État repos** :
- `api-mail` : sur `chore/task-041-sonar-s107-param-objects`, working tree propre, 0 commit applicatif.
- `dtos-mss` : sur `chore/task-041-sonar-s107-param-objects`, working tree propre, 0 commit (auto-include).

---

## Blocker

Le task body annonce **9 occurrences `csharpsquid:S107`** à éliminer. Vérification post-task-040 (Sonar re-analysé 2026-05-17T08:47 UTC, post-exclusion Migrations + fix S1075/S1135) :

```
csharpsquid:S107 → total: 0
```

La règle **n'est pas dans le profile `Weda way`** actif depuis 2026-05-14 (event `QUALITY_PROFILE` dans `/api/project_analyses/search`). Le profile `Sonar way` historique l'incluait — d'où le compte "9" dans le snapshot du PO. Depuis le switch de profile, S107 est silencieuse.

### Méthodes physiquement présentes (mais non-flaggées)

Toutes les 9 méthodes du task body existent toujours dans le code (cf. `git grep` / lecture directe) :

| # | Fichier | Ligne | Statut |
|---|---|---|---|
| 1 | `MailController.cs` | 25 | ✅ Présente — `public sealed class MailController(` (ctor primaire ~16 deps) |
| 2 | `ImapConnectionService.cs` | 29 | ✅ Présente (ligne montre un paramètre du ctor) |
| 3 | `ImapFolderService.cs` | 29 | ✅ Présente — `public ImapFolderService(` |
| 4 | `ImapService.cs` | 42 | ✅ Présente — `public partial class ImapService(ILogger<ImapService> logger,` |
| 5 | `BackgroundImapService.cs` | 36 | ✅ Présente — `public BackgroundImapService(` |
| 6 | `SmtpService.cs` | 15 | ✅ Présente — `public class SmtpService(` |
| 7 | `ISemanticSearchService.cs` | 23 | ✅ Présente — `Task<IEnumerable<SemanticSearchResult>> SearchAsync(` |
| 8 | `ImapLockScope.cs` | 38 | ✅ Présente — `public static async Task<ImapLockScope> AcquireAsync(` |
| 9 | `PatientRepository.cs` | 565 | ⚠️ Ligne 565 vide — peut avoir bougé, méthode probablement toujours là quelques lignes après/avant |

### Implication DOD

La DOD task-041 (l. 93) dit :
> [ ] **0 occurrence** restante de `csharpsquid:S107` post-analyse Sonar

→ **Trivialement satisfait** dès maintenant. Aucun refactor nécessaire pour valider la DOD littéralement.

Mais l'Objectif (l. 13-14) dit :
> chaque méthode (en réalité un constructeur primaire ou une signature de service) avec > 7 paramètres est refactorée en **param object** (record `*Options` ou `*Args`) pour gagner en lisibilité, en testabilité, et en évolutivité.

→ L'intent du PO est un **refactor de design**, pas seulement une coche Sonar. Les méthodes lourdes (notamment `MailController` 16 deps) sont des code smells réels que la disparition de S107 ne fait pas disparaître.

---

## Options demandées au humain

### Option A — Close task-041 comme no-op (couplée à un realignment Sonar profile)

- Renommer task-041 en `done-*` ou directement `archived-*` avec note "DOD trivialement satisfait : règle S107 désactivée par le profile Weda way".
- Spinner une **task séparée** côté SonarQube admin : "ré-évaluer si S107 doit être réactivée dans Weda way (et si oui, à quel seuil — 7 paramètres par défaut, ou plus permissif vu la densité actuelle des ctors DI)".
- Aucun fichier api-mail touché. Branches `chore/task-041-*` supprimées (locale + remote sur api-mail et dtos-mss).

### Option B — Refactorer quand même, indépendamment de Sonar

- Considérer les 9 méthodes (notamment `MailController` 16 deps) comme un vrai code smell de design, traiter comme tel.
- DOD à recalibrer : retirer "0 occurrence S107" (vide de sens) et la remplacer par des critères qualitatifs ("chaque ctor lourd extrait un record `*Dependencies` ou un split fonctionnel justifié").
- Risque : refactor cosmétique (param wrapping) sans valeur design réelle. La vraie réponse est probablement **`MailController` split fonctionnel** (style S6960 task-042/043/044), pas un param object wrapper.
- ~30 j·p estimés (16 deps × 6 fichiers × tests + adaptation callers).

### Option C — Refactorer uniquement les vrais cas design (sous-ensemble des 9)

- `ISemanticSearchService.SearchAsync` (méthode métier publique, vrai pattern S107 design → record `SemanticSearchOptions`).
- `ImapLockScope.AcquireAsync` (méthode publique, vrai pattern S107).
- `PatientRepository.???` (méthode publique).
- **Ignorer** les ctors DI (1-6) : un record `*Dependencies` injecté en DI est juste un wrapper cosmétique sans gain réel. Le vrai fix de `MailController` 16 deps est un split S6960 (déjà tracké ailleurs).
- Compromis raisonnable. ~5-10 j·p.

### Option D — Re-activer S107 dans le profile Weda way, puis revenir à task-041 originale

- Action humaine côté SonarQube admin : ré-importer la règle `csharpsquid:S107` dans `Weda way (cs)`.
- Re-analyse Sonar → S107 = 9 (espéré).
- Reprendre task-041 originale (refactor des 9 méthodes flaggées).
- Coût : 10 min admin Sonar + ~30 j·p refactor.

---

## Recommandation forge

**Option C** — refactorer seulement les vrais cas design (méthodes métier publiques). Les ctors DI lourds doivent être traités par split fonctionnel (S6960 ou une décision d'archi), pas par un wrapper cosmétique. Mais c'est une décision PO/archi qui demande ton arbitrage.

## Pourquoi je halt plutôt que procéder

- **CLAUDE.md règle 7** : Business rule ambiguity. L'Objectif et la DOD pointent vers des cibles incohérentes (intent design vs métrique Sonar trivialement nulle).
- Le coût d'une mauvaise décision est élevé : ~30 j·p de refactor cosmétique si on suit Option B sans valeur réelle, vs ~5-10 j·p ciblé si on suit Option C.
- Le pattern est strictement le même que task-040 (baseline obsolète par switch profile, halt + option A choisie par le humain). Cohérent avec ton choix précédent.

**Aucune étape suivante (`/sonar`, `/lint-angular`, `/review`, `/tech-writer`) n'est invoquée — la chaîne s'arrête ici.**

Task reste en `wip-task-041-sonar-s107-param-objects.md`. Branches `chore/task-041-*` poussées mais vides. Aucun commit applicatif.
