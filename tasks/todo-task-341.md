# todo-task-341.md — Aucune donnée de santé ni saisie du praticien dans les journaux et la télémétrie

**Repos**: api-mail
**Dependencies**: — (aucune)
**Epic**: E009
**Single frontend**: true
**Priorité**: **2** — des **constats cliniques** (réponse brute du modèle de tagging), des saisies libres du praticien, une adresse de messagerie et des noms de dossiers personnels partent dans Seq, OTLP ou un `/metrics` non authentifié.

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, **AUD-37**, **AUD-55**, **AUD-60**, **AUD-61**).
> Règle rappelée : l'INS et les données de santé vont dans le journal d'audit en base, **jamais** dans
> Seq / Graylog / OTLP (mémoire « INS — audit oui, logs jamais », task-184, task-265).

## Ce qui est établi (develop @ `14d58398`)

1. **Réponse du LLM (AUD-37)** — `EmailTaggingService.cs:296` :
   `logger.LogWarning(ex, "... Failed to parse JSON response: {Response}", response);` — sur JSON invalide,
   la réponse entière (qui cite par construction du prompt valeurs biologiques et diagnostics) est
   journalisée au niveau Warning, toujours actif. Le même fichier a été durci par task-265.
2. **Saisies libres (AUD-55)** — `AiController.cs:102` et `AiTextService.cs:100` journalisent la
   description d'un modèle (« courrier pour Mme Martin, suivi de son diabète ») en Information ;
   `AiController.cs:70` journalise chaque morceau du texte médical corrigé en Debug (actif en Staging : `Serilog__MinimumLevel__Default: "Debug"`).
3. **Route morte qui journalise une adresse (AUD-60)** — `POST account/mss-imap-test` : exclue du middleware
   (`UserContextEnricherMiddleware.cs:67-70, 164-169`) donc jeton PSC vide → échoue toujours ; journalise
   l'adresse candidate non masquée en Information (EventId 3700, `AccountController.cs:53-57, 111, 291-294`) ;
   aucun client vivant ne l'appelle.
4. **Labels Prometheus (AUD-61)** — `MailProcessingMetrics.cs:551-563`, `BackgroundSyncService.cs:399-506`,
   `Program.cs:219` : le label `folder=<chemin>` porte les noms de dossiers IMAP du praticien (possiblement
   nominatifs), exposés sur `/metrics` sans authentification, avec une cardinalité non bornée.

## Objective

Qu'**aucune donnée de santé, aucune saisie libre du praticien, aucune adresse en clair ni aucun nom de
dossier personnel** n'atteigne les journaux techniques ou la télémétrie, et qu'un garde-fou empêche la réintroduction.

### Périmètre

1. Tagging : journaliser longueur et type d'exception seulement ; compter l'échec (`RecordTaggingFailure`).
2. Saisies libres IA : longueur seulement, aux trois emplacements.
3. `mss-imap-test` : route et exclusion supprimées (remplacées par `POST account/mailboxes`) ; si l'humain
   préfère la garder, adresse masquée et exclusion corrigée.
4. Métriques : label `folder` réduit à une catégorie bornée (inbox, sent, drafts, trash, other).
5. **Garde-fou** : test d'architecture ou analyseur qui refuse un paramètre de log nommé comme une donnée
   sensible (réponse de modèle, corps, description, texte, INS, NIR…) — nomenclature consignée.
6. Balayage complémentaire des autres `Log*` de la couche IA et de l'assistant, avec la même règle.

### Hors périmètre

- Le journal d'audit en base (où l'INS reste, par finalité réglementaire).
- Les fuites par le bus de messages (task-332).

## Definition of Done

- [ ] Build passes (0 errors) — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` ; Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] **Tests rouges d'abord** (log des runs rouges dans le task file) : logger de test capturant les messages —
      réponse de tagging invalide contenant « Potassium 6,8 mmol/L » → sur le code actuel présente dans le log ; après correctif absente
- [ ] Test : description et texte corrigé absents des logs (Information et Debug)
- [ ] Test : route `mss-imap-test` supprimée (404) — ou adresse masquée si conservée par décision humaine consignée
- [ ] Test : un dossier nommé « Dupont Jean » produit le label `folder="other"`
- [ ] Test d'architecture / analyseur de garde-fou actif et vert sur le code corrigé, **rouge** sur une réintroduction volontaire (vérifié puis retiré)
- [ ] Compteur d'échec de tagging incrémenté sur JSON invalide
- [ ] Aucune régression des tableaux de bord qui lisent le label `folder` (vérifier et adapter les requêtes Grafana du dépôt si présentes)

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` ; Seq local ouvert (port 5341).
2. Provoquer une réponse de tagging invalide (fournisseur IA de test renvoyant un JSON tronqué) sur un compte rendu de biologie de test → dans Seq, **aucune** valeur biologique. Avant : la réponse complète en Warning.
3. Générer un modèle avec une description nominative fictive → Seq ne montre que la longueur.
4. `curl http://localhost:<port>/metrics | grep folder=` → seulement des catégories (`inbox`, `other`…), aucun nom de dossier personnel.
5. `POST /api/v1/account/mss-imap-test` → 404 (ou réponse sans adresse journalisée si conservée).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville, biologie
- **Vague Ségur** : hors Ségur — conformité PGSSI-S
- **Exigences DSR honorées** : non applicable — PGSSI-S (masquage des données de santé dans les journaux techniques)
- **INS** : jamais dans les logs (garde-fou étendu) ; inchangée dans le journal d'audit en base
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : **au cœur** — journaux techniques sans donnée de santé ; échecs de tagging comptés
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — Seq / OTLP / Prometheus dans le périmètre ; données de santé retirées
- **AIPD / impact RGPD** : à informer le DPO — données de santé présentes dans les journaux techniques avant correctif (durée de rétention Seq à vérifier)
