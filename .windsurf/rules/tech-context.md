---
trigger: always_on
---

# Contexte technique HealthPlatform

Ce fichier est chargé automatiquement à chaque conversation. Il évite à Cascade
de retrouver à chaque fois les informations d'environnement (chaînes de
connexion, ports, conteneurs Docker). Mettre à jour quand l'environnement
change.

## Stack & build

- Backend : .NET 10 (mss.mail.api), Aspire AppHost (`Api/Mail/src/AppHost`).
- ORM : Entity Framework Core sur PostgreSQL (provider Npgsql).
- Migrations : FluentMigrator (table `MailPatients`, fichiers dans `Api/Mail/src/Infrastructure/Migrations/`).
- Frontend Angular : Nx workspace dans `Client/Angular/front`, lib principale `mss-lib`.
- Frontend Blazor : `Client/Blazor/Src/Shell` (legacy en parallèle de l'Angular).
- Tests : xUnit côté .NET, Vitest côté Angular (`npx nx run mss-lib:test`).

## Base de données principale (mss-mail-api)

- Moteur : PostgreSQL avec extension `pgvector`.
- Conteneur Docker : `postgres-pgvector` (image `postgresql-postgres`).
- Hôte / port hôte : `localhost:5432`.
- User / password dev : `postgres` / `postgres`.
- Variable d'environnement injectée par `AppHost.cs` :
  - `MSS-MAIL-CONNECTIONSTRING=Host=localhost;Port=5432;Username=postgres;Password=postgres`
- Une base est créée par utilisateur authentifié, via le pattern :
  - `mss_mail_user_{email}` (voir `UserContextInfo.GetUserDatabaseName`).
- **Base active à utiliser exclusivement** :
  - `mss_mail_user_virginie.medecinrpps0062267@medecin.formation.mssante.fr`
  - Toutes les requêtes / inspections doivent cibler cette base sauf demande explicite contraire.

### Commandes utiles

```powershell
# Lister les bases utilisateurs
docker exec postgres-pgvector psql -U postgres -c "\l"

# Se connecter à une base utilisateur (échapper l'arobase via guillemets)
docker exec -it postgres-pgvector psql -U postgres -d "mss_mail_user_virginie.medecinrpps0062267@medecin.formation.mssante.fr"

# Lancer une requête ad-hoc
docker exec postgres-pgvector psql -U postgres -d "<db_name>" -c "SELECT id, \"FileName\", \"DocumentId\" FROM \"MailAttachments\" LIMIT 10;"
```

## Services dépendants (lancés par Aspire AppHost)

| Service | Conteneur | URL / port hôte | Identifiants |
|---------|-----------|-----------------|--------------|
| Redis cache | `mss-mail-redis` | `localhost:6379` | sans auth |
| RabbitMQ | `mss-mail-rabbitmq` | `localhost:5672` (management ~15672) | `guest` / `guest` |
| Seq (logs) | `seq` | http://localhost:5341 | admin / `admin` |
| Seq (Aspire) | `mss-mail-seq-*` | http://localhost:5342 | admin / `admin` |
| Prometheus | `mss-mail-prometheus` | http://localhost:9090 | – |
| Grafana | `mss-mail-grafana` | http://localhost:3001 | admin / `admin` |
| Flagsmith | `flagsmith-app` | http://localhost:8400 | – |
| Flagsmith DB | `flagsmith-db` | `localhost:58074` | postgres / `flagsmith_pwd_2026!` |
| Keycloak | `psc-auth-proxy-keycloak-*` | http://localhost:63703 | – |
| MailHog | `psc-auth-proxy-mailhog-*` | SMTP `localhost:63666`, UI `:63667` | – |
| Graylog | `graylog-graylog-1` | http://localhost:9000 | – |
| Jaeger | `jaeger` | http://localhost:16686 | – |
| Vidal API | `vidal-api` | http://localhost:8011 | – |

## Endpoints applicatifs (dev)

- Mail API : `https://localhost:7142` (HTTPS) / `http://localhost:5052` (metrics).
- Frontend Angular (Nx serve) : `https://localhost:4200`.
- Redis Commander UI : http://localhost:8082.
- Aspire dashboard : démarré par `dotnet run` dans `Api/Mail/src/AppHost`.

## MCP servers utilisables

- `postgresql` : interroger Postgres directement (préférer ce MCP plutôt que
  `docker exec` quand disponible).
- `seq` : récupérer les logs structurés de l'API.
- `graylog` : logs centralisés (incluant clients).
- `git`, `ado` : gestion source/PR.
- `playwright` : e2e Angular.
- `aspire` : inspecter l'état des ressources démarrées par AppHost.

## DTOs partagés (`HealthPlatform.Dtos.Mss`)

- Projet : `Dtos/HealthPlatform.Dtos.Mss.csproj` (référencé en NuGet par les
  consommateurs externes, **pas** par référence projet directe).
- Contient les contrats échangés entre `mss.mail.api`, le shell Blazor et tout
  client tiers (notamment `psc-auth-proxy`).
- **Workflow de mise à jour** : après modification d'un DTO, il faut pousser
  les changements sur GitHub (publication du package NuGet via la CI) avant
  que les projets consommateurs (API backend, Blazor, proxies) puissent
  récupérer la nouvelle version.
- **Skill obligatoire — INVOCATION SYSTÉMATIQUE** :
  `.windsurf/dtos-publish-skill/SKILL.md` **doit être invoqué sans exception
  dès qu'un fichier sous `Dtos/` est ajouté, modifié ou supprimé**, y compris
  pour des changements purement cosmétiques (commentaire, attribut
  `[ExcludeFromCodeCoverage]`, refactor de namespace, etc.). Il n'y a **pas**
  de seuil de "trivialité" en dessous duquel on saute le skill : toute
  modification du sous-repo `Dtos/` doit produire un commit + push + run CI
  vert + bump des consommateurs.
- Le skill automatise&nbsp;:
  1. `git status / add / commit / push` sur le sous-repo
     `https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss.git`
     (toujours via `git -C d:\TechWatch\HealthPlatform\Dtos`, jamais mélanger
     avec le repo parent `HealthPlatform.Forge`).
  2. Attente de la CI GitHub Actions (`gh run watch --exit-status`).
  3. Récupération de la version NuGet publiée
     (`<github.run_number>.0.0`).
  4. **Bump systématique** des `Directory.Packages.props` consommateurs
     (`Api/Mail/`, `Client/Blazor/`) avec commit dans chacun de ces repos
     (qui sont des dépôts Git distincts, gitignorés par `Forge`).
- Ne **jamais** considérer une tâche touchant `Dtos/` terminée tant que la
  CI n'est pas verte et que les consommateurs n'ont pas été bumpés au commit
  correspondant.

## Conventions du projet

- Pas de `_` dans les noms de méthodes / classes (rule utilisateur).
- Pas de génération de documentation `.md` non sollicitée (rule utilisateur).
- Commentaires dans le code en anglais.
- Respecter strictement les règles SonarLint à la génération.

## IHE_XDM / pièces jointes

- Le placeholder `IHE_XDM.ZIP` (filename insensible à la casse) est conservé
  en base pour traçabilité mais **exclu** des compteurs / affichages utilisateur.
- Les PDFs et images embarqués sont extraits récursivement par `CDAParser` et
  persistés dans `MailAttachments` avec `DocumentId` non null.
- `MailDto.AttachmentCount` (peuplé par `MailRepository.GetMailsByUidsAsync`)
  donne le nombre de pièces jointes utilisateur (hors wrapper).
