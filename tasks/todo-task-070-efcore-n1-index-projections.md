# todo-task-070.md — Perf EF Core : N+1, index manquants, projections et batching

**Repos**: api-mail
**Dependencies**: (aucune)
**Epic**: E011

> US mono-repo justifiée : optimisation de la couche d'accès aux données
> (`src/Infrastructure`). Aucun changement de contrat DTO ni d'UI. Inclut une
> migration EF Core (index) — la règle 7c (audit de migration) s'applique.

## Objective

Éliminer les anti-patterns d'accès aux données les plus coûteux de
`src/Infrastructure` : requêtes N+1 dans les boucles d'enrichissement, recherches
patient par INS sans index (full table scan répété), chargements d'entités
lourdes sans projection ni `AsNoTracking`, `SaveChangesAsync` multiples et
lookup O(N²) en mémoire.

## Findings adressés (audit perf 2026-06-10)

| # | Localisation | Problème | Impact |
|---|---|---|---|
| 1 | `src/Infrastructure/Repository/MailRepository.cs:488-509` | `AnyAsync` appelé dans une boucle par pièce jointe (N+1) | Élevé |
| 2 | `src/Infrastructure/Repository/MailRepository.cs:513` | `FirstOrDefaultAsync(p => p.Ins == ...)` dans une boucle, **sans index sur `MailPatient.Ins`** → full table scan × N | Élevé |
| 3 | `src/Infrastructure/Persistance/MailDataContext.cs` | Index manquants : `MailPatient.Ins` ; évaluer `Mails.FolderPath` seul, `Mails.SentDate`, `Mails.IsRead` selon les requêtes réelles | Élevé |
| 4 | `src/Infrastructure/Repository/MailRepository.cs:1947-1952` | 6 `Include` (dont `MailContents` et `MailAttachments` avec colonnes lourdes) sans `AsNoTracking` ni projection ; risque d'explosion cartésienne en SingleQuery | Élevé |
| 5 | `src/Infrastructure/Repository/MailRepository.cs:1414-1466` | 5+ `SaveChangesAsync` séquentiels dans le même flux (5 allers-retours DB au lieu d'1) | Élevé |
| 6 | `src/Infrastructure/Repository/PatientRepository.cs:463` | `mailsRaw.FirstOrDefault(...)` dans un `Select` sur liste = O(N²) → Dictionary | Élevé |
| 7 | `src/Infrastructure/Repository/BiologyRepository.cs:33-37` | Include en cascade complet là où une projection suffirait | Moyen |
| 8 | Configuration DbContext | Pas de `QuerySplittingBehavior` explicite pour les requêtes multi-Include ; `AddDbContextPool` à évaluer | Moyen |
| 9 | `src/Infrastructure/Repository/MailRepository.cs:1733-1735` | Deserialize → mutation → Serialize du `MetadataJson` complet pour patcher un champ | Moyen |

## Comportement attendu

- Les boucles d'enrichissement préchargent leurs lookups en **une** requête
  (attachements existants, patients par INS) avant itération.
- `MailPatient.Ins` est indexé (migration EF Core dédiée, auditée selon la
  règle 7c : lecture du fichier généré, pas d'opération fantôme, `.Designer.cs`
  présent, `dotnet ef migrations has-pending-model-changes` propre).
- Les lectures seules utilisent `AsNoTracking` et des projections `Select`
  ciblées quand les colonnes lourdes (body, contenu de pièce jointe) ne sont pas
  nécessaires.
- Un seul `SaveChangesAsync` par unité de travail logique.
- Le lookup O(N²) est remplacé par un `Dictionary`.
- `QuerySplittingBehavior.SplitQuery` est appliqué (globalement ou par requête)
  sur les requêtes multi-Include après mesure.

## Definition of Done

- [ ] Build passes : `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` (0 erreur)
- [ ] Tests pass : `dotnet test HealthPlatform.Api.Mail.sln` (0 échec)
- [ ] Plus d'appel DB dans les boucles identifiées (findings 1 et 2) — préchargement en une requête
- [ ] Migration EF Core ajoutant l'index sur `MailPatient.Ins` créée ET auditée (règle 7c : migration lue, pas d'opération fantôme, Designer + snapshot présents, pas de drift)
- [ ] Les requêtes de lecture seule des repositories touchés portent `AsNoTracking`
- [ ] La requête multi-Include de `MailRepository.cs:1947` ne charge plus les colonnes lourdes inutilisées (projection) ou est passée en SplitQuery avec justification mesurée
- [ ] Un seul `SaveChangesAsync` sur le flux `MailRepository.cs:1414-1466`
- [ ] Lookup O(N²) de `PatientRepository.cs:463` remplacé par Dictionary (test unitaire de non-régression du tri)
- [ ] Unit tests : >= 1 test par méthode de repository modifiée (comportement identique avant/après — caractérisation)
- [ ] Integration test : >= 1 test traversant le pipeline DI complet sur un endpoint utilisant `MailRepository` (liste de mails taggés) — happy path + dossier vide
- [ ] Aucune donnée de santé (INS, contenu CDA) en clair dans les logs ajoutés/modifiés

## Manual Test Plan

- Lancer l'API : `cd Api/Mail && docker-compose up -d && dotnet run --project src/Api`
- Charger un compte de test avec >= 200 mails dont >= 50 documents médicaux
  (données anonymisées).
- Ouvrir la liste des mails d'un tag : la liste s'affiche correctement
  (mêmes éléments qu'avant la US), temps de réponse mesuré en baisse.
- Intégrer un document médical avec patient existant (rattachement INS) :
  l'opération aboutit, le log SQL (niveau debug en local) montre un nombre de
  requêtes constant, indépendant du nombre de pièces jointes.
- Vérifier en base que la migration d'index est appliquée
  (`\d "MailPatients"` sous psql → index sur `Ins` présent).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (LPS MSSanté)
- **Vague Ségur** : hors Ségur — optimisation technique
- **Exigences DSR honorées** : non applicable — aucun changement fonctionnel
- **INS** : l'INS est utilisé comme clé de recherche (index ajouté) — aucun changement de statut ni de traitement de l'INS ; l'INS n'apparaît dans aucun log
- **Authentification PS** : inchangée
- **Habilitations** : non applicable
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé
- **Consentement patient** : non applicable
- **Référentiels métier** : LOINC (catégorisation documents) — usage inchangé
- **Hébergement HDS** : oui — environnement HDS existant ; la migration d'index ne déplace aucune donnée
- **AIPD / impact RGPD** : inchangé
