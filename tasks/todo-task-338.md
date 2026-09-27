# todo-task-338.md — La recherche dit la vérité : une panne n'est plus « aucun résultat », chaque filtre demandé est appliqué, et les vues par étiquette sont couvertes

**Repos**: api-mail
**Dependencies**: — (aucune ; **à coordonner avec task-192**, qui touche les mêmes fichiers — voir « Coordination »)
**Epic**: E009
**Single frontend**: true
**Priorité**: **2** — le médecin qui cherche un compte rendu pendant une panne conclut qu'il **n'existe pas** ; un filtre désactivé renvoie toute la boîte ; la recherche par mot-clé ne fonctionne pas depuis une vue « Urgent ».

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, **AUD-38**, **AUD-39**, **AUD-40**, **AUD-52**).

## Ce qui est établi (develop @ `14d58398`)

1. **Panne masquée (AUD-38)** — `SemanticSearchService.cs:110-121, 263-268, 283-297, 486-489, 544-547` :
   `catch (Exception ex) { … return Enumerable.Empty<…>(); }` — Postgres, pgvector ou fournisseur
   d'embeddings en panne → 200 `TotalResults = 0` ; en hybride, la partie sémantique disparaît sans
   signal ; `OperationCanceledException` avalée (règle 12 : erreurs au `GlobalExceptionHandler`, 499 central).
2. **Filtres ignorés (AUD-39)** — `SemanticSearchService.cs:62-75, 137, 689-733`,
   `SemanticSearchRepository.cs:663-781` : `PatientFilters` (LastName, Ins, PatientId),
   `StatusFilters.IsAnswered`/`IsDraft`, `DateFilters.MedicalDocumentDate*`/`BiologyResultDate*`, et les
   booléens de contenu à `false` sont **comptés actifs mais non appliqués** ; le chemin « filtres seuls »
   relance alors la requête avec `Take(int.MaxValue)`. Déclencheur réel : désactiver la pastille « PJ »
   dans Blazor envoie `HasAttachments = false` (`SearchMailComponent.razor:406`).
3. **Vues par étiquette (AUD-40)** — `SemanticSearchRepository.cs:395, 430, 467-471, 489-493, 512-517` :
   les requêtes plein texte comparent `m.FolderPath == "tag:Urgent"` sans `ParseTagFolder`
   (contrairement aux requêtes vectorielles et à `SearchByFiltersAsync`) → 0 résultat.
4. **Seuil double (AUD-52)** — `SemanticSearchService.cs:314, 331, 621-641`, `SearchController.cs:99` :
   `MinSimilarity` appliqué au dépôt puis sur le score hybride pénalisé (×0,8 / ×0,6) → au-delà de 0,6,
   plus aucun résultat trouvé seulement par mot-clé.

## Objective

Que la recherche **signale** une panne au lieu de rendre une liste vide, applique **chaque** critère
qu'elle accepte (ou le refuse explicitement), couvre les vues par étiquette en plein texte comme en
sémantique, et filtre sa pertinence **une seule fois**.

### Périmètre

1. **Pannes** : exceptions remontées (503 via `UnavailableException`, 499 pour l'annulation) ; mode
   hybride dégradé (une seule jambe disponible) **signalé explicitement** dans la réponse.
2. **Filtres** : tout critère accepté par le contrat est appliqué, ou rejeté en 400 ; `false` signifie
   « sans … » ; le chemin « filtres seuls » est borné comme les autres.
3. **Étiquettes** : le prédicat dossier/étiquette est partagé par les requêtes plein texte, vectorielles et filtres.
4. **Seuil** : un seul filtrage de pertinence, documenté.

### Coordination avec task-192

task-192 (dédup sur l'UID, casse, jokers, signal de troncature) modifie les mêmes méthodes et **le
contrat** (`SearchResponseDto`, dtos-mss). Ordre recommandé : task-192 d'abord, puis cette US ; si
cette US passe avant, le signal de mode dégradé est ajouté de façon compatible avec le futur contrat de task-192.

### Hors périmètre

- Dédup UID, casse, jokers, troncature (task-192).
- L'historique de recherche (jugé sain par l'audit).

## Definition of Done

- [ ] Build passes (0 errors) — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` ; Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] **Tests rouges d'abord** (log des runs rouges dans le task file), rouges sur le code actuel :
  - [ ] dépôt de recherche qui lève → sur le code actuel liste vide 200 ; après correctif 503 `ProblemDetails`
  - [ ] recherche « filtres seuls » avec `HasAttachments = false` → sur le code actuel tout le dossier ; après correctif seulement les mails **sans** pièce jointe, dans la borne
  - [ ] recherche plein texte « Dupont » dans la vue `tag:Urgent` → sur le code actuel 0 ; après correctif les mails étiquetés qui correspondent
  - [ ] `MinSimilarity = 0,7`, résultat trouvé seulement par mot-clé avec score normalisé 1 → rendu
- [ ] Test : fournisseur d'embeddings en panne en mode hybride → résultats plein texte rendus **et** mode dégradé signalé
- [ ] Test : annulation client → 499 (pas de liste vide)
- [ ] Test : chaque filtre du contrat appliqué (un test par famille : patient, statut, dates documentaires, dates de biologie, contenu)
- [ ] Test d'intégration endpoint (règle 1b) : `POST` de recherche avec filtre patient → seuls les mails de ce patient
- [ ] Aucune requête de recherche brute ni INS dans les logs (cohérence task-184)

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` ; Blazor connecté à une boîte de test seedée.
2. **Panne** : arrêter le conteneur Postgres de l'AppHost (ou couper l'accès à la base) et lancer une recherche → **Attendu** : message d'indisponibilité. Avant : « aucun résultat ».
3. **Pastille PJ** : sans texte, activer puis désactiver la pastille « PJ » → seuls les mails sans pièce jointe s'affichent. Avant : toute la boîte.
4. **Vue Urgent** : ouvrir la vue « Urgent », rechercher un nom de patient de test présent dans un mail urgent → il est trouvé. Avant : aucun résultat en mode mot-clé.
5. **Seuil** : régler la similarité minimale à 0,7, rechercher un nom propre → les mails qui le contiennent sont trouvés.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR honorées** : non applicable — fiabilité de la recherche dans la messagerie
- **INS** : le filtre patient par INS est appliqué côté serveur, sans INS dans les logs ni l'URL
- **Authentification PS** : inchangée
- **Habilitations** : inchangées — recherche limitée à la base du praticien
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé ; les pannes de recherche sont journalisées sans le texte recherché
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement inchangé
- **AIPD / impact RGPD** : inchangé
