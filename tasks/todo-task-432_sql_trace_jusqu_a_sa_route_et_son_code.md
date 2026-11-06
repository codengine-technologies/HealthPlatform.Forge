# todo-task-432.md — Chaque requête SQL porte sa route et la méthode qui l'émet

**Repos**: api-mail
**Dependencies**: — (aucune)
**Epic**: E015
**Single frontend**: true
**Priorité**: **2**. Étage 1 de l'amélioration « le banc comme outil d'exploration » (2026-11-06). Une ligne de
`pg_stat_statements` ne dit pas quel code l'a émise. Remonter d'une requête coûteuse à sa cause demande aujourd'hui de
chercher les noms de tables et de colonnes dans le code, ce qui est lent et parfois ambigu. Utile aussi en
exploitation : la même information sert à lire `pg_stat_statements` en production.

> **Origine.** Exploration du 2026-11-06 (task-429, task-430) : chaque candidat a demandé une recherche dans le code
> pour retrouver son site d'émission.

## Ce qui est établi

- **Un intercepteur de commandes existe** : `DbCommandPhaseInterceptor` (`src/Infrastructure/Telemetry/DbOperationPhaseInterceptors.cs`,
  task-243). Il voit chaque commande avant son exécution, mais ne mesure que les opérations encadrées par un
  `DbOperationScope`.
- **Postgres ignore les commentaires pour regrouper les requêtes** (`queryid`), mais **garde le texte** de la première
  exécution vue, par base. Un commentaire en tête du SQL apparaît donc dans `pg_stat_statements` sans démultiplier les
  formes.
- **Limite connue** : si deux méthodes émettent exactement le même SQL dans une même base, seul le commentaire de la
  première est gardé. C'est rare avec des requêtes EF Core écrites site par site.
- **EF Core 10** propose `TagWith` et `TagWithCallSite`, mais requête par requête, sur des centaines de sites.

## Objective

Chaque commande SQL émise par api-mail commence par un commentaire qui nomme la **route** et la **méthode** qui l'a
émise : `/* route=GET /api/v1/Patients/{patientId}/medical-documents site=PatientRepository.LoadMailsWithAttachmentsAsync */`.

Règles :
- **La route est le gabarit, jamais le chemin réel** : `{patientId}`, pas l'identifiant. Elle vient de l'activité HTTP
  en cours (`http.route`). Hors requête HTTP (consommateur du bus, tâche de fond), le commentaire nomme l'opération
  (consommateur, tâche) : `route=bus:AddNewMail`.
- **La méthode** est la première méthode des dépôts (`*Repository`, `PostgresTenantRegistryClient`) dans la pile
  d'appel. Elle est **calculée une seule fois par texte SQL distinct**, puis mise en cache (par processus, taille
  bornée). Le coût par commande est une recherche dans un dictionnaire.
- **Aucune donnée dans le commentaire** : ni identifiant, ni paramètre, ni valeur. Uniquement des noms de route et de
  méthode du code. Le texte SQL peut finir dans les journaux de Postgres : rien de ce qui y est ajouté ne doit être une
  donnée de santé ou une donnée personnelle.
- **Désactivable** par configuration (`Database:SqlCallSiteComments`), **activé par défaut**.
- **Comportement inchangé** : mêmes résultats, même nombre de requêtes. Le surcoût est mesuré au banc.
- **`report.py`** extrait `route` et `site` du texte de chaque forme et les affiche dans le top des requêtes, et dans les
  signaux de task-431 si elle est mergée.

### Hors périmètre

- Instrumenter le temps SQL par route dans Prometheus : `pg_stat_statements` et le commentaire suffisent pour
  l'exploration.
- Les requêtes émises par Npgsql lui-même (chargement des types) : sans site applicatif, elles restent sans commentaire.

## Definition of Done

- [ ] Build passes (0 errors) : `HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) : `HealthPlatform.Api.Mail.sln`
- [ ] **Test d'intégration de bout en bout (règle 1b)** : un appel à
      `GET /api/v1/Patients/{patientId}/medical-documents?page=1&pageSize=20` sur la vraie pile et la vraie base du
      fixture :
      - la réponse est inchangée ;
      - le SQL relevé par intercepteur commence par
        `/* route=GET /api/v1/Patients/{patientId}/medical-documents site=PatientRepository.` ;
      - le commentaire ne contient pas l'identifiant du patient ;
      - **vu rouge** sans l'intercepteur.
- [ ] **Test d'intégration, la base garde le commentaire** : après l'appel, `pg_stat_statements` de la base du fixture
      (si l'extension est chargée par le fixture ; sinon, `pg_stat_activity` pendant l'appel, ou les journaux du
      conteneur) contient le commentaire. Le moyen retenu est justifié dans le `Develop log`
- [ ] **Test d'intégration, acte système** : une écriture faite par le consommateur du bus porte `route=bus:…` et son
      site
- [ ] **Désactivation** : `Database:SqlCallSiteComments=false` ne produit aucun commentaire (test d'intégration)
- [ ] Tests unitaires : la résolution du site (premier dépôt de la pile), le cache par texte (une seule résolution pour
      deux exécutions), la borne du cache
- [ ] **Surcoût mesuré au banc**, tir court contre contrôle `develop` dans la même session :
      - aucune étape ralentie de plus de 5 % au p50 ;
      - CPU d'api-mail relevé ;
      - rapport régénéré : le top des requêtes affiche `route` et `site`.
- [ ] `report.py` affiche `route` et `site` par forme : test sur une fixture de `pg_stat_statements` qui porte le
      commentaire
- [ ] Aucune donnée de santé en clair dans les logs, ni dans le texte SQL : contrôle mécanique dans le test
      d'intégration, aucune valeur d'identifiant dans le commentaire
- [ ] Parcours e2e verts (`/e2e`), aucun scénario ajouté : aucun parcours n'est modifié

## Manual Test Plan

- [ ] `cd Api/Mail && dotnet run --project src/AppHost`, ouvrir la messagerie et le dossier d'un patient.
- [ ] Sur la base de la boîte :
      `SELECT left(query, 160) FROM pg_stat_statements WHERE query LIKE '/* route=%' LIMIT 20;` : chaque requête porte
      sa route et sa méthode, sans aucun identifiant.
- [ ] Relancer avec `Database__SqlCallSiteComments=false` : les nouvelles formes n'ont plus de commentaire.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — observabilité interne
- **Vague Ségur** : hors Ségur — même raison
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — garde-fou explicite : aucun identifiant, ni INS, ni NIR, ni patient, dans le commentaire
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé. Le commentaire n'est pas une trace d'acte et n'en remplace aucune. Il ne porte aucune
  identité (ni RPPS, ni nom), pour que les journaux de Postgres n'en contiennent pas
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — pas de donnée nouvelle. Le texte SQL reste dans Postgres, sur l'environnement HDS
- **AIPD / impact RGPD** : inchangée — aucune donnée personnelle ajoutée au texte SQL
