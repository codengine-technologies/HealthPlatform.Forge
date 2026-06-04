# todo-task-056-health-checks-prod.md — Sondes de santé (readiness/liveness) en production avec dépendances

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**EpicTitle**: Robustesse & observabilité de la plateforme

## Objective

Exposer des **endpoints de santé exploitables en production** pour permettre à
l'orchestrateur (Aspire / Kubernetes) de piloter readiness et liveness, et de
retirer/redémarrer automatiquement un pod dont une dépendance critique est
tombée.

Aujourd'hui, dans
[DependencyInjectionExtensions.cs](Api/Mail/src/Api/DependencyInjectionExtensions.cs)
(`MapDefaultEndpoints`), les routes `/health` et `/alive` ne sont mappées que
si `app.Environment.IsDevelopment()`. **En production, aucune sonde n'est
exposée** — l'orchestrateur ne peut détecter ni un deadlock (liveness) ni une
dépendance indisponible (readiness). Par ailleurs le seul check enregistré est
`"self"` (`AddDefaultHealthChecks`) : **ni PostgreSQL, ni Redis, ni RabbitMQ**
ne sont sondés.

Cible :

1. **Mapper `/health` (readiness) et `/alive` (liveness) dans tous les
   environnements**, en sécurisant l'accès (anonyme mais réservé au réseau
   interne / filtré, jamais d'exposition publique du détail).
2. **Ajouter des health checks pour les dépendances critiques** taggés
   `ready` : PostgreSQL, Redis, RabbitMQ. La liveness (`/alive`) reste
   limitée au check `self` (l'app répond), la readiness (`/health`) agrège
   toutes les dépendances `ready`.
3. **Iso-comportement fonctionnel** : aucune logique métier modifiée, aucun
   endpoint applicatif touché.

Périmètre **purement infra/observabilité**, mono-repo `api-mail`,
sans impact contrat ni frontend.

## Gherkin

_Pas de `.feature` (BDD déprécié, cf. CLAUDE.md règle 1). Comportements
couverts par tests d'intégration._

## Definition of Done

- [ ] Build passes (`dotnet build HealthPlatform.Api.Mail.sln`, 0 erreurs)
- [ ] Tests pass (`dotnet test HealthPlatform.Api.Mail.sln`, 0 échecs)
- [ ] `/alive` (liveness) et `/health` (readiness) mappés **dans tous les
      environnements** (suppression du garde `IsDevelopment()` dans
      `MapDefaultEndpoints`)
- [ ] `/alive` ne valide que les checks taggés `live` (app responsive)
- [ ] `/health` agrège les checks taggés `ready` (dépendances)
- [ ] Health checks ajoutés et taggés `ready` :
      - [ ] PostgreSQL (connexion DB serveur — pas une base tenant)
      - [ ] Redis (`mss-mail-redis`)
      - [ ] RabbitMQ (`mss-mail-rabbitmq`)
- [ ] Les endpoints health restent exclus du tracing (filtre OpenTelemetry
      déjà présent dans `ConfigureOpenTelemetry`) et **n'exposent pas** de
      détail technique sensible (connection strings, versions, secrets) au
      client — réponse réduite au statut agrégé
- [ ] Accès aux endpoints anonyme mais documenté comme **réservé réseau
      interne** (note de déploiement / commentaire) — pas d'exposition
      publique du détail des checks
- [ ] Test d'intégration : `GET /alive` renvoie 200 quand l'app tourne
- [ ] Test d'intégration : `GET /health` renvoie 200 quand les dépendances
      sont disponibles, et **503** quand une dépendance `ready` est down
      (simulée via un check factice / configuration de test)
- [ ] Aucune régression : les endpoints applicatifs et le pipeline existant
      (`ConfigurePipeline`) restent inchangés

## Manual Test Plan

- Lancer le backend via l'AppHost Aspire : `cd Api/Mail/src/AppHost && dotnet run`
  (PostgreSQL, Redis, RabbitMQ démarrés par Aspire).
- **Liveness** : `GET http://localhost:<port>/alive` → **200**, corps minimal
  (`Healthy`). Vérifier que la réponse n'expose aucun détail de dépendance.
- **Readiness (nominal)** : `GET http://localhost:<port>/health` → **200**
  toutes dépendances `ready` OK.
- **Readiness (dégradé)** : arrêter le conteneur Redis (ou RabbitMQ) puis
  refaire `GET /health` → **503** (Unhealthy). `/alive` doit **rester 200**
  (l'app répond toujours).
- **Tracing** : vérifier dans la console/Seq que les appels `/alive` et
  `/health` **n'apparaissent pas** dans les traces (exclusion OpenTelemetry).
- **Sécurité** : confirmer qu'aucune connection string, secret ou version de
  dépendance n'est présent dans le corps des réponses health.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — observabilité/infra de la plateforme,
  sans impact sur un volet métier Ségur.
- **Vague Ségur** : hors Ségur — robustesse/exploitabilité plateforme.
- **Exigences DSR honorées** : non applicable — aucun volet de contenu ou de
  transport modifié.
- **INS** : non applicable — aucune donnée patient manipulée.
- **Authentification PS** : inchangée — les endpoints health sont anonymes
  (réservés réseau interne), le pipeline d'auth applicatif n'est pas touché.
- **Habilitations** : non applicable.
- **Interop CI-SIS** : non applicable — aucun échange CDA/FHIR/HL7v2.
- **Tracé PGSSI-S** : inchangé — les sondes de santé sont volontairement
  exclues du tracing ; aucun évènement métier à journaliser n'est ajouté.
- **Consentement patient** : non applicable.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : oui — environnement de production HDS existant,
  périmètre inchangé.
- **AIPD / impact RGPD** : inchangé — aucun traitement de données de santé ;
  vigilance : ne pas exposer d'information d'infrastructure exploitable dans
  les réponses health.

### DOD santé (items applicables)
- [ ] Les réponses health n'exposent aucune donnée de santé ni secret/
      connection string / détail d'infrastructure exploitable
